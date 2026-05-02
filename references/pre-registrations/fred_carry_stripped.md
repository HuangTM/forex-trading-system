# Pre-Registration: fred_carry_stripped

**Status:** Prospective pre-registration (Phase 2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** fred_carry_stripped
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** R7
**Phase:** 2 — operational falsification trials
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md

## Hypothesis (the NULL being tested)

This pre-registration tests the load-bearing nature of the BoJ-divergence regime
conditioning in FRED-carry Bet #1. The null being tested is: "the FRED-carry signal,
with the regime conditioning (BoJ-divergence flag) removed, achieves OOS Sharpe >=
0.60 on the OOS-2022 window — i.e., the regime filter is NOT the marginal source of
the 0.80 Sharpe observed in Bet #1 validation." If the null survives (fail-to-falsify:
stripped Sharpe >= 0.60), the arch thesis of Bet #1 is partially undermined —
the BoJ-divergence conditioning may have been incidental rather than causal, and
Bet #1's 0.80 Sharpe may reflect data-snooping in regime selection rather than
a genuine structural edge. Conversely, if the stripped variant's Sharpe falls
materially below 0.60 (the regime filter IS load-bearing), this confirms the Bet #1
arch thesis prospectively on independent data. This is the highest-stakes trial in
the Phase 2 queue: a fail-to-falsify here triggers mandatory Bet #1 re-review before
any paper launch.

## Mechanism

The fred_carry_stripped strategy is the FRED-carry Bet #1 strategy (carry_fred,
`src/forex_system/strategies/carry_fred.py`) with ALL regime conditioning removed.
Specifically, the following components of carry_fred are REMOVED in the stripped
variant:

1. **BoJ-divergence flag** — any conditioning on BoJ policy divergence status
   (whether implemented as a signal gate, position scalar, or regime indicator)
2. **FRED macro composite filter** — any FRED-sourced macro indicator that gates
   or scales the carry signal based on broader macro regime

What is RETAINED from carry_fred:
- The FRED rate differential as the primary signal source
- Cross-sectional z-score rank-normalization across all 12 pairs
- The min_differential threshold (0.001 = 0.1%)
- Standard position sizing via the harness

The stripped strategy should be interpretable as: "pure cross-sectional FRED rate
carry, no regime conditioning." Its performance relative to the unstripped carry_fred
on the same OOS-2022 window is the treatment effect of regime conditioning.

**IMPLEMENTATION NOTE: This module does not yet exist.**
Implementation is ROUTE_TO quant-developer. QD must create
`src/forex_system/strategies/fred_carry_stripped.py` as a subclass or wrapper of
`CarryFREDStrategy` with `regime_conditioning=False` parameter support, or as a
standalone class that exposes only the rank-normalized FRED carry signal path from
`carry_fred._ranked_signals()` without any BoJ-divergence gate. This pre-reg
references the module as TBD-implementation-by-QD; the trial may NOT be run until QD
confirms the implementation is complete and the stripped variant does not leak any
regime signal through indirect conditioning paths.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected — regime conditioning IS load-bearing) if
ANY of the following triggers fire on the OOS-2022 window (2022-01-01 → 2023-12-31):

- **fred_carry_stripped-T1:** OOS Sharpe < 0.60 (this pre-reg's kill_switch_threshold
  supersedes the R1 floor of 0.30; the bar is set high because carry_fred achieved
  0.80 on its OOS window — if the stripped version can't clear 0.60 on an independent
  window, that is strong evidence the regime filter is load-bearing)
- **fred_carry_stripped-T2:** Max drawdown > 25% (R3 firm anchor; note: this
  threshold may be tightened to 20% by CRO pre-freeze; current value is 25% per
  the frozen R3 anchor as of 2026-05-01)
- **fred_carry_stripped-T3:** Deflated Sharpe (DSR per Bailey & Lopez de Prado 2014)
  < 0.50 with N = n_trials_at_spawn (R2 frozen NHT threshold; QD computes via
  src/forex_system/harness/deflated_sharpe.py)
- **fred_carry_stripped-T4:** n_trades < 30 OR n_oos_bars < 252 (R6 sample-size floor)

**INVERSION NOTE:** For this pre-reg only, the failure direction of T1 is inverted
versus R3–R6:

- If OOS Sharpe < 0.60: T1 fires, strategy is FALSIFIED (rejected as weak) — this
  CONFIRMS Bet #1 arch thesis (regime conditioning IS load-bearing)
- If OOS Sharpe >= 0.60: T1 does NOT fire — this is a FAIL-TO-FALSIFY that
  undermines Bet #1 arch thesis and triggers mandatory HoQR + NHT re-review before
  any Bet #1 paper launch

The fail-to-falsify outcome (stripped >= 0.60) is the HIGH-STAKES scenario. It does
not promote fred_carry_stripped to paper trading; it triggers a review gate on
Bet #1 itself.

`kill_switch_threshold: 0.60`

Rationale: Set at 0.60 — materially above the R1 floor of 0.30, and equal to the
VTC gate_threshold (grandfathered). The rationale: carry_fred achieved 0.80 on its
OOS window; a stripped variant that cannot match 0.60 on an independent window (a
75% retention of the original performance) is evidence that the conditioning adds
real lift. Setting the bar at 0.30 would be too lenient — we expect pure FRED carry
to have genuine alpha; the question is HOW MUCH lift the regime conditioning adds.
R1 override rule: max(0.30, 0.60) = 0.60.

## OOS Sample Discipline

`oos_overlap: false`

The OOS-2022 window (2022-01-01 → 2023-12-31) is independent of the window used to
validate FRED-carry Bet #1 (OOS post-2024, BoJ-divergence period). This is critical
for R7: the original Bet #1 validation was explicitly conditioned on BoJ-divergence
regime activity in the post-2024 period. The OOS-2022 window pre-dates that regime
period and therefore provides an independent test of whether the unstripped signal
source (FRED carry) has alpha outside the regime that Bet #1 was designed to exploit.
Non-overlap declaration documented in docs/decisions/oos_window_reservations_2026-05-01.md.

`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Capacity Estimate

$200k notional ceiling (HoQR best-guess) — if the stripped variant performs similarly
to carry_fred on OOS-2022 (the fail-to-falsify scenario), its capacity is assumed
comparable to Bet #1's multi-pair portfolio. However, since this trial is diagnostic
and not promotion-bound, the capacity estimate is advisory only. QD must confirm
actual leverage usage from backtest output before any capacity number is taken as binding.

## Approval

- Quant Researcher: filed by HoQR authority per docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
- NHT: pre-registration filed prospectively; thresholds locked per nht-frozen-thresholds.yaml
- CTO/CRO: absent for Phase 2 falsification trials per acceptance-criteria
