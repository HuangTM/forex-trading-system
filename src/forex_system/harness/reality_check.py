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
    """Expected block length L = ceil(T_oos^(1/3)).

    Legacy heuristic — preserved for backward compatibility.  New code should
    call politis_white_block_length() or politis_white_block_length_multivariate()
    for data-driven automatic block-length selection.
    """
    return math.ceil(t_oos ** (1.0 / 3.0))


# ---------------------------------------------------------------------------
# Politis-White (2004) automatic block-length selection
# ---------------------------------------------------------------------------

# Reference:
#   Politis, D.N. & White, H. (2004). "Automatic Block-Length Selection for
#   the Dependent Bootstrap." Econometric Reviews, 23(1), 53-70.
#
#   Patton, A., Politis, D.N. & White, H. (2009). "Correction to 'Automatic
#   Block-Length Selection for the Dependent Bootstrap' by D. Politis and H.
#   White." Econometric Reviews, 28(4), 372-375.
#
# Implements the STATIONARY BOOTSTRAP optimal mean block length.  The key
# formula (equation (14) in Politis & White 2004 / corrected in PPW 2009):
#
#   L_opt = ( 2 * g_hat^2 / d_hat )^(1/3) * T^(1/3)
#
# where, for the stationary bootstrap:
#   g_hat = sum_{k=-m_hat}^{m_hat} |k| * R(k)   [sum of absolute-lag-weighted autocovs]
#   d_hat = (  sum_{k=-m_hat}^{m_hat} R(k)  )^2  [squared sum of autocovs]
#
#   R(k) = autocovariance at lag k (R(0) = variance).
#   m_hat = data-driven lag cut-off via the "flat-top" threshold rule (PPW 2009
#           correction): the smallest lag m beyond which |rho(k)| <
#           c * sqrt( log10(T) / T ) for K_N consecutive lags,
#           c = qnorm(0.975) = 1.959963984540054 (R blocklength::pwsd default;
#           PW2004 text uses c=2 as an approximation but R reference uses qnorm).
#
# Guards:
#   - L_opt < 1 → return 1 (i.i.d. limit, acceptable per spec).
#   - d_hat == 0 (constant series) → return 1.
#   - NaN / Inf in input → raise ValueError (fail-closed).
#   - Empty input → raise ValueError.


