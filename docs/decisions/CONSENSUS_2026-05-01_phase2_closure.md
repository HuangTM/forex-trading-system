# CONSENSUS — Phase 2 Closure: Falsification Trial Outcomes & Wave-5 Readiness
**Date:** 2026-05-01
**Parent:** docs/decisions/CONSENSUS_2026-05-01_phase2_falsification.md (Phase 2 plan) → docs/decisions/CONSENSUS_2026-04-28.md (Direction v1)
**Status:** Draft — awaiting CEO ratification
**Roles signed:** HoQR, NHT (with append-only dissent), CRO (Wave-4 re-entry), QD, PM (this draft).
**Wave-5 paper-launch verdict:** BLOCKED (3 distinct conditions; see Section 9)

---

## 1. North-star (≤80 words)

"Make money" — operationalized as paper-traded Sharpe ≥ 0.5 OOS within 12 weeks.
Phase 2 was the operational falsification sub-track to satisfy CONDITION-1 (≥10 OOS rejections in trials.jsonl) and the NHT 2-week discipline window (≥5 by 2026-05-15). Phase 2 ALSO answered Phase 1's central strategic question via R7: is BoJ-divergence regime conditioning the load-bearing source of FRED-carry Bet #1's 0.80 Sharpe?

---

## 2. The Phase 2 verdict (≤300 words)

**Tier A (NHT discipline window): SATISFIED 14 days early.** 5 `status:rejected` entries logged (4 STRONG by Bonferroni, 1 WEAK). Logged 2026-05-02, well within the 2026-05-15 deadline.

**Tier B (CONDITION-1 paper-launch gate): NOT SATISFIED.** 6/10 after Bet #2 (tas_ceiling_4h) contributed 1 additional rejection. Gap = 4. Lines 1–22 of trials.jsonl contain zero prior `status:rejected` entries; all 6 rejections are from this wave.

**R7 inverted trigger: NOT fired.** fred_carry_stripped OOS-2022 Sharpe collapsed from carry_fred's 0.80 to 0.07464 (confirmed: trials.jsonl trial b7d1a65a; dominance_benchmarks.json). The carry thesis is **VALIDATED**: regime conditioning IS the load-bearing alpha source. Stripping the BoJ-divergence regime filter reduced Sharpe by 0.725 — matching the unfiltered dominance benchmark exactly (carry_fred OOS-2022 = 0.07464). This confirms the regime-conditional design functions as intended. CRO has revised Bet #1 paper-launch sizing accordingly (Section 4).

**Per-trial summary:** 5 archived baseline strategies REJECTED + 1 marginal PASS (momentum, statistically weak, Sharpe margin 0.014 above threshold) + Bet #2 REJECTED. HoQR Phase 2 candidate queue is now exhausted.

**carry_fred OOS-2022 dominance benchmark = 0.07464** — the same strategy in a non-BoJ-divergence period produces no meaningful alpha. This number is a binding input to CRO sizing: the base-case (regime-inactive) expected Sharpe is 0.07, not 0.80. The 0.80 Sharpe is regime-active only.

---

## 3. Per-trial Bonferroni-adjusted classification (≤200 words)

Source: `nht-3d-tier-verification.yaml`. Bonferroni alpha per test = 0.05/6 = 0.0083 applied to DSR (probabilistic gate only; deterministic R1/R3/R6 gates are not p-value tests and are not adjusted).

