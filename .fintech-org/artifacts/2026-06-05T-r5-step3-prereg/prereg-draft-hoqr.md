# R5 PRE-REGISTRATION — Carry-Universe Terminal Kill Test

**Document status:** DRAFT (HoQR-owned sections complete; mathematician sections marked as merge placeholders). Becomes BINDING and FROZEN only upon consensus ratification + CEO sign-off + freeze-receipt (SHA-256 + git commit hash) per criterion FREEZE-mechanics. No bootstrap draw (STEP 4) may execute before the freeze-receipt is committed.

**Track:** r5-step3-prereg-2026-06-05 / Phase 1 / Task 1.0
**Trial ID:** 576746aa (the R5 family counts as ONE trial; STEP 4 reuses it — no counter increment)
**Authoritative scope input:** docs/decisions/CONSENSUS_2026-06-02_r5_scope.md
**Preserved dissent (append-only, firm rule 6):** .agent-accountability/dissents/r5-scope-2026-06-02:phase1:task1.0:null-hypothesis-tester.yaml

---

## 1. Preamble & Scope (HoQR)

### 1.1 What this pre-registration IS

This document is the **terminal, honest KILL TEST** for the firm's carry program. The firm currently has **ZERO validated out-of-sample alpha**; the retirement / kill-criterion has **TRIPPED** (the Bet#1 retirement closed the last open candidate, and the 2026-05-31 honest review found no surviving validated edge). R5 is the single, pre-committed, one-shot statistical test that converts that posture into a defensible decision: either the carry family produces a class-level signal that survives a Hansen-SPA / White-Reality-Check max-statistic test against a zero benchmark on confirmed-real data, or it does not — and if it does not, the firm winds the program down.

This pre-registration freezes — before any bootstrap draw — every degree of freedom that could otherwise be exploited after seeing results: the universe (Section 2), the evaluation window and snooping treatment (Section 3), the null and statistic (mathematician sections), the decision threshold (Section 4), and the action taken under every possible outcome (Section 5). Freezing these in advance is what makes the resulting p-value interpretable.

### 1.2 What this pre-registration is NOT

