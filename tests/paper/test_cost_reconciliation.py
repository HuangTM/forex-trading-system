"""Deterministic regression oracles for ModeledEquityLedger.

Math TC1-TC5 (shape) + persistence + mock-exclusion + alarm/ladder tests.

All numerical oracles are derived directly from the Mathematician recurrence:
    E_m(t) = E_m(t-1) + held_engine_units(t-1) * (P(t) - P(t-1))
             + swap_usd(t) - cost_usd(t)
where:
    held_engine_units = held_units_nom / mid_prev   (JPY pairs)
                      = held_units_nom               (non-JPY pairs)

Constants sourced from src/forex_system/core/constants.py (DEFAULT_PAIRS):
    USDJPY: pip_value=0.01, spread_pips=0.5, slippage_pips=0.5, commission_pips=0.5
            swap_long_pips_per_day=0.8  →  entry_cost_pips = 0.75, exit_cost_pips = 1.25
    EURUSD: pip_value=0.0001, spread_pips=0.5, slippage_pips=0.5, commission_pips=0.5
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from forex_system.paper.cost_reconciliation import (
    ModeledEquityLedger,
    ledger_from_config,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_ledger(
    strategy_id: str = "test_strat",
    tol_rel: float = 0.005,
    tol_abs: float = 500.0,
    enforce: bool = False,
    consecutive_n: int = 3,
    data_dir: Optional[str] = None,
    ntfy_fn=None,
) -> ModeledEquityLedger:
    """Create a fresh in-memory ledger (temp dir so state files don't pollute cwd)."""
    if data_dir is None:
        data_dir = tempfile.mkdtemp()
    return ModeledEquityLedger(
        strategy_id=strategy_id,
        tol_rel=tol_rel,
        tol_abs=tol_abs,
        enforce=enforce,
        consecutive_n=consecutive_n,
        data_dir=data_dir,
        ntfy_fn=ntfy_fn,
    )


# ---------------------------------------------------------------------------
# TC1: Clean multi-cycle ledger build (no costs, no swap, price move)
#
# Setup: USDJPY, E_b(0)=100000, mid_seed=150.0, held_nom=10000
#   Cycle 1: mid_now=150.5, held_nom=10000 (same as seed), cost=0, swap=0
#     held_engine_units = 10000 / 150.0 = 66.6667
#     pnl = 66.6667 * (150.5 - 150.0) = 33.3333
#     E_m(1) = 100000 + 33.3333 + 0 - 0 = 100033.3333
#   Cycle 2: mid_now=151.0, held_nom=10000, cost=0, swap=0
#     held_engine_units = 10000 / 150.5 = 66.4452
#     pnl = 66.4452 * (151.0 - 150.5) = 33.2226
#     E_m(2) = 100033.3333 + 33.2226 = 100066.5559
# ---------------------------------------------------------------------------


class TestTC1MultiCycleLedger:
    """TC1: Multi-cycle build with price moves only."""

    def test_cycle1_oracle(self):
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)

        result = led.update(
            pair="USDJPY",
            mid_now=150.5,
            held_units_nom=10_000.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=100_050.0,  # broker moved independently
            cycle_id=1,
        )

        # Oracle: held_engine_units = 10000/150.0; pnl = 66.6667 * 0.5
        expected_em = 100_000.0 + (10_000.0 / 150.0) * 0.5
        assert abs(result.modeled_equity - expected_em) < 1e-6, (
            f"TC1 cycle1: E_m={result.modeled_equity:.6f} expected={expected_em:.6f}"
        )

    def test_cycle2_oracle(self):
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)
        led.update("USDJPY", 150.5, 10_000.0, 0.0, 0.0, 100_050.0, cycle_id=1)

        # After cycle1: last_mid["USDJPY"] = 150.5
        result = led.update(
            pair="USDJPY",
            mid_now=151.0,
            held_units_nom=10_000.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=100_100.0,
            cycle_id=2,
        )

        # Oracle: pnl cycle2 = (10000/150.5) * (151.0 - 150.5)
        em_after_c1 = 100_000.0 + (10_000.0 / 150.0) * 0.5
        em_after_c2 = em_after_c1 + (10_000.0 / 150.5) * 0.5
        assert abs(result.modeled_equity - em_after_c2) < 1e-6, (
            f"TC1 cycle2: E_m={result.modeled_equity:.6f} expected={em_after_c2:.6f}"
        )


# ---------------------------------------------------------------------------
# TC2: Costs and swap applied
#
# Setup: USDJPY, E_m(0)=100000, mid_seed=150.0, held_nom=10000
#   Cycle 1 (with cost and swap):
#     mid_now=150.5, held_nom=10000, cost_usd=7.5, swap_usd=5.33
#     held_engine_units = 10000/150.0 = 66.6667
#     pnl = 66.6667 * 0.5 = 33.3333
#     E_m(1) = 100000 + 33.3333 + 5.33 - 7.5 = 100031.1633
# ---------------------------------------------------------------------------


