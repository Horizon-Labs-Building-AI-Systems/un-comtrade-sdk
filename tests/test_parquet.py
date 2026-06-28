"""Tests for the concrete Parquet storage engine (P5-002).

Per the P5-002 task scope, the Parquet engine:
- Writes `CanonicalDataset` records to Parquet files
  via `pyarrow.parquet.write_table`.
- Preserves a stable Arrow schema across runs.
- Preserves `Decimal` precision via
  `decimal128(38, 18)`.
- Writes one file per partition key (default
  `(reporter, year, frequency)` per ADR-0029).

Coverage:

- `TestParquetSchema` — schema is stable, decimal
  columns are typed correctly, column order
  matches.
- `TestParquetDecimalPreservation` — high-precision
  Decimal values survive a roundtrip through
  Parquet.
- `TestParquetWriter` — basic write, empty dataset,
  bad source rejection, multiple partitions,
  default partition strategy, custom partition
  strategy, compression options, schema metadata,
  byte_size accounting.
- `TestParquetInPipeline` — full ETL pipeline
  ending in Parquet storage with a real filesystem
  output.
- `TestParquetSchemaPreservation` — same schema is
  used across multiple writes.
- `TestParquetPartitioning` — one file per partition
  key; deterministic partition paths.
- `TestParquetEdgeCases` — empty dataset, single
  partition, single record, deterministic
  roundtrip, overwrite, parquet_schema_version
  metadata.
"""

from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import pyarrow as pa
import pyarrow.parquet as pq

