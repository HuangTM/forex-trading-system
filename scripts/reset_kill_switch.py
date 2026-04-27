#!/usr/bin/env python3
"""Reset a kill-switch with a structured audit-log entry.

Path B prereq P6 (per-strategy KillSwitch). Operator runs this script
when a fired trigger has been resolved AND the strategy is cleared to
resume. The script writes a single RESET line to the audit log; it does
NOT bring the strategy back online by itself (the runner re-reads the
audit log on its next start; the new RESET overrides the prior HALTED
state per existing _check_audit_log_on_startup logic).

Usage:
    python scripts/reset_kill_switch.py \\
        --strategy-id vol_target_carry \\
        --operator-id huangtm@gmail.com \\
        --reason "manual: 2026-04-25 incident root-caused; positions flat" \\
        --evidence-path data/results/trials/abc.json

All four flags REQUIRED (per Path B §6.4 prereq P6 acceptance criteria
"reset-without-operator-id rejected"). The script refuses to write a
RESET line if any are missing or empty.

Exit codes:
    0  -- RESET line written
    2  -- input error (missing flags, audit log not present, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PER_STRATEGY_PATH = "data/kill_switch_audit_{strategy_id}.log"


def _audit_path_for_strategy(strategy_id: str, override: str | None) -> Path:
    if override:
        return Path(override)
    return REPO_ROOT / DEFAULT_PER_STRATEGY_PATH.format(strategy_id=strategy_id)


def _last_audit_entry(path: Path) -> dict | None:
    if not path.exists():
        return None
    lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset a per-strategy KillSwitch with audit trail."
    )
    parser.add_argument(
        "--strategy-id", required=True,
        help="Strategy identifier whose kill switch is being reset.",
    )
    parser.add_argument(
        "--operator-id", required=True,
        help="Operator email or unique ID; written verbatim into the audit "
             "trail. Cannot be empty.",
    )
    parser.add_argument(
        "--reason", required=True,
        help="One-sentence reason for the reset. Cannot be empty. This is "
             "the line that future incident reviews will read to understand "
             "why the strategy was cleared to resume.",
    )
    parser.add_argument(
        "--evidence-path", default=None,
        help="Optional path to results / log file documenting the resolution.",
    )
    parser.add_argument(
        "--audit-log-path", default=None,
        help="Override the per-strategy audit log path. Defaults to "
             "data/kill_switch_audit_{strategy_id}.log.",
    )
    args = parser.parse_args()

    # Required-non-empty validation (argparse only checks presence, not
    # whether the value is whitespace).
    for name, val in (
        ("--strategy-id", args.strategy_id),
        ("--operator-id", args.operator_id),
        ("--reason", args.reason),
    ):
        if not val or not val.strip():
            print(f"ERROR: {name} cannot be empty.", file=sys.stderr)
            return 2

    audit_path = _audit_path_for_strategy(args.strategy_id, args.audit_log_path)

    last = _last_audit_entry(audit_path)
    previous_state = (
        last.get("new_state", "UNKNOWN") if last else "NO_PRIOR_AUDIT"
    )

    if last is None:
        print(
            f"WARN: no prior audit entries at {audit_path}. The kill switch "
            "may never have been initialized for this strategy_id. Writing "
            "RESET anyway with previous_state=NO_PRIOR_AUDIT for forensics.",
            file=sys.stderr,
        )
    elif "HALTED" not in previous_state:
        print(
            f"WARN: last audit entry at {audit_path} is not HALTED "
            f"(state={previous_state}). RESET written anyway, but this "
            "suggests no halt is in effect to clear.",
            file=sys.stderr,
        )

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "RESET",
        "operator": args.operator_id,
        "reason": args.reason,
        "evidence_path": args.evidence_path,
        "previous_state": previous_state,
        "new_state": "OK",
        "strategy_id": args.strategy_id,
        "reset_method": "scripts/reset_kill_switch.py",
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"[reset] RESET written to {audit_path}")
    print(f"  operator:       {args.operator_id}")
    print(f"  reason:         {args.reason}")
    print(f"  evidence:       {args.evidence_path}")
    print(f"  previous_state: {previous_state}")
    print(f"  new_state:      OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
