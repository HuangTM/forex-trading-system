# Pre-Registration: vol_target_carry

**Status:** Retroactive pre-registration
**Date:** 2026-04-25 (same-day development and validation context noted below)
**Strategy ID:** vol_target_carry
**Pair:** USDJPY
**Binding commit at registration:** see git log

## Retroactive Pre-Registration Note

This pre-registration is filed retroactively for a strategy developed and
validated on the same day (2026-04-20). This is a known methodological
limitation. The binding falsification conditions (T1–T8 below) are derived from
the CONSENSUS.md arson-test evidence, not from cherry-picking post-hoc.

Future strategies MUST file pre-registrations BEFORE validation runs.

---

## Hypothesis

**Primary:** USDJPY long-only carry with volatility-targeted sizing produces
annualized Sharpe > 0.60 on real Saxo daily data (2010–2026), net of realistic
costs (spread 1.0 pip, slippage 0.5 pip, commission 0.5 pip, swap 0.8 pip/day).

**Mechanism:** Volatility-targeted position sizing (inversely proportional to
realized 252-day vol) smooths drawdowns and captures more carry yield in calm
periods while reducing exposure in choppy periods.

---

## Falsification Criteria

gate_threshold: 0.60

The strategy is considered falsified (retire, do not deploy additional capital)
if ANY of the following conditions is observed on new out-of-sample data:

- **VTC-T1:** Production-engine Sharpe < 0.60 on full history (2010–2026)
- **VTC-T2:** Max drawdown exceeds 25% on production-engine run
- **VTC-T3:** Walk-forward OOS windows: fewer than 6 of 14 beat B&H Sharpe
- **VTC-T4:** DSR < 0.90 (deflated for org-wide trial count)
- **VTC-T5:** Forward 6-month paper Sharpe < 0.0 (live SIM evidence)
- **VTC-T6:** Costs doubled: Sharpe falls below 0.40
- **VTC-T7:** Vol signal lagged 5 days: Sharpe falls below 0.50 (vol persistence test)
- **VTC-T8:** Rank percentile vs 200 shuffled-vol signals falls below 95th percentile

---

## Strategy Parameters (as registered)

| Parameter | Value | Notes |
|---|---|---|
| target_vol | 0.10 | 10% annualized target |
| vol_window | 252 | Daily bars for realized vol |
| leverage_cap | 2.0 | Max 2x notional |
| min_carry | -0.10 | No carry filter (VT does the work) |

---

## Validated Evidence (from arson-test campaign 2026-04-20)

All numbers from `scripts/vol_targeting.py` on Saxo USDJPY daily 2010–2026:

- Sharpe: 0.76 vs B&H 0.58 (+0.18)
- MaxDD: 13.5% vs B&H 17.0% (-3.5pp)
- Walk-forward: 9/14 OOS 2-yr windows beat B&H, avg delta +0.08
- Null hypothesis rank: 99.5% vs 200 shuffled-vol signals (p=0.005)
- Arson: double costs, 1d/5d vol delay all leave Sharpe >= 0.76

**IMPORTANT:** The numbers above are from an ad-hoc script. The production-engine
harness trial (Component 2 of Path A) may differ due to: exact cost model
application, sizer discretization, and engine bar-level logic. If production-engine
Sharpe diverges materially from 0.76, the divergence is a finding (not a pass).

---

## Retirement Triggers (machine-checkable)

- If harness trial Sharpe < gate_threshold (0.60): auto-retire
- If DSR < 0.90: escalate to Head of Quant Research before any capital increase
- If 90-day rolling live Sharpe < 0: CTO kill-switch review required

---

## Approval

- Quant Researcher: filed by HoQR authority per CONSENSUS.md
- CTO: conditions C1–C2 satisfied before first harness run
- NHT: p=0.005 from 200-shuffle permutation test
