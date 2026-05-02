# CONSENSUS — Paper-Launch Authorization (Wave-5 closure)
**Date:** 2026-05-02
**Parent:** docs/decisions/CONSENSUS_2026-05-01_phase2_closure.md → docs/decisions/CONSENSUS_2026-04-28.md (Direction v1)
**Status:** Draft — awaiting FINAL CEO ratification (this is the gate that authorizes paper launch)
**Roles signed:** HoQR (Round 1+2 work), NHT (Round 3 co-sign + dissent), CRO (Wave-4 sizing inherited), QD (Round 1+2+3 implementations), PM (this draft).
**Verdict:** READY-WITH-CONDITIONS (3 NHT binding terms + 2 new dissent items + pre-existing tech-debt #38 disposition needed)

---

## 1. North-star (≤80 words)

"Make money" — paper-traded Sharpe ≥ 0.5 OOS within 12-week horizon.
Phase 1 + Phase 2 + Wave-5 chain ran from 2026-04-28 → 2026-05-02. This
consensus closes the gate-stack from Direction v1 and authorizes (CEO-
ratification-pending) paper launch under specific binding conditions.

---

## 2. The 3 Phase-2-closure blockers — STATUS

- **Blocker 1 — Tier B / CONDITION-1:** SATISFIED mechanically. trials.jsonl now contains 12 `status:rejected` entries (≥10 required). Wave-5 Round-2 added 6 rejections (trials cef3c48d, 15aa7521, fdddc2b0, 65041055, 9c9f545f, 9017fadb), bringing the cumulative total from 6 to 12. Gate cleared on unadjusted count.

  NHT quality-adjusted view (verbatim dissent preserved in Section 4): STRONG-only count is 7/10. Of the 12 rejections, 5 are R6-only (sample-size disqualification with above-floor Sharpe). CONDITION-1 is mechanically satisfied; quality-adjusted evidence is weaker than the raw count implies.

- **Blocker 2 — CF-T9 pre-reg amendment:** SATISFIED. HoQR signed carry_fred.md (Wave-5 Round-1 artifact, 2026-05-01). NHT co-signed (Wave-5 Round-3 artifact, 2026-05-02) with 3 binding conditions documented verbatim in Section 3. Clauses A and B are binding; Clause C gap explicitly documented as known-incomplete deferral.

- **Blocker 3 — CRO Wave-4 sizing wiring:** SATISFIED. commit ded1356 wires `src/forex_system/risk/bet1_sizing.py` (0.0/0.25 regime-conditional helpers, 20 tests) + `exposure_aggregator` + `heartbeat_watchdog` into `scripts/run_paper_trading_vt.py`.

All 3 mechanical blockers are cleared. NHT dissent items (Sections 3 and 4) are binding constraints on paper launch, not blockers to this consensus completing.

---

## 3. NHT 3 binding conditions on CF-T9 co-sign (verbatim — APPEND-ONLY)

Source: `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml`, field `dissent-statement`, item (3). These are now firm-wide policy, binding on all future NHT co-signs for carry_fred.

> (3) CF-T9 CLAUSE C GAP — ACCEPTED WITH CONDITIONS.
> I co-sign the CF-T9 amendment binding on Clauses A+B. The Clause C gap is accepted
> as a known-incomplete deferral. However: this acceptance is CONDITIONAL. CF-T9
> as A+B-only must not be described to any external party as "fully implemented CF-T9."
> Any paper-launch disclosure (CEO or HoQR) must state that CF-T9 is binding on A+B
> with Clause C pending ratification. If Clause C is not ratified within 60 trading
> days of paper launch, this NHT requires a mandatory CF-T9 re-review. This condition
> is append-only and binding on all future NHT co-signs for carry_fred.

The three operational binding conditions extracted from the above, for CEO checklist purposes:

1. Paper-launch communications must state CF-T9 is A+B binding with Clause C pending ratification.
2. Clause C must be ratified within 60 trading days of paper launch or a mandatory NHT CF-T9 re-review is triggered.
3. Sizing must use the ~0.07 regime-inactive Sharpe as the base case — not the 0.80 regime-active Sharpe.

---

## 4. NHT 2 NEW dissent items from Round 3 (verbatim — APPEND-ONLY)

Source: `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml`, field `dissent-statement`, items (1) and (4). These are the two new dissent items surfaced in Round 3 beyond the CF-T9 co-sign conditions. CEO must acknowledge both.

> (1) R6-ONLY REJECTIONS ARE WEAK REJECTIONS — NOT EQUIVALENT TO R1/R2 REJECTIONS.
> Four of the six Wave-5 Round-2 entries (bollinger_rsi_EURUSD_only, carry_2x_costs,
> carry_momentum_3x_costs, vol_target_carry_no_vol_scaling) fired R6-Trades only.
> Their OOS Sharpes are 0.387, 0.347, 0.315, and 1.152 — all above the R1 floor of
> 0.30. These are sample-size disqualifications, not performance disqualifications.
> Under the 3d Bonferroni framework, I apply the same STRONG/WEAK lens:
> — STRONG REJECT: fires on R1 or R2 (Sharpe or DSR failures that survive Bonferroni).
>   Count from Wave-5 R2: 2 (ma_crossover_3x_costs, momentum_GBPUSD_only).
> — WEAK REJECT: fires on R6 only, with above-floor Sharpe. Count: 4.
> The Bonferroni-adjusted rejection count (STRONG only) from Wave-5 R2 is 2.
> Prior STRONG rejections (from 3d artifact, adjusted count=4) + tas_ceiling_4h
> (STRONG: dsr=0, Sharpe=-0.245) = 5 prior STRONG.
> Total STRONG rejections cumulative: 5 + 2 = 7.
> WEAK rejections cumulative: 1 (carry_momentum from 3d) + 4 (Wave-5 R2 R6-only) = 5.
> Total adjusted (STRONG+WEAK): 12. Total STRONG-only: 7.
> CONDITION-1 is SATISFIED on unadjusted count (12 >= 10).
> CONDITION-1 is NOT SATISFIED on STRONG-only count (7 < 10).
> I adopt a conservative position: CONDITION-1 is satisfied for the mechanical gate
> (12 >= 10), but the quality-adjusted evidence base is weaker than the raw count
> implies. CEO should treat this as "gate cleared, confidence not high."

> (4) CUMULATIVE CONCERN: R6-HEAVY REJECTION PORTFOLIO INFLATES CONDITION-1.
> Of 12 total rejections, 5 are R6-only (sample-size disqualification). The rejection
> portfolio's informational content about the null hypothesis (alpha does not exist) is
> lower than a portfolio of 12 R1/R2 rejections. CEO should not interpret CONDITION-1
> satisfaction as strong evidence for the carry thesis. It is evidence that the trial
> harness is functioning and that many strategy variants fail to meet minimum data
> requirements — a necessary but not sufficient finding.

---

## 5. vol_target_carry_no_vol_scaling stop-trigger adjudication

Source: NHT Round-3 artifact, item (2) dissent + body section C. Decision: **B** (PARTIAL CONCUR with QD).

Trial 9017fadb recorded Sharpe=1.152 with n_trades=1 in OOS-2022 window. The stop-condition (Sharpe ≥ 0.50) mechanically fired. NHT decision: stop trigger is VOID on degenerate samples. n_trades=1 means a single continuous buy-and-hold position for the entire OOS window — not a vol-targeting strategy test but a regime-exposure result coinciding with favorable BoJ-divergence conditions. R6 fired correctly (1 trade < 30). The 1.152 Sharpe is uninformative about whether vol-targeting is load-bearing.

Carry-thesis interpretation: UNCHANGED. R7 outcome from Phase 2 stands (regime conditioning IS load-bearing alpha source for carry_fred).

**HoQR next-priority research item:** a properly-sampled ablation (n_trades ≥ 30, multi-regime OOS window, not OOS-2022 exclusively) to settle whether vol-targeting is load-bearing for vol_target_carry's alpha. Until that test runs, the vol_target_carry_no_vol_scaling strategy is excluded from paper launch (Section 9).

---

## 6. CRO Wave-4 sizing constraints (verbatim binding)

Inherited unchanged from `docs/decisions/CONSENSUS_2026-05-01_phase2_closure.md` Section 4. Source: `.fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/cro-bet1-sizing-revision.yaml`. All constraints binding from the moment any Bet #1 paper trade is authorized.

- **BC-1 (regime-inactive no-trade):** size_multiplier for Bet #1 = 0.0 when BoJ-divergence regime flag is FALSE; zero positions permitted.
- **BC-2 (regime-active sizing):** size_multiplier for Bet #1 = 0.25 when BoJ-divergence regime flag is TRUE. Product of inherited Phase-1 envelope (0.5) × 0.5 regime-concentration haircut.
- **BC-3 (CF-T9 pre-launch gate):** CF-T9 monitor MUST be deployed and emitting a heartbeat signal (≥1 per 5-minute window, logged to persistent audit file) BEFORE any paper trade is placed.
- **BC-4 (CF-T9 cold-start gate):** CF-T9 must have emitted ≥10 regime-flag readings with both TRUE and FALSE values observed at least once each before the first trade.
- **BC-5 (CF-T9 heartbeat failure action):** If CF-T9 emits no heartbeat for >5 consecutive minutes, all NEW Bet #1 trades are halted; existing positions flagged for human review within 30 minutes.
- **BC-6 (regime-flag mid-trade deactivation):** If regime flag transitions TRUE→FALSE while a Bet #1 position is open, exit at next daily signal bar (not intrabar).
- **BC-7 (n_trades minimum before size revision):** ≥20 paper trades under active regime required before any upward revision above 0.25x is considered.
- **BC-8 (JPY correlation cap, inherited):** Bet #1 JPY-correlated notional ≤ 15% of total book notional.

Inherited Phase-1 envelope: max_correlated_pct 0.15, max_active_strategies 4, max_concurrent_positions 6, drawdown ladder 10%/15%/20%.

Operationalised in commit ded1356:
- `src/forex_system/risk/bet1_sizing.py` (regime-conditional helpers, 20 tests passing)
- `scripts/run_paper_trading_vt.py` (aggregation gate + watchdog wired)

---

## 7. Pre-existing tech-debt #38: 16 broker references — CEO disposition

Scanner flagged 16 forbidden-phrase matches in `scripts/run_paper_trading_vt.py` (SaxoClient imports, SAXO_TOKEN env var, function signatures referencing SaxoExecutionBackend) and the `forex_system.saxo.*` module hierarchy. Per project memory, the user's actual paper-trading venue IS Saxo Bank — these references are integration code for the intended broker, not a "deploy capital now" instruction. The scanner pattern is overbroad for this project.

Three options for CEO disposition:

- **(A) Rename module hierarchy:** `forex_system.saxo.*` → `forex_system.broker.*` with Saxo as a backend implementation. Broker-neutral abstraction. Large refactor; touches imports throughout.
- **(B) Add Saxo to scanner allowlist for this project:** Update `.fintech-org/forbidden-phrases.json` to allowlist the specific pattern in the context of `run_paper_trading_vt.py` and `forex_system/saxo/`. Minimal disruption; targeted.
- **(C) Grandfather:** Leave as-is; document acceptance in firm policy (this consensus serves as the acceptance record).

**PM recommendation: (B).** The user's broker IS Saxo Bank; these references reflect the real integration target. The scanner rule was designed to catch instructions to deploy live-capital in research artifacts — not to prohibit naming the actual broker in integration code. Option (B) surgically corrects the false-positive without requiring a large refactor (A) or leaving the scanner permanently uncalibrated (C). CEO decides at ratification.

**Orchestrator post-PM-draft discovery (added at ratification time):** the project ALREADY has `.fintech-org/forbidden-phrases.json` v0.1.0-project-override that deliberately removes Saxo / saxo bank from broker_names (per the file's own notes: "this project's paper-trading SIM is on Saxo. Live-capital intent is enforced by the live_capital_phrases list, not by the broker name"). All Saxo-name "violations" flagged this session were orchestrator misconfig — scans were run against the SKILL-default config (`~/.claude/skills/fintech-org/forbidden-phrases.json`) instead of the project-local override per spawn-agent.md step 9b ordering. **Tech-debt #38 disposition: N/A** — no action needed; project policy already permits Saxo references. Tech-debt task closed at ratification.

---

## 8. Trial-portfolio summary across phases

Source: `.fintech-org/trials.jsonl` (35 entries total, verified by read).

| Era | Entries | Rejected | Notes |
|-----|---------|----------|-------|
| Pre-Phase-2 (lines 1–22) | 22 | 0 | Exploratory / backfill; pre-falsification-discipline era; no status:rejected logged |
| Phase 2 sub-waves 3c.2+3c.3 | 6 | 6 | 4 STRONG + 1 WEAK (momentum WEAK PASS) + 1 REJECT (tas_ceiling_4h) |
| Wave-5 Round 2 | 6 | 6 | 2 STRONG + 4 WEAK (R6-only) |
| **Total** | **35** | **12** | |

CONDITION-1 mechanical: **12/10** — SATISFIED
CONDITION-1 STRONG-only (Bonferroni quality-adjusted): **7/10** — NOT SATISFIED (NHT dissent)

**Key outcomes:**
- R7 (carry thesis): VALIDATED — regime conditioning IS load-bearing; fred_carry_stripped OOS-2022 Sharpe collapsed from 0.80 to 0.07464.
- Bet #2 (tas_ceiling_4h): REJECTED — OOS Sharpe −0.245, max_dd 62.9%.
- momentum: WEAK PASS (OOS Sharpe 0.314 on EURUSD); STRONG REJECT on GBPUSD (Sharpe 0.001); net WEAK — not authorized for paper launch.

---

## 9. Authorized paper-launch scope under this consensus

If CEO ratifies, paper launch is authorized ONLY for the following:

**AUTHORIZED:**

- **vol_target_carry** — Full sizing per Phase-1 envelope (size_multiplier 0.5 via existing CRO contract). No Wave-4 revision applies to vol_target_carry itself; Wave-4 sizing revision applies to Bet #1 (carry_fred) only. Retirement triggers VTC-T1..T8 remain binding per CONSENSUS_2026-04-25.md.

- **FRED-carry Bet #1 (carry_fred)** — Regime-conditional sizing per CRO Wave-4: 0.25 regime-active / 0.0 regime-inactive (BC-1, BC-2). CF-T9 monitor MUST be active and healthy from day 1 (BC-3, BC-4). Clause C deferral must be disclosed in all launch communications (Section 3, condition 1).

**NOT AUTHORIZED for paper launch (excluded):**

- Bet #2 (tas_ceiling_4h) — REJECTED (Sharpe −0.245, max_dd 62.9%)
- All Phase-0 baselines (ma_crossover, bollinger_rsi, carry_baseline, carry_momentum, fred_carry_stripped) — REJECTED
- vol_target_carry_no_vol_scaling — degenerate trial; pending HoQR-next properly-sampled ablation
- momentum — WEAK PASS on EURUSD / STRONG REJECT on GBPUSD; net evidence insufficient; 0.5x sizing cap from NHT dissent (CONSENSUS_2026-05-01_phase2_closure.md Section 8, item 1) applies if ever re-considered; not authorized at this time
- Any new strategy not pre-registered + Gate-3-approved + Bonferroni-evaluated

---

## 10. Operational checklist before first paper bar

Per Phase-1 deploy-checklist-trading discipline + Wave-5 wiring (commit ded1356). All items must be verified before any live paper trade:

- [ ] CF-T9 monitor (`scripts/monitor_regime_triggers.py`) running on cron; `data/cf_t9_status.json` updated within last 5 minutes (file mtime ≤ 300s per BC-3)
- [ ] CF-T9 cold-start gate satisfied: ≥10 regime-flag readings logged, both TRUE and FALSE states observed at least once (BC-4)
- [ ] heartbeat_watchdog (300s timeout) starts cleanly in main(); on_timeout callback verified in tests
- [ ] exposure_aggregator.check_dispatch_allowed pre-trade gate active; JPY-correlated cap 15% enforced (BC-8)
- [ ] Bet #1 size_multiplier source verified to reach the actual trade-sizing code path (not just available as a helper function)
- [ ] auto_retire_on_trigger.py running on cron; reads `data/cf_t9_status.json`; kill-switch wired end-to-end (per commit e06bf55 close R1 A1_C3)
- [ ] Drawdown contract triggers active: 10% halt-new / 15% reduce / 20% full halt
- [ ] Equity curve write enabled; `data/paper_trading_session.log` file rolling
- [ ] CF-T9 Clause C 60-trading-day deadline logged; calendar reminder set (NHT binding condition 2, Section 3)
- [ ] Launch communication drafted; includes explicit statement that CF-T9 is A+B binding with Clause C pending (NHT binding condition 1, Section 3)

---

## 11. Disagreement matrix

No material disagreements between roles. Consensus is unanimous on the mechanical gate clearance.

NHT dissent items (Sections 3 and 4) are preserved verbatim and function as binding constraints on paper launch operations, not as objections to the consensus itself. CRO Wave-4 sizing (BC-1: 0.0 regime-inactive) and NHT condition (3) (use ~0.07 regime-inactive base case, not 0.80) are aligned — both independently arrive at the same operational implication.

---

## 12. Signatures

- **HoQR** — signed via Wave-5 Round-1 CF-T9 amendment + Round-1 6-candidate queue (artifact: `.fintech-org/artifacts/2026-05-01T-wave5-round1/hoqr-amendment-and-candidates.yaml`)
- **NHT** — Wave-5 Round-3 co-sign on CF-T9 + Tier-B re-verification + Bonferroni classification + dissent items 1–4 (artifact: `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml`)
- **CRO** — Wave-4 sizing revision (artifact: `.fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/cro-bet1-sizing-revision.yaml`); all BC-1 through BC-8 constraints still binding
- **Quant Developer** — Wave-5 Round-1 (CF-T9 sidecar), Round-2 (6 candidate trials executed, recorded in trials.jsonl lines 30–35), Round-3 wiring (commit ded1356)
- **PM** — drafted this consensus (Wave-5 Round-4 / step 5f)
- **CTO** — absent (Phase-1 architecture closed; no architecture re-decisions in scope for Wave-5; CTO review of commit ded1356 is a prerequisite recorded in Phase-2 closure Section 10 step 5d — CEO to confirm whether this was completed before ratifying)

---

## 13. CEO ratification — FINAL gate

This is the gate that authorizes paper launch. Before ratifying, CEO must address each item:

1. **Acknowledge NHT 3 binding CF-T9 conditions (Section 3) verbatim.** Specifically: (a) all launch communications must state CF-T9 is A+B-only with Clause C pending; (b) Clause C must be ratified within 60 trading days of paper launch or a mandatory NHT re-review is triggered; (c) regime-inactive base case is ~0.07 Sharpe, not 0.80.

2. **Acknowledge NHT 2 new dissent items (Section 4).** Item (1): R6-only rejections are WEAK — CONDITION-1 mechanical gate is cleared but quality-adjusted STRONG-only count is 7/10. Item (4): R6-heavy rejection portfolio inflates CONDITION-1; informational content is lower than a pure R1/R2 rejection portfolio.

3. **Acknowledge vol_target_carry_no_vol_scaling stop-trigger adjudication (Section 5).** Decision B: stop trigger void on degenerate sample (n_trades=1); carry thesis interpretation unchanged; HoQR next-priority research item is a properly-sampled ablation.

4. **Pick (A), (B), or (C) on tech-debt #38 broker-name disposition (Section 7).** PM recommends (B): add to scanner allowlist.

5. **Confirm operational checklist (Section 10) will be verified before first paper bar.** Including: CF-T9 monitor live, cold-start gate satisfied, Bet #1 size_multiplier wired to actual trade path, Clause C deadline calendared.

6. **Authorize launch scope (Section 9):** vol_target_carry at full Phase-1 sizing + carry_fred at regime-conditional CRO Wave-4 sizing; nothing else.

7. **CTO review of commit ded1356 (Section 12):** Confirm whether CTO review of the 5d wiring was completed, as specified in Phase-2 closure Section 10. If not yet done, CEO must decide whether to proceed without it or gate ratification on CTO sign-off.

**Reply formats accepted:**

- `approve` — implicit acknowledgement of items 1–3, 5, 6; PM defaults tech-debt #38 to option (B); CTO review of ded1356 assumed satisfactory.
- `approve, #38: A` (or `B` or `C`) — explicit tech-debt disposition; all other items implicitly acknowledged.
- `revise <X>` — PM re-emits with specified changes; paper launch remains blocked.
- `reject` — paper launch BLOCKED indefinitely; firm reverts to backtest-only mode.

---

**File path:** `docs/decisions/CONSENSUS_2026-05-02_paper_launch_authorization.md`
