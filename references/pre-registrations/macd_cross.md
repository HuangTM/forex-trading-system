# Pre-Registration: macd_cross (basket member M1)

**Status:** Frozen pre-registration, EXECUTED as trial 49 → result KILL-1 (see Outcome)
**Date frozen:** 2026-06-17 (before any IS look; Principal-Reviewer cycle-2 APPROVED, honest N=50)
**Strategy ID:** macd_cross
**Pair:** EURUSD (1h bars)
**Trial:** 49 — `trial_id: 82497d05` (org-wide N=50 at execution: 48 + 2 basket members)
**Canonical frozen spec:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/qr-minimal-trend-basket-v2.yaml`
**Parent CONSENSUS:** `CONSENSUS_signals_rl.md`
**CEO ratification:** path (c) — `.agent-accountability/ratifications/signals-rl:phase1:task1.0.yaml`

## Hypothesis (the NULL being tested)

Test whether a canonical trend signal — the MACD(12,26,9) signal-line cross — produces a
forward-confirmable edge on EURUSD 1h net of a frozen 7.5-pip round-trip cost. **NULL (H0):** the
MACD-cross trend strategy has expected net-of-cost return ≤ 0; any positive in-sample Sharpe is
multiple-testing/selection (deflated against org-wide N=50). This is a member of a 2-member
trend-family basket whose purpose is honest negative evidence on whether TREND (as opposed to the
already-killed mean-reversion of trial 48) also fails on cost at 1h.

## Mechanism

`src/forex_system/strategies/macd_cross.py` (`MACDCrossStrategy`). Always-in: +1 when MACD line
> signal line, −1 when <. MACD(12,26,9) = Appel canonical (single config, search-cardinality 1 —
no tunable threshold/confirmation/time-stop, so it does not inflate the deflation N). Reuses the
causal `macd()` in `src/forex_system/features/indicators.py` (EMA-based, `adjust=False`, no forward
operator → no-lookahead). Engine shifts by `entry_delay_bars=1`. Cost: frozen 7.5-pip round-trip
(`src/forex_system/costs/static_roundtrip.py`) on each reversal. ATR(14)/3× catastrophic stop
(non-alpha-selecting risk rail). Size: vol-targeted, size_multiplier 0.25.

## Falsification Criteria

Member is FALSIFIED if ANY fires (pre-OOS, IS only; OOS burned only if all pre-OOS gates pass):
- **POWER:** < 30 qualifying IS trades → INSUFFICIENT-POWER.
- **KILL-1 (DSR):** IS net-of-cost Deflated Sharpe ≤ 0.95 at org-wide N=50 → KILL.
- **KILL-2 (cost):** avg net trade ≤ 0 pips after the 7.5-pip round-trip → KILL.
- **REGIME:** net Sharpe negative in all pre-declared year-blocks → KILL.
- **(OOS, if reached) KILL-5:** OOS net annualized Sharpe < 0.30 → KILL.

`kill_switch_threshold: 0.30` (OOS net annualized Sharpe floor)

## OOS Sample Discipline

`oos_overlap: false`
`is_window: 2021-01-03 .. 2024-05-31`
`seam_embargo: 2024-06 (discarded)`
`oos_window_start: 2024-07-01`
`oos_window_end: 2025-12-31`
`oos_one_shot: true`
`cpcv: 8 groups, k=2; purge 240 bars (10 trading days) / embargo 120 bars (5 trading days), FIXED pre-declared`
`dsr_N: 50`

## Approval

HoQR (prioritization, basket capped), QR (frozen spec author), CRO (size 0.25), NHT (dissent on
multiplicity — preserved verbatim in CONSENSUS), Principal-Reviewer (cycle-2 APPROVE, N=50 honest),
CEO (path c).

## Outcome (recorded post-run — IS only, OOS never burned)

Ran 2026-06-17 (`scripts/trial_basket_is_eval.py`). **Result: KILL-1.**
1,672 IS trades; avg net trade −2.11 pips; CPCV net Sharpe −2.75; **DSR = 0.00 at N=50**; 0/3 regime
blocks positive. Gross fade capture ≈ +5.4 pips/trade but below the 7.5-pip cost floor → cost-churn
(MACD crosses roughly every ~13 bars). Clean falsification; OOS holdout never read. With M2
(ema_cross) → **FAMILY_KILL**: the trend family is cost-bound on 1h EURUSD, mirroring trial-48's
mean-reversion result.

## Addendum 2026-08-17 — original outcome VOID (wiring bug), re-run with fix

**The 2026-06-17 outcome above was computed LONG-ONLY and is invalid.** The pre-reg specifies
always-in long/short (+1/−1, see "Mechanism"), but `scripts/trial_basket_is_eval.py` never
forwarded `allow_shorts=True` to `run_backtest`, so all short signals were silently floored to
flat. Fixed in the working tree 2026-08-17: `allow_shorts=True` is now passed on all three
`run_backtest` call sites (full-IS, CPCV folds, regime blocks), and the engine's short-swap
branch no longer crashes at zero swap. Re-run 2026-08-17, IS-only (2021-01-03..2024-05-31),
frozen constants unchanged (N=50, CPCV 8/2 purge 240/embargo 120, 7.5-pip RT, size_mult 0.25);
OOS holdout never touched.

**Re-run result: KILL-1 again (verdict UNCHANGED).**

| Metric | Old (long-only, INVALID) | New (long/short, fixed) |
|---|---|---|
| IS trades | 1,672 | 3,340 (1,670 long / **1,670 short** — previously 0 short) |
| avg net trade pips | −2.11 | −1.7393 |
| IS net Sharpe | n/r | −4.0521 |
| win rate | n/r | 0.1811 |
| max drawdown | n/r | 0.3020 |
| CPCV net Sharpe | −2.75 | −3.2198 |
| DSR @ N=50 | 0.00 | 0.0000 |
| Regime blocks positive | 0/3 | 0/3 (2021 −4.95, 2022 −4.12, 2023+24H1 −3.79) |

Gates: POWER pass; **KILL-1 FIRES** (DSR 0.0000 ≤ 0.95); KILL-2 fires (−1.74 ≤ 0); KILL-2B
fires (0/3 positive). With shorts enabled the strategy trades roughly 2× as often and loses on
both sides — the cost-bound falsification is *stronger*, not weaker. Family verdict with M2:
**FAMILY_KILL (unchanged)**.
