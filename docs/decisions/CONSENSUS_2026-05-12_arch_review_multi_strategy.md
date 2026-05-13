# CONSENSUS: Multi-Strategy Architecture Review 2026-05-12

**Status:** awaiting-ratification — blocked by 2 halt gates (NHT material_concern + PR needs-revision)
**Track:** `arch-review-multi-strategy-2026-05-12`
**Addressed unit:** `arch-review-multi-strategy-2026-05-12:phase1:task1.0`
**Authored:** 2026-05-12T23:55:00Z
**Produces decision:** false — see § Decision posture
**Ratification artifact target:** `.agent-accountability/ratifications/arch-review-multi-strategy-2026-05-12:phase1:task1.0.yaml`

---

## Task statement

Assess existing system architecture for suitability to expand from 2 validated strategies to
4 (adding intraday-classical + ML) via Strangler-Fig vs rewrite.

---

## Roles and decisions

| Role | Decision | Confidence | Does-block |
|---|---|---|---|
| PM | acceptance-criteria-authored | high | n/a |
| CTO | conditional-go | high | no (conditions enumerated) |
| CRO | size-reduced (6 new binding constraints) | high | yes (BC-9-N4-COND-1..6) |
| NHT | material_concern dissent | high | yes (deterministic from severity) |
| Principal Reviewer | needs-revision (4 blocking findings) | high | yes (routing to owning roles) |

---

## Aggregated findings table

| ID | Unified finding | Sources | Severity | Owning role | Effort (days) |
|---|---|---|---|---|---|
| AGG-1 | Strategy ABC Liskov violation: 6/10 strategies override `__init__` with `rate_data`; registry passes only `params`; production caller uses reflection + allowlist bypass | NHT-ARCH-2 + PR-F-001 | blocking-for-N≥3 | cto | 2-5 |
| AGG-2 | 71.3% paper-script duplication (557 changed lines / 1943 total); BC-8-LIFT-COND-1..7 inline-replicated across N scripts; Knight-Capital-class silent drift at N=4 | NHT-ARCH-3 + PR-F-002 + CTO-Major-2 | blocking-for-N≥3 | cto | 3 (CTO est) / 5-10 (NHT est) |
| AGG-3 | ML infrastructure empirically absent: no `src/forex_system/ml/`, no `portfolio/`, zero matches for 8 ML-infrastructure terms, zero ML-library imports | NHT-ARCH-4 + PR-F-004 + CTO-Blocking-1 + CRO-BC-9-N4-COND-4 | blocking-for-ML | ml-researcher + cto | multi-month |
| AGG-4 | `Position` has no `strategy_id` field; `exposure_aggregator` uses `pair` as proxy; 2-strategy overlap would miscount active strategies; `max_active_strategies=4` gate fires incorrectly | CTO-Major-1 + PR-F-003 + CRO-BC-9-N4-COND-1 | blocking-for-N≥3 | quant-developer (under CTO) | 1 |
| AGG-5 | No per-strategy cap allocation rule in `exposure_aggregator`; last-write-wins under lock = first strategy consumes entire 15% JPY budget; denial-of-dispatch for others | CRO-Q1 | blocking-for-N≥3 | quant-developer (under CTO) | 1 |
| AGG-6 | Saxo 429 not handled in `SaxoClient`; N=4 burst alignment can hit 240% of 120 req/min bucket; no retry-with-Retry-After, no startup jitter, no shared rate-limit token-bucket | CRO-Q3 | blocking-for-N≥3 | quant-developer (under CTO) | 1-2 |
| AGG-7 | Drawdown ladder semantics ambiguous (per-strategy vs aggregate); per-strategy default means correlated DD across strategies bypasses aggregate ladder — LTCM-class blind spot | CRO-Q4 + CTO-BC note | blocking-for-N≥3 | quant-developer (under CTO) | 1 |
| AGG-8 | Kill-switch lacks ML-specific trigger reasons (MODEL_DRIFT, CALIBRATION_DECAY, FEATURE_STALENESS, INFERENCE_LATENCY, PREDICTION_OUT_OF_RANGE); in-process design fails Property-1 for runaway-but-non-crashing ML inference | CRO-Q5 | blocking-for-ML | ml-researcher + cto | multi-month |
| AGG-9 | Risk plumbing is strategy-type-agnostic; kill-switch/aggregator/contract cannot distinguish ML from classical; ML failure modes undetectable without `strategy_type` in `Position` | CRO-Q6 | blocking-for-ML | quant-developer + ml-researcher | 1 + design sprint |
| AGG-10 | No-lookahead sacred test is engine-layer only; per-strategy lookahead probe absent; ML feature-pipeline leakage invisible to current test | NHT-ARCH-5 + PR-F-006 | concern | quant-developer | 1 |
| AGG-11 | Kill-switch Property-4 (tested in prod) not yet executed even for N=2 paper session; expanding to N=4 without first proving N=2 is aspirational safety | CRO-BC-9-N4-COND-5 | blocking-for-N≥3 | ops-engineer | 0.5 |
| AGG-12 | Single dispatch flock with identical 1800s intervals; N=4 burst collision at bar-close; 3/4 strategies skip the same cycle | CTO-Minor-1 | minor | quant-developer | 0.5 |
| AGG-13 | No portfolio-level walk-forward; `backtest/portfolio.py` is `FixedFractionalSizer` not portfolio aggregator; naming misleads | CTO-Minor-2 | minor | quant-developer + HoQR | 5 |
| AGG-14 | Orchestrator did not redact wave-2 stance prose before principal-reviewer wave-3; independence preserved only by reviewer self-discipline | PR-F-005 | concern | orchestrator | 0 (process change) |

