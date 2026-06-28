"""Measure cold-import time and module footprint."""
import sys
import time


def cold_import(modname):
    """Cold-import a module; return (time_ms, modules_loaded_after)."""
    # Remove all cached un_comtrade.* modules
    to_remove = [m for m in sys.modules if m == modname or m.startswith(modname + '.')]
    for m in to_remove:
        del sys.modules[m]
    t0 = time.perf_counter()
    __import__(modname)
    dt = (time.perf_counter() - t0) * 1000
    loaded = sorted(m for m in sys.modules if m.startswith('un_comtrade'))
    return dt, loaded


def warm_import(modname):
    """Warm import (already cached)."""
    t0 = time.perf_counter()
    __import__(modname)
    return (time.perf_counter() - t0) * 1000


def main():
    # Cold top-level
    dt, loaded = cold_import('un_comtrade')
    print(f'COLD import un_comtrade: {dt:.2f} ms')
    print(f'  Modules loaded: {len(loaded)}')
    for m in loaded:
        print(f'    {m}')

    # Subpackages
    for sub in ['analytics', 'models', 'storage', 'trade', 'transport', 'parser', 'transform']:
        dt, loaded = cold_import(f'un_comtrade.{sub}')
        print(f'COLD import un_comtrade.{sub}: {dt:.2f} ms ({len(loaded)} modules)')

    # Heavy: pull everything
    for sub in ['analytics', 'models', 'storage', 'trade', 'transport',
                'parser', 'transform', 'etl', 'export', 'extract', 'pagination',
                'batch', 'async_jobs', 'metadata', 'client', 'config',
                'logging', 'cache', 'exceptions', 'query']:
        try:
            __import__(f'un_comtrade.{sub}')
        except Exception as e:
            print(f'  FAIL un_comtrade.{sub}: {e}')

    loaded = sorted(m for m in sys.modules if m.startswith('un_comtrade'))
    print(f'TOTAL un_comtrade modules loaded: {len(loaded)}')

    # Warm (cached) re-import time
    for sub in ['un_comtrade', 'un_comtrade.analytics', 'un_comtrade.models', 'un_comtrade.storage']:
        dt = warm_import(sub)
        print(f'WARM import {sub}: {dt:.4f} ms')


if __name__ == '__main__':
    main()