| Strategy | Trial ID | Sharpe | Key triggers | Bonferroni class |
|---|---|---|---|---|
| ma_crossover | c530be91 | −0.044 | R1, R2-DSR (0.00), R6 (9 trades) | STRONG REJECT |
| momentum | 87fa1d23 | 0.314 | None fired | WEAK PASS |
| bollinger_rsi | ade58943 | −0.343 | R1, R2-DSR (0.00), R3-MaxDD (30.8%), R6 | STRONG REJECT |
| carry_baseline | 5d18776d | 0.284 | R1 (vs 0.50 strategy override), R6 (7 trades) | STRONG REJECT |
| carry_momentum | 6a56df9c | 0.197 | R1 (vs 0.50 override), R6 (16 trades); DSR=0.989 passes R2 | WEAK REJECT |
| fred_carry_stripped | b7d1a65a | 0.075 | R1, R2-DSR (0.367), R6 (7 trades) | STRONG REJECT |
| tas_ceiling_4h (Bet #2) | ab6f4167 | −0.245 | BET2-T1, R1, R2-DSR (0.00), R3-MaxDD (62.9%) | REJECT |

carry_momentum note: dsr=0.989 is a near-pass on signal quality; rejection driven by magnitude and trade count, not by noise. Most information-rich rejection in the batch.

---

## 4. CRO Wave-4 revised Bet #1 sizing (verbatim binding constraints)

Source: `cro-bet1-sizing-revision.yaml`. All constraints are binding from the moment any Bet #1 paper trade is authorized.

- **BC-1 (regime-inactive no-trade):** size_multiplier for Bet #1 = 0.0 when BoJ-divergence regime flag is FALSE; zero positions permitted when regime is inactive.
- **BC-2 (regime-active sizing):** size_multiplier for Bet #1 = 0.25 (not 0.5) when BoJ-divergence regime flag is TRUE; this is the product of the inherited Phase-1 envelope (0.5) multiplied by a 0.5 regime-concentration haircut, because the validated 0.80 Sharpe is concentrated in a single identified regime — applying the full 0.5 envelope to a regime-conditional strategy with only 7 OOS trades is insufficient evidence for full sizing.
- **BC-3 (CF-T9 pre-launch gate):** CF-T9 monitor MUST be deployed and emitting a heartbeat signal (minimum 1 heartbeat per 5-minute window, logged to a persistent audit file) BEFORE any paper trade is placed; launch is blocked until this is verified by CTO sign-off.
- **BC-4 (CF-T9 cold-start gate):** CF-T9 must have emitted at least 10 regime-flag readings (both TRUE and FALSE values observed at least once each) before the first trade is permitted; a monitor that has only seen one regime state cannot be considered validated.
- **BC-5 (CF-T9 heartbeat failure action):** If CF-T9 emits no heartbeat for >5 consecutive minutes, all NEW Bet #1 trades are halted immediately; existing open Bet #1 positions are NOT automatically unwound but are flagged for human review within 30 minutes.
- **BC-6 (regime-flag mid-trade deactivation):** If regime flag transitions from TRUE to FALSE while a Bet #1 position is open, the position is exited at the next daily signal bar (not immediately intrabar); this prevents flash-crash forced exits while enforcing the regime discipline on a meaningful horizon.
- **BC-7 (n_trades minimum before regime-sizing):** The 7-trade OOS count (trials.jsonl b7d1a65a) is insufficient for statistical confidence; Bet #1 must accumulate ≥ 20 paper trades under active regime before any upward size revision above 0.25x is considered.
- **BC-8 (JPY correlation cap, inherited):** Bet #1 JPY-correlated notional must remain ≤ 15% of total book notional (inherited Phase-1 envelope max_correlated_exposure_pct = 0.15); this is binding regardless of regime state.

Inherited Phase-1 envelope remains binding in full. BC-9 (pre-reg gap structural block) is addressed as Section 5 blocker.

---

## 5. CF-T9 documentation gap — paper-launch blocker

This is a structural blocker, not a disagreement. Implementation and documentation status are distinct.

**Implementation EXISTS (commit 61ea022):**
- `scripts/monitor_regime_triggers.py` — 396 lines, CF-T9 monitor logic
- `tests/scripts/test_cf_t9_monitor.py` — 200 lines, test coverage
- `scripts/auto_retire_on_trigger.py` — reads `data/cf_t9_status.json`, recognizes `monitor_id: CF-T9`, triggers retirement

**Pre-reg DOCUMENTATION incomplete:**
- `references/pre-registrations/carry_fred.md` lists CF-T1 through CF-T8 only
- The CF-T9 amendment referenced in the CONSENSUS 2026-04-26 governance record and in the monitor docstring was never inserted into the pre-reg file itself

**Why this blocks:** Per CRO binding constraint BC-3 and the Phase-1 principle that the pre-reg is source of truth for kill-switch thresholds, the pre-reg file must contain CF-T9 before any paper launch. The implementation being correct is necessary but not sufficient.

**Resolution (Phase 2.5 amendment task):**
1. HoQR authors CF-T9 amendment text into `references/pre-registrations/carry_fred.md` mirroring the CONSENSUS 2026-04-26 amendment definition from the monitor docstring
2. Create paired sidecar `references/pre-registrations/carry_fred.triggers.yaml` with a CF-T9 entry
3. NHT co-signs: formal sign-off appended to the carry_fred.md Approval section
4. HoQR + NHT co-sign recorded in a Phase 2.5 governance artifact

---

## 6. Phase 2 known knowledge gaps — for the record

- **BET2-T2/T3/T6 unimplemented:** metrics `n_negative_pair_sharpes`, `cost_stress_sharpe`, `avg_trade_hold_bars` were not computed by the current harness. Advisory only — BET2-T1 fired decisively (Sharpe −0.245). Track as harness extension for future Bet #2 variants.
- **Bet #2 A1-2 two-author rule unresolved:** QD operated under an implied HoQR Wave-4 waiver. The A1-2 prerequisite (canonical reference script from different author) and BET2-T4 comparison remain unresolved. Moot for this REJECT outcome; blocks any future Bet #2 resurrection.
- **4H data provenance:** data/processed/ and data/processed_synthetic_phase0/ provenance not independently verified. Track as data-discipline item.
- **Pre-existing narrative field references** in trials.jsonl lines 15/18/20 (broker name mentions, pre-Phase-2 era). Tracked separately; no impact on trial verdicts.

---

## 7. Disagreement matrix — none material this consensus

All Wave-2 and Wave-4 artifacts converged on trial verdicts and Tier A/B status. CRO's BC-9 framing ("CF-T9 does not exist") was corrected by orchestrator evidence to "implementation exists; documentation gap" — this is preserved as a structural finding in Section 5, not a disagreement between roles. The CRO artifact correctly identifies the pre-reg absence; the orchestrator-supplied evidence adds that the implementation is already present. Both are true simultaneously.

The only structural divergence is the NHT dissent in Section 8, preserved verbatim per protocol.

---

## 8. NHT dissent (VERBATIM — APPEND-ONLY — DO NOT EDIT)

Per fintech-org rule 6, the following dissent is structurally preserved from `.agent-accountability/dissents/phase2-3d-tier-verification:null-hypothesis-tester.yaml`, field `dissent_text`. It is append-only and cannot be erased or paraphrased.

> Three items requiring CEO acknowledgement, preserved verbatim from
> nht-3d-tier-verification.yaml:
>
> (1) momentum WEAK PASS — sizing constraint:
> Sharpe 0.314 vs threshold 0.30 (margin 0.014). Bonferroni-adjusted family-wise
> alpha = 0.05/6 ≈ 0.008. momentum cleared the universal R1 floor by less than
> 1% of the threshold value. With n=520 OOS-2022 daily bars and N=28 org-wide
> trials at write time, this is a spurious survivor in the statistical sense.
> If momentum is ever paper-launched, sizing must reflect that this is a
> statistically-indistinguishable-from-noise survivor, not a validated alpha.
> Position size cap: 0.5x normal allocation maximum.
>
> (2) carry_fred regime-inactive sizing floor — paper-launch base-case:
> carry_fred OOS-2022 dominance benchmark = 0.07464. The validated Bet #1 OOS
> Sharpe of 0.80 was achieved on the post-2024 BoJ-divergence regime window
> exclusively. On OOS-2022 (USD-tightening + BoJ-YCC-stress regime, distinct
> from the validated regime), the same strategy produces ~0.07 Sharpe. The
> regime conditioning IS the edge. Without the regime filter active and live
> (CF-T9 monitor), Bet #1 produces no alpha.
>
> Paper-launch sizing implications:
> - Base-case (regime-inactive) expected Sharpe = 0.07 (not 0.80)
> - CF-T9 monitor MUST be active and validated before first bar
> - If CF-T9 fails or regime-flag goes inactive: Bet #1 must halt, not
>   continue trading at zero alpha while accruing transaction costs
> - Position size cap should reflect regime-conditional expected return,
>   not validation-window expected return
>
> (3) CONDITION-1 gap — Tier B not satisfied:
> trials.jsonl now contains 5 status:rejected entries. CONDITION-1 requires
> ≥10. Gap = 5. Paper-launch authorization remains blocked per CONSENSUS_2026-
> 04-28.md. The HoQR queue from Phase 2 is exhausted (only Bet #2
> tas_ceiling_4h remains, adding at most 1 to the count). Three paths to close
> the gap, all requiring new dispatch:
> - (a) HoQR re-dispatch with new candidate strategies (Phase 2.5 queue)
> - (b) Lower the Tier B bar via new CONSENSUS revision
> - (c) Accept Tier A as sufficient for limited-sizing paper launch
>
> None of (a)/(b)/(c) is automatic. CEO and HoQR jointly decide via
> CONSENSUS_2026-05-01_phase2_closure.md.
>
> OVERALL: Phase 2 succeeded at the strategic question (R7 inverted NOT fired
> → carry thesis validated). Phase 2 produced honest negative results for 4
> archived baselines and a borderline survivor. The carry_fred OOS-2022 = 0.07
> finding is the most consequential Phase 2 datapoint — it does not falsify
> Bet #1 (which is regime-conditional by design) but it does CONSTRAIN how
> Bet #1 should be sized and operated in paper. Paper launch on Bet #1 with
> the 0.80-Sharpe expectation would be a category error.

*CEO acknowledgement on file: ratified via 'continue' reply 2026-05-01T08:45:00Z, explicitly accepting all 3 dissent items as binding sizing/operational constraints. Source: `.agent-accountability/dissents/phase2-3d-tier-verification:null-hypothesis-tester.yaml` field `ceo_acknowledgement`.*

---

## 9. Wave-5 paper-launch readiness — VERDICT: BLOCKED

Three independent blockers. All three must close before any paper-launch authorization. Closing two of three is not sufficient.

**Blocker 1 — Tier B / CONDITION-1 gap:** 6/10 rejections recorded; 4 more independent OOS rejections required. HoQR Phase 2 queue is exhausted (Bet #2 contributed the 6th). Requires HoQR re-dispatch (Phase 2.5 candidate queue) OR a new CONSENSUS explicitly revising the Tier B threshold downward with NHT sign-off.

**Blocker 2 — CF-T9 pre-reg amendment:** Per Section 5. The pre-reg file `references/pre-registrations/carry_fred.md` must be amended with CF-T9 text, co-signed by HoQR and NHT, and a paired sidecar created. Implementation already exists; documentation is the missing piece.

**Blocker 3 — CRO sizing constraints not wired into paper-trading loop:** The 0.0/0.25 regime-conditional size_multiplier from CRO Wave-4 (Section 4, BC-1/BC-2) must be implemented in the actual paper-trading entry point (`scripts/run_paper_trading_vt.py` or equivalent) before any Bet #1 dispatch. Currently carry_fred.py has no regime-filter wiring and would default to 1.0x sizing — a direct violation of BC-1 and BC-2.

**Pre-existing Phase-1 modules not yet wired (Wave-5 prerequisites):** Aggregation gate and heartbeat watchdog exist as modules but are not integrated into the paper-trading loop. These must be wired before any paper run, per Phase-1 binding commitments.

---

## 10. Recommended Wave-5 dispatch sequence

Conditional on CEO ratifying this closure. Steps are partially parallelizable; dependencies noted.

- **5a (HoQR + QD):** Phase 2.5 amendment of `references/pre-registrations/carry_fred.md` to add CF-T9 (with paired `carry_fred.triggers.yaml` sidecar). Closes Blocker 2. HoQR authors; NHT co-signs; QD creates the sidecar file.
- **5b (HoQR):** Phase 2.5 candidate-queue extension — propose ≥5 new falsification candidates to close the Tier B gap (4 needed; buffer of 1). Candidates may include cost-stress reruns on new OOS windows or genuinely novel hypotheses (e.g., bond-FX co-movement, G10 implied-vol term structure, cross-asset momentum). Each requires pre-reg before QD runs the trial.
- **5c (QD, after 5a + 5b pre-regs filed):** Run the new candidate trials via the existing entry point; record verdicts in trials.jsonl. Apply Bonferroni across the new family.
- **5d (QD, parallel with 5b/5c):** Wire CRO Wave-4 sizing constraints (BC-1/BC-2/BC-3 through BC-8) and Phase-1 modules (aggregation gate, heartbeat watchdog) into `scripts/run_paper_trading_vt.py`. Closes Blocker 3 and the Phase-1 wiring prerequisite. Requires CTO review before merge.
- **5e (NHT, after 5c complete):** Re-verify Tier B with new trials; apply Bonferroni across the extended family; update CONDITION-1 count.
- **5f (PM + CEO):** Only if 5a + 5b + 5c + 5d + 5e all clear with no new blockers, draft a paper-launch authorization consensus. This step cannot be pre-authorized; it requires a fresh PM synthesis of 5a–5e outputs.

---

## 11. Signatures

- **Head of Quant Research** — signed via Wave-2 prioritization artifact (`hoqr-prioritization.yaml`) + Wave-3 sub-wave 3c.3 Bet #2 outcome
- **Null-Hypothesis Tester** — signed via Wave-2 frozen rubric (`nht-frozen-thresholds.yaml`) + Wave-3 3b OOS-2022 sign-off (`nht-oos-2022-signoff.yaml`) + Wave-3 3d Tier A/B + Bonferroni verification (`nht-3d-tier-verification.yaml`) + DISSENT (Section 8)
- **CRO** — Wave-4 re-entry: decision = size-reduced (`cro-bet1-sizing-revision.yaml`); blocker on CF-T9 pre-reg amendment structurally preserved
- **Quant Developer** — sub-waves 3a / 3b / 3c.1 / 3c.1.1 / 3c.2 / 3c.3 implementation and execution reports
- **PM** — drafted this closure; PM autonomous authorization recorded in `.agent-accountability/ratifications/phase2-3d-tier-verification.yaml` field `pm_autonomous_authorization_2026-05-01`
- **CTO** — absent for Phase 2 (Phase-1 architecture closed; no architecture re-decisions in scope for this wave; required for 5d merge review in Wave-5)

---

## 12. CEO ratification gate

Final approval required. CEO must explicitly acknowledge all three items:

1. **Paper launch is BLOCKED** on the 3 conditions in Section 9; no partial or provisional paper launch is authorized until all 3 blockers are resolved.
2. **Authorize Wave-5 dispatch sequence** in Section 10 (or propose revisions to it); this authorizes HoQR to begin 5b candidate queue and QD to begin 5d wiring work in parallel.
3. **Acknowledge NHT dissent verbatim** in Section 8 — specifically: momentum 0.5x sizing cap, Bet #1 base-case Sharpe 0.07 (not 0.80), and CONDITION-1 gap = 4 remaining.

CEO acknowledgement of the NHT 3-item gate from the Wave-3 'continue' reply (2026-05-01T08:45:00Z) is noted but does not substitute for ratification of this full closure document, which incorporates the additional Wave-4 CRO findings and the CF-T9 documentation gap.

---

**File path:** `docs/decisions/CONSENSUS_2026-05-01_phase2_closure.md`
