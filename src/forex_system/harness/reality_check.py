"""Reality-Check (R5) falsification tests — NHT specification implementation.

Three complementary bootstrap tests per NHT R5 spec:
  R5a — Stationary / Circular Block Bootstrap (autocorrelation falsifier)
  R5b — Randomized OOS-Window Placement (regime/window-selection falsifier)
  R5c — Hansen's SPA (pair-selection / best-of-N falsifier)

All tests are deterministic when given the same master_seed:
  R5a child seed = master_seed
  R5b child seed = master_seed + 1
  R5c child seed = master_seed + 2

Spec reference: NHT R5 falsification spec (2026-05-30 p3-intraday-orb wave).

IMPORTANT — data-availability note
-----------------------------------
Running R5 on carry_fred requires full-history per-pair return arrays (not just
the OOS slice). These arrays are not currently surfaced by the harness metrics
dict. Providing them is a data-availability follow-up tracked separately; the
implementation here accepts any numpy arrays of the correct shape and can be
exercised immediately with synthetic data.

Global conventions
------------------
- Sharpe annualised with TRADING_DAYS_PER_YEAR = 252 (matches calculate_metrics).
- B = 10000 bootstrap resamples (per spec).
- alpha = 0.05 (pre-declared).
- p-value formula: (1 + #{S_b >= S_obs}) / (B + 1)  — avoids p=0 artefact.
- All logs include seed, rng="numpy.PCG64", lib versions.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from forex_system.core.constants import TRADING_DAYS_PER_YEAR

logger = logging.getLogger("forex_system.harness.reality_check")

# ---------------------------------------------------------------------------
# Global parameters (per spec)
# ---------------------------------------------------------------------------

_ALPHA = 0.05
_B = 10_000  # Number of bootstrap resamples
_SENSITIVITY_BLOCK_LENGTHS: tuple[int, ...] = (5, 10, 20)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _annualized_sharpe(returns: np.ndarray) -> float:
    """Compute annualized Sharpe ratio from a 1-D daily return array.

    Matches calculate_metrics convention:
      - No risk-free rate adjustment (rf = 0).
      - Annualises by TRADING_DAYS_PER_YEAR = 252.
      - Returns 0.0 when std == 0 (flat / empty series).
    """
    if len(returns) < 2:
        return 0.0
    std = float(np.std(returns, ddof=1))
    if std == 0.0:
        return 0.0
    return float(np.mean(returns) / std * math.sqrt(TRADING_DAYS_PER_YEAR))


def _default_block_length(t_oos: int) -> int:
    """Expected block length L = ceil(T_oos^(1/3))."""
    return math.ceil(t_oos ** (1.0 / 3.0))


def _lib_versions() -> dict[str, str]:
    """Return library versions for reproducibility logging."""
    return {"numpy": np.__version__}


def _log_seed_info(test_label: str, seed: int, rng: np.random.Generator) -> None:
    """Log seed, rng type, and lib versions for each test invocation."""
    logger.info(
        '{"event": "r5.seed_info", "test": "%s", "seed": %d, "rng": "numpy.PCG64",'
        ' "numpy_version": "%s"}',
        test_label,
        seed,
        np.__version__,
    )


def _circular_block_bootstrap(
    series: np.ndarray,
    block_length: int,
    n_resamples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Stationary circular block bootstrap (Politis-Romano 1994).

    Builds each resample by concatenating i.i.d. Geometric(p=1/L) length blocks
    drawn from the series, with circular wrap-around.

    Parameters
    ----------
    series:
        1-D array of de-meaned returns (length T).
    block_length:
        Expected block length L. p = 1/L for Geometric distribution.
    n_resamples:
        Number of bootstrap resamples to generate.
    rng:
        NumPy random generator (seeded externally for determinism).

    Returns
    -------
    resamples:
        2-D array of shape (n_resamples, T).
    """
    t = len(series)
    p = 1.0 / block_length
    resamples = np.empty((n_resamples, t), dtype=float)

    for i in range(n_resamples):
        result: list[float] = []
        while len(result) < t:
            # Block start: uniform over [0, T)
            start = int(rng.integers(0, t))
            # Block length: Geometric(p), clipped to avoid over-run
            blen = int(rng.geometric(p))
            # Circular extraction
            for j in range(blen):
                result.append(series[(start + j) % t])
        resamples[i] = result[:t]

    return resamples


