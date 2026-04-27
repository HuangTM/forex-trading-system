#!/usr/bin/env python3
"""Import-graph guard: assert a backtest entry point does not transitively
depend on Saxo or paper-trading modules.

Operationalizes PROCESS-IMPL-1 from references/pre-registrations/
tas_ceiling_4h.md and closes the WS-05 "third code path" weak-spot per
the CTO inventory: a backtest invocation must NOT pull in live-broker
plumbing because (a) those modules require a live token to import in
some configurations, (b) any side-effect at import time would breach
the firewall between research and execution.

The pre-reg's original specification was a stub:
    grep -r "saxo|paper_trading" $(python -c "import ast; ...")
which is syntactically broken. CTO 2026-04-27 ruling on R2 routed
this to Quant Developer; this is the implementation.

Usage:
    python tools/check_no_saxo_imports.py <entry_point.py>

Exit codes:
    0  --  import graph clean (no Saxo / paper-trading touch)
    1  --  forbidden modules found in transitive import graph (BLOCK)
    2  --  could not analyze (entry point missing, parse error)

Examples:
    python tools/check_no_saxo_imports.py scripts/run_backtest.py
    python tools/check_no_saxo_imports.py src/forex_system/strategies/tas_ceiling_4h.py
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Modules whose import (transitively) into a backtest entry point indicates
# the firewall has been breached. Match by prefix on the dotted module name
# OR by substring on the file path -- belt and suspenders, since dynamic
# imports could bypass either alone.
FORBIDDEN_MODULE_PREFIXES = (
    "forex_system.saxo",
    "forex_system.execution.saxo",
)
FORBIDDEN_FILE_SUBSTRINGS = (
    "scripts/run_paper_trading",
    "src/forex_system/saxo/",
    "src/forex_system/execution/saxo",
)


def parse_imports(path: Path) -> set[str]:
    """Return the set of `import X` and `from X import Y` module names
    declared in the source file. Static AST analysis only -- does NOT
    follow imports recursively (the caller does that)."""
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as e:
        raise RuntimeError(f"Could not parse {path}: {e}")
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def resolve_module_to_path(module: str) -> Path | None:
    """Map a dotted module name (e.g., forex_system.strategies.foo) to the
    file path under src/, returning None if it is a third-party module
    (numpy, pandas, etc.) or a stdlib name."""
    if not module.startswith("forex_system"):
        return None
    rel = module.replace(".", "/") + ".py"
    cand = REPO_ROOT / "src" / rel
    if cand.exists():
        return cand
    # Try package (__init__.py)
    cand_pkg = REPO_ROOT / "src" / module.replace(".", "/") / "__init__.py"
    if cand_pkg.exists():
        return cand_pkg
    return None


def walk_import_graph(entry: Path, max_depth: int = 50) -> set[Path]:
    """Return the transitive set of project file paths reachable from
    `entry` via static `import` declarations. Stops at third-party / stdlib
    boundaries (those imports do not resolve to project paths)."""
    visited: set[Path] = set()
    queue: list[tuple[Path, int]] = [(entry.resolve(), 0)]
    while queue:
        path, depth = queue.pop(0)
        if path in visited or depth >= max_depth:
            continue
        visited.add(path)
        try:
            names = parse_imports(path)
        except RuntimeError as e:
            print(f"WARN: {e}", file=sys.stderr)
            continue
        for name in names:
            sub = resolve_module_to_path(name)
            if sub and sub not in visited:
                queue.append((sub, depth + 1))
    return visited


def find_forbidden(graph: set[Path]) -> list[tuple[Path, str]]:
    """Return list of (path, why_forbidden) for any forbidden file in graph."""
    findings = []
    for p in graph:
        rel = str(p.relative_to(REPO_ROOT)) if REPO_ROOT in p.parents or p == REPO_ROOT else str(p)
        for substr in FORBIDDEN_FILE_SUBSTRINGS:
            if substr in rel:
                findings.append((p, f"path matches forbidden substring '{substr}'"))
                break
    # Module-prefix check: scan each file's parsed imports
    for p in graph:
        try:
            names = parse_imports(p)
        except RuntimeError:
            continue
        for name in names:
            for prefix in FORBIDDEN_MODULE_PREFIXES:
                if name == prefix or name.startswith(prefix + "."):
                    findings.append((p, f"imports forbidden module '{name}'"))
                    break
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assert a backtest entry-point does NOT depend on Saxo / paper-trading code."
    )
    parser.add_argument(
        "entry",
        help="Python file to check (e.g. scripts/run_backtest.py)",
    )
    args = parser.parse_args()

    entry = Path(args.entry)
    if not entry.is_absolute():
        entry = REPO_ROOT / entry
    if not entry.exists():
        print(f"ERROR: entry point not found: {entry}", file=sys.stderr)
        return 2

    try:
        graph = walk_import_graph(entry)
    except Exception as e:
        print(f"ERROR: could not analyze import graph: {e}", file=sys.stderr)
        return 2

    print(f"[no-saxo-imports] entry: {entry.relative_to(REPO_ROOT)}")
    print(f"[no-saxo-imports] reachable project files: {len(graph)}")

    findings = find_forbidden(graph)
    if findings:
        print(f"\n[no-saxo-imports] BLOCKED -- {len(findings)} forbidden touch(es):")
        for path, why in findings:
            rel = str(path.relative_to(REPO_ROOT)) if path.is_absolute() else str(path)
            print(f"  - {rel}: {why}")
        print(
            "\n  PROCESS-IMPL-1 (per references/pre-registrations/tas_ceiling_4h.md): "
            "backtest entry-points must not transitively depend on Saxo or "
            "paper-trading modules. Refactor the backtest entry point or its "
            "dependencies to remove the forbidden import."
        )
        return 1

    print("[no-saxo-imports] PASS -- no Saxo or paper-trading modules in graph.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
