from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Trade:
    trade_id: str
    symbol: str
    side: str
    entry_time: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    confidence: float
    bars_held: int = 0
    is_be_moved: bool = False
    scale_1_taken: bool = False
    scale_2_taken: bool = False
    realized_pnl: float = 0.0
    is_active: bool = True
    initial_units: float = 0.0
    entry_commission: float = 0.0
    accumulated_funding: float = 0.0

@dataclass
class PartialExitResult:
    """Result of a scale-out partial exit."""
    pnl: float          # Pre-commission PnL for this partial exit
    fill_price: float   # Actual price used for this partial fill (clamped to candle H/L)
    close_size: float   # Number of units closed in this partial exit

class TradeManager:
    """Manages active position modifications (Break-Even Shield, Scale-Out Matrix, Trailing Stop)."""

    @staticmethod
    def update_trade(
        trade: Trade,
        current_price: float,
        current_high: float,
        current_low: float,
        atr: float
    ) -> Optional[PartialExitResult]:
        """
        Updates trade state each bar. Returns a PartialExitResult if a scale-out
        partial exit was triggered this bar, otherwise None.

        Partial exit PnL is calculated from the actual fill price (the scale-level
        price clamped to the candle range), NOT from a fixed synthetic dollar amount.
        Commission is NOT included here — backtest.py deducts it using the fill_price.
        """
        if not trade.is_active:
            return None

        trade.bars_held += 1
        if trade.initial_units == 0.0:
            trade.initial_units = trade.size

        initial_risk = abs(trade.entry_price - trade.stop_loss)
        if initial_risk <= 0:
            return None

        # Current R-multiple (positive = in profit direction)
        if trade.side == "BUY":
            current_rr = (current_price - trade.entry_price) / initial_risk
        else:
            current_rr = (trade.entry_price - current_price) / initial_risk

        # ── 1. Break-Even Shield at 1.5 R ────────────────────────────────────
        if current_rr >= 1.5 and not trade.is_be_moved:
            if trade.side == "BUY":
                be_sl = trade.entry_price + (0.1 * atr)
            else:
                be_sl = trade.entry_price - (0.1 * atr)
            trade.stop_loss = round(be_sl, 2)
            trade.is_be_moved = True

        # ── 2. Scale 1: Exit 33% at 2.0 R ────────────────────────────────────
        if current_rr >= 2.0 and not trade.scale_1_taken:
            close_size = round(trade.initial_units * 0.33, 6)
            trade.size = round(trade.size - close_size, 6)
            trade.scale_1_taken = True

            # Actual fill price = the 2.0R level, clamped to candle range
            if trade.side == "BUY":
                scale_price = trade.entry_price + (2.0 * initial_risk)
                scale_price = min(scale_price, current_high)  # cannot fill above candle high
                partial_pnl = (scale_price - trade.entry_price) * close_size
            else:
                scale_price = trade.entry_price - (2.0 * initial_risk)
                scale_price = max(scale_price, current_low)   # cannot fill below candle low
                partial_pnl = (trade.entry_price - scale_price) * close_size

            trade.realized_pnl += partial_pnl
            return PartialExitResult(
                pnl=partial_pnl,
                fill_price=round(scale_price, 2),
                close_size=close_size
            )

        # ── 3. Scale 2: Exit 33% at 3.5 R ────────────────────────────────────
        elif current_rr >= 3.5 and not trade.scale_2_taken:
            close_size = round(trade.initial_units * 0.33, 6)
            trade.size = round(trade.size - close_size, 6)
            trade.scale_2_taken = True

            # Actual fill price = the 3.5R level, clamped to candle range
            if trade.side == "BUY":
                scale_price = trade.entry_price + (3.5 * initial_risk)
                scale_price = min(scale_price, current_high)
                partial_pnl = (scale_price - trade.entry_price) * close_size
            else:
                scale_price = trade.entry_price - (3.5 * initial_risk)
                scale_price = max(scale_price, current_low)
                partial_pnl = (trade.entry_price - scale_price) * close_size

            trade.realized_pnl += partial_pnl
            return PartialExitResult(
                pnl=partial_pnl,
                fill_price=round(scale_price, 2),
                close_size=close_size
            )

        # ── 4. Dynamic Trailing ATR Stop (> 2.5 R) ───────────────────────────
        if current_rr >= 2.5:
            if trade.side == "BUY":
                new_sl = max(trade.stop_loss, current_price - (1.5 * atr))
                trade.stop_loss = round(new_sl, 2)
            elif trade.side == "SELL":
                new_sl = min(trade.stop_loss, current_price + (1.5 * atr))
                trade.stop_loss = round(new_sl, 2)

        return None
