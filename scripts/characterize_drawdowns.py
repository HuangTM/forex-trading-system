#!/usr/bin/env python3
"""Step 1: Characterize USDJPY long-and-hold drawdowns over 16 years.

For each major drawdown (>5%):
  - Peak date, trough date, recovery date (or 'unrecovered')
  - Peak-to-trough %, duration in days
  - Concurrent rate-differential and SMA states

Goal: see if drawdowns cluster around identifiable regimes (vol spikes,
trend reversals, carry collapses) so a defensive filter has something to grab.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from forex_system.core.config import load_config
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators

PAIR = "USDJPY"
CAPITAL = 1_000_000.0
DD_THRESHOLD = 0.05  # report drawdowns >= 5%


def equity_curve(df: pd.DataFrame, pair_info, capital: float) -> pd.Series:
    pip = 0.01 if "JPY" in PAIR else 0.0001
    entry = df["close"].iloc[0]
    units = capital / entry
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    one_time = rt_cost_pips * pip * units
    price_pnl = (df["close"] - entry) / pip * pip * units
    days_held = pd.Series(np.arange(len(df)), index=df.index)
    swap_pnl = pair_info.swap_long_pips_per_day * days_held * pip * units
    return capital + price_pnl + swap_pnl - one_time


def find_drawdowns(equity: pd.Series, threshold: float) -> list[dict]:
    """Find all drawdowns >= threshold. Each = (peak_date, trough_date, recovery_date_or_None)."""
    running_max = equity.cummax()
    dd_pct = (equity - running_max) / running_max
    in_dd = dd_pct < -threshold

    drawdowns = []
    i = 0
    while i < len(equity):
        if not in_dd.iloc[i]:
            i += 1
            continue
        # Found drawdown start. Find peak (last new high before this).
        peak_idx = running_max.iloc[:i + 1][running_max.iloc[:i + 1] == running_max.iloc[i]].index[-1]
        peak_pos = equity.index.get_loc(peak_idx)
        # Find trough: lowest point before recovery (return to peak)
        peak_value = equity.loc[peak_idx]
        recovered = equity.iloc[peak_pos:][equity.iloc[peak_pos:] >= peak_value]
        recovery_idx = recovered.index[1] if len(recovered) > 1 else None
        end_pos = (equity.index.get_loc(recovery_idx) if recovery_idx is not None
                   else len(equity) - 1)
        trough_idx = equity.iloc[peak_pos:end_pos + 1].idxmin()
        trough_value = equity.loc[trough_idx]
        depth = (trough_value - peak_value) / peak_value
        if abs(depth) >= threshold:
            drawdowns.append({
                "peak_date": peak_idx,
                "trough_date": trough_idx,
                "recovery_date": recovery_idx,
                "depth_pct": depth,
                "peak_to_trough_days": (trough_idx - peak_idx).days,
                "trough_to_recovery_days": ((recovery_idx - trough_idx).days
                                            if recovery_idx else None),
                "peak_equity": peak_value,
                "trough_equity": trough_value,
            })
        # Skip past this drawdown
        i = end_pos + 1
    return drawdowns


def main():
    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_info = {p.symbol: p.to_pair_info() for p in cfg.pairs}[PAIR]

    df = load_parquet(PAIR, "daily", "data")
    enriched = compute_indicators(df, ["sma_50", "sma_200", "atr_14"])

    eq = equity_curve(enriched, pair_info, CAPITAL)

    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    rate_data = rate_data.rename(columns={c: c.replace("_diff", "") for c in rate_data.columns})
    if rate_data.index.tz is None and eq.index.tz is not None:
        rate_data = rate_data.copy()
        rate_data.index = rate_data.index.tz_localize(eq.index.tz)
    rate_series = rate_data[PAIR].reindex(eq.index, method="ffill")

    dds = find_drawdowns(eq, DD_THRESHOLD)
    dds.sort(key=lambda d: d["depth_pct"])  # worst first

    print("=" * 96)
    print(f"  {PAIR} long-and-hold drawdowns >= {DD_THRESHOLD:.0%} over 16.1 years")
    print("=" * 96)
    print(f"\n{'#':>3} {'Peak':>12} {'Trough':>12} {'Recovery':>12} "
          f"{'Depth':>7} {'P→T days':>9} {'T→R days':>9} {'rate_diff@peak':>14} {'SMA50/200@peak':>16}")
    print("-" * 96)
    for i, d in enumerate(dds, 1):
        rec = d["recovery_date"].date() if d["recovery_date"] else "UNREC"
        tr_days = d["trough_to_recovery_days"] if d["trough_to_recovery_days"] is not None else "—"
        rd = rate_series.loc[d["peak_date"]] * 100  # pct
        sma50 = enriched["sma_50"].loc[d["peak_date"]]
        sma200 = enriched["sma_200"].loc[d["peak_date"]]
        regime = "UP" if (sma50 > sma200) else "DOWN" if pd.notna(sma200) else "?"
        print(f"{i:>3} {d['peak_date'].date()!s:>12} {d['trough_date'].date()!s:>12} "
              f"{rec!s:>12} {d['depth_pct']:>7.1%} {d['peak_to_trough_days']:>9} "
              f"{tr_days!s:>9} {rd:>13.2f}% {regime:>16}")

    # Aggregate stats
    if dds:
        depths = np.array([d["depth_pct"] for d in dds])
        durations = np.array([d["peak_to_trough_days"] for d in dds])
        unrec = sum(1 for d in dds if d["recovery_date"] is None)
        print(f"\nSummary: {len(dds)} drawdowns >= {DD_THRESHOLD:.0%}")
        print(f"  Worst: {depths.min():.1%}  | Median: {np.median(depths):.1%}  | "
              f"Total time in DD: {sum(durations):.0f} days ({sum(durations) / (16.1 * 365):.0%} of period)")
        print(f"  Unrecovered (still under peak at series end): {unrec}")

    # Histogram of depth distribution
    print(f"\nDepth distribution:")
    bins = [-0.50, -0.20, -0.15, -0.10, -0.07, -0.05]
    for lo, hi in zip(bins[:-1], bins[1:]):
        n = sum(1 for d in dds if lo <= d["depth_pct"] < hi)
        if n:
            print(f"  [{lo:.0%}, {hi:.0%}): {'■' * n}  ({n})")

    # Save for later use
    out = pd.DataFrame(dds)
    out.to_csv("data/usdjpy_bh_drawdowns.csv", index=False)
    print(f"\nSaved details to data/usdjpy_bh_drawdowns.csv")


if __name__ == "__main__":
    main()
