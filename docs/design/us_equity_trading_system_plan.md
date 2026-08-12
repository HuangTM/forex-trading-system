# US Equity Trading System — Project and Implementation Plan

```yaml
status: revised-proposed
created: 2026-08-11
revised: 2026-08-11
scope: new US-equity project
working_name: us-equity-trading-system
capital_authorization: none
remote_publication_authorization: none
paid_data_or_service_authorization: none
recommended_default: evaluate LEAN first; compare NautilusTrader before committing
```

> This is a project plan, not authorization to open an account, place an order, or
> deploy capital, purchase data or services, create a remote repository, or publish
> files. The existing forex repository remains the research and falsification
> source-of-record and is not bulk-copied or modified as part of stock-project setup.
> New stock work should live in a separate repository.

## 1. Executive decision

Create a separate `us-equity-trading-system` project, but do not start by writing a
backtester, order-management system, or broker integration from scratch.

The initial approach is:

1. Evaluate **QuantConnect LEAN** as the default US-equity kernel.
2. Evaluate **NautilusTrader** against the same test contract as the architectural and
   lower-latency alternative.
3. Borrow Freqtrade's operator-control patterns and Qlib/PyBroker's research-workflow
   patterns without combining their runtimes.
4. Build project-owned research governance, auditability, risk policy, telemetry, and
   deployment gates around the selected kernel.
5. Begin with daily/hourly, liquid US equities and ETFs. HFT is explicitly deferred.
6. Create the project locally first. Remote publication and any paid dependency each
   require a separate, exact-target authorization gate.

The system and the strategies have separate success criteria:

| Concern | The system must prove | A strategy must prove |
|---|---|---|
| Correctness | Deterministic inputs, correct accounting, corporate actions, order state | No lookahead, point-in-time features, reproducible signals |
| Safety | Fail-closed risk checks, reconciliation, kill switch, bounded exposure | Loss and capacity assumptions remain within pre-registered limits |
| Operations | Recovery, traceability, monitoring, actionable alerts | Signal health and live-vs-shadow drift are measurable |
| Economics | Realistic fees, spread, slippage, borrow, impact interfaces | Positive after-cost out-of-sample expectancy versus a benchmark |
| Extensibility | Stable domain contracts and replaceable adapters | New hypotheses do not require changes to execution infrastructure |

Profitability is not a platform feature. A stable platform can execute an unprofitable
strategy perfectly; therefore platform readiness must never be used as evidence of alpha.

## 2. Context and lessons carried forward

The forex Phase 0 closure answered its charter honestly: the tested retail FX hypothesis
class did not produce a confirmable, cost-surviving edge. That result is not a software
failure. It establishes several requirements for the stock project:

- Alpha first; infrastructure is built only to support a validated need or protect capital.
- A synthetic-data or in-sample result is never called validated.
- Every research attempt is registered, including negative results.
- Multiple testing, effective breadth, costs, and time-to-confirmability are estimated
  before a large search begins.
- Backtest, paper, and live differences are measured, not assumed away.
- A deployability label must be machine-enforced, not merely written in documentation.
- Research state and broker state must never silently diverge.

Equities require a new domain model. FX-specific concepts such as currency pairs, pips,
swap direction, JPY conversion, and Saxo order semantics must not leak into the new core.
US equities add exchange calendars, symbol changes, splits, dividends, delistings,
point-in-time universes, adjusted/raw prices, borrow availability, and market-session rules.

## 3. Goals and non-goals

### Goals

- Reproducible research on survivorship-aware, point-in-time US-equity data.
- One documented path from a pre-registered hypothesis to backtest, shadow, paper, and
  eventually live execution.
- The same strategy-intent and risk contracts across environments; environment-specific
  behavior is isolated behind data and execution adapters.
- Complete causal trace from data and signal to risk decision, order, fill, and position.
- Startup and continuous reconciliation of observed account effects against the broker.
- Monitoring that detects data, execution, risk, strategy, and infrastructure failures.
- An extension model for new data providers, brokers, strategies, and risk rules.
- An evidence gate that can stop the project before expensive live infrastructure is built.

### Non-goals for the first release

- High-frequency trading, market making, co-location, or latency arbitrage.
- Options, futures, crypto, or multi-asset margin accounting.
- A custom exchange simulator or custom broker protocol if the selected kernel provides one.
- Deep learning or reinforcement learning for direct directional prediction.
- Automatic hyperparameter search without a declared search space and trial accounting.
- Real-capital trading before all readiness gates are independently satisfied.
- A polished mobile application or multi-tenant commercial platform.

## 4. Design principles

1. **Flat and disabled are the safe defaults.** Recovery uncertainty disables new orders.
2. **Same intent, explicit reality models.** Strategy and risk code are shared, but fills,
   clocks, data delivery, and broker behavior remain explicitly environment-dependent.
3. **Broker observations outrank unverified cached belief for account effects.** Mismatches
   remain explicit and trading stays disabled until resolved by policy; internal intent history
   is never overwritten to imitate a broker snapshot.
4. **Audit events are not logs.** The trade journal is append-only, schema-versioned, and
   unsampled. Diagnostic telemetry may be retained or sampled separately.
5. **Immutable messages and idempotent effects.** Duplicate delivery must not duplicate an
   order, fill, cash movement, or alert.
