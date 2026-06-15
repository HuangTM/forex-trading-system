"""Dukascopy 1h-bar ingest: fetches bi5 tick files, resamples to 1h OHLCV parquet.

NETWORK PROTOCOL NOTE:
  Dukascopy's datafeed endpoint (datafeed.dukascopy.com) uses standard HTTPS but
  the Python `requests` library times out due to TLS/keep-alive behaviour in this
  environment.  This script uses a raw TLS socket to bypass that issue — the same
  HTTP semantics, just without `requests`.  Users running from a normal network
  can swap in `requests.get(url).content` if they prefer.

TIMEZONE:
  Dukascopy tick millisecond timestamps are offsets from the START OF EACH HOUR
  in UTC.  The hour is determined by the URL path (YYYY/MM_0indexed/DD/HHh_ticks.bi5).
  Output index is tz-aware UTC DatetimeIndex.  See PROVENANCE.md for spot-check evidence.

VOLUME PROXY:
  FX has no central exchange volume.  The `volume` column stores the SUM of
  Dukascopy ask-side volume (lot proxy) across ticks in each 1h bar.  This is a
  venue-specific liquidity proxy, NOT exchange volume.  Label clearly in any
  strategy that uses it.

CLI USAGE:
  python scripts/ingest_dukascopy_1h.py --pair EURUSD --start 2024-01-01 --end 2024-02-01 \
      --out data/processed/EURUSD_1h.parquet

  # Full backfill (user-run, after verifying proof pull):
  for PAIR in AUDJPY AUDUSD CADJPY EURGBP EURJPY EURUSD GBPJPY GBPUSD NZDJPY NZDUSD USDCAD USDJPY; do
      python scripts/ingest_dukascopy_1h.py --pair $PAIR --start 2010-01-01 --end 2026-05-01 \
          --out data/processed/${PAIR}_1h.parquet
  done
"""

from __future__ import annotations

import argparse
import lzma
import logging
import ssl
import socket
import struct
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dukascopy instrument name mapping
# Dukascopy uses the EURUSD form (no slash), same as the firm's convention.
# ---------------------------------------------------------------------------
DUKASCOPY_INSTRUMENTS: dict[str, str] = {
    "AUDJPY": "AUDJPY",
    "AUDUSD": "AUDUSD",
    "CADJPY": "CADJPY",
    "EURGBP": "EURGBP",
    "EURJPY": "EURJPY",
    "EURUSD": "EURUSD",
    "GBPJPY": "GBPJPY",
    "GBPUSD": "GBPUSD",
    "NZDJPY": "NZDJPY",
    "NZDUSD": "NZDUSD",
    "USDCAD": "USDCAD",
    "USDJPY": "USDJPY",
}

# JPY pairs have 3 decimal places (pip = 0.01), others have 5 (pip = 0.0001).
# Dukascopy stores prices as integer * 1e5 for all pairs.  JPY pairs
# therefore need dividing by 1e3 not 1e5.
JPY_PAIRS: frozenset[str] = frozenset(
    {"AUDJPY", "CADJPY", "EURJPY", "GBPJPY", "NZDJPY", "USDJPY"}
)

_DUKA_HOST = "datafeed.dukascopy.com"
_DUKA_PORT = 443
_TICK_STRUCT = struct.Struct(">IIIff")  # ms, ask*1e5, bid*1e5, ask_vol, bid_vol
_TICK_SIZE = 20  # bytes per tick record


# ---------------------------------------------------------------------------
# Network layer — raw TLS socket (requests lib times out in this environment)
# ---------------------------------------------------------------------------

def _classify_http_response(raw: bytes) -> bytes | None:
    """Classify a raw HTTP/1.1 response into the fetch contract. Pure function.

    Returns:
        - body bytes on HTTP 200 (body may legitimately be empty for a closed hour);
        - b'' on HTTP 404 (genuinely-missing/pre-listing hour) — caller does NOT retry;
        - None on any RETRYABLE condition: truncated response (no header terminator),
          or any non-200/404 status (429 rate-limit, 5xx, unparseable status line).

    Distinguishing b'' (genuine empty) from None (failure) is the crux of the
    data-integrity fix: collapsing failures into b'' silently drops bars.
    """
    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        return None  # truncated/no complete header → retryable
    header = raw[:sep].decode("utf-8", errors="replace")
    status_line = header.splitlines()[0] if header else ""
    parts = status_line.split()
    code = parts[1] if len(parts) >= 2 and parts[1].isdigit() else ""
    if code == "200":
        return raw[sep + 4:]
    if code == "404":
        return b""
    return None  # 429 / 5xx / unparseable → retryable


