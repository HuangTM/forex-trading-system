# Pre-Registration: tas_ceiling_4h (Bet #2)

**Status:** Prospective pre-registration
**Date filed:** 2026-04-27 (before any 4H backtest run; no `scripts/run_backtest.py` invocation has touched 4H data for this strategy at the time this file is committed)
**Strategy ID:** `tas_ceiling_4h`
**Family:** Mean-reversion, narrow-universe, 4H
**Registered by:** Quant Researcher per CONSENSUS 2026-04-26 (HoQR dispatch ruling, R2 action item)
**Binding commit at registration:** filed before first commit of any `tas_ceiling_4h.py` strategy module
**Dispatch authority:** HoQR `hoqr-week-ahead-prioritization.yaml` (2026-04-26T20:35:00Z)

---

## Hypothesis

**Primary:** A 4H mean-reversion strategy on the USDJPY / EURUSD / GBPUSD G3-major universe — entering counter to deviations beyond a Time-Adjusted-Slope (TAS) ceiling/floor envelope around a rolling log-linear price trend — produces an **equal-weighted portfolio annualized Sharpe ≥ 0.30 net of realistic costs** on a pre-registered out-of-sample holdout window (2023-04-25 to 2026-04-06, ~35 months).

**Mechanism (the predictive claim being tested):**

Over multi-day horizons (~1–5 trading days), price deviations above/below a regression-based trend at the 4H frequency tend to mean-revert toward that trend. The "TAS ceiling" is the upper edge of a residual-volatility envelope around the trend; price breaching the ceiling signals an over-extension that historically resolves toward the median. The strategy is structurally distinct from Bet #1 (daily, cross-sectional, carry-direction): it is intraday-but-multi-day-hold, single-pair-independent, and direction-agnostic with respect to fundamentals.

**Why this universe:**

- Confirmed available 4H parquet data: `data/processed/{USDJPY,EURUSD,GBPUSD}_4h.parquet`, all three with ~25,460 bars from 2010-06-17 to 2026-04-06 (verified 2026-04-27).
- No other 4H pairs have parquets — universe is constrained by data, not cherry-picked.
- G3 majors are the deepest, lowest-spread venues retail can trade — cost-floor for mean-reversion edge.

**OOS holdout (binding):** **2023-04-25 to 2026-04-06** (~35 months). This window is reserved before any code is written. Training/exploration on 4H bars is permitted ONLY on data prior to 2023-04-25.

---

## Universe

| Pair | Timeframe | Data path | Bars (verified 2026-04-27) | Range |
|------|-----------|-----------|----------------------------|-------|
| USDJPY | 4H | `data/processed/USDJPY_4h.parquet` | 25,460 | 2010-06-17 → 2026-04-06 |
| EURUSD | 4H | `data/processed/EURUSD_4h.parquet` | 25,457 | 2010-06-17 → 2026-04-06 |
| GBPUSD | 4H | `data/processed/GBPUSD_4h.parquet` | 25,457 | 2010-06-17 → 2026-04-06 |

**No additions, no substitutions.** If 4H data quality validation reveals a defect on any one of these pairs (per HoQR knowledge gap "4H data quality validation"), the family is retired under BET2-T4 PROCESS-G1 — a substitute pair is NOT permitted.

---

## Signal Construction (pre-registered, fully specified)

For each pair independently, at each 4H bar close:

1. **Rolling log-linear trend fit:** Fit OLS linear regression of `log(close)` on bar-index `t` over the trailing window `regression_window_bars = 120` bars (≈ 20 trading days at 6 bars/day during weekdays). Produces slope `β_t` and intercept `α_t`.

2. **Residual computation:** `r_t = log(close_t) − (β_t · t + α_t)` — the de-trended log-price.

3. **Residual volatility:** `σ_r,t = stdev(r_{t-119..t})` over the same 120-bar window.

4. **Z-score:** `z_t = r_t / σ_r,t`.