6. **Point-in-time or it did not happen.** Symbols, universe membership, fundamentals, and
   corporate actions are represented as known at the simulated time.
7. **Costs are measured and stress-tested.** Fees, spread, slippage, borrow, and market
   impact assumptions are versioned inputs.
8. **Configuration is typed, immutable, and hashable.** A run can always be reconstructed.
9. **Observability is designed with the order lifecycle.** It is not added after paper launch.
10. **No framework worship.** Adopt a kernel only after it passes project-owned fixtures.
11. **Durable intent precedes external effect.** An order is never sent before its identity,
    intent, and risk decision are durably recorded; an uncertain outcome is reconciled rather
    than blindly retried.
12. **Least privilege applies to every control.** Enable, cancel, flatten, deploy, and
    risk-limit administration are distinct authorized actions with auditable identities.

## 5. Foundation evaluation: LEAN versus NautilusTrader

### Candidate posture

| Candidate | Primary reason to evaluate | Main concern to test |
|---|---|---|
| LEAN | Mature US-equity domain support, corporate actions, universes, brokerage models, modular handlers | C#-centric core, operational complexity, paid-account/data workflow, licensing terms, framework coupling |
| NautilusTrader | Clean event-driven architecture, immutable domain messages, execution/risk separation, recovery/reconciliation, Python/Rust path | Current beta release posture; official US-equity corporate-action and point-in-time lifecycle coverage must be verified, not assumed |
| Custom engine | Maximum control | Rejected by default due correctness, recovery, and maintenance burden |

The custom-engine option may be reconsidered only if both candidates fail a documented,
load-bearing requirement that cannot be solved with a bounded adapter or extension.

### S1A — Evidence, dependency, and cost pre-screen

Before installing or implementing either candidate:

1. Pin the candidate version or image digest and record license, release status, supported
   Python/.NET/Rust versions, upgrade policy, and security/update path.
2. Verify each mandatory capability from official documentation and source where practical.
   Classify every claim as `VERIFIED`, `CONTRADICTED`, `UNVERIFIED`, or `NOT TESTABLE`;
   absence of evidence is not a pass.
3. Record historical/live data dependencies, broker dependencies, account requirements,
   data-use and redistribution restrictions, expected storage, and total first-year cost.
4. Define an explicit budget cap. Account creation, paid tiers, subscriptions, downloads,
   and broker connections remain prohibited until separately authorized.
5. Eliminate a candidate immediately if a mandatory requirement is contradicted and cannot
   be supplied by a bounded, project-owned adapter with clear maintenance ownership.

This pre-screen produces a versioned evidence ledger. It is deliberately cheaper than a
two-framework implementation spike.

### S1B — Project-owned offline evaluation spike

Implement the same deliberately unprofitable reference strategy in both remaining candidates.
The spike tests research-platform behavior, not alpha or production-live readiness. It runs in
isolated evaluation workspaces with pinned dependencies, synthetic/golden fixtures, no broker
credentials, no paid downloads, and no framework code in permanent project modules.

The minimal evaluation fixture pack is an S1 deliverable, separate from the production data
foundation built in S2. Each fixture declares inputs, expected events/state, accounting mode,
and exact pass/fail observations:

1. Split, cash dividend, symbol change, and delisting with expected share, cash, symbol, and
   total-return outcomes.
2. Holiday, early close, daylight-saving transition, and an attempted order outside the
   declared market session.
3. Small point-in-time universe, scheduled rebalance, market and limit orders, and a
   deterministic local risk rejection.
4. No-lookahead and availability-time fixtures, including a future constituent that must not
   enter the simulated universe early.
5. Raw versus adjusted price modes with explicitly different expected outputs.
6. Repeat execution of identical code, configuration, clock seed, and data producing the same
   strategy decisions and terminal accounting state.
7. A bounded extension exercise for one custom data field and one telemetry hook without a
   framework fork.

Partial fills, cancel/replace races, duplicate or out-of-order execution events, stale live
data, broker disconnects, crash recovery, external orders, journal replay, and control-plane
security are deferred to the selected kernel's S4 acceptance suite. Passing S1 does not claim
that a candidate is ready for paper or live trading.

### Frozen decision matrix

Before either S1B implementation is run, freeze a matrix with these fields:

```text
requirement_id, MUST_or_SHOULD, scenario, fixture_id, expected_outcome,
evidence_type, candidate_version, result, notes
```

The matrix must identify:

- All `MUST` requirements and which may be satisfied by a bounded adapter.
- Numeric workload assumptions from S0: universe size, frequency, history span, maximum
  acceptable backtest duration, and peak-memory cap.
- Cost ceiling and data/storage assumptions.
- Evidence accepted for each row: official source/documentation, deterministic test, measured
  benchmark, or an explicit `UNVERIFIED` result.
- Predeclared `SHOULD` weights and tie-break order: equity completeness, ownership cost,
  maintainability, extensibility, and measured performance.

Decision truth table:

| Result | Action |
|---|---|
| Exactly one candidate passes every `MUST` | Select it provisionally for S2–S3 research |
| Both pass every `MUST` | Apply the frozen `SHOULD` weights and tie-break order |
| Neither passes every `MUST` | Stop and revise scope; do not begin a custom engine |
| Any `MUST` remains `UNVERIFIED` or `NOT TESTABLE` | No selection until resolved or explicitly removed from `MUST` before results are viewed |
| Selected kernel later fails an S4 live-safety `MUST` | Stop paper activation and reopen the ADR; do not waive the test silently |

