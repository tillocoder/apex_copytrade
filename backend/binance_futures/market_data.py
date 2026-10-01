import time
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .config import DEFAULT_CONFIG

class MarketDataManager:
    def __init__(self, symbol: str = "ETHUSDT"):
        self.symbol = symbol
        self.best_bid = 0.0
        self.best_ask = 0.0
        self.bid_qty = 0.0
        self.ask_qty = 0.0
        self.mark_price = 0.0
        self.funding_rate = 0.0
        self.last_update_ts = 0.0
        
        # Multi-timeframe Kline memory (store dicts with open, high, low, close, volume, time)
        self.klines_m1: List[Dict[str, Any]] = []
        self.klines_m5: List[Dict[str, Any]] = []
        self.klines_m15: List[Dict[str, Any]] = []
        self.klines_h1: List[Dict[str, Any]] = []

    def update_book_ticker(self, bid: float, ask: float, bid_qty: float, ask_qty: float):
        self.best_bid = float(bid)
        self.best_ask = float(ask)
        self.bid_qty = float(bid_qty)
        self.ask_qty = float(ask_qty)
        self.last_update_ts = time.time()

    def update_mark_price(self, mark: float, funding_rate: float):
        self.mark_price = float(mark)
        self.funding_rate = float(funding_rate)
        self.last_update_ts = time.time()

    def get_current_price(self) -> float:
        if self.best_bid > 0 and self.best_ask > 0:
            return round((self.best_bid + self.best_ask) / 2.0, 2)
        if self.mark_price > 0:
            return self.mark_price
        if self.klines_m1:
            return float(self.klines_m1[-1]["close"])
        return 2680.0

    def get_spread(self) -> Dict[str, Any]:
        if self.best_bid > 0 and self.best_ask > 0:
            spread_usd = round(self.best_ask - self.best_bid, 2)
            spread_pct = round((spread_usd / self.best_bid) * 100.0, 4)
            return {
                "spread_usd": spread_usd,
                "spread_pct": spread_pct,
                "acceptable": spread_usd <= DEFAULT_CONFIG.max_allowed_spread_usd
            }
        return {"spread_usd": 0.02, "spread_pct": 0.001, "acceptable": True}

    def is_data_stale(self, max_seconds: float = 5.0) -> bool:
        if self.last_update_ts <= 0:
            return False
        return (time.time() - self.last_update_ts) > max_seconds

    def load_initial_klines(self, klines_raw: List[List[Any]], timeframe: str = "1m"):
        parsed = []
        for k in klines_raw:
            parsed.append({
                "time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })
        if timeframe == "1m":
            self.klines_m1 = parsed[-600:]
            self.last_update_ts = time.time()
            self._synthesize_higher_timeframes()
        elif timeframe == "5m":
            self.klines_m5 = parsed[-500:]
            self.last_update_ts = time.time()
        elif timeframe == "15m":
            self.klines_m15 = parsed[-200:]
        elif timeframe == "1h":
            self.klines_h1 = parsed[-300:]
            self.last_update_ts = time.time()

    def update_kline_stream(self, k: Dict[str, Any], interval: str = "1m"):
        candle = {
            "time": int(k.get("t", 0)),
            "open": float(k.get("o", 0)),
            "high": float(k.get("h", 0)),
            "low": float(k.get("l", 0)),
            "close": float(k.get("c", 0)),
            "volume": float(k.get("v", 0))
        }
        is_closed = k.get("x", False)
        if interval == "5m":
            target = self.klines_m5
            max_len = 500
        elif interval == "1h":
            target = self.klines_h1
            max_len = 300
        else:
            target = self.klines_m1
            max_len = 600

        if not target:
            target.append(candle)
        else:
            if target[-1]["time"] == candle["time"]:
                target[-1] = candle
            else:
                target.append(candle)
                if len(target) > max_len:
                    target.pop(0)

        self.last_update_ts = time.time()
        if interval == "1m" and is_closed:
            self._synthesize_higher_timeframes()

    def _synthesize_higher_timeframes(self):
        if len(self.klines_m1) < 15:
            return
        # Synthesize M5 from M1
        self.klines_m5 = self._aggregate_candles(self.klines_m1, 5)
        # Synthesize M15 from M1
        self.klines_m15 = self._aggregate_candles(self.klines_m1, 15)
        # Synthesize H1 from M1
        self.klines_h1 = self._aggregate_candles(self.klines_m1, 60)

    @staticmethod
    def _aggregate_candles(candles: List[Dict[str, Any]], interval_min: int) -> List[Dict[str, Any]]:
        aggregated = []
        interval_ms = interval_min * 60 * 1000
        current_bucket = None

        for c in candles:
            bucket_time = (c["time"] // interval_ms) * interval_ms
            if current_bucket is None or current_bucket["time"] != bucket_time:
                if current_bucket is not None:
                    aggregated.append(current_bucket)
                current_bucket = {
                    "time": bucket_time,
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                    "volume": c["volume"]
                }
            else:
                current_bucket["high"] = max(current_bucket["high"], c["high"])
                current_bucket["low"] = min(current_bucket["low"], c["low"])
                current_bucket["close"] = c["close"]
                current_bucket["volume"] += c["volume"]

        if current_bucket is not None:
            aggregated.append(current_bucket)
        return aggregated

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        if len(prices) < period + 1:
            return [50.0] * len(prices)
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [max(0.0, d) for d in deltas]
        losses = [abs(min(0.0, d)) for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi_series = [50.0] * period
        if avg_loss == 0:
            rsi_series.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_series.append(round(100.0 - (100.0 / (1.0 + rs)), 2))
            
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi_series.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_series.append(round(100.0 - (100.0 / (1.0 + rs)), 2))
                
        return rsi_series

    @staticmethod
    def calculate_ema(values: List[float], period: int) -> List[float]:
        if len(values) < period:
            return []
        multiplier = 2.0 / (period + 1.0)
        ema = [sum(values[:period]) / period]
        for val in values[period:]:
            ema.append((val - ema[-1]) * multiplier + ema[-1])
        return ema

    @staticmethod
    def calculate_atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 1.2
        tr_list = []
        for i in range(1, len(candles)):
            h = candles[i]["high"]
            l = candles[i]["low"]
            pc = candles[i-1]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        if len(tr_list) < period:
            return sum(tr_list) / max(1, len(tr_list))
        # Wilder's smoothing ATR
        atr = sum(tr_list[:period]) / period
        for tr in tr_list[period:]:
            atr = (atr * (period - 1) + tr) / period
        return round(atr, 2)

    def get_atr_m1(self) -> float:
        return self.calculate_atr(self.klines_m1, 14)

    def get_atr_m5(self) -> float:
        return self.calculate_atr(self.klines_m5, 14)

    @staticmethod
    def calculate_supertrend(candles: List[Dict[str, Any]], period: int = 10, multiplier: float = 2.5):
        n = len(candles)
        if n < period + 1:
            return [0.0] * n, [1] * n
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        
        tr = [highs[0] - lows[0]]
        for i in range(1, n):
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        atr = [0.0] * n
        atr[period-1] = sum(tr[:period]) / period
        for i in range(period, n):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

        st = [0.0] * n
        direction = [1] * n
        upper = [0.0] * n
        lower = [0.0] * n
        for i in range(period, n):
            hl2 = (highs[i] + lows[i]) / 2.0
            basic_upper = hl2 + multiplier * atr[i]
            basic_lower = hl2 - multiplier * atr[i]
            lower[i] = basic_lower if basic_lower > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]
            upper[i] = basic_upper if basic_upper < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
            if closes[i] > upper[i-1]:
                direction[i] = 1
            elif closes[i] < lower[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
            st[i] = lower[i] if direction[i] == 1 else upper[i]
        return st, direction

    def get_current_session(self) -> Dict[str, Any]:
        """
        Calculates session based on UTC timestamp.
        Also displays local Tashkent time (UTC+5).
        """
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour + now_utc.minute / 60.0

        # Institutional Execution Window (07:00 - 21:00 UTC)
        is_window_active = (DEFAULT_CONFIG.session_start_hour_utc <= now_utc.hour < DEFAULT_CONFIG.session_end_hour_utc)

        # Session intervals (UTC)
        is_overlap = (13.5 <= hour < 16.5)
        is_ny = (16.5 <= hour < 20.0)
        is_london = (8.0 <= hour < 13.5)
        is_asia = (hour >= 20.0 or hour < 8.0)

        session_name = "ASIA"
        if is_overlap:
            session_name = "LONDON_NY_OVERLAP"
        elif is_ny:
            session_name = "NEW_YORK"
        elif is_london:
            session_name = "LONDON"
        elif is_asia:
            session_name = "ASIA"

        tashkent_hour = (now_utc.hour + 5) % 24
        tashkent_time_str = f"{tashkent_hour:02d}:{now_utc.minute:02d} Tashkent"
        utc_time_str = f"{now_utc.hour:02d}:{now_utc.minute:02d} UTC"

        is_allowed = is_window_active

        return {
            "session": session_name,
            "is_allowed": is_allowed,
            "is_window_active": is_window_active,
            "utc_time": utc_time_str,
            "tashkent_time": tashkent_time_str,
            "is_overlap": is_overlap,
            "volatility_expected": "HIGH" if is_overlap else ("NORMAL" if (is_london or is_ny) else "LOW")
        }

    def get_market_summary(self) -> Dict[str, Any]:
        spread_info = self.get_spread()
        session_info = self.get_current_session()
        current_price = self.get_current_price()
        atr_m1 = self.get_atr_m1()
        
        # 24h Volume approximation from klines or 1m volume sum
        m1_vol = sum(c["volume"] for c in self.klines_m1[-60:]) if self.klines_m1 else 0.0

        return {
            "symbol": DEFAULT_CONFIG.symbol,
            "displaySymbol": DEFAULT_CONFIG.display_symbol,
            "price": current_price,
            "bid": self.best_bid,
            "ask": self.best_ask,
            "spread": spread_info["spread_usd"],
            "spreadPct": spread_info["spread_pct"],
            "spreadAcceptable": spread_info["acceptable"],
            "markPrice": self.mark_price or current_price,
            "fundingRate": self.funding_rate,
            "atrM1": atr_m1,
            "atrM5": self.get_atr_m5(),
            "volume1h": round(m1_vol, 2),
            "session": session_info["session"],
            "sessionAllowed": session_info["is_allowed"],
            "sessionTashkent": session_info["tashkent_time"],
            "volatility": session_info["volatility_expected"],
            "isStale": self.is_data_stale()
        }
