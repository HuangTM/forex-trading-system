#!/usr/bin/env python3
"""Run Phase 0 baseline backtests across all configured pairs and strategies.

Usage:
    python scripts/run_backtest.py --config config/default.yaml
    python scripts/run_backtest.py --config config/default.yaml --walkforward
"""

import argparse
from pathlib import Path

from forex_system.analysis.comparison import format_comparison_table
from forex_system.analysis.reports import format_backtest_report, format_walkforward_report
from forex_system.analysis.visualization import plot_equity_curve, plot_monthly_returns
from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import PerformanceMetrics, calculate_metrics
from forex_system.backtest.walkforward import run_walkforward
from forex_system.core.config import load_config
from forex_system.core.types import PairInfo
from forex_system.costs.model import RealisticCostModel
from forex_system.data.storage import load_parquet
from forex_system.features.registry import compute_indicators
from forex_system.strategies.registry import create_strategy


def main():
    parser = argparse.ArgumentParser(description="Run Phase 0 baseline backtests")
    parser.add_argument(
        "--config", type=str, default="config/default.yaml", help="Config file path"
    )
    parser.add_argument("--walkforward", action="store_true", help="Run walk-forward analysis")
    parser.add_argument("--plots", action="store_true", help="Generate plots")
    parser.add_argument("--output-dir", type=str, default="data/results", help="Output directory")
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build cost model from config
    pair_infos = {p.symbol: p.to_pair_info() for p in config.pairs}
    cost_model = RealisticCostModel(pair_infos)

    comparison_results: list[dict] = []

    for pair_config in config.pairs:
        pair = pair_config.symbol
        print(f"\n{'=' * 60}")
        print(f"Pair: {pair}")
        print(f"{'=' * 60}")

        # Load data
        try:
            data = load_parquet(pair, "daily", config.data_dir)
        except Exception as e:
            print(f"  ERROR: Could not load data for {pair}: {e}")
            continue

        for strat_config in config.strategies:
            strategy = create_strategy(strat_config.name, strat_config.params)
            print(f"\n  Strategy: {strategy.name}")
            print(f"  Params: {strat_config.params}")

            # Compute indicators
            indicators_needed = strategy.required_indicators() + ["atr_14"]
            enriched = compute_indicators(data, indicators_needed)

            # Drop rows where indicators aren't ready yet
            enriched = enriched.dropna(subset=["atr_14"])

            if args.walkforward:
                # Walk-forward analysis
                wf_result = run_walkforward(
                    data=enriched,
                    strategy=strategy,
                    pair=pair,
                    cost_model=cost_model,
                    train_days=config.backtest.walkforward_train_days,
                    test_days=config.backtest.walkforward_test_days,
                    step_days=config.backtest.walkforward_step_days,
                    initial_capital=config.backtest.initial_capital,
                    risk_per_trade=config.backtest.risk_per_trade,
                    stop_loss_atr_multiple=config.backtest.stop_loss_atr_multiple,
                )

                report = format_walkforward_report(wf_result)
                print(f"\n{report}")

                # Save report
                report_path = output_dir / f"wf_{strategy.name}_{pair}.txt"
                report_path.write_text(report)

            else:
                # Full-period backtest
                signals = strategy.generate_signals(enriched)

                result = run_backtest(
                    data=enriched,
                    signals=signals,
                    pair=pair,
                    strategy_name=strategy.name,
                    cost_model=cost_model,
                    initial_capital=config.backtest.initial_capital,
                    risk_per_trade=config.backtest.risk_per_trade,
                    stop_loss_atr_multiple=config.backtest.stop_loss_atr_multiple,
                    entry_delay_bars=config.backtest.entry_delay_bars,
                )

                metrics = calculate_metrics(result.equity_curve, result.trade_log)
                report = format_backtest_report(result, metrics)
                print(f"\n{report}")

                # Save report
                report_path = output_dir / f"bt_{strategy.name}_{pair}.txt"
                report_path.write_text(report)

                # Plots
                if args.plots:
                    plot_equity_curve(
                        result, metrics,
                        save_path=output_dir / f"equity_{strategy.name}_{pair}.png",
                    )
                    plot_monthly_returns(
                        result,
                        save_path=output_dir / f"monthly_{strategy.name}_{pair}.png",
                    )

                comparison_results.append({
                    "strategy": strategy.name,
                    "pair": pair,
                    "metrics": metrics,
                })

    # Print comparison table
    if comparison_results:
        print("\n")
        table = format_comparison_table(comparison_results)
        print(table)

        # Save comparison
        (output_dir / "comparison.txt").write_text(table)
        print(f"\nResults saved to {output_dir}/")


if __name__ == "__main__":
    main()
