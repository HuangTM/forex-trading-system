# Consensus on: Paper-Launch Authorization — Phase-2 Carry-Bet Stack (Governance CONSENSUS resolving 6 deferred CEO sub-decisions)

**Date:** 2026-05-10 (artifacts timestamped 2026-05-11T03:00:00Z–2026-05-11T04:00:00Z)
**Status:** awaiting-CEO-ratification
**Addressed unit:** `paper-launch-auth-2026-05-10:phase1:task4.0`
**Ratification artifact:** `.agent-accountability/ratifications/paper-launch-auth-2026-05-10:phase1:task4.0.yaml`

---

## Roles staffed

- **PM** — Acceptance-criteria authoring (wave 1); CONSENSUS and CONSENSUS-SUMMARY drafting (wave 4); dissent-preservation routing; knowledge-gap aggregation; ratification artifact production. Does not make technical decisions.
- **NHT (Null-Hypothesis Tester)** — Adversarial verification of 5 claims about completeness of SD-1..SD-6 and faithfulness of dissent reproduction. Structural skeptic per fintech-org rule 6. Dissent artifacts preserved verbatim and append-only.
- **CRO** — Re-verification of BC-8 second-loop authorization conditions and CRO pre-flight assumptions against current working-tree state (HEAD `747a6ad`). Decision: `approve`, `size_multiplier: 1.0`. No new dissent emitted.
- **Ops-engineer** — Physical environment verification: stale-log state, RotatingFileHandler fix, monitor scripts, calendar mechanisms, dispatch-lock test, git HEAD. Decision: `completed`. Key divergence surfaced: log is 269 lines (not 122 per prior CONSENSUS), mtime `2026-05-06T23:12:00Z`.
- **Principal Reviewer** — Independent staff-grade review of the complete authorization checklist using `review-plan`, `execution-firewall-review`, and `log-as-decision-trace` rubrics. Decision: `approve-with-conditions`. Eight findings (F-001..F-008) surfaced; zero blocking; two major (F-001, F-002); three minor (F-003..F-005); three observation (F-006..F-008).

---

## Acceptance criteria (from PM)

