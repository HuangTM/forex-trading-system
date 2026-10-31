# Project closure — forex trading system (2026-10-30)

**Decision:** the owner closed the research programme on 2026-10-30.
**Outcome:** no validated trading edge. 36 honest trials were run (the deflation
denominator in `.fintech-org/trials.jsonl`), and none passed its pre-registered gate.
**State at close:** `main` = `origin/main`. Every strategy config is flagged
`deploy_status: do_not_deploy`, so all four order-capable loops refuse to start.
No loop, monitor or scheduled job is running.

## What was tested

There are 30 legacy trials, classified in the ledger's `honest-n-classification` record
(ratified 2026-06-18), and 6 forward trials appended after it. By family:

**Legacy trials:**

| Family | Trials | Outcome |
|---|---|---|
| vol_target_carry parameter variants (USDJPY) | 5 + no-vol-scaling variant | Early "PASS" claims were voided by the 2026-05-31 audit (DSR gate bug, synthetic data) |
| Phase-0 baselines (MA crossover, Bollinger+RSI, momentum, carry, carry-momentum, FRED carry, TAS 4h), two passes | 12 | All rejected by the falsification harness (momentum's 2026-05-02 pass was overturned 2026-06-02 at DSR 0.13) |
| Exploratory looks (buy-and-hold, diagnostics, carry variants) | 8 | Counted as ambiguous, to over-deflate |
| R5 carry-universe kill test (36 cells, one slot) | 1 | AMBIGUOUS_GATE_FAIL; a correction re-run 2026-08-17 left it unchanged |
| R5 confirmatory `f2fb41fd` (vol_target_carry:USDJPY, forward) | 1 | **Shelved** at close (see below) |
| QRB-6 central-bank event study | 1 | Archived |
| A2′ overnight mean reversion EURUSD 1h | 1 | Archived |

**Forward trials:**

| Family | Trials | Outcome |
|---|---|---|
| M1 MACD / M2 EMA 50-200 cross, EURUSD 1h | 2 | FAMILY_KILL. The fix to the shorts setting left the verdict unchanged: the 7.5-pip cost wall |
| carry_fred retest with corrected swap (`65d10ede`) | 1 | **FAIL**: IS SR 0.20, 0.075 at 2× costs, DSR(N=33) 0.31 |
| Fix reversal 1h (`62a72f65`) | 1 | **FAIL**: gross +1.95 bp/day replicates, net −8.5 bp/day after costs |
| FX multifactor carry+value+momentum (`ef3f117d`) | 1 | **INCONCLUSIVE**: SR 0.49, DSR(N=35) 0.63, post-2012 SR 0.22 |
| COT crowding overlay on carry (`f713f511`) | 1 | **FAIL**: −0.44%/yr vs carry, and worse in 2008 |

Each pre-registration and its result is in `references/pre-registrations/`
(`*.md` / `*.RESULT.md`). The last four trials were each committed before they were run.

## What we learned

1. **Costs, not signals, are the binding constraint at retail scale.** Gross patterns
   sometimes replicate; fix reversal is a real effect. But break-even needs about
   0.5-pip round trips, which is the price a liquidity provider pays, not a retail taker.
2. **Carry is the only premium that stays positive across every window.** It is
   compensation for crash risk, and it was never significant in a 7-currency G7 universe.
   Neither value, momentum nor speculative positioning improved it after costs.
3. **Every early "validated" result was an artefact.** The causes were:
   - synthetic daily data for three pairs;
   - JPY rates frozen in 2017;
   - spread units off by 10×;
   - a mathematically broken DSR gate;
   - a lump-sum swap booking;
   - an allow-shorts flag that was silently ignored;
   - a JPY sizing error of 1/150.

   Infrastructure audits found more fake edge than research found real edge.
4. **Pre-registration plus an honest N works.** It is what turned four "PASS" headlines
   into FAILs. With N = 36, monthly data needs an SR of about 0.75–0.80 to clear
   DSR ≥ 0.95. That is a realistic bar for genuine alpha, and nothing here came close.
5. **How the professionals earn in FX** is through market-making spread, client flow,
   breadth (20–40 currencies plus other asset classes) and institutional costs. A retail
   systematic backtest cannot reproduce those structurally.

## Deliberately left open (shelved, not abandoned silently)

- **R5 confirmatory `f2fb41fd`** is frozen and has no capital at risk. Its first look is
  2028-10-06, and the hold-out kill-switch threshold is SR ≥ 1.29. The passive USDJPY
  daily accrual stopped at 2026-04-17, and no quarterly bounds check was logged. To
  revive it, back-fill from the same source (Saxo) before the look; price history does
  not expire. Even a PASS would lead only to a further paper-canary pre-registration.
- **Trend-on-futures pre-registration (`trend-futures-prereg-2026-06-26`)** was frozen
  "awaiting data" and never run. It was not counted (`counts_toward_deflation_denominator:
  false`). Running it would be a new trial.
- **Known issues not fixed** (see CLAUDE.md, "Known issues"):
  - continuous daily pro-rata swap at 5 days/week (pinned by R5);
  - `RealisticCostModel` swap is static by default;
  - script-level null gates in historical research scripts;
  - no config sets `oos_holdout_start`;
  - the committed `data/paper_trading_session.log` and `data/cf_t9_state.json` counter
    are test-contaminated and must never be cited.

## Operational state at close

- **Deploy gate:** `assert_deployable` is wired into all four order-capable loops, and
  every strategy config is flagged: carry_fred FALSIFIED, vol_target_carry
  DO_NOT_DEPLOY, carry_momentum_portfolio FALSIFIED, default and gbpusd_multi RETIRED.
- **Kill switches** persist to per-loop audit logs.
- **LaunchAgent `com.forex.backfill`** (Dukascopy 1h back-fill, finished 2026-10-27) was
  unloaded and disabled on 2026-10-30. The plist was kept. To re-enable:
  `launchctl enable gui/$(id -u)/com.forex.backfill && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.forex.backfill.plist`.
- **Tests:** 1740 passed, 6 skipped, excluding the ~9-minute
  `tests/saxo/test_rem6_429_hardening.py`. The suite no longer writes to tracked files.

## How to reopen

Reopening is an owner decision. Any new idea must:
1. bring a genuinely new information source or breadth;
2. have a pre-registration committed before any return is computed;
3. count as trial #37, with DSR at N = 37.

The engine, cost models (including the opt-in time-varying swap and the margin
simulation in both modes), point-in-time rates, the COT and factor datasets, and the
falsification harness are all in working order.