# ---------------------------------------------------------------------------
# R5a — Stationary / Circular Block Bootstrap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class R5aResult:
    """Result of the R5a stationary block bootstrap test.

    Attributes
    ----------
    pvalue:
        Bootstrap p-value (circular block, L=default). FAIL if > alpha.
    sensitivity:
        Dict mapping block-length → p-value for L in {5, 10, 20}.
    block_sensitive:
        True if verdict flips across any pair of sensitivity block lengths.
    block_length_used:
        The default L used for the primary p-value.
    B:
        Number of bootstrap resamples.
    seed:
        Child seed used (master_seed).
    lib_versions:
        Dict of library versions used.
    """

    pvalue: float
    sensitivity: dict[int, float]
    block_sensitive: bool
    block_length_used: int
    B: int
    seed: int
    lib_versions: dict[str, str]


def r5a_circular_block_bootstrap(
    oos_returns: np.ndarray,
    master_seed: int,
    B: int = _B,
) -> R5aResult:
    """R5a — Stationary circular block bootstrap (autocorrelation falsifier).

    H0: the OOS return series has zero-mean (pure noise).
    Statistic: annualised Sharpe of bootstrap resample under H0 (de-meaned series).
    p-value = (1 + #{S_b >= S_obs}) / (B + 1).

    Parameters
    ----------
    oos_returns:
        1-D array of per-bar portfolio returns for the OOS period (length T_oos).
    master_seed:
        Seed for R5a child rng (uses master_seed directly, per spec).
    B:
        Number of bootstrap resamples (default 10000).

    Returns
    -------
    R5aResult
        Contains primary p-value, sensitivity dict, and metadata.
    """
    oos_returns = np.asarray(oos_returns, dtype=float)
    t_oos = len(oos_returns)
    if t_oos < 2:
        raise ValueError(f"R5a: oos_returns must have at least 2 observations, got {t_oos}")

    child_seed = master_seed  # R5a uses master_seed directly
    rng = np.random.default_rng(np.random.PCG64(child_seed))
    _log_seed_info("R5a", child_seed, rng)

    # Observed statistic (on original, not de-meaned)
    s_obs = _annualized_sharpe(oos_returns)

    # De-mean: impose H0 zero-mean while preserving autocorrelation / variance
    demeaned = oos_returns - np.mean(oos_returns)

    default_L = _default_block_length(t_oos)

    def _pvalue_for_L(block_len: int, rng_local: np.random.Generator) -> float:
        resamples = _circular_block_bootstrap(demeaned, block_len, B, rng_local)
        s_boot = np.array([_annualized_sharpe(resamples[i]) for i in range(B)])
        return float((1 + np.sum(s_boot >= s_obs)) / (B + 1))

    # Primary p-value (default L, uses the seeded rng — consumes rng state)
    pvalue_primary = _pvalue_for_L(default_L, rng)

    # Sensitivity: re-seed sub-rngs deterministically from the same seed
    sensitivity: dict[int, float] = {}
    for idx, L in enumerate(_SENSITIVITY_BLOCK_LENGTHS):
        sub_rng = np.random.default_rng(np.random.PCG64(child_seed + 100 + idx))
        sensitivity[L] = _pvalue_for_L(L, sub_rng)

    # Block sensitivity: verdict flips if any L gives opposite conclusion vs default
    default_rejects = pvalue_primary > _ALPHA
    block_sensitive = any(
        (sensitivity[L] > _ALPHA) != default_rejects
        for L in _SENSITIVITY_BLOCK_LENGTHS
    )

    result = R5aResult(
        pvalue=pvalue_primary,
        sensitivity=sensitivity,
        block_sensitive=block_sensitive,
        block_length_used=default_L,
        B=B,
        seed=child_seed,
        lib_versions=_lib_versions(),
    )
    logger.info(
        '{"event": "r5a.result", "pvalue": %.6f, "block_length": %d,'
        ' "block_sensitive": %s, "sensitivity": %s}',
        result.pvalue,
        result.block_length_used,
        str(result.block_sensitive).lower(),
        str(result.sensitivity),
    )
    return result


