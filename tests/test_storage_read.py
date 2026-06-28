"""Tests for the F-001 storage read() API.

Per `012_STORAGE_SPECIFICATION.md` §11, every storage
backend exposes a `read(config) -> CanonicalDataset`
operation that reloads a previously persisted dataset.

These tests verify:
- round-trip equality for every concrete backend
- Decimal preservation
- the canonical sort order is restored on read
- the Storage Protocol declares `read`
- placeholder storages raise `NotImplementedError`
- `LocalFilesStorage` is the documented default
"""
from __future__ import annotations

import csv as _csv_stdlib
import gzip
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, '.')
sys.path.insert(0, 'tests')

from test_balance_analytics import _baseline_raw

from un_comtrade.models.trade import TradeRecord
from un_comtrade.parser import TradeParser
from un_comtrade.storage import (
    CSVWriter,
    DuckDBWriter,
    JSONWriter,
    LocalFilesStorage,
    ParquetWriter,
    Storage,
    StorageConfig,
)
from un_comtrade.storage.file import _sort_records_deterministically
from un_comtrade.transform import CanonicalDataset


ISO3 = ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'ITA', 'BRA', 'IND', 'AUS']


def _build_dataset(n: int = 20, *, deterministic_decimals: bool = True) -> CanonicalDataset:
    """Build a synthetic `CanonicalDataset` for round-trip tests."""
    raws = []
    for i in range(n):
        period = '2020' if i < n // 2 else '2021'
        flow = 'X' if i % 2 == 0 else 'M'
        # Mix float and string primary_value to test
        # Decimal coercion both ways.
        primary = (
            '12345.678901234' if deterministic_decimals else 12345.67
        )
        raws.append(_baseline_raw(
            reporterCode=(i % 5) + 1,
            reporterISO=ISO3[(i % 5)],
            partnerCode=100 + i,
            partnerISO=ISO3[i % 10],
            flowCode=flow,
            period=period,
            refYear=int(period),
            refPeriodId=int(period) * 10000 + 1,
            primaryValue=primary,
            fobvalue=primary,
        ))
    return CanonicalDataset(
        name='roundtrip',
        records=tuple(
            TradeParser(log_skipped=False).parse_records(raws).records
        ),
        schema_version='1.0',
        parser_name='TradeParser',
    )


# ---------------------------------------------------------------------------
# Protocol contract
# ---------------------------------------------------------------------------


def test_storage_protocol_declares_read():
    """The `Storage` Protocol must declare both
    `store` and `read`."""
    assert 'store' in dir(Storage)
    assert 'read' in dir(Storage)


def test_placeholder_storage_read_raises_not_implemented():
    """Concrete engines implement `read`; placeholders raise
    `NotImplementedError` to signal the engine has not landed."""
    placeholder = LocalFilesStorage()
    with pytest.raises(NotImplementedError):
        placeholder.read(StorageConfig(root='/no/such/path'))


# ---------------------------------------------------------------------------
# CSV round-trip
# ---------------------------------------------------------------------------


def test_csv_roundtrip_record_equality():
    ds_in = _build_dataset(20)
    tmp = Path(tempfile.mkdtemp(prefix='f001_test_csv_'))
    try:
        cfg = StorageConfig(root=str(tmp), overwrite=True)
        CSVWriter().store(ds_in, cfg)
        ds_out = CSVWriter().read(cfg)
        ds_in_sorted = CanonicalDataset(
            name='roundtrip',
            records=tuple(_sort_records_deterministically(list(ds_in.records))),
            schema_version='1.0',
            parser_name='TradeParser',
        )
        assert len(ds_in_sorted.records) == len(ds_out.records)
        for a, b in zip(ds_in_sorted.records, ds_out.records):
            assert a == b
    finally:
        shutil.rmtree(tmp)


def test_csv_roundtrip_preserves_decimal_precision():
    """CSV stringifies Decimal values; read() must
    round-trip the exact precision."""
    ds_in = _build_dataset(10)
    tmp = Path(tempfile.mkdtemp(prefix='f001_test_csv_dec_'))
    try:
        cfg = StorageConfig(root=str(tmp), overwrite=True)
        CSVWriter().store(ds_in, cfg)
        ds_out = CSVWriter().read(cfg)
        for a, b in zip(ds_in.records, ds_out.records):
            assert a.trade_value.primary_value == b.trade_value.primary_value
            assert type(a.trade_value.primary_value) is type(
                b.trade_value.primary_value
            )
    finally:
        shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