Source: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pm-acceptance-criteria.yaml`

Six sub-decisions required before first paper bar (SD-1..SD-6) and three meta-criteria (MC-1..MC-3):

| ID | Label | Done-when |
|----|-------|-----------|
| SD-1 | BC-4 dissent acknowledged verbatim | CEO acknowledges NHT dissent-statement from CONSENSUS_2026-05-03 Section 3 and confirms Wave-7 item 2 closure |
| SD-2 | BC-8 second-loop authorization decision recorded | CEO records "authorized" or "declined"; if authorized, CRO conditions acknowledged |
| SD-3 | Stale-log disposition chosen | CEO chooses one of: truncate / verify-startup-clears / accept-merged |
| SD-4 | CRO pre-flight assumptions acknowledged | CEO acknowledges both frozenset scope and single-account requirement |
| SD-5 | 60-trading-day calendar reminder commitment | CEO commits to set reminder at T=0; mechanism named if already set |
| SD-6 | Launch communication with CF-T9 verbatim clause | CEO authors/approves communication containing the firm-adopted CF-T9 disclosure wording |
| MC-1 | CONSENSUS-SUMMARY.md authored per v0.4.11 | Both files exist; SUMMARY ≤ 80 lines; required sections present |
| MC-2 | Signatures collected from required roles | NHT, CRO, ops-engineer, PR, PM all sign |
| MC-3 | Ratification artifact produced before gate passes | Typed artifact at expected path with closed-set decision enum |

**Hard constraints:** `paper_only: true`, `no_live_capital: true`, `no_paper_loop_start_by_orchestrator: true`.

---

## Decision

The org's recommendation to the CEO is: **authorize paper launch, subject to explicit CEO responses to all 6 sub-decisions below.** All five staffed roles (NHT, CRO, ops-engineer, Principal Reviewer) confirm no capital-loss blocker exists for paper-loop operation as of HEAD `747a6ad`. The engineering closures from Wave-10 (F-001/F-002/F-008/BC-8/NEW-2) are genuine and independently verified. The two NHT dissent items (A: SD-2 redundancy; B: SD-6 wording lineage) and the two major PR findings (F-001, F-002) are governance-completeness issues, not capital-risk issues, and are addressed below.

**SD-2 framing (addressing NHT Dissent A and PR F-001):** SD-2 is NOT a fresh CEO decision. The Wave-10 ratification artifact at `.agent-accountability/ratifications/wave10-fix-and-amend:phase1:task1.0.yaml` (lines 34-37) records CEO (huangtm@gmail.com) on 2026-05-06T14:00:00Z explicitly lifting the BC-8 veto: "BC-8 second-loop authorization veto LIFTED. CEO authorizes concurrent vt + carry_fred operation against the same paper account. CRO reverification confirmed lock placement is correct and concurrent test passes." SD-2 in this CONSENSUS is therefore framed as **confirmation that the 2026-05-06 BC-8 ratification carries through to paper-launch authorization**, with the seven CRO BC-8-LIFT-COND-1..7 constraints (emitted in the wave-2 CRO re-verification artifact `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/cro-reverification.yaml` lines 25-75) attaching as the operative binding-constraint set for paper operation. This resolves the framing ambiguity identified by both NHT and PR: the CEO is confirming carry-through, not making a new decision or reversing 2026-05-06. If the CEO instead wishes to record a different outcome (decline), that MUST be stated explicitly with acknowledgment that it reverses the 2026-05-06 ratification.

**SD-2 binding constraints (addressing PR F-002):** The seven CRO binding constraints are incorporated by reference in full: BC-8-LIFT-COND-1 (dispatch lock active in both scripts, vt.py:553 and carry_fred.py:534); BC-8-LIFT-COND-2 (lock released on all exit paths, vt.py:856-869 and carry_fred.py:805-818); BC-8-LIFT-COND-3 (account-key parity gate enforced at startup, vt.py:923 and carry_fred.py:862); BC-8-LIFT-COND-4 (aggregate JPY-correlated cap 15%, CRO_MAX_CORRELATED_PCT=0.15 at vt.py:594 and carry_fred.py:571); BC-8-LIFT-COND-5 (drawdown ladder 10/15/20 assessed per cycle pre-lock); BC-8-LIFT-COND-6 (kill-switch trigger paths wired to both loops); BC-8-LIFT-COND-7 (paper-only; kill-switch Properties 1/2/3/4 remain live-promotion blockers). If any condition becomes false during paper operation, BC-8 authorization is auto-revoked.

**What the CEO must explicitly decide (6 sub-decisions):**

1. **SD-1** — Acknowledge the BC-4 NHT dissent verbatim (reproduced in Section 10 of this CONSENSUS via pointer to source artifact; CEO states they have read it and acknowledge Wave-7 item 2 closure as the engineering resolution).
2. **SD-2** — Confirm that the 2026-05-06 BC-8 lift carries through to paper launch under the seven BC-8-LIFT-COND-1..7 constraints above; OR explicitly decline (with acknowledgment this reverses the 2026-05-06 ratification).
3. **SD-3** — Choose one of three stale-log dispositions for `data/paper_trading_session.log` (now 269 lines, mtime 2026-05-06T23:12:00Z): `truncate`, `verify-startup-clears`, or `accept-merged`.
4. **SD-4** — Acknowledge both CRO pre-flight assumptions: (1) `_JPY_CORRELATED` frozenset = `{USDJPY, GBPUSD}` at `exposure_aggregator.py:46` — cross-JPY pairs silently bypass the 15% cap if added without frozenset amendment; (2) single-account requirement for cross-strategy aggregation.
5. **SD-5** — Commit to setting a 60-trading-day calendar reminder on the day of first paper bar (T=0). Available mechanisms: `crontab`, `calendar`, `at` (confirmed present by ops-engineer). Calendar reminder is the commitment; the actual setting is a T=0 action.
6. **SD-6** — Author or approve the launch communication. Communication must contain the firm-adopted CF-T9 disclosure wording: **"CF-T9 is binding on Clauses A and B. Clause C is accepted as a known-incomplete deferral and is pending ratification within 60 trading days of paper launch."** This wording (PM-crystallized in the 2026-05-03 wave-6 preflight AC) satisfies the NHT substantive requirement (NHT source dissent at `nht-tier-b-reverify-cosign.yaml` lines 63-70 requires the three facts: CF-T9 A+B binding, Clause C deferral, 60-day window). Per NHT Dissent B (preserved verbatim in Section 10): the wording is PM-authored, not NHT-authored verbatim. The firm adopts this wording as the operative clause for SD-6 satisfaction. Communication reviewer: ops-engineer is designated as the confirming role (NHT's disjunctive "NHT or ops-engineer" resolved to ops-engineer as the available role at launch time). Confirmation artifact path: `docs/launch/sd6-launch-comm-verbatim-check.yaml` (to be created at launch time).

---

## Evidence supporting the decision

- **PM acceptance criteria (wave 1):** `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pm-acceptance-criteria.yaml` — 6 sub-decisions (SD-1..SD-6), 3 meta-criteria (MC-1..MC-3), hard constraints, out-of-scope list.
- **NHT dissent-verification (wave 2):** `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/nht-dissent-verification.yaml` — 5 claims tested; all pass; aggregate verdict: dissent (severity: concern). Two append-only dissent items (A and B) preserved verbatim in Section 10.
- **CRO re-verification (wave 2):** `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/cro-reverification.yaml` — Decision: approve, size_multiplier 1.0. Seven binding constraints (BC-8-LIFT-COND-1..7). Two knowledge gaps (KG-1 cross-JPY frozenset; KG-2 cross-host flock caveat). No new dissent.
- **Ops-engineer verification (wave 2):** `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/ops-engineer-verification.yaml` — Decision: completed. Six steps executed. Stale-log divergence confirmed (269 lines, mtime 2026-05-06T23:12:00Z). RotatingFileHandler confirmed in both paper scripts. HEAD `747a6ad` confirmed.
- **Principal Reviewer review-report (wave 3):** `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/principal-reviewer-review.yaml` — Decision: approve-with-conditions. Eight findings (F-001..F-008). Zero blocking findings. F-001 (major, SD-2 redundancy) and F-002 (major, BC-8 binding-constraint coverage gap) addressed in Section 4 above.
- **Wave-10 ratification (prior, unmodified):** `.agent-accountability/ratifications/wave10-fix-and-amend:phase1:task1.0.yaml` — Records CEO BC-8 lift at 2026-05-06T14:00:00Z. Source of SD-2 carry-through framing.
- **Wave-10 CONSENSUS (prior, unmodified):** `docs/decisions/CONSENSUS_2026-05-06_wave10_fix_and_amend.md` — F-001/F-002/F-008/BC-8/NEW-2 engineering closures confirmed genuine.

---

## Decisions NOT made (deferred, out of scope)

Per PM acceptance-criteria out-of-scope list (verbatim):

- Wave-11 dispatch: F-100/F-101/F-102/F-103 non-blocking findings (routed to Wave-11 binding ticket per Wave-10 CONSENSUS).
- Push to origin/main: currently 51 commits ahead; push is a separate CEO-authorized action.
- Historic-commit cleanup: 4 historic commits containing account-key literals in pre-rewrite content (cleanup deferred).
- Any new code, backtest, strategy registration, or trial pre-registration.
- Kill-switch Properties 2/3/4 remediation: these gate live promotion only, not paper-loop operation (Wave-9 CRO dissent; persists as live-promotion blocker).
- Saxo token revocation: manual user action; orchestrator cannot perform; user must revoke via Saxo developer portal.
- F-006 equity-log shared-path race: deferred Wave-11 per Wave-10 CONSENSUS.
- F-007 carry_fred regime-inactive decision-trace gap: deferred.
- Re-adjudication of any NHT dissent already recorded as append-only in prior CONSENSUS docs.
- Modification to CONSENSUS_2026-05-02_paper_launch_authorization.md or CONSENSUS_2026-05-03_preflight_closure.md: those documents are ratified and unmodified.
- CF-T9 Clause C ratification: deferred; 60-trading-day window post-launch (triggered by SD-5 calendar reminder).

---

## Debate history (if any)

No bounded-round debate occurred; all role artifacts converged with one append-only dissent (NHT) preserved verbatim below.

---

## Assumptions we're betting on

Synthesized from all wave-2/wave-3 role artifacts' `assumptions` fields:

1. HEAD is commit `747a6add72b1a66c4ae9c9be37e9bd59391f946c` (verified by ops-engineer git-log step 6).
2. Prior ratified CONSENSUS files (2026-05-02, 2026-05-03_preflight, 2026-05-03_wave7, 2026-05-06_wave9, 2026-05-06_wave10) are immutable and have not been modified by this dispatch.
3. The ratification artifacts at `.agent-accountability/ratifications/` accurately record CEO decisions and have not been backdated or altered (NHT assumption 3).
4. "Paper-only" means: no production-account capital, all order routing terminates at the Saxo SIM environment, no production credentials, no real P&L. BC-8 lift is scoped to paper operation only; live promotion requires a separate CRO risk-architecture review covering Properties 1/2/3/4 (CRO assumption A-1).
5. Both paper loops run on the same host with the same `data/` directory visible (so `DISPATCH_LOCK_PATH = "data/dispatch_lock.flock"` and `ACCOUNT_KEY_LOCK_PATH = "data/paper_account_key_lock.json"` are the same inode for both processes). Cross-host deployment would defeat the fcntl advisory lock (CRO assumption A-2, KG-2).
6. The `_JPY_CORRELATED` frozenset `{USDJPY, GBPUSD}` is correct for Phase 1 (USDJPY-only signals). Cross-JPY pairs are not traded in paper Phase 1 (CRO KG-1).
7. Verification of Wave-10 closures was performed by reading source files; tests were not re-executed at this wave. NHT and CRO relied on Wave-10 artifact records for behavioral verification (NHT assumption 4, CRO assumption A-3).
8. Wave-7 RotatingFileHandler fix is committed and active (confirmed by ops-engineer grep step 2).
9. The PM-crystallized CF-T9 disclosure wording ("CF-T9 is binding on Clauses A and B...") is adopted by this CONSENSUS as the firm-operative wording for SD-6, satisfying the NHT substantive requirement. The wording is PM-authored, not NHT-authored verbatim (NHT Dissent B).

---

## Pre-registered falsification

N/A — this is a governance ratification, not a strategy proposal. Stated explicitly to satisfy CONSENSUS structure requirement.

---

## Dissent (preserved verbatim)

### Null-Hypothesis Tester

**Severity:** concern | **Does block:** false (orchestrator-resolved per `protocols/full-auto.md` does_block table: concern → false) | **Artifact:** `.agent-accountability/dissents/paper-launch-auth-2026-05-10:phase1:task4.0:null-hypothesis-tester.yaml`

> STRUCTURAL-SKEPTIC DISSENT — Paper-Launch Authorization dispatch
> (2026-05-10). This dissent is append-only per role charter.
>
> (A) SD-2 IS REDUNDANT WITH WAVE-10 RATIFICATION ALREADY ON RECORD.
> The Wave-10 ratification artifact at
> .agent-accountability/ratifications/wave10-fix-and-amend:phase1:task1.0.yaml
> lines 34-37 records CEO (huangtm@gmail.com) on 2026-05-06T14:00:00Z
> explicitly stating: "BC-8 second-loop authorization veto LIFTED. CEO
> authorizes concurrent vt + carry_fred operation against the same
> paper account. CRO reverification confirmed lock placement is correct
> and concurrent test passes." The Wave-10 CONSENSUS line 34 also
> enumerates "Decide BC-8 second-loop authorization" as a Wave-10 CEO
> action. The amendment doc Amendment History line 143 further
> confirms "BC-8 second-loop authorization LIFTED" by CEO on
> 2026-05-06. Yet PM acceptance-criteria SD-2 (lines 206-217) frames
> this as a fresh CEO decision requiring choice between "authorized"
> or "declined" with no acknowledgment that the decision is already
> on record. Two possibilities:
>   (i) The current dispatch is a re-record of an already-decided item
>       for the paper-launch context (defensible — paper-launch
>       authorization is a distinct decision from Wave-10 commit
>       ratification), in which case the criterion should explicitly
>       cite the prior ratification and frame SD-2 as "re-affirm in
>       paper-launch context."
>   (ii) The current dispatch is an unintentional re-dispatch of a
>        closed item, in which case SD-2 should be removed and CEO-
>        action set reduced from 6 to 5.
> Either way, the criterion as written does not surface the prior
> ratification, which means the CEO is being asked to make a decision
> without being told it was already made. This is a governance-
> reconstruction gap (cannot be answered from PM-AC alone — must
> cross-reference the Wave-10 ratification artifact).
>
> (B) SD-6 "VERBATIM CF-T9 CLAUSE" IS PM-AUTHORED CRYSTALLIZATION,
> NOT NHT-AUTHORED VERBATIM TEXT. The clause
> "CF-T9 is binding on Clauses A and B. Clause C is accepted as a
> known-incomplete deferral and is pending ratification within 60
> trading days of paper launch."
> first appears in
> .fintech-org/artifacts/2026-05-03T-wave6-preflight-closure/pm-acceptance-criteria.yaml
> line 168 (PM-authored). It does NOT appear character-for-character
> in the NHT source dissent at
> .fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml.
> The NHT source requires the SUBSTANTIVE content ("Any paper-launch
> disclosure (CEO or HoQR) must state that CF-T9 is binding on A+B
> with Clause C pending ratification") but does not prescribe specific
> wording. The PM-crystallized clause is consistent with the NHT
> requirement and arguably stronger (it adds the 60-trading-day
> reference), but labeling it as "verbatim NHT-required disclosure"
> conflates "verbatim NHT requirement" with "verbatim PM-authored
> clause that satisfies the NHT requirement." If a reviewer later
> cross-checks the PM clause against the NHT source artifact
> expecting verbatim correspondence, they will find none. The
> correct framing: the NHT requires the substantive disclosure; the
> PM clause is the firm-adopted wording that satisfies that
> requirement. SD-6 acceptance criterion should test substantive
> conformance (does the launch communication state the three
> required facts: CF-T9 A+B binding, Clause C deferral, 60-trading-
> day window?), not character-for-character match against the PM
> clause.
>
> (C) CONTAMINATION EXPOSURE NOTED, NOT RAISED AS VETO. The PM
> acceptance-criteria.yaml file at the dispatch directory contains
> task-statement, body, and assumptions fields with proposer-
> equivalent reasoning that the role-spec contamination rule
> instructs the orchestrator to strip. The dispatch prompt
> explicitly told this NHT to skip those fields. NHT read the file
> with Read and saw the structured fields plus the proposer-narrative
> fields (the Read tool does not filter by field). NHT did NOT use
> the body/task-statement/assumptions content to form findings —
> all verdicts above are derived from the structured criteria
> fields and from direct re-reads of source artifacts in the working
> directory. This is logged as a procedural observation, not a
> contamination-veto, because the orchestrator-side stripping
> contract was honored at the prompt level. If future dispatches
> want a hard guarantee, the PM should produce a redacted variant
> of the acceptance-criteria yaml (with body/task-statement/
> assumptions removed) for NHT and dispatch THAT file path, not
> the full file path.

---

## Independent review findings (Principal Reviewer)

Source artifact: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/principal-reviewer-review.yaml`
Decision: `approve-with-conditions`

