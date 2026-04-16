# Brainstorm: Auto-Research Methodology for a Self-Improving Forex Trading System

**Date:** 2026-04-03
**Method:** 5-thinker multi-perspective brainstorm with research, diverge, collide, and devil's advocate phases
**Thinkers:** Systems Thinker, Futurist, Contrarian, Outsider, Data Person
**Total ideas generated:** 79 (54 diverge + 25 collision)

---

## The Big Reframe

All 5 thinkers independently arrived at the same fundamental reframe, and the Devil's Advocate confirmed it with data:

**The question is not "How do we discover better strategies?"**
**The question is "Does exploitable alpha even exist in our target market, and can we detect it?"**

The current system shows 0/9 strategy-pair combinations with positive edge. The Devil's Advocate pointed out: no amount of methodology fixes an alpha failure. Before building research infrastructure, you must answer the gating question — compute the theoretical ceiling, test at finer time resolution, and test fundamentally different strategy classes (carry, value).

The second reframe: if alpha does exist, the system's primary job is **not generating ideas** — it's **making it impossible to fool yourself**. Build the bullshit detector first, the idea generator second.

---

## Top Ideas (Ranked by Convergence + Surprise + Resilience)

### 1. TAS Ceiling / Perfect Foresight Analysis — Surprise: Med | Resilience: HIGH

- **What:** Compute the theoretical maximum extractable alpha per pair/timeframe using perfect-foresight backtesting with realistic costs. This answers "is there anything here worth finding?"
- **Why it matters:** Without this, you don't know if Sharpe 0.5 is 90% of what's achievable or 10%. This one computation determines whether the entire auto-research project is viable.
- **Key insight:** The speedrunning community's genius — know the theoretical limit before attempting optimization. Decompose the ceiling by strategy class (trend/mean-reversion/carry) to reveal WHERE alpha hides.
- **Origin:** 4 thinkers independently (Futurist, Contrarian, Outsider, Data Person + Systems Thinker leaderboard)
- **Wild version:** Route decomposition — break theoretical ceiling into frequency bands and regime windows. Build a "research priority map" showing exactly where uncaptured alpha remains.
- **Devil's advocate says:** This should be done FIRST, before anything else. If the ceiling on daily bars is below Sharpe ~1.0, shift to intraday or rethink the project. A one-day exercise, not a month-long build.
- **Assumptions to verify:** Cost model accuracy (fixed constants vs real execution), daily close as executable price

### 2. Trial Registry + Deflated Sharpe Ratio — Surprise: Low | Resilience: VERY HIGH

- **What:** Log every single strategy configuration tested with a monotonic counter. Use the count to compute DSR — the acceptance threshold rises automatically as you test more.
- **Why it matters:** Without this, automated research is an overfitting factory. The trial count N is the most important number in the system — more important than any Sharpe ratio.
- **Key insight:** Deleting negative results is mathematically equivalent to inflating your Sharpe. The failures are the denominator.
- **Origin:** Data Person (primary), Systems Thinker (DSR as acceptance)
- **Wild version:** PBO Thermometer — continuous monitoring with trip-wires at 0.25/0.35/0.50 that trigger progressive interventions.
- **Devil's advocate says:** High resilience but needs a concrete schema. Current `BacktestResult` lacks trial ID and parameter hash. Define: strategy class, parameter hash, pair, timeframe, date range, IS metrics, OOS metrics, trial ID. Use SQLite, not a framework.
- **Assumptions to verify:** Discipline to log exploratory/informal tests, not just formal runs

### 3. Cost-First Decomposition — Surprise: High | Resilience: HIGH

- **What:** Decompose every strategy's returns into beta (market), alpha (signal timing), gamma (costs). Treat cost reduction as a research track equal to alpha discovery. Map all costs precisely FIRST, establish minimum signal thresholds, only research above threshold.
- **Why it matters:** Current round-trip costs are 2.0-2.9 pips. If a strategy captures 3-5 pips gross, costs consume 40-60%. A 20% cost improvement is equivalent to 20% more alpha — but cost improvement is guaranteed and non-decaying.
- **Key insight:** Everyone competes on alpha discovery. Almost nobody competes on cost reduction for retail systems. The edge you're looking for may be smaller than your cost estimation error.
- **Origin:** Contrarian (primary), Data Person (alpha/beta/gamma decomposition)
- **Wild version:** Build cost cartography — measure Saxo Bank actual spreads by time-of-day, test limit vs market orders, model slippage as a distribution not a constant. Execution alpha through optimal timing.
- **Devil's advocate says:** At retail volumes, cost structure is largely fixed. But even 0.3 pips saved is meaningful. More importantly, replacing fixed-constant cost model with empirical data makes ALL other analysis trustworthy.
- **Assumptions to verify:** Actual costs on Saxo Bank vs model assumptions

