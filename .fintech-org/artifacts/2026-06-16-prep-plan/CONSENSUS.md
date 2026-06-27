# Consensus on: Define per-role deliverables to maximize expected value of incoming 1h OHLCV data while Dukascopy backfill runs; honest about alpha base rates.

**Session:** `.fintech-org/artifacts/2026-06-16-prep-plan/`
**Timestamp:** 2026-06-17T06:30:00Z
**north_star_trace:** [O1, O2]
- O1 (safety / harness integrity): data-quality gate, EXCLUDE-not-impute posture, spread-correctness gate, kill-switch pre-specs, never-lands branch — all guard against the infrastructure failures that voided QRB-6 and broke the prior DSR gate.
- O2 (profit, subject to O1): pre-registering confirmable hypotheses and building rigorous methodology gives the firm its best honest chance of spending the 1h data efficiently.

---

## Roles staffed

| Role | Rationale |
|------|-----------|
| PM | Owns acceptance criteria, workflow sequencing, and this CONSENSUS. |
| CTO | Owns data validation harness, ingest pipeline, and intraday feature scaffold — all infra deliverables gated to 1h-data readiness. |
| CRO | Owns intraday cost-model extension and risk guardrails — required before any 1h strategy can proceed to backtest. |
| HoQR | Owns hypothesis generation, confirmability screening rubric, and pre-registration authoring — the research strategy layer. |
| ML Researcher | Owns CPCV/DSR methodology design and overfitting-risk pre-assessment — required before any model-based hypothesis is filed. |
| NHT | Owns null-hypothesis battery pre-spec and honest-N protocol — load-bearing for research rigor; must be frozen before any backtest slot is granted. |
| Principal Reviewer | Owns the pre-registration review checklist and independent cross-artifact verification — the gate between pre-registration and backtest-slot grant. |

---

## Acceptance criteria (from PM)

- **AC-01 (Deliverables-not-study):** Every role section names a concrete, durable, repo-checkable deliverable. Domain study goals without artifacts do NOT satisfy this criterion. ✅ MET.
- **AC-02 (Per-role prep):** Each role's deliverable is completable before data lands AND demonstrably raises the expected value of the 1h dataset. ✅ MET with conditions (see Blocking Conditions).
- **AC-03 (Honest O2):** No profit promise; success = research-readiness, not profit. Verbatim base-rate present in all role artifacts. ✅ MET.
- **AC-04 (Hard guardrails):** All constraints honored in each role section. ✅ MET.
- **AC-05 (Out-of-scope list):** Explicit out-of-scope section present with all six mandatory entries. ✅ MET.
- **AC-06 (Workflow sequencing):** Ordered data-lands-to-backtest-slot DAG present. ⚠️ PARTIALLY MET — missing NHT blind-structural-report step, spread-correctness gate, and never-lands terminal branch (see Blocking Conditions and Sequenced Workflow).

---

## Decision

The CEO's question — "can roles learn their domain to create a trading system that earns money while the backfill runs?" — is a category error. Domain expertise is NOT the binding constraint: the firm holds expert skills across all roles and has run 48 rigorous trials with full statistical rigor, finding zero validated alpha. The scarce input has never been knowledge; it is a *confirmable edge in data* that the firm can honestly measure within its validation horizon.

The productive use of the wait is to **PRE-BUILD RIGOR**: each role produces durable, repo-checkable artifacts so that the instant clean 1h data lands, the firm can execute confirmable intraday research immediately — with no infrastructure scramble, no data-peeking risk, and no post-hoc re-registration. The deliverables are concrete files, gates, stubs, specs, and pre-registrations; not study plans or reading lists.

**No one promises the system will earn money.** NHT's honest base rate is approximately 15% (10–20%) that the firm finds at least one validated intraday strategy this cycle. The prep plan succeeds if it produces a firm ready to run confirmable research — not a profitable system. That is an outcome of a stochastic process with a low base rate, not a deliverable.

north_star_trace: [O1, O2]

---

## What "prep" actually means here

"Prep" in this plan does NOT mean learning or studying. It means building artifacts that gate future decisions:

- A data-quality gate that fires before any backtest slot is granted (CTO)
- A cost model extension and risk guardrail pre-spec, with EXCLUDE-not-impute posture (CRO)
- A frozen confirmability rubric and a pre-registered hypothesis shortlist (HoQR)
- A CPCV + DSR methodology design with leakage-check protocol (ML Researcher)
- A null-hypothesis battery pre-spec and honest-N protocol (NHT)
- A pre-registration review checklist for the PR to apply at the backtest-slot gate (PR)

