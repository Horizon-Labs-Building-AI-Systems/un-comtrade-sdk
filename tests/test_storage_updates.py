"""Tests for the incremental update orchestrator (P5-006).

Per the P5-006 task scope, this module covers:

- `Merge` — replace existing rows whose composite
  key collides with an incoming row.
- `Replace` — drop existing rows whose composite
  key appears in the incoming batch, then insert
  the incoming batch.
- `Append` — add new rows without touching
  existing data.
- `Duplicate detection` — identify duplicates
  within a single incoming batch via
  `find_duplicates(...)`.
- `Schema compatibility` — verify the incoming
  `CanonicalDataset` matches the existing dataset's
  metadata before applying the update.

Coverage:

- `TestUpdateMode` — enum sanity.
- `TestDuplicatePolicy` — enum sanity.
- `TestUpdateResult` — frozen dataclass.
- `TestFindDuplicates` — group-by-composite-key
  detection.
- `TestDeduplicate` — first-wins / last-wins.
- `TestSchemaCompatibility` — schema_version +
  parser_name checks.
- `TestDatasetUpdaterAppend` — APPEND semantics
  across CSV / JSON / Parquet / DuckDB.
- `TestDatasetUpdaterMerge` — MERGE semantics
  across all four engines; verify collision
  replacement.
- `TestDatasetUpdaterReplace` — REPLACE semantics
  (same as MERGE for the current engines but
  expressed as delete-then-insert).
- `TestDuplicateDetectionInUpdate` — input batch
  with duplicates gets deduped before the update
  is applied.
- `TestSchemaCheckDuringUpdate` —
  `check_schema=False` skips verification; default
  raises `SchemaIncompatibleError`.
- `TestInvalidInputs` — bad source / bad mode /
  bad policy rejected.
- `TestUpdaterRepr` — `__repr__` roundtrip.
"""

from __future__ import annotations

import csv as _csv_stdlib
import json as _json_stdlib
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq
import pytest

from un_comtrade.parser import TradeParser
from un_comtrade.storage import (
    CSVWriter,
    DatasetMetadata,
    DatasetUpdater,
    DuckDBWriter,
    DuplicatePolicy,
    JSONWriter,
    ParquetWriter,
    PartitionStrategy,
    SchemaIncompatibleError,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageRegistry,
    UpdateMode,
    UpdateResult,
    deduplicate,
    find_duplicates,
    verify_schema_compatibility,
)
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baseline_raw(**overrides) -> dict[str, Any]:
    """Baseline raw upstream trade record.

    Vary `fobvalue` / `primaryValue` via the
    `value` kwarg to control the trade value
    per record."""
    raw: dict[str, Any] = {
        "typeCode": "C",
        "freqCode": "A",
        "classificationCode": "H6",
        "classificationSearchCode": "HS",
        "isOriginalClassification": True,
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,
        "period": "2022",
        "reporterCode": 699,
        "reporterISO": "IND",
        "reporterDesc": "India",
        "flowCode": "X",
        "flowDesc": "Export",
        "partnerCode": 0,
        "partnerISO": "W00",
        "partnerDesc": "World",
        "partner2Code": 0,
        "partner2ISO": "W00",
        "partner2Desc": "World",
        "cmdCode": "TOTAL",
        "cmdDesc": "All Commodities",
        "customsCode": "C00",
        "customsDesc": "TOTAL CPC",
        "mosCode": "0",
        "motCode": 0,
        "motDesc": "TOTAL MOT",
        "qtyUnitCode": -1,
        "qtyUnitAbbr": "N/A",
        "qty": 0,
        "isQtyEstimated": False,
        "altQtyUnitCode": -1,
        "altQtyUnitAbbr": "N/A",
        "altQty": 0,
        "isAltQtyEstimated": False,
        "netWgt": 0,
        "isNetWgtEstimated": True,
        "grossWgt": 0,
        "isGrossWgtEstimated": False,
        "cifvalue": None,
        "fobvalue": 100.0,
        "primaryValue": 100.0,
        "legacyEstimationFlag": 0,
        "isReported": False,
        "isAggregate": True,
    }
    raw.update(overrides)
    return raw