This is **not a validation vehicle and not a rescue attempt.** It is not an opportunity to find a surviving cell and re-launch the program on it. It is not exploratory research. The test is acknowledged to be **underpowered** (class-level power ~20–35% against a true ~0.30 annualized Sharpe under FWER over correlated cells — see mathematician's Power section). The most probable honest outcome is a **non-rejection**, and the firm has pre-committed (Section 5) that a non-rejection — powered OR underpowered — maps to **WIND-DOWN**, never to "inconclusive, keep spending." There is no "rescue" branch anywhere in the decision tree. A single isolated significant cell does NOT license CONTINUE on the family; that artifact is precisely what R5 exists to catch.

### 1.3 The binding nature of the freeze

Once this document is ratified and the freeze-receipt (SHA-256 of this file + git commit hash of the pinned code state: `carry_universe_matrix.py` and `reality_check.py` after the permitted N1 fix) is committed, the specification is immutable. **Any post-freeze change to the universe, window, statistic, K, threshold, or code — other than the N1 hardening fix, which must land BEFORE freeze — VOIDS this pre-registration** and forces a re-freeze (and, if a draw has already run, retirement of the contaminated result). STEP 4 is a one-shot run: the test is computed once against the frozen spec; there is no "re-run with a tweak" path that preserves the pre-registration.

---

## 2. Universe (HoQR) — criterion PRE-REG-universe

### 2.1 Explicit 6×6 enumeration (all 36 cells)

The frozen universe is the full Cartesian product of **6 carry variants × 6 JPY crosses = 36 cells**. No cell is privileged; no cell is silently dropped.

| | USDJPY | EURJPY | GBPJPY | AUDJPY | CADJPY | NZDJPY |
|---|---|---|---|---|---|---|
| **carry** | carry·USDJPY | carry·EURJPY | carry·GBPJPY | carry·AUDJPY | carry·CADJPY | carry·NZDJPY |
| **carry_fred** | carry_fred·USDJPY | carry_fred·EURJPY | carry_fred·GBPJPY | carry_fred·AUDJPY | carry_fred·CADJPY | carry_fred·NZDJPY |
| **fred_carry_stripped** | fred_carry_stripped·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |
| **vol_target_carry** | vol_target_carry·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |
| **vol_target_carry_no_vol_scaling** | …·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |
| **carry_momentum** | carry_momentum·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |

**Variants (exhaustive carry family):** `{carry, carry_fred, fred_carry_stripped, vol_target_carry, vol_target_carry_no_vol_scaling, carry_momentum}`
**Pairs (frozen at 6 JPY crosses):** `{USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY}`

USDJPY is **included** because its canonical input `data/processed/USDJPY_daily.parquet` is the REAL series (range 75.82–161.71, verified in the scope consensus). The corrupted `processed_synthetic_phase0/` USDJPY (5.03–7.75) is quarantined and prohibited from this test; if R5 is ever pointed at the synthetic directory the test is void. Non-JPY pairs are out of scope: the carry program never claimed them.

### 2.2 Named constraint: NO-SILENT-EXCLUSION

> **Constraint NO-SILENT-EXCLUSION.** Every one of the 36 cells either (a) appears in the joint return matrix that feeds the test, or (b) is dropped with a **structured, logged reason** (the `carry_matrix.cell_dropped` decision-trace event with `reason`, `exc_type`, `category` fields) recorded in the STEP 4 results and reconciled against this pre-reg. A silent drop — a cell that vanishes with no logged reason — **voids the FWER guarantee** and therefore voids the test. Code errors (KeyError/AttributeError/TypeError/etc.) RAISE loudly and fail the run closed; only genuine, confirmable data-insufficiency may drop a cell, and only with a structured reason. The matrix builder enforces this fail-closed behavior by design (`carry_universe_matrix.py` module docstring).

The expected build is **all 36 cells, 0 dropped** (per the STEP 2b commit). Any deviation from 36 must be explained cell-by-cell in the STEP 4 build report before the p-value is read.

### 2.3 Honest statement: these are NOT 36 independent hypotheses

The six variants are **re-parameterizations and ablations of ONE underlying idea — the cross-currency rate differential.** They share the same signal feed (`rate_differentials.parquet`), and the six JPY crosses share heavily overlapping price-return dynamics. The **effective number of independent tests is ≈ 1–2** (HoQR estimate; NHT's wider 2–4 is preserved in the dissent). This is the reason the test uses joint same-block resampling under a single pooled FWER family rather than 36 separate tests with Bonferroni — and it is why a non-rejection here is not surprising and is not, by itself, proof of no edge (it is, however, pre-committed grounds for wind-down; see Sections 3 and 5).

---

## 3. Evaluation Window & Snooping Treatment (HoQR proposal; mathematician co-signs) — criterion PRE-REG-oos-window

### 3.1 The honest snooping posture

These six variants are the firm's **longest-studied strategies**, carrying a large prior trial history across the full 2010–2026 sample. **That selection is sunk and uncontrollable.** A prospective Reality-Check on the same 2010–2026 data does NOT retroactively control the looks already spent; it inherits the snooping and yields an optimistically biased p (NHT dissent §3). "We used all available data with no haircut" is explicitly **not acceptable** under criterion PRE-REG-oos-window, and we do not propose it.

### 3.2 Proposed treatment — primary path and fallback

There are two principled ways to obtain a face-valid p in the presence of sunk snooping. We propose the following, in priority order:

**PRIMARY (preferred): deflated-Sharpe-style haircut applied to the SPA decision.** Because the rate-differential signal (`rate_differentials.parquet`) is **forward-filled MONTHLY** (sourced from monthly central-bank CSVs), the daily series carries effective-N closer to monthly (~180–190 effective months over the sample) than to the ~4245 daily bars — so a forward hold-out carved purely from daily bars buys very little genuinely-new information per unit of calendar time, and a clean post-development forward window of meaningful length does not exist on this dataset. The honest, achievable control is therefore a **deflation haircut**: the multiple-testing / prior-trial burden is charged against the significance bar before CONTINUE can be declared. **The exact haircut formula, its inputs (number of effective independent trials, prior trial count, variance-of-Sharpe term), and its integration with the SPA p-value are OWNED BY THE MATHEMATICIAN** and specified in the Power-and-Limitations / normalization sections; HoQR co-signs that *a* deflation is applied and is the gate, not "raw p < 0.05 alone." The studentized SPA statistic already recenters and scales poor cells (mathematician's statistic section); the deflation sits on top as the snooping charge.

**FALLBACK (if a defensible forward hold-out is later shown to exist):** designate a genuine post-development hold-out segment at the tail of the common index and evaluate SPA on the hold-out only, with the in-sample segment used for nothing but block-length estimation. This is recorded as the fallback because, given the monthly-effective-N reality above, we do not expect it to be powered enough to be the primary; if adopted it REPLACES the haircut (you do not double-charge a genuine hold-out).

We propose **PRIMARY (deflation haircut)** as the operative path. The mathematician co-signs the method; HoQR owns the *decision that snooping must be charged* and that a bare p < 0.05 is necessary-but-not-sufficient.

### 3.3 Window as a RULE over the common joint index

The evaluation window is defined as a **rule**, not yet as literal dates (literal dates are filled at assembly from the QD verified build report):

> **WINDOW RULE.** The test evaluates the **full common joint index** — the inner-join (intersection) of all 36 cells' valid daily return dates, post-entry-delay (entry_delay_bars=1, the sacred no-lookahead invariant), net-of-cost, after the alignment that produces a rectangular NaN-free matrix (`carry_universe_matrix.py` alignment design). The SPA/White-RC max-statistic is computed over this entire common index. The snooping charge of Section 3.2 (deflation) is applied to the resulting decision; if the FALLBACK hold-out path is adopted instead, the window is the tail hold-out segment only.

> **[EXACT DATES FROM QD BUILD REPORT]** — start date, end date, and bar count `T` of the resolved common joint index (and, if the FALLBACK path is adopted, the hold-out split date) are inserted here at assembly from the quant-developer's verified STEP 2/STEP 4 build report. They are not invented in this draft.

Both HoQR and the mathematician must sign this section before freeze.

---

## 4. Decision Rules (HoQR) — criterion PRE-REG-decision-threshold

The decision is a **single binary firm decision: CONTINUE or WIND-DOWN.** It is read off the frozen-family SPA p-value (with the White-RC p-value as a conservative cross-check; both are reported), after the Section 3 snooping charge. α = 0.05 (mathematician's error-control section).

- **CONTINUE path — `SPA p < 0.05` at the CLASS level (post-deflation), confirmed by White-RC direction.**
  CONTINUE is **NECESSARY-BUT-NOT-SUFFICIENT.** A class-level rejection means the family is distinguishable from chance against a zero benchmark — it does NOT validate any individual cell, and it does NOT re-launch the program. The single named confirmatory next step is: **author a NEW, separate pre-registration for a confirmatory-only test of the specific surviving structure**, with no free exploration, no re-parameterization, no new variant or pair search. Selecting a cell post-hoc and trading it invalidates the p at any magnitude.

- **WIND-DOWN path — `SPA p >= 0.05` at the family level.**
  The carry family is statistically indistinguishable from chance at the class level. Combined with the already-completed Bet#1 retirement and the zero-validated-alpha posture, this makes the no-edge conclusion **structural**. Action: formal wind-down to monitoring (Section 5). This branch fires regardless of whether power was adequate or low — the underpowered-non-rejection caveat does NOT open a third door (Section 5, outcome 3).

- **AMBIGUOUS path — partial / anomalous result** (e.g., the family p straddles the boundary within MC-SE; or only an isolated subset shows signal; or a normalization-driven distortion such as the carry_momentum near-null column — see N2 — produces a result that is not a clean class-level rejection).
  AMBIGUOUS maps to **a confirmatory-only pre-reg gate, NEVER to CONTINUE on the original family.** No capacity is unfrozen for the original 36-cell family on an ambiguous result. The only permitted forward action is a fresh, separately-pre-registered confirmatory test of the specific anomaly, treated as a brand-new hypothesis with its own freeze.

There is no decision branch in this document that results in "keep researching the carry family as-is." CONTINUE only ever buys a *new confirmatory pre-reg*; it never buys free exploration.

---

## 5. Wind-Down Action Map (HoQR) — criterion PRE-REG-winddown-map

Every possible test outcome maps to a **named firm action**, pre-committed here before any draw. "Inconclusive, keep spending" is not a valid action for any outcome.

| # | Outcome | Condition | Named firm action |
|---|---|---|---|
| **1** | **REJECT (class level)** | SPA p < 0.05 (post-deflation), White-RC concordant | **CONFIRMATORY pre-reg only.** Author a new, separate pre-registration for a confirmatory-only test of the surviving structure. NO free exploration, NO re-parameterization, NO new variant/pair search, NO capital. The original 36-cell family is NOT re-opened for research; only the named confirmatory hypothesis proceeds. |
| **2** | **FAIL TO REJECT, powered** | SPA p ≥ 0.05 AND power adequate | **WIND-DOWN.** Zero validated alpha is confirmed structural at adequate power. Execute the wind-down-to-monitoring procedure (§5.1). |
| **3** | **FAIL TO REJECT, underpowered** | SPA p ≥ 0.05 AND power ~20–35% (the expected scenario) | **WIND-DOWN (BINDING).** The low power makes this non-rejection UNINFORMATIVE *as evidence of no-edge* — but it does NOT change the firm action. Per the ratified scope and the NHT dissent, an underpowered non-rejection reads as "no DISTINGUISHABLE class-level alpha at the achievable power" → **WIND-DOWN.** This is explicitly NOT "inconclusive, keep spending." There is no third outcome that licenses continued spend on the carry family. |
| **4** | **ANOMALOUS** | Partial subset survives; boundary-straddle within MC-SE; or normalization-driven distortion (e.g., carry_momentum near-null column post-N2 decision) | **AMBIGUOUS → confirmatory pre-reg gate ONLY.** Does NOT license CONTINUE on the original family. The specific anomaly may be carried into a fresh, separately-pre-registered confirmatory test with its own freeze; the 36-cell family research is not re-opened. No capital. |
| **5** | **TECHNICAL FAILURE** | Code error, data-integrity fault, or unexplained cell drop detected at run time | **HALT, root-cause, re-freeze, re-run.** No p-value is read or reported. The trial counter is NOT incremented (the R5 family remains ONE trial, id 576746aa). After root-cause and a new freeze-receipt, the one-shot run is repeated. A masked bug presented as a benign cell drop is itself a NO-SILENT-EXCLUSION violation that voids the run. |

### 5.1 What "wind-down to monitoring" concretely means for this firm

Outcomes 2 and 3 both trigger this state. Concretely:

- **No new research spend on the carry program.** No new variants, no parameter searches, no re-tests of the 36-cell family on this dataset.
- **Archive the carry strategy registry** entries as RETIRED/FALSIFIED, with a pointer to this pre-reg, the freeze-receipt, and the STEP 4 result (the falsification archive — a curated record of what was killed and why).
- **Observe-only state.** Any residual carry exposure is monitoring-only (no capital at risk; the firm is backtest/paper-only regardless). The decision-trace and result artifacts are retained for the record.
- **Redirect remaining capacity** to the contamination audit and to genuinely-new alpha hypotheses (which require their own fresh pre-registration; the zero-validated-alpha posture means nothing is unfrozen by default).
- **The wind-down recommendation is surfaced to the CEO for ratification** — wind-down is irreversible firm policy and is not in the autonomous quorum's authority.

---

## 6. Retirement Criteria (HoQR) — machine-checkable

These conditions are tied directly to the decision rules (Section 4) and the wind-down map (Section 5). They are the machine-checkable triggers a downstream gate can evaluate against the STEP 4 result artifact:

- `R5.spa_p >= 0.05` → **RETIRE the carry program** (wind-down to monitoring; outcomes 2 & 3). This fires whether or not power was adequate; power does NOT gate this trigger.
- `R5.spa_p < 0.05 AND R5.white_rc_p >= 0.05 (discordant)` → **AMBIGUOUS**, do NOT CONTINUE on the family; confirmatory pre-reg gate only (outcome 4).
- `R5.cells_built != 36 AND any dropped cell has reason == null/empty` → **VOID the run** (NO-SILENT-EXCLUSION breach); HALT, re-freeze (outcome 5).
- `R5.code_error == true OR R5.data_integrity_fault == true` → **HALT**, root-cause, re-freeze, re-run; trial counter NOT incremented (outcome 5).
- `freeze_receipt.sha256 != sha256(this_file) OR freeze_receipt.code_commit != pinned_commit` → **VOID** — the run executed against an unfrozen or drifted spec; result is not face-valid.
- `R5.spa_p < 0.05 AND R5.white_rc_p < 0.05 (concordant, post-deflation)` → **CONTINUE** is permitted, but ONLY as authorization to author a confirmatory-only pre-reg (outcome 1) — never as authorization to trade or to re-open the family.

A non-rejection at any power level is a RETIRE trigger. There is no machine-checkable path from this test to "continue spending on the carry family as-is."

---

# SECTIONS OWNED BY THE MATHEMATICIAN (merged at assembly)

## M1. Null Hypothesis
`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
(Frozen H0, stated verbatim: max over cells k of expected net-of-cost, post-entry-delay, benchmark-relative — benchmark = ZERO — per-bar performance d_k ≤ 0. Criterion PRE-REG-null.)

## M2. Test Statistic and Method
`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
(Hansen SPA primary p-value + White Reality Check p-value off the SAME stationary-bootstrap draws; statistic T_k = sqrt(n)·mean(f_k)/omega_hat_k; family = max_k T_k; joint same-block resampling across all 36 cells; names the reality_check.py function signatures. Criterion PRE-REG-statistic.)

## M3. Per-Cell Normalization (N2 DECISION — mathematician owns the decision; HoQR references it)
`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
(Explicit statement of whether studentized T_k normalization is applied uniformly, or raw-return SPA is used with the carry_momentum near-null-column distortion accepted and documented. The carry_momentum variant's return std is ~1000x smaller than the other five — the correct consequence of `risk_per_trade: 0.007` in `config/carry_momentum_portfolio.yaml` line 58 — which makes it a near-null SPA column under raw returns. The mathematician makes and signs this choice; HoQR's Section 4 AMBIGUOUS branch and Section 5 outcome 4 reference its downstream effect. Criterion N2.)

## M4. Block Length
`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
(Politis-White (2004) automatic data-driven rule, per-variant, guard L ≥ 1, max-across-cells for the joint draw; references reality_check.py. Criterion PRE-REG-block-length.)

## M5. Bootstrap Parameters (K / MC-SE)
`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
(K ≥ 2000, target 5000–10000; MC-SE = sqrt(p(1-p)/K) = 0.0049 at p=0.05, K=2000; K=200 explicitly ruled out. Criterion PRE-REG-K-MCSE.)

## M6. Error Control (alpha / FWER)
`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
(α = 0.05; FWER strong control via max-statistic over the single pooled family of 36 cells; rationale for FWER over FDR — the firm decision is one binary CONTINUE/WIND-DOWN = P(any false CONTINUE) = FWER. Criterion PRE-REG-alpha-FWER.)

## M7. Power and Limitations
`[SECTION OWNED BY MATHEMATICIAN + NHT — merged at assembly]`
(Class-level power ~20–35% at the ~0.30 annualized Sharpe under FWER over correlated cells; source of the estimate; the binding statement that underpowered non-rejection → WIND-DOWN and does NOT license a third "inconclusive" outcome. The deflation-haircut formula and inputs referenced by HoQR Section 3.2 PRIMARY path live here. Criterion PRE-REG-power.)

---

# FREEZE BLOCK (filled at assembly by quant-developer — criterion FREEZE-mechanics)

- **Pre-reg SHA-256:** `[FROM FREEZE-RECEIPT]`
- **Pinned code commit (carry_universe_matrix.py + reality_check.py, post-N1):** `[FROM FREEZE-RECEIPT]`
- **Freeze timestamp:** `[FROM FREEZE-RECEIPT]`
- **Signatures:** HoQR · mathematician · quant-developer (code-pin) · NHT (audit) · CEO (ratification) — collected by PM in CONSENSUS_2026-06-05_r5_step3_prereg.md.
