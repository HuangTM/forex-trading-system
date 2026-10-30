# Pre-Registration: carry with a speculative-crowding overlay (CFTC COT), monthly

**Status:** Pre-registered 2026-10-30, approved by the owner. Committed BEFORE
`scripts/run_fx_cot_carry.py` computes any return; this commit is the freeze. Done
beforehand, with no spot or return data read:
- data-availability checks on the COT files;
- the signal-only overlap check `references/cot_signal_overlap_2026-10-29.md`;
- `run_fx_cot_carry.py --smoke`, which builds signals and weights without loading spot:
  - 309 formation months, weights sum to 0, no NaN;
  - overlay foreign gross equals carry's to 7e-16;
  - 0.99 crowded legs per month on average;
  - COT availability spot-checked at the shutdown windows and on Friday month-ends.

**Runner:** `scripts/run_fx_cot_carry.py`. Before the freeze it may only build signals
and weights (`--smoke`).
kill_switch_threshold: 0.0
(the overlay's mean monthly excess over plain carry ≤ 0, on the full or the post-2012
window, is a FAIL; see the verdict table)
**Honest-N:** one trial, so N = 36 (35 + this). The ledger row is appended after the run.
**Owner context:**
- The programme paused after trial 35 (FX multifactor, INCONCLUSIVE).
- On 2026-10-29 the owner chose to pre-register this single bet after the signal-only check.
- A devil's-advocate review of the first design is reflected below.
- Pause rule: if this does not PASS, the programme stays paused.

## Hypothesis and sources

Carry trades crash when speculators are crowded into them: speculator net positioning,
relative to a currency's own history, predicts currency crash risk (Brunnermeier, Nagel
& Pedersen 2008, NBER Macro Annual).

**Prediction:** cutting the carry position in a currency where speculative positioning is
unusually extended in the same direction improves carry's return, net of retail costs,
at the same gross exposure.

This is a test of whether positioning adds information to carry. It is not a test of
whether positioning alone earns a premium.

## Universe, data, sample

Universe, spot, rates, sample, return definition and costs are **identical** to
`fx_multifactor_monthly.md`:
- 7 currencies (USD, EUR, JPY, GBP, AUD, NZD, CAD);
- Fed H.10 month-end noon fixes;
- `data/rates/raw`;
- return months 2001-01 → 2026-09, 309 months.

One change from that pre-registration: rates enter with the measured publication lags
(`download_fred_rates.PUBLICATION_LAG_MONTHS`, i.e. `run_fx_multifactor.py --pit-rates`),
so AUD carry uses month t−2. This removes the one-month AUD lookahead found on 2026-10-29.

**Positioning:** `data/factors/raw/cot_legacy_fx.csv`, built by
`scripts/fetch_cot_legacy_fx.py`.
- Source: CFTC legacy futures-only COT, CME contracts joined by contract code.
- Definition: net_oi = (noncommercial long − noncommercial short) / open interest, per
  foreign currency, positions vs USD.
- USD has no contract and gets no positioning score.

## COT availability rule (fixed)

Weights are formed at noon NY on the last business day F of month t. A report with
as-of date A (a Tuesday) is usable only if **A + 6 calendar days < F**. Normal release is
the Friday after A at 15:30 ET, after the noon fix, or the Monday after when Friday is a
holiday. The 6-day rule therefore never uses a report published on or after F.

Government-shutdown overrides replace the rule:
- **2013-10-01 … 2013-11-07:** frozen at as-of 2013-09-24. The delayed reports were
  released on a rolling basis from 2013-10-25, and the normal schedule resumed
  2013-11-08 (CFTC releases 6738-13, 6745-13). Their individual release dates are not
  used.
- **2018-12-22 … 2019-03-07:** frozen at as-of 2018-12-18, the last report published
  before the shutdown (published 2018-12-21). The catch-up releases ran until the
  report published 2019-03-08 (CFTC release 7864-19).
- **2025-10-01 … 2025-12-28:** a report is usable only if its release date in the CFTC
  notice of 2025-12-09 is before F:

  | as-of | released | as-of | released |
  |---|---|---|---|
  | 09/30 | 11/19 | 11/18 | 12/12 |
  | 10/07 | 11/21 | 11/25 | 12/15 |
  | 10/14 | 11/25 | 12/02 | 12/17 |
  | 10/21 | 12/02 | 12/09 | 12/19 |
  | 10/28 | 12/05 | 12/16 | 12/23 |
  | 11/04 | 12/09 | 12/23 | 12/29 |
  | 11/10 | 12/10 | | |

  Reports before 2025-09-30 follow the normal rule.

Outside these windows, if the latest usable report for a currency is more than 45 days
old, that currency gets no crowding adjustment (z = 0). The same applies when a currency
has fewer than 78 usable weekly reports in its window. In practice this covers NZD before
2005 and isolated AUD gaps. No back-filling.

