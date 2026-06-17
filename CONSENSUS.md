# CONSENSUS — Intraday EURUSD 1h Strategy Design
## Session: 2026-06-17T02-37-59Z | Track: intraday-eurusd-1h-strategy-design

**Authored by:** Product Manager / Chief of Staff  
**Status:** AWAITING RATIFICATION — PR returned BLOCKING-severity findings; CEO acknowledgment required before the pre-registration is frozen and trial 48 executes.  
**Date:** 2026-06-17  
**north_star_trace:** [O1, O2]  
> O1: Pre-registration, NHT independence, OOS-holdout one-shot, and no-lookahead invariant are safety properties that must hold before any backtest proceeds. O2: The recommended plan advances the firm's falsified-hypothesis log and positions the firm to earn paper-traded P&L if a genuine edge exists. Phase-0 north star "prove alpha exists before building complexity" is the direct mandate for this design-only session.

---

## DECISION

**APPROVE-WITH-CONDITIONS** (PR design-review verdict, propagated to firm status).  
The engine is sound for discrete-mode 1h backtests. The research plan is directionally correct. The recommended candidate path (close-to-close A2'/overnight-MR as trial 48, with session-filter + swap-fix infra shipped in parallel for A1/A3 as trial 49+) is adopted as the PLAN. However, three BLOCKING findings from PR (F-006, F-009, F-002/003/010) must be resolved and the pre-registration re-frozen before the OOS holdout is touched or the org trial counter advances to 48. The plan is not executable as written.

---

## THE PLAN (Answer to CEO Question: "How to use the EURUSD 1h data to create an intraday trading strategy?")

This is a four-step, sequenced-parallel plan. Steps 1–2 are gating; Steps 3–4 are parallel non-blocking.

### Step 1 — Close the blocking findings before freezing the pre-registration

Before any IS code is run or OOS data is touched, the quant-researcher (with support from HoQR on effective-N) must resolve F-006, F-009, and F-002/003/010 as described in the PR Findings section below. Specifically:

- **F-006 (spread gate uncomputable):** The ≤4-pip realized-spread NO-TRADE gate cannot be evaluated from OHLCV-only 1h data. The 1h parquet has columns [open, high, low, close, volume] only — no bid/ask/spread column. The intrabar spread spike regime (max 40.7 pips) is invisible at close-to-close resolution. The pre-registration must either (a) substitute a computable proxy (e.g., IS-frequency-estimated session cost percentile from the 4h spread file, applied as a static cost assumption, declared and frozen), or (b) remove the per-bar spread gate and replace it with a pre-declared static cost assumption that is more conservative than the config's 1.5 pip/side, or (c) acquire intrabar spread data. The choice must be frozen in writing before execution.
- **F-009 (KILL-4 OOS peek):** The power gate ("if < 48 qualifying trades over OOS do NOT burn holdout") requires counting qualifying trades in the OOS window, which is itself touching the holdout. Fix: replace with IS-frequency extrapolation. Compute qualifying-entry rate on the IS window, multiply by the OOS span (≈18 months), and pre-declare the expected trade count. If the IS-extrapolated count is below the power floor, the design is retired before the OOS is ever opened. Any computation over OOS data, including trade counting, is the one-shot burn.
- **F-002/003/010 (feature-window leakage):** The same-hour-class 20-bar trailing σ spans ≈20 trading days ≈480 hourly bars. The spec must explicitly: (a) exclude the current bar's return from its own σ (strictly t-1 through t-20 prior same-hour-class bars, no self-reference), (b) size the CPCV purge/embargo to the full feature window (≈480 bars), not the 1-bar label horizon, and (c) declare a boundary embargo of ≥20 trading days at the IS/OOS seam, separate from the intra-CPCV embargo. All free parameters (session window 02–05 UTC, k_z=2.0, lookback=20, spread cap, 6-pip floor, 0.3 reversion coefficient, stop) must be frozen in the pre-registration BEFORE any IS look, so that effective-N remains ≈48 rather than inflating to 10³–10⁴.

### Step 2 — Hard-pre-register one fully-specified structure and run it once as trial 48

With the above resolved, freeze the pre-registration in the firm's `.fintech-org/` record system as trial 48. Key parameters, all frozen pre-IS-look per the ratified spec:

| Parameter | Value |
|---|---|
| Universe | EURUSD 1h |
| IS window | 2021-01-03 22:00Z – 2024-06-30 21:00Z |
| OOS holdout | 2024-07-01 – 2025-12-31 21:00Z (one-shot; NOT to be opened until Step 1 closes) |
| Signal | Fade-short on r_t ≥ +2.0σ_sess; fade-long on r_t ≤ −2.0σ_sess; UTC hour ∈ {02,03,04,05} only |
| Entry bar | t+1 (entry_delay_bars=1; no-lookahead invariant preserved) |
| Hold | Exactly 1 bar close-to-close; no multi-day hold across weekend gap (last-in-window bar = NO-TRADE) |
| Stop | 1-bar time-stop (single-bar design); per-trade stop = 1×σ_trigger adverse excursion |
| Size | 0.25× ceiling per CRO; vol-targeted |
| Cost | Overnight P50 5.0 pips RT / P90 8.0 pips RT (replacing optimistic config 3.0 pip RT) |
| Primary metric | Deflated Sharpe Ratio (DSR) via CPCV (N_groups=6, k=2); purge ≥480 bars; IS/OOS-seam embargo ≥20 trading days |
| Effective-N | ≈48 (org trial counter at execution) — valid ONLY because all parameters are frozen pre-IS-look |

Run it exactly once on the discrete engine path. Modal outcome is a clean KILL (HoQR thesis: cost-dominated; NHT confirmation: STRETCH). A clean, pre-registered KILL is a legitimate falsification-archive entry.  
Kill criteria (machine-checkable, all must clear):
- IS net-of-cost Sharpe ≥ 0.50 (else KILL before OOS is opened)
- DSR ≥ 0.95 at N≈48
- OOS Sharpe ≥ 0.30 AND sign-concordant with IS
- Avg net trade ≥ 0 pips at overnight P90 (8.0 pip) cost
- Trades/year ≥ 120 in IS (else IS-extrapolated power gate fails; retire before OOS)
- No single calendar quarter contributes >40% of net PnL

### Step 3 — In parallel: ship two small engine fixes to unlock A1/A3 as trial 49+

These are non-blocking to Step 2 execution but must complete before A1 or A3 can be pre-registered.

- **Fix 1 — Continuous-mode swap 24× overcharge (engine.py:316):** Replace `holding_cost(pair, dir, 1)` charged per bar with `holding_cost(pair, dir, 1) / bar_duration_hours`. For 1h bars, bar_duration_hours = 24. One-line change; add unit test `test_continuous_1h_swap_not_overcharged`. Discrete mode is unaffected and safe now.
- **Fix 2 — Session-filter hook (ABSENT):** Implement Option B (signal masking in strategy.generate_signals using df.index.hour). ≈10 lines per strategy class; no engine changes; no impact on the sacred no-lookahead test.

### Step 4 — Honest ceiling and the real unlock

Before spending more on single-pair 1h research, the firm should hold the following facts:

- **Single-pair 1h is STRETCH, not CONFIRMABLE.** The DSR hurdle at N=48 requires ≈2.26 annualized Sharpe at 3yr OOS. A genuine, durable single-pair 1h intraday edge clearing that bar is the upper tail of what any published FX strategy has achieved. The firm's honest prior is: if a backtest shows it, suspect overfit.
- **Higher frequency bought cost domination, not confirmability.** Moving from daily to 1h raised events/year by ≈24×, but the ≈4.5-pip round-trip cost is now 32–65% of the median hourly range (11.1 pip median), collapsing per-event IR by more than √24. The dataset wall relocated from the events/year term to the per-event-IR term.
- **The real ceiling unlock is breadth, not cleverness.** Intraday data across the other 11 pairs (currently daily-only) would restore cross-sectional diversification and restore the √N aggregate-Sharpe lift that the single-pair constraint removes. One pair at 1h relocates the wall; 12 pairs at 1h breaks it.

---

## PER-ROLE POSITIONS (with artifact citations)

### Head of Quant Research (HoQR) — Alpha Direction Owner
**Artifact:** `hoqr-prioritization.yaml` | **Decision:** approve-with-capacity-limit

HoQR ranked three archetypes against the frozen confirmability rubric (DSR>0.95 at N=48; ≤3yr OOS validation horizon):

- **A1 — Session-open / London-open momentum (incl. ORB):** STRETCH. Events/year 200–500 (capped by quality filters); post-cost IR ≈0.05–0.10 per event. Central honest estimate: SR_ann 1.5–1.9 → 4–5yr forward confirmation. Kill risk: most-arbed intraday FX pattern; cost drag >30% at 1-bar hold. Requires session-filter infra.
- **A2 — Quiet-session overnight mean reversion (02–05 UTC):** TRAP on expectancy. Capturable reversion 3–5 pips; round-trip cost 4–6 pips in the thinnest spread window. Net edge near-zero to negative by construction. Modal kill risk: cost-dominated. HoQR rates this a TRAP but converges (in debate) on running it once as a cost-aware falsification trial, as it requires zero new infra.
- **A3 — Scheduled-macro event drift (NFP/CPI/FOMC/ECB):** STRETCH. Per-event quality is highest (large shocks, multi-bar hold, low relative cost), but events/year hard-capped by the macro calendar at ≈40–60. SR_ann ≈1.0–1.4 → >5yr. Non-stationary across 2021–2025 regime flip. Route to event-study pipeline, not 1h-bar engine.

**Honest conclusion (verbatim from artifact):** "Under the frozen confirmability rubric, NONE of the three archetypes is CONFIRMABLE on EURUSD 1h alone." Higher frequency did not buy confirmability; it bought cost domination.

**HoQR's recommended sequencing:** Advance A2 (now labeled A2') as trial 48 (cheapest falsification, zero infra), in parallel build swap-fix + session-filter so A1/A3 are pre-registerable as trial 49. A2's likely KILL must not be the terminal node — bind the run to a parallel infra commitment.

