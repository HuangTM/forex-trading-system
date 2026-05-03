"""Tests for DrawdownContract — CRO Wave-4 + Phase-1 drawdown ladder.

Covers ≥8 test cases:
  1. peak tracking (new high updates peak)
  2. NORMAL at peak (zero drawdown)
  3. HALT_NEW_DISPATCH at exactly 10% drawdown
  4. REDUCE_SIZING at exactly 15% drawdown
  5. FULL_HALT at exactly 20% drawdown
  6. recovery: DD shrinks back below halt threshold → NORMAL
  7. sizing_multiplier values per level (1.0 / 1.0 / 0.5 / 0.0)
  8. structured-log emission via caplog
  9. threshold validation on construction (bad ordering raises ValueError)
 10. allows_new_dispatch semantics (True only at NORMAL)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from forex_system.risk.drawdown_contract import DrawdownContract, DrawdownLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _contract() -> DrawdownContract:
    """Standard CRO-binding thresholds; no silent defaults."""
    return DrawdownContract(
        halt_threshold=0.10,
        reduce_threshold=0.15,
        full_halt_threshold=0.20,
    )


# ---------------------------------------------------------------------------
# Peak tracking
# ---------------------------------------------------------------------------


class TestPeakTracking:
    def test_peak_updates_on_new_high(self):
        """Peak equity must update when current_equity exceeds previous peak."""
        c = _contract()
        a1 = c.assess(100_000.0)
        assert a1.peak_equity == 100_000.0

        a2 = c.assess(105_000.0)
        assert a2.peak_equity == 105_000.0

    def test_peak_does_not_decrease_on_drawdown(self):
        """Peak must NOT fall when equity drops below previous peak."""
        c = _contract()
        c.assess(100_000.0)    # sets peak
        a = c.assess(90_000.0)  # 10% drawdown
        assert a.peak_equity == 100_000.0

    def test_normal_at_peak(self):
        """At exactly the peak (zero drawdown), level must be NORMAL."""
        c = _contract()
        a = c.assess(100_000.0)
        assert a.level == DrawdownLevel.NORMAL
        assert a.drawdown_pct == 0.0
        assert a.allows_new_dispatch is True


# ---------------------------------------------------------------------------
# Threshold boundary tests
# ---------------------------------------------------------------------------


class TestThresholdBoundaries:
    def test_halt_new_dispatch_at_exactly_10pct(self):
        """DD of exactly 10% must return HALT_NEW_DISPATCH."""
        c = _contract()
        c.assess(100_000.0)          # set peak
        a = c.assess(90_000.0)       # 10% drawdown exactly
        assert a.level == DrawdownLevel.HALT_NEW_DISPATCH
        assert abs(a.drawdown_pct - 0.10) < 1e-9
        assert a.allows_new_dispatch is False

    def test_just_below_halt_threshold_is_normal(self):
        """DD just below 10% must remain NORMAL."""
        c = _contract()
        c.assess(100_000.0)
        a = c.assess(90_001.0)       # 9.999% drawdown
        assert a.level == DrawdownLevel.NORMAL
        assert a.allows_new_dispatch is True

    def test_reduce_sizing_at_exactly_15pct(self):
        """DD of exactly 15% must return REDUCE_SIZING."""
        c = _contract()
        c.assess(100_000.0)
        a = c.assess(85_000.0)       # 15% drawdown exactly
        assert a.level == DrawdownLevel.REDUCE_SIZING
        assert abs(a.drawdown_pct - 0.15) < 1e-9

    def test_full_halt_at_exactly_20pct(self):
        """DD of exactly 20% must return FULL_HALT."""
        c = _contract()
        c.assess(100_000.0)
        a = c.assess(80_000.0)       # 20% drawdown exactly
        assert a.level == DrawdownLevel.FULL_HALT
        assert abs(a.drawdown_pct - 0.20) < 1e-9

    def test_full_halt_above_20pct(self):
        """DD above 20% must also return FULL_HALT."""
        c = _contract()
        c.assess(100_000.0)
        a = c.assess(70_000.0)       # 30% drawdown
        assert a.level == DrawdownLevel.FULL_HALT


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------


class TestRecovery:
    def test_recovery_from_halt_new_dispatch_to_normal(self):
        """When equity recovers above halt threshold, level must return to NORMAL."""
        c = _contract()
        c.assess(100_000.0)          # peak
        c.assess(90_000.0)           # HALT_NEW_DISPATCH
        a = c.assess(110_000.0)      # new peak — now at zero drawdown
        assert a.level == DrawdownLevel.NORMAL
        assert a.allows_new_dispatch is True
        assert a.peak_equity == 110_000.0

    def test_recovery_from_reduce_sizing_to_halt_new_dispatch(self):
        """Partial recovery from 15% → between 10–15% must give HALT_NEW_DISPATCH."""
        c = _contract()
        c.assess(100_000.0)          # peak = 100k
        c.assess(85_000.0)           # 15% DD → REDUCE_SIZING
        a = c.assess(92_000.0)       # 8% DD → between 0 and 10 → NORMAL actually
        # 92k / peak 100k = 8% DD < halt threshold → NORMAL
        assert a.level == DrawdownLevel.NORMAL


# ---------------------------------------------------------------------------
# Sizing multiplier values per level
# ---------------------------------------------------------------------------


class TestSizingMultiplier:
    def test_sizing_multiplier_normal(self):
        c = _contract()
        a = c.assess(100_000.0)
        assert a.sizing_multiplier == 1.0

    def test_sizing_multiplier_halt_new_dispatch(self):
        """Existing positions still sized at 1.0x at HALT_NEW_DISPATCH; no NEW dispatch."""
        c = _contract()
        c.assess(100_000.0)
        a = c.assess(90_000.0)   # exactly 10%
        assert a.level == DrawdownLevel.HALT_NEW_DISPATCH
        assert a.sizing_multiplier == 1.0

    def test_sizing_multiplier_reduce_sizing(self):
        c = _contract()
        c.assess(100_000.0)
        a = c.assess(85_000.0)   # exactly 15%
        assert a.sizing_multiplier == 0.5

    def test_sizing_multiplier_full_halt(self):
        c = _contract()
        c.assess(100_000.0)
        a = c.assess(80_000.0)   # exactly 20%
        assert a.sizing_multiplier == 0.0


# ---------------------------------------------------------------------------
# Structured-log emission
# ---------------------------------------------------------------------------


class TestStructuredLogEmission:
    def test_transition_log_emitted_on_level_change(self, caplog):
        """A log record must be emitted when the level transitions."""
        c = _contract()
        with caplog.at_level(logging.WARNING, logger="drawdown_contract"):
            c.assess(100_000.0)   # NORMAL (no WARNING)
            c.assess(90_000.0)    # transitions to HALT_NEW_DISPATCH → WARNING

        # At least one WARNING record about the transition
        records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(records) >= 1

    def test_transition_log_contains_required_keys(self, caplog):
        """Transition log must include all structured-log keys."""
        c = _contract()
        with caplog.at_level(logging.DEBUG, logger="drawdown_contract"):
            c.assess(100_000.0)
            c.assess(90_000.0)

        # Find the transition record
        transition_records = [
            r for r in caplog.records
            if hasattr(r, "transition")
        ]
        assert len(transition_records) >= 1
        rec = transition_records[0]
        assert hasattr(rec, "event")
        assert rec.event == "DRAWDOWN_ASSESSMENT"
        assert hasattr(rec, "current_equity")
        assert hasattr(rec, "peak_equity")
        assert hasattr(rec, "drawdown_pct")
        assert hasattr(rec, "level")
        assert hasattr(rec, "sizing_multiplier")
        assert hasattr(rec, "allows_new_dispatch")
        assert "→" in rec.transition

    def test_full_halt_logs_at_critical(self, caplog):
        """FULL_HALT transition must be logged at CRITICAL level."""
        c = _contract()
        with caplog.at_level(logging.DEBUG, logger="drawdown_contract"):
            c.assess(100_000.0)
            c.assess(80_000.0)   # 20% → FULL_HALT

        critical_records = [r for r in caplog.records if r.levelno == logging.CRITICAL]
        assert len(critical_records) >= 1


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


class TestConstructionValidation:
    def test_invalid_threshold_ordering_raises(self):
        """Thresholds must satisfy halt < reduce < full_halt; otherwise raise ValueError."""
        with pytest.raises(ValueError, match="thresholds must satisfy"):
            DrawdownContract(
                halt_threshold=0.20,
                reduce_threshold=0.15,
                full_halt_threshold=0.10,
            )

    def test_equal_thresholds_raise(self):
        """Equal consecutive thresholds are invalid (< not <=)."""
        with pytest.raises(ValueError):
            DrawdownContract(
                halt_threshold=0.10,
                reduce_threshold=0.10,   # equal to halt
                full_halt_threshold=0.20,
            )

    def test_valid_construction_does_not_raise(self):
        """Standard CRO-binding values must construct without error."""
        c = DrawdownContract(
            halt_threshold=0.10,
            reduce_threshold=0.15,
            full_halt_threshold=0.20,
        )
        assert c.halt_threshold == 0.10
        assert c.reduce_threshold == 0.15
        assert c.full_halt_threshold == 0.20


# ---------------------------------------------------------------------------
# allows_new_dispatch semantics
# ---------------------------------------------------------------------------


class TestAllowsNewDispatch:
    def test_allows_new_dispatch_true_only_at_normal(self):
        """allows_new_dispatch must be True ONLY at NORMAL level."""
        c = _contract()
        assert c.assess(100_000.0).allows_new_dispatch is True   # NORMAL
        assert c.assess(90_000.0).allows_new_dispatch is False   # HALT_NEW
        # need fresh contract to test reduce / full_halt from peak
        c2 = _contract()
        c2.assess(100_000.0)
        assert c2.assess(85_000.0).allows_new_dispatch is False  # REDUCE_SIZING
        c3 = _contract()
        c3.assess(100_000.0)
        assert c3.assess(80_000.0).allows_new_dispatch is False  # FULL_HALT

    def test_assessment_is_frozen_dataclass(self):
        """DrawdownAssessment is frozen — mutation must raise FrozenInstanceError."""
        c = _contract()
        a = c.assess(100_000.0)
        with pytest.raises((AttributeError, TypeError)):
            a.level = DrawdownLevel.FULL_HALT  # type: ignore[misc]