def politis_white_block_length(x: np.ndarray) -> float:
    """Politis-White (2004) + PPW (2009) optimal STATIONARY bootstrap block length.

    Computes the data-driven mean block length L for the stationary bootstrap
    (Politis-Romano 1994) using the automatic block-length selection algorithm
    of Politis & White (2004) with the Patton-Politis-White (2009) correction.

    Parameters
    ----------
    x:
        1-D array of observations (returns or other stationary series).
        Must have length >= 2.  NaN or Inf entries raise ValueError (fail-closed).

    Returns
    -------
    float
        Optimal mean block length L in [1.0, b_max], where
        b_max = ceil(min(3*sqrt(T), T/3)) is the PW2004 upper cap.

    Algorithm
    ---------
    Step 1 — De-mean x.
    Step 2 — Estimate biased autocovariances R(k) = (1/T) * sum x[t]*x[t+k].
    Step 3 — Find m_hat (PPW 2009): lag immediately before the first K_N-length
              run of lags where |rho(k)| < c*sqrt(log10(T)/T),
              c = qnorm(0.975) = 1.959963984540054 (R blocklength::pwsd default).
              m_hat = max(1, run_start - 1) per canonical R implied_hypothesis rule.
              K_N = max(5, ceil(log10(T)))  [PW2004 footnote c; max(5,..) is a
              small-T guard].
    Step 4 — Set band M = min(2*m_hat, ceil(sqrt(T))+K_N, T-1).  Compute G_hat and D_SB using the
              PW2004 flat-top lag window lambda(u) over lags k in [-M, M]:
                lambda(u) = 1          for |u| < 0.5
                lambda(u) = 2*(1-|u|)  for 0.5 <= |u| <= 1
                lambda(u) = 0          otherwise
              G_hat = sum_{k=-M}^{M} lambda(|k|/M) * |k| * R(k)
              D_SB  = 2 * (sum_{k=-M}^{M} lambda(|k|/M) * R(k))^2
    Step 5 — L_opt = (2 * G_hat^2 / D_SB)^(1/3) * T^(1/3)
    Step 6 — L_final = min(max(L_opt, 1.0), b_max)

    Notes
    -----
    PPW (2009) correction: K_N consecutive lags all below threshold (not just one),
    preventing premature truncation at noise spikes.

    References
    ----------
    Politis & White (2004), Econometric Reviews, 23(1), 53-70.
    Patton, Politis & White (2009), Econometric Reviews, 28(4), 372-375.
    R reference implementation: blocklength::pwsd (Alec-Stashevsky).
    """
    x = np.asarray(x, dtype=float)

    if x.ndim != 1:
        raise ValueError(f"politis_white_block_length: x must be 1-D, got shape {x.shape}")
    if len(x) < 2:
        raise ValueError(
            f"politis_white_block_length: x must have at least 2 observations, got {len(x)}"
        )
    if not np.all(np.isfinite(x)):
        raise ValueError(
            "politis_white_block_length: x contains NaN or Inf — cannot compute block length"
        )

    T = len(x)
    # Step 1: de-mean
    x_dm = x - np.mean(x)

    # Step 2: biased autocovariance R(k) = (1/T) * sum x_dm[t] * x_dm[t+k]
    max_lag = T - 1

    def _autocov(k: int) -> float:
        """Biased autocovariance estimate at lag k."""
        if k == 0:
            return float(np.dot(x_dm, x_dm)) / T
        return float(np.dot(x_dm[k:], x_dm[:-k])) / T

    R0 = _autocov(0)
    if R0 < 1e-14:
        # Constant series: variance is effectively zero → i.i.d., L = 1
        logger.info(
            '{"event": "politis_white.constant_series", "T": %d, "R0": %.6e, "L_returned": 1}',
            T,
            R0,
        )
        return 1.0

    # Step 3: find m_hat via the PPW (2009) consecutive-lags criterion.
    # Threshold: c * sqrt( log10(T) / T )   [PPW 2009 eq. 4]
    # c = qnorm(0.975) = 1.959963984540054 — the R blocklength::pwsd default.
    # PW2004 text suggests c=2 as a round-number approximation, but the canonical
    # R reference uses qnorm(0.975).  We use the R value for oracle parity.
    # Materiality: negligible (identical to 4dp on WN per Mathematician adjudication),
    # but removes the only named divergence from the R reference.
    c = 1.959963984540054  # = scipy.stats.norm.ppf(0.975); R blocklength::pwsd default
    threshold = c * math.sqrt(math.log10(T) / T)
    # FIX PW-2: K_N = max(5, ceil(log10(T))) per PW2004 footnote c.
    # max(5, ...) is a small-T guard; ceil not floor, no sqrt.
    K_N = max(5, math.ceil(math.log10(T)))

    # Canonical R blocklength::pwsd `implied_hypothesis` m_hat rule (Mathematician
    # adjudication 2026-06-03, supersedes two prior PR reviews):
    #   m_hat = max(1, run_start - 1)
    # where run_start = first lag of the first K_N-long insignificant run.
    # The "-1" AND the "floor at 1" are BOTH required (AND-semantics, not OR):
    #   - run_start == 1  → max(1, 0) = 1  (floor: insignificant from lag 1 onward)
    #   - run_start > 1   → run_start - 1  (lag immediately before the run starts)
    # R source: `if (run_pos == 1) m_hat <- 1 else m_hat <- sum(lengths[1..run_pos-1])`
    # Previous code `max(1, run_start)` was off-by-one HIGH when run_start > 1
    # (PR#2's "floor" mis-statement dropped the -1 correction PR#1 had correctly
    # identified).  The contradiction is resolved: both -1 AND floor are needed.
    m_hat = max_lag  # default: use all lags
    consecutive_below = 0
    run_start: int | None = None
    for k in range(1, max_lag + 1):
        rho_k = abs(_autocov(k)) / R0
        if rho_k < threshold:
            if consecutive_below == 0:
                run_start = k  # first lag of this insignificant run
            consecutive_below += 1
            if consecutive_below >= K_N:
                # Canonical R rule: max(1, run_start - 1).  Both arms are required.
                m_hat = max(1, run_start - 1) if run_start is not None else 1
                break
        else:
            consecutive_below = 0
            run_start = None
    # If K_N consecutive below-threshold lags never found, m_hat stays at max_lag.

    # FIX PW-1: band M = 2*m_hat (not m_hat), flat-top window on BOTH sums.
    # R blocklength::pwsd: M_max = ceil(sqrt(n)) + K_N; M = min(2*m_hat, M_max).
    # We also bound by max_lag for safety on very short series.
    M_max = math.ceil(math.sqrt(T)) + K_N
    M = min(2 * m_hat, M_max, max_lag)

    def _flat_top(u: float) -> float:
        """PW2004 flat-top lag window: 1 for |u|<0.5, 2*(1-|u|) for 0.5<=|u|<=1."""
        au = abs(u)
        if au < 0.5:
            return 1.0
        if au <= 1.0:
            return 2.0 * (1.0 - au)
        return 0.0

    # Step 4: G_hat and D_SB using the flat-top window over k in [-M, M].
    # G_hat = sum_{k=-M..M} lambda(|k|/M) * |k| * R(k)
    # D_SB  = 2 * (sum_{k=-M..M} lambda(|k|/M) * R(k))^2
    # Edge: M=0 (m_hat=0, near-iid) → sum_for_g=0, guard below fires → L=1.
    sum_for_d = 0.0
    sum_for_g = 0.0
    if M == 0:
        # m_hat=0: only k=0 in the band; |k|=0 → G_hat=0 → degenerate guard.
        sum_for_d = R0  # lambda(0/0) conventionally 1; k=0 contributes R(0)
    else:
        for k in range(-M, M + 1):
            lam = _flat_top(k / M)
            Rk = _autocov(min(abs(k), max_lag))
            sum_for_d += lam * Rk
            sum_for_g += lam * abs(k) * Rk

    g_hat = abs(sum_for_g)
    # FIX PW-1c: factor-2 in D_SB per PW2004 stationary-bootstrap form.
    d_hat = 2.0 * sum_for_d**2

    # Step 5: L_opt = (2 * G_hat^2 / D_SB)^(1/3) * T^(1/3)
    if d_hat < 1e-28 or g_hat < 1e-28:
        # Near-zero numerator or denominator → i.i.d. / degenerate series → L = 1
        L_opt = 1.0
    else:
        L_opt = ((2.0 * g_hat**2) / d_hat) ** (1.0 / 3.0) * (T ** (1.0 / 3.0))

    # FIX PW-3: apply PW2004 upper cap b_max = ceil(min(3*sqrt(T), T/3)).
    b_max = math.ceil(min(3.0 * math.sqrt(T), T / 3.0))
    L_clamped = min(max(float(L_opt), 1.0), float(b_max))
    cap_binds = L_opt > b_max

    logger.info(
        '{"event": "politis_white.block_length", "T": %d, "m_hat": %d,'
        ' "M": %d, "threshold": %.6f, "K_N": %d, "g_hat": %.6e, "d_hat": %.6e,'
        ' "L_opt": %.4f, "b_max": %d, "cap_binds": %s, "L_final": %.4f}',
        T,
        m_hat,
        M,
        threshold,
        K_N,
        g_hat,
        d_hat,
        L_opt,
        b_max,
        str(cap_binds).lower(),
        L_clamped,
    )
    return L_clamped


