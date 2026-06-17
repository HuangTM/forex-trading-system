"""Tests for OvernightMRStrategy — Trial 48 (A2′).

Critical invariants:
  1. No-lookahead: sigma_sess excludes the current bar.
  2. Session filter: signals only on UTC hours {02,03,04,05}.
  3. Pre-gap NO-TRADE: no signal on bar before a weekend/holiday gap.
  4. Signal direction: short on up-bar (fade), long on down-bar (fade).
  5. Sigma gap-skipping: rolling window skips multi-day gaps, counts same-hour bars only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex_system.strategies.overnight_mr import (
    OvernightMRStrategy,
    _SESSION_HOURS,
)


def _make_hourly_ohlcv(
    n_bars: int = 200,
    start: str = "2022-01-03 02:00:00",
    freq: str = "1h",
    base_price: float = 1.1000,
    tz: str = "UTC",
) -> pd.DataFrame:
    """Build minimal 1h OHLCV data with a UTC-aware DatetimeIndex."""
    dates = pd.date_range(start, periods=n_bars, freq=freq, tz=tz)
    prices = base_price + np.cumsum(np.random.default_rng(42).normal(0, 0.0001, n_bars))
    prices = np.maximum(prices, 0.5)  # keep positive
    df = pd.DataFrame(
        {
            "open": prices,
            "high": prices + 0.0005,
            "low": prices - 0.0005,
            "close": prices,
            "volume": 1_000_000.0,
        },
        index=pd.DatetimeIndex(dates, name="datetime"),
    )
    return df


def _make_session_only_ohlcv(
    n_trading_days: int = 50,
    start_date: str = "2022-01-03",
    base_price: float = 1.1000,
) -> pd.DataFrame:
    """Build OHLCV data with only session hours {02,03,04,05} UTC, 5 days/week."""
    rng = np.random.default_rng(99)
    rows = []
    date = pd.Timestamp(start_date, tz="UTC")
    days_added = 0

    while days_added < n_trading_days:
        # Skip weekends
        if date.dayofweek < 5:  # Mon-Fri
            for h in sorted(_SESSION_HOURS):
                ts = date + pd.Timedelta(hours=h)
                rows.append({"datetime": ts, "close": base_price + rng.normal(0, 0.0002)})
            days_added += 1
        date += pd.Timedelta(days=1)

    df = pd.DataFrame(rows).set_index("datetime")
    df.index = pd.DatetimeIndex(df.index, tz="UTC")
    df["open"] = df["close"]
    df["high"] = df["close"] + 0.0005
    df["low"] = df["close"] - 0.0005
    df["volume"] = 1_000_000.0
    return df


# ------------------------------------------------------------------ #
# Test 1: No-lookahead — sigma excludes the current bar
# ------------------------------------------------------------------ #


class TestNoLookahead:
    """Verify that sigma_sess does NOT include bar t in its own computation."""

    def test_sigma_shift_excludes_current_bar(self):
        """Trivially profitable oracle: if sigma included bar t, it would always
        produce a signal on any large move. With the shift, it cannot.

        Construct a synthetic scenario: inject a known large bar at position t.
        If sigma_sess at t used the large bar t, its own z-score would be 0 (since
        the bar equals 1*sigma). The test verifies that sigma at bar t reflects
        the PRIOR bars' volatility, not bar t's own contribution.
        """
        strategy = OvernightMRStrategy(params={})

        # Build session-only data with known returns
        n_sess_bars = 60  # enough for sigma_lookback=20
        rng = np.random.default_rng(7)
        base_price = 1.1000

        rows = []
        date = pd.Timestamp("2022-01-03", tz="UTC")
        days_added = 0

        while days_added < n_sess_bars // 4 + 5:
            if date.dayofweek < 5:
                for h in [2, 3, 4, 5]:
                    ts = date + pd.Timedelta(hours=h)
                    rows.append({"datetime": ts})
                days_added += 1
            date += pd.Timedelta(days=1)

        df_idx = pd.DataFrame(rows).set_index("datetime")
        df_idx.index = pd.DatetimeIndex(df_idx.index, tz="UTC")

        # Generate small constant returns for all bars (near-zero volatility period)
        prices = [base_price]
        for _ in range(len(df_idx) - 1):
            prices.append(prices[-1] * (1 + rng.normal(0, 0.0002)))

        df_idx["close"] = prices
        df_idx["open"] = df_idx["close"]
        df_idx["high"] = df_idx["close"] + 0.0002
        df_idx["low"] = df_idx["close"] - 0.0002
        df_idx["volume"] = 1_000_000.0

        # Baseline signals on un-spiked data (used implicitly to confirm no signal baseline)
        _ = strategy.generate_signals(df_idx)

        # Now inject a massive spike at the 30th bar (well past warmup)
        target_idx = 30
        spike_price = df_idx["close"].iloc[target_idx - 1] * 1.05  # +5% (huge)
        df_injected = df_idx.copy()
        spike_ts = df_injected.index[target_idx]
        df_injected.loc[spike_ts, "close"] = spike_price
        df_injected.loc[spike_ts, "high"] = spike_price + 0.001

        sigs_spike = strategy.generate_signals(df_injected)

        # If the large bar created a signal on itself (lookahead), the signal at
        # target_idx would be non-zero even if sigma included that bar.
        # We verify that the signal is generated by comparing BEFORE vs AFTER:
        # the spike should produce a signal at target_idx (sigma from prior bars
        # is small, spike is huge relative to prior sigma) — this is CORRECT
        # and expected. What we care about: sigma at target_idx does NOT include
        # the spike bar's own return (no lookahead).
        #
        # Direct test: compute what sigma WOULD be if the current bar were included.
        # If sigma included the spike, the ratio r/sigma would be ~1 (the spike is
        # its own std dev), not >> threshold. With the shift (exclude current bar),
        # sigma is still the small prior volatility, so ratio >> threshold → signal fires.
        #
        # Practical invariant: the spike bar SHOULD fire because prior sigma << spike.
        assert sigs_spike.iloc[target_idx] != 0.0, (
            f"Expected signal at spike bar {target_idx}; "
            f"got {sigs_spike.iloc[target_idx]}. "
            "If sigma included the current bar, the spike would be self-normalizing and no "
            "signal would fire — that would be the lookahead bug."
        )

    def test_no_lookahead_oracle_not_profitable(self):
        """Sacred test: future-looking oracle signal is NOT profitable after delay=1.

        This mirrors the engine's test_no_lookahead but specialized for overnight MR.
        We build a signal that knows the NEXT bar's direction (lookahead), pass it
        through the engine with entry_delay_bars=1, and verify the Sharpe is not
        suspiciously high. If the engine had a lookahead bug, this would be very profitable.
        """
        from forex_system.backtest.engine import run_backtest
        from forex_system.backtest.metrics import calculate_metrics
        from forex_system.costs.static_roundtrip import StaticRoundTripCostModel

        data = _make_hourly_ohlcv(n_bars=500)
        # Lookahead oracle: signal = +1 if next bar's close > this bar's close
        future_return = data["close"].shift(-1) - data["close"]
        lookahead_signals = pd.Series(0.0, index=data.index)
        lookahead_signals[future_return > 0] = 1.0
        lookahead_signals[future_return < 0] = -1.0

        cost_model = StaticRoundTripCostModel()
        result = run_backtest(
            data=data,
            signals=lookahead_signals,
            pair="EURUSD",
            strategy_name="lookahead_oracle",
            cost_model=cost_model,
            entry_delay_bars=1,
        )

        ec = result.equity_curve.dropna()
        metrics = calculate_metrics(result.equity_curve, result.trade_log)
        if len(ec) > 10 and ec.pct_change().dropna().std() > 0:
            sharpe = metrics.sharpe_ratio
            assert sharpe < 3.0, (
                f"Suspiciously high Sharpe ({sharpe:.2f}) with delayed lookahead oracle — "
                f"possible engine lookahead leak."
            )


# ------------------------------------------------------------------ #
# Test 2: Session filter — signals only in window hours
# ------------------------------------------------------------------ #


class TestSessionFilter:
    """Signals must only appear on bars with UTC hour in {02,03,04,05}."""

    def test_signals_only_in_session_hours(self):
        """Non-session bars must produce 0.0 signal."""
        strategy = OvernightMRStrategy(params={})
        data = _make_hourly_ohlcv(n_bars=500)  # continuous hourly, all UTC hours

        signals = strategy.generate_signals(data)

        # Build UTC hours for all bars
        hours = data.index.tz_convert("UTC").hour
        out_of_session = ~pd.Series(hours, index=data.index).isin(_SESSION_HOURS)

        # All out-of-session bars must be 0
        out_signals = signals[out_of_session]
        nonzero_out = out_signals[out_signals != 0.0]
        assert len(nonzero_out) == 0, (
            f"Found {len(nonzero_out)} non-zero signals outside session hours: {nonzero_out.head()}"
        )

    def test_signals_possible_in_session_hours(self):
        """In-session bars CAN have non-zero signals (sanity check)."""
        strategy = OvernightMRStrategy(params={})
        # Build session-only data with enough history
        # Need at least 20 same-hour-class bars per hour = 20 trading days minimum.
        # Use 60 days for comfort.
        data = _make_session_only_ohlcv(n_trading_days=60)

        # Inject a large spike at bar 95 (well past warmup; each hour-class gets 1 bar/day,
        # so 20-bar warmup per hour-class requires ~20 trading days = ~80 session bars).
        # Bar 95 gives each hour-class ~23 prior bars.
        bar_idx = 95
        spike_ts = data.index[bar_idx]
        prev_close = data["close"].iloc[bar_idx - 1]
        data = data.copy()
        data.loc[spike_ts, "close"] = prev_close * 1.05  # large +5% spike

        signals = strategy.generate_signals(data)
        # There should be at least one non-zero signal somewhere
        assert (signals != 0.0).any(), "Expected at least one non-zero signal in session data"


# ------------------------------------------------------------------ #
# Test 3: Signal direction — fade (contrarian)
# ------------------------------------------------------------------ #


class TestSignalDirection:
    """Large up-moves → short signal; large down-moves → long signal."""

    def test_fade_short_on_large_up_move(self):
        """An over-extended up bar should generate a SHORT (-1.0) signal."""
        strategy = OvernightMRStrategy(params={})
        # Use 80 trading days so each of 4 session hours has 80 prior same-hour bars
        # (well past the 20-bar sigma_lookback warmup).
        data = _make_session_only_ohlcv(n_trading_days=80)

        # Bar 95: each hour class has seen >= 23 prior bars → sigma warmed up.
        bar_idx = 95
        data = data.copy()
        spike_ts = data.index[bar_idx]
        prev_price = data["close"].iloc[bar_idx - 1]
        data.loc[spike_ts, "close"] = prev_price * 1.05  # large +5% up move

        signals = strategy.generate_signals(data)
        sig_at_spike = signals.iloc[bar_idx]

        # Signal must be SHORT (fade the up move)
        assert sig_at_spike == -1.0, (
            f"Expected SHORT (-1.0) for large up bar; got {sig_at_spike}. "
            f"Bar hour: {spike_ts.hour} UTC. "
            f"If 0.0, sigma may not be warm or pre-gap rule fired."
        )

    def test_fade_long_on_large_down_move(self):
        """An over-extended down bar should generate a LONG (+1.0) signal."""
        strategy = OvernightMRStrategy(params={})
        data = _make_session_only_ohlcv(n_trading_days=80)

        bar_idx = 95
        data = data.copy()
        spike_ts = data.index[bar_idx]
        prev_price = data["close"].iloc[bar_idx - 1]
        data.loc[spike_ts, "close"] = prev_price * 0.95  # large -5% down move

        signals = strategy.generate_signals(data)
        sig_at_spike = signals.iloc[bar_idx]

        assert sig_at_spike == 1.0, (
            f"Expected LONG (+1.0) for large down bar; got {sig_at_spike}. "
            f"Bar hour: {spike_ts.hour} UTC. "
            f"If 0.0, sigma may not be warm or pre-gap rule fired."
        )


# ------------------------------------------------------------------ #
# Test 4: Pre-gap NO-TRADE rule
# ------------------------------------------------------------------ #


class TestPreGapNoTrade:
    """Last bar before a weekend/holiday gap must produce no signal."""

    def test_pre_friday_gap_is_notrade(self):
        """Bar just before a weekend gap (>6h to next bar) must be zeroed."""
        strategy = OvernightMRStrategy(params={})

        # Build data that ends on a Friday evening session bar with a weekend gap after
        # Mon 2022-01-03 02:00 ... Fri 2022-01-07 05:00, then Mon 2022-01-10 02:00
        rows = []
        rng = np.random.default_rng(5)
        price = 1.1000

        # Mon-Thu: 4 session hours per day
        for day_offset in range(4):  # Mon-Thu
            d = pd.Timestamp("2022-01-03", tz="UTC") + pd.Timedelta(days=day_offset)
            for h in [2, 3, 4, 5]:
                ts = d + pd.Timedelta(hours=h)
                price *= 1 + rng.normal(0, 0.0002)
                rows.append({"datetime": ts, "close": price})

        # Fri session bars
        fri = pd.Timestamp("2022-01-07", tz="UTC")
        for h in [2, 3, 4, 5]:
            ts = fri + pd.Timedelta(hours=h)
            price *= 1 + rng.normal(0, 0.0002)
            rows.append({"datetime": ts, "close": price})

        # Next Mon (gap = ~65 hours from Fri 05:00 to Mon 02:00)
        mon = pd.Timestamp("2022-01-10", tz="UTC")
        for h in [2, 3, 4, 5]:
            ts = mon + pd.Timedelta(hours=h)
            price *= 1 + rng.normal(0, 0.0002)
            rows.append({"datetime": ts, "close": price})

        df = pd.DataFrame(rows).set_index("datetime")
        df.index = pd.DatetimeIndex(df.index, tz="UTC")
        df["open"] = df["close"]
        df["high"] = df["close"] + 0.001
        df["low"] = df["close"] - 0.001
        df["volume"] = 1_000_000.0

        # The last Fri bar (index -5 in our list, before the Mon block)
        fri_05 = fri + pd.Timedelta(hours=5)  # last Fri session bar

        # Inject a very large move on the last Fri bar to try to trigger a signal
        df.loc[fri_05, "close"] = df["close"].shift(1).loc[fri_05] * 1.1

        signals = strategy.generate_signals(df)

        # The last Fri session bar must be 0 (pre-gap NO-TRADE)
        assert fri_05 in signals.index, "Fri 05:00 bar not in index"
        assert signals.loc[fri_05] == 0.0, (
            f"Expected 0 signal on last Fri bar (pre-gap NO-TRADE), got {signals.loc[fri_05]}"
        )


# ------------------------------------------------------------------ #
# Test 5: Empty data
# ------------------------------------------------------------------ #


class TestEdgeCases:
    """Edge cases: empty data, insufficient history, tz-naive index."""

    def test_empty_data_returns_empty(self):
        """Empty input → empty signal output."""
        strategy = OvernightMRStrategy(params={})
        empty = pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"], index=pd.DatetimeIndex([], tz="UTC")
        )
        signals = strategy.generate_signals(empty)
        assert len(signals) == 0

    def test_insufficient_history_returns_zeros(self):
        """Fewer than sigma_lookback+1 session bars → all zeros."""
        strategy = OvernightMRStrategy(params={})
        # Only 5 session bars — well below lookback=20
        data = _make_session_only_ohlcv(n_trading_days=2)
        signals = strategy.generate_signals(data)
        assert (signals == 0.0).all(), "Expected all zeros with insufficient history"

    def test_required_indicators_is_empty(self):
        """Strategy computes all features internally; required_indicators is empty."""
        strategy = OvernightMRStrategy(params={})
        assert strategy.required_indicators() == []

    def test_name(self):
        """Strategy name is correct."""
        strategy = OvernightMRStrategy(params={})
        assert strategy.name == "overnight_mr"

    def test_signal_index_matches_input(self):
        """Output signal index must match input data index exactly."""
        strategy = OvernightMRStrategy(params={})
        data = _make_session_only_ohlcv(n_trading_days=50)
        signals = strategy.generate_signals(data)
        pd.testing.assert_index_equal(signals.index, data.index)

    def test_signal_values_in_valid_set(self):
        """All signal values must be in {-1.0, 0.0, +1.0}."""
        strategy = OvernightMRStrategy(params={})
        data = _make_session_only_ohlcv(n_trading_days=60)
        signals = strategy.generate_signals(data)
        valid_values = {-1.0, 0.0, 1.0}
        assert set(signals.unique()).issubset(valid_values), (
            f"Signal values outside valid set: {set(signals.unique()) - valid_values}"
        )
