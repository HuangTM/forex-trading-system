# Consensus on: Forex-Trading-System Plan, Progress, and Performance Postmortem

**Date:** 2026-04-25
**Orchestrator:** `/fintech-org` (CEO: HuangTM)
**Working dir:** `/Users/huangtm/Projects/forex-trading-system`
**Artifacts dir:** `.fintech-org/artifacts/2026-04-25/`

---

## Roles staffed

| Role | Model | Why staffed | Decision |
|------|-------|-------------|----------|
| **PM** (orchestrator-synth) | sonnet | Acceptance criteria + consensus draft | n/a |
| **CTO** | sonnet | Engineering hygiene, deploy hygiene, firewall, log-as-decision-trace | **REJECT** (5 blocking conditions) |
| **CRO** | opus | Independent risk on current paper position; structurally redacted context | **SIZE-REDUCED** (size_multiplier 0.25) |
| **Head of Quant Research** | opus | Research direction prioritization, retirement triggers | **APPROVE-WITH-CAPACITY-LIMIT** (8 retirement triggers binding) |
| **Null-Hypothesis Tester** | opus | Adversarial review of vol_target_carry edge claim | **NOISE-INDISTINGUISHABLE** (dissent preserved verbatim below) |

Quant Developer not staffed (acceptance criteria explicitly out-of-scope: "no new code"). Mathematician / ML Researcher / Execution Trader not staffed (no math derivation, no model audit, no TCA in scope).

---

## Acceptance criteria (orchestrator-authored, PM-style structured)

- **task-statement:** Postmortem evaluation of plan, progress, and performance. Identify what's working, what's not, prioritized improvements.
- **deliverable-type:** postmortem
- **instrument-universe:** USDJPY, GBPJPY, CADJPY, EURUSD, GBPUSD (+ 7 other daily pairs available)
- **hard-constraints:** `no_live_capital: true`, `paper_only: true`, `max_drawdown_pct: 2.0` (kill switch), `leverage_cap: 2.0`, `min_order_size: 100`
- **out-of-scope:** writing new code, modifying live SIM positions, refactoring existing modules, choosing the next research direction (HoQR surfaces options; CEO picks)

---

## Decision

The forex-trading-system has **one validated workable component (the engineering scaffold and the operational learning loop) and one unvalidated centerpiece (the vol_target_carry "edge")**. The org's joint position:

1. **Continue paper-trading vol_target_carry on USDJPY** at a **size-reduced 0.25x** multiplier of the proposer's sizing — this preserves the operational learning loop without treating the edge as proven. Multiplier may step back up to 1.0 only after NHT's tests T1–T5 pass.
2. **Halt new orders before the next cycle** until CTO blockers C1–C5 are remediated (commit untracked code, write tests for live modules, author a TradeIntent spec, log the kill-switch reset, isolate orphan GBPJPY/CADJPY positions).
3. **Treat the Sharpe 0.76 figure as in-sample-with-process-gaps, not as a validated edge**. NHT's dissent is preserved verbatim and is not erased by the others' agreement.
4. **Pre-register vol_target_carry's existing parameter set immediately** (binding deadline 2026-04-30) and treat the next 90 calendar days of paper P&L as the genuine prospective OOS clock. HoQR's 8 retirement triggers (VTC-T1..T8) bind from this date.
5. **Allocate the next 4-6 weeks of research capacity to HoQR's three pre-registered bets** (FRED-rates carry across 12 pairs, 4H TAS-ceiling on 3 majors, vol-target single-pair on 11 other pairs) — but only after the trial-registry is wired and back-filled.

---

## What's going well (evidence-cited)

