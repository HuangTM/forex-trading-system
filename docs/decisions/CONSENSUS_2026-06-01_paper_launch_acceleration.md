# CONSENSUS: Paper Launch Acceleration
**Track:** paper-launch-acceleration-2026-06-01  
**Phase:** phase1 / task1.0  
**Status:** awaiting-ratification (deferred to CEO)  
**Timestamp:** 2026-06-02T00:00:00Z  
**Authored by:** PM / Chief of Staff  

---

## Task Statement

Define the fastest legitimate sequence to first real paper bar, given zero validated OOS alpha and a tripped kill-criterion.

**CEO's directive:** "We haven't started paper trading, speed it up."

**PM acceptance criteria ref:** `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/pm-acceptance-criteria.yaml`

---

## The Honest Reframe

The CEO's framing contains a false premise: the firm does not have a validated strategy waiting to be deployed. The firm's own ratified audit (2026-05-31, CEO-accepted) found zero validated OOS alpha and a tripped kill-criterion — specifically, the kill-criterion's "infrastructure not insight" conjunct: no paper P&L curve AND a falsification log with ≤12 entries / 0 STRONG out-of-sample rejections against a required ≥20.

The bottleneck is not PM coordination speed. It is (a) the absence of validated alpha, and (b) four unresolved operational preconditions that gate even the minimal observe-only canary.

"Speed it up" legitimately means:
1. Close the 4 preconditions on the shortest possible critical path.
2. Get the right role-deliverables in parallel.
3. Emit the first real paper bar from an OBSERVE-ONLY canary — not from a strategy with an edge claim.

The observe-only momentum-EURUSD canary is the only paper action the firm's own ratified audit permits at this date. It is a plumbing smoke-test, not a step toward validated alpha.

---

## The Convergent Decision

**All four roles converge on the following:**

The ONLY legitimate near-term paper action is an **observe-only momentum-EURUSD canary**: read-only, zero capital, routes no orders, computes NO edge metric, and keeps org trial-count frozen at 35. It is a plumbing smoke-test. It does not satisfy either conjunct of the tripped kill-criterion.

**Precondition triage (CRO-authoritative, unanimously adopted):**

| Precondition | Classification | Rationale |
|---|---|---|
| P1: secrets-purge | **BLOCKING** | Leaked broker credential is irreversible/unbounded loss regardless of capital at risk; nearly leaked 2026-06-01 |
| P4: mock-sentinel-fix (float==100000.0) | **BLOCKING** | Collides with SIM seed; canary cannot count real cycles; every "ran clean" claim becomes unfalsifiable; decision-trace failure |
| P2: Saxo TotalValue marking confirmation | **ADVISORY** at zero capital; BLOCKING at sizing>0 | At size_multiplier=0.0 marking only affects a cosmetic ledger that controls no capital |
| P3: 30-50-cycle calibration | **ADVISORY** for starting the loop; BLOCKING for reconciliation_enforce:true and any "paper-launch" claim | This IS the canary's output; gating the loop on its own output is circular |

**Additional requirements before any graduation to sizing>0:**
- Kill-switch properties 3 (known SLA) and 4 (tested in prod-equivalent conditions) are currently UNMET — Knight Capital class gap. A timed production-equivalent drill must close these before any sizing>0 path is authorized. This drill is NOT required to start the zero-capital observe loop.

**Size:** `size_multiplier = 0.0`. Observe-only enforced architecturally (ReadOnlySaxoClient raises AttributeError on any mutating call), NOT by the multiplier alone. Defense-in-depth; the multiplier is a redundant secondary layer.

---

## Per-Role Positions

### Head of Quant Research (HoQR)

**Decision:** approve-with-capacity-limit  
**Artifact:** `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/hoqr-prioritization.yaml`

Ranked research-capacity priority:
1. **Regenerate Bet#1 (trial 87fa1d23) equity parquet + re-adjudicate under fixed DSR** — the ONLY OOS trial in the registry; equity parquet is genuinely missing (zero files found); auto-retires 2026-07-01. This is time-critical. If OOS Sharpe 0.314 survives corrected DSR/effective-N gate, the firm has its first defensible alpha candidate.
2. **Run R5 (permutation/White Reality-Check) on real carry data** — bounds false-discovery risk across the entire carry program at class level; never run on real data.
3. **Fix carry USDJPY data-quality outlier bug** — upstream of both Bet#1 re-adjudication and R5; contaminated inputs silently inflate or destroy Sharpe.
4. **Observe-only canary** (FOURTH, not a research priority) — zero expected-alpha-per-unit-research-cost by construction. Operational/execution deliverable funded from operational capacity, must NOT preempt items 1–3.
5. **New-alpha production** — LOWEST; must not unfreeze N until existing 35 trials are re-adjudicated and falsification machinery is shown to work.

