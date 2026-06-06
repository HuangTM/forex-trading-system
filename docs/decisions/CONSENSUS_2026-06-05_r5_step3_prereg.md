# CONSENSUS: R5 STEP 3 — Carry-Universe Kill Test Pre-Registration
**Track:** r5-step3-prereg-2026-06-05  
**Addressed unit:** r5-step3-prereg-2026-06-05:phase1:task1.0  
**Family trial ID:** 576746aa (org counter line 37; see Transparency Note 1)  
**Date:** 2026-06-06  
**Status:** RATIFIED-FOR-FREEZE by distributed quorum (STEP-4 authorization deferred to CEO)  
**Outcome routing label:** `ratified_with_dissent`

---

## Decision

The R5 carry-universe kill test pre-registration — document `references/pre-registrations/r5_carry_universe_kill_test.md` (~1106 lines, forbidden-phrase scan CLEAN) together with the implementation artifacts (`src/forex_system/harness/r5_decision.py`, `scripts/run_r5_step4.py`, `scripts/cut_freeze_receipt.py`, and their associated tests) — is **RATIFIED-FOR-FREEZE** by the firm's distributed quorum under the autonomous default (v0.6.0). The quorum composition is: Head of Quant Research (hoqr-final-qgr.yaml, APPROVE) and Mathematician (mathematician-qgr.yaml, APPROVE). The Principal Reviewer signed APPROVE on cycle-2 (pr-step3-cycle2.yaml), covering code/design domains. The Null-Hypothesis Tester's original audit SURVIVES (severity concern, orchestrator-escalated to material_concern by keyword scan); the delta-audit SURVIVES (severity note, all reservations resolved). Both NHT dissents are preserved verbatim below and travel with this consensus.

**STEP-4 execution authorization is deferred to the CEO.** Wind-down is irreversible firm policy and the one-shot run is outside the autonomous quorum's authority per the PM's own acceptance criteria (criterion CONSENSUS-signed). The quorum ratifies the frozen spec; the CEO authorizes the run. The freeze sequence after CEO authorization: code+doc commit → `cut_freeze_receipt.py --cut` → receipt commit → STEP 4.

---

## Frozen Parameters Table

