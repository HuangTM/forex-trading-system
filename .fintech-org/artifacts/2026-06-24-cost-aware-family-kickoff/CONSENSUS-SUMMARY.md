# Consensus on: Cost-aware candidate family — CB-decision drift (C1) and carry-sign hold (C2) — cheap feasibility screen

**Status:** ratified_with_dissent (distributed quorum: cro + head-of-quant-research, 2026-06-25; surfaced to Board, non-blocking)
**Full audit:** see `./CONSENSUS.md`
**Session:** `.fintech-org/artifacts/2026-06-24-cost-aware-family-kickoff/`

## Decision

NO-SPEND. C1 RETIRE (regime artifact). C2 KILL. Honest-N stays 30. Trial counter does not increment.
The Board's R1+R2 pivot was adopted: CD0 cost-feasibility gate ran first, before any counted trial.
OPEN-ITEM-F001 (reversal cost under-count) is now CLOSED — fix assertion-verified (flip charges 2 RT).
All four IC reviewers independently converged: the load-bearing cell (USDJPY-12h gross 19.94 pips)
collapses to 5.87 pips / t=0.62 when 2022–2023 is dropped; 8 of 9 C1 cells have raw |t|<1; C2 carry
accrual = 0.02 pips (carry never tested); best cell pre-deflation t=2.33 < Bonferroni floor 2.84.
HoQR's own pre-committed kill gate ("survive dropping 2022–23") is FAILED → C1 RETIRE, C2 KILL.

## Top-3 risks the CEO should know

1. **Single-regime artifact, not a repeatable edge** (severity: high): USDJPY = 97.4% of C1 net
   margin; the 2022–23 FOMC hiking cycle (30% of events) supplies 53–54% of gross. Outside that
   window, 2021 and 2024 means are economically zero (0.20, 0.68 pips). The drop-regime t=0.62
   is the falsification. An edge concentrated in one hiking episode is the JPY-carry-unwind blowup
   profile (CRO: Aug-2024 unwind archetype). Source: HoQR, NHT, CRO, PR — independently converged.

2. **C2 carry hypothesis untested; exit-cost bug understates C2 cost** (severity: high, OPEN item):
   C2 crash filter collapsed holds to ~5 days; carry accrual < 0.5% of gross — carry was never
   exercised. Additionally, PR found the exit-leg cost is dropped for all 366 C2 trades
   (OPEN-ITEM-C2COST): corrected USDJPY C2 margin is −0.74 pips (net negative), not +1.81.
   Source: PR (independent verification), QD, HoQR.

3. **C1 surprise filter non-binding; ECB/BOE dates absent** (severity: medium, OPEN item):
   The filter passed 100% of events (n_fires == all verified CB dates, all 3 pairs) because
   the max-TR bar attribution pre-selects high-volatility bars. C1 as-run = "trade every CB date,"
   not a surprise-conditioned strategy. ECB and BOE have 0 verified-official dates in the store;
   EURUSD and GBPUSD used FED-only events. Source: PR (OPEN-ITEM-C1FILTER), QD, NHT.

## Dissents (one-liner each; full verbatim text in CONSENSUS.md § Dissent)

- **NHT (severity: informational; CONCURS NO-SPEND):** 8/9 cells |t|<1 before any correction;
  drop-2022/23 collapses USDJPY to t=0.62; mean >> median (fat-tail / single-regime domination);
  C2 carry never tested; this is data-snooping, not edge — opposes any framing as "non-negative signal."
- **CRO (size-reduced 0.20 → explicit fallback NO-SPEND):** 0.20 authorized only for a USDJPY-only
  regime-split-gated cell that survives the hiking-cycle drop — which it does not (t=0.62); fallback
  is NO-SPEND; best-cell t=2.12 does not clear Bonferroni floor 2.84; no risk-adjusted metric supplied.

## Open items requiring CEO acknowledgment

- **OPEN-ITEM-C2COST (high; quant-developer):** C2 exit-leg cost dropped in `scripts/cost_feasibility_c1_c2.py` — same bug class as F-001. Must fix and re-assert before any C2 reuse. Corrected USDJPY C2 net = −0.74 pips (not +1.81).
- **OPEN-ITEM-C1FILTER (required before any C1 re-registration; quant-researcher):** C1 surprise filter is non-binding under max-TR attribution. Any future C1 re-screen needs real CB release timestamps + a genuine surprise gate, or the spec must be rewritten as unconditional.
- **ECB/BOE date acquisition (recommended; RANK-2):** 0 verified-official ECB/BOE dates in store; EURUSD/GBPUSD C1 are FED-only proxies. HoQR recommends acquiring these as the gate to re-screening those pairs. CEO decides: authorize acquisition?
- **C1 re-screen authorization (forward path; not executed):** HoQR recommends re-screening C1 with (i) out-of-hike net as a precondition, (ii) a binding surprise filter (requires real release timestamps), (iii) verified ECB/BOE dates. CEO decides: fund the re-screen, or treat C1 as retired and redirect to new generation?

## Skill gaps logged this session (N=0)

*No installable skill gaps logged this session. All knowledge_gaps in session artifacts are
research-data limitations (no tick-level surprise data; no broker-swap ledger; no CB release
timestamps; ECB/BOE verified dates absent). None map to an installable skill.*

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets if relevant: `revise c1-re-screen-path` `revise ecb-boe-acquisition` `revise c2-cost-bug-disposition`

---
*This SUMMARY is for routine ratification. Read full `CONSENSUS.md` for substance. The full doc
is the audit-trail source-of-truth; the SUMMARY is convenience only.*
