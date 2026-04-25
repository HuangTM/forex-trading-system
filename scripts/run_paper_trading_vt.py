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
import logging
import os
import sys
import time
from datetime import datetime
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


def notify(topic: str | None, title: str, message: str, priority: str = "default") -> None:
    if not topic:
        return
    local_hour = datetime.now(LOCAL_TZ).hour
    quiet_start, quiet_end = QUIET_HOURS
    if quiet_start <= local_hour or local_hour < quiet_end:
        logger.info("Notification suppressed (quiet hours): %s", title)
        return
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("ascii", errors="replace"),
            headers={"Title": title, "Priority": priority,
                     "Tags": "chart_with_upwards_trend"},
            timeout=10,
        )
    except Exception as e:
        logger.warning("Failed to send notification: %s", e)


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
) -> dict:
    if kill_switch.is_triggered:
        print(f"\n  KILL SWITCH ACTIVE: {kill_switch.status_line}")
        notify(ntfy_topic, "KILL SWITCH ACTIVE", kill_switch.status_line, "urgent")
        return {}

    equity = fetch_account_equity(client, backend.account_key)
    if equity is None:
        if kill_switch.record_equity_fetch_failure():
            print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
            backend.flatten_all()
            notify(ntfy_topic, "KILL SWITCH — equity fetch failures",
                   kill_switch.status_line, "urgent")
        else:
            remaining = (kill_switch.max_consecutive_fetch_failures
                         - kill_switch.consecutive_fetch_failures)
            print(f"\n  Skipping cycle — equity unavailable ({remaining} skips before halt)")
        return {}
    kill_switch.record_equity_fetch_success()

    if kill_switch.check_and_trigger(equity):
        print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
        backend.flatten_all()
        return {}

    current_positions = backend.get_positions()
    print("\n" + "=" * 60)
    print(f"  Vol-Target Cycle — {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Account equity: {equity:,.2f}")
    print("=" * 60)

    ohlcv = fetch_recent_bars(client, pair, count=300, horizon=horizon)
    if ohlcv.empty:
        print(f"  No data for {pair}")
        return {}
    if len(ohlcv) < strategy.params.get("vol_window", 252) + 10:
        print(f"  Not enough bars: {len(ohlcv)} (need ≥ vol_window + 10)")
        return {}

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

    realized_vol = (ohlcv["close"].pct_change()
                    .rolling(strategy.params.get("vol_window", 252)).std().iloc[-1]) * (252 ** 0.5)
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
        return {pair: sig}

    if not auto_mode:
        response = input("  Execute? [y/N]: ").strip().lower()
        if response != "y":
            print("  Result:        SKIPPED by operator")
            return {pair: sig}

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
            return {pair: sig}
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

    return {pair: sig}


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

    if args.loop:
        print(f"\nLoop mode (every {args.interval}s). Ctrl+C to stop.")
        try:
            while True:
                run_cycle(client, backend, sizer, strategy, pair,
                          pred_log, trade_log, kill_switch,
                          rebal_threshold=rebal_threshold,
                          auto_mode=args.auto, ntfy_topic=args.ntfy,
                          horizon=args.timeframe,
                          monitor_pairs=args.monitor_pairs)
                pred_log.flush()
                trade_log.flush()
                print(f"\nNext check in {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped by operator.")
    else:
        run_cycle(client, backend, sizer, strategy, pair,
                  pred_log, trade_log, kill_switch,
                  rebal_threshold=rebal_threshold,
                  auto_mode=args.auto, ntfy_topic=args.ntfy,
                  horizon=args.timeframe)

    pred_log.close()
    trade_log.close()
    print("\nSession complete.")
    print(trade_log.execution_quality_report())


if __name__ == "__main__":
    main()
