# HoQR REWORK-1 Patches — R5 Pre-Registration §3.4, §4, §5

**FINAL N ELECTION: N = 3.**
One-line basis: N=3 is the midpoint of the combined credible range (HoQR 1–2 / NHT 2–4 → union 1–4); because SR0 strictly *increases* in N, the union FLOOR (N=2) is the least-deflating admissible choice and biases toward a false CONTINUE — unacceptable for a pre-committed KILL test — so I move OFF the floor toward the conservative pole, stopping at the midpoint (3) rather than the skeptic's top (4), since my mechanistic decomposition genuinely finds only 2 *distinct* information sources and N=3 charges a half-look for the residual independence (FRED regime gate, vol-targeting) the 2-source view may understate. The Mathematician is freezing SR0 for N∈{2,3,4} in parallel; N=3 maps to a frozen scalar.

This file replaces the WRONG §3.4 (which narrated a hand-recomputation as `honest_n.py` code output and pinned the anti-conservative N=2 floor) and adds forking-paths counter-discipline to outcomes 1 & 4 and the §4/§6 decision rules. Each PATCH gives an exact-match ANCHOR (text replaced) and REPLACEMENT.

---

## PATCH 1 — §3.4 header: N pin (A-2)

**ANCHOR (replace exactly):**
```
### Honest-N pin: **N = 2**
```

**REPLACEMENT:**
```
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
```

---

## PATCH 2 — §3.4 Derivation (A-1 + A-2 + A-3): replace the false "code-output" narrative and the 8→5→2 collapse

**ANCHOR (replace exactly — the entire block from "**Derivation.**" through the end of the "Why N is neither 1 nor 36 nor 37" bullet list):**
```
**Derivation.** The honest-N is the number of *effectively independent* carry looks the firm has
spent — not the org-wide trials.jsonl line count, and not 1. I apply the firm's de-duplication rule
(`src/forex_system/harness/honest_n.py:39-81`) and then collapse the shared-signal dimension.

Step 1 — apply the suffix-strip dedup rule to the 8 carry-family pre-regs. The rule keys a
hypothesis by `pre_reg_path` if present, else by the strategy name with cost/pair/ablation suffixes
stripped (`honest_n.py:40-58,63-81`). Cost-ablations and pair/vol-scaling suffixes collapse:

| Pre-reg | Strategy | After suffix-strip | Collapses with |
|---|---|---|---|
| carry_baseline | carry | `carry` | carry_2x_costs |
| carry_2x_costs | carry | `carry` | (cost ablation of carry) |
| carry_fred | carry_fred | `carry_fred` | — |
| fred_carry_stripped | fred_carry_stripped | `fred_carry` | (ablation of carry_fred's regime layer) |
| vol_target_carry | vol_target_carry | `vol_target_carry` | vol_target_carry_no_vol_scaling |
| vol_target_carry_no_vol_scaling | vol_target_carry | `vol_target_carry` | (vol-scaling ablation) |
| carry_momentum | carry_momentum | `carry_momentum` | carry_momentum_3x_costs |
| carry_momentum_3x_costs | carry_momentum | `carry_momentum` | (cost ablation of carry_momentum) |

After Step 1 the 8 pre-regs collapse to **5 distinct dedup keys**:
`{carry, carry_fred, fred_carry, vol_target_carry, carry_momentum}`. The 3 cost/vol-scaling
ablations are *not* independent looks — they re-run the same signal on the same window with a
multiplied cost or a removed scaler.

Step 2 — collapse the shared-signal dimension. The remaining 5 keys are **re-parameterizations and
ablations of ONE underlying idea: the cross-currency interest-rate differential**, all driven by the
same `rate_differentials.parquet` feed (carry_fred pre-reg `:131,133`; mechanism sections of all
carry pre-regs). The ratified scope finding is that the 36-cell universe has **effective independent
dimension ≈ 1–2 (HoQR) / 2–4 (NHT)** (`docs/decisions/CONSENSUS_2026-06-02_r5_scope.md:21,45,94`).
The 5 dedup keys are not 5 independent bets; they are two genuinely distinct *information sources*
overlaid on the same rate-differential base:

1. **The pure rate-differential carry look** — `carry`, `carry_fred`, `fred_carry`, and
   `vol_target_carry` are all the same rate-differential signal with a sizing/ranking/conditioning
   wrapper (rank-normalization, vol-targeting, FRED regime gate). They share the feed and their OOS
   returns are dominated by the same JPY-cross carry dynamics. This is **ONE** independent look.
2. **The carry+momentum hybrid look** — `carry_momentum` adds an SMA-crossover momentum overlay
   (`carry_momentum.md:27-40`), a genuinely *different* signal source (price trend, not rate level)
   gated by an agreement filter. The momentum component injects information not present in the pure
   carry look. This is the **SECOND** independent look.

**N = 2.** This sits at the top of HoQR's own scope estimate (1–2) and the bottom of NHT's (2–4),
making it the defensible point inside both ranges.

**Why N is neither 1 nor 36 nor 37:**
- **Not 37** (org-wide trials.jsonl count): that total includes non-carry strategies (ma_crossover,
  bollinger_rsi, momentum, tas_ceiling) and counts every cost-ablation and re-run as a separate
  look. It *overstates* the independent carry looks and would over-deflate (too conservative,
  understating any real edge). `honest_n.py` exists precisely to reject this raw count.
- **Not 36** (the cell count): the 36 cells are NOT 36 hypotheses — the scope ratified effective
  independent dimension ≈1–4, and the joint same-block bootstrap is used *because* the cells are not
  independent. Charging N=36 in the DSR would double-count the multiplicity the SPA max-statistic
  already controls jointly.
- **Not 1**: there genuinely are two distinct information sources (rate-differential carry vs.
  carry+momentum hybrid). Pinning N=1 would treat the momentum overlay as free and under-deflate,
  leaving the momentum-look snooping uncontrolled.
```

