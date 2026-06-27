# Consensus on: Cost-aware candidate family — CB-decision drift (C1) and carry-sign hold (C2) — cheap feasibility screen

**Status:** ratified_with_dissent (distributed quorum: cro + head-of-quant-research, 2026-06-25; surfaced to Board, non-blocking)
**Session artifacts:** `.fintech-org/artifacts/2026-06-24-cost-aware-family-kickoff/`
**Date:** 2026-06-24

---

## Roles staffed

| Role | Rationale |
|------|-----------|
| Quant Researcher (QR) | Authored two declarative TradeIntent candidates: C1 (CB-decision post-announcement drift) and C2 (carry-sign multi-session hold). No implementation code. |
| Quant Developer (QD) | Fixed OPEN-ITEM-F001 (reversal cost under-count), reconciled F-002 label, ran CD0 cheap cost-feasibility screen on C1 and C2 using F-001-corrected code and real per-bar spreads. |
| Head of Quant Research (HoQR) | Reviewed candidate designs; issued advance-or-kill call; own regime-split gate applied. Initial verdict: approve-with-capacity-limit. On reconciliation with own pre-committed kill gate: C1 RETIRE (condition failed), C2 KILL. |
| Chief Risk Officer (CRO) | Structured risk position; sized to 0.20 with explicit NO-SPEND fallback when the regime-split kill gate is not met (which it is not). |
| Null-Hypothesis Tester (NHT) | Structural skeptic; regime-stratification tests on all 11 cells; dissent append-only and verbatim-preserved. Decision: noise-indistinguishable. Concurs NO-SPEND. |
| Principal Reviewer (PR) | Independent single-wave review; reproduced F-001 fix, no-lookahead check, and USDJPY-12h gross to digit; found 3 major and 2 minor/observation findings; 0 blocking. Approve-with-conditions. |
| PM | Synthesized this consensus; preserved dissent verbatim; recorded open items; did not make technical calls. |

---

## Acceptance criteria (from PM artifact)

- [x] F-001-FIXED-AND-VERIFIED: `scripts/compute_9pairs_readiness.py` updated so a +1→−1 flip is charged 2 round-trips. Unit assertion on synthetic [+1, −1, 0] path: 3 half-spread deductions confirmed. (QD: flip-bar cost 5.60 = 2× single 2.80; ASSERTION PASSED: True.)
- [x] F-002-RECONCILED: N_eff label reconciled — N_eff_min (k/λ_max, PR, ENB min) is the participation-ratio bets count; amendment-scaled N_eff* is a separate DSR harness statistic. Label-only clarification; no computation changed.
- [x] CANDIDATE-FAMILY-DESIGNED: C1 and C2 designed as declarative TradeIntent specs with explicit alpha-source, signal-logic, entry/exit, hold-horizon, expected fires/yr, gross-edge rationale, and machine-checkable kill thresholds.
- [x] COST-FEASIBILITY-VERDICT-PER-CANDIDATE: CD0 screen produced structured verdicts per pair × hold for C1 (9 cells) and per pair for C2 (2 cells). See tables below.
- [x] ADVANCE-OR-KILL-DECISION: HoQR issued advance-or-kill. Initial: approve-with-capacity-limit. Final (reconciled against own pre-committed kill gate): C1 RETIRE, C2 KILL.
- [x] NHT-NULL-EVALUATED: NHT evaluated all claims; dissent filed and preserved verbatim.
- [x] TRIAL-COUNTER-UNCHANGED: honest-N = 30 confirmed (trials.jsonl; last honest-n-classification 2026-06-18; all entries since carry `counts_toward_deflation_denominator: false`). No increment.
- [x] CRO-STRUCTURED-FIELDS-COMPLETE: CRO artifact contains all required structured fields.
- [x] PR-REVIEWED: PR issued approve-with-conditions; blocking-finding count = 0; F-001 fix independently spot-checked.
- [x] CONSENSUS-AUTHORED: this document.

---

## Decision

**NO-SPEND. C1 RETIRE (regime artifact). C2 KILL. Honest-N stays 30. No trial-counter increment.**

All four IC roles (HoQR, CRO, NHT, PR) independently converged that the C1 and C2 results are driven by a single-regime artifact. The Board's R1+R2 pivot was adopted and the cost-feasibility gate was the first test run — it worked exactly as designed, separating this screen from a counted trial at zero honest-N cost.