class TestTC2CostsAndSwap:
    """TC2: Verify cost and swap flow through recurrence correctly."""

    def test_cost_swap_oracle(self):
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)

        cost_usd = 7.5
        swap_usd = 5.33
        result = led.update(
            pair="USDJPY",
            mid_now=150.5,
            held_units_nom=10_000.0,
            cost_usd=cost_usd,
            swap_usd=swap_usd,
            broker_equity=100_030.0,
            cycle_id=1,
        )

        pnl = (10_000.0 / 150.0) * 0.5
        expected_em = 100_000.0 + pnl + swap_usd - cost_usd
        assert abs(result.modeled_equity - expected_em) < 1e-6, (
            f"TC2: E_m={result.modeled_equity:.6f} expected={expected_em:.6f}"
        )

    def test_zero_swap_first_cycle(self):
        """TC5 shape: first cycle swap=0 → only pnl and cost."""
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)
        result = led.update("USDJPY", 150.0, 10_000.0, 3.0, 0.0, 100_000.0, cycle_id=1)
        # pnl = 0 (mid unchanged), swap = 0, cost = 3.0
        expected_em = 100_000.0 - 3.0
        assert abs(result.modeled_equity - expected_em) < 1e-6


# ---------------------------------------------------------------------------
# TC3: Rebalance — cost on |delta| only, flat position pnl=0
#
# Setup: E_m(0)=100000, USDJPY mid_seed=150, held_nom=0 (flat), cost_usd=5
#   pnl = 0 (no held units)
#   E_m(1) = 100000 + 0 + 0 - 5 = 99995
# ---------------------------------------------------------------------------


class TestTC3FlatPositionRebalance:
    """TC3: Flat position → pnl=0; only cost is applied."""

    def test_flat_position_no_pnl(self):
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)
        result = led.update(
            pair="USDJPY",
            mid_now=151.0,
            held_units_nom=0.0,  # flat before this cycle
            cost_usd=5.0,
            swap_usd=0.0,
            broker_equity=99_995.0,
            cycle_id=1,
        )
        # Oracle: pnl = 0 (held_units_nom = 0)
        assert abs(result.modeled_equity - 99_995.0) < 1e-6, (
            f"TC3 flat: E_m={result.modeled_equity} expected=99995.0"
        )

    def test_position_flip_cost_only(self):
        """Close existing position then open new: held_nom before close = old_units."""
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)
        # Cycle 1: long 10000, price unchanged, entry cost 7.5
        led.update("USDJPY", 150.0, 0.0, 7.5, 0.0, 99_992.5, cycle_id=1)
        # Cycle 2: CLOSE — held 10000 before action, exit cost 12.5
        result = led.update(
            pair="USDJPY",
            mid_now=150.0,
            held_units_nom=10_000.0,
            cost_usd=12.5,
            swap_usd=0.0,
            broker_equity=99_980.0,
            cycle_id=2,
        )
        # held_engine_units = 10000/150 = 66.6667; pnl = 66.6667 * 0 = 0
        prev_em = 100_000.0 - 7.5
        expected_em = prev_em + 0 + 0 - 12.5
        assert abs(result.modeled_equity - expected_em) < 1e-6


# ---------------------------------------------------------------------------
# TC4: JPY pair engine-units conversion
#
# Verify that for USDJPY, held_engine_units = held_units_nom / mid_prev
# (NOT held_units_nom directly). This is the F-001 fix.
#
# Oracle comparison: if we WRONGLY used held_units_nom directly, the pnl
# would be ~150x larger for USDJPY.
# ---------------------------------------------------------------------------


