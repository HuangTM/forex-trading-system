"""Tests for VolTargetCarryNoVolScalingStrategy — Wave-5 Round-2 ablation.

Covers:
- Signal bounds: output always 1.0 (constant long, no vol-targeting)
- Signal is NOT proportional to volatility (unlike vol_target_carry)
- Required indicators preserved for interface compatibility
- Carry filter gate suppresses signal when rate below min_carry threshold
- Registry lookup resolves the strategy by name
- Name property returns the correct strategy ID
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex_system.strategies.vol_target_carry_no_vol_scaling import (
    VolTargetCarryNoVolScalingStrategy,
)


def _make_daily_ohlcv(n: int = 500, trend: float = 0.0, vol: float = 0.01) -> pd.DataFrame:
    """Synthetic daily OHLCV with configurable vol."""
    rng = np.random.default_rng(99)
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
            "atr_14": close * 0.005,
        },
        index=dates,
    )


class TestSignalIsConstant:
    """Without vol-targeting, the signal must be constant 1.0 (no vol scaling)."""

    def test_signals_always_one_calm_market(self):
        """In a calm market, signal stays at 1.0 (not upsized above 1.0 or scaled)."""
        strategy = VolTargetCarryNoVolScalingStrategy({"pair": "USDJPY"})
        df = _make_daily_ohlcv(n=400, vol=0.002)
        signals = strategy.generate_signals(df)

        assert (signals == 1.0).all(), (
            "Signal must be exactly 1.0 everywhere (no vol scaling)"
        )

    def test_signals_always_one_choppy_market(self):
        """In a choppy market, signal must still be 1.0 (vol scaling removed)."""
        strategy = VolTargetCarryNoVolScalingStrategy({"pair": "USDJPY"})
        df = _make_daily_ohlcv(n=400, vol=0.05)
        signals = strategy.generate_signals(df)

        assert (signals == 1.0).all(), (
            "Signal must be 1.0 even in high-vol market — no vol-targeting applied"
        )

    def test_signal_does_not_vary_with_vol(self):
        """Key ablation property: signal must be identical regardless of realized vol."""
        strategy = VolTargetCarryNoVolScalingStrategy({"pair": "USDJPY"})
        df_calm = _make_daily_ohlcv(n=300, vol=0.001)
        df_choppy = _make_daily_ohlcv(n=300, vol=0.10)

        sig_calm = strategy.generate_signals(df_calm)
        sig_choppy = strategy.generate_signals(df_choppy)

        assert (sig_calm == 1.0).all()
        assert (sig_choppy == 1.0).all()
        # Both must be identical: ablation removes vol-sensitivity.
        pd.testing.assert_series_equal(sig_calm, sig_choppy)


class TestCarryFilter:
    """Carry filter (min_carry gate) must be preserved from vol_target_carry."""

    def test_carry_filter_suppresses_signal_below_threshold(self):
        """When rate < min_carry, signal = 0.0 (same behavior as vol_target_carry)."""
        strategy = VolTargetCarryNoVolScalingStrategy(
            {"pair": "USDJPY", "min_carry": 0.01},
        )
        df = _make_daily_ohlcv(n=300)
        # Rate always below min_carry → all signals suppressed.
        rate_data = pd.DataFrame(
            {"USDJPY": np.full(len(df), 0.005)},  # 0.005 < 0.01 threshold
            index=df.index,
        )
        strategy.rate_data = rate_data
        signals = strategy.generate_signals(df)

        assert (signals == 0.0).all(), (
            "Carry filter must suppress signal when rate < min_carry"
        )

    def test_carry_filter_passes_signal_above_threshold(self):
        """When rate >= min_carry, signal = 1.0 (filter does not suppress)."""
        strategy = VolTargetCarryNoVolScalingStrategy(
            {"pair": "USDJPY", "min_carry": 0.01},
        )
        df = _make_daily_ohlcv(n=300)
        rate_data = pd.DataFrame(
            {"USDJPY": np.full(len(df), 0.02)},  # 0.02 >= 0.01 → pass
            index=df.index,
        )
        strategy.rate_data = rate_data
        signals = strategy.generate_signals(df)

        assert (signals == 1.0).all(), (
            "Signal must be 1.0 when rate >= min_carry (carry filter passes)"
        )


class TestInterfaceContract:
    """Strategy interface contract: name, required_indicators, registration."""

    def test_strategy_name(self):
        strategy = VolTargetCarryNoVolScalingStrategy({"pair": "USDJPY"})
        assert strategy.name == "vol_target_carry_no_vol_scaling"

    def test_required_indicators_includes_atr_14(self):
        """required_indicators must include atr_14 for interface compatibility."""
        strategy = VolTargetCarryNoVolScalingStrategy({"pair": "USDJPY"})
        assert "atr_14" in strategy.required_indicators()

    def test_registry_lookup(self):
        """Strategy must be findable in STRATEGY_REGISTRY by its name."""
        from forex_system.strategies.registry import STRATEGY_REGISTRY
        assert "vol_target_carry_no_vol_scaling" in STRATEGY_REGISTRY
        cls = STRATEGY_REGISTRY["vol_target_carry_no_vol_scaling"]
        assert cls is VolTargetCarryNoVolScalingStrategy

    def test_validated_module_not_modified(self):
        """vol_target_carry.py must not be touched — ablation lives in its own module.

        In high-vol regime (vol=0.05, target_vol=0.10), vol_target_carry produces
        signals < 1.0 (vol > target → downsize). The ablation always returns 1.0.
        This confirms the validated module was not overwritten.
        """
        from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy
        s = VolTargetCarryStrategy(
            {"target_vol": 0.10, "vol_window": 20, "leverage_cap": 2.0}
        )
        # High vol (5% daily) → realized_vol >> target_vol=10% → signals < 1.0
        df = _make_daily_ohlcv(n=300, vol=0.05)
        sig = s.generate_signals(df)
        post_warmup = sig.iloc[25:]
        # vol_target_carry in high-vol regime must produce values < 1.0.
        # If it produced all 1.0, the ablation would have replaced the validated module.
        assert not (post_warmup == 1.0).all(), (
            "vol_target_carry in high-vol regime must produce signals < 1.0; "
            "all-1.0 suggests ablation accidentally replaced the validated module"
        )
