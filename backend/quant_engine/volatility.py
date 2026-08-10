from dataclasses import dataclass
from typing import List
from .market_data import Candle

@dataclass
class VolatilityState:
    atr: float
    is_compression: bool
    is_expansion: bool
    atr_percentile: float

class VolatilityEngine:
    """Detects Volatility Squeeze (Compression) and Breakout Expansion."""

    @staticmethod
    def analyze(candles: List[Candle], current_atr: float) -> VolatilityState:
        if len(candles) < 20:
            return VolatilityState(current_atr, False, False, 50.0)

        # Calculate historical candle ranges
        ranges = [c.high - c.low for c in candles[-50:]]
        avg_range = sum(ranges) / len(ranges)
        
        current_range = candles[-1].high - candles[-1].low

        is_compression = current_range < (0.6 * avg_range)
        is_expansion = current_range > (1.8 * avg_range)

        sorted_ranges = sorted(ranges)
        rank = sum(1 for r in sorted_ranges if r <= current_range)
        percentile = (rank / len(sorted_ranges)) * 100.0

        return VolatilityState(
            atr=round(current_atr, 2),
            is_compression=is_compression,
            is_expansion=is_expansion,
            atr_percentile=round(percentile, 1)
        )