---

## PR adjudication — 4 disputed claims

| Claim | CTO position | NHT position | PR independent verdict | Resolution |
|---|---|---|---|---|
| Strategy ABC is a clean Liskov-safe extension point | Upheld — ABC in interfaces.py:32-63 is minimal and pure-functional | Rejected — 6/10 overrides violate contract; reflection bypass at run_falsification_trial.py:439-474 is structural proof | **CTO position REJECTED.** ABC in isolation is single-arg; reading ABC + all overrides + factory + reflection bypass together reveals the contract is leaky. NHT structural finding upheld exactly: 6/10 strategies, allowlist + inspect.signature, file:line verified. | NHT upheld; CTO's narrow-ABC view rejected |
| 71% duplication / 557 changed lines | Agreed — REM-2 cites duplication; estimates 3-day refactor | Agreed — cites same 557 lines; estimates 1-2 weeks | **Both agree on the fact.** diff measurement reproduced exactly: 312 vt-unique + 245 carry_fred-unique = 557. 71.3% = (1943-557)/1943. Effort estimates not adjudicated (outside PR role contract). | Unanimous on duplication fact; effort estimates diverge (not adjudicated) |
| ML infrastructure is absent | Agreed — interfaces.py:1-145 has zero ML lifecycle contracts; recommends ModelServingInterface before strategy #4 | Agreed — grep evidence chain; building ML foundations is multi-month | **All three agree.** Empty grep across 8 ML-infrastructure terms + 5 ML-library import patterns + no ml/ or portfolio/ subdir. | Unanimous; absence is a verified fact |
| `Position` has no `strategy_id` field | Agreed — types.py:67-76 gap; uses pair proxy in exposure_aggregator.py:121-130; REM-1 | Not directly addressed at this resolution; adjacent Liskov finding covers ABC construction | **CTO and CRO agree; NHT silent at this resolution.** types.py:67-76 enumerates 6 fields, none carry strategy provenance. Trade type at line 49 carries `strategy`; asymmetry self-documented at exposure_aggregator.py:121-130. | CTO upheld; NHT silent; gap confirmed |

---

## Consolidated remediation backlog

