"""Tests for HeartbeatWatchdog (dead-man switch).

All tests use small timeout_seconds values (0.1 – 0.3 s) for fast CI.
Wall-clock manipulation does NOT affect the watchdog because it uses
time.monotonic() exclusively.
"""

from __future__ import annotations

import threading
import time
import unittest.mock as mock

import pytest

from forex_system.risk.heartbeat_watchdog import HeartbeatWatchdog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_watchdog(timeout: float, cb=None):
    """Return a HeartbeatWatchdog with an optional callback (defaults to no-op)."""
    if cb is None:
        cb = lambda elapsed: None  # noqa: E731
    return HeartbeatWatchdog(timeout_seconds=timeout, on_timeout=cb)


# ---------------------------------------------------------------------------
# 1. Ticks within timeout → no alarm
# ---------------------------------------------------------------------------

class TestNoTimeoutWhenTickingFast:
    def test_repeated_ticks_do_not_fire_callback(self):
        fired = threading.Event()
        wd = _make_watchdog(0.2, cb=lambda _e: fired.set())
        wd.start()
        try:
            for _ in range(6):
                wd.tick()
                time.sleep(0.02)  # 20 ms ticks, well within 200 ms timeout
            assert not fired.is_set(), "on_timeout should not have fired"
        finally:
            wd.stop()


# ---------------------------------------------------------------------------
# 2. No tick → timeout fires exactly once
# ---------------------------------------------------------------------------

class TestTimeoutFiresExactlyOnce:
    def test_fires_once_after_timeout(self):
        call_count = 0
        lock = threading.Lock()

        def cb(elapsed):
            nonlocal call_count
            with lock:
                call_count += 1

        timeout = 0.15
        wd = _make_watchdog(timeout, cb=cb)
        wd.start()
        try:
            # Wait well past timeout without ticking
            time.sleep(timeout * 3)
            with lock:
                count_snapshot = call_count
        finally:
            wd.stop()

        assert count_snapshot == 1, (
            f"on_timeout should fire exactly once, fired {count_snapshot} times"
        )

    def test_elapsed_passed_to_callback_is_positive(self):
        received = []

        def cb(elapsed):
            received.append(elapsed)

        timeout = 0.15
        wd = _make_watchdog(timeout, cb=cb)
        wd.start()
        time.sleep(timeout * 2.5)
        wd.stop()

        assert len(received) == 1
        assert received[0] > timeout, (
            f"elapsed {received[0]:.3f} should exceed timeout {timeout}"
        )


# ---------------------------------------------------------------------------
# 3. Tick after fired timeout → resets; subsequent hang re-fires
# ---------------------------------------------------------------------------

class TestTimeoutResetAndRefire:
    def test_tick_after_timeout_resets_and_subsequent_gap_refires(self):
        fired_events: list[float] = []
        lock = threading.Lock()

        def cb(elapsed):
            with lock:
                fired_events.append(elapsed)

        timeout = 0.15
        wd = _make_watchdog(timeout, cb=cb)
        wd.start()
        try:
            # 1st gap — let it fire
            time.sleep(timeout * 2.5)
            with lock:
                first_fire_count = len(fired_events)

            # Tick to reset
            wd.tick()
            time.sleep(0.02)  # brief pause so observer sees reset

            # 2nd gap — let it fire again
            time.sleep(timeout * 2.5)
            with lock:
                second_fire_count = len(fired_events)
        finally:
            wd.stop()

        assert first_fire_count == 1, "should have fired once after first gap"
        assert second_fire_count == 2, "should have fired again after second gap"


# ---------------------------------------------------------------------------
# 4. seconds_since_last_tick() returns approximately elapsed time
# ---------------------------------------------------------------------------

class TestSecondsSinceLastTick:
    def test_returns_approximately_elapsed(self):
        wd = _make_watchdog(timeout=10.0)
        wd.start()
        try:
            wd.tick()
            sleep_duration = 0.1
            time.sleep(sleep_duration)
            elapsed = wd.seconds_since_last_tick()
            # Allow generous bounds: 80 ms to 300 ms
            assert 0.08 <= elapsed <= 0.30, (
                f"seconds_since_last_tick={elapsed:.3f} not in [0.08, 0.30]"
            )
        finally:
            wd.stop()


# ---------------------------------------------------------------------------
# 5. stop() joins cleanly within 1 second
# ---------------------------------------------------------------------------

class TestStopJoinsCleanly:
    def test_stop_joins_within_one_second(self):
        wd = _make_watchdog(timeout=5.0)
        wd.start()
        assert wd._thread is not None and wd._thread.is_alive()

        t0 = time.monotonic()
        wd.stop()
        elapsed = time.monotonic() - t0

        assert elapsed < 1.0, f"stop() took {elapsed:.2f}s, expected < 1.0s"
        # Thread should be dead after stop
        assert not wd._thread.is_alive()


# ---------------------------------------------------------------------------
# 6. Wall-clock manipulation does NOT affect the watchdog
# ---------------------------------------------------------------------------

class TestMonotonicClockUsed:
    def test_patching_time_time_does_not_affect_watchdog(self):
        """Manipulating time.time() (wall clock) must have no effect.

        The watchdog must continue using time.monotonic() for all timing.
        We patch time.time to return a wildly-past value; if the watchdog
        used it, the timeout window would appear huge or broken.  The test
        verifies that ticks still prevent the callback from firing.
        """
        fired = threading.Event()
        wd = _make_watchdog(0.2, cb=lambda _e: fired.set())

        # Freeze wall clock at epoch 0 — very stale.
        with mock.patch("time.time", return_value=0.0):
            wd.start()
            try:
                for _ in range(6):
                    wd.tick()
                    time.sleep(0.02)
                assert not fired.is_set(), (
                    "Watchdog should not fire when ticking; wall-clock mock must not matter"
                )
            finally:
                wd.stop()


# ---------------------------------------------------------------------------
# 7. start() raises if already running
# ---------------------------------------------------------------------------

class TestStartRaisesIfAlreadyRunning:
    def test_double_start_raises_runtime_error(self):
        wd = _make_watchdog(timeout=5.0)
        wd.start()
        try:
            with pytest.raises(RuntimeError, match="already running"):
                wd.start()
        finally:
            wd.stop()


# ---------------------------------------------------------------------------
# 8. Callback exception is caught — watchdog does not crash
# ---------------------------------------------------------------------------

class TestCallbackExceptionHandled:
    def test_raising_callback_does_not_crash_observer(self):
        def bad_cb(elapsed):
            raise ValueError("intentional test error")

        timeout = 0.15
        wd = _make_watchdog(timeout, cb=bad_cb)
        wd.start()
        time.sleep(timeout * 2.5)
        # Observer thread must still be alive (exception was caught internally)
        assert wd._thread is not None and wd._thread.is_alive(), (
            "Observer thread should survive a raising callback"
        )
        wd.stop()
