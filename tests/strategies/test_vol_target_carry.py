"""Tests for VolTargetCarryStrategy — C2 pre-req for Path A.

Covers:
- Signal bounds: output always in [0, 1] (long-only)
- Zero-vol guard: NaN realized vol doesn't produce infinite signal
- Leverage cap clamp: signal never exceeds 1.0 regardless of vol ratio
- Carry filter: min_carry gate suppresses signal when rate below threshold
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy


def _make_daily_ohlcv(n: int = 500, trend: float = 0.0, vol: float = 0.01) -> pd.DataFrame:
    """Synthetic daily OHLCV with configurable vol."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    returns = rng.normal(trend, vol, n)
    close = pd.Series(100.0 * np.exp(np.cumsum(returns)), index=dates)
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.002,
            "low": close * 0.998,
            "close": close,
            "volume": 1_000_000,
            "atr_14": close * 0.005,  # 0.5% ATR — satisfies required_indicators
        },
        index=dates,
    )


class TestSignalBounds:
    """Signal must be in [0, 1] — long-only invariant."""

    def test_signals_in_unit_range_calm_market(self):
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 20, "leverage_cap": 2.0}
        )
        df = _make_daily_ohlcv(n=300, vol=0.005)  # Very calm → upsize toward 1.0
        signals = strategy.generate_signals(df)

        post_warmup = signals.iloc[25:]  # Skip first vol_window bars
        assert (post_warmup >= 0.0).all(), "Signal must be >= 0 (long-only)"
        assert (post_warmup <= 1.0).all(), "Signal must be <= 1.0"

    def test_signals_in_unit_range_choppy_market(self):
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 20, "leverage_cap": 2.0}
        )
        df = _make_daily_ohlcv(n=300, vol=0.05)  # High vol → downsize toward 0
        signals = strategy.generate_signals(df)

        post_warmup = signals.iloc[25:]
        assert (post_warmup >= 0.0).all(), "Signal must be >= 0 in choppy market"
        assert (post_warmup <= 1.0).all(), "Signal must be <= 1.0 in choppy market"

    def test_signal_never_negative(self):
        """Long-only: even extreme downside vol must not produce negative signal."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.01, "vol_window": 20, "leverage_cap": 3.0}
        )
        df = _make_daily_ohlcv(n=200, vol=0.10)  # Very high vol
        signals = strategy.generate_signals(df)
        assert (signals >= 0.0).all(), "Signal must never be negative (long-only)"


class TestZeroVolGuard:
    """Zero or NaN realized vol must not produce infinite or NaN signal."""

    def test_zero_vol_returns_zero_not_inf(self):
        """Perfectly flat price → zero pct_change → zero vol → signal = 0 (not inf)."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 10, "leverage_cap": 2.0}
        )
        dates = pd.bdate_range("2020-01-01", periods=50, freq="B")
        # Completely flat price — realized vol = 0
        close = pd.Series(100.0, index=dates)
        df = pd.DataFrame(
            {
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1_000_000,
                "atr_14": 0.5,
            },
            index=dates,
        )
        signals = strategy.generate_signals(df)

        assert not signals.isnull().any(), "Signal must not be NaN when vol is zero"
        assert not np.isinf(signals).any(), "Signal must not be inf when vol is zero"
        assert (signals >= 0.0).all()
        assert (signals <= 1.0).all()

    def test_insufficient_data_returns_zero_not_nan(self):
        """With fewer bars than vol_window, warmup bars should be 0.0, not NaN."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 252, "leverage_cap": 2.0}
        )
        df = _make_daily_ohlcv(n=50)  # Far fewer than vol_window=252
        signals = strategy.generate_signals(df)

        assert not signals.isnull().any(), "Signal must not be NaN during warmup"
        assert (signals >= 0.0).all()
        assert (signals <= 1.0).all()


class TestLeverageCapClamp:
    """Signal may not exceed 1.0 even when target_vol >> realized_vol."""

    def test_low_vol_does_not_exceed_unit(self):
        """Extremely calm market: target_vol/realized_vol >> leverage_cap → signal = 1.0."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.50, "vol_window": 20, "leverage_cap": 2.0}
        )
        df = _make_daily_ohlcv(n=200, vol=0.0005)  # Tiny vol → ratio = 0.50/~0.008 >> 2.0
        signals = strategy.generate_signals(df)

        post_warmup = signals.iloc[25:]
        assert (post_warmup <= 1.0).all(), "Signal must be clipped at 1.0 (leverage_cap / leverage_cap)"

    def test_leverage_cap_param_respected(self):
        """leverage_cap=1.0 means full position is never more than 1x notional."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.50, "vol_window": 20, "leverage_cap": 1.0}
        )
        df = _make_daily_ohlcv(n=200, vol=0.001)
        signals = strategy.generate_signals(df)

        post_warmup = signals.iloc[25:]
        assert (post_warmup <= 1.0).all()

    def test_different_leverage_caps_scale_consistently(self):
        """Higher leverage_cap should not change signal range (always [0,1])."""
        for cap in [1.0, 2.0, 3.0, 5.0]:
            strategy = VolTargetCarryStrategy(
                {"target_vol": 0.10, "vol_window": 20, "leverage_cap": cap}
            )
            df = _make_daily_ohlcv(n=200, vol=0.01)
            signals = strategy.generate_signals(df)
            post_warmup = signals.iloc[25:]
            assert (post_warmup >= 0.0).all(), f"cap={cap}: signal < 0"
            assert (post_warmup <= 1.0).all(), f"cap={cap}: signal > 1"


class TestMinCarryFilter:
    """min_carry gate: signals should be 0 when carry < threshold."""

    def test_carry_filter_suppresses_signal(self):
        """When carry rate is always below min_carry, all signals should be 0."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 20, "leverage_cap": 2.0,
             "min_carry": 0.05, "pair": "USDJPY"}
        )
        df = _make_daily_ohlcv(n=200, vol=0.01)
        # Rate always below threshold (0.01 < 0.05)
        rate_data = pd.DataFrame({"USDJPY": 0.01}, index=df.index)
        strategy.rate_data = rate_data
        signals = strategy.generate_signals(df)

        post_warmup = signals.iloc[25:]
        assert (post_warmup == 0.0).all(), "All signals should be 0 when carry below threshold"

    def test_carry_filter_passes_signal_when_rate_above(self):
        """When carry rate is always above min_carry, carry filter has no effect."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 20, "leverage_cap": 2.0,
             "min_carry": 0.01, "pair": "USDJPY"}
        )
        df = _make_daily_ohlcv(n=200, vol=0.01)
        # Rate always above threshold (0.10 > 0.01)
        rate_data = pd.DataFrame({"USDJPY": 0.10}, index=df.index)
        strategy.rate_data = rate_data
        signals = strategy.generate_signals(df)

        post_warmup = signals.iloc[25:]
        assert (post_warmup > 0.0).any(), "Signals should be non-zero when carry above threshold"

    def test_no_rate_data_no_carry_filter(self):
        """With rate_data=None, carry filter is skipped — signal proceeds normally."""
        strategy = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 20, "leverage_cap": 2.0,
             "min_carry": 0.99}  # Would suppress if active
        )
        # rate_data is None by default — no filter applied
        df = _make_daily_ohlcv(n=200, vol=0.01)
        signals = strategy.generate_signals(df)

        post_warmup = signals.iloc[25:]
        assert (post_warmup > 0.0).any(), "Without rate_data, carry filter should not suppress"
