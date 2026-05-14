"""Saxo Bank REST API client for historical data and account info.

Minimal client focused on fetching OHLCV data. Uses 24-hour developer
tokens from https://www.developer.saxo/openapi/token — no OAuth flow
needed for data download.

For live trading, a proper OAuth2 flow with token rotation is required
(see architecture doc, Phase 3).

REM-6 hardening (CTO D-6.1, D-6.2 / CRO BC-9-N4-COND-2):
  (a) 429 retry wrapper: inspects Retry-After header; exponential backoff
      when absent (max_retries=3, base_delay=2.0s, jitter_factor=0.5).
  (b) Startup jitter: random 0-30s delay in __init__ to distribute N=4
      process session openings across bar-close window.
  (c) Per-process token bucket: threading.Lock-protected, 30 req/min
      (120 total / 4 processes after D-4.1 stagger distributes the burst).
  (d) All request methods deduct from the bucket before issuing.
"""

from __future__ import annotations

import email.utils
import logging
import random
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

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

# (connect_timeout, read_timeout) in seconds. Applied to every HTTP call unless
# the caller explicitly passes its own timeout. Prevents indefinite hangs —
# a Saxo gateway timeout once masqueraded as a 100% drawdown via the balance
# endpoint and silently halted trading.
DEFAULT_HTTP_TIMEOUT = (10, 30)

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

# REM-6 / D-6.1: Per-process token bucket parameters.
# Per-process budget: 30 req/min (120 total / 4 processes; stagger D-4.1 distributes burst).
# CTO KG-D6-1: measure actual req count per bar-close cycle before adjusting.
_DEFAULT_BUCKET_RATE_PER_MIN: int = 30
_DEFAULT_MAX_RETRIES: int = 3
_DEFAULT_BASE_DELAY_SECONDS: float = 2.0
_DEFAULT_JITTER_FACTOR: float = 0.5  # uniform random in [0, base_delay * factor]
_STARTUP_JITTER_MAX_SECONDS: float = 30.0


class _TokenBucket:
    """Thread-safe per-process token bucket for rate limiting.

    Refills at `rate_per_min` tokens per minute (continuous refill model).
    Capacity = rate_per_min (1 minute burst cap).

    All requests must call deduct() before issuing. If tokens are exhausted,
    deduct() sleeps until enough tokens are available.

    Observability: every deduction logs token state at DEBUG level per REM-6
    log-as-decision-trace requirement.
    """

    def __init__(self, rate_per_min: int = _DEFAULT_BUCKET_RATE_PER_MIN) -> None:
        self._rate_per_min = rate_per_min
        self._capacity = float(rate_per_min)
        self._tokens = float(rate_per_min)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def rate_per_min(self) -> int:
        return self._rate_per_min

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill. Call under lock."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        refill = elapsed * (self._rate_per_min / 60.0)
        self._tokens = min(self._capacity, self._tokens + refill)
        self._last_refill = now

    def deduct(self, tokens: float = 1.0) -> None:
        """Deduct tokens from the bucket. Sleeps if insufficient tokens available.

        Logs token state at DEBUG level per REM-6 observability boundary.
        """
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    current_tokens = self._tokens
                    refill_rate = self._rate_per_min
                    last_refill = self._last_refill
                    break
                # Not enough tokens — calculate wait time before releasing lock
                deficit = tokens - self._tokens
                wait_seconds = deficit / (self._rate_per_min / 60.0)

            # Sleep outside the lock to avoid blocking other threads
            time.sleep(wait_seconds)

        logger.debug(
            "token_bucket_deducted current_tokens=%.2f refill_rate_per_min=%d "
            "last_refill_monotonic=%.3f",
            current_tokens,
            refill_rate,
            last_refill,
        )


