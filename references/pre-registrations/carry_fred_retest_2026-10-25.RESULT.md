# RESULT: carry_fred retest under corrected swap accounting (2026-10-25)

Pre-registration: `carry_fred_retest_2026-10-25.md` (frozen `e59d84d`, Part B
addendum `3e29dcd`, both before the respective runs). Engine fix `012f6c1`,
EUR rate fix `05e41c1`. Artifacts: `data/results/carry_retest_part{A,B}_2026-10-25.json`.
kill_switch_threshold: 0.30
(as pre-registered; this file records results, it declares no new trial)

## Verdicts

| Part | Pre-registered verdict | Valid? |
|---|---|---|
| **A** (2010–2026, NOT blind) | **FAIL** — CF-T8 (IS SR 0.201 < 0.40) and CF-T6 (IS SR 0.075 < 0.20 at 2× costs) fire | Yes |
| **B** (2003–2009, blind) | INCONCLUSIVE (SR 0.414) | **No** — invalidated by a sleeve wipe-out (below) |

**Bet #1's 2026-08-23 "PASS again, 0.6582" is superseded.** That number came from
lump-sum swap booking, and the original pre-registration's own CF-T8 fired on it
(IS 0.00) but was not reported.

## Part A — V1 (as shipped) × C2 (rate-differential swap, 0.5% markup), vol-weighted

| Window | SR | t | p (block boot.) | DSR (N=33) | ann. return | max DD |
|---|---|---|---|---|---|---|
| IS 2010-01 → 2023-04 | 0.201 | 0.75 | — | — | — | — |
| OOS 2023-04 → 2026-04 | 0.915 | 1.60 | 0.050 | 0.31 | +4.1% | 5.7% |

Triggers: T1 0.915 (no) · T2 4/12 (no) · T3 none (no) · T4 5.7% (no) · T5 p=0.019
(no) · **T6 0.075 (FIRES)** · T7 −0.21 (reported only) · **T8 0.201 (FIRES)**.

Context cells (vol-weighted, IS / OOS): static swap 0.03 / 0.55 · markup 0% 0.33 /
1.01 · markup 1% 0.08 / 0.82 · pre-reg quintile rule 0.06 / 0.42 · sign fallback
0.15 / 1.13 · **naive equal-weight long 6 JPY crosses 0.28 / 1.16** (beats every
carry_fred variant in both windows). Correct swap accounting raises OOS
0.66 → 0.92; the earlier years remain weak.

## Part B — why the pre-registered number is invalid

The EURGBP sleeve was short EURGBP (EUR rate < GBP rate) with size fixed at entry
while EURGBP rose ~45% in 2007–08; its equity fell to 0.7% of start under C2 and
below zero under C1 (the engine has no margin/liquidation simulation — known
backlog item). The pre-registered portfolio averages per-pair % returns, i.e.
rebalances daily into the wiped-out sleeve, so a near-zero base produced +958%
single-day "returns" (portfolio +80% on 2008-12-31). The 0.414 is an artifact.

## POST-HOC diagnostic (not pre-registered) — pooled account

`scripts/run_carry_retest_pooled_posthoc.py`: sleeves start at 1/n of capital,
dollar P&L summed, a sleeve at zero stays at zero.

| Cell | Part B 2003–09 SR (t) | ann. | max DD | Part A IS / OOS SR |
|---|---|---|---|---|
| V1 × C2 (primary) | **0.23 (0.62)**, p 0.30 | +1.2% | 23% | 0.14 / 0.92 |
| V1 × C1 static swap | −0.05 (−0.13) | −0.5% | 28% | −0.02 / 0.57 |
| V2 quintile × C2 | 0.16 (0.42) | +0.5% | 14% | −0.01 / 0.47 |
| V3 sign × C2 | 0.17 (0.46) | +1.2% | 35% | 0.11 / 1.09 |
| JPY basket × C2 | 0.24 (0.63) | +2.1% | 35% | 0.27 / 1.16 |

Part A is robust to the accounting change. On the blind window the strategy earned
~1%/yr with a 23% drawdown across 2003–07, the strongest carry boom on record,
plus the 2008 crash; per the pre-registered thresholds (CONFIRMED needs SR ≥ 0.30
and t ≥ 1.65) it would be INCONCLUSIVE, and nothing is close to significant.

## Conclusion

Across 2003–2026 under corrected accounting, carry_fred shows one strong window
(2023–26, the widest USD/JPY differential in decades) and weak-to-flat results
elsewhere, does not beat a naive long-JPY-cross basket, fails its own binding
triggers, and has DSR ≤ 0.31 at N = 33. **Not a validated edge; not deployable.**

Not fixed by this work: no margin/liquidation simulation (now shown to matter);
policy rates stand in for tom-next; FEDFUNDS publication lag; ledger row for this
trial (N = 33) left to the owner.