**The decisive numbers:** USDJPY-12h gross 19.94 pips (mean over n=80) collapses to 5.87 pips (t=0.62, noise-level) when 2022–2023 is dropped. The 2022–2023 FOMC hiking cycle contributes 53–54% of USDJPY 12h/18h gross from only 30% of events. Eight of nine C1 cells have raw |t|<1. No cell survives Bonferroni correction for the 11-cell selection surface (best t=2.33, Bonferroni floor t≈2.84 at p=.05/11). HoQR's own pre-committed kill gate ("survive dropping 2022-23, else retire") is FAILED: drop-regime mean 5.87 pips gross, after cost (2.30 pips RT) = 3.57 pips net — which is nominally positive, but with t=0.62 is indistinguishable from noise. The gate requires the cell to survive as a non-regime artifact; t=0.62 is the falsification.

C2 result: carry accrual = 0.018–0.021 pips per trade (<0.5% of gross). The crash-filter collapsed holds to ~5 days; carry was never exercised. AUDJPY gross −8.14 (decisive FAIL). USDJPY "PASS" (4.81 pips) is the same 2022–23 USD/JPY hiking-cycle price drift as C1, not carry — double-counting one regime. C2 as-run retired.

---

## Process narrative: R1 gate adopted → design → cheap screen → 4-reviewer regime/data-snooping verdict

**Step 1 — R1 gate adopted.** Following the 2026-06-24 9-pairs-landed NO-SPEND CONSENSUS, the Board's R1 recommendation (CD0 cost-feasibility first, before pair acquisition or rho_bar work) and R2 (change the edge input — event-conditioned / lower-turnover family) were adopted as the design constraints for this cycle. No committed backtest, no honest-N increment, no pre-registration in scope.

**Step 2 — F-001 fixed before screen.** QD fixed the reversal cost under-count in `scripts/compute_9pairs_readiness.py` (line ~230: `(pos.diff().abs() > 0).astype(float)` → `pos.diff().abs().fillna(0.0)`) and verified with an independent assertion on the synthetic path [0, +1, +1, −1, 0]: flip-bar charges 2 RT (5.60 pips = 2×2.80), total 11.20 vs prior buggy 8.40 pips. ASSERTION PASSED. OPEN-ITEM-F001 (tracked since the 2026-06-24 9-pairs CONSENSUS errata) is now **CLOSED**.

**Step 3 — QR design.** Two declarative TradeIntent candidates designed: C1 (CB-decision post-announcement drift, event-conditioned, ~8–14 fires/yr/pair, 200–600× lower turnover than F1–F6) and C2 (carry-sign overnight/multi-session hold, the lowest-turnover candidate, grounded in the only OOS-surviving FX factor). Both designed shift(1): enter the bar/day after the signal. No implementation code from QR.

**Step 4 — CD0 cheap feasibility screen.** QD ran `scripts/cost_feasibility_c1_c2.py` (F-001-corrected, real per-bar spread_median_pips, pair-native pips, EXCLUDE-NOT-IMPUTE) against C1 (9 cells: 3 pairs × 3 hold horizons) and C2 (2 pairs). Critical constraint discovered: ECB and BOE have 0 verified-official dates in `cb_decision_dates.parquet`; EURUSD and GBPUSD C1 used FED-only events (n=40 each). USDJPY used FED+BOJ (n=80). The C1 surprise filter passed 100% of events (non-binding — the max-TR bar attribution pre-selects high-volatility bars). Several cells showed positive gross vs RT cost on the surface (USDJPY-12h gross 19.94, RT cost 2.30, margin +17.6 pips).

