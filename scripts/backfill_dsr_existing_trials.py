#!/usr/bin/env python3
"""Backfill `dsr` field for existing complete trials in .fintech-org/trials.jsonl.

Decision trace
--------------
For each line where status == "complete" AND dsr is null AND sharpe is not null:
  - Compute DSR using deflated_sharpe() with:
      n_trials = n_trials_at_spawn   (sourced from trial record; never silently defaulted)
      n_obs    = derived from n_trades if available; else DEFAULT_N_OBS_FALLBACK with warning
      skew     = 0.0 (return distribution skewness not stored in trial record)
      excess_kurtosis = 0.0 (not stored; logged as assumption)
  - Write back the line with dsr populated.

Lines where status != "complete", dsr is already populated, or sharpe is null
are left untouched (idempotent).

Usage
-----
    python scripts/backfill_dsr_existing_trials.py [--dry-run] [--registry PATH]

Flags
-----
--dry-run    Print what WOULD change without writing. No files modified.
--registry   Override .fintech-org/trials.jsonl path (default: .fintech-org/trials.jsonl).

Log format (stderr, JSON-lines, log-as-decision-trace)
-------------------------------------------------------
Each backfill decision emits a structured log line:
  {"event": "trial.dsr.backfill", "trial_id": ..., "old_dsr": null, "new_dsr": 0.xxxx,
   "n_trials": N, "n_obs": T, "n_obs_source": "n_trades|fallback",
   "skew": 0.0, "excess_kurtosis": 0.0, "assumption": "..."}
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from forex_system.harness.deflated_sharpe import deflated_sharpe  # noqa: E402

_DEFAULT_REGISTRY = Path(".fintech-org/trials.jsonl")

# Fallback n_obs when n_trades is unavailable.
# 252 = 1 year of daily bars; used only when n_trades is null.
# Every use of this fallback is logged as a warning.
_DEFAULT_N_OBS_FALLBACK = 252
_DEFAULT_N_OBS_FALLBACK_REASON = (
    "n_trades is null; using 252 (1 year of daily bars) as n_obs fallback. "
    "This is a conservative approximation. Caller should record n_obs in future trials."
)


def _log(event: dict) -> None:
    """Emit a JSON decision-trace log line to stderr."""
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    print(json.dumps(entry), file=sys.stderr)


def _derive_n_obs(trial: dict) -> tuple[int, str]:
    """Derive n_obs from the trial record.

    Strategy:
      1. If n_trades is not null and > 0: use n_trades as a lower-bound proxy.
         This underestimates n_obs (trades << bars), making DSR conservative.
         Callers should record n_obs directly in future trials.
      2. Otherwise: use _DEFAULT_N_OBS_FALLBACK with a logged warning.

    Returns
    -------
    (n_obs, source_label)
    """
    n_trades = trial.get("n_trades")
    if n_trades is not None and isinstance(n_trades, (int, float)) and n_trades > 0:
        # Use n_trades as a conservative proxy: each trade spans ≥1 bar.
        # Real n_obs (bars) is almost certainly larger; this makes DSR conservative.
        n_obs = max(int(n_trades), 2)
        return n_obs, "n_trades_proxy"
    return _DEFAULT_N_OBS_FALLBACK, "fallback_252"


def backfill(registry: Path, dry_run: bool) -> int:
    """Backfill dsr for complete trials with null dsr.

    Parameters
    ----------
    registry:
        Path to trials.jsonl.
    dry_run:
        If True, print planned changes without writing.

    Returns
    -------
    int
        Number of lines that were (or would be) updated.
    """
    if not registry.exists():
        _log({"event": "backfill.error", "msg": f"Registry not found: {registry}"})
        raise FileNotFoundError(f"trials.jsonl not found at {registry}")

    lines = registry.read_text().splitlines()
    updated = 0
    output_lines: list[str] = []

    for raw_line in lines:
        raw_line = raw_line.strip()
        if not raw_line:
            output_lines.append(raw_line)
            continue

        trial = json.loads(raw_line)

        # Only process: status == "complete", dsr is null, sharpe is not null.
        if (
            trial.get("status") != "complete"
            or trial.get("dsr") is not None
            or trial.get("sharpe") is None
        ):
            output_lines.append(raw_line)
            _log({
                "event": "trial.dsr.skip",
                "trial_id": trial.get("trial_id"),
                "reason": (
                    "not-complete" if trial.get("status") != "complete"
                    else "dsr-already-set" if trial.get("dsr") is not None
                    else "sharpe-null"
                ),
            })
            continue

        # Source n_trials from trial record — never silently default.
        n_trials_at_spawn = trial.get("n_trials_at_spawn")
        if n_trials_at_spawn is None or n_trials_at_spawn < 1:
            _log({
                "event": "trial.dsr.backfill_error",
                "trial_id": trial.get("trial_id"),
                "msg": "n_trials_at_spawn missing or < 1 — cannot compute DSR without it. Skipping.",
            })
            output_lines.append(raw_line)
            continue

        sharpe = float(trial["sharpe"])
        skew = 0.0
        excess_kurtosis = 0.0
        n_obs, n_obs_source = _derive_n_obs(trial)

        if n_obs_source == "fallback_252":
            _log({
                "event": "trial.dsr.n_obs_fallback",
                "trial_id": trial.get("trial_id"),
                "warning": _DEFAULT_N_OBS_FALLBACK_REASON,
            })

        dsr_value = deflated_sharpe(
            sharpe=sharpe,
            n_trials=n_trials_at_spawn,
            n_obs=n_obs,
            skew=skew,
            excess_kurtosis=excess_kurtosis,
        )

        _log({
            "event": "trial.dsr.backfill",
            "trial_id": trial.get("trial_id"),
            "dry_run": dry_run,
            "old_dsr": None,
            "new_dsr": round(dsr_value, 10),
            "sharpe": sharpe,
            "n_trials": n_trials_at_spawn,
            "n_obs": n_obs,
            "n_obs_source": n_obs_source,
            "skew": skew,
            "excess_kurtosis": excess_kurtosis,
            "assumption": "skew=0.0 and excess_kurtosis=0.0 (not stored in trial schema); conservative normal-distribution assumption",
        })

        if dry_run:
            print(
                f"DRY-RUN: trial_id={trial.get('trial_id')} "
                f"sharpe={sharpe:.4f} n_trials={n_trials_at_spawn} "
                f"n_obs={n_obs}({n_obs_source}) → dsr={dsr_value:.6f}",
                file=sys.stdout,
            )
            output_lines.append(raw_line)
        else:
            trial["dsr"] = round(dsr_value, 10)
            output_lines.append(json.dumps(trial))

        updated += 1

    if not dry_run and updated > 0:
        registry.write_text("\n".join(output_lines) + "\n")
        _log({"event": "backfill.complete", "lines_updated": updated, "registry": str(registry)})
    elif not dry_run:
        _log({"event": "backfill.complete", "lines_updated": 0, "msg": "No lines required update."})
    else:
        _log({"event": "backfill.dry_run_complete", "lines_would_update": updated})

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill dsr field for complete trials with null dsr in trials.jsonl."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what WOULD change without writing.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=_DEFAULT_REGISTRY,
        help=f"Path to trials.jsonl (default: {_DEFAULT_REGISTRY})",
    )
    args = parser.parse_args()

    _log({
        "event": "backfill.start",
        "registry": str(args.registry),
        "dry_run": args.dry_run,
    })

    updated = backfill(registry=args.registry, dry_run=args.dry_run)

    if args.dry_run:
        print(f"DRY-RUN complete: {updated} line(s) would be updated.", file=sys.stdout)
    else:
        print(f"Backfill complete: {updated} line(s) updated.", file=sys.stdout)


if __name__ == "__main__":
    main()
