"""Backtest arson test — signal sensitivity diagnostic.

Systematically degrades a strategy's signals and measures how performance
changes. This is a DIAGNOSTIC tool, not a pass/fail gate.

Interpretation:
- If degradation hurts Sharpe significantly: signals are load-bearing (good).
- If degradation barely matters: signals may be noise, or strategy is robust.
- If 2x costs kills the strategy: edge is thin, execution quality critical.
- If extra delay kills it: time-sensitive signal, potential lookahead concern.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import calculate_metrics
from forex_system.core.interfaces import CostModel, PositionSizer
from forex_system.core.types import Direction


@dataclass(frozen=True)
class DegradationResult:
    """Metrics from a single degradation mode."""

    name: str
    sharpe_ratio: float
    total_return: float
    max_drawdown: float
    num_trades: int


@dataclass(frozen=True)
class ArsonResult:
    """Full arson test diagnostic results."""

    baseline: DegradationResult
    degradations: list[DegradationResult]

    def summary(self) -> str:
        """Human-readable summary of sensitivity analysis."""
        lines = [
            "=== Backtest Arson Test ===",
            f"{'Mode':<20} {'Sharpe':>8} {'Return':>10} {'MaxDD':>8} {'Trades':>7}",
            "-" * 55,
            _format_row(self.baseline),
        ]
        for d in self.degradations:
            sharpe_delta = d.sharpe_ratio - self.baseline.sharpe_ratio
            lines.append(f"{_format_row(d)}  ({sharpe_delta:+.2f})")
        return "\n".join(lines)


class BacktestArsonTest:
    """Diagnostic: how sensitive is the strategy to signal degradation?"""

    def __init__(self, seed: int | None = None):
        self.seed = seed

    def run(
        self,
        data: pd.DataFrame,
        signals: pd.Series,
        pair: str,
        strategy_name: str,
        cost_model: CostModel,
        sizer: PositionSizer | None = None,
        initial_capital: float = 100_000.0,
    ) -> ArsonResult:
        """Run suite of degradation tests."""
        rng = np.random.default_rng(self.seed)

        # Baseline
        baseline = self._run_single(
            "baseline", data, signals, pair, strategy_name,
            cost_model, sizer, initial_capital,
        )

        degradations = []

        # 1. Randomize 10% of signals
        degradations.append(self._run_single(
            "randomize_10pct", data,
            _randomize_signals(signals, 0.10, rng),
            pair, strategy_name, cost_model, sizer, initial_capital,
        ))

        # 2. Randomize 25% of signals
        degradations.append(self._run_single(
            "randomize_25pct", data,
            _randomize_signals(signals, 0.25, rng),
            pair, strategy_name, cost_model, sizer, initial_capital,
        ))

        # 3. Double costs
        doubled_cost = _ScaledCostModel(cost_model, multiplier=2.0)
        degradations.append(self._run_single(
            "double_costs", data, signals,
            pair, strategy_name, doubled_cost, sizer, initial_capital,
        ))

        # 4. Extra delay (shift signals by 1 more bar)
        extra_delayed = signals.shift(1).fillna(0.0)
        degradations.append(self._run_single(
            "extra_delay", data, extra_delayed,
            pair, strategy_name, cost_model, sizer, initial_capital,
        ))

        return ArsonResult(baseline=baseline, degradations=degradations)

    def _run_single(
        self,
        name: str,
        data: pd.DataFrame,
        signals: pd.Series,
        pair: str,
        strategy_name: str,
        cost_model: CostModel,
        sizer: PositionSizer | None,
        initial_capital: float,
    ) -> DegradationResult:
        result = run_backtest(
            data=data, signals=signals, pair=pair,
            strategy_name=strategy_name, cost_model=cost_model,
            sizer=sizer, initial_capital=initial_capital,
        )
        metrics = calculate_metrics(result.equity_curve, result.trade_log)
        return DegradationResult(
            name=name,
            sharpe_ratio=metrics.sharpe_ratio,
            total_return=metrics.total_return,
            max_drawdown=metrics.max_drawdown,
            num_trades=metrics.num_trades,
        )


class _ScaledCostModel(CostModel):
    """Internal wrapper that scales all costs by a multiplier."""

    def __init__(self, inner: CostModel, multiplier: float = 2.0):
        self._inner = inner
        self._multiplier = multiplier

    def entry_cost(self, pair: str, size: float,
                   timestamp: pd.Timestamp | None = None) -> float:
        return self._inner.entry_cost(pair, size) * self._multiplier

    def exit_cost(self, pair: str, size: float,
                  timestamp: pd.Timestamp | None = None) -> float:
        return self._inner.exit_cost(pair, size) * self._multiplier

    def holding_cost(self, pair: str, direction: Direction, days: float) -> float:
        return self._inner.holding_cost(pair, direction, days) * self._multiplier


def _randomize_signals(
    signals: pd.Series, fraction: float, rng: np.random.Generator,
) -> pd.Series:
    """Replace `fraction` of signals with random values."""
    result = signals.copy()
    n = len(signals)
    mask = rng.random(n) < fraction
    random_vals = rng.choice([-1.0, 0.0, 1.0], size=int(mask.sum()))
    result.iloc[mask] = random_vals
    return result


def _format_row(d: DegradationResult) -> str:
    return (
        f"{d.name:<20} {d.sharpe_ratio:>8.2f} {d.total_return:>10.2%} "
        f"{d.max_drawdown:>8.2%} {d.num_trades:>7d}"
    )
