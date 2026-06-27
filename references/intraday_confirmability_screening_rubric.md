# Intraday Confirmability Screening Rubric (FROZEN)

**Status:** FROZEN — 2026-06-17
**Owner:** Head of Quant Research
**Scope:** Every 1h (intraday) hypothesis MUST pass this rubric BEFORE it is granted
a backtest slot. This rubric is the gate that the firm's DATASET-WALL lesson produced:
on daily data, every idea floored at 3–5yr to validate and the firm correctly spent
nothing. 1h data only matters if it actually moves a hypothesis to ≤2yr confirmability.
This rubric is how we check that *before* peeking at the data.

This extends — does not replace — the existing QRB confirmability gate and the DSR ≥ 0.95
OOS gate. It is a PRE-DATA, PRE-BACKTEST screen.

---

## The core formula

```
SR_ann       = sqrt(events_per_year) * IR_per_event          (event-aggregation identity)
N_required   = (z_alpha + z_power)^2 / IR_per_event^2          (events to detect the per-event edge)
             ≈ 6.18 / IR_per_event^2   at alpha=0.05 (1-sided), power=0.80
years_to_validate = N_required / events_per_year
```

Equivalently, since `N_required` events occur in `years_to_validate` years, the horizon
is governed by **both** the per-event edge AND the event rate. 1h data raises
`events_per_year`; multi-pair pooling raises it further (independent events across pairs
add to N **without** re-using the same per-event edge — this is the lever the prior
EURUSD-only cycle lacked).

**Worked anchor:** IR_per_event = 0.10 → N_required ≈ 618 events. At 350 events/yr
(achievable by pooling a session-momentum signal across ~8 liquid pairs) →
years_to_validate ≈ 1.77yr → **PASSES**. The same IR on one pair at 150 events/yr →
4.1yr → FAILS. The pooling is doing the work.

---

## The gates (ALL must pass — any single FAIL blocks the backtest slot)

| # | Gate | Pass condition | Why |
|---|------|----------------|-----|
| G1 | **Confirmability horizon** | `years_to_validate ≤ 2.0yr` under the HONEST (not optimistic) IR and event-rate estimates | The DATASET-WALL gate. The whole point of 1h data. |
| G2 | **Honest events/yr** | events_per_year estimated AFTER the quality filter and frequency caps that the strategy will actually run with (not the raw bar count) | Prior ORB cycle inflated events/yr by ignoring its own freq caps. |
| G3 | **Post-cost per-event edge** | IR_per_event computed NET of the session-aware round-trip cost (CRO-supplied), and `capturable_move_pips > round_trip_cost_pips` with margin | Kills cost-dominated traps (e.g. quiet-session fade where cost > range). |
| G4 | **Structural mechanism** | A written economic/microstructure reason the edge SHOULD exist (session flow, liquidity, scheduled-information diffusion, rollover timing) — NOT a data-mined pattern | Replication-crisis discipline; mechanism predicts persistence. |
| G5 | **Effective-N honesty (anti-pooling-fraud)** | If events/yr is reached by pooling across pairs, the pooled events must be plausibly INDEPENDENT. Apply the correlation haircut defined in **§G5 ρ̄_eff (amended 2026-06-19)** below; use the resulting `N_eff*` in G1. | A pooled USD-bloc momentum signal across EURUSD+GBPUSD+AUDUSD is NOT 3 independent events — they share the USD leg. This is the easiest way to fake confirmability. |
| G6 | **Non-stationarity disclosure** | The single most likely reason the edge decays or flips across the validation window must be named, with a regime that spans it (e.g. 2021 ZIRP → 2022-23 hikes → 2024-25 cuts). If the edge cannot survive a regime flip inside the validation window, FAIL. | An edge that needs a stable regime cannot be confirmed in a window that contains a regime change. |
| G7 | **Pre-registration before data** | A PreRegistration YAML filed to `references/pre-registrations/` with frozen entry/exit/universe/freq-caps/retirement-triggers BEFORE any 1h bar is loaded or inspected for this hypothesis | No peeking/fishing (AC-04). |

---

## §G5 ρ̄_eff — the effective-N correlation haircut (AMENDED 2026-06-19)

**Amendment provenance:** Mathematician `mathematician-rho-bar-analysis.yaml` + NHT
`nht-rho-bar-ruling.yaml` (both `.fintech-org/artifacts/2026-06-19-rho-bar/`). This amends a
genuine under-specification ("mean cross-pair signal correlation" — signed? magnitude? eigen?)
toward its sole anti-fraud reading. It is purely additive and STRICTER. The fix lives here in
the rubric so EVERY future pooled hypothesis inherits it.

### The series (second bug fix — what ρ̄ is measured ON)

The correlation matrix is computed on the per-pair **PnL-CONTRIBUTION (signal×return)** series
`x_{p,t} = signal_{p,t} · ret_{p,t}` — the actual pooled summands — **demeaned and
event-aligned** on common event timestamps (non-fires treated as 0 contribution, consistently
across pairs). It is **NOT** raw price returns and **NOT** the quote-signed "signal" series.
Rationale: `N_eff` must reflect `Var(Xbar)` of the pooled estimator, which is a functional of
`Cov(x_p, x_q)` of the summands themselves. A coherent factor strategy (e.g. USD-momentum)
applies signs that REALIGN raw-negatively-correlated legs (short EURUSD + long USDJPY in a
USD-up move) into the SAME positively-correlated bet — visible only on the contribution series.

