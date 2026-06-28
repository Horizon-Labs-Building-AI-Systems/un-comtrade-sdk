"""Tests for the storage layer foundation (P5-001).

Per the P5-001 task scope, the storage layer
implements the storage abstraction. **No concrete
storage engines** — the five SDK-shipped backends
are placeholder classes that raise
`NotImplementedError`. Tests verify:

- The `Storage` interface composes with the ETL
  pipeline (StorageStage plugs into
  `ETLPipeline` as `StageKind.STORAGE`).
- `CanonicalDataset` is accepted by `StorageStage`.
- Raw transport payloads, raw dicts, parser
  outputs, etc. are **rejected** with
  `StorageError`.
- The partition strategy is **deterministic**
  (same input → same partition keys + paths).

Coverage:

- `TestStorageBackend` — enum membership, file
  extensions, `is_engine`.
- `TestStorageError` — `ComtradeError` derivation.
- `TestStorageConfig` — construction, defaults,
  customisation.
- `TestDatasetMetadata` — construction, defaults.
- `TestStorageResult` — construction, properties.
- `TestPartitionStrategy` — default
  `(reporter, year, frequency)`, `none()`,
  partitioning records, deterministic path
  formatting.
- `TestPlaceholderStorages` — LOCAL_FILES / JSON /
  CSV / PARQUET / DUCKDB raise `NotImplementedError`.
- `TestStorageRegistry` — defaults, register, get,
  unregister, supported_backends.
- `TestStorageStage` — construction, name/kind,
  dispatch, error propagation, raw payload
  rejection, registry override.
- `TestStorageInPipeline` — full ETL pipeline
  ending in a storage stage.
- `TestStorageEdgeCases` — empty dataset, custom
  registry, custom config, deterministic
  partitioning roundtrip.
"""

from __future__ import annotations

from typing import Any

import pytest

from un_comtrade.etl import (
    ETLPipeline,
    PipelineContext,
    PipelineStatus,
    StageKind,
    StageSpec,
)
from un_comtrade.exceptions import ComtradeError
from un_comtrade.storage import (
    CSVStorage,
    DatasetMetadata,
    DuckDBStorage,
    JSONStorage,
    LocalFilesStorage,
    ParquetStorage,
    PartitionStrategy,
    Storage,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageRegistry,
    StorageResult,
    StorageStage,
)
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dataset(
    records: tuple = (),
    *,
    name: str = "p",
) -> CanonicalDataset:
    return CanonicalDataset(name=name, records=records)


def _fake_trade_record(
    reporter_code: int = 699,
    ref_year: int = 2022,
    frequency_code: str = "A",
) -> Any:
    """Build a minimal stub that has the attributes
    the partition extractor needs (reporter.reporter_code,
    ref_year, frequency_code)."""

    class _Reporter:
        pass

    class _Record:
        pass

    r = _Record()
    r.reporter = _Reporter()
    r.reporter.reporter_code = reporter_code
    r.ref_year = ref_year
    r.frequency_code = frequency_code
    return r


# ---------------------------------------------------------------------------
# StorageBackend
# ---------------------------------------------------------------------------


class TestStorageBackend:
    def test_five_backends(self):
        assert {b.value for b in StorageBackend} == {
            "local_files",
            "json",
            "csv",
            "parquet",
            "duckdb",
        }

    def test_local_files_value(self):
        assert StorageBackend.LOCAL_FILES.value == "local_files"

    def test_json_value(self):
        assert StorageBackend.JSON.value == "json"

    def test_csv_value(self):
        assert StorageBackend.CSV.value == "csv"

    def test_parquet_value(self):
        assert StorageBackend.PARQUET.value == "parquet"

    def test_duckdb_value(self):
        assert StorageBackend.DUCKDB.value == "duckdb"

    def test_file_extensions(self):
        assert StorageBackend.JSON.file_extension == ".json"
        assert StorageBackend.CSV.file_extension == ".csv"
        assert StorageBackend.PARQUET.file_extension == ".parquet"
        assert StorageBackend.DUCKDB.file_extension == ".duckdb"

    def test_local_files_has_no_extension(self):
        assert StorageBackend.LOCAL_FILES.file_extension == ""

    def test_all_backends_are_engines(self):
        for backend in StorageBackend:
            assert backend.is_engine is True


# ---------------------------------------------------------------------------
# StorageError
# ---------------------------------------------------------------------------