5. **Signal mapping (stateful for multi-day holds):**
   - **Entry conditions** (no-position state):
     - If `z_t > +k_enter` (default `+2.0`): set raw signal = `−clip((z_t − k_enter) / k_scale, 0, 1)` (short — counter to over-extension above)
     - If `z_t < −k_enter` (default `−2.0`): set raw signal = `+clip((|z_t| − k_enter) / k_scale, 0, 1)` (long)
     - Otherwise: signal = 0 (flat)
   - **Hold conditions** (in-position state):
     - Continue holding the prior signal direction until `|z_t| < k_exit` (default `0.5`), at which point flatten.
   - **Hard exit:** if the position has been held for more than `max_hold_bars = 60` bars (10 trading days), force-exit regardless of `z_t`. This caps stale-position risk and is itself a falsifiable design choice (see BET2-T6).

6. **Per-pair signal range:** `[−1.0, +1.0]` floats per the firm convention in `CLAUDE.md`.

7. **Vol-target sizing per pair:** Each pair's signal is sized to `target_vol = 10%` annualized using the existing `VolTargetSizer` (same machinery as `vol_target_carry`). This isolates the mean-reversion edge from vol shocks and preserves comparability with prior trials.

8. **Portfolio aggregation:** equal-weighted across the 3 pairs — each pair contributes 1/3 of total notional after vol-targeting. Portfolio return at bar `t+1` = `(1/3) · Σ_pairs (signal_t · realized_return_{t+1} − cost_{t+1})`.

9. **No-lookahead invariant:** signal at bar `N` executes at bar `N+1` (entry_delay_bars=1) per the firm's sacred test. Backtester engine enforces this; do not bypass.

---

## Strategy Parameters (binding)

| Parameter | Value | Rationale |
|---|---|---|
| `regression_window_bars` | 120 | ~20 trading days at 4H freq; long enough to fit a stable trend, short enough to adapt |
| `k_enter` | 2.0 | 2σ residual deviation — single fixed threshold, no per-pair tuning |
| `k_exit` | 0.5 | Hysteresis band; exits before mean is reached to capture asymmetric reversion |
| `k_scale` | 1.0 | Signal saturates 1σ beyond entry (i.e., at z = 3.0 in absolute terms) |
| `max_hold_bars` | 60 | 10 trading days hard cap; kills stale positions in unbroken trends |
| `target_vol` | 0.10 | 10% annualized per pair, equal-vol-weighted aggregation |
| `entry_delay_bars` | 1 | Firm-wide no-lookahead convention |
| `cost_model` | `RealisticCostModel` from `config/default.yaml` (4H section) | Per-pair spread, slippage, commission; no per-strategy cost overrides |

**No parameter sweeps.** This strategy is registered as a single point in parameter space. Any post-hoc parameter exploration is a separate trial registration, counted against the Bonferroni denominator.

---

## Bonferroni / Multiple-Testing Accounting

Per HoQR `hoqr-week-ahead-prioritization.yaml` `bonferroni_accounting`:

- **Pre-Bet#2 family N:** 14 (per `.fintech-org/trials.jsonl`)
- **Post-Bet#2 dispatch family N:** 17 (this pre-reg adds 3 within-family entries — one per pair — counted as ONE family with universe-level hypothesis)
- **Per-pair Bonferroni-corrected α threshold:** `0.05 / 17 = 0.0029`
- **Universe-level threshold:** equal-weighted portfolio Sharpe ≥ 0.30 net of costs (BET2-T1)

If NHT (`WA-02`) ratifies a stricter denominator (per Lopez-de-Prado, count-of-parameter-sets rather than count-of-trials), HoQR DEFERS to that ruling and BET2 thresholds are recomputed accordingly. **However, the BET2-T1 Sharpe ≥ 0.30 gate is a fixed pre-registered threshold and is NOT recomputed by Bonferroni** — the t-statistic test is what gets corrected, the gate threshold itself is binding.

---

## Metrics (pre-registered)

