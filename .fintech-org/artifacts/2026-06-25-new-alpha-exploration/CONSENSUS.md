# Consensus on: New-Alpha Strategic Exploration — Ranked, Costed, Gated Shortlist

**Status:** ratified_with_dissent (distributed quorum: cro + head-of-quant-research, 2026-06-25; surfaced to Board, non-blocking)
**Session artifacts:** `.fintech-org/artifacts/2026-06-25-new-alpha-exploration/`
**Date:** 2026-06-25
**honest-N:** 30 (UNCHANGED — confirmed in trials.jsonl; all exploration entries carry `counts_toward_deflation_denominator: false`)

---

## Roles staffed

| Role | Rationale |
|------|-----------|
| Academic-Factor Lens Generator | Produced 7 directions through the lens of peer-reviewed OOS factor literature (carry, value, TSMOM, VRP, DOL, BAB, option-skew). |
| Practitioner-Microstructure Lens Generator | Produced 7 directions through the lens of practitioner microstructure and execution (London Fix, COT, option RR, macro-surprise, session-open overlay, CIP-basis, retail SSI). |
| Contrarian-Outsider Lens Generator | Produced 7 directions through a first-principles / non-consensus lens (FX-VRP, commodity-futures transplant, retail-COT contrarian, multi-asset basket, CB-text ML, EM carry, harness-as-a-service). |
| Null-Hypothesis Tester (NHT) | Folklore cull and structural skeptic pass over all 21 directions; dissent preserved verbatim; non-blocking, concurs with shortlist, dissents on three structural meta-points. |
| Quant Researcher (QR) | Structured the 3 surviving non-ML candidates (C1/C2/C3) into full four-field + hypothesis records. |
| ML Researcher (MLR) | Evaluated all ML/HFT-adjacent directions; approved one (CB-text) narrowly; cut ML-on-price, ML-on-COT, HFT. |
| Head of Quant Research (HoQR) | Merged 21 raw directions → 8 themes → ranked shortlist of 3 (with a caveated 4th); issued direction call; made the FX-vs-transplant call explicit. |
| Chief Risk Officer (CRO) | Size-reduced (0.45); issued per-direction allocations and guardrails; flagged deployability gate on D-TREND-FUTURES; documented blowup analogs; enforced reversible-data vs irreversible-honest-N asymmetry. |
| Principal Reviewer (PR) | Single-wave cold review of QR + MLR artifacts; approve-with-conditions; 0 blocking-for-shortlist; 2 binding-for-future-pre-registration (F-001, F-008). |
| PM | Sequenced all phases; enforced CRO firewall; synthesized this consensus; preserved NHT dissent verbatim; confirmed trial counter unchanged; made no technical or strategy calls. |

---

## Decision

**THIS CYCLE PRODUCED A COSTED, GATED, RANKED SHORTLIST OF STRUCTURALLY-NEW DIRECTIONS — NOT A SPEND, NO BACKTEST, HONEST-N STAYS 30.**

The firm has proven (CADJPY consensus: net-of-cost SR < 0 across all 84 pair×family combos on retail OHLCV) that existing-data families are exhausted. The purpose of this cycle is to map the directions that COULD produce a positive-SR candidate on new data or new mechanisms, so the Board can make an informed data-acquisition and research-authorization decision. 21 raw directions were generated across 3 lenses → NHT folklore cull → QR structuring + MLR evaluation → HoQR ranking → CRO risk position + PR review. The shortlist is the input to a future Board authorization, not a commitment of firm resources.

**No pre-registration is authored. No trial counter increments. No data is purchased.**

---

## The Reframe: The Harness Is the Asset

The firm's durable asset is its validated research harness (CPCV, Deflated Sharpe, confirmability rubric, honest-N). Retail-FX-OHLCV is the proven-exhausted raw material. The out-of-box win is not faster or fancier signals on the same data — it is pointing the harness at a real-volume futures venue where documented edges live and where the firm's confirmed binding walls (cost-dominance, USD-concentration, no true volume) become structurally non-binding. That is the strategic reframe this cycle produced.

---

## § The Ranked Shortlist

All four directions are ranked by expected-edge-per-data-acquisition-cost, weighted by the firm's hard-won confirmability lens (an edge un-confirmable in ≤3yr is not spendable — QRB-6 precedent: power 9% at the 2030 look).

