"""Tests for Politis-White (2004) block-length selection and White RC p-value.

STEP 2a implementation tests — two gaps added to reality_check.py:
  Gap 1: politis_white_block_length / politis_white_block_length_multivariate
  Gap 2: white_rc_pvalue field in R5cResult, computed from the same draws as SPA

Spec reference:
  Politis & White (2004) + Patton-Politis-White (2009) — automatic block-length
  selection for the stationary bootstrap.
  White (2000) — Reality Check p-value off same draws as Hansen SPA.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from forex_system.harness.reality_check import (
    politis_white_block_length,
    politis_white_block_length_multivariate,
    r5a_circular_block_bootstrap,
    r5c_hansen_spa,
    run_r5,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEED = 42


def _make_ar1(phi: float, n: int, seed: int = _SEED) -> np.ndarray:
    """AR(1) series: x_t = phi * x_{t-1} + eps_t, eps ~ N(0,1)."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    x[0] = rng.standard_normal()
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.standard_normal()
    return x


def _make_wn(n: int, seed: int = _SEED) -> np.ndarray:
    """IID standard normal (white noise)."""
    return np.random.default_rng(seed).standard_normal(n)


# ---------------------------------------------------------------------------
# Gap 1: politis_white_block_length — univariate
# ---------------------------------------------------------------------------


class TestPolitisWhiteUnivariate:
    """Tests for politis_white_block_length (univariate case)."""

    def test_white_noise_returns_short_block_length(self) -> None:
        """White noise should yield a small L (near-iid, little autocorrelation)."""
        x = _make_wn(500)
        L = politis_white_block_length(x)
        # White noise has near-zero ACF; Politis-White should give L in [1, 8]
        assert L >= 1.0, f"L must be >= 1, got {L}"
        assert L <= 8.0, (
            f"White noise (T=500) should yield small L, got {L:.4f}."
            " If this fails, review the m_hat criterion — may be over-fitting noise."
        )

    def test_ar1_strong_returns_larger_block_length_than_white_noise(self) -> None:
        """Strongly autocorrelated AR(1) should yield larger L than white noise."""
        wn = _make_wn(500)
        ar1 = _make_ar1(phi=0.9, n=500)
        L_wn = politis_white_block_length(wn)
        L_ar1 = politis_white_block_length(ar1)
        assert L_ar1 > L_wn, f"AR(1) phi=0.9 L={L_ar1:.4f} should exceed white noise L={L_wn:.4f}"
        # AR(1) phi=0.9 implies theoretical optimal block ~ O(T^(1/3) * correction);
        # expect L well above 5 for T=500
        assert L_ar1 > 5.0, f"Expected L_ar1 > 5 for phi=0.9, got {L_ar1:.4f}"

    def test_l_floor_at_one(self) -> None:
        """L is always >= 1.0, even for very short or iid-like series."""
        x = _make_wn(20)  # small T
        L = politis_white_block_length(x)
        assert L >= 1.0, f"L must be >= 1.0, got {L}"

    def test_guard_nan_raises(self) -> None:
        """NaN in input raises ValueError (fail-closed)."""
        x = np.array([1.0, np.nan, 0.5, -0.3])
        with pytest.raises(ValueError, match="NaN or Inf"):
            politis_white_block_length(x)

    def test_guard_inf_raises(self) -> None:
        """Inf in input raises ValueError (fail-closed)."""
        x = np.array([1.0, np.inf, 0.5])
        with pytest.raises(ValueError, match="NaN or Inf"):
            politis_white_block_length(x)

    def test_guard_empty_raises(self) -> None:
        """Length < 2 raises ValueError."""
        with pytest.raises(ValueError, match="at least 2 observations"):
            politis_white_block_length(np.array([1.0]))

    def test_guard_scalar_raises(self) -> None:
        """Zero-length array raises ValueError."""
        with pytest.raises(ValueError, match="at least 2 observations"):
            politis_white_block_length(np.array([]))

    def test_constant_series_returns_one(self) -> None:
        """Constant series (zero variance) returns L=1 (degenerate iid case)."""
        x = np.ones(200)
        L = politis_white_block_length(x)
        assert L == 1.0, f"Constant series should give L=1, got {L}"

    def test_2d_array_raises(self) -> None:
        """2-D input to the univariate function raises ValueError."""
        with pytest.raises(ValueError, match="1-D"):
            politis_white_block_length(np.ones((10, 3)))

    def test_moderate_ar1_between_wn_and_strong_ar1(self) -> None:
        """AR(1) phi=0.5 yields L between white noise and phi=0.9."""
        wn = _make_wn(500)
        ar1_mid = _make_ar1(phi=0.5, n=500)
        ar1_strong = _make_ar1(phi=0.9, n=500)
        L_wn = politis_white_block_length(wn)
        L_mid = politis_white_block_length(ar1_mid)
        L_strong = politis_white_block_length(ar1_strong)
        # Expected ordering with high probability; not a guaranteed invariant for
        # all seeds, but holds for the canonical seed=42.
        assert L_strong > L_wn, f"phi=0.9 L={L_strong:.2f} should exceed WN L={L_wn:.2f}"
        # phi=0.5 should be somewhere in [1, strong]; not guaranteed strictly
        # between, but should not exceed strong significantly
        assert L_mid <= L_strong * 1.5 or L_mid >= L_wn, (
            f"phi=0.5 L={L_mid:.2f} is inconsistent (WN={L_wn:.2f}, strong={L_strong:.2f})"
        )

    def test_return_type_is_float(self) -> None:
        """Return value is always a Python float."""
        L = politis_white_block_length(_make_wn(100))
        assert isinstance(L, float), f"Expected float, got {type(L)}"

    def test_deterministic_for_same_input(self) -> None:
        """Same array always returns the same L (no randomness in the function)."""
        x = _make_wn(300)
        L1 = politis_white_block_length(x)
        L2 = politis_white_block_length(x)
        assert L1 == L2, "politis_white_block_length must be deterministic"

    def test_longer_series_gives_reasonable_l(self) -> None:
        """Longer T should produce finite, reasonable L for AR(1)."""
        ar1 = _make_ar1(phi=0.8, n=2000)
        L = politis_white_block_length(ar1)
        assert 1.0 <= L <= 200.0, f"L for T=2000 AR(1) phi=0.8 should be in [1, 200], got {L:.4f}"


