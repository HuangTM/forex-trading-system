"""CLI: detect orphaned trials in the trial registry.

A trial is ORPHANED if:
  - it has a status=spawned line AND
  - no subsequent status=complete or status=error line for the same trial_id AND
  - the spawned timestamp is older than --orphan-age-min minutes ago.

Usage:
    python -m forex_system.ops.audit_trials [--registry .fintech-org/trials.jsonl] \
        [--orphan-age-min 60]

Exit codes:
    0 — no orphaned trials
    1 — one or more orphaned trials found
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_REGISTRY_PATH = ".fintech-org/trials.jsonl"
DEFAULT_ORPHAN_AGE_MIN = 60

# Terminal states: a trial with one of these is considered complete/errored.
_TERMINAL_STATUSES = {"complete", "error"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_registry(registry_path: str) -> list[dict]:
    """Load all JSON lines from the registry. Skips blank lines."""
    p = Path(registry_path)
    if not p.exists():
        return []
    lines = []
    for raw in p.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        lines.append(json.loads(raw))
    return lines


def find_orphans(lines: list[dict], orphan_age_min: int) -> list[dict]:
    """Return orphan records — spawned trials with no terminal follow-up.

    For each trial_id, collect all lines in order. A trial is orphaned when
    the latest status is 'spawned' AND the spawned timestamp is older than
    orphan_age_min minutes.
    """
    # Group lines by trial_id, preserving order
    by_id: dict[str, list[dict]] = {}
    for line in lines:
        tid = line.get("trial_id")
        if tid is None:
            continue
        by_id.setdefault(tid, []).append(line)

    now = _now_utc()
    orphans = []

    for trial_id, trial_lines in by_id.items():
        # Determine final status
        statuses = [l.get("status") for l in trial_lines]
        has_terminal = any(s in _TERMINAL_STATUSES for s in statuses)
        if has_terminal:
            continue  # Completed or errored — not an orphan.

        # Find the spawned line (first occurrence)
        spawned_line = next((l for l in trial_lines if l.get("status") == "spawned"), None)
        if spawned_line is None:
            continue  # No spawned line — skip.

        ts_raw = spawned_line.get("timestamp")
        if not ts_raw:
            continue

        try:
            ts = datetime.fromisoformat(ts_raw)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue  # Unparseable timestamp — skip.

        age_seconds = (now - ts).total_seconds()
        age_min = age_seconds / 60.0

        if age_min < orphan_age_min:
            continue  # Still within grace period.

        orphans.append({
            "trial_id": trial_id,
            "spawned_at": ts_raw,
            "age_minutes": round(age_min, 1),
            "strategy": spawned_line.get("strategy", "?"),
            "pair": spawned_line.get("pair", "?"),
            "config_hash": spawned_line.get("config_hash", "?"),
        })

    return orphans


def print_orphan_table(orphans: list[dict]) -> None:
    """Print a human-readable table of orphaned trials."""
    header = f"{'trial_id':<12} {'spawned_at':<35} {'age_min':>8} {'strategy':<25} {'pair':<10} {'config_hash'}"
    print(header)
    print("-" * len(header))
    for o in orphans:
        print(
            f"{o['trial_id']:<12} {o['spawned_at']:<35} {o['age_minutes']:>8.1f} "
            f"{o['strategy']:<25} {o['pair']:<10} {o['config_hash']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect trials that were spawned but never completed."
    )
    parser.add_argument(
        "--registry",
        default=DEFAULT_REGISTRY_PATH,
        help=f"Path to trials.jsonl (default: {DEFAULT_REGISTRY_PATH})",
    )
    parser.add_argument(
        "--orphan-age-min",
        type=int,
        default=DEFAULT_ORPHAN_AGE_MIN,
        help=f"Minimum age (minutes) before a spawned-only trial is flagged as orphaned "
             f"(default: {DEFAULT_ORPHAN_AGE_MIN})",
    )
    args = parser.parse_args(argv)

    try:
        lines = load_registry(args.registry)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading registry: {e}", file=sys.stderr)
        return 2

    orphans = find_orphans(lines, args.orphan_age_min)

    if not orphans:
        print(f"No orphaned trials found in {args.registry}")
        return 0

    print(f"Found {len(orphans)} orphaned trial(s) in {args.registry}:\n")
    print_orphan_table(orphans)
    return 1


if __name__ == "__main__":
    sys.exit(main())