**Retirement criteria (machine-checkable, by 2026-07-01):**
- WIND-DOWN if: (a) Bet#1 equity not regenerated OR regenerated-and-fails corrected DSR/effective-N gate, AND (b) R5 on real carry returns p≥0.05, AND (c) falsification log still <20 entries with 0 STRONG-OOS rejections → zero validated alpha is structural, not pending; recommend formal wind-down to maintenance/monitoring footing.
- CONTINUE if: Bet#1 survives corrected gate OR R5 p<0.05 on a pre-registered hypothesis → one defensible alpha candidate exists; unfreeze N for confirmatory (not exploratory) trials only.

**Key HoQR finding:** "'Speed up to paper trading' optimizes the wrong thing. The bottleneck is NOT time-to-first-paper-bar; it is the absence of any validated edge to put behind the bar."

### Chief Risk Officer (CRO)

**Decision:** size-reduced (size_multiplier = 0.0)  
**Artifact:** `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/cro-risk-assessment.yaml`

Risk contract at zero exposure: VaR=ES=0; all sizing/leverage/drawdown clauses satisfied-by-construction. The declared risk envelope (0.25%/1.0%/2.5% per-trade/pair/portfolio; EUR+GBP 1.5% correlated unit; 3:1 max leverage; 4% daily breaker; 15% hard DD; 50/75% graduated de-risk) becomes load-bearing the instant any sizing>0 is proposed.

Blowup analog on record: **Knight Capital (2012, SEC File No. 3-15570)** — cited for kill-switch-existence-vs-kill-switch-tested gap. The kill switch here has an audit trail (property 5) but has NEVER been exercised in prod-equivalent conditions (properties 3 & 4 unmet). At zero capital this is not a blowup path, but it IS a hard requirement before any graduation to sizing>0.

Additional plumbing notes (flags, not gates for this wave):
- Cost-recon alarm-only (reconciliation_enforce:false): acceptable for observe-only; must flip to enforce with calibrated tolerances before sizing>0.
- Swap accrual 0.0/cycle (_last_cycle_ts resets per process): correctly zero at zero position, but must be fixed before sizing>0 or carry cost will be systematically under-counted.
- Drawdown peak-persistence fix (2026-06-01) must remain in effect for breaker logic to exercise correctly across restarts.
- ES/CVaR gap: VaR-only system; not a go/no-go blocker at zero exposure; IS a blocking gap before any capitalized sizing.

### Execution Trader (ET)

**Decision:** route-with-reduced-size (size_multiplier = 0.0, observe-only)  
**Artifact:** `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/et-execution-plan.yaml`

**Sequenced critical path to first real paper bar:**

| Step | Action | Owner | Duration | Depends-on | Parallelizable? |
|---|---|---|---|---|---|
| 1 | P1 secrets-purge: verify/clean local refs, stash, untracked secrets files; delete backup tags from 2026-05-06 filter-branch | Operator | 15-30min | None | Yes (with Step 2+3) |
| 2 | P4 mock-sentinel-fix: replace float==100000.0 with positive run-mode flag (env var or SaxoClient.is_live==False + account_id tagging); patch ModeledEquityLedger.is_mock_cycle; add cycle_id/UUID to JSONL log | Quant-developer | 1-2h | None | Yes (with Step 1+3) |
| 3 | Operator provisions 24h Saxo SIM developer token; sets SAXO_TOKEN in terminal | Operator | 0-24h (bottleneck) | None | Yes (with Step 1+2) |
| 4 | Merge+push: commit P4 fix; verify git log has no secrets (inline secret-scan) | Quant-developer+Operator | 15min | Steps 1 AND 2 | No (sequential) |
| 5 | **FIRST REAL PAPER BAR**: operator exports SAXO_TOKEN, runs run_observe_momentum_eurusd.py --loop; verifies first log entry is_mock=False with non-ambiguous account identity | Operator | 5min + 1 bar close | Steps 3 AND 4 | No |
| 6 | P2 Saxo-marking probe: run probe_saxo_marking.py --open-and-flatten EURUSD; confirm CurrentPriceType==Bid for long; record result | Operator | 5min | Step 3 (same token) | Yes (alongside or after Step 5) |
| 7 | P3 calibration: accumulate 30-50 real-fill observe cycles; update tol_abs/tol_rel from placeholders (500.0/0.005) to empirical values; CRO approval | Orchestrator+Quant-developer | 30-50 days (daily timeframe) | Step 5 | N/A (time-bound output) |

