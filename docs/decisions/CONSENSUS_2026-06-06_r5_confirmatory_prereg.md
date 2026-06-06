# CONSENSUS: R5 Confirmatory Pre-Registration — vol_target_carry:USDJPY
**Track:** r5-confirmatory-2026-06-06 | **Phase:** 1 | **Task:** 1.0
**Status:** RATIFIED-FOR-FREEZE (awaiting CEO ratification before freeze-receipt is cut)
**Date:** 2026-06-06 | **Trial ID:** f2fb41fd

---

## Decision Paragraph

The confirmatory pre-registration for vol_target_carry:USDJPY (trial f2fb41fd) is **ratified-for-freeze** by quorum (HoQR final QGR approve + Mathematician rework1 approve; PR cycle-2 APPROVE with all 10 findings closed; NHT SURVIVES at severity=concern, does_block=false). The document freezes a confirmatory-only, single-series kill test on genuinely unsnooped post-2026-04-06 USDJPY data, absorbing the R5 36-cell selection burden in N_conf=6. Two looks are scheduled: interim at **2028-10-06** (OBF z1=2.537988, p ≤ 0.005575) and terminal at **2031-04-06** (joint-exact z2=1.662107, p ≤ 0.048246); the terminal look is binding and irrevocable — outcome 2 (KILL) is forced at any power level, outcome 4 (CONTINUE) is explicitly unavailable. Two-look power ≈ 0.34 at SR_plan=0.554361; **the expected terminal outcome is wind-down.** The design buys a cheap option on five years of unsnoopable data, not a likely pass. No capital is authorized at any branch; a PASS routes only to an observe-only paper canary under a fresh ratification with a new trial_id. The post-consensus freeze sequence (commit → `--target confirmatory --cut` → receipt commit → push) is pre-authorized by CEO standing instruction this session; STEP/look execution in 2028/2031 requires its own runner-receipt quorum and CEO acknowledgment at that time.

---

## Frozen Parameter Table

| Parameter | Frozen Value | Provenance / Note |
|---|---|---|
| **Strategy structure** | vol_target_carry:USDJPY | R5 k* argmax (T_SPA max-statistic) |
| **Trial ID** | f2fb41fd | New; never reusing 576746aa; org counter 39 |
| **min_carry (AS-EXECUTED)** | −∞ (strategy default) | MATERIAL: config −0.10 was NOT in effect; filter was no-op; see F-001 |
| **Hold-out window start** | strictly after 2026-04-06 | R5 common index end; zero bar overlap |
| **Look 1 date** | 2028-10-06 | Interim (OBF) |
| **Look 2 date (terminal)** | 2031-04-06 | Terminal; binding; forced outcome |
| **T_holdout (terminal)** | 1260 trading days | at +5yr, 252 days/year |
| **Information fraction t₁** | 0.5 (exact) | 2.5yr / 5yr |
| **N_conf** | 6 | Selection absorption: R5 eff-dim 4 + carry prior 3 − 1 overlap = 6 |
| **dispersion (frozen from R5)** | 0.426385 | sqrt(Var[SR_n]) over {0.80, 0.197}; 2-obs, sample ddof=1 |
| **bracket(N=6)** | 1.300141 | scipy: (1−γ)·Φ⁻¹(5/6) + γ·Φ⁻¹(1−1/(6e)) |
| **SR0_ann (confirmatory)** | 0.554361 | scipy: 0.426385 × 1.300141 |
| **SR0_pp (confirmatory)** | 0.034921 | scipy: 0.554361 / √252 |
| **z1 (OBF look-1)** | 2.537988 | scipy: Φ⁻¹(1 − 0.005575) |
| **z2 (joint-exact terminal)** | 1.662107 | scipy bivariate brentq; triple-verified (CDF + dblquad + 5M MC); joint α = 0.050000 |
| **Operative p threshold (look 1)** | 0.005575 | Φ(−2.537988) |
| **Operative p threshold (look 2)** | 0.048246 | Φ(−1.662107) — NOT the incremental spend 0.044425 |
| **K (bootstrap resamples)** | 10000 | Tighter than R5's 5000 |
| **master_seed** | 924033 | RULE-EXACT: int('f2fb41',16) mod 1e6 = 924033; hand-hex value 924289 was wrong (superseded) |
| **DSR threshold** | ≥ 0.95 | |
| **kill_switch_threshold** | 1.2906 (brentq: 1.290641) | Min ann. Sharpe on hold-out to clear DSR ≥ 0.95 at SR0_pp=0.034921, N_conf=6, T=1260 |
| **var_term (at kill, self-consistent)** | 1.001053 | brentq fixed-point; NOT assumed = 1 |
| **Two-look power (SR_plan=SR0)** | 0.340 | Upper bound; iid assumption; signal autocorrelation will reduce |
| **rho (increment corr)** | √0.5 = 0.707107 | Cov(Z1,Z2) = √(t₁/t₂) = √0.5 |
| **Spending function** | Lan-DeMets sfLDOF, one-sided α=0.05 | |
| **Periods per year** | 252 | |
| **HAC estimator** | NW Bartlett, bandwidth = max(L−1,1) | Politis-White auto L, univariate (not multivariate as in R5) |
| **scipy required** | True | No erf approximation fallback; TECHNICAL_FAILURE if scipy unavailable |
| **entry_delay_bars** | 1 | Sacred no-lookahead invariant |
| **cost_model** | RealisticCostModel USDJPY spread 1.0/slip 0.5/comm 0.5/swapL 0.8/swapS −1.5 | |
| **R5 comparison** | SR0_ann 0.363623 (N=3) → 0.554361 (N=6, +52%); kill 0.767 → 1.2906 | Stricter on both axes |

