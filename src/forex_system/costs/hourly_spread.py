"""Hour-of-day spread curve + time-varying cost model (P0 #1).

The 1h timeframe has no native spread file; spreads exist only for 4h/daily.
This module derives an hour-of-day spread curve from the 4h spread series
(which carries an ``hour`` column) and applies it per-bar so a 1h backtest gets
a realistic, time-varying transaction cost instead of a single fixed spread.

Why this matters: realized intraday spread is NOT flat — it widens in the thin
liquidity window around the 17-18 UTC NY-afternoon / pre-rollover hours and
spikes on the 22:00 rollover and news. A fixed spread under-charges those bars
and over-charges the deep-liquidity London/NY-overlap hours.

The 4h source samples only 18 of 24 hours (4h bars start every 4h, offset), so
hours 3, 7, 11, 15, 19, 23 are absent and are filled by circular linear
interpolation from their nearest present neighbours.
"""

from __future__ import annotations

import pandas as pd

from forex_system.costs.model import RealisticCostModel
from forex_system.core.types import PairInfo


def build_hourly_spread_curve_from_frame(
    spreads: pd.DataFrame,
    quantile: float = 0.5,
    drop_days: tuple[int, ...] = (5,),
) -> dict[int, float]:
    """Build a 24-hour spread curve (pips) from a spreads DataFrame.

    Args:
        spreads: must contain ``spread_pips``; uses an ``hour`` column if present,
            else derives the hour-of-day from a DatetimeIndex.
        quantile: per-hour aggregation quantile. 0.5 (median) is the robust
            central estimate; pass a higher quantile (e.g. 0.9) for a
            conservative, cost-stressed curve.
        drop_days: ISO weekday numbers (Mon=0 .. Sun=6) to exclude before
            aggregating, using a ``day_of_week`` column if present else the
            DatetimeIndex. Defaults to ``(5,)`` — Saturday, a non-trading day
            whose sparse rows are spurious. Sunday (6) is KEPT by default: the
            week-open hours are legitimately thin-liquidity / wider-spread and
            belong in the cost curve. Pass ``()`` to disable filtering.

    Returns:
        ``{hour: spread_pips}`` for all 24 hours; hours absent from the source
        are circular-linear-interpolated from their nearest present neighbours.

    Raises:
        ValueError: if ``spread_pips`` is missing, no hour information is
            available, or no hours could be aggregated.
    """
    if "spread_pips" not in spreads.columns:
        raise ValueError("spreads frame must contain a 'spread_pips' column")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError(f"quantile must be in [0, 1]; got {quantile}")

    df = spreads
    if drop_days:
        if "day_of_week" in df.columns:
            keep = ~df["day_of_week"].astype(int).isin(drop_days).to_numpy()
            df = df[keep]
        elif isinstance(df.index, pd.DatetimeIndex):
            keep = ~pd.Index(df.index.dayofweek).isin(drop_days)
            df = df[keep]
        # else: no weekday info available — cannot filter; aggregate as-is.

    if "hour" in df.columns:
        hours = df["hour"].astype(int)
    elif isinstance(df.index, pd.DatetimeIndex):
        hours = pd.Series(df.index.hour, index=df.index)
    else:
        raise ValueError("spreads need an 'hour' column or a DatetimeIndex")

    by_hour = df.groupby(hours.values)["spread_pips"].quantile(quantile)
    present: dict[int, float] = {
        int(h): float(v) for h, v in by_hour.items() if pd.notna(v)
    }
    if not present:
        raise ValueError("no hours could be aggregated from the spreads frame")

    return _interpolate_missing_hours(present)


def build_hourly_spread_curve(spreads_path: str, quantile: float = 0.5) -> dict[int, float]:
    """Read a spreads parquet and build the hour-of-day spread curve.

    Thin I/O wrapper over :func:`build_hourly_spread_curve_from_frame`.
    """
    return build_hourly_spread_curve_from_frame(pd.read_parquet(spreads_path), quantile)


def make_hourly_spread_cost_model(
    pair_configs: dict[str, PairInfo],
    spreads_path: str,
    quantile: float = 0.9,
) -> "HourlySpreadCostModel":
    """Build an :class:`HourlySpreadCostModel` from a spreads parquet.

    Defaults to ``quantile=0.9`` — the conservative, cost-stressed curve — per
    the Phase-0 "does alpha survive *realistic* costs?" posture (the median
    under-charges the thin-liquidity tail). Pass ``quantile=0.5`` for the
    central-estimate curve.
    """
    curve = build_hourly_spread_curve(spreads_path, quantile=quantile)
    return HourlySpreadCostModel(pair_configs=pair_configs, hourly_spread_curve=curve)


def _interpolate_missing_hours(present: dict[int, float]) -> dict[int, float]:
    """Fill any of hours 0..23 missing from ``present`` via circular linear interp."""
    curve: dict[int, float] = dict(present)
    for h in range(24):
        if h in curve:
            continue
        lo_h, lo_v = _nearest_present(present, h, step=-1)
        hi_h, hi_v = _nearest_present(present, h, step=+1)
        # circular forward distances from lo -> h and h -> hi
        d_lo = (h - lo_h) % 24
        d_hi = (hi_h - h) % 24
        span = d_lo + d_hi
        curve[h] = lo_v if span == 0 else lo_v + (hi_v - lo_v) * (d_lo / span)
    return curve


def _nearest_present(present: dict[int, float], h: int, step: int) -> tuple[int, float]:
    """Nearest hour in ``present`` walking circularly from ``h`` in direction ``step``."""
    for dist in range(1, 24):
        cand = (h + step * dist) % 24
        if cand in present:
            return cand, present[cand]
    # unreachable: present is non-empty, so a neighbour always exists
    raise ValueError("no present hours to interpolate from")


class HourlySpreadCostModel(RealisticCostModel):
    """Cost model that applies an hour-of-day spread curve when a timestamp is given.

    Drop-in for :class:`RealisticCostModel`: ``entry_cost``/``exit_cost`` take an
    optional ``timestamp``. With a timestamp AND a curve, the bar's hour-of-day
    spread is used; otherwise it falls back to the fixed ``PairInfo.spread_pips``
    (so calling it the legacy way returns a numerically identical result to
    RealisticCostModel — same formula and inputs). Slippage, commission, and
    swap are inherited unchanged.
    """

    def __init__(
        self,
        pair_configs: dict[str, PairInfo] | None = None,
        hourly_spread_curve: dict[int, float] | None = None,
    ):
        super().__init__(pair_configs)
        self.curve: dict[int, float] = dict(hourly_spread_curve or {})

    def _spread_pips(self, pair: str, timestamp: pd.Timestamp | None) -> float:
        if timestamp is not None and self.curve:
            ts = pd.Timestamp(timestamp)
            # The curve is keyed on UTC hour-of-day; normalise tz-aware inputs to
            # UTC so a non-UTC timestamp can't silently mis-index it. tz-naive
            # inputs are assumed UTC (the system's storage convention).
            if ts.tzinfo is not None:
                ts = ts.tz_convert("UTC")
            if ts.hour in self.curve:
                return self.curve[ts.hour]
        return self._get_pair(pair).spread_pips

    def entry_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        p = self._get_pair(pair)
        return self._spread_pips(pair, timestamp) / 2.0 + p.slippage_pips

    def exit_cost(self, pair: str, size: float, timestamp: pd.Timestamp | None = None) -> float:
        p = self._get_pair(pair)
        return self._spread_pips(pair, timestamp) / 2.0 + p.slippage_pips + p.commission_pips
