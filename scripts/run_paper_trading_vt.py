#!/usr/bin/env python3
"""Paper trading — vol-targeted long carry on USDJPY (single pair).

Validated 2026-04-20: Sharpe 0.76 vs B&H 0.58, MaxDD 13.5%.

REM-2 full extraction (2026-05-13):
    Subclasses PaperRunnerBase. All BC-8-LIFT-COND-1..7 guards delegate to
    PaperRunnerBase methods. AggregateDrawdownContract instantiated ONCE in
    main() and passed to PaperRunnerBase (cardinality-1 invariant, LTCM defense).

Each cycle:
  1. Fetch last 300 daily bars from Saxo (need 252 for vol window + buffer)
  2. Compute realized vol (252-day rolling std × √252)
  3. signal = clip(target_vol / realized_vol, 0, leverage_cap) / leverage_cap
  4. target_units = signal × leverage_cap × (equity / current_price)
  5. Open / rebalance / close vs current position with 20% threshold
  6. Log everything; ntfy on trade + kill-switch events

Usage:
    export SAXO_TOKEN=...
    python scripts/run_paper_trading_vt.py --auto --loop --interval 1800 \\
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
from forex_system.paper.base_runner import PaperRunnerBase
from forex_system.paper.cost_reconciliation import ModeledEquityLedger, ledger_from_config
from forex_system.risk.drawdown_contract import (
    AggregateDrawdownContract,
    DrawdownContract,
    DrawdownLevel,
)
from forex_system.risk.account_key_parity import (
    reset_account_key_lock,
)
from forex_system.paper.script_compat_shims import (
    check_dispatch_allowed,  # noqa: F401 — patch surface; re-exported from exposure_aggregator
)
from forex_system.risk.heartbeat_watchdog import HeartbeatWatchdog
from forex_system.risk.kill_switch import KillSwitch, TriggerReason
from forex_system.saxo.client import SaxoClient
from forex_system.saxo.execution import SaxoExecutionBackend
from forex_system.saxo.history import bars_to_dataframe
from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.costs.model import RealisticCostModel
from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "config/vol_target_carry.yaml"
LOCAL_TZ = ZoneInfo("America/Los_Angeles")
QUIET_HOURS = (20, 8)

WS01_TRACE_PATH = "data/ws01_trace.log"
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
    loop_name: str = "vt loop",
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


# BC-8 option-B: cross-process advisory file-lock (shared with carry_fred loop).
# Lock acquired BEFORE get_positions; held through execute_signal + reconciliation.
# See docs/specs/drawdown_ladder_amendment_2026-05-06.md and CRO Wave-9 ruling.
DISPATCH_LOCK_PATH = "data/dispatch_lock.flock"

# HIGH-1: Cost model instance — deduct spread/slippage/commission/swap on each
# trade so paper equity curve is backtest-equivalent.  Mirrors usage in engine.py.
_COST_MODEL = RealisticCostModel()

# HIGH-1 swap accrual: track the wall-clock timestamp of the most recent
# equity-write so per-cycle days-elapsed can be derived.  None until first cycle.
# Persisted to disk (data/paper_last_cycle_ts_vol_target_carry.json) so the
# timestamp survives process restarts.  Loaded at startup via
# PaperRunnerBase.load_last_cycle_ts(); written after each cycle via
# PaperRunnerBase.persist_last_cycle_ts().
# Clock source: UTC wall clock (datetime.now(timezone.utc)) in _accrue_swap.
_LAST_CYCLE_TS_STRATEGY_ID = "vol_target_carry"
_last_cycle_ts: datetime | None = None

# ---------------------------------------------------------------------------
# CRO binding constraints — sourced from CONSENSUS_2026-04-28 + CRO Wave-4
# artifact .fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/
# cro-bet1-sizing-revision.yaml. These are NOT silent defaults; they are
# named constants that must match the typed consensus artifact.
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
CRO_DD_HALT_NEW_THRESHOLD: float = 0.10  # DD ≥ 10% (broker TotalValue) → halt new dispatch
CRO_DD_REDUCE_SIZING_THRESHOLD: float = 0.15  # DD ≥ 15% (broker TotalValue) → 0.5x sizing
CRO_DD_FULL_HALT_THRESHOLD: float = 0.20  # DD ≥ 20% (broker TotalValue) → full halt

# Sentinel return values for drawdown skip paths (used in tests to distinguish skip reasons)
SKIP_DD_FULL_HALT: str = "SKIP_DD_FULL_HALT"
SKIP_DD_HALT_NEW: str = "SKIP_DD_HALT_NEW"
# BC-8 sentinel: emitted when the per-cycle dispatch lock is busy (another loop holds it).
SKIP_DISPATCH_LOCK_BUSY: str = "SKIP_DISPATCH_LOCK_BUSY"
# F-101 sentinel: emitted when an unexpected OS-level error prevents dispatch-lock acquisition.
SKIP_DISPATCH_LOCK_FS_ERROR: str = "SKIP_DISPATCH_LOCK_FS_ERROR"


def _attach_ws01_file_handler(path: str = WS01_TRACE_PATH) -> None:
    """Persist ws01 decision-trace lines to disk independently of stderr.

    WS-01 (CTO consensus 2026-04-26) requires a durable signal-to-execution
    audit trail. stderr alone is not durable: nohup/systemd/supervisor must
    redirect it, and operators forget. A dedicated file handler on the module
    logger guarantees the trace exists on disk regardless of how the process
    is launched. Idempotent across re-imports.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler) and getattr(h, "_ws01_marker", False):
            return
    handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    handler._ws01_marker = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    # Make sure INFO records actually flow through this logger regardless of
    # how the host configured logging (basicConfig in __main__ vs pytest's
    # default WARNING root). Without this, the module logger's effective
    # level can suppress ws01 emits silently.
    if logger.level == logging.NOTSET or logger.level > logging.INFO:
        logger.setLevel(logging.INFO)


