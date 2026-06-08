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
COLS = ["open", "high", "low", "close", "volume"]

# A FULL (non-partial) calendar year of FX 1h bars is ~5,000-8,700. A non-partial
# year with 0 < bars < this floor is almost certainly a partial pull (a transient
# failure mid-year), not real data — flag it for review rather than trust it.
SUSPECT_FLOOR = 1000


def _empty_1h_frame() -> pd.DataFrame:
    df = pd.DataFrame(columns=COLS)
    df.index = pd.DatetimeIndex([], tz="UTC", name="datetime")
    return df


def _is_partial_year(year: int, end_dt: datetime) -> bool:
    """True if the window ends before this year is fully covered (the last year)."""
    return datetime(year + 1, 1, 1, tzinfo=timezone.utc) > end_dt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("backfill")


def year_windows(start_year: int, end_dt: datetime):
    """Yield (year, window_start, window_end) tuples, last window capped at end_dt."""
    y = start_year
    while datetime(y, 1, 1, tzinfo=timezone.utc) < end_dt:
        ws = datetime(y, 1, 1, tzinfo=timezone.utc)
        we = min(datetime(y + 1, 1, 1, tzinfo=timezone.utc), end_dt)
        yield y, ws, we
        y += 1


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp, engine="pyarrow")
    tmp.replace(path)  # atomic on POSIX


def _write_manifest(chunk_dir: Path, pair: str, counts: dict[int, int],
                    suspects: list[tuple[int, int, str]]) -> None:
    """Write a per-pair gap-detection manifest. Per-pair file (not a shared
    JSONL) so concurrent workers never race on the same path."""
    data = {
        "pair": pair,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_bars": sum(counts.values()),
        "year_bar_counts": {str(y): n for y, n in sorted(counts.items())},
        "suspect_years": [{"year": y, "bars": n, "flag": f} for y, n, f in suspects],
    }
    mf = chunk_dir / f"{pair}_manifest.json"
    tmp = mf.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(mf)


def pull_pair(pair: str, start_year: int, end_dt: datetime,
              chunk_dir: Path, out_dir: Path
              ) -> tuple[str, int, list[str], list[tuple[int, int, str]]]:
    instrument = ing.DUKASCOPY_INSTRUMENTS[pair]
    year_chunks: list[tuple[int, Path]] = []

    for y, ws, we in year_windows(start_year, end_dt):
        cf = chunk_dir / f"{pair}_{y}.parquet"
        if not cf.exists():
            # retry_attempts/delay reach the now-working per-hour retry (the
            # _fetch_bi5 None-on-failure contract; see ingest module).
            df = ing.fetch_1h_bars(instrument, ws, we, retry_attempts=5, retry_delay=2.0)
            if df is None or df.empty:
                df = _empty_1h_frame()
            _atomic_write_parquet(df, cf)
            log.info("%s %d: %d bars", pair, y, len(df))
        year_chunks.append((y, cf))

    # Read each chunk once: build the concat frames, per-year counts, and suspects.
    counts: dict[int, int] = {}
    suspects: list[tuple[int, int, str]] = []
    frames: list[pd.DataFrame] = []
    for y, cf in year_chunks:
        cdf = pd.read_parquet(cf)
        counts[y] = len(cdf)
        if not cdf.empty:
            frames.append(cdf)
        if not _is_partial_year(y, end_dt):
            if 0 < len(cdf) < SUSPECT_FLOOR:
                suspects.append((y, len(cdf), "LOW"))    # partial pull — almost certainly a gap
            elif len(cdf) == 0:
                suspects.append((y, len(cdf), "ZERO"))   # pre-listing OR total outage — eyeball

    full = pd.concat(frames) if frames else _empty_1h_frame()
    if not full.empty:
        full = full[~full.index.duplicated(keep="first")].sort_index()
    issues = ing.validate_1h_schema(full, pair) if not full.empty else ["EMPTY"]

    out = out_dir / f"{pair}_1h.parquet"
    _atomic_write_parquet(full, out)
    _write_manifest(chunk_dir, pair, counts, suspects)

    if suspects:
        log.error("%s: SUSPECT years (review before trusting): %s", pair, suspects)
    log.info("%s: FINAL %d bars -> %s (issues=%s)", pair, len(full), out.name, issues)
    return pair, len(full), issues, suspects


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start-year", type=int, default=2010)
    ap.add_argument("--end", default="2026-05-01", help="UTC end date, exclusive (YYYY-MM-DD)")
    ap.add_argument("--pairs", default=",".join(PAIRS), help="Comma-separated pair list")
    ap.add_argument("--workers", type=int, default=4,
                    help="Concurrent pairs (kept low to avoid Dukascopy rate-limiting; "
                         "rate-limits now retry rather than corrupt, but fewer workers "
                         "avoid triggering them)")
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

    log.info("Backfill %s  %d -> %s  workers=%d", pairs, a.start_year, a.end, a.workers)
    results: dict[str, tuple[int, list[str], list[tuple[int, int, str]]]] = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(pull_pair, p, a.start_year, end_dt, chunk_dir, out_dir): p for p in pairs}
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
        flag = ""
        if suspects:
            any_suspect = True
            flag = f"  ⚠ SUSPECT={suspects}"
        log.info("  %-7s %s bars  issues=%s%s", p, n, issues, flag)
    if any_suspect:
        log.error("REVIEW REQUIRED: suspect years above are likely data gaps — inspect "
                  "data/processed/_chunks/{PAIR}_manifest.json, delete the bad chunk, re-run to refetch.")
    failed = [p for p, (n, _, _) in results.items() if n is not None and n < 0]
    return 1 if (failed or any_suspect) else 0


if __name__ == "__main__":
    sys.exit(main())