class TestTC4JPYEngineUnits:
    """TC4: JPY pair divides by mid_prev for engine-units."""

    def test_jpy_uses_division(self):
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)
        result = led.update(
            pair="USDJPY",
            mid_now=151.0,
            held_units_nom=15_000.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=100_100.0,
            cycle_id=1,
        )
        # Correct: engine_units = 15000/150 = 100; pnl = 100 * 1.0 = 100
        expected_em = 100_000.0 + 100.0
        assert abs(result.modeled_equity - expected_em) < 1e-6, (
            f"TC4 JPY correct: E_m={result.modeled_equity} expected={expected_em}"
        )

    def test_jpy_wrong_without_division_would_differ(self):
        """Negative oracle: NOT dividing by mid gives ~150x different result."""
        led_correct = _make_ledger(strategy_id="correct")
        led_correct.seed(100_000.0, "USDJPY", 150.0)
        r = led_correct.update("USDJPY", 151.0, 15_000.0, 0.0, 0.0, 100_100.0, cycle_id=1)
        correct_em = r.modeled_equity  # 100_100

        # The "wrong" formula would multiply held_units_nom * price_change directly
        wrong_em = 100_000.0 + 15_000.0 * (151.0 - 150.0)  # = 115_000
        assert abs(correct_em - wrong_em) > 1000, (
            "TC4 negative oracle: JPY without division should produce wildly different result"
        )

    def test_non_jpy_no_division(self):
        """EURUSD: held_engine_units = held_units_nom (no division)."""
        led = _make_ledger()
        led.seed(100_000.0, "EURUSD", 1.08)
        result = led.update(
            pair="EURUSD",
            mid_now=1.09,
            held_units_nom=100_000.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=101_000.0,
            cycle_id=1,
        )
        # EURUSD: engine_units = 100_000 (no division)
        expected_em = 100_000.0 + 100_000.0 * (1.09 - 1.08)
        assert abs(result.modeled_equity - expected_em) < 1e-6, (
            f"TC4 EURUSD: E_m={result.modeled_equity} expected={expected_em}"
        )


# ---------------------------------------------------------------------------
# TC5: First cycle semantics (swap=0, E_m(0)=E_b(0))
# ---------------------------------------------------------------------------


class TestTC5FirstCycle:
    """TC5: Seed and first-cycle invariants."""

    def test_seed_sets_modeled_to_broker(self):
        led = _make_ledger()
        assert led.modeled_equity is None
        led.seed(98_765.43, "USDJPY", 150.0)
        assert abs(led.modeled_equity - 98_765.43) < 1e-6

    def test_seed_idempotent(self):
        """Second seed call is a no-op (preserves first seed value)."""
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)
        led.seed(200_000.0, "USDJPY", 155.0)  # should be ignored
        assert abs(led.modeled_equity - 100_000.0) < 1e-6

    def test_first_cycle_swap_zero(self):
        """swap_usd=0 on first cycle; only cost deducted if any."""
        led = _make_ledger()
        led.seed(100_000.0, "USDJPY", 150.0)
        # First cycle: flat position, no cost, no swap
        result = led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 100_000.0, cycle_id=1)
        # E_m unchanged from seed when all terms are zero
        assert abs(result.modeled_equity - 100_000.0) < 1e-6

    def test_update_without_seed_raises(self):
        led = _make_ledger()
        with pytest.raises(RuntimeError, match="not been seeded"):
            led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 100_000.0)


# ---------------------------------------------------------------------------
# TC6: Negative oracle — OLD non-cumulative formula gives different result
#
# The old formula was: paper_equity_bt_equiv = equity - cost_usd + swap_usd
# (vt.py:799 / carry_fred.py:771).
# Over multiple cycles this drifts because it re-anchors to broker equity
# each cycle rather than running the recurrence.
#
# Scenario: 3 cycles with open position. Broker equity drifts up each cycle
# but the cumulative modeled equity accumulates the price P&L.
# The old formula gives: broker_equity - cost + swap each cycle independently.
# The new formula gives: running E_m that accumulates price moves.
# They will diverge when price moves dominate.
# ---------------------------------------------------------------------------


class TestTC6NegativeOracleOldFormula:
    """TC6: Cumulative ledger differs from old non-cumulative formula."""

    def test_old_formula_differs_after_multiple_cycles(self):
        led = _make_ledger()
        broker_equity_0 = 100_000.0
        led.seed(broker_equity_0, "USDJPY", 150.0)

        # Simulate 3 cycles where price drops 1 pip each cycle
        # but broker equity rises because the broker re-prices live
        mids = [150.5, 150.2, 149.8]
        broker_equities = [100_030.0, 100_025.0, 100_010.0]
        held_nom = 10_000.0
        cost_each = 3.0
        swap_each = 1.5

        for i, (mid, broker_eq) in enumerate(zip(mids, broker_equities)):
            led.update("USDJPY", mid, held_nom, cost_each, swap_each, broker_eq, cycle_id=i + 1)

        final_em = led.modeled_equity

        # Old formula (non-cumulative) for last cycle:
        old_formula_last_cycle = broker_equities[-1] - cost_each + swap_each

        # They should differ (old formula re-anchors to broker, new accumulates)
        assert abs(final_em - old_formula_last_cycle) > 1.0, (
            f"TC6: cumulative E_m ({final_em:.4f}) should differ from old formula "
            f"({old_formula_last_cycle:.4f}) by more than 1 USD after 3 cycles"
        )


# ---------------------------------------------------------------------------
# TC7: Peak persistence across simulated restart
# ---------------------------------------------------------------------------


