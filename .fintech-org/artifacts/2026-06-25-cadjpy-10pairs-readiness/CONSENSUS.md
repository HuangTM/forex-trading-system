# Consensus on: CADJPY DQ admission + 10-pair universe readiness reassessment

**Status:** ratified_with_dissent (distributed quorum: cro + head-of-quant-research, 2026-06-25; surfaced to Board, non-blocking)
**Session artifacts:** `.fintech-org/artifacts/2026-06-25-cadjpy-10pairs-readiness/`
**Date:** 2026-06-25

---

## Roles staffed

| Role | Rationale |
|------|-----------|
| Quant Developer (QD) | Added CADJPY per-pair DQ config entry (AUDJPY-tier); ran CADJPY DQ gate; recomputed rho_bar_eff for ALL-10 and JPY-cross subsets from raw parquet; ran CADJPY CD0 screen across all 6 canonical families with real per-bar spreads under EXCLUDE-NOT-IMPUTE. |
| Head of Quant Research (HoQR) | Issued the posture assessment (C4): HOLD / NO-SPEND, binding constraint = data capability, posture unchanged. Ratified the TREADMILL-STOP criterion as a new machine-checkable retirement condition. |
| Chief Risk Officer (CRO) | Structured risk position; veto / size 0.0; characterized the rho_bar improvement as dilution arithmetic; identified JPY-cross-3 concentration (rho 0.7479) and the LTCM-analog blowup risk from sizing negative-edge correlated sleeves. |
| Null-Hypothesis Tester (NHT) | Structural skeptic; tested all three claims (i–iii); dissent filed and preserved verbatim; non-blocking, concurs NO-SPEND but dissents on any "progress" framing of the rho_bar improvement. |
| Principal Reviewer (PR) | Independent cold review; reproduced all four subsets' rho_bar_eff and all six CADJPY CD0 net SRs exactly; ran same-window control to isolate breadth effect; 0 blocking findings; F-001 as forward condition. |
| PM | Synthesized this consensus; preserved NHT dissent verbatim; tracked forward conditions; made no technical calls. |

---

## Acceptance criteria (from PM artifact)

- [x] **C1 (DQ CADJPY ADMIT):** CADJPY DQ gate run with newly-added per-pair config entry (AUDJPY-tier thresholds). Verdict: ADMIT. All six sub-metrics pass. See table below.
- [x] **C2 (rho_bar_eff recompute):** rho_bar_eff and N_eff reported for ALL-10 and JPY-cross subsets; delta vs ALL-9 stated; gate direction confirmed. PR independently reproduced all headline numbers exact.
- [x] **C3 (CADJPY CD0 sanity):** CADJPY × 6 canonical families, real per-bar spreads, EXCLUDE-NOT-IMPUTE. All 6 FAIL. Best net SR = −2.1914 (F5). PR reproduced all six net SRs to 4 decimal places.
- [x] **C4 (posture assessment — primary deliverable):** Explicit NO: CADJPY does NOT change the ratified NO-SPEND / existing-data-EXHAUSTED posture. See § Strategic posture.
- [x] **C5 (NHT null tests):** All three claims (i/ii/iii) tested; nulls accepted or rejected with deciding numbers. Dissent preserved verbatim.
- [x] **C6 (PR independent verification):** rho_bar_eff ALL-10 reproduced exact; all six CADJPY CD0 net SRs reproduced exact; same-window control stress-test confirms breadth effect genuine. 0 blocking findings.
- [x] **C7 (descriptive log):** `.fintech-org/trials.jsonl` entry appended with `counts_toward_deflation_denominator: false` and `event: descriptive-screen`. Trial counter does NOT increment. honest-N remains 30.

---

## Decision

**CADJPY: DQ ADMIT (to data universe). NO-SPEND. Strategic posture HELD. Honest-N stays 30. No trial-counter increment.**

All four IC roles (HoQR, CRO, NHT, PR) independently converged: CADJPY is a clean data asset (DQ ADMIT, 99.23% bar coverage, 100% spread coverage, 1.2-pip median) and the rho_bar_eff improvement (0.4090 → 0.3716) is arithmetically genuine — but it is IMMATERIAL to a spend decision. The binding constraint is the NO-EDGE wall (net-of-cost SR < 0 across all 84 pair × family combos), not the concentration wall. CADJPY's own CD0 is the WORST in the screen (best net SR −2.19 vs prior best −1.56). Adding breadth to a uniformly-negative edge set improves a non-binding gate and contributes zero toward a positive one.