| ID | Sources | Category | Effort (days) | Owning role | Precedes |
|---|---|---|---|---|---|
| REM-1 | AGG-4; CTO-REM-1; CRO-BC-9-N4-COND-1 | type-system fix | 1 | quant-developer | REM-2, REM-5, REM-6, REM-7 |
| REM-2 | AGG-2; CTO-REM-2; NHT-ARCH-3; PR-F-002 | architecture extraction | 3–10 | quant-developer (CTO oversight) | REM-4, REM-5 |
| REM-3 | AGG-3; CTO-REM-3; CRO-BC-9-N4-COND-4 | ML lifecycle interface | 2 (interface only) | quant-developer (CTO-authored ABC) | strategy #4 paper deploy |
| REM-4 | AGG-12; CTO-REM-4 | config stagger | 0.5 | quant-developer | — |
| REM-5 | AGG-5; CRO-BC-9-N4-COND-1 | risk allocation rule | 1 | quant-developer | REM-6 |
| REM-6 | AGG-6; CRO-Q3; CRO-BC-9-N4-COND-2 | Saxo rate-limit hardening | 1–2 | quant-developer | — |
| REM-7 | AGG-7; CRO-Q4; CRO-BC-9-N4-COND-3 | drawdown ladder semantics + aggregate layer | 1 | quant-developer | — |
| REM-8 | AGG-11; CRO-BC-9-N4-COND-5 | kill-switch Property-4 live test (N=2) | 0.5 | ops-engineer | REM-9 |
| REM-9 | AGG-10; PR-F-006; NHT-ARCH-5 | per-strategy no-lookahead probe | 1 | quant-developer | strategy #3 paper deploy |
| REM-10 | AGG-8, AGG-9; CRO-Q5, Q6; NHT-ARCH-4 | ML kill-switch + risk plumbing (greenfield) | multi-month | ml-researcher + cto | strategy #4 paper deploy |

**Gating rule:** REM-1 + REM-2 + REM-5 + REM-6 + REM-7 + REM-8 MUST complete before any N≥3 paper deployment.
REM-3 + REM-9 + REM-10 gate strategy #4 (ML) deployment only.
REM-4 is recommended (minor safety) but non-blocking.

---

## Acceptable narrowed scope

Per NHT recommendation and CRO binding constraints:

**For strategy #3 (intraday-classical):** Strangler-Fig conditional-yes, after completing
REM-1, REM-2, REM-5, REM-6, REM-7, REM-8. Estimated prerequisite engineering: 7–17 days
depending on REM-2 effort resolution.

**For strategy #4 (ML):** DEFERRED. Requires greenfield `src/forex_system/ml/` design review,
ModelServingInterface ABC (REM-3), ML-specific kill-switch triggers and risk plumbing (REM-10),
and SR 11-7-style model-risk gate. This is multi-month work and is NOT a Strangler-Fig step.

**Rewrite alternative:** NOT recommended. Estimated 3–4 months minimum to re-establish
84 tests, WS-xx decision-trace infrastructure, kill-switch audit log discipline, Saxo OAuth
integration, and CRO binding-constraint wiring. Rewrite inverts the Phase-0 thesis
("prove alpha before complexity"). The existing gaps are targeted, not structural deficiencies.

---

## Blowup analog

**Knight Capital Americas LLC (SEC Release 34-70694, File 3-15570, Oct 16 2013)** — dominant fit.

Knight lost >$460M in ~45 minutes because (a) a deploy touched N parallel order-routing
components without uniform verification, and (b) the kill switch was not reachable independently
of the runaway component.

Both failure modes apply directly to the proposed expansion:
- Adding strategy #3 or #4 without updating `exposure_aggregator`'s per-strategy allocation
  logic = Knight's stale-server problem (N-way silent divergence surface).
- In-process kill-switch design fails Property-1 (out-of-band) for an ML strategy that can
  issue runaway-but-non-crashing signals — direct Knight-class.

Secondary analogs: LTCM (correlated DD across strategies bypassing per-strategy ladder per Q4);
Archegos (single-OAuth/single-account-key concentration). Knight is canonical because the SEC
filing explicitly establishes that single-deploy-with-stale-component is the failure pattern.

---

## Decision posture

