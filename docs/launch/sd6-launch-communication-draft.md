# Paper-Trading Launch Communication — Phase-2 Carry-Bet Stack

**Status:** DRAFT — awaiting CEO author/approve per SD-6 ratification 2026-05-11
**Authorization source:** [CONSENSUS_2026-05-10_paper_launch_authorization.md](../decisions/CONSENSUS_2026-05-10_paper_launch_authorization.md)
**Prior governance chain:** CONSENSUS_2026-05-02 (paper-launch authorization) → CONSENSUS_2026-05-03 (preflight closure) → CONSENSUS_2026-05-06 (Wave-10 closure) → CONSENSUS_2026-05-10 (this gate)
**Drafted:** 2026-05-11 by /fintech-org orchestrator (PM-equivalent coordination)
**Confirming reviewer:** ops-engineer (verbatim char-for-char check at `sd6-launch-comm-verbatim-check.yaml`)

---

## 1. Scope and status

This communication discloses the firm's intent to commence **paper trading** (simulated capital, no live capital) of the Phase-2 carry-bet stack against a Saxo Bank paper account. **No production capital is at risk.** This is a research-validation activity to confirm out-of-sample behavior of two pre-registered strategies before any future consideration of production deployment.

**Production-account promotion is explicitly out of scope of this launch** and is gated on resolution of kill-switch Properties 2/3/4 (Wave-9 CRO dissent, append-only). No promotion can occur without separate consensus and an independent risk review.

## 2. Authorized strategies

The following strategies are authorized for paper-loop operation per `CONSENSUS_2026-05-02_paper_launch_authorization.md` Section 9:

| Strategy | Sizing | Conditions |
|---|---|---|
| **vol_target_carry** (VTC) | Full Phase-1 envelope (`size_multiplier=0.5` per existing CRO contract) | Retirement triggers VTC-T1..T8 binding per `CONSENSUS_2026-04-25.md` |
| **FRED-carry Bet #1** (`carry_fred`) | Regime-conditional: `0.25` regime-active / `0.0` regime-inactive | Per CRO Wave-4 (BC-1, BC-2); CF-T9 monitor must be active and healthy from day 1 (BC-3, BC-4) |

**Strategies explicitly NOT authorized for this launch:**

- Bet #2 (`tas_ceiling_4h`) — REJECTED at Sharpe −0.245
- All Phase-0 baselines (`ma_crossover`, `bollinger_rsi`, `carry_baseline`, `carry_momentum`, `fred_carry_stripped`) — REJECTED
- `momentum` — WEAK PASS / STRONG REJECT mixed; not authorized
- `vol_target_carry_no_vol_scaling` — pending HoQR-next properly-sampled ablation
- Any strategy not pre-registered, Gate-3-approved, and Bonferroni-evaluated

## 3. CF-T9 disclosure (REQUIRED — verbatim per NHT Wave-5 Round-3 co-sign)

This launch operates under **CF-T9 pre-registration amendment**, with the following binding disclosure:

> **"CF-T9 is binding on Clauses A and B. Clause C is accepted as a known-incomplete deferral and is pending ratification within 60 trading days of paper launch."**

The firm-operative wording above is adopted per `CONSENSUS_2026-05-10_paper_launch_authorization.md` Section 4, satisfying the NHT substantive requirement at `.fintech-org/artifacts/2026-05-02T-wave5-round3/nht-tier-b-reverify-cosign.yaml` lines 63-70. **NHT Dissent B** (preserved verbatim in CONSENSUS_2026-05-10 Section 10) notes that this wording is PM-crystallized rather than NHT-verbatim; the firm adopts it as operative.

**NHT binding conditions (verbatim from Wave-5 Round-3, append-only):**

1. Paper-launch communications must state CF-T9 is A+B binding with Clause C pending ratification. *(satisfied by this document)*
2. Clause C must be ratified within 60 trading days of paper launch, or a mandatory NHT CF-T9 re-review is triggered. *(SD-5 calendar reminder commitment)*
3. CF-T9 as A+B-only must not be described to any external party as "fully implemented CF-T9."

## 4. Operational parameters

