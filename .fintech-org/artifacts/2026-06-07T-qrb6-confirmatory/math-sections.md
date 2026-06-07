# QRB-6 CONFIRMATORY — PART II: FROZEN STATISTICAL SPECIFICATION (Mathematician)

**Track:** `qrb6-confirmatory-2026-06-07:phase1:task1.0`
**New Trial ID:** `53981a4a` (org-counter increment 41 → 42; registered in `.fintech-org/trials.jsonl` at freeze. NEVER reuses the exploratory `fa0f982a`.)
**Author role:** Quantitative Mathematician
**Status:** FROZEN at authoring; the numbers below are the pre-registered contract. Becomes BINDING on consensus ratification (QR + Mathematician + NHT + principal-reviewer) + CEO sign-off + the write-once freeze-receipt. No post-2026-04-06 event-return is computed before the receipt is committed.

**Lineage (QR PART I owns the structure; this PART II owns the statistics).** The single structure under test — `y_e = sign(close(D)−close(D-1))·R_post`, `K_pre=1`, `K_post=2` (close(D)→close(D+2), entry D+1, `entry_delay_bars=1`), Scenario-A verified-official banks {FED, BOJ, RBA, BOC}, the §3.2 pair×bank map, banks-as-blocks stationary block bootstrap, cost manifest `config/cost_freeze_qrb6.yaml` (sha `6ec6937e`), `spread_z=3.0`, exclude-not-impute — is pinned **verbatim from the exploratory** `fa0f982a` (freeze-receipt prereg_sha256 `7438b0a`), and is echoed by reference in the QR sections (CONF-structure). PART II changes ONLY what N_sel=1 and the forward single-look horizon force to change: the SR0 benchmark, the look design, the power plan, the kill-switch, and the seed.

**Source anchors (verified, this session):**
- Exploratory result: `references/pre-registrations/qrb6_cb_event_study.STEP-RESULT.yaml:4-11` — `decision: RULE_4_AMBIGUOUS`; `p_agg=0.0230977`, `p_post2015=0.0026997`, `dsr=0.9069704` (< 0.95 gate fail), `sr_ann_pooled=1.3521443`, `skew_pooled=0.4499`, `excess_kurtosis_pooled=2.8684`; `scenario_a_event_days=506`, `post_2015=345`; per-bank PW block lengths FED=3/BOJ=1/RBA=1/BOC=1.
- Exploratory SR0 derivation: `qrb6_cb_event_study.md:370-385` — `bracket(N=3)=0.852804`, dispersion `0.50`, `SR0_ann_sel=0.426402`, `SR0_pp_sel=0.026861`.
- Exploratory power convention: `qrb6_cb_event_study.md:546-566` — `λ = (SR_ann/√252)·√n`, `power=Φ(λ−z₀.₉₅)`, disclosed ~13–18% at n=506.
- Exploratory kill-switch: `qrb6_cb_event_study.md:574-588` — `1.5883` at `SR0_pp_sel=0.026861`, `T=506`, `N_sel=3`, var_term=1, two-pass.
- Exploratory freeze-receipt: `qrb6_cb_event_study.FREEZE-RECEIPT.yaml:6-16` — `master_seed=387992` (`int('fa0f98',16)=16387992 mod 1e6`), `K=10000`.
- Carry-confirmatory template: `r5_confirmatory_vol_target_carry_usdjpy.md:439-467` (kill-switch two-pass), `:477-479` (seed rule), `:392-416` (look design / alpha-spending shape).
- DSR / HAC / PW conventions pinned in code: `src/forex_system/harness/dsr.py:179-203`, `r5_decision.py:147-193`, `reality_check.py:58-88,316-324`.

---

## 1. Null Hypothesis & Test Statistic (CONF-statistic) — FROZEN

### 1.1 Series under test (single, pre-specified)

The confirmatory test evaluates **exactly one** scalar event series:

> `y_e` = the signed-product post-decision net-of-cost event return of the **QRB-6** structure as executed in `fa0f982a` — `y_e = sign(close(D)−close(D-1))·R_post` over the Scenario-A pair×bank map — computed on the **forward hold-out only** (CB decisions strictly after 2026-04-06; window rule in QR §holdout). Same cost manifest, same `spread_z=3.0` overlay, same exclude-not-impute rule.

The 11-proposal → 2-finalist → QRB-6 selection family is **closed**. This is a single-structure test; that multiplicity is not re-run — it was already charged and spent in `fa0f982a` at `N_sel=3` (§2 below).

### 1.2 Null and alternative

> **H0:** `E[y_e] ≤ 0` (no positive post-decision net-of-cost edge on unsnooped forward events).
> **H1:** `E[y_e] > 0`.

One-sided, total `α = 0.05` spent **once** at the single terminal look (§3). Direction is fixed a-priori (the structure was selected as a positive-edge continuation hypothesis); a two-sided test would waste half the α.

### 1.3 Frozen statistic — banks-as-blocks HAC-studentized mean

At the terminal look with `n` deduped forward event-days:

```
t_obs = sqrt(n) · mean(y_e) / omega_hat
```

`omega_hat` = Newey–West (Bartlett) HAC SE of the mean (`reality_check.hac_se_nw`, bandwidth `max(L−1,1)`), `L` = **Politis–White (2004)+PPW(2009)** auto block length, computed **per bank group** on the forward series (banks-as-blocks; same machinery as `fa0f982a`, which produced FED=3/BOJ=1/RBA=1/BOC=1 in-sample). `L ≥ 1` guard (PW clamps to `[1,b_max]`). **Identical statistic family to the exploratory** — the confirmatory is the same test on unsnooped forward events, with N_sel and the look design as the only frozen differences.

### 1.4 p-value mechanism — FROZEN: banks-as-blocks stationary block bootstrap

**Election: `bank_level_blocks_stationary_circular` (NOT asymptotic normal)** — the exploratory's exact scheme. Justification: small-ish, serially-dependent, fat-tailed event series (the exploratory pooled excess kurtosis was 2.87; the in-sample best-of had 8.28); the asymptotic-normal `t` is anti-conservative at `n` in the low hundreds. The stationary bootstrap preserves the per-bank serial structure and tails.

**Mechanism (FROZEN, verbatim from `fa0f982a`):**
1. `t_obs` on the forward series (§1.3).
2. Impose H0 by de-meaning: `d_e = y_e − mean(y)` (zero-mean null, dependence/tails preserved).
3. For `b = 1..K`: draw a banks-as-blocks stationary circular block resample `d*_b` (geometric block lengths, per-bank `L`), recompute `t*_b` with HAC SE re-estimated on each resample.
4. `p = (1 + #{ t*_b ≥ t_obs }) / (K + 1)` (+1/+1 convention; avoids `p=0`).

**FROZEN bootstrap parameters:** `K = 10000`. Block length = Politis–White auto per bank group, `L ≥ 1` guard. RNG = `numpy.PCG64` seeded by `master_seed` (§5). Same as the exploratory.

This `p` is the single look-level evidence (§3). The DSR/selection gate (§2) is a **separate, additional** hurdle that must ALSO clear.

---

## 2. Selection-Absorption at N_sel = 1 (the load-bearing change) — FROZEN

### 2.1 Why N_sel collapses to 1

The garden-of-forking-paths charge attaches to *how the hypothesis was chosen*. In `fa0f982a` the firm chose QRB-6 by maximizing over an 11-proposal pool plus a 2-finalist comparison → that selection was charged at `N_sel = 3` (`qrb6_cb_event_study.md:228`), producing `SR0_pp_sel = 0.026861` and a DSR that **failed** at 0.907 even though both p's cleanly rejected.

The confirmatory **pre-commits this single structure NOW, before any forward event exists.** There is no portfolio, no finalist comparison, no parameter search at the look. The selection event is already spent (it burned `fa0f982a`); the confirmatory introduces **no new selection**. Therefore the confirmatory selection charge is `N_sel = 1`.

> **FROZEN: `N_sel = 1`.** (PM CONF-statistic / hard-constraint `n_sel_equals_1`. NHT adjudicates legitimacy.)