class TestTC7PeakPersistence:
    """TC7: Peak survives process restart; restart mid-drawdown does NOT erase peak."""

    def test_peak_survives_restart(self, tmp_path):
        data_dir = str(tmp_path)
        led1 = _make_ledger(data_dir=data_dir)
        led1.seed(100_000.0, "USDJPY", 150.0)
        # Establish a peak of 102000
        led1.update("USDJPY", 152.0, 10_000.0, 0.0, 0.0, 102_000.0, cycle_id=1)
        assert led1.peak_broker_equity == 102_000.0

        # Simulate restart: create a new ledger that loads state from same dir
        led2 = _make_ledger(data_dir=data_dir)
        # After load, state should be preserved
        assert led2.modeled_equity is not None
        assert led2.peak_broker_equity == 102_000.0, (
            f"TC7: peak after restart={led2.peak_broker_equity} expected=102000"
        )

    def test_restart_mid_drawdown_does_not_erase_peak(self, tmp_path):
        data_dir = str(tmp_path)
        # Session 1: peak established at 110000, then equity drops to 95000
        led1 = _make_ledger(data_dir=data_dir)
        led1.seed(100_000.0, "USDJPY", 150.0)
        led1.update("USDJPY", 155.0, 10_000.0, 0.0, 0.0, 110_000.0, cycle_id=1)
        led1.update("USDJPY", 145.0, 10_000.0, 0.0, 0.0, 95_000.0, cycle_id=2)
        peak_pre_restart = led1.peak_broker_equity

        # Session 2: restart — new ledger MUST NOT re-anchor peak to 95000
        led2 = _make_ledger(data_dir=data_dir)
        assert abs(led2.peak_broker_equity - peak_pre_restart) < 1e-6, (
            f"TC7 restart: peak={led2.peak_broker_equity} but pre-restart peak was "
            f"{peak_pre_restart}. Restart erased the drawdown context."
        )

        # After restart, first equity update should still show drawdown from 110000 peak
        led2.update("USDJPY", 146.0, 10_000.0, 0.0, 0.0, 96_000.0, cycle_id=3)
        # residual = broker_equity - modeled_equity (close-ish since not real-fill calibrated)
        # Peak should still be ~110000 (not updated because 96000 < 110000)
        assert abs(led2.peak_broker_equity - peak_pre_restart) < 1e-6, (
            "TC7: peak should remain at pre-restart value after one more lower-equity cycle"
        )


# ---------------------------------------------------------------------------
# TC8: Mock cycles excluded from residual and peak
# ---------------------------------------------------------------------------


class TestTC8MockCycleExclusion:
    """TC8: Mock sentinel (100000.0) cycles excluded from peak + residual counting."""

    def test_mock_sentinel_excluded_from_peak(self, tmp_path):
        led = _make_ledger(data_dir=str(tmp_path))
        led.seed(50_000.0, "USDJPY", 150.0)

        # Mock cycle with 100000.0 sentinel — must NOT update peak
        result = led.update(
            pair="USDJPY",
            mid_now=150.0,
            held_units_nom=0.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=100_000.0,  # mock sentinel
            cycle_id=1,
        )
        assert result.is_mock is True
        # Peak must NOT be set to 100000 from mock
        assert led.peak_broker_equity == 0.0, (
            f"TC8: mock sentinel must not update peak; got peak={led.peak_broker_equity}"
        )

    def test_mock_excluded_from_breach_counting(self, tmp_path):
        """Breaches on mock cycles do NOT increment consecutive_breaches."""
        led = _make_ledger(
            data_dir=str(tmp_path),
            tol_abs=1.0,  # tiny tolerance so any real deviation breaches
            enforce=True,
        )
        led.seed(50_000.0, "USDJPY", 150.0)

        # Run several mock cycles — even with huge residuals, consecutive must stay 0
        for i in range(5):
            led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 100_000.0, cycle_id=i + 1)

        assert led.consecutive_breaches == 0, (
            f"TC8: mock cycles must not increment consecutive_breaches; "
            f"got {led.consecutive_breaches}"
        )

    def test_is_mock_backend_flag(self, tmp_path):
        """is_mock_backend=True forces mock exclusion regardless of equity value."""
        led = _make_ledger(data_dir=str(tmp_path))
        led.seed(100_000.0, "USDJPY", 150.0)
        result = led.update(
            "USDJPY",
            150.0,
            0.0,
            0.0,
            0.0,
            broker_equity=200_000.0,  # NOT the sentinel, but backend says mock
            is_mock_backend=True,
            cycle_id=1,
        )
        assert result.is_mock is True
        assert led.peak_broker_equity == 0.0, "TC8: is_mock_backend=True must exclude peak update"


# ---------------------------------------------------------------------------
# TC9: Alarm-only mode — does not halt
# ---------------------------------------------------------------------------