### 4. Staged Validation Pipeline (Pharma Model) — Surprise: Low | Resilience: HIGH

- **What:** Phase 0 (MDE pre-screen, kills 60-70%) → Phase 1 (null distribution, beats 99th percentile random) → Phase 2 (walk-forward with PBO < 0.10, anti-fragile gauntlet) → Phase 3 (paper trading on Saxo) → Phase 4 (live micro-size with Andon cord auto-halt).
- **Why it matters:** Most candidates should die early and cheaply. Each stage has a different falsification type (insufficient data, indistinguishable from random, overfit, fragile to perturbation, doesn't work live).
- **Key insight:** Gate criteria are functions of system history, not fixed thresholds. The more you search, the harder it gets to pass. This is the only honest way to do automated research.
- **Origin:** 5/5 thinkers converged. Data Person provided the quantitative gate criteria.
- **Wild version:** Phase -1 — analytical cost/trade-frequency check kills entire strategy families before any backtest (0.001 seconds per check).
- **Devil's advocate says:** Correct in theory but premature as code. Currently N=3 strategies, all dead. Define as a checklist now, implement as code when you have candidates. Don't build filtration infrastructure for a stream producing zero candidates.
- **Assumptions to verify:** Having enough candidates to justify pipeline engineering

### 5. Strategy Disagreement as Regime Sensor — Surprise: HIGH | Resilience: MED

- **What:** Run all strategies (including retired ones) as shadow signals. The NxN agreement/disagreement matrix IS the regime embedding — no separate classifier needed. Maximum disagreement = maximum uncertainty = go flat.
- **Why it matters:** Eliminates the regime detection module entirely. Regime detection emerges from the strategy ensemble. No additional assumptions, parameters, or overfitting surface.
- **Key insight:** A mean-reversion strategy that loses money in trends is a perfect trend detector. Failing strategies are still valuable as sensors. The pattern of activation across strategies encodes richer information than any individual signal.
- **Origin:** Outsider (primary), extended by Futurist and Systems Thinker in collision
- **Wild version:** Build a "market state embedding" — low-dimensional vector from strategy activation patterns. Cluster historical states, discover regime structure empirically, predict transitions by trajectory.
- **Devil's advocate says:** With 3 strategies that all lose money, disagreement is noise between noise generators. This becomes powerful once you have 5-10 strategies with demonstrated edge in different conditions. An idea to revisit later, not build now.
- **Assumptions to verify:** Strategies are individually meaningful in at least some regimes

### 6. Negative Space / Missed Alpha Tracker — Surprise: High | Resilience: MED

- **What:** Instead of "what patterns can we capture?", measure the profitable moves we MISS. Gap between TAS ceiling and captured returns, decomposed by frequency band, regime, and strategy class = quantified research roadmap.
- **Why it matters:** Tells you exactly what KIND of strategy to look for and WHERE. Turns open-ended exploration into targeted gap-closure.
- **Key insight:** A system at 70% of theoretical max needs better optimization. A system at 95% of max needs new categories of alpha. This changes research allocation.
- **Origin:** Contrarian (primary), extended by Data Person (spectral decomposition)
- **Wild version:** Auto-generate research priorities: "AUD/JPY has 70% uncaptured alpha concentrated in volatility regime transitions — research here next."
- **Devil's advocate says:** Requires accurate TAS ceiling first. Decomposition by frequency band and regime requires more data than currently available. Build incrementally.
- **Assumptions to verify:** TAS ceiling computation is accurate

### 7. Failure Museum with Bayesian Priors — Surprise: Med | Resilience: MED

- **What:** Structured database of every tested strategy with failure category (cost-dominated, regime-specific, overfit, correlated with existing). New hypotheses checked against failure clusters — "Warning: 8/10 momentum strategies on GBP failed due to cost dominance." System's prior for new hypotheses updates from history.
- **Why it matters:** Prevents re-testing equivalent dead-ends. Over time, the system gets better at generating hypotheses because it uses failure history as informative priors. This is the "self-improving" part applied to research itself.
- **Key insight:** Drug discovery's most valuable asset is its failed compounds database, not its approved drugs. Failed strategies contain more information than successful ones because there are far more of them.
- **Origin:** 4/5 thinkers converged (Futurist, Contrarian, Outsider, Data Person). Collision extended to Bayesian priors and causal resurrection.
- **Devil's advocate says:** With 3 strategies, the museum has one exhibit. Value compounds only after 50+ tested strategies. Start the logging now (it's free), build the query system later.
- **Assumptions to verify:** Failures are causally diverse and analyzable

