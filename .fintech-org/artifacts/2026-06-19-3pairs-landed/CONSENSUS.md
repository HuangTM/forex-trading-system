# CONSENSUS — 3 of 12 Intraday Pairs Landed: Act Now or Wait?

**Date:** 2026-06-19
**Trigger (Board):** "3 1-hour pairs backfill finished — can you do something about it? If you wait for all backfill, I'm afraid you may not get more signals to act on."
**Cycle type:** Strategic fork + scope (no backtest run, no trial spent this cycle).
**Roles signed:** PM, CEO, Head of Quant Research, CRO, Null-Hypothesis Tester.
**Ratification:** Autonomous quorum (CEO + HoQR + CRO; CRO required-on-risk ✓; NHT dissent preserved verbatim ✓). No forbidden-interim domain (research design only, no live capital / no charter / no vendor).

---

## DECISION

**CONDITIONAL START — YES, act now, but only on the zero-budget / per-pair track.**

Three things, in order:

1. **DO immediately (zero statistical-budget cost):** the legitimate, value-additive work that makes every future trial better and that *cannot* be done later for free. Two items already completed this session (see "Done today").
2. **DO NOT run the frozen 8-pair marquee study** `h1_session_open_momentum_pooled` on the 3-pair subset. It was deliberately frozen for **8 pooled majors** and its confirmability banks on that breadth (≥350 pooled events/yr). Running it on 3 majors would either fail its own gate honestly or tempt gate-weakening — both bad. Keep it **FROZEN-AWAITING-DATA** until ~6–8 majors land.
3. **DO NOT spend a trial-counter increment on the 3-major subset** until a *new, narrower, per-pair* pre-registration clears the confirmability rubric on **within-pair frequency alone** (not borrowed cross-pair breadth). That is the only path by which a 3-pair trial is honest.

**This directly answers the Board:** there is real work to do now and you will not idle — but "act now" does **not** mean "run the headline study on a subset." The marquee study is blocked on breadth, by its own pre-registered design.

---

## WHY (the decisive facts)

- **The 3 pairs are research-grade.** EUR/USD, GBP/USD, USD/JPY: 5.0 yrs each (~31k 1h bars), volume + spread columns, passed full DQ gate (monotonic UTC, no dup/null, OHLC-consistent, no zero-vol/neg-spread, 98.9% exact-1h spacing). This is the firm's first intraday + volume + spread data — the named "DATASET WALL" unlock.
- **But the wall breaks on the *within-pair* axis, not the *breadth* axis.** Intraday gives ~6,150 bars/yr/pair (24× daily). Within-pair power is now plausible. **Cross-pair breadth is not:** PC1 = 69.8% of variance (dominant USD factor); corr(EUR,GBP)=+0.75; USD/JPY = −0.45. Three majors ≈ **~1.3 effective bets**, not 3.
- **The marquee study needs the breadth that hasn't landed.** `h1_session_open_momentum_pooled` (trial `5fff4c63`, FROZEN, counter not burned) requires 8-pair pooling to reach ≥350 events/yr. With 3 pairs it cannot clear `h1-PASS-events`.
- **This is "continue/scale," not "cold start."** Intraday EURUSD already has a clean, honest result: trial-48 (`A2-prime-overnight-MR-EURUSD-1h`) ran IS-only and was **cleanly falsified as cost-dominated** (gross +3.41 pips/trade, below the ~7.5-pip cost floor). The harness and discipline are proven on 1h data; the cost-dominance warning is empirically real.
- **Correct denominator:** honest-N = **30** (latest ratified `honest-n-classification`, 2026-06-18) — not the 50 raw trials.jsonl lines, nor the stale "48" label. The statistical budget is finite and every increment is permanent and org-wide.

---

## DONE TODAY (zero-budget, already executed)

