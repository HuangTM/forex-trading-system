# QRB-6 CONFIRMATORY PRE-REGISTRATION — Single-Structure Forward Re-Test of the CB Scheduled-Decision Event Study (FX)

**Document status:** DRAFT v1 (2026-06-07) — QR PART I authored; Mathematician PART II sections are `[SECTION OWNED BY MATHEMATICIAN — merged at assembly]` placeholders (SR0/N_sel=1 derivation, look design single-vs-2-look, power/look-date, kill_switch_threshold, seed/K). Becomes BINDING and FROZEN only on consensus ratification (QR + Mathematician + NHT + principal-reviewer) + CEO sign-off + an EXTERNAL write-once freeze-receipt (SHA-256 of this file as committed + pinned code-commit hash). **No post-2026-04-06 return data may be examined and no metric computed before the freeze-receipt is committed.**

**Track:** `qrb6-confirmatory-2026-06-07` / Phase 1 / Task 1.0
**New Trial ID:** `53981a4a` (org-wide counter increment; registered at authoring spawn in `.fintech-org/trials.jsonl`, trial-count-at-spawn = 42. This trial NEVER reuses the exploratory id `fa0f982a`, nor the R5 family `576746aa`, nor the R5-confirmatory `f2fb41fd`.)
**Spawned by:** QRB-6 exploratory (trial `fa0f982a`) terminal outcome **RULE_4_AMBIGUOUS** (2026-06-07), per the frozen exploratory §4.2 RULE 4 → confirmatory-or-wind-down gate; CEO elected the confirmatory branch.
**Authoritative parent (IMMUTABLE — referenced, never edited):** `references/pre-registrations/qrb6_cb_event_study.md` and its result `references/pre-registrations/qrb6_cb_event_study.STEP-RESULT.yaml`; lineage receipt `references/pre-registrations/qrb6_cb_event_study.FREEZE-RECEIPT.yaml` (prereg_sha256 **`7438b0a115709ba041126b05c27fb2bdd44335d2b9010709fb253aa4dc9a9758`**, code_commit `563c3553f6e87ac66b391b2ce9c1e03782f9a9c3`).
**Acceptance criteria:** `.fintech-org/artifacts/2026-06-07T-qrb6-confirmatory/pm-acceptance-criteria.yaml` (QR owns CONF-structure, CONF-holdout, CONF-decision-map; co-signs CONF-holdout with Mathematician).
**Cost manifest (immutably frozen, reused verbatim):** `config/cost_freeze_qrb6.yaml` (sha256 **`6ec6937e6a8de84e32c49001c68d0335cc72b5c2932676eba73f4f6514c8b283`**).

---

## 1. Preamble & Confirmatory-Grade Contract (QR) — criterion CONF-structure context

### 1.1 What this pre-registration IS

This document is a **confirmatory-only statistical test of ONE pre-specified structure** — the QRB-6 central-bank scheduled-decision event study **exactly as executed in trial `fa0f982a`** — on **unsnoopable future data that does not yet exist at freeze time** (CB decisions strictly after 2026-04-06, with their accompanying forward OHLCV). It is spawned by the exploratory's terminal **RULE_4_AMBIGUOUS** outcome, which the CEO has resolved under the exploratory's frozen RULE-4 branch into **exactly one permitted forward action: a fresh, separately-pre-registered confirmatory re-test of the single surviving structure**, with no exploration, no parameter search, and no capital.

The exploratory result was AMBIGUOUS in a specific, diagnosable way (disclosed in full as the motivation, §1.3): **both p-gates cleanly rejected** the null — `p_post2015 = 0.0027` and `p_agg = 0.0231`, on a pooled annualized Sharpe of **1.352** — **but the Deflated-Sharpe-Ratio gate did NOT clear**: `DSR = 0.907 < 0.95`. The DSR shortfall was driven **entirely by the selection-deflation charge** carried in the exploratory at `N_sel = 3` (the 11-proposal paper-portfolio + 2-finalist QRB-6-vs-QRB-3 comparison). That is, the *evidence of an edge* rejected the null twice over; the *gate* failed only because the exploratory was charged for the selection that produced the hypothesis. This is precisely the artifact a confirmatory is built to resolve: by **pre-committing the single structure NOW, before any forward data exists**, the new look carries **`N_sel = 1`** — there is no finalist comparison and no portfolio selection at evaluation time, so the selection-deflation charge that sank the exploratory is removed for THIS look, and the test becomes a clean binary on whether the structure earns a net-of-cost edge on data the firm cannot have snooped.

This pre-registration freezes — before any forward return is read — every degree of freedom: the exact structure and its parameter pins (§2, pinned IDENTICAL to `fa0f982a`), the forward hold-out event-set rule and forward-acquisition obligation (§3), the null/statistic/N_sel=1 selection charge and the look design (Mathematician PART II), the decision map under every outcome at every look (§4), the kill-switch threshold (§5, Mathematician-derived), the interim observe-only state (§6), and the freeze mechanics (§7). Freezing these on not-yet-existing data is what makes the resulting p face-valid. This is the Lopez de Prado discipline: the pre-registration is the contract; a peek voids it.

