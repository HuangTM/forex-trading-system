#!/usr/bin/env python3
"""Paper trading — Bet #1: carry_fred / BoJ-divergence regime (USDJPY).

REM-2 full extraction (2026-05-13):
    Subclasses PaperRunnerBase. All BC-8-LIFT-COND-1..7 guards delegate to
    PaperRunnerBase methods. AggregateDrawdownContract instantiated ONCE in
    main() and passed to PaperRunnerBase (cardinality-1 invariant, LTCM defense).


CRO Wave-4 binding constraints (sourced from CONSENSUS_2026-04-28 +
.fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/
cro-bet1-sizing-revision.yaml):

  BC-1  (regime-inactive no-trade): size_multiplier = 0.0 when BoJ-divergence
        regime flag is FALSE; zero positions permitted when regime is inactive.
  BC-2  (regime-active sizing): size_multiplier = 0.25 (0.5 envelope × 0.5
        concentration haircut) when regime flag is TRUE.
  BC-3  (CF-T9 pre-launch gate): CF-T9 monitor must be deployed and emitting
        a heartbeat ≥1 per 5-min window before any trade is placed.
  BC-4  (CF-T9 cold-start gate): CF-T9 must have observed BOTH TRUE and FALSE
        regime states with ≥10 total readings before first trade.
  BC-5  (CF-T9 heartbeat failure): If CF-T9 is silent >5 min, halt new trades.
  DD-1  (drawdown halt-new): paper-equity DD ≥ 10% → halt new trial dispatch
  DD-2  (drawdown reduce): paper-equity DD ≥ 15% → reduce all sizing to 0.5x
  DD-3  (drawdown full-halt): paper-equity DD ≥ 20% → full halt pending CRO review

Each cycle:
  1. CF-T9 status check via regime_active_status() (BC-1/BC-3/BC-4/BC-5)
  2. If regime_active is False → SKIP_REGIME_INACTIVE (BC-1 hard zero; no trades)
  3. Fetch account equity; kill-switch and drawdown-contract checks
  4. Aggregation gate (JPY-correlated ≤15%, active strategies ≤4, positions ≤6)
  5. Fetch last 300 daily bars for USDJPY
  6. carry_fred strategy generates signal
  7. Apply bet1_size_multiplier(regime_active) to target_units (BC-2)
  8. Execute / rebalance / close within rebalance_threshold
  9. WS02 structured-log line on every sizing decision (regime_active, size_multiplier)

Usage:
    export SAXO_TOKEN=...
    python scripts/run_paper_trading_carry_fred.py --auto --loop --interval 1800 \\
        --ntfy tianmin_forex_signal
"""

from __future__ import annotations

import argparse
import fcntl  # noqa: F401 — module-level for test surface (monkeypatching via fcntl.flock)
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
import requests

from forex_system.analysis.prediction_log import PredictionLog
from forex_system.analysis.trade_log import TradeLog
from forex_system.core.config import load_config
from forex_system.core.types import Direction
from forex_system.costs.model import RealisticCostModel
from forex_system.paper.base_runner import PaperRunnerBase
from forex_system.risk.account_key_parity import (
    reset_account_key_lock,
)
from forex_system.risk.bet1_sizing import bet1_size_multiplier, regime_active_status
from forex_system.paper.script_compat_shims import (
    check_dispatch_allowed,  # noqa: F401 — patch surface; re-exported from exposure_aggregator
)
from forex_system.risk.drawdown_contract import (
    AggregateDrawdownContract,
    DrawdownContract,
    DrawdownLevel,
)
from forex_system.risk.heartbeat_watchdog import HeartbeatWatchdog
from forex_system.risk.kill_switch import KillSwitch, TriggerReason
from forex_system.saxo.client import SaxoClient
from forex_system.saxo.execution import SaxoExecutionBackend
from forex_system.saxo.history import bars_to_dataframe
from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.strategies.carry_fred import CarryFREDStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "config/carry_fred.yaml"
LOCAL_TZ = ZoneInfo("America/Los_Angeles")
QUIET_HOURS = (20, 8)

WS02_TRACE_PATH = "data/ws02_trace.log"
EQUITY_LOG_PATH = "data/paper_trading_session.log"


# ---------------------------------------------------------------------------
# Backward-compat shims (REM-2 strangler-fig discipline)
#
# These module-level functions preserve the pre-REM-2 test surface.  Tests
# that patched/imported these at script level continue to work; the real
# implementation now lives in PaperRunnerBase / upstream modules.
# ---------------------------------------------------------------------------

def assert_account_key_parity(
    account_key: str,
    *,
    loop_name: str = "carry_fred loop",
    lock_path: str | None = None,
) -> None:
    """Module-level backward-compat shim — delegates to script_compat_shims.

    Provides default loop_name so tests can call without it, matching the
    original script-level function signature (pre-REM-2).
    """
    from forex_system.paper.script_compat_shims import assert_account_key_parity_impl
    from forex_system.risk.account_key_parity import ACCOUNT_KEY_LOCK_PATH
    assert_account_key_parity_impl(
        account_key,
        lock_path=lock_path if lock_path is not None else ACCOUNT_KEY_LOCK_PATH,
        loop_name=loop_name,
    )


# BC-8 option-B: cross-process advisory file-lock (shared with vt loop).
# Lock acquired BEFORE get_positions; held through execute_signal + reconciliation.
# See docs/specs/drawdown_ladder_amendment_2026-05-06.md and CRO Wave-9 ruling.
DISPATCH_LOCK_PATH = "data/dispatch_lock.flock"

