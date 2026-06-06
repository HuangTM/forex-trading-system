# HoQR Confirmatory Rework #1 — ANCHOR/REPLACEMENT Patches

**Doc patched:** `references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.md` (ASSEMBLED v1, 2026-06-06)
**Author role:** Head of Quantitative Research
**Subtask:** r5-confirmatory-hoqr-rework1 / `r5-confirmatory-2026-06-06:phase1:task1.0` / trial `f2fb41fd`
**Findings addressed:** F-001 (BLOCKING), F-004 (major), F-005 (minor)

Each patch is an exact ANCHOR (quoted verbatim from the assembled doc) and its REPLACEMENT. Apply in order. ANCHORS do not overlap.

---

## PATCH 1 — F-001 (BLOCKING): §2.2 config-vs-executed provenance correction

### Why

ORCHESTRATOR-VERIFIED and re-verified this session against source:

- `VolTargetCarryStrategy.generate_signals` reads `min_carry = self.params.get("min_carry", -np.inf)` (`src/forex_system/strategies/vol_target_carry.py:60`; docstring confirms "default -inf = always", line 41). The carry filter is applied ONLY `if min_carry > -np.inf` (line 72).
- `min_carry` is **NOT** a field of `_VariantExecConfig` (fields enumerated `carry_universe_matrix.py:229-239`: rebalance_mode, rebalance_threshold, sizer_type, config_source, risk_per_trade, stop_loss_atr_multiple, leverage_cap, max_order_units, min_order_size — no min_carry) and is **NOT** present in `_VARIANT_EXEC["vol_target_carry"]` (`carry_universe_matrix.py:266-274`).
- The strategy is built as `params = {"pair": pair, **variant_params}` (`carry_universe_matrix.py:483`), where `variant_params = _variant_params.get(variant, {})` (`:658`) and `_variant_params = variant_params or {}` (`:652`).
- The R5 STEP4 runner called `build_joint_return_matrix(variants=..., pairs=...)` with **NO `variant_params` argument** (`scripts/run_r5_step4.py:312-316`). Therefore `variant_params={}` for every cell.
- **Consequence:** the R5 k* cell `vol_target_carry:USDJPY` executed with `min_carry = -inf` (strategy default — never passed), `target_vol = 0.10` (strategy default, line 57 — never passed), `vol_window = 252` (strategy default, line 58 — never passed), and signal-clip `leverage_cap = 2.0` (strategy default, line 59 — never passed). The config's `min_carry = -0.10` was **NOT in effect**. The sizer params and execution mode/threshold DID flow from config via `_build_sizer`/`exec_cfg`.

The §2.2 prose "The two are consistent; both are pinned" is false for `min_carry` and materially misleading for `target_vol`/`vol_window`/signal `leverage_cap` (config and default coincide, but the builder sources the DEFAULT not the config). VOID condition 1 could not catch this: a runner faithfully reproducing commit `350cbd4` reproduces `min_carry=-inf`, so a pin stating `-0.10` shows zero drift while testing a different structure than the survivor executed.

### ANCHOR (verbatim)

