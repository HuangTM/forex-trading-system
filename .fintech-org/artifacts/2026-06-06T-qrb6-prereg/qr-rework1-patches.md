# QRB-6 PRE-REGISTRATION — QR REWORK-1 PATCHES (trial fa0f982a)

**Role:** Quantitative Researcher (author of PART I + the merged Math PART II assembly)
**Subtask:** `qrb6-prereg-2026-06-06:phase1:task1.0` / `qrb6-prereg-qr-rework1`
**Date:** 2026-06-06
**Targets:**
1. `references/pre-registrations/qrb6_cb_event_study.md` (SECTION A — the freeze object)
2. `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/qr-prereg-draft.yaml` (SECTION B — supporting artifact)

Each patch is an **exact-anchor block**: the ANCHOR is quoted verbatim from the current file; the
REPLACEMENT is the exact text to substitute. Apply in order. No code blocks are executed; no return
data is examined.

**Authoritative gating model (PART II §4.2, the functional these patches conform §5 to):**
- One-sided total `α = 0.05`. The **p-gates use the FIXED threshold `p ≤ 0.0478`** (= `α − MC-SE`,
  MC-SE band `0.0022` at `K=10000`); a p in the straddle `[0.0478, 0.0522]` is neither a clean
  reject nor a clean KILL (→ RULE 4).
- The **selection multiplicity (N_sel=3) is charged via the DSR gate ONLY** (`DSR ≥ 0.95` at
  `SR0_pp_sel = 0.026861`, equivalently aggregate-set ann Sharpe ≥ `kill_switch_threshold = 1.5883`
  / `1.4029` Scenario B). It is **NOT** charged on the p-value scale. There is **no**
  "absorbed-into-the-primary-alpha (~0.0025)" mechanism — that legacy QR-PART-I draft wording is
  superseded and is struck by these patches.

---

# SECTION A — `references/pre-registrations/qrb6_cb_event_study.md`

---

## PATCH A1 — §5 preamble (strike the live-token convention) — PR-01 / NHT-F1

**ANCHOR:**
```
All criteria below are machine-checkable and mirrored in the `.triggers.yaml` sidecar (§7). Where a numeric threshold is the Mathematician's, it is left as `[MATH]`; the STRUCTURE of each criterion is owned here.
```

**REPLACEMENT:**
```
All criteria below are machine-checkable and mirrored in the `.triggers.yaml` sidecar (§7). Every numeric threshold is now STATED DIRECTLY from the frozen PART II values; §4.2 is the authoritative decision functional and these §5 criteria are its prose mirror (no live `[MATH]` token remains, no alternative charge mechanism is described). The single load-bearing reconciliation: the selection-multiplicity charge (`N_sel = 3`) lives in the **DSR gate ONLY** (PART II §2, §4.2, §6); the two p-gates use the **fixed** threshold `p ≤ 0.0478` (= `α 0.05 − MC-SE 0.0022`, K=10000). There is NO charge on the p-value scale and NO "registered post-multiplicity-charge alpha" of ~0.0025 — that earlier draft framing is SUPERSEDED by §4.2 and does not appear here.
```

---

## PATCH A2 — §5.1 PRIMARY criterion (rewrite to fixed p ≤ 0.0478; remove absorbed-charge prose) — PR-01 / NHT-F1

**ANCHOR:**
```
> **PRIMARY:** Compute the pooled, sign-aligned, net-of-cost event-study statistic over the Scenario A deduped event-days (bank-level blocks). The structure FAILS (KILL) if the pooled block-bootstrap p-value for `H0: E[net event-window return] ≤ 0` is **`≥ [MATH primary alpha]`** (the registered post-multiplicity-charge alpha — the 11-proposal portfolio selection charge AND the 2-finalist QRB-6-vs-QRB-3 comparison charge are absorbed by the Mathematician into this alpha; PART II). Equivalently on the metric scale: the pooled net event-window mean / Sharpe must clear the Mathematician's frozen `[MATH]` lower bound. **No directional point target is registered** (see §5.3).
```

