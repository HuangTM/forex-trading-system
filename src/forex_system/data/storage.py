"""Parquet storage for validated OHLCV data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from forex_system.core.errors import DataError, LookaheadError

_OOS_BURNS_LOG = Path(".fintech-org/oos-burns.jsonl")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-pair close-price sanity bounds (daily timeframe, standard pip convention).
#
# RATIONALE: The corrupted processed_synthetic_phase0/ series contains USDJPY
# in 5.03–7.75 range, GBPJPY in 1.54–2.28 range, and CADJPY in 77.47–203.64
# range — the first two are orders of magnitude below reality, the third is a
# corrupted upper-tail that extends well above the real historical maximum of
# 118.74.  A load-time assert catches silent ingestion of those files if
# data_dir is ever pointed at the wrong directory.
#
# HOW BOUNDS WERE SET:
#   lower = 20 (generous floor; well below any plausible JPY-cross post-1990)
#   upper = ceil(observed_real_max * 1.5)  — approximately 1.3–1.5× headroom
#
# Observed real maxima (data/processed/ daily series as of 2026-06-03):
#   USDJPY 161.71, EURJPY 186.24, GBPJPY 215.60,
#   AUDJPY 113.69, CADJPY 118.74, NZDJPY 98.82
#
# Tightening to ~1.5× catches the CADJPY corruption (synthetic max 203.64)
# while leaving comfortable room for historically novel (but plausible) moves.
#
# IMPORTANT LIMITATION: This sanity gate cannot catch corruption that falls
# WITHIN the headroom band (i.e., corrupted values between the real max and
# the upper bound).  The PRIMARY DEFENSE against wrong-directory ingestion is
# load_parquet()'s hardcoded join on ".../processed/..." — this range-assert
# is DEFENCE-IN-DEPTH only.  Do not rely on it exclusively.
#
# Pairs NOT listed here are not range-checked (unknown convention, e.g. scaled
# 4h data).  The guard is fail-closed on listed pairs, pass-through on unlisted.
# ---------------------------------------------------------------------------
_PAIR_CLOSE_BOUNDS: dict[str, tuple[float, float]] = {
    # JPY pairs quoted as JPY per foreign unit.
    # Upper bounds set to ceil(real_max * 1.5) to catch the known corrupted
    # synthetic CADJPY series (real max 118.74; synthetic max 203.64 > 180).
    # Lower bound of 20 catches the synthetic USDJPY (5–8) and GBPJPY (1.5–2.3).
    "USDJPY": (20.0, 245.0),   # real max 161.71 → 1.5× ≈ 242.6 → 245
    "GBPJPY": (20.0, 325.0),   # real max 215.60 → 1.5× ≈ 323.4 → 325
    "EURJPY": (20.0, 280.0),   # real max 186.24 → 1.5× ≈ 279.4 → 280
    "AUDJPY": (20.0, 175.0),   # real max 113.69 → 1.5× ≈ 170.5 → 175
    "CADJPY": (20.0, 180.0),   # real max 118.74 → 1.5× ≈ 178.1 → 180 (catches synth 203.64)
    "NZDJPY": (20.0, 150.0),   # real max  98.82 → 1.5× ≈ 148.2 → 150
    # EURUSD and GBPUSD use standard ~0.80–2.00 pip convention in this codebase.
    "EURUSD": (0.50, 3.00),
    "GBPUSD": (0.50, 4.00),
    # NZDUSD uses standard scale ~0.40–0.90.
    "NZDUSD": (0.20, 2.00),
    # NOTE: AUDUSD, USDCAD, EURGBP in this codebase are stored with a
    # non-standard price scale (observed: AUDUSD ~9–14, USDCAD ~2.6–5.0,
    # EURGBP ~7.4).  Bounds are omitted for these pairs to avoid false
    # positives — they are NOT in the JPY pair group and their synthetic
    # counterparts are not the identified contamination risk for R5.
}

# Pairs where we skip range checking (non-standard scale in stored 4h files)
_PAIR_TIMEFRAME_SKIP: frozenset[tuple[str, str]] = frozenset(
    {
        ("USDJPY", "4h"),
        ("GBPUSD", "4h"),
        ("EURUSD", "4h"),
    }
)


def _assert_price_range(df: pd.DataFrame, pair: str, timeframe: str, path: Path) -> None:
    """Raise DataError if the close series is malformed or outside plausible bounds.

    Two layers:
      1. Basic validity (ALL pairs, incl. range-skipped/unlisted): a missing
         'close' column, an empty series, or any non-finite value (NaN/±inf)
         fails closed. This runs BEFORE bound comparison so all-NaN cannot pass
         the gate open.
      2. Range plausibility (only pairs in _PAIR_CLOSE_BOUNDS, not in the skip
         set): close min/max must lie within the per-pair economic bounds.

    Decision trace: logs one structured entry per load naming the resolved path,
    observed range, and bound source — so a reader can reconstruct the check from
    logs alone without attaching a debugger.
    """
    pair_upper = pair.upper()

    # --- Basic validity (PR FINDING-1 + FINDING-5): applies to EVERY loaded
    # series, including range-skipped (4h) and unlisted pairs. A malformed frame
    # (no close column), an empty series, or ANY non-finite value (NaN / ±inf)
    # is the canonical corruption mode and MUST fail closed BEFORE any bound
    # comparison — `NaN < lo` and `NaN > hi` both evaluate False, so an all-NaN
    # series would otherwise pass the gate OPEN.
    if "close" not in df.columns:
        raise DataError(
            f"Malformed OHLCV frame for {pair_upper} ({timeframe}) loaded from "
            f"{path}: no 'close' column — cannot validate price range."
        )

    close = df["close"]
    n = len(close)
    n_non_finite = int((~np.isfinite(pd.to_numeric(close, errors="coerce"))).sum())
    if n == 0 or n_non_finite > 0:
        logger.warning(
            json.dumps(
                {
                    "event": "data.range_check.FAIL",
                    "pair": pair_upper,
                    "timeframe": timeframe,
                    "path": str(path),
                    "reason": "empty-or-non-finite-close",
                    "n_rows": n,
                    "n_non_finite": n_non_finite,
                }
            )
        )
        raise DataError(
            f"Price sanity check FAILED for {pair_upper} ({timeframe}) loaded from "
            f"{path}: close series is empty (n={n}) or contains {n_non_finite} "
            f"non-finite value(s) (NaN/±inf). Indicates corrupted or malformed data. "
            f"Fix the source file or data_dir."
        )

    # --- Range plausibility: only for pairs with a known price convention.
    if (pair_upper, timeframe) in _PAIR_TIMEFRAME_SKIP:
        # FINDING-4: 4h JPY files are stored at an anomalous scale, so they are
        # NOT range-checked — a corrupted-but-finite 4h file at the wrong scale
        # would slip through here. R5 is daily-only so this is out of its path,
        # but log at WARNING so the unguarded skip is visible, not silent.
        logger.warning(
            json.dumps(
                {
                    "event": "data.range_check.skipped",
                    "pair": pair_upper,
                    "timeframe": timeframe,
                    "path": str(path),
                    "reason": "pair/timeframe in skip-list (anomalous 4h scale); range UNGUARDED",
                }
            )
        )
        return

    if pair_upper not in _PAIR_CLOSE_BOUNDS:
        logger.info(
            json.dumps(
                {
                    "event": "data.range_check.skipped",
                    "pair": pair_upper,
                    "timeframe": timeframe,
                    "path": str(path),
                    "reason": "pair not in bounds registry; check skipped",
                }
            )
        )
        return

    lo, hi = _PAIR_CLOSE_BOUNDS[pair_upper]
    observed_min = float(close.min())
    observed_max = float(close.max())
    failed = observed_min < lo or observed_max > hi  # single predicate, reused in log + raise (FINDING-8)

    logger.info(
        json.dumps(
            {
                "event": "data.range_check.FAIL" if failed else "data.range_check.ok",
                "pair": pair_upper,
                "timeframe": timeframe,
                "path": str(path),
                "observed_min": observed_min,
                "observed_max": observed_max,
                "bound_lo": lo,
                "bound_hi": hi,
                "bound_source": "_PAIR_CLOSE_BOUNDS in data/storage.py",
            }
        )
    )

    if failed:
        raise DataError(
            f"Price range sanity check FAILED for {pair_upper} ({timeframe}) "
            f"loaded from {path}. "
            f"Observed close range [{observed_min:.4f}, {observed_max:.4f}] is outside "
            f"economically plausible bounds [{lo}, {hi}]. "
            f"This likely indicates a wrong data_dir (e.g. processed_synthetic_phase0/ "
            f"instead of processed/) or a corrupted file copied into processed/. "
            f"Fix data_dir in your config or pre-reg sidecar."
        )


def save_parquet(df: pd.DataFrame, pair: str, timeframe: str, data_dir: str | Path) -> Path:
    """Save validated OHLCV data to Parquet."""
    data_dir = Path(data_dir) / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)

    path = data_dir / f"{pair.upper()}_{timeframe}.parquet"
    df.to_parquet(path, engine="pyarrow")
    return path


def load_parquet(
    pair: str,
    timeframe: str,
    data_dir: str | Path,
    holdout_after: str | None = None,
    oos_mode: bool = False,
) -> pd.DataFrame:
    """Load OHLCV data from Parquet store.

    Args:
        pair: Currency pair symbol (e.g. "USDJPY").
        timeframe: Data timeframe (e.g. "daily", "4h").
        data_dir: Base data directory.
        holdout_after: ISO date string (e.g. "2024-01-01"). If set, data on or
            after this date is the OOS holdout. Access is allowed only when
            oos_mode=True (a one-shot final test mode). Raises LookaheadError
            if any caller tries to read holdout data without oos_mode=True.
        oos_mode: If True, access to holdout data is permitted. The first access
            is recorded in .fintech-org/oos-burns.jsonl. Once a holdout is burned
            for a pair/timeframe, callers should not re-access it in the same
            analysis session.

    Returns:
        DataFrame. In non-oos_mode, returns only pre-holdout rows.
        In oos_mode, returns full data and records the burn.

    Raises:
        DataError: if the parquet file is not found.
        DataError: if the close price range fails the per-pair sanity check.
        LookaheadError: if holdout data is requested without oos_mode.
    """
    path = Path(data_dir) / "processed" / f"{pair.upper()}_{timeframe}.parquet"

    # Decision trace: log the fully resolved path so a reader can confirm which
    # directory was used without attaching a debugger (log-as-decision-trace §1-3).
    logger.info(
        json.dumps(
            {
                "event": "data.load.start",
                "pair": pair.upper(),
                "timeframe": timeframe,
                "resolved_path": str(path.resolve()),
                "data_dir": str(data_dir),
            }
        )
    )

    if not path.exists():
        raise DataError(f"No data found: {path}")

    df = pd.read_parquet(path)

    # Sanity-check price ranges before returning — fail-closed on bad data.
    _assert_price_range(df, pair=pair, timeframe=timeframe, path=path)

    if holdout_after is None:
        return df

    # Parse holdout boundary
    holdout_ts = pd.Timestamp(holdout_after)

    # Check if any data falls on or after the holdout date
    if df.index.tz is not None:
        holdout_ts = holdout_ts.tz_localize(df.index.tz)
    has_holdout_data = (df.index >= holdout_ts).any()

    if not has_holdout_data:
        # All data is pre-holdout; no issue
        return df

    if not oos_mode:
        # Block access to holdout data — caller must use oos_mode=True
        raise LookaheadError(
            f"Data for {pair} {timeframe} contains dates on or after holdout_after={holdout_after!r}. "
            f"Access to the OOS holdout is blocked in standard mode. "
            f"Use oos_mode=True (harness --final-oos-test) to access holdout data. "
            f"Holdout access is a one-shot burn recorded in {_OOS_BURNS_LOG}."
        )

    # OOS mode: allowed, but record the burn
    _record_oos_burn(pair=pair, timeframe=timeframe, holdout_after=holdout_after)
    return df


def _record_oos_burn(pair: str, timeframe: str, holdout_after: str) -> None:
    """Write an oos-burn entry to .fintech-org/oos-burns.jsonl."""
    _OOS_BURNS_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "event": "oos.burn",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pair": pair.upper(),
        "timeframe": timeframe,
        "holdout_after": holdout_after,
    }
    with open(_OOS_BURNS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def list_available(data_dir: str | Path) -> list[dict[str, str]]:
    """List all available pair/timeframe combinations in the store."""
    processed = Path(data_dir) / "processed"
    if not processed.exists():
        return []

    available = []
    for f in sorted(processed.glob("*.parquet")):
        parts = f.stem.split("_", 1)
        if len(parts) == 2:
            available.append({"pair": parts[0], "timeframe": parts[1]})
    return available
