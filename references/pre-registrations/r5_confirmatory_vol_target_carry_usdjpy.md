# R5-CONFIRMATORY PRE-REGISTRATION — Single-Structure Confirmatory Kill Test

**Document status:** ASSEMBLED v1 (2026-06-06) — HoQR PART I + Mathematician PART II merged (constants scipy-exact per mathematician-z2-election.yaml + qd-constants-confirmation.yaml); PENDING NHT audit, principal-reviewer review, consensus ratification, CEO sign-off, freeze-receipt. Becomes BINDING and FROZEN only on consensus ratification (HoQR + Mathematician + NHT + principal-reviewer) + CEO sign-off + an EXTERNAL write-once freeze-receipt (SHA-256 of this file as committed + pinned code-commit hash). No hold-out data may be accessed and no metric computed on post-2026-04-06 data before the freeze-receipt is committed.

**Track:** r5-confirmatory-2026-06-06 / Phase 1 / Task 1.0
**New Trial ID:** `f2fb41fd` (org-wide counter increment; registered in `.fintech-org/trials.jsonl`. This trial NEVER reuses the R5 family id `576746aa`.)
**Spawned by:** R5 terminal kill-test outcome AMBIGUOUS_GATE_FAIL (2026-06-06), per the frozen R5 §5 outcome 4 / §7.3.6 RULE 4 confirmatory-only gate.
**Authoritative parent:** `references/pre-registrations/r5_carry_universe_kill_test.md` (IMMUTABLE — this document references it and never edits it) and its result `references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.yaml`.
**Acceptance criteria:** `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/pm-acceptance-criteria.yaml`

---

## 1. Preamble & Confirmatory Contract (HoQR) — criterion CONF-structure / CONF-decision-map context

### 1.1 What this pre-registration IS

This document is a **confirmatory-only statistical test of ONE pre-specified structure** — `vol_target_carry:USDJPY` — on **unsnoopable future data that does not yet exist at freeze time** (post-2026-04-06 daily bars). It is spawned by the R5 terminal kill test's AMBIGUOUS_GATE_FAIL outcome (`r5_carry_universe_kill_test.STEP4-RESULT.yaml:2` `decision: AMBIGUOUS_GATE_FAIL`), which under the frozen R5 decision functional (§7.3.6 RULE 4 → §5 outcome 4) maps to **exactly one permitted forward action: a fresh, separately-pre-registered confirmatory test of the single surviving structure**, with no free exploration and no capital.

The R5 family p was discordant: `p_SPA = 0.0162` (class-level rejection at the consistent estimate) but `p_RC = 0.0588 > 0.05` (White Reality Check did NOT concur), with `DSR = 0.9503` clearing the ≥0.95 gate by +0.0003 (`STEP4-RESULT.yaml:3,7,8`). A boundary/discordant family result is precisely the artifact R5 was built to refuse to over-interpret. This confirmatory test exists to convert that ambiguity into a clean binary on the ONE cell that won the family max-statistic — on data the firm cannot have snooped, because it has not happened yet.

This pre-registration freezes — before any future bar is accessed — every degree of freedom: the exact structure and its config (Section 2), the hold-out window rule and look-date governance (Section 3), the null/statistic/honest-N/selection-absorption and the alpha-spending look design (Mathematician sections), the decision map under every outcome at every look (Section 4), the interim observe-only state (Section 5), and the kill-switch threshold (Section 6). Freezing these on not-yet-existing data is what makes the resulting p face-valid.

### 1.2 What this pre-registration is NOT

- **NOT a family re-open.** The R5 36-cell carry family is closed. No variant search, no pair search, no re-parameterization of any of the 36 cells is authorized by this document. (R5 §5 outcome 4: "the 36-cell family research is not re-opened.")
- **NOT exploration.** No new hypotheses are generated here. Genuinely-new alpha tracks require their own fresh pre-registrations (Section 5 capacity redirect).
- **NOT a validation shortcut or rescue attempt.** A confirmatory PASS does NOT itself authorize capital. It authorizes only a named, governance-gated next step (Section 4). The base-rate honest expectation, given the power reality (Mathematician section), is that a single ~0.77-Sharpe monthly-stale series will take years to confirm and may well fail — wind-down remains the most-likely terminal state of the carry program.
- **NOT a re-run of R5.** This document never edits, re-runs, or re-interprets the R5 SPA/White-RC test on any window. R5 is frozen and immutable.

### 1.3 VOID conditions (the confirmatory contract)

This pre-registration's result is **VOID and not face-valid** if any of the following occur:

1. **Parameter change / structure drift.** Any deviation from the **AS-EXECUTED** pin table in §2.2 — `target_vol=0.10`, `vol_window=252`, signal-`leverage_cap=2.0`, **`min_carry=-inf` (no carry filter — strategy default, NOT the config's -0.10)**, sizer `leverage_cap=2.0`/`max_order_units=5_000_000.0`/`min_order_size=100.0`, `rebalance_threshold=0.20`, `rebalance_mode=continuous`, `entry_delay_bars=1`, the `_DEFAULT_PAIR_INFO["USDJPY"]` cost params, and the `VolTargetSizer` sizer type — between freeze and evaluation voids confirmatory status. The structure is tested AS-EXECUTED-BY-R5. **In particular: the confirmatory runner MUST pass no `variant_params` for the strategy-default-sourced signal parameters (`target_vol`, `vol_window`, signal-`leverage_cap`, `min_carry`), exactly as the R5 STEP4 runner did (`scripts/run_r5_step4.py:312-316`).** Supplying any `variant_params` override — including one that "restores" the config's `min_carry=-0.10` — changes the executed structure and is itself a VOID (it would impose a carry filter the R5 survivor never ran). The structure is tested exactly as the family selected it, not as the config nominally describes it.
2. **Early peek.** Any computation of strategy performance on any post-2026-04-06 bar before a frozen look date (Section 3) voids the test. The interim monitoring state (Section 5) records data accrual and mechanical data-integrity only — NEVER strategy P&L or any test statistic.
3. **Missing selection-absorption.** If the frozen honest-N / SR0 deflation inputs (Mathematician section) do NOT charge the R5 36-cell argmax selection as a spent look, the confirmatory p is a garden-of-forking-paths violation and is VOID. (R5 §4 / §5 outcome 4, BINDING: "MUST absorb the R5 36-cell selection burden in its own honest-N / deflation inputs.")
4. **Missing new trial_id.** If the run registers under `576746aa` or fails to increment the org-wide counter, it is VOID. (This document's trial is `f2fb41fd`.)
5. **Freeze mismatch.** If `receipt.prereg_sha256 != sha256(this file as committed)` or `receipt.code_commit != pinned commit` (Section 2 / freeze block), the run executed against an unfrozen or drifted spec and is VOID.

### 1.4 Lineage

```
R5 family trial 576746aa  (36-cell SPA/White-RC kill test, AMBIGUOUS_GATE_FAIL 2026-06-06)
        │  k* = vol_target_carry:USDJPY selected as family argmax max-statistic
        │  (selection is a SPENT LOOK — charged in this test's honest-N, NOT free)
        ▼
Confirmatory trial f2fb41fd  (THIS document — single-cell, post-2026-04-06, no capital)
```

`f2fb41fd` is a distinct child trial, not a continuation of `576746aa`. The R5 documents and freeze-receipt are immutable; this document only references them.

---

## 2. The Structure Under Test (HoQR) — criterion CONF-structure

### 2.1 The single locked structure

The ONLY structure this confirmatory test may evaluate is the R5 family argmax:

> **`k* = vol_target_carry:USDJPY`** — selected as `k_star_idx: 18`, `k_star_label: vol_target_carry:USDJPY` in the R5 result (`r5_carry_universe_kill_test.STEP4-RESULT.yaml:9-10`), at in-sample annualized Sharpe `0.7672`, skew `0.1963`, excess kurtosis `8.2783`, over `T = 4186` common-index bars (`STEP4-RESULT.yaml:11-13,17`).

No other cell of the 36-cell R5 universe is in scope. No pair other than USDJPY. No variant other than `vol_target_carry`.

### 2.2 Verbatim config pin

The structure is pinned to the parameter values **AS EXECUTED by the R5 k\* cell** — i.e. as the R5 matrix builder actually constructed `vol_target_carry:USDJPY` at commit `350cbd4`. This is NOT the same as the committed `config/vol_target_carry.yaml`. **CRITICAL provenance fact (verified this session):** the R5 STEP4 runner called `build_joint_return_matrix(variants=..., pairs=...)` with **no `variant_params` argument** (`scripts/run_r5_step4.py:312-316`), so the strategy was built as `params = {"pair": "USDJPY"}` only (`carry_universe_matrix.py:483-484`, with `variant_params={}` resolved at `:652,658`). Consequently the strategy SIGNAL parameters that `_VARIANT_EXEC` does not carry fell to their **strategy defaults**, NOT to the config. In particular `min_carry` ran at the strategy default `-inf` (no carry filter ever fired), and the config's `-0.10` was **NOT in effect**. A confirmatory test must reproduce the structure the survivor executed; pinning the config value would freeze a DIFFERENT structure and VOID-condition-1 could not detect the discrepancy (a faithful re-run of `350cbd4` shows zero drift while silently using `-inf`).

The pin below therefore states, for EVERY parameter, its AS-EXECUTED provenance — one of:
- **config-via-`_VARIANT_EXEC`**: sourced from `config/vol_target_carry.yaml` and threaded into the run by a `_VariantExecConfig` field (`carry_universe_matrix.py:242-296`) — these were genuinely in effect from config;
- **strategy-default (builder passes nothing)**: the field is NOT a `_VariantExecConfig` field and the runner passed no `variant_params`, so `VolTargetCarryStrategy` used its own `params.get(..., default)` fallback — the config value, if any, was NOT in effect.

| Parameter | Value AS EXECUTED | AS-EXECUTED provenance | Config value (for reference) |
|---|---|---|---|
| variant | `vol_target_carry` | selector key into `_VARIANT_EXEC` (`carry_universe_matrix.py:266`) | `config/vol_target_carry.yaml:33` (match) |
| pair | `USDJPY` | passed explicitly: `params={"pair": pair, ...}` (`carry_universe_matrix.py:483`) | n/a (pair is the cell axis) |
| `target_vol` | `0.10` | **strategy-default** — NOT a `_VariantExecConfig` field; builder passes no `variant_params`; `params.get("target_vol", 0.10)` (`vol_target_carry.py:57`). Config 0.10 coincides with default but was NOT sourced. | `config/vol_target_carry.yaml:33` = 0.10 (coincides) |
| `vol_window` | `252` | **strategy-default** — NOT a `_VariantExecConfig` field; `params.get("vol_window", 252)` (`vol_target_carry.py:58`). Config 252 coincides but was NOT sourced. | `config/vol_target_carry.yaml:34` = 252 (coincides) |
| `leverage_cap` (signal clip) | `2.0` | **strategy-default** — the value the *signal generator* uses to normalize the position fraction: `params.get("leverage_cap", 2.0)` (`vol_target_carry.py:59`). Builder passes no `variant_params`, so the strategy default 2.0 (which coincides with config) is what clipped the signal. | `config/vol_target_carry.yaml:35` = 2.0 (coincides) |
| `leverage_cap` (sizer) | `2.0` | **config-via-`_VARIANT_EXEC`** — `_VARIANT_EXEC["vol_target_carry"].leverage_cap=2.0` (`carry_universe_matrix.py:271`) → `_build_sizer` → `VolTargetSizer(leverage_cap=2.0)` (`:418-432`). Genuinely config-sourced. | `config/vol_target_carry.yaml:35,44` = 2.0 |
| `min_carry` | **`-inf`** | **strategy-default — config's -0.10 was NOT in effect.** NOT a `_VariantExecConfig` field; builder passes no `variant_params`; `params.get("min_carry", -np.inf)` (`vol_target_carry.py:60`). The carry filter runs ONLY `if min_carry > -np.inf` (`:72`), so with `-inf` the filter was a no-op: **the R5 k\* cell traded the vol-targeted signal unconditionally, with NO carry filter.** | `config/vol_target_carry.yaml:36` = -0.10 (**NOT in effect**) |
| `rebalance_threshold` | `0.20` | **config-via-`_VARIANT_EXEC`** — `_VARIANT_EXEC[...].rebalance_threshold=0.20` (`carry_universe_matrix.py:268`), used by the engine via `exec_cfg.rebalance_threshold` (`:506`). | `config/vol_target_carry.yaml:37,51` = 0.20 |
| `rebalance_mode` | `continuous` | **config-via-`_VARIANT_EXEC`** — `_VARIANT_EXEC[...].rebalance_mode="continuous"` (`carry_universe_matrix.py:267`), via `exec_cfg.rebalance_mode` (`:505`). | `config/vol_target_carry.yaml:50` = continuous |
| sizer | `VolTargetSizer` | **config-via-`_VARIANT_EXEC`** — `sizer_type="vol_target"` (`carry_universe_matrix.py:269`) → `_build_sizer` returns `VolTargetSizer` (`:418-432`). | `config/vol_target_carry.yaml` position_sizing.method=vol_target |
| `max_order_units` | `5_000_000.0` | **config-via-`_VARIANT_EXEC`** — `_VARIANT_EXEC[...].max_order_units` (`carry_universe_matrix.py:272`) → `VolTargetSizer` (`:430`). | `config/vol_target_carry.yaml:46` = 5_000_000.0 |
| `min_order_size` | `100.0` | **config-via-`_VARIANT_EXEC`** — `_VARIANT_EXEC[...].min_order_size` (`carry_universe_matrix.py:273`) → `VolTargetSizer` (`:431`). | `config/vol_target_carry.yaml:45` = 100.0 |
| `entry_delay_bars` | `1` | passed by the harness backtest call (no-lookahead sacred invariant); builder threads `entry_delay_bars` into `_build_cell` (`carry_universe_matrix.py:457,508`). | `config/vol_target_carry.yaml:49` = 1 (coincides) |
| cost model | `RealisticCostModel`, USDJPY `PairInfo` (spread 1.0 / slippage 0.5 / commission 0.5 / swap_long 0.8 / swap_short -1.5 pips) | **builder default** — `_DEFAULT_PAIR_INFO["USDJPY"]` (`carry_universe_matrix.py:108-116`); R5 passed no `pair_infos` override, so these defaults were in effect. (These match the carry_fred.yaml-sourced costs the builder documents.) | `config/vol_target_carry.yaml:21-26` (coincides) |
| `initial_capital` | `1_000_000.0` | **builder default** — `_build_cell` default `initial_capital` (`carry_universe_matrix.py` default path). | `config/vol_target_carry.yaml:40` = 1_000_000.0 (coincides) |
| return convention | `equity_curve.pct_change()` net-of-cost simple returns | builder return path (`carry_universe_matrix.py:522-528`). | n/a |

**Summary of the config-vs-executed discrepancy (disclosed per F-001):** Three signal parameters (`target_vol`, `vol_window`, signal-`leverage_cap`) were pinned in the original draft to config but were in fact strategy-default-sourced — they happen to coincide with config, so the executed structure is unchanged, but the *provenance claim* was wrong. ONE parameter is materially discrepant: **`min_carry` executed at `-inf` (no carry filter), NOT the config's `-0.10`.** The confirmatory runner MUST reproduce `min_carry=-inf` (i.e. pass no `min_carry`, exactly as the R5 builder did) to test the structure the survivor actually executed. Pinning `-0.10` would test a carry-filtered variant the R5 family never selected — itself a VOID (structure drift, §1.3 condition 1).

### 2.3 Code commit lineage

The R5 freeze pinned the matrix builder at code commit **`350cbd4b592485f3bd935ec414ee007e63879de5`** (`r5_carry_universe_kill_test.STEP4-RESULT.yaml:62`). The confirmatory run MUST execute `vol_target_carry:USDJPY` under either:

- (a) the **same exec config at commit `350cbd4`** (`carry_universe_matrix._build_cell` / `_build_sizer` / `_VARIANT_EXEC["vol_target_carry"]`), OR
- (b) a **future-frozen successor commit verified behavior-equivalent** for this single cell — equivalence meaning byte-identical return series on a fixed shared sub-window. Because the original freeze-receipt is WRITE-ONCE (`scripts/cut_freeze_receipt.py:10-11,106-110` refuses to overwrite) and the look-runner does not exist at freeze time, the equivalence evidence is recorded NOT in the original receipt but in a **SUPPLEMENTARY write-once runner-receipt**:

  > **RUNNER-RECEIPT MECHANISM (FROZEN).** When the single-cell look-runner lands, a supplementary write-once file `r5_confirmatory_vol_target_carry_usdjpy.RUNNER-RECEIPT.yaml` is cut (same idempotent refuse-to-overwrite discipline as `cut_freeze_receipt.py`). It contains: (i) the successor runner commit hash; (ii) the equivalence-verification evidence (the fixed shared sub-window, the byte-identical-return-series proof / hash comparison against the commit-`350cbd4` reference series); (iii) a back-reference SHA-256 hash of the ORIGINAL freeze-receipt, binding the two receipts. The ORIGINAL freeze-receipt and this pre-reg (§2.3, FREEZE BLOCK) point FORWARD to it by name. **Cutting the runner-receipt is itself a quorum-gated act:** HoQR + Mathematician sign the equivalence determination; NHT may dissent. It MUST be cut and committed to git BEFORE the first look date (2028-10-06). If no behavior-equivalent successor is needed (the run uses commit `350cbd4` directly per path (a)), no runner-receipt is cut and option (b) is unused.

Any non-equivalent code change to the execution path voids confirmatory status (Section 1.3 condition 1 + 5).

The current working HEAD at draft time is `1c533e8` (informational only; the binding pin is set at freeze).

### 2.4 Single-cell hypothesis H1

The confirmatory alternative is: **`vol_target_carry:USDJPY` has positive expected net-of-cost return / annualized Sharpe strictly greater than zero, net of the confirmatory deflation charge** on the post-2026-04-06 hold-out. The exact null/statistic/deflation formulation is the Mathematician's:

> **MERGED — see PART II §1 (Null Hypothesis & Test Statistic) and PART II §2 (Selection-Absorption Mechanism).**
> CONF-statistic: frozen null H0 for the single-series confirmatory test; the test statistic and method (single-series studentized t / single-cell SPA); the selection-absorption mechanism (how the R5 36-cell argmax is charged as a spent look in the confirmatory honest-N and SR0); the DSR formula inputs for the confirmatory cell, with R5 k* statistics (SR_ann=0.767, skew=0.196, xkurt=8.28) as prior-look anchors only — the confirmatory run uses the hold-out cell's own metrics.

---

## 3. Hold-Out & Calendar Governance (HoQR; co-signed Mathematician) — criterion CONF-holdout

### 3.1 The hold-out window rule (a RULE, not a single date)

> **HOLD-OUT RULE.** The confirmatory return series is computed ONLY from USDJPY daily bars dated **strictly after 2026-04-06** — the R5 common-index terminus (`r5_carry_universe_kill_test.STEP4-RESULT.yaml`; R5 common index ran 2010-03-15 → 2026-04-06, T=4186). There is **zero overlap** with any bar R5 saw. No bar on or before 2026-04-06 enters the confirmatory test under any circumstance.

This is a forward rule over data that does not exist at freeze: the hold-out is unsnoopable by construction because it has not yet been generated.

### 3.2 Data-accrual expectation

USDJPY daily bars accrue at ~250 trading-day bars/year. The signal feed is the cross-currency rate differential (`data/rates/rate_differentials.parquet`), which is **monthly forward-filled** — so the EFFECTIVE information arrival is ~12 fresh rate observations/year (~1 effective obs/month). Calendar-time hold-out length therefore vastly overstates statistical information; the Mathematician converts calendar time to effective observations in the power section. The R5 doc's own power statement (§6) anchors the order of magnitude: at true ann Sharpe ~0.77, ~4.6 years of hold-out for ~50% power, ~10 years for ~80%.

> **MERGED — see PART II §1 (statistic validity / minimum-n guards) and PART II §3 (effective-observation conversion inside the look schedule).**
> CONF-holdout (Math co-sign): minimum T_holdout for block-bootstrap validity; the effective-observation conversion; the exact bar-count gate below which a look is statistically void.

### 3.3 Look-date governance (the calendar discipline I own)

The CALENDAR governance around the looks is HoQR-frozen here; the look SCHEDULE itself (how many looks, at what effective-observation milestones, under which alpha-spending function) is the Mathematician's to freeze (CONF-interim). Binding governance:

1. **Evaluations occur ONLY at the Mathematician's frozen look dates.** No evaluation — no statistic, no Sharpe, no P&L — is computed on the hold-out outside a frozen look date. (R5-pattern; pm-acceptance-criteria `no_evaluation_before_frozen_dates: true`.)
2. **Each look is a logged one-shot against the frozen receipt.** At each look date a single evaluation is run against the frozen spec and freeze-receipt, its inputs and outputs recorded to the decision-trace and to a per-look result artifact. No "re-run with a tweak" path preserves the pre-registration (R5 §1.3 pattern).
3. **No one reads interim performance outside look dates.** The interim monitoring state (Section 5) is data-and-integrity only. Reading interim performance is an early-peek VOID (Section 1.3 condition 2).
4. **Alpha-spending governs multiplicity across looks.** Because the design is multi-look (the power reality forces interim looks rather than a single ~5–10yr wait), every look spends part of the family-wise α under a pre-registered alpha-spending function. Unplanned peeks are prohibited (pm-acceptance-criteria `alpha_spending_required_if_interim_looks: true`).
5. **The final look is terminal.** There is no "inconclusive, keep waiting past the final look" branch (Section 4).

### 3.4 Data-quality / provenance gate

Before any look computes a statistic, the hold-out USDJPY series must pass the existing provenance gate: `data/storage.py::_assert_price_range` requires USDJPY daily closes to lie within economically plausible bounds **`[20.0, 245.0]`** (`src/forex_system/data/storage.py:54`), and the loader is hardcoded to the real `.../processed/...` directory (quarantining the corrupted synthetic series). The upper bound `245.0` is `ceil(real_max 161.71 × 1.5)` calibrated on data through ~2026 (`storage.py:51-54`); the hold-out runs to 2031, so a LEGITIMATE USDJPY appreciation above 245 (a genuine ~52%+ JPY depreciation over five years — within BOJ-policy tail risk) is foreseeable and MUST NOT be auto-read as a data fault.

> **PROVENANCE-BOUND ADJUDICATION PROCEDURE (FROZEN — no-peek-preserving).** If the hold-out USDJPY series breaches the `[20.0, 245.0]` bound at or before a look date, the look does NOT immediately HALT as a TECHNICAL FAILURE. Instead a pre-committed adjudication runs — entirely on PRICE/RATE data, computing NO strategy return, Sharpe, P&L, or test statistic (early-peek-safe, §1.3 condition 2):
>
> 1. **Two-source verification.** The breaching daily close(s) are verified against TWO independent external USDJPY rate sources (e.g. a central-bank reference rate + a second commercial data vendor; the two sources are named in the freeze-receipt). This compares raw exchange rates only — no strategy logic, no performance.
> 2. **Confirmed-legitimate path → logged amendment, look PROCEEDS.** If both independent sources confirm the price level is a real market level (not a feed glitch, split, or scale corruption), the breach is a GENUINE price move. The USDJPY upper bound in `storage.py:_PAIR_CLOSE_BOUNDS` is updated to a new ceiling via a **logged, pre-specified provenance amendment** that: (a) is recorded in the decision-trace and in a dated amendment artifact referencing this §3.4 and the two confirming sources; (b) touches ONLY the data-provenance bound, NEVER any strategy parameter, signal logic, sizer, cost model, or the §2.2 structure pin; (c) does NOT void the look and does NOT reset the confirmatory contract. The look then proceeds normally. (Because only a data-validation bound moved, the AS-EXECUTED structure §2.2 and VOID conditions are untouched — confirmatory status is preserved.)
> 3. **Non-confirmable path → TECHNICAL FAILURE.** If the two sources do NOT corroborate the level (disagreement, glitch, scale/units corruption, or a price no real market reached), the breach is a data fault: this look is a **TECHNICAL FAILURE** (Section 4 outcome 5: HALT / root-cause / re-freeze / re-run), NOT a confirmatory fail.
>
> This adjudication is itself frozen pre-data and is performable without any strategy computation, so it cannot be a peek. A data fault must never be read as a strategy verdict, and — equally — a real price move must never be discarded as a data fault.

> **MERGED — see PART II §3 (Look Schedule + Alpha-Spending: spend₁=0.005575/z₁=2.537988 at 2028-10-06; terminal z₂=1.662107 at 2031-04-06; two-look power 0.340; futility advisory).**
> CONF-interim: the alpha-spending function (e.g. O'Brien-Fleming), the frozen look schedule (in effective observations / calendar dates), the power curve at each planned look, and the optional pre-registered futility boundary. NHT reviews the power statements.

---

## 4. Decision Map (HoQR) — criterion CONF-decision-map

Every outcome at every look maps to a NAMED firm action. There is **no "inconclusive, keep waiting beyond the final look" branch** — the final look is terminal.

| # | Outcome (at a look) | Condition | Named firm action |
|---|---|---|---|
| **1** | **PASS at a look** | Single-cell confirmatory statistic crosses the alpha-spending **efficacy** boundary at this look AND the confirmatory DSR gate clears (≥ the frozen kill-switch threshold, Section 6) AND, where R5's discordance is relevant, the confirmatory single-series test resolves it (a single-series test has no SPA-vs-RC family discordance — see §4.2) | **GRADUATE to the firm's next validation stage — NO CAPITAL on this path.** Concretely: author a FURTHER, separately-pre-registered **observe-only paper canary** (a forward live-data paper run with no capital at risk), governed by its own fresh HoQR+Math+NHT ratification and its own trial_id. PASS here does NOT authorize capital, does NOT re-open the carry family, and does NOT license exploration. The named gate is: *confirmatory-PASS → fresh paper-canary pre-reg*. Any capital decision is a separate, later governance step explicitly out of scope for trial `f2fb41fd`. |
| **2** | **FAIL at the final look** | Final look reached; efficacy boundary never crossed (statistic fails to reject H0 at the terminal cumulative α) | **KILL the structure.** Archive `vol_target_carry:USDJPY` as RETIRED/FALSIFIED in the falsification archive (pointer to this pre-reg, the freeze-receipt, and the per-look result artifacts). The carry program winds down fully per R5 §5.1. This fires whether the final look was adequately powered or not — low terminal power makes the non-rejection uninformative *as evidence of no edge* but does NOT change the action (binding, mirrors R5 §5 outcomes 2 & 3). |
| **3** | **FAIL at an interim look (futility)** | An interim look crosses a pre-registered **futility** boundary downward (only if the Mathematician freezes a futility boundary in CONF-interim) | **Early KILL.** Same archival + wind-down as outcome 2, stopped early. If the Mathematician freezes NO futility boundary, this outcome does not exist and the test runs to the final look regardless. |
| **4** | **CONTINUE-to-next-look** | An interim look crosses neither the efficacy nor (if present) the futility boundary | **Accrue data to the next frozen look.** This is NOT "inconclusive, keep spending" — it is the pre-registered alpha-spending design proceeding to its NEXT pre-frozen look. No new research spend, no capital, no re-parameterization (Section 5). This branch is only available at interim looks; it is unavailable at the final look (outcome 2 is forced there). |
| **5** | **TECHNICAL FAILURE** | Code error, data-integrity / provenance fault (Section 3.4), freeze mismatch (Section 1.3 condition 5), or unexplained data gap at a look | **HALT, root-cause, re-freeze, re-run.** No confirmatory statistic is read or reported for that look. The trial counter is NOT incremented (the confirmatory test remains ONE trial, `f2fb41fd`). After root-cause and a new freeze-receipt, the look is repeated. A masked bug presented as a fail is itself a VOID. |

### 4.1 No keep-spending escape

There is no decision branch anywhere in this document that results in "the structure is inconclusive, so keep researching / keep deferring indefinitely." The only terminal states are GRADUATE-to-paper-canary (outcome 1) and KILL (outcomes 2/3). Outcome 4 is bounded by the frozen look schedule and terminates at the final look. Outcome 5 returns to a re-frozen re-run, never to free exploration.

### 4.2 R5 discordance handling

R5's family discordance (`p_SPA = 0.0162` vs `p_RC = 0.0588`; `STEP4-RESULT.yaml:3,5`) arose from a 36-cell max-statistic family where SPA and White-RC weight the benchmark differently across cells. The confirmatory test is a **single-series** test on one cell — there is no 36-cell family and therefore no SPA-vs-RC max-statistic discordance to reconcile *at the family level*. The confirmatory test's own concordance requirement (a single-series efficacy crossing plus the DSR gate clearing) is the Mathematician's to specify; the decision map above requires BOTH to hold for outcome 1 (PASS). This is how the confirmatory design "handles concordance/discordance" as required by `pm-acceptance-criteria` `r5_discordance_condition_documented: true`.

---

## 5. Interim Monitoring State (HoQR) — criterion CONF-monitoring

Between the freeze date and each look date, the carry family is in **observe-only** state.

1. **No new research spend on the carry family.** No new variant, no new pair, no parameter search, no re-test of the 36-cell R5 family on any dataset. (R5 §5.1; pm-acceptance-criteria `no_pair_or_variant_search: true`.)
2. **Data pipeline keeps accruing bars.** The existing daily USDJPY ingestion continues; the rate-differential feed continues. This is passive accrual — NOT evaluation.
3. **Quarterly mechanical data-integrity checks WITHOUT computing strategy performance.** Each quarter, run the `data/storage.py` provenance/bounds check (`_assert_price_range`, USDJPY bounds `[20.0, 245.0]`, real-directory loader) and log the result. This records DATA health only. It does NOT compute the strategy's return series, Sharpe, P&L, or any test statistic — doing so would be an early-peek VOID (Section 1.3 condition 2). If an interim bounds breach occurs, the §3.4 PROVENANCE-BOUND ADJUDICATION PROCEDURE applies (two-source price/rate verification → logged bound amendment that touches no strategy logic, OR TECHNICAL FAILURE) — performed on price/rate data only, never on strategy performance, so it remains early-peek-safe.
4. **Falsification-archive entry for the R5 outcome.** The R5 AMBIGUOUS_GATE_FAIL result is recorded in the falsification archive (curated record of what was tested and the outcome): pointer to `r5_carry_universe_kill_test.md`, its FREEZE-RECEIPT, and `STEP4-RESULT.yaml`. This confirmatory test's own per-look outcomes append to that archive as they occur.
5. **Capacity redirect.** Active research capacity is redirected to genuinely-new alpha hypotheses. Those are SEPARATE tracks, out of scope for `f2fb41fd`, and each requires its own fresh pre-registration — nothing is unfrozen by default under the firm's zero-validated-alpha posture.

---

## 6. Kill-Switch Threshold (HoQR adopts; Mathematician derives) — criterion CONF-kill-switch-threshold

The repo pre-commit hook requires every new pre-reg file to contain the literal `kill_switch_threshold:` field. The confirmatory threshold is **NOT** R5's `0.767` — absorbing the R5 36-cell argmax selection into the confirmatory honest-N raises the deflation charge, so the minimum hold-out annualized Sharpe required to clear DSR ≥ 0.95 at the confirmatory `SR0_pp` is higher than R5's. The Mathematician derives the exact value; HoQR adopts it verbatim.

```yaml
kill_switch_threshold: 1.2906
```

Semantics: `1.2906` is the minimum annualized Sharpe of `vol_target_carry:USDJPY` on the hold-out that clears the frozen confirmatory DSR ≥ 0.95 gate at the post-absorption honest-N. Any hold-out Sharpe below it fails the gate and cannot produce a PASS (Section 4 outcome 1). No bar executes outside the historical/forward backtest; the threshold governs the confirmatory decision functional, not a live trading loop.

> **MERGED — see PART II §4 (kill_switch_threshold derivation: 1.2906 at SR0_pp_conf=0.034921, N_conf=6, T_holdout=1260).**
> CONF-kill-switch-threshold derivation: the confirmatory honest-N (R5 36-cell selection absorbed), the frozen confirmatory `SR0_pp`, and the mechanical derivation of `kill_switch_threshold` from the single-series DSR formula. Mathematician signs the derivation.

---

## 7. Retirement Criteria (HoQR) — machine-checkable

Machine-checkable triggers a downstream gate evaluates against each per-look result artifact and the freeze-receipt:

- `look.is_final == true AND look.efficacy_crossed == false` → **KILL** `vol_target_carry:USDJPY` (archive FALSIFIED; carry program full wind-down per R5 §5.1). Power level does NOT gate this trigger.
- `look.futility_boundary_exists == true AND look.futility_crossed == true` → **EARLY KILL** (same archival, stopped early).
- `look.efficacy_crossed == true AND look.dsr >= kill_switch_threshold_cleared` → **GRADUATE to fresh paper-canary pre-reg** (NO CAPITAL; new trial_id; new HoQR+Math+NHT ratification).
- `look.is_interim == true AND look.efficacy_crossed == false AND look.futility_crossed == false` → **CONTINUE to next frozen look** (bounded; unavailable at final look).
- **VOID-on-freeze-mismatch:** `receipt.prereg_sha256 != sha256(this file as committed) OR receipt.code_commit != pinned_commit` → **VOID** (Section 1.3 condition 5).
- **VOID-on-early-peek:** any strategy-performance computation on a post-2026-04-06 bar with `timestamp < frozen_look_date` → **VOID** (Section 1.3 condition 2).
- **VOID-on-parameter-drift:** any executed config field for `vol_target_carry:USDJPY` differs from the Section 2.2 verbatim pin (or code path not behavior-equivalent to commit `350cbd4` per Section 2.3) → **VOID** (Section 1.3 condition 1).
- **VOID-on-missing-selection-absorption:** confirmatory honest-N / SR0 does not charge the R5 36-cell argmax as a spent look → **VOID** (Section 1.3 condition 3; R5 §4/§5 outcome 4 BINDING).
- **VOID-on-wrong-trial-id:** run registers under `576746aa` or omits the org-counter increment → **VOID** (Section 1.3 condition 4; trial is `f2fb41fd`).
- `look.code_error == true OR look.data_integrity_fault == true OR holdout fails storage.py bounds [20.0, 245.0]` → **HALT** (Section 4 outcome 5); trial counter NOT incremented.

A non-pass at the final look at any power level is a KILL trigger. There is no machine-checkable path from this test to "keep researching the carry family as-is."

---

## FREEZE BLOCK — criterion CONF-freeze (mechanics owned jointly; receipt is EXTERNAL)

The freeze-receipt is an EXTERNAL write-once file (pattern of `scripts/cut_freeze_receipt.py`) recording: (a) SHA-256 of THIS file as committed; (b) the pinned code-commit hash for the `vol_target_carry:USDJPY` execution path (commit `350cbd4`); (c) the new trial_id `f2fb41fd`; (d) the frozen look schedule (Mathematician). The look-runner is NOT recorded here (it does not exist at freeze and this receipt is write-once); instead, if a behavior-equivalent successor runner is used (§2.3 path b), its commit and equivalence evidence are recorded in the SUPPLEMENTARY write-once `r5_confirmatory_vol_target_carry_usdjpy.RUNNER-RECEIPT.yaml`, which back-references this receipt's SHA-256 and is cut (HoQR+Math-signed, NHT-may-dissent) BEFORE the first look date. This original file does NOT embed its own hash (F-003 pattern — embedding makes verification circular). The receipt is committed to git BEFORE any post-2026-04-06 hold-out data is accessed or any metric computed.

---

*Mathematician-owned sections (CONF-statistic, CONF-interim, CONF-holdout co-sign, CONF-kill-switch-threshold derivation) are merged at assembly. NHT audit and principal-reviewer review precede CONSENSUS; CEO ratification precedes the freeze-receipt cut.*

---

# PART II — FROZEN STATISTICAL SPECIFICATION (Mathematician-owned sections, merged at assembly)

**Track:** `r5-confirmatory-2026-06-06:phase1:task1.0`
**Trial:** `f2fb41fd` (new org-counter trial; NOT a reuse of R5's `576746aa`)
**Author role:** Quantitative Mathematician
**Status:** FROZEN at authoring; numbers below are the pre-registered contract.
**Source anchors (verified, this session):**
- R5 result: `references/pre-registrations/r5_carry_universe_kill_test.STEP4-RESULT.yaml:1-19` (decision `AMBIGUOUS_GATE_FAIL`; `k_star_label=vol_target_carry:USDJPY`, `k_star_idx=18`; `sr_ann_kstar=0.7672287`, `skew_kstar=0.1962855`, `excess_kurtosis_kstar=8.2782585`; `T=4186`, `k=36`; `p_spa_consistent=0.0161968`, `p_rc=0.0587882`, `dsr=0.9502875`; `SR0_PP_frozen=0.022906`; `block_length_used=21`; `B=5000`; `master_seed=576746`).
- R5 SR0 derivation: `r5_carry_universe_kill_test.md:288-320` (dispersion `sqrt(Var[SR_n])=0.426385` over `{0.80, 0.197}`; `bracket(N=3)=0.852804`; `SR0(N=3)=0.363623` ann `=0.022906` per-obs).
- R5 kill-switch: `r5_carry_universe_kill_test.md:399-406` (`0.767` = ann Sharpe to clear DSR≥0.95 at N=3, T=4186).
- Selection-absorption binding rule: `r5_carry_universe_kill_test.md:343,365,385` (confirmatory test MUST absorb the R5 36-cell selection in its own honest-N / SR0).
- Effective independent dimension of the carry family: `r5_carry_universe_kill_test.md:215` (≈1–2 HoQR / 2–4 NHT; joint bootstrap reality ≈1–4).
- DSR conventions pinned: `src/forex_system/harness/dsr.py:179-207`; `src/forex_system/harness/r5_decision.py:122-194`.
- HAC SE + Politis-White: `src/forex_system/harness/reality_check.py:58-88,152-343`.

---

## 1. Null Hypothesis & Test Statistic (CONF-statistic) — FROZEN

### 1.1 Series under test (single, pre-specified)

The confirmatory test evaluates **exactly one** return series:

> `r_t` = net-of-cost, post-`entry_delay_bars=1` daily portfolio returns of the **`vol_target_carry:USDJPY`** structure (R5 cell `k_star_idx=18`), computed on the **hold-out window only** (post-2026-04-06; window rule in CONF-holdout). Same `config/default.yaml` risk/cost params and `RealisticCostModel` as the R5 frozen run. No re-parameterization, no variant or pair substitution.

The 36-cell SPA family is **closed**. This is a single-series test; the family multiplicity is not re-run — it is **absorbed as a selection charge** (Section 2).

### 1.2 Null and alternative

> **H0:** `E[r_t] ≤ 0` (the structure has no positive net edge on unseen data).
> **H1:** `E[r_t] > 0`.

One-sided, `α = 0.05` total (spent across looks per Section 3). Direction is fixed a-priori (the structure was selected as a positive-Sharpe argmax in R5); a two-sided test would waste half the α on an irrelevant tail.

### 1.3 Frozen statistic — studentized mean with HAC SE

At each look with `n` hold-out bars:

```
t_stat = sqrt(n) * mean(r) / omega_hat
```

where `omega_hat` is the **Newey–West (Bartlett-kernel) HAC standard error of the mean**, computed by `reality_check.hac_se_nw(r, bandwidth = max(L - 1, 1))` (pinned: `reality_check.py:58-88`), and `L` is the **Politis–White (2004) + PPW (2009)** automatic mean block length computed **on the hold-out series itself** via `reality_check.politis_white_block_length(r)`, then `L = max(1, ceil(L_pw))`.

**Guard (FROZEN):** `L ≥ 1` always (the PW routine already clamps `L_opt` into `[1, b_max]` and returns `1.0` on constant/near-iid series, `reality_check.py:316-324`). The bandwidth into `hac_se_nw` is `max(L − 1, 1) ≥ 1`. This uses the same statistic family and HAC conventions as the R5 SPA studentization (`r5c_hansen_spa`/`select_k_star_studentized`, `r5_decision.py:104-109`) — the same `T_k` machinery, evaluated on one column on clean data — but with **univariate** Politis–White block-length selection (`reality_check.politis_white_block_length` applied to the single hold-out series), whereas R5 used multivariate PW across 36 columns; the confirmatory is single-series.

### 1.4 p-value mechanism — FROZEN: stationary block bootstrap (NOT asymptotic normal)

**Election: circular/stationary block bootstrap**, not the asymptotic-normal reference.

**Justification.** At the looks the sample is small-ish and serially dependent: `n ≈ 625` bars at +2.5yr, `n ≈ 1255` at +5yr (252 trading days/yr). The selected cell's R5 in-sample return distribution has **excess kurtosis 8.28** and mild positive skew (0.196) — heavy tails. Under fat tails and autocorrelation at `n` in the hundreds, the `t`-statistic's null distribution is NOT well-approximated by N(0,1): the asymptotic-normal p-value is anti-conservative (over-rejects). The stationary bootstrap (Politis–Romano 1994) resamples geometric-length blocks, preserving the serial-dependence and tail structure of the empirical series, and is the same null-generation mechanism R5 used. Consistency demands the confirmatory test use the same falsifier family.

**Mechanism (FROZEN):**
1. Compute observed `t_obs = sqrt(n)*mean(r)/omega_hat` on the hold-out series.
2. Impose H0 by de-meaning: `d = r − mean(r)` (zero-mean null, autocorrelation/variance preserved — identical convention to `r5a` and to R5c's recentering, `reality_check.py:534-535`).
3. For `b = 1..K`: draw a stationary circular block resample `d*_b` (block length `L` as in §1.3, geometric block lengths), recompute `t*_b = sqrt(n)*mean(d*_b)/omega_hat(d*_b)` (HAC SE recomputed on each resample, mirroring R5c, `reality_check.py:938`).
4. `p = (1 + #{ t*_b ≥ t_obs }) / (K + 1)` — the +1/+1 convention avoids `p=0` (matches `reality_check.py:557,962`).

**FROZEN bootstrap parameters:** `K = 10000` resamples (the module default `_B`, `reality_check.py:49`; supersedes the R5 STEP-4 `B=5000` — the single-series confirmatory test is cheap enough to run the full `K`, tightening the bootstrap MC-SE). Block length `L` = Politis–White auto on the hold-out series, `L ≥ 1` guard. Seed = the confirmatory master seed (Section 5); the bootstrap child seed follows the R5a convention (uses `master_seed` directly for the single-series block bootstrap, `reality_check.py:527`).

This `p` is the look-level evidence compared against the alpha-spending boundary (Section 3). The DSR/selection gate (Section 2) is a **separate, additional** hurdle that must ALSO clear at the final look.

---

## 2. Selection-Absorption Mechanism (the load-bearing freeze) — FROZEN

### 2.1 What must be absorbed and why the clean hold-out does NOT erase it

The candidate `vol_target_carry:USDJPY` was chosen as **`argmax` of 36 studentized `T_k`** in R5 (`r5_decision.select_k_star_studentized`). The data is clean (post-2026-04-06, unseen), but **the hypothesis is selected**. The garden-of-forking-paths charge attaches to *how the hypothesis was chosen*, not to *which data tests it*: had a different cell won the R5 argmax, a different confirmatory hypothesis would now be frozen. Clean hold-out data removes the **in-sample overfit** of the point estimate; it does **not** remove the **multiplicity** of the selection event. R5 §4/§5 makes this BINDING (`...md:343,385`): a confirmatory test that omits the R5 selection burden is VOID and its p is not face-valid.

### 2.2 Alternative rejected (stated and defended-against)

> **Rejected alternative — "no charge, the data is unsnooped, so a plain single-series test suffices."**

Steelman: the hold-out is genuinely out-of-sample; conditional on the hypothesis, the single-series `t`/bootstrap p is an honest frequentist statement about *this* series. **Why rejected:** the firm does not get to condition away the selection for free. The relevant error rate is the *family-wise* probability that the firm declares a winner when none exists — and the firm reached this single hypothesis by maximizing over 36 correlated cells in R5. A plain single-series α=0.05 test, applied to the best-of-36 survivor, has an *actual* type-I rate well above 0.05 because the candidate was pre-filtered for apparent strength. Charging the selection in the DSR `N` restores face-validity. (The bootstrap p in Section 1 is the *clean-data* evidence; the DSR gate in §2.3 is where the selection charge is paid.)

### 2.3 The mechanism: a BLdP DSR gate on the hold-out Sharpe with absorbed `N_conf`

The selection enters through the **Deflated Sharpe Ratio benchmark `SR0`**, exactly as in R5 (Method B, BLdP 2014), but with `N` raised to absorb the R5 selection. The DSR gate is computed on the **hold-out cell's own metrics** (its own ann Sharpe, skew, excess kurtosis, and `T_holdout`) — the R5 in-sample `0.767/0.196/8.28` are **prior-look anchors only**, never the hold-out inputs (per CONF-statistic done_when).

**DSR formula (pinned conventions, `dsr.py:179-203` / `r5_decision.py:172-193`):**
```
SR_pp        = SR_ann_holdout / sqrt(252)
var_term     = 1 − skew_holdout * SR_pp + ((xkurt_holdout + 2)/4) * SR_pp^2
z_dsr        = (SR_pp − SR0_pp_conf) * sqrt(T_holdout − 1) / sqrt(var_term)
DSR          = Phi(z_dsr),  clipped to [0,1]
```
Degenerate pins carried forward verbatim: `SR_ann_holdout ≤ 0 → DSR=0`; `var_term ≤ 0 → DSR=0` (gate FAIL, not technical failure). `Phi = scipy.stats.norm.cdf` (required; no approximation — A-5 pin). DSR gate cleared iff **`DSR ≥ 0.95`**.

**BLdP `SR0` benchmark (pinned form, `...md:121,737`):**
```
SR0_ann = sqrt(Var[SR_n]) * [ (1 − γ)·Z⁻¹(1 − 1/N_conf) + γ·Z⁻¹(1 − 1/(N_conf·e)) ]
SR0_pp  = SR0_ann / sqrt(252)
```
with `γ = 0.5772156649`, `e = 2.718281828`, `Z⁻¹ = norm.ppf`.

### 2.4 Election of `N_conf` (the selection charge) — FROZEN

The confirmatory `N` must carry **both** charges the binding rule names:
- the **R5 best-of-36-on-correlated-cells** selection, whose *effective independent dimension* the R5 joint bootstrap and scope analysis put at **≈1–4** (`...md:215`: HoQR ≈1–2, NHT ≈2–4), and
- the **prior honest-N ≈ 3** carry looks already charged in R5 (the family had spent ~3 effectively-independent looks before R5).

These are **not additive in the naive sense** (the 36 cells ARE the carry family — charging 3 prior looks AND 36 raw cells double-counts, exactly the error R5 §7.2 warns against, `...md:243`). The principled construction: the confirmatory selection event is "the firm picked the single best effectively-independent carry look, having already spent the family's effective looks." The effective independent dimension of the *selection pool* is the R5 joint-bootstrap figure (1–4), and the firm's prior carry multiplicity is the elected R5 `N=3`. I elect the confirmatory charge at the **conservative end of the union**:

> **FROZEN: `N_conf = 6`.**

Derivation of the election (anti-survivorship / conservative-for-a-kill-test direction, mirroring R5 §3.4's "elect off the floor that raises the bar" logic — note BLdP `SR0` is strictly INCREASING in `N`, so a HIGHER `N` is the STRICTER, more skeptical gate):
- R5 effective selection dimension upper end (NHT): `≈4`.
- Prior carry honest-N already spent (R5 elected): `3`.
- The confirmatory event spends *one new effective look* (the confirmatory hold-out test itself) on top of the selection pool.
- A defensible conservative union: `N_conf = max(effective_selection_dim_upper, prior_honest_N) + (prior_honest_N − 1)` is one heuristic, but I avoid arithmetic theater. I elect `N_conf = 6` as the smallest integer that (a) strictly exceeds both the R5 effective-dimension ceiling (4) and the R5 prior honest-N (3), and (b) sits at roughly their sum-minus-overlap (`4 + 3 − 1 = 6`), charging the selection-from-pool AND the prior family spend while removing the one-look double-count of the shared rate-differential idea. `N_conf ∈ [2,6]` is the admissible band the prompt names; I freeze the **ceiling (6)** because this is a KILL test and over-deflation is the safe-if-wrong direction (a structure that clears DSR≥0.95 at `N=6` is genuinely hard to explain by selection luck).

**Dispersion convention (FROZEN, carried from R5 unchanged):** `sqrt(Var[SR_n]) = 0.426385` — the sample (÷1) standard deviation over the two observed independently-sourced look-Sharpes `{0.80, 0.197}` (`...md:315`). No third look-Sharpe exists in the archive; inventing one would be fabrication. `Var[SR_n]` is held FIXED across `N`; `N_conf` enters ONLY the expected-maximum bracket axis (R5's frozen two-axis convention, `...md:294-301`).

### 2.5 Derived `SR0_conf` (shown arithmetic)

Bracket at `N_conf = 6`:
```
Z⁻¹(1 − 1/6)        = Z⁻¹(0.833333)            = 0.967422
Z⁻¹(1 − 1/(6e))     = Z⁻¹(1 − 0.061313)
                    = Z⁻¹(0.938687)            = 1.543843
bracket(N=6)        = (1−γ)·0.967422 + γ·1.542968
                    = 0.4227843·0.967422 + 0.5772157·1.543843
                    = 0.409013 + 0.891141
                    = 1.300141
SR0_ann_conf        = 0.426385 · 1.300141      = 0.554361   (annualized)
SR0_pp_conf         = 0.554361 / sqrt(252)
                    = 0.554361 / 15.874508     = 0.034921   (per-obs)
```

> **FROZEN: `SR0_ann_conf = 0.554361`, `SR0_pp_conf = 0.034921` (per-obs), `N_conf = 6`.**

Sanity vs R5: R5 used `N=3 → SR0_ann=0.363623`. Raising `N` to 6 raises the deflation benchmark from 0.3636 to 0.5542 ann (≈+52%), exactly the stricter-gate direction the selection charge requires. (Z⁻¹ values above are standard normal quantiles to 6 dp; QD to confirm via `scipy.stats.norm.ppf` — see Section 5 routed question.)

---

## 3. Look Schedule + Alpha-Spending (CONF-interim) — FROZEN

### 3.1 Planning Sharpe (the shrinkage freeze — read first)

Power must be planned at a **deflated/shrunk** Sharpe, NOT the selection-biased in-sample `0.767`. The `0.767` is the argmax of 36 studentized statistics on snooped data — it is upward-biased by exactly the selection the DSR gate deflates. **FROZEN planning SR:**

> **`SR_plan = SR0_ann_conf = 0.554`** (annualized).

Rationale: `SR0_conf` is the firm's pre-registered benchmark for "what a non-lucky structure must beat." It is the honest, selection-deflated location at which the firm should plan power — equivalently, the smallest true ann Sharpe at which a pass is *meaningful* rather than noise. Planning at the snooped `0.767` would over-state power (claim the test is more sensitive than it is); planning at `SR0_net`≈0.55 is the conservative, defensible choice. (A posterior-shrunk alternative — e.g. James–Stein toward 0 from 0.767 — would land in a similar 0.5–0.6 band; I freeze the pre-registered `SR0_conf` as the single auditable number rather than introduce a second free parameter.)

### 3.2 Look schedule — FROZEN

Hold-out starts **2026-04-07** (first bar strictly after the R5 common-index terminus 2026-04-06).

| Look | Calendar date | Years of hold-out | Approx `n` (daily, 252/yr) | Information fraction `t` |
|------|---------------|-------------------|-----------------------------|---------------------------|
| 1 (interim) | **2028-10-06** | +2.5 yr | ≈ 630 | 0.50 |
| 2 (final, terminal) | **2031-04-06** | +5.0 yr | ≈ 1260 | 1.00 |

Information fraction is taken proportional to elapsed hold-out calendar time (equivalently bar count), `t₁ = 2.5/5.0 = 0.5`. **The final look is TERMINAL — no extension, no third look** (CONF-decision-map outcome 2/3 fires at look 2 regardless). Minimum-bar guard for bootstrap validity (CONF-holdout co-sign): the interim look requires `n ≥ 504` bars (~2 yr) before it may fire; if the data pipeline yields fewer bars than the +2.5yr schedule implies at the frozen date, the interim is SKIPPED (its α is rolled into the final via the spending function — the Lan-DeMets property permits this) and only the terminal look runs. The terminal look requires `n ≥ 756` bars (~3 yr) to be valid; below that → TECHNICAL_FAILURE (re-freeze), never a pass.

### 3.3 Alpha-spending function + boundaries — FROZEN

**Spending function: Lan–DeMets O'Brien–Fleming-type (`sfLDOF`), one-sided, total `α = 0.05`.** OBF is elected over Pocock because it spends almost no α early (preserves power at the terminal look — the firm wants the 5-yr look to retain near-full sensitivity) while still permitting an overwhelming-evidence early stop.

Spending function (gsDesign `sfLDOF` canonical convention; the `α/2` plug-in is the SHAPE parameter, the spend total is the one-sided `α=0.05`):
```
α*(t) = 2·(1 − Φ( Z⁻¹(1 − α/2) / sqrt(t) )) = 2·(1 − Φ( 1.959964 / sqrt(t) ))
```
Cumulative α spent, and incremental per-look spend:
```
α*(0.5) = 2·(1 − Φ(1.959964/0.707107)) = 2·(1 − Φ(2.771808)) = 2·(1 − 0.997213) = 0.005575   →  spend₁ = 0.005575
α*(1.0) = 2·(1 − Φ(1.959964))          = 2·(1 − 0.975000) = 0.050000                          →  spend₂ ≈ 0.04442
```
(I report the directly-derived one-sided OBF spend; the widely-tabulated `≈0.0084 / 0.0416` split corresponds to the t-fraction reported at slightly different look timing — the gsDesign `sfLDOF` at exactly `t=0.5` gives the `0.0056/0.0444` split above; QD pins the exact split via gsDesign at the frozen `t`.)

**One-sided nominal z-boundaries (FROZEN, to be reproduced exactly by QD via gsDesign `sfLDOF`):**

| Look | `t` | incremental α | nominal one-sided z-boundary | reject H0 if |
|------|-----|---------------|------------------------------|--------------|
| 1 | 0.50 | 0.005575 | **z₁ = 2.537988** (one-sided p ≤ 0.005575) | bootstrap-`t` look-1 p ≤ 0.005575 |
| 2 | 1.00 | 0.044425 | **z₂ = 1.662107** (bivariate joint, scipy-exact) | bootstrap-`t` look-2 p ≤ **0.048246** (= Φ(−1.662107); see §3.3 note) |

The boundaries are applied **on the bootstrap p-value scale** (Section 1.4): reject at look `j` iff the look-`j` bootstrap p ≤ **Φ(−z_j)** — i.e. look-1 threshold Φ(−2.537988) = 0.005575 and look-2 threshold Φ(−1.662107) = 0.048246. (Equivalently, on the z-scale: `t_obs ≥ z_j`.) **The z-boundaries z₁, z₂ are the PRIMARY operative reference; the bootstrap p ≤ Φ(−z_j) formulation is the p-scale equivalent.**

> **Note (F-002 correction):** The incremental spend at look 2 is 0.044425 (= α*(1.0) − α*(0.5) = 0.050000 − 0.005575). This is the alpha-BUDGET consumed by look 2, not the look-2 p-threshold. The p-threshold Φ(−z₂) = Φ(−1.662107) = 0.048246 corresponds to the bivariate joint-exact critical value and is the correct operative threshold. Comparing the look-2 bootstrap p against 0.044425 would correspond to using the nominal conditional boundary Φ⁻¹(1 − 0.044425) = 1.701, which is strictly MORE conservative than z₂ = 1.662107 and is not alpha-exact for this joint group-sequential design. The two formulations are equivalent ONLY at look 1, where Φ(−z₁) = Φ(−2.537988) = 0.005575 = spend₁ by construction.

### 3.4 Futility (optional binding early-KILL) — FROZEN as NON-binding advisory

I freeze a **non-binding** futility advisory, not a binding boundary: at the interim look, if the hold-out ann Sharpe is **negative** (point estimate `< 0`), the firm MAY early-KILL (it cannot clear a positive-edge H1 by the terminal look without a regime reversal that itself would void confirmatory logic). It is NON-binding to avoid the NHT objection that a binding futility boundary not symmetric with the efficacy spend can inflate error in the wrong direction; the firm retains discretion to run to the terminal look. No α is recovered from futility (one-sided efficacy spend is unaffected). The terminal look remains the only **binding** decision.

### 3.5 Power at the terminal look — FROZEN (shown work)

Single-series power, daily returns, annualized planning `SR_plan = 0.554`. The horizon-`Y`-years single-series `t`-statistic location under H1 is `λ = SR_true · sqrt(Y)` (annualized-Sharpe convention: over `Y` years the cumulative-mean t-stat scales as `√(years)`; verified against the orchestrator anchor `Y₅₀=(z_α/SR)²`).

At the **terminal look (Y=5)** with the bivariate joint-exact final boundary `z₂ = 1.662107`:
```
λ = SR_plan · sqrt(Y) = 0.554 · sqrt(5) = 0.554 · 2.236068 = 1.238826
power = P(Z + λ ≥ z₂) = Φ(λ − z₂) = Φ(1.239588 − 1.662107) = Φ(−0.422519) = 0.336 (single-look); two-look joint power = 0.340
```
> **Terminal-look power ≈ 0.34 (34%) at `SR_plan = 0.554361` (two-look joint; single-look 0.336).**

This is LOW and is disclosed as such. Cross-check against the orchestrator anchors at the fixed-sample boundary `z=1.645`, `SR=0.767`: `Y₅₀=(1.645/0.767)²=4.60 yr`, `Y₈₀=((1.645+0.8416)/0.767)²=10.5 yr` — i.e. even at the *snooped* 0.767, 5 yr gives ~52% power; at the honest `SR_plan=0.554361`, `Y₅₀=(1.645/0.554361)²=8.81 yr` and `Y₈₀=((1.645+0.8416)/0.554361)²=20.1 yr`. So a 5-yr terminal look at the honest planning SR is **underpowered (~33%)**. This is the explicitly-disclosed power reality (CONF-interim done_when) and is the reason the decision map treats a non-rejection at the terminal look as a KILL with the honest acknowledgment that low power makes non-rejection uninformative as *evidence of no edge* — but it does NOT license continued spend (CONF-decision-map outcome 3). NHT reviews this statement.

The "monthly-stale signal" concern (≈1 effective obs/month) would FURTHER reduce effective `n` and power if the carry signal autocorrelation is high; the Politis–White block length on the hold-out series will surface this empirically (a large `L` ⇒ few effective independent blocks ⇒ wider HAC SE ⇒ lower realized power than the iid-daily calc above). The iid-daily power (~33%) is therefore an UPPER bound; realized power may be lower. Disclosed.

---

## 4. `kill_switch_threshold` Derivation — FROZEN (verbatim pre-reg field)

The `kill_switch_threshold` is the **minimum hold-out annualized Sharpe** the structure must achieve **at the terminal look** to clear the DSR gate (`DSR ≥ 0.95`) at `SR0_pp_conf = 0.034921`, `T_holdout = 1260` (the +5yr terminal `n`), carrying the hold-out cell's own higher-moment plug-ins.

DSR=0.95 ⇒ `z_dsr = Φ⁻¹(0.95) = 1.644854`. Solve the DSR z-equation for `SR_pp`:
```
z_dsr = (SR_pp − SR0_pp_conf) · sqrt(T−1) / sqrt(var_term) = 1.644854
```
`var_term` depends on `SR_pp` and the hold-out skew/kurtosis (unknown until the run). For the FROZEN threshold I plug the R5 prior-look higher moments as the pre-registered placeholder (`skew=0.196`, `xkurt=8.28`) — these are the only pre-registered moment anchors; the runner recomputes `var_term` with the hold-out's OWN moments at evaluation (the threshold is a function, evaluated at run time, but I freeze its value at the anchor moments for the verbatim field). Two-pass solve (var_term is near 1 because `SR_pp` is small):

Pass 0 (var_term = 1):
```
SR_pp ≈ SR0_pp_conf + z_dsr / sqrt(T−1) = 0.034921 + 1.644854/sqrt(1259)
      = 0.034921 + 1.644854/35.482 = 0.034921 + 0.046357 = 0.081278
```
Pass 1 (recompute var_term at SR_pp=0.081265, skew=0.196, xkurt=8.28):
```
kurt_coeff = (8.28 + 2)/4 = 2.570
var_term   = 1 − 0.196·0.081278 + 2.570·0.081278² = 1 − 0.015930 + 2.570·0.006606
           = 1 − 0.015930 + 0.016977 = 1.001047
sqrt(var_term) = 1.000523
SR_pp = 0.034921 + 1.644854·1.000523/35.482 = 0.034921 + 0.046381 = 0.081302   (converged; brentq exact: 0.081303)
```
Annualize:
```
SR_ann = SR_pp · sqrt(252) = 0.081303 · 15.874508 = 1.290641
```

> **FROZEN: `kill_switch_threshold: 1.2906`** (annualized hold-out Sharpe required at the terminal look to clear DSR ≥ 0.95 at `SR0_pp_conf=0.034921`, `N_conf=6`, `T_holdout=1260`; brentq-exact 1.290641).

Interpretation: any terminal-look hold-out ann Sharpe **below 1.291 fails the DSR gate and cannot pass the confirmatory test** (it maps to a KILL branch). This is far stricter than R5's `0.767`, for two compounding reasons: (i) `N_conf=6` raises `SR0` vs R5's `N=3`; (ii) `T_holdout≈1260` is far smaller than R5's `4186`, so the `sqrt(T−1)` lever is weaker and a higher Sharpe is needed to reach the same DSR. Both are correct and intended: a 5-yr clean-data confirmation of a selected structure SHOULD demand a high realized Sharpe. NOT copied from R5 (per CONF-kill-switch-threshold).

(QD numerical-confirmation routed in Section 5: the two `Z⁻¹` quantiles in §2.5, the OBF boundaries in §3.3, and this two-pass solve. All are standard `scipy.stats.norm` evaluations; values shown are my hand-work to 3–6 dp.)

---

## 5. Run Mechanics to Freeze — FROZEN

**Master seed (FROZEN, derived from trial stem `f2fb41fd`, mirroring R5's rule `master_seed=576746` from stem `576746aa`):**
R5 took the first 6 hex of the trial stem and read them as base-10-of-decimal-digits... no — R5's `576746` is the leading numeric run of `576746aa`. The confirmatory stem `f2fb41fd` has no leading decimal digits, so I freeze the rule: **`master_seed = int(first 6 hex chars of trial stem, base 16) mod 1_000_000`**. `f2fb41` (hex) = 15924033; `15924033 mod 1_000_000 = 924033`.
> **FROZEN: `master_seed = 924033`.** *(Corrected from a hand-hex drift 924289 — the frozen RULE `int('f2fb41',16) mod 1_000_000` governs; int('f2fb41',16)=15924033, orchestrator+QD independently verified.)* Child seeds follow the R5 convention (single-series block bootstrap uses `master_seed` directly, `reality_check.py:527`).

**Bootstrap:** `K = 10000` (Section 1.4). Stationary circular block bootstrap, Politis–White auto block length on the hold-out series, `L ≥ 1` guard. RNG = `numpy.PCG64` seeded by `master_seed` (R5 convention, `reality_check.py:528`).

**Estimator conventions (mirror R5 A-5 pins):**
- Sharpe: `mean / std(ddof=1) · sqrt(252)`, `rf=0` (`reality_check.py:91-104`).
- Skew: `scipy.stats.skew(x, bias=True)`; excess kurtosis: `scipy.stats.kurtosis(x, fisher=True, bias=True)` (`r5_decision.py:147-150`).
- HAC SE: `reality_check.hac_se_nw(x, bandwidth=max(L−1,1))`, Bartlett kernel, `s2 ≥ 1e-12` floor (`reality_check.py:58-88`).
- DSR: `dsr.py`/`r5_decision.py` conventions verbatim (§2.3); `Phi = scipy.stats.norm.cdf`; `Z⁻¹ = scipy.stats.norm.ppf`. **scipy is REQUIRED — no approximation fallback** (A-5 pin, `r5_decision.py:22-30`).
- `periods_per_year = 252`.

**scipy pin:** scipy REQUIRED at run time; absence ⇒ TECHNICAL_FAILURE (re-freeze), never a silent approximation (`r5_decision.py:22-30`).

**Evaluation command contract (math contract; QD owns implementation):**
- The runner is **refuse-without-receipt**: it MUST verify the committed freeze-receipt (SHA-256 of this confirmatory pre-reg + pinned code commit) before touching any hold-out bar, mirroring `scripts/cut_freeze_receipt.py` / the R5 STEP-4 runner pattern. No metric is computed on post-2026-04-06 data before the receipt is committed.
- It runs **only at the two frozen look dates** (2028-10-06, 2031-04-06). No unscheduled peeks.
- At each look it emits: `n`, `L_pw`, `t_obs`, look-level bootstrap p, cumulative α spent, the look-`j` boundary, the DSR (with hold-out moments), and the §7.3.6-style decision-functional verdict mapped to the CONF-decision-map branch.
- Whether this reuses the existing harness (`carry_universe_matrix.py` single-column + `reality_check` single-series path) or needs a thin new single-series runner is QD's implementation question — the math contract above is what must be satisfied.

`numerical-question-routed:` " " (QD confirmation received; all constants corrected per mathematician-z2-election.yaml — scipy-exact set: bracket(6)=1.300141, SR0_ann=0.554361, SR0_pp=0.034921, z1=2.537988, z2=1.662107, kill_switch_threshold=1.2906, two-look power=0.340)