**Wall-clock bottleneck:** Step 3 (Saxo SIM token provisioning) — operator human action on external portal; 24h TTL means token must be issued within 2h of intended run window.

**Fastest time-to-first-bar:** 3-5h same-day if operator acts immediately; 4-8h realistic same-day; 18-32h if token requires next business day.

**Go/no-go checklist before first real paper bar** (all must be TRUE):
- [ ] P1 SECRETS-PURGE: `git log --all -p | grep -i SAXO_TOKEN` returns zero results; local backup tags deleted; no untracked credential files.
- [ ] P4 MOCK-SENTINEL-FIX: ModeledEquityLedger.is_mock_cycle uses explicit is_mock_backend flag as primary discriminator, not float==100000.0 alone; JSONL emits run_mode/account_id field; tests pass.
- [ ] SAXO_TOKEN in environment: valid 24h SIM developer token, issued within last 2h.
- [ ] SIM confirmed (not LIVE): `SaxoClient(token, live=False)` asserts not is_live.
- [ ] READ-ONLY ARCHITECTURAL GUARD CONFIRMED: run_observe_momentum_eurusd.py wraps SaxoClient in ReadOnlySaxoClient; any order-routing call raises AttributeError.
- [ ] Python environment: `python3 -c "import forex_system"` succeeds from .venv.
- [ ] data/ writable for JSONL log.
- [ ] No active kill-switch halt in data/kill_switch_audit.log.
- [ ] CRO size_multiplier=0.0 confirmed in modeled ledger.

**Saxo marking protocol (ET-authoritative):**  
Primary confirmation: `CurrentPriceType == "Bid"` for a long. Secondary: `ProfitLossOnTrade` arithmetically closer to bid-marked value than mid-marked value (≤1 pip deviation acceptable). Expected residual while open (EUR/USD, hs=0.25pip, sl=0.5pip): R_open = +u×0.25pip (model below broker). At close per trade: R_close = u×(2sl+c) = u×1.5pip — does NOT converge to zero; this is what cost-reconciliation exists to measure.

**Fill model for future sizing (non-negotiate):** bid/ask not mid; entry fills at ask; exit fills at bid (longs) or ask (shorts); market orders at next-bar open consistent with entry_delay_bars=1 convention.

---

## NHT Dissent (verbatim, append-only)

> **NHT severity: material_concern | does_block: false | The consensus ADOPTS NHT's position — it does not override it.**

The following is the verbatim dissent-statement from null-hypothesis-tester artifact `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/nht-null-test-report.yaml`:

---

*I dissent. The claim is false on both sub-claims and cannot be salvaged by execution.*

*(a) The observe-only canary is NOT the correct next action toward paper trading, because it produces no edge metric, routes no orders, carries no capital, and leaves the trial count frozen at N=35 and the falsification log frozen below its threshold. It is an infrastructure deliverable. The firm's own pre-declared kill-criterion is ALREADY TRIPPED on both conjuncts — no paper P&L curve AND a falsification log with <=12 entries / 0 STRONG out-of-sample rejections, against a required >=20. Shipping a no-edge canary during an infrastructure-overproduction alarm deepens the exact failure the criterion was written to catch. Its output can count as: a plumbing smoke-test (does live ingestion + modeled marking run without error). Its output canNOT count as: evidence of edge, an out-of-sample test, a falsification-log entry, progress on N, or progress toward validated alpha. A modeled paper-equity ledger with no capital and no order routing is a simulation of a simulation; it confirms code paths, not a hypothesis.*