### 8. Alpha Decay Curves as Regime Detector — Surprise: HIGH | Resilience: MED

- **What:** Fit exponential decay to each strategy's rolling OOS performance. Track the decay constant λ as a time series. Abrupt changes in λ = regime transitions. Different strategies' λ curves collectively map regime structure.
- **Why it matters:** Solves regime detection AND strategy lifecycle management with zero additional models. Falls out of performance monitoring you should do anyway.
- **Key insight:** Instead of "detect regime, then select strategy," observe strategy decay rates and the regime reveals itself. No HMM, no extra parameters.
- **Origin:** Data Person (primary), extended by Outsider (adversarial decay clock) and Futurist (alpha decay reactor)
- **Wild version:** Dead strategies' terminal decay parameters become fossils. Cluster analysis of death-λ values reveals categories of regime transitions.
- **Devil's advocate says:** Requires strategies with initial positive performance to measure decay from. Currently, all strategies start negative.
- **Assumptions to verify:** Sufficient walk-forward windows to fit meaningful decay curves

---

## Emerging Themes

1. **Epistemic Infrastructure First** — Build the ability to know what's true before building the ability to generate ideas. Trial registry, DSR, TAS ceiling, null distributions.
2. **Destruction Over Creation** — Invest 95% in validation, 5% in generation. The bottleneck is not ideas but knowing which ideas are real.
3. **Cost Is the Hidden Alpha** — At retail scale, cost optimization has higher expected ROI than alpha discovery.
4. **Death Is Data** — Failed strategies contain the richest information. Log everything, mine failures.
5. **Regimes Emerge, They Aren't Detected** — Use strategy behavior as implicit regime sensors rather than building explicit classifiers.
6. **Know When to Stop** — The system's most valuable output might be "there is nothing here, do not trade."

---

## Productive Tensions

| Tension | Position A | Position B | Resolution |
|---------|-----------|-----------|------------|
| **Build infrastructure vs. test alpha first** | Systems Thinker: build pipeline, then populate | Devil's Advocate: compute TAS ceiling first, infrastructure is premature | **DA wins**: answer the gating question before building anything |
| **Automate generation vs. human hypotheses** | Futurist/Outsider: LLM agents, GP evolution | Contrarian + 4/5 cross-exams: generation is not the bottleneck | **Evolve hypotheses, not code**: LLMs generate natural-language hypotheses; humans implement; pipeline validates |
| **Daily bars vs. intraday** | Current system: daily only | DA: most retail alpha exists intraday | **Test both**: TAS ceiling at daily AND 4H reveals which is viable |
| **Full automation vs. human-in-loop** | Multiple thinkers: autonomous overnight agent | DA: single developer can't build all this | **Augmented human**: system proposes, human decides. Research journal builds developer expertise alongside system capability |

---

## Collision Sparks (Best Combination Ideas)

### Adversarial Sufficiency Gate (Futurist collision)
Unified pre-flight: MDE check → destruction test → DSR deflation. Three cheap gates that catch different failure modes. Combining Data Person's stats + Contrarian's destruction + Systems Thinker's deflation.

### Alpha Decay Reactor (Futurist collision)
Strategy death is not loss, it's information about regime shift. Decay signatures become seed hypotheses for next generation. Combining Systems Thinker's lifecycle + Contrarian's expiration + Data Person's curves.

### Cost-First Alpha Decomposition Loop (Outsider collision)
Map all costs → establish min signal threshold → only research above threshold → treat cost reduction as equal research track. Combining Contrarian's cost focus + Data Person's alpha/beta/gamma.

