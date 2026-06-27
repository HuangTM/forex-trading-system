# Phase 0 Closure — Negative Result

```yaml
role: ceo
artifact_type: phase-closure
decision: close-phase-0-negative
timestamp: 2026-06-26T22:24:00-07:00
subtask_ref: CEO-PHASE0-CLOSE-2026-06-26 (external progress review + real-data revalidation)

charter_question: >
  "Phase 0 baseline forex trading system — proving alpha exists before building
  complexity." (CLAUDE.md). Does an extractable, cost-surviving, statistically
  confirmable systematic edge exist in this retail FX universe?

answer: NO. Closed with a negative result. No strategy validated across 60 trials
  (honest-N = 30). Both surviving candidate frameworks falsified through the firm's
  own tooling. The binding constraints are structural (cost wall at high frequency;
  no edge at low frequency; USD-correlation breadth wall; confirmability arithmetic),
  not fixable by execution venue, broker, or further parameter search.

evidence:
  - scripts/run_phase1_revalidate.py (REAL-DATA run 2026-06-26, candidate at $1M):
    equal-weighted USDJPY/GBPJPY/CADJPY portfolio Sharpe = 0.04 (claim was 0.59);
    annual return 0.01%; per-pair Sharpe USDJPY 0.16, GBPJPY -0.21, CADJPY 0.10.
    CORROBORATED (NHT ratification 2026-06-26): continuous vol-target sizing at $1M
    gives per-pair 0.06 / 0.32 / -0.16 (avg ~0) — the no-edge result is ROBUST to
    sizing mode, not an artifact of fixed-unit positions.
  - EVIDENCE CORRECTION (NHT, blocking-on-document): the null-hypothesis gate, walk-
    forward, and arson outputs as printed by run_phase1_revalidate.py are DEGENERATE
    artifacts of a capital/min-order-size mis-specification — the candidate runs at
    $1M but the gate/WF/arson controls run at the $100k default, where
    ContinuousSizer.min_order_size=1000 zeroes EVERY position (base_size ~175-350
    units < floor). So the printed "p=1.000, rank 0.0%, worse than random / WF 0.00 /
    arson all-0.00" are NOT evidence of no-edge. A FAIR null test (randoms also at
    $1M) ranks the candidate at the ~20-28th percentile (p≈0.98) — it STILL fails the
    95% gate, so the directional conclusion holds, but "worse than random" is FALSE.
    HARNESS BUG FILED: run_phase1_revalidate.py must pass initial_capital consistently
    to gate/WF/arson; left unfixed this bug could manufacture a false POSITIVE in the
    opposite direction. The no-edge conclusion rests ONLY on the valid evidence: the
    $1M headline 0.04, the continuous-mode replication, and the intraday cost wall.
  - scripts/run_phase1_revalidate.py docstring: the original "Sharpe 0.59 / Validated
    2026-04-07" was computed on SYNTHETIC GBM data (USDJPY values ~6.47 vs real ~159).
    The headline never held on real data.
  - config/carry_momentum_portfolio.yaml (header corrected 2026-06-26 to FALSIFIED /
    DO NOT DEPLOY; prior "validated" header preserved for audit).
  - External cost-sensitivity sweep over scripts/compute_9pairs_readiness.run_cd0_family
    (1h CD0 families F1-F6, 11 pairs, 2021-2025): best GROSS (zero-cost) Sharpe 2.295
    (single EURGBP F1, inconsistent across pairs); only 5/66 clear SR>=1.0 even
    frictionless; at a 0.5-pip round-trip ECN cost, 0/66 net-positive. Cost IS the
    wall intraday, and ECN is the cost floor — a cheaper broker cannot rescue it.
  - External cost-sensitivity sweep on the daily carry-momentum signal (reusing
    CarryMomentumStrategy.generate_signals, fixed-unit + magnitude-aware): portfolio
    Sharpe moves only ~0.06-0.07 across retail(5-7.5pip)→frictionless. ~5 trades/yr →
    cost is structurally NOT the binding constraint for the daily framework.
  - .fintech-org/trials.jsonl: 64 registry objects (60 with trial_id; the rest are
    event rows), 0 with verdict "validated", honest-N = 30. (Count corrected post-
    merge per PR ratification; the pre-merge doc said 60. Ledger-hygiene caveat:
    trial 87fa1d23 "momentum" still reads verdict "passed" though ceo-digest records
    it later corrected/retired after a DSR-deflation fix. See Cleanup items below.)
  - .fintech-org/ceo-digest.jsonl (2026-06-26): trend-on-futures FROZEN pre-reg fires
    F7 DO-NOT-RUN; "binding constraint is statistical CONFIRMABILITY of any modest-Sharpe
    edge at this scale/horizon — ARITHMETIC not data-class." Return to OBSERVE-ONLY.
  - RETIREMENT_DECISION_2026-04-25.md: vol_target_carry placed in
    retire-pending-reconciliation (NOT a hard retire — a return path is preserved
    on successful reconciliation) on an engine-vs-script equivalence failure
    (script Sharpe ~0.76, engine ~-0.08; gap ~0.84).

assumptions:
  - The two external cost-sensitivity sweeps were authored during a 2026-06-26 outside
    progress review. The daily-carry headline (Sharpe 0.04) is from the firm's OWN
    run_phase1_revalidate.py and is independently reproducible: `python3 scripts/run_phase1_revalidate.py`.
  - The intraday sweep reuses the firm's run_cd0_family verbatim, varying only the
    per-trade cost term; signals and bar-set are unchanged.
  - This closure is a CEO-level decision. It has NOT been run through the firm's
    NHT/CRO/PR ratification quorum; apply that gate before treating it as ratified
    governance if desired. No role signatures are fabricated here.

confidence: high (charter question answered NO; carry framework falsified via the
  firm's own gate; intraday cost wall reproducible). The 0.59→0.04 collapse is not an
  interpretation — it is the firm's own revalidation output.
```

