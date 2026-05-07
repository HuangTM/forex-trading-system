#!/usr/bin/env python3
"""Volatility-targeted USDJPY long — does scaling size by realized vol beat B&H?

Theory: keep daily-return std constant by sizing inversely to realized vol.
Calm markets → bigger size. Choppy markets → smaller size. Should reduce
MaxDD without proportionally hurting Sharpe (no timing, just sizing).

Tests:
  - Vol window: 20, 60, 252 days
  - Leverage cap: 1.0x, 2.0x (no shorts, capped upside)
  - Target vol: 10% annualized (typical for retail FX)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from forex_system.core.config import load_config
from forex_system.data.storage import load_parquet

PAIR = "USDJPY"
CAPITAL = 1_000_000.0
TARGET_VOL_ANNUAL = 0.10
REBALANCE_THRESHOLD = 0.20  # only adjust size if target differs by >20%


def simulate_voltarget(
    df: pd.DataFrame,
    pair_info,
    capital: float,
    realized_vol: pd.Series,    # annualized daily vol
    target_vol: float,
    leverage_cap: float,
    rebal_threshold: float = REBALANCE_THRESHOLD,
) -> tuple[pd.Series, int]:
    """Long-only USDJPY with vol-targeted sizing. Returns (equity_curve, n_rebalances)."""
    pip = 0.01 if "JPY" in PAIR else 0.0001
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    half_spread_pips = rt_cost_pips / 2
    swap_per_day_pips = pair_info.swap_long_pips_per_day
    daily_swap_per_unit = swap_per_day_pips * pip

    # Position scale: target_vol / realized_vol, capped
    raw_scale = target_vol / realized_vol.replace(0, np.nan)
    scale = raw_scale.clip(0, leverage_cap).fillna(0.0)

    equity = pd.Series(capital, index=df.index, dtype=float)
    cur_units = 0.0
    n_rebalances = 0

    # Initial entry once realized_vol is valid
    first_valid = realized_vol.first_valid_index()
    if first_valid is None:
        return equity, 0
    start_idx = df.index.get_loc(first_valid)

    for i in range(1, len(df)):
        ts = df.index[i]
        prev_close = df["close"].iloc[i - 1]
        cur_close = df["close"].iloc[i]
        equity.iloc[i] = equity.iloc[i - 1]

        if cur_units > 0:
            equity.iloc[i] += (cur_close - prev_close) * cur_units
            equity.iloc[i] += daily_swap_per_unit * cur_units

        if i < start_idx:
            continue

        target_scale = float(scale.iloc[i])
        target_units = (capital / cur_close) * target_scale

        if cur_units == 0 and target_scale > 0:
            cur_units = target_units
            equity.iloc[i] -= rt_cost_pips * pip * cur_units
            n_rebalances += 1
        elif cur_units > 0 and target_scale == 0:
            cur_units = 0.0  # exit cost already accounted for at entry
        elif cur_units > 0 and target_units > 0:
            delta = abs(target_units - cur_units)
            if cur_units > 0 and (delta / cur_units) > rebal_threshold:
                rebal_cost = half_spread_pips * pip * delta
                equity.iloc[i] -= rebal_cost
                cur_units = target_units
                n_rebalances += 1

    return equity, n_rebalances


def metrics(equity: pd.Series) -> dict:
    daily = equity.pct_change().dropna()
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0.0
    dd = (equity - equity.cummax()) / equity.cummax()
    n_yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    total = (equity.iloc[-1] / equity.iloc[0]) - 1.0
    ann = (1 + total) ** (1 / n_yrs) - 1
    realized_vol = daily.std() * np.sqrt(252)
    return dict(sharpe=sharpe, max_dd=abs(dd.min()), total_return=total,
                ann_return=ann, realized_vol=realized_vol)


def b_and_h(df, pair_info, capital):
    pip = 0.01 if "JPY" in PAIR else 0.0001
    entry = df["close"].iloc[0]
    units = capital / entry
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    one_time = rt_cost_pips * pip * units
    price_pnl = (df["close"] - entry) / pip * pip * units
    days_held = pd.Series(np.arange(len(df)), index=df.index)
    swap_pnl = pair_info.swap_long_pips_per_day * days_held * pip * units
    return capital + price_pnl + swap_pnl - one_time


def main():
    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_info = {p.symbol: p.to_pair_info() for p in cfg.pairs}[PAIR]

    df = load_parquet(PAIR, "daily", "data")
    rets = df["close"].pct_change()

    print("=" * 86)
    print(f"  Volatility-targeted long USDJPY — target vol = {TARGET_VOL_ANNUAL:.0%}/yr, $1M, "
          f"{df.index[0].date()} → {df.index[-1].date()}")
    print(f"  Bar to beat: B&H Sharpe 0.71, MaxDD 14.2%")
    print("=" * 86)

    # Baseline B&H
    eq_bh = b_and_h(df, pair_info, CAPITAL)
    m_bh = metrics(eq_bh)

    print(f"\n{'Variant':<32} {'Sharpe':>7} {'Ann.Ret':>9} {'MaxDD':>8} "
          f"{'Realized vol':>12} {'Rebal':>7} {'Total':>8}")
    print("-" * 92)
    print(f"{'B&H baseline (no targeting)':<32} {m_bh['sharpe']:>7.2f} "
          f"{m_bh['ann_return']:>9.2%} {m_bh['max_dd']:>8.2%} "
          f"{m_bh['realized_vol']:>11.2%} {1:>7} {m_bh['total_return']:>8.1%}")

    rows = []
    for vol_window in [20, 60, 252]:
        realized = rets.rolling(vol_window).std() * np.sqrt(252)
        for cap in [1.0, 2.0]:
            eq, n_rebal = simulate_voltarget(
                df, pair_info, CAPITAL, realized, TARGET_VOL_ANNUAL, cap,
            )
            m = metrics(eq)
            label = f"vol{vol_window}d / cap{cap:.1f}x"
            rows.append((label, m, n_rebal))
            print(f"{label:<32} {m['sharpe']:>7.2f} {m['ann_return']:>9.2%} "
                  f"{m['max_dd']:>8.2%} {m['realized_vol']:>11.2%} "
                  f"{n_rebal:>7} {m['total_return']:>8.1%}")

    # Best by Sharpe
    best_label, best_m, best_rebal = max(rows, key=lambda r: r[1]["sharpe"])
    print(f"\nBest variant: {best_label}  (Sharpe {best_m['sharpe']:.2f})")
    print(f"  vs B&H Sharpe {m_bh['sharpe']:.2f}: "
          f"{'BEAT' if best_m['sharpe'] > m_bh['sharpe'] else 'TIE/LOSE'}")
    print(f"  vs B&H MaxDD {m_bh['max_dd']:.1%}: "
          f"{best_m['max_dd']:.1%} ({(best_m['max_dd'] - m_bh['max_dd']) * 100:+.1f}pp)")
    print(f"  vs B&H realized vol {m_bh['realized_vol']:.1%}: "
          f"{best_m['realized_vol']:.1%} ({(best_m['realized_vol'] - m_bh['realized_vol']) * 100:+.1f}pp)")

    # Return / MaxDD ratio comparison
    print(f"\nReturn-on-drawdown (calmar-ish):")
    for label, m, n in [("B&H", m_bh, 1)] + rows:
        rr = (m["ann_return"] / m["max_dd"]) if m["max_dd"] > 0 else float("inf")
        print(f"  {label:<32} ann_ret/maxdd = {rr:.2f}")

    # ===== Validate the winner =====
    # Use vol252d / cap2.0x (winner)
    realized_252 = rets.rolling(252).std() * np.sqrt(252)

    # Walk-forward: test stability across non-overlapping 2-year periods
    print("\n" + "=" * 86)
    print("  WALK-FORWARD: vol252d/cap2.0x on rolling 2-year out-of-sample windows")
    print("=" * 86)
    test_days = 252 * 2
    step_days = 252
    start = 252 + 100  # need rolling vol to warm up
    wf = []
    while start + test_days <= len(df):
        sub_df = df.iloc[start:start + test_days]
        sub_vol = realized_252.iloc[start:start + test_days]
        eq, n = simulate_voltarget(sub_df, pair_info, CAPITAL, sub_vol, TARGET_VOL_ANNUAL, 2.0)
        # Compare to B&H over same window
        eq_bh_w = b_and_h(sub_df, pair_info, CAPITAL)
        m_w = metrics(eq)
        m_bh_w = metrics(eq_bh_w)
        wf.append((sub_df.index[0].date(), sub_df.index[-1].date(),
                   m_w["sharpe"], m_bh_w["sharpe"], m_w["sharpe"] - m_bh_w["sharpe"]))
        start += step_days

    print(f"\n  {'Window':<25} {'VT Sharpe':>10} {'B&H Sharpe':>11} {'Delta':>8}")
    print("  " + "-" * 56)
    for d1, d2, s_vt, s_bh, delta in wf:
        winner = "VT" if delta > 0 else "B&H"
        print(f"  {str(d1) + ' → ' + str(d2):<25} {s_vt:>10.2f} {s_bh:>11.2f} {delta:>+8.2f} {winner}")

    vt_wins = sum(1 for _, _, _, _, d in wf if d > 0)
    print(f"\n  Vol-targeting beats B&H in {vt_wins}/{len(wf)} OOS windows ({vt_wins / len(wf):.0%})")
    avg_delta = np.mean([d for _, _, _, _, d in wf])
    print(f"  Avg Sharpe delta: {avg_delta:+.2f}")

    # Null hypothesis: shuffle the vol signal — does sizing-by-noise also beat B&H?
    print("\n" + "=" * 86)
    print("  NULL HYPOTHESIS: 200 shuffled vol series — is real vol load-bearing?")
    print("=" * 86)
    rng = np.random.default_rng(42)
    eq_real, _ = simulate_voltarget(df, pair_info, CAPITAL, realized_252, TARGET_VOL_ANNUAL, 2.0)
    real_sharpe = metrics(eq_real)["sharpe"]

    null_sharpes = []
    for _ in range(200):
        # Shuffle the realized-vol values keeping NaN positions fixed
        valid = realized_252.dropna()
        shuffled_values = rng.permutation(valid.values)
        shuffled = pd.Series(np.nan, index=realized_252.index)
        shuffled.loc[valid.index] = shuffled_values
        eq, _ = simulate_voltarget(df, pair_info, CAPITAL, shuffled, TARGET_VOL_ANNUAL, 2.0)
        null_sharpes.append(metrics(eq)["sharpe"])
    null_arr = np.array(null_sharpes)
    rank = (null_arr < real_sharpe).mean()
    print(f"  Real vol-target Sharpe: {real_sharpe:.2f}")
    print(f"  Shuffled vol distribution: mean={null_arr.mean():.2f}, "
          f"std={null_arr.std():.2f}, 95th={np.percentile(null_arr, 95):.2f}")
    print(f"  Strategy rank: {rank:.1%}  (p-value {1 - rank:.3f})")
    print(f"  Verdict: {'PASSED — vol signal IS load-bearing' if rank > 0.95 else 'FAILED — random vol works as well'}")

    # Arson: stress-test costs and delays
    print("\n" + "=" * 86)
    print("  ARSON TESTS")
    print("=" * 86)
    pi2 = type(pair_info)(
        symbol=pair_info.symbol, pip_value=pair_info.pip_value,
        spread_pips=pair_info.spread_pips * 2,
        slippage_pips=pair_info.slippage_pips * 2,
        commission_pips=pair_info.commission_pips * 2,
        swap_long_pips_per_day=pair_info.swap_long_pips_per_day,
        swap_short_pips_per_day=pair_info.swap_short_pips_per_day,
    )
    eq_dc, _ = simulate_voltarget(df, pi2, CAPITAL, realized_252, TARGET_VOL_ANNUAL, 2.0)
    eq_d1, _ = simulate_voltarget(df, pair_info, CAPITAL, realized_252.shift(1), TARGET_VOL_ANNUAL, 2.0)
    eq_d5, _ = simulate_voltarget(df, pair_info, CAPITAL, realized_252.shift(5), TARGET_VOL_ANNUAL, 2.0)
    print(f"  {'Test':<25} {'Sharpe':>7} {'vs base':>9}")
    print("  " + "-" * 45)
    print(f"  {'baseline':<25} {real_sharpe:>7.2f} {'—':>9}")
    print(f"  {'double costs':<25} {metrics(eq_dc)['sharpe']:>7.2f} "
          f"{metrics(eq_dc)['sharpe'] - real_sharpe:>+9.2f}")
    print(f"  {'1-day delay on vol':<25} {metrics(eq_d1)['sharpe']:>7.2f} "
          f"{metrics(eq_d1)['sharpe'] - real_sharpe:>+9.2f}")
    print(f"  {'5-day delay on vol':<25} {metrics(eq_d5)['sharpe']:>7.2f} "
          f"{metrics(eq_d5)['sharpe'] - real_sharpe:>+9.2f}")


if __name__ == "__main__":
    main()