The ADR records the matrix, candidate versions, fixture hashes, commands, raw outputs, known
limitations, and rejected alternatives. Selection is provisional for research until S4 proves
the selected kernel's execution, recovery, and control-plane requirements.

## 6. Target architecture

```text
                         RESEARCH PLANE
  Point-in-time data -> features -> hypothesis -> validation -> strategy artifact
           |                                                    |
           |                                            versioned trade intent
           v                                                    v
  Data quality/catalog                              +---------------------+
                                                    | Independent risk    |
                                                    | gate                |
                                                    +----------+----------+
                                                               |
                         TRADING PLANE                         order command
                                                               v
  Broker <-> broker adapter <-> OMS/execution <-> portfolio/accounting
     |                              |                    |
     +-------- reconciliation ------+--------------------+
                                    |
                           append-only event journal
                                    |
                         OPERATIONS AND CONTROL PLANE
              metrics + traces + logs -> dashboard -> alert router
                                    |
                    operator commands + deploy/kill controls
```

The planes may initially run in one process, but their contracts remain explicit. A message
bus or event dispatcher is an implementation detail selected with the kernel, not a reason to
introduce distributed services prematurely.

The operations/control plane is a trust boundary, even in a single-process deployment.
Read-only health/telemetry access is separate from authenticated command access. Alert receivers
do not gain trading-control authority. The broker is authoritative for observed account effects;
the journal is authoritative for internal intent and decision history. Reconciliation compares
both and applies an explicit policy rather than silently overwriting either side.

### Required component boundaries

- `data`: symbol master, calendars, corporate actions, market/fundamental data, quality gates.
- `research`: features, labels, hypotheses, portfolio construction, validation, artifacts.
- `domain`: instrument, price, quantity, money, signal, risk, order, fill, position types.
- `risk`: pre-trade rules, exposure aggregation, drawdown policy, kill switch.
- `execution`: order state machine, idempotency, routing, reconciliation.
- `adapters`: kernel, broker, market data, persistence, notification integrations.
- `audit`: append-only domain journal and deterministic replay.
- `operations`: health, telemetry, dashboards, alerts, operator commands, runbooks.
- `security`: identity, authorization policy, secret lifecycle, audit access, dependency trust.
- `governance`: trial ledger, preregistration, frozen configs, deploy authorization.

## 7. Core contracts and traceability

The domain contracts are framework-neutral even when implemented as wrappers around the
selected kernel:

- `InstrumentId` and versioned symbol mapping.
- Fixed-point or decimal `Price`, `Quantity`, and `Money`; floats are not authoritative cash.
- `MarketEvent` with event time, receive time, source, sequence, and quality status.
- `Signal` with strategy artifact, data snapshot, feature hash, and decision timestamp.
- `OrderIntent` expressing desired economic change without broker-specific fields.
- `RiskDecision` containing accepted/denied, policy version, rule results, and limits used.
- `OrderCommand` containing an idempotency key and client order ID.
- `ExecutionEvent` for acknowledgement, rejection, partial fill, fill, cancel, and expiry.
- `PositionSnapshot` and `AccountSnapshot` with source and as-of timestamp.
- `ReconciliationReport` with differences, resolution policy, and trading-enabled result.

The minimum causal chain is:

```text
global_run_id
  -> strategy_artifact_id
  -> signal_id
  -> risk_decision_id
  -> order_intent_id
  -> client_order_id
  -> broker_order_id
  -> execution_event_id / fill_id
  -> position_change_id
```

Every record in the causal chain carries schema version, event time, ingestion time, code
revision, configuration hash, data version, environment, applicable account/actor identity,
and correlation/causation IDs.

### Order lifecycle invariants

- Submission has a stable idempotency key across every broker-safe retry; an unsafe or unknown
  outcome is reconciled before another external effect is allowed.
- Terminal states cannot transition back to active states.
- Filled quantity is monotonic and cannot exceed ordered quantity without an explicit bust or
  correction event.
- A cancel request does not imply cancellation; only a broker event changes final state.
- Unknown and external orders are represented, never discarded.
- Portfolio changes derive from accepted execution events, not strategy intention.
- Replaying the journal reconstructs the same order and position state.

### External-effect consistency contract

Before S4 implementation, an ADR must select the journal persistence technology and define
the write/send/recovery policy. At minimum:

1. Generate the stable client order ID and idempotency key, then durably persist the
   `OrderIntent`, `RiskDecision`, and `SubmitRequested` event before contacting the broker.
2. Treat a send timeout or lost acknowledgement as `OUTCOME_UNKNOWN`, not as rejection and not
   as permission for a blind retry.
3. Reuse the same client order ID only where the broker contract provides safe idempotency;
   otherwise reconcile before deciding whether another external effect is allowed.
4. Append acknowledgements, rejections, fills, corrections, and reconciliation decisions as new
   events. Never rewrite historical events to make local state resemble broker state.
5. On startup, rebuild local state, query broker cash/positions/open orders/recent executions,
   and resolve or quarantine every difference before enabling new orders.
6. Record external/manual orders explicitly. Any unresolved or unowned order leaves new-order
   routing disabled.