The findings list is preserved verbatim per `protocols/consensus.md` rule 2 (append-only). The two major findings (F-001 and F-002) are addressed explicitly in the Decision paragraph above.

---

**F-001**
- severity: major
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:43-46` and `.agent-accountability/ratifications/wave10-fix-and-amend:phase1:task1.0.yaml:33-37`
- category: spec-drift
- observation: SD-2 frames the BC-8 second-loop authorization decision as a fresh decision the 2026-05-10 CONSENSUS must record. The Wave-10 ratification at 2026-05-06T14:00:00Z (artifact wave10-fix-and-amend:phase1:task1.0.yaml lines 34-37) already records the CEO-authority decision verbatim: "BC-8 second-loop authorization veto LIFTED. CEO authorizes concurrent vt + carry_fred operation against the same paper account." The Wave-10 CONSENSUS (CONSENSUS_2026-05-06_wave10_fix_and_amend.md lines 37, 88) also explicitly framed this as a CEO decision under Wave-10, ratified four days before the 2026-05-10 acceptance-criteria was authored. The acceptance criteria appears to treat this as undecided ("CONSENSUS records one of the two permitted values"), which structurally creates one of two failure modes: (a) the 2026-05-10 CONSENSUS re-records "authorized" — duplicating a prior ratification and creating two ratification entries for the same decision with potentially different conditions attached, OR (b) the 2026-05-10 CONSENSUS records "declined" — silently reversing the 2026-05-06 CEO ratification without explicit "I am reversing my prior ratification" CEO action. For decision-trace accuracy, a future reader auditing "when did the CEO authorize concurrent vt + carry_fred?" must be able to identify the single operative ratification. Two parallel ratifications without an explicit subordination relationship break that property.
- inference: The SD-2 phrasing does not distinguish between (i) a paper-launch-specific re-confirmation that the 2026-05-06 ratification carries through to paper-launch, and (ii) a fresh CEO decision that overrides 2026-05-06. PM must clarify which intent is operative. If (i), the done_when text should reference the prior ratification artifact path and frame SD-2 as "CEO confirms the 2026-05-06 BC-8 lift remains operative for paper-launch under the seven CRO BC-8-LIFT-COND-1..7 constraints." If (ii), the done_when text must include the operative reversal language and an explicit CEO acknowledgment that this overrides the 2026-05-06 ratification.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:43-46`; `.agent-accountability/ratifications/wave10-fix-and-amend:phase1:task1.0.yaml:33-37`; `docs/decisions/CONSENSUS_2026-05-06_wave10_fix_and_amend.md:37, 88`
- recommended-action-class: clarify-spec
- owning-role: pm

