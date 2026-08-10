import math
from dataclasses import dataclass
from typing import List, Optional
from .market_data import Candle

@dataclass
class IndicatorSnapshot:
    ema_fast: float      # EMA-20
    ema_slow: float      # EMA-50
    ema_trend: float     # EMA-200 (distinct from ema_slow)
    atr: float
    rsi: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_bandwidth: float

class IndicatorEngine:
    """
    Calculates rolling technical indicators with strict zero-lookahead.

    EMA periods:
      - ema_fast  = EMA(20):  uses all available history up to 200 bars
      - ema_slow  = EMA(50):  uses all available history up to 200 bars
      - ema_trend = EMA(200): uses all available history up to 200 bars

    ATR: Wilder-style 14-period average true range over last 30 bars.
    RSI: 14-period over last 30 bars.
    Bollinger: 20-period.

    Bug fixes vs prior version:
      - ema_trend was mistakenly set to ema_slow (the EMA-50).
        Now uses a separate EMA(200) calculation.
      - EMA warm-up now uses up to 200 bars of history for accurate convergence.
    """

    @staticmethod
    def calculate_snapshot(candles: List[Candle], atr_period: int = 14) -> Optional[IndicatorSnapshot]:
        n = len(candles)
        if n < 50:
            return None

        # ── EMA 20, 50, 200 — use all available history (up to 200 bars) ──────
        # Longer warm-up ensures EMAs have converged rather than starting from
        # the most recent close, which biases all three to the same value.
        history = candles[-200:]   # up to 200 bars for warm-up

        k20  = 2.0 / (20  + 1)  # EMA-20  smoothing factor
        k50  = 2.0 / (50  + 1)  # EMA-50  smoothing factor
        k200 = 2.0 / (200 + 1)  # EMA-200 smoothing factor

        # Seed from the OLDEST bar in the history window
        ema20  = history[0].close
        ema50  = history[0].close
        ema200 = history[0].close

        for bar in history[1:]:
            c = bar.close
            ema20  = (c * k20)  + (ema20  * (1.0 - k20))
            ema50  = (c * k50)  + (ema50  * (1.0 - k50))
            ema200 = (c * k200) + (ema200 * (1.0 - k200))

        # ── ATR-14 over last 30 bars ──────────────────────────────────────────
        atr_sub = candles[-30:]
        tr_sum = 0.0
        for i in range(1, len(atr_sub)):
            tr = max(
                atr_sub[i].high - atr_sub[i].low,
                abs(atr_sub[i].high - atr_sub[i - 1].close),
                abs(atr_sub[i].low  - atr_sub[i - 1].close)
            )
            tr_sum += tr
        atr = max(0.01, tr_sum / (len(atr_sub) - 1))

        # ── RSI-14 over last 30 bars ──────────────────────────────────────────
        gains, losses_sum = 0.0, 0.0
        for i in range(1, len(atr_sub)):
            chg = atr_sub[i].close - atr_sub[i - 1].close
            if chg > 0:
                gains += chg
            else:
                losses_sum += abs(chg)
        avg_g = gains      / (len(atr_sub) - 1)
        avg_l = losses_sum / (len(atr_sub) - 1)
        rsi = 100.0 if avg_l == 0 else 100.0 - (100.0 / (1.0 + (avg_g / avg_l)))

        # ── Bollinger Bands (20-period) ───────────────────────────────────────
        bb_sub = candles[-20:]
        mean = sum(c.close for c in bb_sub) / 20.0
        var  = sum((c.close - mean) ** 2 for c in bb_sub) / 20.0
        std  = math.sqrt(var)
        bb_upper = mean + (2.0 * std)
        bb_lower = mean - (2.0 * std)
        bb_bw    = (bb_upper - bb_lower) / max(0.0001, mean)

        return IndicatorSnapshot(
            ema_fast=round(ema20,  2),
            ema_slow=round(ema50,  2),
            ema_trend=round(ema200, 2),   # ← NOW correctly uses EMA-200
            atr=round(atr, 2),
            rsi=round(rsi, 2),
            bb_upper=round(bb_upper, 2),
            bb_middle=round(mean, 2),
            bb_lower=round(bb_lower, 2),
            bb_bandwidth=round(bb_bw, 4)
        )
