# Post-Backfill Reassessment — Breadth Wall Broken, Edge Still Absent

```yaml
artifact_type: research-reassessment
written_at: "2026-06-27T07:10:00Z"
trigger: "All 1h backfill finished — 12-pair 1h universe complete (2021-2025, ~31k bars/pair, crosses incl.)"
relates_to: PHASE0_CLOSURE_2026-06-26.md (Phase 1 scope requirements #1 edge, #2 breadth)
honest_N: 30   # descriptive probes only; no trial spent
decision: closure-strengthened-not-overturned
```

## What completed

The 1h Dukascopy backfill finished: **12 pairs, 5 years (2021-2025), ~31k bars each**, including the non-USD crosses (AUDJPY, CADJPY, EURGBP, EURJPY, GBPJPY, NZDJPY) the firm flagged as the breadth unlock. NZDJPY was the pair that completed the registered set.

## Finding 1 — the USD-correlation breadth wall is BROKEN

`compute_rho_bar_eff` (eigenvalue/sign-blind, gate ≤ 0.41) on the completed universe:

| Universe | rho_bar_eff | Gate | N_eff |
|---|---|---|---|
| USD-majors-6 | 0.597 | FAIL | 1.51 |
| Crosses-6 | 0.608 | FAIL | 1.48 |
| **All-12 (USD + crosses)** | **0.404** | **PASS** (knife-edge) | 2.20 |
| **Best 7-pair subset** (CADJPY,EURGBP,EURJPY,EURUSD,NZDUSD,USDCAD,USDJPY) | **0.260** | **PASS** (comfortable) | 2.73 |

USD-majors and crosses each fail alone (one shared factor each), but **decorrelate each other when mixed** — exactly the firm's hypothesis. **Phase 1 scope requirement #2 (real diversifying breadth) is now MET.** (Caveat: proxy on raw hourly returns; the binding gate is on signal series at pre-registration.)

## Finding 2 — but edge is still absent across all simple price-only factors

`scripts/probe_intraday_edge_feasibility.py` — time-series momentum (best-evidenced FX factor), pre-specified lookbacks {12,24,48,96}h, all cells reported, firm's CD0 cost model, 5yr confirmability bar (net Sharpe ≥ 0.89 → t≥2):

| Lookback | Trades/yr/pair | Net-positive pairs | Portfolio net SR (12/7) | Portfolio GROSS SR |
|---|---|---|---|---|
| 12h | ~1672 | **0/12** | -6.18 / -6.43 | **+0.30** |
| 24h | ~1073 | 0/12 | -4.11 / -4.42 | -0.04 |
| 48h | ~736 | 0/12 | -2.92 / -3.11 | -0.16 |
| 96h | ~538 | 0/12 | -2.83 / -2.67 | -0.80 |

Even **frictionless**, the best case (12h) is portfolio gross Sharpe **+0.30 — below the confirmability bar before any cost**; at lower-turnover horizons the gross edge is negative. 0/12 pairs net-positive at every lookback; diversification cannot rescue a negative mean. Combined with the earlier F1-F6 CD0 screen (also all net-negative), **~10 simple price-only intraday factor families are now exhausted on this universe with a negative result.**

## Implication

The completed data **strengthens** the Phase 0 closure rather than overturning it:

- It definitively removes the "maybe breadth was the binding blocker" hypothesis. Breadth was real and is now broken — and edge is *still* absent. **Breadth was not the binding constraint; edge is.**
- Phase 1 scope: requirement **#2 (breadth) MET**; requirement **#1 (gross edge surviving cost) tested and UNMET** across every simple price-only factor.
- The Phase 1 entry gate therefore remains **not cleared** (it needs BOTH; #1 fails). No pre-registration is justified; honest-N stays 30.

## Forward guidance (unchanged, now better-evidenced)

A money path requires a genuinely **different edge CLASS** — order-flow / positioning, microstructure, macro-event, or ML-conditioned signals — NOT more pairs, more history, or more price-only factors on this universe. Those classes need data the firm does not have and are a separate, larger undertaking. Until such a candidate clears a $0 gross-edge feasibility probe, the correct posture stays **OBSERVE-ONLY**.

**Scope honesty:** this tested momentum/reversal/breakout/session families only — not order-flow, alt-data, or novel microstructure. Those remain untested (and un-acquired).