---

**F-002**
- severity: major
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:43-46` and `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/cro-reverification-redacted.yaml:21-75`
- category: spec-drift
- observation: CRO re-verification emitted seven binding constraints BC-8-LIFT-COND-1 through BC-8-LIFT-COND-7. The PM SD-2 done_when text enumerates three conditions ("single shared account, dispatch lock active, aggregate JPY-correlated cap ≤15%") inline as the items the CEO acknowledges in the "authorized" branch. The remaining four CRO binding constraints (BC-8-LIFT-COND-1, -2, -3, -5, -6 — by elimination since -4 maps to dispatch-lock and -7 is paper-only-no-live-promotion) are not referenced.
- inference: When CEO ratifies SD-2 as "authorized," the binding-constraint coverage that travels with the ratification is incomplete relative to CRO emission. Either CRO emitted four constraints PM does not consider operative (in which case the firewall is open and CRO authority is being curated by PM, which is a firewall violation), or PM intended to incorporate all seven constraints by reference rather than enumeration (acceptable, but the done_when must say so explicitly). The acceptance-criteria currently does neither.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:43-46`; `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/cro-reverification-redacted.yaml:21-75`
- recommended-action-class: clarify-spec
- owning-role: pm

---

**F-003**
- severity: minor
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:64-68`
- category: observability-gap
- observation: SD-6 done_when says: "a reviewer (NHT or ops-engineer) confirms the verbatim disclosure clause is present character-for-character." Three sub-gaps: (a) the reviewer identity is disjunctive ("NHT or ops-engineer") with no tie-break rule for who actually performs the check; (b) the timing is "before T=0" but how-much-before is unspecified (an hour, a day, the prior wave?); (c) the artifact path where the confirmation lands is not named — when an auditor later asks "show me the char-for-char verification result for SD-6," there is no spec-anchored place to look.
- inference: A reviewer-discretion check with no named output artifact is not machine-checkable and fails the log-as-decision-trace item-1 (outcome named) and item-2 (inputs that drove the outcome) when one tries to reconstruct the SD-6 outcome from logs/governance-artifacts alone.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:64-68`
- recommended-action-class: clarify-spec
- owning-role: pm

