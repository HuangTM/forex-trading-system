#!/usr/bin/env python3
"""Fetch CFTC legacy COT (futures only) for the CME currency contracts.

Writes data/factors/raw/cot_legacy_fx.csv: one row per (as-of Tuesday, currency) with
noncommercial (speculative) long/short and open interest. Contracts are joined by
CFTC contract market code because the exchange names changed over time (GBP, AUD, NZD).

Source: https://www.cftc.gov/files/dea/history/deacot1986_2016.zip and deacotYYYY.zip.
The files carry only the as-of date, not the release date (normally the Friday after,
15:30 ET; later during the 2013, 2018-19 and 2025 government shutdowns).

Usage:
    python scripts/fetch_cot_legacy_fx.py                  # download
    python scripts/fetch_cot_legacy_fx.py --raw-dir DIR    # reuse downloaded zips
"""

from __future__ import annotations

import argparse
import io
import tempfile
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

BASE_URL = "https://www.cftc.gov/files/dea/history"
OUT = Path(__file__).resolve().parent.parent / "data/factors/raw/cot_legacy_fx.csv"
CODES = {"099741": "EUR", "097741": "JPY", "096742": "GBP", "232741": "AUD",
         "112741": "NZD", "090741": "CAD", "092741": "CHF"}
COLS = {
    "As of Date in Form YYYY-MM-DD": "as_of",
    "CFTC Contract Market Code": "code",
    "Market and Exchange Names": "market",
    "Noncommercial Positions-Long (All)": "noncomm_long",
    "Noncommercial Positions-Short (All)": "noncomm_short",
    "Open Interest (All)": "open_interest",
}


def _files() -> list[str]:
    return ["deacot1986_2016.zip"] + [f"deacot{y}.zip" for y in range(2017, date.today().year + 1)]


def _download(raw_dir: Path) -> None:
    for name in _files():
        target = raw_dir / name
        if not target.exists():
            print(f"  downloading {name}")
            urllib.request.urlretrieve(f"{BASE_URL}/{name}", target)


def build(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for name in _files():
        with zipfile.ZipFile(raw_dir / name) as zf:
            for member in zf.namelist():
                df = pd.read_csv(io.BytesIO(zf.read(member)), low_memory=False,
                                 usecols=lambda c: c in COLS)
                frames.append(df.rename(columns=COLS))
    df = pd.concat(frames, ignore_index=True)
    df["code"] = df["code"].astype(str).str.strip()
    # 099741 also carried the European Currency Unit contract in 1986, which is not the euro.
    df = df[df["code"].isin(CODES) & ~df["market"].str.contains("EUROPEAN CURRENCY UNIT")].copy()
    df["ccy"] = df["code"].map(CODES)
    df["as_of"] = pd.to_datetime(df["as_of"]).dt.date
    df = df.drop_duplicates(["ccy", "as_of"]).sort_values(["ccy", "as_of"])
    return df[["as_of", "ccy", "code", "market", "noncomm_long", "noncomm_short", "open_interest"]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw-dir", type=Path, help="directory holding (or to receive) the zips")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = args.raw_dir or Path(tmp)
        _download(raw_dir)
        df = build(raw_dir)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Saved {OUT} ({len(df)} rows, {df['as_of'].min()}..{df['as_of'].max()})")
    print(df.groupby("ccy")["as_of"].agg(["min", "max", "count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