Every artifact names the decision it gates. Artifacts that cannot name a decision they gate are infrastructure theater (NHT-D1) and must be cut.

---

## Per-role deliverable table

| Role | Deliverable | Path | Decision it gates |
|------|-------------|------|-------------------|
| CTO | 1h ingest validation harness (pytest) | `tests/data/test_1h_data_quality_gate.py` | Whether each pair's 1h parquet is approved for research (EXCLUDE on fail) |
| CTO | Per-pair data-quality gate YAML | `config/data_quality_gates_1h.yaml` | Per-pair thresholds for bar-count, gap fraction, spread plausibility |
| CTO | Intraday feature scaffold stubs | `src/forex_system/features/session.py`, `intraday_atr.py`, `time_encoding.py` | Whether pre-registration interface contracts are stable before data lands |
| CRO | Intraday cost-model extension spec | `cro-risk-gates.yaml` (Deliverable A) | Whether a 1h trial's cost coverage is sufficient to freeze (EXCLUDE-not-impute gate) |
| CRO | Risk guardrail pre-spec | `cro-risk-gates.yaml` (Deliverable B) | Hard constraints every 1h strategy inherits at pre-registration |
| HoQR | Frozen confirmability screening rubric | `references/intraday_confirmability_screening_rubric.md` | Whether a hypothesis clears the ≤2yr gate before backtest slot is granted |
| HoQR | Intraday hypothesis shortlist (ranked) | `references/pre-registrations/` (to be authored) | Which hypotheses enter the pre-registration queue; routing for H1 to Quant Researcher |
| ML | CPCV + DSR + leakage methodology design | `.fintech-org/artifacts/2026-06-16-prep-plan/ml-methodology-prep.yaml` | Whether the evaluation harness prevents the most common 1h false-positive traps |
| ML | Overfitting-risk pre-assessment + ALLOW/DENY feature list | (same artifact) | Whether a 1h ML strategy's feature set is admissible before backtest |
| NHT | Null-hypothesis battery pre-spec | (filed before any backtest) | Whether any 1h claim must survive random-entry, session-time-only, and daily-momentum baselines |
| NHT | Honest-N protocol for 1h data | (filed before any backtest) | Whether years_to_validate uses autocorrelation-corrected effective-N (not nominal bar count) |
| PR | Pre-registration review checklist | `.fintech-org/protocols/` (to be authored) | Whether each pre-registration clears the backtest-slot gate |

---

## The decisive finding

**1h data likely MOVES the confirmability wall to ~1.5–3yr for a few hypotheses. It does not break the wall.**

Three structural reasons (NHT-D3):
1. 1h bars are heavily autocorrelated and session-clustered. Effective-N gain is far below the nominal 24x. Overlapping, dependent observations do not buy independent evidence.
2. Intraday edges are smaller per-event and live closer to the spread. The TCA hurdle is HARDER intraday because realized edge per bar shrinks faster than cost does.
3. More bars multiply the multiple-comparisons surface, raising the DSR deflation denominator.

Net: events/yr UP, per-event-Sharpe DOWN, effective-N-per-nominal-N DOWN, deflation-penalty UP. These partially cancel. The honest result is a real but modest unlock — not a regime change.

**No hypothesis pre-clears the ≤2yr gate on honest low-end priors.**

HoQR applied its own rubric's mandatory LOW-end-IR honesty defaults and found: grant_backtest_slot_to is empty. H1 (pooled 8-pair session-open momentum) sits at ~3.2yr STRETCH on the low-end prior; it crosses 2yr ONLY if measured data delivers IR≥0.10 AND ev/yr≥350 AND cross-pair ρ̄≤0.41. H2 (CB-window intraday drift) is ~3.1yr STRETCH. H4 (carry-rollover) is a hard FAIL (~19yr). H5 is a pre-declared negative control / cost-model canary.

**Readiness does not equal a guaranteed PASS.** The firm is preparing to run confirmable research, not confirming that alpha exists.

---

## Sequenced workflow: data-lands → backtest-slot

This workflow incorporates all PR and NHT-mandated steps. AC-06 was PARTIALLY MET without these additions; this section fills the gaps.

