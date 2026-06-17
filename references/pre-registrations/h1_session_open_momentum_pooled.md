# Pre-Registration: H1 — Pooled Multi-Pair Session-Open Momentum (8 majors)

**Status:** FROZEN — AWAITING DATA. Authored data-independent, BEFORE any 1h bar is loaded
or inspected for this hypothesis. The org-wide trial counter is **NOT** burned by this
authoring; it burns once, later, only when the frozen single structure is actually spawned
as a backtest (and only after the confirmability PASS-CONDITIONS below clear on landed data).
**Strategy ID:** h1_session_open_momentum_pooled
**Universe:** 8 liquid majors, POOLED (1h bars)
**Trial:** NOT YET SPAWNED — `trial_id: 5fff4c63-cc2e-4939-8f63-6859a711fa53`
(`counter_burned: false`; org-wide N would be 49 at the moment of spawn, current N=48)
**Date frozen:** 2026-06-17 (pre-data)
**Source rubric:** `references/intraday_confirmability_screening_rubric.md` (HoQR FROZEN, G1–G7)
**HoQR shortlist (rank 1):** `.fintech-org/artifacts/2026-06-16-prep-plan/hoqr-hypothesis-prep.yaml`
**Scaffold lifted:** `.fintech-org/artifacts/2026-06-17T02-37-59Z_intraday_eurusd_1h/qr-prereg-v2.yaml`
(trial-48 overnight_mr KILL-gate house style) + the 2026-05-30 ORB design.

---

## Hypothesis (H1) and Null (H0)

**H1 (alternative):** The directional impulse formed in the first hours after a major FX
session open (London ~07:00 UTC, New York ~13:00 UTC) extends intraday — a real
order-flow/liquidity-arrival momentum effect — such that taking the position in the *sign
of the opening-range impulse* and holding for a few hours has expected value **> 0 net of a
frozen, conservative, session-aware round-trip cost**, and this edge is **detectable in ≤2yr**
once pooled across 8 majors (pooling adds independent events without re-using the same
per-event edge).

**H0 (null being tested):** Pooled session-open momentum is **not net-of-TCA tradeable** —
the post-open directional continuation has expected value **≤ 0 after the session-aware
round-trip cost** (i.e. it is cost-dominated and/or noise), and any positive in-sample
pooled Sharpe is multiple-testing/selection, captured by the org-wide Deflated-Sharpe
deflation at N. The session-open impulse is an arbed-out / non-stationary remnant by the
2021–2025 validation window.

This is the firm's modal expectation. Base rate: 0 validated / 48 honest trials; NHT honest
estimate of finding *any* validated net-of-TCA intraday alpha this cycle is ~15% (10–20%).

---

## Frozen Single Structure (ONE structure — no grid, no parameter search)

All degrees of freedom are LOCKED below BEFORE any IS look. There is exactly **one** entry
rule and **one** exit rule. No sweep over session-window length, threshold, hold length, or
pair subset is permitted — a search would inflate effective-N and raise the DSR bar. This
keeps honest-N = **1** for this hypothesis when it is spawned.

