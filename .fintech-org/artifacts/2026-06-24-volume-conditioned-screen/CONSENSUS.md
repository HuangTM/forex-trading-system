# Consensus on: Volume-conditioned candidate screen — V1 (relvol-continuation) and V2 (relvol∧low-spread mean-reversion)

**Status:** ratified_with_dissent (distributed quorum: cro + head-of-quant-research, 2026-06-25; surfaced to Board, non-blocking)
**Session artifacts:** `.fintech-org/artifacts/2026-06-24-volume-conditioned-screen/`
**Date:** 2026-06-24

---

## Roles staffed

| Role | Rationale |
|------|-----------|
| Quant Researcher (QR) | Authored two declarative TradeIntent candidates: V1 (relative-volume participation-surprise continuation) and V2 (relvol-high ∧ spread-low mean-reversion). Pre-registered a volatility-control test. Measured raw volume~range and relvol~relrng correlations prior to design. No implementation code. |
| Quant Developer (QD) | Fixed OPEN-ITEM-C2COST (exit-leg cost under-count in `scripts/cost_feasibility_c1_c2.py`), verified with a new distinct assertion; ran the R1 cost-feasibility screen on V1 (5 pairs) and V2 (3 pairs) using a new `scripts/volume_conditioned_screen.py`; executed the volatility-control regression and 2×2 stratification. |
| Head of Quant Research (HoQR) | Pre-screen review; advance-or-kill call; issued the strategic meta-call that the existing-data strategy space is exhausted. |
| Chief Risk Officer (CRO) | Structured risk position; veto / size 0.0; identified the conjunctive (cost-pass AND vol-control t≥2.00) gate as EMPTY; characterized the apparent signal as volatility-harvesting. |
| Null-Hypothesis Tester (NHT) | Structural skeptic; reproduced all V1 relvol t-stats to 3 decimal places; dissent filed and preserved verbatim; non-blocking, concurs kill but dissents on framing. |
| Principal Reviewer (PR) | Independent cold review; reproduced 4 headline numbers exactly; C2COST fix verified twice on two topologies; 0 blocking findings; 2 forward conditions (F-002, F-004). |
| PM | Synthesized this consensus; preserved NHT dissent verbatim; tracked forward conditions; made no technical calls. |

---

## Acceptance criteria (from PM artifact)

- [x] **C2COST-FIXED-AND-VERIFIED:** `scripts/cost_feasibility_c1_c2.py` line 575 updated — slice extended from `[entry_i:exit_i+1]` to `[entry_i:exit_i+2]`, capturing the exit-change bar. New distinct assertion `C2COST_FULL_RT_ENTRY_PLUS_EXIT` verified on synthetic flat→+1→+1→+1→flat path: buggy slice 1.10 pips (entry only), fixed slice 2.20 pips (entry + exit = full RT), undercount = exactly 1 exit leg. `compute_rt_cost_series` NOT modified. OPEN-ITEM-C2COST formally **CLOSED**. PR independently confirmed on two topologies (toy path and multi-bar carry-loop topology).
- [x] **VOLUME-CONDITIONED-CANDIDATES-DESIGNED:** V1 and V2 specified as declarative TradeIntent artifacts (pair scope, volume signal, entry/exit/hold, gross-edge rationale with derivation, fires/yr, explicit tick-vs-volatility orthogonality argument). No implementation code by QR.
- [x] **COST-FEASIBILITY-VERDICT-PER-CANDIDATE:** QD produced structured records per pair with N_fires, fires/yr, gross/trade, RT cost/trade (conditioned-bar spreads + 0.80 overhead, pair-native pips, EXCLUDE-NOT-IMPUTE), margin, and explicit cost verdict. See tables below.
- [x] **VOLATILITY-CONTROL-CHECK:** Joint OLS of gross on rank(relvol) + rank(relrng) run on all 8 pair-candidate combinations; 2×2 stratification (relvol high/low × relrng high/low) run on V1 pairs. relvol t-stat < 2.00 for ALL 8 combinations.
- [x] **HoQR-PRE-SCREEN-REVIEW-GATE:** HoQR reviewed both candidates and pre-cleared V1 and V2 before QD ran the screen.
- [x] **AMENDED-GATE-APPLIED:** Regime-stratification, t-statistic, and no-single-year checks applied. Both families killed before reaching the amended gate (vol-control fires first), confirming no advancement is warranted.
- [x] **ADVANCE-OR-KILL-DECISION:** HoQR issued explicit direction: **KILL / FAMILY-CLOSED**. No candidate is cost-PASS AND GATE-CLEAR.
- [x] **NHT-NULL-EVALUATED:** NHT evaluated whether the volume-conditioning effect is distinguishable from volatility. Dissent filed and preserved verbatim.
- [x] **TRIAL-COUNTER-UNCHANGED:** honest-N = 30 confirmed. No entry with `counts_toward_deflation_denominator: true` appended. Descriptive feasibility screen only.
- [x] **CRO-STRUCTURED-FIELDS-COMPLETE:** CRO artifact contains all required structured fields; veto issued; size 0.0.
- [x] **PR-REVIEWED:** PR issued approve-with-conditions; 0 blocking findings; C2COST fix independently spot-checked on two topologies.
- [x] **CONSENSUS-AUTHORED:** this document.

