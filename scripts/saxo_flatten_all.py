#!/usr/bin/env python3
"""D2 — Flatten all open Saxo SIM positions.

Operational procedure per CEO directive 2026-04-25:
  - Vol-target carry paper trading halted pending engine-strategy reconciliation.
  - Registered strategy Sharpe (0.0653) != paper-traded strategy Sharpe (0.76).
  - Flatten all SIM positions before halting the paper loop.

Safety constraints:
  1. Re-fetches positions immediately before placing orders (no stale snapshots).
  2. Places market order in opposite direction for each open net position.
  3. After all orders submitted, re-fetches positions and asserts net=0.
  4. If net=0 cannot be confirmed: emits POLICY_VIOLATION and exits non-zero.
  5. Never runs on LIVE environment (live=False enforced below).

Usage:
    export SAXO_TOKEN=your_24h_dev_token
    python scripts/saxo_flatten_all.py

    # Or pass directly:
    python scripts/saxo_flatten_all.py --token YOUR_TOKEN

    # Dry run (no orders placed — just shows what would happen):
    python scripts/saxo_flatten_all.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forex_system.saxo.client import PAIR_UICS, SaxoClient

DATE_TAG = "2026-04-26"
OUT_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_PATH = OUT_DIR / f"saxo_flatten_{DATE_TAG}.log"

# Rate limit: 1 order/sec is Saxo's documented limit. We sleep 1.2s between
# orders to stay under it with margin.
ORDER_SLEEP_SECS = 1.2

# After all orders are submitted, wait this long before the confirmation fetch.
# Market orders fill within ~200ms on SIM but we allow generous buffer.
POST_ORDER_SLEEP_SECS = 3.0


def _uic_to_pair(uic: int) -> str:
    for pair, u in PAIR_UICS.items():
        if u == uic:
            return pair
    return f"UIC:{uic}"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(log_path: Path, entry: dict) -> None:
    """Append a JSON line to the flatten log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def fetch_net_positions(client: SaxoClient, account_key: str) -> list[dict]:
    """Fetch and parse net positions. Returns list of position dicts."""
    raw = client.get_net_positions(client_key=account_key)
    positions = []
    for pos in raw:
        base = pos.get("NetPositionBase", {})
        view = pos.get("NetPositionView", {})
        amount = base.get("Amount", 0)
        if amount == 0:
            continue
        uic = base.get("Uic")
        pair = _uic_to_pair(uic) if uic is not None else "UNKNOWN"
        positions.append({
            "pair": pair,
            "uic": uic,
            "amount": amount,
            "direction": "LONG" if amount > 0 else "SHORT",
            "size": abs(amount),
            "entry_price": view.get("AverageOpenPrice", 0.0),
            "unrealized_pnl": view.get("ProfitLossOnTrade", 0.0),
            "net_position_id": pos.get("NetPositionId", "?"),
        })
    return positions


