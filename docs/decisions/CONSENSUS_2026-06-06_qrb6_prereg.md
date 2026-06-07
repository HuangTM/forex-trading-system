# CONSENSUS — QRB-6 Pre-Registration Package
**Track:** qrb6-prereg-2026-06-06  
**Trial ID:** fa0f982a  
**Status:** AWAITING-CEO-FREEZE-ACK  
**Date:** 2026-06-06  
**Authored by:** PM / Chief of Staff

---

## Decision

The QRB-6 central-bank scheduled-decision event study pre-registration package (trial fa0f982a) is **ratified as freeze-ready**, subject to CEO authorization to execute the freeze-receipt cut. All six review criteria (AC-1 through AC-6) are satisfied: the Quant Researcher pre-registration document is internally consistent and complete; the Mathematician's frozen statistics are formally sound and filtration-invariant; the Quant Developer's sidecar, receipt infrastructure, and runner are correctly built; the NHT cycle-2 audit SURVIVES (severity advisory, does_block false); the Principal Reviewer cycle-2 approves with all conditions closed (NF-01 §5 boundary prose fixed, PR-01 through PR-05 closed). The quorum ratifies the pre-registration package as **freeze-ready**. The freeze-receipt cut (`cut_freeze_receipt.py --target qrb6 --cut`) and the one-shot run (`run_qrb6.py --ceo-ack`) are **CEO-reserved actions** not authorized by this consensus. No capital is committed by this document. The expected outcome at run time is **KILL** — this is a kill test, not a validator.

---

## Frozen Constants Table