def test_json_roundtrip_record_equality():
    ds_in = _build_dataset(20)
    tmp = Path(tempfile.mkdtemp(prefix='f001_test_json_'))
    try:
        cfg = StorageConfig(root=str(tmp), overwrite=True)
        JSONWriter().store(ds_in, cfg)
        ds_out = JSONWriter().read(cfg)
        ds_in_sorted = CanonicalDataset(
            name='roundtrip',
            records=tuple(_sort_records_deterministically(list(ds_in.records))),
            schema_version='1.0',
            parser_name='TradeParser',
        )
        assert len(ds_in_sorted.records) == len(ds_out.records)
        for a, b in zip(ds_in_sorted.records, ds_out.records):
            assert a == b
    finally:
        shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# Parquet round-trip
# ---------------------------------------------------------------------------


def test_parquet_roundtrip_record_equality():
    pytest.importorskip("pyarrow")
    ds_in = _build_dataset(20)
    tmp = Path(tempfile.mkdtemp(prefix='f001_test_parquet_'))
    try:
        cfg = StorageConfig(root=str(tmp), overwrite=True)
        ParquetWriter().store(ds_in, cfg)
        ds_out = ParquetWriter().read(cfg)
        ds_in_sorted = CanonicalDataset(
            name='roundtrip',
            records=tuple(_sort_records_deterministically(list(ds_in.records))),
            schema_version='1.0',
            parser_name='TradeParser',
        )
        assert len(ds_in_sorted.records) == len(ds_out.records)
        for a, b in zip(ds_in_sorted.records, ds_out.records):
            assert a == b
    finally:
        shutil.rmtree(tmp)


def test_parquet_roundtrip_preserves_decimal_precision():
    pytest.importorskip("pyarrow")
    ds_in = _build_dataset(10)
    tmp = Path(tempfile.mkdtemp(prefix='f001_test_parquet_dec_'))
    try:
        cfg = StorageConfig(root=str(tmp), overwrite=True)
        ParquetWriter().store(ds_in, cfg)
        ds_out = ParquetWriter().read(cfg)
        for a, b in zip(ds_in.records, ds_out.records):
            assert a.trade_value.primary_value == b.trade_value.primary_value
    finally:
        shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# DuckDB round-trip
# ---------------------------------------------------------------------------


def test_duckdb_roundtrip_record_equality():
    pytest.importorskip("duckdb")
    ds_in = _build_dataset(20)
    tmp = Path(tempfile.mkdtemp(prefix='f001_test_duckdb_'))
    try:
        # DuckDB is a single-file backend; use a `.duckdb`
        # file inside the temp dir.
        root = tmp / 'rt.duckdb'
        cfg = StorageConfig(root=str(root), overwrite=True)
        DuckDBWriter().store(ds_in, cfg)
        ds_out = DuckDBWriter().read(cfg)
        ds_in_sorted = CanonicalDataset(
            name='roundtrip',
            records=tuple(_sort_records_deterministically(list(ds_in.records))),
            schema_version='1.0',
            parser_name='TradeParser',
        )
        assert len(ds_in_sorted.records) == len(ds_out.records)
        for a, b in zip(ds_in_sorted.records, ds_out.records):
            assert a == b
    finally:
        shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# Cross-cutting checks
# ---------------------------------------------------------------------------


def test_roundtrip_preserves_dataset_name():
    pytest.importorskip("pyarrow")
    pytest.importorskip("duckdb")
    ds_in = _build_dataset(10)
    for label, cls in [('csv', CSVWriter), ('json', JSONWriter),
                       ('parquet', ParquetWriter), ('duckdb', DuckDBWriter)]:
        tmp = Path(tempfile.mkdtemp(prefix=f'f001_name_{label}_'))
        try:
            if cls is DuckDBWriter:
                root = tmp / 'rt.duckdb'
            else:
                root = tmp
            cfg = StorageConfig(root=str(root), overwrite=True)
            cls().store(ds_in, cfg)
            ds_out = cls().read(cfg)
            assert ds_out.name == 'roundtrip'
        finally:
            shutil.rmtree(tmp)


