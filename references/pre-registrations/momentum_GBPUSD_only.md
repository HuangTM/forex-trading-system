# Pre-Registration: momentum_GBPUSD_only

**Status:** Prospective pre-registration (Phase 2 Wave-5 Round-2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** momentum
**Pair:** GBPUSD
**Pre-reg ID:** W5R2-3
**Phase:** 2.5 — Wave-5 Tier B closure
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
**HoQR queue ref:** .fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 3

## Hypothesis (the NULL being tested)

This pre-registration tests whether the momentum strategy (which previously passed on EURUSD) holds on a single non-EURUSD pair, GBPUSD. The null: "momentum generates no exploitable alpha (OOS Sharpe < 0.30) on GBPUSD alone over 2022-01-01 to 2023-12-31." This is the only candidate in this batch with genuine scientific interest — a fail-to-falsify would suggest momentum has broader pair applicability than EURUSD alone.

## Mechanism

Reuses `src/forex_system/strategies/momentum.py` (MomentumStrategy). The single-pair restriction is applied via the `--pair-restrict GBPUSD` hook in `scripts/run_falsification_trial.py`, which overrides the sidecar's pair_resolved list. HoQR estimates ~70% falsification probability (borderline genuine test).

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire:

- **W5R2-3-T1:** OOS Sharpe < 0.30 (R1 universal floor)
- **W5R2-3-T2:** Max drawdown > 25% (R3 firm anchor)
- **W5R2-3-T3:** DSR < 0.50 with N = n_trials_at_spawn (R2 NHT frozen)
- **W5R2-3-T4-trades:** n_trades < 30 (R6 sample-size floor)
- **W5R2-3-T4-bars:** n_oos_bars < 252 (R6 sample-size floor)

`kill_switch_threshold: 0.30`

## OOS Sample Discipline

`oos_overlap: false`
`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Approval

- HoQR: signed via Wave-5 Round-1 artifact (.fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 3)
- NHT co-sign: deferred to Round 3
- CTO/CRO: absent for Phase-2.5 per acceptance criteria
