"""Integration test — full pipeline from data to comparison table."""

import numpy as np
import pandas as pd

from forex_system.analysis.comparison import format_comparison_table
from forex_system.analysis.reports import format_backtest_report
from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.costs.model import RealisticCostModel
from forex_system.data.validation import validate_ohlcv
from forex_system.features.registry import compute_indicators
from forex_system.strategies.registry import create_strategy


def test_full_pipeline(sample_ohlcv):
    """End-to-end: data → validate → indicators → strategy → backtest → metrics → report."""
    pair = "EURUSD"

    # 1. Validate data
    report = validate_ohlcv(sample_ohlcv, pair)
    assert report.passed

    # 2. Create strategy
    strategy = create_strategy("ma_crossover", {"fast_period": 10, "slow_period": 30})

    # 3. Compute indicators
    indicators = strategy.required_indicators() + ["atr_14"]
    enriched = compute_indicators(sample_ohlcv, indicators)
    enriched = enriched.dropna(subset=["atr_14"])
    assert len(enriched) > 0

    # 4. Generate signals
    signals = strategy.generate_signals(enriched)
    assert len(signals) == len(enriched)

    # 5. Run backtest
    cost_model = RealisticCostModel()
    result = run_backtest(
        data=enriched,
        signals=signals,
        pair=pair,
        strategy_name=strategy.name,
        cost_model=cost_model,
    )

    assert result.pair == pair
    assert len(result.equity_curve.dropna()) > 0

    # 6. Calculate metrics
    metrics = calculate_metrics(result.equity_curve, result.trade_log)
    assert metrics.total_return is not None
    assert not np.isnan(metrics.sharpe_ratio)

    # 7. Generate report
    text_report = format_backtest_report(result, metrics)
    assert "Sharpe" in text_report
    assert pair in text_report


def test_all_strategies(sample_ohlcv):
    """All three baseline strategies run without error."""
    pair = "EURUSD"
    cost_model = RealisticCostModel()
    comparison = []

    for name, params in [
        ("ma_crossover", {"fast_period": 10, "slow_period": 30}),
        ("bollinger_rsi", {"bb_period": 10, "bb_std": 2.0, "rsi_period": 7,
                           "rsi_oversold": 30, "rsi_overbought": 70}),
        ("momentum", {"lookback_period": 10, "threshold": 0.0}),
    ]:
        strategy = create_strategy(name, params)
        indicators = strategy.required_indicators() + ["atr_14"]
        enriched = compute_indicators(sample_ohlcv, indicators)
        enriched = enriched.dropna(subset=["atr_14"])

        signals = strategy.generate_signals(enriched)
        result = run_backtest(
            data=enriched, signals=signals, pair=pair,
            strategy_name=strategy.name, cost_model=cost_model,
        )
        metrics = calculate_metrics(result.equity_curve, result.trade_log)

        comparison.append({"strategy": name, "pair": pair, "metrics": metrics})

    # Generate comparison table
    table = format_comparison_table(comparison)
    assert "PHASE 0" in table
    assert "DECISION" in table