# HIGH-1: cost model — mirrors engine.py usage so paper equity is backtest-equiv.
_COST_MODEL = RealisticCostModel()

# HIGH-1 swap accrual: track wall-clock timestamp of most recent equity-write
# so per-cycle days-elapsed can be derived for swap accumulation.
_last_cycle_ts: datetime | None = None

# ---------------------------------------------------------------------------
# CRO binding constants — sourced from CONSENSUS_2026-04-28 + Wave-4 artifact.
# All thresholds are explicit named constants; no silent defaults.
# ---------------------------------------------------------------------------

# CRO binding constraint #1 (exposure_aggregator): JPY-correlated notional ≤15% of book
CRO_MAX_CORRELATED_PCT: float = 0.15
# CRO Phase-1 envelope: max concurrent active paper strategies
CRO_MAX_ACTIVE_STRATEGIES: int = 4
# CRO Phase-1 envelope: max concurrent open positions
CRO_MAX_CONCURRENT_POSITIONS: int = 6
# CRO binding constraint #2 (heartbeat_watchdog): ≤5 min timeout on paper-trading loop
CRO_WATCHDOG_TIMEOUT_SECONDS: float = 300.0

# CRO binding constraints DD-1/DD-2/DD-3 (drawdown contract ladder).
# Calibrated against raw broker TotalValue per
# docs/specs/drawdown_ladder_amendment_2026-05-06.md (CEO Decision 5 amendment).
# DO NOT change without CRO + CEO CONSENSUS amendment.
CRO_DD_HALT_NEW_THRESHOLD: float = 0.10    # DD ≥ 10% (broker TotalValue) → halt new dispatch
CRO_DD_REDUCE_SIZING_THRESHOLD: float = 0.15  # DD ≥ 15% (broker TotalValue) → 0.5x sizing
CRO_DD_FULL_HALT_THRESHOLD: float = 0.20   # DD ≥ 20% (broker TotalValue) → full halt

# Sentinel return values for skip paths
SKIP_REGIME_INACTIVE: str = "SKIP_REGIME_INACTIVE"
SKIP_DD_FULL_HALT: str = "SKIP_DD_FULL_HALT"
SKIP_DD_HALT_NEW: str = "SKIP_DD_HALT_NEW"
# BC-8 sentinel: emitted when the per-cycle dispatch lock is busy (another loop holds it).
SKIP_DISPATCH_LOCK_BUSY: str = "SKIP_DISPATCH_LOCK_BUSY"
# F-101 sentinel: emitted when an unexpected OS-level error prevents dispatch-lock acquisition.
SKIP_DISPATCH_LOCK_FS_ERROR: str = "SKIP_DISPATCH_LOCK_FS_ERROR"


# ---------------------------------------------------------------------------
# WS02 file handler (audit trail — mirrors WS01 in vt loop)
# ---------------------------------------------------------------------------


def _attach_ws02_file_handler(path: str = WS02_TRACE_PATH) -> None:
    """Persist ws02 decision-trace lines to disk independently of stderr."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler) and getattr(h, "_ws02_marker", False):
            return
    handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    handler._ws02_marker = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    if logger.level == logging.NOTSET or logger.level > logging.INFO:
        logger.setLevel(logging.INFO)


def _finite_or_none(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _emit_ws02(
    cycle_id: int | None,
    pair: str,
    action: str,
    *,
    signal: float | None = None,
    equity: float | None = None,
    price: float | None = None,
    target_units: float | None = None,
    current_units: float | None = None,
    regime_active: bool | None = None,
    size_multiplier: float | None = None,
    strategy_params: dict | None = None,
) -> None:
    """Emit one structured WS-02 decision-trace line.

    Includes regime_active and size_multiplier on EVERY cycle so the audit
    trail can reconstruct the BC-1/BC-2 sizing decision from the log alone
    (log-as-decision-trace principle).
    """
    logger.info(
        "ws02 %s",
        json.dumps({
            "decision_ts": datetime.now(timezone.utc).isoformat(),
            "cycle_id": cycle_id,
            "pair": pair,
            "signal": _finite_or_none(signal),
            "equity": _finite_or_none(equity),
            "price": _finite_or_none(price),
            "target_units": _finite_or_none(target_units),
            "current_units": _finite_or_none(current_units),
            "regime_active": regime_active,
            "size_multiplier": _finite_or_none(size_multiplier),
            "action": action,
            "strategy_params": strategy_params,
        }),
    )


def notify(topic: str | None, title: str, message: str, priority: str = "default") -> None:
    if not topic:
        return
    local_hour = datetime.now(LOCAL_TZ).hour
    quiet_start, quiet_end = QUIET_HOURS
    if quiet_start <= local_hour or local_hour < quiet_end:
        logger.info("Notification suppressed (quiet hours): %s", title)
        return
    safe_title = title.encode("ascii", errors="replace").decode("ascii")
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("ascii", errors="replace"),
            headers={"Title": safe_title, "Priority": priority,
                     "Tags": "chart_with_upwards_trend"},
            timeout=10,
        )
    except Exception as e:
        logger.warning("Failed to send notification: %s", e)


def write_heartbeat(
    heartbeat_path: str,
    cycle_id: int,
    loop_start: float,
    last_signal: float | None = None,
    last_action: str | None = None,
) -> None:
    """Write heartbeat.json atomically (write-then-rename)."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle_id": cycle_id,
        "pid": os.getpid(),
        "last_signal": last_signal,
        "last_action": last_action,
        "uptime_seconds": time.monotonic() - loop_start,
    }
    path = Path(heartbeat_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".heartbeat_cf_tmp_")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(payload, f)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        logger.warning("Failed to write heartbeat: %s", e)


