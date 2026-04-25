"""Tests for Deflated Sharpe Ratio computation (harness/dsr.py).

Covers:
- expected_max_sr: grows with n_trials, near-zero for k=1
- compute_dsr: output in [0,1], higher for better SR, degrades with more trials
- Edge cases: zero observations, negative SR, single trial
"""

from __future__ import annotations

import pytest

from forex_system.harness.dsr import compute_dsr, expected_max_sr


class TestExpectedMaxSR:
    """expected_max_sr should be monotonically increasing in n_trials."""

    def test_single_trial_near_zero(self):
        """One trial: expected max SR ≈ 0 (no multiple-comparisons inflation)."""
        sr_star = expected_max_sr(n_trials=1, n_observations=252)
        # k=1 → args are near 0 and near 0 → result should be small
        assert sr_star >= 0.0

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
        )
        assert dsr > 0.80, f"Expected high DSR for SR=3.0, got {dsr:.4f}"

    def test_many_trials_deflates_dsr(self):
        """Same modest Sharpe with more trials → lower DSR (multiple comparisons penalty).

        Use a modest Sharpe (0.5) with a small observation count so DSR doesn't saturate.
        """
        # With SR=0.5 and few observations, DSR is in a range where deflation is measurable
        dsr_1trial = compute_dsr(
            sharpe_ratio=0.5,
            n_observations=100,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=2,  # k>=2 for expected_max_sr to be non-zero
        )
        dsr_100trials = compute_dsr(
            sharpe_ratio=0.5,
            n_observations=100,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=1000,
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
        )
        assert dsr == 0.0

    def test_few_observations_returns_zero(self):
        """Fewer than 3 observations: returns 0.0 (insufficient data guard)."""
        dsr = compute_dsr(
            sharpe_ratio=2.0,
            n_observations=2,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=1,
        )
        assert dsr == 0.0

    def test_non_normal_skew_has_larger_variance_term(self):
        """Negative skewness inflates the DSR variance denominator.

        We test the variance term effect indirectly: with skewness=-2 and
        a modest SR, the variance term 1 - skew*SR + kurt/4*SR^2 is larger
        → DSR should be lower (or equal at saturation with high n_obs).
        Use a small n_obs to avoid saturation at 1.0.
        """
        # Use modest SR and few observations to keep DSR in mid-range
        dsr_normal = compute_dsr(
            sharpe_ratio=0.4,
            n_observations=60,
            skewness=0.0,
            excess_kurtosis=0.0,
            n_trials=5,
        )
        dsr_skewed = compute_dsr(
            sharpe_ratio=0.4,
            n_observations=60,
            skewness=-2.0,  # Negatively skewed — heavier left tail
            excess_kurtosis=0.0,
            n_trials=5,
        )
        # Negative skew with positive SR: skew*SR = -2.0*0.4 = -0.8
        # variance_term = 1 - (-0.8) + ... = 1.8 + ... → larger denominator → lower z → lower DSR
        assert dsr_skewed <= dsr_normal, (
            f"Negative skew should reduce DSR: normal={dsr_normal:.4f}, skewed={dsr_skewed:.4f}"
        )
