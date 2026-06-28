"""Detect duplicate functionality: same function name in 2+ public modules.

Two public functions in different modules with the same name and
similar purpose may indicate duplicate functionality.
"""
import os
import sys
# Ensure parent dir is on path (this script may be invoked from tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib

modnames = [
    'un_comtrade.analytics.balance', 'un_comtrade.analytics.commodity',
    'un_comtrade.analytics.compare', 'un_comtrade.analytics.country',
    'un_comtrade.analytics.partner', 'un_comtrade.analytics.timeseries',
    'un_comtrade.async_jobs', 'un_comtrade.batch', 'un_comtrade.cache',
    'un_comtrade.client', 'un_comtrade.config', 'un_comtrade.etl',
    'un_comtrade.exceptions', 'un_comtrade.export', 'un_comtrade.extract',
    'un_comtrade.logging', 'un_comtrade.metadata', 'un_comtrade.pagination',
    'un_comtrade.parser', 'un_comtrade.query', 'un_comtrade.storage',
    'un_comtrade.storage.duckdb', 'un_comtrade.storage.file',
    'un_comtrade.storage.parquet', 'un_comtrade.storage.update',
    'un_comtrade.trade', 'un_comtrade.transform', 'un_comtrade.transport',
    'un_comtrade.models', 'un_comtrade.models.classification',
    'un_comtrade.models.country', 'un_comtrade.models.data_item',
    'un_comtrade.models.frequency', 'un_comtrade.models.hs_code',
    'un_comtrade.models.quantity_unit', 'un_comtrade.models.reference_entry',
    'un_comtrade.models.response', 'un_comtrade.models.trade',
    'un_comtrade.models.trade_flow', 'un_comtrade.models.transport_mode',
]

by_name = {}
for mname in modnames:
    try:
        mod = importlib.import_module(mname)
    except Exception:
        continue
    for name in getattr(mod, '__all__', []):
        obj = getattr(mod, name, None)
        kind = type(obj).__name__
        by_name.setdefault(name, []).append((mname, kind))


# Functions in 2+ modules with same name
print('=== Function names that appear in 2+ public modules ===')
fn_dupes = []
for name, locs in by_name.items():
    kinds = set(l[1] for l in locs)
    if 'function' in kinds and len(locs) > 1:
        fn_dupes.append((name, locs))
for name, locs in sorted(fn_dupes):
    print(f'  {name}:')
    for m, k in locs:
        print(f'    {m} ({k})')

# Constants in 2+ modules
print()
print('=== Constants that appear in 2+ public modules ===')
const_dupes = []
for name, locs in by_name.items():
    kinds = set(l[1] for l in locs)
    if kinds.issubset({'str', 'int', 'float', 'frozenset', 'tuple', 'WindowsPath'}) and len(locs) > 1:
        const_dupes.append((name, locs))
for name, locs in sorted(const_dupes):
    print(f'  {name}:')
    for m, k in locs:
        print(f'    {m} ({k})')