class TestTC9AlarmOnlyMode:
    """TC9: enforce=False (default) never triggers HALT-NEW-DISPATCH."""

    def test_alarm_only_no_halt_after_n_breaches(self, tmp_path):
        """N consecutive breaches in alarm-only mode → NO halt."""
        alarm_calls = []
        led = _make_ledger(
            data_dir=str(tmp_path),
            tol_abs=1.0,  # tiny so first real cycle breaches
            tol_rel=0.0,
            enforce=False,  # alarm-only
            consecutive_n=3,
            ntfy_fn=lambda title, msg, pri: alarm_calls.append((title, msg, pri)),
        )
        led.seed(100_000.0, "USDJPY", 150.0)

        # 5 consecutive breaching cycles
        for i in range(5):
            led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 100_500.0, cycle_id=i + 1)
            assert not led.should_halt_new_dispatch(), (
                f"TC9: alarm-only cycle {i + 1} should not halt; "
                f"consecutive={led.consecutive_breaches}"
            )
        # Alarms should have fired
        assert len(alarm_calls) > 0, "TC9: alarm-only mode should still emit ntfy on breach"

    def test_alarm_only_real_cycle_count_advances(self, tmp_path):
        led = _make_ledger(data_dir=str(tmp_path), enforce=False)
        led.seed(98_000.0, "USDJPY", 150.0)  # non-sentinel seed
        for i in range(3):
            # Use non-sentinel equity (100_000.0 is the mock sentinel → excluded)
            led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 98_000.0 + i, cycle_id=i + 1)
        assert led.real_cycle_count == 3


# ---------------------------------------------------------------------------
# TC10: Enforce-mode ladder — halts-new-dispatch at N consecutive, never flattens
# ---------------------------------------------------------------------------


class TestTC10EnforceModeHaltLadder:
    """TC10: enforce=True activates ladder; at N consecutive → should_halt_new_dispatch()."""

    def test_n_consecutive_triggers_halt(self, tmp_path):
        led = _make_ledger(
            data_dir=str(tmp_path),
            tol_abs=1.0,  # tiny tolerance
            tol_rel=0.0,
            enforce=True,
            consecutive_n=3,
        )
        led.seed(100_000.0, "USDJPY", 150.0)

        # After 2 breaches: should NOT halt yet
        for i in range(2):
            led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 100_500.0, cycle_id=i + 1)
        assert not led.should_halt_new_dispatch(), (
            f"TC10: 2 consecutive breaches should not halt (need 3); "
            f"consecutive={led.consecutive_breaches}"
        )

        # 3rd breach: NOW should halt
        led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 100_500.0, cycle_id=3)
        assert led.should_halt_new_dispatch(), (
            f"TC10: 3 consecutive breaches should trigger halt; "
            f"consecutive={led.consecutive_breaches}"
        )

    def test_double_breach_triggers_halt(self, tmp_path):
        """Single-cycle 2× tolerance → ReconResult.double_breach is True."""
        led = _make_ledger(
            data_dir=str(tmp_path),
            tol_abs=100.0,
            tol_rel=0.0,
            enforce=True,
        )
        led.seed(100_000.0, "USDJPY", 150.0)
        # broker_equity = 100_300 → modeled = 100_000 → residual = 300 > 2×100
        result = led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 100_300.0, cycle_id=1)
        assert result.double_breach is True, (
            f"TC10: |residual|={abs(result.residual)} should exceed 2×tolerance={2 * result.tolerance}"
        )

    def test_consecutive_resets_after_clean_cycle(self, tmp_path):
        led = _make_ledger(
            data_dir=str(tmp_path),
            tol_abs=1.0,
            tol_rel=0.0,
            enforce=True,
            consecutive_n=3,
        )
        # Use non-sentinel seed so all cycles are treated as real
        led.seed(98_000.0, "USDJPY", 150.0)
        # 2 breaching cycles: broker_equity=98_500 → residual=500 >> tol_abs=1.0
        for i in range(2):
            led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 98_500.0, cycle_id=i + 1)
        assert led.consecutive_breaches == 2

        # Clean cycle — residual within tolerance (broker matches modeled exactly)
        # Use modeled_equity as broker_equity so residual = 0 (non-sentinel value)
        em = led.modeled_equity
        assert em != 100_000.0, "oracle: modeled_equity must not equal mock sentinel"
        led.update(
            "USDJPY",
            150.0,
            0.0,
            0.0,
            0.0,
            em,  # exact match → residual = 0
            cycle_id=3,
        )
        assert led.consecutive_breaches == 0, (
            "TC10: clean cycle should reset consecutive_breaches to 0"
        )

    def test_enforce_mode_never_calls_kill_switch(self, tmp_path):
        """Even in enforce mode, halt ladder must not trigger kill switch or flatten."""
        # This is a design invariant: ModeledEquityLedger has no kill_switch reference.
        led = _make_ledger(
            data_dir=str(tmp_path),
            tol_abs=1.0,
            tol_rel=0.0,  # pure abs tolerance: max(1.0, 0.0*peak) = 1.0
            enforce=True,
            consecutive_n=1,
        )
        # Use non-sentinel seed; broker_equity also non-sentinel so residual is real
        led.seed(98_000.0, "USDJPY", 150.0)
        led.update("USDJPY", 150.0, 0.0, 0.0, 0.0, 98_500.0, cycle_id=1)
        # residual = 98_500 - 98_000 = 500 >> tol_abs=1.0 → breach
        # should_halt_new_dispatch returns True but we never called kill/flatten
        # Verify the ledger has no kill_switch attribute at all
        assert not hasattr(led, "kill_switch"), (
            "TC10: ModeledEquityLedger must not hold a kill_switch reference"
        )
        assert not hasattr(led, "flatten_all"), (
            "TC10: ModeledEquityLedger must not have flatten_all method"
        )
        assert led.should_halt_new_dispatch() is True


