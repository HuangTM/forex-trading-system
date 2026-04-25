"""Tests for CarryFREDStrategy — CONSENSUS Bet #1.

Covers:
- Signal bounds: always in [-1, +1]
- Non-degenerate: with real FRED data, signal varies over time
- Missing rate data: forward-fill behaviour
- Cross-sectional rank normalization (z-score)
- Raw signal mode (rank_normalize=False)
- Registry integration
- No-lookahead: partial data produces matching prefix of full-data signals
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.strategies.carry_fred import CarryFREDStrategy
from forex_system.strategies.registry import create_strategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ohlcv_data():
    """Simple OHLCV data, 500 business days starting 2020-01-01."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-01", periods=500)
    base = 110.0 + np.cumsum(rng.normal(0, 0.5, 500))
    return pd.DataFrame(
        {
            "open": base,
            "high": base + 0.5,
            "low": base - 0.5,
            "close": base + rng.normal(0, 0.2, 500),
            "volume": rng.integers(1000, 5000, 500),
            "atr_14": np.abs(rng.normal(1.0, 0.3, 500)),
        },
        index=dates,
    )


def _make_rate_data(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Synthetic 12-pair rate differential DataFrame matching FRED column names."""
    n = len(dates)
    # Vary differentials over time so signals are non-constant
    data = {
        "AUDJPY_diff": np.linspace(0.01, 0.04, n),
        "AUDUSD_diff": np.linspace(0.005, -0.005, n),
        "CADJPY_diff": np.linspace(0.02, 0.03, n),
        "EURGBP_diff": np.linspace(-0.01, 0.01, n),
        "EURJPY_diff": np.linspace(0.005, 0.025, n),
        "EURUSD_diff": np.linspace(-0.02, -0.005, n),
        "GBPJPY_diff": np.linspace(0.015, 0.035, n),
        "GBPUSD_diff": np.linspace(-0.01, 0.01, n),
        "NZDJPY_diff": np.linspace(0.02, 0.04, n),
        "NZDUSD_diff": np.linspace(0.005, 0.015, n),
        "USDCAD_diff": np.linspace(-0.005, 0.005, n),
        "USDJPY_diff": np.linspace(0.03, 0.05, n),
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def rate_data(ohlcv_data):
    """Synthetic rate data aligned to ohlcv dates."""
    return _make_rate_data(ohlcv_data.index)


# ---------------------------------------------------------------------------
# Signal bound tests
# ---------------------------------------------------------------------------

class TestSignalBounds:
    """Signals must always be in [-1, +1]."""

    def test_ranked_signals_in_bounds(self, ohlcv_data, rate_data):
        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True},
            rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert signals.max() <= 1.0 + 1e-9
        assert signals.min() >= -1.0 - 1e-9

    def test_raw_signals_in_bounds(self, ohlcv_data, rate_data):
        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": False, "max_differential": 0.05},
            rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert signals.max() <= 1.0 + 1e-9
        assert signals.min() >= -1.0 - 1e-9

    def test_extreme_differentials_clipped(self, ohlcv_data):
        """100x normal differentials are clipped to ±1."""
        dates = ohlcv_data.index
        extreme = _make_rate_data(dates)
        extreme = extreme * 100  # huge values

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True},
            rate_data=extreme,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert signals.max() <= 1.0 + 1e-9
        assert signals.min() >= -1.0 - 1e-9

    def test_signals_are_series(self, ohlcv_data, rate_data):
        strategy = CarryFREDStrategy({"pair": "AUDUSD"}, rate_data=rate_data)
        signals = strategy.generate_signals(ohlcv_data)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(ohlcv_data)


# ---------------------------------------------------------------------------
# Non-degenerate / varying signal tests
# ---------------------------------------------------------------------------

class TestNonDegenerate:
    """Signals must vary — not all identical (the Phase 1 carry bug)."""

    def test_signals_vary_over_time_ranked(self, ohlcv_data):
        """Cross-sectional ranked signal should vary over time (not constant).

        Build a symmetric cross-section where all pairs vary at the same rate,
        so that USDJPY's z-score is continuously varying (not clipped constant).
        """
        dates = ohlcv_data.index
        n = len(dates)
        rng = np.random.default_rng(55)
        # Each pair gets a small random walk — z-scoring a random walk produces
        # continuously varying (not clipped) z-scores
        pairs = [
            "AUDJPY_diff", "AUDUSD_diff", "CADJPY_diff", "EURGBP_diff",
            "EURJPY_diff", "EURUSD_diff", "GBPJPY_diff", "GBPUSD_diff",
            "NZDJPY_diff", "NZDUSD_diff", "USDCAD_diff", "USDJPY_diff",
        ]
        data = {c: np.cumsum(rng.normal(0, 0.002, n)) + 0.01 for c in pairs}
        rate_df = pd.DataFrame(data, index=dates)

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True, "min_differential": 0.0},
            rate_data=rate_df,
        )
        signals = strategy.generate_signals(ohlcv_data)
        # Random-walk cross-section produces continuously varying z-scores
        assert signals.nunique() > 5, (
            "Signals are nearly constant — degenerate static-carry bug detected"
        )

    def test_signals_vary_over_time_raw(self, ohlcv_data, rate_data):
        """Raw (non-ranked) signal should also vary when diff changes."""
        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": False},
            rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert signals.nunique() > 1

    def test_signals_vary_with_real_fred_data(self):
        """With real FRED data (if available), signal must vary per pair."""
        import pathlib

        rate_path = pathlib.Path("data/rates/rate_differentials.parquet")
        if not rate_path.exists():
            pytest.skip("Real FRED data not available")

        rate_data = pd.read_parquet(rate_path)
        dates = pd.bdate_range("2010-01-04", "2023-01-01", freq="B")
        rng = np.random.default_rng(99)
        base = 110.0 + np.cumsum(rng.normal(0, 0.5, len(dates)))
        ohlcv = pd.DataFrame(
            {
                "open": base,
                "high": base + 0.5,
                "low": base - 0.5,
                "close": base + rng.normal(0, 0.2, len(dates)),
                "volume": rng.integers(1000, 5000, len(dates)),
                "atr_14": np.abs(rng.normal(1.0, 0.3, len(dates))),
            },
            index=dates,
        )

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True},
            rate_data=rate_data,
        )
        signals = strategy.generate_signals(ohlcv)
        n_unique = signals.nunique()
        assert n_unique > 5, (
            f"USDJPY signals have only {n_unique} unique values — "
            "likely degenerate/stale FRED data"
        )


# ---------------------------------------------------------------------------
# Missing / sparse rate data
# ---------------------------------------------------------------------------

class TestMissingRateData:
    """Strategy must handle forward-fill of sparse (monthly) rate data."""

    def test_monthly_rate_data_forward_filled(self, ohlcv_data):
        """Monthly rate data (1 obs/month) forward-fills to all daily bars."""
        monthly_dates = pd.date_range("2020-01-01", "2022-01-01", freq="MS")
        n = len(monthly_dates)
        rng = np.random.default_rng(13)
        monthly_data = {
            col: rng.uniform(-0.02, 0.05, n)
            for col in [
                "AUDJPY_diff", "AUDUSD_diff", "CADJPY_diff", "EURGBP_diff",
                "EURJPY_diff", "EURUSD_diff", "GBPJPY_diff", "GBPUSD_diff",
                "NZDJPY_diff", "NZDUSD_diff", "USDCAD_diff", "USDJPY_diff",
            ]
        }
        rate_df = pd.DataFrame(monthly_data, index=monthly_dates)

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True, "min_differential": 0.0},
            rate_data=rate_df,
        )
        signals = strategy.generate_signals(ohlcv_data)

        # Should have no NaNs after forward-fill
        assert signals.isna().sum() == 0

    def test_nan_diff_produces_zero_signal(self, ohlcv_data):
        """If rate data can't be forward-filled (before first obs), signal=0."""
        # Create rate data that starts AFTER ohlcv start
        late_dates = pd.bdate_range("2021-01-01", periods=200)
        rate_df = _make_rate_data(late_dates)

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True},
            rate_data=rate_df,
        )
        signals = strategy.generate_signals(ohlcv_data)
        # First ~250 bars are before rate data — should be 0.0
        pre_rate_signals = signals[signals.index < pd.Timestamp("2021-01-01")]
        assert (pre_rate_signals == 0.0).all()