**REPLACEMENT:**
```
> **PRIMARY:** Compute the pooled, sign-aligned (§5.0), net-of-cost POST-decision event-study statistic over the Scenario A deduped event-days (bank-level blocks). The structure FAILS (KILL) if the pooled bank-blocked stationary-block-bootstrap p-value for `H0: E[net post-decision event-window return] ≤ 0` is **`> 0.0478`** (the FIXED one-sided gate `α 0.05 − MC-SE 0.0022` at `K = 10000`; PART II §4.2 RULE 2). The 11-proposal portfolio selection charge AND the 2-finalist QRB-6-vs-QRB-3 comparison charge are **NOT** charged on this p-threshold — they are charged via the DSR selection-deflation gate (`N_sel = 3`, §5.7 / PART II §2, §6), so the p-gate threshold stays at the fixed `0.0478`. A PASS additionally requires the DSR gate (§5.7); a clean p-reject that cannot clear the DSR charge is NOT a PASS (PART II §4.2 RULE 4). A p in the straddle band `[0.0478, 0.0522]` is neither a clean reject nor a clean KILL (→ RULE 4, §5.7). **No directional point target is registered** (see §5.3). §4.2 is the authoritative functional; this is its prose mirror.
```

---

## PATCH A3 — §5.2 POST-2015 KILL (substitute fixed 0.0478; pin post-decision quantity) — PR-01 / NHT-F1 / NHT-F2

**ANCHOR:**
```
> **POST-2015 KILL (mandatory):** The runner computes the primary statistic **separately** on the post-2015 sub-window (`date >= 2015-01-01`, 345 deduped Scenario A days) and writes it to the result YAML **before** the decision functional fires. If the post-2015 sub-window FAILS the primary test (does not clear `[MATH primary alpha]`), the structure is **KILLED — and this overrides any full-window aggregate pass.** An aggregate-only pass carried by pre-2015 data is dead alpha in the current regime (§2.3). The 2015-01-01 cutoff is the documented structural-break endpoint, not the sample midpoint (§3.4). BOC-gap confound disclosed (§3.4b).
```

**REPLACEMENT:**
```
> **POST-2015 KILL (mandatory):** The runner computes the SAME primary POST-decision statistic (§5.0 / §5.1) **separately** on the post-2015 sub-window (`date >= 2015-01-01`, 345 deduped Scenario A days) and writes `p_post2015` to the result YAML **before** the decision functional fires. If the post-2015 sub-window does NOT cleanly reject — i.e. **`p_post2015 > 0.0478`** (the same fixed gate) — the structure is **KILLED, and this overrides any full-window aggregate pass** (PART II §4.2 RULE 1, evaluated FIRST). An aggregate-only pass carried by pre-2015 data is dead alpha in the current regime (§2.3). The component under test in BOTH windows is the POST-decision reaction (the `K_post = 2` window return, §4.2/§5.0) — the documented-dead PRE-announcement drift is NOT tested by any criterion (§2.3, §5.0). The 2015-01-01 cutoff is the documented structural-break endpoint, not the sample midpoint (§3.4). BOC-gap confound disclosed (§3.4b).
```

---

## PATCH A4 — NEW §5.0 (pin the hypothesis-identity statement + the frozen sign-alignment rule) — NHT-F2 / NHT-F5

**ANCHOR** (insert immediately before §5.1; anchor on the §5.1 header line, replacing it with NEW §5.0 followed by the unchanged §5.1 header):
```
### 5.1 Primary falsification criterion (structure owned here; value is MATH's)
```