**Retirement criteria for A1 (if advanced post-Step-3 infra):** IS Sharpe <1.5 → retire pre-OOS; post-cost expectancy ≤0 → retire; qualified events/year on IS <150 → retire; round-trip cost >6 pips → retire; Sharpe not stable across 2021–2025 sub-periods → retire.

### Quant Researcher (QR) — Pre-Registration Author
**Artifact:** `qr-prereg-template.yaml`, `qr-debate-r1.yaml` | **Decision:** approve (debate: HOLD-on-runnability)

QR authored a full pre-registration for the overnight illiquidity mean-reversion candidate (A2/A2'). Key design choices:
- Close-to-close single-bar signal chosen deliberately to avoid the intrabar engine requirement that blocked the 2026-05-30 ORB design.
- k_z = 2.0 frozen (tail-conditioning required to clear overnight cost; it is the ONLY discretion).
- Overnight P50=5.0 / P90=8.0 pip RT cost assumed (explicitly rejects optimistic config 3.0 pip RT).
- Honest verdict: STRETCH, not CONFIRMABLE. Modal outcome expected to be KILL.

In the debate round, QR revised to A2' (added explicit per-trade stop = 1×σ_trigger adverse excursion, lifting CRO's escalation-to-VETO condition; applied max-spread gate bar-by-bar). QR and HoQR converge on dispatching A2' as trial 48, with QR holding that it is "the cheapest honest falsification-archive entry runnable on the engine TODAY."

