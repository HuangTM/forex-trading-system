#!/usr/bin/env python3
"""Generate synthetic 4H forex data for testing sub-daily carry strategy.

Produces ~15,000 bars (6 per trading day, 10 years) with realistic
volatility patterns (London/NY sessions more volatile than Asian).

This is synthetic data for testing the pipeline — NOT for production
backtesting. Real 4H data should come from Saxo Bank API or Dukascopy.

Usage:
    python scripts/generate_4h_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from forex_system.data.storage import save_parquet
from forex_system.data.validation import validate_ohlcv

PAIRS = {
    "EURUSD": {"start": 1.1200, "vol": 0.0025},
    "USDJPY": {"start": 110.00, "vol": 0.0025},
    "GBPUSD": {"start": 1.3000, "vol": 0.0030},
}

# 4H session volatility multipliers (6 sessions per 24h)
# UTC: 00, 04, 08, 12, 16, 20
SESSION_VOL = [0.6, 0.7, 1.3, 1.5, 1.2, 0.7]  # Asian low, London/NY high


def generate_4h_forex(pair: str, years: int = 10, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic 4H forex data."""
    rng = np.random.default_rng(seed + hash(pair) % 10000)
    params = PAIRS.get(pair, {"start": 1.0, "vol": 0.0025})

    # Generate 4H timestamps: 6 per trading day, weekdays only
    start = pd.Timestamp("2016-01-04", tz="UTC")  # First Monday of 2016
    end = pd.Timestamp("2026-03-27", tz="UTC")

    # Build weekday-only 4H index
    all_4h = pd.date_range(start, end, freq="4h", tz="UTC")
    # Filter to weekdays and trading hours (Sun 22:00 to Fri 22:00 UTC for FX)
    # Simplified: keep only Monday-Friday bars
    weekday_mask = all_4h.weekday < 5
    timestamps = all_4h[weekday_mask]
    n = len(timestamps)

    # Session-based volatility
    hours = timestamps.hour
    vol_multipliers = np.array([SESSION_VOL[h // 4] for h in hours])
    bar_vol = params["vol"] * vol_multipliers

    # Generate returns
    returns = rng.normal(0, bar_vol)
    # Add slight mean-reversion to prevent drift
    prices = np.zeros(n)
    prices[0] = params["start"]
    for i in range(1, n):
        mean_rev = -0.001 * (prices[i - 1] - params["start"]) / params["start"]
        prices[i] = prices[i - 1] * np.exp(returns[i] + mean_rev)

    close = prices
    bar_range = np.abs(rng.normal(0, bar_vol * 0.7)) * prices
    high = close + bar_range * rng.uniform(0.3, 0.7, n)
    low = close - bar_range * rng.uniform(0.3, 0.7, n)

    open_prices = np.roll(close, 1) * (1 + rng.normal(0, bar_vol * 0.05))
    open_prices[0] = params["start"]

    # Ensure OHLC consistency
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))

    volume = rng.uniform(10000, 80000, n) * vol_multipliers

    df = pd.DataFrame(
        {
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=pd.DatetimeIndex(timestamps, name="datetime"),
    )

    return df


def main():
    data_dir = Path("data")

    for pair in PAIRS:
        print(f"Generating 4H data for {pair}...")
        df = generate_4h_forex(pair)

        report = validate_ohlcv(df, pair)
        if report.issues:
            print(f"  Validation issues: {report.issues}")
        else:
            print(f"  Validation: PASSED ({report.row_count} bars)")

        path = save_parquet(df, pair, "4h", str(data_dir))
        print(f"  Saved to {path}")
        print(f"  Range: {df.index[0]} to {df.index[-1]}")

    print("\nDone. 4H data ready for backtesting.")
    print("NOTE: This is SYNTHETIC data. Use Saxo API for real 4H data.")


if __name__ == "__main__":
    main()
