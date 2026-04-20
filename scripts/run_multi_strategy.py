#!/usr/bin/env python3
"""Multi-strategy paper trading — blended signals from multiple strategies and timeframes.

For each pair, computes a weighted average signal across all configured
strategy/timeframe combos. Executes from the blended signal.

Usage:
    export SAXO_TOKEN=your_token
    python scripts/run_multi_strategy.py --config config/gbpusd_multi.yaml
    python scripts/run_multi_strategy.py --config config/gbpusd_multi.yaml --loop
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
import yaml

from forex_system.analysis.prediction_log import PredictionLog
from forex_system.analysis.trade_log import TradeLog
from forex_system.core.types import Direction
from forex_system.features.registry import compute_indicators
from forex_system.risk.kill_switch import KillSwitch, TriggerReason
from forex_system.saxo.client import SaxoClient
from forex_system.saxo.execution import SaxoExecutionBackend
from forex_system.saxo.history import bars_to_dataframe
from forex_system.sizing.continuous import ContinuousSizer
from forex_system.strategies.registry import STRATEGY_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("America/Los_Angeles")
QUIET_HOURS = (20, 8)
REBALANCE_THRESHOLD = 0.20


def notify(topic: str | None, title: str, message: str, priority: str = "default") -> None:
    """Send a push notification via ntfy.sh."""
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
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": priority, "Tags": "chart_with_upwards_trend"},
            timeout=10,
        )
    except Exception as e:
        logger.warning("Failed to send notification: %s", e)


def fetch_bars(client: SaxoClient, pair: str, horizon: str, count: int = 200) -> pd.DataFrame:
    """Fetch recent bars from Saxo."""
    data = client.get_chart_data(pair, horizon=horizon, count=count)
    bars = data.get("Data", [])
    if not bars:
        return pd.DataFrame()
    df = bars_to_dataframe(bars)
    return df[["open", "high", "low", "close", "volume"]]


def compute_blended_signals(
    client: SaxoClient,
    pair: str,
    strategy_configs: list[dict],
    rate_data: pd.DataFrame | None = None,
) -> tuple[float, list[dict]]:
    """Compute weighted blended signal for a pair across all strategies.

    Returns:
        (blended_signal, details) where details is a list of per-strategy info.
    """
    details = []
    total_weight = 0.0
    weighted_sum = 0.0

    for scfg in strategy_configs:
        strat_name = scfg["name"]
        timeframe = scfg["timeframe"]
        weight = scfg["weight"]
        params = scfg.get("params", {})

        # Fetch bars for this timeframe
        ohlcv = fetch_bars(client, pair, timeframe)
        if ohlcv.empty:
            details.append({
                "strategy": strat_name, "timeframe": timeframe,
                "weight": weight, "signal": 0.0, "status": "NO DATA",
            })
            continue

        # Build strategy
        strat_cls = STRATEGY_REGISTRY.get(strat_name)
        if strat_cls is None:
            details.append({
                "strategy": strat_name, "timeframe": timeframe,
                "weight": weight, "signal": 0.0, "status": f"UNKNOWN STRATEGY",
            })
            continue

        # Pass rate_data for carry strategies
        kwargs = {"params": {**params, "pair": pair}}
        if strat_name in ("carry", "carry_momentum") and rate_data is not None:
            kwargs["rate_data"] = rate_data

        strategy = strat_cls(**kwargs)

        # Compute indicators and generate signal
        try:
            indicators = strategy.required_indicators()
            enriched = compute_indicators(ohlcv, indicators + ["atr_14"])
            # Drop rows where required indicators aren't ready
            drop_cols = [c for c in enriched.columns if c in indicators or c == "atr_14"]
            enriched = enriched.dropna(subset=[c for c in drop_cols if c in enriched.columns])

            if enriched.empty:
                details.append({
                    "strategy": strat_name, "timeframe": timeframe,
                    "weight": weight, "signal": 0.0, "status": "WARMUP",
                })
                continue

            signals = strategy.generate_signals(enriched)
            current_signal = float(signals.iloc[-1])
        except Exception as e:
            logger.warning("Strategy %s/%s failed: %s", strat_name, timeframe, e)
            details.append({
                "strategy": strat_name, "timeframe": timeframe,
                "weight": weight, "signal": 0.0, "status": f"ERROR: {e}",
            })
            continue

        weighted_sum += weight * current_signal
        total_weight += weight
        details.append({
            "strategy": strat_name, "timeframe": timeframe,
            "weight": weight, "signal": current_signal, "status": "OK",
            "atr": float(enriched["atr_14"].iloc[-1]),
        })

    blended = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    blended = max(-1.0, min(1.0, blended))  # Clip
    return blended, details


def fetch_account_equity(client: SaxoClient, account_key: str) -> float | None:
    """Fetch current account equity from Saxo.

    Returns None if the balance cannot be reliably determined. Callers must
    skip the cycle rather than substitute a hardcoded fallback — a wrong
    baseline desynchronizes the kill switch and spuriously triggers it.
    """
    try:
        balance = client.get_balance(account_key)
        equity = balance.get("TotalValue", 0.0)
        if equity > 0:
            return equity
        cash = balance.get("CashBalance", 0.0)
        if cash > 0:
            return cash
        logger.error("Balance API returned zero equity (TotalValue=%.2f, CashBalance=%.2f)",
                     equity, cash)
        return None
    except Exception as e:
        logger.warning("Could not fetch balance: %s", e)
        return None


def run_signal_cycle(
    client: SaxoClient,
    backend: SaxoExecutionBackend,
    pairs: list[str],
    strategy_configs: list[dict],
    sizer: ContinuousSizer,
    pred_log: PredictionLog,
    trade_log: TradeLog,
    kill_switch: KillSwitch,
    rate_data: pd.DataFrame | None = None,
    ntfy_topic: str | None = None,
) -> None:
    """Run one multi-strategy signal cycle."""
    if kill_switch.is_triggered:
        print(f"\n  KILL SWITCH ACTIVE: {kill_switch.status_line}")
        notify(ntfy_topic, "KILL SWITCH ACTIVE", kill_switch.status_line, priority="urgent")
        return

    account_equity = fetch_account_equity(client, backend.account_key)

    # Skip the cycle if equity is unknown — a transient Saxo timeout must
    # not masquerade as a drawdown and trip the daily-loss guard. Repeated
    # failures trip the kill switch: we can't protect positions without
    # equity data.
    if account_equity is None:
        if kill_switch.record_equity_fetch_failure():
            print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
            print("  Flattening all positions...")
            backend.flatten_all()
            notify(ntfy_topic, "KILL SWITCH — equity fetch failures",
                   kill_switch.status_line, priority="urgent")
        else:
            remaining = (kill_switch.max_consecutive_fetch_failures
                         - kill_switch.consecutive_fetch_failures)
            print(f"\n  Skipping cycle — account equity unavailable "
                  f"(failure {kill_switch.consecutive_fetch_failures}/"
                  f"{kill_switch.max_consecutive_fetch_failures}, "
                  f"{remaining} before halt).")
            notify(ntfy_topic, "Multi-strategy skipped",
                   f"Saxo balance unavailable — cycle skipped "
                   f"({remaining} skips before halt).",
                   priority="urgent")
        return
    kill_switch.record_equity_fetch_success()

    if kill_switch.check_and_trigger(account_equity):
        print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
        backend.flatten_all()
        notify(ntfy_topic, "KILL SWITCH — flattened", kill_switch.status_line, priority="urgent")
        return

    current_positions = backend.get_positions()

    print("\n" + "=" * 70)
    print(f"  Multi-Strategy Cycle — {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Equity: {account_equity:,.2f}")
    print("=" * 70)

    for pair in pairs:
        print(f"\n--- {pair} ---")

        # Compute blended signal
        blended, details = compute_blended_signals(
            client, pair, strategy_configs, rate_data,
        )

        # Show individual strategy signals
        for d in details:
            status_str = f"{d['signal']:>+.3f}" if d["status"] == "OK" else d["status"]
            print(f"  {d['strategy']:>15s}/{d['timeframe']:<6s}  w={d['weight']:.2f}  signal={status_str}")
        print(f"  {'BLENDED':>15s}        signal={blended:>+.3f}")

        # Get current price
        try:
            price_info = client.get_info_price(pair)
            quote = price_info.get("Quote", {})
            bid = quote.get("Bid", 0)
            ask = quote.get("Ask", 0)
            pip = 0.01 if "JPY" in pair else 0.0001
            spread = (ask - bid) / pip if bid and ask else 0
        except Exception:
            bid, ask, spread = 0, 0, 0

        print(f"  Price: {bid:.5f} / {ask:.5f}  (spread: {spread:.1f} pips)")

        # Use max ATR (longest timeframe) for sizing — reflects true risk horizon
        atrs = [d["atr"] for d in details if d["status"] == "OK" and "atr" in d]
        avg_atr = max(atrs) if atrs else 0
        price = (bid + ask) / 2 if bid and ask else 0

        # Current position
        current_pos = current_positions.get(pair)
        pos_str = "FLAT" if not current_pos else f"{current_pos.direction.name} {current_pos.size:.0f}"
        print(f"  Current: {pos_str}")

        # Compute proposed action
        if abs(blended) < 1e-6:
            if not current_pos:
                print(f"  Action: HOLD FLAT")
                continue
            else:
                proposed_action = "CLOSE"
                proposed_size = current_pos.size
                needs_action = True
        else:
            proposed_size = sizer.calculate_size(
                blended, account_equity, price, avg_atr, pair,
            )
            direction = "LONG" if blended > 0 else "SHORT"

            if proposed_size == 0.0:
                print(f"  Action: HOLD (below min size for {direction})")
                continue

            proposed_action = f"GO {direction} {proposed_size:.0f} units"
            needs_action = False

            if not current_pos:
                needs_action = True
            elif (blended > 0) != (current_pos.direction == Direction.LONG):
                needs_action = True  # Reverse
            elif current_pos.size > 0:
                size_ratio = abs(proposed_size - current_pos.size) / current_pos.size
                if size_ratio > REBALANCE_THRESHOLD:
                    needs_action = True
                    proposed_action = (
                        f"REBALANCE {direction} {current_pos.size:.0f}"
                        f" -> {proposed_size:.0f} ({size_ratio:+.0%})"
                    )

        print(f"  Proposed: {proposed_action}")

        if not needs_action:
            print(f"  Action: NO CHANGE NEEDED")
            continue

        # Execute
        is_rebalance = "REBALANCE" in proposed_action
        if is_rebalance:
            close_result = backend.execute_signal(pair, 0, 0)
            trade_log.record(close_result, signal=0, strategy="multi",
                             source="paper", context={"equity": account_equity, "rebalance": True})
            if not close_result.success:
                print(f"  Result: REBALANCE CLOSE FAILED: {close_result.error}")
                continue
            time.sleep(1.5)

        if abs(blended) < 1e-6:
            # Close only
            result = backend.execute_signal(pair, 0, 0)
        else:
            result = backend.execute_signal(pair, blended, proposed_size)

        status = "EXECUTED" if result.success else f"FAILED: {result.error}"
        if is_rebalance:
            status = f"REBALANCED — {status}"
        print(f"  Result: {status}")

        trade_log.record(
            result, signal=blended, strategy="multi",
            source="paper", context={
                "equity": account_equity,
                "strategies": str([(d["strategy"], d["timeframe"], d["signal"]) for d in details]),
            },
        )

        direction = "LONG" if blended > 0 else "SHORT" if blended < 0 else "FLAT"
        notify(
            ntfy_topic,
            f"Trade {status}: {pair}",
            f"{pair} {direction} {proposed_size:.0f}\n"
            f"Blended: {blended:+.3f} | Equity: {account_equity:,.0f}\n"
            + "\n".join(f"  {d['strategy']}/{d['timeframe']}: {d['signal']:+.3f}" for d in details if d["status"] == "OK"),
            priority="high" if result.success else "urgent",
        )
        time.sleep(1.5)

    # Reconcile
    time.sleep(2)
    discrepancies = backend.reconcile()
    if discrepancies:
        print(f"\n  RECONCILIATION WARNINGS: {discrepancies}")
        kill_switch.trigger(TriggerReason.RECONCILIATION, discrepancies[0], account_equity)
        backend.flatten_all()
        notify(ntfy_topic, "KILL SWITCH — reconciliation", discrepancies[0], priority="urgent")
    else:
        print("\n  Reconciliation: OK")


def main():
    parser = argparse.ArgumentParser(description="Multi-strategy paper trading")
    parser.add_argument("--token", default=os.environ.get("SAXO_TOKEN"),
                        help="Saxo SIM bearer token")
    parser.add_argument("--config", required=True, help="Portfolio config YAML")
    parser.add_argument("--auto", action="store_true", default=True,
                        help="Auto-approve trades (default: True)")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--ntfy", metavar="TOPIC", help="ntfy.sh topic for notifications")
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or SAXO_TOKEN required")
        sys.exit(1)

    # Load config
    with open(args.config) as f:
        config = yaml.safe_load(f)

    pairs = [p["symbol"] for p in config["pairs"]]
    portfolio = config["portfolio"]
    strategy_configs = portfolio["strategies"]
    check_interval = portfolio.get("check_interval", 1800)
    sizing = config["backtest"]["position_sizing"]

    total_weight = sum(s["weight"] for s in strategy_configs)
    if abs(total_weight - 1.0) > 0.01:
        print(f"Warning: strategy weights sum to {total_weight:.2f}, not 1.0")

    # Load rate data for carry strategies
    rate_data = None
    has_carry = any(s["name"] in ("carry", "carry_momentum") for s in strategy_configs)
    if has_carry:
        rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
        col_map = {c: c.replace("_diff", "") for c in rate_data.columns}
        rate_data = rate_data.rename(columns=col_map)

    client = SaxoClient(args.token, live=False)
    backend = SaxoExecutionBackend(client)
    sizer = ContinuousSizer(
        risk_per_trade=sizing.get("risk_per_trade", 0.01),
        stop_loss_atr_multiple=sizing.get("stop_loss_atr_multiple", 2.0),
    )
    pred_log = PredictionLog(output_dir="data/predictions")
    trade_log = TradeLog(output_dir="data/trades")
    initial_equity = fetch_account_equity(client, backend.account_key)
    if initial_equity is None:
        print("Error: could not fetch initial account equity from Saxo. "
              "Refusing to start with an unknown baseline.")
        sys.exit(1)
    kill_switch = KillSwitch(initial_equity=initial_equity)

    print("=" * 70)
    print("  MULTI-STRATEGY PAPER TRADING")
    print(f"  Config: {args.config}")
    print(f"  Pairs: {', '.join(pairs)}")
    print(f"  Strategies: {len(strategy_configs)}")
    for s in strategy_configs:
        print(f"    {s['name']}/{s['timeframe']}  weight={s['weight']}")
    print(f"  Equity: {initial_equity:,.2f}")
    print(f"  Check interval: {check_interval}s")
    if args.ntfy:
        print(f"  Notifications: ntfy.sh/{args.ntfy}")
    print("=" * 70)

    # Show current positions
    positions = backend.get_positions()
    if positions:
        print("\nExisting positions:")
        for pair, pos in positions.items():
            print(f"  {pair}: {pos.direction.name} {pos.size:.0f} @ {pos.entry_price:.4f}")

    if args.loop:
        print(f"\nRunning in loop mode (every {check_interval}s). Ctrl+C to stop.")
        try:
            while True:
                run_signal_cycle(
                    client, backend, pairs, strategy_configs, sizer,
                    pred_log, trade_log, kill_switch, rate_data, args.ntfy,
                )
                pred_log.flush()
                trade_log.flush()
                print(f"\nNext check in {check_interval}s...")
                time.sleep(check_interval)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        run_signal_cycle(
            client, backend, pairs, strategy_configs, sizer,
            pred_log, trade_log, kill_switch, rate_data, args.ntfy,
        )

    pred_log.close()
    trade_log.close()
    print(trade_log.execution_quality_report())


if __name__ == "__main__":
    main()