def _record(
    *,
    reporter: int = 699,
    partner: int = 0,
    period: str = "2022",
    period_id: int = 20220101,
    flow: str = "X",
    classification: str = "H6",
    commodity: str = "TOTAL",
    value: float | str = 100.0,
) -> Any:
    """Build a parsed `TradeRecord`."""
    raw = _baseline_raw(
        reporterCode=reporter,
        partnerCode=partner,
        period=period,
        refPeriodId=period_id,
        refYear=int(period),
        flowCode=flow,
        classificationCode=classification,
        cmdCode=commodity,
        fobvalue=value,
        primaryValue=value,
    )
    return TradeParser(log_skipped=False).parse_records([raw]).records[0]


def _records(*tuples) -> tuple:
    """Build multiple records from tuples of
    `(reporter, partner, period, flow, value)`."""
    out = []
    for t in tuples:
        reporter, partner, period, flow, value = t
        out.append(
            _record(
                reporter=reporter,
                partner=partner,
                period=period,
                period_id=int(period) * 10000 + 1,
                flow=flow,
                value=value,
            )
        )
    return tuple(out)


def _make_dataset(records, *, name: str = "p") -> CanonicalDataset:
    return CanonicalDataset(
        name=name, records=records, parser_name="TradeParser"
    )


def _temp_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="test_storage_updates_"))


# ---------------------------------------------------------------------------
# TestUpdateMode
# ---------------------------------------------------------------------------


class TestUpdateMode:
    def test_three_modes(self):
        assert UpdateMode.APPEND.value == "append"
        assert UpdateMode.MERGE.value == "merge"
        assert UpdateMode.REPLACE.value == "replace"

    def test_inherits_from_str(self):
        # StringEnum semantics — usable as dict key.
        assert UpdateMode.APPEND == "append"
        assert hash(UpdateMode.MERGE) == hash("merge")


# ---------------------------------------------------------------------------
# TestDuplicatePolicy
# ---------------------------------------------------------------------------


class TestDuplicatePolicy:
    def test_two_policies(self):
        assert DuplicatePolicy.KEEP_FIRST.value == "keep_first"
        assert DuplicatePolicy.KEEP_LAST.value == "keep_last"


# ---------------------------------------------------------------------------
# TestUpdateResult
# ---------------------------------------------------------------------------


class TestUpdateResult:
    def test_frozen_dataclass(self):
        r = UpdateResult(
            mode=UpdateMode.APPEND,
            backend=StorageBackend.CSV,
            records_added=1,
            records_merged=0,
            duplicates_in_input=0,
            duration_seconds=0.01,
            destination="/tmp/x",
        )
        with pytest.raises((AttributeError, Exception)):
            r.records_added = 999  # type: ignore[misc]

    def test_all_fields_present(self):
        r = UpdateResult(
            mode=UpdateMode.MERGE,
            backend=StorageBackend.DUCKDB,
            records_added=2,
            records_merged=1,
            duplicates_in_input=3,
            duration_seconds=0.05,
            destination="/tmp/x.duckdb",
        )
        assert r.mode is UpdateMode.MERGE
        assert r.backend is StorageBackend.DUCKDB
        assert r.records_added == 2
        assert r.records_merged == 1
        assert r.duplicates_in_input == 3
        assert r.duration_seconds == pytest.approx(0.05)
        assert r.destination == "/tmp/x.duckdb"


# ---------------------------------------------------------------------------
# TestFindDuplicates
# ---------------------------------------------------------------------------


