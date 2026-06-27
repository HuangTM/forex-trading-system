#!/usr/bin/env python3
"""Resumable, year-chunked Dukascopy 1h backfill for all 12 pairs.

Reuses the tested fetch path in ``ingest_dukascopy_1h.py``. Each ``(pair, year)``
window is pulled into a checkpoint chunk under ``data/processed/_chunks/`` and
written atomically, so an interrupted run loses at most one in-progress
pair-year and auto-resumes on re-run (existing chunks are skipped). After all
year-chunks for a pair exist, they are concatenated, de-duplicated and sorted
into ``data/processed/{PAIR}_1h.parquet``.

Why this wrapper exists: the underlying ingest script accumulates an entire
multi-year pull in memory and writes the parquet ONCE at the end, so a single
network blip near the end of a 16-year pull discards everything. Chunking caps
the blast radius to one year (~2h) and makes the long run survivable in an
ephemeral environment.

Usage:
    python3 scripts/backfill_dukascopy_all.py                 # full default backfill
    python3 scripts/backfill_dukascopy_all.py --pairs EURUSD,USDJPY --start-year 2021
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INGEST_PATH = ROOT / "scripts" / "ingest_dukascopy_1h.py"

# Load the tested ingest module as a library (its __main__ guard means import
# does not run main()).
_spec = importlib.util.spec_from_file_location("ingest_dukascopy_1h", INGEST_PATH)
ing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ing)

PAIRS = [
    "AUDJPY", "AUDUSD", "CADJPY", "EURGBP", "EURJPY", "EURUSD",
    "GBPJPY", "GBPUSD", "NZDJPY", "NZDUSD", "USDCAD", "USDJPY",
]
COLS = ["open", "high", "low", "close", "volume",
        "spread_median_pips", "spread_mean_pips", "spread_p90_pips"]

# A FULL (non-partial) calendar month of active FX 1h bars is ~300-500. A
# non-partial month with 0 < bars < this floor is almost certainly a partial
# pull (interrupted/throttled mid-month), not real data — flag for review.
# Checkpointing is MONTHLY (not yearly) so a stall loses ≤1 month of work, not
# a whole year — learned the hard way: an 8h run with year-checkpoints stalled
# on source throttling and saved nothing because no full year completed.
SUSPECT_FLOOR = 100


def _empty_1h_frame() -> pd.DataFrame:
    # COLS includes the spread columns — present in all new-style frames.
    # Pre-existing chunks without spread columns will be handled by backward-compat
    # logic in validate_1h_schema (SPREAD_COL_MISSING_WARNING, not an error).
    df = pd.DataFrame(columns=COLS)
    df.index = pd.DatetimeIndex([], tz="UTC", name="datetime")
    return df


def _month_start(year: int, month: int) -> datetime:
    """First instant of (year, month) in UTC; month is 1-based, rolls over Dec→Jan."""
    if month == 12:
        return datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(year, month + 1, 1, tzinfo=timezone.utc)


def _is_partial_month(year: int, month: int, end_dt: datetime) -> bool:
    """True if the window ends before this month is fully covered."""
    return _month_start(year, month) > end_dt


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("backfill")


def month_windows(start_year: int, end_dt: datetime):
    """Yield (year, month, window_start, window_end), last window capped at end_dt."""
    y, m = start_year, 1
    while datetime(y, m, 1, tzinfo=timezone.utc) < end_dt:
        ws = datetime(y, m, 1, tzinfo=timezone.utc)
        we = min(_month_start(y, m), end_dt)
        yield y, m, ws, we
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp, engine="pyarrow")
    tmp.replace(path)  # atomic on POSIX


def _write_manifest(chunk_dir: Path, pair: str, counts: dict[str, int],
                    suspects: list[tuple[str, int, str]]) -> None:
    """Write a per-pair gap-detection manifest. Per-pair file (not a shared
    JSONL) so concurrent workers never race on the same path."""
    data = {
        "pair": pair,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_bars": sum(counts.values()),
        "month_bar_counts": {ym: n for ym, n in sorted(counts.items())},
        "suspect_months": [{"month": ym, "bars": n, "flag": f} for ym, n, f in suspects],
    }
    mf = chunk_dir / f"{pair}_manifest.json"
    tmp = mf.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(mf)


def pull_pair(pair: str, start_year: int, end_dt: datetime,
              chunk_dir: Path, out_dir: Path, timeout: float, request_delay: float
              ) -> tuple[str, int, list[str], list[tuple[str, int, str]]]:
    instrument = ing.DUKASCOPY_INSTRUMENTS[pair]
    month_chunks: list[tuple[str, Path]] = []

    for y, m, ws, we in month_windows(start_year, end_dt):
        ym = f"{y}-{m:02d}"
        cf = chunk_dir / f"{pair}_{ym}.parquet"
        if not cf.exists():
            # 5 retries w/ exponential backoff + fail-fast timeout reach the
            # working per-hour retry (the _fetch_bi5 None-on-failure contract).
            df = ing.fetch_1h_bars(instrument, ws, we, retry_attempts=5, retry_delay=2.0,
                                   timeout=timeout, request_delay=request_delay)
            if df is None or df.empty:
                df = _empty_1h_frame()
            _atomic_write_parquet(df, cf)
            log.info("%s %s: %d bars", pair, ym, len(df))
        month_chunks.append((ym, cf))

    # Read each chunk once: build the concat frames and per-month counts.
    counts: dict[str, int] = {}
    frames: list[pd.DataFrame] = []
    full_months: list[str] = []   # non-partial months, for the adaptive floor
    for ym, cf in month_chunks:
        y, m = int(ym[:4]), int(ym[5:])
        cdf = pd.read_parquet(cf)
        counts[ym] = len(cdf)
        if not cdf.empty:
            frames.append(cdf)
        if not _is_partial_month(y, m, end_dt):
            full_months.append(ym)

    # Adaptive relative floor: a static SUSPECT_FLOOR=100 lets a ~150-bar month
    # (a third of a real ~480-bar month) slip through as "fine". Flag any
    # full month below HALF the median full-month count too — that catches
    # silently-incomplete months the static floor misses.
    full_counts = [counts[ym] for ym in full_months if counts[ym] > 0]
    median_full = sorted(full_counts)[len(full_counts) // 2] if full_counts else 0
    relative_floor = max(SUSPECT_FLOOR, int(0.5 * median_full))

    suspects: list[tuple[str, int, str]] = []
    for ym in full_months:
        n = counts[ym]
        if n == 0:
            suspects.append((ym, n, "ZERO"))            # pre-listing OR total outage — eyeball
        elif n < SUSPECT_FLOOR:
            suspects.append((ym, n, "LOW"))             # partial pull — almost certainly a gap
        elif n < relative_floor:
            suspects.append((ym, n, "THIN"))            # below 50% of median full month — incomplete

    full = pd.concat(frames) if frames else _empty_1h_frame()
    if not full.empty:
        full = full[~full.index.duplicated(keep="first")].sort_index()
    issues = ing.validate_1h_schema(full, pair) if not full.empty else ["EMPTY"]

    out = out_dir / f"{pair}_1h.parquet"
    _atomic_write_parquet(full, out)
    _write_manifest(chunk_dir, pair, counts, suspects)

    if suspects:
        log.error("%s: %d SUSPECT months (review before trusting); see manifest", pair, len(suspects))
    log.info("%s: FINAL %d bars -> %s (issues=%s)", pair, len(full), out.name, issues)
    return pair, len(full), issues, suspects


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start-year", type=int, default=2010)
    ap.add_argument("--end", default="2026-05-01", help="UTC end date, exclusive (YYYY-MM-DD)")
    ap.add_argument("--pairs", default=",".join(PAIRS), help="Comma-separated pair list")
    ap.add_argument("--workers", type=int, default=2,
                    help="Concurrent pairs (kept low to fly under Dukascopy throttling, "
                         "which tarpits sustained concurrent pulls)")
    ap.add_argument("--timeout", type=float, default=8.0,
                    help="Per-request socket timeout (s); low = fail fast under a throttle")
    ap.add_argument("--request-delay", type=float, default=0.25,
                    help="Seconds to sleep after each hourly request (paces the source)")
    a = ap.parse_args()

    end_dt = datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc)
    pairs = [p.strip().upper() for p in a.pairs.split(",") if p.strip()]
    unknown = [p for p in pairs if p not in ing.DUKASCOPY_INSTRUMENTS]
    if unknown:
        log.error("Unknown pairs: %s", unknown)
        return 1

    chunk_dir = ROOT / "data" / "processed" / "_chunks"
    out_dir = ROOT / "data" / "processed"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("Backfill %s  %d -> %s  workers=%d timeout=%.1fs delay=%.2fs (monthly checkpoints)",
             pairs, a.start_year, a.end, a.workers, a.timeout, a.request_delay)
    results: dict[str, tuple[int, list[str], list[tuple[str, int, str]]]] = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(pull_pair, p, a.start_year, end_dt, chunk_dir, out_dir,
                          a.timeout, a.request_delay): p for p in pairs}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                pair, n, issues, suspects = fut.result()
                results[pair] = (n, issues, suspects)
            except Exception as e:  # noqa: BLE001 — one pair failing must not abort the rest
                log.error("%s: FAILED %s", p, e)
                results[p] = (-1, [str(e)], [])

    log.info("=== BACKFILL SUMMARY ===")
    any_suspect = False
    for p in pairs:
        n, issues, suspects = results.get(p, (None, None, []))
        flag = f"  ⚠ {len(suspects)} suspect-months" if suspects else ""
        if suspects:
            any_suspect = True
        log.info("  %-7s %s bars  issues=%s%s", p, n, issues, flag)
    if any_suspect:
        log.error("REVIEW REQUIRED: suspect months are likely data gaps — inspect "
                  "data/processed/_chunks/{PAIR}_manifest.json, delete the bad chunk(s), re-run to refetch.")
    failed = [p for p, (n, _, _) in results.items() if n is not None and n < 0]
    return 1 if (failed or any_suspect) else 0


if __name__ == "__main__":
    sys.exit(main())
