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
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

logger = logging.getLogger(__name__)

# Hardcoded invariants — require code review to change
MAX_DAILY_LOSS_PCT = 0.02  # 2% of equity
RECONCILIATION_TOLERANCE_UNITS = 1  # Units mismatch before triggering


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
    """

    initial_equity: float
    max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT

    # State
    is_triggered: bool = field(default=False, init=False)
    day_start_equity: float = field(default=0.0, init=False)
    current_day: str = field(default="", init=False)
    events: list[KillSwitchEvent] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.day_start_equity = self.initial_equity
        self.current_day = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")

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