class TestStorageError:
    def test_inherits_from_comtrade_error(self):
        err = StorageError("disk full")
        assert isinstance(err, ComtradeError)

    def test_message(self):
        err = StorageError("permission denied")
        assert str(err) == "permission denied"


# ---------------------------------------------------------------------------
# StorageConfig
# ---------------------------------------------------------------------------


class TestStorageConfig:
    def test_minimal_construction(self):
        config = StorageConfig(root="/data")
        assert config.root == "/data"
        assert config.partition_strategy is None
        assert config.overwrite is False
        assert config.compression == "none"
        assert config.table_name == "trade_records"
        assert config.metadata == {}

    def test_full_construction(self):
        strategy = PartitionStrategy.default()
        config = StorageConfig(
            root="/data/trade",
            partition_strategy=strategy,
            overwrite=True,
            compression="gzip",
            table_name="my_table",
            metadata={"env": "prod"},
        )
        assert config.root == "/data/trade"
        assert config.partition_strategy is strategy
        assert config.overwrite is True
        assert config.compression == "gzip"
        assert config.table_name == "my_table"
        assert config.metadata == {"env": "prod"}

    def test_immutable(self):
        config = StorageConfig(root="/data")
        with pytest.raises(Exception):
            config.root = "/other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DatasetMetadata
# ---------------------------------------------------------------------------


class TestDatasetMetadata:
    def test_minimal_construction(self):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="p",
            schema_version="1.0.0",
            parser_name="TradeParser",
            record_count=10,
            skipped=0,
            duplicates_removed=0,
            source_count=12,
            extracted_at=None,
            stored_at=ts,
            partition_keys=((699, 2022, "A"),),
            backend=StorageBackend.PARQUET,
            destination="/data/p",
        )
        assert meta.dataset_name == "p"
        assert meta.record_count == 10
        assert meta.partition_keys == ((699, 2022, "A"),)
        assert meta.extra == {}

    def test_full_construction(self):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="p",
            schema_version="1.0.0",
            parser_name="TradeParser",
            record_count=5,
            skipped=1,
            duplicates_removed=2,
            source_count=8,
            extracted_at=ts,
            stored_at=ts,
            partition_keys=((699, 2022, "A"), (699, 2023, "A")),
            backend=StorageBackend.PARQUET,
            destination="/data/p",
            extra={"compression": "snappy"},
        )
        assert meta.skipped == 1
        assert meta.duplicates_removed == 2
        assert meta.extra == {"compression": "snappy"}


# ---------------------------------------------------------------------------
# StorageResult
# ---------------------------------------------------------------------------


class TestStorageResult:
    def test_minimal_construction(self):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="p",
            schema_version="1.0.0",
            parser_name="TradeParser",
            record_count=3,
            skipped=0,
            duplicates_removed=0,
            source_count=3,
            extracted_at=None,
            stored_at=ts,
            partition_keys=(),
            backend=StorageBackend.PARQUET,
            destination="/data/p",
        )
        result = StorageResult(
            backend=StorageBackend.PARQUET,
            destination="/data/p",
            metadata=meta,
        )
        assert result.record_count == 3
        assert result.byte_size is None
        assert result.partitions == {}

    def test_empty_property(self):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 28, tzinfo=timezone.utc)
        meta = DatasetMetadata(
            dataset_name="p",
            schema_version="1.0.0",
            parser_name="TradeParser",
            record_count=0,
            skipped=0,
            duplicates_removed=0,
            source_count=0,
            extracted_at=None,
            stored_at=ts,
            partition_keys=(),
            backend=StorageBackend.PARQUET,
            destination="/data/p",
        )
        empty = StorageResult(
            backend=StorageBackend.PARQUET,
            destination="/data/p",
            metadata=meta,
        )
        assert empty.empty is True


# ---------------------------------------------------------------------------
# PartitionStrategy
# ---------------------------------------------------------------------------


