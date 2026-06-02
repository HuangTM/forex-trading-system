#!/usr/bin/env python3
"""Observe-only momentum canary (EURUSD) — Saxo SIM.

SHAKEDOWN / DATA-GATHERING, NOT alpha validation. Per the 2026-05-31 honest review
there is no validated edge; momentum EURUSD (n=126, oos=true, Sharpe~0.31) is the only
honest survivor, run here purely to exercise the now-fixed paper READ path (Saxo
connectivity, chart fetch, indicator/signal generation) on live SIM data and to
accumulate a backtest-faithful signal/decision series.

OBSERVE-ONLY — STRUCTURAL guarantee:
    The Saxo client is wrapped in ReadOnlySaxoClient, which exposes ONLY read methods;
    any mutating call (place_order / close_position / close_all_positions / cancel_order)
    raises AttributeError. So this canary cannot place an order even if a future edit
    tries to — the invariant is structural, not by-convention.
    It generates NO fills, so it does NOT calibrate the cost-reconciliation tolerance
    and does NOT confirm the Saxo marking convention (both need real positions).

    It deliberately does NOT write to PredictionLog: that is the DSR / honest-N trial
    denominator, and logging an unvalidated observe-only strategy there would inflate N
    and cause false-negative DSR gating (NHT risk). The standalone JSONL below is the
    only sink.

Usage:
    SAXO_TOKEN=<24h-sim-token> python scripts/run_observe_momentum_eurusd.py
    SAXO_TOKEN=<24h-sim-token> python scripts/run_observe_momentum_eurusd.py --loop --interval 3600
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from forex_system.core.config import load_config
from forex_system.features.registry import compute_indicators
from forex_system.saxo.client import SaxoClient
from forex_system.saxo.history import bars_to_dataframe
from forex_system.strategies.momentum import MomentumStrategy

OBS_LOG_PATH = "data/paper_observe_momentum_eurusd.jsonl"
DEFAULT_CONFIG = "config/default.yaml"


class ReadOnlySaxoClient:
    """Structural observe-only guard: wraps a SaxoClient exposing ONLY read methods.

    Any non-whitelisted (mutating) method raises AttributeError, so the observe
    canary cannot place/cancel/close an order even via a future maintenance edit.
    """

    _READ_ONLY = frozenset({
        "get_chart_data", "get_chart_data_range", "get_account_info", "get_balance",
        "get_positions", "get_instrument_details", "get_info_price", "get_account_key",
        "get_open_orders", "get_net_positions",
    })

    def __init__(self, client: SaxoClient) -> None:
        object.__setattr__(self, "_client", client)

    @property
    def is_live(self) -> bool:
        return bool(getattr(self._client, "is_live", False))

    def __getattr__(self, name: str):
        if name in ReadOnlySaxoClient._READ_ONLY:
            return getattr(object.__getattribute__(self, "_client"), name)
        raise AttributeError(
            f"ReadOnlySaxoClient blocks '{name}': observe-only canary may not call "
            "mutating or non-whitelisted SaxoClient methods."
        )


def notify(topic: str | None, title: str, message: str, priority: str = "default") -> None:
    """Best-effort ntfy.sh push; no-ops without a topic or on error."""
    if not topic:
        return
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": priority},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _momentum_params(config) -> dict:
    """Read momentum params from config (strategies.momentum), with safe defaults."""
    raw = getattr(config, "raw", {}) or {}
    params = dict(raw.get("strategies", {}).get("momentum", {}))
    params.setdefault("lookback_period", 20)
    params.setdefault("threshold", 0.0)
    return params


def drop_forming_bar(ohlcv: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """Return OHLCV with the current (forming) bar removed, so signals use the last
    CLOSED bar — matching the backtest's closed-bar convention.

    daily: a bar dated today (UTC) is still forming -> drop it.
    intraday (4h/1h): conservatively drop the last bar (likely forming).
    """
    if ohlcv.empty:
        return ohlcv
    if horizon == "daily":
        last_date = pd.Timestamp(ohlcv.index[-1]).date()
        if last_date >= datetime.now(timezone.utc).date():
            return ohlcv.iloc[:-1]
        return ohlcv
    return ohlcv.iloc[:-1]  # intraday: drop the possibly-forming latest bar


def compute_observation(ohlcv_closed: pd.DataFrame, params: dict) -> dict:
    """Pure: latest momentum signal on the last CLOSED bar. No I/O.

    `ohlcv_closed` must already have the forming bar removed (see drop_forming_bar).
    Raises ValueError if there is not enough data to form a signal.
    """
    period = int(params.get("lookback_period", 20))
    mom_col = f"momentum_{period}"
    if ohlcv_closed.empty or len(ohlcv_closed) < period + 2:
        raise ValueError(f"insufficient closed bars: have {len(ohlcv_closed)}, need >= {period + 2}")

    enriched = compute_indicators(ohlcv_closed, [mom_col])
    strategy = MomentumStrategy({**params, "pair": "EURUSD"})
    signals = strategy.generate_signals(enriched)
    sig = float(signals.iloc[-1])
    mom_val = enriched[mom_col].iloc[-1]
    return {
        "signal": sig,
        "would_be_position": ("LONG" if sig > 0 else "SHORT" if sig < 0 else "FLAT"),
        "momentum_value": (None if pd.isna(mom_val) else float(mom_val)),
        "price": float(ohlcv_closed["close"].iloc[-1]),
        "signal_bar_ts": pd.Timestamp(ohlcv_closed.index[-1]).isoformat(),
        "n_closed_bars": int(len(ohlcv_closed)),
    }


def fetch_recent_bars(client, pair: str, count: int, horizon: str) -> pd.DataFrame:
    data = client.get_chart_data(pair, horizon=horizon, count=count)
    bars = data.get("Data", [])
    if not bars:
        return pd.DataFrame()
    df = bars_to_dataframe(bars)
    return df[["open", "high", "low", "close", "volume"]]


def fetch_account_equity(client, account_key: str) -> float | None:
    try:
        balance = client.get_balance(account_key)
        equity = balance.get("TotalValue", 0.0)
        return float(equity) if equity else None
    except Exception:
        return None


def build_observation(client, account_key: str, params: dict, horizon: str, count: int) -> dict:
    """One read-only observation cycle: fetch -> trim forming bar -> compute. No write."""
    ohlcv = fetch_recent_bars(client, "EURUSD", count=count, horizon=horizon)
    closed = drop_forming_bar(ohlcv, horizon)
    obs = compute_observation(closed, params)
    equity = fetch_account_equity(client, account_key)
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "strategy": "momentum_observe", "pair": "EURUSD", "horizon": horizon,
        "observe_only": True, "account_equity": equity, **obs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", default=os.environ.get("SAXO_TOKEN"))
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--timeframe", default="daily", choices=["daily", "4h", "1h"])
    parser.add_argument("--count", type=int, default=300, help="bars to fetch")
    parser.add_argument("--account-key", default=None, help="override auto-detected account")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=3600, help="seconds between cycles")
    parser.add_argument("--ntfy", metavar="TOPIC")
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or SAXO_TOKEN required (24h SIM developer token).")
        return 2

    config = load_config(args.config)
    params = _momentum_params(config)
    print(f"momentum params: {params}  | OBSERVE-ONLY (read-only client; no orders possible)")

    raw_client = SaxoClient(args.token, live=False, startup_jitter=False)  # SIM only
    if getattr(raw_client, "is_live", False):
        print("Error: refusing to run against a LIVE client. SIM only.")
        return 2
    client = ReadOnlySaxoClient(raw_client)

    # HIGH-3: surface multi-account ambiguity instead of silently using account[0].
    if args.account_key:
        account_key = args.account_key
    else:
        accounts = client.get_account_info().get("Data", [])
        if len(accounts) > 1:
            print(f"WARNING: {len(accounts)} SIM accounts found; using the first. "
                  "Pass --account-key to disambiguate.")
        account_key = client.get_account_key()
    print(f"Connected to SIM. account_key=***{account_key[-4:]}")

    last_logged_bar_ts: str | None = None
    while True:
        try:
            rec = build_observation(client, account_key, params, args.timeframe, args.count)
            is_new = rec["signal_bar_ts"] != last_logged_bar_ts
            status = "NEW closed bar" if is_new else "no new closed bar (skip write)"
            print(f"[observe {rec['ts']}] EURUSD signal={rec['signal']:+.1f} "
                  f"would_be={rec['would_be_position']} mom={rec['momentum_value']} "
                  f"price={rec['price']:.5f} bar={rec['signal_bar_ts']} equity={rec['account_equity']} "
                  f"| {status}")
            if is_new:  # HIGH-2: dedup — write only when the closed bar advances
                with open(OBS_LOG_PATH, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                notify(args.ntfy, "momentum-EURUSD observe",
                       f"signal={rec['signal']:+.1f} ({rec['would_be_position']}) @ {rec['price']:.5f}")
                last_logged_bar_ts = rec["signal_bar_ts"]
        except Exception as e:
            print(f"[observe] cycle error: {e}")
        if not args.loop:
            break
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