**Step 0 — Never-lands branch (NHT-D5, PR F-005):**
If Dukascopy throttling or data failure means fewer than a usable threshold of pairs land clean within a declared timeout window: HALT the research phase. Do not proceed to backtest on partial or suspect data. Declare the cycle outcome as DATA-DOA and surface to CEO for a strategic decision. The plan does not run forward on hope.

**Step 1 — Run CTO data-quality gate (CTO-D1):**
`pytest -k TestIntegrationGateDecision` against each `*_1h.parquet`. Produce `data/processed/{PAIR}_1h_gate_result.json`. On fail: EXCLUDE the pair. NEVER impute.

**Step 2 — Publish per-pair LAND/PARTIAL/MISSING/NEVER status (NHT-D5, PR F-005):**
CTO publishes a structured status for all 12 pairs. Any pair with `gate_result: EXCLUDED` is dropped from all subsequent steps. CEO is notified if more than half the pairs are excluded.

**Step 3 — Run spread-column END-TO-END correctness check (NHT-D5, PR F-005, PR-RISK-3):**
QD reconstructs the per-bar spread independently (from tick data or a second reference source, per NHT RR-1) for at least one landed pair and reports the distribution of `(recovered_spread − independent_spread)`. A plausible-but-mis-scaled spread (e.g., JPY-pip scaling error) passes all existence and ≤50-pip plausibility checks but silently corrupts all TCA — the QRB-6 failure mode in a new field. This step is a HARD GATE: a correctness check is required before TCA-based decisions are trusted.

**Step 4 — Run CRO cost-coverage gate (CRO KG-4):**
The rollover-aware holding_cost callable and the per-bar/per-pair EXCLUDE coverage gate (CRO KG-4, BUILD-PRECONDITION) must be built and running before this step. Run the coverage gate against each approved pair. Any pair with MEASURED-bar fraction < 0.90 over the trade window is EXCLUDED.

**Step 5 — Blind structural data-quality report (NHT-D2, PR F-004):**
A BLIND structural report (bar counts, gap fractions, spread sanity per pair — NO return/signal statistics, NO predictive content) is produced. This is the ONLY data contact permitted before pre-registrations are frozen. Its purpose is to allow the hypothesis shortlist to be EXPANDED if the data structure reveals a better structural hypothesis than the priors suggested. Fishing (inspecting return/signal statistics before freezing) remains forbidden. This step is positioned BEFORE Step 6 so that anchoring to prior-generation bets does not preclude a structurally superior candidate revealed by the data's shape.

**Step 6 — HoQR finalizes / expands pre-registrations (referencing only approved pairs):**
After the blind structural report, HoQR may finalize H1 and expand the shortlist if the data structure justifies it. Pre-registrations may reference only APPROVED pairs. H1's backtest slot remains BLOCKED unless measured data moves years_to_validate ≤2yr — "H1 pre-registered" does NOT mean "H1 approved to backtest" (PR F-007).

**Step 7 — PR reviews and counter-signs each pre-registration:**
PR applies the pre-registration review checklist (years_to_validate independently computed, data-peeking absence attestation, CRO cost-model coverage verified, NHT null battery referenced, execution-firewall compliance confirmed). No backtest slot is granted without PR counter-signature.

**Step 8 — NHT null battery frozen:**
NHT freezes the null battery for each approved pre-registration before the backtest runs. Battery must be frozen before any backtest is run, not after.

**Step 9 — CEO grants backtest slot:**
CEO is the required approver for the backtest-slot grant. Confirms trial counter increment is correct. Any scope expansion beyond the approved pairs requires explicit CEO decision.

---

## Blocking conditions before any 1h trial

The following must be resolved BEFORE the data-quality gate is run or any pre-registration is frozen:

**BLOCKING — PR F-001 (CTO bar-count threshold fix):**
`min_bars_2yr: 17520` in `config/data_quality_gates_1h.yaml` exceeds the maximum achievable clean 24x5 bar count (~13,770 per CTO's own FM-4 arithmetic). Under the current schema, EVERY clean pair would fail the bar-count gate and be EXCLUDED — silently emptying the research universe at the exact moment clean data arrives. CTO must correct `min_bars_2yr` and `min_bars_5yr` to values below the achievable clean density (CTO's FM-4 computes ~13,770 for 2yr) before the gate is run. The corrected constant must be re-validated against measured Dukascopy 1h density once data lands.

