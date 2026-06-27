"""
Volume-conditioned cost-feasibility screen: V1 (relvol-continuation) + V2 (relvol-high ^ spread-low mean-reversion).
Subtask: volume-conditioned-2026-06-24-qd

JOB 1: Fix OPEN-ITEM-C2COST — extend trade-loop hold_cost slice to include exit-change bar;
        verify with a NEW, DISTINCT assertion (full RT = entry + exit, not 1 leg).
JOB 2: Run cost-feasibility + volatility-control screen on V1 and V2 per QR design.

Firewall: IMPLEMENTATION ONLY. No research judgments. No trial increment. Descriptive screen.
"""

from __future__ import annotations

import sys
import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path("/Users/huangtm/Projects/forex-trading-system")
sys.path.insert(0, str(REPO / "src"))

DATA_DIR = REPO / "data" / "processed"
SESSION_DIR = REPO / ".fintech-org" / "artifacts" / "2026-06-24-volume-conditioned-screen"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# ── Cost constants ────────────────────────────────────────────────────────────
SLIP_PIPS = 0.25
HAIRCUT_PIPS = 0.15
RT_OVERHEAD = 2.0 * (SLIP_PIPS + HAIRCUT_PIPS)  # 0.80 pips

# ── Pip size per pair (JPY=0.01, all others 0.0001) ─────────────────────────
PIP_SIZE: dict[str, float] = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "USDJPY": 0.01,
    "AUDJPY": 0.01,
    "EURJPY": 0.01,
    "AUDUSD": 0.0001,
    "USDCAD": 0.0001,
    "NZDUSD": 0.0001,
    "EURGBP": 0.0001,
}

# V1 pair universe (5 lowest-spread / highest-liquidity, GBPJPY excluded per HoQR R3)
V1_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY", "AUDUSD"]
# V2 pair universe (3 pairs where spread-low gate is meaningful)
V2_PAIRS = ["EURUSD", "USDJPY", "EURGBP"]

# V1 cost hurdles: spread_median_pips (conditioned-bar) + 0.80 computed at runtime.
# Pre-spec reference hurdles (full-sample) per QR design:
V1_HURDLE_REF = {"EURUSD": 1.10, "GBPUSD": 1.70, "USDJPY": 1.40, "EURJPY": 1.80, "AUDUSD": 1.80}
V2_HURDLE_REF = {"EURUSD": 1.00, "USDJPY": 1.20, "EURGBP": 1.50}

# V1/V2 relvol threshold (pre-specified, not optimized)
RELVOL_THRESHOLD = 1.5
# V1 session-open hours (strict primary definition per QR)
V1_SESSION_HOURS_UTC = {7, 13}
# V1 hold horizon (bars after entry signal bar)
V1_HOLD_BARS = 2  # exit at close of bar t+2 (enter at t+1)
# V2 hold horizon
V2_HOLD_BARS = 3  # exit at close of bar t+3
# V2 spread percentile gate
V2_SPREAD_PCTILE = 40
# V2 extension threshold: must be >= 0.75 x seasonal-median-range from session open
V2_EXTENSION_MULT = 0.75
# Number of seasonal buckets: 7 days × 24 hours
N_SEASONAL_BUCKETS = 168


# =============================================================================
# JOB 1 — C2COST FIX + NEW DISTINCT ASSERTION
# =============================================================================
# Bug: scripts/cost_feasibility_c1_c2.py line 575:
#   hold_cost = float(cost_series.iloc[entry_i:exit_i + 1].sum())
#
# The position series (from compute_rt_cost_series) transitions as:
#   pos: [... 0, +1, +1, ..., +1, 0, ...]
#              ^entry_i         ^exit_i  ^j=exit_i+1
# pos.diff().abs() registers:
#   entry-leg cost at bar entry_i (0→+1, diff=1)
#   exit-leg cost at bar j=exit_i+1 (+1→0, diff=1)
#
# The slice [entry_i : exit_i+1] = [entry_i : j] covers [entry_i, exit_i] INCLUSIVE,
# stopping at index exit_i (the last bar with pos==direction).
# Bar j = exit_i+1 (where pos returns to 0) is OUTSIDE the slice → exit cost DROPPED.
#
# FIX: extend slice by 1 to [entry_i : exit_i+2] = [entry_i : j+1].
# The variable j is already computed in run_c2_pair's while-loop as the first index
# where pos differs from direction; exit_i = j - 1, so exit_i + 2 = j + 1.
#
# In the volume screen we implement the fix from scratch.
# For JOB 1 we ALSO fix it in cost_feasibility_c1_c2.py and run the new assertion.