**REPLACEMENT:**
```
### 5.0 What is tested (hypothesis identity) and the FROZEN sign-alignment rule — NHT-F2 / NHT-F5

**Component under test (pinned, unambiguous).** Every §5 criterion tests the **POST-decision reaction component**: the `K_post = 2` cumulative net-of-cost return from the close of the decision-reflecting bar `D` to the close of `D + K_post`, entered at `D+1` under `entry_delay_bars = 1` (§4.2, §4.3). The PRE-announcement drift is documented essentially DEAD post-2015 (§2.3) and **NO pre-drift criterion exists anywhere in this document or its sidecar** — neither the primary, the post-2015 KILL, nor the reversal sub-claim references the pre-window as a source of edge. The `K_pre = 1` bar enters ONLY as the sign-alignment input below, never as a tested return. (The `.triggers.yaml` sidecar is being rebuilt in parallel to test this same post-decision `K_post=2` quantity — its prior pre-window/pre-drift primary metric is a known assembly defect, NHT-F2, corrected so doc and sidecar test the identical quantity.)

**FROZEN sign-alignment rule (one mechanical rule, no runtime judgment).** The firm has NO survey/consensus/expectations feed and the calendar carries only `{bank, currency, date}` — so a "surprise vs consensus" or "decision vs expectation" sign is **NOT computable** and is rejected. Rate-change sign is derivable for only some banks and is dominated by HOLDS post-2015, so it is also rejected as the primary mechanism. The pinned rule is therefore the **realized-initial-reaction continuation rule**, computable from the data the firm HAS:

> **`sign_align_e = sign( close(D) − close(D-1) )`** measured on the bank-event's mapped leg (the per-bank reference pair, fixed in §3.2 ordering; for the equal-weight bank-event the same `sign_align_e` scalar is applied to every responsive pair so the bank-event remains one sign-aligned unit). The traded position over the post-window `[D+1 close … D+K_post close]` is **LONG `sign_align_e`** — i.e. the strategy bets the initial reaction realized within bar `D` **continues** through the `K_post = 2` window. If `close(D) = close(D-1)` exactly (measure-zero tie), `sign_align_e = 0` and the event is FLAT (excluded from the realized return; its event-day still counts as a block-day, §5.5 convention).

**What the strategy then claims.** With this rule the registered alpha is a **continuation of the post-announcement initial reaction** (not a reversal of a pre-event move, and not a mean-reversion of the reaction). The §5.3 "reversal asymmetry" sub-claim is the COMPLEMENTARY diagnostic: it asks whether the continuation is partial (the reaction neither fully persists, 0% reversal, nor fully unwinds, 100% reversal) — it does not change the primary's continuation direction.

**No-look-ahead proof (the load-bearing check, NHT-F5).** `sign_align_e` uses `close(D)` and `close(D-1)` — both known at the close of bar `D`. The entry executes at the **open/close of `D+1`** under the engine's `entry_delay_bars = 1` invariant (§4.3, `test_no_lookahead`). The realized post-window return runs from `D+1` forward; it does **NOT** include the `D-1→D` bar used to form the sign. Therefore the sign is formed strictly from information available at-or-before `D` and the traded return is strictly after `D` — no bar is both a sign-input and a realized-return bar without the mandatory `entry_delay_bars` shift. The bar-`D` return (the initial reaction itself) is the SIGNAL, consumed at signal-formation time; it is **not** part of the realized P&L, so using its own sign creates no look-ahead into the `D+1` entry. The genre's silent leak (treating bar `D` as PRE-decision and letting the announcement reaction sneak into the realized window) is closed by §4.1's "bar `D` is the first decision-reflecting bar" convention combined with this rule.

**Compatibility flag (Mathematician sign-off, running in parallel).** This sign rule pins PART II §1.1's `sign_align_e` ("a-priori directional hypothesis, NO data-driven sign fit") to the realized-initial-reaction-continuation function above. It is **NOT** a data-driven *fit* (no free parameter is estimated from returns; the sign is a deterministic function of two adjacent closes), but it IS a function of price, so it is flagged for the Mathematician's compatibility sign-off that (a) the HAC/block-bootstrap studentization in PART II §1.3–§1.4 is unaffected (the bootstrap resamples the already-signed scalar `r_e`), and (b) the one-sided `H1: E[r_e] > 0` remains correct under continuation (a true continuation edge makes the signed return positive in expectation). MATH compatibility status: PENDING parallel sign-off.

### 5.1 Primary falsification criterion (structure owned here; value is MATH's)
```

---

## PATCH A5 — §5.3 reversal sub-claim (substitute the live `[MATH]` token) — PR-01 / NHT-F1

**ANCHOR:**
```
KILL the reversal sub-claim if the reversal fraction is statistically indistinguishable from 0% OR from 100% (the exact two-sided distinguishability test and its threshold are MATH's, `[MATH]`).
```

**REPLACEMENT:**
```
KILL the reversal sub-claim if the realized post-decision reaction fraction is statistically indistinguishable from 0% (no reaction) OR from 100% (full unwind) — i.e. no exploitable partial continuation exists. The two-sided distinguishability test uses the SAME bank-blocked stationary-block-bootstrap machinery (PART II §1.4, §3) at the same fixed gate (a two-sided `p ≤ 0.0478` against each of the 0% and 100% nulls; both must reject for the sub-claim to survive). This is a secondary/diagnostic sub-claim on the post-decision component (§5.0); it does not alter the primary continuation direction or the primary/post-2015 p-gates.
```

---