---

## § CADJPY DQ gate — ADMIT

Config entry added to `config/data_quality_gates_1h.yaml` (spread_median_floor=0.2, ceiling=5.0, p90_ceiling=15.0; AUDJPY-tier). Gate run: 5yr trade window.

| Metric | Value | Gate | Result |
|--------|-------|------|--------|
| n_rows | 31,032 | — | — |
| UTC range | 2021-01-03 22:00 → 2025-12-31 21:00 UTC | — | — |
| bar_coverage_pct | 99.23% | ≥ 85% | PASS |
| measured_spread_coverage_pct | 100.0% | ≥ 90% | PASS |
| max_contiguous_gap_h | 24 h | ≤ 24 (inclusive) | PASS |
| spread_median_pips | 1.200 | ≤ 5.0 | PASS |
| spread_p90_pips | 1.500 | ≤ 15.0 | PASS |
| spread_max_pips | 36.2 | — (spike, not structural) | — |
| frac_bars_above_5pips | 3.99% | — (not a gate criterion) | — |
| n_zero_spread_bars | 0 | — (SC-3 clean) | — |
| n_missing_spread_bars | 0 | — | — |

**VERDICT: ADMIT.** SC-4 cross-pair check: ADMIT. The max_contiguous_gap_h = 24 sits at the inclusive gate ceiling. QD and PR both confirmed this is a coverage gap (100% spread coverage, 0 zero-spread bars), not a quality gap — consistent with a national-holiday one-day closure (same pattern as AUDJPY in prior cycle). Note: zero gate margin on this one criterion — a single additional missing in-session hour would flip to EXCLUDE.

---

## § rho_bar_eff — improved but immaterial

Formula: rho_bar_eff = (λmax − 1) / (k − 1). Proxy: aligned raw log-returns, Pearson correlation (eigenvalue/sign-blind per 2026-06-19 amendment). N_eff = min(k/λmax, k²/Σλ²ᵢ, exp(Shannon entropy)).

| Subset | k | n_obs | λmax | PC1 | rho_bar_eff | Gate (≤0.41) | N_eff_min |
|--------|---|-------|------|-----|-------------|--------------|-----------|
| ALL-10 | 10 | 29,660 | 4.3446 | 43.5% | **0.3716** | **PASS** | 2.302 |
| ALL-9 (reference) | 9 | 29,805 | 4.2723 | 47.5% | 0.4090 | PASS | 2.107 |
| JPY-cross-3 | 3 | 30,743 | 2.4958 | 83.2% | 0.7479 | FAIL | 1.202 |
| CROSSES-4 | 4 | 30,588 | 2.4965 | 62.4% | 0.4988 | FAIL | 1.602 |

**ALL-9 confirmation:** QD recomputed 0.4090; matches prior reference exactly — confirmed.

**Delta ALL-10 vs ALL-9:** −0.0374 (decreases = better). Gate margin: 0.038 vs the prior razor-thin 0.001 — a genuine 38× improvement in nominal margin.

**PR same-window stress-test:** PR recomputed ALL-9 on the IDENTICAL common index as ALL-10 (controlling for the n_obs/k confound). Same-window delta = −0.0376, essentially identical to QD's −0.0374. The breadth effect is NOT a window artifact — CADJPY genuinely lowers normalized concentration. Mechanism: λmax barely moves (4.2736 → 4.3446) while k rises 9 → 10.

**Three reasons the improvement is IMMATERIAL (each independently sufficient):**

1. **The gate is vacuous over an empty edge set.** The 2026-06-24 9-pairs CONSENSUS established, and this wave reconfirms: "a confirmability gate over an empty edge set is vacuous." rho_bar_eff measures whether an edge, IF one existed, could be confirmed across enough effective-independent bets. With CD0 uniformly negative across 84 pair × family combos, there is no alpha whose confirmability the gate could certify. Improving 0.409 → 0.372 optimizes the denominator of a fraction whose numerator is still exactly zero.

