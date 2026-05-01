"""Dead-man switch for the paper-trading loop.

Design
------
The paper-trading loop calls ``HeartbeatWatchdog.tick()`` each cycle.
A background observer thread monitors the gap between ticks.  If the gap
exceeds ``timeout_seconds`` the watchdog calls ``on_timeout`` exactly once
(per window) and emits a structured log line.  A subsequent ``tick()``
resets the fired flag so a re-hang will fire again.

CRO binding constraint #2:
    No paper-trading dispatch unless a heartbeat/dead-man watchdog with
    ≤5 min timeout exists on the paper-trading loop.

Production callers MUST pass ``timeout_seconds=300.0`` (or less) explicitly.
There is NO silent default — this is intentional so the caller's intent
is visible at construction time.

Clock discipline:
    Uses ``time.monotonic()`` throughout.  Wall-clock (``time.time()``)
    can jump on NTP corrections; monotonic never goes backwards.  See the
    ``clock-and-ordering`` skill for full rationale.

Thread-safety:
    ``_last_tick`` and ``_timeout_fired`` are both protected by
    ``_lock`` (a ``threading.Lock``).  The observer thread acquires the
    lock for each read; ``tick()`` acquires it for each write.

Structured-log keys emitted on each transition (``extra=`` dict):
    event         : str   — one of STARTED / STOPPED / TICK / TIMEOUT_FIRED /
                            TIMEOUT_RESET
    timeout_seconds : float
    seconds_since_last_tick : float  (TICK, TIMEOUT_FIRED, TIMEOUT_RESET)
    on_timeout_callable : str  (STARTED)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger("heartbeat_watchdog")


@dataclass
class HeartbeatWatchdog:
    """Dead-man switch on a paper-trading loop.

    Caller calls ``.tick()`` each cycle; a separate observer thread raises
    an alarm (log + structured event + ``on_timeout`` callback) if no tick
    is observed within ``timeout_seconds``.

    Args:
        timeout_seconds: Maximum allowed gap between ticks.  Production callers
            MUST pass 300.0 or less per CRO binding constraint #2.  There is no
            silent default — the caller's intent must be explicit.
        on_timeout: Called with ``seconds_since_last_tick`` when the watchdog
            fires.  In production, wire this to halt the paper loop and emit a
            kill-switch event.  For this module the callback is a pure parameter;
            production wiring is a separate task.
    """

    timeout_seconds: float
    on_timeout: Callable[[float], None]

    # Internal state — not part of the public API; do not set at construction.
    _last_tick: float = field(default_factory=time.monotonic)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = field(default=None)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _timeout_fired: bool = field(default=False)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def tick(self) -> None:
        """Record that the paper-trading loop is alive.

        Updates the internal monotonic timestamp.  If a timeout had previously
        fired, the first tick after the gap resets the fired flag (so a
        subsequent hang will re-fire the alarm).

        Log level: DEBUG for normal ticks; INFO for a timeout-reset tick.
        """
        now = time.monotonic()
        with self._lock:
            elapsed = now - self._last_tick
            was_fired = self._timeout_fired
            self._last_tick = now
            if was_fired:
                self._timeout_fired = False

        if was_fired:
            logger.info(
                "heartbeat_watchdog tick (timeout-reset)",
                extra={
                    "event": "TIMEOUT_RESET",
                    "timeout_seconds": self.timeout_seconds,
                    "seconds_since_last_tick": elapsed,
                },
            )
        else:
            logger.debug(
                "heartbeat_watchdog tick",
                extra={
                    "event": "TICK",
                    "timeout_seconds": self.timeout_seconds,
                    "seconds_since_last_tick": elapsed,
                },
            )

    def start(self) -> None:
        """Start the observer thread.

        Raises:
            RuntimeError: If the watchdog is already running.
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("HeartbeatWatchdog is already running; call stop() first.")

        self._stop.clear()
        # Reset last_tick so the timeout window starts fresh from now.
        with self._lock:
            self._last_tick = time.monotonic()
            self._timeout_fired = False

        self._thread = threading.Thread(
            target=self._observer_loop,
            name="heartbeat-watchdog-observer",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "heartbeat_watchdog started",
            extra={
                "event": "STARTED",
                "timeout_seconds": self.timeout_seconds,
                "on_timeout_callable": repr(self.on_timeout),
            },
        )

    def stop(self) -> None:
        """Signal the observer thread to stop and join it (blocks ≤ ~poll interval + 1s)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self._poll_interval() * 2))
        logger.info(
            "heartbeat_watchdog stopped",
            extra={
                "event": "STOPPED",
                "timeout_seconds": self.timeout_seconds,
            },
        )

    def seconds_since_last_tick(self) -> float:
        """Return the elapsed monotonic seconds since the last tick."""
        with self._lock:
            return time.monotonic() - self._last_tick

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _poll_interval(self) -> float:
        """Observer sleep interval: min(1.0, timeout_seconds / 5)."""
        return min(1.0, self.timeout_seconds / 5.0)

    def _observer_loop(self) -> None:
        """Background thread: polls for missed ticks until stop() is called."""
        poll = self._poll_interval()
        while not self._stop.wait(timeout=poll):
            elapsed = self.seconds_since_last_tick()
            if elapsed > self.timeout_seconds:
                with self._lock:
                    already_fired = self._timeout_fired
                    if not already_fired:
                        self._timeout_fired = True

                if not already_fired:
                    logger.critical(
                        "heartbeat_watchdog TIMEOUT: no tick for %.2fs (threshold %.2fs)",
                        elapsed,
                        self.timeout_seconds,
                        extra={
                            "event": "TIMEOUT_FIRED",
                            "timeout_seconds": self.timeout_seconds,
                            "seconds_since_last_tick": elapsed,
                        },
                    )
                    try:
                        self.on_timeout(elapsed)
                    except Exception:
                        logger.exception(
                            "heartbeat_watchdog: on_timeout callback raised an exception"
                        )
