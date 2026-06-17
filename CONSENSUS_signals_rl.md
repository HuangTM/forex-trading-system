# CONSENSUS — Classic Signals & RL Feasibility
**Track:** signals-rl | **Phase:** 1 | **Task:** 1.0
**Authored by:** PM / Chief of Staff (fintech-org)
**Timestamp:** 2026-06-17T06:00:00Z
**Status:** AWAITING CEO RATIFICATION

---

## Decision

**Classic signals (MACD/RSI/Bollinger):** The disciplined-basket design approach is correct in
structure. The FIRST basket (QR artifact) is **NOT freeze-ready.** Principal Reviewer returned a
package-level REJECT on a blocking finding (dishonest deflation denominator, N=54 understates true
N ≈ 30–200+) and four major design defects. NHT independently dissented on the same N issue.
Proceeding to freeze the QR basket as written would produce a pass bar that is too lenient,
potentially manufacturing a spurious positive finding on the upside branch — the exact failure the
DSR discipline exists to prevent.

**RL:** UNANIMOUS verdict — PREMATURE-BEHIND-DATA-WALL. ML-Researcher vetoed build-now;
HoQR ranked RL #3; NHT classified it a TRAP on effective-N grounds; CRO issued conditional-NO
without an outer deterministic risk envelope. Deliverable achieved: RL feasibility + eval
methodology design doc is banked. A named data-milestone gate must be set before any RL build is
authorized. No RL was trained.

**Priority (firm-unanimous):** DATA-CAPABILITY — breadth (more pairs at ≤1h) + true bid/ask
spread data — ranks #1 by every role. It burns zero deflation slots and attacks the binding
constraint.

**Governance status:** Design-only task; no live capital, no charter/vendor/role edits — no
forbidden-interim actions. However, PR's BLOCKING finding, NHT's formal DISSENT, and
ML-Researcher's BUILD-NOW VETO require **explicit CEO acknowledgment** before any follow-on
spend. Status: AWAITING RATIFICATION.

---

## North-Star Trace

`north_star_trace: [O1, O2]`

The honest negative-evidence result (if the basket is reworked and run) serves O2 (maximize
alpha/profit per unit research cost; a clean FAMILY_KILL defensibly closes the open question).
Enforcing the correct deflation denominator and refusing to freeze an under-deflated pre-reg
serves O1 (safety / audit integrity / pre-registration discipline). Data-capability acquisition
serves both: O2 (raises alpha ceiling) and O1 (more data reduces the data-assumption risk the CRO
flagged as the binding gap).

---

## Per-Role Positions

### Head of Quant Research (HoQR)
**Decision:** APPROVE-WITH-CAPACITY-LIMIT

**Ranking:** C (data-capability) > A (capped classic basket, ≤4 members) > B (RL design doc only).

Trial 48 is load-bearing: the overnight-MR edge was REAL (+3.41 gross pips/trade, 55.2% hit-rate)
and died because the 7.5-pip round-trip cost is ~2.2x the gross edge. This is not a signal
problem — it is a frequency × cost × breadth problem. Data-capability (C) burns ZERO deflation
slots and raises the ceiling for every future trial. Classic basket (A) is worth a SMALL, capped
burn for honest negative information, not for expected positive alpha. A disciplined ≤4-member
fixed basket converts the open "did we try MACD/RSI?" question into pre-registered, deflation-
corrected evidence. RL (B) cannot manufacture gross edge the tape does not contain; 31k bars on
a single regime-poor pair is the wrong arena. RL build deferred to AFTER data-capability
milestone.

Recommended basket (4 members): A1 MACD-cross-trend (MACD not yet in registry — downstream
pre-condition), A2 BB-band-fade (cost-suspect control), A3 RSI-extreme-reversion (cost-suspect
control), A4 EMA50/200-cross (slow trend). A1 and A4 are the only members with a non-zero
a-priori path through the 7.5-pip wall. A2 and A3 serve as cost-wall generalization controls —
their kills are the load-bearing negative evidence.

