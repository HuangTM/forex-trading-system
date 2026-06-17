"""Tests for the UTC-hour session filter.

Invariants verified:
  1. In-window signals are preserved exactly (value unchanged).
  2. Out-of-window signals are zeroed.
  3. Boundary hours are handled correctly (start inclusive, end exclusive).
  4. Filter commutes correctly with entry_delay_bars: no lookahead is introduced.
  5. Empty window list zeros all signals.
  6. Bad window specs raise ValueError.
"""

import pandas as pd
import pytest

from forex_system.backtest.session_filter import apply_session_filter


def _make_hourly_signals(
    start: str = "2023-01-02",
    periods: int = 48,
    tz: str = "UTC",
    fill_value: float = 1.0,
) -> pd.Series:
    """Build a simple 1h signal series, all set to fill_value."""
    dates = pd.date_range(start, periods=periods, freq="1h", tz=tz)
    return pd.Series(fill_value, index=pd.DatetimeIndex(dates, name="datetime"))


# ---------------------------------------------------------------------------
# Core correctness tests
# ---------------------------------------------------------------------------


def test_in_window_signals_preserved():
    """Invariant 1: signals whose bar hour falls inside the window are unchanged."""
    signals = _make_hourly_signals(periods=24)
    # Window 02:00–05:00 UTC — hours 2, 3, 4 are in-window
    filtered = apply_session_filter(signals, allowed_windows=[(2, 5)])

    in_window_hours = [2, 3, 4]
    for h in in_window_hours:
        mask = signals.index.hour == h
        pd.testing.assert_series_equal(
            filtered[mask],
            signals[mask],
            check_names=False,
        )


def test_out_of_window_signals_zeroed():
    """Invariant 2: signals outside all windows are set to 0.0."""
    signals = _make_hourly_signals(periods=24)
    filtered = apply_session_filter(signals, allowed_windows=[(2, 5)])

    # Hours 0,1,5,6,...,23 are outside the window
    out_of_window = filtered[
        ~filtered.index.isin(signals.index[signals.index.hour.isin([2, 3, 4])])
    ]
    assert (out_of_window == 0.0).all(), (
        f"Expected all out-of-window values to be 0.0; got non-zero at: "
        f"{out_of_window[out_of_window != 0.0].index.tolist()}"
    )


def test_boundary_hours_start_inclusive_end_exclusive():
    """Invariant 3: boundary semantics — start hour is included, end hour is excluded."""
    signals = _make_hourly_signals(periods=24)
    # Window [7, 10) → hours 7, 8, 9 included; hour 10 excluded
    filtered = apply_session_filter(signals, allowed_windows=[(7, 10)])

    assert filtered.iloc[7] == 1.0, f"Hour 7 (start) should be included; got {filtered.iloc[7]}"
    assert filtered.iloc[8] == 1.0, f"Hour 8 should be included; got {filtered.iloc[8]}"
    assert filtered.iloc[9] == 1.0, f"Hour 9 should be included; got {filtered.iloc[9]}"
    assert filtered.iloc[10] == 0.0, f"Hour 10 (end) should be excluded; got {filtered.iloc[10]}"
    assert filtered.iloc[6] == 0.0, (
        f"Hour 6 (before start) should be excluded; got {filtered.iloc[6]}"
    )


def test_no_lookahead_after_shift():
    """Invariant 4: session filter commutes correctly with entry_delay_bars shift.

    The session filter is a ZERO/PASS-THROUGH operation — it does not introduce
    any temporal shift relative to the original signal index. The no-lookahead
    guarantee comes entirely from the downstream `entry_delay_bars` shift.

    Structural verification:
      - filter(signals).shift(1) must equal shift(filter(signals), 1)
        (these are equivalent by definition since filter only zeros values)
      - The filtered+shifted series must NOT equal the raw unshifted filtered
        series (i.e., the shift is still present after filtering)
      - In particular, at in-window bars: filtered_shifted[i] == filtered[i-1]
        (shift by 1 step, not shift by 0 = no skipping of the shift)
    """
    dates = pd.date_range("2023-01-02", periods=48, freq="1h", tz="UTC")
    # Assign distinct values to each bar so we can track temporal identity
    signals = pd.Series(
        [float(i + 1) for i in range(48)],
        index=pd.DatetimeIndex(dates, name="datetime"),
    )

    # Apply session filter: 02:00–05:00 UTC
    filtered = apply_session_filter(signals, allowed_windows=[(2, 5)])

    # Apply the entry_delay shift (what the engine does)
    shifted = filtered.shift(1).fillna(0.0)

    # The shifted series at position i must equal filtered[i-1]
    # i.e., the shift moves values forward by 1 bar, not 0 bars
    # Check several in-window bars (hours 2,3,4 in the first day = indices 2,3,4)
    for idx in [2, 3, 4, 26, 27, 28]:  # two cycles (first + second day in-window)
        expected = filtered.iloc[idx - 1]  # value from one bar earlier
        actual = shifted.iloc[idx]
        assert actual == expected, (
            f"At index {idx} (hour {dates[idx].hour} UTC): "
            f"shifted[{idx}]={actual} != filtered[{idx - 1}]={expected}. "
            f"Session filter may have introduced a temporal displacement."
        )

    # Also verify: session filter does NOT apply an internal shift to in-window values
    # (i.e., filtered[i] == signals[i] for in-window i, not signals[i-1])
    in_window_indices = [i for i, d in enumerate(dates) if d.hour in (2, 3, 4)]
    for idx in in_window_indices[:6]:
        assert filtered.iloc[idx] == signals.iloc[idx], (
            f"In-window bar {idx} (hour {dates[idx].hour}): "
            f"filter changed the value ({signals.iloc[idx]} → {filtered.iloc[idx]}), "
            f"suggesting an unintended shift."
        )


