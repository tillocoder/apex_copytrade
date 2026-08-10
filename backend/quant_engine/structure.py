from dataclasses import dataclass
from typing import List, Optional
from .market_data import Candle

@dataclass
class StructurePoints:
    last_swing_high: Optional[float]
    last_swing_low: Optional[float]
    is_bos_bullish: bool
    is_bos_bearish: bool
    is_choch_bullish: bool
    is_choch_bearish: bool

class StructureEngine:
    """Detects Market Structure: Swing Highs/Lows, Body Close BOS, and Counter-trend CHoCH."""

    @staticmethod
    def analyze(candles: List[Candle], swing_window: int = 3) -> StructurePoints:
        sub = candles[-50:]
        n = len(sub)
        if n < (swing_window * 2 + 1):
            return StructurePoints(None, None, False, False, False, False)

        swing_highs = []
        swing_lows = []

        for i in range(swing_window, n - swing_window):
            h_i = sub[i].high
            l_i = sub[i].low

            if all(h_i >= sub[i - j].high for j in range(1, swing_window + 1)) and \
               all(h_i > sub[i + j].high for j in range(1, swing_window + 1)):
                swing_highs.append(h_i)

            if all(l_i <= sub[i - j].low for j in range(1, swing_window + 1)) and \
               all(l_i < sub[i + j].low for j in range(1, swing_window + 1)):
                swing_lows.append(l_i)

        last_sh = swing_highs[-1] if swing_highs else None
        last_sl = swing_lows[-1] if swing_lows else None

        current_close = candles[-1].close
        prev_close = candles[-2].close if len(candles) >= 2 else current_close

        is_bos_bullish = False
        is_bos_bearish = False
        is_choch_bullish = False
        is_choch_bearish = False

        # Body close beyond swing level = Confirmed BOS
        if last_sh and current_close > last_sh and prev_close <= last_sh:
            is_bos_bullish = True
        if last_sl and current_close < last_sl and prev_close >= last_sl:
            is_bos_bearish = True

        # Break of 2nd last swing = Structural CHoCH
        if len(swing_highs) >= 2 and swing_highs[-2] and current_close > swing_highs[-2]:
            is_choch_bullish = True
        if len(swing_lows) >= 2 and swing_lows[-2] and current_close < swing_lows[-2]:
            is_choch_bearish = True

        return StructurePoints(
            last_swing_high=last_sh,
            last_swing_low=last_sl,
            is_bos_bullish=is_bos_bullish,
            is_bos_bearish=is_bos_bearish,
            is_choch_bullish=is_choch_bullish,
            is_choch_bearish=is_choch_bearish
        )
