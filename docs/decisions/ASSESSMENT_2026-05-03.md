# Project Assessment — 2026-05-03

**T+5 from Direction v1 ratification. T+80 to north-star deadline 2026-07-21.**

Five roles conducted independent assessment of the forex trading system project state on 2026-05-03. The overall finding is **YELLOW**: one role (CRO) returns CONDITIONAL-APPROVE on launch readiness; all four others (HoQR, CTO, QD, NHT) return YELLOW on probabilistic alpha quality, engineering hygiene, and falsification discipline. The project is operationally ready for a first paper bar under the authorized scope (USDJPY-only, vol_target_carry + Bet #1 regime-conditional) subject to two HIGH-severity remediation items that should be resolved before first trade. The joint probability of hitting the Tier-2 compound criterion (STRONG-only ≥10 AND paper Sharpe ≥0.5 by 2026-07-21) is approximately **0.18 (range 0.09–0.45)** per NHT. HoQR estimates the Sharpe-only criterion at approximately **0.35**.

---

## Per-role traffic-light table

| Role | Decision | Headline | Artifact path |
|---|---|---|---|
| HoQR (Head of Quant Research) | YELLOW | Thesis defensible but compressing; P(Sharpe ≥0.5 by deadline) ≈ 0.35; 3 early-kill scenarios with material probabilities | `.fintech-org/artifacts/2026-05-03T-project-assessment/hoqr-strategic-assessment.yaml` |
| CRO (Chief Risk Officer) | CONDITIONAL-APPROVE | All BC-1..BC-8 wired and verified; 2 conditions remain (account-key parity, 18.5% DD awareness) before second loop authorized | `.fintech-org/artifacts/2026-05-03T-project-assessment/cro-risk-assessment.yaml` |
| CTO (Chief Technology Officer) | YELLOW | 666 tests pass, sacred test intact, 6 CTO/CRO conditions closed-durable; ruff not clean (59 errors, 65 files to reformat) | `.fintech-org/artifacts/2026-05-03T-project-assessment/cto-engineering-assessment.yaml` |
| QD (Quant Developer) | YELLOW | HIGH: paper loop has no cost model; MEDIUM: constant_capital_sizing undocumented, fill model slippage=0.0 unreconciled | `.fintech-org/artifacts/2026-05-03T-project-assessment/qd-implementation-assessment.yaml` |
| NHT (Null-Hypothesis Tester) | maintain-prior-dissent (severity: material_concern) | Only 2/12 rejections are clean-STRONG (R6 NOT triggered); meta-concern partially resolved, new refined formulation preserved | `.fintech-org/artifacts/2026-05-03T-project-assessment/nht-falsification-assessment.yaml` |

---

## Where the project stands

### Strategic (HoQR)

The carry-family thesis remains defensible at T+5. The macro tape since 2026-04-25 is mixed: the BoJ held at 0.75% on 2026-04-28 with a hawkish 6-3 split (three members proposed a hike to 1.0% — the biggest dissent of the Ueda era), raised core CPI forecast to 2.8% from 1.9%, and cut FY26 growth to 0.5% from 1.0%. This is precisely the BoJ-divergence regime that CF-T9 is built to detect, and it argues for the regime-conditional Bet #1 thesis. However, the edge is compressing: the rate differential is projected to fall from ~325bp today to ~250-275bp by Q4 2026 as BoJ hikes and the Fed cuts; MoF intervention risk near the 162 "line in the sand" creates left-tail gap risk for any USDJPY long.

The STRONG-only 7/10 alpha confidence (or 8/12 by NHT's current count, with only 2 clean-STRONG per strict R6-NOT-triggered criterion) implies a probability-true-alpha of 60–75%, not the 95%+ a STRONG-only 10/10 would deliver.

**Three early-kill scenarios:**

| Scenario | Probability | Action |
|---|---|---|
| BoJ surprise rate hike at June 2026 meeting (one defection flips 6-3 hold to majority hike) | 0.25 | Pull Tier-1 alpha-direction kill day-of BoJ hike; convene pivot review within 5 trading days; flip Bet #1 size_multiplier to 0.0 immediately |
| USDJPY breaches 162 triggering MoF intervention with 3–5% gap move | 0.20 | Pull Tier-1 kill if rolling 60-bar OOS Sharpe drops below 0.30 OR drawdown exceeds 25% (fires before the 2026-06-23 calendar trigger) |
| ≥30 consecutive regime-inactive days for Bet #1 with Sharpe <0.40 | 0.15 | Retire Bet #1 immediately on auto_retire_on_trigger fire (already machine-checkable per pre-flight item 6); vol_target_carry continues solo |

### Risk (CRO)

The pre-launch wiring is correct. All 8 binding constraints (BC-1..BC-8) are verified with file/line evidence across both paper-trading loops. Drawdown ladder references paper-MTM equity (Saxo TotalValue including unrealized PnL). The three CRO conditions from prior consensus are closed-durable.

**Two conditional gates remain:**

1. **Account-key parity** — both paper-loop processes must be verified to point to the same Saxo paper account before the second loop (carry_fred regime-conditional) is authorized. Without this check, independent per-account exposure aggregation allows ~15x over-exposure relative to the CRO envelope.
2. **Operator awareness of the 18.5% worst-case 30-day drawdown scenario** — this is a plausible (not extreme) outcome under a BoJ surprise hike + carry unwind, well within the 20% full-halt ceiling. It must be pre-accepted by the operator before first bar.

Verification notes: `_JPY_CORRELATED` frozenset (`{USDJPY, GBPUSD}`) is structurally non-binding at USDJPY-only launch but becomes BLOCKING before any cross-JPY pair expansion. The watchdog observer thread lacks a top-level exception handler (known gap, non-blocking per Wave-6 CTO assessment, Wave-8+ hardening item).

### Engineering (CTO + QD)

666 tests pass as of 2026-05-03; the no-lookahead sacred invariant (`test_no_lookahead`) passes. All 6 CTO/CRO engineering conditions are closed-durable. Commit `ded1356` is approve-reaffirmed after independent CTO review.

The ruff linter is not clean: 59 errors and 65 files requiring reformatting. The errors are pre-existing (24 acknowledged in CONSENSUS_2026-04-28, grown to 59); none are on hot-path execution code (engine.py, execution.py, bet1_sizing.py, vol_target_carry.py, carry_fred.py are all clean).

**HIGH-severity QD finding: the paper loop has no cost model.** The backtest engine applies `RealisticCostModel` (spread, slippage, commission, swap) on every trade. Neither `run_paper_trading_vt.py` nor `run_paper_trading_carry_fred.py` imports or applies this model. Costs are absorbed implicitly by Saxo SIM fill prices, but the paper equity curve cannot be directly compared to the backtest equity curve without post-hoc cost reconciliation. Over a 60-trading-day CF-T9 Clause C window, this divergence compounds. The backtest Sharpe values (0.7594 vol_target_carry, 0.80 Bet #1) were computed with explicit cost deductions that are invisible in the paper log.

Additional MEDIUM divergences: `constant_capital_sizing` mode is undocumented for the validation run (if the validated Sharpe was computed with `constant_capital_sizing=True`, the paper loop compounding will diverge over multi-month run); fill model records `slippage_pips=0.0` at order placement with no post-fill reconciliation; swap/carry accrual relies on Saxo SIM automatic credits (may differ from `RealisticCostModel` swap constants).

---

## Falsification-discipline (NHT) — append-only refinement of meta-concern

**NHT refinement of meta-concern, append-only per Rule 6**

Severity: `material_concern`. Orchestrator-computed `does_block: false` (per NHT's explicit self-assessment: `does_block is orchestrator-computed from severity. NHT does not self-assert.`). Auto-ratification under `--full-auto` proceeds per user standing preference (reference: `/Users/huangtm/.claude/projects/-Users-huangtm-Projects-forex-trading-system/memory/feedback_full_auto_no_prompts.md`). The NHT dissent is a REFINEMENT of the already-preserved meta-concern from Direction v1 Section 8, which was CEO-ratified verbatim.

**NHT dissent-statement (verbatim, append-only):**

> PRESERVED-AND-REFINED DISSENT (2026-05-03 NHT project assessment, append-only):
>
> Updated meta-concern: of 12 rejections in trials.jsonl, only 2 are clean
> performance-falsifications on adequate samples (n_trades>=30 AND R1/R2/R3 fired
> AND R6 NOT triggered): tas_ceiling_4h (ab6f4167) and momentum (fdddc2b0). The
> remaining 10 are sample-size-contaminated: 4 pure-R6-only rejections, plus 6
> R1/R2 rejections that ALSO fired R6 (the strategy fell below the Sharpe/DSR
> floor at a sample size where the floor itself is statistically uninterpretable).
>
> This is a refinement, not a withdrawal, of the original 2026-04-28 meta-concern.
> The original framing ('22 trials WITHOUT falsifications is itself a
> falsification of the claim that this org falsifies') has been answered in
> process — rejections ARE now logged. The new framing is sharper:
>
>   "12 rejections of which only 2 are clean performance-falsifications on
>    adequate samples is itself a partial falsification of the claim that
>    this org performs ADEQUATE-SAMPLE performance falsification."
>
> Concrete operational implication for the paper-launch period (T+0 → T+80
> days, deadline 2026-07-21): the STRONG-only quality-adjusted CONDITION-1
> (10 STRONG-only rejections) cannot be met within the deadline at the
> current rate of HoQR dispatch (zero new STRONG-rejection trials scheduled
> during paper-launch operations). Joint Tier-2 probability is 0.18 (range
> 0.09–0.45 depending on HoQR bandwidth allocation).
>
> Recommended remediation (route to HoQR + QD, not NHT-implementable):
> a) Dispatch 5 re-config sweeps against the existing registry — each
>    designed to force n_trades >= 30 so the resulting R1/R2 verdict is
>    a clean-STRONG: vol_target_carry_no_vol_scaling multi-regime
>    ablation, tas_ceiling on 1d/1w, bollinger_rsi shorter lookback,
>    carry_momentum daily rebalance, ma_crossover 5/20.
> b) Amend the trial schema so oos_window_start/end is REQUIRED at
>    spawn for ALL trials including rejections (currently populated for
>    1 of 13 post-Phase-2 trials — the one PASS). Without this, the
>    family-wise FDR over the 80-day paper window is unaudited.
> c) Add a derived field 'strong_clean' to the rejection record: True
>    iff (R1 OR R2 OR R3) AND NOT R6. Track CONDITION-1 against this
>    derived field rather than the raw rejection count, so the
>    mechanical 12/10 vs quality-adjusted 2/10 gap is visible to CEO.
>
> This dissent does NOT block paper launch — paper launch is independently
> authorized under CONSENSUS_2026-05-02 with vol_target_carry + Bet #1
> regime-conditional sizing. The dissent is preserved to ensure the
> STRONG-only Tier B gap is a tracked deliverable, not a quietly-dropped
> governance item, during the paper-launch wave.

---

## Material risks before first paper bar (HIGH)

1. **QD HIGH — Cost model absent in paper loop.** Neither paper script applies `RealisticCostModel`. The backtest equity curve (Sharpe 0.7594 / 0.80) includes spread, slippage, commission, and swap costs that the paper loop does not log or reconcile. The paper P&L will appear higher than backtest-equivalent until costs are applied, creating a systematic backtest-vs-paper P&L divergence that will mislead performance attribution throughout the Clause C window. Owner: QD. Scope: ~30 LoC across 2 files.

2. **CRO HIGH — Separate-accounts misconfiguration → ~15x silent over-exposure.** If both paper loops (vol_target_carry and carry_fred) run against different Saxo paper accounts, neither loop sees the other's USDJPY exposure. Combined notional could reach ~225% of single-account-equity (2x leverage vt + 0.25 carry_fred) vs. 15% CRO intent. The code provides no cross-account aggregation primitive. Mitigation: account_key assertion at startup. Owner: QD + Ops.

3. **HoQR/NHT joint — P(Tier-2 by deadline) is low (~0.18).** The project faces a meaningful probability of hitting the Tier-1 alpha-direction kill criterion (2026-06-23) before the Tier-2 north-star. Early-kill trigger enumeration and monitoring rules should be in place before first bar, not deferred to the calendar trigger.

---

## Material risks before first paper bar (MEDIUM)

4. **QD MEDIUM — `constant_capital_sizing` mode undocumented for validation run.** If the validated Sharpe figures (0.7594 / 0.80) were computed with `constant_capital_sizing=True`, the paper loop (which always uses live equity compounding) will exhibit different volatility-targeting behavior during periods of equity drawdown or growth. Owner: QD + HoQR. Scope: annotate the validated backtest call; confirm paper loop is consistent.

5. **QD MEDIUM — Fill model `slippage_pips=0.0` with no post-fill reconciliation.** `execution.py:117-119` records `fill_price=mid` and `slippage_pips=0.0` at order placement. No post-fill update fetches the actual fill price from the broker response. Realized slippage is permanently untracked in the paper log. Owner: QD.

6. **CTO MEDIUM — F-code count grew 24→59.** Style hygiene; the accumulation signal suggests technical debt is growing. None of the 59 errors are on hot-path execution files. All 46 fixable errors can be resolved with `ruff --fix` in a single dispatch. Not a blocking concern but should not be deferred past Wave-8.

---

## What the org has gotten right (signal)

- All BC-1..BC-8 wired and verified with file/line evidence — the risk architecture is correctly instantiated.
- Sacred test (`test_no_lookahead`) intact through 7 commits and 666 passing tests.
- NHT caught the Wave-6 CF-T9 cold-start gate producer/consumer schema mismatch — adversarial discipline is working, and the Wave-7 fix was verified by NHT re-verification before this assessment.
- 6/6 CTO/CRO engineering conditions closed-durable with audit-grade evidence.
- `bet1_size_multiplier` fully traced from `regime_active_status()` through to `client.place_order()` at `execution.py:89` — no bypass exists.
- Policy-violations log (`policy-violations.jsonl`) exercised by real violations, not a synthetic test artifact.
- Pre-commit hook is installed and active; kill-switch threshold pre-registration is enforced at commit time.

---

## Recommended next actions

| Priority | Action | Owner | By |
|---|---|---|---|
| HIGH | Close cost-model gap before first paper bar: apply spread/slippage/swap costs in paper loop equity-write so paper P&L is backtest-equivalent | QD | Before first paper bar |
| HIGH | Deploy-checklist account-key parity gate: pre-bar startup check that `backend.account_key` matches across both paper-loop processes; halt if divergent | QD + Ops | Before second loop authorization |
| MEDIUM | Resolve `constant_capital_sizing` semantics: annotate the validated backtest call; document validated mode; ensure paper loop is consistent | QD + HoQR | Wave-8 |
| MEDIUM | Fill model post-fill reconciliation: after order submission, re-fetch and update `fill_price`, `slippage_pips` from broker response | QD | Wave-8 |
| STRATEGIC | Enumerate Tier-1 early-kill triggers: define 3 early-kill scenarios (BoJ hike, intervention, 30-day regime-inactive) with monitoring rules and decision logic so they can fire BEFORE 2026-06-23 calendar trigger | HoQR + CRO | Before first paper bar |
| NHT informational (not Wave-8 blocker) | Dispatch 5 re-config sweeps to force n_trades≥30; make `oos_window_start/end` REQUIRED at trial spawn; add derived `strong_clean` field to rejection records | HoQR + QD | Wave-9+ |

---

## CEO actions still pending (from CONSENSUS_2026-05-03_wave7_closure)

- **Item 9**: 60-trading-day calendar reminder for CF-T9 Clause C (must be set on day T=0 of first paper bar).
- **Item 10**: Launch communication with verbatim CF-T9 disclosure.
- **Stale log disposition**: QD recommends archiving `data/paper_trading_session.log` to a timestamped backup path and letting the first real paper bar create a clean log. Do NOT truncate in-place (the 3 plain-text header lines and mixed equity=1000000.0/100000.0 entries indicate multiple sessions; truncate would hide this history).
- **Saxo paper-account parity confirmation**: Confirm that both paper-loop processes will target the same Saxo paper account before authorizing the second loop.

---

## Disagreement matrix

All 5 roles converge on YELLOW at the system level. CRO is structurally CONDITIONAL-APPROVE (not YELLOW) because the CRO lens is launch-readiness on risk controls, not probabilistic alpha; the launch-readiness verdict is positive given that BC-1..BC-8 are all wired. NHT's `material_concern` is structural-skeptic discipline — a governance quality observation — not a disagreement with the other roles about engineering state or risk controls. No role-vs-role contradictions exist in this assessment cycle.

---

## Signatures

| Role | Decision | Artifact timestamp |
|---|---|---|
| HoQR | YELLOW | 2026-05-03T15:30:00Z |
| CRO | CONDITIONAL-APPROVE | 2026-05-03T00:00:00Z |
| CTO | YELLOW | 2026-05-03T20:00:00Z |
| QD | YELLOW | 2026-05-03T18:30:00Z |
| NHT | maintain-prior-dissent (material_concern) | 2026-05-03T11:55:00Z |
| PM (consolidation) | auto-ratified | 2026-05-03T16:05:00Z |

**Auto-ratification basis:** Consolidated under `--full-auto` per user standing preference (`feedback_full_auto_no_prompts.md`). NHT severity `material_concern` is orchestrator-computed as `does_block: false`. The NHT dissent is a refinement of the existing CEO-ratified meta-concern from Direction v1 Section 8 (preserved verbatim, append-only). Proceeding silently per user preference; body surfaced via async-transparency.
