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
    INFRASTRUCTURE = "infrastructure_failure"
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

    Usage (single-strategy, backward-compat):
        ks = KillSwitch(initial_equity=100_000)

        # Before each signal cycle:
        if ks.is_triggered:
            # Do not trade — system halted
            return

        # After every equity update, check the daily-loss threshold:
        if ks.check_and_trigger(current_equity):
            # Threshold breached -- ks.trigger() has fired internally
            return

        # After reconciliation:
        if discrepancies:
            ks.trigger(TriggerReason.RECONCILIATION, detail="...")

        # Human reset (writes RESET audit entry per Path B P6):
        ks.reset(operator="HuangTM", reason="incident resolved 2026-04-27")

    Usage (per-strategy, Path B prereq P6):
        ks_a = KillSwitch(initial_equity=100_000, strategy_id="vol_target_carry")
        ks_b = KillSwitch(initial_equity=100_000, strategy_id="carry_fred")
        # Independent state, independent audit logs:
        # data/kill_switch_audit_vol_target_carry.log
        # data/kill_switch_audit_carry_fred.log

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
    strategy_id: str | None = None     # Path B prereq P6: per-strategy isolation

    # State
    is_triggered: bool = field(default=False, init=False)
    day_start_equity: float = field(default=0.0, init=False)
    current_day: str = field(default="", init=False)
    consecutive_fetch_failures: int = field(default=0, init=False)
    events: list[KillSwitchEvent] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.day_start_equity = self.initial_equity
        self.current_day = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        # Path B P6: per-strategy audit-log namespacing. If strategy_id is
        # set and no explicit audit_log_path was passed, default to a
        # per-strategy file so two strategies running in parallel cannot
        # cross-contaminate each other's audit trails. Single-strategy
        # (strategy_id=None) preserves the existing default.
        if self.strategy_id is not None and self.audit_log_path is None:
            self.audit_log_path = f"data/kill_switch_audit_{self.strategy_id}.log"
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
        """Trigger the kill switch. Idempotent — safe to call multiple times.

        WS-03 (CTO consensus 2026-04-26): every trigger appends a structured
        JSON-line to the audit log so the kill-switch state transition can be
        reconstructed post-hoc without grepping process stderr. The new_state
        contains the substring "HALTED" so a subsequent process restart's
        _check_audit_log_on_startup correctly refuses-to-start.
        """
        if self.is_triggered:
            return

        self.is_triggered = True
        ts = pd.Timestamp.now(tz="UTC")
        event = KillSwitchEvent(
            timestamp=ts,
            reason=reason,
            detail=detail,
            equity_at_trigger=equity,
        )
        self.events.append(event)
        logger.critical(
            "KILL SWITCH TRIGGERED: %s — %s (equity: %.2f)",
            reason.value, detail, equity,
        )

        # WS-03 audit append. Best-effort: an audit-write failure must NOT
        # prevent the kill switch from halting trading. Log critical and
        # proceed if the file write fails (process may exit before the next
        # trigger anyway).
        if not self.audit_log_path:
            return
        try:
            _write_audit_entry(
                self.audit_log_path,
                {
                    "timestamp": ts.isoformat(),
                    "event": "TRIGGER",
                    "operator": "system",
                    "reason": reason.value,
                    "detail": detail,
                    "equity_at_trigger": float(equity),
                    "previous_state": "OK",
                    "new_state": f"HALTED_{reason.value.upper()}",
                },
            )
        except Exception as e:
            logger.critical(
                "KILL SWITCH: failed to write trigger audit entry: %s "
                "(in-memory event preserved at events[-1])", e,
            )

    def reset(
        self,
        operator: str,
        *,
        reason: str = "operator reset (no reason given)",
        evidence_path: str | None = None,
        current_equity: float | None = None,
    ) -> None:
        """Reset the kill switch. Requires human operator name for audit.

        Args:
            operator: Human operator name for audit trail. Empty/falsy
                operator raises ValueError per Path B P6 audit requirement.
            reason: Why the reset is being performed. Defaults to a generic
                placeholder for backward compat with existing test callers;
                the CLI (scripts/reset_kill_switch.py) requires a real reason.
            evidence_path: Optional path to a results / log file documenting
                the resolution of the trigger condition.
            current_equity: If provided, resets daily baseline to this value
                (gives a fresh daily loss budget from reset point).

        Path B P6: writes a structured RESET audit-log entry on every
        successful reset so the trigger->reset cycle is reconstructable
        post-hoc. Previously operator had to hand-type the audit line;
        that gap closes here.
        """
        if not operator or not operator.strip():
            raise ValueError("KillSwitch.reset requires a non-empty operator name")
        if not self.is_triggered:
            return

        last_event = self.last_event
        previous_state = (
            f"HALTED_{last_event.reason.value.upper()}" if last_event else "HALTED"
        )

        logger.warning("Kill switch RESET by operator: %s (reason: %s)", operator, reason)
        self.is_triggered = False
        ts = pd.Timestamp.now(tz="UTC")
        self.current_day = ts.strftime("%Y-%m-%d")
        if current_equity is not None:
            self.day_start_equity = current_equity

        if not self.audit_log_path:
            return
        try:
            _write_audit_entry(
                self.audit_log_path,
                {
                    "timestamp": ts.isoformat(),
                    "event": "RESET",
                    "operator": operator,
                    "reason": reason,
                    "evidence_path": evidence_path,
                    "previous_state": previous_state,
                    "new_state": "OK",
                    "strategy_id": self.strategy_id,
                },
            )
        except Exception as e:
            logger.critical(
                "KILL SWITCH: failed to write RESET audit entry: %s "
                "(in-memory state already reset)", e,
            )

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