### The statistic (eigenvalue-based, sign-blind)

Let `C` be the k×k Pearson correlation matrix of the demeaned, event-aligned PnL-contribution
series, with eigenvalues `λ_1 ≥ … ≥ λ_k` (Σλ_i = k, since diag(C)=1). Gate on:

```
N_eff* = MIN(  N_raw / λ_max ,                       (λ_max / Kish route)
               N_raw · k / Σλ_i²  [participation ratio PR] ,
               N_raw · k / ENB    [Meucci ENB = exp(−Σ p_i ln p_i), p_i = λ_i/Σλ_j ; if used] )

floor/ceiling always:   N_raw / k  ≤  N_eff*  ≤  N_raw
```

Report the equivalent scalar in the rubric's familiar Kish notation:

```
ρ̄_eff = (λ_max(C) − 1) / (k − 1)        ⇒    N_raw / (1 + (k−1)·ρ̄_eff) = N_raw / λ_max
```

`ρ̄_eff` reduces EXACTLY to the true ρ when `C` is equicorrelated, and for a sign-mixed
one-factor matrix returns the dominant-factor variance share (NOT zero), because `λ_max` is
blind to variable sign-flips (`C' = SCS` is similar to `C`; spectrum invariant).

### FORBIDDEN: the naive SIGNED pairwise mean

The signed simple mean `ρ̄_signed = mean(C_{pq})` is **categorically forbidden** firm-wide. It
is an **SD2-class under-deflation fraud**: anti-correlated entries CANCEL, laundering a
one-factor basket into nominally-independent events. It **fails Redundant-Pair Monotonicity** —
adding a perfectly redundant sign-flipped duplicate (corr = −1) drives `ρ̄_signed → −1`,
`DEFF → 0`, `N_eff → +∞`: a zero-information pair manufactures INFINITE fake independence. Any
artifact computing pooled effective-N from a signed mean is rejected on sight (NHT veto
`sharpe-not-distinguishable-from-noise-under-deflation`).

### Fallback (no eigendecomposition available)

Use the **MAGNITUDE mean** `ρ̄ = mean|C_{pq}|` in the Kish form `N_raw/(1+(k−1)ρ̄)`. It
dominates the signed mean by the triangle inequality (`mean|C_{pq}| ≥ |mean C_{pq}|`) and so
removes the sign-cancellation fraud. It is a heuristic floor over the signed mean, NOT a
substitute for the spectral statistic when eigendecomposition IS available (it has no proven
ordering against `ρ̄_eff`).

### Conservative rule

WHEN IN DOUBT, take the MIN N_eff route (lower N_eff / larger deflation). Neither the `λ_max`
route nor the PR route dominates the other in general — that is precisely why the gate is the
explicit `MIN` over routes, not a single statistic. Under-deflation is the fraud; over-deflation
only costs a real edge we can re-pursue.

### Threshold (UNCHANGED)

The **`ρ̄_eff ≤ 0.41` break-even does NOT move.** `ρ̄_eff` is the sign-blind
equicorrelation-equivalent on the SAME Kish scale, so the existing
`N_eff = N_raw/(1+(k−1)·ρ̄_eff)` gate and the `0.41` threshold are KEPT as-is. **Re-deriving the
0.41 break-even under the new statistic would be a SEPARATE pre-result freeze — it is NOT part
of this amendment.**

### Implementation follow-on

The eigen-computation of `C`, its full spectrum (`λ_max`, PR, ENB, `ρ̄_eff`, `cond(C)`,
Ledoit–Wolf-shrunk variants) and `N_eff*` on landed gate-cleared data is **quant-developer's
job** (Mathematician routed it), to be run when the full-8 majors land — not computed at
amendment time.

---

## Scoring & disposition

- **PASS** — all of G1–G7 satisfied → eligible for a backtest slot (subject to NHT null
  battery + PR pre-registration verification).
- **STRETCH** — mechanism (G4) and cost (G3) hold but `years_to_validate ∈ (2.0, 3.0]yr`
  under honest estimates → NOT granted a slot now; parked for refinement (can it be pooled
  across more pairs to cross 2.0?).
- **FAIL** — any of G1 (after honest+pooling-haircut), G3, G4, G6 fails → archived to the
  falsification log with the failing gate recorded. Do not resurrect without new evidence
  addressing the failing gate.

---

## Honesty defaults (use the pessimistic end when uncertain)

- IR_per_event: use the LOW end of the plausible range, post-cost.
- events_per_year: count AFTER quality filters and freq caps.
- pooling: always apply the G5 correlation haircut; never assume independence across
  same-leg pairs.
- z-constants: alpha = 0.05 one-sided (z=1.645), power = 0.80 (z=0.84) → numerator 6.18.
  A two-sided or higher-power choice only RAISES N_required (more conservative) — never lower it.

---

## What this rubric is NOT

It does not promise profit. Passing G1–G7 means the hypothesis is **confirmable in ≤2yr** —
i.e. if the edge is real we can detect it, and if it is noise we can reject it, within the
data we have. The base rate stands: most hypotheses that pass this screen will still FAIL
out-of-sample. Success at this phase = a queue of *confirmable* hypotheses ready to run the
moment clean 1h data lands, with zero data-structure surprises forcing a re-registration.
