"""Session-window filter for intraday signal gating.

Purpose
-------
Restrict trading signals to specified UTC-hour windows (e.g. overnight carry
accumulation 02:00–05:00 UTC, London session 07:00–16:00 UTC). Signals whose
bar timestamp falls outside ALL allowed windows are zeroed before the backtest
engine processes them.

Design contract
---------------
- Pure function: no side effects, no I/O.
- Must be applied to RAW signals BEFORE the entry_delay_bars shift so that the
  shifted signal correctly carries zeroed values forward. The no-lookahead
  guarantee is therefore preserved: filtering happens at the signal-generation
  layer, not inside the engine.
- Config-drivable: callers pass ``allowed_windows`` as a list of (start_hour,
  end_hour) pairs (UTC). No magic constants live here.
- Boundary convention: a bar at hour H is INSIDE a window [start, end) if
  ``start <= H < end``. This matches the natural interpretation of session
  opens (e.g. 07:00 bar is the first London bar; 16:00 bar is the last).

Decision-boundary logging
-------------------------
Per log-as-decision-trace discipline, the function logs at DEBUG level when it
zeros a non-zero signal so the gate decision is auditable.

Usage example
-------------
    from forex_system.backtest.session_filter import apply_session_filter

    # Overnight carry window: 02:00 UTC (inclusive) – 05:00 UTC (exclusive)
    filtered = apply_session_filter(
        signals,
        allowed_windows=[(2, 5)],
    )
    # Then shift and run backtest as usual — delay still applied after filter
    delayed = filtered.shift(entry_delay_bars).fillna(0.0)
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def apply_session_filter(
    signals: pd.Series,
    allowed_windows: list[tuple[int, int]],
) -> pd.Series:
    """Zero signals whose bar timestamp falls outside all allowed UTC-hour windows.

    Args:
        signals: Raw signal Series with a UTC-timezone-aware DatetimeIndex.
            Values in [-1, +1]. Non-UTC or tz-naive indices are accepted and
            treated as UTC (with a DEBUG warning).
        allowed_windows: List of (start_hour, end_hour) pairs, UTC, where
            ``start_hour <= bar_hour < end_hour``. An empty list zeros ALL
            signals. Windows may overlap; a bar is kept if it falls inside ANY
            window.

    Returns:
        A new Series with the same index and dtype as ``signals``, with
        out-of-window values set to 0.0. In-window values are unchanged.

    Raises:
        ValueError: If any window has start_hour >= end_hour, or if hours are
            outside [0, 24).
    """
    # Validate windows
    for start, end in allowed_windows:
        if not (0 <= start < 24) or not (0 <= end <= 24):
            raise ValueError(f"Session window hours must be in [0, 24). Got ({start}, {end}).")
        if start >= end:
            raise ValueError(f"Session window start must be < end. Got ({start}, {end}).")

    if signals.empty:
        return signals.copy()

    # Normalise index to UTC hour
    index = signals.index
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"signals must have a DatetimeIndex, got {type(index).__name__}.")

    if index.tz is None:
        logger.debug("session_filter: tz-naive index — treating as UTC for hour extraction.")
        hours = index.hour
    else:
        hours = index.tz_convert("UTC").hour

    # Build boolean mask: True = bar is inside at least one allowed window
    if allowed_windows:
        in_window = pd.Series(False, index=signals.index)
        for start, end in allowed_windows:
            in_window |= (hours >= start) & (hours < end)
    else:
        # No windows → zero everything
        in_window = pd.Series(False, index=signals.index)

    # Log decision-boundary zeroing (DEBUG; avoids log flood in production)
    out_of_window_nonzero = signals[~in_window & (signals != 0.0)]
    if not out_of_window_nonzero.empty:
        logger.debug(
            "session_filter: zeroing %d non-zero signal(s) outside windows %s "
            "(first: ts=%s signal=%.4f)",
            len(out_of_window_nonzero),
            allowed_windows,
            out_of_window_nonzero.index[0],
            float(out_of_window_nonzero.iloc[0]),
        )

    result = signals.copy()
    result[~in_window] = 0.0
    return result