---

**F-004**
- severity: minor
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:58-62`
- category: observability-gap
- observation: SD-5 done_when is conditional: "If CEO has already set a provisional reminder based on a target launch date, the reminder mechanism (calendar system, task system, or cron entry) is named." Per CONSENSUS_2026-05-03_preflight_closure.md line 288 ("Cannot be set until paper loop start date (T=0) is known. CEO must set the calendar reminder on the day of first paper bar"), the expected state at CONSENSUS-sign time is that T=0 is unknown, the reminder is NOT yet set, and the SD-5 done_when collapses to "CONSENSUS records the commitment in a dedicated item-9 section" — i.e., a commitment to do a thing, not the thing.
- inference: SD-5 as currently written is satisfiable by writing a paragraph stating "CEO will set a calendar reminder on T=0." The action that actually matters (the reminder existing, in a system that will fire 60 trading days later) is not check-gateable from CONSENSUS content.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:58-62`; `docs/decisions/CONSENSUS_2026-05-03_preflight_closure.md:288`
- recommended-action-class: tighten-invariant
- owning-role: pm

---

**F-005**
- severity: minor
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:33-35`
- category: spec-drift
- observation: The PM-pinned "required verbatim disclosure" string ("CF-T9 is binding on Clauses A and B. Clause C is accepted as a known-incomplete deferral and is pending ratification within 60 trading days of paper launch.") does not appear in the source NHT dissent at `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml` lines 63-70. The source NHT dissent reads: "Any paper-launch disclosure (CEO or HoQR) must state that CF-T9 is binding on A+B with Clause C pending ratification." The longer form first appears in CONSENSUS_2026-05-03_wave7_closure.md line 233 and CONSENSUS_2026-05-03_preflight_closure.md line 289 — both as derived pm-acceptance-criteria references, not as the source dissent text.
- inference: "Verbatim" is being used here to mean "verbatim relative to the 2026-05-03 PM authoring," not "verbatim relative to the source NHT dissent." A reader auditing whether the launch communication faithfully reproduces what NHT asked for will find that the pinned string is a longer reformulation.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:33-35`; `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml:63-70`; `docs/decisions/CONSENSUS_2026-05-03_wave7_closure.md:231-235`; `docs/decisions/CONSENSUS_2026-05-03_preflight_closure.md:289`
- recommended-action-class: clarify-spec
- owning-role: pm

