#!/usr/bin/env python3
"""Re-run Phase 1 carry-momentum portfolio on REAL Saxo data.

Phase 1 config (config/carry_momentum_portfolio.yaml) claims Sharpe 0.59 on
USDJPY/GBPJPY/CADJPY. Original `data/processed/*_daily.parquet` was synthetic
GBM data (USDJPY values ~6.47 vs real ~159). This script re-runs the same
strategy on freshly downloaded real Saxo daily data.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from forex_system.analysis.arson_test import BacktestArsonTest
from forex_system.analysis.null_hypothesis import NullHypothesisGate
from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.backtest.walkforward import run_walkforward
from forex_system.core.config import load_config
from forex_system.costs.model import RealisticCostModel
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.sizing.continuous import ContinuousSizer
from forex_system.strategies.carry_momentum import CarryMomentumStrategy

PAIRS = ["USDJPY", "GBPJPY", "CADJPY"]

# Phase 1 validated params from config/carry_momentum_portfolio.yaml
STRATEGY_PARAMS = {
    "fast_period": 20,
    "slow_period": 50,
    "agreement_only": True,
    "min_differential": 0.002,
    "max_differential": 0.05,
    "carry_weight": 0.4,
    "momentum_weight": 0.6,
}
RISK_PER_TRADE = 0.007
STOP_ATR = 2.0


def run_pair(pair, rate_data, sizer, cost_model):
    ohlcv = load_parquet(pair, "daily", "data")
    enriched = compute_indicators(ohlcv, ["atr_14", "sma_20", "sma_50"])
    enriched = enriched.dropna(subset=["atr_14", "sma_50"])

    strategy = CarryMomentumStrategy({**STRATEGY_PARAMS, "pair": pair}, rate_data=rate_data)
    signals = strategy.generate_signals(enriched)
    result = run_backtest(
        data=enriched, signals=signals, pair=pair,
        strategy_name="carry_momentum", cost_model=cost_model, sizer=sizer,
        initial_capital=INITIAL_PER_PAIR,
    )
    metrics = calculate_metrics(result.equity_curve, result.trade_log)
    return enriched, signals, result, metrics, strategy


INITIAL_PER_PAIR = 1_000_000.0  # Match live Saxo SIM equity scale


def portfolio_metrics(results):
    initial_per_pair = INITIAL_PER_PAIR
    n_pairs = len(results)
    all_returns = {}
    for pair, (_, _, result, _, _) in results.items():
        ec = result.equity_curve.dropna()
        if len(ec) > 1:
            all_returns[pair] = ec.pct_change().fillna(0.0)
    returns_df = pd.DataFrame(all_returns).fillna(0.0)
    portfolio_returns = returns_df.mean(axis=1)
    portfolio_equity = (1 + portfolio_returns).cumprod() * (initial_per_pair * n_pairs)
    total_return = (portfolio_equity.iloc[-1] / portfolio_equity.iloc[0]) - 1.0
    n_years = (portfolio_equity.index[-1] - portfolio_equity.index[0]).days / 365.25
    ann_return = (1 + total_return) ** (1.0 / max(n_years, 0.001)) - 1.0
    daily = portfolio_equity.pct_change().dropna()
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0.0
    drawdown = (portfolio_equity - portfolio_equity.cummax()) / portfolio_equity.cummax()
    return {
        "period": (portfolio_equity.index[0].date(), portfolio_equity.index[-1].date()),
        "n_years": n_years,
        "total_return": total_return,
        "ann_return": ann_return,
        "sharpe": sharpe,
        "max_dd": abs(drawdown.min()),
        "equity": portfolio_equity,
    }


def main():
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    rate_data = rate_data.rename(columns={c: c.replace("_diff", "") for c in rate_data.columns})

    cfg = load_config("config/carry_momentum_portfolio.yaml")
    pair_configs = {p.symbol: p.to_pair_info() for p in cfg.pairs}
    cost_model = RealisticCostModel(pair_configs=pair_configs)
    sizer = ContinuousSizer(risk_per_trade=RISK_PER_TRADE, stop_loss_atr_multiple=STOP_ATR)

    print("=" * 72)
    print("  PHASE 1 RE-VALIDATION ON REAL SAXO DATA")
    print(f"  Pairs: {', '.join(PAIRS)} | Strategy: CarryMomentum 20/50 agree")
    print(f"  Risk/trade: {RISK_PER_TRADE:.1%} | ATR stop: {STOP_ATR}x")
    print("=" * 72)

    print(f"\n{'Pair':<10} {'Bars':>6} {'Return':>10} {'Ann.Ret':>10} {'Sharpe':>8} "
          f"{'MaxDD':>8} {'Trades':>7} {'WinRate':>8}")
    print("-" * 72)

    results = {}
    for pair in PAIRS:
        e, s, r, m, strat = run_pair(pair, rate_data, sizer, cost_model)
        results[pair] = (e, s, r, m, strat)
        print(f"{pair:<10} {len(e):>6} {m.total_return:>10.2%} {m.annualized_return:>10.2%} "
              f"{m.sharpe_ratio:>8.2f} {m.max_drawdown:>8.2%} "
              f"{m.num_trades:>7d} {m.win_rate:>8.1%}")

    print("\n" + "=" * 72)
    print("  EQUAL-WEIGHTED PORTFOLIO")
    print("=" * 72)
    pm = portfolio_metrics(results)
    print(f"  Period:         {pm['period'][0]} → {pm['period'][1]}  ({pm['n_years']:.1f} yrs)")
    print(f"  Total Return:   {pm['total_return']:>10.2%}")
    print(f"  Annual Return:  {pm['ann_return']:>10.2%}")
    print(f"  Sharpe:         {pm['sharpe']:>10.2f}   (Phase 1 claim: 0.59)")
    print(f"  Max Drawdown:   {pm['max_dd']:>10.2%}")

    print("\n" + "=" * 72)
    print("  WALK-FORWARD (504 train / 126 test / 63 step)")
    print("=" * 72)
    print(f"  {'Pair':<10} {'Windows':>8} {'Avg SR':>8} {'Consistent':>12} {'OOS Trades':>11}")
    print("  " + "-" * 54)
    for pair in PAIRS:
        e, _, _, _, strat = results[pair]
        wf = run_walkforward(
            data=e, strategy=strat, pair=pair,
            cost_model=cost_model, sizer=sizer,
            train_days=504, test_days=126, step_days=63,
            initial_capital=INITIAL_PER_PAIR,  # B1 fix: match candidate scale; $100k default zeroes positions via min_order_size
        )
        consistent = "YES" if wf.consistent else "NO"
        print(f"  {pair:<10} {len(wf.windows):>8} {wf.avg_sharpe:>8.2f} "
              f"{consistent:>12} {wf.total_trades:>11}")

    print("\n" + "=" * 72)
    print("  NULL HYPOTHESIS GATE (last 504 bars, 200 random shuffles)")
    print("=" * 72)
    for pair in PAIRS:
        e, s, _, _, _ = results[pair]
        n_held = min(504, len(e) - 100)
        held = e.iloc[-n_held:]
        held_s = s.iloc[-n_held:]
        held_r = run_backtest(
            data=held, signals=held_s, pair=pair,
            strategy_name="carry_momentum", cost_model=cost_model, sizer=sizer,
            initial_capital=INITIAL_PER_PAIR,
        )
        gate = NullHypothesisGate(n_random=200, percentile=95.0, seed=42)
        gr = gate.test(held_r, held, pair, cost_model, sizer=sizer, total_trials=10,
                       initial_capital=INITIAL_PER_PAIR)  # B1 fix: randoms must use the same capital as the candidate
        status = "PASSED" if gr.passed else "FAILED"
        print(f"  {pair:<10} {status:<8} Sharpe={gr.candidate_sharpe:>6.2f}  "
              f"Rank={gr.candidate_rank_pct:>5.1f}%  p={gr.dsr_adjusted_pvalue:.3f}")

    print("\n" + "=" * 72)
    print("  ARSON TEST (USDJPY)")
    print("=" * 72)
    e, s, _, _, _ = results["USDJPY"]
    arson = BacktestArsonTest(seed=42)
    ar = arson.run(e, s, "USDJPY", "carry_momentum", cost_model, sizer=sizer,
                   initial_capital=INITIAL_PER_PAIR)  # B1 fix: arson must use the candidate's capital scale
    print(ar.summary())


if __name__ == "__main__":
    main()