---

## Finding/Rework Ledger

### Principal Reviewer Findings (PR cycle-1 → cycle-2)

| ID | Severity | Finding | Resolution | Status |
|---|---|---|---|---|
| **F-001** | BLOCKING | min_carry AS-EXECUTED identity: strategy ran at −∞ (no carry filter), NOT config −0.10; original doc mis-pinned | §2.2 re-pins min_carry=−inf with 16-row provenance table; §1.3 cond.1 VOIDs any variant_params override; three coincident-value mis-attributions corrected | CLOSED |
| **F-002** | Major | Operative look rule stated inconsistently: look-2 threshold was 0.044425 (incremental spend) but should be Φ(−z₂) = 0.048246 | §3.3 elects operative rule p_j ≤ Φ(−z_j); look-2 threshold corrected to 0.048246; 0.044425 retained as alpha-budget figure only | CLOSED |
| **F-003** | Major | Receipt tool --target not parameterized; r5 and confirmatory receipts shared a single path | cut_freeze_receipt.py refactored to --target r5\|confirmatory; write-once guard per-target; confirmatory field-spec matches doc; r5 target behavior preserved byte-identical | CLOSED |
| **F-004** | Significant | No-peek provenance-bound adjudication not specified for bound breach at look time | §3.4 adds frozen no-peek provenance-bound adjudication: two-source price/rate verify → logged bound-only amendment, look PROCEEDS; non-confirmable → TECHNICAL FAILURE | CLOSED |
| **F-005** | Significant | No supplementary runner-receipt mechanism; original receipt claimed to record a not-yet-existing runner | §2.3 adds write-once RUNNER-RECEIPT mechanism (quorum-gated HoQR+Math, NHT may dissent; cut before 2028-10-06; refuse-to-overwrite; back-ref SHA-256 of original receipt) | CLOSED |
| **F-006** | Moderate | No guard preventing look-time runner from reusing r5_decision's R5-only SR0_PP literal (0.022906) | r5_decision.py: CROSS-TRIAL CONSTANT WARNING docstring + R5-ONLY inline guard at SR0_PP literal; test pins sr0_pp=0.034921 in confirmatory field-spec; sr0_note field in receipt | CLOSED |
| **F-007** | Observation | N_conf=6 election wording | Accepted as-is: disclosed as conservative ceiling of admissible band for a kill test | CLOSED |
| **F-008** | Observation | "bit-for-bit" mirroring of R5 SPA overstates correspondence | §1.3 wording corrected: same statistic family and HAC conventions; univariate Politis-White block-length vs R5 multivariate; zero "bit-for-bit" remaining | CLOSED |
| **R-001** | Rework | Seed adjudication: hand-hex 924289 wrong; rule-exact int('f2fb41',16) mod 1e6 = 924033 | Doc §5 FROZEN, tool _TARGETS, test _EXPECTED_MASTER_SEED all updated to 924033 with drift disclosed | CLOSED |
| **R-002** | Rework (cosmetic) | test_confirmatory_freeze_receipt.py:288 docstring reads "must be 924289" while assertion correctly checks 924033 | Cosmetic; assertion correct; test passes | CLOSED (cosmetic) |

