"""DSR Historical Recompute — 2026-06-01.

Recomputes Deflated Sharpe Ratios for every falsification-eligible trial using:
  - compute_honest_n()  — HoQR de-duplication rule for N_honest
  - compute_dsr()       — corrected per-observation formula (units + kurtosis + variance guard)
  - Actual bar count T and realized skew/kurtosis from equity parquet series

DOES NOT re-adjudicate pass/fail.  Produces side-by-side old vs new DSR in
.fintech-org/dsr_recompute_2026-06-01.jsonl.

Usage:
    python -m forex_system.harness.dsr_recompute [--trials JSONL] [--output JSONL]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd
from scipy import stats as scipy_stats

from forex_system.core.constants import TRADING_DAYS_PER_YEAR
from forex_system.harness.dsr import compute_dsr
from forex_system.harness.honest_n import RETAIN_STATUSES, compute_honest_n

logger = logging.getLogger(__name__)

_DEFAULT_TRIALS_PATH = Path(".fintech-org/trials.jsonl")
_DEFAULT_OUTPUT_PATH = Path(".fintech-org/dsr_recompute_2026-06-01.jsonl")
_EQUITY_DIR = Path("data/results/trials")


def _load_equity_series(trial_id: str) -> tuple[pd.Series | None, str]:
    """Load the equity return series for a trial.

    Returns:
        (returns_series | None, source_description)
        Returns (None, reason) when the file is missing or unusable.
    """
    parquet_path = _EQUITY_DIR / f"{trial_id}_equity.parquet"
    if not parquet_path.exists():
        return None, "missing-file"

    try:
        df = pd.read_parquet(parquet_path)
    except Exception as exc:
        logger.warning(
            '{"event": "dsr_recompute.parquet_read_error", "trial_id": "%s", "error": "%s"}',
            trial_id,
            str(exc),
        )
        return None, f"read-error: {exc}"

    if "equity" not in df.columns or len(df) < 2:
        return None, "empty-or-missing-equity-column"

    returns = df["equity"].pct_change().dropna()
    if len(returns) < 2:
        return None, "insufficient-returns"

    return returns, "equity-parquet"


def recompute_all(
    trials_path: Path,
    output_path: Path,
) -> list[dict]:
    """Recompute DSR for all falsification-eligible trials.

    Steps:
      1. Compute N_honest via HoQR de-duplication rule.
      2. For each retained trial with a Sharpe value:
           - Load equity parquet → actual bar count, skew, excess_kurtosis
           - Call compute_dsr() with corrected formula
           - Record old vs new side by side
      3. Write output JSONL.
      4. Return list of result dicts.

    Args:
        trials_path: Path to .fintech-org/trials.jsonl.
        output_path: Path to write output JSONL.

    Returns:
        List of per-trial result dicts.
    """
    # --- Step 1: Honest-N ---
    n_honest, retained_keys, excluded_counts = compute_honest_n(trials_path)
    logger.info(
        '{"event": "dsr_recompute.n_honest", "n_honest": %d, '
        '"excluded_counts": %s, "retained_keys": %s}',
        n_honest,
        excluded_counts,
        sorted(retained_keys),
    )

    # --- Step 2: Load retained trial records ---
    by_id: dict[str, dict] = {}
    with open(trials_path) as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            by_id[record["trial_id"]] = record  # last row wins

    retained = [r for r in by_id.values() if r.get("status") in RETAIN_STATUSES]

    results: list[dict] = []

    for record in retained:
        trial_id = record["trial_id"]
        strategy = record.get("strategy", "unknown")
        pair = record.get("pair", "unknown")
        sharpe = record.get("sharpe")
        old_dsr = record.get("dsr")

        # Trials with no Sharpe cannot have DSR recomputed.
        if sharpe is None:
            row = {
                "trial_id": trial_id,
                "strategy": strategy,
                "pair": pair,
                "sharpe": None,
                "old_dsr": old_dsr,
                "new_dsr": None,
                "n_obs_used": None,
                "n_obs_source": "no-sharpe-recorded",
                "skew": None,
                "excess_kurt": None,
                "n_honest": n_honest,
                "recompute_status": "blocked-no-sharpe",
            }
            results.append(row)
            logger.info(
                '{"event": "dsr_recompute.blocked", "trial_id": "%s", "reason": "no-sharpe"}',
                trial_id,
            )
            continue

        # Load equity parquet for actual bar count and realized moments.
        returns, n_obs_source = _load_equity_series(trial_id)

        if returns is None:
            # Spec: DO NOT substitute n_trades — mark blocked.
            row = {
                "trial_id": trial_id,
                "strategy": strategy,
                "pair": pair,
                "sharpe": sharpe,
                "old_dsr": old_dsr,
                "new_dsr": None,
                "n_obs_used": None,
                "n_obs_source": n_obs_source,
                "skew": None,
                "excess_kurt": None,
                "n_honest": n_honest,
                "recompute_status": "blocked-no-equity-series",
            }
            results.append(row)
            logger.warning(
                '{"event": "dsr_recompute.blocked", "trial_id": "%s", "reason": "no-equity-series", '
                '"source": "%s"}',
                trial_id,
                n_obs_source,
            )
            continue

        n_obs = len(returns)
        skew = float(scipy_stats.skew(returns))
        # scipy kurtosis with fisher=True returns excess kurtosis (kurt - 3)
        excess_kurt = float(scipy_stats.kurtosis(returns, fisher=True))

        try:
            new_dsr = compute_dsr(
                sharpe_ratio=float(sharpe),
                n_observations=n_obs,
                skewness=skew,
                excess_kurtosis=excess_kurt,
                n_trials=n_honest,
                periods_per_year=float(TRADING_DAYS_PER_YEAR),
            )
            recompute_status = "ok"
        except Exception as exc:
            new_dsr = None
            recompute_status = f"compute-error: {exc}"
            logger.error(
                '{"event": "dsr_recompute.compute_error", "trial_id": "%s", "error": "%s"}',
                trial_id,
                str(exc),
            )

        row = {
            "trial_id": trial_id,
            "strategy": strategy,
            "pair": pair,
            "sharpe": sharpe,
            "old_dsr": old_dsr,
            "new_dsr": new_dsr,
            "n_obs_used": n_obs,
            "n_obs_source": n_obs_source,
            "skew": round(skew, 6),
            "excess_kurt": round(excess_kurt, 6),
            "n_honest": n_honest,
            "recompute_status": recompute_status,
        }
        results.append(row)

        crossed = ""
        if new_dsr is not None and old_dsr is not None:
            old_above = float(old_dsr) >= 0.50
            new_above = new_dsr >= 0.50
            if old_above and not new_above:
                crossed = " [CROSSED BELOW 0.50]"
            elif not old_above and new_above:
                crossed = " [CROSSED ABOVE 0.50]"

        logger.info(
            '{"event": "dsr_recompute.trial_done", "trial_id": "%s", '
            '"old_dsr": %s, "new_dsr": %s, "note": "%s"}',
            trial_id,
            old_dsr,
            new_dsr,
            crossed.strip(),
        )

    # --- Step 3: Write output JSONL ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as fh:
        for row in results:
            fh.write(json.dumps(row) + "\n")

    # --- Step 4: Print summary ---
    _print_summary(results, n_honest, retained_keys, excluded_counts)

    return results


def _print_summary(
    results: list[dict],
    n_honest: int,
    retained_keys: set[str],
    excluded_counts: dict[str, int],
) -> None:
    """Print a human-readable summary to stdout."""
    total = len(results)
    ok = sum(1 for r in results if r["recompute_status"] == "ok")
    blocked_no_equity = sum(
        1 for r in results if r["recompute_status"] == "blocked-no-equity-series"
    )
    blocked_no_sharpe = sum(1 for r in results if r["recompute_status"] == "blocked-no-sharpe")

    crossed_above = 0
    crossed_below = 0
    for r in results:
        old = r.get("old_dsr")
        new = r.get("new_dsr")
        if old is not None and new is not None:
            if float(old) < 0.50 and new >= 0.50:
                crossed_above += 1
            elif float(old) >= 0.50 and new < 0.50:
                crossed_below += 1

    print("\n" + "=" * 70)
    print("DSR RECOMPUTE SUMMARY — 2026-06-01")
    print("=" * 70)
    print(f"N_honest (distinct hypotheses): {n_honest}")
    print(f"Retained hypothesis keys: {sorted(retained_keys)}")
    print(f"Excluded: {excluded_counts}")
    print()
    print(f"Retained trials processed : {total}")
    print(f"  Recomputed (ok)          : {ok}")
    print(f"  Blocked (no equity file) : {blocked_no_equity}")
    print(f"  Blocked (no sharpe)      : {blocked_no_sharpe}")
    print()
    print("Crossed 0.50 threshold:")
    print(f"  Old < 0.50, New >= 0.50  : {crossed_above}")
    print(f"  Old >= 0.50, New < 0.50  : {crossed_below}")
    print()
    print("Per-trial results (retained set with Sharpe):")
    print(f"  {'trial_id':18} {'strategy':35} {'old_dsr':>10} {'new_dsr':>10}  status")
    print(f"  {'-' * 18} {'-' * 35} {'-' * 10} {'-' * 10}  ------")
    for r in results:
        old_str = f"{r['old_dsr']:.4f}" if r["old_dsr"] is not None else "   None"
        new_str = f"{r['new_dsr']:.4f}" if r["new_dsr"] is not None else "   None"
        flag = ""
        if r.get("old_dsr") is not None and r.get("new_dsr") is not None:
            if float(r["old_dsr"]) >= 0.50 and r["new_dsr"] < 0.50:
                flag = " <-- crossed BELOW"
            elif float(r["old_dsr"]) < 0.50 and r["new_dsr"] >= 0.50:
                flag = " <-- crossed ABOVE"
        print(
            f"  {r['trial_id']:18} {r['strategy']:35} {old_str:>10} {new_str:>10}"
            f"  {r['recompute_status']}{flag}"
        )
    print()
    print("NOTE: Pass/fail re-adjudication is HoQR/NHT's next step.")
    print("      vol_target_carry and FRED-carry Bet#1 re-adjudication deferred to HoQR/NHT.")
    print("=" * 70)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Recompute historical DSRs using corrected formula + HoQR honest-N.",
    )
    parser.add_argument(
        "--trials",
        default=str(_DEFAULT_TRIALS_PATH),
        help="Path to trials.jsonl (default: .fintech-org/trials.jsonl)",
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT_PATH),
        help="Output path for side-by-side JSONL (default: .fintech-org/dsr_recompute_2026-06-01.jsonl)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        stream=sys.stderr,
    )

    recompute_all(
        trials_path=Path(args.trials),
        output_path=Path(args.output),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