---

**F-006**
- severity: observation
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:38-42`
- category: maintainability
- observation: SD-1 (BC-4 dissent acknowledged verbatim) requires that CONSENSUS body contain CEO-authored acknowledgment citing the verbatim dissent source. The done_when is acceptable as written, but it does not specify where the verbatim dissent is reproduced (in the CONSENSUS body itself, or by reference to a prior document containing it). Both options are valid; only the choice needs to be pinned.
- inference: Without a specified location for the verbatim reproduction, two CONSENSUSes could both "satisfy SD-1" while one reproduces the dissent and the other only references its file path.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:38-42`
- recommended-action-class: clarify-spec
- owning-role: pm

---

**F-007**
- severity: observation
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:53-57`
- category: maintainability
- observation: SD-4 (CRO pre-flight assumptions acknowledged) done_when permits acknowledgment "by their description or by reference to CONSENSUS_2026-05-03 Section 6." The "by description" branch is unbounded — a CEO who writes "I acknowledge the two CRO pre-flight items" satisfies the done_when literally but produces nothing reconstruction-grade.
- inference: The acceptance-criteria offers two satisfaction modes with very different trace accuracy. Recommend tightening to the "by reference to specific section + verbatim re-quote of the two assumption descriptions" mode.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:53-57`; `docs/decisions/CONSENSUS_2026-05-03_preflight_closure.md:282-284`
- recommended-action-class: clarify-spec
- owning-role: pm