---

## Decision

**NO-SPEND. RETIRE V1. RETIRE V2. FAMILY-CLOSED (volume-conditioning on existing 9-pair 1h store). Honest-N stays 30. No trial-counter increment. OPEN-ITEM-C2COST CLOSED.**

All four IC roles (HoQR, CRO, NHT, PR) independently converged: volume conditioning on the existing 9-pair 1h parquet carries no directional information orthogonal to realized volatility. Both candidates are killed on pre-registered, machine-checkable triggers. The FAMILY-CLOSED label applies: no re-parameterization of this family on this data class can rescue it — the collinearity (raw volume~range Spearman 0.69–0.74) is a structural property of broker tick-volume in OTC FX, not a measurement artifact.

**The decisive single fact:** USDJPY V1 — the only pair with a nominally large gross (+3.30 pips) — has its entire positive edge in the high-relvol × HIGH-range cell (+6.03 pips). The "volume-without-volatility" cell (high-relvol × low-range) is −0.45 pips. The volume signal is a volatility proxy; the signal carries no directional information orthogonal to range. This is confirmed independently by the volatility-control regression: relvol t-statistic is below 2.00 for all 8 pair-candidate combinations (range: −0.90 to +1.15). The conjunctive gate (cost-pass AND vol-control t≥2.00) is EMPTY across the entire selection surface.

---

## Volume-vs-volatility evidence — V1 and V2 tables

### Volume~Range correlation diagnostics (measured by QD on 9-pair 1h parquet)

| Pair   | raw_vol~rng (Spearman) | relvol~relrng (Spearman) | log-log R² |
|--------|------------------------|--------------------------|------------|
| EURUSD | 0.6879                 | 0.3557                   | 0.1584     |
| GBPUSD | 0.7105                 | 0.3911                   | 0.1644     |
| USDJPY | 0.7279                 | 0.5730                   | 0.3073     |
| EURJPY | 0.7414                 | 0.5570                   | 0.2994     |
| AUDUSD | 0.7398                 | 0.5235                   | 0.2990     |
| EURGBP | 0.7431                 | 0.4225                   | 0.2042     |

QR's descriptive probe stated raw_vol~range ≈ 0.62–0.72; measured = 0.69–0.74 (consistent, slightly higher). QR's relvol~relrng stated 0.53–0.64; measured = 0.36–0.57 (EURUSD/GBPUSD somewhat lower). The lower relvol~relrng on EURUSD/GBPUSD improves the orthogonality argument marginally, but the regression confirms the residual carries no directional sign.

### V1 — RELVOL-CONTINUATION cost-feasibility

Signal: session-open hour (07 or 13 UTC), relvol ≥ 1.5 × seasonal norm, direction = sign(close−open). Entry: bar t+1 open. Exit: bar t+2 close (2-bar hold). RT cost: entry_spread + exit_spread + 0.80 on CONDITIONED bars.

| Pair   | N_fires | Fires/yr | Gross/tr (pips) | RT cost/tr (pips) | Margin (pips) | Cost verdict |
|--------|---------|----------|-----------------|-------------------|---------------|--------------|
| EURUSD |     791 |    158.6 |          1.6446 |            1.5083 |        +0.1363 | **PASS**    |
| GBPUSD |     504 |    101.0 |          0.9149 |            2.8298 |        −1.9149 | FAIL        |
| USDJPY |     819 |    164.2 |          3.3023 |            2.1192 |        +1.1832 | **PASS**    |
| EURJPY |     503 |    100.8 |          0.0132 |            3.2076 |        −3.1943 | FAIL        |
| AUDUSD |     616 |    123.5 |          1.2712 |            3.1135 |        −1.8423 | FAIL        |

QR pre-registered kill: FAIL iff gross ≤ 0.80 × RT_cost on ≥3 of 5 pairs. **KILL criterion fires: 3 of 5 FAIL (GBPUSD, EURJPY, AUDUSD).**

Note: EURUSD and USDJPY are cost-PASS. These do not rescue V1 because (a) the family-level kill criterion fires (3/5), and (b) both PASS pairs fail the volatility-control test decisively (see below).