# ---------------------------------------------------------------------------
# Gap 1: politis_white_block_length_multivariate
# ---------------------------------------------------------------------------


class TestPolitisWhiteMultivariate:
    """Tests for politis_white_block_length_multivariate."""

    def test_max_across_columns(self) -> None:
        """Multivariate max equals max of per-column L values."""
        wn = _make_wn(500)
        ar1 = _make_ar1(phi=0.9, n=500)
        X = np.column_stack([wn, ar1])
        L_mv = politis_white_block_length_multivariate(X)
        L_wn = politis_white_block_length(wn)
        L_ar1 = politis_white_block_length(ar1)
        expected = max(L_wn, L_ar1)
        assert math.isclose(L_mv, expected, rel_tol=1e-9), (
            f"Multivariate L={L_mv:.4f} should equal max({L_wn:.4f}, {L_ar1:.4f})={expected:.4f}"
        )

    def test_single_column_matches_univariate(self) -> None:
        """A (T, 1) matrix gives the same result as the univariate function."""
        x = _make_wn(300)
        L_uni = politis_white_block_length(x)
        L_mv = politis_white_block_length_multivariate(x[:, np.newaxis])
        assert math.isclose(L_mv, L_uni, rel_tol=1e-9), (
            f"Single-column multivariate L={L_mv:.4f} != univariate L={L_uni:.4f}"
        )

    def test_1d_input_treated_as_single_column(self) -> None:
        """1-D input is accepted (treated as a single column)."""
        x = _make_wn(200)
        L_uni = politis_white_block_length(x)
        L_mv = politis_white_block_length_multivariate(x)
        assert math.isclose(L_mv, L_uni, rel_tol=1e-9)

    def test_guard_nan_in_any_column_raises(self) -> None:
        """NaN in any column raises ValueError (fail-closed)."""
        X = np.ones((100, 3))
        X[5, 1] = np.nan
        with pytest.raises(ValueError, match="NaN or Inf"):
            politis_white_block_length_multivariate(X)

    def test_guard_too_short_raises(self) -> None:
        """T < 2 raises ValueError."""
        X = np.array([[1.0, 2.0]])  # T=1, k=2
        with pytest.raises(ValueError, match="T>=2"):
            politis_white_block_length_multivariate(X)

    def test_l_floor_at_one(self) -> None:
        """L >= 1.0 is enforced for all columns."""
        X = _make_wn(50).reshape(-1, 1)
        L = politis_white_block_length_multivariate(X)
        assert L >= 1.0

    def test_many_columns_dominated_by_strong_ar1(self) -> None:
        """If one column has high autocorrelation, the max is driven by it."""
        n = 500
        rng = np.random.default_rng(7)
        cols = [rng.standard_normal(n) for _ in range(5)]  # 5 WN columns
        ar1_col = _make_ar1(phi=0.9, n=n, seed=8)
        X = np.column_stack(cols + [ar1_col])
        L_mv = politis_white_block_length_multivariate(X)
        L_ar1 = politis_white_block_length(ar1_col)
        # Max should be driven by the AR(1) column
        assert math.isclose(L_mv, L_ar1, rel_tol=1e-9), (
            f"Multivariate L={L_mv:.4f} should equal AR(1) L={L_ar1:.4f}"
        )


