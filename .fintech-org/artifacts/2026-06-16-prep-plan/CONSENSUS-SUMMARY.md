# Consensus on: Define per-role deliverables to maximize EV of incoming 1h OHLCV data while backfill runs; honest about alpha base rates.

**Status:** awaiting-ratification
**Full audit:** see `./CONSENSUS.md`
**Session:** `.fintech-org/artifacts/2026-06-16-prep-plan/`

## Decision (one paragraph)

"Learning their domain" is NOT the lever — the roles already hold expert skills and the firm has run 48 rigorous trials with zero validated alpha. The scarce input is a *confirmable edge*, not knowledge. The productive use of the wait is to PRE-BUILD RIGOR: each role produces durable, repo-checkable artifacts (test harness, gate YAML, cost-model spec, frozen rubric, hypothesis shortlist, CPCV/DSR design, null battery) so the instant clean 1h data lands, confirmable intraday research can begin with no scramble. NO ONE promises the system will earn money. NHT's honest base rate is ~15% that the firm finds ≥1 validated intraday strategy this cycle.

## Top-3 risks the CEO should know

1. **F-001 — CTO bar-count gate rejects all clean data; severity: blocking; source: principal-review.yaml.** `min_bars_2yr: 17520` exceeds the achievable 24x5 bar count (~13,770 for 2yr). Every clean parquet would be EXCLUDED before research begins.
2. **NHT-D5 — Data may be DOA (throttling, zero volume, unverified spread column); severity: high; source: nht-dissent.yaml.** Prior run retrieved ~1.6% (2/12 pairs) due to IP throttling. A wrong spread column silently corrupts all TCA — the QRB-6 failure mode in a new field.
3. **CRO KG-4 — Rollover-aware swap and EXCLUDE-gate are SPEC, NOT CODE; severity: high; source: cro-risk-gates.yaml.** `holding_cost` pro-rates swap by hours (the banned anti-pattern). No per-bar exclusion gate exists yet. 1h cost realism is unenforceable until QD builds both items.

## Dissents (one-liner each; full text in CONSENSUS.md)

- **NHT (severity: approve-with-dissent; D1–D6 all load-bearing):** D1 — infrastructure theater is the firm's own kill-criterion re-armed; require every artifact to name the decision it gates ... D2 — pre-register NOW but shortlist MUST be expandable after blind structural data report; fishing is the worse error ... D3 — intraday likely MOVES the wall to ~1.5–3yr, not breaks it; do not sell "ceiling removed" internally ... D4 — honest base rate ~15% (10–20%), empirical prior 0/48; I will not round up ... D5 — data may be DOA (throttling, zero volume, unverified spread column); require LAND/PARTIAL/MISSING status + never-lands branch + spread-correctness check ... D6 — naive nominal-N counting re-creates the broken-gate failure in a new costume; effective-N must be ACF-corrected. → see CONSENSUS.md §Dissent for verbatim text.
- **CRO (severity: KG-4 is blocking; does_block: true for 1h trials):** cost-coverage gate and rollover-aware swap are BUILD items, not present code; no 1h trial may freeze until QD delivers both.

## Open items requiring CEO acknowledgment

- F-001 (blocking; §Blocking conditions): Fix `min_bars_2yr` in `config/data_quality_gates_1h.yaml` before gate runs — current value excludes every clean pair.
- CRO KG-4 (blocking; §Blocking conditions): QD must build EXCLUDE-gate callable + rollover-aware holding_cost before any 1h trial freezes.
- F-004 + F-005 (major; §Sequenced workflow): Blind structural data-quality report (Step 5) and spread-correctness gate (Step 3) added to the workflow; H1 pre-registration slot remains BLOCKED until measured data clears G1.
- Never-lands terminal branch (Step 0; §Sequenced workflow): If Dukascopy throttling means data never arrives clean, the plan halts and surfaces to CEO — not assumed away.

## Skill gaps logged this session (N=9)

- HoQR: Empirical decay rate of intraday FX session-open momentum post-2020 (H1 G6 kill-risk)
- HoQR: Cross-pair signal correlation (rho_bar) for pooled session-momentum — H1 effective-N make-or-break
- HoQR: Whether single CB decision yields ~2 semi-independent sub-events (H2's only path to ≤2yr)
- CTO: Dukascopy 1h bar density per pair (min_bars thresholds are pre-data estimates)
- CTO: Per-pair typical spread_median_pips — CTO-D2 spread ceilings need CRO cross-check
... and 4 more — see CONSENSUS.md § Knowledge gaps surfaced.

## Ratification prompt

> **Do you approve this consensus and authorize follow-on execution dispatches? (yes / no / revise <X>)**

Suggested revise targets: `revise f-001` `revise workflow` `revise blocking-conditions` `revise nht-dissent`

---
*This SUMMARY is for routine ratification. Read full `CONSENSUS.md` for substance. The full doc is the audit-trail source-of-truth; the SUMMARY is convenience.*