def _fetch_bi5(instrument: str, year: int, month_0based: int, day: int, hour: int,
               timeout: float = 30.0) -> bytes | None:
    """Fetch a single bi5 tick file from Dukascopy.

    Returns the raw (LZMA-compressed) body bytes on success.  Returns b'' for a
    genuinely-empty hour (HTTP 200 with empty body — a closed weekend hour — or
    HTTP 404 — a non-existent/pre-listing hour); the caller treats b'' as a valid
    empty bar and does NOT retry.  Returns None on a RETRYABLE failure (socket
    timeout, OS/connection error, truncated response, or any non-200/404 status
    such as a 429 rate-limit or 5xx); the caller retries on None.  Distinguishing
    these is critical: collapsing failures into b'' silently drops bars and, over
    a full window, can cache an entire empty year as if it were genuine.

    Args:
        instrument: Dukascopy instrument code e.g. 'EURUSD'.
        year: 4-digit year.
        month_0based: 0-based month index (January = 0).
        day: Day of month (1-31).
        hour: Hour of day UTC (0-23).
        timeout: Socket operation timeout in seconds.
    """
    path = f"/datafeed/{instrument}/{year:04d}/{month_0based:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
    ctx = ssl.create_default_context()
    try:
        with ctx.wrap_socket(socket.socket(), server_hostname=_DUKA_HOST) as s:
            s.settimeout(timeout)
            s.connect((_DUKA_HOST, _DUKA_PORT))
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {_DUKA_HOST}\r\n"
                f"Connection: close\r\n\r\n"
            )
            s.sendall(request.encode())
            chunks: list[bytes] = []
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
    except socket.timeout:
        logger.warning(f"Timeout fetching {path} — retryable")
        return None
    except OSError as e:
        logger.warning(f"Socket error fetching {path}: {e} — retryable")
        return None

    result = _classify_http_response(b"".join(chunks))
    if result is None:
        logger.warning(f"Retryable response for {path} (truncated or non-200/404)")
    return result


# ---------------------------------------------------------------------------
# Tick parsing and OHLCV resampling
# ---------------------------------------------------------------------------

def _decode_bi5(body: bytes | None, bar_start_utc: datetime, instrument: str) -> pd.DataFrame:
    """Decompress and parse a bi5 body into a tick DataFrame.

    Returns a DataFrame with columns [timestamp_utc, mid, ask_vol] where
    timestamp_utc is tz-aware UTC.  Empty body → empty DataFrame.

    The price divisor is 1e5 for non-JPY pairs and 1e3 for JPY pairs
    (Dukascopy stores all prices as integer * 1e5, but JPY pairs have only
    3 significant decimal places so the effective divisor is 1e3).
    """
    if not body:
        return pd.DataFrame(columns=["timestamp_utc", "mid", "ask_vol"])

    try:
        raw = lzma.decompress(body)
    except lzma.LZMAError as e:
        logger.warning(f"LZMA decompress failed for {bar_start_utc}: {e}")
        return pd.DataFrame(columns=["timestamp_utc", "mid", "ask_vol"])

    n_ticks = len(raw) // _TICK_SIZE
    if n_ticks == 0:
        return pd.DataFrame(columns=["timestamp_utc", "mid", "ask_vol"])

    # Unpack all ticks at once
    ticks = _TICK_STRUCT.iter_unpack(raw[: n_ticks * _TICK_SIZE])

    divisor = 1e3 if instrument in JPY_PAIRS else 1e5

    rows: list[tuple[datetime, float, float]] = []
    base_ts = bar_start_utc.timestamp() * 1000  # milliseconds since epoch for this hour
    for ms, ask_raw, bid_raw, ask_vol, _bid_vol in ticks:
        ts_ms = base_ts + ms
        ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        mid = (ask_raw + bid_raw) / 2.0 / divisor
        rows.append((ts, mid, float(ask_vol)))

    df = pd.DataFrame(rows, columns=["timestamp_utc", "mid", "ask_vol"])
    return df


