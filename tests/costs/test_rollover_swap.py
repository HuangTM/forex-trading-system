"""Tests for rollover-aware swap cost model.  CRO CM-2.

Verifies:
  - count_rollover_crossings: correct counting of 22:00 UTC boundaries, triple Wed
  - RolloverAwareRealisticCostModel.holding_cost: zero for intraday, correct for cross-rollover
  - rollover_cost_for_bar: fires only on 21:00 UTC bars, 3× on Wednesday
  - Backward-compatibility: no-timestamp path falls back to pro-rata (daily-bar path)
  - No-lookahead: cost charged at BAR CLOSE time (21:00 UTC bar), not prospectively
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pandas as pd
import pytest

from forex_system.core.types import Direction, PairInfo
from forex_system.costs.model import (
    RolloverAwareRealisticCostModel,
    _next_rollover_at_or_after,
    count_rollover_crossings,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_PAIR_CFG = {
    "EURUSD": PairInfo(
        symbol="EURUSD",
        pip_value=0.0001,
        spread_pips=0.5,
        slippage_pips=0.1,
        commission_pips=0.1,
        swap_long_pips_per_day=-1.0,   # long = cost 1 pip/day
        swap_short_pips_per_day=0.5,   # short = income 0.5 pip/day
    )
}

_MODEL = RolloverAwareRealisticCostModel(pair_configs=_PAIR_CFG)

# Helpers
def _ts(dt_str: str) -> pd.Timestamp:
    return pd.Timestamp(dt_str, tz="UTC")


def _dt(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests: count_rollover_crossings
# ---------------------------------------------------------------------------


class TestCountRolloverCrossings:
    def test_no_crossing_within_session(self):
        """Intraday: opened 10:00 UTC, closed 15:00 UTC — no rollover."""
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-02 10:00:00"),
            _ts("2023-01-02 15:00:00"),
        )
        assert n_single == 0
        assert n_triple == 0

    def test_one_standard_rollover(self):
        """Hold from Mon 10:00 UTC → Tue 10:00 UTC: crosses Mon 22:00 UTC (1 rollover)."""
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-02 10:00:00"),  # Monday
            _ts("2023-01-03 10:00:00"),  # Tuesday
        )
        assert n_single == 1
        assert n_triple == 0

    def test_wednesday_rollover_is_triple(self):
        """Hold across Wed 22:00 UTC → triple charge."""
        # Wed Jan 04 10:00 → Thu Jan 05 10:00 crosses Wed 22:00
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-04 10:00:00"),  # Wednesday
            _ts("2023-01-05 10:00:00"),  # Thursday
        )
        assert n_single == 0
        assert n_triple == 1

    def test_entry_at_rollover_not_counted(self):
        """Position opened at exactly 22:00 UTC does NOT count that rollover."""
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-02 22:00:00"),  # Monday exactly at rollover
            _ts("2023-01-03 10:00:00"),  # Tue 10:00 — no more rollovers
        )
        assert n_single == 0
        assert n_triple == 0

    def test_exit_at_rollover_counted(self):
        """Position closed at exactly 22:00 UTC counts that rollover."""
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-02 10:00:00"),  # Monday
            _ts("2023-01-02 22:00:00"),  # Monday exactly at rollover
        )
        assert n_single == 1
        assert n_triple == 0

    def test_three_days_including_wednesday(self):
        """Mon 10:00 → Thu 10:00: Mon 22:00 (1×), Tue 22:00 (1×), Wed 22:00 (3×)."""
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-02 10:00:00"),  # Monday
            _ts("2023-01-05 10:00:00"),  # Thursday
        )
        assert n_single == 2   # Mon + Tue rollovers
        assert n_triple == 1   # Wed rollover

    def test_zero_duration_no_crossings(self):
        """Entry == exit → no crossings."""
        ts = _ts("2023-01-02 22:00:00")
        n_single, n_triple = count_rollover_crossings(ts, ts)
        assert n_single == 0
        assert n_triple == 0

    def test_reverse_order_no_crossings(self):
        """exit < entry → no crossings (silent no-op)."""
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-02 22:00:00"),
            _ts("2023-01-02 10:00:00"),
        )
        assert n_single == 0
        assert n_triple == 0

    def test_five_days_excluding_fri_22(self):
        """Mon 10:00 → Sat 10:00: Mon(1), Tue(1), Wed(3×), Thu(1); Fri 22:00 skipped (closed).

        PREVIOUSLY WRONG: old code was named test_five_days_four_single_one_triple and
        asserted n_single==4, counting Fri 22:00 UTC as a rollover boundary.
        CORRECT: Fri 22:00 UTC is market-closed (quality_gate_1h._WEEKEND_CLOSED_DAY_HOUR
        includes Fri hours 21-23) — it must NOT count as a rollover boundary.
        """
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-02 10:00:00"),  # Monday
            _ts("2023-01-07 10:00:00"),  # Saturday 10:00 (after Fri 22:00)
        )
        # Mon + Tue + Thu = 3 single rollovers; Wed = 1 triple; Fri 22:00 SKIPPED
        assert n_single == 3
        assert n_triple == 1


# ---------------------------------------------------------------------------
# Tests: RolloverAwareRealisticCostModel.holding_cost
# ---------------------------------------------------------------------------


class TestRolloverAwareHoldingCost:
    def test_intraday_no_rollover_crossing_zero_swap(self):
        """Long held 10:00 → 15:00 UTC (no rollover) → zero swap cost."""
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.LONG, days=0,
            entry_ts=_ts("2023-01-02 10:00:00"),
            exit_ts=_ts("2023-01-02 15:00:00"),
        )
        assert cost == 0.0, f"Expected 0.0, got {cost}"

    def test_one_rollover_charges_one_day_swap(self):
        """Long held across Mon 22:00 UTC → exactly 1 day's swap cost."""
        # swap_long_pips_per_day = -1.0 → cost = -(-1.0) × 1 = 1.0 pips
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.LONG, days=0,
            entry_ts=_ts("2023-01-02 10:00:00"),
            exit_ts=_ts("2023-01-03 10:00:00"),
        )
        assert cost == pytest.approx(1.0), f"Expected 1.0 pip cost, got {cost}"

    def test_wednesday_rollover_charges_triple(self):
        """Long held across Wed 22:00 UTC → 3× daily swap charge."""
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.LONG, days=0,
            entry_ts=_ts("2023-01-04 10:00:00"),  # Wednesday
            exit_ts=_ts("2023-01-05 10:00:00"),  # Thursday
        )
        # 3× 1 day's swap = 3.0 pips cost
        assert cost == pytest.approx(3.0), f"Expected 3.0 pip cost, got {cost}"

    def test_short_position_income_becomes_cost_when_negative_swap(self):
        """Short with positive daily_swap (income) → negative cost (income for holder)."""
        # swap_short_pips_per_day = +0.5 → income → holding_cost returns -0.5 (negative = income)
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.SHORT, days=0,
            entry_ts=_ts("2023-01-02 10:00:00"),
            exit_ts=_ts("2023-01-03 10:00:00"),
        )
        assert cost == pytest.approx(-0.5), f"Expected -0.5 (income), got {cost}"

    def test_flat_position_zero_cost(self):
        """Direction.FLAT → always zero."""
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.FLAT, days=0,
            entry_ts=_ts("2023-01-02 10:00:00"),
            exit_ts=_ts("2023-01-03 10:00:00"),
        )
        assert cost == 0.0

    def test_backward_compat_no_timestamps_falls_back_to_prorata(self):
        """No timestamps → fall back to pro-rata (daily-bar path, backward-compatible)."""
        cost = _MODEL.holding_cost("EURUSD", Direction.LONG, days=2.0)
        # Pro-rata: -(-1.0) × 2.0 = 2.0
        assert cost == pytest.approx(2.0)

    def test_five_day_hold_mon_to_sat(self):
        """Mon 10:00 → Sat 10:00: 3 single (Mon,Tue,Thu) + 1 triple (Wed) = 6 days charge.

        PREVIOUSLY WRONG: old assertion was cost==7.0, counting Fri 22:00 as a rollover
        (n_single=4).  CORRECT: Fri 22:00 UTC is market-closed; n_single=3, n_triple=1,
        total charge = 3×1 + 1×3 = 6 days.
        """
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.LONG, days=0,
            entry_ts=_ts("2023-01-02 10:00:00"),
            exit_ts=_ts("2023-01-07 10:00:00"),
        )
        # Total charge = 3 × 1 + 1 × 3 = 6 days
        assert cost == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# Tests: rollover_cost_for_bar (per-bar accrual pattern)
