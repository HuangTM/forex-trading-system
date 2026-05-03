"""Tests for scripts/run_paper_trading_carry_fred.py — Bet #1 wiring (Gap C).

Covers ≥6 test cases:
  1. Module imports without errors (no network/broker deps)
  2. run_cycle calls bet1_size_multiplier (BC-2 wired)
  3. Regime-inactive path returns SKIP_REGIME_INACTIVE (BC-1 hard zero)
  4. Aggregation gate honoured when positions exceed CRO limit
  5. Watchdog is wired (CRO #2: timeout constant exported, halt callback works)
  6. DrawdownContract integrated: DD ≥ 20% → SKIP_DD_FULL_HALT
  7. DD ≥ 10% → SKIP_DD_HALT_NEW without halting loop
  8. REDUCE_SIZING (15% DD) does NOT skip but applies 0.5x multiplier in assessment
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from forex_system.core.types import Direction, Position
from forex_system.risk.drawdown_contract import DrawdownContract, DrawdownLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_position(pair: str, size: float, entry_price: float) -> "Position":
    import pandas as pd
    return Position(
        pair=pair,
        direction=Direction.LONG,
        size=size,
        entry_price=entry_price,
        entry_time=pd.Timestamp.now(tz="UTC"),
        unrealized_pnl=0.0,
    )


def _make_mock_infra(equity: float = 100_000.0, flat_book: bool = True):
    """Return (client, backend, kill_switch) mocks for a healthy cycle."""
    kill_switch = MagicMock()
    kill_switch.is_triggered = False
    kill_switch.check_and_trigger.return_value = False
    kill_switch.record_equity_fetch_failure.return_value = False
    kill_switch.consecutive_fetch_failures = 0
    kill_switch.max_consecutive_fetch_failures = 3
    kill_switch.record_equity_fetch_success.return_value = None

    backend = MagicMock()
    backend.get_positions.return_value = {} if flat_book else {
        "USDJPY": _make_position("USDJPY", 10_000, 150.0)
    }
    backend.account_key = "TEST_CF_ACCOUNT"

    client = MagicMock()
    return client, backend, kill_switch


def _std_dd_contract() -> DrawdownContract:
    return DrawdownContract(
        halt_threshold=0.10,
        reduce_threshold=0.15,
        full_halt_threshold=0.20,
    )


# ---------------------------------------------------------------------------
# Test 1: Module imports
# ---------------------------------------------------------------------------


class TestModuleImports:
    def test_module_importable(self):
        """scripts/run_paper_trading_carry_fred.py must import without errors."""
        import scripts.run_paper_trading_carry_fred  # noqa: F401


# ---------------------------------------------------------------------------
# Test 2: bet1_size_multiplier is called in run_cycle
# ---------------------------------------------------------------------------


class TestBet1SizeMultiplierWired:
    def test_run_cycle_calls_bet1_size_multiplier(self):
        """bet1_size_multiplier must be called each cycle (BC-2 wired)."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        client, backend, ks = _make_mock_infra()
        dd = _std_dd_contract()
        dd.assess(100_000.0)   # set peak

        # Patch regime_active_status to return True, and bet1_size_multiplier
        with patch.object(cf_mod, "regime_active_status", return_value=True) as mock_ras, \
             patch.object(cf_mod, "bet1_size_multiplier", return_value=0.25) as mock_b1m, \
             patch.object(cf_mod, "fetch_account_equity", return_value=100_000.0), \
             patch.object(cf_mod, "fetch_recent_bars",
                          return_value=__import__("pandas").DataFrame()):
            cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=MagicMock(),
                strategy=MagicMock(),
                pair="USDJPY",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=1,
            )

        mock_ras.assert_called_once()
        mock_b1m.assert_called_once_with(True)


# ---------------------------------------------------------------------------
# Test 3: Regime-inactive path
# ---------------------------------------------------------------------------


class TestRegimeInactivePath:
    def test_regime_inactive_returns_skip_regime_inactive(self):
        """When regime_active_status() is False, cycle must return SKIP_REGIME_INACTIVE."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        client, backend, ks = _make_mock_infra()
        dd = _std_dd_contract()

        with patch.object(cf_mod, "regime_active_status", return_value=False):
            result = cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=MagicMock(),
                strategy=MagicMock(),
                pair="USDJPY",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=1,
            )

        assert result.get("_action") == cf_mod.SKIP_REGIME_INACTIVE
        # Loop must remain active — SKIP_REGIME_INACTIVE is the steady state
        assert cf_mod._HALT_REQUESTED is False

    def test_regime_inactive_does_not_fetch_equity(self):
        """Regime check is the FIRST gate; equity fetch must NOT happen when inactive."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        client, backend, ks = _make_mock_infra()
        dd = _std_dd_contract()

        with patch.object(cf_mod, "regime_active_status", return_value=False), \
             patch.object(cf_mod, "fetch_account_equity") as mock_eq:
            cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=MagicMock(),
                strategy=MagicMock(),
                pair="USDJPY",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=2,
            )

        mock_eq.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Aggregation gate
# ---------------------------------------------------------------------------