### V1 — Volatility-control OLS (decisive)

Regression: gross_pips ~ intercept + rank(relvol) + rank(relrng). Pass criterion: relvol t-stat ≥ 2.00.

| Pair   | N    | relvol coef | relvol t | relrng coef | relrng t | R²     | Pass t≥2? |
|--------|------|-------------|----------|-------------|----------|--------|-----------|
| EURUSD |  791 |   +0.00185  |    +0.45 |   +0.00381  |    +0.94 | 0.0024 | **NO**   |
| GBPUSD |  504 |   −0.00194  |    −0.16 |   +0.00857  |    +0.71 | 0.0010 | NO       |
| USDJPY |  819 |   −0.00205  |    −0.33 |   +0.01155  |    +1.83 | 0.0042 | NO       |
| EURJPY |  503 |   −0.01384  |    −0.90 |   +0.02700  |    +1.76 | 0.0064 | NO       |
| AUDUSD |  616 |   +0.00579  |    +1.15 |   +0.00012  |    +0.02 | 0.0025 | NO       |

**ALL FIVE PAIRS FAIL.** R² = 0.001–0.006; the regression explains essentially nothing. relvol t-stat is negative for 4 of 5 pairs. NHT independently reproduced all five V1 t-stats to 3 decimal places (EURUSD +0.453, GBPUSD −0.161, USDJPY −0.326, EURJPY −0.904, AUDUSD +1.153). Not fabricated — genuinely null.

### V1 — USDJPY 2×2 stratification (the decisive disqualification)

| Cell                      | n   | Gross (pips) | Interpretation                        |
|---------------------------|-----|--------------|---------------------------------------|
| high_relvol × high_relrng | 250 | **+6.03**    | **Edge lives HERE — the volatility cell** |
| high_relvol × low_relrng  | 160 | **−0.45**    | Volume-without-volatility: NEGATIVE   |
| low_relvol × high_relrng  | —   | +2.69        | Range drives the return, not volume   |
| low_relvol × low_relrng   | —   | +3.36        | Consistent with range-not-volume      |

Per QR's pre-registered disqualification trigger: "If the gross edge lives ONLY in the high-relvol/high-relrng cell, the signal is volatility, not volume → DISQUALIFIED." The disqualification fires. USDJPY is disqualified as a F1–F6 vol-breakout restatement wearing a volume label. The full 2×2 makes the case stronger than the two-cell summary: positive gross persists across relrng-high cells regardless of relvol; relvol is not the relevant axis.

**V1 VERDICT: DISQUALIFIED.** Both independent kill paths fire. V1 CLOSED.

### V2 — RELVOL-HIGH ∧ SPREAD-LOW MEAN-REVERSION cost-feasibility

Signal: relvol ≥ 1.5 AND spread ≤ p40, extension ≥ 0.75 × seasonal-median-range from session open. Direction: fade the extension. Entry: t+1 open. Exit: t+3 close or session-open touch, whichever first.

| Pair   | N_fires | Fires/yr | p40 spread (pips) | Gross/tr (pips) | RT cost/tr (pips) | Margin (pips) | Cost verdict |
|--------|---------|----------|-------------------|-----------------|-------------------|---------------|--------------|
| EURUSD |   2926  |    586.6 |              0.30 |         −0.1703 |            1.4777 |       −1.6480 | FAIL         |
| USDJPY |    788  |    158.0 |              0.50 |         −3.4409 |            2.3074 |       −5.7484 | FAIL         |
| EURGBP |    969  |    194.3 |              0.80 |         −1.1696 |            2.7087 |       −3.8783 | FAIL         |

All three pairs: FAIL with deeply negative gross (negative BEFORE costs).

### V2 — Construction void (disqualification)

The spread-low gate was designed to exclude high-volatility bars. The verification checks whether conditioned-entry relrng median < 1.2 × sample median (= 1.0).

| Pair   | Conditioned relrng median | vs sample (1.0) | Ratio | Status             |
|--------|---------------------------|-----------------|-------|--------------------|
| EURUSD | 1.3108                    | +31.1%          | 1.31  | **DISQUALIFIED**   |
| USDJPY | 1.2523                    | +25.2%          | 1.25  | **DISQUALIFIED**   |
| EURGBP | 1.5368                    | +53.7%          | 1.54  | **DISQUALIFIED**   |

All three pairs disqualified: the spread-low gate FAILED to exclude high-range bars. Conditioned entries are 25–54% higher-range than the full-sample average. The joint relvol-high ∧ spread-low condition does not isolate a low-volatility regime on this data. V2 volatility-control regression: relvol t = +0.25, +0.04, −0.49 — all far below 2.00.