# ---------------------------------------------------------------------------


class TestRolloverCostForBar:
    def test_non_rollover_bar_zero_cost(self):
        """Bar at 10:00 UTC (not rollover hour) → zero swap."""
        ts = _ts("2023-01-02 10:00:00")  # Monday 10:00
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        assert cost == 0.0

    def test_rollover_bar_21h_utc_charges_swap(self):
        """Bar at 21:00 UTC → closes at 22:00 = rollover → charges swap."""
        ts = _ts("2023-01-02 21:00:00")  # Monday 21:00 UTC (closes at 22:00)
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        # 1× daily swap: -(-1.0) × 1 = 1.0 pip cost
        assert cost == pytest.approx(1.0)

    def test_wednesday_rollover_bar_triple_charge(self):
        """Bar at Wednesday 21:00 UTC → 3× daily swap."""
        # 2023-01-04 is a Wednesday
        ts = _ts("2023-01-04 21:00:00")
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        # 3× daily swap: -(-1.0) × 3 = 3.0 pip cost
        assert cost == pytest.approx(3.0)

    def test_non_wednesday_non_21h_zero(self):
        """Bar at 22:00 UTC (not 21:00) → zero (rollover already past)."""
        ts = _ts("2023-01-02 22:00:00")  # Monday 22:00 — the rollover itself is at start of this bar
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        # 22:00 bar opens AFTER the rollover; cost fires on the 21:00 bar
        assert cost == 0.0

    def test_short_rollover_bar(self):
        """Short at rollover bar: income (negative cost)."""
        ts = _ts("2023-01-02 21:00:00")
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.SHORT, ts)
        # swap_short_pips_per_day = +0.5 → income → cost = -(+0.5) × 1 = -0.5
        assert cost == pytest.approx(-0.5)

    def test_flat_rollover_bar_zero(self):
        """Flat position at rollover bar → zero."""
        ts = _ts("2023-01-02 21:00:00")
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.FLAT, ts)
        assert cost == 0.0

    def test_no_lookahead_cost_at_bar_close_time(self):
        """No-lookahead: cost fires at bar_ts 21:00 (bar CLOSES at 22:00), not before.

        Invariant: cost must be 0 for any bar_ts.hour != 21.
        Specifically, the 20:00 UTC bar must carry zero cost even though it is one
        hour before rollover — it does NOT lookahead to the next bar's crossing.
        """
        ts_before = _ts("2023-01-02 20:00:00")  # one hour before rollover
        cost_before = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts_before)
        ts_at = _ts("2023-01-02 21:00:00")        # bar that closes at 22:00
        cost_at = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts_at)
        assert cost_before == 0.0, f"No-lookahead violated: cost at 20:00 = {cost_before}"
        assert cost_at > 0.0, f"Rollover cost at 21:00 must be non-zero, got {cost_at}"


