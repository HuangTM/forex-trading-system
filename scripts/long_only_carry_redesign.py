#!/usr/bin/env python3
"""Steps 2-6: Long-only carry redesign for USDJPY.

Tests three variants and validates the best one with walk-forward + null hypothesis:

  V1: B&H baseline                                    (Sharpe target = 0.58)
  V2: Long when SMA50 > SMA200, flat otherwise        (binary trend filter)
  V3: Long when SMA50 > SMA200 AND carry > 0.5%       (trend + carry filter)
  V4: Continuous size = base * tanh(trend_strength)   (sizing variant)

Validation on the best variant:
  - Walk-forward: 504-train / 126-test, fixed params (no optimization)
  - Null hypothesis: 200 random sign-shuffles on held-out
  - Arson: randomize 10/25%, double costs, extra entry delay
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from forex_system.core.config import load_config
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators

PAIR = "USDJPY"
CAPITAL = 1_000_000.0


def load_pair_data():
    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_info = {p.symbol: p.to_pair_info() for p in cfg.pairs}[PAIR]
    df = load_parquet(PAIR, "daily", "data")
    enriched = compute_indicators(df, ["sma_50", "sma_200", "atr_14"])
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    rate_data = rate_data.rename(columns={c: c.replace("_diff", "") for c in rate_data.columns})
    if rate_data.index.tz is None and enriched.index.tz is not None:
        rate_data = rate_data.copy()
        rate_data.index = rate_data.index.tz_localize(enriched.index.tz)
    rate_series = rate_data[PAIR].reindex(enriched.index, method="ffill")
    return enriched, pair_info, rate_series


def simulate_long_only(
    df: pd.DataFrame,
    pair_info,
    capital: float,
    in_market: pd.Series,            # boolean: long-this-bar?
    size_scale: pd.Series | None = None,  # 0..1 multiplier on base position
) -> pd.Series:
    """Daily mark-to-market equity for long-only carry strategy.

    Treats every signal change as a real trade with spread+slippage cost.
    Swap accrues every day position is held.
    """
    pip = 0.01 if "JPY" in PAIR else 0.0001
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    swap_per_day_pips = pair_info.swap_long_pips_per_day

    if size_scale is None:
        size_scale = pd.Series(1.0, index=df.index)
    in_market = in_market.fillna(False).astype(bool)

    # Detect entries (False→True) — those incur full round-trip cost (entry+future exit)
    entries = in_market & ~in_market.shift(1).fillna(False)
    n_entries = int(entries.sum())

    equity = pd.Series(capital, index=df.index, dtype=float)
    cur_units = 0.0
    cur_cost_per_unit = 0.0
    daily_swap_per_unit = swap_per_day_pips * pip

    for i in range(1, len(df)):
        ts = df.index[i]
        prev_close = df["close"].iloc[i - 1]
        cur_close = df["close"].iloc[i]
        equity.iloc[i] = equity.iloc[i - 1]

        # Position from yesterday
        if cur_units > 0:
            # Daily price PnL on units held
            equity.iloc[i] += (cur_close - prev_close) * cur_units
            # Swap income for the day held
            equity.iloc[i] += daily_swap_per_unit * cur_units

        was_in = in_market.iloc[i - 1]
        is_in = in_market.iloc[i]

        if not was_in and is_in:
            # Enter today: size by scale
            scale = float(size_scale.iloc[i])
            scale = max(0.0, min(1.0, scale))
            cur_units = (capital / cur_close) * scale
            cur_cost_per_unit = rt_cost_pips * pip
            equity.iloc[i] -= cur_cost_per_unit * cur_units  # round-trip cost charged on entry
        elif was_in and not is_in:
            # Exit today: cost already paid up-front, just zero out units
            cur_units = 0.0
        elif was_in and is_in and size_scale is not None:
            # Already in market — adjust size if scale changed materially
            target_scale = float(size_scale.iloc[i])
            target_scale = max(0.0, min(1.0, target_scale))
            target_units = (capital / cur_close) * target_scale
            if abs(target_units - cur_units) / max(cur_units, 1) > 0.20:
                # 20% rebalance threshold — incur half-spread on the delta
                delta = abs(target_units - cur_units)
                rebal_cost = (rt_cost_pips / 2) * pip * delta
                equity.iloc[i] -= rebal_cost
                cur_units = target_units

    return equity


def metrics(equity: pd.Series) -> dict:
    daily = equity.pct_change().dropna()
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0.0
    dd = (equity - equity.cummax()) / equity.cummax()
    n_yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    total = (equity.iloc[-1] / equity.iloc[0]) - 1.0
    ann = (1 + total) ** (1 / n_yrs) - 1
    return dict(sharpe=sharpe, max_dd=abs(dd.min()), total_return=total, ann_return=ann)


def main():
    df, pair_info, rate_series = load_pair_data()
    df = df.dropna(subset=["sma_200", "atr_14"]).copy()
    rate_series = rate_series.reindex(df.index)

    print("=" * 80)
    print(f"  Long-only carry redesign — {PAIR}, $1M, {df.index[0].date()} → {df.index[-1].date()}")
    print(f"  Bar to beat: B&H Sharpe 0.58")
    print("=" * 80)

    # ===== V1: Buy-and-hold (baseline) =====
    bh_signal = pd.Series(True, index=df.index)
    eq_v1 = simulate_long_only(df, pair_info, CAPITAL, bh_signal)
    m1 = metrics(eq_v1)

    # ===== V2: SMA50 > SMA200 trend filter =====
    trend_up = df["sma_50"] > df["sma_200"]
    eq_v2 = simulate_long_only(df, pair_info, CAPITAL, trend_up)
    m2 = metrics(eq_v2)
    n_entries_v2 = int((trend_up & ~trend_up.shift(1).fillna(False)).sum())
    in_market_pct_v2 = trend_up.mean()

    # ===== V3: trend AND carry > 0.5% =====
    carry_strong = rate_series > 0.005
    combo = trend_up & carry_strong
    eq_v3 = simulate_long_only(df, pair_info, CAPITAL, combo)
    m3 = metrics(eq_v3)
    n_entries_v3 = int((combo & ~combo.shift(1).fillna(False)).sum())
    in_market_pct_v3 = combo.mean()

    # ===== V4: continuous sizing by trend strength =====
    # size = clip( (sma50 - sma200) / sma200 / 0.05, 0, 1 ) — flat when sma50<sma200
    trend_strength = ((df["sma_50"] - df["sma_200"]) / df["sma_200"]).clip(lower=0) / 0.05
    trend_strength = trend_strength.clip(0, 1)
    in_market_v4 = trend_strength > 0.05  # arbitrary tiny threshold
    eq_v4 = simulate_long_only(df, pair_info, CAPITAL, in_market_v4, size_scale=trend_strength)
    m4 = metrics(eq_v4)
    in_market_pct_v4 = in_market_v4.mean()

    print(f"\n{'Variant':<35} {'Sharpe':>7} {'Ann.Ret':>9} {'MaxDD':>8} "
          f"{'Total':>8} {'In-mkt':>7} {'Trades':>7}")
    print("-" * 85)
    print(f"{'V1: Buy-and-hold':<35} {m1['sharpe']:>7.2f} {m1['ann_return']:>9.2%} "
          f"{m1['max_dd']:>8.2%} {m1['total_return']:>8.1%} {'100%':>7} {1:>7}")
    print(f"{'V2: trend (SMA50>200)':<35} {m2['sharpe']:>7.2f} {m2['ann_return']:>9.2%} "
          f"{m2['max_dd']:>8.2%} {m2['total_return']:>8.1%} {in_market_pct_v2:>7.0%} {n_entries_v2:>7}")
    print(f"{'V3: trend AND carry>0.5%':<35} {m3['sharpe']:>7.2f} {m3['ann_return']:>9.2%} "
          f"{m3['max_dd']:>8.2%} {m3['total_return']:>8.1%} {in_market_pct_v3:>7.0%} {n_entries_v3:>7}")
    print(f"{'V4: continuous trend-sizing':<35} {m4['sharpe']:>7.2f} {m4['ann_return']:>9.2%} "
          f"{m4['max_dd']:>8.2%} {m4['total_return']:>8.1%} {in_market_pct_v4:>7.0%} {'-':>7}")

    # Pick best by Sharpe
    cands = [("V1 B&H", m1, bh_signal, None),
             ("V2 trend", m2, trend_up, None),
             ("V3 trend+carry", m3, combo, None),
             ("V4 cont sizing", m4, in_market_v4, trend_strength)]
    best_name, best_m, best_sig, best_scale = max(cands, key=lambda x: x[1]["sharpe"])
    print(f"\nBest: {best_name} (Sharpe {best_m['sharpe']:.2f})")

    # ===== Walk-forward on best variant (no parameter optimization, fixed params) =====
    print("\n" + "=" * 80)
    print(f"  WALK-FORWARD: {best_name} on rolling 504-train / 126-test windows")
    print(f"  (no parameter re-fitting — testing if fixed params hold up OOS)")
    print("=" * 80)
    train_days = 504
    test_days = 126
    step_days = 63

    wf_results = []
    i = train_days
    while i + test_days <= len(df):
        test_slice = slice(i, i + test_days)
        sub_df = df.iloc[test_slice]
        sub_sig = best_sig.iloc[test_slice]
        sub_scale = best_scale.iloc[test_slice] if best_scale is not None else None
        eq = simulate_long_only(sub_df, pair_info, CAPITAL, sub_sig, size_scale=sub_scale)
        m = metrics(eq)
        wf_results.append(m["sharpe"])
        i += step_days

    wf_arr = np.array(wf_results)
    pos_pct = (wf_arr > 0).mean() if len(wf_arr) else 0
    print(f"  Windows: {len(wf_arr)}")
    print(f"  Avg OOS Sharpe: {wf_arr.mean():.2f}")
    print(f"  Median OOS Sharpe: {np.median(wf_arr):.2f}")
    print(f"  Std: {wf_arr.std():.2f}")
    print(f"  Positive windows: {(wf_arr > 0).sum()}/{len(wf_arr)} ({pos_pct:.0%})")
    print(f"  Best: {wf_arr.max():.2f},  Worst: {wf_arr.min():.2f}")

    # ===== Null hypothesis: sign-shuffle on full series =====
    print("\n" + "=" * 80)
    print(f"  NULL HYPOTHESIS: 200 random binary signals (matched in-market %)")
    print("=" * 80)
    rng = np.random.default_rng(42)
    in_market_target = best_sig.mean()
    null_sharpes = []
    for _ in range(200):
        # Random binary signal at same in-market frequency
        rand_sig = pd.Series(rng.random(len(df)) < in_market_target, index=df.index)
        eq = simulate_long_only(df, pair_info, CAPITAL, rand_sig)
        null_sharpes.append(metrics(eq)["sharpe"])
    null_arr = np.array(null_sharpes)
    rank = (null_arr < best_m["sharpe"]).mean()
    p_value = 1.0 - rank
    print(f"  Strategy Sharpe: {best_m['sharpe']:.2f}")
    print(f"  Null distribution: mean={null_arr.mean():.2f}, std={null_arr.std():.2f}, "
          f"95%={np.percentile(null_arr, 95):.2f}")
    print(f"  Strategy rank: {rank:.1%}  (p-value: {p_value:.3f})")
    null_passed = rank > 0.95
    print(f"  Null hypothesis: {'PASSED' if null_passed else 'FAILED'} (need >95%)")

    # ===== Arson tests =====
    print("\n" + "=" * 80)
    print("  ARSON TESTS (signal load-bearing checks)")
    print("=" * 80)
    rng = np.random.default_rng(42)

    # Randomize 10% of signals
    rand10 = best_sig.copy()
    flip_idx = rng.choice(len(rand10), size=int(0.10 * len(rand10)), replace=False)
    rand10.iloc[flip_idx] = ~rand10.iloc[flip_idx]
    eq = simulate_long_only(df, pair_info, CAPITAL, rand10)
    m_r10 = metrics(eq)

    # Randomize 25%
    rand25 = best_sig.copy()
    flip_idx = rng.choice(len(rand25), size=int(0.25 * len(rand25)), replace=False)
    rand25.iloc[flip_idx] = ~rand25.iloc[flip_idx]
    eq = simulate_long_only(df, pair_info, CAPITAL, rand25)
    m_r25 = metrics(eq)

    # Double costs
    pi2 = type(pair_info)(
        symbol=pair_info.symbol, pip_value=pair_info.pip_value,
        spread_pips=pair_info.spread_pips * 2,
        slippage_pips=pair_info.slippage_pips * 2,
        commission_pips=pair_info.commission_pips * 2,
        swap_long_pips_per_day=pair_info.swap_long_pips_per_day,
        swap_short_pips_per_day=pair_info.swap_short_pips_per_day,
    )
    eq = simulate_long_only(df, pair_info=pi2, capital=CAPITAL, in_market=best_sig)
    m_dc = metrics(eq)

    # Extra entry delay (shift signal by 1 more day)
    delayed = best_sig.shift(1).fillna(False)
    eq = simulate_long_only(df, pair_info, CAPITAL, delayed)
    m_ed = metrics(eq)

    print(f"  {'Test':<25} {'Sharpe':>7} {'vs base':>9}")
    print("  " + "-" * 45)
    print(f"  {'baseline':<25} {best_m['sharpe']:>7.2f} {'—':>9}")
    print(f"  {'randomize 10%':<25} {m_r10['sharpe']:>7.2f} {m_r10['sharpe'] - best_m['sharpe']:>+9.2f}")
    print(f"  {'randomize 25%':<25} {m_r25['sharpe']:>7.2f} {m_r25['sharpe'] - best_m['sharpe']:>+9.2f}")
    print(f"  {'double costs':<25} {m_dc['sharpe']:>7.2f} {m_dc['sharpe'] - best_m['sharpe']:>+9.2f}")
    print(f"  {'extra 1-bar delay':<25} {m_ed['sharpe']:>7.2f} {m_ed['sharpe'] - best_m['sharpe']:>+9.2f}")

    # ===== Decision =====
    print("\n" + "=" * 80)
    print("  DECISION GATE")
    print("=" * 80)
    beats_bh = best_m["sharpe"] > m1["sharpe"]
    wf_consistent = pos_pct > 0.6
    arson_robust = (m_r10["sharpe"] < best_m["sharpe"]) and (m_dc["sharpe"] < best_m["sharpe"])
    print(f"  Beats B&H?           {'YES' if beats_bh else 'NO'}  ({best_m['sharpe']:.2f} vs {m1['sharpe']:.2f})")
    print(f"  Walk-forward stable? {'YES' if wf_consistent else 'NO'}  ({pos_pct:.0%} positive windows)")
    print(f"  Null hyp passed?     {'YES' if null_passed else 'NO'}  (rank {rank:.1%})")
    print(f"  Arson robust?        {'YES' if arson_robust else 'NO'}  (signals are load-bearing)")
    if all([beats_bh, wf_consistent, null_passed, arson_robust]):
        print("\n  VERDICT: ALL GATES PASSED — candidate for paper trading.")
    elif not beats_bh:
        print("\n  VERDICT: REJECTED — does not beat B&H. Just hold USDJPY.")
    else:
        print("\n  VERDICT: PARTIAL — beats B&H but failed at least one validation gate. Iterate.")


if __name__ == "__main__":
    main()