*(b) The delay does NOT reflect execution slowness over a deployable edge. The firm has exactly ONE out-of-sample trial (87fa1d23, momentum EURUSD). Its headline DSR ~0.99999986 is a confirmed bar-count artifact of a now-fixed units bug. Its equity series is MISSING from the repo, so the corrected DSR is literally null/uncomputable and the trial cannot be independently re-verified. A single, unverifiable OOS candidate is the signature of ABSENCE of a confirmed deployable edge, not of slowness. I additionally flag a material discrepancy: the recompute file shows the surviving corrected-DSR trials are vol_target_carry (~0.85/0.94 on series with excess-kurtosis up to ~385-688, violating DSR's tail assumption) — NOT momentum, and NOT the strategy this canary runs.*

*MINIMUM precondition before ANY canary evidence is interpretable as progress toward validated alpha: the falsification log must reach >=20 entries with >=1 STRONG out-of-sample rejection of a real return hypothesis (clearing the kill-criterion's insight conjunct), AND at least one trial — ideally the momentum-EURUSD candidate itself — must have its equity series restored and a corrected-units, multiple-testing-deflated, tail-aware DSR computed at or above the firm's gate. Until then, a canary measures plumbing, not edge, and starting it now is the wrong action.*

*This dissent is append-only and may not be softened.*

---

**How consensus handles NHT's position:**  
The consensus does NOT override NHT. All claims made about the canary — both in this consensus and in any downstream communication — are bounded by NHT's findings: the canary is a plumbing smoke-test; it does not validate edge, does not advance N, does not satisfy either kill-criterion conjunct, and cannot be presented as evidence of alpha. Any communication presenting it otherwise would be a policy violation.

---

## Open Items Requiring CEO Acknowledgment

### OA-1: DSR Re-adjudication Incomplete (FACTUAL CORRECTION)

NHT surfaced a material discrepancy between the claim packet's framing and the actual recompute file `.fintech-org/dsr_recompute_2026-06-01.jsonl`.

**The corrected-DSR picture is NOT uniformly sub-gate.** The recompute file shows:
- `d572999d` (vol_target_carry, Sharpe 0.759): new_dsr = **0.938** — ABOVE 0.50
- `f66dd64c` (Sharpe 0.598): new_dsr = **0.847** — ABOVE 0.50
- `87fa1d23` (momentum-EURUSD canary basis, OOS trial): new_dsr = **None** — MISSING equity, uncomputable

**Important caveat:** These bar-count DSRs are **optimistic upper bounds**. The series exhibit excess-kurtosis of 385–688 (skew up to 10.8), which violates DSR's Gaussian-tail assumption. The 2026-06-01 binding ruling requires re-running under effective-independent-sample T (~23 bets, not 4,231 bars). That T_eff re-run has NOT been done. Under T_eff, vol_target_carry collapses.

**CEO must acknowledge:** The statement "all trials are sub-gate" is incorrect. The correct statement is: "Two carry trials survive at ~0.85–0.94 on bar-count T, but these are optimistic upper bounds given extreme non-Gaussianity, and the corrected T_eff re-adjudication under effective-N is incomplete. The momentum candidate (the only OOS trial) is uncomputable due to missing equity. No trial is unconditionally above gate."

### OA-2: Saxo SIM Token — Operator Dependency (TIME-SENSITIVE)

The 24h Saxo SIM developer token is the **wall-clock bottleneck** for first real paper bar. It is an operator-only action (Saxo developer portal login, application selection, token issuance). No engineering path bypasses this. Token must be issued within 2h of intended run window due to 24h TTL.

**Timeline:** 3-5h to first bar if operator acts immediately; 18-32h if token requires next business day.

**CEO must acknowledge and act:** Token provisioning is the single action the CEO can take that directly unlocks the canary critical path.

### OA-3: Kill-Switch Drill Required Before Any Sizing>0

Kill-switch properties 3 (known SLA) and 4 (tested in prod-equivalent conditions) are currently UNMET — Knight Capital class gap. This does NOT block starting the zero-capital observe loop (no runaway loss path when no orders route and size=0). But it IS a **hard required precondition** before any future graduation to sizing>0 / order-routing.

**CEO must acknowledge:** A timed prod-equivalent kill-switch drill must be scheduled and recorded to `.fintech-org/kill-switch-tests.jsonl` before any sizing>0 is ever proposed. The canary must not be cited as "approved for paper trading" without this caveat.

### OA-4: Bet#1 Auto-Retire Deadline — 2026-07-01 (TIME-CRITICAL)

Trial 87fa1d23 (momentum-EURUSD, the only OOS trial in the entire registry) is the sole candidate for validated alpha. Its equity parquet is **genuinely missing** (zero files found in repo). Under HoQR retirement criteria, if the equity is not regenerated and re-adjudicated under corrected DSR/effective-N by 2026-07-01, it **auto-retires** and the firm formally has zero verified OOS candidates.

**CEO must acknowledge:** Regeneration of 87fa1d23 equity (deterministic re-run from git_hash 54df16a) is time-critical. This is the single cheapest path to a YES/NO on whether any validated edge exists. It is the highest-priority research item and competes for attention only with quant-developer capacity — it is a re-run, not new research.

---

## Decisions NOT Made / Out of Scope

The following were explicitly not decided by this consensus and are deferred:

- **No new alpha strategies or backtests.** The canary must not be cited as alpha deployment.
- **No trial re-adjudication.** Gated on F-001 DSR fix (separate track); this consensus does not re-adjudicate any prior trial.
- **No committing or pushing any code.** Operator action; not agent action.
- **No P3 intraday ORB implementation.** Three infra prerequisites unmet: 15m pipeline, session-calendar, intrabar engine (ratified 2026-05-30).
- **No architecture or implementation work.** The mock-sentinel fix (P4), routing-disabled flag, and any intrabar engine work are implementation tasks. They are scoped in this consensus but require a future CTO + quant-developer + principal-reviewer wave to execute. CTO was not staffed this session.
- **No BC-ES (Expected Shortfall/CVaR) resolution.** Acknowledged risk; out of scope per stated constraints. Becomes blocking before any capitalized sizing.
- **No SEV-3 watchdog observer loop exception guard fix.** Known since 2026-05-03; separate remediation track.
- **No paper P&L curve interpretation.** The ≥30-cycle calibration phase (P3) must complete first; interpretation is the NEXT wave.
- **No vendor onboarding, charter edits, or live capital movement.**

---

## Knowledge Gaps Surfaced (Routed to Skill-Gap Loop)

The following knowledge gaps were identified across role artifacts and are routed to the skill-gap loop for future resolution:

**From HoQR:**
- Whether the F-001-corrected DSR, once applied to 87fa1d23, leaves OOS Sharpe 0.314 above or below the effective-N-adjusted threshold — cannot know until regeneration + Mathematician re-derivation.
- Magnitude of the carry USDJPY data-quality outlier and whether it materially moves carry Sharpe — unmeasured.
- Saxo TotalValue marking convention not yet empirically confirmed (P2 open; awaits operator SIM token).

**From ET:**
- Exact Saxo developer portal flow for SIM token issuance (number of steps, whether a SIM application already exists, whether MFA is required) — affects token provisioning duration estimate.
- Whether the momentum-EURUSD equity parquet for trial 87fa1d23 is recoverable from git history at commit 54df16a.
- Whether Saxo SIM EUR/USD spreads are wider than 0.5pip at any time of day the daily-bar canary executes.

**From NHT:**
- Canonical count of the falsification/kill log (raw-data says 12 entries; direct inspection of kill_switch_audit.log found 2 operational entries); discrepancy should be reconciled — does not change the conclusion (0 STRONG-OOS rejections either way).

---

## Ratification Determination

**Status: awaiting-ratification**

**Quorum available:** CRO (required, risk) + HoQR + ET all approve. NHT dissent preserved.

**Ratification is DEFERRED TO CEO for the following reasons:**

1. **Kill-switch testing — materiality severity: high.** This consensus references a kill-switch testing requirement (kill-switch properties 3 & 4 unmet, drill required before sizing>0). Per the firm's deferred-decisions protocol, references to kill-switch testing at materiality severity:high require CEO ratification rather than quorum ratification.

2. **Architecture and implementation work out of scope.** The consensus references the P4 mock-sentinel fix, the routing-disabled architectural flag, and an intrabar engine — all implementation tasks. These are explicitly out of scope for this wave and require a future CTO + quant-developer + principal-reviewer wave. CTO was not staffed this session. A consensus that scopes implementation work it cannot also close requires CEO sign-off on the boundary.

3. **Strategic premise-reversal directed at CEO.** This consensus is a direct answer to the CEO's "speed it up" directive, finding the premise false. Strategic premise-reversals directed at the CEO require CEO ratification — not quorum auto-approval.

**CEO ratification prompt:**

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise \<X\>)**

---

## Signatures

| Role | Decision | Artifact |
|---|---|---|
| Head of Quant Research | approve-with-capacity-limit | `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/hoqr-prioritization.yaml` |
| Chief Risk Officer | size-reduced (0.0) | `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/cro-risk-assessment.yaml` |
| Execution Trader | route-with-reduced-size (0.0) | `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/et-execution-plan.yaml` |
| Null-Hypothesis Tester | dissent (material_concern, non-blocking) | `.fintech-org/artifacts/2026-06-01T-paper-launch-acceleration/nht-null-test-report.yaml` |
| PM / Chief of Staff | synthesis (awaiting-ratification) | this document |

*Dissent artifact:* `.agent-accountability/dissents/paper-launch-acceleration-2026-06-01:phase1:task1.0:null-hypothesis-tester.yaml`
