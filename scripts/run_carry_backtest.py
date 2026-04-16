#!/usr/bin/env python3
"""Run carry strategy backtest on USDJPY with FRED rate data.

This is the first real test of whether carry has edge after costs.
Runs: full-period backtest, walk-forward validation, null hypothesis gate,
and arson test diagnostic.

Usage:
    python scripts/run_carry_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

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


def main():
    # Load data
    print("Loading data...")
    ohlcv = load_parquet("USDJPY", "daily", "data")
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")

    # Rename column to match pair name expected by CarryStrategy
    rate_data = rate_data.rename(columns={"USDJPY_diff": "USDJPY"})

    print(f"  OHLCV: {len(ohlcv)} bars ({ohlcv.index[0].date()} to {ohlcv.index[-1].date()})")
    print(f"  Rates: {len(rate_data)} rows ({rate_data.index[0].date()} to "
          f"{rate_data.index[-1].date()})")

    # Setup
    strategy = CarryStrategy(
        params={"pair": "USDJPY", "min_differential": 0.005, "max_differential": 0.05},
        rate_data=rate_data,
    )
    cost_model = RealisticCostModel()
    sizer = ContinuousSizer(risk_per_trade=0.02, stop_loss_atr_multiple=2.0)

    # Compute indicators
    enriched = compute_indicators(ohlcv, strategy.required_indicators())
    enriched = enriched.dropna(subset=["atr_14"])
    print(f"  Enriched: {len(enriched)} bars after warmup")

    # ========== 1. Full-Period Backtest ==========
    print("\n" + "=" * 60)
    print("1. FULL-PERIOD BACKTEST (carry on USDJPY)")
    print("=" * 60)

    signals = strategy.generate_signals(enriched)
    print(f"  Signal stats: mean={signals.mean():.3f}, "
          f"non-zero={((signals.abs() > 0.01).sum() / len(signals)):.1%}")

    result = run_backtest(
        data=enriched, signals=signals, pair="USDJPY",
        strategy_name="carry", cost_model=cost_model, sizer=sizer,
    )
    metrics = calculate_metrics(result.equity_curve, result.trade_log)

    print(f"  Total Return:      {metrics.total_return:>10.2%}")
    print(f"  Annualized Return: {metrics.annualized_return:>10.2%}")
    print(f"  Sharpe Ratio:      {metrics.sharpe_ratio:>10.2f}")
    print(f"  Sortino Ratio:     {metrics.sortino_ratio:>10.2f}")
    print(f"  Max Drawdown:      {metrics.max_drawdown:>10.2%}")
    print(f"  Win Rate:          {metrics.win_rate:>10.2%}")
    print(f"  Profit Factor:     {metrics.profit_factor:>10.2f}")
    print(f"  Num Trades:        {metrics.num_trades:>10d}")
    print(f"  Avg Trade (pips):  {metrics.avg_trade_pnl_pips:>10.1f}")
    print(f"  Avg Duration:      {metrics.avg_trade_duration_days:>10.0f} days")
    print(f"  Exposure:          {metrics.exposure_pct:>10.2%}")

    # ========== 2. Walk-Forward Validation ==========
    print("\n" + "=" * 60)
    print("2. WALK-FORWARD VALIDATION")
    print("=" * 60)

    wf_result = run_walkforward(
        data=enriched, strategy=strategy, pair="USDJPY",
        cost_model=cost_model, sizer=sizer,
        train_days=504, test_days=126, step_days=63,
    )

    print(f"  Windows:    {len(wf_result.windows)}")
    print(f"  Avg Sharpe: {wf_result.avg_sharpe:.2f}")
    print(f"  Avg MaxDD:  {wf_result.avg_max_drawdown:.2%}")
    print(f"  Consistent: {'YES' if wf_result.consistent else 'NO'}")
    print(f"  Total OOS Trades: {wf_result.total_trades}")

    print(f"\n  {'Window':<6} {'Test Period':<25} {'Sharpe':>8} {'MaxDD':>8} {'Trades':>7}")
    print("  " + "-" * 56)
    for i, w in enumerate(wf_result.windows):
        print(f"  {i+1:<6} {str(w.test_start.date()) + ' to ' + str(w.test_end.date()):<25} "
              f"{w.metrics.sharpe_ratio:>8.2f} {w.metrics.max_drawdown:>8.2%} "
              f"{w.metrics.num_trades:>7d}")

    # ========== 3. Null Hypothesis Gate ==========
    print("\n" + "=" * 60)
    print("3. NULL HYPOTHESIS GATE (n=200 random strategies)")
    print("=" * 60)

    # Use last 2 years as held-out data
    held_out_start = enriched.index[-504] if len(enriched) > 504 else enriched.index[0]
    held_out = enriched.loc[held_out_start:]
    held_out_signals = signals.loc[held_out_start:]

    held_out_result = run_backtest(
        data=held_out, signals=held_out_signals, pair="USDJPY",
        strategy_name="carry", cost_model=cost_model, sizer=sizer,
    )

    gate = NullHypothesisGate(n_random=200, percentile=95.0, seed=42)
    gate_result = gate.test(
        held_out_result, held_out, "USDJPY", cost_model, sizer=sizer,
        total_trials=10,  # Account for all strategies tested in this project
    )

    print(f"  PASSED:            {'YES' if gate_result.passed else 'NO'}")
    print(f"  Candidate Sharpe:  {gate_result.candidate_sharpe:>10.2f}")
    print(f"  Rank Percentile:   {gate_result.candidate_rank_pct:>10.1f}%")
    print(f"  Random Mean SR:    {gate_result.random_sharpe_mean:>10.2f}")
    print(f"  Random Std SR:     {gate_result.random_sharpe_std:>10.2f}")
    print(f"  DSR p-value:       {gate_result.dsr_adjusted_pvalue:>10.4f}")
    print(f"  Total Trials:      {gate_result.total_trials:>10d}")

    # ========== 4. Arson Test ==========
    print("\n" + "=" * 60)
    print("4. ARSON TEST (signal sensitivity diagnostic)")
    print("=" * 60)

    arson = BacktestArsonTest(seed=42)
    arson_result = arson.run(
        enriched, signals, "USDJPY", "carry", cost_model, sizer=sizer,
    )
    print(arson_result.summary())

    # ========== Summary ==========
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if gate_result.passed:
        print("  Carry on USDJPY PASSED the null hypothesis gate.")
        print("  Proceed to Phase 2: paper trading on Saxo SIM.")
    else:
        print("  Carry on USDJPY DID NOT pass the null hypothesis gate.")
        print("  The strategy may not have genuine edge after costs.")
        print("  Consider: different pairs, timeframes, or strategy classes.")


if __name__ == "__main__":
    main()