- **Account:** Saxo Bank paper account (production-account capital is NOT touched)
- **Cross-strategy aggregation:** Both loops (vt + carry_fred) operate against the SAME Saxo paper account per CRO Assumption 2 (CONSENSUS_2026-05-03 Section 6). Operating against separate accounts would silently bypass the 15% JPY-correlated exposure cap.
- **Concurrent operation:** AUTHORIZED per BC-8 ratification 2026-05-06 (carry-through confirmed in this CONSENSUS) under the 7 binding constraints:
  - `BC-8-LIFT-COND-1` Per-cycle dispatch lock (`fcntl.flock(LOCK_EX|LOCK_NB)`) ACTIVE on both scripts
  - `BC-8-LIFT-COND-2` Lock released on ALL exit paths (try/finally invariant)
  - `BC-8-LIFT-COND-3` Account-key parity gate enforced at startup
  - `BC-8-LIFT-COND-4` Aggregate JPY-correlated cap ≤15% (frozenset `{USDJPY, GBPUSD}`)
  - `BC-8-LIFT-COND-5` Drawdown ladder ACTIVE: 10% halt-new / 15% reduce / 20% full halt
  - `BC-8-LIFT-COND-6` Kill-switch auto-trigger paths wired (daily-loss / fetch-failure / reconciliation)
  - `BC-8-LIFT-COND-7` Paper-only; no production-account promotion authorized
- **Kill-switch live-promotion blockers:** Properties 2/3/4 of `src/forex_system/risk/kill_switch.py` are FAIL for production but acceptable for paper-only operation. Production promotion is NOT authorized.
- **Cross-JPY pair gap (KG-1):** The `_JPY_CORRELATED` frozenset at `src/forex_system/risk/exposure_aggregator.py:46` contains only `{USDJPY, GBPUSD}`. If scope ever expands to cross-JPY pairs (EUR/JPY, GBP/JPY, AUD/JPY, NZD/JPY), the 15% cap is bypassed until the frozenset is amended. Phase 1 is USDJPY-only; this gap is documented but not active.

## 5. Engineering closure references

- HEAD commit: `747a6ad` (Wave-10 fix-and-amend)
- F-001 / F-002 / F-008 / BC-8 / NEW-2 remediated per Wave-10 CONSENSUS
- Wave-7 RotatingFileHandler closure: present in `scripts/run_paper_trading_vt.py:220` and `scripts/run_paper_trading_carry_fred.py:235`
- Wave-7 cold-start gate (BC-4) item 2 closure: per `CONSENSUS_2026-05-03_wave7_closure.md`
- Drawdown ladder amendment: `docs/specs/drawdown_ladder_amendment_2026-05-06.md`
- Dispatch-lock concurrent test: `tests/scripts/test_wave10_dispatch_lock.py` (332 lines, 11/11 PASS)

## 6. Append-only dissent surface

The following dissents are preserved verbatim in `CONSENSUS_2026-05-10_paper_launch_authorization.md` Section 10 and are append-only:

- **NHT Dissent A** (`concern`, does_block: false): SD-2 was already decided 2026-05-06 — CEO was asked to re-decide via SD-2 framing without explicit subordination disclosure. *Resolved by carry-through framing in CONSENSUS_2026-05-10 Decision paragraph.*
- **NHT Dissent B** (`concern`, does_block: false): The CF-T9 verbatim clause in this document is PM-authored, not NHT-source-verbatim. *Firm adopts PM wording as operative per CONSENSUS_2026-05-10 Section 4.*
- **Wave-9 CRO dissent** (`strong_objection`, does_block: false): Kill-switch Properties 2/3/4 remain production-promotion blockers. *Out of scope for paper launch; persists append-only.*

## 7. Disclaimers

- This communication discloses RESEARCH activity. Not investment advice. Not a solicitation. Not a guarantee of any backtest, paper, or future result.
- Pre-registration documents and falsification criteria are at `references/pre-registrations/` and govern strategy retirement.
- The firm reserves the right to halt the paper loop at any time without prior notice for any reason, including but not limited to: kill-switch trigger, drawdown ladder trigger, operational concern, or CEO discretion.

## 8. Effective date

This communication is effective **T=0** (the day of first paper bar execution). Prior to T=0, all elements of this document remain DRAFT status pending CEO author/approve action.

The 60-trading-day CF-T9 Clause C ratification deadline begins counting on T=0. Calendar reminder mechanism: per SD-5 commitment.

---

**Author/approver:** *(CEO signature required before T=0)*
**Char-for-char verification artifact:** `docs/launch/sd6-launch-comm-verbatim-check.yaml`
**Ratification chain:**
- `paper-launch-auth-2026-05-10:phase1:task4.0` (CONSENSUS_2026-05-10) — RATIFIED 2026-05-11T04:05:00Z by huangtm@gmail.com
