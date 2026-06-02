"""Saxo execution backend — bridges the Strategy layer to Saxo Bank API.

Implements the ExecutionBackend interface for paper trading (SIM) and
eventually live trading. Handles order placement, position tracking,
and reconciliation against broker state.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from forex_system.core.interfaces import ExecutionBackend
from forex_system.core.types import Direction, Position, ExecutionResult
from forex_system.saxo.client import SaxoClient

logger = logging.getLogger(__name__)


class SaxoExecutionBackend(ExecutionBackend):
    """Execution backend that routes orders through Saxo Bank API.

    Works with both SIM (paper) and LIVE environments.
    The SaxoClient determines which environment is used.
    """

    def __init__(self, client: SaxoClient):
        self.client = client
        self._account_key: str | None = None
        self._internal_positions: dict[str, Position] = {}

    @property
    def account_key(self) -> str:
        if self._account_key is None:
            self._account_key = self.client.get_account_key()
        return self._account_key

    @property
    def is_mock(self) -> bool:
        """Return False: SaxoExecutionBackend is always a real broker connection (SIM or LIVE).

        MC-6: Backend-identity mock detection.  SaxoExecutionBackend routes through
        the real Saxo API whether in SIM or LIVE mode — it is never a test stub.
        Test suites that need a mock backend should subclass ExecutionBackend directly
        and override is_mock to return True.

        Note: both SIM (paper) and LIVE Saxo accounts initialise at 100_000.0 —
        float-equality on equity value cannot distinguish them from test mocks.
        Backend-identity (this property) is the correct primary signal.
        """
        return False

    def execute_signal(
        self,
        pair: str,
        signal: float,
        size: float,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a trading signal by placing an order on Saxo.

        Args:
            pair: Currency pair.
            signal: Direction and magnitude. >0 = buy, <0 = sell, 0 = flatten.
            size: Position size in base currency units.
            context: Optional metadata (logged but not used for execution).

        Returns:
            ExecutionResult with fill details.
        """
        context = context or {}
        timestamp = pd.Timestamp.now(tz="UTC")

        # Get current price for slippage measurement
        try:
            price_info = self.client.get_info_price(pair)
            quote = price_info.get("Quote", {})
            bid = quote.get("Bid", 0.0)
            ask = quote.get("Ask", 0.0)
            mid = (bid + ask) / 2 if bid and ask else 0.0
            spread_pips = (ask - bid) / _pip_value(pair) if bid and ask else 0.0
        except Exception as e:
            logger.warning("Could not get price for %s: %s", pair, e)
            mid = 0.0
            spread_pips = 0.0

        # Determine action
        if abs(signal) < 1e-9 or size < 1e-6:
            # Flatten: close any existing position
            return self._flatten_pair(pair, timestamp, mid, spread_pips)

        buy_sell = "Buy" if signal > 0 else "Sell"
        direction = Direction.LONG if signal > 0 else Direction.SHORT

        # Check if we need to close existing opposite position first
        current = self._internal_positions.get(pair)
        if current and current.direction != direction:
            self._flatten_pair(pair, timestamp, mid, spread_pips)

        # Place the order
        try:
            result = self.client.place_order(
                pair=pair,
                buy_sell=buy_sell,
                amount=round(size),  # Saxo requires integer amounts for FX
                order_type="Market",
                account_key=self.account_key,
            )
            order_id = result.get("OrderId", "unknown")
            logger.info(
                "Order placed: %s %s %.0f %s (OrderId=%s)",
                buy_sell, pair, size, "Market", order_id,
            )

            # Update internal position tracking
            self._internal_positions[pair] = Position(
                pair=pair,
                direction=direction,
                size=round(size),
                entry_price=mid,
                entry_time=timestamp,
                unrealized_pnl=0.0,
            )

            return ExecutionResult(
                pair=pair,
                direction=direction,
                size=round(size),
                requested_price=mid,
                fill_price=mid,  # Actual fill price comes from order confirmation
                fill_time=timestamp,
                slippage_pips=0.0,  # Measured after fill confirmation
                spread_at_fill=spread_pips,
                success=True,
                error=None,
            )

        except Exception as e:
            logger.error("Order failed for %s: %s", pair, e)
            return ExecutionResult(
                pair=pair,
                direction=direction,
                size=round(size),
                requested_price=mid,
                fill_price=0.0,
                fill_time=timestamp,
                slippage_pips=0.0,
                spread_at_fill=spread_pips,
                success=False,
                error=str(e),
            )

    def get_positions(self) -> dict[str, Position]:
        """Get current positions from Saxo (source of truth)."""
        positions = {}
        try:
            net_positions = self.client.get_net_positions()
            for pos in net_positions:
                base = pos.get("NetPositionBase", {})
                view = pos.get("NetPositionView", {})

                amount = base.get("Amount", 0)
                if amount == 0:
                    continue

                uic = base.get("Uic")
                try:
                    pair = self.client._uic_to_pair(uic)
                except ValueError:
                    continue

                direction = Direction.LONG if amount > 0 else Direction.SHORT

                positions[pair] = Position(
                    pair=pair,
                    direction=direction,
                    size=abs(amount),
                    entry_price=view.get("AverageOpenPrice", 0.0),
                    entry_time=pd.Timestamp.now(tz="UTC"),  # Saxo doesn't always return this
                    unrealized_pnl=view.get("ProfitLossOnTrade", 0.0),
                )

            # Update internal tracking to match broker
            self._internal_positions = positions

        except Exception as e:
            logger.error("Failed to get positions from Saxo: %s", e)

        return positions

    def flatten_all(self) -> list[ExecutionResult]:
        """Close all open positions."""
        results = []
        timestamp = pd.Timestamp.now(tz="UTC")

        try:
            close_results = self.client.close_all_positions(self.account_key)
            for r in close_results:
                if "error" in r:
                    results.append(ExecutionResult(
                        pair="unknown", direction=Direction.FLAT, size=0,
                        requested_price=0, fill_price=0, fill_time=timestamp,
                        slippage_pips=0, spread_at_fill=0,
                        success=False, error=r["error"],
                    ))
                else:
                    results.append(ExecutionResult(
                        pair="unknown", direction=Direction.FLAT, size=0,
                        requested_price=0, fill_price=0, fill_time=timestamp,
                        slippage_pips=0, spread_at_fill=0,
                        success=True, error=None,
                    ))

            self._internal_positions.clear()

        except Exception as e:
            logger.error("Failed to flatten all: %s", e)
            results.append(ExecutionResult(
                pair="all", direction=Direction.FLAT, size=0,
                requested_price=0, fill_price=0, fill_time=timestamp,
                slippage_pips=0, spread_at_fill=0,
                success=False, error=str(e),
            ))

        return results

    def reconcile(self) -> list[str]:
        """Compare internal position state against Saxo broker state.

        Returns list of discrepancies (empty = positions match).
        """
        # Snapshot internal state BEFORE fetching broker state
        # (get_positions overwrites _internal_positions)
        internal_snapshot = dict(self._internal_positions)
        broker_positions = self.get_positions()
        discrepancies = []

        all_pairs = set(list(internal_snapshot.keys()) +
                        list(broker_positions.keys()))

        for pair in all_pairs:
            internal = internal_snapshot.get(pair)
            broker = broker_positions.get(pair)

            if internal and not broker:
                discrepancies.append(
                    f"{pair}: internal has {internal.direction.name} {internal.size}, "
                    f"broker has nothing"
                )
            elif broker and not internal:
                discrepancies.append(
                    f"{pair}: broker has {broker.direction.name} {broker.size}, "
                    f"internal has nothing"
                )
            elif internal and broker:
                if internal.direction != broker.direction:
                    discrepancies.append(
                        f"{pair}: direction mismatch — internal={internal.direction.name}, "
                        f"broker={broker.direction.name}"
                    )
                if abs(internal.size - broker.size) > 1:
                    discrepancies.append(
                        f"{pair}: size mismatch — internal={internal.size}, "
                        f"broker={broker.size}"
                    )

        if discrepancies:
            logger.warning("Position reconciliation found %d discrepancies", len(discrepancies))
            for d in discrepancies:
                logger.warning("  %s", d)
        else:
            logger.debug("Position reconciliation OK")

        return discrepancies

    def _flatten_pair(
        self, pair: str, timestamp: pd.Timestamp, mid: float, spread: float,
    ) -> ExecutionResult:
        """Close position for a single pair."""
        current = self._internal_positions.pop(pair, None)
        if current is None:
            return ExecutionResult(
                pair=pair, direction=Direction.FLAT, size=0,
                requested_price=mid, fill_price=mid, fill_time=timestamp,
                slippage_pips=0, spread_at_fill=spread,
                success=True, error=None,
            )

        close_side = "Sell" if current.direction == Direction.LONG else "Buy"
        try:
            self.client.place_order(
                pair=pair, buy_sell=close_side, amount=current.size,
                order_type="Market", account_key=self.account_key,
            )
            return ExecutionResult(
                pair=pair, direction=Direction.FLAT, size=current.size,
                requested_price=mid, fill_price=mid, fill_time=timestamp,
                slippage_pips=0, spread_at_fill=spread,
                success=True, error=None,
            )
        except Exception as e:
            # Put position back if close failed
            self._internal_positions[pair] = current
            return ExecutionResult(
                pair=pair, direction=current.direction, size=current.size,
                requested_price=mid, fill_price=0, fill_time=timestamp,
                slippage_pips=0, spread_at_fill=spread,
                success=False, error=str(e),
            )


def _pip_value(pair: str) -> float:
    """Get pip value for a pair."""
    return 0.01 if "JPY" in pair.upper() else 0.0001