**V2 VERDICT: DISQUALIFIED on all three independent grounds simultaneously.** Cost-axis FAIL (all pairs, negative gross); construction void (spread-low gate failed); vol-control FAIL (all pairs). V2 CLOSED.

---

## § Strategic posture — existing-data space exhausted; data capability is the binding constraint

**This section records HoQR's strategic meta-call. It is the headline for the Board.**

HoQR's honest research-leadership finding: **the existing-data intraday/daily strategy space is, for practical purposes, exhausted. The binding constraint is now DATA CAPABILITY, not idea generation.**

The evidence is structural, not stochastic. The full firm corpus now reads as a coherent set of named structural falsifications:

- **F1–F6 canonical families:** Retired-saturated. Trend, breakout, and mean-reversion families all data-snooped out; OOS collapse is the documented base rate.
- **C1 (CB-decision drift):** Regime artifact. Edge was a 2022–23 FOMC hiking-cycle shadow; drop-regime t = 0.62 (noise).
- **C2 (carry multi-session hold):** Idea untested-but-cost-failed. C2COST exit-leg fix (this cycle) reconfirmed USDJPY net-negative (+1.807 → −0.743). Carry is a real factor but a low-frequency one; the 5-year daily window cannot confirm it at power.
- **Volume-conditioned (this cycle):** Volume = volatility on tick-data; no orthogonal directional edge.

Four distinct levers. Four structural walls. The same four recurring causes every cycle: (1) cost-dominance on any turnover the data can support, (2) USD-factor concentration across a dozen mostly-USD pairs (little cross-sectional breadth), (3) regime-dependence that a single 5-year window cannot separate from alpha, and (4) the absence of true volume / order-flow / depth. ~50+ trials, ~2 months, honest-N = 30, **ZERO confirmable net-of-cost edge.**

When the same wall recurs across independent idea families, the wall is the dataset, not the ideas. This is the DATASET WALL the firm has flagged before — now confirmed a third time by an independent family. HoQR's inversion test: what would make this conclusion WRONG? It would take a structurally-new hypothesis class — not a relabel of trend/breakout/event-drift/carry/volume — that the existing dataset can confirm at power. HoQR does not see one.

**HoQR's ranked forward options:**

1. **DATA-CAPABILITY ACQUISITION** — the only lever that lifts the binding constraint. Candidate classes in rough order of expected unlock: true traded volume / order-flow (CME FX futures volume as a CLS/interbank proxy, or L2 depth feed) → intraday tick data → more instruments (EM / crosses for cross-sectional breadth) → longer history (for carry / low-frequency confirmation power). **HARD PRECONDITION: a written, falsifiable hypothesis that genuinely REQUIRES the new data class must exist BEFORE any acquisition spend.** The firm does not buy data on spec. The volume cycle is the proof-of-concept of WHY this precondition matters: tick-volume failed specifically because it is not real volume — that names the acquisition target but does NOT justify the purchase on its own.