| Rank | Direction | Hypothesis (one-line) | Data Class + Cost | Cheap $0 Test + Kill Number | Walls Attacked / Walls NOT Solved | Confirmability Horizon | CRO Allocation + Deployability | PR Conditions |
|------|-----------|----------------------|-------------------|-----------------------------|----------------------------------|----------------------|-------------------------------|---------------|
| **#1** | **TREND-FOLLOWING ON FUTURES** (CME FX futures + commodity/cross-asset futures transplant) | IF 12-month TSMOM is run across CME FX futures (6E/6B/6J/6A/6C/6S/6N/6M) and/or commodity/rates futures, THEN net-of-cost Sharpe > 0 because CME RT cost (~0.2-0.8 pip-equivalent) is 5-10x below retail spot, making the documented gross OOS SR (~0.4, Moskowitz-Ooi-Pedersen 2012; Hurst-Ooi-Pedersen 2017) survivable. | CME/Globex futures OHLCV + true exchange VOLUME + OI; ~$0 (free G10 daily via Yahoo/public series) for the kill test; ~$250-500/yr (Norgate/Nasdaq-DataLink) for backtest-grade continuous series; **LOW / $0 to test** | Read MOP-2012 FX-futures sleeve OOS SR and Hurst-2017 Exhibit 2 post-2000 commodity-trend SR; compute CME round-trip cost as SR drag from public fee schedules. **KILL if post-2000 OOS SR < 0.3 OR modeled RT cost > 25% of gross per-rebalance edge OR min-viable-notional > capital base.** ~1hr desk arithmetic, $0. | W1 (cost 5-10x lower) ATTACKED; W4 (real exchange volume/OI) ATTACKED; W2 (40+ contracts dilutes USD loading) PARTIALLY attacked; W3 (12-month long-lookback is multi-regime by construction) PARTIALLY attacked. **NOT solved:** W2 — FX futures universe is still USD-cross-loaded, effective independent bets ~2-4; W3 — TSMOM still suffers in sharp reversals; **NEW wall introduced:** capital-scale (min viable contract notional at firm's capital base may be non-deployable). | **SHORTEST of the genuine new-data directions.** Trend is daily/monthly across 40+ contracts; effective breadth (post-correlation) of ~5-10 independent bets puts years_to_validate plausibly in the **~2-4yr band** — the ONLY new-data direction with a credible path inside the firm's ≤3yr confirmability bar. Breadth, not frequency, is what shortens the horizon. The FX-futures-only subset recurs the confirmability wall at effective-N; the commodity/rates transplant (T5) is the decisive breadth unlock. | **0.55; RESEARCH-ONLY designation until min-viable-notional reconciled with capital base.** 6E = 125,000 EUR fixed notional; no fractional sizing; micro-futures (M6E ~12,500 EUR) must be confirmed available + liquid. A strategy you cannot size is a study, not a strategy. Treat the whole 40+-contract program as ONE correlated bet (cross-asset trend correlation → 1 in liquidation regimes). | F-002 (kill-number: apply a McLean-Pontiff post-publication decay haircut to the gross SR before the arithmetic gate; pin the turnover input to a published figure not a desk-supplied one); F-005 (add explicit machine-checkable years-to-validate ≤3yr pre-check as a hard gate, not a soft prose flag). |
| **#2** | **CIP / FX-SWAP-BASIS** (cross-currency basis as funding-stress predictor) | IF the 3-month EURUSD cross-currency basis (CIP deviation) predicts subsequent 1-4 week EURUSD excess return (negative basis → subsequent USD weakness as funding stress unwinds), THEN gross SR ~0.4-0.6 OOS (Du-Tepper-Verdelhan 2018 JF; Avdjiev 2019 JF) is achievable at low turnover. | Daily 3M cross-currency basis swap spread; **FREE for kill test** (BIS quarterly + FRED OIS-spread reconstruction); ~$1,200-3,600/yr (Refinitiv) for daily if it survives; **$0 to test** | Download BIS quarterly EURUSD CCS basis (free) and/or reconstruct from FRED; align to quarterly spot; compute Spearman rho vs lagged basis. **KILL if |rho| < 0.15 WITH a CI/permutation p-value at the honest effective-N (NOT a bare point estimate — F-001 condition) OR sign contradicts theory OR DTV-2018 net SR < 0.3.** ~1hr, $0. | W4 (interbank derivatives pricing — entirely distinct from OHLCV) ATTACKED; W3 (funding stress fires across GFC 2008/COVID 2020/2023 banking stress — NOT the 2022-23 hiking cycle) ATTACKED on a **different axis**. W1 (1-4 week hold, low turnover) INDIRECTLY attacked. **NOT solved:** W2 — primarily a USD-funding / EURUSD-centric signal; USD-concentration is **NOT escaped** (it is partly a USD-funding signal by construction). **NEW regime-concentration risk on a different axis:** signal may fire ONLY in ~3 independent stress episodes → recurs the confirmability wall on a stress-vs-calm axis. | **MEDIUM-LONG; probable dataset-wall RELOCATION, not escape.** 1-4 week signal on essentially one funding axis (EURUSD-centric) with stress-clustered events = low effective independent event count → multi-year confirmability horizon (~4-6yr), similar to QRB-6. Strong evidence and $0 test earn rank 2 (most orthogonal data class); the long horizon and W2 non-solution keep it below #1. Board must go in eyes-open on the confirmability caveat. | **0.50; $0 / FREE-DATA test FIRST.** Effective-N must count stress EPISODES (~3), not calendar days — any SR/DSR computed on daily obs across 3 clustered events is a small-sample illusion; require episode-level block-bootstrap at pre-registration. No counted trial until free probe confirms event count and per-episode signal survive honest effective-N deflation against the 21-wide surface. | F-001 (MAJOR / binding-for-pre-registration): the Spearman kill-test must gate on rho WITH a CI / permutation p-value at honest effective-N, NOT a bare |rho| < 0.15 point estimate — at ~3 independent stress episodes the SE on rho is too large for a point-estimate gate to be decisive. |
| **#3 (caveated)** | **CB-TEXT REGIME CLASSIFIER** (LLM zero-shot classification of FOMC/ECB/BOE/BOJ statements as regime-conditioning overlay) | IF LLM zero-shot classification of CB statements predicts the 90-day policy direction (hike/cut/hold) with accuracy whose 95% Wilson CI lower bound clears the 33% 3-class chance rate (N~120), THEN that regime label can gate an existing carry/trend sleeve to remove documented W3 regime-dependence — testable by auto-labeling ~120 FOMC statements against realized fed-funds direction. | Full-text CB statements (all FREE, public); ~$0-50 LLM API for the test (or $0 on a local model); **ZERO data cost** | Auto-label ~120 FOMC statements (2010-2024) by sign of 90-day-forward fed-funds change; zero-shot LLM classify hawkish/dovish/neutral; measure accuracy with 3-class Wilson CI; run a keyword/dictionary baseline ALONGSIDE (mandatory — load-bearing honesty gate per MLR). **KILL if accuracy < 70% OR Wilson CI-lower < 33% OR LLM does NOT beat the dictionary baseline by more than its CI.** Half-day, ~$0. | W3 (regime-dependence — explicit target; exogenous regime label converts regime-dependent strategy to regime-conditioned) ATTACKED; W4 (CB text = categorically different data class carrying CB intention) ATTACKED. **NOT solved:** W1, W2 — NOT touched. **CRITICAL CAVEAT:** this feasibility test tests CLASSIFICATION READABILITY (look-ahead labeled), NOT a tradable edge. A passing classifier is necessary but not sufficient. Even if the classifier passes, whether the regime label improves a gated carry Sharpe net-of-cost is a SEPARATE downstream step that re-inherits W1/W2/W3-residual AND the same carry confirmability horizon. | **TWO-STAGE and honest.** STAGE-1 (does the classifier work?): confirmable in HALF A DAY — this is what earns rank 3. STAGE-2 (does the regime gate add net-of-cost carry edge?): inherits the SAME multi-year carry confirmability horizon the firm already hit (~8 events/yr is the hard ceiling; same wall QRB-6 died on). **Ranked #3 NOT because the alpha is proven but because the cost-to-decisively-test is the lowest in the slate and it attacks the firm's single most-documented failure (W3).** | **0.25; lowest-conviction direction on confirmability grounds.** ~8 events/yr is a hard small-sample ceiling. Cannot be validated independently of the host sleeve — pre-register the host and the overlay jointly or the result is uninterpretable (cf. QRB-6 cost-coverage void lesson). Cap bandwidth: earns a probe, not a program. | F-007 (observation): the feasibility screen is double-contaminated — look-ahead labels AND LLM pretraining recall post-dating the statements; the dictionary baseline is the load-bearing control that disentangles these. Dictionary baseline is MANDATORY, not optional. |
| **(4th, flagged)** | **(T2) COT POSITIONING — ranked but NOT on shortlist** | IF 4-week change in CFTC Leveraged-Fund net positioning predicts subsequent 4-week spot return at |t|>2, THEN gross SR ~0.4-0.6 survives at weekly-monthly rebalancing on the FREE CFTC COT series. | CFTC COT Disaggregated CSV — **FREE, $0 | Spearman rho of 4-week Leveraged-Fund net change vs forward 4-week EURUSD spot; KILL if rho < 0.05 or CV gross SR < 0.3. ~2hr, $0.** | W4 (true exchange positioning) ATTACKED; W3 (positioning re-prices across regimes) PARTIALLY attacked. **NOT solved: W1** (modest edge, thin margin over cost). **DECISIVE binding caveat (per generator's own honest estimate):** years_to_validate ~6yr — exactly the QRB-6 dataset-wall pattern recurring in a new guise. | **~6yr by the generator's own honest estimate.** Free data does NOT buy a short horizon. Edge-per-DOLLAR is infinite; edge-per-CONFIRMABILITY-YEAR is poor. **Below the shortlist.** A cheap kill-test is warranted but it is flagged, not a primary program. | *(not allocated as primary)*  | — |

---

## § Closed Doors

**These directions are definitively closed for this cycle and, unless the firm's structural constraints change, for future cycles under the same data-class + mechanism assumptions. Record explicitly.**

### ML-on-Price: CONFIRMED DEAD
ML applied to the same OHLCV (or tick-count, which is not true volume) data does not create signal that is not there. It raises the effective trial count and the expected max-in-sample Sharpe (N=128 → >2.6 at true-zero skill), making the DSR deflation problem worse, while OOS performance degrades with more in-sample optimization on memory-bearing series (Bailey et al.). The CADJPY consensus established net-of-cost SR < 0 across all 84 pair×family combos on retail OHLCV. No data-class change → no admissible ML direction. This is the firm's hard-won prior, confirmed by the ML Researcher this cycle.

### HFT: NOT VIABLE ON RETAIL INFRA — CONFIRMED WITH SPECIFICS
(1) **Latency:** competitive FX HFT operates at single-digit microseconds; retail order paths are tens-to-hundreds of milliseconds — 3-5 orders of magnitude slower. Retail is the last to see and last to act. (2) **Co-location:** competitive edges require cross-connects in LD4/NY4/TY3 — $tens-of-thousands/month plus exchange membership; not a retail capability. (3) **True L2/order flow:** real spot-FX depth-of-book is interbank (EBS/Reuters Matching) or bank-internal; retail "depth" is a broker-curated approximation. Genuine L2 costs $50k+/yr (per practitioner slate) and is STILL a proxy for spot. (4) **Cost:** HFT profits per trade are sub-pip; at retail spreads (0.4 pip normal, 3-5 pip at news release) the spread alone exceeds the entire edge — this is Wall W1 head-on. **The out-of-box win is not faster or fancier — it is pointing the harness at a futures venue where real volume exists.**

### Carry-Family Variants (A1/A6/C6): Shelved Mechanism in New Clothes
Three directions in the slate repackaged the firm's already-shelved carry mechanism (R5/QRB archive, RULE_4_AMBIGUOUS, DSR=0.907): A1 (crash-overlay on G10 carry), A6 (carry-timing via option skew), C6 (EM carry). None is a clean NEW mechanism. The PM's FOUR-WALLS-STAY-CLOSED constraint correctly excludes them as candidates. They remain available as cheap kill-tests (the skew-signal sub-variant via free FRBNY EUR/JPY data is worth a single-shot test) but not as programs.

### Option VRP Harvest (A4/C1): Execution-Infrastructure-Blocked
Carr-Wu (2009) FX VRP is a genuine OOS factor. The mechanism requires selling options and delta-hedging, which at retail FX option bid-ask "destroys the premium." The firm has no institutional option-execution infrastructure. An OOS-survivor factor that is un-executable at the firm's access tier is not a tradable OOS-survivor for this firm. Future-cycle candidate once infra is resolved; not this cycle.

---

## § The Disciplines That Make the Cheap Test Honest

These four disciplines are non-negotiable conditions the PM carries forward from this cycle into any future pre-registration. Violating any of them is the mechanism by which the cheap-test becomes the firm's next p-hacking instrument.

1. **Single-shot pre-committed kills.** Every cheap feasibility test is run ONCE with a stated threshold, declared in advance. The test is not iteratively tuned. If it passes, the direction advances to a separate, gated, pre-registered step. If it fails, the direction is retired. No iterations.

2. **Declare the 21-direction generation surface.** The shortlist is the survivor of a 21-direction search across 3 deliberately-divergent lenses. The generation surface must be formally declared at any future pre-registration. Picking the best of 21 by edge-per-cost is itself a snoop unless the gross-edge basis is taken from PUBLISHED OOS literature (as specified) and NOT from any firm-data peek.

3. **Effective-N deflation accounts for the selection surface (F-008 — binding for future pre-registration).** When a surviving direction advances to a committed pre-registration, the effective N must increment by the SELECTION SURFACE (21 generated + cheap tests run), not just +1. Deflating by +1 repeats the exact under-deflation the honest-review reset already corrected. The mechanism count (~6-7 distinct mechanisms, not 21) is the honest denominator — deflating by naive 21 over-corrects; deflating by 1 under-corrects. NHT owns this gate at pre-registration.

4. **Effective-N, not nominal-N, governs every confirmability claim.** The correlated futures program = 1 (not 40). CIP basis = ~3 independent stress episodes (not 16 years of quarterly obs). CB-text = ~8 events/yr. These are the honest effective-N denominators for any future confirmability arithmetic.

---

## § Dissent (NHT) — Verbatim, Append-Only

> DISSENT (append-only, verbatim for CONSENSUS.md). I record three structural objections that must not be paraphrased away in ranking. (1) TREND-FOLLOWING ON FUTURES IS THE ONLY THEME THAT ESCAPES THE BINDING WALL ON ITS MERITS, AND IT IS TRIPLE-COUNTED. A2 (FX futures TSMOM), C2 (commodity-futures trend) and the trend/momentum sleeves of C4 are the SAME factor; the slate's apparent breadth here is an artifact of three lenses hitting one mechanism. The firm should advance ONE trend-on-futures program, not three, and must NOT let cross-lens agreement masquerade as independent confirmation. (2) EVERY LOW-FREQUENCY "NEW-DATA" DIRECTION RELOCATES THE CONFIRMABILITY WALL RATHER THAN ESCAPING IT. COT positioning (P2/C3), option skew/RR (A6/P3), CIP basis (P6), and REER value (A3) all change the DATA CLASS (escaping W4) while leaving the events/yr × per-event-Sharpe arithmetic that killed QRB-6 essentially intact — 1-4 week (or multi-year, for REER) signals on a handful of pairs cannot confirm in <=3yr. The practitioner generator's own COT note concedes ~6yr-to-validate; that honesty must survive into the consensus. P6 (CIP basis) is the best of this class and worth a cheap test, but it must be advanced with the explicit caveat that a passing cheap test does NOT retire the downstream confirmability wall. (3) THE SLATE IS A 21-WIDE SELECTION SURFACE AND THE WINNER INHERITS A SNOOP BURDEN ON TOP OF honest-N=30. The eventual pre-registration of any promoted direction MUST declare the size of the generation surface it emerged from and deflate accordingly; and every firm-data-touching cheap test must be a single-shot pre-committed kill with a stated threshold, run once, never iterated — otherwise the "cheap feasibility test" silently becomes the firm's next p-hacking instrument. Finally, I note for the record that the firm's already-falsified carry family reappears in this slate THREE TIMES wearing new clothes (A1 crash-overlay, A6 skew-timing, C6 EM-carry); none of these is a clean NEW mechanism, and the PM's FOUR-WALLS-STAY-CLOSED constraint should keep them as cheap kill-tests, not as candidates for advance.

**NHT disposition:** NHT concurs that the shortlist is the correct advance and that the firm's observe-only posture is correctly the default if the cheap tests fail. NHT dissents on three meta-points — over-confidence from cross-lens convergence, wall-relocation vs wall-escape for all low-frequency new-data directions, and the snoop burden on the 21-wide selection surface. All three dissents are recorded verbatim and are non-blocking for the shortlist. All three are BINDING at future pre-registration.

---

## § Principal Reviewer Findings — First-Class

PR verdict: **approve-with-conditions. 0 blocking findings for this shortlist. 2 binding-for-future-pre-registration.**

| Finding ID | Severity | Location | What It Is |
|-----------|---------|---------|-----------|
| **F-001** | **Major / binding-for-pre-registration** | C3 cheap-feasibility-test: Spearman |rho| < 0.15 kill-number | A bare point-estimate rho on ~16yr overlapping quarterly BIS data with no CI and no effective-N adjustment is NOT decisive. At the honest effective-N (a handful of independent stress episodes), the SE on Spearman rho is large enough that 0.15 is statistically indistinguishable from 0. The test can FALSE-KILL a real signal (point estimate < 0.15 by sampling noise) and FALSE-PASS a spurious one (a few stress quarters drive the rank order). **Fix: gate on rho WITH a CI / permutation p-value at the honest effective-N, not on a bare point estimate.** |
| **F-008** | **Observation / binding-for-pre-registration** | Cross-cutting: selection surface of 21 → shortlist promotion | The shortlist is correctly promoted as non-counting this cycle. The forward hazard: when any survivor advances to a committed pre-registration, the effective N must absorb the 21-direction generation surface + cheap tests run, not just +1. This is the firm's previously-corrected under-deflation failure — it will recur silently if effective-N is reset to +1 at advance. NHT owns this gate. |
| F-002 | Major | C1 cheap-feasibility-test: published MOP-2012 gross SR used raw as edge numerator | The kill-number is sensitive to a desk-supplied turnover input (not pinned by a public number) and does not discount for McLean-Pontiff post-publication decay (~35-58%); a generous turnover assumption or undiscounted gross SR can pass a direction whose live net edge is below the gate. Fix: apply a decay haircut and pin the turnover to a published figure. |
| F-003 | Minor | C2 cheap-feasibility-test: cost hurdle omits continuous-contract roll/curve cost | The artifact says roll "must be modeled explicitly" but the cheap-test field itself does not include a roll term in the hurdle arithmetic. Internal inconsistency; a direction could pass the cheap hurdle and have net edge eaten by roll at backtest. |
| F-004 | Minor | C2 kill-criteria: cross-sleeve correlation gate is deferred to committed backtest | The load-bearing diversification premise (low cross-sleeve corr → W2/W3 relief) has its only kill-number at the future costed stage. A $0 proxy exists now: realized cross-asset factor-return correlations are reportable from the same free daily series, and AMP-2013 / Hurst-2017 publish cross-asset correlations directly. |
| F-005 | Minor | C1/C3 confirmability sections | Only CB-text carries an explicit machine-checkable years-to-validate ≤3yr pre-check. C1 and C3 leave it as a soft/prose flag. Given QRB-6 died at power=9%, the same explicit hard pre-check belongs on C1/C3. |
| F-007 | Observation | CB-text feasibility screen | The screen is double-contaminated — look-ahead labels (90-day realized fed-funds path) AND LLM pretraining recall (model cutoff post-dates the statements). This strengthens, not weakens, the MLR's own conclusion: the dictionary/keyword baseline is LOAD-BEARING, not optional. |

**PR confirmability-honesty verdict: adequate.** No over-claim detected. Each candidate honestly states whether its data class escapes or merely relocates the wall. PR notes this is the strongest property of the slate — the over-claim the reviewer expected ("new data class => wall escaped") is explicitly NOT made by any candidate.

---

## § CRO Position

**Size-reduced: 0.45 overall.** This is not a veto. The directions are worth scarce research bandwidth. Three of five risk axes argue for restraint; one (min-viable-notional on D-TREND-FUTURES) reclassifies the highest-allocated direction as research-only until proven otherwise.

**Per-direction allocations:**

| Direction | CRO Allocation | Key Guardrails |
|-----------|---------------|----------------|
| D-TREND-FUTURES | 0.55 | RESEARCH-ONLY until min-viable-notional reconciled with capital base. 6E = 125,000 EUR fixed notional; smallest tradeable unit = 1 contract. M6E micro-futures availability/liquidity unverified. Pre-register the ENTIRE 40+-contract universe before any backtest. Treat as ONE correlated program — do NOT count 40 contracts as 40 independent confirmations. Data spend ($250-500/yr) is a SEPARATE reversible Board step. |
| D-CIP-SWAP-BASIS | 0.50 | $0 / FREE-DATA feasibility test FIRST. Edge concentrated in ~3 stress episodes; effective-N must count episodes, not calendar days. Probable dataset-wall RELOCATION, not escape — flag explicitly. |
| D-CBTEXT | 0.25 | Tests CLASSIFICATION, not EDGE at feasibility stage. ~8 events/yr hard ceiling. Pre-register host sleeve and overlay jointly. Cap bandwidth — earns a probe, not a program. |

**Blowup analogs (CRO, verbatim):**
- *(1) Managed-futures / trend-following 2009-2018 'long winter':* a real, decades-validated trend program delivered a multi-year drawdown precisely because its 40+ markets were ONE correlated bet that all reversed together — the concentration risk flagged here, realized.
- *(2) LTCM-style convergence/basis trades:* CIP-deviation/basis edges are convergence trades whose worst losses cluster in the same funding-stress episodes that generate the edge — the ~3-episode concentration means tail and signal share a regime, the classic convergence-trade blowup geometry.

**Decisive asymmetry (CRO's governing principle for this cycle):**
Data acquisition is $0-500/yr and REVERSIBLE. A counted trial is an IRREVERSIBLE honest-N decrement against a budget of 30 with 4 families already spent to NO-SPEND. **Run the free probes first. Reserve any data spend as a separate reversible Board step. Gate every honest-N decrement behind a pre-registered effective-N test.** Overall 0.45: commit real bandwidth, spend essentially no honest-N this cycle.

**CRO knowledge gaps (Board inputs, not skill gaps):**
- Deployable capital base figure — needed to compute whether one futures contract (6E = 125,000 EUR) is risk-acceptable at the firm's paper base. Until provided, D-TREND-FUTURES is research-only.
- Micro-futures (M6E etc.) availability and liquidity — determines whether D-TREND-FUTURES becomes deployable or remains a study.
- Per-episode return distributions for CIP-basis and CB-text — needed to convert nominal horizons into honest effective-N.

---

## § Signatures

| Role | Verdict | Condition |
|------|---------|-----------|
| Academic-Factor Lens Generator | approve | 7 directions produced, divergent, with OOS discipline and self-downgraded grades where warranted |
| Practitioner-Microstructure Lens Generator | approve | 7 directions produced; COT confirmability ~6yr self-flagged; P5/P7 self-culled in honest-notes |
| Contrarian-Outsider Lens Generator | approve | 7 directions produced; harness-transplant reframe highest-conviction; C7 routed to strategy |
| Null-Hypothesis Tester (NHT) | survives (concurs with shortlist; DISSENTS on 3 structural points — see § Dissent, verbatim) | Non-blocking |
| Quant Researcher (QR) | approve (3 structured candidates C1/C2/C3 with four-field records, falsifiable hypotheses, machine-checkable kill-numbers) | No pre-registration authored; honest-N unchanged |
| ML Researcher (MLR) | approve (narrowly; CB-text the one ML keeper, de-hyped; ML-on-price + HFT all cut) | Dictionary baseline mandatory at feasibility |
| Head of Quant Research (HoQR) | approve (ranked shortlist: T1 trend-on-futures primary; T6 CB-text $0 parallel; T7 CIP rank 3; T5 commodity/rates as documented fallback if T1 capital-scale fails) | No data spend, no pre-registration, no counted trial this cycle; if T1 + T6 kill → remain observe-only |
| Chief Risk Officer (CRO) | size-reduced (0.45) | D-TREND-FUTURES RESEARCH-ONLY until min-viable-notional confirmed; free probes first; data spend = separate Board step |
| Principal Reviewer (PR) | approve-with-conditions | 0 blocking-for-shortlist; F-001 (major, C3 rho CI gate) + F-008 (selection-surface into effective-N at advance) binding-for-future-pre-registration |
| PM | implement (consensus synthesized; NHT dissent verbatim-preserved; trial counter confirmed unchanged; no technical calls made) | — |

---

## § Knowledge Gaps

| Gap | Classification | Owner |
|-----|---------------|-------|
| Installable skill gap: high-frequency-trading domain skill was absent from the harness | **N = 0 installable gaps** — the HFT direction was CUT on structural grounds (latency 3-5 orders off; co-lo out of reach; true L2 $50k+/yr and still a proxy). The absence of an HFT skill did not impair the review; the evidence was sufficient to close the door. No new skill installation needed this cycle. | — |
| Deployable capital base figure (is one 6E contract = 125,000 EUR risk-acceptable?) | **Board input, not a skill gap.** The CRO cannot compute this without the capital base; it is not resolvable by installing a skill. | Board / CEO |
| Micro-futures availability/liquidity (M6E, M6B, etc.) | **Board / CEO data-gathering step.** Verify with broker (Saxo Bank) before D-TREND-FUTURES advances from research-only to deployable. | Board / CEO |
| Effective independent-bet count for a 40+-contract trend program (quantifying the breadth that would shorten the confirmability horizon) | Research-resolvable; ROUTE to Quant Developer. Free analytical step using published cross-asset correlation tables (AMP-2013, Hurst-2017). | Quant Developer |

---

## § Open Items Requiring Board Acknowledgment

1. **Green-light for $0 feasibility probes (the primary ask):** Authorize the following single-shot pre-committed cheap tests — all $0, all non-counting, all dispositive:
   - **(a) Trend-on-futures kill test:** Read MOP-2012 FX-futures sleeve OOS SR + Hurst-2017 post-2000 commodity-trend SR; compute CME RT cost drag from public fee schedules; check min-viable-notional vs capital base. ~1hr desk arithmetic. KILL or advance to data-spend gate.
   - **(b) CIP/basis kill test:** Download BIS quarterly EURUSD CCS basis (free) + FRED reconstruction; Spearman rho vs subsequent quarterly spot, with CI at honest effective-N. ~1hr. KILL or advance to Refinitiv daily-data gate (~$1,200/yr).
   - **(c) CB-text classifier feasibility:** Auto-label ~120 FOMC statements; zero-shot LLM + dictionary baseline alongside; 3-class Wilson CI. Half-day, ~$0. KILL or advance to overlay pre-registration.
   - All three run as SINGLE-SHOT pre-committed kills with pre-stated thresholds. ZERO honest-N risk. If all three kill → remain observe-only, report to Board.

2. **Deployability / capital-base question (required before D-TREND-FUTURES leaves research-only status):** The CRO has flagged that one 6E CME futures contract = 125,000 EUR fixed notional with no fractional sizing. The Board must provide the deployable capital base figure and confirm whether micro-futures (M6E ~12,500 EUR) are available + liquid via Saxo Bank. Until confirmed, D-TREND-FUTURES is a research program, not a deployable strategy.

3. **Defer any data-spend as a separate Board-authorized step:** If the trend-on-futures kill test passes, the question of acquiring ~$250-500/yr CME continuous futures data (Norgate/Nasdaq-DataLink) is a SEPARATE Board authorization step — cheap, reversible, but not bundled into this consensus.

4. **Defer any pre-registration as a separate Board-authorized step:** No direction in this shortlist is pre-registered. Pre-registration requires: (a) full universe and signal family frozen before any backtest; (b) effective-N deflation accounting for the 21-direction generation surface (F-008 condition); (c) NHT sign-off.

5. **Observe-only posture remains the default:** If the $0 cheap tests kill all three shortlisted directions, the honest outcome is to remain on observe-only and report that to the Board. The shortlist is an input to a future Board decision; it is not itself a commitment.

---

*Consensus is append-only. Dissents are preserved verbatim. No technical calls were made by the PM.*
