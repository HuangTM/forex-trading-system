#!/usr/bin/env python3
"""Simplest possible carry baseline: buy USDJPY on day 1, hold for 16 years.

Net of:
  - Spread + slippage on entry/exit (0.5 + 0.5 = 1.0 pip × 2 = 2.0 pips)
  - Daily swap income for being long USDJPY (positive carry)
  - No commission (assume zero for buy-and-hold)

If THIS doesn't make money, retail FX carry isn't an edge.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from forex_system.core.config import load_config
from forex_system.data.storage import load_parquet


def buy_and_hold(pair: str, capital: float, pair_info) -> dict:
    df = load_parquet(pair, "daily", "data")
    entry_price = df["close"].iloc[0]
    exit_price = df["close"].iloc[-1]
    n_days = len(df)
    n_years = (df.index[-1] - df.index[0]).days / 365.25

    # Position sizing: use ~3x ATR risk on $1M (matches Phase 1 scale)
    # Just for "what if we put all of $1M into USDJPY"
    pip_value = 0.01 if "JPY" in pair else 0.0001
    units = capital / entry_price  # 1M USD worth of base currency

    # Price PnL
    price_change_pips = (exit_price - entry_price) / pip_value
    price_pnl_dollars = price_change_pips * pip_value * units

    # Spread/slippage cost (entry + exit)
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    cost_dollars = rt_cost_pips * pip_value * units

    # Swap income (long → long swap rate)
    swap_per_day_pips = pair_info.swap_long_pips_per_day
    swap_pips_total = swap_per_day_pips * n_days
    swap_dollars = swap_pips_total * pip_value * units

    net_pnl = price_pnl_dollars - cost_dollars + swap_dollars
    final_equity = capital + net_pnl

    return {
        "pair": pair,
        "n_years": n_years,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "price_pnl": price_pnl_dollars,
        "cost": cost_dollars,
        "swap_income": swap_dollars,
        "net_pnl": net_pnl,
        "total_return": net_pnl / capital,
        "annual_return": (1 + net_pnl / capital) ** (1 / n_years) - 1,
        "swap_per_day_pips": swap_per_day_pips,
    }


def main():
    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_configs = {p.symbol: p.to_pair_info() for p in cfg.pairs}
    capital = 1_000_000.0

    print("=" * 76)
    print("  BUY-AND-HOLD BASELINE — JPY crosses, $1M each, 16.1 years")
    print(f"  Question: Does retail carry yield positive after costs?")
    print("=" * 76)
    print(f"\n{'Pair':<8} {'Price PnL':>14} {'Spread Cost':>13} "
          f"{'Swap Income':>13} {'Net PnL':>14} {'Total Ret':>10} {'Ann.Ret':>10}")
    print("-" * 86)

    rows = []
    for p in ["USDJPY", "GBPJPY", "CADJPY"]:
        r = buy_and_hold(p, capital, pair_configs[p])
        rows.append(r)
        print(f"{p:<8} ${r['price_pnl']:>12,.0f} ${r['cost']:>11,.0f} "
              f"${r['swap_income']:>11,.0f} ${r['net_pnl']:>12,.0f} "
              f"{r['total_return']:>9.1%} {r['annual_return']:>9.2%}")

    # Equal-weighted portfolio
    total_net = sum(r["net_pnl"] for r in rows)
    total_capital = capital * len(rows)
    port_return = total_net / total_capital
    port_ann = (1 + port_return) ** (1 / rows[0]["n_years"]) - 1
    print("-" * 86)
    print(f"{'PORT':<8} {'-':>14} {'-':>13} {'-':>13} ${total_net:>12,.0f} "
          f"{port_return:>9.1%} {port_ann:>9.2%}")

    print(f"\nNotes:")
    print(f"  - Costs: spread + 2*slippage + commission, charged once on entry+exit")
    print(f"  - Swap: pair_info.swap_long_pips_per_day * n_calendar_days")
    print(f"  - No leverage, no rebalancing, no stop-out")
    print(f"  - 'Annual return' is CAGR over {rows[0]['n_years']:.1f} years")

    print("\n" + "=" * 76)
    print("  COMPARE vs Phase 1 carry-momentum strategy:")
    print("=" * 76)
    print(f"  Phase 1 portfolio (real data):     +0.15% total, Sharpe 0.04")
    print(f"  Buy-and-hold portfolio:            {port_return:+.1%} total, Sharpe (not computed here)")
    print()
    print(f"  Best individual carry pair:        {max(rows, key=lambda r: r['total_return'])['pair']} = "
          f"{max(rows, key=lambda r: r['total_return'])['total_return']:+.1%}")


if __name__ == "__main__":
    main()
