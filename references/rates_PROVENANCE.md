# Interest Rates — Provenance Document

**Dataset:** `data/rates/rate_differentials.parquet` (12 `{PAIR}_diff` columns) and `data/rates/raw/{CCY}.csv`
**Rebuilt:** 2026-08-17
**Generator:** `scripts/download_fred_rates.py` — this script generates ALL 12 `_diff` columns.

---

## Why this file exists (2026-08-17 incident)

The previous on-disk `rate_differentials.parquet` had 12 `_diff` columns but the
in-repo generator only emitted 3 — the 12-pair file's generator was not in the
repo (provenance hole). Separately, `data/rates/raw/JPY.csv` was frozen at
2017-04-01 = 0.3 (FRED `INTDSRJPM193N` is annual and ends early), missing the
entire 2016–2024 negative-rate era and the 2024+ BoJ hikes. The old files were
quarantined to `data/raw/quarantine_fake_daily_2026-08-17/` (not deleted).

## Sources (all fetched 2026-08-17, all percent per annum)

| CCY | FRED series | Description | Freq | Coverage at fetch |
|-----|-------------|-------------|------|-------------------|
| USD | `FEDFUNDS` | Effective Federal Funds Rate | monthly | 1954-07 → 2026-07 |
| EUR | `ECBMRRFR` | ECB Main Refinancing Operations Rate | daily | 1999-01 → 2026-08 |
| JPY | `IRSTCI01JPM156N` | Uncollateralized overnight call rate (OECD Immediate Rates) | monthly | 1985-07 → 2026-06 |
| AUD | `IR3TIB01AUM156N` | 3-month interbank rate | monthly | 1968-01 → 2026-06 |
| NZD | `IR3TIB01NZM156N` | 3-month interbank rate | monthly | 1973-12 → 2026-06 |
| CAD | `IR3TIB01CAM156N` | 3-month interbank rate | monthly | 1956-01 → 2026-06 |
| GBP | manual table in script | BoE Bank Rate decision dates (source: https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp) | event | 2000-01 → 2025-11 |

JPY series choice: `IRSTCI01JPM156N` is the uncollateralized overnight call rate
— the closest FRED series to the BoJ policy target. Verified to capture:
NIRP era (negative from 2016-02, ≈ -0.03 to -0.07 through 2023), 2024-03 hike
(+0.02 → +0.08), 2024-08 hike (+0.227), 2025-02 hike (+0.478), 2026 hikes
(0.841 by 2026-06). The previous candidate `INTDSRJPM193N` (annual) ends too
early and must NOT be used.

Fetch endpoint: `https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES_ID}`
— the public chart-download endpoint; **no FRED API key required**.

## Units and conventions

- Raw CSVs: percent per annum (e.g. 3.63 = 3.63%).
- `rate_differentials.parquet`: business-day index; each `{PAIR}_diff` =
  `(base_rate − quote_rate) / 100` — annualized carry of a LONG position in
  the pair, in decimal. Validated against the pre-incident file: EUR/USD/GBP-only
  pairs are bit-identical (corr = 1.0000); JPY and AUD/NZD/CAD pairs correlate
  ≥ 0.978 (JPY changed by design; AUD/NZD/CAD previously came from an
  undocumented source).

## Known caveat: publication-lag lookahead

Monthly FRED series are timestamped at the first of the reference month but
published weeks later; the generator's plain `ffill` (see comment at the ffill
site in `scripts/download_fred_rates.py`) makes month-M rates visible from
M-01. This is a KNOWN issue — not fixed in the 2026-08-17 pass.

## Regeneration

```bash
python scripts/download_fred_rates.py          # no API key needed
```