```
The structure is pinned to the committed config file `config/vol_target_carry.yaml` and to the R5 matrix builder's `_VARIANT_EXEC["vol_target_carry"]` execution config (`src/forex_system/harness/carry_universe_matrix.py:266-274`). The two are consistent; both are pinned. Verbatim values:

| Parameter | Value | Source |
|---|---|---|
| variant | `vol_target_carry` | `config/vol_target_carry.yaml:33`; `carry_universe_matrix.py:266` |
| pair | `USDJPY` | `config/vol_target_carry.yaml:20-26` |
| `target_vol` | `0.10` (annualized 10%) | `config/vol_target_carry.yaml:33` |
| `vol_window` | `252` daily bars | `config/vol_target_carry.yaml:34` |
| `leverage_cap` | `2.0` | `config/vol_target_carry.yaml:35,44`; `carry_universe_matrix.py:271` |
| `min_carry` | `-0.10` (no carry filter — vol-targeting does the work) | `config/vol_target_carry.yaml:36` |
| `rebalance_threshold` | `0.20` | `config/vol_target_carry.yaml:37,51`; `carry_universe_matrix.py:268` |
| `rebalance_mode` | `continuous` | `config/vol_target_carry.yaml:50`; `carry_universe_matrix.py:267` |
| sizer | `VolTargetSizer` | `carry_universe_matrix.py:270` (`sizer_type="vol_target"`) |
| `max_order_units` | `5_000_000.0` | `config/vol_target_carry.yaml:46`; `carry_universe_matrix.py:272` |
| `min_order_size` | `100.0` | `config/vol_target_carry.yaml:45`; `carry_universe_matrix.py:273` |
| `entry_delay_bars` | `1` (no-lookahead sacred invariant) | `config/vol_target_carry.yaml:49`; `carry_universe_matrix.py:587-589` |
| cost model | `RealisticCostModel`, USDJPY `PairInfo` (spread 1.0 / slippage 0.5 / commission 0.5 / swap_long 0.8 / swap_short -1.5 pips) | `config/vol_target_carry.yaml:21-26`; `carry_universe_matrix.py:108-116` |
| `initial_capital` | `1_000_000.0` | `config/vol_target_carry.yaml:40`; `carry_universe_matrix.py:554` |
| return convention | `equity_curve.pct_change()` net-of-cost simple returns | `carry_universe_matrix.py:522-528` |
```

### REPLACEMENT

```
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
```

---

## PATCH 2 — F-001 follow-through: §1.3 VOID condition 1 sweep

### Why

VOID condition 1 currently lists `min_carry` among config fields whose change voids the test, implying `min_carry` is config-pinned at `-0.10`. After PATCH 1 the binding pin is `min_carry = -inf` (strategy default, no `variant_params`). The VOID condition must reference the AS-EXECUTED pin (§2.2 as corrected), and must explicitly flag that introducing a `variant_params` override for any signal parameter (which WOULD make the config value bind) is itself structure drift.

### ANCHOR (verbatim)

```
1. **Parameter change / structure drift.** Any change to the pinned `vol_target_carry:USDJPY` config (Section 2) — any of `target_vol`, `vol_window`, `leverage_cap`, `min_carry`, `rebalance_threshold`, `entry_delay_bars`, cost params, sizer type — between freeze and evaluation voids confirmatory status. The structure is tested AS-IS.
```

### REPLACEMENT

```
1. **Parameter change / structure drift.** Any deviation from the **AS-EXECUTED** pin table in §2.2 — `target_vol=0.10`, `vol_window=252`, signal-`leverage_cap=2.0`, **`min_carry=-inf` (no carry filter — strategy default, NOT the config's -0.10)**, sizer `leverage_cap=2.0`/`max_order_units=5_000_000.0`/`min_order_size=100.0`, `rebalance_threshold=0.20`, `rebalance_mode=continuous`, `entry_delay_bars=1`, the `_DEFAULT_PAIR_INFO["USDJPY"]` cost params, and the `VolTargetSizer` sizer type — between freeze and evaluation voids confirmatory status. The structure is tested AS-EXECUTED-BY-R5. **In particular: the confirmatory runner MUST pass no `variant_params` for the strategy-default-sourced signal parameters (`target_vol`, `vol_window`, signal-`leverage_cap`, `min_carry`), exactly as the R5 STEP4 runner did (`scripts/run_r5_step4.py:312-316`).** Supplying any `variant_params` override — including one that "restores" the config's `min_carry=-0.10` — changes the executed structure and is itself a VOID (it would impose a carry filter the R5 survivor never ran). The structure is tested exactly as the family selected it, not as the config nominally describes it.
```

---

## PATCH 3 — F-005 (minor): §2.3 successor-commit runner-receipt mechanism

### Why