- **Primary (gate metric):** Equal-weighted portfolio annualized Sharpe (4H returns, annualized by `sqrt(252 × 6) = sqrt(1512)`) on the OOS holdout 2023-04-25 → 2026-04-06.
- **Secondary:**
  - Per-pair Sharpe on full in-sample (pre-2023-04-25)
  - Per-pair Sharpe on OOS holdout
  - Average trade-holding-period in 4H bars (binding for BET2-T6)
  - Number of trades per pair (sanity check)
  - Max drawdown (%) on OOS portfolio
  - Sortino ratio
  - One-sample t-test on per-pair Sharpe distribution vs zero (binding for BET2-T5)
- **Cost-stress secondary:** Re-run with 2× `RealisticCostModel` costs; record in-sample portfolio Sharpe (binding for BET2-T3).

---

## Kill Criterion (pre-registered threshold)

`gate_threshold: 0.30`

The 4H TAS-ceiling mean-reversion mechanism on the USDJPY/EURUSD/GBPUSD universe is considered **officially falsified** if the OOS equal-weighted portfolio Sharpe < 0.30 net of measured costs. Per CONSENSUS 2026-04-26, this retires the family at this capacity scale.

---

## Falsification Triggers (binding, pre-registered, copied verbatim from CONSENSUS 2026-04-26)

- **BET2-T1:** OOS portfolio Sharpe (equal-weighted USDJPY+EURUSD+GBPUSD 4H) < 0.30 net of costs on pre-registered OOS holdout → **retire family**.
- **BET2-T2:** ≥ 2 of 3 per-pair Sharpes negative on OOS → retire (no cherry-pick of 1-of-3) — TAS-ceiling not robust across G3 majors.
- **BET2-T3:** Doubling measured 4H costs reduces in-sample Sharpe < 0.20 → retire — too thin to survive cost estimation error.
- **BET2-T4:** Engine output diverges from canonical reference script Sharpe-Δ > 0.10 OR correlation < 0.95 → **HARD RETIRE per PROCESS-G1**. (Mirrors the vol_target_carry equivalence test that consumed 5 paper-trading days; will not repeat that.)
- **BET2-T5:** OOS per-pair Sharpe distribution does not differ from zero (one-sample t-test p > 0.10, two-tailed across 3 per-pair OOS Sharpes) → retire — no cross-pair edge present.
- **BET2-T6:** Average trade-holding-period < 6 4H bars (≤ 1 trading day) on OOS → retire — TAS-ceiling mechanism predicts multi-day hold; sub-day-hold falsifies the mechanism even if Sharpe passes.

**Additional implementation guards (not retirement triggers, but PROCESS-level):**

- **PROCESS-IMPL-1:** Before invoking `scripts/run_backtest.py` for `tas_ceiling_4h`, confirm that the import graph of the backtest entry point does NOT touch `scripts/run_paper_trading_vt.py` or `forex_system.saxo.*` modules. (Closes WS-05 third-code-path risk per CTO weak-spot inventory.)
- **PROCESS-IMPL-2:** The first backtest run must be on a pre-2023-04-25 in-sample slice to prove the engine produces output before any OOS holdout exposure. OOS evaluation is a SEPARATE invocation post-IS-validation. Do not co-mingle.

---

## Approval

- **Quant Researcher:** pre-registered prospectively per CONSENSUS.md R2 action item; mechanism specified to engineer-implementable precision before any backtest run.
- **Head of Quant Research:** dispatch authorized in `hoqr-week-ahead-prioritization.yaml` 2026-04-26T20:35:00Z; H2 hard-gated on this file's existence + mtime predating any 4H backtest invocation.
- **NHT:** Bonferroni denominator handling per N2 ruling (count-of-trials = 17 unless NHT escalates); dissent on Bet #1 testability does NOT extend to this pre-reg (Bet #2 has a clean OOS window with no regime-overlap claim — but see Amendment 1).
- **CTO:** PROCESS-IMPL-1 and PROCESS-IMPL-2 added on top of CONSENSUS's BET2-T1..T6 to close WS-05 risk ahead of dispatch.
- **CRO:** backtest-only research dispatch — no paper-trading exposure, no live-capital exposure, no broker-side state mutation. No CRO sign-off required for this artifact.