**Option A:** Approve expansion to 4 strategies now, accept structural gaps as known risk.
- Risk: Knight-Capital-class silent drift; LTCM-class aggregate-DD blind spot; ML strategy
  deployed with no model-risk gate. PM recommendation: REJECTED.

**Option B (PM RECOMMENDS):** Approve Strangler-Fig for strategy #3 ONLY, conditional on
completing REM-1 + REM-2 + REM-5 + REM-6 + REM-7 + REM-8 first. Defer strategy #4 (ML)
pending greenfield ml/ design review and REM-3 + REM-10. Authorize CEO to review this
consensus and issue explicit authorization of strategy #3 prerequisites as a tracked backlog
sprint.

**Option C:** Reject Strangler-Fig; commission rewrite.
- Risk: 3–4 months cost, inverts Phase-0 thesis, high probability of re-introducing the
  same structural gaps without the existing ratified-risk-envelope heritage.
  PM recommendation: REJECTED.

---

## NHT dissent verbatim (append-only; per fintech-org rule 6)

> Null-Hypothesis Tester DISSENTS from the atomic claim that "the
> existing forex-trading-system Phase-0 baseline is robust, flexible,
> and scalable enough to absorb the 2 -> 4 strategy expansion via
> Strangler-Fig without rework of existing foundations."
>
> Three blocking findings, with file:line evidence:
>
> 1. Strategy ABC is Liskov-violated in production. The abstract
>    contract at src/forex_system/core/interfaces.py:35 declares
>    __init__(self, params), but 6 of 10 registered strategies
>    override __init__ with a second positional argument (rate_data).
>    The registry factory at src/forex_system/strategies/registry.py:31
>    passes ONLY params, never rate_data. Production caller code at
>    scripts/run_falsification_trial.py:439-474 maintains a hardcoded
>    _SELF_LOADING_RATE_STRATEGIES allowlist and uses
>    inspect.signature on __init__ to choose between two construction
>    paths — structural proof the ABC contract is already leaky. Adding
>    strategies #3 and #4 with new construction-time dependencies
>    (intraday tick-data source, ML model artifact path/version) will
>    compound the leak. The atomic claim's "no rework of foundations"
>    cannot hold.
>
> 2. The two paper-loop scripts (1005 LoC + 938 LoC = 1943 LoC) are
>    ~71% duplicated (557 changed lines out of ~1000 each). BC-8-LIFT-
>    COND-1..7 risk-envelope code (kill switch, drawdown contract,
>    account-key parity gate, heartbeat watchdog, fcntl dispatch lock,
>    JPY-correlated cap, swap accrual) is inline-replicated, not
>    shared-library-extracted. At N=4 strategies, projected ~4000 LoC
>    with 4 copies of the same risk envelope. Knight-Capital-class
>    drift risk. The PM-quoted "Strangler-Fig step 1: template paper
>    scripts (1-2d)" estimate is unsafe — that step is actually 1-2
>    weeks of foundation rework (shared risk envelope extraction +
>    paper-loop regression fixture + integration test for BC-8-LIFT-
>    COND-1..7), contradicting the atomic claim.
>
> 3. ML infrastructure is empirically absent. ls src/forex_system/
>    shows no ml/ subdirectory and no portfolio/ subdirectory. Grep
>    across src/ returns zero matches for model_card, drift_monitor,
>    calibration_tracker, safetensors, .onnx, model_version,
>    model_registry, model_serving, inference_server. Zero imports of
>    sklearn, torch, tensorflow, xgboost, lightgbm anywhere under
>    src/. Absorbing an ML strategy "without rework of foundations" is
>    literally false — the foundations do not exist. Building them
>    (model artifact contract, versioning, training-vs-serving parity
>    test, feature-pipeline reproducibility, drift monitor, calibration
>    tracker, rollback, ML-kill-switch) is multi-month work, not a 2-3
>    week Strangler-Fig step.
>
> Asymmetric-cost analysis (NHT-ARCH-8): false-positive (approve and
> be wrong) carries governance and design-debt cost with a long tail;
> false-negative (reject and be wrong) costs ~1-2 weeks of delay.
> Standard NHT doctrine: err toward false-negative.
>
> Acceptable narrowed claim: the baseline can absorb ONE additional
> intraday-classical strategy via Strangler-Fig CONDITIONAL on prior
> remediation of (a) the Strategy ABC Liskov violation, (b) shared
> risk-envelope extraction from the paper scripts, (c) a parameterized
> per-strategy no-lookahead probe, and (d) a paper-loop regression
> fixture + integration test for BC-8-LIFT-COND-1..7. The ML strategy
> is DEFERRED pending a greenfield src/forex_system/ml/ design review.
>
> Forward-looking only. Does NOT gate current T=0 paper trading per PM
> hard-constraint line 25 ("does_not_gate_current_t0_paper_trading:
> true"). No live-capital recommendations. Per fintech-org rule 6,
> this dissent is append-only and must be preserved verbatim in any
> consensus artifact.

---

## CRO blocking findings verbatim (append-only)

> CRO BLOCKING FINDINGS — 2→4 strategy expansion is structurally indefensible as-is.
>
> Q1 — NO per-strategy allocation rule exists. exposure_aggregator.compute_exposure
> (line 121-130) uses pair as proxy. At N=4, first strategy to dispatch consumes entire 15%
> JPY budget under last-write-wins; subsequent strategies blocked without a fairness rule.
> 4-strategy paper experiment is scientifically void without this fix.
> [severity: blocking; file: src/forex_system/risk/exposure_aggregator.py:46,121-130,148-216]
>
> Q3 — N=4 burst alignment can generate 144 req/min instantaneous (240% of 120/min Saxo
> bucket). SaxoClient has NO 429 handling or backoff (raise_for_status() at lines 155, 211,
> 220, 230 propagates as unhandled HTTPError). Failure mode: intermittent cycle failure under
> synchronized polling.
> [severity: blocking; file: src/forex_system/saxo/client.py:67-74,94-110,394]
>
> Q4 — DrawdownContract is per-instance (_peak_equity per instance). Both paper loops
> instantiate per-loop = per-strategy by default. JPY shock at N=4 could produce 8% per
> strategy individually while aggregate book is at 18% — ladder bypassed for systemic shocks.
> LTCM-class aggregate-DD blind spot.
> [severity: blocking; file: src/forex_system/risk/drawdown_contract.py:42-46,116-127,129-216]
>
> Q5 — kill_switch.py TriggerReason enum (line 43-49) has no ML failure modes
> (MODEL_DRIFT, CALIBRATION_DECAY, FEATURE_STALENESS, INFERENCE_LATENCY,
> PREDICTION_OUT_OF_RANGE, GRADIENT_OF_OUTPUT). In-process design fails Property-1
> for runaway-but-non-crashing ML inference. Property-4 (tested in prod) not yet
> executed even at N=2.
> [severity: blocking-for-ML-strategy-class;
>  file: src/forex_system/risk/kill_switch.py:43-49,131-207,270-325]
>
> Q6 — Risk plumbing is strategy-type-agnostic. exposure_aggregator.compute_exposure
> (line 94-140) consumes only {pair, size, entry_price}; no strategy_type/model_id.
> ML failure modes (Q5) cannot be routed correctly without strategy_type in Position.
> fintech-org rule 3 (Execution-Researcher Firewall) unenforceable at the risk boundary.
> [severity: blocking-for-ML-strategy-class;
>  file: src/forex_system/risk/exposure_aggregator.py:94-140,
>  src/forex_system/risk/kill_switch.py:209-236]
>
> New binding constraints: BC-9-N4-COND-1..6 (all must be satisfied before any N≥3
> paper deployment; ML strategy additionally requires SR 11-7-style model-risk gate).
> Closest historical analog: Knight Capital (SEC Release 34-70694). No live-capital
> recommendation. T=0 unchanged.

---

## Knowledge gaps surfaced (routed to skill-gap loop)

All gaps below are routed to `.fintech-org/skill-gaps.jsonl` with `session_id="arch-review-multi-strategy-2026-05-12"`.

| ID | Originating role | Gap topic | Routed to protocol |
|---|---|---|---|
| KG-PM-1 | pm | Whether Strategy #4 (ML) requires model serving infrastructure with no current interface in core/interfaces.py | skill-gap.md |
| KG-PM-2 | pm | Whether dispatch-lock mechanism (fcntl.flock) is designed for N>2 or N=2 was the design ceiling | skill-gap.md |
| KG-PM-3 | pm | Whether _JPY_CORRELATED frozenset needs expansion for Strategy #3 or #4 pair universe | skill-gap.md |
| KG-PM-4 | pm | Actual LOC and structural similarity between 3 paper trading scripts | skill-gap.md |
| KG-PM-5 | pm | Whether walkforward.py supports multi-strategy portfolio-level walk-forward | skill-gap.md |
| KG-CTO-1 | cto | Whether walkforward.py supports multi-strategy portfolio-level evaluation | skill-gap.md |
| KG-CTO-2 | cto | What specific algorithm class strategy #3 (intraday-classical) is | skill-gap.md |
| KG-CTO-3 | cto | Cross-host flock caveat (NFS silent failure) — scaling boundary | skill-gap.md |
| KG-CTO-4 | cto | Quantified lock contention probability at 4H frequency with 4 strategies | skill-gap.md |
| KG-CRO-1 | cro | Saxo session boundary — one session = one bearer token, one IP, or one process? | skill-gap.md |
| KG-CRO-2 | cro | Empirical SKIP_DISPATCH_LOCK_BUSY rate at N=2 — never measured | skill-gap.md |
| KG-CRO-3 | cro | Whether kill_switch.py has been triggered against live N=2 paper session even once | skill-gap.md |
| KG-CRO-4 | cro | What "ML strategy" means in this proposal — classifier, regressor, or RL? | skill-gap.md |
| KG-CRO-5 | cro | Whether intraday-classical strategy will trade USDJPY/GBPUSD or cross-JPY pairs | skill-gap.md |
| KG-PR-1 | principal-reviewer | Full create_strategy() call-site enumeration (latent breaks for rate-data-needing strategies) | skill-gap.md |
| KG-PR-2 | principal-reviewer | End-to-end paper-loop behavior under duplicated risk envelope (requires integration test fixture) | skill-gap.md |
| KG-PR-3 | principal-reviewer | Refactor effort estimate adjudication (3 days CTO vs 1-2 weeks NHT) | skill-gap.md |
| KG-NHT-1 | null-hypothesis-tester | Whether any concrete regression fixture tests BC-8-LIFT-COND-1..7 as a unit | skill-gap.md |

---

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets: "revise nht-block" "revise cro-bc9" "revise decision-posture" "revise rem-2-effort"

---

## produces_decision: false

Rationale: two halt gates are firing (NHT material_concern + PR needs-revision with 4 blocking
findings). Under `--full-auto` protocols, auto-ratification falls back to human-prompt path.
This CONSENSUS document surfaces the full evidence chain for CEO ratification. No downstream
execution dispatches are authorized until the CEO issues an explicit "yes" or "revise" response
to the ratification prompt above.

Linked dissent artifacts:
- `.agent-accountability/dissents/arch-review-multi-strategy-2026-05-12:phase1:task1.0:null-hypothesis-tester.yaml`
- `.agent-accountability/dissents/arch-review-multi-strategy-2026-05-12:phase1:task1.0:cro.yaml`

Source wave artifacts:
- `.fintech-org/artifacts/2026-05-12T-arch-review-multi-strategy/pm-acceptance-criteria.yaml`
- `.fintech-org/artifacts/2026-05-12T-arch-review-multi-strategy/cto-architecture-review.yaml`
- `.fintech-org/artifacts/2026-05-12T-arch-review-multi-strategy/cro-risk-assessment.yaml`
- `.fintech-org/artifacts/2026-05-12T-arch-review-multi-strategy/nht-null-test-report.yaml`
- `.fintech-org/artifacts/2026-05-12T-arch-review-multi-strategy/principal-reviewer-review-report.yaml`