# ---------------------------------------------------------------------------
# Tests: _next_rollover_at_or_after helper
# ---------------------------------------------------------------------------


class TestNextRolloverAtOrAfter:
    def test_same_day_after_22h(self):
        """If dt is after 22:00, next rollover is the NEXT day at 22:00."""
        dt = _dt("2023-01-02 23:00:00")
        nxt = _next_rollover_at_or_after(dt, strict_after=False)
        assert nxt == _dt("2023-01-03 22:00:00")

    def test_same_day_before_22h(self):
        """If dt is before 22:00, next rollover is TODAY at 22:00."""
        dt = _dt("2023-01-02 10:00:00")
        nxt = _next_rollover_at_or_after(dt, strict_after=False)
        assert nxt == _dt("2023-01-02 22:00:00")

    def test_strict_after_at_exactly_22h(self):
        """strict_after=True: dt exactly at 22:00 → next rollover is next day."""
        dt = _dt("2023-01-02 22:00:00")
        nxt = _next_rollover_at_or_after(dt, strict_after=True)
        assert nxt == _dt("2023-01-03 22:00:00")


# ---------------------------------------------------------------------------
# Tests: weekend-spanning holds (C-2 additions — must FAIL old code, PASS fix)
# ---------------------------------------------------------------------------


class TestWeekendSpanningRollovers:
    """New tests added in fix-round-1 (C-2).

    These tests exercise weekend-spanning holds that PREVIOUSLY returned wrong
    counts (the old code counted Fri/Sat/Sun 22:00 as rollover boundaries).
    They must FAIL against the pre-fix code and PASS after the fix.

    Canonical case from Principal Reviewer: Fri 2023-01-06 10:00 → Mon 2023-01-09 10:00.
    Old result: (3, 0)  — billed Fri 22:00 + Sat 22:00 + Sun 22:00 erroneously.
    Correct:    (0, 0)  — no rollovers; no Wed in this span; Fri/Sat/Sun skipped.
    """

    def test_fri_to_mon_no_rollovers(self):
        """Fri 10:00 → Mon 10:00: NO rollover crossings.

        The 3 candidates (Fri 22:00, Sat 22:00, Sun 22:00) are ALL market-closed
        and must be skipped.  The Wed triple pre-pay happened before entry (prior
        Wed) so is not in scope.  Correct result = (0, 0).
        """
        # 2023-01-06 = Friday, 2023-01-09 = Monday
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-06 10:00:00"),  # Friday
            _ts("2023-01-09 10:00:00"),  # Monday
        )
        assert n_single == 0, f"Expected 0 single rollovers, got {n_single}"
        assert n_triple == 0, f"Expected 0 triple rollovers, got {n_triple}"

    def test_fri_to_mon_holding_cost_zero(self):
        """holding_cost for a Fri → Mon hold (no Wed in span) = 0.0 pips."""
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.LONG, days=0,
            entry_ts=_ts("2023-01-06 10:00:00"),  # Friday
            exit_ts=_ts("2023-01-09 10:00:00"),   # Monday
        )
        assert cost == pytest.approx(0.0), f"Expected 0.0 pip cost, got {cost}"

    def test_wed_spanning_with_weekend_charges_only_wed(self):
        """Wed 10:00 → Mon 10:00: only Wed 22:00 counts (1 triple); Fri/Sat/Sun skipped.

        The Wed triple pre-pays the weekend; no additional Fri/Sat/Sun charge.
        """
        # 2023-01-04 = Wednesday, 2023-01-09 = Monday
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-04 10:00:00"),  # Wednesday
            _ts("2023-01-09 10:00:00"),  # Monday
        )
        # Wed 22:00 (triple) + Thu 22:00 (single); Fri/Sat/Sun skipped
        assert n_single == 1, f"Expected 1 single (Thu), got {n_single}"
        assert n_triple == 1, f"Expected 1 triple (Wed), got {n_triple}"

    def test_wed_spanning_with_weekend_holding_cost(self):
        """Wed 10:00 → Mon 10:00: charge = Wed triple (3) + Thu single (1) = 4 days."""
        cost = _MODEL.holding_cost(
            "EURUSD", Direction.LONG, days=0,
            entry_ts=_ts("2023-01-04 10:00:00"),  # Wednesday
            exit_ts=_ts("2023-01-09 10:00:00"),   # Monday
        )
        # 3× (Wed) + 1× (Thu) = 4 days swap; long swap = -(-1.0) × 4 = 4.0 pips
        assert cost == pytest.approx(4.0), f"Expected 4.0 pip cost, got {cost}"

    def test_sat_rollover_bar_zero(self):
        """rollover_cost_for_bar: Sat 21:00 UTC bar must return 0.0 (market closed)."""
        # 2023-01-07 = Saturday
        ts = _ts("2023-01-07 21:00:00")
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        assert cost == 0.0, f"Sat 21:00 bar must be 0.0 (market closed), got {cost}"

    def test_sun_rollover_bar_zero(self):
        """rollover_cost_for_bar: Sun 21:00 UTC bar must return 0.0 (market closed / open boundary)."""
        # 2023-01-08 = Sunday
        ts = _ts("2023-01-08 21:00:00")
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        assert cost == 0.0, f"Sun 21:00 bar must be 0.0 (not a financing boundary), got {cost}"

    def test_fri_rollover_bar_zero(self):
        """rollover_cost_for_bar: Fri 21:00 UTC bar must return 0.0 (closes at Fri 22:00 = closed)."""
        # 2023-01-06 = Friday
        ts = _ts("2023-01-06 21:00:00")
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        assert cost == 0.0, f"Fri 21:00 bar must be 0.0 (Fri 22:00 is market-closed), got {cost}"

    def test_thu_rollover_bar_nonzero(self):
        """rollover_cost_for_bar: Thu 21:00 UTC (day before Fri) still charges 1×."""
        # 2023-01-05 = Thursday
        ts = _ts("2023-01-05 21:00:00")
        cost = _MODEL.rollover_cost_for_bar("EURUSD", Direction.LONG, ts)
        assert cost == pytest.approx(1.0), f"Thu 21:00 bar must charge 1×, got {cost}"

    def test_sat_crossing_not_counted(self):
        """Sat 22:00 UTC is not a rollover: hold spanning it accrues nothing for that boundary."""
        n_single, n_triple = count_rollover_crossings(
            _ts("2023-01-07 10:00:00"),  # Saturday
            _ts("2023-01-07 23:00:00"),  # Saturday — after Sat 22:00
        )
        assert n_single == 0, f"Sat 22:00 must not count, got {n_single}"
        assert n_triple == 0
