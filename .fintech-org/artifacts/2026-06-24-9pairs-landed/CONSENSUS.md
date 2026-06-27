# Consensus on: Zero-budget readiness reassessment of intraday 1h FX data with 9 pairs landed

**Status:** awaiting-ratification
**Session artifacts:** `.fintech-org/artifacts/2026-06-24-9pairs-landed/`
**Date:** 2026-06-24

---

## Roles staffed

| Role | Rationale |
|------|-----------|
| Head of Quant Research (HoQR) | Owns H1 freeze/unfreeze decision (C5), SPEND/NO-SPEND call (C4), F1–F6 retirement call, and strategic recommendations. |
| Quant Developer (QD) | Ran DQ manifests for EURGBP and AUDJPY, recomputed rho_bar_eff on all required subsets, ran CD0 screen with real per-bar spreads across all 9 pairs and 6 families. |
| Chief Risk Officer (CRO) | Veto authority on any trial spend; owns concentration-regime characterization; three independent each-sufficient veto arguments. |
| Null-Hypothesis Tester (NHT) | Structural skeptic; tested Claims (i)/(ii)/(iii); dissent append-only and verbatim-preserved. |
| Principal Reviewer (PR) | Independent recompute of all three load-bearing facts (rho_bar_eff ALL-9, DQ calls, all-54-CD0-FAIL); single review wave; approve-with-conditions (0 blocking findings). |
| PM | Synthesized this consensus; ensured dissent preservation; did not make technical calls. |

---

## Acceptance criteria (from PM)

- [x] C1: DQ manifest for EURGBP and AUDJPY; verdict ADMIT/EXCLUDE per pair with gap explanation.
- [x] C2: rho_bar_eff and N_eff for ALL-9 and four required subsets; delta vs prior; direction statement; H1 freeze/unfreeze call with numeric justification.
- [x] C3: CD0 screen with real per-bar spreads; all families on new crosses; all 54 pair×family combos; FAIL/STRETCH/PASS threshold applied.
- [x] C4: Explicit SPEND/NO-SPEND with deciding number; STRETCH/PASS candidate count; trial-counter decision.
- [x] C5: Explicit REMAIN-FROZEN or UN-FREEZE with binding gate and numeric shortfall.
- [x] C6: NHT null tests: Claims (i)/(ii)/(iii) all evaluated with deciding numbers.
- [x] C7: PR independently reproduced rho_bar_eff (ALL-9), DQ gates (EURGBP, AUDJPY), and CD0 spot-checks; no discrepancies on load-bearing facts.
- [x] C8: trials.jsonl entry appended with counts_toward_deflation_denominator: false and event: descriptive-screen.

---

## Decision

**NO-SPEND. H1 REMAIN-FROZEN. Honest-N stays 30. No trial-counter increment.**

All four IC roles (HoQR, CRO, NHT, PR) converged on NO-SPEND independently. EURGBP and AUDJPY both pass DQ (C1-ADMIT). The rho_bar_eff for ALL-9 = 0.4090, clearing the 0.41 G5 gate by 0.0010 (a raw-return proxy margin statistically at the gate, within estimation noise per NHT). However, the CD0 net-Sharpe screen is unanimously negative across all 54 pair × family combos — best result AUDJPY F5 = −1.56, 3.00 SR units below the STRETCH bar of 1.44. **The deciding number is −1.56 net SR vs +1.44 STRETCH; shortfall = 3.00 SR units. There is no STRETCH candidate, let alone a PASS candidate. Nothing exists to pre-register.**

The H1 freeze requires both Gate A (rho_bar_eff ≤ 0.41) AND Gate B (CD0 net SR ≥ 1.76 on ≥1 family for ≥1 pair). Gate B fails by 3.32 SR units to PASS (and 3.00 to STRETCH). The marginal Gate A pass is vacuous when Gate B fails categorically — a confirmability gate over an empty edge set certifies nothing.

---

## North-star trace

```
north_star_trace: [O1, O2]
```

- **O1:** Pre-registration gate, NHT independence, append-only dissent, and honest-N preservation honored throughout. No charter-floor violations. PR single-wave review produced approve-with-conditions with zero blocking findings. NHT dissent preserved verbatim.
- **O2:** NO-SPEND is the correct action: zero CD0 candidates at any bar; spending the counter would inflate the DSR denominator for a known-negative screen. The firm correctly ran the full two-cross reassessment and spent nothing.

