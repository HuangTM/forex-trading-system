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
| G5 | **Effective-N honesty (anti-pooling-fraud)** | If events/yr is reached by pooling across pairs, the pooled events must be plausibly INDEPENDENT. Apply a correlation haircut: `N_effective = N_raw / (1 + (k-1)*rho_bar)` where rho_bar is the mean cross-pair signal correlation and k = number of pooled pairs. Use N_effective in G1. | A pooled USD-bloc momentum signal across EURUSD+GBPUSD+AUDUSD is NOT 3 independent events — they share the USD leg. This is the easiest way to fake confirmability. |
| G6 | **Non-stationarity disclosure** | The single most likely reason the edge decays or flips across the validation window must be named, with a regime that spans it (e.g. 2021 ZIRP → 2022-23 hikes → 2024-25 cuts). If the edge cannot survive a regime flip inside the validation window, FAIL. | An edge that needs a stable regime cannot be confirmed in a window that contains a regime change. |
| G7 | **Pre-registration before data** | A PreRegistration YAML filed to `references/pre-registrations/` with frozen entry/exit/universe/freq-caps/retirement-triggers BEFORE any 1h bar is loaded or inspected for this hypothesis | No peeking/fishing (AC-04). |

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