7. Name the single writer for each mutable store, schema/version compatibility rules, backup and
   restore procedure, retention period, and behavior when durable storage is unavailable.

The acceptance suite injects failure before persistence, after persistence but before send,
after send but before acknowledgement, after broker acknowledgement but before local append,
during partial fill, and during recovery. Each case declares the expected journal, broker,
portfolio, and trading-enabled state; terminal replay plus reconciliation must converge without
duplicating an economic effect.

## 8. US-equity data foundation

### Required datasets

- Versioned symbol master with permanent instrument IDs and ticker history.
- Trading calendars, sessions, holidays, and early closes.
- Raw OHLCV and, where needed, quotes/trades with source timestamps.
- Splits, cash/stock dividends, symbol changes, mergers, spin-offs, and delistings.
- Point-in-time universe membership and delisting returns.
- Point-in-time fundamentals only when a hypothesis needs them.
- Fee schedules and spread/slippage observations.
- Borrow availability, borrow rate, and locate assumptions before any short strategy.

### Data rules

- Store raw and adjusted data separately; never overwrite raw observations.
- Declare the price normalization mode in every run artifact.
- Record when data became available, not merely its economic period-end date.
- Fail on duplicate primary keys, non-monotonic event sequences, impossible prices/volume,
  missing corporate-action factors, and calendar inconsistencies.
- Quarantine suspicious partitions instead of silently filling them.
- Hash or version every input partition used by a run.
- Test for survivorship bias with known delisted and renamed fixtures.

Vendor candidates are screened in S1A and selected in a separate ADR before S2 ingestion work.
The ADR covers historical depth, point-in-time fidelity, corporate-action quality, delistings,
API limits, live latency, storage volume, data residency, redistribution/use restrictions,
replacement/export path, and total cost. A convenient API is not sufficient evidence of
research-grade data. Paid access or download requires a separately approved exact product and
cost cap. Raw or licensed market data, provider credentials, and account exports are never
committed to Git, including a private remote; the repository stores only permitted fixtures,
schemas, manifests, hashes, and provenance.

## 9. Research program

### Research operating assumptions

S0 freezes a versioned assumptions sheet before the kernel matrix or strategy search. It is a
modeling contract, not capital authorization, and includes:

- Hypothetical capital range and capacity objective.
- Account type and tax posture; jurisdiction-specific tax conclusions require qualified advice.
- Long-only versus short-enabled scope, margin/leverage, fractional-share policy, and settlement
  assumptions.
- Intended broker model, order types, fee schedule, market sessions, and any intraday/PDT limits.
- Short availability, locate, borrow-rate, and recall assumptions for every short-enabled study.
- Maximum universe size, decision/rebalance frequency, history span, storage budget, maximum
  acceptable backtest duration, and peak-memory cap.
- Benchmark, cash return, risk-free-rate source, and treatment of dividends and withholding.

If account, borrow, tax, or broker assumptions are unresolved, the first cycle is restricted to
long-only, unlevered, daily strategies in liquid US equities/ETFs and reports sensitivity bands
rather than pretending uncertain inputs are known.

### Baselines before hypotheses

Build these first to test accounting and establish opportunity cost:

- Cash/T-bill-equivalent benchmark where data permits.
- Buy-and-hold SPY total-return benchmark.
- Equal-weight liquid-universe benchmark with explicit rebalance costs.
- Random and permuted-signal controls that share the candidate's turnover and constraints.

These are diagnostics, not candidate alpha strategies.

### Initial hypothesis scope

The first research cycle uses daily/hourly data on liquid US equities and ETFs. Candidate
families may include cross-sectional momentum, medium-horizon mean reversion, overnight versus
intraday decomposition, and economically motivated event/fundamental signals. Each family needs
a mechanism statement and a pre-data confirmability/cost screen before implementation.

HFT, market making, and order-book prediction are not fallback choices when a slower hypothesis
fails. They require a new charter, tick/order-book data, queue-position and impact models,
latency measurements, broker/exchange constraints, and a separate economic feasibility gate.

### Research contract

Every candidate is pre-registered with:

- Mechanism and falsifiable prediction.
- Universe and point-in-time membership rule.
- Sample, embargo/purge rules, and untouched final holdout.
- Feature, label, rebalance, sizing, and portfolio-construction rules.
- Benchmark and primary metric.
- Fee, spread, slippage, impact, tax, and borrow assumptions as applicable.
- Search space, number of variants, and stopping rule.
- Capacity/turnover and concentration constraints.
- Pass, fail, ambiguous, and retirement criteria.

Validation includes walk-forward or purged cross-validation as appropriate, Deflated Sharpe or
another declared multiple-testing correction, autocorrelation-aware statistics, cost stress,
subperiod/regime diagnostics, and a final untouched evaluation.

### Attempt accounting

The stock project starts a new family ledger but does not erase prior researcher discretion:

- `global_attempt_id` links the organization-wide research history.
- `family_attempt_id` counts stock variants within a declared hypothesis family.
- Imported or previously viewed hypotheses disclose their provenance.
- Negative, broken, and abandoned trials remain in the ledger with standing status.
- Multiple-testing correction uses the pre-registered relevant selection family; the choice of
  family is itself frozen before results are viewed.

## 10. Risk and capital safety

Every order passes an independent, fail-closed risk gate. Minimum pre-trade checks:

