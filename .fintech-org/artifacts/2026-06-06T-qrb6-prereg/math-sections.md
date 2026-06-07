# QRB-6 PRE-REGISTRATION — MATHEMATICIAN FROZEN STATISTICAL SECTIONS

**Track:** `qrb6-prereg-2026-06-06:phase1:task1.0`
**Trial:** `fa0f982a` (org-wide counter increment at freeze; 40 → 41). NEVER reuses R5 `576746aa` or confirmatory `f2fb41fd`.
**Author role:** Quantitative Mathematician
**Owns:** AC-2 (pm-acceptance-criteria.yaml). These sections are VALUE-FROZEN; the QR pins the window convention in parallel — my statistic is convention-parameterized but every numeric value below is the pre-registered contract.
**Status:** SKELETON-FIRST draft; numbers below are the pre-registered contract once consensus-ratified + freeze-receipt cut.

**Binding inputs (READ, this session):**
- NHT rescreen (BINDING counts): `nht-qrb6-rescreen.yaml` — Scenario A **506** deduped event-days / **345** post-2015 (orchestrator cross-checked exact); Scenario B **716/491** pre-committed auto-activation; banks-as-independent-blocks; ECB training-memory-unverified INADMISSIBLE.
- PM acceptance criteria: `pm-acceptance-criteria.yaml` (AC-2 ownership; no_cross_trial_constant_imports; banks_as_blocks; post_2015_subwindow_kill_mandatory; no_65pct_point_target).
- Machinery (pinned, NOT re-derived): `reality_check.py:58-88` (`hac_se_nw`, Bartlett/Newey-West), `:152-343` (Politis-White + PPW), `:403-446` (stationary circular block bootstrap), `:557,962` (+1/+1 p-value); `dsr.py:46-207` (BLdP SR0 + DSR z-form, `var_term`, scipy norm).
- Selection-history precedent (NOT constant reuse): R5 `0.022906` and confirmatory `0.034921` are OTHER TRIALS' constants — forbidden to import (no_cross_trial_constant_imports). My SR0 is derived FRESH below.

---

## 1. Null Hypothesis & Test Statistic (CONF-statistic analogue) — FROZEN

### 1.1 Series under test

`r_e` = the net-of-cost, sign-aligned, post-`entry_delay_bars=1` **event-window return** for one deduped bank-event `e`. The event-window length convention (pre-window bars, post-window bars) is pinned by the QR in parallel (AC-1c/d) and is NOT scanned over — my statistic is parameterized by that convention but is value-frozen once the QR's bar-counts are fixed. Define the per-event scalar:

> `r_e = sign_align_e · ( cumulative net-of-cost return over the QR-frozen event window for the bank-event's currency leg )`

`sign_align_e` is the a-priori directional hypothesis (pre-decision drift direction registered ex-ante per the QR hypothesis; NO data-driven sign fit). The **unit of observation is the deduped bank-event-day** (NHT: banks-as-independent-blocks; pair×event is NOT the unit — cross-pair returns on one decision day share a common currency factor).

Per-scenario n (BINDING from NHT):
- **Scenario A (default, frozen primary):** n = **506** deduped event-days; post-2015 sub-window n = **345**.
- **Scenario B (pre-committed auto-activation on C4 spot-check):** n = **716**; post-2015 n = **491**.

### 1.2 Null and alternative

> **H0:** `E[r_e] ≤ 0` (the event-window strategy has no positive net edge across deduped bank-events).
> **H1:** `E[r_e] > 0`.

One-sided, total `α = 0.05` (R5/confirmatory precedent; direction fixed a-priori from the registered drift hypothesis). The post-announcement reversal sub-test is framed per NHT C2 as "directional bias statistically distinguishable from BOTH 0% and 100%" — NO 65% point target enters any frozen field (no_65pct_point_target).

### 1.3 Frozen statistic — studentized mean event-window return with HAC SE

For a set of `n` deduped event-days with event returns `{r_e}`:

```
t_stat = sqrt(n) * mean(r) / omega_hat
```

`omega_hat` = **Newey-West (Bartlett-kernel) HAC standard error of the mean**, computed by
`reality_check.hac_se_nw(r, bandwidth = max(L - 1, 1))` (pinned `reality_check.py:58-88`).

`L` = the **Politis-White (2004) + PPW (2009)** automatic mean block length on the **event-day-ordered** series via `reality_check.politis_white_block_length(r)`, then `L = max(1, ceil(L_pw))`. Guard FROZEN: `L ≥ 1`; bandwidth `max(L-1, 1) ≥ 1` (PW clamps `L_opt ∈ [1, b_max]`, returns 1.0 on near-iid, `reality_check.py:316-324`).