---

## What was tested, and how each door closed

| Framework | Frequency | Verdict | Binding constraint | Broker/venue fix? |
|---|---|---|---|---|
| **Intraday CD0 (1h, F1–F6)** | ~hourly | Edge exists but is destroyed by cost | **Cost** — 0/66 net-positive even at 0.5-pip ECN | **No** — ECN is the cost floor |
| **Daily carry-momentum (3 JPY pairs)** | ~5 trades/yr | No edge on real data | **No edge** — Sharpe 0.04, fails null (p=1.000) | **No** — cost is not the lever |
| **"Phase 1 Validated 0.59" claim** | — | Synthetic-data artifact | Real-data revalidation: 0.04 | — |

The two frameworks fail for **opposite** reasons — one has a narrow edge it cannot outrun cost to harvest, the other has no edge while cost is irrelevant — and **neither is rescued by changing execution.** That hypothesis is empirically dead from both ends.

This is consistent with the broader Phase 0 record: 60 trials, 0 validated, and the firm's own June-26 finding that the binding constraint is the **statistical confirmability of any modest-Sharpe edge at retail scale/horizon** — arithmetic, not data quality.

## Why the project *felt* stuck

It was never blocked on process, code, or discipline. The governance machinery (pre-registration gates, OOS holdout, DSR deflation, null-hypothesis gates, falsification archive) is rigorous and load-bearing — it caught the vol_target_carry script-vs-engine gap and the momentum DSR bug. The "stuck" feeling came from the loop continuing to spend cycles *after the answer was already in*: motion without displacement. Closing Phase 0 formally is the act of accepting the negative result the evidence already produced.

## Phase 0 disposition

- **Status:** RATIFIED-WITH-DISSENT (NHT/CRO/HoQR/PR quorum, 2026-06-26) — negative
  result. No live capital. No strategy graduates. Two blocking conditions remain open
  before this is archive-clean: the harness-capital bug fix and the loader DO-NOT-DEPLOY
  enforcement (see Cleanup items + ratification artifact).
- **Closure is NOT authorization to deploy or to reset the kill switch** (CRO C3). The
  no-live-capital invariant stays in force; the Saxo account remains HALTED/flat-of-record
  through and after closure. Last inventory: position_count 0 (saxo_positions_2026-04-26.json).
- **Honest-N preserved at 30.** This closure (and its ratification) spends no trial.
- **Retained as falsification records:** all trial entries, the corrected `carry_momentum_portfolio.yaml`, the CD0 screens, this document, and the ratification artifact + NHT dissent.
- **The engineering is sound and reusable:** clean-architecture engine, sacred no-lookahead test, realistic cost model, walk-forward, null-hypothesis gate, confirmability rubric, falsification ledger. A genuine asset for any future phase.

