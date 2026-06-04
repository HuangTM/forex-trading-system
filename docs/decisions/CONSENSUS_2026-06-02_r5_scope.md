# CONSENSUS: R5-on-real-carry — SCOPE / test-design package (kill-test, not rescue)

**Status:** RATIFIED — distributed quorum (ratified_with_dissent: head-of-quant-research + mathematician approve; NHT dissent preserved verbatim). **SCOPE/DESIGN-stage only** — NOT authorization to build, run, or wind-down. The build-vs-wind-down fork is surfaced to the CEO below.
**Track:** r5-scope-2026-06-02 / Phase 1 / Task 1.0
**Ratification:** `.agent-accountability/ratifications/r5-scope-2026-06-02:phase1:task1.0.yaml`
**Dissent:** `.agent-accountability/dissents/r5-scope-2026-06-02:phase1:task1.0:null-hypothesis-tester.yaml`
**Follow-on under:** `CONSENSUS_2026-06-01_paper_launch_acceleration.md` (HoQR research item #1) and `CONSENSUS_2026-06-02_bet1_retirement.md` (firm has ZERO validated OOS survivors)
**Session:** /fintech-org "continue" → R5 scope, autonomous default (v0.6.0). Authored by the orchestrator from the four completed role artifacts (PM agent dropped mid-author — socket close; synthesis, not domain judgment).

## Roles staffed

- **pm** (sonnet) — acceptance criteria CRIT-1..21, coordination; makes no test-design/provenance decisions.
- **mathematician** (opus) — R5 test-design spec: method choice, statistic, resampling unit, block length, K, FWER/FDR.
- **head-of-quant-research** (opus) — carry-program universe, data-provenance framing, prerequisites/sequencing, go/no-go.
- **null-hypothesis-tester** (opus) — power, theatricality risks, data-snooping verdict, data-integrity precondition; dissent (verbatim §Dissent).

No CRO/CTO/Principal-Reviewer staffed: design-only scope wave, no capital, no position-sizing, no code or architecture artifact ratified (harness work is a *named prerequisite*, not decided here).

## Decision (one paragraph)

The org delivers a complete, internally-consistent **scope/test-design package for R5 on real carry data**. The correct instrument is **Hansen's SPA (primary) + White's Reality Check (conservative cross-check), computed off one set of joint stationary-block bootstrap draws**: benchmark = **zero** (cost-of-carry is already in the swap leg → an external carry benchmark double-counts), test operates on the **net-of-cost, post-entry-delay** per-cell return series, **K ≥ 2000** (K=200 is theatrical — MC-SE 0.015 straddles the 0.05 boundary), **FWER via the max-statistic** over a **single pooled family of 6 carry variants × 6 JPY crosses (~36 cells)** whose *effective* independent dimension is ≈1–4 (HoQR estimates 1–2 / NHT 2–4; they are re-parameterizations/ablations of ONE rate-differential idea, hence joint same-block resampling). **The R5 core test math substantially EXISTS** (`src/forex_system/harness/reality_check.py`, 762 LoC: R5a circular-block bootstrap, R5c Hansen SPA, B=10000) — the dominant bottleneck is **data, not greenfield statistics**, but **STEP 2 is NOT pure plumbing**: per the Mathematician's `harness-prereq` field the existing `r5c_hansen_spa` needs three real additions before it serves this test — (a) **Politis-White automatic block-length selection** (current code uses a fixed `block_length=10`, not the data-driven rule); (b) **White-RC emitted as a separate p-value** off the same draws (current R5c outputs SPA only); (c) **joint (T, ~36) cell-matrix construction** across all 6 variants on one gap-aligned daily index (existing signature was framed per-strategy-multi-pair). Sequenced: (STEP 1) a **data-integrity audit [HARD BLOCKER]** ∥ (STEP 2) the harness work above, then (STEP 3) a **crypto-frozen pre-registration with a wind-down action map [the NEXT deliverable]**, then (STEP 4) a one-shot run. **R5 is UNDERPOWERED** — class-level power ≈ **20–35%** against a true ~0.30 annualized Sharpe over ~16y of daily data under FWER over correlated cells — so it is an **HONEST KILL TEST, not a rescue vehicle**: the pre-reg MUST pre-commit that an underpowered **non-rejection → WIND-DOWN**, not "inconclusive, keep spending," and a **p < 0.05 is NECESSARY-but-NOT-sufficient** for CONTINUE (snooping on the firm's longest-studied strategies is sunk and uncontrollable; a clean p needs a genuine hold-out or a deflated-Sharpe haircut). **This consensus ratifies the SCOPE only; the strategic BUILD-R5-as-terminal-kill-test vs SKIP-to-WIND-DOWN-NOW fork is a CEO decision, surfaced below.**

