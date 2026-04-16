"""Null hypothesis gate — statistical validation for strategy significance.

Generates N random strategies with the same trade frequency and holding period
as the candidate, runs each through the backtest engine, and ranks the candidate.
If the candidate isn't in the top percentile (DSR-adjusted), it's noise.

Reference: Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio"
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.core.interfaces import CostModel, PositionSizer


@dataclass(frozen=True)
class NullHypothesisResult:
    """Result of null hypothesis significance test."""

    passed: bool
    candidate_sharpe: float
    candidate_rank_pct: float  # Percentile rank among random strategies
    random_sharpe_mean: float
    random_sharpe_std: float
    dsr_adjusted_pvalue: float
    total_trials: int
    n_random: int


class NullHypothesisGate:
    """Statistical gate: is this strategy distinguishable from random?

    The test must be run on held-out out-of-sample data that was NEVER
    used for strategy development or parameter tuning.
    """

    def __init__(
        self,
        n_random: int = 1000,
        percentile: float = 95.0,
        seed: int | None = None,
    ):
        self.n_random = n_random
        self.percentile = percentile
        self.seed = seed

    def test(
        self,
        candidate_result: BacktestResult,
        data: pd.DataFrame,
        pair: str,
        cost_model: CostModel,
        sizer: PositionSizer | None = None,
        initial_capital: float = 100_000.0,
        total_trials: int = 1,
    ) -> NullHypothesisResult:
        """Run null hypothesis test on held-out data.

        Args:
            candidate_result: Backtest result of the candidate strategy.
            data: The held-out OHLCV data (must not overlap with dev data).
            pair: Currency pair.
            cost_model: Transaction cost model.
            sizer: Optional position sizer.
            initial_capital: Starting capital for each random backtest.
            total_trials: Total strategies ever tested (for DSR correction).

        Returns:
            NullHypothesisResult with pass/fail, rank, and p-value.
        """
        rng = np.random.default_rng(self.seed)

        candidate_metrics = calculate_metrics(
            candidate_result.equity_curve, candidate_result.trade_log
        )
        candidate_sharpe = candidate_metrics.sharpe_ratio

        # Measure candidate signal characteristics for random generation
        ref_signals = candidate_result.signals
        trade_freq = _estimate_trade_frequency(ref_signals)

        # Generate and evaluate random strategies
        random_sharpes = []
        for _ in range(self.n_random):
            random_signals = _generate_random_signals(ref_signals, trade_freq, rng)
            random_result = run_backtest(
                data=data,
                signals=random_signals,
                pair=pair,
                strategy_name="random_null",
                cost_model=cost_model,
                sizer=sizer,
                initial_capital=initial_capital,
            )
            random_metrics = calculate_metrics(
                random_result.equity_curve, random_result.trade_log
            )
            random_sharpes.append(random_metrics.sharpe_ratio)

        random_sharpes_arr = np.array(random_sharpes)
        rank_pct = float(np.mean(random_sharpes_arr < candidate_sharpe) * 100.0)
        sr_mean = float(np.mean(random_sharpes_arr))
        sr_std = float(np.std(random_sharpes_arr))

        # DSR adjustment for multiple testing
        dsr_pvalue = _deflated_sharpe_pvalue(
            candidate_sharpe, sr_mean, sr_std, total_trials,
        )

        passed = rank_pct >= self.percentile and dsr_pvalue < 0.05

        return NullHypothesisResult(
            passed=passed,
            candidate_sharpe=candidate_sharpe,
            candidate_rank_pct=rank_pct,
            random_sharpe_mean=sr_mean,
            random_sharpe_std=sr_std,
            dsr_adjusted_pvalue=dsr_pvalue,
            total_trials=total_trials,
            n_random=self.n_random,
        )


def _estimate_trade_frequency(signals: pd.Series) -> float:
    """Estimate fraction of bars where the signal changes direction."""
    changes = signals.diff().fillna(0.0)
    return float((changes.abs() > 1e-6).mean())


def _generate_random_signals(
    reference: pd.Series,
    change_freq: float,
    rng: np.random.Generator,
) -> pd.Series:
    """Generate random signals matching reference direction-change frequency.

    Creates a signal series that changes direction at the same rate as the
    reference, with random long/short/flat choices at each change point.
    """
    n = len(reference)
    signals = pd.Series(0.0, index=reference.index)

    # Determine change points
    change_mask = rng.random(n) < change_freq
    # First bar is always a potential change
    change_mask[0] = True

    # Random direction at each change: -1, 0, +1
    directions = rng.choice([-1.0, 0.0, 1.0], size=n, p=[0.33, 0.34, 0.33])

    # Apply directions only at change points, forward-fill between them
    current_dir = 0.0
    for i in range(n):
        if change_mask[i]:
            current_dir = directions[i]
        signals.iloc[i] = current_dir

    return signals


def _deflated_sharpe_pvalue(
    candidate_sr: float,
    null_mean: float,
    null_std: float,
    total_trials: int,
) -> float:
    """Compute DSR-adjusted p-value (Bailey & Lopez de Prado, 2014).

    Adjusts the significance of a Sharpe ratio by accounting for the
    expected maximum Sharpe ratio under the null hypothesis, given
    the total number of strategies tested.
    """
    if total_trials <= 1 or null_std < 1e-10:
        # No correction needed / not enough variance
        if null_std < 1e-10:
            return 0.0 if candidate_sr > null_mean else 1.0
        z = (candidate_sr - null_mean) / null_std
        return float(1.0 - stats.norm.cdf(z))

    # Expected maximum SR under null (Euler-Mascheroni approximation)
    # E[max(SR)] ≈ mean + std * ((1 - γ) * Φ⁻¹(1 - 1/N) + γ * Φ⁻¹(1 - 1/(N*e)))
    gamma = 0.5772156649  # Euler-Mascheroni constant
    e_max_sr = null_mean + null_std * (
        (1 - gamma) * stats.norm.ppf(1 - 1.0 / total_trials)
        + gamma * stats.norm.ppf(1 - 1.0 / (total_trials * np.e))
    )

    # Test: is candidate SR significantly above the expected max?
    z = (candidate_sr - e_max_sr) / null_std
    return float(1.0 - stats.norm.cdf(z))


# Import here to avoid circular import at module level
from forex_system.core.types import BacktestResult  # noqa: E402
