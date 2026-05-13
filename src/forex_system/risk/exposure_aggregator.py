"""Cross-strategy exposure aggregator — CRO binding constraints.

Computes JPY-correlated notional exposure across all open positions and
checks dispatch gates before any new trial is launched.

CRO envelope (CONSENSUS_2026-04-28 + REM-5 R-5.1):
    max_active_paper_strategies : 4
    max_concurrent_open_positions: 6  (2 per pair max)
    max_correlated_exposure_pct  : 0.15  (JPY-correlated notional ≤15% of book)
    per_strategy_correlated_pct  : 0.0375  (0.15/4; per REM-5 R-5.1 equal-weight)
    size_multiplier              : 0.5   (effective risk_per_trade_pct = 1%)
    Drawdown contract            : ≥10% → halt new dispatch | ≥15% → 0.5x sizing
                                   | ≥20% → full halt pending CRO review

IMPORTANT: Limits are NEVER hard-coded here — callers must pass them explicitly
so that the source-of-truth remains the typed consensus artifact.  The defaults
on ``check_dispatch_allowed`` match the CONSENSUS document only for
*documentation* purposes; production callers must provide them.

JPY-correlated pairs (per CRO note, universe EURUSD/USDJPY/GBPUSD):
    USDJPY — direct
    GBPUSD — indirect, via shared JPY tail risk
    EURUSD — no JPY exposure

REM-5 (CRO R-5.1) — per-strategy allocation rule:
    Algorithm: equal-weight-cap-per-strategy.
    per_strategy_cap = max_correlated_pct / max_active_strategies (default 0.15/4 = 0.0375).
    On breach: raise AllocationGateBlocked (distinct from AggregationGateBlocked).
    No partial allocation; no queueing (execution-firewall violation if either).
    Tie-break: strategy_id lexicographic, secondary by request receive-time monotonic.
    NOT lock-acquisition order (clock-and-ordering anti-pattern).

    INV-R5-1: sum(strategy_jpy_correlated_notional) ≤ 0.15 * book_equity AND
              per-strategy ≤ 0.0375 * book_equity.
    INV-R5-2: count(active) ≤ 4.
    INV-R5-3: tie-break is deterministic given identical inputs.

    fairness_rule_version: "equal-weight-cap-r5.1-2026-05-13"

Design:
    - Pure functions; no state mutations.
    - All decisions logged via ``logging.getLogger("exposure_aggregator")``
      at INFO level (allowed) or WARNING level (blocked) with full field trace.
    - ``compute_exposure`` derives notional from ``position.size * position.entry_price``.
      For the cross-rate assumption we treat size as units of base currency and
      entry_price as units of quote currency per unit base; notional = size * price.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from forex_system.core.types import Position

logger = logging.getLogger("exposure_aggregator")

# REM-5 fairness rule version — logged with every allocation decision so
# post-hoc reconstruction can identify which rule version applied.
_FAIRNESS_RULE_VERSION = "equal-weight-cap-r5.1-2026-05-13"

# ---------------------------------------------------------------------------
# JPY-correlation table (only FX-domain knowledge in this module)
# ---------------------------------------------------------------------------

_JPY_CORRELATED: frozenset[str] = frozenset({"USDJPY", "GBPUSD"})


def is_jpy_correlated(pair: str) -> bool:
    """Return True if *pair* carries JPY tail risk.

    Per CRO envelope (CONSENSUS_2026-04-28):
        USDJPY — direct JPY exposure
        GBPUSD — indirect, shared JPY tail risk
        EURUSD — no direct JPY exposure → False
    """
    return pair.upper() in _JPY_CORRELATED


# ---------------------------------------------------------------------------
# Snapshot dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExposureSnapshot:
    """Aggregated cross-strategy exposure at a single point in time."""

    jpy_correlated_notional: float      # Absolute USD notional in JPY-correlated pairs
    total_paper_book_notional: float    # Absolute USD notional across all open positions
    jpy_correlated_pct: float           # = jpy_correlated_notional / total (0.0 if total == 0)
    active_paper_strategies: int        # Distinct strategy_id values across positions
    concurrent_open_positions: int      # Total open position count


# ---------------------------------------------------------------------------
# Gate exceptions
# ---------------------------------------------------------------------------


class AggregationGateBlocked(Exception):
    """Raised when ``check_dispatch_allowed`` detects a limit would be breached.

    Callers catch this exception and decide the appropriate action
    (skip dispatch, alert operator, etc.).  This module does NOT mutate state.
    """


class AllocationGateBlocked(Exception):
    """Raised when a per-strategy JPY-correlated cap is breached.

    REM-5 / CRO R-5.1: DISTINCT from AggregationGateBlocked (which is the
    aggregate gate). AllocationGateBlocked is the per-strategy gate.

    The caller MUST NOT partial-allocate or queue the request — the strategy's
    declared signal must be honoured in full or refused in full.
    Partial fills are an execution-firewall violation.
    """


# ---------------------------------------------------------------------------
# Exposure computation
# ---------------------------------------------------------------------------


def compute_exposure(positions: list[Position]) -> ExposureSnapshot:
    """Compute ``ExposureSnapshot`` from a list of open positions.

    Notional per position = ``abs(position.size) * position.entry_price``.

    REM-1 / D-1.2: ``active_paper_strategies`` now uses ``Position.strategy_id``
    (the str field added in REM-1) rather than the pair-as-proxy workaround.
    If strategy_id is empty string "", it is counted as one anonymous strategy.

    Args:
        positions: All currently open positions across all strategies.

    Returns:
        Immutable ``ExposureSnapshot`` for the current bar.
    """
    total_notional = 0.0
    jpy_notional = 0.0
    strategy_ids: set[str] = set()

    for pos in positions:
        notional = abs(pos.size) * pos.entry_price
        total_notional += notional
        if is_jpy_correlated(pos.pair):
            jpy_notional += notional
        # REM-1: use Position.strategy_id (str field) — no longer a pair-as-proxy workaround
        strategy_ids.add(pos.strategy_id if pos.strategy_id else "__anonymous__")

    jpy_pct = jpy_notional / total_notional if total_notional > 0.0 else 0.0

    return ExposureSnapshot(
        jpy_correlated_notional=jpy_notional,
        total_paper_book_notional=total_notional,
        jpy_correlated_pct=jpy_pct,
        active_paper_strategies=len(strategy_ids),
        concurrent_open_positions=len(positions),
    )


def compute_per_strategy_exposure(
    positions: list[Position],
) -> dict[str, dict[str, float]]:
    """Compute per-strategy exposure breakdown keyed by strategy_id.

    Returns:
        dict[strategy_id, {"jpy_notional": float, "total_notional": float}]
    """
    result: dict[str, dict[str, float]] = {}
    for pos in positions:
        sid = pos.strategy_id if pos.strategy_id else "__anonymous__"
        notional = abs(pos.size) * pos.entry_price
        if sid not in result:
            result[sid] = {"jpy_notional": 0.0, "total_notional": 0.0}
        result[sid]["total_notional"] += notional
        if is_jpy_correlated(pos.pair):
            result[sid]["jpy_notional"] += notional
    return result


# ---------------------------------------------------------------------------
# Per-strategy allocation gate (REM-5)
# ---------------------------------------------------------------------------


def check_per_strategy_allocation(
    strategy_id: str,
    requested_jpy_notional: float,
    existing_positions: list[Position],
    book_equity: float,
    max_correlated_pct: float = 0.15,
    max_active_strategies: int = 4,
    receive_time: Optional[float] = None,
) -> None:
    """Check per-strategy JPY-correlated cap per CRO R-5.1 equal-weight rule.

    Algorithm (CRO R-5.1):
        per_strategy_cap = max_correlated_pct / max_active_strategies
        If strategy's existing JPY notional + requested > per_strategy_cap * book_equity:
            raise AllocationGateBlocked

    Tie-break (INV-R5-3 determinism):
        strategy_id lexicographic primary, receive_time monotonic secondary.
        This is enforced structurally: each strategy gets its own allocation slot
        equal to max_correlated_pct / max_active_strategies regardless of order.

    Observability: logs strategy_id + requested_exposure + allocated_exposure +
    cap_applied + fairness_rule_version at INFO (allowed) or WARNING (blocked).

    Args:
        strategy_id: The requesting strategy's ID.
        requested_jpy_notional: The new JPY-correlated notional the strategy wants to add.
        existing_positions: All current open positions (all strategies).
        book_equity: Current book equity in USD (used to compute the cap).
        max_correlated_pct: Aggregate cap (default 0.15 = 15%).
        max_active_strategies: Denominator for equal-weight split (default 4).
        receive_time: Monotonic clock at request receive time; used only for logging
                      (INV-R5-3: tie-break is lexicographic on strategy_id first).

    Raises:
        AllocationGateBlocked: Per-strategy cap would be exceeded.
    """
    per_strategy_cap_notional = (max_correlated_pct / max_active_strategies) * book_equity
    per_strategy_cap_pct = max_correlated_pct / max_active_strategies

    # Compute current per-strategy JPY exposure from existing positions
    per_strategy = compute_per_strategy_exposure(existing_positions)
    current_jpy = per_strategy.get(strategy_id, {}).get("jpy_notional", 0.0)
    projected_jpy = current_jpy + requested_jpy_notional
    allocated = max(0.0, per_strategy_cap_notional - current_jpy)

    _log_fields = (
        f"strategy_id={strategy_id} "
        f"requested_jpy_notional={requested_jpy_notional:.2f} "
        f"current_jpy_notional={current_jpy:.2f} "
        f"projected_jpy_notional={projected_jpy:.2f} "
        f"per_strategy_cap_notional={per_strategy_cap_notional:.2f} "
        f"per_strategy_cap_pct={per_strategy_cap_pct:.4f} "
        f"book_equity={book_equity:.2f} "
        f"fairness_rule_version={_FAIRNESS_RULE_VERSION} "
        f"receive_time={receive_time or time.monotonic():.6f}"
    )

    if projected_jpy > per_strategy_cap_notional:
        msg = (
            f"ALLOCATION_BLOCKED {_log_fields} | "
            f"reason=per_strategy_jpy_cap_exceeded "
            f"allocated_notional={allocated:.2f}"
        )
        logger.warning(
            "exposure_aggregator.allocation_blocked strategy_id=%s "
            "requested_exposure=%.2f allocated_exposure=%.2f "
            "cap_applied=%.4f fairness_rule_version=%s",
            strategy_id, requested_jpy_notional, allocated,
            per_strategy_cap_pct, _FAIRNESS_RULE_VERSION,
        )
        raise AllocationGateBlocked(msg)

    # F-003 / INV-R5-1 aggregate-sum conjunct: even if the per-strategy cap is
    # satisfied, check that the SUM of all strategies' JPY notional (existing +
    # this request) does not exceed max_correlated_pct * book_equity.
    # This prevents a caller from calling check_per_strategy_allocation without
    # also calling check_dispatch_allowed and inadvertently violating the aggregate cap.
    aggregate_cap_notional = max_correlated_pct * book_equity
    existing_jpy_all_strategies = sum(
        v["jpy_notional"] for v in compute_per_strategy_exposure(existing_positions).values()
    )
    # Include this strategy's current exposure + requested
    other_strategies_jpy = existing_jpy_all_strategies - per_strategy.get(strategy_id, {}).get(
        "jpy_notional", 0.0
    )
    projected_aggregate_jpy = other_strategies_jpy + projected_jpy
    if projected_aggregate_jpy > aggregate_cap_notional:
        msg = (
            f"ALLOCATION_BLOCKED {_log_fields} | "
            f"reason=aggregate_sum_cap_exceeded "
            f"projected_aggregate_jpy={projected_aggregate_jpy:.2f} "
            f"aggregate_cap_notional={aggregate_cap_notional:.2f}"
        )
        logger.warning(
            "exposure_aggregator.allocation_blocked_aggregate_sum strategy_id=%s "
            "requested_exposure=%.2f projected_aggregate_jpy=%.2f "
            "aggregate_cap_notional=%.2f fairness_rule_version=%s",
            strategy_id, requested_jpy_notional, projected_aggregate_jpy,
            aggregate_cap_notional, _FAIRNESS_RULE_VERSION,
        )
        raise AllocationGateBlocked(msg)

    logger.info(
        "exposure_aggregator.allocation_allowed strategy_id=%s "
        "requested_exposure=%.2f allocated_exposure=%.2f "
        "cap_applied=%.4f fairness_rule_version=%s",
        strategy_id, requested_jpy_notional, projected_jpy,
        per_strategy_cap_pct, _FAIRNESS_RULE_VERSION,
    )


# ---------------------------------------------------------------------------
# Dispatch gate
# ---------------------------------------------------------------------------


def check_dispatch_allowed(
    snapshot: ExposureSnapshot,
    max_correlated_pct: float = 0.15,
    max_active_strategies: int = 4,
    max_concurrent_positions: int = 6,
) -> None:
    """Check all CRO dispatch limits. Raises ``AggregationGateBlocked`` on breach.

    Logs a structured decision-trace line for every call (allow OR block) so
    that the dispatch gate history is fully reconstructible from log output
    alone — per ``log-as-decision-trace`` discipline.

    **Limits must be passed by the caller** — the defaults shown above are the
    CONSENSUS_2026-04-28 values for documentation purposes only.  Production
    callers must pass them explicitly from the typed consensus artifact to
    avoid silent drift.

    Checks performed (first breach raises, remaining checks are skipped):
        1. JPY-correlated notional ≤ ``max_correlated_pct`` of total book
        2. Active paper strategies ≤ ``max_active_strategies``
        3. Concurrent open positions ≤ ``max_concurrent_positions``

    Args:
        snapshot: Exposure snapshot from ``compute_exposure``.
        max_correlated_pct: CRO envelope limit for JPY-correlated notional
            as a fraction of total book (e.g., 0.15 = 15%).
        max_active_strategies: CRO envelope limit on concurrent active strategies.
        max_concurrent_positions: CRO envelope limit on total open positions.

    Raises:
        AggregationGateBlocked: If any limit would be breached.
    """
    _fields = (
        f"jpy_correlated_pct={snapshot.jpy_correlated_pct:.4f} "
        f"active_strategies={snapshot.active_paper_strategies} "
        f"open_positions={snapshot.concurrent_open_positions} "
        f"limits=({max_correlated_pct},{max_active_strategies},{max_concurrent_positions})"
    )

    # Check 1: JPY-correlated exposure
    if snapshot.jpy_correlated_pct > max_correlated_pct:
        msg = (
            f"DISPATCH_BLOCKED jpy_correlated_pct={snapshot.jpy_correlated_pct:.4f} "
            f"exceeds max_correlated_pct={max_correlated_pct} | {_fields}"
        )
        logger.warning(msg)
        raise AggregationGateBlocked(msg)

    # Check 2: Active strategies
    if snapshot.active_paper_strategies > max_active_strategies:
        msg = (
            f"DISPATCH_BLOCKED active_strategies={snapshot.active_paper_strategies} "
            f"exceeds max_active_strategies={max_active_strategies} | {_fields}"
        )
        logger.warning(msg)
        raise AggregationGateBlocked(msg)

    # Check 3: Concurrent open positions
    if snapshot.concurrent_open_positions > max_concurrent_positions:
        msg = (
            f"DISPATCH_BLOCKED open_positions={snapshot.concurrent_open_positions} "
            f"exceeds max_concurrent_positions={max_concurrent_positions} | {_fields}"
        )
        logger.warning(msg)
        raise AggregationGateBlocked(msg)

    # All checks passed
    logger.info("DISPATCH_ALLOWED | %s", _fields)
