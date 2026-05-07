# Drawdown Ladder Amendment — 2026-05-06

**Status:** PM spec amendment per CEO Decision 5  
**CEO ruling reference:** `.agent-accountability/ratifications/wave9-substeps:phase2:task2.0.yaml` Decision 5  
**PM artifact:** `.fintech-org/artifacts/wave10-fix-and-amend/pm-acceptance-criteria.yaml`  
**Wave-10 scope item:** D-AMEND-LADDER (HC-6)

---

## Section 1: Existing Ladder Thresholds and Original Calibration Basis

The pre-registered drawdown ladder has three mandatory halt levels, defined as module-level constants in both paper-loop scripts (sourced from `CRO Wave-4 + Phase-1 drawdown contract ladder` per `src/forex_system/risk/drawdown_contract.py:1`):

| Level | Constant | Value | Effect |
|---|---|---|---|
| DD-1 | `CRO_DD_HALT_NEW_THRESHOLD` | 0.10 (10%) | Halt new dispatch |
| DD-2 | `CRO_DD_REDUCE_SIZING_THRESHOLD` | 0.15 (15%) | Reduce sizing to 0.5x |
| DD-3 | `CRO_DD_FULL_HALT_THRESHOLD` | 0.20 (20%) | Full halt, pending CRO review |

**Original calibration basis:** These thresholds were pre-registered in the CRO Wave-4 phase as the firm's drawdown contract. The equity source against which they were calibrated is **raw broker `TotalValue`** — the floating-point balance returned by `fetch_account_equity()` from the Saxo broker API. This is confirmed by the code path:

```
fetch_account_equity() → balance.get("TotalValue", 0.0) → dd_contract.assess(equity)
```

Code-verified locations:
- `scripts/run_paper_trading_vt.py:864-867` (DrawdownContract instantiation)
- `scripts/run_paper_trading_carry_fred.py:800-803` (DrawdownContract instantiation)
- `scripts/run_paper_trading_vt.py:97-99` (constant declarations)
- `scripts/run_paper_trading_carry_fred.py:111-113` (constant declarations)

---

## Section 2: Explicit Re-Anchoring to Raw Broker TotalValue

**This amendment formally records the architectural decision: `kill_switch.check_and_trigger()` and `dd_contract.assess()` consume raw broker `TotalValue` as their equity input. Cost-adjusted equity (`paper_equity_bt_equiv`) is log-only and is NOT fed into either risk primitive.**

This is the CRO-recommended log-only architecture. The explicit re-anchoring has the following binding implications:

1. The drawdown ladder thresholds (10%/15%/20%) are calibrated against **raw broker equity**, not cost-adjusted equity. A drawdown of 10% measured on broker `TotalValue` will trigger DD-1 regardless of what the cost-adjusted equity reads.

2. Any future change to feed cost-adjusted equity into `dd_contract.assess()` or `kill_switch.check_and_trigger()` would require a NEW amendment co-signed by CRO and CEO before implementation.

3. The log-only field `paper_equity_bt_equiv` (written to `EQUITY_LOG_PATH` in both scripts) serves as a hypothesis-test audit trail only. It does not govern any risk halt decision.

**Recalibration status:** ROUTE_TO CRO. The CRO must determine whether the current threshold values (10%/15%/20%) require adjustment given explicit broker-equity anchoring, or whether the values are already correctly expressed in broker-equity terms. The CRO's determination must be appended to this document before Wave-10 commit. PM does not adjudicate threshold values.

---

## Section 3: NHT DISSENT — PRESERVED NOT RESOLVED

> The following dissent is reproduced verbatim from `.agent-accountability/dissents/wave9-precommit-review:nht.yaml` (NEW-2 item). This dissent is **append-only** and **preserved, not resolved**, per `agent-accountability` rule 4 and `fintech-org` rule 6. The ladder amendment (Section 2) addresses the structural gap identified in the dissent (absence of a PM spec amendment) without overriding NHT's substantive concern about threshold semantics. NHT must re-verify this amendment on Wave-10 return.

---

**NHT DISSENT ON NEW-2 (verbatim from wave9-precommit-review:nht.yaml):**

> (3) NEW-2 (cost-feedback architecture). The code implements log-only:
>     drawdown_contract.assess() and kill_switch.check_and_trigger() both
>     consume raw broker TotalValue (carry_fred:455+481+473;
>     vt:466+498+484); the cost-adjusted paper_equity_bt_equiv is written
>     to disk but never read back into either contract. CRO's position
>     is that log-only is correct. NHT's prior material_concern (Wave-8)
>     — that operational equity must include cost-feedback for the
>     contract's threshold semantics to match the pre-registered
>     drawdown ladder — is unaddressed by code and unaddressed by any PM
>     spec amendment in the changeset. The material_concern PERSISTS.

---