If CEO wants minimal burn: 2-member basket (A1, A4) at the cost of forfeiting the generalized
cost-wall negative result.

**Citation:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/hoqr-prioritization.yaml`

---

### Quant Researcher (QR)
**Decision:** APPROVE (self-declared) | REJECTED by PR (package-level)

A 6-member basket (M1 RSI-MR, M2 BB-MR, M3 MACD-trend, M4 MA-cross-slow, M5 momentum-breakout,
M6 RSI-session-filtered) on EURUSD 1h. DSR denominator stated as N=54 (48+6). Modal expected
outcome declared: FAMILY_KILL (honest expectation). M6 nominally the most likely survivor
(session-filtered RSI, tighter in-session spreads). M3 (MACD) flagged as downstream-gated on
implementation + no-lookahead test.

**Citation:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/qr-classic-basket-prereg.yaml`

**Status:** REJECTED. See PR Findings section.

---

### ML Researcher (MLR)
**Decision:** VETO (build RL now)

PREMATURE-BEHIND-DATA-WALL. Binding constraint: ONE price path = ONE realization of history. RL's
requirement — near-unlimited interaction with a resamplable MDP — is structurally absent. The
RL-binding independent sample count is not 31,019 bars (N_eff_returns ≈ 31,018 for raw returns)
but the number of independent macro-regime realizations: ~6–10 (five annual vol regimes:
2021=5.6%, 2022=10.6%, 2023=7.5%, 2024=6.2%, 2025=7.9%; one ZIRP→hike→cut arc). You cannot
learn a generalizable policy from ~10 seen regimes.

Effective-N for an RL search: architectures × reward variants × feature sets × HP configs × seeds
≈ 4,800 floor (modest) to 10^5 realistic. DSR bar rises accordingly: ~2.20 annual SR at N=5,000;
~2.70 at N=10^5. Combined with the same 7.5-pip cost wall that produced DSR=0.00 at trial 48.

What flips it to feasible: multi-pair intraday (≥6 of 12 pairs at ≤1h) to multiply independent
regime realizations; true bid/ask spread column (currently absent — parquet cols: open, high, low,
close, volume, datetime); leak-proof cost-inside simulator.

Eval methodology if pursued (banked): combinatorial-purged walk-forward (standard CPCV breaks for
sequential RL: trajectory state + cross-fold gradient coupling), retrain each step, purge ≥
architecture-imposed memory bound (pre-declared, NOT data-derived), embargo on vol-autocorr scale
(|return| ACF lag1=0.247, persistent to lag24; ≥ several days). DSR at org-wide N + full RL
multiplicity. ≥6 pre-declared regime buckets, DSR>0 in ≥3 to pass. One never-touched holdout,
burned once. Forward shadow observe-only confirmation gate.

**Citation:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/mlr-rl-feasibility.yaml`

---

### Null-Hypothesis Tester (NHT)
**Decision:** DISSENT (formal)

**Dissent artifact:** `.agent-accountability/dissents/signals-rl:phase1:task1.0:null-hypothesis-tester.yaml`

**NHT DISSENT TEXT (VERBATIM — append-only, never paraphrased):**

> I dissent against treating either claim's headline framing as admissible. CLAIM A understates N
> by logging only "48 + basket-size": if the K members were selected from a variant grid (and
> classic indicators ARE families of variants), the honest denominator is 48 + grid-size, not 48+K,
> and the cost wall makes the expected cost-dominated fraction ~>=70% (the trial-48 pattern). CLAIM B
> is structurally a TRAP as stated: "trained on 5 years" reports the survivor of a 10^3-10^5 search
> as if N=1, on a single price path, against a 7.5-pip cost that already buried a REAL edge. Neither
> is noise-confirmed-dead (a pre-registered single classic member could clear ~1.75), but neither
> survives as currently framed. Required before any spend: pre-registration with honest effective-N
> logged to trials.jsonl, net-of-7.5-pip economics, and the null controls above on purged walk-forward.

**DSR Bar computation (NHT):**
- N=48 → bar ~1.75 annual SR
- N=49..56 (48+K=1..8) → 1.750..1.773 (K-inflation is logarithmic, COSMETIC, +0.02 SR total)
- N~5,000 (modest RL search) → ~2.20 | N=10^4 → ~2.46 | N=10^5 → ~2.70

**Honest prior on basket:** ~>=70% of a <=8 member basket expected cost-dominated. P(>=1 member
clears member-DSR>0.95 net): ~10–20%. Verdict on basket: STRETCH. Verdict on RL-as-framed: TRAP.

**Citation:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/nht-signals-rl-multiplicity.yaml`

