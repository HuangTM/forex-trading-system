# Pre-Registration: FX fix-reversal (Krohn, Mueller & Whelan 2024) on 1h data

**Status:** Pre-registered 2026-10-25, committed BEFORE `scripts/run_fix_reversal.py` is
run on real data beyond a smoke run (2 pairs, first 2,000 bars, no metrics printed).
**Runner:** `scripts/run_fix_reversal.py`
kill_switch_threshold: 0.0
(net Sharpe ≤ 0 on the primary cell = FAIL; see verdict rule)
**Honest-N:** one trial → N = 34 (ledger 32 + carry retest 1 + this 1). Ledger row left
to the owner, as for the carry retest.

## Source and why this is a fair out-of-sample test

Krohn, Mueller & Whelan, "Foreign Exchange Fixings and Returns around the Clock",
Journal of Finance 79(1) 2024 (Bank of Canada WP 2021-48). Sample 1999–2019, G9 vs USD.
Finding: USD appreciates before the Tokyo (9:55 Tokyo), ECB (14:15 CET) and London
(16:00 London) fixes and depreciates after — ≈2.5 bp/day each side; reversal
portfolios positive on ~55–60% of days. The paper also reports (Sec. V.B) decay:
Tokyo reversal ≤5%/yr since 2013 with a first negative year in 2018; Europe reversal
below 5%/yr in 2018–19; and (Sec. V.E) that profits shrink sharply under bid-ask costs.

**Rules come from the paper, not from our data.** Our 1h data (Dukascopy, 2021-01 →
2025-12) is entirely after the paper's sample and was never used for this idea.

## Strategy (paper Section V.E, times in New York / ET)

| Window (ET) | USD position |
|---|---|
| 17:00 → Tokyo fix | long USD |
| Tokyo fix → 02:00 | short USD |
| 02:00 → ECB fix | long USD |
| ECB fix → 11:00 (London fix) | flat |
| 11:00 → 17:00 | short USD |

1h approximations (fixed now): Tokyo boundary = bar starting 01:00 UTC (fix at 00:55
UTC, Japan has no DST); ECB boundary = 08:00 ET (paper 08:15). A bar belongs to the
window containing its START time. Verified on a winter and a summer day.

- **Universe:** the 6 USD pairs we have at 1h: EURUSD, GBPUSD, AUDUSD, NZDUSD,
  USDJPY, USDCAD (paper's CHF/NOK/SEK unavailable). Crosses excluded (no USD leg).
- **Portfolio (primary):** equal-weight "dollar portfolio" of the 6 pairs, 1 unit
  each, schedule = Tokyo + Europe combined (4 round trips/day as in the paper).
- **Returns:** bar log return close-to-close; across a gap (weekend) the bar's own
  open → close. Daily = ET trading day 17:00 → 17:00. Annualized by observed
  trading days per year.
- **Costs (primary = CD0, the firm's intraday convention):** per side = half of the
  executing bar's `spread_median_pips` + 0.4 pip; charged on every unit of position
  change. Also reported: gross, spread-only. Real per-hour spreads are used, so the
  17:00 ET rollover bar (EURUSD median 1.9 pips vs 0.3 elsewhere) is charged as is.
- **Swap:** ignored (flip occurs at the 17:00 ET rollover boundary; acknowledged).

**Secondary (reported, not used for the verdict):** Tokyo-only; Europe-only;
`combined_avoid_rollover` (flat during the 17:00 ET bar); per-pair; gross bp/day per
paper window vs the paper's ~2.5 bp.

## Statistics and verdict (fixed)

t = mean/SE of daily returns; stationary block bootstrap p (20-day blocks, 10,000
reps, seed 0); DSR via `harness.dsr.compute_dsr`, N = 34.

- **Gross pattern replicates** (descriptive): primary schedule, gross, t ≥ 1.65.
- **Verdict on primary (combined × CD0):** PASS if t ≥ 1.65 AND DSR ≥ 0.95;
  FAIL if Sharpe ≤ 0; otherwise INCONCLUSIVE.

## Known limits

1h bars cannot place the ECB boundary exactly; no swap; Dukascopy spreads are one
ECN venue's; 5 years of data, so a true net Sharpe below ~0.75 cannot reach t = 1.65.
