# Saxo Bank OpenAPI Integration Research

Researched: 2026-03-30
Developer Portal: https://www.developer.saxo/

---

## 1. Architecture

REST + WebSocket hybrid -- the same infrastructure powering SaxoTraderGO.

| Component | SIM (Sandbox) | LIVE (Production) |
|-----------|---------------|-------------------|
| REST API | `https://gateway.saxobank.com/sim/openapi` | `https://gateway.saxobank.com/openapi` |
| WebSocket | `wss://streaming.saxobank.com/sim/openapi/streamingws/connect` | `wss://streaming.saxobank.com/openapi/streamingws/connect` |
| OAuth | `https://sim.logonvalidation.net` | `https://live.logonvalidation.net` |

---

## 2. Authentication (OAuth 2.0)

Four flows supported:
1. **Authorization Code Grant** -- server-side web apps (recommended)
2. **Authorization Code Grant with PKCE** -- native apps (recommended for personal bots)
3. **Implicit Flow** -- SPAs (no refresh tokens)
4. **Certificate-Based (JWT)** -- server-to-server, **institutional partners ONLY** (not available to retail)

**Token lifetimes:**
- Access token: **20 minutes**
- Refresh token: **40 minutes** (single-use; each refresh returns a new refresh_token)

**For automated trading as retail client:**
1. Log in manually once via OAuth Code/PKCE flow
2. Keep session alive by refreshing tokens before expiry
3. Store refresh tokens in persistent secure storage

**Quick start:** 24-hour tokens available from the Developer Portal for development/testing.

---

## 3. Key Endpoints for Forex

### Order Placement (`/trade/v2/orders`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/trade/v2/orders` | Place order (with optional related SL/TP) |
| PATCH | `/trade/v2/orders` | Modify existing order |
| DELETE | `/trade/v2/orders/{OrderId}?AccountKey={key}` | Cancel order |
| POST | `/trade/v2/orders/precheck` | Pre-validate before submission |

**Order types:** Market, Limit, Stop, StopLimit, TrailingStop

**Order durations:** DayOrder, GoodTillCancel, GoodTillDate, ImmediateOrCancel, FillOrKill

**Related orders:** Up to 3 orders together (entry + SL + TP). OCO supported.

**Example -- Market order:**
```json
{
  "AccountKey": "YOUR_KEY",
  "Amount": 10000.0,
  "BuySell": "Buy",
  "OrderType": "Market",
  "ManualOrder": false,
  "Uic": 21,
  "AssetType": "FxSpot",
  "OrderDuration": {"DurationType": "DayOrder"}
}
```

**Example -- Entry with stop loss:**
```json
{
  "AccountKey": "YOUR_KEY",
  "Amount": 10000.0,
  "BuySell": "Buy",
  "OrderPrice": 1.06375,
  "OrderType": "Limit",
  "Uic": 21,
  "AssetType": "FxSpot",
  "ManualOrder": false,
  "OrderDuration": {"DurationType": "DayOrder"},
  "Orders": [
    {
      "BuySell": "Sell",
      "OrderPrice": 1.05875,
      "OrderType": "Stop",
      "ManualOrder": false,
      "OrderDuration": {"DurationType": "GoodTillCancel"}
    }
  ]
}
```

### Portfolio

| Endpoint | Purpose |
|----------|---------|
| `GET /port/v1/accounts/me` | Account details |
| `GET /port/v1/balances/me` | Balances (margin, cash, P&L) |
| `GET /port/v1/positions` | Open positions |
| `GET /port/v1/netpositions` | Net positions (aggregated) |
| `GET /port/v1/orders` | Active orders |
| `GET /port/v1/closedpositions` | Closed positions history |
| `GET /port/v1/exposure` | Currency exposure |

### Pricing

| Endpoint | Purpose |
|----------|---------|
| `GET /trade/v1/infoprices?Uic=21&AssetType=FxSpot` | Snapshot price (non-tradable) |
| `POST /trade/v1/prices/subscriptions` | Streaming tradable prices |
| `POST /trade/v1/infoprices/subscriptions` | Streaming info prices |

### Reference Data

| Endpoint | Purpose |
|----------|---------|
| `GET /ref/v1/instruments?Keywords=EURUSD&AssetTypes=FxSpot` | Search instruments |
| `GET /ref/v1/instruments/details?Uics=21&AssetType=FxSpot` | Instrument details |
| `GET /ref/v1/currencypairs` | All currency pairs |

### Historical Data

| Endpoint | Purpose |
|----------|---------|
| `POST /chart/v3/charts/subscriptions` | OHLC chart data |

