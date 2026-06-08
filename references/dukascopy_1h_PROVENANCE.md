# Dukascopy 1h Bars — Provenance Document

**Dataset:** `data/processed/{PAIR}_1h.parquet`
**Frequency:** 1-hour OHLCV bars
**Source:** Dukascopy Bank SA — free historical tick datafeed
**Built:** 2026-06-07

---

## Source

**Provider:** Dukascopy Bank SA  
**Endpoint:** `https://datafeed.dukascopy.com/datafeed/{INSTRUMENT}/{YYYY}/{MM_0based}/{DD}/{HH}h_ticks.bi5`  
**Format:** LZMA-compressed binary (bi5), 20 bytes per tick  
**Tick structure:** `(ms_from_hour_start: uint32 BE, ask*scale: uint32 BE, bid*scale: uint32 BE, ask_vol: float32 BE, bid_vol: float32 BE)`  
**Cost:** Free. No registration required. The endpoint is publicly accessible.  
**License:** Dukascopy data described as free for research/download use. No commercial redistribution restriction found; the firm should review Dukascopy's Terms of Service before publishing any strategy derived from this data.  
**CTO red-team reference:** `.fintech-org/artifacts/2026-06-07T-data-capability/cto-source-redteam.yaml`

---

## Timezone Convention — VERIFIED UTC

**Dukascopy timestamps are UTC.** This was verified by two independent checks:

### Check 1: Weekend Gap (Structural)

FX markets close at approximately Friday 21:00 UTC and reopen at approximately Sunday 21:00 UTC. A test fetch of EURUSD tick data for Friday 2024-01-05 confirmed:

- Hour bar 21 (21:00 UTC): `HTTP 200`, body = 12,190 bytes, 2,848 ticks — market activity present
- Hour bar 22 (22:00 UTC): `HTTP 200`, body = 0 bytes — empty, market closed

This proves the hour index in the URL is UTC. If the source were in e.g. EST (UTC-5), the 22h bar would be noisy and the correct close would appear elsewhere.

### Check 2: NFP Release (Event-Anchored)

NFP (US Non-Farm Payrolls) releases at **13:30:00 UTC** on the first Friday of each month.  
For 2024-01-05 (first Friday of January 2024), the 13h bar (13:00–14:00 UTC) was fetched:

- Body: 76,541 bytes  
- Total ticks: 16,196  
- Ticks after the 30-minute mark (after 13:30 UTC): **12,690** — heavy burst, consistent with NFP release  

This confirms the 1h bar boundaries are correctly anchored to UTC hours, not any DST-affected or venue-local timezone.

**The QRB-6 confirmatory trial was voided by a timezone bug. UTC correctness is a HARD GATE for this dataset. Both checks above were verified live on 2026-06-07.**

---

## Volume Column — Tick-Proxy Caveat

**`volume` = sum of Dukascopy ask-side lot volume across ticks in each 1h bar.**

This is **NOT exchange volume**. FX spot has no central exchange. The volume column is a venue-specific liquidity proxy reflecting Dukascopy's own platform feed. Any intraday strategy that uses volume must acknowledge this limitation explicitly. The proxy is useful for relative liquidity comparison (higher in active sessions, near zero on weekends) but should not be interpreted as market-wide notional.

This caveat is consistent with the CTO red-team document:
> "Real FX spot has NO central exchange volume. Any 'volume' column from a broker or data vendor is that venue's tick-count or notional traded — a proxy, not exchange volume."

---

## Price Scaling

| Pair type | Raw integer divisor | Example |
|-----------|--------------------|---------| 
| Non-JPY (EURUSD, GBPUSD, AUDUSD, USDCAD, NZDUSD, EURGBP) | 1e5 | ask_raw=110370 → 1.10370 |
| JPY pairs (USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY) | 1e3 | ask_raw=147500 → 147.500 |

The output OHLCV uses mid-price: `mid = (ask + bid) / 2 / divisor`.

---

## Ingest Script

```
python scripts/ingest_dukascopy_1h.py \
    --pair EURUSD \
    --start 2024-01-01 \
    --end 2024-02-01 \
    --out data/processed/EURUSD_1h.parquet
```

**Arguments:**
- `--pair`: Instrument code (one of the 12 target pairs)
- `--start`: Start date UTC, inclusive, ISO format YYYY-MM-DD
- `--end`: End date UTC, exclusive, ISO format YYYY-MM-DD
- `--out`: Output parquet path

**Output schema:** matches existing firm convention:
- Index: `datetime` — tz-aware UTC `DatetimeIndex`
- Columns: `open`, `high`, `low`, `close`, `volume` — all `float64`
- Sorted, no duplicates, monotonic

---

## Proof Pull Result

**Pair:** EURUSD  
**Window:** 2024-01-01 → 2024-02-01  
**Calendar hours:** 744  
**Bars written:** 530  
**Empty hours (weekends/closed):** 214  
**Network reachable:** YES  
**Elapsed wall-clock:** 10 minutes 47 seconds  
**Output file:** `data/processed/EURUSD_1h.parquet`  
**Output shape:** (530, 5)  
**UTC range:** `2024-01-01 22:00:00+00:00 → 2024-01-31 23:00:00+00:00`  
**Weekend gap check:** PASSED (0 Saturday bars, last Friday bar = 21:00 UTC)  
**Schema validation:** PASSED  
**Parquet round-trip:** PASSED  
**Date:** 2026-06-07  

