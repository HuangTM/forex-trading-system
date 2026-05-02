"""Tests for TasCeiling4hStrategy (Bet #2 Phase-2 falsification instrument).

Verifies:
1. Module imports and class is importable.
2. Conforms to Strategy ABC (name, required_indicators, generate_signals).
3. Signals are in [-1, +1] on synthetic data.
4. No-lookahead invariant: signal at bar N uses only data through bar N.
5. required_indicators() returns an empty list (all computation from close).
6. registry.create_strategy('tas_ceiling_4h', params) returns correct class.
7. Stateful signal: no entry on the cooldown bar immediately after an exit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forex_system.core.interfaces import Strategy
from forex_system.strategies.registry import create_strategy
from forex_system.strategies.tas_ceiling_4h import TasCeiling4hStrategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """Synthetic 4H OHLCV with a random-walk close for signal-generation tests."""
    rng = np.random.default_rng(seed)
    # Random walk with some mean reversion to generate both long/short entries.
    returns = rng.normal(0.0, 0.005, n)
    close = 100.0 * np.exp(np.cumsum(returns))
    dates = pd.date_range("2022-01-03 00:00:00", periods=n, freq="4h")
    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.002,
            "low": close * 0.998,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=dates,
    )


def _make_ohlcv_spike(n: int = 250) -> pd.DataFrame:
    """OHLCV with a large spike at bar 150 to trigger entry + exit."""
    close = np.full(n, 100.0)
    # Inject a 5σ spike at bar 150 (entry); then revert to flat.
    close[150] = 115.0   # spike up → z >> +k_enter → short entry
    dates = pd.date_range("2022-01-03 00:00:00", periods=n, freq="4h")
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Interface compliance tests
# ---------------------------------------------------------------------------


def test_module_imports() -> None:
    """Strategy class is importable from its module."""
    from forex_system.strategies.tas_ceiling_4h import TasCeiling4hStrategy  # noqa: F401


def test_strategy_name() -> None:
    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    assert strategy.name == "tas_ceiling_4h"


def test_abc_compliance() -> None:
    """TasCeiling4hStrategy is an instance of the Strategy ABC."""
    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    assert isinstance(strategy, Strategy)


def test_required_indicators_is_empty_list() -> None:
    """required_indicators() returns [] — strategy needs no pre-computed indicators."""
    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    indicators = strategy.required_indicators()
    assert isinstance(indicators, list)
    assert indicators == []


# ---------------------------------------------------------------------------
# Signal generation tests
# ---------------------------------------------------------------------------


def test_signals_range_bounds() -> None:
    """Signals are strictly within [-1, +1]."""
    data = _make_ohlcv(n=300)
    strategy = TasCeiling4hStrategy({"pair": "EURUSD"})
    signals = strategy.generate_signals(data)
    assert isinstance(signals, pd.Series)
    assert len(signals) == len(data)
    assert signals.min() >= -1.0 - 1e-9
    assert signals.max() <= 1.0 + 1e-9


def test_signals_index_aligned() -> None:
    """Signal index matches input data index exactly."""
    data = _make_ohlcv(n=200)
    strategy = TasCeiling4hStrategy({"pair": "GBPUSD"})
    signals = strategy.generate_signals(data)
    pd.testing.assert_index_equal(signals.index, data.index)


def test_no_nan_in_signals() -> None:
    """Output signal Series has no NaN values."""
    data = _make_ohlcv(n=200)
    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    signals = strategy.generate_signals(data)
    assert not signals.isna().any(), "Signals contain NaN values"


def test_flat_before_warmup() -> None:
    """Bars before regression_window_bars warmup should be zero (no z-score)."""
    data = _make_ohlcv(n=300)
    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    signals = strategy.generate_signals(data)
    # First 120 bars: z-score undefined → signals must be 0
    assert (signals.iloc[:120] == 0.0).all(), (
        "Expected flat signals during warmup period (first 120 bars)"
    )


# ---------------------------------------------------------------------------
# No-lookahead invariant test
# ---------------------------------------------------------------------------


def test_no_lookahead_invariant() -> None:
    """Signal at bar N must not change when future bars are added.

    Methodology: generate signals on first 200 bars; then generate signals on
    250 bars. Signals on the shared prefix [0:200] must be identical.
    Adding future data must not change signals on past bars.
    """
    rng = np.random.default_rng(99)
    returns = rng.normal(0.0, 0.005, 250)
    close_all = 100.0 * np.exp(np.cumsum(returns))
    dates = pd.date_range("2022-01-03", periods=250, freq="4h")

    def make_df(n: int) -> pd.DataFrame:
        return pd.DataFrame(
            {"open": close_all[:n], "high": close_all[:n], "low": close_all[:n],
             "close": close_all[:n], "volume": 1_000_000.0},
            index=dates[:n],
        )

    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    signals_200 = strategy.generate_signals(make_df(200))
    signals_250 = strategy.generate_signals(make_df(250))

    # The shared prefix [0:200] must be identical.
    pd.testing.assert_series_equal(
        signals_200,
        signals_250.iloc[:200],
        check_names=False,
        atol=1e-9,
    )


# ---------------------------------------------------------------------------
# Stateful signal: cooldown test
# ---------------------------------------------------------------------------


def test_cooldown_bar_is_zero() -> None:
    """The bar immediately following an exit must be zero (1-bar cooldown, A1-1)."""
    data = _make_ohlcv_spike(n=250)
    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    signals = strategy.generate_signals(data)

    # Detect exit bars: transitions from nonzero to zero.
    nonzero = signals != 0.0
    exit_bars = nonzero.shift(1).fillna(False) & ~nonzero

    for idx in exit_bars.index[exit_bars]:
        pos = signals.index.get_loc(idx)
        if pos + 1 < len(signals):
            cooldown_signal = signals.iloc[pos + 1]
            assert cooldown_signal == 0.0, (
                f"Expected cooldown (0.0) at bar {pos + 1} after exit at {pos}, "
                f"got {cooldown_signal}"
            )


# ---------------------------------------------------------------------------
# Missing required column
# ---------------------------------------------------------------------------


def test_missing_close_raises() -> None:
    """ValueError raised when 'close' column is absent."""
    data = pd.DataFrame({"open": [1.0, 2.0]}, index=pd.date_range("2022-01-03", periods=2))
    strategy = TasCeiling4hStrategy({"pair": "USDJPY"})
    with pytest.raises(ValueError, match="'close' column required"):
        strategy.generate_signals(data)


# ---------------------------------------------------------------------------
# Registry integration test
# ---------------------------------------------------------------------------


def test_registry_create_strategy() -> None:
    """create_strategy('tas_ceiling_4h', ...) returns TasCeiling4hStrategy instance."""
    strategy = create_strategy("tas_ceiling_4h", {"pair": "USDJPY"})
    assert isinstance(strategy, TasCeiling4hStrategy)
    assert strategy.name == "tas_ceiling_4h"
