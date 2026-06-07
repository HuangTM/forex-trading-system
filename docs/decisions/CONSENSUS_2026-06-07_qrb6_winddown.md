# CONSENSUS: QRB-6 (CB-Decision Event Study) — WIND-DOWN / Archived Near-Miss

**Status:** RATIFIED (distributed quorum: head-of-quant-research + null-hypothesis-tester)
**Track:** qrb6-winddown-2026-06-07 / Phase 1 / Task 1.0
**Ratification:** `.agent-accountability/ratifications/qrb6-winddown-2026-06-07:phase1:task1.0.yaml`
**Dissent:** none — NHT concurs (survives verdict); no dissent artifact required

---

## Decision

QRB-6 (CB-decision event study, central-bank signed-product continuation, four-bank universe
{FED, BOJ, RBA, BOC}) is **WOUND DOWN** and **archived as a documented near-miss**.

The exploratory trial **fa0f982a** found a real, in-sample, low-frequency edge (p_post2015=0.0027,
p_agg=0.0231, pooled annualised Sharpe 1.352) that fails only the conservative N_sel=3 deflation
bar (DSR=0.9070 < 0.95). The confirmatory design (trial **53981a4a**) was constructed correctly
to clear that bar at N_sel=1, but the Mathematician's power analysis — independently reproduced
by both HoQR and NHT to zero delta — is **dispositive**: at the bootstrap-valid 2030-04-07 look
(n≈120 events), power = **0.091** (9%). Reaching 80% power requires 852–7,670 events (28–256
years at the 1/3 haircut); even a 50%-coin-flip rejection requires 373 events (~12 years). No
feasible horizon changes this picture.

**Terminal verdict:** QRB-6 is a real-but-modest, low-frequency edge — in-sample significant,
fails the conservative deflation charge, and **cannot be confirmed out-of-sample on any
tradeable horizon**. It is archived as a documented near-miss; it is **NOT validated** and it is
**NOT a clean falsification**.

Trial **53981a4a** is **RETIRED as "withdrawn, pre-freeze (never tested)"** — no freeze-receipt
was cut, no return data was examined, no trial result was realized — and it does **NOT** count
toward the org-wide DSR deflation denominator. Trial **fa0f982a** (exploratory, which did realize
a result and bore its own N_sel=3 charge) remains in the denominator unchanged. The org-wide
trial counter stays at 42 spawned; 53981a4a is logged withdrawn, not completed.

**QRB-3** (runner-up): **UNCHANGED** — stays queued and independent. Its only advance trigger
was a post-2015 sub-window KILL of QRB-6, which never fired (the exploratory was AMBIGUOUS; the
confirmatory carried no post-2015 KILL branch by construction). Wind-down of QRB-6 is neither a
KILL nor a graduation and triggers no auto-advance. QRB-3 requires its own fresh pre-registration
and trial ID under separate governance.

**Confirmability lesson:** hypothesis generation must weight confirmability — (events/year ×
per-event Sharpe) must support ≥80% power (or at minimum >50% rejection power) within ≤3 years
of forward data before a structure enters the exploratory queue. This lesson is adopted into the
HoQR screening rubric for the next new-alpha wave.

---

## AMBIGUOUS → Infeasible-Confirmation Narrative

The exploratory fa0f982a (pre-reg `references/pre-registrations/qrb6_cb_event_study.md`) returned
RULE_4_AMBIGUOUS: both p-values cleanly reject (p_post2015=0.0027, p_agg=0.0231), but DSR=0.9070
falls below the 0.95 threshold under the N_sel=3 selection charge. The edge is real in-sample;
it only fails the appropriately-conservative deflation bar.

The confirmatory (53981a4a) was designed precisely to clear this bar: with N_sel=1 (no new
strategy selection occurs forward), the selection penalty legitimately vanishes and DSR defaults
to a clean test. However, the confirmatory's power at the sole bootstrap-valid look (n≈120 events,
lock date 2030-04-07) is 9%. The barrier is not the haircut choice — even at the full un-haircut
in-sample Sharpe of 1.352, 80% power needs 28 years and a 50% coin-flip reject needs 12 years.
The barrier is the sqrt(n) scaling of a genuinely tiny per-event effect (~0.085 Sharpe per event
un-haircut; ~0.028 haircut) against a sparse series (~30 verified-official event-days/yr).

