# Pre-Registration: carry_momentum

**Status:** Prospective pre-registration (Phase 2 falsification trial)
**Date:** 2026-05-01
**Strategy ID:** carry_momentum
**Pair:** EURUSD, USDJPY, GBPUSD
**Pre-reg ID:** R6b
**Phase:** 2 — operational falsification trials
**Parent CONSENSUS:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md

## Hypothesis (the NULL being tested)

This pre-registration tests the carry_momentum strategy (macro-direction timing hybrid)
on the held-out OOS-2022 window and operates as a decision node for the arch thesis.
The null being tested is: "carry_momentum does not provide a Sharpe improvement over
unaugmented carry (R6a) sufficient to constitute a distinct strategy worth evaluating
for paper trading — OOS Sharpe < 0.50 OR dominated by carry_fred by more than 0.30."
This is a genuine decision node, not pure box-checking, because: (a) the carry_momentum
thesis (macro direction + price timing creates a more tradeable signal with higher
trade frequency) is an explicit arch conjecture that has not been tested on OOS data;
and (b) the outcome determines whether this strategy family branches (carry_baseline
rejected, carry_momentum evaluated as standalone) or collapses (both dominated by
carry_fred). Per R6 split from Conflict 1 reconciliation: this pre-reg (R6b) covers
carry_momentum only; the unaugmented carry baseline is R6a.

## Mechanism

The carry_momentum strategy blends two signals: (1) a carry component from static or
FRED rate differentials, normalized by max_differential (default: 5%) and zeroed
below a minimum threshold (default: 0.2%), and (2) a momentum component from an SMA
crossover (default: 20-period fast, 50-period slow), computed as the normalized
distance between fast and slow SMAs clipped to [-1.0, +1.0]. Default weights are 50%
carry, 50% momentum. The key behavioral rule: when `agreement_only=True` (the default),
signals are only non-zero when carry and momentum agree on direction — this filters
momentum signals that fight the macro carry direction. When they disagree, the strategy
is flat. This agreement filter is the primary differentiator from either strategy alone:
it should produce fewer trades than pure momentum and higher per-trade conviction.
Implementation: `src/forex_system/strategies/carry_momentum.py`, class
`CarryMomentumStrategy`.

## Falsification Criteria

The strategy is FALSIFIED (status: rejected) if ANY of the following triggers fire on
the OOS-2022 window (2022-01-01 → 2023-12-31):

- **carry_momentum-T1:** OOS Sharpe < 0.50 (this pre-reg's kill_switch_threshold
  supersedes the R1 floor of 0.30; carry_momentum is expected to have carry-level
  alpha at minimum, given carry is a component; the 0.50 bar matches R6a)
- **carry_momentum-T2:** Max drawdown > 25% (R3 firm anchor)
- **carry_momentum-T3:** Deflated Sharpe (DSR per Bailey & Lopez de Prado 2014) < 0.50
  with N = n_trials_at_spawn (R2 frozen NHT threshold; QD computes via
  src/forex_system/harness/deflated_sharpe.py)
- **carry_momentum-T4:** n_trades < 30 OR n_oos_bars < 252 (R6 sample-size floor;
  NOTE: the agreement_only filter may reduce trade count materially — QD must verify
  n_trades before treating OOS-2022 as valid)
- **carry_momentum-T5 (dominance test):** OOS Sharpe < (carry_fred OOS Sharpe on
  same OOS-2022 window − 0.30). The margin here is wider than R6a (0.30 vs 0.20)
  because carry_momentum adds the momentum overlay to the carry base — if the blended
  strategy still cannot come within 0.30 Sharpe of carry_fred, the blend provides no
  arch advantage over the dominant validated strategy.

`kill_switch_threshold: 0.50`

Rationale: Same as R6a — carry is a component of carry_momentum, so the minimum bar
should match carry_baseline's threshold. The momentum overlay is conjectured to add
value; the OOS test will determine if the conjecture holds. Setting the bar below 0.50
would allow a carry_momentum result that's weaker than the carry baseline to survive,
which would be a methodological regression. R1 override rule: max(0.30, 0.50) = 0.50.

## OOS Sample Discipline

`oos_overlap: false`

The OOS-2022 window (2022-01-01 → 2023-12-31) was selected specifically to avoid
overlap with vol_target_carry (full-history through 2026-04-25) and FRED-carry
Bet #1 (OOS post-2024). The 2022–2023 USD tightening and BoJ-YCC-stress macro regime
is distinct from the BoJ-divergence regime used in Bet #1 validation. Non-overlap
declaration documented in docs/decisions/oos_window_reservations_2026-05-01.md.

`oos_window_start: 2022-01-01`
`oos_window_end: 2023-12-31`

## Capacity Estimate

N/A — backtest-only OOS evaluation, no position sizing changes from existing code.

## Approval

- Quant Researcher: filed by HoQR authority per docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md
- NHT: pre-registration filed prospectively; thresholds locked per nht-frozen-thresholds.yaml
- CTO/CRO: absent for Phase 2 falsification trials per acceptance-criteria
