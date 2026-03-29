#!/usr/bin/env python3
"""Download historical forex data and prepare for backtesting.

Generates synthetic data for development/testing, or loads from CSV files.

Usage:
    python scripts/download_data.py --pairs EURUSD USDJPY GBPUSD --years 10
    python scripts/download_data.py --source csv --csv-dir data/raw/
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from forex_system.data.storage import save_parquet
from forex_system.data.validation import validate_ohlcv
from forex_system.data.sources.csv_source import CSVSource


def generate_synthetic_forex(
    pair: str,
    years: int = 10,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic synthetic daily forex data for development.

    Uses geometric Brownian motion with realistic volatility per pair.
    NOT for production backtesting — only for development and testing.
    """
    rng = np.random.default_rng(seed + hash(pair) % 10000)

    n_days = years * 252
    dates = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=n_days, freq="B")
    n_days = len(dates)  # Actual count may differ slightly

    # Realistic starting prices and volatilities
    pair_params = {
        "EURUSD": {"start": 1.1200, "vol": 0.005},
        "USDJPY": {"start": 110.00, "vol": 0.005},
        "GBPUSD": {"start": 1.3000, "vol": 0.006},
        "AUDUSD": {"start": 0.7500, "vol": 0.006},
        "USDCHF": {"start": 0.9200, "vol": 0.005},
    }

    params = pair_params.get(pair.upper(), {"start": 1.0000, "vol": 0.005})
    start_price = params["start"]
    daily_vol = params["vol"]

    # Generate daily returns with slight mean-reversion
    returns = rng.normal(0, daily_vol, n_days)
    prices = start_price * np.exp(np.cumsum(returns))

    # Generate OHLCV from close prices
    close = prices
    daily_range = np.abs(rng.normal(0, daily_vol * 0.7, n_days)) * prices
    high = close + daily_range * rng.uniform(0.3, 0.7, n_days)
    low = close - daily_range * rng.uniform(0.3, 0.7, n_days)

    # Open is previous close with small gap
    open_prices = np.roll(close, 1) * (1 + rng.normal(0, daily_vol * 0.1, n_days))
    open_prices[0] = start_price

    # Ensure OHLC consistency
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))

    volume = rng.uniform(50000, 200000, n_days)

    df = pd.DataFrame(
        {
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=pd.DatetimeIndex(dates, tz="UTC", name="datetime"),
    )

    return df


def main():
    parser = argparse.ArgumentParser(description="Download/generate forex data")
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["EURUSD", "USDJPY", "GBPUSD"],
        help="Currency pairs to download",
    )
    parser.add_argument("--years", type=int, default=10, help="Years of history")
    parser.add_argument(
        "--source",
        choices=["synthetic", "csv"],
        default="synthetic",
        help="Data source (synthetic for dev, csv for real data)",
    )
    parser.add_argument("--csv-dir", type=str, default="data/raw/", help="CSV directory")
    parser.add_argument("--data-dir", type=str, default="data", help="Output data directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    for pair in args.pairs:
        pair = pair.upper()
        print(f"Processing {pair}...")

        if args.source == "csv":
            source = CSVSource(args.csv_dir)
            df = source.fetch(pair, "2000-01-01", "2030-12-31")
        else:
            print(f"  Generating {args.years} years of synthetic data...")
            df = generate_synthetic_forex(pair, years=args.years)

        # Validate
        report = validate_ohlcv(df, pair)
        if report.issues:
            print(f"  Validation issues: {report.issues}")
        else:
            print(f"  Validation: PASSED ({report.row_count} bars)")

        # Save to parquet
        path = save_parquet(df, pair, "daily", str(data_dir))
        print(f"  Saved to {path}")
        if report.date_range:
            print(f"  Date range: {report.date_range[0]} to {report.date_range[1]}")

    print("\nDone. Data ready for backtesting.")


if __name__ == "__main__":
    main()
