"""Tests for the CSV / JSON storage engines (P5-004).

Per the P5-004 task scope, this module covers:

- CSV writer (Python stdlib `csv` module).
- JSON writer (Python stdlib `json` module).
- Compression support (gzip on both; metadata sidecar
  always plain JSON).
- Metadata files (`<root>/<dataset_name>.meta.json`
  sidecar).

Coverage:

- `TestCSVWriter` — basic write, header row,
  Decimal-as-string, gzip compression, multi-
  partition, empty dataset, metadata sidecar,
  in-pipeline usage.
- `TestJSONWriter` — basic write, top-level shape,
  Decimal-as-string, gzip compression, multi-
  partition, empty dataset, metadata sidecar,
  pretty-print via `indent`, in-pipeline usage.
- `TestMetadataSidecar` — roundtrip the sidecar
  contents, validate metadata_schema_version,
  validate partition keys format.
- `TestCompression` — gzip output is smaller than
  plain; gzipped files can be decompressed and
  read.
- `TestFileStorageEdgeCases` — bad source rejected,
  bad compression rejected, empty dataset,
  metadata sidecar always plain JSON.
"""

from __future__ import annotations

import csv as _csv_stdlib
import gzip
import json
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.parser import TradeParser
from un_comtrade.storage import (
    DatasetMetadata,
    PartitionStrategy,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageResult,
)
from un_comtrade.storage.file import (
    CSV_SCHEMA_VERSION,
    CSVWriter,
    JSON_SCHEMA_VERSION,
    JSONWriter,
    METADATA_SCHEMA_VERSION,
    write_metadata_sidecar,
)
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baseline_raw_record(**overrides) -> dict:
    """Build a baseline raw upstream trade record."""
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
        "fobvalue": 452684213646.747,
        "primaryValue": 452684213646.747,
        "legacyEstimationFlag": 0,
        "isReported": False,
        "isAggregate": True,
    }
    raw.update(overrides)
    return raw


def _parse(raws: list[dict]) -> tuple:
    """Parse a list of raw records into TradeRecord
    instances."""
    return tuple(TradeParser(log_skipped=False).parse_records(raws).records)


def _make_dataset(
    records: tuple,
    *,
    name: str = "p",
    parser_name: str = "TradeParser",
) -> CanonicalDataset:
    return CanonicalDataset(
        name=name, records=records, parser_name=parser_name
    )


def _temp_root() -> Path:
    """Return a fresh temp directory."""
    import tempfile

    return Path(tempfile.mkdtemp(prefix="test_file_storage_"))


# ---------------------------------------------------------------------------
# TestCSVWriter
# ---------------------------------------------------------------------------


