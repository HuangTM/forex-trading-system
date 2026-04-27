"""WS-01 (CTO consensus 2026-04-26): decision-boundary structured-log test.

Asserts that run_cycle() emits exactly one `ws01 {...json...}` log line per
cycle, containing the consensus-pinned fields: cycle_id, pair, signal, vol,
equity, price, target_units, current_units, action.

This is the HARD-BLOCKER instrumentation for paper-cycle resumption per
CONSENSUS.md gate chain (A1 → A2 → A3 → Q2 → cycle resume). If this test
fails, the trace contract has regressed and paper trading must NOT resume.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

import run_paper_trading_vt as rpt


def _make_ohlcv(n: int = 320, base: float = 150.0) -> pd.DataFrame:
    """Synthetic daily bars long enough to exceed vol_window + buffer."""
    rng = np.random.default_rng(42)
    rets = rng.normal(0.0001, 0.005, n)
    close = base * np.exp(np.cumsum(rets))
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=pd.date_range("2025-01-01", periods=n, freq="B"),
    )


@pytest.fixture
def ws01_lines(monkeypatch, caplog):
    """Run a single cycle in HOLD FLAT mode and capture ws01 log lines."""
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")

    client = MagicMock()
    client.get_chart_data.return_value = {"Data": []}
    client.get_info_price.return_value = {"Quote": {"Bid": 150.10, "Ask": 150.20}}

    backend = MagicMock()
    backend.account_key = "TEST_ACCT"
    backend.get_positions.return_value = {}
    backend.reconcile.return_value = []

    # Stub fetch_recent_bars to return our synthetic frame regardless of args
    monkeypatch.setattr(rpt, "fetch_recent_bars", lambda *a, **kw: _make_ohlcv())
    # Stub equity to a known value
    monkeypatch.setattr(rpt, "fetch_account_equity", lambda *a, **kw: 100_000.0)

    sizer = MagicMock()
    sizer.calculate_size.return_value = 0.0  # forces HOLD FLAT branch (no current pos)

    strategy = MagicMock()
    strategy.params = {"vol_window": 252, "leverage_cap": 2.0, "target_vol": 0.10}
    # Generate signals returns last value 0.5 (mid-strength long)
    sig_series = pd.Series(np.full(320, 0.5), index=pd.date_range("2025-01-01", periods=320, freq="B"))
    strategy.generate_signals.return_value = sig_series

    kill_switch = MagicMock()
    kill_switch.is_triggered = False
    kill_switch.check_and_trigger.return_value = False
    kill_switch.record_equity_fetch_failure.return_value = False

    pred_log = MagicMock()
    trade_log = MagicMock()

    rpt.run_cycle(
        client=client,
        backend=backend,
        sizer=sizer,
        strategy=strategy,
        pair="USDJPY",
        pred_log=pred_log,
        trade_log=trade_log,
        kill_switch=kill_switch,
        rebal_threshold=0.20,
        auto_mode=True,
        ntfy_topic=None,
        horizon="daily",
        monitor_pairs=None,
        cycle_id=42,
    )

    return [r.message for r in caplog.records if r.message.startswith("ws01 ")]


def test_ws01_log_emitted_exactly_once(ws01_lines):
    """Exactly one ws01 line per cycle (single decision boundary)."""
    assert len(ws01_lines) == 1, f"expected 1 ws01 line, got {len(ws01_lines)}: {ws01_lines}"


def test_ws01_log_contains_required_fields(ws01_lines):
    """All consensus-pinned fields must be present and the right type.

    Per CTO 2026-04-27 Q1+Q2 conditions, the field set is extended:
    - decision_ts: explicit UTC timestamp at the decision instant
    - strategy_params: the parameter dict in force at decision time
    """
    payload = json.loads(ws01_lines[0].removeprefix("ws01 "))

    required = {"decision_ts", "cycle_id", "pair", "signal", "vol", "equity",
                "price", "target_units", "current_units", "action",
                "strategy_params"}
    assert required.issubset(payload.keys()), \
        f"missing fields: {required - set(payload.keys())}"

    assert payload["cycle_id"] == 42
    assert payload["pair"] == "USDJPY"
    assert payload["signal"] == pytest.approx(0.5)
    assert payload["equity"] == 100_000.0
    assert payload["target_units"] == 0.0
    assert payload["current_units"] == 0.0
    assert payload["action"] == "HOLD FLAT"
    # vol may be None if NaN, but for our 320-bar synthetic it should be float
    assert isinstance(payload["vol"], float) and payload["vol"] > 0
    # decision_ts must be an ISO-8601 UTC string parseable by datetime
    from datetime import datetime
    parsed = datetime.fromisoformat(payload["decision_ts"])
    assert parsed.tzinfo is not None  # UTC, not naive
    # strategy_params must be a dict and contain the standard knobs
    assert isinstance(payload["strategy_params"], dict)
    assert "vol_window" in payload["strategy_params"]
    assert "leverage_cap" in payload["strategy_params"]


def test_ws01_log_is_machine_parseable(ws01_lines):
    """Log line must be `ws01 ` prefix + valid JSON (single line, no embedded newlines)."""
    line = ws01_lines[0]
    assert line.startswith("ws01 ")
    body = line.removeprefix("ws01 ")
    assert "\n" not in body, "JSON body must be single-line for log-parser compatibility"
    json.loads(body)  # must not raise


# --------------------------------------------------------------------------- #
# Early-exit coverage (critic Issue 1): WS-01 must fire on every cycle exit,
# not just the main path. A kill-halt or data-failure cycle is exactly when
# ops most need the trace.
# --------------------------------------------------------------------------- #

def _make_ws01_kwargs(monkeypatch, **overrides):
    """Build a default kwargs dict for run_cycle() — caller can override fields."""
    client = MagicMock()
    client.get_chart_data.return_value = {"Data": []}
    client.get_info_price.return_value = {"Quote": {"Bid": 150.10, "Ask": 150.20}}

    backend = MagicMock()
    backend.account_key = "TEST_ACCT"
    backend.get_positions.return_value = {}
    backend.reconcile.return_value = []

    monkeypatch.setattr(rpt, "fetch_recent_bars", lambda *a, **kw: _make_ohlcv())
    monkeypatch.setattr(rpt, "fetch_account_equity", lambda *a, **kw: 100_000.0)

    sizer = MagicMock()
    sizer.calculate_size.return_value = 0.0

    strategy = MagicMock()
    strategy.params = {"vol_window": 252, "leverage_cap": 2.0, "target_vol": 0.10}
    sig_series = pd.Series(np.full(320, 0.5), index=pd.date_range("2025-01-01", periods=320, freq="B"))
    strategy.generate_signals.return_value = sig_series

    kill_switch = MagicMock()
    kill_switch.is_triggered = False
    kill_switch.check_and_trigger.return_value = False
    kill_switch.record_equity_fetch_failure.return_value = False
    kill_switch.max_consecutive_fetch_failures = 3
    kill_switch.consecutive_fetch_failures = 0

    kwargs = dict(
        client=client, backend=backend, sizer=sizer, strategy=strategy,
        pair="USDJPY", pred_log=MagicMock(), trade_log=MagicMock(),
        kill_switch=kill_switch, rebal_threshold=0.20, auto_mode=True,
        ntfy_topic=None, horizon="daily", monitor_pairs=None, cycle_id=7,
    )
    kwargs.update(overrides)
    return kwargs


def _ws01_lines_after(caplog):
    return [r.message for r in caplog.records if r.message.startswith("ws01 ")]


def test_ws01_emits_on_kill_switch_already_active(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    kwargs = _make_ws01_kwargs(monkeypatch)
    kwargs["kill_switch"].is_triggered = True
    kwargs["kill_switch"].status_line = "TRIGGERED 2026-04-25"
    rpt.run_cycle(**kwargs)
    lines = _ws01_lines_after(caplog)
    assert len(lines) == 1, "kill-active cycle must emit ws01"
    payload = json.loads(lines[0].removeprefix("ws01 "))
    assert payload["action"] == "KILL_HALTED_PRECYCLE"
    assert payload["cycle_id"] == 7
    assert payload["pair"] == "USDJPY"


def test_ws01_emits_on_equity_fetch_failure(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    kwargs = _make_ws01_kwargs(monkeypatch)
    monkeypatch.setattr(rpt, "fetch_account_equity", lambda *a, **kw: None)
    rpt.run_cycle(**kwargs)
    lines = _ws01_lines_after(caplog)
    assert len(lines) == 1
    payload = json.loads(lines[0].removeprefix("ws01 "))
    assert payload["action"] == "SKIP_EQUITY_FETCH_FAIL"


def test_ws01_emits_on_drawdown_kill_trigger(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    kwargs = _make_ws01_kwargs(monkeypatch)
    kwargs["kill_switch"].check_and_trigger.return_value = True
    kwargs["kill_switch"].status_line = "DD trigger"
    rpt.run_cycle(**kwargs)
    lines = _ws01_lines_after(caplog)
    assert len(lines) == 1
    payload = json.loads(lines[0].removeprefix("ws01 "))
    assert payload["action"] == "KILL_HALTED_DRAWDOWN"
    assert payload["equity"] == 100_000.0


def test_ws01_emits_on_no_data(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    kwargs = _make_ws01_kwargs(monkeypatch)
    monkeypatch.setattr(rpt, "fetch_recent_bars", lambda *a, **kw: pd.DataFrame())
    rpt.run_cycle(**kwargs)
    lines = _ws01_lines_after(caplog)
    assert len(lines) == 1
    payload = json.loads(lines[0].removeprefix("ws01 "))
    assert payload["action"] == "SKIP_NO_DATA"


def test_ws01_emits_on_insufficient_bars(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    kwargs = _make_ws01_kwargs(monkeypatch)
    monkeypatch.setattr(rpt, "fetch_recent_bars", lambda *a, **kw: _make_ohlcv(n=50))
    rpt.run_cycle(**kwargs)
    lines = _ws01_lines_after(caplog)
    assert len(lines) == 1
    payload = json.loads(lines[0].removeprefix("ws01 "))
    assert payload["action"] == "SKIP_INSUFFICIENT_BARS"
    assert payload["price"] is not None  # last close was available


# --------------------------------------------------------------------------- #
# Finite-float guard (critic Issue 3): json.dumps must never crash the
# decision boundary on non-finite vol/equity/price/units.
# --------------------------------------------------------------------------- #

def test_finite_or_none_handles_inf_nan_none():
    assert rpt._finite_or_none(1.5) == 1.5
    assert rpt._finite_or_none(0) == 0.0
    assert rpt._finite_or_none(float("inf")) is None
    assert rpt._finite_or_none(float("-inf")) is None
    assert rpt._finite_or_none(float("nan")) is None
    assert rpt._finite_or_none(None) is None
    assert rpt._finite_or_none("not a number") is None


def test_emit_ws01_does_not_raise_on_inf_vol(caplog):
    """Regression for critic Issue 3: inf in any field must serialize as null."""
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    rpt._emit_ws01(
        cycle_id=99, pair="USDJPY", action="HOLD FLAT",
        signal=0.5, vol=float("inf"), equity=100_000.0,
        price=150.0, target_units=0.0, current_units=0.0,
    )
    lines = _ws01_lines_after(caplog)
    assert len(lines) == 1
    payload = json.loads(lines[0].removeprefix("ws01 "))
    assert payload["vol"] is None  # inf got scrubbed
    assert payload["signal"] == 0.5  # finite values pass through


# --------------------------------------------------------------------------- #
# Durability (critic Issue 2): file handler must persist trace independent
# of stderr redirection.
# --------------------------------------------------------------------------- #

def test_attach_ws01_file_handler_writes_to_disk(tmp_path):
    """Attaching the handler creates the file and routes ws01 lines to it."""
    trace_path = tmp_path / "ws01_trace.log"
    rpt._attach_ws01_file_handler(str(trace_path))
    try:
        rpt._emit_ws01(cycle_id=5, pair="USDJPY", action="HOLD FLAT",
                       signal=0.1, equity=10_000.0)
        # Flush the handler we just attached
        for h in rpt.logger.handlers:
            if isinstance(h, logging.FileHandler) and getattr(h, "_ws01_marker", False):
                h.flush()
        assert trace_path.exists()
        contents = trace_path.read_text()
        assert "ws01 " in contents
        assert '"cycle_id": 5' in contents
        assert '"action": "HOLD FLAT"' in contents
    finally:
        # Cleanup: remove handler so it doesn't bleed into other tests
        for h in list(rpt.logger.handlers):
            if isinstance(h, logging.FileHandler) and getattr(h, "_ws01_marker", False):
                h.close()
                rpt.logger.removeHandler(h)


def test_attach_ws01_file_handler_is_idempotent(tmp_path):
    """Calling twice must not stack duplicate handlers."""
    trace_path = tmp_path / "ws01_trace.log"
    rpt._attach_ws01_file_handler(str(trace_path))
    rpt._attach_ws01_file_handler(str(trace_path))
    try:
        ws01_handlers = [h for h in rpt.logger.handlers
                         if isinstance(h, logging.FileHandler)
                         and getattr(h, "_ws01_marker", False)]
        assert len(ws01_handlers) == 1
    finally:
        for h in list(rpt.logger.handlers):
            if isinstance(h, logging.FileHandler) and getattr(h, "_ws01_marker", False):
                h.close()
                rpt.logger.removeHandler(h)


# --------------------------------------------------------------------------- #
# Regression: WS01 must be emitted BEFORE backend.flatten_all() on every
# kill path (R1 critic finding #4). Otherwise the audit trace records the
# decision AFTER the execution side-effect.
# --------------------------------------------------------------------------- #

class _OrderTracker:
    """Records the sequence of (event_type, payload) pairs to verify ordering."""

    def __init__(self):
        self.events: list[tuple[str, str]] = []

    def add(self, event_type: str, payload: str = "") -> None:
        self.events.append((event_type, payload))


def test_ws01_emitted_before_flatten_on_drawdown_kill(monkeypatch, caplog):
    """On drawdown-kill path, ws01 emit must precede flatten_all()."""
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    tracker = _OrderTracker()

    kwargs = _make_ws01_kwargs(monkeypatch)
    kwargs["kill_switch"].check_and_trigger.return_value = True
    kwargs["kill_switch"].status_line = "DD trigger"
    kwargs["backend"].flatten_all = lambda: tracker.add("flatten_all")

    # Wrap _emit_ws01 to record its invocation order
    real_emit = rpt._emit_ws01
    def tracked_emit(*a, **kw):
        tracker.add("ws01", kw.get("equity", a[2] if len(a) > 2 else ""))
        return real_emit(*a, **kw)
    monkeypatch.setattr(rpt, "_emit_ws01", tracked_emit)

    rpt.run_cycle(**kwargs)

    # Find indexes; ws01 must come before flatten_all
    types = [e[0] for e in tracker.events]
    assert "ws01" in types and "flatten_all" in types
    ws01_idx = types.index("ws01")
    flatten_idx = types.index("flatten_all")
    assert ws01_idx < flatten_idx, (
        f"WS01 must precede flatten_all; observed order {types}"
    )


def test_ws01_emitted_before_flatten_on_equity_fetch_kill(monkeypatch, caplog):
    """On equity-fetch-failure kill path, ws01 must precede flatten_all()."""
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    tracker = _OrderTracker()

    kwargs = _make_ws01_kwargs(monkeypatch)
    monkeypatch.setattr(rpt, "fetch_account_equity", lambda *a, **kw: None)
    kwargs["kill_switch"].record_equity_fetch_failure.return_value = True
    kwargs["kill_switch"].status_line = "fetch fail"
    kwargs["backend"].flatten_all = lambda: tracker.add("flatten_all")

    real_emit = rpt._emit_ws01
    def tracked_emit(*a, **kw):
        tracker.add("ws01")
        return real_emit(*a, **kw)
    monkeypatch.setattr(rpt, "_emit_ws01", tracked_emit)

    rpt.run_cycle(**kwargs)

    types = [e[0] for e in tracker.events]
    assert "ws01" in types and "flatten_all" in types
    assert types.index("ws01") < types.index("flatten_all"), (
        f"WS01 must precede flatten_all; observed order {types}"
    )


# --------------------------------------------------------------------------- #
# Regression: vol field in WS01 trace must use the same bars_per_year as
# the strategy's signal computation. Otherwise on 4h bars the trace shows
# a vol that's a factor of sqrt(6) too small (R1 critic finding #3).
# --------------------------------------------------------------------------- #

def test_ws01_decision_ts_is_distinct_per_cycle(monkeypatch, caplog):
    """decision_ts must change between cycles (it's the actual timestamp,
    not a constant). Two consecutive cycles produce two distinct values."""
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    kwargs = _make_ws01_kwargs(monkeypatch)
    rpt.run_cycle(**kwargs)
    # Sleep a tick so timestamps differ
    import time
    time.sleep(0.01)
    rpt.run_cycle(**kwargs)
    lines = _ws01_lines_after(caplog)
    assert len(lines) >= 2
    ts1 = json.loads(lines[0].removeprefix("ws01 "))["decision_ts"]
    ts2 = json.loads(lines[-1].removeprefix("ws01 "))["decision_ts"]
    assert ts1 != ts2, "decision_ts must update per cycle, not be constant"


def test_ws01_strategy_params_absent_on_early_exit(monkeypatch, caplog):
    """Early-exit paths (kill-active, no-data, etc.) emit ws01 BEFORE
    the strategy module computes -- strategy_params must serialize as
    null (or be absent), not crash."""
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")
    kwargs = _make_ws01_kwargs(monkeypatch)
    kwargs["kill_switch"].is_triggered = True
    kwargs["kill_switch"].status_line = "halted"
    rpt.run_cycle(**kwargs)
    lines = _ws01_lines_after(caplog)
    payload = json.loads(lines[0].removeprefix("ws01 "))
    # Either absent OR null -- both are fine; the trace must not crash and
    # must not emit a stale prior-cycle params dict.
    assert payload.get("strategy_params") is None
    assert payload["action"] == "KILL_HALTED_PRECYCLE"


def test_ws01_vol_uses_dynamic_bars_per_year_4h(monkeypatch, caplog):
    """On 4H-frequency bars, vol annualization must NOT use hardcoded sqrt(252).

    A 4h bar at median dt = 4*3600s yields bars_per_year = 252*24*3600/14400
    = 1512 -- so sqrt(1512) ≈ 38.9 vs sqrt(252) ≈ 15.9 (a factor of ~2.45
    difference). The WS01 vol field must reflect the dynamic factor.
    """
    caplog.set_level(logging.INFO, logger="run_paper_trading_vt")

    # Build 4H synthetic data with controlled return std so we can verify
    # the annualization scalar.
    rng = np.random.default_rng(7)
    n = 320
    base_sigma_per_bar = 0.001  # arbitrary
    rets = rng.normal(0, base_sigma_per_bar, n)
    close = 150.0 * np.exp(np.cumsum(rets))
    ohlcv = pd.DataFrame({
        "open": close, "high": close * 1.001, "low": close * 0.999,
        "close": close, "volume": np.full(n, 1000.0),
    }, index=pd.date_range("2025-01-01", periods=n, freq="4h"))

    kwargs = _make_ws01_kwargs(monkeypatch)
    monkeypatch.setattr(rpt, "fetch_recent_bars", lambda *a, **kw: ohlcv)

    # Set sizer to return 0 so we hit HOLD FLAT branch (main-path emit)
    kwargs["sizer"].calculate_size.return_value = 0.0

    rpt.run_cycle(**kwargs)

    lines = _ws01_lines_after(caplog)
    assert len(lines) >= 1
    payload = json.loads(lines[-1].removeprefix("ws01 "))

    # Compute the expected vol with dynamic bars_per_year
    from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy
    expected_bars_per_year = VolTargetCarryStrategy._bars_per_year(ohlcv)
    expected_vol = (
        ohlcv["close"].pct_change().rolling(252).std().iloc[-1]
    ) * (expected_bars_per_year ** 0.5)
    # 4H data yields bars_per_year ≈ 1512, NOT 252
    assert expected_bars_per_year > 1000, (
        f"4h bars should yield bars_per_year >> 252; got {expected_bars_per_year}"
    )
    # The vol in the trace must match the dynamic-formula expected vol
    assert payload["vol"] == pytest.approx(float(expected_vol), rel=1e-6)
    # And NOT match the wrong-formula (sqrt(252)) vol
    wrong_vol = (
        ohlcv["close"].pct_change().rolling(252).std().iloc[-1]
    ) * (252 ** 0.5)
    assert payload["vol"] != pytest.approx(float(wrong_vol), rel=1e-3)