### Research Journal as Bayesian Prior (Data Person collision)
Trial history updates priors for new hypotheses. 3/200 passing = 1.5% prior for new ideas. Similar-to-failed hypotheses get lower priors. System gets better at generating over time.

### Ignorance-Directed Research Queue (Outsider collision)
Research ordered by maximum expected information gain, not expected return. Reduces maximum ignorance about the opportunity space. Prevents premature convergence on early winners.

---

## Devil's Advocate Findings

### Verdict: NEEDS WORK

Strong ideas but dangerous gap between proposed sophistication and current reality.

### Key Challenges

1. **The Barren Field Problem (HIGH probability):** Daily forex on 3 majors with retail costs may simply not contain exploitable alpha at detectable levels. All infrastructure wasted. **Mitigation:** Compute TAS ceiling first. One-day exercise.

2. **Complexity Overwhelms Single Developer (HIGH probability):** 79 ideas, dozens of proposed systems. A single developer building all of this will either build shallow versions that don't work or spend 6+ months on infrastructure and never run a real experiment. **Mitigation:** Sequence ruthlessly. First research cycle needs only: TAS ceiling, trial registry (SQLite table), parameter sweep harness.

3. **Meta-Overfitting (MEDIUM probability):** Methodology designed around daily-bar failure modes may not transfer to intraday. **Mitigation:** Parameterize methodology by timeframe.

### Assumptions Inventory

| # | Assumption | Verified? | Risk If Wrong |
|---|---|---|---|
| 1 | Exploitable alpha exists in daily forex for major pairs after retail costs | **NO** — 0/9 pass | Entire project misallocated |
| 2 | Current cost model is accurate | **NO** — fixed constants | All edge calculations unreliable |
| 3 | Daily bar resolution sufficient for alpha detection | **NO** — never tested sub-daily | May be mining at wrong timescale |
| 4 | 3 pairs provide sufficient diversification | **Questionable** | Sample size fundamentally insufficient |
| 5 | Walk-forward adequately controls overfitting | **Partially** — no CPCV/PBO | WF can still overfit |
| 6 | ~10 years daily data sufficient for validation | **Marginal** — 2500 bars | MDE may require more data |
| 7 | Indicator transforms contain info beyond price | **Dubious** | More indicators ≠ more information |
| 8 | Single developer can build this | **Unverified** | Scope creep → abandonment |

### Alternative Paths Not Explored

1. **Sub-daily resolution (4H/1H)** — Most retail forex alpha exists intraday. More bars = more statistical power. Session-based microstructure effects.
2. **Cross-asset signals** — Bond yields, equity indices, VIX as forex inputs. No new methodology needed.
3. **Execution alpha** — Does execution timing (London open vs NY close) affect fill quality?
4. **Carry trade baseline** — Config shows positive USDJPY swap. Never tested.
5. **Systematic factor exposure** — Should this be an auto-research system at all, or a systematic factor execution system?

---

## Blind Spots

1. **Sub-daily resolution** — The biggest missing piece. Most retail forex alpha exists at 4H/1H.
2. **Cross-asset signals** — Bond yields, equity indices, VIX as forex inputs. Zero methodology change needed.
3. **Carry trade baseline** — Simplest forex strategy, never tested.
4. **Execution reality** — Gap between backtest fills and live execution. Slippage is a constant, not a distribution.
5. **Data quality** — 3 parquet files, ~2500 bars each. Is this enough? Is it clean?
6. **Strategy correlation** — If all strategies are trend-following variants, you have one bet, not three.

---

## What To Actually Do

### Priority Matrix

```
              High Impact
                  |
   EXPLORE        |        DO FIRST
   Strategies-    |    1. TAS ceiling (daily + 4H)
   as-sensors,    |    2. Carry trade baseline
   decay-as-      |    3. Trial registry (SQLite)
   regime,        |    4. Measure real Saxo costs
   causal         |    5. Alpha/beta/gamma decomp
   discovery      |
   ---------------+------------------
                  |
   PARK           |        QUICK WIN
   GP evolution,  |    - Null distribution for
   foundation     |      each strategy class
   model,         |    - MDE pre-screen checklist
   overnight      |    - Test 4H bars on existing
   agent          |      strategies
                  |
             Low Impact

   Low Novelty <---------> High Novelty
```