# ---------------------------------------------------------------------------
# TC11: ledger_from_config factory
# ---------------------------------------------------------------------------


class TestTC11LedgerFromConfig:
    """TC11: ledger_from_config reads tolerances from the config dict."""

    def test_defaults_when_no_config_section(self, tmp_path):
        led = ledger_from_config("test", {})
        assert led.tol_rel == 0.005
        assert led.tol_abs == 500.0
        assert led.enforce is False
        assert led.consecutive_n == 3

    def test_reads_from_paper_cost_reconciliation(self, tmp_path):
        cfg = {
            "paper": {
                "cost_reconciliation": {
                    "tol_rel": 0.01,
                    "tol_abs": 250.0,
                    "reconciliation_enforce": True,
                    "consecutive_breach_halt_n": 5,
                }
            }
        }
        led = ledger_from_config("test", cfg)
        assert led.tol_rel == 0.01
        assert led.tol_abs == 250.0
        assert led.enforce is True
        assert led.consecutive_n == 5


# ---------------------------------------------------------------------------
# TC12: Residual tolerance band
# ---------------------------------------------------------------------------


class TestTC12ResidualTolerance:
    """TC12: Tolerance = max(tol_abs, tol_rel * peak_broker_equity)."""

    def test_tolerance_uses_abs_floor_at_low_peak(self, tmp_path):
        """At small peak, abs floor dominates."""
        led = _make_ledger(data_dir=str(tmp_path), tol_rel=0.005, tol_abs=500.0)
        led.seed(1_000.0, "EURUSD", 1.08)  # small equity
        result = led.update("EURUSD", 1.08, 0.0, 0.0, 0.0, 1_001.0, cycle_id=1)
        # peak_broker_equity = 1001; rel tolerance = 0.005*1001 = 5.005
        # abs floor = 500.0 → max(500, 5.005) = 500.0
        assert abs(result.tolerance - 500.0) < 1e-6, (
            f"TC12: expected tolerance=500.0 (abs floor), got {result.tolerance}"
        )

    def test_tolerance_uses_rel_at_high_equity(self, tmp_path):
        """At large equity, relative tolerance dominates."""
        led = _make_ledger(data_dir=str(tmp_path), tol_rel=0.005, tol_abs=500.0)
        led.seed(1_000_000.0, "EURUSD", 1.08)
        result = led.update("EURUSD", 1.08, 0.0, 0.0, 0.0, 1_000_000.0, cycle_id=1)
        # rel = 0.005 * 1_000_000 = 5000 > 500 abs floor
        expected_tol = 0.005 * 1_000_000.0
        assert abs(result.tolerance - expected_tol) < 1.0, (
            f"TC12: expected relative tolerance={expected_tol}, got {result.tolerance}"
        )


# ---------------------------------------------------------------------------
# TC13: DrawdownContract peak persistence (CRO VETO #5)
# ---------------------------------------------------------------------------


