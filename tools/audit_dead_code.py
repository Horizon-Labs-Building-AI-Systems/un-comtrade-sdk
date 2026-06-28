"""Dead-code analysis: which public modules are NEVER imported?"""
import os
import re
import ast


def list_modules():
    mods = []
    for root, dirs, files in os.walk('un_comtrade'):
        if '__pycache__' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                mods.append(os.path.join(root, f).replace(os.sep, '/'))
    return sorted(mods)


def to_modname(p):
    return p.replace('/', '.').replace('.py', '')


def collect_imports(text, src_mod):
    """Yield absolute target module names from this file."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            level = node.level or 0
            mod = node.module
            if level == 0:
                if mod and mod.startswith('un_comtrade'):
                    yield mod
            else:
                parts = src_mod.split('.')
                if level == 1:
                    base = '.'.join(parts[:-1])
                else:
                    base = '.'.join(parts[:-(level - 1)])
                if mod:
                    yield f'{base}.{mod}'
                else:
                    yield base
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('un_comtrade'):
                    yield alias.name


def main():
    mods = list_modules()
    # All targets
    all_targets = set()
    src_targets = {}
    for m in mods:
        src = to_modname(m)
        with open(m) as fp:
            text = fp.read()
        ts = set(collect_imports(text, src))
        src_targets[src] = ts
        all_targets.update(ts)

    # All modules
    all_modules = set(to_modname(m) for m in mods)

    # Imported-by (fan-in)
    fan_in = {}
    for src, ts in src_targets.items():
        for t in ts:
            fan_in.setdefault(t, set()).add(src)

    # Fan-in >= 1 means "someone imports this"
    # For top-level modules, "importable from outside" is enough
    imported = set(fan_in.keys())

    # Modules not in fan_in (i.e. no other module imports them) AND not the top-level __init__
    print('=== Modules with NO in-project importers ===')
    unreferenced = []
    for m in sorted(all_modules):
        if m in imported:
            continue
        # Top-level __init__ is special - it's the entry point
        if m.endswith('.__init__'):
            continue
        # Public __init__ modules with no importers are still public surfaces (re-export hubs)
        # So count them as "leaf re-export hubs" if they have __all__
        mod_path = m.replace('.', '/') + '.py'
        if not os.path.exists(mod_path):
            continue
        with open(mod_path) as fp:
            text = fp.read()
        has_all = '__all__' in text
        unreferenced.append((m, has_all, mod_path))

    for m, has_all, path in unreferenced:
        kind = 're-export hub' if has_all else 'LEAF (possibly dead)'
        print(f'  {kind:20s} {m}  ({path})')

    # Modules imported by 1 module only (potential over-coupling)
    print()
    print('=== Modules with EXACTLY 1 in-project importer ===')
    one_importer = [(m, list(s)[0]) for m, s in fan_in.items() if len(s) == 1]
    for m, src in sorted(one_importer):
        print(f'  {m} <- {src}')

    # Modules with many importers (heavy-use)
    print()
    print('=== Top 15 modules by fan-in ===')
    for m, s in sorted(fan_in.items(), key=lambda kv: -len(kv[1]))[:15]:
        print(f'  {len(s):3d} importers: {m}')


if __name__ == '__main__':
    main()