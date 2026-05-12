"""Tests for W11-2: F-100 JPY mid <= 0 guard (CRO Decision A).

Covers 5 test cases:
  1. USDJPY mid=0   → SKIP_F100_JPY_MID_GUARD returned, warning logged (vt)
  2. USDJPY mid=-1  → SKIP_F100_JPY_MID_GUARD returned, warning logged (vt)
  3. USDJPY mid=NaN → SKIP_F100_JPY_MID_GUARD returned, warning logged (vt)
  4. EURUSD mid=0   → guard does NOT fire (non-JPY pair falls through)
  5. USDJPY mid=150 → guard does NOT fire, cycle proceeds normally (vt)

Tests are written at the guard level using real run_cycle calls with mocked
infrastructure, consistent with the existing test_run_paper_trading_carry_fred
pattern in this directory.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from forex_system.risk.drawdown_contract import DrawdownContract


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _std_dd_contract() -> DrawdownContract:
    return DrawdownContract(
        halt_threshold=0.10,
        reduce_threshold=0.15,
        full_halt_threshold=0.20,
    )


def _make_ohlcv(close: float = 150.0, rows: int = 300) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=rows, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=idx,
    )


def _make_vt_infra(equity: float = 100_000.0):
    """Return (client, backend, kill_switch, sizer, strategy, pred_log, trade_log) for vt."""
    kill_switch = MagicMock()
    kill_switch.is_triggered = False
    kill_switch.check_and_trigger.return_value = False
    kill_switch.record_equity_fetch_failure.return_value = False
    kill_switch.consecutive_fetch_failures = 0
    kill_switch.max_consecutive_fetch_failures = 3
    kill_switch.record_equity_fetch_success.return_value = None

    backend = MagicMock()
    backend.get_positions.return_value = {}
    backend.account_key = "TEST_VT_ACCOUNT"

    client = MagicMock()

    sizer = MagicMock()
    sizer.calculate_size.return_value = 1000.0

    strategy = MagicMock()
    signals = pd.Series([0.5], index=[_make_ohlcv().index[-1]])
    strategy.generate_signals.return_value = signals
    strategy.params = {"vol_window": 252}

    pred_log = MagicMock()
    trade_log = MagicMock()

    return client, backend, kill_switch, sizer, strategy, pred_log, trade_log


def _run_vt_cycle_with_mid(pair: str, mid_value: float):
    """Drive run_cycle in vt script, forcing the computed mid to equal mid_value.

    The ternary in the script is:
        mid = (bid + ask) / 2 if (bid and ask) else float(ohlcv["close"].iloc[-1])

    Key truth-table edge cases:
    - bid=0 or ask=0 → (bid and ask) is falsy → mid = close
    - bid=NaN or ask=NaN → (bid and ask) is truthy (NaN is truthy) → mid = NaN

    Strategy to produce a given mid reliably:
    - NaN: bid=ask=NaN (truthy, so ternary takes left branch → NaN)
    - 0 or negative: use truthy small positives for bid/ask but set close=mid_value
      so the fallback also produces mid_value; then override using a tiny non-zero
      bid/ask that averages to mid_value.  Simplest: bid=ask=mid_value when non-zero
      (truthy), or patch the close column to mid_value and force bid=ask=0 for the
      ternary fallback path.
    - positive: bid=ask=mid_value (truthy, ternary left branch)

    For 0 and negative we force bid=ask=mid_value as tiny non-zero-ish values so
    that the ternary left branch fires.  Concretely: bid = ask = mid_value when
    mid_value != 0; for mid_value == 0 we need a special trick since 0 is falsy.
    We use a helper that patches the mid variable directly after computation via
    a monkeypatch of math.isnan — but that is complex.  Instead, we set
    ohlcv close = mid_value (so fallback produces it) AND make bid=ask=0 to force
    the fallback path.  This tests the guard for the close-fallback case (Saxo
    quote fails and close itself is degenerate).
    """
    import scripts.run_paper_trading_vt as vt_mod

    vt_mod._HALT_REQUESTED = False
    vt_mod._HALT_REASON = ""

    client, backend, ks, sizer, strategy, pred_log, trade_log = _make_vt_infra()
    dd = _std_dd_contract()
    dd.assess(100_000.0)

    if math.isnan(mid_value):
        # NaN is truthy in Python, so (bid and ask) == True → mid = NaN
        bid = ask = float("nan")
        ohlcv = _make_ohlcv(close=150.0)
        client.get_info_price.return_value = {"Quote": {"Bid": bid, "Ask": ask}}
    elif mid_value <= 0:
        # Force ternary fallback: bid=ask=0 (falsy) → mid = close.
        # Set close column to mid_value so the fallback yields the degenerate value.
        bid = ask = 0.0
        ohlcv = _make_ohlcv(close=mid_value)
        client.get_info_price.return_value = {"Quote": {"Bid": bid, "Ask": ask}}
    else:
        # Normal positive path: bid=ask=mid_value (truthy) → mid = mid_value
        bid = ask = mid_value
        ohlcv = _make_ohlcv(close=mid_value)
        client.get_info_price.return_value = {"Quote": {"Bid": bid, "Ask": ask}}

    with patch.object(vt_mod, "fetch_account_equity", return_value=100_000.0), \
         patch.object(vt_mod, "fetch_recent_bars", return_value=ohlcv):
        result = vt_mod.run_cycle(
            client=client,
            backend=backend,
            sizer=sizer,
            strategy=strategy,
            pair=pair,
            pred_log=pred_log,
            trade_log=trade_log,
            kill_switch=ks,
            dd_contract=dd,
            rebal_threshold=0.20,
            auto_mode=True,
            cycle_id=42,
        )
    return result


# ---------------------------------------------------------------------------
# Test 1: USDJPY mid=0 halts cycle
# ---------------------------------------------------------------------------


class TestF100UsdJpyMidZeroHaltsCycle:
    def test_mid_zero_returns_skip_sentinel(self):
        result = _run_vt_cycle_with_mid("USDJPY", 0.0)
        assert result.get("_action") == "SKIP_F100_JPY_MID_GUARD", (
            f"Expected SKIP_F100_JPY_MID_GUARD, got {result}"
        )

    def test_mid_zero_emits_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            _run_vt_cycle_with_mid("USDJPY", 0.0)
        assert any("F100_JPY_MID_GUARD" in r.message or "f100_jpy_mid_guard_triggered" in r.message
                   for r in caplog.records), (
            "Expected F100_JPY_MID_GUARD warning log not found"
        )


# ---------------------------------------------------------------------------
# Test 2: USDJPY mid=-1 halts cycle
# ---------------------------------------------------------------------------


class TestF100UsdJpyMidNegativeHaltsCycle:
    def test_mid_negative_returns_skip_sentinel(self):
        result = _run_vt_cycle_with_mid("USDJPY", -1.0)
        assert result.get("_action") == "SKIP_F100_JPY_MID_GUARD", (
            f"Expected SKIP_F100_JPY_MID_GUARD, got {result}"
        )


# ---------------------------------------------------------------------------
# Test 3: USDJPY mid=NaN halts cycle
# ---------------------------------------------------------------------------


class TestF100UsdJpyMidNanHaltsCycle:
    def test_mid_nan_returns_skip_sentinel(self):
        result = _run_vt_cycle_with_mid("USDJPY", float("nan"))
        assert result.get("_action") == "SKIP_F100_JPY_MID_GUARD", (
            f"Expected SKIP_F100_JPY_MID_GUARD, got {result}"
        )


# ---------------------------------------------------------------------------
# Test 4: EURUSD mid=0 does NOT halt (non-JPY pair)
# ---------------------------------------------------------------------------


class TestF100EurUsdMidZeroDoesNotHalt:
    def test_eurusd_mid_zero_does_not_return_guard_sentinel(self):
        # EURUSD with mid=0 should not trigger the JPY guard.
        # The cycle may still fail for other reasons (sizer, etc.) but must NOT
        # return SKIP_F100_JPY_MID_GUARD.
        result = _run_vt_cycle_with_mid("EURUSD", 0.0)
        assert result.get("_action") != "SKIP_F100_JPY_MID_GUARD", (
            f"Guard must not fire for non-JPY pair, got {result}"
        )


# ---------------------------------------------------------------------------
# Test 5: USDJPY mid=150 (normal) — guard does not fire, cycle proceeds
# ---------------------------------------------------------------------------


class TestF100UsdJpyMidPositivePassesThrough:
    def test_mid_positive_does_not_return_guard_sentinel(self):
        result = _run_vt_cycle_with_mid("USDJPY", 150.0)
        assert result.get("_action") != "SKIP_F100_JPY_MID_GUARD", (
            f"Guard must not fire for positive mid, got {result}"
        )
