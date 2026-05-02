"""Tests for fred_carry_stripped strategy (Phase-2 R7 instrument).

Verifies:
1. Module loads and class is importable.
2. Conforms to Strategy ABC interface (name, required_indicators, generate_signals).
3. Produces signals on synthetic rate data WITHOUT applying regime filter.
4. Signals are in [-1, +1].
5. Returns zeros when min_differential not met.
6. registry.create_strategy('fred_carry_stripped', params) works.
"""

from __future__ import annotations

import pandas as pd
import pytest

from forex_system.strategies.fred_carry_stripped import FredCarryStrippedStrategy
from forex_system.strategies.registry import create_strategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ohlcv(n: int = 60) -> pd.DataFrame:
    """Minimal OHLCV DataFrame for signal generation testing."""
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": 130.0,
            "high": 131.0,
            "low": 129.0,
            "close": 130.5,
            "volume": 1_000,
        },
        index=dates,
    )


def _make_rate_data(n: int = 60, pair_col: str = "USDJPY_diff") -> pd.DataFrame:
    """Synthetic rate differentials DataFrame with 12 pair columns."""
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    # All pairs get a small differential; USDJPY gets a larger one so it
    # produces non-zero signals
    data = {col: 0.005 for col in [
        "AUDJPY_diff", "AUDUSD_diff", "CADJPY_diff", "EURGBP_diff",
        "EURJPY_diff", "EURUSD_diff", "GBPJPY_diff", "GBPUSD_diff",
        "NZDJPY_diff", "NZDUSD_diff", "USDCAD_diff", "USDJPY_diff",
    ]}
    data["USDJPY_diff"] = 0.03  # clear positive carry for USDJPY
    return pd.DataFrame(data, index=dates)


# ---------------------------------------------------------------------------
# Interface compliance tests
# ---------------------------------------------------------------------------


def test_module_imports() -> None:
    """Strategy class is importable from its module."""
    from forex_system.strategies.fred_carry_stripped import FredCarryStrippedStrategy  # noqa: F401


def test_strategy_name() -> None:
    strategy = FredCarryStrippedStrategy({"pair": "USDJPY"})
    assert strategy.name == "fred_carry_stripped"


def test_required_indicators_is_list() -> None:
    strategy = FredCarryStrippedStrategy({"pair": "USDJPY"})
    indicators = strategy.required_indicators()
    assert isinstance(indicators, list)
    # Stripped variant requires no indicators
    assert indicators == []


def test_strategy_abc_compliance() -> None:
    """FredCarryStrippedStrategy implements the Strategy ABC."""
    from forex_system.core.interfaces import Strategy

    strategy = FredCarryStrippedStrategy({"pair": "USDJPY"})
    assert isinstance(strategy, Strategy)


# ---------------------------------------------------------------------------
# Signal generation tests
# ---------------------------------------------------------------------------


def test_signals_range_ranked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Signals are bounded to [-1, +1] with rank_normalize=True."""
    ohlcv = _make_ohlcv()
    rate_data = _make_rate_data()
    strategy = FredCarryStrippedStrategy(
        {"pair": "USDJPY", "rank_normalize": True},
        rate_data=rate_data,
    )
    signals = strategy.generate_signals(ohlcv)
    assert isinstance(signals, pd.Series)
    assert len(signals) == len(ohlcv)
    assert signals.min() >= -1.0 - 1e-9
    assert signals.max() <= 1.0 + 1e-9


def test_signals_index_aligned() -> None:
    """Signal index matches ohlcv index exactly."""
    ohlcv = _make_ohlcv()
    rate_data = _make_rate_data()
    strategy = FredCarryStrippedStrategy(
        {"pair": "USDJPY"},
        rate_data=rate_data,
    )
    signals = strategy.generate_signals(ohlcv)
    pd.testing.assert_index_equal(signals.index, ohlcv.index)


def test_signals_range_raw() -> None:
    """Signals are bounded to [-1, +1] with rank_normalize=False."""
    ohlcv = _make_ohlcv()
    rate_data = _make_rate_data()
    strategy = FredCarryStrippedStrategy(
        {"pair": "USDJPY", "rank_normalize": False, "max_differential": 0.05},
        rate_data=rate_data,
    )
    signals = strategy.generate_signals(ohlcv)
    assert signals.min() >= -1.0 - 1e-9
    assert signals.max() <= 1.0 + 1e-9


def test_no_regime_filter_applied(caplog: pytest.LogCaptureFixture) -> None:
    """Decision trace log confirms regime_filter_applied=False."""
    import json
    import logging

    ohlcv = _make_ohlcv()
    rate_data = _make_rate_data()
    strategy = FredCarryStrippedStrategy(
        {"pair": "USDJPY"},
        rate_data=rate_data,
    )

    with caplog.at_level(logging.INFO, logger="forex_system.strategies.fred_carry_stripped"):
        strategy.generate_signals(ohlcv)

    # Find the decision trace log entry
    decision_entries = [
        json.loads(r.message)
        for r in caplog.records
        if r.name == "forex_system.strategies.fred_carry_stripped"
    ]
    assert len(decision_entries) >= 1
    trace = decision_entries[0]
    assert trace["regime_filter_applied"] is False
    assert trace["r7_instrument"] is True


def test_zero_signals_below_min_differential() -> None:
    """All signals are zero when all differentials are below min_differential."""
    ohlcv = _make_ohlcv()
    dates = pd.date_range("2022-01-03", periods=60, freq="B")
    # All differentials below 0.001 threshold
    tiny_diff = {col: 0.0001 for col in [
        "AUDJPY_diff", "AUDUSD_diff", "CADJPY_diff", "EURGBP_diff",
        "EURJPY_diff", "EURUSD_diff", "GBPJPY_diff", "GBPUSD_diff",
        "NZDJPY_diff", "NZDUSD_diff", "USDCAD_diff", "USDJPY_diff",
    ]}
    rate_data = pd.DataFrame(tiny_diff, index=dates)
    strategy = FredCarryStrippedStrategy(
        {"pair": "USDJPY", "min_differential": 0.001},
        rate_data=rate_data,
    )
    signals = strategy.generate_signals(ohlcv)
    assert (signals == 0.0).all()


def test_unknown_pair_raises() -> None:
    """ValueError raised for unsupported pair."""
    ohlcv = _make_ohlcv()
    rate_data = _make_rate_data()
    strategy = FredCarryStrippedStrategy(
        {"pair": "XYZABC"},
        rate_data=rate_data,
    )
    with pytest.raises(ValueError, match="unknown pair"):
        strategy.generate_signals(ohlcv)


def test_missing_pair_param_raises() -> None:
    """ValueError raised when pair param is missing."""
    ohlcv = _make_ohlcv()
    rate_data = _make_rate_data()
    strategy = FredCarryStrippedStrategy({}, rate_data=rate_data)
    with pytest.raises(ValueError, match="'pair' param is required"):
        strategy.generate_signals(ohlcv)


# ---------------------------------------------------------------------------
# Registry integration test
# ---------------------------------------------------------------------------


def test_registry_create_strategy() -> None:
    """create_strategy('fred_carry_stripped', ...) returns correct class."""
    strategy = create_strategy("fred_carry_stripped", {"pair": "USDJPY"})
    assert isinstance(strategy, FredCarryStrippedStrategy)
    assert strategy.name == "fred_carry_stripped"
