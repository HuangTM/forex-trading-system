#!/usr/bin/env python3
"""Download the monthly FX factor inputs from FRED (public fredgraph.csv, no API key).

- Spot: Federal Reserve H.10 daily noon buying rates in New York (DEX* series).
- Value: BIS real broad effective exchange rates, monthly (RB*BIS series).

Interest rates come from data/rates/raw/*.csv (scripts/download_fred_rates.py), so the
carry signal uses the same, already-audited rate series as the rest of the repo.

Writes data/factors/raw/{SERIES}.csv (two columns: date, value; FRED "." -> empty).

Usage:
    python scripts/download_fx_factor_data.py
"""

from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

# currency -> (H.10 series, True if quoted as USD per unit of currency)
SPOT = {
    "EUR": ("DEXUSEU", True),
    "GBP": ("DEXUSUK", True),
    "AUD": ("DEXUSAL", True),
    "NZD": ("DEXUSNZ", True),
    "CAD": ("DEXCAUS", False),
    "JPY": ("DEXJPUS", False),
}
REER = {
    "USD": "RBUSBIS", "EUR": "RBXMBIS", "JPY": "RBJPBIS", "GBP": "RBGBBIS",
    "AUD": "RBAUBIS", "NZD": "RBNZBIS", "CAD": "RBCABIS",
}
OUT_DIR = Path("data/factors/raw")
_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def fetch(series_id: str) -> pd.DataFrame:
    req = urllib.request.Request(_URL.format(series_id=series_id), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        df = pd.read_csv(io.BytesIO(resp.read()))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for series_id in [s for s, _ in SPOT.values()] + list(REER.values()):
        df = fetch(series_id)
        df.to_csv(OUT_DIR / f"{series_id}.csv", index=False)
        valid = df.dropna()
        print(f"{series_id:10s} {len(valid):6d} obs  {valid['date'].iloc[0]} -> {valid['date'].iloc[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
