"""
Armandino Engine - Signal Generators for ETH and ZEC
Implements:
1. ETH Multi-Timeframe Trend Breakout & Mean Reversion (M15/H1)
2. ZEC Local Peak Aggressive Short & Post-Dump Consolidation Long (M15)
"""

from typing import List, Dict, Optional, Tuple
from .models import Side
from .indicators import ema, sma, rsi, bollinger_bands, donchian_channel


class SignalGenerator:
    def __init__(self):
        pass

    @staticmethod
    def generate_eth_signals(
        m15_candles: List[Dict],
        h1_candles: List[Dict]
    ) -> List[Optional[Tuple[Side, str]]]:
        """
        ETH Signals on M15:
        1. Breakout: H1 EMA(20) > EMA(50) + M15 20-bar Donchian High breakout -> LONG
                     H1 EMA(20) < EMA(50) + M15 20-bar Donchian Low breakout -> SHORT
        2. Mean Reversion: M15 RSI(14) < 30 & Low <= Lower BB -> LONG
                           M15 RSI(14) > 70 & High >= Upper BB -> SHORT
        """
        n_m15 = len(m15_candles)
        signals: List[Optional[Tuple[Side, str]]] = [None] * n_m15
        
        # M15 series
        m15_closes = [c["close"] for c in m15_candles]
        m15_highs = [c["high"] for c in m15_candles]
        m15_lows = [c["low"] for c in m15_candles]
        
        m15_rsi = rsi(m15_closes, 14)
        m15_bb_upper, m15_bb_mid, m15_bb_lower = bollinger_bands(m15_closes, 20, 2.0)
        m15_don_upper, m15_don_lower = donchian_channel(m15_highs, m15_lows, 20)
        
        # H1 series
        h1_closes = [c["close"] for c in h1_candles]
        h1_ema20 = ema(h1_closes, 20)
        h1_ema50 = ema(h1_closes, 50)
        h1_ts_map = {c["timestamp"]: i for i, c in enumerate(h1_candles)}
        
        # Map each M15 bar to the latest closed H1 bar
        h1_timestamps = [c["timestamp"] for c in h1_candles]
        
        h1_idx = 0
        for i in range(25, n_m15):
            t_m15 = m15_candles[i]["timestamp"]
            # Find latest completed H1 bar before or at t_m15
            while h1_idx + 1 < len(h1_timestamps) and h1_timestamps[h1_idx + 1] <= t_m15:
                h1_idx += 1
                
            h1_bullish = False
            h1_bearish = False
            if h1_idx >= 50:
                e20 = h1_ema20[h1_idx]
                e50 = h1_ema50[h1_idx]
                if not (e20 != e20 or e50 != e50): # Not nan
                    h1_bullish = e20 > e50
                    h1_bearish = e20 < e50
                    
            c = m15_closes[i]
            prev_c = m15_closes[i - 1]
            h = m15_highs[i]
            l = m15_lows[i]
            r = m15_rsi[i]
            
            # 1. Breakout setup
            don_u = m15_don_upper[i - 1]
            don_l = m15_don_lower[i - 1]
            
            if h1_bullish and prev_c <= don_u and c > don_u:
                signals[i] = (Side.LONG, "ETH_BREAKOUT_LONG")
                continue
            elif h1_bearish and prev_c >= don_l and c < don_l:
                signals[i] = (Side.SHORT, "ETH_BREAKOUT_SHORT")
                continue
                
            # 2. Mean Reversion setup
            b_low = m15_bb_lower[i]
            b_high = m15_bb_upper[i]
            if r < 30.0 and l <= b_low and c > m15_candles[i]["open"]:
                signals[i] = (Side.LONG, "ETH_MEANREV_LONG")
                continue
            elif r > 70.0 and h >= b_high and c < m15_candles[i]["open"]:
                signals[i] = (Side.SHORT, "ETH_MEANREV_SHORT")
                continue
                
        return signals

    @staticmethod
    def generate_zec_signals(m15_candles: List[Dict]) -> List[Optional[Tuple[Side, str]]]:
        """
        ZEC Signals on M15:
        1. Aggressive Short on local peaks:
           RSI(14) > 68 AND High >= Upper BB(20, 2) AND rejection (upper wick >= 30% of range or red candle)
        2. Long on consolidation after strong dump:
           Dump detected in last 4 bars (Low < Lower BB and RSI < 32),
           Current bar confirms bounce: Close crosses above EMA(9) with green candle.
        """
        n = len(m15_candles)
        signals: List[Optional[Tuple[Side, str]]] = [None] * n
        
        closes = [c["close"] for c in m15_candles]
        highs = [c["high"] for c in m15_candles]
        lows = [c["low"] for c in m15_candles]
        opens = [c["open"] for c in m15_candles]
        
        z_rsi = rsi(closes, 14)
        bb_upper, bb_mid, bb_lower = bollinger_bands(closes, 20, 2.0)
        ema9 = ema(closes, 9)
        
        for i in range(25, n):
            c = closes[i]
            o = opens[i]
            h = highs[i]
            l = lows[i]
            r = z_rsi[i]
            b_u = bb_upper[i]
            b_l = bb_lower[i]
            
            # Setup 1: Aggressive Peak Short
            if r > 68.0 and h >= b_u:
                total_range = h - l
                upper_wick = h - max(o, c)
                # Rejection if upper wick >= 30% or candle is bearish
                if total_range > 0 and (upper_wick / total_range >= 0.30 or c < o):
                    signals[i] = (Side.SHORT, "ZEC_PEAK_SHORT")
                    continue
                    
            # Setup 2: Long on consolidation after strong dump
            # Check if any of previous 4 bars had dump condition
            recent_dump = False
            for prev_idx in range(max(0, i - 4), i):
                if lows[prev_idx] <= bb_lower[prev_idx] and z_rsi[prev_idx] < 32.0:
                    recent_dump = True
                    break
                    
            if recent_dump:
                e9 = ema9[i]
                prev_c = closes[i - 1]
                prev_e9 = ema9[i - 1]
                # Consolidation hook: crossing above EMA 9 with bullish candle
                if prev_c <= prev_e9 and c > e9 and c > o:
                    signals[i] = (Side.LONG, "ZEC_DUMP_BOUNCE_LONG")
                    continue
                    
        return signals