class TestCSVWriter:
    def test_writer_backend_is_csv(self):
        writer = CSVWriter()
        assert writer.backend is StorageBackend.CSV

    def test_writer_rejects_non_canonical_dataset(self, tmp_root):
        writer = CSVWriter()
        config = StorageConfig(root=str(tmp_root))
        with pytest.raises(StorageError, match="CanonicalDataset"):
            writer.store({"raw": "dict"}, config)

    def test_writer_writes_csv_with_header(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = CSVWriter()
        config = StorageConfig(root=str(tmp_root))
        writer.store(dataset, config)

        # Find the produced CSV (Hive-style partition).
        csv_files = list(tmp_root.rglob("*.csv"))
        assert len(csv_files) == 1

        # Read back: header + 1 row.
        with csv_files[0].open("rt", encoding="utf-8") as fh:
            reader = _csv_stdlib.DictReader(fh)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["reporter_code"] == "699"
        assert rows[0]["period"] == "2022"

    def test_writer_writes_metadata_sidecar(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records, name="my_dataset")

        writer = CSVWriter()
        config = StorageConfig(root=str(tmp_root))
        writer.store(dataset, config)

        # Metadata sidecar exists.
        sidecar = tmp_root / "my_dataset.meta.json"
        assert sidecar.exists()
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert payload["dataset_name"] == "my_dataset"
        assert payload["record_count"] == 1
        assert payload["metadata_schema_version"] == (
            METADATA_SCHEMA_VERSION
        )
        assert payload["backend"] == "csv"
        # csv_schema_version lives under extra (along
        # with engine-specific settings).
        assert payload["extra"]["csv_schema_version"] == (
            CSV_SCHEMA_VERSION
        )

    def test_writer_decimal_preserved_as_string(self, tmp_root):
        raw = _baseline_raw_record(
            fobvalue="452684213646.747",
            primaryValue="452684213646.747",
        )
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = CSVWriter()
        config = StorageConfig(root=str(tmp_root))
        writer.store(dataset, config)

        # Find the produced CSV.
        csv_files = list(tmp_root.rglob("*.csv"))
        with csv_files[0].open("rt", encoding="utf-8") as fh:
            reader = _csv_stdlib.DictReader(fh)
            row = next(iter(reader))
        # Decimal values are serialised as strings
        # to preserve exact precision.
        assert row["trade_value_primary_value"] == "452684213646.747"

    def test_writer_handles_empty_dataset(self, tmp_root):
        dataset = _make_dataset(records=())
        writer = CSVWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        assert result.empty
        # File exists with header only.
        csv_files = list(tmp_root.rglob("*.csv"))
        assert len(csv_files) == 1
        with csv_files[0].open("rt", encoding="utf-8") as fh:
            lines = fh.readlines()
        assert len(lines) == 1  # header only

    def test_writer_gzip_compression(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = CSVWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="gzip"
        )
        writer.store(dataset, config)

        # The data file is gzipped (extension .csv.gz).
        gz_files = list(tmp_root.rglob("*.csv.gz"))
        assert len(gz_files) == 1

        # Read back via gzip.
        with gzip.open(gz_files[0], "rt", encoding="utf-8") as fh:
            reader = _csv_stdlib.DictReader(fh)
            rows = list(reader)
        assert len(rows) == 1

    def test_writer_metadata_extra_carries_compression(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = CSVWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="gzip"
        )
        result = writer.store(dataset, config)

        assert result.metadata.extra["compression"] == "gzip"

    def test_writer_multiple_partitions(self, tmp_root):
        raws = [
            _baseline_raw_record(
                reporterCode=699, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
            _baseline_raw_record(
                reporterCode=156, refYear=2023,
                refPeriodId=20230101, period="2023",
            ),
        ]
        records = _parse(raws)
        dataset = _make_dataset(records=records)

        writer = CSVWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        # Two distinct partition keys → two CSV files.
        csv_files = list(tmp_root.rglob("*.csv"))
        assert len(csv_files) == 2
        assert len(result.partitions) == 2

    def test_writer_repr(self):
        writer = CSVWriter()
        r = repr(writer)
        assert "CSVWriter" in r
        assert "csv" in r


# ---------------------------------------------------------------------------
# TestJSONWriter
# ---------------------------------------------------------------------------


class TestJSONWriter:
    def test_writer_backend_is_json(self):
        writer = JSONWriter()
        assert writer.backend is StorageBackend.JSON

    def test_writer_rejects_non_canonical_dataset(self, tmp_root):
        writer = JSONWriter()
        config = StorageConfig(root=str(tmp_root))
        with pytest.raises(StorageError, match="CanonicalDataset"):
            writer.store({"raw": "dict"}, config)

    def test_writer_writes_json_with_top_level_shape(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = JSONWriter()
        config = StorageConfig(root=str(tmp_root))
        writer.store(dataset, config)

        json_files = [
            p for p in tmp_root.rglob("*.json")
            if not p.name.endswith(".meta.json")
        ]
        assert len(json_files) == 1

        with json_files[0].open("rt", encoding="utf-8") as fh:
            payload = json.load(fh)
        # Per spec §10.1: top-level has
        # `schema_version`, `count`, `records`.
        assert payload["schema_version"] == JSON_SCHEMA_VERSION
        assert payload["count"] == 1
        assert isinstance(payload["records"], list)
        assert len(payload["records"]) == 1
        assert payload["records"][0]["reporter_code"] == 699

    def test_writer_writes_metadata_sidecar(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records, name="my_dataset")

        writer = JSONWriter()
        config = StorageConfig(root=str(tmp_root))
        writer.store(dataset, config)

        sidecar = tmp_root / "my_dataset.meta.json"
        assert sidecar.exists()
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert payload["dataset_name"] == "my_dataset"
        assert payload["record_count"] == 1
        assert payload["backend"] == "json"

    def test_writer_decimal_preserved_as_string(self, tmp_root):
        raw = _baseline_raw_record(
            fobvalue="452684213646.747",
            primaryValue="452684213646.747",
        )
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = JSONWriter()
        config = StorageConfig(root=str(tmp_root))
        writer.store(dataset, config)

        json_files = [
            p
            for p in tmp_root.rglob("*.json")
            if not p.name.endswith(".meta.json")
        ]
        with json_files[0].open("rt", encoding="utf-8") as fh:
            payload = json.load(fh)
        # Decimal values are strings (exact precision).
        assert payload["records"][0]["trade_value_primary_value"] == (
            "452684213646.747"
        )

    def test_writer_gzip_compression(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = JSONWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="gzip"
        )
        writer.store(dataset, config)

        gz_files = list(tmp_root.rglob("*.json.gz"))
        assert len(gz_files) == 1

        with gzip.open(gz_files[0], "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
        assert payload["count"] == 1

    def test_writer_pretty_print_via_indent(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = JSONWriter()
        config = StorageConfig(
            root=str(tmp_root),
            compression="none",
            metadata={"indent": 2},
        )
        writer.store(dataset, config)

        json_files = list(tmp_root.rglob("*.json"))
        text = json_files[0].read_text(encoding="utf-8")
        # Pretty-printed with indent 2 → contains
        # newlines + leading spaces.
        assert "\n" in text

    def test_writer_handles_empty_dataset(self, tmp_root):
        dataset = _make_dataset(records=())
        writer = JSONWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        assert result.empty
        json_files = [
            p
            for p in tmp_root.rglob("*.json")
            if not p.name.endswith(".meta.json")
        ]
        with json_files[0].open("rt", encoding="utf-8") as fh:
            payload = json.load(fh)
        assert payload["count"] == 0
        assert payload["records"] == []

    def test_writer_metadata_extra_carries_indent(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = JSONWriter()
        config = StorageConfig(
            root=str(tmp_root), metadata={"indent": 4}
        )
        result = writer.store(dataset, config)
        assert result.metadata.extra["indent"] == 4

    def test_writer_multiple_partitions(self, tmp_root):
        raws = [
            _baseline_raw_record(
                reporterCode=699, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
            _baseline_raw_record(
                reporterCode=156, refYear=2023,
                refPeriodId=20230101, period="2023",
            ),
        ]
        records = _parse(raws)
        dataset = _make_dataset(records=records)

        writer = JSONWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        json_files = [
            p for p in tmp_root.rglob("*.json")
            if not p.name.endswith(".meta.json")
        ]
        assert len(json_files) == 2

    def test_writer_repr(self):
        writer = JSONWriter()
        r = repr(writer)
        assert "JSONWriter" in r
        assert "json" in r


# ---------------------------------------------------------------------------
# TestMetadataSidecar
# ---------------------------------------------------------------------------


class TestMetadataSidecar:
    def test_sidecar_roundtrip(self, tmp_root):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="my_dataset",
            schema_version="1.0.0",
            parser_name="TradeParser",
            record_count=42,
            skipped=3,
            duplicates_removed=1,
            source_count=46,
            extracted_at=ts,
            stored_at=ts,
            partition_keys=((699, 2022, "A"), (156, 2022, "A")),
            backend=StorageBackend.CSV,
            destination=str(tmp_root),
            extra={"compression": "none"},
        )
        path = write_metadata_sidecar(tmp_root, "my_dataset", meta)
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["dataset_name"] == "my_dataset"
        assert payload["record_count"] == 42
        assert payload["skipped"] == 3
        assert payload["duplicates_removed"] == 1
        assert payload["source_count"] == 46
        assert payload["partition_keys"] == [
            [699, 2022, "A"],
            [156, 2022, "A"],
        ]
        assert payload["backend"] == "csv"
        # compression lives in the `extra` map.
        assert payload["extra"]["compression"] == "none"
        assert payload["extracted_at"] is not None
        assert payload["stored_at"] is not None

    def test_sidecar_metadata_version_constant(self, tmp_root):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="d",
            schema_version="1.0.0",
            parser_name="p",
            record_count=0,
            skipped=0,
            duplicates_removed=0,
            source_count=0,
            extracted_at=None,
            stored_at=ts,
            partition_keys=(),
            backend=StorageBackend.JSON,
            destination=str(tmp_root),
        )
        path = write_metadata_sidecar(tmp_root, "d", meta)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["metadata_schema_version"] == (
            METADATA_SCHEMA_VERSION
        )

    def test_sidecar_indent_override(self, tmp_root):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="d",
            schema_version="1.0.0",
            parser_name="p",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=ts,
            partition_keys=(),
            backend=StorageBackend.JSON,
            destination=str(tmp_root),
        )
        path = write_metadata_sidecar(
            tmp_root, "d", meta, indent=None
        )
        text = path.read_text(encoding="utf-8")
        # indent=None → no pretty-printing.
        assert "\n" not in text

    def test_sidecar_creates_missing_dirs(self, tmp_root):
        from datetime import datetime, timezone

        nested = tmp_root / "deep" / "nested" / "path"
        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="d",
            schema_version="1.0.0",
            parser_name="p",
            record_count=1,
            skipped=0,
            duplicates_removed=0,
            source_count=1,
            extracted_at=None,
            stored_at=ts,
            partition_keys=(),
            backend=StorageBackend.JSON,
            destination=str(nested),
        )
        path = write_metadata_sidecar(nested, "d", meta)
        assert path.exists()


# ---------------------------------------------------------------------------
# TestCompression
# ---------------------------------------------------------------------------


class TestCompression:
    def test_unsupported_compression_rejected(self, tmp_root):
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = CSVWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="bzip2"
        )
        with pytest.raises(StorageError, match="Unsupported compression"):
            writer.store(dataset, config)

    def test_gzip_output_smaller_than_plain(self, tmp_root):
        # Repeat a single record many times so the
        # compression has data to work with.
        raws = [
            _baseline_raw_record(
                refPeriodId=20220101 + i,
                period="2022",
            )
            for i in range(100)
        ]
        records = _parse(raws)
        dataset = _make_dataset(records=records)

        # Plain
        plain_root = tmp_root / "plain"
        CSVWriter().store(
            dataset, StorageConfig(root=str(plain_root))
        )
        plain_size = sum(
            p.stat().st_size for p in plain_root.iterdir()
        )

        # Gzip
        gz_root = tmp_root / "gz"
        CSVWriter().store(
            dataset,
            StorageConfig(root=str(gz_root), compression="gzip"),
        )
        gz_size = sum(
            p.stat().st_size
            for p in gz_root.iterdir()
            if p.suffix == ".gz"
        )

        # Gzip is smaller for repetitive data.
        assert gz_size < plain_size

    def test_metadata_sidecar_always_plain_json(self, tmp_root):
        # Even when the data file is gzipped, the
        # metadata sidecar is plain JSON.
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)

        writer = CSVWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="gzip"
        )
        writer.store(dataset, config)

        sidecar = tmp_root / "p.meta.json"
        assert sidecar.exists()
        # The sidecar is plain JSON (no .gz extension).
        assert not sidecar.name.endswith(".gz")
        # Read it as plain JSON.
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert payload["dataset_name"] == "p"