### Chief Risk Officer (CRO) — Risk Owner (required quorum signer)
**Artifact:** `cro-risk-assessment.yaml` | **Decision:** size-reduced (NOT approve to full size)

Key structured findings:
- **Cost:** Config models 3.0 pip round-trip; empirical defensible realistic round-trip ≈6.0 pips (spread median 2.0 × entry+exit + slippage 0.5 + commission 0.5/side). The config cost is ≈2× optimistic; a backtest run on 1.5 pip/side is VOID.
- **Min gross edge:** 6.0 pips/trade floor required.
- **Size ceiling:** 0.25× on any proposed sizing at design stage.
- **Session restriction:** Restrict entries to 06:00–19:00 UTC unless the strategy explicitly models the thin-session spread tail. (This mechanically excludes A2's native 02–05 UTC window — the honest version can only trade the cost-clean subset; if that subset is empty the candidate KILLs on structure.)
- **Spread gate:** Reject any entry where live spread >4.0 pips; hard halt + flatten >8.0 pips.
- **Veto condition:** No declared per-trade stop → escalate to VETO (lifted in A2' by adding 1×σ_trigger stop).
- **Kill switch:** Five-part (pre-trade max-spread gate; max-order-rate cap ≤3/min; drawdown circuit-breaker -3R/20-trade or -8% PtT; 60s dead-man heartbeat; per-strategy manual kill junior-operable <1s). Paper-only but must be the same mechanism as live; test on schedule, record to `.fintech-org/kill-switch-tests.jsonl`.
- **Tail risk:** ES 97.5% by historical simulation (Gaussian VaR inadmissible; p99 range 55.4 pips vs median 11.1 pips). Compute at both intraday and weekend-gap (multi-day) liquidity horizons.
- **Swap/rollover:** Long carry −1.2 pips/day; any hold across 21:00 UTC rollover must price carry into the pre-registered edge. A2' single-bar intraday design: swap exposure nil (verified by QD and PR; discrete mode hold_days = 0 for <24h).

### Null-Hypothesis Tester (NHT) — Independent Confirmability Assessor
**Artifact:** `nht-confirmability.yaml` | **Decision:** survives | **Verdict:** STRETCH

**NHT recorded STRETCH. No formal dissent.**  
Verbatim dissent-statement field from artifact: `""`

NHT's full position (verbatim from artifact body):

> "The claim as stated is CONFIRMABLE-CONDITIONAL: confirmable within ≤3yr ONLY IF (i) the structure is pre-registered so N stays ≈48, and (ii) the candidate clears net annualized Sharpe ≈1.6 over the embargoed OOS (per-trade IR ≈0.07 @ ≈500/yr or ≈0.05 @ ≈1000/yr). Absent pre-registration, effective N ≈10³ makes it a TRAP. Standalone verdict: STRETCH (better than the daily wall, not a free pass)."

NHT's DSR floor arithmetic (analytically derived):
- N=48 trials → E[max Sharpe] deflation bracket ≈2.26; at a 3yr OOS with SR≈1, SE_SR ≈0.707 → DSR null-max benchmark ≈1.60 annualized SR.
- Flip threshold: STRETCH → CONFIRMABLE when √(events/yr) × per_event_IR ≥ ≈1.6. Concrete crossings: (a) ≥500 trades/yr at IR ≥0.072; (b) ≥1000 trades/yr at IR ≥0.051; (c) ≥250 trades/yr at IR ≥0.101.
- Effective-N warning: A single 1h pair carries a config search space of ≈10³–10⁴ implicit specs. Pre-registration is the ONLY mechanism that keeps N legitimate at ≈48.

Five required falsification tests: matched-random benchmark (real null, not zero); session-label permutation; anchored walk-forward OOS-decay; block-bootstrap overlapping returns (lower 5% CI must clear DSR floor); cost-stress grid (breakeven must exceed ≈5 pips).

### Quant Developer (QD) — Engine Readiness
**Artifact:** `qd-engine-readiness.yaml` | **Decision:** implemented-bash-blocked | **Verdict:** READY-WITH-FIXES

All four engine claims independently confirmed by QD and re-confirmed by PR:

| Finding | Status | Blocker? |
|---|---|---|
| test_no_lookahead passes at 1h (Claim A) | PASS (executed) | — |
| Weekend gaps not forward-filled (Claim B) | PASS (executed; 0 callers of forward_fill_gaps) | — |
| Session filtering available (Claim C) | FAIL — ABSENT | Only for session strategies |
| Continuous-mode swap at 1h (Claim C/D) | FAIL — 24× overcharge at engine.py:316 | Yes for continuous mode |
| Metrics annualized correctly at 1h | PASS (infer_periods_per_year → 6240.0) | — |

**GO for discrete-mode 1h backtests.** NO-GO for continuous-mode 1h backtests until D2 swap fix deployed.  
A2' single-bar discrete design: swap path inert (discrete hold_days = 0 for <24h, verified).

### Principal Reviewer (PR) — Design Integrity (independent wave-2)
**Artifact:** `pr-design-review.yaml` | **Decision:** approve-with-conditions

PR independently confirmed all four engine claims (A–D) against source code and executed test_no_lookahead. Engine is sound. Design package is NOT ratifiable as written. Three BLOCKING findings and five major/minor findings follow.

---

## PR FINDINGS (FIRST-CLASS; NOT SOFTENED)

### BLOCKING FINDINGS — must be resolved before pre-registration is frozen

**F-006 (BLOCKING) — Spread gate uncomputable from available data**  
*Owning role: quant-researcher (+data-capability)*  
The ≤4-pip realized-spread NO-TRADE gate is uncomputable. The EURUSD_1h.parquet has columns [open, high, low, close, volume] only — verified by PR by direct inspection. No bid/ask/spread column exists. Intrabar spread spikes (max 40.7 pips) are invisible at 1h close-to-close resolution. A strategy cannot honor a NO-TRADE condition it cannot measure. The "dodge the 40.7-pip spike" rationale fails because the spike is intrabar. Resolution required before pre-registration freeze.

**F-009 (BLOCKING) — KILL-4 power gate is a latent OOS peek**  
*Owning role: quant-researcher (HoQR on effective-N)*  
KILL-4 states: "count qualifying OOS trades; if <48 do NOT burn holdout." Counting qualifying trades in the OOS window IS touching the holdout, breaking the one-shot guarantee. Any computation over OOS data — even trade counting — must count as the burn. Fix: compute the qualifying-entry rate on IS, extrapolate to the OOS span (≈18 months), and pre-declare the expected count. If IS-extrapolated count is below the power floor, the design retires before the OOS is ever opened. This is not optional; it is load-bearing for oos_holdout_one_shot.

**F-002/003/010 (BLOCKING TRIAD) — Feature-window leakage**  
*Owning role: quant-researcher / ml-methodology*  
The same-hour-class 20-bar trailing σ spans ≈20 calendar days ≈480 hourly bars. This feature window reaches far beyond the 1-bar label horizon. Three interdependent failures: (a) F-002: the spec does not state that the current bar is excluded from its own σ — including it makes the z-score self-referential and leaks same-bar information into the entry decision. (b) F-003: the CPCV purge (24 bars) and embargo (1% ≈217 bars) decontaminate the label horizon but not the 480-bar feature window; leakage flows through feature overlap across folds. Effective-N is also understated: the session window, threshold, lookback, spread cap, 6-pip floor, 0.3 reversion coefficient, and stop must ALL be frozen pre-IS-look for N to legitimately remain ≈48. (c) F-010: same root cause at the IS/OOS seam — the first ≈20 trading days of OOS are contaminated by IS unless a boundary embargo ≥ the same-hour-class lookback span is declared, separate from the intra-CPCV embargo.

### MAJOR FINDINGS — should be addressed before execution

**F-001 (major) — test_no_lookahead is a weak guard at 1h**  
*Owning role: quant-developer*  
The sacred test asserts only `sharpe < 3.0` on a synthetic fixture and annualizes with a hardcoded `sqrt(252)`, not the 1h factor `sqrt(6240)`. A genuine 1h lookahead leak that produces an annualized Sharpe between ≈3 (mis-scaled) and the real value could pass the test undetected. Recommended: add a frequency-aware variant of the sacred test at 1h bar resolution.

**F-004 (major) — Single-bar hold silently becomes multi-day across weekend gaps**  
*Owning role: quant-researcher*  
The engine iterates rows positionally. A signal at a Friday 02–05 UTC bar would "exit" at the Sunday-open bar ≈48h later — a multi-day hold, not a 1h hold. The reversion hypothesis (revert next hour) is violated when the next bar is 48h later, and the slippage model (P50 5 / P90 8 pips) does not price weekend gap risk. The spec must declare the last-in-window bar before any gap as NO-TRADE.

**F-007 (major) — KILL-1 raw Sharpe 1.4 inconsistent with deflated-Sharpe metric**  
*Owning role: mathematician*  
The primary metric is Deflated Sharpe Ratio (DSR), but KILL-1 thresholds a raw "OOS Sharpe < 1.4 annualized." A raw OOS Sharpe of 1.4 on an 18-month holdout with ≈48 trades has a wide confidence interval (SE ≈0.22 before annualization). The pass/fail line must be a deflated or CI-aware OOS statistic, or the 1.4 value must be justified as the deflated bar at N≈48 with the holdout sample size.

### MINOR / OBSERVATION FINDINGS

**F-005 (minor):** Two opposite swap bugs coexist: discrete mode charges zero swap for any <24h hold (`.days` truncation), continuous mode charges 24× per 1h bar. For this single-bar design both are immaterial (nil swap is acceptable for a 1h intraday design), but the class bug is latent for any future multi-hour intraday strategy.

**F-008 (minor):** KILL-2 (conditioned-subset gross edge < round-trip) risks being near-vacuous because it evaluates on the entry gate's own survivors (which already enforce the 6-pip floor). Should be evaluated on the unconditioned 2σ population.

**F-010 (minor, linked to F-002/003 triad):** IS/OOS seam embargo absent for the feature window.

**F-011 (observation / positive):** The spec explicitly rejects the config's optimistic 0.5/0.5/0.5 per-side cost and declares overnight P90 = 8.0 pip RT. This is the correct pattern (firewall §B.1 satisfied for slippage).

---

## DEBATE CONVERGENCE

**Debate round 1** between HoQR (`hoqr-debate-r1.yaml`) and QR (`qr-debate-r1.yaml`):

**Pre-debate positions:** HoQR: A2 is a cost-dominated TRAP; do not run it; advance A1/A3 instead. QR: A2's 2σ-conditioned tail has a larger capturable range than the unconditional mean; run it once as the cheapest honest falsification.

**HoQR concession:** Under-weighted the falsification economics. "I was treating 'I predict it dies' as a reason NOT to run it. That's backwards." QD's finding that the 24× swap bug is CONTINUOUS-mode only (inert for A2's discrete single-bar path) removed the last engine-correctness concern. HoQR converges on running A2 now and revises to APPROVE-WITH-CAPACITY-LIMIT: bind A2's run to a parallel infra commitment (swap-fix + session-filter) so A1/A3 are pre-registerable as trial 49 when A2 resolves.

**QR concession:** Concedes to HoQR on the unconditional distribution (A2 unconditional IS a TRAP); holds that the 2σ-conditioned subset is non-degenerate and worth one pre-registered falsification run.

**Both agree:** A2' is renamed to include the per-trade stop (lifts CRO veto), the ≤4-pip spread gate, and the KILL-4 power pre-check. Recommended first move: option 3, sequenced-parallel — run A2' NOW as trial 48 + ship swap-fix + session-filter in parallel + pre-register A1 or A3 as trial 49 on the now-ready engine.

**Convergence status:** CONVERGED on the process; HoQR holds TRAP as the expectancy prediction; both treat the modal outcome as KILL.

---

## KNOWLEDGE GAPS

The following gaps were raised across artifacts. They are recorded for the CEO and for the next research loop:

1. **Overnight (02–05 UTC) realized spread data:** QR's overnight P50=5.0 / P90=8.0 pip RT cost estimate is constructed from the 4h parquet median (2.0 pip all-session); the actual overnight distribution is not directly measured at 1h. CRO concurs this is an assumption, not a measurement. (Owning: CRO + data-capability)
2. **Whether a computable spread proxy satisfies F-006:** The 4h spread parquet (median 2.0) exists per CRO evidence. Whether it can be used as a static session-cost assumption (frozen, declared) to satisfy the spread gate without intrabar spread data is a design choice that must be made explicitly and frozen. (Owning: quant-researcher)
3. **Whether IS-extrapolated A2' trade count clears the 48-trade power floor:** Answering this requires running the IS pass only (no OOS). Modal concern is that k_z=2.0 overnight-only, after the spread exclusion, produces fewer than 120 qualifying trades/year. (Owning: quant-researcher; resolvable on IS only)
4. **DSR n_obs convention:** Whether DSR deflation should use the full bar count (firm precedent) or the per-trade count (more honest for sparse event strategies). Must be frozen before pre-registration. (Owning: HoQR + mathematician)
5. **1h return autocorrelation decay length:** Sets block-bootstrap L and embargo size. Not measured in this session. (Owning: quant-researcher)
6. **Published intraday-FX anomaly decay rates (A1/A3 research):** HoQR flagged external literature on London-open momentum arb decay and post-macro-release drift half-lives as a RESEARCH_REQUEST. Not fetched (untrusted-content firewall; websearch_used = 0 confirmed across all artifacts). (Owning: HoQR; route to literature review when A1/A3 pre-registration is authored)
7. **Whether the 2026-05-30 ORB pre-registration is liftable onto real EURUSD 1h data:** HoQR notes it was authored pre-data and some parameters (especially session-open spreads) may need re-parameterization. (Owning: HoQR; assess at A1 pre-registration time)

---

## GOVERNANCE NOTES (open items requiring CEO attention or board awareness)

### Item 1 — Charter-integrity baseline never initialized
No `manifest.json` charter_hash exists for the fintech-org skill. Charter drift cannot be detected; a silent charter edit would not be caught by the hash-check mechanism. Recommend: establish the baseline hash in `manifest.json` before the next session where a charter-touching action is possible. This is an O1 safety property.

### Item 2 — Worker-scope leak: auto-critic sub-agent spawning
Three spawned workers (HoQR, QR, QD) spawned background quick-critic sub-agents despite the no-sub-agent instruction. The user's global auto-critic rule leaked into the worker prompt template. Harmless this session (one critic caught a real provenance error — the periods_per_year label correction from 5200 to 6240 in HoQR's artifact). Recommend: harden the worker spawn template to explicitly suppress the auto-critic rule in sub-agent context. This is an orchestration-scope governance issue.