def compute_rt_cost_series(
    pos: pd.Series,
    spread_pips: pd.Series,
    exclude_mask: pd.Series,
) -> pd.Series:
    """
    Return per-bar RT cost in pips (F-001 corrected: flips cost 2x).
    Bars in exclude_mask are zeroed (not charged).
    """
    changes = pos.diff().abs().fillna(0.0)
    spread_cost = spread_pips.where(~exclude_mask, other=0.0)
    rt_cost_per_rt = spread_cost + RT_OVERHEAD
    return changes * rt_cost_per_rt


# ─── NEW DISTINCT ASSERTION (C2COST / OPEN-ITEM) ────────────────────────────
def run_c2cost_assertion() -> dict:
    """
    NEW assertion proving that the CORRECTED slice charges BOTH entry and exit legs.

    Synthetic trade:
      bar 0: pos=0 (flat)
      bar 1: pos=+1  ← entry (flat→+1), cost registers here
      bar 2: pos=+1  ← hold
      bar 3: pos=+1  ← hold
      bar 4: pos=0   ← exit (+1→flat), cost registers HERE (bar 4 = exit_i+1)

    entry_i = 1, exit_i = 3, j = 4
    Buggy slice: [1 : 3+1] = [1:4] → covers bars 1,2,3 → MISSES bar 4 → UNDER-CHARGES
    Fixed slice: [1 : 3+2] = [1:5] → covers bars 1,2,3,4 → CAPTURES BOTH legs ← CORRECT

    Synthetic spread = 0.30 pips (EURUSD-like), constant.
    Expected per-change cost:
      rt_cost_per_bar = spread + RT_OVERHEAD = 0.30 + 0.80 = 1.10 pips
      entry-leg at bar 1: diff=1, cost = 1.10
      bars 2-3: diff=0, cost = 0
      exit-leg at bar 4: diff=1, cost = 1.10
      Full RT cost = 2.20 pips (entry + exit)
    Buggy cost = 1.10 pips (entry only, exit dropped)
    """
    SPREAD = 0.30  # EURUSD-like, constant
    RT_PER_LEG = SPREAD + RT_OVERHEAD  # 1.10 pips

    pos = pd.Series([0.0, 1.0, 1.0, 1.0, 0.0])
    spread_pips = pd.Series([SPREAD] * 5)
    exclude_mask = pd.Series([False] * 5)

    cost_series = compute_rt_cost_series(pos, spread_pips, exclude_mask)
    # cost_series values: [0, 1.10, 0, 0, 1.10]

    entry_i = 1
    exit_i = 3   # last bar where pos==+1
    j = 4        # first bar where pos==0 (exit_i + 1)

    # BUGGY slice (old code): [entry_i : exit_i+1] = [1:4] → misses bar 4
    buggy_cost = float(cost_series.iloc[entry_i: exit_i + 1].sum())   # covers bars 1,2,3

    # FIXED slice: [entry_i : exit_i+2] = [1:5] → covers bars 1,2,3,4
    fixed_cost = float(cost_series.iloc[entry_i: exit_i + 2].sum())   # covers bars 1,2,3,4

    expected_full_rt = 2.0 * RT_PER_LEG   # 2.20 pips (entry + exit)
    expected_buggy   = 1.0 * RT_PER_LEG   # 1.10 pips (entry only)

    assert abs(buggy_cost - expected_buggy) < 1e-9, (
        f"Buggy slice expected {expected_buggy:.4f}, got {buggy_cost:.4f}"
    )
    assert abs(fixed_cost - expected_full_rt) < 1e-9, (
        f"Fixed slice expected {expected_full_rt:.4f}, got {fixed_cost:.4f}"
    )
    undercount = expected_full_rt - buggy_cost
    assert abs(undercount - RT_PER_LEG) < 1e-9, (
        f"Undercount should equal exactly 1 exit leg ({RT_PER_LEG:.4f}), got {undercount:.4f}"
    )

    return {
        "assertion_name": "C2COST_FULL_RT_ENTRY_PLUS_EXIT",
        "description": "Synthetic single trade flat→+1 at bar 1, hold bars 2-3, +1→flat at bar 4",
        "spread_pips": SPREAD,
        "rt_overhead_pips": RT_OVERHEAD,
        "rt_per_leg_pips": RT_PER_LEG,
        "position_path": list(pos),
        "cost_series": list(cost_series.round(6)),
        "entry_i": entry_i,
        "exit_i": exit_i,
        "j_exit_change_bar": j,
        "buggy_slice": f"iloc[{entry_i}:{exit_i+1}]  ← covers bars {list(range(entry_i, exit_i+1))}",
        "fixed_slice":  f"iloc[{entry_i}:{exit_i+2}]  ← covers bars {list(range(entry_i, exit_i+2))}",
        "buggy_cost_pips": round(buggy_cost, 6),
        "fixed_cost_pips": round(fixed_cost, 6),
        "expected_full_rt_pips": round(expected_full_rt, 6),
        "expected_buggy_pips": round(expected_buggy, 6),
        "undercount_per_trade_pips": round(undercount, 6),
        "assertion_passed": True,
        "interpretation": (
            f"Buggy slice charges {buggy_cost:.4f} pips (entry leg only). "
            f"Fixed slice charges {fixed_cost:.4f} pips (entry + exit = full RT). "
            f"Every trade was under-charged by exactly {undercount:.4f} pips "
            f"(= 1 exit leg × (spread {SPREAD} + overhead {RT_OVERHEAD}) pips)."
        ),
    }


