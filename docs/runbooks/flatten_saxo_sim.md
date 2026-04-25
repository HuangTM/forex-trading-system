# Runbook: Flatten Saxo SIM Positions

## When to run
- **Condition:** CEO directive / operational policy requires closing all open SIM positions before halting the trading loop.
- **Evidence:** Kill-switch audit log entry marks state as `FLAT_AND_HALTED`.
- **Decision point:** If any positions remain open after the flatten attempt, operator intervention is required.

## Prerequisites
- Fresh Saxo SIM 24-hour bearer token from https://www.developer.saxo/openapi/token
- Shell with Python 3.11+ in venv activated: `source .venv/bin/activate`
- Working directory: `/Users/huangtm/Projects/forex-trading-system`

## Step 1: Inventory Open Positions

**Command:**
```bash
export SAXO_TOKEN=your_24h_token_here
python scripts/saxo_position_inventory.py
```

OR pass token directly:
```bash
python scripts/saxo_position_inventory.py --token your_24h_token_here
```

**Expected output:**
- Markdown table showing open positions (Pair, Direction, Size, Entry Price, Unrealized PnL, NetPositionId)
- If no positions: "_No open positions._"
- File saved: `data/saxo_positions_2026-04-25.json` (structured inventory)
- File saved: `data/saxo_positions_raw_2026-04-25.json` (raw API response)

**Decision point:**
- **If auth fails** (401/403): token is expired. Fetch a fresh one at https://www.developer.saxo/openapi/token and retry.
- **If no positions found:** Skip to Step 3 (flatten already complete).
- **If positions open:** Proceed to Step 2.

## Step 2: Flatten All Positions

**Dry run first** (recommended):
```bash
python scripts/saxo_flatten_all.py --dry-run --token your_24h_token_here
```

**Expected output (dry run):**
- "[DRY RUN] Placing {close_side} {pair} {size} units..." for each position
- "Confirmation: net=0 confirmed on all N pair(s)." (or "[DRY RUN] Skipping post-flatten confirmation.")
- No orders placed
- Exit code: 0
- File saved: `data/saxo_flatten_2026-04-25.log` (dry-run event log)

**Review dry run output.** If it looks correct, proceed to live flatten.

**Live flatten:**
```bash
python scripts/saxo_flatten_all.py --token your_24h_token_here
```

**Expected output (live):**
```
Authenticating to Saxo SIM...
  Account: <account_key>

Fetching current positions (live re-fetch)...

Positions to flatten: 3
  Placing Sell EURUSD 100000 units (closing LONG @ ~1.0850)
    -> OrderId=XXXXX  approx_fill=1.0849
  Placing Buy GBPUSD 50000 units (closing SHORT @ ~1.2700)
    -> OrderId=XXXXX  approx_fill=1.2701
  [1.2s sleep between orders to respect Saxo's 1 order/sec rate limit]

Waiting 3.0s for fills to settle...
Re-fetching positions to confirm flat...

  Confirmation: net=0 confirmed on all 2 pair(s).

============================================================
  FLATTEN REPORT
============================================================
  Positions before: 2
    ...
  Orders placed: 2
    ...
  Status: net=0 CONFIRMED
  Log: data/saxo_flatten_2026-04-25.log
============================================================
```

**Exit codes:**
- **0:** Success — all positions flattened, net=0 confirmed.
- **1:** Recoverable error (e.g., network glitch, one order failed). **Manual inspection required.** Check `data/saxo_flatten_2026-04-25.log` for which orders failed.
- **2:** Policy violation — one or more positions still open after flatten. **Manual intervention required.** See "If something goes wrong" below.

**Files created:**
- `data/saxo_flatten_2026-04-25.log` (JSON-line event log; append-only)
  - `FLATTEN_START` – operation began
  - `POSITIONS_BEFORE` – snapshot of positions before orders
  - `ORDER_PLACED` or `ORDER_FAILED` – one per order attempt
  - `FLATTEN_COMPLETE` – net=0 confirmed
  - `POLICY_VIOLATION` – if net ≠ 0 or confirmation failed

## Step 3: Post-Flatten Confirmation

After live flatten completes with exit code 0:

1. **Append audit trail** (if not auto-written by flatten script):
   ```bash
   cat >> data/kill_switch_audit.log << 'EOF'
   {"timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "event": "FLATTEN_COMPLETE", "operator": "your_email@example.com", "positions_flattened": 3, "log_file": "data/saxo_flatten_2026-04-25.log"}
   EOF
   ```
   
   (The flatten script already writes to `data/saxo_flatten_2026-04-25.log`; the audit log entry confirms the flatten succeeded from the operator's perspective.)

2. **Verify no lingering positions:**
   ```bash
   python scripts/saxo_position_inventory.py --token your_24h_token_here
   ```
   Expected: "_No open positions._"

3. **Mark system halted** in operational status tracking (out of scope of this runbook; consult your runbook for "Mark Trading Halted").

## If something goes wrong

### Scenario 1: "Confirmation: net=0 could not be confirmed" (exit code 2)

**Cause:** One or more positions remain open after orders were placed.

**Action:**
1. Check the log for which pair(s) are still open:
   ```bash
   grep "POLICY_VIOLATION" data/saxo_flatten_2026-04-25.log
   ```
2. Manually close remaining positions via the Saxo developer portal or re-run flatten with `--dry-run` to identify which orders may have failed.
3. **DO NOT proceed** to Step 3 until net=0 is confirmed.

### Scenario 2: "Order FAILED" errors in live flatten (exit code 1)

**Cause:** One or more orders were rejected by Saxo (e.g., invalid size, invalid pair, insufficient margin, API error).

**Action:**
1. Check which orders failed:
   ```bash
   grep "ORDER_FAILED" data/saxo_flatten_2026-04-25.log
   ```
2. Manually place closing orders for those positions via the Saxo developer portal.
3. Once all positions are manually closed, re-run the flatten script to confirm net=0.

### Scenario 3: "AUTH FAILED" (exit code 1)

**Cause:** Token is expired or invalid.

**Action:**
1. Get a fresh 24-hour SIM token from https://www.developer.saxo/openapi/token
2. Re-run the flatten script with the new token.

### Scenario 4: "Failed to fetch positions after flatten" (exit code 2)

**Cause:** Network error after orders were submitted; cannot confirm if net=0.

**Action:**
1. Wait a few seconds for network to stabilize.
2. Re-run the flatten script (it will re-fetch live positions and confirm the state).
3. If the re-run shows net=0, operation is complete.
4. If positions are still open, escalate to manual close via Saxo portal.

## Success Criteria

After this runbook completes successfully:
- Exit code from `saxo_flatten_all.py` is **0**.
- `data/saxo_flatten_2026-04-25.log` contains `"event": "FLATTEN_COMPLETE"` with `"net_zero_confirmed": true`.
- Running `saxo_position_inventory.py` again shows "_No open positions._"
- `data/kill_switch_audit.log` documents the flatten operation.

## References
- **Saxo SIM Token:** https://www.developer.saxo/openapi/token
- **Saxo OpenAPI Docs:** https://www.developer.saxo/openapi/
- **Kill-switch policy:** See `CONSENSUS.md` and commit `70e3cc7`