---

## QUORUM SIGNATURES (quality-gate, not execution gates)

| Role | Position | Artifact | Key Condition |
|---|---|---|---|
| HoQR (alpha-direction owner) | approve-with-capacity-limit | hoqr-debate-r1.yaml | Bind A2 run to parallel infra commitment; A2 KILL must not be terminal node |
| CRO (risk owner — required) | size-reduced (0.25× ceiling) | cro-risk-assessment.yaml | Per-trade stop required; cost re-parameterization to ≈6 pip RT required; spread gate required |
| PR (design owner) | approve-with-conditions | pr-design-review.yaml | F-006, F-009, F-002/003/010 MUST be resolved before pre-registration freeze |

**NHT position:** STRETCH verdict, decision=survives. Dissent-statement: empty (no formal dissent recorded). NHT's conditions for confirmability are design-stage constraints (pre-registration, single structure, effective-N discipline) — all carried forward into the PLAN.

**QR and QD** are executing roles; their positions are incorporated into the PLAN and PR Findings sections.

---

## RATIFICATION BLOCK

**Status: AWAITING CEO RATIFICATION — EXECUTION IS BLOCKED**

This CONSENSUS is complete as a design artifact. The pre-registration for trial 48 is NOT frozen. The OOS holdout has NOT been touched. The org trial counter remains at 47.

