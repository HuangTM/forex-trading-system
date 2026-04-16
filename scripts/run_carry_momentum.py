#!/usr/bin/env python3
"""Run carry-adjusted momentum strategy — the direction-timing hybrid.

Tests multiple parameter combinations and compares against pure carry
and pure momentum baselines.

Usage:
    python scripts/run_carry_momentum.py
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
from forex_system.costs.model import RealisticCostModel
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.sizing.continuous import ContinuousSizer
from forex_system.strategies.carry import CarryStrategy
from forex_system.strategies.carry_momentum import CarryMomentumStrategy
from forex_system.strategies.ma_crossover import MACrossoverStrategy

PAIRS = ["EURUSD", "USDJPY", "GBPUSD"]


def run_strategy(enriched, signals, pair, name, cost_model, sizer):
    """Run backtest and return metrics."""
    result = run_backtest(
        data=enriched, signals=signals, pair=pair,
        strategy_name=name, cost_model=cost_model, sizer=sizer,
    )
    metrics = calculate_metrics(result.equity_curve, result.trade_log)
    return result, metrics


def main():
    print("Loading data...")
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    col_map = {c: c.replace("_diff", "") for c in rate_data.columns}
    rate_data = rate_data.rename(columns=col_map)

    cost_model = RealisticCostModel()
    sizer = ContinuousSizer(risk_per_trade=0.02, stop_loss_atr_multiple=2.0)

    # ========== Parameter Grid ==========
    param_configs = [
        {"label": "CM 20/50 agree", "fast_period": 20, "slow_period": 50, "agreement_only": True},
        {"label": "CM 10/30 agree", "fast_period": 10, "slow_period": 30, "agreement_only": True},
        {"label": "CM 20/50 blend", "fast_period": 20, "slow_period": 50, "agreement_only": False},
        {"label": "CM 50/200 agree", "fast_period": 50, "slow_period": 200, "agreement_only": True},
    ]

    for pair in PAIRS:
        print(f"\n{'=' * 70}")
        print(f"  {pair}")
        print(f"{'=' * 70}")

        ohlcv = load_parquet(pair, "daily", "data")
        # Need indicators for all configs
        all_indicators = ["atr_14", "sma_10", "sma_20", "sma_30", "sma_50", "sma_200"]
        enriched = compute_indicators(ohlcv, all_indicators)
        enriched = enriched.dropna(subset=["atr_14", "sma_200"])  # Wait for slowest

        # Baselines
        print(f"\n  {'Strategy':<22} {'Return':>10} {'Ann.Ret':>10} {'Sharpe':>8} "
              f"{'MaxDD':>8} {'Trades':>7} {'WinRate':>8}")
        print("  " + "-" * 78)

        # Pure carry baseline
        carry_strat = CarryStrategy(
            {"pair": pair, "min_differential": 0.002, "max_differential": 0.05},
            rate_data=rate_data,
        )
        carry_sig = carry_strat.generate_signals(enriched)
        _, carry_m = run_strategy(enriched, carry_sig, pair, "carry", cost_model, sizer)
        print(f"  {'Pure Carry':<22} {carry_m.total_return:>10.2%} "
              f"{carry_m.annualized_return:>10.2%} {carry_m.sharpe_ratio:>8.2f} "
              f"{carry_m.max_drawdown:>8.2%} {carry_m.num_trades:>7} "
              f"{carry_m.win_rate:>8.1%}")

        # Pure momentum baseline (50/200 SMA)
        ma_strat = MACrossoverStrategy({"fast_period": 50, "slow_period": 200})
        ma_sig = ma_strat.generate_signals(enriched)
        _, ma_m = run_strategy(enriched, ma_sig, pair, "ma_cross", cost_model, sizer)
        print(f"  {'Pure MA 50/200':<22} {ma_m.total_return:>10.2%} "
              f"{ma_m.annualized_return:>10.2%} {ma_m.sharpe_ratio:>8.2f} "
              f"{ma_m.max_drawdown:>8.2%} {ma_m.num_trades:>7} "
              f"{ma_m.win_rate:>8.1%}")

        # Carry-momentum variants
        best_sharpe = -999
        best_config = None
        best_result = None
        best_signals = None

        for cfg in param_configs:
            cm_strat = CarryMomentumStrategy(
                {
                    "pair": pair,
                    "fast_period": cfg["fast_period"],
                    "slow_period": cfg["slow_period"],
                    "agreement_only": cfg["agreement_only"],
                    "min_differential": 0.002,
                    "max_differential": 0.05,
                    "carry_weight": 0.4,
                    "momentum_weight": 0.6,
                },
                rate_data=rate_data,
            )
            cm_sig = cm_strat.generate_signals(enriched)
            cm_result, cm_m = run_strategy(
                enriched, cm_sig, pair, cfg["label"], cost_model, sizer,
            )

            marker = ""
            if cm_m.sharpe_ratio > best_sharpe:
                best_sharpe = cm_m.sharpe_ratio
                best_config = cfg
                best_result = cm_result
                best_signals = cm_sig
                marker = " <-- best"

            print(f"  {cfg['label']:<22} {cm_m.total_return:>10.2%} "
                  f"{cm_m.annualized_return:>10.2%} {cm_m.sharpe_ratio:>8.2f} "
                  f"{cm_m.max_drawdown:>8.2%} {cm_m.num_trades:>7} "
                  f"{cm_m.win_rate:>8.1%}{marker}")

    # ========== Deep Dive: Best Config on USDJPY ==========
    print(f"\n{'=' * 70}")
    print("DEEP DIVE: USDJPY (strongest carry pair)")
    print(f"{'=' * 70}")

    ohlcv = load_parquet("USDJPY", "daily", "data")
    enriched = compute_indicators(ohlcv, ["atr_14", "sma_20", "sma_50"])
    enriched = enriched.dropna(subset=["atr_14", "sma_50"])

    best_strat = CarryMomentumStrategy(
        {
            "pair": "USDJPY", "fast_period": 20, "slow_period": 50,
            "agreement_only": True, "min_differential": 0.002,
            "max_differential": 0.05, "carry_weight": 0.4, "momentum_weight": 0.6,
        },
        rate_data=rate_data,
    )
    signals = best_strat.generate_signals(enriched)
    result = run_backtest(
        data=enriched, signals=signals, pair="USDJPY",
        strategy_name="carry_momentum", cost_model=cost_model, sizer=sizer,
    )
    metrics = calculate_metrics(result.equity_curve, result.trade_log)

    # Signal analysis
    signal_changes = (signals.diff().abs() > 0.01).sum()
    time_in_market = (signals.abs() > 0.01).mean()
    print(f"  Signal changes:    {signal_changes}")
    print(f"  Time in market:    {time_in_market:.1%}")
    print(f"  Trades:            {metrics.num_trades}")
    print(f"  Sharpe:            {metrics.sharpe_ratio:.2f}")

    # Walk-forward
    print("\n  Walk-Forward:")
    wf = run_walkforward(
        data=enriched, strategy=best_strat, pair="USDJPY",
        cost_model=cost_model, sizer=sizer,
        train_days=504, test_days=126, step_days=63,
    )
    print(f"    Windows: {len(wf.windows)}, Avg Sharpe: {wf.avg_sharpe:.2f}, "
          f"Consistent: {'YES' if wf.consistent else 'NO'}")
    positive = sum(1 for w in wf.windows if w.metrics.sharpe_ratio > 0)
    print(f"    Positive windows: {positive}/{len(wf.windows)}")

    # Null Hypothesis Gate
    print("\n  Null Hypothesis Gate (n=200):")
    n_held = min(504, len(enriched) - 100)
    held_out = enriched.iloc[-n_held:]
    held_signals = signals.iloc[-n_held:]
    held_result = run_backtest(
        data=held_out, signals=held_signals, pair="USDJPY",
        strategy_name="carry_momentum", cost_model=cost_model, sizer=sizer,
    )

    gate = NullHypothesisGate(n_random=200, percentile=95.0, seed=42)
    gr = gate.test(held_result, held_out, "USDJPY", cost_model, sizer=sizer, total_trials=15)
    status = "PASSED" if gr.passed else "FAILED"
    print(f"    {status}: Sharpe={gr.candidate_sharpe:.2f}, "
          f"Rank={gr.candidate_rank_pct:.1f}%, p={gr.dsr_adjusted_pvalue:.3f}")

    # Arson Test
    print("\n  Arson Test:")
    arson = BacktestArsonTest(seed=42)
    ar = arson.run(enriched, signals, "USDJPY", "carry_momentum", cost_model, sizer=sizer)
    print(ar.summary())


if __name__ == "__main__":
    main()