### 1.2 What this pre-registration is NOT

- **NOT an exploration.** No window scan, no parameter search, no event-identification snooping, no new bank, no new pair, no new variant. The structure is pinned verbatim from `fa0f982a` (§2). Genuinely-new alpha hypotheses require their own fresh pre-registrations (§6 capacity redirect).
- **NOT a re-run or re-interpretation of `fa0f982a`.** This document never edits, re-runs, or re-interprets the exploratory on any window. `fa0f982a` is frozen, COMPLETE, and immutable. This is a NEW trial (`53981a4a`) on NEW data.
- **NOT a rescue of the AMBIGUOUS exploratory.** A confirmatory PASS does NOT retroactively convert `fa0f982a`'s AMBIGUOUS into a PASS, and does NOT itself authorize capital. It authorizes only a named, governance-gated next step — a fresh observe-only paper canary under its own ratification (§4 outcome 1). The base-rate honest expectation, given the power reality (Mathematician PART II), is that a ~30-event/yr forward CB calendar will take multiple years to accumulate adequate power and may well fail.
- **NOT a Scenario-B activation.** Scenario B (BOE/ECB/RBNZ) is out of scope: the C4 verified-official certification for those banks was never completed (`fa0f982a` §3.5 left Scenario B DORMANT at `partial`). This confirmatory tests the Scenario-A structure only.

### 1.3 Lineage & exploratory result echo (the motivation, disclosed)

```
QRB-6 exploratory trial fa0f982a  (CB-event study, Scenario A primary; remediated re-run COMPLETE 2026-06-07)
        │  RESULT: RULE_4_AMBIGUOUS
        │    p_post2015 = 0.0027  (clean reject, < 0.0378 straddle-lower)
        │    p_agg      = 0.0231  (clean reject, < 0.0378 straddle-lower)
        │    sr_ann_pooled = 1.352   (per-bank: FED 2.50 / BOJ 1.44 / RBA 1.24 / BOC 0.42)
        │    DSR = 0.907 < 0.95     (gate FAIL — driven by N_sel=3 selection-deflation charge)
        │    SR0_pp_sel = 0.026861  (N_sel=3, disp 0.50);  kill_switch_threshold = 1.5883 (N_sel=3)
        │  prereg_sha 7438b0a..., code 563c355, master_seed 387992
        │
        │  CEO elects the RULE-4 confirmatory branch (not wind-down)
        ▼
QRB-6 confirmatory trial 53981a4a  (THIS document — SAME structure, FORWARD events, N_sel=1, no capital)
        registered at authoring spawn; org counter at spawn = 42.
```

`53981a4a` is a distinct child trial, not a continuation of `fa0f982a`. The exploratory documents, its FREEZE-RECEIPT, its STEP-RESULT, the cost manifest, and the R5/R5-confirmatory family artifacts are ALL immutable; this document only references them.

**The single governing logic.** The exploratory's *evidence* passed (both p's reject); the exploratory *gate* failed only on the selection charge. The confirmatory removes that charge **legitimately** — not by erasing it, but by pre-committing the one structure before the data exists, so this new look is a single, unselected, one-shot test (N_sel=1) on truly OOS data. A rejection here is **NOT a selection artifact**, because there is no selection event between this freeze and this look. (NHT adjudicates the legitimacy of this N_sel=1 election — see CONF-statistic / NHT-audit.)

### 1.4 VOID conditions (the confirmatory contract)

This pre-registration's result is **VOID and not face-valid** if any of the following occur. These mirror `fa0f982a` §1.4, substituted for the confirmatory context (forward data, N_sel=1):

