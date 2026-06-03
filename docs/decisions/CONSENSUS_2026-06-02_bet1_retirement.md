# CONSENSUS: Bet#1 (trial 87fa1d23) — RETIRED as falsified

**Status:** ratified (distributed quorum: head-of-quant-research + null-hypothesis-tester)
**Track:** bet1-retirement-2026-06-02 / Phase 1 / Task 1.0
**Ratification:** `.agent-accountability/ratifications/bet1-retirement-2026-06-02:phase1:task1.0.yaml`
**Follow-on under:** `CONSENSUS_2026-06-01_paper_launch_acceleration.md` (HoQR-prioritized research item)

## Decision

Trial **87fa1d23** — the firm's "FRED-carry Bet#1", in fact a momentum (rate-of-change)
equal-weight **EURUSD + USDJPY + GBPUSD** portfolio over OOS 2022–2023 — is **RETIRED as
FALSIFIED**. Its corrected Deflated Sharpe **0.12963** fires the pre-registered gate
**momentum-T3 (DSR < 0.50)** by ~3.9×. The prior "PASS" (DSR 0.99999986) was an artifact of
the F-001 degenerate-units bug, now fixed. **The firm has ZERO validated OOS survivors.**

## How we got the number (verified)

- **Equity regenerated** (it was never originally persisted — the falsification entry-point
  didn't write equity parquets). The reconstruction reproduces the recorded metrics **exactly**:
  Sharpe 0.31406, n_trades 126 (43+30+53), maxDD 0.15425 — zero delta. Restored to
  `data/results/trials/87fa1d23_equity.parquet`. **No new trial registered** (honest-N still 10).
- **DSR — bar-count:** T=519, skew 0.356, excess-kurt 1.002, honest-N=10 → **0.12963**.
- **DSR — T_eff (2026-06-01 binding ruling):** lag-1 autocorr ρ=0.0253 (< 0.05) → T_eff = T = 519
  → **0.12963** (coincides with bar-count; no autocorrelation shrinkage). Robust to N∈[10,24].

## Gate adjudication (pre-reg `references/pre-registrations/momentum.md` R4 — "FALSIFY if ANY fires")

| Gate | Threshold | Value | Fires? |
|---|---|---|---|
| momentum-T1 | OOS Sharpe < 0.30 | 0.31406 | no (by 0.014 < ~1 SE — a coin-flip pass) |
| momentum-T2 | maxDD > 25% | 0.15425 | no |
| **momentum-T3** | **DSR < 0.50** | **0.12963** | **YES — decisive** |
| momentum-T4 | n_trades<30 or bars<252 | 126 / 519 | no |

## Roles (concordant — no override)

- **NHT → noise-indistinguishable.** Raw 0.314 → deflated 0.13 ≈ 13% confidence the edge is
  real; ~87% consistent with selection luck + finite-sample noise on a heavy-tailed series.
  T1-pass / T3-fail is the same data before vs after correcting for multiplicity + non-normality.
- **HoQR → retire.** Validated-OOS-survivor count after = **0**. 2026-07-01 auto-retire resolved
  early on the Bet#1 leg; kill-criterion remains TRIPPED. Filed to the falsification record
  (registry verdict corrected to `rejected`, triggered `momentum-T3`, via append/last-row-wins;
  trial retained, not deleted). Resurrection bar: new pre-reg + new OOS window + a
  deflation-surviving prior — never a bare raw-Sharpe pass.

## Caveats (foregrounded)

- Data is **Phase-0 synthetic** — even the retained "carry dominates" direction is provisional.
- The raw-Sharpe T1 pass must not be misread as edge.

## Next research capacity (HoQR ranking)

1. R5 permutation / Reality-Check on **real** carry data (now the dominant open question).
2. Fix the carry USDJPY data-quality outlier (upstream of R5).
3. Acquire/validate **real** (non-synthetic) data.
4. Harden the falsification machinery (0 STRONG OOS rejections to date).
