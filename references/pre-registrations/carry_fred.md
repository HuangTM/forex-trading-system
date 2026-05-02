# Pre-Registration: carry_fred

**Status:** Prospective pre-registration
**Date:** 2026-04-25 (before any code written or validation run)
**Strategy ID:** carry_fred
**Registered by:** HoQR — CONSENSUS Bet #1
**Binding commit at registration:** filed before first commit of carry_fred.py

---

## Hypothesis

**Primary:** Long-short FX carry on a 12-pair daily universe, with signals derived
from FRED central-bank rate differentials, cross-sectionally rank-normalized and
equal-vol-weighted, produces portfolio annualized Sharpe ≥ 0.30 net of realistic
costs on a true 36-month out-of-sample holdout (2023-04-25 to 2026-04-25).

**Mechanism:** Higher-yielding currencies tend to appreciate against lower-yielding
ones (the carry trade) — the "forward premium puzzle". The signal is computed as:
rate_differential = base_rate - quote_rate from FRED monthly rates, forward-filled
to daily frequency, cross-sectionally rank-normalized to a [-1, +1] signal across
all 12 pairs. The portfolio is equal-vol-weighted (each pair sized inversely
proportional to its own realized volatility) to prevent high-vol pairs dominating.

**OOS holdout:** 2023-04-25 to 2026-04-25 (last 36 months). This period is reserved
before any code is written. Training/exploration may use only data prior to
2023-04-25.

---

## Universe

All 12 pairs listed below, equal participation:

| Pair | Base | Quote |
|------|------|-------|
| AUDJPY | AUD | JPY |
| AUDUSD | AUD | USD |
| CADJPY | CAD | JPY |
| EURGBP | EUR | GBP |
| EURJPY | EUR | JPY |
| EURUSD | EUR | USD |
| GBPJPY | GBP | JPY |
| GBPUSD | GBP | USD |
| NZDJPY | NZD | JPY |
| NZDUSD | NZD | USD |
| USDCAD | USD | CAD |
| USDJPY | USD | JPY |

---

## Signal Construction (pre-registered)

1. **Rate differential**: `rate_diff = base_currency_rate - quote_currency_rate`
   sourced from FRED monthly rates, forward-filled to daily frequency.
2. **Cross-sectional rank normalization**: at each bar, rank all 12 pair
   differentials and z-score (subtract mean, divide by std). Clip to [-1, +1].
3. **Long-short balance**: top quintile (rank ≥ 80th pct) receives positive signal,
   bottom quintile (rank ≤ 20th pct) receives negative signal, middle is neutral.
   Implemented via clipping the z-scored rank signal.
4. **Simplification fallback** (if cross-sectional ranking degrades OOS):
   per-pair signal = sign(rate_differential) only (no ranking). This fallback is
   documented if used and constitutes a separate falsification-level test.

---

## Metrics (pre-registered)

- **Primary:** Annualized Sharpe ratio (daily returns, annualized by sqrt(252))
  - Per-pair Sharpe on full in-sample period
  - Equal-vol-weighted portfolio Sharpe on OOS holdout (2023-04-25 to 2026-04-25)
- **Secondary:** Max drawdown (%), number of trades, Sortino ratio
- **Portfolio construction:** equal-vol-weight = target_vol / pair_realized_vol
  where target_vol = 10% annualized per leg

---

## Kill Criterion (pre-registered threshold)

gate_threshold: 0.30

The carry-as-edge-mechanism on this 12-pair daily universe is considered
**officially falsified** if the OOS portfolio vol-weighted Sharpe < 0.30 net of
measured costs. Per the CONSENSUS Bet #1 agreement, this retires the carry
research thread at this capacity scale.

---

## Falsification Triggers (binding, pre-registered)

- **CF-T1:** OOS portfolio vol-weighted Sharpe < 0.30 — primary kill criterion
- **CF-T2:** More than 8 of 12 per-pair Sharpes are negative in the OOS period
  (random-walk consistent result; no systematic carry edge present)
- **CF-T3:** Signal is non-varying for any pair (rate differential constant over
  multi-month periods) — indicates degenerate/stale FRED data, not a valid test
- **CF-T4:** Portfolio max drawdown > 40% on the OOS period — risk is unacceptable
  regardless of Sharpe
- **CF-T5:** The OOS Sharpe distribution across 12 pairs does not differ from
  zero-mean (one-sample t-test p > 0.10, two-tailed) — no cross-sectional
  carry signal
- **CF-T6:** Doubling measured costs reduces the in-sample portfolio Sharpe below
  0.20 — edge is too thin to survive cost estimation error
- **CF-T7:** Removing cross-sectional ranking (using raw differentials) reduces
  portfolio Sharpe by more than 0.30 vs. the ranked version — ranking provides
  no edge over raw signal
- **CF-T8:** In-sample period (pre-2023-04-25) portfolio Sharpe < 0.40 — if
  even in-sample Sharpe is weak, there is no edge to hold out
- **CF-T9:** BoJ policy-rate regime trigger — retire carry_fred within 5 trading
  days when ALL of the following clauses hold simultaneously within a
  90-trading-day window:
  - **(A)** BoJ policy rate (FRED series IRSTCB01JPM156N) >= 0.50% for >= 2
    consecutive quarter-end observations
  - **(B)** Aggregate equal-vol-weighted 60-trading-day rolling Sharpe across
    {AUDJPY, CADJPY, EURJPY, GBPJPY, NZDJPY, USDJPY} drops below 0.20 net of
    costs
  - **(C — KNOWN GAP):** The monitor docstring in `scripts/monitor_regime_triggers.py`
    references "ALL three clauses" but only implements clauses A and B. No third
    clause text exists in the implementation or in the CONSENSUS 2026-04-26
    record as of HoQR inspection 2026-05-01. CF-T9 is therefore binding on
    clauses A+B only until NHT or CEO amends this record with a ratified
    Clause C. Operationalisation: `scripts/monitor_regime_triggers.py` (commit
    61ea022) + `scripts/auto_retire_on_trigger.py` wiring.

---

## Strategy Parameters (as pre-registered)

| Parameter | Value | Notes |
|---|---|---|
| rate_data_path | data/rates/rate_differentials.parquet | FRED-sourced differentials |
| rank_normalize | true | Z-score cross-sectional rank |
| target_vol | 0.10 | 10% annualized per-leg vol target |
| min_differential | 0.001 | Ignore pairs with near-zero carry |
| oos_holdout_start | 2023-04-25 | OOS period reserved before code written |

---

## Approval

- Quant Researcher: pre-registered prospectively per docs/decisions/CONSENSUS.md Bet #1 conditions
- NHT: OOS holdout enforced in harness; no data snooping permitted after this file commit
- CTO: per-pair plus portfolio tests required before declaring pass/fail

### CF-T9 Amendment — 2026-05-01

- **HoQR (HuangTM):** CF-T9 added as binding falsification criterion per CONSENSUS 2026-04-26
  Section 5 and Wave-5 Round-1 closure mandate. Clauses A+B are operationalised;
  Clause C gap is flagged and documented. Amendment signed 2026-05-01.
- **NHT:** Co-signed 2026-05-02 (Wave-5 Round-3, artifact: `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml`). Binding on Clauses A+B only. Clause C gap accepted as known-incomplete deferral. Conditions: (1) paper-launch communications must state CF-T9 is A+B binding with C pending; (2) Clause C must be ratified within 60 trading days of paper launch or NHT re-review is mandatory; (3) sizing must not use 0.80 regime-active Sharpe as base case — use ~0.07 for regime-inactive periods.