# =============================================================================
# SEASONAL NORM
# =============================================================================

def compute_seasonal_norm(df: pd.DataFrame) -> pd.Series:
    """
    Full-sample median volume per (day_of_week × 24 + hour_utc) bucket.
    Returns a Series aligned to df.index.
    NOTE: uses full-sample median (acceptable for descriptive feasibility screen;
    would need rolling/expanding norm for any committed CPCV backtest).
    """
    bucket = df.index.dayofweek * 24 + df.index.hour  # 0..167
    seasonal_med = df.groupby(bucket)["volume"].transform("median")
    return seasonal_med.clip(lower=1.0)  # avoid divide-by-zero


def compute_relvol(df: pd.DataFrame) -> pd.Series:
    """relative volume = volume / seasonal_median per bucket."""
    seasonal_med = compute_seasonal_norm(df)
    return df["volume"] / seasonal_med


def compute_relrng(df: pd.DataFrame) -> pd.Series:
    """relative range = bar_range / full-sample median bar_range."""
    rng = df["high"] - df["low"]
    return rng / rng.median()


# =============================================================================
# VOLUME/RANGE CORRELATION DIAGNOSTICS
# =============================================================================

def compute_vol_range_corr(df: pd.DataFrame, pair: str) -> dict:
    """
    Compute raw-volume~range and relvol~relrange correlations per pair.
    Returns Spearman (rank) correlation for robustness to outliers.
    """
    rng = (df["high"] - df["low"]) / PIP_SIZE[pair]
    raw_vol = df["volume"]
    relvol = compute_relvol(df)
    relrng = compute_relrng(df)

    r_raw, _ = stats.spearmanr(raw_vol, rng)
    r_rel, _ = stats.spearmanr(relvol, relrng)

    log_relvol = np.log1p(relvol)
    log_relrng = np.log1p(relrng)
    r2_log = np.corrcoef(log_relvol, log_relrng)[0, 1] ** 2

    return {
        "pair": pair,
        "raw_vol_range_spearman": round(r_raw, 4),
        "relvol_relrng_spearman": round(r_rel, 4),
        "log_relvol_log_relrng_R2": round(r2_log, 4),
    }


# =============================================================================
# VOLATILITY CONTROL TEST
# =============================================================================