def run_flatten(token: str, dry_run: bool = False) -> dict:
    """Execute the flatten procedure.

    Returns a result dict with keys:
        - success: bool
        - orders_placed: list[dict]
        - positions_before: list[dict]
        - positions_after: list[dict]
        - policy_violation: str | None
        - errors: list[str]
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "success": False,
        "orders_placed": [],
        "positions_before": [],
        "positions_after": [],
        "policy_violation": None,
        "errors": [],
    }

    # --- Auth ---
    print("Authenticating to Saxo SIM...")
    client = SaxoClient(token, live=False)  # NEVER live=True here

    try:
        info = client.get_account_info()
    except Exception as e:
        if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e):
            raise RuntimeError(
                f"AUTH FAILED: {e}\n"
                "Token expired or invalid.\n"
                "Get a fresh token: https://www.developer.saxo/openapi/token"
            )
        raise RuntimeError(f"Network / API error during auth: {e}")

    accounts = info.get("Data", [])
    if not accounts:
        raise RuntimeError("No accounts returned.")
    account_key = accounts[0]["AccountKey"]
    print(f"  Account: {account_key}")

    _append_log(LOG_PATH, {
        "event": "FLATTEN_START",
        "timestamp": _now_utc(),
        "account_key": account_key,
        "dry_run": dry_run,
        "operator": "huangtm@gmail.com",
        "reason": "CEO directive 2026-04-25: flatten SIM pending engine-strategy reconciliation",
    })

    # --- Step 1: Re-fetch positions (live, not from D1 snapshot) ---
    print("\nFetching current positions (live re-fetch)...")
    try:
        positions_before = fetch_net_positions(client, account_key)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch positions before flatten: {e}")

    result["positions_before"] = positions_before

    _append_log(LOG_PATH, {
        "event": "POSITIONS_BEFORE",
        "timestamp": _now_utc(),
        "count": len(positions_before),
        "positions": positions_before,
    })

    if not positions_before:
        print("  No open positions found — nothing to flatten.")
        result["success"] = True
        _append_log(LOG_PATH, {
            "event": "FLATTEN_COMPLETE",
            "timestamp": _now_utc(),
            "orders_placed": 0,
            "net_zero_confirmed": True,
            "note": "No positions were open",
        })
        return result

    # --- Step 2: Place closing orders ---
    print(f"\nPositions to flatten: {len(positions_before)}")
    for pos in positions_before:
        close_side = "Sell" if pos["direction"] == "LONG" else "Buy"
        print(
            f"  {'[DRY RUN] ' if dry_run else ''}"
            f"Placing {close_side} {pos['pair']} {pos['size']:,.0f} units "
            f"(closing {pos['direction']} @ ~{pos['entry_price']:.4f})"
        )

        if dry_run:
            order_entry = {
                "event": "ORDER_DRY_RUN",
                "timestamp": _now_utc(),
                "pair": pos["pair"],
                "direction": close_side,
                "size": pos["size"],
                "entry_price_at_flatten": pos["entry_price"],
                "net_position_id": pos["net_position_id"],
                "order_id": "DRY_RUN",
                "fill_price": None,
            }
            result["orders_placed"].append(order_entry)
            _append_log(LOG_PATH, order_entry)
            continue

        # Live order placement
        try:
            order_resp = client.place_order(
                pair=pos["pair"],
                buy_sell=close_side,
                amount=int(pos["size"]),
                order_type="Market",
                account_key=account_key,
            )
            order_id = order_resp.get("OrderId", "unknown")
            # Saxo market orders don't return fill price synchronously —
            # we record mid price from info price as the best approximation.
            try:
                price_info = client.get_info_price(pos["pair"])
                quote = price_info.get("Quote", {})
                fill_price_approx = (quote.get("Bid", 0) + quote.get("Ask", 0)) / 2
            except Exception:
                fill_price_approx = None

            order_entry = {
                "event": "ORDER_PLACED",
                "timestamp": _now_utc(),
                "pair": pos["pair"],
                "direction": close_side,
                "size": pos["size"],
                "fill_price_approx": fill_price_approx,
                "order_id": order_id,
                "net_position_id": pos["net_position_id"],
                "api_response": order_resp,
            }
            result["orders_placed"].append(order_entry)
            _append_log(LOG_PATH, order_entry)
            fill_str = f"{fill_price_approx:.4f}" if fill_price_approx else "?"
            print(
                f"    -> OrderId={order_id}  approx_fill={fill_str}"
            )

        except Exception as e:
            err_msg = f"Order FAILED for {pos['pair']} {close_side} {pos['size']}: {e}"
            result["errors"].append(err_msg)
            print(f"    -> ERROR: {err_msg}")
            _append_log(LOG_PATH, {
                "event": "ORDER_FAILED",
                "timestamp": _now_utc(),
                "pair": pos["pair"],
                "direction": close_side,
                "size": pos["size"],
                "error": str(e),
            })

        if len(positions_before) > 1:
            time.sleep(ORDER_SLEEP_SECS)

    # --- Step 3: Confirm net=0 ---
    if dry_run:
        print("\n[DRY RUN] Skipping post-flatten confirmation.")
        result["success"] = True
        return result

    print(f"\nWaiting {POST_ORDER_SLEEP_SECS}s for fills to settle...")
    time.sleep(POST_ORDER_SLEEP_SECS)

    print("Re-fetching positions to confirm flat...")
    try:
        positions_after = fetch_net_positions(client, account_key)
    except Exception as e:
        msg = f"Could not fetch positions after flatten: {e}"
        result["errors"].append(msg)
        result["policy_violation"] = f"POLICY_VIOLATION: failed-to-confirm-flat — {msg}"
        print(f"\n  {result['policy_violation']}")
        _append_log(LOG_PATH, {
            "event": "CONFIRMATION_FAILED",
            "timestamp": _now_utc(),
            "error": msg,
        })
        return result

    result["positions_after"] = positions_after

    # Check which pairs from before are still open
    pairs_before = {p["pair"] for p in positions_before}
    pairs_still_open = {p["pair"] for p in positions_after if p["pair"] in pairs_before}

    if pairs_still_open:
        msg = (
            f"Pairs still have open positions after flatten attempt: "
            f"{sorted(pairs_still_open)}"
        )
        result["policy_violation"] = f"POLICY_VIOLATION: failed-to-confirm-flat — {msg}"
        print(f"\n  {result['policy_violation']}")
        print("  Leaving alarm in log. Operator must manually close remaining positions.")
        _append_log(LOG_PATH, {
            "event": "POLICY_VIOLATION",
            "timestamp": _now_utc(),
            "message": msg,
            "positions_after": positions_after,
        })
        return result

    # All previously-open pairs confirmed flat
    print(f"\n  Confirmation: net=0 confirmed on all {len(pairs_before)} pair(s).")
    result["success"] = True
    _append_log(LOG_PATH, {
        "event": "FLATTEN_COMPLETE",
        "timestamp": _now_utc(),
        "orders_placed": len(result["orders_placed"]),
        "pairs_flattened": sorted(pairs_before),
        "net_zero_confirmed": True,
        "positions_after": positions_after,
    })
    return result


def print_report(result: dict, dry_run: bool) -> None:
    """Print a human-readable summary of the flatten operation."""
    print("\n" + "=" * 60)
    print("  FLATTEN REPORT")
    print("=" * 60)

    print(f"\n  Positions before: {len(result['positions_before'])}")
    for p in result["positions_before"]:
        print(
            f"    {p['pair']:8} {p['direction']:5}  {p['size']:>12,.0f}  "
            f"entry={p['entry_price']:.4f}  pnl={p['unrealized_pnl']:+,.2f}"
        )

    print(f"\n  Orders placed: {len(result['orders_placed'])}")
    for o in result["orders_placed"]:
        fp = o.get("fill_price_approx")
        fp_str = f"{fp:.4f}" if fp else "?"
        print(
            f"    {o['pair']:8} {o['direction']:4}  {o['size']:>12,.0f}  "
            f"fill~{fp_str}  OrderId={o.get('order_id', '?')}"
        )

    if result["errors"]:
        print(f"\n  ERRORS ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"    {e}")

    if result["policy_violation"]:
        print(f"\n  *** {result['policy_violation']} ***")
        print("  ACTION REQUIRED: manually inspect and close remaining positions.")
    else:
        status = "DRY RUN — no orders placed" if dry_run else "net=0 CONFIRMED"
        print(f"\n  Status: {status}")

    print(f"\n  Log: {LOG_PATH}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Flatten all open Saxo SIM positions (operational)"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("SAXO_TOKEN"),
        help="Saxo SIM bearer token (or set SAXO_TOKEN env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without placing any orders",
    )
    args = parser.parse_args()

    if not args.token:
        print("ERROR: No token provided.")
        print()
        print("Get a 24-hour SIM token from:")
        print("  https://www.developer.saxo/openapi/token")
        print()
        print("Then run:")
        print("  export SAXO_TOKEN=your_token_here")
        print("  python scripts/saxo_flatten_all.py")
        sys.exit(1)

    if args.dry_run:
        print("*** DRY RUN MODE — no orders will be placed ***\n")

    try:
        result = run_flatten(args.token, dry_run=args.dry_run)
    except RuntimeError as e:
        print(f"\nSTOP: {e}")
        print("\nFlatten ABORTED — no positions were touched.")
        sys.exit(1)

    print_report(result, dry_run=args.dry_run)

    if result["policy_violation"]:
        sys.exit(2)
    elif not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