**Entry (frozen):** On the completed 1h bar at a session open hour `H_open` (`H_open ∈
{07:00 UTC = London, 13:00 UTC = New York}`), define the **opening-range impulse** as the
sign of the close-to-close log return of the **first 1 post-open bar** measured *strictly on
completed bars*:
- `r_open = log(close[H_open] / close[H_open − 1h])` (the open-hour bar's own return).
- **LONG** candidate if `r_open ≥ +κ · σ_sess`; **SHORT** candidate if `r_open ≤ −κ · σ_sess`;
  else **flat** (no trade this open).
- Direction = **sign of the impulse** (momentum continuation, NOT fade).
- `κ = 1.0` (LOCKED — a z-score floor so we only act on a *qualified* impulse, not every open).
- `σ_sess` = stdev of 1h log-returns over the trailing **20 same-session-open-hour-class** bars
  (i.e. the trailing 20 London-open bars for a London signal), computed STRICTLY from bars
  `≤ H_open − 1h` (the current open bar is EXCLUDED from its own σ — no-lookahead by
  construction). The trailing window SKIPS weekend/holiday gap bars (no forward-fill).

**Exit (frozen):** Enter at the OPEN of the next bar (`H_open + 1h`); the engine shifts the
signal by `entry_delay_bars = 1` (signal at `H_open` executes at `H_open + 1h`;
`test_no_lookahead` MUST stay green). Hold a fixed **3 bars** (3h) and exit at the close of
`H_open + 3h` (time-stop), OR earlier if the per-trade adverse stop triggers (see below).
No discretionary hold extension. Flat between signals.

**Per-trade stop (frozen):** Hard adverse-excursion cap = `1.5 · σ_sess_pips` against the
position, plus the 3-bar time-stop. Where the held bars pierce the stop level, the stop is
assumed filled at the level (declared conservative 1h-bar approximation, not a hidden one).

**Weekend/holiday gap (frozen):** A session-open signal whose 3-bar hold would straddle the
Friday 21:00 UTC → Sunday ~21:00 UTC weekend gap (or any holiday session gap) is **NO-TRADE**.
A momentum bet is never held across the gap. (Inherits trial-48 F-004.)

**Pooling (frozen):** The identical structure runs **independently on each of the 8 pairs**;
their per-trade returns are POOLED into one return stream for the Sharpe/DSR computation. No
per-pair tuning. No pair is dropped or weighted by in-sample performance (that would be
selection). A pair enters the pool **only** if it clears the CTO data-quality gate and the
CRO cost-coverage gate (Data Preconditions below); a pair excluded for **data quality** is
out of the universe for *mechanical* reasons declared pre-data, which is not selection.

**Cost (frozen):** Session-aware, per-bar, per-pair round-trip cost supplied by the CRO
intraday cost model, defaulting to **`spread_p90_pips`** (cost-stressed, never the median;
CRO binding constraint), plus thin-book slippage and commission per the CRO spec, charged on
entry and exit of every trade. Daily swap is charged **only** if a hold crosses the 22:00 UTC
rollover (3× on Wednesday) via the **rollover-aware** holding cost — never pro-rated by hour
(CRO CM-2). For a 3-bar intraday hold not crossing 22:00 UTC, swap = 0.

### Locked degrees of freedom (enumerated, frozen pre-data)
`session_open_hours = {07:00, 13:00} UTC` · `impulse_window = 1 bar (open hour)` ·
`κ = 1.0` · `σ lookback = 20 same-open-hour-class bars (current bar excluded)` ·
`direction = sign(impulse) [momentum]` · `hold = 3 bars` · `adverse stop = 1.5·σ_sess` ·
`one signal per open per pair (freq cap)` · `cost = CRO p90 session-aware + rollover-aware swap` ·
`size = vol-targeted, cold-start size_multiplier ≤ 0.25 (CRO ladder)` ·
`weekend/holiday-gap = NO-TRADE`. **No grid over any of these.**

---

## Universe (the 8 majors, pooled)

`EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, EURGBP`

Pooled into a single return stream. The 4 JPY/cross minors (EURJPY, GBPJPY, AUDJPY, EURCHF)
are **NOT** in H1's frozen universe; they may be added only as an explicit, separately
pre-registered extension after H1's primary run — never mid-flight.

---

## Windows (IS / OOS, one-shot, embargo/purge)

```
is_window:        2021-01-01T00:00Z .. 2024-05-31T21:00Z   (~3.4yr in-sample / development)
seam_embargo:     2024-06 discarded (≥20 trading days ≈ ~480 hourly bars; neither trained nor tested)
oos_window_start: 2024-07-01T00:00Z
oos_window_end:   2025-12-31T21:00Z                        (~1.5yr one-shot holdout)
oos_one_shot:     true   (burned exactly once, ONLY if all pre-OOS KILL gates pass)
oos_overlap:      false
```

- Chronological ~70/30 split, declared BEFORE any look. The most-recent ~18 months are the
  holdout because forward-confirmability is the question.
- **Purge/Embargo (ML methodology):** CPCV with PURGE = EMBARGO = the **full feature window
  ≈ 480 hourly bars** (~20 trading days, the span of the 20 same-open-hour-class σ window) on
  EACH side of every test fold — sized to the feature window, NOT the 3-bar label, so no train
  bar's σ_sess or label overlaps a test bar's feature window. The IS/OOS **seam embargo** of
  ≥20 trading days (2024-06 discarded) carries the same horizon so neither side's feature
  window crosses the seam.
- ALL parameter freezing, CPCV, robustness and effective-N estimation happen **exclusively
  inside IS**. The OOS is read exactly once, at the end, and only if every pre-OOS gate clears.

---

## Metric

**PRIMARY = Deflated Sharpe Ratio** (Lopez de Prado 2014), net of the session-aware
per-bar round-trip cost, computed on the **POOLED** per-trade return stream.

- IS pooled net Sharpe via **Combinatorial Purged Cross-Validation (CPCV)**, N_groups=6, k=2
  (15 train/test combinations), purge=embargo=~480 bars per fold (feature-window sized).
- **DSR deflates** the observed pooled Sharpe by the multiple-testing variance using the
  **org-wide trial count visible at spawn** (current 48 + this trial → N = 49 at execution)
  and the realized skew/kurtosis of the pooled per-trade distribution.
- **PASS bar: DSR ≥ 0.95 at org-wide N.** Never report raw Sharpe alone.
- **Effective-N honesty (NHT D6, binding):** `events_per_year` used in any confirmability /
  power statement is the **autocorrelation-corrected, NON-OVERLAPPING, session-clustering-aware,
  cross-pair-haircut** effective count — never the nominal bar count. Report a 95% CI via
  stationary block-bootstrap (block ≈ 24 bars) on the pooled stream.
- Secondary (non-gating): net annualized return, max drawdown, Calmar, hit-rate, avg net
  pips/trade, trades/year, turnover, tail ratio, **Expected Shortfall (97.5%)** (CRO: VaR-only
  is a REJECT).

Effective-N stays singular ONLY because the structure is singular and every DoF is
pre-committed; if any frozen DoF were tuned on IS, true N explodes and the DSR bar rises —
which is exactly why nothing is tuned.

---

## Pre-Registered KILL Gates

FALSIFIED (status: rejected) if ANY trigger fires. Pre-OOS gates (IS only) are checked
first; the one-shot OOS holdout is burned ONLY if all pre-OOS gates pass. All thresholds are
machine-checkable.

- **KILL-0 (power, IS-only extrapolation — no OOS peek):** `f_IS` = qualifying pooled trades /
  IS trading days (post weekend-gap removal); `N_oos_expected = f_IS × OOS trading days` (from
  the calendar, NOT by reading OOS). If `N_oos_expected < 48` → INSUFFICIENT-POWER; OOS never
  burned. (Mirrors trial-48 KILL-4.)
- **KILL-1 (DSR edge, primary):** IS pooled net-of-cost **DSR ≤ 0.95** at org-wide N → KILL.
- **KILL-2 (cost domination):** **avg net pips/trade ≤ 0** after the session-aware p90 round-trip
  cost on the qualified-impulse subset → KILL. (Directly tests whether the post-open
  continuation clears the conservative cost; records "session momentum cost-dominated" either way.)
- **KILL-3 (directional-edge sanity):** pooled **directional hit-rate ≤ 0.50** on the qualified
  subset (the impulse did NOT continue more often than chance → the move was mean-reverting or
  noise, not momentum) → KILL.
- **KILL-4 (pooling-fraud / effective-N, G5):** if, after the **measured** cross-pair signal
  correlation haircut `N_eff = N_raw / (1 + (k−1)·ρ̄)` (k=8), the resulting
  `years_to_validate > 2.0yr`, the pooling did NOT deliver independent events → KILL. (Machine-
  checks the ρ̄ ≤ ~0.41 break-even; above it H1 slips past 2yr.)
- **KILL-5 (forward-decay, OOS one-shot):** OOS pooled net annualized Sharpe **< 0.30** → KILL.
- **KILL-6 (sign-inversion, OOS):** OOS pooled net Sharpe **sign ≠ IS sign** → KILL (overfit/decayed).
- **KILL-7 (concentration):** any **single pair > 50%** of pooled net PnL, OR any single
  calendar quarter **> 40%** of pooled net PnL → KILL (not a pooled structural edge; a single-name
  or single-regime artifact masquerading as breadth).

**PASS requires ALL of:** KILL-0 power cleared on IS-extrapolation · DSR ≥ 0.95 at org-wide N ·
avg net pips/trade > 0 at p90 cost · directional hit-rate > 0.50 · ρ̄-haircut years_to_validate
≤ 2.0yr · OOS net Sharpe > 0.30 · sign-concordant · no >50% single-pair and no >40% single-quarter
concentration.

`kill_switch_threshold: 0.30` (OOS net annualized Sharpe floor; KILL-5).

---

## Confirmability PASS-CONDITIONS (measured on landed data BEFORE the backtest slot is granted)

The HoQR honest reading is that H1 sits at **~3.2yr STRETCH** on low-end priors (IR=0.08) and
crosses the ≤2yr gate **only** if the landed data delivers all three of the following. These
are measured on the IS portion of the landed, gate-cleared data (a blind STRUCTURAL pass —
event counts, signal-correlation, and per-event IR — NOT a return-fishing pass), and the
backtest slot is granted ONLY if all three clear. If any fails, H1 is **STRETCH** and the slot
is **NOT** granted (parked for refinement / more pooling), per the rubric G1 disposition.

1. **IR ≥ 0.10** — per-event Information Ratio, post-(session-aware p90)-cost, on the qualified
   impulse subset (low end 0.08 → ~3.2yr STRETCH; only IR ≥ 0.10 reaches the ≤2yr region).
2. **events/yr ≥ 350** — honest, autocorrelation-corrected, NON-OVERLAPPING, post-quality-filter,
   post-frequency-cap, post-cross-pair-haircut pooled effective event count per year (NHT D6).
3. **ρ̄ ≤ 0.41** — measured mean cross-pair signal correlation (k=8). Above ρ̄ ≈ 0.41 the
   `N_eff = N_raw/(1+(k−1)ρ̄)` haircut pushes years_to_validate past 2.0yr (at ρ̄=0.50,
   `N_eff ≈ 89/yr` → ~6.9yr FAIL). This is the load-bearing pooling assumption; it is measured,
   not assumed.

These three are the rubric's G1/G2/G3/G5 instantiated. G4 (mechanism) and G6 (non-stationarity)
are addressed in Alpha-Source below; G7 (pre-registration-before-data) is satisfied by this
frozen artifact.

---

## Alpha-Source (economic justification) and Pre-Registered Reasons It Would FAIL

**Why it could exist / persist (G4 structural mechanism):** A session open is a *dated,
recurring liquidity event*. At ~07:00 UTC (London) and ~13:00 UTC (New York), a fresh tranche
of institutional order flow arrives as that timezone's participants come online, digest
overnight news, and position for the day. A directional impulse formed in the first hour after
an open reflects *real participant flow anchored to a recurring liquidity event*, not a chart
pattern, and has a documented (but decaying) tendency to extend over the next few hours. This
is the ORB / session-momentum FLOW family (who is trading, and when). It is under-arbitraged
relative to its visibility partly because the per-event edge is small and the cost hurdle is
unforgiving — exactly why it must be measured net of a conservative p90 cost, and why pooling
across 8 pairs (not a single pair) is the lever that makes it *confirmable in ≤2yr* rather than
merely *present*.

**Pre-registered reasons it would FAIL (declared before any look):**
1. **Non-stationary / arbed-out post-2020 (G6, top failure mode):** intraday session-open
   momentum in liquid majors is a well-known, heavily-traded anomaly; its half-life may already
   be short, so the edge measured 2021–2025 may be a decayed remnant or gone. The validation
   window spans a ZIRP → 2022–23 hikes → 2024–25 cuts regime sweep; an edge that needs a stable
   regime cannot be confirmed in a window containing a regime flip (KILL-6 sign-inversion is the
   machine-check).
2. **Redundant with overlap-volatility effects:** the post-open continuation may be the same
   flow as the London–NY overlap volatility expansion (H3) rather than an orthogonal open
   effect; if so the "open" anchor adds no independent confirmable alpha.
3. **Cost domination (KILL-2):** the first-bars edge is thin and session-open spreads can WIDEN
   precisely at the open; net-of-p90-cost the avg trade may be ≤ 0 (the same arithmetic that
   killed trial 48: positive gross, cost-dominated net).
4. **Pooling fraud / correlation blow-up (KILL-4):** the 8 pairs share USD/EUR legs; if measured
   ρ̄ > 0.41 the effective-N collapses and the ≤2yr confirmability is illusory.
5. **Insufficient power (KILL-0):** the κ=1.0 qualification cap may thin events/yr below the
   power floor once honestly counted (effective, non-overlapping).

---

## Data Preconditions (HARD — must hold before this is spawned)

1. **CTO per-pair data-quality gate PASS** for every pair in the pooled universe:
   `config/data_quality_gates_1h.yaml` thresholds (min bar count, max-gap %, session coverage,
   spread sanity) → per-pair `ADMIT` verdict in `data/processed/{PAIR}_1h_gate_result.json`.
   **EXCLUDE-NOT-IMPUTE**: a failing pair is dropped from H1's universe; its bars are never
   zero/default/neighbour-imputed. (Direct remediation of the QRB-6 cost-void.)
2. **CRO cost-coverage EXCLUDE gate** in place and PASS: per-pair MEASURED-cost fraction
   ≥ 0.90 over the trade window; no contiguous MEASURED gap > 24 in-session hours; default
   charge = `spread_p90_pips`. A universe containing any EXCLUDE-verdict pair cannot freeze/run.
3. **Rollover-aware swap** (CRO CM-2) implemented: daily swap charged only across 22:00 UTC
   (3× Wed), never pro-rated by hour. (Build precondition KG-4; the banned pro-rata path must be
   replaced before any session-crossing hold is costed.)
4. **Spread-column CORRECTNESS verified** end-to-end (NHT D5 / RR-1): recovered per-bar
   bid/ask spread (commit 96f6f84) cross-checked against an independent reconstruction with
   negligible/explainable residual — not merely present/plausible. A wrong spread column
   silently corrupts every net-of-TCA estimate (the exact QRB-6 void cause).
5. **NHT null battery** frozen for H1 BEFORE the backtest: the pooled net-of-TCA Sharpe must
   BEAT all of — (a) random-entry, (b) session-time-only (in-session but unconditional on the
   impulse sign), (c) daily-momentum-carryover — AND clear DSR ≥ 0.95 at org-wide N.
6. **Principal-Reviewer counter-signature** and **CEO backtest-slot grant** per the AC-06
   data→backtest workflow (`cto-infra-prep.yaml` steps 1–6); CEO confirms the trial-counter
   increment at spawn.

---

## Approval / Provenance

- **HoQR:** ranked H1 #1; routed for authoring under the FROZEN confirmability rubric.
- **Quant-Researcher:** author of this frozen pre-registration (declarative; no executable code).
- **CRO:** binding cost/risk pre-spec (`cro-risk-gates.yaml`) — p90 cost, rollover-aware swap,
  cold-start size ≤ 0.25, ES-not-VaR, EXCLUDE-not-impute.
- **CTO:** per-pair data-quality gate (`cto-infra-prep.yaml`, `config/data_quality_gates_1h.yaml`).
- **NHT:** null battery + effective-N (D6) + spread-correctness (D5/RR-1) preconditions.
- **CEO:** authorized this data-independent authoring; grants the backtest slot only on landed
  data clearing the PASS-CONDITIONS.

## Outcome

**NOT YET RUN.** No backtest spawned. No 1h price data inspected. The org-wide trial counter is
**UNCHANGED** (honest-N = 48). This artifact is FROZEN-AWAITING-DATA.