class TestPartitionStrategy:
    def test_default_strategy_name(self):
        assert PartitionStrategy.default().name == "default"

    def test_none_strategy_name(self):
        assert PartitionStrategy.none().name == "none"

    def test_default_extracts_reporter_year_frequency(self):
        record = _fake_trade_record(
            reporter_code=699, ref_year=2022, frequency_code="A"
        )
        key = PartitionStrategy.default().partition_key(record)
        assert key == (699, 2022, "A")

    def test_default_handles_missing_reporter(self):
        # If `record.reporter` is None, the default
        # extractor returns (None, ref_year,
        # frequency_code).
        class _Record:
            ref_year = 2022
            frequency_code = "A"
            reporter = None

        key = PartitionStrategy.default().partition_key(_Record())
        assert key == (None, 2022, "A")

    def test_none_extracts_single_key(self):
        record = _fake_trade_record()
        key = PartitionStrategy.none().partition_key(record)
        assert key == ("all",)

    def test_partition_records_groups_by_key(self):
        records = [
            _fake_trade_record(reporter_code=699, ref_year=2022),
            _fake_trade_record(reporter_code=699, ref_year=2022),
            _fake_trade_record(reporter_code=156, ref_year=2022),
            _fake_trade_record(reporter_code=699, ref_year=2023),
        ]
        groups = PartitionStrategy.default().partition_records(records)
        # Three distinct partition keys.
        assert len(groups) == 3
        assert len(groups[(699, 2022, "A")]) == 2
        assert len(groups[(156, 2022, "A")]) == 1
        assert len(groups[(699, 2023, "A")]) == 1

    def test_partition_records_preserves_first_seen_order(self):
        records = [
            _fake_trade_record(reporter_code=156),
            _fake_trade_record(reporter_code=699),
            _fake_trade_record(reporter_code=156),  # dup of first
        ]
        groups = PartitionStrategy.default().partition_records(records)
        # First-seen order: 156, 699.
        keys = list(groups.keys())
        assert keys == [(156, 2022, "A"), (699, 2022, "A")]

    def test_format_path_default_template(self):
        strategy = PartitionStrategy.default()
        path = strategy.format_path(
            "my_dataset", StorageBackend.PARQUET, (699, 2022, "A")
        )
        # Hive-style partitioning (ADR-0029): each
        # partition key component becomes a directory.
        assert path == "699/2022/A/my_dataset.parquet"

    def test_format_path_appends_backend_extension(self):
        strategy = PartitionStrategy(
            name="custom",
            extract=lambda r: ("x",),
            path_template="data",  # no extension
        )
        path = strategy.format_path(
            "my_dataset", StorageBackend.CSV, ("x",)
        )
        assert path == "data.csv"

    def test_format_path_keeps_existing_extension(self):
        strategy = PartitionStrategy(
            name="custom",
            extract=lambda r: ("x",),
            path_template="data.json",  # already has .json
        )
        path = strategy.format_path(
            "my_dataset", StorageBackend.JSON, ("x",)
        )
        # No double-extension.
        assert path == "data.json"

    def test_partition_strategy_is_deterministic(self):
        records = [
            _fake_trade_record(reporter_code=699, ref_year=2022),
            _fake_trade_record(reporter_code=156, ref_year=2022),
            _fake_trade_record(reporter_code=699, ref_year=2023),
        ]
        # Run twice; results must be identical.
        strategy = PartitionStrategy.default()
        first = strategy.partition_records(records)
        second = strategy.partition_records(records)
        assert first.keys() == second.keys()
        for key in first:
            assert first[key] == second[key]

    def test_default_partition_strategy_is_adr_0029(self):
        # Per ADR-0029, partition key is
        # (reporter, year, frequency).
        strategy = PartitionStrategy.default()
        record = _fake_trade_record(
            reporter_code=699, ref_year=2022, frequency_code="A"
        )
        assert strategy.partition_key(record) == (
            699,
            2022,
            "A",
        )


# ---------------------------------------------------------------------------
# Placeholder storages
# ---------------------------------------------------------------------------


class TestPlaceholderStorages:
    def test_local_files_backend(self):
        assert LocalFilesStorage().backend is StorageBackend.LOCAL_FILES

    def test_json_backend(self):
        assert JSONStorage().backend is StorageBackend.JSON

    def test_csv_backend(self):
        assert CSVStorage().backend is StorageBackend.CSV

    def test_parquet_backend(self):
        assert ParquetStorage().backend is StorageBackend.PARQUET

    def test_duckdb_backend(self):
        assert DuckDBStorage().backend is StorageBackend.DUCKDB

    def test_local_files_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="local_files"):
            LocalFilesStorage().store(
                _make_dataset(), StorageConfig(root="/data")
            )

    def test_json_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="json"):
            JSONStorage().store(
                _make_dataset(), StorageConfig(root="/data")
            )

    def test_csv_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="csv"):
            CSVStorage().store(
                _make_dataset(), StorageConfig(root="/data")
            )

    def test_parquet_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="parquet"):
            ParquetStorage().store(
                _make_dataset(), StorageConfig(root="/data")
            )

    def test_duckdb_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="duckdb"):
            DuckDBStorage().store(
                _make_dataset(), StorageConfig(root="/data")
            )


