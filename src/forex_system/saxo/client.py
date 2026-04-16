"""Saxo Bank REST API client for historical data and account info.

Minimal client focused on fetching OHLCV data. Uses 24-hour developer
tokens from https://www.developer.saxo/openapi/token — no OAuth flow
needed for data download.

For live trading, a proper OAuth2 flow with token rotation is required
(see architecture doc, Phase 3).
"""

from __future__ import annotations

import time

import requests

# Saxo environments
SIM_BASE = "https://gateway.saxobank.com/sim/openapi"
LIVE_BASE = "https://gateway.saxobank.com/openapi"

# UICs for major forex pairs — verified against SIM /ref/v1/instruments 2026-04-15.
# SIM and LIVE environments use different UICs. These are SIM values.
# If switching to LIVE, re-verify via /ref/v1/instruments?Keywords=PAIR&AssetTypes=FxSpot
PAIR_UICS = {
    "EURUSD": 21,
    "GBPUSD": 31,
    "USDJPY": 42,
    "AUDUSD": 4,
    "USDCHF": 39,
    "NZDUSD": 37,
    "USDCAD": 38,
    "EURGBP": 17,
    "EURJPY": 18,
    "GBPJPY": 26,
    "AUDJPY": 2,
    "NZDJPY": 36,
    "CADJPY": 6,
}

# Horizon codes: minutes per bar
HORIZONS = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "daily": 1440,
    "weekly": 10080,
}