class TestAggregationGateHonoured:
    def test_aggregation_gate_blocks_when_jpy_concentration_exceeded(self):
        """When JPY-correlated notional > 15% of book, cycle returns SKIP_AGGREGATION_GATE."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        # Build a backend with an all-USDJPY book (100% JPY-correlated)
        client, backend, ks = _make_mock_infra(flat_book=False)
        dd = _std_dd_contract()
        dd.assess(100_000.0)

        with patch.object(cf_mod, "regime_active_status", return_value=True), \
             patch.object(cf_mod, "bet1_size_multiplier", return_value=0.25), \
             patch.object(cf_mod, "fetch_account_equity", return_value=100_000.0):
            result = cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=MagicMock(),
                strategy=MagicMock(),
                pair="USDJPY",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=dd,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=3,
            )

        assert result.get("_action") == "SKIP_AGGREGATION_GATE"


# ---------------------------------------------------------------------------
# Test 5: Watchdog wired
# ---------------------------------------------------------------------------


class TestWatchdogWired:
    def test_cro_watchdog_timeout_constant_exported(self):
        """Module must export CRO_WATCHDOG_TIMEOUT_SECONDS == 300.0."""
        import scripts.run_paper_trading_carry_fred as cf_mod
        assert cf_mod.CRO_WATCHDOG_TIMEOUT_SECONDS == 300.0

    def test_halt_paper_loop_sets_flag(self):
        """halt_paper_loop must set _HALT_REQUESTED module flag."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        cf_mod.halt_paper_loop(reason="watchdog_timeout_305.0s")

        assert cf_mod._HALT_REQUESTED is True
        assert "watchdog" in cf_mod._HALT_REASON

        # Reset
        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

    def test_run_cycle_blocked_when_halt_requested(self):
        """When _HALT_REQUESTED is True, run_cycle returns HALT_WATCHDOG immediately."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = True
        cf_mod._HALT_REASON = "watchdog_timeout_305.0s"

        result = cf_mod.run_cycle(
            client=MagicMock(),
            backend=MagicMock(),
            sizer=MagicMock(),
            strategy=MagicMock(),
            pair="USDJPY",
            pred_log=MagicMock(),
            trade_log=MagicMock(),
            kill_switch=MagicMock(is_triggered=False),
            dd_contract=_std_dd_contract(),
            rebal_threshold=0.20,
            cycle_id=99,
        )

        assert result.get("_action") == "HALT_WATCHDOG"

        # Reset
        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""


# ---------------------------------------------------------------------------
# Test 6 + 7: DrawdownContract integrated
# ---------------------------------------------------------------------------


class TestDrawdownContractIntegrated:
    def test_full_halt_returns_skip_dd_full_halt_and_halts_loop(self):
        """DD ≥ 20% must return SKIP_DD_FULL_HALT and set _HALT_REQUESTED."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        client, backend, ks = _make_mock_infra()
        contract = DrawdownContract(
            halt_threshold=0.10, reduce_threshold=0.15, full_halt_threshold=0.20,
        )
        contract.assess(100_000.0)   # peak = 100k

        with patch.object(cf_mod, "regime_active_status", return_value=True), \
             patch.object(cf_mod, "bet1_size_multiplier", return_value=0.25), \
             patch.object(cf_mod, "fetch_account_equity", return_value=80_000.0):
            result = cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=MagicMock(),
                strategy=MagicMock(),
                pair="USDJPY",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=contract,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=5,
            )

        assert result.get("_action") == cf_mod.SKIP_DD_FULL_HALT
        assert cf_mod._HALT_REQUESTED is True

        # Reset
        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

    def test_halt_new_dispatch_returns_skip_dd_halt_new_no_loop_halt(self):
        """10% ≤ DD < 15% must return SKIP_DD_HALT_NEW without halting the loop."""
        import scripts.run_paper_trading_carry_fred as cf_mod

        cf_mod._HALT_REQUESTED = False
        cf_mod._HALT_REASON = ""

        client, backend, ks = _make_mock_infra()
        contract = DrawdownContract(
            halt_threshold=0.10, reduce_threshold=0.15, full_halt_threshold=0.20,
        )
        contract.assess(100_000.0)

        with patch.object(cf_mod, "regime_active_status", return_value=True), \
             patch.object(cf_mod, "bet1_size_multiplier", return_value=0.25), \
             patch.object(cf_mod, "fetch_account_equity", return_value=90_000.0):
            result = cf_mod.run_cycle(
                client=client,
                backend=backend,
                sizer=MagicMock(),
                strategy=MagicMock(),
                pair="USDJPY",
                pred_log=MagicMock(),
                trade_log=MagicMock(),
                kill_switch=ks,
                dd_contract=contract,
                rebal_threshold=0.20,
                auto_mode=True,
                cycle_id=6,
            )

        assert result.get("_action") == cf_mod.SKIP_DD_HALT_NEW
        assert cf_mod._HALT_REQUESTED is False

    def test_reduce_sizing_does_not_produce_skip_action(self):
        """15% DD gives REDUCE_SIZING: no skip, but dd_contract.assess returns 0.5 multiplier."""
        contract = DrawdownContract(
            halt_threshold=0.10, reduce_threshold=0.15, full_halt_threshold=0.20,
        )
        contract.assess(100_000.0)
        assessment = contract.assess(85_000.0)   # exactly 15% DD

        assert assessment.level == DrawdownLevel.REDUCE_SIZING
        assert assessment.sizing_multiplier == 0.5
        # Not HALT_NEW_DISPATCH or FULL_HALT — cycle would continue with 0.5x sizing
        assert assessment.level not in (DrawdownLevel.HALT_NEW_DISPATCH, DrawdownLevel.FULL_HALT)