def _finite_or_none(v) -> float | None:
    """Return v as float if finite, else None.

    json.dumps raises ValueError on inf/-inf/nan by default; the WS-01 trace
    must never be the source of an uncaught exception at the decision boundary.
    """
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _emit_ws01(
    cycle_id: int | None,
    pair: str,
    action: str,
    *,
    signal: float | None = None,
    vol: float | None = None,
    equity: float | None = None,
    price: float | None = None,
    target_units: float | None = None,
    current_units: float | None = None,
    strategy_params: dict | None = None,
) -> None:
    """Emit one structured WS-01 decision-trace line.

    Called at every cycle exit (early returns + main path) so ops can
    reconstruct what the system saw and decided — including kill-halts,
    equity-fetch failures, and data-unavailable cycles.

    CTO 2026-04-27 conditional findings on Q1+Q2:
      C1 (strategy_params): the trace must capture the parameters in force
         when the decision was made. Without this, an audit reading
         historical ws01 lines cannot tell whether a config drift between
         cycles changed the decision -- the strategy module's params live
         in memory only. Pass strategy.params at the main path; early-exit
         paths pass None (the strategy hasn't computed yet).
      C2 (decision_ts): the asctime in the formatter is the LOG-WRITE time,
         not the DECISION time. On a slow cycle (network latency), these
         differ. Capture the decision instant explicitly so latency
         analysis is possible from the trace alone.
    """
    logger.info(
        "ws01 %s",
        json.dumps(
            {
                "decision_ts": datetime.now(timezone.utc).isoformat(),
                "cycle_id": cycle_id,
                "pair": pair,
                "signal": _finite_or_none(signal),
                "vol": _finite_or_none(vol),
                "equity": _finite_or_none(equity),
                "price": _finite_or_none(price),
                "target_units": _finite_or_none(target_units),
                "current_units": _finite_or_none(current_units),
                "action": action,
                "strategy_params": strategy_params,
            }
        ),
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
            headers={"Title": safe_title, "Priority": priority, "Tags": "chart_with_upwards_trend"},
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
    """Write heartbeat.json atomically (write-then-rename).

    A watcher process (check_heartbeat.py) reads this file to detect hangs.
    Atomic rename ensures the reader never sees a half-written file.
    """
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
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".heartbeat_tmp_")
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


HEARTBEAT_PATH = "data/heartbeat.json"


def fetch_recent_bars(
    client: SaxoClient, pair: str, count: int = 300, horizon: str = "daily"
) -> pd.DataFrame:
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


def log_monitor_signals(
    client: SaxoClient,
    monitor_pairs: list[str],
    strategy_params: dict,
    pred_log: PredictionLog,
    horizon: str,
) -> None:
    """Fetch bars and log signals for monitor-only (no trade) pairs."""
    for mp in monitor_pairs:
        try:
            ohlcv = fetch_recent_bars(client, mp, count=300, horizon=horizon)
            if ohlcv.empty or len(ohlcv) < strategy_params.get("vol_window", 252) + 10:
                print(f"  [monitor {mp}] insufficient data")
                continue
            ms = VolTargetCarryStrategy({**strategy_params, "pair": mp})
            sigs = ms.generate_signals(ohlcv)
            sig = float(sigs.iloc[-1])
            rv = (
                ohlcv["close"]
                .pct_change()
                .rolling(strategy_params.get("vol_window", 252))
                .std()
                .iloc[-1]
            ) * (252**0.5)
            mid_price = float(ohlcv["close"].iloc[-1])
            pred_log.log(
                sigs.iloc[-1:],
                "vol_target_carry_monitor",
                mp,
                parameters=strategy_params,
                source="paper",
            )
            print(f"  [monitor {mp}] signal={sig:.3f}  vol={rv:.1%}  price={mid_price:.4f}")
        except Exception as e:
            print(f"  [monitor {mp}] FAILED: {e}")


