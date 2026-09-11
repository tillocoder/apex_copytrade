"""
Production Multi-Strategy Signal Engine.
ZERO LOOKAHEAD AUDITED:
- Strictly uses completed 1H candle i.
- Strictly uses last closed 4H candle: idx_4h = max(0, map_1h_to_4h[i] - 1).
"""
from typing import Optional, Dict, Any, List
from .config import ProductionConfig
from .market_data import MarketDataEngine

class MultiStrategySignalEngine:
    def __init__(self, cfg: ProductionConfig):
        self.cfg = cfg

    def evaluate_strategy_a(self, i: int, data: MarketDataEngine, symbol: str) -> Optional[Dict[str, Any]]:
        """Strategy A: 1H EMA Trend Pullback on BTC or ETH."""
        if i < self.cfg.market_data.min_warmup_bars:
            return None

        c = data.closes[i]
        o = data.opens[i]
        v = data.volumes[i]
        vol_ma = data.vol_ma20[i]
        atr = data.atr_1h[i]
        rsi = data.rsi_1h[i]
        e50_1h = data.ema50_1h[i]

        # Normalization filter
        atr_pct = (atr / c) * 100.0 if c > 0 else 0.0
        if atr_pct < self.cfg.strategy_a.min_atr_pct or atr_pct > self.cfg.strategy_a.max_atr_pct:
            return None

        # STRICT ZERO LOOKAHEAD 4H FILTER: last closed 4H bar
        idx_4h = max(0, data.map_1h_to_4h[i] - 1)
        if idx_4h < 50:
            return None
        cl_4h = data.closes_4h[idx_4h]
        e50_4h = data.ema50_4h[idx_4h]

        # Volume expansion confirmation
        if v < self.cfg.strategy_a.volume_multiplier * vol_ma:
            return None

        sl_dist = max(self.cfg.strategy_a.sl_atr_multiplier * atr, 0.002 * c)
        ts_ms = int(data.timestamps[i] * 1000)

        # Bullish Pullback: 4H trend UP, 1H RSI oversold pullback (<45), 1H price above 1H EMA50
        if cl_4h > e50_4h and rsi < self.cfg.strategy_a.rsi_pullback_long and c > e50_1h:
            sig_id = f"{symbol}_1H_{ts_ms}_STRATA_BUY"
            return {
                "id": sig_id, "symbol": symbol, "strategy": "A_EMA_Pullback",
                "side": "BUY", "bar": i, "timestamp": ts_ms, "close": c,
                "sl": c - sl_dist, "sl_dist": sl_dist,
                "tp1": c + self.cfg.strategy_a.tp1_atr_multiplier * atr,
                "tp2": c + self.cfg.strategy_a.tp2_atr_multiplier * atr,
                "reason": f"4H_e50_bull({cl_4h:.1f}>{e50_4h:.1f})_rsi({rsi:.1f}<45)_vol({v/vol_ma:.2f}x)"
            }

        # Bearish Pullback: 4H trend DOWN, 1H RSI overbought pullback (>55), 1H price below 1H EMA50
        if cl_4h < e50_4h and rsi > self.cfg.strategy_a.rsi_pullback_short and c < e50_1h:
            sig_id = f"{symbol}_1H_{ts_ms}_STRATA_SELL"
            return {
                "id": sig_id, "symbol": symbol, "strategy": "A_EMA_Pullback",
                "side": "SELL", "bar": i, "timestamp": ts_ms, "close": c,
                "sl": c + sl_dist, "sl_dist": sl_dist,
                "tp1": c - self.cfg.strategy_a.tp1_atr_multiplier * atr,
                "tp2": c - self.cfg.strategy_a.tp2_atr_multiplier * atr,
                "reason": f"4H_e50_bear({cl_4h:.1f}<{e50_4h:.1f})_rsi({rsi:.1f}>55)_vol({v/vol_ma:.2f}x)"
            }

        return None

    def evaluate_strategy_b(self, i: int, data: MarketDataEngine, symbol: str) -> Optional[Dict[str, Any]]:
        """Strategy B: 1H Donchian 48H Breakout on BTCUSDT."""
        if symbol != "BTCUSDT":
            return None

        lb = self.cfg.strategy_b.lookback_bars
        if i < lb + 50:
            return None

        c = data.closes[i]
        o = data.opens[i]
        v = data.volumes[i]
        vol_ma = data.vol_ma20[i]
        atr = data.atr_1h[i]
        e200_1h = data.ema200_1h[i]

        # Normalization filter
        atr_pct = (atr / c) * 100.0 if c > 0 else 0.0
        if atr_pct < self.cfg.strategy_b.min_atr_pct or atr_pct > self.cfg.strategy_b.max_atr_pct:
            return None

        # Volume expansion confirmation
        if v < self.cfg.strategy_b.volume_multiplier * vol_ma:
            return None

        # 48H High and Low of closed bars strictly before current bar
        hh = max(data.highs[i - lb : i])
        ll = min(data.lows[i - lb : i])

        sl_dist = max(self.cfg.strategy_b.sl_atr_multiplier * atr, 0.002 * c)
        ts_ms = int(data.timestamps[i] * 1000)

        # Bullish Breakout
        if c > hh and c > e200_1h and c > o:
            sig_id = f"{symbol}_1H_{ts_ms}_STRATB_BUY"
            return {
                "id": sig_id, "symbol": symbol, "strategy": "B_Donchian_48H",
                "side": "BUY", "bar": i, "timestamp": ts_ms, "close": c,
                "sl": c - sl_dist, "sl_dist": sl_dist,
                "tp1": c + self.cfg.strategy_b.tp1_atr_multiplier * atr,
                "tp2": c + self.cfg.strategy_b.tp2_atr_multiplier * atr,
                "reason": f"Donchian48H_HighBreak({c:.1f}>{hh:.1f})_e200({c:.1f}>{e200_1h:.1f})_vol({v/vol_ma:.2f}x)"
            }

        # Bearish Breakout
        if c < ll and c < e200_1h and c < o:
            sig_id = f"{symbol}_1H_{ts_ms}_STRATB_SELL"
            return {
                "id": sig_id, "symbol": symbol, "strategy": "B_Donchian_48H",
                "side": "SELL", "bar": i, "timestamp": ts_ms, "close": c,
                "sl": c + sl_dist, "sl_dist": sl_dist,
                "tp1": c - self.cfg.strategy_b.tp1_atr_multiplier * atr,
                "tp2": c - self.cfg.strategy_b.tp2_atr_multiplier * atr,
                "reason": f"Donchian48H_LowBreak({c:.1f}<{ll:.1f})_e200({c:.1f}<{e200_1h:.1f})_vol({v/vol_ma:.2f}x)"
            }

        return None
