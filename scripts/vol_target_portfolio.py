#!/usr/bin/env python3
"""Test vol-targeted long carry on JPY portfolio (USDJPY/GBPJPY/CADJPY).

Per-pair vol targeting + equal weighting. Compare to:
  - B&H portfolio (Sharpe 0.39, MaxDD 23.9% from prior test)
  - B&H USDJPY only (Sharpe 0.58)
  - VT USDJPY only (Sharpe 0.76, MaxDD 13.5%)

Question: does the vol-targeting benefit survive the 0.7+ correlation drag?
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
from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy

PAIRS = ["USDJPY", "GBPJPY", "CADJPY"]
CAPITAL = 1_000_000.0
TARGET_VOL = 0.10
LEVERAGE_CAP = 2.0


def simulate_pair(pair: str, df: pd.DataFrame, pair_info, capital: float,
                  target_vol: float, leverage_cap: float) -> tuple[pd.Series, int]:
    """Daily mark-to-market vol-targeted long-only carry."""
    pip = 0.01 if "JPY" in pair else 0.0001
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    half_spread = rt_cost_pips / 2
    swap_per_day_pips = pair_info.swap_long_pips_per_day
    daily_swap_per_unit = swap_per_day_pips * pip

    strat = VolTargetCarryStrategy(
        {"pair": pair, "target_vol": target_vol,
         "vol_window": 252, "leverage_cap": leverage_cap},
    )
    signals = strat.generate_signals(df)  # in [0, 1]

    equity = pd.Series(capital, index=df.index, dtype=float)
    cur_units = 0.0
    n_rebalances = 0
    rebal_threshold = 0.20

    for i in range(1, len(df)):
        prev_close = df["close"].iloc[i - 1]
        cur_close = df["close"].iloc[i]
        equity.iloc[i] = equity.iloc[i - 1]
        if cur_units > 0:
            equity.iloc[i] += (cur_close - prev_close) * cur_units
            equity.iloc[i] += daily_swap_per_unit * cur_units

        sig = float(signals.iloc[i])
        target_units = sig * leverage_cap * (capital / cur_close)
        if cur_units == 0 and target_units > 0:
            cur_units = target_units
            equity.iloc[i] -= rt_cost_pips * pip * cur_units
            n_rebalances += 1
        elif cur_units > 0 and target_units == 0:
            cur_units = 0.0
        elif cur_units > 0 and target_units > 0:
            delta = abs(target_units - cur_units)
            if (delta / cur_units) > rebal_threshold:
                equity.iloc[i] -= half_spread * pip * delta
                cur_units = target_units
                n_rebalances += 1
    return equity, n_rebalances


def b_and_h(pair: str, df: pd.DataFrame, pair_info, capital: float) -> pd.Series:
    pip = 0.01 if "JPY" in pair else 0.0001
    entry = df["close"].iloc[0]
    units = capital / entry
    rt_cost_pips = (pair_info.spread_pips + 2 * pair_info.slippage_pips
                    + pair_info.commission_pips)
    one_time = rt_cost_pips * pip * units
    price_pnl = (df["close"] - entry) / pip * pip * units
    days = pd.Series(np.arange(len(df)), index=df.index)
    swap_pnl = pair_info.swap_long_pips_per_day * days * pip * units
    return capital + price_pnl + swap_pnl - one_time


def metrics(equity: pd.Series) -> dict:
    daily = equity.pct_change().dropna()
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0.0
    dd = (equity - equity.cummax()) / equity.cummax()
    n_yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    total = (equity.iloc[-1] / equity.iloc[0]) - 1.0
    ann = (1 + total) ** (1 / n_yrs) - 1
    rv = daily.std() * np.sqrt(252)
    return dict(sharpe=sharpe, max_dd=abs(dd.min()), total=total, ann=ann, vol=rv)


def main():
    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_info = {p.symbol: p.to_pair_info() for p in cfg.pairs}

    print("=" * 88)
    print(f"  Vol-target carry portfolio — {', '.join(PAIRS)}, $1M each")
    print(f"  target_vol={TARGET_VOL:.0%}/yr, leverage_cap={LEVERAGE_CAP}x, vol_window=252d")
    print("=" * 88)
    print(f"\n{'Pair':<10} {'Strategy':<8} {'Sharpe':>7} {'Ann.Ret':>9} "
          f"{'MaxDD':>8} {'Vol':>7} {'Trades':>7} {'Total':>8}")
    print("-" * 80)

    bh_curves, vt_curves = {}, {}
    for p in PAIRS:
        df = load_parquet(p, "daily", "data")
        df = compute_indicators(df, ["atr_14"]).dropna(subset=["atr_14"])
        eq_bh = b_and_h(p, df, pair_info[p], CAPITAL)
        eq_vt, n = simulate_pair(p, df, pair_info[p], CAPITAL, TARGET_VOL, LEVERAGE_CAP)
        bh_curves[p] = eq_bh
        vt_curves[p] = eq_vt
        m_bh = metrics(eq_bh)
        m_vt = metrics(eq_vt)
        print(f"{p:<10} {'B&H':<8} {m_bh['sharpe']:>7.2f} {m_bh['ann']:>9.2%} "
              f"{m_bh['max_dd']:>8.2%} {m_bh['vol']:>6.1%} {1:>7} {m_bh['total']:>8.1%}")
        print(f"{'':<10} {'VT':<8} {m_vt['sharpe']:>7.2f} {m_vt['ann']:>9.2%} "
              f"{m_vt['max_dd']:>8.2%} {m_vt['vol']:>6.1%} {n:>7} {m_vt['total']:>8.1%}")

    # Equal-weighted portfolios
    def portfolio(curves):
        rdf = pd.DataFrame({p: c.pct_change() for p, c in curves.items()}).dropna()
        port_ret = rdf.mean(axis=1)
        eq = (1 + port_ret).cumprod() * (CAPITAL * len(curves))
        return eq

    pe_bh = portfolio(bh_curves)
    pe_vt = portfolio(vt_curves)
    m_pbh = metrics(pe_bh)
    m_pvt = metrics(pe_vt)
    print("-" * 80)
    print(f"{'PORTFOLIO':<10} {'B&H':<8} {m_pbh['sharpe']:>7.2f} {m_pbh['ann']:>9.2%} "
          f"{m_pbh['max_dd']:>8.2%} {m_pbh['vol']:>6.1%} {'-':>7} {m_pbh['total']:>8.1%}")
    print(f"{'':<10} {'VT':<8} {m_pvt['sharpe']:>7.2f} {m_pvt['ann']:>9.2%} "
          f"{m_pvt['max_dd']:>8.2%} {m_pvt['vol']:>6.1%} {'-':>7} {m_pvt['total']:>8.1%}")

    print("\n" + "=" * 88)
    print(f"  PORTFOLIO COMPARISON")
    print("=" * 88)
    delta_sh = m_pvt["sharpe"] - m_pbh["sharpe"]
    delta_dd = m_pvt["max_dd"] - m_pbh["max_dd"]
    print(f"  B&H portfolio: Sharpe {m_pbh['sharpe']:.2f}, MaxDD {m_pbh['max_dd']:.1%}")
    print(f"  VT portfolio:  Sharpe {m_pvt['sharpe']:.2f}, MaxDD {m_pvt['max_dd']:.1%}")
    print(f"  Delta:         {delta_sh:+.2f} Sharpe, {delta_dd * 100:+.1f}pp MaxDD")
    print(f"  vs single-pair USDJPY VT (0.76 Sharpe, 13.5% MaxDD): "
          f"{'PORTFOLIO BETTER' if m_pvt['sharpe'] > 0.76 else 'USDJPY ALONE BETTER'}")

    # Correlation comparison
    bh_rets = pd.DataFrame({p: bh_curves[p].pct_change() for p in PAIRS}).dropna()
    vt_rets = pd.DataFrame({p: vt_curves[p].pct_change() for p in PAIRS}).dropna()
    print(f"\nDaily-return correlations:")
    print(f"  B&H:")
    print(bh_rets.corr().round(2).to_string().replace("\n", "\n    ").replace("    ", "    ", 1))
    print(f"  VT:")
    print(vt_rets.corr().round(2).to_string().replace("\n", "\n    ").replace("    ", "    ", 1))


if __name__ == "__main__":
    main()
