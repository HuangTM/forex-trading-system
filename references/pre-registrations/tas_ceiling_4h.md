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
- **NHT:** Bonferroni denominator handling per N2 ruling (count-of-trials = 17 unless NHT escalates); dissent on Bet #1 testability does NOT extend to this pre-reg (Bet #2 has a clean OOS window with no regime-overlap claim).
- **CTO:** PROCESS-IMPL-1 and PROCESS-IMPL-2 added on top of CONSENSUS's BET2-T1..T6 to close WS-05 risk ahead of dispatch.
- **CRO:** backtest-only research dispatch — no paper-trading exposure, no live-capital exposure, no broker-side state mutation. No CRO sign-off required for this artifact.