- Trading/deployment authorization and environment.
- Freshness and quality of market data.
- Valid market session and supported order type.
- Price collars and fat-finger notional/quantity limits.
- Available cash/buying power and settlement assumptions.
- Per-symbol, sector, strategy, gross, net, and concentration limits.
- Turnover/order-rate limits and duplicate intent detection.
- Shortability, locate, and borrow constraints where applicable.
- Daily loss, drawdown, and kill-switch state.

Required safety controls:

- Manual and automatic kill switch with an append-only audit event.
- Separate `disable_new_orders` and `cancel_open_orders` actions; flattening is an explicit,
  separately authorized action because it creates market risk.
- Startup reconciliation before strategies may emit executable orders.
- Continuous reconciliation of cash, positions, open orders, and recent fills.
- Trading disabled on unresolved mismatch, stale data, lost heartbeat, corrupt journal, or
  unknown order state.
- Configuration limits cannot be widened by a strategy.
- Secrets never enter run artifacts, logs, or source control.

### Trust and control contract

S0 creates a threat model for data/vendor inputs, configuration, strategy artifacts, broker
events, operator commands, webhooks, dependencies, persistence, and CI. Before S4 paper
activation, the implementation must provide:

- Authenticated operator identity and explicit authorization at each protected action.
- Separate permissions for viewing state, disabling/enabling new orders, canceling orders,
  flattening positions, deploying artifacts, resetting the kill switch, and changing risk limits.
- Least-privilege service and broker credentials scoped to the environment and account.
- A private-by-default network boundary; any remote command endpoint requires encrypted
  transport, replay protection, rate limits, bounded inputs, and safe failure behavior.
- Secret provisioning, encrypted storage, access audit, rotation, revocation, and incident
  replacement procedures. Secrets are redacted from logs, metrics, traces, URLs, and errors.
- Append-only audit access controls, tamper detection, retention, backup/restore, and a named
  write owner. Custom cryptography is prohibited.
- Locked dependencies plus provenance, license, vulnerability, update, and rollback checks.
- Negative tests for unauthorized, replayed, malformed, oversized, rate-limited, cross-
  environment, and tampered commands/events.

Alerts and notification channels are informational outputs and never double as an implicit
trading-command channel. A failed identity, authorization, secret, or audit-integrity check
keeps paper/live order routing disabled.

No real-capital step occurs automatically at the end of this plan. It requires a separate,
dated authorization based on current broker state and readiness evidence.

## 11. Observability, monitoring, and alerting

### Three evidence channels

1. **Audit journal:** unsampled domain truth for signals, risk, orders, fills, reconciliation,
   control actions, and deployment decisions.
2. **Telemetry:** structured logs, metrics, and traces correlated by run/order IDs.
3. **Research artifacts:** immutable configs, data/code versions, predictions, reports, and
   validation decisions.

OpenTelemetry is the preferred vendor-neutral instrumentation contract. Prometheus-compatible
metrics and an Alertmanager-style router provide grouping, deduplication, silencing, inhibition,
and receiver routing. Specific storage/dashboard vendors remain replaceable.

### Required metrics

- Process and strategy heartbeat age.
- Market-data age, gap count, sequence errors, and processing lag.
- Broker connection and authentication state.
- Order submit-to-ack and submit-to-fill latency distributions.
- New, accepted, partial, filled, rejected, canceled, expired, and unknown order counts.
- Unacknowledged/stuck order age and duplicate suppression count.
- Broker-versus-local cash, position, and open-order differences.
- Gross/net exposure, concentration, turnover, leverage, P&L, and drawdown.
- Arrival-price slippage, fees, spread cost, fill ratio, and paper/shadow divergence.
- Strategy signal rate, missing decision cycles, feature/data drift, and benchmark-relative P&L.
- Exception, restart, reconciliation failure, journal write, and alert-delivery failures.

### Alert policy

| Severity | Examples | Expected action |
|---|---|---|
| P0 — safety | Unknown position/order, reconciliation mismatch while enabled, risk breach, corrupt journal | Disable new orders automatically; page operator |
| P1 — impaired | Broker disconnect, stale data near decision time, stuck orders, heartbeat loss | Notify urgently; new-order routing is force-disabled per the §10 disable conditions (stale data, lost heartbeat, unknown/stuck order state, unverifiable broker state) and re-enabled only after the condition resolves and reconciliation confirms clean state |
| P2 — investigate | Rejection/slippage spike, paper-shadow drift, unusual turnover | Ticket or session notification |
| Informational | Fills, deployments, daily summary, expected market close | Dashboard or digest; never page |

Every alert has an owner, runbook, deduplication key, cooldown, recovery notification, and test.
Alerts without an actionable response are metrics or logs, not alerts.

## 12. Verification strategy

### Test layers

- Unit tests for domain values, calendars, corporate actions, risk rules, and state transitions.
- Property/state-machine tests for duplicate, delayed, missing, and out-of-order events.
- Contract tests for every data and broker adapter.
- Golden fixtures for splits, dividends, symbol changes, delistings, and total-return accounting.
- Deterministic replay tests from journal to terminal account/order state.
- Integration tests with simulated venue and broker sandbox/paper environments.
- Fault injection at every journal-write/broker-send boundary plus disconnects, timeouts,
  restarts, stale data, storage failure, and alert failure.
