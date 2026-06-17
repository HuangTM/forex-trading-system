# CONSENSUS SUMMARY — Intraday EURUSD 1h Strategy Design
## 1-Page CEO Ratification Surface

**Session:** 2026-06-17 | **Track:** intraday-eurusd-1h-strategy-design  
**Status:** AWAITING RATIFICATION | **Trial count:** 47 (trial 48 reserved; not yet burned)  
**north_star_trace:** [O1, O2]

---

## Decision (≤5 sentences)

The firm has a viable intraday research path using the EURUSD 1h data, but it is not yet executable. The recommended plan is: (1) resolve three BLOCKING findings from the Principal Reviewer, then re-freeze the pre-registration; (2) run the overnight mean-reversion candidate (A2') exactly once as trial 48 on the discrete engine — modal outcome is a clean KILL, which is a legitimate falsification-archive entry; (3) in parallel, ship two small engine fixes (continuous-mode swap 24× overcharge at engine.py:316; session-filter hook absent) so the more-confirmable session-momentum archetype (A1) is pre-registerable as trial 49; (4) hold the honest ceiling: single-pair 1h is STRETCH not CONFIRMABLE, and the real intraday unlock is breadth (12 pairs at 1h), not cleverness on one pair. The pre-registration is not frozen, the OOS holdout has not been touched, and the org trial counter remains at 47 pending CEO acknowledgment of items below.

---

## Top-3 Risks

1. **F-006 — Spread gate uncomputable (BLOCKING):** The ≤4-pip per-bar realized-spread NO-TRADE gate cannot be evaluated from the 1h OHLCV parquet (columns: open, high, low, close, volume — no bid/ask column; intrabar 40.7-pip spikes are invisible at close-to-close resolution). The gate must be replaced with a computable substitute before the pre-registration is valid. If left unresolved, the cost-protection intent of the design fails and a backtest result would be uninterpretable.

2. **F-009 — KILL-4 power gate is a latent OOS peek (BLOCKING):** The spec's "count qualifying OOS trades; if <48 do NOT burn holdout" requires computing entry-gate qualifications over OOS data, which itself constitutes touching the one-shot holdout. Fix requires IS-frequency extrapolation only; any OOS computation is the burn. This is load-bearing for the oos_holdout_one_shot hard constraint.

3. **F-002/003/010 — Feature-window leakage triad (BLOCKING):** The 20-bar same-hour-class trailing σ spans ≈480 hourly bars (≈20 trading days). CPCV purge (24 bars) and the intra-CPCV embargo decontaminate the label horizon but not the feature window. Additionally, the spec does not exclude the current bar from its own σ (self-referential lookahead). All free parameters must be frozen pre-IS-look, or effective-N inflates from ≈48 to ≈10³–10⁴ and the DSR deflation bar becomes too lenient.

---

## Dissents (one-liners)

- **NHT:** STRETCH verdict, decision=survives. Dissent-statement field: empty — NHT recorded no formal dissent. NHT's position is that the claim is CONFIRMABLE-CONDITIONAL only if the structure is pre-registered (keeping N ≈48) and clears net annualized Sharpe ≈1.6 over the embargoed OOS.
- **HoQR (substantive hold, not a formal block):** Holds TRAP as the expectancy prediction for A2' — converges on running it for falsification economics, not because HoQR expects it to survive. HoQR's approval is explicitly capacity-limited: A2's run is approved ONLY IF the swap-fix + session-filter build is committed in parallel, so A1/A3 are not permanently blocked behind the infra wall.
- **CRO (size-reduced, not full approval):** Decision is size-reduced (0.25× ceiling), not approve. Full-size approval requires the pre-registration to be reissued with the ≈6-pip realistic round-trip cost, a declared per-trade stop, and the spread gate resolved. Absent a declared stop, CRO escalates to VETO.

---

## Open Items Needing CEO Acknowledgment

1. **F-006 resolution approach:** Choose: (a) substitute a static per-session cost assumption (e.g., from the 4h spread parquet, declared and frozen in the pre-registration) in place of the per-bar realized-spread gate, or (b) acquire intrabar spread data before running. CEO choice required; quant-researcher cannot proceed without it.

2. **F-009 fix authorization:** Confirm that the power gate must use IS-frequency extrapolation only, and that any OOS computation counts as the one-shot burn. This closes the holdout integrity risk.

3. **F-002/003/010 fix authorization:** Authorize quant-researcher to re-issue the pre-registration with (a) current-bar exclusion from σ, (b) CPCV purge/embargo sized to the feature window (≈480 bars), and (c) a boundary embargo ≥20 trading days at the IS/OOS seam, all frozen before any IS code runs.

4. **Parallel infra commitment:** Authorize QD to ship the swap one-liner (engine.py:316 ÷ bar_duration_hours) and the session-filter hook in parallel with the A2' trial 48 run. Without this commitment, A1/A3 remain blocked behind an infra wall after A2' likely KILLs.

5. **Honest ceiling acknowledged:** Confirm the firm acknowledges that (a) the modal outcome of trial 48 is a clean KILL and that is a legitimate use of trial 48, and (b) the real intraday ceiling unlock is intraday data across the other 11 pairs (data-capability track), not further single-pair signal generation.

---

## Skill Gaps Logged This Session

N=2 gaps identified; both are data-capability gaps, not installed-skill gaps.

1. **Intrabar / tick-level spread data for EURUSD:** The 1h OHLCV parquet has no bid/ask column; intrabar spread spikes are invisible at close-to-close resolution. The spread gate (CRO requirement) and the overnight cost distribution (QR assumption) both rest on proxies. Acquiring native 1h or tick-level bid/ask data from Dukascopy would close F-006 and sharpen the overnight P90 slippage estimate.
2. **Intraday data for the other 11 pairs:** All non-EURUSD pairs remain daily-only. The dataset wall finding is that single-pair 1h relocates but does not break the confirmability ceiling. Cross-sectional diversification across 12 pairs at 1h is the one-time structural unlock. This is the standing data-capability recommendation from HoQR.

---

## Ratification Prompt

> **CEO action required.** The firm's Principal Reviewer returned three BLOCKING findings (F-006, F-009, F-002/003/010) that prevent the pre-registration for trial 48 from being frozen. Per governance protocol, BLOCKING findings require explicit CEO acknowledgment before execution proceeds. The OOS holdout is intact; the trial counter is at 47.
>
> **To proceed:** Acknowledge items 1–5 in the Open Items section above, or redirect the research. A simple "acknowledged, proceed with fixes" on items 1–5 authorizes the quant-researcher to re-issue a corrected pre-registration, QD to ship the parallel infra fixes, and the firm to run trial 48 after the pre-registration is re-frozen.
>
> **To pause:** Redirect to the data-capability track (acquire intraday data for the remaining 11 pairs) as the higher-value prior action, and defer trial 48 until breadth is available.
>
> **No action required to preserve the OOS holdout** — it is safe; no computation has been run against it.

---

*Full CONSENSUS with per-role citations, artifact evidence, and full PR findings: `CONSENSUS.md`*  
*PM authored: 2026-06-17*
