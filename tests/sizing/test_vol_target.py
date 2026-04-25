"""Tests for VolTargetSizer — C2 pre-req for Path A.

Covers:
- Signal bounds: positive signals produce valid sizes
- Zero-vol guard: zero/negative signal → 0 size (long-only)
- Leverage cap clamp: signal=1.0 produces leverage_cap × equity (USD nominal)
- min_order_size boundary: sub-minimum signal returns 0.0
- max_order_units hard cap: never exceeded
- Output is USD nominal (Saxo FX convention): no price division here;
  the backtest engine applies the quote-currency correction for JPY pairs.
"""

from __future__ import annotations

import pytest

from forex_system.sizing.vol_target import VolTargetSizer


@pytest.fixture
def sizer():
    return VolTargetSizer(
        leverage_cap=2.0,
        max_order_units=5_000_000.0,
        min_order_size=1_000.0,
    )


class TestSignalBounds:
    """Positive signals within [0, 1] should produce proportional sizes."""

    def test_full_signal_produces_max_size(self, sizer):
        """signal=1.0 → leverage_cap × equity (USD nominal)."""
        equity = 100_000.0
        size = sizer.calculate_size(1.0, equity, 150.0, 0.5, "USDJPY")
        expected = 1.0 * sizer.leverage_cap * equity  # = 200_000
        assert abs(size - expected) < 1e-6

    def test_half_signal_gives_half_size(self, sizer):
        """signal=0.5 → half of signal=1.0."""
        equity = 100_000.0
        full = sizer.calculate_size(1.0, equity, 150.0, 0.5, "USDJPY")
        half = sizer.calculate_size(0.5, equity, 150.0, 0.5, "USDJPY")
        assert abs(half - full * 0.5) < 1e-6

    def test_zero_signal_gives_zero(self, sizer):
        """signal=0.0 → flat (long-only, no short)."""
        size = sizer.calculate_size(0.0, 100_000.0, 150.0, 0.5, "USDJPY")
        assert size == 0.0


class TestLongOnlyGuard:
    """Negative and zero signals must produce 0 (no short positions)."""

    def test_negative_signal_gives_zero(self, sizer):
        size = sizer.calculate_size(-0.5, 100_000.0, 150.0, 0.5, "USDJPY")
        assert size == 0.0

    def test_minus_one_signal_gives_zero(self, sizer):
        size = sizer.calculate_size(-1.0, 100_000.0, 150.0, 0.5, "USDJPY")
        assert size == 0.0

    def test_very_small_negative_gives_zero(self, sizer):
        size = sizer.calculate_size(-1e-9, 100_000.0, 150.0, 0.5, "USDJPY")
        assert size == 0.0


class TestZeroInputGuards:
    """Zero equity or zero price must return 0 without error."""

    def test_zero_equity_gives_zero(self, sizer):
        size = sizer.calculate_size(1.0, 0.0, 150.0, 0.5, "USDJPY")
        assert size == 0.0

    def test_zero_price_gives_zero(self, sizer):
        size = sizer.calculate_size(1.0, 100_000.0, 0.0, 0.5, "USDJPY")
        assert size == 0.0

    def test_negative_equity_gives_zero(self, sizer):
        size = sizer.calculate_size(1.0, -100_000.0, 150.0, 0.5, "USDJPY")
        assert size == 0.0


class TestMinOrderSizeBoundary:
    """Sub-minimum size returns 0 (broker minimum enforcement)."""

    def test_very_weak_signal_below_min_returns_zero(self):
        sizer = VolTargetSizer(leverage_cap=2.0, max_order_units=5_000_000.0, min_order_size=1_000.0)
        # equity=1000, signal=0.001, cap=2 → 1000*0.001*2 = 2 < 1000
        size = sizer.calculate_size(0.001, 1_000.0, 150.0, 0.5, "USDJPY")
        assert size == 0.0

    def test_exactly_at_min_returns_nonzero(self):
        """Exactly at min_order_size threshold: code checks `units < min`, so == min passes."""
        sizer = VolTargetSizer(leverage_cap=2.0, max_order_units=5_000_000.0, min_order_size=1_000.0)
        # equity=1000, signal=0.5, cap=2 → 1000*0.5*2 = 1000 == min_order_size
        # Code: `if units < min_order_size` → 1000 < 1000 is False → returns 1000
        size = sizer.calculate_size(0.5, 1_000.0, 150.0, 0.5, "USDJPY")
        assert size == 1_000.0  # At boundary (not below): returns the size

        # One above the boundary: returns 0
        sizer2 = VolTargetSizer(leverage_cap=2.0, max_order_units=5_000_000.0, min_order_size=1_001.0)
        size2 = sizer2.calculate_size(0.5, 1_000.0, 150.0, 0.5, "USDJPY")
        assert size2 == 0.0  # 1000 < 1001 → stay flat

    def test_min_order_size_zero_allows_any_positive(self):
        """min_order_size=0 means even tiny sizes are returned."""
        sizer = VolTargetSizer(leverage_cap=2.0, max_order_units=5_000_000.0, min_order_size=0.0)
        size = sizer.calculate_size(0.0001, 100.0, 150.0, 0.5, "USDJPY")
        assert size > 0.0


class TestMaxOrderUnitsCap:
    """Hard cap on position size must never be exceeded."""

    def test_max_units_cap_enforced(self):
        """Large equity + signal=1.0 must not exceed max_order_units."""
        sizer = VolTargetSizer(leverage_cap=2.0, max_order_units=1_000_000.0, min_order_size=0.0)
        # equity=10M * signal=1.0 * cap=2 = 20M > max=1M
        size = sizer.calculate_size(1.0, 10_000_000.0, 150.0, 0.5, "USDJPY")
        assert size == 1_000_000.0

    def test_normal_size_not_artificially_capped(self, sizer):
        """When natural size is below cap, cap doesn't interfere."""
        # equity=100k, signal=1.0, cap=2 → 200k < 5M cap
        size = sizer.calculate_size(1.0, 100_000.0, 150.0, 0.5, "USDJPY")
        assert size == 200_000.0


class TestConfidenceAndRatchet:
    """confidence and ratchet_level scale the output multiplicatively."""

    def test_confidence_half_halves_size(self, sizer):
        full = sizer.calculate_size(1.0, 100_000.0, 150.0, 0.5, "USDJPY", confidence=1.0)
        half_conf = sizer.calculate_size(1.0, 100_000.0, 150.0, 0.5, "USDJPY", confidence=0.5)
        assert abs(half_conf - full * 0.5) < 1e-6

    def test_ratchet_quarter_quarters_size(self, sizer):
        full = sizer.calculate_size(1.0, 100_000.0, 150.0, 0.5, "USDJPY", ratchet_level=1.0)
        quarter = sizer.calculate_size(1.0, 100_000.0, 150.0, 0.5, "USDJPY", ratchet_level=0.25)
        assert abs(quarter - full * 0.25) < 1e-6