def halt_paper_loop(reason: str) -> None:
    """Mark the paper loop for halt by setting a module-level flag.

    Called by the HeartbeatWatchdog on_timeout callback (CRO binding
    constraint #2). Does NOT auto-unwind positions — per CRO 2026-04-30
    design, existing positions are flagged for human review, not force-closed.
    The main loop checks ``_HALT_REQUESTED`` at the top of each cycle and
    exits gracefully.
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


# Module-level halt flag — set by halt_paper_loop; read at loop entry.
_HALT_REQUESTED: bool = False
_HALT_REASON: str = ""


def run_cycle(
    client: SaxoClient,
    backend: SaxoExecutionBackend,
    sizer: VolTargetSizer,
    strategy: VolTargetCarryStrategy,
    pair: str,
    pred_log: PredictionLog,
    trade_log: TradeLog,
    kill_switch: KillSwitch,
    rebal_threshold: float,
    runner: PaperRunnerBase | None = None,
    dd_contract: DrawdownContract | None = None,
    auto_mode: bool = False,
    ntfy_topic: str | None = None,
    horizon: str = "daily",
    monitor_pairs: list[str] | None = None,
    cycle_id: int | None = None,
    cost_ledger: ModeledEquityLedger | None = None,
) -> dict:
    """Execute one vol-target carry cycle.

    REM-2: All BC-8-LIFT-COND-1..7 guards delegate to runner (PaperRunnerBase).

    runner is optional for backward-compat with pre-REM-2 test call sites.
    When None, a minimal PaperRunnerBase is constructed from kill_switch.
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
            strategy_id="vol_target_carry",
            dispatch_lock_path=DISPATCH_LOCK_PATH,
        )
    # --- CRO binding constraint #2: watchdog halt check ---
    # The HeartbeatWatchdog callback sets _HALT_REQUESTED if the loop went
    # idle for > CRO_WATCHDOG_TIMEOUT_SECONDS.  Check at cycle entry so no
    # new dispatch is initiated after a watchdog fire.
    if _HALT_REQUESTED:
        logger.critical(
            "run_cycle blocked — watchdog halt active",
            extra={"event": "CYCLE_BLOCKED_WATCHDOG_HALT", "halt_reason": _HALT_REASON},
        )
        _emit_ws01(cycle_id, pair, "HALT_WATCHDOG_BLOCKED")
        return {"_action": "HALT_WATCHDOG"}

    # COND-1: kill switch check via PaperRunnerBase (cardinality-1)
    if not runner._check_kill_switch():
        print(f"\n  KILL SWITCH ACTIVE: {kill_switch.status_line}")
        notify(ntfy_topic, "KILL SWITCH ACTIVE", kill_switch.status_line, "urgent")
        _emit_ws01(cycle_id, pair, "KILL_HALTED_PRECYCLE")
        return {"_action": "KILL_HALTED"}

    equity = fetch_account_equity(client, backend.account_key)
    if equity is None:
        if kill_switch.record_equity_fetch_failure():
            print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
            # Emit WS01 BEFORE the execution branch so the audit trace shows
            # what the system saw at the decision point, not after it acted.
            _emit_ws01(cycle_id, pair, "KILL_HALTED_EQUITY_FETCH")
            backend.flatten_all()
            notify(
                ntfy_topic, "KILL SWITCH - equity fetch failures", kill_switch.status_line, "urgent"
            )
        else:
            remaining = (
                kill_switch.max_consecutive_fetch_failures - kill_switch.consecutive_fetch_failures
            )
            print(f"\n  Skipping cycle — equity unavailable ({remaining} skips before halt)")
            _emit_ws01(cycle_id, pair, "SKIP_EQUITY_FETCH_FAIL")
        return {"_action": "SKIP"}
    kill_switch.record_equity_fetch_success()

    if kill_switch.check_and_trigger(equity):
        print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
        # Emit WS01 BEFORE flatten_all so the audit captures the decision
        # state before the execution side-effect.
        _emit_ws01(cycle_id, pair, "KILL_HALTED_DRAWDOWN", equity=equity)
        backend.flatten_all()
        return {"_action": "KILL_HALTED"}

    # Gap-3 / CRO VETO #4: compute the mock flag ONCE here using the single
    # canonical predicate so every downstream consumer (dd_contract.assess,
    # _check_aggregate_drawdown, and cost_ledger.update) shares the same detection
    # logic without duplication.
    # MC-6: PRIMARY signal is backend.is_mock (backend identity, not float equality).
    # SaxoExecutionBackend.is_mock always returns False; test stubs override to True.
    # Secondary: 100_000.0 sentinel retained in is_mock_cycle for defence-in-depth.
    _cycle_is_mock = ModeledEquityLedger.is_mock_cycle(equity, is_mock_backend=backend.is_mock)

    # --- CRO binding constraint DD-1/DD-2/DD-3: drawdown contract ladder ---
    # Thresholds sourced from CRO CONSENSUS_2026-04-28 + cro-bet1-sizing-revision.yaml.
    # DISTINCT from KillSwitch 2% daily-loss: this enforces peak-to-trough DD.
    # dd_contract is instantiated ONCE in main() and passed per cycle (not
    # re-created here) so peak tracking is maintained across cycles.
    if dd_contract is not None:
        _dd = dd_contract.assess(equity, is_mock=_cycle_is_mock)
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
            _emit_ws01(cycle_id, pair, f"SKIP_DD_FULL_HALT_{_dd.drawdown_pct:.4f}", equity=equity)
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
            _emit_ws01(cycle_id, pair, f"SKIP_DD_HALT_NEW_{_dd.drawdown_pct:.4f}", equity=equity)
            return {"_action": SKIP_DD_HALT_NEW}
        # DrawdownLevel.REDUCE_SIZING: no early return; sizing_multiplier honored downstream
        # at the target_units calculation. _dd_sizing_multiplier captured here defaults to
        # 1.0 when no dd_contract; downstream multiplication is unconditional.
        _dd_sizing_multiplier = _dd.sizing_multiplier
    else:
        _dd_sizing_multiplier = 1.0

    # COND-2: AggregateDrawdownContract per-bar update via PaperRunnerBase
    # Called with the same equity value fetched above so both contracts share
    # a single broker-receive-time snapshot (clock-and-ordering discipline).
    # F1 / MC-6: pass _cycle_is_mock so the aggregate peak cannot be poisoned
    # by the 100_000.0 mock sentinel — mirrors dd_contract.assess(is_mock=).
    _snapshot_ts = datetime.now(timezone.utc)
    _agg_assess = runner._check_aggregate_drawdown(
        equity,
        ["vol_target_carry"],
        snapshot_timestamp=_snapshot_ts,
        is_mock=_cycle_is_mock,
    )
    if _agg_assess is not None:
        if _agg_assess.force_flat:
            logger.critical(
                "aggregate_drawdown_lockout_vt",
                extra={
                    "event": "AGGREGATE_DD_LOCKOUT",
                    "aggregate_drawdown_pct": _agg_assess.aggregate_drawdown_pct,
                    "equity": equity,
                    "cycle_id": cycle_id,
                    "pair": pair,
                },
            )
            _emit_ws01(cycle_id, pair, "SKIP_AGGREGATE_DD_LOCKOUT", equity=equity)
            halt_paper_loop(reason=f"aggregate_dd_lockout_{_agg_assess.aggregate_drawdown_pct:.4f}")
            return {"_action": "SKIP_AGGREGATE_DD_LOCKOUT"}
        elif not _agg_assess.allows_new_dispatch:
            logger.critical(
                "aggregate_drawdown_halt_vt",
                extra={
                    "event": "AGGREGATE_DD_HALT",
                    "aggregate_drawdown_pct": _agg_assess.aggregate_drawdown_pct,
                    "equity": equity,
                    "cycle_id": cycle_id,
                    "pair": pair,
                },
            )
            _emit_ws01(cycle_id, pair, "SKIP_AGGREGATE_DD_HALT", equity=equity)
            return {"_action": "SKIP_AGGREGATE_DD_HALT"}
        # Apply aggregate sizing multiplier (HALVE level) multiplicatively with per-strategy
        _dd_sizing_multiplier = _dd_sizing_multiplier * _agg_assess.sizing_multiplier

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
                _emit_ws01(cycle_id, pair, SKIP_DISPATCH_LOCK_FS_ERROR)
                return {"_action": SKIP_DISPATCH_LOCK_FS_ERROR}
            _emit_ws01(cycle_id, pair, SKIP_DISPATCH_LOCK_BUSY)
            return {"_action": SKIP_DISPATCH_LOCK_BUSY}

        # Lock held — all remaining work is inside this block.
        # COND-6: JPY-correlated cap check via PaperRunnerBase BEFORE dispatch.
        # When runner was auto-constructed (shim), use module-level check_dispatch_allowed
        # so tests that patch vt_mod.check_dispatch_allowed can still control this gate.
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
            _emit_ws01(cycle_id, pair, "SKIP_AGGREGATION_GATE_BLOCKED", equity=equity)
            return {"_action": "SKIP_AGGREGATION_GATE"}

        print("\n" + "=" * 60)
        print(f"  Vol-Target Cycle — {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Account equity: {equity:,.2f}")
        print("=" * 60)

        ohlcv = fetch_recent_bars(client, pair, count=300, horizon=horizon)
        if ohlcv.empty:
            print(f"  No data for {pair}")
            _emit_ws01(cycle_id, pair, "SKIP_NO_DATA", equity=equity)
            return {"_action": "SKIP"}
        if len(ohlcv) < strategy.params.get("vol_window", 252) + 10:
            print(f"  Not enough bars: {len(ohlcv)} (need ≥ vol_window + 10)")
            _emit_ws01(
                cycle_id,
                pair,
                "SKIP_INSUFFICIENT_BARS",
                equity=equity,
                price=float(ohlcv["close"].iloc[-1]) if len(ohlcv) else None,
            )
            return {"_action": "SKIP"}

        signals = strategy.generate_signals(ohlcv)
        sig = float(signals.iloc[-1])
        pred_log.log(
            signals.iloc[-1:], "vol_target_carry", pair, parameters=strategy.params, source="paper"
        )

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

        # Use the same bars-per-year factor the strategy uses; otherwise the WS01
        # trace would show a vol computed with hardcoded sqrt(252) while the
        # signal was computed on the actual bar frequency (4h, 1h). For daily
        # bars these are identical; for non-daily timeframes they diverge.
        bars_per_year = VolTargetCarryStrategy._bars_per_year(ohlcv)
        realized_vol = (
            ohlcv["close"]
            .pct_change()
            .rolling(strategy.params.get("vol_window", 252))
            .std()
            .iloc[-1]
        ) * (bars_per_year**0.5)
        _raw_target_units = sizer.calculate_size(sig, equity, mid, 0.0, pair)
        # CRO Wave-4 + Phase-1 binding: when DrawdownLevel.REDUCE_SIZING is active,
        # multiply target_units by 0.5 per the dd contract. dd_sizing_multiplier
        # is 1.0 in NORMAL state and when no dd_contract is wired (test paths).
        target_units = _raw_target_units * _dd_sizing_multiplier
        if _dd_sizing_multiplier != 1.0:
            logger.info(
                "dd_reduce_sizing_applied",
                extra={
                    "event": "DD_REDUCE_SIZING_APPLIED",
                    "raw_target_units": float(_raw_target_units),
                    "dd_sizing_multiplier": _dd_sizing_multiplier,
                    "adjusted_target_units": float(target_units),
                    "cycle_id": cycle_id,
                    "pair": pair,
                },
            )
        cur_pos = current_positions.get(pair)
        cur_units = cur_pos.size if cur_pos else 0.0
        cur_dir = cur_pos.direction if cur_pos else None

        print(f"  Signal:        {sig:>.3f}  (size fraction of leverage_cap)")
        print(f"  Realized vol:  {realized_vol:>.1%} annualized")
        print(f"  Mid price:     {mid:.4f}  (bid {bid:.4f} / ask {ask:.4f})")
        print(f"  Target units:  {target_units:>10,.0f}")
        print(
            f"  Current:       {('FLAT' if not cur_pos else f'{cur_dir.name} {cur_units:.0f}'):>10}"
        )

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
            # Shouldn't happen — vt strategy is long-only. Defensive.
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

        # WS-01 main-path emit: action determined, no execution branch yet taken.
        _emit_ws01(
            cycle_id,
            pair,
            action,
            signal=sig,
            vol=float(realized_vol) if pd.notna(realized_vol) else None,
            equity=equity,
            price=mid,
            target_units=float(target_units),
            current_units=float(cur_units),
            strategy_params=dict(strategy.params),
        )

        # HIGH-1 / F-001 fix: apply _to_engine_units JPY conversion before cost compute.
        # For JPY pairs: engine_units = usd_nominal / price (engine.py:544-573).
        # For non-JPY pairs: engine_units = usd_nominal (identity).
        # WITHOUT this division the paper loop charges ~150x too much for USDJPY
        # because pip_v=0.01 is sized for engine-units (e.g. 666), not USD-nominal (100_000).
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
        _engine_units = (
            (_trade_units_nom / mid) if ("JPY" in pair.upper() and mid > 0) else _trade_units_nom
        )
        _cost_usd = _cost_pips * _pip_v * _engine_units

        # COND-7: swap accrual via PaperRunnerBase — mirrors engine.py:316-317.
        # cur_units = USD-nominal position before this cycle's action.
        # _last_cycle_ts is loaded from disk at startup (see main()) so it
        # survives process restarts; after each cycle it is persisted back.
        _swap_usd, _now_ts = runner._accrue_swap(
            pair=pair,
            held_units_nom=cur_units,
            mid=mid,
            last_cycle_ts=_last_cycle_ts,
            cost_model=_COST_MODEL,
        )
        _last_cycle_ts = _now_ts
        # Persist _now_ts so the next process restart can load it and accrue swap
        # correctly on the first cycle.  Non-fatal if write fails (logged in base_runner).
        PaperRunnerBase.persist_last_cycle_ts(_LAST_CYCLE_TS_STRATEGY_ID, _now_ts)

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
        # BC-COST-RECON Option B: update cumulative modeled-equity ledger.
        # Writes modeled_equity (E_m) and residual instead of the broken
        # non-cumulative paper_equity_bt_equiv (equity - cost + swap).
        # CRO VETO #1: equity (broker TotalValue) is NOT fed into kill/DD here.
        _modeled_equity_val: float | None = None
        _residual_val: float | None = None
        if cost_ledger is not None:
            # Seed on first call (idempotent if already seeded or loaded from disk).
            cost_ledger.seed(equity, pair, mid)
            _recon = cost_ledger.update(
                pair=pair,
                mid_now=mid,
                held_units_nom=cur_units,  # held BEFORE this cycle's action
                cost_usd=_cost_usd,
                swap_usd=_swap_usd,
                broker_equity=equity,
                # Gap-3 / CRO VETO #4: reuse the single canonical mock predicate
                # computed above (ModeledEquityLedger.is_mock_cycle) so that mock
                # sentinel rows are excluded from both dd_contract peak AND residual.
                is_mock_backend=_cycle_is_mock,
                cycle_id=cycle_id,
            )
            _modeled_equity_val = round(_recon.modeled_equity, 4)
            _residual_val = round(_recon.residual, 4)
            # Enforce-mode halt check (alarm-only by default; no-op when enforce=False).
            if cost_ledger.should_halt_new_dispatch() or (
                cost_ledger.enforce and _recon.double_breach
            ):
                logger.warning(
                    "cost_recon_halt_new_dispatch strategy_id=vt cycle_id=%s — "
                    "reusing SKIP_DD_HALT_NEW path (measurement failure, not capital failure)",
                    cycle_id,
                    extra={
                        "event": "COST_RECON_HALT_NEW_DISPATCH",
                        "strategy_id": "vol_target_carry",
                        "cycle_id": cycle_id,
                        "consecutive_breaches": _recon.consecutive_breaches,
                        "double_breach": _recon.double_breach,
                    },
                )
                return {"_action": SKIP_DD_HALT_NEW}
        with open(EQUITY_LOG_PATH, "a") as _ef:
            _ef.write(
                json.dumps(
                    {
                        "ts": _now_ts.isoformat(),
                        "strategy": "vt",
                        "equity": equity,
                        "cost_pips": round(_cost_pips, 4),
                        "cost_usd": round(_cost_usd, 4),
                        "swap_usd": round(_swap_usd, 4),
                        "modeled_equity": _modeled_equity_val,
                        "residual": _residual_val,
                    }
                )
                + "\n"
            )

        print(f"  Action:        {action}")

        if not needs_action:
            time.sleep(1)
            discrepancies = backend.reconcile()
            if discrepancies:
                print(f"\n  RECONCILIATION WARNINGS: {discrepancies[0]}")
                kill_switch.trigger(
                    TriggerReason.RECONCILIATION, f"{len(discrepancies)} discrepancies", equity
                )
                backend.flatten_all()
            if monitor_pairs:
                print("\n  --- monitor-only signals ---")
                log_monitor_signals(client, monitor_pairs, strategy.params, pred_log, horizon)
            return {pair: sig, "_action": "HOLD", "_signal": sig}

        if not auto_mode:
            response = input("  Execute? [y/N]: ").strip().lower()
            if response != "y":
                print("  Result:        SKIPPED by operator")
                return {pair: sig, "_action": "SKIP", "_signal": sig}

        if is_close:
            result = backend.execute_signal(pair, 0, 0)
            status = "EXECUTED" if result.success else f"FAILED: {result.error}"
            print(f"  Result:        CLOSE — {status}")
            trade_log.record(
                result,
                signal=0,
                strategy="vol_target_carry",
                source="paper",
                context={"equity": equity},
            )
            notify(ntfy_topic, f"CLOSE: {pair}", f"Closed at {mid:.4f}", "high")
        elif is_rebalance:
            # Flatten then re-open at target
            close_r = backend.execute_signal(pair, 0, 0)
            trade_log.record(
                close_r,
                signal=0,
                strategy="vol_target_carry",
                source="paper",
                context={"equity": equity, "rebalance": True},
            )
            if not close_r.success:
                print(f"  Result:        REBALANCE CLOSE FAILED: {close_r.error}")
                return {pair: sig, "_action": "SKIP", "_signal": sig}
            time.sleep(1.5)
            result = backend.execute_signal(pair, sig, target_units)
            status = "EXECUTED" if result.success else f"FAILED: {result.error}"
            print(f"  Result:        REBALANCED — {status}")
            trade_log.record(
                result,
                signal=sig,
                strategy="vol_target_carry",
                source="paper",
                context={"equity": equity, "rebalance": True},
            )
            notify(
                ntfy_topic,
                f"REBALANCE {status}: {pair}",
                f"{cur_units:.0f} → {target_units:.0f} @ {mid:.4f}",
                "high",
            )
        else:
            result = backend.execute_signal(pair, sig, target_units)
            status = "EXECUTED" if result.success else f"FAILED: {result.error}"
            print(f"  Result:        OPEN — {status}")
            trade_log.record(
                result,
                signal=sig,
                strategy="vol_target_carry",
                source="paper",
                context={"equity": equity},
            )
            notify(
                ntfy_topic,
                f"OPEN LONG {status}: {pair}",
                f"{target_units:.0f} units @ {mid:.4f}\nVol={realized_vol:.1%}, sig={sig:.2f}",
                "high",
            )

        time.sleep(2)
        discrepancies = backend.reconcile()
        if discrepancies:
            print(f"\n  RECONCILIATION WARNINGS: {discrepancies[0]}")
            kill_switch.trigger(
                TriggerReason.RECONCILIATION, f"{len(discrepancies)} discrepancies", equity
            )
            backend.flatten_all()
        else:
            print("\n  Reconciliation: OK")

        if monitor_pairs:
            print("\n  --- monitor-only signals ---")
            log_monitor_signals(client, monitor_pairs, strategy.params, pred_log, horizon)

        # Derive heartbeat action label from which branch we took
        if is_close:
            hb_action = "EXIT"
        elif is_rebalance:
            hb_action = "REBALANCE"
        else:
            hb_action = "ENTER"
        return {pair: sig, "_action": hb_action, "_signal": sig}


