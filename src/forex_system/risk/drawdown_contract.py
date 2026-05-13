"""CRO Wave-4 + Phase-1 + REM-7 drawdown contract ladder.

Enforces three mandatory halt levels sourced verbatim from:
    .fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/
    cro-bet1-sizing-revision.yaml  (BC-DD-1 / BC-DD-2 / BC-DD-3)

Per-strategy ladder (per-DrawdownContract instance):
    paper-equity DD ≥ 10%  →  halt new trial dispatch
    paper-equity DD ≥ 15%  →  reduce all sizing to 0.5x
    paper-equity DD ≥ 20%  →  full halt pending CRO review

Aggregate ladder (AggregateDrawdownContract, REM-7 / CRO R-7.1):
    aggregate DD ≥ 4%   →  warn only (no sizing change)
    aggregate DD ≥ 8%   →  halve aggregate sizing (0.5x applied to ALL strategies)
    aggregate DD ≥ 12%  →  halt new dispatch ALL strategies (DRAWDOWN_AGGREGATE_HALT)
    aggregate DD ≥ 15%  →  lockout ALL strategies, force flat (DRAWDOWN_AGGREGATE_LOCKOUT)

The aggregate ladder fires on correlated DD well BEFORE any per-strategy contract
would. This is the LTCM-class defense: 4 strategies each at 8% DD (below 10%
per-strategy threshold) but aggregate at 18% DD fires the aggregate halt.

Cross-action composition rule (CRO R-7.1):
    effective_sizing = min(per_strategy, aggregate_sizing)
    effective_dispatch_allowed = per_strategy_allows AND aggregate_allows
    effective_force_flat = per_strategy_force_flat OR aggregate_force_flat

DO NOT modify threshold constants without a CONSENSUS amendment co-signed by
NHT + HoQR.

Clock discipline:
    No wall-clock or monotonic is needed here; drawdown is a pure equity ratio.
    The caller owns the clock (it passes equity each cycle).

Thread-safety:
    _peak_equity is protected by threading.Lock so the same DrawdownContract
    instance can be shared across threads (e.g. a monitor thread + a cycle
    thread).  In production the paper loops are single-threaded, but the lock
    costs nothing and prevents subtle bugs if the architecture evolves.

Structured-log keys emitted on every assess() call:
    event, current_equity, peak_equity, drawdown_pct, level, sizing_multiplier,
    allows_new_dispatch, [transition] (if the level changed from previous call)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, List, Optional

logger = logging.getLogger("drawdown_contract")


class StaleEquitySnapshotError(Exception):
    """Raised when update_equity receives a stale or non-monotonic timestamp.

    F-004 / clock-and-ordering: AggregateDrawdownContract.update_equity enforces
    that each snapshot_timestamp is (a) monotonically non-decreasing relative to
    the previous call, and (b) not stale relative to wall-clock time (within
    staleness_budget_seconds of now).

    This prevents the LTCM-class race where a delayed or duplicated equity
    snapshot causes the aggregate contract to evaluate on stale state.
    """


class DrawdownLevel(Enum):
    NORMAL = "normal"
    HALT_NEW_DISPATCH = "halt_new_dispatch"  # DD >= halt_threshold (10%)
    REDUCE_SIZING = "reduce_sizing"           # DD >= reduce_threshold (15%)
    FULL_HALT = "full_halt"                   # DD >= full_halt_threshold (20%)


@dataclass(frozen=True)
class DrawdownAssessment:
    """Immutable snapshot of the current drawdown state.

    Callers must honour:
      - allows_new_dispatch: if False, do NOT dispatch new trades.
      - sizing_multiplier: apply to all position sizes before sending.
      - level == FULL_HALT: call halt_paper_loop and exit the dispatch path.
    """

    current_equity: float
    peak_equity: float
    drawdown_pct: float         # 0.0 to 1.0; positive means drawdown from peak
    level: DrawdownLevel
    sizing_multiplier: float    # 1.0 at NORMAL/HALT_NEW; 0.5 at REDUCE_SIZING; 0.0 at FULL_HALT
    allows_new_dispatch: bool   # True only at NORMAL


# Sizing multipliers per level — sourced from CRO Wave-4 binding; no silent defaults.
_SIZING_BY_LEVEL: dict[DrawdownLevel, float] = {
    DrawdownLevel.NORMAL: 1.0,
    DrawdownLevel.HALT_NEW_DISPATCH: 1.0,   # existing positions held; no NEW dispatch
    DrawdownLevel.REDUCE_SIZING: 0.5,
    DrawdownLevel.FULL_HALT: 0.0,
}


@dataclass
class DrawdownContract:
    """Enforces the CRO Wave-4 + Phase-1 drawdown contract ladder.

    Caller passes equity each cycle via assess(); the returned DrawdownAssessment
    contains the current level and sizing_multiplier.  Caller MUST honour the
    assessment in its dispatch path — this module enforces the contract logic;
    it does NOT take action on its own.

    Construction requires explicit threshold values — no silent defaults
    (per hard rule in dispatch).

    Args:
        halt_threshold:       DD fraction at which new dispatch is halted.
                              CRO binding: 0.10 (10%).
        reduce_threshold:     DD fraction at which sizing is cut to 0.5x.
                              CRO binding: 0.15 (15%).
        full_halt_threshold:  DD fraction at which all activity halts (0.0x sizing).
                              CRO binding: 0.20 (20%).

    Example::

        contract = DrawdownContract(
            halt_threshold=0.10,
            reduce_threshold=0.15,
            full_halt_threshold=0.20,
        )
        assessment = contract.assess(current_equity=95_000.0)
        if assessment.level == DrawdownLevel.FULL_HALT:
            halt_paper_loop(reason=f"drawdown_full_halt_{assessment.drawdown_pct:.4f}")
            return SKIP_DD_FULL_HALT
        elif assessment.level == DrawdownLevel.HALT_NEW_DISPATCH:
            return SKIP_DD_HALT_NEW
        # apply sizing_multiplier to target_units downstream
    """

    halt_threshold: float        # 0.10 — caller passes; no silent default
    reduce_threshold: float      # 0.15
    full_halt_threshold: float   # 0.20

    # Internal state — peak tracks the running high-water mark.
    _peak_equity: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _last_level: DrawdownLevel = field(default=DrawdownLevel.NORMAL, init=False)

    def __post_init__(self) -> None:
        if not (0.0 < self.halt_threshold < self.reduce_threshold < self.full_halt_threshold < 1.0):
            raise ValueError(
                f"DrawdownContract thresholds must satisfy "
                f"0 < halt({self.halt_threshold}) < reduce({self.reduce_threshold}) "
                f"< full_halt({self.full_halt_threshold}) < 1.0"
            )

    def assess(self, current_equity: float) -> DrawdownAssessment:
        """Evaluate current drawdown and return a DrawdownAssessment.

        Updates the running peak if current_equity > _peak_equity.
        Classifies the drawdown into one of four DrawdownLevel values.
        Emits one structured log line per call including level transitions.

        Args:
            current_equity: The current account equity (same currency as the
                initial equity — fetched from broker each cycle).

        Returns:
            DrawdownAssessment with level, sizing_multiplier, and allows_new_dispatch.
        """
        with self._lock:
            if current_equity > self._peak_equity:
                self._peak_equity = current_equity
            peak = self._peak_equity
            previous_level = self._last_level

        if peak <= 0.0:
            # Defensive: cannot compute drawdown without a positive peak.
            # Treat as NORMAL but log a warning.
            dd_pct = 0.0
            level = DrawdownLevel.NORMAL
        else:
            dd_pct = max(0.0, (peak - current_equity) / peak)

            if dd_pct >= self.full_halt_threshold:
                level = DrawdownLevel.FULL_HALT
            elif dd_pct >= self.reduce_threshold:
                level = DrawdownLevel.REDUCE_SIZING
            elif dd_pct >= self.halt_threshold:
                level = DrawdownLevel.HALT_NEW_DISPATCH
            else:
                level = DrawdownLevel.NORMAL

        sizing_multiplier = _SIZING_BY_LEVEL[level]
        allows_new_dispatch = level == DrawdownLevel.NORMAL

        with self._lock:
            self._last_level = level

        log_extra: dict = {
            "event": "DRAWDOWN_ASSESSMENT",
            "current_equity": current_equity,
            "peak_equity": peak,
            "drawdown_pct": round(dd_pct, 6),
            "level": level.value,
            "sizing_multiplier": sizing_multiplier,
            "allows_new_dispatch": allows_new_dispatch,
            "halt_threshold": self.halt_threshold,
            "reduce_threshold": self.reduce_threshold,
            "full_halt_threshold": self.full_halt_threshold,
        }

        if level != previous_level:
            log_extra["transition"] = f"{previous_level.value} → {level.value}"
            if level == DrawdownLevel.NORMAL:
                log_level = logging.INFO
            elif level == DrawdownLevel.FULL_HALT:
                log_level = logging.CRITICAL
            else:
                log_level = logging.WARNING
            logger.log(
                log_level,
                "drawdown_level_transition %s → %s (dd=%.4f)",
                previous_level.value,
                level.value,
                dd_pct,
                extra=log_extra,
            )
        else:
            logger.debug(
                "drawdown_assessment level=%s dd=%.4f",
                level.value,
                dd_pct,
                extra=log_extra,
            )

        return DrawdownAssessment(
            current_equity=current_equity,
            peak_equity=peak,
            drawdown_pct=dd_pct,
            level=level,
            sizing_multiplier=sizing_multiplier,
            allows_new_dispatch=allows_new_dispatch,
        )


# ---------------------------------------------------------------------------
# Aggregate drawdown contract (REM-7 / CRO R-7.1)
# ---------------------------------------------------------------------------


class AggregateDDLevel(Enum):
    """Aggregate drawdown ladder rungs per CRO R-7.1."""
    NORMAL = "normal"
    WARN = "warn"           # DD >= 4%: log only
    HALVE = "halve"         # DD >= 8%: aggregate sizing_multiplier = 0.5
    HALT = "halt"           # DD >= 12%: halt new dispatch ALL strategies
    LOCKOUT = "lockout"     # DD >= 15%: force flat ALL strategies; frozen state


@dataclass(frozen=True)
class AggregateDrawdownAssessment:
    """Immutable snapshot of the aggregate drawdown state.

    CRO R-7.1 cross-action composition:
        effective_sizing = min(per_strategy_sizing, aggregate_sizing)
        effective_dispatch_allowed = per_strategy_allows AND aggregate_allows
        effective_force_flat = per_strategy_force_flat OR aggregate_force_flat
    """

    current_aggregate_equity: float
    peak_aggregate_equity: float
    aggregate_drawdown_pct: float    # 0.0 to 1.0; positive means drawdown from peak
    level: AggregateDDLevel
    sizing_multiplier: float         # 1.0 (normal/warn), 0.5 (halve), 0.0 (halt/lockout)
    allows_new_dispatch: bool        # False at HALT and LOCKOUT
    force_flat: bool                 # True only at LOCKOUT
    contributing_strategies: list    # list of strategy_id strings feeding into this assessment


# Sizing multipliers per aggregate level — CRO R-7.1
_AGGREGATE_SIZING_BY_LEVEL: dict[AggregateDDLevel, float] = {
    AggregateDDLevel.NORMAL: 1.0,
    AggregateDDLevel.WARN: 1.0,    # warn only; no sizing change
    AggregateDDLevel.HALVE: 0.5,   # multiplicative halving
    AggregateDDLevel.HALT: 0.0,    # no new dispatch; existing positions held
    AggregateDDLevel.LOCKOUT: 0.0, # force flat; frozen state
}


@dataclass
class AggregateDrawdownContract:
    """Enforces the CRO R-7.1 aggregate drawdown ladder across all strategies.

    The aggregate contract is the LAST line of defense against correlated
    drawdown: 4 strategies each at 8% DD (below 10% per-strategy threshold)
    but aggregate at 18% fires the HALT at 12% and LOCKOUT at 15%.

    This is the LTCM-class defense: per-strategy contracts all pass individually
    but the aggregate book equity has imploded due to correlation.

    Instantiation point: PaperRunnerBase (post-REM-2). In the interim (before
    REM-2 full BaseRunner extraction), both paper scripts instantiate this
    directly and call update_equity() from each strategy's per-bar cycle.

    Clock-and-ordering discipline (CRO R-7.1 BC-REM7-LADDER-3):
        Single broker fetch per cycle. Equity timestamp = broker response
        receive-time. Same timestamp distributed synchronously to:
            (a) AggregateDrawdownContract.update_equity()
            (b) Per-strategy DrawdownContract.assess()
        NOT event-driven on per-fill — that creates a race where the aggregate
        evaluates between two simultaneously-arriving fills and reports an
        inconsistent state.

    Args:
        warn_threshold:     DD fraction at which a WARNING is logged (no action).
                            CRO R-7.1: 0.04 (4%).
        halve_threshold:    DD fraction at which aggregate sizing = 0.5x.
                            CRO R-7.1: 0.08 (8%).
        halt_threshold:     DD fraction at which new dispatch halts for ALL.
                            CRO R-7.1: 0.12 (12%).
        lockout_threshold:  DD fraction at which ALL are forced flat.
                            CRO R-7.1: 0.15 (15%).
        kill_switch:        Optional KillSwitch instance. If provided, HALT triggers
                            kill_switch.trigger(DRAWDOWN_AGGREGATE_HALT) and LOCKOUT
                            triggers kill_switch.trigger(DRAWDOWN_AGGREGATE_LOCKOUT).
        n_strategies_max:   Maximum number of strategies for startup assertion
                            (INV-R7-3 tighter-than-N×per-strategy check).

    INV-R7-3: Startup assertion verifies aggregate thresholds are strictly tighter
    than N × per_strategy_thresholds. This fires at contract instantiation time.
    """

    warn_threshold: float = 0.04      # 4% — CRO R-7.1
    halve_threshold: float = 0.08     # 8% — CRO R-7.1
    halt_threshold: float = 0.12      # 12% — CRO R-7.1
    lockout_threshold: float = 0.15   # 15% — CRO R-7.1

    # Per-strategy thresholds (for INV-R7-3 startup assertion)
    per_strategy_halt_threshold: float = 0.10    # 10% per-strategy halt
    per_strategy_full_halt_threshold: float = 0.20  # 20% per-strategy full halt
    n_strategies_max: int = 4

    # Optional kill switch — if provided, HALT/LOCKOUT call kill_switch.trigger()
    kill_switch: object = None  # KillSwitch | None — avoid circular import

    # F-004 / clock-and-ordering: staleness budget for snapshot timestamps.
    # Snapshots older than this many seconds relative to wall-clock raise
    # StaleEquitySnapshotError. 60s is the contract-level guard per F-004 spec.
    staleness_budget_seconds: float = 60.0

    # Internal state
    _peak_equity: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _last_level: AggregateDDLevel = field(default=AggregateDDLevel.NORMAL, init=False)
    _contributing_strategies: list = field(default_factory=list, init=False)
    # F-004: monotonic timestamp guard — stores the last accepted snapshot_timestamp
    _last_snapshot_timestamp: Optional[datetime] = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Validate thresholds and enforce INV-R7-3 startup assertion."""
        if not (0.0 < self.warn_threshold < self.halve_threshold
                < self.halt_threshold < self.lockout_threshold < 1.0):
            raise ValueError(
                f"AggregateDrawdownContract thresholds must satisfy "
                f"0 < warn({self.warn_threshold}) < halve({self.halve_threshold}) "
                f"< halt({self.halt_threshold}) < lockout({self.lockout_threshold}) < 1.0"
            )

        # INV-R7-3: aggregate thresholds must be strictly tighter than N × per-strategy
        n = self.n_strategies_max
        assert self.halt_threshold < n * self.per_strategy_halt_threshold, (
            f"INV-R7-3 violated: aggregate halt ({self.halt_threshold}) >= "
            f"N×per-strategy halt ({n}×{self.per_strategy_halt_threshold}="
            f"{n * self.per_strategy_halt_threshold}). "
            "Aggregate contract is NOT tighter than individual contracts at N={n}."
        )
        assert self.lockout_threshold < n * self.per_strategy_full_halt_threshold, (
            f"INV-R7-3 violated: aggregate lockout ({self.lockout_threshold}) >= "
            f"N×per-strategy full halt ({n}×{self.per_strategy_full_halt_threshold}="
            f"{n * self.per_strategy_full_halt_threshold})."
        )

    def update_equity(
        self,
        aggregate_equity: float,
        *,
        snapshot_timestamp: Optional[datetime] = None,
        contributing_strategies: Optional[List[str]] = None,
    ) -> AggregateDrawdownAssessment:
        """Update aggregate equity and evaluate the drawdown ladder.

        Called once per bar cycle with the aggregate book equity (cash +
        sum(unrealized P&L) across ALL strategies). The caller owns the clock
        and must ensure single broker fetch per cycle (clock-and-ordering discipline).

        F-004 / clock-and-ordering: snapshot_timestamp is keyword-required and
        enforces two contract-level invariants:
            (a) Monotonicity: each call's timestamp must be >= the previous call's.
                A non-monotonic timestamp indicates out-of-order delivery or a
                duplicated snapshot — raises StaleEquitySnapshotError.
            (b) Staleness: the timestamp must be within staleness_budget_seconds
                (default 60s) of wall-clock time now. A stale snapshot (e.g. from
                a broker cache hit on a stale value) raises StaleEquitySnapshotError.

        Args:
            aggregate_equity: Total book equity across all strategies (USD).
            snapshot_timestamp: UTC datetime when the broker equity snapshot was
                received. Keyword-only. If None, wall-clock now() is used (for
                backwards-compatibility during the REM-2 full-extraction migration);
                a WARNING is emitted when omitted.
            contributing_strategies: List of strategy_id strings that contributed
                to this equity snapshot (for observability).

        Returns:
            AggregateDrawdownAssessment with level, sizing_multiplier, and actions.

        Raises:
            StaleEquitySnapshotError: timestamp is non-monotonic or stale.
        """
        contrib = contributing_strategies or []

        # F-004: resolve snapshot timestamp; warn if not provided (caller discipline gap)
        now_utc = datetime.now(timezone.utc)
        if snapshot_timestamp is None:
            logger.warning(
                "aggregate_drawdown_contract.update_equity called without "
                "snapshot_timestamp — defaulting to wall-clock now. "
                "F-004: callers should pass snapshot_timestamp=<broker_receive_time> "
                "to enforce clock-and-ordering invariant.",
                extra={
                    "event": "AGGREGATE_EQUITY_NO_TIMESTAMP",
                    "wall_clock_now": now_utc.isoformat(),
                },
            )
            snapshot_timestamp = now_utc

        # Ensure snapshot_timestamp is timezone-aware for comparison
        if snapshot_timestamp.tzinfo is None:
            snapshot_timestamp = snapshot_timestamp.replace(tzinfo=timezone.utc)

        # (a) Monotonicity check
        with self._lock:
            last_ts = self._last_snapshot_timestamp

        if last_ts is not None and snapshot_timestamp < last_ts:
            raise StaleEquitySnapshotError(
                f"Non-monotonic snapshot_timestamp: received {snapshot_timestamp.isoformat()} "
                f"which is before last accepted {last_ts.isoformat()}. "
                "F-004: clock-and-ordering violation — out-of-order or duplicated snapshot."
            )

        # (b) Staleness check: snapshot must be within staleness_budget_seconds of now
        staleness_seconds = (now_utc - snapshot_timestamp).total_seconds()
        if staleness_seconds > self.staleness_budget_seconds:
            raise StaleEquitySnapshotError(
                f"Stale equity snapshot: snapshot_timestamp={snapshot_timestamp.isoformat()} "
                f"is {staleness_seconds:.1f}s behind wall-clock now={now_utc.isoformat()} "
                f"(budget={self.staleness_budget_seconds}s). "
                "F-004: potential broker cache hit on stale equity value."
            )

        with self._lock:
            if aggregate_equity > self._peak_equity:
                self._peak_equity = aggregate_equity
            peak = self._peak_equity
            self._contributing_strategies = list(contrib)
            previous_level = self._last_level
            self._last_snapshot_timestamp = snapshot_timestamp

        if peak <= 0.0:
            dd_pct = 0.0
            level = AggregateDDLevel.NORMAL
        else:
            dd_pct = max(0.0, (peak - aggregate_equity) / peak)

            if dd_pct >= self.lockout_threshold:
                level = AggregateDDLevel.LOCKOUT
            elif dd_pct >= self.halt_threshold:
                level = AggregateDDLevel.HALT
            elif dd_pct >= self.halve_threshold:
                level = AggregateDDLevel.HALVE
            elif dd_pct >= self.warn_threshold:
                level = AggregateDDLevel.WARN
            else:
                level = AggregateDDLevel.NORMAL

        sizing_multiplier = _AGGREGATE_SIZING_BY_LEVEL[level]
        allows_new_dispatch = level not in (AggregateDDLevel.HALT, AggregateDDLevel.LOCKOUT)
        force_flat = level == AggregateDDLevel.LOCKOUT

        with self._lock:
            self._last_level = level

        # Observability: log aggregate equity state at DEBUG per REM-7 boundary
        logger.debug(
            "aggregate_drawdown_assessment aggregate_equity=%.2f aggregate_peak=%.2f "
            "aggregate_drawdown_pct=%.4f level=%s contributing_strategies=%s",
            aggregate_equity,
            peak,
            dd_pct,
            level.value,
            contrib,
        )

        # Observability: log transitions and action levels at appropriate severity
        if level != previous_level:
            log_extra = {
                "event": "AGGREGATE_DRAWDOWN_TRANSITION",
                "contract_type": "aggregate",
                "strategy_id": None,
                "current_drawdown_pct": round(dd_pct, 6),
                "threshold_pct": self.halt_threshold if level == AggregateDDLevel.HALT
                    else self.lockout_threshold if level == AggregateDDLevel.LOCKOUT
                    else self.halve_threshold,
                "peak_equity": peak,
                "current_equity": aggregate_equity,
                "level": level.value,
                "previous_level": previous_level.value,
            }
            if level == AggregateDDLevel.LOCKOUT:
                logger.critical(
                    "AGGREGATE_DRAWDOWN_LOCKOUT dd=%.4f threshold=%.4f "
                    "contributing_strategies=%s — ALL strategies force-flat; "
                    "pending CRO review",
                    dd_pct, self.lockout_threshold, contrib,
                    extra=log_extra,
                )
            elif level == AggregateDDLevel.HALT:
                logger.critical(
                    "AGGREGATE_DRAWDOWN_HALT dd=%.4f threshold=%.4f "
                    "contributing_strategies=%s — halting new dispatch ALL strategies",
                    dd_pct, self.halt_threshold, contrib,
                    extra=log_extra,
                )
            elif level == AggregateDDLevel.HALVE:
                logger.warning(
                    "AGGREGATE_DRAWDOWN_HALVE dd=%.4f threshold=%.4f — "
                    "aggregate sizing_multiplier=0.5 for ALL strategies",
                    dd_pct, self.halve_threshold,
                    extra=log_extra,
                )
            elif level == AggregateDDLevel.WARN:
                logger.warning(
                    "AGGREGATE_DRAWDOWN_WARN dd=%.4f threshold=%.4f — warn only",
                    dd_pct, self.warn_threshold,
                    extra=log_extra,
                )
            else:
                logger.info(
                    "AGGREGATE_DRAWDOWN_NORMAL dd=%.4f (recovered from %s)",
                    dd_pct, previous_level.value,
                    extra=log_extra,
                )

        # Trigger kill switch on HALT and LOCKOUT per CRO R-7.1 BC-REM7-LADDER-5
        if self.kill_switch is not None:
            ks = self.kill_switch
            if level == AggregateDDLevel.HALT and not ks.is_triggered:
                from forex_system.risk.kill_switch import TriggerReason
                ks.trigger(
                    TriggerReason.DRAWDOWN_AGGREGATE_HALT,
                    f"aggregate_dd={dd_pct:.4f} >= halt_threshold={self.halt_threshold:.4f}",
                    equity=aggregate_equity,
                )
            elif level == AggregateDDLevel.LOCKOUT and not ks.is_triggered:
                from forex_system.risk.kill_switch import TriggerReason
                ks.trigger(
                    TriggerReason.DRAWDOWN_AGGREGATE_LOCKOUT,
                    f"aggregate_dd={dd_pct:.4f} >= lockout_threshold={self.lockout_threshold:.4f}",
                    equity=aggregate_equity,
                )

        return AggregateDrawdownAssessment(
            current_aggregate_equity=aggregate_equity,
            peak_aggregate_equity=peak,
            aggregate_drawdown_pct=dd_pct,
            level=level,
            sizing_multiplier=sizing_multiplier,
            allows_new_dispatch=allows_new_dispatch,
            force_flat=force_flat,
            contributing_strategies=contrib,
        )

    @property
    def current_level(self) -> AggregateDDLevel:
        """Current aggregate drawdown level."""
        with self._lock:
            return self._last_level


