# Consensus on: Sunday-Night Pre-Open Preparation + Week-Ahead Dispatch

**Track ID:** `sunday-pre-open-prep-2026-04-26`
**Drafted:** 2026-04-26T22:30:00Z
**Status:** PENDING CEO RATIFICATION

---

## Roles staffed

- **PM** (sonnet) — coordinator + acceptance-criteria author + this draft
- **CRO** (opus) — risk on residual SIM positions, kill-switch architecture for Path B; redacted-evidence dispatch
- **Null-Hypothesis Tester** (opus) — falsification of "production-ready week 17" with N=14 Bonferroni; structurally-skeptic role; dissent append-only
- **Head of Quant Research** (opus) — three-way dispatch ruling + Bet #1 regime-OOS ruling
- **CTO** (sonnet) — observability/firewall audit applying `log-as-decision-trace` + `execution-firewall-review`
- **Ops Engineer** (haiku) — pre-open mechanical checklist (PRE-01..03)

Trial counter at dispatch time: **N=14** (`.fintech-org/trials.jsonl`)

---

## Acceptance criteria (from PM)

Pre-open (deadline **2026-04-26T22:00Z**):
- PRE-01 SIM book confirmed FLAT
- PRE-02 Kill-switch state confirmed FLAT_AND_HALTED dated today
- PRE-03 Log-write paths healthy
- PRE-04 CRO pre-open risk attestation
- PRE-05 CTO observability check (no NEW gaps since `a5128e4`)