§2.3(b) permits a future look-runner via "successor commit verified behavior-equivalent ... recorded in the freeze-receipt", but the freeze-receipt is WRITE-ONCE (`scripts/cut_freeze_receipt.py:10-11,106-110` — refuses to overwrite) and the look-runner does not exist at freeze time. A write-once receipt cannot later record a not-yet-existing runner. The mechanism must be a SUPPLEMENTARY write-once receipt cut when the runner lands.

### ANCHOR (verbatim)

```
- (b) a **future-frozen successor commit verified behavior-equivalent** for this single cell — equivalence meaning byte-identical return series on a fixed shared sub-window, demonstrated and recorded in the freeze-receipt. Any non-equivalent code change to the execution path voids confirmatory status (Section 1.3 condition 1 + 5).

The current working HEAD at draft time is `1c533e8` (informational only; the binding pin is set at freeze).
```

### REPLACEMENT

```
- (b) a **future-frozen successor commit verified behavior-equivalent** for this single cell — equivalence meaning byte-identical return series on a fixed shared sub-window. Because the original freeze-receipt is WRITE-ONCE (`scripts/cut_freeze_receipt.py:10-11,106-110` refuses to overwrite) and the look-runner does not exist at freeze time, the equivalence evidence is recorded NOT in the original receipt but in a **SUPPLEMENTARY write-once runner-receipt**:

  > **RUNNER-RECEIPT MECHANISM (FROZEN).** When the single-cell look-runner lands, a supplementary write-once file `r5_confirmatory_vol_target_carry_usdjpy.RUNNER-RECEIPT.yaml` is cut (same idempotent refuse-to-overwrite discipline as `cut_freeze_receipt.py`). It contains: (i) the successor runner commit hash; (ii) the equivalence-verification evidence (the fixed shared sub-window, the byte-identical-return-series proof / hash comparison against the commit-`350cbd4` reference series); (iii) a back-reference SHA-256 hash of the ORIGINAL freeze-receipt, binding the two receipts. The ORIGINAL freeze-receipt and this pre-reg (§2.3, FREEZE BLOCK) point FORWARD to it by name. **Cutting the runner-receipt is itself a quorum-gated act:** HoQR + Mathematician sign the equivalence determination; NHT may dissent. It MUST be cut and committed to git BEFORE the first look date (2028-10-06). If no behavior-equivalent successor is needed (the run uses commit `350cbd4` directly per path (a)), no runner-receipt is cut and option (b) is unused.

Any non-equivalent code change to the execution path voids confirmatory status (Section 1.3 condition 1 + 5).

The current working HEAD at draft time is `1c533e8` (informational only; the binding pin is set at freeze).
```

---

## PATCH 4 — F-005 follow-through: FREEZE BLOCK forward-pointer

### Why

The FREEZE BLOCK enumerates what the receipt records, including "any new evaluation/look runner". Per PATCH 3 the runner is recorded in the SUPPLEMENTARY runner-receipt, not the original. The FREEZE BLOCK must point forward to the runner-receipt by name.

### ANCHOR (verbatim)

```
The freeze-receipt is an EXTERNAL write-once file (pattern of `scripts/cut_freeze_receipt.py`) recording: (a) SHA-256 of THIS file as committed; (b) the pinned code-commit hash for the `vol_target_carry:USDJPY` execution path (commit `350cbd4` or a verified-equivalent successor per Section 2.3) and any new evaluation/look runner; (c) the new trial_id `f2fb41fd`; (d) the frozen look schedule (Mathematician). This file does NOT embed its own hash (F-003 pattern — embedding makes verification circular). The receipt is committed to git BEFORE any post-2026-04-06 hold-out data is accessed or any metric computed.
```

### REPLACEMENT

