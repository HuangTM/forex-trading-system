"""Overnight Mean-Reversion Strategy — Trial 48 (A2′), EURUSD 1h.

Pre-registration: .fintech-org/artifacts/2026-06-17T02-37-59Z_intraday_eurusd_1h/qr-prereg-v2.yaml
Trial ID: 15923fe1

Signal logic (all from frozen spec — NO params may be changed):
  - Entry universe: UTC hour in {02, 03, 04, 05}
  - r_t = log(close_t / close_{t-1})
  - sigma_sess = stdev of r over the trailing 20 same-UTC-hour-class bars,
    computed STRICTLY from bars at or before t-1 (current bar t EXCLUDED).
  - FADE-SHORT if r_t >= +2.0 * sigma_sess  → signal = -1.0
  - FADE-LONG  if r_t <= -2.0 * sigma_sess  → signal = +1.0
  - else signal = 0.0
  - Weekend/holiday gap NO-TRADE: if bar t+1 would straddle the Fri 21:00Z–Sun 21:00Z
    gap (or any session gap > 6h), the signal is forced to 0.0 (NO-TRADE).

The engine applies entry_delay_bars=1, so signal at bar t executes at bar t+1.
Single-bar hold: flat at bar t+1 close. Cost: 7.5-pip frozen static round-trip.

No-lookahead: sigma_sess uses bars STRICTLY <= t-1 (current bar excluded).
This is load-bearing per F-002; the no-lookahead test must remain green.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from forex_system.core.interfaces import Strategy

logger = logging.getLogger(__name__)

# Frozen degrees of freedom — DO NOT MODIFY without a new pre-registration
_SESSION_HOURS: frozenset[int] = frozenset({2, 3, 4, 5})
_SIGMA_LOOKBACK: int = 20
_ENTRY_THRESHOLD: float = 2.0
# Gap detection: if the time gap to the next bar exceeds this threshold, it is a
# weekend/holiday gap (NO-TRADE). Must distinguish:
#   - Normal inter-session gap: ~21h (from 05:00 to next day's 02:00)
#   - Weekend gap: ~65h (from Fri 05:00 to Mon 02:00)
#   - Holiday gaps: variable, but always > 24h between session bars
# Threshold: 30h captures weekends/holidays but not the normal 21h inter-session gap.
_MAX_NORMAL_GAP_HOURS: float = 30.0


class OvernightMRStrategy(Strategy):
    """Overnight mean-reversion fade on EURUSD 1h bars (Trial 48 / A2′).

    All parameters are FROZEN in the pre-registration spec. This class
    accepts a ``params`` dict for interface compatibility but ignores all
    values — every degree of freedom is hardcoded from the frozen spec.
    """

    @property
    def name(self) -> str:
        return "overnight_mr"

    def required_indicators(self) -> list[str]:
        # All features computed internally — no external indicator registry needed.
        return []

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate fade signals for the overnight window.

        Args:
            data: OHLCV DataFrame with a UTC-aware DatetimeIndex, covering ONLY
                the IS window (caller is responsible for slicing). Must contain
                'close' column.

        Returns:
            Series of signals in {-1.0, 0.0, +1.0}, same index as data.
            -1.0 = fade short (bar over-extended up)
            +1.0 = fade long (bar over-extended down)
             0.0 = flat (no signal or NO-TRADE)

        No-lookahead guarantee:
            sigma_sess at bar t is computed from bars {i < t, hour_i in session_hours},
            i.e. the trailing 20 same-hour-class bars EXCLUDING bar t itself.
            This is enforced by computing the rolling std on the same-hour-class
            return series and then aligning back to the full-data index with a
            one-position shift, so bar t's sigma uses only bars at or before t-1.
        """
        if data.empty:
            return pd.Series(dtype=float)

        # --- Step 1: Compute log returns ---
        log_returns = np.log(data["close"] / data["close"].shift(1))

        # --- Step 2: Build same-hour-class series ---
        # Extract UTC hour from DatetimeIndex
        if data.index.tz is None:
            hours = data.index.hour
        else:
            hours = data.index.tz_convert("UTC").hour

        in_session = pd.Series(hours, index=data.index).isin(_SESSION_HOURS)

        # Session-only log returns (NaN for non-session bars)
        sess_returns = log_returns.where(in_session)

        # --- Step 3: Compute sigma_sess with current bar EXCLUDED ---
        # rolling().std() at position i includes position i, so we shift by 1
        # to exclude the current bar. This is the load-bearing no-lookahead fix.
        #
        # Process:
        #   a) Extract session-bar returns as a sub-series (only session bars),
        #      compute rolling std over the last 20, then re-index back to the
        #      full index. This correctly skips gap bars (no forward-fill).
        #   b) Shift the result by 1 (so bar t gets the sigma from bars <= t-1).
        #
        # The sub-series rolling handles gap-skipping naturally: rolling on the
        # session-only sub-series counts 20 same-hour-class bars, not 20 calendar
        # bars, so multi-day gaps are transparent.

        sess_only_returns = sess_returns.dropna()

        if len(sess_only_returns) < _SIGMA_LOOKBACK + 1:
            # Not enough history — return all zeros
            logger.debug(
                "overnight_mr: insufficient session bars (%d < %d); returning zeros",
                len(sess_only_returns),
                _SIGMA_LOOKBACK + 1,
            )
            return pd.Series(0.0, index=data.index)

        # Rolling std over the trailing 20 bars, computed on session sub-series.
        # shift(1) on the sub-series means: at position i of the sub-series,
        # the value uses positions 0..i-1, i.e. excludes position i itself.
        sess_rolling_std = (
            sess_only_returns.shift(1)  # exclude current bar
            .rolling(_SIGMA_LOOKBACK, min_periods=_SIGMA_LOOKBACK)
            .std()
        )

        # Re-align to full data index (NaN for non-session or insufficient history)
        sigma_sess = sess_rolling_std.reindex(data.index)

        # --- Step 4: Detect pre-gap (NO-TRADE) bars ---
        # A bar is NO-TRADE if the NEXT bar's timestamp is more than
        # _MAX_NORMAL_GAP_HOURS hours away (Friday close, holiday, etc.).
        # We compare bar t's gap-to-next against the threshold.
        timestamps = data.index
        next_gap_hours = pd.Series(np.nan, index=timestamps)
        if len(timestamps) > 1:
            # Compute hours until next bar for all bars except the last
            diffs = (timestamps[1:] - timestamps[:-1]).total_seconds() / 3600.0
            next_gap_hours.iloc[:-1] = diffs
        # Last bar: treat as pre-gap (conservative — can't see what comes next)
        next_gap_hours.iloc[-1] = np.inf

        pre_gap = next_gap_hours > _MAX_NORMAL_GAP_HOURS

        # --- Step 5: Generate signals ---
        signals = pd.Series(0.0, index=data.index)

        # Only consider in-session bars with valid sigma
        valid = in_session & sigma_sess.notna() & (sigma_sess > 0)

        fade_short = valid & ~pre_gap & (log_returns >= _ENTRY_THRESHOLD * sigma_sess)
        fade_long = valid & ~pre_gap & (log_returns <= -_ENTRY_THRESHOLD * sigma_sess)

        signals[fade_short] = -1.0
        signals[fade_long] = 1.0

        # Decision-boundary log (debug, per log-as-decision-trace discipline)
        n_short = int(fade_short.sum())
        n_long = int(fade_long.sum())
        n_nogap = int(pre_gap.sum())
        logger.debug(
            "overnight_mr.generate_signals: bars=%d in_session=%d "
            "short_signals=%d long_signals=%d pre_gap_zeroed=%d "
            "insufficient_sigma=%d",
            len(data),
            int(in_session.sum()),
            n_short,
            n_long,
            n_nogap,
            int(valid.sum()) - n_short - n_long,
        )

        return signals
