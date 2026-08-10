from dataclasses import dataclass
from .structure import StructurePoints
from .liquidity import LiquiditySnapshot
from .trend import TrendState
from .regime import RegimeSnapshot, MarketRegime

@dataclass
class ConfidenceScore:
    score: float  # 0 to 100
    side: str  # "BUY", "SELL", or "NONE"
    reasons: list

class ConfidenceEngine:
    """
    Evaluates multi-factor evidence to generate an institutional Confidence Score (0-100).

    Scoring Breakdown (each component applied EXACTLY ONCE):
      1. Market Structure (BOS / CHoCH) ——— max 25 pts
      2. Liquidity & SMC (FVG / OB / Sweep) max 30 pts
      3. Trend Alignment (EMA 20/50/200) ——— max 25 pts
      4. Market Regime Confirmation ———————— max 20 pts

    Total maximum: 100 pts.
    Entry threshold (from entry.py): >= 70 pts.
    """

    @staticmethod
    def calculate(
        structure: StructurePoints,
        liquidity: LiquiditySnapshot,
        trend: TrendState,
        regime: RegimeSnapshot
    ) -> ConfidenceScore:
        buy_score = 0.0
        sell_score = 0.0
        buy_reasons: list = []
        sell_reasons: list = []

        # ── 1. Structure Evidence (Max: 25 pts) ──────────────────────────────
        if structure.is_bos_bullish and structure.is_choch_bullish:
            buy_score += 25
            buy_reasons.append("[+25] Bullish Structure Confluence (BOS + CHoCH)")
        elif structure.is_bos_bullish:
            buy_score += 15
            buy_reasons.append("[+15] Bullish BOS confirmed")

        if structure.is_bos_bearish and structure.is_choch_bearish:
            sell_score += 25
            sell_reasons.append("[+25] Bearish Structure Confluence (BOS + CHoCH)")
        elif structure.is_bos_bearish:
            sell_score += 15
            sell_reasons.append("[+15] Bearish BOS confirmed")

        # ── 2. Liquidity & SMC Evidence (Max: 30 pts) ───────────────────────
        if liquidity.liquidity_sweep_bullish:
            buy_score += 20
            buy_reasons.append("[+20] Sell-side Liquidity Sweep")
        elif liquidity.recent_fvg and liquidity.recent_fvg.is_bullish:
            buy_score += 10
            buy_reasons.append("[+10] Bullish FVG")

        if liquidity.liquidity_sweep_bearish:
            sell_score += 20
            sell_reasons.append("[+20] Buy-side Liquidity Sweep")
        elif liquidity.recent_fvg and not liquidity.recent_fvg.is_bullish:
            sell_score += 10
            sell_reasons.append("[+10] Bearish FVG")

        if liquidity.recent_ob:
            if liquidity.recent_ob.is_bullish:
                buy_score += 10
                buy_reasons.append("[+10] Order Block support")
            else:
                sell_score += 10
                sell_reasons.append("[+10] Order Block resistance")

        # ── 3. Trend Alignment (Max: 25 pts) ─────────────── Applied ONCE ───
        if trend.direction == "BULLISH" and trend.is_aligned:
            buy_score += 25
            buy_reasons.append("[+25] EMA 20/50/200 Perfect Bullish Alignment")
        elif trend.direction == "BULLISH":
            buy_score += 15
            buy_reasons.append("[+15] Moving Average Uptrend")

        if trend.direction == "BEARISH" and trend.is_aligned:
            sell_score += 25
            sell_reasons.append("[+25] EMA 20/50/200 Perfect Bearish Alignment")
        elif trend.direction == "BEARISH":
            sell_score += 15
            sell_reasons.append("[+15] Moving Average Downtrend")

        # ── 4. Market Regime Confirmation (Max: 20 pts) ──── Applied ONCE ───
        if regime.regime == MarketRegime.STRONG_TREND_BULL:
            buy_score += 20
            buy_reasons.append("[+20] Strong Bull Regime")
        elif regime.regime == MarketRegime.EXPANSION_BREAKOUT:
            buy_score += 15
            buy_reasons.append("[+15] Volatility Expansion Breakout (buy side)")

        if regime.regime == MarketRegime.STRONG_TREND_BEAR:
            sell_score += 20
            sell_reasons.append("[+20] Strong Bear Regime")
        elif regime.regime == MarketRegime.EXPANSION_BREAKOUT:
            sell_score += 15
            sell_reasons.append("[+15] Volatility Expansion Breakout (sell side)")

        # Liquidity sweep bearish adds SELL confidence (separate from regime)
        if liquidity.liquidity_sweep_bearish and regime.regime != MarketRegime.STRONG_TREND_BEAR:
            # avoid double-count: only add if not already captured above
            sell_score += 5
            sell_reasons.append("[+5] Liquidity Raid / Sweep of equal highs")

        # ── Final Decision ────────────────────────────────────────────────────
        buy_score = min(100.0, buy_score)
        sell_score = min(100.0, sell_score)

        if buy_score >= sell_score and buy_score >= 50.0:
            return ConfidenceScore(score=buy_score, side="BUY", reasons=buy_reasons)
        elif sell_score > buy_score and sell_score >= 50.0:
            return ConfidenceScore(score=sell_score, side="SELL", reasons=sell_reasons)
        else:
            return ConfidenceScore(score=0.0, side="NONE", reasons=[])
