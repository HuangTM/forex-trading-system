"""Tests for ExperimentRegistry."""

from __future__ import annotations

import pandas as pd
import pytest

from forex_system.analysis.experiment_registry import ExperimentRegistry, _hash_dict
from forex_system.backtest.metrics import PerformanceMetrics
from forex_system.core.types import BacktestResult


@pytest.fixture
def registry(tmp_path):
    """Create a registry with a temp DB."""
    reg = ExperimentRegistry(db_path=tmp_path / "test.db")
    yield reg
    reg.close()


@pytest.fixture
def sample_result():
    """Minimal BacktestResult for testing."""
    dates = pd.bdate_range("2020-01-01", periods=10)
    return BacktestResult(
        equity_curve=pd.Series(range(100_000, 100_010), index=dates),
        trade_log=[],
        signals=pd.Series(0.0, index=dates),
        parameters={"fast_period": 50, "slow_period": 200},
        pair="EURUSD",
        strategy_name="ma_crossover",
        start_date=dates[0],
        end_date=dates[-1],
    )


@pytest.fixture
def sample_metrics():
    """Minimal PerformanceMetrics for testing."""
    return PerformanceMetrics(
        total_return=0.05,
        annualized_return=0.10,
        sharpe_ratio=1.2,
        sortino_ratio=1.5,
        max_drawdown=0.08,
        max_drawdown_duration_days=30,
        win_rate=0.55,
        profit_factor=1.3,
        num_trades=20,
        avg_trade_pnl_pips=2.5,
        avg_trade_duration_days=5.0,
        exposure_pct=0.40,
    )


class TestExperimentRegistry:

    def test_record_and_query(self, registry, sample_result, sample_metrics):
        """Record an experiment and query it back."""
        exp_id = registry.record(
            sample_result, sample_metrics,
            config_snapshot={"test": True},
            data_hash="abc123",
            tags=["test", "baseline"],
        )
        assert isinstance(exp_id, str)
        assert len(exp_id) == 36  # UUID format

        records = registry.query()
        assert len(records) == 1
        assert records[0].experiment_id == exp_id
        assert records[0].strategy_name == "ma_crossover"
        assert records[0].pair == "EURUSD"
        assert records[0].metrics["sharpe_ratio"] == 1.2
        assert records[0].parameters == {"fast_period": 50, "slow_period": 200}
        assert records[0].tags == ["test", "baseline"]

    def test_query_by_strategy(self, registry, sample_result, sample_metrics):
        """Filter experiments by strategy name."""
        registry.record(sample_result, sample_metrics, {"a": 1}, "h1")

        # Record a different strategy
        result2 = BacktestResult(
            equity_curve=sample_result.equity_curve,
            trade_log=[],
            signals=sample_result.signals,
            parameters={},
            pair="EURUSD",
            strategy_name="momentum",
            start_date=sample_result.start_date,
            end_date=sample_result.end_date,
        )
        registry.record(result2, sample_metrics, {"a": 2}, "h2")

        ma_records = registry.query(strategy="ma_crossover")
        assert len(ma_records) == 1
        assert ma_records[0].strategy_name == "ma_crossover"

        mom_records = registry.query(strategy="momentum")
        assert len(mom_records) == 1

    def test_query_by_pair(self, registry, sample_result, sample_metrics):
        """Filter experiments by pair."""
        registry.record(sample_result, sample_metrics, {"a": 1}, "h1")

        result2 = BacktestResult(
            equity_curve=sample_result.equity_curve,
            trade_log=[],
            signals=sample_result.signals,
            parameters={},
            pair="USDJPY",
            strategy_name="ma_crossover",
            start_date=sample_result.start_date,
            end_date=sample_result.end_date,
        )
        registry.record(result2, sample_metrics, {"a": 2}, "h2")

        eurusd = registry.query(pair="EURUSD")
        assert len(eurusd) == 1
        assert eurusd[0].pair == "EURUSD"

    def test_query_by_min_sharpe(self, registry, sample_result, sample_metrics):
        """Filter by minimum Sharpe ratio."""
        registry.record(sample_result, sample_metrics, {"a": 1}, "h1")

        low_sharpe = PerformanceMetrics(
            total_return=-0.05, annualized_return=-0.10, sharpe_ratio=-0.5,
            sortino_ratio=-0.3, max_drawdown=0.15, max_drawdown_duration_days=60,
            win_rate=0.35, profit_factor=0.7, num_trades=15,
            avg_trade_pnl_pips=-1.0, avg_trade_duration_days=3.0, exposure_pct=0.50,
        )
        result2 = BacktestResult(
            equity_curve=sample_result.equity_curve, trade_log=[],
            signals=sample_result.signals, parameters={},
            pair="EURUSD", strategy_name="bad_strategy",
            start_date=sample_result.start_date, end_date=sample_result.end_date,
        )
        registry.record(result2, low_sharpe, {"a": 2}, "h2")

        good = registry.query(min_sharpe=0.5)
        assert len(good) == 1
        assert good[0].metrics["sharpe_ratio"] == 1.2

    def test_query_by_tags(self, registry, sample_result, sample_metrics):
        """Filter by tag membership."""
        registry.record(sample_result, sample_metrics, {"a": 1}, "h1",
                        tags=["carry", "4h"])
        registry.record(sample_result, sample_metrics, {"a": 2}, "h2",
                        tags=["momentum", "daily"])

        carry = registry.query(tags=["carry"])
        assert len(carry) == 1
        assert "carry" in carry[0].tags

        # Multiple tags: all must match
        carry_4h = registry.query(tags=["carry", "4h"])
        assert len(carry_4h) == 1

        no_match = registry.query(tags=["carry", "daily"])
        assert len(no_match) == 0

    def test_trial_count(self, registry, sample_result, sample_metrics):
        """Trial count increments with each record."""
        assert registry.trial_count() == 0
        registry.record(sample_result, sample_metrics, {"a": 1}, "h1")
        assert registry.trial_count() == 1
        registry.record(sample_result, sample_metrics, {"a": 2}, "h2")
        assert registry.trial_count() == 2

    def test_wal_mode(self, registry):
        """Verify WAL journal mode is set."""
        mode = registry._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_empty_query(self, registry):
        """Query on empty DB returns empty list."""
        assert registry.query() == []

    def test_config_hash_deterministic(self):
        """Same config produces same hash."""
        config = {"strategy": "ma_crossover", "params": {"fast": 50, "slow": 200}}
        assert _hash_dict(config) == _hash_dict(config)

        # Different order, same content -> same hash
        config2 = {"params": {"slow": 200, "fast": 50}, "strategy": "ma_crossover"}
        assert _hash_dict(config) == _hash_dict(config2)

    def test_config_hash_differs_for_different_configs(self):
        """Different configs produce different hashes."""
        h1 = _hash_dict({"a": 1})
        h2 = _hash_dict({"a": 2})
        assert h1 != h2