- ✅ Full data-quality gate on all 3 landed pairs — **PASS** (clean, research-grade).
- ✅ Factor-structure characterization — PCA on 1h returns: PC1=69.8%, full correlation matrix. (This *is* the firm's own AC-3 / open-question-2; now answered with numbers.)

---

## IMMEDIATE NEXT ACTIONS (prioritized, all zero-budget until a slot is granted)

| # | Action | Owner role | Burns trial? |
|---|--------|-----------|--------------|
| CD1 | **Freeze the within-pair events/yr deflation method** (block-bootstrap or Newey-West effective-N keyed to actual holding period). The frozen rubric rigorously deflates *cross-pair* corr (G5) but leaves *within-pair* overlap-deflation **unspecified** — must be frozen pre-result. | Mathematician → Quant Developer | No |
| CD2 | **Resolve the rho gate for k=3:** either re-derive the 0.41 break-even under the new eigenvalue ρ̄_eff statistic (firm self-disclosed this is an open gap), **or** restrict the 3-pair study to **per-pair (non-pooled) inference** so the rho gate is not load-bearing. Per-pair is the cleaner route at k=3. | HoQR + Mathematician | No |
| CD3 | **Dukascopy→Saxo spread reconciliation** + bake a **+0.3 pip/RT provenance haircut** into the intraday cost model; require any edge to survive it. Retires the vendor-artifact trap before it can contaminate a result. | CRO + Quant Developer | No |
| CD4 | **Re-validate the no-lookahead guarantee for intraday semantics** (hour-of-day, session boundary, rollover bar, bar's-own-close). The sacred `test_no_lookahead` covers the daily shift, not session boundaries. Gate: passes on 1h or no signals run. | Quant Developer | No |
| CD5 | **Author a NEW per-pair 3-major intraday pre-reg** (not a mutation of the frozen 8-pair H1) once CD1–CD4 land; counter burns only when a slot is granted and it PASSES (not STRETCH) the rubric on within-pair power. → triggers a **Principal-Reviewer review wave** before any code. | HoQR / Quant Researcher | Only at slot grant |
| — | **Keep `h1_session_open_momentum_pooled` FROZEN-AWAITING-DATA.** Add a held-out pair reservation for when breadth lands. | HoQR | No |

---

## HARD CONDITIONS (non-negotiable, from CEO + CRO)

1. **No trial-counter increment on the 3-major subset** until a new per-pair pre-reg PASSES the rubric on within-pair power. (CEO C1/C4, CRO C2, NHT bright line.)
2. **Pre-registration before any backtest** — safety floor, no exception.
3. **USD-factor neutrality:** any candidate edge must report performance after projecting out PC1 (use G5's PnL-contribution haircut, not a sign-flip proxy). An edge that is just levered PC1 is rejected at design.
4. **Saxo cost-haircut mandatory** (CD3) before any edge is taken seriously.
5. **Universe freeze:** pairs 4–12 landing mid-study may **not** be added to an in-flight study — they seed a new pre-registration.
6. **Confirmability ≲2yr bar unchanged;** STRETCH stays no-spend.

---

## NULL-HYPOTHESIS TESTER DISSENT (verbatim, append-only — cannot be erased)

> I dissent against starting **trial-spending** intraday research on the 3-pair subset now. The null — that a 3-pair start produces no confirmable alpha that waiting wouldn't, while spending irreplaceable budget and inviting a USD-factor artifact — has NOT been rejected, and on the facts it is structurally likely TRUE: with PC1=69.8% and the mandated eigenvalue haircut, three USD majors are ~1.3 effective bets and a USD-factor signal almost certainly breaches the frozen ρ̄_eff ≤ 0.41 gate at k=3, failing G5 by construction. "Three pairs finished, let's go" is the firm's own documented kill-criterion — infra-excitement substituting for a confirmable hypothesis — wearing the new coat of intraday paint. Board urgency ("idling = no signals") is not evidence; the firm's disciplined NO-SPEND record is the system working.
>
> I do NOT dissent against doing *something* now. There is a fully legitimate, budget-free path: pre-registration design scored against the frozen G1–G7 rubric, descriptive-only data characterization, the Dukascopy-vs-Saxo spread reconciliation, and building the spectral N_eff tooling. Do ALL of that immediately — pure value, zero budget.
>
> The firm MAY proceed to a budget-spending 3-pair trial **only** when a pre-registered hypothesis PASSES (not STRETCH) the rubric on the k=3 universe on its own honest power. If G1≤2.0yr is reachable only by borrowing the nine unlanded pairs' independence, the honest disposition is WAIT and run the trial once, well-powered — not now, twice, badly. Spend design effort, not statistical budget, until the data earns the trial.

---

## ROLE STANCES

| Role | Stance |
|------|--------|
| CEO | APPROVE_WITH_CONDITIONS (exploratory-only START; block any confirmatory subset trial before breadth) |
| Head of Quant Research | APPROVE_WITH_CONDITIONS (NO-GO on frozen 8-pair H1; CONDITIONAL GO on new per-pair 3-pair design) |
| CRO | CONDITIONAL (clear as exploratory under C1–C5; VETO trigger = any subset counter-increment or unhaircut edge) |
| Null-Hypothesis Tester | DISSENT on trial-spending; AFFIRM the zero-budget track |
| PM | Consensus meets all 7 acceptance criteria |

**The single thing the firm must NOT do:** run a confirmatory, trial-spending backtest to "validate" a strategy on these 3 correlated majors. A validated-looking result on a 70%-single-factor universe is the firm's worst failure mode — false-alpha certification that burns irreplaceable DSR budget and then collapses when the other 9 pairs reveal it was levered USD beta.

---

## AMENDMENT (post-consensus quick-critic review, 2026-06-19)

A background critic flagged that the consensus asserted a per-pair path "CAN" clear ≲2yr **without checking event rates** — a real overclaim. Resolved with a zero-budget G1 pre-screen:

**Finding — the confirmability bar is just an annualized-Sharpe bar.** Since `SR_ann² = events_per_year × IR_per_event²`, the G1 formula `years_to_validate = 6.18/SR_ann²` reduces to:
- **PASS (≤2.0yr) ⟺ post-cost annualized Sharpe ≥ 1.76**
- **STRETCH (≤3.0yr) ⟺ post-cost annualized Sharpe ≥ 1.44**

The events/yr decomposition is a distraction — what must clear the bar is the **post-cost annualized Sharpe**. This makes the per-pair path's difficulty explicit and refutes "high intraday frequency ⇒ confirmable."

**Pooling the 3 majors barely helps.** k_eff = k/λ_max = 3/2.093 = **1.43**, so pooling all three lifts Sharpe only **√1.43 = 1.20× (+20%)**. To PASS even via pooled-3, each pair needs post-cost SR ≥ **1.47**; single-pair needs ≥ **1.76**. (For reference, trial-48 EURUSD overnight-MR was SR < 0 post-cost — cost-dominated.)

**Plan changes:**
- **NEW CD0 (gate before CD5):** for each candidate per-pair family, estimate the *plausible* post-cost annualized Sharpe and screen against the 1.76 bar (pure paper-math, zero budget). **Do NOT author a CD5 pre-reg for any family whose honest post-cost SR cannot plausibly reach ~1.76.** This likely closes session-open *momentum* per-pair (the critic's point), but higher-Sharpe / higher-frequency families (hourly reversal, spread-/volume-timed entry) are screened on their own merits, not pre-judged.
- **CD1/CD2 must freeze the k=1 (per-pair) confirmability statement explicitly** (the SR≥1.76 bar above is the analytic form) before CD5 authors against it — closes the "pre-reg written against an under-specified gate" gap.
- **Critic correction (don't overgeneralize trial-48):** trial-48 was an overnight *fade*; session-open momentum is directional *continuation* at wider-range opens — different cost geometry. Trial-48 is evidence that costs are decisive intraday, **not** a class verdict that all intraday majors are cost-dominated.

This amendment strengthens the NHT dissent's core point: the honest disposition may well be NO-SPEND on 3 pairs, and CD0 will surface that on paper before any design effort is spent.

---

## CD0 RESULT (executed 2026-06-19) — honest NO-SPEND

Ran the pre-screen: 6 canonical per-pair intraday families × 3 majors, full 5yr **in-sample** (optimistic upper bound), one fixed spec each, **no parameter search, no OOS, no trial-counter increment** (logged as non-counting `descriptive-screen` in `trials.jsonl`). Cost model: half-spread (real per-bar `spread_median_pips`) + 0.25 slippage + 0.15 Saxo haircut per side. Bar: PASS ≥ 1.76 / STRETCH ≥ 1.44 annualized Sharpe.

**Every family FAILS — all 18 pair-family combos and all 6 pooled-3 portfolios are net-negative post-cost.**

| Family | best net SR | max gross SR | verdict |
|---|---|---|---|
| F1 hourly-reversal | −3.24 | 1.50 | FAIL |
| F2 session-open-mom | −0.09 | 1.77 | FAIL |
| F3 intraday-mom-3 | −1.26 | 0.79 | FAIL |
| F4 vol-breakout | −0.42 | 1.90 | FAIL |
| F5 london-am-drift | −0.38 | 1.17 | FAIL |
| F6 spread-filt-reversal | −2.81 | 1.31 | FAIL |

**The tell is in the gross numbers.** Even ignoring *all* costs, only 3 of 18 specs exceed the 1.44 STRETCH bar gross (max 1.90); the raw signal is weak-to-modest, and realistic costs flip every single family net-negative. This is the cost-dominance the NHT/CRO predicted — now confirmed across the whole canonical family space, not just trial-48's overnight fade.

**DISPOSITION: honest NO-SPEND on the 3-major canonical intraday space.** Do NOT author any CD5 pre-registration. Statistical budget preserved (honest-N stays 30). The NHT dissent is upheld by the evidence.

**Scope of this claim (honest limits):** this kills the *canonical* price/volume/spread families on the *3 majors* in their single-spec forms. It does NOT prove no intraday FX alpha exists anywhere — more sophisticated signals, ML meta-labeling, or genuine cross-pair breadth (the 8-pair H1) remain logically open. But combined with H1 trending FAIL on ρ̄_eff (≈0.48 > 0.41), the firm is converging on its pre-identified fork: *if breadth doesn't rescue confirmability, the binding constraint is data capability, not ideas.*