### Recommended Sequence

1. **DO FIRST** — TAS ceiling, carry baseline, real cost measurement, trial registry. Answers: "is there anything here?"
2. **QUICK WIN** — Null distributions, MDE checklist, 4H data. Expands search space if ceiling is promising.
3. **EXPLORE** — Disagreement-as-regime, decay curves, failure museum. Builds compound intelligence over time.
4. **PARK** — GP evolution, overnight agent, foundation model. Premature until validated alpha exists.

---

## Convergence Summary

| Concept | Thinkers | Verdict |
|---------|----------|---------|
| Staged validation pipeline | 5/5 | **STRONG SIGNAL** — the architecture |
| Adversarial destruction testing | 5/5 | **STRONG SIGNAL** — the test methodology |
| Failure as primary knowledge | 4/5 | **STRONG SIGNAL** — the data asset |
| Theoretical ceiling / TAS | 4/5 | **STRONG SIGNAL** — the gating question |
| Statistical rigor (DSR/PBO) | 4/5 | **STRONG SIGNAL** — the foundation |
| Regime awareness | 5/5 | **SIGNAL** — but implementation varies |
| Cost optimization | 2/5 | **UNDERAPPRECIATED** — highest practical ROI |
| GP/LLM evolution | 3/5 proposed, 4/5 criticized | **NOISE** — premature for Phase 0 |

---

## Key References from Research Phase

### Statistical Frameworks
- Bailey & Lopez de Prado — Deflated Sharpe Ratio (2014): corrects for selection bias and non-normality
- Bailey, Borwein, Lopez de Prado & Zhu — Probability of Backtest Overfitting (2015): CSCV-based PBO estimation
- Lopez de Prado — Combinatorial Purged Cross-Validation (2017): handles autocorrelation in financial CV
- Lopez de Prado — Meta-Labeling (2018): separates direction from sizing decisions

### AI/ML for Trading
- Chain-of-Alpha, AlphaAgent, AlphaLogics, QuantaAlpha — LLM-driven alpha mining frameworks (2025-2026)
- Kronos, FinCast — Financial time series foundation models
- AlphaEvolve (DeepMind, 2025) — LLM-guided evolutionary coding agent
- AI Scientist v2 (Sakana, 2025) — Automated research pipeline with BFTS

### Systems & Methodology
- Donella Meadows — Leverage Points: Places to Intervene in a System
- Drug discovery pipeline methodology (Phase 0-IV)
- Adaptive immune system computational parallels (clonal selection, affinity maturation)
- Competitive speedrunning methodology (TAS ceiling, route optimization)

### Market Structure
- Alpha decay: ~12 months average, 5-10% annual degradation
- 94% of active fund managers underperform benchmark over 20 years
- 78% of published trading strategies fail out-of-sample
- Market regime detection: $1.8B industry, 23.8% CAGR

---

## Raw Ideas by Thinker

### Systems Thinker (12 diverge + 5 collision = 17)

**Diverge:**
1. Alpha Stock-and-Flow Model — design for decay, not discovery
2. Immune System Architecture — massive diversity + clonal selection + affinity maturation
3. Deflated Discovery Rate — DSR/PBO as primary acceptance criteria
4. Regime Ecosystem — strategies as species in competing niches
5. Speedrunning Leaderboard — competitive benchmarking with theoretical limits
6. Information Flow Audit — prioritize orthogonal data sources
7. Delay Structure Map — temporal delays; accidental delays = edge
8. Anti-Correlation Research Hypothesis Portfolio
9. Minimum Viable Live Signal — close feedback loop immediately
10. GP Strategy Evolution — strategies as evolvable ASTs
11. Observability Lattice — meta-performance tracking
12. Drug Discovery Pipeline — staged Phase 0-4 validation

**Collision:**
13. Alpha Lifecycle Engine — strategies with estimated half-lives
14. Falsification-First Research Protocol — 4-stage destruction
15. Disagreement-as-Alpha Meta-Strategy — NxN tensor
16. Research Efficiency Manifold — 4D research priority space
17. Causal Immune System — causal interventions in adversarial testing

**Cross-exam target:** Futurist's Foundation Model (data problem, meta-overfitting)

### Futurist (10 diverge + 5 collision = 15)

