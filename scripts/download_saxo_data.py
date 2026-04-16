#!/usr/bin/env python3
"""Download real historical OHLCV data from Saxo Bank API.

Fetches daily and 4H data for all target pairs, saves as Parquet.
Replaces synthetic data with real market data.

Prerequisites:
    1. Get a 24-hour developer token from https://www.developer.saxo/openapi/token
    2. Pass it via --token or SAXO_TOKEN env var

Usage:
    export SAXO_TOKEN=your_24h_token
    python scripts/download_saxo_data.py
    python scripts/download_saxo_data.py --pairs EURUSD USDJPY --horizon 4h
    python scripts/download_saxo_data.py --start 2010-01-01 --end 2026-04-01
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forex_system.data.storage import save_parquet
from forex_system.data.validation import validate_ohlcv
from forex_system.saxo.client import SaxoClient
from forex_system.saxo.history import bars_to_dataframe, compute_spread_stats

PAIRS = ["EURUSD", "USDJPY", "GBPUSD"]
HORIZONS = ["daily", "4h"]


def main():
    parser = argparse.ArgumentParser(description="Download Saxo historical data")
    parser.add_argument("--token", default=os.environ.get("SAXO_TOKEN"),
                        help="Saxo 24h developer token (or set SAXO_TOKEN)")
    parser.add_argument("--pairs", nargs="+", default=PAIRS,
                        help="Pairs to download")
    parser.add_argument("--horizons", nargs="+", default=HORIZONS,
                        help="Timeframes to download (daily, 4h, 1h)")
    parser.add_argument("--start", default="2010-01-01",
                        help="Start date")
    parser.add_argument("--end", default="2026-04-07",
                        help="End date")
    parser.add_argument("--data-dir", default="data",
                        help="Output directory")
    parser.add_argument("--live", action="store_true",
                        help="Use live API instead of SIM")
    args = parser.parse_args()

    if not args.token:
        print("Error: Saxo token required.")
        print("Get one from: https://www.developer.saxo/openapi/token")
        print("Pass via --token or set SAXO_TOKEN env var.")
        sys.exit(1)

    client = SaxoClient(args.token, live=args.live)

    # Verify connection
    print("Verifying Saxo API connection...")
    try:
        account = client.get_account_info()
        accounts = account.get("Data", [])
        if accounts:
            print(f"  Connected: {accounts[0].get('AccountId', 'unknown')}")
        else:
            print("  Connected (no account data in SIM is normal)")
    except Exception as e:
        print(f"  Connection failed: {e}")
        print("  Token may be expired. Get a new one from the developer portal.")
        sys.exit(1)

    # Download data
    for pair in args.pairs:
        for horizon in args.horizons:
            print(f"\nDownloading {pair} {horizon} ({args.start} to {args.end})...")

            try:
                bars = client.get_chart_data_range(
                    pair, horizon, args.start, args.end,
                    sleep_between=0.6,
                )
                print(f"  Received {len(bars)} bars")

                if not bars:
                    print(f"  WARNING: No data received for {pair} {horizon}")
                    continue

                # Convert to DataFrame
                df = bars_to_dataframe(bars)
                print(f"  DataFrame: {len(df)} rows, "
                      f"{df.index[0].date()} to {df.index[-1].date()}")

                # Validate
                # Use standard OHLCV columns only for validation
                ohlcv = df[["open", "high", "low", "close", "volume"]].copy()
                report = validate_ohlcv(ohlcv, pair)
                if report.issues:
                    print(f"  Validation issues: {report.issues}")
                else:
                    print("  Validation: PASSED")

                # Save OHLCV (standard columns only)
                path = save_parquet(ohlcv, pair, horizon, args.data_dir)
                print(f"  Saved: {path}")

                # Save spread data if available
                spread_stats = compute_spread_stats(df)
                if not spread_stats.empty:
                    spread_dir = Path(args.data_dir) / "spreads"
                    spread_dir.mkdir(parents=True, exist_ok=True)
                    spread_path = spread_dir / f"{pair}_{horizon}_spreads.parquet"
                    spread_stats.to_parquet(spread_path)
                    avg_spread = spread_stats["spread_pips"].mean()
                    print(f"  Spread data saved: avg={avg_spread:.2f} pips")

            except Exception as e:
                print(f"  ERROR: {e}")
                continue

    print("\nDone. Real market data saved to data/processed/.")
    print("Re-run backtests with: python scripts/run_carry_momentum.py")


if __name__ == "__main__":
    main()