**BLOCKING — CRO KG-4 (EXCLUDE-gate + rollover-aware swap MUST BE BUILT):**
Two required code items do not yet exist in the repo:
1. A `coverage_gate(parquet, window) -> {pair: verdict ADMIT|EXCLUDE}` callable that actually EXCLUDES (not merely warns) bars failing spread_p90>0, spread_median≤p90 ordering, and MEASURED-fraction≥0.90 checks. The current `validate_1h_schema()` warns only — it does not exclude. A parquet with spread_p90_pips=0 or p90<median passes the current code cleanly and reaches the backtest.
2. A rollover-aware `holding_cost` in the cost model that charges daily swap ONLY across the 22:00 UTC rollover (3x Wednesday), never pro-rating by hours. `RealisticCostModel.holding_cost` at `model.py:42-53` currently implements the banned pro-rata anti-pattern (`-daily_swap * days`). Until items 1 and 2 ship, 1h cost realism is NOT enforced and the VOIDED-trial failure class is NOT yet closed in code — only specified. Owner: Quant Developer.

**MAJOR — PR F-002 (Dual completeness gates, unreconciled):**
CTO's `max_gap_pct` gate and CRO's `MEASURED-fraction≥0.90` gate have different denominators and thresholds with no defined precedence. A single authoritative completeness rule must be defined (AND-of-both or explicit precedence) before the gate is run.

**MAJOR — PR F-003 (Spread thresholds unreconciled):**
CTO's `spread_median_pips_max` ceilings (3.0–6.0 per pair) and CRO's 0.1–8 pip sanity band are independent, pre-data estimates set without coordination. CTO identified this as a self-declared research-quality blocker. CRO must supply authoritative per-pair spread priors; CTO ceilings must derive from them before the gate is run.

**MAJOR — PR F-004 (HoQR freeze-now vs NHT blind-report sequencing):**
HoQR's `single_highest_ev_prep_action` freezes H1 pre-registration NOW. NHT-D2 requires the shortlist to remain EXPANDABLE after the blind structural data-quality report. These are reconciled in the sequenced workflow above (Step 5 precedes Step 6). H1's pre-registration may be DRAFTED pre-data (data-independent work), but the shortlist must be expandable and the slot remains blocked until Step 5 is complete and measured data clears G1.

**MAJOR — PR F-005 (Missing spread-correctness gate and never-lands branch):**
The spread-column END-TO-END correctness check (NHT RR-1) must be a workflow precondition, not merely a RESEARCH_REQUEST. The never-lands terminal branch must be defined before the backfill completes. Both are encoded in the sequenced workflow above (Steps 0 and 3).

---

## Dissent (preserved verbatim)

### Null-Hypothesis Tester — approve-with-dissent

**D1. The firm's documented kill-criterion is "producing infrastructure, not insight" (honest-review 2026-05-31). A prep plan that produces SEVEN role artifacts (validation harness, cost spec, risk pre-spec, hypothesis shortlist, rubric, ML methodology, null battery, honest-N protocol, PR checklist) while the ONE thing that determines value — clean data and a confirmable edge — remains unresolved is EXACTLY the shape of activity the kill-criterion warns against. Building gates and scaffolds FEELS productive and is locally rational, but none of it raises the probability that a real edge EXISTS in the incoming data; at best it lowers the probability we MISS or MIS-MEASURE one. I do not block the plan, but I require that every artifact carry an explicit "expected-value mechanism" line stating HOW it changes a decision — any artifact that cannot name the decision it gates is theater and must be cut, not filed.**

**D2. There is a real tension the plan under-states. Pre-registering >=5 intraday hypotheses BEFORE the data lands anchors the firm on bets chosen from PRIOR (daily) intuition and from the same minds that produced 48 failures — we may freeze the wrong structures and then feel committed to them. The OPPOSITE error is fishing: inspecting the 1h data first and reverse-engineering hypotheses to fit what we see, which inflates effective-N invisibly and is precisely the data-snooping the confirmability gate exists to prevent. MY RULING: seeing-data-first (fishing) is the WORSE error and must remain forbidden, because its damage is undetectable after the fact — a fished hypothesis looks identical to an honest one in the prereg file, and DSR deflation cannot price degrees of freedom it never saw. Anchoring's damage is bounded and visible: a wrong pre-registered bet simply FAILS its KILL gate (as trial 48 did, cleanly, in one day) and costs one trial-counter increment. The asymmetry is decisive. REQUIRED MITIGATION: pre-registrations may be authored now but the shortlist must be EXPANDABLE after a BLIND data-quality report (bar counts, gap fractions, spread sanity — NO return/signal statistics) so that anchoring does not preclude a structurally better hypothesis the clean-data STRUCTURE (not its predictive content) reveals. That blind report is the only data contact permitted before freeze.**

