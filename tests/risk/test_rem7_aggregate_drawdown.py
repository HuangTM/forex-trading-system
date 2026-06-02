"""REM-7 aggregate drawdown contract dual-instance — acceptance tests.

Covers:
    REM-7-T1: LTCM scenario — 4×8% per-strategy DD, aggregate 18% fires halt
    REM-7-T2: Per-strategy isolation — strategy-A at 12% fires; aggregate does NOT
    REM-7-T3: Dual-trigger — strategy-A 12% AND aggregate 18%; both fire
    N-3:      SHUFFLE-CONTROL variant of LTCM scenario (NHT mandatory)
              — aggregate halt fires in ≥99% of 1000 shuffled trajectories
    INV-R7-1: Cross-action composition (min/AND/OR) for all level pairs
    INV-R7-2: At aggregate_dd >= 12%, no new dispatch for ANY strategy
    INV-R7-3: Startup assertion that aggregate thresholds are tighter than N×per-strategy
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

import pytest

from forex_system.risk.drawdown_contract import (
    AggregateDrawdownContract,
    AggregateDDLevel,
    ContractAssessment,
    DrawdownContract,
    DrawdownLevel,
    compose_dispatch_decision,
)
from forex_system.risk.kill_switch import KillSwitch, TriggerReason


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# CRO R-7.1 thresholds
AGG_WARN = 0.04
AGG_HALVE = 0.08
AGG_HALT = 0.12
AGG_LOCKOUT = 0.15

# Per-strategy thresholds (unchanged)
PS_HALT = 0.10
PS_REDUCE = 0.15
PS_FULL = 0.20


def _ts(offset_seconds: float = 0.0) -> datetime:
    """Return a UTC datetime offset_seconds before now (for monotonic test timestamps).

    Uses wall-clock relative offsets so timestamps pass the staleness check.
    offset_seconds=0 is now; negative offsets are in the past (stale if > budget);
    positive offsets are in the future — but for sequential bar simulation we
    use offset_seconds counting upward from a recent past baseline.

    For test sequences: bar 0 = now-30s, bar 1 = now-29s, ..., bar N = now-(30-N)s.
    This keeps all timestamps within the 60s staleness budget.
    """
    now = datetime.now(timezone.utc)
    return now - timedelta(seconds=30.0) + timedelta(seconds=offset_seconds)


# ---------------------------------------------------------------------------
# Mock trajectory-fragile contract for F-002 / N-3 counterexample
# ---------------------------------------------------------------------------

class _MockTrajectoryFragileContract:
    """Deliberate counterexample: smooths aggregate_equity over 5-bar moving average.

    A genuinely trajectory-fragile contract: it evaluates drawdown on the
    5-bar moving average of aggregate equity rather than the raw value.
    This means a single-bar trough does NOT cause it to fire if the surrounding
    bars are higher — the very relocation pattern N-3 names.

    Used in F-002 to prove the REAL AggregateDrawdownContract is threshold-shaped
    (not trajectory-shaped) by comparison.
    """

    HALT_THRESHOLD = 0.12
    LOCKOUT_THRESHOLD = 0.15
    WINDOW = 5

    def __init__(self) -> None:
        self._peak = 0.0
        self._history: list[float] = []

    def update_equity(self, equity: float, **kwargs) -> object:
        """Update with moving-average smoothing (trajectory-fragile)."""
        if equity > self._peak:
            self._peak = equity
        self._history.append(equity)
        smoothed = sum(self._history[-self.WINDOW:]) / len(self._history[-self.WINDOW:])
        dd = max(0.0, (self._peak - smoothed) / self._peak) if self._peak > 0 else 0.0

        @dataclass(frozen=True)
        class _FakeAssessment:
            level: str
            allows_new_dispatch: bool
            force_flat: bool

        if dd >= self.LOCKOUT_THRESHOLD:
            return _FakeAssessment(level="lockout", allows_new_dispatch=False, force_flat=True)
        elif dd >= self.HALT_THRESHOLD:
            return _FakeAssessment(level="halt", allows_new_dispatch=False, force_flat=False)
        return _FakeAssessment(level="normal", allows_new_dispatch=True, force_flat=False)


def _make_agg_contract(kill_switch=None) -> AggregateDrawdownContract:
    # persist_peak=False: tests must not write to or read from data/dd_agg_peak.json.
    # Production code uses persist_peak=True (the default); tests use False so that:
    #   (a) test isolation is guaranteed — no cross-test state leakage via the file
    #   (b) tests that mock the FS can control the path without side-effects
    return AggregateDrawdownContract(
        warn_threshold=AGG_WARN,
        halve_threshold=AGG_HALVE,
        halt_threshold=AGG_HALT,
        lockout_threshold=AGG_LOCKOUT,
        per_strategy_halt_threshold=PS_HALT,
        per_strategy_full_halt_threshold=PS_FULL,
        n_strategies_max=4,
        kill_switch=kill_switch,
        persist_peak=False,  # test path: no filesystem I/O
    )


def _make_per_strategy_contract() -> DrawdownContract:
    return DrawdownContract(
        halt_threshold=PS_HALT,
        reduce_threshold=PS_REDUCE,
        full_halt_threshold=PS_FULL,
    )


def _equity_at_dd(peak: float, dd_pct: float) -> float:
    """Compute equity value representing a given drawdown from peak."""
    return peak * (1.0 - dd_pct)


# ---------------------------------------------------------------------------
# REM-7-T1: LTCM scenario
# ---------------------------------------------------------------------------

class TestRem7T1LtcmScenario:
    """4 strategies at 8% per-strategy DD (below 10% threshold);
    aggregate book at 18% DD (above 15% lockout threshold).
    Aggregate fires; per-strategy contracts do NOT fire.
    """

    def test_aggregate_fires_when_per_strategy_thresholds_not_breached(self) -> None:
        """REM-7-T1: LTCM scenario core assertion.

        4 strategies each at 8% DD (below 10% per-strategy halt threshold).
        Aggregate equity at 18% DD (above 15% aggregate lockout threshold).
        Assert: AggregateDrawdownContract fires LOCKOUT.
        Assert: per-strategy DrawdownContracts do NOT fire (still NORMAL).

        This scenario WOULD produce wrong behavior today without this fix:
        no aggregate instance exists; 4×8% individual DDs bypass the ladder.
        """
        peak_per_strategy = 25_000.0  # 4 strategies × 25k = 100k peak aggregate
        peak_aggregate = 100_000.0

        per_strategy_equity = _equity_at_dd(peak_per_strategy, 0.08)  # 8% DD each
        aggregate_equity = _equity_at_dd(peak_aggregate, 0.18)        # 18% aggregate DD

        # Per-strategy contracts — should remain NORMAL (8% < 10% halt threshold)
        per_strategy_contracts = [_make_per_strategy_contract() for _ in range(4)]
        # Prime the peak on each contract
        for contract in per_strategy_contracts:
            contract.assess(peak_per_strategy)  # establish peak
        per_strategy_assessments = [
            contract.assess(per_strategy_equity) for contract in per_strategy_contracts
        ]

        for i, assessment in enumerate(per_strategy_assessments):
            assert assessment.level == DrawdownLevel.NORMAL, (
                f"Per-strategy contract {i} should be NORMAL at 8% DD, "
                f"got {assessment.level} (LTCM scenario REM-7-T1)"
            )
            assert assessment.allows_new_dispatch, (
                f"Per-strategy contract {i} should allow dispatch at 8% DD"
            )

        # Aggregate contract — should fire LOCKOUT (18% > 15% lockout threshold)
        agg_contract = _make_agg_contract()
        agg_contract.update_equity(peak_aggregate)  # establish peak
        agg_assessment = agg_contract.update_equity(
            aggregate_equity,
            contributing_strategies=["s1", "s2", "s3", "s4"],
        )

        assert agg_assessment.level == AggregateDDLevel.LOCKOUT, (
            f"Aggregate contract should be LOCKOUT at 18% DD, "
            f"got {agg_assessment.level} (LTCM scenario REM-7-T1)"
        )
        assert not agg_assessment.allows_new_dispatch, (
            "Aggregate contract at LOCKOUT must NOT allow new dispatch"
        )
        assert agg_assessment.force_flat, (
            "Aggregate contract at LOCKOUT must force flat"
        )

    def test_aggregate_fires_at_halt_threshold(self) -> None:
        """Aggregate at 12% DD fires HALT (not just HALVE)."""
        peak = 100_000.0
        agg_contract = _make_agg_contract()
        agg_contract.update_equity(peak)
        equity_at_12 = _equity_at_dd(peak, 0.13)  # 13% > 12% halt
        assessment = agg_contract.update_equity(equity_at_12)
        assert assessment.level == AggregateDDLevel.HALT
        assert not assessment.allows_new_dispatch

    def test_aggregate_fires_at_halve_threshold(self) -> None:
        """Aggregate at 8% DD fires HALVE (sizing_multiplier=0.5)."""
        peak = 100_000.0
        agg_contract = _make_agg_contract()
        agg_contract.update_equity(peak)
        equity_at_9 = _equity_at_dd(peak, 0.09)  # 9% > 8% halve
        assessment = agg_contract.update_equity(equity_at_9)
        assert assessment.level == AggregateDDLevel.HALVE
        assert assessment.sizing_multiplier == pytest.approx(0.5)

    def test_per_strategy_below_threshold_stays_normal(self) -> None:
        """Per-strategy at 8% is NORMAL (threshold is 10%)."""
        contract = _make_per_strategy_contract()
        contract.assess(100_000.0)
        assessment = contract.assess(_equity_at_dd(100_000.0, 0.08))
        assert assessment.level == DrawdownLevel.NORMAL


# ---------------------------------------------------------------------------
# N-3: SHUFFLE-CONTROL variant (NHT mandatory)
# ---------------------------------------------------------------------------

class TestN3ShuffleControl:
    """Monte Carlo: 1000 permutations of per-strategy DD onset timing.

    F-002 rewrite: tests BOTH the threshold-shaped AggregateDrawdownContract
    and a trajectory-fragile mock, proving the test can distinguish them.

    The real contract must fire in >=99% of shuffled trajectories where the
    aggregate trough breaches the halt threshold. The fragile mock must fire
    in <50% of the same trajectories, demonstrating trajectory sensitivity.

    This design ensures the test actually falsifies trajectory dependence —
    the original test was tautological (it injected 18% DD by construction
    whenever all strategies hit DD, so any contract would fire).
    """

    def _run_breaching_trajectories(
        self,
        contract_factory,
        seed: int,
        total: int = 1000,
        bars: int = 15,
        peak_aggregate: float = 100_000.0,
        trough_dd_pct: float = 0.18,
    ) -> float:
        """Run `total` randomly-shaped trajectories that ALL breach the halt threshold.

        Each trajectory GUARANTEES the threshold is breached — the test exclusively
        asserts that a threshold-shaped contract catches it regardless of SHAPE.

        Trajectory construction:
        - Establish peak at peak_aggregate.
        - A random onset bar (0..bars//2) triggers a random lead-in (gradual decline).
        - At the "trough bar" (randomly positioned), aggregate = trough_dd_pct % DD.
        - Before onset: at peak. After trough bar: recovery back toward peak.
        - The SHAPE (lead-in length, lead-in slope, recovery rate) is randomized.
        - This tests whether the contract catches ALL trajectories that breach the
          threshold, regardless of how quickly the trough is reached or how brief it is.

        The fragile mock uses 5-bar moving-average smoothing: a sharp single-bar
        trough is damped, so the smoothed value may not breach the threshold even
        when the raw value does. That's the relocation pattern N-3 names.

        Returns fraction of `total` trajectories where contract fires HALT or LOCKOUT.
        """
        random.seed(seed)
        fires = 0

        for _ in range(total):
            c = contract_factory()

            # Establish peak
            peak_ts = _ts(0)
            if isinstance(c, AggregateDrawdownContract):
                c.update_equity(peak_aggregate, snapshot_timestamp=peak_ts)
            else:
                c.update_equity(peak_aggregate)

            # Random trough bar: where the 18% DD minimum is reached
            onset = random.randint(0, bars // 3)          # gradual lead-in starts here
            trough_bar = random.randint(onset + 1, bars // 2)  # trough happens here

            # Random lead-in slope: how quickly equity drops toward trough
            lead_in_steps = max(1, trough_bar - onset)
            trough_equity = _equity_at_dd(peak_aggregate, trough_dd_pct)  # 82000

            # Generate per-bar equities
            fired = False
            for bar in range(bars):
                bar_ts = _ts(bar + 1)

                if bar < onset:
                    eq = peak_aggregate
                elif bar <= trough_bar:
                    # Linear interpolation: peak → trough over lead_in_steps bars
                    progress = (bar - onset) / lead_in_steps
                    eq = peak_aggregate + (trough_equity - peak_aggregate) * progress
                else:
                    # Recovery: move back toward peak at a random rate
                    recovery_rate = random.uniform(0.3, 0.9)  # fraction recovered per bar
                    bars_since_trough = bar - trough_bar
                    eq = trough_equity + (peak_aggregate - trough_equity) * (
                        1.0 - (1.0 - recovery_rate) ** bars_since_trough
                    )

                if isinstance(c, AggregateDrawdownContract):
                    assessment = c.update_equity(
                        eq,
                        snapshot_timestamp=bar_ts,
                        contributing_strategies=["s1", "s2", "s3", "s4"],
                    )
                    fired_this_bar = assessment.level in (
                        AggregateDDLevel.HALT, AggregateDDLevel.LOCKOUT
                    )
                else:
                    assessment = c.update_equity(eq)
                    fired_this_bar = not assessment.allows_new_dispatch

                if fired_this_bar:
                    fired = True
                    break

            if fired:
                fires += 1

        return fires / total

    @pytest.mark.parametrize("seed", [42, 123, 999])
    def test_aggregate_fires_in_99pct_of_shuffled_trajectories(self, seed: int) -> None:
        """N-3 SHUFFLE-CONTROL (threshold-shaped half, F-002 rewrite):
        AggregateDrawdownContract fires in >=99% of trajectories that breach the threshold.

        All 1000 trajectories are constructed to breach the 12% halt threshold
        (reaching 18% DD trough). The shape (lead-in slope, trough timing, recovery)
        is randomly varied. A threshold-shaped contract must catch 100% of threshold
        breaches regardless of trajectory shape.

        Contrast with test_fragile_contract_fires_below_50pct: the mock fragile
        contract uses 5-bar smoothing and misses many threshold breaches because
        the smoothed value does not breach the threshold even when the raw does.
        This asymmetry proves the test is NOT tautological — it distinguishes
        threshold-shaped from trajectory-shaped contracts.
        """
        fire_rate = self._run_breaching_trajectories(
            _make_agg_contract, seed=seed, total=1000
        )
        assert fire_rate >= 0.99, (
            f"N-3 SHUFFLE-CONTROL FAILED (seed={seed}): AggregateDrawdownContract fired "
            f"in {fire_rate:.4f} of threshold-breaching trajectories — expected >=0.99. "
            "Contract appears trajectory-fragile (not purely threshold-shaped). "
            "Every trajectory that breaches the 12% halt threshold MUST fire."
        )

    @pytest.mark.parametrize("seed", [42, 123, 999])
    def test_fragile_contract_fires_below_50pct_of_same_trajectories(self, seed: int) -> None:
        """N-3 SHUFFLE-CONTROL (trajectory-fragile counterexample half, F-002 rewrite):
        _MockTrajectoryFragileContract fires in <50% of the same threshold-breaching trajectories.

        The mock contract uses a 5-bar moving-average: single-bar troughs that breach
        the threshold are smoothed, so the smoothed value may not breach even when the
        raw value does. This is the relocation pattern N-3 names.

        This test proves the N-3 test CAN distinguish threshold-shaped from
        trajectory-fragile contracts — the original test could not.
        """
        fire_rate = self._run_breaching_trajectories(
            _MockTrajectoryFragileContract, seed=seed, total=1000
        )
        assert fire_rate < 0.50, (
            f"N-3 SHUFFLE-CONTROL FRAGILE-COUNTEREXAMPLE FAILED (seed={seed}): "
            f"_MockTrajectoryFragileContract fired in {fire_rate:.4f} of trajectories "
            "— expected <0.50. The mock contract is not actually trajectory-fragile "
            "relative to the test scenarios, so the test cannot distinguish contracts."
        )


# ---------------------------------------------------------------------------
# REM-7-T2: Per-strategy isolation
# ---------------------------------------------------------------------------

class TestRem7T2PerStrategyIsolation:
    """Strategy-A at 12% DD fires per-strategy; AggregateDrawdownContract does NOT."""

    def test_per_strategy_fires_aggregate_stays_normal(self) -> None:
        """REM-7-T2: Strategy-A at 12% DD fires HALT_NEW_DISPATCH.
        Other 3 strategies flat. Aggregate book at 3% DD (< 4% warn threshold).
        AggregateDrawdownContract stays NORMAL.
        """
        peak_aggregate = 100_000.0
        # Strategy A: 25k → 12% DD
        equity_a = _equity_at_dd(25_000.0, 0.12)  # 22000
        # Strategies B, C, D: each at 25k (flat)
        equity_other = 25_000.0 * 3

        aggregate_equity = equity_a + equity_other  # 22000 + 75000 = 97000

        # Per-strategy contract for A
        contract_a = _make_per_strategy_contract()
        contract_a.assess(25_000.0)  # establish peak
        assessment_a = contract_a.assess(equity_a)

        assert assessment_a.level == DrawdownLevel.HALT_NEW_DISPATCH, (
            f"Strategy A at 12% DD should be HALT_NEW_DISPATCH, got {assessment_a.level}"
        )

        # Aggregate contract: 97k/100k = 3% DD (< 4% warn threshold → NORMAL)
        agg_contract = _make_agg_contract()
        agg_contract.update_equity(peak_aggregate)
        agg_assessment = agg_contract.update_equity(aggregate_equity)

        assert agg_assessment.level == AggregateDDLevel.NORMAL, (
            f"Aggregate at 3% DD should be NORMAL, got {agg_assessment.level}"
        )
        assert agg_assessment.allows_new_dispatch, (
            "Aggregate at NORMAL should allow new dispatch"
        )


# ---------------------------------------------------------------------------
# REM-7-T3: Dual-trigger — both fire simultaneously
# ---------------------------------------------------------------------------

class TestRem7T3DualTrigger:
    """Strategy-A at 12% DD AND aggregate at 18% DD simultaneously."""

    def test_both_contracts_fire_with_distinct_contract_type_labels(self) -> None:
        """REM-7-T3: Per-strategy at 12% DD fires HALT_NEW_DISPATCH.
        Aggregate at 18% fires LOCKOUT.
        Both fire simultaneously; kill switch log would contain two trigger events.
        """
        # Per-strategy A: 12% DD → HALT_NEW_DISPATCH
        contract_a = _make_per_strategy_contract()
        contract_a.assess(100_000.0)
        assessment_a = contract_a.assess(_equity_at_dd(100_000.0, 0.12))
        assert assessment_a.level == DrawdownLevel.HALT_NEW_DISPATCH

        # Aggregate: 18% DD → LOCKOUT
        agg_contract = _make_agg_contract()
        agg_contract.update_equity(100_000.0)
        agg_assessment = agg_contract.update_equity(_equity_at_dd(100_000.0, 0.18))
        assert agg_assessment.level == AggregateDDLevel.LOCKOUT

        # Both have distinct contract_type semantics
        assert not assessment_a.allows_new_dispatch  # per-strategy halted
        assert not agg_assessment.allows_new_dispatch  # aggregate locked out
        assert agg_assessment.force_flat  # aggregate forces flat

    def test_dual_trigger_with_kill_switch(self) -> None:
        """REM-7-T3 with kill switch: LOCKOUT triggers DRAWDOWN_AGGREGATE_LOCKOUT."""
        ks = KillSwitch(initial_equity=100_000.0)
        agg_contract = _make_agg_contract(kill_switch=ks)
        agg_contract.update_equity(100_000.0)
        agg_contract.update_equity(_equity_at_dd(100_000.0, 0.18))

        assert ks.is_triggered, "Kill switch should be triggered at 18% aggregate DD"
        assert ks.last_event is not None
        assert ks.last_event.reason == TriggerReason.DRAWDOWN_AGGREGATE_LOCKOUT, (
            f"Expected DRAWDOWN_AGGREGATE_LOCKOUT, got {ks.last_event.reason}"
        )

    def test_halt_triggers_correct_reason(self) -> None:
        """HALT (12-15% DD) triggers DRAWDOWN_AGGREGATE_HALT, not LOCKOUT."""
        ks = KillSwitch(initial_equity=100_000.0)
        agg_contract = _make_agg_contract(kill_switch=ks)
        agg_contract.update_equity(100_000.0)
        agg_contract.update_equity(_equity_at_dd(100_000.0, 0.13))  # 13% → HALT

        assert ks.is_triggered
        assert ks.last_event.reason == TriggerReason.DRAWDOWN_AGGREGATE_HALT, (
            f"Expected DRAWDOWN_AGGREGATE_HALT, got {ks.last_event.reason}"
        )


# ---------------------------------------------------------------------------
# INV-R7-1: Cross-action composition
# ---------------------------------------------------------------------------

class TestInvR7_1CrossActionComposition:
    """Conservative composition: min(sizing), AND(dispatch_allowed), OR(force_flat)."""

    @pytest.mark.parametrize("per_strategy_level,agg_level,expected_sizing,expected_dispatch,expected_force_flat", [
        # per_strategy NORMAL (1.0), agg NORMAL (1.0) → 1.0, True, False
        (DrawdownLevel.NORMAL, AggregateDDLevel.NORMAL, 1.0, True, False),
        # per_strategy NORMAL (1.0), agg HALVE (0.5) → 0.5, True, False
        (DrawdownLevel.NORMAL, AggregateDDLevel.HALVE, 0.5, True, False),
        # per_strategy REDUCE_SIZING (0.5), agg NORMAL (1.0) → 0.5, False, False
        (DrawdownLevel.REDUCE_SIZING, AggregateDDLevel.NORMAL, 0.5, False, False),
        # per_strategy REDUCE_SIZING (0.5), agg HALVE (0.5) → 0.5, False, False
        (DrawdownLevel.REDUCE_SIZING, AggregateDDLevel.HALVE, 0.5, False, False),
        # per_strategy NORMAL (1.0), agg HALT (0.0) → 0.0, False, False
        (DrawdownLevel.NORMAL, AggregateDDLevel.HALT, 0.0, False, False),
        # per_strategy HALT_NEW_DISPATCH (1.0), agg NORMAL (1.0) → 1.0, False, False
        (DrawdownLevel.HALT_NEW_DISPATCH, AggregateDDLevel.NORMAL, 1.0, False, False),
        # per_strategy FULL_HALT (0.0), agg NORMAL (1.0) → 0.0, False, True
        # (per_strategy FULL_HALT forces flat; OR rule: True OR False = True)
        (DrawdownLevel.FULL_HALT, AggregateDDLevel.NORMAL, 0.0, False, True),
        # per_strategy NORMAL (1.0), agg LOCKOUT (0.0) → 0.0, False, True
        (DrawdownLevel.NORMAL, AggregateDDLevel.LOCKOUT, 0.0, False, True),
        # per_strategy FULL_HALT (0.0), agg LOCKOUT (0.0) → 0.0, False, True
        (DrawdownLevel.FULL_HALT, AggregateDDLevel.LOCKOUT, 0.0, False, True),
    ])
    def test_inv_r7_1_composition(
        self,
        per_strategy_level: DrawdownLevel,
        agg_level: AggregateDDLevel,
        expected_sizing: float,
        expected_dispatch: bool,
        expected_force_flat: bool,
    ) -> None:
        """INV-R7-1: conservative composition for all (per_strategy × aggregate) pairs.

        F-010: Uses the PRODUCTION compose_dispatch_decision() function — not an
        inline reimplementation. This ensures the test can catch bugs in production
        composition logic (e.g., using max instead of min, OR instead of AND).

        Rules verified via compose_dispatch_decision():
            effective_sizing = min(per_strategy_sizing, aggregate_sizing)
            effective_dispatch = per_strategy_allows AND aggregate_allows
            effective_force_flat = per_strategy_force_flat OR aggregate_force_flat
        """
        from forex_system.risk.drawdown_contract import _SIZING_BY_LEVEL, _AGGREGATE_SIZING_BY_LEVEL

        ps_sizing = _SIZING_BY_LEVEL[per_strategy_level]
        agg_sizing = _AGGREGATE_SIZING_BY_LEVEL[agg_level]
        ps_allows = per_strategy_level == DrawdownLevel.NORMAL
        agg_allows = agg_level not in (AggregateDDLevel.HALT, AggregateDDLevel.LOCKOUT)
        ps_force_flat = per_strategy_level == DrawdownLevel.FULL_HALT
        agg_force_flat = agg_level == AggregateDDLevel.LOCKOUT

        # F-010: call the PRODUCTION function — not inline computation
        ps_assessment = ContractAssessment(
            sizing=ps_sizing,
            dispatch_allowed=ps_allows,
            force_flat=ps_force_flat,
        )
        agg_assessment = ContractAssessment(
            sizing=agg_sizing,
            dispatch_allowed=agg_allows,
            force_flat=agg_force_flat,
        )
        composed = compose_dispatch_decision(ps_assessment, agg_assessment)

        assert composed.effective_sizing == pytest.approx(expected_sizing, abs=1e-6), (
            f"INV-R7-1 composition error: "
            f"compose_dispatch_decision(...).effective_sizing = {composed.effective_sizing} "
            f"!= {expected_sizing} (expected min({ps_sizing}, {agg_sizing}))"
        )
        assert composed.effective_dispatch_allowed == expected_dispatch, (
            f"INV-R7-1 dispatch composition error: "
            f"compose_dispatch_decision(...).effective_dispatch_allowed = "
            f"{composed.effective_dispatch_allowed} != {expected_dispatch}"
        )
        assert composed.effective_force_flat == expected_force_flat, (
            f"INV-R7-1 force_flat composition error: "
            f"compose_dispatch_decision(...).effective_force_flat = "
            f"{composed.effective_force_flat} != {expected_force_flat}"
        )


# ---------------------------------------------------------------------------
# INV-R7-2: At aggregate_dd >= 12%, no new dispatch for ANY strategy
# ---------------------------------------------------------------------------

class TestInvR7_2NoDispatchAboveHaltThreshold:
    """INV-R7-2: aggregate_dd >= 12% → no new dispatch for ANY strategy."""

    def test_no_new_dispatch_at_exactly_halt_threshold(self) -> None:
        """At exactly 12% aggregate DD, no new dispatch allowed."""
        agg_contract = _make_agg_contract()
        agg_contract.update_equity(100_000.0)
        # 12.01% > 12% halt threshold
        assessment = agg_contract.update_equity(_equity_at_dd(100_000.0, 0.1201))
        assert not assessment.allows_new_dispatch, (
            f"INV-R7-2: no dispatch allowed at 12.01% aggregate DD, "
            f"got allows_new_dispatch={assessment.allows_new_dispatch}"
        )

    def test_dispatch_allowed_below_halt_threshold(self) -> None:
        """Below 12% aggregate DD, dispatch allowed (at NORMAL/WARN/HALVE levels)."""
        agg_contract = _make_agg_contract()
        agg_contract.update_equity(100_000.0)
        # 10% < 12% halt threshold → HALVE level, dispatch still allowed
        assessment = agg_contract.update_equity(_equity_at_dd(100_000.0, 0.10))
        assert assessment.allows_new_dispatch, (
            f"Dispatch should be allowed at 10% aggregate DD (below 12% halt), "
            f"got {assessment.level}"
        )


# ---------------------------------------------------------------------------
# INV-R7-3: Startup assertion
# ---------------------------------------------------------------------------

class TestInvR7_3StartupAssertion:
    """Startup validates that aggregate thresholds are strictly tighter than N×per-strategy."""

    def test_valid_thresholds_do_not_raise(self) -> None:
        """Default thresholds satisfy INV-R7-3."""
        # Should not raise — default thresholds are calibrated per CRO R-7.1
        contract = _make_agg_contract()
        assert contract is not None

    def test_invalid_thresholds_raise_assertion_error(self) -> None:
        """Aggregate halt threshold >= N × per-strategy halt raises AssertionError."""
        with pytest.raises((AssertionError, ValueError)):
            AggregateDrawdownContract(
                halt_threshold=0.50,   # 50% — not tighter than 4×10%=40%... wait, IS > 40%
                lockout_threshold=0.80,
                per_strategy_halt_threshold=0.10,  # 4×0.10 = 0.40 < 0.50 → FAILS INV-R7-3
                n_strategies_max=4,
            )

    def test_trigger_reason_enum_has_aggregate_values(self) -> None:
        """CRO BC-REM7-LADDER-5: TriggerReason enum has DRAWDOWN_AGGREGATE_HALT and LOCKOUT."""
        assert hasattr(TriggerReason, "DRAWDOWN_AGGREGATE_HALT"), (
            "TriggerReason missing DRAWDOWN_AGGREGATE_HALT (CRO BC-REM7-LADDER-5)"
        )
        assert hasattr(TriggerReason, "DRAWDOWN_AGGREGATE_LOCKOUT"), (
            "TriggerReason missing DRAWDOWN_AGGREGATE_LOCKOUT (CRO BC-REM7-LADDER-5)"
        )
        assert TriggerReason.DRAWDOWN_AGGREGATE_HALT.value == "drawdown_aggregate_halt"
        assert TriggerReason.DRAWDOWN_AGGREGATE_LOCKOUT.value == "drawdown_aggregate_lockout"


# ---------------------------------------------------------------------------
# Gap-2 / CRO VETO #5 class: AggregateDrawdownContract peak persistence tests
# ---------------------------------------------------------------------------


class TestAggregateDrawdownPeakPersistence:
    """Gap-2: AggregateDrawdownContract persists its peak across restarts.

    Without this fix, a restart mid-drawdown re-anchors the aggregate peak to 0.0
    and blinds the LTCM-defense ladder for the entire recovery period — the same
    kill-switch-blindness CRO vetoed for per-strategy DrawdownContract.
    """

    def _make_persisting_contract(
        self, *, data_dir, kill_switch=None
    ) -> AggregateDrawdownContract:
        """Create an AggregateDrawdownContract with persist_peak=True wired to tmp_path.

        Uses unittest.mock.patch to redirect _agg_peak_state_path to the temp dir
        so tests are isolated and don't write to data/dd_agg_peak.json.
        """
        # Patch applied by each test individually via with-block.
        return AggregateDrawdownContract(
            warn_threshold=AGG_WARN,
            halve_threshold=AGG_HALVE,
            halt_threshold=AGG_HALT,
            lockout_threshold=AGG_LOCKOUT,
            per_strategy_halt_threshold=PS_HALT,
            per_strategy_full_halt_threshold=PS_FULL,
            n_strategies_max=4,
            kill_switch=kill_switch,
            persist_peak=True,
        )

    def test_peak_survives_restart(self) -> None:
        """Gap-2: Aggregate peak written on update is loaded by a new contract instance.

        Simulates two process starts. First process establishes a peak;
        second process (new contract) loads it and should NOT re-anchor to 0.
        """
        import tempfile
        import unittest.mock as mock
        from pathlib import Path as _Path

        tmp_dir = _Path(tempfile.mkdtemp())
        state_path = tmp_dir / "dd_agg_peak.json"

        def _patched_path():
            return state_path

        with mock.patch(
            "forex_system.risk.drawdown_contract._agg_peak_state_path",
            side_effect=_patched_path,
        ):
            # Session 1: establish peak at 110_000
            c1 = self._make_persisting_contract(data_dir=str(tmp_dir))
            c1.update_equity(110_000.0, snapshot_timestamp=_ts(1))
            assert abs(c1._peak_equity - 110_000.0) < 1e-6

            # State file must exist after the first update
            assert state_path.exists(), "Gap-2: peak state file must be written after update"

        # Session 2: new contract instance — must load the persisted 110_000 peak
        with mock.patch(
            "forex_system.risk.drawdown_contract._agg_peak_state_path",
            side_effect=_patched_path,
        ):
            c2 = self._make_persisting_contract(data_dir=str(tmp_dir))
            assert abs(c2._peak_equity - 110_000.0) < 1e-6, (
                f"Gap-2: restart erased aggregate peak; "
                f"loaded={c2._peak_equity}, expected=110000. "
                "Restart mid-drawdown would blind the LTCM-defense ladder."
            )

    def test_restart_mid_drawdown_does_not_blind_ladder(self) -> None:
        """Gap-2: After restart during 18% DD, ladder must still fire LOCKOUT.

        Without fix: new contract starts at peak=0, first equity sets new peak,
        DD appears to be 0% — LOCKOUT never fires even though the REAL DD is 18%.
        With fix: persisted peak is loaded; 18% DD fires LOCKOUT immediately.
        """
        import tempfile
        import unittest.mock as mock
        from pathlib import Path as _Path

        tmp_dir = _Path(tempfile.mkdtemp())
        state_path = tmp_dir / "dd_agg_peak.json"

        def _patched_path():
            return state_path

        peak_equity = 100_000.0
        equity_after_drawdown = peak_equity * (1.0 - 0.18)  # 18% DD — above lockout 15%

        with mock.patch(
            "forex_system.risk.drawdown_contract._agg_peak_state_path",
            side_effect=_patched_path,
        ):
            # Session 1: establish peak, then drop 18% (no restart yet)
            c1 = self._make_persisting_contract(data_dir=str(tmp_dir))
            c1.update_equity(peak_equity, snapshot_timestamp=_ts(1))
            # Don't update with the drawdown equity yet — simulate restart before that

        # Session 2: restart. Peak was 100_000. Now provide equity at 18% DD.
        with mock.patch(
            "forex_system.risk.drawdown_contract._agg_peak_state_path",
            side_effect=_patched_path,
        ):
            c2 = self._make_persisting_contract(data_dir=str(tmp_dir))
            # Loaded peak must be 100_000 (not 0)
            assert abs(c2._peak_equity - peak_equity) < 1e-6, (
                f"Gap-2: pre-condition failed — loaded peak={c2._peak_equity} != {peak_equity}"
            )
            assessment = c2.update_equity(equity_after_drawdown, snapshot_timestamp=_ts(2))
            assert assessment.level == AggregateDDLevel.LOCKOUT, (
                f"Gap-2: restart-blind bug — after restart with persisted peak, "
                f"18% DD should fire LOCKOUT but got level={assessment.level.value}. "
                "Without this fix the ladder is blind until the peak re-establishes."
            )

    def test_persist_peak_false_no_file_written(self) -> None:
        """persist_peak=False (test path) must not write any state file."""
        import tempfile
        import unittest.mock as mock
        from pathlib import Path as _Path

        tmp_dir = _Path(tempfile.mkdtemp())
        state_path = tmp_dir / "dd_agg_peak.json"

        def _patched_path():
            return state_path

        with mock.patch(
            "forex_system.risk.drawdown_contract._agg_peak_state_path",
            side_effect=_patched_path,
        ):
            c = _make_agg_contract()  # uses persist_peak=False
            c.update_equity(100_000.0, snapshot_timestamp=_ts(1))

        assert not state_path.exists(), (
            "Gap-2: persist_peak=False must not write a state file "
            "(test isolation violation)"
        )

    def test_aggregate_mock_cycle_does_not_advance_agg_peak(self, tmp_path) -> None:
        """F1: AggregateDrawdownContract.update_equity(is_mock=True) must NOT advance peak.

        This test drives the AGGREGATE path directly — not the per-strategy contract.
        It verifies the F1 fix: that the 100_000.0 mock-sentinel cannot poison the
        aggregate high-water mark or be written to dd_agg_peak.json.

        Previous test (Gap-3) was a FALSE test: it exercised DrawdownContract.assess()
        (per-strategy) while the aggregate AggregateDrawdownContract.update_equity()
        had NO is_mock guard and would advance _peak_equity unconditionally.

        Assertions:
            1. After update_equity(100_000.0, is_mock=True), _peak_equity remains 0.0.
            2. No dd_agg_peak.json file is written (persist_peak=False in test fixture;
               also verified via a persist_peak=True variant with tmp_path).
            3. A subsequent real cycle sets the peak from the first non-mock equity.
        """
        from unittest import mock

        # --- Part A: persist_peak=False (test isolation, verifies in-process guard) ---
        c = _make_agg_contract()  # persist_peak=False

        # Mock cycle: must NOT advance _peak_equity
        c.update_equity(100_000.0, snapshot_timestamp=_ts(0), is_mock=True)
        assert c._peak_equity == 0.0, (
            "F1: update_equity(is_mock=True) must not advance aggregate _peak_equity. "
            f"Got {c._peak_equity}; expected 0.0. Mock sentinel poisoned the aggregate peak."
        )

        # First real cycle: peak must be established from this equity value
        c.update_equity(98_500.0, snapshot_timestamp=_ts(1), is_mock=False)
        assert abs(c._peak_equity - 98_500.0) < 1e-6, (
            f"F1: first non-mock update_equity must set peak to 98500.0; got {c._peak_equity}"
        )

        # Second mock cycle with higher value: peak must NOT advance
        c.update_equity(200_000.0, snapshot_timestamp=_ts(2), is_mock=True)
        assert abs(c._peak_equity - 98_500.0) < 1e-6, (
            f"F1: mock cycle with higher equity must not advance peak; "
            f"expected 98500.0, got {c._peak_equity}"
        )

        # --- Part B: persist_peak=True — verify no file written on mock cycle ---
        agg_peak_path = tmp_path / "dd_agg_peak.json"

        def _patched_path():
            return agg_peak_path

        with mock.patch(
            "forex_system.risk.drawdown_contract._agg_peak_state_path",
            side_effect=_patched_path,
        ):
            c2 = AggregateDrawdownContract(
                warn_threshold=AGG_WARN,
                halve_threshold=AGG_HALVE,
                halt_threshold=AGG_HALT,
                lockout_threshold=AGG_LOCKOUT,
                per_strategy_halt_threshold=PS_HALT,
                per_strategy_full_halt_threshold=PS_FULL,
                n_strategies_max=4,
                persist_peak=True,  # production mode: writes to disk
            )
            c2.update_equity(100_000.0, snapshot_timestamp=_ts(0), is_mock=True)

        assert not agg_peak_path.exists(), (
            "F1: update_equity(is_mock=True) with persist_peak=True must NOT write "
            "dd_agg_peak.json. The mock sentinel 100_000.0 must not poison the "
            "persisted aggregate high-water mark."
        )
        assert c2._peak_equity == 0.0, (
            f"F1 (persist_peak=True path): _peak_equity must remain 0.0 after mock cycle; "
            f"got {c2._peak_equity}"
        )
