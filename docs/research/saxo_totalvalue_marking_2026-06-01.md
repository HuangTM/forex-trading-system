# Saxo `TotalValue` marking-convention investigation

**Date:** 2026-06-01
**Purpose:** Resolve BC-COST-RECON precondition (ii) / NHT MC-5 / CRO open-Q2 — does Saxo
`/port/v1/balances` `TotalValue` mark open-position unrealized P&L at **mid** or at the
**bid/ask close-out price**? This determines whether the cost-reconciliation residual
`R(t) = broker_equity − modeled_equity` is interpretable.

---

## Question

The paper loop fetches account equity as `balance["TotalValue"]`
(`scripts/run_paper_trading_vt.py:327`, `fetch_account_equity`). The new modeled-equity
ledger (`src/forex_system/paper/cost_reconciliation.py`) marks open positions' unrealized
P&L at **mid** (`held_engine_units · (mid_now − mid_prev)`; the system computes
`mid = (bid+ask)/2` at `src/forex_system/saxo/execution.py:67`) and deducts modeled costs
(half-spread) discretely at trade time. If Saxo marks `TotalValue` differently, the
residual carries a deterministic offset that is **not** model divergence.

## Conclusion (documentary, HIGH confidence)

**Saxo `TotalValue` marks open positions at the close-out price (Bid for a long, Ask for a
short), NOT at mid.** `TotalValue` includes unrealized P&L of open positions, and that
unrealized P&L is priced at the close-out side of the spread.

### Evidence chain
1. **`TotalValue` includes open-position unrealized P&L.** The `/port/v1/balances`
   response carries `UnrealizedPositionsValue`, `UnrealizedMarginOpenProfitLoss`,
   `UnrealizedMarginClosedProfitLoss`, and `UnrealizedMarginProfitLoss` alongside
   `TotalValue`; documented Saxo example responses show `TotalValue` moving with non-zero
   unrealized values (e.g. `TotalValue: 103771.48` with `UnrealizedPositionsValue:
   −19684.70`). Source: Saxo Developer Portal — Account Details / Balances reference.
2. **Open positions are marked at the close-out side.** The `PositionView` object
   (`/port/v1/positions`) exposes `Bid`, `Ask`, `CurrentPrice`, **`CurrentPriceType`**, and
   `ProfitLossOnTrade`. In Saxo's documented example, a long position reports
   `CurrentPriceType: "Bid"` — i.e. `CurrentPrice` is the **bid** (the price the long would
   close at), and `ProfitLossOnTrade` (unrealized P&L) is marked to that close-out price.
   For a short, `CurrentPriceType` is `"Ask"`. There is **no** mid-priced unrealized field.
   Source: Saxo Developer Portal — `GET /port/v1/positions` reference (PositionView schema).

### Residual uncertainty
This is documentary confirmation from Saxo's authoritative API reference, which is
sufficient to design the reconciliation. The **gold-standard empirical confirmation** —
open a small SIM position and verify `TotalValue` tracks bid (not mid) — is still worth
running once (script provided below) because (a) SIM pricing can differ from LIVE and
(b) `CalculationReliability` / delayed-price edge cases exist. Until that probe runs, treat
the conclusion as HIGH-confidence-documentary, not empirically-verified-on-our-account.

---

## Implication for the reconciliation residual

While a position is **open**, broker and model disagree by a deterministic basis, not by
model error. Take a long of `u` engine-units, entry mid `m0`, current mid `m1`, broker
half-spread `hs` (= `spread_pips/2`), modeled slippage `sl` (= `slippage_pips`) and
commission `c` (= `commission_pips`). From `src/forex_system/costs/model.py:26-34`:
`entry_cost = hs + sl`, `exit_cost = hs + sl + c` (exit_cost is booked **only** on a close —
`is_close=True` in both paper scripts — so it is deferred during the hold).

> **NOTE (corrected 2026-06-01 after adversarial review):** the first draft used `entry_cost
> ≈ hs` and concluded `R ≈ −u·hs → 0` at close. That dropped slippage and is **wrong in both
> sign and magnitude** for our config (`hs=0.25`, `sl=0.5`, `c=0.5` pips for EURUSD — so
> `sl > hs`). The corrected algebra below supersedes it.