from un_comtrade.parser import TradeParser
from un_comtrade.storage import (
    DatasetMetadata,
    ParquetWriter,
    PartitionStrategy,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageResult,
)
from un_comtrade.storage.parquet import (
    PARQUET_SCHEMA_VERSION,
    parquet_schema,
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
    """Return a fresh temp directory path (caller
    cleans up)."""
    import tempfile

    return Path(tempfile.mkdtemp(prefix="test_parquet_"))


# ---------------------------------------------------------------------------
# TestParquetSchema
# ---------------------------------------------------------------------------


class TestParquetSchema:
    def test_schema_is_pa_schema(self):
        schema = parquet_schema()
        assert isinstance(schema, pa.Schema)

    def test_schema_has_canonical_columns(self):
        schema = parquet_schema()
        names = schema.names
        # Identifier / metadata
        for col in (
            "type_code",
            "frequency_code",
            "classification_code",
            "classification_search_code",
            "edition",
            "is_original_classification",
            "ref_period_id",
            "ref_year",
            "ref_month",
            "period",
        ):
            assert col in names
        # Subjects
        for col in (
            "reporter_code",
            "reporter_iso3",
            "reporter_name",
            "partner_code",
            "partner_iso3",
            "partner_name",
            "flow_code",
            "commodity_code",
        ):
            assert col in names
        # Monetary
        for col in (
            "trade_value_primary_value",
            "trade_value_fob_value",
            "trade_value_cif_value",
        ):
            assert col in names

    def test_decimal_columns_use_decimal128(self):
        schema = parquet_schema()
        for col in (
            "trade_value_primary_value",
            "trade_value_fob_value",
            "trade_value_cif_value",
            "quantity_qty",
            "net_weight_kg",
            "gross_weight_kg",
        ):
            assert pa.types.is_decimal(schema.field(col).type), (
                f"{col} should be decimal128"
            )

    def test_decimal_columns_non_nullable_primary(self):
        # Primary monetary value is non-nullable
        # (every record has a primary_value).
        schema = parquet_schema()
        f = schema.field("trade_value_primary_value")
        assert f.nullable is False

    def test_decimal_columns_nullable_optional(self):
        # Optional monetary fields are nullable.
        schema = parquet_schema()
        for col in (
            "trade_value_fob_value",
            "trade_value_cif_value",
            "net_weight_kg",
            "gross_weight_kg",
            "quantity_qty",
        ):
            assert schema.field(col).nullable is True, (
                f"{col} should be nullable"
            )

    def test_schema_is_stable_across_calls(self):
        s1 = parquet_schema()
        s2 = parquet_schema()
        assert s1.names == s2.names
        for i, name in enumerate(s1.names):
            assert s1.field(i).type == s2.field(i).type

    def test_schema_version_constant(self):
        assert PARQUET_SCHEMA_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# TestParquetDecimalPreservation
# ---------------------------------------------------------------------------


class TestParquetDecimalPreservation:
    def _write_and_read_back(
        self,
        tmp_root: Path,
        records: tuple,
    ) -> pa.Table:
        dataset = _make_dataset(records=records)
        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)
        # Read back from the single partition file.
        partition_paths = list(result.partitions.values())
        assert len(partition_paths) == 1
        return pq.read_table(partition_paths[0][0])

    def test_high_precision_decimal_preserved(self, tmp_root):
        raw = _baseline_raw_record(
            fobvalue="452684213646.747",
            primaryValue="452684213646.747",
        )
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        table = self._write_and_read_back(tmp_root, tuple(parsed))

        # The value comes back as Decimal (pyarrow
        # returns Decimal for decimal128 columns).
        values = table.column("trade_value_primary_value").to_pylist()
        assert len(values) == 1
        assert Decimal(values[0]) == Decimal("452684213646.747")

    def test_decimal_smaller_value_preserved(self, tmp_root):
        raw = _baseline_raw_record(
            fobvalue="123.45",
            primaryValue="123.45",
        )
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        table = self._write_and_read_back(tmp_root, tuple(parsed))

        values = table.column("trade_value_primary_value").to_pylist()
        assert Decimal(values[0]) == Decimal("123.45")

    def test_decimal_zero_preserved(self, tmp_root):
        # The parser requires non-negative Decimal
        # values, so a zero is the smallest value we
        # can test. This still exercises the
        # DECIMAL precision path.
        raw = _baseline_raw_record(
            fobvalue="0",
            primaryValue="0",
        )
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        table = self._write_and_read_back(tmp_root, tuple(parsed))

        primary = table.column("trade_value_primary_value").to_pylist()
        fob = table.column("trade_value_fob_value").to_pylist()
        assert Decimal(primary[0]) == Decimal("0")
        assert Decimal(fob[0]) == Decimal("0")

    def test_null_decimal_preserved(self, tmp_root):
        # CIF is None (only FOB and primary are present).
        raw = _baseline_raw_record(
            cifvalue=None,
            fobvalue="50.0",
            primaryValue="50.0",
        )
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        table = self._write_and_read_back(tmp_root, tuple(parsed))

        cif_values = table.column("trade_value_cif_value").to_pylist()
        assert cif_values[0] is None

    def test_quantity_decimal_preserved(self, tmp_root):
        raw = _baseline_raw_record(
            cmdCode="71023100",
            qty="12345.678",
            netWgt="12345.678",
            qtyUnitCode=8,
            qtyUnitAbbr="kg",
        )
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        table = self._write_and_read_back(tmp_root, tuple(parsed))

        qty_values = table.column("quantity_qty").to_pylist()
        net_values = table.column("net_weight_kg").to_pylist()
        assert Decimal(qty_values[0]) == Decimal("12345.678")
        assert Decimal(net_values[0]) == Decimal("12345.678")


# ---------------------------------------------------------------------------
# TestParquetWriter
# ---------------------------------------------------------------------------


