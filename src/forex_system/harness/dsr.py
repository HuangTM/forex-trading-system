"""Deflated Sharpe Ratio (DSR) computation.

Bailey & Lopez de Prado (2014) — "The Deflated Sharpe Ratio: Correcting for
Selection Bias, Backtest Overfitting and Non-Normality."

DSR adjusts the Sharpe Ratio downward based on:
  - T: number of observations (bars)
  - skew: skewness of returns (non-normality penalty)
  - excess_kurtosis: kurtosis penalty
  - n_trials: total number of trials run org-wide (multiple-comparisons penalty)
  - periods_per_year: annualisation factor used when computing sharpe_ann
    (252 for daily bars; must match what calculate_metrics() used)

The formula deflates the observed Sharpe by computing the expected maximum SR
from n_trials independent draws, then computing the probability that the
observed SR exceeds this benchmark.

Reference implementation follows the BLP (2014) equations:
  SR*(k) = ((1 - γ)Z^{-1}(1 - 1/k) + γZ^{-1}(1 - 1/(k*e))) / sqrt(T - 1)

Where γ = Euler-Mascheroni constant ≈ 0.5772156649,
      k = n_trials, e = Euler's number,
      Z^{-1} = inverse standard normal CDF.

Units discipline (Mathematician corrected formula, 2026-05-31):
  All SR quantities are per-observation (not annualised).
  SR_pp = sharpe_ann / sqrt(periods_per_year)   converts to per-obs scale.
  SR_star is already per-obs (its denominator is sqrt(T-1)).
  z = (SR_pp - SR_star) * sqrt(T-1) / sqrt(var_term) is dimensionless and O(1).

DSR = Φ(z), clipped to [0, 1].
"""

from __future__ import annotations

import logging
import math


logger = logging.getLogger(__name__)

# Euler-Mascheroni constant
_EULER_MASCHERONI = 0.5772156649015328


def expected_max_sr(n_trials: int, n_observations: int) -> float:
    """Expected maximum per-observation Sharpe Ratio from n_trials independent trials.

    Equation (2) from BLP 2014.  Returns a per-observation SR (denominator
    sqrt(T-1) keeps it in the same units as SR_pp).

    Args:
        n_trials: total number of trials in the registry (including this one)
        n_observations: number of return observations (bars)

    Returns:
        Expected maximum SR (per-observation scale, non-negative).
        Returns 0.0 for n_trials == 1 (no multiple-comparisons inflation).
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
    periods_per_year: float,
) -> float:
    """Compute the Deflated Sharpe Ratio.

    Corrected implementation per Mathematician spec 2026-05-31.  Three defects
    from the previous version are fixed:

    1. Units bug: sharpe_ratio is annualised.  We first convert to per-observation
       scale: SR_pp = sharpe_ratio / sqrt(periods_per_year).  All subsequent
       quantities (SR_star, sigma_SR) are per-observation, so the z-ratio is
       dimensionless and O(1).  The old code omitted this conversion, inflating
       z by ~sqrt(periods_per_year) and saturating DSR near 1.0.

    2. Kurtosis off-by-one: canonical var-of-SR term uses (excess_kurtosis + 2)/4,
       not (excess_kurtosis + 3)/4.  Derivation: V[SR] contains gamma4/4 where
       gamma4 = excess_kurtosis + 3 (non-excess), giving (excess_kurtosis+3-1)/4
       = (excess_kurtosis+2)/4.

    3. Fabricated guard: the old code reset variance_term to 1.0 when non-positive,
       silently inventing a value.  We now return 0.0 and log a structured warning.

    Args:
        sharpe_ratio: annualized Sharpe (same scale as returned by calculate_metrics)
        n_observations: number of return observations (bars in backtest)
        skewness: skewness of the return series
        excess_kurtosis: excess kurtosis (kurtosis - 3, i.e. Fisher convention)
        n_trials: number of trials in .fintech-org/trials.jsonl (including this one)
        periods_per_year: annualisation factor used by calculate_metrics (252 for
            daily bars — must match the sqrt(P) factor in the Sharpe computation).
            Raises ValueError if <= 0.

    Returns:
        DSR in [0, 1] — probability that the true SR exceeds the expected max SR.
        Values > 0.50 indicate the SR is more likely genuine than a false positive.

    Raises:
        ValueError: if n_observations <= 1, n_trials < 1, or periods_per_year <= 0.
    """
    # --- Input validation ---
    if n_observations <= 1:
        raise ValueError(
            f"n_observations must be > 1; got {n_observations}. "
            "Need at least 2 return observations to estimate SR variance."
        )
    if n_trials < 1:
        raise ValueError(
            f"n_trials must be >= 1; got {n_trials}. "
            "Source this from n_trials_at_spawn in the trial record."
        )
    if periods_per_year <= 0:
        raise ValueError(
            f"periods_per_year must be > 0; got {periods_per_year}."
        )

    # Non-positive Sharpe cannot exceed the expected maximum positive SR.
    if sharpe_ratio <= 0.0:
        return 0.0

    try:
        from scipy.stats import norm
        z_cdf = norm.cdf
    except ImportError:
        # Simple approximation for CDF
        def z_cdf(x: float) -> float:  # type: ignore[misc]
            return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    # Step 1: convert annualised SR to per-observation SR (units fix)
    sr_pp = sharpe_ratio / math.sqrt(periods_per_year)

    # Step 2: variance of the SR estimator — corrected kurtosis term
    # V[SR_hat] ≈ (1 - skew*SR + ((excess_k+2)/4)*SR^2) / (T-1)
    kurtosis_term = (excess_kurtosis + 2.0) / 4.0
    variance_term = 1.0 - skewness * sr_pp + kurtosis_term * sr_pp ** 2

    if variance_term <= 0.0:
        # Degenerate: cannot certify — return 0.0 and emit structured warning.
        logger.warning(
            '{"event": "dsr.variance_term.degenerate", "variance_term": %s, '
            '"skewness": %s, "excess_kurtosis": %s, "sr_pp": %s, '
            '"action": "return_0.0_cannot_certify"}',
            variance_term, skewness, excess_kurtosis, sr_pp,
        )
        return 0.0

    # Step 3: expected max SR (per-observation scale; k=1 → 0)
    sr_star = expected_max_sr(n_trials, n_observations)

    # Step 4: z-score (dimensionless; O(1))
    # z = (SR_pp - SR_star) * sqrt(T-1) / sqrt(var_term)
    t = n_observations
    z_score = (sr_pp - sr_star) * math.sqrt(t - 1) / math.sqrt(variance_term)

    # Step 5: DSR = Φ(z), clipped to [0, 1]
    dsr = float(z_cdf(z_score))
    return max(0.0, min(1.0, dsr))