```
The freeze-receipt is an EXTERNAL write-once file (pattern of `scripts/cut_freeze_receipt.py`) recording: (a) SHA-256 of THIS file as committed; (b) the pinned code-commit hash for the `vol_target_carry:USDJPY` execution path (commit `350cbd4`); (c) the new trial_id `f2fb41fd`; (d) the frozen look schedule (Mathematician). The look-runner is NOT recorded here (it does not exist at freeze and this receipt is write-once); instead, if a behavior-equivalent successor runner is used (§2.3 path b), its commit and equivalence evidence are recorded in the SUPPLEMENTARY write-once `r5_confirmatory_vol_target_carry_usdjpy.RUNNER-RECEIPT.yaml`, which back-references this receipt's SHA-256 and is cut (HoQR+Math-signed, NHT-may-dissent) BEFORE the first look date. This original file does NOT embed its own hash (F-003 pattern — embedding makes verification circular). The receipt is committed to git BEFORE any post-2026-04-06 hold-out data is accessed or any metric computed.
```

---

## PATCH 5 — F-004 (major): §3.4 provenance-bound adjudication procedure

### Why

The USDJPY upper bound `245.0` was calibrated as `ceil(real_max 161.71 × 1.5)` on data through ~2026 (`src/forex_system/data/storage.py:51-54`). The hold-out runs to 2031-04-06. A LEGITIMATE USDJPY level above 245 (a real ~52%+ JPY depreciation from the calibration max over 5 years — not implausible given BOJ policy tail risk) would trip `_assert_price_range` and be read as a TECHNICAL FAILURE under §3.4 / outcome 5, halting a look that should proceed. A genuine price move must not be silently treated as a data fault. F-004 requires a pre-committed, no-peek adjudication: a bounds breach triggers data-provenance verification against two independent rate sources; a confirmed-legitimate level updates the bound via a logged pre-specified amendment that does NOT touch strategy logic and does NOT void the look; a non-confirmable level is the TECHNICAL FAILURE path. The adjudication must be performable WITHOUT computing strategy performance (no-peek preserved).

### ANCHOR (verbatim)

```
Before any look computes a statistic, the hold-out USDJPY series must pass the existing provenance gate: `data/storage.py::_assert_price_range` requires USDJPY daily closes to lie within economically plausible bounds **`[20.0, 245.0]`** (`src/forex_system/data/storage.py:54`), and the loader is hardcoded to the real `.../processed/...` directory (quarantining the corrupted synthetic series). If the hold-out data fails the provenance gate at a look date, that look is a **TECHNICAL FAILURE** (Section 4 outcome 5: HALT / re-freeze), NOT a confirmatory fail — a data fault must never be read as a strategy verdict.
```

### REPLACEMENT

```
Before any look computes a statistic, the hold-out USDJPY series must pass the existing provenance gate: `data/storage.py::_assert_price_range` requires USDJPY daily closes to lie within economically plausible bounds **`[20.0, 245.0]`** (`src/forex_system/data/storage.py:54`), and the loader is hardcoded to the real `.../processed/...` directory (quarantining the corrupted synthetic series). The upper bound `245.0` is `ceil(real_max 161.71 × 1.5)` calibrated on data through ~2026 (`storage.py:51-54`); the hold-out runs to 2031, so a LEGITIMATE USDJPY appreciation above 245 (a genuine ~52%+ JPY depreciation over five years — within BOJ-policy tail risk) is foreseeable and MUST NOT be auto-read as a data fault.

> **PROVENANCE-BOUND ADJUDICATION PROCEDURE (FROZEN — no-peek-preserving).** If the hold-out USDJPY series breaches the `[20.0, 245.0]` bound at or before a look date, the look does NOT immediately HALT as a TECHNICAL FAILURE. Instead a pre-committed adjudication runs — entirely on PRICE/RATE data, computing NO strategy return, Sharpe, P&L, or test statistic (early-peek-safe, §1.3 condition 2):
>
> 1. **Two-source verification.** The breaching daily close(s) are verified against TWO independent external USDJPY rate sources (e.g. a central-bank reference rate + a second commercial data vendor; the two sources are named in the freeze-receipt). This compares raw exchange rates only — no strategy logic, no performance.
> 2. **Confirmed-legitimate path → logged amendment, look PROCEEDS.** If both independent sources confirm the price level is a real market level (not a feed glitch, split, or scale corruption), the breach is a GENUINE price move. The USDJPY upper bound in `storage.py:_PAIR_CLOSE_BOUNDS` is updated to a new ceiling via a **logged, pre-specified provenance amendment** that: (a) is recorded in the decision-trace and in a dated amendment artifact referencing this §3.4 and the two confirming sources; (b) touches ONLY the data-provenance bound, NEVER any strategy parameter, signal logic, sizer, cost model, or the §2.2 structure pin; (c) does NOT void the look and does NOT reset the confirmatory contract. The look then proceeds normally. (Because only a data-validation bound moved, the AS-EXECUTED structure §2.2 and VOID conditions are untouched — confirmatory status is preserved.)
> 3. **Non-confirmable path → TECHNICAL FAILURE.** If the two sources do NOT corroborate the level (disagreement, glitch, scale/units corruption, or a price no real market reached), the breach is a data fault: this look is a **TECHNICAL FAILURE** (Section 4 outcome 5: HALT / root-cause / re-freeze / re-run), NOT a confirmatory fail.
>
> This adjudication is itself frozen pre-data and is performable without any strategy computation, so it cannot be a peek. A data fault must never be read as a strategy verdict, and — equally — a real price move must never be discarded as a data fault.
```