---

## Amendment 1 — Critic-driven spec hardening (2026-04-27)

This amendment is **append-only** per pre-reg discipline. The original specification above is unchanged. This amendment closes 8 ambiguities and structural gaps surfaced by an adversarial review prior to any backtest run; all 8 are resolved here, BEFORE the H2 dispatch executes. Ratifying this amendment is a precondition for the H2 hard gate.

### A1-1. Stateful signal: post-exit re-entry rule (closes critic Issue #1)

**Binding:** After ANY exit (z-threshold exit OR `max_hold_bars` force-exit OR direction flip), the state machine returns to the `no-position` state. The next entry requires `|z_t| > k_enter` to be satisfied on a **subsequent bar after the exit bar** — i.e., the bar of the exit cannot itself be the bar of a new entry, even if its z-score qualifies. This is implemented by requiring a one-bar cooldown after exit:

```
state := no_position
for each bar t:
    if state == no_position and |z_t| > k_enter:
        enter direction = -sign(z_t), position_age = 0
    elif state == in_position:
        position_age += 1
        if |z_t| < k_exit OR position_age > max_hold_bars OR sign(z_t) != position_direction_consistent:
            exit; state := exit_cooldown(1 bar)
    elif state == exit_cooldown:
        state := no_position  # next bar evaluable
```

Rationale: prevents single-bar churn in trending markets where price oscillates around the |z|=k_enter boundary. If the implementer chooses to ignore the cooldown, the resulting strategy is a DIFFERENT strategy and constitutes a new trial registration.

### A1-2. BET2-T4 canonical reference script: binding co-authorship requirement (closes critic Issue #2)

**Binding:** BET2-T4's "engine vs. canonical script" comparison requires a canonical reference script to exist *independently of the engine implementation*. To satisfy this:

1. **Two-author rule:** The canonical reference script (`scripts/tas_ceiling_4h_canonical.py`) and the engine strategy module (`src/forex_system/strategies/tas_ceiling_4h.py`) MUST be authored by **different engineers/agents**. Solo author = T4 vacated, dispatch BLOCKED.
2. **Same-PR commit:** Both files MUST be committed in the same pull request as the strategy module. Sequential PRs are permitted only if the canonical script lands FIRST and is signed off by HoQR before the engine module is begun.
3. **IS fixture invariant:** The canonical script MUST include a small in-sample fixture window (e.g., 2018-01 → 2018-12) with its computed Sharpe committed as a comment or YAML sidecar. The engine implementer reads the canonical fixture Sharpe BEFORE running the engine and is bound to match it within Δ=0.05 on the same window. Deviation = HARD STOP, escalate to HoQR + CTO.
4. **Cost stress co-runs:** Both engine AND canonical script must be re-run with 2× costs (BET2-T3 stress test) and produce the same Sharpe-Δ < 0.10 invariant.

This rule operationalizes the lesson from `vol_target_carry` (5 paper-trading days lost on the equivalence reconciliation; CONSENSUS_2026-04-25 §NHT). T4 is empty without it.

### A1-3. Cost model: explicit 4H proration; new config file required (closes critic Issue #3)

**Binding:** Before any 4H backtest of `tas_ceiling_4h` runs, a new config file MUST exist at `config/tas_ceiling_4h.yaml` with **explicit per-4H-bar costs**. Loading from `config/default.yaml`'s daily swap rates without proration is a HARD VIOLATION and constitutes BET2-T4 (engine divergence) — auto-retire.

Required structure for `config/tas_ceiling_4h.yaml`:

