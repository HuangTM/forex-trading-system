"""Tests for walk-forward analysis."""

from forex_system.backtest.walkforward import run_walkforward
from forex_system.costs.model import RealisticCostModel
from forex_system.strategies.ma_crossover import MACrossoverStrategy


def test_walkforward_produces_windows(long_ohlcv):
    """Walk-forward should produce multiple test windows."""
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    cost_model = RealisticCostModel()

    result = run_walkforward(
        data=long_ohlcv,
        strategy=strategy,
        pair="EURUSD",
        cost_model=cost_model,
        train_days=100,
        test_days=50,
        step_days=50,
    )

    assert len(result.windows) > 0
    assert result.pair == "EURUSD"
    assert result.strategy_name == "ma_crossover"


def test_walkforward_no_overlap(long_ohlcv):
    """Test windows should not use training data."""
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    cost_model = RealisticCostModel()

    result = run_walkforward(
        data=long_ohlcv,
        strategy=strategy,
        pair="EURUSD",
        cost_model=cost_model,
        train_days=100,
        test_days=50,
        step_days=50,
    )

    for w in result.windows:
        # Test period must start after training period ends
        assert w.test_start > w.train_end


def test_walkforward_metrics_populated(long_ohlcv):
    """Each window should have valid metrics."""
    strategy = MACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    cost_model = RealisticCostModel()

    result = run_walkforward(
        data=long_ohlcv,
        strategy=strategy,
        pair="EURUSD",
        cost_model=cost_model,
        train_days=100,
        test_days=50,
        step_days=50,
    )

    for w in result.windows:
        assert w.metrics is not None
        assert w.num_test_bars > 0
