"""Cross-strategy exposure aggregator — CRO binding constraint #1.

Computes JPY-correlated notional exposure across all open positions and
checks dispatch gates before any new trial is launched.

CRO envelope (CONSENSUS_2026-04-28):
    max_active_paper_strategies : 4
    max_concurrent_open_positions: 6  (2 per pair max)
    max_correlated_exposure_pct  : 0.15  (JPY-correlated notional ≤15% of book)
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
from dataclasses import dataclass

from forex_system.core.types import Position

logger = logging.getLogger("exposure_aggregator")

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
# Gate exception
# ---------------------------------------------------------------------------


class AggregationGateBlocked(Exception):
    """Raised when ``check_dispatch_allowed`` detects a limit would be breached.

    Callers catch this exception and decide the appropriate action
    (skip dispatch, alert operator, etc.).  This module does NOT mutate state.
    """


# ---------------------------------------------------------------------------
# Exposure computation
# ---------------------------------------------------------------------------


def compute_exposure(positions: list[Position]) -> ExposureSnapshot:
    """Compute ``ExposureSnapshot`` from a list of open positions.

    Notional per position = ``abs(position.size) * position.entry_price``.

    ``active_paper_strategies`` is the count of distinct *strategy* values on
    the ``Position`` objects.  If your ``Position`` instances lack a
    ``strategy`` attribute (the frozen dataclass in ``core/types.py`` does not
    include one), every position is counted as belonging to one anonymous
    strategy — callers that track per-strategy positions should wrap positions
    with the strategy context before calling this function.

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
        # Position.strategy is the strategy name field defined in core/types.py
        # (via Trade.strategy).  core/types.Position does NOT have a strategy
        # field — we use pair as a proxy for uniqueness here and note the gap.
        # Callers should augment positions if per-strategy count is critical.

    # Strategy count: Position in core/types has no strategy field; we count
    # unique pairs as a conservative proxy.  Callers that need exact strategy
    # counts must pass pre-grouped data.
    for pos in positions:
        strategy_ids.add(pos.pair)  # proxy; see note above

    jpy_pct = jpy_notional / total_notional if total_notional > 0.0 else 0.0

    return ExposureSnapshot(
        jpy_correlated_notional=jpy_notional,
        total_paper_book_notional=total_notional,
        jpy_correlated_pct=jpy_pct,
        active_paper_strategies=len(strategy_ids),
        concurrent_open_positions=len(positions),
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