def test_empty_window_list_zeros_all_signals():
    """Invariant 5: empty allowed_windows zeroes every signal."""
    signals = _make_hourly_signals(periods=24)
    filtered = apply_session_filter(signals, allowed_windows=[])
    assert (filtered == 0.0).all(), "Empty window list should zero all signals."


def test_multiple_non_overlapping_windows():
    """Multiple windows: signals inside either window are preserved, rest zeroed."""
    signals = _make_hourly_signals(periods=24)
    # Two windows: [2,4) and [14,16)
    filtered = apply_session_filter(signals, allowed_windows=[(2, 4), (14, 16)])

    for h in [2, 3, 14, 15]:
        mask = signals.index.hour == h
        assert (filtered[mask] == 1.0).all(), f"Hour {h} should be preserved."

    for h in [0, 1, 4, 5, 13, 16, 17, 23]:
        mask = signals.index.hour == h
        assert (filtered[mask] == 0.0).all(), f"Hour {h} should be zeroed."


def test_mixed_signal_values_preserved_correctly():
    """Non-uniform signal values: in-window values kept exactly, out-of-window zeroed."""
    dates = pd.date_range("2023-01-02", periods=5, freq="1h", tz="UTC")
    # hours 0,1,2,3,4
    values = [0.5, -0.8, 1.0, 0.3, -0.2]
    signals = pd.Series(values, index=pd.DatetimeIndex(dates, name="datetime"))

    # Window [2, 4): hours 2 and 3 are inside
    filtered = apply_session_filter(signals, allowed_windows=[(2, 4)])

    assert filtered.iloc[0] == 0.0  # hour 0 — outside
    assert filtered.iloc[1] == 0.0  # hour 1 — outside
    assert filtered.iloc[2] == 1.0  # hour 2 — inside
    assert filtered.iloc[3] == 0.3  # hour 3 — inside
    assert filtered.iloc[4] == 0.0  # hour 4 — outside (end exclusive)


def test_invalid_window_start_equals_end_raises():
    """Bad window spec: start == end should raise ValueError."""
    signals = _make_hourly_signals(periods=10)
    with pytest.raises(ValueError, match="start must be < end"):
        apply_session_filter(signals, allowed_windows=[(5, 5)])


def test_invalid_window_start_greater_than_end_raises():
    """Bad window spec: start > end should raise ValueError."""
    signals = _make_hourly_signals(periods=10)
    with pytest.raises(ValueError, match="start must be < end"):
        apply_session_filter(signals, allowed_windows=[(10, 5)])


def test_invalid_window_hour_out_of_range_raises():
    """Bad window spec: hour outside [0, 24) should raise ValueError."""
    signals = _make_hourly_signals(periods=10)
    with pytest.raises(ValueError, match="hours must be in"):
        apply_session_filter(signals, allowed_windows=[(0, 25)])


def test_daily_index_is_not_crashed():
    """Daily-bar (business-day) signal index: all bars are same wall-clock time,
    so result depends on that time. Should not raise."""
    dates = pd.bdate_range("2023-01-02", periods=20, freq="B", tz="UTC")
    signals = pd.Series(1.0, index=pd.DatetimeIndex(dates, name="datetime"))
    # bdate_range default time = 00:00 UTC → all bars at hour 0
    filtered = apply_session_filter(signals, allowed_windows=[(0, 1)])
    assert (filtered == 1.0).all(), "All daily bars at 00:00 should be inside [0,1) window."


def test_empty_signals_returns_empty():
    """Empty input series → empty output (no crash)."""
    signals = pd.Series([], dtype=float, index=pd.DatetimeIndex([], tz="UTC", name="datetime"))
    filtered = apply_session_filter(signals, allowed_windows=[(2, 5)])
    assert len(filtered) == 0