**Event-study HAC note (FROZEN):** event-days are calendar-sparse and irregularly spaced. HAC bandwidth is computed on the event-day INDEX ordering (events sorted ascending by decision date), NOT calendar-day lags — adjacent events are adjacent in the ordered return vector regardless of the calendar gap between them. This is the conventional event-study treatment (each event is one observation; serial dependence is event-to-event, not bar-to-bar). PW selects `L` empirically; for near-independent event returns PW returns `L≈1` ⇒ HAC collapses to the iid SE, which is correct.

### 1.4 p-value mechanism — FROZEN: banks-as-blocks stationary block bootstrap

**Election: bank-blocked stationary/circular block bootstrap**, NOT asymptotic-normal. Mirrors the R5/confirmatory falsifier family for consistency; bank-blocking is the event-study extension required by NHT (banks_as_blocks).

See Section 3 for the exact bank-block scheme. Mechanism:
1. Compute observed `t_obs = sqrt(n)·mean(r)/omega_hat` on the full event-day series.
2. Impose H0 by de-meaning: `d_e = r_e − mean(r)` (zero-mean null, autocorrelation/variance preserved — identical convention to `r5a`/`r5c` recentering, `reality_check.py:534-535,959`).
3. For `b = 1..K`: draw a **bank-blocked** stationary block resample `d*_b` (Section 3), recompute `t*_b = sqrt(n)·mean(d*_b)/omega_hat(d*_b)` (HAC SE recomputed each resample, mirroring `reality_check.py:938`).
4. `p = (1 + #{ t*_b ≥ t_obs }) / (K + 1)` (+1/+1, `reality_check.py:557,962`).

---

## 2. Multiplicity / Selection Charge (the load-bearing freeze) — FROZEN

### 2.1 The selection event being charged

QRB-6 is the survivor of a **PAPER selection**, not a data selection. Selection history (BINDING, from prompt + acceptance-criteria evidence):
11 generated proposals → NHT screen (9 survive) → frozen-rubric ranking → 2-finalist informed comparison (QRB-6 vs QRB-3) decided AFTER a data acquisition (the CB calendar). The firm's honest-N ≈ 11-12; org counter = 41.

**FIRST-PRINCIPLES DISTINCTION FROM R5 (the crux).** R5's `N=3` charged a **data-selection**: 36 carry cells were each **backtested** and the argmax studentized statistic was selected — every cell consumed a real look at return data, so the multiplicity is a max-over-realized-statistics and the DSR `N` charges expected-max-of-N-draws inflation. QRB-6's 11 proposals were **NEVER backtested**: no return series was computed for any of the 11, no Sharpe was harvested, the ranking used a frozen *qualitative* rubric (testability, data availability, hypothesis priors) on paper. **No garden-of-forking-paths inflation of an observed Sharpe occurred at the 11→1 stage, because no Sharpe was observed at that stage.** The DSR selection charge exists to deflate a Sharpe that was selected for being large; here the Sharpe has not yet been measured at all (the one-shot run is post-freeze).

### 2.2 What an honest N_sel IS for paper-selection — derivation

The DSR `N` is "number of effectively-independent trials over which a max was taken **on the quantity being deflated** (the realized Sharpe)." For QRB-6 the quantity being deflated is the QRB-6 hold-out Sharpe, and the question is: across how many effectively-independent *realized-Sharpe* looks was THIS hypothesis selected?

- The 11→9 NHT screen and 9→2 rubric ranking touched **zero** realized Sharpes ⇒ they contribute **0** to the Sharpe-multiplicity. (They reduce the *hypothesis* space, not via data on the deflated quantity.)
- The 2-finalist comparison (QRB-6 vs QRB-3) was decided AFTER a data acquisition — but the acquisition was the **CB calendar** (event dates), NOT return series; the comparison used the calendar's *event-count / testability* (NHT counts), not any QRB-6 or QRB-3 Sharpe. So this stage too charges **0** realized-Sharpe looks on the deflated quantity. (If the finalist choice had peeked at either strategy's returns, this would be ≥1; it did not — no return data examined before freeze, AC-4.)
- The one event that DOES consume a realized-Sharpe look is the **forthcoming QRB-6 one-shot run itself** — exactly ONE look.

A pure "the data is unsnooped, charge N=1" is the anti-conservative floor I REJECT (steelmanned in §2.3): even paper-selection leaks a *little* multiplicity because the rubric was informed by the analysts' soft priors about which hypotheses tend to work, and because the firm will (under its own honest-accounting posture) have effectively explored a few correlated event-study framings. The defensible charge is the small-integer effective dimension of that soft prior exploration.

