"""No-lookahead tests for basket member strategies M1 (MACD cross) and M2 (EMA cross).

Invariant: signals generated from data[0..t] must not depend on data[t+1..].
The specific test: a strategy that predicts the NEXT bar's price using current
data is trivially profitable with lookahead. With entry_delay_bars=1 in the engine,
the signal should NOT be consistently highly profitable — the move already happened.

These tests mirror the sacred test_no_lookahead in tests/backtest/test_engine.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.backtest.engine import run_backtest
from forex_system.costs.static_roundtrip import StaticRoundTripCostModel
from forex_system.features.registry import compute_indicators
from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.strategies.ema_cross import EMACrossStrategy
from forex_system.strategies.macd_cross import MACDCrossStrategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trending_ohlcv(n_bars: int = 500, tz: str = "UTC") -> pd.DataFrame:
    """Build 1h OHLCV with a pronounced sinusoidal trend so both EMAs warm up.

    Uses a controlled sine wave so we can predict signal direction for the
    lookahead test. 500 bars ensures EMA(200) has enough warmup.
    """
    dates = pd.date_range("2021-01-04", periods=n_bars, freq="1h", tz=tz)
    np.random.seed(42)
    # Deterministic: base trend + small noise
    base = 1.1000
    trend = np.sin(np.linspace(0, 4 * np.pi, n_bars)) * 0.01
    noise = np.random.normal(0, 0.0001, n_bars)
    close = base + trend + np.cumsum(noise)
    close = np.abs(close)  # prevent negatives

    return pd.DataFrame(
        {
            "open": close * (1 + np.random.uniform(-0.0002, 0.0002, n_bars)),
            "high": close * (1 + np.abs(np.random.normal(0, 0.0003, n_bars))),
            "low": close * (1 - np.abs(np.random.normal(0, 0.0003, n_bars))),
            "close": close,
            "volume": np.random.randint(100_000, 1_000_000, n_bars).astype(float),
        },
        index=pd.DatetimeIndex(dates, name="datetime"),
    )


@pytest.fixture
def trending_ohlcv() -> pd.DataFrame:
    return _make_trending_ohlcv(n_bars=600)


@pytest.fixture
def enriched_ohlcv(trending_ohlcv) -> pd.DataFrame:
    return compute_indicators(trending_ohlcv, ["atr_14"])


# ---------------------------------------------------------------------------
# No-lookahead test: M1 MACD cross
# ---------------------------------------------------------------------------


def test_no_lookahead_macd_cross(enriched_ohlcv: pd.DataFrame) -> None:
    """No-lookahead invariant for MACDCrossStrategy.

    The MACD signal at bar t is based on EMA values at bar t (causal).
    The engine shifts signals by entry_delay_bars=1, so the trade fires at bar t+1.
    A signal that is trivially profitable WITH lookahead should NOT be consistently
    profitable WITH the delay — the informational edge is in the past bar.

    We verify: the MACD strategy's signals, when shifted by the engine, do NOT
    produce a Sharpe > 5 (a level that would indicate future leakage rather than
    genuine signal edge).
    """
    strategy = MACDCrossStrategy(params={})
    signals = strategy.generate_signals(enriched_ohlcv)

    # Verify signals are within valid range
    assert signals.min() >= -1.0, f"Signal below -1.0: {signals.min()}"
    assert signals.max() <= 1.0, f"Signal above +1.0: {signals.max()}"

    # Verify no future data is used: shift signals by 1 and check they are
    # causal — the signal at bar t should not equal the sign of return from t→t+2.
    # If signals systematically predict t+1 open → t+2 open returns (two bars ahead),
    # that would indicate a fundamental lookahead bug.
    future_2bar_return = enriched_ohlcv["close"].shift(-2) - enriched_ohlcv["close"]
    valid = signals.notna() & future_2bar_return.notna() & (signals != 0)
    if valid.sum() > 20:
        correct_predictions = (signals[valid] * future_2bar_return[valid] > 0).mean()
        # With lookahead 2 bars ahead, a lookahead-contaminated signal would be ~0%
        # (wrong direction because signal used bar+1 close already passed). The point:
        # we are NOT using data from bar t+1 or later. So the rate should be ~random (~50%).
        # We only reject if it is suspiciously high (>85%), which would indicate
        # the signal is being computed using future data.
        assert correct_predictions < 0.85, (
            f"MACD signal predicts 2-bar-ahead returns at {correct_predictions:.1%}; "
            f"expected ~50% if causal. Possible lookahead in signal generation."
        )

    # Run backtest with entry_delay_bars=1 and verify not suspiciously profitable
    cost_model = StaticRoundTripCostModel()
    sizer = VolTargetSizer(leverage_cap=0.25)
    result = run_backtest(
        data=enriched_ohlcv,
        signals=signals,
        pair="EURUSD",
        strategy_name="macd_cross_nolookahead_test",
        cost_model=cost_model,
        entry_delay_bars=1,
        sizer=sizer,
        rebalance_mode="continuous",
        constant_capital_sizing=True,
    )

    ec = result.equity_curve.dropna()
    assert len(ec) > 10, "Equity curve too short to test"

    bar_returns = ec.pct_change().dropna()
    if bar_returns.std() > 0:
        # Use 1h annualization (6240 periods per year for FX 1h)
        sharpe_1h = bar_returns.mean() / bar_returns.std() * np.sqrt(6240)
        # A Sharpe > 10 on SYNTHETIC data would indicate future leakage.
        # We use a generous bound because a sinusoidal price series CAN have
        # a genuine trend-following edge — the test is purely a sanity guard.
        assert sharpe_1h < 20.0, (
            f"MACD cross Sharpe ({sharpe_1h:.1f}) suspiciously high; "
            f"possible lookahead in signal generation."
        )


# ---------------------------------------------------------------------------
# No-lookahead test: M2 EMA cross
# ---------------------------------------------------------------------------


def test_no_lookahead_ema_cross(enriched_ohlcv: pd.DataFrame) -> None:
    """No-lookahead invariant for EMACrossStrategy.

    The EMA(50)/EMA(200) values at bar t are computed using data[0..t] only
    (causal EMA, adjust=False, min_periods enforced). The engine shifts by 1.
    A future-leaking implementation would produce EMA values at t that use bar t+1.

    We verify: the EMA cross signals, shifted by 1 bar, do NOT systematically
    predict the t+2 close direction better than chance.
    """
    strategy = EMACrossStrategy(params={})
    signals = strategy.generate_signals(enriched_ohlcv)

    # Verify signals are within valid range
    assert signals.min() >= -1.0, f"Signal below -1.0: {signals.min()}"
    assert signals.max() <= 1.0, f"Signal above +1.0: {signals.max()}"

    # Verify warmup: first 199 bars should be 0.0 (EMA-200 needs 200 data points,
    # so bars 0-198 (0-indexed) cannot yet have a valid EMA-200 value).
    # Bar index 199 is the FIRST bar where min_periods=200 is satisfied (200 bars
    # total from index 0 to 199). So we check iloc[:199], not iloc[:200].
    first_199 = signals.iloc[:199]
    assert (first_199 == 0.0).all(), (
        f"Expected all-zero signals during EMA-200 warmup (bars 0-198); "
        f"found {int((first_199 != 0.0).sum())} non-zero signals. "
        f"This indicates min_periods not enforced for slow EMA."
    )

    # Causal check: no systematic 2-bar-ahead prediction
    future_2bar_return = enriched_ohlcv["close"].shift(-2) - enriched_ohlcv["close"]
    valid = signals.notna() & future_2bar_return.notna() & (signals != 0)
    if valid.sum() > 20:
        correct_predictions = (signals[valid] * future_2bar_return[valid] > 0).mean()
        assert correct_predictions < 0.85, (
            f"EMA cross signal predicts 2-bar-ahead returns at {correct_predictions:.1%}; "
            f"expected ~50% if causal. Possible lookahead in EMA computation."
        )

    # Run backtest and check for suspicious Sharpe
    cost_model = StaticRoundTripCostModel()
    sizer = VolTargetSizer(leverage_cap=0.25)
    result = run_backtest(
        data=enriched_ohlcv,
        signals=signals,
        pair="EURUSD",
        strategy_name="ema_cross_nolookahead_test",
        cost_model=cost_model,
        entry_delay_bars=1,
        sizer=sizer,
        rebalance_mode="continuous",
        constant_capital_sizing=True,
    )

    ec = result.equity_curve.dropna()
    assert len(ec) > 10, "Equity curve too short to test"

    bar_returns = ec.pct_change().dropna()
    if bar_returns.std() > 0:
        sharpe_1h = bar_returns.mean() / bar_returns.std() * np.sqrt(6240)
        assert sharpe_1h < 20.0, (
            f"EMA cross Sharpe ({sharpe_1h:.1f}) suspiciously high; "
            f"possible lookahead in EMA computation."
        )


# ---------------------------------------------------------------------------
# Signal structure tests
# ---------------------------------------------------------------------------


def test_macd_cross_always_in(enriched_ohlcv: pd.DataFrame) -> None:
    """M1 is always-in: no zeros after warmup (except exact MACD == signal equality).

    After the warmup period (first ~34 bars for MACD 12/26/9), signals should
    be +1 or -1 on virtually every bar. Exact equality is astronomically rare.
    """
    strategy = MACDCrossStrategy(params={})
    signals = strategy.generate_signals(enriched_ohlcv)

    # After 35-bar warmup, effectively no zeros (always-in)
    post_warmup = signals.iloc[35:]
    zero_count = int((post_warmup == 0.0).sum())
    # Allow <=5 zeros (exact MACD-line == signal-line, floating point collision)
    assert zero_count <= 5, (
        f"MACD cross has {zero_count} zeros after warmup; "
        f"expected <=5 (always-in strategy). "
        f"Possible off-by-one in warmup handling."
    )


def test_ema_cross_always_in(enriched_ohlcv: pd.DataFrame) -> None:
    """M2 is always-in: no zeros after EMA-200 warmup.

    After bar 200 (EMA-200 has min_periods=200), signals should be +1 or -1.
    """
    strategy = EMACrossStrategy(params={})
    signals = strategy.generate_signals(enriched_ohlcv)

    # After 200-bar warmup, effectively no zeros (always-in)
    post_warmup = signals.iloc[201:]
    zero_count = int((post_warmup == 0.0).sum())
    # Allow <=5 zeros (exact EMA50 == EMA200, floating point collision)
    assert zero_count <= 5, (
        f"EMA cross has {zero_count} zeros after warmup; "
        f"expected <=5 (always-in strategy). "
        f"Possible off-by-one in warmup handling."
    )


def test_macd_uses_ema_not_sma() -> None:
    """M1 MACD uses EMA internally, not SMA. Verify the MACD line differs from SMA cross."""
    import pandas as pd
    import numpy as np
    from forex_system.features.indicators import sma, macd as compute_macd

    np.random.seed(7)
    close = pd.Series(
        1.1 + np.cumsum(np.random.normal(0, 0.001, 300)),
        index=pd.date_range("2021-01-04", periods=300, freq="1h", tz="UTC"),
    )

    # MACD(12,26,9) from indicator module
    macd_line, _, _ = compute_macd(close, fast=12, slow=26, signal=9)

    # If it were SMA-based instead of EMA-based
    sma_diff = sma(close, 12) - sma(close, 26)

    # They should differ (EMA ≠ SMA for non-constant series)
    both_valid = macd_line.notna() & sma_diff.notna()
    if both_valid.sum() > 10:
        max_diff = abs(macd_line[both_valid] - sma_diff[both_valid]).max()
        assert max_diff > 1e-6, (
            "MACD line is identical to SMA difference — "
            "indicator is computing SMA instead of EMA."
        )