class TestParquetWriter:
    def test_writer_backend_is_parquet(self):
        writer = ParquetWriter()
        assert writer.backend is StorageBackend.PARQUET

    def test_writer_rejects_non_canonical_dataset(self, tmp_root):
        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        with pytest.raises(StorageError, match="CanonicalDataset"):
            writer.store({"raw": "dict"}, config)

    def test_writer_writes_single_partition(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        # One partition (all records share the same
        # partition key).
        assert len(result.partitions) == 1
        # One file per partition.
        paths = list(result.partitions.values())[0]
        assert len(paths) == 1
        # File exists.
        file_path = Path(paths[0])
        assert file_path.exists()

    def test_writer_returns_storage_result(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        assert isinstance(result, StorageResult)
        assert result.backend is StorageBackend.PARQUET
        assert result.record_count == 1
        assert result.byte_size is not None
        assert result.byte_size > 0

    def test_writer_metadata_carries_provenance(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        assert isinstance(result.metadata, DatasetMetadata)
        assert result.metadata.dataset_name == "p"
        assert result.metadata.parser_name == "TradeParser"
        assert result.metadata.record_count == 1
        assert result.metadata.stored_at is not None

    def test_writer_metadata_extra_carries_schema_version(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="snappy"
        )
        result = writer.store(dataset, config)
        assert (
            result.metadata.extra["parquet_schema_version"]
            == PARQUET_SCHEMA_VERSION
        )
        assert result.metadata.extra["compression"] == "snappy"

    def test_writer_handles_empty_dataset(self, tmp_root):
        dataset = _make_dataset(records=())
        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        # Empty dataset: no files, metadata-only result.
        assert result.empty
        assert result.record_count == 0
        assert result.byte_size == 0
        assert result.partitions == {}

    def test_writer_writes_multiple_partitions(self, tmp_root):
        # Records with different (reporter, year)
        # produce different partitions. Each record
        # has a matching period so the parser's
        # composite-key dedup doesn't collapse them.
        raws = [
            _baseline_raw_record(
                reporterCode=699, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
            _baseline_raw_record(
                reporterCode=699, refYear=2023,
                refPeriodId=20230101, period="2023",
            ),
            _baseline_raw_record(
                reporterCode=156, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
        ]
        parsed = TradeParser(log_skipped=False).parse_records(raws).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        # Three distinct partition keys.
        assert len(result.partitions) == 3
        # Three files (one per partition).
        all_paths = [
            p for paths in result.partitions.values() for p in paths
        ]
        assert len(all_paths) == 3
        for p in all_paths:
            assert Path(p).exists()

    def test_writer_with_custom_partition_strategy(self, tmp_root):
        # Custom strategy that partitions by reporter_code only.
        def by_reporter(record: Any) -> tuple:
            r = getattr(record, "reporter", None)
            return (getattr(r, "reporter_code", None),)

        strategy = PartitionStrategy(
            name="by_reporter",
            extract=by_reporter,
            path_template="{dataset_name}",
        )
        raws = [
            _baseline_raw_record(
                reporterCode=699, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
            _baseline_raw_record(
                reporterCode=699, refYear=2023,
                refPeriodId=20230101, period="2023",
            ),
            _baseline_raw_record(
                reporterCode=156, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
        ]
        parsed = TradeParser(log_skipped=False).parse_records(raws).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(
            root=str(tmp_root), partition_strategy=strategy
        )
        result = writer.store(dataset, config)

        # Two distinct keys (699 and 156), three records.
        assert len(result.partitions) == 2
        all_paths = [
            p for paths in result.partitions.values() for p in paths
        ]
        assert len(all_paths) == 2

    def test_writer_with_compression(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(
            root=str(tmp_root), compression="snappy"
        )
        result = writer.store(dataset, config)
        # File was written; we don't deeply inspect the
        # compression codec here, just confirm the
        # writer doesn't reject a valid compression.
        assert result.byte_size > 0

    def test_writer_byte_size_sums_partition_files(self, tmp_root):
        raws = [
            _baseline_raw_record(reporterCode=699, refYear=2022),
            _baseline_raw_record(reporterCode=699, refYear=2023),
        ]
        parsed = TradeParser(log_skipped=False).parse_records(raws).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        # Sum of file sizes matches byte_size.
        total = sum(
            Path(p).stat().st_size
            for paths in result.partitions.values()
            for p in paths
        )
        assert result.byte_size == total


# ---------------------------------------------------------------------------
# TestParquetInPipeline
# ---------------------------------------------------------------------------


class TestParquetInPipeline:
    def test_full_pipeline_with_parquet_storage(self, tmp_root):
        """Extract → Transform → Storage (Parquet)."""
        raw_records = [
            _baseline_raw_record(
                refYear=2022, refPeriodId=20220101, period="2022"
            ),
            _baseline_raw_record(
                refYear=2023, refPeriodId=20230101, period="2023"
            ),
        ]

        class _Extractor:
            name = "extract_trade"
            kind = None  # not used; we set StageKind manually

            def __call__(self, source, c):
                return raw_records

        from un_comtrade.etl import StageKind
        from un_comtrade.transform import TradeTransformer
        from un_comtrade.storage import StorageStage

        _Extractor.kind = StageKind.EXTRACT
        _Extractor.name = "extract_trade"

        transformer = TradeTransformer()
        storage_stage = StorageStage(
            backend=StorageBackend.PARQUET,
            config=StorageConfig(root=str(tmp_root)),
        )

        from un_comtrade.etl import ETLPipeline, StageSpec

        pipeline = ETLPipeline(
            name="parquet_ingest",
            stages=(
                StageSpec(
                    name="extract_trade",
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: _Extractor(),
                ),
                StageSpec(
                    name="transform_trade",
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name="store_parquet",
                    kind=StageKind.STORAGE,
                    factory=lambda ctx: storage_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)

        assert result.status.value == "success"
        assert isinstance(result.output, StorageResult)
        # Two records: 2022 and 2023 — both share
        # reporter=699 / frequency=A, so they're in
        # DIFFERENT partitions (different ref_year).
        assert result.output.record_count == 2
        assert len(result.output.partitions) == 2

    def test_pipeline_with_custom_collector(self, tmp_root):
        """End-to-end via a captured storage that
        records the canonical dataset."""
        captured_dataset = []

        class _CapturingStage:
            """A custom storage stage that captures
            the dataset AND delegates to the real
            ParquetWriter so the file is actually
            written."""
            from un_comtrade.etl import StageKind as _SK

            name = "store"
            kind = _SK.STORAGE

            def __init__(self) -> None:
                self._writer = ParquetWriter()

            def __call__(self, source, context):
                captured_dataset.append(source)
                from un_comtrade.storage import (
                    StorageConfig,
                )

                config = StorageConfig(root=str(tmp_root))
                return self._writer.store(source, config)

        from un_comtrade.etl import (
            ETLPipeline,
            StageKind,
            StageSpec,
        )
        from un_comtrade.transform import TradeTransformer

        raw = _baseline_raw_record()
        transformer = TradeTransformer()

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
                    factory=lambda ctx: _CapturingStage(),
                ),
            ),
        )
        result = pipeline.run(source=[raw])
        assert result.status.value == "success"
        # The storage stage received a CanonicalDataset.
        assert isinstance(captured_dataset[0], CanonicalDataset)


# ---------------------------------------------------------------------------
# TestParquetSchemaPreservation
# ---------------------------------------------------------------------------


class TestParquetSchemaPreservation:
    def test_same_schema_across_writes(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        result1 = writer.store(
            dataset, StorageConfig(root=str(tmp_root / "run1"))
        )
        result2 = writer.store(
            dataset, StorageConfig(root=str(tmp_root / "run2"))
        )

        path1 = list(result1.partitions.values())[0][0]
        path2 = list(result2.partitions.values())[0][0]

        table1 = pq.read_table(path1)
        table2 = pq.read_table(path2)
        assert table1.schema.names == table2.schema.names
        for i, name in enumerate(table1.schema.names):
            assert (
                table1.schema.field(i).type
                == table2.schema.field(i).type
            )

    def test_schema_matches_canonical_schema(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        result = writer.store(dataset, StorageConfig(root=str(tmp_root)))

        path = list(result.partitions.values())[0][0]
        table = pq.read_table(path)
        # The persisted table's schema equals the
        # canonical schema.
        canonical = parquet_schema()
        assert table.schema.names == canonical.names
        for i, name in enumerate(canonical.names):
            assert table.schema.field(i).type == canonical.field(i).type


# ---------------------------------------------------------------------------
# TestParquetPartitioning
# ---------------------------------------------------------------------------


class TestParquetPartitioning:
    def test_one_file_per_partition(self, tmp_root):
        raws = [
            _baseline_raw_record(
                reporterCode=699, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
            _baseline_raw_record(
                reporterCode=699, refYear=2022,
                refPeriodId=20220102, period="2022",
            ),
            _baseline_raw_record(
                reporterCode=699, refYear=2023,
                refPeriodId=20230101, period="2023",
            ),
            _baseline_raw_record(
                reporterCode=156, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
        ]
        parsed = TradeParser(log_skipped=False).parse_records(raws).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        # 3 distinct partition keys.
        assert len(result.partitions) == 3
        # 3 files (one per partition).
        all_paths = [
            p for paths in result.partitions.values() for p in paths
        ]
        assert len(all_paths) == 3

    def test_partition_keys_match_strategy(self, tmp_root):
        # Default strategy: (reporter, year, frequency).
        raws = [
            _baseline_raw_record(
                reporterCode=699, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
            _baseline_raw_record(
                reporterCode=699, refYear=2023,
                refPeriodId=20230101, period="2023",
            ),
            _baseline_raw_record(
                reporterCode=156, refYear=2022,
                refPeriodId=20220101, period="2022",
            ),
        ]
        parsed = TradeParser(log_skipped=False).parse_records(raws).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        keys = set(result.partitions.keys())
        # All records share frequency="A".
        assert (699, 2022, "A") in keys
        assert (699, 2023, "A") in keys
        assert (156, 2022, "A") in keys

    def test_partition_paths_use_strategy_format(self, tmp_root):
        # Default path_template is the Hive-style
        # `{key_0}/{key_1}/{key_2}/{dataset_name}{ext}`.
        # Single-partition records land at
        # `<root>/699/2022/A/my_dataset.parquet`.
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed), name="my_dataset")

        writer = ParquetWriter()
        config = StorageConfig(root=str(tmp_root))
        result = writer.store(dataset, config)

        all_paths = [
            p for paths in result.partitions.values() for p in paths
        ]
        for p in all_paths:
            assert Path(p).name == "my_dataset.parquet"
            # Hive-style parent dirs.
            assert Path(p).parent.name == "A"
            assert Path(p).parent.parent.name == "2022"
            assert Path(p).parent.parent.parent.name == "699"


# ---------------------------------------------------------------------------
# TestParquetEdgeCases
# ---------------------------------------------------------------------------


class TestParquetEdgeCases:
    def test_single_record_single_partition(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        result = writer.store(dataset, StorageConfig(root=str(tmp_root)))
        assert len(result.partitions) == 1
        assert result.record_count == 1

    def test_overwrite_existing_file(self, tmp_root):
        # Write twice to the same root: the second
        # write succeeds (overwrite is the default
        # behaviour of `pq.write_table`).
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        result1 = writer.store(dataset, StorageConfig(root=str(tmp_root)))
        result2 = writer.store(dataset, StorageConfig(root=str(tmp_root)))
        # Both succeeded.
        assert result1.byte_size is not None
        assert result2.byte_size is not None
        # Files still exist.
        for paths in result2.partitions.values():
            for p in paths:
                assert Path(p).exists()

    def test_parquet_schema_version_in_metadata(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        result = writer.store(dataset, StorageConfig(root=str(tmp_root)))
        assert (
            result.metadata.extra["parquet_schema_version"]
            == "1.0.0"
        )

    def test_destination_equals_root(self, tmp_root):
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        result = writer.store(dataset, StorageConfig(root=str(tmp_root)))
        assert result.destination == str(tmp_root)
        assert result.metadata.destination == str(tmp_root)

    def test_records_in_root_subdirectory(self, tmp_root):
        # The writer should create any missing
        # parent directories under root.
        nested_root = tmp_root / "deep" / "nested" / "path"
        raw = _baseline_raw_record()
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))

        writer = ParquetWriter()
        result = writer.store(
            dataset, StorageConfig(root=str(nested_root))
        )
        assert nested_root.exists()
        all_paths = [
            p for paths in result.partitions.values() for p in paths
        ]
        for p in all_paths:
            assert Path(p).exists()

    def test_writer_repr(self):
        writer = ParquetWriter()
        r = repr(writer)
        assert "ParquetWriter" in r
        assert "parquet" in r


# ---------------------------------------------------------------------------
# Cleanup fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_root():
    """Yield a fresh temp directory and clean up
    after the test."""
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="test_parquet_"))
    yield root
    shutil.rmtree(root, ignore_errors=True)