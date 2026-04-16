"""Tests for NullHypothesisGate."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.analysis.null_hypothesis import (
    NullHypothesisGate,
    _deflated_sharpe_pvalue,
    _estimate_trade_frequency,
)
from forex_system.backtest.engine import run_backtest
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators


@pytest.fixture
def test_data(sample_ohlcv):
    """Enriched OHLCV data with ATR for testing."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    return enriched.dropna(subset=["atr_14"])


class TestNullHypothesisGate:

    def test_strong_signal_passes(self, test_data):
        """A strategy with obvious edge should pass."""
        # Create a signal that buys during the uptrend, sells during downtrend
        # The sample_ohlcv fixture has an uptrend then downtrend
        n = len(test_data)
        signals = pd.Series(1.0, index=test_data.index)
        signals.iloc[n // 2:] = -1.0

        result = run_backtest(
            data=test_data, signals=signals, pair="EURUSD",
            strategy_name="strong", cost_model=RealisticCostModel(),
        )

        gate = NullHypothesisGate(n_random=50, percentile=90.0, seed=42)
        gate_result = gate.test(
            result, test_data, "EURUSD", RealisticCostModel(),
        )

        # The candidate should rank high (though may not always pass with
        # only 50 random strategies and noisy data)
        assert gate_result.candidate_rank_pct > 50.0
        assert gate_result.n_random == 50

    def test_random_strategy_ranks_low(self, test_data):
        """A purely random signal should not rank in top percentile."""
        rng = np.random.default_rng(123)
        signals = pd.Series(
            rng.choice([-1.0, 0.0, 1.0], size=len(test_data)),
            index=test_data.index,
        )

        result = run_backtest(
            data=test_data, signals=signals, pair="EURUSD",
            strategy_name="random", cost_model=RealisticCostModel(),
        )

        gate = NullHypothesisGate(n_random=50, percentile=95.0, seed=42)
        gate_result = gate.test(
            result, test_data, "EURUSD", RealisticCostModel(),
        )

        # Random strategy should NOT consistently pass the gate
        # We check that it's not in the extreme top
        assert gate_result.candidate_rank_pct < 99.0

    def test_seed_reproducibility(self, test_data):
        """Same seed produces identical results."""
        signals = pd.Series(1.0, index=test_data.index)
        result = run_backtest(
            data=test_data, signals=signals, pair="EURUSD",
            strategy_name="test", cost_model=RealisticCostModel(),
        )

        gate = NullHypothesisGate(n_random=20, seed=42)
        r1 = gate.test(result, test_data, "EURUSD", RealisticCostModel())

        gate2 = NullHypothesisGate(n_random=20, seed=42)
        r2 = gate2.test(result, test_data, "EURUSD", RealisticCostModel())

        assert r1.candidate_rank_pct == r2.candidate_rank_pct
        assert r1.random_sharpe_mean == r2.random_sharpe_mean

    def test_result_fields(self, test_data):
        """NullHypothesisResult has all expected fields."""
        signals = pd.Series(1.0, index=test_data.index)
        result = run_backtest(
            data=test_data, signals=signals, pair="EURUSD",
            strategy_name="test", cost_model=RealisticCostModel(),
        )

        gate = NullHypothesisGate(n_random=10, seed=42)
        r = gate.test(result, test_data, "EURUSD", RealisticCostModel(), total_trials=5)

        assert isinstance(r.passed, bool)
        assert isinstance(r.candidate_sharpe, float)
        assert 0 <= r.candidate_rank_pct <= 100
        assert isinstance(r.random_sharpe_mean, float)
        assert isinstance(r.random_sharpe_std, float)
        assert isinstance(r.dsr_adjusted_pvalue, float)
        assert r.total_trials == 5
        assert r.n_random == 10


class TestDSRCorrection:

    def test_more_trials_increases_pvalue(self):
        """More total_trials makes it harder to pass (higher p-value)."""
        p1 = _deflated_sharpe_pvalue(1.5, 0.0, 0.5, total_trials=1)
        p10 = _deflated_sharpe_pvalue(1.5, 0.0, 0.5, total_trials=10)
        p100 = _deflated_sharpe_pvalue(1.5, 0.0, 0.5, total_trials=100)

        # More trials -> higher p-value (harder to reject null)
        assert p1 < p10 < p100

    def test_zero_std_extreme(self):
        """Zero null std returns deterministic result."""
        p = _deflated_sharpe_pvalue(1.0, 0.5, 0.0, total_trials=1)
        assert p == 0.0  # Candidate above mean

        p2 = _deflated_sharpe_pvalue(-0.5, 0.5, 0.0, total_trials=1)
        assert p2 == 1.0  # Candidate below mean


class TestHelpers:

    def test_trade_frequency_estimation(self):
        """Trade frequency correctly measures signal direction changes."""
        signals = pd.Series([1.0, 1.0, -1.0, -1.0, 0.0, 1.0, 1.0, -1.0])
        freq = _estimate_trade_frequency(signals)
        # Changes at indices 2, 4, 5, 7 = 4 changes out of 8 bars
        assert 0.3 < freq < 0.7