def run_volatility_control(gross_pips: np.ndarray, relvol: np.ndarray, relrng: np.ndarray,
                            pair: str, candidate: str) -> dict:
    """
    Regress per-trade gross pips on relvol_rank and relrng_rank jointly.
    Report relvol coefficient and its t-stat net of relrng.
    PASS iff relvol t-stat >= 2.00 after controlling for relrng.
    """
    n = len(gross_pips)
    if n < 10:
        return {
            "pair": pair,
            "candidate": candidate,
            "n_trades": n,
            "relvol_coef": float("nan"),
            "relvol_tstat": float("nan"),
            "relrng_coef": float("nan"),
            "relrng_tstat": float("nan"),
            "r2": float("nan"),
            "pass_tstat_ge_2": False,
            "note": "insufficient trades for regression",
        }

    # Rank-transform: robust to distribution shape
    rv_rank = stats.rankdata(relvol).astype(float)
    rr_rank = stats.rankdata(relrng).astype(float)

    X = np.column_stack([np.ones(n), rv_rank, rr_rank])
    result = np.linalg.lstsq(X, gross_pips, rcond=None)
    coefs = result[0]
    fitted = X @ coefs
    resid = gross_pips - fitted
    ss_res = float((resid ** 2).sum())
    ss_tot = float(((gross_pips - gross_pips.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")

    # Standard errors via OLS formula: SE = sqrt(diag(s^2 (X'X)^-1))
    s2 = ss_res / max(n - 3, 1)
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(XtX_inv) * s2)
    except np.linalg.LinAlgError:
        se = np.array([float("nan")] * 3)

    t_relvol = float(coefs[1] / se[1]) if se[1] > 1e-12 else float("nan")
    t_relrng = float(coefs[2] / se[2]) if se[2] > 1e-12 else float("nan")

    return {
        "pair": pair,
        "candidate": candidate,
        "n_trades": n,
        "relvol_coef": round(float(coefs[1]), 6),
        "relvol_tstat": round(t_relvol, 4),
        "relrng_coef": round(float(coefs[2]), 6),
        "relrng_tstat": round(t_relrng, 4),
        "r2": round(r2, 4),
        "pass_tstat_ge_2": t_relvol >= 2.00,
        "note": f"relvol t={t_relvol:.2f} {'≥' if t_relvol >= 2.00 else '<'} 2.00 threshold",
    }


# =============================================================================
# V1: RELVOL-CONTINUATION SCREEN
# =============================================================================

def run_v1_pair(pair: str) -> dict:
    """
    V1: relative-volume participation-surprise continuation.

    Entry condition:
      - Bar t is at a session-open hour (07 or 13 UTC)
      - relvol_t >= 1.5 (volume >= 1.5x seasonal norm)
      - |close_t - open_t| > 0 (well-defined direction)

    Signal: direction = sign(close_t - open_t)
    Entry: open of bar t+1 (shift(1) no-lookahead)
    Exit: close of bar t+2 (2-bar hold from signal bar)
      → trade covers bars t+1 (entry) and t+2 (exit)
      → entry price = open of bar t+1
      → exit price = close of bar t+2

    Gross pips: pure price capture = direction × (exit_close - entry_open) / pip_size
    RT cost: entry_bar spread + exit_bar spread + RT_OVERHEAD (on CONDITIONED bars)
    EXCLUDE-NOT-IMPUTE: skip any trade where entry or exit spread is zero/missing.

    C2COST FIX applied: we directly use entry_bar spread + exit_bar spread
    (not the buggy hold_cost slice). This is architecturally clean for this
    event-trade setup: no persistent position series needed.
    """
    pip_size = PIP_SIZE[pair]
    df = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    relvol = compute_relvol(df)
    relrng = compute_relrng(df)

    # Signal bars: session-open hours where relvol >= threshold
    hour = df.index.hour
    is_session_open = pd.Series(
        [h in V1_SESSION_HOURS_UTC for h in hour], index=df.index
    )
    signal_mask = is_session_open & (relvol >= RELVOL_THRESHOLD)

    # For each signal bar t, we need entry at t+1 and exit at t+2
    # entry bar = t+1 open, exit bar = t+2 close
    signal_indices = np.where(signal_mask.values)[0]

    trades = []
    trade_relvol = []
    trade_relrng = []

    for t in signal_indices:
        entry_i = t + 1
        exit_i = t + 2

        if exit_i >= len(df):
            continue

        # Direction of signal bar
        bar_open = float(df["open"].iloc[t])
        bar_close = float(df["close"].iloc[t])
        bar_return = bar_close - bar_open
        if bar_return == 0.0:
            continue
        direction = 1.0 if bar_return > 0 else -1.0

        entry_open = float(df["open"].iloc[entry_i])
        exit_close = float(df["close"].iloc[exit_i])

        entry_spread = float(df["spread_median_pips"].iloc[entry_i])
        exit_spread = float(df["spread_median_pips"].iloc[exit_i])

        # EXCLUDE-NOT-IMPUTE
        if entry_spread <= 0 or np.isnan(entry_spread):
            continue
        if exit_spread <= 0 or np.isnan(exit_spread):
            continue

        # Gross pips: pure price (entry open → exit close), direction-signed
        price_move = direction * (exit_close - entry_open)
        gross_pips = price_move / pip_size

        # RT cost on CONDITIONED bars (entry + exit spread, NOT full-sample)
        rt_cost = entry_spread + exit_spread + RT_OVERHEAD

        trades.append({
            "signal_bar": df.index[t],
            "entry_bar": df.index[entry_i],
            "exit_bar": df.index[exit_i],
            "direction": direction,
            "relvol_t": round(float(relvol.iloc[t]), 4),
            "relrng_t": round(float(relrng.iloc[t]), 4),
            "gross_pips": round(gross_pips, 6),
            "entry_spread": entry_spread,
            "exit_spread": exit_spread,
            "rt_cost": round(rt_cost, 6),
            "net_pips": round(gross_pips - rt_cost, 6),
        })
        trade_relvol.append(float(relvol.iloc[t]))
        trade_relrng.append(float(relrng.iloc[t]))

    if not trades:
        return {"pair": pair, "candidate": "V1", "n_fires": 0, "error": "no qualifying trades"}

    tdf = pd.DataFrame(trades)
    n_fires = len(tdf)
    mean_gross = float(tdf["gross_pips"].mean())
    mean_rt_cost = float(tdf["rt_cost"].mean())
    margin = mean_gross - mean_rt_cost

    # Fires per year
    sample_years = (df.index[-1] - df.index[0]).days / 365.25
    fires_per_year = n_fires / sample_years

    # Cost verdict vs QR kill criterion:
    # FAIL iff gross <= 0.80 × RT_cost (i.e. margin < -0.20 × RT_cost)
    # STRETCH iff 0.80 × RT_cost < gross <= RT_cost (gross/RT in (0.80, 1.00])
    # PASS iff gross > RT_cost
    gross_rt_ratio = mean_gross / mean_rt_cost if mean_rt_cost > 0 else float("nan")
    if gross_rt_ratio <= 0.80:
        cost_verdict = "FAIL"
    elif gross_rt_ratio <= 1.00:
        cost_verdict = "STRETCH"
    else:
        cost_verdict = "PASS"

    # Volatility control
    vol_ctrl = run_volatility_control(
        gross_pips=tdf["gross_pips"].values,
        relvol=np.array(trade_relvol),
        relrng=np.array(trade_relrng),
        pair=pair,
        candidate="V1",
    )

    # 2x2 stratification (supplementary form b per QR design)
    rv_med = np.median(trade_relvol)
    rr_med = np.median(trade_relrng)
    strat = {}
    for rv_label, rv_high in [("high_relvol", True), ("low_relvol", False)]:
        for rr_label, rr_high in [("high_relrng", True), ("low_relrng", False)]:
            mask = np.array([
                (rv >= rv_med if rv_high else rv < rv_med) and
                (rr >= rr_med if rr_high else rr < rr_med)
                for rv, rr in zip(trade_relvol, trade_relrng)
            ])
            cell_gross = tdf["gross_pips"].values[mask]
            strat[f"{rv_label}_x_{rr_label}"] = {
                "n": int(mask.sum()),
                "mean_gross": round(float(cell_gross.mean()), 4) if mask.sum() > 0 else float("nan"),
            }

    return {
        "pair": pair,
        "candidate": "V1",
        "n_fires": n_fires,
        "fires_per_year": round(fires_per_year, 1),
        "sample_years": round(sample_years, 2),
        "mean_gross_pips": round(mean_gross, 4),
        "mean_rt_cost_pips": round(mean_rt_cost, 4),
        "gross_minus_cost_margin": round(margin, 4),
        "gross_rt_ratio": round(gross_rt_ratio, 4),
        "cost_verdict": cost_verdict,
        "volatility_control": vol_ctrl,
        "stratification_2x2": strat,
        "trades": trades,
    }


# =============================================================================
# V2: RELVOL-HIGH ^ SPREAD-LOW MEAN-REVERSION SCREEN
# =============================================================================

def compute_session_open_price(df: pd.DataFrame) -> pd.Series:
    """
    Session open = the open of the first bar of each calendar date (UTC).
    Each bar is assigned the session open of its calendar date.
    """
    # calendar date per bar
    dates = df.index.date
    # First bar of each date → use that bar's open as session open
    date_first_open = {}
    for idx_pos, (dt, row_open) in enumerate(zip(dates, df["open"])):
        if dt not in date_first_open:
            date_first_open[dt] = float(row_open)
    session_open = pd.Series(
        [date_first_open[d] for d in dates],
        index=df.index,
        dtype=float,
    )
    return session_open


def compute_seasonal_median_range(df: pd.DataFrame) -> pd.Series:
    """
    Full-sample median range per (day_of_week × 24 + hour_utc) seasonal bucket.
    Used for V2's extension threshold.
    """
    bar_range = df["high"] - df["low"]
    bucket = df.index.dayofweek * 24 + df.index.hour
    return bar_range.groupby(bucket).transform("median").clip(lower=1e-8)


def run_v2_pair(pair: str) -> dict:
    """
    V2: relvol-high AND spread-low mean-reversion.

    Entry condition (bar t):
      - relvol_t >= 1.5
      - spread_t <= pair's 40th-percentile spread
      - |close_t - session_open_t| >= 0.75 × seasonal-median-range[bucket(t)]

    Signal direction: mean-reversion toward session open
      direction = -sign(close_t - session_open_t)

    Entry: open of bar t+1
    Exit: close of bar t+3 OR first bar touching session_open_price (whichever first)
    Gross pips: direction × (exit_price - entry_open) / pip_size
    RT cost: entry_spread + exit_spread + RT_OVERHEAD (on CONDITIONED bars)
    """
    pip_size = PIP_SIZE[pair]
    df = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    relvol = compute_relvol(df)
    relrng = compute_relrng(df)
    session_open = compute_session_open_price(df)
    seasonal_med_rng = compute_seasonal_median_range(df)

    # Spread percentile gate (40th pctile, full-sample)
    spread_p40 = float(df["spread_median_pips"].quantile(V2_SPREAD_PCTILE / 100.0))

    signal_indices = []
    for t in range(len(df) - V2_HOLD_BARS - 1):
        rv = float(relvol.iloc[t])
        sp = float(df["spread_median_pips"].iloc[t])
        if sp <= 0 or np.isnan(sp):
            continue
        if rv < RELVOL_THRESHOLD:
            continue
        if sp > spread_p40:
            continue

        sess_open = float(session_open.iloc[t])
        close_t = float(df["close"].iloc[t])
        extension = abs(close_t - sess_open)
        med_rng = float(seasonal_med_rng.iloc[t])
        if extension < V2_EXTENSION_MULT * med_rng:
            continue

        direction = -1.0 if (close_t - sess_open) > 0 else 1.0
        signal_indices.append((t, direction, rv, float(relrng.iloc[t])))

    trades = []
    trade_relvol = []
    trade_relrng = []

    for (t, direction, rv_t, rr_t) in signal_indices:
        entry_i = t + 1
        if entry_i >= len(df):
            continue

        entry_open = float(df["open"].iloc[entry_i])
        entry_spread = float(df["spread_median_pips"].iloc[entry_i])
        if entry_spread <= 0 or np.isnan(entry_spread):
            continue

        target_price = float(session_open.iloc[t])  # reversion target = session open
        exit_i = None
        exit_price = None

        # Check each hold bar for early exit (price touches session_open)
        for h in range(1, V2_HOLD_BARS + 1):
            bar_i = entry_i + h
            if bar_i >= len(df):
                exit_i = entry_i + h - 1
                exit_price = float(df["close"].iloc[exit_i])
                break
            bar_high = float(df["high"].iloc[bar_i])
            bar_low = float(df["low"].iloc[bar_i])
            # Touch check: did price cross target (session open)?
            if direction > 0 and bar_high >= target_price:
                exit_i = bar_i
                exit_price = min(target_price, float(df["close"].iloc[bar_i]))
                break
            elif direction < 0 and bar_low <= target_price:
                exit_i = bar_i
                exit_price = max(target_price, float(df["close"].iloc[bar_i]))
                break
            if h == V2_HOLD_BARS:
                exit_i = bar_i
                exit_price = float(df["close"].iloc[bar_i])

        if exit_i is None or exit_price is None:
            continue

        exit_spread = float(df["spread_median_pips"].iloc[exit_i])
        if exit_spread <= 0 or np.isnan(exit_spread):
            continue

        price_move = direction * (exit_price - entry_open)
        gross_pips = price_move / pip_size
        rt_cost = entry_spread + exit_spread + RT_OVERHEAD

        trades.append({
            "signal_bar": df.index[t],
            "entry_bar": df.index[entry_i],
            "exit_bar": df.index[exit_i],
            "direction": direction,
            "relvol_t": round(rv_t, 4),
            "relrng_t": round(rr_t, 4),
            "gross_pips": round(gross_pips, 6),
            "entry_spread": entry_spread,
            "exit_spread": exit_spread,
            "rt_cost": round(rt_cost, 6),
            "net_pips": round(gross_pips - rt_cost, 6),
        })
        trade_relvol.append(rv_t)
        trade_relrng.append(rr_t)

    if not trades:
        return {"pair": pair, "candidate": "V2", "n_fires": 0,
                "spread_p40": round(spread_p40, 4),
                "error": "no qualifying trades after all filters"}

    tdf = pd.DataFrame(trades)
    n_fires = len(tdf)
    mean_gross = float(tdf["gross_pips"].mean())
    mean_rt_cost = float(tdf["rt_cost"].mean())
    margin = mean_gross - mean_rt_cost

    sample_years = (df.index[-1] - df.index[0]).days / 365.25
    fires_per_year = n_fires / sample_years

    gross_rt_ratio = mean_gross / mean_rt_cost if mean_rt_cost > 0 else float("nan")
    if gross_rt_ratio <= 0.80:
        cost_verdict = "FAIL"
    elif gross_rt_ratio <= 1.00:
        cost_verdict = "STRETCH"
    else:
        cost_verdict = "PASS"

    # V2 volatility construction check:
    # Verify conditioned-entry relrng median vs full-sample relrng median.
    # Construction disqualified if conditioned relrng median >= 1.2 × sample median.
    sample_relrng_median = 1.0  # by construction (relrng = rng / median(rng)), median = 1.0
    conditioned_relrng_median = float(np.median(trade_relrng))
    construction_ratio = conditioned_relrng_median / sample_relrng_median
    construction_valid = construction_ratio < 1.2

    vol_ctrl = run_volatility_control(
        gross_pips=tdf["gross_pips"].values,
        relvol=np.array(trade_relvol),
        relrng=np.array(trade_relrng),
        pair=pair,
        candidate="V2",
    )

    return {
        "pair": pair,
        "candidate": "V2",
        "n_fires": n_fires,
        "fires_per_year": round(fires_per_year, 1),
        "sample_years": round(sample_years, 2),
        "spread_p40_gate": round(spread_p40, 4),
        "mean_gross_pips": round(mean_gross, 4),
        "mean_rt_cost_pips": round(mean_rt_cost, 4),
        "gross_minus_cost_margin": round(margin, 4),
        "gross_rt_ratio": round(gross_rt_ratio, 4),
        "cost_verdict": cost_verdict,
        "v2_construction_check": {
            "sample_relrng_median": round(sample_relrng_median, 4),
            "conditioned_relrng_median": round(conditioned_relrng_median, 4),
            "conditioned_vs_sample_ratio": round(construction_ratio, 4),
            "construction_valid": construction_valid,
            "disqualified": not construction_valid,
            "note": (
                "CONSTRUCTION VALID: conditioned entries not high-range (anti-vol gate worked)"
                if construction_valid else
                "DISQUALIFIED: conditioned relrng >= 1.2x sample (spread-low gate failed to exclude volatility)"
            ),
        },
        "volatility_control": vol_ctrl,
        "trades": trades,
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 72)
    print("VOLUME-CONDITIONED FEASIBILITY SCREEN: V1 + V2")
    print("=" * 72)

    # ── JOB 1: C2COST FIX ASSERTION ─────────────────────────────────────────
    print("\n── JOB 1: C2COST FIX — NEW DISTINCT ASSERTION ──")
    c2cost_assr = run_c2cost_assertion()
    print(f"  Assertion name:       {c2cost_assr['assertion_name']}")
    print(f"  Description:          {c2cost_assr['description']}")
    print(f"  Spread:               {c2cost_assr['spread_pips']} pips")
    print(f"  RT overhead:          {c2cost_assr['rt_overhead_pips']} pips")
    print(f"  RT per leg:           {c2cost_assr['rt_per_leg_pips']} pips")
    print(f"  Position path:        {c2cost_assr['position_path']}")
    print(f"  Cost series:          {c2cost_assr['cost_series']}")
    print(f"  entry_i={c2cost_assr['entry_i']}, exit_i={c2cost_assr['exit_i']}, j(exit_change_bar)={c2cost_assr['j_exit_change_bar']}")
    print(f"  Buggy slice:          {c2cost_assr['buggy_slice']}")
    print(f"    → buggy cost:       {c2cost_assr['buggy_cost_pips']} pips  (entry only)")
    print(f"  Fixed slice:          {c2cost_assr['fixed_slice']}")
    print(f"    → fixed cost:       {c2cost_assr['fixed_cost_pips']} pips  (entry + exit = full RT)")
    print(f"  Expected full RT:     {c2cost_assr['expected_full_rt_pips']} pips")
    print(f"  Undercount per trade: {c2cost_assr['undercount_per_trade_pips']} pips  (= exactly 1 exit leg)")
    print(f"  ASSERTION PASSED:     {c2cost_assr['assertion_passed']} ✓")
    print(f"  Interpretation: {c2cost_assr['interpretation']}")

    # ── VOLUME/RANGE CORRELATION DIAGNOSTICS ────────────────────────────────
    print("\n── VOLUME ~ RANGE CORRELATION DIAGNOSTICS (per pair) ──")
    all_pairs_corr = sorted(set(V1_PAIRS) | set(V2_PAIRS))
    corr_results = []
    print(f"  {'Pair':<10} {'raw_vol~rng':>14} {'relvol~relrng':>16} {'logR²':>8}")
    print("  " + "-" * 55)
    for pair in all_pairs_corr:
        df_tmp = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
        if df_tmp.index.tz is None:
            df_tmp.index = df_tmp.index.tz_localize("UTC")
        c = compute_vol_range_corr(df_tmp, pair)
        corr_results.append(c)
        print(f"  {pair:<10} {c['raw_vol_range_spearman']:>14.4f} {c['relvol_relrng_spearman']:>16.4f} {c['log_relvol_log_relrng_R2']:>8.4f}")

    # ── JOB 2a: V1 SCREEN ───────────────────────────────────────────────────
    print("\n── JOB 2a: V1 — RELVOL-CONTINUATION SCREEN ──")
    print("  Session-open hours: 07 and 13 UTC (strict primary definition)")
    print(f"  relvol threshold: >= {RELVOL_THRESHOLD}x seasonal norm")
    print("  Hold: enter t+1 open, exit t+2 close (2-bar)")
    print("  Cost hurdle: entry_spread + exit_spread + 0.80 (CONDITIONED bars)")
    print()

    v1_results = {}
    for pair in V1_PAIRS:
        v1_results[pair] = run_v1_pair(pair)

    print(f"  {'Pair':<10} {'N_fires':>9} {'FPY':>7} {'Gross/tr':>10} {'RTcost/tr':>11} {'Margin':>9} {'Verdict'}")
    print("  " + "-" * 80)
    for pair in V1_PAIRS:
        r = v1_results[pair]
        if "error" in r:
            print(f"  {pair:<10}  ERROR: {r.get('error', '?')}")
            continue
        print(f"  {pair:<10} {r['n_fires']:>9} {r['fires_per_year']:>7.1f} {r['mean_gross_pips']:>10.4f} "
              f"{r['mean_rt_cost_pips']:>11.4f} {r['gross_minus_cost_margin']:>9.4f}  {r['cost_verdict']}")

    print("\n  Volatility-control (V1): relvol coefficient net of relrng_rank, OLS:")
    print(f"  {'Pair':<10} {'N':>6} {'rv_coef':>10} {'rv_t':>8} {'rr_coef':>10} {'rr_t':>8} {'R2':>6} {'Pass t>=2'}")
    print("  " + "-" * 75)
    for pair in V1_PAIRS:
        r = v1_results[pair]
        if "error" in r:
            continue
        vc = r["volatility_control"]
        print(f"  {pair:<10} {vc['n_trades']:>6} {vc['relvol_coef']:>10.5f} {vc['relvol_tstat']:>8.2f} "
              f"{vc['relrng_coef']:>10.5f} {vc['relrng_tstat']:>8.2f} {vc['r2']:>6.4f} {vc['pass_tstat_ge_2']}")

    print("\n  2×2 Stratification V1 (key cell: high_relvol × LOW_relrng = volume w/o volatility spike):")
    for pair in V1_PAIRS:
        r = v1_results[pair]
        if "error" in r:
            continue
        strat = r.get("stratification_2x2", {})
        key_cell = strat.get("high_relvol_x_low_relrng", {})
        high_high = strat.get("high_relvol_x_high_relrng", {})
        print(f"  {pair}: high_rv×low_rr: n={key_cell.get('n','?')}, "
              f"gross={key_cell.get('mean_gross','?')} pips   "
              f"high_rv×high_rr: n={high_high.get('n','?')}, "
              f"gross={high_high.get('mean_gross','?')} pips")

    # ── JOB 2b: V2 SCREEN ───────────────────────────────────────────────────
    print("\n── JOB 2b: V2 — RELVOL-HIGH ^ SPREAD-LOW MEAN-REVERSION SCREEN ──")
    print(f"  relvol >= {RELVOL_THRESHOLD} AND spread <= p{V2_SPREAD_PCTILE}")
    print(f"  Extension >= {V2_EXTENSION_MULT}× seasonal-median-range from session open")
    print("  Direction: mean-revert toward session open")
    print("  Hold: enter t+1 open, exit t+3 close or session-open touch, whichever first")
    print()

    v2_results = {}
    for pair in V2_PAIRS:
        v2_results[pair] = run_v2_pair(pair)

    print(f"  {'Pair':<10} {'N_fires':>9} {'FPY':>7} {'p40_sp':>8} {'Gross/tr':>10} {'RTcost/tr':>11} {'Margin':>9} {'Verdict'}")
    print("  " + "-" * 90)
    for pair in V2_PAIRS:
        r = v2_results[pair]
        if "error" in r:
            print(f"  {pair:<10}  ERROR: {r.get('error', '?')}")
            continue
        p40 = r.get("spread_p40_gate", float("nan"))
        print(f"  {pair:<10} {r['n_fires']:>9} {r['fires_per_year']:>7.1f} {p40:>8.4f} {r['mean_gross_pips']:>10.4f} "
              f"{r['mean_rt_cost_pips']:>11.4f} {r['gross_minus_cost_margin']:>9.4f}  {r['cost_verdict']}")

    print("\n  V2 construction check (conditioned relrng vs sample — must be <1.2x to be valid):")
    for pair in V2_PAIRS:
        r = v2_results[pair]
        if "error" in r:
            continue
        cc = r.get("v2_construction_check", {})
        print(f"  {pair}: conditioned relrng median = {cc.get('conditioned_relrng_median','?'):.4f} "
              f"(sample=1.0, ratio={cc.get('conditioned_vs_sample_ratio','?'):.4f}) → {cc.get('note','?')}")

    print("\n  Volatility-control (V2): relvol coefficient net of relrng_rank, OLS:")
    print(f"  {'Pair':<10} {'N':>6} {'rv_coef':>10} {'rv_t':>8} {'rr_coef':>10} {'rr_t':>8} {'R2':>6} {'Pass t>=2'}")
    print("  " + "-" * 75)
    for pair in V2_PAIRS:
        r = v2_results[pair]
        if "error" in r:
            continue
        vc = r["volatility_control"]
        print(f"  {pair:<10} {vc['n_trades']:>6} {vc['relvol_coef']:>10.5f} {vc['relvol_tstat']:>8.2f} "
              f"{vc['relrng_coef']:>10.5f} {vc['relrng_tstat']:>8.2f} {vc['r2']:>6.4f} {vc['pass_tstat_ge_2']}")

    print("\n── DONE. Saving raw JSON. ──")

    out = {
        "c2cost_assertion": c2cost_assr,
        "vol_range_correlations": corr_results,
        "v1": v1_results,
        "v2": v2_results,
    }
    out_json = SESSION_DIR / "volume_screen_raw.json"
    with out_json.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"  Raw JSON: {out_json}")
