"""Transaction cost modeling — the make-or-break of Phase 0.

Realistic costs determine whether apparent alpha survives to become real edge.

ROLLOVER-AWARE SWAP (CRO CM-2)
-------------------------------
FX swap / financing is charged ONLY when a position hold crosses the 22:00 UTC
daily rollover boundary (Wednesday 22:00 UTC counts triple for the T+2 weekend
roll).  An intraday position opened and closed within a single session pays ZERO
swap; a position held across 22:00 UTC pays the full daily swap (3× on Wed).

WEEKEND ROLLOVER RULE (fix-round-1):
Fri 22:00, Sat 22:00, and Sun 22:00 UTC are NOT counted as rollover boundaries.
The FX market is closed Fri 21:00 → Sun 22:00 UTC (aligns with quality_gate_1h
_WEEKEND_CLOSED_DAY_HOUR definition).  The T+2 weekend settlement cost for
Sat/Sun is PRE-PAID by the Wednesday 22:00 triple charge; no additional Sat/Sun
charge accrues.  A hold from Fri to Mon with no Wednesday crossing in the window
therefore incurs ZERO rollover cost.

DST note: rollover is anchored at 22:00 UTC.  Broker convention varies; we use
strict UTC throughout.  This is a simplification acknowledged here (CRO CM-2).

Pro-rating daily swap by hours_held/24 is the BANNED ANTI-PATTERN (CRO CM-2):
it silently under-charges multi-session holds and over-charges intra-session
holds.  Use RolloverAwareRealisticCostModel for 1h intraday backtests.

The existing RealisticCostModel.holding_cost(pair, direction, days) is KEPT
UNCHANGED for daily-bar backtests — its pro-rata semantics are correct at daily
resolution (each bar IS one rollover crossing).
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from forex_system.core.constants import DEFAULT_PAIRS
from forex_system.core.interfaces import CostModel
from forex_system.core.types import Direction, PairInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rollover boundary helpers
# ---------------------------------------------------------------------------

# FX daily rollover: 22:00 UTC.  Wednesday (weekday 2) carries triple charge.
_ROLLOVER_HOUR_UTC = 22


def count_rollover_crossings(
    entry_ts: pd.Timestamp | datetime,
    exit_ts: pd.Timestamp | datetime,
) -> tuple[int, int]:
    """Count how many 22:00 UTC rollover boundaries fall in (entry_ts, exit_ts].

    Returns (n_single, n_triple) where:
      n_single : rollover boundaries that carry 1× daily swap charge
      n_triple : Wednesday 22:00 UTC boundaries that carry 3× charge (weekend roll)

    A position opened at exactly 22:00 UTC does NOT cross that rollover (the bar
    that caused the open is the 22:00 bar; the NEXT rollover is 23 hours away).
    We count boundaries STRICTLY AFTER entry and up to AND INCLUDING exit.

    WEEKEND RULE: Saturday (weekday 5) and Sunday (weekday 6) 22:00 UTC are NOT
    counted as rollover boundaries — the FX market is closed Fri 21:00 → Sun 22:00
    UTC (identical to quality_gate_1h._WEEKEND_CLOSED_DAY_HOUR).  Friday 22:00 UTC
    (weekday 4, hour 22) is also market-closed and therefore skipped.  The T+2
    weekend financing cost is pre-paid by the Wednesday triple charge; no additional
    Sat/Sun charge accrues.

    Clock discipline:
      - All timestamps must be UTC-aware.  If tz-naive, UTC is assumed.
      - The triple charge fires on Wednesday 22:00 UTC (weekday==2, hour==22)
        to account for the Saturday+Sunday settlement dates (T+2 convention).
      - Rollover is anchored strictly at 22:00 UTC (DST simplification; see module
        docstring).
    """
    # Normalise to UTC-aware datetime
    entry_dt = _to_utc_dt(entry_ts)
    exit_dt = _to_utc_dt(exit_ts)

    if exit_dt <= entry_dt:
        return 0, 0

    n_single = 0
    n_triple = 0

    # Walk from the first candidate rollover after entry_dt
    # Candidate = next 22:00 UTC on or after (entry_dt + 1 min)
    # to ensure we start strictly after entry.
    candidate = _next_rollover_at_or_after(entry_dt, strict_after=True)

    while candidate <= exit_dt:
        wd = candidate.weekday()  # 0=Mon … 6=Sun
        # Skip weekend-closed 22:00 boundaries.  The FX market is closed on
        # Friday 22:00 UTC (wd=4), Saturday 22:00 UTC (wd=5), and Sunday 22:00
        # UTC (wd=6).  These align with quality_gate_1h._WEEKEND_CLOSED_DAY_HOUR
        # which marks Fri 21-23, all Sat, and Sun 00-21 as closed.  Sunday 22:00
        # is the market OPEN (not a financing boundary).
        if wd not in (4, 5, 6):
            if wd == 2:  # Wednesday
                n_triple += 1
            else:
                n_single += 1
        # Advance by exactly 24 hours to reach the next day's 22:00 UTC.
        # Using timedelta(days=1) is correct: FX swap ignores DST (UTC-only).
        candidate = candidate + timedelta(days=1)

    return n_single, n_triple


def _to_utc_dt(ts: pd.Timestamp | datetime) -> datetime:
    """Convert a Timestamp or datetime to a tz-aware UTC datetime."""
    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        elif str(ts.tz) not in ("UTC", "utc"):
            ts = ts.tz_convert("UTC")
        return ts.to_pydatetime()
    # Plain datetime
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _next_rollover_at_or_after(dt: datetime, *, strict_after: bool = False) -> datetime:
    """Return the next 22:00 UTC on or after (or strictly after) dt."""
    candidate = dt.replace(hour=_ROLLOVER_HOUR_UTC, minute=0, second=0, microsecond=0)
    if strict_after and candidate <= dt:
        candidate += timedelta(days=1)
    elif not strict_after and candidate < dt:
        candidate += timedelta(days=1)
    return candidate


# ---------------------------------------------------------------------------
# Cost models
# ---------------------------------------------------------------------------


class RealisticCostModel(CostModel):
    """Fixed spread + slippage + commission + daily swap costs.

    Per-pair parameters from config or defaults.

    NOTE: holding_cost pro-rates swap linearly by ``days``.  This is CORRECT
    for daily-bar backtests (each bar IS one rollover).  For 1h intraday
    backtests use RolloverAwareRealisticCostModel.
    """

    def __init__(self, pair_configs: dict[str, PairInfo] | None = None):
        self.pairs = pair_configs or DEFAULT_PAIRS

    def _get_pair(self, pair: str) -> PairInfo:
        p = self.pairs.get(pair.upper())
        if p is None:
            raise ValueError(f"No cost config for pair: {pair}")
        return p

    def entry_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Cost in pips to enter a position (half spread + slippage).

        ``timestamp`` is accepted for interface compatibility but ignored — this
        model uses a fixed per-pair spread.
        """
        p = self._get_pair(pair)
        return p.spread_pips / 2.0 + p.slippage_pips

    def exit_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        """Cost in pips to exit (half spread + slippage + commission). ``timestamp`` ignored."""
        p = self._get_pair(pair)
        return p.spread_pips / 2.0 + p.slippage_pips + p.commission_pips

    def holding_cost(self, pair: str, direction: Direction, days: float) -> float:
        """Swap cost in pips for holding a position over N calendar days.

        Pro-rates daily swap linearly by ``days``.  Correct for daily bars;
        use RolloverAwareRealisticCostModel for 1h intraday positions.
        """
        p = self._get_pair(pair)
        if direction == Direction.LONG:
            daily_swap = p.swap_long_pips_per_day
        elif direction == Direction.SHORT:
            daily_swap = p.swap_short_pips_per_day
        else:
            return 0.0
        # Negative swap = cost, positive swap = income
        # Return as cost (positive = money lost)
        return -daily_swap * days

    def round_trip_cost(self, pair: str, size: float) -> float:
        """Total cost in pips for entering and exiting a position (excluding swap)."""
        return self.entry_cost(pair, size) + self.exit_cost(pair, size)


