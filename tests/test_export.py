"""Tests for the export framework (P4-004).

Per the P4-004 task scope, the export framework
implements the export abstraction with interfaces
for CSV / JSON / Parquet / DuckDB. **No actual
storage engines are implemented** — the four
formats ship as placeholder classes that raise
`NotImplementedError`. The `CANONICAL` exporter IS
implemented (in-memory; no engine needed).

Coverage:

- `TestExportFormat` — enum membership, file
  extensions, is_engine property.
- `TestExportError` — derives from `ComtradeError`.
- `TestExportOptions` — construction, defaults, get.
- `TestExportResult` — construction, properties,
  defaults.
- `TestCanonicalExporter` — emits records in-memory;
  default format; metadata carries provenance.
- `TestPlaceholderExporters` — CSV / JSON / Parquet
  / DuckDB raise `NotImplementedError`.
- `TestExporterRegistry` — defaults, register,
  get, supported_formats, unregister.
- `TestExportStageImpl` — construction, name/kind,
  dispatch, error propagation, registry override.
- `TestDetectFormatFromPath` — file extension
  detection.
- `TestExportInPipeline` — full ETL pipeline
  (extract → transform → export) with the export
  stage.
- `TestExportEdgeCases` — empty dataset, custom
  registry, export error propagation, dataset
  type check.
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
from un_comtrade.export import (
    CANONICAL_FORMAT,
    CSVExporter,
    CanonicalExporter,
    DuckDBExporter,
    ExportError,
    ExportFormat,
    ExportOptions,
    ExportResult,
    ExportStageImpl,
    ExporterRegistry,
    JSONExporter,
    ParquetExporter,
    detect_format_from_path,
)
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dataset(
    records: tuple = (),
    *,
    name: str = "p",
    schema_version: str = "1.0.0",
) -> CanonicalDataset:
    """Build a CanonicalDataset for testing."""
    return CanonicalDataset(
        name=name,
        records=records,
        schema_version=schema_version,
        parser_name="TradeParser",
        skipped=0,
        duplicates_removed=0,
        source_count=len(records),
    )


# ---------------------------------------------------------------------------
# ExportFormat
# ---------------------------------------------------------------------------


class TestExportFormat:
    def test_five_formats(self):
        assert {f.value for f in ExportFormat} == {
            "canonical",
            "csv",
            "json",
            "parquet",
            "duckdb",
        }

    def test_canonical_value(self):
        assert ExportFormat.CANONICAL.value == "canonical"

    def test_csv_value(self):
        assert ExportFormat.CSV.value == "csv"

    def test_json_value(self):
        assert ExportFormat.JSON.value == "json"

    def test_parquet_value(self):
        assert ExportFormat.PARQUET.value == "parquet"

    def test_duckdb_value(self):
        assert ExportFormat.DUCKDB.value == "duckdb"

    def test_file_extensions(self):
        assert ExportFormat.CSV.file_extension == ".csv"
        assert ExportFormat.JSON.file_extension == ".json"
        assert ExportFormat.PARQUET.file_extension == ".parquet"
        assert ExportFormat.DUCKDB.file_extension == ".duckdb"

    def test_canonical_has_no_extension(self):
        assert ExportFormat.CANONICAL.file_extension == ""

    def test_is_engine_true_for_real_formats(self):
        assert ExportFormat.CSV.is_engine is True
        assert ExportFormat.JSON.is_engine is True
        assert ExportFormat.PARQUET.is_engine is True
        assert ExportFormat.DUCKDB.is_engine is True

    def test_is_engine_false_for_canonical(self):
        assert ExportFormat.CANONICAL.is_engine is False


# ---------------------------------------------------------------------------
# ExportError
# ---------------------------------------------------------------------------


class TestExportError:
    def test_inherits_from_comtrade_error(self):
        err = ExportError("boom")
        assert isinstance(err, ComtradeError)

    def test_message(self):
        err = ExportError("destination unwritable")
        assert str(err) == "destination unwritable"


# ---------------------------------------------------------------------------
# ExportOptions
# ---------------------------------------------------------------------------


class TestExportOptions:
    def test_minimal_construction(self):
        opts = ExportOptions()
        assert opts.values == {}

    def test_with_values(self):
        opts = ExportOptions(values={"destination": "/tmp/x.csv"})
        assert opts.values["destination"] == "/tmp/x.csv"

    def test_get_default(self):
        opts = ExportOptions()
        assert opts.get("destination") is None
        assert opts.get("destination", "/default") == "/default"

    def test_get_existing(self):
        opts = ExportOptions(values={"key": "value"})
        assert opts.get("key") == "value"

    def test_immutable(self):
        opts = ExportOptions(values={"a": 1})
        with pytest.raises(Exception):
            opts.values = {"b": 2}  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExportResult
# ---------------------------------------------------------------------------


class TestExportResult:
    def test_minimal_construction(self):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 27, tzinfo=timezone.utc)
        result = ExportResult(
            format=ExportFormat.CANONICAL,
            destination="<in-memory>",
            record_count=10,
            byte_size=None,
            exported_at=ts,
        )
        assert result.format is ExportFormat.CANONICAL
        assert result.destination == "<in-memory>"
        assert result.record_count == 10
        assert result.byte_size is None
        assert result.metadata == {}

    def test_empty_property(self):
        from datetime import datetime, timezone

        ts = datetime(2026, 6, 27, tzinfo=timezone.utc)
        empty = ExportResult(
            format=ExportFormat.CANONICAL,
            destination="<in-memory>",
            record_count=0,
            byte_size=None,
            exported_at=ts,
        )
        non_empty = ExportResult(
            format=ExportFormat.CANONICAL,
            destination="<in-memory>",
            record_count=5,
            byte_size=None,
            exported_at=ts,
        )
        assert empty.empty is True
        assert non_empty.empty is False


# ---------------------------------------------------------------------------
# CanonicalExporter
# ---------------------------------------------------------------------------


class TestCanonicalExporter:
    def test_format_attribute(self):
        exporter = CanonicalExporter()
        assert exporter.format is ExportFormat.CANONICAL

    def test_export_returns_export_result(self):
        dataset = _make_dataset(records=("r1", "r2", "r3"))
        exporter = CanonicalExporter()
        result = exporter.export(dataset)
        assert isinstance(result, ExportResult)
        assert result.format is ExportFormat.CANONICAL
        assert result.record_count == 3

    def test_export_default_destination(self):
        dataset = _make_dataset()
        exporter = CanonicalExporter()
        result = exporter.export(dataset)
        assert result.destination == "<in-memory>"

    def test_export_custom_destination(self):
        dataset = _make_dataset()
        exporter = CanonicalExporter()
        opts = ExportOptions(values={"destination": "/custom/path"})
        result = exporter.export(dataset, options=opts)
        assert result.destination == "/custom/path"

    def test_export_no_options_works(self):
        dataset = _make_dataset()
        exporter = CanonicalExporter()
        result = exporter.export(dataset, options=None)
        assert isinstance(result, ExportResult)

    def test_export_metadata_carries_provenance(self):
        dataset = _make_dataset()
        exporter = CanonicalExporter()
        result = exporter.export(dataset)
        assert result.metadata["schema_version"] == "1.0.0"
        assert result.metadata["parser_name"] == "TradeParser"

    def test_export_byte_size_is_none(self):
        dataset = _make_dataset()
        exporter = CanonicalExporter()
        result = exporter.export(dataset)
        assert result.byte_size is None

    def test_export_timestamp_set(self):
        dataset = _make_dataset()
        exporter = CanonicalExporter()
        result = exporter.export(dataset)
        assert result.exported_at is not None
        assert result.exported_at.tzinfo is not None


# ---------------------------------------------------------------------------
# Placeholder exporters (CSV / JSON / Parquet / DuckDB)
# ---------------------------------------------------------------------------


class TestPlaceholderExporters:
    def test_csv_exporter_format(self):
        assert CSVExporter().format is ExportFormat.CSV

    def test_json_exporter_format(self):
        assert JSONExporter().format is ExportFormat.JSON

    def test_parquet_exporter_format(self):
        assert ParquetExporter().format is ExportFormat.PARQUET

    def test_duckdb_exporter_format(self):
        assert DuckDBExporter().format is ExportFormat.DUCKDB

    def test_csv_exporter_raises_not_implemented(self):
        exporter = CSVExporter()
        with pytest.raises(NotImplementedError, match="CSV"):
            exporter.export(_make_dataset())

    def test_json_exporter_raises_not_implemented(self):
        exporter = JSONExporter()
        with pytest.raises(NotImplementedError, match="json"):
            exporter.export(_make_dataset())

    def test_parquet_exporter_raises_not_implemented(self):
        exporter = ParquetExporter()
        with pytest.raises(NotImplementedError, match="parquet"):
            exporter.export(_make_dataset())

    def test_duckdb_exporter_raises_not_implemented(self):
        exporter = DuckDBExporter()
        with pytest.raises(NotImplementedError, match="duckdb"):
            exporter.export(_make_dataset())


# ---------------------------------------------------------------------------
# ExporterRegistry
# ---------------------------------------------------------------------------


class TestExporterRegistry:
    def test_default_registry_has_all_formats(self):
        registry = ExporterRegistry()
        supported = registry.supported_formats()
        assert ExportFormat.CANONICAL in supported
        assert ExportFormat.CSV in supported
        assert ExportFormat.JSON in supported
        assert ExportFormat.PARQUET in supported
        assert ExportFormat.DUCKDB in supported

    def test_get_canonical(self):
        registry = ExporterRegistry()
        exporter = registry.get(ExportFormat.CANONICAL)
        assert isinstance(exporter, CanonicalExporter)

    def test_get_csv_placeholder(self):
        registry = ExporterRegistry()
        exporter = registry.get(ExportFormat.CSV)
        assert isinstance(exporter, CSVExporter)

    def test_get_unknown_format_raises(self):
        registry = ExporterRegistry()
        registry.unregister(ExportFormat.JSON)
        with pytest.raises(ExportError, match="json"):
            registry.get(ExportFormat.JSON)

    def test_register_overrides(self):
        registry = ExporterRegistry()
        # Override the CSV placeholder with a custom exporter.
        class _CustomCSV:
            format = ExportFormat.CSV

            def export(self, dataset, options=None):
                return ExportResult(
                    format=ExportFormat.CSV,
                    destination="custom",
                    record_count=dataset.count,
                    byte_size=42,
                    exported_at=options.get("now"),
                )

        registry.register(ExportFormat.CSV, _CustomCSV())
        exporter = registry.get(ExportFormat.CSV)
        assert isinstance(exporter, _CustomCSV)

    def test_register_rejects_non_format(self):
        registry = ExporterRegistry()
        with pytest.raises(TypeError, match="ExportFormat"):
            registry.register("csv", CanonicalExporter())  # type: ignore[arg-type]

    def test_register_rejects_invalid_exporter(self):
        registry = ExporterRegistry()

        class _BadExporter:
            pass

        with pytest.raises(TypeError, match="export"):
            registry.register(ExportFormat.CSV, _BadExporter())  # type: ignore[arg-type]

    def test_supported_formats_returns_tuple(self):
        registry = ExporterRegistry()
        supported = registry.supported_formats()
        assert isinstance(supported, tuple)
        assert len(supported) == 5

    def test_unregister(self):
        registry = ExporterRegistry()
        registry.unregister(ExportFormat.CSV)
        assert ExportFormat.CSV not in registry.supported_formats()

    def test_unregister_unknown_raises(self):
        registry = ExporterRegistry()
        registry.unregister(ExportFormat.CSV)
        with pytest.raises(ExportError):
            registry.unregister(ExportFormat.CSV)

    def test_constructor_with_initial_exporters(self):
        # Initial exporters passed at construction time
        # override the defaults.

        class _CustomJSON:
            format = ExportFormat.JSON

            def export(self, dataset, options=None):
                return ExportResult(
                    format=ExportFormat.JSON,
                    destination="custom",
                    record_count=dataset.count,
                    byte_size=None,
                    exported_at=dataset.extracted_at,
                )

        registry = ExporterRegistry(
            exporters={ExportFormat.JSON: _CustomJSON()},
        )
        assert isinstance(registry.get(ExportFormat.JSON), _CustomJSON)
        # CSV still uses the default placeholder.
        assert isinstance(registry.get(ExportFormat.CSV), CSVExporter)


# ---------------------------------------------------------------------------
# ExportStageImpl
# ---------------------------------------------------------------------------


class TestExportStageImpl:
    def test_default_construction(self):
        stage = ExportStageImpl()
        assert stage.format is ExportFormat.CANONICAL
        assert isinstance(stage.registry, ExporterRegistry)

    def test_with_format(self):
        stage = ExportStageImpl(format=ExportFormat.CSV)
        assert stage.format is ExportFormat.CSV

    def test_with_options(self):
        opts = ExportOptions(values={"destination": "/tmp/x.csv"})
        stage = ExportStageImpl(
            format=ExportFormat.CSV, options=opts
        )
        assert stage.options is opts

    def test_invalid_format_rejected(self):
        with pytest.raises(TypeError, match="ExportFormat"):
            ExportStageImpl(format="csv")  # type: ignore[arg-type]

    def test_name_property(self):
        assert ExportStageImpl().name == "export_canonical"
        assert ExportStageImpl(format=ExportFormat.CSV).name == "export_csv"
        assert ExportStageImpl(format=ExportFormat.JSON).name == "export_json"
        assert ExportStageImpl(format=ExportFormat.PARQUET).name == "export_parquet"
        assert ExportStageImpl(format=ExportFormat.DUCKDB).name == "export_duckdb"

    def test_kind_property(self):
        assert ExportStageImpl().kind is StageKind.EXPORT

    def test_call_with_canonical_dataset(self):
        stage = ExportStageImpl()
        dataset = _make_dataset(records=("r1", "r2"))
        ctx = PipelineContext(pipeline_name="p")
        result = stage(source=dataset, context=ctx)
        assert isinstance(result, ExportResult)
        assert result.record_count == 2

    def test_call_updates_context_records_out(self):
        stage = ExportStageImpl()
        dataset = _make_dataset(records=("r1", "r2", "r3"))
        ctx = PipelineContext(pipeline_name="p")
        stage(source=dataset, context=ctx)
        assert ctx.records_out == 3

    def test_call_with_bad_source_raises(self):
        stage = ExportStageImpl()
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(ExportError, match="CanonicalDataset"):
            stage(source={"not": "a dataset"}, context=ctx)

    def test_call_with_unknown_format_raises(self):
        registry = ExporterRegistry()
        registry.unregister(ExportFormat.PARQUET)
        stage = ExportStageImpl(
            format=ExportFormat.PARQUET, registry=registry
        )
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(ExportError):
            stage(source=_make_dataset(), context=ctx)

    def test_call_with_placeholder_raises_export_error(self):
        # The placeholder raises NotImplementedError;
        # ExportStageImpl translates it to ExportError.
        stage = ExportStageImpl(format=ExportFormat.CSV)
        ctx = PipelineContext(pipeline_name="p")
        with pytest.raises(ExportError, match="placeholder"):
            stage(source=_make_dataset(), context=ctx)
        assert any(
            "placeholder" in e or "not yet implemented" in e
            for e in ctx.errors
        )

    def test_with_custom_registry(self):
        class _CustomCanonical:
            format = ExportFormat.CANONICAL

            def __init__(self):
                self.calls = []

            def export(self, dataset, options=None):
                self.calls.append(dataset)
                return ExportResult(
                    format=ExportFormat.CANONICAL,
                    destination="custom",
                    record_count=dataset.count,
                    byte_size=None,
                    exported_at=dataset.extracted_at,
                )

        custom = _CustomCanonical()
        registry = ExporterRegistry(
            exporters={ExportFormat.CANONICAL: custom},
        )
        stage = ExportStageImpl(registry=registry)
        ctx = PipelineContext(pipeline_name="p")
        stage(source=_make_dataset(), context=ctx)
        assert custom.calls == [_make_dataset()]

    def test_repr(self):
        stage = ExportStageImpl(format=ExportFormat.CSV)
        r = repr(stage)
        assert "ExportStageImpl" in r
        assert "csv" in r


# ---------------------------------------------------------------------------
# detect_format_from_path
# ---------------------------------------------------------------------------


class TestDetectFormatFromPath:
    def test_csv_path(self):
        assert detect_format_from_path("/tmp/trade.csv") is ExportFormat.CSV

    def test_json_path(self):
        assert detect_format_from_path("/tmp/trade.json") is ExportFormat.JSON

    def test_parquet_path(self):
        assert (
            detect_format_from_path("/tmp/trade.parquet")
            is ExportFormat.PARQUET
        )

    def test_duckdb_path(self):
        assert (
            detect_format_from_path("/tmp/trade.duckdb")
            is ExportFormat.DUCKDB
        )

    def test_uppercase_extension(self):
        assert detect_format_from_path("/tmp/trade.CSV") is ExportFormat.CSV

    def test_unknown_extension(self):
        assert detect_format_from_path("/tmp/trade.txt") is None

    def test_no_extension(self):
        assert detect_format_from_path("/tmp/trade") is None

    def test_empty_path(self):
        assert detect_format_from_path("") is None

    def test_path_with_directory(self):
        assert (
            detect_format_from_path("/var/data/v1/trade_2022.parquet")
            is ExportFormat.PARQUET
        )


# ---------------------------------------------------------------------------
# End-to-end ETL pipeline integration
# ---------------------------------------------------------------------------


class TestExportInPipeline:
    def test_full_pipeline_with_canonical_export(self):
        """Extract → Transform → Export (canonical)."""
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

        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

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
                    name="export_canonical",
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)

        assert result.status is PipelineStatus.SUCCESS
        assert isinstance(result.output, ExportResult)
        assert result.output.record_count == 1

    def test_pipeline_with_placeholder_exporter_fails(self):
        """CSV placeholder raises ExportError → pipeline
        records FAILED status."""
        raw_records: list = []

        class _Extractor:
            name = "extract"
            kind = StageKind.EXTRACT

            def __call__(self, source, c):
                return raw_records

        class _Transformer:
            name = "transform"
            kind = StageKind.TRANSFORM

            def __call__(self, source, c):
                from un_comtrade.transform import CanonicalDataset
                return CanonicalDataset(name="p", records=())

        export_stage = ExportStageImpl(format=ExportFormat.CSV)

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
                    factory=lambda ctx: _Transformer(),
                ),
                StageSpec(
                    name="export",
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)

        assert result.status is PipelineStatus.FAILED
        assert any("placeholder" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestExportEdgeCases:
    def test_empty_dataset_exports_zero_records(self):
        exporter = CanonicalExporter()
        dataset = _make_dataset(records=())
        result = exporter.export(dataset)
        assert result.record_count == 0
        assert result.empty

    def test_placeholder_can_be_inspected(self):
        # Placeholders are inspectable even though
        # their `export` raises.
        for cls in (CSVExporter, JSONExporter, ParquetExporter, DuckDBExporter):
            instance = cls()
            assert instance.format.is_engine

    def test_export_stage_with_default_options(self):
        stage = ExportStageImpl()
        ctx = PipelineContext(pipeline_name="p")
        result = stage(source=_make_dataset(), context=ctx)
        assert isinstance(result, ExportResult)

    def test_optional_keyword_only_options(self):
        # ExportOptions is keyword-only via values=.
        opts = ExportOptions(values={"a": 1})
        assert opts.get("a") == 1

    def test_register_then_unregister_then_register(self):
        registry = ExporterRegistry()
        registry.unregister(ExportFormat.CSV)

        class _NewCSV:
            format = ExportFormat.CSV

            def export(self, dataset, options=None):
                return ExportResult(
                    format=ExportFormat.CSV,
                    destination="new",
                    record_count=dataset.count,
                    byte_size=None,
                    exported_at=None,
                )

        registry.register(ExportFormat.CSV, _NewCSV())
        assert isinstance(registry.get(ExportFormat.CSV), _NewCSV)

    def test_format_string_to_enum(self):
        # ExportFormat is a str Enum; callers can
        # use the string value directly.
        assert ExportFormat("csv") is ExportFormat.CSV
        assert ExportFormat("json") is ExportFormat.JSON
        assert ExportFormat("canonical") is ExportFormat.CANONICAL

    def test_format_invalid_string_raises(self):
        with pytest.raises(ValueError):
            ExportFormat("unknown_format")