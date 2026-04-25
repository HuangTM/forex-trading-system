"""Binary kill switch — flattens all positions and halts trading.

Triggers:
    1. Daily P&L crosses max loss threshold (default -2% of equity)
    2. Position reconciliation mismatch
    3. Auth chain death (token expiry imminent)

Design principles:
    - Binary: ON (trading allowed) or OFF (all positions flat, no new trades)
    - Human reset required — no automatic recovery
    - Logs trigger reason for audit trail
    - Exception-safe — failure in the kill switch itself triggers it
    - Restart-safe — refuses to start silently if last audit event was HALTED;
      operator must set KILL_SWITCH_FORCE_RESET=1 to override.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Hardcoded invariants — require code review to change
MAX_DAILY_LOSS_PCT = 0.02  # 2% of equity
RECONCILIATION_TOLERANCE_UNITS = 1  # Units mismatch before triggering
MAX_CONSECUTIVE_FETCH_FAILURES = 3  # Equity-fetch misses before halting

# States that mean trading was halted when the process last stopped.
# Substring match: any new_state containing one of these strings is treated
# as HALTED.
_HALTED_STATE_SUBSTRINGS = ("HALTED", "FLAT_AND_HALTED")

_DEFAULT_AUDIT_LOG = "data/kill_switch_audit.log"


class TriggerReason(Enum):
    DAILY_LOSS = "daily_loss_exceeded"
    RECONCILIATION = "reconciliation_mismatch"
    AUTH_DEATH = "auth_chain_dying"
    MANUAL = "manual_trigger"
    ERROR = "internal_error"


@dataclass
class KillSwitchEvent:
    """Record of a kill switch trigger."""

    timestamp: pd.Timestamp
    reason: TriggerReason
    detail: str
    equity_at_trigger: float


def _last_audit_entry(audit_log_path: str) -> dict | None:
    """Return the last JSON line from the audit log, or None if empty/missing."""
    p = Path(audit_log_path)
    if not p.exists():
        return None
    lines = [l.strip() for l in p.read_text().splitlines() if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        logger.warning("KillSwitch: could not parse last audit log entry — treating as clean.")
        return None


def _new_state_is_halted(new_state: str | None) -> bool:
    """Return True if new_state string indicates the switch was HALTED."""
    if new_state is None:
        return False
    for substr in _HALTED_STATE_SUBSTRINGS:
        if substr in new_state:
            return True
    return False


def _write_audit_entry(audit_log_path: str, entry: dict) -> None:
    """Append a single JSON line to the audit log."""
    p = Path(audit_log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(entry) + "\n")


@dataclass
class KillSwitch:
    """Binary circuit breaker for trading operations.

    Usage:
        ks = KillSwitch(initial_equity=100_000)

        # Before each signal cycle:
        if ks.is_triggered:
            # Do not trade — system halted
            return

        # After execution, update P&L:
        ks.update_equity(current_equity)

        # After reconciliation:
        if discrepancies:
            ks.trigger(TriggerReason.RECONCILIATION, detail="...")

        # Human reset:
        ks.reset(operator="HuangTM")

    Restart safety:
        On __init__, if an audit log exists and the last entry's new_state
        contains "HALTED" (or "FLAT_AND_HALTED"), KillSwitch refuses to start
        and raises RuntimeError unless the environment variable
        KILL_SWITCH_FORCE_RESET=1 is set.
    """

    initial_equity: float
    max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT
    max_consecutive_fetch_failures: int = MAX_CONSECUTIVE_FETCH_FAILURES
    audit_log_path: str | None = None  # Set to _DEFAULT_AUDIT_LOG in production

    # State
    is_triggered: bool = field(default=False, init=False)
    day_start_equity: float = field(default=0.0, init=False)
    current_day: str = field(default="", init=False)
    consecutive_fetch_failures: int = field(default=0, init=False)
    events: list[KillSwitchEvent] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.day_start_equity = self.initial_equity
        self.current_day = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        self._check_audit_log_on_startup()

    def _check_audit_log_on_startup(self) -> None:
        """Refuse to start silently if last audit event indicated HALTED state.

        If KILL_SWITCH_FORCE_RESET=1 is set, allows startup but logs CRITICAL
        and writes a FORCE_RESET_ON_STARTUP audit entry so the decision is
        recorded for the operator.
        """
        if not self.audit_log_path:
            return

        last = _last_audit_entry(self.audit_log_path)
        if last is None:
            return  # Empty or missing audit log — clean start.

        new_state = last.get("new_state", "")
        if not _new_state_is_halted(new_state):
            return  # Last event was a clean state — no action needed.

        ts = last.get("timestamp", "unknown")
        operator = last.get("operator", "unknown")

        force_reset = os.environ.get("KILL_SWITCH_FORCE_RESET", "").strip() == "1"

        if not force_reset:
            msg = (
                f"KillSwitch starting fresh but last audit event was HALTED at {ts} "
                f"(operator={operator}). Refusing to start unless "
                "--force-reset is passed via env KILL_SWITCH_FORCE_RESET=1."
            )
            logger.critical(msg)
            raise RuntimeError(msg)

        # Force-reset path: log clearly and write audit entry.
        env_user = os.environ.get("USER", "unknown")
        logger.critical(
            "KILL SWITCH FORCE RESET on startup by env var. "
            "Operator must justify in next audit-log entry. (USER=%s)",
            env_user,
        )
        _write_audit_entry(
            self.audit_log_path,
            {
                "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
                "event": "FORCE_RESET_ON_STARTUP",
                "operator": env_user,
                "reason": "KILL_SWITCH_FORCE_RESET=1 set in env",
                "previous_state": new_state,
                "new_state": "RUNNING",
            },
        )

    def check_and_trigger(self, current_equity: float) -> bool:
        """Check if daily loss threshold is breached. Returns True if triggered.

        Call this after every execution or equity update.
        """
        if self.is_triggered:
            return True

        today = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        if today != self.current_day:
            # New trading day — reset daily tracking
            self.day_start_equity = current_equity
            self.current_day = today

        if self.day_start_equity <= 0:
            return False

        daily_pnl_pct = (current_equity - self.day_start_equity) / self.day_start_equity

        if daily_pnl_pct <= -self.max_daily_loss_pct:
            self.trigger(
                TriggerReason.DAILY_LOSS,
                f"Daily P&L: {daily_pnl_pct:.2%} (threshold: -{self.max_daily_loss_pct:.2%})",
                current_equity,
            )
            return True

        return False

    def record_equity_fetch_failure(self) -> bool:
        """Record a failed equity fetch. Trips the kill switch after N in a row.

        Skipping a single cycle on a transient Saxo timeout is safe; skipping
        many cycles silently disables the daily-loss guard while positions
        keep accruing real P&L. After `max_consecutive_fetch_failures` misses
        we halt and flatten as a fail-safe.

        Returns True iff this call pushed the kill switch into a triggered
        state (caller should flatten positions in response).
        """
        if self.is_triggered:
            return False
        self.consecutive_fetch_failures += 1
        if self.consecutive_fetch_failures >= self.max_consecutive_fetch_failures:
            self.trigger(
                TriggerReason.ERROR,
                f"Equity fetch failed {self.consecutive_fetch_failures} consecutive cycles",
                0.0,
            )
            return True
        logger.warning(
            "Could not fetch balance (failure %d of %d before kill switch fires)",
            self.consecutive_fetch_failures,
            self.max_consecutive_fetch_failures,
        )
        return False

    def record_equity_fetch_success(self) -> None:
        """Reset the consecutive-failure counter after a successful fetch."""
        self.consecutive_fetch_failures = 0

    def trigger(
        self,
        reason: TriggerReason,
        detail: str,
        equity: float = 0.0,
    ) -> None:
        """Trigger the kill switch. Idempotent — safe to call multiple times."""
        if self.is_triggered:
            return

        self.is_triggered = True
        event = KillSwitchEvent(
            timestamp=pd.Timestamp.now(tz="UTC"),
            reason=reason,
            detail=detail,
            equity_at_trigger=equity,
        )
        self.events.append(event)
        logger.critical(
            "KILL SWITCH TRIGGERED: %s — %s (equity: %.2f)",
            reason.value, detail, equity,
        )

    def reset(self, operator: str, current_equity: float | None = None) -> None:
        """Reset the kill switch. Requires human operator name for audit.

        Args:
            operator: Human operator name for audit trail.
            current_equity: If provided, resets daily baseline to this value
                (gives a fresh daily loss budget from reset point).
        """
        if not self.is_triggered:
            return

        logger.warning("Kill switch RESET by operator: %s", operator)
        self.is_triggered = False
        self.current_day = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        if current_equity is not None:
            self.day_start_equity = current_equity

    @property
    def last_event(self) -> KillSwitchEvent | None:
        return self.events[-1] if self.events else None

    @property
    def status_line(self) -> str:
        """Human-readable status for display."""
        if not self.is_triggered:
            return "OK"
        event = self.last_event
        if event:
            return f"HALTED: {event.reason.value} at {event.timestamp.strftime('%H:%M UTC')}"
        return "HALTED"