```yaml
pairs:
  - symbol: USDJPY
    pip_value: 0.01
    spread_pips: 0.5            # may differ from daily; verify against Saxo 4H quotes
    slippage_pips: 0.5
    commission_pips: 0.5
    # 4H-specific swap proration. Daily swap = 6 × per_bar_swap.
    swap_long_pips_per_4h_bar: 0.1333    # +0.8 daily / 6
    swap_short_pips_per_4h_bar: -0.25    # -1.5 daily / 6
  - symbol: EURUSD
    pip_value: 0.0001
    spread_pips: 0.5
    slippage_pips: 0.5
    commission_pips: 0.5
    swap_long_pips_per_4h_bar: -0.20     # -1.2 daily / 6
    swap_short_pips_per_4h_bar: 0.05     # +0.3 daily / 6
  - symbol: GBPUSD
    pip_value: 0.0001
    spread_pips: 0.8
    slippage_pips: 0.6
    commission_pips: 0.5
    swap_long_pips_per_4h_bar: -0.15     # -0.9 daily / 6
    swap_short_pips_per_4h_bar: 0.0167   # +0.1 daily / 6
```

The cost model implementation MUST verify total-per-day swap equals daily rate within 1e-6 tolerance, regardless of how many 4H bars elapsed during a holding period.

### A1-4. Signal price domain: returns, not log-prices (closes critic Issue #4)

**Binding:** The OLS regression in step (1) of the original signal construction is **redefined** to operate on **cumulative log-returns** rather than `log(close)`:

```
cum_log_ret_t = sum_{s=t-119..t} log(close_s / close_{s-1})
```

Then fit `cum_log_ret_t = β_t · t + α_t` over the 120-bar window. Compute residuals on the cum-log-return scale and z-score the same way.

**Why:** Mean-reversion in cumulative-log-return space is sign-symmetric regardless of FX quote convention. Operating on `log(close)` directly produces opposite-sign residuals between USD-base pairs (EURUSD, GBPUSD) and USD-quote pairs (USDJPY) under identical underlying mean-reversion phenomena, which would silently flip the strategy's direction on USDJPY. This amendment is mathematically equivalent to the original spec on USD-base pairs (cum-log-return is just `log(close_t) - log(close_{t-120})` plus a constant), but eliminates the USDJPY sign-flip footgun.

### A1-5. Trade-holding-period: precise definition (closes critic Issue #5)

**Binding for BET2-T6:** "Trade holding period" is defined as the number of consecutive bars from the bar where the position was opened (signal first becomes nonzero of a given sign) to the bar where the position is fully closed (signal returns to 0). Direction flips count as a CLOSE of the prior trade plus an OPEN of a new trade — they are NOT a single continuous holding period.

For fractional signals from the `clip()` operation:
- A signal of `+0.7` is a "long position" regardless of magnitude.
- The trade is "open" while signal magnitude > 0.
- The trade "closes" when signal returns to exactly 0 (z-threshold exit, max-hold force-exit, or direction flip).
- A signal change from `+0.7` to `+0.3` is NOT a new trade; the trade continues.

`average_trade_holding_period_bars = mean of (close_bar_index - open_bar_index)` across all trades on OOS. BET2-T6 fires if this mean < 6 bars on OOS.

### A1-6. No-parameter-sweeps enforcement: hard prerequisite on Q4 (closes critic Issue #6)

**Binding:** The "no parameter sweeps" line in the original spec is enforceable only via the Q4 pre-commit equivalence-gate hook (per CONSENSUS Q4 / Path B prerequisite P5). Until Q4 lands AND its hook is wired to block strategy-file commits without a paired pre-reg signature, parameter sweeps are enforceable ONLY by manual review.

Therefore: **H2 dispatch is HARD-GATED on Q4 having landed in main**, OR on an explicit waiver from HoQR + NHT acknowledging that no enforcement layer exists and accepting the implementer's discipline as the only safeguard. Until Q4 lands, the implementer commits a sworn statement at the top of the PR description: "I tested no parameter values for tas_ceiling_4h other than {regression_window_bars=120, k_enter=2.0, k_exit=0.5, k_scale=1.0, max_hold_bars=60} prior to OOS evaluation."