Returns bid AND ask OHLC. Limited to 1200 datapoints per request. Horizons: 1min to 1month. Forex data back to ~2002.

---

## 4. WebSocket Streaming

**Connect:**
```
GET wss://streaming.saxobank.com/sim/openapi/streamingws/connect?contextId=MyCtx
Authorization: BEARER {token}
```

**Subscribe (via REST):**
```json
POST /trade/v1/prices/subscriptions
{
  "Arguments": {"AssetType": "FxSpot", "Uic": 21},
  "ContextId": "MyCtx",
  "ReferenceId": "eurusd_price",
  "RefreshRate": 1000
}
```

**Binary message format:**

| Offset | Size | Content |
|--------|------|---------|
| 0 | 8 bytes | Message ID (64-bit LE) |
| 8 | 2 bytes | Reserved |
| 10 | 1 byte | Reference ID length (N) |
| 11 | N bytes | Reference ID (ASCII) |
| 11+N | 1 byte | Format (0=JSON, 1=Protobuf) |
| 12+N | 4 bytes | Payload size (M) |
| 16+N | M bytes | Payload data |

**Delta compression:** Only changed fields sent after initial snapshot. Must maintain full state locally.

**Control messages:** `_heartbeat`, `_disconnect` (re-auth needed), `_resetsubscriptions` (recreate listed subs).

**Token refresh on stream:** `PUT /streamingws/authorize?contextid={id}` with new bearer token before expiry.

**Reconnection:** Pass `messageid=<lastMsgId>` as query param to resume.

---

## 5. Rate Limits

| Dimension | Limit |
|-----------|-------|
| Application total per day | 10,000,000 |
| Per session per service group | 120/minute |
| Orders per session | 1/second |

HTTP 429 when exceeded. Duplicate orders within 15 seconds rejected (409) unless unique `x-request-id` header.

---

## 6. Python Libraries

### hootnot/saxo_openapi (most mature)
- **GitHub:** https://github.com/hootnot/saxo_openapi (104 stars)
- **Install:** `pip install saxo_openapi requests`
- Covers: trading, portfolio, reference data, chart, account history
- Includes Jupyter notebook examples
- Caveat: originally Python 3.4-3.7 on PyPI, may need testing with 3.11+

### toanalien/saxo-openapi-client-python
- **GitHub:** https://github.com/toanalien/saxo-openapi-client-python
- **Install:** `pip install saxo-apy`
- OAuth code flow with auto SSO callback, async token refresh, WebSocket decoding
- Modern stack (pydantic, httpx, websockets)
- Personal project, not production-grade

### nohikomiso/saxo-openapi
- **GitHub:** https://github.com/nohikomiso/saxo-openapi
- 275+ JSON schemas, AI-first design, updated March 2026

### SaxoBank/openapi-samples-js (official)
- **GitHub:** https://github.com/SaxoBank/openapi-samples-js (66 stars)
- Official Saxo Bank repo with vanilla JS samples

### IOITI/WATA (reference architecture)
- **GitHub:** https://github.com/IOITI/WATA
- Full automated trading system for Saxo Bank
- Microservice arch: RabbitMQ, DuckDB, Telegram notifications

---

## 7. Sandbox / Simulation

- **Free signup:** https://developer.saxobank.com/sim/login/
- Simulated $100,000 virtual balance
- 24-hour tokens from Developer Portal (no OAuth implementation needed for testing)
- Must test in SIM before going live
- Some reporting/market data unavailable in SIM

---

## 8. Going Live

Requirements:
1. Create and test at least one SIM application
2. Fill out evaluation form (from Developer Portal)
3. Link SIM account to LIVE account
4. Accept disclaimers confirming adequate SIM testing
5. Approval usually automatic within minutes

LIVE apps are extensively monitored -- irregular behavior flagged.

---

## 9. Common Forex UIC Codes

| Pair | Uic |
|------|-----|
| EURUSD | 21 |
| GBPUSD | 31 |
| USDJPY | 41 |

Always verify via `/ref/v1/instruments` -- UICs may vary.

---

## 10. Key Pitfalls

1. **ManualOrder field required** on every order -- set `false` for automated trading
2. **Duplicate protection:** identical orders within 15s rejected; use unique `x-request-id`
3. **Delta compression:** WebSocket sends only changed fields; maintain full state from snapshot
4. **Token rotation:** refresh tokens are single-use; each refresh returns a new pair
5. **SIM/LIVE keys not portable:** separate app credentials for each environment
6. **1 order/second limit:** batch execution logic accordingly
7. **Certificate auth not available to retail:** must use OAuth with refresh rotation
8. **Free forex market data:** streaming FX prices included, no additional subscription needed
9. **Order precheck:** use `/trade/v2/orders/precheck` to validate margin/pricing before placing
10. **Tradable vs info prices:** use `/trade/v1/prices/subscriptions` for order-capable prices