Week-ahead (deadline **2026-04-27T13:00Z**):
- GATE-01 vol_target_carry retire-pending-reconciliation flag formally resolved
- GATE-02 carry_fred Bet #1 regime-OOS HoQR ruling
- WA-01 three-way dispatch decision (Path B vs Bet #2 vs Bet #3)
- WA-02 NHT falsification of production-ready claim with N=14
- WA-03 weak-spot inventory (CTO; CEO's specific ask)

Out-of-scope: live capital, untracked exploratory scripts from today, new code/refactoring this dispatch wave, Phase 0→1 transition.

---

## Decision

**No paper-trading orders resume tonight.** Two operator actions are required before any paper-side activity in week 17 begins: (1) fresh Saxo SIM bearer token + execution of `scripts/saxo_position_inventory.py` (and `saxo_flatten_all.py` if non-empty) to produce a system-verified flat-book record dated 2026-04-26; (2) a kill-switch audit-log VERIFY entry dated today citing the position-inventory output. Until both clear, the CRO veto holds and ops-engineer's PRE-01/PRE-02 precondition failures stand.

**Week 17 plan is research-dispatch + observability hardening, not paper trading.** HoQR dispatches **Bet #2 (4H TAS-ceiling on USDJPY/EURUSD/GBPUSD)** as a backtest-only research run — this does not require a flat SIM book. Bet #3 queues for week +2 (Bonferroni-deflation ordering); Path B defers to week +3–4 (its own design doc binds the firm to "no carve-out" on P3-P6, and CRO's architecture verdict adds 7 unmet kill-switch prerequisites). Concurrent unblocking work approved as parallel CTO/QD effort: P5 pre-commit equivalence-gate, P6 per-strategy KillSwitch class.

**Bet #1 (carry_fred) is conditional-pass** with binding new retirement trigger CF-T9 (BoJ policy rate ≥ 0.50% sustained 2 quarters AND aggregate JPY-cross 60-day rolling Sharpe < 0.20 within a 90-trading-day window → retire within 5 trading days). The pre-registration is amended in place; paper enrollment of Bet #1 unlocks only after the CF-T9 monitor is scripted by ops-engineer AND PRE-01 clears.

**Vol_target_carry retire-pending-reconciliation flag is recommended for CEO+HoQR ratification to LIFT** — engine/script equivalence Δ=0.0055 per commit `a5128e4` is well within the 0.10 tolerance — but the lifting itself is a CEO ratification act, not an artifact of this consensus.

**Three observability fixes block the week** (CTO weak-spot inventory):
- WS-01 signal-to-execution trace at `run_paper_trading_vt.py` `run_cycle()` — before any new paper cycle in week 17
- WS-02 TradeIntent spec for `vol_target_carry` — before Bet #2/#3 implementation
- WS-03 kill-switch trigger() events written to `kill_switch_audit.log` — before next kill-switch test
Plus one tactical: C1 fix em-dash in Title header at `run_paper_trading_vt.py:197` (route to QD).

---

## Action list (the CEO's deliverable)

**For the CEO (operator) — must act before market trades resume:**

| # | Action | Owner | Deadline | Blocking? |
|---|--------|-------|----------|-----------|
| A1 | Issue fresh Saxo SIM bearer token; export `SAXO_TOKEN` | CEO | before any paper cycle | YES |
| A2 | Run `scripts/saxo_position_inventory.py`; if non-empty, run `scripts/saxo_flatten_all.py` per `docs/runbooks/flatten_saxo_sim.md` | CEO + Ops | before any paper cycle | YES |
| A3 | Append `kill_switch_audit.log` VERIFY entry dated 2026-04-26 citing A2 output | CEO + Ops | before any paper cycle | YES (ALSO BLOCKED ON Q2 — see below) |
| A4 | Ratify (or veto) lifting of vol_target_carry retire-pending-reconciliation flag | CEO + HoQR | 2026-04-27 morning | gates Bet #1/Bet #2 paper enrollment |
| A5 | Approve this CONSENSUS.md (or revise) | CEO | now | gates all follow-on dispatches |

**Paper-cycle resumption gate chain (all required):** A1 → A2 → A3 → **Q2 (WS-01 signal-to-execution trace must be merged)** → cycle may resume. Clearing only A1–A5 is NOT sufficient; Q2 is a hard blocker per CTO condition C1.

**For QD (queued, ratification-gated):**

| # | Action | Severity | Cost | Owner | Notes |
|---|--------|----------|------|-------|-------|
| Q1 | Fix em-dash in Title header `run_paper_trading_vt.py:197` (sanitize or encode) | C1 (CTO) | S | QD | Add Title-arg coverage to `tests/scripts/test_notify.py` |
| Q2 | **WS-01 (PAPER-CYCLE BLOCKER):** add structured `logger.info()` at `run_cycle()` decision boundary (signal/vol/equity/price/units/action/cycle_id) | critical | M | QD | Read-only change; **HARD BLOCKER on paper-cycle resumption — see gate chain above** |
| Q3 | WS-03: add structured-JSON append in `kill_switch.py` `trigger()` so audit log captures trigger events | high | S | QD | Test against parser at `kill_switch.py:72` first |
| Q4 | Implement P5: pre-commit hook blocking strategy/sizer commits without passing equivalence test | Path B prereq | M | QD | Parallel work |
| Q5 | Implement P6: per-strategy `KillSwitch` class (8+ test cases) | Path B prereq | M | QD | Parallel work |
| Q6 | Script CF-T9 monitor (`scripts/monitor_regime_triggers.py`): FRED BoJ policy rate + JPY-cross 60d rolling Sharpe | binding for Bet #1 paper enrollment | M | Ops + QD | Required before Bet #1 paper trading |
| Q7 | WS-05: synthetic live-loop integration test | reproducibility | M | QD | Catches the "third code path" gap |

**For QR (queued):**

| # | Action | Owner | Notes |
|---|--------|-------|-------|
| R1 | Author TradeIntent YAML for `vol_target_carry` (entry conditions, sizing formula, slippage P50/P90/P99 by regime, retirement triggers VTC-T1..T8, pre-reg path) | QR | WS-02; gates Bet #2/#3 implementation |
| R2 | Author/locate Bet #2 4H TAS-ceiling pre-registration before dispatch | QR | HoQR knowledge_gap; firm rule: no backtest without pre-reg |
| R3 | Backfill 8 untracked scripts into `trials.jsonl` with `status=exploratory` | QR + QD | WS-06; closes Bonferroni-honesty gap |

**For HoQR (queued):**

| # | Action | Notes |
|---|--------|-------|
| H1 | Sign carry_fred pre-reg amendment appending CF-T9 (binding, 2026-04-26) | After CEO ratifies this consensus |
| H2 | Dispatch Bet #2 backtest with N=14+3 Bonferroni accounting | **HARD GATE: no `scripts/run_backtest.py` invocation for Bet #2 until R2 artifact exists at `references/pre-registrations/tas_ceiling_4h.md` with file mtime predating any backtest code execution. Pre-reg-after-results = post-hoc falsification = firm rule 4 violation.** Additionally: verify `scripts/run_backtest.py --config <Bet#2 config>` import graph does not touch `scripts/run_paper_trading_vt.py` or any Saxo backend module before first run (closes WS-05 third-code-path risk). |

**For NHT (queued):**

| # | Action | Notes |
|---|--------|-------|
| N1 | Compute CF-T5 (one-sample t-test on carry_fred per-pair Sharpe distribution vs zero) | HoQR knowledge_gap |
| N2 | Rule on authoritative Bonferroni denominator (count-of-trials vs count-of-parameter-sets) | Affects all downstream NHT verdicts |
| N3 | Execute T1/T2/T5/T6 per `nht-null-test-report.yaml` `tests-requested` (matched-random benchmark, feature-permutation, rolling-OOS decay, BoJ-pivot decomposition) | After QD dispatched |

---

## Evidence supporting the decision

- `.fintech-org/artifacts/2026-04-26/pm-acceptance-criteria.yaml` — schema-validated; CRO redacted variant
- `.fintech-org/artifacts/2026-04-26/cro-risk-assessment.yaml` — VETO; conditional 0.25 multipliers on both gate-passers; kill-switch architecture INADEQUATE for Path B (7 gaps, 6 remediations); blowup-analog Knight Capital 2012
- `.fintech-org/artifacts/2026-04-26/nht-null-test-report.yaml` — production-ready=false; DSR vol_target_carry=0.569, carry_fred=0.596 (both << 0.95); Bonferroni t-stats fail (1.31, 1.38 < 2.69); regime-bet structurally untestable within OOS window
- `.fintech-org/artifacts/2026-04-26/hoqr-bet1-regime-ruling.yaml` — conditional-pass with binding CF-T9; pre-reg amended in place
- `.fintech-org/artifacts/2026-04-26/hoqr-week-ahead-prioritization.yaml` — Bet #2 dispatched; Bet #3 week+2; Path B week+3-4; 6 BET2-T1..T6 retirement triggers
- `.fintech-org/artifacts/2026-04-26/cto-pre05-checklist-result.yaml` — log paths PASS write check; em-dash partially fixed; all 4 session logs noise/mixed except kill-switch audit
- `.fintech-org/artifacts/2026-04-26/cto-wa03-weak-spot-inventory.yaml` — 6 weak spots ranked; top 3 critical for week 17
- `.fintech-org/artifacts/2026-04-26/ops-engineer-runbook-result.yaml` — PRE-01 + PRE-02 PRECONDITION_FAILED (need fresh token + dated verification entry); PRE-03 PASS

Source artifacts: `c41212f` Bet#1, `a5128e4` Track 5, `c131200` Path B design, `CONSENSUS_2026-04-25.md`, `docs/runbooks/flatten_saxo_sim.md`, `.fintech-org/trials.jsonl` (14 lines).

---

## Decisions NOT made (deferred, out of scope)

- **Live-capital deployment** — firm rule 1 (paper-only Phase 0); not on the table
- **Phase 0 → Phase 1 transition** — gates on GATE-01 + GATE-02 + at least 25 registered trials + Path B prereqs; not this consensus
- **Lifting of vol_target_carry `retire-pending-reconciliation`** — recommended (engine/script Δ=0.0055 well under tolerance) but is a CEO+HoQR ratification ACT, not a consensus artifact
- **Bet #2 implementation code** — research-dispatch only this week; implementation queued behind WS-02 (TradeIntent spec)
- **Untracked exploratory scripts from 2026-04-26** — CEO out-of-scope; backfill is queued as R3 but dispatch did not analyze them
- **Trade-execution venue diversification** — Saxo SIM only; out of scope
- **NHT denominator authoritative ruling** (count-of-trials vs count-of-parameter-sets) — flagged as N2 for next dispatch; this consensus uses official 14

---

## Debate history

**No structured debate rounds were run.** The orchestrator's pre-consensus disagreement scan found convergence on every material decision point:

| Decision point | CRO | NHT | HoQR | CTO | Ops | Convergent? |
|---|---|---|---|---|---|---|
| Pre-open paper resume | VETO | n/a | "no paper onto non-flat SIM" | C1 blocking | PRE-01/02 fail | YES |
| Production-ready week 17 (paper) | VETO | dissent (DSR fail) | research-only this week | WS-01 blocking | n/a | YES |
| Bet #1 status | 0.25 conditional + regime-flag | **dissent — regime claim "logically untestable"** | conditional-pass + CF-T9 | n/a | n/a | **UNRESOLVED METHODOLOGICAL DISPUTE** — HoQR exercises dispatch authority + adds binding CF-T9 retirement trigger; NHT objects on testability grounds (OOS window fully inside the regime being tested). Resolved by jurisdiction split (governance), not by methodological agreement. CEO ratifies the governance resolution, not a finding of agreement. |
| Bet #2 dispatch (backtest) | n/a | needs pre-reg | DISPATCH (subject to R2 hard gate) | WS-02 needed before implementation | n/a | YES (sequencing — H2 hard-gated on R2 timestamp) |
| Path B | architecture INADEQUATE | n/a | defer week+3-4 | WS-02..06 needed | n/a | YES |

Where roles emphasize different facets, the **strictest binding constraint is honored** (CRO veto sets the gate; NHT dissent preserved; HoQR retirement criteria binding; CTO conditions binding).

---

## Assumptions we're betting on

1. The Saxo SIM positions reported in yesterday's CONSENSUS (USDJPY 1.13M + GBPJPY + CADJPY) are still open. If they were quietly closed by another path, A2 will confirm and de-escalate.
2. BoJ policy rate has held ≤ 0.50% throughout the OOS window 2023-04-25 → 2026-04-17. CF-T9 trigger is calibrated against this regime; if BoJ policy already changed during the window, the regime-OOS ruling is wrong and the trigger needs recalibration.
3. The trial counter (`.fintech-org/trials.jsonl` = 14) is the authoritative N for Bonferroni and DSR. NHT's WA-02 verdict depends on this being correct; if true historical N is higher (HoQR estimate 250-500 unbackfilled), both gate-passers fail by larger margins.
4. The 4H parquet data quality for USDJPY/EURUSD/GBPUSD is comparable to the validated daily data. If 4H has microstructure artifacts (synthetic gaps, weekend handling, broker-quote drift), Bet #2 results are not trustworthy.
5. Path B's design-doc-pinned veto rule ("if ANY of P1-P6 missing, design rejected — no carve-out") will be honored. If anyone tries to dispatch Path B early on a partial-prereq basis, the entire decision needs re-litigation.
6. The kill-switch architecture (single-process, log-file convention) is adequate for serial single-strategy operation. CRO has flagged it INADEQUATE for parallel multi-strategy (Path B); if even single-strategy operation has a hidden race, this assumption is wrong.

---

## Pre-registered falsification

**Bet #1 (carry_fred) — binding from 2026-04-26:**

- CF-T1..T8: existing pre-reg at `references/pre-registrations/carry_fred.md`, unchanged
- **CF-T9 (NEW):** retire within 5 trading days when ALL three clauses hold simultaneously within a 90-trading-day window:
  - BoJ policy rate (FRED `IRSTCB01JPM156N` or equivalent) ≥ 0.50% for ≥ 2 consecutive quarter-end observations
  - Aggregate equal-vol-weighted 60-trading-day rolling Sharpe across {AUDJPY, CADJPY, EURJPY, GBPJPY, NZDJPY, USDJPY} drops below 0.20 net of costs

**Bet #2 (4H TAS-ceiling, USDJPY+EURUSD+GBPUSD) — binding from dispatch:**

- BET2-T1: equal-weighted portfolio Sharpe < 0.30 net of costs on pre-registered OOS holdout → retire family
- BET2-T2: ≥2 of 3 per-pair Sharpes negative on OOS → retire (no cherry-pick of 1-of-3)
- BET2-T3: doubling measured 4H costs reduces in-sample Sharpe < 0.20 → retire
- BET2-T4: engine output diverges from canonical script Sharpe-Δ > 0.10 OR correlation < 0.95 → HARD RETIRE (PROCESS-G1)
- BET2-T5: per-pair Sharpe distribution does not differ from zero (one-sample t p > 0.10) → retire
- BET2-T6: average trade-holding-period < 6 4H bars (≤1 trading day) → retire (TAS-ceiling predicts multi-day hold)

**Vol_target_carry retire-pending-reconciliation lifting** is recommended subject to CEO+HoQR ratification; CONSENSUS does not pre-register a new falsification (existing VTC-T1..T8 in pre-reg remain binding).

---

## Dissent (preserved verbatim)

### Null-Hypothesis Tester

```
NHT DISSENT — recorded 2026-04-26, append-only per /fintech-org charter.

I dissent from any production-ready determination for week 17
(2026-04-27 → 2026-05-01) that rests on the two named gate-passers
(vol_target_carry, carry_fred Bet #1).

Statistical grounds:
1. Deflated Sharpe Ratio at family-wise N=14 with empirically-measured
   trial-Sharpe stdev 0.379 yields DSR = 0.569 (vol_target_carry) and
   0.596 (carry_fred). Both are far below the conventional 0.95
   significance bar. The reported Sharpes are not distinguishable from
   the maximum-order statistic of 14 noise trials.
2. Bonferroni-corrected t-statistic threshold (z >= 2.69 at alpha = 0.05/14)
   is met by neither: vol_target_carry t = 1.31, carry_fred t = 1.38.
3. The pre-committed gate threshold of Sharpe >= 0.30 was not corrected
   for the 14 trials run. Applying it un-deflated is a multiple-testing
   violation.

Structural grounds:
4. vol_target_carry carries an unlifted "retire-pending-reconciliation"
   flag in the atomic claim itself. Deploying flagged strategies is
   inconsistent with the gate they purport to pass.
5. carry_fred's "diversified 12-pair" framing is contradicted by:
   (a) its own "regime-concentrated (BoJ-divergence)" flag,
   (b) top-5 OOS pairs all sharing the JPY leg,
   (c) only 2 of 12 pairs positive on full-period IS.
   The effective number of independent bets is closer to 1 (short-JPY-
   vs-G10) than 12.
6. The OOS window for carry_fred is fully contained in the regime
   whose dependence it must rule out. The claim is logically untestable
   against its own evidence; it requires either a pre-2022 walk-forward
   or a forward-OOS post-BoJ-pivot sub-period before regime-independence
   can be asserted.

I recommend:
- Tests T1 (matched-random), T2 (feature-permutation), T5 (rolling-OOS
  decay), and T6 (BoJ-pivot decomposition) be executed before any
  production dispatch.
- The retire-pending-reconciliation flag on vol_target_carry be either
  formally lifted (with HoQR + CEO signature) or honored.
- The carry_fred result be re-classified as "regime-conditional candidate"
  not "production-ready strategy" until a pre-pivot OR post-pivot
  sub-Sharpe is computed and disclosed.

This dissent is APPEND-ONLY and must be reproduced verbatim in
CONSENSUS.md per the charter. Any consensus that omits or paraphrases
it is procedurally invalid.

— Null-Hypothesis Tester, 2026-04-26
```

### NHT — additional structural objections (from `structural_objections` field, not in the verbatim dissent above but binding on the record)

7. **Trial independence violated by pair overlap.** vol_target_carry (USDJPY) and carry_fred (12 pairs including USDJPY) share the dominant exposure. The two "gate-passing" strategies are not independent trials for Bonferroni accounting purposes; effective N for power is < 14, not = 14. This strengthens NHT's case beyond DSR alone.
8. **Production readiness requires more than a statistical pass.** Execution wiring, kill-switch testing in week-17 conditions, and CRO sign-off are not in evidence in the production-ready claim. (CRO veto + ops PRE-01/02 failure now satisfy this independently.)
9. **Per-pair full-period IS Sharpes positive in only 2 of 12 pairs (carry_fred).** When extended outside the BoJ-divergence window, only CADJPY and NZDJPY are positive IS — corroborating the regime-bet hypothesis.

### CRO (structural risk-architecture concern, not blocking)

CRO is a designated structural skeptic on risk-architecture decisions. Its `kill-switch-architecture-verdict` records 7 gaps in the current single-process kill-switch model that make Path B (multi-strategy parallel) operationally unsafe. The 6 required remediations (R1-R6) are reproduced in `cro-risk-assessment.yaml`; R1, R2, R5, R6 are pre-conditions for Path B dispatch. This dissent does NOT block the current week's plan (which dispatches no parallel strategies) but is preserved as a binding constraint on any future Path B dispatch attempt.

---

## Signatures

- **pm:** @pm-2026-04-26 (synthesizer; this draft)
- **cro:** @a71adc71f774b4e49 (VETO with conditional-lift conditions; pre-open attestation; kill-switch architecture verdict)
- **null-hypothesis-tester:** @acbf06bf141c74ab4 (production-ready=FALSE; dissent verbatim above)
- **head-of-quant-research:** @a4672a603f6234081 (conditional-pass Bet #1 with CF-T9; dispatch Bet #2; defer Path B)
- **cto:** @a88f8030c74df8f5d (PRE-05 approve-with-conditions; WA-03 6 weak spots)
- **ops-engineer:** @ada12f0e8e5d0e672 (PRE-01 + PRE-02 halted; PRE-03 PASS)
- **ceo:** APPROVED 2026-04-26T22:45:00Z (explicit "approve" via /fintech-org orchestrator; ratification artifact at `.fintech-org/.agent-accountability/ratifications/sunday-pre-open-prep-2026-04-26.yaml`)