## Signals (formed at the end of month t, held during month t+1)

**1. Carry weights** w⁰ are exactly the multifactor carry factor:
- input: the short-rate level per currency, with the publication lags above;
- cross-sectional ranks over the 7 currencies (average ties), demeaned;
- scaled to sum|w| = 2.

**2. Crowding z-score** per foreign currency c, from the usable reports:
- z_c = (net_oi_latest − mean) / std over the latest 156 usable weekly reports (3 years);
- this needs at least 78 reports, otherwise z_c = 0.

**3. Crowding in the direction of the carry position:** s_c = z_c · sign(w⁰_c).
- If s_c > 0, speculators are extended the same way the carry portfolio is positioned.

**4. Overlay:**
- **Cut:** w¹_c = 0.5 · w⁰_c if s_c > 1.0; otherwise w¹_c = w⁰_c. A position is halved
  when crowding is more than one standard deviation above its own 3-year mean.
- **Rescale:** scale the six foreign w¹_c by a common factor so that Σ_foreign|w¹| =
  Σ_foreign|w⁰|. This keeps the same gross exposure, reallocated away from crowded legs.
- **No crowded legs:** if no currency is crowded, w¹ = w⁰.
- **All legs crowded:** if all non-zero legs are crowded, the rescale restores w⁰
  exactly.

The cut fraction (0.5), the threshold (1.0 sd) and the window (156 weeks) are fixed
here, not tuned. No other variant is run.

Returns: month t+1 return = Σ_foreign w_c · [log spot change of c vs USD + (i_c − i_USD)/12],
the same as the multifactor test. Costs:
- **base (primary)** and **high** as in `fx_multifactor_monthly.md`, charged on each
  portfolio's own Σ|Δw|;
- **gross** has no costs.

## Statistics and verdict (fixed)

**Primary statistic:** the paired monthly difference d_t = r_overlay,t − r_carry,t, both at
base cost, same months.
- Test: one-sided on mean(d) > 0.
- p-value: stationary block bootstrap (mean block 6 months, 10,000 reps, seed 0).
- Also reported: the t-statistic and the information ratio, mean(d)/sd(d) × √12.

**Overlay statistics:** Sharpe ×√12, t, bootstrap p, and DSR via
`harness.dsr.compute_dsr` with N = 36 and periods_per_year 12. Each is reported for the
full window, pre-2012 and post-2012 (post = 2012-01 onward).

**Verdict on overlay × base:**

| Outcome | Condition |
|---|---|
| **PASS** | paired p ≤ 0.05 AND post-2012 mean(d) > 0 AND overlay full DSR ≥ 0.95 AND overlay post-2012 Sharpe > 0 |
| **FAIL** | full mean(d) ≤ 0, OR post-2012 mean(d) ≤ 0, OR overlay full Sharpe ≤ 0 |
| **INCONCLUSIVE — improves carry** | not PASS, not FAIL, paired p ≤ 0.05 (adds to carry but not a deployable edge at N = 36) |
| **INCONCLUSIVE** | otherwise |

Expected hurdle, computed with `compute_dsr` at T = 309, N = 36, and stated here so it
cannot be reinterpreted: DSR ≥ 0.95 needs a full-window overlay Sharpe of about 0.75
(normal returns) to 0.80 (skew −1, excess kurtosis 5). Plain carry was 0.38 in trial 35
with point-in-time rates. A PASS is therefore unlikely; the main value of the trial is the
paired answer.

**Secondary, not used for the verdict:**
- the high-cost and gross cells;
- plain carry's own statistics with point-in-time rates;
- per-year d;
- the number of crowded legs per month;
- turnover of overlay vs carry;
- the largest carry drawdowns (2008, and others) with and without the overlay.

**After the verdict:** months after 2026-09 are monitored as an implementation check
only. A monthly strategy cannot be confirmed in any useful forward horizon: at an
information ratio of 0.3–0.5, reaching t ≈ 1.65 takes more than 10 years. Forward data
never changes this verdict.

## Known limits

- The 2001–2006 sample overlaps Brunnermeier/Nagel/Pedersen (1986–2006), and the carry
  return path for 2001–2026 was already seen in trial 35. Pre-2012 is therefore in
  practice in-sample; post-2012 carries the evidence.
- Legacy "noncommercial" is a coarse proxy for speculators. CME futures are a small slice
  of FX turnover.
- G7 only, so the cross-section is thin.
- NZD has no positioning before about 2005.
- Policy and 3-month rates stand in for forward points.
- The 2013 and 2018–19 shutdown windows use a conservative freeze rather than the exact
  catch-up release dates, which could not be verified individually.