---

### CRO
**Decision:** SIZE-REDUCED (size_multiplier: 0.25; min gross edge 11.25 pips)

Cost floor is the binding risk for both workstreams. Min gross edge gate: 11.25 pips (7.5 × 1.5
slippage buffer), at the p90 of per-bar range (25.9 pips). 02–05 UTC session (range 7–10 pips) is
a structural dead zone below the cost floor.

**Direction A (basket):** Design-OK at size_multiplier 0.25, single-name risk budgeting (all
members trade EURUSD/1h — effective N << K; Var(sum)=sum Var + 2 sum Cov; positive cross-member
correlation inflates aggregate variance). Machine-checkable drawdown contract on COMBINED net P&L.
ES at 97.5pct (not VaR-only; p99/median range ratio is ~5x — fat-tailed). Spread tail risk: max
40.7 pips vs median 2.0 pips; cost must be stressed at the spread tail in tail scenarios.

**Direction B (RL):** CONDITIONAL-NO. RL policy is un-pre-declarable (violates Model-Engineering
Firewall), regime-fragile, reward-hackable (gross-vs-net 2x gap demonstrated), and unreconstructable
(kill-switch property 5: attributable). Mitigation requires an OUTER DETERMINISTIC RISK ENVELOPE
— a separate process the policy cannot observe or override — built and prod-tested before any RL
deployment (paper or otherwise). Knight Capital analog: the kill must not depend on the killed
thing being healthy. No such envelope exists. RL not approved to run until it does.

