# Pre-Registration: momentum

**Status:** Prospective pre-registration (Phase 2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** momentum
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** R4
**Phase:** 2 — operational falsification trials
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md

## Hypothesis (the NULL being tested)

This pre-registration tests whether the momentum strategy, archived in Phase 0 as
producing no incremental alpha over the carry family on this universe, clears a
minimal positive Sharpe threshold on the held-out OOS-2022 window. The null being
tested is: "momentum (rate-of-change signal) generates no exploitable price-momentum
alpha (OOS Sharpe < 0.30) on EURUSD, USDJPY, GBPUSD over 2022-01-01 to 2023-12-31."
The strategy was archived on the thesis that carry dominates on this universe; the
OOS-2022 run confirms or challenges that verdict on independent data. Acknowledged as
box-checking per NHT dissent clause (a): thresholds are locked before any backtest
run on OOS-2022 data so that the verdict is prospective, not post-hoc.

## Mechanism

The strategy computes a rate-of-change (momentum) indicator over a configurable
lookback period (default: `momentum_14`, i.e., 14-bar ROC). The signal is the
momentum indicator value clipped to [-1.0, +1.0] — positive values produce long
signals, negative values produce short signals, and values near zero are attenuated
toward flat. The indicator is computed as the percentage change over the lookback
window using the features registry (`src/forex_system/features/registry.py`), parsed
as `momentum_{period}`. Implementation: `src/forex_system/strategies/momentum.py`,
class `MomentumStrategy`. Signals are shifted by entry_delay_bars=1 by the harness
before execution.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire on
the OOS-2022 window (2022-01-01 → 2023-12-31):

- **momentum-T1:** OOS Sharpe < 0.30 (R1 floor; this pre-reg's kill_switch_threshold
  is 0.30, matching the universal R1 floor — no strategy-specific override)
- **momentum-T2:** Max drawdown > 25% (R3 firm anchor)
- **momentum-T3:** Deflated Sharpe (DSR per Bailey & Lopez de Prado 2014) < 0.50
  with N = n_trials_at_spawn (R2 frozen NHT threshold; QD computes via
  src/forex_system/harness/deflated_sharpe.py)
- **momentum-T4:** n_trades < 30 OR n_oos_bars < 252 (R6 sample-size floor)

`kill_switch_threshold: 0.30`

Rationale: Same reasoning as R3 (ma_crossover). The R1 universal floor of 0.30 is
appropriate for a strategy expected to produce near-zero Sharpe on this carry-dominated
universe. The strategy is archived as dominated; the OOS run logs the verdict rather
than tests a novel thesis. Setting the bar higher than 0.30 would manufacture a
foregone rejection at a more arbitrary threshold.

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
