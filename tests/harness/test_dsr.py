"""Tests for Deflated Sharpe Ratio computation (harness/dsr.py).

Covers:
- expected_max_sr: grows with n_trials, near-zero for k=1
- compute_dsr: output in [0,1], higher for better SR, degrades with more trials
- Edge cases: invalid observations, negative SR, single trial, var_term<=0
- Spec reference rows (Mathematician corrected formula, 2026-05-31):
    Row1-4 binding inequality assertions + exact value print
- Unit-invariance invariant: compute_dsr(SR, N, T, s, k, P) == compute_dsr(SR*c, N, T, s, k, P*c^2)
- Anti-saturation gate (primary sacred test): Row1 must NOT return > 0.90
"""

from __future__ import annotations

import math

import pytest

from forex_system.harness.dsr import compute_dsr, expected_max_sr


class TestExpectedMaxSR:
    """expected_max_sr should be monotonically increasing in n_trials."""

    def test_single_trial_near_zero(self):
        """One trial: expected max SR = 0 (no multiple-comparisons inflation)."""
        sr_star = expected_max_sr(n_trials=1, n_observations=252)
        assert sr_star == 0.0

    def test_more_trials_higher_expected_max(self):
        """More trials → higher expected maximum SR (multiple comparisons penalty)."""
        sr1 = expected_max_sr(n_trials=1, n_observations=252)
        sr10 = expected_max_sr(n_trials=10, n_observations=252)
        sr100 = expected_max_sr(n_trials=100, n_observations=252)
        assert sr100 > sr10 >= sr1

    def test_zero_trials_returns_zero(self):
        """Zero trials: returns 0.0 (degenerate input guard)."""
        assert expected_max_sr(n_trials=0, n_observations=252) == 0.0

    def test_zero_observations_returns_zero(self):
        """Zero observations: returns 0.0 (degenerate input guard)."""
        assert expected_max_sr(n_trials=10, n_observations=0) == 0.0

    def test_single_observation_returns_zero(self):
        """Single observation: returns 0.0 (no variance to estimate SR)."""
        assert expected_max_sr(n_trials=10, n_observations=1) == 0.0

    def test_positive_output(self):
        """Output should always be non-negative."""
        for k in [1, 5, 10, 50, 100]:
            result = expected_max_sr(n_trials=k, n_observations=252)
            assert result >= 0.0, f"Negative expected_max_sr for k={k}"