2. **CADJPY's own CD0 fails — and WORSE than the prior best.** Best CADJPY net SR = −2.19 (F5), vs the all-9 best of −1.56. The pair that lowered concentration contributed the worst single-pair CD0 in the screen. The improvement is on a non-binding gate; the binding one (cost feasibility) is untouched except to worsen.

3. **The improvement is breadth, not a new data class.** The binding constraint, per the firm's ratified finding, is the NO-EDGE wall — which requires a data CLASS change (sub-1h, volume-bearing, or event-microstructure), not additional retail OHLCV pairs. CADJPY is retail 1h OHLCV with zero volume; it is the same data class as the other 9. It moves a non-binding gate and leaves the binding one exactly where it was.

**JPY-concentration note (QD + PR + NHT):** CADJPY is highly correlated with EURJPY (0.757), AUDJPY (0.776), and USDJPY (0.775). The JPY-cross-3 subset rho_bar_eff = 0.7479 (FAIL) and CROSSES-4 = 0.4988 (FAIL), confirming the JPY sub-cluster became MORE concentrated. The ALL-10 portfolio-level drop is carried primarily by ONE negative leg: CADJPY vs USDCAD = −0.403, partially cancelling USD factor exposure. CRO labels this "dilution arithmetic, not de-correlation."

**Proxy disclosure:** rho_bar_eff uses raw log-return proxy (no signal series available — nothing cleared screening). PR independently ran crude PnL-contribution proxies (F1-reversal, F3-momentum) for ALL-10: rho_eff ≈ 0.21, well below the raw-return 0.3716. Raw returns are a CONSERVATIVE proxy (actual signal correlations are lower if strategies differ in timing/direction). The 0.3716 PASS is directionally safe and represents the HARDER test.

---

## § CADJPY CD0 — all FAIL, worst-in-screen; running tally 84/84

Settings: real per-bar spread_median_pips, EXCLUDE-NOT-IMPUTE (0 zero-spread bars excluded), pip=0.0001 uniform (canonical prior spec, same as prior 9-pair cycles), shift(1) no-lookahead, RT cost = spread + 2×(0.25 + 0.15) = spread + 0.80 pips per position change; direct flip (+1→−1) charged as 2 position changes.

| Family | Gross SR | Net SR | N_trades | Verdict |
|--------|----------|--------|----------|---------|
| F1 hourly reversal | −0.5979 | −14.8138 | 31,085 | **FAIL** |
| F2 session-open mom | +0.4206 | −3.8527 | 2,574 | **FAIL** |
| F3 intraday mom 3 | +0.8404 | −7.1838 | 17,207 | **FAIL** |
| F4 vol breakout | +1.2064 | −7.2459 | 12,801 | **FAIL** |
| F5 London AM drift | +0.1722 | −2.1914 | 2,304 | **FAIL** |
| F6 spread-filt rev. | −0.8720 | −11.8669 | 13,715 | **FAIL** |

**Best net SR: −2.1914 (F5)** — FAIL. Distance to STRETCH bar (1.44): 3.63 SR units. Distance to PASS bar (1.76): 3.95 SR units.

**CADJPY is the WORST-IN-SCREEN:** prior all-9 best was AUDJPY F5 at −1.56; CADJPY's best is −2.19. The 10th pair did not raise the edge floor — it lowered it.

**All 6 results reproduced exact by PR** (F1 −14.8138, F2 −3.8527, F3 −7.1838, F4 −7.2459, F5 −2.1914, F6 −11.8669). No-lookahead via shift(1) confirmed. F-001 flip-cost fix confirmed (direct +1→−1 flip charged as 2 RTs).

**Running tally:** 3 waves (24 + 54 + 6 combos) = **84/84 pair × family combos net-negative**. Best-ever: −1.56 (AUDJPY F5). No candidate has cleared even the STRETCH bar (1.44) on any pair or any family in any cycle. The falsification is structural, not stochastic.