def test_roundtrip_preserves_record_count():
    pytest.importorskip("pyarrow")
    pytest.importorskip("duckdb")
    for n in [5, 20, 100]:
        ds_in = _build_dataset(n)
        for label, cls in [('csv', CSVWriter), ('json', JSONWriter),
                           ('parquet', ParquetWriter),
                           ('duckdb', DuckDBWriter)]:
            tmp = Path(tempfile.mkdtemp(prefix=f'f001_cnt_{label}_{n}_'))
            try:
                if cls is DuckDBWriter:
                    root = tmp / 'rt.duckdb'
                else:
                    root = tmp
                cfg = StorageConfig(root=str(root), overwrite=True)
                cls().store(ds_in, cfg)
                ds_out = cls().read(cfg)
                assert len(ds_out.records) == n, (
                    f'{label} n={n}: got {len(ds_out.records)} records'
                )
            finally:
                shutil.rmtree(tmp)


def test_sort_records_deterministically_is_idempotent():
    """Sorting twice yields the same order."""
    ds = _build_dataset(20)
    sorted_once = _sort_records_deterministically(list(ds.records))
    sorted_twice = _sort_records_deterministically(sorted_once)
    assert sorted_once == sorted_twice


def test_sort_records_deterministically_handles_stubs():
    """The sort key must accept the StubObj produced
    by `_dict_to_record` (used by the updater path)
    where field types may differ from a real
    TradeRecord's."""
    from un_comtrade.storage.update import _dict_to_record

    class _Stub:
        pass

    a = _Stub()
    a.ref_period_id = 20220101
    a.reporter = _Stub()
    a.reporter.reporter_code = 1
    a.partner = _Stub()
    a.partner.partner_code = 0
    a.flow = _Stub()
    a.flow.flow_code = 'X'
    a.commodity = _Stub()
    a.commodity.commodity_code = 'TOTAL'

    b = _Stub()
    b.ref_period_id = '20220101'  # string variant
    b.reporter = _Stub()
    b.reporter.reporter_code = '1'  # string variant
    b.partner = _Stub()
    b.partner.partner_code = '0'
    b.flow = _Stub()
    b.flow.flow_code = 'X'
    b.commodity = _Stub()
    b.commodity.commodity_code = 'TOTAL'

    sorted_records = _sort_records_deterministically([b, a])
    # Sorting normalises to strings, so no TypeError.
    assert sorted_records == [b, a] or sorted_records == [a, b]


# ---------------------------------------------------------------------------
# Equality invariant (the F-001 deliverable)
# ---------------------------------------------------------------------------


def test_roundtrip_invariant_for_all_backends():
    """The F-001 invariant: for every backend,
    `read(store(ds, cfg), cfg)` equals the
    canonical-sorted `ds`.

    This is the single test that demonstrates the
    round-trip correctness.
    """
    pytest.importorskip("pyarrow")
    pytest.importorskip("duckdb")
    ds_in = _build_dataset(50)
    ds_in_sorted = CanonicalDataset(
        name='roundtrip',
        records=tuple(_sort_records_deterministically(list(ds_in.records))),
        schema_version='1.0',
        parser_name='TradeParser',
    )
    for label, cls in [('CSV', CSVWriter), ('JSON', JSONWriter),
                       ('Parquet', ParquetWriter), ('DuckDB', DuckDBWriter)]:
        tmp = Path(tempfile.mkdtemp(prefix=f'f001_inv_{label}_'))
        try:
            if cls is DuckDBWriter:
                root = tmp / 'rt.duckdb'
            else:
                root = tmp
            cfg = StorageConfig(root=str(root), overwrite=True)
            cls().store(ds_in, cfg)
            ds_out = cls().read(cfg)
            assert len(ds_out.records) == len(ds_in_sorted.records), (
                f'{label}: record count mismatch '
                f'{len(ds_out.records)} vs {len(ds_in_sorted.records)}'
            )
            for i, (a, b) in enumerate(
                zip(ds_in_sorted.records, ds_out.records)
            ):
                if a != b:
                    pytest.fail(
                        f'{label}: record {i} differs after round-trip'
                    )
        finally:
            shutil.rmtree(tmp)