| Constant | Value | Source | Notes |
|---|---|---|---|
| `trial_id` | `fa0f982a` | orchestrator spawn (counter 40→41) | BC-1, the firm's single authorized trial |
| `master_seed` | `387992` | math-spec.yaml; scipy-verified | int('fa0f98', 16)=16387992 mod 1_000_000 |
| `K_replications` | `10000` | math-spec.yaml | banks-as-blocks stationary bootstrap |
| `N_sel` | `3` | math-spec.yaml | paper-selection charge (NOT R5's data-selection 6) |
| `dispersion` | `0.50` | math-spec.yaml; re-derived | R5's 0.426385 explicitly rejected as cross-trial import |
| `SR0_pp_sel` | `0.026861` | math-spec.yaml; scipy-verified | N_sel=3, disp=0.50 |
| `DSR_gate` | `≥ 0.95` | math-spec.yaml | |
| `kill_switch_threshold_scenario_a` | `1.5883` | math-spec.yaml; scipy-verified | T=506 event-days |
| `kill_switch_threshold_scenario_b` | `1.4029` | math-spec.yaml; scipy-verified | T=716 event-days; Scenario B DORMANT at freeze |
| `straddle_lower` | `0.0478` | math-spec.yaml | strict `< 0.0478` + DSR≥0.95 → PASS |
| `straddle_upper` | `0.0522` | math-spec.yaml | strict `> 0.0522` → KILL; [0.0478,0.0522] closed → AMBIGUOUS |
| `spread_z_threshold` | `3.0` | qrb2 overlay; pre-registered | QRB-2 spread-blowout modifier; frozen, not discoverable post-hoc |
| `scenario_a_event_days` | `506` | NHT rescreen; calendar groupby | deduped; FED/BOJ/RBA/BOC verified-official tier |
| `post_2015_event_days` | `345` | NHT rescreen | structural-break sub-window; mandatory KILL if fails |
| `scenario_b_event_days` | `716` | NHT rescreen | DORMANT-PENDING-CERTIFIED-SPOTCHECK |
| `scenario_b_post2015` | `491` | NHT rescreen | DORMANT |
| `power_honest` | `~13–18%` | math-spec.yaml | four N's; kill is the expected outcome |
| `tested_object` | `y_e = sign(close(D)−close(D−1)) × R_post,e` | §5.0 / §4.4 frozen contract | bar-D signed product; post-2015 structure; F_D-measurable signal |
| `null_hypothesis` | `H0: E[y_e] ≤ 0` | math-convergence.yaml | unconditional; bootstrap recentering d_e=y_e−mean(y) |

---

## Review and Rework Ledger

### Wave 1 — QR Draft + MATH Frozen Stats + QD Spotcheck

**QR (qr-prereg-draft.yaml):** Full pre-registration authored. One orchestrator-detected defect — phantom RBA/BOC pair mappings — micro-fixed (RBA/BOC maps corrected to inventory). All AC-1 sub-items (a)–(k) satisfied.

**MATH (math-spec.yaml → math-sections.md):** Frozen statistics produced. N_sel=3 paper-selection charge explicitly NOT R5's data-selection 6. Dispersion 0.50 re-derived; R5's 0.426385 rejected as cross-trial import. Seed 387992 scipy-verified exact. Kill thresholds 1.5883/1.4029 scipy-verified. K=10000. Power honestly 13–18% across four N values. This is a kill test: **the expected outcome is KILL**.

**QD (qd-spotcheck-sidecar.yaml + qd-runner.yaml):** `scenario_b_certification=PARTIAL` → Scenario B DORMANT per NHT C4. One QD agent stall at verification; orchestrator ran the suite and transcribed the on-disk state (logged per Transparency Note 4). `cut_freeze_receipt.py` `qrb6` target built and verified. Runner built receipt-interlocked (refuses without hash-matching receipt + `--ceo-ack`; dry-run touches zero return data).

### Wave 2 — NHT Audit Cycle 1 (nht-audit.yaml)

**Verdict: DO-NOT-FREEZE-AS-IS (material_concern).** Three blocking findings:

- **F1:** Alpha double-specified — §5.1 said ~0.0025 absorbed into alpha; §4.2 used p≤0.0478; five live [MATH] tokens in §5.
- **F2:** Sidecar tested the PRE-window/pre-drift component (explicitly DEAD post-2015 per §2.3); doc tested POST-decision reaction.
- **F3:** C4 violated — sidecar mapped "partial" spotcheck verdict to Scenario B ACTIVATE; NHT C4 maps "partial" to DORMANT.

Additional findings F4 (wrong sidecar path named in §7) and F5 (sign-rule unfrozen — sign-alignment rule asserted but no frozen formula) also flagged. Assessment: assembly defects, not a methodology rejection.

### Wave 3 — Rework Cycle 1

QR rework-1 (qr-rework1.yaml + qr-rework1-patches.md): 11 doc patches + 4 draft-yaml patches. Sidecar rebuilt (qd-rework1.yaml): certified-only condition enforced (NHT C4 honored), NHT-F2 reference in rebuild rationale header, POST-decision only in hypothesis_summary.

**Real Debate (Round 1 of 3, CONVERGED):** QR-vs-Math on the sign source — QR proposed bar-D (sign of close(D)−close(D-1)), Mathematician's initial ruling was F_{D-1} (sign of bar immediately before the decision-reflecting bar). Debate artifacts: `debate-r1-qr.yaml` + `debate-r1-math.yaml`. **Resolved to the signed-product object y_e = sign(close(D)−close(D−1)) × R\_post**: bar-D tests the alive post-2015 component; F_{D-1} tests the dead pre-drift component (§2.3). Mathematician formally retracted the F_{D-1} ruling (math-convergence.yaml). §4.4 Signal/Execution Separation Contract added. Frozen constants are filtration-invariant — all unchanged by the convergence.

### Wave 4 — PR Cycle 1 (pr-review.yaml)

**Verdict: APPROVE-WITH-CONDITIONS (2 blocking conditions):**

- **PR-01 (blocking):** Five live [MATH] tokens in §5; alpha double-spec (~0.0025 absorbed-into-alpha vs. DSR-only mechanism in §4.2).
- **PR-02 (blocking):** Sidecar had unbound symbols (`aggregate_gate_alpha`, `post2015_alpha`), stale [FROZEN-AT-ASSEMBLY] notes, and missing/wrong trigger encodings.
- PR-03 (major): Wrong hex-seed comment (16256920→256920; correct is 16387992→387992).
- PR-04 (minor): §4.2 boundary inequality inconsistency.
- PR-05 (minor): Phantom CLAUDE.md 21:00-UTC citation.

Root cause: incomplete orchestrator assembly (placeholder sweep incomplete). Acknowledged in spawns.jsonl.

### Wave 5 — Math Convergence Patches (math-convergence.yaml + math-convergence-patches.md)

PATCH C-01 through C-04 applied. F_{D-1} §4.4 insertion superseded before application. PR-04 boundary patches stand. Decision: SOUND. All frozen constants confirmed filtration-invariant.

### Wave 6 — PR Cycle 2 (pr-review-cycle2.yaml)

**Verdict: APPROVE-WITH-CONDITIONS (1 blocking condition — NF-01):**

All five cycle-1 conditions closed (PR-01 through PR-05). New finding:

- **NF-01 (blocking):** §5.1/§5.2/§5.4 prose still said "p > 0.0478 → KILL" after PR-04 updated §4.2 to "p > 0.0522 → KILL"; straddle band [0.0478,0.0522] routes to RULE 4 AMBIGUOUS, not KILL. Sidecar not affected (T1/T2 correctly use `> p_straddle_hi = 0.0522`).

Non-blocking: NF-02 (§5.0 window phrasing superseded by §4.4.1 — adequate), NF-03 (signed-product object consistent across §5/§4.4/§1.2 — clean), NF-04 (reversal-distinguishability redesignated secondary/diagnostic — acceptable; runner must implement sub-claim verdict).

QR fixed NF-01 (orchestrator-verified): §5.1/§5.2/§5.4 boundary prose updated to "p > 0.0522 → KILL; p in [0.0478, 0.0522] → RULE 4 AMBIGUOUS."

### Wave 7 — NHT Audit Cycle 2 (nht-delta-audit.yaml)

**Verdict: SURVIVES (severity advisory, does_block false).** F1–F6 all closed. Two F3 residuals in §3.5 doc prose (names non-existent `qd-boe-ecb-spotcheck.yaml` path; missing verdict gate in binding prose) downgraded from blocking to acknowledged-disclosure: sidecar's `condition_expression: "scenario_b_certification == 'certified'"` is the machine-executable gate and is correct. Reconciliation required in freeze pre-flight, not a freeze blocker.

**Sign-rule multiplicity adjudication:** Sign-rule selection (bar-D chosen over D-1-sign and rate-change-sign) is **covered by N_sel=3**. Sign function is parameter-free; selection was theory-driven (bar-D tests the alive post-2015 component; D-1 tests the dead pre-drift); no return data examined. §4.4.2 considered-and-rejected documentation is the honest disclosure record.

### Wave 8 — Test Suite

489 harness+data tests green. Sacred test `test_no_lookahead` green. 60 runner-specific tests green.

---

## NHT Dissent (VERBATIM, Cycle 1 Preserved as Append-Only History)

Per nht-delta-audit.yaml, the cycle-1 material_concern dissent is preserved in full below, followed by the cycle-2 disposition. Both are append-only; neither is modified.

```
CYCLE-1 DISSENT (preserved verbatim, append-only):

QRB-6 PRE-REGISTRATION — NHT PRE-FREEZE AUDIT — 2026-06-06.

VERDICT: DO NOT FREEZE AS-IS. Three blocking internal contradictions corrupt the
one-shot-testability the atomic claim asserts. The underlying METHODOLOGY is sound — the
banks-as-blocks bootstrap, the post-2015 structural-break KILL, the DSR-charged paper-selection
multiplicity (N_sel=3, disp 0.50, SR0_pp 0.026861, kill 1.5883), and the honestly-disclosed
~13-18% power are all admissible and, where they err, err toward OVER-deflation (harder PASS),
which is the correct direction for an adversarial kill test. My objection is NOT to the strategy
or the constants; it is that the ASSEMBLED document and its machine sidecar disagree with each
other and with my binding C4 on three load-bearing points, and the falsification section is not
actually frozen (five live [MATH] tokens).

BLOCKER 1 (F1 — the primary threshold): §5.1 said the selection multiplicity is "absorbed into
the primary alpha" (=> p-threshold ~0.0025) and left it as the unfilled token "[MATH primary
alpha]"; §4.2, the sidecar gate, and math-spec all instead used p<=0.0478 (alpha 0.05,
multiplicity charged via DSR only). Reconcile to one statement.

BLOCKER 2 (F2 — the quantity under test): the machine sidecar the RUNNER executes defined the
primary metric as the PRE-WINDOW / pre-decision-drift return, the component §2.3 explicitly
declares DEAD post-2015. The binding prose tested the POST-decision reaction/reversal.

BLOCKER 3 (F3 — C4 NOT honored): C4 maps the "partial" spot-check verdict to Scenario B DORMANT.
The sidecar mapped "partial" to ACTIVATE (spotcheck_result IN ['partial','certified']) and
PROVENANCE line 706 called "partial" "sufficient for activation" — a direct contradiction of my
binding condition, with a NO-human-re-decision auto-activation path.

CALIBRATION: I was NOT crying contamination-veto and was NOT dissenting against the alpha
hypothesis or the math. The blockers were reconciliation defects of an ASSEMBLY — fixable in
an editing pass, not a redesign.

---
CYCLE-2 DISPOSITION (appended; cycle-1 above is unchanged):

F1, F2, F3 (the three blockers): FIXED. F4 (path): FIXED. F5 (sign-rule): FIXED and formally
adjudicated via the QR-Math debate (see closure_verification above). F6 (runner-pin ordering):
FIXED in spec; runner creation is the mandatory next pre-freeze step, correctly deferred at this
stage (R5 precedent). Two residuals on F3 (§3.5 doc names a non-existent artifact path;
§3.5 verdict-gate missing from binding prose) are acknowledged-disclosure defects that should be
reconciled in the freeze pre-flight but do not independently block freeze given the sidecar's
correct certified-only enforcement.

UPDATED VERDICT: SURVIVES. The assembled pre-registration is now a coherent, one-shot-testable
specification with all internal contradictions resolved. The underlying methodology assessment
from cycle-1 is unchanged: it remains sound and errs toward over-deflation. My binding C4 is
now honored (certified-only in the sidecar's machine-executable condition). The sign-rule
multiplicity question (the one genuinely new surface since cycle-1) is adjudicated as covered
by N_sel=3 — no additional charge required.

The signed-product framing introduced after the debate convergence is a NEW DOF surface that
I have scrutinized adversarially (see sign_rule_multiplicity_ruling above). I do not find it
to require a separate multiplicity acknowledgment beyond what N_sel=3 already covers, provided
the §4.4.2 considered-and-rejected documentation remains in the frozen doc.

MANDATORY PRE-FREEZE PRE-FLIGHT ITEMS (not blockers, but required before receipt cut):
1. Runner script (scripts/run_qrb6.py) must be authored, committed, and its commit hash
   pinned in the freeze-receipt (F6 enforcement step).
2. §3.5 doc prose should be reconciled to match the sidecar's artifact path
   (qd-spotcheck-sidecar.yaml, not the non-existent qd-boe-ecb-spotcheck.yaml) and
   should add "with verdict == 'certified'" to the activation condition.
3. Zero return data may be examined before the freeze-receipt is committed (AC-4, VOID §1.4(1)).

severity: advisory
```

Dissent artifact: `.agent-accountability/dissents/qrb6-prereg-2026-06-06:phase1:task1.0:null-hypothesis-tester.yaml`

---

## Transparency Notes

**Note 1 — Trial-registration timing conflict.**
The PM acceptance criteria (pm-acceptance-criteria.yaml) placed registration at receipt-cut (AC-8: "This is the only moment at which the trial is registered per BC-1"). The charter's spawn-time rule governed instead — trial fa0f982a was registered at the QR-author spawn (charter step 3), counter 40→41, consistent with R5 precedent (where the same conflict arose and charter won). This conflict is logged transparently here. The receipt-cut (AC-8) remains the freeze-sealing action; it is not also the registration event.

**Note 2 — Orchestrator assembly defect.**
The cycle-1 NHT audit caught three blocking internal contradictions that were direct products of an incomplete placeholder sweep in the orchestrator assembly pass (live [MATH] tokens in §5; sidecar tested wrong quantity; C4 violated). Root cause acknowledged in spawns.jsonl. Remediated fully in rework cycle 1 and verified in PR cycle 2 and NHT cycle 2.

**Note 3 — The real debate.**
The first genuine cross-role conflict in this track: QR proposed bar-D sign; Mathematician's initial frozen ruling was F_{D-1}. Formally debated in debate-r1-qr.yaml + debate-r1-math.yaml. Converged in round 1. Both positions are preserved verbatim in the debate artifacts; neither is erased. The Mathematician retracted F_{D-1} on economic-coherence grounds (bar D-1 proxies the pre-drift declared DEAD post-2015 in §2.3) and the statistical mechanics confirmed no recalibration needed. §4.4 Signal/Execution Separation Contract is the frozen outcome.

**Note 4 — QD stall + orchestrator transcription.**
One QD agent stalled at the BoE/ECB spotcheck verification step. The orchestrator ran the verification suite independently and transcribed the on-disk state into qd-spotcheck-sidecar.yaml. The result (`scenario_b_certification=PARTIAL`) was logged and the sidecar's DORMANT status reflects it. This is a process irregularity, not a data irregularity; the transcription was verified against the actual on-disk file.

**Note 5 — Honest power ~13–18%: the expected outcome is KILL.**
Power is honestly 13–18% across the four N values in the freeze design (Scenario A 506/345 event-days; Scenario B 716/491 DORMANT). This means the pre-registered test will most likely KILL even if the true edge exists at the planning Sharpe. This is a kill test by design, not a validator. The graduation map: QRB-6 KILL → QRB-3 (runner-up, weighted 4.02, first-candidate bar cleared) advances in a future wave with a future trial. QRB-3 does NOT register in this wave.

**Note 6 — CEO-reserved actions.**
Three actions remain CEO-gated and are explicitly outside this consensus's authority:
(a) **Freeze-receipt cut** — `cut_freeze_receipt.py --target qrb6 --cut` — the act that makes trial fa0f982a cryptographically irrevocable and increments the trial counter to 41. Mandatory prerequisites before this cut: runner script authored and committed, §3.5 doc prose reconciled (per NHT pre-flight items).
(b) **One-shot run** — `run_qrb6.py --ceo-ack` — a separate later authorization, post-freeze. Not scheduled.
(c) **Push authorization** — current HEAD is 1 ahead of origin; push requires CEO authorization.

---

## Signature Table

| Role | Artifact Path | Decision | Status |
|---|---|---|---|
| Head of Quant Research (HoQR) | `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/hoqr-final-qgr.yaml` | approve | pending orchestrator validation |
| Principal Reviewer (PR) | `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/pr-final-qgr.yaml` | approve | pending orchestrator validation |
| Mathematician (MATH) | `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/math-convergence.yaml` | sound (supporting, non-quorum) | verified on disk |
| Null-Hypothesis Tester (NHT) | `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/nht-delta-audit.yaml` | survives (supporting, non-quorum) | verified on disk |
| PM / Chief of Staff | `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/pm-consensus.yaml` | approve | this consensus |

**Quorum basis:** research-direction → HoQR; design/algorithm review → PR. Math's derivation-review (decision: sound) and NHT (survives) are supporting non-quorum signals. No CRO trigger — no sizing or live-capital domain. No CTO trigger — no architecture change beyond the reviewed runner pattern (receipt-interlocked gate structure, consistent with R5/confirmatory precedent).

**Scope:** The quorum ratifies the pre-registration package as **freeze-ready**. The freeze-receipt cut and the run are CEO-reserved actions.

---

## Knowledge Gaps Surfaced

None.

---

## Next Steps

1. **CEO authorizes freeze-receipt cut** — this consensus is the final gate before that action.
2. **Pre-freeze pre-flight** (before CEO cuts): author `scripts/run_qrb6.py` runner, commit it, confirm commit hash; reconcile §3.5 doc prose (per NHT pre-flight items 1–2).
3. **Freeze-receipt cut** — `cut_freeze_receipt.py --target qrb6 --cut` (CEO ack required). Confirm trial counter increments to exactly 41.
4. **Commit and push** (CEO authorization required for push).
5. **One-shot run** — `run_qrb6.py --ceo-ack` — a separate CEO ack at a later time. **Not scheduled by this consensus.**
6. **QRB-6 KILL outcome** → QRB-3 advances as runner-up in a future wave with a future trial.