F1–F6 REMAINS RETIRED-AS-SATURATED. Retirement is **UNCONDITIONAL** on pair count. Machine-checkable re-open conditions (unchanged): (a) a NEW family spec outside F1–F6, OR (b) CRO ratifies a materially lower-cost execution assumption, OR (c) a new DATA CLASS (sub-1h / volume-bearing) changes the gross-edge-per-trade arithmetic. A 10th same-class pair is none of these.

---

## § TREADMILL-STOP — new first-class finding and machine-checkable criterion

**This is a new ratified criterion, proposed by HoQR and adopted this wave.**

The firm has now run **four readiness waves** on same-class retail-OHLCV pairs:

| Wave | Pairs | CD0 scope | Outcome |
|------|-------|-----------|---------|
| 2026-06-22 | 6→7 | 24 combos | NO-SPEND |
| 2026-06-24 (9-pairs) | 7→9 (EURGBP + AUDJPY) | 54 combos | NO-SPEND |
| 2026-06-25 (this wave) | 9→10 (CADJPY) | 84 combos | NO-SPEND |
| GBPJPY (mid-ingest) | 10→11 (projected) | +6 combos | **Math-guaranteed FAIL** |

Each wave: ingested a same-class pair, re-ran the falsified F1–F6 screen, recomputed rho_bar, and concluded NO-SPEND. GBPJPY is mid-ingest. Its CD0 result is predictable with near-certainty from 84/84 consecutive negative evaluations: FAIL. Running a 5th identical wave is the **treadmill**: cheap, infinitely repeatable, feels like motion, and cannot move the binding constraint (data CLASS) by construction.

**TREADMILL-STOP criterion (ratified, machine-checkable):**

> A same-class retail-OHLCV pair landing does **NOT** auto-trigger a readiness wave (CD0 screen + rho_bar recompute). Accept its DQ verdict as inventory hygiene (DQ-admit-and-shelve). A CD0/rho_bar readiness wave is warranted ONLY when the **data CLASS changes**: timeframe < 1h, OR volume-bearing data, OR event-microstructure feed. A bare pair-count increment within the same class is inventory hygiene, not a research event.

**GBPJPY processing rule (forward, under this criterion):** When GBPJPY completes ingest, run the DQ gate and accept the ADMIT/EXCLUDE verdict for inventory purposes. Do NOT run a CD0 screen or rho_bar recompute. Do NOT convene a readiness wave. Do NOT represent GBPJPY's DQ result as a research event or progress toward posture change.

This criterion converts "we keep getting pairs, so we keep screening" into "we screen when the thing that could actually change the answer changes." It prevents the treadmill from masquerading as research velocity.

---

## § Strategic posture HELD — existing-data exhausted; binding constraint = data capability

**The ratified posture is UNCHANGED by CADJPY.**

**Posture (verbatim from prior cycle, reconfirmed):** the existing-data strategy space is EXHAUSTED. The binding constraint is DATA CAPABILITY — a new CLASS of data (sub-1h resolution, volume-bearing, or event-microstructure feed), not additional retail OHLCV pairs. The DATASET WALL is a wall of CLASS, not of count.

**CADJPY's contribution to this posture:** None. CADJPY is retail 1h OHLCV with zero volume — the same data class as the other 9 pairs. It improved a non-binding gate (rho_bar from 0.409 to 0.372) and added the worst single-pair CD0 in the screen (best −2.19 vs prior best −1.56). A better concentration number over an edge set that remains entirely negative is not progress toward an edge.

**The strategic fork remains open and is unchanged by CADJPY (Board decision required):**

1. **DATA-CAPABILITY ACQUISITION** (recommended by HoQR) — the only lever that lifts the binding constraint. Candidate data classes: true traded volume / order-flow (CME FX futures volume, L2 depth feed) → intraday tick data → event-microstructure feeds. **HARD PRECONDITION: a written, falsifiable, data-REQUIRING hypothesis that genuinely REQUIRES the new data class must be authored AND cleared through a CD0-feasibility pre-screen BEFORE any acquisition spend.** The firm does not buy data on spec. CADJPY's breadth does NOT constitute this hypothesis or advance its authoring.

2. **WIND DOWN to observe-only / maintenance posture** — the honest default if the precondition for Option 1 cannot be met. Preserve the falsification corpus. Freeze active new-strategy generation on existing data. Gate reactivation on (a) new data arriving OR (b) a genuinely structurally-new hypothesis class.

