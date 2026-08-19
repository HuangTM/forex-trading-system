#!/usr/bin/env python3
"""One-off fix: USDJPY_4h_spreads.parquet was stored in pipettes, not pips.

2026-08-17 audit finding: data/spreads/USDJPY_4h_spreads.parquet has
spread_pips median 25.0 / floor 25.0 — exactly 10x the daily file for the same
pair (median 2.4, floor 2.0). EURUSD/GBPUSD 4h files match their daily files,
so only USDJPY_4h is affected. Root cause: the Saxo spread builder used a
price-level pip heuristic (0.01 if close.mean() > 10) instead of a pair-based
pip convention; the 4h USDJPY price series was stored at an anomalous scale
(~5-8, synthetic), which broke the pip conversion. The heuristic is now fixed
(pair-based) in src/forex_system/saxo/history.py; this script repairs the
on-disk artifact because the Saxo generator cannot be re-run (no API token).

The fix divides spread_pips by 10 (pipettes -> pips). The original file is
quarantined, never deleted. Sanity checks (fail loudly):
  * corrected median within [1.5, 4.0] pips (daily file median is 2.4)
  * corrected floor within [1.0, 3.0] pips (daily floor is 2.0)
  * per-hour shape preserved: corr(original hourly mean, corrected hourly mean) == 1

Usage:
    python scripts/fix_usdjpy_4h_spread_units.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

SRC = Path("data/spreads/USDJPY_4h_spreads.parquet")
QUARANTINE = Path("data/raw/quarantine_fake_daily_2026-08-17/USDJPY_4h_spreads.parquet")
DAILY = Path("data/spreads/USDJPY_daily_spreads.parquet")


def main() -> int:
    if not SRC.exists():
        print(f"Nothing to fix: {SRC} does not exist")
        return 1
    if QUARANTINE.exists():
        print(f"Quarantine copy already exists: {QUARANTINE} — refusing to re-run")
        return 1

    df = pd.read_parquet(SRC)
    daily = pd.read_parquet(DAILY)
    orig = df.copy()

    df["spread_pips"] = df["spread_pips"] / 10.0

    med, floor = float(df["spread_pips"].median()), float(df["spread_pips"].min())
    daily_med = float(daily["spread_pips"].median())
    if not 1.5 <= med <= 4.0:
        print(f"FAIL: corrected median {med} outside [1.5, 4.0] (daily median {daily_med})")
        return 1
    if not 1.0 <= floor <= 3.0:
        print(f"FAIL: corrected floor {floor} outside [1.0, 3.0]")
        return 1
    shape_corr = (
        orig.groupby("hour")["spread_pips"].mean()
        .corr(df.groupby("hour")["spread_pips"].mean())
    )
    if shape_corr != 1.0:
        print(f"FAIL: intraday shape changed (hourly-mean corr {shape_corr})")
        return 1

    QUARANTINE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, QUARANTINE)
    df.to_parquet(SRC, engine="pyarrow")

    print(f"Quarantined original -> {QUARANTINE}")
    print(f"Wrote corrected {SRC}")
    print(f"  before: median={orig['spread_pips'].median():.2f} min={orig['spread_pips'].min():.2f} "
          f"max={orig['spread_pips'].max():.2f}")
    print(f"  after:  median={med:.2f} min={floor:.2f} max={df['spread_pips'].max():.2f}")
    print(f"  daily reference: median={daily_med:.2f} min={daily['spread_pips'].min():.2f}")
    print(f"  intraday shape preserved (hourly-mean corr = {shape_corr})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