**Step 5 — Four-reviewer regime/data-snooping verdict.** All four reviewers independently computed or reproduced the regime concentration:
- NHT ran per-year decomposition and drop-2022/23 t-tests: USDJPY-12h t 2.33→0.62 on drop; 8/9 cells raw |t|<1; mean >> median (fat-tail domination). Verdict: noise-indistinguishable.
- CRO quantified concentration: USDJPY = 97.4% of C1 total net margin; in-hike window 30% of events = 53–54% of gross; best cell pre-deflation t≈2.12 < Bonferroni floor 2.84; no risk-adjusted metric supplied. Size 0.20 authorized only for a USDJPY-only regime-split-gated cell — which fails HoQR's own gate → CRO fallback: NO-SPEND.
- HoQR read the raw JSON per-trade records and computed per-year decomposition. Applied own pre-committed kill gate: drop-2022/23 must survive. USDJPY-12h drop-regime t=0.62 fails that gate. C1 RETIRE. C2 KILL (carry untested; USDJPY "pass" duplicates C1's regime).
- PR independently reproduced USDJPY-12h gross (19.9369 — exact match to digit), confirmed no lookahead, confirmed F-001 fix correct, and found C2 cost under-charges the exit leg (OPEN-ITEM-C2COST; see PR findings below). Three major findings; 0 blocking.

---

## C1 feasibility table — CB-decision post-announcement drift

**Universe:** EURUSD (RT cost 1.10 pips), USDJPY (1.40 pips), GBPUSD (1.70 pips). Hold horizons swept: 6h, 12h, 18h. Kill threshold = 80% of RT cost per pair per spec. Data constraint: ECB and BOE have 0 verified-official dates in `cb_decision_dates.parquet`; EURUSD and GBPUSD use FED-only events.

| Pair | Hold | N_fires | Mean Gross (pips) | Mean RT Cost (pips) | Margin (pips) | Kill Threshold | Verdict | Drop-2022/23 gross (pips) | Drop-2022/23 t |
|------|------|---------|-------------------|---------------------|---------------|----------------|---------|---------------------------|----------------|
| EURUSD | 6h | 40 | 1.919 | 1.555 | +0.364 | 0.88 | PASS | ~negative | <0.5 |
| EURUSD | 12h | 40 | 1.345 | 1.518 | −0.173 | 0.88 | PASS (gross>kill but margin<0) | ~negative | <0.5 |
| EURUSD | 18h | 40 | 0.539 | 1.513 | −0.974 | 0.88 | FAIL | — | — |
| USDJPY | 6h | 80 | 6.354 | 2.461 | +3.893 | 1.12 | PASS | 0.73 | 0.10 |
| **USDJPY** | **12h** | **80** | **19.937** | **2.296** | **+17.641** | **1.12** | **PASS** | **5.87** | **0.62** |
| USDJPY | 18h | 80 | 21.116 | 2.403 | +18.714 | 1.12 | PASS | 7.00 | 0.66 |
| GBPUSD | 6h | 40 | 3.737 | 2.693 | +1.045 | 1.36 | PASS | ~negative | <0.8 |
| GBPUSD | 12h | 40 | 1.103 | 2.588 | −1.485 | 1.36 | FAIL | — | — |
| GBPUSD | 18h | 40 | 5.966 | 2.583 | +3.384 | 1.36 | PASS | ~negative | <0.8 |

**Regime concentration (USDJPY 12h, per-year means):** 2021=0.20, 2022=28.1, 2023=54.0, 2024=0.7, 2025=16.7. The 2022–2023 FOMC hiking cycle contributes 53–54% of 12h/18h gross from 30% of events. **Per HoQR's pre-committed kill gate:** dropping 2022–2023 collapses the load-bearing cell (t: 2.33→0.62). Gate FAILED. C1 RETIRE.

**Additional C1 findings:** (a) EURUSD and GBPUSD are FED-only proxies; their own central banks (ECB, BOE) contributed 0 verified-official events. (b) Surprise filter non-binding: 100% of events pass because the max-TR bar attribution pre-selects high-volatility bars (OPEN-ITEM-C1FILTER). (c) Horizon selection was post-hoc (per-pair best), adding to the multiple-comparison surface.

---

## C2 feasibility table — Carry-sign multi-session hold

**Universe:** AUDJPY (RT cost 1.60 pips), USDJPY (1.40 pips). Crash filter: 10-bar realised vol > 2× 60-bar median. Decision bar: 22:00 UTC with shift(1).

| Pair | N_holds | Mean Gross (pips) | Carry (pips) | Drift (pips) | RT Cost (pips)* | Margin (pips)* | Avg Hold | Verdict |
|------|---------|-------------------|--------------|--------------|-----------------|----------------|----------|---------|
| AUDJPY | 181 | −8.141 | 0.018 | −8.159 | 4.052 | −12.193 | 5.0 days | FAIL (gross << kill 1.28) |
| USDJPY | 185 | 4.811 | 0.021 | 4.791 | 3.004 | +1.807* | 4.8 days | PASS (gross > kill 1.12) |

*C2 RT cost charges entry leg only — exit leg dropped (OPEN-ITEM-C2COST, PR finding F-001). Corrected USDJPY margin = −0.74 pips (net negative). AUDJPY unaffected by the bug (gross already −8.14).

**Key findings:** (a) Crash filter collapsed holds to ~5 days; carry accrual = 0.018–0.021 pips (<0.5% of gross). The carry hypothesis was NOT tested. (b) AUDJPY gross −8.14: decisive FAIL — crash-period price losses dominated. (c) USDJPY "PASS": price drift only, the same 2022–23 USD/JPY hiking-cycle trend as C1 USDJPY — double-counting one regime, not independent evidence. C2 AS-RUN KILLED.

---

## § Process win

**The R1 cost-feasibility gate worked exactly as designed at zero honest-N cost.** This is the most important finding of the cycle. The gate:

1. **Separated a regime artifact from a counted trial cheaply.** Three surface-level "PASS" labels in C1 (USDJPY 12h/18h, GBPUSD 18h at 6h) were exposed as a 2-of-5-year single-regime artifact before any counted pre-registration. A naive CPCV run would have inflated the DSR denominator (honest-N penalty) for a result that was knowable cheaply — and likely produced an ambiguous full-sample t-stat that hid the regime concentration.

2. **Closed OPEN-ITEM-F001.** The reversal cost under-count tracked since the 2026-06-24 9-pairs CONSENSUS errata is now fixed and assertion-verified. Flip charges 2 RT (+2.80 pips recovered on the synthetic path). This closes the open item and hardens the cost engine for all future screens.

3. **Confirmed R2 arithmetic works in principle.** USDJPY-12h gross 19.94 pips vs RT cost 2.30 pips (margin +17.6 pips) is genuinely different from the cost-dominated F1–F6 space (max net SR −1.56). The R2 lever — higher per-trade edge via event volatility, drastically lower turnover — is the correct axis. The result was regime-concentrated, not the wrong design direction.

4. **Generated two precise, actionable open items** (OPEN-ITEM-C2COST, OPEN-ITEM-C1FILTER) and a concrete forward path (acquire ECB/BOE verified decision dates; re-screen C1 with out-of-hike net as a precondition and a binding surprise filter).

---

## § Dissent (NHT) — verbatim, append-only

*(From `nht-null-test-report.yaml`, `dissent-statement` field. Severity: informational (the NHT CONCURS with NO-SPEND and with the trial counter staying at 30). This dissent is append-only and survives any consensus revision.)*

> DISSENT (verbatim for CONSENSUS.md): This is NOT the firm's first non-negative signal
> in any sense that survives scrutiny; it is a regime artifact. The only cells with a
> raw t-stat above 2 are USDJPY 12h and 18h, and BOTH are manufactured entirely by the
> 2022-2023 USD/JPY trend (Fed hiking + BOJ YCC -> JPY collapse 115->150). Dropping just
> those two years takes USDJPY 12h from mean 19.94 pips / t=2.33 to mean 5.87 / t=0.62,
> and 18h from 21.12 / t=2.37 to 7.00 / t=0.66 — i.e. to noise. Eight of the nine C1
> cells are |t|<1 BEFORE any correction. The EURUSD/GBPUSD 'PASS' verdicts are an
> artifact of the kill threshold being set at 80% of the RT hurdle (so two cells that
> do NOT even net positive are labelled PASS), plus a per-pair best-horizon cherry-pick
> across 3 holds. The C2 'pass' is mislabelled: the carry channel contributed 0.02 pips
> (<0.5%) at 5-day holds — C2 never tested carry; it tested USD/JPY drift again, the same
> 2022-23 episode. Net: a per-trade cost screen that clears a hurdle on a mean dominated
> by a fat tail (mean >> median in every cell) and a single macro regime is data-snooping,
> not evidence of edge. I oppose treating any C1/C2 cell as VALIDATED or near-validated.
> At most this is a HYPOTHESIS-GENERATING note: 'is there post-FOMC USD/JPY drift OUTSIDE
> hiking cycles?' — which the data already answers NO (drop-regime t=0.6).

**Disposition:** NHT concurs with NO-SPEND and confirms the trial counter correctly stays at 30. The dissent is specifically against any framing of C1 USDJPY-12h as a "non-negative signal" or "edge" rather than a regime artifact.

---

## § Principal Reviewer findings — first-class

**PR decision: approve-with-conditions.** 0 blocking findings. F-001 fix independently verified on the production function. C1 no-lookahead confirmed clean. USDJPY-12h gross reproduced exactly (19.9369). Drop-2022/23 reproduced: 5.8729 pips.

| id | severity | category | location | observation | owning-role |
|----|----------|----------|----------|-------------|-------------|
| F-001 (PR report) | major | correctness | `scripts/cost_feasibility_c1_c2.py:573-575` | C2 RT cost charges ONLY the entry leg; exit/flatten leg silently dropped for all 366 C2 trades. Corrected USDJPY C2 margin: +1.807 → −0.743 (net negative). AUDJPY unaffected. Same bug class as OPEN-ITEM-F001 (under-counted RT leg), reintroduced in the C2 code path. | quant-developer |
| F-002 (PR report) | major | spec-drift | `scripts/cost_feasibility_c1_c2.py:258-279`; `quant-researcher-design.yaml:52-54` | C1 surprise filter passed 100% of events (n_fires == verified-date-count for all 3 pairs). The max-TR bar attribution pre-selects high-volatility bars, making the 1.5× filter non-binding. C1 as-run = "trade every scheduled CB date in the sign of its biggest bar" — not the surprise-conditioned strategy the spec declared. Implementation drift from a research-class gate. | quant-researcher |
| F-003 (PR report) | major | numerical | `cost_feasibility_raw.json`; `quant-developer-feasibility.yaml:179-193` | USDJPY-12h mean gross (19.94) collapses to 5.87 when 2022+2023 dropped; 2021=0.20, 2022=28.08, 2023=53.99, 2024=0.68, 2025=16.73. The headline "strongest result" is a 2-of-5-year regime artifact (~70% collapse). QD disclosed directionally; PR quantified independently. | head-of-quant-research |
| F-004 (PR report) | minor | numerical | `scripts/cost_feasibility_c1_c2.py:230-236, 397-425` | 11 cells screened; per-pair "best hold horizon" selected post-hoc (EURUSD→6h, USDJPY→12h, GBPUSD→18h). Uncontrolled horizon-selection mini multiple-comparison. Acceptable for a necessary-not-sufficient feasibility screen; must be fixed before any counted CPCV pre-registration. | head-of-quant-research |
| F-005 (PR report) | minor/observation | edge-case | `scripts/cost_feasibility_c1_c2.py:315-338, 553` | C1 stop-out exits use stop-bar CLOSE as exit price (32/80 USDJPY-12h trades are stop exits). Fill-realism approximation; not a lookahead; can bias gross either way. Acceptable for cheap screen; disclose as modeling choice. | quant-developer |

**Two new OPEN items created this cycle (tracked forward):**
- **OPEN-ITEM-C2COST** (from PR F-001): C2 exit-leg cost dropped in `scripts/cost_feasibility_c1_c2.py`. Must be fixed before ANY C2 reuse. Owner: quant-developer.
- **OPEN-ITEM-C1FILTER** (from PR F-002): C1 surprise filter is non-binding under the max-TR bar-attribution rule. Any future C1 re-screen needs real CB release times + a genuine surprise gate, OR the spec must be rewritten as an unconditional CB-date strategy. Owner: quant-researcher.

**PR coverage statement:** Reviewed: F-001 fix (production + mirror function, independently re-asserted); C1 no-lookahead trace (entry index, gross start, median-TR shift, direction source); C1 cost application (entry+exit, pair-native pips, EXCLUDE-NOT-IMPUTE) — correct; C2 cost application — found the entry-leg-only bug; USDJPY-12h gross independently reproduced (exact match 19.9369) and drop-2022/23 reproduced (5.8729); cell count + horizon selection; stop-fill realism; skip-path observability. Skipped: full re-derivation of EURUSD/GBPUSD cells (spot-checked via same code path); ML annex (no model artifact); DSR/N_eff* harness (separate harness, out of scope); C2 carry-accrual proxy economics (confirmed carry ≈ 0.02 pips, immaterial).

---

## § CRO risk position

**Decision: size-reduced (0.20). Explicit fallback: NO-SPEND.**

**Size 0.20 was authorized ONLY for a USDJPY-only, regime-split-gated cell that survives dropping 2022–2023.** That cell does NOT survive the drop (drop-regime t=0.62, noise-level). Per the CRO's explicit fallback: if the firm is unwilling to narrow to a single pre-registered USDJPY cell with a regime-split kill gate, the position is NO-SPEND — consistent with all prior cycles.

**Regime and concentration flags:**
- **Single-instrument dependence:** USDJPY = 97.4% of C1 total net margin (3,219.8 of 3,306.2 net pips). EURUSD: −0.9% share (net-negative). GBPUSD: +3.6%.
- **Single-regime dependence:** 2022-03–2023-07 FOMC hiking cycle (30% of events) = 53–54% of USDJPY 12h/18h gross. Per-event mean in-regime 35.97 vs 13.07 out (2.7×).
- **Horizon sign-instability (signature of noise):** EURUSD margin flips sign across holds (+0.364@6h → −0.173@12h); GBPUSD same (+1.045@6h → −1.485@12h). A real drift edge does not reverse sign one bar later on the same instrument.
- **Best-cell pre-deflation t≈2.12** (USDJPY 18h, net) does not clear Bonferroni floor: 11-cell surface requires |t|≈2.84 for family-wise 0.05. Not close.
- **C2 carry collapsed:** carry accrual 0.02 pips/trade; AUDJPY net −12.19/trade (decisive fail); USDJPY C2 net t=0.14 (indistinguishable from zero even without correction for the exit-leg cost drop).

**Blowup analog:** Single-regime carry/momentum collapse (JPY-carry-unwind class): an edge measured almost entirely inside one rate-hiking episode is exactly the profile that pays steadily then gives it all back in the regime turn. The August 2024 JPY carry unwind is the recent archetype. C2's AUDJPY leg (net −12.19 in-sample) is the same failure shape already realized.

**Conditions on the 0.20 (all unmet, hence NO-SPEND):**
1. Pre-register ONE cell: USDJPY, 12h OR 18h (locked before run).
2. Pre-declare deflation N including the 11-cell selection surface.
3. Regime-split kill gate: out-of-hike net must independently clear cost+hurdle. It does not (drop-regime t=0.62). → FALLBACK: NO-SPEND.
4. EXCLUDE-NOT-IMPUTE; no FED-proxy events for EUR/GBP in any counted run.
5. Keep F-001 cost-flip accounting ON; reverting is a veto condition.

---

## § HoQR reconciliation

**Initial verdict:** approve-with-capacity-limit (C1 USDJPY-only, n=80, 12h horizon pre-committed, regime-stratified hard gate).

**Reconciliation:** HoQR's own pre-committed kill gate is machine-checkable: "if post-cost net pips/trade ≤ 0 on the drop-2022/23 sub-sample for the pre-committed pair+horizon, C1 is RETIRED regardless of full-sample DSR." The drop-2022/23 result: USDJPY 12h mean gross 5.87 pips, RT cost 2.30 pips, net ~3.57 pips, t=0.62. The gate does not say "must be positive" — it says "survive dropping 2022–23" as a non-regime-artifact. A t=0.62 result is indistinguishable from zero; the condition "survive" is failed. **C1 RETIRE. Condition failed.**

HoQR's capacity-limit was built on seven hard conditions, all of which are relevant to the confirmed NO-SPEND:
- The USDJPY-only scope was the only advanceable cell; EURUSD/GBPUSD were not advanceable (within noise, negative recent years, FED-only). Confirmed.
- The horizon must be pre-committed; post-hoc sweep forbidden. Confirmed as a process control for any future cycle.
- The regime-stratified gate is the load-bearing control. Its failure is the deciding fact.
- The surprise filter must be binding or C1 must be re-labeled as unconditional. Not met (OPEN-ITEM-C1FILTER).
- ECB/BOE data acquisition is the gate to EURUSD/GBPUSD. Still the forward path.

**C2 verdict:** KILLED as-run. Carry untested (accrual 0.02 pips at 5-day holds). USDJPY "PASS" is duplicated 2022–23 C1 drift. C2 re-spec shelved (RANK-3; conditional, low priority — carry's cost-adjusted edge "did not survive verification" per the evidence layer). Re-spec conditions if ever revived: mean realised hold > 20 trading days AND carry accrual component > 50% of gross; otherwise auto-FAIL.

---

## Signatures

| Role | Verdict | Signed |
|------|---------|--------|
| quant-researcher | implement (C1, C2 declarative designs authored; honest caveats embedded) | @fintech-org-qr-2026-06-24 |
| quant-developer | implemented-and-verified (F-001 fixed + asserted; F-002 label reconciled; screen executed) | @fintech-org-qd-2026-06-24 |
| head-of-quant-research | C1 RETIRE (own kill gate failed: drop-2022/23 t=0.62); C2 KILL (carry untested, duplicates C1 drift) | @fintech-org-hoqr-2026-06-24 |
| cro | size-reduced (0.20) → explicit fallback NO-SPEND (regime-split gate not met; 97.4% USDJPY concentration; best-cell t<Bonferroni floor) | @fintech-org-cro-2026-06-24 |
| null-hypothesis-tester | noise-indistinguishable (8/9 cells |t|<1; drop-2022/23 t=0.62; regime artifact; C2 carry untested); CONCURS NO-SPEND | @fintech-org-nht-2026-06-24 |
| principal-reviewer | approve-with-conditions (F-001 fix correct + no-lookahead clean + USDJPY-12h reproduced exactly; 3 major findings, 0 blocking; 2 new open items) | @fintech-org-pr-2026-06-24 |
| pm | synthesis-complete (dissent preserved verbatim; PR findings first-class; open items tracked; no technical calls) | @fintech-org-pm-2026-06-24 |

---

## Knowledge gaps surfaced

The following are role-level research and data-measurement limitations surfaced in session artifacts. They are NOT installable skill gaps — no new skill installation or research methodology is needed to address them. **Installable-skill-gap count N = 0.** No new entries appended to `.fintech-org/skill-gaps.jsonl` this session.

| Gap | Source | Resolution path |
|-----|--------|----------------|
| No tick-level / consensus CB-expectations data. C1 "surprise" is proxied from price (announcement-bar return/range). A true expectations-surprise filter (e.g. consensus-vs-actual differential) is not in the store and cannot be synthesized from price alone. | QR, QD, NHT | Requires sourcing a CB-expectations/consensus data feed. Not an installable skill gap — a data acquisition gap. |
| ECB and BOE have 0 verified-official dates in `cb_decision_dates.parquet`. EURUSD and GBPUSD C1 are FED-only proxies; the genuine EUR/GBP central bank catalyst is unmeasured. The forward re-screen path requires acquiring these dates. | QD, NHT, HoQR | Data acquisition: verified ECB and BOE decision date series with official timestamps. Not a skill gap. |
| No realised broker-swap ledger for C2. Carry accrual is a 50%-haircut headline-differential proxy. Moot as-run (holds too short to accrue carry). A re-spec would need a faithful overnight-swap rate series. | QR, QD | Data acquisition: broker overnight swap ledger or a trusted per-pair swap rate series. Not a skill gap. |
| No intraday CB release timestamps in the current data store. The max-TR bar proxy is the QD's best available substitute; it makes the C1 surprise filter non-binding (OPEN-ITEM-C1FILTER). | QD, PR, NHT | Acquire exact UTC release timestamps per CB decision (e.g. from official CB calendars). Not a skill gap. |

---

## Open items requiring Board acknowledgment

**(a) OPEN-ITEM-C2COST (new, this cycle; high priority before any C2 reuse):** C2 exit-leg cost dropped in `scripts/cost_feasibility_c1_c2.py`. Same bug class as F-001. Must be fixed and re-asserted before any C2 reuse. Owner: quant-developer. The USDJPY C2 "net positive" claim (+1.807 pips) is false; corrected net is −0.74 pips. Board should acknowledge that the C2 USDJPY "PASS" verdict (keyed to gross vs kill-threshold) is mechanically correct but the net-positive narrative is wrong.

**(b) OPEN-ITEM-C1FILTER (new, this cycle; required before any C1 re-registration):** C1 surprise filter is non-binding under the max-TR bar-attribution rule. Any future C1 re-screen must either (i) acquire exact CB release timestamps so the filter can genuinely discriminate, or (ii) drop the selectivity claim and label C1 as an unconditional post-CB-date drift bet. Owner: quant-researcher. Board should acknowledge that C1 as-run is not the surprise-conditioned strategy on the label.

**(c) Forward ECB/BOE data acquisition (recommended; RANK-2 per HoQR):** Acquiring verified-official ECB and BOE decision dates (currently 0 in `cb_decision_dates.parquet`) is the gate to re-screening EURUSD and GBPUSD C1 with their own central banks. Mirroring the standing DATASET-WALL finding. Board should decide: authorize ECB/BOE date acquisition? Or defer until C1 USDJPY is re-screened with out-of-hike net as a precondition?

**(d) Whether to fund the C1 re-screen (forward path, not executed):** HoQR recommends re-screening C1 with (i) out-of-hike net as a precondition (must show the edge exists outside 2022–23), (ii) a binding surprise filter (real release times required), and (iii) verified ECB/BOE dates for EURUSD/GBPUSD. This is a design-and-data-acquisition task, not a counted trial. Board must decide: authorize the re-screen investment? Or treat C1/C2 as retired and redirect to a new candidate generation cycle?

---

## Prior decisions NOT made / carry-forward items

- **C2 carry re-spec:** Shelved (RANK-3, conditional). Can only be revived with (a) mean hold > 20 trading days, (b) carry accrual > 50% of gross, and (c) a faithful broker-swap series. Low priority — carry's cost-adjusted edge "did not survive verification" per the evidence layer.
- **H1 un-freeze:** FORBIDDEN. Gate B (CD0 net SR ≥ 1.76) fails categorically. No change.
- **GBPJPY acquisition:** Remains on hold per HoQR R3 ratified in the 9-pairs CONSENSUS.
- **F1–F6 canonical families:** Remain retired-as-saturated (78 total evaluations, max net SR −1.56 across two independent cycles).
- **honest-N:** Remains 30. No increment this cycle.

---

*This CONSENSUS.md is the audit-trail source-of-truth for the 2026-06-24 cost-aware-family-kickoff wave. Append-only per protocol. No section may be softened, reordered, or omitted in future revisions — only new sections may be appended.*

---

## § Errata — orchestrator post-ratification correction (2026-06-25, prompted by quick-critic faithfulness pass)

A critic correctly flagged that the § HoQR reconciliation above conflated HoQR's *literal* pre-committed kill gate with a stricter criterion. **The decision (NO-SPEND / C1 RETIRE / C2 KILL / honest-N=30) is unchanged.** Appended, not rewritten, per append-only discipline.

1. **The literal gate was NOT triggered; HoQR formally AMENDED it (owning-role call).** The signed gate text (`head-of-quant-research.yaml:16`) was `net ≤ 0 on the drop-2022-23 sub-sample → retire`. Applied literally to the drop-2022-23 sub-sample MEAN for USDJPY-12h, net = 5.87 − 2.30 = **+3.57 (positive)**, so the literal `≤ 0` condition is **not met** — read literally, the gate would ADVANCE. The +3.57 is positive only because 2025 (16.7 pips) sits in the post-drop remainder; the out-of-hike years 2021/2024 (0.20/0.68 gross) are net-negative and the drop-period t=0.62. On routing this discrepancy back to HoQR (the gate's owner), HoQR chose to **AMEND** the under-specified gate and confirmed RETIRE under the amended form. **Amended gate (verbatim, supersedes the original C1-REGIME-KILL):**

   > **C1-REGIME-KILL (HARD, pre-committed; amended 2026-06-24):** Re-estimate post-cost net-pips/trade on the sub-sample EXCLUDING 2022-01-01..2023-12-31 for the pre-committed pair+horizon. C1 RETIRES unless ALL THREE hold: (1) drop-2022-23 post-cost mean net-pips/trade > 0; (2) the drop-2022-23 gross-pips/trade mean is statistically distinguishable from zero at t ≥ 2.00 (one-sample, on the per-event array); (3) the result is NOT dominated by a single residual calendar year — specifically, removing the single best post-drop year individually must leave drop-2022-23 mean net > 0. Failing ANY of the three retires C1.

   Applied to USDJPY-12h: (1) +3.57 > 0 PASS; (2) t=0.62 < 2.00 **FAIL**; (3) removing 2025 leaves 2021/2024 net-NEGATIVE **FAIL**. Fails 2 of 3 → **RETIRE**. This is HoQR's deliberate amendment (its `strategy-kill-decisions` domain); the orchestrator surfaced the discrepancy but did not make the call.

2. **CRO position is conditional, not an automatic numeric fallback.** CRO authorized `size_multiplier 0.20` for ONE pre-registered USDJPY-only cell *gated by a regime-split kill gate*, and stated NO-SPEND **if the firm is unwilling/unable to narrow to such a qualifying cell.** The accurate chain: HoQR's amended regime gate RETIRES the only candidate cell (C1-USDJPY-12h fails conditions 2 & 3) → no qualifying regime-gated cell exists for the 0.20 to apply to → CRO's NO-SPEND condition is satisfied. (Earlier wording implied the NO-SPEND was triggered automatically by the gate numerics; it is a consequence of the cell failing the regime gate CRO required.)

3. **Why NO-SPEND is robust regardless.** Advancing a counted CPCV (honest-N → 31) on a drop-regime mean with t=0.62 — indistinguishable from zero, and positive only via one residual year — is precisely the honest-N-burning-on-a-likely-null that the firm's discipline exists to prevent. Under either the literal gate's *intent* or the amended gate's *letter*, the substantive answer is NO-SPEND.
