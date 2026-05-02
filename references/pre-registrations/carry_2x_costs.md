# Pre-Registration: carry_2x_costs

**Status:** Prospective pre-registration (Phase 2 Wave-5 Round-2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** carry
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** W5R2-4
**Phase:** 2.5 — Wave-5 Tier B closure
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
**HoQR queue ref:** .fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 4

## Hypothesis (the NULL being tested)

This pre-registration tests whether the raw carry baseline (already rejected at 1× costs with OOS Sharpe 0.28) survives a 2× cost stress. The null: "carry generates no exploitable alpha at 2× costs (OOS Sharpe < 0.30) on EURUSD, USDJPY, GBPUSD over 2022-01-01 to 2023-12-31." HoQR estimates ~98% falsification probability.

## Mechanism

Reuses `src/forex_system/strategies/carry.py` (CarryStrategy). The 2× cost stress is applied via the `--cost-multiplier 2.0` hook in `scripts/run_falsification_trial.py`, which scales all cost-model parameters by 2.0. Materially different configuration from the already-rejected carry 1× trial.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire:

- **W5R2-4-T1:** OOS Sharpe < 0.30 (R1 universal floor)
- **W5R2-4-T2:** Max drawdown > 25% (R3 firm anchor)
- **W5R2-4-T3:** DSR < 0.50 with N = n_trials_at_spawn (R2 NHT frozen)
- **W5R2-4-T4-trades:** n_trades < 30 (R6 sample-size floor)
- **W5R2-4-T4-bars:** n_oos_bars < 252 (R6 sample-size floor)
- **W5R2-4-T5-cost-stress:** cost_multiplier = 2.0 (cost-stress trigger)

`kill_switch_threshold: 0.30`

## OOS Sample Discipline

`oos_overlap: false`
`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Approval

- HoQR: signed via Wave-5 Round-1 artifact (.fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 4)
- NHT co-sign: deferred to Round 3
- CTO/CRO: absent for Phase-2.5 per acceptance criteria