2. **WIND DOWN active existing-data screening to observe-only / maintenance posture** — the correct default if no data-acquisition hypothesis clears the precondition. Preserve the falsification corpus (the firm's most valuable current asset), freeze new existing-data generation, and gate reactivation on (a) new data arriving OR (b) a genuinely structurally-new hypothesis class not a relabel of the four falsified families. This is NOT a failure verdict — running a full cycle and correctly spending nothing is the governance system working.

3. **CARRY C2 re-attempt on longer history** — LOW priority, folds into option 1 (needs longer history to confirm at power). Real factor; wrong window.

4. **MORE EXISTING-DATA GENERATION** — REJECTED as EV-negative. Diminishing-to-negative returns; the four structural walls will recur.

**NHT's guardrail on this meta-call (see § Dissent below):** The volume null does NOT itself justify a data acquisition spend. What this screen established is narrower: broker tick-volume on the existing 9-pair 1h parquet is mechanically collinear with range and adds no directional information. That is NOT evidence that true traded-volume or L2 depth would carry an edge, and it is NOT independent confirmation of the dataset-wall thesis. Any data-capability spend must stand on its own pre-registered hypothesis. (NHT concurs with the kill; dissent is against the "progress" framing and the data-spend inference.)

---

## § Process note — OPEN-ITEM-C2COST CLOSED; R1 gate separated another dead lever at zero honest-N cost

**OPEN-ITEM-C2COST CLOSED.** QD fixed the exit-leg cost under-count in `scripts/cost_feasibility_c1_c2.py` at line 575. The old slice `[entry_i:exit_i+1]` stopped one bar short of the exit-change bar (bar `j = exit_i+1`), silently dropping the exit-leg RT cost for every trade. The fix: `[entry_i:exit_i+2]`. `compute_rt_cost_series` is NOT modified — it already correctly charges the exit-change bar; only the slice boundary changed.

**PR independently verified the fix on two topologies:**
- Toy path (QD's synthetic): buggy → 1.10 pips (entry only); fixed → 2.20 pips (entry + exit). Confirmed.
- Real carry-loop topology (multi-bar hold, entry_i=2, exit_i=5, j=6): buggy `iloc[2:6]` → 1.30 pips; fixed `iloc[2:7]` → 2.60 pips. Confirmed NOT double-charging.

**PR scoping of the fix:** The C2COST bug lived ONLY in the C2 carry screen's trade-loop (`cost_feasibility_c1_c2.py:run_c2_pair`). The V1/V2 volume screen (`volume_conditioned_screen.py`) charges cost directly as `entry_spread + exit_spread + RT_OVERHEAD` on the event-trade — a different code path. The C2COST bug NEVER affected V1/V2 numbers. The volume-screen verdicts are uncontaminated by the prior bug.

**R1 cost-feasibility gate worked as designed at zero honest-N cost.** The amended R1+R2+amended-gate framework separated the last major existing-data lever from a counted trial cheaply. Both V1 and V2 were killed at the cost-feasibility and volatility-control gates — before any committed CPCV pre-registration, before any honest-N increment. This is the correct use of the firm's governance framework.

---

## § Dissent (NHT) — verbatim, append-only

*(From `nht-null-test-report.yaml`, `dissent-statement` field. Severity: informational. NHT concurs with the kill and with honest-N staying at 30. This dissent is append-only and survives any consensus revision. It may NOT be paraphrased, summarized, softened, or reordered.)*

> I do not dissent from the quant-developer's CONCLUSION (both families CLOSED) -- the
> data supports it and I reproduced the deciding numbers independently. I dissent from
> any framing that treats this screen as PROGRESS or as having "found" anything.
>
> THE KEY CLAIM (ii) -- that volume conditioning carries directional information beyond
> volatility -- is REJECTED by the firm's own pre-registered test, on every pair, with
> no ambiguity. The volatility-control relvol t-statistic is below 2.00 for all 8
> pair-candidate cells, and is NEGATIVE for 4 of the 5 V1 pairs and 1 of 3 V2 pairs.
> raw_vol~range = 0.69-0.74 and relvol~relrng = 0.36-0.57 confirm volume is, on this
> data, largely a noisy restatement of range. The single positive cell anyone might
> point to -- USDJPY high-relvol x HIGH-relrng = +6.03 pips -- lives in the VOLATILITY
> cell; its volume-without-volatility sibling cell is -0.45 pips. That is the signature
> of a volatility proxy, not a volume edge.
>
> The two "cost-PASS" labels (EURUSD, USDJPY) must NOT be read as partial success. I
> checked their unconditioned gross significance: nominal one-sample t = +2.01 and +2.34
> -- barely above 2 even BEFORE controlling for volatility, before any multiplicity
> deflation, and before the volatility-control test strips the volume attribution away.
> Across 8 pair-candidate cells, two marginal nominal passes is precisely what selection
> manufactures. They are not orthogonal alpha; they are the EUR/JPY majors' tight spreads
> meeting a 2-bar momentum carry that the t<2 volatility-control test attributes to range,
> not volume.
>
> GUARD on the 2026-05-31 'more-data = progress' failure mode, in its new dress: the
> temptation here is to log "we screened the volume lever, it didn't work, onward to
> intraday tick / L2 depth." That conclusion (the data-capability path) may well be
> right -- but it does NOT follow from THIS screen, and must not borrow this screen's
> credibility. What this screen actually established is narrower and should be stated
> plainly: on the EXISTING 9-pair 1h parquet, BROKER TICK-VOLUME is mechanically
> collinear with range and adds no directional information. That is a statement about
> THIS volume proxy on THIS data -- it is NOT evidence that true traded-volume or L2
> depth WOULD carry an edge, and it is NOT independent confirmation of the dataset-wall
> thesis. Spending more data money on the strength of a screen that merely re-confirmed
> volume = volatility would be the exact 2026-05-31 error wearing a volume hat. The
> honest read: one more lever on the existing data is exhausted; the case for buying
> new data must stand on its OWN pre-registered hypothesis, not on this null result.
>
> No trial increment. honest-N stays 30. The firm ran a cheap screen and correctly
> spent nothing -- that is the win, and the only win.

**Disposition:** NHT concurs with NO-SPEND and with the trial counter staying at 30. The dissent is specifically against (a) framing this screen as "progress" or as having "found" anything, and (b) treating the volume null result as independent justification for a data-capability spend. NHT's guard is preserved verbatim and is NOT inconsistent with HoQR's strategic meta-call — both acknowledge the data-capability path; they differ only on whether this screen's null provides independent evidence for it.

---

## § Principal Reviewer findings — first-class

**PR decision: approve-with-conditions. 0 blocking findings.** Reviewed cold, without sight of any other role's verdict. All headline numbers reproduced exact. C2COST fix verified twice on two independent topologies.

| id | severity | category | location | observation | owning-role |
|----|----------|----------|----------|-------------|-------------|
| F-001 (PR report) | observation | spec-drift | `volume_conditioned_screen.py:405,625` vs `cost_feasibility_c1_c2.py:579` | The C2COST fix is correct and necessary for the C2 carry screen. The V1/V2 volume screen charges cost directly (entry+exit spread + RT_OVERHEAD on the event-trade, not via the trade-loop hold_cost slice). So the C2COST bug NEVER touched the V1/V2 results. The deliverable correctly attributes the fix's impact to prior C2 results, not to V1/V2. Flagged so readers do not conflate the two code paths. | quant-developer |
| F-002 (PR report) | minor — **FORWARD CONDITION** | numerical | `volume_conditioned_screen.py:205-214` (`compute_seasonal_norm`) | Seasonal volume norm uses full-sample median per (dow×24+hour) bucket — a mild lookahead. PR verified the bias direction empirically: full-sample norm fires 820 USDJPY session-open bars vs 1181 under an expanding past-only norm — the full-sample norm is MORE restrictive (strongest-tail selector), so the bias is conservative w.r.t. the family-close verdict. The lookahead cannot rescue a killed candidate. BUT: any future committed CPCV backtest MUST replace the full-sample norm with a rolling/expanding past-only norm. This is a hard forward condition. | quant-researcher |
| F-003 (PR report) | minor | observability-gap | QD deliverable USDJPY 2×2 narrative | QD's 2×2 summary emphasized the high_rv×high_rr (+6.03) and high_rv×low_rr (−0.45) cells. The full 2×2 in the raw JSON additionally shows low_rv×high_rr = +2.69 and low_rv×low_rr = +3.36 — positive gross persists across high-relrng cells regardless of relvol level. This makes the "range, not volume" case STRONGER than the two-cell summary. Not a correctness error; the conclusion is understated, not overstated. Raw JSON preserves the full decision trace. | quant-developer |
| F-004 (PR report) | observation — **FORWARD CONDITION** | edge-case | `quant-developer-feasibility.yaml:320`; QR design V2 session-open anchor | V2 fired 2926 times on EURUSD (~587/yr) vs QR's estimate of 40–80/yr — a ~7–15× miss. Root cause: the V2 "session open = first bar of UTC calendar date (00:00 UTC)" anchor means cumulative drift from a fixed midnight anchor grows through the day, making the "extension from session open" gate near-vacuous by late in the session. The FAIL/DISQUALIFY verdict is unaffected (construction ratio 1.25–1.54 >> 1.2 = DISQUALIFIED on its own terms). If the volume lever is ever revisited on intraday data, the session-open anchor MUST be fixed to a genuine trading-session open (e.g., London-open bar). | quant-researcher |
| F-005 (PR report) | observation | correctness | QD V1 cost-PASS labels (EURUSD, USDJPY) | Two V1 pairs are labeled cost-PASS (EURUSD gross 1.6446 > RT 1.5083; USDJPY 3.3023 > 2.1192). QR's 1-bar probe predicted ~0.9 pips. The lift comes from the 2-bar hold window, not a measurement error. PR confirmed gross is computed correctly: entry_open(t+1) → exit_close(t+2), genuine 2-bar capture. The cost-PASS labels are arithmetically correct but do NOT advance the candidate — family-kill fires on ≥3/5 cost-FAIL AND vol-control t<2.00 on ALL pairs including both PASS pairs. Transparency win, not a buried lede. | quant-developer |

**PR coverage statement:** Reviewed: C2COST fix (independent recompute on toy path AND real carry-loop topology); no-lookahead trace (signal on closed bar t, entry bar t+1 open, exit bar t+2 close — clean); seasonal norm direction measurement (USDJPY full-sample=820, expanding=1181, bias conservative); volatility-control OLS (SE re-derived, t-stats matched to digit); USDJPY 2×2 (reproduced exactly, full 4-cell table noted); V2 construction check (conditioned relrng ratios reproduced); cost application (entry+exit conditioned spreads, pair-native pips JPY=0.01, EXCLUDE-NOT-IMPUTE — 0 zero/NaN spread bars on all 6 pairs, path correct-but-inert); multiplicity (39 descriptive cells / 19 decision cells; all decisions run against the candidate; no false PASS claimed). Skipped: forex/TA alpha plausibility (forbidden by role scope); C1 re-screen (out of scope). Reproduced 4 headline numbers — all EXACT.

**Blocking finding count: 0.** Both forward conditions (F-002, F-004) are documentation/fidelity notes; neither can flip the FAIL/DISQUALIFY verdict.

---

## § CRO risk position

**Decision: VETO. Size: 0.0. No capital allocation. No counted trial.**

The risk contract requires a conjunctive gate: cost-pass AND volatility-control t≥2.00. This gate defines the minimum credible evidence for an edge. **The intersection of (cost-pass AND t≥2.00) is EMPTY across the entire 8-cell selection surface.**

**The arithmetic:**
- Cost gate: 2 of 8 cells clear margin > 0 (V1 EURUSD +0.14, V1 USDJPY +1.18). EURUSD +0.14 pips is within any realistic cost-estimation error band on a spread+0.80 hurdle; treat as not robustly positive.
- Volatility-control gate: every V1 relvol t-stat is below 2.00 (0.45, −0.16, −0.33, −0.90, +1.15). Both cost-passing cells fail hardest: EURUSD t=0.45, USDJPY t=−0.33. The single positive vol-control reading (+1.15, AUDUSD) sits in a cost-FAILING cell (margin −1.84). Cost survivors lack the statistic; the cell with the best statistic lacks the economics.
- Under H0 (no edge), across 8 pair-candidate cells, max |t|=1.15 is fully consistent with pure noise even before any 8-cell multiplicity correction. No correction is needed to reach the verdict.

**CRO blowup-analog:** The apparent payoff is a volatility-harvesting signal in a volume costume. The USDJPY stratification is the tell: profit concentrates in the high-relvol × HIGH-RANGE cell (+6.03 pips), not the volume-without-volatility cell (−0.45 pips). A strategy whose in-sample profit co-locates with the volatility-clustering cell is structurally long realized-vol: it harvests calm-to-storm transitions in-sample and pays the tail when the storm gaps against the position. This is the carry-trade failure shape (steady small wins, episodic large loss) and the LTCM/short-vol family of analogs — precisely the pattern the t≥2.00 vol-control gate exists to reject.

**CRO recommendation:** Do NOT advance either family to a pre-registered backtest. If the firm wants to pursue the genuine signal hinted at, it is a VOLATILITY/RANGE conditioning hypothesis — not a volume one — and must be proposed fresh, pre-registered against the range variable directly, and screened with the same conjunctive gate. That is a new hypothesis, not a rescue of this one. Spending honest-N on a candidate the firm's own contract disqualifies a priori is a governance blowup-analog, not just a P&L one.

---

## Signatures

| Role | Verdict | Signed |
|------|---------|--------|
| quant-researcher | implement (V1, V2 declarative designs authored; honest prior of FAIL embedded; tick-vs-volatility caveat and orthogonality argument made; descriptive probe grounded) | @fintech-org-qr-2026-06-24 |
| quant-developer | implemented-and-verified (C2COST fixed + asserted; volume screen executed; vol-control regression + 2×2 stratification run) | @fintech-org-qd-2026-06-24 |
| head-of-quant-research | KILL / FAMILY-CLOSED (V1: cost-kill ≥3/5 + vol-control FAIL all 5; V2: cost-FAIL all 3 + construction void + vol-control FAIL all 3; strategic meta-call: existing-data exhausted, binding constraint = data capability) | @fintech-org-hoqr-2026-06-24 |
| cro | VETO / size 0.0 (conjunctive gate EMPTY; volatility-harvesting in volume costume; spending honest-N here is a governance blowup-analog) | @fintech-org-cro-2026-06-24 |
| null-hypothesis-tester | noise-indistinguishable (relvol t<2.00 all 8 cells; USDJPY edge is the volatility cell; two cost-PASS labels are selection artifacts; CONCURS kill; DISSENTS on "progress" framing and data-spend inference — verbatim preserved above) | @fintech-org-nht-2026-06-24 |
| principal-reviewer | approve-with-conditions (C2COST fix correct + scoped to C2; no-lookahead clean; vol-control OLS sound; 4 headline numbers reproduced exact; 0 blocking; F-002 and F-004 as forward conditions) | @fintech-org-pr-2026-06-24 |
| pm | synthesis-complete (NHT dissent preserved verbatim; PR findings first-class; OPEN-ITEM-C2COST closed; strategic meta-call recorded prominently; no technical calls) | @fintech-org-pm-2026-06-24 |

---

## Knowledge gaps surfaced

The following are role-level data and scoping limitations surfaced in session artifacts. They are NOT installable skill gaps. **Installable-skill-gap count N = 0.** No new entries appended to `.fintech-org/skill-gaps.jsonl` this session. All gaps below are data-acquisition or scoping gaps — they can only be resolved by acquiring new data or commissioning new hypothesis work.

| Gap | Source | Resolution path |
|-----|--------|----------------|
| Broker tick-volume is a count of price updates (OTC FX, no consolidated tape), not traded notional. This is a DATA-CLASS limitation, not a measurement artifact. No re-parameterization of the existing `volume` column can resolve it. | QR, QD, HoQR, CRO, NHT | Data acquisition: true traded volume / order-flow (CME FX futures volume, CLS settlement data, L2 depth feed). Not an installable skill gap. |
| Access, cost, latency, and licensing terms for candidate data classes (CME FX futures, CLS, L2 depth providers) are not yet scoped. | HoQR | Requires commercial due diligence. Not an installable skill gap. |
| Whether a structurally-new existing-data hypothesis class exists that is NOT a relabel of F1–F6 / C1 / C2 / volume. HoQR does not see one but cannot prove non-existence. | HoQR | Option-2 reactivation gate (b) accounts for this. Not an installable skill gap. |
| V2 mean-reversion gross edge was unprobed by QR (required session-open anchoring QD had to build). V2 was disqualified on construction-void before this gap mattered. | QR | Moot for this cycle; relevant only if a future intraday re-attempt is commissioned. Not an installable skill gap. |

---

## Open items requiring Board acknowledgment

**(a) THE STRATEGIC FORK (primary; requires CEO decision):** HoQR's strategic meta-call establishes that the existing-data screening space is exhausted. The Board must choose between two postures:

- **Option 1 (Data-capability acquisition):** Authorize a data-diligence phase for true volume / order-flow / intraday tick data. HARD PRECONDITION: a written, falsifiable, data-REQUIRING hypothesis must be authored and cleared before any acquisition spend. HoQR recommends this path only if such a hypothesis can be written and cleared. NHT's guardrail: the volume null result does NOT itself constitute the hypothesis or justify the spend.
- **Option 2 (Wind down to observe-only / maintenance):** Freeze active new-strategy generation on existing data. Preserve the falsification corpus. Gate reactivation on new data arriving or a structurally-new hypothesis class. This is the honest default if Option 1's precondition cannot be met.

**Options 3 (carry on longer history) and 4 (more existing-data generation) are low-priority and EV-negative, respectively, per HoQR.**

**(b) PR Forward condition F-002 (future CPCV commitment):** Any future committed CPCV backtest using a volume-relative signal MUST replace the full-sample seasonal norm with a rolling/expanding past-only norm. The full-sample norm is the more restrictive selector (conservative for this kill verdict), but would bias a future backtest. Owner: quant-researcher. Board acknowledgment sufficient; no action required until and unless a future volume-class candidate is commissioned.

**(c) PR Forward condition F-004 (intraday re-attempt design note):** If the volume lever is ever revisited on intraday data, the V2 session-open anchor must be fixed to a genuine trading-session open (not UTC calendar-date midnight bar). The midnight anchor made the extension gate near-vacuous (~587 fires/yr vs 40–80 expected). This does not change this cycle's verdict (construction ratio 1.25–1.54 >> 1.2 = DISQUALIFIED regardless). Owner: quant-researcher. Action required only if a future intraday volume-class hypothesis is commissioned.

**(d) OPEN-ITEM-C1FILTER (carried forward from prior cycle):** C1 surprise filter remains non-binding under the max-TR bar-attribution rule. Requires verified ECB/BOE release timestamps. Status: held pending decision on Option 1 above.

---

## Prior decisions NOT made / carry-forward items

- **OPEN-ITEM-C1FILTER:** Unresolved. Requires ECB/BOE verified decision timestamps. Not in scope this cycle. Held pending the strategic fork decision.
- **H1 un-freeze:** FORBIDDEN. No CD0 net SR ≥ 1.76 candidate exists. No change.
- **GBPJPY acquisition:** Remains on hold per HoQR R3 ratified in the 9-pairs CONSENSUS.
- **F1–F6 canonical families:** Remain retired-as-saturated.
- **C1 (CB-decision drift):** Remains retired (regime artifact; OPEN-ITEM-C1FILTER unresolved).
- **C2 (carry multi-session hold):** Remains killed as-run. OPEN-ITEM-C2COST now CLOSED.
- **honest-N:** Remains 30. No increment this cycle.

---

*This CONSENSUS.md is the audit-trail source-of-truth for the 2026-06-24 volume-conditioned-screen wave. Append-only per protocol. No section may be softened, reordered, or omitted in future revisions — only new sections may be appended.*