class TestTC13DrawdownPeakPersistence:
    """TC13: DrawdownContract _peak_equity persists across restarts when strategy_id given."""

    def test_peak_loaded_on_init(self, tmp_path):
        from forex_system.risk.drawdown_contract import DrawdownContract
        import unittest.mock as mock

        strategy_id = "test_dd_persist"
        # Pre-populate a peak file in tmp_path
        peak_path = tmp_path / f"dd_peak_{strategy_id}.json"
        peak_path.write_text(
            json.dumps(
                {
                    "strategy_id": strategy_id,
                    "peak_equity": 115_000.0,
                    "saved_at": "2026-01-01T00:00:00+00:00",
                }
            )
        )

        with mock.patch(
            "forex_system.risk.drawdown_contract._peak_state_path",
            side_effect=lambda sid: tmp_path / f"dd_peak_{sid}.json",
        ):
            dc = DrawdownContract(
                halt_threshold=0.10,
                reduce_threshold=0.15,
                full_halt_threshold=0.20,
                strategy_id=strategy_id,
            )
            assert abs(dc._peak_equity - 115_000.0) < 1e-6, (
                f"TC13: peak not loaded from disk; _peak_equity={dc._peak_equity}"
            )

    def test_peak_takes_max_on_restart(self, tmp_path):
        """If current equity > persisted peak, new max is used (not just persisted)."""
        from forex_system.risk.drawdown_contract import DrawdownContract
        import unittest.mock as mock

        strategy_id = "test_dd_max"
        peak_path = tmp_path / f"dd_peak_{strategy_id}.json"
        peak_path.write_text(
            json.dumps(
                {
                    "strategy_id": strategy_id,
                    "peak_equity": 105_000.0,
                    "saved_at": "2026-01-01T00:00:00+00:00",
                }
            )
        )
        with mock.patch(
            "forex_system.risk.drawdown_contract._peak_state_path",
            side_effect=lambda sid: tmp_path / f"dd_peak_{sid}.json",
        ):
            dc = DrawdownContract(
                halt_threshold=0.10,
                reduce_threshold=0.15,
                full_halt_threshold=0.20,
                strategy_id=strategy_id,
            )
            # Loaded persisted peak = 105000
            assert abs(dc._peak_equity - 105_000.0) < 1e-6
            # Now assess with equity > persisted → peak should update to new max
            assessment = dc.assess(110_000.0)
            assert abs(assessment.peak_equity - 110_000.0) < 1e-6, (
                f"TC13: peak should update to max(persisted=105000, current=110000)=110000; "
                f"got {assessment.peak_equity}"
            )

    def test_peak_not_persisted_without_strategy_id(self):
        """Legacy path: no strategy_id → peak stays in-process, no file written."""
        from forex_system.risk.drawdown_contract import DrawdownContract

        dc = DrawdownContract(
            halt_threshold=0.10,
            reduce_threshold=0.15,
            full_halt_threshold=0.20,
            # No strategy_id
        )
        # Use non-sentinel equity (100_000.0 is the mock sentinel → would be excluded)
        dc.assess(105_000.0)
        # No file should be written (we can't easily check file absence globally,
        # but the contract should work exactly as before)
        assert dc._peak_equity == 105_000.0  # in-process peak updated

    def test_mock_sentinel_does_not_update_peak_via_is_mock_kwarg(self):
        """CRO VETO #4: is_mock=True must prevent peak update (caller-asserted).

        DrawdownContract does NOT auto-detect the 100_000.0 sentinel by value
        (it's too common a real equity). Callers must pass is_mock=True explicitly.
        """
        from forex_system.risk.drawdown_contract import (
            DrawdownContract,
            _DD_MOCK_EQUITY_SENTINEL,
        )

        dc = DrawdownContract(halt_threshold=0.10, reduce_threshold=0.15, full_halt_threshold=0.20)
        # Assess with is_mock=True — peak must stay 0
        dc.assess(_DD_MOCK_EQUITY_SENTINEL, is_mock=True)
        assert dc._peak_equity == 0.0, (
            f"TC13: is_mock=True must not update peak; _peak_equity={dc._peak_equity}"
        )

    def test_is_mock_kwarg_excludes_peak_update(self):
        """is_mock=True keyword excludes peak update even for non-sentinel values."""
        from forex_system.risk.drawdown_contract import DrawdownContract

        dc = DrawdownContract(halt_threshold=0.10, reduce_threshold=0.15, full_halt_threshold=0.20)
        dc.assess(150_000.0, is_mock=True)
        assert dc._peak_equity == 0.0, "TC13: is_mock=True must not update _peak_equity"


# ---------------------------------------------------------------------------
# TC14: Gap-3 — mock flag propagated end-to-end from is_mock_cycle predicate
# ---------------------------------------------------------------------------


