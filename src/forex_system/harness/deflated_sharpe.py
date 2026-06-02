"""Deflated Sharpe Ratio (DSR) — Bailey & Lopez de Prado (2014), equation 10.

Reconciliation note (2026-05-31):
    This module previously contained a divergent implementation of the DSR
    formula alongside dsr.py::compute_dsr.  The Mathematician identified three
    correctness defects (units bug, kurtosis off-by-one, fabricated guard) that
    were present in both implementations.

    Resolution: the canonical corrected implementation now lives in
    dsr.py::compute_dsr (with the new required ``periods_per_year`` parameter).
    This module is kept as a thin compatibility shim so that:
      - backfill_dsr_existing_trials.py and its tests need no code changes.
      - A single source of truth (dsr.py) is maintained — DRY.

    The shim ``deflated_sharpe()`` signature is UNCHANGED (no breaking change for
    existing callers).  It hard-codes periods_per_year=252 (daily bars) because
    all historical trial records were computed on daily OHLCV data.  If a caller
    needs a different annualisation factor it should call compute_dsr() directly.

Public API (unchanged)
----------------------
deflated_sharpe(sharpe, n_trials, n_obs, skew, excess_kurtosis) -> float
"""

from __future__ import annotations

from forex_system.core.constants import TRADING_DAYS_PER_YEAR
from forex_system.harness.dsr import compute_dsr

# Daily bars — matches the annualisation factor in backtest/metrics.py
_DAILY_PERIODS_PER_YEAR: float = float(TRADING_DAYS_PER_YEAR)


def deflated_sharpe(
    sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    excess_kurtosis: float = 0.0,
) -> float:
    """Compute the Deflated Sharpe Ratio per Bailey & Lopez de Prado (2014).

    Thin shim over dsr.compute_dsr with periods_per_year=252 (daily bars).
    All correctness fixes are in dsr.compute_dsr — see that module for details.

    Parameters
    ----------
    sharpe:
        Observed annualised Sharpe Ratio. Negative or zero values return 0.0.
    n_trials:
        Number of trials in the registry AT SPAWN TIME (n_trials_at_spawn).
        MUST be sourced from the trial record — never silently defaulted.
        Raises ValueError if < 1.
    n_obs:
        Number of return observations (bars in the evaluation window).
        Raises ValueError if <= 1.
    skew:
        Skewness of the return series. Default 0.0.
    excess_kurtosis:
        Excess kurtosis (kurtosis - 3, Fisher convention). Default 0.0.

    Returns
    -------
    float
        DSR in [0.0, 1.0].

    Raises
    ------
    ValueError
        If n_trials < 1 or n_obs <= 1.
    """
    return compute_dsr(
        sharpe_ratio=sharpe,
        n_observations=n_obs,
        skewness=skew,
        excess_kurtosis=excess_kurtosis,
        n_trials=n_trials,
        periods_per_year=_DAILY_PERIODS_PER_YEAR,
    )
