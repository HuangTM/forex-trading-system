"""Tests for PredictionLog."""

from __future__ import annotations

import pandas as pd
import pytest

from forex_system.analysis.prediction_log import PredictionLog, _hash_params


@pytest.fixture
def log(tmp_path):
    plog = PredictionLog(output_dir=tmp_path / "predictions")
    yield plog
    plog.close()


@pytest.fixture
def sample_signals():
    dates = pd.bdate_range("2024-01-02", periods=20)
    return pd.Series([1.0] * 10 + [-1.0] * 10, index=dates)


class TestPredictionLog:

    def test_log_and_load(self, log, sample_signals):
        """Log signals and load them back."""
        log.log(sample_signals, "carry_momentum", "USDJPY",
                parameters={"fast": 20, "slow": 50})
        log.flush()

        loaded = log.load()
        assert len(loaded) == 20
        assert loaded["strategy"].iloc[0] == "carry_momentum"
        assert loaded["pair"].iloc[0] == "USDJPY"
        assert loaded["signal"].iloc[0] == 1.0
        assert loaded["signal"].iloc[15] == -1.0

    def test_filter_by_strategy(self, log, sample_signals):
        """Filter by strategy name."""
        log.log(sample_signals, "carry_momentum", "USDJPY")
        log.log(sample_signals, "ma_crossover", "USDJPY")
        log.flush()

        carry = log.load(strategy="carry_momentum")
        assert len(carry) == 20
        assert (carry["strategy"] == "carry_momentum").all()

    def test_filter_by_pair(self, log, sample_signals):
        """Filter by pair."""
        log.log(sample_signals, "carry_momentum", "USDJPY")
        log.log(sample_signals, "carry_momentum", "GBPJPY")
        log.flush()

        usdjpy = log.load(pair="USDJPY")
        assert len(usdjpy) == 20
        assert (usdjpy["pair"] == "USDJPY").all()

    def test_filter_by_source(self, log, sample_signals):
        """Filter by source."""
        log.log(sample_signals, "cm", "USDJPY", source="backtest")
        log.log(sample_signals, "cm", "USDJPY", source="paper")
        log.flush()

        bt = log.load(source="backtest")
        assert len(bt) == 20
        assert (bt["source"] == "backtest").all()

    def test_filter_by_date_range(self, log, sample_signals):
        """Filter by date range."""
        log.log(sample_signals, "cm", "USDJPY")
        log.flush()

        subset = log.load(start="2024-01-10", end="2024-01-20")
        assert len(subset) > 0
        assert subset["timestamp"].min() >= pd.Timestamp("2024-01-10")

    def test_predictions_with_confidence(self, log):
        """Log with prediction DataFrame including confidence."""
        dates = pd.bdate_range("2024-01-02", periods=10)
        signals = pd.Series([0.8] * 10, index=dates)
        preds = pd.DataFrame({
            "signal": signals,
            "confidence": [0.7] * 10,
            "model_id": ["cm_v1"] * 10,
        }, index=dates)

        log.log(signals, "cm", "USDJPY", predictions=preds)
        log.flush()

        loaded = log.load()
        assert "confidence" in loaded.columns
        assert loaded["confidence"].iloc[0] == 0.7

    def test_compare_sources(self, log):
        """Compare backtest vs paper signals."""
        dates = pd.bdate_range("2024-01-02", periods=10)
        bt_signals = pd.Series([1.0] * 10, index=dates)
        paper_signals = pd.Series([1.0] * 8 + [-1.0] * 2, index=dates)

        log.log(bt_signals, "cm", "USDJPY", source="backtest")
        log.log(paper_signals, "cm", "USDJPY", source="paper")
        log.flush()

        comp = log.compare_sources("cm", "USDJPY", "backtest", "paper")
        assert len(comp) == 10
        assert "signal_backtest" in comp.columns
        assert "signal_paper" in comp.columns
        assert "diff" in comp.columns
        assert "agree" in comp.columns
        # First 8 agree, last 2 disagree
        assert comp["agree"].sum() == 8

    def test_unique_trials(self, log, sample_signals):
        """Count unique strategy-param combos."""
        log.log(sample_signals, "cm", "USDJPY", parameters={"fast": 20})
        log.log(sample_signals, "cm", "USDJPY", parameters={"fast": 50})
        log.log(sample_signals, "ma", "USDJPY", parameters={"fast": 20})
        log.flush()

        assert log.unique_trials() == 3

    def test_append_to_existing(self, log):
        """Second flush appends to existing month file."""
        dates1 = pd.bdate_range("2024-01-02", periods=5)
        dates2 = pd.bdate_range("2024-01-09", periods=5)

        log.log(pd.Series([1.0] * 5, index=dates1), "cm", "USDJPY")
        log.flush()

        log.log(pd.Series([-1.0] * 5, index=dates2), "cm", "USDJPY")
        log.flush()

        loaded = log.load()
        assert len(loaded) == 10

    def test_empty_load(self, log):
        """Load on empty log returns empty DataFrame."""
        assert log.load().empty

    def test_params_hash_deterministic(self):
        """Same params produce same hash."""
        h1 = _hash_params({"fast": 20, "slow": 50})
        h2 = _hash_params({"slow": 50, "fast": 20})
        assert h1 == h2

    def test_params_hash_differs(self):
        """Different params produce different hash."""
        h1 = _hash_params({"fast": 20})
        h2 = _hash_params({"fast": 50})
        assert h1 != h2