## Acceptance criteria (PM CRIT-1..21) — coverage

| Area | CRITs | Owner | Status |
|---|---|---|---|
| Data provenance | 1,2,3,6 | HoQR + NHT | ✅ processed/ is REAL (range-verified, not by filename); synthetic_phase0 corrupt in 3 pairs → quarantine; rate feed REAL but monthly. Two checks remain OPEN (fetch manifest; contamination grep) → folded into STEP 1. |
| Carry universe | 4,5 | HoQR | ✅ all 6 variants × 6 JPY crosses; NO silent exclusion (would void FWER). |
| Test design | 7–13 | Mathematician | ✅ SPA primary + White-RC cross-check; statistic, resampling unit, block length, K=2000, FWER all specified + steelmanned. |
| Prereqs / sequencing | 14,15,16 | HoQR | ✅ 4-step critical path; STEP 1∥STEP 2 → STEP 3 (pre-reg, NEXT) → STEP 4 (run). |
| Go/no-go | 17,18,19 | HoQR + NHT | ✅ CONTINUE/WIND-DOWN/AMBIGUOUS framework; power flagged inadequate (CRIT-18); p<0.05 necessary-not-sufficient (CRIT-19). |
| Output completeness | 20,21 | PM | ✅ this document is the single self-contained package; all four role artifacts referenced, none silently excluded. |

## R5 test design (Mathematician — verified)

