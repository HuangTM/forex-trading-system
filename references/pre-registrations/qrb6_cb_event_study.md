# QRB-6 PRE-REGISTRATION — Central-Bank Scheduled-Decision Event Study (FX)

**Document status:** REMEDIATION-AMENDED v2 (2026-06-07) — v1 frozen run VOIDED (cost-config contamination); re-run binds the tightened OBF extra-look gate (p_reject 0.0378 / KILL 0.0422) + the mechanical cost manifest + exclude-not-impute. Re-cut receipt supersedes the voided one. See the REMEDIATION AMENDMENT v2 box below.

> ## ⚠ REMEDIATION AMENDMENT v2 — 2026-06-07 (binds this re-run; supersedes the voided v1 freeze where they differ)
>
> **The first one-shot run of trial fa0f982a was VOIDED.** It executed on a CONTAMINATED event set: the cost configuration covered only 3 of the 11 Scenario-A pairs, so RBA (AUDUSD/AUDJPY) and BOC (USDCAD/CADJPY) events — ~44.5% of the full set and ~50.7% of the post-2015 sub-window — were ZERO-IMPUTED into the pooled statistic instead of computed or excluded. Adjudicated VOID under §1.4 (parameter drift) by NHT + Mathematician (`nht-run-integrity-adjudication.yaml`, `math-bias-analysis.yaml`): the recorded `RULE_1_KILL_POST2015` is UNINTERPRETABLE (the corruption biases toward KILL AND degrades the banks-as-blocks bootstrap; kill-monotonicity NOT-PROVABLE). The void run's numbers (`p_agg=0.0791`, `p_post2015=0.2158`, `dsr=0.768`) are preserved in `*.STEP-RESULT.VOIDED-CONTAMINATED.yaml` and DISCLOSED here as contamination.
>
> **Binding remediation (NHT-ratified, `nht-remediation-ratification.yaml`), in force for the re-run:**
> 1. **Mechanical cost rule** — per-pair costs are frozen in `config/cost_freeze_qrb6.yaml`, derived mechanically (no per-pair discretion) as `spread_pips = round(median(data/spreads/{PAIR}_daily_spreads.parquet), 2)`, uniform `slippage = commission = 0.5 pips`, `swap = −1.5 pips/day` both sides, with the USDCAD fractional-pip unit corrected (raw 45.0 ÷10 = 4.50). NHT re-verified 9/9 medians; the cost lever moves the statistic only ~0.31 t-units vs a 0.84 t-unit gap to KILL, so the post-exposure cost choice cannot flip the verdict.
> 2. **EXTRA-LOOK PENALTY (the gate below is TIGHTENED).** Because the void run was a look at the data, the re-run is treated as a 2-look design (O'Brien-Fleming spend, info-fraction t1=0.5; look-1 spend `1−Φ(1.6449/√0.5)=0.010005`; look-2 nominal `α_look2 = 0.05−0.010005 = 0.039995`). The frozen p-gates for the re-run are therefore: **PASS requires strict `p < 0.0378`** (`= α_look2 − MC-SE 0.0022`); **KILL requires strict `p > 0.0422`** (`= α_look2 + MC-SE 0.0022`); **CLOSED straddle `[0.0378, 0.0422]` → RULE 4 AMBIGUOUS**. These SUPERSEDE the original single-look `0.0478 / 0.0522` throughout §4.2/§5/§7. `N_sel = 3`, `DSR ≥ 0.95`, `SR0_pp_sel = 0.026861`, `kill_switch_threshold = 1.5883`, `master_seed = 387992`, `K = 10000`, `spread_z = 3.0` are UNCHANGED (the selection charge and the look penalty are orthogonal — no double-count).
> 3. **EXCLUDE-not-impute** (§4.4.3/§5.5) is enforced in code; a per-event cost/data gap is now a LOUD counter, never a silent zero. A committed cost-coverage gate in `cut_freeze_receipt.py` REFUSES to cut a receipt unless all 11 Scenario-A pairs resolve to a present, positive cost entry (the structural fix for the gap that survived 7 review checkpoints).
>
> **Trial accounting:** fa0f982a is the same (already-burned) trial; this is its single remediated re-run, NOT a new trial (counter stays 41). QRB-3 did NOT auto-advance on the voided KILL. Everything below this box is the original v1 text with the v2 threshold values applied; where any v1 prose conflicts with this box, THIS BOX governs.

**Track:** `qrb6-prereg-2026-06-06` / Phase 1 / Task 1.0
**Trial ID:** `fa0f982a` (org-wide counter; registered at authoring spawn per charter step 3 — `.fintech-org/trials.jsonl`, trial-count-at-spawn = 41. This trial NEVER reuses any prior trial id, in particular not R5's `576746aa` nor the R5-confirmatory `f2fb41fd`.)
**Acceptance criteria:** `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/pm-acceptance-criteria.yaml` (QR owns AC-1)
**Calendar dataset:** `data/rates/cb_decision_dates.parquet` (842 rows; committed git `62421b6`)
**Provenance:** `references/cb_decision_dates_PROVENANCE.md`

---

## 1. Preamble & Confirmatory-Grade Contract (QR) — criterion AC-1(i)

### 1.1 What this pre-registration IS

This document freezes — **before any FX return series is examined** — every degree of freedom of a **pooled, banks-as-blocks event study** of FX behavior around **scheduled central-bank rate decisions**. The trigger is the announcement DATE/window read from an externally-acquired, provenance-graded decision calendar; the test is whether a pre-specified, sign-aligned event-window strategy earns a net-of-cost edge that is statistically distinguishable from zero, and — the question that actually governs deployment — whether any such edge **survives in the post-2015 sub-window**.

Freezing the event set, the pair×bank mapping, the entry/exit window length, the primary statistic, the multiplicity charge, the kill thresholds, and the QRB-2 overlay **before** any return is read is what makes the resulting p-value face-valid. This is the Lopez de Prado discipline: the pre-registration is the contract; a peek voids it.

### 1.2 What this pre-registration is NOT

- **NOT an exploration.** No window scan, no parameter search, no event-identification snooping. The event dates are unambiguous calendar facts (scheduled decisions, emergency actions excluded at acquisition). One frozen pre-window length, one frozen post-window length, one frozen entry/exit convention.
- **NOT a multi-trial wave.** This consumes the firm's single authorized trial (BC-1). QRB-3 is the queued runner-up; it does NOT register here and advances only if QRB-6 fails its mandatory post-2015 kill (§5.2).
- **NOT a validation shortcut.** A pass authorizes only a named, governance-gated next step (§5.6 retirement/graduation map); it does NOT authorize capital. The firm's posture is zero validated OOS alpha; the honest base-rate expectation, given the documented post-2015 decay (§2.3), is that the post-2015 sub-window is the most-likely point of failure.

### 1.3 Trial echo & lineage

```
Trial fa0f982a  (THIS document — QRB-6 CB-event study, Scenario A primary, no capital)
   registered at authoring spawn; org counter at spawn = 41.
```

**Lineage (the chain that produced this pre-reg):**
```
new-alpha kickoff (11-proposal slice-B portfolio; QRB-6 authored)
   │  nht-screen.yaml: QRB-6 conditional-survive (C1 post-2015 kill, C2 no-65% target, C3 banks-as-blocks)
   ▼
HoQR two-finalist selection (QRB-6 vs QRB-3) — QRB-6 picked (hoqr-qrb6-rescreen.yaml: A 4.36 / B 4.48)
   ▼
CRO sequencing (BC-1 one-trial hard cap; CEO "go ahead and push it" authorizes consumption on this track)
   ▼
calendar acquisition (data/rates/cb_decision_dates.parquet, 842 rows, provenance-graded)
   ▼
NHT re-screen pick (nht-qrb6-rescreen.yaml: verified counts 506/345 Scenario A; 716/491 Scenario B;
                    grade admissibility ruling; C2/C4 still blocking pre-reg language/spot-check)
   ▼
THIS pre-registration (Scenario A primary; Scenario B pre-committed automatic extension)
```

### 1.4 VOID conditions (the confirmatory contract)

This pre-registration's result is **VOID and not face-valid** if any of the following occur:

1. **Early peek.** Any computation of strategy performance — any return series, equity curve, Sharpe, p-value, or test statistic — on any `data/processed/{PAIR}_{daily,4h}.parquet` bar **before** the freeze-receipt is cut and committed to git voids the test. Row-count / schema / index-timestamp / calendar inspection (already performed) is NOT a return examination; computing a return IS.
2. **Parameter drift.** Any deviation between freeze and evaluation from the frozen pins in this document — the event set (§3), the pair×bank map (§3.2), the entry/exit window convention and the single frozen pre/post bar counts (§4), the primary statistic and its threshold (§5.1, MATH-owned value), the post-2015 cutoff `2015-01-01` (§3.4), the QRB-2 `spread_z` threshold (§5.5), the `kill_switch_threshold` (§6) — voids confirmatory status. The test runs AS-FROZEN.
3. **Scenario-B manual activation.** Scenario B (§3.5) activates ONLY by the documented pre-committed automatic rule upon completion of the BoE/ECB spot-check (AC-3a / NHT C4). Any human re-decision to "turn on" Scenario B, any peek-driven scenario choice, or any access to Scenario-B return data before the C4 spot-check artifact is committed voids the test.
4. **Cross-trial constant import.** Any import or hard-code into the QRB-6 runner of a constant from a prior trial — `r5_decision.SR0_PP` (`0.022906`), the R5-confirmatory receipt (`sr0_pp = 0.034921`, `kill_switch_threshold 1.2906`), or any other prior trial's pre-registered threshold — voids the test. QRB-6's thresholds are derived fresh by the Mathematician in this track (PART II) and are the sole authoritative source.
5. **Wrong trial id / freeze mismatch.** If the run registers under any id other than `fa0f982a`, or if `receipt.prereg_sha256 != sha256(this file as committed)` or `receipt.code_commit != pinned commit`, the run executed against an unfrozen/drifted spec and is VOID.

---

## 2. Hypothesis, Alpha-Source & Honest Decay (QR) — criterion AC-1(a)

### 2.1 Hypothesis (one sentence)

> **H1:** Around scheduled central-bank rate decisions, the affected currency's pairs exhibit a sign-aligned **post-decision reaction/reversal** structure that earns a net-of-cost edge **statistically distinguishable from zero** on the pooled banks-as-blocks event set — **and that edge persists in the post-2015 sub-window**, not only in the pre-2015 regime.

The null is `H0: E[event-window net return] ≤ 0` (no exploitable post-decision structure); the alternative is one-sided positive on the sign-aligned construction. The exact statistic, studentization, and threshold are the Mathematician's (PART II, §5.1).

### 2.2 Alpha-source — who is on the other side, and why it persists

Scheduled rate decisions are **pre-announced uncertainty-resolution events**. In the run-up, a documented risk-compensation premium accrued (the pre-FOMC drift, Lucca–Moench 2015): investors demanded compensation for holding risk into a known binary, and that compensation showed up as drift. Around and after the announcement, the resolution of uncertainty drives a **reaction** (repricing to the new policy stance) and a partial **reversal** of the pre-event positioning as the risk premium is paid out and over-positioned participants unwind. The counterparties are: (a) hedgers and risk-averse participants who pay to de-risk into the event and buy back after; (b) participants who **avoid** trading the announcement window precisely because realized vol and spreads spike (so any structure is under-arbitraged exactly when it is hardest/most expensive to act on). The persistence argument is structural, not informational: the calendar is a permanent anchor (decisions recur ~8×/yr per bank), and a risk-compensation interpretation does not self-arbitrage away the way a pure information edge does.

### 2.3 Honest decay statement — the component I expect alive vs. dead

**The PRE-announcement drift component is documented essentially DEAD post-2015.** The carried-forward NHT finding (nht-screen.yaml base_rate_note; nht-qrb6-rescreen.yaml) is that the pre-FOMC / pre-decision drift "essentially disappeared after 2015"; 2015 is the documented **structural-break endpoint**, not a sample midpoint. McLean–Pontiff-style post-publication decay (~35% average) is a *lower* bound where structural disappearance has been documented.

Consequently this pre-registration **frames H1 on the component I actually expect alive: the post-decision reaction/reversal dynamics**, NOT the pre-announcement drift. The pre-window is retained only as a sign-alignment / positioning input (§4), not as the source of the claimed edge. And the design makes the **post-2015 sub-window a hard KILL test** (§5.2): an aggregate pass that is carried by pre-2015 data while the post-2015 sub-window fails is dead alpha in the current deployment regime and KILLS the structure. I do not forecast the outcome; I make the test fair and the failure mode machine-checkable.

---

## 3. Event Set & Universe (CONF-grade exactness, QR) — criterion AC-1(b),(k); AC-1(h)

### 3.1 Primary event set — Scenario A (verified-official tier ONLY)

The **frozen primary** event set is **Scenario A**: the verified-official tier only, sourced directly from official central-bank pages with zero corrections (FED, BOJ, RBA via official sites; BOC via official schedule press releases). Pin:

> **`nht_accepted_effective_n: 506`** deduped event-days (full window 2010–2026-04-06).
> **`nht_accepted_effective_n_post2015: 345`** deduped event-days (post-2015 sub-window).

Banks in Scenario A: **FED (all years), BOJ (all years), RBA (all years), BOC (2019+ only)**. Raw bank-events = 528; deduped market-days = 506 (22 same-day overlaps); post-2015 deduped = 345. (Verified by NHT via direct pandas query on the parquet; this pre-reg accepts those counts and does NOT recompute returns.)

**INADMISSIBLE — excluded from every registered event set:** the 43 ECB rows graded `training-memory-unverified` (years 2010, 2017, 2018, 2020, 2021). They may not be relabeled or mixed into any tier without Bloomberg/Refinitiv or the official ECB Governing Council minutes index cross-check. The runner MUST filter at load: `df = df[df['verification'] != 'training-memory-unverified']` — verbatim, tested.

### 3.2 The EXACT pair×bank mapping (frozen)

The calendar carries one `bank` and one `currency` per event row (schema: `bank, currency, date, scheduled, verification, source_tier`). Each bank's decision is mapped to the firm-universe pairs in which **that bank's currency is one leg**. A bank-event is sign-aligned and pooled at the **bank-event level** (§3.3); the pairs below are the legs on which the bank-event's return is measured.

| Bank | Currency | Mapped firm pairs (the legs of the bank-event) | Pairs | Scenario A post-2015 events |
|------|----------|------------------------------------------------|-------|-----------------------------|
| **FED** | USD | EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD | 6 | 89 |
| **BOJ** | JPY | USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY | 6 | 97 |
| **RBA** | AUD | AUDUSD, AUDJPY | 2 | 117 |
| **BOC** | CAD | USDCAD, CADJPY | 2 | 58 |

(Corrected to verified data inventory: {AUDJPY, AUDUSD, CADJPY, EURGBP, EURJPY, EURUSD, GBPJPY, GBPUSD, NZDJPY, NZDUSD, USDCAD, USDJPY}. Phantom pairs GBPAUD, EURAUD, AUDNZD (formerly RBA), EURCAD, GBPCAD (formerly BOC) removed — firm has no data for these. FED and BOJ rows unchanged.) The pair set per bank is the firm-universe subset touching that currency; it is pinned ex-ante and not subject to selection.

**Per-event weighting rule (pinned):** For each bank-event, the bank-event observation is the **equal-weight average of the sign-aligned net-of-cost returns across that event day's responsive pairs** (i.e. the pairs mapped to that bank above). The resulting scalar is the unit pooled into the block bootstrap. Pair-count asymmetry across banks (FED 6, BOJ 6, RBA 2, BOC 2) is disclosed and does **NOT** receive a bank-level weight correction — the unit of observation is the bank-event, and within that event the equal-weight average is the frozen convention. This rule is pinned here; it may not be altered post-hoc (VOID §1.4(2)).

### 3.3 Banks as INDEPENDENT BLOCKS (the unit of observation)

The unit of observation for the primary hypothesis is the **BANK-EVENT (deduped market-day)**, NOT the pair×event. Within one bank-event (e.g. a FED decision), the 6 mapped USD-cross pairs share a single common currency-factor shock; their 6 returns are NOT 6 independent observations (effective independent information ≈ 1–2 factors: currency direction + cross-currency relative response). The pooled block-bootstrap therefore uses **bank-level blocks** (block construction by `bank` label), and **per-bank Sharpe is reported as a secondary metric**. The power calculation MUST be stated in bank-events / deduped market-days, NEVER in pair×event. Block construction methodology, block-length estimation (Politis–White precedent from R5), B replications, seed, and the per-bank secondary metric are the Mathematician's to freeze (PART II).

### 3.4 Same-day multi-bank events & the post-2015 boundary (pinned conventions)

- **Same-day multi-bank handling:** when two banks decide on the same market day (22 such overlaps in Scenario A), it is counted as **ONE market day** for the deduped-market-day total (giving 506 from 528 raw), but the two banks' currencies affect **different** pairs, so each bank's sign-aligned bank-event return is still measured on its own mapped pairs. The pooled unit is the bank-event; the dedup removes double-counting of the *market day* in the block structure, not the distinct currency reactions.
- **Post-2015 cutoff (pinned verbatim):** `post_2015_cutoff: 2015-01-01 (inclusive)`. This is the **documented structural-break endpoint** (disappearing-drift literature), NOT the sample midpoint. Events with `date >= 2015-01-01` form the post-2015 sub-window (345 deduped Scenario A days).
- **Weekends/holidays:** decision dates are official announcement dates (all weekday by construction at acquisition, with documented Monday election reschedulings already normalized in the calendar). The event-relative window (§4) is anchored on the first daily bar that reflects the decision and steps over the available daily bars; if a window endpoint falls on a non-trading day with no bar, the window uses the next available daily bar (no synthetic bar is created). This rule is frozen and applies identically across the full and post-2015 windows.

### 3.4b BOC 2010–2018 gap — disclosed confound (AC-1(h))

BOC contributes **zero events pre-2019** (the 2010–2018 FAD dates could not be acquired from official sources; anti-fabrication rule applied — no dates invented). Therefore BOC is **entirely absent from the pre-2015 sub-window** and contributes only post-2019 events (all 58 BOC events are post-2015). This is a **confound for the structural-break test**: the full-window aggregate and the post-2015 sub-window have *different bank composition* for BOC (pre-2015 has no BOC at all). The structural-break comparison is therefore not a clean within-bank pre/post split for BOC; FED/BOJ/RBA carry the pre-2015 vs post-2015 contrast, and BOC enters only the post-2015 side. Disclosed here so it is not silently read as a regime effect. (RBNZ has the analogous 2010–2023 gap but RBNZ is Scenario-B-only, §3.5.)

### 3.5 Scenario B — pre-committed AUTOMATIC extension (not a new trial)

Scenario B extends the event set to the aggregator-grade tier: **BOE (158 events), ECB aggregator-years (102 events — the 43 TMU rows stay excluded), RBNZ (11 events, 2024+)** — totalling **716 deduped market-days (491 post-2015)**. Scenario B is a **pre-committed automatic extension of THIS trial, not a separate registerable test and not a new trial id.**

> **FROZEN ACTIVATION RULE (no human re-decision, no peek):** Scenario B activates **iff and only iff** the BoE/ECB spot-check (AC-3a; NHT C4: ≥5 randomly sampled BoE years 2010–2024 cross-checked vs BoE MPC minutes, ECB aggregator-years anchor-verified) is **completed and the machine condition `scenario_b_certification == "certified"` is confirmed** in the sidecar artifact `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/qd-spotcheck-sidecar.yaml` (field `spotcheck_result.scenario_b_certification`). The year-by-year spot-check verdict tables backing that field are in the SPOT-CHECK section of `references/cb_decision_dates_PROVENANCE.md`. **The current on-file value is `partial`** — Scenario B is therefore **DORMANT at freeze**; `partial` or any value other than `"certified"` never activates Scenario B. Upon the sidecar field reading `"certified"` (committed to git), the event set EXTENDS automatically to Scenario B per this frozen rule. If the spot-check is NOT certified before the freeze-receipt is cut, the frozen pre-reg declares **Scenario B PENDING C4 certification**, and **no Scenario-B return data may be accessed** until the sidecar `scenario_b_certification == "certified"` condition is committed. The pair×bank map for the Scenario-B banks (BOE→GBP pairs; ECB→EUR pairs; RBNZ→NZD pairs) is pinned at the same time and by the same construction rule as §3.2. No peek-driven or human "activate B" decision is permitted (VOID condition §1.4(3)).

---

## 4. Trading-Window Convention (QR) — criterion AC-1(c),(d)

### 4.1 Daily-bar timestamp convention vs. announcement time (the honest part)

**Schema fact (verified from the index of `data/processed/{PAIR}_daily.parquet`, no returns read):** daily bars are timestamped at **00:00:00 UTC** (tz-aware UTC DatetimeIndex; every observed hour-of-day is 0 — verified directly from the EURUSD_daily index, terminus 2026-04-06). The bar dated `D 00:00 UTC` is the daily OHLC for the UTC calendar day `D`. This 00:00-UTC convention is established by that index check alone; there is no competing CLAUDE.md timestamp note (an earlier draft assumption referenced a "21:00-UTC CLAUDE.md note" that does NOT exist — it originated from a dispatch prompt, not CLAUDE.md, and is struck). Announcements occur **intraday**, at bank-local times, so the daily bar that first REFLECTS a decision differs by bank timezone:

| Bank | Announcement local time (provenance) | Approx UTC | First daily bar that REFLECTS the decision |
|------|--------------------------------------|------------|--------------------------------------------|
| FED | 14:00 ET (decision day D) | ~18–19:00 UTC | Bar **D** (decision lands within UTC day D; close of D captures it) |
| BOC | 09:45 ET (decision day D) | ~13:45 UTC | Bar **D** |
| BOE | 12:00 noon UK (decision day D) | ~11–12:00 UTC | Bar **D** |
| ECB | ~13:45 CET decision + presser (decision day D) | ~12:45 UTC | Bar **D** |
| RBA | ~14:30 AEST (decision day D) | ~03:30–04:30 UTC | Bar **D** |
| BOJ | end of MPM, JST (decision day D), typically pre-noon JST | ~02–04:00 UTC | Bar **D** |
| RBNZ | 14:00 NZST/NZDT (decision day D) | ~01–02:00 UTC | Bar **D** |

For every bank, the announcement occurs within UTC calendar day `D` and **the daily bar `D` (00:00-UTC-stamped OHLC for UTC day D) is the first bar whose close reflects the decision.** This is the silent break point of naive event studies: if one (wrongly) treated bar `D` as PRE-decision, the post-window would secretly include the announcement reaction and leak look-ahead. **Frozen convention: the announcement is realized within bar `D`; the post-decision (reaction/reversal) window therefore begins at the CLOSE of bar `D` and the entry executes no earlier than bar `D+1` under the no-lookahead invariant (§4.3).** No bar before `D` may carry any decision information.

> **Honesty note / residual risk:** because the firm has daily bars only, the intraday timing within day `D` is not resolved. A decision late in UTC day `D` (e.g. FED ~19:00 UTC) is captured by the close of `D`; a decision early in UTC day `D` (e.g. BOJ ~03:00 UTC) is also captured by the close of `D`. Treating bar `D` uniformly as the first decision-reflecting bar is the conservative, no-leak choice for ALL banks; it does not attempt sub-daily precision the data cannot support. The pre-window drift component (documented dead post-2015, §2.3) would in any case require intraday resolution to trade cleanly — another reason the claimed edge is framed on the post-decision component.

### 4.2 Pre/post window lengths — ONE frozen `k` each, no scanning

Two window lengths, both pre-registered ex-ante; **no scan over N**:

- **Pre-window (positioning / sign-alignment only):** the `K_pre = 1` daily bar immediately before the decision-reflecting bar `D` — i.e. bar `D-1`. Used to compute the sign-alignment input (direction of the pre-event move / prior trend proxy), NOT as the source of claimed edge (§2.3). Frozen at `K_pre = 1`.
- **Post-window (the claimed-edge window):** the `K_post = 2` daily bars after the decision is realized — i.e. the cumulative net return from the close of bar `D` to the close of bar `D + K_post` measured on the sign-aligned construction. Frozen at `K_post = 2`. One value, frozen; no optimization over `K_post`.

These two integers (`K_pre = 1`, `K_post = 2`) are frozen here and may not be tuned post-hoc (VOID condition §1.4(2)). The sign-alignment rule (how the pre-window move maps to the post-window position sign) is pinned with the statistic in PART II; the structural commitment — one frozen pre length, one frozen post length, sign-aligned, pooled at bank-event level — is owned here.

### 4.3 Entry/exit & no-lookahead (`entry_delay_bars`) compliance

Entry respects the sacred no-lookahead invariant: a signal formed using information available up to and including bar `t` executes at bar `t+1` (`entry_delay_bars = 1`, the engine default and the `test_no_lookahead` guarantee). Concretely: the position sign is determined from information through the close of bar `D` (the decision-reflecting bar); entry executes at bar `D+1`; the post-window cumulative return runs from the entry through the close of bar `D + 1 + K_post`-equivalent exit, with `K_post = 2` post-decision bars held. No bar carrying the decision's own reaction may be both the signal-formation bar AND part of the realized return without the `entry_delay_bars` shift — the engine enforces this and the runner inherits it. Exit is at the frozen post-window end; there is no discretionary or trailing exit.

---

## 5. Falsification Criteria (machine-checkable, QR) — criterion AC-1(e),(f),(g)

All criteria below are machine-checkable and mirrored in the `.triggers.yaml` sidecar (§7). Every numeric threshold is now STATED DIRECTLY from the frozen PART II values; §4.2 is the authoritative decision functional and these §5 criteria are its prose mirror (no live `[MATH]` token remains, no alternative charge mechanism is described). The single load-bearing reconciliation: the selection-multiplicity charge (`N_sel = 3`) lives in the **DSR gate ONLY** (PART II §2, §4.2, §6); the two p-gates use the **fixed** threshold `p ≤ 0.0378` (= OBF look-2 `α 0.039995 − MC-SE 0.0022`, K=10000; see REMEDIATION AMENDMENT v2). There is NO charge on the p-value scale and NO "registered post-multiplicity-charge alpha" of ~0.0025 — that earlier draft framing is SUPERSEDED by §4.2 and does not appear here.

### 5.0 What is tested (hypothesis identity) and the FROZEN sign-alignment rule — NHT-F2 / NHT-F5

**Component under test (pinned, unambiguous).** Every §5 criterion tests the **POST-decision reaction component**: the `K_post = 2` cumulative net-of-cost return from the close of the decision-reflecting bar `D` to the close of `D + K_post`, entered at `D+1` under `entry_delay_bars = 1` (§4.2, §4.3). The PRE-announcement drift is documented essentially DEAD post-2015 (§2.3) and **NO pre-drift criterion exists anywhere in this document or its sidecar** — neither the primary, the post-2015 KILL, nor the reversal sub-claim references the pre-window as a source of edge. The `K_pre = 1` bar enters ONLY as the sign-alignment input below, never as a tested return. (The `.triggers.yaml` sidecar is being rebuilt in parallel to test this same post-decision `K_post=2` quantity — its prior pre-window/pre-drift primary metric is a known assembly defect, NHT-F2, corrected so doc and sidecar test the identical quantity.)

**FROZEN sign-alignment rule (one mechanical rule, no runtime judgment).** The firm has NO survey/consensus/expectations feed and the calendar carries only `{bank, currency, date}` — so a "surprise vs consensus" or "decision vs expectation" sign is **NOT computable** and is rejected. Rate-change sign is derivable for only some banks and is dominated by HOLDS post-2015, so it is also rejected as the primary mechanism. The pinned rule is therefore the **realized-initial-reaction continuation rule**, computable from the data the firm HAS:

> **`sign_align_e = sign( close(D) − close(D-1) )`** measured on the bank-event's mapped leg (the per-bank reference pair, fixed in §3.2 ordering; for the equal-weight bank-event the same `sign_align_e` scalar is applied to every responsive pair so the bank-event remains one sign-aligned unit). The traded position over the post-window `[D+1 close … D+K_post close]` is **LONG `sign_align_e`** — i.e. the strategy bets the initial reaction realized within bar `D` **continues** through the `K_post = 2` window. If `close(D) = close(D-1)` exactly (measure-zero tie), `sign_align_e = 0` and the event is FLAT (excluded from the realized return; its event-day still counts as a block-day, §5.5 convention).

**What the strategy then claims.** With this rule the registered alpha is a **continuation of the post-announcement initial reaction** (not a reversal of a pre-event move, and not a mean-reversion of the reaction). The §5.3 "reversal asymmetry" sub-claim is the COMPLEMENTARY diagnostic: it asks whether the continuation is partial (the reaction neither fully persists, 0% reversal, nor fully unwinds, 100% reversal) — it does not change the primary's continuation direction.

**No-look-ahead proof (the load-bearing check, NHT-F5).** `sign_align_e` uses `close(D)` and `close(D-1)` — both known at the close of bar `D`. The entry executes at the **open/close of `D+1`** under the engine's `entry_delay_bars = 1` invariant (§4.3, `test_no_lookahead`). The realized post-window return runs from `D+1` forward; it does **NOT** include the `D-1→D` bar used to form the sign. Therefore the sign is formed strictly from information available at-or-before `D` and the traded return is strictly after `D` — no bar is both a sign-input and a realized-return bar without the mandatory `entry_delay_bars` shift. The bar-`D` return (the initial reaction itself) is the SIGNAL, consumed at signal-formation time; it is **not** part of the realized P&L, so using its own sign creates no look-ahead into the `D+1` entry. The genre's silent leak (treating bar `D` as PRE-decision and letting the announcement reaction sneak into the realized window) is closed by §4.1's "bar `D` is the first decision-reflecting bar" convention combined with this rule.

**Compatibility flag (Mathematician sign-off — CONFIRMED).** This sign rule pins PART II §1.1's `sign_align_e` to the realized-initial-reaction-continuation function `sign(close(D)−close(D−1))`. Mathematician sign-off granted (debate-r1-math.yaml + math-convergence-patches.md §4.4): (a) the HAC/block-bootstrap studentization in PART II §1.3–§1.4 is UNAFFECTED — the bootstrap resamples the already-signed scalar `y_e`; PW adapts to the observed autocorrelation of the y_e series regardless of which sign definition is used; recentering `d_e = y_e − mean(y)` correctly imposes H0: E[y_e]=0 on the bootstrap distribution for any stationary series; (b) the one-sided H1: E[y_e] > 0 is correct under the continuation hypothesis — a true post-announcement continuation edge makes the signed product positive in expectation; (c) the unconditional null H0: E[y_e] ≤ 0 is the correct null on the signed product (not a conditional null conditional on the direction of bar D); the bootstrap recentering imposes it correctly. No change to any frozen constant (N_sel, SR0_pp_sel, DSR gate, kill_switch_threshold, master_seed, K, straddle band) follows from the filtration convergence. MATH compatibility: CONFIRMED (§4.4).

### 5.1 Primary falsification criterion (structure owned here; value is MATH's)

> **PRIMARY:** Compute the pooled, sign-aligned (§5.0), net-of-cost POST-decision event-study statistic over the Scenario A deduped event-days (bank-level blocks). The structure FAILS (KILL) iff the pooled bank-blocked stationary-block-bootstrap p-value for `H0: E[net post-decision event-window return] ≤ 0` is **strictly `> 0.0422`** — above the MC-indistinguishability straddle band (PART II §4.2 RULE 2). The 11-proposal portfolio selection charge AND the 2-finalist QRB-6-vs-QRB-3 comparison charge are **NOT** charged on this p-threshold — they are charged via the DSR selection-deflation gate (`N_sel = 3`, §5.7 / PART II §2, §6), so the p-gate threshold stays at the fixed OBF look-2 `0.0378` / `0.0422` straddle bounds. A PASS requires strict `p < 0.0378` (below the straddle band's lower edge) AND the DSR gate (§5.7); a clean p-reject that cannot clear the DSR charge is NOT a PASS (PART II §4.2 RULE 4). A p in the CLOSED straddle band `[0.0378, 0.0422]` is MC-indistinguishable from the look-2 boundary α_look2=0.039995 — it is neither a clean reject nor a clean KILL (→ RULE 4, AMBIGUOUS; never PASS, never KILL). **No directional point target is registered** (see §5.3). §4.2 is the authoritative functional; this is its prose mirror.

### 5.2 MANDATORY post-2015 sub-window KILL (overrides aggregate pass)

> **POST-2015 KILL (mandatory):** The runner computes the SAME primary POST-decision statistic (§5.0 / §5.1) **separately** on the post-2015 sub-window (`date >= 2015-01-01`, 345 deduped Scenario A days) and writes `p_post2015` to the result YAML **before** the decision functional fires. If the post-2015 sub-window does NOT cleanly reject — i.e. **`p_post2015 > 0.0422`** (strictly above the straddle band's upper edge) — the structure is **KILLED, and this overrides any full-window aggregate pass** (PART II §4.2 RULE 1, evaluated FIRST). A `p_post2015` in the CLOSED straddle band `[0.0378, 0.0422]` is AMBIGUOUS (→ RULE 4) — never KILL, never PASS; it too overrides any aggregate-level pass. An aggregate-only pass carried by pre-2015 data is dead alpha in the current regime (§2.3). The component under test in BOTH windows is the POST-decision reaction (the `K_post = 2` window return, §4.2/§5.0) — the documented-dead PRE-announcement drift is NOT tested by any criterion (§2.3, §5.0). The 2015-01-01 cutoff is the documented structural-break endpoint, not the sample midpoint (§3.4). BOC-gap confound disclosed (§3.4b).

### 5.3 Reversal asymmetry — framed WITHOUT a point target (NHT C2)

The post-decision reversal component is tested as: the realized reversal fraction is **statistically distinguishable from BOTH 0% (no reversal) and 100% (full reversal)** — i.e. an exploitable partial asymmetry exists. **NO ~65% point target appears anywhere** in this document or the sidecar (the ~65% figure is unverified — WebSearch-only; NY Fed / ResearchGate WebFetch returned 403 at kickoff). KILL the reversal sub-claim if the realized post-decision reaction fraction is statistically indistinguishable from 0% (no reaction) OR from 100% (full unwind) — i.e. no exploitable partial continuation exists. The two-sided distinguishability test uses the SAME bank-blocked stationary-block-bootstrap machinery (PART II §1.4, §3) at the same fixed gate (a two-sided `p ≤ 0.0378` against each of the 0% and 100% nulls; both must reject for the sub-claim to survive). This is a secondary/diagnostic sub-claim on the post-decision component (§5.0); it does not alter the primary continuation direction or the primary/post-2015 p-gates.

### 5.4 Retirement triggers (machine-checkable)

- `p_post2015 > 0.0422` (strictly, above the straddle band) → **KILL**, `overrides_aggregate_pass: true` (the structural-break kill, evaluated FIRST; §5.2, PART II §4.2 RULE 1). `p_post2015` in `[0.0378, 0.0422]` → **AMBIGUOUS** (RULE 4, never KILL, never PASS).
- `p_agg > 0.0422` (strictly, above the straddle band) → **KILL** (no aggregate edge; §5.1, PART II §4.2 RULE 2). `p_agg` in `[0.0378, 0.0422]` → **AMBIGUOUS** (RULE 4, never KILL, never PASS).
- `reversal_fraction indistinguishable from 0% OR from 100%` → **KILL** the reversal sub-claim (§5.3).
- `DSR < 0.95` at `SR0_pp_sel = 0.026861` (equivalently aggregate-set ann Sharpe < `kill_switch_threshold = 1.5883`, Scenario A) → **no PASS** even when both p's cleanly reject; the rejection cannot clear the `N_sel = 3` selection charge (→ RULE 4; §5.7, §6, PART II §4.2).
- `per_bank_sharpe` floor breach (secondary; advisory) → flagged, advisory unless MATH binds it (no numeric floor is registered as a hard gate; PART II reports per-bank Sharpe as a secondary metric only).
- On any KILL: archive `qrb6_cb_event_study` as RETIRED/FALSIFIED (pointer to this pre-reg, freeze-receipt, result YAML). QRB-3 (queued runner-up) advances to a subsequent wave only on a post-2015 KILL.

### 5.5 QRB-2 spread_z overlay — pre-registered MODIFIER (not a separate trial)

QRB-2 (spread-blowout liquidity gate) attaches to QRB-6 as a **pre-registered modifier**, NOT a separate trial: it does NOT increment the trial counter and does NOT consume a separate trial budget. Frozen specification:

- **`spread_z` definition (frozen):** `spread_z = (spread_pips − trailing_median_N) / trailing_MAD_N`, computed on **trailing past data only** (no look-ahead), from `data/spreads/{PAIR}_daily_spreads.parquet` (schema: `spread_pips`, `hour`, `day_of_week`; tz-aware UTC DatetimeIndex — verified). Trailing window `N = 60` daily bars; `trailing_median_N` and `trailing_MAD_N` are the trailing 60-bar median and median-absolute-deviation, both strictly causal (computed through bar `t-1` for a signal acting at bar `t`).
- **Frozen threshold (pinned constant):** `spread_z_threshold = 3.0`. This named constant is frozen here and may not be tuned post-hoc (VOID §1.4(2)).
- **Suppress-entry semantics:** if, on the entry bar (`D+1`, §4.3), `spread_z > spread_z_threshold` for the pair being traded, **the CB-event entry for that pair is SUPPRESSED (position set to 0)** — the regime is illiquid/unstable and the cost is not worth it. Suppression removes the trade; it does not fade or invert. Suppressed events are excluded from the realized return but their event-day still counts as a market-day for block construction (the block structure is on the calendar, not on whether a given pair traded).

### 5.7 DSR selection-deflation gate — where the multiplicity charge LIVES (stated directly)

The 11-proposal portfolio selection charge AND the 2-finalist (QRB-6 vs QRB-3) comparison charge are charged **entirely through this gate**, NOT on the p-value scale (this REPLACES the earlier draft's "absorbed into the primary alpha (~0.0025)" mechanism, which is superseded by PART II §4.2). The paper-selection multiplicity is frozen at `N_sel = 3` (PART II §2; a paper-selection — nothing was backtested — so `N_sel` charges one real one-shot look + ~2 effective soft-prior framings, NOT R5's data-selection N=6). The deflation benchmark is `SR0_pp_sel = 0.026861` (annualized `SR0_ann_sel = 0.426402`; `N_sel = 3`, dispersion `0.50`; PART II §2.5).

> **DSR GATE:** A PASS requires `DSR ≥ 0.95` at `SR0_pp_sel = 0.026861`, equivalently the aggregate-set annualized Sharpe `≥ kill_switch_threshold = 1.5883` (Scenario A, T=506) / `1.4029` (Scenario B, T=716; §4.2/§6). `DSR < 0.95` → no PASS even with both p-gates cleanly rejecting (→ RULE 4). This is the SOLE locus of the selection-multiplicity charge; the p-gates remain at the fixed OBF look-2 value `0.0378`.

### 5.6 Graduation map (a pass is not capital)

A full PASS (`p_agg ≤ 0.0378` AND `p_post2015 ≤ 0.0378`, both clean rejections outside the straddle band, AND `DSR ≥ 0.95` at `SR0_pp_sel = 0.026861`; reversal distinguishable from both 0%/100% for the reversal sub-claim) authorizes **only** a named next governance step: author a fresh, separately-pre-registered observe-only paper canary under its own HoQR+Math+NHT ratification and its own trial id. PASS here does NOT authorize capital, does NOT re-open the proposal portfolio, and does NOT license exploration. (This is PART II §4.2 RULE 3 restated.)

---

## 6. Kill-Switch Threshold (QR adopts; Mathematician derives) — criterion AC-1(j)

The repo pre-commit discipline requires every pre-reg to carry the literal `kill_switch_threshold:` field. QRB-6's threshold is derived **fresh** by the Mathematician in this track — it is NOT R5's `0.767`, NOT the R5-confirmatory `1.2906`, and NOT imported from any prior trial (VOID §1.4(4)). The derivation must account for: the 11-proposal portfolio selection multiplicity charge, the 2-finalist (QRB-6 vs QRB-3) comparison charge, the explicitly-registered alpha, the power at 506 total / 345 post-2015 deduped event-days, and the banks-as-blocks bootstrap. HoQR/QR adopt the value verbatim.

```yaml
kill_switch_threshold: 1.5883
```

Semantics: the minimum pooled net-of-cost event-study metric (e.g. annualized Sharpe of the sign-aligned pooled event series, banks-as-blocks) required to clear the frozen QRB-6 DSR/decision gate at the registered post-multiplicity alpha and the verified event-day N. Any value below it fails the gate and cannot produce a PASS. No bar executes outside the backtest; the threshold governs the decision functional, not a live trading loop.

# PART II — FROZEN STATISTICAL SPECIFICATION (Mathematician-owned, merged at assembly)

# QRB-6 PRE-REGISTRATION — MATHEMATICIAN FROZEN STATISTICAL SECTIONS

**Track:** `qrb6-prereg-2026-06-06:phase1:task1.0`
**Trial:** `fa0f982a` (org-wide counter increment at freeze; 40 → 41). NEVER reuses R5 `576746aa` or confirmatory `f2fb41fd`.
**Author role:** Quantitative Mathematician
**Owns:** AC-2 (pm-acceptance-criteria.yaml). These sections are VALUE-FROZEN; the QR pins the window convention in parallel — my statistic is convention-parameterized but every numeric value below is the pre-registered contract.
**Status:** SKELETON-FIRST draft; numbers below are the pre-registered contract once consensus-ratified + freeze-receipt cut.

**Binding inputs (READ, this session):**
- NHT rescreen (BINDING counts): `nht-qrb6-rescreen.yaml` — Scenario A **506** deduped event-days / **345** post-2015 (orchestrator cross-checked exact); Scenario B **716/491** pre-committed auto-activation; banks-as-independent-blocks; ECB training-memory-unverified INADMISSIBLE.
- PM acceptance criteria: `pm-acceptance-criteria.yaml` (AC-2 ownership; no_cross_trial_constant_imports; banks_as_blocks; post_2015_subwindow_kill_mandatory; no_65pct_point_target).
- Machinery (pinned, NOT re-derived): `reality_check.py:58-88` (`hac_se_nw`, Bartlett/Newey-West), `:152-343` (Politis-White + PPW), `:403-446` (stationary circular block bootstrap), `:557,962` (+1/+1 p-value); `dsr.py:46-207` (BLdP SR0 + DSR z-form, `var_term`, scipy norm).
- Selection-history precedent (NOT constant reuse): R5 `0.022906` and confirmatory `0.034921` are OTHER TRIALS' constants — forbidden to import (no_cross_trial_constant_imports). My SR0 is derived FRESH below.

---

## 1. Null Hypothesis & Test Statistic (CONF-statistic analogue) — FROZEN

### 1.1 Series under test

`r_e` = the net-of-cost, sign-aligned, post-`entry_delay_bars=1` **event-window return** for one deduped bank-event `e`. The event-window length convention (pre-window bars, post-window bars) is pinned by the QR in parallel (AC-1c/d) and is NOT scanned over — my statistic is parameterized by that convention but is value-frozen once the QR's bar-counts are fixed. Define the per-event scalar:

> `r_e = sign_align_e · ( cumulative net-of-cost return over the QR-frozen event window for the bank-event's currency leg )`

`sign_align_e` is the a-priori directional hypothesis (post-announcement reaction direction — specifically `sign(close(D) − close(D−1))` on the bank-event's mapped leg, as pinned in §4.4 and §5.0; NO data-driven sign fit). The **unit of observation is the deduped bank-event-day** (NHT: banks-as-independent-blocks; pair×event is NOT the unit — cross-pair returns on one decision day share a common currency factor).

Per-scenario n (BINDING from NHT):
- **Scenario A (default, frozen primary):** n = **506** deduped event-days; post-2015 sub-window n = **345**.
- **Scenario B (pre-committed auto-activation on C4 spot-check):** n = **716**; post-2015 n = **491**.

### 1.2 Null and alternative

> **H0:** `E[y_e] ≤ 0` (the signed-product event strategy earns no positive net edge on average across deduped bank-events — an UNCONDITIONAL null on the per-event signed-product scalar, not a conditional null conditioned on the direction of bar D).
> **H1:** `E[y_e] > 0` (the post-announcement reaction continues through the K_post=2 window on average, net of costs).

where the tested quantity is the **signed-product event return**:

> `y_e = sign(close(D,e) − close(D−1,e)) · R_post,e`

and `R_post,e` = the bank-event equal-weight net-of-cost cumulative return **close(D) → close(D+2)** — i.e. the post-decision return on the responsive pairs (§3.2), entered at bar D+1 under `entry_delay_bars=1`, position held during bars D+1 and D+2. The symbol `r_e` used in §1.3–§1.4 is `y_e` under this definition; notation is unified here from §1.2 forward. For the degenerate case `close(D) = close(D−1)` exactly: `sign_align_e = 0`, position FLAT, event EXCLUDED from the realized return (its event-day still counts as a block-day for bootstrap block construction; see §4.4.3).

One-sided, total `α = 0.05` (R5/confirmatory precedent; direction fixed a-priori from the post-announcement continuation hypothesis; §4.4 pins the signal/execution separation). The post-announcement reversal sub-test is framed per NHT C2 as "directional bias statistically distinguishable from BOTH 0% and 100%" — NO 65% point target enters any frozen field (no_65pct_point_target).

### 1.3 Frozen statistic — studentized mean event-window return with HAC SE

For a set of `n` deduped event-days with event returns `{r_e}`:

```
t_stat = sqrt(n) * mean(r) / omega_hat
```

`omega_hat` = **Newey-West (Bartlett-kernel) HAC standard error of the mean**, computed by
`reality_check.hac_se_nw(r, bandwidth = max(L - 1, 1))` (pinned `reality_check.py:58-88`).

`L` = the **Politis-White (2004) + PPW (2009)** automatic mean block length on the **event-day-ordered** series via `reality_check.politis_white_block_length(r)`, then `L = max(1, ceil(L_pw))`. Guard FROZEN: `L ≥ 1`; bandwidth `max(L-1, 1) ≥ 1` (PW clamps `L_opt ∈ [1, b_max]`, returns 1.0 on near-iid, `reality_check.py:316-324`).

**Event-study HAC note (FROZEN):** event-days are calendar-sparse and irregularly spaced. HAC bandwidth is computed on the event-day INDEX ordering (events sorted ascending by decision date), NOT calendar-day lags — adjacent events are adjacent in the ordered return vector regardless of the calendar gap between them. This is the conventional event-study treatment (each event is one observation; serial dependence is event-to-event, not bar-to-bar). PW selects `L` empirically; for near-independent event returns PW returns `L≈1` ⇒ HAC collapses to the iid SE, which is correct.

### 1.4 p-value mechanism — FROZEN: banks-as-blocks stationary block bootstrap

**Election: bank-blocked stationary/circular block bootstrap**, NOT asymptotic-normal. Mirrors the R5/confirmatory falsifier family for consistency; bank-blocking is the event-study extension required by NHT (banks_as_blocks).

See Section 3 for the exact bank-block scheme. Mechanism:
1. Compute observed `t_obs = sqrt(n)·mean(r)/omega_hat` on the full event-day series.
2. Impose H0 by de-meaning: `d_e = r_e − mean(r)` (zero-mean null, autocorrelation/variance preserved — identical convention to `r5a`/`r5c` recentering, `reality_check.py:534-535,959`).
3. For `b = 1..K`: draw a **bank-blocked** stationary block resample `d*_b` (Section 3), recompute `t*_b = sqrt(n)·mean(d*_b)/omega_hat(d*_b)` (HAC SE recomputed each resample, mirroring `reality_check.py:938`).
4. `p = (1 + #{ t*_b ≥ t_obs }) / (K + 1)` (+1/+1, `reality_check.py:557,962`).

---

## 2. Multiplicity / Selection Charge (the load-bearing freeze) — FROZEN

### 2.1 The selection event being charged

QRB-6 is the survivor of a **PAPER selection**, not a data selection. Selection history (BINDING, from prompt + acceptance-criteria evidence):
11 generated proposals → NHT screen (9 survive) → frozen-rubric ranking → 2-finalist informed comparison (QRB-6 vs QRB-3) decided AFTER a data acquisition (the CB calendar). The firm's honest-N ≈ 11-12; org counter = 41.

**FIRST-PRINCIPLES DISTINCTION FROM R5 (the crux).** R5's `N=3` charged a **data-selection**: 36 carry cells were each **backtested** and the argmax studentized statistic was selected — every cell consumed a real look at return data, so the multiplicity is a max-over-realized-statistics and the DSR `N` charges expected-max-of-N-draws inflation. QRB-6's 11 proposals were **NEVER backtested**: no return series was computed for any of the 11, no Sharpe was harvested, the ranking used a frozen *qualitative* rubric (testability, data availability, hypothesis priors) on paper. **No garden-of-forking-paths inflation of an observed Sharpe occurred at the 11→1 stage, because no Sharpe was observed at that stage.** The DSR selection charge exists to deflate a Sharpe that was selected for being large; here the Sharpe has not yet been measured at all (the one-shot run is post-freeze).

### 2.2 What an honest N_sel IS for paper-selection — derivation

The DSR `N` is "number of effectively-independent trials over which a max was taken **on the quantity being deflated** (the realized Sharpe)." For QRB-6 the quantity being deflated is the QRB-6 hold-out Sharpe, and the question is: across how many effectively-independent *realized-Sharpe* looks was THIS hypothesis selected?

- The 11→9 NHT screen and 9→2 rubric ranking touched **zero** realized Sharpes ⇒ they contribute **0** to the Sharpe-multiplicity. (They reduce the *hypothesis* space, not via data on the deflated quantity.)
- The 2-finalist comparison (QRB-6 vs QRB-3) was decided AFTER a data acquisition — but the acquisition was the **CB calendar** (event dates), NOT return series; the comparison used the calendar's *event-count / testability* (NHT counts), not any QRB-6 or QRB-3 Sharpe. So this stage too charges **0** realized-Sharpe looks on the deflated quantity. (If the finalist choice had peeked at either strategy's returns, this would be ≥1; it did not — no return data examined before freeze, AC-4.)
- The one event that DOES consume a realized-Sharpe look is the **forthcoming QRB-6 one-shot run itself** — exactly ONE look.

A pure "the data is unsnooped, charge N=1" is the anti-conservative floor I REJECT (steelmanned in §2.3): even paper-selection leaks a *little* multiplicity because the rubric was informed by the analysts' soft priors about which hypotheses tend to work, and because the firm will (under its own honest-accounting posture) have effectively explored a few correlated event-study framings. The defensible charge is the small-integer effective dimension of that soft prior exploration.

> **FROZEN: `N_sel = 3`.**

Defense: `N_sel = 3` charges (a) the one real realized-Sharpe look (the QRB-6 run), plus (b) ~2 effective-independent soft-prior "framings" the firm implicitly explored when an analyst pool generated 11 proposals and ranked them (the event-study idea-family — CB-decision drift/reversal — is ONE correlated family, not 11 independent bets; its effective independent dimension under the firm's own honest-N≈11-12 collapses to a low single digit once the heavy within-family correlation of "trade-around-scheduled-macro-events" framings is removed). `N_sel = 3` equals the R5 *prior-honest-N* convention (the firm's standing charge for "a few effective looks at a correlated idea-family") WITHOUT importing R5's data-selection 36-cell argmax charge — which is correctly ABSENT here because no QRB cell was backtested. I do NOT copy R5's N=6 (that absorbed a best-of-36-BACKTESTS argmax that has no analogue in paper-selection) nor R5's N=3 constant (the *value* coincides but is RE-DERIVED here from the paper-selection first-principles above, not imported — no_cross_trial_constant_imports honored: the reasoning, not the constant, is the source).

### 2.3 Alternatives stated and rejected

- **N_sel = 1 ("unsnooped data, no charge")** — REJECTED. Steelman: the one-shot run is genuinely OOS, so conditional on the hypothesis the bootstrap p is honest. Rejection: the firm reached THIS hypothesis through an informed multi-stage funnel; a plain N=1 understates the firm-wide false-discovery exposure across its idea-generation process. Over-deflation is the safe-if-wrong direction for a kill test.
- **N_sel = 11 (honest count of generated proposals)** — REJECTED. The 11 are NOT 11 independent realized-Sharpe draws; they were never backtested and they are heavily correlated as event-study framings. Charging 11 as a DSR `N` would treat paper ideas as if each had consumed a max-over-data look — it conflates *hypothesis-space size* with *realized-statistic multiplicity*, the inverse of the §2.2 error. It also double-charges, since the eventual run is a SINGLE look.
- **N_sel = 41 (org trial counter)** — REJECTED. The org counter mixes unrelated trials (carry family, MA, momentum) that share no selection event with QRB-6; the DSR `N` charges THIS hypothesis's selection depth, not the firm's lifetime trial count. (Using 41 would also import the BLdP "n_trials org-wide" reading, which the firm's honest-N discipline has explicitly rejected as the wrong denominator for a single pre-registered structure.)
- **N_sel = 6 (copy R5-confirmatory)** — REJECTED. R5's 6 absorbed a best-of-36-backtests argmax + prior family spend; QRB-6 has NO backtested argmax to absorb. Copying 6 would over-charge by importing a data-selection burden that did not occur, and would violate no_cross_trial_constant_imports in spirit.

### 2.4 Dispersion plug-in (FROZEN — derived, NOT carried from R5)

BLdP `SR0` needs `sqrt(Var[SR_n])` — the cross-trial dispersion of candidate Sharpes. R5/confirmatory used `sqrt(Var)=0.426385`, the sample SD over two OBSERVED look-Sharpes `{0.80, 0.197}`. **For QRB-6 NO per-proposal Sharpes exist** (paper-selection — nothing backtested), so I cannot use observed-look dispersion. I MUST elect a defensible *planning* dispersion.

**Election: `sqrt(Var[SR_n]) = 0.50` (annualized), the planning Sharpe dispersion implied by the published CB-event-study effect-size band.** Derivation:
- The deflation dispersion should reflect how much candidate true-Sharpes plausibly vary across the event-study idea-family the firm drew from. The published scheduled-macro-announcement / pre-FOMC-drift literature (Lucca-Moench 2015 pre-FOMC equity drift; CB-decision FX event studies) reports economically meaningful but modest pre-decision effects whose *annualized Sharpe-equivalent on a tradeable event-only strategy*, AFTER a realistic decay/cost haircut, plausibly spans roughly `[0, ~1]` across framings.
- A dispersion of `0.50` is the SD of a candidate-Sharpe distribution centered near the planning effect size (§5) with support across that `[0,1]` band — i.e. the family's true-Sharpe heterogeneity is on the order of the planning effect itself. This is intentionally a ROUND, auditable single number (not arithmetic theater from invented look-Sharpes): one free planning constant, defended by the published magnitude band, frozen ex-ante.
- `0.50 > ` would over-deflate (claim wilder candidate heterogeneity than the literature supports); `< 0.30` would under-deflate (claim the family's framings are near-identical in true Sharpe, contradicting the visible spread across event-study designs). `0.50` sits in the defensible middle and is NOT the R5 value (0.426385) — it is freshly elected for this paper-selection context.

> **FROZEN: `sqrt(Var[SR_n]) = 0.50` (annualized planning dispersion). RE-DERIVED for QRB-6 paper-selection; NOT imported from R5.**

### 2.5 BLdP SR0 benchmark and derived SR0 — FROZEN (shown arithmetic)

BLdP form (pinned `dsr.py:46-104`, `expected_max_sr` two-axis bracket):
```
SR0_ann = sqrt(Var[SR_n]) · [ (1 − γ)·Z⁻¹(1 − 1/N_sel) + γ·Z⁻¹(1 − 1/(N_sel·e)) ]
SR0_pp  = SR0_ann / sqrt(252)
```
with `γ = 0.5772156649`, `e = 2.718281828`, `Z⁻¹ = scipy.stats.norm.ppf`.

Bracket at `N_sel = 3` (the bracket VALUE is a property of N only — it equals R5's `0.852804` at N=3; the SR0 differs from R5 solely because my dispersion plug-in 0.50 ≠ R5's 0.426385):
```
Z⁻¹(1 − 1/3)        = Z⁻¹(0.666667)            = 0.430727
Z⁻¹(1 − 1/(3e))     = Z⁻¹(1 − 0.122626)
                    = Z⁻¹(0.877374)            = 1.161957
bracket(N=3)        = (1−γ)·0.430727 + γ·1.161957
                    = 0.4227843·0.430727 + 0.5772157·1.161957
                    = 0.182118 + 0.670721
                    = 0.852804
SR0_ann_sel         = 0.50 · 0.852804           = 0.426402   (annualized)
SR0_pp_sel          = 0.426402 / sqrt(252)
                    = 0.426402 / 15.874508      = 0.026861   (per-obs)
```

> **FROZEN: `SR0_ann_sel = 0.426402`, `SR0_pp_sel = 0.026861` (per-obs), `N_sel = 3`, `sqrt(Var[SR_n]) = 0.50`.**
> *(Z⁻¹ bracket values are standard-normal quantiles to 6 dp, orchestrator-verified via `statistics.NormalDist.inv_cdf` and routed to QD for `scipy.stats.norm.ppf` confirmation — Section 6. bracket(N=3)=0.852804 matches the R5 value EXACTLY because the bracket depends only on N; this is a consistency check, NOT a constant import — the SR0 it feeds is fresh because the dispersion differs.)*

**Implied hold-out sample Sharpe the strategy must clear:** the SR0 above is the deflation BENCHMARK; the minimum hold-out annualized Sharpe that clears the DSR gate at the terminal n is the kill_switch_threshold (Section 6) — `≈ SR0_pp + z_{0.95}/sqrt(T−1)`, annualized. At Scenario-A n=506 this is far higher than SR0 because the `sqrt(T−1)` lever is short (Section 6).

---

## 3. Bootstrap Spec — banks-as-independent-blocks — FROZEN

### 3.1 Block construction (the NHT banks_as_blocks requirement)

The unit is the deduped bank-event-day. NHT requires banks treated as **independent blocks**, NOT individual observations: within one bank-event the affected pairs share a common currency factor (not independent), and the bootstrap must resample at bank granularity.

> **FROZEN bank-block scheme.** Partition the `n` event-days into `G` bank-groups by the parquet `bank` column (Scenario A: G=4 — FED/BOJ/RBA/BOC; Scenario B: G=7 — +BOE/ECB/RBNZ). Within each bank-group the event-day returns are ordered ascending by decision date. The stationary circular block bootstrap (`reality_check._circular_block_bootstrap`, Politis-Romano 1994) is applied **within bank-group, then concatenated** to form each resample, preserving (a) within-bank event-to-event serial dependence via geometric blocks and (b) the bank-group sizes (block draws never cross a bank boundary — a block started in FED never wraps into BOJ; circular wrap is within-bank only). This is the event-study analogue of R5c's JOINT bootstrap, with the join axis being **bank** rather than pair-column.

Rationale: bank-events of different banks are the independent units (different currency, different decision calendar); bank-events of the SAME bank carry the only event-to-event serial dependence worth preserving (e.g. a persistent regime in FED-decision drift). Blocking within-bank and concatenating across banks resamples the independent units while preserving the within-unit dependence — exactly the "banks as independent blocks" NHT instruction.

**Same-day multi-bank co-decisions** (22 in Scenario A, 83-surplus in Scenario B) are already deduped to market-days in the NHT counts; each deduped event-day carries its bank label (the dominant deciding bank for that market-day per the QR's dedup rule). No event-day appears in two bank-groups.

### 3.2 Block length

`L` per bank-group = Politis-White auto on that group's event-day return series, `L_group = max(1, ceil(L_pw))`. The bootstrap uses the **per-bank** `L_group` for that group's internal resampling. For the single pooled HAC `omega_hat` (Section 1.3) the block length is the multivariate-style **max across bank-groups**, `L_pool = max_g L_group` (mirroring `politis_white_block_length_multivariate`'s "max L covers every cell's dependence", `reality_check.py:346-384`), so the HAC bandwidth is conservative (widest dependence covered). FROZEN: `L_group ≥ 1`, `L_pool ≥ 1`.

### 3.3 K (replications) + MC-SE

> **FROZEN: `K = 10000`** (the module default `_B`, `reality_check.py:49`; matches confirmatory's full-K election). The single pooled event-study test is cheap enough to run full K.

MC standard error of a bootstrap p-value `p` is `sqrt(p(1−p)/K)`. Table at K=10000:

| p (true) | MC-SE = sqrt(p(1−p)/K) |
|----------|------------------------|
| 0.01     | 0.000995               |
| 0.05     | 0.002179               |
| 0.10     | 0.003000               |
| 0.50     | 0.005000               |

MC-SE = 0.00218 at K=10000 ⇒ `±MC-SE = 0.0022` half-width. For the remediated re-run (REMEDIATION AMENDMENT v2) the band recenters on the OBF look-2 boundary `α_look2 = 0.039995`, giving the CLOSED straddle `[0.0378, 0.0422]` (`0.039995 ∓ 0.0022`). (The original single-look freeze centered the band at α=0.05 ⇒ `[0.0478, 0.0522]`, now VOIDED; R5 used 0.0031 at K=5000.)

### 3.4 Seed RULE — FROZEN (digit-by-digit)

> **FROZEN RULE:** `master_seed = int(first 6 hex chars of trial stem, base 16) mod 1_000_000`. (Same RULE the confirmatory froze after catching a hand-hex drift; `fa0f982a` HAS no leading decimal run, so the hex-mod rule governs — NOT a "leading decimal digits" reading.)

Trial stem: `fa0f982a`. First 6 hex chars: `fa0f98`. Arithmetic, digit-by-digit base-16 (positions weighted 16^5..16^0):
```
f = 15 ;  a = 10 ;  0 = 0 ;  f = 15 ;  9 = 9 ;  8 = 8

16^5 = 1048576 ;  16^4 = 65536 ;  16^3 = 4096 ;  16^2 = 256 ;  16^1 = 16 ;  16^0 = 1

15 · 1048576 = 15728640
10 ·   65536 =   655360
 0 ·    4096 =        0
15 ·     256 =     3840
 9 ·      16 =      144
 8 ·       1 =        8
                ----------
int('fa0f98', 16) = 15728640 + 655360 + 0 + 3840 + 144 + 8 = 16387992

16387992 mod 1_000_000 = 387992
```

> **FROZEN: `master_seed = 387992`.** *(int('fa0f98',16)=16387992; 16387992 mod 1e6 = 387992. Orchestrator + QD to independently re-verify, mirroring the confirmatory's hand-hex-drift catch.)*

Child-seed convention follows R5: the single pooled block bootstrap uses `master_seed` directly (R5a convention, `reality_check.py:527`). RNG = **`numpy.PCG64`** seeded by `master_seed`. **scipy REQUIRED** (no approximation fallback) for `norm.ppf`/`norm.cdf`; absence ⇒ TECHNICAL_FAILURE, never silent approximation (R5/confirmatory A-5 pin).

---

## 4. Error Control & Decision Rule — FROZEN

### 4.1 Alpha

One-sided total `α = 0.05` (R5/confirmatory precedent). The aggregate test and the post-2015 sub-window KILL are BOTH evaluated against this α (the post-2015 gate is a SEPARATE mandatory hurdle, not an α-split — see §4.2; NHT post_2015_subwindow_kill_mandatory).

### 4.2 The two-gate functional (both-must-pass) — FROZEN, §7.3.6-style ordered rules

Let `p_agg` = the bank-blocked bootstrap p on the FULL Scenario-A event set (n=506), `p_post2015` = the same statistic on the post-2015 sub-window (n=345), `DSR` = the §2/§6 deflated-Sharpe statistic on the full event set, and the run-integrity flags. The frozen firm decision is an **ordered, mutually-exclusive, exhaustive** evaluation — FIRST matching rule fires and STOPS. Order chosen so no boundary case buys PASS; every tie resolves to the more conservative (non-PASS) branch. MC-SE straddle band = **0.0022** (§3.3). Evaluate top to bottom:

> **RULE 0 — TECHNICAL FAILURE** (→ HALT, root-cause, re-freeze, re-run; NO p read). Fires iff a code error, data-integrity/provenance fault, training-memory-unverified row leaking into the event set, freeze-receipt mismatch, cross-trial constant import detected, or any divergence of the runner from the pinned `reality_check`/`dsr` conventions. If RULE 0 fires, RULES 1–4 are NOT evaluated.
>
> **RULE 1 — KILL (post-2015 structural-break fail)** (→ the mandatory NHT kill; overrides any aggregate pass). Fires iff RULE 0 did not, AND **`p_post2015 > 0.0422`** — the post-2015 sub-window does NOT cleanly reject H0, with the p-value sitting above the MC-indistinguishability straddle band. This is evaluated **BEFORE** any aggregate-pass test, so a strategy alive only pre-2015 is KILLED **regardless of `p_agg` or `DSR`** (NHT: pre-2015-only drift = dead alpha in the current regime; post_2015_subwindow_kill overrides_aggregate_pass: true). Archive QRB-6 RETIRED/FALSIFIED.
>
> **RULE 2 — KILL (aggregate fail)** (→ wind-down). Fires iff RULES 0–1 did not (so post-2015 cleanly rejects), AND **`p_agg > 0.0422`** — the full event set does not reject H0, above the straddle band. Statistically indistinguishable from chance at the pooled level (above even the MC uncertainty envelope). Archive RETIRED.
>
> **RULE 3 — PASS** (→ §-action: graduate to a fresh, separately-pre-registered observe-only paper canary; NO CAPITAL; new trial_id; new HoQR+Math+NHT ratification). Fires iff RULES 0–2 did not, AND **`p_post2015 < 0.0378`** AND **`p_agg < 0.0378`** (BOTH strictly below the straddle band's lower edge — clean rejections with no MC-ambiguity), AND **`DSR ≥ 0.95`** (selection-deflation gate cleared at `SR0_pp_sel=0.026861`, equivalently aggregate-set ann Sharpe ≥ kill_switch_threshold=1.5883, §2/§6). PASS is NECESSARY-BUT-NOT-SUFFICIENT and authorizes only a confirmatory/observe-only next step.
>
> **RULE 4 — AMBIGUOUS / gate-fail (catch-all, guarantees exhaustiveness)** (→ no-PASS; default to wind-down under full-auto, or a fresh single-structure confirmatory pre-reg if HoQR elects). Fires iff RULES 0–3 did not. This catches three disjoint sub-cases, all non-PASS: (a) either p sits in the **CLOSED** straddle band `[0.0378, 0.0422]` — MC-indistinguishable from 0.05 at K=10000; boundary p **never** buys PASS and **never** reads as clean KILL; (b) both p's are strict clean rejections (`p_post2015 < 0.0378` AND `p_agg < 0.0378`) but `DSR < 0.95` — the rejection cannot clear the selection-deflation charge; (c) any combination not covered by RULES 0–3. A bare bootstrap rejection that cannot survive deflation, or any p in the straddle band (including exact boundary values 0.0378 and 0.0422), maps here — NEVER to PASS.

**Exhaustiveness & mutual-exclusivity.** Ordered disjoint conditions: {technical-fail} → {p_post2015 > 0.0422: KILL} → {p_agg > 0.0422: KILL} → {both p's < 0.0378 ∧ DSR≥0.95: PASS} → {else: AMBIGUOUS}. Evaluation stops at first match ⇒ disjoint by construction; RULE 4 is the unconditional else ⇒ every non-technical-fail outcome lands in exactly one of RULES 1–4. No overlap between the post-2015 gate and the aggregate gate: post-2015 is tested FIRST and its failure (p > 0.0422) short-circuits before the aggregate is consulted (the both-must-pass semantics — post-2015 fail KILLS even when aggregate passes; aggregate is only reached if post-2015 cleanly rejects). **Boundary convention (frozen):** the straddle band `[0.0378, 0.0422]` is CLOSED; both endpoints and all interior values route to RULE 4 (AMBIGUOUS). PASS requires strict `< 0.0378`; KILL requires strict `> 0.0422`. This inequality appears once per rule body — no other representation of the threshold exists in this document.

**Both-must-pass restated:** PASS requires BOTH `p_post2015` AND `p_agg` to cleanly reject AND `DSR≥0.95`. A post-2015 fail with an aggregate pass = KILL (RULE 1), never PASS — this is the NHT-mandated structural-break kill encoded as the highest-priority non-technical rule.

### 4.3 Scenario-B auto-activation arithmetic — FROZEN (no recompute at activation)

Scenario B activates automatically on C4 spot-check completion (pre-committed; no new pre-reg). The two-gate functional is IDENTICAL; only the n's change, which changes only the kill_switch_threshold (via the `sqrt(T−1)` lever) and the MC-SE-band-free p-thresholds (the α and straddle band are n-invariant). FROZEN both parameter sets so activation needs NO recompute:

| Quantity | Scenario A (frozen default) | Scenario B (pre-frozen, auto-activate on C4) |
|----------|------------------------------|-----------------------------------------------|
| n (aggregate) | 506 | 716 |
| n (post-2015 sub-window) | 345 | 491 |
| α (one-sided, total) | 0.05 | 0.05 |
| MC-SE band (K=10000) | 0.0022 | 0.0022 |
| p-reject threshold (PASS, strict) | p < 0.0378 (strict, both gates) | p < 0.0378 (strict, both gates) |
| p-KILL threshold (strict) | p > 0.0422 (strict, either gate) | p > 0.0422 (strict, either gate) |
| straddle band (AMBIGUOUS, CLOSED) | [0.0378, 0.0422] → RULE 4 | [0.0378, 0.0422] → RULE 4 |
| SR0_pp_sel (N_sel=3, disp=0.50) | 0.026861 | 0.026861 |
| DSR gate | ≥ 0.95 | ≥ 0.95 |
| kill_switch_threshold (ann Sharpe, aggregate-set anchor) | **1.5883** (T=506) | **1.4029** (T=716) |

The DSR benchmark `SR0_pp_sel` and `N_sel` are n-INVARIANT (selection charge does not depend on the event count). ONLY `kill_switch_threshold` moves with n (Section 6 derivation for both). Activation = swap the n-pair and read the pre-frozen threshold; nothing is recomputed live.

---

## 4.4 Signal/Execution Separation Contract (NHT-F5 companion) — FROZEN

This section pins the signal/P&L boundary for the `sign_align_e` rule. It is the **mathematician's contract for the NHT-F5 companion**: the QR pins the sign-alignment rule in §5.0; I state what that rule must satisfy to preserve the hypothesis stated in §1.2 and the filtration this statistic assumes. **This section was authored after DEBATE ROUND-1 CONVERGENCE (artifact: `debate-r1-math.yaml`); it replaces the earlier NHT-F5 companion block from math-rework1-patches.md (the F_{D-1} ruling), which is SUPERSEDED and was never applied.**

### 4.4.1 Filtration assumption and signal/execution boundary (FINAL, bar-D)

The no-lookahead invariant (§4.3, `entry_delay_bars = 1`) and the daily-bar timestamp convention (§4.1) jointly fix the signal/execution boundary.

**FROZEN filtration ruling (bar-D signed product):**

> `sign_align_e = sign(close(D) − close(D−1))` where `D` is the decision-reflecting bar (§4.1). The signal is determined from the CLOSE of bar D — F_D-measurable. Entry executes at bar D+1 under `entry_delay_bars=1`. The post-window cumulative return (the P&L) runs from D+1 forward: bars D+1 and D+2 (K_post=2). No bar is simultaneously a sign-input and a realized-return bar without the mandatory `entry_delay_bars` shift.

**Why the bar-D return is the SIGNAL, not the P&L:** bar D's close-to-close return `close(D)−close(D−1)` captures the initial post-announcement market reaction. This return is consumed at signal-formation time — it is the input to `sign_align_e`. The firm's engine records P&L only from the entry bar D+1 onward; bar D's own return is therefore a signal variable, not a P&L variable. The signal/execution separation is enforced by `entry_delay_bars=1` and is auditable via the sacred `test_no_lookahead` test (§4.3).

**Engine semantics (single authoritative phrasing, echoed identically in §5.0 and §1.2):** signal computed at bar D (F_D-measurable, no look-ahead into future bars); entry at D+1; position held during bars D+1 and D+2; exit at close of D+2. The K_post=2 net-of-cost cumulative return from close(D) to close(D+2) is the P&L window. This phrasing supersedes any alternative window description (e.g., "[D+1 close … D+K_post close]") that might appear in earlier draft artifacts; the engine executes the entry_delay_bars=1 shift mechanically, and the return is close(D)→close(D+2) as a result.

**Entry bar information check:** at entry bar D+1, close(D) is observable. The signal `sign_align_e` uses only data available through close(D) — strictly in the past relative to the entry. No future bar (D+1, D+2) is accessed during signal formation. No firm data-access command examines return data before the freeze-receipt is cut (§1.4(1)); once the runner executes, it uses only the frozen signal rule and the engine's entry_delay_bars shift.

### 4.4.2 Why F_{D-1} was CONSIDERED and REJECTED

The alternative filtration — `sign_align_e = sign(ret_{D−1})`, i.e., the direction of bar D−1's return (F_{D-1}-measurable) — was the mathematician's initial ruling (math-rework1.yaml) and was RETRACTED after full economic and statistical review in debate-r1-math.yaml. It is documented here for intellectual honesty and auditability.

**Economic rejection (the decisive reason):** F_{D-1} filtration makes the sign input the direction of the pre-decision drift component — the component §2.3 explicitly declares DEAD post-2015. Using the dead component as the alignment signal would mean the pre-registration tests "the pre-event trend direction (documented essentially disappeared post-2015) predicts post-announcement returns." This is not the hypothesis §2.1 registers (which is "post-decision reaction/reversal structure"). Adopting F_{D-1} would have embedded a ghost signal into the pre-reg while claiming to test the alive post-announcement component.

**Statistical consequence (secondary):** under F_{D-1}, the signed product `y_e = sign(ret_{D−1}) · R_post,e` tests a different economic object — whether the pre-event drift direction predicts post-announcement continuation. The HAC/bootstrap machinery is unchanged between the two filtrations (PW adapts to whichever y_e series is presented; recentering d_e = y_e − mean(y) correctly imposes H0 for either). The statistical mechanics do NOT mandate rejection of bar-D filtration; the economic incoherence does.

**F_{D-1} is not a backup option.** If bar-D reaction data is unavailable (e.g., index lookup failure), the correct action is RULE 0 TECHNICAL_FAILURE — not silent fallback to F_{D-1}, which would silently change the registered hypothesis. The runner must implement the bar-D rule exactly and halt if it cannot be computed.

### 4.4.3 Degenerate-case handling — close(D) = close(D−1) exactly

If bar D's return is exactly zero — i.e., `close(D) = close(D−1)` within floating-point equality — there is no initial reaction to continue or fade. The direction is undefined.

**FROZEN degenerate-case convention:**

> If `ret_D = close(D) − close(D−1) = 0` (floating-point equality), `sign_align_e = 0`, position = FLAT (excluded from the realized return average). The event-day STILL COUNTS as a block-day for bootstrap block construction — it is included in the bank-group's event sequence and contributes to the block structure. It is excluded only from the numerator of the pooled mean (the return series used in `mean(y)` and the bootstrap).

Justification: the frequency of exact-zero daily returns in liquid FX OHLCV data is near-negligible; the convention has no material effect on the statistic. The FLAT/exclusion convention is chosen over +1 (the earlier F_{D-1} ruling's convention) because: (a) a zero reaction on decision day carries no directional information — assigning +1 would introduce an arbitrary long bias; (b) the QR's §5.0 explicitly specifies this FLAT/exclusion convention; (c) the block-day inclusion preserves the block structure's calendar integrity. The convention is frozen ex-ante and may not be changed post-hoc once any event-day data are examined (VOID §1.4(2)).

**Runner implementation requirement:** the runner MUST implement `sign_align_e = numpy.sign(ret_D)` (which returns 0.0 when ret_D = 0.0 exactly), with a branch: if `sign_align_e == 0.0` → position = 0 (FLAT), event-day included in block count but excluded from return average. A unit test on a **synthetic zero-ret_D event** is REQUIRED before the freeze-receipt is cut. (This requirement carries forward from the original §4.4.3; the trigger condition is updated from `ret_{D−1}=0` to `ret_D=0`.)

### 4.4.4 Contract summary (machine-readable)


### 5.1 Planning effect size (justified)

Power must be planned at a **defensible, decay-haircut event-study effect size**, NOT a snooped Sharpe (none exists — nothing backtested). Published anchors: pre-FOMC / pre-decision drift studies (Lucca-Moench 2015 pre-FOMC equity drift; scheduled-CB-decision FX event studies) report economically meaningful pre-decision moves; translated to a tradeable **event-only** annualized Sharpe AFTER a realistic decay + cost haircut, the planning effect is modest.

> **FROZEN planning effect size: `SR_plan = SR0_ann_sel = 0.4264` (annualized).** Rationale (mirroring confirmatory §3.1): plan power at the firm's own selection-deflated benchmark — the smallest true ann Sharpe at which a PASS is *meaningful* rather than selection luck. Planning at a larger snooped figure would overstate power. A literature-anchored alternative (a `~0.3–0.5` post-haircut event-Sharpe band) lands in the same neighborhood; I freeze the single auditable `SR0_ann_sel` rather than add a second free parameter.

### 5.2 Power curves — event-day-count convention

For an event-study pooled t-test, the non-centrality at n deduped event-days is `λ = SR_pp · sqrt(n) = (SR_ann/sqrt(252)) · sqrt(n)`. With `SR_ann = 0.4264`, `SR_pp = 0.426402/15.874508 = 0.026861`. One-sided boundary `z_{0.95} = 1.644854`. Power `= Φ(λ − z_{0.95})` (orchestrator-verified; QD to confirm).

```
Scenario A aggregate, n = 506:
  λ = 0.026861 · sqrt(506) = 0.026861 · 22.49444 = 0.604219
  power = Φ(0.604219 − 1.644854) = Φ(−1.040635) = 0.149   (≈ 15%)

Scenario A post-2015, n = 345:
  λ = 0.026861 · sqrt(345) = 0.026861 · 18.57418 = 0.498918
  power = Φ(0.498918 − 1.644854) = Φ(−1.145936) = 0.126   (≈ 13%)

Scenario B aggregate, n = 716:
  λ = 0.026861 · sqrt(716) = 0.026861 · 26.75818 = 0.718746
  power = Φ(0.718746 − 1.644854) = Φ(−0.926108) = 0.177   (≈ 18%)

Scenario B post-2015, n = 491:
  λ = 0.026861 · sqrt(491) = 0.026861 · 22.15852 = 0.595196
  power = Φ(0.595196 − 1.644854) = Φ(−1.049658) = 0.147   (≈ 15%)
```

> **Power at the planning effect SR_plan=0.4264 is LOW (~13–18%) across all four n's.** Disclosed honestly. The event-study has MANY event-days but each event carries little independent signal at the planning Sharpe; the pooled non-centrality grows only as sqrt(n). This is the explicitly-disclosed power reality: a non-rejection (KILL) at the terminal n is uninformative *as evidence of no edge* but does NOT license continued spend (mirrors confirmatory §3.5 / decision map). NHT reviews.

**Sensitivity (higher planning effect, for context, NOT the frozen plan):** if the true event-Sharpe were the un-haircut `~0.7` band, n=506 power `= Φ(0.7/15.8745·sqrt(506) − 1.645) = Φ(0.04410·22.494 − 1.645) = Φ(0.9920−1.645) = Φ(−0.653) = 0.257` (~26%). Even doubling the planning effect leaves the test underpowered at n=506 — the event-only Sharpe is intrinsically low. The PW block length on the event series may FURTHER reduce effective n (high event-to-event autocorrelation ⇒ fewer effective blocks ⇒ wider HAC SE); the iid-event power above is an UPPER bound. Disclosed.

---

## 6. kill_switch_threshold — FROZEN (verbatim pre-reg field)

The `kill_switch_threshold` is the **minimum event-strategy annualized Sharpe** required to clear the DSR gate (`DSR ≥ 0.95`) at `SR0_pp_sel = 0.026861`, carrying the event-set's own higher moments at evaluation. The DECLARED verbatim value anchors to **Scenario A aggregate, T = 506** (the frozen primary event set on which the DSR gate is computed; Scenario B's 716-anchor value is pre-frozen in §4.3 for auto-activation). var_term reference = 1.

DSR conventions pinned (`dsr.py:179-203`): `var_term = 1 − skew·SR_pp + ((xkurt+2)/4)·SR_pp²`; `z_dsr = (SR_pp − SR0_pp_sel)·sqrt(T−1)/sqrt(var_term)`; `DSR = Φ(z_dsr)`. DSR=0.95 ⇒ `z_dsr = Φ⁻¹(0.95) = 1.644854`. var_term reference = 1 (event-set higher moments unknown until run; the runner recomputes var_term with the event-set's OWN skew/kurtosis at evaluation — I freeze the declared value at the var_term=1 reference, which is the conservative, auditable anchor since `SR_pp` is small ⇒ var_term ≈ 1; mirrors confirmatory §4's two-pass with the pre-registered placeholder, where the second pass moved the result by < 0.001).

Solve at `var_term = 1`, `T = 506` (Scenario A aggregate — the declared anchor):
```
SR_pp = SR0_pp_sel + z_dsr / sqrt(T − 1)
      = 0.026861 + 1.644854 / sqrt(505)
      = 0.026861 + 1.644854 / 22.472205
      = 0.026861 + 0.073195
      = 0.100056
SR_ann = SR_pp · sqrt(252) = 0.100056 · 15.874508 = 1.588337
```

> **FROZEN: `kill_switch_threshold: 1.5883`** (annualized Scenario-A-aggregate event-strategy Sharpe required at T=506 to clear DSR ≥ 0.95 at `SR0_pp_sel=0.026861`, `N_sel=3`, `disp=0.50`, var_term=1; orchestrator-verified 1.588337).

Scenario B, T=716 (pre-frozen, §4.3):
```
SR_pp = 0.026861 + 1.644854/sqrt(715) = 0.026861 + 1.644854/26.74883 = 0.026861 + 0.061493 = 0.088354
SR_ann = 0.088354 · 15.874508 = 1.402907   → kill_switch (Scenario B) = 1.4029
```

> Interpretation: any aggregate-set event-strategy ann Sharpe BELOW 1.5883 (Scenario A) / 1.4029 (Scenario B) fails the DSR gate and cannot produce a PASS (maps to RULE 4). NOT copied from any prior trial — derived fresh at QRB-6's `SR0_pp_sel`, `N_sel=3`, `disp=0.50`, and T. The threshold sits far above the planning SR (0.43) and SR0 (0.027) because `T≈506` is short (the `sqrt(T−1)` lever is weak) and the DSR demands a high realized Sharpe to certify a selected structure on a modest sample — exactly the confirmatory dynamic (confirmatory got 1.2906 at N=6/T=1260; QRB-6 gets 1.5883 at N=3/T=506: the smaller N LOWERS the SR0 contribution but the smaller T RAISES the threshold more, netting higher). This high bar against a ~13–18%-power test (Section 5) is the honest, disclosed reality: the most-likely terminal state is KILL.

> **kill_switch_threshold (verbatim field for the pre-reg file): `1.5883`** (Scenario A primary; `1.4029` Scenario B on auto-activation).

---

## ROUTED NUMERICAL QUESTION (to quant-developer)

Confirm via `scipy.stats.norm` (PCG64 irrelevant for these deterministic constants): (1) the two §2.5 quantiles `Z⁻¹(0.666667)`, `Z⁻¹(0.877374)` and `bracket(N=3)`; (2) `SR0_ann_sel`, `SR0_pp_sel`; (3) `int('fa0f98',16)=16387992` ⇒ `master_seed=387992`; (4) the §6 two-pass solves for `kill_switch_threshold` at T=506 and T=716; (5) the §5 power values. All are standard `scipy.stats.norm.ppf`/`.cdf` evaluations; values shown are my hand-work to 3–6 dp.

---

## 7. Freeze Mechanics (QR) — criterion AC-1; AC-8

The freeze-receipt is an EXTERNAL write-once file (pattern of `scripts/cut_freeze_receipt.py`), cut POST-CONSENSUS via `cut_freeze_receipt.py --target qrb6 --cut`. It records: (a) SHA-256 of THIS file as committed; (b) the pinned code-commit hash for the QRB-6 execution path; (c) the trial id `fa0f982a`; (d) the Mathematician's frozen constants (registered alpha, K, master_seed, `kill_switch_threshold`, `spread_z_threshold`, post-2015 cutoff). The receipt REFUSES to overwrite (per-target write-once guard) and MUST NOT touch the immutable R5 / R5-confirmatory receipts.

**Receipt-before-any-return-data-examination (the cryptographic boundary):** no OHLCV return, equity curve, Sharpe, or test statistic may be computed on `data/processed/{PAIR}_{daily,4h}.parquet` before the freeze-receipt is committed to git. The orchestrator confirms the receipt exists in git before any return-computing data-access command. This boundary is what makes the QRB-6 p-value face-valid (Lopez de Prado; AC hard-constraint `no_return_data_examination_before_freeze`).

**Permitted pre-freeze code changes (R5 precedent — the ONLY permitted post-freeze code object).** Mirroring the R5 STEP-4 runner precedent: exactly ONE named code object is a permitted pre-freeze artifact — the QRB-6 one-shot runner (the "look"/STEP-4-style runner, `scripts/run_qrb6.py` or equivalent), which is authored and committed BEFORE the freeze-receipt is cut and is then **pinned by the freeze commit** (`receipt.code_commit == pinned commit`, §1.4(5)). The runner is interlocked with the receipt: it **REFUSES to execute unless it reads a committed freeze-receipt whose `prereg_sha256` matches `sha256(this file as committed)` and whose `code_commit` matches the runner's own commit** (a hash-matching receipt interlock — no receipt, or a mismatched hash, ⇒ TECHNICAL_FAILURE / RULE 0, never a silent run). The freeze-receipt cut is therefore explicitly ORDERED AFTER the runner commit exists and is pinned (closes NHT-F6's "ordering implied, not enforced"). **No other post-freeze code change is permitted:** once the receipt is cut, neither this pre-reg, the sidecar, nor the runner may be edited — any edit changes the hash and the interlock refuses, voiding the run (§1.4(2), §1.4(5)). This single named exception (runner pinned by the freeze commit + hash-matching receipt interlock) is the complete permitted-pre-freeze-changes set; everything else is frozen.

**Sidecar:** all kill conditions in §5 are machine-encoded in the `.triggers.yaml` sidecar at `references/pre-registrations/qrb6_cb_event_study.triggers.yaml` (QD authors; AC-3b). Every prose kill condition here has a corresponding machine-readable entry there, testing the SAME post-decision `K_post=2` quantity (§5.0): the fixed `p ≤ 0.0378` primary gate (OBF look-2), the post-2015 sub-window kill with `overrides_aggregate_pass: true`, the DSR ≥ 0.95 selection gate (`SR0_pp_sel = 0.026861`, `N_sel = 3`), the reversal-distinguishability sub-claim, and the `spread_z` overlay threshold with suppress-entry semantics. (The per-bank Sharpe is a secondary/advisory metric, not a hard trigger.) The sidecar is being rebuilt in parallel to test the post-decision quantity (NHT-F2) — doc and sidecar must test the identical `r_e` at freeze. The trial registers (BC-1, counter at 41) only at the moment the freeze-receipt is cut.

---

*Mathematician-owned PART II (statistic/null, multiplicity charge, bootstrap spec, alpha/K/seed, power, kill_switch_threshold derivation) is merged at assembly. NHT audit (AC-5) and principal-reviewer review (AC-6) precede CONSENSUS (AC-7); CEO sign-off precedes the freeze-receipt cut (AC-8).*
