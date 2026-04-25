#!/usr/bin/env python3
"""Pre-registration gate for strategy commits.

Checks staged changes for new files under src/forex_system/strategies/
and verifies that a corresponding pre-registration markdown exists at
references/pre-registrations/<strategy_name>.md

Exits 0 if all checks pass. Exits 1 (blocking commit) if any new strategy
file lacks a pre-registration.

Usage (called by .git/hooks/pre-commit):
    python tools/check_pre_registration.py

Usage (standalone check):
    python tools/check_pre_registration.py --all    # Check all existing strategies
    python tools/check_pre_registration.py --staged # Check staged changes (default)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_STRATEGIES_DIR = "src/forex_system/strategies"
_PRE_REG_DIR = Path("references/pre-registrations")
_EXCLUDED = {"__init__.py", "registry.py"}


def get_staged_new_strategy_files() -> list[Path]:
    """Return new (A = added) Python files staged under strategies/."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=A"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[pre-reg gate] git diff failed: {result.stderr}", file=sys.stderr)
        return []

    new_files = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, filepath = parts
        if status != "A":
            continue
        path = Path(filepath)
        if (
            path.parts[:3] == ("src", "forex_system", "strategies")
            and path.suffix == ".py"
            and path.name not in _EXCLUDED
        ):
            new_files.append(path)
    return new_files


def get_all_strategy_files() -> list[Path]:
    """Return all existing Python strategy files (for --all mode)."""
    strategies_path = Path(_STRATEGIES_DIR)
    if not strategies_path.exists():
        return []
    return [
        f for f in strategies_path.glob("*.py")
        if f.name not in _EXCLUDED
    ]


def check_pre_registration(strategy_file: Path) -> tuple[bool, str]:
    """Check if a pre-registration exists for a strategy file.

    Returns (passed, message).
    """
    strategy_name = strategy_file.stem  # e.g. "vol_target_carry"
    pre_reg_path = _PRE_REG_DIR / f"{strategy_name}.md"

    if pre_reg_path.exists():
        return True, f"  [PASS] {strategy_file.name} → {pre_reg_path}"
    else:
        return False, (
            f"  [FAIL] {strategy_file.name}: missing pre-registration.\n"
            f"         Expected: {pre_reg_path}\n"
            f"         Create a pre-registration markdown before committing this strategy.\n"
            f"         See references/pre-registrations/vol_target_carry.md for the format."
        )


def main() -> int:
    """Return 0 (pass) or 1 (block)."""
    args = sys.argv[1:]
    check_all = "--all" in args

    if check_all:
        strategy_files = get_all_strategy_files()
        mode = "all strategies"
    else:
        strategy_files = get_staged_new_strategy_files()
        mode = "staged new strategies"

    if not strategy_files:
        print(f"[pre-reg gate] No new strategy files found ({mode}). Gate passed.")
        return 0

    print(f"[pre-reg gate] Checking {len(strategy_files)} {mode}:")

    failures = []
    for f in strategy_files:
        passed, message = check_pre_registration(f)
        print(message)
        if not passed:
            failures.append(f)

    if failures:
        print(
            f"\n[pre-reg gate] BLOCKED: {len(failures)} strategy file(s) lack pre-registrations.\n"
            f"  Pre-registrations must be created BEFORE validating a strategy.\n"
            f"  This gate exists to enforce hypothesis pre-commitment (HoQR §5 condition 5).\n"
            f"  To bypass in exceptional circumstances: git commit --no-verify\n"
            f"  Bypasses are logged in .fintech-org/policy-violations.jsonl automatically."
        )
        return 1

    print(f"[pre-reg gate] All {len(strategy_files)} strategy file(s) have pre-registrations. Gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