**REPLACEMENT:**
```
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
```

---

## PATCH 3 — §3.4 Sharpe-table source note (F-007): strengthen the SR_1=0.80 provenance disclosure

**ANCHOR (replace exactly):**
```
| Look | Representative member | Sharpe (SR_n) | Source (file:line) |
|---|---|---|---|
| 1 — rate-differential carry | carry_fred (Bet #1, OOS) | **0.80** | `references/pre-registrations/carry_fred.md:16` (≥0.30 hypothesis; 0.80 realized), `references/pre-registrations/fred_carry_stripped.md:18,66` ("carry_fred achieved 0.80 on its OOS window") |
| 2 — carry+momentum hybrid | carry_momentum (OOS-2022) | **0.197** | trial `6a56df9c`, `.fintech-org/trials.jsonl:21` (`oos_sharpe=0.197`) |
```

**REPLACEMENT:**
```
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
```

---

## PATCH 4 — Outcome 1 (CONTINUE) counter-discipline (A-4)

**ANCHOR (replace exactly — the §4 CONTINUE-path bullet):**
```
- **CONTINUE path — `SPA p < 0.05` at the CLASS level (post-deflation), confirmed by White-RC direction.**
  CONTINUE is **NECESSARY-BUT-NOT-SUFFICIENT.** A class-level rejection means the family is distinguishable from chance against a zero benchmark — it does NOT validate any individual cell, and it does NOT re-launch the program. The single named confirmatory next step is: **author a NEW, separate pre-registration for a confirmatory-only test of the specific surviving structure**, with no free exploration, no re-parameterization, no new variant or pair search. Selecting a cell post-hoc and trading it invalidates the p at any magnitude.
```

**REPLACEMENT:**
```
- **CONTINUE path — `SPA p < 0.05` at the CLASS level (post-deflation), confirmed by White-RC direction.**
  CONTINUE is **NECESSARY-BUT-NOT-SUFFICIENT.** A class-level rejection means the family is distinguishable from chance against a zero benchmark — it does NOT validate any individual cell, and it does NOT re-launch the program. The single named confirmatory next step is: **author a NEW, separate pre-registration for a confirmatory-only test of the specific surviving structure**, with no free exploration, no re-parameterization, no new variant or pair search. Selecting a cell post-hoc and trading it invalidates the p at any magnitude.
  **Forking-paths counter-discipline (BINDING).** Any R5-spawned confirmatory test (i) **increments the org-wide trial counter as a NEW trial** (a fresh `trial_id`, distinct from R5's `576746aa`; it does NOT reuse the R5 family id), and (ii) **MUST absorb the R5 36-cell selection burden in its own honest-N and deflation inputs** — the candidate it confirms was SELECTED after seeing R5's 36-cell results, so that selection is a spent look and is part of the confirmatory test's OWN multiplicity. A confirmatory test that does not carry the R5 selection forward into its honest-N / `SR0` is itself a garden-of-forking-paths violation and its p is not face-valid.
```

---

## PATCH 5 — Outcome 4 / AMBIGUOUS counter-discipline (A-4)

