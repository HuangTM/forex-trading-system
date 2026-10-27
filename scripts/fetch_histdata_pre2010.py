#!/usr/bin/env python3
"""Rebuild the 2002-2009 daily holdout used by the carry_fred retest Part B.

HistData whole-year M1 zips (cached in data/raw/histdata_m1/) -> daily bars in
data/holdout_pre2010/{PAIR}_daily.parquet (gitignored). Reuses the fetch/parse/resample
functions of scripts/rebuild_daily_from_histdata.py, whose "current year is fetched
month by month" logic does not suit an end date in 2009/2010. Years HistData lacks
are skipped (CADJPY starts 2007-03, NZDJPY 2006-09, NZDUSD 2005-08).
Bad ticks are NOT cleaned here; scripts/run_carry_retest.py::clean_holdout does that
(rule fixed in references/pre-registrations/carry_fred_retest_2026-10-25.md, Addendum 1).

Usage:
    python scripts/fetch_histdata_pre2010.py
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd  # noqa: E402
import rebuild_daily_from_histdata as H  # noqa: E402

PAIRS = [
    "AUDJPY", "AUDUSD", "CADJPY", "EURGBP", "EURJPY", "EURUSD",
    "GBPJPY", "GBPUSD", "NZDJPY", "NZDUSD", "USDCAD", "USDJPY",
]
CACHE = Path("data/raw/histdata_m1")
OUT = Path("data/holdout_pre2010")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    for pair in PAIRS:
        frames = []
        for year in range(2002, 2010):
            z = CACHE / f"{pair}_M1_{year}.zip"
            try:
                if not z.exists():
                    z.write_bytes(H.fetch_year_zip(pair, year))
                    time.sleep(1.0)
                frames.append(H.parse_m1_zip(z.read_bytes(), pair, year))
            except Exception as e:  # HistData simply lacks some early pair-years
                logging.info("%s %d: unavailable (%s: %s)", pair, year, type(e).__name__, str(e)[:80])
        if not frames:
            logging.info("%s: no data", pair)
            continue
        m1 = pd.concat(frames)
        m1 = m1[~m1.index.duplicated(keep="first")]
        daily = H.resample_to_daily(m1)
        daily = daily[daily.index < pd.Timestamp("2010-01-01", tz="UTC")]
        daily.to_parquet(OUT / f"{pair}_daily.parquet", engine="pyarrow")
        logging.info("%s: %d daily bars %s -> %s", pair, len(daily),
                     daily.index[0].date(), daily.index[-1].date())
    return 0


if __name__ == "__main__":
    sys.exit(main())