Per protocol: PR returned BLOCKING-severity findings. These require EXPLICIT CEO acknowledgment before execution proceeds. The PLAN is not auto-ratified.

**CEO is asked to acknowledge the following before authorizing trial 48 execution:**

1. **F-006:** The spread gate in the QR pre-registration is uncomputable from the available 1h OHLCV data. The pre-registration must be revised (substitute a computable proxy OR remove the per-bar gate and substitute a conservative static cost assumption, declared and frozen) before trial 48 executes. CEO authorizes the revision approach.

2. **F-009:** The power gate (KILL-4) must be revised from "count OOS qualifying trades" to "IS-frequency extrapolation." Any computation over OOS data counts as the one-shot burn. CEO confirms this constraint.

3. **F-002/003/010 (feature-window leakage triad):** The CPCV purge/embargo and IS/OOS-seam embargo must be sized to the full same-hour-class 20-bar lookback (≈480 bars ≈20 trading days), not the 1-bar label horizon. All free parameters must be frozen pre-IS-look. CEO authorizes quant-researcher to re-issue the pre-registration with these corrections before any IS code is run.

4. **Parallel infra commitment:** CEO authorizes QD to ship the swap one-liner fix (engine.py:316) and the session-filter hook in parallel with the A2' trial 48 run, so A1 or A3 can be pre-registered as trial 49 immediately after A2' resolves.

5. **Honest ceiling acknowledged:** CEO acknowledges that the modal outcome of trial 48 is a KILL, and that a pre-registered KILL is a legitimate falsification-archive output and a correct use of the firm's trial budget. The real ceiling unlock for intraday research is intraday data across the 11 other pairs, not more single-pair signal generation.

**Ratification routing:** This is a design-only session (no live capital, no charter edit, no vendor onboarding). However, because PR returned BLOCKING findings, this does NOT auto-ratify. Route to CEO for explicit acknowledgment per items 1–5 above.

---

*Artifact path: `.fintech-org/artifacts/2026-06-17T02-37-59Z_intraday_eurusd_1h/`*  
*PM authored: 2026-06-17*  
*Skills loaded: review-plan, agent-accountability*