# ---------------------------------------------------------------------------
# F-010 / INV-R7-1: Production composition function
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractAssessment:
    """Normalised view of either a per-strategy or aggregate assessment.

    Both DrawdownAssessment and AggregateDrawdownAssessment carry these three
    fields; this dataclass gives compose_dispatch_decision a uniform interface.
    """
    sizing: float
    dispatch_allowed: bool
    force_flat: bool


@dataclass(frozen=True)
class ComposedDecision:
    """Result of compose_dispatch_decision — the effective risk-envelope decision.

    CRO R-7.1 cross-action composition rules:
        effective_sizing          = min(per_strategy.sizing, aggregate.sizing)
        effective_dispatch_allowed = per_strategy.dispatch_allowed AND aggregate.dispatch_allowed
        effective_force_flat       = per_strategy.force_flat OR aggregate.force_flat
    """
    effective_sizing: float
    effective_dispatch_allowed: bool
    effective_force_flat: bool


def compose_dispatch_decision(
    per_strategy_assess: ContractAssessment,
    aggregate_assess: ContractAssessment,
) -> ComposedDecision:
    """Apply CRO R-7.1 cross-action composition rule to produce the effective decision.

    This is the PRODUCTION function that a paper-loop caller MUST use when
    combining per-strategy and aggregate drawdown assessments. Tests MUST call
    this function (not re-implement the rule inline) to verify production behaviour.

    Rules (CRO R-7.1, INV-R7-1):
        effective_sizing          = min(per_strategy_assess.sizing, aggregate_assess.sizing)
        effective_dispatch_allowed = per_strategy_assess.dispatch_allowed
                                     AND aggregate_assess.dispatch_allowed
        effective_force_flat       = per_strategy_assess.force_flat
                                     OR aggregate_assess.force_flat

    Args:
        per_strategy_assess: ContractAssessment from the per-strategy DrawdownContract.
        aggregate_assess:    ContractAssessment from the AggregateDrawdownContract.

    Returns:
        ComposedDecision with the effective sizing, dispatch_allowed, and force_flat.
    """
    effective_sizing = min(per_strategy_assess.sizing, aggregate_assess.sizing)
    effective_dispatch_allowed = (
        per_strategy_assess.dispatch_allowed and aggregate_assess.dispatch_allowed
    )
    effective_force_flat = per_strategy_assess.force_flat or aggregate_assess.force_flat

    logger.debug(
        "compose_dispatch_decision "
        "per_strategy_sizing=%.2f per_strategy_dispatch=%s per_strategy_flat=%s "
        "aggregate_sizing=%.2f aggregate_dispatch=%s aggregate_flat=%s "
        "effective_sizing=%.2f effective_dispatch=%s effective_flat=%s",
        per_strategy_assess.sizing, per_strategy_assess.dispatch_allowed,
        per_strategy_assess.force_flat,
        aggregate_assess.sizing, aggregate_assess.dispatch_allowed,
        aggregate_assess.force_flat,
        effective_sizing, effective_dispatch_allowed, effective_force_flat,
    )

    return ComposedDecision(
        effective_sizing=effective_sizing,
        effective_dispatch_allowed=effective_dispatch_allowed,
        effective_force_flat=effective_force_flat,
    )