# ---------------------------------------------------------------------------
# Cross-sectional rank tests
# ---------------------------------------------------------------------------

class TestCrossSectionalRank:
    """Ranked signals reflect relative carry position."""

    def test_highest_carry_pair_gets_positive_signal(self, ohlcv_data):
        """The pair with the highest differential should get a positive z-score."""
        dates = ohlcv_data.index
        n = len(dates)
        # USDJPY has by far the highest carry (+10%)
        data = {c: np.full(n, 0.0) for c in [
            "AUDJPY_diff", "AUDUSD_diff", "CADJPY_diff", "EURGBP_diff",
            "EURJPY_diff", "EURUSD_diff", "GBPJPY_diff", "GBPUSD_diff",
            "NZDJPY_diff", "NZDUSD_diff", "USDCAD_diff",
        ]}
        data["USDJPY_diff"] = np.full(n, 0.10)  # highest
        rate_df = pd.DataFrame(data, index=dates)

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True, "min_differential": 0.0},
            rate_data=rate_df,
        )
        signals = strategy.generate_signals(ohlcv_data)
        # USDJPY should be positive (it's the highest-carry pair)
        assert (signals > 0).all()

    def test_lowest_carry_pair_gets_negative_signal(self, ohlcv_data):
        """The pair with the lowest (most negative) differential should be short."""
        dates = ohlcv_data.index
        n = len(dates)
        data = {c: np.full(n, 0.0) for c in [
            "AUDJPY_diff", "AUDUSD_diff", "CADJPY_diff", "EURGBP_diff",
            "EURJPY_diff", "EURUSD_diff", "GBPJPY_diff", "GBPUSD_diff",
            "NZDJPY_diff", "NZDUSD_diff", "USDCAD_diff",
        ]}
        data["USDJPY_diff"] = np.full(n, -0.10)  # lowest
        rate_df = pd.DataFrame(data, index=dates)

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True, "min_differential": 0.0},
            rate_data=rate_df,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert (signals < 0).all()

    def test_min_differential_zeros_out_small_carry(self, ohlcv_data):
        """min_differential filter zeros out near-zero rate differentials."""
        dates = ohlcv_data.index
        n = len(dates)
        data = {c: np.full(n, 0.0002) for c in [
            "AUDJPY_diff", "AUDUSD_diff", "CADJPY_diff", "EURGBP_diff",
            "EURJPY_diff", "EURUSD_diff", "GBPJPY_diff", "GBPUSD_diff",
            "NZDJPY_diff", "NZDUSD_diff", "USDCAD_diff", "USDJPY_diff",
        ]}
        rate_df = pd.DataFrame(data, index=dates)

        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True, "min_differential": 0.001},
            rate_data=rate_df,
        )
        signals = strategy.generate_signals(ohlcv_data)
        assert (signals == 0.0).all()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Invalid inputs raise descriptive errors."""

    def test_unknown_pair_raises(self, ohlcv_data, rate_data):
        strategy = CarryFREDStrategy({"pair": "XYZABC"}, rate_data=rate_data)
        with pytest.raises(ValueError, match="unknown pair"):
            strategy.generate_signals(ohlcv_data)

    def test_missing_pair_param_raises(self, ohlcv_data, rate_data):
        strategy = CarryFREDStrategy({}, rate_data=rate_data)
        with pytest.raises(ValueError, match="'pair' param is required"):
            strategy.generate_signals(ohlcv_data)

    def test_col_not_in_rate_data_raises(self, ohlcv_data):
        """If column not in provided rate_data, raise ValueError."""
        # Rate data with only 1 column (USDJPY_diff missing EURUSD_diff etc.)
        dates = ohlcv_data.index
        tiny_rate = pd.DataFrame({"USDJPY_diff": np.full(len(dates), 0.02)}, index=dates)
        strategy = CarryFREDStrategy(
            {"pair": "EURUSD", "rank_normalize": False},
            rate_data=tiny_rate,
        )
        with pytest.raises(ValueError, match="not found in rate_data"):
            strategy.generate_signals(ohlcv_data)


# ---------------------------------------------------------------------------
# No-lookahead test
# ---------------------------------------------------------------------------

class TestNoLookahead:
    """Partial data signals must match the prefix of full data signals."""

    def test_no_lookahead_ranked(self, ohlcv_data, rate_data):
        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": True},
            rate_data=rate_data,
        )
        full_signals = strategy.generate_signals(ohlcv_data)
        partial_signals = strategy.generate_signals(ohlcv_data.iloc[:250])

        pd.testing.assert_series_equal(
            partial_signals,
            full_signals.iloc[:250],
            check_names=False,
        )

    def test_no_lookahead_raw(self, ohlcv_data, rate_data):
        strategy = CarryFREDStrategy(
            {"pair": "USDJPY", "rank_normalize": False},
            rate_data=rate_data,
        )
        full_signals = strategy.generate_signals(ohlcv_data)
        partial_signals = strategy.generate_signals(ohlcv_data.iloc[:250])

        pd.testing.assert_series_equal(
            partial_signals,
            full_signals.iloc[:250],
            check_names=False,
        )


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestRegistry:
    """Registry integration for carry_fred."""

    def test_factory_creates_carry_fred(self):
        strategy = create_strategy("carry_fred", {"pair": "USDJPY"})
        assert strategy.name == "carry_fred"
        assert isinstance(strategy, CarryFREDStrategy)

    def test_strategy_name_property(self):
        strategy = CarryFREDStrategy({"pair": "AUDUSD"})
        assert strategy.name == "carry_fred"

    def test_required_indicators(self):
        strategy = CarryFREDStrategy({"pair": "USDJPY"})
        assert "atr_14" in strategy.required_indicators()
