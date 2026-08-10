from enum import Enum
from dataclasses import dataclass
from .indicators import IndicatorSnapshot
from .trend import TrendState
from .volatility import VolatilityState

class MarketRegime(Enum):
    STRONG_TREND_BULL = "STRONG_TREND_BULL"
    STRONG_TREND_BEAR = "STRONG_TREND_BEAR"
    EXPANSION_BREAKOUT = "EXPANSION_BREAKOUT"
    CHOP_CONSOLIDATION = "CHOP_CONSOLIDATION"
    HIGH_VOLATILITY_SPIKE = "HIGH_VOLATILITY_SPIKE"
    LOW_VOLATILITY_SQUEEZE = "LOW_VOLATILITY_SQUEEZE"

@dataclass
class RegimeSnapshot:
    regime: MarketRegime
    description: str
    is_tradable: bool

class RegimeEngine:
    """Classifies market dynamics into 6 statistical regimes for entry & risk filtering."""

    @staticmethod
    def classify(
        trend: TrendState,
        volatility: VolatilityState,
        indicators: IndicatorSnapshot
    ) -> RegimeSnapshot:
        # High Volatility Spike (> 85th ATR percentile) -> Tradable with reduced risk
        if volatility.atr_percentile > 85.0:
            return RegimeSnapshot(
                regime=MarketRegime.HIGH_VOLATILITY_SPIKE,
                description="Extreme volatility spike / news-like movement",
                is_tradable=True
            )

        # Volatility Squeeze Compression -> Wait for breakout
        if volatility.is_compression or indicators.bb_bandwidth < 0.015:
            return RegimeSnapshot(
                regime=MarketRegime.LOW_VOLATILITY_SQUEEZE,
                description="Tight volatility squeeze / compression",
                is_tradable=True
            )

        # Momentum Breakout Expansion
        if volatility.is_expansion and trend.is_aligned:
            return RegimeSnapshot(
                regime=MarketRegime.EXPANSION_BREAKOUT,
                description="High momentum breakout with volatility expansion",
                is_tradable=True
            )

        # Strong Institutional Trends
        if trend.direction == "BULLISH" and trend.strength >= 70.0:
            return RegimeSnapshot(
                regime=MarketRegime.STRONG_TREND_BULL,
                description="Sustained institutional bullish trend",
                is_tradable=True
            )
        elif trend.direction == "BEARISH" and trend.strength >= 70.0:
            return RegimeSnapshot(
                regime=MarketRegime.STRONG_TREND_BEAR,
                description="Sustained institutional bearish trend",
                is_tradable=True
            )

        # Chop / Consolidation -> STRICT NO TRADE ZONE
        return RegimeSnapshot(
            regime=MarketRegime.CHOP_CONSOLIDATION,
            description="Mean-reverting sideway chop (NO TRADE ZONE)",
            is_tradable=False
        )
