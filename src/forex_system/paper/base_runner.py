"""PaperRunnerBase — shared paper-trading execution infrastructure.

REM-2 (CTO D-2.1, D-2.2): Canonical base class for all per-strategy paper runners.
Located at src/forex_system/paper/base_runner.py per CTO decision D-2.1.

Class name: PaperRunnerBase per CTO decision D-2.2.

Full REM-2 extraction (2026-05-13):
    COND-1 through COND-7 are fully extracted into this base class.
    Both paper scripts (run_paper_trading_vt.py, run_paper_trading_carry_fred.py)
    inherit PaperRunnerBase and delegate all BC-8-LIFT-COND guards here.

BC-8-LIFT-COND extraction status:
    COND-1: kill_switch hook — EXTRACTED (Phase-A; 2026-05-13)
    COND-2: drawdown_contract (AggregateDrawdownContract) — EXTRACTED (2026-05-13)
    COND-3: account_key parity gate — EXTRACTED (2026-05-13)
    COND-4: heartbeat watchdog registration — EXTRACTED (2026-05-13)
    COND-5: fcntl dispatch lock — EXTRACTED (2026-05-13)
    COND-6: JPY-correlated cap wiring — EXTRACTED (2026-05-13)
    COND-7: swap accrual call — EXTRACTED (2026-05-13)

AggregateDrawdownContract cardinality-1 invariant (LTCM defense, CRO R-7.1):
    Exactly ONE AggregateDrawdownContract instance per loop run.
    It is instantiated externally and passed into PaperRunnerBase.__init__.
    PaperRunnerBase does NOT create a second instance.
    Both paper scripts pass the same AggregateDrawdownContract they create
    in main() — this preserves cardinality-1 across both runners.

N-2 relocation invariants (NHT mandate):
    The architectural invariant is: the set of distinct AST nodes implementing
    BC-8-LIFT-COND-1..7 across all paper scripts must have cardinality 1
    (only in BaseRunner). Tests enforce this:
        tests/integration/test_paper_runner_bc8_conds.py (REM-2-T1)
        tests/strategies/test_rem1_liskov_fix.py::test_no_feature_flag_kill_switch_bypass (N-2)

    No monkey-patching of BaseRunner methods is permitted.
    No env-var-conditioned suppression of kill switches is permitted.

Observability boundaries per PM acceptance-criteria REM-2:
    1. PaperRunnerBase.__init__ emits a structured startup log line listing which
       BC-8-LIFT-COND guards are active (as a list of string IDs).
    2. Each guard's entry and exit logs strategy_id + condition_id + outcome.
"""

from __future__ import annotations

import fcntl
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class DispatchStaggerConfigError(Exception):
    """Raised when dispatch_stagger_offsets_seconds config is too short.

    F-005 / D-4.1 FM-4: config must have at least one offset per active strategy.
    A config shorter than len(active_strategies) would cause an out-of-range index
    at dispatch time, silently applying offset 0 to some strategies and recreating
    the storm pattern the stagger is meant to prevent.
    """


# Sentinel yielded by _acquire_dispatch_lock on OS-level error (not BlockingIOError).
# Distinct from False (BUSY) so callers can emit SKIP_DISPATCH_LOCK_FS_ERROR.
# F-101 (CRO Decision B): OSError triggers kill-switch + returns this sentinel.
_DISPATCH_LOCK_FS_ERROR: object = object()  # identity-checked, never falsely equals False


# Active BC-8-LIFT-COND guards (all 7 extracted — CTO wave-2 COND-A2: phase-A
# prefix is a temporal artifact; renamed to _ACTIVE_GUARDS).
_ACTIVE_GUARDS = [
    "BC-8-LIFT-COND-1",
    "BC-8-LIFT-COND-2",
    "BC-8-LIFT-COND-3",
    "BC-8-LIFT-COND-4",
    "BC-8-LIFT-COND-5",
    "BC-8-LIFT-COND-6",
    "BC-8-LIFT-COND-7",
]