class TestComputeDSR:
    """compute_dsr should return a probability in [0, 1]."""

    def test_output_in_unit_interval(self):
        """DSR must be a probability: in [0, 1]."""
        dsr = compute_dsr(
            sharpe_ratio=1.0,
            n_observations=252,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=1,
            periods_per_year=252.0,
        )
        assert 0.0 <= dsr <= 1.0

    def test_high_sharpe_high_dsr(self):
        """A very high Sharpe with single trial should yield high DSR."""
        dsr = compute_dsr(
            sharpe_ratio=3.0,
            n_observations=2520,  # 10 years daily
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=1,
            periods_per_year=252.0,
        )
        assert dsr > 0.80, f"Expected high DSR for SR=3.0, got {dsr:.4f}"

    def test_many_trials_deflates_dsr(self):
        """Same modest Sharpe with more trials → lower DSR (multiple comparisons penalty)."""
        dsr_1trial = compute_dsr(
            sharpe_ratio=0.5,
            n_observations=100,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=2,
            periods_per_year=252.0,
        )
        dsr_100trials = compute_dsr(
            sharpe_ratio=0.5,
            n_observations=100,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=1000,
            periods_per_year=252.0,
        )
        assert dsr_100trials < dsr_1trial, (
            f"More trials should deflate DSR: got 1trial={dsr_1trial:.4f}, "
            f"1000trials={dsr_100trials:.4f}"
        )

    def test_negative_sharpe_returns_zero(self):
        """Negative Sharpe: DSR = 0.0 (early return guard)."""
        dsr = compute_dsr(
            sharpe_ratio=-0.5,
            n_observations=252,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=5,
            periods_per_year=252.0,
        )
        assert dsr == 0.0

    def test_zero_sharpe_returns_zero(self):
        """Zero Sharpe: DSR = 0.0."""
        dsr = compute_dsr(
            sharpe_ratio=0.0,
            n_observations=252,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=5,
            periods_per_year=252.0,
        )
        assert dsr == 0.0

    def test_n_observations_one_raises(self):
        """n_observations <= 1: raises ValueError (insufficient data)."""
        with pytest.raises(ValueError, match="n_observations"):
            compute_dsr(
                sharpe_ratio=2.0,
                n_observations=1,
                skewness=0.0,
                excess_kurtosis=0.0,
                n_trials=1,
                periods_per_year=252.0,
            )

    def test_n_trials_zero_raises(self):
        """n_trials < 1: raises ValueError."""
        with pytest.raises(ValueError, match="n_trials"):
            compute_dsr(
                sharpe_ratio=2.0,
                n_observations=252,
                skewness=0.0,
                excess_kurtosis=0.0,
                n_trials=0,
                periods_per_year=252.0,
            )

    def test_periods_per_year_zero_raises(self):
        """periods_per_year <= 0: raises ValueError."""
        with pytest.raises(ValueError, match="periods_per_year"):
            compute_dsr(
                sharpe_ratio=2.0,
                n_observations=252,
                skewness=0.0,
                excess_kurtosis=0.0,
                n_trials=1,
                periods_per_year=0.0,
            )

    def test_n_trials_one_sr_star_is_zero(self):
        """n_trials=1: SR_star=0, formula still runs (no multiple-comparisons penalty)."""
        dsr = compute_dsr(
            sharpe_ratio=0.5,
            n_observations=252,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=1,
            periods_per_year=252.0,
        )
        assert 0.0 <= dsr <= 1.0

    def test_var_term_non_positive_returns_zero(self):
        """Degenerate var_term <= 0: returns 0.0 (cannot certify)."""
        # To force var_term <= 0: need 1 - skew*sr_pp + (exkurt+2)/4 * sr_pp^2 <= 0
        # With large positive skew and modest SR_pp:
        # sr_pp = 4.0/sqrt(252) ≈ 0.252; skew=100 → 1 - 100*0.252 + ... < 0
        dsr = compute_dsr(
            sharpe_ratio=4.0,
            n_observations=252,
            skewness=100.0,  # pathologically high positive skew
            excess_kurtosis=0.0,
            n_trials=1,
            periods_per_year=252.0,
        )
        assert dsr == 0.0

    def test_non_normal_skew_has_larger_variance_term(self):
        """Negative skewness inflates variance term → lower DSR (when z > 0).

        Direction analysis: negative skew with positive SR_pp increases var_term.
        When z > 0 (SR_pp > SR_star), larger var_term → smaller z → lower DSR.
        Use SR_ann=2.0, N=5, T=252 to get SR_pp=0.126 > SR_star(5,252)=0.075.
        """
        dsr_normal = compute_dsr(
            sharpe_ratio=2.0,
            n_observations=252,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=5,
            periods_per_year=252.0,
        )
        dsr_skewed = compute_dsr(
            sharpe_ratio=2.0,
            n_observations=252,
            skewness=-2.0,
            excess_kurtosis=0.0,
            n_trials=5,
            periods_per_year=252.0,
        )
        assert dsr_skewed <= dsr_normal, (
            f"Negative skew should reduce DSR when z>0: normal={dsr_normal:.4f}, skewed={dsr_skewed:.4f}"
        )


