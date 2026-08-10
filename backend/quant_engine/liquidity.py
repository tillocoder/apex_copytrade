from dataclasses import dataclass
from typing import List, Optional
from .market_data import Candle

@dataclass
class FVG:
    is_bullish: bool
    top: float
    bottom: float
    midpoint: float

@dataclass
class OrderBlock:
    is_bullish: bool
    high: float
    low: float

@dataclass
class LiquiditySnapshot:
    recent_fvg: Optional[FVG]
    recent_ob: Optional[OrderBlock]
    liquidity_sweep_bullish: bool
    liquidity_sweep_bearish: bool

class LiquidityEngine:
    """Smart Money Concepts (SMC) Engine: Order Blocks, FVG, Liquidity Sweeps."""

    @staticmethod
    def analyze(candles: List[Candle], atr: float = 1.0) -> LiquiditySnapshot:
        if len(candles) < 5:
            return LiquiditySnapshot(None, None, False, False)

        # Detect FVG on last 3 bars (bars -3, -2, -1)
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        recent_fvg = None

        if c3.low > c1.high and (c3.low - c1.high) >= (0.3 * atr):  # Bullish FVG
            top = c3.low
            bottom = c1.high
            recent_fvg = FVG(is_bullish=True, top=top, bottom=bottom, midpoint=(top + bottom) / 2.0)
        elif c1.low > c3.high and (c1.low - c3.high) >= (0.3 * atr):  # Bearish FVG
            top = c1.low
            bottom = c3.high
            recent_fvg = FVG(is_bullish=False, top=top, bottom=bottom, midpoint=(top + bottom) / 2.0)

        # Detect Order Block (OB)
        recent_ob = None
        for i in range(len(candles) - 4, len(candles) - 1):
            curr = candles[i]
            nxt = candles[i + 1]
            if curr.close < curr.open and (nxt.close - nxt.open) > (1.5 * atr):  # Bullish OB
                recent_ob = OrderBlock(is_bullish=True, high=curr.high, low=curr.low)
                break
            elif curr.close > curr.open and (curr.open - nxt.close) > (1.5 * atr):  # Bearish OB
                recent_ob = OrderBlock(is_bullish=False, high=curr.high, low=curr.low)
                break

        # Detect Liquidity Sweep (Wick hunt beyond prior 10-bar high/low followed by close inside)
        sweep_bullish = False
        sweep_bearish = False

        if len(candles) >= 15:
            prior_lows = [c.low for c in candles[-15:-1]]
            prior_highs = [c.high for c in candles[-15:-1]]
            min_low = min(prior_lows)
            max_high = max(prior_highs)

            last = candles[-1]
            if last.low < min_low and last.close > min_low:
                sweep_bullish = True
            if last.high > max_high and last.close < max_high:
                sweep_bearish = True

        return LiquiditySnapshot(
            recent_fvg=recent_fvg,
            recent_ob=recent_ob,
            liquidity_sweep_bullish=sweep_bullish,
            liquidity_sweep_bearish=sweep_bearish
        )