1. **Early peek (return-data).** Any computation of strategy performance — any return series, equity curve, Sharpe, p-value, or test statistic — on any post-2026-04-06 bar **before** the freeze-receipt is cut and committed to git, and thereafter before a frozen look date (§7, Mathematician's look schedule), voids the test. Row-count / schema / index-timestamp / calendar inspection (admissible for forward-acquisition validation, §3) is NOT a return examination; computing a return IS. **A confirmatory author or runner who peeks at forward return/price-derived performance before freeze voids the test outright.**
2. **Structural deviation from `fa0f982a`.** ANY deviation between this confirmatory's executed structure and the structure as executed in `fa0f982a` (signed-product construction, `K_pre=1`/`K_post=2` windows, `close(D)→close(D+2)` entry-`D+1` convention, the §3.2 pair×bank map, the cost manifest `config/cost_freeze_qrb6.yaml`, the `spread_z=3.0` overlay, exclude-not-impute, `entry_delay_bars=1`, banks-as-blocks stationary block bootstrap, Politis-White auto block-length, `K=10000`) voids confirmatory status. The structure is tested **AS-EXECUTED-BY-`fa0f982a`** (receipt sha `7438b0a...`). No parameter search, no structural variant, no new pair, no new bank.
3. **Snooped event entering the confirmatory set.** Any event on or before 2026-04-06 entering the confirmatory event set, or any in-sample/exploratory-window event (any event `fa0f982a` saw) entering the confirmatory set, voids the test. The confirmatory event set is strictly post-2026-04-06 with **zero overlap** with the exploratory's 2010→2026-04-06 sample.
4. **Manual / unscheduled look.** Any look on the post-2026-04-06 hold-out before the Mathematician's frozen look date(s), any human "let's check it now" evaluation, or any peek-driven look-timing decision voids the test. Evaluations occur ONLY at the frozen look date(s), one-shot, against the committed receipt.
5. **Cross-trial constant import.** Any import or hard-code into the confirmatory runner of a constant from a prior trial — the exploratory's `SR0_pp_sel=0.026861` or `kill_switch_threshold=1.5883` (both N_sel=3), the R5-confirmatory `sr0_pp=0.034921`/`1.2906`, R5 `0.022906`, or any other prior trial's threshold — voids the test. The confirmatory's N_sel=1 thresholds are derived FRESH by the Mathematician in this track (PART II) and are the sole authoritative source.
6. **Wrong trial id / freeze mismatch.** If the run registers under any id other than `53981a4a`, or if `receipt.prereg_sha256 != sha256(this file as committed)` or `receipt.code_commit != pinned commit`, the run executed against an unfrozen/drifted spec and is VOID.

---

## 2. The Structure Under Test — pinned IDENTICAL to `fa0f982a` (QR) — criterion CONF-structure

### 2.1 This is the SAME structure — the only differences are listed in §2.5

The ONLY structure this confirmatory may evaluate is **QRB-6 exactly as executed in trial `fa0f982a`** (frozen at receipt sha `7438b0a...`). Every degree of freedom is **quoted from `fa0f982a`, not redesigned**. No cell, window, sign rule, cost, or overlay is re-opened. The three differences from `fa0f982a` are enumerated explicitly in §2.5 and are confined to (a) the event set is forward/unsnoopable, (b) `N_sel = 1`, and (c) the confirmatory decision gate (Math-owned). Everything else is byte-for-byte the exploratory structure.

### 2.2 The signed-product construction (pinned verbatim from `fa0f982a` §1.2 / §4.2 / §5.0)

The tested quantity is the **signed-product event return** per deduped bank-event `e`:

> **`y_e = sign( close(D,e) − close(D−1,e) ) · R_post,e`**

where:
- **`sign_align_e = sign( close(D) − close(D−1) )`** is the realized-initial-reaction continuation sign, measured on the bank-event's mapped leg (per-bank reference pair, §3.2 ordering). This is the FROZEN sign-alignment rule from `fa0f982a` §5.0 — the firm has no survey/consensus feed, so a surprise-vs-consensus sign is not computable; the realized-initial-reaction continuation rule is the pinned mechanical rule. The strategy bets the bar-`D` initial reaction **continues** through the post-window.
- **`R_post,e`** = the bank-event **equal-weight, net-of-cost cumulative return from `close(D)` to `close(D+2)`** across that event-day's responsive pairs (§3.2), entered at bar `D+1` under `entry_delay_bars = 1`, position held during bars `D+1` and `D+2`.
- **Degenerate tie:** if `close(D) = close(D−1)` exactly (measure-zero), `sign_align_e = 0`, position FLAT, event EXCLUDED from the realized return; its event-day still counts as a block-day for bootstrap block construction.

**No-lookahead (pinned).** `sign_align_e` uses `close(D)` and `close(D−1)`, both known at the close of bar `D`. Entry executes at `D+1` under the engine's sacred `entry_delay_bars = 1` invariant (`test_no_lookahead`). The realized post-window return runs from `D+1` forward and does NOT include the `D−1→D` bar used to form the sign. The bar-`D` reaction is the SIGNAL, consumed at signal-formation time; it is not part of realized P&L. This is identical to `fa0f982a` §5.0.

### 2.3 Window lengths, entry/exit, cost & overlay (pinned verbatim from `fa0f982a` §4, §5.5)

| Degree of freedom | Frozen value (IDENTICAL to `fa0f982a`) | Source in `fa0f982a` |
|---|---|---|
| Pre-window | `K_pre = 1` daily bar (bar `D−1`); sign-alignment input ONLY, not source of edge | §4.2 |
| Post-window | `K_post = 2` daily bars; cumulative net return `close(D) → close(D+2)` | §4.2 |
| Entry/exit | entry at `D+1` under `entry_delay_bars = 1`; exit at frozen post-window end; no discretionary/trailing exit | §4.3 |
| Decision-reflecting bar | bar `D` (00:00-UTC-stamped daily OHLC for UTC day `D`) is the first bar whose close reflects the decision, for ALL banks (conservative no-leak convention) | §4.1 |
| Unit of observation | deduped **bank-event-day**; per-event scalar = equal-weight average of sign-aligned net-of-cost returns across the event's responsive pairs | §3.2, §3.3 |
| Block structure | **banks-as-independent-blocks** stationary/circular block bootstrap; block construction by `bank` label | §3.3, PART II §1.4, §3 |
| Block length | **Politis-White (2004) + PPW (2009)** auto, on the event-day-ordered series; `L = max(1, ceil(L_pw))`, `L ≥ 1` guard | PART II §1.3 |
| Bootstrap reps | `K = 10000` | PART II §1.4 |
| Cost manifest | **`config/cost_freeze_qrb6.yaml`** (sha256 `6ec6937e...`), mechanical per-pair, used verbatim — NO re-derivation, NO per-pair discretion | §3 remediation v2, §5.5 |
| `spread_z` overlay | `spread_z = (spread_pips − trailing_median_60) / trailing_MAD_60`, strictly causal; threshold **`spread_z_threshold = 3.0`**; on entry bar `D+1`, if `spread_z > 3.0` for a pair, that pair's entry is SUPPRESSED (position 0); suppressed events excluded from realized return but their event-day still counts as a block-day | §5.5 |
| Exclude-not-impute | a per-event cost/data gap is a LOUD EXCLUDE counter, never a silent zero; the cost-coverage gate requires **`n_event_cost_or_data_gap = 0`** — every confirmatory event must resolve to a present, positive cost entry for all responsive pairs, or it is excluded loudly | §3 remediation v2, §4.4.3/§5.5 |

The `spread_z` overlay and exclude-not-impute rule carry forward **identically** to the forward event set — the cost-coverage gate (`n_event_cost_or_data_gap = 0`) applies equally to every post-2026-04-06 event.

### 2.4 The exact pair×bank mapping (pinned verbatim from `fa0f982a` §3.2)

The confirmatory uses the **same Scenario-A verified-official banks {FED, BOJ, RBA, BOC}** and the **same pair×bank map** as `fa0f982a` §3.2 — carried verbatim, not re-derived. Each bank-event is sign-aligned and pooled at the bank-event level; the pairs below are the legs on which the bank-event's return is measured:

| Bank | Currency | Mapped firm pairs (legs of the bank-event) | Pairs |
|------|----------|--------------------------------------------|-------|
| **FED** | USD | EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD | 6 |
| **BOJ** | JPY | USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY | 6 |
| **RBA** | AUD | AUDUSD, AUDJPY | 2 |
| **BOC** | CAD | USDCAD, CADJPY | 2 |

Pair-count asymmetry (FED 6, BOJ 6, RBA 2, BOC 2) is disclosed and receives NO bank-level weight correction — the unit is the bank-event, within which the equal-weight average is the frozen convention (`fa0f982a` §3.2). **Scenario B (BOE/ECB/RBNZ) is NOT in scope** (C4 certification incomplete; out of this confirmatory). The ECB `training-memory-unverified` rows remain INADMISSIBLE; the runner MUST filter at load: `df = df[df['verification'] != 'training-memory-unverified']`, verbatim.

### 2.5 The THREE — and ONLY three — differences from `fa0f982a`

This is the SAME structure as `fa0f982a`. The only differences are:

1. **(a) Forward / unsnoopable event set.** The event set is CB decisions strictly AFTER 2026-04-06 (§3), with zero overlap with the exploratory's 2010→2026-04-06 sample. The exploratory tested historical events the firm had already acquired; the confirmatory tests events that **do not yet exist at freeze**.
2. **(b) `N_sel = 1`.** The structure is pre-committed before the look; there is no 11-proposal portfolio, no 2-finalist comparison, no selection at evaluation time. `N_sel = 1`. This removes the selection-deflation charge that produced `fa0f982a`'s `DSR = 0.907 < 0.95`. The Mathematician derives the resulting (lower) `SR0_pp` and `kill_switch_threshold` FRESH at `N_sel = 1` (PART II) — **NOT** copied from `fa0f982a` (`0.026861` / `1.5883`, both N_sel=3) or any prior trial.
3. **(c) Confirmatory decision gate.** The decision functional (PART II) is the confirmatory single-structure gate: a single pre-specified look schedule (single-look or 2-look OBF — Math decides), the N_sel=1 DSR gate, and the PASS/KILL/AMBIGUOUS branches of §4. There is no mandatory post-2015 sub-window KILL branch (the forward window is entirely post-2015 — see §4.5).

Everything else — every parameter, window, sign rule, cost, overlay, and bootstrap convention — is IDENTICAL to `fa0f982a`.

---

## 3. The Hold-Out Event Set & Forward-Acquisition Obligation (QR; co-signed Mathematician) — criterion CONF-holdout

### 3.1 The hold-out window rule (a RULE, not a single date)

> **HOLD-OUT RULE.** The confirmatory event set consists EXCLUSIVELY of central-bank scheduled decisions dated **strictly after 2026-04-06** — the exploratory `fa0f982a` terminus. There is **zero event-day overlap** with any event day the exploratory saw (the exploratory ran 2010 → 2026-04-06, Scenario A `n=506` deduped). No event on or before 2026-04-06 enters the confirmatory test under any circumstance (VOID condition §1.4(3)).

This is a forward rule over data that does not exist at freeze: the hold-out is **unsnoopable by construction because it has not yet been generated**. The forward CB calendar currently terminates 2026-03-19 (842 rows, committed git `62421b6`); the OHLCV terminates ~2026-04. The confirmatory event set is therefore empty at freeze and accrues forward.

### 3.2 Provenance gate — verified-official grade ONLY

Forward events must be **verified-official-grade**, sourced directly from official central-bank pages with the SAME acquisition discipline as the Scenario-A primary in `fa0f982a` §3.1 (FED, BOJ, RBA via official sites; BOC via official schedule press releases). The anti-fabrication discipline is binding: aggregator or training-memory-unverified grade events are **inadmissible** unless a committed spot-check artifact (analogous to `fa0f982a` AC-3a / NHT C4) certifies them. No dates are invented; a bank whose forward official calendar cannot be acquired contributes zero forward events rather than fabricated ones. The runner MUST filter at load: `df = df[df['verification'] != 'training-memory-unverified']`, verbatim (same filter as §2.4).

### 3.3 The FORWARD-ACQUISITION OBLIGATION (a named pre-look step — NOT doable at freeze, NOT part of this wave)

> **FORWARD-ACQUISITION OBLIGATION (pre-look, out of this wave).** BOTH the forward CB calendar (post-2026-04-06 verified-official {FED, BOJ, RBA, BOC} decision dates) AND the forward OHLCV (daily bars for the §2.4 pairs through each look date) MUST be acquired, validated, and committed to git **BEFORE** the Mathematician's frozen look date — and **before any return is computed on any post-2026-04-06 bar**. This acquisition is a named pre-look obligation; it is **NOT doable at freeze time** (the data does not yet exist) and is **NOT part of this authoring wave**. It is a separate post-freeze STEP, gated by the calendar-lock and CEO ack (§7).

Acquisition conventions (pinned to match `fa0f982a`):
- **Forward run-rate:** ~30 verified-official event-days/yr ({FED, BOJ, RBA, BOC} ~8 decisions each per year). The Mathematician converts the required event-count for adequate power into a calendar look date (PART II).
- **Dedup / same-day multi-bank:** same as `fa0f982a` §3.4 — when two banks decide on the same market day it counts as ONE deduped market-day, but each bank's sign-aligned return is measured on its own mapped pairs; the dedup removes double-counting of the market-day in the block structure, not the distinct currency reactions.
- **Roll-forward / non-trading-day endpoints:** same as `fa0f982a` §3.4 / §4.1 — the event-relative window anchors on bar `D` and steps over available daily bars; if a window endpoint falls on a non-trading day with no bar, it uses the next available daily bar (no synthetic bar created). Frozen identically to the exploratory.
- **Cost-coverage gate:** the `n_event_cost_or_data_gap = 0` gate (§2.3) applies to every forward event; any forward event lacking a present, positive cost entry for all responsive pairs is loudly EXCLUDED (exclude-not-impute), never zero-imputed. This is the structural guard that the v1 contamination (3/12 cost coverage) cannot recur on the forward set.

### 3.4 Minimum event-day count for block-bootstrap validity

`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`
*(CONF-holdout Math co-sign: the minimum number of forward deduped bank-event-days required for banks-as-blocks stationary-block-bootstrap validity at the terminal look; the bar-count / event-count gate below which a look is statistically void; the conversion of ~30 verified-official event-days/yr into the calendar look date(s). The look is SKIPPED or declared TECHNICAL_FAILURE below the Math-derived minimum, never a pass.)*

---

## 4. Decision Map (QR) — criterion CONF-decision-map

Every outcome at every look maps to a NAMED firm action. There is **no "inconclusive, keep waiting beyond the final look" branch** — the final look is TERMINAL.

| # | Outcome (at a look) | Condition | Named firm action |
|---|---|---|---|
| **1** | **PASS at a look** | The confirmatory bootstrap p-gate **rejects** H0 at this look's alpha-spending boundary (PART II) **AND** the N_sel=1 DSR gate clears (`DSR ≥ 0.95` at the Mathematician's fresh `SR0_pp` for N_sel=1, equivalently hold-out ann Sharpe `≥ kill_switch_threshold`, §5) | **GRADUATE to a fresh observe-only paper canary — NO CAPITAL on this path.** Author a FURTHER, separately-pre-registered observe-only paper canary (forward live-data paper run, no capital at risk) under its own fresh QR+Math+NHT ratification and its own NEW trial_id. PASS here does NOT authorize capital, does NOT re-open the proposal portfolio, does NOT license exploration, and does NOT retroactively change `fa0f982a`'s AMBIGUOUS outcome. The named gate is: *confirmatory-PASS → fresh paper-canary pre-reg*. |
| **2** | **KILL at the terminal look** | Terminal look reached; the bootstrap p-gate **fails to reject** H0 at the terminal cumulative α | **KILL the structure.** Archive `qrb6_cb_event_study` (the structure) as RETIRED/FALSIFIED in the falsification archive (pointer to this confirmatory pre-reg, its freeze-receipt, and the per-look result artifacts). This fires whether the terminal look was adequately powered or not — low terminal power makes the non-rejection uninformative *as evidence of no edge* but does NOT change the action (binding). **QRB-3 does NOT auto-advance on this confirmatory KILL** (see §4.4). |
| **3** | **Early KILL at an interim look (futility)** | An interim look crosses a pre-registered **futility** boundary downward (ONLY if the Mathematician freezes a futility boundary in PART II) | **Early KILL.** Same archival + retirement as outcome 2, stopped early. If the Mathematician freezes NO futility boundary (or the design is single-look), this outcome does not exist and the test runs to the terminal look regardless. |
| **4** | **CONTINUE to next look** | An interim look crosses neither the efficacy nor (if present) the futility boundary | **Accrue data to the next frozen look.** This is NOT "inconclusive, keep spending" — it is the pre-registered alpha-spending design proceeding to its NEXT pre-frozen look. No new research spend, no capital, no re-parameterization (§6). This branch exists ONLY if the design is 2-look (PART II); it is unavailable at the terminal look (outcome 2 is forced there). If the design is single-look, this branch does not exist. |
| **5** | **TECHNICAL FAILURE** | Code error, data-integrity / provenance fault, freeze mismatch (§1.4(6)), provenance breach (a forward event failing the verified-official grade or the cost-coverage gate), or an unexplained data gap at a look | **HALT, root-cause, re-freeze, re-run.** No confirmatory statistic is read or reported for that look. **The trial counter is NOT incremented** (the confirmatory remains ONE trial, `53981a4a`). After root-cause and a new freeze-receipt, the look is repeated. A masked bug or contamination presented as a fail/pass is itself a VOID. |