**D3. The optimistic thesis is that 1h granularity multiplies events/yr ~24x and thereby drops years_to_validate below the 2yr gate. I dissent from treating this as established. Three structural reasons the wall likely RELOCATES rather than falls: (i) 1h bars are heavily AUTOCORRELATED and session-clustered, so the EFFECTIVE-N gain is far below the nominal 24x — overlapping/dependent observations do not buy independent evidence (this is my D6 honest-N concern). (ii) Intraday edges are SMALLER per-event and live closer to the spread; the TCA hurdle that already killed trial 48 (gross fade +3.41 pips POSITIVE but cost-dominated at a 7.5-pip conservative cost) is HARDER intraday, not easier, because realized edge per bar shrinks faster than cost does. (iii) More bars also multiply the MULTIPLE-COMPARISONS surface (N x 24 look opportunities), raising the DSR deflation denominator. Net: events/yr UP, per-event-Sharpe DOWN, effective-N-per-nominal-N DOWN, deflation-penalty UP. These partially cancel. My honest base rate (below) reflects that they likely cancel to "the wall moved from ~3-5yr to ~1.5-3yr for a FEW hypotheses" — a real but modest unlock, not a regime change. The plan must not be sold internally as "the ceiling is removed."**

**D4. Conditioned on (a) clean 1h data actually landing for a usable majority of pairs, and (b) the prep gates intact, my honest estimate that THIS firm finds at least one VALIDATED (DSR>=0.95 under org-wide N, survives my null battery, replicates OOS on a held-out period, net-of-TCA POSITIVE) intraday strategy within the next research cycle is: 10-20%, point estimate ~15%. Basis: prior 48 trials -> 0 validated (an empirical 0/48 ceiling on this firm's hit rate), partially offset by the genuine new information that intraday data adds and the fact that 0/48 was largely DATA-WALL-bound rather than idea-bound. The published quant literature finding that <30% of backtested strategies survive rigorous multiple-testing correction is an UPPER bound for us because our gate is stricter than most and our universe is small. I will NOT round this up. If a role's plan implies a materially higher number, that is an unbacked claim and I dissent against it. Success is NOT promised; it is a coin-flip's fraction.**

**D5. The PM acceptance-criteria ASSUME "clean 1h data lands" (assumptions[0], AC-06 step 1). I dissent against that assumption being load-bearing without a published failure branch. Three concrete DOA vectors, all evidenced in firm history: (i) THROTTLING — a prior Dukascopy run over 4 days retrieved only ~1.6% (2 of 12 pairs) because the environment's IP was throttled; the backfill was explicitly moved to the user's machine for this reason. There is a real probability the data NEVER lands cleanly for all 12 pairs, in which case the entire prep plan gates on a dataset that does not arrive — and several artifacts (12-pair cost spec, 12-pair honest-N) are speculative. (ii) ZERO VOLUME — Dukascopy 1h carries no true volume; any "volume proxy from spread" (CTO feature scaffold) is an UNVALIDATED construct and must not be smuggled into a hypothesis as if it were real volume. (iii) SPREAD-COLUMN TRUST — the spread recovery (commit 96f6f84, current branch ingest-spread-column) is RECENT and its correctness is unverified end-to-end; a wrong spread column silently corrupts every TCA estimate, which is the exact failure that VOIDED the first QRB-6 run. REQUIRED: the CTO data-quality gate must include an explicit per-pair LAND/PARTIAL/MISSING status and a spread-column CORRECTNESS check (not just presence/plausibility), and the workflow (AC-06) must have an explicit branch for "data partially/never lands" that does NOT proceed to backtest on incomplete pairs.**

**D6. My honest-N protocol deliverable is not a formality — it is the single number that decides whether ANY 1h hypothesis clears the 2yr gate. The danger: naive counting will use nominal bar counts (24x daily) and make every hypothesis LOOK confirmable, re-creating the broken-gate failure mode in a new costume. Effective-N must be deflated for: intraday autocorrelation (block bootstrap / non-overlapping windows), session clustering (an edge that only fires at one session has far fewer independent events than bars-per-year suggests), and overlap in any multi-bar holding period. I dissent in advance against any confirmability calculation that uses nominal N. The years_to_validate formula (N_required / events_per_year) is only honest if events_per_year is the EFFECTIVE, autocorrelation-corrected, non-overlapping count — per pair, per session, per hypothesis.**

---

## Independent review findings (Principal Reviewer)

Decision: approve-with-conditions. Reviewed 6 of 6 artifacts plus 5 repo verifications. All SPEC-vs-CODE honesty claims verified true against the repo.

| ID | Severity | Location | Observation | Recommended action | Owning role |
|----|----------|----------|-------------|-------------------|-------------|
| F-001 | **blocking** | CTO-D2 schema (`min_bars_2yr: 17520`) vs CTO FM-4 arithmetic | min_bars_2yr=17520 exceeds achievable clean 24x5 bar count (~13,770 for 2yr per CTO's own FM-4). Every clean pair would fail the bar-count gate and be EXCLUDED. The artifact's own FM-4 prose contains the disproving arithmetic but the schema value was not corrected. | clarify-spec: set per-pair min_bars below achievable clean density | cto |
| F-002 | major | CRO coverage_gate (MEASURED-fraction≥0.90) vs CTO max_gap_pct (0.5%–1.0%) — two unreconciled completeness gates, different denominators | A pair could PASS one gate and FAIL the other; no defined precedence; admitted universe is ambiguous | clarify-spec: define single authoritative completeness rule (AND-of-both or explicit precedence) | cto |
| F-003 | major | CTO spread_median_pips_max (3.0–6.0 per pair) vs CRO per-pair sanity band (0.1–8 pips) — unreconciled pre-data estimates | CTO's own routed_to.cro explicitly identifies discordance as a research-quality blocker; the reconciliation did not happen in these artifacts | escalate-to-owning-role: CRO supplies authoritative per-pair priors; CTO ceilings derive from them | cro |
| F-004 | major | HoQR freeze-H1-NOW vs NHT-D2 blind-structural-report-then-expandable; AC-06 missing blind-report step | Unresolved sequencing conflict: either H1's freeze is premature under NHT's ruling, or NHT's ruling is not honored in the workflow | clarify-spec: encode one permitted pre-freeze data contact (blind structural report) in AC-06 | head-of-quant-research |
| F-005 | major | NHT-D5/RR-2 (spread-column CORRECTNESS check + never-lands branch) absent from PM AC-06 and CTO workflow | Spread correctness is a RESEARCH_REQUEST, not a workflow gate; a mis-scaled-but-plausible spread (QRB-6 failure mode in a new field) would pass silently | add-edge-case-handling: spread-correctness gate as precondition + LAND/PARTIAL/MISSING/NEVER branch | cto |
| F-006 | minor | ML DSR-N=48 (deflation) vs HoQR N_required≈6.18/IR² (confirmability sample size) — two distinct "N" concepts unlabeled | Low risk of actual error (both formulas individually sound) but exactly the kind of ambiguity that produced the broken-DSR-gate reset | clarify-spec: one-line disambiguation | ml-researcher |
| F-007 | minor | HoQR H1 disposition STRETCH + grant_backtest_slot_to:[] vs AC-06 step 6 granting slot | "H1 pre-registered" could be misread as "H1 approved to backtest"; the slot contingency on measured data clearing G1 is in prose but not in the step list | clarify-spec: state explicitly that >2yr-on-priors pre-reg's slot stays BLOCKED until measured data clears G1 | head-of-quant-research |
| F-008 | observation | Whole plan — NHT-D1 infrastructure-theater self-test | CTO (why_raises_ev) and CRO (gate ties to VOIDED trial) satisfy NHT-D1; ML and HoQR articulate it in prose; PM plan does not add a per-artifact decision-gated EV line uniformly | other: uniform EV-mechanism line at consensus assembly | pm |

---

## Evidence supporting the decision

- `pm-acceptance-criteria.yaml` — task reframe, acceptance criteria AC-01–AC-06, instrument universe, hard constraints
- `cto-infra-prep.yaml` — evidence reads of `src/forex_system/data/validation.py`, `scripts/ingest_dukascopy_1h.py`, `tests/data/test_dukascopy_ingest.py`, `src/forex_system/features/`, `data/processed/`; deliverables CTO-D1/D2/D3; FM-4 bar-count arithmetic; session constant design
- `cro-risk-gates.yaml` — Deliverable A (intraday cost-model extension spec, CM-1/CM-2/CM-3, coverage gate); Deliverable B (risk guardrail pre-spec); KG-4 BUILD-PRECONDITION (rollover-aware swap and EXCLUDE-gate not yet in code)
- `hoqr-hypothesis-prep.yaml` — frozen confirmability rubric; ranked hypothesis shortlist H1–H5; ranked_disposition `grant_backtest_slot_to: []`; honest low-end prior application; H1 retirement criteria
- `ml-methodology-prep.yaml` — CPCV N=6/k=2/15 folds, purge=480 bars, embargo≥24 bars; DSR deflation against org-wide N=48; ALLOW/DENY feature list; overfitting-risk pre-assessment; what 1h OHLCV cannot support
- `nht-dissent.yaml` — D1–D6 verbatim; honest-base-rate 15% (10–20%); NHT-deliverables-acknowledged (null battery + honest-N protocol)
- `principal-review.yaml` — findings F-001–F-008; AC-by-AC completeness; SPEC-vs-CODE honesty verified; reviewer-surfaced-risks PR-RISK-1/2/3

---

## Honest base rate and success definition

**Base rate:** ~15% (range 10–20%) that this firm finds at least one VALIDATED (DSR≥0.95 under org-wide N=48, survives NHT null battery, replicates OOS on held-out period, net-of-TCA positive) intraday strategy in the next research cycle. This is conditioned on clean 1h data landing for a usable majority of pairs AND prep gates remaining intact.

Basis: empirical 0/48 validated alpha across all prior trials; partially offset by the genuine data-capability unlock. Published quant literature: <30% of backtested strategies survive rigorous multiple-testing correction — an UPPER bound for this firm given its stricter gate and small universe. NHT will not round this number up.

**Success definition for this preparation phase:** The firm is ready to execute confirmable intraday research the moment clean 1h data lands — with zero pre-registered hypotheses needing revision due to data-structure surprises, no infrastructure scramble, and all guardrails enforced. Success is NOT a profitable system. It is not even a passed backtest. It is research-readiness.

---

## Assumptions we're betting on

- The Dukascopy 1h backfill (12 pairs) is actively running on the user's machine and has not yet landed cleanly — no 1h data is available for analysis as of this consensus.
- The firm has no validated OOS alpha from any prior cycle (honest-review-2026-05-31 is authoritative and retroactively invalidated all prior VALIDATED/PASSES/paper-launch claims).
- Expert-level domain skills are already present in the role-agents; "prep" means DELIVERABLES, not domain study.
- The confirmability gate (years_to_validate ≤ 2yr) established in prior cycles is frozen and applies to all intraday hypotheses.
- DSR ≥ 0.95 and org-wide N=48 are carried forward without change.
- No live capital has ever been deployed (charter rule 1, never broken).

If any of the following are wrong, the consensus is partially invalidated: (a) the Dukascopy 1h spread column is systematically mis-scaled (would corrupt all TCA and require a full re-ingest); (b) the effective-N gain at 1h is negligible even after session-pooling (would move years_to_validate well above 2yr for all hypotheses); (c) the data never lands for most pairs (would trigger the never-lands terminal branch).

---

## Pre-registered falsification

No backtest has been run. No strategy is being proposed. Pre-registration artifacts have not yet been filed; H1's pre-registration is routed to Quant Researcher but not frozen. The section is therefore empty at this consensus stage — it will be populated when H1 and (if applicable) H2 pre-registrations are filed, reviewed by PR, and counter-signed.

---

## Decisions NOT made (deferred, out of scope)

The following are explicitly out of scope for this preparation plan:

1. **Running any backtest** — 1h data not yet available; any backtest run now constitutes data-peeking if data has partially landed.
2. **Building execution infrastructure** — no order management, broker API wrappers, or position sizing for live orders.
3. **Live or paper trading** — no live capital; observe-only canary is the maximum allowed per prior NHT ruling.
4. **Descriptive or exploratory data analysis on the 1h data** — any EDA before pre-registration is frozen violates the no-peeking constraint. The ONLY permitted data contact before freeze is the BLIND structural data-quality report (Step 5 of the sequenced workflow).
5. **Generating new daily-pair strategies** — the daily dataset wall is a firm finding; 1h is the unlock; daily strategy generation is out of scope.
6. **Incrementing the trial counter** — planning and pre-registration do not constitute trials.
7. **Profit projections or expected-return claims** — O2 is a target direction, not a deliverable outcome.
8. **Domain study outputs without a corresponding artifact** — reading, watching, or summarizing without producing a durable deliverable does not satisfy this plan.

---

## Debate history

No formal debate rounds were run. Roles produced independent artifacts; PM synthesized. NHT dissent was append-only (6 items, D1–D6) and surfaced verbatim. PR findings (F-001–F-008) were produced independently with other roles' decision stances stripped from PR's context (contamination-check: clean).

---

## Knowledge gaps surfaced (routed to skill-gap loop)

9 knowledge gaps from this session appended to `.fintech-org/skill-gaps.jsonl`. Full list:

| # | Originating role | Gap topic |
|---|------------------|-----------|
| 1 | HoQR | Empirical decay rate of intraday FX session-open momentum post-2020 (H1 G6 non-stationarity kill-risk) |
| 2 | HoQR | Whether cross-pair signal correlation (rho_bar) for pooled session-momentum is ~0.35 or materially higher (H1 effective-N make-or-break) |
| 3 | HoQR | Whether a single CB decision yields ~2 semi-independent intraday sub-events (the ONLY path to H2 ≤2yr; may be data-mining artifact) |
| 4 | CTO | Dukascopy 1h bar density per pair (actual bars/year) — min_bars thresholds in CTO-D2 are pre-data estimates |
| 5 | CTO | Per-pair typical spread_median_pips from Dukascopy 1h — CTO-D2 spread ceilings need CRO cross-check |
| 6 | CRO | n_crossed_clipped and tick_count not persisted to parquet; R-1/R-2 risks cannot be gated per-bar from parquet alone |
| 7 | CRO | Per-pair plausible spread bands are 0.1–8 pip placeholders; real P50/P90 distributions unknown pre-data |
| 8 | ML | Empirical 1h residual-return ACF-decay length not measured; embargo=480 and effective-N are provisional |
| 9 | NHT | Spread-column correctness in commit 96f6f84 not verified end-to-end; required before any net-of-TCA claim is trusted |

All entries routed via `protocols/skill-gap.md` at wave 4.

---

## Signatures

- **pm:** approved — synthesis and coordination complete; CONSENSUS drafted per `protocols/consensus.md`; NHT dissent preserved verbatim D1–D6; PR findings listed verbatim F-001–F-008; knowledge gaps routed to skill-gap loop (N=9)
- **cto:** approved — deliverables CTO-D1/D2/D3 committed; FM-4 bar-count arithmetic is honest and confirms F-001 is a real defect; KG-1–KG-4 acknowledged; firewall clean
- **cro:** approved with KG-4 preconditions — Deliverables A and B are pre-specs, not code; KG-4 BUILD-PRECONDITION (EXCLUDE-gate + rollover-aware swap) is BLOCKING before any 1h trial freezes; size_multiplier=0.0 (no strategy to size); binding constraints stated
- **head-of-quant-research:** approved — rubric frozen; shortlist ranked H1–H5; grant_backtest_slot_to:[] honest; H1 pre-registration routed to QR for authoring; blind-structural-report sequencing per NHT-D2 honored in workflow
- **ml-researcher:** approved — CPCV/DSR/leakage methodology design committed; ALLOW/DENY feature list; zero-volume honest constraint stated; overfitting pre-assessment complete; all deliverables routed to QD
- **null-hypothesis-tester:** approved-with-dissent — D1–D6 recorded verbatim above; both NHT deliverables (null battery pre-spec + honest-N protocol) acknowledged and committed before any backtest; base rate 15% (10–20%) is the firm's honest prior
- **principal-reviewer:** approved-with-conditions — F-001 is blocking (must be fixed before gate runs); F-002/F-003/F-004/F-005 are major and must be resolved before pre-registration is frozen; SPEC-vs-CODE honesty verified TRUE against repo for all five checked claims; no profit promise detected; no contamination

**Ratification path:** Expert quorum — CTO (architecture), CRO (risk), PR (design) all signed. NHT dissent (6 items, approve-with-dissent) is recorded and surfaced. PR blocking finding (F-001) must be addressed before the data-quality gate is run. This consensus does NOT auto-ratify execution dispatches; those require CEO approval after the sequenced workflow gates pass.

---

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets if relevant: `revise f-001` (CTO bar-count threshold fix), `revise nht-dissent` (discussion of D3 wall-moves framing), `revise workflow` (sequencing changes), `revise blocking-conditions`.
