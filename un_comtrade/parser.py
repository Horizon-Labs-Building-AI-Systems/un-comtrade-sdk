"""Metadata parser and normalizer for the UN Comtrade Python SDK.

This module is the L3 metadata-layer parser per
`003_ARCHITECTURE.md` §5.3 and `008_METADATA_LAYER_SPEC.md`
§6, plus the L4 trade-layer parser per `009_TRADE_LAYER_SPEC.md`.
It converts raw upstream JSON payloads into the
canonical model instances declared in `un_comtrade.models`.

Two parsers live here:

- **`MetadataParser`** — L3 metadata reference catalogues
  (R01-R15: reporters, partners, HS codes, trade flows,
  transport modes, quantity units, data items).
- **`TradeParser`** — L4 trade observations (E12
  TradeRecord). Converts the upstream's camelCase
  payload into the canonical `TradeRecord` model
  defined in `un_comtrade.models.trade`.

Responsibilities (per the task scope):

- **Parsing** — turn upstream JSON dicts into model
  instances.
- **Validation** — model `__post_init__` enforces the
  documented field constraints; invalid records are
  dropped with a `WARNING` log.
- **Normalization** — handle field-name variants
  (e.g. `PartnerCode` vs `reporterCode` for partners),
  case differences (`flowDesc` vs `flowCode`), and
  date-format variants (ISO-8601 with or without time).
- **Deduplication** — records sharing a primary key are
  collapsed (first-wins for metadata; composite-key
  first-wins for trade records).

Excluded (handled by other layers):

- Downloading — `un_comtrade.metadata.MetadataDownloader`.
- Storage / persistence — `un_comtrade.cache.MetadataCache`.
- Trade response envelope — `un_comtrade.trade._execute`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping

from .logging import get_logger
from .models import (
    Classification,
    Commodity,
    Country,
    DataItem,
    Frequency,
    HSCode,
    Partner,
    Quantity,
    QuantityUnit,
    RecordTradeFlow,
    ReferenceEntry,
    Reporter,
    TradeFlow,
    TradePartner,
    TradeRecord,
    TradeValue,
    TransportMode,
)


__all__ = [
    "ParseResult",
    "MetadataParser",
    "SUPPORTED_RESOURCES",
    "TRADE_RECORD_KEY_FIELDS",
    "TradeParser",
]


#: Resources whose parsers return canonical model instances.
#: Other resources (R06/R07/R08 SITC/BEC/EBOPS) require
#: their own model classes; their raw payloads are not yet
#: mapped here.
SUPPORTED_RESOURCES: frozenset[str] = frozenset(
    {"R01", "R02", "R03", "R04", "R05", "R09", "R10", "R12", "R14", "R15"}
)


# ---------------------------------------------------------------------------
# Parse result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParseResult:
    """The outcome of a parse operation.

    `records` is the canonical model list (deduplicated,
    validated). `skipped` is the number of records the
    parser dropped because they failed validation or
    were duplicates.
    """

    records: list[Any]
    skipped: int


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class MetadataParser:
    """L3 metadata parser / normalizer.

    Stateless: every method is a pure function of its
    inputs. The parser holds no resources and can be
    shared across threads.
    """

    def __init__(self, *, log_skipped: bool = True) -> None:
        """Construct a parser.

        Parameters
        ----------
        log_skipped
            When `True` (default) the parser logs a
            WARNING for every record it skips (invalid or
            duplicate). When `False` the skip is silent —
            useful for tests and high-throughput batch
            parsing.
        """
        self._log_skipped = log_skipped
        self._logger = get_logger("metadata")

    # ----- Top-level dispatch ----------------------------------------------

    def parse(
        self, resource_id: str, payload: Any
    ) -> ParseResult:
        """Parse `payload` for the given `resource_id`.

        Returns a `ParseResult` containing the canonical
        records and the number of skipped records. The
        caller (the catalogue fetcher) is responsible for
        any post-processing.
        """
        method = self._dispatch(resource_id)
        records_list = self._extract_data(payload)
        return self._run_with_skipped_count(records_list, method)

    def parse_payload(
        self, payload: Any, method: Callable[[list[dict]], list[Any]]
    ) -> ParseResult:
        """Parse `payload` using the supplied `method`.

        Used by the dispatch table and exposed for callers
        that want to use a custom parser.
        """
        records_list = self._extract_data(payload)
        return self._run_with_skipped_count(records_list, method)

    # ----- Resource parsers ------------------------------------------------

    def parse_r01_references(self, records: list[dict]) -> list[ReferenceEntry]:
        return self._dedupe_by(
            records,
            lambda r: (r.get("category"), r.get("variable")),
            lambda r: ReferenceEntry(
                category=str(r.get("category") or ""),
                variable=str(r.get("variable") or ""),
                description=str(r.get("description") or ""),
                fileuri=str(r.get("fileuri") or ""),
            ),
        )

    def parse_r02_reporters(self, records: list[dict]) -> list[Country]:
        return self._dedupe_by(
            records,
            lambda r: self._coerce_int(r.get("reporterCode", r.get("id"))),
            lambda r: Country(
                country_code=self._coerce_int(r.get("reporterCode", r.get("id"))),
                iso_alpha2=self._normalize_alpha2(r.get("reporterCodeIsoAlpha2")),
                iso_alpha3=self._normalize_alpha3(r.get("reporterCodeIsoAlpha3")),
                display_name=str(r.get("reporterDesc") or r.get("text") or ""),
                entry_effective_date=self._parse_date(r.get("entryEffectiveDate")),
                entry_expired_date=self._parse_date(r.get("entryExpiredDate")),
            ),
        )

    def parse_r03_partners(self, records: list[dict]) -> list[Partner]:
        return self._dedupe_by(
            records,
            lambda r: self._coerce_int(r.get("PartnerCode", r.get("id"))),
            lambda r: Partner(
                country_code=self._coerce_int(r.get("PartnerCode", r.get("id"))),
                iso_alpha2=self._normalize_alpha2(r.get("PartnerCodeIsoAlpha2")),
                iso_alpha3=self._normalize_alpha3(r.get("PartnerCodeIsoAlpha3")),
                display_name=str(r.get("PartnerDesc") or r.get("text") or ""),
                entry_effective_date=self._parse_date(r.get("entryEffectiveDate")),
                entry_expired_date=self._parse_date(r.get("entryExpiredDate")),
            ),
        )

    def parse_r04_hs_combined(
        self, records: list[dict]
    ) -> list[HSCode]:
        # The HS combined catalogue covers multiple editions;
        # the parser tags each record with classification_code="HS"
        # and edition="combined" (a sentinel).
        return self._parse_hs_codes(records, edition="combined")

    def parse_r05_hs_edition(
        self, records: list[dict], edition: str
    ) -> list[HSCode]:
        return self._parse_hs_codes(records, edition=edition)

    def parse_r09_frequencies(self, records: list[dict]) -> list[Frequency]:
        return self._dedupe_by(
            records,
            lambda r: str(r.get("id") or ""),
            lambda r: Frequency(
                frequency_code=str(r.get("id") or ""),
                display_name=str(r.get("text") or ""),
            ),
        )

    def parse_r10_trade_flows(self, records: list[dict]) -> list[TradeFlow]:
        return self._dedupe_by(
            records,
            lambda r: str(r.get("id") or ""),
            lambda r: TradeFlow(
                flow_code=str(r.get("id") or ""),
                display_name=str(r.get("text") or ""),
            ),
        )

    def parse_r12_transport_modes(
        self, records: list[dict]
    ) -> list[TransportMode]:
        return self._dedupe_by(
            records,
            lambda r: self._coerce_int(r.get("id")),
            lambda r: TransportMode(
                mot_code=self._coerce_int(r.get("id")),
                display_name=str(r.get("text") or ""),
            ),
        )

    def parse_r14_quantity_units(
        self, records: list[dict]
    ) -> list[QuantityUnit]:
        return self._dedupe_by(
            records,
            lambda r: self._coerce_int(r.get("qtyCode", r.get("id"))),
            lambda r: QuantityUnit(
                qty_unit_code=self._coerce_int(r.get("qtyCode", r.get("id"))),
                qty_abbr=str(r.get("qtyAbbr") or r.get("text") or ""),
                qty_description=str(r.get("qtyDescription") or ""),
            ),
        )

    def parse_r15_data_items(self, records: list[dict]) -> list[DataItem]:
        return self._dedupe_by(
            records,
            lambda r: str(r.get("dataItem") or ""),
            lambda r: DataItem(
                data_item=str(r.get("dataItem") or ""),
                description=str(r.get("description") or ""),
            ),
        )

    # ----- Helpers --------------------------------------------------------

    def _dispatch(self, resource_id: str) -> Callable[[list[dict]], list[Any]]:
        """Map a resource id to its parser method."""
        if resource_id not in SUPPORTED_RESOURCES:
            raise ValueError(
                f"No parser registered for resource {resource_id!r}; "
                f"supported: {sorted(SUPPORTED_RESOURCES)}"
            )
        name = {
            "R01": "parse_r01_references",
            "R02": "parse_r02_reporters",
            "R03": "parse_r03_partners",
            "R04": "parse_r04_hs_combined",
            "R05": "parse_r05_hs_edition",
            "R09": "parse_r09_frequencies",
            "R10": "parse_r10_trade_flows",
            "R12": "parse_r12_transport_modes",
            "R14": "parse_r14_quantity_units",
            "R15": "parse_r15_data_items",
        }[resource_id]
        method: Callable[..., list[Any]] = getattr(self, name)
        return method  # type: ignore[return-value]

    def _parse_hs_codes(
        self, records: list[dict], *, edition: str
    ) -> list[HSCode]:
        return self._dedupe_by(
            records,
            lambda r: str(r.get("id") or ""),
            lambda r: HSCode(
                commodity_code=str(r.get("id") or ""),
                classification_code="HS",
                edition=edition,
                display_name=(
                    str(r.get("text") or "") if r.get("text") else None
                ),
            ),
        )

    def _extract_data(self, payload: Any) -> list[dict]:
        """Return the records list from the upstream payload shape.

        The upstream may return either a bare JSON array or
        an object with a top-level ``data`` array. This
        helper normalises both shapes to a list of
        records.
        """
        if isinstance(payload, list):
            return payload
        if isinstance(payload, Mapping) and isinstance(payload.get("data"), list):
            return payload["data"]
        raise ValueError(
            f"Unsupported payload shape: expected list or "
            f"object with 'data' array; got {type(payload).__name__}"
        )

    def _run_with_skipped_count(
        self,
        records_list: list[dict],
        method: Callable[..., list[Any]],
    ) -> ParseResult:
        """Invoke `method(records_list)` and return a `ParseResult`."""
        input_count = len(records_list)
        try:
            records = method(records_list)
        except (ValueError, TypeError) as exc:
            # Top-level parser failure (not a per-record skip).
            # Log and return an empty result.
            if self._log_skipped:
                self._logger.warning(
                    "parser failed method=%s exc=%r",
                    method.__name__,
                    exc,
                )
            return ParseResult(records=[], skipped=input_count)
        skipped = input_count - len(records)
        return ParseResult(records=records, skipped=skipped)

    def _dedupe_by(
        self,
        records: list[dict],
        key: Callable[[dict], Any],
        factory: Callable[[dict], Any],
    ) -> list[Any]:
        """Deduplicate `records` by `key(record)` and build models via `factory`.

        Records that fail construction are dropped (logged
        when `log_skipped` is `True`). When two records share
        a key, the first wins.
        """
        seen: set[Any] = set()
        result: list[Any] = []
        for record in records:
            try:
                k = key(record)
            except (ValueError, TypeError) as exc:
                if self._log_skipped:
                    self._logger.warning(
                        "skipped record (bad key) exc=%r", exc
                    )
                continue
            if k in seen:
                if self._log_skipped:
                    self._logger.debug(
                        "skipped duplicate key=%r", k
                    )
                continue
            try:
                instance = factory(record)
            except (ValueError, TypeError) as exc:
                if self._log_skipped:
                    self._logger.warning(
                        "skipped record (validation failed) "
                        "key=%r exc=%r",
                        k,
                        exc,
                    )
                continue
            seen.add(k)
            result.append(instance)
        return result

    # ----- Field-level helpers ---------------------------------------------

    @staticmethod
    def _coerce_int(value: Any) -> int:
        """Coerce a value to int. Strings are parsed as base-10."""
        if isinstance(value, bool):
            raise TypeError("bool is not a valid integer code")
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        raise TypeError(
            f"Cannot coerce {type(value).__name__} to int"
        )

    @staticmethod
    def _normalize_alpha2(value: Any) -> str | None:
        """Normalise an ISO-3166-1 alpha-2 code; returns None for missing."""
        if value is None or value == "":
            return None
        return str(value).upper()

    @staticmethod
    def _normalize_alpha3(value: Any) -> str | None:
        """Normalise an ISO-3166-1 alpha-3 code; returns None for missing."""
        if value is None or value == "":
            return None
        return str(value).upper()

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        """Parse a date from an ISO-8601 string or date object.

        Accepts:
        - `None` -> `None`
        - `date` -> `date` (returned as-is)
        - `str` -> the date portion is parsed; the time
          portion (if present) is ignored.
        Returns `None` for any unparseable value rather than
        raising — bad upstream dates must not break the
        parser.
        """
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            return None
        # Take the date portion before any 'T' / ' ' separator.
        text = value.split("T", 1)[0].split(" ", 1)[0]
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# L4 Trade Parser
# ---------------------------------------------------------------------------


#: Composite key fields for `TradeRecord` deduplication
#: (per `006_DATA_MODEL.md` §3.12). The combination is
#: unique within the upstream dataset. Records that share
#: all of these fields are considered the same observation.
TRADE_RECORD_KEY_FIELDS: tuple[str, ...] = (
    "reporter_code",
    "partner_code",
    "period",
    "flow_code",
    "commodity_code",
    "classification_code",
    "edition",
    "customs_code",
    "mot_code",
    "partner2_code",
)


class TradeParser:
    """L4 trade-record parser / normalizer.

    Stateless: every method is a pure function of its
    inputs. The parser holds no resources and can be
    shared across threads.

    Converts raw upstream payloads (camelCase dicts)
    into canonical `TradeRecord` instances per
    `006_DATA_MODEL.md` §3.12 / §4.12.

    Responsibilities (per the P2-006 task scope):

    - **Parsing** — turn upstream JSON dicts into
      `TradeRecord` instances.
    - **Validation** — `TradeRecord.__post_init__`
      enforces the documented field constraints;
      invalid records are dropped with a `WARNING`
      log.
    - **Deduplication** — records sharing the
      composite key (per `TRADE_RECORD_KEY_FIELDS`)
      are collapsed (first-wins; "latest wins"
      deduplication by `ref_period_id` is a future
      enhancement).
    - **Decimal handling** — monetary and quantity
      values are coerced via `Decimal(str(value))`
      per ADR-0027 to preserve exact precision.

    Excluded (handled by other layers):

    - Downloading — `un_comtrade.metadata.MetadataDownloader`.
    - Response envelope validation —
      `un_comtrade.trade._execute`.
    """

    def __init__(self, *, log_skipped: bool = True) -> None:
        """Construct a trade parser.

        Parameters
        ----------
        log_skipped
            When `True` (default) the parser logs a
            WARNING for every record it skips (invalid
            or duplicate). When `False` the skip is
            silent — useful for tests and high-
            throughput batch parsing.
        """
        self._log_skipped = log_skipped
        self._logger = get_logger("metadata")

    # ----- Top-level dispatch ----------------------------------------------

    def parse_records(
        self, raw_records: list[dict[str, Any]]
    ) -> ParseResult:
        """Parse a list of raw upstream records.

        Returns a `ParseResult` containing the canonical
        `TradeRecord` list and the number of skipped
        records (duplicates or validation failures).
        """
        seen: set[tuple] = set()
        result: list[TradeRecord] = []
        skipped = 0
        for raw in raw_records:
            if not isinstance(raw, Mapping):
                skipped += 1
                if self._log_skipped:
                    self._logger.warning(
                        "skipped trade record (not a mapping): got %s",
                        type(raw).__name__,
                    )
                continue
            try:
                record = self.parse_record(raw)
            except (ValueError, TypeError) as exc:
                skipped += 1
                if self._log_skipped:
                    self._logger.warning(
                        "skipped trade record (validation failed): %s",
                        exc,
                    )
                continue
            try:
                k = self._record_key(record)
            except (ValueError, TypeError) as exc:
                skipped += 1
                if self._log_skipped:
                    self._logger.warning(
                        "skipped trade record (bad key): %s",
                        exc,
                    )
                continue
            if k in seen:
                skipped += 1
                if self._log_skipped:
                    self._logger.debug(
                        "skipped duplicate trade record key=%r",
                        k,
                    )
                continue
            seen.add(k)
            result.append(record)
        return ParseResult(records=result, skipped=skipped)

    def parse_record(self, raw: Mapping[str, Any]) -> TradeRecord:
        """Parse a single raw upstream record into a `TradeRecord`.

        Raises `ValueError` or `TypeError` on any
        validation failure (caught by `parse_records`
        and reported as a skip).
        """
        # ----- Identifier / metadata
        type_code = self._coerce_str(raw, "typeCode")
        frequency_code = self._coerce_str(raw, "freqCode")
        classification_code = self._coerce_str(
            raw, "classificationCode"
        )
        classification_search_code = self._optional_str(
            raw, "classificationSearchCode"
        )
        edition = self._coerce_str(raw, "classificationCode")
        # Per the data model §4.12, `edition` is required and
        # is sourced from the same value as `classificationCode`
        # for HS-classified records (e.g., "H6", "H4").
        is_original_classification = self._optional_bool(
            raw, "isOriginalClassification"
        )

        # ----- Period
        ref_period_id = self._optional_int(raw, "refPeriodId")
        ref_year = self._coerce_int(raw, "refYear")
        ref_month = self._coerce_int(raw, "refMonth")
        period = self._coerce_str(raw, "period")

        # ----- Subjects
        reporter = Reporter(
            reporter_code=self._coerce_int(raw, "reporterCode"),
            iso3=self._optional_str(raw, "reporterISO"),
            name=self._optional_str(raw, "reporterDesc"),
        )
        partner = TradePartner(
            partner_code=self._coerce_int(raw, "partnerCode"),
            iso3=self._optional_str(raw, "partnerISO"),
            name=self._optional_str(raw, "partnerDesc"),
        )
        partner2_raw_code = raw.get("partner2Code")
        if partner2_raw_code is None or (
            isinstance(partner2_raw_code, (int, float))
            and int(partner2_raw_code) == 0
            and raw.get("partner2ISO") in (None, "", "W00")
        ):
            # Default sentinel: partner2 absent or all-zero.
            partner2: TradePartner | None = None
        else:
            partner2 = TradePartner(
                partner_code=self._coerce_int(raw, "partner2Code"),
                iso3=self._optional_str(raw, "partner2ISO"),
                name=self._optional_str(raw, "partner2Desc"),
            )
        flow = RecordTradeFlow(
            flow_code=self._coerce_str(raw, "flowCode"),
            flow_name=self._optional_str(raw, "flowDesc"),
        )
        commodity = Commodity(
            commodity_code=self._coerce_str(raw, "cmdCode"),
            name=self._optional_str(raw, "cmdDesc"),
        )

        # ----- Procedural
        customs_code = self._coerce_str(raw, "customsCode")
        customs_name = self._optional_str(raw, "customsDesc")
        mos_code = self._coerce_str(raw, "mosCode")
        mot_code = self._coerce_int(raw, "motCode")
        mot_name = self._optional_str(raw, "motDesc")

        # ----- Quantities
        quantity = Quantity(
            qty=self._optional_decimal(raw, "qty"),
            qty_unit_code=self._coerce_int(raw, "qtyUnitCode"),
            qty_unit_abbr=self._optional_str(raw, "qtyUnitAbbr"),
            is_estimated=self._optional_bool(raw, "isQtyEstimated")
            or False,
            alt_qty=self._optional_decimal(raw, "altQty"),
            alt_qty_unit_code=self._optional_int(raw, "altQtyUnitCode"),
            alt_qty_unit_abbr=self._optional_str(raw, "altQtyUnitAbbr"),
            is_alt_qty_estimated=self._optional_bool(
                raw, "isAltQtyEstimated"
            )
            or False,
        )

        # ----- Weights
        net_weight_kg = self._optional_decimal(raw, "netWgt")
        is_net_weight_estimated = (
            self._optional_bool(raw, "isNetWgtEstimated") or False
        )
        gross_weight_kg = self._optional_decimal(raw, "grossWgt")
        is_gross_weight_estimated = (
            self._optional_bool(raw, "isGrossWgtEstimated") or False
        )

        # ----- Trade value
        trade_value = TradeValue(
            primary_value=self._coerce_decimal(raw, "primaryValue"),
            fob_value=self._optional_decimal(raw, "fobvalue"),
            cif_value=self._optional_decimal(raw, "cifvalue"),
        )

        # ----- Flags
        legacy_estimation_flag = self._coerce_int(
            raw, "legacyEstimationFlag", default=0
        )
        is_reported = self._optional_bool(raw, "isReported") or False
        is_aggregate = self._optional_bool(raw, "isAggregate") or False

        # ----- Provenance (derived / opaque)
        provenance = self._build_provenance(raw)

        return TradeRecord(
            type_code=type_code,
            frequency_code=frequency_code,
            classification_code=classification_code,
            classification_search_code=classification_search_code,
            edition=edition,
            is_original_classification=is_original_classification,
            ref_period_id=ref_period_id,
            ref_year=ref_year,
            ref_month=ref_month,
            period=period,
            reporter=reporter,
            partner=partner,
            partner2=partner2,
            flow=flow,
            commodity=commodity,
            customs_code=customs_code,
            customs_name=customs_name,
            mos_code=mos_code,
            mot_code=mot_code,
            mot_name=mot_name,
            quantity=quantity,
            net_weight_kg=net_weight_kg,
            is_net_weight_estimated=is_net_weight_estimated,
            gross_weight_kg=gross_weight_kg,
            is_gross_weight_estimated=is_gross_weight_estimated,
            trade_value=trade_value,
            legacy_estimation_flag=legacy_estimation_flag,
            is_reported=is_reported,
            is_aggregate=is_aggregate,
            provenance=provenance,
        )

    # ----- Helpers --------------------------------------------------------

    @staticmethod
    def _record_key(record: TradeRecord) -> tuple:
        """Return the composite deduplication key for a `TradeRecord`.

        Per `006_DATA_MODEL.md` §3.12 the composite
        key is `(reporter_code, partner_code, period,
        flow_code, commodity_code, classification_code,
        edition, customs_code, mot_code, partner2_code)`.

        Internal — prefer `composite_key` (public).
        """
        return TradeParser.composite_key(record)

    @staticmethod
    def composite_key(record: TradeRecord) -> tuple:
        """Return the composite deduplication key for a `TradeRecord`.

        Public alias of the internal `_record_key`
        helper. The composite key uniquely identifies a
        trade observation per the documented data-model
        contract (§3.12): two `TradeRecord` instances
        with the same composite key represent the same
        upstream observation (potentially with
        different `ref_period_id` revision markers).

        Used by the pagination engine
        (`un_comtrade.pagination`) to merge records
        across pages without duplication.
        """
        return (
            record.reporter.reporter_code,
            record.partner.partner_code,
            record.period,
            record.flow.flow_code,
            record.commodity.commodity_code,
            record.classification_code,
            record.edition,
            record.customs_code,
            record.mot_code,
            (
                record.partner2.partner_code
                if record.partner2 is not None
                else 0
            ),
        )

    # ----- Field-level helpers --------------------------------------------

    @staticmethod
    def _coerce_str(raw: Mapping[str, Any], key: str) -> str:
        """Return the value at `key` as a non-empty str.

        Raises `ValueError` on missing / empty values.
        Raises `TypeError` on non-str values.
        """
        if key not in raw or raw[key] is None or raw[key] == "":
            raise ValueError(f"missing required field {key!r}")
        value = raw[key]
        if not isinstance(value, str):
            # Upstream may send ints as strings; coerce.
            value = str(value)
        if not value.strip():
            raise ValueError(f"empty field {key!r}")
        return value

    @staticmethod
    def _optional_str(raw: Mapping[str, Any], key: str) -> str | None:
        """Return the value at `key` as a str, or `None`."""
        if key not in raw or raw[key] is None or raw[key] == "":
            return None
        value = raw[key]
        return str(value)

    @staticmethod
    def _coerce_int(
        raw: Mapping[str, Any], key: str, *, default: int | None = None
    ) -> int:
        """Return the value at `key` as an int.

        When `default` is supplied, returns the default
        for missing/None fields. Otherwise raises.
        """
        if key not in raw or raw[key] is None:
            if default is not None:
                return default
            raise ValueError(f"missing required field {key!r}")
        value = raw[key]
        if isinstance(value, bool):
            raise TypeError(f"bool is not a valid int for {key!r}")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError(f"non-finite float for {key!r}: {value!r}")
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError(
                    f"cannot parse int from {key!r}={value!r}"
                ) from exc
        raise TypeError(
            f"cannot coerce {type(value).__name__} to int for {key!r}"
        )

    @staticmethod
    def _optional_int(raw: Mapping[str, Any], key: str) -> int | None:
        """Return the value at `key` as an int, or `None`."""
        if key not in raw or raw[key] is None:
            return None
        value = raw[key]
        if isinstance(value, bool):
            raise TypeError(f"bool is not a valid int for {key!r}")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError(f"non-finite float for {key!r}: {value!r}")
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError(
                    f"cannot parse int from {key!r}={value!r}"
                ) from exc
        raise TypeError(
            f"cannot coerce {type(value).__name__} to int for {key!r}"
        )

    @staticmethod
    def _coerce_decimal(
        raw: Mapping[str, Any], key: str
    ) -> Decimal:
        """Return the value at `key` as a `Decimal`.

        Per ADR-0027, monetary / quantity values use
        `Decimal(str(value))` to preserve exact precision.
        """
        if key not in raw or raw[key] is None:
            raise ValueError(f"missing required field {key!r}")
        value = raw[key]
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(
                f"cannot parse decimal from {key!r}={value!r}"
            ) from exc

    @staticmethod
    def _optional_decimal(
        raw: Mapping[str, Any], key: str
    ) -> Decimal | None:
        """Return the value at `key` as a `Decimal`, or `None`."""
        if key not in raw or raw[key] is None:
            return None
        value = raw[key]
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(
                f"cannot parse decimal from {key!r}={value!r}"
            ) from exc

    @staticmethod
    def _optional_bool(
        raw: Mapping[str, Any], key: str
    ) -> bool | None:
        """Return the value at `key` as a bool, or `None`.

        Accepts JSON booleans (Python `bool`), as well
        as the strings "true" / "false" / "True" /
        "False" (case-insensitive). Returns `None` for
        missing / null values.
        """
        if key not in raw or raw[key] is None:
            return None
        value = raw[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
        raise TypeError(
            f"cannot coerce {type(value).__name__} to bool for {key!r}"
        )

    @staticmethod
    def _build_provenance(raw: Mapping[str, Any]) -> dict[str, Any]:
        """Build an opaque provenance payload for the record.

        Captures fields not modelled in the canonical
        entity (e.g. `aggrLevel`, `isLeaf`) so consumers
        can inspect them via `TradeRecord.provenance`
        without breaking the canonical schema.
        """
        KNOWN = {
            "typeCode",
            "freqCode",
            "refPeriodId",
            "refYear",
            "refMonth",
            "period",
            "reporterCode",
            "reporterISO",
            "reporterDesc",
            "flowCode",
            "flowDesc",
            "partnerCode",
            "partnerISO",
            "partnerDesc",
            "partner2Code",
            "partner2ISO",
            "partner2Desc",
            "classificationCode",
            "classificationSearchCode",
            "isOriginalClassification",
            "cmdCode",
            "cmdDesc",
            "customsCode",
            "customsDesc",
            "mosCode",
            "motCode",
            "motDesc",
            "qtyUnitCode",
            "qtyUnitAbbr",
            "qty",
            "isQtyEstimated",
            "altQtyUnitCode",
            "altQtyUnitAbbr",
            "altQty",
            "isAltQtyEstimated",
            "netWgt",
            "isNetWgtEstimated",
            "grossWgt",
            "isGrossWgtEstimated",
            "cifvalue",
            "fobvalue",
            "primaryValue",
            "legacyEstimationFlag",
            "isReported",
            "isAggregate",
            "aggrLevel",
            "isLeaf",
        }
        return {k: v for k, v in raw.items() if k not in KNOWN}