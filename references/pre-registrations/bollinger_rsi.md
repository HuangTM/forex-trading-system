# Pre-Registration: bollinger_rsi

**Status:** Prospective pre-registration (Phase 2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** bollinger_rsi
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** R5
**Phase:** 2 — operational falsification trials
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md

## Hypothesis (the NULL being tested)

This pre-registration tests whether the bollinger_rsi mean-reversion strategy
achieves a positive Sharpe threshold on the held-out OOS-2022 window. Unlike
ma_crossover and momentum, this trial is partially novel: mean-reversion on
forex (exploiting overshoots relative to Bollinger Bands confirmed by RSI extremes)
has a credible mechanism on major pairs and may not be obviously dominated by the
carry family. The null being tested is: "bollinger_rsi generates no exploitable
mean-reversion alpha (OOS Sharpe < 0.30) on EURUSD, USDJPY, GBPUSD over 2022-01-01
to 2023-12-31." A fail-to-falsify (Sharpe >= 0.30) would be a genuine finding
requiring further investigation — it would indicate the archival decision was based
on relative dominance by carry, not absence of absolute alpha. Thresholds are locked
before any backtest run on OOS-2022 data.

## Mechanism

The strategy generates buy signals when the close price falls below the lower
Bollinger Band (default: 20-period, 2-sigma) AND the RSI (default: 14-period)
is below 30 (oversold), and sell signals when close exceeds the upper Bollinger Band
AND RSI is above 70 (overbought). Signals are forward-filled: the position is held
until the opposite signal fires (Bollinger + RSI threshold on the other side). This
produces a regime-aware mean-reversion pattern — it only fades moves that are both
statistically extreme (BB breach) and momentum-confirmed extreme (RSI reading). When
neither condition fires, the signal holds the prior position. Implementation:
`src/forex_system/strategies/bollinger_rsi.py`, class `BollingerRSIStrategy`.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire on
the OOS-2022 window (2022-01-01 → 2023-12-31):

- **bollinger_rsi-T1:** OOS Sharpe < 0.30 (R1 floor; this pre-reg's kill_switch_threshold
  is 0.30 — HoQR has no directional view strong enough to override the R1 floor for
  a partially novel strategy)
- **bollinger_rsi-T2:** Max drawdown > 25% (R3 firm anchor)
- **bollinger_rsi-T3:** Deflated Sharpe (DSR per Bailey & Lopez de Prado 2014) < 0.50
  with N = n_trials_at_spawn (R2 frozen NHT threshold; QD computes via
  src/forex_system/harness/deflated_sharpe.py)
- **bollinger_rsi-T4:** n_trades < 30 OR n_oos_bars < 252 (R6 sample-size floor)
- **bollinger_rsi-T5:** If OOS Sharpe >= 0.30 (fail-to-falsify), escalate to HoQR
  for review before any paper evaluation — a positive result here is unexpected and
  requires an arch-thesis update, not automatic promotion.

`kill_switch_threshold: 0.30`

Rationale: 0.30 is the R1 universal floor. The mean-reversion thesis has ambiguous
expected Sharpe on this universe (0.15–0.35 range per HoQR DSR awareness, Wave 2).
Setting a higher bar would prejudge the result; setting a lower bar would be
meaningless. If the strategy is genuinely not noise, 0.30 is the minimum bar to
distinguish real alpha from estimation noise at 252 OOS bars.

## OOS Sample Discipline

`oos_overlap: false`

The OOS-2022 window (2022-01-01 → 2023-12-31) was selected specifically to avoid
overlap with vol_target_carry (full-history through 2026-04-25) and FRED-carry
Bet #1 (OOS post-2024). Non-overlap declaration documented in
docs/decisions/oos_window_reservations_2026-05-01.md.

`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Capacity Estimate

N/A — backtest-only OOS evaluation, no position sizing changes from existing code.

## Approval

- Quant Researcher: filed by HoQR authority per docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
- NHT: pre-registration filed prospectively; thresholds locked per nht-frozen-thresholds.yaml
- CTO/CRO: absent for Phase 2 falsification trials per acceptance-criteria
