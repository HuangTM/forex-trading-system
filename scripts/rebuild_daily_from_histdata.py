#!/usr/bin/env python3
"""Rebuild daily OHLCV series from HistData.com 1-minute ASCII data.

Created 2026-08-17 to replace 3 synthetic daily files (AUDUSD, USDCAD, EURGBP —
fake data discovered by audit, quarantined to data/raw/quarantine_fake_daily_2026-08-17/).

SOURCE: HistData.com free historical data, "ASCII 1-minute bar quotes".
  - Listing page:  https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{PAIR}/{YEAR}
  - Download:      POST https://www.histdata.com/get.php  (tk token scraped from listing page)
  - Format:        ZIP containing DAT_ASCII_{PAIR}_M1_{YEAR}.csv with rows
                   "YYYYMMDD HHMMSS;open;high;low;close;vol" — bid-side, EST (UTC-5).
  - Free, no registration. One request per pair-year (~3-15 MB zipped).

AGGREGATION: minute bars are shifted EST→UTC (+5h) and resampled to UTC calendar
days (open=first, high=max, low=min, close=last), labelled at 00:00 UTC.
Sunday partial sessions are dropped. This matches the convention of the repo's
9 real daily files (verified: close ratio vs Dukascopy 1h resampled to UTC days
has std 0.06-0.11% over 2021-2025). volume is set to 0.0 as in the existing files.

NOTE: `requests` is avoided deliberately — this environment has TLS/keep-alive
issues with it (same as scripts/ingest_dukascopy_1h.py); raw TLS sockets are used.

Usage:
    python scripts/rebuild_daily_from_histdata.py --pairs AUDUSD USDCAD EURGBP \
        --start-year 2010 --end 2026-04-07 --out-dir data/processed --cache-dir data/raw/histdata_m1
"""
from __future__ import annotations

import argparse
import io
import logging
import re
import ssl
import socket
import sys
import time
import urllib.parse
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger("histdata_daily")

HOST = "www.histdata.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
EST_TO_UTC = pd.Timedelta(hours=5)  # HistData timestamps are EST (UTC-5), constant


def _https(host: str, path: str, method: str = "GET", body: bytes | None = None,
           referer: str | None = None, timeout: float = 60.0) -> bytes:
    """Minimal HTTPS over raw TLS socket (requests times out in this environment).

    Returns the de-chunked response body. Raises RuntimeError on non-200 status.
    """
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
        s.settimeout(timeout)
        s.connect((host, 443))
        head = (f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
                f"User-Agent: {UA}\r\nAccept: */*\r\n")
        if referer:
            head += f"Referer: {referer}\r\n"
        if body is not None:
            head += (f"Content-Type: application/x-www-form-urlencoded\r\n"
                     f"Content-Length: {len(body)}\r\n")
        s.sendall(head.encode() + b"\r\n" + (body or b""))
        chunks: list[bytes] = []
        while True:
            c = s.recv(65536)
            if not c:
                break
            chunks.append(c)
    raw = b"".join(chunks)
    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        raise RuntimeError(f"Truncated HTTP response for {path}")
    header = raw[:sep].decode(errors="replace")
    status = header.splitlines()[0]
    if " 200 " not in status:
        raise RuntimeError(f"HTTP {status} for {method} {path}")
    bdy = raw[sep + 4:]
    if "chunked" in header.lower():
        out = b""
        i = 0
        while i < len(bdy):
            j = bdy.find(b"\r\n", i)
            if j == -1:
                break
            try:
                n = int(bdy[i:j], 16)
            except ValueError:
                break
            if n == 0:
                break
            out += bdy[j + 2:j + 2 + n]
            i = j + 2 + n + 2
        bdy = out
    return bdy


def fetch_year_zip(pair: str, year: int, month: int | None = None,
                   retries: int = 4) -> bytes:
    """Fetch the zipped M1 ASCII file for one pair-year (or pair-month).

    HistData serves past years as one file per year; the CURRENT year is only
    served month-by-month (the year page has no download token), hence the
    optional ``month`` parameter.

    Retries with exponential backoff — the listing/download endpoints drop
    connections intermittently (ConnectionResetError) under any pacing.
    """
    page = (f"/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{year}"
            + (f"/{month}" if month else ""))
    referer = f"https://{HOST}{page}"
    datemonth = f"{year}{month:02d}" if month else str(year)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            html = _https(HOST, page, referer=referer)
            m = re.search(rb'name="tk" id="tk" value="([0-9a-f]+)"', html)
            if not m:
                raise RuntimeError(f"No tk token on listing page for {pair} {datemonth}")
            post = urllib.parse.urlencode({
                "tk": m.group(1).decode(), "date": str(year), "datemonth": datemonth,
                "platform": "ASCII", "timeframe": "M1", "fxpair": pair,
            }).encode()
            zbytes = _https(HOST, "/get.php", method="POST", body=post, referer=referer)
            if zbytes[:2] != b"PK":
                raise RuntimeError(f"Expected ZIP, got {len(zbytes)} bytes starting {zbytes[:40]!r}")
            return zbytes
        except (RuntimeError, OSError, ssl.SSLError) as exc:
            last_exc = exc
            wait = 2.0 * (2 ** attempt)
            log.warning("%s %s: attempt %d failed (%s) — retrying in %.0fs",
                        pair, datemonth, attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"All {retries} attempts failed for {pair} {datemonth}: {last_exc}")