# ---------------------------------------------------------------------------
# R5b — Randomized OOS-Window Placement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class R5bResult:
    """Result of the R5b randomized OOS-window placement test.

    Attributes
    ----------
    window_percentile:
        Fraction of windows with Sharpe <= S_obs (i.e. P(S(w) <= S_obs)).
    upper_pvalue:
        Fraction of windows with Sharpe >= S_obs (P(S(w) >= S_obs)).
    median_sharpe:
        Median Sharpe across all windows.
    n_windows:
        Total number of windows (step=1 sliding, or step=21 if declared).
    n_windows_nonoverlapping:
        Honest n = floor(N_total / window_len).
    window_len:
        OOS window length used.
    step:
        Step size used (1 or 21).
    seed:
        Child seed used (master_seed + 1).
    lib_versions:
        Library versions.
    """

    window_percentile: float
    upper_pvalue: float
    median_sharpe: float
    n_windows: int
    n_windows_nonoverlapping: int
    window_len: int
    step: int
    seed: int
    lib_versions: dict[str, str]


def r5b_window_placement(
    full_returns: np.ndarray,
    oos_len: int,
    master_seed: int,
    step: int = 1,
) -> R5bResult:
    """R5b — Randomized OOS-window placement (regime/window-selection falsifier).

    Slides a window of length oos_len across all offsets (step=1 or step=21),
    computing Sharpe per window to build the null distribution.

    window_percentile = #{S(w) <= S_obs} / #windows
    upper_pvalue     = #{S(w) >= S_obs} / #windows

    Verdict logic (per spec):
      FAIL if window_percentile >= 0.90
      PASS if window_percentile <= 0.75 AND median_sharpe >= 0.30
      Else INCONCLUSIVE

    Parameters
    ----------
    full_returns:
        1-D array of full-history per-bar portfolio returns (all available history).
    oos_len:
        Length of the OOS window (number of bars).
    master_seed:
        Not used for computation (no randomness in R5b) but captured for audit trail.
    step:
        Sliding step (default 1; use 21 to reduce compute; must declare it).

    Returns
    -------
    R5bResult
    """
    full_returns = np.asarray(full_returns, dtype=float)
    n_total = len(full_returns)
    child_seed = master_seed + 1  # Per spec: R5b uses master_seed + 1
    _log_seed_info("R5b", child_seed, np.random.default_rng(np.random.PCG64(child_seed)))

    if oos_len > n_total:
        raise ValueError(
            f"R5b: oos_len ({oos_len}) exceeds total series length ({n_total})"
        )
    if oos_len < 2:
        raise ValueError(f"R5b: oos_len must be >= 2, got {oos_len}")

    # The observed statistic: Sharpe of the LAST oos_len bars (the actual OOS)
    s_obs = _annualized_sharpe(full_returns[-oos_len:])

    # Slide window across all valid start offsets
    start_indices = list(range(0, n_total - oos_len + 1, step))
    window_sharpes = np.array(
        [_annualized_sharpe(full_returns[s : s + oos_len]) for s in start_indices]
    )
    n_windows = len(window_sharpes)

    window_percentile = float(np.sum(window_sharpes <= s_obs) / n_windows)
    upper_pvalue = float(np.sum(window_sharpes >= s_obs) / n_windows)
    median_sharpe = float(np.median(window_sharpes))
    n_windows_nonoverlapping = n_total // oos_len

    result = R5bResult(
        window_percentile=window_percentile,
        upper_pvalue=upper_pvalue,
        median_sharpe=median_sharpe,
        n_windows=n_windows,
        n_windows_nonoverlapping=n_windows_nonoverlapping,
        window_len=oos_len,
        step=step,
        seed=child_seed,
        lib_versions=_lib_versions(),
    )
    logger.info(
        '{"event": "r5b.result", "window_percentile": %.4f, "upper_pvalue": %.4f,'
        ' "median_sharpe": %.4f, "n_windows": %d, "n_nonoverlapping": %d}',
        result.window_percentile,
        result.upper_pvalue,
        result.median_sharpe,
        result.n_windows,
        result.n_windows_nonoverlapping,
    )
    return result