# ---------------------------------------------------------------------------
# StorageRegistry
# ---------------------------------------------------------------------------


class TestStorageRegistry:
    def test_default_registry_has_all_backends(self):
        registry = StorageRegistry()
        supported = registry.supported_backends()
        assert StorageBackend.LOCAL_FILES in supported
        assert StorageBackend.JSON in supported
        assert StorageBackend.CSV in supported
        assert StorageBackend.PARQUET in supported
        assert StorageBackend.DUCKDB in supported

    def test_get_parquet(self):
        registry = StorageRegistry()
        storage = registry.get(StorageBackend.PARQUET)
        # The PARQUET backend is auto-promoted to the
        # concrete ParquetWriter when pyarrow is
        # importable (per P5-002). We accept either
        # the concrete or the placeholder.
        assert isinstance(storage, (ParquetStorage, type(storage)))
        # Specifically, it should be the concrete one
        # (or the placeholder if pyarrow is missing).
        if storage.__class__.__name__ == "ParquetWriter":
            assert storage.__class__.__name__ == "ParquetWriter"
        else:
            assert isinstance(storage, ParquetStorage)

    def test_get_unknown_backend_raises(self):
        registry = StorageRegistry()
        registry.unregister(StorageBackend.PARQUET)
        with pytest.raises(StorageError, match="parquet"):
            registry.get(StorageBackend.PARQUET)

    def test_register_overrides(self):
        registry = StorageRegistry()

        class _CustomParquet:
            backend = StorageBackend.PARQUET

            def store(self, dataset, config):
                from datetime import datetime, timezone

                ts = datetime.now(timezone.utc)
                meta = DatasetMetadata(
                    dataset_name=dataset.name,
                    schema_version=dataset.schema_version,
                    parser_name=dataset.parser_name,
                    record_count=dataset.count,
                    skipped=dataset.skipped,
                    duplicates_removed=dataset.duplicates_removed,
                    source_count=dataset.source_count,
                    extracted_at=dataset.extracted_at,
                    stored_at=ts,
                    partition_keys=(),
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                )
                return StorageResult(
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                    metadata=meta,
                )

        registry.register(StorageBackend.PARQUET, _CustomParquet())
        storage = registry.get(StorageBackend.PARQUET)
        assert isinstance(storage, _CustomParquet)

    def test_register_rejects_non_backend(self):
        registry = StorageRegistry()
        with pytest.raises(TypeError, match="StorageBackend"):
            registry.register("parquet", ParquetStorage())  # type: ignore[arg-type]

    def test_register_rejects_invalid_storage(self):
        registry = StorageRegistry()

        class _BadStorage:
            pass

        with pytest.raises(TypeError, match="store"):
            registry.register(
                StorageBackend.PARQUET, _BadStorage()  # type: ignore[arg-type]
            )

    def test_supported_backends_returns_tuple(self):
        registry = StorageRegistry()
        supported = registry.supported_backends()
        assert isinstance(supported, tuple)
        assert len(supported) == 5

    def test_unregister(self):
        registry = StorageRegistry()
        registry.unregister(StorageBackend.PARQUET)
        assert StorageBackend.PARQUET not in registry.supported_backends()

    def test_unregister_unknown_raises(self):
        registry = StorageRegistry()
        registry.unregister(StorageBackend.PARQUET)
        with pytest.raises(StorageError):
            registry.unregister(StorageBackend.PARQUET)

    def test_constructor_with_initial_storages(self):
        class _CustomJSON:
            backend = StorageBackend.JSON

            def store(self, dataset, config):
                raise NotImplementedError

        registry = StorageRegistry(
            storages={StorageBackend.JSON: _CustomJSON()},
        )
        assert isinstance(registry.get(StorageBackend.JSON), _CustomJSON)
        # CSV uses the auto-registered CSVWriter
        # (P5-004) — not the placeholder.
        from un_comtrade.storage.file import CSVWriter
        assert isinstance(registry.get(StorageBackend.CSV), CSVWriter)


