# HistData M1 → Daily PROVENANCE (AUDUSD, USDCAD, EURGBP)

**Created:** 2026-08-17
**Script:** `scripts/rebuild_daily_from_histdata.py`
**Cache:** `data/raw/histdata_m1/` (raw pair-year ZIPs as downloaded)
**Output:** `data/processed/{AUDUSD,USDCAD,EURGBP}_daily.parquet`

## Why this exists

The daily files for AUDUSD, USDCAD, EURGBP were discovered on 2026-08-17 to be
**synthetic** (fake random-walk data: AUDUSD close 9.47–14.01, USDCAD 2.65–5.01,
EURGBP flat 7.43–7.48 over 16 years). The sanity gate in
`src/forex_system/data/storage.py` had deliberately omitted range bounds for
exactly these 3 pairs. Originals are quarantined at
`data/raw/quarantine_fake_daily_2026-08-17/` (not deleted). Bounds for all three
pairs are now enforced in `storage.py`.

## Source

HistData.com free historical data, "ASCII 1-minute bar quotes", bid-side, EST
(UTC-5) timestamps. Free, no registration.

- Listing: `https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{PAIR}/{YEAR}`
- Download: `POST https://www.histdata.com/get.php` (tk token scraped from listing page)
- Coverage pulled: 2010-01 → 2026-04, one ZIP per pair-year.

## Aggregation

Minute bars shifted EST→UTC (+5h), resampled to UTC calendar days
(open=first, high=max, low=min, close=last), labelled at 00:00 UTC; Sunday
partial sessions dropped; volume = 0.0. This matches the convention of the
repo's 9 real daily files.

## Validation (2026-08-17)

Cross-checked new daily closes against the independent on-disk Dukascopy 1h
series (last-bar-of-day), 1303 overlapping days, 2021–2025:

| Pair | std of close ratio | max deviation |
|---|---|---|
| AUDUSD | 0.055% | 0.429% |
| USDCAD | 0.030% | 0.338% |
| EURGBP | 0.031% | 0.486% |

Comparable to the 9 real pairs (0.06–0.14% std). `tests/data`: 183 passed after
the `storage.py` bounds update (`tests/data/test_storage.py`).

## Regenerate

```
.venv/bin/python scripts/rebuild_daily_from_histdata.py \
    --pairs AUDUSD USDCAD EURGBP --start-year 2010 --end 2026-04-07 \
    --out-dir data/processed --cache-dir data/raw/histdata_m1
```

## Caveat

HistData bid-side M1 vs Dukascopy mid: sources differ at the ~0.05% level
(above). For spread-sensitive work prefer Dukascopy-derived series; this daily
store is used for signal generation, not cost measurement.