### A1-7. OOS regime-overlap defense (closes critic Issue #7)

**Binding new triggers:**

- **BET2-T7:** Split the OOS window 2023-04-25 → 2026-04-06 into TWO sub-windows at 2024-10-01 (BoJ pivot date — when policy rate first exceeded 0.30%):
  - sub-window 1: 2023-04-25 → 2024-09-30 (post-SVB / pre-BoJ-pivot, low-vol regime)
  - sub-window 2: 2024-10-01 → 2026-04-06 (post-BoJ-pivot, normalization regime)

  The strategy MUST pass equal-weighted portfolio Sharpe ≥ 0.30 net of costs on **at least one** sub-window AND not have a portfolio Sharpe < -0.10 on the other. A strategy that produces +0.60 on sub-1 and -0.40 on sub-2 (regime-concentrated) FAILS BET2-T7 even if the overall OOS Sharpe averages above 0.30.

- **BET2-T8:** Pre-2023 walk-forward sanity. The implementer MUST report per-pair OOS Sharpes from a walk-forward run on the IS data (pre-2023-04-25) using the firm's standard walk-forward protocol (504-day train, 126-day test, 63-day step per `config/default.yaml:73`). If the walk-forward's median window-Sharpe is < 0.20, the strategy mechanism is suspect even if the official 2023-2026 OOS passes — file with HoQR for ruling.

These triggers directly address NHT's regime-overlap objection. They cannot be eliminated by parameter choice.

### A1-8. BET2-T5 toothlessness — add stronger alternative (closes critic Issue #8)

The original BET2-T5 (one-sample t-test on 3 per-pair Sharpes vs zero, p > 0.10) has near-zero falsification power at N=3 (df=2; critical t≈2.92 → requires per-pair Sharpe ~1.0+ to reject zero). It remains in force per CONSENSUS verbatim, but is supplemented by:

- **BET2-T5b (binding):** OOS portfolio Sharpe degradation from in-sample to OOS exceeds 50% → retire. Specifically: if `(IS_portfolio_Sharpe − OOS_portfolio_Sharpe) / |IS_portfolio_Sharpe| > 0.50`, the strategy is regime-fragile and retires regardless of whether OOS Sharpe absolute level passes BET2-T1.

  This catches the "passed BET2-T1 by luck on a favorable OOS window" scenario that BET2-T5 cannot detect at N=3.

### A1-9. Implementation prerequisites checklist (binding before H2 dispatch)

H2 (HoQR Bet #2 backtest dispatch) is HARD-GATED on **all** of the following BEFORE any backtest invocation:

- [ ] `config/tas_ceiling_4h.yaml` committed with explicit per-bar costs per A1-3
- [ ] `scripts/tas_ceiling_4h_canonical.py` committed with IS fixture per A1-2
- [ ] `src/forex_system/strategies/tas_ceiling_4h.py` committed by a DIFFERENT author per A1-2
- [ ] Q4 pre-commit hook in place OR HoQR + NHT waiver attached to PR per A1-6
- [ ] PROCESS-IMPL-1 verification (no Saxo / paper imports in backtest path) — `python tools/check_no_saxo_imports.py scripts/run_backtest.py` returns exit code 0. (The original grep stub here was non-runnable; CTO 2026-04-27 routed the fix to Quant Developer; the tool is now the operative check. Run on each backtest entry point individually if multiple exist.)
- [ ] PROCESS-IMPL-2 verification — IS-only run committed and signed-off BEFORE OOS run executes; the two backtest invocations are separate `git log` entries

Any item missing → H2 BLOCKED. The amendment author's commit time of this file (or its successor amendment) is the binding pre-execution mtime for H2 audit.

### Amendment 1 author

- **Quant Researcher:** filed 2026-04-27 in response to adversarial review; closes 8 critic findings; original spec unchanged, this amendment binding additively.