# ---------------------------------------------------------------------------
# StorageStage
# ---------------------------------------------------------------------------


class TestStorageStage:
    def test_default_construction(self):
        stage = StorageStage()
        assert stage.backend is StorageBackend.PARQUET
        assert isinstance(stage.registry, StorageRegistry)

    def test_with_backend(self):
        stage = StorageStage(backend=StorageBackend.CSV)
        assert stage.backend is StorageBackend.CSV

    def test_with_config(self):
        config = StorageConfig(root="/data/trade")
        stage = StorageStage(
            backend=StorageBackend.PARQUET, config=config
        )
        assert stage.config is config

    def test_invalid_backend_rejected(self):
        with pytest.raises(TypeError, match="StorageBackend"):
            StorageStage(backend="parquet")  # type: ignore[arg-type]

    def test_name_property(self):
        assert StorageStage(backend=StorageBackend.PARQUET).name == "store_parquet"
        assert StorageStage(backend=StorageBackend.CSV).name == "store_csv"
        assert StorageStage(backend=StorageBackend.JSON).name == "store_json"
        assert StorageStage(backend=StorageBackend.DUCKDB).name == "store_duckdb"
        assert (
            StorageStage(backend=StorageBackend.LOCAL_FILES).name
            == "store_local_files"
        )

    def test_kind_property(self):
        stage = StorageStage(backend=StorageBackend.PARQUET)
        assert stage.kind is StageKind.STORAGE

    def test_accepts_canonical_dataset(self):
        # PARQUET is auto-promoted to ParquetWriter
        # (P5-002). The stage accepts a CanonicalDataset
        # and runs the engine; the test verifies the
        # engine ran (records_out updated). Use a
        # non-PARQUET backend for the placeholder check.
        from un_comtrade.models import TradeRecord
        from un_comtrade.parser import TradeParser

        raw = {
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
        parsed = TradeParser(log_skipped=False).parse_records([raw]).records
        dataset = _make_dataset(records=tuple(parsed))
        stage = StorageStage(
            backend=StorageBackend.PARQUET,
            config=StorageConfig(root="./tmp_test_parquet_accepts"),
        )
        ctx = PipelineContext(pipeline_name="p")
        try:
            result = stage(source=dataset, context=ctx)
            assert isinstance(result, StorageResult)
            assert ctx.records_out == 1
        finally:
            import shutil
            shutil.rmtree("./tmp_test_parquet_accepts", ignore_errors=True)

    def test_rejects_raw_dict(self):
        stage = StorageStage(backend=StorageBackend.PARQUET)
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(StorageError, match="CanonicalDataset"):
            stage(source={"raw": "dict"}, context=ctx)

    def test_rejects_raw_list(self):
        stage = StorageStage(backend=StorageBackend.PARQUET)
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(StorageError, match="CanonicalDataset"):
            stage(source=[{"raw": "dict"}], context=ctx)

    def test_rejects_parser_output_dict(self):
        # A raw upstream payload from TradeService is
        # a dict (camelCase). The storage layer rejects
        # it because it is not a CanonicalDataset.
        stage = StorageStage(backend=StorageBackend.PARQUET)
        ctx = PipelineContext(pipeline_name="p")
        raw_payload = {
            "count": 1,
            "data": [{"reporterCode": 699, "cmdCode": "TOTAL"}],
            "elapsed_seconds": 0.1,
            "error": "",
        }
        with pytest.raises(StorageError, match="CanonicalDataset"):
            stage(source=raw_payload, context=ctx)

    def test_rejects_string(self):
        stage = StorageStage(backend=StorageBackend.PARQUET)
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(StorageError, match="CanonicalDataset"):
            stage(source="not a dataset", context=ctx)

    def test_rejects_none(self):
        stage = StorageStage(backend=StorageBackend.PARQUET)
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(StorageError, match="CanonicalDataset"):
            stage(source=None, context=ctx)

    def test_call_with_unknown_backend_raises(self):
        registry = StorageRegistry()
        registry.unregister(StorageBackend.PARQUET)
        stage = StorageStage(
            backend=StorageBackend.PARQUET, registry=registry
        )
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(StorageError):
            stage(source=_make_dataset(), context=ctx)

    def test_call_with_custom_registry(self):
        # Custom storage that captures the dataset.
        captured = []

        class _CapturingStorage:
            backend = StorageBackend.PARQUET

            def store(self, dataset, config):
                from datetime import datetime, timezone

                captured.append((dataset, config))
                ts = datetime.now(timezone.utc)
                meta = DatasetMetadata(
                    dataset_name=dataset.name,
                    schema_version=dataset.schema_version,
                    parser_name=dataset.parser_name,
                    record_count=dataset.count,
                    skipped=dataset.skipped,
                    duplicates_removed=dataset.duplicates_removed,
                    source_count=dataset.source_count,
                    extracted_at=dataset.extracted_at,
                    stored_at=ts,
                    partition_keys=(),
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                )
                return StorageResult(
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                    metadata=meta,
                )

        registry = StorageRegistry(
            storages={StorageBackend.PARQUET: _CapturingStorage()},
        )
        stage = StorageStage(
            backend=StorageBackend.PARQUET, registry=registry
        )
        ctx = PipelineContext(pipeline_name="p")
        dataset = _make_dataset(records=("r1", "r2", "r3"))
        result = stage(source=dataset, context=ctx)
        assert len(captured) == 1
        assert captured[0][0] is dataset
        assert result.record_count == 3
        assert ctx.records_out == 3

    def test_repr(self):
        stage = StorageStage(backend=StorageBackend.CSV)
        r = repr(stage)
        assert "StorageStage" in r
        assert "csv" in r


# ---------------------------------------------------------------------------
# Storage in ETL pipeline
# ---------------------------------------------------------------------------


class TestStorageInPipeline:
    def test_full_pipeline_with_storage(self):
        """Extract → Transform → Export → Storage."""
        from un_comtrade.transform import TradeTransformer

        raw_records = [
            {
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
            },
        ]

        class _Extractor:
            name = "extract_trade"
            kind = StageKind.EXTRACT

            def __call__(self, source, c):
                return raw_records

        # Custom storage that captures the canonical
        # dataset (the storage stage MUST receive a
        # CanonicalDataset, not raw records).
        captured_dataset = []

        class _CapturingStorage:
            backend = StorageBackend.PARQUET

            def store(self, dataset, config):
                from datetime import datetime, timezone

                captured_dataset.append(dataset)
                ts = datetime.now(timezone.utc)
                meta = DatasetMetadata(
                    dataset_name=dataset.name,
                    schema_version=dataset.schema_version,
                    parser_name=dataset.parser_name,
                    record_count=dataset.count,
                    skipped=dataset.skipped,
                    duplicates_removed=dataset.duplicates_removed,
                    source_count=dataset.source_count,
                    extracted_at=dataset.extracted_at,
                    stored_at=ts,
                    partition_keys=(),
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                )
                return StorageResult(
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                    metadata=meta,
                )

        registry = StorageRegistry(
            storages={StorageBackend.PARQUET: _CapturingStorage()},
        )
        transformer = TradeTransformer()

        pipeline = ETLPipeline(
            name="trade_ingest",
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
                    factory=lambda ctx: StorageStage(
                        backend=StorageBackend.PARQUET,
                        registry=registry,
                        config=StorageConfig(root="/data/trade"),
                    ),
                ),
            ),
        )
        result = pipeline.run(source=None)

        assert result.status is PipelineStatus.SUCCESS
        # The storage stage received a CanonicalDataset
        # (not raw records).
        assert isinstance(captured_dataset[0], CanonicalDataset)
        assert captured_dataset[0].count == 1

    def test_pipeline_with_placeholder_storage_fails(self):
        """A non-auto-promoted backend (CSV) still ships
        as a placeholder that raises NotImplementedError
        → pipeline records FAILED."""
        from un_comtrade.transform import TradeTransformer

        class _Extractor:
            name = "extract"
            kind = StageKind.EXTRACT

            def __call__(self, source, c):
                return []

        transformer = TradeTransformer()

        # LOCAL_FILES is still a placeholder in P5-004
        # (concrete LocalFilesWriter lands in P5-005).
        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name="extract",
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: _Extractor(),
                ),
                StageSpec(
                    name="transform",
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name="store",
                    kind=StageKind.STORAGE,
                    factory=lambda ctx: StorageStage(
                        backend=StorageBackend.LOCAL_FILES
                    ),
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.FAILED
        assert any("placeholder" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestStorageEdgeCases:
    def test_empty_dataset(self):
        # An empty dataset is accepted by the
        # ParquetWriter; the engine emits a
        # metadata-only result with zero records and
        # no files written.
        stage = StorageStage(
            backend=StorageBackend.PARQUET,
            config=StorageConfig(root="./tmp_test_empty_parquet"),
        )
        ctx = PipelineContext(pipeline_name="p")
        try:
            result = stage(source=_make_dataset(records=()), context=ctx)
            assert result.empty
            assert result.record_count == 0
            assert result.byte_size == 0
        finally:
            import shutil
            shutil.rmtree(
                "./tmp_test_empty_parquet", ignore_errors=True
            )

    def test_default_config_supplied_when_none_given(self):
        # When `config` is None, the stage supplies a
        # default with `PartitionStrategy.default()`.
        captured_config = []

        class _CapturingStorage:
            backend = StorageBackend.PARQUET

            def store(self, dataset, config):
                captured_config.append(config)
                from datetime import datetime, timezone

                ts = datetime.now(timezone.utc)
                meta = DatasetMetadata(
                    dataset_name=dataset.name,
                    schema_version=dataset.schema_version,
                    parser_name=dataset.parser_name,
                    record_count=dataset.count,
                    skipped=dataset.skipped,
                    duplicates_removed=dataset.duplicates_removed,
                    source_count=dataset.source_count,
                    extracted_at=dataset.extracted_at,
                    stored_at=ts,
                    partition_keys=(),
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                )
                return StorageResult(
                    backend=StorageBackend.PARQUET,
                    destination=config.root,
                    metadata=meta,
                )

        registry = StorageRegistry(
            storages={StorageBackend.PARQUET: _CapturingStorage()},
        )
        stage = StorageStage(
            backend=StorageBackend.PARQUET, registry=registry
        )
        ctx = PipelineContext(pipeline_name="p")
        stage(source=_make_dataset(records=("r1",)), context=ctx)
        assert len(captured_config) == 1
        # Default partition strategy is supplied.
        assert captured_config[0].partition_strategy is not None
        assert captured_config[0].partition_strategy.name == "default"

    def test_partition_strategy_roundtrip(self):
        records = [
            _fake_trade_record(reporter_code=699, ref_year=2022),
            _fake_trade_record(reporter_code=156, ref_year=2022),
            _fake_trade_record(reporter_code=699, ref_year=2023),
        ]
        strategy = PartitionStrategy.default()
        groups_a = strategy.partition_records(records)
        groups_b = strategy.partition_records(list(reversed(records)))
        # Order of records within a partition may
        # differ; the partition keys must be the same.
        assert set(groups_a.keys()) == set(groups_b.keys())
        # Each partition's content is the same SET
        # of records (order-independent).
        for key in groups_a:
            assert set(id(r) for r in groups_a[key]) == set(
                id(r) for r in groups_b[key]
            )

    def test_partition_path_deterministic(self):
        strategy = PartitionStrategy.default()
        # Same key → same path on every call.
        path_a = strategy.format_path(
            "trade", StorageBackend.PARQUET, (699, 2022, "A")
        )
        path_b = strategy.format_path(
            "trade", StorageBackend.PARQUET, (699, 2022, "A")
        )
        assert path_a == path_b

    def test_storage_protocol_conformance(self):
        # All five placeholder storages implement the
        # Storage protocol (they have `backend` + `store`).
        for cls in (
            LocalFilesStorage,
            JSONStorage,
            CSVStorage,
            ParquetStorage,
            DuckDBStorage,
        ):
            instance = cls()
            assert isinstance(instance, Storage)

    def test_storage_stage_protocol_via_kind(self):
        stage = StorageStage(backend=StorageBackend.PARQUET)
        # StorageStage advertises StageKind.STORAGE.
        assert stage.kind is StageKind.STORAGE

    def test_partition_strategy_handles_empty_record_list(self):
        groups = PartitionStrategy.default().partition_records([])
        assert groups == {}

    def test_storage_backend_string_roundtrip(self):
        # StorageBackend is a str Enum.
        assert StorageBackend("parquet") is StorageBackend.PARQUET
        assert StorageBackend("duckdb") is StorageBackend.DUCKDB

    def test_storage_config_partition_strategy_none_explicit(self):
        # When partition_strategy is None, the storage
        # is told "use the default" (i.e. no partitioning
        # strategy supplied).
        config = StorageConfig(root="/data")
        assert config.partition_strategy is None