#!/usr/bin/env python3
"""Check carry trade viability per pair using current central bank rates.

Fetches current rates from FRED and computes whether carry is positive
after Saxo Bank's transaction costs. This is a research script, not a
production module.

Usage:
    pip install fredapi
    python scripts/check_swap_rates.py --api-key YOUR_FRED_API_KEY
    # or: FRED_API_KEY=... python scripts/check_swap_rates.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add src to path for config loading
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from fredapi import Fred
except ImportError:
    print("fredapi not installed. Run: pip install 'forex-system[research]'")
    sys.exit(1)

from forex_system.core.config import load_config

# FRED series IDs for central bank policy rates
RATE_SERIES = {
    "USD": "FEDFUNDS",       # Federal Funds Effective Rate
    "EUR": "ECBMRRFR",       # ECB Main Refinancing Operations Rate
    "JPY": "INTDSRJPM193N",  # Japan Discount Rate
}
# BOE rate not reliably available on FRED; hardcoded with last-known value
BOE_RATE = 3.75  # Bank of England bank rate as of 2026-03-20

# Pair definitions: (base_currency, quote_currency, carry_direction_description)
PAIRS = {
    "EURUSD": ("EUR", "USD", "Long EURUSD = long EUR, short USD"),
    "USDJPY": ("USD", "JPY", "Long USDJPY = long USD, short JPY"),
    "GBPUSD": ("GBP", "USD", "Long GBPUSD = long GBP, short USD"),
}


def fetch_latest_rates(api_key: str) -> dict[str, float]:
    """Fetch the most recent central bank rate for each currency."""
    fred = Fred(api_key=api_key)
    rates = {}

    for currency, series_id in RATE_SERIES.items():
        try:
            series = fred.get_series(series_id)
            rates[currency] = series.dropna().iloc[-1]
        except Exception as e:
            print(f"  Warning: Could not fetch {currency} ({series_id}): {e}")
            rates[currency] = float("nan")

    rates["GBP"] = BOE_RATE
    return rates


def compute_carry(rates: dict[str, float], config_path: str) -> None:
    """Compute and display carry trade viability per pair."""
    config = load_config(config_path)
    pair_costs = {p.symbol: p for p in config.pairs}

    print("\n=== Central Bank Rates ===")
    for currency, rate in sorted(rates.items()):
        print(f"  {currency}: {rate:.2f}%")

    print("\n=== Carry Analysis ===")
    print(f"{'Pair':<10} {'Long Carry':<12} {'Short Carry':<13} {'RT Cost':<12} {'Viable?'}")
    print("-" * 60)

    for symbol, (base, quote, desc) in PAIRS.items():
        base_rate = rates.get(base, float("nan"))
        quote_rate = rates.get(quote, float("nan"))

        # Long carry = base rate - quote rate (you earn base, pay quote)
        long_carry_pct = base_rate - quote_rate
        short_carry_pct = -long_carry_pct

        # Get transaction costs from config
        pair_cfg = pair_costs.get(symbol)
        if pair_cfg:
            rt_cost_pips = (
                pair_cfg.spread_pips + pair_cfg.slippage_pips * 2 + pair_cfg.commission_pips
            )
            # Approximate annual cost as % (assuming monthly rebalance = 12 RT/year)
            # 1 pip on EURUSD ≈ 0.01% of notional for major pairs
            annual_cost_pct = rt_cost_pips * 12 * 0.01
        else:
            rt_cost_pips = float("nan")
            annual_cost_pct = float("nan")

        # Best direction
        best_carry = max(long_carry_pct, short_carry_pct)
        viable = "YES" if best_carry > annual_cost_pct else "NO"

        print(
            f"  {symbol:<8} {long_carry_pct:>+8.2f}%    {short_carry_pct:>+8.2f}%"
            f"     {rt_cost_pips:.1f} pips    {viable}"
        )
        print(f"           ({desc})")

    print("\n  Note: 'Viable' means best-direction annual carry exceeds estimated")
    print("  annual transaction costs (assuming monthly rebalance).")


def main():
    parser = argparse.ArgumentParser(description="Check carry trade viability per pair")
    parser.add_argument("--api-key", default=os.environ.get("FRED_API_KEY"),
                        help="FRED API key (or set FRED_API_KEY env var)")
    parser.add_argument("--config", default="config/default.yaml",
                        help="Config file for cost parameters")
    args = parser.parse_args()

    if not args.api_key:
        print("Error: FRED API key required. Pass --api-key or set FRED_API_KEY.")
        sys.exit(1)

    print("Fetching central bank rates from FRED...")
    rates = fetch_latest_rates(args.api_key)
    compute_carry(rates, args.config)


if __name__ == "__main__":
    main()