## Cleanup items (ledger hygiene)

- **`.fintech-org/trials.jsonl` line 24 (trial `87fa1d23` "momentum") still reads
  `"verdict": "passed"`** despite the later DSR-deflation correction (line 36 supersedes
  it with `"verdict": "rejected"`; DSR recomputed 0.999 → ~0.13, below gate). This is
  the SOLE stale `"passed"` row — grep confirms `verdict "passed"` appears only on line
  24 (PR ratification corrected an earlier draft that wrongly implicated lines ~36/46/50).
  Recommend reconciling line 24 (mark deprecated in place) so a future Phase 1 screen
  cannot read a corrected-down trial as a standing pass.
- **[FIXED 2026-06-27] HARNESS BUG — `run_phase1_revalidate.py` capital inconsistency**
  (NHT, B1): the script ran the candidate at $1M but the null-gate/walk-forward/arson
  controls at the $100k default, where `ContinuousSizer.min_order_size` zeroes all
  positions. Fixed by passing `initial_capital=INITIAL_PER_PAIR` to all three. Re-ran:
  null gate now rank 28.0/20.5/28.0%, p=0.982–0.993 (still FAILS the 95% gate); WF
  −0.02/−0.03/−0.15; arson non-degenerate. Matches the fair-test figures; conclusion
  unchanged. (The corrected evidence above already reflects these numbers.)
- **[FIXED 2026-06-27] ENFORCEMENT — the DO-NOT-DEPLOY label is now a control** (CRO C1,
  B2): added a machine-readable `deploy_status:` block to the config and a
  `core.config.assert_deployable()` guard wired into both live loops
  (`run_paper_trading.py`, `run_multi_strategy.py`); removed the falsified `DEFAULT_CONFIG`
  (`--config` is now required). Verified: deployment refuses the falsified config (exit 2),
  allows clean configs, `--force-falsified` overrides with a loud log, and backtests still
  load it freely. 56 config tests pass.
- This does not change the Phase 0 verdict: even counting every `"passed"` row at
  face value, none survived its later correction and 0 carry the `"validated"` mark.

---

## What a different-edge-class Phase 1 would require (scope, not a commitment)

Phase 0 falsified the *retail-archetype* hypothesis class on *price-only daily/1h data in a USD-correlated pair universe*. A Phase 1 should not reopen that class. The evidence points at three hard requirements; a Phase 1 charter is only worth writing if it can satisfy at least the first plus one of the others.

1. **A genuinely different EDGE CLASS** (price-only technical/carry archetypes are exhausted here):
   - order-flow / positioning data (CFTC COT, dealer-flow, options-implied skew),
   - macro/event microstructure (CB-text ML — flagged exploratory but zero-cost),
   - or cross-asset signals not expressible from spot OHLCV alone.

2. **Real diversifying breadth** (the USD-correlation wall: rho_bar_eff ≈ 0.60 vs ≤0.41 gate; N_eff ≈ 1.5 from 8 USD-majors). Requires **non-USD crosses** (EURGBP, GBPJPY, AUDJPY…) or other-asset legs whose effective independent-bet count actually clears the gate. This is a **data-acquisition** task, not a research task.

3. **Confirmability honesty up front.** The firm's own arithmetic: a modest single-leg Sharpe needs ~37–92 years to confirm at this horizon. A Phase 1 must either (a) target an edge large/frequent enough to confirm in ≤3 years, or (b) explicitly adopt a **portfolio-of-many-weak-uncorrelated-signals** thesis (Fundamental Law of Active Management) where the *aggregate* is confirmable even when no leg is — and pre-register the aggregate test, not per-leg.

**Phase 1 entry gate (proposed):** Do NOT author a Phase 1 pre-registration until a candidate edge clears a $0 descriptive feasibility probe showing (i) gross Sharpe that survives realistic cost with margin, AND (ii) an effective-N / breadth profile that can clear the confirmability gate in ≤3 years. Absent both, the correct posture is OBSERVE-ONLY — the same conclusion the June-26 trend-on-futures probe reached.

> **CEO note:** If the goal is *capital return* rather than *research*, the highest-EV action given this evidence is to NOT fund systematic retail FX and to treat Phase 0's negative result as the deliverable. A Phase 1 in a new edge/data class is a separate, larger commitment that should be scoped against expected capital, data cost, and time-to-confirmability before any spend.