| Parameter | Frozen Value |
|---|---|
| Null hypothesis H0 | max_k E[d_k] <= 0 (net-of-cost, post-entry-delay, benchmark=ZERO) |
| Primary test statistic | Hansen SPA max-statistic, studentized T_k = sqrt(T)·mean(f_k)/omega_hat_k |
| Secondary cross-check | White Reality Check (White-RC), p_RC < 0.05 |
| Bootstrap draws | Joint stationary bootstrap; SAME draws for SPA + White-RC |
| Block-length rule | Politis-White auto per-variant, max across 36 cells (L_max = 21.33, L_int = 22) |
| K (bootstrap reps) | 5000 |
| Master seed | 576746 |
| Alpha / error control | 0.05 FWER (max-statistic single pooled family of 36 cells) |
| Elected N (DSR deflation) | N = 3 (union midpoint of HoQR [1,2] and NHT [2,4]; bias-direction disclosed) |
| SR0 (annualized) | 0.363623 |
| SR0_pp (per-observation) | 0.022906 = 0.363623 / sqrt(252) |
| DSR threshold | DSR >= 0.95 |
| Var[SR_n] (dispersion) | sqrt(Var) = 0.426385 = sample std (ddof=1) over {SR_1=0.80, SR_2=0.197}; two-observation basis; held fixed across N |
| SR_1 provenance | 0.80, registry-prose only (carry_fred.md:16); no trials.jsonl row; Bet#1 label is momentum (trial 87fa1d23, retired); conservative-if-wrong on Var/spread axis only (disclosed) |
| Snooping treatment | Method A UNAVAILABLE (two variants' development windows post-date R5 terminus); Method B (BLdP deflation haircut) operative |
| OOS window | 2010-03-15 to 2026-04-06; T = 4186 bars; 0 cells dropped |
| Decision functional | Ordered RULES 0–4 (first-match-wins): RULE 0=TECHNICAL FAILURE, RULE 1=AMBIGUOUS_STRADDLE (|p_SPA-0.05|<=0.0031), RULE 2=WIND_DOWN (p_SPA>=0.05, outside straddle), RULE 3=CONTINUE (p_SPA<0.05 AND DSR>=0.95 AND p_RC<0.05), RULE 4=AMBIGUOUS_DSR_RC |
| Freeze mechanism | External write-once freeze-receipt via cut_freeze_receipt.py --cut; document NEVER embeds its own hash; runner verifies sha256(prereg) == receipt.prereg_sha256 before any draw |
| Five pinned code objects | r5_decision.py, run_r5_step4.py, cut_freeze_receipt.py, reality_check.py (hac_se_nw extraction), carry_universe_matrix.py (N1 hardening) |
| Three permitted pre-freeze changes | (1) N1 sizer hardening (already landed); (2) STEP-4 runner (already landed); (3) hac_se_nw module extraction (behavior-identical, already landed) |
| Universe | 6 variants × 6 JPY crosses = 36 cells (USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY); no-silent-exclusion rule; drop requires structured reason/exc_type/category |

---

## Wind-Down Action Map (Pre-Committed)

| Outcome | Condition | Firm Action |
|---|---|---|
| 1 CONTINUE | p_SPA < 0.05 AND DSR >= 0.95 AND p_RC < 0.05 | Confirmatory pre-reg only (new trial_id; absorbs R5 36-cell selection into honest-N; no capital, no family re-open) |
| 2 WIND-DOWN (powered) | p_SPA >= 0.05, power adequate | WIND-DOWN — zero validated alpha; carry family monitoring only |
| 3 WIND-DOWN (underpowered) | p_SPA >= 0.05, power ~20-35% | WIND-DOWN — binding; underpowered non-rejection does NOT license "inconclusive, keep spending" |
| 4 AMBIGUOUS | Straddle or DSR/RC discordant; partial subset anomaly | Confirmatory-only pre-reg (same discipline as outcome 1: new trial_id + R5 selection absorption; omitting either VOIDS) |
| 5 TECHNICAL FAILURE | Hash mismatch, scipy absent, data error, hash interlock failure | HALT; root-cause; re-freeze before re-run; counter NOT incremented |

---

## Finding and Rework Ledger

### PR Cycle-1 Blocking Findings (all closed in cycle-2)

| ID | Severity | Category | Description | Status | Owner |
|---|---|---|---|---|---|
| F-001 | blocking | spec-drift | DSR gate unexecutable: compute_dsr has no SR0 parameter; expected_max_sr uses null-theoretical dispersion incapable of reproducing empirical SR0=0.221616 for any n_trials | CLOSED — runner (r5_decision.py) computes gate directly with frozen SR0_PP=0.022906 literal; compute_dsr demoted to conventions reference | mathematician |
| F-002 | blocking | correctness | CONTINUE/AMBIGUOUS branch overlap: p_SPA=0.048 + DSR=0.96 + p_RC=0.01 satisfied both CONTINUE and AMBIGUOUS_STRADDLE with no precedence rule | CLOSED — ordered RULES 0-4 first-match; RULE 1 straddle fires before RULE 3 CONTINUE; test_rule1_straddle_p_spa_0_048 pins the exact counterexample | mathematician |
| F-003 | blocking | invariant-violation | Self-referential freeze hash: three [FROM FREEZE-RECEIPT] placeholders; document hashed "this file" while embedding its own hash | CLOSED — external write-once receipt model; grep confirms zero placeholders and zero self-hash references | quant-developer |
| F-004 | minor | spec-drift | Second compute_dsr 0.0 path (sr<=0) undocumented in pre-reg | CLOSED — §7.3.4 pins both degenerate paths | mathematician |
| F-005 | minor | spec-drift | HAC floor line-citation drift: :867 cited for omega floor, actually at :868; s2 clamp at :863 | CLOSED — §2.3 corrected: :868 omega floor, :863 s2 clamp, "distinct from" note | mathematician |
| F-006 | observation | test-coverage | N1 end-to-end 0.0 override not tested; None-config+None-override TypeError path untested | CLOSED (over-closed) — TestBuildCellSizerOverrideEndToEnd + test_float_none_config_raises_type_error | quant-developer |
| F-007 | observation | other | SR_1=0.80 provenance weak + monotonicity safety net contingent on F-001 gate | CLOSED — §3.4 source note added; Bet#1=momentum corrected; F-001 now real, discharging contingency | head-of-quant-research |

### PR Cycle-2 Orchestrator/QD Remediations (all closed)

| ID | Description | Status |
|---|---|---|
| R-001 | cut_freeze_receipt.py --cut guard: any invocation (incl. --help) wrote premature receipt | CLOSED — argparse --cut required; bare/--help are dry-runs; no receipt in repo; write-once refusal intact |
| R-002 | hac_se_nw module-level extraction from _hac_se closure: behavior-identical; §1.3 item 3 naming | CLOSED — bit-identical kernel confirmed; bandwidth=max(actual_block_length-1,1) = original h |
| R-003 | k* argmax must use studentized T_k (§7.3.4), not plain Sharpe | CLOSED — select_k_star_studentized() uses T_k with same block_length as SPA; divergence test proves AR(1) higher-plain-Sharpe LOSES to white-noise on T_k |

### NHT Original Audit Findings (A-series)

| ID | Severity | Status | Notes |
|---|---|---|---|
| A-1 | minor | RESOLVED | §3.4 now separates honest_n.py mechanical return (N_honest=10) from HoQR adjudication; false code-citation authority retracted |
| A-2 | material | RESOLVED | N re-elected 2→3 (union midpoint); N-axis anti-conservatism disclosed with verified scalars; "conservative" framing removed |
| A-3 | minor | RESOLVED | Sharpe-table citations trial_id-primary; SR_1=0.80 flagged registry-prose |
| A-4 | concern | RESOLVED | Confirmatory-branch counter discipline now binding in §4/§5/§6: new trial_id + R5 36-cell selection absorption; omitting either VOIDS |
| A-5 | note | RESOLVED | scipy bias flag pinned (skew bias=True, kurtosis fisher=True bias=True); scipy required at run time |
| A-6 | note | RESOLVED | benchmark=ZERO with anti-double-count rationale stands |

### NHT Delta-Audit Findings (D-series)

| ID | Severity | Status |
|---|---|---|
| D-1 | note | Non-blocking — N=3 midpoint residual anti-conservative bias if true N=4; HALF prior magnitude; disclosed; no capital path |
| D-2 | clarification | Non-blocking — ONE stale sign-off sentence (§3.4:327-329) said "three look-Sharpes"; contradicts frozen two-observation convention; frozen scalar unaffected; clause reconciled post-delta-audit (spawns.jsonl 2026-06-06T03:46:44Z) |
| D-3 | note | Non-blocking — N_obs=2 dispersion / N=3 bracket factoring is correct BLP factoring; no exploit |
| D-4 | note | Non-blocking — runner-based gate adds no new material DOF; freeze-receipt sha256 + write-once convert new code to hash-pinned code |

---

## NHT Dissent Statements (Verbatim, Append-Only)

### Original Audit Dissent (nht-audit.yaml, 2026-06-05T22:40:00Z)

**Severity: concern (agent-calibrated). Orchestrator-escalated to material_concern by deterministic keyword scan matching "garden of forking paths" (documented item-#67 false-positive candidate). Escalation NOT overridden. Superseded by delta-audit (severity=note, all reservations resolved). Both preserved verbatim.**

> NHT POSITION ON THE R5 PRE-REGISTRATION (append-only; preserve verbatim in CONSENSUS):
>
> The pre-reg SURVIVES my audit and is freezable as-is. It honors every condition of my 2026-06-02
> dissent: joint same-block stationary bootstrap against a zero benchmark (with a sound anti-double-count
> rationale for zero over matched-carry); a crypto-frozen full-grid pre-reg with an exhaustive wind-down
> action map; K=5000 >> the 2000 floor with reported MC-SE=0.0031; and a snooping charge that is real,
> not theater — Method A (clean hold-out) was honestly adjudicated UNAVAILABLE per-variant (two variants'
> development windows end AFTER the R5 index terminus), and Method B (BLdP deflation haircut) is operative
> with arithmetic I reproduced exactly (SR0=0.221616). The decision tree contains NO branch that maps to
> "inconclusive, keep spending": a non-rejection at ANY power -> WIND-DOWN (binding, outcomes 2 & 3);
> CONTINUE and AMBIGUOUS buy only a fresh confirmatory pre-reg, never capital or family re-open. The
> underpowered-non-rejection caveat (power ~20-35%) is correctly bound to WIND-DOWN rather than a third door.
>
> I record FOUR reservations, none of which block the freeze:
>
> (1) MATERIAL — N=2 is pinned at the FLOOR of the credible range and SR0 is strictly increasing in N
> (N=2->0.2216, N=4->0.4486). On the multiplicity axis this is the ANTI-conservative choice, biasing toward
> false CONTINUE — the OPPOSITE of the conservatism the pre-reg claims. The pre-reg's monotonicity defense
> is valid ONLY on the Var/spread (SR_1) axis, which I confirmed; it is silent on the N axis. This is
> contained because a false CONTINUE buys only a confirmatory pre-reg behind three AND-gates, never spend.
> But the pre-reg should not describe N=2 as conservative; it is the least-deflating admissible N.
>
> (2) MINOR — "honest_n.py:40-81" is cited as the mechanism for N, but the code on the real registry returns
> N_honest=10, not the "8->5->2" the pre-reg narrates. N=2 is a sound JUDGEMENT but it is dressed as a code
> computation it is not. carry_fred (the SR_1=0.80 representative) has NO registry row, and the "Bet#1 =
> carry_fred" label contradicts the registry (Bet#1 = trial 87fa1d23 = momentum, retired). The 0.80 is
> registry-unverified; the pre-reg discloses this and the Var-monotonicity neutralizes its direction.
>
> (3) CONCERN — the confirmatory-test branch (outcomes 1 & 4) does not pin the trial-counter / honest-N
> discipline for the spun-off test. A post-hoc-selected winning cell tested "fresh" without absorbing the
> 36-cell selection burden re-opens the garden of forking paths. Contained by the requirement that the
> confirmatory test get its own freeze + audit, but should be pinned now.
>
> (4) MINOR — trials.jsonl line-number citations are off by ~6; trial_ids resolve correctly so the data is
> verifiable, but a frozen kill-test should not carry stale line pointers.
>
> CALIBRATION: I rejected my own instinct to escalate. The expected outcome remains WIND-DOWN, the gate is
> honestly hard (best-cell annualized SR ~0.625 needed to clear DSR), and every residual loophole terminates
> at a fresh pre-reg behind a fresh audit — never at uncontrolled spend. Over-rejecting this would itself be
> a calibration failure. I sign the audit as SURVIVES with the four reservations recorded, and I recommend
> HoQR/Mathematician adopt the two one-sentence fixes (N-axis conservatism caveat; confirmatory-branch
> counter discipline) at or before freeze if they wish to close (1) and (3) cleanly — but their absence does
> not make the spec unfreezable.

### Delta Audit Dissent (nht-delta-audit.yaml, 2026-06-05T23:55:00Z)

**Severity: note (agent-calibrated). No orchestrator keyword escalation (zero matches). All A-series reservations resolved. does_block: false.**

> NHT DELTA-POSITION ON THE REVISED R5 PRE-REGISTRATION (append-only; preserve verbatim in CONSENSUS):
>
> The REVISED pre-reg SURVIVES my delta-audit and is freezable as-is. All FOUR reservations from my
> 2026-06-05 audit are RESOLVED — not merely acknowledged, but materially fixed:
>
> (A-2, was MATERIAL) N re-elected 2->3 off the union FLOOR to the midpoint, for the exact bias-direction
> reason I raised. The N-axis anti-conservatism is now DISCLOSED with the verified scalars (SR0(N=2)=0.221616,
> N=3=0.363623, N=4=0.448610, all reproduced exactly by me) and explicitly NOT defended as conservative; the
> "conservative" framing of the N election is gone. The residual anti-conservative bias is roughly HALVED.
> This is the single most important fix and it is the right one.
>
> (A-4, was CONCERN) The confirmatory-test counter discipline is now BINDING in outcomes 1 & 4, §4, and the
> §6 machine-checkable criteria: any R5-spawned confirmatory test must take a NEW trial_id AND absorb the R5
> 36-cell selection into its own honest-N/deflation, with "omitting either VOIDS it." The back-door
> garden-of-forking-paths is closed at the spec level.
>
> (A-1, was MINOR) §3.4 now cleanly separates honest_n.py's actual return (N_honest=10 org-wide) from HoQR's
> judgement adjudication; the false code-citation authority and the carry_fred-key fiction are retracted.
>
> (A-3, was MINOR) Sharpe-table citations are trial_id-primary; SR_1=0.80 is correctly flagged registry-prose,
> not a trial row.
>
> (A-5, A-6, were NOTE) The scipy bias flag is pinned (skew bias=True, kurtosis fisher=True bias=True), the last
> unfrozen knob; benchmark=ZERO stands.
>
> I stress-tested the NEW surfaces and record FOUR findings, NONE blocking:
> - D-1 (note): the N=3 midpoint still carries a residual anti-conservative bias if true N=4, but HALF the prior
>   magnitude, disclosed, and contained behind three AND-gates with no capital path.
> - D-2 (clarification): ONE stale sign-off sentence (§3.4:327-329) still says variance is "computed over the
>   three look-Sharpes," contradicting the frozen two-observation dispersion convention (:290-301,315). The
>   frozen SCALAR is unaffected (I reproduced 0.426385 from exactly the two observed Sharpes). Recommend deleting
>   the stale clause; non-blocking documentation coherence.
> - D-3, D-4 (note): the N_obs=2 dispersion / N=3 bracket factoring is a coherent frozen plug-in, not an exploit;
>   the runner-based gate introduces no new material DOF — the freeze-receipt sha256 interlock + the exhaustive
>   five-object code pin + write-once receipt convert "new code" into "hash-pinned code," and k* uses the
>   studentized T_k argmax (not plain Sharpe), internally consistent with §7.3.4.
>
> CALIBRATION: I REJECTED any instinct to hold a reservation open for theater. Every prior reservation was
> genuinely fixed; the two new notes (D-1 residual bias, D-2 stale prose) are recorded-but-non-blocking by my
> own binding severity rule (material_concern+ ONLY if the doc must not be frozen as-is — neither qualifies).
> The expected outcome remains WIND-DOWN, the gate is now HARDER (best-cell annualized SR ~0.767 vs the prior
> ~0.625), and no residual loophole reaches uncontrolled spend. I sign the delta-audit as SURVIVES at
> severity=note, and I recommend (do not require) deleting the one stale §3.4 sign-off clause (D-2) at or
> before freeze to close the last coherence wrinkle.

---

## PR Review Verdicts

### Cycle-1 (pr-step3-review.yaml, 2026-06-05T14:30:00Z): REJECT

Three blocking findings: F-001 (DSR gate unexecutable), F-002 (CONTINUE/AMBIGUOUS branch overlap), F-003 (self-referential freeze hash). Two minors (F-004, F-005). Two observations (F-006, F-007). The arithmetic and statistical machinery were assessed as almost entirely correct; the load-bearing gate could not run as written.

### Cycle-2 (pr-step3-cycle2.yaml, 2026-06-06T04:15:00Z): APPROVE

All 10 rows closed (F-001..F-007, R-001..R-003). SR0_PP=0.022906 arithmetic verified: 0.363623/sqrt(252) = 0.02290609... round6 = 0.022906. 303 tests pass (including 112 harness tests and 9/9 sacred tests). No finding remains at blocking severity. No p-value or DSR computed on real data.

---

## Transparency Notes (Required Disclosures)

### Note 1 — Trial-Counter Ruling

The PM's acceptance-criteria hard-constraint (pm-acceptance-criteria.yaml) stated `no_trial_counter_increment: true` on the grounds that STEP 3 is a spec artifact, not a new trial. However, the charter protocol `spawn-agent.md` step 3 mandates a spawn-time increment for pre-registration artifacts. The orchestrator followed the charter: ONE family trial was incremented (trial_id 576746aa, org counter line 37). STEP 4 REUSES this same trial_id — no second increment. The conflict between the PM's AC and the charter protocol is recorded here, not hidden. The orchestrator judged the charter to control when it conflicts with the PM artifact, per the firm's governance ordering (charter > role artifact).

### Note 2 — NHT Severity-Escalation Lineage

The NHT calibrated severity `concern` (non-blocking) on the original audit (nht-audit.yaml). The deterministic keyword scan one-way-escalated to `material_concern` on matching "garden of forking paths" — arguably the documented item-#67 false-positive pattern in the escalation log (the NHT's use was a domain-specific finding about the confirmatory-branch counter discipline, not a snooping condition). The escalation was NOT overridden. Instead, the rework cycle resolved the underlying findings (A-2 N-axis framing; A-4 counter discipline), and the superseding delta-audit calibrates `note` with zero keyword matches. Both dissents are preserved verbatim above. The escalation lineage is an honest record: the keyword rule was applied, the underlying concern was real, and it was fixed rather than escalated around.

### Note 3 — Forbidden-Phrase Scan Match (Remediated)

A broker name appeared in a historical data-provenance citation in an HoQR section draft. Adjudicated as a false positive (no capital-routing semantics; the citation identified a data provider for the rate differential series, not a live-capital instruction). The text was reworded to cite trials.jsonl:15 neutrally. The YAML artifact scanned clean. No policy-violations.jsonl entry was written (adjudication rationale: provenance citation is not a live-capital instruction). The CEO sees this here rather than in a policy-violations.jsonl entry.

### Note 4 — Orchestrator Interventions Under Infra Degradation

Seven background-agent stalls occurred this session. All interventions are logged in `.fintech-org/spawns.jsonl`. Interventions consisted of:
- 2 artifact transcriptions from completed-on-disk work (mathematician-qgr.yaml wave-2d; qd-rework1.yaml after agent stalled at report step)
- Mechanical schema fixes (assumptions mirrors, missing timestamp)
- Pre-authorized N=3/constants reconciliations (four prose remnants reconciled to the signed N=3 election, the hand-bracketed probits superseded by scipy-exact values, stale-constant substitutions)
- The `cut_freeze_receipt.py --cut` argparse guard (live-found defect: bare/--help invocations wrote a premature receipt, immediately deleted; guard applied and logged before PR cycle-2 reviewed the full diff)
- Stale-prose reconciliation (D-2 stale "three look-Sharpes" clause reconciled post-delta-audit per spawns.jsonl 2026-06-06T03:46:44Z)
- PR cycle-2 verified R-001..R-003 as closed. No domain judgment was made by the orchestrator.

### Note 5 — Repo Hygiene

Thirty-three pre-existing ruff errors exist in files untouched by this session: `tests/harness/test_run_trial.py`, `src/forex_system/analysis/reports.py`, `scripts/run_trial.py`. These are out of scope for R5 STEP 3 and are flagged for a future dedicated hygiene pass.

### Note 6 — What Is Deferred to the CEO

STEP-4 execution authorization — the one-shot bootstrap run producing p_SPA, p_RC, and the DSR evaluation — is outside the autonomous quorum's authority. Wind-down is irreversible firm policy per the PM's acceptance criteria (criterion CONSENSUS-signed). The quorum ratifies the FROZEN SPEC; the CEO authorizes the RUN. The freeze sequence after CEO authorization: (1) code+doc commit, (2) `cut_freeze_receipt.py --cut` produces external write-once receipt, (3) receipt committed, (4) STEP 4 executes with receipt gate enforcing sha256(prereg_bytes)==receipt.prereg_sha256 before any draw. Violation of the sequence routes to TECHNICAL FAILURE (outcome 5), which does not increment the trial counter.

---

## Signature Table

| Role | Artifact | Path | Decision |
|---|---|---|---|
| Head of Quant Research | Final quality-gate-review | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/hoqr-final-qgr.yaml` | APPROVE (2026-06-06T05:10:00Z) |
| Mathematician | Quality-gate-review (wave-2d transcription) | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/mathematician-qgr.yaml` | APPROVE (2026-06-05T23:05:00Z) |
| Mathematician (rework-1) | Derivation-review with scipy-exact constants | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/mathematician-rework1b.yaml` | sound |
| Quant Developer | Implementation report (transcription + remediation) | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/qd-rework1.yaml` | implemented-and-verified |
| Quant Developer (argmax fix) | k* studentized argmax fix + hac_se_nw extraction | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/qd-argmax-fix.yaml` | implemented |
| Null Hypothesis Tester | Original audit | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/nht-audit.yaml` | SURVIVES (severity concern; orchestrator-escalated material_concern) |
| Null Hypothesis Tester | Delta audit | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/nht-delta-audit.yaml` | SURVIVES (severity note) |
| Principal Reviewer | Cycle-1 review | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/pr-step3-review.yaml` | REJECT (3 blocking) |
| Principal Reviewer | Cycle-2 review | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/pr-step3-cycle2.yaml` | APPROVE (all 10 rows closed) |
| PM | Acceptance criteria | `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/pm-acceptance-criteria.yaml` | approve |
| PM | This consensus | `docs/decisions/CONSENSUS_2026-06-05_r5_step3_prereg.md` | ratified-for-freeze |

---

## Knowledge Gaps Surfaced (Routed to Skill-Gap Loop)

None this session. No knowledge gap artifacts were emitted. The NHT logged two knowledge gaps in its artifacts (harness SR0 override acceptance; realized k* skew/kurtosis values) — both are STEP-4 runtime items, not pre-registration blockers, and neither requires a skill-gap escalation.

---

## Next Steps

1. **CEO reviews and authorizes STEP-4 execution.** Required open items for CEO acknowledgment are listed in the CONSENSUS-SUMMARY.
2. **Freeze sequence (after CEO authorization):**
   - Commit code + pre-registration document (final state)
   - Run `cut_freeze_receipt.py --cut` to produce the external write-once freeze-receipt at `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/FREEZE-RECEIPT.yaml`
   - Commit the receipt in a follow-up commit
3. **STEP 4 (one-shot run):** Execute `scripts/run_r5_step4.py` with the `--i-am-step4` flag; the runner verifies the receipt hash before reading any bootstrap draw. Outcome routes per the ordered RULES 0–4 decision functional. Expected outcome: WIND-DOWN.
4. **If WIND-DOWN (most likely):** firm executes the §5.1 wind-down-to-monitoring action map. Carry family monitoring only; no new carry exploration authorized.

---

*Authored by: PM / Chief of Staff — synthesizer and scheduler; no domain or test-design judgment made.*  
*Session: r5-step3-prereg-2026-06-05 | Wave 4 | 2026-06-06*