### 2.2 BLdP `SR0` at N_sel = 1 — the bracket collapses to ZERO

The DSR benchmark is BLdP (Bailey–López de Prado 2014):

```
SR0_ann = sqrt(Var[SR_n]) · [ (1 − γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e)) ]
```

The bracket is the **expected maximum of `N` standardized candidate Sharpes**. The two-quantile, γ-weighted form is the **large-`N` asymptotic** approximation. **At `N = 1` it must NOT be evaluated mechanically:** the first term `(1−γ)·Z⁻¹(1 − 1/1) = (1−γ)·Z⁻¹(0) = −∞` — the asymptotic formula breaks down. The finite-sample truth is exact and elementary:

> **E[max of a single standard-normal draw] = E[Z] = 0.**

A single pre-committed candidate has no maximum-over-alternatives inflation to subtract. Hence:

```
bracket(N=1)   = 0   (exact; the expected-max of one standardized draw)
SR0_ann_conf   = sqrt(Var[SR_n]) · 0   = 0   for ANY finite dispersion
SR0_pp_conf    = 0 / sqrt(252)         = 0
```

> **FROZEN: `SR0_ann_conf = 0.0`, `SR0_pp_conf = 0.0`, `N_conf = 1`.**

**Dispersion convention — IRRELEVANT at N=1, stated for the record.** The exploratory elected a planning dispersion `sqrt(Var[SR_n]) = 0.50` (`qrb6_cb_event_study.md:354-359`) because no per-proposal Sharpes existed. At `N=1` the bracket is 0, so `SR0 = dispersion × 0 = 0` regardless of whether dispersion is the exploratory's 0.50 or R5's 0.426385. **I therefore do NOT re-litigate the dispersion at N=1; it does not enter.** (Were `N≥2`, I would carry the exploratory's 0.50 unchanged for consistency; the point is moot here.)

### 2.3 Contrast with the exploratory — WHY the confirmatory can clear what the exploratory could not

| Quantity | Exploratory `fa0f982a` (N_sel=3) | Confirmatory `53981a4a` (N_sel=1) |
|---|---|---|
| bracket(N) | `0.852804` | `0` (exact, expected-max of one draw) |
| dispersion | `0.50` | irrelevant (×0) |
| `SR0_ann` | `0.426402` | `0.0` |
| `SR0_pp` | `0.026861` | `0.0` |
| DSR null benchmark | edge must beat a **0.4264-ann** selection floor | edge must beat **0** |
| Exploratory DSR outcome | `0.907 < 0.95` (FAIL despite p_agg=0.0231, p_post2015=0.0027) | — |

The exploratory's DSR failure was *entirely* the `N_sel=3` selection floor: the realized in-sample ann Sharpe 1.352 was strong, both p's cleanly rejected, but deflating against `SR0_pp=0.026861` pulled DSR to 0.907. **At `N_sel=1` that floor is removed** — the DSR now tests `SR > 0` against a zero benchmark, exactly the legitimate question for a single pre-committed structure on data the firm has never seen. This removal is the entire mechanical reason the confirmatory exists. The quantitative size of the removal: at a fixed `T`, the kill-switch drops by exactly `SR0_pp_sel·√252 = 0.026861·15.8745 = 0.4264` ann (see §4: at `T=506` the N=1 kill-switch would be `1.1619` vs the exploratory's `1.5883` — the `0.4264` difference IS the removed SR0).

### 2.4 DSR formula (pinned conventions, carried verbatim)

```
SR_pp     = SR_ann_holdout / sqrt(252)
var_term  = 1 − skew_holdout·SR_pp + ((xkurt_holdout + 2)/4)·SR_pp²
z_dsr     = (SR_pp − SR0_pp_conf)·sqrt(T_holdout − 1) / sqrt(var_term)
          = SR_pp·sqrt(T_holdout − 1) / sqrt(var_term)      [since SR0_pp_conf = 0]
DSR       = Φ(z_dsr),  clipped to [0,1];  gate cleared iff DSR ≥ 0.95
```

Degenerate pins (verbatim): `SR_ann_holdout ≤ 0 → DSR=0`; `var_term ≤ 0 → DSR=0` (gate FAIL, not technical failure). `Φ = scipy.stats.norm.cdf` (required; no approximation). The runner recomputes `var_term` with the hold-out's OWN skew/kurtosis at evaluation; the frozen field (§4) uses the `var_term=1` reference.

---

## 3. Look Design + Horizon (CONF-interim) — FROZEN: SINGLE TERMINAL LOOK

### 3.1 Single-look vs 2-look OBF — the decision (PM's flagged question)

The carry confirmatory used 2-look OBF (interim +2.5yr / terminal +5yr) because it had **~252 daily bars/yr** (≈630 bars at the interim). The QRB-6 event rate is **~30 verified-official event-days/yr** ({FED,BOJ,RBA,BOC}, ~8 decisions each/yr) — **~8× sparser**. A 2-look interim at +2.5yr would see only **~75 event-days**.

**Bootstrap-validity floor (banks-as-blocks).** With 4 bank-blocks {FED,BOJ,RBA,BOC} and Politis–White block lengths ~1–3 (the exploratory's per-bank L's were FED=3/BOJ=1/RBA=1/BOC=1), a non-degenerate pooled resample distribution and a stable HAC-studentized mean require enough events per bank-block that the geometric-block resample explores cross-bank variation rather than collapsing onto a handful of draws. **I freeze the floor at `n ≥ 90` deduped event-days** (≈22–23 events per bank averaged over 4 blocks; below this the per-bank block count is too small for the stationary bootstrap to mix). A `~75`-event interim sits **at/below this floor** — and even if technically runnable, it carries only ~9% power (§3.4) while spending α. Spending α on a sub-floor, ~9%-power interim is self-handicapping with no upside.

> **FROZEN DECISION: SINGLE TERMINAL LOOK.** The full one-sided `α = 0.05` is spent **once** at the terminal look. There is NO interim, NO alpha-spending function, NO OBF boundary. This departs from the carry-confirmatory pattern *because the event rate forces it* — the carry pattern was a function of 252 bars/yr, not of any principle that transfers to a 30-events/yr study.

### 3.2 Single-look boundary — FROZEN

```
Reject H0 at the terminal look  iff  bootstrap p ≤ 0.05   (equivalently t_obs ≥ z₀.₉₅ = 1.644854).
```

MC-SE straddle at `K=10000` (MC-SE = `sqrt(0.05·0.95/10000) = 0.002179`, half-width `0.0022`):

| Outcome | Condition |
|---|---|
| **PASS-eligible** (p-reject) | `p < 0.0478` (clean reject, below the straddle) **AND** DSR ≥ 0.95 (§2/§4) |
| **AMBIGUOUS** (MC straddle) | `0.0478 ≤ p ≤ 0.0522` |
| **KILL** (fail to reject) | `p > 0.0522` |

This mirrors the exploratory's **single-look** straddle convention (`[0.0478, 0.0522]` centered on α=0.05, `md:420`). The confirmatory carries **no extra-look penalty** — unlike the exploratory's remediated re-run, this is a genuine first single look on unsnooped forward data, so the boundary is the honest α=0.05, not the tightened OBF look-2 `0.0378`.

### 3.3 Planning Sharpe (the shrinkage freeze) — FROZEN

The exploratory in-sample pooled ann Sharpe `1.3521` is **upward-biased** (argmax of a 2-finalist comparison over an 11-proposal pool, plus in-sample overfit). Planning power at `1.352` would grossly overstate the test's sensitivity.

> **FROZEN: `SR_plan_ann = (1/3)·1.3521 = 0.4507` (annualized).**

Rationale: a **1/3 out-of-sample retention** is a defensible published-event-study decay — scheduled-CB / pre-decision drift effects (Lucca–Moench 2015 pre-FOMC drift; CB-decision FX event studies) typically retain on the order of a third-to-half out-of-sample after a realistic cost+decay haircut. The 1/3 fraction is the conservative end. This lands at `0.45`, in the same `[0.3,0.5]` band as the exploratory's own frozen planning anchor (`SR0_ann_sel=0.4264`) — so it is consistent with the exploratory discipline while being a **fresh, separately-justified** number (I do not import the exploratory's 0.4264, because at N=1 there is no `SR0` to anchor to — see §2.2). A James–Stein shrinkage of 1.352 toward 0 would land in the same neighborhood; I freeze the single auditable 1/3-decay number rather than add a second free parameter.

Per-event planning effect (inheriting the exploratory's frozen convention `md:546` verbatim):
```
g_pp = SR_plan_ann / sqrt(252) = 0.450715 / 15.874508 = 0.028392
```

### 3.4 Power curve — FROZEN (shown work)

Pooled event-study non-centrality at `n` deduped event-days: `λ = g_pp·√n`; `power = Φ(λ − z₀.₉₅)`, `z₀.₉₅ = 1.644854`.

| n (events) | years (~30/yr) | λ = 0.028392·√n | power = Φ(λ − 1.644854) |
|---|---|---|---|
| 30 | 1.0 | 0.15551 | **0.068** |
| 60 | 2.0 | 0.21993 | **0.077** |
| 90 | 3.0 | 0.26935 | **0.085** |
| **120** | **4.0** | **0.31102** | **0.091** |
| 150 | 5.0 | 0.34773 | **0.097** |
| 180 | 6.0 | 0.38092 | **0.103** |

**80% power requirement (disclosed as structurally impractical):**
```
n*(80%) = ((z₀.₉₅ + z₀.₈₀)/g_pp)²  = ((1.644854 + 0.841621)/0.028392)²  ≈ 7670 events ≈ 256 years.
n(50%)  = (z₀.₉₅/g_pp)²            ≈ 3357 events ≈ 112 years.
```

> **The event-study has many event-days but each carries little independent signal at the honest planning Sharpe; pooled non-centrality grows only as √n. 80% power is unreachable in any practical horizon.** This is the explicitly-disclosed power reality (mirrors carry §3.5's ~34% and the exploratory §5's ~13–18%). A non-rejection (KILL) at the terminal look is uninformative *as evidence of no edge*, but does NOT license continued spend (QR decision map). High event-to-event autocorrelation (large PW `L`) would push realized power BELOW this iid-event curve — so the curve is an UPPER bound. NHT reviews this statement (CONF-interim done_when).

### 3.5 Lock horizon → look date — FROZEN

Given that 80% power is unreachable, the horizon is set by the **validity-vs-deferral balance**, not by a power target: pick the smallest horizon that (a) clears the `n ≥ 90` bootstrap-validity floor with margin and (b) does not defer a binary outcome unreasonably for marginal power. Forward window starts **2026-04-07** (first event strictly after the exploratory terminus 2026-04-06).

> **FROZEN: terminal `n* = 120` deduped event-days → lock horizon `+4.0 years` → LOOK DATE `2030-04-07`.**

At `+4yr`/`n≈120`: above the 90-event floor with comfortable margin; power ≈ 9.1%; kill-switch ≈ 2.39 (§4). The **horizon–kill-switch curve is disclosed** so the CEO may elect a longer horizon if a lower kill bar is preferred:

| terminal n | years | kill-switch (ann Sharpe, SR0=0, var_term=1) | power |
|---|---|---|---|
| 90 | 3.0 | 2.7678 | 0.085 |
| **120** | **4.0** | **2.3936** | **0.091** |
| 150 | 5.0 | 2.1391 | 0.097 |
| 180 | 6.0 | 1.9516 | 0.103 |
| 300 | 10.0 | 1.5101 | ~0.12 |

(Power gains beyond +4yr are sub-2% per additional 2 years — not worth multi-year deferral; +4yr is the frozen balance.) **The terminal look is BINDING — no extend, no re-parameterize, no third look.** If the forward run-rate yields `n < 90` at the look date → TECHNICAL_FAILURE (re-freeze with a later look date), never a KILL.

---

## 4. `kill_switch_threshold` Derivation (CONF-kill-switch-threshold) — FROZEN

The `kill_switch_threshold` is the **minimum forward-event annualized Sharpe** the structure must achieve **at the terminal look** to clear the DSR gate (`DSR ≥ 0.95`) at `SR0_pp_conf = 0` (N_sel=1) and `T_holdout = 120` (the +4yr terminal n). var_term reference = 1.

`DSR = 0.95 ⇒ z_dsr = Φ⁻¹(0.95) = 1.644854`. With `SR0_pp_conf = 0`:
```
z_dsr = (SR_pp − 0)·sqrt(T − 1) / sqrt(var_term) = 1.644854
```
**Pass 0 (var_term = 1):**
```
SR_pp = z_dsr / sqrt(T − 1) = 1.644854 / sqrt(119) = 1.644854 / 10.908712 = 0.150783
```
**Pass 1 (recompute var_term at SR_pp=0.150783 with exploratory anchor moments skew=0.45, xkurt=2.87 as the pre-registered placeholder):**
```
kurt_coeff = (2.87 + 2)/4 = 1.2175
var_term   = 1 − 0.45·0.150783 + 1.2175·0.150783² = 1 − 0.067852 + 1.2175·0.022735
           = 1 − 0.067852 + 0.027680 = 0.959828
sqrt(var_term) = 0.979708
SR_pp = 1.644854·0.979708 / 10.908712 = 1.611479 / 10.908712 = 0.147724
```
A modest skew/kurtosis correction (the exploratory pooled moments are mild). I freeze the **var_term=1 reference value** as the verbatim field (the conservative, auditable anchor; the runner recomputes var_term with the hold-out's OWN moments at evaluation — the placeholder shows the second pass moves the value by < ~0.05 ann, immaterial to the gate semantics, and the field convention matches the exploratory and carry which both froze the var_term=1 anchor):
```
SR_ann = SR_pp·sqrt(252) = 0.150783·15.874508 = 2.393603
```

> **FROZEN: `kill_switch_threshold: 2.3936`** (annualized forward-event Sharpe required at the terminal look to clear DSR ≥ 0.95 at `SR0_pp_conf = 0`, `N_sel = 1`, `T_holdout = 120`, var_term=1).

**Strictly different from the exploratory's `1.5883` (N_sel=3) and the carry-confirmatory's `1.2906` (different study) — per CONF-kill-switch-threshold.** Two opposing forces relative to the exploratory's 1.5883:
- (i) `N_sel=1` REMOVES the `SR0_pp=0.026861` floor → LOWERS the threshold by exactly `0.026861·√252 = 0.4264` ann at any fixed T. (At the exploratory's own T=506, the N=1 threshold is `1.644854/√505·√252 = 1.1619` — i.e. `1.5883 − 0.4264`, the removed SR0. This is the "at N_sel=1 it is LOWER" the prompt names.)
- (ii) `T_holdout=120 ≪ 506` SHORTENS the `√(T−1)` lever → RAISES the threshold.

Force (ii) dominates here (the forward sample is far smaller than the exploratory's accumulated 506), netting `2.3936 > 1.5883`. **The removal of the selection floor is real and is exactly 0.4264 ann at equal T; the headline value is higher only because the forward terminal n is small.** A 4-year clean-data single look on a sparse event series SHOULD demand a high realized Sharpe — this is the honest, disclosed bar. (If the CEO prefers a lower bar, §3.5's horizon curve shows e.g. T=300/+10yr → 1.5101.)

---

## 5. Run Mechanics to Freeze — FROZEN

### 5.1 Master seed (hex arithmetic SHOWN — the carry track had a hex-drift caught)

Rule (same convention as the carry confirmatory `int(first 6 hex, 16) mod 1_000_000`, `r5_confirmatory...md:478`): **`master_seed = int(first 6 hex chars of trial stem '53981a4a', 16) mod 1_000_000`.**

`'53981a'` base-16, digit-by-digit (`a` = 10):
```
5 · 16⁵ = 5 · 1048576 = 5242880
3 · 16⁴ = 3 ·   65536 =  196608
9 · 16³ = 9 ·    4096 =   36864
8 · 16² = 8 ·     256 =    2048
1 · 16¹ = 1 ·      16 =      16
10· 16⁰ = 10·       1 =      10
                      ----------
int('53981a',16)       = 5478426
5478426 mod 1_000_000  =  478426
```

> **FROZEN: `master_seed = 478426`.** *(orchestrator-verified: `int('53981a',16)=5478426`, `mod 1e6 = 478426`. No hex-drift — contrast the carry track's caught drift 924289→924033.)* Child seeds follow the exploratory convention (banks-as-blocks bootstrap uses `master_seed` directly via `numpy.PCG64`).

### 5.2 Constants (pinned)

- **`K = 10000`** resamples (exploratory default; the single pooled test is cheap enough for full K).
- **`alpha = 0.05`** one-sided, spent once at the single terminal look (§3.2).
- **MC-SE** `= sqrt(p(1−p)/K)` at K=10000: `p=0.01→0.000995`, `p=0.05→0.002179`, `p=0.10→0.003000`, `p=0.50→0.005000`. Straddle half-width at the α=0.05 boundary = **0.0022** → closed straddle `[0.0478, 0.0522]` (§3.2).
- **Bootstrap scheme:** `bank_level_blocks_stationary_circular`, Politis–White auto block length per bank group, `L ≥ 1` guard, +1/+1 p convention, de-meaned H0 (`d_e = y_e − mean(y)`), HAC-studentized mean (Newey–West Bartlett, bandwidth `max(L−1,1)`) recomputed on each resample. RNG `numpy.PCG64` seeded by `master_seed=478426`. **Identical to `fa0f982a`.**
- **Estimator conventions (mirror exploratory A-5 pins):** Sharpe `mean/std(ddof=1)·√252`, `rf=0`; skew `scipy.stats.skew(bias=True)`; excess kurtosis `scipy.stats.kurtosis(fisher=True, bias=True)`; DSR `Φ=scipy.stats.norm.cdf`, `Z⁻¹=scipy.stats.norm.ppf` (scipy REQUIRED — absence ⇒ TECHNICAL_FAILURE, never silent approximation); `periods_per_year=252`.

### 5.3 Evaluation command contract (math contract; QD owns implementation)

- **Refuse-without-receipt:** the runner MUST verify the committed freeze-receipt (SHA-256 of this confirmatory pre-reg + pinned code commit) BEFORE touching any post-2026-04-06 event. No metric on forward data before the receipt is committed.
- Runs **once** at the single frozen look date **2030-04-07** (no unscheduled peeks; the interim-monitoring state is data-integrity only).
- Filters forward events to **date > 2026-04-06** and to **verified-official grade** (`df = df[df['verification'] != 'training-memory-unverified']`, verbatim).
- Validity guard: if `n < 90` at the look → TECHNICAL_FAILURE (re-freeze), never a KILL.
- Emits: `n`, per-bank `L_pw`, `t_obs`, bootstrap `p`, the §3.2 boundary verdict, DSR (with hold-out moments at `SR0_pp_conf=0`), and the decision-map branch.

`numerical-question-routed:` see math-spec.yaml `numerical-question-routed` (QD scipy-confirmation of: bracket(1)=0 ⇒ SR0_pp_conf=0; `z₀.₉₅=1.644854`; kill-switch two-pass at SR0=0/T=120/var_term=1 → 2.3936 and the horizon curve; the power-curve points and n*(80%)=7670; `int('53981a',16)=5478426 mod 1e6 = 478426`).

---

*Mathematician-owned sections (CONF-statistic, CONF-interim, CONF-holdout co-sign on the bootstrap-validity floor, CONF-kill-switch-threshold) frozen above. The QR PART I structure, hold-out rule, decision map, and monitoring state are echoed by reference. NHT audit and principal-reviewer review precede CONSENSUS; CEO ratification precedes the freeze-receipt cut.*

**Mathematician signature:** Quantitative Mathematician, trial `53981a4a`, 2026-06-07. Decision: **sound**.
