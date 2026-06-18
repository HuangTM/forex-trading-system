# Field Survey: FX Trading Systems, RL/ML, and the Math of Sound Strategy (2026-06-18)

Commissioned research (3 cited web-research streams) to ground the next hypothesis cycle in
what the field actually does and what's theoretically sound. **Honest frame:** knowledge was
never the firm's bottleneck (a confirmable edge is) — this survey produces *vetted candidates*,
which still must clear the firm's confirmability + forward-test bar. Full cited streams are in
the session task outputs; this is the actionable distillation. PM-verified corrections noted.

## Convergent thesis (all 3 streams independently)
The firm's standing **"dataset wall"** is corroborated by independent literature: the
strongest-evidence FX edges are either (a) **slow/monthly** (carry, value → un-confirmable on a
≤2yr clock) or (b) **intraday flow-driven** (order-flow, session, execution → need the
tick/volume/order-book data the firm structurally lacks, and spot FX arguably *can't* consolidate
a volume tape). No model architecture manufactures signal the data doesn't contain.

## 1. Strategy archetypes (financial-markets stream)
**The real FX factor zoo (academic backing):** carry (rate-diff risk premium; SR~0.8 gross,
decaying ~5.4%/yr post-2008), value (PPP reversion; multi-year horizon), momentum (TS-trend
SR~0.4 over 67 markets incl 12 FX; XS-momentum real but high-turnover/cost-sensitive), dollar factor.

**Runnable on the firm's data (D/1h price-only), ranked by mechanism × runnable × ≤2yr-confirmable:**
1. **TS trend/momentum** — best fit; century evidence; but SR~0.4 → hard to clear DSR in ≤2yr.
2. **XS momentum across the 12 pairs** — real; cost-sensitive (the new spread column is load-bearing).
3. **Month-end / calendar-flow** — *most confirmability-friendly new candidate*: datable, recurs
   ~12×/yr, documented equity-hedge-rebalancing mechanism (Melvin–Prins JFE); 1h adequate for the
   day-effect (not the fix-window). Highest events/yr of any *real* effect.
4. **Carry** — strongest economics, but needs external rate data + monthly horizon kills ≤2yr; structural tilt only.

**Avoid (folklore or need-data-we-lack):** chart/candlestick patterns (data-snooping, no mechanism),
naive single indicators, COT-contrarian (uncited lore), triangular/stat-arb (HFT/latency, zero
retail capacity), order-flow strategies (need flow data), PPP-value as a ≤2yr strategy.

**Field overclaims:** carry/momentum SRs are gross/full-sample/pre-decay; "200yr evidence" is
regime-dependent/possibly data-snooped; "chart patterns 600%" is snooping-uncorrected;
Meese–Rogoff stands — daily *directional* forecasting doesn't reliably beat a random walk OOS.

## 2. RL / ML (RL stream)
- **RL for direct FX alpha = the trap.** Field's own review: "no decent profitability for the
  majority of works." Best honest net-of-cost FX-RL IR≈0.52 (no better than classical). RL training
  is a giant *uncounted* multiple-comparisons machine (architectures × rewards × seeds) — exactly
  what DSR defends against. Reproducibility unsolved (seed alone flips outcomes; Henderson 2018).
- **RL execution/market-making** is defensible but needs order-book/flow data → points to CME FX
  *futures* or equities, not spot OHLCV.
- **The ONE legitimate offensive ML move: meta-labeling** (López de Prado) — gradient-boosted trees
  (never deep nets) on top of an *already-validated* primary signal, learning when to size-up/veto.
  Bounded DoF, no data-volume need. ML's honest role here = risk/sizing/filtering/stationarity, NOT direction.
- **Borrow the reward machinery, not the agent:** differential Sharpe (Moody–Saffell), vol-scaling,
  CVaR-aware objectives. Plus frac-diff (AFML Ch.5) + triple-barrier/uniqueness-weighted labels.

## 3. Math of sound strategy + firm-code findings (math stream, PM-verified)
**Unifying law:** power ∝ √(*independent* observations) — Lo's autocorr correction, Grinold √breadth,
`t=SR·√T`, DSR's √(2 ln N), and the effective-N haircut are all one law; all degrade when
"independent" is violated by serial- or cross-correlation.

**Verified literature-correct in the firm:** `dsr.py` (Deflated Sharpe, EVT max-SR, skew/kurtosis
denominator), `honest_n.py` (ratified N=30, fail-closed, over-deflating census), and the
forward-OOS-over-historical-OOS philosophy (ahead of most shops). **CPCV with purge+embargo EXISTS**
(`scripts/trial_48_is_eval.py`: `_build_cpcv_folds`, purge=embargo=480, N_groups=6, k=2) — the
math stream's "no CPCV" claim was a false negative (it only grepped `src/`/`harness/`, not `scripts/`).

**Valid, actionable findings (candidate backlog — none committed; NHT/PR-gate before any DSR-gate change):**
1. **Effective-N haircut into the DSR denominator + pooled-Sharpe SE.** The Kish design-effect
   `N_eff = N/(1+(N−1)ρ̄)` is already correct in rubric **G5** but only in the *pre-data* screen.
   N=30 is a *raw attempt census*, not a correlation-clustered effective count (Bailey–LdP canonical).
   Since FX strategies share the USD factor, true effective-N < 30 → the firm currently **over-deflates**
   (safe direction; costs missed edges, not false passes). Worth clustering the trial set per LdP.
2. **Lo autocorrelation-corrected annualization.** `metrics.py` annualizes by a constant
   `periods_per_year` (naive √P) — overstates Sharpe under autocorrelation; the 1h transition makes
   signals *more* persistent, so this matters more now. Apply η(q). (Verified: no autocorr term.)
3. **MinBTL framing.** At N=30, MinBTL ≈ 2·ln(30)/SR² ≈ 6.8yr to support IS Sharpe=1. The ≤2yr
   confirmability window is *below* its own MinBTL → IS Sharpe is structurally untrustworthy and the
   **forward test does all the validation work**. Reframes the firm's "AMBIGUOUS by a hair" history as expected.
4. **Make CPCV a shared, tested library** (it's per-trial-script today → drift risk across trials).
5. **Compute PBO/CSCV** (have DSR, not PBO) once CPCV paths are library-ized.
6. **Sizing:** prefer μ-free (vol-targeting / risk-parity) or capped fractional-Kelly — full-Kelly /
   unconstrained Σ⁻¹μ are error-maximizers under 12 noisy μ (Chopra–Ziemba 20:2:1).

**Correctly out of scope (need data the firm lacks):** square-root/ADV impact models, Almgren-Chriss
calibration, Avellaneda-Stoikov — all need volume; the current spread + linear-slippage cost model is
the *correct* posture for zero-volume FX (fabricating V would be a manufactured input).

## Bottom line for the next hypothesis cycle
Price-only sweet spot = **trend/momentum + cross-sectional momentum + month-end/calendar-flow**, run
through the firm's existing DSR/CPCV/forward-test gates, sober about low post-2010 net Sharpes. The one
ML option is a **meta-labeling layer on a validated primary signal**. The highest-leverage *methodology*
upgrades are the effective-N-haircut-into-DSR and Lo's annualization correction. RL-for-direct-alpha,
chart-pattern folklore, and any volume/flow strategy are out.