HEARTBEAT_PATH = "data/heartbeat_carry_fred.json"


def fetch_recent_bars(client: SaxoClient, pair: str, count: int = 300,
                      horizon: str = "daily") -> pd.DataFrame:
    data = client.get_chart_data(pair, horizon=horizon, count=count)
    bars = data.get("Data", [])
    if not bars:
        return pd.DataFrame()
    df = bars_to_dataframe(bars)
    return df[["open", "high", "low", "close", "volume"]]


def fetch_account_equity(client: SaxoClient, account_key: str) -> float | None:
    try:
        balance = client.get_balance(account_key)
        equity = balance.get("TotalValue", 0.0)
        if equity > 0:
            return equity
        cash = balance.get("CashBalance", 0.0)
        if cash > 0:
            logger.warning("TotalValue unavailable, using CashBalance: %.2f", cash)
            return cash
        logger.error("Balance API returned zero equity")
        return None
    except Exception as e:
        logger.warning("Could not fetch account balance: %s", e)
        return None


def halt_paper_loop(reason: str) -> None:
    """Mark the paper loop for halt.

    Sets module-level _HALT_REQUESTED flag.  The main loop checks this flag
    at the top of each cycle and exits gracefully.  Does NOT auto-unwind
    positions — existing positions flagged for human review per CRO 2026-04-30.
    """
    global _HALT_REQUESTED, _HALT_REASON
    _HALT_REQUESTED = True
    _HALT_REASON = reason
    logger.critical(
        "paper_loop_halt_requested",
        extra={
            "event": "HALT_REQUESTED",
            "reason": reason,
        },
    )


_HALT_REQUESTED: bool = False
_HALT_REASON: str = ""