def parse_m1_zip(zbytes: bytes, pair: str, year: int) -> pd.DataFrame:
    """Parse DAT_ASCII_{PAIR}_M1_{YEAR}.csv into a UTC-indexed minute DataFrame."""
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_names:
        raise RuntimeError("No .csv in zip")
    with zf.open(csv_names[0]) as f:
        raw = f.read()
    df = pd.read_csv(
        io.BytesIO(raw), sep=";", header=None,
        names=["ts", "open", "high", "low", "close", "vol"],
        dtype={"ts": str, "open": float, "high": float, "low": float,
               "close": float, "vol": float},
    )
    ts = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
    # HistData timestamps are EST (UTC-5, no DST); shift to UTC.
    idx = pd.DatetimeIndex((ts + EST_TO_UTC).values, tz="UTC", name="datetime")
    df = df.drop(columns=["ts", "vol"])
    df.index = idx
    return df.sort_index()


def resample_to_daily(m1: pd.DataFrame) -> pd.DataFrame:
    """UTC-calendar-day OHLC, weekdays only (Sunday partial sessions dropped),
    volume=0.0 — matching the repo's existing daily-file convention."""
    daily = m1.resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna(subset=["close"])
    daily = daily[daily.index.dayofweek < 5]  # drop Sun partial + any Sat
    daily["volume"] = 0.0
    return daily[["open", "high", "low", "close", "volume"]].astype(float)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--start-year", type=int, default=2010)
    ap.add_argument("--end", default="2026-04-07",
                    help="Exclusive end date (YYYY-MM-DD) for the output series")
    ap.add_argument("--out-dir", default="data/processed")
    ap.add_argument("--cache-dir", default="data/raw/histdata_m1",
                    help="Where raw zips are cached (re-run reuses cache)")
    ap.add_argument("--request-delay", type=float, default=1.0)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    end_ts = pd.Timestamp(args.end, tz="UTC")

    for pair in [p.upper() for p in args.pairs]:
        frames = []
        for year in range(args.start_year, end_ts.year + 1):
            # Current year is served month-by-month only (no year-level token).
            if year == end_ts.year:
                months = range(1, end_ts.month + 1)
                for month in months:
                    zpath = cache / f"{pair}_M1_{year}-{month:02d}.zip"
                    if not zpath.exists():
                        log.info("%s %d-%02d: downloading...", pair, year, month)
                        zbytes = fetch_year_zip(pair, year, month=month)
                        zpath.write_bytes(zbytes)
                        time.sleep(args.request_delay)
                    else:
                        log.info("%s %d-%02d: cache hit", pair, year, month)
                        zbytes = zpath.read_bytes()
                    frames.append(parse_m1_zip(zbytes, pair, year))
                continue
            zpath = cache / f"{pair}_M1_{year}.zip"
            if not zpath.exists():
                log.info("%s %d: downloading...", pair, year)
                zbytes = fetch_year_zip(pair, year)
                zpath.write_bytes(zbytes)
                time.sleep(args.request_delay)
            else:
                log.info("%s %d: cache hit", pair, year)
                zbytes = zpath.read_bytes()
            frames.append(parse_m1_zip(zbytes, pair, year))
        m1 = pd.concat(frames)
        m1 = m1[~m1.index.duplicated(keep="first")]
        daily = resample_to_daily(m1)
        daily = daily[(daily.index >= pd.Timestamp(args.start_year, 1, 1, tz="UTC"))
                      & (daily.index < end_ts)]
        out = Path(args.out_dir) / f"{pair}_daily.parquet"
        daily.to_parquet(out, engine="pyarrow")
        log.info("%s: wrote %d daily bars %s -> %s  (%s)",
                 pair, len(daily), daily.index[0].date(), daily.index[-1].date(), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