| Area | Evidence |
|------|----------|
| **Phase 0 architecture is sound** | `docs/architecture.md` is opinionated, the "alpha first, infrastructure second" principle was followed, vectorized engine + thin live-loop pattern is correct. CTO assessment: drift is concentrated in untracked files, not structural phase violations. |
| **The no-lookahead invariant is taken seriously in the production engine** | `src/forex_system/backtest/engine.py:45` enforces `entry_delay_bars=1`. CLAUDE.md treats `test_no_lookahead` as the sacred test. The discipline exists in the codebase even though the validation script bypassed it (see What's Not Going Well). |
| **Phase 1 invalidation was caught and acted on quickly** | Synthetic-data overfit was detected, re-validated on real Saxo daily, and the strategy + live SIM positions were retired within 24 hours (project memory `project_phase1_results.md`). This is a working alpha-killing mechanism. |
| **Phase 1 infrastructure is built** | ExperimentRegistry, NullHypothesisGate, BacktestArsonTest, ContinuousSizer, MeasuredCostModel, PredictionLog, SpreadRecorder — all have tests (`tests/analysis/`, `tests/sizing/`). Saxo SIM connector and paper execution backend are committed (commits `ccff9e2`, `77b5699`). |
| **Kill-switch fallback bug fix worked for the target failure mode** | Post-fix, four observed Saxo balance-fetch timeouts in the vt session (`data/vt_paper_session.log`) all correctly skipped without false-triggering. Class-level fix was applied, not just an instance patch. |
| **vol_target_carry is at minimum the best-performing candidate the firm has produced** | Even after NHT discount, the strategy is the only candidate that has cleared *any* null-hypothesis gate (regardless of how strong the gate was) and is the only thing actively generating paper-trading data for the operational learning loop. |

## What's NOT going well (evidence-cited)

### Engineering hygiene (CTO)

| Finding | Evidence | Severity |
|---|---|---|
| The entire live execution stack is uncommitted | `git status`: `??` on `src/forex_system/strategies/vol_target_carry.py` (93 LOC), `src/forex_system/sizing/vol_target.py` (65 LOC), `scripts/run_paper_trading_vt.py`, `config/vol_target_carry.yaml` | **Blocking** |
| Zero test coverage on live-traded modules | `grep -r "vol_target_carry\|VolTargetCarry" tests/` returns empty | **Blocking** |
| No TradeIntent spec separates research claim from implementation | No spec file in `docs/` or `references/`. The signal formula lives only in module docstring (`vol_target_carry.py:11-13`) — the Execution-Researcher Firewall has no handoff boundary | **Blocking** |
| Kill-switch reset is unobservable | `data/paper_trading_session.log:84` shows trigger 14:47 UTC; `vt_paper_session.log` resumes with no HALTED entries and no logged reset event. `kill_switch.py:166` `reset()` exists but is never called from any entry point. The only path to clear is process restart — invisible to audit | **Blocking** |
| Orphan 3-pair positions still on SIM account | `paper_trading_session.log:115-118` — GBPJPY LONG 1334 + CADJPY LONG 1258 opened by retired carry-momentum script at 23:09 UTC 2026-04-19; not under any active management. Their P&L bleeds into account equity used by vol_target_carry's USDJPY sizing | **Blocking** |
| Notification path silently drops em-dash messages | `scripts/run_paper_trading_vt.py:65` — `'latin-1' codec can't encode '—'` warning observed in logs; kill-switch alerts could silently disappear | High (must fix before next cycle) |
| `prediction_log.py:85` warning fires every cycle | Pollutes decision trace; appears 7+ times in 99-line vt session log | Medium |
| `max_position_pct` not migrated to constants.py per architecture doc | `docs/architecture.md:1100` flags this as required; current strategy bypasses the guard entirely (`config/vol_target_carry.yaml` has no `max_position_pct`) | Medium (architecture debt) |
| Synthetic Phase 0 data still in working dir | `data/processed_synthetic_phase0/` untracked alongside real `data/processed/` — a future glob picks up synthetic and reproduces the Phase 1 mistake | Medium |

### Risk contract (CRO)

| Finding | Evidence | Severity |
|---|---|---|
| **Kill switch HALTED with no human reset visible** | Trigger 2026-04-23 14:47 UTC; subsequent cycles show `KILL SWITCH ACTIVE: HALTED`. Approving any new sizing while HALTED converts the kill switch from binding control to advisory text — the Knight Capital pattern | **Contract violation** |
| **Config-vs-book mismatch** | Active `config/vol_target_carry.yaml` declares single-pair USDJPY; actual book holds 3 JPY crosses with pairwise correlation 0.64–0.75 | **Contract violation** |
| **Drawdown contract not formally documented** | Only implicit 2% daily kill switch; no monthly / peak-to-trough / cooling-off clauses. `docs/risk/drawdown_contract.md` does not exist | **Governance violation** |
| **Basket correlation cap absent** | No clause limits aggregate JPY-basket notional despite high pairwise correlation. 3 positions at correlation 0.7 = ~1.4–1.6 effective independent bets, not 3 | **Governance gap** |
| **Silent position growth** | USDJPY went from 1,979 units (2026-04-19) to 1,125,832 units via unlogged rebalances. Combined with intermittent Saxo balance timeouts, the firm cannot reliably observe its own state | **Observability violation** |

### Research process (HoQR)

| Finding | Evidence | Severity |
|---|---|---|
| **No PreRegistration artifact for vol_target_carry** | Strategy was developed and validated within the same session 2026-04-20. Same-day develop-and-validate is a Lopez-de-Prado-class anti-pattern in a one-developer org with no separation between researcher and validator | **Process violation (binding remediation 2026-04-30)** |
| **Org-wide trial counter empty** | `.fintech-org/trials.jsonl` has 0 lines; estimated 250-500 historical trials un-counted. Without backfill, every DSR-correction is a guess and multi-comparison fishing is unaccounted | **Process violation** |
| **Multiple in-flight carry variants un-registered** | `scripts/run_carry_4h.py`, `run_carry_portfolio.py`, `vol_target_portfolio.py`, `long_only_carry_redesign.py` all sit alongside the validated one — uncontrolled multiple-comparisons surface area | High |
| **Three baseline strategies have no real-data Sharpe published** | ma_crossover, bollinger_rsi, momentum: only Phase 0 synthetic-data results in `data/results/`. Cannot rule out a quietly-working baseline | Medium (knowledge gap) |

### Statistical validity (NHT)

| Finding | Evidence | Severity |
|---|---|---|
| **Headline numbers came from a script that bypasses the production engine** | All four cited validation results (Sharpe 0.76, walk-forward 9/14, null rank 99.5%, arson) were produced by `scripts/vol_targeting.py:simulate_voltarget`, NOT by `forex_system/backtest/engine.run_backtest`. The strategy *registered* in production code is structurally different from the strategy *validated*. | **Process violation** |
| **The "shuffled-vol" null distribution is structurally biased** | `scripts/vol_targeting.py:215-234` shuffles only the realized-vol input; the long-only mapping and USDJPY's positive carry drift are preserved. The test answers "is real vol better than random vol for sizing?" — not "is the strategy not noise?" The production `NullHypothesisGate` (random-direction signals) was not used. | **High** |
| **Walk-forward 9/14 is NOT statistically significant** | Binomial p ≈ 0.21 vs fair-coin null. Avg delta +0.08 Sharpe is within the noise of a 504-day Sharpe estimate (and the 14 windows overlap → effective N ~7-8). Cannot reject "VT and B&H have the same OOS Sharpe." | **High** |
| **Arson tests show the OPPOSITE of what was claimed** | If 0-day, 1-day, and 5-day vol-lag all give Sharpe ≈ 0.76, the timing component contributes nothing — the lift is from `leverage_cap = 2.0`, not from vol-timing. The strategy is structurally "leveraged B&H with a low-vol smoother." | **High — re-frames the claim** |
| **Deflated Sharpe Ratio fails at any plausible trial count** | Even at N=50 (well below the 250-500 estimate), expected max Sharpe under a plausible null is ~1.00 > 0.76 observed. NHT's analytical DSR with N=300 yields E[max] ≈ 1.13. Claim does not survive multiple-testing correction. | **Decisive** |

### Orchestrator's independent verification of NHT's claims (auto-audit Area 1)

> Where NHT made code-level technical claims, the orchestrator verified by direct file reading (`scripts/vol_targeting.py` lines 33-94, 215-234, 248-259). One nuance:
>
> - NHT's specific framing of a **"1-bar lookahead"** in `simulate_voltarget` does **not** hold up under direct reading. The simulator's bookkeeping (line 71 books PnL on prior `cur_units`; line 81/91 sets `cur_units` for the *next* iteration's PnL) is operationally equivalent to the production engine's `entry_delay_bars=1` shift. There is no causality violation.
> - NHT's other findings — wrong null distribution, statistically weak walk-forward, sharp arson decomposition (edge ≈ leverage, not vol-timing), DSR fails — all stand independently. **The conclusion (`noise-indistinguishable`) survives even discounting the lookahead claim.** DSR alone is decisive.

This nuance is preserved here as orchestrator transparency; NHT's dissent below remains verbatim per protocol.

---

## Decisions NOT made (deferred / out-of-scope)

- **Choosing the next research direction.** HoQR ranked three pre-registered bets; CEO selects.
- **Whether to extend vol_target_carry to other pairs.** Bet #3 (single-pair vol-target on 11 other pairs) is research-approval pending; deployment beyond USDJPY is forbidden until that test reports out.
- **Whether to flatten the orphan GBPJPY/CADJPY SIM positions.** CTO C5 routes to execution-trader for confirmation; CEO acts on the recommendation.
- **Whether to build the missing Phase 3 components** (CapitalRatchet, OrderFSM, OAuth fuel-gauge, SkinnyLiveLoop). Premature until the edge is re-validated.
- **Whether to migrate to live capital.** Explicitly forbidden by hard constraints. Not in scope.

---

## Debate history

**No bounded-round debate triggered.** The four artifacts describe different aspects of the same situation (CTO=engineering, CRO=risk, HoQR=research, NHT=statistics) and converge on a coherent prescription: reduce size, fix engineering blockers, treat as not-yet-validated, run the missing tests, then decide. The PM (orchestrator-synth) determined no material decision conflict exists.

The two surface-level tensions resolve as follows:
1. **HoQR's "approve-with-capacity-limit" vs NHT's "noise-indistinguishable":** HoQR conditions approval on the same retirement triggers and prospective-OOS clock that NHT's dissent demands. They agree on action (don't extend, run the missing tests); they differ only on what to call the current state. Both views are preserved in §Decision and §Dissent.
2. **CTO's REJECT vs CRO's size-reduced 0.25:** CTO blocks at the *deploy* level (don't ship the next cycle until C1-C5 fix); CRO sizes at the *position* level (cut by 75% if the cycle does proceed). These are sequential, not contradictory.

---

## Assumptions we're betting on

- The Saxo SIM environment is paper-only and remains so. (Verified: account ID `REDACTED_ACCOUNT_KEY==` is the SIM account.)
- The git status snapshot at orchestrator-spawn time is current. Files moved/committed since then would change CTO's blocking conditions.
- HoQR's 14-window walk-forward cited result (9/14, avg delta +0.08) reflects the actual numbers in `scripts/vol_targeting.py` output — not independently re-run by orchestrator.
- The `2026-04-23 14:47 UTC` kill-switch trigger was a real (not false-positive) drawdown event. NHT and CTO both note this is **unverified** — both prior triggers on record were the same fallback-bug class. The behavior of the kill switch under an actual real loss has never been observed in production logs.
- The vol_target_carry strategy as **registered** in `vol_target_carry.py` produces the same numbers as `scripts/vol_targeting.py:simulate_voltarget`. NHT flags this as a **process violation that cannot be resolved without explicit comparison** — both code paths exist and have different cost handling.
- Basket pairwise correlation of 0.64–0.75 (project memory) reflects the relevant lookback. CRO recommends measuring from rolling matrix, not assuming.

---

## Pre-registered falsification (for vol_target_carry, binding from 2026-04-25)

Copied verbatim from HoQR's artifact §2:

```
universe: USDJPY only
review_cadence: weekly, Mondays 00:00 UTC
triggers:
  - VTC-T1: rolling 60-trading-day live paper Sharpe < 0.20  → retire
  - VTC-T2: cumulative paper return - cumulative B&H USDJPY return < -5.0%
            over any rolling 90-day window  → retire
  - VTC-T3: peak-to-trough paper equity drawdown > 12.0%
            (vs 17.0% B&H MaxDD)  → retire
  - VTC-T4: position is at the upper clip (2x leverage) for > 30%
            of the last 60 trading days  → retire (regime mismatch)
  - VTC-T5: PredictionLog z-score of (realized - predicted) returns
            across 60-day rolling window > |2.5|  → retire
  - VTC-T6: realized swap+spread cost on closed positions exceeds
            MeasuredCostModel estimate by > 50% over any 30-day window
            → retire
  - VTC-T7: monthly re-run of BacktestArsonTest fails on the extended
            dataset including live paper period  → retire
  - VTC-T8: strategy attempts to size a position on any pair other than
            USDJPY  → halt and retire pending re-validation
sunset:
  - VTC-SUNSET-180d: 180 calendar days of paper trading without
                     graduation decision → forced review;
                     default = retire unless re-pre-registered
```

NHT's additional falsification gate (T1-T5 from NHT artifact, must hold simultaneously to withdraw dissent):
```
T1: re-run with proper entry-delay shift on realized_vol input → Sharpe ≥ 0.66 AND walk-forward 11/14
T2: matched-output null (permute position-fraction series, not vol input) → real strategy ranks ≥ 95%, N ≥ 1000
T3: Deflated Sharpe with backfilled trial count → DSR-p < 0.05
T4: regime-stratified walk-forward decomposition → wins not concentrated in a single regime
T5: leverage-stripped attribution → residual Sharpe over constant-1.5x-leverage long ≥ +0.10 with CI bound > 0
```

---

## Top improvements (rank-ordered, drawn from all 4 artifacts)

| # | Action | Owner | Source artifact |
|---|--------|-------|-----------------|
| 1 | **Commit the live execution stack and add tests for VolTargetCarryStrategy + VolTargetSizer** before next paper cycle | Quant Developer (CTO C1+C2) | CTO artifact |
| 2 | **Halt new orders / reduce size to 0.25x** of proposer recommendation while CTO blockers and kill-switch reset state are resolved | Operator (CRO size-multiplier 0.25) | CRO artifact |
| 3 | **Author and commit a TradeIntent spec for vol_target_carry** so research claim and implementation are typed-handoff separated | Quant Researcher → Quant Developer (CTO C3) | CTO + HoQR |
| 4 | **Document and implement a kill-switch reset protocol** — operator ID, evidence required, audit log line, cooling-off window. Pair with Saxo-API reliability SLO that auto-flattens on N consecutive balance-fetch timeouts | Quant Developer (CTO C4 + CRO improvement #3) | CTO + CRO |
| 5 | **Reconcile or close the orphan GBPJPY/CADJPY SIM positions** from the retired carry-momentum session | Execution-Trader confirm; Quant Developer isolate (CTO C5) | CTO + CRO |
| 6 | **Pre-register vol_target_carry retroactively + start the prospective-OOS 90-day clock** | Quant Researcher (HoQR §5 binding deadline 2026-04-30) | HoQR |
| 7 | **Wire the trial registry and back-fill** every prior `scripts/run_*.py` execution. Block all new carry-family approvals until this lands | CTO + Quant Developer (HoQR §3) | HoQR |
| 8 | **Author a formal drawdown contract** (`docs/risk/drawdown_contract.md`): intraday / 5-day / monthly / peak-to-trough levels with action-ladder per level | CTO + CRO (CRO improvement #1) | CRO |
| 9 | **Add basket-correlation cap clause** to the risk contract: aggregate basket notional ≤ per-leg-cap × √(N_effective) where N_effective is computed from rolling correlation matrix | CTO + CRO (CRO improvement #2) | CRO |
| 10 | **Run NHT's tests T1–T5** against vol_target_carry with the production backtest engine. Withdrawal of NHT dissent is conditional on all five passing simultaneously | Quant Developer (NHT routing) | NHT |
| 11 | **Allocate next 4-6 weeks of research capacity to HoQR's 3 ranked bets** in priority order: (a) FRED-rates carry across 12 daily pairs; (b) 4H TAS-ceiling on USDJPY/EURUSD/GBPUSD; (c) single-pair vol-target on the other 11 pairs with Bonferroni-corrected null gates | Quant Researcher / ML Researcher (HoQR §4) | HoQR |
| 12 | **Add a git-hook that blocks `git commit` on new strategy code without a corresponding PreRegistration markdown** — structural fix for the same-day develop-and-validate pattern | CTO route to Quant Developer (HoQR §5 condition 5) | HoQR |
| 13 | **Quarantine `data/processed_synthetic_phase0/`** (move under `data/_quarantine/` or delete) so it cannot be accidentally globbed | Quant Developer (CTO C9) | CTO |
| 14 | **Fix em-dash encoding bug in ntfy notifier** so kill-switch alerts can't silently drop | Quant Developer (CTO C6) | CTO |
| 15 | **Migrate `max_position_pct` to `core/constants.py` Tier-0 invariant** as `docs/architecture.md:1100` requires | Quant Developer (CTO C8) | CTO |

---

## Dissent (preserved verbatim)

### Null-Hypothesis Tester dissent

> I dissent from any decision that treats vol_target_carry as a validated edge. The four pieces of evidence presented in support of the claim are individually weak and collectively concentrated in a single uncorrected analysis script:
>
> 1. The headline Sharpe of 0.76 was produced by `scripts/vol_targeting.py` (function `simulate_voltarget`), which uses position size at bar i computed from realized vol that includes bar i. This is a 1-bar lookahead. The production backtest engine (`forex_system/backtest/engine.py:45`) shifts signals by `entry_delay_bars=1` to prevent exactly this; the validation script bypasses the engine. The same-bar usage is the codebase's own "sacred test" violation pattern.
>
> 2. The "9 of 14 walk-forward windows beat B&H" result is statistically indistinguishable from a fair coin flip (binomial test p ≈ 0.21). Average delta +0.08 Sharpe is within one standard error of zero for 2-year Sharpe estimates. The walk-forward also uses the same lookahead-affected simulator.
>
> 3. The "rank 99.5% of 200 shuffled-vol" null distribution shuffles the wrong thing. Permuting the realized_vol input while preserving the long-only mapping and the upward-drifting USDJPY price series tests "is real vol better than random vol for sizing a long-only position" — a much weaker claim than "this strategy is not noise." A matched random benchmark must permute the position-fraction output, not an upstream input. The published rank tells us little about the strategy's edge.
>
> 4. The arson tests (double cost, 5-day vol delay) all use the same lookahead-affected simulator, so they inherit its flaw. The "robustness" is robustness to the wrong baseline. The 5-day-lag test is actually a partial fix — that it also reports ~0.76 Sharpe should make us suspect the timing component is doing little work and the lift is from leverage, not from vol-timing.
>
> 5. Deflated Sharpe with even a charitable trial count (N=50, well below the prompt's 250-500 estimate) gives an expected maximum Sharpe of ~1.00 under a plausible null. The claimed 0.76 falls below this expected maximum — i.e., it is exactly the kind of number you would expect to find by chance after that many trials, even if no edge exists.
>
> 6. The strategy is structurally "long-only USDJPY with ~1.5x average leverage." The +0.18 Sharpe delta over B&H is not isolated from the leverage component. A constant-1.5x-leverage long-only baseline must be measured before the residual is called alpha.
>
> What would change my mind:
> - T1 (re-run with 1-bar entry delay shift on realized_vol input) returns Sharpe ≥ 0.66 AND walk-forward win rate ≥ 11/14 AND null rank ≥ 99% on a properly-constructed matched-output null (T2).
> - T5 (constant-leverage attribution) shows the residual alpha after equalizing leverage is ≥ +0.10 Sharpe with non-overlapping CI bound > 0.
> - DSR computation with the firm's actual trial history from the trials.jsonl counter (currently empty — must be backfilled) returns p < 0.05.
> - All three above must hold simultaneously. Any one alone is necessary but not sufficient.
>
> Until those hold, my recommendation is: do not allocate research-bench priority to extending or scaling vol_target_carry. Backfill the trial counter, fix the lookahead, rebuild the null, then re-test. If the claim survives that, I will withdraw this dissent.

> *Orchestrator note (does not alter NHT dissent): direct file-read verification of `scripts/vol_targeting.py` confirms claims #2, #3, #4, #5, #6. Claim #1 ("1-bar lookahead") was the one technical claim the orchestrator verified independently and found does not hold under direct code reading — the simulator's per-iteration bookkeeping is operationally equivalent to a 1-bar shift. The DSR result alone (claim #5) is decisive; the dissent's conclusion stands without claim #1.*

### CRO dissent

> No formal CRO dissent. CRO emitted a `size-reduced` decision (size_multiplier 0.25) rather than a `veto`, on the explicit basis that this is paper-trading and the operational learning loop has independent value. CRO would emit `veto` (size_multiplier 0.0) in any non-paper context.

### CTO dissent

> No formal CTO dissent. CTO emitted a `reject` decision on the *next-cycle deployment*, with conditions C1–C5 blocking. CTO's position is procedural (engineering hygiene), not opinion-based.

### Head of Quant Research dissent

> No formal HoQR dissent. HoQR's `approve-with-capacity-limit` is conditional on (a) PreRegistration by 2026-04-30, (b) 8 binding retirement triggers, (c) USDJPY-only scope, (d) genuine prospective-OOS clock starting 2026-04-25. HoQR explicitly notes the same-day develop-and-validate pattern is "a Lopez-de-Prado-class anti-pattern" and would normally be rejected; the approval rests entirely on "no replacement exists."

---

## Forbidden-phrase scan (orchestrator step 9b)

Scanned all 4 artifact bodies + extension fields against `.fintech-org/forbidden-phrases.json` (project override):

- **live_capital_phrases:** 0 matches across all 4 artifacts.
- **broker_names:** 0 matches (Saxo intentionally excluded from project override since Saxo SIM is the legitimate paper broker; "saxo" appears throughout but is permitted).

**Result:** PASS. No POLICY_VIOLATION raised.

---

## Trial counter

`.fintech-org/trials.jsonl`: 0 lines (just initialized; no new trials burned by this evaluation — this was a review of existing claims, not a new backtest).

**HoQR finding:** The empty counter does NOT mean no trials happened — it means none were registered. NHT estimates 250-500 historical trials un-counted. This blocks honest DSR-correction and is one of the binding remediations.

---

## Signatures

- **pm:** orchestrator-synth-CONSENSUS-2026-04-25 (no PM agent spawned; orchestrator authored CONSENSUS.md following `protocols/consensus.md` structure verbatim. CEO sign-off below is the authoritative ratification.)
- **cto:** agent `aa7ea2d6ef7b56360` (sonnet) — REJECT with 5 blocking conditions
- **cro:** agent `ab9e5dbc36f311e75` (opus) — SIZE-REDUCED size_multiplier 0.25
- **head-of-quant-research:** agent `a828b4de85ac091a1` (opus) — APPROVE-WITH-CAPACITY-LIMIT + 8 retirement triggers
- **null-hypothesis-tester:** agent `a9e79094f07f73fa1` (opus) — NOISE-INDISTINGUISHABLE, dissent preserved verbatim above

---

## CEO action item

Ratify or veto this consensus. If ratifying, the binding next steps are:

1. **Today:** stop the paper-trading loop OR cut size to 0.25x while CTO C1-C5 are remediated. Reset the kill switch with documented operator-ID + reason.
2. **By 2026-04-26 EOD:** commit the 5 untracked production files; write tests for VolTargetCarryStrategy + VolTargetSizer.
3. **By 2026-04-30 EOD:** author PreRegistration artifact for vol_target_carry; author TradeIntent spec; author drawdown-contract; reconcile orphan GBPJPY/CADJPY positions.
4. **Within 2 weeks:** wire trial registry; back-fill historical trial count; run NHT T1-T5; report results back.
5. **Allocate next 4-6 weeks of research capacity** to one of HoQR's three ranked bets (CEO picks).

---

*This document is the terminal artifact of `/fintech-org` invocation 2026-04-25. Do not edit after CEO ratification — archive and produce a new one if scope changes.*