### 4.1 PASS requires BOTH gates — and the N_sel=1 gate is the one `fa0f982a`'s 0.907 could clear

A confirmatory **PASS** requires BOTH (i) the bootstrap p-gate to reject H0 at the look's boundary AND (ii) the N_sel=1 DSR gate (`DSR ≥ 0.95`) to clear. This is the load-bearing point of the whole confirmatory: the exploratory's `DSR = 0.907` failed the gate at `N_sel = 3`. At **`N_sel = 1`** the deflation benchmark `SR0_pp` is materially lower (Mathematician PART II derives the exact value), so the **same realized edge that produced `DSR = 0.907` at N_sel=3 would clear `DSR ≥ 0.95` at N_sel=1** — provided the forward edge is real and not a selection artifact. A confirmatory that rejects the p-gate but cannot clear the N_sel=1 DSR gate is NOT a PASS (it maps to AMBIGUOUS — §4.3). The kill_switch_threshold (§5) is the operational restatement of the N_sel=1 DSR gate on the annualized-Sharpe scale.

### 4.2 No keep-spending escape

There is no decision branch anywhere in this document that results in "the structure is inconclusive, so keep researching / keep deferring indefinitely." Terminal states are GRADUATE-to-paper-canary (outcome 1) and KILL (outcomes 2/3). Outcome 4 (if it exists) is bounded by the frozen look schedule and terminates at the terminal look. Outcome 5 returns to a re-frozen re-run, never to free exploration.

