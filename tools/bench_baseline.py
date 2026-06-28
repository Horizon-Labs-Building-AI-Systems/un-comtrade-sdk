"""Performance baseline harness.

Measures every major subsystem at three dataset sizes (small,
medium, large). Writes results to tools/_bench_results.json.

NOT for production use; benchmark only.
"""
import gc
import json
import os
import platform
import statistics
import sys
import time

# Ensure parent dir is on path so we can import un_comtrade
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def mem_kb():
    """Return current RSS in KB."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _mem_probe import mem_kb as _k
    return _k()


def mem_mb():
    return mem_kb() / 1024


def time_block(fn, repeat=5):
    """Run fn() `repeat` times, return mean ms + stdev."""
    times = []
    for _ in range(repeat):
        gc.collect()
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.mean(times), statistics.stdev(times) if len(times) > 1 else 0


def hw_info():
    return {
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'processor': platform.processor() or 'unknown',
        'machine': platform.machine(),
        'cpu_count': os.cpu_count(),
    }


# ---------------------------------------------------------------------------
# Helpers to build synthetic datasets
# ---------------------------------------------------------------------------

ISO3 = ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'ITA', 'BRA', 'IND', 'AUS',
        'KOR', 'MEX', 'CAN', 'RUS', 'ESP', 'NLD', 'CHE', 'TUR', 'SWE', 'POL']


def build_raw_records(n):
    """Build n raw upstream-style records (dict payloads) using
    the same shape as the existing tests' _baseline_raw helper.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))
    from test_balance_analytics import _baseline_raw
    out = []
    for i in range(n):
        reporter = (i % 20) + 1
        partner = (i // 20) + 100
        period = '2020' if i < n // 2 else '2021'
        flow = 'X' if i % 2 == 0 else 'M'
        out.append(_baseline_raw(
            reporterCode=reporter,
            reporterISO=ISO3[reporter - 1],
            partnerCode=partner,
            partnerISO=ISO3[partner % 20],
            flowCode=flow,
            period=period,
            refYear=int(period),
            refPeriodId=int(period) * 10000 + 1,
            primaryValue=100.0 + (i % 1000),
            fobvalue=100.0 + (i % 1000),
        ))
    return out


def main():
    print('=== Hardware ===')
    print(json.dumps(hw_info(), indent=2))
    print()

    sizes = {'small': 1000, 'medium': 5000, 'large': 20000}
    results = {'hardware': hw_info(), 'datasets': {}}

    # Import each module cold
    print('=== Cold import time per subpackage ===')
    cold = {}
    for sub in ['', 'analytics', 'models', 'storage', 'trade', 'transport',
                'parser', 'transform', 'etl', 'export', 'extract',
                'pagination', 'batch', 'async_jobs', 'metadata', 'client',
                'config', 'logging', 'cache', 'exceptions', 'query']:
        # remove from sys.modules
        name = f'un_comtrade.{sub}' if sub else 'un_comtrade'
        for m in [m for m in sys.modules if m == name or m.startswith(name + '.')]:
            del sys.modules[m]
        t0 = time.perf_counter()
        try:
            __import__(name)
            cold[name] = (time.perf_counter() - t0) * 1000
            print(f'  cold {name}: {cold[name]:.2f} ms')
        except Exception as e:
            cold[name] = None
            print(f'  cold {name}: FAIL {e}')
    results['cold_imports_ms'] = cold
    print()

    # Now we measure warm
    print('=== Warm import time per subpackage (cached) ===')
    warm = {}
    for name in cold:
        if cold[name] is None: continue
        t0 = time.perf_counter()
        __import__(name)
        warm[name] = (time.perf_counter() - t0) * 1000
        print(f'  warm {name}: {warm[name]:.4f} ms')
    results['warm_imports_ms'] = warm
    print()

    # Reload everything
    for m in [m for m in sys.modules if m.startswith('un_comtrade')]:
        del sys.modules[m]
    import un_comtrade
    import un_comtrade.analytics
    import un_comtrade.models
    import un_comtrade.storage
    import un_comtrade.trade
    import un_comtrade.transport
    import un_comtrade.parser
    import un_comtrade.transform
    import un_comtrade.etl
    import un_comtrade.export
    import un_comtrade.extract
    import un_comtrade.pagination
    import un_comtrade.batch
    import un_comtrade.async_jobs
    import un_comtrade.metadata
    import un_comtrade.config
    import un_comtrade.logging
    import un_comtrade.cache
    import un_comtrade.query
    from un_comtrade.client import ComtradeClient
    from un_comtrade.exceptions import ComtradeError
    from un_comtrade.parser import TradeParser, MetadataParser
    from un_comtrade.transform import CanonicalDataset
    from un_comtrade.analytics import (
        country_ranking, country_balance, country_trend,
        partner_trade_balance, top_partners, country_vs_country,
        AnalyticsEngine, Filter, Metric, Aggregation,
    )

    mem_baseline = mem_mb()
    print(f'Memory after full imports: {mem_baseline:.1f} MB')
    results['memory_after_imports_mb'] = mem_baseline
    print()

    # Client initialization
    print('=== Client initialization ===')
    def init_client():
        return ComtradeClient()
    mean, sd = time_block(init_client)
    print(f'  ComtradeClient(): {mean:.3f} ± {sd:.3f} ms')
    results['client_init_ms'] = mean
    print()

    # Dataset benchmarks
    from un_comtrade.models.trade import TradeRecord
    from decimal import Decimal

    for size_name, n in sizes.items():
        print(f'=== Dataset size: {size_name} ({n} records) ===')
        results['datasets'][size_name] = {'records': n, 'benchmarks': {}}

        # Build raw
        t0 = time.perf_counter()
        raws = build_raw_records(n)
        build_ms = (time.perf_counter() - t0) * 1000
        print(f'  Build raw records: {build_ms:.2f} ms')
        results['datasets'][size_name]['benchmarks']['build_raw_ms'] = build_ms

        # Trade parsing
        parser = TradeParser(log_skipped=False)
        t0 = time.perf_counter()
        result = parser.parse_records(raws)
        parse_ms = (time.perf_counter() - t0) * 1000
        records = result.records
        print(f'  TradeParser.parse_records: {parse_ms:.2f} ms ({n/parse_ms*1000:.0f} rec/s)')
        results['datasets'][size_name]['benchmarks']['trade_parse_ms'] = parse_ms
        results['datasets'][size_name]['benchmarks']['trade_parse_rec_per_sec'] = n / parse_ms * 1000

        # CanonicalDataset construction
        t0 = time.perf_counter()
        ds = CanonicalDataset(
            name='bench',
            records=tuple(records),
            schema_version='1.0',
            parser_name='TradeParser',
        )
        cd_ms = (time.perf_counter() - t0) * 1000
        print(f'  CanonicalDataset construction: {cd_ms:.2f} ms')
        results['datasets'][size_name]['benchmarks']['canonical_construction_ms'] = cd_ms

        # Analytics: country_balance
        t0 = time.perf_counter()
        r = country_balance(ds)
        cb_ms = (time.perf_counter() - t0) * 1000
        print(f'  country_balance: {cb_ms:.2f} ms ({len(r)} reporter rows)')
        results['datasets'][size_name]['benchmarks']['country_balance_ms'] = cb_ms

        # Analytics: country_ranking
        t0 = time.perf_counter()
        r = country_ranking(ds, by='total_trade_value', limit=10)
        cr_ms = (time.perf_counter() - t0) * 1000
        print(f'  country_ranking (top 10): {cr_ms:.2f} ms ({len(r)} rows)')
        results['datasets'][size_name]['benchmarks']['country_ranking_ms'] = cr_ms

        # Analytics: country_trend
        t0 = time.perf_counter()
        r = country_trend(ds, reporter_code=1)
        ct_ms = (time.perf_counter() - t0) * 1000
        print(f'  country_trend (reporter=1): {ct_ms:.2f} ms ({len(r.points)} trend points)')
        results['datasets'][size_name]['benchmarks']['country_trend_ms'] = ct_ms

        # Analytics: partner_trade_balance
        t0 = time.perf_counter()
        r = partner_trade_balance(ds, reporter_code=1)
        pt_ms = (time.perf_counter() - t0) * 1000
        print(f'  partner_trade_balance (reporter=1): {pt_ms:.2f} ms ({len(r)} rows)')
        results['datasets'][size_name]['benchmarks']['partner_trade_balance_ms'] = pt_ms

        # Analytics: top_partners
        t0 = time.perf_counter()
        r = top_partners(ds, reporter_code=1, limit=10)
        tp_ms = (time.perf_counter() - t0) * 1000
        print(f'  top_partners (reporter=1, top 10): {tp_ms:.2f} ms ({len(r)} rows)')
        results['datasets'][size_name]['benchmarks']['top_partners_ms'] = tp_ms

        # Analytics: compare
        t0 = time.perf_counter()
        r = country_vs_country(ds, reporter_codes=[1, 2, 3, 4, 5], breakdown_by='partner')
        cv_ms = (time.perf_counter() - t0) * 1000
        print(f'  country_vs_country (5 reporters, partner): {cv_ms:.2f} ms ({len(r.rows)} rows)')
        results['datasets'][size_name]['benchmarks']['country_vs_country_ms'] = cv_ms

        # AnalyticsEngine
        def ae_run():
            engine = (AnalyticsEngine(name='bench')
                      .add_filter(Filter.reporter(1))
                      .add_filter(Filter.flow_export())
                      .add_metric(Metric.count())
                      .add_metric(Metric.sum_primary_value())
                      .add_aggregation(Aggregation(
                          name='by_partner',
                          group_by=('partner_code',),
                          metric=Metric.sum_primary_value(),
                      )))
            return engine.run(ds)
        mean, sd = time_block(ae_run, repeat=3)
        print(f'  AnalyticsEngine.run (full): {mean:.2f} ± {sd:.2f} ms')
        results['datasets'][size_name]['benchmarks']['analytics_engine_run_ms'] = mean

        # Query Engine
        from un_comtrade.analytics._query_engine import Query
        t0 = time.perf_counter()
        result = Query(ds).filter(reporter_code=1).execute()
        qf_ms = (time.perf_counter() - t0) * 1000
        print(f'  Query.filter: {qf_ms:.2f} ms ({len(result.records)} records)')
        results['datasets'][size_name]['benchmarks']['query_filter_ms'] = qf_ms

        t0 = time.perf_counter()
        result = Query(ds).group_by('reporter_code').execute()
        qg_ms = (time.perf_counter() - t0) * 1000
        print(f'  Query.group_by: {qg_ms:.2f} ms ({len(result.groups)} groups)')
        results['datasets'][size_name]['benchmarks']['query_group_by_ms'] = qg_ms

        # Storage (DuckDB)
        if os.path.exists('_bench_duck.db'):
            try: os.remove('_bench_duck.db')
            except: pass
        from un_comtrade.storage import DuckDBWriter, StorageConfig
        t0 = time.perf_counter()
        w = DuckDBWriter()
        cfg = StorageConfig(root='_bench_duck.db', overwrite=True)
        r = w.store(ds, cfg)
        duck_ms = (time.perf_counter() - t0) * 1000
        print(f'  DuckDBWriter.store: {duck_ms:.2f} ms ({n/duck_ms*1000:.0f} rec/s)')
        results['datasets'][size_name]['benchmarks']['duckdb_write_ms'] = duck_ms
        results['datasets'][size_name]['benchmarks']['duckdb_write_rec_per_sec'] = n / duck_ms * 1000
        try: os.remove('_bench_duck.db')
        except: pass

        # Storage (Parquet)
        if os.path.exists('_bench_pq'):
            try:
                import shutil; shutil.rmtree('_bench_pq')
            except: pass
        from un_comtrade.storage import ParquetWriter
        t0 = time.perf_counter()
        w = ParquetWriter()
        cfg = StorageConfig(root='_bench_pq', overwrite=True)
        r = w.store(ds, cfg)
        pq_ms = (time.perf_counter() - t0) * 1000
        print(f'  ParquetWriter.store: {pq_ms:.2f} ms ({n/pq_ms*1000:.0f} rec/s)')
        results['datasets'][size_name]['benchmarks']['parquet_write_ms'] = pq_ms
        try:
            import shutil; shutil.rmtree('_bench_pq')
        except: pass

        # Storage (CSV)
        if os.path.exists('_bench_csv'):
            try:
                import shutil; shutil.rmtree('_bench_csv')
            except: pass
        from un_comtrade.storage import CSVWriter
        t0 = time.perf_counter()
        w = CSVWriter()
        cfg = StorageConfig(root='_bench_csv', overwrite=True)
        r = w.store(ds, cfg)
        csv_ms = (time.perf_counter() - t0) * 1000
        print(f'  CSVWriter.store: {csv_ms:.2f} ms ({n/csv_ms*1000:.0f} rec/s)')
        results['datasets'][size_name]['benchmarks']['csv_write_ms'] = csv_ms
        try:
            import shutil; shutil.rmtree('_bench_csv')
        except: pass

        # Storage (JSON)
        if os.path.exists('_bench_json'):
            try:
                import shutil; shutil.rmtree('_bench_json')
            except: pass
        from un_comtrade.storage import JSONWriter
        t0 = time.perf_counter()
        w = JSONWriter()
        cfg = StorageConfig(root='_bench_json', overwrite=True)
        r = w.store(ds, cfg)
        json_ms = (time.perf_counter() - t0) * 1000
        print(f'  JSONWriter.store: {json_ms:.2f} ms ({n/json_ms*1000:.0f} rec/s)')
        results['datasets'][size_name]['benchmarks']['json_write_ms'] = json_ms
        try:
            import shutil; shutil.rmtree('_bench_json')
        except: pass

        # Memory after this dataset
        gc.collect()
        mem_now = mem_mb()
        print(f'  Memory after {size_name}: {mem_now:.1f} MB (delta +{mem_now - mem_baseline:.1f} MB)')
        results['datasets'][size_name]['memory_mb'] = mem_now
        print()

    # Peak memory
    peak = mem_mb()
    print(f'Peak memory: {peak:.1f} MB')
    results['peak_memory_mb'] = peak

    # Save
    out = 'tools/_bench_results.json'
    with open(out, 'w') as fp:
        json.dump(results, fp, indent=2)
    print(f'Results saved to {out}')


if __name__ == '__main__':
    main()