class TestTC14Gap3MockFlagPropagation:
    """TC14: Gap-3 integration — mock-cycle predicate drives dd_contract and ledger exclusion.

    CRO VETO #4 is only available, not enforced, when the scripts pass is_mock=False
    to dd_contract.assess() and is_mock_backend=False to ledger.update() regardless
    of the actual equity value.  This test proves the canonical predicate path:
      1. ModeledEquityLedger.is_mock_cycle(sentinel) → True
      2. That True value, if passed to dd_contract.assess(is_mock=True), suppresses peak update
      3. That same True value, if passed to ledger.update(is_mock_backend=True), excludes residual

    The integration seam being tested is the predicate chain — the tests above at
    TC8 and TC13 test the individual components; this test proves the chain is wired
    correctly as a composition.
    """

    def test_sentinel_equity_is_detected_as_mock(self):
        """is_mock_cycle(100000.0) returns True — the sentinel IS the predicate."""
        assert ModeledEquityLedger.is_mock_cycle(100_000.0) is True

    def test_non_sentinel_equity_is_not_mock(self):
        """is_mock_cycle returns False for non-sentinel values."""
        assert ModeledEquityLedger.is_mock_cycle(100_001.0) is False
        assert ModeledEquityLedger.is_mock_cycle(99_999.0) is False
        assert ModeledEquityLedger.is_mock_cycle(50_000.0) is False

    def test_mock_cycle_propagated_to_dd_contract_suppresses_peak(self):
        """End-to-end: mock predicate → dd_contract.assess(is_mock=True) → peak unchanged.

        Simulates the script cycle path:
          equity = fetch_account_equity(...)  # returns 100_000.0 (sentinel)
          _cycle_is_mock = ModeledEquityLedger.is_mock_cycle(equity)  # True
          dd_contract.assess(equity, is_mock=_cycle_is_mock)          # is_mock=True
          → peak must NOT be updated to 100_000.0
        """
        from forex_system.risk.drawdown_contract import DrawdownContract

        dc = DrawdownContract(halt_threshold=0.10, reduce_threshold=0.15, full_halt_threshold=0.20)

        sentinel_equity = 100_000.0
        _cycle_is_mock = ModeledEquityLedger.is_mock_cycle(sentinel_equity)
        assert _cycle_is_mock is True  # pre-condition

        dc.assess(sentinel_equity, is_mock=_cycle_is_mock)
        assert dc._peak_equity == 0.0, (
            f"TC14: mock sentinel equity passed with is_mock=True must not update peak; "
            f"_peak_equity={dc._peak_equity}. This is Gap-3 — the is_mock flag must be "
            "PASSED to dd_contract.assess, not just computed and discarded."
        )

    def test_mock_cycle_propagated_to_ledger_excludes_residual(self, tmp_path):
        """End-to-end: mock predicate → ledger.update(is_mock_backend=True) → no peak/breach.

        Simulates the script cycle path:
          equity = 100_000.0  (sentinel)
          _cycle_is_mock = ModeledEquityLedger.is_mock_cycle(equity)  # True
          ledger.update(..., broker_equity=equity, is_mock_backend=_cycle_is_mock)
          → peak_broker_equity must NOT advance; consecutive_breaches must stay 0
        """
        led = _make_ledger(data_dir=str(tmp_path), tol_abs=1.0, enforce=True, consecutive_n=1)
        led.seed(50_000.0, "USDJPY", 150.0)

        sentinel_equity = 100_000.0
        _cycle_is_mock = ModeledEquityLedger.is_mock_cycle(sentinel_equity)
        assert _cycle_is_mock is True

        result = led.update(
            pair="USDJPY",
            mid_now=150.0,
            held_units_nom=0.0,
            cost_usd=0.0,
            swap_usd=0.0,
            broker_equity=sentinel_equity,
            is_mock_backend=_cycle_is_mock,
            cycle_id=1,
        )
        assert result.is_mock is True, "TC14: sentinel with is_mock_backend=True must produce is_mock=True result"
        assert led.peak_broker_equity == 0.0, (
            f"TC14: mock cycle must not advance peak_broker_equity; got {led.peak_broker_equity}"
        )
        assert led.consecutive_breaches == 0, (
            f"TC14: mock cycle must not increment consecutive_breaches; got {led.consecutive_breaches}"
        )

    def test_mock_cycle_does_not_suppress_modeled_equity_update(self, tmp_path):
        """E_m advances even on mock cycles (recurrence runs unconditionally).

        Per spec: 'The ledger is updated unconditionally (E_m advances each cycle).
        However, residual tolerance checking and peak tracking are ONLY applied on
        real-fill cycles.'  So a mock cycle with a cost still deducts from E_m.
        """
        led = _make_ledger(data_dir=str(tmp_path))
        led.seed(50_000.0, "USDJPY", 150.0)

        sentinel_equity = 100_000.0
        _cycle_is_mock = ModeledEquityLedger.is_mock_cycle(sentinel_equity)

        result = led.update(
            pair="USDJPY",
            mid_now=150.0,
            held_units_nom=0.0,
            cost_usd=10.0,  # cost still applied to E_m even on mock cycle
            swap_usd=0.0,
            broker_equity=sentinel_equity,
            is_mock_backend=_cycle_is_mock,
            cycle_id=1,
        )
        # E_m must have decreased by 10.0 (cost deducted)
        assert abs(result.modeled_equity - (50_000.0 - 10.0)) < 1e-6, (
            f"TC14: E_m must advance even on mock cycles; "
            f"expected={50_000.0 - 10.0}, got={result.modeled_equity}"
        )