# ---------------------------------------------------------------------------
# R5c — Hansen's SPA (Superior Predictive Ability)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class R5cResult:
    """Result of Hansen's SPA test (pair-selection / best-of-N falsifier).

    Attributes
    ----------
    pvalue_consistent:
        SPA consistent p-value (Hansen's recommended test statistic). FAIL if > alpha.
    pvalue_lower:
        SPA lower (anti-conservative) p-value.
    pvalue_upper:
        SPA upper (conservative) p-value.
    t_spa_obs:
        Observed SPA test statistic: max_k [ sqrt(T) * mean(d_k) / omega_hat_k ].
    B:
        Number of bootstrap resamples.
    seed:
        Child seed used (master_seed + 2).
    lib_versions:
        Library versions.
    """

    pvalue_consistent: float
    pvalue_lower: float
    pvalue_upper: float
    t_spa_obs: float
    B: int
    seed: int
    lib_versions: dict[str, str]


def r5c_hansen_spa(
    pair_returns: np.ndarray,
    master_seed: int,
    block_length: int = 10,
    B: int = _B,
) -> R5cResult:
    """R5c — Hansen's SPA test (pair-selection / best-of-N falsifier).

    Tests H0: none of the k pairs has predictive ability over zero-return benchmark.
    Benchmark = zero return; d_{k,t} = pair k return at bar t.
    Statistic: T_SPA = max_k [ sqrt(T) * mean(d_k) / omega_hat_k ]

    Block bootstrap is applied JOINTLY across all pairs (preserving cross-pair
    correlation) — pairs are NOT bootstrapped independently.

    Parameters
    ----------
    pair_returns:
        2-D array of shape (T, k): per-bar return for each of k pairs.
    master_seed:
        R5c uses master_seed + 2 as child seed.
    block_length:
        Block length for stationary bootstrap (default L=10, per spec).
    B:
        Number of bootstrap resamples (default 10000).

    Returns
    -------
    R5cResult
        SPA lower / consistent / upper p-values and observed statistic.

    Notes
    -----
    Hansen (2005) "A Test for Superior Predictive Ability".
    Recenter by subtracting the thresholded mean (Hansen's recommended approach):
      mu_bar_k = max(0, mean(d_k))  — only re-centers for models that appear
      to have positive performance under H0, which is the conservative choice.
    """
    pair_returns = np.asarray(pair_returns, dtype=float)
    if pair_returns.ndim == 1:
        pair_returns = pair_returns[:, np.newaxis]
    if pair_returns.ndim != 2:
        raise ValueError(
            f"R5c: pair_returns must be 2-D (T, k), got shape {pair_returns.shape}"
        )

    T, k = pair_returns.shape
    if T < 2:
        raise ValueError(f"R5c: need at least 2 observations, got T={T}")

    child_seed = master_seed + 2  # Per spec: R5c uses master_seed + 2
    rng = np.random.default_rng(np.random.PCG64(child_seed))
    _log_seed_info("R5c", child_seed, rng)

    # --- Observed statistic ---
    means = np.mean(pair_returns, axis=0)  # shape (k,)

    # HAC (Newey-West) standard error for each pair's mean, with block_length lags
    def _hac_se(x: np.ndarray) -> float:
        """Newey-West HAC SE for a 1-D series (bandwidth = block_length - 1)."""
        n = len(x)
        x_dm = x - np.mean(x)
        # Bartlett kernel, bandwidth h = block_length - 1
        h = max(block_length - 1, 1)
        gamma0 = np.dot(x_dm, x_dm) / n
        s2 = gamma0
        for lag in range(1, h + 1):
            w = 1.0 - lag / (h + 1)
            gamma_lag = np.dot(x_dm[lag:], x_dm[:-lag]) / n
            s2 += 2.0 * w * gamma_lag
        # Clamp to avoid negative variance from small samples
        s2 = max(s2, 1e-12)
        return float(math.sqrt(s2 / n))

    omegas = np.array([_hac_se(pair_returns[:, j]) for j in range(k)])
    # Guard against zero omega (all returns identical)
    omegas = np.where(omegas < 1e-12, 1e-12, omegas)

    studentized = math.sqrt(T) * means / omegas  # shape (k,)
    t_spa_obs = float(np.max(studentized))

    # --- Joint stationary circular block bootstrap of the k-dim return vector ---
    p = 1.0 / block_length

    def _joint_bootstrap_once(rng_local: np.random.Generator) -> np.ndarray:
        """Return one (T, k) resample preserving cross-pair correlation."""
        result_rows: list[np.ndarray] = []
        while len(result_rows) < T:
            start = int(rng_local.integers(0, T))
            blen = int(rng_local.geometric(p))
            for j in range(blen):
                result_rows.append(pair_returns[(start + j) % T])
        return np.stack(result_rows[:T], axis=0)  # (T, k)

    # Hansen (2005): recenter with thresholded mean (mu_bar_k = max(0, mean(d_k)))
    # This is the "consistent" recentering; only models with positive apparent
    # performance are recentered (conservative against spurious winners).
    mu_bar = np.maximum(means, 0.0)  # shape (k,): thresholded mean per pair

    # For lower bound: recenter all (anti-conservative — no threshold)
    mu_lower = means.copy()

    # For upper bound: no recentering (null = zero mean for all pairs)
    mu_upper = np.zeros(k)

    t_spa_boot_consistent = np.empty(B)
    t_spa_boot_lower = np.empty(B)
    t_spa_boot_upper = np.empty(B)

    for b in range(B):
        boot = _joint_bootstrap_once(rng)  # (T, k) — joint resample

        # Consistent: recenter by mu_bar (thresholded)
        boot_means_c = np.mean(boot - mu_bar[np.newaxis, :], axis=0)
        boot_se_c = np.array([_hac_se(boot[:, j] - mu_bar[j]) for j in range(k)])
        boot_se_c = np.where(boot_se_c < 1e-12, 1e-12, boot_se_c)
        t_spa_boot_consistent[b] = np.max(math.sqrt(T) * boot_means_c / boot_se_c)

        # Lower: recenter by sample mean (anti-conservative)
        boot_means_l = np.mean(boot - mu_lower[np.newaxis, :], axis=0)
        boot_se_l = np.array([_hac_se(boot[:, j] - mu_lower[j]) for j in range(k)])
        boot_se_l = np.where(boot_se_l < 1e-12, 1e-12, boot_se_l)
        t_spa_boot_lower[b] = np.max(math.sqrt(T) * boot_means_l / boot_se_l)

        # Upper: no recentering (most conservative)
        boot_means_u = np.mean(boot - mu_upper[np.newaxis, :], axis=0)
        boot_se_u = np.array([_hac_se(boot[:, j]) for j in range(k)])
        boot_se_u = np.where(boot_se_u < 1e-12, 1e-12, boot_se_u)
        t_spa_boot_upper[b] = np.max(math.sqrt(T) * boot_means_u / boot_se_u)

    pvalue_consistent = float((1 + np.sum(t_spa_boot_consistent >= t_spa_obs)) / (B + 1))
    pvalue_lower = float((1 + np.sum(t_spa_boot_lower >= t_spa_obs)) / (B + 1))
    pvalue_upper = float((1 + np.sum(t_spa_boot_upper >= t_spa_obs)) / (B + 1))

    result = R5cResult(
        pvalue_consistent=pvalue_consistent,
        pvalue_lower=pvalue_lower,
        pvalue_upper=pvalue_upper,
        t_spa_obs=t_spa_obs,
        B=B,
        seed=child_seed,
        lib_versions=_lib_versions(),
    )
    logger.info(
        '{"event": "r5c.result", "spa_consistent": %.6f, "spa_lower": %.6f,'
        ' "spa_upper": %.6f, "t_spa_obs": %.4f}',
        result.pvalue_consistent,
        result.pvalue_lower,
        result.pvalue_upper,
        result.t_spa_obs,
    )
    return result


