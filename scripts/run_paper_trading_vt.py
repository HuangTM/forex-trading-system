#!/usr/bin/env python3
"""Paper trading — vol-targeted long carry on USDJPY (single pair).

Validated 2026-04-20: Sharpe 0.76 vs B&H 0.58, MaxDD 13.5%.

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
import json
import logging
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
from forex_system.risk.kill_switch import KillSwitch, TriggerReason
from forex_system.saxo.client import SaxoClient
from forex_system.saxo.execution import SaxoExecutionBackend
from forex_system.saxo.history import bars_to_dataframe
from forex_system.sizing.vol_target import VolTargetSizer
from forex_system.strategies.vol_target_carry import VolTargetCarryStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "config/vol_target_carry.yaml"
LOCAL_TZ = ZoneInfo("America/Los_Angeles")
QUIET_HOURS = (20, 8)

WS01_TRACE_PATH = "data/ws01_trace.log"


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
    handler = logging.FileHandler(path)
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
) -> None:
    """Emit one structured WS-01 decision-trace line.

    Called at every cycle exit (early returns + main path) so ops can
    reconstruct what the system saw and decided — including kill-halts,
    equity-fetch failures, and data-unavailable cycles.
    """
    logger.info(
        "ws01 %s",
        json.dumps({
            "cycle_id": cycle_id,
            "pair": pair,
            "signal": _finite_or_none(signal),
            "vol": _finite_or_none(vol),
            "equity": _finite_or_none(equity),
            "price": _finite_or_none(price),
            "target_units": _finite_or_none(target_units),
            "current_units": _finite_or_none(current_units),
            "action": action,
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
            rv = (ohlcv["close"].pct_change().rolling(strategy_params.get("vol_window", 252))
                  .std().iloc[-1]) * (252 ** 0.5)
            mid_price = float(ohlcv["close"].iloc[-1])
            pred_log.log(sigs.iloc[-1:], "vol_target_carry_monitor", mp,
                         parameters=strategy_params, source="paper")
            print(f"  [monitor {mp}] signal={sig:.3f}  vol={rv:.1%}  price={mid_price:.4f}")
        except Exception as e:
            print(f"  [monitor {mp}] FAILED: {e}")


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
    auto_mode: bool = False,
    ntfy_topic: str | None = None,
    horizon: str = "daily",
    monitor_pairs: list[str] | None = None,
    cycle_id: int | None = None,
) -> dict:
    if kill_switch.is_triggered:
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
            notify(ntfy_topic, "KILL SWITCH - equity fetch failures",
                   kill_switch.status_line, "urgent")
        else:
            remaining = (kill_switch.max_consecutive_fetch_failures
                         - kill_switch.consecutive_fetch_failures)
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

    current_positions = backend.get_positions()
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
        _emit_ws01(cycle_id, pair, "SKIP_INSUFFICIENT_BARS", equity=equity,
                   price=float(ohlcv["close"].iloc[-1]) if len(ohlcv) else None)
        return {"_action": "SKIP"}

    signals = strategy.generate_signals(ohlcv)
    sig = float(signals.iloc[-1])
    pred_log.log(signals.iloc[-1:], "vol_target_carry", pair,
                 parameters=strategy.params, source="paper")

    try:
        pi = client.get_info_price(pair)
        quote = pi.get("Quote", {})
        bid, ask = quote.get("Bid", 0), quote.get("Ask", 0)
    except Exception:
        bid = ask = float(ohlcv["close"].iloc[-1])
    mid = (bid + ask) / 2 if (bid and ask) else float(ohlcv["close"].iloc[-1])

    # Use the same bars-per-year factor the strategy uses; otherwise the WS01
    # trace would show a vol computed with hardcoded sqrt(252) while the
    # signal was computed on the actual bar frequency (4h, 1h). For daily
    # bars these are identical; for non-daily timeframes they diverge.
    bars_per_year = VolTargetCarryStrategy._bars_per_year(ohlcv)
    realized_vol = (ohlcv["close"].pct_change()
                    .rolling(strategy.params.get("vol_window", 252))
                    .std().iloc[-1]) * (bars_per_year ** 0.5)
    target_units = sizer.calculate_size(sig, equity, mid, 0.0, pair)
    cur_pos = current_positions.get(pair)
    cur_units = cur_pos.size if cur_pos else 0.0
    cur_dir = cur_pos.direction if cur_pos else None

    print(f"  Signal:        {sig:>.3f}  (size fraction of leverage_cap)")
    print(f"  Realized vol:  {realized_vol:>.1%} annualized")
    print(f"  Mid price:     {mid:.4f}  (bid {bid:.4f} / ask {ask:.4f})")
    print(f"  Target units:  {target_units:>10,.0f}")
    print(f"  Current:       {('FLAT' if not cur_pos else f'{cur_dir.name} {cur_units:.0f}'):>10}")

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
        cycle_id, pair, action,
        signal=sig,
        vol=float(realized_vol) if pd.notna(realized_vol) else None,
        equity=equity,
        price=mid,
        target_units=float(target_units),
        current_units=float(cur_units),
    )

    print(f"  Action:        {action}")

    if not needs_action:
        time.sleep(1)
        discrepancies = backend.reconcile()
        if discrepancies:
            print(f"\n  RECONCILIATION WARNINGS: {discrepancies[0]}")
            kill_switch.trigger(TriggerReason.RECONCILIATION,
                                f"{len(discrepancies)} discrepancies", equity)
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
        trade_log.record(result, signal=0, strategy="vol_target_carry",
                         source="paper", context={"equity": equity})
        notify(ntfy_topic, f"CLOSE: {pair}", f"Closed at {mid:.4f}", "high")
    elif is_rebalance:
        # Flatten then re-open at target
        close_r = backend.execute_signal(pair, 0, 0)
        trade_log.record(close_r, signal=0, strategy="vol_target_carry",
                         source="paper", context={"equity": equity, "rebalance": True})
        if not close_r.success:
            print(f"  Result:        REBALANCE CLOSE FAILED: {close_r.error}")
            return {pair: sig, "_action": "SKIP", "_signal": sig}
        time.sleep(1.5)
        result = backend.execute_signal(pair, sig, target_units)
        status = "EXECUTED" if result.success else f"FAILED: {result.error}"
        print(f"  Result:        REBALANCED — {status}")
        trade_log.record(result, signal=sig, strategy="vol_target_carry",
                         source="paper", context={"equity": equity, "rebalance": True})
        notify(ntfy_topic, f"REBALANCE {status}: {pair}",
               f"{cur_units:.0f} → {target_units:.0f} @ {mid:.4f}", "high")
    else:
        result = backend.execute_signal(pair, sig, target_units)
        status = "EXECUTED" if result.success else f"FAILED: {result.error}"
        print(f"  Result:        OPEN — {status}")
        trade_log.record(result, signal=sig, strategy="vol_target_carry",
                         source="paper", context={"equity": equity})
        notify(ntfy_topic, f"OPEN LONG {status}: {pair}",
               f"{target_units:.0f} units @ {mid:.4f}\nVol={realized_vol:.1%}, sig={sig:.2f}",
               "high")

    time.sleep(2)
    discrepancies = backend.reconcile()
    if discrepancies:
        print(f"\n  RECONCILIATION WARNINGS: {discrepancies[0]}")
        kill_switch.trigger(TriggerReason.RECONCILIATION,
                            f"{len(discrepancies)} discrepancies", equity)
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
    parser.add_argument("--monitor-pairs", nargs="+", default=[],
                        help="Pairs to log signals for without trading (e.g. GBPUSD AUDJPY)")
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or SAXO_TOKEN required")
        sys.exit(1)

    # WS-01: attach file handler before any cycle runs so the audit trail
    # exists on disk independent of stderr redirection.
    _attach_ws01_file_handler()

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
            if hasattr(config.backtest, "position_sizing") else 100,
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

    print("=" * 60)
    print("  PAPER TRADING — Vol-Target Carry (USDJPY)")
    print(f"  Config: {args.config}")
    print(f"  Mode: {'SUPERVISED (auto)' if args.auto else 'MANUAL (approval)'}")
    print(f"  Pair: {pair}  |  leverage_cap: {leverage_cap}x  |  "
          f"target_vol: {strat_params.get('target_vol', 0.10):.0%}")
    print(f"  Account: {backend.account_key}")
    print(f"  Equity: {initial_equity:,.2f}")
    print(f"  Kill switch: {kill_switch.status_line} "
          f"(max daily loss: {kill_switch.max_daily_loss_pct:.1%})")
    print("=" * 60)

    positions = backend.get_positions()
    if positions:
        print("\nExisting positions:")
        for p, pos in positions.items():
            print(f"  {p}: {pos.direction.name} {pos.size:.0f} @ {pos.entry_price:.4f}")

    loop_start = time.monotonic()
    last_signal: float | None = None
    last_action: str | None = None

    if args.loop:
        print(f"\nLoop mode (every {args.interval}s). Ctrl+C to stop.")
        cycle_id = 0
        try:
            while True:
                cycle_id += 1
                write_heartbeat(HEARTBEAT_PATH, cycle_id, loop_start,
                                last_signal=last_signal, last_action=last_action)
                result = run_cycle(client, backend, sizer, strategy, pair,
                                   pred_log, trade_log, kill_switch,
                                   rebal_threshold=rebal_threshold,
                                   auto_mode=args.auto, ntfy_topic=args.ntfy,
                                   horizon=args.timeframe,
                                   monitor_pairs=args.monitor_pairs,
                                   cycle_id=cycle_id)
                last_signal = result.get("_signal")
                last_action = result.get("_action")
                pred_log.flush()
                trade_log.flush()
                print(f"\nNext check in {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped by operator.")
    else:
        write_heartbeat(HEARTBEAT_PATH, 1, loop_start,
                        last_signal=last_signal, last_action=last_action)
        run_cycle(client, backend, sizer, strategy, pair,
                  pred_log, trade_log, kill_switch,
                  rebal_threshold=rebal_threshold,
                  auto_mode=args.auto, ntfy_topic=args.ntfy,
                  horizon=args.timeframe,
                  cycle_id=1)

    pred_log.close()
    trade_log.close()
    print("\nSession complete.")
    print(trade_log.execution_quality_report())


if __name__ == "__main__":
    main()