---

## 11. Python Integration Example (Direct REST)

```python
import requests

BASE_URL = "https://gateway.saxobank.com/sim/openapi"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Get account key
resp = requests.get(f"{BASE_URL}/port/v1/accounts/me", headers=HEADERS)
account_key = resp.json()["Data"][0]["AccountKey"]

# Search for instrument
resp = requests.get(
    f"{BASE_URL}/ref/v1/instruments",
    headers=HEADERS,
    params={"Keywords": "EURUSD", "AssetTypes": "FxSpot"}
)

# Get current price
resp = requests.get(
    f"{BASE_URL}/trade/v1/infoprices",
    headers=HEADERS,
    params={"Uic": 21, "AssetType": "FxSpot",
            "FieldGroups": "DisplayAndFormat,InstrumentPriceDetails,Quote"}
)

# Place limit order with stop loss
order = {
    "AccountKey": account_key,
    "Amount": 10000,
    "AssetType": "FxSpot",
    "BuySell": "Buy",
    "OrderType": "Limit",
    "OrderPrice": 1.0500,
    "ManualOrder": False,
    "Uic": 21,
    "OrderDuration": {"DurationType": "GoodTillCancel"},
    "Orders": [{
        "BuySell": "Sell",
        "OrderPrice": 1.0450,
        "OrderType": "Stop",
        "ManualOrder": False,
        "OrderDuration": {"DurationType": "GoodTillCancel"}
    }]
}
resp = requests.post(f"{BASE_URL}/trade/v2/orders", headers=HEADERS, json=order)
```

---

## 12. WebSocket Streaming Example (Python)

```python
import websocket
import struct
import json

def parse_saxo_message(data):
    """Parse Saxo binary WebSocket message format."""
    offset = 0
    messages = []
    while offset < len(data):
        msg_id = struct.unpack_from('<Q', data, offset)[0]
        offset += 10  # 8 bytes msg_id + 2 reserved
        ref_id_len = data[offset]
        offset += 1
        ref_id = data[offset:offset+ref_id_len].decode('ascii')
        offset += ref_id_len
        payload_format = data[offset]
        offset += 1
        payload_size = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        payload = data[offset:offset+payload_size]
        offset += payload_size
        if payload_format == 0:
            messages.append({
                'msg_id': msg_id,
                'ref_id': ref_id,
                'data': json.loads(payload.decode('utf-8'))
            })
    return messages

def on_message(ws, message):
    if isinstance(message, bytes):
        for msg in parse_saxo_message(message):
            if msg['ref_id'].startswith('_'):
                print(f"Control: {msg['ref_id']}")
            else:
                print(f"Price: {msg['data']}")

ws = websocket.WebSocketApp(
    f"wss://streaming.saxobank.com/sim/openapi/streamingws/connect?contextId=myctx",
    header=[f"Authorization: Bearer {TOKEN}"],
    on_message=on_message,
)
ws.run_forever()
```

---

## 13. Integration Architecture for Our System

```
┌─────────────────────────────────────────────────────┐
│                  Forex Trading System                │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
│  │ Strategy │──>│ Signal   │──>│ Order Manager  │  │
│  │ Engine   │   │ Generator│   │ (rate limiting,│  │
│  └──────────┘   └──────────┘   │  dedup, retry) │  │
│                                └───────┬────────┘  │
│                                        │           │
│  ┌──────────────────────────────┐      │           │
│  │ DataProvider                 │      │           │
│  │  - REST: /chart (OHLCV)     │      │           │
│  │  - WS: /prices (real-time)  │      │           │
│  └──────────┬───────────────────┘      │           │
│             │                          │           │
│  ┌──────────┴──────────────────────────┴────────┐  │
│  │ SaxoClient                                   │  │
│  │  - OAuth token management (auto-refresh)     │  │
│  │  - REST client (requests/httpx)              │  │
│  │  - WebSocket client (binary parser)          │  │
│  │  - SIM/LIVE environment switching            │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         │
                    Saxo OpenAPI
```

### Recommended build order:
1. **SaxoClient** -- OAuth + REST + WebSocket wrapper
2. **DataProvider adapter** -- fetch historical OHLCV, stream real-time prices
3. **Order Manager** -- place/modify/cancel with rate limiting and dedup
4. **Position Tracker** -- sync positions via REST + streaming
5. **Strategy Bridge** -- connect existing Strategy ABC to live execution
