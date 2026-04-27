#!/usr/bin/env python3
"""Auto-retirement workflow for pre-registered triggers.

Closes R1 Amendment 1 finding A1_C3 (vol_target_carry TradeIntent):
the retirement-trigger CONDITIONS were machine-checkable, but the
ACTION (mark trial retired in .fintech-org/trials.jsonl) was operator-
mediated. Without this tool, an operator could miss a fired trigger
and continue running a retired strategy.

Usage modes
-----------
1) Direct retirement (CLI): operator confirms a trigger fired and
   asks the tool to write the retirement record.

   python scripts/auto_retire_on_trigger.py \\
     --strategy vol_target_carry \\
     --trigger-id VTC-T6 \\
     --reason "costs doubled stress: Sharpe 0.18 below 0.40" \\
     --evidence-path data/results/trials/abc123.json

2) From-gate-output (CLI): pass a gate-evaluation JSON. The tool
   parses pre-registered trigger conditions, finds any fired, and
   writes RETIRED records.

   python scripts/auto_retire_on_trigger.py \\
     --gate-output data/cf_t9_status.json \\
     --strategy carry_fred

The tool NEVER auto-derives a trigger from raw stats; it only writes
RETIRED records when called with explicit trigger-id + reason. The
gate-output mode wraps a structured JSON that already contains a
"triggered: true" field (the CF-T9 monitor's exit-1 envelope).

Exit codes
----------
  0 -- retirement record written (or gate not triggered, no action needed)
  1 -- retirement was needed but write failed
  2 -- input error (missing args, malformed gate output)

Invariants
----------
- Retirement records are APPEND-ONLY. The tool never modifies prior
  trial-jsonl entries; it appends a new record with status="retired".
- Idempotent: re-running with the same {strategy, trigger-id} pair
  does NOT write a duplicate retired record. The tool reads the
  trail and exits 0 if already-retired-by-this-trigger.
- Audit trail: every retirement record cites operator, evidence_path,
  trigger-id, reason, and pre-reg-path. No silent retirements.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRIALS_LOG = REPO_ROOT / ".fintech-org" / "trials.jsonl"

# Map of strategy -> pre-registration path. Authoritative source for
# evidence_paths in the retirement record.
PRE_REG_PATHS = {
    "vol_target_carry": "references/pre-registrations/vol_target_carry.md",
    "carry_fred": "references/pre-registrations/carry_fred.md",
    "tas_ceiling_4h": "references/pre-registrations/tas_ceiling_4h.md",
}


def _git_hash() -> str:
    """Return current git hash for audit traceability."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _operator() -> str:
    """Best-effort operator identification for the audit trail."""
    return os.environ.get("USER", "unknown")


def already_retired_by_trigger(strategy: str, trigger_id: str) -> bool:
    """Return True if the trials log already records a RETIRED entry for
    this {strategy, trigger_id} pair. Idempotency guard."""
    if not TRIALS_LOG.exists():
        return False
    for line in TRIALS_LOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            entry.get("status") == "retired"
            and entry.get("strategy") == strategy
            and entry.get("retirement_trigger_id") == trigger_id
        ):
            return True
    return False


def write_retirement_record(
    strategy: str,
    trigger_id: str,
    reason: str,
    evidence_path: str | None = None,
    operator: str | None = None,
) -> dict:
    """Append a RETIRED entry to the trials log. Returns the entry dict."""
    pre_reg = PRE_REG_PATHS.get(strategy)
    if not pre_reg:
        raise ValueError(
            f"Unknown strategy {strategy!r}. Must be one of: "
            f"{sorted(PRE_REG_PATHS.keys())}"
        )
    record = {
        "trial_id": f"retire-{strategy}-{trigger_id}-{int(datetime.now(timezone.utc).timestamp())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_hash": _git_hash(),
        "strategy": strategy,
        "status": "retired",
        "retirement_trigger_id": trigger_id,
        "retirement_reason": reason,
        "pre_reg_path": pre_reg,
        "evidence_path": evidence_path,
        "operator": operator or _operator(),
    }
    TRIALS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(TRIALS_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def parse_gate_output(gate_output_path: Path) -> tuple[bool, str | None, str | None]:
    """Parse a gate-evaluation JSON (e.g., data/cf_t9_status.json from
    monitor_regime_triggers.py) and return (triggered, trigger_id, reason)."""
    if not gate_output_path.exists():
        raise RuntimeError(f"gate output not found: {gate_output_path}")
    payload = json.loads(gate_output_path.read_text())
    triggered = bool(payload.get("triggered", False))
    if not triggered:
        return False, None, None
    # CF-T9 envelope per scripts/monitor_regime_triggers.py
    if payload.get("monitor_id") == "CF-T9":
        return True, "CF-T9", (
            f"Both CF-T9 clauses fired simultaneously per "
            f"{gate_output_path.name}; latest BoJ rate "
            f"{payload['clause_a_boj_rate'].get('latest_rate_pct')}% at "
            f"{payload['clause_a_boj_rate'].get('latest_quarter_end')}; "
            f"current basket Sharpe "
            f"{payload['clause_b_basket_sharpe']['evidence'].get('current')}"
        )
    # Generic envelope: monitor must self-identify
    monitor_id = payload.get("monitor_id", "UNKNOWN")
    return True, monitor_id, payload.get("reason", f"Triggered per {gate_output_path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-retirement workflow for pre-registered triggers."
    )
    parser.add_argument("--strategy", required=True,
                        choices=sorted(PRE_REG_PATHS.keys()))
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--trigger-id", help="Explicit trigger ID (e.g., VTC-T6)")
    src.add_argument("--gate-output", help="Path to a gate-evaluation JSON")
    parser.add_argument("--reason",
                        help="Human-readable retirement reason; required with --trigger-id")
    parser.add_argument("--evidence-path",
                        help="Path to results JSON / log that supports the retirement")
    parser.add_argument("--operator", default=None,
                        help="Override operator name (default: $USER)")
    args = parser.parse_args()

    if args.trigger_id:
        if not args.reason:
            print("ERROR: --reason required with --trigger-id", file=sys.stderr)
            return 2
        trigger_id = args.trigger_id
        reason = args.reason
        evidence = args.evidence_path
    else:
        try:
            triggered, trigger_id, reason = parse_gate_output(Path(args.gate_output))
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        if not triggered:
            print(f"[auto-retire] Gate not triggered. No action needed.")
            return 0
        evidence = args.gate_output

    # Idempotency guard
    if already_retired_by_trigger(args.strategy, trigger_id):
        print(
            f"[auto-retire] {args.strategy} already retired by {trigger_id} "
            f"(no duplicate record written)."
        )
        return 0

    try:
        record = write_retirement_record(
            strategy=args.strategy,
            trigger_id=trigger_id,
            reason=reason,
            evidence_path=evidence,
            operator=args.operator,
        )
    except Exception as e:
        print(f"ERROR: failed to write retirement record: {e}", file=sys.stderr)
        return 1

    print(f"[auto-retire] RETIRED {args.strategy} via {trigger_id}")
    print(f"  trial_id: {record['trial_id']}")
    print(f"  pre-reg:  {record['pre_reg_path']}")
    print(f"  evidence: {record['evidence_path']}")
    print(f"  operator: {record['operator']}")
    print(f"  trail:    {TRIALS_LOG.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
