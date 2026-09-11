"""
Market Data Engine — High-performance 1H and 4H ingestion, caching & indicators.
"""
import json
import math
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone

class MarketDataEngine:
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        with open(cache_file, "r", encoding="utf-8") as f:
            self.raw_candles = json.load(f)

        self.n = len(self.raw_candles)
        self.timestamps = [c[0] / 1000.0 for c in self.raw_candles]
        self.opens = [float(c[1]) for c in self.raw_candles]
        self.highs = [float(c[2]) for c in self.raw_candles]
        self.lows = [float(c[3]) for c in self.raw_candles]
        self.closes = [float(c[4]) for c in self.raw_candles]
        self.volumes = [float(c[5]) for c in self.raw_candles]

        self._compute_indicators()
        self._resample_4h()

    def _compute_indicators(self):
        n = self.n
        # 1H EMAs
        self.ema21_1h = self._calc_ema(self.closes, 21)
        self.ema50_1h = self._calc_ema(self.closes, 50)
        self.ema200_1h = self._calc_ema(self.closes, 200)

        # 1H ATR
        tr = [self.highs[0] - self.lows[0]] * n
        for i in range(1, n):
            tr[i] = max(self.highs[i] - self.lows[i], abs(self.highs[i] - self.closes[i - 1]), abs(self.lows[i] - self.closes[i - 1]))
        self.atr_1h = [0.0] * n
        self.atr_1h[13] = sum(tr[:14]) / 14.0
        for i in range(14, n):
            self.atr_1h[i] = (self.atr_1h[i - 1] * 13.0 + tr[i]) / 14.0

        # 1H RSI
        self.rsi_1h = [50.0] * n
        gains = [0.0] * n; losses = [0.0] * n
        for i in range(1, n):
            diff = self.closes[i] - self.closes[i - 1]
            if diff >= 0: gains[i] = diff
            else: losses[i] = abs(diff)
        avg_gain = sum(gains[1:15]) / 14.0
        avg_loss = sum(losses[1:15]) / 14.0
        for i in range(14, n):
            if i > 14:
                avg_gain = (avg_gain * 13.0 + gains[i]) / 14.0
                avg_loss = (avg_loss * 13.0 + losses[i]) / 14.0
            rs = avg_gain / max(1e-9, avg_loss)
            self.rsi_1h[i] = 100.0 - (100.0 / (1.0 + rs))

        # 20-period Volume MA
        self.vol_ma20 = [self.volumes[0]] * n
        for i in range(19, n):
            self.vol_ma20[i] = sum(self.volumes[i-19:i+1]) / 20.0

    def _resample_4h(self):
        self.candles_4h = []
        self.map_1h_to_4h = []
        curr = []
        for idx, c in enumerate(self.raw_candles):
            curr.append(c)
            if len(curr) == 4:
                o = float(curr[0][1])
                h = max(float(x[2]) for x in curr)
                l = min(float(x[3]) for x in curr)
                cl = float(curr[-1][4])
                v = sum(float(x[5]) for x in curr)
                t = curr[0][0]
                self.candles_4h.append([t, o, h, l, cl, v])
                curr = []
            self.map_1h_to_4h.append(len(self.candles_4h) - 1)

        self.closes_4h = [c[4] for c in self.candles_4h]
        self.ema50_4h = self._calc_ema(self.closes_4h, 50)
        self.ema200_4h = self._calc_ema(self.closes_4h, 200)

    @staticmethod
    def _calc_ema(arr: List[float], period: int) -> List[float]:
        emas = [arr[0]] * len(arr)
        k = 2.0 / (period + 1.0)
        for i in range(1, len(arr)):
            emas[i] = (arr[i] * k) + (emas[i - 1] * (1.0 - k))
        return emas