**Citation:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/cro-signals-rl-risk.yaml`

---

### Principal Reviewer (PR)
**Decision:** REJECT (package-level)

The RL feasibility artifact is sound and would stand on its own. The classic-basket pre-reg carries
a blocking defect and three major defects that make it unsafe to freeze.

**Citation:** `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/pr-signals-rl-review.yaml`

---

## PR FINDINGS (FIRST-CLASS — not softened)

### F-001 (BLOCKING): Dishonest deflation denominator
**Location:** `qr-classic-basket-prereg.yaml:10,30-46` (dsr_N_at_freeze=54)
**Finding:** The pre-reg fixes N=54 = 48 + 6 declared members and asserts "the N=54 deflation IS
the family correction." Each member, however, embeds 4–6 author-chosen, un-deflated design knobs
(thresholds, exits, stop multiples, time-stops, MACD noise band, M6 session set). The Bailey-LdP
expected-max-SR (null_hypothesis.py:188) is selected from the cardinality of the SEARCH that
produced the winner — which is the per-member knob grid, not the member count. True N is plausibly
30–200+. A "pass" at N=54 may not survive at the honest N — a deflation artifact, exactly the
failure the screen claims to prevent. Per the firm's own `src/forex_system/analysis/null_hypothesis.py`
(lines 168–197), N = cardinality of the search the winner came from. NHT's "48 + grid-size" is
the structurally correct family. QR's "deflation IS the family correction" misses the within-family
configuration search.
**Owning role:** quant-researcher

### F-002 (MAJOR): Disguised directional sweep
**Location:** `qr-classic-basket-prereg.yaml:49-138` (basket_members)
**Finding:** The basket is presented as a fixed pre-declared set, but 3 of 6 members (M1, M2, M6)
harvest the same intraday mean-reversion that trial 48 already killed. M6 = M1 + session filter —
a conditioned variant of M1, not an independent structure. The honest_expectation explicitly
nominates M6 as "the one member with a non-trivial reason to beat cost." A "fixed basket" whose
members are sequential refinements of one failed idea (all-hours MR → oscillator MR → band MR →
session-filtered MR) is a disguised sweep along the mean-reversion axis. The +1 deflation slot per
member does not capture that M6 was chosen *because* M1 is expected to fail. This compounds F-001:
the search has a direction, and conditional selection inflates effective N beyond the literal count.
**Owning role:** quant-researcher

### F-003 (MAJOR): M3 MACD frozen but uncomputable
**Location:** `qr-classic-basket-prereg.yaml:80,192,258`
**Finding:** M3 (MACD 12/26/9) is declared frozen in the basket but MACD does not exist in
`src/forex_system/features/` (verified by PR: grep for 'macd' returns nothing; `indicators.py`
exposes only `sma/ema/rsi/bollinger_bands/atr/momentum`). Freezing a member whose generating code
does not yet exist means the exit/entry semantics are unverifiable at freeze time. A future
implementer has latitude to match the indicator to the hoped-for behavior — a back-channel for
post-freeze tuning. Either M3 is dropped (changing N) or it is implemented + no-lookahead-tested
BEFORE freeze, not after.
**Owning role:** quant-developer

### F-004 (MAJOR): Always-in M3/M4 purge width is adaptive, not frozen
**Location:** `qr-classic-basket-prereg.yaml:83,98,247-258`
**Finding:** M3 and M4 are always-in trend-followers with no time-stop (only 3xATR catastrophic
stop). The purge for M3/M4 is defined as `purge_M3M4 = min(max_in_fold_hold, 5d)` — a quantity
computed from DATA OBSERVED IN-FOLD. A purge width that is a function of the realized data is not
a pre-frozen gate; it is adaptive and could itself leak or be tuned. Furthermore, an always-in
trend-follower's realized holding period can span weeks to months; capping purge at 5 days when a
50/200 SMA position persists until the opposite cross (potentially months) means OOF blocks
adjacent to a fold boundary can share an open M3/M4 position whose entry decision and exit P&L
straddle the cut — a leakage path. The purge must be replaced by an architecture-imposed, pre-frozen
upper bound on holding horizon.
**Owning role:** quant-researcher

### F-005 (MAJOR): Flat 7.5-pip cost neutralizes M6's only cost-beating mechanism
**Location:** `qr-classic-basket-prereg.yaml:60,89,104,119,136`
**Finding:** Every member lists required_gross_pips_to_net_positive = 7.5 as a flat constant. The
dataset has NO bid/ask spread column (verified: parquet cols = open, high, low, close, volume,
datetime — no bid/ask). M6's entire thesis — "in-session spreads are ~2.0 pips, tighter than
all-hours" — cannot be tested against the data because there is no spread series. A uniform 7.5-pip
RT cost actually NEUTRALIZES the one mechanism M6 relies on to beat the wall (session-conditional
spread tightening) while M6 is nominated as the most likely survivor. M6's a-priori edge is
un-evaluable with the available data and the chosen flat cost — an internal contradiction.
**Owning role:** quant-researcher

### F-006 (MINOR): Regime-consistency gate on unequal, thin blocks
**Finding:** Three IS year-blocks are unequal in length and span only ~3.4 IS years. A low-frequency
member (M4) split across 3 blocks may have <10 trades per block — per-block Sharpe is statistically
meaningless at that count. The 2-of-3 rule on tiny blocks is noise, not robustness.
**Owning role:** quant-researcher

### F-007 (OBSERVATION): Self-authored decision fields
**Finding:** Both artifacts carry self-authored decision fields ('approve' on QR pre-reg, 'veto' on
RL methodology). These are author dispositions, not injected reviewer verdicts. Contamination-check
remains clean; flagged for transparency only.

### F-008 (MINOR, RL only): Circular purge horizon
**Finding (RL feasibility):** "Purge >= policy memory horizon" is circular — the policy's effective
memory horizon is a learned, architecture-dependent quantity not known until after training. The
methodology should require an architecture-imposed, pre-declared memory bound (e.g., a fixed
observation window / truncated BPTT length declared in the pre-reg) so the purge is frozen, not
data/architecture-derived post hoc. The RL verdict (PREMATURE) is still justified; this is a
clarification required before any future RL pre-reg, not a verdict-reversal.
**Owning role:** ml-researcher

**PR steelman (RL):** PR steelmanned offline/batch RL as a counter-argument — offline RL (CQL, IQL,
decision-transformer) is explicitly designed to learn from ONE fixed logged dataset. Verdict
survives: the binding constraint is not interaction count but INDEPENDENT REGIME REALIZATIONS
(~6–10). Offline RL is if anything MORE prone to overfitting the single logged path (distributional
shift, Q-value extrapolation error). PREMATURE verdict stands.

---

## Verified Facts (cited from tool results this session)

- `data/processed/EURUSD_1h.parquet`: 31,019 1h bars, 2021-01-03 to 2025-12-31, OHLCV + volume
  proxy. **NO bid/ask spread column** (verified by PR: parquet cols = open, high, low, close,
  volume, datetime).
- Org trial count = 48 (trials.jsonl, 49 lines; last entry 2026-06-17T04:05:50Z "Honest-N now 48").
- MACD: **ABSENT** from `src/forex_system/features/` (grep exit=1; indicators.py exposes only
  sma/ema/rsi/bollinger_bands/atr/momentum).
- RSI and Bollinger Bands (bb): **PRESENT** in `src/forex_system/features/registry.py`.
- Trial 48 (15923fe1): overnight MR EURUSD 1h; gross fade +3.41 pips/trade REAL (reversion
  hit-rate 0.5517 > 0.50); CPCV net Sharpe −4.93; avg net trade −4.09 pips; DSR=0.00 at N=48;
  terminal_verdict: clean-falsification (cost-dominated, not signal-absent).
- No trial was burned in this design-only task. Basket would burn slots only at a future freeze.
- `src/forex_system/analysis/null_hypothesis.py:168–197`: E[max SR] grows in total_trials — the
  deflation N is the cardinality of the search that produced the winner (source of PR's F-001
  ruling).
- `src/forex_system/harness/honest_n.py:6–16`: firm de-dups by pre_reg_path OR stripped strategy
  family — a THIRD denominator rule, inconsistent with the pre-reg's N=54 claim (the pre-reg
  invents its own rule matching neither firm mechanism).

---

## The Honest Conclusion (3 points)

**1. Classic signals (MACD/RSI/BB) — disciplined basket approach is correct, but this basket is NOT
freeze-ready.** The Principal Reviewer REJECTED it on a dishonest multiplicity correction (true N
≈ 30–200+, not 54) plus 4 major design defects (disguised-sweep composition, uncomputable M3,
adaptive purge on always-in members, flat cost neutralizing M6's thesis). NHT independently
dissented on the same N issue. Run honestly, the bar is far higher and the modal outcome is
FAMILY_KILL (cost-bound), confirming that trial 48's lesson generalizes. Value if pursued = honest
NEGATIVE evidence, at a real (higher-than-claimed) deflation cost.

**2. RL — UNANIMOUS premature behind the data wall.** ML-Researcher veto, HoQR rank #3, NHT TRAP,
CRO conditional-NO without outer risk envelope. One pair / 5yr ≈ ~10 regime realizations; an RL
search's effective-N is 5k–100k. Deliverable = the feasibility + eval methodology doc (banked) +
a NAMED data-milestone gate before any build. No RL trained.

**3. Priority (firm-unanimous) — DATA-CAPABILITY.** Breadth (more pairs at ≤1h) + true bid/ask
spread data ranks #1 by every role. It burns zero deflation slots and attacks the binding
constraint that killed trial 48 and would kill most of the basket.

---

## CEO Decision-Fork (Open Items — Require Explicit Acknowledgment)

**(a) REWORK the classic basket to PR/NHT standard** — honest N ≈ grid-size, drop the disguised-
sweep members (M1/M2/M6 are sequential refinements of trial 48's killed MR idea), implement MACD
first and confirm it passes test_no_lookahead BEFORE freeze, pre-freeze the M3/M4 purge width as
an architecture-imposed upper bound, resolve the flat-cost/M6-thesis contradiction — then run for
honest negative evidence. Alternatively: **minimal 2-member basket** (MACD-cross + EMA50/200-cross,
the only members with a non-zero a-priori path through the cost wall per HoQR) at honest N.

**(b) SKIP the basket, pivot to DATA-CAPABILITY track** (firm-unanimous #1 recommendation) — acquire
intraday breadth (≥6 of 12 pairs at ≤1h) + true bid/ask spread data. Zero deflation slots burned.
This is the one-time ceiling unlock; every future basket and RL attempt benefits.

**(c) RL FEASIBILITY DOC IS BANKED — set the named data-milestone gate.** HoQR's stated gate: RL
BUILD re-triggers when EITHER (a) intraday breadth lands — ≥6 of 12 pairs at ≤1h with true bid/ask
spread; OR (b) sub-1h + volume/order-flow for EURUSD lands. CEO must explicitly name the milestone
and the re-initiator (HoQR on CEO sign-off) to close this fork.

**Explicit acknowledgments required:**
- PR BLOCKING finding (F-001: N=54 is dishonest) — CEO acknowledges; owning role (QR) must resolve
  before any freeze
- NHT formal DISSENT — CEO acknowledges; dissent is append-only and survives this consensus
- ML-Researcher BUILD-NOW VETO — CEO acknowledges; RL build remains blocked until named data
  milestone fires

---

## Governance Notes

**Auto-critic leak (persisted from prior cycles):** During this dispatch, HoQR, QR, and PM workers
referenced spawning critics/sub-agents despite a no-sub-agent instruction on this task. This pattern
has persisted across multiple cycles. Recommended: add an explicit prohibition to the PM prompt for
future dispatches.

**Charter-hash baseline:** Still uninitialized. The charter machinery relies on a pre-declared hash
to detect unauthorized amendments; without the baseline, the detection mechanism is not operational.

**Ratification routing:** This consensus is DESIGN-ONLY (no live capital, no charter/vendor/role
edits). However, PR BLOCKING + NHT DISSENT + MLR VETO require explicit CEO ratification before any
follow-on spend. The auto-ratification path is closed.

---

## Artifact Index

| Artifact | Role | Decision |
|---|---|---|
| `hoqr-prioritization.yaml` | HoQR | APPROVE-WITH-CAPACITY-LIMIT; C>A>B |
| `qr-classic-basket-prereg.yaml` | QR | APPROVE (self); REJECTED by PR |
| `mlr-rl-feasibility.yaml` | MLR | VETO (build-now) |
| `nht-signals-rl-multiplicity.yaml` | NHT | DISSENT |
| `cro-signals-rl-risk.yaml` | CRO | SIZE-REDUCED (0.25x) |
| `pr-signals-rl-review.yaml` | PR | REJECT (package) |
| `pm-acceptance-criteria.yaml` | PM | IMPLEMENT (original dispatch) |
| `.agent-accountability/dissents/signals-rl:phase1:task1.0:null-hypothesis-tester.yaml` | PM | NHT dissent artifact (append-only) |

All artifacts in: `.fintech-org/artifacts/2026-06-17T04-30-05Z_signals_and_rl/`