## PATCH A6 — §5.4 retirement triggers (substitute live tokens; renumber DSR gate as §5.7 cross-ref) — PR-01 / NHT-F1

**ANCHOR:**
```
- `full_window primary p >= [MATH primary alpha]` → **KILL** (no aggregate edge).
- `post_2015 primary p >= [MATH primary alpha]` → **KILL**, `overrides_aggregate_pass: true` (the structural-break kill, §5.2).
- `reversal_fraction indistinguishable from 0% OR from 100%` → **KILL** the reversal sub-claim (§5.3).
- `per_bank_sharpe` floor breach (secondary; `[MATH]` floor) → flagged, advisory unless MATH binds it.
- On any KILL: archive `qrb6_cb_event_study` as RETIRED/FALSIFIED (pointer to this pre-reg, freeze-receipt, result YAML). QRB-3 (queued runner-up) advances to a subsequent wave only on a post-2015 KILL.
```

**REPLACEMENT:**
```
- `p_post2015 > 0.0478` → **KILL**, `overrides_aggregate_pass: true` (the structural-break kill, evaluated FIRST; §5.2, PART II §4.2 RULE 1).
- `p_agg > 0.0478` → **KILL** (no aggregate edge; §5.1, PART II §4.2 RULE 2).
- `reversal_fraction indistinguishable from 0% OR from 100%` → **KILL** the reversal sub-claim (§5.3).
- `DSR < 0.95` at `SR0_pp_sel = 0.026861` (equivalently aggregate-set ann Sharpe < `kill_switch_threshold = 1.5883`, Scenario A) → **no PASS** even when both p's cleanly reject; the rejection cannot clear the `N_sel = 3` selection charge (→ RULE 4; §5.7, §6, PART II §4.2).
- `per_bank_sharpe` floor breach (secondary; advisory) → flagged, advisory unless MATH binds it (no numeric floor is registered as a hard gate; PART II reports per-bank Sharpe as a secondary metric only).
- On any KILL: archive `qrb6_cb_event_study` as RETIRED/FALSIFIED (pointer to this pre-reg, freeze-receipt, result YAML). QRB-3 (queued runner-up) advances to a subsequent wave only on a post-2015 KILL.
```

---

## PATCH A7 — NEW §5.7 (the DSR selection gate, stated directly — the charge mechanism that REPLACES the absorbed-into-alpha prose) — PR-01 / NHT-F1

**ANCHOR** (insert immediately before §5.6; anchor on the §5.6 header line):
```
### 5.6 Graduation map (a pass is not capital)
```

**REPLACEMENT:**
```
### 5.7 DSR selection-deflation gate — where the multiplicity charge LIVES (stated directly)

The 11-proposal portfolio selection charge AND the 2-finalist (QRB-6 vs QRB-3) comparison charge are charged **entirely through this gate**, NOT on the p-value scale (this REPLACES the earlier draft's "absorbed into the primary alpha (~0.0025)" mechanism, which is superseded by PART II §4.2). The paper-selection multiplicity is frozen at `N_sel = 3` (PART II §2; a paper-selection — nothing was backtested — so `N_sel` charges one real one-shot look + ~2 effective soft-prior framings, NOT R5's data-selection N=6). The deflation benchmark is `SR0_pp_sel = 0.026861` (annualized `SR0_ann_sel = 0.426402`; `N_sel = 3`, dispersion `0.50`; PART II §2.5).

> **DSR GATE:** A PASS requires `DSR ≥ 0.95` at `SR0_pp_sel = 0.026861`, equivalently the aggregate-set annualized Sharpe `≥ kill_switch_threshold = 1.5883` (Scenario A, T=506) / `1.4029` (Scenario B, T=716; §4.2/§6). `DSR < 0.95` → no PASS even with both p-gates cleanly rejecting (→ RULE 4). This is the SOLE locus of the selection-multiplicity charge; the p-gates remain at the fixed `0.0478`.

### 5.6 Graduation map (a pass is not capital)
```

> NOTE: §5.7 is intentionally placed before §5.6 in source order so the gate that §5.4/§5.1 cross-reference is defined before the graduation map reads it. Numbering is non-sequential in source but the cross-references (§5.7) resolve correctly. (If the orchestrator prefers strict ascending order, relabel this block §5.5b and update the three §5.7 cross-refs in PATCH A2/A6 accordingly — flagged, non-blocking.)

