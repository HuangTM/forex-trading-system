# Pre-Registration: carry_fred retest under corrected swap accounting

**Status:** Pre-registered 2026-10-25, committed BEFORE `scripts/run_carry_retest.py`
is run on either evaluation window (a smoke run on 2 pairs, 2010–2011, only checks
that the script executes).
**Parent:** `references/pre-registrations/carry_fred.md` (CONSENSUS Bet #1)
**Runner:** `scripts/run_carry_retest.py`
kill_switch_threshold: 0.30
(= CF-T1 primary kill level, unchanged from the parent pre-registration)
**Honest-N:** this retest counts as ONE additional trial → N = 33 (ledger 32 + 1)
for deflation. Ledger row to be appended by the owner (not done here: the 3
honest-N sacred tests are already failing on 30 vs 32, governance decision #1).

---

## Why

The 2026-08-23 "PASS again, OOS Sharpe 0.6582" re-run is not a valid measurement:

1. **Swap was booked as a lump sum at trade exit** in discrete mode
   (`engine._close_position`). carry_fred makes 1–11 trades per pair in 16 years,
   so years of carry landed on single days (e.g. NZDJPY +16% on 2026-04-06, the
   forced close at data end). Through 2026-04-03 the same run gives ~0.43–0.45.
   **Fixed** (this branch): swap accrues per elapsed calendar day; per-trade totals
   are unchanged (verified to ~1e-7 USD on 16 backtests).
2. **Swap rates were static constants** for 2010–2026 while policy differentials
   moved 0 → 5%. **Fixed** (opt-in): `RateDifferentialSwapCostModel`.
3. **The code does not implement the pre-registered selection rule.** Step 3 says
   top quintile long / bottom quintile short / middle neutral; the code clips a
   z-score and the discrete engine trades its sign, so all 12 legs are always
   on. Added `selection="quintile"`; default unchanged.
4. **CF-T8 was never evaluated.** As-shipped IS Sharpe was 0.00 (< 0.40), so the
   original binding trigger set FIRED; the addendum reported T1–T4 only.

## Disclosure — what has already been seen (this is NOT a blind test of 2010–2026)

An adversarial review on 2026-10-25 rebuilt the strategy OUTSIDE the engine
(constant notional, daily accrual at the raw differential) and reported, IS / OOS:
as-shipped clip rule 0.20 / 1.04; minus 0.5% markup 0.08 / 0.94; quintile 0.11 /
1.37; sign(diff) 0.20 / 1.22; currency-level top2/bottom2 0.29 / 0.72; equal-weight
long 6 JPY crosses 0.35 / 1.21. Those numbers are known to the author of this
pre-registration. **Part A is therefore a re-evaluation of the original binding
triggers under corrected accounting, not new evidence.** Only Part B is blind.

## Fixed specification (identical for every cell; nothing tuned)

- Universe: the 12 pre-registered pairs. Strategy: `CarryFREDStrategy`,
  `rank_normalize=True`, `min_differential=0.001`; engine `run_backtest`,
  discrete mode, `entry_delay_bars=1`, `initial_capital=1e6`, default ATR sizing;
  costs from `config/carry_fred.yaml`.
- **Variants:** V1 `selection="clip"` (as shipped) — **primary**;
  V2 `selection="quintile"` (step 3 as worded); V3 `rank_normalize=False`
  (sign fallback, step 4; used for CF-T7).
- **Swap models:** C1 static config swap (daily accrual); **C2 rate-differential
  swap, markup 0.5%/yr per side — primary**; C3 markup 0.0%; C4 markup 1.0%;
  C2x2 = C2 with spread/slippage/commission AND markup doubled (CF-T6).
- **Portfolio:** vol-weighted exactly as `run_carry_fred_all_pairs.py`
  (weight = min(0.10 / IS realized vol of the pair's equity curve, 5), normalized)
  — **primary for Part A**; equal-weighted reported alongside.
- **Statistics:** Sharpe = mean/std × √252 of daily portfolio returns; t = SR·√years;
  stationary block bootstrap p (20-day blocks, 10,000 reps, seed 0, H0 = demeaned
  returns); DSR via `harness.dsr.compute_dsr` with n_trials = 33.
- **Comparator (descriptive only):** equal-weight long of the 6 JPY crosses
  (signal ≡ +1) through the same engine, C2 swap.

## Part A — 2010–2026 re-evaluation of Bet #1

- Price data truncated at **2026-04-06** (last date all 12 pairs share; avoids the
  3-pair tail flagged in review). IS = start → 2023-04-24; OOS = 2023-04-25 → 2026-04-06.
- Binding triggers evaluated exactly as worded in `carry_fred.md` on V1×C2:
  CF-T1 OOS vol-weighted SR < 0.30; CF-T2 > 8 of 12 negative OOS pair Sharpes;
  CF-T3 any pair's differential constant through OOS; CF-T4 OOS max DD > 40%;
  CF-T5 one-sample t-test of the 12 OOS pair Sharpes, two-sided p > 0.10;
  CF-T6 IS SR under C2x2 < 0.20; CF-T7 (V1 − V3) OOS SR > 0.30 (wording is
  internally inconsistent — reported as a number, flagged, not used for the verdict);
  CF-T8 IS vol-weighted SR < 0.40.
- **Verdict rule:** Bet #1 = PASS only if none of CF-T1..T6, T8 fires on V1×C2.
  Otherwise FAIL, naming the triggers. CF-T9 is a live monitor, out of scope.

## Part B — pre-2010 blind holdout (conditional)

Runs only if BOTH hold: (1) HistData daily rebuilt for ≥ 9 of 12 pairs covering
2003-01 → 2009-12, stored outside `data/processed`; (2) the EUR rate gap is fixed —
FRED `ECBMRRFR` (fixed-rate tenders) has no values 2000-06-09 → 2008-12-10 (the ECB
ran variable-rate tenders), so the on-disk EUR rate is frozen at 4.25% for 8.5 years.
Fill: corridor midpoint (ECBDFR + ECBMLFR) / 2, valid while the corridor was
symmetric; validated against ECBMRRFR where both exist. If either condition fails,
Part B is reported as NOT RUN.

- Window: 2003-01-01 → 2009-12-31 (pairs without data in a sub-period are flat).
- Equal-weighted portfolio (vol weights would need post-holdout data), V1×C2 primary.
- **Verdict:** CONFIRMED if SR ≥ 0.30 AND one-sided t ≥ 1.65; REFUTED if SR ≤ 0;
  otherwise INCONCLUSIVE. Max DD (2008) reported regardless.

## What this cannot show

No margin/liquidation simulation; policy rates stand in for tom-next rates; ACT/365
for all currencies; FEDFUNDS publication-lag lookahead in the signal (a 1-month lag
moved the as-shipped OOS SR 0.66 → 0.75, i.e. not inflating); retail swap markups
vary by broker and account (C3/C4 bracket them).

---

## Addendum 1 (2026-10-25, before Part B was run) — holdout data and cleaning

Part A ran first (result committed separately). Part B data condition: HistData
whole-year M1 for 2002–2009 → daily (`data/holdout_pre2010/`, gitignored). Full
2003-01 → 2009-12 coverage for 9 of 12 pairs (condition met). CADJPY starts
2007-03-19, NZDJPY 2006-09-04, NZDUSD 2005-08-12 (HistData has nothing earlier);
they are flat in the portfolio before their first bar. EUR rate gap fixed in
`05e41c1`; Part A was re-run on the fixed rate file and is byte-identical.

Bad ticks found by inspecting data only (no strategy output was computed):
AUDJPY 2005-05-02..05-13 closes of 1.2–2.3 (real ≈ 81–88); EURGBP 2004-03-26 close
0.6000 (real ≈ 0.67); bad intraday highs/lows on 7 bars in AUDJPY/AUDUSD/EURGBP/
EURJPY/NZDUSD. Cleaning rule fixed now (`clean_holdout` in the runner):

1. Cross close > 2% from the close implied by its two USD legs → bar dropped.
   (Crosses match their legs with median |dev| 0.013–0.042%; this flags exactly
   the 11 bars above and nothing else.)
2. Any close > 20% from its centered 21-bar median → dropped (flags none beyond 1).
3. Open/high/low > 20% from that median → open := previous close, high/low :=
   max/min(open, close).

A spike-and-revert rule was considered and rejected: it flagged real crash days
(CADJPY/NZDJPY 2008-11-12). Verdict rule, cells and window are unchanged.
