# Path B — Multi-Strategy Paper-Trading Competition

> **Status:** DESIGN ONLY. Not approved for dispatch. Not implemented.
> **Author role context:** CTO + Head of Quant Research hybrid (orchestrator authoring).
> **Date:** 2026-04-25
> **Audience:** CEO (HuangTM) for dispatch decision; CTO/HoQR for refinement; Quant Developer for eventual implementation.
> **Length cap on dispatch:** if approved, max 4 implementation milestones before forced re-review.

---

## 0. TL;DR

Run 3-10 strategies simultaneously on Saxo SIM, each with its own equity slice, kill switch, audit log, and pre-registration. An auto-promote/demote ladder reallocates capital share by realized OOS performance, not by backtest claims. Goal: increase research throughput from "1 strategy per 4 weeks" to "N strategies in parallel, with the bad ones killed automatically." This is a **research velocity tool**, not a portfolio optimizer.

**Recommendation (see §10):** Dispatch *after* Tracks 5 and 6 land (vol_target_carry equivalence pass + at least one alternate strategy passing the harness gate). Dispatching now would re-run the same anti-pattern that killed vol_target_carry, just in parallel.

---

## 1. Problem statement & non-goals

### 1.1 Problem
Research velocity is the firm's binding constraint. Today's pipeline is serial: one strategy researched, validated, paper-traded, retired (or graduated) over ~4 weeks. The 2026-04-25 retirement of `vol_target_carry` consumed 5 paper-trading days for an answer the production engine could have surfaced in one trial. The firm has at least three pre-registered bets queued (FRED-rates carry × 12 pairs, 4H TAS-ceiling × 3 majors, single-pair vol-target × 11 other pairs) — at the current cadence, that's 12 weeks of sequential paper time before the next decision.

A multi-strategy paper-trading harness collapses 12 weeks of serial work into 4-6 weeks of parallel work, *if* strategy-level attribution and per-strategy retirement triggers actually work as designed.

### 1.2 Non-goals (explicit)
- **NOT a portfolio optimizer.** No mean-variance, no Black-Litterman, no risk-parity allocator. Capital share is set by tier, tier is set by realized OOS Sharpe, that's it.
- **NOT a multi-strategy execution engine for live capital.** Paper-trading evaluation only. Live capital remains forbidden by hard constraint.
- **NOT a hedge-fund-of-strategies.** No correlation-based risk budgeting, no factor decomposition. Each strategy stands or falls on its own attribution slice.
- **NOT a replacement for pre-registration.** Every strategy admitted to Path B must already have a PreRegistration artifact and pass the harness gate. Path B is the prospective-OOS clock, not the validation gate.
- **NOT a tournament that picks one winner.** Multiple strategies may coexist at Tier 2 indefinitely. The mechanism is "kill the bad ones," not "crown the best one."

---

## 2. Hard prerequisites (gating — Path B may not dispatch until ALL hold)

| # | Prerequisite | Verifier | Why it gates |
|---|---|---|---|
| **P1** | `vol_target_carry` equivalence test passes | `tests/equivalence/test_engine_vs_script.py` xfail removed, strict pass | If we dispatch before equivalence is solved, every Path B strategy that uses the engine inherits the same "registered ≠ validated" risk. PROCESS-G1 from RETIREMENT_DECISION_2026-04-25 is binding firm-wide; Path B is the highest-leverage place to enforce it. |
| **P2** | At least 1 alternate strategy clears harness gate | `python -m forex_system.harness.run_trial --pre-reg <path>` produces metrics matching its PreRegistration within VTC-T9 tolerances; entry in `.fintech-org/trials.jsonl`. Candidates: FRED carry, TAS-ceiling, or fresh strategy. | Path B with N=1 is just single-strategy paper trading. The minimum viable competition is N=2 — a candidate against a benchmark (B&H or constant-vol). |
| **P3** | Saxo SIM positions flat | `scripts/saxo_position_inventory.py` reports `position_count = 0`; `data/saxo_flatten_2026-04-25.log` populated with successful execution | Path B starts from a known clean slate. Inheriting the orphan GBPJPY/CADJPY basket means strategy attribution is poisoned from cycle 1. |
| **P4** | Trial registry has ≥ 25 entries | `wc -l .fintech-org/trials.jsonl` ≥ 25, with at least 10 historical-backfill entries flagged `provenance: backfill` | DSR-correction needs a denominator. The current 10-entry registry under-counts; Path B trials add more strategies × more pairs × more parameter sets, multiplying the multiple-comparison burden. The 25 floor includes the CONSENSUS-mandated historical backfill (NHT estimate 250-500 un-counted, but 25 is a reasonable working minimum to avoid blocking). |
| **P5** | Pre-commit hook blocks engine/strategy/sizer commits without passing equivalence test | `tools/git-hooks/pre-commit` extended per RETIREMENT_DECISION §8 | Without this, a researcher can land a Path B strategy whose validation source is a research script — the exact failure VTC-T9 was created to prevent. |
| **P6** | Per-strategy KillSwitch class exists and is unit-tested | `src/forex_system/risk/kill_switch.py` extended to accept a strategy_id; tests in `tests/risk/test_kill_switch_per_strategy.py` cover 3+ trigger scenarios per strategy in isolation | Single-instance KillSwitch is the existing single-strategy pattern. Path B's whole premise is per-strategy isolation; a shared kill switch creates the cascade in §6.4. |

**Veto rule:** If ANY of P1-P6 is missing at dispatch time, this design is rejected. No "we'll fix it in milestone 1" carve-out. The cost of dispatching with one missing prereq is materially larger than the cost of waiting another week.

---

## 3. Architecture

### 3.1 Per-strategy isolation (the core invariant)

