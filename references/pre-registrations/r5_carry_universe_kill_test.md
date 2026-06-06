# R5 PRE-REGISTRATION — Carry-Universe Terminal Kill Test

**Document status:** ASSEMBLED v1 (2026-06-05) — all sections merged (HoQR draft + HoQR snooping-inputs finalization + Mathematician frozen spec); PENDING mathematician sign-off, NHT audit, principal-reviewer review, consensus ratification, and freeze-receipt. Becomes BINDING and FROZEN only upon consensus ratification + CEO sign-off + freeze-receipt (SHA-256 + git commit hash) per criterion FREEZE-mechanics. No bootstrap draw (STEP 4) may execute before the freeze-receipt is committed.

**Track:** r5-step3-prereg-2026-06-05 / Phase 1 / Task 1.0
**Trial ID:** 576746aa (the R5 family counts as ONE trial; STEP 4 reuses it — no counter increment)
**Authoritative scope input:** docs/decisions/CONSENSUS_2026-06-02_r5_scope.md
**Preserved dissent (append-only, firm rule 6):** .agent-accountability/dissents/r5-scope-2026-06-02:phase1:task1.0:null-hypothesis-tester.yaml

---

## 1. Preamble & Scope (HoQR)

### 1.1 What this pre-registration IS

This document is the **terminal, honest KILL TEST** for the firm's carry program. The firm currently has **ZERO validated out-of-sample alpha**; the retirement / kill-criterion has **TRIPPED** (the Bet#1 retirement closed the last open candidate, and the 2026-05-31 honest review found no surviving validated edge). R5 is the single, pre-committed, one-shot statistical test that converts that posture into a defensible decision: either the carry family produces a class-level signal that survives a Hansen-SPA / White-Reality-Check max-statistic test against a zero benchmark on confirmed-real data, or it does not — and if it does not, the firm winds the program down.

This pre-registration freezes — before any bootstrap draw — every degree of freedom that could otherwise be exploited after seeing results: the universe (Section 2), the evaluation window and snooping treatment (Section 3), the null and statistic (mathematician sections), the decision threshold (Section 4), and the action taken under every possible outcome (Section 5). Freezing these in advance is what makes the resulting p-value interpretable.

### 1.2 What this pre-registration is NOT