---

## PATCH A8 — §5.6 graduation map (substitute live `[MATH]` tokens) — PR-01 / NHT-F1

**ANCHOR:**
```
A full PASS (full-window primary clears `[MATH]` AND post-2015 sub-window clears `[MATH]` AND reversal distinguishable from both 0%/100%) authorizes **only** a named next governance step: author a fresh, separately-pre-registered observe-only paper canary under its own HoQR+Math+NHT ratification and its own trial id. PASS here does NOT authorize capital, does NOT re-open the proposal portfolio, and does NOT license exploration.
```

**REPLACEMENT:**
```
A full PASS (`p_agg ≤ 0.0478` AND `p_post2015 ≤ 0.0478`, both clean rejections outside the straddle band, AND `DSR ≥ 0.95` at `SR0_pp_sel = 0.026861`; reversal distinguishable from both 0%/100% for the reversal sub-claim) authorizes **only** a named next governance step: author a fresh, separately-pre-registered observe-only paper canary under its own HoQR+Math+NHT ratification and its own trial id. PASS here does NOT authorize capital, does NOT re-open the proposal portfolio, and does NOT license exploration. (This is PART II §4.2 RULE 3 restated.)
```

---

## PATCH A9 — §4.1 daily-bar timestamp convention (correct the phantom 21:00-UTC citation echo) — PR-05

**ANCHOR:**
```
**Schema fact (verified from the index of `data/processed/{PAIR}_daily.parquet`, no returns read):** daily bars are timestamped at **00:00:00 UTC** (tz-aware UTC DatetimeIndex; every observed hour-of-day is 0). The bar dated `D 00:00 UTC` is the daily OHLC for the UTC calendar day `D`. Announcements occur **intraday**, at bank-local times, so the daily bar that first REFLECTS a decision differs by bank timezone:
```

**REPLACEMENT:**
```
**Schema fact (verified from the index of `data/processed/{PAIR}_daily.parquet`, no returns read):** daily bars are timestamped at **00:00:00 UTC** (tz-aware UTC DatetimeIndex; every observed hour-of-day is 0 — verified directly from the EURUSD_daily index, terminus 2026-04-06). The bar dated `D 00:00 UTC` is the daily OHLC for the UTC calendar day `D`. This 00:00-UTC convention is established by that index check alone; there is no competing CLAUDE.md timestamp note (an earlier draft assumption referenced a "21:00-UTC CLAUDE.md note" that does NOT exist — it originated from a dispatch prompt, not CLAUDE.md, and is struck). Announcements occur **intraday**, at bank-local times, so the daily bar that first REFLECTS a decision differs by bank timezone:
```

---

## PATCH A10 — §7 sidecar path (qrb6_triggers.yaml → qrb6_cb_event_study.triggers.yaml; fix §7 completeness claim) — NHT-F4

**ANCHOR:**
```
**Sidecar:** all kill conditions in §5 are machine-encoded in the `.triggers.yaml` sidecar at `references/pre-registrations/qrb6_triggers.yaml` (QD authors; AC-3b). Every prose kill condition here has a corresponding machine-readable entry there: primary p-threshold, post-2015 sub-window kill with `overrides_aggregate_pass: true`, reversal-distinguishability, `spread_z` overlay threshold with suppress-entry semantics, and the per-bank secondary metric floor. The trial registers (BC-1, counter at 41) only at the moment the freeze-receipt is cut.
```

**REPLACEMENT:**
```
**Sidecar:** all kill conditions in §5 are machine-encoded in the `.triggers.yaml` sidecar at `references/pre-registrations/qrb6_cb_event_study.triggers.yaml` (QD authors; AC-3b). Every prose kill condition here has a corresponding machine-readable entry there, testing the SAME post-decision `K_post=2` quantity (§5.0): the fixed `p ≤ 0.0478` primary gate, the post-2015 sub-window kill with `overrides_aggregate_pass: true`, the DSR ≥ 0.95 selection gate (`SR0_pp_sel = 0.026861`, `N_sel = 3`), the reversal-distinguishability sub-claim, and the `spread_z` overlay threshold with suppress-entry semantics. (The per-bank Sharpe is a secondary/advisory metric, not a hard trigger.) The sidecar is being rebuilt in parallel to test the post-decision quantity (NHT-F2) — doc and sidecar must test the identical `r_e` at freeze. The trial registers (BC-1, counter at 41) only at the moment the freeze-receipt is cut.
```