**Diverge:**
1. Strategy Meta-Language/DSL — LLM evolves grammar
2. Adversarial Immune System — traders vs adversaries co-evolution
3. Regime as First-Class Type — RegimeSpec type checking
4. Overnight Research Agent — Claude Code auto mode
5. Delete All Strategies — discover from scratch
6. Strategy Graveyard — structured failure DB
7. Foundation Model on YOUR Backtest History
8. Speedrunner's TAS Ceiling
9. Causal Strategy Discovery — do-calculus
10. Inverted System — risk manager first

**Collision:**
11. Alpha Decay Reactor — decay as fuel
12. Adversarial Sufficiency Gate — unified pre-flight
13. Strategy Disagreement as Regime Sensor
14. Research Fossil Record with Causal Autopsy
15. Overnight Causal Discovery Agent with Cost-First Objective

**Cross-exam target:** AlphaEvolve/GP (LLM prior = everyone's prior, attribution problem)

### Contrarian (10 diverge + 5 collision = 15)

**Diverge:**
1. Strategy Destruction Engine — 95% validation / 5% generation
2. Negative Space Strategy — measure what you MISS
3. Anti-Research Loop — mandatory expiration
4. Optimize for Maximum Ignorance — minimax regret
5. "Do Nothing" Benchmark — prove beats passive carry
6. Map Theoretical Limits — perfect-foresight gating
7. Failure Museum — negative knowledge graph
8. Regime-Aware Silence — maximize flat time
9. Adversarial Self-Play — worst-case simulator
10. Optimize Costs Not Returns — guaranteed edge

**Collision:**
11. Ignorance-Weighted Research Budget
12. Adversarial Graveyard — dead strategies as antibodies
13. Do-Nothing Ceiling — max of no-skill optimized strategy
14. Regime Silence as Research Signal — confusion index
15. Anti-Fragile Deletion Engine — ablation testing

**Cross-exam target:** GP/DSL evolution (adversarial landscape, expressiveness = overfitting)
**Reframe:** "Does alpha exist? Should we bother?" — optimize for truth, not activity

### Outsider (11 diverge + 5 collision = 16)

**Diverge:**
1. Pharma Pipeline — explicit go/no-go stages
2. Immune System Diversity — mutate losers, clone winners
3. Speedrun TAS Ceiling — route efficiency %
4. AlphaEvolve Loop — LLM semantic mutations
5. Andon Cord — SPC auto-halt on degradation
6. Adversarial Red Team — failures become test cases
7. Fossil Record — death conditions reveal regime transitions
8. Elo Tournament — round-robin rolling windows
9. External Signal Ingestion — macro data as modulators
10. Diff-Based Research Journal — git diff reveals alpha essentials
11. Strategies as Sensors — disagreement = signal; market embedding

**Collision:**
12. Adversarial Decay Clock — survival probability curves
13. Ignorance-Directed Research Queue — max info gain per compute
14. Fossil Record with Causal Resurrection
15. Elo Tournament with Regime Brackets
16. Cost-First Alpha Decomposition Loop

**Cross-exam target:** GP/AlphaEvolve (overfitting scales with expressiveness)

### Data Person (11 diverge + 5 collision = 16)

**Diverge:**
1. Trial Registry — log all; DSR needs N
2. Null Strategy Distribution — random baseline per class
3. Minimum Detectable Effect Budget
4. Combinatorial Strategy Autopsy — failure decomposition
5. Effective Independent Bets — nominal ≠ actual sample size
6. Speedrun Theoretical Limits — per-class ceiling
7. Overfitting Thermometer — PBO trip-wires
8. Effect Size Decomposition — alpha/beta/gamma
9. Anti-Fragile Validation Gauntlet
10. Information Decay Curves — predict retirement
11. Data Sufficiency Manifold — what's testable

**Collision:**
12. Deflated Pharma Pipeline with MDE Gates
13. Alpha Decay Curves as Regime Transition Detectors
14. Information-Theoretic Research Prioritization
15. Adversarial Self-Play with Null Distribution Calibration
16. Research Journal as Bayesian Prior

**Cross-exam target:** GP/AlphaEvolve (combinatorial deflation, fitness function IS the problem)
**Reframe:** "Build a measurement system that makes it impossible to fool ourselves" — bullshit detector first