Every Path B strategy gets its own:
- **Equity slice** — `equity_slice = total_equity × tier_share[strategy]`. NO commingling. A strategy's drawdown affects only its own slice.
- **KillSwitch instance** — `KillSwitch(initial_equity=equity_slice, audit_log_path=f"data/kill_switch_audit_{strategy_id}.log")`.
- **Audit log** — `data/audit/{strategy_id}_{date}.jsonl`, append-only, structured. Every signal, every order, every reconciliation, every tier transition.
- **Heartbeat file** — `data/heartbeat/{strategy_id}.json`, atomic write-then-rename per Track 3 pattern. Watcher process flags strategies with stale heartbeats > 2× expected cycle interval.
- **PredictionLog partition** — predictions tagged with `strategy_id` so OOS performance is reconstructable.
- **Daily reconciliation** — `Reconciler.reconcile_strategy(strategy_id)` compares per-strategy intended position vs. attributed Saxo SIM position (see §3.3).
- **PreRegistration** — `references/pre-registrations/{strategy_id}.md` with binding retirement triggers.

### 3.2 Capital allocation
- `total_equity` = Saxo SIM account equity (single account; sub-accounts deferred — see §3.3).
- Initial allocation per Tier-0 strategy: `total_equity / N` is **wrong** (gives untrusted strategies too much rope). Use:
  - Tier 0 (probation): 1% of `total_equity` per strategy. Up to 5 simultaneous probationers = 5% total at-risk.
  - Tier 1 (active): 8% per strategy. Up to 5 simultaneous = 40%.
  - Tier 2 (proven): 15% per strategy. Up to 3 simultaneous = 45%.
  - **Reserve:** 10% always uninvested across all tiers to absorb tier-transition slack.
  - **Cap:** total at-risk capital ≤ 90% of `total_equity` at any time.

If the configured strategies would exceed the cap, the **lowest-tier strategy with the lowest 30-day Sharpe is auto-demoted** by one tier until the cap holds. (This is a soft cap; the hard cap is the daily kill-switch threshold per slice.)

### 3.3 Strategy-to-position attribution (the unsolved problem in Saxo SIM)

Saxo SIM holds positions at the **account level** with no strategy tag. Three options were considered:

#### (a) Sub-accounts per strategy
**Status:** Not viable in Saxo SIM. Saxo SIM provides one client account; sub-account creation requires institutional access this firm does not have. Verified by inference from `references/saxo-bank-api-research.md` and `scripts/test_saxo_sim_connectivity.py` — no sub-account API surface is exposed for retail.

#### (b) Intent-tracking + attribution
Track each strategy's *intended* position separately in `data/strategy_state/{strategy_id}.json`. When an order fills, attribute the fill to the strategy whose intent change matched. Net broker position = sum of intended positions across strategies on that pair.

**Pros:** Allows strategies to overlap on the same pair.
**Cons:** Attribution becomes ambiguous on partial fills, on price-improved fills, on rejected-then-retried orders, and especially on net-zero scenarios (Strategy A wants long 1000, Strategy B wants short 1000 → broker shows flat, but each strategy thinks it has its own position). Reconciliation requires solving an NP-easy-but-fragile assignment problem on every cycle.

#### (c) Pair partitioning (one strategy = one pair, no overlap)
Each strategy is assigned a unique pair. Strategy A trades USDJPY only; Strategy B trades EURUSD only; etc. Broker position on a pair = that strategy's position.

**Pros:** Attribution is trivial. Reconciliation is trivial. KillSwitch per strategy is meaningful (slice is the single pair). Strategy retirement just closes that pair.
**Cons:** Limits the strategy universe — you can't run two carry strategies if they both want to trade USDJPY. Also limits N to ~10-12 (the available daily pairs).

#### Decision: **(c) pair partitioning for Path B v1**, with a documented upgrade path to (b) if N > 10 strategies materializes.

**Justification:**
1. The CONSENSUS findings repeatedly hammer "config-vs-book mismatch" and "silent position growth" as the firm's most-real risk-contract violations. Option (b) makes those problems *worse*, not better. Option (c) eliminates them by construction.
2. The Knight Capital pattern that retired vol_target_carry was a state/book divergence. Path B with overlapping positions multiplies the divergence surface area by N. The whole point of Path B is to *increase* research throughput, not to *increase* operational risk.
3. The available daily pair universe (12 in CONSENSUS + 5 majors) is wider than the 3-10 strategy target. Pair partitioning fits.
4. Two strategies that *want* the same pair is a research-direction conflict to be adjudicated by HoQR before dispatch, not by the harness at runtime. (HoQR vetoes the duplicate via `duplicate-hypothesis-already-falsified-in-archive` if applicable, or assigns the loser to a different pair / different timeframe.)

**Enforcement:** the harness loader (`harness.load_competition_config`) MUST refuse to start if any pair is claimed by more than one strategy. Hard error, not warning.

### 3.4 Module layout (additive to existing architecture)

```
src/forex_system/
  competition/                          # NEW Path B namespace
    __init__.py
    config.py                           # CompetitionConfig (multi-strategy YAML loader)
    runner.py                           # MultiStrategyRunner (replaces single-strategy loop)
    attribution.py                      # PositionAttribution (per-strategy slice tracking)
    ladder.py                           # AutoLadder (promote/demote rules engine)
    dashboard.py                        # DailyDashboard (writes single-pane JSON)
    heartbeat_watcher.py                # CompetitionHeartbeatWatcher (per-strategy)
  risk/
    kill_switch.py                      # MODIFIED: accept strategy_id; per-strategy state
                                        # (back-compat: defaults preserve single-instance behavior)
config/
  competition/
    competition.yaml                    # Top-level: strategies enrolled, total_equity, tier bands
    {strategy_id}.yaml                  # Per-strategy config (existing pattern)
data/
  competition/
    state.json                          # Current tier + capital_share per strategy (atomic writes)
    ladder_history.jsonl                # Append-only tier transition log
    dashboard.json                      # Refreshed every cycle
  audit/
    {strategy_id}_{YYYY-MM-DD}.jsonl
  heartbeat/
    {strategy_id}.json
docs/
  design/
    path_b_multi_strategy_competition.md  # THIS DOC
  runbooks/
    competition_operator.md             # NEW: per-strategy reset/halt/promote runbook
scripts/
  run_competition.py                    # NEW entry point (extends run_paper_trading_vt.py pattern)
  competition_dashboard.py              # CLI to render dashboard.json as terminal table
references/
  pre-registrations/
    {strategy_id}.md                    # Per-strategy PreRegistration (already required by P5)
```

