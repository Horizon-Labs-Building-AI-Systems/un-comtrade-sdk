"""Per-size benchmark — run one dataset size at a time.

Use this to avoid pipeline hangs on big sizes. Run separately:
  python tools/bench_one.py small 1000
  python tools/bench_one.py medium 5000
  python tools/bench_one.py large 20000
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests'))


def main():
    size_name = sys.argv[1] if len(sys.argv) > 1 else 'small'
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    print(f'=== Dataset: {size_name} ({n} records) ===', flush=True)

    from _mem_probe import mem_mb
    from test_balance_analytics import _baseline_raw
    from un_comtrade.transform import CanonicalDataset
    from un_comtrade.parser import TradeParser

    ISO3 = ['USA','CHN','JPN','DEU','GBR','FRA','ITA','BRA','IND','AUS',
            'KOR','MEX','CAN','RUS','ESP','NLD','CHE','TUR','SWE','POL']

    # Build raw
    t0 = time.perf_counter()
    raws = []
    for i in range(n):
        reporter = (i % 20) + 1
        partner = (i // 20) + 100
        period = '2020' if i < n // 2 else '2021'
        flow = 'X' if i % 2 == 0 else 'M'
        raws.append(_baseline_raw(
            reporterCode=reporter, reporterISO=ISO3[reporter - 1],
            partnerCode=partner, partnerISO=ISO3[partner % 20],
            flowCode=flow, period=period, refYear=int(period),
            refPeriodId=int(period) * 10000 + 1,
            primaryValue=100.0 + (i % 1000), fobvalue=100.0 + (i % 1000),
        ))
    build_ms = (time.perf_counter() - t0) * 1000
    print(f'  build_raw: {build_ms:.1f} ms', flush=True)

    # Parse
    parser = TradeParser(log_skipped=False)
    t0 = time.perf_counter()
    result = parser.parse_records(raws)
    parse_ms = (time.perf_counter() - t0) * 1000
    n_parsed = len(result.records)
    print(f'  parse: {parse_ms:.1f} ms ({n_parsed} records)', flush=True)

    ds = CanonicalDataset(name='b', records=tuple(result.records), schema_version='1.0', parser_name='TradeParser')

    # Analytics
    from un_comtrade.analytics import (
        country_balance, country_ranking, country_trend,
        partner_trade_balance, top_partners, country_vs_country,
    )

    benches = {}
    for name, fn in [
        ('country_balance', lambda: country_balance(ds)),
        ('country_ranking_top10', lambda: country_ranking(ds, by='total_trade_value', limit=10)),
        ('country_trend_reporter1', lambda: country_trend(ds, reporter_code=1)),
        ('partner_trade_balance_reporter1', lambda: partner_trade_balance(ds, reporter_code=1)),
        ('top_partners_reporter1', lambda: top_partners(ds, reporter_code=1, limit=10)),
        ('country_vs_country_5', lambda: country_vs_country(ds, reporter_codes=[1,2,3,4,5], breakdown_by='partner')),
    ]:
        t0 = time.perf_counter()
        r = fn()
        ms = (time.perf_counter() - t0) * 1000
        n_rows = len(r) if isinstance(r, tuple) else (len(r.points) if hasattr(r, 'points') else (len(r.rows) if hasattr(r, 'rows') else 0))
        benches[name] = {'ms': ms, 'rows': n_rows}
        print(f'  {name}: {ms:.1f} ms ({n_rows} rows)', flush=True)

    # Storage
    from un_comtrade.storage import (
        ParquetWriter, CSVWriter, JSONWriter, StorageConfig,
    )

    # Skip DuckDB on medium/large — its row-by-row insert path is too slow
    # on synthetic data. Benchmark DuckDB only at the small size.
    storage_targets = [('parquet', ParquetWriter), ('csv', CSVWriter), ('json', JSONWriter)]
    if size_name == 'small':
        from un_comtrade.storage import DuckDBWriter
        storage_targets.insert(0, ('duckdb', DuckDBWriter))

    for label, cls in storage_targets:
        root = f'_b_{label}_{size_name}'
        try:
            import shutil
            if os.path.exists(root): shutil.rmtree(root)
            if os.path.exists(root): os.remove(root)
        except: pass
        t0 = time.perf_counter()
        try:
            w = cls()
            cfg = StorageConfig(root=root, overwrite=True)
            w.store(ds, cfg)
            ms = (time.perf_counter() - t0) * 1000
            benches[f'{label}_store'] = {'ms': ms, 'rec_per_sec': n_parsed / ms * 1000}
            print(f'  {label}_store: {ms:.1f} ms ({n_parsed/ms*1000:.0f} rec/s)', flush=True)
        except Exception as e:
            benches[f'{label}_store'] = {'error': str(e)}
            print(f'  {label}_store: FAIL {e}', flush=True)
        try:
            import shutil
            if os.path.exists(root): shutil.rmtree(root)
            if os.path.exists(root): os.remove(root)
        except: pass

    # Query Engine
    from un_comtrade.analytics._query_engine import Query
    t0 = time.perf_counter()
    r = Query(ds).filter(reporter_code=1).execute()
    ms = (time.perf_counter() - t0) * 1000
    benches['qe_filter'] = {'ms': ms, 'rec': len(r.records)}
    print(f'  qe_filter: {ms:.1f} ms ({len(r.records)} records)', flush=True)

    t0 = time.perf_counter()
    r = Query(ds).group_by('reporter_code').execute()
    ms = (time.perf_counter() - t0) * 1000
    benches['qe_group_by'] = {'ms': ms, 'groups': len(r.groups)}
    print(f'  qe_group_by: {ms:.1f} ms ({len(r.groups)} groups)', flush=True)

    # Memory after this dataset
    mem_now = mem_mb()
    print(f'  memory_now: {mem_now:.1f} MB', flush=True)
    benches['memory_mb'] = mem_now

    out = f'tools/_bench_{size_name}.json'
    with open(out, 'w') as fp:
        json.dump({'size_name': size_name, 'records_requested': n, 'records_parsed': n_parsed,
                   'build_raw_ms': build_ms, 'parse_ms': parse_ms, 'benchmarks': benches}, fp, indent=2)
    print(f'Saved to {out}')


if __name__ == '__main__':
    main()