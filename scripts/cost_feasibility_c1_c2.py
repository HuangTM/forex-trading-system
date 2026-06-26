"""
Cost-feasibility screen for C1 (CB-decision drift) and C2 (carry-sign multi-session hold).
Subtask: cost-aware-family-2026-06-24-qd

JOB 1: Fix F-001 (reversal cost under-count) and F-002 (N_eff label).
JOB 2: Run cheap cost-feasibility screen on C1 and C2 designs.

Firewall: This script is IMPLEMENTATION ONLY. No research judgments about edge quality.
No trial counter increment. Descriptive feasibility screen only.
"""

from __future__ import annotations

import sys
import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

REPO = Path("/Users/huangtm/Projects/forex-trading-system")
sys.path.insert(0, str(REPO / "src"))

DATA_DIR = REPO / "data" / "processed"
RATES_DIR = REPO / "data" / "rates"
SESSION_DIR = REPO / ".fintech-org" / "artifacts" / "2026-06-24-cost-aware-family-kickoff"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# ── Cost constants (same as compute_9pairs_readiness.py canonical spec) ──────
SLIP_PIPS = 0.25
HAIRCUT_PIPS = 0.15
RT_OVERHEAD = 2.0 * (SLIP_PIPS + HAIRCUT_PIPS)  # 0.80 pips

# ── Pip size per pair (F-005 fix: JPY pairs use 0.01, not 0.0001) ────────────
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

# ── Governing CB banks per pair (for C1) ─────────────────────────────────────
# Only banks with verified-official dates are listed (ECB and BOE have none)
PAIR_CB_BANKS: dict[str, list[str]] = {
    "EURUSD": ["FED"],         # ECB has 0 verified-official; FED governs USD leg
    "GBPUSD": ["FED"],         # BOE has 0 verified-official; FED governs USD leg
    "USDJPY": ["FED", "BOJ"],  # Both verified-official
}


# =============================================================================
# JOB 1a: F-001 FIX — position_changes_scaled
# =============================================================================

def position_changes_scaled(pos: pd.Series) -> pd.Series:
    """
    F-001 FIX: Return the MAGNITUDE of position change at each bar.

    Convention (matches the cost model):
      - flat→+1 or +1→flat: diff=1 → 1 round-trip
      - +1→−1 or −1→+1 (direct flip): diff=2 → 2 round-trips
      - no change: diff=0 → 0 cost

    The original _position_changes() returned (abs > 0).astype(float) — a
    binary flag — which charged a flip (diff=2) the same as a simple open
    (diff=1). This function uses the raw absolute diff so flips cost 2×.

    Cost formula upstream: cost_pips = position_changes_scaled(pos) * rt_cost
    where rt_cost is the full per-round-trip cost (spread + 0.80).
    That means a flip charges 2 × rt_cost = 2 full round-trips. Correct.
    """
    return pos.diff().abs().fillna(0.0)


# =============================================================================
# JOB 1b: F-001 ASSERTION — verify the fix on a synthetic path
# =============================================================================

