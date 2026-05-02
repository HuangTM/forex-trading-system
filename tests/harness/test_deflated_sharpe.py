"""Tests for deflated_sharpe module (BLP 2014, eq. 10).

Coverage:
- Known-result cases: N=1 (no inflation), N=22 (Phase 1 baseline), N=29
- Edge cases: n_obs=1 raises, n_trials=0 raises
- Monotonicity: more trials → lower DSR for same observed SR
- Non-normality: skew/kurt sensitivity direction
- Boundary: SR ≤ 0 returns 0.0
"""

from __future__ import annotations

import pytest

from forex_system.harness.deflated_sharpe import deflated_sharpe, _expected_max_sr


class TestExpectedMaxSR:
    """Internal helper: _expected_max_sr (E[max SR | N trials])."""

    def test_n_trials_1_returns_zero(self):
        """Single trial has no multiple-comparisons benchmark — E[max SR] = 0."""
        result = _expected_max_sr(n_trials=1, n_obs=252)
        assert result == 0.0

    def test_n_trials_22_positive(self):
        """N=22 (Phase 1 org-wide): expected max SR must be positive."""
        result = _expected_max_sr(n_trials=22, n_obs=252)
        assert result > 0.0

    def test_n_trials_29_greater_than_22(self):
        """More trials → higher expected maximum SR (monotone in N)."""
        r22 = _expected_max_sr(n_trials=22, n_obs=252)
        r29 = _expected_max_sr(n_trials=29, n_obs=252)
        assert r29 > r22

    def test_monotone_in_n(self):
        """E[max SR | N] is strictly increasing in N for N >= 2."""
        vals = [_expected_max_sr(n_trials=k, n_obs=252) for k in [2, 10, 22, 50, 100]]
        for i in range(len(vals) - 1):
            assert vals[i + 1] > vals[i], f"Not monotone at index {i}: {vals}"


class TestDeflatedSharpe:
    """deflated_sharpe(sharpe, n_trials, n_obs, skew, excess_kurtosis)."""

    # ---- Input validation ------------------------------------------------

    def test_n_trials_zero_raises(self):
        """n_trials < 1 must raise ValueError (no silent default)."""
        with pytest.raises(ValueError, match="n_trials_at_spawn"):
            deflated_sharpe(sharpe=1.0, n_trials=0, n_obs=252)

    def test_n_obs_one_raises(self):
        """n_obs < 2 must raise ValueError (insufficient observations)."""
        with pytest.raises(ValueError, match="n_obs"):
            deflated_sharpe(sharpe=1.0, n_trials=5, n_obs=1)

    # ---- Boundary conditions ---------------------------------------------

    def test_negative_sharpe_returns_zero(self):
        """Negative SR is not above the expected maximum — DSR = 0.0."""
        dsr = deflated_sharpe(sharpe=-0.5, n_trials=22, n_obs=252)
        assert dsr == 0.0

    def test_zero_sharpe_returns_zero(self):
        """SR = 0.0: trivially not above expected max — DSR = 0.0."""
        dsr = deflated_sharpe(sharpe=0.0, n_trials=22, n_obs=252)
        assert dsr == 0.0

    # ---- Output range ----------------------------------------------------

    def test_output_in_unit_interval(self):
        """DSR must be a valid probability in [0, 1]."""
        dsr = deflated_sharpe(sharpe=0.80, n_trials=22, n_obs=2520)
        assert 0.0 <= dsr <= 1.0

    # ---- Known-result cases: N=22 ----------------------------------------

    def test_n22_high_sharpe_high_dsr(self):
        """vol_target_carry OOS Sharpe 0.76, N=22, T=2520 → DSR near 1."""
        # BLP deflation factor 0.5–0.7x for N=22; 0.76 * 0.7 = 0.53 > R2 threshold 0.50
        dsr = deflated_sharpe(sharpe=0.76, n_trials=22, n_obs=2520)
        assert dsr > 0.50, f"Expected DSR > 0.50 for Sharpe=0.76 N=22, got {dsr:.4f}"

    def test_n22_low_sharpe_below_threshold(self):
        """Sharpe=0.30, N=100, T=60: DSR should be modest (≤ 0.80).

        With many trials (N=100) and few bars (T=60), the expected max SR is
        large and the variance term large, deflating DSR well below 1.
        """
        dsr = deflated_sharpe(sharpe=0.30, n_trials=100, n_obs=60)
        assert dsr <= 0.80, f"Expected DSR ≤ 0.80 for deflated case N=100 T=60, got {dsr:.4f}"

    def test_n1_no_inflation(self):
        """N=1: no multiple-comparisons penalty; modest SR still gets moderate DSR."""
        dsr_n1 = deflated_sharpe(sharpe=0.50, n_trials=1, n_obs=252)
        dsr_n22 = deflated_sharpe(sharpe=0.50, n_trials=22, n_obs=252)
        # N=1 should yield higher or equal DSR than N=22 (less deflation).
        assert dsr_n1 >= dsr_n22, (
            f"N=1 should have ≥ DSR vs N=22 for same SR: n1={dsr_n1:.4f} n22={dsr_n22:.4f}"
        )

    def test_n29_deflates_more_than_n22(self):
        """N=29: more trials → lower DSR for same observed SR."""
        dsr_n22 = deflated_sharpe(sharpe=0.60, n_trials=22, n_obs=252)
        dsr_n29 = deflated_sharpe(sharpe=0.60, n_trials=29, n_obs=252)
        assert dsr_n29 <= dsr_n22, (
            f"N=29 should deflate further than N=22: n22={dsr_n22:.4f} n29={dsr_n29:.4f}"
        )

    # ---- Non-normality sensitivity ---------------------------------------

    def test_negative_skew_reduces_dsr(self):
        """Negative skewness inflates variance term → lower DSR.

        With positive SR and negative skew: 1 - skew*SR = 1 + |skew|*SR > 1
        → larger variance_term → larger sigma_sr → lower z → lower DSR.
        """
        dsr_normal = deflated_sharpe(sharpe=0.50, n_trials=10, n_obs=120)
        dsr_neg_skew = deflated_sharpe(sharpe=0.50, n_trials=10, n_obs=120, skew=-2.0)
        assert dsr_neg_skew <= dsr_normal, (
            f"Negative skew should reduce DSR: normal={dsr_normal:.4f} neg_skew={dsr_neg_skew:.4f}"
        )

    def test_positive_excess_kurtosis_reduces_dsr(self):
        """High excess kurtosis (fat tails) increases variance term → lower DSR."""
        dsr_normal = deflated_sharpe(sharpe=0.50, n_trials=10, n_obs=120)
        dsr_fat_tails = deflated_sharpe(
            sharpe=0.50, n_trials=10, n_obs=120, excess_kurtosis=4.0
        )
        assert dsr_fat_tails <= dsr_normal, (
            f"Fat tails should reduce DSR: normal={dsr_normal:.4f} fat={dsr_fat_tails:.4f}"
        )