class TestFindDuplicates:
    def test_no_duplicates_returns_empty_dict(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
        )
        dupes = find_duplicates(records)
        assert dupes == {}

    def test_two_records_same_key_one_duplicate(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "X", 999.0),
        )
        dupes = find_duplicates(records)
        assert len(dupes) == 1
        key = list(dupes.keys())[0]
        assert dupes[key][0].reporter.reporter_code == 699

    def test_three_records_same_key_two_duplicates(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "X", 200.0),
            (699, 0, "2022", "X", 300.0),
        )
        dupes = find_duplicates(records)
        assert len(dupes) == 1
        assert len(list(dupes.values())[0]) == 3

    def test_mixed_duplicates_and_uniques(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
            (699, 0, "2023", "X", 400.0),
        )
        dupes = find_duplicates(records)
        assert len(dupes) == 1
        # Only the (699, 0, 2022, X) pair is a dupe.
        key = list(dupes.keys())[0]
        assert key[0] == 699
        assert key[2] == "2022"

    def test_custom_key_fn(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
        )
        # Custom key fn: only the reporter_code.
        dupes = find_duplicates(records, key_fn=lambda r: (r.reporter.reporter_code,))
        assert len(dupes) == 1
        assert list(dupes.keys())[0] == (699,)


# ---------------------------------------------------------------------------
# TestDeduplicate
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_no_duplicates_passthrough(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        out = deduplicate(records)
        assert len(out) == 2

    def test_keep_last_default(self):
        # Two records with same composite key, last
        # wins.
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "X", 999.0),
        )
        out = deduplicate(records)
        assert len(out) == 1
        assert out[0].trade_value.primary_value == Decimal("999")

    def test_keep_first(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "X", 999.0),
        )
        out = deduplicate(
            records, policy=DuplicatePolicy.KEEP_FIRST
        )
        assert len(out) == 1
        assert out[0].trade_value.primary_value == Decimal("100")

    def test_preserves_first_seen_order(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
            (699, 0, "2023", "X", 300.0),
            (156, 0, "2022", "X", 400.0),  # dup of #2
        )
        out = deduplicate(
            records, policy=DuplicatePolicy.KEEP_LAST
        )
        # Three unique keys, in first-seen order:
        # (699, 2022) → (156, 2022) → (699, 2023)
        assert len(out) == 3
        assert out[0].reporter.reporter_code == 699
        assert out[0].period == "2022"
        assert out[1].reporter.reporter_code == 156
        assert out[1].trade_value.primary_value == Decimal("400")
        assert out[2].reporter.reporter_code == 699
        assert out[2].period == "2023"


# ---------------------------------------------------------------------------
# TestSchemaCompatibility
# ---------------------------------------------------------------------------


class TestSchemaCompatibility:
    def test_no_existing_metadata_is_compatible(self):
        ds = _make_dataset(_records((699, 0, "2022", "X", 100.0)))
        ok, reason = verify_schema_compatibility(ds, None)
        assert ok is True
        assert reason == ""

    def test_matching_schema_is_compatible(self):
        records = _records((699, 0, "2022", "X", 100.0))
        ds = _make_dataset(records)
        existing = DatasetMetadata(
            dataset_name="p",
            schema_version=ds.schema_version,
            parser_name="TradeParser",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=None,
            partition_keys=(),
            backend=StorageBackend.CSV,
            destination="/tmp/x",
        )
        ok, reason = verify_schema_compatibility(ds, existing)
        assert ok is True

    def test_mismatched_schema_version(self):
        ds = _make_dataset(_records((699, 0, "2022", "X", 100.0)))
        existing = DatasetMetadata(
            dataset_name="p",
            schema_version="0.9.0",  # different
            parser_name="TradeParser",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=None,
            partition_keys=(),
            backend=StorageBackend.CSV,
            destination="/tmp/x",
        )
        ok, reason = verify_schema_compatibility(ds, existing)
        assert ok is False
        assert "schema_version" in reason

    def test_mismatched_parser_name(self):
        ds = _make_dataset(_records((699, 0, "2022", "X", 100.0)))
        existing = DatasetMetadata(
            dataset_name="p",
            schema_version=ds.schema_version,
            parser_name="OtherParser",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=None,
            partition_keys=(),
            backend=StorageBackend.CSV,
            destination="/tmp/x",
        )
        ok, reason = verify_schema_compatibility(ds, existing)
        assert ok is False
        assert "parser_name" in reason


# ---------------------------------------------------------------------------
# TestDatasetUpdaterAppend
# ---------------------------------------------------------------------------