def _resample_ticks_to_1h(ticks_df: pd.DataFrame, bar_start_utc: datetime) -> dict[str, float] | None:
    """Resample tick DataFrame to a single 1h OHLCV bar dict.

    Returns None if there are no ticks (empty/weekend hour).

    OHLC from mid-price: open=first, high=max, low=min, close=last.
    Volume = sum(ask_vol) — Dukascopy ask-side lot proxy.
    """
    if ticks_df.empty:
        return None

    mid = ticks_df["mid"]
    return {
        "open": float(mid.iloc[0]),
        "high": float(mid.max()),
        "low": float(mid.min()),
        "close": float(mid.iloc[-1]),
        "volume": float(ticks_df["ask_vol"].sum()),
    }


# ---------------------------------------------------------------------------
# Hourly fetch loop → DataFrame
# ---------------------------------------------------------------------------

def fetch_1h_bars(
    instrument: str,
    start: datetime,
    end: datetime,
    retry_attempts: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 30.0,
    request_delay: float = 0.0,
) -> pd.DataFrame:
    """Fetch all 1h bars for an instrument over [start, end).

    Args:
        instrument: Dukascopy instrument code e.g. 'EURUSD'.
        start: Start datetime (UTC, inclusive).
        end: End datetime (UTC, exclusive).
        retry_attempts: Number of retry attempts per hour on network error.
        retry_delay: Seconds to wait between retries.
        timeout: Per-request socket timeout (s). Lower → fail fast under a
            throttling/tarpit server instead of blocking the full default.
        request_delay: Seconds to sleep after each hourly request. A small
            value paces the fetch under a rate-limiting source.

    Returns:
        DataFrame with tz-aware UTC DatetimeIndex and OHLCV columns.
        Volume column is the ask-volume proxy (see module docstring).
    """
    if instrument in JPY_PAIRS:
        logger.info(f"{instrument}: JPY pair — price divisor 1e3")
    else:
        logger.info(f"{instrument}: non-JPY pair — price divisor 1e5")

    bars: list[dict] = []
    current = start.replace(minute=0, second=0, microsecond=0)
    total_hours = int((end - current).total_seconds() / 3600)
    fetched = 0
    empty = 0

    logger.info(f"Fetching {instrument} {start.date()} → {end.date()}, ~{total_hours} hours")

    while current < end:
        # Dukascopy URL uses 0-based month
        month_0 = current.month - 1

        body = b""
        for attempt in range(retry_attempts):
            body = _fetch_bi5(instrument, current.year, month_0, current.day,
                              current.hour, timeout=timeout)
            if body is not None:  # b'' is valid (empty hour), only None means "retry"
                break
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay * (2 ** attempt))  # exponential backoff

        ticks_df = _decode_bi5(body, current, instrument)
        bar = _resample_ticks_to_1h(ticks_df, current)

        if bar is not None:
            bar["datetime"] = current
            bars.append(bar)
            fetched += 1
        else:
            empty += 1

        if request_delay:
            time.sleep(request_delay)
        current += timedelta(hours=1)

    logger.info(f"Done: {fetched} bars fetched, {empty} empty hours (weekends/closed)")

    if not bars:
        logger.warning(f"No bars fetched for {instrument} {start.date()} → {end.date()}")
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(bars)
    df = df.set_index("datetime")
    df.index = pd.DatetimeIndex(df.index, tz=timezone.utc)
    df.index.name = "datetime"
    df = df[["open", "high", "low", "close", "volume"]]  # canonical column order
    df = df.sort_index()

    # Dedup (should never happen with hourly URL fetches, but be defensive)
    n_before = len(df)
    df = df[~df.index.duplicated(keep="first")]
    if len(df) < n_before:
        logger.warning(f"Removed {n_before - len(df)} duplicate timestamps")

    return df


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