class RolloverAwareRealisticCostModel(RealisticCostModel):
    """Rollover-aware cost model for 1h intraday backtests.  CRO CM-2.

    Swap / financing is charged ONLY on 22:00 UTC rollover crossings:
      - 1× daily swap per standard rollover (Mon-Tue, Thu-Fri, Sun)
      - 3× daily swap on Wednesday 22:00 UTC (T+2 weekend settlement roll)
      - 0 swap for positions opened and closed within a single session

    USAGE (per-bar accrual pattern, continuous engine mode)
    -------------------------------------------------------
    On each 1h bar where a position is open, call:

        cost_pips = model.rollover_cost_for_bar(pair, direction, bar_ts)

    ``bar_ts`` is the bar's UTC timestamp (the bar CLOSES at bar_ts + 1h;
    the rollover is counted if the close crosses 22:00 UTC, i.e. bar_ts.hour == 21).

    USAGE (discrete mode — trade-level lump sum)
    --------------------------------------------
    Supply entry_ts and exit_ts to holding_cost:

        cost_pips = model.holding_cost(pair, direction, days=0,
                                       entry_ts=entry, exit_ts=exit)

    The ``days`` argument is IGNORED when entry_ts and exit_ts are provided.
    When called without timestamps (backwards-compatibility), falls back to the
    pro-rata RealisticCostModel.holding_cost(pair, direction, days) — this case
    should only arise in daily-bar contexts.
    """

    def holding_cost(
        self,
        pair: str,
        direction: Direction,
        days: float,
        *,
        entry_ts: pd.Timestamp | datetime | None = None,
        exit_ts: pd.Timestamp | datetime | None = None,
    ) -> float:
        """Rollover-aware swap cost.

        If entry_ts and exit_ts are provided, counts actual 22:00 UTC rollover
        crossings (3× on Wednesday) and charges accordingly.  Zero swap for
        positions that do not cross any rollover boundary.

        Falls back to linear pro-rata (super().holding_cost) if timestamps are
        absent — backward-compatible with the engine's daily-bar path.
        """
        if entry_ts is None or exit_ts is None:
            # Backward-compatible fallback: pro-rata by days (daily-bar path only)
            logger.debug(
                "RolloverAwareRealisticCostModel.holding_cost: no timestamps — "
                "falling back to pro-rata (daily-bar path)"
            )
            return super().holding_cost(pair, direction, days)

        p = self._get_pair(pair)
        if direction == Direction.LONG:
            daily_swap = p.swap_long_pips_per_day
        elif direction == Direction.SHORT:
            daily_swap = p.swap_short_pips_per_day
        else:
            return 0.0

        n_single, n_triple = count_rollover_crossings(entry_ts, exit_ts)
        total_swap_days = n_single + 3 * n_triple

        logger.debug(
            "rollover_cost[%s] entry=%s exit=%s n_single=%d n_triple=%d total_days=%d",
            pair, entry_ts, exit_ts, n_single, n_triple, total_swap_days,
        )

        # Convention: negative daily_swap = cost per day; positive = income.
        # Return as cost (positive = money lost by trader).
        return -daily_swap * total_swap_days

    def rollover_cost_for_bar(
        self,
        pair: str,
        direction: Direction,
        bar_ts: pd.Timestamp,
    ) -> float:
        """Swap cost in pips for the BAR whose period crosses the 22:00 UTC rollover.

        A 1h bar timestamped at 21:00 UTC CLOSES at 22:00 UTC — it crosses the
        rollover.  This is the per-bar accrual pattern for the continuous engine.

        Returns non-zero ONLY for bars whose open-to-close spans the 22:00 UTC
        boundary (i.e. bar_ts.hour == 21 UTC), with 3× charge on Wednesday.
        Returns 0.0 for all other bars.

        WEEKEND RULE: bars at 21:00 UTC on Friday (weekday 4), Saturday (weekday 5),
        or Sunday (weekday 6) are NOT charged — the FX market is closed from Fri 21:00
        UTC through Sun 22:00 UTC.  Fri 21:00 closes at Fri 22:00 (market-closed);
        Sat 21:00 closes at Sat 22:00 (market-closed); Sun 21:00 closes at Sun 22:00
        (this is the market OPEN, not a financing boundary).  Consistent with
        count_rollover_crossings() and quality_gate_1h._WEEKEND_CLOSED_DAY_HOUR.
        """
        bar_ts_utc = bar_ts if bar_ts.tzinfo is not None else bar_ts.tz_localize("UTC")
        if str(bar_ts_utc.tz) not in ("UTC", "utc"):
            bar_ts_utc = bar_ts_utc.tz_convert("UTC")

        # A bar at hour 21 closes at 22:00 — crosses the rollover
        if bar_ts_utc.hour != 21:
            return 0.0

        # Skip weekend-closed 22:00 boundaries (Fri/Sat/Sun 21:00 UTC bars).
        # See WEEKEND RULE in docstring above.
        wd = bar_ts_utc.weekday()  # 0=Mon … 6=Sun
        if wd in (4, 5, 6):  # Friday, Saturday, Sunday
            return 0.0

        p = self._get_pair(pair)
        if direction == Direction.LONG:
            daily_swap = p.swap_long_pips_per_day
        elif direction == Direction.SHORT:
            daily_swap = p.swap_short_pips_per_day
        else:
            return 0.0

        # Wednesday 22:00 UTC rollover carries 3× (covers Sat+Sun settlement)
        # bar_ts is at hour 21, meaning the CLOSE is at hour 22 on the SAME day
        # weekday of the bar_ts still equals the weekday of the crossing (hour is 21)
        multiplier = 3 if wd == 2 else 1  # 2 = Wednesday

        logger.debug(
            "rollover_cost_for_bar[%s] ts=%s multiplier=%d", pair, bar_ts_utc, multiplier
        )

        return -daily_swap * multiplier