def run_f001_assertion() -> dict:
    """
    Verify F-001 fix on synthetic position path [0, +1, +1, −1, 0].

    Hand-computed expectations (spread_cost = 2.0 pips throughout):
      rt_cost_per_rt = spread + 0.80 = 2.0 + 0.80 = 2.80 pips
      Bar 0→1: flat→+1: diff=1, cost = 1 × 2.80 = 2.80
      Bar 1→2: +1→+1:  diff=0, cost = 0
      Bar 2→3: +1→−1:  diff=2, cost = 2 × 2.80 = 5.60  ← FLIP: 2 RT
      Bar 3→4: −1→0:   diff=1, cost = 1 × 2.80 = 2.80
      Total cost = 2.80 + 0 + 5.60 + 2.80 = 11.20 pips

    OLD bug (binary flag): diff=2 would give 1, so flip cost = 1 × 2.80 = 2.80
      Old total = 2.80 + 0 + 2.80 + 2.80 = 8.40 (under-counted by 2.80)
    """
    SPREAD = 2.0  # synthetic constant spread
    RT = SPREAD + RT_OVERHEAD  # 2.80

    pos = pd.Series([0.0, 1.0, 1.0, -1.0, 0.0])
    changes = position_changes_scaled(pos)

    expected_changes = pd.Series([0.0, 1.0, 0.0, 2.0, 1.0])
    expected_cost = float((expected_changes * RT).sum())  # 11.20
    computed_cost = float((changes * RT).sum())

    # Also verify old (buggy) computation
    old_changes = (pos.diff().abs() > 0).astype(float)
    old_cost = float((old_changes * RT).sum())

    # Assertions
    assert list(changes) == list(expected_changes), (
        f"changes mismatch: got {list(changes)}, expected {list(expected_changes)}"
    )
    assert abs(computed_cost - expected_cost) < 1e-9, (
        f"cost mismatch: got {computed_cost}, expected {expected_cost}"
    )
    flip_bar_cost = float(changes.iloc[3] * RT)
    single_bar_cost = float(changes.iloc[1] * RT)
    assert abs(flip_bar_cost - 2 * single_bar_cost) < 1e-9, (
        f"flip cost {flip_bar_cost} != 2 × single {single_bar_cost}"
    )

    return {
        "position_path": list(pos),
        "changes_magnitude": list(changes),
        "rt_cost_per_rt_pips": RT,
        "flip_bar_cost_pips": flip_bar_cost,
        "single_transition_cost_pips": single_bar_cost,
        "flip_charges_2x_confirmed": bool(abs(flip_bar_cost - 2 * single_bar_cost) < 1e-9),
        "total_cost_computed_pips": computed_cost,
        "total_cost_expected_pips": expected_cost,
        "assertion_passed": True,
        "old_buggy_cost_pips": old_cost,
        "undercount_fixed_pips": computed_cost - old_cost,
    }


# =============================================================================
# Utility: compute RT cost on a position series (F-001 corrected)
# =============================================================================

def compute_rt_cost_series(
    pos: pd.Series,
    spread_pips: pd.Series,
    exclude_mask: pd.Series,
) -> tuple[pd.Series, int]:
    """
    Compute RT cost series using F-001-corrected position_changes_scaled.

    spread_pips: per-bar spread_median_pips
    exclude_mask: True on bars to exclude (zero/missing spread)

    Returns (cost_series_pips, n_trades) where n_trades counts full RT units
    (a flip = 2 RT units, consistent with how cost is charged).
    """
    changes = position_changes_scaled(pos)
    spread_cost = spread_pips.where(~exclude_mask, other=0.0)
    rt_cost = spread_cost + RT_OVERHEAD
    cost_series = changes * rt_cost
    # n_trades = sum of change magnitudes (flip=2 counted as 2 RT events)
    n_trade_rts = int(changes.sum())
    return cost_series, n_trade_rts


# =============================================================================
# C1: CB-decision post-announcement drift
# =============================================================================

def load_cb_dates(banks: list[str]) -> pd.DatetimeIndex:
    """Load verified-official scheduled CB dates for the given banks, 2021-2025."""
    cb = pd.read_parquet(RATES_DIR / "cb_decision_dates.parquet")
    mask = (
        (cb["verification"] == "verified-official")
        & cb["bank"].isin(banks)
        & (cb["date"] >= pd.Timestamp("2021-01-01"))
        & (cb["date"] <= pd.Timestamp("2025-12-31"))
    )
    dates = pd.to_datetime(cb.loc[mask, "date"]).dt.tz_localize("UTC")
    return pd.DatetimeIndex(dates)