class TestSpecReferenceRows:
    """Spec reference table assertions (Mathematician corrected formula, 2026-05-31).

    These are BINDING tests.  Exact 4-dp may differ slightly from the hand-calc
    in the spec; the inequalities are sacred.
    """

    def test_row1_anti_saturation_gate(self):
        """Row1 (PRIMARY SACRED TEST): SR_ann=0.31, T=126, N=35, skew=0, exkurt=0.

        Old buggy code returned ~0.999 (saturated near 1.0).
        Corrected code must return < 0.50 AND must NOT be > 0.90.
        This is the primary anti-saturation gate.
        """
        dsr = compute_dsr(
            sharpe_ratio=0.31,
            n_observations=126,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=35,
            periods_per_year=252.0,
        )
        print(f"\nRow1 exact DSR = {dsr:.4f}")  # Printed for evidence in test output
        assert dsr < 0.50, (
            f"Row1: DSR must be < 0.50 (anti-saturation gate); got {dsr:.4f}"
        )
        assert dsr <= 0.90, (
            f"Row1: DSR must NOT be > 0.90 (old bug was ~0.999); got {dsr:.4f}"
        )

    def test_row2_short_history(self):
        """Row2: SR_ann=0.76, T=23, N=35 → DSR ≈ 0.03, must be < 0.50."""
        dsr = compute_dsr(
            sharpe_ratio=0.76,
            n_observations=23,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=35,
            periods_per_year=252.0,
        )
        print(f"\nRow2 exact DSR = {dsr:.4f}")
        assert dsr < 0.50, (
            f"Row2: DSR must be < 0.50; got {dsr:.4f}"
        )

    def test_row3_longer_history(self):
        """Row3: SR_ann=0.80, T=778, N=35 → DSR ≈ 0.23, must be in (0,1), expect < 0.50."""
        dsr = compute_dsr(
            sharpe_ratio=0.80,
            n_observations=778,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=35,
            periods_per_year=252.0,
        )
        print(f"\nRow3 exact DSR = {dsr:.4f}")
        assert 0.0 < dsr < 1.0, (
            f"Row3: DSR must be in (0,1); got {dsr:.4f}"
        )
        assert dsr < 0.50, (
            f"Row3: spec expects DSR < 0.50; got {dsr:.4f}"
        )

    def test_row4_overfit_with_nonnormality(self):
        """Row4: SR=0.45, T=60, N=500, skew=-0.8, exkurt=6 → DSR ≈ 0.003, must be < 0.50.

        Proves that skew, kurtosis, and large-N paths all activate correctly.
        """
        dsr = compute_dsr(
            sharpe_ratio=0.45,
            n_observations=60,
            skewness=-0.8,
            excess_kurtosis=6.0,
            n_trials=500,
            periods_per_year=252.0,
        )
        print(f"\nRow4 exact DSR = {dsr:.4f}")
        assert dsr < 0.50, (
            f"Row4: DSR must be < 0.50 (overfit scenario); got {dsr:.4f}"
        )


class TestUnitInvariance:
    """Unit-invariance invariant: rescaling SR and periods_per_year consistently is a no-op.

    compute_dsr(SR, N, T, s, k, P) == compute_dsr(SR*c, N, T, s, k, P*c^2)
    for any c > 0.  This invariant catches any reintroduction of the units bug.
    """

    @pytest.mark.parametrize("c", [0.5, 1.0, 2.0, 3.7, 10.0])
    def test_scale_invariance(self, c: float):
        """DSR is invariant to consistent rescaling of SR and periods_per_year."""
        sr_base = 0.50
        P_base = 252.0
        kwargs = dict(n_observations=300, skewness=0.1, excess_kurtosis=1.5, n_trials=10)

        dsr_base = compute_dsr(sharpe_ratio=sr_base, periods_per_year=P_base, **kwargs)
        dsr_scaled = compute_dsr(
            sharpe_ratio=sr_base * c,
            periods_per_year=P_base * c ** 2,
            **kwargs,
        )
        assert abs(dsr_base - dsr_scaled) < 1e-10, (
            f"Unit invariance failed for c={c}: base={dsr_base:.10f}, scaled={dsr_scaled:.10f}"
        )

    def test_scale_invariance_negative_skew(self):
        """Unit invariance holds with negative skew and excess kurtosis."""
        sr_base = 0.80
        P_base = 252.0
        c = 4.0
        kwargs = dict(n_observations=500, skewness=-0.5, excess_kurtosis=3.0, n_trials=20)

        dsr_base = compute_dsr(sharpe_ratio=sr_base, periods_per_year=P_base, **kwargs)
        dsr_scaled = compute_dsr(
            sharpe_ratio=sr_base * c,
            periods_per_year=P_base * c ** 2,
            **kwargs,
        )
        assert abs(dsr_base - dsr_scaled) < 1e-10, (
            f"Unit invariance failed: base={dsr_base:.10f}, scaled={dsr_scaled:.10f}"
        )
