# Pre-Registration: vol_target_carry_no_vol_scaling

**Status:** Prospective pre-registration (Phase 2 Wave-5 Round-2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** vol_target_carry_no_vol_scaling
**Pair:** USDJPY
**Pre-reg ID:** W5R2-6
**Phase:** 2.5 — Wave-5 Tier B closure
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
**HoQR queue ref:** .fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 6

## Hypothesis (the NULL being tested)

This pre-registration tests whether vol-targeting is load-bearing for the validated vol_target_carry edge. The ablation removes the vol-targeting sizing (replaces it with unit/fixed long signal = 1.0) while preserving everything else. The null: "vol_target_carry without vol-targeting generates no exploitable alpha (OOS Sharpe < 0.30) on USDJPY over 2022-01-01 to 2023-12-31 (OOS-2022 window — distinct from vol_target_carry's full-history validation window)." This is the only scientifically meaningful candidate in Wave-5 Round-2; either outcome has interpretive value for the carry-thesis.

## Mechanism

New module `src/forex_system/strategies/vol_target_carry_no_vol_scaling.py` (VolTargetCarryNoVolScalingStrategy). Subclasses the Strategy interface separately from vol_target_carry.py — the validated module is not modified. Signal = 1.0 constant (unit long). The carry-filter gate (min_carry) is preserved for ablation parity. Registered as `vol_target_carry_no_vol_scaling` in `src/forex_system/strategies/registry.py`. HoQR estimates ~65% falsification probability.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire:

- **W5R2-6-T1:** OOS Sharpe < 0.30 (R1 universal floor)
- **W5R2-6-T2:** Max drawdown > 25% (R3 firm anchor)
- **W5R2-6-T3:** DSR < 0.50 with N = n_trials_at_spawn (R2 NHT frozen)
- **W5R2-6-T4-trades:** n_trades < 30 (R6 sample-size floor)
- **W5R2-6-T4-bars:** n_oos_bars < 252 (R6 sample-size floor)

`kill_switch_threshold: 0.30`

Stop conditions: if OOS Sharpe >= 0.50, surface to CEO/HoQR (suggests vol-targeting is NOT load-bearing for vol_target_carry's alpha; affects Bet #1 carry-thesis interpretation).

## OOS Sample Discipline

`oos_overlap: false`
`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Approval

- HoQR: signed via Wave-5 Round-1 artifact (.fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml §B candidate 6)
- NHT co-sign: deferred to Round 3
- CTO/CRO: absent for Phase-2.5 per acceptance criteria