# ---------------------------------------------------------------------------
# Combined R5 verdict
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class R5CombinedResult:
    """Combined R5 verdict — all three sub-tests must pass.

    Verdict logic:
      "PASS"        — all three pass (pvalue <= 0.05 where required).
      "FAIL"        — any sub-test fails definitively.
      "INCONCLUSIVE" — any sub-test is INCONCLUSIVE (block-sensitive in R5a,
                       borderline in R5b, or structural issue in R5c).

    This is the top-level block emitted as "r5" in the trial metrics aggregate.

    Attributes
    ----------
    master_seed:
        Master seed used; child seeds are +0, +1, +2 for R5a/R5b/R5c.
    rng:
        RNG identifier string (always "numpy.PCG64").
    lib_versions:
        Dict of library versions.
    block_length:
        Default block length L (ceil(T^(1/3))) used for R5a primary.
    B:
        Number of bootstrap resamples.
    r5a_circular_block_pvalue:
        R5a primary p-value.
    r5a_block_sensitivity:
        Dict mapping L → p-value for L in {5, 10, 20}.
    r5a_block_sensitive:
        True if verdict flips across sensitivity block lengths.
    r5b_window_percentile:
        Fraction of windows with Sharpe <= S_obs.
    r5b_window_upper_pvalue:
        Fraction of windows with Sharpe >= S_obs.
    r5b_window_median_sharpe:
        Median Sharpe across all sliding windows.
    r5b_n_windows_nonoverlapping:
        Honest non-overlapping n = floor(N_total / oos_len).
    r5c_spa_pvalue_consistent:
        SPA consistent p-value.
    r5c_spa_pvalue_lower:
        SPA lower p-value.
    r5c_spa_pvalue_upper:
        SPA upper p-value.
    r5_combined_verdict:
        "PASS", "FAIL", or "INCONCLUSIVE".
    permutation_pvalue:
        Flat mirror of r5a_circular_block_pvalue (for evaluator compatibility).
    """

    master_seed: int
    rng: str
    lib_versions: dict[str, str]
    block_length: int
    B: int
    r5a_circular_block_pvalue: float
    r5a_block_sensitivity: dict[int, float]
    r5a_block_sensitive: bool
    r5b_window_percentile: float
    r5b_window_upper_pvalue: float
    r5b_window_median_sharpe: float
    r5b_n_windows_nonoverlapping: int
    r5c_spa_pvalue_consistent: float
    r5c_spa_pvalue_lower: float
    r5c_spa_pvalue_upper: float
    r5_combined_verdict: str
    permutation_pvalue: float  # Flat mirror of r5a_circular_block_pvalue

    def to_metrics_dict(self) -> dict[str, float]:
        """Return flat dict of scalar metrics for the evaluator.

        Only includes the keys that the falsification_evaluator reads via
        the R5 rubric triggers:
          - permutation_pvalue  (R5a mirror — existing aspirational field)
          - r5b_window_percentile
          - r5c_spa_pvalue_consistent
        """
        return {
            "permutation_pvalue": self.permutation_pvalue,
            "r5b_window_percentile": self.r5b_window_percentile,
            "r5c_spa_pvalue_consistent": self.r5c_spa_pvalue_consistent,
        }


