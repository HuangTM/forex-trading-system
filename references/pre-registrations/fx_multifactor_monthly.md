# Pre-Registration: currency-level carry + value + momentum, monthly

**Status:** Pre-registered 2026-10-26, committed BEFORE `scripts/run_fx_multifactor.py`
computes any return. Only signals and weights were built beforehand (shape/sanity check:
weights sum to 0, gross 2, no NaN; carry and value weights for 2024-06 inspected).
**Runner:** `scripts/run_fx_multifactor.py`
kill_switch_threshold: 0.0
(composite net Sharpe ≤ 0 on the full or post-2012 window = FAIL; see verdict rule)
**Honest-N:** one trial → N = 35 (34 + this). Ledger row to be appended after the run.
**Owner context (2026-10-26):** chosen as the single next research bet; if it does not
pass, the research programme pauses rather than adding trials.

## Hypothesis and sources

The three best-documented FX factor premia, combined across currencies, earn a positive
risk-adjusted return net of retail costs: carry (Lustig, Roussanov & Verdelhan 2011;
Menkhoff et al. 2012 JF), cross-sectional momentum (Menkhoff, Sarno, Schmeling &
Schrimpf 2012 JFE) and value (Asness, Moskowitz & Pedersen 2013 JF; Menkhoff et al.
2017 RFS). Definitions follow these papers; nothing is fitted to our data.

## Universe, data, sample

- 7 currencies: USD, EUR, JPY, GBP, AUD, NZD, CAD (positions vs USD via the 6 USD pairs).
- Spot: Fed H.10 noon NY rates, month-end (`data/factors/raw/DEX*.csv`; cross-checked
  against the repo's HistData/processed daily closes 2002–2026: median |dev| 0.10–0.15%).
- Value: BIS real broad effective exchange rates (`data/factors/raw/RB*BIS.csv`).
- Rates: `data/rates/raw/{CCY}.csv` (same audited series as the rest of the repo; EUR
  gap fixed in `05e41c1`), monthly average of the daily-filled series.
- **Return months 2001-01 → 2026-09** (309 months, ~25.75 yrs). The start is the first
  month for which every input exists (rates begin 2000-01; momentum needs 11 months).
- This repo never tested a currency-level factor model. Published samples end ~2010–11,
  so 2012+ is post-publication; that split is pre-registered.

## Signals (formed at the end of month t, held during month t+1)

All inputs are as of month t−1 or earlier (one-month publication lag for rates and REER).
- **Carry:** short rate level, month t−1.
- **Value:** −(log REER(t−1) − mean log REER over months t−66 … t−54), i.e. minus the
  real appreciation versus 4.5–5.5 years ago (cheap = long).
- **Momentum:** sum of monthly excess returns (log spot change vs USD + rate
  differential/12) over months t−11 … t−1 (12-month, skipping the latest month).
- **Weights per factor:** cross-sectional ranks (average ties), demeaned, scaled to
  sum|w| = 2 ($1 long / $1 short); USD weight implied (weights sum to 0).
- **Composite (primary):** equal average of the three factor weight vectors.

## Returns and costs

Month t+1 return = Σ_c w_c · [log spot change of c vs USD + (i_c − i_USD)/12].
- **base (primary):** per traded unit, half the Dukascopy 2021–25 median spread of the
  c/USD pair + 0.4 pip slippage, on Σ|Δw| across the 6 foreign currencies; plus a
  financing markup of 0.5%/yr on Σ|w| (both sides pay).
- **high:** spreads and slippage ×2, markup 1.0%/yr (2000s retail spreads were wider).
- **gross:** none.

## Statistics and verdict (fixed)

Monthly returns; Sharpe ×√12; t = mean/SE; stationary block bootstrap p (mean block
6 months, 10,000 reps, seed 0); DSR via `harness.dsr.compute_dsr`, N = 35,
periods_per_year 12. Reported for full, pre-2012 and post-2012 windows.

**Verdict on composite × base:**
- **PASS:** full-window t ≥ 1.65 AND DSR ≥ 0.95 AND post-2012 Sharpe > 0.
- **FAIL:** full-window Sharpe ≤ 0, OR post-2012 Sharpe ≤ 0 (decayed after publication).
- **INCONCLUSIVE:** otherwise.

Secondary, not used for the verdict: each factor alone, the high-cost and gross cells,
per-year returns, factor return correlations.

## Known limits

Policy/3-month rates stand in for forward points; month-end noon NY fixes; no
intramonth risk management; G7 only (7 currencies — far less breadth than the
papers' 15–48), so the cross-section is thin and results noisier than published.