# ---------------------------------------------------------------------------
# TestFileStorageEdgeCases
# ---------------------------------------------------------------------------


class TestFileStorageEdgeCases:
    def test_csv_writer_in_pipeline(self, tmp_root):
        """Extract → Transform → Storage (CSV)."""
        from un_comtrade.etl import (
            ETLPipeline,
            StageKind,
            StageSpec,
        )
        from un_comtrade.storage import StorageStage
        from un_comtrade.transform import TradeTransformer

        raws = [_baseline_raw_record()]
        transformer = TradeTransformer()
        stage = StorageStage(
            backend=StorageBackend.CSV,
            config=StorageConfig(root=str(tmp_root)),
        )
        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name="transform",
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name="store",
                    kind=StageKind.STORAGE,
                    factory=lambda ctx: stage,
                ),
            ),
        )
        result = pipeline.run(source=raws)
        assert result.status.value == "success"
        csv_files = list(tmp_root.rglob("*.csv"))
        assert len(csv_files) == 1

    def test_json_writer_in_pipeline(self, tmp_root):
        from un_comtrade.etl import (
            ETLPipeline,
            StageKind,
            StageSpec,
        )
        from un_comtrade.storage import StorageStage
        from un_comtrade.transform import TradeTransformer

        raws = [_baseline_raw_record()]
        transformer = TradeTransformer()
        stage = StorageStage(
            backend=StorageBackend.JSON,
            config=StorageConfig(root=str(tmp_root)),
        )
        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name="transform",
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name="store",
                    kind=StageKind.STORAGE,
                    factory=lambda ctx: stage,
                ),
            ),
        )
        result = pipeline.run(source=raws)
        assert result.status.value == "success"
        json_files = [
            p for p in tmp_root.rglob("*.json")
            if not p.name.endswith(".meta.json")
        ]
        assert len(json_files) == 1

    def test_csv_writer_with_unsupported_compression_rejected(self, tmp_root):
        writer = CSVWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="snappy"
        )
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)
        with pytest.raises(StorageError, match="Unsupported compression"):
            writer.store(dataset, config)

    def test_json_writer_with_unsupported_compression_rejected(self, tmp_root):
        writer = JSONWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="zstd"
        )
        raw = _baseline_raw_record()
        records = _parse([raw])
        dataset = _make_dataset(records=records)
        with pytest.raises(StorageError, match="Unsupported compression"):
            writer.store(dataset, config)

    def test_registry_returns_csv_writer(self):
        from un_comtrade.storage import StorageRegistry

        registry = StorageRegistry()
        storage = registry.get(StorageBackend.CSV)
        assert isinstance(storage, CSVWriter)

    def test_registry_returns_json_writer(self):
        from un_comtrade.storage import StorageRegistry

        registry = StorageRegistry()
        storage = registry.get(StorageBackend.JSON)
        assert isinstance(storage, JSONWriter)

    def test_csv_schema_version_constant(self):
        assert CSV_SCHEMA_VERSION == "1.0.0"

    def test_json_schema_version_constant(self):
        assert JSON_SCHEMA_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# Cleanup fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_root():
    """Yield a fresh temp directory and clean up."""
    root = _temp_root()
    yield root
    shutil.rmtree(root, ignore_errors=True)