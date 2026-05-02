"""Deflated Sharpe Ratio (DSR) — Bailey & Lopez de Prado (2014), equation 10.

Public API
----------
deflated_sharpe(sharpe, n_trials, n_obs, skew, excess_kurtosis) -> float

DSR measures the probability that the observed Sharpe Ratio (SR_obs) exceeds
the expected maximum SR from N independent trials drawn from the same
distribution, adjusted for non-normality of returns.

Formula (BLP 2014, eq. 10):

    SR*(N) = E[max SR | N trials]
           ≈ ((1 - γ) * Φ^{-1}(1 - 1/N) + γ * Φ^{-1}(1 - 1/(N*e))) / sqrt(T - 1)

    DSR = Φ(
            (SR_obs - SR*(N)) /
            sqrt((1 - skew*SR_obs + ((kurt+1)/4)*SR_obs²) / (T-1))
          )

Where:
    γ = Euler-Mascheroni constant ≈ 0.5772156649
    Φ^{-1} = inverse standard normal CDF (scipy.stats.norm.ppf)
    T = n_obs (number of return observations)
    kurt = excess_kurtosis (kurtosis - 3)

Caller contract
---------------
- n_trials MUST be n_trials_at_spawn from the trial record. Never pass a
  fixed default — the caller is responsible for sourcing this from the
  registry entry. This module raises ValueError if n_trials < 1.
- n_obs MUST be the number of return observations (bars). Raises ValueError
  if n_obs < 2.
- Returns float in [0.0, 1.0]. 0.0 means the observed SR is indistinguishable
  from the expected maximum; 1.0 means it is far above.

References
----------
Bailey, D. H., & Lopez de Prado, M. (2014). The Deflated Sharpe Ratio:
Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
Journal of Portfolio Management, 40(5), 94–107.
"""

from __future__ import annotations

import math

from scipy.stats import norm  # required; no silent fallback

# Euler-Mascheroni constant
_EULER_MASCHERONI: float = 0.5772156649015328


def _expected_max_sr(n_trials: int, n_obs: int) -> float:
    """Compute E[max SR | N trials] via the Euler-Mascheroni approximation.

    Implements BLP (2014) equation (2).

    Parameters
    ----------
    n_trials:
        Number of independent trials (≥1; sourced from n_trials_at_spawn).
    n_obs:
        Number of return observations T (bars); used as sqrt(T-1) denominator.

    Returns
    -------
    float
        Expected maximum SR (non-negative). Returns 0.0 for n_trials == 1
        (no multiple-comparisons inflation with a single trial).
    """
    if n_trials == 1:
        # Single trial: no multiple-comparisons benchmark to beat.
        return 0.0

    t = max(n_obs - 1, 1)

    # Clamp arguments to avoid ppf(0) and ppf(1) which diverge.
    arg1 = max(min(1.0 - 1.0 / n_trials, 1.0 - 1e-9), 1e-9)
    arg2 = max(min(1.0 - 1.0 / (n_trials * math.e), 1.0 - 1e-9), 1e-9)

    z1: float = norm.ppf(arg1)
    z2: float = norm.ppf(arg2)

    sr_star = ((1.0 - _EULER_MASCHERONI) * z1 + _EULER_MASCHERONI * z2) / math.sqrt(t)
    return max(float(sr_star), 0.0)


def deflated_sharpe(
    sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    excess_kurtosis: float = 0.0,
) -> float:
    """Compute the Deflated Sharpe Ratio per Bailey & Lopez de Prado (2014).

    Parameters
    ----------
    sharpe:
        Observed Sharpe Ratio (annualized). Negative values return 0.0
        (the null is not falsified).
    n_trials:
        Number of trials in the registry AT SPAWN TIME (n_trials_at_spawn).
        MUST be sourced from the trial record — never silently defaulted.
        Raises ValueError if < 1.
    n_obs:
        Number of return observations (bars in the evaluation window).
        Raises ValueError if < 2.
    skew:
        Skewness of the return series. Default 0.0 (normal distribution).
    excess_kurtosis:
        Excess kurtosis (kurtosis - 3). Default 0.0 (normal distribution).

    Returns
    -------
    float
        DSR in [0.0, 1.0]. Values > 0.50 indicate the observed SR is more
        likely genuine than a false positive from multiple comparisons.
        The NHT Phase 2 rejection threshold is DSR < 0.50 (R2).

    Raises
    ------
    ValueError
        If n_trials < 1 or n_obs < 2 (prevents silent miscalculation).
    """
    if n_trials < 1:
        raise ValueError(
            f"n_trials must be ≥ 1; got {n_trials}. "
            "Source this from n_trials_at_spawn in the trial record."
        )
    if n_obs < 2:
        raise ValueError(
            f"n_obs must be ≥ 2; got {n_obs}. "
            "Need at least 2 return observations to estimate SR variance."
        )

    # Non-positive Sharpe cannot exceed the expected maximum positive SR.
    if sharpe <= 0.0:
        return 0.0

    sr_star = _expected_max_sr(n_trials=n_trials, n_obs=n_obs)

    # Variance of the SR estimator (BLP 2014, eq. 9).
    # Uses excess_kurtosis: (excess_kurtosis + 1) / 4 follows from
    # V[SR] ≈ (1 - skew*SR + ((kurt-1)/4)*SR²) / (T-1) where kurt = excess_k + 3
    # => (excess_kurtosis + 3 - 1) / 4 = (excess_kurtosis + 2) / 4
    # BLP's published eq. 10 writes the denominator term as:
    #   1 - skew * SR + (kurtosis / 4) * SR^2     (kurtosis = excess + 3)
    # which simplifies to: 1 - skew*SR + ((excess_kurtosis + 3)/4) * SR^2
    kurtosis_term = (excess_kurtosis + 3.0) / 4.0
    variance_term = 1.0 - skew * sharpe + kurtosis_term * sharpe ** 2

    if variance_term <= 0.0:
        # Degenerate: protect against sqrt of negative number.
        variance_term = 1.0

    t = max(n_obs - 1, 1)
    sigma_sr = math.sqrt(variance_term / t)

    if sigma_sr <= 0.0:
        return 0.0

    z_score = (sharpe - sr_star) / sigma_sr
    dsr = float(norm.cdf(z_score))
    return max(0.0, min(1.0, dsr))