class SaxoClient:
    """REST client for Saxo Bank OpenAPI.

    Two ways to create:
        1. SaxoClient(token="...") — static token (24h dev tokens)
        2. SaxoClient.from_auth(auth) — managed OAuth with auto-refresh
    """

    def __init__(self, token: str, live: bool = False):
        self.base_url = LIVE_BASE if live else SIM_BASE
        self._auth = None  # Set by from_auth()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    @classmethod
    def from_auth(cls, auth) -> "SaxoClient":
        """Create a client with managed OAuth token refresh.

        The auth object's ensure_valid() is called before each request
        to keep the token fresh.
        """
        token = auth.ensure_valid()
        client = cls(token=token, live=auth.live)
        client._auth = auth
        return client

    def _ensure_token_fresh(self) -> None:
        """Refresh the bearer token if using managed auth."""
        if self._auth is not None:
            token = self._auth.ensure_valid()
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path: str, **kwargs) -> requests.Response:
        """GET with auto token refresh."""
        self._ensure_token_fresh()
        return self.session.get(f"{self.base_url}{path}", **kwargs)

    def _post(self, path: str, **kwargs) -> requests.Response:
        """POST with auto token refresh."""
        self._ensure_token_fresh()
        return self.session.post(f"{self.base_url}{path}", **kwargs)

    def _delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE with auto token refresh."""
        self._ensure_token_fresh()
        return self.session.delete(f"{self.base_url}{path}", **kwargs)

    def get_chart_data(
        self,
        pair: str,
        horizon: str = "daily",
        count: int = 1200,
        start: str | None = None,
        end: str | None = None,
    ) -> dict:
        """Fetch OHLCV chart data.

        Args:
            pair: Currency pair (e.g., "EURUSD")
            horizon: Timeframe key from HORIZONS
            count: Number of bars (max 1200 per request)
            start: Start date as ISO string (optional)
            end: End date as ISO string (optional)

        Returns:
            Raw API response dict with Data array.
        """
        uic = PAIR_UICS.get(pair.upper())
        if uic is None:
            raise ValueError(f"Unknown pair: {pair}. Known: {list(PAIR_UICS.keys())}")

        horizon_minutes = HORIZONS.get(horizon)
        if horizon_minutes is None:
            raise ValueError(f"Unknown horizon: {horizon}. Known: {list(HORIZONS.keys())}")

        params = {
            "AssetType": "FxSpot",
            "Uic": uic,
            "Horizon": horizon_minutes,
            "Count": min(count, 1200),
        }
        if start:
            params["Mode"] = "From"
            # Ensure ISO 8601 format with timezone
            params["Time"] = start if "T" in start else f"{start}T00:00:00Z"
        if end and not start:
            params["Mode"] = "UpTo"
            params["Time"] = end if "T" in end else f"{end}T00:00:00Z"

        resp = self._get("/chart/v3/charts", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_chart_data_range(
        self,
        pair: str,
        horizon: str,
        start: str,
        end: str,
        sleep_between: float = 0.6,
    ) -> list[dict]:
        """Fetch chart data across a date range, paginating as needed.

        Saxo limits to 1200 bars per request. This method fetches
        in chunks, advancing the start time after each batch.

        Args:
            pair, horizon: as in get_chart_data
            start: ISO date string (e.g., "2016-01-01")
            end: ISO date string
            sleep_between: seconds between requests (rate limiting)

        Returns:
            List of OHLC bar dicts.
        """
        all_bars = []
        current_start = start

        while True:
            data = self.get_chart_data(
                pair, horizon, count=1200, start=current_start,
            )

            bars = data.get("Data", [])
            if not bars:
                break

            all_bars.extend(bars)

            # Check if we've reached the end
            last_time = bars[-1].get("Time", "")
            if last_time >= end or len(bars) < 1200:
                break

            # Advance start to last bar's time
            current_start = last_time
            time.sleep(sleep_between)

        # Filter to requested range
        all_bars = [b for b in all_bars if b.get("Time", "") <= end]

        return all_bars

    def get_account_info(self) -> dict:
        """Get account details."""
        resp = self._get("/port/v1/accounts/me")
        resp.raise_for_status()
        return resp.json()

    def get_balance(self, account_key: str) -> dict:
        """Get account balances (margin, cash, P&L).

        Uses ClientKey param — AccountKey returns 400 on SIM.
        For retail accounts, ClientKey == AccountKey.
        """
        resp = self._get("/port/v1/balances", params={"ClientKey": account_key})
        resp.raise_for_status()
        return resp.json()

    def get_positions(self, client_key: str | None = None) -> dict:
        """Get open positions."""
        params = {}
        if client_key:
            params["ClientKey"] = client_key
        resp = self._get("/port/v1/positions", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_instrument_details(self, uic: int) -> dict:
        """Get instrument details including current conditions."""
        resp = self._get(
            "/ref/v1/instruments/details",
            params={"Uics": uic, "AssetTypes": "FxSpot",
                    "FieldGroups": "OrderSetting,TradingSessions"},
        )
        resp.raise_for_status()
        return resp.json()

    def get_info_price(self, pair: str) -> dict:
        """Get current price snapshot."""
        uic = PAIR_UICS.get(pair.upper())
        if uic is None:
            raise ValueError(f"Unknown pair: {pair}")

        resp = self._get(
            "/trade/v1/infoprices",
            params={
                "Uic": uic,
                "AssetType": "FxSpot",
                "FieldGroups": "DisplayAndFormat,InstrumentPriceDetails,Quote",
            },
        )
        resp.raise_for_status()
        return resp.json()

    # === Order Management ===

    def get_account_key(self) -> str:
        """Get the account key needed for order placement."""
        info = self.get_account_info()
        accounts = info.get("Data", [])
        if not accounts:
            raise RuntimeError("No accounts found")
        return accounts[0]["AccountKey"]

    def place_order(
        self,
        pair: str,
        buy_sell: str,
        amount: float,
        order_type: str = "Market",
        order_price: float | None = None,
        duration: str = "DayOrder",
        account_key: str | None = None,
    ) -> dict:
        """Place an order on Saxo.

        Args:
            pair: Currency pair.
            buy_sell: "Buy" or "Sell".
            amount: Position size in base currency units.
            order_type: "Market", "Limit", "Stop".
            order_price: Required for Limit/Stop orders.
            duration: "DayOrder", "GoodTillCancel", etc.
            account_key: Saxo account key (fetched if not provided).

        Returns:
            Order response dict with OrderId.
        """
        uic = PAIR_UICS.get(pair.upper())
        if uic is None:
            raise ValueError(f"Unknown pair: {pair}")

        if account_key is None:
            account_key = self.get_account_key()

        order = {
            "AccountKey": account_key,
            "Uic": uic,
            "AssetType": "FxSpot",
            "BuySell": buy_sell,
            "Amount": amount,
            "OrderType": order_type,
            "ManualOrder": False,
            "OrderDuration": {"DurationType": duration},
        }
        if order_price is not None and order_type != "Market":
            order["OrderPrice"] = order_price

        resp = self._post("/trade/v2/orders", json=order)
        resp.raise_for_status()
        return resp.json()

    def get_open_orders(self) -> list[dict]:
        """Get all open/pending orders."""
        resp = self._get("/port/v1/orders")
        resp.raise_for_status()
        return resp.json().get("Data", [])

    def cancel_order(self, order_id: str, account_key: str | None = None) -> None:
        """Cancel a pending order."""
        if account_key is None:
            account_key = self.get_account_key()
        resp = self._delete(
            f"/trade/v2/orders/{order_id}",
            params={"AccountKey": account_key},
        )
        resp.raise_for_status()

    def get_net_positions(self, client_key: str | None = None) -> list[dict]:
        """Get net positions (aggregated by instrument)."""
        if client_key is None:
            client_key = self.get_account_key()  # AccountKey == ClientKey for retail
        resp = self._get("/port/v1/netpositions", params={"ClientKey": client_key})
        resp.raise_for_status()
        return resp.json().get("Data", [])

    def close_position(self, position_id: str, account_key: str | None = None) -> dict:
        """Close a specific position by placing an opposing market order.

        Note: Saxo doesn't have a direct "close position" endpoint.
        We need to find the position details and place an opposing order.
        """
        if account_key is None:
            account_key = self.get_account_key()

        # Get position details
        positions = self.get_net_positions()
        target = None
        for pos in positions:
            if str(pos.get("NetPositionId", "")) == str(position_id):
                target = pos
                break

        if target is None:
            raise ValueError(f"Position {position_id} not found")

        base = target.get("NetPositionBase", {})
        amount = abs(base.get("Amount", 0))
        uic = base.get("Uic")
        current_side = "Buy" if base.get("Amount", 0) > 0 else "Sell"
        close_side = "Sell" if current_side == "Buy" else "Buy"

        return self.place_order(
            pair=self._uic_to_pair(uic),
            buy_sell=close_side,
            amount=amount,
            order_type="Market",
            account_key=account_key,
        )

    def close_all_positions(self, account_key: str | None = None) -> list[dict]:
        """Close all open positions."""
        if account_key is None:
            account_key = self.get_account_key()

        positions = self.get_net_positions()
        results = []
        for pos in positions:
            base = pos.get("NetPositionBase", {})
            amount = abs(base.get("Amount", 0))
            if amount == 0:
                continue
            try:
                result = self.close_position(
                    str(pos.get("NetPositionId", "")),
                    account_key=account_key,
                )
                results.append(result)
                time.sleep(1.1)  # Respect 1 order/sec rate limit
            except Exception as e:
                results.append({"error": str(e), "position_id": pos.get("NetPositionId")})
        return results

    def _uic_to_pair(self, uic: int) -> str:
        """Reverse lookup: UIC -> pair name."""
        for pair, u in PAIR_UICS.items():
            if u == uic:
                return pair
        raise ValueError(f"Unknown UIC: {uic}")
