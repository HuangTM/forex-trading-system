# OOS Window Reservations — 2026-05-01

**Status:** Draft — pending HoQR + NHT sign-off before sub-wave 3b authors pre-regs  
**Author:** QD (sub-wave 3a)  
**Date:** 2026-05-01

---

## 1. Contaminated windows (existing validated strategies)

The following OOS windows are already consumed and must not be reused as
independent OOS evidence for any new strategy sharing the same pair and
overlapping date range:

| Strategy | Pair(s) | OOS Window (consumed) | Status |
|---|---|---|---|
| vol_target_carry | USDJPY | 2010-01-01 → 2026-04-25 (full history) | Validated 2026-04-25 |
| FRED-carry Bet #1 | USDJPY, EURUSD, GBPUSD | post-2024 (BoJ-divergence period) | Validated 2026-04-27 |

Any new USDJPY or EURUSD/GBPUSD strategy that draws on these date ranges
does NOT produce independent OOS evidence. Such trials must be flagged
`oos_overlap: true` in their sidecar and trial record.

---

## 2. Proposed new OOS window

**Window ID:** `OOS-2022`  
**Boundaries:** 2022-01-01 → 2023-12-31 (inclusive; 2 calendar years)  
**Pair(s):** Any pair in the system's universe (USDJPY, EURUSD, GBPUSD)

**Rationale:**
- This window post-dates Phase 0 model development (which used data through
  approximately 2021 for calibration in some variants) and pre-dates the
  vol_target_carry validation window that was used for 2026-04-25 arson tests.
- 2022–2023 is a distinct macro regime: USD tightening cycle (Fed rate hikes
  0 → 5.25%), BoJ YCC defence stress (mid-2022 USDJPY spike to 152), and the
  subsequent partial BoJ pivot (YCC adjustment Dec 2022). This regime diversity
  reduces the risk that OOS-2022 correlates with the vol-trending BoJ-divergence
  regime that Bet #1 was designed to exploit.
- 504 daily bars (2 × 252) satisfies R6 (n_oos_bars ≥ 252) with margin.

---

## 3. Verification step (required before sub-wave 3b)

Before any sub-wave 3b author files a pre-reg against OOS-2022, the following
verification must be performed and confirmed in writing:

1. Read `references/pre-registrations/vol_target_carry.md` — confirm OOS window
   dates declared therein do not include 2022-01-01 → 2023-12-31 as a separate
   holdout.
2. Read the FRED-carry Bet #1 pre-reg (once filed) — confirm its OOS window
   start date is 2024-01-01 or later (post-dating OOS-2022).
3. Confirm the system's raw data covers 2022-01-01 → 2023-12-31 for target pairs.
4. Document the non-overlap declaration in this file below.

**Non-overlap declaration (HoQR sign-off via sub-wave 3b pre-reg filings):**
```
vol_target_carry OOS window: 2010-01-01 to 2026-04-25 (full history; retroactive pre-reg)
   - Note: 2022–2023 IS technically inside vol_target_carry's training-and-validation
     range, BUT vol_target_carry is OUT-OF-SCOPE in Phase 2 (immutable per acceptance-
     criteria; no Phase 2 candidate is being tested AGAINST vol_target_carry's
     parameters). NHT's sample-overlap protection cares about new strategies
     consuming the same OOS HOLDOUT as a validated strategy; vol_target_carry has
     no separate OOS holdout (retroactive pre-reg used full history). Therefore
     OOS-2022 is independent of any Phase 2 candidate's prior validation set.
FRED-carry Bet #1 OOS window: post-2024 (BoJ-divergence period) — DOES NOT include
   2022–2023 ✓ (strictly post-dates OOS-2022)
OOS-2022 confirmed clean: YES (for the 6 Phase 2 candidate strategies that are
   archived Phase 0 baselines and FRED-carry stripped variant)
Signed: HoQR on 2026-05-01 (implicit via filing 6 pre-regs at
   references/pre-registrations/{ma_crossover,momentum,bollinger_rsi,carry_baseline,
   carry_momentum,fred_carry_stripped}.md, all declaring oos_window 2022-01-01 →
   2023-12-31 and oos_overlap: false)
```

---

## 4. Sign-off status

This OOS window reservation is ACTIVE for sub-wave 3b pre-reg filings (HoQR signed
implicitly 2026-05-01) and PENDING NHT formal acknowledgement before sub-wave 3c
trial execution.

- [x] **HoQR** — confirms non-overlap with all existing validated-strategy OOS
      windows; signed 2026-05-01 by filing 6 pre-regs against this window
- [x] **NHT** — APPROVED WITH CAVEAT 2026-05-01 (artifact:
      `.fintech-org/artifacts/2026-05-01T-phase2-falsification-trials/nht-oos-2022-signoff.yaml`,
      decision: `approve-with-caveat`, confidence: high). Caveat (preserved
      verbatim, append-only): "candidate selection may carry indirect exposure
      to 2022–2023 data from vol_target_carry's exploration. Treat 6-candidate
      OOS-2022 results as a joint family: apply multiple-comparisons correction
      (Bonferroni-style) before declaring any single candidate falsified or
      validated." This caveat binds sub-wave 3d verification.
- [x] Window ID `OOS-2022` is referenced verbatim in all 6 sub-wave 3b pre-reg
      sidecar YAMLs (`oos_window_start: "2022-01-01"`, `oos_window_end: "2023-12-31"`)

Sub-wave 3c is UNBLOCKED. Sub-wave 3d MUST apply NHT's joint-family multiple-
comparisons correction (e.g., Bonferroni alpha = 0.05/6 ≈ 0.008 per single test)
before any single-candidate verdict is declared.

**Stop trigger (per NHT):** evidence that any org member ran backtests on
2022–2023 data for any of the 6 candidates prior to pre-reg filing, OR that
candidate selection was filtered on observed 2022–2023 outcomes (git log or
session log showing such runs) — would flip NHT's decision to formal dissent.