CADJPY's rho_bar improvement provides zero evidence for either option over the other. It improves the DENOMINATOR of a fraction (confirmability of an edge) whose NUMERATOR (net-of-cost edge) is still exactly zero.

---

## § Dissent (NHT) — verbatim, append-only

*(From `nht-null-test-report.yaml`, `dissent-statement` field. Severity: informational. NHT concurs with NO-SPEND and with honest-N staying at 30. This dissent is append-only and survives any consensus revision. It may NOT be paraphrased, summarized, softened, or reordered.)*

> DISSENT (append-only, preserved verbatim):
>
> The ALL-10 rho_bar_eff = 0.3716 "clearing the 0.41 G5 gate by 0.038" must NOT be
> characterized as PROGRESS, as the universe becoming "more confirmable," or as any
> step toward H1. I record the following for the permanent record:
>
> 1. THE GATE IS VACUOUS — this was already ruled on. The 2026-06-24 9-pairs CONSENSUS
>    established, in its own words, that "a confirmability gate over an empty edge set is
>    vacuous" and "you cannot be well-diversified across an empty alpha set." That ruling
>    is binding. CADJPY changes NOTHING about it: its own CD0 screen FAILS all 6 families
>    (best net -2.19, a full 3.63 SR below STRETCH). A diversification statistic computed
>    over a basket whose net-of-cost alpha set is STILL EMPTY is measuring the covariance
>    of noise. Lowering that statistic from 0.409 to 0.372 is not progress toward
>    confirmable alpha; it is a more-precise characterization of the correlation structure
>    of strategies that all lose money.
>
> 2. THE IMPROVEMENT IS REAL BUT IMMATERIAL — and that is exactly the trap. I do not
>    dispute the arithmetic (0.3716 reproduces; the 0.038 margin is genuine and more
>    sampling-robust than the prior 0.001 razor). I dispute that it MEANS anything. A real
>    metric moving in the "good" direction while remaining causally disconnected from the
>    binding constraint is the textbook 2026-05-31 "more-data = progress" failure mode.
>    The binding constraint, per the firm's own ratified finding, is the NO-EDGE WALL
>    (net-of-cost SR < 0), not the concentration wall. CADJPY does not touch the no-edge
>    wall except to make it slightly worse (-2.19 vs the prior -1.56 best).
>
> 3. THE DROP IS NOT EVEN CLEAN BREADTH. CADJPY is +0.78/+0.78/+0.76 correlated with
>    USDJPY/AUDJPY/EURJPY; the JPY-cross-3 subset rho_bar_eff is 0.7479 (FAIL) and
>    CROSSES-4 is 0.4988 (FAIL). The headline ALL-10 decline is carried almost entirely
>    by ONE negative leg (CADJPY vs USDCAD = -0.403) that partially cancels USD factor
>    exposure. The JPY sub-cluster became MORE concentrated. Reading the portfolio-level
>    number as "the universe is more diversified" obscures that the new pair piled onto
>    the single most concentrated factor in the book.
>
> 4. NO POSTURE CHANGE, NO COUNTER INCREMENT. The ratified posture — existing-data family
>    space (F1-F6 / event-drift / carry / volume) retired-saturated; binding constraint =
>    DATA CAPABILITY (sub-1h / volume-bearing / lower realized cost) — is untouched. A 10th
>    pair of the SAME retail-OHLCV daily-class tier is not the missing capability; it is
>    more of the exhausted one. The ledger correctly carries no increment and honest-N
>    stays 30.
>
> I would NOT certify any framing of this drop as advancement. If the firm ever wants to
> assert the concentration wall is "broken," it still requires (a) a real confirmable
> signal to populate the universe — which does not exist — and (b) a block-bootstrap CI
> whose upper bound sits below 0.41. Neither condition is met, and (a) is the one that
> actually matters: with zero net edge to confirm, the gate has nothing to gate.

