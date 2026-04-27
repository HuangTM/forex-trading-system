#!/usr/bin/env python3
"""CF-T9 regime monitor for carry_fred (Bet #1).

Pre-registered retirement trigger CF-T9 (CONSENSUS 2026-04-26, references/
pre-registrations/carry_fred.md amendment): retire carry_fred within 5
trading days when ALL three clauses hold simultaneously within a
90-trading-day window:

  (A) BoJ policy rate (FRED series IRSTCB01JPM156N) >= 0.50% for >= 2
      consecutive quarter-end observations
  (B) aggregate equal-vol-weighted 60-trading-day rolling Sharpe across
      {AUDJPY, CADJPY, EURJPY, GBPJPY, NZDJPY, USDJPY} drops below 0.20
      net of costs

This script is the operationalization of CF-T9. It fetches fresh FRED data,
loads pair daily parquets, computes the rolling basket Sharpe, evaluates
both clauses, and emits a structured JSON record plus a human-readable
summary. Designed to be runnable from cron.

Exit codes:
    0  -- CF-T9 NOT triggered (carry_fred remains eligible)
    1  -- CF-T9 TRIGGERED (carry_fred must be retired within 5 trading days)
    2  -- monitor failed (data fetch error, stale data, missing pair, etc.)
       -- treat exit-2 as inconclusive: do NOT auto-retire, escalate to ops

Usage:
    export FRED_API_KEY=your_fred_key  # or pass --api-key
    python scripts/monitor_regime_triggers.py
    python scripts/monitor_regime_triggers.py --output data/cf_t9_status.json
    python scripts/monitor_regime_triggers.py --json-only   # for cron

Audit:
    Every invocation appends one JSON-line to data/cf_t9_audit.log.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Constants (pre-registered; do not change without amending carry_fred.md)
# --------------------------------------------------------------------------- #

JPY_CROSS_PAIRS: list[str] = [
    "AUDJPY", "CADJPY", "EURJPY", "GBPJPY", "NZDJPY", "USDJPY",
]
PAIR_DATA_DIR = Path("data/processed")
PAIR_DATA_PATTERN = "{pair}_daily.parquet"

BOJ_FRED_SERIES_ID = "IRSTCB01JPM156N"  # CONSENSUS 2026-04-26 specified

# CF-T9 thresholds (binding pre-registered constants)
CF_T9_BOJ_RATE_THRESHOLD_PCT = 0.50      # clause A: >=0.50%
CF_T9_BOJ_QUARTERS_REQUIRED = 2          # clause A: 2 consecutive quarter-ends
CF_T9_ROLLING_SHARPE_WINDOW = 60         # clause B: 60 trading days
CF_T9_ROLLING_SHARPE_THRESHOLD = 0.20    # clause B: <0.20
CF_T9_LOOKBACK_WINDOW = 90               # both clauses must hold within 90 days

# Equal-vol-weighting target (carry_fred convention)
TARGET_VOL_ANNUALIZED = 0.10
VOL_WINDOW_DAYS = 252  # rolling vol estimate window

# Output paths
DEFAULT_OUTPUT_PATH = Path("data/cf_t9_status.json")
AUDIT_LOG_PATH = Path("data/cf_t9_audit.log")

# Staleness guard: warn if FRED data older than this
FRED_MAX_STALENESS_DAYS = 95   # ~3 months (FRED rates publish monthly)
PAIR_MAX_STALENESS_DAYS = 14   # 2 trading weeks; normal pair-data refresh cadence is weekly


# --------------------------------------------------------------------------- #
# Data fetching
# --------------------------------------------------------------------------- #

def fetch_boj_rate_series(api_key: str | None) -> pd.Series:
    """Fetch BoJ policy rate from FRED.

    Returns a monthly-frequency series of BoJ policy rate in percent.
    Raises on auth failure or network error so caller can apply STOP policy.
    """
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY required. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    try:
        from fredapi import Fred
    except ImportError:
        raise RuntimeError("fredapi not installed. Run: pip install fredapi")
    fred = Fred(api_key=api_key)
    series = fred.get_series(BOJ_FRED_SERIES_ID, observation_start="2000-01-01")
    series = series.dropna()
    series.index = pd.to_datetime(series.index)
    series.name = "boj_rate_pct"
    return series


def load_pair_returns() -> pd.DataFrame:
    """Load close-prices for all 6 JPY-cross pairs and compute daily returns.

    Returns a DataFrame indexed by date with one column per pair.
    Pairs missing data are dropped with a warning -- caller decides how to
    handle the resulting universe shrinkage.
    """
    closes = {}
    for pair in JPY_CROSS_PAIRS:
        path = PAIR_DATA_DIR / PAIR_DATA_PATTERN.format(pair=pair)
        if not path.exists():
            print(f"WARN: missing {path}", file=sys.stderr)
            continue
        df = pd.read_parquet(path)
        if "close" not in df.columns:
            print(f"WARN: {path} has no 'close' column", file=sys.stderr)
            continue
        closes[pair] = df["close"]
    if not closes:
        raise RuntimeError("No JPY-cross pair data available.")
    closes_df = pd.DataFrame(closes).sort_index()
    closes_df = closes_df.dropna(how="all")
    returns = closes_df.pct_change().dropna(how="all")
    return returns


# --------------------------------------------------------------------------- #
# CF-T9 evaluation
# --------------------------------------------------------------------------- #

def quarter_end_observations(boj_series: pd.Series) -> pd.Series:
    """Resample BoJ rate to quarter-end frequency, last observation per quarter.

    Returns a series indexed by quarter-end date with the rate at that date
    (forward-filled from the latest available monthly observation).
    """
    # Forward-fill so quarter-ends always have a rate (FRED publishes monthly,
    # so quarter-end may align with the monthly obs already, but we ffill for
    # robustness against irregular publication schedules).
    daily = boj_series.resample("D").ffill()
    return daily.resample("QE").last().dropna()


def boj_clause_satisfied(quarterly: pd.Series) -> tuple[bool, list[dict]]:
    """Clause A: >=2 CONSECUTIVE quarter-end obs at >=0.50%.

    Returns (satisfied, contributing_observations) where contributing_observations
    is the list of qualifying quarters as dicts.
    """
    qualifying = quarterly >= CF_T9_BOJ_RATE_THRESHOLD_PCT
    # Find the longest run of consecutive True values; record the most recent one
    obs = []
    run = 0
    longest_run_end = None
    longest_run_len = 0
    for i, (date, q) in enumerate(qualifying.items()):
        if q:
            run += 1
            if run > longest_run_len:
                longest_run_len = run
                longest_run_end = date
        else:
            run = 0
    satisfied = longest_run_len >= CF_T9_BOJ_QUARTERS_REQUIRED
    if satisfied:
        # Record the qualifying run that ends at longest_run_end
        end_idx = list(qualifying.index).index(longest_run_end)
        for off in range(longest_run_len):
            d = qualifying.index[end_idx - off]
            obs.append({
                "quarter_end": d.strftime("%Y-%m-%d"),
                "rate_pct": float(quarterly.loc[d]),
            })
        obs.reverse()
    return satisfied, obs


def equal_vol_weighted_basket(returns: pd.DataFrame) -> pd.Series:
    """Compute equal-vol-weighted basket return.

    Each pair contributes target_vol / pair_realized_vol units. Cross-section
    is then averaged equally so the basket is target-vol scaled per pair.
    Returns a daily basket return series.
    """
    realized_vol = returns.rolling(VOL_WINDOW_DAYS).std() * np.sqrt(252)
    weights = TARGET_VOL_ANNUALIZED / realized_vol.replace(0, np.nan)
    # Long-only carry-style weighting (this monitor is regime detection, not a
    # tradable signal -- equal-weighted long basket of JPY-crosses tracks the
    # BoJ-divergence regime returns).
    weighted_returns = (returns * weights.shift(1)).mean(axis=1)
    return weighted_returns.dropna()


def rolling_sharpe(daily_returns: pd.Series, window: int) -> pd.Series:
    """Annualized rolling Sharpe ratio (252-trading-day annualization)."""
    rolling_mean = daily_returns.rolling(window).mean()
    rolling_std = daily_returns.rolling(window).std()
    annualized = rolling_mean / rolling_std * np.sqrt(252)
    return annualized.replace([np.inf, -np.inf], np.nan)


def sharpe_clause_satisfied(rolling_sharpe_series: pd.Series) -> tuple[bool, dict]:
    """Clause B: 60-day rolling Sharpe drops below 0.20.

    Returns (satisfied, evidence_dict). The latest 90-day window
    (CF_T9_LOOKBACK_WINDOW) is the evaluation period.
    """
    recent = rolling_sharpe_series.tail(CF_T9_LOOKBACK_WINDOW).dropna()
    if recent.empty:
        return False, {"reason": "insufficient data in lookback window"}
    below = recent < CF_T9_ROLLING_SHARPE_THRESHOLD
    satisfied = bool(below.any())
    evidence = {
        "lookback_days": CF_T9_LOOKBACK_WINDOW,
        "min_in_window": float(recent.min()),
        "min_in_window_date": recent.idxmin().strftime("%Y-%m-%d"),
        "current": float(recent.iloc[-1]),
        "current_date": recent.index[-1].strftime("%Y-%m-%d"),
        "days_below_threshold": int(below.sum()),
    }
    return satisfied, evidence


def evaluate_cf_t9(
    boj_series: pd.Series,
    pair_returns: pd.DataFrame,
) -> dict:
    """Run both clauses and produce the monitor decision record."""
    quarterly = quarter_end_observations(boj_series)
    clause_a_pass, clause_a_obs = boj_clause_satisfied(quarterly)

    basket = equal_vol_weighted_basket(pair_returns)
    rs = rolling_sharpe(basket, CF_T9_ROLLING_SHARPE_WINDOW)
    clause_b_pass, clause_b_evidence = sharpe_clause_satisfied(rs)

    triggered = clause_a_pass and clause_b_pass

    # Data freshness checks -- escalate to exit-2 if stale.
    boj_last = boj_series.index.max()
    pair_last = pair_returns.index.max()
    # Normalize all timestamps to tz-naive for comparison; FRED returns naive,
    # parquets may carry UTC tz. Use UTC wall-clock as the staleness reference.
    now_naive = pd.Timestamp.now(tz="UTC").tz_localize(None)
    boj_last_naive = boj_last.tz_localize(None) if boj_last.tzinfo else boj_last
    pair_last_naive = pair_last.tz_localize(None) if pair_last.tzinfo else pair_last
    boj_staleness_days = (now_naive - boj_last_naive).days
    pair_staleness_days = (now_naive - pair_last_naive).days
    fred_stale = boj_staleness_days > FRED_MAX_STALENESS_DAYS
    pair_stale = pair_staleness_days > PAIR_MAX_STALENESS_DAYS

    return {
        "monitor_id": "CF-T9",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "triggered": triggered,
        "clause_a_boj_rate": {
            "satisfied": clause_a_pass,
            "threshold_pct": CF_T9_BOJ_RATE_THRESHOLD_PCT,
            "quarters_required": CF_T9_BOJ_QUARTERS_REQUIRED,
            "qualifying_observations": clause_a_obs,
            "latest_quarter_end": quarterly.index[-1].strftime("%Y-%m-%d") if len(quarterly) else None,
            "latest_rate_pct": float(quarterly.iloc[-1]) if len(quarterly) else None,
        },
        "clause_b_basket_sharpe": {
            "satisfied": clause_b_pass,
            "rolling_window_days": CF_T9_ROLLING_SHARPE_WINDOW,
            "lookback_window_days": CF_T9_LOOKBACK_WINDOW,
            "threshold": CF_T9_ROLLING_SHARPE_THRESHOLD,
            "evidence": clause_b_evidence,
        },
        "universe": JPY_CROSS_PAIRS,
        "data_freshness": {
            "boj_last_obs": boj_last_naive.strftime("%Y-%m-%d"),
            "boj_staleness_days": boj_staleness_days,
            "pair_last_obs": pair_last_naive.strftime("%Y-%m-%d"),
            "pair_staleness_days": pair_staleness_days,
            "fred_stale": fred_stale,
            "pair_stale": pair_stale,
        },
        "pre_reg_reference": "references/pre-registrations/carry_fred.md (CF-T9 amendment)",
        "consensus_track_id": "sunday-pre-open-prep-2026-04-26",
    }


# --------------------------------------------------------------------------- #
# CLI / output
# --------------------------------------------------------------------------- #

def write_audit_record(record: dict, audit_path: Path = AUDIT_LOG_PATH) -> None:
    """Append a JSON-line to the CF-T9 audit log."""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def print_human_summary(record: dict) -> None:
    """Print a human-readable summary to stdout."""
    print("=" * 70)
    print(f"  CF-T9 Regime Monitor — {record['evaluated_at']}")
    print("=" * 70)
    status = "TRIGGERED" if record["triggered"] else "not triggered"
    print(f"\n  Status: {status}")
    print()

    a = record["clause_a_boj_rate"]
    a_mark = "PASS" if a["satisfied"] else "fail"
    print(f"  Clause A (BoJ rate >={a['threshold_pct']}% for >={a['quarters_required']} consecutive quarters): {a_mark}")
    if a["latest_quarter_end"]:
        print(f"    Latest quarter-end: {a['latest_quarter_end']}  rate={a['latest_rate_pct']:.3f}%")
    if a["qualifying_observations"]:
        print(f"    Qualifying run:")
        for obs in a["qualifying_observations"]:
            print(f"      {obs['quarter_end']}  {obs['rate_pct']:.3f}%")

    b = record["clause_b_basket_sharpe"]
    b_mark = "PASS" if b["satisfied"] else "fail"
    print(f"\n  Clause B (60d rolling Sharpe <{b['threshold']} within {b['lookback_window_days']}d window): {b_mark}")
    e = b["evidence"]
    if "current" in e:
        print(f"    Current 60d Sharpe: {e['current']:.3f}  (as of {e['current_date']})")
        print(f"    Min in 90d window: {e['min_in_window']:.3f}  (on {e['min_in_window_date']})")
        print(f"    Days below threshold: {e['days_below_threshold']}")

    f = record["data_freshness"]
    fred_warn = " STALE" if f["fred_stale"] else ""
    pair_warn = " STALE" if f["pair_stale"] else ""
    print(f"\n  Data freshness:")
    print(f"    BoJ last obs: {f['boj_last_obs']} ({f['boj_staleness_days']}d ago){fred_warn}")
    print(f"    Pair last obs: {f['pair_last_obs']} ({f['pair_staleness_days']}d ago){pair_warn}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CF-T9 regime monitor for carry_fred Bet #1"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("FRED_API_KEY"),
        help="FRED API key (or set FRED_API_KEY env var)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to write structured JSON status (default: data/cf_t9_status.json)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Suppress human-readable summary; emit JSON only on stdout",
    )
    args = parser.parse_args()

    try:
        boj = fetch_boj_rate_series(args.api_key)
    except Exception as e:
        print(f"ERROR: BoJ rate fetch failed: {e}", file=sys.stderr)
        return 2

    try:
        pair_returns = load_pair_returns()
    except Exception as e:
        print(f"ERROR: pair return loading failed: {e}", file=sys.stderr)
        return 2

    record = evaluate_cf_t9(boj, pair_returns)

    # Write outputs (audit always; structured to --output; human to stdout unless suppressed).
    write_audit_record(record)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(record, f, indent=2, default=str)

    if args.json_only:
        print(json.dumps(record, default=str))
    else:
        print_human_summary(record)
        print(f"  Status JSON: {args.output}")
        print(f"  Audit log:   {AUDIT_LOG_PATH}")

    # Inconclusive if data is stale -- exit 2 (do NOT auto-retire on bad data).
    if record["data_freshness"]["fred_stale"] or record["data_freshness"]["pair_stale"]:
        print("\n  WARN: stale data — exit 2 (inconclusive, escalate to ops)",
              file=sys.stderr)
        return 2

    return 1 if record["triggered"] else 0


if __name__ == "__main__":
    sys.exit(main())