Sample bar (2024-01-02 00:00 UTC): open=1.10368, high=1.10384, low=1.10344, close=1.10383, volume=4519.4

> **Note on network access:** The Python `requests` library times out against `datafeed.dukascopy.com` in the development environment due to TLS/keep-alive behaviour. The ingest script uses a raw TLS socket (`ssl` + `socket` stdlib) which works correctly. Users in standard network environments may substitute `requests.get(url).content` for simpler code.

**Full QD implementation artifact:** `.fintech-org/artifacts/2026-06-07T-data-capability/qd-dukascopy-ingest.yaml`

---

## Scale-Up Plan — Full 12-Pair Backfill

### Volume Estimate

| Component | Value |
|-----------|-------|
| Pairs | 12 |
| History depth target | ~2010-01-01 → 2026-05-01 (~16.3 years) |
| Calendar hours per year | 8,760 |
| Active FX hours (≈70% of calendar — no weekends, no dead nights) | ~6,100/year |
| Total 1h bars estimated | 12 × 16.3 × 6,100 ≈ **1.19 million bars** |
| Compressed bi5 per hour | ~5–80 KB (active hours), 0 (weekends) |
| Estimated total download | ~20–50 GB compressed |
| Decompressed parquet size (12 pairs) | ~200–500 MB (parquet is columnar + compressed) |

### Time Estimate

Sequential fetch rate in this environment: ~4–8 hours per year of history per pair (raw TLS socket, single-threaded). For 12 pairs × 16 years: approximately **3–6 days** of continuous sequential fetching. This can be parallelized by pair (12 parallel processes → ~6–12 hours), subject to Dukascopy rate-limiting (undocumented; add exponential backoff if 429s appear).

### Scale-Up Command

```bash
# Full backfill — run pair by pair, one at a time (safe / no rate-limit risk)
for PAIR in AUDJPY AUDUSD CADJPY EURGBP EURJPY EURUSD GBPJPY GBPUSD NZDJPY NZDUSD USDCAD USDJPY; do
    echo "Starting $PAIR..."
    python3 scripts/ingest_dukascopy_1h.py \
        --pair $PAIR \
        --start 2010-01-01 \
        --end 2026-05-01 \
        --out data/processed/${PAIR}_1h.parquet \
        --log-level INFO
    echo "Done: $PAIR"
done

# Or parallel (12 processes, faster but higher load):
for PAIR in AUDJPY AUDUSD CADJPY EURGBP EURJPY EURUSD GBPJPY GBPUSD NZDJPY NZDUSD USDCAD USDJPY; do
    python3 scripts/ingest_dukascopy_1h.py \
        --pair $PAIR --start 2010-01-01 --end 2026-05-01 \
        --out data/processed/${PAIR}_1h.parquet &
done
wait
```

### Pair Coverage Caveat

CADJPY and NZDJPY start dates on Dukascopy are unverified (CTO red-team: "assumed, not individually confirmed"). Run the script with `--start 2005-01-01` for these pairs on a short window first to confirm availability. If a pair returns zero bars before 2010, adjust `--start` accordingly and document in this file.

---

## Data Quality Gates (Mandatory Before Strategy Use)

1. **UTC spot-check PASSES** — both checks above confirmed on 2026-06-07
2. **Weekend gap test green** — `pytest tests/data/test_dukascopy_ingest.py -q`
3. **OHLCV schema valid** — `validate_1h_schema()` passes (no missing cols, UTC tz, monotonic, no dupes)
4. **Bar count plausible** — for any pair/window, count actual bars vs expected weekday hours; flag if <50%
5. **No-lookahead extension** — `test_intraday_no_lookahead` must be written and green before any intraday strategy enters NHT pre-registration (per CTO conditions)

---

## Caveats and Limitations

1. **Broker-venue data, not ECN composite.** Dukascopy data reflects their own platform's bid/ask feed. Spreads and liquidity may differ from Saxo execution. Cross-check spreads against `config/default.yaml` pair spread parameters before using for cost-model calibration.

2. **Intraday data does NOT validate daily strategies.** Acquiring 1h bars opens a new design space requiring QRB-0 restart. The CTO honest caveat (red-team YAML) applies in full: "An intraday signal is a DIFFERENT strategy with its own per-event Sharpe, its own design phase, its own NHT pre-registration, and its own OOS test."

3. **Network access method.** The raw TLS socket approach works in the current environment. If Dukascopy changes their TLS configuration, update the socket-level HTTP/1.1 headers in `_fetch_bi5()`.

4. **No retry on empty body.** An empty `b""` response is treated as a valid empty hour (weekend/closed). Transient network errors that return empty bodies will silently produce missing bars. For production ingest, add a content-length cross-check against the `Content-Length` HTTP header.