- Security tests for unauthorized, replayed, malformed, cross-environment, and tampered control
  requests and broker events.
- Shadow-versus-backtest and paper-versus-shadow reconciliation reports.
- Load tests sized to the declared universe and frequency, not hypothetical HFT throughput.

### Sacred invariants

The following tests block merge and deployment:

1. No lookahead: information unavailable at decision time cannot affect the order intent.
2. Point-in-time membership: future constituents and renamed/delisted history cannot leak.
3. Corporate-action conservation: share/cash/value transformations follow declared accounting.
4. Idempotency: repeated commands/events do not repeat economic effects.
5. Fail-closed risk: a missing dependency or invalid input cannot bypass the risk gate.
6. Reconciliation before trading: unresolved broker mismatch leaves execution disabled.
7. Deterministic replay: identical journal/config/code reconstructs identical terminal state.
8. Trace completeness: every broker order/fill has a complete or explicitly external causal chain.
9. Deployability enforcement: rejected/retired artifacts cannot enter paper/live mode.
10. Audit durability: an order is not emitted if its required intent/risk audit record cannot be
    durably recorded under the external-effect consistency contract.
11. Control authorization: unauthorized, replayed, expired, or cross-environment commands cannot
    change trading, order, risk, deployment, or kill-switch state.
12. Capital authorization: paper readiness, a successful deployment, or an operator login cannot
    implicitly enable real-capital routing.

## 13. Phased delivery plan

### S0 — Charter and repository boundary

Deliverables:

- After the user explicitly authorizes starting S0, verify that
  `~/Projects/us-equity-trading-system` is absent or stop for inspection; never overwrite,
  merge into, or delete an existing path automatically.
- Create a local-only repository at that path. Do not create a remote or push during this step.
- Write the charter, research operating-assumptions sheet, initial asset/frequency scope,
  workload envelope, cost budget, capital posture, and non-goals.
- Write the S0 threat model, repository/data-residency policy, and secret lifecycle policy.
- Add ADR, preregistration, runbook, and trial-ledger templates.
- Document what is reused, reimplemented, and retained only as FX history.
- Establish dependency locking, provenance/license checks, secret scanning, formatting, local
  test commands, and CI configuration that does not require a remote to validate.

Exit gate:

- Scope is explicit; the stock repository contains no FX pair/pip/swap assumptions.
- The assumptions sheet contains numeric workload and cost ceilings required by the S1 matrix.
- The threat model and repository/data policy cover every planned external input and output.
- No broker credential or live-capital path exists.
- No paid account, subscription, download, remote repository, or publication has occurred.

#### S0-R — Optional remote-publication gate

Remote publication is not required to complete local S0. Before creating or pushing a remote:

1. Obtain explicit authorization for the exact GitHub owner/organization, repository name,
   visibility, administrators, default branch, and intended initial commit.
2. Record the local repository status and an exact intended-file manifest. Selectively extract
   approved reusable files; never bulk-copy the dirty FX worktree or use catch-all staging there.
3. Verify that the commit contains no market/account data, logs, credentials, secrets, licensed
   vendor payloads, or unrelated files; run secret and data-policy checks and review the diff.
4. Stop on any existing local target, remote-name collision, authentication ambiguity, or failed
   check. Do not overwrite, force-push, delete, or change visibility as recovery.
5. After publication, verify that the remote identity, visibility, default branch, and resolved
   commit match the authorization. If publication partially fails, retain the local repository
   and inspect remote state before retrying.

### S1 — Kernel evidence screen and offline evaluation spike

Deliverables:

- Complete S1A's pinned-version capability, dependency, license, data, account, and cost ledger.
- Freeze the `MUST`/`SHOULD` decision matrix and decision truth table before implementation.
- Build the project-owned minimal fixture pack with explicit inputs and expected outcomes.
- Implement the same reference strategy in isolated LEAN and NautilusTrader evaluation
  workspaces for every candidate that survives S1A.
- Run the S1B correctness, research-integrity, determinism, extension, and bounded-performance
  fixtures; preserve commands, fixture hashes, raw results, and resource measurements.
- Write the provisional kernel-selection ADR, including rejected alternatives, unresolved
  limitations, and the S4 conditions that can reopen the decision.

Exit gate:

- Apply the frozen decision truth table literally. A candidate with an unresolved `MUST` cannot
  be selected.
- One candidate is selected provisionally for S2–S3 research, or the project stops for scope
  revision. No S1 result authorizes paper/live execution.
- No paid service, broker connection, or production framework integration was used without a
  separate exact-scope authorization.

### S2 — Point-in-time data and research foundation

Deliverables:

- Symbol master, calendar, corporate-action, and market-data ingestion contracts.
- Raw/adjusted storage with data manifests, hashes, provenance, and quarantine.
- Baseline portfolios and total-return accounting fixtures.
- Trial registry, preregistration freeze, reproducible run artifact, and report schema.
- No-lookahead, survivorship, delisting, and corporate-action sacred tests.
- Promote or rewrite S1 golden fixtures into the permanent test suite, but never use synthetic
  S1 data as evidence of strategy profitability.

Exit gate:

- A clean checkout can reproduce baseline reports from versioned data inputs.
- Known renamed/delisted instruments behave correctly.
- Every data input has a permitted-use, residency, provenance, version, and replacement record;
  no licensed raw payload is stored in Git.

### S3 — First bounded research cycle