### 3.5 Loop structure (extension of `scripts/run_paper_trading_vt.py`)

```
MultiStrategyRunner.run_cycle():
  1. Fetch total_equity once (shared call, rate-budget conscious).
  2. If total_equity is None: increment competition-level fetch-failure counter;
     if max exceeded, halt ALL strategies and flatten ALL positions.
  3. For each enrolled strategy (in deterministic order, sorted by strategy_id):
     a. Compute equity_slice = total_equity × ladder.capital_share(strategy_id).
     b. Update per-strategy KillSwitch with equity_slice.
     c. If kill_switch[strategy_id].is_triggered: log, skip, notify, continue.
     d. Run strategy.generate_signals on its assigned pair.
     e. Compute target_units against equity_slice (NOT total_equity).
     f. Execute via SaxoExecutionBackend (no change to backend; per-pair routing).
     g. Reconcile attributed position (per-strategy) vs. broker position on that pair.
     h. Log to per-strategy audit + prediction log.
     i. Write per-strategy heartbeat.
  4. Run AutoLadder.evaluate_all() → emit any tier transitions, update state.json.
  5. Render dashboard.json.
  6. Notify on tier transitions (NOT on every trade — see §6.5 alert fatigue).
  7. Sleep until next cycle (default 30 min, same as existing).
```

### 3.6 Rate limit budget
Saxo: 1 req/sec. With N=10 strategies × ~3 API calls per strategy per cycle (chart, price, balance) + 1 shared balance + reconciliation = ~35 calls per cycle. At 30-min cycles, average rate is 0.02 req/sec. Headroom is fine.

**Watch-out:** if a kill switch triggers, the resulting `flatten_all` per strategy is a burst (one DELETE per position). N=10 simultaneous kill triggers (the §6.1 cascade scenario) = 10 burst calls. Implement a 200ms inter-call jitter to avoid Saxo throttling during the worst-case event.

---

## 4. Auto-promote/demote ladder (the competition mechanism)

Each rule below is **machine-checkable**, has a **numeric trigger**, an **action**, and a **cooldown/hysteresis**. Ladder evaluation runs once per cycle, *after* per-strategy execution, *before* dashboard render.

### 4.1 Tier definitions

| Tier | Capital share per strategy | Max # strategies | Total cap | Purpose |
|------|---|---|---|---|
| **TIER -1 (RETIRED)** | 0% | unlimited | 0% | Dead. Hard-retired per VTC-T9 / PROCESS-G1. May not return without new PreRegistration. Audit history preserved. |
| **TIER 0 (PROBATION)** | 1% | 5 | 5% | Just admitted from harness gate. Earning trust. |
| **TIER 1 (ACTIVE)** | 8% | 5 | 40% | Demonstrated 30+ days of OOS-Sharpe ≥ pre-reg threshold. Trades real (paper) size. |
| **TIER 2 (PROVEN)** | 15% | 3 | 45% | 90+ days at T1 with cumulative positive P&L. The "this is probably an edge" tier. |

**Total at-risk cap: 90%.** Reserve 10%. If the count of strategies × per-tier share would exceed 90%, see §3.2 auto-demote rule.

### 4.2 Promotion rules

| Transition | Trigger condition (machine-checkable) | Cooldown / hysteresis |
|---|---|---|
| **T0 → T1** | All hold for 30 consecutive trading days from T0 entry: (i) realized 30-day Sharpe ≥ `pre_reg.minimum_sharpe`; (ii) zero kill-switch triggers; (iii) zero equivalence-test failures; (iv) zero reconciliation kill-switch triggers; (v) cumulative P&L on the slice ≥ 0. | After promotion, strategy is **immune from demotion for 7 trading days** (settling period — early demotion on tier-transition noise is a Goodhart trap). |
| **T1 → T2** | All hold for 90 consecutive trading days at T1: (i) realized 90-day Sharpe ≥ `pre_reg.minimum_sharpe`; (ii) cumulative P&L on the slice ≥ +5% (i.e., the slice grew); (iii) ≤ 1 kill-switch trigger across the 90 days, with operator-signed reset; (iv) monthly equivalence test passes 3 consecutive months. | Immune from demotion for 14 trading days post-promotion. |

### 4.3 Demotion rules

| Transition | Trigger condition (machine-checkable) | Action / cooldown |
|---|---|---|
| **T1 → T0** | ANY of: (i) 30-day Sharpe < 0.5 × `pre_reg.minimum_sharpe` for 5 consecutive trading days; (ii) MaxDD on slice > 1.5 × `pre_reg.expected_max_dd`; (iii) monthly equivalence-test re-run fails (corr ≤ 0.95 OR Sharpe gap > 0.10 OR MaxDD gap > 2 pp); (iv) kill-switch triggered ≥ 2 times in any rolling 14-day window. | Capital share drops to T0 (1%) immediately. NOT closed; continues trading at probation size. Re-promotion requires 30 fresh consecutive days at T0. **No re-demote within 7 days** (hysteresis). |
| **T2 → T1** | ANY of: (i) 90-day Sharpe < 0.7 × `pre_reg.minimum_sharpe` for 5 consecutive trading days; (ii) cumulative P&L on slice goes ≤ −10% from peak; (iii) monthly equivalence-test fails. | Drops to T1 share (8%). 14-day hysteresis. |
| **ANY → RETIRED** (HARD) | ANY of: (i) **VTC-T9** equivalence violation (this is the PROCESS-G1 firm-wide invariant); (ii) any pre-reg trigger (`VTC-T1..T8` analogues per strategy) fires; (iii) operator manual retire with audit-log line. | Position flattened. Strategy removed from runner enrollment. Audit log marked `RETIRED_AT: <ts>`. May NOT return without new PreRegistration filed ≥ 30 calendar days before re-trial (per RETIREMENT_DECISION L4). |

