# CONSENSUS SUMMARY — Trend-on-Futures Pre-Registration (2026-06-26)

**Status:** ratified_with_dissent (distributed quorum: head-of-quant-research + principal-reviewer, 2026-06-26; F7 DO-NOT-RUN; observe-only)
**honest-N:** 30 (UNCHANGED — no trial spent)
**Session:** `.fintech-org/artifacts/2026-06-26-trend-futures-prereg/`

---

## Decision

The trend-on-futures pre-registration is FROZEN as a model artifact; its F7 confirmability power gate fires DO-NOT-RUN; the committed backtest is NOT authorized; honest-N stays 30; the firm returns to observe-only. The pre-registration's own arithmetic, computed at $0 on published-decayed inputs (per-bet Sharpe 0.20, effective bets B=4-10, compound 37-trial deflated alpha), yields years-to-validate of 37-92 years — clearing the ≤3yr bar would require a net annual Sharpe of ~2.2, roughly 4-5× the highest gross diversified-trend Sharpe ever published. Cost (W1) is not the binding constraint (probe: residual ~0.40 >> 0.20 gate). Confirmability is. The firm proved this for $0, before spending a single honest-N trial — the F7 gate working exactly as designed.

---

## The Headline Finding

**The firm's binding constraint is ARITHMETIC, not data class.** Trend-on-futures escaped cost (W1) and the no-volume wall (W4). It did not escape the confirmability wall — because that wall is determined by modest-Sharpe × finite-breadth-and-horizon under honest deflation, not by data class. Cross-asset breadth helps (lifts B from ~2-4 to ~4-10, shortening the horizon from centuries toward decades); it does not help enough. Decades is not 3 years. There is no retail-accessible, modest-Sharpe systematic edge the firm can confirm at power within a reasonable horizon. The validated harness and the falsification corpus are the firm's real assets.

---

## Top-3 Risks / Findings

1. **F7 arithmetic is decisive and not close.** Even the most generous honest construction (Hurst diversified gross ~1.0 × 0.50 decay = 0.50 taken as direct net program Sharpe) yields ~59 years. The required Sharpe of ~2.2 is not a numerical near-miss — it is ~4-5× the published frontier. The do-not-run verdict is robust to every plausible input.

2. **The confirmability wall is the terminal constraint, not a data gap.** The 2026-06-07 DATA-CAPABILITY finding (dataset wall, not idea wall) was correct but incomplete. This arc establishes the deeper result: even with real-volume futures data and cross-asset breadth, the events/yr × per-event-Sharpe arithmetic governs. More or better data of the same class does not change this.

3. **v1 prose error and v2 self-correction set the model for honest peer review.** The quant-researcher's v1 pre-registration contained a material false claim (breadth compresses horizon to ≤2-3yr). NHT demonstrated the claim to be arithmetically false by 1-2 orders of magnitude under the pre-registration's own formula. The quant-researcher self-corrected in v2 (surgical fix: pinned s=0.20 as non-circular; removed all ≤2-3yr achievable claims; froze three secondary DOFs). This v1→v2 cycle is a model for how the firm's peer review is supposed to function.

---

## Dissents

**NHT (DISSENT verbatim-preserved in CONSENSUS.md, § Dissent; append-only):** Affirms the falsification machinery (all 7 criteria frozen, single-program accounting, 37-trial compound deflation). Dissents on the v1 prose: the central thesis (breadth compresses horizon to ≤2-3yr) is arithmetically false by 1-2 orders of magnitude under the pre-reg's own F7 formula; F7 fires DO-NOT-RUN on every plausible input. Required v2 corrections: (1) prose to honest do-not-run posture; (2) F7 per-bet Sharpe input pinned to published-decayed 0.20 (non-circular). V2 applied both. Dissent is append-only; the machinery survives; the v1 narrative defect was the sole veto point.

**PR (non-dissent, approve-with-conditions):** 0 blocking for frozen design; 3 blocking-for-committed-backtest (F-001: threshold reconcile 3.0yr vs canonical 2.0yr G1 bar; F-002: holdout-seam purge; F-006: freeze roll/back-adjust convention). Independently recomputed years-to-validate; consistent with NHT and QR v2 results.

---

## Open Items

1. **No Board spend authorization is required.** Observe-only stands. No data purchase, no committed backtest, no honest-N spend.

2. **Frozen pre-registration is on file as a re-activatable spec.** `quant-researcher-prereg.yaml` (v2) is the authorized design if the firm ever operates in a regime where the F7 power gate is feasible. Reactivation conditions: a fundamentally higher Sharpe regime, a much longer history, or a non-modest-edge class — not another modest-Sharpe systematic idea.

3. **Forward conditions for any future committed-backtest** (should the power gate ever clear): F-001 (reconcile F7's 3.0yr threshold with canonical 2.0yr G1 bar), F-002 (symmetric purge+embargo at holdout seam), F-006 (freeze back-adjust method and roll trigger before acquisition).

---

## Skill Gaps

**Installable skill gaps: N = 0.** No skill gap impaired this review. All remaining gaps are Board inputs (capital base, Saxo CME access) or pre-computable research tasks (realized effective-bet count from published tables), not installable skills.

---

## Ratification Prompt

> Board (CEO): this arc reached its terminal conclusion at $0. The trend-on-futures pre-registration is FROZEN as a model artifact; its own F7 power gate fires DO-NOT-RUN on published-decayed inputs (years-to-validate 37-92yr; clearing ≤3yr would require net annual Sharpe ~2.2, roughly 4-5× the published frontier). Honest-N stays 30 — no trial was spent. The NHT dissent is preserved verbatim; the v1 prose error was self-corrected in v2; the PR finds 0 issues blocking the frozen design. The firm's binding constraint is not data class — it is the arithmetic of confirmability for any modest-Sharpe edge at this scale. The validated harness and falsification corpus are the firm's assets. Observe-only stands. Do you ratify this consensus and acknowledge that no spend authorization is requested?
