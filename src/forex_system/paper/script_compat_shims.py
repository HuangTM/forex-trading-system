"""Backward-compatibility shims for paper-trading scripts.

DEPRECATION NOTICE: This module exists to preserve the test surface of legacy
script-level functions that pre-date the REM-2 PaperRunnerBase extraction.
New code should call PaperRunnerBase methods directly. These shims will be
removed once tests are migrated to the new BaseRunner interface.

Provides:
- assert_account_key_parity_impl: shared body of the COND-3 startup gate
- check_dispatch_allowed: re-export of the dispatch gate (takes ExposureSnapshot)
- fcntl: re-export of stdlib module (test patch surface)
- construct_default_runner: helper for run_cycle(runner=None) fallback path

Per CTO architecture-review 2026-05-14: this module lives under paper/ to share
namespace with PaperRunnerBase; no circular import risk (verified by AST: base_runner
defers all forex_system imports to method bodies).
"""
import fcntl  # noqa: F401 — re-exported as patch surface
from typing import Optional

# Import the underlying primitives FROM the risk module (single source of truth)
from forex_system.risk.account_key_parity import (
    assert_account_key_parity as _assert_account_key_parity_core,
)

# Re-export check_dispatch_allowed from the canonical risk module.
# Takes ExposureSnapshot (not open_positions) — matches the existing call sites in
# run_cycle's _runner_is_shim branch.  Tests patch vt_mod.check_dispatch_allowed /
# cf_mod.check_dispatch_allowed by name; re-exporting here preserves that surface.
from forex_system.risk.exposure_aggregator import (
    check_dispatch_allowed,  # noqa: F401 — re-exported as patch surface
)


def assert_account_key_parity_impl(
    account_key: str,
    lock_path: str,
    loop_name: str,
) -> None:
    """Shared implementation of the COND-3 startup gate.

    Each paper script provides a thin wrapper supplying its specific loop_name
    default. This implementation contains the body that was previously
    duplicated in both scripts.
    """
    _assert_account_key_parity_core(
        account_key, lock_path=lock_path, loop_name=loop_name
    )


def construct_default_runner(
    *,
    kill_switch,
    strategy_id: str,
    dispatch_lock_path: Optional[str] = None,
    aggregate_dd_contract=None,
):
    """Shared fallback for run_cycle(runner=None) path.

    Constructs a PaperRunnerBase with per-script identity.
    """
    from forex_system.paper.base_runner import PaperRunnerBase
    return PaperRunnerBase(
        kill_switch=kill_switch,
        strategy_id=strategy_id,
        dispatch_lock_path=dispatch_lock_path if dispatch_lock_path is not None
            else "data/dispatch_lock.flock",
        aggregate_dd_contract=aggregate_dd_contract,
    )