def politis_white_block_length_multivariate(X: np.ndarray) -> float:
    """Politis-White block length for a (T, k) matrix: max L across k columns.

    Per spec (Mathematician R5 spec, block-length-rule): "take the max L across
    the |U| cells so every cell's dependence is covered."

    Parameters
    ----------
    X:
        2-D array of shape (T, k).  Each column is a univariate series.
        NaN/Inf in any column raises ValueError (fail-closed).

    Returns
    -------
    float
        max(politis_white_block_length(X[:, j]) for j in range(k)), >= 1.0.
    """
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, np.newaxis]
    if X.ndim != 2:
        raise ValueError(
            f"politis_white_block_length_multivariate: X must be 1-D or 2-D, got shape {X.shape}"
        )
    T, k = X.shape
    if T < 2:
        raise ValueError(f"politis_white_block_length_multivariate: need T>=2, got T={T}")

    col_lengths = [politis_white_block_length(X[:, j]) for j in range(k)]
    L_max = max(col_lengths)

    logger.info(
        '{"event": "politis_white.multivariate", "T": %d, "k": %d, "col_Ls": %s, "L_max": %.4f}',
        T,
        k,
        str([round(v, 4) for v in col_lengths]),
        L_max,
    )
    return L_max


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
        The L used for the primary p-value (auto-selected or caller-supplied).
    block_length_auto:
        True if L was selected via Politis-White (2004); False if caller supplied
        a fixed block_length.
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
    block_length_auto: bool
    B: int
    seed: int
    lib_versions: dict[str, str]


