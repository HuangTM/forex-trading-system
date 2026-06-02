#!/usr/bin/env python3
"""Probe: does Saxo `TotalValue` mark open positions at bid/ask close-out, or at mid?

Empirical confirmation of BC-COST-RECON precondition (ii) — see
docs/research/saxo_totalvalue_marking_2026-06-01.md for the documentary conclusion
(HIGH confidence: close-out / bid for long, ask for short). This script confirms it on
our own SIM account.

READ-ONLY by default: reads /port/v1/balances, /port/v1/positions, /trade/v1/infoprices.
For each open position it compares the broker's reported unrealized P&L against a
close-out-marked vs a mid-marked computation and prints `CurrentPriceType`.

Optional --open-and-flatten PAIR (SIM ONLY, hard-guarded): opens ~1,000 units, samples,
then immediately flattens — so you don't have to open a position by hand.

Usage:
    SAXO_TOKEN=<24h-sim-token> python scripts/probe_saxo_marking.py
    SAXO_TOKEN=<24h-sim-token> python scripts/probe_saxo_marking.py --open-and-flatten EURUSD
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from forex_system.saxo.client import PAIR_UICS, SaxoClient
from forex_system.saxo.execution import SaxoExecutionBackend

# Reverse map Uic -> pair symbol so we can tell whether a position's quote currency
# equals the (USD) account currency. Only USD-quoted pairs (symbol ends in "USD")
# let us compare account-ccy P&L arithmetically; for JPY/CHF/CAD-quoted and crosses
# the amount*(price-open) figure is in the quote ccy, not USD, so we skip the
# arithmetic verdict and rely on CurrentPriceType (which is unit-free and definitive).
_UIC_TO_PAIR = {uic: pair for pair, uic in PAIR_UICS.items()}


def _is_usd_quoted(pair: str | None) -> bool:
    return bool(pair) and pair.upper().endswith("USD")


def _analyze_positions(client: SaxoClient, account_key: str) -> int:
    """Read positions + balances, report bid/ask-close-out vs mid marking. Returns count."""
    balance = client.get_balance(account_key)
    print("\n=== /port/v1/balances ===")
    for k in (
        "TotalValue",
        "CashBalance",
        "UnrealizedPositionsValue",
        "UnrealizedMarginProfitLoss",
        "UnrealizedMarginOpenProfitLoss",
    ):
        if k in balance:
            print(f"  {k:32s} = {balance[k]}")

    positions = client.get_positions(account_key).get("Data", [])
    open_pos = [p for p in positions if p.get("PositionBase", {}).get("Amount", 0)]
    print(f"\n=== open positions: {len(open_pos)} ===")
    if not open_pos:
        print(
            "  No open positions. To confirm the convention, either open a tiny SIM\n"
            "  position manually in SaxoTraderGO, or re-run with --open-and-flatten EURUSD."
        )
        return 0

    for p in open_pos:
        base = p.get("PositionBase", {})
        view = p.get("PositionView", {})
        amount = base.get("Amount", 0.0)  # signed: >0 long, <0 short
        open_price = base.get("OpenPrice")
        bid = view.get("Bid")
        ask = view.get("Ask")
        cur = view.get("CurrentPrice")
        cur_type = view.get("CurrentPriceType")
        pl_broker = view.get("ProfitLossOnTrade")
        uic = base.get("Uic")

        pair = _UIC_TO_PAIR.get(uic)
        is_long = amount > 0
        print(f"\n  --- Uic={uic} ({pair or '?'}) Amount={amount} OpenPrice={open_price} ---")
        print(f"    Bid={bid}  Ask={ask}  CurrentPrice={cur}  CurrentPriceType={cur_type}")
        print(f"    ProfitLossOnTrade (broker) = {pl_broker}")

        # PRIMARY verdict — unit-free and definitive. Close-out marking means a long is
        # marked at Bid, a short at Ask. This does not depend on account currency.
        expected = "Bid" if is_long else "Ask"
        if cur_type is not None:
            ok = str(cur_type) == expected
            print(
                f"    => CurrentPriceType={cur_type!r} (expected {expected!r} for "
                f"{'long' if is_long else 'short'}): "
                + ("CLOSE-OUT ✓ — matches documentary conclusion" if ok else
                   "UNEXPECTED — investigate (does NOT match close-out marking)")
            )
        else:
            print("    => CurrentPriceType absent — cannot give primary verdict")

        # SECONDARY (arithmetic) — only valid when quote ccy == account ccy (USD-quoted).
        if None in (open_price, bid, ask) or not amount:
            print("    (insufficient price fields for arithmetic corroboration)")
            continue
        if not _is_usd_quoted(pair):
            print(
                f"    (arithmetic corroboration SKIPPED — {pair or 'unknown'} is not "
                "USD-quoted; amount*(price-open) would be in quote ccy, not USD)"
            )
            continue
        closeout = bid if is_long else ask  # close a long at bid, a short at ask
        mid = (bid + ask) / 2.0
        pl_closeout = amount * (closeout - open_price)
        pl_mid = amount * (mid - open_price)
        print(f"    close-out-marked P&L (bid/ask) ~ {pl_closeout:.2f} USD")
        print(f"    mid-marked       P&L          ~ {pl_mid:.2f} USD")
        if pl_broker is not None:
            closer = "CLOSE-OUT (bid/ask)" if abs(pl_broker - pl_closeout) < abs(
                pl_broker - pl_mid) else "MID"
            print(f"    => broker P&L arithmetically closer to: {closer}")
    return len(open_pos)


def _wait_for_position(client: SaxoClient, account_key: str, *, retries: int = 12,
                       interval_s: float = 1.0) -> bool:
    """Poll until at least one open position appears, or retries exhaust. Returns found."""
    for i in range(retries):
        positions = client.get_positions(account_key).get("Data", [])
        if any(p.get("PositionBase", {}).get("Amount", 0) for p in positions):
            return True
        print(f"    ...no position yet ({i + 1}/{retries}); waiting {interval_s}s")
        time.sleep(interval_s)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", default=os.environ.get("SAXO_TOKEN"))
    parser.add_argument(
        "--open-and-flatten",
        metavar="PAIR",
        help="SIM ONLY: open ~1000 units of PAIR, sample, then flatten. Omit for read-only.",
    )
    parser.add_argument("--units", type=float, default=1000.0)
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or SAXO_TOKEN required (24h SIM developer token).")
        return 2

    client = SaxoClient(args.token, live=False)  # SIM only
    if getattr(client, "is_live", False):
        print("Error: refusing to probe a LIVE client. SIM only.")
        return 2
    account_key = client.get_account_key()
    print(f"Connected to SIM. account_key=***{account_key[-4:]}")

    if args.open_and_flatten:
        pair = args.open_and_flatten.upper()
        backend = SaxoExecutionBackend(client)
        print(f"\n[open-and-flatten] SIM: opening ~{args.units:.0f} units long {pair} ...")
        res = backend.execute_signal(pair, 1.0, args.units)
        if not getattr(res, "success", False):
            print(f"  open FAILED: {getattr(res, 'error', res)} — aborting (nothing to flatten)")
            return 1
        print("  opened. polling for the filled position ...")
        rc = 0
        try:
            if not _wait_for_position(client, account_key):
                print(
                    "  ERROR: position did not appear after polling — SIM fill latency or "
                    "rejected fill. Verdict NOT produced; do not treat as confirmation."
                )
                rc = 1
            else:
                _analyze_positions(client, account_key)
        finally:
            print("\n[open-and-flatten] flattening all positions (SIM cleanup) ...")
            backend.flatten_all()
            print("  flattened.")
        return rc

    n = _analyze_positions(client, account_key)
    print(
        "\nDocumentary conclusion (HIGH confidence): Saxo TotalValue marks open positions at "
        "the close-out price (Bid for long, Ask for short), not mid.\n"
        "See docs/research/saxo_totalvalue_marking_2026-06-01.md."
    )
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