### 4.4 Anti-flap hysteresis (additional rules)

- **Tier-transition cooldown:** No strategy may transition tiers more than once per 7 trading days. If a second trigger fires within the window, log it but defer action until the cooldown expires.
- **Same-day flap protection:** If a strategy is demoted T1→T0 and immediately satisfies promotion criteria the next day (e.g., a single strong day flips the rolling Sharpe), the promotion is *suppressed* until 14 trading days of fresh T0 history accrue.
- **Operator manual override:** the operator may force a tier transition with a signed audit log line (operator_id, reason, evidence_paths). Manual overrides also respect the 7-day cooldown unless flagged `EMERGENCY` (which auto-notifies CTO/CRO).

### 4.5 Monthly maintenance (automated)

On the 1st trading day of each month, after the cycle:
1. Re-run equivalence test for every enrolled strategy (engine vs. canonical reference). Failures trigger HARD RETIRE.
2. Re-run BacktestArsonTest on extended dataset including the prior month's paper data.
3. Recompute DSR with current trial count for every active strategy. If any strategy's DSR-adjusted p > 0.05, flag for HoQR review (does NOT auto-retire — DSR is a denominator-of-a-fishing-pool diagnostic, not a kill trigger; HoQR decides whether to require re-pre-registration).
4. Emit monthly competition report to `data/competition/monthly_{YYYY-MM}.md`.

### 4.6 Pre-registration enforcement

Every strategy admitted to Path B MUST have a PreRegistration that declares:
- `minimum_sharpe`: the floor below which retirement is automatic
- `expected_max_dd`: the slice drawdown ceiling
- `expected_n_trades`: per-month estimate (per RETIREMENT_DECISION L4 — auto-flag if observed deviates >2x)
- `pre_reg.retirement_triggers`: the 8-T VTC-style triggers, **strategy-specific**
- `pair`: which pair this strategy is assigned (for §3.3 partitioning)
- `validation_source`: which implementation produced the headline metrics (per PROCESS-G1)

The harness loader rejects any strategy without all of the above. No exceptions, no defaults.

---

## 5. Dashboard

### 5.1 What the operator sees (single screen, terminal-friendly)

```
COMPETITION DASHBOARD — 2026-04-25 14:30 UTC                  total_equity: $98,432
========================================================================================
strategy_id            tier  share  pair      today_pnl   30d_sharpe  hb_age  ks_state
----------------------------------------------------------------------------------------
fred_carry_eurusd      T1    8.0%   EURUSD    +$23.40     +0.42       2min    OK
fred_carry_gbpusd      T0    1.0%   GBPUSD    -$2.10      +0.18       2min    OK
tas_ceiling_usdjpy     T0    1.0%   USDJPY    +$0.00      n/a (warmup) 2min   OK
voltgt_audusd          T1    8.0%   AUDUSD    -$45.20     -0.31       2min    OK [DEMOTE_PENDING]
mean_rev_eurchf        T0    1.0%   EURCHF    +$1.10      +0.05       2min    OK
mom_4h_eurjpy          T2    15%    EURJPY    +$78.20     +0.78       2min    OK
----------------------------------------------------------------------------------------
totals                              6 strats   +$55.40                         0 HALTED
                                    34% allocated, 56% reserve+unallocated

Recent transitions (last 7 days):
  2026-04-23 mom_4h_eurjpy   T1→T2 (90d Sharpe 0.78, +6.2% slice growth)
  2026-04-21 mean_rev_eurchf RETIRED→T0 (re-pre-registered after equivalence pass, was R-2025-12-04)
  2026-04-19 fred_carry_audusd T0→RETIRED (VTC-T1 analog: 30d Sharpe -0.18 < 0.20)

Alerts:
  voltgt_audusd: 30d Sharpe -0.31 < 0.5 × pre_reg(0.30) for 4 consecutive days
                 (1 more day → DEMOTE T1→T0)
```

### 5.2 Underlying file format
- **`data/competition/dashboard.json`** — refreshed at end of every cycle (≤ 30 min latency). Schema:
  ```json
  {
    "rendered_at": "2026-04-25T14:30:00Z",
    "total_equity": 98432.10,
    "strategies": [
      {
        "strategy_id": "fred_carry_eurusd",
        "tier": "T1",
        "capital_share": 0.08,
        "pair": "EURUSD",
        "today_pnl_usd": 23.40,
        "rolling_sharpe_30d": 0.42,
        "rolling_sharpe_90d": 0.38,
        "slice_equity_usd": 7874.57,
        "slice_pnl_pct_today": 0.0030,
        "heartbeat_age_seconds": 124,
        "kill_switch_state": "OK",
        "kill_switch_reason": null,
        "pre_reg_path": "references/pre-registrations/fred_carry_eurusd.md",
        "minimum_sharpe": 0.30,
        "demote_pending_days": 0,
        "promote_pending_days": 12
      }
    ],
    "transitions_last_7d": [...],
    "alerts": [...],
    "totals": {
      "n_active": 6,
      "n_halted": 0,
      "allocated_pct": 0.34,
      "today_pnl_total_usd": 55.40
    }
  }
  ```
- **`data/competition/ladder_history.jsonl`** — append-only, one line per transition. Operator can `tail -f`.
- **`data/competition/state.json`** — current tier + capital share, atomic write-then-rename. Authoritative state; loader reads this on startup.
- **Markdown rendering:** `scripts/competition_dashboard.py` reads `dashboard.json` and renders the terminal table above. **Refresh cadence:** the JSON updates at 30-min cycle cadence; the terminal renderer is on-demand (operator runs it whenever they want to look). No daemon, no web server, no SSE — a flat file the operator can `cat` from anywhere is sufficient and auditable.
- **ntfy push (compressed):** see §6.5 — single daily digest, plus immediate notification on tier transitions and kill-switch triggers. NOT on every trade.

