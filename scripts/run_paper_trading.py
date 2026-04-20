#!/usr/bin/env python3
"""Paper trading — Manual mode (Autonomy Level 1).

Runs the carry-momentum strategy on live Saxo SIM data. For each signal:
1. Displays the proposed trade
2. Waits for human approval (y/n)
3. Executes on Saxo SIM if approved
4. Logs everything to the prediction log

This is the "reality tax" measurement phase — comparing what the strategy
wants to do against what actually happens on the broker.

Usage:
    export SAXO_TOKEN=your_token
    python scripts/run_paper_trading.py
    python scripts/run_paper_trading.py --auto  # skip approval (supervised mode)
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
from forex_system.features.registry import compute_indicators
from forex_system.risk.kill_switch import KillSwitch, TriggerReason
from forex_system.saxo.auth import SaxoAuth
from forex_system.saxo.client import SaxoClient
from forex_system.saxo.execution import SaxoExecutionBackend
from forex_system.saxo.history import bars_to_dataframe
from forex_system.sizing.continuous import ContinuousSizer
from forex_system.strategies.carry_momentum import CarryMomentumStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "config/carry_momentum_portfolio.yaml"
REBALANCE_THRESHOLD = 0.20  # Rebalance if target differs from current by >20%
LOCAL_TZ = ZoneInfo("America/Los_Angeles")
QUIET_HOURS = (20, 8)  # No notifications between 8pm and 8am local time


def notify(topic: str | None, title: str, message: str, priority: str = "default") -> None:
    """Send a push notification via ntfy.sh. No-op if topic is None."""
    if not topic:
        return

    # Respect quiet hours
    local_hour = datetime.now(LOCAL_TZ).hour
    quiet_start, quiet_end = QUIET_HOURS
    if quiet_start <= local_hour or local_hour < quiet_end:
        logger.info("Notification suppressed (quiet hours): %s", title)
        return

    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "chart_with_upwards_trend",
            },
            timeout=10,
        )
    except Exception as e:
        logger.warning("Failed to send notification: %s", e)


def fetch_recent_bars(
    client: SaxoClient, pair: str, count: int = 200, horizon: str = "daily",
) -> pd.DataFrame:
    """Fetch recent bars from Saxo for signal generation."""
    data = client.get_chart_data(pair, horizon=horizon, count=count)
    bars = data.get("Data", [])
    if not bars:
        return pd.DataFrame()
    df = bars_to_dataframe(bars)
    return df[["open", "high", "low", "close", "volume"]]


def fetch_account_equity(client: SaxoClient, account_key: str) -> float | None:
    """Fetch current account equity from Saxo balance API.

    Returns None if the balance cannot be reliably determined. Callers must
    treat None as "unknown equity" and skip any action that depends on it —
    never substitute a hardcoded fallback, which would desynchronize the
    kill-switch baseline and spuriously trip the daily-loss guard.
    """
    try:
        balance = client.get_balance(account_key)
        equity = balance.get("TotalValue", 0.0)
        if equity > 0:
            return equity
        cash = balance.get("CashBalance", 0.0)
        if cash > 0:
            logger.warning("TotalValue unavailable, using CashBalance: %.2f", cash)
            return cash
        logger.error("Balance API returned zero equity (TotalValue=%.2f, CashBalance=%.2f)",
                     equity, cash)
        return None
    except Exception as e:
        logger.warning("Could not fetch account balance: %s", e)
        return None


def run_signal_cycle(
    client: SaxoClient,
    backend: SaxoExecutionBackend,
    rate_data: pd.DataFrame,
    sizer: ContinuousSizer,
    pred_log: PredictionLog,
    trade_log: TradeLog,
    kill_switch: KillSwitch,
    portfolio_pairs: list[str],
    strategy_params: dict,
    auto_mode: bool = False,
    auth: SaxoAuth | None = None,
    ntfy_topic: str | None = None,
    horizon: str = "daily",
) -> dict:
    """Run one signal generation cycle across all portfolio pairs.

    Returns dict of {pair: signal_value} for logging.
    """
    # Auth death check — flatten everything if token chain is dying
    if auth and auth.should_emergency_flatten():
        kill_switch.trigger(
            TriggerReason.AUTH_DEATH,
            f"Token chain dying — {auth.minutes_to_auth_death:.1f}min remaining",
            0.0,
        )
        print(f"\n  AUTH CHAIN DYING — {auth.fuel_gauge}")
        print("  Flattening all positions...")
        backend.flatten_all()
        return {}

    # Kill switch check — halt all trading if triggered
    if kill_switch.is_triggered:
        print(f"\n  KILL SWITCH ACTIVE: {kill_switch.status_line}")
        print("  No trades will be executed. Reset required.")
        notify(ntfy_topic, "KILL SWITCH ACTIVE", kill_switch.status_line, priority="urgent")
        return {}

    signals_generated = {}
    account_equity = fetch_account_equity(client, backend.account_key)

    # Skip the cycle if equity is unknown — sizing and the daily-loss guard
    # both require a trustworthy number. A transient Saxo timeout must not
    # masquerade as a 100% drawdown. Repeated failures trip the kill switch
    # as a fail-safe — open positions can't be protected without equity data.
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
            notify(ntfy_topic, "Paper trading skipped",
                   f"Saxo balance unavailable — cycle skipped "
                   f"({remaining} skips before halt).",
                   priority="urgent")
        return {}
    kill_switch.record_equity_fetch_success()

    # Check daily P&L against kill switch threshold
    if kill_switch.check_and_trigger(account_equity):
        print(f"\n  KILL SWITCH TRIGGERED: {kill_switch.status_line}")
        print("  Flattening all positions...")
        backend.flatten_all()
        return {}

    # Get current positions from broker
    current_positions = backend.get_positions()

    print("\n" + "=" * 60)
    print(f"  Signal Cycle — {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Account equity: {account_equity:,.2f}")
    print("=" * 60)

    for pair in portfolio_pairs:
        print(f"\n--- {pair} ---")

        # Fetch recent data
        ohlcv = fetch_recent_bars(client, pair, count=200, horizon=horizon)
        if ohlcv.empty:
            print(f"  No data available for {pair}")
            continue

        # Compute indicators
        enriched = compute_indicators(ohlcv, ["sma_20", "sma_50", "atr_14"])
        enriched = enriched.dropna(subset=["atr_14", "sma_50"])

        if enriched.empty:
            print("  Not enough data after indicator warmup")
            continue

        # Generate signal
        strategy = CarryMomentumStrategy(
            {**strategy_params, "pair": pair}, rate_data=rate_data,
        )
        signals = strategy.generate_signals(enriched)
        current_signal = signals.iloc[-1]
        signals_generated[pair] = current_signal

        # Log to prediction log
        pred_log.log(
            signals.iloc[-1:], "carry_momentum", pair,
            parameters=strategy_params, source="paper",
        )

        # Get current price
        try:
            price_info = client.get_info_price(pair)
            quote = price_info.get("Quote", {})
            bid = quote.get("Bid", 0)
            ask = quote.get("Ask", 0)
            spread = (ask - bid) / (0.01 if "JPY" in pair else 0.0001)
        except Exception:
            bid, ask, spread = 0, 0, 0

        # Current position
        current_pos = current_positions.get(pair)
        pos_str = "FLAT"
        if current_pos:
            pos_str = f"{current_pos.direction.name} {current_pos.size:.0f}"

        # Compute proposed action
        current_atr = enriched["atr_14"].iloc[-1]
        price = enriched["close"].iloc[-1]

        if abs(current_signal) < 1e-6:
            proposed_action = "HOLD FLAT" if not current_pos else "CLOSE"
            proposed_size = current_pos.size if current_pos else 0
        else:
            proposed_size = sizer.calculate_size(
                current_signal, account_equity, price, current_atr, pair,
            )
            direction = "LONG" if current_signal > 0 else "SHORT"
            if proposed_size == 0.0:
                # Signal exists but below broker minimum — hold, don't close
                proposed_action = f"HOLD (below min size for {direction})"
            else:
                proposed_action = f"GO {direction} {proposed_size:.0f} units"

        # Determine if action needed
        needs_action = False
        is_rebalance = False
        if abs(current_signal) < 1e-6 and current_pos:
            needs_action = True  # Close
        elif abs(current_signal) >= 1e-6 and proposed_size > 0:
            if not current_pos:
                needs_action = True  # Open
            elif (current_signal > 0) != (current_pos.direction == Direction.LONG):
                needs_action = True  # Reverse
            elif current_pos.size > 0:
                # Same direction — check for size drift
                size_ratio = abs(proposed_size - current_pos.size) / current_pos.size
                if size_ratio > REBALANCE_THRESHOLD:
                    needs_action = True
                    is_rebalance = True
                    proposed_action = (
                        f"REBALANCE {direction} {current_pos.size:.0f}"
                        f" → {proposed_size:.0f} units ({size_ratio:+.0%})"
                    )

        # Display
        print(f"  Signal:      {current_signal:>+.3f}")
        print(f"  Price:       {bid:.4f} / {ask:.4f}  (spread: {spread:.1f} pips)")
        print(f"  Current:     {pos_str}")
        print(f"  Proposed:    {proposed_action}")

        if not needs_action:
            print("  Action:      NO CHANGE NEEDED")
            continue

        # Approval
        if auto_mode:
            approved = True
            print("  Action:      AUTO-APPROVED")
        else:
            response = input("  Execute? [y/N]: ").strip().lower()
            approved = response == "y"

        if approved:
            if is_rebalance:
                # Flatten existing, then re-open at target size
                close_result = backend.execute_signal(pair, 0, 0)
                trade_log.record(
                    close_result, signal=0, strategy="carry_momentum",
                    source="paper", context={"equity": account_equity, "rebalance": True},
                )
                if not close_result.success:
                    print(f"  Result:      REBALANCE CLOSE FAILED: {close_result.error}")
                    continue
                time.sleep(1.5)  # Saxo 1 order/sec rate limit
            result = backend.execute_signal(pair, current_signal, proposed_size)
            status = "EXECUTED" if result.success else f"FAILED: {result.error}"
            if is_rebalance:
                status = f"REBALANCED — {status}"
            print(f"  Result:      {status}")
            trade_log.record(
                result, signal=current_signal, strategy="carry_momentum",
                source="paper", context={"equity": account_equity, "rebalance": is_rebalance},
            )

            # Notify on trade execution
            direction = "LONG" if current_signal > 0 else "SHORT"
            notify(
                ntfy_topic,
                f"Trade {status}: {pair}",
                f"{pair} {direction} {proposed_size:.0f} @ {bid:.4f}/{ask:.4f}\n"
                f"Signal: {current_signal:+.3f} | Equity: {account_equity:,.0f}",
                priority="high" if result.success else "urgent",
            )
            time.sleep(1.5)  # Saxo 1 order/sec rate limit between pairs
        else:
            print("  Result:      SKIPPED by operator")

    # Reconcile after all orders
    time.sleep(2)
    discrepancies = backend.reconcile()
    if discrepancies:
        print("\n  RECONCILIATION WARNINGS:")
        for d in discrepancies:
            print(f"    {d}")
        kill_switch.trigger(
            TriggerReason.RECONCILIATION,
            f"{len(discrepancies)} discrepancies: {discrepancies[0]}",
            account_equity,
        )
        print("  KILL SWITCH TRIGGERED — flattening all positions")
        backend.flatten_all()
        notify(
            ntfy_topic, "KILL SWITCH — positions flattened",
            f"Reason: {discrepancies[0]}\nAll positions closed.",
            priority="urgent",
        )
    else:
        print("\n  Reconciliation: OK")

    return signals_generated


def main():
    parser = argparse.ArgumentParser(description="Paper trading — Manual mode")
    auth_group = parser.add_mutually_exclusive_group()
    auth_group.add_argument("--token", default=os.environ.get("SAXO_TOKEN"),
                            help="Static bearer token (24h dev token)")
    auth_group.add_argument("--oauth", metavar="CLIENT_ID",
                            help="OAuth PKCE login with Saxo client_id")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"Config file path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-approve all trades (Supervised mode)")
    parser.add_argument("--loop", action="store_true",
                        help="Run continuously, checking every bar close")
    parser.add_argument("--interval", type=int, default=None,
                        help="Seconds between checks (default: auto from timeframe)")
    parser.add_argument("--timeframe", default="daily", choices=["daily", "4h", "1h"],
                        help="Bar timeframe (default: daily)")
    parser.add_argument("--ntfy", metavar="TOPIC",
                        help="ntfy.sh topic for push notifications (8am-8pm Pacific only)")
    args = parser.parse_args()

    # Auto-set interval from timeframe if not specified
    if args.interval is None:
        args.interval = {"daily": 86400, "4h": 14400, "1h": 3600}[args.timeframe]

    if not args.token and not args.oauth:
        print("Error: Auth required — use --token or --oauth CLIENT_ID")
        sys.exit(1)

    # Load config from YAML
    config = load_config(args.config)
    portfolio_pairs = config.pair_symbols
    strategy_cfg = next(
        (s for s in config.strategies if s.name == "carry_momentum"), None,
    )
    if strategy_cfg is None:
        print("Error: carry_momentum strategy not found in config")
        sys.exit(1)
    strategy_params = strategy_cfg.params

    # Setup auth and client
    auth = None
    if args.oauth:
        auth = SaxoAuth(client_id=args.oauth)
        if not auth.is_authenticated:
            print("No saved session found — opening browser for Saxo login...")
            auth.login()
        else:
            print(f"Restored saved session — {auth.fuel_gauge}")
        auth.start_keepalive()  # Keep tokens alive between long sleep cycles
        client = SaxoClient.from_auth(auth)
    else:
        client = SaxoClient(args.token, live=False)
    backend = SaxoExecutionBackend(client)
    rate_data = pd.read_parquet("data/rates/rate_differentials.parquet")
    col_map = {c: c.replace("_diff", "") for c in rate_data.columns}
    rate_data = rate_data.rename(columns=col_map)

    sizer = ContinuousSizer(
        risk_per_trade=config.backtest.risk_per_trade,
        stop_loss_atr_multiple=config.backtest.stop_loss_atr_multiple,
    )
    pred_log = PredictionLog(output_dir="data/predictions")
    trade_log = TradeLog(output_dir="data/trades")

    # Fetch initial equity for kill switch baseline
    initial_equity = fetch_account_equity(client, backend.account_key)
    if initial_equity is None:
        print("Error: could not fetch initial account equity from Saxo. "
              "Refusing to start with an unknown baseline.")
        sys.exit(1)
    kill_switch = KillSwitch(initial_equity=initial_equity)

    print("=" * 60)
    print("  PAPER TRADING — JPY Carry-Momentum Portfolio")
    print(f"  Config: {args.config}")
    print(f"  Auth: {'OAuth PKCE' if auth else 'static token'}")
    print(f"  Mode: {'SUPERVISED (auto-approve)' if args.auto else 'MANUAL (human approval)'}")
    print(f"  Pairs: {', '.join(portfolio_pairs)}")
    print(f"  Account: {backend.account_key}")
    print(f"  Equity: {initial_equity:,.2f}")
    print(f"  Kill switch: {kill_switch.status_line} (max daily loss: {kill_switch.max_daily_loss_pct:.1%})")
    if auth:
        print(f"  Auth fuel: {auth.fuel_gauge}")
    print("=" * 60)

    # Show current positions
    positions = backend.get_positions()
    if positions:
        print("\nExisting positions:")
        for pair, pos in positions.items():
            print(f"  {pair}: {pos.direction.name} {pos.size:.0f} @ {pos.entry_price:.4f}")

    if args.loop:
        print(f"\nRunning in loop mode (every {args.interval}s). Ctrl+C to stop.")
        try:
            while True:
                run_signal_cycle(
                    client, backend, rate_data, sizer, pred_log, trade_log,
                    kill_switch, portfolio_pairs, strategy_params,
                    auto_mode=args.auto, auth=auth, ntfy_topic=args.ntfy, horizon=args.timeframe,
                )
                pred_log.flush()
                trade_log.flush()
                if auth:
                    print(f"  Auth: {auth.fuel_gauge}")
                print(f"\nNext check in {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped by operator.")
    else:
        run_signal_cycle(
            client, backend, rate_data, sizer, pred_log, trade_log,
            kill_switch, portfolio_pairs, strategy_params,
            auto_mode=args.auto, auth=auth, ntfy_topic=args.ntfy,
        )

    pred_log.close()
    trade_log.close()
    print("\nPaper trading session complete.")
    print("  Predictions: data/predictions/")
    print("  Trades: data/trades/")
    print(trade_log.execution_quality_report())


if __name__ == "__main__":
    main()
