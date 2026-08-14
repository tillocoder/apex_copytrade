from dataclasses import dataclass
from typing import Optional
from .market_data import Candle
from .confidence import ConfidenceScore
from .indicators import IndicatorSnapshot

# ── Symbol Whitelist ─────────────────────────────────────────────────────────
# SOL removed: Win Rate 48.65% and PF 0.84 were dragging overall performance.
# Only trade high-liquidity, trend-following assets with proven edge.
ALLOWED_SYMBOLS = {"BTC/USDT", "ETH/USDT"}

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
        # Symbol whitelist — only trade proven symbols
        if candle.symbol not in ALLOWED_SYMBOLS:
            return None

        if confidence.score < min_confidence or confidence.side == "NONE":
            return None

        price = candle.close
        # ── SL: 1.2× ATR (tighter than before 1.5×) keeps losses small ──────
        # ── Min floor: 0.8% instead of 1.5% to allow tighter SL on BTC/ETH ──
        sl_dist = max(1.2 * indicators.atr, price * 0.008)
        # ── TP: 3× SL distance → RR = 3:1 (was 2:1) ─────────────────────────
        # This is the primary lever: same win rate, 50% more profit per winner
        tp_dist = sl_dist * 3.0

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