---

## PATCH A11 — §7 freeze mechanics: add the permitted-pre-freeze-changes clause (R5 precedent, runner + receipt interlock) — NHT-F6

**ANCHOR:**
```
**Receipt-before-any-return-data-examination (the cryptographic boundary):** no OHLCV return, equity curve, Sharpe, or test statistic may be computed on `data/processed/{PAIR}_{daily,4h}.parquet` before the freeze-receipt is committed to git. The orchestrator confirms the receipt exists in git before any return-computing data-access command. This boundary is what makes the QRB-6 p-value face-valid (Lopez de Prado; AC hard-constraint `no_return_data_examination_before_freeze`).
```

**REPLACEMENT:**
```
**Receipt-before-any-return-data-examination (the cryptographic boundary):** no OHLCV return, equity curve, Sharpe, or test statistic may be computed on `data/processed/{PAIR}_{daily,4h}.parquet` before the freeze-receipt is committed to git. The orchestrator confirms the receipt exists in git before any return-computing data-access command. This boundary is what makes the QRB-6 p-value face-valid (Lopez de Prado; AC hard-constraint `no_return_data_examination_before_freeze`).

**Permitted pre-freeze code changes (R5 precedent — the ONLY permitted post-freeze code object).** Mirroring the R5 STEP-4 runner precedent: exactly ONE named code object is a permitted pre-freeze artifact — the QRB-6 one-shot runner (the "look"/STEP-4-style runner, `scripts/run_qrb6.py` or equivalent), which is authored and committed BEFORE the freeze-receipt is cut and is then **pinned by the freeze commit** (`receipt.code_commit == pinned commit`, §1.4(5)). The runner is interlocked with the receipt: it **REFUSES to execute unless it reads a committed freeze-receipt whose `prereg_sha256` matches `sha256(this file as committed)` and whose `code_commit` matches the runner's own commit** (a hash-matching receipt interlock — no receipt, or a mismatched hash, ⇒ TECHNICAL_FAILURE / RULE 0, never a silent run). The freeze-receipt cut is therefore explicitly ORDERED AFTER the runner commit exists and is pinned (closes NHT-F6's "ordering implied, not enforced"). **No other post-freeze code change is permitted:** once the receipt is cut, neither this pre-reg, the sidecar, nor the runner may be edited — any edit changes the hash and the interlock refuses, voiding the run (§1.4(2), §1.4(5)). This single named exception (runner pinned by the freeze commit + hash-matching receipt interlock) is the complete permitted-pre-freeze-changes set; everything else is frozen.
```

---

# SECTION B — `.fintech-org/artifacts/2026-06-06T-qrb6-prereg/qr-prereg-draft.yaml`

---

## PATCH B1 — draft assumption line ~127: strike the phantom CLAUDE.md 21:00-UTC citation — PR-05

**ANCHOR:**
```
  - "The 00:00-UTC daily-bar convention (verified from index) supersedes the CLAUDE.md 21:00-UTC note for THIS dataset; documented honestly in the pre-reg windows section."
```

**REPLACEMENT:**
```
  - "The 00:00-UTC daily-bar convention is verified directly from the EURUSD_daily parquet index (all hour-of-day=0, tz-aware UTC, terminus 2026-04-06). There is NO CLAUDE.md 21:00-UTC note — the earlier '21:00-UTC CLAUDE.md' reference was a phantom citation (it came from a dispatch prompt, not CLAUDE.md) and is struck; the index check is the sole and sufficient evidence."
```

---

## PATCH B2 — draft falsification_criteria PRIMARY/POST2015 (substitute live `[MATH primary alpha]` tokens with fixed 0.0478 + DSR locus) — PR-01 / NHT-F1

**ANCHOR:**
```
  - id: PRIMARY
    form: "pooled banks-as-blocks block-bootstrap p-value for H0:E[net event-window return]<=0 >= [MATH primary alpha] -> KILL"
    machine_checkable: true
  - id: POST2015_KILL
    form: "post_2015 sub-window (date>=2015-01-01, 345 deduped days) primary p >= [MATH primary alpha] -> KILL; overrides_aggregate_pass: true"
    machine_checkable: true
    mandatory: true
```

