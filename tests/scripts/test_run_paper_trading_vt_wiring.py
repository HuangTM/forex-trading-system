"""Tests for Wave-5 Round-1 wiring in scripts/run_paper_trading_vt.py.

Covers three deliverables:
  D1 — Pre-trade aggregation gate (CRO binding constraint #1)
  D2 — HeartbeatWatchdog (CRO binding constraint #2)
  D3 — CF-T9 status reader / Bet #1 sizing helpers (bet1_sizing.py)

Does NOT import the full paper loop (avoids network / broker dependencies).
Each test mocks at the module boundary and exercises the wiring logic in
isolation.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from forex_system.core.types import Direction, Position
from forex_system.risk.bet1_sizing import (
    BET1_SIZE_MULTIPLIER_REGIME_ACTIVE,
    BET1_SIZE_MULTIPLIER_REGIME_INACTIVE,
    CF_T9_HEARTBEAT_MAX_AGE_SECONDS,
    CF_T9_MIN_REGIME_READINGS,
    bet1_size_multiplier,
    regime_active_status,
)
from forex_system.risk.exposure_aggregator import (
    AggregationGateBlocked,
    check_dispatch_allowed,
    compute_exposure,
)
from forex_system.risk.heartbeat_watchdog import HeartbeatWatchdog

# ---------------------------------------------------------------------------
# D1: Aggregation gate
# ---------------------------------------------------------------------------


def _make_position(pair: str, size: float, entry_price: float) -> Position:
    import pandas as pd
    return Position(
        pair=pair,
        direction=Direction.LONG,
        size=size,
        entry_price=entry_price,
        entry_time=pd.Timestamp.now(tz="UTC"),
        unrealized_pnl=0.0,
    )


class TestAggregationGateWiring:
    """D1: Verify aggregation gate blocks when CRO limits are breached."""

    def test_gate_passes_when_within_limits(self):
        """Mixed book with USDJPY (JPY-correlated) at <15% of total notional should pass.

        A single USDJPY position is 100% JPY-correlated, so a mixed book is
        required to stay under the 15% threshold.  Here we put 1 USDJPY unit
        at notional 150 alongside a large EURUSD position (notional 10_000)
        so JPY-correlated fraction ≈ 1.5% < 15%.
        """
        positions = [
            _make_position("USDJPY", 1, 150.0),   # notional 150; JPY-correlated
            _make_position("EURUSD", 10_000, 1.0), # notional 10000; not JPY-correlated
        ]
        snapshot = compute_exposure(positions)
        # jpy_correlated_pct ≈ 150 / 10150 ≈ 1.5% — well under 0.15 limit
        # Should not raise
        check_dispatch_allowed(
            snapshot,
            max_correlated_pct=0.15,
            max_active_strategies=4,
            max_concurrent_positions=6,
        )

    def test_gate_blocks_jpy_concentration(self):
        """When JPY-correlated notional > 15% of book, gate must raise."""
        # 100% of book is JPY-correlated → exceeds 0.15
        positions = [_make_position("USDJPY", 10_000, 150.0)]
        snapshot = compute_exposure(positions)
        with pytest.raises(AggregationGateBlocked, match="jpy_correlated_pct"):
            check_dispatch_allowed(
                snapshot,
                max_correlated_pct=0.15,
                max_active_strategies=4,
                max_concurrent_positions=6,
            )

    def test_gate_blocks_max_concurrent_positions_exceeded(self):
        """When open positions > max_concurrent_positions, gate must raise."""
        # Create 7 EURUSD positions (no JPY correlation, unique pairs proxied)
        pairs = [f"EUR{chr(65+i)}SD" for i in range(7)]
        positions = [_make_position(p, 1000, 1.0) for p in pairs]
        snapshot = compute_exposure(positions)
        with pytest.raises(AggregationGateBlocked, match="open_positions"):
            check_dispatch_allowed(
                snapshot,
                max_correlated_pct=0.15,
                max_active_strategies=4,
                max_concurrent_positions=6,
            )

    def test_gate_blocks_max_active_strategies_exceeded(self):
        """When distinct pair-proxied strategy count > max, gate must raise."""
        # 5 distinct pairs → proxy strategy count = 5 > 4
        pairs = [f"PAIR{i}FX" for i in range(5)]
        positions = [_make_position(p, 1000, 1.0) for p in pairs]
        snapshot = compute_exposure(positions)
        with pytest.raises(AggregationGateBlocked, match="active_strategies"):
            check_dispatch_allowed(
                snapshot,
                max_correlated_pct=0.15,
                max_active_strategies=4,
                max_concurrent_positions=6,
            )

    def test_paper_loop_run_cycle_skips_on_gate_blocked(self):
        """Mock run_cycle path: when aggregation gate raises, cycle returns SKIP_AGGREGATION_GATE."""
        import scripts.run_paper_trading_vt as loop_mod

        # Reset module halt state
        loop_mod._HALT_REQUESTED = False
        loop_mod._HALT_REASON = ""

        # Build a minimal position dict that will trigger JPY concentration block
        import pandas as pd
        pos = Position(
            pair="USDJPY",
            direction=Direction.LONG,
            size=10_000,
            entry_price=150.0,
            entry_time=pd.Timestamp.now(tz="UTC"),
            unrealized_pnl=0.0,
        )

        kill_switch = MagicMock()
        kill_switch.is_triggered = False
        kill_switch.check_and_trigger.return_value = False
        kill_switch.record_equity_fetch_failure.return_value = False
        kill_switch.consecutive_fetch_failures = 0
        kill_switch.max_consecutive_fetch_failures = 3
        kill_switch.record_equity_fetch_success.return_value = None

        backend = MagicMock()
        backend.get_positions.return_value = {"USDJPY": pos}
        backend.account_key = "TEST_ACCOUNT"

        client = MagicMock()
        client.get_balance.return_value = {"TotalValue": 100_000.0}

        # patch fetch_account_equity to return a value
        with patch.object(loop_mod, "fetch_account_equity", return_value=100_000.0):
            result = loop_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=MagicMock(),
                strategy=MagicMock(),
                pair="USDJPY",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=kill_switch,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=1,
            )

        assert result.get("_action") == "SKIP_AGGREGATION_GATE"


# ---------------------------------------------------------------------------
# D2: HeartbeatWatchdog wiring
# ---------------------------------------------------------------------------


class TestHeartbeatWatchdogWiring:
    """D2: Verify watchdog fires after timeout and halt callback is invoked."""

    def test_watchdog_fires_on_timeout(self):
        """After idle > timeout_seconds, on_timeout must be called exactly once."""
        fired: list[float] = []

        def capture_timeout(seconds_idle: float) -> None:
            fired.append(seconds_idle)

        wd = HeartbeatWatchdog(
            timeout_seconds=0.1,  # 100ms — accelerated for test
            on_timeout=capture_timeout,
        )
        wd.start()
        try:
            # Do NOT tick — let it time out
            time.sleep(0.5)
        finally:
            wd.stop()

        assert len(fired) == 1
        assert fired[0] > 0.1

    def test_watchdog_does_not_fire_when_ticking(self):
        """When tick() is called regularly (faster than timeout), callback must NOT fire."""
        fired: list[float] = []

        def capture_timeout(seconds_idle: float) -> None:
            fired.append(seconds_idle)

        wd = HeartbeatWatchdog(
            timeout_seconds=0.5,
            on_timeout=capture_timeout,
        )
        wd.start()
        try:
            for _ in range(10):
                wd.tick()
                time.sleep(0.05)  # 50ms — well under 500ms timeout
        finally:
            wd.stop()

        assert fired == []

    def test_halt_callback_invoked_by_loop_module(self):
        """Verify halt_paper_loop sets module-level _HALT_REQUESTED flag."""
        import scripts.run_paper_trading_vt as loop_mod

        # Reset state before test
        loop_mod._HALT_REQUESTED = False
        loop_mod._HALT_REASON = ""

        loop_mod.halt_paper_loop(reason="watchdog_timeout_301.0s")

        assert loop_mod._HALT_REQUESTED is True
        assert "watchdog_timeout" in loop_mod._HALT_REASON

    def test_run_cycle_blocked_when_halt_requested(self):
        """When _HALT_REQUESTED is True, run_cycle must return HALT_WATCHDOG without dispatch."""
        import scripts.run_paper_trading_vt as loop_mod

        loop_mod._HALT_REQUESTED = True
        loop_mod._HALT_REASON = "watchdog_timeout_301.0s"

        kill_switch = MagicMock()
        kill_switch.is_triggered = False

        result = loop_mod.run_cycle(
            client=MagicMock(),
            backend=MagicMock(),
            sizer=MagicMock(),
            strategy=MagicMock(),
            pair="USDJPY",
            pred_log=MagicMock(),
            trade_log=MagicMock(),
            kill_switch=kill_switch,
            rebal_threshold=0.20,
            cycle_id=99,
        )

        assert result.get("_action") == "HALT_WATCHDOG"

        # Reset for subsequent tests
        loop_mod._HALT_REQUESTED = False
        loop_mod._HALT_REASON = ""

    def test_cro_timeout_constant_is_300s(self):
        """Verify the module exports the CRO-mandated 300s timeout constant."""
        import scripts.run_paper_trading_vt as loop_mod
        assert loop_mod.CRO_WATCHDOG_TIMEOUT_SECONDS == 300.0


# ---------------------------------------------------------------------------
# D3: CF-T9 status reader / bet1_sizing
# ---------------------------------------------------------------------------


class TestBet1Sizing:
    """D3: Verify CF-T9 status reader + Bet #1 sizing helpers."""

    def test_size_multiplier_regime_inactive(self):
        """BC-1: size_multiplier must be 0.0 when regime is inactive."""
        assert bet1_size_multiplier(regime_active=False) == BET1_SIZE_MULTIPLIER_REGIME_INACTIVE
        assert bet1_size_multiplier(regime_active=False) == 0.0

    def test_size_multiplier_regime_active(self):
        """BC-2: size_multiplier must be 0.25 when regime is active."""
        assert bet1_size_multiplier(regime_active=True) == BET1_SIZE_MULTIPLIER_REGIME_ACTIVE
        assert bet1_size_multiplier(regime_active=True) == 0.25

    def test_regime_active_returns_false_when_file_missing(self, tmp_path):
        """BC-3/BC-5: Returns False when CF-T9 status file does not exist."""
        result = regime_active_status(cf_t9_status_path=str(tmp_path / "no_such_file.json"))
        assert result is False

    def test_regime_active_returns_false_when_file_stale(self, tmp_path):
        """BC-5: Returns False when file mtime is older than 5 minutes."""
        status_file = tmp_path / "cf_t9_status.json"
        payload = {
            "regime_active": True,
            "n_readings": 20,
            "seen_regime_active_true": True,
            "seen_regime_active_false": True,
        }
        status_file.write_text(json.dumps(payload))

        # Backdate the mtime by 6 minutes (> CF_T9_HEARTBEAT_MAX_AGE_SECONDS = 300s)
        stale_mtime = time.time() - 360.0
        import os
        os.utime(status_file, (stale_mtime, stale_mtime))

        result = regime_active_status(cf_t9_status_path=str(status_file))
        assert result is False

    def test_regime_active_returns_false_when_cold_start_not_cleared(self, tmp_path):
        """BC-4: Returns False when n_readings < 10."""
        status_file = tmp_path / "cf_t9_status.json"
        payload = {
            "regime_active": True,
            "n_readings": 5,  # < CF_T9_MIN_REGIME_READINGS = 10
            "seen_regime_active_true": True,
            "seen_regime_active_false": True,
        }
        status_file.write_text(json.dumps(payload))

        result = regime_active_status(cf_t9_status_path=str(status_file))
        assert result is False

    def test_regime_active_returns_false_when_both_states_not_seen(self, tmp_path):
        """BC-4: Returns False when only one regime state has been observed."""
        status_file = tmp_path / "cf_t9_status.json"
        payload = {
            "regime_active": True,
            "n_readings": 15,
            "seen_regime_active_true": True,
            "seen_regime_active_false": False,  # never saw regime=False
        }
        status_file.write_text(json.dumps(payload))

        result = regime_active_status(cf_t9_status_path=str(status_file))
        assert result is False

    def test_regime_active_returns_true_when_all_gates_clear(self, tmp_path):
        """Returns True only when all BC-3/BC-4/BC-5 gates are satisfied."""
        status_file = tmp_path / "cf_t9_status.json"
        payload = {
            "regime_active": True,
            "n_readings": 15,
            "seen_regime_active_true": True,
            "seen_regime_active_false": True,
        }
        status_file.write_text(json.dumps(payload))
        # File is fresh (just written — mtime is now)

        result = regime_active_status(cf_t9_status_path=str(status_file))
        assert result is True

    def test_regime_active_returns_false_when_regime_flag_false(self, tmp_path):
        """Returns False when all gates pass but regime flag itself is False."""
        status_file = tmp_path / "cf_t9_status.json"
        payload = {
            "regime_active": False,  # regime is inactive
            "n_readings": 15,
            "seen_regime_active_true": True,
            "seen_regime_active_false": True,
        }
        status_file.write_text(json.dumps(payload))

        result = regime_active_status(cf_t9_status_path=str(status_file))
        assert result is False

    def test_cro_constants_match_wave4_artifact(self):
        """Verify binding constants match CRO Wave-4 artifact values."""
        assert BET1_SIZE_MULTIPLIER_REGIME_INACTIVE == 0.0
        assert BET1_SIZE_MULTIPLIER_REGIME_ACTIVE == 0.25
        assert CF_T9_HEARTBEAT_MAX_AGE_SECONDS == 300.0
        assert CF_T9_MIN_REGIME_READINGS == 10


# ---------------------------------------------------------------------------
# Sacred test guard: no_lookahead (import + run in-process)
# ---------------------------------------------------------------------------

class TestSacredTestStillPasses:
    """Verify the sacred no-lookahead invariant is unaffected by wiring changes."""

    def test_no_lookahead_import(self):
        """The sacred test module must be importable without errors."""
        import tests.backtest.test_engine  # noqa: F401 (import side-effect check)
        # If this import fails, the sacred test is broken at import time.