def _r5b_verdict(r5b: R5bResult) -> str:
    """Compute R5b sub-verdict per spec."""
    if r5b.window_percentile >= 0.90:
        return "FAIL"
    if r5b.window_percentile <= 0.75 and r5b.median_sharpe >= 0.30:
        return "PASS"
    return "INCONCLUSIVE"


def run_r5(
    oos_returns: np.ndarray,
    full_returns: np.ndarray,
    pair_returns: np.ndarray,
    master_seed: int,
    B: int = _B,
    r5b_step: int = 1,
) -> R5CombinedResult:
    """Run all three R5 sub-tests and return a combined verdict.

    Parameters
    ----------
    oos_returns:
        1-D array of per-bar OOS portfolio returns (length T_oos).
    full_returns:
        1-D array of full-history per-bar portfolio returns (all history).
    pair_returns:
        2-D array of shape (T_oos, k): per-bar return for each of k pairs,
        covering the OOS period. Used for R5c.
    master_seed:
        Master seed; R5a child=master_seed, R5b child=master_seed+1,
        R5c child=master_seed+2.
    B:
        Number of bootstrap resamples (default 10000).
    r5b_step:
        Step size for R5b window sliding (default 1; use 21 for large series).

    Returns
    -------
    R5CombinedResult
        Combined verdict with all sub-test results embedded.
    """
    oos_len = len(oos_returns)
    default_L = _default_block_length(oos_len)

    r5a = r5a_circular_block_bootstrap(oos_returns, master_seed=master_seed, B=B)
    r5b = r5b_window_placement(full_returns, oos_len=oos_len, master_seed=master_seed, step=r5b_step)
    r5c = r5c_hansen_spa(pair_returns, master_seed=master_seed, block_length=default_L, B=B)

    # Combined verdict: conservative conjunction
    r5a_verdict: str
    if r5a.block_sensitive:
        r5a_verdict = "INCONCLUSIVE"
    elif r5a.pvalue > _ALPHA:
        r5a_verdict = "FAIL"
    else:
        r5a_verdict = "PASS"

    r5b_v = _r5b_verdict(r5b)

    r5c_verdict: str
    if r5c.pvalue_consistent > _ALPHA:
        r5c_verdict = "FAIL"
    else:
        r5c_verdict = "PASS"

    sub_verdicts = (r5a_verdict, r5b_v, r5c_verdict)
    if "INCONCLUSIVE" in sub_verdicts:
        combined = "INCONCLUSIVE"
    elif "FAIL" in sub_verdicts:
        combined = "FAIL"
    else:
        combined = "PASS"

    # Sensitivity dict: keyed by L (int)
    sensitivity_dict = {
        L: r5a.sensitivity[L] for L in _SENSITIVITY_BLOCK_LENGTHS
    }

    return R5CombinedResult(
        master_seed=master_seed,
        rng="numpy.PCG64",
        lib_versions=_lib_versions(),
        block_length=default_L,
        B=B,
        r5a_circular_block_pvalue=r5a.pvalue,
        r5a_block_sensitivity=sensitivity_dict,
        r5a_block_sensitive=r5a.block_sensitive,
        r5b_window_percentile=r5b.window_percentile,
        r5b_window_upper_pvalue=r5b.upper_pvalue,
        r5b_window_median_sharpe=r5b.median_sharpe,
        r5b_n_windows_nonoverlapping=r5b.n_windows_nonoverlapping,
        r5c_spa_pvalue_consistent=r5c.pvalue_consistent,
        r5c_spa_pvalue_lower=r5c.pvalue_lower,
        r5c_spa_pvalue_upper=r5c.pvalue_upper,
        r5_combined_verdict=combined,
        permutation_pvalue=r5a.pvalue,  # flat mirror per spec
    )
