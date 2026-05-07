#!/usr/bin/env python3
"""Diagnose why carry-momentum returns ~0 on real Saxo USDJPY data.

Decompose:
  1. Time-in-market by direction (long days vs short days)
  2. Per-trade PnL distribution (winners vs losers)
  3. Cost breakdown (entry/exit cost vs swap income vs gross move)
  4. Signal-vs-future-return correlation
  5. Trade-direction vs subsequent N-day return alignment
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.core.config import load_config
from forex_system.costs.model import RealisticCostModel
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.sizing.continuous import ContinuousSizer
from forex_system.strategies.carry_momentum import CarryMomentumStrategy

PAIR = "USDJPY"
INITIAL = 1_000_000.0


def main():
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    rate_data = rate_data.rename(columns={c: c.replace("_diff", "") for c in rate_data.columns})

    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_configs = {p.symbol: p.to_pair_info() for p in cfg.pairs}
    pair_info = pair_configs[PAIR]
    cost = RealisticCostModel(pair_configs=pair_configs)
    sizer = ContinuousSizer(risk_per_trade=0.007, stop_loss_atr_multiple=2.0)

    ohlcv = load_parquet(PAIR, "daily", "data")
    e = compute_indicators(ohlcv, ["atr_14", "sma_20", "sma_50"]).dropna(subset=["atr_14", "sma_50"])
    strat = CarryMomentumStrategy(
        {"pair": PAIR, "fast_period": 20, "slow_period": 50, "agreement_only": True,
         "min_differential": 0.002, "max_differential": 0.05,
         "carry_weight": 0.4, "momentum_weight": 0.6},
        rate_data=rate_data,
    )
    sig = strat.generate_signals(e)

    # ---------- 1. Signal stats ----------
    print("=" * 70)
    print(f"  DIAGNOSIS: {PAIR} carry-momentum on REAL Saxo daily data")
    print(f"  Bars: {len(e)}  ({e.index[0].date()} → {e.index[-1].date()})")
    print("=" * 70)

    pos = np.sign(sig)
    print("\n1. Time-in-market by direction (raw signals):")
    print(f"   Long bars:  {(pos > 0).sum():>5}  ({(pos > 0).mean():>5.1%})")
    print(f"   Short bars: {(pos < 0).sum():>5}  ({(pos < 0).mean():>5.1%})")
    print(f"   Flat bars:  {(pos == 0).sum():>5}  ({(pos == 0).mean():>5.1%})")

    # ---------- 2. Buy-and-hold drift comparison ----------
    print("\n2. Buy-and-hold benchmark (no costs, no signals):")
    bh_ret = (e["close"].iloc[-1] / e["close"].iloc[0]) - 1.0
    n_yrs = (e.index[-1] - e.index[0]).days / 365.25
    print(f"   USDJPY price drift: {bh_ret:+.2%} over {n_yrs:.1f} years "
          f"({(1 + bh_ret) ** (1 / n_yrs) - 1:+.2%}/yr)")

    # ---------- 3. Realized return alignment ----------
    print("\n3. Signal-direction vs next-bar return alignment:")
    fwd_ret = e["close"].pct_change().shift(-1).fillna(0.0)
    sig_dir = pos.shift(1).fillna(0.0)  # entry-delay aligned
    when_long = fwd_ret[sig_dir > 0]
    when_short = fwd_ret[sig_dir < 0]
    print(f"   When LONG  ({len(when_long):>4} bars): mean fwd_ret = {when_long.mean() * 1e4:+.2f} bp,  "
          f"hit rate = {(when_long > 0).mean():.1%}")
    print(f"   When SHORT ({len(when_short):>4} bars): mean fwd_ret = {when_short.mean() * 1e4:+.2f} bp,  "
          f"hit rate = {(when_short < 0).mean():.1%}")
    print(f"   When FLAT  ({(sig_dir == 0).sum():>4} bars): mean fwd_ret = "
          f"{fwd_ret[sig_dir == 0].mean() * 1e4:+.2f} bp")

    # ---------- 4. Per-trade PnL ----------
    r = run_backtest(data=e, signals=sig, pair=PAIR, strategy_name="cm",
                     cost_model=cost, sizer=sizer, initial_capital=INITIAL)
    trades = pd.DataFrame([t.__dict__ for t in r.trade_log])
    print(f"\n4. Trade PnL distribution (n={len(trades)}):")
    print(f"   Mean PnL:     ${trades['pnl_dollars'].mean():>10,.2f}")
    print(f"   Median PnL:   ${trades['pnl_dollars'].median():>10,.2f}")
    print(f"   Best:         ${trades['pnl_dollars'].max():>10,.2f}")
    print(f"   Worst:        ${trades['pnl_dollars'].min():>10,.2f}")
    print(f"   Total:        ${trades['pnl_dollars'].sum():>10,.2f}  "
          f"= {trades['pnl_dollars'].sum() / INITIAL:+.2%} on $1M")
    print(f"   Win rate:     {(trades['pnl_dollars'] > 0).mean():.1%}")
    long_trades = trades[trades["direction"] == 1]
    short_trades = trades[trades["direction"] == -1]
    print(f"   LONG trades:  {len(long_trades)}  total ${long_trades['pnl_dollars'].sum():>10,.2f}  "
          f"win {(long_trades['pnl_dollars'] > 0).mean():.1%}")
    print(f"   SHORT trades: {len(short_trades)} total ${short_trades['pnl_dollars'].sum():>10,.2f}  "
          f"win {(short_trades['pnl_dollars'] > 0).mean():.1%}")

    # ---------- 5. Cost decomposition ----------
    print("\n5. Cost breakdown per trade (estimated):")
    avg_size = trades.iloc[0:5]["pnl_dollars"].abs().mean() if len(trades) > 0 else 1000
    rt_pips = pair_info.spread_pips + 2 * pair_info.slippage_pips + pair_info.commission_pips
    print(f"   Round-trip cost: {rt_pips:.1f} pips/trade × {len(trades)} trades = {rt_pips * len(trades):.0f} pips total")
    swap_long = pair_info.swap_long_pips_per_day
    swap_short = pair_info.swap_short_pips_per_day
    print(f"   Swap/day: long={swap_long:+.2f} pips,  short={swap_short:+.2f} pips")
    long_days = (sig_dir > 0).sum()
    short_days = (sig_dir < 0).sum()
    swap_income = swap_long * long_days + swap_short * short_days
    print(f"   Swap income est: long_days={long_days}*{swap_long:+.2f} + short_days={short_days}*{swap_short:+.2f}")
    print(f"                   = {swap_income:+.0f} pips total over period")

    # ---------- 6. Carry vs momentum component breakdown ----------
    print("\n6. Carry component alone vs momentum alone:")
    carry_only = strat._carry_signal(e)
    mom_only = strat._momentum_signal(e)
    print(f"   Carry signal:    nonzero={((carry_only.abs() > 1e-6).sum()):>5}, "
          f"mean dir={np.sign(carry_only).mean():+.2f}, range=[{carry_only.min():+.2f}, {carry_only.max():+.2f}]")
    print(f"   Momentum signal: nonzero={((mom_only.abs() > 1e-6).sum()):>5}, "
          f"mean dir={np.sign(mom_only).mean():+.2f}, range=[{mom_only.min():+.2f}, {mom_only.max():+.2f}]")
    agree = (np.sign(carry_only) == np.sign(mom_only)) & (np.sign(carry_only) != 0)
    print(f"   Agreement bars:  {agree.sum()}/{len(e)} ({agree.mean():.1%})")
    print(f"   When carry>0 AND mom>0: {((carry_only > 0) & (mom_only > 0)).sum()} bars (long)")
    print(f"   When carry<0 AND mom<0: {((carry_only < 0) & (mom_only < 0)).sum()} bars (short)")

    # ---------- 7. What if just buy-and-hold long-carry-only? ----------
    print("\n7. What if we just stayed LONG when carry > min_diff (no momentum filter)?")
    pure_carry_long = (carry_only > 0).astype(float)  # +1 long when positive carry, 0 otherwise
    r2 = run_backtest(data=e, signals=pure_carry_long, pair=PAIR, strategy_name="ph",
                      cost_model=cost, sizer=sizer, initial_capital=INITIAL)
    eq = r2.equity_curve
    final_ret = (eq.iloc[-1] / eq.iloc[0]) - 1.0
    print(f"   Total return: {final_ret:+.2%}  ({(1 + final_ret) ** (1 / n_yrs) - 1:+.2%}/yr)")
    print(f"   Trades: {len(r2.trade_log)} (mostly entry, then ride forever)")


if __name__ == "__main__":
    main()
