# R5 STEP-4 (2026-06-06) — Evidence-Correction Note

<!-- kill_switch_threshold: not-applicable — evidence-correction note, spawns no trial; the ratified R5 pre-reg declares 0.767 -->

**Date:** 2026-08-17
**Status of original:** `r5_carry_universe_kill_test.STEP4-RESULT.yaml` (2026-06-06,
`decision: AMBIGUOUS_GATE_FAIL`) — decision-level outcome **corroborated** by correction
re-run; 6 individual cells **voided** and replaced (see below). The original YAML is
retained unmodified for audit. This note is informational; formal supersession of the
ratified STEP-4 result requires CEO ratification.

## Why the original run was partially void

The 2026-08-17 independent audit found that the 6 `carry_momentum:*` cells ran
`rebalance_mode="continuous"` + `ContinuousSizer` **without the USD-nominal unit
contract**: JPY-quoted pairs carried ~1/price (~1/150) of intended risk
(`sizing/continuous.py` emitted price-denominated units; `engine.py:369-376` treated
them as USD nominal and divided by price again), plus silent `min_order_size` clipping.
Those 6 matrix columns were near-flat by construction, and they fed the joint
stationary bootstrap (Hansen SPA / White RC) — so the family-level p-values were also
computed with corrupted inputs.

Fixes landed 2026-08-17: `ContinuousSizer(usd_nominal=True)` at
`carry_universe_matrix.py:_build_sizer`; clipping now counted loudly
(`n_clipped_to_zero`); engine warns when a continuous-mode sizer does not declare the
USD-nominal contract.

## Correction re-run (informational)

Script: `scripts/r5_step4_correction_rerun_2026-08-17.py` — mirrors
`scripts/run_r5_step4.py` exactly (same frozen master_seed=576746, B=5000, SR0_PP,
Politis-White block length, studentized k* selection, DSR gate, decision functional),
same data window (already consumed by the 2026-06-06 run — no new one-shot burn).
Output: `r5_carry_universe_kill_test.STEP4-RESULT.correction-rerun.yaml`;
per-cell Sharpes: `r5_carry_universe_kill_test.correction-rerun-cell-sharpes.yaml`.

| Quantity | Original (2026-06-06) | Correction re-run (2026-08-17) |
|---|---|---|
| Decision | AMBIGUOUS_GATE_FAIL | **AMBIGUOUS_GATE_FAIL (unchanged)** |
| k* cell | vol_target_carry:USDJPY | vol_target_carry:USDJPY (unchanged) |
| DSR @ k* | 0.95029 (cleared ≥0.95) | 0.9503 (cleared, still marginal) |
| SPA p (consistent) | 0.0162 | 0.0144 |
| White RC p | 0.0588 | 0.0528 |
| Block length | 21 | 14 (Politis-White recomputed on corrected matrix) |
| T × k | 4186 × 36 | 4186 × 36 |

## The 6 voided cells, now at intended risk (annualized Sharpe)

| Cell | Original | Corrected |
|---|---|---|
| carry_momentum:USDJPY | ~0 (void — ~1/150 risk) | +0.25 |
| carry_momentum:EURJPY | ~0 (void) | +0.24 |
| carry_momentum:GBPJPY | ~0 (void) | +0.07 |
| carry_momentum:AUDJPY | ~0 (void) | +0.00 |
| carry_momentum:CADJPY | ~0 (void) | −0.05 |
| carry_momentum:NZDJPY | ~0 (void) | −0.08 |

**Reading:** at correct sizing the carry_momentum variant is weak-to-flat — the
near-zero readings were a bug, but the corrected numbers do not rescue the variant.
The family-level decision (AMBIGUOUS_GATE_FAIL) is robust to the fix. The
k*-adjacent diagnostics and the vol_target_carry:USDJPY DSR remain marginal
(0.9503 vs 0.95 threshold) — within noise of the gate, as before.

## Related 2026-08-17 corrections (same audit cycle)

- Basket M1/M2 kill-gate re-runs with `allow_shorts` fixed: addenda appended to
  `references/pre-registrations/macd_cross.md` and `ema_cross.md`. Verdicts
  unchanged (FAMILY_KILL); short legs improved economics but did not clear any gate.
- 3 synthetic daily pairs (AUDUSD/USDCAD/EURGBP) replaced with real data; not part
  of this 36-cell JPY-only matrix, but they DID contaminate
  `data/results/carry_fred_aggregate_2026-04-25.json` (Bet #1 "PASS, Sharpe 0.796") —
  that aggregate is separately void pending its own re-run.
- JPY rate series (frozen at 2017) replaced and `rate_differentials.parquet` rebuilt
  **before** this re-run — so the `carry_fred:*` / `fred_carry_stripped:*` cells here
  already reflect the corrected rates. The re-run therefore bundles two corrections
  (sizing contract + JPY rates); they were not isolated. The original 2026-06-06 run
  had BOTH defects. Comparing old-vs-new per-cell Sharpes for carry_fred cells
  (e.g. carry_fred:USDJPY −0.01) against any pre-fix numbers mixes both effects.

## Ratification (2026-10-28)

The owner ratified this correction re-run as **superseding** the 2026-06-06 STEP-4
result as the evidence of record. The decision (AMBIGUOUS_GATE_FAIL) and k*
(vol_target_carry:USDJPY) are unchanged, so no downstream action changes. The original
YAML stays in place unmodified. Confirmatory trial f2fb41fd
(`r5_confirmatory_vol_target_carry_usdjpy.md`) keeps its frozen receipt as-is: its SR0,
look dates and kill-switch threshold are not re-derived from the re-run, because
changing a frozen parameter would void the confirmatory test.