**ANCHOR (replace exactly — the §4 AMBIGUOUS-path bullet):**
```
- **AMBIGUOUS path — partial / anomalous result** (e.g., the family p straddles the boundary within MC-SE; or only an isolated subset shows signal; or a normalization-driven distortion such as the carry_momentum near-null column — see N2 — produces a result that is not a clean class-level rejection).
  AMBIGUOUS maps to **a confirmatory-only pre-reg gate, NEVER to CONTINUE on the original family.** No capacity is unfrozen for the original 36-cell family on an ambiguous result. The only permitted forward action is a fresh, separately-pre-registered confirmatory test of the specific anomaly, treated as a brand-new hypothesis with its own freeze.
```

**REPLACEMENT:**
```
- **AMBIGUOUS path — partial / anomalous result** (e.g., the family p straddles the boundary within MC-SE; or only an isolated subset shows signal; or a normalization-driven distortion such as the carry_momentum near-null column — see N2 — produces a result that is not a clean class-level rejection).
  AMBIGUOUS maps to **a confirmatory-only pre-reg gate, NEVER to CONTINUE on the original family.** No capacity is unfrozen for the original 36-cell family on an ambiguous result. The only permitted forward action is a fresh, separately-pre-registered confirmatory test of the specific anomaly, treated as a brand-new hypothesis with its own freeze.
  **Forking-paths counter-discipline (BINDING, identical to the CONTINUE path).** Any such confirmatory test (i) **increments the org-wide trial counter as a NEW trial** (fresh `trial_id`, not R5's `576746aa`), and (ii) **MUST absorb the R5 36-cell selection burden in its own honest-N and deflation inputs** — the anomaly being confirmed was SELECTED after seeing R5's 36-cell results, so that selection is a spent look counted in the confirmatory test's OWN multiplicity. Untracked, a post-R5 confirmatory test re-opens the garden of forking paths and its p is not face-valid.
```

---

## PATCH 6 — §6 machine-checkable retirement criteria: confirmatory-path discipline (A-4)

**ANCHOR (replace exactly — the two §6 bullets that reference the confirmatory / CONTINUE path):**
```
- `R5.spa_p < 0.05 AND R5.white_rc_p >= 0.05 (discordant)` → **AMBIGUOUS**, do NOT CONTINUE on the family; confirmatory pre-reg gate only (outcome 4).
```

**REPLACEMENT:**
```
- `R5.spa_p < 0.05 AND R5.white_rc_p >= 0.05 (discordant)` → **AMBIGUOUS**, do NOT CONTINUE on the family; confirmatory pre-reg gate only (outcome 4). Any spawned confirmatory test MUST register as a NEW `trial_id` (counter increment) AND carry the R5 36-cell selection into its own honest-N / deflation inputs; a confirmatory test that reuses `576746aa` or omits the R5 selection burden is VOID.
```

**ANCHOR 2 (replace exactly — the §6 CONTINUE bullet):**
```
- `R5.spa_p < 0.05 AND R5.white_rc_p < 0.05 (concordant, post-deflation)` → **CONTINUE** is permitted, but ONLY as authorization to author a confirmatory-only pre-reg (outcome 1) — never as authorization to trade or to re-open the family.
```

**REPLACEMENT 2:**
```
- `R5.spa_p < 0.05 AND R5.white_rc_p < 0.05 (concordant, post-deflation)` → **CONTINUE** is permitted, but ONLY as authorization to author a confirmatory-only pre-reg (outcome 1) — never as authorization to trade or to re-open the family. That confirmatory pre-reg MUST register as a NEW `trial_id` (org-wide counter increment, NOT a reuse of `576746aa`) AND absorb the R5 36-cell selection burden in its own honest-N / `SR0` deflation inputs; omitting either VOIDS the confirmatory result.
```

---

## PATCH 7 — §5 Wind-Down Action Map table: outcomes 1 & 4 counter-discipline (A-4)

**ANCHOR (replace exactly — the outcome-1 "Named firm action" cell text):**
```
| **1** | **REJECT (class level)** | SPA p < 0.05 (post-deflation), White-RC concordant | **CONFIRMATORY pre-reg only.** Author a new, separate pre-registration for a confirmatory-only test of the surviving structure. NO free exploration, NO re-parameterization, NO new variant/pair search, NO capital. The original 36-cell family is NOT re-opened for research; only the named confirmatory hypothesis proceeds. |
```

