"""Build the un_comtrade import graph from AST.

Handles both absolute (un_comtrade.X) and relative (from .X)
imports by resolving to absolute module names.
"""
import ast
import os


def to_modname(p):
    return p.replace('/', '.').replace('.py', '')


def collect_imports(path):
    """Walk all nodes; collect both absolute and relative imports.

    For ImportFrom with level>=1 (relative), return (level, module) tuples.
    For ImportFrom with level=0 (absolute), return (0, module) tuples.
    For Import, return the module names.
    """
    with open(path) as fp:
        text = fp.read()
    tree = ast.parse(text)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            level = node.level or 0
            mod = node.module
            if level == 0:
                if mod and mod.startswith('un_comtrade'):
                    imports.append((0, mod))
            else:
                # Relative - resolve later
                imports.append((level, mod or ''))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('un_comtrade'):
                    imports.append((0, alias.name))
    return imports


def resolve_relative(src_mod: str, level: int, mod: str) -> str | None:
    """Resolve `from .X import Y` (level>=1) to absolute module name."""
    parts = src_mod.split('.')
    # level=1 means sibling -> base is parent of src_mod
    # level=2 means parent -> base is grandparent
    # level=N means N-1 levels up from src_mod's parent
    if level == 1:
        base = '.'.join(parts[:-1])
    else:
        base = '.'.join(parts[:-(level - 1)])
    if mod:
        return f'{base}.{mod}'
    return base


def main():
    mods = []
    for root, dirs, files in os.walk('un_comtrade'):
        if '__pycache__' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                mods.append(os.path.join(root, f).replace(os.sep, '/'))
    mods.sort()

    src_targets = {}
    for m in mods:
        src = to_modname(m)
        raw_imports = collect_imports(m)
        for level, mod in raw_imports:
            if level == 0:
                resolved = mod
            else:
                resolved = resolve_relative(src, level, mod)
            if resolved and resolved != src:
                src_targets.setdefault(src, set()).add(resolved)

    # Stats
    print(f'Modules: {len(mods)}; modules with imports: {len(src_targets)}')
    print(f'Total edges: {sum(len(v) for v in src_targets.values())}')

    # Detect cycles
    nodes = set(src_targets.keys())
    for targets in src_targets.values():
        nodes.update(targets)

    # Tarjan SCC
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = {}
    sccs = []

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlinks[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in src_targets.get(v, ()):
            if w not in index:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif on_stack.get(w, False):
                lowlinks[v] = min(lowlinks[v], index[w])
        if lowlinks[v] == index[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    for n in sorted(nodes):
        if n not in index:
            strongconnect(n)

    nontrivial_sccs = [s for s in sccs if len(s) > 1]
    print()
    print(f'Strongly connected components: {len(sccs)}')
    print(f'Non-trivial SCCs (cycles): {len(nontrivial_sccs)}')
    for scc in nontrivial_sccs:
        print(f'  CYCLE: {sorted(scc)}')

    # Reverse map: module -> who imports it (in-degree / fan-in)
    fan_in = {}
    for src, targets in src_targets.items():
        for t in targets:
            fan_in.setdefault(t, set()).add(src)

    print()
    print('=== Fan-in (modules most imported by others) ===')
    for m, sources in sorted(fan_in.items(), key=lambda kv: -len(kv[1])):
        if len(sources) >= 1:
            print(f'  {len(sources):3d} importers: {m}')
            for s in sorted(sources):
                print(f'      <- {s}')

    # Save the graph for the report
    with open('tools/_audit_graph.txt', 'w') as fp:
        fp.write('=== Source -> Targets ===\n')
        for s in sorted(src_targets):
            fp.write(f'{s}\n')
            for t in sorted(src_targets[s]):
                fp.write(f'  -> {t}\n')
        fp.write('\n=== Non-trivial SCCs (cycles) ===\n')
        for scc in nontrivial_sccs:
            fp.write(f'CYCLE: {sorted(scc)}\n')

    print()
    print('Graph saved to tools/_audit_graph.txt')


if __name__ == '__main__':
    main()