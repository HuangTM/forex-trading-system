#!/usr/bin/env python3
"""D1 — Inventory open Saxo SIM positions.

Authenticates to Saxo SIM, lists all open net positions, prints a
markdown table to stdout, and saves both the structured inventory and
the raw API response to data/.

Usage:
    export SAXO_TOKEN=your_24h_dev_token
    python scripts/saxo_position_inventory.py

    # Or pass directly:
    python scripts/saxo_position_inventory.py --token YOUR_TOKEN

STOP policy: if auth fails this script exits with a non-zero code and
prints explicit manual instructions. It NEVER attempts to modify positions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forex_system.saxo.client import PAIR_UICS, SaxoClient

DATE_TAG = "2026-04-25"
OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def _uic_to_pair(uic: int) -> str:
    """Reverse lookup: UIC -> pair symbol."""
    for pair, u in PAIR_UICS.items():
        if u == uic:
            return pair
    return f"UIC:{uic}"


def run_inventory(token: str) -> list[dict]:
    """Authenticate, fetch positions, return structured list.

    Raises on auth failure (HTTP 401/403) or network error so callers
    can apply STOP policy.
    """
    client = SaxoClient(token, live=False)

    # --- Auth check: get account info ---
    print("Checking auth / account info...")
    try:
        info = client.get_account_info()
    except Exception as e:
        if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e):
            raise RuntimeError(
                f"AUTH FAILED: {e}\n"
                "Token is expired or invalid.\n"
                "Get a fresh 24h SIM token from:\n"
                "  https://www.developer.saxo/openapi/token\n"
                "Then re-run:\n"
                "  export SAXO_TOKEN=<token>\n"
                "  python scripts/saxo_position_inventory.py"
            )
        raise RuntimeError(f"Network / API error: {e}")

    accounts = info.get("Data", [])
    if not accounts:
        raise RuntimeError("No accounts returned — check token permissions.")

    acct = accounts[0]
    account_key = acct["AccountKey"]
    currency = acct.get("Currency", "?")
    print(f"  Account key: {account_key}")
    print(f"  Currency:    {currency}")

    # --- Balance ---
    try:
        balance = client.get_balance(account_key)
        equity = balance.get("TotalValue", balance.get("CashBalance", 0.0))
        print(f"  Equity:      {equity:,.2f} {currency}")
    except Exception as e:
        print(f"  Balance:     Could not fetch ({e})")
        balance = {}
        equity = None

    # --- Net positions (raw) ---
    print("\nFetching net positions...")
    raw_positions = client.get_net_positions(client_key=account_key)

    # --- Also fetch all open order positions for forensics ---
    print("Fetching all positions (individual legs)...")
    try:
        all_positions_raw = client.get_positions(client_key=account_key)
    except Exception as e:
        print(f"  Warning: could not fetch individual positions: {e}")
        all_positions_raw = {}

    # --- Save raw API responses ---
    raw_path = OUT_DIR / f"saxo_positions_raw_{DATE_TAG}.json"
    raw_payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "account_info": info,
        "balance": balance,
        "net_positions_raw": raw_positions,
        "all_positions_raw": all_positions_raw,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(raw_path, "w") as f:
        json.dump(raw_payload, f, indent=2, default=str)
    print(f"\nRaw API response saved: {raw_path}")

    # --- Parse into structured inventory ---
    inventory = []
    for pos in raw_positions:
        base = pos.get("NetPositionBase", {})
        view = pos.get("NetPositionView", {})

        amount = base.get("Amount", 0)
        if amount == 0:
            continue

        uic = base.get("Uic")
        pair = _uic_to_pair(uic) if uic is not None else "UNKNOWN"
        direction = "LONG" if amount > 0 else "SHORT"
        size = abs(amount)
        entry_price = view.get("AverageOpenPrice", 0.0)
        unrealized_pnl = view.get("ProfitLossOnTrade", 0.0)
        net_position_id = pos.get("NetPositionId", "?")

        inventory.append({
            "pair": pair,
            "direction": direction,
            "size": size,
            "entry_price": entry_price,
            "unrealized_pnl_account_currency": unrealized_pnl,
            "net_position_id": net_position_id,
            "uic": uic,
            "account_key": account_key,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    # --- Save structured inventory ---
    inventory_path = OUT_DIR / f"saxo_positions_{DATE_TAG}.json"
    inventory_payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "account_key": account_key,
        "account_currency": currency,
        "equity": equity,
        "positions": inventory,
        "position_count": len(inventory),
    }
    with open(inventory_path, "w") as f:
        json.dump(inventory_payload, f, indent=2, default=str)
    print(f"Structured inventory saved: {inventory_path}")

    return inventory


def print_markdown_table(inventory: list[dict]) -> None:
    """Print the position inventory as a markdown table."""
    print("\n## Open Positions — Saxo SIM")
    if not inventory:
        print("\n_No open positions._\n")
        return

    header = "| Pair | Dir | Size | Entry Price | Unrealized PnL | NetPositionId |"
    sep    = "|------|-----|------|-------------|----------------|---------------|"
    print(header)
    print(sep)
    for p in inventory:
        pair = p["pair"]
        direction = p["direction"]
        size = f"{p['size']:,.0f}"
        entry = f"{p['entry_price']:.4f}" if p["entry_price"] else "?"
        pnl = f"{p['unrealized_pnl_account_currency']:+,.2f}"
        pos_id = p["net_position_id"]
        print(f"| {pair} | {direction} | {size} | {entry} | {pnl} | {pos_id} |")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Inventory open Saxo SIM positions (read-only)"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("SAXO_TOKEN"),
        help="Saxo SIM bearer token (or set SAXO_TOKEN env var)",
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
        print("  python scripts/saxo_position_inventory.py")
        sys.exit(1)

    try:
        inventory = run_inventory(args.token)
    except RuntimeError as e:
        print(f"\nSTOP: {e}")
        print("\nInventory ABORTED — no positions were touched.")
        sys.exit(1)

    print_markdown_table(inventory)

    if inventory:
        print(f"Total open positions: {len(inventory)}")
    else:
        print("No open positions found.")

    print("\nInventory complete. No positions were modified.")


if __name__ == "__main__":
    main()
