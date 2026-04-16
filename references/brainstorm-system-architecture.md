# Brainstorm: Premium Real Trading System Architecture

Date: 2026-04-05
Thinkers: Systems Architect, Battle-Scarred Quant, Contrarian, ML Engineer, SRE/Infrastructure
Process: Full 5-phase (Frame → Research+Diverge → Collide → Devil's Advocate → Distill)
Ideas generated: 50 diverge + 17 collision = 67 total

---

## The Big Reframe

The Devil's Advocate and Contrarian converged on the same uncomfortable truth:

> **The group designed a production trading system when the research problem isn't solved.** 0/9 strategy-pair combos show no edge. The correct response is not "build better infrastructure to run strategies that don't work" -- it's "find a strategy that works using the simplest possible tools."

Infrastructure doesn't create alpha. Event sourcing doesn't create alpha. Kill switches don't create alpha. The brainstorm generated 50+ engineering answers to a research question.

Some infrastructure genuinely serves research (cost measurement, basic logging, statistical rigor). And if/when edge is found, the operational ideas become load-bearing. The distillation below respects both realities.

---

## Top Ideas (Ranked by Convergence + Surprise + Resilience)

### 1. Cost Empiricism -- Measure Before You Model
**Surprise: Med | Resilience: HIGH**

- **What:** Connect to Saxo SIM, record actual bid/ask spreads for 2 weeks across all sessions. Build spread distribution by (pair, hour, day, volatility). Current 0.5 pip fixed spread is wrong -- Saxo charges 0.9 pips for the account tier.
- **Why it matters:** Cost model error is likely larger than any alpha. Execution timing IS a strategy -- EURUSD spread is 0.6 pips during London-NY overlap and 2.5 pips at 3 AM.
- **Key insight:** The one piece of measurement infrastructure that directly serves alpha discovery, not just operational safety.
- **Origin:** Battle-Scarred Quant, reinforced by Collision "Reality-Calibrated Cost Surface" and "Cost-Is-Alpha Reversal"
- **Wild version:** The spread itself becomes a trading signal -- when spreads spike, liquidity providers are pulling back, which often precedes sharp moves.
- **Devil's advocate says:** "Necessary work regardless of strategy." Fails only if it becomes an end in itself rather than a 2-hour sanity check.
- **Assumptions to verify:** That Saxo SIM spreads represent live spreads. Check swap rates too.

### 2. Flat as Default / Continuous Sizing
**Surprise: Med | Resilience: HIGH**

- **What:** Default position is FLAT. Signals below conviction threshold map to zero. Add regime uncertainty filter, cost hurdle. 70% of time flat may be optimal.
- **Why it matters:** Current system is always in market. In FX, edge is often in NOT trading. Every trade pays 2.0-2.9 pips RT.
- **Key insight:** Don't implement as hard threshold (overfitting risk). Use continuous position sizing where signal strength maps to size. Kelly/fractional-Kelly gives flat-as-default without a threshold to overfit.
- **Origin:** Quant #9, ML #5 (abstention), Collision "Skinny Loop + Abstention Gate"
- **Devil's advocate says:** "Core insight correct. Fails only if implemented as hard threshold rather than continuous sizing."
- **Assumptions to verify:** That confidence can be meaningfully measured for rule-based strategies.

### 3. Capital Ratchet -- Trust-Building Sizing Protocol
**Surprise: High | Resilience: HIGH**

- **What:** Start at 0.1% risk per trade. Explicit pre-committed criteria for ratcheting up (N consecutive profitable months, Sharpe > X). Ratchet down fast on any anomaly. Criteria written before going live.
- **Why it matters:** Position sizing is not a mathematical optimization -- it's a trust problem. The ratchet externalizes trust-building into a protocol that can't be short-circuited by greed.
- **Key insight:** Collision improves this: continuous function with convex downside response (halve instantly on 1-sigma underperformance, require 3-sigma outperformance to double).
- **Origin:** Quant #6, Collision "Inverse Capital Ratchet"
- **Devil's advocate says:** "Simple, mechanically enforceable, aligns incentives."
- **Assumptions to verify:** Enough trades to measure performance meaningfully at each level.

### 4. Carry Trade as Starting Point + Canary
**Surprise: Med | Resilience: MEDIUM**

- **What:** Implement minimal carry strategy (long high-yield, short low-yield, rebalance monthly). Test it first. If profitable, becomes permanent canary -- every other strategy must beat carry net of costs.
- **Why it matters:** Carry is the one FX strategy with decades of academic evidence (Sharpe 0.89). The 0/9 failure tested technical indicators -- the strategy class with no academic support in FX. Haven't tested the one that does.
- **Key insight:** Before building carry, do 2-hour pre-check: download Saxo's current swap rates, compute annualized carry per pair net of spread costs. If no pair is positive after costs, save yourself.
- **Origin:** Contrarian #4, Collision "Canary Carry Gauntlet"
- **Devil's advocate says:** "Carry has known blow-up profile (picking up pennies in front of steamroller). Must validate swap rates first."
- **Assumptions to verify:** That Saxo retail swap rates support positive carry after costs.

### 5. Null Hypothesis Gate -- Statistical Rigor for Every Strategy
**Surprise: High | Resilience: HIGH**

- **What:** For every strategy, generate 1,000 random strategies with same trade frequency and holding period. If yours isn't top 1% (DSR-adjusted), it's noise. Collision version: run random strategies as shadow signals with adaptive per-window ranking.
- **Why it matters:** The most profitable trade you'll ever make is not deploying a strategy you've convinced yourself works through insufficient testing.
- **Key insight:** Not defeatism -- the only intellectually honest path. If something survives, you'll trust it with real money.
- **Origin:** Contrarian #6, Collision "Null Hypothesis Gate with Shadow Signals"
- **Devil's advocate says:** Risk is the gate becomes another layer to overfit. Keep it simple: fixed percentile threshold.
- **Assumptions to verify:** Random strategy generation preserves structural similarity to candidate.

### 6. Backtest Arson Test -- Sabotage to Measure Robustness
**Surprise: HIGH | Resilience: HIGH**

- **What:** Deliberately degrade strategy: randomize 10% of signals, add 2x cost multiplier, shift signals by extra bar, corrupt one indicator. If degraded versions perform similarly, original has no edge.
- **Why it matters:** Directly measures sensitivity to signal quality. If randomizing 10% of signals barely changes Sharpe, you have a cost-harvesting artifact, not alpha.
- **Key insight:** Faster and more informative than 3 months paper trading. The question: "how much sabotage can it absorb?"
- **Origin:** Collision (Contrarian)
- **Devil's advocate says:** Novel, cheap to implement, high information density.
- **Assumptions to verify:** That sabotage modes are representative of real-world degradation.

### 7. Graduated Autonomy Ladder
**Surprise: High | Resilience: MEDIUM**

- **What:** Single continuum: Manual (human trades, system logs) -> Suggest (system proposes, human approves) -> Semi-Auto (auto with gate on large trades) -> Supervised Auto (auto with daily review) -> Full Auto (alerts on anomalies only). Quantitative promotion criteria, instant demotion on safety violation.
- **Why it matters:** "Trade manually first" and "graduated kill switch" are the same idea at different lifecycle stages. Makes transition from research to live explicit and reversible.
- **Key insight:** Binary kill switch (RUN/FLAT) sufficient within each level. Autonomy levels handle lifecycle, kill switch handles emergencies. Simplify to 3 levels for solo use.
- **Origin:** Collision (Quant), synthesizing SRE #4, Architect Telemetry-First, Contrarian #1
- **Devil's advocate says:** Simplify to 3 levels (Manual, Supervised, Auto).
- **Assumptions to verify:** That promotion criteria can be defined objectively.

### 8. Skinny Live Loop
**Surprise: Med | Resilience: MEDIUM**

- **What:** Live loop does: receive price -> lookup pre-computed decision envelope -> execute. All heavy computation runs ahead of time on slower cadence. Default branch: abstain.
- **Why it matters:** Makes real-time path nearly impossible to break -- no pandas, no numpy, no indicator computation that could throw. Decision envelope expires if heavy computation hasn't run, forcing safe abstention.
- **Key insight:** Solves stale signal handling for free. Don't need sub-second computation for daily/4H strategies.
- **Origin:** Architect #7, Collision "Skinny Loop + Abstention Gate"
- **Devil's advocate says:** "Architecturally sound. Irrelevant until you go live." A blueprint, not a build target yet.
- **Assumptions to verify:** Pre-computed envelopes can capture full action space for all strategy types.

### 9. Execution State Machine -- Order Lifecycle as FSM
**Surprise: Low | Resilience: MEDIUM**

- **What:** Explicit FSM: SIGNAL -> ORDER_SUBMITTED -> ACKNOWLEDGED -> FILLED -> POSITION_OPEN -> EXIT_SIGNAL -> EXIT_SUBMITTED... Each state has timeout and failure transitions.
- **Why it matters:** Every 3 AM blowup from implicit state machine where assumed transitions don't hold. Saxo's 1/sec rate limit + 20-min token expiry create specific stuck states.
- **Origin:** Architect #6, Quant #8, SRE #10
- **Devil's advocate says:** "Critical for live trading, irrelevant for finding edge." Build when going live.
- **Assumptions to verify:** Saxo's actual order lifecycle matches modeled states.

### 10. Token Chain Fuel Gauge
**Surprise: High | Resilience: MEDIUM**

- **What:** "Time to auth death" metric. Yellow at 10 min, red at 5 min, auto-flatten at 2 min. Track refresh jitter. Cold-start recovery runbook tested monthly.
- **Why it matters:** If auth dies with open positions, cannot manage them programmatically. Maximum financial damage with minimum visibility.
- **Origin:** SRE #2
- **Devil's advocate says:** "Build it the week before going live." Simple to implement, critical when needed.
- **Assumptions to verify:** Saxo's token behavior matches docs under stress.

---

## Emerging Themes

| Theme | Ideas | Core Insight |
|-------|-------|-------------|
| **Alpha First, Infrastructure Second** | Contrarian #2/#5, DA reframe | 0/9 is a research problem. Don't engineer around it. |
| **Measure Reality, Don't Model It** | Quant #2/#5, Collision cost surface | Fixed-param cost models hide the truth. Measure empirically. |
| **The Default Is Do Nothing** | Quant #9, ML #5, Capital Ratchet | Flat is safe. Trading is a cost. Require proof before acting. |
| **Safety Through Simplicity** | DA binary kill switch, Skinny Loop | Complex safety systems become failure modes themselves. |
| **Continuous, Not Discrete** | Collision capital ratchet, sizing-as-conviction | Avoid hard thresholds -- they create overfitting opportunities. |
| **Reconcile Against Reality** | Architect #9, SRE #1/#10, Quant #5 | Broker is truth. Internal state is an optimistic cache. |
| **Ritualized Human Oversight** | Quant #3, SRE #6/#8, Collision dashboard | Solo operator needs structured, low-cognitive-load review. |

---

## Productive Tensions

1. **Build vs. Don't Build.** Contrarian: architecture is the enemy; 4 others produced sophisticated ideas. Resolution: build only what directly serves "does edge exist?" Defer the rest.

2. **Sophisticated Safety vs. Simple Binary.** SRE: 5-level degradation; DA: binary RUN/FLAT sufficient and testable. Resolution: start binary, add levels only when actual failure patterns demand it.

3. **Observation Mode vs. Micro-Trading.** Architect: weeks of telemetry-first shadow mode; Contrarian: skip to live. DA cross-examined: "observation mode tests the wrong thing." Resolution: micro-trade telemetry -- real 0.01 lot trades that test execution while risking ~$5/trade.

4. **Event Sourcing vs. Statelessness.** Architect + SRE: elaborate event stores; Contrarian collision: stateless daemon from Saxo + git. Resolution: structured trade log (80% value, 10% complexity), not full event sourcing.

5. **500-Line Ceiling vs. Measurement Infrastructure.** Two cross-examinations defended measurement code. Resolution: 500-line ceiling for signal generation, unlimited for measurement harness.

---

## Collision Sparks

| Spark | Lineage | Why Better Than Either Parent |
|-------|---------|-------------------------------|
| **Replay Tribunal** | Architect Event Journal + ML Prediction Log + SRE Shadow Ledger | Unified event store with counterfactual replay -- one system replaces three |
| **Canary Carry Gauntlet** | Contrarian Carry + ML Canary Model + Contrarian Null Hypothesis | Every strategy must beat carry AND its own randomized null distribution |
| **Graduated Autonomy Ladder** | Contrarian Manual First + SRE Kill Switch + Architect Telemetry | Full lifecycle from manual to auto as single continuum |
| **Null Hypothesis Gate** | Contrarian Null Hypothesis + ML Shadow Signals + Quant Flat Default | Real strategy must rank top 5% of random cohort per window |
| **Cost-Is-Alpha Reversal** | Quant Cost Empiricist + Architect Dual-Clock | Spread time series AS a trading signal, not just friction |
| **Backtest Arson Test** | ML Canary + Quant Reconciliation + Contrarian provocation | Sabotage strategy to measure signal sensitivity |
| **Skinny Loop + Abstention** | Architect Skinny Loop + ML Abstention + SRE Cognitive Load | Pre-computed decision envelope with abstention default |
| **Reality-Calibrated Cost Surface** | Quant Cost Empiricist + ML Hashable Feature Graph + SRE Shadow Ledger | Cost params as measured, versioned, hashable feature |
| **Adaptive Flat-Time Classifier** | Quant Flat Default + Architect Experiment Registry + Architect Telemetry | ML classifier for "is this bar worth trading?" -- trained on observation data |
| **Brutal Honesty Dashboard** | Quant Daily Review + SRE Cognitive Load + ML Prediction Log + Architect Registry | Single daily email with 3 numbers: match expectations? drifting? should you be in market? |

---

## Devil's Advocate Findings

### Resilience Ratings

| Idea | Rating | Reasoning |
|------|--------|-----------|
| Cost Empiricism | **HIGH** | Necessary regardless of strategy. Fails only if becomes an end in itself |
| Flat as Default | **HIGH** | Core insight correct. Use continuous sizing, not hard thresholds |
| Capital Ratchet | **HIGH** | Simple, enforceable, aligns incentives |
| Null Hypothesis Gate | **HIGH** | Intellectually honest, cheap to implement |
| Backtest Arson Test | **HIGH** | Novel, high information density, no significant challenges |
| Carry as Canary | **MEDIUM** | Must validate swap rates first. Blow-up profile known |
| Autonomy Ladder | **MEDIUM** | Sound principle. Simplify to 3 levels for solo use |
| Skinny Live Loop | **MEDIUM** | Good blueprint. Irrelevant until live |
| Execution FSM | **MEDIUM** | Critical for live, irrelevant for research |
| Token Fuel Gauge | **MEDIUM** | Simple, critical when needed |
| Event-Sourced Audit | **LOW** | High cost, zero alpha contribution, schema lock-in risk |
| Shadow Signals | **LOW** | Premature. Shadow signals from broken strategies are noise |
| Three-Layer Decision | **LOW** | Premature decomposition. Need working first layer |

### Top 3 Failure Scenarios

| # | Scenario | Probability | Mitigation |
|---|----------|-------------|------------|
| 1 | **Death by Infrastructure** -- 6+ months building beautiful systems with no profitable strategies | 60% | Time-box infrastructure to 2 weeks. 80% time on alpha research |
| 2 | **Overfitting the Alpha Search** -- too many filters create in-sample illusion | 25% | Null hypothesis gate, arson test, DSR adjustment |
| 3 | **Carry Blow-Up** -- small steady gains -> overconfidence -> risk-off wipeout | 10% | Capital ratchet, binary kill switch, margin call simulator |

### Alternative Paths Not Explored

1. **Alternative data** -- COT reports, central bank NLP, cross-asset signals, order flow. Group stayed in OHLCV technical analysis paradigm.
2. **Execution alpha** -- limit order strategies, spread capture, time-of-day optimization. Edge might be in HOW you trade, not WHAT.
3. **Multi-asset diversification** -- Saxo offers CFDs on indices, commodities, bonds. If FX has no edge, adjacent markets might.
4. **Ensemble of weak learners** -- Can 9 slightly-negative-edge strategies with negative correlation produce positive edge?
5. **Regime-first, strategy-second** -- Classify regime accurately, then use trivially simple matched strategy.
6. **Red team the backtest** -- Verify engine against published academic results before searching for more alpha.

### Collective Biases

1. **Builder bias** -- every thinker defaulted to "build something." Nobody said "read 50 academic papers."
2. **Survivorship bias in pattern-matching** -- patterns from successful systems (event sourcing from fintech, kill switches from HFT) applied to a solo project with zero alpha is cargo culting.
3. **Complexity bias** -- collision process rewarded elaboration over simplification.
4. **Technology-forward, not problem-forward** -- most ideas start with a pattern and work backward to the problem.

---

## Blind Spots

- **No voice from a successful solo FX trader** -- all archetypes were technologists
- **Academic literature under-leveraged** -- group relied on code analysis and web research, not academic papers on FX alpha
- **Psychology barely addressed** -- only Quant touched emotional reality of live trading
- **Regulatory/tax implications** -- zero discussion of tax treatment of FX gains

---

## 2x2 Matrix

```
              High Impact
                  |
   EXPLORE        |        DO FIRST
   Regime-first   |   1. Cost Empiricism
   Execution alpha|   4. Carry + swap check
   Ensemble of    |   5. Null Hypothesis Gate
   weak learners  |   6. Backtest Arson Test
   Alt data (COT) |   2. Flat/Continuous Sizing
                  |   3. Capital Ratchet
   ---------------+------------------
                  |
   PARK           |        QUICK WIN
   Event Store    |   Token Fuel Gauge
   Shadow Signals |   Structured trade log
   Three-Layer    |   Experiment Registry (SQLite)
   Genotype/Pheno |   Autonomy Ladder (define on
                  |   paper, don't build)
             Low Impact

  Low Novelty <----------> High Novelty
```

---

## Recommended Sequence

### Week 1-2: Validate the Premise
1. **2-hour swap rate check** -- is carry positive after Saxo costs?
2. **Cost empiricism** -- connect to SIM, record spreads for 1 week
3. **Red team backtest** -- run known academic strategy, verify results match published figures

### Week 3-4: Find Edge (Research, Not Engineering)
4. **Implement carry** (100 lines, one script)
5. **Backtest arson test** on carry + existing strategies
6. **Null hypothesis gate** -- are any results distinguishable from random?

### Month 2: If Edge Found, Prepare for Live
7. **Capital ratchet** -- define levels and criteria on paper
8. **Autonomy ladder** -- define 3 levels (Manual, Supervised, Auto)
9. **Micro-trade telemetry** -- 0.01 lots on Saxo live to measure reality tax
10. **Binary kill switch** -- single hard circuit breaker

### Month 3+: If Validated in Live Micro-Trading
11. Execution state machine
12. Token fuel gauge
13. Structured trade log (not full event sourcing)
14. Skinny live loop architecture

### Defer Until Multiple Strategies Proven
- Shadow signals
- Three-layer decision
- Full event sourcing
- Genotype/phenotype strategy abstraction

---

## Raw Ideas by Thinker

### Systems Architect (10 ideas)
1. Execution Journal -- event-sourced audit trail as primary data store
2. Sourdough Architecture -- genotype/phenotype strategy separation
3. Telemetry-First Pit Stop -- instrument every decision before trading
4. Dual-Clock Architecture -- wall time vs market time as explicit concept
5. Inverse Safety Architecture -- 6 invariants from reverse-engineering catastrophic failures
6. State Machine Broker -- order lifecycle as explicit FSM
7. Skinny Live Loop -- minimize real-time critical path
8. Configuration Gradient -- 4-tier parameter exposure
9. Reconciliation Loop -- Saxo as source of truth
10. Experiment Registry -- versioned reproducible backtests (SQLite)

### Battle-Scarred Quant (10 ideas)
1. Overnight Margin Call Simulator -- replay worst historical events through Saxo margin rules
2. Cost Empiricist -- measure actual Saxo spreads before modeling
3. Sourdough System -- mandatory daily 10-min human review ritual
4. Reverse Blowup Engineering -- work backwards from ruin
5. Paper Trading Reconciliation Engine -- quantify the "reality tax"
6. Anti-Fragile Capital Allocation Ratchet -- trust-building sizing protocol
7. Single-Pair Single-Strategy Proof -- go narrow and deep first
8. Execution State Machine with Explicit Failure Modes
9. Regime-Aware Flat Position as Default
10. Kill Switch Hierarchy -- pre-committed shutdown criteria

### Contrarian (10 ideas)
1. Stop Building, Trade Manually for 3 Months First
2. The 500-Line Ceiling -- find edge with minimal code
3. You Are Solving the Wrong Market -- FX worst for retail algo
4. The Carry Trade Is the Only Honest Starting Point
5. The Architecture IS the Enemy -- research needs notebooks, not frameworks
6. Bet Against Yourself -- Null Hypothesis Fund
7. The Saxo Bank API IS the Product -- sell infrastructure, not alpha
8. The One-Trade System -- 4 trades/year macro bets
9. Kill the Project, Invest in Index Funds
10. The Minimum Viable Bet -- $1,000 live in 2 weeks

### ML Engineer (10 ideas)
1. Prediction Column Contract -- generate_predictions() returns DataFrame with signal + metadata
2. Feature Computation as Hashable Transform Graph -- deterministic hashes for reproducibility
3. Shadow Signal Architecture -- all strategies run, only active ones trade
4. Point-in-Time Feature Snapshots -- no-lookahead extended to features
5. ML Models Should Refuse to Predict 70% of the Time -- null signal support
6. Walk-Forward Retraining Contract -- train_fn(symbol, train, test) -> Model
7. Drift Detection as First-Class Metric -- PSI per walk-forward window
8. Immutable Prediction Log -- every signal gets a receipt
9. Three-Layer Decision: What/When/How Much -- separate retraining frequencies
10. Canary Model -- simple frozen baseline that ML must beat

### SRE / Infrastructure (10 ideas)
1. Inverted Watchdog -- prove correctness, don't just detect failure
2. Token Chain Fuel Gauge -- auth as finite resource with fuel gauge
3. Shadow Ledger -- append-only event sourcing
4. Graduated Kill Switch -- 5-level autonomous degradation
5. Deployment as Trade -- canary releases for strategy updates
6. Sourdough Process -- Sunday automated health ritual
7. Chaos Budget -- monthly fault injection testing
8. Cognitive Load Budget -- max 3 ACT-NOW alerts/day
9. Pre-Flight Checklist -- executable startup validation
10. Position-Aware Process Management -- reconcile broker state on restart

### Collision Ideas (17)
1. Reality-Calibrated Cost Surface (Architect: Cost Empiricist + ML Hashable Graph + SRE Shadow Ledger)
2. Null Hypothesis Gate with Shadow Signals (Contrarian + ML + Quant)
3. Pre-Flight State Machine with Cognitive Load Budget (SRE + Quant + SRE)
4. Backtest-vs-Paper Reconciliation as Carry Validator (Quant + Contrarian + ML)
5. Replay Tribunal (Architect + ML + SRE -- unified event store)
6. Canary Carry Gauntlet (Contrarian + ML + Contrarian)
7. Graduated Autonomy Ladder (SRE + Architect + Contrarian)
8. Skinny Loop + Abstention Gate (Architect + ML + SRE)
9. Anti-Infrastructure Thesis (Contrarian challenge to Architect + SRE)
10. Backtest Arson Test (Contrarian sabotage framework)
11. Inverse Capital Ratchet (Quant + SRE -- continuous asymmetric function)
12. Cost-Is-Alpha Reversal (Quant + Architect -- spread as signal)
13. Brutal Honesty Dashboard (Quant + SRE + ML + Architect -- 3-number daily email)
14. Learned Execution Cost Model (ML: Cost Empiricist + Genotype/Phenotype + Null Hypothesis)
15. Regime-Aware Capital Ratchet (ML: Capital Ratchet + Margin Simulator + Shadow Ledger)
16. Adaptive Flat-Time Classifier (ML: Flat Default + Registry + Telemetry)
17. Synthetic Stress Test Generator (ML: Margin Simulator + Null Hypothesis + Chaos Budget)

### Cross-Examinations (4)
1. **Architect cross-examined Contrarian's "500-Line Ceiling"** -- conflates signal expression (can be 50 lines) with measurement infrastructure (needs thousands). Fix: 500-line ceiling for signal generation only.
2. **Quant cross-examined Contrarian's "500-Line Ceiling"** -- same conclusion. Fix: replace LOC ceiling with time ceiling (2 weeks of focused research).
3. **ML Engineer cross-examined Architect's "Genotype/Phenotype"** -- massively expands hypothesis space with insufficient data. Fix: manual structural changes with pre-registered hypotheses, not automated graph search.
4. **Contrarian cross-examined Architect's "Telemetry-First"** -- observation mode tests the wrong thing (never places orders). Fix: micro-trade telemetry with 0.01 lots instead.
