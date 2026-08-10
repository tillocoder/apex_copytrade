from dataclasses import dataclass
from typing import Optional
from .market_data import Candle
from .confidence import ConfidenceScore
from .indicators import IndicatorSnapshot

@dataclass
class EntrySignal:
    symbol: str
    side: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: float
    reasons: list

class EntryEngine:
    """Entry signal aggregation and validation."""

    @staticmethod
    def generate(
        candle: Candle,
        confidence: ConfidenceScore,
        indicators: IndicatorSnapshot,
        min_confidence: float = 70.0
    ) -> Optional[EntrySignal]:
        if confidence.score < min_confidence or confidence.side == "NONE":
            return None

        price = candle.close
        sl_dist = max(1.5 * indicators.atr, price * 0.015)
        tp_dist = sl_dist * 2.0

        if confidence.side == "BUY":
            sl = round(price - sl_dist, 2)
            tp = round(price + tp_dist, 2)
            return EntrySignal(
                symbol=candle.symbol,
                side="BUY",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                confidence_score=confidence.score,
                reasons=confidence.reasons
            )
        elif confidence.side == "SELL":
            sl = round(price + sl_dist, 2)
            tp = round(price - tp_dist, 2)
            return EntrySignal(
                symbol=candle.symbol,
                side="SELL",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                confidence_score=confidence.score,
                reasons=confidence.reasons
            )

        return None