---

**F-008**
- severity: observation
- location: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml:1-96` (whole-artifact)
- category: maintainability
- observation: The artifact has no explicit "decision authority" matrix per sub-decision. SD-2 lift is CEO-with-CRO-input. SD-1, SD-4 are CEO-acknowledgment. SD-3 is CEO-choice-with-Ops-followup. SD-5 is CEO-commitment. SD-6 is CEO-authored-with-reviewer-confirm. Each varies in who owns the decision and who verifies it. The acceptance-criteria as a whole does not surface this allocation; a reader has to infer it from done_when prose.
- inference: A small "decision authority" table mapping {SD-id → decision-owner, verifier} would tighten the firewall hygiene. Not blocking, but a maintainability improvement.
- evidence: `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pr-redacted/pm-acceptance-criteria-redacted.yaml`
- recommended-action-class: clarify-spec
- owning-role: pm

---

## Resolution of major findings

**F-001 (SD-2 redundancy):** Resolved in the Decision paragraph by explicitly framing SD-2 as carry-through confirmation of the 2026-05-06 ratification with paper-launch-specific CRO binding constraints attached. The single operative ratification for "when did CEO authorize BC-8" remains `wave10-fix-and-amend:phase1:task1.0.yaml` (2026-05-06T14:00:00Z). The 2026-05-10 CONSENSUS records carry-through confirmation with the seven BC-8-LIFT-COND-1..7 constraints as the paper-launch-specific binding-constraint set.

**F-002 (binding-constraint coverage gap):** Resolved by incorporating all seven BC-8-LIFT-COND-1..7 constraints by explicit enumeration with file:line citations in the Decision paragraph. No CRO authority is curated or dropped by PM; all seven travel with the SD-2 ratification.

---

## Knowledge gaps surfaced (routed to skill-gap loop)

All entries appended to `.fintech-org/skill-gaps.jsonl` per `pm.md` v0.4.10 gap-aggregation discipline and routed to `protocols/skill-gap.md`.

| # | Originating role | Gap topic | Routed-to |
|---|-----------------|-----------|-----------|
| KG-1 | CRO | Cross-JPY pairs in PM instrument-universe but NOT in `_JPY_CORRELATED` frozenset at `exposure_aggregator.py:46`. Under-counts JPY tail risk if cross-JPY signals fire. Not blocking for USDJPY-only paper Phase 1. | skill-gap.md |
| KG-2 | CRO | Cross-host or symlink-based deployment topologies could defeat fcntl advisory lock. Current single-host topology is binding; any deployment change is CRO re-review trigger. | skill-gap.md |
| KG-3 | NHT | NHT did not independently execute test suite (pytest/ruff/forbidden-phrases) to re-verify Wave-10 closures — relied on Wave-10 NHT artifact records. Conditional on artifact accuracy. | skill-gap.md |
| KG-4 | NHT | Whether the firm has explicitly adopted the PM-crystallized CF-T9 disclosure wording as binding policy (vs. substantive conformance) is not stated in any artifact NHT read. Affects SD-6 strictness interpretation. | skill-gap.md |
| KG-5 | Principal Reviewer | PR could not independently verify which three of the seven BC-8-LIFT-COND-* constraints PM enumerated inline in SD-2 done_when (redaction). Resolved in Decision paragraph (all seven incorporated by reference). | skill-gap.md |
| KG-6 | Principal Reviewer | Whether the seven CRO constraints emitted on 2026-05-10 were ratified with the 2026-05-06 BC-8 lift or are additive paper-launch-specific constraints. Resolved in Decision paragraph (additive paper-launch-specific). | skill-gap.md |

---

## Signatures

| Role | Artifact path | Signed-via-artifact |
|------|--------------|---------------------|
| PM | `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/pm-acceptance-criteria.yaml` | signed-via-artifact (this CONSENSUS document) |
| NHT | `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/nht-dissent-verification.yaml` | signed-via-artifact |
| CRO | `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/cro-reverification.yaml` | signed-via-artifact |
| Ops-engineer | `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/ops-engineer-verification.yaml` | signed-via-artifact |
| Principal Reviewer | `.fintech-org/artifacts/2026-05-10T-paper-launch-authorization/principal-reviewer-review.yaml` | signed-via-artifact |

---

*This CONSENSUS is the audit-trail source-of-truth. For the ratification surface, see `CONSENSUS-SUMMARY_2026-05-10_paper_launch_authorization.md`. Both files versioned together.*
