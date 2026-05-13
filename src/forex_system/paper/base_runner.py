"""PaperRunnerBase — shared paper-trading execution infrastructure.

REM-2 (CTO D-2.1, D-2.2): Canonical base class for all per-strategy paper runners.
Located at src/forex_system/paper/base_runner.py per CTO decision D-2.1.

Class name: PaperRunnerBase per CTO decision D-2.2.

Phase-A dispatch (2026-05-13):
    This is a PHASE-A SCAFFOLD only. Full REM-2 extraction is 5-10 days
    (CTO D-2.3 effort estimate). Neither run_paper_trading_vt.py nor
    run_paper_trading_carry_fred.py migrates to use PaperRunnerBase yet.

BC-8-LIFT-COND-1 (kill switch hook) is the ONLY condition extracted in Phase-A.
The remaining 6 conditions are documented as TODO below.

BC-8-LIFT-COND extraction status:
    COND-1: kill_switch hook — EXTRACTED (Phase-A; this dispatch)
    COND-2: drawdown_contract — TODO: follow-up REM-2 full extraction dispatch
    COND-3: account_key parity gate — TODO: follow-up dispatch
    COND-4: heartbeat watchdog registration — TODO: follow-up dispatch
    COND-5: fcntl dispatch lock — TODO: follow-up dispatch
    COND-6: JPY-correlated cap wiring — TODO: follow-up dispatch
    COND-7: swap accrual call — TODO: follow-up dispatch

REM-7 note (CTO D-7.1):
    AggregateDrawdownContract instantiation belongs in PaperRunnerBase (post-full
    extraction). In the interim, both paper scripts instantiate it directly.
    This is documented here as the target home for COND-2 (drawdown_contract).

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

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DispatchStaggerConfigError(Exception):
    """Raised when dispatch_stagger_offsets_seconds config is too short.

    F-005 / D-4.1 FM-4: config must have at least one offset per active strategy.
    A config shorter than len(active_strategies) would cause an out-of-range index
    at dispatch time, silently applying offset 0 to some strategies and recreating
    the storm pattern the stagger is meant to prevent.
    """

# Active BC-8-LIFT-COND guards in Phase-A (COND-1 only)
_PHASE_A_ACTIVE_GUARDS = ["BC-8-LIFT-COND-1"]


class PaperRunnerBase:
    """Abstract base class for all paper-trading runners.

    Per-strategy subclasses (e.g., VtPaperRunner, CarryFredPaperRunner) inherit
    this class and implement the strategy-specific logic. The base class provides
    all BC-8-LIFT-COND risk-envelope logic as single-source-of-truth methods.

    Phase-A: Only COND-1 (kill switch hook) is implemented. Subclasses must call
    `_check_kill_switch()` at the start of each dispatch cycle.

    Args:
        strategy_id: Identifying string for this runner's strategy. Used in
            audit logs and kill switch namespacing.
        kill_switch: KillSwitch instance for this strategy. Required.

    Instantiation observability (REM-2):
        __init__ logs which BC-8-LIFT-COND guards are active at startup.
        Post-full-extraction, this will list all 7 conditions.
    """

    def __init__(
        self,
        strategy_id: str,
        kill_switch,  # KillSwitch — avoid circular import; type-checked at runtime
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

        # REM-2 observability boundary: log active guards at startup
        logger.info(
            "paper_runner_startup strategy_id=%s active_bc8_lift_cond_guards=%s "
            "phase=A note='COND-2..7 pending full REM-2 extraction'",
            strategy_id,
            _PHASE_A_ACTIVE_GUARDS,
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
        )
        return not triggered

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
    # BC-8-LIFT-COND-2..7: TODO — pending full REM-2 extraction dispatch
    # ---------------------------------------------------------------------------

    # TODO (follow-up dispatch: REM-2 full extraction, 5-10 days, CTO D-2.3):
    #   COND-2: def _check_drawdown_contract(self, dd_contract, equity) -> str | None
    #       Extract halt-new/reduce-sizing/full-halt logic from run_cycle() in both scripts.
    #       Must also instantiate AggregateDrawdownContract (REM-7 / CTO D-7.1).
    #
    #   COND-3: def _check_account_key_parity(self, client, backend) -> bool
    #       Extract account key reconciliation from paper scripts.
    #
    #   COND-4: def _register_heartbeat_watchdog(self, watchdog) -> None
    #       Extract HeartbeatWatchdog registration from paper scripts.
    #
    #   COND-5: def _acquire_dispatch_lock(self) -> contextmanager
    #       Extract fcntl dispatch lock from paper scripts.
    #
    #   COND-6: def _check_jpy_correlated_cap(self, client, backend) -> bool
    #       Extract JPY-correlated cap from paper scripts (uses exposure_aggregator).
    #
    #   COND-7: def _call_swap_accrual(self, ...) -> None
    #       Extract swap accrual call from paper scripts.
    #
    # Test coverage required BEFORE extraction merges (CTO D-2.4, PM hard-constraint):
    #   tests/integration/test_paper_runner_bc8_conds.py (REM-2-T1)
    #   tests/integration/test_paper_runner_bc8_cond_units.py (REM-2-T2, optional this wave)

    @property
    def kill_switch(self):
        """Expose kill switch for testing and BC-8-LIFT-COND verification."""
        return self._kill_switch

    @property
    def active_guards(self) -> list[str]:
        """List of active BC-8-LIFT-COND guard IDs (for observability)."""
        return list(_PHASE_A_ACTIVE_GUARDS)
