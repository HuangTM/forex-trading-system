# Pre-Registration: ema_cross (basket member M2)

**Status:** Frozen pre-registration, EXECUTED as trial 50 → result KILL-1 (see Outcome)
**Date frozen:** 2026-06-17 (before any IS look; Principal-Reviewer cycle-2 APPROVED, honest N=50)
**Strategy ID:** ema_cross
**Pair:** EURUSD (1h bars)
**Trial:** 50 — `trial_id: b309935c` (org-wide N=50 at execution: 48 + 2 basket members)
**Canonical frozen spec:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/qr-minimal-trend-basket-v2.yaml`
**Parent CONSENSUS:** `CONSENSUS_signals_rl.md`
**CEO ratification:** path (c) — `.agent-accountability/ratifications/signals-rl:phase1:task1.0.yaml`

## Hypothesis (the NULL being tested)

Test whether a canonical slow-trend signal — the EMA(50)/EMA(200) golden/death cross — produces a
forward-confirmable edge on EURUSD 1h net of a frozen 7.5-pip round-trip cost. **NULL (H0):** the
EMA-cross strategy has expected net-of-cost return ≤ 0; any positive in-sample Sharpe is
multiple-testing/selection (deflated against org-wide N=50). Flagged a-priori STRETCH on the
≥30-trade power floor (slow signal on 1h). Member of the 2-member trend-family basket.

## Mechanism

`src/forex_system/strategies/ema_cross.py` (`EMACrossStrategy`). Always-in: +1 when EMA50 > EMA200
(golden), −1 when EMA50 < EMA200 (death). Canonical golden/death cross (single config,
search-cardinality 1 — no tunable). Uses EMA, not SMA (faithful to the frozen spec); reuses the
causal `ema()` in `src/forex_system/features/indicators.py` (`adjust=False` → no-lookahead). Engine
shifts by `entry_delay_bars=1`. Cost: frozen 7.5-pip round-trip on each reversal. ATR(14)/3×
catastrophic stop (risk rail). Size: vol-targeted, size_multiplier 0.25.

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

HoQR, QR (frozen spec author), CRO (size 0.25), NHT (dissent preserved verbatim), Principal-Reviewer
(cycle-2 APPROVE, N=50 honest), CEO (path c).

## Outcome (recorded post-run — IS only, OOS never burned)

Ran 2026-06-17 (`scripts/trial_basket_is_eval.py`). **Result: KILL-1.**
128 IS trades (power OK — not < 30, contrary to the a-priori STRETCH worry); avg net trade −3.91
pips; CPCV net Sharpe −0.66; **DSR = 0.00 at N=50**; 0/3 regime blocks positive. The slow signal's
per-trade edge (~3.6 pips gross) also fails to clear the 7.5-pip cost. Clean falsification; OOS
holdout never read. With M1 (macd_cross) → **FAMILY_KILL**: the trend family is cost-bound on 1h
EURUSD, mirroring trial-48's mean-reversion result.

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
| IS trades | 128 | 258 (128 long / **130 short** — previously 0 short) |
| avg net trade pips | −3.91 | −0.0283 |
| IS net Sharpe | n/r | −0.1581 |
| win rate | n/r | 0.1473 |
| max drawdown | n/r | 0.0375 |
| CPCV net Sharpe | −0.66 | −0.0402 |
| DSR @ N=50 | 0.00 | 0.0000 |
| Regime blocks positive | 0/3 | 1/3 (2021 +0.154, 2022 −0.129, 2023+24H1 −0.398) |

Gates: POWER pass (258 ≥ 30); **KILL-1 FIRES** (DSR 0.0000 ≤ 0.95); KILL-2 fires (−0.03 ≤ 0);
KILL-2B fires (1/3 < 2 positive). The short side materially improves the economics (avg net
trade −3.91 → −0.03 pips; 2021 block flips positive) but not enough to clear any gate. Family
verdict with M1: **FAMILY_KILL (unchanged)**.