The firm stopped before freeze — at the power finding — rather than cut a receipt for a
diagnostically-inert test. That is the correct decision. The authored confirmatory design is
retained on disk as a "designed, not frozen — infeasible power" record.

---

## Power Table (reproduced independently by HoQR and NHT — zero delta)

| Quantity | Haircut (1/3 × 1.352) | Full (no haircut, 1.352) |
|---|---|---|
| Per-event Sharpe (g_pp) | 0.02839 | 0.08518 |
| Power at n=120 (2030-04-07 look) | **0.091** | 0.238 |
| Power at n=180 (+6yr) | 0.103 | ~0.35 |
| Power at n=300 (+10yr) | 0.124 | ~0.43 |
| n* for 80% power | 7,670 (~256 yr) | 852 (~28 yr) |
| n* for 50% rejection | ~3,356 (~112 yr) | 373 (~12 yr) |
| Kill-switch at n=120 | 2.3936 | — |
| Kill-switch at n=300 | 1.5101 | — |

Kill-switch formula: z_{0.95}/√(n−1) × √252. Power formula: Φ(g·√n − z_{0.95}), one-sided.
Both independently derived from NormalDist primitives by all parties.

---

## Alternatives-Rejected Ledger

### A. Low-power freeze with non-punitive decision map
**Rejected.** A non-punitive decision map (non-reject = "inconclusive, never kill") makes the
test unfalsifiable: at ~91% probability of non-rejection even if the edge is real, a non-reject
is near-uninformative, and removing the kill branch means no finite outcome can retire the
hypothesis. The strategy becomes immortal by construction. The QR-authored draft's own decision
map (non-reject = KILL) avoids that trap but introduces the opposite failure at 9% power: a
structurally near-certain false KILL of a possibly-real edge. **Neither mapping is legitimate at
this power.** The fix is not to re-map; it is to not run.

Precise methodological basis (NHT refinement): the correct term is **"DIAGNOSTIC INERTNESS"**,
not "unfalsifiability." At ≤9% power, both outcomes are near-uninformative — a rare rejection is
a low-prior surprise, and a non-rejection (even if mapped to KILL) is uninformative as evidence
of no edge. A legitimately-designed sequential trial CAN carry an inconclusive branch (cf. the
carry confirmatory f2fb41fd frozen at ~34% power), but only when a horizon exists at which power
becomes adequate. Here, none does.

### B. Longer single-look horizon (+10 yr / n=300)
**Rejected as primary.** Power at n=300 is ~12% (haircut) / ~43% (full). Deferring a binary
a decade for a sub-3% power gain — the test remains diagnostically inert — is functionally
identical to wind-down except it ties up a frozen trial slot and pretends a verdict is coming.
Honest wind-down dominates. Disclosed to CEO as an elective if a lower kill bar is ever preferred;
not recommended by any party.

### C. Universe expansion (add BoE/ECB/RBNZ to reach ~70–80 events/yr)
**Rejected as a confirmatory; endorsed only as a separate future hypothesis (QRB-7).** Expanding
the bank universe would accrue events faster and is research-interesting, but it is a DIFFERENT
structure on DIFFERENT banks, changes the estimand, breaks the structural-identity predicate of
the confirmatory (qr-prereg-draft.yaml §3.3 structural-deviation VOID clause), and re-introduces
a fresh N_sel charge. It cannot confirm fa0f982a — it would be a new exploratory bet (QRB-7)
requiring aggregator-grade forward calendar + OHLCV the firm does not have verified-official.
The CB-decision continuation family may merit a future wave scoped multi-bank from the start;
that belongs in new-alpha generation, not as a rescue of QRB-6.

---

## Transparency Notes

**T1 — Confirmatory designed, not frozen.** The confirmatory (trial 53981a4a) was designed in
full — QR pre-reg draft, Mathematician power spec, QD runner spec, PM acceptance criteria, all on
disk in `.fintech-org/artifacts/2026-06-07T-qrb6-confirmatory/`. The firm stopped at the power
finding rather than freeze a diagnostically-inert test. The authored work is retained as a
"designed, not frozen — infeasible power" record and is accessible for the post-mortem record.

