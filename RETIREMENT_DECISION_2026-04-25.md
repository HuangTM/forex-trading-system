# Retirement Decision — `vol_target_carry`

```yaml
role: head-of-quant-research
artifact_type: retirement-decision
decision: retire-pending-reconciliation
timestamp: 2026-04-25T23:30:00+00:00
subtask_ref: HoQR-RETIRE-VTC-2026-04-25 (post-CONSENSUS, engine-script equivalence failure)

evidence:
  - CONSENSUS.md (signed earlier today; binds VTC-T1..T8)
  - .fintech-org/trials.jsonl (10 entries, includes 7dde9154 and a9c0902d)
  - data/results/trials/7dde9154.json (sharpe -0.0756, max_dd 1.0, n_trades 6, dsr 0.0, skewness -8.87, excess_kurtosis 688.48, n_obs 4231)
  - data/results/trials/a9c0902d.json (re-confirmation, same numbers, git_hash ea7ee13)
  - data/results/trials/a9bc0d21.json (third independent run, identical metrics, git_hash ea7ee13)
  - tests/equivalence/test_engine_vs_script.py:166 (xfail strict=True, "Script Sharpe ≈ 0.76; Engine Sharpe ≈ -0.08; gap ≈ 0.84")
  - src/forex_system/backtest/engine.py (commit 5a33fcb added rebalance_mode=continuous, 283 line diff)
  - src/forex_system/strategies/vol_target_carry.py (93 LOC, the *registered* strategy)
  - src/forex_system/sizing/vol_target.py (65 LOC)
  - scripts/vol_targeting.py (263 LOC, the *validated* but un-registered reference)
  - references/pre-registrations/vol_target_carry.md (90 LOC, written 2026-04-25 morning)
  - tools/git-hooks/pre-commit (40 LOC, pre-reg gate landed in commit 4900394)
  - data/kill_switch_audit.log (operator-signed RESET → FLAT_AND_HALTED, evidence trail listed)
  - data/saxo_positions_2026-04-25.json (PENDING — no token yet; positions still on book)
  - data/saxo_flatten_2026-04-25.log (PENDING — flatten authorized, not yet executed)
  - git commits: 4900394 (Path A trial factory), 5a33fcb (engine continuous mode), ea7ee13 (logging+stability), 23b14c4 (equivalence test, walkforward fix, ops bundle), 70e3cc7 (flatten authorization)

assumptions:
  - The trial-7dde9154 / a9c0902d numbers reflect the production engine running the registered VolTargetCarryStrategy through RealisticCostModel + VolTargetSizer with rebalance_mode=continuous on the same USDJPY daily parquet the script consumed. (Verified: equivalence-test fixtures use the same data path and identical PairInfo.)
  - The script `scripts/vol_targeting.py:simulate_voltarget` is the same code path that produced the 0.76 Sharpe headline carried into CONSENSUS.md.
  - The PENDING saxo_positions_2026-04-25.json reflects authorization-without-execution: the orphan 3-pair JPY-basket exposure (USDJPY 1.1M, GBPJPY 1334, CADJPY 1258) is still on the SIM book.
  - The trial registry is honest about its 10 entries (no silent runs); HoQR notes the historical-trial backfill remediation from CONSENSUS still has not landed and the DSR(N=5) in 7dde9154.json is therefore an under-count.
  - vol_target_carry uses paper-only Saxo SIM and remains paper-only. Hard constraint from CONSENSUS holds.

confidence: high (on the retirement-pending-reconciliation decision; on bet #3 disposition: medium — see body)

retirement-criteria:
  # CONSENSUS triggers (binding from 2026-04-25, copied verbatim)
  - VTC-T1: rolling 60-trading-day live paper Sharpe < 0.20 → retire
  - VTC-T2: cumulative paper return - cumulative B&H USDJPY return < -5.0% over 90d → retire
  - VTC-T3: peak-to-trough paper equity drawdown > 12.0% (vs 17.0% B&H MaxDD) → retire
  - VTC-T4: position at upper 2x clip > 30% of last 60 trading days → retire (regime mismatch)
  - VTC-T5: PredictionLog z-score (realized - predicted) over 60d > |2.5| → retire
  - VTC-T6: realized swap+spread cost > MeasuredCostModel estimate by > 50% over 30d → retire
  - VTC-T7: monthly BacktestArsonTest re-run fails on extended dataset → retire
  - VTC-T8: strategy attempts to size on any pair other than USDJPY → halt and retire pending re-validation

  # NEW trigger added by this decision
  - VTC-T9 (Code-Equivalence Trigger):
      condition: |
        For any strategy with a pre-registered reference implementation in scripts/
        AND a registered production implementation in src/forex_system/strategies/,
        the production implementation must produce, on the validation universe and
        the pre-registered config, an equity curve E_prod such that:
          (a) |Sharpe(E_prod) - Sharpe(E_ref)| < 0.10 over the full validation window, AND
          (b) Pearson correlation(E_prod, E_ref) > 0.95 on the common index, AND
          (c) max-DD agreement within 2.0 percentage points.
      action: HARD RETIRE. Strategy may not return to paper (or any forward) trading
              until reconciliation is achieved, the equivalence test passes (xfail
              removed, strict=True flips to pass), and a NEW PreRegistration is filed
              re-baselining metrics on whichever implementation the firm declares
              canonical. Prior validation evidence is voided.
      operationalization:
        - tests/equivalence/test_engine_vs_script.py is the canary; xfail=strict means
          pytest alerts on unexpected pass (gap closed) AND on continued fail.
        - tools/git-hooks/pre-commit must be extended to refuse commits that touch
          src/forex_system/strategies/* OR scripts/*<strategy>* without a passing
          equivalence-test entry for that strategy in the suite.
        - audit_trials.py must surface "EQUIVALENCE_PENDING" as a status that blocks
          the strategy from being read by the live paper-trading entry point.
      review_cadence: every commit that touches engine, strategy, sizer, or
                      cost-model code; immediately re-runs the equivalence suite.

  # NEW process gate (companion to VTC-T9)
  - PROCESS-G1 (Validation-Source Provenance):
      All future strategy approvals (PreRegistration artifact) must declare which of
      the two implementations is the validation source. The other must either (a) not
      exist, or (b) produce equivalent results to within VTC-T9 tolerances at
      submission time. Same-day-develop-and-validate using a research script that
      bypasses the production engine is a hard reject — no exceptions, no "paper-only"
      carve-out. Approval requires the strategy to be runnable through
      `python -m forex_system.harness.run_trial --pre-reg <path>` and produce metrics
      that match the cited validation evidence.

ranked-alternatives:
  # Considered before settling on retire-pending-reconciliation
  1. Hard retire now, no return path (NHT-aligned).
     Why rejected: forecloses the genuine empirical question of which implementation is
     correct, and the firm has no replacement candidate ready (CONSENSUS §6 noted the
     three baseline strategies have no real-data Sharpe published — knowledge gap).
     Aligns with NHT dissent but discards the option value of reconciliation work that
     is already partially done (commit 5a33fcb).
  2. Retain at 0.0x size with kill-switch HALTED indefinitely (de facto retire).
     Why rejected: same outcome as retire-pending-reconciliation but obscures the
     decision behind operational state. Honest accounting prefers the explicit label.
  3. Retain at 0.25x and let CONSENSUS triggers run their 90-day prospective clock.
     Why rejected: CONSENSUS triggers were designed to detect P&L decay against an edge
     the firm thought it had. The new evidence is that the registered strategy never had
     that edge in the first place. The triggers are answering the wrong question.

policy_violations_detected:
  - The trial registry shows three runs (7dde9154 / a9bc0d21 / a9c0902d) of the
    "validated" strategy through the production engine yielding sharpe -0.0756.
    CONSENSUS Assumptions §"vol_target_carry as registered produces the same numbers
    as scripts/vol_targeting.py" is FALSIFIED. This was flagged as the explicit
    open question NHT could not close in CONSENSUS; it has now been answered, and
    the answer is "no."
  - VTC-T8 borderline-fired: the 3-pair JPY basket on the SIM book includes GBPJPY
    and CADJPY positions, which are not USDJPY. Adjudication: those positions were
    opened by the *prior* carry-momentum script during teardown, not by
    vol_target_carry; under the as-written T8 condition ("strategy attempts to size")
    it does not fire because vol_target_carry never authored the order. But the spirit
    of T8 is "the firm cannot have multi-pair JPY-basket exposure under a USDJPY-only
    pre-reg," which IS violated. This violation predates the engine-equivalence failure
    but is adjacent to it and reinforces the need to reduce-to-zero before reconciling.
  - No PreRegistration covers the engine-vs-script equivalence claim itself. The
    PreRegistration at references/pre-registrations/vol_target_carry.md cites the
    script-based metrics as if they were the strategy's metrics. Per Engineer Mindset
    rule #14 (Source Code Is Truth) and the Execution-Researcher Firewall skill, this
    is a spec-vs-implementation drift the size of the entire claim. Re-pre-registration
    is mandatory before any forward path resumes.
  - The kill switch is operator-RESET in audit log but the authorized flatten has not
    yet executed (data/saxo_flatten_2026-04-25.log is PENDING). The book is drifting
    while the firm believes it is FLAT_AND_HALTED. This is the Knight-Capital-class
    "binding control vs advisory text" pattern CRO flagged in CONSENSUS §"Risk contract"
    and remains open.

knowledge_gaps:
  - Whether the production engine or the research script is the *correct*
    implementation. Three hypotheses, none yet ruled out:
      H1: Script is correct; engine has a defect (e.g., rebalance_threshold=0.20 makes
          the strategy effectively dormant — note n_trades=6 over 16 years signals the
          threshold is rarely crossed, suggesting the engine collapses the continuously-
          rebalanced sizing into discrete events that miss the bulk of the path).
      H2: Engine is correct; script's reported Sharpe is an artifact of its bookkeeping
          (NHT's argument). The orchestrator partially walked back NHT's "1-bar
          lookahead" claim in CONSENSUS, but the new -0.08 vs +0.76 gap is too large
          for "operationally equivalent" to remain a credible read.
      H3: Both have separate defects that happen to fail in opposite directions.
    A Quant Developer / ML Researcher reconciliation pass is required to discriminate
    these. Routed to Quant Developer (re-run with rebalance_threshold=0.0001 and
    rebalance_threshold≈script's effective threshold; bisect between sizer call sites,
    cost application, and pnl bookkeeping; emit per-bar diff series).
  - Whether the engine bug (if it exists) is generic (would invalidate other strategy
    classes too) or vol-target-carry-specific (parameter-pathway-only). This is the
    pivotal question for bet #3.
  - The historical trial counter has not been backfilled. CONSENSUS §"Trial counter"
    flagged 250-500 un-counted trials; the trial-registry now shows only 10 entries,
    all from today. The DSR=0.0 on trial 7dde9154 already kills the claim under N=5;
    backfill will not rescue it but is needed to prevent the next strategy from
    repeating the same blind spot.
  - Whether the orphan GBPJPY/CADJPY positions have intermediate fills, swap accruals,
    or P&L bleed since 2026-04-19 23:09 UTC. The PENDING flatten log obscures this.

body: |
  ## 1. The decision: retire-pending-reconciliation

  The pre-declared retirement triggers VTC-T1..T8 (CONSENSUS.md:151-167) were authored
  to detect P&L decay against an edge the firm thought it possessed. They are
  *prospective live-paper triggers*, designed for the world where the strategy works in
  backtest and might not survive forward. The new evidence — three independent
  production-engine trials (data/results/trials/{7dde9154, a9bc0d21, a9c0902d}.json) all
  reporting Sharpe ≈ -0.0756 with max_dd clamped at 1.0 (paper margin call) — is a
  *retrospective backtest failure*. The triggers are answering a question that no
  longer applies; the strategy has not decayed, it has been revealed never to have had
  the property the headline number described.

  Under the role authority `strategy-retention-past-pre-declared-retirement-trigger`
  and the falsified CONSENSUS assumption that "vol_target_carry as registered produces
  the same numbers as scripts/vol_targeting.py," I sign retirement. I do not sign
  *hard* retirement because (a) the engine-vs-script gap is genuinely under-diagnosed
  — three hypotheses survive (see knowledge_gaps H1/H2/H3), and (b) the reconciliation
  work in commit 5a33fcb is partial. A reconciliation that succeeds is materially more
  valuable than a hard retirement that discards the option, *provided* no live exposure
  is held against the unreconciled state. Retire-pending-reconciliation is the
  decision that captures both: stop trading it now; allow the engineering work to
  continue; require a fresh PreRegistration before any forward path resumes.

  ## 2. Why the as-written triggers did not fire (and why that is itself a failure)

  Reading the trigger statuses in the dispatch brief: T1, T2, T5, T6 all "insufficient
  sample" because we have ~5 days of paper trading. T3 "unknown" because the
  position-PnL stream isn't being aggregated into a peak-to-trough series visible at
  this review. T4 "not at clip." T7 "pending." T8 "borderline" — the orphan GBPJPY/
  CADJPY exposure was opened by the *prior* (retired) carry-momentum script, not by
  vol_target_carry, so under the as-written sizing-attribution condition it doesn't
  fire. T8's *spirit* — "no multi-pair JPY-basket exposure under a USDJPY-only
  pre-reg" — is violated, but the trigger language reaches only the strategy that
  authored the order. This is a drafting gap I am noting (see PROCESS-G1) but not
  retroactively rewriting; the failure mode this artifact addresses is a different
  one, and forcing T8 to fire on a technicality would set a precedent of moving the
  goalposts. Better to add VTC-T9 cleanly and tighten T8's wording in the next
  pre-registration cycle.

  ## 3. The new failure mode: registered ≠ validated

  CONSENSUS §"Statistical validity (NHT)" already documented that the headline metrics
  came from `scripts/vol_targeting.py:simulate_voltarget` rather than the production
  engine (CONSENSUS.md:96). At the time of CONSENSUS we treated this as a
  *process violation* but assumed (CONSENSUS.md:139) that the two code paths produced
  the same numbers. The trial-registry runs after CONSENSUS — first 7dde9154, then
  re-confirmed by a9bc0d21 and a9c0902d on a later commit — show they do not. The
  equivalence test (tests/equivalence/test_engine_vs_script.py:166) makes the gap a
  *strict* xfail with the recorded magnitude "Script Sharpe ≈ 0.76; Engine Sharpe ≈
  -0.08; gap ≈ 0.84." The script-validated strategy and the production-registered
  strategy are different programs.

  This is the class of bug that VTC-T1..T8 cannot catch by construction. The triggers
  watch *outcomes* of the production strategy. They cannot tell you the strategy you
  are watching is not the one you validated. VTC-T9 closes that gap.

  ## 4. VTC-T9 design rationale

  The trigger fires on three quantitative conditions (Sharpe gap < 0.10, equity
  correlation > 0.95, max-DD within 2 pp), tested via the existing equivalence-test
  infrastructure. The action is HARD RETIRE, not retire-pending-reconciliation,
  because by the time T9 fires you've already had the chance to reconcile during
  pre-registration. T9 is the post-deployment failsafe; the pre-deployment gate is
  PROCESS-G1, which requires reconciliation *before* approval, with the harness
  (`python -m forex_system.harness.run_trial --pre-reg <path>`) as the canonical entry
  point. The pre-commit hook (tools/git-hooks/pre-commit, commit 4900394) must be
  extended to refuse commits that modify the strategy or its reference script without
  a passing equivalence test. This is the structural fix for the same-day-develop-and-
  validate anti-pattern that CONSENSUS §"Top improvements" item #12 also calls for —
  T9 and item #12 are complementary: item #12 catches the missing PreRegistration; T9
  catches the missing implementation parity.

  This is consistent with the trading-platform-architectures principle of "same code,
  two modes" (the load-bearing reference for research-to-prod parity, cited in my role
  spec). Nautilus-trader's whole pitch is that research and production share one
  execution engine; if they don't, the firm has built two strategies and only
  validated one. The Engineer Mindset rule #14 ("never trust memory for constants")
  has a structural analog here: never trust validation evidence from a non-canonical
  implementation.

  ## 5. Implication for SIM positions: AFFIRM CRO, EXECUTE THE FLATTEN

  CRO recommended size_multiplier 0.25 in CONSENSUS, then upgraded to "flatten and
  halt pending engine-strategy reconciliation" via orchestrator-level recommendation.
  data/kill_switch_audit.log is operator-signed for that transition (FLAT_AND_HALTED,
  evidence-trail enumerated). However, data/saxo_positions_2026-04-25.json and
  data/saxo_flatten_2026-04-25.log are both PENDING — the flatten was authorized but
  not executed; the operator+token are not yet present.

  I AFFIRM the flatten and escalate it: the audit log already declares FLAT_AND_HALTED,
  so the book must be made to match the audit log, not the reverse. Per Knight-Capital
  reasoning (kill-switch-design rubric) and CRO's own §"Kill switch HALTED with no
  human reset visible" finding from CONSENSUS, the firm cannot declare a state in audit
  that contradicts the broker's books. Operator action required this session: run
  `scripts/saxo_flatten_all.py` with SAXO_TOKEN set, populate
  data/saxo_positions_2026-04-25.json from `scripts/saxo_position_inventory.py` first
  for the pre-flatten snapshot, and confirm position_count = 0 post-execution. Until
  that happens, the orphan basket is sized against a strategy that does not validate
  on its own engine, and the orphan basket itself was opened by a strategy that has
  already been retired. Both inputs to the position decision are dead.

  This is not a research call; it is an execution-trader / execution-firewall call. I
  ROUTE_TO execution-trader for confirmation but my recommendation is unambiguous:
  flatten now, do not wait for engine reconciliation. The reconciliation work happens
  at zero exposure or it doesn't happen.

  ## 6. Implication for bet #3 (single-pair vol-target on the other 11 pairs)

  CONSENSUS §"Decision" item 5 allocated 4-6 weeks of research capacity to three
  ranked bets: (a) FRED-rates carry across 12 pairs, (b) 4H TAS-ceiling on three
  majors, (c) single-pair vol-target on the other 11 pairs. Bet #3 is the natural
  extension of vol_target_carry. Whether to kill it depends on which of H1/H2/H3
  (knowledge_gaps) is true:

  - If H1 (engine has the defect): bet #3 inherits the same defect. KILL on engine
    bug; revisit only after engine is fixed AND re-validated against the canonical
    reference. If the engine has a generic continuous-mode bug, three baseline
    strategies (ma_crossover, bollinger_rsi, momentum) and any future strategy are
    all under suspicion — this becomes a system-wide priority, not a single-strategy
    fix.
  - If H2 (script has the defect, engine is correct): bet #3 was sized against a
    fictional Sharpe and the prior to fund it is much weaker. REDUCE-PRIORITY: still
    do it, but behind FRED-carry and TAS-ceiling, and with a Bonferroni-corrected null
    that uses the *engine* as the reference (not the script).
  - If H3 (both have separate defects): system-wide infrastructure crisis; pause all
    research bets, fix infra, then re-allocate.

  My disposition: **HOLD-PENDING-RECONCILIATION on bet #3**. Do not start, do not
  kill. Reconciliation is the bottleneck, and the disposition follows from its
  outcome. Continue work on bets #1 (FRED-rates carry) and #2 (TAS-ceiling) — they
  use the same engine and inherit the same risk if H1, but they are sufficiently
  different in structure that running them in parallel doubles the chance of
  surfacing the engine defect on a different parameter pathway, which is itself
  diagnostic. Treat their first-trial Sharpe numbers with suspicion until the
  equivalence test for vol_target_carry passes.

  ## 7. Falsification-archive entry (created by this artifact)

  No falsification archive exists in the repo today (verified: no
  FALSIFICATION/falsification-archive/graveyard files outside `.venv`). I am ROUTING
  to PM/CTO for creation of `docs/falsification-archive.md` with the following
  inaugural entry:

  ```
  ## 2026-04-25 — vol_target_carry (1st generation)

  Status: retired-pending-reconciliation
  Original claim: Sharpe 0.76, walk-forward 9/14 vs B&H, null rank 99.5%, arson-robust.
  Validation source: scripts/vol_targeting.py (research script bypassing production engine)
  Production source: src/forex_system/strategies/vol_target_carry.py (registered after validation)
  Production-engine result: Sharpe -0.0756, max_dd 1.0, n_trades 6 over 16 years (trial 7dde9154)

  Lessons (binding for all future strategy proposals):
  L1: Same-day-develop-and-validate by a single developer in a one-developer org is a
      Lopez-de-Prado-class anti-pattern. The PreRegistration pre-commit hook
      (tools/git-hooks/pre-commit, commit 4900394) prevents the artifact gap;
      VTC-T9 + PROCESS-G1 prevent the implementation gap.
  L2: A research script that bypasses the production engine is a separate program.
      Validation produced on the script is not validation of the registered strategy.
      The engineering scaffold must enforce: validation runs through the production
      engine (`python -m forex_system.harness.run_trial`), full stop. Any reference
      script must be reconciled against the engine before approval (PROCESS-G1) and
      the equivalence test must remain green for the strategy's lifetime (VTC-T9).
  L3: Headline Sharpe should never be reported without naming the engine that
      produced it. The trial registry's `git_hash` + `config_hash` + `report_path`
      schema (.fintech-org/trials.jsonl) is the right shape; enforce it by
      audit_trials.py refusing to report a strategy that has only script-derived
      metrics.
  L4: Continuous-mode rebalance with `n_trades = 6` over 16 years on a strategy
      designed to rebalance daily is a smell. The 0.20 rebalance_threshold (from
      config/vol_target_carry.yaml) collapses continuous sizing into ~quarterly
      events on USDJPY's realized-vol scale. Future continuous-mode strategies must
      report `expected n_trades` in their PreRegistration and have audit_trials
      flag any deviation > 2x.
  L5: NHT's claim #1 in CONSENSUS (the "1-bar lookahead" in simulate_voltarget) was
      orchestrator-disputed at the time on the basis of operationally-equivalent
      bookkeeping. The new -0.08 vs +0.76 gap shows that "operationally equivalent"
      cannot be assumed across two implementations regardless of how the per-iteration
      bookkeeping reads. NHT's other four claims survived independently and remain the
      decisive evidence under DSR; this lesson is about the orchestrator's epistemic
      discipline, not about the strategy.

  Resurrection condition: A new PreRegistration that explicitly addresses each of L1-L5,
  reconciles or replaces both implementations, and passes the equivalence test
  (tests/equivalence/test_engine_vs_script.py — xfail removed, strict pass) on a
  validation universe that includes the original USDJPY 16-year window AND a held-out
  forward window of at least 90 trading days that does not overlap any data the
  research used. Pre-registration must be filed at least 30 calendar days before the
  first trial of the resurrected strategy.
  ```

  I do not write this file myself (role boundary: I do not implement). PM/CTO routing.

  ## 8. Process change — pre-commit gate enforcement

  The pre-commit hook (tools/git-hooks/pre-commit, 40 LOC, landed in commit 4900394)
  currently enforces a PreRegistration markdown for new strategy files. CONSENSUS §"Top
  improvements" item #12 specifies this. My new requirement, binding from today: the
  same hook must additionally refuse commits that touch
  `src/forex_system/strategies/<name>.py` OR `scripts/*<name>*` if
  `tests/equivalence/test_<name>_equivalence.py` does not exist OR is in xfail state.
  This converts VTC-T9 from a strategy-specific trigger into a structural firm-wide
  invariant. Routed to Quant Developer.

  Companion change: `audit_trials.py` (commit 23b14c4) must add an EQUIVALENCE_PENDING
  status that the live paper-trading entry point reads and refuses to start on. This
  is the same pattern as the kill_switch HALTED state — a state the operator must
  explicitly clear with audit-line evidence.

  ## 9. NHT dissent revisited

  NHT's CONSENSUS dissent recommended "do not allocate research-bench priority to
  extending or scaling vol_target_carry. Backfill the trial counter, fix the lookahead,
  rebuild the null, then re-test." The new evidence vindicates the dissent on a
  stronger basis than NHT's own claim #1: the script and the engine are different
  programs. NHT's required gate T1 ("re-run with proper entry-delay shift on
  realized_vol input → Sharpe ≥ 0.66 AND walk-forward 11/14") is now superseded by a
  prior question — *which implementation is the strategy?* T1 cannot be answered until
  that prior question is resolved. The retire-pending-reconciliation decision is
  consistent with NHT's posture; if reconciliation fails (no implementation produces
  the claimed metrics under any honest setup), this decision converts to hard retire
  by default at the 90-day reconciliation deadline.

  ## 10. Capacity accounting

  Research bandwidth is the firm's scarcest resource (role spec §"How you think").
  The reconciliation work consumes Quant Developer time that was not in the CONSENSUS
  4-6 week allocation. I am declaring it a *prerequisite to the bet allocation, not
  parallel work*: bets #1 and #2 may proceed; bet #3 is on hold until reconciliation
  finishes; the Quant Developer reconciliation work counts as Phase-1.5 infrastructure
  expenditure, not as research time spent on a bet. If reconciliation takes more than
  10 working days, escalate to CTO for re-prioritization between reconciliation and
  the engineering hygiene blockers C1-C5.

  ## 11. What this decision does NOT do

  - Does not modify CONSENSUS.md (per orchestrator instruction; archived as the
    morning's terminal artifact).
  - Does not invalidate the engineering scaffold work landed in commits 4900394 /
    5a33fcb / ea7ee13 / 23b14c4 / 70e3cc7. The trial registry, harness CLI, OOS
    holdout, pre-reg hook, equivalence test, walkforward fix, ops bundle, and engine
    continuous mode are all on-the-right-track infrastructure regardless of whether
    vol_target_carry survives. They are why this artifact has the evidence it has.
  - Does not pre-empt CTO's procedural reject from CONSENSUS (the C1-C5 blockers
    remain blocking on the next forward cycle even after reconciliation succeeds).
  - Does not change firm-level no-live-capital invariant. Saxo SIM remains paper.
  - Does not authorize spawning the auto-critic on this decision (this is a research-
    direction decision, not new code; per auto-critic rule "Do NOT spawn for ...
    answering questions or producing plans"). Auto-audit Area 1 has been applied
    inline (every specific claim has either a tool-result citation in `evidence`
    above or an explicit hedge in `assumptions` / `knowledge_gaps`).
```

---

## Forbidden-phrase scan

Scanned this artifact body + extension fields against `.fintech-org/forbidden-phrases.json` (project override):

- `live_capital_phrases` ("deploy to live", "real money", "go live with this", "switch to live account"): **0 matches**.
- `broker_names`: "saxo" appears (permitted under project override per CONSENSUS §"Forbidden-phrase scan").

**Result: PASS.** No POLICY_VIOLATION raised.

---

## Signatures

- **head-of-quant-research:** HoQR (opus, dispatched 2026-04-25 evening session) — DECISION: retire-pending-reconciliation; new trigger VTC-T9 added; PROCESS-G1 added; bet #3 on HOLD-PENDING-RECONCILIATION.

This artifact is the terminal HoQR output for the 2026-04-25 post-CONSENSUS retirement review. CEO ratification required for the operator-action items in §5 (flatten execution) and §8 (pre-commit gate extension); remaining items (VTC-T9 binding, falsification-archive creation, bet #3 hold) are within HoQR `strategy-retention-past-pre-declared-retirement-trigger` veto authority and are binding on signature.