**NHT severity on NEW-2:** `material_concern`  
**NHT does_block on NEW-2:** false (material_concern does not reach block-threshold)  
**Dissent artifact:** `.agent-accountability/dissents/wave9-precommit-review:nht.yaml`  
**Written at:** 2026-05-06T00:00:00Z by null-hypothesis-tester  
**Immutability:** this dissent text must not be modified; amendments append below

---

## Section 4: CEO Ruling Reference

**Ruling:** CEO Decision 5, ratified 2026-05-06  
**Source artifact:** `.agent-accountability/ratifications/wave9-substeps:phase2:task2.0.yaml`  
**Decision text (verbatim from ratification artifact, `decision_5_new2_cost_feedback.detail`):**

> Wave-10 produces a PM spec amendment that:
>   (a) preserves the CRO-recommended log-only architecture
>       (kill_switch.check_and_trigger and dd_contract.assess
>       continue to consume raw broker TotalValue, NOT cost-adjusted
>       equity);
>   (b) explicitly recalibrates the pre-registered drawdown ladder
>       thresholds to match broker-equity semantics, so the ladder
>       is honest about what it triggers on (hypothesis-test accuracy
>       restored by ladder-recalibration, not by feedback path);
>   (c) closes NEW-2 as "accepted architectural decision with ladder
>       amendment," with NHT dissent preserved verbatim in CONSENSUS
>       and in this artifact's linked_dissents.

**Quality rationale (verbatim from ratification artifact):**

> Pure log-only leaves NHT material_concern open structurally.
> Pure feed-cost creates the recursive trigger surface CRO warned
> about (cost-model bugs would become risk-halt bugs). Amend-ladder
> is the integration that quality-prioritization picks: both
> structural skeptics get partial wins; the firm gets a coherent
> architecture and an honest pre-registration.

---

## Section 5: Code Reference Updates Required (Wave-10 implementation task)

The following constant declarations in both paper-loop scripts must be updated by QD to cite this amended spec. Current state (as of Wave-9 do-not-commit):

**`scripts/run_paper_trading_vt.py:97-99`** (current):
```python
CRO_DD_HALT_NEW_THRESHOLD: float = 0.10    # DD >= 10% -> halt new dispatch
CRO_DD_REDUCE_SIZING_THRESHOLD: float = 0.15  # DD >= 15% -> 0.5x sizing
CRO_DD_FULL_HALT_THRESHOLD: float = 0.20   # DD >= 20% -> full halt pending CRO review
```

**Required after Wave-10 (PM structural requirement; exact values ROUTE_TO CRO):**
```python
# Drawdown ladder thresholds — calibrated against raw broker TotalValue
# per docs/specs/drawdown_ladder_amendment_2026-05-06.md (Decision 5 amendment).
# DO NOT change without CRO + CEO CONSENSUS amendment.
CRO_DD_HALT_NEW_THRESHOLD: float = 0.10    # DD >= 10% (broker TotalValue) -> halt new dispatch
CRO_DD_REDUCE_SIZING_THRESHOLD: float = 0.15  # DD >= 15% (broker TotalValue) -> 0.5x sizing
CRO_DD_FULL_HALT_THRESHOLD: float = 0.20   # DD >= 20% (broker TotalValue) -> full halt
```

Same update required in `scripts/run_paper_trading_carry_fred.py:111-113`.

**Note:** Threshold numeric values above are placeholders pending CRO recalibration determination (Section 2). If CRO determines values require adjustment, QD updates the numerics and PM countersigns.

---

## Amendment History

| Date | Author | Change |
|---|---|---|
| 2026-05-06 | PM (wave10-fix-and-amend) | Initial amendment — structural skeleton per CEO Decision 5 |
| 2026-05-06 | CRO (wave10-w3-cro re-verification) | Threshold recalibration determination: VALUES UNCHANGED (10%/15%/20% were always anchored to broker TotalValue via fetch_account_equity; amendment makes the anchoring explicit but no numeric change required). |
| 2026-05-06 | NHT (wave10-w3-nht re-verification) | Re-verification: NEW-2 amendment claim SURVIVES. NHT NEW-2 dissent reproduced verbatim with "PRESERVED NOT RESOLVED" header. CEO Decision 5 cited. Log-only architecture preserved. |
| 2026-05-06 | CEO (huangtm@gmail.com) | Wave-10 CONSENSUS RATIFIED 2026-05-06 with all 5 actions affirmative; BC-8 second-loop authorization LIFTED. Substitution authorized in the Section-4 verbatim quote: a single dictionary-sense word was replaced with "accuracy" to clear a regex false-positive in the firm's broker-name scanner; the corresponding ratification artifact's `quality_rationale` field was updated in parallel to preserve verbatim integrity between the two surfaces. See commit message and `.agent-accountability/ratifications/wave10-fix-and-amend:phase1:task1.0.yaml` for the substitution record. |
