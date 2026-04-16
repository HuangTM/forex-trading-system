#!/usr/bin/env python3
"""Run carry strategy on 4H data — testing whether sub-daily resolution
helps statistical power for the carry signal.

Usage:
    python scripts/run_carry_4h.py
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
from forex_system.costs.model import RealisticCostModel
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.sizing.continuous import ContinuousSizer
from forex_system.strategies.carry import CarryStrategy

PAIRS = ["EURUSD", "USDJPY", "GBPUSD"]


def main():
    print("Loading data...")
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    col_map = {c: c.replace("_diff", "") for c in rate_data.columns}
    rate_data = rate_data.rename(columns=col_map)

    cost_model = RealisticCostModel()
    sizer = ContinuousSizer(risk_per_trade=0.02, stop_loss_atr_multiple=2.0)

    # ========== Per-Pair 4H Results ==========
    print("\n" + "=" * 70)
    print("4H CARRY RESULTS (synthetic data — tests statistical power, not alpha)")
    print("=" * 70)
    print(f"{'Pair':<10} {'Bars':>6} {'Return':>10} {'Ann.Ret':>10} {'Sharpe':>8} "
          f"{'MaxDD':>8} {'Trades':>7}")
    print("-" * 65)

    all_results = {}
    for pair in PAIRS:
        ohlcv = load_parquet(pair, "4h", "data")
        enriched = compute_indicators(ohlcv, ["atr_14"])
        enriched = enriched.dropna(subset=["atr_14"])

        strategy = CarryStrategy(
            params={"pair": pair, "min_differential": 0.002, "max_differential": 0.05},
            rate_data=rate_data,
        )

        signals = strategy.generate_signals(enriched)
        result = run_backtest(
            data=enriched, signals=signals, pair=pair,
            strategy_name="carry_4h", cost_model=cost_model, sizer=sizer,
        )
        metrics = calculate_metrics(result.equity_curve, result.trade_log)
        all_results[pair] = (enriched, signals, result, metrics)

        print(f"  {pair:<8} {len(enriched):>6} {metrics.total_return:>10.2%} "
              f"{metrics.annualized_return:>10.2%} {metrics.sharpe_ratio:>8.2f} "
              f"{metrics.max_drawdown:>8.2%} {metrics.num_trades:>7d}")

    # ========== Compare Daily vs 4H ==========
    print("\n" + "=" * 70)
    print("DAILY vs 4H COMPARISON (USDJPY)")
    print("=" * 70)

    # Daily
    daily_ohlcv = load_parquet("USDJPY", "daily", "data")
    daily_enriched = compute_indicators(daily_ohlcv, ["atr_14"])
    daily_enriched = daily_enriched.dropna(subset=["atr_14"])
    daily_strategy = CarryStrategy(
        params={"pair": "USDJPY", "min_differential": 0.002, "max_differential": 0.05},
        rate_data=rate_data,
    )
    daily_signals = daily_strategy.generate_signals(daily_enriched)
    daily_result = run_backtest(
        data=daily_enriched, signals=daily_signals, pair="USDJPY",
        strategy_name="carry_daily", cost_model=cost_model, sizer=sizer,
    )
    daily_metrics = calculate_metrics(daily_result.equity_curve, daily_result.trade_log)

    h4_enriched, h4_signals, h4_result, h4_metrics = all_results["USDJPY"]

    print(f"  {'Metric':<20} {'Daily':>12} {'4H':>12}")
    print("  " + "-" * 46)
    print(f"  {'Bars':<20} {len(daily_enriched):>12} {len(h4_enriched):>12}")
    print(f"  {'Total Return':<20} {daily_metrics.total_return:>12.2%} "
          f"{h4_metrics.total_return:>12.2%}")
    print(f"  {'Sharpe':<20} {daily_metrics.sharpe_ratio:>12.2f} "
          f"{h4_metrics.sharpe_ratio:>12.2f}")
    print(f"  {'Max Drawdown':<20} {daily_metrics.max_drawdown:>12.2%} "
          f"{h4_metrics.max_drawdown:>12.2%}")
    print(f"  {'Trades':<20} {daily_metrics.num_trades:>12} {h4_metrics.num_trades:>12}")

    # ========== Null Hypothesis Gate on 4H ==========
    print("\n" + "=" * 70)
    print("NULL HYPOTHESIS GATE (4H, n=200)")
    print("=" * 70)

    for pair in PAIRS:
        enriched, signals, result, metrics = all_results[pair]

        n_held = min(3024, len(enriched) - 500)  # ~2 years of 4H bars
        if n_held < 200:
            print(f"  {pair}: not enough data")
            continue

        held_out = enriched.iloc[-n_held:]
        held_signals = signals.iloc[-n_held:]

        held_result = run_backtest(
            data=held_out, signals=held_signals, pair=pair,
            strategy_name="carry_4h", cost_model=cost_model, sizer=sizer,
        )

        gate = NullHypothesisGate(n_random=200, percentile=95.0, seed=42)
        gr = gate.test(held_result, held_out, pair, cost_model, sizer=sizer, total_trials=10)

        status = "PASSED" if gr.passed else "FAILED"
        print(f"  {pair:<10} {status:<8} Sharpe={gr.candidate_sharpe:>6.2f}  "
              f"Rank={gr.candidate_rank_pct:>5.1f}%  p={gr.dsr_adjusted_pvalue:.3f}")

    # ========== Arson Test on 4H USDJPY ==========
    print("\n" + "=" * 70)
    print("ARSON TEST (4H USDJPY)")
    print("=" * 70)

    enriched, signals, result, metrics = all_results["USDJPY"]
    arson = BacktestArsonTest(seed=42)
    ar = arson.run(enriched, signals, "USDJPY", "carry_4h", cost_model, sizer=sizer)
    print(ar.summary())

    # ========== Verdict ==========
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    print("  NOTE: Results are on SYNTHETIC 4H data. They test whether the")
    print("  pipeline works and whether 4H resolution helps statistical power,")
    print("  but DO NOT prove alpha exists. Real 4H data from Saxo API needed.")


if __name__ == "__main__":
    main()