**Disposition:** NHT concurs with CADJPY DQ ADMIT, with NO-SPEND, and with the trial counter staying at 30. The dissent is specifically against any framing of the rho_bar improvement as progress, advancement toward H1, or evidence the concentration wall is "broken." NHT's guard is preserved verbatim and is NOT inconsistent with HoQR's posture call — both agree NO-SPEND; they agree the gate is vacuous; the dissent is purely against the "improving non-binding gate = progress" narrative.

---

## § Principal Reviewer findings — first-class

**PR decision: approve-with-conditions. 0 blocking findings.** Reviewed cold, without sight of any other role's verdict prior to independent recompute. All headline numbers reproduced exact. Same-window control confirms breadth effect genuine (not a window artifact).

| id | severity | category | location | observation | owning-role |
|----|----------|----------|----------|-------------|-------------|
| F-001 | minor — **FORWARD CONDITION** | spec-drift | `compute_9pairs_readiness.py:126-159` (compute_rho_bar_eff); rho-bar amendment lines 43-45, 84-85 | The rho-bar amendment mandates rho_eff computed on the per-pair PnL-CONTRIBUTION series (signal × return, demeaned, event-aligned) and calls that "the actual gate input." The compute instead uses raw hourly log-return correlations. PR ran PnL-contribution proxies (F1-reversal, F3-momentum) for ALL-10 and obtained rho_eff ≈ 0.21 — well below raw-return 0.3716. Raw returns OVER-STATE concentration (conservative direction); the raw-return proxy is the HARDER test. The 0.3716 PASS is therefore directionally safe for a descriptive readiness screen. CONDITION (forward-looking): any actual frozen pooled-hypothesis GATE decision binding the 0.41 threshold MUST recompute rho_eff on the amendment-mandated PnL-contribution series for the specific pre-registered signal — the 0.3716 raw-return number is NOT a substitute for that gate input. | head-of-quant-research |
| F-002 | minor | edge-case | `compute_9pairs_readiness.py:379-401` (F5 london_am_drift position construction) | F5 builds position via positional .shift(s+1) across a non-contiguous index. On clean days the hold is correctly 09:00–12:00 (4 bars). Across missing-bar boundaries the shifts land on later in-session hours, so effective hold window is 09:00–17:00. Forward-only — no lookahead. Verdict-irrelevant (F5 net −2.19 far below 1.44 bar). Flagged for hygiene: fix if any F5-class strategy is ever promoted past CD0. | quant-developer |
| F-003 | observation | edge-case | `compute_10pairs_raw.json` C1 max_contiguous_gap_h=24 | CADJPY's max contiguous gap = 24 h, exactly at the inclusive gate ceiling. PASS is correct (gate is ≤24). Zero gate margin on this one criterion — a single additional missing in-session hour would flip to EXCLUDE. | quant-developer |
| F-004 | observation | numerical | `quant-developer-compute.yaml` assumptions[1]; `run_cd0_family` docstring lines 299-310 | pip=0.0001 applied uniformly to CADJPY (a JPY-quote pair). Gross PnL scales multiplicatively by the pip denominator while cost is additive, so the "scales together → comparable" justification in the docstring is an over-claim. Immaterial here: all net SRs are −2.19 to −14.81, far below any FAIL→PASS flip. Flagged: if any JPY-pair result ever lands near the bar, the pip convention must be addressed. | quant-developer |

**PR coverage statement:** Independently reproduced rho_bar_eff for all four subsets (ALL-10, ALL-9, JPY3, CROSSES4 — all exact); ran same-window ALL-9 control (delta −0.0376, confirms genuine breadth effect); reproduced all 9 CADJPY pairwise correlations (all exact); ran DQ gate via coverage_gate library directly (ADMIT, all sub-metrics exact); reproduced all 6 CD0 net SRs to 4 decimal places (all exact); confirmed shift(1) no-lookahead, F-001 flip-cost fix, and cost model (spread + 0.80). Also ran two PnL-contribution proxies to test the F-001 conservatism direction. **Blocking finding count: 0.** F-001 is a forward condition only; it cannot flip any verdict in this descriptive-screen context.

---

## § CRO risk position

**Decision: VETO. Size: 0.0. No capital allocation. No counted trial.**

CRO's three-reason analysis (each independently sufficient):

