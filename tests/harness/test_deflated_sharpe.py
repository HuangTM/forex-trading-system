"""Tests for deflated_sharpe shim module (harness/deflated_sharpe.py).

Coverage:
- The shim correctly delegates to compute_dsr with periods_per_year=252.
- Input validation (n_trials, n_obs) is forwarded correctly.
- Monotonicity: more trials → lower DSR for same observed SR.
- Non-normality: skew/kurt sensitivity direction.
- Boundary: SR <= 0 returns 0.0.

Note: _expected_max_sr tests are now in test_dsr.py (it lives in dsr.py).
The shim no longer exposes _expected_max_sr directly.
"""

from __future__ import annotations

import pytest

from forex_system.harness.deflated_sharpe import deflated_sharpe
from forex_system.harness.dsr import expected_max_sr


class TestExpectedMaxSRViaShim:
    """Test the underlying expected_max_sr (sourced from dsr.py)."""

    def test_n_trials_1_returns_zero(self):
        """Single trial has no multiple-comparisons benchmark — E[max SR] = 0."""
        result = expected_max_sr(n_trials=1, n_observations=252)
        assert result == 0.0

    def test_n_trials_22_positive(self):
        """N=22 (Phase 1 org-wide): expected max SR must be positive."""
        result = expected_max_sr(n_trials=22, n_observations=252)
        assert result > 0.0

    def test_n_trials_29_greater_than_22(self):
        """More trials → higher expected maximum SR (monotone in N)."""
        r22 = expected_max_sr(n_trials=22, n_observations=252)
        r29 = expected_max_sr(n_trials=29, n_observations=252)
        assert r29 > r22

    def test_monotone_in_n(self):
        """E[max SR | N] is strictly increasing in N for N >= 2."""
        vals = [expected_max_sr(n_trials=k, n_observations=252) for k in [2, 10, 22, 50, 100]]
        for i in range(len(vals) - 1):
            assert vals[i + 1] > vals[i], f"Not monotone at index {i}: {vals}"


class TestDeflatedSharpe:
    """deflated_sharpe(sharpe, n_trials, n_obs, skew, excess_kurtosis)."""

    # ---- Input validation ------------------------------------------------

    def test_n_trials_zero_raises(self):
        """n_trials < 1 must raise ValueError (no silent default)."""
        with pytest.raises(ValueError, match="n_trials"):
            deflated_sharpe(sharpe=1.0, n_trials=0, n_obs=252)

    def test_n_obs_one_raises(self):
        """n_obs <= 1 must raise ValueError (insufficient observations)."""
        with pytest.raises(ValueError, match="n_observations"):
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
        """vol_target_carry OOS Sharpe 0.76, N=22, T=2520 → DSR > 0.50.

        Corrected formula: SR_pp = 0.76/sqrt(252) ≈ 0.0479, SR_star(22,2520) ≈ 0.039.
        z ≈ 0.46 → DSR ≈ 0.677.
        """
        dsr = deflated_sharpe(sharpe=0.76, n_trials=22, n_obs=2520)
        assert dsr > 0.50, f"Expected DSR > 0.50 for Sharpe=0.76 N=22, got {dsr:.4f}"

    def test_n22_low_sharpe_below_threshold(self):
        """Sharpe=0.30, N=100, T=60: DSR should be well below 0.50.

        With many trials (N=100), few bars (T=60), and the corrected per-obs
        conversion, DSR is small.
        """
        dsr = deflated_sharpe(sharpe=0.30, n_trials=100, n_obs=60)
        assert dsr < 0.50, f"Expected DSR < 0.50 for deflated case N=100 T=60, got {dsr:.4f}"

    def test_n1_no_inflation(self):
        """N=1: no multiple-comparisons penalty; modest SR still gets moderate DSR."""
        dsr_n1 = deflated_sharpe(sharpe=0.50, n_trials=1, n_obs=252)
        dsr_n22 = deflated_sharpe(sharpe=0.50, n_trials=22, n_obs=252)
        # N=1 should yield higher or equal DSR than N=22 (less deflation).
        assert dsr_n1 >= dsr_n22, (
            f"N=1 should have >= DSR vs N=22 for same SR: n1={dsr_n1:.4f} n22={dsr_n22:.4f}"
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
        """Negative skewness inflates variance term → lower DSR (when z > 0).

        Direction: 1 - skew*SR_pp = 1 + |skew|*SR_pp > 1 (larger var_term).
        When z > 0 (SR_pp > SR_star), larger var_term → smaller z → lower DSR.
        This requires a high annualised SR so that SR_pp = SR_ann/sqrt(252)
        exceeds SR_star.  SR_ann=2.0, N=5, T=252 gives z ≈ 0.80 > 0.
        """
        dsr_normal = deflated_sharpe(sharpe=2.0, n_trials=5, n_obs=252)
        dsr_neg_skew = deflated_sharpe(sharpe=2.0, n_trials=5, n_obs=252, skew=-2.0)
        assert dsr_neg_skew <= dsr_normal, (
            f"Negative skew should reduce DSR when z>0: normal={dsr_normal:.4f} neg_skew={dsr_neg_skew:.4f}"
        )

    def test_positive_excess_kurtosis_reduces_dsr(self):
        """High excess kurtosis (fat tails) increases variance term → lower DSR (when z > 0).

        Uses same z > 0 regime: SR_ann=2.0, N=5, T=252.
        """
        dsr_normal = deflated_sharpe(sharpe=2.0, n_trials=5, n_obs=252)
        dsr_fat_tails = deflated_sharpe(
            sharpe=2.0, n_trials=5, n_obs=252, excess_kurtosis=4.0
        )
        assert dsr_fat_tails <= dsr_normal, (
            f"Fat tails should reduce DSR when z>0: normal={dsr_normal:.4f} fat={dsr_fat_tails:.4f}"
        )