### 4.3 AMBIGUOUS at the terminal look

If, at the terminal look, the bootstrap p-gate cleanly rejects H0 but the N_sel=1 DSR gate does NOT clear (`DSR < 0.95`), the terminal outcome is **AMBIGUOUS** — neither PASS nor a clean p-fail KILL. Because this is the **confirmatory** (the test the firm built specifically to resolve the exploratory's ambiguity at N_sel=1, with no further selection charge to remove), a terminal AMBIGUOUS resolves to **wind-down of the QRB-6 structure** — there is no further confirmatory to elect (a confirmatory-of-a-confirmatory would be an unbounded escape, prohibited by §4.2). The structure is archived; QRB-3 does NOT advance (§4.4). *(The exact straddle-band definition of "clean reject" vs "AMBIGUOUS band" on the p-scale, and any MC-SE straddle, is the Mathematician's to freeze in PART II; the firm-action mapping above is QR-owned.)*

### 4.4 QRB-3 advance rule (CONF-grade — DIFFERENT from `fa0f982a`)

> **QRB-3 does NOT auto-advance on ANY outcome of this confirmatory.** In `fa0f982a`, QRB-3 (the queued runner-up) was set to advance ONLY on a **post-2015 KILL** of the exploratory's structure (`fa0f982a` §5.4: "QRB-3 advances to a subsequent wave only on a post-2015 KILL"). That branch was specific to the exploratory's mandatory post-2015 sub-window KILL test. **This confirmatory has no post-2015 sub-window KILL branch** (the forward window is entirely post-2015 — §4.5), so the condition that would have advanced QRB-3 **does not exist here**. A confirmatory KILL (outcome 2), an early futility KILL (outcome 3), or a terminal AMBIGUOUS (§4.3) of `fa0f982a`'s structure **does NOT advance QRB-3**. QRB-3, if ever pursued, requires its own fresh pre-registration and its own trial_id under separate governance.