---

## The three computed facts (QD-implemented, PR-independently-reproduced)

### Fact 1: DQ manifests — EURGBP ADMIT, AUDJPY ADMIT

| Field | EURGBP | Gate | Status | AUDJPY | Gate | Status |
|-------|--------|------|--------|--------|------|--------|
| n_rows | 31,022 | — | — | 31,037 | — | — |
| UTC range | 2021-01-03 22:00 → 2025-12-31 21:00 | — | — | 2021-01-03 22:00 → 2025-12-31 21:00 | — | — |
| bar_coverage_pct | 99.19% | ≥85% | PASS | 99.25% | ≥85% | PASS |
| measured_spread_coverage | 100.0% | ≥90% | PASS | 100.0% | ≥90% | PASS |
| max_contiguous_gap_h | 24h | ≤24h | PASS (at limit) | 24h | ≤24h | PASS (at limit) |
| spread_median_pips (pair-level) | 0.90 pips | ≤3.0 | PASS | 0.80 pips | ≤5.0 | PASS |
| spread_p90_pips (col median) | 1.0 pips | ≤8.0 | PASS | 1.0 pips | ≤15.0 | PASS |
| zero_spread_bars | 0 | — | PASS | 0 | — | PASS |
| n_missing_spread_bars | 0 | — | PASS | 0 | — | PASS |

