# Pre-Registration: carry_momentum_3x_costs

**Status:** Prospective pre-registration (Phase 2 Wave-5 Round-2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** carry_momentum
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** W5R2-5
**Phase:** 2.5 — Wave-5 Tier B closure
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
**HoQR queue ref:** .fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 5

## Hypothesis (the NULL being tested)

This pre-registration tests whether carry_momentum (already rejected at 1× costs, OOS Sharpe 0.197) remains rejected under 3× cost stress. The null: "carry_momentum generates no exploitable alpha at 3× costs (OOS Sharpe < 0.30) on EURUSD, USDJPY, GBPUSD over 2022-01-01 to 2023-12-31." HoQR estimates ~99% falsification probability — box-checking to confirm the strategy fails robustly under cost escalation.

## Mechanism

Reuses `src/forex_system/strategies/carry_momentum.py` (CarryMomentumStrategy). The 3× cost stress is applied via the `--cost-multiplier 3.0` hook in `scripts/run_falsification_trial.py`, scaling all cost-model parameters by 3.0. Materially different configuration from the already-rejected carry_momentum 1× trial.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire:

- **W5R2-5-T1:** OOS Sharpe < 0.30 (R1 universal floor)
- **W5R2-5-T2:** Max drawdown > 25% (R3 firm anchor)
- **W5R2-5-T3:** DSR < 0.50 with N = n_trials_at_spawn (R2 NHT frozen)
- **W5R2-5-T4-trades:** n_trades < 30 (R6 sample-size floor)
- **W5R2-5-T4-bars:** n_oos_bars < 252 (R6 sample-size floor)
- **W5R2-5-T5-cost-stress:** cost_multiplier = 3.0 (cost-stress trigger)

`kill_switch_threshold: 0.30`

## OOS Sample Discipline

`oos_overlap: false`
`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Approval

- HoQR: signed via Wave-5 Round-1 artifact (.fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 5)
- NHT co-sign: deferred to Round 3
- CTO/CRO: absent for Phase-2.5 per acceptance criteria
