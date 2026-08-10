from dataclasses import dataclass
from typing import List
from .indicators import IndicatorSnapshot

@dataclass
class TrendState:
    direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    strength: float  # 0 to 100
    is_aligned: bool

class TrendEngine:
    """Multi-Moving Average & Price Action Trend Analysis."""

    @staticmethod
    def analyze(price: float, snapshot: IndicatorSnapshot) -> TrendState:
        bullish_score = 0
        bearish_score = 0

        if price > snapshot.ema_fast:
            bullish_score += 25
        else:
            bearish_score += 25

        if snapshot.ema_fast > snapshot.ema_slow:
            bullish_score += 35
        else:
            bearish_score += 35

        if snapshot.ema_slow > snapshot.ema_trend:
            bullish_score += 40
        else:
            bearish_score += 40

        if bullish_score >= 75:
            return TrendState(direction="BULLISH", strength=float(bullish_score), is_aligned=True)
        elif bearish_score >= 75:
            return TrendState(direction="BEARISH", strength=float(bearish_score), is_aligned=True)
        else:
            return TrendState(direction="NEUTRAL", strength=50.0, is_aligned=False)