**Max-gap explanation (both pairs):** 24h gap = 2023-12-31 22:00 UTC to 2024-01-01 21:00 UTC. This is the New Year 2024 market holiday closure — a legitimate market event, not a data defect (same pattern as NZDUSD's 73h closure in the prior cycle).

**Spread distribution note:** EURGBP spread_median_pips ranges 0.30–29.9; only 2.06% of bars exceed 5 pips; pair-level median = 0.90, well below the 3.0-pip ceiling. AUDJPY spread_median_pips ranges 0.40–33.2; only 3.06% exceed 5 pips; pair-level median = 0.80, well below the 5.0-pip ceiling. High-spread bars are illiquid-session spikes and are included in cost when they occur (EXCLUDE-NOT-IMPUTE; zero zero-spread or missing-spread bars were found in either file).

**PR independent confirmation:** PR ran coverage_gate() independently — EURGBP 99.194%/100.0%/24h/0.90, AUDJPY 99.249%/100.0%/24h/0.80 — all numbers match QD to full precision.

---

### Fact 2: rho_bar_eff recompute — five required subsets

Statistic: rho_bar_eff = (lambda_max(C) − 1) / (k − 1), eigenvalue/sign-blind per 2026-06-19 amendment. Proxy: raw 1h log-returns (no signal series pre-pre-reg). Conservative direction disclosed below. N_eff = MIN(k/lambda_max, PR, ENB) — route 1 (k/lambda_max) is the binding MIN for ALL-9.

| Subset | k | lambda_max | PC1 | rho_bar_eff | N_eff (min) | G5 gate (≤0.41) | vs prior |
|--------|---|-----------|-----|-------------|-------------|-----------------|---------|
| ALL-9 | 9 | 4.2723 | 47.5% | **0.4090** | 2.11 | **PASS (margin 0.0010)** | Δ −0.093 vs ALL-7 (0.502) |
| USD-majors-7 (excl EURGBP/AUDJPY) | 7 | 4.0138 | 57.3% | 0.5023 | 1.74 | FAIL | Δ +0.0003 vs prior ALL-7 (stable) |
| USD-majors-6 (prior ref) | 6 | 3.9853 | 66.4% | 0.5971 | 1.51 | FAIL | Δ +0.0001 vs prior USD-6 (stable) |
| CROSSES-only (EURJPY/EURGBP/AUDJPY) | 3 | 1.7127 | 57.1% | **0.3563** | 1.75 | **PASS** | — |
| (CROSSES-only included at N_eff 1.75) | — | — | — | — | — | — | — |

Eigenvalues ALL-9 (descending): [4.2723, 2.2317, 1.2869, 0.6802, 0.3700, 0.1427, 0.0061, 0.0054, 0.0046]; sum = 9.0 (valid decomposition confirmed by QD and PR independently).

N_eff routes (ALL-9): k/λ_max = 2.11 / PR = 3.18 / ENB = 3.99. MIN = 2.11 (conservative per amendment).

**Delta summary vs prior ALL-7 (0.502):** −0.093. EURGBP is the primary diversifier (USDJPY corr +0.004, GBPUSD corr −0.489 — genuinely low USD-beta). AUDJPY partially re-concentrates (EURJPY corr +0.712, AUDUSD +0.617), adding JPY and commodity factor back. Net of both crosses: 0.502 → 0.409.

**Proxy disclosure (CRITICAL):** The 0.4090 value is a raw-return eigenvalue proxy, not the true PnL-contribution gate stat (uncomputable pre-pre-reg — no signal series exists). The 2026-06-19 ruling established the proxy over-states concentration vs the true PnL-contribution stat (conservative direction: true stat ≤ proxy). However, the margin is only 0.0010 — 0.23% of the gate value — and per NHT's sampling-uncertainty analysis, the estimate sits 0.02–0.23 SD from the gate across realistic autocorrelation deflation scenarios. The proposer's own 3yr subsample gives 0.392 (Δ = 0.017 = 17× the claimed clearance), confirming the margin is within estimation noise. **Honest read: ALL-9 raw-return proxy is AT the 0.41 gate, within noise. It is not a robust cleared gate.**

**PR independent confirmation:** PR own eigen-decomposition (did not import QD's code) gives lambda_max = 4.272341, rho_bar_eff = 0.40904259, margin = +0.000957; all subset values and eigenvalue list match QD exactly.

---

### Fact 3: CD0 net-Sharpe re-screen — all 54 pair × family combos

Cost model: RT cost per trade = spread_median_pips (real per-bar) + 2×(0.25 slip + 0.15 paper haircut) = spread_median_pips + 0.80 pips. Annualization: sqrt(6150). Thresholds: PASS ≥ 1.76 / STRETCH ≥ 1.44. Pip convention: 0.0001 uniform (matching prior canonical F1-F6 spec, including JPY — see F-005 note below). EXCLUDE-NOT-IMPUTE: zero/missing spread bars excluded; zero such bars found in EURGBP or AUDJPY.

#### New crosses (EURGBP, AUDJPY)

| Pair | Family | Gross SR | Net SR | N_trades | Verdict |
|------|--------|----------|--------|----------|---------|
| EURGBP | F1 hourly-reversal | +2.2948 | −8.2122 | 16,101 | FAIL |
| EURGBP | F2 session-open-mom | +0.5721 | −4.5687 | 2,584 | FAIL |
| EURGBP | F3 intraday-mom-3 | −1.4937 | −7.4668 | 9,132 | FAIL |
| EURGBP | F4 vol-breakout | −1.0187 | −9.1281 | 9,841 | FAIL |
| EURGBP | F5 london-am-drift | −0.6701 | **−3.2006** | 2,342 | FAIL |
| EURGBP | F6 spread-filt-reversal | +1.6931 | −8.4554 | 9,632 | FAIL |
| AUDJPY | F1 hourly-reversal | −0.6208 | −5.7901 | 15,699 | FAIL |
| AUDJPY | F2 session-open-mom | +0.8123 | −2.2830 | 2,588 | FAIL |
| AUDJPY | F3 intraday-mom-3 | +0.0878 | −2.8236 | 8,716 | FAIL |
| AUDJPY | F4 vol-breakout | +0.4220 | −4.9903 | 11,712 | FAIL |
| AUDJPY | F5 london-am-drift | +0.1581 | **−1.5555** | 2,240 | FAIL |
| AUDJPY | F6 spread-filt-reversal | −0.6803 | −6.1662 | 9,336 | FAIL |

#### Prior 7 pairs (with real spreads, for reference)

| Pair | Best net SR | Best family | Verdict |
|------|-------------|-------------|---------|
| EURUSD | −1.5891 | F5 london-am-drift | FAIL |
| GBPUSD | −2.0377 | F5 london-am-drift | FAIL |
| USDJPY | −1.6109 | F5 london-am-drift | FAIL |
| AUDUSD | −1.9860 | F5 london-am-drift | FAIL |
| USDCAD | −3.5042 | F5 london-am-drift | FAIL |
| NZDUSD | −2.3636 | F5 london-am-drift | FAIL |
| EURJPY | −1.9824 | F5 london-am-drift | FAIL |
| EURGBP | −3.2006 | F5 london-am-drift | FAIL |
| AUDJPY | **−1.5555** | F5 london-am-drift | FAIL |

**ALL 54 pair × family combos FAIL net SR. Zero reach STRETCH (1.44) or PASS (1.76). The least-negative result across all 54 combos is AUDJPY F5 = −1.5555, which is 3.00 SR units below STRETCH and 3.32 below PASS.** Note: EURGBP F1 gross SR of +2.29 is the highest gross SR across all 9 pairs — a real hourly reversal signal entirely consumed by costs (net −8.21). This is the cost-dominated, price-only, high-turnover trap documented across prior cycles.

**PR independent confirmation:** PR verified EURGBP F1 (gross 2.2948/net −8.2122/16,101 trades — exact match), AUDJPY F1 (gross −0.6208/net −5.7901/15,699 — exact match), and AUDJPY F5 (gross 0.1581/net −1.5555/2,240 — exact match). A lookahead sanity check (F1 unshifted gross SR = −63.26) confirmed shift(1) is operative and no same-bar leak exists.

---

## Binding-constraint analysis: concentration-wall → no-edge-wall (strategic finding)

This is the substantive HoQR finding of the wave. **The binding constraint has moved from the concentration wall (rho_bar_eff > 0.41) to the no-edge wall (CD0 net SR < 0).**

- **Concentration wall (Gate A):** Marginally addressed. EURGBP did its job — genuinely low USD-beta (USDJPY corr +0.004) — pulling ALL-9 from 0.502 to 0.409. AUDJPY partially re-concentrated, but the net of both crosses cleared the 0.41 proxy point estimate. The cross-acquisition thesis from 2026-06-22 was directionally correct. The wall the firm spent two cycles worrying about is essentially down, at least on the raw-return proxy point estimate.

- **No-edge wall (Gate B):** Now fully exposed and dominant. With concentration removed as the excuse, the screen shows the real problem in stark relief: there is NO net-of-cost edge in any canonical intraday family on any of the 9 pairs. Gross signals exist (EURGBP F1 gross +2.29 is the all-pairs high) but are entirely consumed by spread + slippage. This is the price-only high-turnover trap. A confirmability gate over an empty edge set is vacuous — the firm has spent two cycles optimizing the denominator of a fraction whose numerator is zero.

### F1–F6 canonical family space retirement

**F1–F6 on 1h data are declared RETIRED-AS-SATURATED for net-of-cost edge.** Machine-checkable condition met: max over all pairs × {F1..F6} of net_SR < STRETCH (1.44) across two independent cycles (cycle-2: 24 combos; this cycle: 54 combos; 78 total evaluations), with the best result (−1.56) being 3.00 SR units below STRETCH and 3.32 below PASS. This is not a near-miss — it is a flat, falsified result with a wide margin.

Re-open conditions (any one sufficient):
- A NEW family spec outside F1–F6 is proposed and clears the CD0 cost-feasibility pre-screen.
- A materially lower-cost execution assumption is ratified by CRO (e.g. realized round-trip empirically below the model cost).
- Sub-1h or volume-bearing data changes the gross-edge-per-trade arithmetic.

---

## Recommendations to CEO (NOT executed this cycle — surfaced only)

These are HoQR strategic recommendations. They require CEO acknowledgment and authorization before any execution. They are NOT decisions made by this consensus.

**R1 (recommended) — Re-order the gates so CD0 cost-feasibility is the FIRST cheap test.** Stop the current pipeline of "acquire a pair → recompute rho_bar → re-run F1–F6." The binding constraint was always the cost wall, not the concentration wall. Any future hypothesis must show a gross edge that plausibly exceeds the round-trip cost hurdle BEFORE pair acquisition or rho_bar work is initiated. This is a process change, not a research change. The concentration gate should only be engaged once a cost-feasible candidate exists.

**R2 — Change the edge INPUT, not the universe.** The only lever on CD0 is per-trade-edge / turnover. F1–F6 are all price-only, fixed-spec, high-frequency constructs whose gross signal is fully consumed by spread + slippage. A cost-aware or event-conditioned family (fewer, higher-conviction fires; longer holds; gating on a gross-edge estimate exceeding cost) is the design change that could matter. A 10th pair cannot manufacture an edge that 9 pairs do not possess.

**R3 — Do NOT acquire GBPJPY.** Its sole acquisition rationale was breaking the USD concentration wall, which is now marginally addressed (ALL-9 = 0.409). AUDJPY already demonstrated that crosses can re-concentrate (EURJPY +0.712, AUDUSD +0.617). GBPJPY reuses both the GBP leg (already present via GBPUSD, EURGBP) and the JPY leg (already present via USDJPY, EURJPY, AUDJPY) — its orthogonal diversification is small. With no edge to confirm, improving the confirmability gate further is wasted ingest effort. HOLD unless R2's redesign produces a candidate whose feasibility specifically requires more cross-sectional breadth.

---

## Dissent (NHT) — verbatim, append-only

*(From `nht-null-test-report.yaml`, `dissent-statement` field. Severity: material_concern. Non-blocking on the NO-SPEND decision — NHT CONCURS with NO-SPEND. Disposition: NHT agrees with NO-SPEND and agrees the ledger correctly shows no increment; the dissent is specifically against any framing of the rho_bar_eff proxy point estimate as "wall broken" or "progress toward H1." This dissent is append-only and survives any consensus revision.)*

> DISSENT (append-only, preserved verbatim):
>
> The ALL-9 rho_bar_eff = 0.4090 "PASS" of the 0.41 G5 gate must NOT be characterized as
> the structural-concentration wall being "broken," nor as "progress toward H1." I record
> the following for the permanent record:
>
> 1. The margin (0.0010 in rho units; 0.0077 / 0.18% in lambda_max) is smaller than the
>    sampling uncertainty of the statistic by 4x–50x. Under the most generous (iid,
>    counterfactually wrong) assumption the gap is 0.23 SD; under realistic hourly-return
>    autocorrelation it is 0.02–0.09 SD. The estimate is statistically AT the gate, not below it.
>    The proposer's own robustness check (last-3yr = 0.392) moves the number by 0.017 — 17x the
>    claimed clearance — which is direct empirical confirmation that this margin is noise.
>
> 2. The statistic is a raw-return eigenvalue PROXY, not the PnL-contribution gate stat. The
>    proxy's "conservative direction" argument cannot rescue a 0.001 margin: a direction claim
>    ("true <= proxy") with no measured magnitude does not certify a sub-0.001 clearance. The
>    true stat is uncomputable here because no signal series exists (nothing cleared screening).
>
> 3. Most importantly: there is NOTHING TO BE LESS-CONCENTRATED ABOUT. The rho_bar_eff gate
>    exists to bound cross-strategy concentration AMONG CONFIRMABLE EDGES. The net-of-cost screen
>    returns ZERO edges across all 54 in-sample combos — best net −1.56, a full 3.00 SR below the
>    STRETCH bar. A diversification statistic over a portfolio of zero alphas is vacuous. Passing
>    it is not progress; it is measuring the correlation structure of noise.
>
> This is precisely the 2026-05-31 failure mode: "more data = progress" substituting for
> confirmable alpha. Two new clean pairs, a marginally-improved proxy concentration number, and
> zero net edge is NOT a step toward H1. The correct disposition is honest NO-SPEND, no counter
> increment (which the ledger correctly reflects), and NO claim that the wall is broken. I would
> NOT certify the wall "broken" on this evidence. If the firm ever wants to assert it, that
> requires (a) a real confirmable signal to populate the universe, and (b) a block-bootstrap CI
> on rho_bar_eff whose UPPER bound sits below 0.41 — not a point estimate 0.18% under it.

---

## Principal Reviewer findings (first-class section, append-only)

**PR decision: approve-with-conditions.** Zero blocking findings. All three load-bearing facts independently reproduced to full precision.

| id | severity | category | location | observation | owning-role |
|----|----------|----------|----------|-------------|-------------|
| F-001 | major | spec-drift | scripts/compute_9pairs_readiness.py:228–231, 260–261, 374–377 | Reversals (+1→−1) are charged ONE round-trip cost via a binary change-flag (`changes = pos.diff().abs() > 0`). A flip physically crosses the spread TWICE (close + open). This UNDER-counts transaction cost — anti-conservative for a FAIL screen. Verdict-safe here (3.0-SR gap to STRETCH), but this cost code must be fixed before any pre-registration reuses it. | quant-developer |
| F-002 | minor | spec-drift | scripts/compute_9pairs_readiness.py:160–167 (N_eff routes) | The 2026-06-19 amendment specifies N_eff* = MIN(N_raw/λ_max, N_raw·k/Σλ², N_raw·k/ENB) — routes scaled by N_raw (~30k). The script reports k/λ_max = 2.11 (a bets-count, not N_raw-scaled). N_eff is labeled "N_eff (min)" against a definition that would give ~6,976. A downstream consumer plugging 2.11 where ~6,976 belongs would mis-deflate by 3 orders of magnitude. Non-gate here; must be reconciled before N_eff feeds any power/validate calculation. | quant-developer |
| F-003 | minor | numerical | quant-developer-compute.yaml:133–146 (CRITICAL DISCLOSURE) | rho_bar_eff gate stat per amendment §2 is the PnL-contribution correlation; QD computes on raw log-returns as proxy (no signal series exists). QD discloses this and argues conservative direction. PR independently confirms raw-return rho=0.40904 ≤ 0.41 but did NOT re-derive the conservatism-direction claim (inherited from mathematician-rho-bar-analysis.yaml). A decision leaning on "ALL-9 clears G5" leans on a 0.001 proxy margin whose sign-direction to the true gate stat is unverified by PR. Route to HoQR for conservatism-direction sign-off. | head-of-quant-research |
| F-004 | observation | correctness | quant-developer-compute.yaml:307 (knowledge_gaps) | QD's EURJPY F2 net = −4.0 vs prior PR-verified −0.872 (cycle-1). QD disclosed this as a session-logic/cost-alignment difference and notes both FAIL. Confirms F1–F6 are not reproducible across cycles (not frozen as code); the sign/FAIL-classification is authoritative, but exact net-SR magnitudes are not. Any future use requires freezing specs as code first. | quant-developer |
| F-005 | observation | numerical | scripts/compute_9pairs_readiness.py:404–406 (pip convention) | pip=0.0001 applied uniformly to all pairs including JPY (physical pip = 0.01). Under the true JPY pip, AUDJPY F5 net goes from −1.5555 to −21.35; gross SR is unchanged (scale-invariant). All-54-FAIL verdict robust either way — true pip basis only deepens the FAIL. But JPY net-SR magnitudes are not physically meaningful and should not be carried forward as cost estimates. | quant-developer |

**PR coverage statement:** PR independently recomputed all three load-bearing facts: (a) rho_bar_eff + N_eff for all 4 required subsets plus 3yr robustness cut; (b) DQ ADMIT/EXCLUDE for EURGBP and AUDJPY via independent coverage_gate() run; (c) CD0 F1 (both new pairs) and F5 (best-case) with exact number matching plus lookahead sanity check. All match QD to full precision; zero discrepancies on any load-bearing fact.

**Two forward-looking conditions (neither blocks NO-SPEND):**
- **C-i (F-003):** HoQR sign-off that the 0.001 raw-return-proxy clearance is acceptable as G5 input. *Already satisfied in direction:* HoQR explicitly does NOT lean on the proxy for the decision (it de-rated Gate A to non-binding while Gate B has no edge to confirm). HoQR's verdict would be identical regardless of where rho_bar_eff sits relative to 0.41. Condition is satisfied as a de facto matter.
- **C-ii (F-001):** QD must fix the reversal cost under-count and reconcile the N_eff label (F-002) before this cost code or N_eff figure feeds any pre-registration. Tracked as an open item for the next wave in which a positive-net-SR candidate emerges and a pre-registration is authored.

---

## CRO risk position

**Decision: veto. size_multiplier: 0.0.**

Three independent arguments, each sufficient on its own:

1. **No positive edge to size (primary).** The net-of-cost screen is unanimously negative across all 54 canonical-family × pair combinations. Best combo is −1.56 net annualized SR — 3.00 SR units below the 1.44 STRETCH floor and 3.32 below PASS. This is an IN-SAMPLE DESCRIPTIVE UPPER BOUND, preceding any OOS deflation, trial-selection penalty, or DSR shrinkage against honest_N = 30. The best case is already a loss-making book; the realized case can only be worse. sizing_multiplier = 0.0 is the only defensible output.

2. **G5 confirmability not robustly cleared.** ALL-9 at 0.4090 clears by 0.0010 — a 0.24% margin on a statistic the brief itself flags as a conservative raw-return proxy. The 3yr window gives 0.392, confirming the point estimate oscillates across the gate depending on the window. Both USD-majors sub-universes (7 and 6) fail outright (0.5023, 0.5971). The only sub-universe with real G5 margin is crosses-only (0.3563) — but that is a 3-instrument book at N_eff 1.75, achieving the concentration gate by becoming MORE concentrated, not less.

3. **Effective-bet count ~2.1 forbids concentration-insensitive sizing.** N_eff = 2.11 means nine pairs behave as ~2 independent bets. A risk budget allocated as if this were a diversified 9-leg book would understate tail concentration by ~4.3× (9 / 2.11). A single USD or EUR-complex regime shock correlates nearly every leg — the August 2007 quant-quake / LTCM correlated-book failure mode.

**Blowup analog:** August 2007 quant-quake / LTCM correlated-book failure — a book that looks diversified across many instruments but carries a low effective-bet count (N_eff ~2) concentrates apparently-spread positions into one factor; a single USD or EUR-complex regime shock hits nearly all legs together. Sizing as if 9 independent bets would understate tail concentration by ~4.3×.

**Procedural note:** This is a descriptive screen, not a pre-registered trial. Under no_trial_increment_without_pre_registration, no counted trial may be spent and honest_N stays at 30. DQ ADMIT on EURGBP/AUDJPY is real and bankable; data quality is not the gate that fails here.

---

## Signatures

| Role | Verdict | Signed |
|------|---------|--------|
| quant-developer | implemented-and-verified | @fintech-org-qd-2026-06-24 |
| head-of-quant-research | reject (NO-SPEND / REMAIN-FROZEN; F1–F6 retired-as-saturated; R1/R2/R3 surfaced) | @fintech-org-hoqr-2026-06-24 |
| cro | veto (NO-SPEND; size_multiplier 0.0; three each-sufficient reasons) | @fintech-org-cro-2026-06-24 |
| null-hypothesis-tester | noise-indistinguishable (Claims i/ii/iii evaluated; dissent preserved) | @fintech-org-nht-2026-06-24 |
| principal-reviewer | approve-with-conditions (F-001..F-005 documented; 0 blocking; two forward conditions; all load-bearing facts reproduced) | @fintech-org-pr-2026-06-24 |
| pm | synthesis-complete (dissent preserved verbatim; PR findings first-class; no technical calls) | @fintech-org-pm-2026-06-24 |

---

## Knowledge gaps surfaced

The following are role-level research and data-measurement limitations surfaced in session artifacts. They are NOT installable skill gaps — no new skill installation or research methodology is needed to address them. They are resolved by running the relevant measurement when a qualifying candidate exists. **Installable-skill-gap count N = 0.** No new entries appended to `.fintech-org/skill-gaps.jsonl` this session.

| Gap | Source | Resolution path |
|-----|--------|----------------|
| True PnL-contribution rho_bar_eff for ALL-9 is uncomputable pre-pre-reg (no signal series cleared screening). The 0.4090 raw-return proxy clears the gate by 0.001 but the conservative-direction magnitude is unverified. | QD + HoQR + PR + NHT | Becomes computable only when a family produces net SR ≥ STRETCH on ≥1 pair, at which point a signal series exists. Moot until then. |
| F1–F6 specs not frozen as a code artifact; reconstructed from prior CONSENSUS prose; EURJPY F2 differs across cycles (QD: −4.0; prior PR-verified: −0.872). FAIL verdict robust at 3 SR-unit margin but exact net-SR magnitudes are not authoritative. | QD + PR (F-004) | Freeze as code before any pre-registration. Pre-condition for F-001 fix (C-ii). |
| Non-F1–F6 / cost-aware / event-conditioned family space on 1h data: completely untested. No hypothesis exists with sufficient gross-edge-per-trade to plausibly clear the round-trip cost. This is the R2 open question. | HoQR | Requires R2 design initiative authorized by CEO. |
| Reversal cost under-count in current cost code (F-001, major): anti-conservative for a FAIL screen, verdict-safe at 3-SR margin but must be corrected before any pre-registration. | PR (F-001) | QD fix tracked under C-ii. |

---

## Open items requiring CEO acknowledgment

**(a) Strategic pivot decision.** HoQR recommends R1 (re-order gates so CD0 feasibility is the first screen) and R2 (change the edge input — cost-aware / event-conditioned / lower-turnover family redesign — not the universe). These are the only identified paths to a positive net-SR candidate on 1h data. CEO must decide: authorize R2 redesign? Authorize R1 gate-reordering as process change? Continue current pipeline (assessed by HoQR as diminishing returns)? Continue but re-examine a different data tier?

**(b) GBPJPY hold recommendation.** HoQR explicitly recommends against GBPJPY acquisition this cycle (R3). The prior 2026-06-22 CONSENSUS recommended EURGBP > GBPJPY > AUDJPY; EURGBP and AUDJPY have now landed. GBPJPY's only rationale (break concentration wall) is moot, and it reuses existing factor legs (GBP, JPY) with limited orthogonal diversification. CEO must acknowledge the hold, or override with a specific rationale.

**(c) PR condition C-ii — QD cost-code fix.** Before any future pre-registration reuses the current CD0 cost code, QD must fix the reversal cost under-count (F-001) and reconcile the N_eff label (F-002). No action required now (nothing to pre-register). Tracked as a pre-condition for the first pre-registration in any future cycle that produces a positive-net-SR candidate.

---

## Prior decisions NOT made (carry-forward from 2026-06-22)

- **USDCHF acquisition:** still de-prioritized (dollar pair; adds SNB-unpeg tail; cannot rescue G5 and adds wrong factor).
- **Volume-conditioned families:** 1h parquets carry fully-populated non-zero volume (confirmed prior cycle); volume-conditioned CD0 screen remains out of scope. Relevant if R2 redesign includes volume conditioning.
- **H1 un-freeze:** FORBIDDEN while Gate B (CD0 net SR ≥ 1.76) fails categorically. Not deferred — actively prohibited.
- **Formal code freezing of F1–F6:** moot given F1–F6 retirement-as-saturated. Not a blocker; retire the task.

---

*This CONSENSUS.md is the audit-trail source-of-truth for the 2026-06-24 9-pairs-landed wave. Append-only per protocol. No section may be softened, reordered, or omitted in future revisions — only new sections may be appended.*

---

## § Errata — orchestrator post-ratification correction (2026-06-25, prompted by quick-critic faithfulness pass)

Three corrections to this document's framing and condition-disposition. **None change the decision (NO-SPEND / REMAIN-FROZEN holds).** Appended (not rewritten) per append-only audit discipline.

1. **"Wall essentially down" framing is qualified, not retracted.** Where the binding-constraint analysis says the USD-concentration wall is "essentially down," read it as: *the ALL-9 raw-return PROXY point estimate touched the 0.41 gate (0.4090), in the predicted direction.* It is NOT a certified clearance. NHT's preserved dissent governs the record on this point: the margin (0.001) is 0.02–0.23 SD from the gate and the 3yr subsample alone moves it 17×; the wall is NOT certified "broken." The two statements are both retained on purpose — majority directional read + skeptic's refutation — but for any downstream use, NHT's framing is the operative one.

2. **PR condition C-i is OPEN, not "satisfied."** The ratification rationale's phrase "satisfied in direction" for C-i (HoQR sign-off that the 0.001 proxy clearance is acceptable as G5 input) is **withdrawn as circular**: HoQR cannot independently sign off a condition that requires HoQR's independent sign-off, and the body does cite the proxy as "clearing the gate." Correct disposition: **C-i is MOOT for this NO-SPEND decision (the decision does not lean on the gate clearing) and remains OPEN** — it must be properly resolved (true PnL-contribution stat, or a block-bootstrap CI whose upper bound sits below 0.41) before ANY future decision that relies on the rho_bar gate clearing.

3. **F-001 reversal-cost fix is decoupled from F1–F6 retirement and tracked as actionable.** C-ii previously triggered "before the next F1–F6 pre-registration." Since F1–F6@1h is retired-as-saturated, that trigger may never fire — yet any new (R2) family reuses the SAME cost function in `scripts/compute_9pairs_readiness.py`. Corrected trigger: **the reversal-cost under-count (a +1→−1 flip charged 1 round-trip, should be 2) and the N_eff label MUST be fixed before ANY future net-of-cost screen or pre-registration reuses that cost code — regardless of family.** Tracked as OPEN-ITEM-F001 (owner: quant-developer; surfaced to Board).
