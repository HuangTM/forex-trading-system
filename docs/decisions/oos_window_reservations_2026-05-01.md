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

**Non-overlap declaration (to be filled in by HoQR before sub-wave 3b):**
```
vol_target_carry OOS window: ________ to ________  ← DOES NOT include 2022–2023 holdout ✓
FRED-carry Bet #1 OOS window: ________ to ________  ← DOES NOT include 2022–2023 holdout ✓
OOS-2022 confirmed clean: YES / NO
Signed: HoQR on ____-__-__
```

---

## 4. Sign-off required

This OOS window reservation is PROPOSED, not active. It becomes active
only after:

- [ ] HoQR reviews and confirms non-overlap with all existing validated-strategy OOS windows.
- [ ] NHT confirms the window is eligible for use as independent OOS evidence.
- [ ] Window ID `OOS-2022` is referenced verbatim in sub-wave 3b pre-reg sidecar
      YAML (`oos_window_start: "2022-01-01"`, `oos_window_end: "2023-12-31"`).

Until sign-off is complete, sub-wave 3b authors MUST NOT use 2022–2023 data
as their holdout window.