def run_cycle(
    client: SaxoClient,
    backend: SaxoExecutionBackend,
    sizer: VolTargetSizer,
    strategy: CarryFREDStrategy,
    pair: str,
    pred_log: PredictionLog,
    trade_log: TradeLog,
    kill_switch: KillSwitch,
    dd_contract: DrawdownContract,
    rebal_threshold: float,
    runner: PaperRunnerBase | None = None,
    auto_mode: bool = False,
    ntfy_topic: str | None = None,
    horizon: str = "daily",
    cycle_id: int | None = None,
) -> dict:
    """Execute one Bet #1 carry_fred cycle.

    REM-2: All BC-8-LIFT-COND-1..7 guards delegate to runner (PaperRunnerBase).

    runner is optional for backward-compat with pre-REM-2 test call sites.
    When None, a minimal PaperRunnerBase is constructed from kill_switch.

    Returns a dict with '_action' sentinel indicating what the cycle decided.
    Possible _action values: HALT_WATCHDOG, KILL_HALTED, SKIP (various reasons),
    SKIP_REGIME_INACTIVE, SKIP_DD_FULL_HALT, SKIP_DD_HALT_NEW, SKIP_AGGREGATION_GATE,
    HOLD, ENTER, EXIT, REBALANCE.
    """
    # Backward-compat: construct minimal runner when not provided.
    # Pre-REM-2 tests call run_cycle without runner=; they pass kill_switch.
    # _runner_is_shim tracks whether we auto-created the runner so the COND-6
    # check can use the module-level check_dispatch_allowed (patchable by tests).
    _runner_is_shim = runner is None
    if _runner_is_shim:
        from forex_system.paper.script_compat_shims import construct_default_runner
        runner = construct_default_runner(
            kill_switch=kill_switch,
            strategy_id="carry_fred",
            dispatch_lock_path=DISPATCH_LOCK_PATH,
        )
    # --- Watchdog halt check (must be first) ---
    if _HALT_REQUESTED:
        logger.critical(
            "run_cycle blocked — watchdog halt active",
            extra={"event": "CYCLE_BLOCKED_WATCHDOG_HALT", "halt_reason": _HALT_REASON},
        )
        _emit_ws02(cycle_id, pair, "HALT_WATCHDOG_BLOCKED")
        return {"_action": "HALT_WATCHDOG"}

    # COND-1: kill switch check via PaperRunnerBase (cardinality-1)
    if not runner._check_kill_switch():
        print(f"\n  KILL SWITCH ACTIVE: {kill_switch.status_line}")
        notify(ntfy_topic, "KILL SWITCH ACTIVE", kill_switch.status_line, "urgent")
        _emit_ws02(cycle_id, pair, "KILL_HALTED_PRECYCLE")
        return {"_action": "KILL_HALTED"}

    # --- BC-1/BC-3/BC-4/BC-5: CF-T9 regime check ---
    # MUST be the first substantive gate: if regime is inactive or CF-T9
    # health gates are not cleared, no Bet #1 trade may be dispatched.
    # bet1_size_multiplier(False) returns 0.0 (BC-1: hard zero).
    regime_active = regime_active_status()
    size_multiplier = bet1_size_multiplier(regime_active)

    logger.info(
        "ws02_sizing_decision",
        extra={
            "event": "BET1_SIZING_DECISION",
            "regime_active": regime_active,
            "size_multiplier": size_multiplier,
            "bc_ref": "BC-1/BC-2 cro-bet1-sizing-revision.yaml",
            "cycle_id": cycle_id,
        },
    )

    if not regime_active:
        # BC-1: size_multiplier = 0.0 means no trades when regime is inactive.
        # This is not an error — it is the expected steady-state for Bet #1.
        _emit_ws02(cycle_id, pair, SKIP_REGIME_INACTIVE,
                   regime_active=False, size_multiplier=0.0)
        return {"_action": SKIP_REGIME_INACTIVE}

    # Regime is active; proceed with equity fetch and risk checks.
    equity = fetch_account_equity(client, backend.account_key)
    if equity is None:
        if kill_switch.record_equity_fetch_failure():
            print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
            _emit_ws02(cycle_id, pair, "KILL_HALTED_EQUITY_FETCH",
                       regime_active=regime_active, size_multiplier=size_multiplier)
            backend.flatten_all()
            notify(ntfy_topic, "KILL SWITCH - equity fetch failures",
                   kill_switch.status_line, "urgent")
        else:
            remaining = (kill_switch.max_consecutive_fetch_failures
                         - kill_switch.consecutive_fetch_failures)
            print(f"\n  Skipping cycle — equity unavailable ({remaining} skips before halt)")
            _emit_ws02(cycle_id, pair, "SKIP_EQUITY_FETCH_FAIL",
                       regime_active=regime_active, size_multiplier=size_multiplier)
        return {"_action": "SKIP"}
    kill_switch.record_equity_fetch_success()

    if kill_switch.check_and_trigger(equity):
        print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
        _emit_ws02(cycle_id, pair, "KILL_HALTED_DRAWDOWN", equity=equity,
                   regime_active=regime_active, size_multiplier=size_multiplier)
        backend.flatten_all()
        return {"_action": "KILL_HALTED"}

    # --- CRO DD-1/DD-2/DD-3: drawdown contract ---
    _dd = dd_contract.assess(equity)
    if _dd.level == DrawdownLevel.FULL_HALT:
        logger.critical(
            "drawdown_contract_full_halt",
            extra={
                "event": "DD_FULL_HALT",
                "drawdown_pct": _dd.drawdown_pct,
                "equity": equity,
                "peak_equity": _dd.peak_equity,
                "cycle_id": cycle_id,
            },
        )
        _emit_ws02(cycle_id, pair, f"SKIP_DD_FULL_HALT_{_dd.drawdown_pct:.4f}",
                   equity=equity, regime_active=regime_active, size_multiplier=0.0)
        halt_paper_loop(reason=f"drawdown_full_halt_{_dd.drawdown_pct:.4f}")
        return {"_action": SKIP_DD_FULL_HALT}
    elif _dd.level == DrawdownLevel.HALT_NEW_DISPATCH:
        logger.warning(
            "drawdown_contract_halt_new_dispatch",
            extra={
                "event": "DD_HALT_NEW_DISPATCH",
                "drawdown_pct": _dd.drawdown_pct,
                "equity": equity,
                "peak_equity": _dd.peak_equity,
                "cycle_id": cycle_id,
            },
        )
        _emit_ws02(cycle_id, pair, f"SKIP_DD_HALT_NEW_{_dd.drawdown_pct:.4f}",
                   equity=equity, regime_active=regime_active, size_multiplier=size_multiplier)
        return {"_action": SKIP_DD_HALT_NEW}
    # REDUCE_SIZING: honor _dd.sizing_multiplier downstream by multiplying
    # target_units before execution.

    # COND-2: AggregateDrawdownContract per-bar update via PaperRunnerBase
    # Called with the same equity value fetched above so both contracts share
    # a single broker-receive-time snapshot (clock-and-ordering discipline).
    _snapshot_ts = datetime.now(timezone.utc)
    _agg_dd_extra_multiplier = 1.0
    _agg_assess = runner._check_aggregate_drawdown(
        equity,
        ["carry_fred"],
        snapshot_timestamp=_snapshot_ts,
    )
    if _agg_assess is not None:
        if _agg_assess.force_flat:
            logger.critical(
                "aggregate_drawdown_lockout_carry_fred",
                extra={
                    "event": "AGGREGATE_DD_LOCKOUT",
                    "aggregate_drawdown_pct": _agg_assess.aggregate_drawdown_pct,
                    "equity": equity,
                    "cycle_id": cycle_id,
                    "pair": pair,
                },
            )
            _emit_ws02(cycle_id, pair, "SKIP_AGGREGATE_DD_LOCKOUT", equity=equity,
                       regime_active=regime_active, size_multiplier=size_multiplier)
            halt_paper_loop(reason=f"aggregate_dd_lockout_{_agg_assess.aggregate_drawdown_pct:.4f}")
            return {"_action": "SKIP_AGGREGATE_DD_LOCKOUT"}
        elif not _agg_assess.allows_new_dispatch:
            logger.critical(
                "aggregate_drawdown_halt_carry_fred",
                extra={
                    "event": "AGGREGATE_DD_HALT",
                    "aggregate_drawdown_pct": _agg_assess.aggregate_drawdown_pct,
                    "equity": equity,
                    "cycle_id": cycle_id,
                    "pair": pair,
                },
            )
            _emit_ws02(cycle_id, pair, "SKIP_AGGREGATE_DD_HALT", equity=equity,
                       regime_active=regime_active, size_multiplier=size_multiplier)
            return {"_action": "SKIP_AGGREGATE_DD_HALT"}
        # Apply aggregate sizing multiplier (HALVE level) multiplicatively
        _agg_dd_extra_multiplier = _agg_assess.sizing_multiplier

    # COND-5: acquire advisory cross-process file-lock via PaperRunnerBase BEFORE get_positions.
    # CRO Wave-9 ruling: without this lock two concurrent loops can both pass
    # check_dispatch_allowed with stale exposure snapshots, doubling JPY exposure.
    # docs/specs/drawdown_ladder_amendment_2026-05-06.md; CRO Wave-9 option-B.
    with runner._acquire_dispatch_lock(cycle_id=cycle_id, pair=pair) as _dl_acquired:
        if _dl_acquired is not True:
            # Distinguish BUSY (lock held by another process) from FS_ERROR (OS error).
            # _DISPATCH_LOCK_FS_ERROR sentinel is yielded on OSError; False on LOCK_NB busy.
            from forex_system.paper.base_runner import _DISPATCH_LOCK_FS_ERROR
            if _dl_acquired is _DISPATCH_LOCK_FS_ERROR:
                logger.warning(
                    "dispatch_lock.fs_error",
                    extra={
                        "event": "SKIP_DISPATCH_LOCK_FS_ERROR",
                        "cycle_id": cycle_id,
                        "pair": pair,
                    },
                )
                _emit_ws02(cycle_id, pair, SKIP_DISPATCH_LOCK_FS_ERROR,
                           regime_active=regime_active, size_multiplier=size_multiplier)
                return {"_action": SKIP_DISPATCH_LOCK_FS_ERROR}
            _emit_ws02(cycle_id, pair, SKIP_DISPATCH_LOCK_BUSY,
                       regime_active=regime_active, size_multiplier=size_multiplier)
            return {"_action": SKIP_DISPATCH_LOCK_BUSY}

        # Lock held — all remaining work is inside this block.
        # COND-6: JPY-correlated cap check via PaperRunnerBase BEFORE dispatch.
        # When runner was auto-constructed (shim), use module-level check_dispatch_allowed
        # so tests that patch cf_mod.check_dispatch_allowed can still control this gate.
        current_positions = backend.get_positions()
        _open_pos_list = list(current_positions.values())
        if _runner_is_shim:
            from forex_system.risk.exposure_aggregator import (
                AggregationGateBlocked,
                compute_exposure,
            )
            _exposure = compute_exposure(_open_pos_list)
            _cond6_allowed = True
            try:
                check_dispatch_allowed(
                    _exposure,
                    max_correlated_pct=CRO_MAX_CORRELATED_PCT,
                    max_active_strategies=CRO_MAX_ACTIVE_STRATEGIES,
                    max_concurrent_positions=CRO_MAX_CONCURRENT_POSITIONS,
                )
            except AggregationGateBlocked:
                _cond6_allowed = False
        else:
            _cond6_allowed = runner._check_jpy_correlated_cap(
                _open_pos_list,
                max_correlated_pct=CRO_MAX_CORRELATED_PCT,
                max_active_strategies=CRO_MAX_ACTIVE_STRATEGIES,
                max_concurrent_positions=CRO_MAX_CONCURRENT_POSITIONS,
                cycle_id=cycle_id,
                pair=pair,
                equity=equity,
            )
        if not _cond6_allowed:
            _emit_ws02(cycle_id, pair, "SKIP_AGGREGATION_GATE_BLOCKED", equity=equity,
                       regime_active=regime_active, size_multiplier=size_multiplier)
            return {"_action": "SKIP_AGGREGATION_GATE"}

        print("\n" + "=" * 60)
        print(f"  Carry-Fred Cycle — {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Account equity:  {equity:,.2f}")
        print(f"  Regime active:   {regime_active}  |  size_multiplier: {size_multiplier}")
        print("=" * 60)

        ohlcv = fetch_recent_bars(client, pair, count=300, horizon=horizon)
        if ohlcv.empty:
            print(f"  No data for {pair}")
            _emit_ws02(cycle_id, pair, "SKIP_NO_DATA", equity=equity,
                       regime_active=regime_active, size_multiplier=size_multiplier)
            return {"_action": "SKIP"}
        min_bars = strategy.params.get("lookback", 252) + 10
        if len(ohlcv) < min_bars:
            print(f"  Not enough bars: {len(ohlcv)} (need ≥ {min_bars})")
            _emit_ws02(cycle_id, pair, "SKIP_INSUFFICIENT_BARS", equity=equity,
                       regime_active=regime_active, size_multiplier=size_multiplier)
            return {"_action": "SKIP"}

        signals = strategy.generate_signals(ohlcv)
        sig = float(signals.iloc[-1])
        pred_log.log(signals.iloc[-1:], "carry_fred", pair,
                     parameters=strategy.params, source="paper")

        try:
            pi = client.get_info_price(pair)
            quote = pi.get("Quote", {})
            bid, ask = quote.get("Bid", 0), quote.get("Ask", 0)
        except Exception:
            bid = ask = float(ohlcv["close"].iloc[-1])
        mid = (bid + ask) / 2 if (bid and ask) else float(ohlcv["close"].iloc[-1])

        # F-100 guard (CRO Decision A): halt-cycle on degenerate mid for JPY pairs
        if "JPY" in pair.upper() and (mid <= 0 or math.isnan(mid)):
            logger.warning(
                "f100_jpy_mid_guard_triggered",
                extra={
                    "event": "F100_JPY_MID_GUARD",
                    "cycle_id": cycle_id,
                    "pair": pair,
                    "mid": mid,
                    "action": "halt-cycle",
                    "cro_artifact": ".fintech-org/artifacts/2026-05-11T-wave11/cro-risk-review.yaml",
                    "ts": datetime.now(timezone.utc).isoformat(),
                },
            )
            return {"_action": "SKIP_F100_JPY_MID_GUARD"}

        # Compute raw target units from sizer then apply BC-2 size_multiplier.
        # Also honor REDUCE_SIZING if the drawdown contract requires it.
        raw_target_units = sizer.calculate_size(sig, equity, mid, 0.0, pair)
        effective_dd_multiplier = _dd.sizing_multiplier   # 1.0/0.5/0.0 per DD level
        # REM-7: also apply aggregate DD multiplier (1.0 if HALVE not fired, 0.5 if HALVE)
        target_units = int(raw_target_units * size_multiplier * effective_dd_multiplier
                           * _agg_dd_extra_multiplier)

        cur_pos = current_positions.get(pair)
        cur_units = cur_pos.size if cur_pos else 0.0
        cur_dir = cur_pos.direction if cur_pos else None

        print(f"  Signal:          {sig:>.3f}")
        print(f"  Mid price:       {mid:.4f}  (bid {bid:.4f} / ask {ask:.4f})")
        print(f"  Raw target:      {raw_target_units:>10,.0f}")
        print(f"  BC-2 multiplier: {size_multiplier}  (regime_active={regime_active})")
        print(f"  DD multiplier:   {effective_dd_multiplier}  (DD level: {_dd.level.value})")
        print(f"  Target units:    {target_units:>10,.0f}")
        print(f"  Current:         {('FLAT' if not cur_pos else f'{cur_dir.name} {cur_units:.0f}'):>10}")

        needs_action = False
        is_close = False
        is_rebalance = False
        if target_units == 0 and cur_pos:
            needs_action = True
            is_close = True
            action = "CLOSE"
        elif target_units > 0 and not cur_pos:
            needs_action = True
            action = f"OPEN LONG {target_units:.0f}"
        elif target_units > 0 and cur_pos and cur_dir == Direction.SHORT:
            needs_action = True
            action = f"REVERSE TO LONG {target_units:.0f}"
        elif target_units > 0 and cur_pos and cur_units > 0:
            delta = abs(target_units - cur_units) / cur_units
            if delta > rebal_threshold:
                needs_action = True
                is_rebalance = True
                action = f"REBALANCE {cur_units:.0f} → {target_units:.0f} ({delta:+.0%})"
            else:
                action = f"HOLD (delta {delta:.0%} < {rebal_threshold:.0%})"
        else:
            action = "HOLD FLAT"

        _emit_ws02(
            cycle_id, pair, action,
            signal=sig,
            equity=equity,
            price=mid,
            target_units=float(target_units),
            current_units=float(cur_units),
            regime_active=regime_active,
            size_multiplier=size_multiplier,
            strategy_params=dict(strategy.params),
        )

        # HIGH-1 / F-001 fix: apply _to_engine_units JPY conversion before cost compute.
        # For JPY pairs: engine_units = usd_nominal / price (engine.py:544-573).
        # For non-JPY pairs: engine_units = usd_nominal (identity).
        # WITHOUT this division the paper loop charges ~150x too much for USDJPY.
        # F-001 fix (Wave-10): docs/specs/drawdown_ladder_amendment_2026-05-06.md.
        global _last_cycle_ts
        _pip_v = 0.01 if "JPY" in pair.upper() else 0.0001
        if needs_action and is_close:
            _cost_pips = _COST_MODEL.exit_cost(pair, cur_units)
            _trade_units_nom = cur_units
        elif needs_action and is_rebalance:
            # Fix 2: cost on |delta|, mirroring engine.py:331-332.
            _rebal_delta = abs(target_units - cur_units)
            _cost_pips = _COST_MODEL.entry_cost(pair, _rebal_delta)
            _trade_units_nom = _rebal_delta
        elif needs_action:
            _cost_pips = _COST_MODEL.entry_cost(pair, target_units)
            _trade_units_nom = target_units
        else:
            _cost_pips = 0.0
            _trade_units_nom = 0.0
        # F-001: convert USD-nominal to engine-units (divides by price for JPY pairs).
        _engine_units = (_trade_units_nom / mid) if ("JPY" in pair.upper() and mid > 0) else _trade_units_nom
        _cost_usd = _cost_pips * _pip_v * _engine_units

        # COND-7: swap accrual via PaperRunnerBase — mirrors engine.py:316-317.
        _swap_usd, _now_ts = runner._accrue_swap(
            pair=pair,
            held_units_nom=cur_units,
            mid=mid,
            last_cycle_ts=_last_cycle_ts,
            cost_model=_COST_MODEL,
        )
        _last_cycle_ts = _now_ts

        logger.info(
            "cost_compute.decision",
            extra={
                "event": "COST_COMPUTED",
                "cycle_id": cycle_id,
                "pair": pair,
                "trade_units_nom": round(_trade_units_nom, 4),
                "engine_units": round(_engine_units, 4),
                "mid_price": round(mid, 4),
                "cost_pips": round(_cost_pips, 4),
                "pip_v": _pip_v,
                "cost_usd": round(_cost_usd, 4),
                "swap_usd": round(_swap_usd, 4),
                "decision_ts": _now_ts.isoformat(),
            },
        )
        with open(EQUITY_LOG_PATH, "a") as _ef:
            _ef.write(json.dumps({
                "ts": _now_ts.isoformat(),
                "strategy": "carry_fred", "equity": equity,
                "regime_active": regime_active,
                "cost_pips": round(_cost_pips, 4), "cost_usd": round(_cost_usd, 4),
                "swap_usd": round(_swap_usd, 4),
                "paper_equity_bt_equiv": round(equity - _cost_usd + _swap_usd, 4),
            }) + "\n")

        print(f"  Action:          {action}")

        if not needs_action:
            time.sleep(1)
            discrepancies = backend.reconcile()
            if discrepancies:
                print(f"\n  RECONCILIATION WARNINGS: {discrepancies[0]}")
                kill_switch.trigger(TriggerReason.RECONCILIATION,
                                    f"{len(discrepancies)} discrepancies", equity)
                backend.flatten_all()
            return {pair: sig, "_action": "HOLD", "_signal": sig}

        if not auto_mode:
            response = input("  Execute? [y/N]: ").strip().lower()
            if response != "y":
                print("  Result:          SKIPPED by operator")
                return {pair: sig, "_action": "SKIP", "_signal": sig}

        if is_close:
            result = backend.execute_signal(pair, 0, 0)
            status = "EXECUTED" if result.success else f"FAILED: {result.error}"
            print(f"  Result:          CLOSE — {status}")
            trade_log.record(result, signal=0, strategy="carry_fred",
                             source="paper", context={"equity": equity})
            notify(ntfy_topic, f"CLOSE: {pair}", f"Closed at {mid:.4f}", "high")
        elif is_rebalance:
            close_r = backend.execute_signal(pair, 0, 0)
            trade_log.record(close_r, signal=0, strategy="carry_fred",
                             source="paper", context={"equity": equity, "rebalance": True})
            if not close_r.success:
                print(f"  Result:          REBALANCE CLOSE FAILED: {close_r.error}")
                return {pair: sig, "_action": "SKIP", "_signal": sig}
            time.sleep(1.5)
            result = backend.execute_signal(pair, sig, target_units)
            status = "EXECUTED" if result.success else f"FAILED: {result.error}"
            print(f"  Result:          REBALANCED — {status}")
            trade_log.record(result, signal=sig, strategy="carry_fred",
                             source="paper", context={"equity": equity, "rebalance": True})
            notify(ntfy_topic, f"REBALANCE {status}: {pair}",
                   f"{cur_units:.0f} → {target_units:.0f} @ {mid:.4f}", "high")
        else:
            result = backend.execute_signal(pair, sig, target_units)
            status = "EXECUTED" if result.success else f"FAILED: {result.error}"
            print(f"  Result:          OPEN — {status}")
            trade_log.record(result, signal=sig, strategy="carry_fred",
                             source="paper", context={"equity": equity})
            notify(ntfy_topic, f"OPEN LONG {status}: {pair}",
                   f"{target_units:.0f} units @ {mid:.4f} (regime={regime_active}, "
                   f"mult={size_multiplier})", "high")

        time.sleep(2)
        discrepancies = backend.reconcile()
        if discrepancies:
            print(f"\n  RECONCILIATION WARNINGS: {discrepancies[0]}")
            kill_switch.trigger(TriggerReason.RECONCILIATION,
                                f"{len(discrepancies)} discrepancies", equity)
            backend.flatten_all()
        else:
            print("\n  Reconciliation: OK")

        if is_close:
            hb_action = "EXIT"
        elif is_rebalance:
            hb_action = "REBALANCE"
        else:
            hb_action = "ENTER"
        return {pair: sig, "_action": hb_action, "_signal": sig}


