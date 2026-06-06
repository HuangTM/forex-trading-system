# R5 Pre-Registration — Snooping Treatment, Finalized (HoQR)

**Replaces draft §3.2 and §3.3; adds new §3.4 (Frozen DSR inputs).**
**Owner:** Head of Quant Research · Trial family: 576746aa
**Co-signature condition satisfied:** Mathematician §7 (prereg-sections-mathematician.md) co-signs
the window/snooping proposal iff HoQR supplies, frozen, EITHER (A) a per-variant
post-development hold-out attestation, OR (B) the full-sample run plus honest-N, Var[SR_n],
and DSR threshold inputs. This document delivers the Method-A adjudication (negative) and the
frozen Method-B inputs. **Method B is OPERATIVE.**

---

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

### Honest-N pin: **N = 2**

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

### Sharpe table (representative estimate per independent look)

The DSR formula needs the Sharpe estimates across the N independent looks. I use the canonical
realized Sharpe of the representative member of each look, cited to source. For look 1 (pure
rate-differential carry) the representative member is **carry_fred = Bet #1**, the firm's flagship
carry validation; for look 2, **carry_momentum**.

| Look | Representative member | Sharpe (SR_n) | Source (file:line) |
|---|---|---|---|
| 1 — rate-differential carry | carry_fred (Bet #1, OOS) | **0.80** | `references/pre-registrations/carry_fred.md:16` (≥0.30 hypothesis; 0.80 realized), `references/pre-registrations/fred_carry_stripped.md:18,66` ("carry_fred achieved 0.80 on its OOS window") |
| 2 — carry+momentum hybrid | carry_momentum (OOS-2022) | **0.197** | trial `6a56df9c`, `.fintech-org/trials.jsonl:21` (`oos_sharpe=0.197`) |

Supporting per-member Sharpes (for the record; not the N=2 inputs): carry baseline 0.2841
(`trials.jsonl:20`), fred_carry_stripped 0.07464 (`trials.jsonl:22`), vol_target_carry 0.7594
full-history (trial `d572999d`, `trials.jsonl:14`). These collapse into look 1's representative
(carry_fred 0.80, the strongest and the one the firm acted on); using the strongest member is the
conservative, anti-survivorship choice — it makes Var[SR_n] larger and the DSR threshold higher.

### Var[SR_n] — computed by hand over the N = 2 look Sharpes

Inputs: `SR_1 = 0.80`, `SR_2 = 0.197`.

- **Mean:** `SR_bar = (0.80 + 0.197) / 2 = 0.997 / 2 = 0.4985`
- **Squared deviations:**
  - `(0.80 − 0.4985)^2 = (0.3015)^2 = 0.09090225`
  - `(0.197 − 0.4985)^2 = (−0.3015)^2 = 0.09090225`
  - sum = `0.1818045`
- **Variance (population, /N):** `0.1818045 / 2 = 0.09090225`
- **Variance (sample, /(N−1)):** `0.1818045 / 1 = 0.1818045`

> **Var[SR_n] (FROZEN) = 0.0909** (population estimator, dividing by N). `sqrt(Var[SR_n]) = 0.3015`.

Estimator choice: the BLdP `SR0` benchmark is the *expected maximum* of N draws from a distribution
of estimated Sharpes; `Var[SR_n]` is the dispersion of that trial distribution, for which the
population (÷N) estimator is the natural plug-in with only N=2 looks. The sample (÷(N−1)) value
0.1818 is recorded for the Mathematician's election; it would *raise* `sqrt(Var)` to 0.4264 and make
the haircut more conservative. **Frozen primary: Var[SR_n] = 0.0909, sqrt = 0.3015.** Routed to
quant-developer for arithmetic verification (ROUTE_TO below); the values above are HoQR's and are the
frozen inputs.

### DSR threshold inputs handed to the Mathematician (frozen)

The Mathematician owns plugging these into `SR0` (§7.2). The frozen inputs are:

- `N = 2`
- `Var[SR_n] = 0.0909` (population; sample 0.1818 recorded as the conservative alternative)
- `sqrt(Var[SR_n]) = 0.3015`
- `γ = 0.5772156649` (Euler–Mascheroni)
- `e = 2.718281828`
- The two normal-quantile arguments the formula needs: `Z⁻¹(1 − 1/N) = Z⁻¹(0.5) = 0` and
  `Z⁻¹(1 − 1/(N·e)) = Z⁻¹(1 − 1/5.43656) = Z⁻¹(0.81607)`. (HoQR notes that with N=2 the first
  quantile term `Z⁻¹(0.5) = 0` zeroes the `(1−γ)` leg, so `SR0` reduces to
  `0.3015 · 0.5772 · Z⁻¹(0.81607)`. The exact `Z⁻¹(0.81607)` evaluation and the final `SR0` scalar
  are the Mathematician's to compute and sign — this is a normal-CDF inverse, not hand arithmetic.)

> **ROUTE_TO: quant-developer** — verify (1) `Var[SR_n]` arithmetic above
> (mean 0.4985, squared devs 0.09090225 each, population variance 0.09090225); and (2) the
> normal-quantile `Z⁻¹(0.81607)` so the Mathematician can finalize `SR0`. Inputs frozen by HoQR; QD
> verifies, does not re-derive N.

---

*HoQR sign-off: Method A UNAVAILABLE (per-variant negative attestation above); Method B operative;
N = 2; Var[SR_n] = 0.0909. Pinned to the freeze-receipt at assembly.*