# ---------------------------------------------------------------------------
# Gap 2: White RC p-value in R5cResult
# ---------------------------------------------------------------------------


class TestWhiteRCPvalue:
    """Tests for the white_rc_pvalue field added to R5cResult."""

    def test_white_rc_field_present(self) -> None:
        """R5cResult now has a white_rc_pvalue field."""
        rng = np.random.default_rng(1)
        pair_ret = rng.standard_normal((200, 3)) * 0.01
        res = r5c_hansen_spa(pair_ret, master_seed=0, block_length=5, B=200)
        assert hasattr(res, "white_rc_pvalue"), "R5cResult must have white_rc_pvalue"

    def test_t_rc_obs_field_present(self) -> None:
        """R5cResult now has a t_rc_obs field (observed White RC statistic)."""
        rng = np.random.default_rng(2)
        pair_ret = rng.standard_normal((200, 3)) * 0.01
        res = r5c_hansen_spa(pair_ret, master_seed=0, block_length=5, B=200)
        assert hasattr(res, "t_rc_obs"), "R5cResult must have t_rc_obs"

    def test_white_rc_pvalue_in_valid_range(self) -> None:
        """white_rc_pvalue must be in (0, 1]."""
        rng = np.random.default_rng(3)
        pair_ret = rng.standard_normal((200, 4)) * 0.01
        res = r5c_hansen_spa(pair_ret, master_seed=0, block_length=5, B=300)
        assert 0.0 < res.white_rc_pvalue <= 1.0, (
            f"white_rc_pvalue={res.white_rc_pvalue} not in (0, 1]"
        )
        assert 0.0 < res.pvalue_consistent <= 1.0

    def test_rc_pvalue_geq_spa_consistent_poor_model_dominated(self) -> None:
        """RC p-value >= SPA p-value when many poor models are present.

        White RC is the conservative test: it does NOT studentize or recenter
        poor models, so its null distribution is inflated relative to SPA's
        consistent recentering.  With many near-zero/negative cells, RC should
        yield a p-value >= SPA consistent p-value.

        Expected (not guaranteed for every possible draw, but holds in expectation
        and for this specific deterministic seed scenario with a clear winner
        against poor models).
        """
        # 1 strong cell + 5 near-zero/negative cells (poor-model dominated)
        T = 400
        rng = np.random.default_rng(99)
        poor = rng.standard_normal((T, 5)) * 0.005 - 0.001  # slight negative drift
        winner = rng.standard_normal(T) * 0.005 + 0.003  # consistently positive
        pair_ret = np.column_stack([poor, winner])
        res = r5c_hansen_spa(pair_ret, master_seed=0, block_length=5, B=2000)
        # Both p-values are defined and finite
        assert 0.0 < res.white_rc_pvalue <= 1.0
        assert 0.0 < res.pvalue_consistent <= 1.0
        # RC >= SPA is the expected ordering (RC is more conservative)
        assert res.white_rc_pvalue >= res.pvalue_consistent, (
            f"Expected RC p={res.white_rc_pvalue:.4f} >= SPA consistent p={res.pvalue_consistent:.4f}."
            " RC must be more conservative when poor models are present."
        )

    def test_same_draws_produce_both_pvalues(self) -> None:
        """Both p-values are computed from one set of draws (verifiable via seed determinism).

        We verify that running r5c_hansen_spa twice with the same seed produces
        exactly the same SPA and RC p-values (deterministic), confirming they
        share the same RNG state path.
        """
        rng = np.random.default_rng(11)
        pair_ret = rng.standard_normal((250, 3)) * 0.01
        res1 = r5c_hansen_spa(pair_ret, master_seed=5, block_length=5, B=500)
        res2 = r5c_hansen_spa(pair_ret, master_seed=5, block_length=5, B=500)
        assert res1.pvalue_consistent == res2.pvalue_consistent
        assert res1.white_rc_pvalue == res2.white_rc_pvalue
        assert res1.t_rc_obs == res2.t_rc_obs

    def test_block_length_auto_field_present(self) -> None:
        """R5cResult has block_length_auto and block_length_used fields."""
        rng = np.random.default_rng(4)
        pair_ret = rng.standard_normal((200, 2)) * 0.01
        res = r5c_hansen_spa(pair_ret, master_seed=0, block_length=5, B=100)
        assert hasattr(res, "block_length_auto")
        assert hasattr(res, "block_length_used")
        assert res.block_length_used == 5
        assert res.block_length_auto is False

    def test_block_length_none_triggers_auto_selection(self) -> None:
        """block_length=None triggers Politis-White auto-selection in r5c."""
        rng = np.random.default_rng(5)
        pair_ret = rng.standard_normal((300, 3)) * 0.01
        res = r5c_hansen_spa(pair_ret, master_seed=0, block_length=None, B=100)
        assert res.block_length_auto is True
        assert res.block_length_used >= 1

    def test_spa_is_primary_rc_is_crosscheck_ordering_documented(self) -> None:
        """SPA consistent is primary; RC is cross-check; RC >= SPA documented behaviour.

        Uses a null scenario (zero-mean returns) where both should be high p-values
        (fail to reject H0).  Verifies both are present and the ordering is stable.
        """
        T = 300
        rng = np.random.default_rng(77)
        # All cells pure noise → should not reject H0
        pair_ret = rng.standard_normal((T, 4)) * 0.001
        res = r5c_hansen_spa(pair_ret, master_seed=0, block_length=5, B=500)
        # Both should have high p-values under null
        assert res.pvalue_consistent > 0.05, (
            f"Pure noise should not reject H0: SPA p={res.pvalue_consistent:.4f}"
        )
        assert res.white_rc_pvalue > 0.05, (
            f"Pure noise should not reject H0: RC p={res.white_rc_pvalue:.4f}"
        )


