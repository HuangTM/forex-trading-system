#!/usr/bin/env python3
"""Run carry strategy as a diversified portfolio across all pairs.

The thesis: single-pair carry failed the null hypothesis gate because
the signal was nearly constant. A multi-pair portfolio diversifies
the carry exposure and produces more meaningful statistics.

Usage:
    python scripts/run_carry_portfolio.py
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

PAIRS = ["EURUSD", "USDJPY", "GBPUSD"]


def run_single_pair(pair: str, rate_data: pd.DataFrame, sizer, cost_model):
    """Run carry backtest on a single pair. Returns result + metrics."""
    ohlcv = load_parquet(pair, "daily", "data")
    enriched = compute_indicators(ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    strategy = CarryStrategy(
        params={"pair": pair, "min_differential": 0.002, "max_differential": 0.05},
        rate_data=rate_data,
    )

    signals = strategy.generate_signals(enriched)
    result = run_backtest(
        data=enriched, signals=signals, pair=pair,
        strategy_name="carry", cost_model=cost_model, sizer=sizer,
    )
    metrics = calculate_metrics(result.equity_curve, result.trade_log)

    return enriched, signals, result, metrics, strategy


def build_portfolio_equity(results: dict[str, tuple]) -> pd.Series:
    """Combine per-pair equity curves into an equal-weighted portfolio.

    Each pair gets 1/N of the capital. Portfolio equity = sum of per-pair
    equity curves, each starting at initial_capital/N.
    """
    n_pairs = len(results)
    initial_per_pair = 100_000.0  # Each pair backtested with 100K

    # Normalize each equity curve to returns, then combine
    all_returns = {}
    for pair, (_, _, result, _, _) in results.items():
        ec = result.equity_curve.dropna()
        if len(ec) > 1:
            returns = ec.pct_change().fillna(0.0)
            all_returns[pair] = returns

    if not all_returns:
        return pd.Series(dtype=float)

    # Align all return series to common date range
    returns_df = pd.DataFrame(all_returns)
    returns_df = returns_df.fillna(0.0)

    # Equal-weighted portfolio return
    portfolio_returns = returns_df.mean(axis=1)

    # Build portfolio equity curve
    portfolio_equity = (1 + portfolio_returns).cumprod() * (initial_per_pair * n_pairs)
    return portfolio_equity


def main():
    print("Loading rate data...")
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")

    # Rename columns to match pair names
    col_map = {c: c.replace("_diff", "") for c in rate_data.columns}
    rate_data = rate_data.rename(columns=col_map)

    cost_model = RealisticCostModel()
    sizer = ContinuousSizer(risk_per_trade=0.02, stop_loss_atr_multiple=2.0)

    # ========== Per-Pair Results ==========
    print("\n" + "=" * 70)
    print("PER-PAIR CARRY RESULTS")
    print("=" * 70)
    print(f"{'Pair':<10} {'Return':>10} {'Ann.Ret':>10} {'Sharpe':>8} "
          f"{'MaxDD':>8} {'Trades':>7} {'Signal Mean':>12}")
    print("-" * 70)

    results = {}
    for pair in PAIRS:
        enriched, signals, result, metrics, strategy = run_single_pair(
            pair, rate_data, sizer, cost_model,
        )
        results[pair] = (enriched, signals, result, metrics, strategy)

        print(f"  {pair:<8} {metrics.total_return:>10.2%} {metrics.annualized_return:>10.2%} "
              f"{metrics.sharpe_ratio:>8.2f} {metrics.max_drawdown:>8.2%} "
              f"{metrics.num_trades:>7d} {signals.mean():>12.3f}")

    # ========== Portfolio ==========
    print("\n" + "=" * 70)
    print("EQUAL-WEIGHTED CARRY PORTFOLIO (3 pairs)")
    print("=" * 70)

    portfolio_equity = build_portfolio_equity(results)
    if len(portfolio_equity) < 2:
        print("  Not enough data for portfolio analysis.")
        return

    # Compute portfolio metrics manually
    total_return = (portfolio_equity.iloc[-1] / portfolio_equity.iloc[0]) - 1.0
    n_years = (portfolio_equity.index[-1] - portfolio_equity.index[0]).days / 365.25
    ann_return = (1 + total_return) ** (1.0 / max(n_years, 0.001)) - 1.0

    daily_returns = portfolio_equity.pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)
              if daily_returns.std() > 0 else 0.0)

    drawdown = (portfolio_equity - portfolio_equity.cummax()) / portfolio_equity.cummax()
    max_dd = abs(drawdown.min())

    total_trades = sum(m.num_trades for _, _, _, m, _ in results.values())

    print(f"  Period:            {portfolio_equity.index[0].date()} to "
          f"{portfolio_equity.index[-1].date()}")
    print(f"  Total Return:      {total_return:>10.2%}")
    print(f"  Annualized Return: {ann_return:>10.2%}")
    print(f"  Sharpe Ratio:      {sharpe:>10.2f}")
    print(f"  Max Drawdown:      {max_dd:>10.2%}")
    print(f"  Total Trades:      {total_trades:>10d}")

    # ========== Walk-Forward per pair ==========
    print("\n" + "=" * 70)
    print("WALK-FORWARD SUMMARY (per pair)")
    print("=" * 70)
    print(f"  {'Pair':<10} {'Windows':>8} {'Avg SR':>8} {'Consistent':>12} {'OOS Trades':>11}")
    print("  " + "-" * 52)

    for pair in PAIRS:
        enriched, signals, result, metrics, strategy = results[pair]
        wf = run_walkforward(
            data=enriched, strategy=strategy, pair=pair,
            cost_model=cost_model, sizer=sizer,
            train_days=504, test_days=126, step_days=63,
        )
        consistent = "YES" if wf.consistent else "NO"
        print(f"  {pair:<10} {len(wf.windows):>8} {wf.avg_sharpe:>8.2f} "
              f"{consistent:>12} {wf.total_trades:>11}")

    # ========== Null Hypothesis Gate (on best pair) ==========
    print("\n" + "=" * 70)
    print("NULL HYPOTHESIS GATE")
    print("=" * 70)

    for pair in PAIRS:
        enriched, signals, result, metrics, strategy = results[pair]

        # Use last 2 years as held-out
        n_held = min(504, len(enriched) - 100)
        if n_held < 50:
            print(f"  {pair}: not enough data for held-out test")
            continue

        held_out = enriched.iloc[-n_held:]
        held_signals = signals.iloc[-n_held:]

        held_result = run_backtest(
            data=held_out, signals=held_signals, pair=pair,
            strategy_name="carry", cost_model=cost_model, sizer=sizer,
        )

        gate = NullHypothesisGate(n_random=200, percentile=95.0, seed=42)
        gr = gate.test(held_result, held_out, pair, cost_model, sizer=sizer, total_trials=10)

        status = "PASSED" if gr.passed else "FAILED"
        print(f"  {pair:<10} {status:<8} Sharpe={gr.candidate_sharpe:>6.2f}  "
              f"Rank={gr.candidate_rank_pct:>5.1f}%  p={gr.dsr_adjusted_pvalue:.3f}")

    # ========== Arson Test (on USDJPY — strongest carry) ==========
    print("\n" + "=" * 70)
    print("ARSON TEST (USDJPY — strongest carry signal)")
    print("=" * 70)

    enriched, signals, result, metrics, strategy = results["USDJPY"]
    arson = BacktestArsonTest(seed=42)
    ar = arson.run(enriched, signals, "USDJPY", "carry", cost_model, sizer=sizer)
    print(ar.summary())

    # ========== Verdict ==========
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    print(f"  Portfolio Sharpe: {sharpe:.2f}")
    if sharpe > 0.5:
        print("  Carry portfolio shows promising edge. Consider Phase 2 testing.")
    elif sharpe > 0:
        print("  Carry portfolio is marginally positive but weak.")
        print("  Consider: carry-adjusted momentum, more pairs (G10), sub-daily data.")
    else:
        print("  Carry portfolio is not positive. FX carry may not work at retail scale.")


if __name__ == "__main__":
    main()
