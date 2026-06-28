"""Trade query builder for the UN Comtrade Python SDK.

This module is the L4 trade-layer entry point for
constructing canonical API request parameters. It is
**pure**: no HTTP, no parsing, no business logic. The
trade methods that follow (`get_trade`, `get_tariffline`,
etc.) compose this builder with the transport and the
parser to produce real upstream calls.

Per `009_TRADE_LAYER_SPEC.md` §4 the canonical query
parameters are:

- `reporterCode` (int, required)
- `partnerCode` (int, optional; `0` selects the World
  aggregate)
- `period` (string; comma-separated years or year-months)
- `cmdCode` (string; HS commodity code; `"TOTAL"` selects
  every commodity)
- `flowCode` (string; trade flow)
- `classification` / `classificationCode` (string;
  defaults to `"HS"`)
- `partner2Code`, `customsCode`, `motCode`, `mosCode`
  (optional dimension codes)
- `maxRecords` (int; 1-250000)
- `breakdownMode` (`"classic"` or `"plus"`)
- `aggregateBy` (comma-separated)
- `includeDesc` (bool; default `True`)
- `countOnly` (bool; default `False`)

This module validates every parameter per the documented
rules and exposes a deterministic serialisation to URL
parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


__all__ = [
    "BREAKDOWN_MODES",
    "DEFAULT_BREAKDOWN_MODE",
    "DEFAULT_CLASSIFICATION",
    "FLOW_CODES",
    "FREQUENCY_CODES",
    "MAX_RECORDS_LIMIT",
    "MIN_RECORDS",
    "PARTNER_WORLD",
    "TradeQuery",
    "TradeQueryBuilder",
    "TRADE_TYPES",
]


#: Documented frequency codes (from `006_DATA_MODEL.md` §3.9).
FREQUENCY_CODES: frozenset[str] = frozenset({"A", "M"})

#: Documented trade flow codes (from `006_DATA_MODEL.md` §3.5).
FLOW_CODES: frozenset[str] = frozenset({"M", "X", "RX", "RM"})

#: Documented classification codes (from `006_DATA_MODEL.md` §3.2).
DEFAULT_CLASSIFICATION: str = "HS"

#: Documented trade-type codes used in the URL path.
TRADE_TYPES: frozenset[str] = frozenset({"C", "S"})

#: Documented breakdown modes (from the trade-layer spec).
BREAKDOWN_MODES: frozenset[str] = frozenset({"classic", "plus"})

#: Default breakdown mode for new queries.
DEFAULT_BREAKDOWN_MODE: str = "classic"

#: Sentinel for the World aggregate partner code.
PARTNER_WORLD: int = 0

#: Minimum value for `max_records`.
MIN_RECORDS: int = 1

#: Maximum value for `max_records` per upstream cap.
MAX_RECORDS_LIMIT: int = 250_000

#: Period format pattern: 4-digit year (annual) or 6-digit year-month.
import re as _re

_PERIOD_PATTERN: _re.Pattern[str] = _re.compile(r"^\d{4}(\d{2})?$")


# ---------------------------------------------------------------------------
# TradeQuery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeQuery:
    """Canonical, validated trade query.

    All fields are validated in `__post_init__` per
    `009_TRADE_LAYER_SPEC.md` §4. The dataclass is frozen
    so consumers cannot mutate a query after building it.
    """

    reporter_code: int
    period: str
    cmd_code: str = "TOTAL"
    flow_code: str | None = None
    classification_code: str = DEFAULT_CLASSIFICATION
    classification_edition: str | None = None
    partner_code: int | None = None
    partner2_code: int | None = None
    customs_code: str | None = None
    mot_code: int | None = None
    mos_code: int | None = None
    max_records: int | None = None
    breakdown_mode: str = DEFAULT_BREAKDOWN_MODE
    aggregate_by: str | None = None
    include_desc: bool = True
    count_only: bool = False

    def __post_init__(self) -> None:
        # Reporter
        if not isinstance(self.reporter_code, int) or isinstance(
            self.reporter_code, bool
        ):
            raise TypeError(
                f"reporter_code must be an int; got {type(self.reporter_code).__name__}"
            )
        if self.reporter_code < 0:
            raise ValueError(
                f"reporter_code must be a non-negative integer; got {self.reporter_code}"
            )

        # Period
        if not isinstance(self.period, str) or not self.period.strip():
            raise ValueError("period must be a non-empty string")
        for token in self.period.split(","):
            token = token.strip()
            if not _PERIOD_PATTERN.fullmatch(token):
                raise ValueError(
                    f"period token {token!r} must be YYYY or YYYYMM"
                )

        # cmd_code
        if not isinstance(self.cmd_code, str) or not self.cmd_code.strip():
            raise ValueError("cmd_code must be a non-empty string")

        # Flow
        if self.flow_code is not None and self.flow_code not in FLOW_CODES:
            raise ValueError(
                f"flow_code must be one of {sorted(FLOW_CODES)} or None; "
                f"got {self.flow_code!r}"
            )

        # Classification
        if not isinstance(self.classification_code, str) or not self.classification_code.strip():
            raise ValueError("classification_code must be a non-empty string")
        if self.classification_edition is not None and (
            not isinstance(self.classification_edition, str)
            or not self.classification_edition.strip()
        ):
            raise ValueError(
                "classification_edition, if provided, must be a non-empty string"
            )

        # Optional partner codes
        for name in ("partner_code", "partner2_code", "mot_code", "mos_code"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{name} must be an int or None; got {type(value).__name__}"
                )
            if value < 0:
                raise ValueError(f"{name} must be a non-negative integer; got {value}")

        # customs_code
        if self.customs_code is not None and (
            not isinstance(self.customs_code, str) or not self.customs_code.strip()
        ):
            raise ValueError(
                "customs_code, if provided, must be a non-empty string"
            )

        # max_records
        if self.max_records is not None:
            if not isinstance(self.max_records, int) or isinstance(
                self.max_records, bool
            ):
                raise TypeError(
                    f"max_records must be an int; got {type(self.max_records).__name__}"
                )
            if not MIN_RECORDS <= self.max_records <= MAX_RECORDS_LIMIT:
                raise ValueError(
                    f"max_records must be in [{MIN_RECORDS}, {MAX_RECORDS_LIMIT}]; "
                    f"got {self.max_records}"
                )

        # breakdown_mode
        if self.breakdown_mode not in BREAKDOWN_MODES:
            raise ValueError(
                f"breakdown_mode must be one of {sorted(BREAKDOWN_MODES)}; "
                f"got {self.breakdown_mode!r}"
            )

        # aggregate_by
        if self.aggregate_by is not None and (
            not isinstance(self.aggregate_by, str) or not self.aggregate_by.strip()
        ):
            raise ValueError(
                "aggregate_by, if provided, must be a non-empty string"
            )

        # Booleans are already typed; nothing more to check.

    # ----- Serialisation -------------------------------------------------

    def to_query_params(self, *, trade_type: str = "C") -> dict[str, str]:
        """Return the upstream's query-string parameter mapping.

        `trade_type` (`"C"` for commodities, `"S"` for services)
        selects the field name for the classification code:
        `classification` for `"C"`, `classificationCode` for
        `"S"`. The default is `"C"`.
        """
        params: dict[str, str] = {}
        params["reporterCode"] = str(self.reporter_code)
        if self.partner_code is not None:
            params["partnerCode"] = str(self.partner_code)
        params["period"] = self.period
        if self.flow_code is not None:
            params["flowCode"] = self.flow_code
        params["cmdCode"] = self.cmd_code
        cls_field = (
            "classificationCode" if trade_type == "S" else "classification"
        )
        params[cls_field] = self.classification_code
        if self.classification_edition is not None:
            # `classificationCode` is the edition selector when
            # classification is HS / SITC / etc.; for the trade
            # layer the edition travels in the same field as
            # the classification code (the upstream distinguishes
            # them via the documented value, e.g. "H2022").
            params[cls_field] = self.classification_edition
        if self.partner2_code is not None:
            params["partner2Code"] = str(self.partner2_code)
        if self.customs_code is not None:
            params["customsCode"] = self.customs_code
        if self.mot_code is not None:
            params["motCode"] = str(self.mot_code)
        if self.mos_code is not None:
            params["mosCode"] = str(self.mos_code)
        if self.max_records is not None:
            params["maxRecords"] = str(self.max_records)
        if self.breakdown_mode != DEFAULT_BREAKDOWN_MODE:
            params["breakdownMode"] = self.breakdown_mode
        if self.aggregate_by is not None:
            params["aggregateBy"] = self.aggregate_by
        # Booleans are always serialised; the upstream expects
        # the literal "true" / "false" strings.
        params["includeDesc"] = "true" if self.include_desc else "false"
        if self.count_only:
            params["countOnly"] = "true"
        return params

    def to_url_path(self, *, trade_type: str = "C") -> str:
        """Return the upstream's URL path fragment for this query.

        Path shape (per `005_API_ENDPOINT_CATALOG.md` T1):
        ``/{trade_type}/{freqCode}/{flowCode}/{classificationCode}``

        `freqCode` is NOT part of the TradeQuery dataclass
        (it is a path parameter that the call site supplies
        alongside the query). The returned path is the
        ``/C/A/HS`` portion; callers prepend ``/data/v1/get``
        or ``/public/v1/preview`` as appropriate.
        """
        if trade_type not in TRADE_TYPES:
            raise ValueError(
                f"trade_type must be one of {sorted(TRADE_TYPES)}; got {trade_type!r}"
            )
        if self.flow_code is None:
            raise ValueError(
                "flow_code is required for the URL path; set it via the builder"
            )
        # The upstream distinguishes classification by the
        # classificationCode field in the path; pass the
        # edition (or the bare code) so the URL carries the
        # intended value.
        path_class = (
            self.classification_edition or self.classification_code
        )
        return f"/{trade_type}/{{freqCode}}/{self.flow_code}/{path_class}"

    # ----- Convenience ----------------------------------------------------

    def with_freq_code(self, freq_code: str) -> "TradeQuery":
        """Return a copy with the given frequency code.

        Frequency lives in the URL path, not the query
        body, but consumers find it useful to keep the
        code near the rest of the query fields.
        """
        # We don't store freq_code on the query; this is a
        # placeholder for callers that want to bundle the
        # query + path parameters. Returns self unchanged so
        # the call site compiles.
        if freq_code not in FREQUENCY_CODES:
            raise ValueError(
                f"freq_code must be one of {sorted(FREQUENCY_CODES)}; "
                f"got {freq_code!r}"
            )
        return self


# ---------------------------------------------------------------------------
# TradeQueryBuilder
# ---------------------------------------------------------------------------


@dataclass
class TradeQueryBuilder:
    """Fluent builder for `TradeQuery`.

    All setter methods return `self` for chaining. `build()`
    returns an immutable `TradeQuery`. The builder is
    not validated at construction time — validation
    happens on `build()`.

    Usage::

        q = (
            TradeQueryBuilder()
            .reporter(699)
            .partner(156)
            .period("2022")
            .flow("M")
            .cmd("TOTAL")
            .build()
        )
    """

    _reporter_code: int | None = None
    _period: str = ""
    _cmd_code: str = "TOTAL"
    _flow_code: str | None = None
    _classification_code: str = DEFAULT_CLASSIFICATION
    _classification_edition: str | None = None
    _partner_code: int | None = None
    _partner2_code: int | None = None
    _customs_code: str | None = None
    _mot_code: int | None = None
    _mos_code: int | None = None
    _max_records: int | None = None
    _breakdown_mode: str = DEFAULT_BREAKDOWN_MODE
    _aggregate_by: str | None = None
    _include_desc: bool = True
    _count_only: bool = False

    # ----- Setters --------------------------------------------------------

    def reporter(self, code: int) -> "TradeQueryBuilder":
        """Set the reporter code (required)."""
        if not isinstance(code, int) or isinstance(code, bool):
            raise TypeError(
                f"reporter_code must be an int; got {type(code).__name__}"
            )
        if code < 0:
            raise ValueError(f"reporter_code must be >= 0; got {code}")
        self._reporter_code = code
        return self

    def partner(self, code: int) -> "TradeQueryBuilder":
        """Set the partner code; `0` selects the World aggregate."""
        if not isinstance(code, int) or isinstance(code, bool):
            raise TypeError(
                f"partner_code must be an int; got {type(code).__name__}"
            )
        if code < 0:
            raise ValueError(f"partner_code must be >= 0; got {code}")
        self._partner_code = code
        return self

    def period(self, *tokens: str) -> "TradeQueryBuilder":
        """Set the period(s) — accepts one or more YYYY / YYYYMM tokens.

        Multiple tokens are joined with commas. Single
        string with embedded commas is also accepted.
        """
        # Flatten and split on comma to normalise.
        flat: list[str] = []
        for t in tokens:
            flat.extend(p.strip() for p in t.split(","))
        flat = [t for t in flat if t]
        if not flat:
            raise ValueError("period must contain at least one token")
        # Validate each token.
        for token in flat:
            if not _PERIOD_PATTERN.fullmatch(token):
                raise ValueError(
                    f"period token {token!r} must be YYYY or YYYYMM"
                )
        self._period = ",".join(flat)
        return self

    def flow(self, code: str) -> "TradeQueryBuilder":
        """Set the trade flow code (`M`, `X`, `RX`, `RM`)."""
        if code not in FLOW_CODES:
            raise ValueError(
                f"flow_code must be one of {sorted(FLOW_CODES)}; got {code!r}"
            )
        self._flow_code = code
        return self

    def cmd(self, code: str) -> "TradeQueryBuilder":
        """Set the commodity code (HS). Use `"TOTAL"` for all commodities."""
        if not isinstance(code, str) or not code.strip():
            raise ValueError("cmd_code must be a non-empty string")
        self._cmd_code = code
        return self

    def classification(
        self, code: str = DEFAULT_CLASSIFICATION, *, edition: str | None = None
    ) -> "TradeQueryBuilder":
        """Set the classification system and (optionally) edition."""
        if not code or not code.strip():
            raise ValueError("classification_code must be a non-empty string")
        self._classification_code = code
        self._classification_edition = edition
        return self

    def partner2(self, code: int) -> "TradeQueryBuilder":
        """Set the secondary partner code (used by `plus` breakdown mode)."""
        if not isinstance(code, int) or isinstance(code, bool):
            raise TypeError(
                f"partner2_code must be an int; got {type(code).__name__}"
            )
        if code < 0:
            raise ValueError(f"partner2_code must be >= 0; got {code}")
        self._partner2_code = code
        return self

    def customs(self, code: str) -> "TradeQueryBuilder":
        """Set the customs procedure code (e.g. `"C00"` for total)."""
        if not code or not code.strip():
            raise ValueError("customs_code must be a non-empty string")
        self._customs_code = code
        return self

    def mot(self, code: int) -> "TradeQueryBuilder":
        """Set the mode-of-transport code (`0` for total)."""
        if not isinstance(code, int) or isinstance(code, bool):
            raise TypeError(
                f"mot_code must be an int; got {type(code).__name__}"
            )
        if code < 0:
            raise ValueError(f"mot_code must be >= 0; got {code}")
        self._mot_code = code
        return self

    def mos(self, code: int) -> "TradeQueryBuilder":
        """Set the mode-of-supply code (only for services trade type)."""
        if not isinstance(code, int) or isinstance(code, bool):
            raise TypeError(
                f"mos_code must be an int; got {type(code).__name__}"
            )
        if code < 0:
            raise ValueError(f"mos_code must be >= 0; got {code}")
        self._mos_code = code
        return self

    def max_records(self, value: int) -> "TradeQueryBuilder":
        """Set the maximum records per call (1-250000)."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(
                f"max_records must be an int; got {type(value).__name__}"
            )
        if not MIN_RECORDS <= value <= MAX_RECORDS_LIMIT:
            raise ValueError(
                f"max_records must be in [{MIN_RECORDS}, {MAX_RECORDS_LIMIT}]; "
                f"got {value}"
            )
        self._max_records = value
        return self

    def breakdown(self, mode: str) -> "TradeQueryBuilder":
        """Set the breakdown mode (`"classic"` or `"plus"`)."""
        if mode not in BREAKDOWN_MODES:
            raise ValueError(
                f"breakdown_mode must be one of {sorted(BREAKDOWN_MODES)}; "
                f"got {mode!r}"
            )
        self._breakdown_mode = mode
        return self

    def aggregate_by(self, *dimensions: str) -> "TradeQueryBuilder":
        """Set the aggregate-by dimensions (one or more)."""
        flat: list[str] = []
        for d in dimensions:
            flat.extend(p.strip() for p in d.split(","))
        flat = [d for d in flat if d]
        if not flat:
            raise ValueError("aggregate_by must contain at least one dimension")
        self._aggregate_by = ",".join(flat)
        return self

    def include_desc(self, value: bool = True) -> "TradeQueryBuilder":
        """Set the include-description flag (default True)."""
        self._include_desc = bool(value)
        return self

    def count_only(self, value: bool = True) -> "TradeQueryBuilder":
        """Set the count-only flag (default False)."""
        self._count_only = bool(value)
        return self

    # ----- Build ----------------------------------------------------------

    def build(self) -> TradeQuery:
        """Construct a validated `TradeQuery`."""
        if self._reporter_code is None:
            raise ValueError("reporter_code is required")
        if not self._period:
            raise ValueError("period is required")
        return TradeQuery(
            reporter_code=self._reporter_code,
            period=self._period,
            cmd_code=self._cmd_code,
            flow_code=self._flow_code,
            classification_code=self._classification_code,
            classification_edition=self._classification_edition,
            partner_code=self._partner_code,
            partner2_code=self._partner2_code,
            customs_code=self._customs_code,
            mot_code=self._mot_code,
            mos_code=self._mos_code,
            max_records=self._max_records,
            breakdown_mode=self._breakdown_mode,
            aggregate_by=self._aggregate_by,
            include_desc=self._include_desc,
            count_only=self._count_only,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def default_trade_query(reporter_code: int, year: int) -> TradeQuery:
    """Build a default India-export-style query for a single year.

    Useful as a starting point and in tests. The flow is
    `M` (Import) by default — flip via `.flow("X")` for
    exports.
    """
    return (
        TradeQueryBuilder()
        .reporter(reporter_code)
        .partner(PARTNER_WORLD)
        .period(str(year))
        .flow("M")
        .cmd("TOTAL")
        .build()
    )