**REPLACEMENT:**
```
  - id: PRIMARY
    form: "pooled banks-as-blocks stationary-block-bootstrap p-value for H0:E[net POST-decision K_post=2 return]<=0 > 0.0478 (fixed gate alpha 0.05 - MC-SE 0.0022, K=10000) -> KILL. Multiplicity (N_sel=3) charged via DSR gate ONLY, NOT on this p-threshold (PART II 4.2)."
    machine_checkable: true
  - id: POST2015_KILL
    form: "post_2015 sub-window (date>=2015-01-01, 345 deduped days) SAME post-decision primary p > 0.0478 -> KILL; overrides_aggregate_pass: true; evaluated FIRST (PART II 4.2 RULE 1)"
    machine_checkable: true
    mandatory: true
  - id: DSR_SELECTION_GATE
    form: "PASS requires DSR >= 0.95 at SR0_pp_sel=0.026861 (N_sel=3, disp=0.50), equiv aggregate-set ann Sharpe >= kill_switch_threshold 1.5883 (A) / 1.4029 (B). DSR<0.95 with both p clean -> no PASS (RULE 4). SOLE locus of the 11-proposal + 2-finalist selection charge."
    machine_checkable: true
```

---

## PATCH B3 — draft `metric` field (substitute the placeholder with the pinned sign-aligned post-decision quantity) — NHT-F2 / NHT-F5

**ANCHOR:**
```
metric: "[frozen by Mathematician — see PART II]"
```

**REPLACEMENT:**
```
metric: "r_e = sign_align_e * (net-of-cost cumulative K_post=2 POST-decision return from close of D to close of D+K_post, on the bank-event's responsive pairs, equal-weight averaged). sign_align_e = sign(close(D) - close(D-1)) on the mapped leg — realized-initial-reaction CONTINUATION (no survey/expectations feed exists; rate-change sign rejected, holds dominate post-2015). No look-ahead: sign known at close(D); entry at D+1 (entry_delay_bars=1); bar-D return is signal not P&L. Studentization/bootstrap frozen in PART II §1.3-1.4, §3; MATH compatibility sign-off PENDING (parallel)."
```

---

## PATCH B4 — draft `windows.post_window` (make the post-decision continuation explicit) — NHT-F2 / NHT-F5

**ANCHOR:**
```
  post_window: "K_post = 2 bars after the decision is realized — the claimed-edge window (sign-aligned cumulative net return from close of D)"
```

**REPLACEMENT:**
```
  post_window: "K_post = 2 bars after the decision is realized — the claimed-edge window (sign-aligned cumulative net return from close of D to close of D+K_post). sign_align_e = sign(close(D)-close(D-1)); position = LONG sign_align_e = CONTINUATION of the initial reaction. The pre-window K_pre=1 is the sign INPUT only, never a tested return; no pre-drift criterion exists."
```

---

# APPLY-ORDER SUMMARY

| # | File | Finding(s) closed |
|---|------|-------------------|
| A1 | doc §5 preamble | PR-01 / NHT-F1 |
| A2 | doc §5.1 | PR-01 / NHT-F1 |
| A3 | doc §5.2 | PR-01 / NHT-F1 / NHT-F2 |
| A4 | doc NEW §5.0 | NHT-F2 / NHT-F5 |
| A5 | doc §5.3 | PR-01 / NHT-F1 |
| A6 | doc §5.4 | PR-01 / NHT-F1 |
| A7 | doc NEW §5.7 | PR-01 / NHT-F1 |
| A8 | doc §5.6 | PR-01 / NHT-F1 |
| A9 | doc §4.1 | PR-05 |
| A10 | doc §7 sidecar path | NHT-F4 |
| A11 | doc §7 freeze mechanics | NHT-F6 |
| B1 | draft assumption ~127 | PR-05 |
| B2 | draft falsification_criteria | PR-01 / NHT-F1 |
| B3 | draft metric | NHT-F2 / NHT-F5 |
| B4 | draft windows.post_window | NHT-F2 / NHT-F5 |

**Zero live `[MATH]` / `[MATH primary alpha]` tokens remain in §5 or the draft falsification fields after A2/A3/A5/A6/A8 + B2.** All seven §5 tokens (§5.1, §5.2, §5.3, §5.4×2, §5.6×2) are substituted with the fixed `0.0478` p-gate and the DSR gate is stated directly as the sole multiplicity-charge locus. The absorbed-into-alpha (~0.0025) mechanism is struck everywhere.
