#!/usr/bin/env python3
"""Equivalence-gate for strategy / sizer / engine commits.

Path B prerequisite P5 (per docs/design/path_b_multi_strategy_competition.md)
and CONSENSUS 2026-04-26 Q4. Blocks commits that touch strategy, sizer, or
engine code unless the corresponding engine-vs-canonical-script equivalence
test passes.

This closes the failure mode that consumed five paper-trading days on
vol_target_carry: a sizer change (units = signal*leverage*equity, missing
JPY-pair quote-currency correction) produced engine Sharpe 0.16 vs script
Sharpe 0.76 -- a 0.60 gap that lived in production-bound code without a
reproducible test pinning the canonical contract. After commit a5128e4
closed the gap to |Delta| = 0.0055, this hook keeps that invariant from
silently regressing.

Trigger rules (any staged change in these paths triggers the hook):
  - src/forex_system/strategies/*.py   -> run equivalence tests
  - src/forex_system/sizing/*.py       -> run equivalence tests
  - src/forex_system/backtest/*.py     -> run equivalence tests
  - scripts/<canonical>.py referenced by an equivalence test -> run

If equivalence tests pass, exit 0. If any fail, exit 1 (block commit).
If no relevant files were staged, exit 0 (gate is no-op).

Bypass: `git commit --no-verify`. Bypasses are logged to
`.fintech-org/policy-violations.jsonl` automatically by the wrapping
shell hook.

Usage:
    python tools/check_equivalence_gate.py --staged   # default
    python tools/check_equivalence_gate.py --all      # run all equivalence tests
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EQUIVALENCE_DIR = REPO_ROOT / "tests" / "equivalence"
POLICY_LOG = REPO_ROOT / ".fintech-org" / "policy-violations.jsonl"

# Path prefixes whose changes require equivalence-test re-run.
TRIGGER_PREFIXES = (
    "src/forex_system/strategies/",
    "src/forex_system/sizing/",
    "src/forex_system/backtest/",
)
# Canonical research scripts that pair with engine code; add as new ones land.
TRIGGER_SCRIPTS = {
    "scripts/vol_targeting.py",                    # paired with vol_target_carry equivalence
    "scripts/tas_ceiling_4h_canonical.py",         # paired with Bet #2 (R2 Amendment 1 A1-2)
                                                    # Authored alongside the engine module per
                                                    # the two-author rule. Will be created when
                                                    # H2 dispatch begins; the path is registered
                                                    # NOW so the gate covers it on day 1.
}


def get_staged_files() -> list[str]:
    """Return paths of files currently staged for commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"[equivalence gate] git diff failed: {result.stderr}", file=sys.stderr)
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def files_trigger_gate(files: list[str]) -> tuple[bool, list[str]]:
    """Return (trigger?, list_of_triggering_paths)."""
    triggers = []
    for f in files:
        if any(f.startswith(p) for p in TRIGGER_PREFIXES):
            # Exclude __init__.py and bare registry files; they don't change behavior
            if not f.endswith("__init__.py") and not f.endswith("registry.py"):
                triggers.append(f)
        elif f in TRIGGER_SCRIPTS:
            triggers.append(f)
    return bool(triggers), triggers


def equivalence_tests_exist() -> list[Path]:
    """Return all equivalence test files."""
    if not EQUIVALENCE_DIR.exists():
        return []
    return sorted(
        f for f in EQUIVALENCE_DIR.glob("test_*.py")
        if f.name != "__init__.py"
    )


def find_pytest() -> str | None:
    """Locate a pytest binary -- prefer venv."""
    candidates = [
        REPO_ROOT / ".venv" / "bin" / "pytest",
        REPO_ROOT / "venv" / "bin" / "pytest",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # Fall back to system pytest
    result = subprocess.run(["which", "pytest"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def run_equivalence_tests(test_files: list[Path]) -> tuple[bool, str]:
    """Run pytest on the given equivalence tests; return (passed, stdout+stderr)."""
    pytest = find_pytest()
    if not pytest:
        return False, "[equivalence gate] pytest not found in venv or system PATH."
    cmd = [pytest, *(str(t) for t in test_files), "-v", "--tb=short", "-q"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def log_policy_violation(reason: str, files: list[str]) -> None:
    """Append a JSON-line to .fintech-org/policy-violations.jsonl."""
    POLICY_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "policy": "equivalence-gate-Q4-P5",
        "reason": reason,
        "triggering_files": files,
    }
    with open(POLICY_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Equivalence-gate hook")
    parser.add_argument(
        "--staged", action="store_true",
        help="Check staged files only (default; for use in pre-commit hook).",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all equivalence tests regardless of staged paths.",
    )
    args = parser.parse_args()

    if args.all:
        triggering = ["--all explicitly requested"]
        triggered = True
    else:
        staged = get_staged_files()
        triggered, triggering = files_trigger_gate(staged)
        if not triggered:
            print("[equivalence gate] No strategy/sizer/engine changes staged. Gate skipped.")
            return 0
        print(f"[equivalence gate] Triggered by {len(triggering)} staged path(s):")
        for t in triggering:
            print(f"  - {t}")

    test_files = equivalence_tests_exist()
    if not test_files:
        # Hard policy: a strategy/sizer/engine change WITHOUT any equivalence
        # test in the repo means the firm has lost its canonical-contract
        # guarantee entirely. Block, log, force the operator to add coverage
        # or use --no-verify with full audit.
        msg = (
            "[equivalence gate] BLOCKED: no equivalence tests found in "
            f"{EQUIVALENCE_DIR.relative_to(REPO_ROOT)}. Strategy/sizer/engine "
            "changes require at least one engine-vs-canonical-script equivalence "
            "test to verify Sharpe-Delta < 0.10 and correlation > 0.95.\n"
            "  Add a test under tests/equivalence/test_<strategy>_*.py before committing.\n"
            "  Bypass (operator-acknowledged): git commit --no-verify"
        )
        print(msg)
        log_policy_violation("no_equivalence_tests_present", triggering)
        return 1

    print(f"\n[equivalence gate] Running {len(test_files)} equivalence test file(s):")
    for t in test_files:
        print(f"  - {t.relative_to(REPO_ROOT)}")
    print()

    passed, output = run_equivalence_tests(test_files)
    print(output)

    if not passed:
        print(
            "\n[equivalence gate] BLOCKED: equivalence test(s) failed.\n"
            "  This means engine output diverges from canonical script output beyond\n"
            "  the firm's PROCESS-G1 tolerance (|Sharpe-Delta| < 0.10 OR correlation > 0.95).\n"
            "  Root-cause the divergence before committing -- DO NOT --no-verify a\n"
            "  failed equivalence test (this is the exact failure mode that consumed\n"
            "  5 paper-trading days on vol_target_carry; docs/decisions/CONSENSUS_2026-04-25.md)."
        )
        log_policy_violation("equivalence_test_failed", triggering)
        return 1

    print(f"[equivalence gate] All {len(test_files)} equivalence test(s) passed. Gate cleared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