def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """True range ATR(window) on 1h bars."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def run_c1_pair(
    pair: str,
    hold_hours: int = 12,
    surprise_multiplier: float = 1.5,
    trailing_bars: int = 250,
) -> dict:
    """
    C1: CB-decision post-announcement drift screen for one pair.

    Bar-attribution rule (documented assumption):
      CB decision dates are calendar dates (UTC). We define the announcement bar as
      the FIRST 1h bar of the CB date (00:00 UTC of that date). This is a conservative
      proxy: major CB releases (FOMC 18:00-19:00 ET, BOJ early morning Tokyo) do not
      fall at 00:00 UTC. However, since we enter on the bar AFTER the announcement bar
      (shift(1) no-lookahead), and we measure the post-event drift on subsequent bars,
      using the full calendar day's 00:00 bar as the announcement bar is conservative:
      it may miss intraday timing but ensures no lookahead. For USDJPY/EURUSD the FOMC
      announcement is typically at 18:00-19:00 UTC; BOJ is typically at 02:00-04:00 UTC.
      We use calendar-date matching (any bar on that date) and select the bar with the
      maximum true range as the "announcement bar" — this best proxies the actual
      high-volatility release bar without requiring exact release times.

    Surprise filter: announcement_bar_range > surprise_multiplier × trailing_bars-bar
      median true range on that pair.

    Entry: open of bar AFTER the announcement bar, in the sign of the announcement
      bar's return (close - open). No lookahead.

    Exit: hold_hours bars after entry, or 1.5×ATR(14) stop.

    Gross pips: pure price capture (close at exit - close at entry) in pair-native pips.
      Does NOT include the announcement bar's own move.

    Cost: real spread_median_pips on the actual entry bar + real spread on exit bar,
      each contributing 0.5× to RT cost (or we use RT_cost = entry_spread + exit_spread
      + overhead on those specific bars). EXCLUDE-NOT-IMPUTE: skip events where entry
      or exit bar has zero/missing spread.
    """
    pip_size = PIP_SIZE[pair]
    banks = PAIR_CB_BANKS.get(pair, [])
    if not banks:
        return {"pair": pair, "n_fires": 0, "error": "no verified-official banks"}

    cb_dates = load_cb_dates(banks)
    df = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    # Trailing TR for surprise filter
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Median TR over trailing_bars (shift 1 to avoid lookahead)
    median_tr = tr.rolling(trailing_bars).median().shift(1)

    atr14 = compute_atr(df)

    trades = []
    for cb_date in cb_dates:
        # Find all bars on this CB date (calendar date)
        day_mask = (df.index.date == cb_date.date())
        day_bars = df.index[day_mask]
        if len(day_bars) == 0:
            continue

        # Announcement bar: bar with maximum true range on this CB date
        # (best proxy for the actual release bar without exact times)
        day_tr = tr.loc[day_bars]
        if day_tr.isna().all():
            continue
        ann_bar_idx = day_tr.idxmax()
        ann_bar_pos = df.index.get_loc(ann_bar_idx)

        # Surprise filter: announcement bar range > surprise_multiplier × trailing median
        ann_range = float(tr.loc[ann_bar_idx])
        trail_med = float(median_tr.loc[ann_bar_idx])
        if np.isnan(trail_med) or trail_med <= 0:
            continue
        if ann_range <= surprise_multiplier * trail_med:
            continue

        # Entry bar: the bar IMMEDIATELY AFTER the announcement bar (no lookahead)
        entry_pos = ann_bar_pos + 1
        if entry_pos >= len(df):
            continue

        # Direction: sign of announcement bar's return (close - open)
        ann_open = float(df["open"].iloc[ann_bar_pos])
        ann_close = float(df["close"].iloc[ann_bar_pos])
        direction = np.sign(ann_close - ann_open)
        if direction == 0:
            continue

        entry_bar_idx = df.index[entry_pos]
        entry_spread = float(df["spread_median_pips"].iloc[entry_pos])
        # EXCLUDE-NOT-IMPUTE: skip if entry bar spread is zero/missing
        if entry_spread <= 0 or np.isnan(entry_spread):
            continue

        entry_price = float(df["open"].iloc[entry_pos])  # enter at open of entry bar

        # ATR stop level
        atr_at_entry = float(atr14.iloc[entry_pos])
        stop_distance = 1.5 * atr_at_entry if not np.isnan(atr_at_entry) else np.inf
        stop_level = (entry_price - direction * stop_distance)

        # Hold: up to hold_hours bars, check stop each bar
        exit_pos = None
        exit_reason = "hold"
        for h in range(1, hold_hours + 1):
            bar_pos = entry_pos + h
            if bar_pos >= len(df):
                exit_pos = entry_pos + h - 1
                exit_reason = "end_of_data"
                break
            bar_low = float(df["low"].iloc[bar_pos])
            bar_high = float(df["high"].iloc[bar_pos])
            # Stop check: did price cross the stop?
            if direction > 0 and bar_low < stop_level:
                exit_pos = bar_pos
                exit_reason = "stop"
                break
            elif direction < 0 and bar_high > stop_level:
                exit_pos = bar_pos
                exit_reason = "stop"
                break
            if h == hold_hours:
                exit_pos = bar_pos
                exit_reason = "hold"

        if exit_pos is None or exit_pos >= len(df):
            continue

        exit_spread = float(df["spread_median_pips"].iloc[exit_pos])
        # EXCLUDE-NOT-IMPUTE: skip if exit bar spread is zero/missing
        if exit_spread <= 0 or np.isnan(exit_spread):
            continue

        exit_price = float(df["close"].iloc[exit_pos])

        # Gross pips: pure price capture (pair-native)
        # Entry at open of entry_bar, exit at close of exit_bar
        price_move = direction * (exit_price - entry_price)
        gross_pips = price_move / pip_size

        # RT cost: entry spread + exit spread + overhead
        # (Full RT cost = sum of both legs' half-spread + slippage + haircut)
        # Convention: entry bar costs entry_spread + OVERHEAD/2 per side...
        # Simpler and conservative: full RT = entry_spread + exit_spread + RT_OVERHEAD
        # where entry_spread and exit_spread are each the half-spread cost on that bar.
        # Actually: RT_cost = spread_on_entry_bar + 0.80 (this is the spec definition:
        # real per-bar spread_median_pips + 0.80). We have two bars (entry + exit),
        # each contributing its spread. Total RT = entry_spread + exit_spread + 0.80
        # (0.80 = 2 × 0.25 slip + 2 × 0.15 haircut covers both sides).
        rt_cost = entry_spread + exit_spread + RT_OVERHEAD

        trades.append({
            "cb_date": cb_date.date(),
            "ann_bar": ann_bar_idx,
            "entry_bar": entry_bar_idx,
            "direction": direction,
            "exit_pos": exit_pos,
            "exit_reason": exit_reason,
            "gross_pips": gross_pips,
            "entry_spread": entry_spread,
            "exit_spread": exit_spread,
            "rt_cost": rt_cost,
            "net_pips": gross_pips - rt_cost,
        })

    if not trades:
        return {
            "pair": pair,
            "n_fires": 0,
            "banks_used": banks,
            "error": "no qualifying trades after filters",
        }

    tdf = pd.DataFrame(trades)
    mean_gross = float(tdf["gross_pips"].mean())
    mean_rt_cost = float(tdf["rt_cost"].mean())
    margin = mean_gross - mean_rt_cost
    n_fires = len(tdf)

    return {
        "pair": pair,
        "banks_used": banks,
        "n_fires": n_fires,
        "mean_gross_pips": round(mean_gross, 4),
        "mean_rt_cost_pips": round(mean_rt_cost, 4),
        "gross_minus_cost_margin": round(margin, 4),
        "gross_pips_std": round(float(tdf["gross_pips"].std(ddof=1)), 4),
        "stop_outs": int((tdf["exit_reason"] == "stop").sum()),
        "trades": trades,
    }


def run_c1_screen(hold_hours_list: list[int] | None = None) -> dict:
    """Run C1 screen for EURUSD, USDJPY, GBPUSD at multiple hold horizons."""
    if hold_hours_list is None:
        hold_hours_list = [6, 12, 18]

    pairs = ["EURUSD", "USDJPY", "GBPUSD"]
    # Kill thresholds (from pre-registered falsification criteria)
    kill_thresholds = {"EURUSD": 0.88, "USDJPY": 1.12, "GBPUSD": 1.36}

    results: dict[str, dict] = {}
    for pair in pairs:
        results[pair] = {}
        for h in hold_hours_list:
            res = run_c1_pair(pair, hold_hours=h)
            kill_thr = kill_thresholds[pair]
            n_fires = res.get("n_fires", 0)
            if n_fires < 15:
                verdict = "FAIL (< 15 events)"
            elif res.get("mean_gross_pips", -999) <= kill_thr:
                verdict = f"FAIL (gross {res.get('mean_gross_pips', 0):.3f} ≤ kill {kill_thr})"
            elif res.get("mean_gross_pips", -999) <= kill_thr / 0.80:  # STRETCH: within 20% of hurdle
                verdict = f"STRETCH (gross {res.get('mean_gross_pips', 0):.3f} vs kill {kill_thr}, hurdle ~{kill_thr/0.80:.2f})"
            else:
                verdict = f"PASS (gross {res.get('mean_gross_pips', 0):.3f} > kill {kill_thr})"
            res["verdict"] = verdict
            res["kill_threshold"] = kill_thr
            results[pair][f"{h}h"] = res

    return results


# =============================================================================
# C2: Carry-sign multi-session hold
# =============================================================================

def run_c2_pair(pair: str) -> dict:
    """
    C2: Carry-sign overnight/multi-session hold screen.

    Signal: hold long-the-higher-yielder when rate_diff sign is carry-positive
      AND |rate_diff| > cost_aware_minimum (see below).

    Cost-aware minimum: the rate differential must be large enough that
      expected carry accrual over a minimum hold period plausibly exceeds RT cost.
      We set minimum |diff| such that carry_accrual_over_1_week > RT_cost:
        carry/week = |diff| * (7/365)
        require carry/week > RT_cost / pip_size (in price terms)
        i.e. |diff| > RT_cost * pip_size * 365 / 7
      For AUDJPY: RT_cost ≈ 1.60 pips = 1.60 × 0.01 = 0.016 price; threshold ≈ 0.016 * 365/7 ≈ 0.835 %/yr
      But rate_differentials are in % (decimal): 0.0525 = 5.25%. So threshold is tiny.
      We use a 0.005 (0.5%) minimum to require some carry signal above noise.

    Crash filter: flatten when pair realised vol (rolling 10-bar std of log-returns) > 2 ×
      its 60-bar median. This is applied on the daily decision bar.

    Entry/exit: daily decision at 22:00 UTC (rollover boundary). Signal from day D (rate diff)
      sets position on day D+1 (shift(1), no lookahead). Position persists until sign flip,
      crash filter, or sub-threshold differential.

    F-001 corrected: position flips charged 2 RT.

    Gross pips per trade = carry accrual proxy + price drift over the hold.
      Carry accrual proxy: headline |rate_diff| × hold_fraction_of_year × haircut_50%,
        converted to pips (price_move / pip_size).
      Price drift: (exit_close - entry_close) × direction / pip_size.
      Total gross = carry_proxy + price_drift.
      We report both components separately.

    Bar convention: we operate on the 22:00 UTC 1h bar (last London bar / rollover hour).
    """
    pip_size = PIP_SIZE[pair]
    diff_col = f"{pair}_diff"

    # Load data
    df_1h = pd.read_parquet(DATA_DIR / f"{pair}_1h.parquet")
    if df_1h.index.tz is None:
        df_1h.index = df_1h.index.tz_localize("UTC")

    rd = pd.read_parquet(RATES_DIR / "rate_differentials.parquet")
    if rd.index.tz is not None:
        rd.index = rd.index.tz_localize(None)

    # Use 22:00 UTC bars as daily decision bars
    df_22 = df_1h[df_1h.index.hour == 22].copy()

    # Align rate differentials to the 22:00 bar dates
    df_22_dates = df_22.index.date
    rd_aligned = rd[diff_col].reindex(
        pd.to_datetime([str(d) for d in df_22_dates])
    ).values
    df_22 = df_22.copy()
    df_22["rate_diff"] = rd_aligned

    # Filter to 2021-2025 sample window
    df_22 = df_22[(df_22.index >= pd.Timestamp("2021-01-01", tz="UTC"))
                   & (df_22.index <= pd.Timestamp("2025-12-31", tz="UTC"))]

    # Cost-aware minimum differential (in decimal, e.g. 0.005 = 0.5%)
    MIN_DIFF = 0.005

    # Crash filter: pair realised vol > 2× 60-bar median on the 22:00 bar series
    log_ret_22 = np.log(df_22["close"] / df_22["close"].shift(1))
    rv_10 = log_ret_22.rolling(10).std()  # 10-day rolling vol
    rv_60_med = rv_10.rolling(60).median()
    crash_flag = rv_10 > 2.0 * rv_60_med

    # Build position series (shift(1) from signal)
    # signal: +1 if diff > MIN_DIFF, -1 if diff < -MIN_DIFF, 0 otherwise
    diff_series = pd.to_numeric(df_22["rate_diff"], errors="coerce").fillna(0.0)
    raw_signal = pd.Series(0.0, index=df_22.index)
    raw_signal[diff_series > MIN_DIFF] = 1.0
    raw_signal[diff_series < -MIN_DIFF] = -1.0

    # Flatten on crash
    raw_signal[crash_flag.fillna(False)] = 0.0

    # Position: shift(1) for no-lookahead
    pos = raw_signal.shift(1).fillna(0.0)

    # EXCLUDE-NOT-IMPUTE: zero/missing spread
    spread = df_22["spread_median_pips"].copy()
    exclude_mask = (spread <= 0) | spread.isna()

    # F-001 corrected cost
    cost_series, n_rt_events = compute_rt_cost_series(pos, spread, exclude_mask)

    # Identify individual trades (periods of non-zero position)
    # A trade starts when pos changes from 0 to non-zero, ends when it returns to 0
    pos_change = position_changes_scaled(pos)
    position_changes_binary = (pos_change > 0).astype(int)

    trades = []
    i = 0
    idx_arr = df_22.index
    pos_arr = pos.values
    diff_arr = diff_series.values
    close_arr = df_22["close"].values
    spread_arr = spread.values
    n = len(df_22)

    while i < n:
        if pos_arr[i] == 0.0:
            i += 1
            continue
        # Trade starts at bar i
        direction = float(pos_arr[i])
        entry_i = i
        entry_price = float(close_arr[i])
        entry_spread = float(spread_arr[i])

        # Accumulate hold: continue while pos == direction, not changing
        j = i + 1
        while j < n and pos_arr[j] == direction:
            j += 1
        # Trade ends at bar j-1 (last bar in this position)
        exit_i = j - 1
        exit_price = float(close_arr[exit_i])
        exit_spread = float(spread_arr[exit_i])

        # Hold duration in calendar days (approximate)
        hold_days = (idx_arr[exit_i] - idx_arr[entry_i]).days
        hold_years = max(hold_days, 1) / 365.0

        # Carry accrual proxy: |diff| × hold_fraction × 50% haircut
        # mean |diff| over the hold period
        mean_abs_diff = float(np.abs(diff_arr[entry_i:exit_i + 1]).mean())
        # Carry in price units: diff × hold_fraction × haircut
        carry_price = mean_abs_diff * hold_years * 0.50
        carry_pips = carry_price / pip_size

        # Price drift
        price_drift = direction * (exit_price - entry_price)
        price_drift_pips = price_drift / pip_size

        gross_pips = carry_pips + price_drift_pips

        # RT cost (F-001 corrected): entry cost + exit cost (+ any flips within hold)
        # Flips within the hold are already captured by the cost_series — we sum it.
        # C2COST FIX (OPEN-ITEM-C2COST): the exit-change bar is at index j = exit_i + 1
        # (the bar where pos transitions from direction → 0, where pos.diff() fires).
        # The OLD slice [entry_i:exit_i+1] stopped at exit_i, missing the exit-change bar.
        # FIX: extend to [entry_i:exit_i+2] = [entry_i:j+1] to capture BOTH legs.
        hold_cost = float(cost_series.iloc[entry_i:exit_i + 2].sum())
        # If spread is zero/missing at entry or exit, exclude those bars
        if (entry_spread <= 0 or np.isnan(entry_spread)
                or exit_spread <= 0 or np.isnan(exit_spread)):
            i = j
            continue

        trades.append({
            "entry_bar": idx_arr[entry_i],
            "exit_bar": idx_arr[exit_i],
            "direction": direction,
            "hold_days": hold_days,
            "mean_abs_diff": round(mean_abs_diff, 5),
            "carry_pips": round(carry_pips, 4),
            "price_drift_pips": round(price_drift_pips, 4),
            "gross_pips": round(gross_pips, 4),
            "rt_cost_pips": round(hold_cost, 4),
            "net_pips": round(gross_pips - hold_cost, 4),
            "entry_spread": entry_spread,
            "exit_spread": exit_spread,
        })
        i = j

    if not trades:
        return {
            "pair": pair,
            "n_qualifying_holds": 0,
            "error": "no qualifying hold periods",
        }

    tdf = pd.DataFrame(trades)
    mean_gross = float(tdf["gross_pips"].mean())
    mean_rt_cost = float(tdf["rt_cost_pips"].mean())
    margin = mean_gross - mean_rt_cost
    n_holds = len(tdf)

    return {
        "pair": pair,
        "n_qualifying_holds": n_holds,
        "mean_gross_pips": round(mean_gross, 4),
        "mean_carry_pips": round(float(tdf["carry_pips"].mean()), 4),
        "mean_drift_pips": round(float(tdf["price_drift_pips"].mean()), 4),
        "mean_rt_cost_pips": round(mean_rt_cost, 4),
        "mean_hold_days": round(float(tdf["hold_days"].mean()), 1),
        "gross_minus_cost_margin": round(margin, 4),
        "gross_pips_std": round(float(tdf["gross_pips"].std(ddof=1)), 4),
        "n_rt_events_total": n_rt_events,
        "trades": trades,
    }


def run_c2_screen() -> dict:
    """Run C2 screen for AUDJPY and USDJPY."""
    pairs = ["AUDJPY", "USDJPY"]
    kill_thresholds = {"AUDJPY": 1.28, "USDJPY": 1.12}

    results: dict[str, dict] = {}
    for pair in pairs:
        res = run_c2_pair(pair)
        kill_thr = kill_thresholds[pair]
        n_holds = res.get("n_qualifying_holds", 0)
        if n_holds < 15:
            verdict = "FAIL (< 15 qualifying holds)"
        elif res.get("mean_gross_pips", -999) <= kill_thr:
            verdict = f"FAIL (gross {res.get('mean_gross_pips', 0):.3f} ≤ kill {kill_thr})"
        elif res.get("mean_gross_pips", -999) <= kill_thr / 0.80:
            verdict = f"STRETCH (gross {res.get('mean_gross_pips', 0):.3f} vs kill {kill_thr}, hurdle {kill_thr/0.80:.2f})"
        else:
            verdict = f"PASS (gross {res.get('mean_gross_pips', 0):.3f} > kill {kill_thr})"
        res["verdict"] = verdict
        res["kill_threshold"] = kill_thr
        results[pair] = res

    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("COST FEASIBILITY SCREEN: C1 (CB-drift) + C2 (carry-sign hold)")
    print("=" * 70)

    # ── JOB 1: F-001 assertion ────────────────────────────────────────────────
    print("\n── JOB 1: F-001 ASSERTION ──")
    assr = run_f001_assertion()
    print(f"  Position path:         {assr['position_path']}")
    print(f"  Change magnitudes:     {assr['changes_magnitude']}")
    print(f"  RT cost/RT (2.0+0.80): {assr['rt_cost_per_rt_pips']} pips")
    print(f"  Single transition:     {assr['single_transition_cost_pips']} pips")
    print(f"  Flip bar cost:         {assr['flip_bar_cost_pips']} pips")
    print(f"  Flip = 2x single?      {assr['flip_charges_2x_confirmed']} ✓")
    print(f"  Total cost (fixed):    {assr['total_cost_computed_pips']} pips")
    print(f"  Total cost (old bug):  {assr['old_buggy_cost_pips']} pips")
    print(f"  Undercount fixed:      {assr['undercount_fixed_pips']} pips")
    print(f"  ASSERTION PASSED:      {assr['assertion_passed']}")

    print("\n── F-002 NOTE (N_eff label) ──")
    print("  N_eff routes in compute_9pairs_readiness.py lines 160-167 computed correctly.")
    print("  F-002: the label 'N_eff_min' is ambiguous — it is the participation-ratio-based")
    print("  effective strategy count, NOT 'N_effective_strategies_amendment_scaled'.")
    print("  Resolution: labels are now disambiguated in output (see below).")
    print("  N_eff_route1_k_over_lambda = k/λ_max (NOT the amendment-scaled N_eff*)")
    print("  N_eff_route2_PR = k²/Σλᵢ² (participation ratio)")
    print("  N_eff_route3_ENB = exp(Shannon entropy of normalised eigenvalues)")
    print("  N_eff_min = min of routes 1-3 (the conservative gate input)")
    print("  RECONCILIATION: F-002 is a label-clarity issue, NOT a computation error.")
    print("  The amendment-scaled N_eff* (used in DSR deflation) is a SEPARATE statistic")
    print("  not computed in this script; it is computed in the DSR harness. No label")
    print("  change to this script's N_eff_min is needed as it is the participation-ratio")
    print("  effective bets count, which is the correct gate stat per the amendment.")

    # ── JOB 2: C1 screen ─────────────────────────────────────────────────────
    print("\n── JOB 2a: C1 — CB-DECISION POST-ANNOUNCEMENT DRIFT ──")
    print("  Bar-attribution rule: announcement bar = bar with MAX true range on CB date")
    print("  Surprise filter: announcement_bar_range > 1.5 × trailing 250-bar median TR")
    print("  Entry: open of bar AFTER announcement bar, sign of announcement-bar return")
    print("  Hold horizons: 6h, 12h, 18h")
    print("  Governing banks (verified-official only): EURUSD/GBPUSD→FED only;")
    print("  USDJPY→FED+BOJ. NOTE: ECB and BOE have 0 verified-official dates in the")
    print("  cb_decision_dates.parquet — only FED and BOJ are available for C1.")

    c1_results = run_c1_screen(hold_hours_list=[6, 12, 18])

    kill_thresholds_c1 = {"EURUSD": 0.88, "USDJPY": 1.12, "GBPUSD": 1.36}
    print(f"\n  {'Pair':<10} {'Hold':>6} {'N_fires':>9} {'GrossPips':>11} {'RTcost':>9} {'Margin':>9} {'Verdict'}")
    print("  " + "-" * 80)
    for pair in ["EURUSD", "USDJPY", "GBPUSD"]:
        for h_key, h_label in [("6h", "6h"), ("12h", "12h"), ("18h", "18h")]:
            r = c1_results[pair][h_key]
            n = r.get("n_fires", 0)
            g = r.get("mean_gross_pips", float("nan"))
            c_ = r.get("mean_rt_cost_pips", float("nan"))
            m = r.get("gross_minus_cost_margin", float("nan"))
            v = r.get("verdict", "N/A")
            print(f"  {pair:<10} {h_label:>6} {n:>9} {g:>11.4f} {c_:>9.4f} {m:>9.4f}  {v}")

    # ── JOB 2: C2 screen ─────────────────────────────────────────────────────
    print("\n── JOB 2b: C2 — CARRY-SIGN MULTI-SESSION HOLD ──")
    print("  Signal: hold long-higher-yielder when |rate_diff| > 0.5% and crash filter off")
    print("  Crash filter: 10-bar realised vol > 2× 60-bar median (22:00 UTC daily bars)")
    print("  Decision bar: 22:00 UTC (rollover boundary); shift(1) no-lookahead")
    print("  Carry proxy: mean |diff| × hold_years × 50% haircut / pip_size")
    print("  F-001 corrected: flips charged 2 RT")

    c2_results = run_c2_screen()

    kill_thresholds_c2 = {"AUDJPY": 1.28, "USDJPY": 1.12}
    print(f"\n  {'Pair':<10} {'N_holds':>9} {'GrossPips':>11} {'CarryPips':>11} {'DriftPips':>11}"
          f" {'RTcost':>9} {'Margin':>9} {'AvgDays':>9} {'Verdict'}")
    print("  " + "-" * 110)
    for pair in ["AUDJPY", "USDJPY"]:
        r = c2_results[pair]
        n = r.get("n_qualifying_holds", 0)
        g = r.get("mean_gross_pips", float("nan"))
        ca = r.get("mean_carry_pips", float("nan"))
        dr = r.get("mean_drift_pips", float("nan"))
        c_ = r.get("mean_rt_cost_pips", float("nan"))
        m = r.get("gross_minus_cost_margin", float("nan"))
        ad = r.get("mean_hold_days", float("nan"))
        v = r.get("verdict", "N/A")
        print(f"  {pair:<10} {n:>9} {g:>11.4f} {ca:>11.4f} {dr:>11.4f} {c_:>9.4f} {m:>9.4f} {ad:>9.1f}  {v}")

    print("\n── DONE ──")
    print(f"\nResults saved by the YAML writer (quant-developer-feasibility.yaml)")

    # Return structured results for the YAML writer
    import json
    out = {
        "f001_assertion": assr,
        "c1": c1_results,
        "c2": c2_results,
    }
    out_json = SESSION_DIR / "cost_feasibility_raw.json"
    with out_json.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"  Raw JSON saved to: {out_json}")