def r5a_circular_block_bootstrap(
    oos_returns: np.ndarray,
    master_seed: int,
    B: int = _B,
    block_length: int | None = None,
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
    block_length:
        Mean block length L for the stationary bootstrap.  If None (default),
        the data-driven Politis-White (2004) + PPW (2009) automatic block-length
        rule is applied to oos_returns (recommended).  Pass an int to override
        with a fixed value (backward-compatible with existing call sites that
        supply a fixed L).

    Returns
    -------
    R5aResult
        Contains primary p-value, sensitivity dict, and metadata.
        R5aResult.block_length_auto is True when Politis-White was used.
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

    # Block length: data-driven (Politis-White 2004) or caller-supplied override
    if block_length is None:
        pw_L = politis_white_block_length(demeaned)
        default_L = max(1, int(math.ceil(pw_L)))
        block_length_auto = True
    else:
        default_L = int(block_length)
        block_length_auto = False

    logger.info(
        '{"event": "r5a.block_length", "block_length_used": %d,'
        ' "block_length_auto": %s, "T_oos": %d}',
        default_L,
        str(block_length_auto).lower(),
        t_oos,
    )

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
        (sensitivity[L] > _ALPHA) != default_rejects for L in _SENSITIVITY_BLOCK_LENGTHS
    )

    result = R5aResult(
        pvalue=pvalue_primary,
        sensitivity=sensitivity,
        block_sensitive=block_sensitive,
        block_length_used=default_L,
        block_length_auto=block_length_auto,
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
        raise ValueError(f"R5b: oos_len ({oos_len}) exceeds total series length ({n_total})")
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
    """Result of Hansen's SPA test + White's Reality Check (pair-selection / best-of-N falsifier).

    Both SPA and White RC p-values are computed from the SAME stationary-bootstrap
    draws, at no additional cost.

    Primary decision statistic: ``pvalue_consistent`` (Hansen SPA consistent).
    Conservative cross-check:   ``white_rc_pvalue`` (White 2000 Reality Check).

    It is EXPECTED (not contradictory) that white_rc_pvalue >= pvalue_consistent.
    White RC recenters by the sample mean (White 2000 eq. 3.7) but does NOT
    studentise and does NOT apply poor-model recentering (no max(0, mean) threshold).
    SPA is strictly more powerful under H0 with many near-zero/negative cells.
    Both are reported for transparency; the pre-registered decision rule is SPA primary.

    Attributes
    ----------
    pvalue_consistent:
        SPA consistent p-value (Hansen's recommended test statistic). FAIL if > alpha.
    pvalue_lower:
        SPA lower (anti-conservative) p-value.
    pvalue_upper:
        SPA upper (conservative) p-value.
    white_rc_pvalue:
        White (2000) Reality Check p-value, computed off the SAME bootstrap draws.
        RC is recentered by the sample mean (White 2000 eq. 3.7) — the bootstrap
        null is ``boot - mean(d_k)``.  The distinction from SPA is the absence of
        studentisation (no omega division) and the absence of poor-model recentering
        (no max(0, mean) threshold).  RC >= SPA consistent p-value is the expected
        ordering.  Source: White (2000) "A Reality Check for Data Snooping",
        Econometrica, 68(5), 1097-1126.
    t_spa_obs:
        Observed SPA test statistic: max_k [ sqrt(T) * mean(d_k) / omega_hat_k ].
    t_rc_obs:
        Observed White RC test statistic: max_k [ sqrt(T) * mean(d_k) ] (NOT
        studentised — no omega normalisation).
    block_length_used:
        Mean block length L used for the stationary bootstrap (auto-selected via
        Politis-White 2004 or caller-supplied).
    block_length_auto:
        True if L was selected via Politis-White (2004); False if caller supplied
        a fixed block_length.
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
    white_rc_pvalue: float
    t_spa_obs: float
    t_rc_obs: float
    block_length_used: int
    block_length_auto: bool
    B: int
    seed: int
    lib_versions: dict[str, str]


def r5c_hansen_spa(
    pair_returns: np.ndarray,
    master_seed: int,
    block_length: int | None = None,
    B: int = _B,
) -> R5cResult:
    """R5c — Hansen's SPA + White's Reality Check (pair-selection / best-of-N falsifier).

    Tests H0: none of the k pairs has predictive ability over zero-return benchmark.
    Benchmark = zero return; d_{k,t} = pair k return at bar t.

    Computes BOTH:
    - Hansen SPA (2005) statistic:  T_SPA = max_k [ sqrt(T)*mean(d_k) / omega_hat_k ]
      (primary — studentised + recentered)
    - White's Reality Check (2000): T_RC  = max_k [ sqrt(T)*mean(d_k) ]
      (conservative cross-check — NOT studentised, recentered by sample mean)

    Both p-values are computed from the SAME stationary-bootstrap draws.
    Expected: white_rc_pvalue >= pvalue_consistent (RC is the more conservative test).

    Block bootstrap is applied JOINTLY across all pairs (preserving cross-pair
    correlation) — pairs are NOT bootstrapped independently.

    Parameters
    ----------
    pair_returns:
        2-D array of shape (T, k): per-bar return for each of k pairs.
    master_seed:
        R5c uses master_seed + 2 as child seed.
    block_length:
        Mean block length L for the stationary bootstrap.  If None (default),
        the data-driven Politis-White (2004) + PPW (2009) automatic block-length
        selection is applied to the joint (T, k) matrix (max L across columns,
        per spec).  Pass an int to override with a fixed value.
        NOTE: the old default was fixed block_length=10; passing block_length=10
        explicitly preserves the old behaviour (backward-compatible).
    B:
        Number of bootstrap resamples (default 10000).

    Returns
    -------
    R5cResult
        SPA lower / consistent / upper p-values, White RC p-value, and metadata.

    Notes
    -----
    SPA reference: Hansen (2005) "A Test for Superior Predictive Ability",
      J. Business & Economic Statistics, 23(4), 365-380.
    RC reference: White (2000) "A Reality Check for Data Snooping",
      Econometrica, 68(5), 1097-1126.

    SPA recentering (consistent): mu_bar_k = max(0, mean(d_k)) — only re-centers
    models that appear to have positive performance under H0 (conservative against
    spurious winners).

    White RC: recentered by the sample mean (White 2000 eq. 3.7) but NOT
    studentised and NOT poor-model-recentered (no max(0, mean) threshold).
    RC >= SPA p-value is the expected and documented behaviour, not a contradiction.
    """
    pair_returns = np.asarray(pair_returns, dtype=float)
    if pair_returns.ndim == 1:
        pair_returns = pair_returns[:, np.newaxis]
    if pair_returns.ndim != 2:
        raise ValueError(f"R5c: pair_returns must be 2-D (T, k), got shape {pair_returns.shape}")

    T, k = pair_returns.shape
    if T < 2:
        raise ValueError(f"R5c: need at least 2 observations, got T={T}")

    child_seed = master_seed + 2  # Per spec: R5c uses master_seed + 2
    rng = np.random.default_rng(np.random.PCG64(child_seed))
    _log_seed_info("R5c", child_seed, rng)

    # --- Block length: auto (Politis-White 2004) or caller-supplied ---
    if block_length is None:
        pw_L = politis_white_block_length_multivariate(pair_returns)
        actual_block_length = max(1, int(math.ceil(pw_L)))
        block_length_auto = True
    else:
        actual_block_length = int(block_length)
        block_length_auto = False

    logger.info(
        '{"event": "r5c.block_length", "block_length_used": %d,'
        ' "block_length_auto": %s, "T": %d, "k": %d}',
        actual_block_length,
        str(block_length_auto).lower(),
        T,
        k,
    )

    # --- Observed statistics ---
    means = np.mean(pair_returns, axis=0)  # shape (k,)

    # HAC (Newey-West) standard error for each pair's mean, with actual_block_length lags
    def _hac_se(x: np.ndarray) -> float:
        """Newey-West HAC SE for a 1-D series (bandwidth = actual_block_length - 1)."""
        n = len(x)
        x_dm = x - np.mean(x)
        # Bartlett kernel, bandwidth h = actual_block_length - 1
        h = max(actual_block_length - 1, 1)
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

    # SPA observed: studentized max (T_k = sqrt(T) * mean(d_k) / omega_hat_k)
    studentized = math.sqrt(T) * means / omegas  # shape (k,)
    t_spa_obs = float(np.max(studentized))

    # White RC observed: non-studentized max (T_RC_k = sqrt(T) * mean(d_k))
    # White (2000) eq. (3.1): V_l = (1/n)*sum f_l — benchmark = 0, no omega division.
    rc_raw = math.sqrt(T) * means  # shape (k,): no studentisation
    t_rc_obs = float(np.max(rc_raw))

    # --- Joint stationary circular block bootstrap of the k-dim return vector ---
    p_geom = 1.0 / actual_block_length

    def _joint_bootstrap_once(rng_local: np.random.Generator) -> np.ndarray:
        """Return one (T, k) resample preserving cross-pair correlation."""
        result_rows: list[np.ndarray] = []
        while len(result_rows) < T:
            start = int(rng_local.integers(0, T))
            blen = int(rng_local.geometric(p_geom))
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

    # White RC: no recentering, no studentization — the null is all-zero means.
    # Each bootstrap replicate: T_RC^(b) = max_k [ sqrt(T) * mean(boot_k - 0) ]
    # = max_k [ sqrt(T) * mean(boot_k) ].  No omega division.

    t_spa_boot_consistent = np.empty(B)
    t_spa_boot_lower = np.empty(B)
    t_spa_boot_upper = np.empty(B)
    t_rc_boot = np.empty(B)  # White RC bootstrap distribution

    for b in range(B):
        boot = _joint_bootstrap_once(rng)  # (T, k) — joint resample

        # Consistent SPA: recenter by mu_bar (thresholded)
        boot_means_c = np.mean(boot - mu_bar[np.newaxis, :], axis=0)
        boot_se_c = np.array([_hac_se(boot[:, j] - mu_bar[j]) for j in range(k)])
        boot_se_c = np.where(boot_se_c < 1e-12, 1e-12, boot_se_c)
        t_spa_boot_consistent[b] = np.max(math.sqrt(T) * boot_means_c / boot_se_c)

        # Lower SPA: recenter by sample mean (anti-conservative)
        boot_means_l = np.mean(boot - mu_lower[np.newaxis, :], axis=0)
        boot_se_l = np.array([_hac_se(boot[:, j] - mu_lower[j]) for j in range(k)])
        boot_se_l = np.where(boot_se_l < 1e-12, 1e-12, boot_se_l)
        t_spa_boot_lower[b] = np.max(math.sqrt(T) * boot_means_l / boot_se_l)

        # Upper SPA: no recentering (most conservative)
        boot_means_u = np.mean(boot - mu_upper[np.newaxis, :], axis=0)
        boot_se_u = np.array([_hac_se(boot[:, j]) for j in range(k)])
        boot_se_u = np.where(boot_se_u < 1e-12, 1e-12, boot_se_u)
        t_spa_boot_upper[b] = np.max(math.sqrt(T) * boot_means_u / boot_se_u)

        # White RC: max of NON-studentized bootstrap means (no omega, no recenter).
        # White (2000): V_l^* = (1/n) sum_t f_{l,t}^* where f^* is the block-
        # resampled series.  Null: V_l^* - mu_bar_l where mu_bar_l = mean(d_l)
        # (RC uses sample-mean recentering for the stationary bootstrap version —
        # see White 2000 eq. (3.7), stationary bootstrap variant).
        boot_means_rc = np.mean(boot - means[np.newaxis, :], axis=0)  # recenter by sample mean
        t_rc_boot[b] = np.max(math.sqrt(T) * boot_means_rc)

    pvalue_consistent = float((1 + np.sum(t_spa_boot_consistent >= t_spa_obs)) / (B + 1))
    pvalue_lower = float((1 + np.sum(t_spa_boot_lower >= t_spa_obs)) / (B + 1))
    pvalue_upper = float((1 + np.sum(t_spa_boot_upper >= t_spa_obs)) / (B + 1))
    # White RC: compare observed non-studentized max against the RC bootstrap null
    white_rc_pvalue = float((1 + np.sum(t_rc_boot >= t_rc_obs)) / (B + 1))

    result = R5cResult(
        pvalue_consistent=pvalue_consistent,
        pvalue_lower=pvalue_lower,
        pvalue_upper=pvalue_upper,
        white_rc_pvalue=white_rc_pvalue,
        t_spa_obs=t_spa_obs,
        t_rc_obs=t_rc_obs,
        block_length_used=actual_block_length,
        block_length_auto=block_length_auto,
        B=B,
        seed=child_seed,
        lib_versions=_lib_versions(),
    )
    logger.info(
        '{"event": "r5c.result", "spa_consistent": %.6f, "spa_lower": %.6f,'
        ' "spa_upper": %.6f, "white_rc_pvalue": %.6f,'
        ' "t_spa_obs": %.4f, "t_rc_obs": %.4f,'
        ' "block_length": %d, "block_length_auto": %s}',
        result.pvalue_consistent,
        result.pvalue_lower,
        result.pvalue_upper,
        result.white_rc_pvalue,
        result.t_spa_obs,
        result.t_rc_obs,
        result.block_length_used,
        str(result.block_length_auto).lower(),
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
        Block length L used for R5a primary (Politis-White auto-selected or
        supplied by caller).
    block_length_auto:
        True if L was selected via Politis-White (2004) for R5a.
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
        SPA consistent p-value (primary decision statistic).
    r5c_spa_pvalue_lower:
        SPA lower p-value.
    r5c_spa_pvalue_upper:
        SPA upper p-value.
    r5c_white_rc_pvalue:
        White (2000) Reality Check p-value from the same draws as SPA.
        Expected to be >= r5c_spa_pvalue_consistent (RC is more conservative).
    r5_combined_verdict:
        "PASS", "FAIL", or "INCONCLUSIVE".
    permutation_pvalue:
        Flat mirror of r5a_circular_block_pvalue (for evaluator compatibility).
    """

    master_seed: int
    rng: str
    lib_versions: dict[str, str]
    block_length: int
    block_length_auto: bool
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
    r5c_white_rc_pvalue: float
    r5_combined_verdict: str
    permutation_pvalue: float  # Flat mirror of r5a_circular_block_pvalue

    def to_metrics_dict(self) -> dict[str, float]:
        """Return flat dict of scalar metrics for the evaluator.

        Only includes the keys that the falsification_evaluator reads via
        the R5 rubric triggers:
          - permutation_pvalue  (R5a mirror — existing aspirational field)
          - r5b_window_percentile
          - r5c_spa_pvalue_consistent
          - r5c_white_rc_pvalue (new — White RC cross-check)
        """
        return {
            "permutation_pvalue": self.permutation_pvalue,
            "r5b_window_percentile": self.r5b_window_percentile,
            "r5c_spa_pvalue_consistent": self.r5c_spa_pvalue_consistent,
            "r5c_white_rc_pvalue": self.r5c_white_rc_pvalue,
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

    # R5a: block_length=None → auto-select via Politis-White (2004)
    r5a = r5a_circular_block_bootstrap(oos_returns, master_seed=master_seed, B=B, block_length=None)
    r5b = r5b_window_placement(
        full_returns, oos_len=oos_len, master_seed=master_seed, step=r5b_step
    )
    # R5c: block_length=None → auto-select via Politis-White (max across pair columns)
    r5c = r5c_hansen_spa(pair_returns, master_seed=master_seed, block_length=None, B=B)

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
    sensitivity_dict = {L: r5a.sensitivity[L] for L in _SENSITIVITY_BLOCK_LENGTHS}

    logger.info(
        '{"event": "run_r5.combined", "verdict": "%s",'
        ' "r5a_pvalue": %.6f, "r5c_spa_consistent": %.6f,'
        ' "r5c_white_rc": %.6f, "r5b_window_pct": %.4f,'
        ' "r5a_block_length": %d, "r5a_block_length_auto": %s,'
        ' "r5c_block_length": %d, "r5c_block_length_auto": %s}',
        combined,
        r5a.pvalue,
        r5c.pvalue_consistent,
        r5c.white_rc_pvalue,
        r5b.window_percentile,
        r5a.block_length_used,
        str(r5a.block_length_auto).lower(),
        r5c.block_length_used,
        str(r5c.block_length_auto).lower(),
    )

    return R5CombinedResult(
        master_seed=master_seed,
        rng="numpy.PCG64",
        lib_versions=_lib_versions(),
        block_length=r5a.block_length_used,
        block_length_auto=r5a.block_length_auto,
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
        r5c_white_rc_pvalue=r5c.white_rc_pvalue,
        r5_combined_verdict=combined,
        permutation_pvalue=r5a.pvalue,  # flat mirror per spec
    )