class TestDatasetUpdaterAppend:
    """APPEND adds new rows without touching existing."""

    def test_csv_append(self, tmp_root):
        _initial_write_csv(tmp_root, value=100.0)
        new_record = _record(
            reporter=156, period="2022", value=200.0
        )
        ds = _make_dataset((new_record,))
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.APPEND)
        assert result.records_added == 1
        assert result.records_merged == 0
        # Verify final state: 2 distinct rows.
        rows = _read_csv_rows(tmp_root)
        assert len(rows) == 2
        reporters = {r["reporter_code"] for r in rows}
        assert reporters == {"699", "156"}

    def test_json_append(self, tmp_root):
        _initial_write_json(tmp_root, value=100.0)
        new_record = _record(
            reporter=156, period="2022", value=200.0
        )
        ds = _make_dataset((new_record,))
        updater = DatasetUpdater(
            backend=StorageBackend.JSON,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.APPEND)
        assert result.records_added == 1
        rows = _read_json_rows(tmp_root)
        assert len(rows) == 2

    def test_parquet_append(self, tmp_root):
        _initial_write_parquet(tmp_root, value=100.0)
        new_record = _record(
            reporter=156, period="2022", value=200.0
        )
        ds = _make_dataset((new_record,))
        updater = DatasetUpdater(
            backend=StorageBackend.PARQUET,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.APPEND)
        assert result.records_added == 1
        rows = _read_parquet_rows(tmp_root)
        assert len(rows) == 2

    def test_duckdb_append(self, tmp_duckdb):
        _initial_write_duckdb(tmp_duckdb, value=100.0)
        new_record = _record(
            reporter=156, period="2022", value=200.0
        )
        ds = _make_dataset((new_record,))
        updater = DatasetUpdater(
            backend=StorageBackend.DUCKDB,
            config=StorageConfig(root=str(tmp_duckdb)),
        )
        result = updater.update(ds, UpdateMode.APPEND)
        assert result.records_added == 1
        rows = _read_duckdb_rows(tmp_duckdb)
        assert len(rows) == 2

    def test_append_multiple_records(self, tmp_root):
        _initial_write_csv(tmp_root, value=100.0)
        records = _records(
            (156, 0, "2022", "X", 200.0),
            (842, 0, "2022", "X", 300.0),
        )
        ds = _make_dataset(records)
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.APPEND)
        assert result.records_added == 2
        rows = _read_csv_rows(tmp_root)
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# TestDatasetUpdaterMerge
# ---------------------------------------------------------------------------