**1. NO EDGE TO SIZE.** All six CADJPY canonical families screen net-NEGATIVE in-sample with real spreads under EXCLUDE-NOT-IMPUTE. Best is −2.19 net SR — 3.63 SR units below the STRETCH bar (1.44) and 3.95 below PASS (1.76). In-sample is the OPTIMISTIC bound: no OOS penalty, no DSR deflation. A candidate that cannot clear zero in-sample has no path to clearing a deflated 1.76 out-of-sample. Sizing a negative-expectancy sleeve is a guaranteed bleed, not a risk-reward trade.

**2. DIVERSIFICATION IS ILLUSORY.** G5 gate clears (ALL-10 rho_bar_eff 0.3716 ≤ 0.41), but the gate is necessary, not sufficient. N_eff = 2.302 means the 10-instrument book behaves like ~2.3 independent bets. CADJPY does not add a new bet: its correlations to EURJPY (+0.757) and AUDJPY (+0.776) place it inside an already-concentrated JPY-cross-3 block (rho 0.7479). The aggregate rho improving from 0.409 to 0.372 is the mechanical effect of averaging in one more column — **dilution arithmetic, not genuine de-correlation**. The single negative cross-correlation (USDCAD −0.403) is real but cannot offset a block of +0.76 co-movement at the portfolio level.

**3. THE COMBINATION IS STRICTLY DOMINATED.** Negative edge AND concentrated tail is worse than flat on every axis CRO measures: expected return (negative), tail (correlated JPY-cross drawdown realizes together), and capital efficiency (risk consumed for sub-zero reward). There is no size_multiplier > 0 that is defensible.

**CRO blowup-analog:** Sizing multiple tightly co-moving negative-edge sleeves (JPY-cross-3 at rho 0.748) realizes the full block's loss simultaneously while the nominal "10-instrument diversification" implies an independence that N_eff 2.302 disproves — the LTCM-style "we hold many positions but one bet" failure mode, caught pre-capital. No edge + concentrated tail is strictly dominated by holding flat.

**What would change this:** a future candidate that (a) screens net-POSITIVE through STRETCH/PASS after OOS + DSR deflation, AND (b) is risk-budgeted against the JPY-cross-3 block rather than counted as an independent 10th bet. CADJPY's admission to the data universe is appropriate (clean DQ); allocation of risk to it on this evidence is not.

---

## Signatures

| Role | Verdict | Signed |
|------|---------|--------|
| quant-developer | implemented-and-verified (CADJPY DQ gate run with new config entry; rho_bar ALL-10 computed; CD0 all-6 FAIL confirmed; all reuses from prior 9-pairs harness; counts_toward_deflation_denominator: false) | @fintech-org-qd-2026-06-25 |
| head-of-quant-research | reject=HOLD/NO-SPEND (posture unchanged; binding constraint = data capability; F1–F6 retirement unconditional; TREADMILL-STOP ratified as new machine-checkable criterion; GBPJPY to be processed as DQ-admit-and-shelve) | @fintech-org-hoqr-2026-06-25 |
| cro | VETO / size 0.0 (no edge to size; diversification illusory / dilution arithmetic; negative-edge + concentrated-tail strictly dominated by flat; LTCM-analog blowup risk caught pre-capital) | @fintech-org-cro-2026-06-25 |
| null-hypothesis-tester | noise-indistinguishable (all three nulls tested; rho_bar improvement real but immaterial; CADJPY CD0 worst-in-screen; no posture change; no counter increment; CONCURS NO-SPEND; DISSENTS on any "progress" framing — verbatim preserved above) | @fintech-org-nht-2026-06-25 |
| principal-reviewer | approve-with-conditions (all headline numbers reproduced exact; same-window breadth control confirms genuine; 0 blocking findings; F-001 as forward condition for any future binding gate decision) | @fintech-org-pr-2026-06-25 |
| pm | synthesis-complete (NHT dissent preserved verbatim; PR findings first-class; TREADMILL-STOP recorded prominently; strategic posture held recorded; no technical calls) | @fintech-org-pm-2026-06-25 |

---

## Knowledge gaps surfaced

The following are role-level data and scoping limitations surfaced in session artifacts. They are NOT installable skill gaps. **Installable-skill-gap count N = 0.** No new entries appended to `.fintech-org/skill-gaps.jsonl` this session. All gaps below are data-class or scope gaps resolved only by acquiring new data or commissioning new hypothesis work.