### 5.3 Refresh cadence summary
| Surface | Cadence | Trigger |
|---|---|---|
| `dashboard.json` | Every cycle (≤ 30 min) | End of `MultiStrategyRunner.run_cycle()` |
| `state.json` | On every tier transition | `AutoLadder.evaluate_all()` writes-then-renames |
| `ladder_history.jsonl` | On every tier transition | Same call site |
| Terminal table | On-demand (operator runs script) | `python scripts/competition_dashboard.py` |
| ntfy daily digest | Once at 16:00 local time | Cron-style scheduler in runner |
| ntfy immediate | On RETIRE / kill-switch trigger / equivalence fail | Inline in event handler |

---

## 6. Failure modes (devil's-advocate, mandatory ≥ 5)

### 6.1 All N strategies correlate; "diversification" is fake; one regime kills all
**Risk:** Multiple strategies are nominally distinct but all rely on the same hidden factor (e.g., USDJPY trend, low-vol regime, global risk-on). A regime change (BoJ pivot, vol spike) drawdowns them all simultaneously. The 90% cap means the firm watches 80% of paper equity bleed in a single week, and the dashboard celebrates "diversification" while every slice drops in lock-step.

**Mitigations:**
- **Pair partitioning (§3.3) reduces same-instrument correlation** but does NOT reduce factor correlation. A USDJPY long-vol strategy and an AUDUSD long-vol strategy are both short JPY and long carry-related risk-off pairs.
- **Pre-registration must declare expected-correlation cohorts.** HoQR rejects new strategies if their factor-cohort already has ≥ 3 strategies enrolled (e.g., max 3 "carry-flavored" strategies regardless of pair).
- **Monthly correlation report.** Compute pairwise daily-PnL correlation across all enrolled strategies. If any pair > 0.7 across a rolling 30-day window, flag for HoQR review.
- **CRO-style basket-correlation cap** (CONSENSUS Top Improvement #9) applies at the competition level: aggregate at-risk capital ≤ per-tier-cap × √(N_effective).

**Residual risk:** This is the highest unmitigated risk in Path B. Pair partitioning makes the problem *visible* (no "we don't know what we hold") but does not *solve* the factor-overlap problem. Accept and monitor.

### 6.2 Goodhart's law — researchers tune to tier criteria, not to truth
**Risk:** "30-day Sharpe ≥ pre-reg threshold" is a measurable target. Researchers begin tuning their strategies to clear T0→T1 promotion rather than to produce edge. Strategies optimized to look good for 30 days then decay are a known anti-pattern.

**Mitigations:**
- **Pre-registration locks the parameters.** A researcher who tunes parameters to clear T1 promotion is committing a PROCESS-G1 violation (equivalence fail vs. pre-reg). The pre-commit hook (P5) refuses the commit.
- **DSR with correct denominator.** Every parameter set evaluated counts as a trial, even if the researcher doesn't paper-trade it. The trial registry backfill is exactly the antidote.
- **The promotion thresholds are not knobs the researcher controls.** They are set by HoQR on PreRegistration approval. Changing them post-hoc requires a re-pre-registration.
- **Monthly arson test rerun.** A strategy that survived 30 days of paper but fails arson on the extended dataset is exactly the Goodhart symptom; it triggers HARD RETIRE.

**Residual risk:** A determined researcher who proposes 10 strategies and only pre-registers the 3 that "feel right after looking at paper data" still gets multiple-comparison fishing through the back door. HoQR is the only line of defense — must enforce "no strategy proposed after seeing any paper-trading data on a related strategy."

### 6.3 Single Saxo API timeout cascades across all N strategies' kill switches
**Risk:** The existing single-strategy kill switch trips on equity-fetch failures. With N=10 strategies, a single Saxo balance-API outage (which happens; CONSENSUS observed multiple) causes all 10 strategies to record a fetch failure, all 10 to trip the consecutive-failure threshold simultaneously, all 10 to attempt `flatten_all`, all 10 to write notifications. The result is N×N×... compounding failure modes the firm has never tested.

**Mitigations:**
- **Single shared `total_equity` fetch per cycle (§3.5 step 1).** All N strategies derive their slice from the one shared call. One fetch failure → one shared `equity_unavailable` flag → all strategies skip the cycle (NOT trigger their own kill switches).
- **Competition-level fetch-failure counter** distinct from per-strategy kill switches. Only the competition-level counter trips the global flatten. Per-strategy kill switches trigger only on per-strategy P&L drawdown of the slice, not on data-fetch failures.
- **Inter-call jitter (§3.6) on flatten bursts** to avoid Saxo throttling-induced cascading failure during the actual emergency.
- **Reconciliation pause when `equity_unavailable`.** Don't reconcile against zero or stale equity — that's how false-positive divergence triggers happen.

**Residual risk:** A Saxo outage that lasts > N × cycle_interval flattens everything by design. This is correct behavior (we cannot trade what we cannot observe) but the operator gets one big notification storm. The §6.5 mitigation handles the alert side.

### 6.4 Strategy-level P&L attribution becomes a fight when fills overlap
**Risk:** Originally a problem under attribution option (b). Pair partitioning in §3.3 *eliminates* fill-overlap by construction. **However:** the orphan-position problem from CONSENSUS shows the firm has historically had positions on the SIM book that were not authored by the currently-enrolled strategies. If a Path B strategy is enrolled on USDJPY and discovers an existing USDJPY position from a previous (retired) strategy, attribution fails — the strategy thinks it's flat, but the broker says long.

**Mitigations:**
- **P3 prerequisite:** start from a flat book. The 2026-04-25 flatten authorization must be executed before P3 is satisfied.
- **Startup reconciliation on every runner start:** if any pair has a broker position not matched to an enrolled strategy's intent, the runner refuses to start. Operator must manually reconcile (close orphan, transfer attribution, or remove the strategy enrollment).
- **Per-strategy intent file (`data/strategy_state/{strategy_id}.json`)** is the authoritative intent. Reconciliation compares intent vs. broker position on the strategy's assigned pair. Any divergence > min_order_size → kill switch trip on that strategy + halt (NOT competition-wide halt).

**Residual risk:** A bug in the attribution code that double-counts a position cannot be caught by reconciliation because reconciliation is *checking* attribution. The unit tests for `PositionAttribution` are load-bearing — see §7 milestone 2.

### 6.5 Operator alert fatigue (every strategy independently sends ntfy)
**Risk:** N strategies × every trade × every kill-switch trigger × every reconciliation warning = the operator silences notifications, then misses the one that mattered.

**Mitigations:**
- **Notification taxonomy:**
  - **Daily digest (low priority, once a day at 16:00 local):** total P&L, all strategy P&L lines, any tier transitions, any open alerts.
  - **Tier transition (default priority):** "fred_carry_eurusd promoted T0→T1." One notification per transition.
  - **HARD RETIRE (high priority):** "voltgt_audusd RETIRED — VTC-T9 equivalence fail." One notification.
  - **Competition-wide kill (urgent):** "COMPETITION HALTED — Saxo outage 6 consecutive failures, all positions flattened." One notification.
  - **Per-strategy kill (high, but rate-limited):** at most 1 per strategy per 24h. Subsequent triggers fold into the daily digest.
  - **NO per-trade notifications.** Trades go to `data/audit/{strategy_id}_*.jsonl` and the daily digest only.
- **Quiet hours respected** (existing pattern from `run_paper_trading_vt.py:60-64`).
- **Em-dash bug fixed** (CONSENSUS Top Improvement #14) — Path B inherits whatever fix lands in the existing notifier.

**Residual risk:** A single highly-active strategy could still produce many transitions in a week. Acceptable — that's signal, not noise.

### 6.6 (BONUS) The harness becomes the bottleneck
**Risk:** Every researcher routes through the same harness, the same trial registry, the same pre-commit hook, the same equivalence test infrastructure. If the harness has a defect (e.g., the rebalance_threshold collapse from RETIREMENT_DECISION L4), every Path B strategy inherits it. The exact failure that retired vol_target_carry, but now multiplied by N.

**Mitigations:**
- **P1 prerequisite:** the equivalence test must already pass for vol_target_carry before Path B dispatches. This forces the harness to be debugged once before N strategies depend on it.
- **Monthly equivalence rerun for ALL enrolled strategies.** Any strategy whose engine output drifts from its canonical reference triggers HARD RETIRE *and* an investigation into whether the engine itself drifted (vs. the strategy code). If the engine drifted, that's an incident — all strategies pause until reconciled.
- **Engine version pinning:** Path B's `competition.yaml` declares the engine git_hash it was approved against. Any commit to `src/forex_system/backtest/engine.py` triggers re-approval (pre-commit hook).

**Residual risk:** The engineering scaffold is now load-bearing for N strategies' validation, not 1. Ops cost rises non-linearly.

### 6.7 (BONUS) The kill-switch reset audit pattern doesn't scale
**Risk:** CONSENSUS flagged that the existing single-strategy kill-switch reset is opaque (no operator-ID, no audit-line, only process restart). With N strategies, reset becomes a more frequent operator action. If the audit pattern doesn't scale, the firm now has N opportunities for the Knight Capital pattern.

**Mitigations:**
- **CTO C4 remediation must land before P6.** The kill-switch reset protocol (operator_id + reason + evidence + audit line) is a prerequisite for Path B (folded into P6 via "per-strategy KillSwitch must be unit-tested" → tests must include reset audit).
- **Per-strategy reset uses per-strategy audit log.** `data/kill_switch_audit_{strategy_id}.log`. Operator must specify `--strategy-id` on reset CLI to prevent fat-fingered cross-strategy resets.

---

## 7. Implementation plan (phased, NOT executed today)

Each milestone has: deliverable, acceptance criterion (machine-checkable), estimated dev sessions (1 session ≈ 4 hours of focused dev).

### Milestone M1 — Per-strategy KillSwitch + audit (P6)
- **Deliverable:** `KillSwitch` class extended to accept `strategy_id` parameter; per-strategy state, per-strategy audit log path. Backward-compat: defaults preserve single-instance behavior. Operator reset CLI: `python scripts/reset_kill_switch.py --strategy-id <id> --operator-id <id> --reason <str>`.
- **Acceptance:** `tests/risk/test_kill_switch_per_strategy.py` ≥ 8 test cases passing (isolation, reset audit, reset CLI, two strategies tripping independently, shared-equity-fetch-failure scenario, reset-without-operator-id rejected, audit log format, double-reset rejected). All existing kill-switch tests continue to pass.
- **Estimate:** 2 sessions.

### Milestone M2 — `competition/` package skeleton + attribution
- **Deliverable:** `CompetitionConfig`, `MultiStrategyRunner` (no execution yet — dry-run only), `PositionAttribution` with startup-reconciliation. `harness.load_competition_config` rejects pair-overlap configs.
- **Acceptance:** `tests/competition/test_attribution.py` covers: pair-overlap rejection, orphan-position startup detection, intent-vs-broker reconciliation pass and fail. Dry-run mode prints planned actions for 3-strategy config without calling Saxo.
- **Estimate:** 3 sessions.

### Milestone M3 — `AutoLadder` rules engine
- **Deliverable:** `AutoLadder` evaluates all promote/demote/retire rules per cycle. Writes `state.json` and `ladder_history.jsonl`. Handles cooldowns, hysteresis, manual operator override.
- **Acceptance:** `tests/competition/test_ladder.py` covers: every transition rule (T0→T1, T1→T2, T1→T0, T2→T1, ANY→RETIRED), cooldown enforcement, anti-flap protection, capital-cap enforcement, manual override, equivalence-fail HARD RETIRE.
- **Estimate:** 3 sessions.

### Milestone M4 — Dashboard + ntfy integration
- **Deliverable:** `dashboard.json` writer at end of cycle, `competition_dashboard.py` terminal renderer, daily-digest scheduler, taxonomy-compliant ntfy notifier.
- **Acceptance:** `tests/competition/test_dashboard.py` covers: JSON schema validity, terminal renderer output snapshot, alert-prediction logic (DEMOTE_PENDING is correctly populated), notification taxonomy (no per-trade notifications emitted, daily digest emitted at scheduled time).
- **Estimate:** 2 sessions.

### Milestone M5 — `run_competition.py` + monthly maintenance
- **Deliverable:** Top-level entry point integrating M1-M4. Monthly equivalence rerun + arson rerun + DSR recompute scheduled. Heartbeat watcher for per-strategy heartbeats.
- **Acceptance:** End-to-end dry-run with 3 strategies × 3 simulated cycles produces correct dashboard, audit, ladder transitions. Monthly maintenance path is unit-tested with frozen-time cycling.
- **Estimate:** 3 sessions.

### Milestone M6 — Documentation + runbook + dispatch readiness review
- **Deliverable:** `docs/runbooks/competition_operator.md` (reset, halt, force-promote, force-retire, daily-review checklist), updated `CLAUDE.md` Path B section, dispatch-readiness checklist signed by CTO + HoQR + CRO.
- **Acceptance:** Runbook reviewed by CTO via `deploy-checklist-trading` skill; dispatch checklist all-green.
- **Estimate:** 2 sessions.

### Milestone M7 — Live dispatch with N=2 strategies
- **Deliverable:** Path B activated on Saxo SIM with vol_target_carry-resurrected (if equivalence-pass) + one alternate. Both at Tier 0 (1% slice each).
- **Acceptance:** 14 consecutive cycles complete without harness defects. Reconciliation passes every cycle. Daily digest delivered. No spurious tier transitions. Operator confirms dashboard usability.
- **Estimate:** 1 session of dev to enable; 14 cycles × 30 min = 7 hours of monitoring (not dev time).

### Milestone M8 — Scale to N=5
- **Deliverable:** 5 strategies enrolled, mix of T0 and T1 (depending on history at this point).
- **Acceptance:** Dashboard remains readable. Notification volume ≤ 5/day on average. No cross-strategy interference observed.
- **Estimate:** 1 session of dev (mostly config + monitoring).

**Total dev sessions:** 17 (= ~68 dev-hours = 8.5 work days).
**Calendar time:** Realistically 4-6 weeks given the prerequisite work needed before M1.

---

## 8. Cost & complexity estimate (honest)

### 8.1 Build cost
- **Dev hours:** 60-80 hours of focused dev (4-6 weeks calendar at solo pace, including the prerequisite work for P1-P6).
- **Net new code:** ~1,500-2,000 LOC across `competition/`, modified `kill_switch.py`, scripts, tests.
- **New tests required:** 30-50 unit tests across attribution, ladder, dashboard, reset-audit, isolation. The test suite roughly doubles in size for the competition path.

### 8.2 Ongoing maintenance cost
- **Per-cycle ops cost:** the harness runs every 30 min. With N=10 strategies, each cycle is ~5-10× the work of a single-strategy cycle (more API calls, more attribution checks, more dashboard updates). Saxo rate limit budget is fine (§3.6).
- **Operator daily ritual:** ~10 min/day reviewing dashboard.json, ladder_history.jsonl, and the daily digest. Up from ~2 min/day for single-strategy.
- **Monthly maintenance:** ~2 hours/month for equivalence reruns, arson reruns, DSR recompute, monthly report review. Up from ~30 min/month single-strategy.
- **Per-incident cost:** a kill-switch trigger now requires per-strategy investigation. If 3 strategies trigger in a week (the basket-correlation scenario), that's 3 separate post-mortems.
- **Per-PR review cost:** any PR touching `engine.py`, `kill_switch.py`, `attribution.py`, or `ladder.py` must run the equivalence test suite (P5 hook) and the competition test suite. Adds ~5-10 min per relevant PR.

### 8.3 Multi-strategy complexity multiplier
Reality check: **multi-strategy adds 5-10× the operational complexity of single-strategy.** Concretely:
- 5× the audit logs to inspect during incidents
- 5× the kill-switch states to monitor
- N× the equivalence tests to maintain
- Non-linear growth in cross-strategy interaction modes (the §6 failure modes are real)
- The dashboard becomes the operator's single point of truth — if it breaks, the firm is operating blind on N strategies, not 1

The 4-6 week dev estimate accounts for the *code*, not the *organizational discipline* required to operate it. The latter is the harder problem.

---

## 9. The kill criterion FOR THIS DISPATCH

> **If after running 5 strategies for 8 weeks, the firm has not learned anything that single-strategy + sequential trials wouldn't have surfaced, Path B is shut down.**

**Concrete operationalization:**

After 8 weeks of N≥5 enrolled strategies, HoQR + CTO conduct a **Path B retrospective** with these questions, each answered with evidence:

1. **Did Path B retire any strategy faster than a sequential trial would have?** Compare the actual retirement timestamps to a counterfactual sequential-trial calendar. If Path B did not save calendar time on at least 2 retirements, **fail**.
2. **Did Path B promote any strategy to Tier 2?** If zero strategies reached T2, the competition mechanism produced no graduations — Path B is operating as an expensive single-strategy harness. **Fail.**
3. **Did the parallel structure surface any failure mode (correlation, equivalence drift, ladder flap) that single-strategy trials would have missed?** If no novel failure modes were caught, Path B's distinctive value is unrealized. **Soft fail** (HoQR judgment call).
4. **Did the operator's daily-review time increase by more than 3× without corresponding learning?** If yes, the cost is not justified. **Fail.**
5. **Did any Path B strategy violate VTC-T9 (engine-equivalence) silently — i.e., the equivalence test missed a drift the monthly rerun caught?** If yes, the safety-net failed; Path B's risk has exceeded its benefit. **HARD FAIL** — shut down immediately, do not wait 8 weeks.

**Three failures (or one HARD FAIL) → Path B is sunset.** Strategies revert to single-strategy paper-trading via `run_paper_trading_vt.py` pattern. Code remains in repo (option value); enrollment goes to zero.

**Decision date:** 8 weeks after M7 dispatch, or earlier if HARD FAIL fires.

---

## 10. Recommendation to CEO

**Recommendation: DISPATCH AFTER TRACKS 5 AND 6 LAND.** Do not dispatch now; do not dispatch after the first single-strategy graduation. The middle path — wait for the prerequisites — is the only one consistent with the lessons just signed in `RETIREMENT_DECISION_2026-04-25.md`.

### Justification (against the prerequisites in §2)

1. **P1 (vol_target_carry equivalence pass):** This is binding firm-wide via PROCESS-G1. Path B is the highest-leverage place to enforce it (N strategies × the same engine). Dispatching before P1 means recreating the vol_target_carry failure mode at scale — the very thing the retirement was meant to prevent. **Cannot be skipped.**

2. **P2 (≥1 alternate strategy clearing harness gate):** Path B with N=1 is just single-strategy paper trading with extra steps. The competition mechanism is unproven if there is no second strategy to compete. The Track 6 work (FRED carry across 12 pairs, OR fresh strategy) provides the second candidate. **Cannot be skipped.**

3. **P3 (Saxo SIM flat):** The orphan basket from the prior carry-momentum script is exactly the attribution-poisoning failure mode (§6.4). Dispatching with non-zero starting positions guarantees a startup-reconciliation failure on cycle 1. **Cannot be skipped.**

4. **P4 (trial registry ≥ 25 entries):** The DSR denominator is currently 10. Path B will add ~50-100 trials in the first month. Without backfill, every Path B strategy's DSR-corrected p-value is wrong by an unknown factor. The risk is not catastrophic (DSR is a diagnostic, not a hard gate in Path B), but the firm is on record (CONSENSUS) committing to backfill. Dispatching before backfill normalizes the violation. **Should not be skipped.**

5. **P5 (pre-commit equivalence hook):** Without this, a researcher can land a Path B strategy validated by a research script. PROCESS-G1 violation. The pre-commit hook is the structural fix. **Cannot be skipped.**

6. **P6 (per-strategy KillSwitch unit-tested):** The cascade scenario (§6.3) and the alert-fatigue scenario (§6.5) both require per-strategy isolation. Without it, Path B is a multi-strategy facade over single-strategy primitives — strictly worse than running single-strategy in series. **Cannot be skipped.**

### Why not "dispatch now"
Dispatching now requires writing the harness *and* the prerequisites in parallel. Every prerequisite was created in response to a real failure (vol_target_carry retirement, kill-switch fallback bug, orphan-position observability, trial-registry under-count). Skipping a prerequisite to launch faster is choosing the same anti-pattern that produced the failures the prerequisite addresses. The expected-value calculation does not work — the cost of waiting 4 more weeks is small compared to the cost of launching N strategies on top of an unfixed engine.

### Why not "dispatch after first single-strategy graduation"
That standard is *too high*. The firm has zero strategies graduated to date. Waiting for the first T2-equivalent in single-strategy mode means waiting another 90+ days minimum. Path B's value is *increasing research velocity*; deferring it until after a single-strategy graduation forfeits the velocity gain on the next 12 weeks of bets.

### The middle path
Tracks 5 and 6 are already the firm's binding next priorities (per CONSENSUS Decision items 4 and 5, plus RETIREMENT_DECISION §6). They will land on the natural cadence regardless of Path B. Designing Path B *now* (this document), letting Tracks 5 and 6 land on their own timeline (~4-6 weeks), then dispatching Path B M1-M7 immediately after — that's the schedule that respects the lessons learned without sacrificing the velocity gain.

### Operational ask of CEO
1. **Approve this design doc** as the binding spec for Path B (no implementation begins until approved).
2. **Confirm the kill criterion in §9** — these are pre-committed retirement triggers for the dispatch itself, not just the strategies.
3. **Confirm the prerequisite gating in §2** — particularly P3 (orphan-position flatten must execute, not just be authorized).
4. **Decide the alternate strategy for P2** (HoQR's three ranked bets: FRED carry, TAS-ceiling, vol-target single-pair). The CEO selection from CONSENSUS Decision item 5 satisfies this.

---

## Appendix A — Cross-references

- `docs/architecture.md` (esp. §4.7 Execution Layer Live, §4.8 Analysis Layer, §8 Risk Architecture, §10 Phase 2/3 priority table) — Path B is a Phase 2 extension that pre-stages the Phase 3 multi-strategy execution path
- `docs/decisions/CONSENSUS.md` (esp. §"Top improvements" #6, #7, #10, #11, #12) — Path B is the structural home for these
- `RETIREMENT_DECISION_2026-04-25.md` (esp. §4 VTC-T9, §8 PROCESS-G1, L1-L5 lessons) — binding firm-wide invariants Path B must enforce
- `scripts/run_paper_trading_vt.py` — single-strategy pattern Path B extends
- `scripts/run_multi_strategy.py` — existing multi-strategy *blender* (different architecture: blends N signals into 1 trade per pair). Path B is the *competitor* (N independent strategies, N independent slices). The blender is NOT Path B's predecessor; they may coexist as different tools for different research questions.
- `references/saxo-bank-api-research.md` — sub-account availability constraint that drove §3.3 decision (c)

## Appendix B — What Path B is NOT replacing
- `scripts/run_paper_trading_vt.py` remains the canonical single-strategy paper-trading entry point. A strategy that wants single-strategy isolation (no competition pressure, no tier mechanics) uses this. Path B is additive.
- The existing `run_multi_strategy.py` (signal blender) remains for the research question "does ensembling these signals produce a better single decision per pair?" Different question from Path B's "which of these standalone strategies survives the OOS clock?"

---

*End of design document. No implementation work authorized by this document. Dispatch decision is reserved to CEO per §10.*