def main():
    parser = argparse.ArgumentParser(description="Paper trading — vol-target carry")
    parser.add_argument("--token", default=os.environ.get("SAXO_TOKEN"))
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=1800)
    parser.add_argument("--timeframe", default="daily", choices=["daily", "4h", "1h"])
    parser.add_argument("--ntfy", metavar="TOPIC")
    parser.add_argument(
        "--monitor-pairs",
        nargs="+",
        default=[],
        help="Pairs to log signals for without trading (e.g. GBPUSD AUDJPY)",
    )
    # Fix 5: explicit reset path — operator must provide both flags; no trading loop starts.
    parser.add_argument(
        "--reset-account-key-lock",
        metavar="NEW_KEY",
        help="Reset the account-key lock to NEW_KEY (requires --confirm-account-reset).",
    )
    parser.add_argument(
        "--confirm-account-reset",
        action="store_true",
        help="Second confirmation required with --reset-account-key-lock.",
    )
    args = parser.parse_args()

    # Fix 5: handle reset before anything else — no trading loop when resetting.
    if args.reset_account_key_lock:
        if not args.confirm_account_reset:
            print(
                "ERROR: --reset-account-key-lock requires --confirm-account-reset "
                "(two flags required to prevent accidental lock replacement)."
            )
            sys.exit(1)
        reset_account_key_lock(args.reset_account_key_lock)
        # reset_account_key_lock calls sys.exit(0) on success; unreachable here.

    if not args.token:
        print("Error: --token or SAXO_TOKEN required")
        sys.exit(1)

    # WS-01: attach file handler before any cycle runs so the audit trail
    # exists on disk independent of stderr redirection.
    _attach_ws01_file_handler()

    # SWAP-FIX: load persisted last-cycle timestamp so swap accrual is non-zero
    # on the first cycle of a restarted process (SEV-2 fix).
    # Clock source: UTC wall clock stored by prior run; guarded against future ts
    # in PaperRunnerBase.load_last_cycle_ts().
    global _last_cycle_ts
    _last_cycle_ts = PaperRunnerBase.load_last_cycle_ts(_LAST_CYCLE_TS_STRATEGY_ID)

    config = load_config(args.config)
    pair = config.pair_symbols[0]  # single-pair vol-target deployment
    strat_cfg = next(s for s in config.strategies if s.name == "vol_target_carry")
    strat_params = strat_cfg.params
    rebal_threshold = strat_params.get("rebalance_threshold", 0.20)
    leverage_cap = strat_params.get("leverage_cap", 2.0)

    client = SaxoClient(args.token, live=False)
    backend = SaxoExecutionBackend(client)
    sizer = VolTargetSizer(
        leverage_cap=leverage_cap,
        min_order_size=config.backtest.position_sizing.get("min_order_size", 100)
        if hasattr(config.backtest, "position_sizing")
        else 100,
    )
    strategy = VolTargetCarryStrategy({**strat_params, "pair": pair})
    pred_log = PredictionLog(output_dir="data/predictions")
    trade_log = TradeLog(output_dir="data/trades")

    initial_equity = fetch_account_equity(client, backend.account_key)
    if initial_equity is None:
        print("Error: cannot fetch initial equity. Refusing to start.")
        sys.exit(1)
    kill_switch = KillSwitch(
        initial_equity=initial_equity,
        audit_log_path="data/kill_switch_audit.log",
    )

    # --- CRO binding constraints DD-1/DD-2/DD-3 ---
    # Instantiated ONCE; peak tracking persists across all cycles of this session.
    # Thresholds explicit; no silent defaults (per hard rule).
    dd_contract = DrawdownContract(
        halt_threshold=CRO_DD_HALT_NEW_THRESHOLD,  # 0.10 — CRO DD-1
        reduce_threshold=CRO_DD_REDUCE_SIZING_THRESHOLD,  # 0.15 — CRO DD-2
        full_halt_threshold=CRO_DD_FULL_HALT_THRESHOLD,  # 0.20 — CRO DD-3
        strategy_id="vol_target_carry",  # CRO VETO #5: enables peak persistence
    )

    # --- REM-7: AggregateDrawdownContract (LTCM-class defense, cardinality-1) ---
    # Instantiated ONCE here in main(); passed to PaperRunnerBase.
    # Cardinality-1 invariant: one instance per loop run (LTCM defense per CRO R-7.1).
    aggregate_dd_contract = AggregateDrawdownContract(
        warn_threshold=0.04,  # 4% — CRO R-7.1
        halve_threshold=0.08,  # 8% — CRO R-7.1
        halt_threshold=0.12,  # 12% — CRO R-7.1
        lockout_threshold=0.15,  # 15% — CRO R-7.1
        per_strategy_halt_threshold=CRO_DD_HALT_NEW_THRESHOLD,
        per_strategy_full_halt_threshold=CRO_DD_FULL_HALT_THRESHOLD,
        n_strategies_max=CRO_MAX_ACTIVE_STRATEGIES,
        kill_switch=kill_switch,
    )

    print("=" * 60)
    print("  PAPER TRADING — Vol-Target Carry (USDJPY)")
    print(f"  Config: {args.config}")
    print(f"  Mode: {'SUPERVISED (auto)' if args.auto else 'MANUAL (approval)'}")
    print(
        f"  Pair: {pair}  |  leverage_cap: {leverage_cap}x  |  "
        f"target_vol: {strat_params.get('target_vol', 0.10):.0%}"
    )
    print(f"  Account: {backend.account_key}")
    print(f"  Equity: {initial_equity:,.2f}")
    print(
        f"  Kill switch: {kill_switch.status_line} "
        f"(max daily loss: {kill_switch.max_daily_loss_pct:.1%})"
    )
    print("=" * 60)

    positions = backend.get_positions()
    if positions:
        print("\nExisting positions:")
        for p, pos in positions.items():
            print(f"  {p}: {pos.direction.name} {pos.size:.0f} @ {pos.entry_price:.4f}")

    loop_start = time.monotonic()
    last_signal: float | None = None
    last_action: str | None = None

    # --- COND-4: HeartbeatWatchdog instantiation ---
    # Timeout sourced from CRO CONSENSUS_2026-04-28 binding constraint #2.
    # on_timeout halts new dispatches; does NOT auto-unwind (per CRO 2026-04-30).
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
            f"Paper loop idle {seconds_idle:.1f}s > {CRO_WATCHDOG_TIMEOUT_SECONDS}s limit",
            "urgent",
        )

    watchdog = HeartbeatWatchdog(
        timeout_seconds=CRO_WATCHDOG_TIMEOUT_SECONDS,  # 300.0 — CRO binding #2, explicit
        on_timeout=_on_watchdog_timeout,
    )
    watchdog.start()

    # --- REM-2: PaperRunnerBase (COND-1..7 single source of truth) ---
    # account_key + loop_name triggers COND-3 parity gate at construction.
    # aggregate_dd_contract passes COND-2 (cardinality-1: same instance as above).
    # heartbeat_watchdog passes COND-4.
    # dispatch_lock_path passes COND-5 (shared with carry_fred loop).
    runner = PaperRunnerBase(
        strategy_id="vol_target_carry",
        kill_switch=kill_switch,
        aggregate_dd_contract=aggregate_dd_contract,
        account_key=backend.account_key,
        loop_name="vt loop",
        heartbeat_watchdog=watchdog,
        dispatch_lock_path=DISPATCH_LOCK_PATH,
    )

    # --- BC-COST-RECON Option B: cumulative modeled-equity ledger ---
    # Ships in alarm-only mode (reconciliation_enforce: false in config) until
    # ≥30-50 real fills accrue and CRO calibrates the tolerance band.
    # ntfy_fn wired so breaches page the operator (same topic as other alerts).
    def _ntfy_fn_for_recon(title, msg, pri):
        if args.ntfy:
            notify(args.ntfy, title, msg, pri)

    # Gap-1 / BC-COST-RECON: pass config.raw (the full parsed YAML dict) so that
    # ledger_from_config can read config["paper"]["cost_reconciliation"] directly.
    # SystemConfig.raw is now always populated by load_config; no defensive fallback
    # needed.  The empty-dict default on SystemConfig.raw means tests that construct
    # SystemConfig without raw= still work (ledger falls back to spec defaults).
    cost_ledger = ledger_from_config(
        "vol_target_carry",
        config.raw,
        ntfy_fn=_ntfy_fn_for_recon,
    )

    if args.loop:
        print(f"\nLoop mode (every {args.interval}s). Ctrl+C to stop.")
        cycle_id = 0
        try:
            while True:
                cycle_id += 1
                runner._tick_heartbeat()  # COND-4: dead-man tick via PaperRunnerBase
                write_heartbeat(
                    HEARTBEAT_PATH,
                    cycle_id,
                    loop_start,
                    last_signal=last_signal,
                    last_action=last_action,
                )
                result = run_cycle(
                    client,
                    backend,
                    sizer,
                    strategy,
                    pair,
                    pred_log,
                    trade_log,
                    kill_switch,
                    rebal_threshold=rebal_threshold,
                    runner=runner,
                    dd_contract=dd_contract,
                    auto_mode=args.auto,
                    ntfy_topic=args.ntfy,
                    horizon=args.timeframe,
                    monitor_pairs=args.monitor_pairs,
                    cycle_id=cycle_id,
                    cost_ledger=cost_ledger,
                )
                last_signal = result.get("_signal")
                last_action = result.get("_action")
                pred_log.flush()
                trade_log.flush()
                if _HALT_REQUESTED:
                    logger.critical(
                        "paper_loop_exiting — halt requested by watchdog",
                        extra={"event": "LOOP_EXIT_WATCHDOG_HALT", "reason": _HALT_REASON},
                    )
                    print(f"\nPaper loop HALTED by watchdog: {_HALT_REASON}")
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
            write_heartbeat(
                HEARTBEAT_PATH, 1, loop_start, last_signal=last_signal, last_action=last_action
            )
            run_cycle(
                client,
                backend,
                sizer,
                strategy,
                pair,
                pred_log,
                trade_log,
                kill_switch,
                rebal_threshold=rebal_threshold,
                runner=runner,
                dd_contract=dd_contract,
                auto_mode=args.auto,
                ntfy_topic=args.ntfy,
                horizon=args.timeframe,
                cycle_id=1,
                cost_ledger=cost_ledger,
            )
        finally:
            watchdog.stop()

    pred_log.close()
    trade_log.close()
    print("\nSession complete.")
    print(trade_log.execution_quality_report())


if __name__ == "__main__":
    main()