Deliverables:

- Pre-data feasibility screen for confirmability, breadth, turnover, and costs.
- One pre-registered strategy family with a small frozen search space.
- Walk-forward/purged validation, multiple-testing correction, stress tests, and holdout report.
- Formal verdict: rejected, ambiguous, or research-validated.
- Reconfirm that the S0 account, cost, tax, borrow, capital, and capacity assumptions still match
  the candidate; freeze any pre-data amendment before viewing candidate results.

Exit gate:

- Continue only if the candidate has positive after-cost out-of-sample evidence, beats its
  declared benchmark, and has a plausible forward-confirmation horizon.
- A negative result closes the strategy family without triggering infrastructure expansion.

### S4 — Paper-capable trading and operations core

This phase starts only after S3 produces a standing research-validated result. S1 selection is
still provisional until the selected kernel passes the S4 live-safety `MUST` suite.

Deliverables:

- Freeze the external-effect consistency ADR and trust/control contract before writing an
  order-emitting adapter.
- Strategy artifact to versioned order-intent boundary.
- Independent risk engine, order lifecycle, journal, replay, and reconciliation.
- Broker paper adapter through the selected kernel.
- Health endpoint, metrics, traces, structured logs, dashboards, and alert router.
- Operator commands, kill switch, deployment guard, and runbooks.
- Automate the deferred S4 acceptance scenarios: partial fill; cancel/replace race; duplicate and
  out-of-order execution events; stale data; broker disconnect with a fill before reconnect;
  every journal-write/broker-send crash boundary; restart with broker-only state; manual/external
  order and cash movement; backup/restore; complete replay; and unauthorized/replayed controls.

Exit gate:

- Every S4 `MUST` passes with pinned kernel/broker-adapter versions. A failure stops activation
  and reopens the kernel ADR; it is not silently waived.
- Recovery/reconciliation and backup/restore tests pass with no unexplained state or duplicated
  economic effect.
- Every test order and fill has a complete causal trace.
- Alerts reach a test receiver and link to a working runbook.
- Unauthorized, replayed, expired, malformed, and cross-environment controls cannot change state;
  no secret appears in logs, metrics, traces, URLs, errors, or artifacts.

### S5 — Shadow and paper validation

Deliverables:

- Continuous shadow decisions without orders, followed by tightly controlled paper execution.
- Backtest-shadow-paper reconciliation dashboard and incident ledger.
- Measured data latency, order latency, fill quality, slippage, fees, and uptime.
- Strategy health, parameter/config drift, and benchmark-relative performance report.
- Restart, disconnect, manual-order, and stale-data drills in the paper environment.
- Expiring, least-privilege paper credentials and operator-role drills, including loss of the
  primary operator and alert receiver.

Exit gate:

- Pre-registered minimum observation/trade requirements are met.
- Divergence is explained and within declared tolerances.
- Zero unresolved cash, position, order, or audit discrepancies.
- Strategy evidence remains standing after measured reality costs.
- Paper completion does not alter the machine-enforced real-capital-disabled state.

### S6 — Live-readiness review, not automatic launch

Deliverables:

- Independent readiness review covering research, data, risk, execution, operations, security,
  broker constraints, and incident response.
- Capacity and loss-budget proposal with a capital ratchet and rollback rules.
- Current broker/account reconciliation and explicit named-owner coverage.
- A separate dated live-capital authorization or a no-launch decision.

Exit gate:

- Exactly one terminal decision artifact is recorded:
  - `NO_LAUNCH` — the default safe completion; reasons are recorded and real-capital routing
    remains mechanically disabled.
  - `AUTHORIZED_FOR_MICRO_LIVE` — a separate explicit authorization naming the broker account,
    strategy artifact/config/data versions, maximum capital and exposure, allowed instruments and
    order types, start/expiry time, operators, monitoring coverage, rollback/kill triggers, and
    current reconciliation evidence.
- Missing evidence, an expired approval, or any unresolved discrepancy results in `NO_LAUNCH` or
  leaves S6 `BLOCKED`; it can never imply authorization.
- `AUTHORIZED_FOR_MICRO_LIVE` permits only the bounded run it names. It is not general approval
  for later strategies, accounts, capital increases, or extensions.

## 14. Reuse and isolation from the forex repository

| Existing asset | Disposition | Conditions |
|---|---|---|
| Preregistration, freeze, honest-N, DSR, falsification concepts | Reuse concept; extract selectively | Add stock family/global attempt IDs and point-in-time rules |
| No-lookahead sacred test pattern | Reuse and extend | Add universe, corporate-action, and availability-time leakage tests |
| Walk-forward/CPCV and reporting logic | Reuse after validation | Verify calendar, return frequency, autocorrelation, and portfolio assumptions |
| Experiment manifests and immutable configs | Reuse pattern | New schemas and stock-specific provenance |
| Kill switch, heartbeat, drawdown contracts | Reuse requirements, not implementations blindly | Integrate with selected kernel and equity account model |
| Audit/prediction/trade log ideas | Evolve into schema-versioned journal/artifacts | Validate schemas and event ownership before extraction |
| FX backtest engine and position/accounting model | Do not copy | Pair, pip, swap, conversion, and execution assumptions are incompatible |
| Saxo adapters and tokens/configuration | Do not copy | Preserve only as historical FX artifacts |
| FX strategies and FX trial ledger | Archive/reference only | Do not present as stock evidence or silently merge family counts |