This is **not a validation vehicle and not a rescue attempt.** It is not an opportunity to find a surviving cell and re-launch the program on it. It is not exploratory research. The test is acknowledged to be **underpowered** (class-level power ~20–35% against a true ~0.30 annualized Sharpe under FWER over correlated cells — see mathematician's Power section). The most probable honest outcome is a **non-rejection**, and the firm has pre-committed (Section 5) that a non-rejection — powered OR underpowered — maps to **WIND-DOWN**, never to "inconclusive, keep spending." There is no "rescue" branch anywhere in the decision tree. A single isolated significant cell does NOT license CONTINUE on the family; that artifact is precisely what R5 exists to catch.

### 1.3 The binding nature of the freeze

Once this document is ratified and the freeze-receipt (SHA-256 of this file + git commit hash of the pinned code state: `carry_universe_matrix.py`, `reality_check.py` after the permitted N1 fix, and the STEP-4 DSR-gate runner described below) is committed, the specification is immutable. **Any post-freeze change to the universe, window, statistic, K, threshold, or code — other than the two permitted pre-freeze changes enumerated below, which must land BEFORE freeze — VOIDS this pre-registration** and forces a re-freeze (and, if a draw has already run, retirement of the contaminated result). STEP 4 is a one-shot run: the test is computed once against the frozen spec; there is no "re-run with a tweak" path that preserves the pre-registration.

> **PERMITTED PRE-FREEZE CHANGES (exhaustive — ALL THREE land BEFORE the freeze-receipt; all are pinned by it):**
> 1. **The N1 hardening fix** to `reality_check.py` (the floor/guard hardening already adjudicated).
> 2. **The STEP-4 DSR-gate runner** — a new, single-purpose invocation script that (a) calls `r5c_hansen_spa` to obtain `p_SPA`, `p_RC`, and the winning cell `k*`; (b) computes the §7.3.4 DSR statistic for cell `k*` **directly from the frozen formula** `Φ((SR_pp − SR0_pp)·sqrt(T−1)/sqrt(var_term))`, using the §7.3.4 conventions, with the **frozen** `SR0_pp = 0.022906` (per-obs; `= 0.363623 / sqrt(252)`, elected N = 3 per §3.4) injected as a literal; and (c) evaluates the §7.3.6 decision functional. This runner does **not** modify `dsr.py`, `reality_check.py`, or `carry_universe_matrix.py`. The canonical `dsr.py:compute_dsr` is unchanged and is pinned only as the CONVENTIONS reference (§7.3.3, §7.3.4) — its internal `expected_max_sr` benchmark is NOT the frozen execution path.
> 3. **The `hac_se_nw` module-level extraction in `reality_check.py`** — the Newey-West HAC-SE
>    computation, previously a closure inside `r5c_hansen_spa`, extracted verbatim to module level
>    so the STEP-4 runner can compute the §7.3.4 studentized `T_k` for the k* selection EXACTLY
>    (same Bartlett kernel, same `s2 >= 1e-12` clamp, same `h = block_length − 1` convention)
>    without duplicating statistical code. The closure now delegates to the extracted function —
>    behavior-identical by construction (verified: full harness + reality_check test suites pass
>    unchanged). No other code change is permitted; any post-freeze edit to any of these FIVE code
>    objects (the two §1.3-item files, the runner, the receipt tool, `r5_decision.py`) voids the pre-reg.

---

## 2. Universe (HoQR) — criterion PRE-REG-universe

### 2.1 Explicit 6×6 enumeration (all 36 cells)

The frozen universe is the full Cartesian product of **6 carry variants × 6 JPY crosses = 36 cells**. No cell is privileged; no cell is silently dropped.

| | USDJPY | EURJPY | GBPJPY | AUDJPY | CADJPY | NZDJPY |
|---|---|---|---|---|---|---|
| **carry** | carry·USDJPY | carry·EURJPY | carry·GBPJPY | carry·AUDJPY | carry·CADJPY | carry·NZDJPY |
| **carry_fred** | carry_fred·USDJPY | carry_fred·EURJPY | carry_fred·GBPJPY | carry_fred·AUDJPY | carry_fred·CADJPY | carry_fred·NZDJPY |
| **fred_carry_stripped** | fred_carry_stripped·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |
| **vol_target_carry** | vol_target_carry·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |
| **vol_target_carry_no_vol_scaling** | …·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |
| **carry_momentum** | carry_momentum·USDJPY | …·EURJPY | …·GBPJPY | …·AUDJPY | …·CADJPY | …·NZDJPY |

**Variants (exhaustive carry family):** `{carry, carry_fred, fred_carry_stripped, vol_target_carry, vol_target_carry_no_vol_scaling, carry_momentum}`
**Pairs (frozen at 6 JPY crosses):** `{USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY}`

USDJPY is **included** because its canonical input `data/processed/USDJPY_daily.parquet` is the REAL series (range 75.82–161.71, verified in the scope consensus). The corrupted `processed_synthetic_phase0/` USDJPY (5.03–7.75) is quarantined and prohibited from this test; if R5 is ever pointed at the synthetic directory the test is void. Non-JPY pairs are out of scope: the carry program never claimed them.

### 2.2 Named constraint: NO-SILENT-EXCLUSION

> **Constraint NO-SILENT-EXCLUSION.** Every one of the 36 cells either (a) appears in the joint return matrix that feeds the test, or (b) is dropped with a **structured, logged reason** (the `carry_matrix.cell_dropped` decision-trace event with `reason`, `exc_type`, `category` fields) recorded in the STEP 4 results and reconciled against this pre-reg. A silent drop — a cell that vanishes with no logged reason — **voids the FWER guarantee** and therefore voids the test. Code errors (KeyError/AttributeError/TypeError/etc.) RAISE loudly and fail the run closed; only genuine, confirmable data-insufficiency may drop a cell, and only with a structured reason. The matrix builder enforces this fail-closed behavior by design (`carry_universe_matrix.py` module docstring).

The expected build is **all 36 cells, 0 dropped** (per the STEP 2b commit). Any deviation from 36 must be explained cell-by-cell in the STEP 4 build report before the p-value is read.

### 2.3 Honest statement: these are NOT 36 independent hypotheses

The six variants are **re-parameterizations and ablations of ONE underlying idea — the cross-currency rate differential.** They share the same signal feed (`rate_differentials.parquet`), and the six JPY crosses share heavily overlapping price-return dynamics. The **effective number of independent tests is ≈ 1–2** (HoQR estimate; NHT's wider 2–4 is preserved in the dissent). This is the reason the test uses joint same-block resampling under a single pooled FWER family rather than 36 separate tests with Bonferroni — and it is why a non-rejection here is not surprising and is not, by itself, proof of no edge (it is, however, pre-committed grounds for wind-down; see Sections 3 and 5).

---

## 3. Evaluation Window & Snooping Treatment (HoQR proposal; mathematician co-signs) — criterion PRE-REG-oos-window

### 3.1 The honest snooping posture

These six variants are the firm's **longest-studied strategies**, carrying a large prior trial history across the full 2010–2026 sample. **That selection is sunk and uncontrollable.** A prospective Reality-Check on the same 2010–2026 data does NOT retroactively control the looks already spent; it inherits the snooping and yields an optimistically biased p (NHT dissent §3). "We used all available data with no haircut" is explicitly **not acceptable** under criterion PRE-REG-oos-window, and we do not propose it.

## §3.2 Snooping treatment — Method A adjudicated UNAVAILABLE; Method B operative

### Method A adjudication (formal, per-variant)

Method A (Mathematician §7.1) requires, for **every one of the 6 variants**, a window whose bars
were generated *after* that variant's last development/parameter-selection touch, that was *never*
used in any prior carry trial, and that has enough bars for a valid block bootstrap. The verified
QD build fact is that the **common joint index ends 2026-04-06**. A genuine hold-out would have to
sit at the tail of that index, after the latest per-variant development touch. The per-variant
evidence below shows no such window of meaningful length exists; for two of the six variants the
development/validation window ends *after* the entire R5 index, so the candidate hold-out region is
empty or negative.

| Variant | Last development / parameter-selection touch (evidence) | Hold-out window available inside R5 index (ends 2026-04-06)? |
|---|---|---|
| **carry** (baseline) | OOS-2022 falsification window 2022-01-01 → 2023-12-31, rejected 2026-05-02 (`references/pre-registrations/carry_baseline.md:81-83`; trial `5d18776d`, `.fintech-org/trials.jsonl:20`). Parameters (max_differential 5%, min 0.5%) inherited from the shared carry config. | NO meaningful clean window. The signal is a monthly forward-filled rate differential; the 2024-01 → 2026-04 tail carries ≈27 fresh monthly observations only. |
| **carry_fred** (Bet #1) | OOS holdout reserved through **2026-04-25** (`references/pre-registrations/carry_fred.md:16,25,134`; `carry_fred.triggers.yaml:38` `oos_window_end: "2026-04-25"`). The Bet #1 validation period (post-2024 BoJ-divergence) was *selected* using data through 2026-04-25. | NO — the development/validation window **ends 2026-04-25, AFTER the entire R5 index (2026-04-06)**. There is zero post-development tail inside the R5 index for this variant. Method-A condition 1 fails outright. |
| **fred_carry_stripped** | Designed 2026-05-01 as an ablation of carry_fred; tested on OOS-2022 2022-01-01 → 2023-12-31, rejected 2026-05-02 (`references/pre-registrations/fred_carry_stripped.md:1-7,111-112`; trial `b7d1a65a`, `trials.jsonl:22`). Inherits all parameters from carry_fred, whose selection used data through 2026-04-25. | NO — inherits carry_fred's through-2026-04-25 selection; same defect. |
| **vol_target_carry** | Developed AND validated same day 2026-04-20 on full-history 2010–2026 (`references/pre-registrations/vol_target_carry.md:4-14,23-24,63`). Retroactive pre-reg; full-history validation explicitly uses the entire sample including the R5 tail. | NO — full-history (2010–2026) validation consumed the entire index; nothing inside R5 is post-development. |
| **vol_target_carry_no_vol_scaling** | Ablation designed 2026-05-01; OOS-2022 window 2022-01-01 → 2023-12-31, rejected 2026-05-02 (`references/pre-registrations/vol_target_carry_no_vol_scaling.md:1-9,37-38`; trial `9017fadb`, `trials.jsonl:25`). Parameters inherited from vol_target_carry (full-history selection). | NO — inherits vol_target_carry's full-history selection. |
| **carry_momentum** | OOS-2022 window 2022-01-01 → 2023-12-31, rejected 2026-05-02 (`references/pre-registrations/carry_momentum.md:1-9,80-81`; trial `6a56df9c`, `trials.jsonl:21`). Momentum params (SMA 20/50) and carry params from the shared config; an earlier diagnostic touched real broker-sourced market data 2026-04-20 (`trials.jsonl:15`, `backfill-0e02f2dd`). | NO meaningful clean window; same monthly-stale-signal limit as carry. |

**VERDICT — Method A is UNAVAILABLE.** This table IS the §7.1 attestation, in the negative. No
variant clears condition 1 (post-development bars inside the R5 index) for a window of meaningful
length. Two variants (carry_fred, vol_target_carry) fail decisively: their development/validation
windows extend to 2026-04-25 (carry_fred) or span the full 2010–2026 history (vol_target_carry),
both of which **end at or after the R5 index terminus (2026-04-06)**, leaving an empty or negative
post-development tail. The remaining four inherit those same selections or rely on the monthly
forward-filled `rate_differentials.parquet` signal, whose effective information content over the
candidate tail (2024-01 → 2026-04) is ≈27 fresh monthly observations — far too thin to be a
powered hold-out and not "never-used" (the firm acted on full-history and OOS-2022 metrics that
overlap it). A daily-bar hold-out carved from this region buys almost no genuinely-new information
per unit of calendar time. **Method A is therefore declined, and Method B (deflation haircut) is
the operative snooping control.**

### Method B (operative): selection-deflated Sharpe haircut on the SPA decision

Because Method A is unavailable, R5 runs on the **full common joint index** and the SPA decision is
gated by a **Bailey–López de Prado (2014) Deflated-Sharpe-Ratio (DSR) haircut**, using the formula
frozen by the Mathematician (§7.2):

> `SR0 = sqrt(Var[SR_n]) · [ (1 − γ) · Z⁻¹(1 − 1/N) + γ · Z⁻¹(1 − 1/(N·e)) ]`

with `γ` = Euler–Mascheroni ≈ 0.5772, `Z⁻¹` the inverse standard-normal CDF, `N` the honest number
of effectively-independent carry looks (§3.4), and `Var[SR_n]` the variance of the Sharpe estimates
across those `N` looks. The observed best cell Sharpe must clear `SR0` (incorporating the return
series' skewness and excess kurtosis and sample length per the BLdP DSR statistic) before a bare
`SPA p < 0.05` is treated as face-valid. **HoQR owns the decision that snooping MUST be charged and
that a bare p is necessary-but-not-sufficient; the Mathematician owns the formula and its
integration with the SPA p-value.** The studentized SPA statistic recenters/rescales poor cells; the
deflation sits on top as the snooping charge. There is no double-charge: because Method A is
declined, only the haircut applies.

---

## §3.3 Window as a RULE over the common joint index (finalized with exact dates)

> **WINDOW RULE (FROZEN).** The test evaluates the **full common joint index** — the inner-join
> (intersection) of all 36 cells' valid daily return dates, post-entry-delay
> (`entry_delay_bars = 1`, the sacred no-lookahead invariant), net-of-cost, after the alignment that
> produces a rectangular NaN-free matrix (`carry_universe_matrix.py` alignment design). The
> SPA / White-RC max-statistic is computed over this entire common index. The snooping charge of
> §3.2 (Method B deflation) is applied to the resulting decision.

> **EXACT DATES (verified QD build report):**
> - **Common joint index start:** **2010-03-15**
> - **Common joint index end:** **2026-04-06**
> - **T = 4186 daily bars**
> - **Dropped cells: 0** — **all 36 cells present** (NO-SILENT-EXCLUSION constraint satisfied at build)

Because Method A is UNAVAILABLE (adjudicated above), there is **no hold-out split**; the window is
the full 2010-03-15 → 2026-04-06 index and Method B is the operative snooping control. Both HoQR and
the Mathematician sign this section before freeze.

---

## §3.4 Frozen DSR inputs (NEW — the load-bearing call)

### Honest-N pin: **N = 3**

> **Bias-direction caveat (load-bearing — read first).** `SR0` is strictly INCREASING in `N`
> (more looks ⇒ a higher expected maximum Sharpe under the null ⇒ a higher deflation bar). The
> combined credible range for the honest carry-N is **1–2 (HoQR) / 2–4 (NHT) → union 1–4**. The
> UNION FLOOR (`N = 2`) is therefore the LEAST-deflating admissible choice — it sets the LOWEST bar
> the observed Sharpe must clear, biasing the decision toward CONTINUE. For a pre-committed KILL
> test whose declared most-likely outcome is WIND-DOWN, pinning the anti-conservative floor is hard
> to square with the conservatism this pre-reg claims elsewhere (that conservatism is real only on
> the `Var[SR_n]`/`SR_1` axis, §3.4 Sharpe table, NOT on the N axis). I therefore move OFF the floor.
> **Elected `N = 3`** — the midpoint of the union range. I stop at the midpoint rather than the
> skeptic's top (`N = 4`) because the mechanistic decomposition below genuinely identifies only TWO
> *distinct* information sources; `N = 3` charges a half-look for the residual independence the
> 2-source view may understate (the FRED regime gate and the vol-targeting layer are not pure
> re-parameterizations of the bare rate differential). The Mathematician freezes `SR0` for
> `N ∈ {2,3,4}` in parallel; the elected `N = 3` maps to the frozen middle scalar.

**Derivation — and an honest statement of what is code-mechanical vs. what is MY adjudication.**
The honest-N is the number of *effectively independent* carry looks the firm has spent — not the
org-wide trials.jsonl count, and not 1. This pin is **my adjudication as falsification-archive
owner.** It is NOT an output of `honest_n.py`. I separate the two cleanly below so the authority is
not overstated.

**(a) What `honest_n.py` actually returns — verbatim, on the REAL registry.** Running
`compute_honest_n(Path(".fintech-org/trials.jsonl"))` against the real `.fintech-org/trials.jsonl`
(37 lines, 30 unique trial_ids after last-row-wins collapse; 8 excluded as spawned/exploratory)
yields **`N_honest = 10`, ORG-WIDE**, with retained hypothesis keys:
`{references/pre-registrations/vol_target_carry.md, references/pre-registrations/momentum.md,
ma_crossover, bollinger_rsi, carry, carry_momentum, fred_carry, vol_target_carry, tas_ceiling,
momentum}`. The carry-family SUBSET of those keys is
**`{carry, carry_momentum, fred_carry, vol_target_carry, vol_target_carry.md}` = 5 keys.** Two facts
about the code that the earlier draft got wrong and I correct here:

  - The code keys by **`pre_reg_path` FIRST** when a row carries one (`honest_n.py:147-152`); only
    rows with NO pre_reg_path fall through to the suffix-strip on `strategy`. So the six retained
    `vol_target_carry` trials (all carrying `pre_reg_path:
    references/pre-registrations/vol_target_carry.md`) and the one `vol_target_carry_no_vol_scaling`
    trial (no pre_reg_path → strips `_no_vol_scaling` → `vol_target_carry`) land on TWO different
    keys (`...vol_target_carry.md` and the bare `vol_target_carry`), not one. The code does NOT
    perform the tidy "8 pre-regs → 5 keys" collapse the earlier draft tabulated.
  - **`carry_fred` never appears as a key.** No retained trial has `strategy == "carry_fred"`; the
    only carry_fred-adjacent retained row is `fred_carry_stripped` (trial `b7d1a65a`), which strips
    `_stripped` to `fred_carry`. The earlier draft's "carry_fred" key was a hand-fiction.

**(b) Why I do NOT use the code's `N_honest = 10` directly.** Org-wide 10 mixes non-carry
strategies (ma_crossover, bollinger_rsi, momentum, tas_ceiling) into the count and is keyed by the
*archive's* dedup convention, which is built for org-wide multiplicity bookkeeping, not for the
*effective independent dimension of the carry family* that the DSR `SR0` benchmark requires. The
DSR needs "how many genuinely-independent carry bets were the firm's selection drawn from," which is
a smaller, judgment-laden number. The 5 carry-family keys above are the relevant raw material; the
collapse from 5 keys to an *effective* count is the adjudication step, performed below — by me, not
by the code.

**(c) MY adjudication (judgment, defended on merits — the skeptic accepts it as defensible).** The
5 carry-family keys are **re-parameterizations and ablations of ONE underlying idea: the
cross-currency interest-rate differential**, all driven by the same `rate_differentials.parquet`
feed (carry_fred pre-reg `:131,133`; mechanism sections of all carry pre-regs). The ratified scope
finding is that the 36-cell universe has **effective independent dimension ≈ 1–2 (HoQR) / 2–4 (NHT)**
(`docs/decisions/CONSENSUS_2026-06-02_r5_scope.md:21,45,94`). Decomposed by *information source*:

1. **The pure rate-differential carry look** — `carry`, `fred_carry`, `vol_target_carry`, and the
   `vol_target_carry.md` pre-reg key are all the same rate-differential signal with a
   sizing/ranking/conditioning wrapper (rank-normalization, vol-targeting, FRED regime gate). They
   share the feed and their OOS returns are dominated by the same JPY-cross carry dynamics. This is
   essentially **ONE** information source.
2. **The carry+momentum hybrid look** — `carry_momentum` adds an SMA-crossover momentum overlay
   (`carry_momentum.md:27-40`), a genuinely *different* signal source (price trend, not rate level)
   gated by an agreement filter. The momentum component injects information not present in the pure
   carry look. This is a **SECOND** information source.

The bare 2-source decomposition would pin `N = 2`. **I elect `N = 3`, not `N = 2`,** for the
bias-direction reason stated in the header: `SR0` increases in `N`, so `N = 2` is the union-FLOOR
and the LEAST-deflating admissible choice, biasing a KILL test toward false CONTINUE. `N = 3` is the
midpoint of the union range 1–4 and charges a half-look beyond the bare 2-source count, recognizing
that the FRED regime gate and the vol-targeting layer are not *pure* re-parameterizations of the bare
differential — each conditions on information (a regime flag; realized-vol) that the bare carry look
does not use, so the "effectively ONE source" claim for look 1 understates its internal dispersion.
`N = 3` is the conservative-but-not-extreme point: above the anti-conservative floor, below the
skeptic's top.

**Why N is neither 1 nor 36 nor 37, and why I stop at 3 rather than going to 4:**
- **Not 37 / not the org-wide 10** (raw or `honest_n.py` counts): both include non-carry strategies
  and/or count cost-ablations and re-runs as separate looks. They *overstate* the independent carry
  looks and would over-deflate (understating any real edge — the symmetric error to the N=2 floor).
- **Not 36** (the cell count): the 36 cells are NOT 36 hypotheses — the joint same-block bootstrap
  is used *because* the cells are not independent. Charging N=36 in the DSR would double-count the
  multiplicity the SPA max-statistic already controls jointly.
- **Not 1**: there genuinely are two distinct information sources (rate-differential carry vs.
  carry+momentum hybrid). N=1 would treat the momentum overlay as free and under-deflate.
- **Not 4** (skeptic's top / the most-conservative pole): 4 would charge as if all five carry keys
  carried near-independent information, which the mechanistic decomposition does not support — the
  four pure-carry keys demonstrably share the rate-differential feed. I take the midpoint, not the
  skeptic's ceiling, because over-deflation (my own argument against N=37) would understate a real
  edge just as a floor-pin overstates it. `N = 3` is the point that is honestly defensible on both
  axes for a kill test.

### Sharpe table (representative estimate per independent look)

The DSR formula needs the Sharpe estimates across the N independent looks. I use the canonical
realized Sharpe of the representative member of each look, cited to source. For look 1 (pure
rate-differential carry) the representative member is **carry_fred = Bet #1**, the firm's flagship
carry validation; for look 2, **carry_momentum**.

| Look | Representative member | Sharpe (SR_n) | Source (trial_id / file:line) |
|---|---|---|---|
| 1 — rate-differential carry | carry_fred (Bet #1, regime-active OOS) | **0.80** | **REGISTRY-PROSE, NOT a trial-result row** — see source note below. `references/pre-registrations/carry_fred.md:15,25` (≥0.30 portfolio gate hypothesis; OOS holdout 2023-04-25→2026-04-25), `references/pre-registrations/fred_carry_stripped.md:65-66,92` ("carry_fred achieved 0.80 on its OOS window") |
| 2 — carry+momentum hybrid | carry_momentum (OOS-2022) | **0.197** | trial `6a56df9c` (`.fintech-org/trials.jsonl` line 27; `oos_sharpe=0.197`, status rejected) |

> **Source note on SR_1 = 0.80 (F-007 — acknowledged).** The independent reviewer correctly flags
> that `SR_1 = 0.80` is **registry-PROSE, not a trial-result row.** There is NO completed trial in
> `.fintech-org/trials.jsonl` carrying `strategy == "carry_fred"` and `sharpe ≈ 0.80`; 0.80 is the
> regime-ACTIVE Sharpe quoted in the carry_fred / fred_carry_stripped pre-reg prose, and carry_fred's
> own NHT co-sign condition (`carry_fred.md:149`, condition 3) explicitly says sizing must NOT use
> the 0.80 regime-active number as a base case (regime-INACTIVE is ≈0.07). I retain 0.80 here on a
> **conservative-if-wrong** basis: it is the LARGEST plausible representative Sharpe for look 1, which
> MAXIMIZES `Var[SR_n]` and therefore RAISES the DSR `SR0` bar — the anti-survivorship direction. If
> 0.80 is an overstatement, the true `Var[SR_n]` is smaller and the haircut I impose is *too harsh*,
> never too lax; the error cannot manufacture a false CONTINUE. **Contingency disclosed:** this
> safety argument holds only if the DSR gate actually EXECUTES on the SPA decision. That execution is
> the Mathematician's F-001 fix (the degenerate-DSR-units bug that produced the false Bet#1 PASS,
> trials.jsonl line 36 correction). If F-001 does not land before freeze, the haircut is inert and
> this conservative-if-wrong argument is void; the freeze-receipt must therefore pin the F-001-fixed
> code commit. SR_1 = 0.80 is NOT independently trial-verified and is flagged as such for the record.

Supporting per-member Sharpes (for the record; not the N=2 inputs): carry baseline 0.2841
(`trials.jsonl:20`), fred_carry_stripped 0.07464 (`trials.jsonl:22`), vol_target_carry 0.7594
full-history (trial `d572999d`, `trials.jsonl:14`). These collapse into look 1's representative
(carry_fred 0.80, the strongest and the one the firm acted on); using the strongest member is the
conservative, anti-survivorship choice — it makes Var[SR_n] larger and the DSR threshold higher.

### Frozen dispersion convention and DSR inputs (Mathematician-owned, elected N = 3)

**Dispersion convention (explicit — required by the Mathematician's rework-1b NOTE).** The dispersion
plug-in `sqrt(Var[SR_n]) = 0.426385` is the **sample standard deviation computed over the TWO
observed, independently-sourced look-representative Sharpes `{SR_1 = 0.80, SR_2 = 0.197}`** — the
sample (÷(N_obs − 1) = ÷1) estimator over the observed pair — held fixed across N ∈ {2, 3, 4}, with
the elected N entering only through the expected-maximum bracket axis. There are only two OBSERVED
independent look-representatives in the firm's falsification archive; the N = 3 election charges a
half-look of multiplicity on the bracket axis for residual independence (the FRED regime gate and the
vol-targeting layer condition on information absent from the bare rate-differential look), but
inventing a third Sharpe observation to inflate or deflate `sqrt(Var)` would be fabrication — there
is no third independently-drawn look-Sharpe in the archive from which to estimate anything. The
sample (÷1) estimator over `{0.80, 0.197}` is therefore the only non-fabricated dispersion estimate
available, and it is the plug-in for all three candidate N values.

**Limitation (honest — the Mathematician's obligation).** A dispersion estimate from exactly 2
observations is itself highly uncertain; the estimation noise propagates in both directions on
`SR0`. The direction of this residual error is absorbed into the two-axis framing disclosed in
§7.3.1 (Var/spread axis conservative-if-wrong; N-axis anti-conservative at the floor) rather than
being claimed away. See §7.3.1 for the full two-axis analysis.

**Cross-reference.** The full frozen SR0 table (all N ∈ {2,3,4}, all quantiles, brackets, and
annualized/per-obs scalars) is in §7.3.1. The derivations are in §7.3.3. The frozen execution
scalar for the STEP-4 runner is in §7.3.3 (FROZEN line) and §7.3.4 (code block).

**Frozen inputs (N = 3 elected — Mathematician-signed):**
- `N = 3` (elected by HoQR §3.4 header; Mathematician-co-signed)
- `sqrt(Var[SR_n]) = 0.426385` (sample ÷1 estimator over observed look-Sharpes `{0.80, 0.197}`; held fixed across all candidate N)
- `γ = 0.5772156649` (Euler–Mascheroni constant)
- `e = 2.718281828`
- `bracket(N=3) = (1−γ)·Z⁻¹(2/3) + γ·Z⁻¹(1 − 1/(3e)) = 0.4227843·0.430727 + 0.5772157·1.161957 = 0.852804`
- `SR0(N=3) = 0.426385 · 0.852804 = 0.363623` (annualized) / `0.022906` (per-obs, = 0.363623/√252)
- `α = 0.05`; DSR gate threshold: `DSR ≥ 0.95`

---

*HoQR sign-off: Method A UNAVAILABLE (per-variant negative attestation above); Method B operative;
**N = 3** (elected off the union FLOOR for the bias-direction reason in the §3.4 header — `SR0`
increases in `N`, so the floor is anti-conservative for a kill test); `Var[SR_n]` is the dispersion
of the look-level Sharpes the Mathematician freezes for the elected `N` (the prior `N = 2` hand-arith
`Var = 0.0909` is SUPERSEDED — with `N = 3` the dispersion remains the frozen sample standard deviation over the TWO
observed look-representative Sharpes {0.80, 0.197} per the Mathematician's frozen convention (§3.4
Frozen-dispersion block) — the elected `N` enters only the expected-max bracket — not HoQR hand-arithmetic; `SR0` is frozen by the Mathematician for
`N ∈ {2,3,4}` and the elected value is the `N = 3` scalar). SR_1 = 0.80 is registry-prose,
conservative-if-wrong, contingent on the F-001 DSR-gate fix (see Sharpe-table source note). Pinned to
the freeze-receipt at assembly.*

---

## 4. Decision Rules (HoQR) — criterion PRE-REG-decision-threshold

The decision is a **single binary firm decision: CONTINUE or WIND-DOWN.** It is read off the frozen-family SPA p-value (with the White-RC p-value as a conservative cross-check; both are reported), after the Section 3 snooping charge. α = 0.05 (mathematician's error-control section).

- **CONTINUE path — `SPA p < 0.05` at the CLASS level (post-deflation), confirmed by White-RC direction.**
  CONTINUE is **NECESSARY-BUT-NOT-SUFFICIENT.** A class-level rejection means the family is distinguishable from chance against a zero benchmark — it does NOT validate any individual cell, and it does NOT re-launch the program. The single named confirmatory next step is: **author a NEW, separate pre-registration for a confirmatory-only test of the specific surviving structure**, with no free exploration, no re-parameterization, no new variant or pair search. Selecting a cell post-hoc and trading it invalidates the p at any magnitude.
  **Forking-paths counter-discipline (BINDING).** Any R5-spawned confirmatory test (i) **increments the org-wide trial counter as a NEW trial** (a fresh `trial_id`, distinct from R5's `576746aa`; it does NOT reuse the R5 family id), and (ii) **MUST absorb the R5 36-cell selection burden in its own honest-N and deflation inputs** — the candidate it confirms was SELECTED after seeing R5's 36-cell results, so that selection is a spent look and is part of the confirmatory test's OWN multiplicity. A confirmatory test that does not carry the R5 selection forward into its honest-N / `SR0` is itself a garden-of-forking-paths violation and its p is not face-valid.

- **WIND-DOWN path — `SPA p >= 0.05` at the family level.**
  The carry family is statistically indistinguishable from chance at the class level. Combined with the already-completed Bet#1 retirement and the zero-validated-alpha posture, this makes the no-edge conclusion **structural**. Action: formal wind-down to monitoring (Section 5). This branch fires regardless of whether power was adequate or low — the underpowered-non-rejection caveat does NOT open a third door (Section 5, outcome 3).

- **AMBIGUOUS path — partial / anomalous result** (e.g., the family p straddles the boundary within MC-SE; or only an isolated subset shows signal; or a normalization-driven distortion such as the carry_momentum near-null column — see N2 — produces a result that is not a clean class-level rejection).
  AMBIGUOUS maps to **a confirmatory-only pre-reg gate, NEVER to CONTINUE on the original family.** No capacity is unfrozen for the original 36-cell family on an ambiguous result. The only permitted forward action is a fresh, separately-pre-registered confirmatory test of the specific anomaly, treated as a brand-new hypothesis with its own freeze.
  **Forking-paths counter-discipline (BINDING, identical to the CONTINUE path).** Any such confirmatory test (i) **increments the org-wide trial counter as a NEW trial** (fresh `trial_id`, not R5's `576746aa`), and (ii) **MUST absorb the R5 36-cell selection burden in its own honest-N and deflation inputs** — the anomaly being confirmed was SELECTED after seeing R5's 36-cell results, so that selection is a spent look counted in the confirmatory test's OWN multiplicity. Untracked, a post-R5 confirmatory test re-opens the garden of forking paths and its p is not face-valid.

There is no decision branch in this document that results in "keep researching the carry family as-is." CONTINUE only ever buys a *new confirmatory pre-reg*; it never buys free exploration.

---

## 5. Wind-Down Action Map (HoQR) — criterion PRE-REG-winddown-map

Every possible test outcome maps to a **named firm action**, pre-committed here before any draw. "Inconclusive, keep spending" is not a valid action for any outcome.

| # | Outcome | Condition | Named firm action |
|---|---|---|---|
| **1** | **REJECT (class level)** | SPA p < 0.05 (post-deflation), White-RC concordant | **CONFIRMATORY pre-reg only.** Author a new, separate pre-registration for a confirmatory-only test of the surviving structure. NO free exploration, NO re-parameterization, NO new variant/pair search, NO capital. The original 36-cell family is NOT re-opened for research; only the named confirmatory hypothesis proceeds. **The confirmatory test increments the org-wide trial counter as a NEW trial (fresh `trial_id`, not `576746aa`) AND absorbs the R5 36-cell selection burden in its own honest-N / deflation inputs (the post-R5 cell selection is a spent look in that test's multiplicity).** |
| **2** | **FAIL TO REJECT, powered** | SPA p ≥ 0.05 AND power adequate | **WIND-DOWN.** Zero validated alpha is confirmed structural at adequate power. Execute the wind-down-to-monitoring procedure (§5.1). |
| **3** | **FAIL TO REJECT, underpowered** | SPA p ≥ 0.05 AND power ~20–35% (the expected scenario) | **WIND-DOWN (BINDING).** The low power makes this non-rejection UNINFORMATIVE *as evidence of no-edge* — but it does NOT change the firm action. Per the ratified scope and the NHT dissent, an underpowered non-rejection reads as "no DISTINGUISHABLE class-level alpha at the achievable power" → **WIND-DOWN.** This is explicitly NOT "inconclusive, keep spending." There is no third outcome that licenses continued spend on the carry family. |
| **4** | **ANOMALOUS** | Partial subset survives; boundary-straddle within MC-SE; or normalization-driven distortion (e.g., carry_momentum near-null column post-N2 decision) | **AMBIGUOUS → confirmatory pre-reg gate ONLY.** Does NOT license CONTINUE on the original family. The specific anomaly may be carried into a fresh, separately-pre-registered confirmatory test with its own freeze; the 36-cell family research is not re-opened. No capital. **That confirmatory test increments the org-wide trial counter as a NEW trial (fresh `trial_id`, not `576746aa`) AND absorbs the R5 36-cell selection burden in its own honest-N / deflation inputs.** |
| **5** | **TECHNICAL FAILURE** | Code error, data-integrity fault, or unexplained cell drop detected at run time | **HALT, root-cause, re-freeze, re-run.** No p-value is read or reported. The trial counter is NOT incremented (the R5 family remains ONE trial, id 576746aa). After root-cause and a new freeze-receipt, the one-shot run is repeated. A masked bug presented as a benign cell drop is itself a NO-SILENT-EXCLUSION violation that voids the run. |

### 5.1 What "wind-down to monitoring" concretely means for this firm

Outcomes 2 and 3 both trigger this state. Concretely:

- **No new research spend on the carry program.** No new variants, no parameter searches, no re-tests of the 36-cell family on this dataset.
- **Archive the carry strategy registry** entries as RETIRED/FALSIFIED, with a pointer to this pre-reg, the freeze-receipt, and the STEP 4 result (the falsification archive — a curated record of what was killed and why).
- **Observe-only state.** Any residual carry exposure is monitoring-only (no capital at risk; the firm is backtest/paper-only regardless). The decision-trace and result artifacts are retained for the record.
- **Redirect remaining capacity** to the contamination audit and to genuinely-new alpha hypotheses (which require their own fresh pre-registration; the zero-validated-alpha posture means nothing is unfrozen by default).
- **The wind-down recommendation is surfaced to the CEO for ratification** — wind-down is irreversible firm policy and is not in the autonomous quorum's authority.

---

## 6. Retirement Criteria (HoQR) — machine-checkable

These conditions are tied directly to the decision rules (Section 4) and the wind-down map (Section 5). They are the machine-checkable triggers a downstream gate can evaluate against the STEP 4 result artifact:

- `R5.spa_p >= 0.05` → **RETIRE the carry program** (wind-down to monitoring; outcomes 2 & 3). This fires whether or not power was adequate; power does NOT gate this trigger.
- `R5.spa_p < 0.05 AND R5.white_rc_p >= 0.05 (discordant)` → **AMBIGUOUS**, do NOT CONTINUE on the family; confirmatory pre-reg gate only (outcome 4). Any spawned confirmatory test MUST register as a NEW `trial_id` (counter increment) AND carry the R5 36-cell selection into its own honest-N / deflation inputs; a confirmatory test that reuses `576746aa` or omits the R5 selection burden is VOID.
- `R5.cells_built != 36 AND any dropped cell has reason == null/empty` → **VOID the run** (NO-SILENT-EXCLUSION breach); HALT, re-freeze (outcome 5).
- `R5.code_error == true OR R5.data_integrity_fault == true` → **HALT**, root-cause, re-freeze, re-run; trial counter NOT incremented (outcome 5).
- `receipt.prereg_sha256 != sha256(bytes_of_this_prereg_file_as_committed) OR receipt.code_commit != pinned_commit` → **VOID** — the run executed against an unfrozen or drifted spec; result is not face-valid.
  The receipt is the EXTERNAL file `r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml`
  written by `cut_freeze_receipt.py`.  This pre-reg file DOES NOT embed its own hash
  (F-003 fix: embedding the hash would make the scheme circular and impossible to
  satisfy).  Verification: `sha256(this_file_bytes_on_disk) == receipt.prereg_sha256`.
- `R5.spa_p < 0.05 AND R5.white_rc_p < 0.05 (concordant, post-deflation)` → **CONTINUE** is permitted, but ONLY as authorization to author a confirmatory-only pre-reg (outcome 1) — never as authorization to trade or to re-open the family. That confirmatory pre-reg MUST register as a NEW `trial_id` (org-wide counter increment, NOT a reuse of `576746aa`) AND absorb the R5 36-cell selection burden in its own honest-N / `SR0` deflation inputs; omitting either VOIDS the confirmatory result.

A non-rejection at any power level is a RETIRE trigger. There is no machine-checkable path from this test to "continue spending on the carry family as-is."

### Kill-switch threshold declaration (CRO binding constraint #3, CONSENSUS_2026-04-28.md)

`kill_switch_threshold: 0.767`

Semantics for this one-shot family test (mechanically derived from the ratified frozen spec, §7.3.1
N = 3 row): 0.767 is the best-cell annualized Sharpe required to clear the frozen DSR ≥ 0.95
deflation gate at the elected `N = 3` — any winning cell below it fails the gate and cannot produce
CONTINUE. The binding family-level kill is stricter still: `R5.spa_p >= 0.05 → RETIRE the carry
program` (this section, first criterion), regardless of any cell's Sharpe. No bar executes outside
the historical backtest; the threshold governs the §7.3.6 decision functional, not a live loop.

---

---

# PART II — FROZEN STATISTICAL SPECIFICATION (Mathematician-owned sections, merged at assembly)

> **Status:** FREEZABLE. Every parameter below is a final value. No "to be decided" clauses.
> **Authored by:** Quantitative Mathematician. Trial family: 576746aa.
> **Pins implementation:** `src/forex_system/harness/reality_check.py` (`r5c_hansen_spa`,
> `politis_white_block_length`, `politis_white_block_length_multivariate`) and
> `src/forex_system/harness/carry_universe_matrix.py` (`build_joint_return_matrix`,
> `run_r5_on_carry_universe`), at the git commit recorded in the freeze-receipt.
> Sections 4 and 7 are co-signed: block-length with quant-developer; power with NHT; OOS
> window with HoQR (HoQR proposes the window, the mathematician signs the snooping method).

---

## 1. Null Hypothesis

Let the universe `U` be the `K = 36` cells indexed `k = 1..36`: the 6 carry variants
`{carry, carry_fred, fred_carry_stripped, vol_target_carry, vol_target_carry_no_vol_scaling, carry_momentum}`
crossed with the 6 JPY pairs `{USDJPY, EURJPY, GBPJPY, AUDJPY, CADJPY, NZDJPY}`.

For cell `k` and bar `t = 1..n`, define `f_{k,t}` as the **net-of-cost, post-entry-delay,
benchmark-relative per-bar return** of cell `k`. Concretely, `f_{k,t}` is the bar-`t` simple
return of that cell's backtest equity curve: `f_{k,t} = EC_{k,t}/EC_{k,t-1} - 1`, taken from
`equity_curve.pct_change()` of a `run_backtest` whose signals were already shifted by
`entry_delay_bars = 1` (no-lookahead invariant) and whose equity is already net of the
RealisticCostModel (spread + slippage + commission + direction-dependent swap).

**Benchmark = ZERO.** The benchmark-relative return equals the raw cell return:
`d_{k,t} := f_{k,t} - b_t = f_{k,t}` because `b_t = 0`. Rationale (double-counting): for a carry
strategy the cost-of-carry is already realized inside the swap leg, which is part of the
net-of-cost equity curve. Subtracting an external cost-of-carry benchmark would deduct the carry
return a second time. Zero is therefore the correct, non-double-counting benchmark.

Define the cell expectation `d_k := E[f_{k,t}]` (stationary mean of the benchmark-relative return).

**Frozen null hypothesis (verbatim):**

> **H0: max over cells k of the expected net-of-cost, post-entry-delay, benchmark-relative
> (benchmark = ZERO) per-bar performance d_k ≤ 0**, i.e. `H0: max_{k=1..36} E[d_k] ≤ 0`,
> against `H1: max_{k=1..36} E[d_k] > 0`.

Type discipline: `d_k` is a population parameter (an expectation), not the sample mean. The
test statistic in §2 is the studentized sample estimator of the family maximum. Rejection of H0
means at least one cell has positive expected benchmark-relative performance that the joint null
distribution cannot explain as the maximum of 36 correlated mean-zero series.

---

## 2. Test Statistic and Method

### 2.1 N2 normalization decision (the mathematician owns this)

**DECISION: studentize uniformly.** The per-cell statistic is

```
T_k = sqrt(n) * mean_hat(f_k) / omega_hat_k
```

and the family statistic is the maximum over cells, `T_SPA = max_{k=1..36} T_k`. Raw-mean SPA
is **rejected**.

**Rationale (this is the binding answer to finding N2).** The carry_momentum variant's per-bar
return std is ~1000× smaller than the other five variants (a correct consequence of its
config `risk_per_trade = 0.007` plus fixed pip-cost drag, pinned at
`carry_universe_matrix.py:284-293,429-437`). Under a **raw** mean statistic `max_k sqrt(n)·mean(f_k)`,
that scale disparity makes every carry_momentum cell a near-null column: its mean is ~1000× smaller
in absolute terms, so it can never be the family argmax and contributes nothing — the cell is silently
neutralized, which is a multiplicity/representation defect, not a design choice.

Studentization removes this by construction. `T_k` is **scale-invariant**: replacing
`f_{k,t} → c·f_{k,t}` for any constant `c > 0` multiplies both `mean_hat(f_k)` and `omega_hat_k`
by `c`, leaving `T_k` unchanged. (Type note: this is exact for any positive scalar rescaling of a
single column, because `omega_hat_k` is a positive-homogeneous-degree-1 functional of the column —
a HAC standard error.) Therefore the 1000× std gap does **not** distort the family maximum after
studentization: carry_momentum competes on its t-ratio, the same currency as every other cell. This
is also the standard Hansen (2005) SPA specification (Hansen 2005, §2-3: statistic
`T^SPA = max_l sqrt(n)·d_bar_l / omega_hat_l`), so studentizing is both the scale-correct and the
canonical choice. No separate treatment of carry_momentum is needed; the normalization handles it
by design.

### 2.2 The variance estimator ω̂_k (specified exactly)

`omega_hat_k` is the **heteroskedasticity-and-autocorrelation-consistent (HAC) Newey–West standard
error of the cell mean**, with a **Bartlett (triangular) kernel** and bandwidth tied to the
bootstrap block length. Verified at `reality_check.py:850-864` (`_hac_se`):

```
gamma_0       = (1/n) * sum_t (x_t - x_bar)^2
gamma_lag     = (1/n) * sum_t (x_t - x_bar)(x_{t-lag} - x_bar)
h             = max(L - 1, 1)                     # Bartlett bandwidth = block_length - 1
s2            = gamma_0 + 2 * sum_{lag=1..h} (1 - lag/(h+1)) * gamma_lag
s2            = max(s2, 1e-12)                     # negative-variance clamp (small-sample guard)
omega_hat_k   = sqrt(s2 / n)
```

where `L` is the Politis–White block length of §3. The Bartlett weights `w_lag = 1 - lag/(h+1)`
guarantee a positive-semidefinite long-run variance (Newey–West 1987), so `s2 ≥ 0` up to the
finite-sample correction; the `max(s2, 1e-12)` clamp is the documented small-sample fail-safe, not
a routine path.

### 2.3 Zero / near-zero-variance column guard (frozen)

Two guards are frozen, both already implemented:

1. **HAC-SE (omega) floor (`reality_check.py:868`):** after computing all `omega_hat_k`, the guard
   `omegas = np.where(omegas < 1e-12, 1e-12, omegas)` (`reality_check.py:868`) sets any
   `omega_hat_k < 1e-12` to `1e-12` before the division `T_k = sqrt(n)·mean_hat/omega_hat_k`. This is
   the *omega* floor — distinct from the *internal* long-run-variance clamp `s2 = max(s2, 1e-12)` at
   `reality_check.py:863` (inside `_hac_se`), which guards a single column's `s2` against a negative
   small-sample value before `omega_hat_k = sqrt(s2/n)` is returned. Both floors are `1e-12`; they
   act at different points (the `:863` clamp on each `s2`; the `:868` floor on the vector of returned
   `omega_hat_k`).
   This makes `T_k` finite for any column whose long-run variance underflows (e.g. a cell with no
   trades → constant equity → `mean_hat ≈ 0` and `omega_hat ≈ 0`): such a column resolves to a
   bounded, effectively-null `T_k` rather than `0/0 = NaN` or `+Inf`. The same floor is applied to
   every bootstrap-replicate SE (`reality_check.py:918,924,930`), so the null distribution is
   computed consistently.
2. **No-trade / data-insufficiency cells never reach the statistic silently.** A cell that produces
   `< 2` equity-curve points, mid-series NaN, or a hard rate-data failure is dropped *before*
   matrix assembly with a **structured logged reason** (`carry_universe_matrix.py:519-530,680-715`),
   and a code error (KeyError/TypeError/ConfigError) is re-raised loud — never silently dropped.
   Any drop is recorded; per the no-silent-exclusion constraint, an unlogged drop voids the FWER
   guarantee. **Frozen rule:** the realized `K` entering the max-statistic is whatever survives this
   logged filter; if `K < 36` the dropped cells and reasons are part of the result record.

> **Caveat — DISCHARGED (floor-safe; resolved before freeze).** The studentized statistic
> `T_k = sqrt(n)·mean_hat_k / omega_hat_k` is scale-invariant *in exact arithmetic*; the only way
> finite-precision arithmetic could break that invariance is if the absolute HAC-SE (omega) floor
> `1e-12` (`reality_check.py:868`, `np.where(omegas < 1e-12, 1e-12, omegas)`; the related internal
> `s2 = max(s2, 1e-12)` clamp sits at `reality_check.py:863`) clipped a genuine `omega_hat_k`, which
> would spuriously null the affected
> cell. The routed numerical check has been executed on the realized joint matrix and the floor does
> **not** activate for any cell. On the frozen matrix (`2010-03-15 → 2026-04-06`, `T = 4186`, `0`
> dropped — identical to the STEP 2b build), `L_max = 21.330121 → actual_block_length = 22 →`
> Bartlett bandwidth `h = 21`. The carry_momentum cells — the only ones at risk, with ~1000× smaller
> return std — have `omega_hat_k ∈ [6.472882e-08 (GBPJPY, the minimum over ALL 36 cells), 1.811096e-07
> (NZDJPY)]`. The minimum-to-floor ratio is `6.472882e-08 / 1e-12 = 6.47e+04` — **~4.8 orders of
> magnitude above the floor**, far exceeding the "≥ 3 orders" floor-safe criterion this caveat
> pre-committed. The absolute floor `1e-12` therefore **never clips** any carry_momentum cell (nor
> any other), scale-invariance of `T_k` is preserved exactly, and **no relative-floor substitution is
> required**. The absolute floor stands UNCHANGED at `1e-12`; no pre-freeze code change is made on this
> account. *(No p-value was computed in this check; the diagnostic `T_k` range `[−22.8, +67.0]` for
> carry_momentum and `max_all36 = 200.9` for vol_target_carry:USDJPY are informational only — STEP 4
> remains the one-shot run.)* **Evidence:**
> `.fintech-org/artifacts/2026-06-05T-r5-step3-prereg/qd-omega-floor-check.yaml` (decision
> `implemented-and-verified`, verdict `floor-safe`), pinning `reality_check.py:850-867` (`_hac_se`,
> floor) and `carry_universe_matrix.py:546-820` (joint matrix build).

### 2.4 Method, recentering, and the two p-values

**Primary statistic and decision p-value: Hansen (2005) SPA "consistent".** Implemented in
`r5c_hansen_spa` (`reality_check.py:755-974`). The joint null is imposed by **recentering each
column by its thresholded mean** `mu_bar_k = max(0, mean_hat(f_k))` (`reality_check.py:895`): only
cells with apparent positive performance are recentered to their mean, poor cells are left at their
(negative) sample mean — Hansen's consistent recentering, which removes spurious near-positive
winners from the least-favourable configuration and is strictly more powerful than White's RC when
the universe is dominated by near-zero/negative cells (Hansen 2005, §3.2). The SPA lower
(recenter all by `mean_hat`) and upper (recenter none) bounds are also emitted
(`reality_check.py:898-901,921-931`) but are diagnostic, not the decision statistic.

**Conservative cross-check p-value: White (2000) Reality Check**, computed off the **same**
bootstrap draws (`reality_check.py:874-877,938-939`). RC is recentered by the full sample mean
(`boot - means`, White 2000 eq. 3.7 stationary-bootstrap variant) and is **not** studentized
(`t_rc_obs = max_k sqrt(n)·mean_hat(f_k)`). It is expected and documented that
`white_rc_pvalue ≥ pvalue_consistent`; that ordering is a property of the two nulls, not a
contradiction. RC is reported for transparency; **the pre-registered decision rule is SPA-consistent
primary.**

**Resampling: JOINT same-block stationary bootstrap.** Each replicate resamples the full
36-dimensional per-bar return *vector* in lockstep — the same block draw selects the same time
indices across all cells (`reality_check.py:882-890`, `_joint_bootstrap_once` stacks
`pair_returns[(start+j) % T]`, i.e. whole rows). This preserves the **cross-sectional dependence**,
which is the dominant dependence in this universe (the 36 cells are re-parameterizations/ablations of
ONE rate-differential idea; effective independent dimension ≈ 1-4). Cells are **never** bootstrapped
independently. The bootstrap is the stationary bootstrap of Politis–Romano (1994): block start
uniform on `[0, T)`, block length `Geometric(p = 1/L)`, circular wrap-around.

**p-value formula (both tests):** `p = (1 + #{S_b ≥ S_obs}) / (B + 1)` (`reality_check.py:941-945`),
the +1/+1 convention that prevents the `p = 0` artifact.

---

## 3. Block Length

**Frozen rule: Politis–White (2004) + Patton–Politis–White (2009) automatic data-driven selection,
applied to the joint matrix via `politis_white_block_length_multivariate`, aggregated as the MAX
across the 36 columns, with guard `L ≥ 1`.** Verified at `reality_check.py:313-351`: the multivariate
function computes `politis_white_block_length(X[:, j])` for every column `j` and returns
`L_max = max_j L_j`, then `r5c_hansen_spa` takes `actual_block_length = max(1, ceil(L_max))`
(`reality_check.py:829-835`). The max-across-cells aggregation is the conservative choice: it guarantees
**every** cell's serial dependence is covered by a block at least as long as its own optimal block, so
no cell is under-blocked. `L` is computed from the actual realized series at run time — it is **not**
assumed from the prior near-white ACF proxy finding (which was a single-series proxy and may not hold
for the vol-targeted or FRED-conditioned variants).

The univariate Politis–White estimator (`reality_check.py:119-310`) implements the canonical PW2004/PPW2009
algorithm and has been adjudicated against the R `blocklength::pwsd` reference to <0.5% (WN → 2.392,
AR(0.5) → 7.164, AR(0.9) → 19.963): de-mean; biased autocovariances `R(k)`; data-driven lag cut-off
`m_hat` via the PPW2009 consecutive-lags flat-top threshold `c·sqrt(log10(T)/T)` with
`c = qnorm(0.975) = 1.959963984540054` and `K_N = max(5, ceil(log10(T)))`; band `M = min(2·m_hat,
ceil(sqrt(T)) + K_N, T-1)`; flat-top window `lambda(u)`; `L_opt = (2·G_hat^2 / D_SB)^(1/3)·T^(1/3)`;
upper cap `b_max = ceil(min(3·sqrt(T), T/3))`; lower guard `L ≥ 1`. Degenerate guards: constant column
(`R0 < 1e-14`) → `L = 1`; near-zero `g_hat`/`d_hat` → `L = 1`. **A near-zero-variance carry_momentum
column therefore returns `L = 1` and cannot inflate `L_max`** — it is dominated by the
genuinely-autocorrelated variants, which is correct.

**Why temporal `L` is second-order here (frozen rationale).** The prior materiality sweep over
`L ∈ {1, 2, 3, 5}` produced **0/10 verdict flips** — the SPA decision is insensitive to the temporal
block length over the plausible range. The reason is structural: in this universe the **cross-sectional**
dependence dominates the **temporal** dependence (carry strategy *returns* are near-white despite
persistent positions; ACF lag-1 ≈ -0.003, `|ACF| < 0.017` to lag 60). The joint same-block resampling
captures the dominant (cross-sectional) dependence regardless of `L`; `L` only tunes the second-order
temporal correction. We still compute `L` from the data (no hardcoded value) for correctness and
auditability, but the decision does not hinge on it.

---

## 4. Bootstrap Parameters

**Frozen `K = 5000` bootstrap resamples.** (The implementation default is `B = _B = 10_000`,
`reality_check.py:49`; the frozen run passes `B = 5000` explicitly — comfortably above the `K ≥ 2000`
minimum and within the scope's preferred `5000-10000` band, while keeping the joint
36-column × 5000-replicate × per-replicate-HAC cost bounded for a one-shot run.)

**Monte-Carlo standard error of a bootstrap p-value:** `MC-SE = sqrt(p(1-p)/K)`. At the decision
boundary `p = 0.05`:

| K | MC-SE at p=0.05 | Verdict |
|---|---|---|
| 200 | `sqrt(0.05·0.95/200) = 0.0154` | **PROHIBITED** — straddles the 0.05 threshold; the decision would flip on bootstrap noise alone |
| 2000 | `sqrt(0.05·0.95/2000) = 0.0049` | minimum acceptable |
| **5000 (frozen)** | `sqrt(0.05·0.95/5000) = 0.0031` | **frozen** |
| 10000 | `sqrt(0.05·0.95/10000) = 0.0022` | acceptable upper |

`K = 200` is **explicitly ruled out**: its MC-SE (0.0154) is larger than a third of the entire
distance from `p = 0.05` to `p = 0`, so a borderline result could not be distinguished from noise.
`K` controls p-value *resolution* (Monte-Carlo precision), **not** statistical power; power is set by
`n` and the true effect (see §6).

**RNG seeding (frozen, deterministic, logged).** RNG = `numpy.PCG64` (`reality_check.py:825`).
Child seeds are derived from a single `master_seed`: R5c uses `master_seed + 2`
(`reality_check.py:824`). **Frozen `master_seed = 576746` (the trial-id numeric stem).** The seed,
RNG identifier (`"numpy.PCG64"`), and numpy version are logged on every invocation
(`reality_check.py:359-367`, `_log_seed_info`). The run is fully reproducible from the frozen seed +
the frozen code commit; both go in the freeze-receipt.

---

## 5. Error Control

- **α = 0.05** (one-sided; H1 is `max_k E[d_k] > 0`). `_ALPHA = 0.05`, `reality_check.py:48`.
- **Family-wise error rate (FWER), strong control, via the max-statistic** over the single pooled
  family of (up to) 36 cells. The max-statistic SPA construction controls
  `P(reject H0 | H0 true) ≤ α` jointly over all 36 cells — the joint same-block bootstrap null *is*
  the distribution of `max_k T_k` under the least-favourable configuration, so no separate Bonferroni
  or Romano–Wolf step is layered on top. One pooled family ⇒ one p-value ⇒ one decision.
- **FWER, not FDR (frozen rationale).** The firm decision is a **single binary** CONTINUE/WIND-DOWN.
  The cost object is therefore `P(any false CONTINUE) = P(at least one false rejection) = FWER`. FDR
  controls the *expected proportion* of false discoveries — the right object when you will act on a
  *set* of discoveries (e.g. sizing a portfolio of many strategies), which is not the case here. A
  single false "this family has alpha" rejection is the entire harm, so FWER is the correct control.

---

## 6. Power and Limitations

**Class-level power estimate: ≈ 20–35%** at a true per-cell **annualized** Sharpe of ≈ **0.30**, over
the available daily sample, under FWER control across the 36 cross-correlated cells.

**Derivation / source and its assumptions.** The figure originates from the ratified scope
(`CONSENSUS_2026-06-02_r5_scope.md` §R5 test design and the NHT dissent §1) and is confirmed here.
The ~0.30 Sharpe is **annualized** (confirmed: the only economically plausible reading — a per-bar
daily 0.30 would be a trivially-significant ~4.8 annualized Sharpe and the framing would be wrong).
Sketch of the back-of-envelope that yields it: a per-cell annualized Sharpe of 0.30 over `n ≈ 4186`
daily bars (the joint inner-join index length; confirm exact `n` against the realized matrix at run
time) implies a single-cell t-statistic of order `t ≈ SR_annual · sqrt(n / 252) ≈ 0.30 · sqrt(4186/252)
≈ 0.30 · 4.08 ≈ 1.22` — already **below** the ordinary 1.96 two-sided threshold *before* any
multiplicity correction. Imposing FWER over ~36 cross-correlated cells (effective independent
dimension ≈ 1-4) raises the rejection bar further, leaving rejection probability in the ~20-35% band.
**Assumptions this rests on:** (i) the true edge, if any, is ~0.30 annualized and roughly constant
across the OOS window; (ii) returns are approximately stationary so the block bootstrap null is valid;
(iii) effective independent dimension 1-4 (cross-sectional correlation is high). The number is a
class-level order-of-magnitude, not a precise operating characteristic; an exact power curve would
require a Monte-Carlo under an assumed alternative (routed to quant-developer if the firm wants it,
but **not required** for the decision).

**Binding statement (frozen).** Low power makes a **non-rejection (`p ≥ 0.05`) UNINFORMATIVE as
evidence of no-edge** — it is *not* proof that carry alpha is zero. **However, the firm action under
non-rejection is WIND-DOWN regardless.** Power does *not* license a third "inconclusive, keep
spending" outcome. The honest reading of an underpowered non-rejection is "no *distinguishable*
class-level alpha at the achievable power," and combined with the firm's zero validated OOS survivors,
that maps to **WIND-DOWN**. This is pre-committed before any draw.

---

## 7. Snooping Treatment (method requirements — co-signed with HoQR)

These are the firm's longest-studied strategies on the 2010–2026 data; that spent selection is sunk
and is **not** retroactively controlled by a prospective Reality Check on the same data (the SPA/RC
null controls only the 36 looks pre-registered here, not the prior trial history). A face-valid clean
`p` therefore requires **one** of the two admissible methods below. The mathematician signs the method;
HoQR proposes the concrete window/inputs.

### 7.1 Admissible Method A — genuine post-development hold-out (preferred)

A window qualifies as a genuine hold-out **iff all** of the following hold:
1. The window's bars were **generated after** the last development/parameter-selection touch of **every
   one of the 6 variants** (no variant's design, parameters, or feature choices were informed by any bar
   in the window). HoQR must attest this per-variant with dates.
2. The window was **never** used in any prior carry trial, plot, or metric the firm acted on.
3. The window is frozen in the pre-reg **before** any R5 draw, by date range and bar count.
4. The window has `n ≥` enough bars for the block bootstrap to be valid (`n` comfortably exceeds
   `L_max`; in practice `n` in the hundreds+).

If a window meeting (1)-(4) exists, R5 runs on that window **only**, and no haircut is required because
the snooping is genuinely escaped. **I will co-sign HoQR's window proposal exactly when HoQR provides
the per-variant last-development-date attestation establishing (1) and the never-used attestation
establishing (2).** Absent that attestation, Method A is not available and Method B applies.

### 7.2 Admissible Method B — deflated-Sharpe-style haircut (fallback when no clean hold-out exists)

If R5 must run on the full snooped sample, the cell Sharpe must clear a **selection-deflated**
threshold before its `p` is treated as face-valid. Use the Bailey–López de Prado (2014) Deflated
Sharpe Ratio. The frozen benchmark (expected maximum Sharpe under the null of zero true skill across
`N` trials) is:

> `SR0 = sqrt(Var[SR_n]) · [ (1 - euler_gamma) · Z^{-1}(1 - 1/N) + euler_gamma · Z^{-1}(1 - 1/(N·e)) ]`

where `Z^{-1}` is the inverse standard-normal CDF, `euler_gamma ≈ 0.5772` is the Euler–Mascheroni
constant, `Var[SR_n]` is the **variance of the Sharpe estimates across the `N` trials**, and `N` is the
number of **independent** trials. The Deflated Sharpe Ratio then evaluates the observed best Sharpe
against `SR0` using the DSR test statistic that incorporates the return series' **skewness and excess
kurtosis** and sample length (Bailey–López de Prado 2014, eqs. for `SR0` and `DSR`).

**Frozen inputs — the `N` decision (this is the load-bearing call).** `N` must be the **honest
effective number of independent trials**, and the two candidate sources are explicitly distinguished:
- **Org-wide `trials.jsonl` count (currently 37):** this is the *total* trial count and **overstates**
  the independent looks on the carry family specifically — it includes non-carry trials and counts
  correlated re-parameterizations as if independent.
- **Honest-N registry (the correct input):** `N` = the number of **effectively independent** carry
  looks. Given the scope finding that the 36 cells have effective independent dimension ≈ 1-4 and that
  the 6 variants are re-parameterizations/ablations of ONE rate-differential idea, the honest `N` for
  the carry family is **small** (single-digit), not 36 and not the org-wide total.

> **Frozen rule:** if Method B is used, `N` is taken from the **honest-N registry of independent carry
> looks**, NOT the raw `trials.jsonl` line count. `Var[SR_n]` is computed over those same independent
> looks' Sharpe estimates. Using the inflated raw trial count would *over*-deflate (too conservative,
> understating any real edge); using `N = 1` would *under*-deflate (snooping uncontrolled). The
> honest-N registry is the pre-committed source. The exact `N` value and `Var[SR_n]` are an input HoQR
> supplies and the mathematician signs; they are frozen in the pre-reg before any draw.

**Condition under which I co-sign HoQR's window proposal:** I co-sign when HoQR's proposal specifies,
in frozen form, **either** (A) a window with the per-variant post-development + never-used attestation
of §7.1, **or** (B) the full-sample run *plus* the honest-`N` value, its `Var[SR_n]`, and the DSR
threshold computed from the formula above. "We used all available data" with no hold-out and no haircut
is **not** signable.

---

### 7.3 Frozen DSR gate and integrated decision functional (Mathematician — finalizes Method B)

This section freezes the Method-B (§3.2, §3.4) deflation gate and binds it to the SPA decision of
§4/§5. It is the load-bearing numerical freeze: after this is ratified, `SR0`, the DSR statistic, the
threshold, and the integrated CONTINUE/AMBIGUOUS/WIND-DOWN rule are immutable. All quantities below
are pinned to the canonical firm implementation `src/forex_system/harness/dsr.py`
(`compute_dsr`, `expected_max_sr`) — the Mathematician-corrected (2026-05-31) BLP (2014)
implementation, NOT a hand-rolled variant.

#### 7.3.1 Adjudication of the §3.4 inputs (HoQR-supplied, Mathematician-signed)

- **`N` input — ACCEPTED; originally proposed `N = 2`, RE-ELECTED `N = 3` per §3.4 (the N-axis bias-direction disclosure below drove the re-election; the §7.3.3 table maps the election to the frozen scalar `SR0 = 0.363623`).** The original `N = 2` proposal was admissible under the §7.2 frozen rule ("`N` from the honest-N registry of
  independent carry looks, not the raw `trials.jsonl` count, not 1"). HoQR applied
  `honest_n.py:40-81` suffix-strip dedup (8 carry pre-regs → 5 keys), then collapsed the shared
  `rate_differentials.parquet` feed to **two genuinely distinct information sources** — (1) pure
  rate-differential carry, (2) the carry+momentum hybrid (which injects an SMA price-trend signal
  absent from the carry look). `N = 2` lies inside both ratified scope ranges (HoQR 1–2, NHT 2–4) and
  is neither the under-deflating `N = 1` nor the double-counting `N = 36/37`. Signed.

- **Sharpe table `{SR_1 = 0.80, SR_2 = 0.197}` — ACCEPTED, with the provenance caution weighed; the
  conservatism claim is restricted to the Var/spread axis ONLY.** `SR_1 = 0.80` is registry-unverified
  (pre-reg-documented at `carry_fred.md:16`, `fred_carry_stripped.md:18,66`, with no `trials.jsonl`
  row) and its "Bet #1 = carry_fred" label repeats the labeling that the 2026-06-02 adjudication
  flagged (Bet #1 / trial `87fa1d23` was a momentum portfolio, not carry_fred). The Mathematician
  records this as a genuine provenance weakness.

  **The two axes of `SR0` run in OPPOSITE directions — this must be stated honestly:**
  - **Var/spread axis (conservative-if-wrong).** `SR0` is strictly increasing in `Var[SR_n]`, which
    is strictly increasing in the spread `|SR_1 − SR_2|`. An *over*-stated `SR_1` therefore *raises*
    the haircut (makes CONTINUE harder); on this axis the input error can only cause a false
    WIND-DOWN, never a false CONTINUE. This is the only axis on which the "conservative-if-wrong"
    defense holds.
  - **N axis (ANTI-conservative — disclosed, NOT defended).** `SR0` is strictly **increasing in `N`**
    (the bracket `(1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−1/(Ne))` grows with `N`, since both quantile arguments
    increase toward 1). At the elected sample dispersion `sqrt(Var) = 0.426385`, the verified scalars
    are `SR0(N=2) = 0.221616`, `SR0(N=3) = 0.363623`, `SR0(N=4) = 0.448609` (table below). Pinning `N`
    at the **floor** of the credible range (HoQR 1–2 / NHT 2–4) is therefore the **LEAST-deflating
    admissible choice** — it gives the *smallest* `SR0` and is **biased toward a false CONTINUE**, the
    opposite direction from the Var-axis conservatism. I do **not** describe the `N = 2` election as
    conservative. It is the smallest defensible `N` (top of HoQR's range, bottom of NHT's), and on the
    N axis a smaller `N` makes the gate *easier*, not harder. The N VALUE is HoQR's pin and is being
    re-adjudicated in parallel; whatever HoQR pins maps to a frozen scalar via the table below with no
    recompute.

  **Net.** The Var-axis conservatism and the N-axis anti-conservatism are not netted into a single
  "conservative" claim. The honest statement is: the gate is conservative against `SR_1`-provenance
  error and anti-conservative against under-estimation of `N`. The mitigation is that `N` is bounded
  above by NHT's own ceiling (4), so the worst-case under-deflation is bounded — `SR0` cannot fall
  below `0.221616` for any admissible `N ≥ 2`, and the table makes the gate-strength consequence of
  each candidate `N` explicit so the choice is not hidden.

  **Frozen SR0 table at the elected sample `sqrt(Var[SR_n]) = 0.426385` (§7.3.2), for the credible
  `N ∈ {2, 3, 4}`** (derivations in §7.3.3; quantiles to 6 decimals):

  | N | Z⁻¹(1−1/N) | Z⁻¹(1−1/(N·e)) | bracket = (1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e)) | **SR0 (annualized)** | per-obs SR0_pp (÷√252) | Best-cell annualized SR needed to clear DSR ≥ 0.95 |
  |---|---|---|---|---|---|---|
  | **2** | Z⁻¹(0.500000) = 0.000000 | Z⁻¹(0.816060) = 0.900452 | 0.519756 | **0.221616** | 0.013961 | ≈ **0.625** |
  | **3** **(elected)** | Z⁻¹(0.666667) = 0.430727 | Z⁻¹(0.877374) = 1.161957 | 0.852804 | **0.363623** | 0.022906 | ≈ **0.767** |
  | **4** | Z⁻¹(0.750000) = 0.674490 | Z⁻¹(0.908030) = 1.328722 | 1.052123 | **0.448609** | 0.028260 | ≈ **0.852** |

  (γ = 0.5772156649; e = 2.718281828; 1−γ = 0.4227843351. The "needed annualized SR" column is the
  smallest annualized best-cell Sharpe that yields `DSR ≥ 0.95`, i.e. `z ≥ Φ⁻¹(0.95) = 1.644854`,
  under `var_term ≈ 1` and `T = 4186` (`sqrt(T−1) = 64.692`): `SR_pp ≥ SR0_pp + 1.644854/64.692 =
  SR0_pp + 0.025427`, annualized `SR_ann ≥ SR0_ann + 0.025427·sqrt(252) = SR0_ann + 0.403631`. The
  `var_term ≈ 1` approximation holds to the displayed precision for the small per-obs Sharpes here;
  the runner uses the cell's actual skew/kurtosis at STEP 4. All quantile values are
  `scipy.stats.norm.ppf`-grade exact values (orchestrator-verified mechanical arithmetic); the
  prior hand-bracketed values for N = 3 and N = 4 are superseded.)

#### 7.3.2 Var[SR_n] estimator election — SAMPLE (÷(N−1)) = 0.1818

**ELECTED: the sample estimator `Var[SR_n] = 0.1818045`, `sqrt(Var[SR_n]) = 0.426385`.** (The
population/÷N value `0.0909` is recorded as the less-conservative alternative.)

Basis (three reasons, all pointing the same way):
1. **Definition.** BLP's `Var[SR_n]` is "the variance of the Sharpe estimates across the `N` trials" —
   a cross-trial sample variance. The unbiased estimator of a population variance from `N` draws is
   the `÷(N−1)` form; the `÷N` form is biased low, which would *under*-deflate.
2. **`N = 2` makes the bias maximal.** At the smallest possible `N`, the `÷N` vs `÷(N−1)` gap is a
   factor of 2 in variance (`0.0909` vs `0.1818`) — the regime where electing the biased-low estimator
   is least defensible.
3. **Provenance caution (§7.3.1).** With `SR_1 = 0.80` registry-unverified, the conservative
   (larger-`Var`, higher-`SR0`) election is the honest choice: if the 0.80 is genuine, the gate is
   correctly calibrated-to-conservative; if it is inflated, the larger spread is already absorbed into
   a higher bar rather than a falsely-easy one.

The cost of this conservatism is borne entirely by the (pre-committed, most-likely) WIND-DOWN posture;
over-deflation cannot manufacture a false CONTINUE. The asymmetry is therefore correct.

#### 7.3.3 The frozen SR0 benchmark scalar

`SR0` is the BLP (2014) expected-maximum-Sharpe benchmark under the null of zero true skill across `N`
trials, in the §7.2 Var-plug-in rendering:

> `SR0 = sqrt(Var[SR_n]) · [ (1 − γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e)) ]`

With the elected sample dispersion `sqrt(Var[SR_n]) = 0.426385`, `γ = 0.5772156649`,
`1−γ = 0.4227843351`, `e = 2.718281828`, the bracket and `SR0` are derived for each credible
`N ∈ {2, 3, 4}` (the ELECTED pin is `N = 3` per §3.4; the full set is frozen so the election
maps to a scalar with no recompute, and `N = 2` / `N = 4` remain recorded contingencies). The two quantile arguments per `N` are
`a1 = 1 − 1/N` and `a2 = 1 − 1/(N·e)`.

**N = 2 (contingency — superseded by the §3.4 `N = 3` election):**
- `a1 = 1 − 1/2 = 0.500000`; `Z⁻¹(0.500000) = 0.000000` (median; zeroes the `(1−γ)` leg).
- `a2 = 1 − 1/(2e) = 1 − 0.183940 = 0.816060`; `Z⁻¹(0.816060) = 0.900452`.
- bracket `= 0.4227843·0.000000 + 0.5772157·0.900452 = 0.519756`.
- `SR0 = 0.426385 · 0.519756 = 0.221616`.

**N = 3 (ELECTED per §3.4):**
- `a1 = 1 − 1/3 = 0.666667`; `Z⁻¹(0.666667) = 0.430727`. *(Exact `scipy.stats.norm.ppf`-grade value,
  orchestrator-verified mechanical arithmetic. Prior hand-bracketed derivation confirmed this value
  to 6 dp; it stands.)*
- `a2 = 1 − 1/(3e) = 1 − 1/8.154845 = 1 − 0.122626 = 0.877374`; **`Z⁻¹(0.877374) = 1.161957`**.
  *(Exact `scipy.stats.norm.ppf`-grade value, orchestrator-verified mechanical arithmetic. The prior
  hand-bracketed value 1.162095 was off by 1.4 × 10⁻⁴ and is superseded.)*
- bracket `= 0.4227843·0.430727 + 0.5772157·1.161957 = 0.182103 + 0.670701 =` **`0.852804`**.
- `SR0 = 0.426385 · 0.852804 =` **`0.363623`**.

**N = 4:**
- `a1 = 1 − 1/4 = 0.750000`; `Z⁻¹(0.750000) = 0.674490` (the canonical upper-quartile probit;
  exact `scipy.stats.norm.ppf`-grade value, confirmed unchanged).
- `a2 = 1 − 1/(4e) = 1 − 1/10.873127 = 1 − 0.091970 = 0.908030`; **`Z⁻¹(0.908030) = 1.328722`**.
  *(Exact `scipy.stats.norm.ppf`-grade value, orchestrator-verified mechanical arithmetic. The prior
  hand-bracketed value 1.328869 was off by 1.5 × 10⁻⁴ and is superseded.)*
- bracket `= 0.4227843·0.674490 + 0.5772157·1.328722 = 0.285167 + 0.767059 =` **`1.052123`** (prior: 1.052310, superseded).
- `SR0 = 0.426385 · 1.052123 =` **`0.448609`** (prior: 0.448688, superseded).

> **FROZEN (elected, `N = 3`): `SR0 = 0.363623` (annualized Sharpe units), per-obs
> `SR0_pp = 0.363623 / sqrt(252) = 0.022906`.** *(Contingency scalar `N = 2` (recorded not elected):
> `SR0 = 0.221616`, per-obs `0.013961`. Contingency scalar `N = 4` (recorded not elected): `SR0 =
> 0.448609`, per-obs `0.028260`.)* See the §7.3.1 table for the per-obs values and the best-cell
> annualized Sharpe each `N` requires to clear `DSR ≥ 0.95`. `SR0` is in the same **annualized**
> units as `SR_1`, `SR_2`, and the firm's `calculate_metrics` Sharpe.
>
> All 6-dp normal-quantile values in §7.3.1 and the derivations above are `scipy.stats.norm.ppf`-grade
> exact values (orchestrator-verified mechanical arithmetic). The `N = 3` and `N = 4` quantiles
> `Z⁻¹(0.877374) = 1.161957` and `Z⁻¹(0.908030) = 1.328722` supersede the prior hand-bracketed
> values (1.162095 and 1.328869 respectively, each off by ~1.4–1.5 × 10⁻⁴); the `N = 2` value
> `Z⁻¹(0.816060) = 0.900452` stands (sub-ULP difference from orchestrator's 0.900453; retained).
> `scipy.stats.norm.ppf` is required at run time per the A-5 pin (§7.3.4); the values here are the
> frozen reference, not the hand-bracketing.

**Units reconciliation (must hold at run time).** The canonical `compute_dsr` (`dsr.py:107-207`)
operates in **per-observation** units: it converts the input annualized Sharpe via
`SR_pp = SR_ann / sqrt(252)` (`dsr.py:180`) and computes its own per-obs expected-max benchmark
`expected_max_sr(n_trials, T) = bracket / sqrt(T−1)` *internally* (`dsr.py:198`, `expected_max_sr` at
`dsr.py:46-104`). The §7.2 Var-plug-in `SR0` above is the *annualized* analogue of that benchmark,
with the empirical cross-trial dispersion `sqrt(Var[SR_n]) = 0.426385` substituted for the
null-theoretical per-obs dispersion `1/sqrt(T−1)`. The two renderings are the same BLP quantity under
two dispersion estimators; on this matrix (`T = 4186`) the elected (sample) rendering is the more
conservative (elected `N = 3`: `SR0_ann = 0.363623` → per-obs `0.022906`, vs the code's internal null-dispersion
benchmark `expected_max_sr(2, 4186) = 0.008034` per-obs).

**Why the frozen `SR0` is NOT injectable into `compute_dsr` — and the execution mechanism that
resolves it (election: SPEC CHANGE, no code change).** `compute_dsr(sharpe_ratio, n_observations,
skewness, excess_kurtosis, n_trials, periods_per_year)` (`dsr.py:107-114`) has **no benchmark
parameter**. It computes its deflation benchmark *internally* from `expected_max_sr(n_trials, T)`
(`dsr.py:198`), whose dispersion is the null-theoretical `1/sqrt(T−1)` (`dsr.py:103`), NOT the
empirical cross-trial `sqrt(Var[SR_n])`. There is **no integer `n_trials`** for which
`expected_max_sr(n_trials, 4186)` equals the frozen per-obs target `0.022906` (elected `N = 3`):
`expected_max_sr(2, 4186) = 0.008034`, and the closest integer over the whole range, `n_trials = 8`,
gives `0.022553` — neither reproduces `0.022906`. (The same impossibility held for the superseded
`N = 2`-era target `0.013961`: closest was `n_trials = 3` → `0.013183`.) The earlier "pass the frozen `SR0` as the benchmark — a parameter pin,
not a code change" claim was therefore **factually wrong**: the signature admits no such argument, so
the only ways to use `compute_dsr` as the execution path would be to **edit `dsr.py` post-freeze
(forbidden)** or to mis-set `n_trials` to a value that does not reproduce the frozen benchmark (which
silently changes the test). Accordingly:

> **FROZEN EXECUTION MECHANISM (spec change, no code change to `dsr.py`).** The DSR gate is computed
> at STEP 4 by the dedicated **STEP-4 DSR-gate runner** (§1.3 permitted-change item 2), **directly
> from the frozen formula**
> `DSR = Φ( (SR_pp − SR0_pp) · sqrt(T − 1) / sqrt(var_term) )` with the §7.3.4 conventions and the
> **frozen literal** `SR0_pp = 0.022906` (per-obs; `= 0.363623 / sqrt(252)`; elected N = 3 per §3.4). `compute_dsr` is the
> **CONVENTIONS reference only** — it pins (i) the per-obs unit convention `SR_pp = SR_ann/sqrt(252)`
> (`dsr.py:180`), (ii) the corrected variance-of-Sharpe kurtosis term `(γ4_excess + 2)/4`
> (`dsr.py:184`), (iii) the two degenerate early-return paths (§7.3.4: `var_term ≤ 0 → 0.0` at
> `dsr.py:187-195`, and `sharpe_ratio ≤ 0 → 0.0` at `dsr.py:168-169`), and (iv) the final
> `Φ(z)` clip to `[0,1]` (`dsr.py:205-207`). `compute_dsr` is **NOT** the execution path: its internal
> `expected_max_sr` benchmark is bypassed entirely because the frozen `SR0_pp` is supplied directly.
> The runner MUST reproduce these four conventions exactly; any divergence between the runner's
> arithmetic and the `compute_dsr` conventions it references is a TECHNICAL FAILURE (§5 outcome 5),
> not a license to fall back to the code's internal benchmark. `dsr.py`, `reality_check.py`, and
> `carry_universe_matrix.py` are bit-for-bit unchanged for this gate; the runner is the only new code
> and is pinned by the freeze-receipt commit.

#### 7.3.4 The DSR statistic evaluated at run time (exact)

The DSR is evaluated on **the single best cell** — the cell `k*` that attains the family maximum
studentized statistic `T_SPA = max_k T_k` (§2.1). Its skewness and excess kurtosis are that cell's
own (`γ3 = skew(f_{k*})`, `γ4_excess = excess_kurtosis(f_{k*})` in Fisher convention, i.e.
`kurtosis − 3`), computed on cell `k*`'s realized per-bar net-of-cost return series over the frozen
common index. **It is NOT computed on a pooled series and NOT on any other cell.**

> **Estimator-convention pins (frozen, A-5):**
> - **Sample-bias flag:** `γ3` and `γ4_excess` are computed with `scipy.stats.skew(...,
>   bias=True)` and `scipy.stats.kurtosis(..., fisher=True, bias=True)` — the **biased** (uncorrected,
>   maximum-likelihood) sample estimators, `bias=True` (scipy's default). With `T = 4186` the
>   bias correction is `O(1/T)` and changes `γ3, γ4` in the fourth+ decimal — immaterial to the gate —
>   but the convention is pinned so the STEP-4 runner is deterministic and not subject to a silent
>   `bias=False` substitution.
> - **scipy is REQUIRED at run time.** The STEP-4 runner MUST execute under an environment where
>   `scipy.stats` (`norm.ppf`, `norm.cdf`, `skew`, `kurtosis`) is importable. The `dsr.py` ImportError
>   fallbacks — the Beasley-Springer-Moro probit approximation (`dsr.py:72-90`) and the `math.erf`
>   CDF approximation (`dsr.py:176-177`) — are **NOT** the frozen path; if scipy is absent at run time
>   that is a TECHNICAL FAILURE (§5 outcome 5), not a license to certify on the approximation. The
>   frozen quantiles in §7.3.3 are the exact `scipy.stats.norm.ppf` values. The statistic
(Bailey–López de Prado 2014, eq. 10; pinned to `dsr.py:compute_dsr`):

```
SR_hat_pp  = SR_hat_ann / sqrt(252)                 # per-obs Sharpe of cell k* (annualized ÷ sqrt(252))
SR0_pp     = 0.363623 / sqrt(252) = 0.022906        # FROZEN benchmark, per-obs (§7.3.3; elected N=3)
var_term   = 1 − γ3·SR_hat_pp + ((γ4_excess + 2)/4)·SR_hat_pp²
DSR        = Φ( (SR_hat_pp − SR0_pp) · sqrt(T − 1) / sqrt(var_term) )
```

**Unit discipline (binding).** `SR_hat`, `SR0`, `γ3`, `γ4` ALL enter in **per-observation** units; the
annualized cell Sharpe is divided by `sqrt(252)` exactly once before entering, matching
`dsr.py:180`. The variance-of-Sharpe term uses **excess** kurtosis with the `+2` coefficient
(`(γ4_excess + 2)/4`, the corrected kurtosis convention, `dsr.py:184` — NOT `+3`, NOT `+1`), because
`var[SR] ∝ 1 − γ3·SR + (γ4_nonexcess − 1)/4·SR²` and `γ4_nonexcess − 1 = γ4_excess + 2`. `T = 4186`
(the frozen common-index length). `Φ` is the standard-normal CDF. **Two degenerate paths are pinned,
both reference-matched to `compute_dsr` and both resolving to `DSR = 0.0` so the gate FAILS (neither
is a TECHNICAL FAILURE):**
1. **`var_term ≤ 0 → DSR = 0.0`** (cannot certify the variance of the Sharpe estimator;
   `dsr.py:187-195`). The STEP-4 runner reproduces this guard before taking `sqrt(var_term)`.
2. **`SR_hat ≤ 0 → DSR = 0.0`** (a non-positive winning Sharpe cannot exceed the positive deflated
   benchmark; `dsr.py:168-169`, the early return `if sharpe_ratio <= 0.0: return 0.0`). This is a
   **defensive pin, not an expected path**: under the §7.3.6 ordering the DSR gate is only consulted
   when `p_SPA < 0.0469` (a genuine SPA rejection), and a genuine rejection against a zero benchmark
   with a non-positive best-cell Sharpe is essentially impossible — the studentized family max `T_SPA`
   is driven by the cell with the largest positive t-ratio, so its annualized Sharpe is positive
   whenever the SPA null is rejected. The pin exists so that, in the pathological event of a
   sign/units mishandling upstream, the gate fails closed (`DSR = 0.0 → not CONTINUE`) rather than
   silently certifying.

#### 7.3.5 Frozen threshold

> **FROZEN: the DSR gate is cleared iff `DSR ≥ 0.95`.**

Basis. `DSR = Φ(z)` is the probability that cell `k*`'s true Sharpe exceeds the selection-deflated
benchmark `SR0`; `DSR ≥ 0.95` is the one-sided 95% certainty that the best cell's edge survives the
snooping charge. The threshold is set **equal to `1 − α` with `α = 0.05`** (§5), so the DSR gate and
the SPA p-gate enforce the **same** 5% false-positive tolerance on the two distinct error channels
they each control (SPA: family-wise rejection error under the joint null; DSR: selection/overfit
inflation of the winning Sharpe). Matching them prevents one gate from being silently slacker than the
other. A laxer `0.90` would admit a 10% overfit-survival probability — inconsistent with `α = 0.05`;
a stricter `0.99` would over-charge beyond the firm's stated error budget. `0.95` is the
budget-consistent choice and is frozen.

#### 7.3.6 The integrated decision functional (binds §4 / §5)

Let `p_SPA` = the Hansen-SPA "consistent" p-value (§2.4, the primary decision p-value),
`p_RC` = the White-RC cross-check p-value, and `DSR` = the §7.3.4 statistic on cell `k*`. The frozen
firm decision is:

The functional is defined as an **ordered, mutually-exclusive, exhaustive** evaluation: the FIRST
matching rule fires and STOPS evaluation. The order is chosen so that no boundary case can buy
CONTINUE — every tie resolves toward the more conservative (non-CONTINUE) branch. Inputs are
`p_SPA`, `p_RC`, `DSR` (cell `k*`), and the run-integrity flags. Evaluate top to bottom:

> **RULE 0 — TECHNICAL FAILURE** (→ §5 outcome 5: HALT, root-cause, re-freeze, re-run; NO p-value is
> read). Fires iff a code error, data-integrity fault, unlogged cell drop (`K ≠ 36` with a null/empty
> reason), freeze-receipt mismatch, or any divergence of the STEP-4 runner from the §7.3.4 `compute_dsr`
> conventions (§7.3.3) is detected. If RULE 0 fires, RULES 1–4 are NOT evaluated.
>
> **RULE 1 — AMBIGUOUS (straddle)** (→ §5 outcome 4). Fires iff RULE 0 did not, AND the family p
> straddles the threshold within one MC-SE: **`|p_SPA − 0.05| ≤ MC-SE = 0.0031`** (§4). This rule is
> evaluated **before** any CONTINUE/WIND-DOWN test, so a result whose `p_SPA` sits in
> `[0.0469, 0.0531]` is AMBIGUOUS **regardless of `DSR` or `p_RC`** — a boundary p is not
> distinguishable from noise and must NOT buy CONTINUE and must NOT be read as a clean WIND-DOWN.
>
> **RULE 2 — WIND-DOWN** (→ §5 outcomes 2 & 3, binding regardless of power). Fires iff RULES 0–1 did
> not, AND **`p_SPA ≥ 0.05`** (i.e. `p_SPA ≥ 0.05` and outside the straddle band, so
> `p_SPA > 0.0531`). The carry family is statistically indistinguishable from chance at the class
> level.
>
> **RULE 3 — CONTINUE** (→ §5 outcome 1: confirmatory-only pre-reg, never trade/re-open). Fires iff
> RULES 0–2 did not (so `p_SPA < 0.05` AND outside the straddle band, i.e. `p_SPA < 0.0469`), AND
> **BOTH (ii) `DSR ≥ 0.95`** (deflation gate cleared) **AND (iii) `p_RC < 0.05`** (White-RC
> concordant). CONTINUE is NECESSARY-BUT-NOT-SUFFICIENT and only authorizes a confirmatory-only
> pre-reg.
>
> **RULE 4 — AMBIGUOUS (gate-fail / anomalous)** (→ §5 outcome 4; the catch-all, guaranteeing
> exhaustiveness). Fires iff RULES 0–3 did not — i.e. `p_SPA < 0.0469` (a genuine, non-straddle SPA
> rejection) BUT **(`DSR < 0.95` OR `p_RC ≥ 0.05`)**, OR only an isolated subset / a
> normalization-driven distortion (N2 carry_momentum near-null artifact) produced the apparent
> rejection. A bare SPA rejection that cannot clear the selection-deflation charge or is not
> White-RC-concordant maps here, NEVER to CONTINUE.

**Exhaustiveness and mutual-exclusivity (proof).** The rules partition the joint outcome space on
the disjoint, ordered conditions {technical-fail} → {straddle} → {`p_SPA ≥ 0.05` ∧ ¬straddle} →
{`p_SPA < 0.05` ∧ ¬straddle ∧ all-gates} → {else}. Because evaluation stops at the first match, the
bands are disjoint by construction; because RULE 4 is the unconditional else, every non-technical-fail
outcome lands in exactly one of RULES 1–4. The previously-overlapping instance — `p_SPA = 0.048`,
`DSR = 0.96`, `p_RC = 0.01` — now resolves **unambiguously to RULE 1 (AMBIGUOUS, straddle)**, because
`|0.048 − 0.05| = 0.002 ≤ 0.0031` is tested before the CONTINUE rule; the prior text let this same
instance match both CONTINUE and AMBIGUOUS.

> **Boundary-case ruling (binding, restated for emphasis):** when a result lands on or within the
> MC-SE straddle band of `0.05`, **AMBIGUOUS wins** (RULE 1), never CONTINUE. The document's posture
> (§1.2, §4) is that a boundary result must NOT buy CONTINUE: a p indistinguishable from 0.05 at the
> frozen `K = 5000` resolution is, by the firm's own error budget, not a clean class-level rejection.
> The straddle check is therefore positioned ahead of both the WIND-DOWN and CONTINUE tests so that
> the tie can resolve to neither a false CONTINUE nor a falsely-clean WIND-DOWN.

**The load-bearing branch ruling (made precise):** **`p_SPA < 0.05` but the DSR gate FAILS
(`DSR < 0.95`) → AMBIGUOUS, NOT CONTINUE and NOT WIND-DOWN.** Rationale: a bare SPA rejection that
cannot survive the selection-deflation charge is exactly the snooping artifact Method B exists to
catch — it is *necessary-but-not-sufficient* (§3.2, §4 CONTINUE clause). It does not license CONTINUE
on the family (the deflation says the winning Sharpe is consistent with selection luck), and it is not
a clean WIND-DOWN either (the SPA null *was* rejected, so "indistinguishable from chance" is not the
honest description). It maps to the confirmatory-only gate of §5 outcome 4: the specific surviving
structure may be carried into a fresh, separately-pre-registered confirmatory test with its own
freeze, treated as a brand-new hypothesis. No capital, no re-opening of the 36-cell family.

This functional is consistent with §4 (CONTINUE is necessary-but-not-sufficient and only ever buys a
confirmatory pre-reg) and §5 (the action map). Where §4/§5 said "post-deflation," §7.3.6 is the exact
operationalization of that phrase.

---

*Mathematician sign-off applies to §1, §2, §3 (co-signed: quant-developer), §4, §5, §6 (co-signed: NHT),
§7 (co-signed: HoQR). Pinned to the freeze-receipt git commit of reality_check.py and
carry_universe_matrix.py.*

---

# FREEZE BLOCK — criterion FREEZE-mechanics

**Hash integrity model (F-003 fix):** The freeze-receipt lives EXTERNALLY at:

    references/pre-registrations/r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml

The hashed state is THIS FILE AS COMMITTED, WITHOUT any embedded hash — this
document NEVER contains its own hash (embedding the hash would change the file,
changing the hash, making verification impossible).

**Verification rule:**
1. Compute `sha256(bytes of this file as committed)`.
2. That value must equal `receipt.prereg_sha256` in the external FREEZE-RECEIPT.yaml.
3. The git commit of `carry_universe_matrix.py`, `reality_check.py`, and
   `r5_decision.py` (the STEP-4 runner) must equal `receipt.code_commit`.
4. Any edit to this file or those code objects AFTER the receipt is committed
   VOIDS the pre-registration.

The FREEZE-RECEIPT.yaml is written by `scripts/cut_freeze_receipt.py` AFTER
consensus ratification and CEO sign-off.  It is write-once and idempotent-safe
(refuses to overwrite an existing receipt).

- **Signatures:** HoQR · mathematician · quant-developer (code-pin) · NHT (audit) · CEO (ratification) — collected by PM in CONSENSUS_2026-06-05_r5_step3_prereg.md.
