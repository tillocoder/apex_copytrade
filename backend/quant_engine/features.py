import math
from dataclasses import dataclass
from typing import List
from .market_data import Candle

@dataclass
class BarFeatures:
    timestamp: str
    symbol: str
    body_size: float
    upper_wick: float
    lower_wick: float
    total_range: float
    body_ratio: float
    is_bullish: bool
    volume: float
    volatility_ratio: float

class FeatureEngine:
    """Calculates microstructure and bar-level features."""

    @staticmethod
    def extract_features(candle: Candle, atr_val: float = 1.0) -> BarFeatures:
        body = abs(candle.close - candle.open)
        total_range = max(0.0001, candle.high - candle.low)
        
        if candle.close >= candle.open:
            upper_wick = candle.high - candle.close
            lower_wick = candle.open - candle.low
        else:
            upper_wick = candle.high - candle.open
            lower_wick = candle.close - candle.low

        body_ratio = body / total_range
        volatility_ratio = total_range / max(0.0001, atr_val)

        return BarFeatures(
            timestamp=candle.timestamp.strftime("%Y-%m-%d %H:%M"),
            symbol=candle.symbol,
            body_size=round(body, 2),
            upper_wick=round(upper_wick, 2),
            lower_wick=round(lower_wick, 2),
            total_range=round(total_range, 2),
            body_ratio=round(body_ratio, 4),
            is_bullish=candle.close >= candle.open,
            volume=candle.volume,
            volatility_ratio=round(volatility_ratio, 4)
        )
