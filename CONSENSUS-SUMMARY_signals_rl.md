# CONSENSUS SUMMARY — Classic Signals & RL Feasibility
**Track:** signals-rl | **Phase:** 1 | **Task:** 1.0 | **PM:** fintech-org
**Timestamp:** 2026-06-17T06:00:00Z | **Status:** AWAITING CEO RATIFICATION

## Decision (≤5 sentences)

The QR classic-basket pre-reg is **NOT freeze-ready**: PR issued a package-level REJECT on a
blocking finding (N=54 deflation denominator is dishonest — true N ≈ 30–200+ per the firm's own
`null_hypothesis.py`) plus four major defects (disguised directional sweep; MACD frozen but absent
from codebase; adaptive purge on always-in members; flat cost neutralizes M6's only thesis). RL is
UNANIMOUSLY premature behind the data wall (MLR veto, HoQR rank #3, NHT TRAP, CRO conditional-NO):
one price path ≈ ~10 regime realizations; RL feasibility doc is banked; named data-milestone gate
must be set. Firm-unanimous #1 priority is DATA-CAPABILITY (breadth + true bid/ask spread): burns
zero deflation slots and is the one lever that changes the cost arithmetic for every future trial.

## Top-3 Risks

1. **Spurious pass at N=54 (F-001).** If M6 clears DSR≥0.95 at N=54 the "pass" is suspect — the
   bar was set against a denominator that is the smallest of three plausible options applied to the
   broadest selection surface. This bites exactly on the upside branch where it does the most harm.

2. **RL effective-N explosion (NHT TRAP).** A modest RL search ≈ 4,800 distinct policies (floor);
   realistic ≈ 10^4–10^5. DSR bar at N=5,000 is ~2.20 annual SR, combined with the 7.5-pip cost
   wall that already produced DSR=0.00 at trial 48. Logging as "1 trial" is the largest honesty
   failure available.

3. **No bid/ask spread column.** Both M6's thesis and RL's cost term are modeled assumptions, not
   measured data. The gap that decides feasibility is a data gap, not an analytical one.

## Dissents

**NHT (formal, strong_objection, does_block=false — VERBATIM-SHORT):**
> "CLAIM A understates N by logging only '48 + basket-size': if the K members were selected from a
> variant grid (and classic indicators ARE families of variants), the honest denominator is 48 +
> grid-size, not 48+K, and the cost wall makes the expected cost-dominated fraction ~>=70%. CLAIM B
> is structurally a TRAP as stated: 'trained on 5 years' reports the survivor of a 10^3-10^5
> search as if N=1, on a single price path, against a 7.5-pip cost that already buried a REAL edge."

**MLR (BUILD-NOW VETO):** PREMATURE — ~10 regime realizations, RL eval bar ~2.20–2.70 annual SR
against same cost wall that killed trial 48.

**CRO (size-reduced, conditional-NO on RL):** Size multiplier 0.25; min gross edge 11.25 pips;
RL blocked pending outer deterministic risk envelope (separate process, out-of-band, Knight Capital
lesson); basket = ONE EURUSD position for risk budgeting.

## Open Items (CEO fork)

**(a)** Rework basket to PR/NHT standard (honest N ≈ grid-size; implement MACD before freeze; pre-
freeze purge; resolve cost/M6 contradiction). Or: **minimal 2-member** (MACD-cross + EMA50/200).

**(b)** Skip basket; pivot to DATA-CAPABILITY (firm-unanimous #1). Zero deflation slots burned.

**(c)** Both in parallel: data-capability + minimal basket as cheap rider (HoQR preferred path).

Set the **named RL re-trigger milestone**: ≥6 of 12 pairs at ≤1h with true bid/ask spread, OR
sub-1h + volume for EURUSD. Name the re-initiator (HoQR on CEO sign-off) to close this item.

## Skill Gaps (N=2)

- Bid/ask spread data absent from parquet — data acquisition is the resolution, not more analysis.
- DSR denominator rule inconsistency: `honest_n.py` and `null_hypothesis.py` give different N's;
  the pre-reg invented a third rule. Recommend adopting Bailey-LdP search-cardinality as canonical.

## Ratification Prompt

**Three explicit acknowledgments required before any spend:**

1. **PR BLOCKING (F-001):** N=54 is dishonest. Acknowledge and direct QR to rework.
2. **NHT DISSENT:** Formal dissent recorded, append-only, survives consensus. Acknowledge.
3. **MLR VETO:** RL build blocked. Name the data-milestone that re-triggers authorization.

> **(a) Rework basket (or minimal 2-member) / (b) Pivot to data-capability / (c) Both — which path?**
>
> *Ambiguous reply = re-prompt. Auto-ratification is closed.*