### NHT Audit Finding

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| **NHT F-1** | Material (non-blocking) | Runner does not exist; r5_decision.compute_dsr_gate hardcodes SR0_PP=0.022906 (R5 N=3 literal); dsr.py carries scipy-erf approximation fallback | Contained by: doc freezes correct SR0_pp_conf=0.034921 and kill_switch_threshold=1.2906 verbatim; VOID-on-mismatch + refuse-without-receipt + behavior-equivalence pin all attach at receipt. REQUIRED (non-blocking): freeze-receipt MUST pin SR0_pp_conf=0.034921 as the literal the runner injects (NOT compute_dsr_gate's 0.022906) and MUST state the runner uses the r5_decision scipy-hard path |

---

## NHT Dissent-Statement (VERBATIM — append-only, never edited)

```
NHT POSITION ON THE R5-CONFIRMATORY PRE-REGISTRATION (append-only; preserve verbatim in CONSENSUS):

The confirmatory pre-reg SURVIVES my audit and is freezable as-is. It is an honest, binding,
confirmatory-ONLY test of the single pre-specified structure vol_target_carry:USDJPY on genuinely
unsnoopable post-2026-04-06 data, and it honors every condition the frozen R5 map (§5 outcome 4 /
§7.3.6 RULE 4) attaches to a confirmatory spawn: a NEW trial_id (f2fb41fd, registered, never reusing
576746aa), the R5 36-cell selection burden ABSORBED into the confirmatory honest-N, and NO capital /
NO family re-open / NO exploration.

On the axis the Mathematician flagged for MY adjudication — the N_conf=6 selection charge — the
polarity is the OPPOSITE of the R5 problem I caught and the point chosen is honest. BLdP SR0 is
strictly increasing in N (R5 N=3 -> SR0_ann=0.363623; conf N=6 -> 0.554361, +52%). In R5 I flagged
N=2-at-the-FLOOR as anti-conservative; here the Mathematician elected the CEILING (6) of the [2,6]
band — the STRICTEST, most-skeptical gate, the safe-if-wrong direction for a kill test. The
no-double-count construction (effective-selection-dim 4 + prior-honest-N 3 − 1 shared-idea overlap = 6)
is a disclosed judgement that errs toward MORE charge; I accept it. I cannot build an exploit where a
higher N_conf yields a false PASS — higher N only makes PASS harder.

The clean-hold-out-vs-selection adjudication is correct and is the crux: clean future data removes the
in-sample point-estimate overfit but NOT the multiplicity of the selection EVENT, so the selection is
charged exactly once, in the right place (the DSR SR0 benchmark), while the bootstrap-t p carries the
clean-data evidence. Two distinct AND-gated hurdles for PASS; no double-charge, no under-charge. The
z2=1.662107 joint-OR boundary is scipy-exact and triple-verified (joint alpha=0.050000); the
kill_switch_threshold=1.2906 is correctly STRICTER than R5 for two compounding reasons (higher N_conf,
smaller T_holdout) and is NOT copied from R5. The two-look OBF schedule is canonical Lan-DeMets sfLDOF
(I confirmed the spending-function form and the sqrt(0.5) increment correlation against the source).
The final look is genuinely TERMINAL: I searched for "extend / one more look / re-parameterize after a
near-miss" and found NO such branch — outcome 2 (KILL) is forced at look 2 at any power level, outcome 4
(CONTINUE) is explicitly unavailable at the final look, and the pass destination is an observe-only
paper canary under a fresh ratification with NO capital and a NEW trial_id, which is NOT a disguised
CONTINUE. The advisory (non-binding) futility leaks no optionality in the dangerous direction. The
no-peek interim state is mechanically credible (raw-price provenance check only; never instantiates the
return series or any statistic). Power ~0.34 is LOW, honestly disclosed as an upper bound, and correctly
bound to KILL-with-caveat rather than a third door — the expected terminal state is wind-down.

I record ONE material and five lesser findings, NONE of which block the freeze:

(F-1, MATERIAL) The look-time RUNNER DOES NOT YET EXIST, and the existing DSR code is a trap for it:
r5_decision.compute_dsr_gate hardcodes SR0_PP=0.022906 (the R5 N=3 value) as a FROZEN LITERAL, not the
confirmatory 0.034921; and the canonical dsr.py carries a scipy-ImportError erf approximation fallback
that the pre-reg's "scipy REQUIRED, no approximation" pin forbids. A look-time runner that reuses
compute_dsr_gate would under-deflate (R5's lower SR0), and one that imports raw dsr.py could silently
approximate. This is a FUTURE implementation risk, not a defect in the frozen spec — the document
freezes the CORRECT SR0_pp_conf=0.034921 and kill_switch_threshold=1.2906 verbatim, and
VOID-on-mismatch + VOID-on-drift + refuse-without-receipt + the behavior-equivalence pin all attach at
the receipt. I REQUIRE (as a recommendation that does not block the freeze) that the freeze-receipt pin,
NOW, the literal SR0_pp_conf=0.034921 the runner must inject (explicitly NOT compute_dsr_gate's 0.022906)
and state the runner uses the r5_decision scipy-hard path (no dsr.py erf fallback). Pin it now so the
look-time QD in 2028 cannot reach for the R5 literal.

(F-2..F-6, minor/note) The z2 joint-OR convention is a defensible election (the more-spending of two
admissible conventions, but dominated by the binding DSR gate, so no false-PASS path); advisory futility
is correct; no-peek is mechanically credible; power honesty is coherent; the unfrozen-DOF sweep is clean
at the spec level (seed/K/estimators all pinned; the only true unfrozen DOF is the runner, F-1). One
cosmetic: the Section 5 seed-derivation prose has a garbled false-start sentence, but the frozen rule and
value (924289) are unambiguous.

CALIBRATION: I REJECTED any instinct to escalate F-1 to material_concern+. My binding rule is that
material_concern+ applies ONLY if the document must NOT freeze as-is — and F-1 is a look-time
implementation hole fully contained by the receipt interlock that attaches AT freeze, not a defect in
the frozen text. The spec is internally consistent, the selection charge is honest and conservative, the
terminal look is binding, the no-peek is credible, and the expected outcome remains wind-down. Over-
rejecting a spec this disciplined would itself be a calibration failure. I sign as SURVIVES, severity
=material_concern is NOT warranted; I record severity=concern with the single one-sentence freeze-receipt
pin (F-1) recommended at or before the receipt cut.
```

*Severity: concern. does_block: false. Dissent artifact: `.agent-accountability/dissents/r5-confirmatory-2026-06-06:phase1:task1.0:null-hypothesis-tester.yaml`*

---

## Six Transparency Notes

**1. The confirmatory identity correction (F-001).** The R5 survivor executed `min_carry=-inf` (strategy default), NOT the config's −0.10. The carry filter (which runs only if `min_carry > -inf`) was a no-op throughout the entire R5 backtest. The doc now pins AS-EXECUTED with a 16-row provenance table distinguishing `config_via_variant_exec` fields from `strategy_default` fields. Three further provenance mis-attributions (target_vol, vol_window, leverage_cap_signal_clip — coincidentally equal to config values) are corrected: they are strategy defaults, not config-sourced. Only min_carry is materially discrepant. The confirmatory runner MUST pass no `variant_params`, reproducing `min_carry=-inf` exactly.

**2. The seed adjudication.** §5 frozen RULE: `int('f2fb41',16) mod 1e6`. The hand-computed value 924289 (presented as the arithmetic result in the original draft) was wrong: `int('f2fb41',16) = 15924033`, and `15924033 mod 1000000 = 924033`. The rule-exact value 924033 is now in doc §5 FROZEN, the `_TARGETS["confirmatory"]["fields"]["master_seed"]` in `cut_freeze_receipt.py`, and `_EXPECTED_MASTER_SEED` in `test_confirmatory_freeze_receipt.py`. QD and the orchestrator independently verified. Mathematician's final QGR ratifies. The QD rework1 artifact (qd-conf-rework1.yaml) stated 924289 pending adjudication — the live code now carries 924033; the QD artifact is superseded.

**3. Constant-precision discipline.** Four instances of hand-arithmetic drift corrected to scipy-exact this track: (a) z2 election 1.687 → 1.662107 (1.48% divergence; bivariate joint criterion satisfied; NHT adjudicated the polarity as safe); (b) bracket_6 1.299649 → 1.300141; (c) SR0_ann 0.554150 → 0.554361; (d) kill_switch 1.291 → 1.2906 (brentq-exact 1.290641). 26 total substitutions applied to the PART II mathematician sections. The operative look-2 p-threshold correction (0.044425 → 0.048246) is a direct consequence of the z2 election and the Φ(−z_j) operative rule: the incremental spend 0.044425 is an alpha-budget figure, not the reject threshold.

**4. The known gap, contained.** The look-time runner does NOT exist yet — this is deliberate, not an oversight. Containment: (a) the doc freezes SR0_pp_conf=0.034921 and kill_switch_threshold=1.2906 verbatim; (b) VOID-on-freeze-mismatch and VOID-on-parameter-drift attach at the freeze-receipt; (c) the supplementary write-once RUNNER-RECEIPT mechanism (§2.3) is quorum-gated (HoQR+Math sign, NHT may dissent) and must be cut and committed **before 2028-10-06**; (d) behavior-equivalence pin requires byte-identical return series on a shared sub-window vs the reference commit 350cbd4. The freeze-receipt MUST explicitly pin SR0_pp_conf=0.034921 as the literal the runner injects (NOT compute_dsr_gate's 0.022906) and state use of the r5_decision scipy-hard path.

**5. Honest power disclosure.** Two-look power ≈ 0.34 at SR_plan=0.554361. This is LOW and is disclosed as an upper bound (iid assumption; monthly-stale signal autocorrelation will reduce effective n further). Power is planned at the selection-deflated SR_plan=SR0_ann_conf=0.554361, not the snooped 0.767 (which would overstate sensitivity). The design is expected to result in KILL/wind-down at the terminal look; a non-rejection is forced as KILL-with-caveat at any power level and does not license continued spend. "Expected outcome = wind-down" is stated honestly in the pre-reg preamble (§1.2).

**6. Deferred to CEO.** The post-consensus freeze sequence (commit → `cut_freeze_receipt.py --target confirmatory --cut` → receipt commit → push) is pre-authorized by CEO standing instruction this session. STEP/look execution in 2028/2031 requires its own runner-receipt quorum plus CEO acknowledgment at the time of each look. The carry family is in observe-only state during the interim; no new research spend on the carry family is authorized.

---

## Signature Table

| Role | Decision | Artifact Path |
|---|---|---|
| **PM** (acceptance criteria) | approve | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/pm-acceptance-criteria.yaml` |
| **HoQR** (rework-1) | approve | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/hoqr-conf-rework1.yaml` |
| **HoQR** (final QGR) | approve | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/hoqr-conf-final-qgr.yaml` |
| **Mathematician** (z2 election + constants) | sound | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/mathematician-z2-election.yaml` |
| **Mathematician** (operative rule rework-1) | sound | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/math-conf-rework1.yaml` |
| **Mathematician** (final QGR) | approve | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/math-conf-final-qgr.yaml` *(path; orchestrator validates before ratification)* |
| **QD** (constants confirmation) | implemented-and-verified | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/qd-constants-confirmation.yaml` |
| **QD** (rework-1 implementation) | implemented-and-verified | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/qd-conf-rework1.yaml` |
| **NHT** (audit) | survives (severity=concern, does_block=false) | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/nht-conf-audit.yaml` |
| **PR** (cycle-1) | needs-work (8 findings) | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/pr-conf-review.yaml` |
| **PR** (cycle-2) | approve | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/pr-conf-cycle2.yaml` |
| **PM** (consensus draft) | approve | `.fintech-org/artifacts/2026-06-06T-r5-confirmatory/pm-conf-consensus.yaml` |
| **Pre-registration document** | (subject of ratification) | `references/pre-registrations/r5_confirmatory_vol_target_carry_usdjpy.md` |

---

## Knowledge Gaps Surfaced

None.

---

## Next Steps

1. **CEO ratification** of this consensus (required before the freeze-receipt is cut per the PM acceptance criteria and the autonomous-quorum charter).
2. **Freeze sequence** (pre-authorized by CEO standing instruction this session):
   - Commit the settled pre-reg document (if not already committed).
   - Run `python scripts/cut_freeze_receipt.py --target confirmatory --cut` to write the write-once receipt.
   - Commit the receipt.
   - Push.
   - The receipt MUST pin `sr0_pp_conf=0.034921` (NOT `0.022906`) and state the runner uses the r5_decision scipy-hard path per NHT F-1.
3. **2028-10-06** (look 1): before this date, the RUNNER-RECEIPT must be cut (quorum-gated HoQR+Math, NHT may dissent). Look execution requires a new CEO ack.
4. **2031-04-06** (look 2, terminal): same governance. Outcome is binding KILL or PASS-to-canary.
5. **Carry family status**: observe-only during the entire interim. No new research spend authorized without a separate pre-registration.