# Data-quality thresholds, calibrated against clean Dukascopy majors so that
# normal market microstructure never trips them (EURUSD 2021-2025: 0 zero-vol
# bars, 0 fully-flat-OHLC bars, max 1h |move| 1.74%). They fire only on the
# corruption signatures a happy-path schema check misses (a throttled/cached
# fetch silently repeating a body, a resample emitting a no-liquidity bar, an
# integer-overflow price spike). See data-capability hardening 2026-06-15.
STALE_OHLC_RUN_THRESHOLD = 6   # ≥6 consecutive bars with identical O=H=L=C = cached/repeated body
SPIKE_PCT_THRESHOLD = 0.10     # |1h close-to-close move| > 10% on a major = corrupt tick, not news


def _max_identical_ohlc_run(df: pd.DataFrame) -> int:
    """Longest run of consecutive bars whose (O,H,L,C) all equal the prior bar's.

    A handful of isolated flat bars are normal in thin hours; a LONG run of an
    identical body is the fingerprint of a fetch that silently repeated a cached
    response across many hours (the QRB-6 data-corruption class).
    """
    if len(df) < 2:
        return 0
    same = (
        (df["open"].diff() == 0)
        & (df["high"].diff() == 0)
        & (df["low"].diff() == 0)
        & (df["close"].diff() == 0)
    ).to_numpy()
    max_run = run = 0
    for v in same:
        run = run + 1 if v else 0
        max_run = max(max_run, run)
    # +1 because a run of N "equal-to-prior" flags spans N+1 identical bars
    return max_run + 1 if max_run else 0


