#!/usr/bin/env python3
"""Compute Sharpe + drawdown for buy-and-hold JPY portfolio with daily equity curves.

Each pair: long $1M nominal on day 1. Daily equity = entry_pnl + price_pnl_to_date
+ accumulated_swap_to_date. Spread cost charged on entry.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from forex_system.core.config import load_config
from forex_system.data.storage import load_parquet


def equity_curve(pair: str, capital: float, pair_info) -> pd.Series:
    df = load_parquet(pair, "daily", "data")
    pip_value = 0.01 if "JPY" in pair else 0.0001
    entry_price = df["close"].iloc[0]
    units = capital / entry_price

    # Entry + exit cost (one-time, charge upfront for simplicity)
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    one_time_cost = rt_cost_pips * pip_value * units

    # Price PnL each day (mark-to-market)
    price_pnl = (df["close"] - entry_price) / pip_value * pip_value * units

    # Swap income each day (accumulated)
    days_held = pd.Series(np.arange(len(df)), index=df.index)
    swap_pnl = pair_info.swap_long_pips_per_day * days_held * pip_value * units

    return capital + price_pnl + swap_pnl - one_time_cost


def sharpe_and_dd(equity: pd.Series) -> tuple[float, float, float, float]:
    daily_ret = equity.pct_change().dropna()
    sharpe = daily_ret.mean() / daily_ret.std() * np.sqrt(252) if daily_ret.std() > 0 else 0.0
    dd = (equity - equity.cummax()) / equity.cummax()
    max_dd = abs(dd.min())
    n_yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    total_ret = (equity.iloc[-1] / equity.iloc[0]) - 1.0
    ann_ret = (1 + total_ret) ** (1 / n_yrs) - 1
    return sharpe, max_dd, total_ret, ann_ret


def main():
    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_configs = {p.symbol: p.to_pair_info() for p in cfg.pairs}
    capital = 1_000_000.0
    pairs = ["USDJPY", "GBPJPY", "CADJPY"]

    print("=" * 76)
    print("  BUY-AND-HOLD SHARPE — JPY long, $1M each, real Saxo daily, 16.1 yrs")
    print("=" * 76)
    print(f"\n{'Pair':<10} {'Total Ret':>10} {'Ann.Ret':>10} {'Sharpe':>8} "
          f"{'MaxDD':>10} {'Return/DD':>10}")
    print("-" * 64)

    curves = {}
    for p in pairs:
        eq = equity_curve(p, capital, pair_configs[p])
        curves[p] = eq
        sh, dd, tr, ar = sharpe_and_dd(eq)
        ratio = (ar / dd) if dd > 0 else float("inf")
        print(f"{p:<10} {tr:>10.2%} {ar:>10.2%} {sh:>8.2f} {dd:>10.2%} {ratio:>10.2f}")

    # Portfolio: equal-weight, daily-rebalanced returns
    returns_df = pd.DataFrame({p: curves[p].pct_change() for p in pairs}).dropna()
    portfolio_ret = returns_df.mean(axis=1)  # equal-weighted daily return
    portfolio_eq = (1 + portfolio_ret).cumprod() * (capital * len(pairs))
    sh, dd, tr, ar = sharpe_and_dd(portfolio_eq)
    ratio = (ar / dd) if dd > 0 else float("inf")
    print("-" * 64)
    print(f"{'PORT EW':<10} {tr:>10.2%} {ar:>10.2%} {sh:>8.2f} {dd:>10.2%} {ratio:>10.2f}")

    # Correlations
    print("\nDaily-return correlations:")
    print(returns_df.corr().round(2).to_string())

    print("\n" + "=" * 76)
    print("  COMPARISON — the bar to beat")
    print("=" * 76)
    print(f"  Phase 1 carry-momentum (real data):    Sharpe  0.04, +0.15% total")
    print(f"  Buy-and-hold portfolio:                Sharpe  {sh:.2f}, {tr:+.1%} total")
    print(f"  Best single pair (USDJPY long):        Sharpe  {sharpe_and_dd(curves['USDJPY'])[0]:.2f}, "
          f"{sharpe_and_dd(curves['USDJPY'])[2]:+.1%} total")


if __name__ == "__main__":
    main()
