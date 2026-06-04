# Consensus on: R5-on-real-carry — scope / test-design package (kill-test, not rescue)

**Status:** RATIFIED — distributed quorum (ratified_with_dissent: head-of-quant-research + mathematician approve; NHT dissent preserved). **SCOPE/DESIGN-stage only** — NOT authorization to build, run, or wind-down.
**Full audit:** see `./CONSENSUS_2026-06-02_r5_scope.md`
**Session:** /fintech-org "continue" → R5 scope, 2026-06-02/03 (autonomous default; orchestrator-authored from 4 completed role artifacts after PM agent dropped)

## Decision (one paragraph)

The org delivered a complete scope for R5 on **real** carry data. Correct instrument: **Hansen SPA (primary) + White Reality Check (cross-check)** off one set of **joint stationary-block bootstrap** draws; benchmark = **zero** (cost-of-carry already in the swap leg); **net-of-cost, post-entry-delay** returns; **K ≥ 2000**; **FWER via max-statistic** over a **single pooled family of 6 carry variants × 6 JPY crosses (~36 cells, effective independent ≈ 1–4)**. The R5 test math **ALREADY EXISTS** (`src/forex_system/harness/reality_check.py`); the bottleneck is **data, not implementation** — (STEP 1) data-integrity audit [HARD BLOCKER] ∥ (STEP 2) data-plumbing → (STEP 3) crypto-frozen pre-registration + wind-down map [the NEXT deliverable] → (STEP 4) one-shot run. **R5 is UNDERPOWERED** (class-level power ≈ 20–35% at true ~0.30 ann-Sharpe) → it is an **HONEST KILL TEST, not a rescue**; an underpowered **non-rejection → WIND-DOWN**, and **p<0.05 is necessary-not-sufficient** for CONTINUE (snooping on the firm's longest-studied strategies is sunk; needs hold-out / deflated-Sharpe haircut). Scope ratified; the **BUILD-vs-WIND-DOWN strategic fork is a CEO decision**. No backtest, no new trial (org line count 36), no capital.

## Top-3 things the CEO should know

1. **R5 is a kill test, most-likely → wind-down** (severity: high) — underpowered at ~0.30 Sharpe over 16y of monthly-signal carry; a non-rejection is the *expected* honest outcome and reads as WIND-DOWN, not "keep spending." (mathematician + null-hypothesis-tester, concordant.)
2. **The "everything synthetic" prior is WRONG; data integrity is the gate** (severity: high) — `data/processed/` is REAL (range-verified); the harness loads it by default; but `processed_synthetic_phase0/` is corrupt in 3 pairs (USDJPY/GBPJPY/CADJPY) and it is UNCONFIRMED which set fed prior carry results → STEP 1 must instrument the loader, re-derive prior carry on REAL series, and quarantine the corrupted set BEFORE any R5 spec is sized. (head-of-quant-research + null-hypothesis-tester.)
3. **Bottleneck is data, not greenfield stats — but STEP 2 is not pure plumbing** (severity: med) — `reality_check.py` (762 LoC) already implements the bootstrap + Hansen SPA, but STEP 2 must still add Politis-White auto block-length (replacing fixed L=10), emit White-RC as a 2nd p-value, and build the joint (T,~36) cell matrix across all 6 variants. Cheaper than greenfield, but real implementation work — don't under-scope it. (head-of-quant-research + mathematician.)

## Dissent (one-liner; full text in CONSENSUS.md)

- **NHT (severity: material_concern; does_block: false):** R5 as a *validation vehicle* is underpowered theater (single cell t≈1.2 pre-correction; K=200 can't resolve the corrected quantile; prospective RC can't launder spent selection; corrupted-USDJPY ambiguity is a HARD BLOCKER). Build it ONLY as an honest kill test — data-integrity first, block-bootstrap matched-carry null, crypto pre-reg + wind-down map, Romano-Wolf StepM, K≥2000+MC-SE, hold-out/forward eval. **The scope ADOPTS all of this** → concordant-with-conditions, not overridden.

## Open items requiring CEO acknowledgment

- **The BUILD-vs-WIND-DOWN fork** (the strategic decision this scope tees up): `build` (terminal honest kill test, cheap, most-likely → wind-down) vs `wind-down` (accept zero-validated-alpha as structural now) vs `revise <X>`. Either way STEP 1 data-integrity audit runs first if BUILD.
- If BUILD: the NEXT deliverable is the STEP 3 crypto-frozen pre-registration (HoQR + Mathematician + NHT), gated on STEP 1 + STEP 2.

## Ratification status

> **RATIFIED by distributed quorum (ratified_with_dissent).** Signers: head-of-quant-research, mathematician. NHT dissent preserved verbatim and adopted into the scope. Required-role coverage: none triggered (design-only, no risk/architecture artifact ratified). No forbidden-interim match. No capital. SCOPE-stage only.

CEO decision still open: **build R5, or skip to wind-down?** (`build` / `wind-down` / `revise <X>`).
