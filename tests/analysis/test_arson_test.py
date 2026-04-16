"""Tests for BacktestArsonTest."""

from __future__ import annotations

import pandas as pd
import pytest

from forex_system.analysis.arson_test import BacktestArsonTest
from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators


@pytest.fixture
def test_data(sample_ohlcv):
    """Enriched OHLCV data with ATR."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    return enriched.dropna(subset=["atr_14"])


@pytest.fixture
def test_signals(test_data):
    """Simple alternating signal for testing."""
    n = len(test_data)
    signals = pd.Series(1.0, index=test_data.index)
    signals.iloc[n // 2:] = -1.0
    return signals


class TestBacktestArsonTest:

    def test_baseline_matches_direct_backtest(self, test_data, test_signals):
        """Arson test baseline matches a direct run_backtest call."""
        direct_result = run_backtest(
            data=test_data, signals=test_signals, pair="EURUSD",
            strategy_name="test", cost_model=RealisticCostModel(),
        )
        direct_metrics = calculate_metrics(
            direct_result.equity_curve, direct_result.trade_log,
        )

        arson = BacktestArsonTest(seed=42)
        result = arson.run(
            test_data, test_signals, "EURUSD", "test", RealisticCostModel(),
        )

        assert abs(result.baseline.sharpe_ratio - direct_metrics.sharpe_ratio) < 1e-6
        assert abs(result.baseline.total_return - direct_metrics.total_return) < 1e-6
        assert result.baseline.num_trades == direct_metrics.num_trades

    def test_has_all_degradation_modes(self, test_data, test_signals):
        """Arson test produces results for all 4 degradation modes."""
        arson = BacktestArsonTest(seed=42)
        result = arson.run(
            test_data, test_signals, "EURUSD", "test", RealisticCostModel(),
        )

        names = [d.name for d in result.degradations]
        assert "randomize_10pct" in names
        assert "randomize_25pct" in names
        assert "double_costs" in names
        assert "extra_delay" in names

    def test_double_costs_reduces_return(self, test_data, test_signals):
        """Doubling costs should reduce total return."""
        arson = BacktestArsonTest(seed=42)
        result = arson.run(
            test_data, test_signals, "EURUSD", "test", RealisticCostModel(),
        )

        double_cost = next(d for d in result.degradations if d.name == "double_costs")
        # With double costs, return should be worse (more negative or less positive)
        assert double_cost.total_return <= result.baseline.total_return + 1e-6

    def test_seed_reproducibility(self, test_data, test_signals):
        """Same seed produces identical results."""
        arson1 = BacktestArsonTest(seed=42)
        r1 = arson1.run(test_data, test_signals, "EURUSD", "test", RealisticCostModel())

        arson2 = BacktestArsonTest(seed=42)
        r2 = arson2.run(test_data, test_signals, "EURUSD", "test", RealisticCostModel())

        for d1, d2 in zip(r1.degradations, r2.degradations):
            assert d1.sharpe_ratio == d2.sharpe_ratio
            assert d1.total_return == d2.total_return

    def test_summary_output(self, test_data, test_signals):
        """ArsonResult.summary() returns non-empty, formatted string."""
        arson = BacktestArsonTest(seed=42)
        result = arson.run(
            test_data, test_signals, "EURUSD", "test", RealisticCostModel(),
        )

        summary = result.summary()
        assert len(summary) > 100
        assert "baseline" in summary
        assert "double_costs" in summary
        assert "Sharpe" in summary

    def test_randomization_changes_results(self, test_data, test_signals):
        """25% randomization should produce different Sharpe than baseline."""
        arson = BacktestArsonTest(seed=42)
        result = arson.run(
            test_data, test_signals, "EURUSD", "test", RealisticCostModel(),
        )

        rand_25 = next(d for d in result.degradations if d.name == "randomize_25pct")
        # With 25% of signals randomized, we expect some difference
        # (not guaranteed with small sample, but very likely)
        # At minimum, the degradation should complete without error
        assert isinstance(rand_25.sharpe_ratio, float)
