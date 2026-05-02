# Pre-Registration: ma_crossover

**Status:** Prospective pre-registration (Phase 2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** ma_crossover
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** R3
**Phase:** 2 — operational falsification trials
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md

## Hypothesis (the NULL being tested)

This pre-registration tests whether ma_crossover, archived in Phase 0 as producing
no incremental alpha over the carry family on this universe, nonetheless clears a
minimal positive Sharpe threshold on the held-out OOS-2022 window. The null being
tested is: "ma_crossover generates no exploitable trend-following alpha (OOS Sharpe
< 0.30) on EURUSD, USDJPY, GBPUSD over 2022-01-01 to 2023-12-31." The strategy was
archived on the thesis that carry dominates trend on this universe; this OOS run
either confirms that archival verdict on independent data or produces a surprising
fail-to-falsify that would require re-examination of the archival decision. It is
acknowledged as box-checking per NHT dissent clause (a): the pre-reg exists to LOG
the verdict prospectively, not to generate new information. Thresholds are locked
before any backtest run on OOS-2022 data.

## Mechanism

The strategy computes a 50-period simple moving average (fast) and a 200-period
simple moving average (slow) on the close price of each pair. The signal is +1.0
(max long) when the fast SMA exceeds the slow SMA (golden cross), -1.0 (max short)
when the fast SMA falls below the slow SMA (death cross), and 0.0 during the SMA
warm-up period where either MA is undefined. Signals are generated independently
per pair. Position sizing is applied by the harness using the standard backtester
pipeline (signal shift by entry_delay_bars=1, then sizing and cost model).
Implementation: `src/forex_system/strategies/ma_crossover.py`, class `MACrossoverStrategy`.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire on
the OOS-2022 window (2022-01-01 → 2023-12-31):

- **ma_crossover-T1:** OOS Sharpe < 0.30 (R1 floor; this pre-reg's kill_switch_threshold
  is 0.30, matching the universal R1 floor — no strategy-specific override)
- **ma_crossover-T2:** Max drawdown > 25% (R3 firm anchor)
- **ma_crossover-T3:** Deflated Sharpe (DSR per Bailey & Lopez de Prado 2014) < 0.50
  with N = n_trials_at_spawn (R2 frozen NHT threshold; QD computes via
  src/forex_system/harness/deflated_sharpe.py)
- **ma_crossover-T4:** n_trades < 30 OR n_oos_bars < 252 (R6 sample-size floor)

`kill_switch_threshold: 0.30`

Rationale: The R1 universal floor of 0.30 is appropriate here. ma_crossover is
expected to produce near-zero Sharpe on this carry-dominated universe; setting a
higher bar would be inconsistent with the archived verdict and would create a
goalpost-stuffing risk in the opposite direction. 0.30 is a real but minimal
evidence threshold.

## OOS Sample Discipline

`oos_overlap: false`

The OOS-2022 window (2022-01-01 → 2023-12-31) was selected specifically to avoid
overlap with vol_target_carry (full-history through 2026-04-25) and FRED-carry
Bet #1 (OOS post-2024). The 2022-2023 window pre-dates the Bet #1 BoJ-divergence
regime and post-dates Phase 0 calibration data. The non-overlap declaration for this
window is documented in docs/decisions/oos_window_reservations_2026-05-01.md.

`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Capacity Estimate

N/A — backtest-only OOS evaluation, no position sizing changes from existing code.

## Approval

- Quant Researcher: filed by HoQR authority per docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
- NHT: pre-registration filed prospectively; thresholds locked per nht-frozen-thresholds.yaml
- CTO/CRO: absent for Phase 2 falsification trials per acceptance-criteria