### 4.5 The post-2015 sub-window concern is MOOT for the confirmatory

`fa0f982a` carried a mandatory post-2015 sub-window KILL (§5.2) because its 2010→2026 sample spanned the documented 2015 structural break in pre-decision drift, and an aggregate pass carried by pre-2015 data would have been dead alpha. **For this confirmatory the concern is structurally moot:** the forward event set is dated strictly after 2026-04-06, so it is **entirely post-2015** by construction. There is no pre-2015 data to carry an aggregate, and no within-sample structural-break split to test. The confirmatory therefore has a **single primary p-gate** on the (entirely-post-2015) forward set — there is no separate post-2015 sub-window KILL branch, and accordingly no post-2015-KILL → QRB-3 graduation branch (§4.4). This is addressed cleanly here so it is not silently read as a missing gate: the gate is not missing; the forward window IS the post-2015 window.

---

## 5. Kill-Switch Threshold (QR adopts; Mathematician derives) — criterion CONF-kill-switch-threshold

The repo pre-commit hook requires every pre-reg file to carry the literal `kill_switch_threshold:` field. The confirmatory threshold is derived **FRESH** by the Mathematician at **`N_sel = 1`** and the confirmatory `T_holdout` (the number of deduped forward bank-event-days expected at the terminal look, ~30/yr × the Math-derived lock horizon). It is **NOT** copied from `fa0f982a` (`1.5883`, N_sel=3) and **NOT** from the r5-confirmatory (`1.2906`, a different study). Different `N_sel` and different `T_holdout` produce a different threshold. QR adopts the value verbatim; HoQR co-signs.

