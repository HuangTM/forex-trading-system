# CONSENSUS — Phase 0 Closure Ratification

**Addressed unit:** phase0-closure-2026-06-26:phase0:task1.0
**Date:** 2026-06-26 (ratified 2026-06-27T05:40:00Z)
**Decision under ratification:** Close Phase 0 with a NEGATIVE result (no validated strategy; daily carry-momentum + intraday CD0 families falsified). Artifact: `PHASE0_CLOSURE_2026-06-26.md`.
**Outcome:** **RATIFIED-WITH-DISSENT** — the *decision* is approved by all four roles; two **blocking conditions** apply to the *document/enforcement* before it is archive-clean.

---

## Verdicts

### Null-Hypothesis Tester — `dissent-nonblocking` (on decision) / `blocking` (on document)
Tried to break the closure four ways (fair null gate, continuous sizing, intraday gross-edge, ledger audit); **refutation failed — the decision to close negative is correct.** Headline reproduces (portfolio Sharpe 0.04 at $1M). No-edge is robust to sizing (continuous vol-target at $1M: per-pair 0.06/0.32/-0.16, avg ~0). Intraday cost wall robust and understated (0/54 net-positive; script cost spread+0.80pip is harsher than the doc's 0.5pip ECN).

**BLOCKING DOCUMENT DEFECT:** the null-gate/walk-forward/arson "proofs" are the **same degenerate $100k-capital artifact** — candidate runs at $1M, controls at the $100k default where `ContinuousSizer.min_order_size=1000` zeroes every position. "p=1.000 / rank 0.0% / worse than random" is **FALSE**; the fair test (randoms at $1M) ranks the candidate at the ~20–28th percentile (p≈0.98) — still fails the 95% gate, so the conclusion holds on valid evidence only. **Harness bug must be filed** (could manufacture a false positive in the opposite direction).

### CRO — `approve-with-conditions` (cro_required: true)
Live/SIM book FLAT of record (saxo_positions_2026-04-26.json position_count 0; account HALTED). No live capital at risk; the no-live-capital invariant is intact. **False-positive risk (deploying a falsified strategy) dominates decisively** → close + harden.
- **C1 (BLOCKING):** the DO-NOT-DEPLOY label is a YAML comment only; `scripts/run_paper_trading.py:51` still defaults to `carry_momentum_portfolio.yaml` with no loader guard. Enforce in code + drop as default.
- **C2:** pull a fresh inventory to close the GBPJPY/CADJPY SIM forensics gap.
- **C3:** closure must state it is NOT authorization to reset the kill switch. *(Added to doc.)*
- **C4:** reconcile stale `trials.jsonl` "passed" rows.

### Head of Quant Research — `approve-with-conditions`
Consistent with the research arc (Board already voted OBSERVE-ONLY 2026-06-25; trend-futures DO-NOT-RUN 2026-06-26). Negative result load-bearing and correctly scoped; Phase 1 guidance sound (different edge class; breadth vs rho_bar_eff≈0.60 wall; confirmability honesty). Precision note: for the **intraday** framework the *proximal* binding constraint is **cost**, with confirmability the *terminal* wall — the doc's table disaggregates this correctly; the one-line header conflates slightly.

### Principal Reviewer — `approve-with-conditions`
Core facts verified (synthetic-GBM disclosure, retire-pending-reconciliation characterization, 0.76/-0.08 gap, 0 validated, valid JSON digest entry). Blocking: (1) "60 ledger entries" is wrong — 64 objects / 60 with trial_id (post-merge); (2) stale `"passed"` is **only** line 24, not lines ~36/46/50. *(Both corrected.)*

---

## NHT dissent (append-only, preserved verbatim)

> APPEND-ONLY NHT DISSENT — Phase 0 closure 2026-06-26.
> I CONCUR that Phase 0 closes NEGATIVE: no validated strategy exists; the daily
> carry-momentum config has no edge at deployable scale (portfolio Sharpe 0.04, robust
> across discrete and continuous sizing at 1M), and the intraday CD0 families are
> destroyed by cost (0/54 net-positive, gross mostly <1). Honest-N stays 30. Do NOT
> reopen this hypothesis class.
> I DISSENT on the EVIDENCE as written. Three of the closure's evidence bullets are
> artifacts of an initial-capital / min-order-size mis-specification in
> run_phase1_revalidate.py (candidate at 1M; null-gate randoms, walk-forward, and arson
> at the 100k default where ContinuousSizer min_order_size=1000 zeroes every position):
>   (a) "null-hypothesis gate FAILED ... p=1.000, rank 0.0% — worse than random
>       shuffles" is FALSE. Fair test (randoms at 1M): rank 28/20.5/28%, p≈0.98 — fails,
>       but at ~25th percentile, NOT worse-than-all-random.
>   (b) "walk-forward avg SR 0.00, Consistent = NO" is a zero-capital artifact, not
>       evidence of no edge. Remove or re-run at ≥1M.
>   (c) the arson table (all 0.00) is degenerate and non-informative.
> REQUIRED BEFORE RATIFICATION (blocking on the DOCUMENT, not the decision): correct
> bullets (a)-(c) to the fair-test figures or strike them; downgrade "confidence: high"
> to rest on the surviving, independently-valid evidence (the 1M headline 0.04, the
> continuous-mode replication, and the intraday cost wall). FILE A HARNESS BUG:
> run_phase1_revalidate.py must pass initial_capital consistently to the gate,
> walk-forward, and arson (this bug could manufacture a FALSE POSITIVE in the opposite
> direction and is not caught by any current gate).

**Disposition of dissent:** bullets (a)–(c) corrected in `PHASE0_CLOSURE_2026-06-26.md` and the config header; harness bug filed as a Cleanup item. Dissent preserved here append-only per rule 6.

---

## Open blocking conditions (tracked, not yet closed)
1. **Harness-capital bug** (NHT) — fix `run_phase1_revalidate.py` initial_capital consistency.
2. **Loader enforcement** (CRO C1) — `run_paper_trading.py` must refuse FALSIFIED configs and drop the falsified default.

Both are code changes; each warrants its own Principal-Reviewer pass. The **closure decision stands ratified**; these gate "archive-clean / fully-enforced" status, not the negative-result conclusion.
