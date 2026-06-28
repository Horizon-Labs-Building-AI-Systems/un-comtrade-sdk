"""Transformation layer for the ETL pipeline.

The transformation layer is the **canonicalisation
stage** of the ETL pipeline (per
`011_ETL_SPECIFICATION.md` §2 + §5 + §6). It
consumes the raw records produced by the extract
stage and produces a `CanonicalDataset` that
downstream stages (validate, deduplicate, quality
check, export, store) consume.

Per the P4-003 task scope:

- **Reuses** `un_comtrade.parser.TradeParser` for
  parsing. The transformation layer composes the
  parser rather than re-implementing field mapping,
  camelCase → snake_case conversion, Decimal
  coercion, or record-level validation.
- **No parser duplication** — the parser is the
  single source of truth for "raw upstream dict →
  canonical TradeRecord" conversion.
- **Dataset normalisation** — the layer produces
  a `CanonicalDataset` (a frozen, structured
  container with provenance metadata) rather than
  a bare list of records.
- **Schema validation** — record-level schema
  validation is delegated to the parser (which
  raises `ValueError` / `TypeError` on invalid
  records, caught and counted as skipped). The
  transformation layer adds **dataset-level**
  schema checks (e.g. all records must share the
  same reporter / flow / commodity dimension).
- **Duplicate removal** — the parser applies
  first-wins deduplication within a single call.
  The transformation layer applies a
  **latest-wins** policy by `ref_period_id` per
  the ETL specification §7.3, so that duplicate
  records with different revision markers are
  resolved to the most recent revision. Latest-
  wins is idempotent for already-deduplicated
  inputs (no-op).
- **Decimal preservation** — `Decimal` monetary
  and quantity values survive the transformation
  unchanged (per ADR-0027); no coercion away from
  `Decimal` is applied.
- **Canonical dataset output** — the layer emits
  a `CanonicalDataset`, the canonical output
  shape of the transformation stage.

Two transformers are exposed:

1. **`TradeTransformer`** — converts raw trade
   records (camelCase dicts) into a
   `CanonicalDataset` of canonical `TradeRecord`
   instances. Implements the `TransformStage`
   protocol from `un_comtrade.etl`.
2. **`MetadataTransformer`** — converts raw
   metadata reference records into a
   `CanonicalDataset` of canonical metadata
   models (no parsing required; the upstream
   already returns the canonical entities).

Both compose cleanly into an `ETLPipeline`
downstream of the extract layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Mapping,
    Sequence,
)

from .etl import PipelineContext, StageKind, TransformStage
from .logging import get_logger
from .models import TradeRecord


if TYPE_CHECKING:
    from .parser import TradeParser


__all__ = [
    "CanonicalDataset",
    "ConflictResolution",
    "MetadataTransformer",
    "TradeTransformer",
]


_logger = get_logger("lifecycle")


#: Current schema version of the canonical dataset.
SCHEMA_VERSION: str = "1.0.0"


# ---------------------------------------------------------------------------
# ConflictResolution
# ---------------------------------------------------------------------------


class ConflictResolution(str, Enum):
    """Conflict-resolution policy for duplicate records.

    The ETL pipeline spec §7.3 declares "latest wins" as
    the documented default. The transformation layer
    honours this; `FIRST_WINS` is exposed for callers
    that want to opt out.
    """

    LATEST_WINS = "latest_wins"
    FIRST_WINS = "first_wins"


# ---------------------------------------------------------------------------
# CanonicalDataset
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanonicalDataset:
    """A canonical, normalised, deduplicated dataset.

    The output of the transformation stage. Carries
    the canonical records plus provenance
    metadata (extraction timestamp, parser used,
    skipped + duplicate counts, schema version).

    Parameters
    ----------
    name
        Pipeline name (carried over from
        `PipelineContext.pipeline_name`).
    records
        Tuple of canonical records. For the trade
        pipeline this is `tuple[TradeRecord, ...]`;
        for the metadata pipeline this is a tuple of
        canonical metadata models.
    schema_version
        The schema version of the canonical entity
        (default `"1.0.0"`). Bumped when the record
        shape changes in a non-backward-compatible
        way.
    extracted_at
        UTC timestamp the dataset was extracted.
    parser_name
        Name of the parser used (e.g. `"TradeParser"`).
    skipped
        Number of records the parser skipped
        (validation failures + duplicates within a
        single parse call).
    duplicates_removed
        Number of records removed by the
        transformation layer's cross-call deduplication
        (always 0 for first-wins; >0 when latest-wins
        resolves cross-call duplicates).
    source_count
        Number of raw records the transformer
        received as input.
    metadata
        Free-form metadata map.
    """

    name: str
    records: tuple[Any, ...]
    schema_version: str = SCHEMA_VERSION
    extracted_at: datetime | None = None
    parser_name: str = ""
    skipped: int = 0
    duplicates_removed: int = 0
    source_count: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        """Number of canonical records in the dataset."""
        return len(self.records)

    @property
    def is_empty(self) -> bool:
        """True when the dataset has no records."""
        return len(self.records) == 0

    @property
    def schema(self) -> str:
        """Alias for `schema_version`."""
        return self.schema_version


# ---------------------------------------------------------------------------
# TradeTransformer
# ---------------------------------------------------------------------------


class TradeTransformer:
    """Transform raw trade records into a `CanonicalDataset`.

    Pipeline (per `011_ETL_SPECIFICATION.md` §2 + §5):

    1. **Parse** — delegate to `TradeParser.parse_records`
       (camelCase → snake_case, Decimal coercion,
       record-level validation, first-wins dedup
       within the call).
    2. **Schema validate** — apply dataset-level schema
       checks (all records share the same reporter /
       flow / classification; ref_period_ids are
       monotonic). Record-level failures are already
       counted by the parser as `skipped`; dataset-
       level warnings are appended to the
       `PipelineContext`.
    3. **Deduplicate** — apply latest-wins by
       `(composite_key, ref_period_id)` per
       §7.3. Idempotent for already-deduplicated
       inputs (the parser's first-wins dedup
       collapses same-call duplicates; the
       transformer collapses cross-call duplicates
       that survived).
    4. **Decimal preservation** — `Decimal` values
       survive unchanged (per ADR-0027). No
       coercion away from `Decimal`.
    5. **Wrap** — return a `CanonicalDataset` with
       provenance metadata.

    Implements the `TransformStage` protocol from
    `un_comtrade.etl` (`name` + `kind=StageKind.TRANSFORM`
    + callable).

    Usage::

        transformer = TradeTransformer()
        dataset = transformer(source=raw_records, context=ctx)

        # Or with a custom parser:
        from un_comtrade.parser import TradeParser
        transformer = TradeTransformer(parser=TradeParser(log_skipped=False))

        # Or with a different conflict resolution:
        transformer = TradeTransformer(
            conflict_resolution=ConflictResolution.FIRST_WINS,
        )
    """

    def __init__(
        self,
        parser: "TradeParser | None" = None,
        *,
        conflict_resolution: str = ConflictResolution.LATEST_WINS,
        schema_version: str = SCHEMA_VERSION,
    ) -> None:
        # Lazy import to avoid circular dependency
        # (transform.py is imported before parser.py
        # would be initialised in some test scenarios).
        from .parser import TradeParser

        if conflict_resolution not in (
            ConflictResolution.LATEST_WINS,
            ConflictResolution.FIRST_WINS,
        ):
            raise ValueError(
                f"conflict_resolution must be one of "
                f"{[ConflictResolution.LATEST_WINS, ConflictResolution.FIRST_WINS]}; "
                f"got {conflict_resolution!r}"
            )
        self._parser = parser if parser is not None else TradeParser()
        self._conflict_resolution = conflict_resolution
        self._schema_version = schema_version

    @property
    def parser(self) -> "TradeParser":
        """The underlying `TradeParser` instance."""
        return self._parser

    @property
    def conflict_resolution(self) -> str:
        """The conflict-resolution policy."""
        return self._conflict_resolution

    @property
    def schema_version(self) -> str:
        """The schema version stamped on the produced dataset."""
        return self._schema_version

    @property
    def name(self) -> str:
        """Stage identifier (`transform_trade`)."""
        return "transform_trade"

    @property
    def kind(self) -> StageKind:
        """Always `StageKind.TRANSFORM`."""
        return StageKind.TRANSFORM

    def __call__(
        self,
        source: Any,
        context: PipelineContext,
    ) -> CanonicalDataset:
        """Transform a list of raw records into a
        `CanonicalDataset`.

        Parameters
        ----------
        source
            List of raw upstream records (camelCase
            dicts) OR a list of canonical
            `TradeRecord` instances OR a
            `CanonicalDataset` (in which case the
            transformer's pipeline is applied to its
            records — useful for re-running the
            pipeline through multiple transformers).
        context
            The shared `PipelineContext`. The
            transformer records warnings (dataset-
            level schema violations, latest-wins
            dedup summary) and updates
            `records_out` on the context.

        Returns
        -------
        CanonicalDataset
            The canonical, deduplicated dataset.
        """
        raw_records, parent_dataset = self._extract_raw_records(source)

        # ----- Step 1: Parse via TradeParser (only for raw
        # dicts; TradeRecord instances are already canonical).
        if raw_records and all(
            isinstance(r, TradeRecord) for r in raw_records
        ):
            records = list(raw_records)
            skipped = 0
            parser_name = "pre-canonical"
        else:
            parse_result = self._parser.parse_records(raw_records)
            records = parse_result.records
            skipped = parse_result.skipped
            parser_name = type(self._parser).__name__

        # ----- Step 2: Dataset-level schema validation
        dataset_warnings = self._validate_dataset_schema(records)
        for warning in dataset_warnings:
            context.warn(warning)

        # ----- Step 3: Latest-wins dedup (or pass-through)
        if self._conflict_resolution == ConflictResolution.LATEST_WINS:
            deduped, duplicates_removed = self._latest_wins_dedup(records)
        else:
            deduped = records
            duplicates_removed = 0

        # ----- Step 4: Decimal preservation is automatic —
        # Decimal values on TradeRecord survive unchanged.

        # ----- Step 5: Wrap in CanonicalDataset
        dataset = CanonicalDataset(
            name=context.pipeline_name,
            records=tuple(deduped),
            schema_version=self._schema_version,
            extracted_at=datetime.now(timezone.utc),
            parser_name=parser_name,
            skipped=skipped,
            duplicates_removed=duplicates_removed,
            source_count=len(raw_records),
            metadata={
                "conflict_resolution": self._conflict_resolution,
                "parent_dataset_skipped": (
                    parent_dataset.skipped if parent_dataset else 0
                ),
            },
        )

        context.records_out = dataset.count
        _logger.debug(
            "TradeTransformer produced %d canonical records "
            "(%d skipped, %d duplicates removed)",
            dataset.count,
            dataset.skipped,
            dataset.duplicates_removed,
        )
        return dataset

    # ----- Helpers --------------------------------------------------------

    @staticmethod
    def _extract_raw_records(
        source: Any,
    ) -> tuple[list[Any], "CanonicalDataset | None"]:
        """Normalise the input into a list of records.

        - `list[dict]` → returned as-is.
        - `list[TradeRecord]` (or any list of canonical
          models) → returned as-is. The caller decides
          whether to re-parse or pass through.
        - `CanonicalDataset` → returned records are the
          dataset's records (canonical or raw, depending
          on what produced the dataset) and the parent
          dataset is returned alongside for provenance.
        - Anything else → `TypeError`.

        The caller (`__call__`) decides whether to
        invoke the parser based on whether the records
        are already canonical (`TradeRecord` instances)
        or raw (`dict` instances).
        """
        if isinstance(source, CanonicalDataset):
            return list(source.records), source
        if isinstance(source, Mapping):
            return [dict(source)], None
        if isinstance(source, Iterable) and not isinstance(
            source, (str, bytes)
        ):
            records: list[Any] = []
            for item in source:
                if isinstance(item, Mapping):
                    records.append(dict(item))
                else:
                    # Pass through; the parser will
                    # either accept it (canonical model)
                    # or reject with a TypeError
                    # (counted as skipped).
                    records.append(item)
            return records, None
        raise TypeError(
            f"TradeTransformer source must be a list of dicts, "
            f"a list of canonical records, or a "
            f"CanonicalDataset; got {type(source).__name__}"
        )

    def _latest_wins_dedup(
        self,
        records: Sequence[Any],
    ) -> tuple[list[Any], int]:
        """Apply latest-wins deduplication by
        `(composite_key, ref_period_id)`.

        Records sharing a composite key
        (per `TradeParser.composite_key`) are grouped;
        within each group, the record with the
        highest `ref_period_id` is retained. Records
        with `ref_period_id=None` are treated as
        `ref_period_id=0` (lowest priority).

        Returns
        -------
        (kept_records, duplicates_removed)
            The kept records (in encounter order)
            and the number of duplicates removed.

        Notes
        -----
        The `TradeParser` already does first-wins
        deduplication within a single parse call.
        This method is therefore a no-op for the
        typical case of a single extractor feeding
        raw records. It is meaningful when:

        - Records come from MULTIPLE parse calls
          (e.g. a year-by-year download that produced
          overlapping records across calls).
        - Records are canonical `TradeRecord` instances
          fed directly into the transformer (via a
          `CanonicalDataset` source).
        """
        return self.latest_wins(records)

    @staticmethod
    def latest_wins(
        records: Sequence[Any],
    ) -> tuple[list[Any], int]:
        """Apply latest-wins deduplication to a list
        of canonical records.

        Public helper (also reachable via the
        instance method). Useful for cross-call
        deduplication: pass records from multiple
        `parse_records` calls and receive a single
        deduplicated list.

        Records sharing a composite key
        (per `TradeParser.composite_key`) are grouped;
        within each group, the record with the
        highest `ref_period_id` is retained. Records
        with `ref_period_id=None` are treated as
        `ref_period_id=0` (lowest priority).

        Returns
        -------
        (kept_records, duplicates_removed)
            The kept records (in encounter order)
            and the number of duplicates removed.
        """
        from .parser import TradeParser  # local import

        groups: dict[tuple, Any] = {}
        order: list[tuple] = []
        for record in records:
            key = TradeParser.composite_key(record)
            if key not in groups:
                groups[key] = record
                order.append(key)
            else:
                # Compare ref_period_id; keep the higher one.
                current_ref = (
                    getattr(groups[key], "ref_period_id", None) or 0
                )
                new_ref = getattr(record, "ref_period_id", None) or 0
                if new_ref > current_ref:
                    groups[key] = record

        duplicates_removed = len(records) - len(groups)
        if duplicates_removed > 0:
            _logger.debug(
                "TradeTransformer.latest_wins removed %d "
                "duplicate(s)",
                duplicates_removed,
            )
        return [groups[k] for k in order], duplicates_removed

    @staticmethod
    def _validate_dataset_schema(records: Sequence[Any]) -> list[str]:
        """Apply dataset-level schema checks.

        The parser does record-level validation
        (raises ValueError on invalid records).
        This method adds dataset-level checks that
        only make sense across the full record set.

        Returns a list of warning strings (empty if
        the dataset is uniform).
        """
        warnings: list[str] = []
        if not records:
            return warnings

        # ----- Reporter / partner / flow / commodity
        # ----- homogeneity check
        reporters: set[Any] = set()
        flows: set[Any] = set()
        classifications: set[Any] = set()
        editions: set[Any] = set()
        for record in records:
            r = getattr(record, "reporter", None)
            if r is not None and hasattr(r, "reporter_code"):
                reporters.add(r.reporter_code)
            f = getattr(record, "flow", None)
            if f is not None and hasattr(f, "flow_code"):
                flows.add(f.flow_code)
            cls_code = getattr(record, "classification_code", None)
            if cls_code is not None:
                classifications.add(cls_code)
            ed = getattr(record, "edition", None)
            if ed is not None:
                editions.add(ed)

        if len(reporters) > 1:
            warnings.append(
                f"dataset spans {len(reporters)} reporters: "
                f"{sorted(reporters)}"
            )
        if len(flows) > 1:
            warnings.append(
                f"dataset spans {len(flows)} flows: {sorted(flows)}"
            )
        if len(classifications) > 1:
            warnings.append(
                f"dataset spans {len(classifications)} "
                f"classifications: {sorted(classifications)}"
            )
        if len(editions) > 1:
            warnings.append(
                f"dataset spans {len(editions)} editions: "
                f"{sorted(editions)}"
            )

        # ----- ref_period_id monotonicity check (annual only)
        ref_period_ids: list[int] = []
        for record in records:
            ref = getattr(record, "ref_period_id", None)
            if ref is not None:
                ref_period_ids.append(ref)
        if ref_period_ids:
            non_monotonic = sum(
                1
                for a, b in zip(ref_period_ids, ref_period_ids[1:])
                if a > b
            )
            if non_monotonic:
                warnings.append(
                    f"dataset has {non_monotonic} non-monotonic "
                    f"ref_period_id transition(s)"
                )

        return warnings

    def __repr__(self) -> str:
        return (
            f"TradeTransformer(parser={type(self._parser).__name__}, "
            f"conflict_resolution={self._conflict_resolution!r})"
        )


# ---------------------------------------------------------------------------
# MetadataTransformer
# ---------------------------------------------------------------------------


class MetadataTransformer:
    """Transform metadata reference records into a
    `CanonicalDataset`.

    Metadata reference catalogues are already
    returned by `MetadataService` as canonical
    model instances (e.g. `Country`, `Partner`,
    `HSCode`). No field mapping, no Decimal
    coercion, no dedup is required. The
    `MetadataTransformer` is therefore a thin
    wrapper that:

    1. Validates each record is a non-None
       model instance (drops non-conforming values
       and counts them as `skipped`).
    2. Applies a name-based dedup (records with
       the same `(resource, code)` key are
       collapsed to the first-wins value).
    3. Wraps the result in a `CanonicalDataset`.

    Implements the `TransformStage` protocol from
    `un_comtrade.etl`.

    Usage::

        transformer = MetadataTransformer(resource="R01")
        dataset = transformer(source=country_list, context=ctx)
    """

    def __init__(
        self,
        resource: str = "",
        *,
        schema_version: str = SCHEMA_VERSION,
    ) -> None:
        if not isinstance(resource, str):
            raise TypeError(
                f"resource must be a str; got {type(resource).__name__}"
            )
        self._resource = resource
        self._schema_version = schema_version

    @property
    def resource(self) -> str:
        """The metadata resource code (e.g. `"R01"`)."""
        return self._resource

    @property
    def schema_version(self) -> str:
        """The schema version stamped on the produced dataset."""
        return self._schema_version

    @property
    def name(self) -> str:
        """Stage identifier (`transform_metadata`)."""
        return "transform_metadata"

    @property
    def kind(self) -> StageKind:
        """Always `StageKind.TRANSFORM`."""
        return StageKind.TRANSFORM

    def __call__(
        self,
        source: Any,
        context: PipelineContext,
    ) -> CanonicalDataset:
        """Transform a list of metadata models into a
        `CanonicalDataset`.

        Parameters
        ----------
        source
            Iterable of canonical metadata models
            (e.g. `list[Country]`, `list[Partner]`).
        context
            The shared `PipelineContext`. Warnings
            (non-conforming records, dedup) are
            recorded; `records_out` is updated.

        Returns
        -------
        CanonicalDataset
            The canonical, deduplicated dataset.
        """
        raw_records, parent_dataset = TradeTransformer._extract_raw_records(
            source
        )

        # Validate + dedup by (resource, code).
        seen: set[tuple] = set()
        kept: list[Any] = []
        skipped = 0
        for record in raw_records:
            code = self._extract_code(record)
            key = (self._resource, code)
            if key in seen:
                continue
            if record is None or (
                not isinstance(record, Mapping)
                and not hasattr(record, "to_dict")
            ):
                skipped += 1
                context.warn(
                    f"MetadataTransformer skipped non-conforming "
                    f"record at resource={self._resource!r}"
                )
                continue
            seen.add(key)
            kept.append(record)

        duplicates_removed = len(raw_records) - len(kept) - skipped

        dataset = CanonicalDataset(
            name=context.pipeline_name,
            records=tuple(kept),
            schema_version=self._schema_version,
            extracted_at=datetime.now(timezone.utc),
            parser_name="MetadataTransformer",
            skipped=skipped,
            duplicates_removed=duplicates_removed,
            source_count=len(raw_records),
            metadata={
                "resource": self._resource,
                "parent_dataset_skipped": (
                    parent_dataset.skipped if parent_dataset else 0
                ),
            },
        )

        context.records_out = dataset.count
        _logger.debug(
            "MetadataTransformer produced %d canonical records "
            "for resource %s (%d skipped, %d duplicates removed)",
            dataset.count,
            self._resource,
            dataset.skipped,
            dataset.duplicates_removed,
        )
        return dataset

    @staticmethod
    def _extract_code(record: Any) -> Any:
        """Return a stable code from a metadata record.

        Tries, in order:
        - `record.id` (most catalogue entries).
        - `record.code`.
        - `record.iso3` / `record.iso_alpha3` (countries).
        - `record.commodity_code` (HS codes).
        - The dict's `id` / `code` key.
        - `None` (records without a code are still
          accepted; their key is `(resource, None)`).
        """
        for attr in ("id", "code", "iso3", "iso_alpha3", "commodity_code"):
            if hasattr(record, attr):
                value = getattr(record, attr, None)
                if value is not None:
                    return value
        if isinstance(record, Mapping):
            for key in ("id", "code", "iso3", "iso_alpha3", "commodity_code"):
                if key in record:
                    return record[key]
        return None

    def __repr__(self) -> str:
        return f"MetadataTransformer(resource={self._resource!r})"