"""Walk-forward optimization — prevents overfitting by construction.

Splits data into rolling train/test windows, evaluates out-of-sample
performance across multiple periods.
"""

from dataclasses import dataclass

import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.backtest.metrics import PerformanceMetrics, calculate_metrics
from forex_system.core.interfaces import CostModel, PositionSizer, Strategy
from forex_system.features.registry import compute_indicators


@dataclass
class WalkForwardWindow:
    """Result from a single walk-forward window."""

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    metrics: PerformanceMetrics
    num_test_bars: int


@dataclass
class WalkForwardResult:
    """Aggregate walk-forward results."""

    windows: list[WalkForwardWindow]
    pair: str
    strategy_name: str

    @property
    def avg_sharpe(self) -> float:
        sharpes = [w.metrics.sharpe_ratio for w in self.windows]
        return sum(sharpes) / len(sharpes) if sharpes else 0.0

    @property
    def avg_max_drawdown(self) -> float:
        dds = [w.metrics.max_drawdown for w in self.windows]
        return sum(dds) / len(dds) if dds else 0.0

    @property
    def total_trades(self) -> int:
        return sum(w.metrics.num_trades for w in self.windows)

    @property
    def consistent(self) -> bool:
        """True if majority of windows show positive Sharpe."""
        if not self.windows:
            return False
        positive = sum(1 for w in self.windows if w.metrics.sharpe_ratio > 0)
        return positive > len(self.windows) / 2


def run_walkforward(
    data: pd.DataFrame,
    strategy: Strategy,
    pair: str,
    cost_model: CostModel,
    train_days: int = 504,
    test_days: int = 126,
    step_days: int = 63,
    initial_capital: float = 100_000.0,
    risk_per_trade: float = 0.02,
    stop_loss_atr_multiple: float = 2.0,
    sizer: PositionSizer | None = None,
) -> WalkForwardResult:
    """Run walk-forward analysis across rolling windows.

    Args:
        data: Raw OHLCV data (indicators will be computed per window)
        strategy: Strategy instance
        pair: Currency pair symbol
        cost_model: Cost model
        train_days: Training window in trading days
        test_days: Test window in trading days
        step_days: Step size for rolling (overlap between windows)
        initial_capital: Starting capital per window
        risk_per_trade: Risk fraction per trade
        stop_loss_atr_multiple: ATR stop multiplier
    """
    windows: list[WalkForwardWindow] = []
    total_bars = len(data)

    start_idx = 0
    while start_idx + train_days + test_days <= total_bars:
        train_end_idx = start_idx + train_days
        test_end_idx = min(train_end_idx + test_days, total_bars)

        # Split data
        test_data = data.iloc[train_end_idx:test_end_idx].copy()

        if len(test_data) < 10:  # Skip tiny windows
            start_idx += step_days
            continue

        # Compute indicators using lookback from training period for warmup
        indicator_lookback = max(train_days, 250)
        lookback_start = max(0, train_end_idx - indicator_lookback)
        full_window = data.iloc[lookback_start:test_end_idx].copy()
        enriched = compute_indicators(full_window, strategy.required_indicators())

        # Ensure ATR is available for position sizing
        if "atr_14" not in enriched.columns:
            enriched = compute_indicators(enriched, ["atr_14"])

        # Generate signals on the full enriched window
        signals = strategy.generate_signals(enriched)

        # Trim to test period only
        test_enriched = enriched.loc[test_data.index[0]:test_data.index[-1]]
        test_signals = signals.loc[test_data.index[0]:test_data.index[-1]]

        # Run backtest on test window
        result = run_backtest(
            data=test_enriched,
            signals=test_signals,
            pair=pair,
            strategy_name=strategy.name,
            cost_model=cost_model,
            initial_capital=initial_capital,
            risk_per_trade=risk_per_trade,
            stop_loss_atr_multiple=stop_loss_atr_multiple,
            sizer=sizer,
        )

        metrics = calculate_metrics(result.equity_curve, result.trade_log)

        windows.append(WalkForwardWindow(
            train_start=data.index[start_idx],
            train_end=data.index[train_end_idx - 1],
            test_start=test_data.index[0],
            test_end=test_data.index[-1],
            metrics=metrics,
            num_test_bars=len(test_data),
        ))

        start_idx += step_days

    return WalkForwardResult(
        windows=windows,
        pair=pair,
        strategy_name=strategy.name,
    )