```yaml
kill_switch_threshold: [VALUE FROM MATHEMATICIAN]
```

Semantics: the minimum pooled net-of-cost annualized Sharpe of the sign-aligned forward event series (banks-as-blocks) required, at the terminal look, to clear the confirmatory DSR gate (`DSR ≥ 0.95`) at the N_sel=1 `SR0_pp` and the terminal `T_holdout`. Any value below it fails the gate and cannot produce a PASS (§4 outcome 1; §4.1). No bar executes outside the backtest; the threshold governs the confirmatory decision functional, not a live trading loop.

> **MERGED — see PART II:** the N_sel=1 `SR0_pp` derivation (BLdP `SR0` at N_sel=1, shown arithmetic, NOT copied from `fa0f982a`); the two-pass brentq-style solve for the minimum passing annualized Sharpe at the terminal `T_holdout`; the DSR formula inputs. **The frozen value MUST be strictly different from `1.5883` and `1.2906`.**

# PART II — FROZEN STATISTICAL SPECIFICATION (Mathematician-owned, merged at assembly)

`[SECTION OWNED BY MATHEMATICIAN — merged at assembly]`

The Mathematician owns and freezes, in this PART II:

1. **CONF-statistic — Null, statistic, and N_sel=1 selection charge.**
   - Frozen null `H0: E[y_e] ≤ 0` (no positive net-of-cost post-decision edge on the unsnooped forward event set), one-sided `H1: E[y_e] > 0` on the signed-product scalar `y_e` (§2.2). Same unconditional null on the signed product as `fa0f982a` PART II §1.2.
   - The test statistic and bootstrap mechanics: the HAC-studentized mean (`t = sqrt(n)·mean(y)/omega_hat`, Newey-West Bartlett HAC SE), the **banks-as-blocks** stationary/circular block bootstrap with **`K = 10000`**, **Politis-White** auto block-length, the H0-imposing de-mean recentering `d_e = y_e − mean(y)`, and the `p = (1 + #{t*_b ≥ t_obs})/(K+1)` convention — **same machinery and estimator conventions as `fa0f982a` PART II §1.3–§1.4 / §3**, pinned on the forward hold-out series.
   - **N_sel=1 election + fresh `SR0_pp` derivation (shown arithmetic, NOT copied from `fa0f982a`'s `0.026861`).** The rationale: the structure is pre-committed before the look, no finalist comparison, no portfolio selection at evaluation time — the selection-deflation charge that produced `fa0f982a`'s `DSR=0.907` is removed because that charge attaches to the *selection event* (the 11-proposal → 2-finalist → QRB-6 selection), which was already spent by `fa0f982a`; the confirmatory runs the pre-committed structure on unseen data, so no NEW selection charge attaches to THIS look. NHT adjudicates this election (NHT-audit).
   - The decision functional mapping bootstrap-p + DSR to PASS / KILL / AMBIGUOUS, including any straddle band on the p-scale.

2. **CONF-interim — Look design (the most important design decision) + power.**
   - **Single-look vs 2-look OBF** decision and justification. The carry confirmatory used 2-look OBF (looks at +2.5yr/+5yr of daily bars, Lan-DeMets `sfLDOF`), but the QRB-6 event rate is ~30 events/yr (not ~252 bars/yr), so the look horizon may differ materially — the Mathematician decides whether 2-look OBF or single-look is appropriate given the power reality at ~30 events/yr.
   - The **planning Sharpe** (an honest haircut/decay of the exploratory's pooled in-sample `1.352`, which is selection-biased upward — the Mathematician decides the decay; the carry confirmatory used `SR_plan = SR0_ann_conf` as the conservative anchor).
   - The **power curve** at each planned look, stated in **event-days AND calendar years**, → the **lock horizon / frozen look date(s)**.
   - If 2-look: the alpha-spending function (Lan-DeMets `sfLDOF` recommended, matching the carry pattern), per-look boundaries, and information fraction. If single-look: explicit justification and the single committed look date. The terminal look is declared BINDING (no extend, no re-parameterize). NHT reviews the power statements.

3. **CONF-kill-switch-threshold — fresh derivation at N_sel=1.**
   - `kill_switch_threshold = [VALUE FROM MATHEMATICIAN]` — the minimum terminal-look pooled annualized Sharpe clearing `DSR ≥ 0.95` at the N_sel=1 `SR0_pp` and the terminal `T_holdout` (= ~30 event-days/yr × lock-horizon years). Two-pass brentq-style solve (same discipline as the carry confirmatory PART II §4), DSR formula inputs stated. **Strictly different from `1.5883` and `1.2906`.**

4. **Run mechanics — seed / K / estimator pins.**
   - **Master seed** derived from the new trial stem `53981a4a` via the same hex-mod-1e6 convention as the r5-confirmatory (`int(first 6 hex chars, base 16) mod 1_000_000`).
   - `K = 10000`; banks-as-blocks stationary block bootstrap; Politis-White auto block length, `L ≥ 1` guard; estimator conventions (`mean/std(ddof=1)·sqrt(252)`; `scipy.stats.skew/kurtosis` bias=True; `hac_se_nw` Bartlett; DSR `Phi=scipy.stats.norm.cdf`, `Z⁻¹=norm.ppf`; scipy REQUIRED, absence → TECHNICAL_FAILURE) — mirroring `fa0f982a` PART II and the r5-confirmatory PART II §5.

---

## 6. Interim Monitoring State (QR) — criterion CONF-monitoring

Between the freeze date and each frozen look date, the QRB-6 structure is in **observe-only** state. The no-peek discipline below is a VOID condition (§1.4(1),(4)).

1. **No new research spend on the QRB-6 structure.** No new variant, no new bank, no new pair, no parameter search, no re-test of `fa0f982a`'s structure on any dataset.
2. **No new variant / bank / pair search.** The structure is frozen; the only forward activity is passive data accrual (item 3) and the named forward-acquisition obligation (§3.3), which is a pre-look acquisition step, not an evaluation.
3. **Data pipeline keeps accruing passively.** The forward CB calendar updates and forward OHLCV ingestion continue as **passive accrual** — NOT evaluation. Acquiring and validating forward verified-official events and bars (schema/index/row-count/provenance checks) is admissible and is the §3.3 obligation; computing any strategy return on those bars is NOT.
4. **Quarterly mechanical data-integrity checks WITHOUT computing any strategy return or statistic.** Each quarter, run the data-provenance/bounds checks on the forward price data and log the result. This records DATA health only (early-peek-safe; analogous to the carry-confirmatory interim monitoring pattern). It does NOT compute the strategy's return series, Sharpe, P&L, or any test statistic — doing so is an early-peek VOID (§1.4(1)).
5. **Active research capacity redirected to genuinely-new alpha hypotheses.** Those are SEPARATE tracks, out of scope for `53981a4a`, each requiring its own fresh pre-registration. Nothing is unfrozen by default under the firm's zero-validated-alpha posture.

The no-peek discipline — **no statistic on post-2026-04-06 data before a frozen look date** — is stated as a VOID condition (§1.4(1),(4)).

---

## 7. Freeze Mechanics (QR) — criterion CONF-freeze

The freeze-receipt is an EXTERNAL write-once file, cut via `scripts/cut_freeze_receipt.py --target qrb6_confirmatory --cut` (the `qrb6_confirmatory` receipt target is registered by the Quant Developer per CONF-qd-runner, analogous to the confirmatory target added for r5). The receipt records: (a) SHA-256 of THIS file as committed; (b) the pinned code-commit hash for the QRB-6 execution path; (c) the new trial_id `53981a4a`; (d) the N_sel=1 `SR0_pp`, the `kill_switch_threshold`, and the frozen look date(s) (all Mathematician-derived); (e) the cost-manifest sha `6ec6937e...`. This file does NOT embed its own hash (F-003 pattern — embedding makes verification circular).

**Receipt-before-any-return-data (binding).** The freeze-receipt is committed to git **BEFORE** any post-2026-04-06 hold-out data is accessed for performance, and before any metric is computed. The runner is **REFUSE-WITHOUT-RECEIPT**: it MUST verify the committed freeze-receipt (SHA-256 of this pre-reg + pinned code commit) before touching any hold-out return, mirroring `scripts/cut_freeze_receipt.py` and the `fa0f982a` / r5-confirmatory runner pattern.

**Calendar-lock + one-shot look as a separate post-freeze STEP.** After the freeze-receipt is committed, the structure is calendar-locked until the Mathematician's frozen look date(s). The forward-acquisition obligation (§3.3) and the one-shot look are **separate post-freeze STEPs, each gated by the calendar-lock and a CEO ack** at that time. Each look is a single logged one-shot against the frozen receipt; no "re-run with a tweak" path preserves the pre-registration. The terminal look is TERMINAL (§4).

---

*Mathematician-owned PART II sections (CONF-statistic, CONF-interim, CONF-holdout co-sign §3.4, CONF-kill-switch-threshold derivation) are merged at assembly. NHT audit and principal-reviewer review precede CONSENSUS; CEO ratification precedes the freeze-receipt cut. QRB-6 confirmatory consumes trial `53981a4a` (org counter 42); no capital is authorized on any branch.*