- **Method:** Hansen SPA primary, White RC conservative cross-check, off the **same** stationary-bootstrap draws (report BOTH p-values). SPA dominates RC in power here because the universe is dominated by near-zero/negative cells (RC's least-favourable-configuration null collapses power exactly then; SPA studentizes + recenters poor cells out). Feature-label permutation **rejected** as primary (it tests a single-strategy null; min over 36 cells IS the snooping it was meant to prevent).
- **Null (pre-registerable):** H0: max over cells k of expected **benchmark-relative, net-of-cost** per-bar performance d_k ≤ 0. Reject iff SPA p < α = 0.05. Universe U, benchmark, OOS window, per-cell construction MUST be frozen in pre-reg before any draw.
- **Statistic:** studentized mean T_k = √n·mean(f_k)/ω̂_k; family T_SPA = max_k T_k. Daily returns (4245 bars > monthly's ~190; autocorrelation handled by the block bootstrap).
- **Resampling:** JOINT per-bar vector across all ~36 cells, same blocks in lockstep (preserves cross-sectional dependence — the dominant dependence; lets the max-stat null reflect the true small effective dimensionality; no separate Bonferroni needed). Stationary bootstrap (Politis-Romano), mean block length L by Politis-White (2004) auto-rule, max across cells, guard L≥1. **Empirical surprise:** carry strategy-RETURNS are near-white (ACF lag-1 = −0.003, |ACF|<0.017 to lag 60) despite persistent positions → L likely short (1–20d). Do NOT inflate L from the false "held-for-months ⇒ highly autocorrelated" intuition.
- **K = 2000** (up from aspirational K=200): MC-SE of a bootstrap p at p=0.05 is √(p(1−p)/K) → K=200 gives 0.0154 (decision flips on bootstrap noise); K=2000 gives 0.0049. K controls p-resolution, NOT power.
- **Multiplicity:** FWER strong control via max-stat (CONTINUE/WIND-DOWN is one binary firm decision → cost object is P(any false CONTINUE) = FWER). FDR is the wrong control (a portfolio-sizing question). Single pooled family of ~36 cells = one p, one decision; per-pair families would need a second Bonferroni-over-6.

## Carry universe (HoQR — verified)

6 variants `{carry, carry_fred, fred_carry_stripped, vol_target_carry, vol_target_carry_no_vol_scaling, carry_momentum}` × 6 JPY crosses `{USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY}`. NO exclusion (silent drop voids FWER). These are NOT 6 independent hypotheses — re-parameterizations/ablations of ONE rate-differential idea sharing the same feed and overlapping price returns; effective independent tests ≈ 1–2 (HoQR) / 2–4 (NHT). Non-JPY pairs out of scope (program never claimed them). USDJPY pair INCLUDED because the canonical input `data/processed/USDJPY_daily.parquet` is REAL (75.8–161.7); it is excluded only if R5 is ever pointed at `processed_synthetic_phase0/`, which is prohibited.

## Data provenance (HoQR + NHT — independently verified by reading parquets, not filenames)

- **`data/processed/` is REAL** over 2010–2026 (n≈4245/pair): USDJPY 75.82–161.71, EURUSD 0.959–1.483, all 6 JPY crosses realistic. `storage.load_ohlcv` reads `data_dir/'processed'/` → the **harness consumes the REAL set by default**. The long-held "everything synthetic" prior is WRONG.
- **`data/processed_synthetic_phase0/` is CORRUPT in 3 pairs** (broader than the reported 1): USDJPY 5.03–7.75, GBPJPY 1.54–2.28, CADJPY max 203.64 (EURUSD/EURJPY/AUDJPY/NZDJPY there match the real set). Disposition: **QUARANTINE** (tag DO-NOT-USE / range-assert at load), purge only after the contamination audit.
- **Rate differentials** `data/rates/rate_differentials.parquet` (2001–2026, n=6540) are REAL policy-rate diffs but **forward-filled MONTHLY** (sourced from monthly central-bank CSVs) → daily carry "alpha" is dominated by the price leg and **effective-N is closer to monthly (~180, fewer per the ~36-month holdout) than daily**. Must be reflected in block length and power.
- **Two provenance checks remain OPEN** (folded into STEP 1, not papered over): (1) locate the fetch/manifest to PROVE `processed/` origin (`data/raw` is empty); (2) **contamination audit** — grep `scripts/`, `src/`, committed result parquets for `processed_synthetic_phase0`/hardcoded synthetic paths and enumerate which prior carry results used the corrupt USDJPY/GBPJPY/CADJPY. Until (2) closes, no historical carry Sharpe is a trustworthy CONTINUE input.

## Sequencing (HoQR) — the bottleneck is data, not math

| Step | Work | Owner | Depends on | Blocking? |
|---|---|---|---|---|
| **STEP 1** | Data-integrity audit: instrument loader (print resolved path + content hash), re-derive prior carry on REAL series, quarantine/range-assert corrupted synthetic, confirm rate-index alignment | QD/data | none | **YES — HARD BLOCKER (NHT)** |
| **STEP 2** | Surface clean per-variant/per-pair **full-history net-of-cost** return arrays into the metrics dict feeding `reality_check.py`, **PLUS** the three named code gaps: (a) Politis-White auto block-length (replace fixed `block_length=10`), (b) White-RC as a 2nd p-value off the same draws, (c) joint (T,~36) cell-matrix on one gap-aligned daily index. Block length MUST be re-derived per-variant (the near-white ACF was a single-proxy finding; vol-targeted/FRED-conditioned variants may differ) | QD/harness | none (∥ STEP 1) | YES (long pole) |
| **STEP 3** | **Crypto-frozen pre-registration** + **wind-down action map**: null, statistic, frozen 6×6 grid, OOS window, block length, K, α, go/no-go threshold, deflation/hold-out treatment | HoQR + Mathematician + NHT | STEP 1 + STEP 2 | YES — **the NEXT deliverable** |
| **STEP 4** | Execute R5 once against the frozen pre-reg on confirmed-real data | QD + NHT (witness) | STEP 3 | terminal |

## Go/no-go interpretation (HoQR + NHT)

- **CONTINUE (R5-path):** SPA p < 0.05 at the **CLASS level** on a **frozen pre-registered** hypothesis surfaces ≥1 distinguishable carry variant → firm has a defensible class-level candidate; unfreeze N for **confirmatory-only** trials. **NECESSARY-but-NOT-sufficient** — a single isolated p<0.05 cell does NOT rescue the program (that is the artifact R5 exists to catch); post-hoc variant/pair selection invalidates the p at any magnitude.
- **WIND-DOWN (R5-path):** p ≥ 0.05 across the family → carry program indistinguishable from chance at the class level; combined with the already-completed Bet#1 retirement → **zero validated alpha is structural**, recommendation = formal wind-down to monitoring.
- **AMBIGUOUS:** subset survives → new pre-reg for confirmatory-only testing of the survivor(s); never a CONTINUE on the original family.
- **POWER caveat (binding):** the pre-reg MUST state the power number and pre-commit that an underpowered non-rejection reads as "no DISTINGUISHABLE class-level alpha at the achievable power" → **WIND-DOWN**, NOT "carry alpha is zero" and NOT "inconclusive, keep spending."

## Decisions NOT made (deferred / out of scope)

- **Running R5** (no permutations this wave). **Implementing STEP 1/STEP 2** (named QD prerequisites). **Writing the pre-registration** (the NEXT deliverable). **The BUILD-vs-WIND-DOWN strategic fork** (CEO decision, surfaced below). New-alpha / new trial (org trial-counter line count = 36, verified `wc -l .fintech-org/trials.jsonl`; design-only, no increment). The observe-only momentum-EURUSD canary (separate operational track). Any sizing/capital/paper decision.

## Assumptions we're betting on

- The CONTINUE/WIND-DOWN framework (HoQR retirement criteria, `CONSENSUS_2026-06-01`) is ratified firm policy for this wave.
- The 6 strategy files are the EXHAUSTIVE carry family (STEP 1 grep to confirm none live outside `src/forex_system/strategies/`).
- `rate_differentials.parquet` is the single signal source for all 6 variants.
- The stated ~0.30 carry Sharpe is **ANNUALIZED** (both NHT and Mathematician — the only economically plausible reading; if per-bar daily, the cell is trivially significant and the framing is wrong → MUST be confirmed in pre-reg).
- The OOS window is genuinely held-out from all six variants' development (HoQR/NHT to confirm in pre-reg; if not, R5 is in-sample-contaminated and its p is not face-valid).

## Pre-registered falsification (the NEXT deliverable — not produced here)

This scope produces the *requirements* for the R5 pre-registration; the pre-reg document itself (crypto-frozen null, statistic, frozen 6×6 grid, OOS window, block length, K, α, go/no-go threshold, deflation/hold-out treatment, wind-down action map) is STEP 3, to be filed and frozen BEFORE any draw.

## Dissent (preserved verbatim)

### Null-Hypothesis Tester — `decision: dissent`, `severity: material_concern`, `does_block: false`

> *Byte-authoritative verbatim copy: the linked dissent artifact (content-hash in the ratification). The blockquote below preserves the wording exactly; markdown reflows source line-wrapping only.*

> NHT DISSENT — R5 as proposed is underpowered theater, not a test that can reject.
>
> 1. At the stated per-cell annualized Sharpe ~0.30 over ~4000 bars, a single pre-specified cell already only reaches t ~ 1.2 — below the ordinary 1.96 threshold BEFORE any multiplicity correction. Under FWER control across ~36 highly cross-correlated JPY-cross carry cells (effective independent bets ~ 2-4), the expected outcome is FAILURE TO REJECT whether or not a small real edge exists. A p >= 0.05 from this design is therefore UNINFORMATIVE — it is not evidence of no-edge, and it must not be read as one.
> 2. K=200 cannot resolve a multiplicity-corrected 0.05 quantile: p is quantized at ~0.005 with Monte-Carlo SE ~0.015 at the boundary, a coin-flip straddling the threshold. Any FWER-controlled decision needs K >= 2000 (target 5000-10000) with reported MC-SE.
> 3. R5 controls ONLY the looks it pre-registers. These are the firm's longest-studied strategies with a large prior trial history; that spent selection is NOT retroactively controlled by a prospective Reality-Check. A re-test on the same 2010-2026 data inherits the snooping and yields an optimistically biased p. The only clean p comes from post-pre-registration forward/hold-out bars or an explicit deflated-Sharpe haircut.
> 4. HARD BLOCKER: I confirmed a corrupted USDJPY series (close 5.03-7.75) sits in data/processed_synthetic_phase0/ alongside the real one (75.82-161.71). It is unknown which fed prior carry results. No R5 may be sized until the runtime data path is instrumented, prior carry numbers are re-derived on the REAL series, and the corrupted file is quarantined/range-asserted.
>
> RECOMMENDATION: Do NOT build R5 as a validation vehicle. Resolve data integrity first. Then, if built, scope R5 explicitly as an HONEST KILL TEST (block-bootstrap matched-carry null, crypto pre-reg of the full grid + wind-down action map, Romano-Wolf StepM, K>=2000 with MC-SE, evaluated on hold-out/forward bars). Its most probable honest outcome is a non-rejection — which is itself the signal to weigh WIND-DOWN. A non-significant R5 cannot license CONTINUE; a significant R5 on snooped in-sample data cannot either.

**Resolution:** CONCORDANT-WITH-CONDITIONS — the scope ADOPTS every NHT condition (kill-test framing, data-integrity STEP 1 hard blocker, K≥2000+MC-SE, Romano-Wolf-StepM/SPA/White-RC max-stat over the joint null, crypto pre-reg + wind-down map as STEP 3, hold-out/deflation for prior snooping, annualized-Sharpe reading confirmed). The dissent is not overridden; it is the spine of the scope. HoQR concurs explicitly: *if the underpowered-null=wind-down pre-commitment cannot be accepted, SKIP the build and go straight to wind-down.*

## Independent review findings (Principal Reviewer)

none — Principal Reviewer not staffed (design/scope wave, no code or algorithm artifact produced; the test math `reality_check.py` already exists and is not modified this wave). A PR review wave is required when STEP 2 plumbing code is produced.

## Signatures

- pm: acceptance-criteria CRIT-1..21 — `.fintech-org/artifacts/2026-06-02T-r5-scope/pm-acceptance-criteria.yaml`
- mathematician: `decision: implement` (test-design) — `.fintech-org/artifacts/2026-06-02T-r5-scope/mathematician-r5-spec.yaml`
- head-of-quant-research: `decision: approve-with-capacity-limit` — `.fintech-org/artifacts/2026-06-02T-r5-scope/hoqr-r5-universe.yaml`
- null-hypothesis-tester: `decision: dissent` (material_concern, non-blocking; verbatim above) — `.fintech-org/artifacts/2026-06-02T-r5-scope/nht-r5-power-integrity.yaml`

---

## ⮕ CEO DECISION REQUIRED (surfaced, NOT auto-ratified): the BUILD-vs-WIND-DOWN fork

The scope above is quorum-ratified. The **strategic fork it tees up is a first-class CEO decision** (terminal/high-stakes — wind-down is irreversible firm policy; not in the autonomous quorum's authority):

- **BUILD** R5 as the terminal honest kill test — cheap (math already exists; only STEP 1 audit + STEP 2 plumbing + STEP 3 pre-reg remain), but **most-likely outcome is a non-rejection → wind-down anyway** (underpowered). Value: a wind-down then rests on a frozen, pre-registered class-level test on confirmed-real data rather than a prior.
- **SKIP to WIND-DOWN NOW** — accept the underpowered-kill-test reality (HoQR + NHT concordant prior is LOW), declare zero validated alpha structural, and redirect remaining capacity to the contamination audit + monitoring.

Either path, **STEP 1 data-integrity audit runs first** if BUILD is chosen (NHT hard blocker). Suggested responses: `build` · `wind-down` · `revise <X>`.