def main():
    parser = argparse.ArgumentParser(description="Paper trading — Bet #1 carry_fred")
    parser.add_argument("--token", default=os.environ.get("SAXO_TOKEN"))
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=1800)
    parser.add_argument("--timeframe", default="daily", choices=["daily", "4h", "1h"])
    parser.add_argument("--ntfy", metavar="TOPIC")
    parser.add_argument(
        "--reset-account-key-lock", metavar="NEW_KEY",
        help="Atomically replace the account-key lock. Must pair with --confirm-account-reset."
    )
    parser.add_argument(
        "--confirm-account-reset", action="store_true",
        help="Required second factor for --reset-account-key-lock to prevent accidental reset."
    )
    args = parser.parse_args()

    if args.reset_account_key_lock:
        if not args.confirm_account_reset:
            print("ERROR: --reset-account-key-lock requires --confirm-account-reset")
            sys.exit(1)
        reset_account_key_lock(args.reset_account_key_lock)  # exits 0 on success

    if not args.token:
        print("Error: --token or SAXO_TOKEN required")
        sys.exit(1)

    _attach_ws02_file_handler()

    config = load_config(args.config)
    pair = config.pair_symbols[0]
    strat_cfg = next(s for s in config.strategies if s.name == "carry_fred")
    strat_params = strat_cfg.params
    rebal_threshold = strat_params.get("rebalance_threshold", 0.20)
    leverage_cap = strat_params.get("leverage_cap", 1.0)

    client = SaxoClient(args.token, live=False)
    backend = SaxoExecutionBackend(client)
    sizer = VolTargetSizer(
        leverage_cap=leverage_cap,
        min_order_size=config.backtest.position_sizing.get("min_order_size", 100)
            if hasattr(config.backtest, "position_sizing") else 100,
    )
    strategy = CarryFREDStrategy({**strat_params, "pair": pair})
    pred_log = PredictionLog(output_dir="data/predictions")
    trade_log = TradeLog(output_dir="data/trades")

    initial_equity = fetch_account_equity(client, backend.account_key)
    if initial_equity is None:
        print("Error: cannot fetch initial equity. Refusing to start.")
        sys.exit(1)
    kill_switch = KillSwitch(
        initial_equity=initial_equity,
        audit_log_path="data/kill_switch_audit_cf.log",
    )

    # --- CRO DD-1/DD-2/DD-3: drawdown contract — instantiate ONCE ---
    # Peak tracking persists across all cycles of this session.
    # Thresholds explicit from CRO binding constants above; no silent defaults.
    dd_contract = DrawdownContract(
        halt_threshold=CRO_DD_HALT_NEW_THRESHOLD,        # 0.10 — CRO DD-1
        reduce_threshold=CRO_DD_REDUCE_SIZING_THRESHOLD, # 0.15 — CRO DD-2
        full_halt_threshold=CRO_DD_FULL_HALT_THRESHOLD,  # 0.20 — CRO DD-3
    )

    # --- REM-7: AggregateDrawdownContract (LTCM-class defense, cardinality-1) ---
    # Instantiated ONCE here in main(); passed to PaperRunnerBase.
    # Cardinality-1 invariant: one instance per loop run (LTCM defense per CRO R-7.1).
    aggregate_dd_contract = AggregateDrawdownContract(
        warn_threshold=0.04,      # 4% — CRO R-7.1
        halve_threshold=0.08,     # 8% — CRO R-7.1
        halt_threshold=0.12,      # 12% — CRO R-7.1
        lockout_threshold=0.15,   # 15% — CRO R-7.1
        per_strategy_halt_threshold=CRO_DD_HALT_NEW_THRESHOLD,
        per_strategy_full_halt_threshold=CRO_DD_FULL_HALT_THRESHOLD,
        n_strategies_max=CRO_MAX_ACTIVE_STRATEGIES,
        kill_switch=kill_switch,
    )

    print("=" * 60)
    print("  PAPER TRADING — Bet #1 Carry-Fred (USDJPY)")
    print(f"  Config: {args.config}")
    print(f"  Mode: {'SUPERVISED (auto)' if args.auto else 'MANUAL (approval)'}")
    print(f"  Pair: {pair}  |  leverage_cap: {leverage_cap}x")
    print(f"  Account: {backend.account_key}")
    print(f"  Equity: {initial_equity:,.2f}")
    print(f"  Kill switch: {kill_switch.status_line}")
    print(f"  DD thresholds: halt_new={CRO_DD_HALT_NEW_THRESHOLD:.0%}  "
          f"reduce={CRO_DD_REDUCE_SIZING_THRESHOLD:.0%}  "
          f"full_halt={CRO_DD_FULL_HALT_THRESHOLD:.0%}")
    print("=" * 60)

    loop_start = time.monotonic()
    last_signal: float | None = None
    last_action: str | None = None

    # --- CRO #2: HeartbeatWatchdog instantiation ---
    def _on_watchdog_timeout(seconds_idle: float) -> None:
        logger.critical(
            "heartbeat_watchdog fired",
            extra={
                "event": "WATCHDOG_TIMEOUT_FIRED",
                "seconds_idle": seconds_idle,
            },
        )
        halt_paper_loop(reason=f"watchdog_timeout_{seconds_idle:.1f}s")
        notify(
            args.ntfy,
            "WATCHDOG TIMEOUT — trades halted",
            f"Carry-Fred loop idle {seconds_idle:.1f}s > {CRO_WATCHDOG_TIMEOUT_SECONDS}s limit",
            "urgent",
        )

    watchdog = HeartbeatWatchdog(
        timeout_seconds=CRO_WATCHDOG_TIMEOUT_SECONDS,
        on_timeout=_on_watchdog_timeout,
    )
    watchdog.start()

    # --- REM-2: PaperRunnerBase (COND-1..7 single source of truth) ---
    # account_key + loop_name triggers COND-3 parity gate at construction.
    # aggregate_dd_contract passes COND-2 (cardinality-1: same instance as above).
    # heartbeat_watchdog passes COND-4.
    # dispatch_lock_path passes COND-5 (shared with vt loop).
    runner = PaperRunnerBase(
        strategy_id="carry_fred",
        kill_switch=kill_switch,
        aggregate_dd_contract=aggregate_dd_contract,
        account_key=backend.account_key,
        loop_name="carry_fred loop",
        heartbeat_watchdog=watchdog,
        dispatch_lock_path=DISPATCH_LOCK_PATH,
    )

    if args.loop:
        print(f"\nLoop mode (every {args.interval}s). Ctrl+C to stop.")
        cycle_id = 0
        try:
            while True:
                cycle_id += 1
                runner._tick_heartbeat()  # COND-4: dead-man tick via PaperRunnerBase
                write_heartbeat(HEARTBEAT_PATH, cycle_id, loop_start,
                                last_signal=last_signal, last_action=last_action)
                result = run_cycle(
                    client, backend, sizer, strategy, pair,
                    pred_log, trade_log, kill_switch, dd_contract,
                    rebal_threshold=rebal_threshold,
                    runner=runner,
                    auto_mode=args.auto, ntfy_topic=args.ntfy,
                    horizon=args.timeframe,
                    cycle_id=cycle_id,
                )
                last_signal = result.get("_signal")
                last_action = result.get("_action")
                pred_log.flush()
                trade_log.flush()
                if _HALT_REQUESTED:
                    logger.critical(
                        "paper_loop_exiting — halt requested",
                        extra={"event": "LOOP_EXIT_HALT", "reason": _HALT_REASON},
                    )
                    print(f"\nPaper loop HALTED: {_HALT_REASON}")
                    break
                print(f"\nNext check in {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped by operator.")
        finally:
            watchdog.stop()
    else:
        try:
            runner._tick_heartbeat()  # COND-4: tick even for single-shot run
            write_heartbeat(HEARTBEAT_PATH, 1, loop_start)
            run_cycle(
                client, backend, sizer, strategy, pair,
                pred_log, trade_log, kill_switch, dd_contract,
                rebal_threshold=rebal_threshold,
                runner=runner,
                auto_mode=args.auto, ntfy_topic=args.ntfy,
                horizon=args.timeframe,
                cycle_id=1,
            )
        finally:
            watchdog.stop()

    pred_log.close()
    trade_log.close()
    print("\nSession complete.")
    print(trade_log.execution_quality_report())


if __name__ == "__main__":
    main()