| Gap | Source | Resolution path |
|-----|--------|----------------|
| True PnL-contribution rho_bar_eff for ALL-10 is uncomputable (no signal series cleared screening; only raw-return proxy exists). Moot: raw-return is conservative direction; gate vacuous over empty edge set. | HoQR, NHT, PR | Computable only after a positive-net-SR candidate clears CD0 and has a frozen signal series. Not an installable skill gap. |
| Whether a non-F1-F6 / cost-aware / event-conditioned family OR a new data class can clear the CD0 cost hurdle is the only open path to a positive net SR. Untested by design until the strategic fork is resolved. | HoQR | Requires: (a) data-CLASS acquisition with precondition, OR (b) wind-down decision. Not an installable skill gap. |
| A block-bootstrap CI on λmax (to certify rho_bar_eff "robustly cleared" at the 0.038 margin) has not been run. Moot for this decision: even a CI-certified gate-pass is vacuous over a zero-edge universe. | NHT | Would ROUTE_TO quant-developer only if a positive-SR candidate existed and the concentration gate were binding. Not an installable skill gap. |

---

## Open items requiring Board acknowledgment

**(a) TREADMILL-STOP ADOPTION (required):** The Board must acknowledge the TREADMILL-STOP criterion ratified this wave. GBPJPY will be processed under this rule when ingest completes: DQ-admit-and-shelve, no CD0 screen, no rho_bar recompute, no readiness wave. Any future same-class retail-OHLCV pair (if ingest continues) is treated identically. A readiness wave is re-warranted ONLY when the data CLASS changes.

**(b) THE STRATEGIC FORK (primary; requires CEO decision — unchanged from prior cycle):** The Board must choose between:
- **Option 1 (Data-capability acquisition):** Authorize a data-diligence phase. HARD PRECONDITION: a written, falsifiable, data-REQUIRING hypothesis AND a ratified CD0-feasibility pre-screen showing a candidate family's GROSS edge plausibly clears the round-trip cost hurdle BEFORE any acquisition spend. HoQR recommends this path. CADJPY's breadth does NOT constitute this hypothesis or advance its authoring.
- **Option 2 (Wind down to observe-only / maintenance):** Freeze active new-strategy generation on existing data. Preserve the falsification corpus. Gate reactivation on new data arriving or a structurally-new hypothesis class. The honest default if Option 1's precondition cannot be met.

Options 3 and 4 (carry on longer history; more existing-data generation) remain low-priority / EV-negative per HoQR.

**(c) PR forward condition F-001 (any future binding gate decision):** Any future frozen pooled-hypothesis GATE decision that binds the 0.41 rho_bar_eff threshold MUST recompute rho_eff on the amendment-mandated PnL-contribution series for the specific pre-registered signal. The 0.3716 raw-return descriptive number is NOT a substitute for that gate input. Owner: head-of-quant-research. Board acknowledgment sufficient; no action required until a positive-SR candidate exists.

---

## Prior decisions NOT made / carry-forward items

- **H1 un-freeze:** FORBIDDEN. No CD0 net SR ≥ 1.76 candidate exists. No change.
- **GBPJPY:** To be processed under the TREADMILL-STOP rule when ingest completes (DQ-admit-and-shelve).
- **F1–F6 canonical families:** Remain RETIRED-AS-SATURATED (84/84 combos net-negative; UNCONDITIONAL on pair count).
- **Volume-conditioned family:** Remains RETIRED / FAMILY-CLOSED (2026-06-24 wave).
- **C1 (CB-decision drift):** Remains retired (regime artifact; OPEN-ITEM-C1FILTER unresolved).
- **C2 (carry multi-session hold):** Remains killed as-run (OPEN-ITEM-C2COST now CLOSED per prior cycle).
- **honest-N:** Remains 30. No increment this cycle.

---

*This CONSENSUS.md is the audit-trail source-of-truth for the 2026-06-25 CADJPY 10-pairs readiness wave. Append-only per protocol. No section may be softened, reordered, or omitted in future revisions — only new sections may be appended.*