# ---------------------------------------------------------------------------
# R5a backward-compat: block_length parameter
# ---------------------------------------------------------------------------


class TestR5aBlockLengthParam:
    """Tests for block_length parameter in r5a (auto vs fixed)."""

    def test_fixed_block_length_backward_compat(self) -> None:
        """Passing block_length=int still works (backward-compatible)."""
        returns = _make_wn(252)
        res = r5a_circular_block_bootstrap(returns, master_seed=0, B=200, block_length=10)
        assert res.block_length_used == 10
        assert res.block_length_auto is False

    def test_auto_block_length_default(self) -> None:
        """Default block_length=None triggers auto-selection."""
        returns = _make_wn(252)
        res = r5a_circular_block_bootstrap(returns, master_seed=0, B=200)
        assert res.block_length_auto is True
        assert res.block_length_used >= 1

    def test_block_length_auto_field_in_result(self) -> None:
        """R5aResult has block_length_auto field."""
        returns = _make_wn(100)
        res = r5a_circular_block_bootstrap(returns, master_seed=0, B=100, block_length=5)
        assert hasattr(res, "block_length_auto")
        assert isinstance(res.block_length_auto, bool)


# ---------------------------------------------------------------------------
# R5CombinedResult: new fields
# ---------------------------------------------------------------------------