class SaxoClient:
    """REST client for Saxo Bank OpenAPI.

    Two ways to create:
        1. SaxoClient(token="...") — static token (24h dev tokens)
        2. SaxoClient.from_auth(auth) — managed OAuth with auto-refresh

    REM-6 hardening: startup jitter, per-process token bucket, 429 retry.
    Pass startup_jitter=False in tests to disable the random delay.
    """

    def __init__(
        self,
        token: str,
        live: bool = False,
        startup_jitter: bool = True,
        rate_per_min: int = _DEFAULT_BUCKET_RATE_PER_MIN,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        base_delay_seconds: float = _DEFAULT_BASE_DELAY_SECONDS,
        jitter_factor: float = _DEFAULT_JITTER_FACTOR,
        strategy_id: Optional[str] = None,
    ):
        # REM-6 D-6.1 startup jitter: random 0–30s delay so N=4 strategies
        # launched simultaneously do not all open sessions at the same instant.
        if startup_jitter:
            jitter = random.uniform(0, _STARTUP_JITTER_MAX_SECONDS)
            logger.info(
                "saxo_client_startup_jitter strategy_id=%s jitter_seconds=%.2f",
                strategy_id or "unset",
                jitter,
            )
            time.sleep(jitter)

        self.base_url = LIVE_BASE if live else SIM_BASE
        self._auth = None  # Set by from_auth()
        self._strategy_id = strategy_id or "unset"
        self._max_retries = max_retries
        self._base_delay = base_delay_seconds
        self._jitter_factor = jitter_factor
        self._bucket = _TokenBucket(rate_per_min=rate_per_min)
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

    def _retry_request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> requests.Response:
        """Issue an HTTP request with 429 retry logic and token-bucket deduction.

        REM-6 / D-6.1: deducts one token before each attempt.
        REM-6 / D-6.2: on HTTP 429, respects Retry-After header or applies
        exponential backoff with jitter (base=2.0s, jitter_factor=0.5).

        Observability: every 429 response logs at WARN with full context per
        REM-6 observability boundary.

        Raises requests.exceptions.HTTPError for non-200 non-429 responses
        after the caller calls resp.raise_for_status(), or after max_retries
        are exhausted on 429.
        """
        fn = getattr(self.session, method)
        kwargs.setdefault("timeout", DEFAULT_HTTP_TIMEOUT)

        for attempt in range(1, self._max_retries + 2):  # attempt 1..max_retries+1
            # Deduct from token bucket before each attempt
            self._bucket.deduct()

            resp = fn(url, **kwargs)

            if resp.status_code != 429:
                return resp

            # 429 handling
            retry_after_str = resp.headers.get("Retry-After")
            if retry_after_str is not None:
                try:
                    # Numeric seconds (most common Saxo form)
                    delay = float(retry_after_str)
                except ValueError:
                    # F-007: RFC 7231 §7.1.3 HTTP-date form (e.g. "Wed, 21 Oct 2015 07:28:00 GMT")
                    try:
                        retry_dt = email.utils.parsedate_to_datetime(retry_after_str)
                        delay = max(0.0, (retry_dt - datetime.now(timezone.utc)).total_seconds())
                    except Exception:
                        # Malformed Retry-After: use exponential backoff WITH jitter.
                        # F-007: jitter is REQUIRED here to prevent N-process storm
                        # (without jitter all processes wake at the same computed delay).
                        base = self._base_delay * (2 ** (attempt - 1))
                        jitter = random.uniform(0, base * self._jitter_factor)
                        delay = base + jitter
            else:
                # Exponential backoff with jitter: delay = base * 2^(attempt-1) ± jitter
                base = self._base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, base * self._jitter_factor)
                delay = base + jitter

            logger.warning(
                "saxo_429_rate_limit request_url=%s retry_after_header=%s "
                "retry_attempt=%d/%d delay_seconds=%.2f strategy_id=%s",
                url,
                retry_after_str,
                attempt,
                self._max_retries,
                delay,
                self._strategy_id,
            )

            if attempt > self._max_retries:
                # Exhausted retries — return the 429 response for caller to raise_for_status
                return resp

            time.sleep(delay)

        # Should not be reachable, but satisfies type checker
        return resp  # type: ignore[return-value]

    def _get(self, path: str, **kwargs) -> requests.Response:
        """GET with auto token refresh and 429 retry. REM-6: token bucket deducted."""
        self._ensure_token_fresh()
        return self._retry_request("get", f"{self.base_url}{path}", **kwargs)

    def _post(self, path: str, **kwargs) -> requests.Response:
        """POST with auto token refresh and 429 retry. REM-6: token bucket deducted."""
        self._ensure_token_fresh()
        return self._retry_request("post", f"{self.base_url}{path}", **kwargs)

    def _delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE with auto token refresh and 429 retry. REM-6: token bucket deducted."""
        self._ensure_token_fresh()
        return self._retry_request("delete", f"{self.base_url}{path}", **kwargs)

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