class PaperRunnerBase:
    """Abstract base class for all paper-trading runners.

    Per-strategy subclasses (e.g., VtPaperRunner, CarryFredPaperRunner) inherit
    this class and implement the strategy-specific logic. The base class provides
    all BC-8-LIFT-COND risk-envelope logic as single-source-of-truth methods.

    All 7 BC-8-LIFT-COND guards are active (full REM-2 extraction).

    Args:
        strategy_id: Identifying string for this runner's strategy. Used in
            audit logs and kill switch namespacing.
        kill_switch: KillSwitch instance for this strategy. Required.
        aggregate_dd_contract: AggregateDrawdownContract instance (COND-2).
            Must be instantiated ONCE externally (cardinality-1 invariant, LTCM
            defense). Required for COND-2 to be active; None disables COND-2
            (only for test contexts where AggDD is explicitly opted out).
        account_key: Saxo account key for COND-3 parity gate. If provided (with
            loop_name), assert_account_key_parity is called at init. Pass None
            to skip (e.g., in tests where no Saxo connection is available).
        loop_name: Human-readable name of this paper loop (e.g. "vt loop").
            Required when account_key is provided.
        heartbeat_watchdog: HeartbeatWatchdog instance (COND-4). If provided,
            stored for tick() calls. Start/stop is the caller's responsibility
            (the watchdog is typically started before the loop begins).
        dispatch_lock_path: Path to the fcntl advisory lock file (COND-5).
            Defaults to "data/dispatch_lock.flock". Shared between all runners
            on the same machine.

    Instantiation observability (REM-2):
        __init__ logs which BC-8-LIFT-COND guards are active at startup.
        All 7 conditions are listed post-full-extraction.
    """

    def __init__(
        self,
        strategy_id: str,
        kill_switch,  # KillSwitch — avoid circular import; type-checked at runtime
        aggregate_dd_contract=None,  # AggregateDrawdownContract | None
        account_key: Optional[str] = None,
        loop_name: Optional[str] = None,
        heartbeat_watchdog=None,  # HeartbeatWatchdog | None
        dispatch_lock_path: str = "data/dispatch_lock.flock",
    ) -> None:
        if not strategy_id or not strategy_id.strip():
            raise ValueError("PaperRunnerBase requires a non-empty strategy_id")
        if kill_switch is None:
            raise ValueError(
                "PaperRunnerBase requires a kill_switch instance. "
                "A paper runner without a kill switch violates BC-8-LIFT-COND-1."
            )

        self.strategy_id = strategy_id
        self._kill_switch = kill_switch

        # COND-2: AggregateDrawdownContract (cardinality-1 enforced at caller site)
        self._aggregate_dd_contract = aggregate_dd_contract

        # COND-3: account_key parity gate — enforced at startup if account_key provided
        if account_key is not None:
            if not loop_name:
                raise ValueError(
                    "loop_name is required when account_key is provided (COND-3 parity gate). "
                    "Pass loop_name='<strategy> loop' to PaperRunnerBase.__init__."
                )
            from forex_system.risk.account_key_parity import assert_account_key_parity
            # PR F-001 fix: never log full account_key (PII; Wave-10 sanitization discipline).
            # Show last 4 chars only, prefixed with ellipsis, so log readers can verify
            # which key was used without leaking the credential.
            account_key_redacted = (
                "***" + account_key[-4:] if account_key and len(account_key) >= 4 else "***"
            )
            logger.info(
                "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-3 outcome=CHECKING",
                strategy_id,
                extra={
                    "strategy_id": strategy_id,
                    "condition_id": "BC-8-LIFT-COND-3",
                    "outcome": "CHECKING",
                    "account_key": account_key_redacted,
                    "loop_name": loop_name,
                },
            )
            assert_account_key_parity(account_key, loop_name=loop_name)
            logger.info(
                "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-3 outcome=OK",
                strategy_id,
                extra={
                    "strategy_id": strategy_id,
                    "condition_id": "BC-8-LIFT-COND-3",
                    "outcome": "OK",
                },
            )

        # COND-4: heartbeat watchdog registration
        self._heartbeat_watchdog = heartbeat_watchdog
        if heartbeat_watchdog is not None:
            logger.info(
                "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-4 outcome=REGISTERED "
                "watchdog_timeout_seconds=%s",
                strategy_id,
                getattr(heartbeat_watchdog, "timeout_seconds", "unknown"),
            )

        # COND-5: dispatch lock path
        self._dispatch_lock_path = dispatch_lock_path

        # REM-2 observability boundary: log ALL active guards at startup
        logger.info(
            "paper_runner_startup strategy_id=%s active_bc8_lift_cond_guards=%s "
            "note='full REM-2 extraction complete; all 7 conditions active'",
            strategy_id,
            _ACTIVE_GUARDS,
        )

    # ---------------------------------------------------------------------------
    # BC-8-LIFT-COND-1: Kill switch hook (EXTRACTED — Phase-A)
    # ---------------------------------------------------------------------------

    def _check_kill_switch(self) -> bool:
        """BC-8-LIFT-COND-1: Check kill switch state at cycle entry.

        Returns True if trading is allowed; False if kill switch is triggered.
        Callers MUST return early (halt dispatch) when this method returns False.

        Observability: logs strategy_id + condition_id + outcome per REM-2 boundary.
        """
        triggered = self._kill_switch.is_triggered
        outcome = "HALTED" if triggered else "OK"
        logger.info(
            "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-1 outcome=%s",
            self.strategy_id,
            outcome,
            extra={
                "strategy_id": self.strategy_id,
                "condition_id": "BC-8-LIFT-COND-1",
                "outcome": outcome,
            },
        )
        return not triggered

    # ---------------------------------------------------------------------------
    # BC-8-LIFT-COND-2: AggregateDrawdownContract check
    # ---------------------------------------------------------------------------

    def _check_aggregate_drawdown(
        self,
        equity: float,
        contributing_strategies: list,
        *,
        snapshot_timestamp: Optional[datetime] = None,
    ):
        """BC-8-LIFT-COND-2: Evaluate aggregate drawdown ladder.

        Returns the AggregateDrawdownAssessment if aggregate_dd_contract is wired;
        returns None if aggregate_dd_contract was not provided at construction.

        Callers MUST check assessment.force_flat and assessment.allows_new_dispatch
        to gate dispatch. See run_cycle in both paper scripts for the gating pattern.

        Args:
            equity: Current account equity from broker fetch.
            contributing_strategies: List of strategy_id strings contributing to
                this equity snapshot (for observability).
            snapshot_timestamp: UTC datetime of broker equity fetch (clock-and-ordering).
                Defaults to datetime.now(timezone.utc) if not provided.

        Observability: logs strategy_id + condition_id + outcome.
        """
        if self._aggregate_dd_contract is None:
            logger.debug(
                "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-2 outcome=SKIP "
                "reason=no_aggregate_dd_contract_wired",
                self.strategy_id,
            )
            return None

        if snapshot_timestamp is None:
            snapshot_timestamp = datetime.now(timezone.utc)

        assessment = self._aggregate_dd_contract.update_equity(
            equity,
            snapshot_timestamp=snapshot_timestamp,
            contributing_strategies=contributing_strategies,
        )

        if assessment.force_flat:
            outcome = "LOCKOUT"
        elif not assessment.allows_new_dispatch:
            outcome = "HALT"
        elif assessment.sizing_multiplier < 1.0:
            outcome = "HALVE"
        else:
            outcome = "OK"

        logger.info(
            "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-2 outcome=%s",
            self.strategy_id,
            outcome,
            extra={
                "strategy_id": self.strategy_id,
                "condition_id": "BC-8-LIFT-COND-2",
                "outcome": outcome,
                "aggregate_drawdown_pct": assessment.aggregate_drawdown_pct,
                "sizing_multiplier": assessment.sizing_multiplier,
            },
        )
        return assessment

    # ---------------------------------------------------------------------------
    # BC-8-LIFT-COND-3: account_key parity gate (enforced at __init__)
    # ---------------------------------------------------------------------------
    # The parity gate is enforced once at construction (startup gate per SEC 15c3-5).
    # No per-cycle method required; the gate fires at instantiation and calls
    # sys.exit(1) on violation (fail-closed). The __init__ above handles this.

    # ---------------------------------------------------------------------------
    # BC-8-LIFT-COND-4: HeartbeatWatchdog registration
    # ---------------------------------------------------------------------------

    def _tick_heartbeat(self) -> None:
        """BC-8-LIFT-COND-4: Emit a heartbeat tick on the registered watchdog.

        Callers MUST call this at the START of each dispatch cycle to satisfy
        the bounded-interval semantics. If no watchdog is registered (test
        contexts), this is a no-op.

        Observability: logs strategy_id + condition_id + outcome.
        """
        if self._heartbeat_watchdog is None:
            logger.debug(
                "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-4 outcome=SKIP "
                "reason=no_watchdog_registered",
                self.strategy_id,
            )
            return

        self._heartbeat_watchdog.tick()
        logger.debug(
            "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-4 outcome=TICKED",
            self.strategy_id,
        )

    # ---------------------------------------------------------------------------
    # BC-8-LIFT-COND-5: fcntl dispatch lock
    # ---------------------------------------------------------------------------

    @contextmanager
    def _acquire_dispatch_lock(
        self,
        cycle_id: Optional[int] = None,
        pair: Optional[str] = None,
    ) -> Generator[bool, None, None]:
        """BC-8-LIFT-COND-5: Acquire process-level fcntl advisory dispatch lock.

        Yields True on successful acquisition. On BlockingIOError (lock busy),
        logs the skip and yields False WITHOUT entering the lock body — the caller
        MUST handle the False case by returning SKIP_DISPATCH_LOCK_BUSY.

        On unexpected OSError, triggers the kill switch and yields False.

        The lock is automatically released in the finally block on all exit paths.

        Usage::

            with self._acquire_dispatch_lock(cycle_id=cycle_id, pair=pair) as locked:
                if not locked:
                    return {"_action": SKIP_DISPATCH_LOCK_BUSY}
                # ... dispatch logic inside the lock ...

        Observability: logs strategy_id + condition_id + outcome + lock_path.
        """
        from forex_system.risk.kill_switch import TriggerReason

        _dl_path = Path(self._dispatch_lock_path)
        _dl_path.parent.mkdir(parents=True, exist_ok=True)
        _dl_fd = os.open(str(_dl_path), os.O_CREAT | os.O_WRONLY, 0o644)
        _acquired = False

        try:
            fcntl.flock(_dl_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _acquired = True
            _acquire_ts = datetime.now(timezone.utc).isoformat()
            logger.info(
                "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-5 outcome=ACQUIRED",
                self.strategy_id,
                extra={
                    "strategy_id": self.strategy_id,
                    "condition_id": "BC-8-LIFT-COND-5",
                    "outcome": "ACQUIRED",
                    "lock_path": self._dispatch_lock_path,
                    "cycle_id": cycle_id,
                    "pair": pair,
                    "acquire_ts": _acquire_ts,
                },
            )
            yield True
        except BlockingIOError:
            os.close(_dl_fd)
            _dl_fd = -1
            logger.warning(
                "bc8_cond_check condition_id=BC-8-LIFT-COND-5 outcome=BUSY",
                extra={
                    "strategy_id": self.strategy_id,
                    "condition_id": "BC-8-LIFT-COND-5",
                    "outcome": "BUSY",
                    "lock_path": self._dispatch_lock_path,
                    "cycle_id": cycle_id,
                    "pair": pair,
                    "decision_ts": datetime.now(timezone.utc).isoformat(),
                },
            )
            yield False
        except OSError as exc:
            os.close(_dl_fd)
            _dl_fd = -1
            logger.warning(
                "bc8_cond_check condition_id=BC-8-LIFT-COND-5 outcome=FS_ERROR",
                extra={
                    "strategy_id": self.strategy_id,
                    "condition_id": "BC-8-LIFT-COND-5",
                    "outcome": "FS_ERROR",
                    "lock_path": self._dispatch_lock_path,
                    "cycle_id": cycle_id,
                    "pair": pair,
                    "errno": getattr(exc, "errno", None),
                    "strerror": getattr(exc, "strerror", None) or repr(exc),
                    "decision_ts": datetime.now(timezone.utc).isoformat(),
                },
            )
            self._kill_switch.trigger(
                TriggerReason.INFRASTRUCTURE,
                detail=(
                    f"dispatch_lock_fs_error: errno={getattr(exc, 'errno', None)}"
                    f" strerror={getattr(exc, 'strerror', None) or repr(exc)}"
                ),
            )
            # F-101: yield _DISPATCH_LOCK_FS_ERROR sentinel (not False/BUSY) so
            # callers can distinguish OS-level error from LOCK_NB contention.
            yield _DISPATCH_LOCK_FS_ERROR
        finally:
            if _dl_fd >= 0:
                if _acquired:
                    fcntl.flock(_dl_fd, fcntl.LOCK_UN)
                    logger.info(
                        "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-5 outcome=RELEASED",
                        self.strategy_id,
                        extra={
                            "strategy_id": self.strategy_id,
                            "condition_id": "BC-8-LIFT-COND-5",
                            "outcome": "RELEASED",
                            "lock_path": self._dispatch_lock_path,
                            "cycle_id": cycle_id,
                            "release_ts": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                os.close(_dl_fd)

    # ---------------------------------------------------------------------------
    # BC-8-LIFT-COND-6: JPY-correlated cap check
    # ---------------------------------------------------------------------------

    def _check_jpy_correlated_cap(
        self,
        positions: list,
        *,
        max_correlated_pct: float,
        max_active_strategies: int,
        max_concurrent_positions: int,
        cycle_id: Optional[int] = None,
        pair: Optional[str] = None,
        equity: Optional[float] = None,
    ) -> bool:
        """BC-8-LIFT-COND-6: Check JPY-correlated exposure cap before dispatch.

        Calls compute_exposure + check_dispatch_allowed. Returns True if dispatch
        is allowed; returns False if the aggregation gate is blocked (caller should
        return SKIP_AGGREGATION_GATE).

        Raises AggregationGateBlocked internally and converts to False return;
        logs the block reason.

        Args:
            positions: List of currently open Position objects.
            max_correlated_pct: CRO cap (e.g. 0.15 for 15%).
            max_active_strategies: CRO envelope limit.
            max_concurrent_positions: CRO envelope limit.
            cycle_id: For observability logging.
            pair: For observability logging.
            equity: For observability logging.

        Returns:
            True if dispatch allowed; False if blocked.

        Observability: logs strategy_id + condition_id + outcome + jpy_correlated_pct.
        """
        from forex_system.risk.exposure_aggregator import (
            AggregationGateBlocked,
            check_dispatch_allowed,
            compute_exposure,
        )

        exposure = compute_exposure(positions)
        try:
            check_dispatch_allowed(
                exposure,
                max_correlated_pct=max_correlated_pct,
                max_active_strategies=max_active_strategies,
                max_concurrent_positions=max_concurrent_positions,
            )
        except AggregationGateBlocked as exc:
            logger.warning(
                "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-6 outcome=BLOCKED",
                self.strategy_id,
                extra={
                    "strategy_id": self.strategy_id,
                    "condition_id": "BC-8-LIFT-COND-6",
                    "outcome": "BLOCKED",
                    "reason": str(exc),
                    "jpy_correlated_pct": exposure.jpy_correlated_pct,
                    "active_strategies": exposure.active_paper_strategies,
                    "open_positions": exposure.concurrent_open_positions,
                    "cycle_id": cycle_id,
                    "pair": pair,
                    "equity": equity,
                },
            )
            return False

        logger.info(
            "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-6 outcome=OK",
            self.strategy_id,
            extra={
                "strategy_id": self.strategy_id,
                "condition_id": "BC-8-LIFT-COND-6",
                "outcome": "OK",
                "jpy_correlated_pct": exposure.jpy_correlated_pct,
                "active_strategies": exposure.active_paper_strategies,
                "open_positions": exposure.concurrent_open_positions,
                "cycle_id": cycle_id,
                "pair": pair,
            },
        )
        return True

    # ---------------------------------------------------------------------------
    # BC-8-LIFT-COND-7: Swap accrual
    # ---------------------------------------------------------------------------

    def _accrue_swap(
        self,
        pair: str,
        held_units_nom: float,
        mid: float,
        last_cycle_ts: Optional[datetime],
        cost_model,  # RealisticCostModel — avoid circular import
    ) -> tuple[float, datetime]:
        """BC-8-LIFT-COND-7: Compute swap accrual for held position.

        Returns (swap_usd, now_ts) where swap_usd is the swap credit/debit for
        the interval since last_cycle_ts, and now_ts is the current UTC timestamp
        to be stored as the new last_cycle_ts.

        swap_usd > 0 means a carry credit (e.g. USDJPY long); < 0 means a cost.

        The swap computation mirrors engine.py:316-317 continuous-mode daily swap:
            holding_cost(pair, LONG, 1) returns -swap_long_pips_per_day
            (positive return = money lost; negative = carry credit).
        F-001 JPY correction: held_engine_units = held_units_nom / mid for JPY pairs.

        Observability: logs strategy_id + condition_id + outcome + swap_usd.

        Args:
            pair: Currency pair string (e.g. "USDJPY").
            held_units_nom: USD-nominal position size before this cycle's action.
            mid: Mid-market price used for JPY unit conversion.
            last_cycle_ts: UTC timestamp of previous cycle; None on first cycle.
            cost_model: RealisticCostModel instance.

        Returns:
            (swap_usd, now_ts)
        """
        from forex_system.core.types import Direction

        now_ts = datetime.now(timezone.utc)
        pip_v = 0.01 if "JPY" in pair.upper() else 0.0001
        held_engine_units = (
            (held_units_nom / mid) if ("JPY" in pair.upper() and mid > 0) else held_units_nom
        )

        swap_usd = 0.0
        if held_units_nom > 0 and last_cycle_ts is not None:
            days_elapsed = (now_ts - last_cycle_ts).total_seconds() / 86_400.0
            swap_pips_per_day = -cost_model.holding_cost(pair, Direction.LONG, 1)
            swap_usd = swap_pips_per_day * pip_v * held_engine_units * days_elapsed

        logger.info(
            "bc8_cond_check strategy_id=%s condition_id=BC-8-LIFT-COND-7 outcome=ACCRUED",
            self.strategy_id,
            extra={
                "strategy_id": self.strategy_id,
                "condition_id": "BC-8-LIFT-COND-7",
                "outcome": "ACCRUED",
                "pair": pair,
                "held_units_nom": held_units_nom,
                "held_engine_units": held_engine_units,
                "swap_usd": swap_usd,
                "days_elapsed": (
                    f"{(now_ts - last_cycle_ts).total_seconds() / 86_400.0:.6f}"
                    if last_cycle_ts is not None else "N/A"
                ),
            },
        )
        return swap_usd, now_ts

    # ---------------------------------------------------------------------------
    # F-005 / D-4.1: Dispatch stagger config validation
    # ---------------------------------------------------------------------------

    def _validate_dispatch_stagger_config(
        self,
        config: dict,
        active_strategies: list[str],
    ) -> None:
        """Validate that dispatch_stagger_offsets_seconds has enough entries.

        F-005 / D-4.1 FM-4: reads config['paper']['dispatch_stagger_offsets_seconds']
        and asserts len(offsets) >= len(active_strategies). On violation: emits
        a CRITICAL structured log line and raises DispatchStaggerConfigError.

        Args:
            config: The loaded config dict (typically from load_config).
            active_strategies: List of strategy_id strings that will be dispatched.

        Raises:
            DispatchStaggerConfigError: offsets list is shorter than active_strategies.
        """
        paper_cfg = config.get("paper", {}) if isinstance(config, dict) else {}
        offsets = paper_cfg.get("dispatch_stagger_offsets_seconds", [])

        if len(offsets) < len(active_strategies):
            log_extra = {
                "event": "DISPATCH_STAGGER_CONFIG_INVALID",
                "config_key": "paper.dispatch_stagger_offsets_seconds",
                "expected_min_length": len(active_strategies),
                "actual_length": len(offsets),
                "active_strategies": active_strategies,
            }
            logger.critical(
                "dispatch_stagger_config_invalid: "
                "config_key=paper.dispatch_stagger_offsets_seconds "
                "expected_min_length=%d actual_length=%d active_strategies=%s — "
                "CRITICAL: config too short; storm risk if strategies assigned offset 0",
                len(active_strategies),
                len(offsets),
                active_strategies,
                extra=log_extra,
            )
            raise DispatchStaggerConfigError(
                f"paper.dispatch_stagger_offsets_seconds has {len(offsets)} entries "
                f"but {len(active_strategies)} active strategies require at least "
                f"{len(active_strategies)} entries. "
                "F-005 D-4.1 FM-4: risk of storm pattern if strategies share offset 0."
            )

        # Log the consumed stagger offsets per REM-4 observability boundary
        for i, strategy_id in enumerate(active_strategies):
            offset_seconds = offsets[i]
            logger.info(
                "dispatch_stagger_offset_assigned "
                "strategy_id=%s scheduled_offset_seconds=%s",
                strategy_id,
                offset_seconds,
                extra={
                    "event": "DISPATCH_STAGGER_OFFSET_ASSIGNED",
                    "strategy_id": strategy_id,
                    "scheduled_offset_seconds": offset_seconds,
                    "config_key": "paper.dispatch_stagger_offsets_seconds",
                },
            )

    # ---------------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------------

    @property
    def kill_switch(self):
        """Expose kill switch for testing and BC-8-LIFT-COND verification."""
        return self._kill_switch

    @property
    def aggregate_dd_contract(self):
        """Expose AggregateDrawdownContract for testing and COND-2 verification."""
        return self._aggregate_dd_contract

    @property
    def heartbeat_watchdog(self):
        """Expose heartbeat watchdog for testing and COND-4 verification."""
        return self._heartbeat_watchdog

    @property
    def active_guards(self) -> list[str]:
        """List of active BC-8-LIFT-COND guard IDs (for observability)."""
        return list(_ACTIVE_GUARDS)