Shared reusable code should be extracted only after both projects need a stable abstraction.
Premature creation of a generic `quant-core` repository is deferred.

## 15. Major risks and mitigations

| Risk | Mitigation |
|---|---|
| Building infrastructure before alpha | Cheap S1A screen + bounded offline S1B; S3 evidence gate precedes paper-capable S4 work |
| Framework lock-in | Framework-neutral domain/artifact contracts and a documented adapter boundary |
| Survivorship or corporate-action bias | Point-in-time symbol master, delisting fixtures, raw/adjusted separation |
| Backtest/live fantasy | Explicit reality models and continuous shadow/paper reconciliation |
| Data/vendor dependency or surprise cost | S1A evidence/cost ledger, explicit cap and purchase authorization, versioned provider contract, replacement path |
| Unauthorized publication or data leakage | Local-first S0 plus exact-target S0-R authorization, intended-file manifest, secret/data-policy scan |
| Multiple-testing leakage | Frozen family, global provenance, honest attempt ledger, declared stopping rule |
| False precision in costs | Measured observations, stress bands, capacity/turnover limits |
| Alert fatigue | Severity policy, ownership, deduplication, runbooks, regular test alerts |
| Journal/broker dual-write failure | Durable-before-send consistency ADR, stable identity, fault injection, reconciliation before retry |
| Control-plane compromise | Threat model, least privilege, authenticated commands, replay protection, negative tests |
| HFT scope creep | Separate charter and data/infrastructure feasibility gate |
| Premature live launch | Machine-enforced deploy state and exact S6 `NO_LAUNCH`/bounded-authorization terminal contract |

## 16. Definition of done for the initial project

The initial stock project is successful when it can produce an honest decision, including a
decision not to continue. It is not defined by placing a live trade.

Minimum completion criteria:

- Kernel selected provisionally through the frozen S1 matrix, reproducible fixtures, and an ADR.
- Point-in-time data and baseline accounting pass sacred tests.
- A candidate research family receives a formal after-cost out-of-sample verdict.
- Every artifact is reproducible from code, config, and data versions.
- If research passes and S4–S5 execute, the selected kernel passes every live-safety `MUST`, and
  paper execution can recover, reconcile, replay, authorize controls, and alert correctly.
- If S4–S5 execute, no unresolved order, cash, position, audit, security, or deployment-control
  discrepancy exists at their terminal decision.
- Remote publication and paid dependencies, if used, have exact authorization and verification
  artifacts; otherwise they remain absent.
- S6 records `NO_LAUNCH` by default or a separately authorized, expiring, bounded
  `AUTHORIZED_FOR_MICRO_LIVE`; live-capital state remains machine-enforced.

## 17. Immediate next actions

1. Approve this revised proposal as charter input. Approval alone authorizes no filesystem
   change, remote publication, installation, account, purchase, broker connection, or trading.
2. When explicitly asked to begin S0, verify the sibling path and create the local-only
   `~/Projects/us-equity-trading-system` scaffold without a remote.
3. Freeze the charter, assumptions sheet, workload/cost caps, threat model, data/repository
   policy, and reuse map.
4. Complete S1A and freeze the common LEAN/Nautilus `MUST`/`SHOULD` matrix and minimal offline
   fixture specification before installing either candidate.
5. Decide historical-data and future paper-broker candidates, recording license, account,
   storage, and cost constraints; request separate authorization for anything paid or external.
6. Execute bounded S1B and record the provisional kernel ADR.
7. Only then scaffold the permanent S2 domain, data, governance, and research boundaries.
8. If a private GitHub remote is desired, execute S0-R only after exact-target authorization.

## 18. Reference systems

- [QuantConnect LEAN engine](https://github.com/QuantConnect/Lean)
- [LEAN US-equity corporate actions](https://www.quantconnect.com/docs/v2/writing-algorithms/securities/asset-classes/us-equity/corporate-actions)
- [LEAN local US-equity data requirements and pricing](https://www.quantconnect.com/docs/v2/lean-cli/datasets/quantconnect/us-equity)
- [LEAN live reconciliation](https://www.quantconnect.com/docs/v2/writing-algorithms/live-trading/reconciliation)
- [NautilusTrader releases](https://github.com/nautechsystems/nautilus_trader/releases)
- [NautilusTrader architecture](https://nautilustrader.io/docs/latest/concepts/architecture/)
- [NautilusTrader message bus](https://nautilustrader.io/docs/latest/concepts/message_bus/)
- [NautilusTrader live recovery and reconciliation](https://nautilustrader.io/docs/latest/concepts/live/)
- [Freqtrade operational interfaces](https://www.freqtrade.io/en/stable/rest-api/)
- [Qlib portfolio strategy workflow](https://qlib.readthedocs.io/en/stable/component/strategy.html)
- [OpenTelemetry instrumentation](https://opentelemetry.io/docs/concepts/instrumentation/)
- [Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)

Related local evidence:

- `PHASE0_CLOSURE_2026-06-26.md`
- `docs/architecture.md`
- `references/field-survey-2026-06-18.md`
- `references/nautilus-trader-analysis.md`
- `references/freqtrade-analysis.md`
- `references/pybroker-analysis.md`
- `references/vectorbt-analysis.md`
