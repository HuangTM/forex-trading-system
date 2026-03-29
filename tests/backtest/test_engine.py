"""Tests for the backtest engine — including the sacred no-lookahead test."""

import numpy as np
import pandas as pd

from forex_system.backtest.engine import run_backtest
from forex_system.costs.model import RealisticCostModel
from forex_system.features.registry import compute_indicators


def test_basic_backtest(sample_ohlcv):
    """Engine produces valid results with constant long signal."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    signals = pd.Series(1.0, index=enriched.index)  # Always long
    cost_model = RealisticCostModel()

    result = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="test",
        cost_model=cost_model,
        initial_capital=100_000.0,
    )

    assert len(result.equity_curve.dropna()) > 0
    assert result.pair == "EURUSD"
    assert result.strategy_name == "test"


def test_no_signals_no_trades(sample_ohlcv):
    """Zero signals should produce zero trades."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    signals = pd.Series(0.0, index=enriched.index)
    cost_model = RealisticCostModel()

    result = run_backtest(
        data=enriched,
        signals=signals,
        pair="EURUSD",
        strategy_name="test",
        cost_model=cost_model,
    )

    assert len(result.trade_log) == 0
    # Equity should be unchanged
    ec = result.equity_curve.dropna()
    assert ec.iloc[-1] == ec.iloc[0]


def test_no_lookahead(sample_ohlcv):
    """THE SACRED TEST: engine must not use future data.

    Strategy: signal = +1 if NEXT bar's close > current close (trivially profitable
    with lookahead). With entry_delay_bars=1, this signal should NOT consistently
    profit because by the time we enter, the move already happened.
    """
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    # Lookahead signal: +1 when next bar rises, -1 when it falls
    future_return = enriched["close"].shift(-1) - enriched["close"]
    lookahead_signals = pd.Series(0.0, index=enriched.index)
    lookahead_signals[future_return > 0] = 1.0
    lookahead_signals[future_return < 0] = -1.0

    cost_model = RealisticCostModel()
    result = run_backtest(
        data=enriched,
        signals=lookahead_signals,
        pair="EURUSD",
        strategy_name="lookahead_test",
        cost_model=cost_model,
        entry_delay_bars=1,
    )

    # With proper delay, this should NOT be consistently profitable
    # The lookahead signal becomes a lagging signal after shift
    ec = result.equity_curve.dropna()
    # We don't assert loss, just that it's not suspiciously profitable
    # A Sharpe > 3 would indicate the engine is leaking future data
    if len(ec) > 10:
        daily_returns = ec.pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            assert sharpe < 3.0, f"Suspiciously high Sharpe ({sharpe:.1f}) — possible lookahead"


def test_costs_reduce_equity(sample_ohlcv):
    """Trades with costs should produce lower equity than without."""
    enriched = compute_indicators(sample_ohlcv, ["atr_14"])
    enriched = enriched.dropna(subset=["atr_14"])

    # Alternate long/short every 10 bars
    signals = pd.Series(0.0, index=enriched.index)
    for i in range(0, len(signals), 20):
        signals.iloc[i:i + 10] = 1.0
        if i + 10 < len(signals):
            signals.iloc[i + 10:i + 20] = -1.0

    # High-cost model
    from forex_system.core.types import PairInfo
    expensive = {"EURUSD": PairInfo("EURUSD", 0.0001, 5.0, 5.0, 5.0, -1.2, 0.3)}
    expensive_cost = RealisticCostModel(expensive)

    # Zero-cost model
    cheap = {"EURUSD": PairInfo("EURUSD", 0.0001, 0.0, 0.0, 0.0, 0.0, 0.0)}
    cheap_cost = RealisticCostModel(cheap)

    result_expensive = run_backtest(
        data=enriched, signals=signals, pair="EURUSD", strategy_name="test",
        cost_model=expensive_cost,
    )
    result_cheap = run_backtest(
        data=enriched, signals=signals, pair="EURUSD", strategy_name="test",
        cost_model=cheap_cost,
    )

    ec_expensive = result_expensive.equity_curve.dropna()
    ec_cheap = result_cheap.equity_curve.dropna()

    # Expensive should end lower than cheap
    assert ec_expensive.iloc[-1] < ec_cheap.iloc[-1]