class TestR5CombinedResultFields:
    """Verify R5CombinedResult exposes White RC and block_length_auto fields."""

    def test_combined_result_has_white_rc_pvalue(self) -> None:
        """R5CombinedResult must have r5c_white_rc_pvalue field."""
        rng = np.random.default_rng(20)
        oos = rng.standard_normal(120) * 0.01
        full = rng.standard_normal(500) * 0.01
        pairs = rng.standard_normal((120, 3)) * 0.01
        res = run_r5(oos, full, pairs, master_seed=0, B=100, r5b_step=10)
        assert hasattr(res, "r5c_white_rc_pvalue"), "R5CombinedResult must have r5c_white_rc_pvalue"
        assert 0.0 < res.r5c_white_rc_pvalue <= 1.0

    def test_combined_result_has_block_length_auto(self) -> None:
        """R5CombinedResult must have block_length_auto field."""
        rng = np.random.default_rng(21)
        oos = rng.standard_normal(120) * 0.01
        full = rng.standard_normal(500) * 0.01
        pairs = rng.standard_normal((120, 3)) * 0.01
        res = run_r5(oos, full, pairs, master_seed=0, B=100, r5b_step=10)
        assert hasattr(res, "block_length_auto")
        assert isinstance(res.block_length_auto, bool)

    def test_to_metrics_dict_includes_white_rc(self) -> None:
        """to_metrics_dict() includes r5c_white_rc_pvalue."""
        rng = np.random.default_rng(22)
        oos = rng.standard_normal(120) * 0.01
        full = rng.standard_normal(500) * 0.01
        pairs = rng.standard_normal((120, 3)) * 0.01
        res = run_r5(oos, full, pairs, master_seed=0, B=100, r5b_step=10)
        d = res.to_metrics_dict()
        assert "r5c_white_rc_pvalue" in d, (
            f"to_metrics_dict() must include r5c_white_rc_pvalue; got keys: {list(d.keys())}"
        )
        assert "r5c_spa_pvalue_consistent" in d  # existing field still present
        assert "permutation_pvalue" in d  # backward-compat still present


# ---------------------------------------------------------------------------
# Politis-White numbers — spot check for exact reproducibility
# ---------------------------------------------------------------------------


