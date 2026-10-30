"""Vectorized backtest engine — the heart of Phase 0.

Takes OHLCV data + signals + cost model -> equity curve + trade log.
Strictly avoids lookahead: signals at bar N execute at bar N+1 open.

rebalance_mode="discrete" (default):
    Sign-of-signal direction changes only. Enters/exits on direction flip.
    One trade per direction change. Swap is accrued into equity per elapsed
    calendar day (each trade's total swap is the same as an exit-time lump sum).

rebalance_mode="continuous":
    Every bar, compute target_units = sizer.calculate_size(signal, equity, price, atr, pair).
    If |target_units - cur_units| / cur_units > rebalance_threshold (when in position),
    execute a delta trade. Cost is charged on the delta only. Long-only: negative signal → flat.
    Swap/carry is credited daily via per-bar equity accrual (not as a lump sum at exit).
    Requires sizer to be provided.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from forex_system.core.interfaces import CostModel, PositionSizer
from forex_system.core.types import BacktestResult, Direction, MarginConfig, Trade
from forex_system.costs.model import RolloverAwareRealisticCostModel

logger = logging.getLogger(__name__)

_VALID_REBALANCE_MODES = frozenset({"discrete", "continuous"})


def run_backtest(
    data: pd.DataFrame,
    signals: pd.Series,
    pair: str,
    strategy_name: str,
    cost_model: CostModel,
    initial_capital: float = 100_000.0,
    risk_per_trade: float = 0.02,
    stop_loss_atr_multiple: float = 2.0,
    entry_delay_bars: int = 1,
    sizer: PositionSizer | None = None,
    rebalance_mode: str = "discrete",
    rebalance_threshold: float = 0.20,
    constant_capital_sizing: bool = False,
    allow_shorts: bool = False,
    margin: MarginConfig | None = None,
) -> BacktestResult:
    """Run a vectorized backtest.

    Args:
        data: OHLCV DataFrame with indicators (must include atr_14)
        signals: Series of floats in [-1, +1], same index as data
        pair: Currency pair symbol
        strategy_name: Name for logging
        cost_model: Transaction cost model
        initial_capital: Starting equity in USD
        risk_per_trade: Fraction of equity to risk per trade
        stop_loss_atr_multiple: ATR multiplier for position sizing
        entry_delay_bars: Bars to delay signal execution (1 = next bar)
        sizer: Optional position sizer (required for rebalance_mode="continuous")
        rebalance_mode: "discrete" (default) or "continuous". Discrete mode
            enters/exits on direction changes only. Continuous mode rebalances
            position size every bar when target differs from current by more than
            rebalance_threshold. Backward compatible: "discrete" is unchanged.
        rebalance_threshold: Fractional threshold for continuous rebalancing.
            Rebalance fires when |target - cur| / cur_units > threshold (when in position),
            matching the script's semantics (vol_targeting.py:88).
            Default 0.20 (20%). Only used in continuous mode.
        constant_capital_sizing: If True, the sizer always receives initial_capital as
            account_equity, producing constant-notional sizing (matching the research
            script's `capital / cur_close * scale` convention). If False (default),
            the sizer receives current equity — constant-leverage-on-equity behavior,
            which is correct for live Saxo trading but diverges from the script over
            long compounding periods. Only used in continuous mode.
        allow_shorts: If True, negative signals are passed through to the sizer,
            enabling short positions in continuous mode. Default False preserves
            today's long-only behavior (bit-identical for all existing callers).
            Only meaningful in continuous mode (discrete mode is already sign-aware).
        margin: Optional broker margin terms (both modes). When given, entry
            size is capped at 1/margin_rate leverage, an open position is liquidated
            intrabar once equity falls to stop_out_level * used margin (at the
            stop-out price, or the open if the bar gapped through it), and no new
            position opens while equity <= 0. None (default) = no margin simulation,
            bit-identical to earlier behavior.
    """
    if rebalance_mode not in _VALID_REBALANCE_MODES:
        raise ValueError(
            f"rebalance_mode must be one of {sorted(_VALID_REBALANCE_MODES)}, "
            f"got {rebalance_mode!r}"
        )
    if margin is not None:
        if not 0 < margin.margin_rate <= 1 or not 0 <= margin.stop_out_level < 1:
            raise ValueError(f"invalid MarginConfig: {margin}")

    if data.empty:
        return _empty_result(pair, strategy_name, signals)

    logger.debug(
        "run_backtest: pair=%s strategy=%s mode=%s threshold=%.2f bars=%d constant_cap=%s",
        pair,
        strategy_name,
        rebalance_mode,
        rebalance_threshold,
        len(data),
        constant_capital_sizing,
    )

    if rebalance_mode == "continuous":
        result = _run_continuous(
            data=data,
            signals=signals,
            pair=pair,
            strategy_name=strategy_name,
            cost_model=cost_model,
            initial_capital=initial_capital,
            risk_per_trade=risk_per_trade,
            stop_loss_atr_multiple=stop_loss_atr_multiple,
            entry_delay_bars=entry_delay_bars,
            sizer=sizer,
            rebalance_threshold=rebalance_threshold,
            constant_capital_sizing=constant_capital_sizing,
            allow_shorts=allow_shorts,
            margin=margin,
        )
    else:
        result = _run_discrete(
            data=data,
            signals=signals,
            pair=pair,
            strategy_name=strategy_name,
            cost_model=cost_model,
            initial_capital=initial_capital,
            risk_per_trade=risk_per_trade,
            stop_loss_atr_multiple=stop_loss_atr_multiple,
            entry_delay_bars=entry_delay_bars,
            sizer=sizer,
            margin=margin,
        )

    # Surface silent min_order_size floor clips (F-C): a sizer that clipped
    # nonzero targets to flat must be visible in the result metadata and logs,
    # not produce a degenerate flat equity curve that looks like "no edge".
    n_clipped = getattr(sizer, "n_clipped_to_zero", 0) if sizer is not None else 0
    if n_clipped:
        logger.warning(
            "run_backtest: pair=%s strategy=%s sizer=%s clipped %d nonzero target "
            "size(s) to 0 via min_order_size floor — equity curve may be "
            "degenerate-flat.",
            pair,
            strategy_name,
            type(sizer).__name__,
            n_clipped,
        )
        result.parameters["n_clipped_to_zero"] = n_clipped

    return result


def _run_discrete(
    data: pd.DataFrame,
    signals: pd.Series,
    pair: str,
    strategy_name: str,
    cost_model: CostModel,
    initial_capital: float,
    risk_per_trade: float,
    stop_loss_atr_multiple: float,
    entry_delay_bars: int,
    sizer: PositionSizer | None,
    margin: MarginConfig | None = None,
) -> BacktestResult:
    """Original discrete mode: enter/exit on sign-of-signal direction changes."""
    # Shift signals forward to avoid lookahead
    delayed_signals = signals.shift(entry_delay_bars).fillna(0.0)

    # Discretize to positions: +1, -1, 0
    positions = np.sign(delayed_signals).astype(float)

    # Detect position changes — first bar change is 0 (no prior position)
    position_changes = positions.diff().fillna(0.0)

    atr_series = _get_atr(data)
    pip_value = _get_pip_value(pair)

    # Simulate bar by bar
    equity = initial_capital
    equity_curve = pd.Series(np.nan, index=data.index)
    trade_log: list[Trade] = []

    current_position = 0.0
    current_size = 0.0
    entry_price = 0.0
    entry_time: pd.Timestamp | None = None
    # Swap accrued into equity for the open position (pips per unit, cost-signed)
    # and the whole calendar days it covers.
    swap_cost_pips = 0.0
    swap_days = 0
    liquidations: list[pd.Timestamp] = []

    for i, (ts, row) in enumerate(data.iterrows()):
        price = row["close"]
        if pd.isna(price):
            equity_curve.iloc[i] = equity
            continue

        pos = positions.iloc[i]
        change = position_changes.iloc[i]

        # Accrue swap as calendar days elapse, not as a lump sum at exit: a
        # multi-year hold otherwise books years of carry on its closing bar.
        if current_position != 0:
            bar_cost_pips, swap_days = _accrue_swap(
                cost_model, pair, current_position, entry_time, ts, swap_days
            )
            equity -= bar_cost_pips * pip_value * current_size
            swap_cost_pips += bar_cost_pips

        # Margin stop-out, intrabar: checked before the scheduled close because it
        # happens first. The strategy then stays flat until its signal changes.
        if margin is not None and current_position != 0 and entry_time < ts:
            stop_px = _stop_out_price(equity, entry_price, current_size, current_position, margin)
            fill_px = _stop_out_fill(row, current_position, stop_px)
            if fill_px is not None:
                trade = _close_position(
                    pair,
                    strategy_name,
                    cost_model,
                    pip_value,
                    current_position,
                    current_size,
                    entry_price,
                    entry_time,
                    ts,
                    fill_px,
                    swap_cost_pips=swap_cost_pips,
                )
                trade_log.append(trade)
                equity += trade.pnl_dollars + swap_cost_pips * pip_value * current_size
                liquidations.append(ts)
                current_position = 0.0
                current_size = 0.0
                entry_time = None
                swap_cost_pips = 0.0
                swap_days = 0

        # Close existing position if direction changed
        if change != 0 and current_position != 0:
            trade = _close_position(
                pair,
                strategy_name,
                cost_model,
                pip_value,
                current_position,
                current_size,
                entry_price,
                entry_time,
                ts,
                price,
                swap_cost_pips=swap_cost_pips,
            )
            trade_log.append(trade)
            # trade.pnl_dollars includes the swap already accrued into equity.
            equity += trade.pnl_dollars + swap_cost_pips * pip_value * current_size
            current_position = 0.0
            current_size = 0.0
            entry_time = None
            swap_cost_pips = 0.0
            swap_days = 0

        # Open new position if signal is non-zero
        if change != 0 and pos != 0:
            current_atr = atr_series.iloc[i]
            if sizer is not None:
                raw_signal = delayed_signals.iloc[i]
                current_size = sizer.calculate_size(
                    raw_signal,
                    equity,
                    price,
                    current_atr,
                    pair,
                )
            else:
                current_size = _calculate_size(
                    equity,
                    risk_per_trade,
                    current_atr,
                    stop_loss_atr_multiple,
                    price,
                )
            if margin is not None:
                # Leverage cap; a blown account (equity <= 0) cannot open.
                max_size = equity / (margin.margin_rate * price) if equity > 0 else 0.0
                current_size = min(current_size, max_size)

            if margin is None or current_size > 0:
                entry_cost_pips = cost_model.entry_cost(pair, current_size, timestamp=ts)
                equity -= entry_cost_pips * pip_value * current_size

                current_position = pos
                entry_price = price
                entry_time = ts

        # Mark-to-market (unrealized P&L)
        if current_position != 0:
            unrealized_pips = (price - entry_price) / pip_value * current_position
            equity_curve.iloc[i] = equity + unrealized_pips * pip_value * current_size
        else:
            equity_curve.iloc[i] = equity

    # Close any remaining position at the last bar
    if current_position != 0:
        last_ts = data.index[-1]
        last_price = data["close"].iloc[-1]
        # No-op unless the last bar(s) were skipped as NaN-priced.
        bar_cost_pips, swap_days = _accrue_swap(
            cost_model, pair, current_position, entry_time, last_ts, swap_days
        )
        equity -= bar_cost_pips * pip_value * current_size
        swap_cost_pips += bar_cost_pips
        trade = _close_position(
            pair,
            strategy_name,
            cost_model,
            pip_value,
            current_position,
            current_size,
            entry_price,
            entry_time,
            last_ts,
            last_price,
            swap_cost_pips=swap_cost_pips,
        )
        trade_log.append(trade)
        equity += trade.pnl_dollars + swap_cost_pips * pip_value * current_size
        equity_curve.iloc[-1] = equity

    parameters: dict = {"rebalance_mode": "discrete"}
    if margin is not None:
        parameters.update(
            margin_rate=margin.margin_rate,
            stop_out_level=margin.stop_out_level,
            n_liquidations=len(liquidations),
            liquidation_times=liquidations,
        )
        if liquidations:
            logger.warning(
                "run_backtest: pair=%s strategy=%s margin stop-out x%d (first %s)",
                pair, strategy_name, len(liquidations), liquidations[0],
            )

    return BacktestResult(
        equity_curve=equity_curve,
        trade_log=trade_log,
        signals=signals,
        parameters=parameters,
        pair=pair,
        strategy_name=strategy_name,
        start_date=data.index[0],
        end_date=data.index[-1],
    )


def _run_continuous(
    data: pd.DataFrame,
    signals: pd.Series,
    pair: str,
    strategy_name: str,
    cost_model: CostModel,
    initial_capital: float,
    risk_per_trade: float,
    stop_loss_atr_multiple: float,
    entry_delay_bars: int,
    sizer: PositionSizer | None,
    rebalance_threshold: float,
    constant_capital_sizing: bool = False,
    allow_shorts: bool = False,
    margin: MarginConfig | None = None,
) -> BacktestResult:
    """Continuous rebalance mode.

    Every bar, compute target_units from the sizer using the (already-delayed)
    signal. If the fractional delta vs current units exceeds rebalance_threshold,
    trade the delta. Long-only: negative target → exit to flat.

    No-lookahead guarantee: signals are shifted by entry_delay_bars before any
    sizing decision, identical to discrete mode. The rebalance decision at bar i
    uses delayed_signals[i] (which saw data up to bar i-1), so the economic effect
    lands in that bar's equity mark-to-market.

    Swap/carry is credited daily to the equity curve (not lump-sum at exit), matching
    the reference script vol_targeting.py:72 semantics.
    """
    if sizer is None:
        raise ValueError(
            "rebalance_mode='continuous' requires a sizer. "
            "Pass a PositionSizer instance (e.g. VolTargetSizer) to run_backtest()."
        )

    # Unit-contract guard (F-B): continuous mode treats sizer output as
    # USD-nominal and converts via _to_engine_units. A sizer that declares
    # legacy discrete-convention output (usd_nominal=False, e.g. a default
    # ContinuousSizer) would carry ~1/price of intended risk on JPY pairs.
    if getattr(sizer, "usd_nominal", True) is False:
        logger.warning(
            "continuous mode expects USD-nominal sizer output, but %s was built "
            "with usd_nominal=False — JPY-quoted pairs will carry ~1/price of "
            "intended risk. Rebuild the sizer with usd_nominal=True.",
            type(sizer).__name__,
        )

    # Defensive rail: a rebalance_threshold >= 1.0 with shorts enabled can suppress
    # a flip (frac_delta for a flip = (|cur|+|tgt|)/|cur| > 1.0, but exactly at
    # threshold=1.0 the `>` guard would still fire — however values >1.0 could
    # suppress small flips). Warn once so operators aren't silently misled.
    if allow_shorts and rebalance_threshold >= 1.0:
        logger.warning(
            "allow_shorts=True with rebalance_threshold=%.2f >= 1.0: "
            "a small long-to-short flip may be suppressed if frac_delta <= threshold. "
            "Default threshold=0.20 is safe; consider lowering if flips are missing.",
            rebalance_threshold,
        )

    # Shift signals forward to avoid lookahead — identical to discrete mode
    delayed_signals = signals.shift(entry_delay_bars).fillna(0.0)

    atr_series = _get_atr(data)
    pip_value = _get_pip_value(pair)

    # FIX-1: Compute bar duration in fractional days from the actual index spacing.
    # Use the median timedelta so a few weekend gaps (daily) or session gaps (1h)
    # don't distort the result. Fallback to 1.0 (daily) for single-bar data.
    # The pro-rata path scales by bar_duration_days; the rollover-aware path charges the
    # 22:00 UTC rollovers inside each bar's (ts, ts + bar_duration] span.
    bar_duration_days = _infer_bar_duration_days(data.index)
    # Whole seconds: a float 1/24 day can land a hair under 1h and miss 22:00.
    bar_duration = pd.Timedelta(seconds=round(bar_duration_days * 86_400))

    # KG-QD-3: Select accrual path once before the loop — O(1) check, not per-bar.
    # Plain RealisticCostModel (all validated daily-bar trials) → use_rollover_accrual=False
    # → old pro-rata path, bit-identical results. No existing result changes.
    use_rollover_accrual = isinstance(cost_model, RolloverAwareRealisticCostModel)

    logger.debug(
        "continuous.bar_duration_days=%.6f (freq-agnostic swap scaling)",
        bar_duration_days,
    )

    equity = initial_capital
    equity_curve = pd.Series(np.nan, index=data.index)
    trade_log: list[Trade] = []

    cur_units = 0.0
    entry_price = 0.0
    entry_time: pd.Timestamp | None = None
    # Close of the last processed bar: the rollover-aware accrual window runs from here
    # to this bar's close, so rollovers in data gaps (Friday 22:00 on 1h data) count.
    prev_bar_close: pd.Timestamp | None = None
    liquidations: list[pd.Timestamp] = []

    for i, (ts, row) in enumerate(data.iterrows()):
        price = row["close"]
        if pd.isna(price):
            equity_curve.iloc[i] = equity
            continue

        raw_signal = float(delayed_signals.iloc[i])
        current_atr = float(atr_series.iloc[i]) if not pd.isna(atr_series.iloc[i]) else 0.0

        # Signal clamp: when allow_shorts=False (default) clamp to long-only so
        # that negative signals → flat (bit-identical to today's behavior).
        # When allow_shorts=True, pass the signed signal through — the sizer
        # receives abs() and the sign is re-applied in the engine (Site-S).
        clamped_signal = raw_signal if allow_shorts else max(raw_signal, 0.0)

        # Compute target units using the sizer.
        # The sizer returns USD-nominal exposure (magnitude only). Convert to
        # engine-convention units for quote-currency pairs (e.g. USDJPY) so
        # that the engine's pnl = price_change * units formula yields USD P&L.
        # RC4: constant_capital_sizing uses initial_capital (constant-notional,
        # matching the research script). Default (False) uses current equity
        # (constant-leverage-on-equity, correct for live Saxo trading).
        #
        # Site-S: keep VolTargetSizer magnitude-only (no change to sizer).
        # Apply sign here in the engine: feed abs(clamped_signal) to sizer,
        # then multiply the result by signal_sign to get signed usd_nominal.
        # Under allow_shorts=False: clamped_signal>=0, signal_sign=+1 → no-op.
        signal_sign = 1.0 if clamped_signal >= 0.0 else -1.0
        sizing_equity = initial_capital if constant_capital_sizing else equity
        usd_nominal = signal_sign * sizer.calculate_size(
            abs(clamped_signal),
            sizing_equity,
            price,
            current_atr,
            pair,
        )
        target_units = _to_engine_units(usd_nominal, pair, price)
        if margin is not None:
            # Leverage cap in the P&L numeraire (|units| * price); a blown account
            # (equity <= 0) gets target 0, which closes any open position.
            max_units = equity / (margin.margin_rate * price) if equity > 0 else 0.0
            target_units = float(np.sign(target_units)) * min(abs(target_units), max_units)

        # Decision boundary log — per log-as-decision-trace §3
        logger.debug(
            "continuous.bar: ts=%s signal=%.4f clamped=%.4f usd_nominal=%.0f "
            "target_units=%.2f cur_units=%.2f price=%.4f equity=%.2f",
            ts,
            raw_signal,
            clamped_signal,
            usd_nominal,
            target_units,
            cur_units,
            price,
            equity,
        )

        # RC5: Per-bar swap accrual — credit carry income every bar while in position.
        # The script (vol_targeting.py:72) adds daily_swap_per_unit * cur_units each bar.
        # The engine must do the same so the equity curve reflects carry in real time,
        # not as a lump-sum at position close. Using include_swap=False in _close_position
        # prevents double-counting the holding swap at exit.
        #
        # FIX-1: Scale the per-bar accrual by the bar's duration in days (bar_duration_days),
        # derived from the data index once before the loop. For daily bars this is ≈1.0 (no
        # change). For 1h bars this is 1/24, preventing the 24× over-charge.
        #
        # KG-QD-3: Two paths gated by use_rollover_accrual (set once before loop).
        # rollover-aware path: charge only on 22:00 UTC crossing bars (returns 0.0 on all
        #   non-crossing bars). Negation mirrors line 369: both holding_cost and
        #   rollover_cost_for_bar return `-daily_swap * N`; the engine convention is
        #   `equity += per_bar_swap_pips * pip_value * units` where a NEGATIVE
        #   per_bar_swap_pips means cost (equity decreases).
        # pro-rata path (else): UNCHANGED — bit-identical for all daily-bar callers.
        if cur_units > 0:
            if use_rollover_accrual:
                # Intraday rollover-aware path: charge only on 22:00 UTC crossing bars.
                # rollover_cost_for_bar returns 0.0 on all non-crossing bars; no net
                # change to equity on those bars. Negate per sign-convention (CTO spec
                # sign_convention_correction): rollover_cost_for_bar returns
                # -daily_swap*mult; negate → correct sign for equity accrual.
                per_bar_swap_pips = -cost_model.rollover_cost_for_bar(
                    pair, Direction.LONG, ts, bar_duration, span_start=prev_bar_close
                )
            else:
                # Daily/pro-rata path (unchanged — preserves validated daily results).
                per_bar_swap_pips = -cost_model.holding_cost(
                    pair, Direction.LONG, bar_duration_days, timestamp=ts
                )
            equity += per_bar_swap_pips * pip_value * cur_units
        elif cur_units < 0:
            if use_rollover_accrual:
                # Short-side rollover accrual: mirrors long branch.
                # Branch is now REACHABLE when allow_shorts=True enables negative units.
                per_bar_swap_pips = -cost_model.rollover_cost_for_bar(
                    pair, Direction.SHORT, ts, bar_duration, span_start=prev_bar_close
                )
                equity += per_bar_swap_pips * pip_value * abs(cur_units)
            else:
                # Daily/pro-rata short swap accrual. The cost model's own contract
                # decides: holding_cost(Direction.SHORT) == 0.0 means the model
                # declares swap inert for shorts (e.g. StaticRoundTripCostModel's
                # frozen spec) — accruing that zero is NOT an engine-side research
                # decision. A NONZERO pro-rata short swap is still refused: on
                # intraday data pro-rata over-charges (24x at 1h), so fail loud and
                # require RolloverAwareRealisticCostModel (execution-firewall §A).
                per_bar_swap_pips = -cost_model.holding_cost(
                    pair, Direction.SHORT, bar_duration_days, timestamp=ts
                )
                if allow_shorts and per_bar_swap_pips != 0.0:
                    raise NotImplementedError(
                        "daily/pro-rata short swap accrual not implemented; "
                        "H1 is intraday rollover-aware only. "
                        "Use RolloverAwareRealisticCostModel for short strategies."
                    )
                equity += per_bar_swap_pips * pip_value * abs(cur_units)

        prev_bar_close = ts + bar_duration

        # Margin stop-out, intrabar, after this bar's swap and before any rebalance.
        # Same stop-out price as discrete mode; no re-entry on the liquidation bar.
        liquidated = False
        if margin is not None and cur_units != 0.0 and entry_time is not None and entry_time < ts:
            side = 1.0 if cur_units > 0.0 else -1.0
            stop_px = _stop_out_price(equity, entry_price, abs(cur_units), side, margin)
            fill_px = _stop_out_fill(row, side, stop_px)
            if fill_px is not None:
                trade = _close_position(
                    pair,
                    strategy_name,
                    cost_model,
                    pip_value,
                    side,
                    abs(cur_units),
                    entry_price,
                    entry_time,
                    ts,
                    fill_px,
                    include_swap=False,
                )
                trade_log.append(trade)
                equity += trade.pnl_dollars
                liquidations.append(ts)
                cur_units = 0.0
                entry_price = 0.0
                entry_time = None
                liquidated = True

        # Compute fractional delta to determine if rebalance fires.
        # RC1: use cur_units as denominator (matching script line 88: delta / cur_units)
        # not max(cur_units, 1.0). For USDJPY the units are always >> 1 so the
        # difference is negligible, but the script semantics are correct and cleaner.
        # Site-D: use abs(cur_units) so a short position (cur_units < 0) rebalances
        # on magnitude, not sign. When cur_units==0 both the old and new form yield 1.0.
        denominator = abs(cur_units) if cur_units != 0.0 else 1.0
        frac_delta = abs(target_units - cur_units) / denominator

        if frac_delta > rebalance_threshold and not liquidated:
            # Four-case magnitude+sign decision tree (Site-E / CTO spec Section 3).
            # Branch on sign(cur) vs sign(target), NEVER on sign(delta) or target<=0.
            # This is the ONLY structure that correctly handles shorts, flips, and
            # increase-a-short without the `target_units<=0.0` full-exit trap.
            cur_sign = 0 if cur_units == 0.0 else (1 if cur_units > 0.0 else -1)
            tgt_sign = 0 if target_units == 0.0 else (1 if target_units > 0.0 else -1)

            if tgt_sign == 0:
                # C1: To-flat — close current side completely.
                trade = _close_position(
                    pair,
                    strategy_name,
                    cost_model,
                    pip_value,
                    float(cur_sign),  # +1.0 for long, -1.0 for short
                    abs(cur_units),
                    entry_price,
                    entry_time,
                    ts,
                    price,
                    include_swap=False,
                )
                trade_log.append(trade)
                equity += trade.pnl_dollars
                cur_units = 0.0
                entry_price = 0.0
                entry_time = None

                logger.debug(
                    "continuous.exit: ts=%s pnl=%.2f",
                    ts,
                    trade.pnl_dollars,
                )

            elif cur_sign == 0:
                # C2: From-flat entry — open a fresh position on either side.
                cost_pips = cost_model.entry_cost(pair, abs(target_units), timestamp=ts)
                equity -= cost_pips * pip_value * abs(target_units)
                entry_price = price
                entry_time = ts
                trade_log.append(
                    Trade(
                        pair=pair,
                        direction=Direction.LONG if tgt_sign > 0 else Direction.SHORT,
                        entry_time=ts,
                        exit_time=ts,
                        entry_price=entry_price,
                        exit_price=price,
                        size=abs(target_units),
                        pnl_pips=0.0,
                        pnl_dollars=0.0,
                        cost_pips=cost_pips,
                        cost_dollars=cost_pips * pip_value * abs(target_units),
                        strategy=strategy_name,
                    )
                )
                cur_units = target_units

                logger.debug(
                    "continuous.entry: ts=%s units=%.0f cost_pips=%.4f side=%s",
                    ts,
                    cur_units,
                    cost_pips,
                    "LONG" if tgt_sign > 0 else "SHORT",
                )

            elif tgt_sign == cur_sign:
                # C3: Same-sign resize — increase or partially reduce on the same side.
                m_cur = abs(cur_units)
                m_tgt = abs(target_units)

                if m_tgt > m_cur:
                    # C3-increase: add to the position (works for both long and short).
                    delta_mag = m_tgt - m_cur
                    cost_pips = cost_model.entry_cost(pair, delta_mag, timestamp=ts)
                    equity -= cost_pips * pip_value * delta_mag
                    # Magnitude-form weighted-average entry_price (never signed, so the
                    # `total_new > 0` guard bug cannot affect shorts — Critic finding #2).
                    entry_price = (entry_price * m_cur + price * delta_mag) / m_tgt
                    trade_log.append(
                        Trade(
                            pair=pair,
                            direction=Direction.LONG if cur_sign > 0 else Direction.SHORT,
                            entry_time=entry_time or ts,
                            exit_time=ts,
                            entry_price=entry_price,
                            exit_price=price,
                            size=delta_mag,
                            pnl_pips=0.0,
                            pnl_dollars=0.0,
                            cost_pips=cost_pips,
                            cost_dollars=cost_pips * pip_value * delta_mag,
                            strategy=strategy_name,
                        )
                    )
                    cur_units = target_units

                    logger.debug(
                        "continuous.rebalance_up: ts=%s delta=%.0f new_units=%.0f "
                        "cost_pips=%.4f",
                        ts,
                        delta_mag * cur_sign,
                        cur_units,
                        cost_pips,
                    )

                else:
                    # C3-reduce: trim the position (same side, smaller magnitude).
                    reduce_mag = m_cur - m_tgt
                    cost_pips = cost_model.exit_cost(pair, reduce_mag, timestamp=ts)
                    # Signed price diff: long gains when price rises, short gains when falls.
                    price_diff_pips = (price - entry_price) / pip_value * cur_sign
                    realized_pnl_dollars = (
                        price_diff_pips * pip_value * reduce_mag
                        - cost_pips * pip_value * reduce_mag
                    )
                    equity += realized_pnl_dollars
                    trade_log.append(
                        Trade(
                            pair=pair,
                            direction=Direction.LONG if cur_sign > 0 else Direction.SHORT,
                            entry_time=entry_time or ts,
                            exit_time=ts,
                            entry_price=entry_price,
                            exit_price=price,
                            size=reduce_mag,
                            pnl_pips=price_diff_pips - cost_pips,
                            pnl_dollars=realized_pnl_dollars,
                            cost_pips=cost_pips,
                            cost_dollars=cost_pips * pip_value * reduce_mag,
                            strategy=strategy_name,
                        )
                    )
                    cur_units = target_units

                    logger.debug(
                        "continuous.rebalance_down: ts=%s reduce=%.0f new_units=%.0f "
                        "realized_pnl=%.2f",
                        ts,
                        reduce_mag,
                        cur_units,
                        realized_pnl_dollars,
                    )

            else:
                # C4: Flip — cross-zero direction change. CLOSE-THEN-OPEN (never net).
                # Two legs in one bar; both costs charged (economically honest).

                # Leg 1: close the current side.
                close_trade = _close_position(
                    pair,
                    strategy_name,
                    cost_model,
                    pip_value,
                    float(cur_sign),  # +1.0 for long, -1.0 for short
                    abs(cur_units),
                    entry_price,
                    entry_time,
                    ts,
                    price,
                    include_swap=False,
                )
                trade_log.append(close_trade)
                equity += close_trade.pnl_dollars

                # Leg 2: reset bookkeeping BEFORE opening the new side (Critic finding #4).
                # _close_position does NOT mutate entry_price/entry_time; must be explicit.
                entry_price = price
                entry_time = ts

                # Open the new side.
                open_cost_pips = cost_model.entry_cost(pair, abs(target_units), timestamp=ts)
                equity -= open_cost_pips * pip_value * abs(target_units)
                trade_log.append(
                    Trade(
                        pair=pair,
                        direction=Direction.LONG if tgt_sign > 0 else Direction.SHORT,
                        entry_time=ts,
                        exit_time=ts,
                        entry_price=entry_price,
                        exit_price=price,
                        size=abs(target_units),
                        pnl_pips=0.0,
                        pnl_dollars=0.0,
                        cost_pips=open_cost_pips,
                        cost_dollars=open_cost_pips * pip_value * abs(target_units),
                        strategy=strategy_name,
                    )
                )
                cur_units = target_units

                logger.debug(
                    "continuous.flip: ts=%s from_units=%.0f to_units=%.0f "
                    "close_pnl=%.2f open_cost_pips=%.4f",
                    ts,
                    close_trade.size * cur_sign * -1,  # original side (before flip)
                    cur_units,
                    close_trade.pnl_dollars,
                    open_cost_pips,
                )

        # Mark-to-market (Site-G): widen guard to != 0 so shorts get MtM too.
        # Formula: (price - entry_price)/pip * cur_units is sign-correct for shorts
        # because cur_units < 0 → gain when price falls, loss when price rises.
        if cur_units != 0.0:
            unrealized_pips = (price - entry_price) / pip_value
            equity_curve.iloc[i] = equity + unrealized_pips * pip_value * cur_units
        else:
            equity_curve.iloc[i] = equity

    # Close any remaining position at the last bar (Site-H).
    # Swap was already credited daily so skip it here (include_swap=False).
    # Widen guard to != 0 so a held short is closed and not silently abandoned
    # (closes KG-QD-3 known gap). Pass sign-aware position and abs(size).
    if cur_units != 0.0:
        last_ts = data.index[-1]
        last_price = data["close"].iloc[-1]
        end_position = 1.0 if cur_units > 0.0 else -1.0
        trade = _close_position(
            pair,
            strategy_name,
            cost_model,
            pip_value,
            end_position,
            abs(cur_units),
            entry_price,
            entry_time,
            last_ts,
            last_price,
            include_swap=False,
        )
        trade_log.append(trade)
        equity += trade.pnl_dollars
        equity_curve.iloc[-1] = equity

    parameters: dict = {
        "rebalance_mode": "continuous",
        "rebalance_threshold": rebalance_threshold,
    }
    if margin is not None:
        parameters.update(
            margin_rate=margin.margin_rate,
            stop_out_level=margin.stop_out_level,
            n_liquidations=len(liquidations),
            liquidation_times=liquidations,
        )
        if liquidations:
            logger.warning(
                "run_backtest: pair=%s strategy=%s margin stop-out x%d (first %s)",
                pair, strategy_name, len(liquidations), liquidations[0],
            )

    return BacktestResult(
        equity_curve=equity_curve,
        trade_log=trade_log,
        signals=signals,
        parameters=parameters,
        pair=pair,
        strategy_name=strategy_name,
        start_date=data.index[0],
        end_date=data.index[-1],
    )


def _close_position(
    pair: str,
    strategy_name: str,
    cost_model: CostModel,
    pip_value: float,
    position: float,
    size: float,
    entry_price: float,
    entry_time: pd.Timestamp | None,
    exit_time: pd.Timestamp,
    exit_price: float,
    include_swap: bool = True,
    swap_cost_pips: float | None = None,
) -> Trade:
    """Close a position and return the completed Trade.

    Args:
        include_swap: If True (default), include swap/carry P&L for the holding
            period in the trade PnL. Set to False in continuous mode where swap
            is already credited daily via per-bar equity accrual.
        swap_cost_pips: Swap already accrued over the hold (discrete mode). When
            given it is recorded in the trade PnL as-is instead of being
            recomputed from the hold length; ``include_swap`` is then ignored.
    """
    direction = Direction.LONG if position > 0 else Direction.SHORT
    hold_days = (exit_time - entry_time).days if entry_time is not None else 0

    exit_cost_pips = cost_model.exit_cost(pair, size, timestamp=exit_time)
    if swap_cost_pips is None:
        swap_cost_pips = (
            cost_model.holding_cost(pair, direction, hold_days, timestamp=exit_time)
            if include_swap
            else 0.0
        )
    total_cost_pips = exit_cost_pips + swap_cost_pips

    price_diff_pips = (exit_price - entry_price) / pip_value * position
    net_pnl_pips = price_diff_pips - total_cost_pips

    pnl_dollars = net_pnl_pips * pip_value * size
    cost_dollars = total_cost_pips * pip_value * size

    return Trade(
        pair=pair,
        direction=direction,
        entry_time=entry_time or exit_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        size=size,
        pnl_pips=net_pnl_pips,
        pnl_dollars=pnl_dollars,
        cost_pips=total_cost_pips,
        cost_dollars=cost_dollars,
        strategy=strategy_name,
    )


def _accrue_swap(
    cost_model: CostModel,
    pair: str,
    position: float,
    entry_time: pd.Timestamp,
    ts: pd.Timestamp,
    days_accrued: int,
) -> tuple[float, int]:
    """Swap cost (pips per unit) for the whole calendar days newly held as of ``ts``.

    Counts whole days since entry — the same ``.days`` count the old exit-time
    lump sum used — so each trade's total swap is unchanged; only its timing
    moves into the equity curve. Returns (cost_pips, days_held).
    """
    days_held = (ts - entry_time).days
    new_days = days_held - days_accrued
    if new_days <= 0:
        return 0.0, days_accrued
    direction = Direction.LONG if position > 0 else Direction.SHORT
    return cost_model.holding_cost(pair, direction, new_days, timestamp=ts), days_held


def _stop_out_price(
    equity: float, entry_price: float, size: float, position: float, margin: MarginConfig
) -> float:
    """Price at which equity + unrealized P&L == stop_out_level * margin_rate * size * price.

    ``equity`` is cash equity (entry cost and accrued swap already applied).
    """
    k = margin.stop_out_level * margin.margin_rate
    if position > 0:
        return (entry_price * size - equity) / (size * (1.0 - k))
    return (equity + entry_price * size) / (size * (1.0 + k))


def _stop_out_fill(row: pd.Series, position: float, stop_px: float) -> float | None:
    """Fill price if this bar reached the stop-out level, else None.

    Fills at the stop-out price, or at the open when the bar gapped through it.
    Bars without open/high/low fall back to the close.
    """
    close = row["close"]
    o, hi, lo = (row.get(c, close) for c in ("open", "high", "low"))
    o, hi, lo = (close if pd.isna(v) else v for v in (o, hi, lo))
    if position > 0 and lo <= stop_px:
        return min(o, stop_px)
    if position < 0 and hi >= stop_px:
        return max(o, stop_px)
    return None


def _calculate_size(
    equity: float,
    risk_per_trade: float,
    atr: float,
    atr_multiple: float,
    price: float,
) -> float:
    """Calculate position size based on ATR-based stop distance."""
    if not pd.isna(atr) and atr > 0:
        stop_distance = atr * atr_multiple
        return equity * risk_per_trade / stop_distance
    # Fallback: size based on 2% price move
    return equity * risk_per_trade / (price * 0.02) if price > 0 else 0.0


def _get_atr(data: pd.DataFrame) -> pd.Series:
    """Get ATR series from data, computing if absent."""
    if "atr_14" in data.columns:
        return data["atr_14"]
    tr = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - data["close"].shift(1)).abs(),
            (data["low"] - data["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(14).mean()


def _get_pip_value(pair: str) -> float:
    """Get pip value for a pair (0.0001 for most, 0.01 for JPY)."""
    if "JPY" in pair.upper():
        return 0.01
    return 0.0001


def _to_engine_units(usd_nominal: float, pair: str, price: float) -> float:
    """Convert USD-nominal position size to engine-convention units.

    The engine P&L formula is: pnl_dollars = price_change * units.

    For USD-quoted pairs (EURUSD, GBPUSD) the price change is in USD per unit,
    so units = usd_nominal directly.

    For JPY-quoted pairs (USDJPY, EURJPY) the price change is in JPY, not USD.
    To make pnl_dollars = price_change * units give USD P&L, we need:
        units = usd_nominal / price

    because: pnl_usd = (delta_price_jpy / price_jpy) * usd_nominal
                     = delta_price_jpy * (usd_nominal / price_jpy)
                     = delta_price_jpy * units  ✓

    This keeps VolTargetSizer outputting USD nominal (matching Saxo FX order
    semantics) while the engine handles the quote-currency conversion.

    Args:
        usd_nominal: USD nominal position size from the sizer
        pair: currency pair symbol (e.g. "USDJPY")
        price: current mid price

    Returns:
        Engine-convention units for correct USD P&L arithmetic.
    """
    if pair.upper().endswith("JPY") and price > 0:
        return usd_nominal / price
    return usd_nominal


def _infer_bar_duration_days(index: pd.DatetimeIndex) -> float:
    """Infer the bar duration in fractional days from the index spacing.

    Uses the median timedelta between consecutive bars so that weekend/session
    gaps (which inflate individual deltas) don't distort the result.

    Returns:
        Fractional days per bar. Examples:
          - Business-day daily bars:  ~1.0
          - 4-hour bars:              ~0.1667  (1/6)
          - 1-hour bars:              ~0.0417  (1/24)
          - 15-minute bars:           ~0.0104  (1/96)

    Fallback: 1.0 if the index has fewer than 2 elements (single-bar data).
    """
    if len(index) < 2:
        return 1.0
    deltas = pd.Series(index).diff().dropna()
    median_seconds = float(deltas.median().total_seconds())
    seconds_per_day = 86_400.0
    if median_seconds <= 0:
        return 1.0
    return median_seconds / seconds_per_day


def _empty_result(pair: str, strategy_name: str, signals: pd.Series) -> BacktestResult:
    return BacktestResult(
        equity_curve=pd.Series(dtype=float),
        trade_log=[],
        signals=signals,
        parameters={},
        pair=pair,
        strategy_name=strategy_name,
        start_date=pd.Timestamp.now(),
        end_date=pd.Timestamp.now(),
    )