**REPLACEMENT:**
```
| **1** | **REJECT (class level)** | SPA p < 0.05 (post-deflation), White-RC concordant | **CONFIRMATORY pre-reg only.** Author a new, separate pre-registration for a confirmatory-only test of the surviving structure. NO free exploration, NO re-parameterization, NO new variant/pair search, NO capital. The original 36-cell family is NOT re-opened for research; only the named confirmatory hypothesis proceeds. **The confirmatory test increments the org-wide trial counter as a NEW trial (fresh `trial_id`, not `576746aa`) AND absorbs the R5 36-cell selection burden in its own honest-N / deflation inputs (the post-R5 cell selection is a spent look in that test's multiplicity).** |
```

**ANCHOR 2 (replace exactly — the outcome-4 "Named firm action" cell text):**
```
| **4** | **ANOMALOUS** | Partial subset survives; boundary-straddle within MC-SE; or normalization-driven distortion (e.g., carry_momentum near-null column post-N2 decision) | **AMBIGUOUS → confirmatory pre-reg gate ONLY.** Does NOT license CONTINUE on the original family. The specific anomaly may be carried into a fresh, separately-pre-registered confirmatory test with its own freeze; the 36-cell family research is not re-opened. No capital. |
```

**REPLACEMENT 2:**
```
| **4** | **ANOMALOUS** | Partial subset survives; boundary-straddle within MC-SE; or normalization-driven distortion (e.g., carry_momentum near-null column post-N2 decision) | **AMBIGUOUS → confirmatory pre-reg gate ONLY.** Does NOT license CONTINUE on the original family. The specific anomaly may be carried into a fresh, separately-pre-registered confirmatory test with its own freeze; the 36-cell family research is not re-opened. No capital. **That confirmatory test increments the org-wide trial counter as a NEW trial (fresh `trial_id`, not `576746aa`) AND absorbs the R5 36-cell selection burden in its own honest-N / deflation inputs.** |
```

---

## PATCH 8 — §3.4 closing sign-off line: update N (consistency with elected N=3)

**ANCHOR (replace exactly):**
```
*HoQR sign-off: Method A UNAVAILABLE (per-variant negative attestation above); Method B operative;
N = 2; Var[SR_n] = 0.0909. Pinned to the freeze-receipt at assembly.*
```

**REPLACEMENT:**
```
*HoQR sign-off: Method A UNAVAILABLE (per-variant negative attestation above); Method B operative;
**N = 3** (elected off the union FLOOR for the bias-direction reason in the §3.4 header — `SR0`
increases in `N`, so the floor is anti-conservative for a kill test); `Var[SR_n]` is the dispersion
of the look-level Sharpes the Mathematician freezes for the elected `N` (the prior `N = 2` hand-arith
`Var = 0.0909` is SUPERSEDED — with `N = 3` the variance is computed over the three look-Sharpes the
Mathematician pins, not by HoQR hand-arithmetic; `SR0` is frozen by the Mathematician for
`N ∈ {2,3,4}` and the elected value is the `N = 3` scalar). SR_1 = 0.80 is registry-prose,
conservative-if-wrong, contingent on the F-001 DSR-gate fix (see Sharpe-table source note). Pinned to
the freeze-receipt at assembly.*
```

---

## NOTE on the §3.4 Var[SR_n] hand-arithmetic block (N=2 artifact)

The original §3.4 contains a "Var[SR_n] — computed by hand over the N = 2 look Sharpes" block and a
"DSR threshold inputs handed to the Mathematician (frozen)" block, both hard-wired to `N = 2`
(two-Sharpe mean/variance, and the `Z⁻¹(1 − 1/N) = Z⁻¹(0.5) = 0` simplification that only holds at
N=2). **With the elected N = 3 these blocks are SUPERSEDED.** Per the rework routing, the
Mathematician is freezing `SR0` for `N ∈ {2,3,4}` in parallel and owns the variance/quantile
arithmetic for the elected `N`; HoQR no longer hand-computes `Var[SR_n]` (the two-look hand-arith was
itself only valid at N=2 and is part of the anti-conservative artifact being retired). The Mathematician
should replace those two blocks with the `N = 3` frozen scalars. HoQR's frozen inputs are now: **`N = 3`**,
`γ = 0.5772156649`, `e = 2.718281828`, the look-level representative Sharpes of the §3.4 Sharpe table
(SR_1 = 0.80 conservative-if-wrong; SR_2 = 0.197; the third look-Sharpe drawn per the Mathematician's
N=3 dispersion convention from the carry-family member set), and `α = 0.05`. The arithmetic is the
Mathematician's to compute and sign.