**T2 — QD runner machinery committed.** The QD runner infrastructure (date-window parameter,
qrb6_confirmatory receipt target, 25-test plan) is committed to the repository. It is harmless
general capability that cannot activate without a frozen receipt; it stays committed. No action
required.

**T3 — "Diagnostic inertness," not "unfalsifiability."** NHT's refinement: the precise objection
is diagnostic inertness (at ≤9% power, both outcomes are near-uninformative about the underlying
edge). The orchestrator's unfalsifiability argument is CORRECT as applied to the non-punitive
decision map option it rejected, but imprecise if generalized — the QR-authored draft's own
decision map does carry a KILL branch and is technically falsifiable. The sounder, more defensible
characterization is diagnostic inertness. This consensus uses that framing.

**T4 — Trial counter accounting.** The org-wide trial counter stands at 42 spawned. fa0f982a
(exploratory, realized a verdict) COUNTS and remains in the deflation denominator. 53981a4a
(authored but never frozen, no return data examined, no result realized) does NOT count and must
NOT be cited as "falsified" — it is "withdrawn, never tested." This is the honest accounting: the
deflation charge (BLdP) penalizes selection over realized candidate results; an un-run, un-frozen
trial produced no Sharpe that could enter any argmax. Contrast bet1 (87fa1d23): that trial was
run, regenerated, and FALSIFIED on a fired gate — it DOES count because it produced a realized
verdict. The discriminating rule is "was a result realized," and it cleanly separates the two
cases.

---

## Signature Table

| Role | Artifact | Decision | Status |
|---|---|---|---|
| head-of-quant-research | `.fintech-org/artifacts/2026-06-07T-qrb6-confirmatory/hoqr-winddown-qgr.yaml` | approve (ratify wind-down) | SIGNED |
| null-hypothesis-tester | `.fintech-org/artifacts/2026-06-07T-qrb6-confirmatory/nht-winddown-honesty.yaml` | survives (wind-down is honest call) | SIGNED |

No dissent artifact. NHT concurs with the wind-down. NHT's methodological refinement
(diagnostic inertness framing; 53981a4a must be "withdrawn, never tested") is **adopted**
into this consensus — it does not constitute a dissent; it strengthens the basis.

---

## Knowledge Gaps Surfaced

**KG-1 (Actionable — adopt into HoQR rubric):** Whether a materially-stronger-per-observation
statistic on the same post-2026-04-06 CB-decision data (e.g. a panel cross-event t-stat,
windowed drift-magnitude, or regression with event-level covariates) could lift power into a
confirmable band was NOT formally costed out. NHT judges it low-probability (a 0.085 per-event
Sharpe on a sparse series is hard to rescue by re-statisticking), and regardless, any such change
constitutes a NEW pre-registered structure with its own N_sel charge — it cannot rescue 53981a4a.
It would be QRB-7, a new bet. The firm has not proven it infeasible; only that the signed-product
continuation statistic used in QRB-6 is.

**Screening rubric (adopt now):** Future hypothesis generation must score CONFIRMABILITY up front.
Pre-screen formula: estimate forward run-rate and haircut effect → compute n*(power) and years →
if years > 3 at 50% power, the hypothesis is research-interesting but NOT validatable on a
tradeable horizon; route to a higher-frequency variant or drop. This screen would have flagged
QRB-6 at generation time.

---

## Next Steps

1. **CEO: push authorization.** HEAD is 1 ahead of origin (commit 62421b6); push the committed
   QD runner and confirmatory design artifacts. This is CEO-reserved.
2. **CEO: confirmability rubric adoption timing.** Adopt the pre-screen rubric into the HoQR
   new-alpha-wave checklist now, or defer to the next kickoff — CEO's call.
3. **QRB-3:** No action required. Remains queued/independent. Advance requires its own fresh
   pre-reg, trial ID, and quorum under separate governance when the firm elects to pursue it.
4. **Trial registry:** Update 53981a4a entry to status `withdrawn-pre-freeze (never tested)`.
   fa0f982a remains `COMPLETE / RULE_4_AMBIGUOUS`.
