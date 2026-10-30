# RESULT: carry with a speculative-crowding overlay (CFTC COT), monthly

kill_switch_threshold: 0.0 (declared in the pre-registration; see the verdict table there)

**Verdict: FAIL.** Run once on 2026-10-30, after the pre-registration and runner were frozen
at `c5ec8bb`. Trial `f713f511`; honest N = 36. Output:
`data/results/fx_cot_crowding_carry_monthly.json`.

The FAIL condition fired on the full window: overlay minus carry has mean ≤ 0
(−0.44%/yr). Per the owner's rule, the research programme stays paused.

## Primary statistic: overlay − carry, paired monthly, base cost

| Window | Ann. mean of d | t | one-sided bootstrap p | info ratio |
|---|---|---|---|---|
| Full 2001-01..2026-09 (309 mo) | **−0.44%** | −1.28 | 0.88 | −0.25 |
| Pre-2012 | −1.23% | −2.39 | 0.99 | −0.72 |
| Post-2012 | +0.14% | +0.31 | 0.38 | +0.08 |

The high-cost and gross cells are within 0.03%/yr of base. The difference is not a cost
effect: overlay turnover is 0.29 per month against 0.10 for carry, but the costs involved
are small.

## Portfolios (base cost)

| | Full SR | t | DSR(N=36) | Pre-2012 SR | Post-2012 SR | Max DD |
|---|---|---|---|---|---|---|
| Carry (point-in-time rates) | 0.384 | 1.95 | 0.426 | 0.467 | 0.310 | 36.4% |
| **Overlay** | **0.318** | 1.62 | **0.309** | 0.341 | 0.311 | 38.3% |

Consistency check: plain carry reproduces trial 35's point-in-time carry exactly
(SR 0.384, `fx_multifactor_monthly.RESULT.md` addendum).

Per-year d (%/yr). Selected years: 2003 −3.0, 2004 −2.7, 2005 −4.9, 2008 −2.6, 2013 −4.7,
2018 +2.7, 2020 −2.1, 2021 +1.9.

Crowded-leg counts over 309 months:

| EUR | JPY | GBP | AUD | NZD | CAD |
|---|---|---|---|---|---|
| 36 | 67 | 56 | 68 | 36 | 42 |

## Reading

- **The hypothesis is rejected in its pre-registered form.** Halving carry legs where
  speculators were unusually extended in the same direction lowered carry's return. The
  cost is concentrated before 2012 (t −2.4), the period where crowded carry trades were
  supposedly most dangerous.
- **The overlay did not help in the crash it was designed for.** In 2008 it lost a further
  2.6% relative to carry, and its maximum drawdown is larger (38.3% vs 36.4%). On this
  data, extended speculative positioning marked carry trades that kept paying. It did not
  mark trades that were about to unwind.
- The post-2012 difference is a negligible +0.14%/yr (t 0.3).

## Known limits

The limits listed in the pre-registration still apply:
- the 2001–2006 overlap with the original paper;
- legacy "noncommercial" is a coarse proxy for speculators;
- G7 breadth only;
- NZD has no positioning data before about 2005.

None of these limits changes the sign of the result. Exploratory follow-ups would be new
trials, and per the owner's rule none is planned. Examples are other thresholds, the
opposite sign, or a positioning-change signal.
