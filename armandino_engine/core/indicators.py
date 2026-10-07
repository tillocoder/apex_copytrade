"""
Armandino Engine - Technical Indicators
Pure Python implementation of SMA, EMA, RSI, Bollinger Bands, and Donchian Channels.
Fast, deterministic, and dependency-free.
"""

import math
from typing import List, Tuple


def sma(values: List[float], period: int) -> List[float]:
    out = [float("nan")] * len(values)
    if len(values) < period:
        return out
    current_sum = sum(values[:period])
    out[period - 1] = current_sum / period
    for i in range(period, len(values)):
        current_sum += values[i] - values[i - period]
        out[i] = current_sum / period
    return out


def ema(values: List[float], period: int) -> List[float]:
    out = [float("nan")] * len(values)
    if len(values) < period:
        return out
    k = 2.0 / (period + 1.0)
    current_ema = sum(values[:period]) / period
    out[period - 1] = current_ema
    for i in range(period, len(values)):
        current_ema = values[i] * k + current_ema * (1.0 - k)
        out[i] = current_ema
    return out


def rsi(values: List[float], period: int = 14) -> List[float]:
    out = [float("nan")] * len(values)
    if len(values) <= period:
        return out
        
    gains = []
    losses = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
        
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0.0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - (100.0 / (1.0 + rs))
        
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        idx = i + 1
        if avg_loss == 0.0:
            out[idx] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[idx] = 100.0 - (100.0 / (1.0 + rs))
            
    return out


def bollinger_bands(values: List[float], period: int = 20, num_std: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    mid = sma(values, period)
    upper = [float("nan")] * len(values)
    lower = [float("nan")] * len(values)
    
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        m = mid[i]
        variance = sum((x - m) ** 2 for x in window) / period
        sd = math.sqrt(variance)
        upper[i] = m + num_std * sd
        lower[i] = m - num_std * sd
        
    return upper, mid, lower


def donchian_channel(highs: List[float], lows: List[float], period: int = 20) -> Tuple[List[float], List[float]]:
    upper = [float("nan")] * len(highs)
    lower = [float("nan")] * len(highs)
    
    for i in range(period - 1, len(highs)):
        # Channel based on preceding bars (excluding current bar to avoid lookahead)
        upper[i] = max(highs[i - period + 1 : i + 1])
        lower[i] = min(lows[i - period + 1 : i + 1])
        
    return upper, lower
