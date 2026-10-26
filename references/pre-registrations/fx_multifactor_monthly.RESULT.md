# RESULT: currency-level carry + value + momentum, monthly (2026-10-26)

Pre-registration `fx_multifactor_monthly.md` (frozen `e455aab`, before any return was
computed). Artifact: `data/results/fx_multifactor_monthly_2026-10-26.json`.
kill_switch_threshold: 0.0
(as pre-registered; this file records results, it declares no new trial)

## Verdict: INCONCLUSIVE (composite × base costs)

| Window | Sharpe | t | p (boot) | DSR (N=35) | ann. return | ann. vol | max DD |
|---|---|---|---|---|---|---|---|
| **Full 2001-01 → 2026-09** | **0.49** | **2.47** | 0.018 | **0.63** | +1.86% | 3.8% | 9.8% |
| Pre-2012 (in published samples) | 0.78 | 2.58 | 0.020 | 0.66 | +3.35% | 4.3% | 5.6% |
| **Post-2012 (post-publication)** | **0.22** | 0.85 | 0.166 | 0.09 | +0.75% | 3.4% | 9.8% |

- PASS needed t ≥ 1.65 (met: 2.47), DSR ≥ 0.95 (**not met: 0.63**) and post-2012
  Sharpe > 0 (met: 0.22). FAIL needed full or post-2012 Sharpe ≤ 0 (not met).
- Gross (no costs): full 0.60, post-2012 0.35. High costs: full 0.38, post-2012 0.10.

## By factor (base costs, full / pre-2012 / post-2012 Sharpe)

| Factor | Full | Pre-2012 | Post-2012 |
|---|---|---|---|
| Carry | 0.37 | 0.47 | 0.29 |
| Value | −0.04 | −0.00 | −0.08 |
| Momentum | 0.14 | 0.38 | −0.09 |
| **Composite** | **0.49** | **0.78** | **0.22** |

Return correlations: carry–value −0.34, value–momentum −0.38, carry–momentum +0.14.
The composite's value is diversification: in 2008 carry lost 28.7% and value gained
23.4%, so the composite lost 0.2%.

## Reading

- A modest premium is visible over 26 years (t 2.47), but it sits mostly before 2012 —
  inside the period the papers studied. After publication the composite earns a net
  Sharpe of 0.22, indistinguishable from zero (t 0.85).
- Momentum disappeared after 2012; value never paid net of costs in this G7 universe;
  carry is the only factor positive in both halves.
- Scaled to 10% volatility, post-2012 performance would be ~+2%/yr above cash with a
  ~25% drawdown — before tax, and with a 7-currency cross-section much thinner than
  the papers' 15–48.
- Per the owner's pre-agreed rule (pause the programme unless this bet passes), this
  result does not justify more trials.
