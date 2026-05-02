# Pre-Registration: ma_crossover_3x_costs

**Status:** Prospective pre-registration (Phase 2 Wave-5 Round-2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** ma_crossover
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** W5R2-1
**Phase:** 2.5 — Wave-5 Tier B closure
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
**HoQR queue ref:** .fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 1

## Hypothesis (the NULL being tested)

This pre-registration tests whether ma_crossover (already rejected at 1× costs OOS-2022) remains rejected when transaction costs are tripled. The null: "ma_crossover generates no exploitable alpha at 3× costs (OOS Sharpe < 0.30) on EURUSD, USDJPY, GBPUSD over 2022-01-01 to 2023-12-31."

## Mechanism

Reuses `src/forex_system/strategies/ma_crossover.py` (MACrossoverStrategy). The 3× cost stress is applied via the `--cost-multiplier 3.0` hook in `scripts/run_falsification_trial.py`, which scales all cost-model parameters (spread, slippage, commission, swap) by 3.0 before the backtest run. This constitutes a materially different configuration from the already-rejected ma_crossover trial (W2R1, 1× costs).

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire:

- **W5R2-1-T1:** OOS Sharpe < 0.30 (R1 universal floor)
- **W5R2-1-T2:** Max drawdown > 25% (R3 firm anchor)
- **W5R2-1-T3:** DSR < 0.50 with N = n_trials_at_spawn (R2 NHT frozen)
- **W5R2-1-T4-trades:** n_trades < 30 (R6 sample-size floor)
- **W5R2-1-T4-bars:** n_oos_bars < 252 (R6 sample-size floor)
- **W5R2-1-T5-cost-stress:** cost_multiplier = 3.0 (cost-stress trigger; any Sharpe under 3× costs confirms cost sensitivity)

`kill_switch_threshold: 0.30`

## OOS Sample Discipline

`oos_overlap: false`
`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Approval

- HoQR: signed via Wave-5 Round-1 artifact (.fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 1)
- NHT co-sign: deferred to Round 3
- CTO/CRO: absent for Phase-2.5 per acceptance criteria