> **FROZEN: `N_sel = 3`.**

Defense: `N_sel = 3` charges (a) the one real realized-Sharpe look (the QRB-6 run), plus (b) ~2 effective-independent soft-prior "framings" the firm implicitly explored when an analyst pool generated 11 proposals and ranked them (the event-study idea-family — CB-decision drift/reversal — is ONE correlated family, not 11 independent bets; its effective independent dimension under the firm's own honest-N≈11-12 collapses to a low single digit once the heavy within-family correlation of "trade-around-scheduled-macro-events" framings is removed). `N_sel = 3` equals the R5 *prior-honest-N* convention (the firm's standing charge for "a few effective looks at a correlated idea-family") WITHOUT importing R5's data-selection 36-cell argmax charge — which is correctly ABSENT here because no QRB cell was backtested. I do NOT copy R5's N=6 (that absorbed a best-of-36-BACKTESTS argmax that has no analogue in paper-selection) nor R5's N=3 constant (the *value* coincides but is RE-DERIVED here from the paper-selection first-principles above, not imported — no_cross_trial_constant_imports honored: the reasoning, not the constant, is the source).

### 2.3 Alternatives stated and rejected

- **N_sel = 1 ("unsnooped data, no charge")** — REJECTED. Steelman: the one-shot run is genuinely OOS, so conditional on the hypothesis the bootstrap p is honest. Rejection: the firm reached THIS hypothesis through an informed multi-stage funnel; a plain N=1 understates the firm-wide false-discovery exposure across its idea-generation process. Over-deflation is the safe-if-wrong direction for a kill test.
- **N_sel = 11 (honest count of generated proposals)** — REJECTED. The 11 are NOT 11 independent realized-Sharpe draws; they were never backtested and they are heavily correlated as event-study framings. Charging 11 as a DSR `N` would treat paper ideas as if each had consumed a max-over-data look — it conflates *hypothesis-space size* with *realized-statistic multiplicity*, the inverse of the §2.2 error. It also double-charges, since the eventual run is a SINGLE look.
- **N_sel = 41 (org trial counter)** — REJECTED. The org counter mixes unrelated trials (carry family, MA, momentum) that share no selection event with QRB-6; the DSR `N` charges THIS hypothesis's selection depth, not the firm's lifetime trial count. (Using 41 would also import the BLdP "n_trials org-wide" reading, which the firm's honest-N discipline has explicitly rejected as the wrong denominator for a single pre-registered structure.)
- **N_sel = 6 (copy R5-confirmatory)** — REJECTED. R5's 6 absorbed a best-of-36-backtests argmax + prior family spend; QRB-6 has NO backtested argmax to absorb. Copying 6 would over-charge by importing a data-selection burden that did not occur, and would violate no_cross_trial_constant_imports in spirit.

### 2.4 Dispersion plug-in (FROZEN — derived, NOT carried from R5)

BLdP `SR0` needs `sqrt(Var[SR_n])` — the cross-trial dispersion of candidate Sharpes. R5/confirmatory used `sqrt(Var)=0.426385`, the sample SD over two OBSERVED look-Sharpes `{0.80, 0.197}`. **For QRB-6 NO per-proposal Sharpes exist** (paper-selection — nothing backtested), so I cannot use observed-look dispersion. I MUST elect a defensible *planning* dispersion.

**Election: `sqrt(Var[SR_n]) = 0.50` (annualized), the planning Sharpe dispersion implied by the published CB-event-study effect-size band.** Derivation:
- The deflation dispersion should reflect how much candidate true-Sharpes plausibly vary across the event-study idea-family the firm drew from. The published scheduled-macro-announcement / pre-FOMC-drift literature (Lucca-Moench 2015 pre-FOMC equity drift; CB-decision FX event studies) reports economically meaningful but modest pre-decision effects whose *annualized Sharpe-equivalent on a tradeable event-only strategy*, AFTER a realistic decay/cost haircut, plausibly spans roughly `[0, ~1]` across framings.
- A dispersion of `0.50` is the SD of a candidate-Sharpe distribution centered near the planning effect size (§5) with support across that `[0,1]` band — i.e. the family's true-Sharpe heterogeneity is on the order of the planning effect itself. This is intentionally a ROUND, auditable single number (not arithmetic theater from invented look-Sharpes): one free planning constant, defended by the published magnitude band, frozen ex-ante.
- `0.50 > ` would over-deflate (claim wilder candidate heterogeneity than the literature supports); `< 0.30` would under-deflate (claim the family's framings are near-identical in true Sharpe, contradicting the visible spread across event-study designs). `0.50` sits in the defensible middle and is NOT the R5 value (0.426385) — it is freshly elected for this paper-selection context.

> **FROZEN: `sqrt(Var[SR_n]) = 0.50` (annualized planning dispersion). RE-DERIVED for QRB-6 paper-selection; NOT imported from R5.**

### 2.5 BLdP SR0 benchmark and derived SR0 — FROZEN (shown arithmetic)

BLdP form (pinned `dsr.py:46-104`, `expected_max_sr` two-axis bracket):
```
SR0_ann = sqrt(Var[SR_n]) · [ (1 − γ)·Z⁻¹(1 − 1/N_sel) + γ·Z⁻¹(1 − 1/(N_sel·e)) ]
SR0_pp  = SR0_ann / sqrt(252)
```
with `γ = 0.5772156649`, `e = 2.718281828`, `Z⁻¹ = scipy.stats.norm.ppf`.

Bracket at `N_sel = 3` (the bracket VALUE is a property of N only — it equals R5's `0.852804` at N=3; the SR0 differs from R5 solely because my dispersion plug-in 0.50 ≠ R5's 0.426385):
```
Z⁻¹(1 − 1/3)        = Z⁻¹(0.666667)            = 0.430727
Z⁻¹(1 − 1/(3e))     = Z⁻¹(1 − 0.122626)
                    = Z⁻¹(0.877374)            = 1.161957
bracket(N=3)        = (1−γ)·0.430727 + γ·1.161957
                    = 0.4227843·0.430727 + 0.5772157·1.161957
                    = 0.182118 + 0.670721
                    = 0.852804
SR0_ann_sel         = 0.50 · 0.852804           = 0.426402   (annualized)
SR0_pp_sel          = 0.426402 / sqrt(252)
                    = 0.426402 / 15.874508      = 0.026861   (per-obs)
```

> **FROZEN: `SR0_ann_sel = 0.426402`, `SR0_pp_sel = 0.026861` (per-obs), `N_sel = 3`, `sqrt(Var[SR_n]) = 0.50`.**
> *(Z⁻¹ bracket values are standard-normal quantiles to 6 dp, orchestrator-verified via `statistics.NormalDist.inv_cdf` and routed to QD for `scipy.stats.norm.ppf` confirmation — Section 6. bracket(N=3)=0.852804 matches the R5 value EXACTLY because the bracket depends only on N; this is a consistency check, NOT a constant import — the SR0 it feeds is fresh because the dispersion differs.)*

**Implied hold-out sample Sharpe the strategy must clear:** the SR0 above is the deflation BENCHMARK; the minimum hold-out annualized Sharpe that clears the DSR gate at the terminal n is the kill_switch_threshold (Section 6) — `≈ SR0_pp + z_{0.95}/sqrt(T−1)`, annualized. At Scenario-A n=506 this is far higher than SR0 because the `sqrt(T−1)` lever is short (Section 6).

---

## 3. Bootstrap Spec — banks-as-independent-blocks — FROZEN

### 3.1 Block construction (the NHT banks_as_blocks requirement)

The unit is the deduped bank-event-day. NHT requires banks treated as **independent blocks**, NOT individual observations: within one bank-event the affected pairs share a common currency factor (not independent), and the bootstrap must resample at bank granularity.

> **FROZEN bank-block scheme.** Partition the `n` event-days into `G` bank-groups by the parquet `bank` column (Scenario A: G=4 — FED/BOJ/RBA/BOC; Scenario B: G=7 — +BOE/ECB/RBNZ). Within each bank-group the event-day returns are ordered ascending by decision date. The stationary circular block bootstrap (`reality_check._circular_block_bootstrap`, Politis-Romano 1994) is applied **within bank-group, then concatenated** to form each resample, preserving (a) within-bank event-to-event serial dependence via geometric blocks and (b) the bank-group sizes (block draws never cross a bank boundary — a block started in FED never wraps into BOJ; circular wrap is within-bank only). This is the event-study analogue of R5c's JOINT bootstrap, with the join axis being **bank** rather than pair-column.

Rationale: bank-events of different banks are the independent units (different currency, different decision calendar); bank-events of the SAME bank carry the only event-to-event serial dependence worth preserving (e.g. a persistent regime in FED-decision drift). Blocking within-bank and concatenating across banks resamples the independent units while preserving the within-unit dependence — exactly the "banks as independent blocks" NHT instruction.

**Same-day multi-bank co-decisions** (22 in Scenario A, 83-surplus in Scenario B) are already deduped to market-days in the NHT counts; each deduped event-day carries its bank label (the dominant deciding bank for that market-day per the QR's dedup rule). No event-day appears in two bank-groups.

### 3.2 Block length

`L` per bank-group = Politis-White auto on that group's event-day return series, `L_group = max(1, ceil(L_pw))`. The bootstrap uses the **per-bank** `L_group` for that group's internal resampling. For the single pooled HAC `omega_hat` (Section 1.3) the block length is the multivariate-style **max across bank-groups**, `L_pool = max_g L_group` (mirroring `politis_white_block_length_multivariate`'s "max L covers every cell's dependence", `reality_check.py:346-384`), so the HAC bandwidth is conservative (widest dependence covered). FROZEN: `L_group ≥ 1`, `L_pool ≥ 1`.

### 3.3 K (replications) + MC-SE

> **FROZEN: `K = 10000`** (the module default `_B`, `reality_check.py:49`; matches confirmatory's full-K election). The single pooled event-study test is cheap enough to run full K.

MC standard error of a bootstrap p-value `p` is `sqrt(p(1−p)/K)`. Table at K=10000:

| p (true) | MC-SE = sqrt(p(1−p)/K) |
|----------|------------------------|
| 0.01     | 0.000995               |
| 0.05     | 0.002179               |
| 0.10     | 0.003000               |
| 0.50     | 0.005000               |

At the decision boundary `p=0.05`, **MC-SE = 0.00218**. The straddle band (Section 4) uses `±MC-SE` ⇒ `0.0022` (rounded up), i.e. p in `[0.0478, 0.0522]` is the MC-indistinguishable-from-0.05 band. (R5 used 0.0031 at K=5000; my tighter band follows from K=10000.)

### 3.4 Seed RULE — FROZEN (digit-by-digit)

> **FROZEN RULE:** `master_seed = int(first 6 hex chars of trial stem, base 16) mod 1_000_000`. (Same RULE the confirmatory froze after catching a hand-hex drift; `fa0f982a` HAS no leading decimal run, so the hex-mod rule governs — NOT a "leading decimal digits" reading.)

Trial stem: `fa0f982a`. First 6 hex chars: `fa0f98`. Arithmetic, digit-by-digit base-16 (positions weighted 16^5..16^0):
```
f = 15 ;  a = 10 ;  0 = 0 ;  f = 15 ;  9 = 9 ;  8 = 8

16^5 = 1048576 ;  16^4 = 65536 ;  16^3 = 4096 ;  16^2 = 256 ;  16^1 = 16 ;  16^0 = 1

15 · 1048576 = 15728640
10 ·   65536 =   655360
 0 ·    4096 =        0
15 ·     256 =     3840
 9 ·      16 =      144
 8 ·       1 =        8
                ----------
int('fa0f98', 16) = 15728640 + 655360 + 0 + 3840 + 144 + 8 = 16387992

16387992 mod 1_000_000 = 387992
```

> **FROZEN: `master_seed = 387992`.** *(int('fa0f98',16)=16387992; 16387992 mod 1e6 = 387992. Orchestrator + QD to independently re-verify, mirroring the confirmatory's hand-hex-drift catch.)*

Child-seed convention follows R5: the single pooled block bootstrap uses `master_seed` directly (R5a convention, `reality_check.py:527`). RNG = **`numpy.PCG64`** seeded by `master_seed`. **scipy REQUIRED** (no approximation fallback) for `norm.ppf`/`norm.cdf`; absence ⇒ TECHNICAL_FAILURE, never silent approximation (R5/confirmatory A-5 pin).

---

## 4. Error Control & Decision Rule — FROZEN

### 4.1 Alpha

One-sided total `α = 0.05` (R5/confirmatory precedent). The aggregate test and the post-2015 sub-window KILL are BOTH evaluated against this α (the post-2015 gate is a SEPARATE mandatory hurdle, not an α-split — see §4.2; NHT post_2015_subwindow_kill_mandatory).

### 4.2 The two-gate functional (both-must-pass) — FROZEN, §7.3.6-style ordered rules

Let `p_agg` = the bank-blocked bootstrap p on the FULL Scenario-A event set (n=506), `p_post2015` = the same statistic on the post-2015 sub-window (n=345), `DSR` = the §2/§6 deflated-Sharpe statistic on the full event set, and the run-integrity flags. The frozen firm decision is an **ordered, mutually-exclusive, exhaustive** evaluation — FIRST matching rule fires and STOPS. Order chosen so no boundary case buys PASS; every tie resolves to the more conservative (non-PASS) branch. MC-SE straddle band = **0.0022** (§3.3). Evaluate top to bottom:

> **RULE 0 — TECHNICAL FAILURE** (→ HALT, root-cause, re-freeze, re-run; NO p read). Fires iff a code error, data-integrity/provenance fault, training-memory-unverified row leaking into the event set, freeze-receipt mismatch, cross-trial constant import detected, or any divergence of the runner from the pinned `reality_check`/`dsr` conventions. If RULE 0 fires, RULES 1–4 are NOT evaluated.
>
> **RULE 1 — KILL (post-2015 structural-break fail)** (→ the mandatory NHT kill; overrides any aggregate pass). Fires iff RULE 0 did not, AND **`p_post2015 ≥ 0.05 − MC-SE` (i.e. `p_post2015 > 0.0478`)** — the post-2015 sub-window does NOT cleanly reject H0. This is evaluated **BEFORE** any aggregate-pass test, so a strategy alive only pre-2015 is KILLED **regardless of `p_agg` or `DSR`** (NHT: pre-2015-only drift = dead alpha in the current regime; post_2015_subwindow_kill overrides_aggregate_pass: true). Archive QRB-6 RETIRED/FALSIFIED.
>
> **RULE 2 — KILL (aggregate fail)** (→ wind-down). Fires iff RULES 0–1 did not (so post-2015 cleanly passes), AND **`p_agg ≥ 0.05 − MC-SE` (i.e. `p_agg > 0.0478`)** — the full event set does not reject H0. Statistically indistinguishable from chance at the pooled level. Archive RETIRED.
>
> **RULE 3 — PASS** (→ §-action: graduate to a fresh, separately-pre-registered observe-only paper canary; NO CAPITAL; new trial_id; new HoQR+Math+NHT ratification). Fires iff RULES 0–2 did not (so `p_post2015 ≤ 0.0478` AND `p_agg ≤ 0.0478`, BOTH cleanly reject outside the straddle band), AND **`DSR ≥ 0.95`** (selection-deflation gate cleared at `SR0_pp_sel=0.026861`, equivalently aggregate-set ann Sharpe ≥ kill_switch_threshold=1.5883, §2/§6). PASS is NECESSARY-BUT-NOT-SUFFICIENT and authorizes only a confirmatory/observe-only next step.
>
> **RULE 4 — AMBIGUOUS / gate-fail (catch-all, guarantees exhaustiveness)** (→ no-PASS; default to wind-down under full-auto, or a fresh single-structure confirmatory pre-reg if HoQR elects). Fires iff RULES 0–3 did not — i.e. both p's are clean rejections (`< 0.0478`) BUT `DSR < 0.95` (the rejection cannot clear the selection-deflation charge), OR either p sits in the straddle band `[0.0478, 0.0522]` (a boundary p indistinguishable from 0.05 at K=10000 must NOT buy PASS and must NOT be read as a clean KILL). A bare bootstrap rejection that cannot survive deflation, or a straddle, maps here — NEVER to PASS.

**Exhaustiveness & mutual-exclusivity.** Ordered disjoint conditions: {technical-fail} → {post-2015 not-clean-reject} → {agg not-clean-reject} → {both clean-reject ∧ DSR≥0.95} → {else}. Evaluation stops at first match ⇒ disjoint by construction; RULE 4 is the unconditional else ⇒ every non-technical-fail outcome lands in exactly one of RULES 1–4. No overlap between the post-2015 gate and the aggregate gate: post-2015 is tested FIRST and its failure short-circuits before the aggregate is consulted (the both-must-pass semantics — post-2015 fail KILLS even when aggregate passes; aggregate is only reached if post-2015 is clean).

**Both-must-pass restated:** PASS requires BOTH `p_post2015` AND `p_agg` to cleanly reject AND `DSR≥0.95`. A post-2015 fail with an aggregate pass = KILL (RULE 1), never PASS — this is the NHT-mandated structural-break kill encoded as the highest-priority non-technical rule.

### 4.3 Scenario-B auto-activation arithmetic — FROZEN (no recompute at activation)

Scenario B activates automatically on C4 spot-check completion (pre-committed; no new pre-reg). The two-gate functional is IDENTICAL; only the n's change, which changes only the kill_switch_threshold (via the `sqrt(T−1)` lever) and the MC-SE-band-free p-thresholds (the α and straddle band are n-invariant). FROZEN both parameter sets so activation needs NO recompute:

| Quantity | Scenario A (frozen default) | Scenario B (pre-frozen, auto-activate on C4) |
|----------|------------------------------|-----------------------------------------------|
| n (aggregate) | 506 | 716 |
| n (post-2015 sub-window) | 345 | 491 |
| α (one-sided, total) | 0.05 | 0.05 |
| MC-SE band (K=10000) | 0.0022 | 0.0022 |
| p-reject threshold (both gates) | p ≤ 0.0478 (clean) | p ≤ 0.0478 (clean) |
| SR0_pp_sel (N_sel=3, disp=0.50) | 0.026861 | 0.026861 |
| DSR gate | ≥ 0.95 | ≥ 0.95 |
| kill_switch_threshold (ann Sharpe, aggregate-set anchor) | **1.5883** (T=506) | **1.4029** (T=716) |

The DSR benchmark `SR0_pp_sel` and `N_sel` are n-INVARIANT (selection charge does not depend on the event count). ONLY `kill_switch_threshold` moves with n (Section 6 derivation for both). Activation = swap the n-pair and read the pre-frozen threshold; nothing is recomputed live.

---

## 5. Power — FROZEN (shown work)

### 5.1 Planning effect size (justified)

Power must be planned at a **defensible, decay-haircut event-study effect size**, NOT a snooped Sharpe (none exists — nothing backtested). Published anchors: pre-FOMC / pre-decision drift studies (Lucca-Moench 2015 pre-FOMC equity drift; scheduled-CB-decision FX event studies) report economically meaningful pre-decision moves; translated to a tradeable **event-only** annualized Sharpe AFTER a realistic decay + cost haircut, the planning effect is modest.

> **FROZEN planning effect size: `SR_plan = SR0_ann_sel = 0.4264` (annualized).** Rationale (mirroring confirmatory §3.1): plan power at the firm's own selection-deflated benchmark — the smallest true ann Sharpe at which a PASS is *meaningful* rather than selection luck. Planning at a larger snooped figure would overstate power. A literature-anchored alternative (a `~0.3–0.5` post-haircut event-Sharpe band) lands in the same neighborhood; I freeze the single auditable `SR0_ann_sel` rather than add a second free parameter.

### 5.2 Power curves — event-day-count convention

For an event-study pooled t-test, the non-centrality at n deduped event-days is `λ = SR_pp · sqrt(n) = (SR_ann/sqrt(252)) · sqrt(n)`. With `SR_ann = 0.4264`, `SR_pp = 0.426402/15.874508 = 0.026861`. One-sided boundary `z_{0.95} = 1.644854`. Power `= Φ(λ − z_{0.95})` (orchestrator-verified; QD to confirm).

```
Scenario A aggregate, n = 506:
  λ = 0.026861 · sqrt(506) = 0.026861 · 22.49444 = 0.604219
  power = Φ(0.604219 − 1.644854) = Φ(−1.040635) = 0.149   (≈ 15%)

Scenario A post-2015, n = 345:
  λ = 0.026861 · sqrt(345) = 0.026861 · 18.57418 = 0.498918
  power = Φ(0.498918 − 1.644854) = Φ(−1.145936) = 0.126   (≈ 13%)

Scenario B aggregate, n = 716:
  λ = 0.026861 · sqrt(716) = 0.026861 · 26.75818 = 0.718746
  power = Φ(0.718746 − 1.644854) = Φ(−0.926108) = 0.177   (≈ 18%)

Scenario B post-2015, n = 491:
  λ = 0.026861 · sqrt(491) = 0.026861 · 22.15852 = 0.595196
  power = Φ(0.595196 − 1.644854) = Φ(−1.049658) = 0.147   (≈ 15%)
```

> **Power at the planning effect SR_plan=0.4264 is LOW (~13–18%) across all four n's.** Disclosed honestly. The event-study has MANY event-days but each event carries little independent signal at the planning Sharpe; the pooled non-centrality grows only as sqrt(n). This is the explicitly-disclosed power reality: a non-rejection (KILL) at the terminal n is uninformative *as evidence of no edge* but does NOT license continued spend (mirrors confirmatory §3.5 / decision map). NHT reviews.

**Sensitivity (higher planning effect, for context, NOT the frozen plan):** if the true event-Sharpe were the un-haircut `~0.7` band, n=506 power `= Φ(0.7/15.8745·sqrt(506) − 1.645) = Φ(0.04410·22.494 − 1.645) = Φ(0.9920−1.645) = Φ(−0.653) = 0.257` (~26%). Even doubling the planning effect leaves the test underpowered at n=506 — the event-only Sharpe is intrinsically low. The PW block length on the event series may FURTHER reduce effective n (high event-to-event autocorrelation ⇒ fewer effective blocks ⇒ wider HAC SE); the iid-event power above is an UPPER bound. Disclosed.

---

## 6. kill_switch_threshold — FROZEN (verbatim pre-reg field)

The `kill_switch_threshold` is the **minimum event-strategy annualized Sharpe** required to clear the DSR gate (`DSR ≥ 0.95`) at `SR0_pp_sel = 0.026861`, carrying the event-set's own higher moments at evaluation. The DECLARED verbatim value anchors to **Scenario A aggregate, T = 506** (the frozen primary event set on which the DSR gate is computed; Scenario B's 716-anchor value is pre-frozen in §4.3 for auto-activation). var_term reference = 1.

DSR conventions pinned (`dsr.py:179-203`): `var_term = 1 − skew·SR_pp + ((xkurt+2)/4)·SR_pp²`; `z_dsr = (SR_pp − SR0_pp_sel)·sqrt(T−1)/sqrt(var_term)`; `DSR = Φ(z_dsr)`. DSR=0.95 ⇒ `z_dsr = Φ⁻¹(0.95) = 1.644854`. var_term reference = 1 (event-set higher moments unknown until run; the runner recomputes var_term with the event-set's OWN skew/kurtosis at evaluation — I freeze the declared value at the var_term=1 reference, which is the conservative, auditable anchor since `SR_pp` is small ⇒ var_term ≈ 1; mirrors confirmatory §4's two-pass with the pre-registered placeholder, where the second pass moved the result by < 0.001).

Solve at `var_term = 1`, `T = 506` (Scenario A aggregate — the declared anchor):
```
SR_pp = SR0_pp_sel + z_dsr / sqrt(T − 1)
      = 0.026861 + 1.644854 / sqrt(505)
      = 0.026861 + 1.644854 / 22.472205
      = 0.026861 + 0.073195
      = 0.100056
SR_ann = SR_pp · sqrt(252) = 0.100056 · 15.874508 = 1.588337
```

> **FROZEN: `kill_switch_threshold: 1.5883`** (annualized Scenario-A-aggregate event-strategy Sharpe required at T=506 to clear DSR ≥ 0.95 at `SR0_pp_sel=0.026861`, `N_sel=3`, `disp=0.50`, var_term=1; orchestrator-verified 1.588337).

Scenario B, T=716 (pre-frozen, §4.3):
```
SR_pp = 0.026861 + 1.644854/sqrt(715) = 0.026861 + 1.644854/26.74883 = 0.026861 + 0.061493 = 0.088354
SR_ann = 0.088354 · 15.874508 = 1.402907   → kill_switch (Scenario B) = 1.4029
```

> Interpretation: any aggregate-set event-strategy ann Sharpe BELOW 1.5883 (Scenario A) / 1.4029 (Scenario B) fails the DSR gate and cannot produce a PASS (maps to RULE 4). NOT copied from any prior trial — derived fresh at QRB-6's `SR0_pp_sel`, `N_sel=3`, `disp=0.50`, and T. The threshold sits far above the planning SR (0.43) and SR0 (0.027) because `T≈506` is short (the `sqrt(T−1)` lever is weak) and the DSR demands a high realized Sharpe to certify a selected structure on a modest sample — exactly the confirmatory dynamic (confirmatory got 1.2906 at N=6/T=1260; QRB-6 gets 1.5883 at N=3/T=506: the smaller N LOWERS the SR0 contribution but the smaller T RAISES the threshold more, netting higher). This high bar against a ~13–18%-power test (Section 5) is the honest, disclosed reality: the most-likely terminal state is KILL.

> **kill_switch_threshold (verbatim field for the pre-reg file): `1.5883`** (Scenario A primary; `1.4029` Scenario B on auto-activation).

---

## ROUTED NUMERICAL QUESTION (to quant-developer)

Confirm via `scipy.stats.norm` (PCG64 irrelevant for these deterministic constants): (1) the two §2.5 quantiles `Z⁻¹(0.666667)`, `Z⁻¹(0.877374)` and `bracket(N=3)`; (2) `SR0_ann_sel`, `SR0_pp_sel`; (3) `int('fa0f98',16)=16387992` ⇒ `master_seed=387992`; (4) the §6 two-pass solves for `kill_switch_threshold` at T=506 and T=716; (5) the §5 power values. All are standard `scipy.stats.norm.ppf`/`.cdf` evaluations; values shown are my hand-work to 3–6 dp.