class TestDatasetUpdaterMerge:
    """MERGE replaces existing rows on composite-key
    collision."""

    def test_csv_merge_replaces_collision(self, tmp_root):
        _initial_write_csv(tmp_root, value=100.0)
        # New record with SAME composite key as
        # initial (reporter=699, partner=0,
        # period=2022, flow=X).
        updated = _record(value=999.0)
        ds = _make_dataset((updated,))
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        assert result.records_added == 1
        assert result.records_merged == 1

        rows = _read_csv_rows(tmp_root)
        assert len(rows) == 1
        assert Decimal(rows[0]["trade_value_primary_value"]) == Decimal(
            "999"
        )

    def test_csv_merge_preserves_unique_existing(self, tmp_root):
        # Initial write: 2 distinct records.
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        _initial_write_csv(tmp_root, records=records)

        # Update only the (699, ...) row.
        updated = _record(reporter=699, value=999.0)
        ds = _make_dataset((updated,))
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        assert result.records_added == 1
        assert result.records_merged == 1

        rows = _read_csv_rows(tmp_root)
        assert len(rows) == 2
        # Find each by reporter.
        by_reporter = {r["reporter_code"]: r for r in rows}
        assert Decimal(
            by_reporter["699"]["trade_value_primary_value"]
        ) == Decimal("999")
        assert Decimal(
            by_reporter["156"]["trade_value_primary_value"]
        ) == Decimal("200")

    def test_json_merge(self, tmp_root):
        _initial_write_json(tmp_root, value=100.0)
        updated = _record(value=999.0)
        ds = _make_dataset((updated,))
        updater = DatasetUpdater(
            backend=StorageBackend.JSON,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        assert result.records_merged == 1

    def test_parquet_merge(self, tmp_root):
        _initial_write_parquet(tmp_root, value=100.0)
        updated = _record(value=999.0)
        ds = _make_dataset((updated,))
        updater = DatasetUpdater(
            backend=StorageBackend.PARQUET,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        assert result.records_merged == 1

        rows = _read_parquet_rows(tmp_root)
        assert len(rows) == 1
        val = rows[0]["trade_value_primary_value"]
        if hasattr(val, "as_tuple"):
            assert val == Decimal("999")
        else:
            assert str(val) == "999"

    def test_duckdb_merge(self, tmp_duckdb):
        _initial_write_duckdb(tmp_duckdb, value=100.0)
        updated = _record(value=999.0)
        ds = _make_dataset((updated,))
        updater = DatasetUpdater(
            backend=StorageBackend.DUCKDB,
            config=StorageConfig(root=str(tmp_duckdb)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        assert result.records_merged == 1

        rows = _read_duckdb_rows(tmp_duckdb)
        assert len(rows) == 1
        val = rows[0]["trade_value_primary_value"]
        if hasattr(val, "as_tuple"):
            assert val == Decimal("999")
        else:
            assert str(val) == "999"

    def test_merge_with_mixed_new_and_existing_keys(self, tmp_root):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        _initial_write_csv(tmp_root, records=records)

        new_records = _records(
            (699, 0, "2022", "X", 999.0),  # collision
            (842, 0, "2022", "X", 300.0),  # new key
        )
        ds = _make_dataset(new_records)
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        assert result.records_added == 2
        assert result.records_merged == 1
        rows = _read_csv_rows(tmp_root)
        assert len(rows) == 3
        # Reporter 999 → 699 only.
        by_reporter = {r["reporter_code"]: r for r in rows}
        assert set(by_reporter.keys()) == {"699", "156", "842"}


# ---------------------------------------------------------------------------
# TestDatasetUpdaterReplace
# ---------------------------------------------------------------------------


class TestDatasetUpdaterReplace:
    """REPLACE has same final state as MERGE but
    expressed as delete-then-insert."""

    def test_csv_replace(self, tmp_root):
        _initial_write_csv(tmp_root, value=100.0)
        updated = _record(value=999.0)
        ds = _make_dataset((updated,))
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.REPLACE)
        assert result.mode is UpdateMode.REPLACE
        assert result.records_merged == 1
        rows = _read_csv_rows(tmp_root)
        assert Decimal(rows[0]["trade_value_primary_value"]) == Decimal(
            "999"
        )

    def test_duckdb_replace(self, tmp_duckdb):
        _initial_write_duckdb(tmp_duckdb, value=100.0)
        updated = _record(value=999.0)
        ds = _make_dataset((updated,))
        updater = DatasetUpdater(
            backend=StorageBackend.DUCKDB,
            config=StorageConfig(root=str(tmp_duckdb)),
        )
        result = updater.update(ds, UpdateMode.REPLACE)
        assert result.mode is UpdateMode.REPLACE
        assert result.records_merged == 1


# ---------------------------------------------------------------------------
# TestDuplicateDetectionInUpdate
# ---------------------------------------------------------------------------


class TestDuplicateDetectionInUpdate:
    """Incoming batches with internal duplicates
    are deduplicated before the update is applied."""

    def test_input_with_internal_duplicates_deduped(self, tmp_root):
        _initial_write_csv(tmp_root, value=100.0)
        # Two records with the SAME composite key.
        duplicate_records = _records(
            (699, 0, "2022", "X", 200.0),
            (699, 0, "2022", "X", 300.0),
        )
        ds = _make_dataset(duplicate_records)
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        # 2 incoming records, 1 unique → 1 duplicate
        assert result.duplicates_in_input == 1
        # Last-wins by default → 300.
        rows = _read_csv_rows(tmp_root)
        assert len(rows) == 1
        assert Decimal(rows[0]["trade_value_primary_value"]) == Decimal(
            "300"
        )

    def test_keep_first_policy(self, tmp_root):
        _initial_write_csv(tmp_root, value=100.0)
        duplicate_records = _records(
            (699, 0, "2022", "X", 200.0),
            (699, 0, "2022", "X", 300.0),
        )
        ds = _make_dataset(duplicate_records)
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(
            ds,
            UpdateMode.MERGE,
            duplicate_policy=DuplicatePolicy.KEEP_FIRST,
        )
        assert result.duplicates_in_input == 1
        rows = _read_csv_rows(tmp_root)
        # First wins → 200.
        assert Decimal(rows[0]["trade_value_primary_value"]) == Decimal(
            "200"
        )


# ---------------------------------------------------------------------------
# TestSchemaCheckDuringUpdate
# ---------------------------------------------------------------------------


class TestSchemaCheckDuringUpdate:
    """`check_schema=True` (default) verifies
    schema compatibility; `check_schema=False`
    skips the check."""

    def test_no_existing_metadata_skips_check(self, tmp_root):
        # No prior write → no existing_metadata →
        # no schema check needed.
        records = _records((699, 0, "2022", "X", 100.0),)
        _initial_write_csv(tmp_root, records=records)

        new = _record(value=200.0)
        ds = _make_dataset((new,))
        # When existing_metadata is None, no check
        # is performed.
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(ds, UpdateMode.MERGE)
        assert result.records_added == 1

    def test_compatible_metadata_passes(self, tmp_root):
        records = _records((699, 0, "2022", "X", 100.0),)
        _initial_write_csv(tmp_root, records=records)

        new = _record(value=200.0)
        ds = _make_dataset((new,))
        existing = DatasetMetadata(
            dataset_name="p",
            schema_version=ds.schema_version,
            parser_name="TradeParser",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=None,
            partition_keys=(),
            backend=StorageBackend.CSV,
            destination=str(tmp_root),
        )
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        result = updater.update(
            ds, UpdateMode.MERGE, existing_metadata=existing
        )
        assert result.records_added == 1

    def test_incompatible_metadata_raises(self, tmp_root):
        records = _records((699, 0, "2022", "X", 100.0),)
        _initial_write_csv(tmp_root, records=records)

        new = _record(value=200.0)
        ds = _make_dataset((new,))
        existing = DatasetMetadata(
            dataset_name="p",
            schema_version="0.9.0",  # mismatch
            parser_name="TradeParser",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=None,
            partition_keys=(),
            backend=StorageBackend.CSV,
            destination=str(tmp_root),
        )
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        with pytest.raises(SchemaIncompatibleError):
            updater.update(
                ds, UpdateMode.MERGE, existing_metadata=existing
            )

    def test_check_schema_false_skips_check(self, tmp_root):
        records = _records((699, 0, "2022", "X", 100.0),)
        _initial_write_csv(tmp_root, records=records)

        new = _record(value=200.0)
        ds = _make_dataset((new,))
        existing = DatasetMetadata(
            dataset_name="p",
            schema_version="0.9.0",  # mismatch
            parser_name="TradeParser",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=None,
            partition_keys=(),
            backend=StorageBackend.CSV,
            destination=str(tmp_root),
        )
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        # check_schema=False → no raise.
        result = updater.update(
            ds,
            UpdateMode.MERGE,
            check_schema=False,
            existing_metadata=existing,
        )
        assert result.records_added == 1


# ---------------------------------------------------------------------------
# TestInvalidInputs
# ---------------------------------------------------------------------------


class TestInvalidInputs:
    """Reject bad source / bad mode / bad policy."""

    def test_non_canonical_dataset_source_rejected(self, tmp_root):
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        with pytest.raises(StorageError, match="CanonicalDataset"):
            updater.update([{"raw": "dict"}], UpdateMode.APPEND)

    def test_bad_mode_rejected(self, tmp_root):
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        ds = _make_dataset(_records((699, 0, "2022", "X", 100.0),))
        with pytest.raises(TypeError, match="UpdateMode"):
            updater.update(ds, "append")  # type: ignore[arg-type]

    def test_bad_duplicate_policy_rejected(self, tmp_root):
        updater = DatasetUpdater(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        ds = _make_dataset(_records((699, 0, "2022", "X", 100.0),))
        with pytest.raises(TypeError, match="DuplicatePolicy"):
            updater.update(
                ds,
                UpdateMode.APPEND,
                duplicate_policy="keep_last",  # type: ignore[arg-type]
            )

    def test_bad_backend_type_rejected(self, tmp_root):
        with pytest.raises(TypeError, match="StorageBackend"):
            DatasetUpdater(
                backend="csv",  # type: ignore[arg-type]
                config=StorageConfig(root=str(tmp_root)),
            )

    def test_bad_config_type_rejected(self, tmp_root):
        with pytest.raises(TypeError, match="StorageConfig"):
            DatasetUpdater(
                backend=StorageBackend.CSV,
                config={"root": str(tmp_root)},  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# TestUpdaterRepr
# ---------------------------------------------------------------------------


class TestUpdaterRepr:
    def test_repr_includes_backend_and_root(self, tmp_root):
        updater = DatasetUpdater(
            backend=StorageBackend.DUCKDB,
            config=StorageConfig(root=str(tmp_root)),
        )
        r = repr(updater)
        assert "DatasetUpdater" in r
        assert "duckdb" in r
        # `repr()` escapes Windows backslashes
        # (`\` → `\\`), so the string-equality
        # check must use `repr()` of the path
        # too.
        assert repr(str(tmp_root)) in r


# ---------------------------------------------------------------------------
# Initial-write helpers (one per backend)
# ---------------------------------------------------------------------------


def _initial_write_csv(
    root: Path,
    *,
    value: float | None = None,
    records: tuple | None = None,
) -> None:
    if records is None:
        records = _records((699, 0, "2022", "X", value or 100.0),)
    ds = _make_dataset(records)
    CSVWriter().store(ds, StorageConfig(root=str(root)))


def _initial_write_json(
    root: Path,
    *,
    value: float | None = None,
    records: tuple | None = None,
) -> None:
    if records is None:
        records = _records((699, 0, "2022", "X", value or 100.0),)
    ds = _make_dataset(records)
    JSONWriter().store(ds, StorageConfig(root=str(root)))


def _initial_write_parquet(
    root: Path,
    *,
    value: float | None = None,
    records: tuple | None = None,
) -> None:
    if records is None:
        records = _records((699, 0, "2022", "X", value or 100.0),)
    ds = _make_dataset(records)
    ParquetWriter().store(ds, StorageConfig(root=str(root)))


def _initial_write_duckdb(
    db_path: Path,
    *,
    value: float | None = None,
    records: tuple | None = None,
) -> None:
    if records is None:
        records = _records((699, 0, "2022", "X", value or 100.0),)
    ds = _make_dataset(records)
    DuckDBWriter().store(ds, StorageConfig(root=str(db_path)))


# ---------------------------------------------------------------------------
# Read-back helpers (one per backend)
# ---------------------------------------------------------------------------


def _read_csv_rows(root: Path) -> list[dict]:
    rows = []
    for f in root.rglob("*.csv"):
        with f.open("rt", encoding="utf-8") as fh:
            rows.extend(_csv_stdlib.DictReader(fh))
    return rows


def _read_json_rows(root: Path) -> list[dict]:
    rows = []
    for f in root.rglob("*.json"):
        if f.name.endswith(".meta.json"):
            continue
        payload = _json_stdlib.loads(f.read_text(encoding="utf-8"))
        rows.extend(payload.get("records", []))
    return rows


def _read_parquet_rows(root: Path) -> list[dict]:
    rows = []
    for f in sorted(root.rglob("*.parquet")):
        rows.extend(pq.read_table(f).to_pylist())
    return rows


def _read_duckdb_rows(db_path: Path) -> list[dict]:
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        # Use fetchall + column names to avoid the
        # pandas/numpy dependency that fetchdf
        # requires.
        result = conn.execute("SELECT * FROM trade_records")
        columns = [d[0] for d in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cleanup fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_root():
    root = _temp_root()
    yield root
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def tmp_duckdb(tmp_root):
    db = tmp_root / "test.duckdb"
    yield db