from dataclasses import dataclass
from typing import Optional
from .market_data import Candle

@dataclass
class ExitSignal:
    reason: str  # "STOP_LOSS", "TAKE_PROFIT", "TIME_STOP"
    exit_price: float

class ExitEngine:
    """
    Evaluates exit triggers during trade lifecycle.

    Intrabar ordering rule (when both SL and TP are touched in the same candle):
      For BUY trades:
        - Bearish candle (open > close): price moved UP first then DOWN.
          → High was reached before Low → TP hit first.
        - Bullish candle (open <= close): price moved DOWN first then UP.
          → Low was reached before High → SL hit first (conservative).
      For SELL trades: inverse logic.

    This OHLC heuristic is a deterministic convention. It does NOT perfectly
    reconstruct intrabar tick order but is unbiased and reproducible.
    """

    @staticmethod
    def evaluate(
        candle: Candle,
        side: str,
        stop_loss: float,
        take_profit: float,
        bars_held: int,
        max_bars_held: int = 96,  # 96 M15 bars = 24 hours
        mode: str = "CONSERVATIVE"
    ) -> Optional[ExitSignal]:

        if side == "BUY":
            sl_triggered = candle.low <= stop_loss
            tp_triggered = candle.high >= take_profit

            if sl_triggered and tp_triggered:
                if mode == "OPTIMISTIC":
                    return ExitSignal(reason="TAKE_PROFIT", exit_price=take_profit)
                elif mode == "DIRECTIONAL":
                    if candle.open > candle.close:
                        return ExitSignal(reason="TAKE_PROFIT", exit_price=take_profit)
                    else:
                        return ExitSignal(reason="STOP_LOSS", exit_price=stop_loss)
                else:  # CONSERVATIVE (default)
                    return ExitSignal(reason="STOP_LOSS", exit_price=stop_loss)

            elif sl_triggered:
                return ExitSignal(reason="STOP_LOSS", exit_price=stop_loss)
            elif tp_triggered:
                return ExitSignal(reason="TAKE_PROFIT", exit_price=take_profit)

        elif side == "SELL":
            sl_triggered = candle.high >= stop_loss
            tp_triggered = candle.low <= take_profit

            if sl_triggered and tp_triggered:
                if mode == "OPTIMISTIC":
                    return ExitSignal(reason="TAKE_PROFIT", exit_price=take_profit)
                elif mode == "DIRECTIONAL":
                    if candle.open < candle.close:
                        return ExitSignal(reason="TAKE_PROFIT", exit_price=take_profit)
                    else:
                        return ExitSignal(reason="STOP_LOSS", exit_price=stop_loss)
                else:  # CONSERVATIVE (default)
                    return ExitSignal(reason="STOP_LOSS", exit_price=stop_loss)

            elif sl_triggered:
                return ExitSignal(reason="STOP_LOSS", exit_price=stop_loss)
            elif tp_triggered:
                return ExitSignal(reason="TAKE_PROFIT", exit_price=take_profit)

        # Time-based decay stop: exit if trade stagnates beyond max_bars_held
        if bars_held >= max_bars_held:
            return ExitSignal(reason="TIME_STOP", exit_price=candle.close)

        return None
