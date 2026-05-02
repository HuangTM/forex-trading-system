# Pre-Registration: carry_baseline

**Status:** Prospective pre-registration (Phase 2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** carry
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** R6a
**Phase:** 2 — operational falsification trials
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md

## Hypothesis (the NULL being tested)

This pre-registration tests the carry (unaugmented) strategy on the held-out OOS-2022
window and performs a DOMINANCE TEST against carry_fred (FRED-carry Bet #1). The null
being tested is: "the unaugmented carry signal (raw interest-rate differential, no
FRED macro conditioning, no regime filter, no cross-sectional ranking) achieves OOS
Sharpe >= carry_fred OOS Sharpe minus 0.20 on the same window — i.e., the dominance
margin claimed in the archival decision is not supported by independent OOS data."
This is GENUINE FALSIFICATION, not box-checking: the explicit arch thesis is that
FRED macro conditioning provides material lift (the dominance claim); testing that
claim on OOS-2022 data, where both strategies run on the same window, is a real
experiment. If the unaugmented carry is not dominated on OOS-2022, the archival
decision requires re-examination. Per R6 split from Conflict 1 reconciliation: this
pre-reg (R6a) covers the carry baseline only; carry_momentum is R6b.

## Mechanism

The carry strategy generates signals proportional to the interest-rate differential
between the base and quote currencies, sourced from FRED rate data (dynamic mode) or
static swap rates (fallback). In dynamic mode, the rate differential for each pair is
retrieved from `data/rates/rate_differentials.parquet`, forward-filled to daily
frequency, normalized by a maximum differential parameter (default: 5%), and clipped
to [-1.0, +1.0]. Differentials below a minimum threshold (default: 0.5%) produce
zero signal. This is the UNAUGMENTED baseline — no cross-sectional rank-normalization,
no BoJ-divergence regime flag, no FRED composite macro conditioning. It represents
the raw interest-rate carry trade with proportional position sizing.
Implementation: `src/forex_system/strategies/carry.py`, class `CarryStrategy`.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire on
the OOS-2022 window (2022-01-01 → 2023-12-31):

- **carry_baseline-T1:** OOS Sharpe < 0.50 (this pre-reg's kill_switch_threshold
  supersedes the R1 floor of 0.30; carry is expected to have real alpha — the
  higher bar reflects that archived carry strategies should clear a higher minimum
  than pure noise baselines before being considered alive)
- **carry_baseline-T2:** Max drawdown > 25% (R3 firm anchor)
- **carry_baseline-T3:** Deflated Sharpe (DSR per Bailey & Lopez de Prado 2014) < 0.50
  with N = n_trials_at_spawn (R2 frozen NHT threshold; QD computes via
  src/forex_system/harness/deflated_sharpe.py)
- **carry_baseline-T4:** n_trades < 30 OR n_oos_bars < 252 (R6 sample-size floor)
- **carry_baseline-T5 (dominance test):** OOS Sharpe < (carry_fred OOS Sharpe on
  same OOS-2022 window − 0.20). If carry_fred achieves Sharpe X on OOS-2022,
  carry_baseline must achieve >= X − 0.20 to avoid a dominance rejection. This is
  the primary falsification criterion — the arch thesis states carry_fred dominates
  carry by a material margin. Failure of T5 confirms the dominance claim; survival
  of T5 challenges it.

`kill_switch_threshold: 0.50`

Rationale: Set above the R1 universal floor of 0.30 because carry is a known
positive-alpha signal with decades of academic evidence. A carry strategy that
achieves only 0.10–0.29 Sharpe on OOS-2022 would be generating real but trivially
small alpha — below any deployment-worthiness threshold. The 0.50 bar is the
dominance-relevant threshold: if carry can't clear 0.50, the question of whether
carry_fred dominates it becomes moot (carry is simply weak). R1 override rule
applies: max(0.30, 0.50) = 0.50.

## OOS Sample Discipline

`oos_overlap: false`

The OOS-2022 window (2022-01-01 → 2023-12-31) was selected specifically to avoid
overlap with vol_target_carry (full-history through 2026-04-25) and FRED-carry
Bet #1 (OOS post-2024). Note: carry_fred's validated OOS was post-2024 (BoJ-divergence
period); the OOS-2022 window is entirely prior to that period, making this an
independent evaluation of both strategies on the same novel holdout window.
Non-overlap declaration documented in docs/decisions/oos_window_reservations_2026-05-01.md.

`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Capacity Estimate

N/A — backtest-only OOS evaluation, no position sizing changes from existing code.

## Approval

- Quant Researcher: filed by HoQR authority per docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
- NHT: pre-registration filed prospectively; thresholds locked per nht-frozen-thresholds.yaml
- CTO/CRO: absent for Phase 2 falsification trials per acceptance-criteria
