"""CLI: check whether the paper-trading loop heartbeat is fresh.

Usage:
    python -m forex_system.ops.check_heartbeat [--max-age-min 60] [--heartbeat-path data/heartbeat.json]

Exit codes:
    0 — heartbeat is fresh
    1 — heartbeat is stale (older than --max-age-min)
    2 — heartbeat file is missing or malformed
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_HEARTBEAT_PATH = "data/heartbeat.json"
DEFAULT_MAX_AGE_MIN = 60


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def check_heartbeat(heartbeat_path: str, max_age_min: int) -> tuple[int, str]:
    """Read and validate the heartbeat file.

    Returns:
        (exit_code, message) where exit_code is 0/1/2.
    """
    p = Path(heartbeat_path)

    if not p.exists():
        return 2, "heartbeat file missing"

    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return 2, f"heartbeat file malformed: {e}"

    ts_raw = data.get("timestamp")
    if not ts_raw:
        return 2, "heartbeat file malformed: missing 'timestamp' field"

    try:
        ts = datetime.fromisoformat(ts_raw)
        # Ensure timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError as e:
        return 2, f"heartbeat file malformed: cannot parse timestamp '{ts_raw}': {e}"

    cycle_id = data.get("cycle_id", "?")
    age_seconds = (_now_utc() - ts).total_seconds()
    age_min = age_seconds / 60.0

    if age_min > max_age_min:
        return 1, f"heartbeat stale: last seen {age_min:.1f}m ago (threshold {max_age_min}m)"

    return 0, f"heartbeat OK ({age_min:.1f}m ago, cycle {cycle_id})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether the paper-trading loop heartbeat is fresh."
    )
    parser.add_argument(
        "--max-age-min",
        type=int,
        default=DEFAULT_MAX_AGE_MIN,
        help=f"Maximum acceptable heartbeat age in minutes (default: {DEFAULT_MAX_AGE_MIN})",
    )
    parser.add_argument(
        "--heartbeat-path",
        default=DEFAULT_HEARTBEAT_PATH,
        help=f"Path to heartbeat.json (default: {DEFAULT_HEARTBEAT_PATH})",
    )
    args = parser.parse_args(argv)

    exit_code, message = check_heartbeat(args.heartbeat_path, args.max_age_min)
    print(message)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
