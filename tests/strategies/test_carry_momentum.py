"""Tests for CarryMomentumStrategy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.features.registry import compute_indicators
from forex_system.strategies.carry_momentum import CarryMomentumStrategy
from forex_system.strategies.registry import create_strategy


@pytest.fixture
def rate_data():
    """Synthetic rate data: USDJPY positive carry throughout."""
    dates = pd.bdate_range("2019-01-01", periods=600)
    return pd.DataFrame(
        {"USDJPY": np.full(600, 0.03)},  # +3% carry
        index=dates,
    )


@pytest.fixture
def uptrend_data():
    """OHLCV with clear uptrend (momentum should agree with positive carry)."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-01", periods=300)
    # Strong uptrend: price goes from 100 to ~115
    trend = np.linspace(100, 115, 300) + rng.normal(0, 0.3, 300)
    return pd.DataFrame(
        {
            "open": trend + rng.normal(0, 0.1, 300),
            "high": trend + abs(rng.normal(0, 0.5, 300)),
            "low": trend - abs(rng.normal(0, 0.5, 300)),
            "close": trend,
            "volume": rng.integers(1000, 5000, 300),
        },
        index=dates,
    )


@pytest.fixture
def downtrend_data():
    """OHLCV with clear downtrend (momentum should disagree with positive carry)."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-01", periods=300)
    trend = np.linspace(115, 100, 300) + rng.normal(0, 0.3, 300)
    return pd.DataFrame(
        {
            "open": trend + rng.normal(0, 0.1, 300),
            "high": trend + abs(rng.normal(0, 0.5, 300)),
            "low": trend - abs(rng.normal(0, 0.5, 300)),
            "close": trend,
            "volume": rng.integers(1000, 5000, 300),
        },
        index=dates,
    )


class TestCarryMomentum:

    def test_agreement_produces_signal(self, rate_data, uptrend_data):
        """When carry is positive and momentum is up -> positive signal."""
        strategy = CarryMomentumStrategy(
            {"pair": "USDJPY", "fast_period": 20, "slow_period": 50},
            rate_data=rate_data,
        )
        enriched = compute_indicators(uptrend_data, strategy.required_indicators())
        enriched = enriched.dropna()
        signals = strategy.generate_signals(enriched)

        # After warmup, should see positive signals in uptrend
        late_signals = signals.iloc[-50:]
        assert (late_signals > 0).mean() > 0.7, "Expected mostly positive signals in uptrend"

    def test_disagreement_goes_flat(self, rate_data, downtrend_data):
        """When carry is positive but momentum is down -> flat."""
        strategy = CarryMomentumStrategy(
            {"pair": "USDJPY", "fast_period": 20, "slow_period": 50,
             "agreement_only": True},
            rate_data=rate_data,
        )
        enriched = compute_indicators(downtrend_data, strategy.required_indicators())
        enriched = enriched.dropna()
        signals = strategy.generate_signals(enriched)

        # In downtrend with positive carry, agreement_only should produce mostly zeros
        late_signals = signals.iloc[-50:]
        assert (late_signals == 0.0).mean() > 0.7, "Expected mostly flat when signals disagree"

    def test_no_agreement_mode_blends(self, rate_data, downtrend_data):
        """With agreement_only=False, signals blend even when opposing."""
        strategy = CarryMomentumStrategy(
            {"pair": "USDJPY", "fast_period": 20, "slow_period": 50,
             "agreement_only": False},
            rate_data=rate_data,
        )
        enriched = compute_indicators(downtrend_data, strategy.required_indicators())
        enriched = enriched.dropna()
        signals = strategy.generate_signals(enriched)

        # Should have non-zero signals even in disagreement
        late_signals = signals.iloc[-50:]
        assert (late_signals != 0.0).any(), "Expected some non-zero signals in blend mode"

    def test_signals_bounded(self, rate_data, uptrend_data):
        """Signals always in [-1, 1]."""
        strategy = CarryMomentumStrategy(
            {"pair": "USDJPY"}, rate_data=rate_data,
        )
        enriched = compute_indicators(uptrend_data, strategy.required_indicators())
        enriched = enriched.dropna()
        signals = strategy.generate_signals(enriched)

        assert signals.max() <= 1.0
        assert signals.min() >= -1.0

    def test_more_trades_than_pure_carry(self, rate_data, uptrend_data, downtrend_data):
        """Carry-momentum produces more signal changes than pure carry."""
        from forex_system.strategies.carry import CarryStrategy

        # Build mixed data: uptrend then downtrend
        mixed = pd.concat([uptrend_data.iloc[:150], downtrend_data.iloc[:150]])
        mixed.index = pd.bdate_range("2020-01-01", periods=len(mixed))

        carry_only = CarryStrategy(
            {"pair": "USDJPY", "min_differential": 0.002}, rate_data=rate_data,
        )
        carry_mom = CarryMomentumStrategy(
            {"pair": "USDJPY", "fast_period": 20, "slow_period": 50},
            rate_data=rate_data,
        )

        enriched = compute_indicators(mixed, carry_mom.required_indicators())
        enriched = enriched.dropna()

        carry_signals = carry_only.generate_signals(enriched)
        cm_signals = carry_mom.generate_signals(enriched)

        carry_changes = (carry_signals.diff().abs() > 0.01).sum()
        cm_changes = (cm_signals.diff().abs() > 0.01).sum()

        assert cm_changes >= carry_changes, "Carry-momentum should have more signal changes"

    def test_no_lookahead(self, rate_data, uptrend_data):
        """Partial data signals match full data signals."""
        strategy = CarryMomentumStrategy(
            {"pair": "USDJPY"}, rate_data=rate_data,
        )
        enriched = compute_indicators(uptrend_data, strategy.required_indicators())
        enriched = enriched.dropna()

        full = strategy.generate_signals(enriched)
        partial = strategy.generate_signals(enriched.iloc[:150])

        pd.testing.assert_series_equal(
            partial, full.iloc[:150], check_names=False,
        )

    def test_factory_creates(self):
        """Registry creates carry_momentum."""
        strategy = create_strategy("carry_momentum", {"pair": "USDJPY"})
        assert strategy.name == "carry_momentum"

    def test_no_rate_data_uses_momentum_only(self, uptrend_data):
        """Without rate_data, carry component is zero -> pure momentum."""
        strategy = CarryMomentumStrategy(
            {"pair": "USDJPY", "agreement_only": False},
            rate_data=None,
        )
        enriched = compute_indicators(uptrend_data, strategy.required_indicators())
        enriched = enriched.dropna()
        signals = strategy.generate_signals(enriched)

        # With agreement_only=False and no carry, pure momentum
        late_signals = signals.iloc[-50:]
        assert (late_signals != 0.0).any()
