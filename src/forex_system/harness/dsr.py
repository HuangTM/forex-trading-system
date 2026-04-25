"""Deflated Sharpe Ratio (DSR) computation.

Bailey & Lopez de Prado (2014) — "The Deflated Sharpe Ratio: Correcting for
Selection Bias, Backtest Overfitting and Non-Normality."

DSR adjusts the Sharpe Ratio downward based on:
  - T: number of observations (bars)
  - skew: skewness of returns (non-normality penalty)
  - excess_kurtosis: kurtosis penalty
  - n_trials: total number of trials run org-wide (multiple-comparisons penalty)

The formula deflates the observed Sharpe by computing the expected maximum SR
from n_trials independent draws, then computing the probability that the
observed SR exceeds this benchmark.

Reference implementation follows the BLP (2014) equations:
  SR*(k) = ((1 - γ)Z^{-1}(1 - 1/k) + γZ^{-1}(1 - 1/(k*e))) / sqrt(T - 1)

Where γ = Euler-Mascheroni constant ≈ 0.5772156649,
      k = n_trials, e = Euler's number,
      Z^{-1} = inverse standard normal CDF.

DSR = Z( (SR_hat * sqrt(T-1) - SR*(k)) /
         sqrt(1 - skew*SR_hat + (kurtosis-1)/4 * SR_hat^2) )
"""

from __future__ import annotations

import math

import numpy as np


# Euler-Mascheroni constant
_EULER_MASCHERONI = 0.5772156649015328


def expected_max_sr(n_trials: int, n_observations: int) -> float:
    """Expected maximum Sharpe Ratio from n_trials independent trials.

    Equation (2) from BLP 2014.

    Args:
        n_trials: total number of trials in the registry (including this one)
        n_observations: number of return observations (bars)

    Returns:
        Expected maximum SR (annualized terms, but T-normalized)
    """
    if n_trials <= 0 or n_observations <= 1:
        return 0.0

    k = max(n_trials, 1)
    t = max(n_observations - 1, 1)

    # Inverse normal CDF approximation via scipy if available, else rational approx
    try:
        from scipy.stats import norm
        z_inv = norm.ppf
    except ImportError:
        # Fallback: rational approximation of probit
        def z_inv(p: float) -> float:  # type: ignore[misc]
            if p <= 0:
                return -8.0
            if p >= 1:
                return 8.0
            # Beasley-Springer-Moro algorithm approximation
            p = float(p)
            c = [2.515517, 0.802853, 0.010328]
            d = [1.432788, 0.189269, 0.001308]
            if p < 0.5:
                t_val = math.sqrt(-2.0 * math.log(p))
            else:
                t_val = math.sqrt(-2.0 * math.log(1.0 - p))
            num = c[0] + c[1] * t_val + c[2] * t_val ** 2
            den = 1.0 + d[0] * t_val + d[1] * t_val ** 2 + d[2] * t_val ** 3
            approx = t_val - num / den
            if p < 0.5:
                return -approx
            return approx

    # For k=1 there's no multiple-comparisons inflation — expected max SR = 0
    if k == 1:
        return 0.0

    # Clamp to avoid extreme values near 0 or 1
    arg1 = max(min(1.0 - 1.0 / k, 1.0 - 1e-9), 1e-9)
    arg2 = max(min(1.0 - 1.0 / (k * math.e), 1.0 - 1e-9), 1e-9)

    z1 = z_inv(arg1)
    z2 = z_inv(arg2)

    sr_star = ((1.0 - _EULER_MASCHERONI) * z1 + _EULER_MASCHERONI * z2) / math.sqrt(t)
    return max(float(sr_star), 0.0)


def compute_dsr(
    sharpe_ratio: float,
    n_observations: int,
    skewness: float,
    excess_kurtosis: float,
    n_trials: int,
) -> float:
    """Compute the Deflated Sharpe Ratio.

    Args:
        sharpe_ratio: annualized Sharpe (same scale as returned by calculate_metrics)
        n_observations: number of return observations (bars in backtest)
        skewness: skewness of the return series
        excess_kurtosis: excess kurtosis (kurtosis - 3)
        n_trials: number of trials in .fintech-org/trials.jsonl (including this one)

    Returns:
        DSR in [0, 1] — probability that the true SR exceeds the expected max SR.
        Values > 0.95 are considered statistically significant.
    """
    if n_observations <= 2 or sharpe_ratio <= 0:
        return 0.0

    try:
        from scipy.stats import norm
        z_cdf = norm.cdf
    except ImportError:
        # Simple approximation for CDF
        def z_cdf(x: float) -> float:  # type: ignore[misc]
            return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    sr_star = expected_max_sr(n_trials, n_observations)

    t = n_observations
    # Annualized SR → per-observation SR for DSR formula
    # BLP formula uses SR in per-observation terms; we keep annualized scale
    # and adjust denominator accordingly. Following common implementation:
    # variance of SR estimator = (1 - skew*SR + (kurt/4)*SR^2) / (T-1)
    kurtosis_term = (excess_kurtosis + 3.0) / 4.0  # uses full kurtosis
    variance_term = 1.0 - skewness * sharpe_ratio + kurtosis_term * sharpe_ratio ** 2

    if variance_term <= 0:
        variance_term = 1.0  # degenerate protection

    denominator = math.sqrt(variance_term / max(t - 1, 1))
    if denominator <= 0:
        return 0.0

    z_score = (sharpe_ratio - sr_star) / denominator
    dsr = float(z_cdf(z_score))
    return dsr