def validate_1h_schema(df: pd.DataFrame, pair: str) -> list[str]:
    """Validate output schema AND data quality matches firm conventions.

    Returns a list of issue strings (empty == clean). Covers structural schema
    (columns, UTC index, monotonic/unique, OHLC internal consistency) plus the
    data-quality gates that catch silent corruption: zero/negative volume,
    repeated-body stale runs, and outlier price spikes.
    """
    issues: list[str] = []

    # Columns
    required = {"open", "high", "low", "close", "volume"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        issues.append(f"Missing columns: {missing_cols}")

    # Index
    if not isinstance(df.index, pd.DatetimeIndex):
        issues.append("Index is not DatetimeIndex")
    elif df.index.tz is None:
        issues.append("Index is tz-naive — must be tz-aware UTC")
    elif str(df.index.tz) not in ("UTC", "utc"):
        issues.append(f"Index tz is {df.index.tz}, expected UTC")

    # Monotonic + unique
    if not df.index.is_monotonic_increasing:
        issues.append("Index is not monotonically increasing")
    if df.index.duplicated().any():
        issues.append("Index has duplicate timestamps")

    # OHLC consistency
    if not missing_cols:
        bad_high = (df["high"] < df[["open", "close"]].max(axis=1)).sum()
        bad_low = (df["low"] > df[["open", "close"]].min(axis=1)).sum()
        if bad_high:
            issues.append(f"{bad_high} bars where high < max(open,close)")
        if bad_low:
            issues.append(f"{bad_low} bars where low < min(open,close)")

        # NaN / non-positive prices — a bar exists but a field is missing/garbage
        n_nan = int(df[["open", "high", "low", "close"]].isna().to_numpy().sum())
        if n_nan:
            issues.append(f"{n_nan} NaN price values")
        n_nonpos = int((df[["open", "high", "low", "close"]] <= 0).to_numpy().sum())
        if n_nonpos:
            issues.append(f"{n_nonpos} non-positive price values")

        # Zero/negative volume — a real OHLC bar means ticks existed, so vol > 0;
        # vol <= 0 is a resample/fetch artifact (real price, no liquidity signal).
        n_zerovol = int((df["volume"] <= 0).sum())
        if n_zerovol:
            issues.append(f"{n_zerovol} bars with volume <= 0")

        # Stale repeated-body run (cached-fetch corruption)
        stale_run = _max_identical_ohlc_run(df)
        if stale_run >= STALE_OHLC_RUN_THRESHOLD:
            issues.append(
                f"stale data: {stale_run} consecutive identical-OHLC bars "
                f"(>= {STALE_OHLC_RUN_THRESHOLD})"
            )

        # Outlier price spike (corrupt tick / integer overflow)
        if len(df) > 1:
            n_spike = int((df["close"].pct_change().abs() > SPIKE_PCT_THRESHOLD).sum())
            if n_spike:
                worst = float(df["close"].pct_change().abs().max()) * 100
                issues.append(
                    f"{n_spike} price spikes > {SPIKE_PCT_THRESHOLD:.0%} 1h move "
                    f"(worst {worst:.1f}%)"
                )

    return issues


# ---------------------------------------------------------------------------
# Weekend gap spot-check (TZ correctness gate)
# ---------------------------------------------------------------------------

def spot_check_weekend_gap(df: pd.DataFrame) -> dict[str, object]:
    """Verify the Friday 21:00 UTC → Sunday 21:00 UTC weekend gap.

    FX markets close at approximately Friday 21:00 UTC and reopen at
    approximately Sunday 21:00 UTC.  This spot-check verifies that the
    1h bar index respects this gap — confirming UTC timestamps are correct.

    Returns a dict with 'passed' bool and diagnostic info.
    """
    # Find Fridays in the data
    fridays = df.index[df.index.dayofweek == 4]  # 4 = Friday
    if len(fridays) == 0:
        return {"passed": False, "reason": "no Fridays in data range"}

    # Check that no bars exist on Saturday (dayofweek == 5)
    saturdays = df.index[df.index.dayofweek == 5]
    n_saturday_bars = len(saturdays)

    # Check that most Fridays have bars up to ~21:00 UTC
    late_fridays = fridays[fridays.hour >= 20]

    result = {
        "passed": n_saturday_bars == 0,
        "n_saturday_bars": int(n_saturday_bars),
        "n_fridays_in_data": int(len(fridays)),
        "n_fridays_with_hour_ge_20": int(len(late_fridays)),
        "reason": "OK" if n_saturday_bars == 0 else f"{n_saturday_bars} bars found on Saturday — possible tz error",
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Dukascopy 1h bars and write to parquet."
    )
    parser.add_argument("--pair", required=True, help="Currency pair e.g. EURUSD")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD (UTC, inclusive)")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD (UTC, exclusive)")
    parser.add_argument("--out", required=True, help="Output parquet path")
    parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    pair = args.pair.upper()
    if pair not in DUKASCOPY_INSTRUMENTS:
        logger.error(f"Unknown pair: {pair}. Supported: {sorted(DUKASCOPY_INSTRUMENTS)}")
        return 1

    instrument = DUKASCOPY_INSTRUMENTS[pair]

    try:
        start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    except ValueError as e:
        logger.error(f"Invalid date: {e}")
        return 1

    if end <= start:
        logger.error(f"end ({args.end}) must be after start ({args.start})")
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Fetch
    df = fetch_1h_bars(instrument, start, end)

    if df.empty:
        logger.error("No data fetched — check network connectivity to datafeed.dukascopy.com")
        return 1

    # Validate schema
    issues = validate_1h_schema(df, pair)
    if issues:
        logger.error(f"Schema validation FAILED: {issues}")
        return 1

    # TZ spot-check (weekend gap)
    gap_check = spot_check_weekend_gap(df)
    if gap_check["passed"]:
        logger.info(f"Weekend gap spot-check PASSED: {gap_check}")
    else:
        logger.warning(f"Weekend gap spot-check WARN: {gap_check}")

    # Write parquet
    df.to_parquet(out_path, engine="pyarrow")
    logger.info(f"Written {len(df)} bars → {out_path}")
    logger.info(f"  Date range: {df.index[0]} → {df.index[-1]}")
    logger.info(f"  Columns: {list(df.columns)}")
    logger.info("  Volume is Dukascopy ask-side lot proxy (NOT exchange volume)")

    # Reload and verify round-trip
    df_check = pd.read_parquet(out_path)
    assert len(df_check) == len(df), "Round-trip parquet length mismatch"
    assert str(df_check.index.tz) in ("UTC", "utc"), "Round-trip tz not UTC"
    logger.info("Parquet round-trip check: OK")

    print("\nSummary:")
    print(f"  Pair:       {pair}")
    print(f"  Window:     {args.start} → {args.end}")
    print(f"  Bars:       {len(df)}")
    print(f"  UTC range:  {df.index[0]} → {df.index[-1]}")
    print(f"  Output:     {out_path}")
    print(f"  Weekend gap check: {'PASSED' if gap_check['passed'] else 'WARN — see log'}")
    print("  NOTE: volume column = Dukascopy ask-vol proxy, not exchange volume")
    return 0


if __name__ == "__main__":
    sys.exit(main())