---

## PATCH 6 — F-004 follow-through: §5.3 interim integrity-check wording

### Why

§5.3 (interim monitoring) runs the quarterly `_assert_price_range` bounds check and treats a failure as cause to log a data issue. With the F-004 adjudication frozen, an interim bound breach should trigger the SAME no-peek adjudication (price/rate only), not a bare failure log — keeping interim and look-date handling consistent.

### ANCHOR (verbatim)

```
3. **Quarterly mechanical data-integrity checks WITHOUT computing strategy performance.** Each quarter, run the `data/storage.py` provenance/bounds check (`_assert_price_range`, USDJPY bounds `[20.0, 245.0]`, real-directory loader) and log the result. This records DATA health only. It does NOT compute the strategy's return series, Sharpe, P&L, or any test statistic — doing so would be an early-peek VOID (Section 1.3 condition 2).
```

### REPLACEMENT

```
3. **Quarterly mechanical data-integrity checks WITHOUT computing strategy performance.** Each quarter, run the `data/storage.py` provenance/bounds check (`_assert_price_range`, USDJPY bounds `[20.0, 245.0]`, real-directory loader) and log the result. This records DATA health only. It does NOT compute the strategy's return series, Sharpe, P&L, or any test statistic — doing so would be an early-peek VOID (Section 1.3 condition 2). If an interim bounds breach occurs, the §3.4 PROVENANCE-BOUND ADJUDICATION PROCEDURE applies (two-source price/rate verification → logged bound amendment that touches no strategy logic, OR TECHNICAL FAILURE) — performed on price/rate data only, never on strategy performance, so it remains early-peek-safe.
```

---

## Patch summary

| # | Finding | Section | Nature |
|---|---|---|---|
| 1 | F-001 (BLOCKING) | §2.2 | Re-pin `min_carry=-inf` AS-EXECUTED; full row-by-row provenance table; disclose config-vs-executed discrepancy |
| 2 | F-001 | §1.3 cond. 1 | VOID condition references AS-EXECUTED pin; bars `variant_params` overrides |
| 3 | F-005 | §2.3 | Supplementary write-once RUNNER-RECEIPT mechanism, quorum-gated, before first look |
| 4 | F-005 | FREEZE BLOCK | Forward-pointer to runner-receipt |
| 5 | F-004 | §3.4 | Provenance-bound adjudication (two-source verify → logged amendment or TECHNICAL FAILURE), no-peek |
| 6 | F-004 | §5.3 | Interim breach routes through §3.4 adjudication |

**6 patches.** F-001 (blocking) fully resolved with row-by-row AS-EXECUTED provenance; F-004 and F-005 closed.
