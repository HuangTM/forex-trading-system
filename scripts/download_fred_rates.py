#!/usr/bin/env python3
"""Download historical central bank rate data from FRED and save as Parquet.

Produces data/rates/rate_differentials.parquet with columns:
    date (index), EURUSD_diff, USDJPY_diff, GBPUSD_diff

These differentials are used by CarryStrategy for dynamic signal generation.

Usage:
    pip install fredapi
    python scripts/download_fred_rates.py --api-key YOUR_FRED_API_KEY
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

try:
    from fredapi import Fred
except ImportError:
    print("fredapi not installed. Run: pip install 'forex-system[research]'")
    sys.exit(1)

# FRED series IDs
SERIES = {
    "USD": "FEDFUNDS",
    "EUR": "ECBMRRFR",
    "JPY": "INTDSRJPM193N",
}

# BOE historical rates: FRED coverage is incomplete, so we provide a manual
# time series of key BOE rate changes. This covers major moves since 2000.
# Source: https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp
BOE_MANUAL = [
    ("2000-01-01", 5.50), ("2001-02-08", 5.75), ("2001-04-05", 5.50),
    ("2001-05-10", 5.25), ("2001-08-02", 5.00), ("2001-09-18", 4.75),
    ("2001-10-04", 4.50), ("2001-11-08", 4.00), ("2003-02-06", 3.75),
    ("2003-07-10", 3.50), ("2003-11-06", 3.75), ("2004-02-05", 4.00),
    ("2004-06-10", 4.50), ("2004-08-05", 4.75), ("2005-08-04", 4.50),
    ("2006-08-03", 4.75), ("2006-11-09", 5.00), ("2007-01-11", 5.25),
    ("2007-07-05", 5.75), ("2007-12-06", 5.50), ("2008-02-07", 5.25),
    ("2008-04-10", 5.00), ("2008-10-08", 4.50), ("2008-11-06", 3.00),
    ("2008-12-04", 2.00), ("2009-01-08", 1.50), ("2009-02-05", 1.00),
    ("2009-03-05", 0.50), ("2016-08-04", 0.25), ("2017-11-02", 0.50),
    ("2018-08-02", 0.75), ("2020-03-11", 0.25), ("2020-03-19", 0.10),
    ("2021-12-16", 0.25), ("2022-02-03", 0.50), ("2022-03-17", 0.75),
    ("2022-05-05", 1.00), ("2022-06-16", 1.25), ("2022-08-04", 1.75),
    ("2022-09-22", 2.25), ("2022-11-03", 3.00), ("2022-12-15", 3.50),
    ("2023-02-02", 4.00), ("2023-03-23", 4.25), ("2023-05-11", 4.50),
    ("2023-06-22", 5.00), ("2023-08-03", 5.25), ("2024-08-01", 5.00),
    ("2024-11-07", 4.75), ("2025-02-06", 4.50), ("2025-05-08", 4.25),
    ("2025-08-07", 4.00), ("2025-11-06", 3.75),
]

OUTPUT_DIR = Path("data/rates")


def download_fred_series(fred: Fred, series_id: str, start: str = "2000-01-01") -> pd.Series:
    """Download a FRED series and return as a pandas Series."""
    data = fred.get_series(series_id, observation_start=start)
    data = data.dropna()
    data.index = pd.to_datetime(data.index)
    data.index.name = "date"
    return data


def build_boe_series() -> pd.Series:
    """Build BOE rate series from manual data."""
    dates = [pd.Timestamp(d) for d, _ in BOE_MANUAL]
    rates = [r for _, r in BOE_MANUAL]
    return pd.Series(rates, index=dates, name="GBP")


def build_rate_differentials(rates: dict[str, pd.Series]) -> pd.DataFrame:
    """Merge rate series and compute pair differentials.

    Returns DataFrame indexed by date with columns:
        EURUSD_diff: EUR rate - USD rate
        USDJPY_diff: USD rate - JPY rate
        GBPUSD_diff: GBP rate - USD rate
    """
    # Create a common daily date range
    all_dates = set()
    for s in rates.values():
        all_dates.update(s.index)
    date_range = pd.date_range(min(all_dates), max(all_dates), freq="B")  # Business days

    # Reindex each series to business days and forward-fill
    aligned = pd.DataFrame(index=date_range)
    aligned.index.name = "date"
    for currency, series in rates.items():
        aligned[currency] = series.reindex(date_range).ffill()

    # Compute differentials (base rate - quote rate for long position)
    result = pd.DataFrame(index=aligned.index)
    result.index.name = "date"
    result["EURUSD_diff"] = (aligned["EUR"] - aligned["USD"]) / 100.0  # Convert % to decimal
    result["USDJPY_diff"] = (aligned["USD"] - aligned["JPY"]) / 100.0
    result["GBPUSD_diff"] = (aligned["GBP"] - aligned["USD"]) / 100.0

    return result.dropna()


def main():
    parser = argparse.ArgumentParser(description="Download FRED rate data for carry strategy")
    parser.add_argument("--api-key", default=os.environ.get("FRED_API_KEY"),
                        help="FRED API key (or set FRED_API_KEY env var)")
    parser.add_argument("--start", default="2000-01-01", help="Start date for data download")
    args = parser.parse_args()

    if not args.api_key:
        print("Error: FRED API key required. Pass --api-key or set FRED_API_KEY.")
        sys.exit(1)

    fred = Fred(api_key=args.api_key)
    rates = {}

    # Download from FRED
    for currency, series_id in SERIES.items():
        print(f"Downloading {currency} ({series_id})...")
        rates[currency] = download_fred_series(fred, series_id, args.start)
        print(f"  Got {len(rates[currency])} observations: "
              f"{rates[currency].index[0].date()} to {rates[currency].index[-1].date()}")

    # Add BOE manual series
    print("Building GBP series from manual BOE data...")
    rates["GBP"] = build_boe_series()
    print(f"  {len(rates['GBP'])} rate changes")

    # Save individual series
    raw_dir = OUTPUT_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for currency, series in rates.items():
        path = raw_dir / f"{currency}.csv"
        series.to_csv(path, header=True)
        print(f"  Saved {path}")

    # Build and save differentials
    print("Computing rate differentials...")
    diffs = build_rate_differentials(rates)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "rate_differentials.parquet"
    diffs.to_parquet(output_path)
    print(f"Saved {output_path} ({len(diffs)} rows, "
          f"{diffs.index[0].date()} to {diffs.index[-1].date()})")

    # Summary
    print("\n=== Latest Differentials ===")
    latest = diffs.iloc[-1]
    for col in diffs.columns:
        pair = col.replace("_diff", "")
        print(f"  {pair}: {latest[col]:+.4f} ({latest[col]*100:+.2f}%)")


if __name__ == "__main__":
    main()
