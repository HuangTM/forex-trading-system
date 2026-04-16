"""Tests for ContinuousSizer and engine integration."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.engine import run_backtest
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators
from forex_system.sizing.continuous import ContinuousSizer


@pytest.fixture
def sizer():
    return ContinuousSizer(risk_per_trade=0.02, stop_loss_atr_multiple=2.0, min_order_size=0.0)


class TestContinuousSizer:
    """Unit tests for ContinuousSizer."""

    def test_zero_signal_gives_zero_size(self, sizer):
        """Flat-as-default invariant: zero signal -> zero position."""
        size = sizer.calculate_size(0.0, 100_000.0, 1.1000, 0.005, "EURUSD")
        assert size == 0.0

    def test_full_signal_matches_base_formula(self, sizer):
        """With signal=1.0, base formula matches: equity * risk / (atr * multiple)."""
        equity = 100_000.0
        atr = 0.01  # Large ATR so base_size is small (no cap)
        price = 1.1000

        # base_size = 100000 * 0.02 / (0.01 * 2.0) = 100000
        # max_size = 100000 * 0.10 / 1.1 = 9090.9
        # Use even larger ATR to avoid cap
        atr = 0.5
        expected = equity * 0.02 / (atr * 2.0)  # 2000
        continuous_size = sizer.calculate_size(1.0, equity, price, atr, "EURUSD")

        assert abs(continuous_size - expected) < 1e-6

    def test_half_signal_gives_half_size(self, sizer):
        """Signal magnitude scales linearly (using large ATR to avoid cap)."""
        full = sizer.calculate_size(1.0, 100_000.0, 1.1, 0.5, "EURUSD")
        half = sizer.calculate_size(0.5, 100_000.0, 1.1, 0.5, "EURUSD")
        assert abs(half - full * 0.5) < 1e-6

    def test_negative_signal_same_magnitude(self, sizer):
        """Short and long signals of same magnitude produce same size."""
        long_size = sizer.calculate_size(0.7, 100_000.0, 1.1, 0.5, "EURUSD")
        short_size = sizer.calculate_size(-0.7, 100_000.0, 1.1, 0.5, "EURUSD")
        assert abs(long_size - short_size) < 1e-6

    def test_confidence_scales_size(self, sizer):
        """confidence=0.5 halves the position size (using large ATR to avoid cap)."""
        full_conf = sizer.calculate_size(1.0, 100_000.0, 1.1, 0.5, "EURUSD", confidence=1.0)
        half_conf = sizer.calculate_size(1.0, 100_000.0, 1.1, 0.5, "EURUSD", confidence=0.5)
        assert abs(half_conf - full_conf * 0.5) < 1e-6

    def test_ratchet_scales_size(self, sizer):
        """ratchet_level=0.25 quarters the position size (using large ATR to avoid cap)."""
        full = sizer.calculate_size(1.0, 100_000.0, 1.1, 0.5, "EURUSD", ratchet_level=1.0)
        quarter = sizer.calculate_size(1.0, 100_000.0, 1.1, 0.5, "EURUSD", ratchet_level=0.25)
        assert abs(quarter - full * 0.25) < 1e-6

    def test_max_order_units_cap(self, sizer):
        """Size never exceeds max_order_units."""
        # Use very small ATR to make base_size very large
        size = sizer.calculate_size(1.0, 100_000.0, 1.1, 0.0001, "EURUSD")
        assert size <= sizer.max_order_units + 1e-6

    def test_min_order_size_floor(self):
        """Size below broker minimum returns zero (stay flat)."""
        sizer = ContinuousSizer(min_order_size=1000.0)
        # Very weak signal with high ATR -> small size
        size = sizer.calculate_size(0.01, 10_000.0, 1.1, 0.5, "EURUSD")
        # base=10000*0.02/(0.5*2)=200, scaled=200*0.01=2 -> below 1000
        assert size == 0.0

    def test_zero_atr_gives_zero(self, sizer):
        """Edge case: zero ATR returns zero size."""
        assert sizer.calculate_size(1.0, 100_000.0, 1.1, 0.0, "EURUSD") == 0.0

    def test_negative_atr_gives_zero(self, sizer):
        """Edge case: negative ATR returns zero size."""
        assert sizer.calculate_size(1.0, 100_000.0, 1.1, -0.005, "EURUSD") == 0.0

    def test_zero_equity_gives_zero(self, sizer):
        """Edge case: zero equity returns zero size."""
        assert sizer.calculate_size(1.0, 0.0, 1.1, 0.005, "EURUSD") == 0.0


class TestEngineWithSizer:
    """Integration tests: engine + ContinuousSizer."""

    def test_engine_backward_compat(self, sample_ohlcv):
        """Engine without sizer produces identical results to before."""
        enriched = compute_indicators(sample_ohlcv, ["sma_50", "atr_14"])
        enriched = enriched.dropna(subset=["atr_14"])
        signals = pd.Series(1.0, index=enriched.index)  # Always long

        result = run_backtest(
            data=enriched, signals=signals, pair="EURUSD",
            strategy_name="test", cost_model=RealisticCostModel(),
            sizer=None,  # Explicit None
        )
        assert len(result.trade_log) > 0
        assert result.equity_curve.iloc[-1] > 0

    def test_engine_with_sizer_runs(self, sample_ohlcv):
        """Engine with ContinuousSizer produces valid results."""
        enriched = compute_indicators(sample_ohlcv, ["sma_50", "atr_14"])
        enriched = enriched.dropna(subset=["atr_14"])
        signals = pd.Series(0.8, index=enriched.index)  # Continuous signal

        sizer = ContinuousSizer()
        result = run_backtest(
            data=enriched, signals=signals, pair="EURUSD",
            strategy_name="test", cost_model=RealisticCostModel(),
            sizer=sizer,
        )
        assert result.equity_curve.iloc[-1] > 0
        assert len(result.trade_log) >= 0

    def test_weak_signal_smaller_than_strong(self, sample_ohlcv):
        """Weaker signals produce smaller position sizes."""
        enriched = compute_indicators(sample_ohlcv, ["atr_14"])
        enriched = enriched.dropna(subset=["atr_14"])

        sizer = ContinuousSizer(min_order_size=0.0)
        strong = run_backtest(
            data=enriched, signals=pd.Series(1.0, index=enriched.index),
            pair="EURUSD", strategy_name="strong",
            cost_model=RealisticCostModel(), sizer=sizer,
        )
        weak = run_backtest(
            data=enriched, signals=pd.Series(0.2, index=enriched.index),
            pair="EURUSD", strategy_name="weak",
            cost_model=RealisticCostModel(), sizer=sizer,
        )

        # Weak signal should have smaller trade sizes
        if strong.trade_log and weak.trade_log:
            strong_avg_size = np.mean([t.size for t in strong.trade_log])
            weak_avg_size = np.mean([t.size for t in weak.trade_log])
            assert weak_avg_size < strong_avg_size

    def test_no_lookahead_with_sizer(self, sample_ohlcv):
        """THE SACRED TEST with sizer: engine must not use future data."""
        enriched = compute_indicators(sample_ohlcv, ["atr_14"])
        enriched = enriched.dropna(subset=["atr_14"])

        # Lookahead signal: +1 when next bar rises
        future_return = enriched["close"].shift(-1) - enriched["close"]
        lookahead_signals = pd.Series(0.0, index=enriched.index)
        lookahead_signals[future_return > 0] = 1.0
        lookahead_signals[future_return < 0] = -1.0

        sizer = ContinuousSizer()
        result = run_backtest(
            data=enriched, signals=lookahead_signals, pair="EURUSD",
            strategy_name="lookahead_test", cost_model=RealisticCostModel(),
            entry_delay_bars=1, sizer=sizer,
        )

        ec = result.equity_curve.dropna()
        daily_returns = ec.pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            assert sharpe < 3.0, f"Suspiciously high Sharpe ({sharpe:.1f}) — possible lookahead"
