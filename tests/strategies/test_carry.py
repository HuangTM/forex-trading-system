"""Tests for CarryStrategy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.strategies.carry import CarryStrategy
from forex_system.strategies.registry import create_strategy


@pytest.fixture
def rate_data():
    """Synthetic rate differential data with a sign change midway."""
    dates = pd.bdate_range("2020-01-01", periods=500)
    # USDJPY: positive carry first half, flips negative second half
    usdjpy = np.concatenate([
        np.full(250, 0.03),   # +3% carry (long USD vs JPY)
        np.full(250, -0.02),  # -2% carry (flipped)
    ])
    # EURUSD: always negative carry
    eurusd = np.full(500, -0.015)
    return pd.DataFrame(
        {"USDJPY": usdjpy, "EURUSD": eurusd},
        index=dates,
    )


@pytest.fixture
def ohlcv_data():
    """Simple OHLCV data aligned with rate_data dates."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-01", periods=500)
    base = 110 + np.cumsum(rng.normal(0, 0.5, 500))
    return pd.DataFrame(
        {
            "open": base,
            "high": base + 0.5,
            "low": base - 0.5,
            "close": base + rng.normal(0, 0.2, 500),
            "volume": rng.integers(1000, 5000, 500),
        },
        index=dates,
    )


class TestCarryDynamic:
    """Tests for dynamic carry signals from rate differentials."""

    def test_positive_diff_produces_positive_signal(self, rate_data, ohlcv_data):
        """Positive rate differential -> positive signal."""
        strategy = CarryStrategy(
            {"pair": "USDJPY"}, rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv_data)

        # First half has +3% carry -> positive signal
        first_half = signals.iloc[:250]
        assert (first_half > 0).all()

    def test_sign_change_flips_signal(self, rate_data, ohlcv_data):
        """When differential flips sign, signal flips."""
        strategy = CarryStrategy(
            {"pair": "USDJPY"}, rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv_data)

        # First half positive, second half negative
        assert signals.iloc[100] > 0
        assert signals.iloc[400] < 0

    def test_signal_magnitude_proportional(self, rate_data, ohlcv_data):
        """Larger differential -> larger abs(signal)."""
        strategy = CarryStrategy(
            {"pair": "USDJPY", "max_differential": 0.05},
            rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv_data)

        # 3% carry / 5% max = 0.6 signal magnitude
        assert abs(signals.iloc[100] - 0.6) < 0.01
        # -2% carry / 5% max = -0.4 signal magnitude
        assert abs(signals.iloc[400] - (-0.4)) < 0.01

    def test_min_differential_threshold(self, ohlcv_data):
        """Differentials below threshold produce zero signal."""
        # Create rate data with tiny differential
        dates = pd.bdate_range("2020-01-01", periods=500)
        tiny_rates = pd.DataFrame(
            {"USDJPY": np.full(500, 0.001)},  # 0.1% — below default 0.5% threshold
            index=dates,
        )
        strategy = CarryStrategy(
            {"pair": "USDJPY", "min_differential": 0.005},
            rate_data=tiny_rates,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert (signals == 0.0).all()

    def test_signal_clipped_to_bounds(self, ohlcv_data):
        """Signals never exceed [-1, 1]."""
        dates = pd.bdate_range("2020-01-01", periods=500)
        huge_rates = pd.DataFrame(
            {"USDJPY": np.full(500, 0.20)},  # 20% — way beyond max_differential
            index=dates,
        )
        strategy = CarryStrategy(
            {"pair": "USDJPY", "max_differential": 0.05},
            rate_data=huge_rates,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert signals.max() <= 1.0
        assert signals.min() >= -1.0

    def test_missing_pair_raises(self, rate_data, ohlcv_data):
        """Requesting a pair not in rate_data raises ValueError."""
        strategy = CarryStrategy(
            {"pair": "GBPUSD"}, rate_data=rate_data,
        )
        with pytest.raises(ValueError, match="Rate data missing"):
            strategy.generate_signals(ohlcv_data)

    def test_negative_carry_pair(self, rate_data, ohlcv_data):
        """EURUSD with always-negative carry produces negative signals."""
        strategy = CarryStrategy(
            {"pair": "EURUSD"}, rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv_data)
        non_zero = signals[signals != 0.0]
        assert (non_zero < 0).all()


class TestCarryStatic:
    """Tests for static fallback mode."""

    def test_static_fallback_warns(self, ohlcv_data):
        """Using static mode emits a UserWarning."""
        strategy = CarryStrategy(
            {"pair": "USDJPY", "swap_long_pips_per_day": 0.8,
             "swap_short_pips_per_day": -1.5},
        )
        with pytest.warns(UserWarning, match="static swap rates"):
            strategy.generate_signals(ohlcv_data)

    def test_static_positive_swap_long(self, ohlcv_data):
        """Positive long swap -> constant +1 signal."""
        strategy = CarryStrategy(
            {"swap_long_pips_per_day": 0.8, "swap_short_pips_per_day": -1.5},
        )
        with pytest.warns(UserWarning):
            signals = strategy.generate_signals(ohlcv_data)
        assert (signals == 1.0).all()

    def test_static_positive_swap_short(self, ohlcv_data):
        """Positive short swap -> constant -1 signal."""
        strategy = CarryStrategy(
            {"swap_long_pips_per_day": -1.2, "swap_short_pips_per_day": 0.3},
        )
        with pytest.warns(UserWarning):
            signals = strategy.generate_signals(ohlcv_data)
        assert (signals == -1.0).all()


class TestCarryRegistry:
    """Tests for registry integration."""

    def test_factory_creates_carry(self):
        """create_strategy('carry', ...) works."""
        strategy = create_strategy("carry", {"pair": "USDJPY"})
        assert strategy.name == "carry"
        assert isinstance(strategy, CarryStrategy)

    def test_no_lookahead(self, rate_data, ohlcv_data):
        """Partial data signals match full data signals (no future leakage)."""
        strategy = CarryStrategy(
            {"pair": "USDJPY"}, rate_data=rate_data,
        )

        full_signals = strategy.generate_signals(ohlcv_data)
        partial_signals = strategy.generate_signals(ohlcv_data.iloc[:250])

        # Signals on the partial data should match the first 250 of full
        pd.testing.assert_series_equal(
            partial_signals,
            full_signals.iloc[:250],
            check_names=False,
        )