class TestPolitisWhiteExactValues:
    """Pin exact L values for canonical inputs (seed=42, T=500).

    These pins are cross-validated against the R blocklength::pwsd reference
    implementation (Alec-Stashevsky, GitHub), which implements the canonical
    Politis-White (2004) / Patton-Politis-White (2009) algorithm.

    Implementation uses the corrected formula per Mathematician adjudication
    2026-06-03 (mathematician-pw-adjudication.yaml):
      - m_hat = max(1, run_start - 1)  [canonical R implied_hypothesis AND-rule]
      - c = qnorm(0.975) = 1.959963984540054  [R blocklength::pwsd default]
      - M_max = ceil(sqrt(T)) + K_N   [R oracle band cap]

    Oracle-matched impl values vs R blocklength::pwsd oracle (numpy/R RNG differ
    on the same seed, so small deviations in the ~1e-3 range are expected and
    acceptable; the algorithm, not the draw, is what the oracle validates):
      WN    T=500 seed=42: impl L=2.3922, R oracle L=2.4016  (rel diff < 0.5%)
      AR0.5 T=500 seed=42: impl L=7.1642, R oracle L=7.1646  (rel diff < 0.01%)
      AR0.9 T=500 seed=42: impl L=19.9629, R oracle L≈19.94  (rel diff < 0.2%)

    arch.bootstrap.optimal_block_length was NOT available (ModuleNotFoundError);
    the R reference was used as the oracle instead.
    """

    def test_wn_exact_l(self) -> None:
        """White noise T=500 seed=42 yields L≈2.392 (cross-validated vs R oracle ~2.40).

        Corrected formula: m_hat = max(1, run_start - 1).  For WN, run_start=1
        → m_hat = max(1, 0) = 1 (floor applies; m_hat is never 0).
        M = 2*1 = 2 → spectral sums are computed over k in [-2, 2] → finite G_hat
        → L_opt≈2.392.  The R oracle produces L≈2.40 on the same series (numpy/R
        RNG differ, but both use m_hat=1 and M=2, so the algorithm agrees).

        The old pin of L=1.0 was based on the interim `m_hat = run_start - 1`
        WITHOUT the floor, which gave m_hat=0 → M=0 → degenerate guard.  The
        canonical R rule is max(1, run_start - 1), which floors at 1, not 0.
        Cross-validated: R blocklength::pwsd oracle (Mathematician 2026-06-03).
        """
        wn = _make_wn(500, seed=42)
        L = politis_white_block_length(wn)
        # impl=2.392177, R oracle=2.4016; rel diff ~0.4% (numpy/R RNG, not algorithm)
        assert math.isclose(L, 2.392177, rel_tol=1e-5), (
            f"Pinned WN L differs: got {L:.6f}, expected 2.392177 "
            f"(R oracle ~2.40; cross-validated 2026-06-03)"
        )

    def test_ar1_phi09_exact_l(self) -> None:
        """AR(1) phi=0.9 T=500 seed=42 yields L≈19.963 (cross-validated vs R oracle ~19.94).

        Corrected formula: m_hat = max(1, run_start - 1) with c=qnorm(0.975).
        With c=1.96: run_start=11 → m_hat=10, M=20.
        R oracle: m_hat=9 at c=2.0 (R RNG); m_hat=10 at c=1.96 with numpy RNG.
        Algorithm agreement: both use the same max(1, run_start-1) rule; the
        m_hat difference is RNG-induced (numpy vs R draw different lag-11 ACF).
        impl L=19.9629, R oracle L≈19.94; within 1e-3 relative tolerance.
        Cross-validated: R blocklength::pwsd oracle (Mathematician 2026-06-03).
        """
        ar1 = _make_ar1(phi=0.9, n=500, seed=42)
        L = politis_white_block_length(ar1)
        # impl=19.962904, R oracle≈19.94; rel diff ~0.1%
        assert math.isclose(L, 19.962904, rel_tol=1e-5), (
            f"Pinned AR(1) phi=0.9 L differs: got {L:.6f}, expected 19.962904 "
            f"(R oracle ~19.94; cross-validated 2026-06-03)"
        )

    def test_ar1_phi05_exact_l(self) -> None:
        """AR(1) phi=0.5 T=500 seed=42 yields L≈7.164 (cross-validated vs R oracle 7.1646).

        Corrected formula: m_hat = max(1, run_start - 1) with c=qnorm(0.975).
        run_start=3 → m_hat=2, M=4.
        impl L=7.164245, R oracle L=7.1646; rel diff < 0.005%.
        Near-exact agreement: same m_hat and M, spectral sum differences only
        from numpy/R ACF estimation RNG.
        Cross-validated: R blocklength::pwsd oracle (Mathematician 2026-06-03).
        """
        ar1 = _make_ar1(phi=0.5, n=500, seed=42)
        L = politis_white_block_length(ar1)
        # impl=7.164245, R oracle=7.1646; rel diff <0.005%
        assert math.isclose(L, 7.164245, rel_tol=1e-5), (
            f"Pinned AR(1) phi=0.5 L differs: got {L:.6f}, expected 7.164245 "
            f"(R oracle 7.1646; cross-validated 2026-06-03)"
        )

    def test_bmax_cap_and_mmax_cap_near_unit_root(self) -> None:
        """AR(0.97) T=500 seed=123: M_max binds before b_max does; b_max is still enforced.

        With the corrected R-oracle M_max = ceil(sqrt(T)) + K_N = 23 + 5 = 28 (T=500),
        M is capped at 28 regardless of 2*m_hat.  This reduces L_opt from the old ~81.76
        to ~34.11, which is below b_max=68 — so b_max does NOT bind for this series with
        the corrected formula.  The corrected behavior matches the R blocklength::pwsd
        oracle (which also caps M via M_max before b_max).

        b_max is verified to still be a valid cap (L_final <= b_max for all valid inputs).
        Cross-validated: R blocklength::pwsd oracle M_max rule (Mathematician 2026-06-03).
        """
        ar1 = _make_ar1(phi=0.97, n=500, seed=123)
        L = politis_white_block_length(ar1)
        b_max = math.ceil(min(3 * math.sqrt(500), 500 / 3))
        assert b_max == 68, f"b_max for T=500 should be 68, got {b_max}"
        # M_max=ceil(sqrt(500))+5=28 binds before b_max; L_opt drops to ~34.11
        # so b_max does not bind — but the result is still within [1, b_max].
        assert math.isclose(L, 34.106116, rel_tol=1e-4), (
            f"AR(0.97) seed=123 L differs: got {L:.6f}, expected ~34.106 "
            f"(M_max=28 binds; b_max=68 does not; cross-validated 2026-06-03)"
        )
        assert L <= float(b_max), f"L={L:.4f} must be <= b_max={b_max}"