- **Broker** marks the open position at the close-out side: bought at ask `m0+hs`, marks at
  bid `m1−hs` ⇒ `unrealized_broker = u·(m1−m0) − 2·u·hs`. (Broker marking captures the
  *spread* only; any real slippage/commission Saxo applies is separate and is exactly what
  the residual is meant to surface.)
- **Model** marks at mid and booked `entry_cost = u·(hs+sl)` once at entry, defers exit:
  `unrealized_model = u·(m1−m0) − u·(hs+sl)`.
- **Residual while open:** `R = broker − model = u·(hs+sl) − 2·u·hs = u·(sl − hs)`.
  For our config `sl − hs = 0.25` pips > 0, so the **model sits BELOW the broker** by
  `≈ u·(sl−hs)` while open (it over-charges relative to the broker's spread-only marking).
  Sign flips if a pair ever has `sl < hs`.
- **On close (cumulative per trade):** model additionally books `exit_cost = u·(hs+sl+c)`.
  Net realized residual `R_close = u·(2·sl + c)` (model below broker), **not ~0**. This
  constant is precisely `(modeled slippage+commission) − (broker's actual slippage+
  commission)` — i.e. the cost-model error reconciliation exists to measure. It is zero only
  if the model's slippage+commission assumptions exactly match Saxo's realized costs.

So a naïve `|R| ≤ tol` alarm fires on the deterministic `u·(sl−hs)` open-position basis, not
on divergence — exactly the false-signal NHT MC-5 warned about. The interpretable signal is
the *deviation of `R` from its expected basis*, not `R` itself.

### Recommendation (for the QD when reconciliation moves toward enforce-mode)
Our live strategies (vol_target_carry, carry_fred) are **long-hold carry** — positions can be
held days to weeks — so "flat-to-flat only" would give almost no signal during a hold (a
breach on day 3 that self-heals by day 10 would never fire). Therefore, in order of
preference:

1. **Per-cycle expected-offset-adjusted residual (PRIMARY).** Track
   `R_adj = R − u·(sl − hs)` every cycle (remove the known open-position spread basis using
   the live `hs` from the same quote fetch that gives mid). `R_adj` should hover near zero +
   model error; a *trend* in `R_adj` is genuine divergence. This gives coverage across the
   entire holding period — the property the carry strategies need. Record `R`, `R_adj`, and
   the expected basis as separate JSONL columns for post-hoc analysis.
2. **Flat-to-flat as a clean corroborating check.** On zero-exposure cycles the open basis
   vanishes and the realized per-trade residual `≈ u·(2sl+c)` is the pure cost-model error —
   a clean, low-noise anchor to cross-check (1). Also sidesteps `CalculationReliability`
   delayed-price edge cases. Use it *alongside* (1), not instead of it.
3. **Mark the modeled ledger at close-out (fallback).** Mark unrealized at bid/ask via the
   position's `CurrentPriceType`. Apples-to-apples per cycle, but diverges from the
   *backtest*'s mid+cost convention, muddying backtest-equivalence — hence a fallback.

This is a calibration-phase decision; it does **not** change the shipped alarm-only posture.
Logged here so tolerance calibration (precondition iii) starts from the corrected model. The
empirical probe (below) pins `hs` and reveals whether Saxo charges separate commission, which
sets the `u·(2sl+c)` term's expected value.

---

## Empirical confirmation — operator probe (precondition ii, gold standard)

`scripts/probe_saxo_marking.py` (read-only by default) confirms the convention on our own
SIM account. It needs a 24h SIM developer token (`SAXO_TOKEN` env or `--token`). Read-only
mode reads balances + open positions + infoprices and reports, for each open position,
whether `TotalValue`'s implied unrealized matches **bid-marked** vs **mid-marked** P&L, and
prints `CurrentPriceType`. If no position is open, it instructs how to open a tiny one
manually (or pass `--open-and-flatten EURUSD` to open 1k units, sample, and immediately
flatten — SIM only; never LIVE).

Run:
```bash
SAXO_TOKEN=<24h-sim-token> python scripts/probe_saxo_marking.py            # read-only
SAXO_TOKEN=<24h-sim-token> python scripts/probe_saxo_marking.py --open-and-flatten EURUSD
```
Expected result if the conclusion holds: for an open long, `CurrentPriceType == "Bid"` and
`TotalValue` tracks the **bid**-marked unrealized (not the mid-marked one) within rounding.
