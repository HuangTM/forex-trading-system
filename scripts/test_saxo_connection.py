#!/usr/bin/env python3
"""Test Saxo SIM connectivity — run this before paper trading.

Three checks:
  1. Account info (auth works, get account key)
  2. Price quote (market data works, show live bid/ask)
  3. Recent bars (chart API works, fetch last 5 daily bars)

Usage:
    export SAXO_TOKEN=your_24h_dev_token
    python scripts/test_saxo_connection.py

    # Or pass directly:
    python scripts/test_saxo_connection.py --token YOUR_TOKEN

Get a 24-hour SIM token from: https://www.developer.saxo/openapi/token
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forex_system.saxo.client import PAIR_UICS, SaxoClient
from forex_system.saxo.history import bars_to_dataframe

PORTFOLIO_PAIRS = ["USDJPY", "GBPJPY", "CADJPY"]


def main():
    parser = argparse.ArgumentParser(description="Test Saxo SIM connectivity")
    parser.add_argument(
        "--token",
        default=os.environ.get("SAXO_TOKEN"),
        help="Saxo SIM bearer token (or set SAXO_TOKEN env var)",
    )
    args = parser.parse_args()

    if not args.token:
        print("Error: No token provided.")
        print()
        print("Get a 24-hour SIM token from:")
        print("  https://www.developer.saxo/openapi/token")
        print()
        print("Then run:")
        print("  export SAXO_TOKEN=your_token_here")
        print("  python scripts/test_saxo_connection.py")
        sys.exit(1)

    client = SaxoClient(args.token, live=False)
    all_ok = True

    # --- Check 1: Account Info ---
    print("=" * 50)
    print("  CHECK 1: Account Info")
    print("=" * 50)
    try:
        info = client.get_account_info()
        accounts = info.get("Data", [])
        if not accounts:
            print("  FAIL: No accounts returned")
            all_ok = False
        else:
            acct = accounts[0]
            account_key = acct.get("AccountKey", "?")
            currency = acct.get("Currency", "?")
            acct_type = acct.get("AccountType", "?")
            print(f"  Account key:  {account_key}")
            print(f"  Currency:     {currency}")
            print(f"  Type:         {acct_type}")

            # Try balance
            try:
                balance = client.get_balance(account_key)
                total = balance.get("TotalValue", 0)
                cash = balance.get("CashBalance", 0)
                margin = balance.get("MarginAvailable", 0)
                print(f"  Total value:  {total:,.2f} {currency}")
                print(f"  Cash balance: {cash:,.2f} {currency}")
                print(f"  Margin avail: {margin:,.2f} {currency}")
            except Exception as e:
                print(f"  Balance:      Could not fetch ({e})")

            print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        if "401" in str(e) or "Unauthorized" in str(e):
            print()
            print("  Token is invalid or expired.")
            print("  Get a fresh one from: https://www.developer.saxo/openapi/token")
        all_ok = False

    # --- Check 2: UIC Verification ---
    print()
    print("=" * 50)
    print("  CHECK 2: UIC Verification")
    print("=" * 50)
    uic_ok = True
    for pair in PORTFOLIO_PAIRS:
        expected_uic = PAIR_UICS.get(pair)
        try:
            resp = client._get(
                "/ref/v1/instruments",
                params={"Keywords": pair, "AssetTypes": "FxSpot"},
            )
            resp.raise_for_status()
            data = resp.json().get("Data", [])
            match = next((i for i in data if i.get("Symbol") == pair), None)
            if match is None:
                print(f"  {pair}:  FAIL — not found in instrument search")
                uic_ok = False
            elif match["Identifier"] != expected_uic:
                print(
                    f"  {pair}:  MISMATCH — client has UIC {expected_uic}, "
                    f"API returns UIC {match['Identifier']}"
                )
                uic_ok = False
            else:
                print(f"  {pair}:  UIC {expected_uic} confirmed")
        except Exception as e:
            print(f"  {pair}:  FAIL — {e}")
            uic_ok = False
    if uic_ok:
        print("  PASS")
    else:
        print("  FAIL — UICs in client.py need updating!")
    all_ok = all_ok and uic_ok

    # --- Check 3: Price Quotes ---
    print()
    print("=" * 50)
    print("  CHECK 3: Live Prices")
    print("=" * 50)
    price_ok = True
    for pair in PORTFOLIO_PAIRS:
        try:
            price = client.get_info_price(pair)
            quote = price.get("Quote", {})
            bid = quote.get("Bid", 0)
            ask = quote.get("Ask", 0)
            if not bid or not ask:
                print(f"  {pair}:  WARN — zero quote (market may be closed)")
                price_ok = False
                continue
            pip = 0.01 if "JPY" in pair else 0.0001
            spread = (ask - bid) / pip
            print(f"  {pair}:  {bid:.3f} / {ask:.3f}  (spread: {spread:.1f} pips)")
        except Exception as e:
            print(f"  {pair}:  FAIL — {e}")
            price_ok = False
    if price_ok:
        print("  PASS")
    else:
        print("  WARN — some quotes unavailable (check market hours)")
    all_ok = all_ok and price_ok

    # --- Check 4: Chart Data ---
    print()
    print("=" * 50)
    print("  CHECK 4: Chart Data (last 5 daily bars)")
    print("=" * 50)
    chart_ok = True
    for pair in PORTFOLIO_PAIRS:
        try:
            data = client.get_chart_data(pair, horizon="daily", count=5)
            bars = data.get("Data", [])
            if not bars:
                print(f"  {pair}:  No bars returned")
                chart_ok = False
                continue
            df = bars_to_dataframe(bars)
            latest = df.iloc[-1]
            print(
                f"  {pair}:  {len(df)} bars, "
                f"latest: {df.index[-1].strftime('%Y-%m-%d')} "
                f"O={latest['open']:.3f} H={latest['high']:.3f} "
                f"L={latest['low']:.3f} C={latest['close']:.3f}"
            )
        except Exception as e:
            print(f"  {pair}:  FAIL — {e}")
            chart_ok = False
    if chart_ok:
        print("  PASS")
    all_ok = all_ok and chart_ok

    # --- Summary ---
    print()
    print("=" * 50)
    if all_ok:
        print("  ALL CHECKS PASSED — ready for paper trading")
        print()
        print("  Next step:")
        print("    python scripts/run_paper_trading.py --token $SAXO_TOKEN")
    else:
        print("  SOME CHECKS FAILED — fix issues above first")
    print("=" * 50)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
