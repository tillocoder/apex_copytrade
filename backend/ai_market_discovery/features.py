"""
APEX Quantitative Feature Engine
Computes 100-300+ measurable features grouped into 10 factor families:
1. TREND
2. MOMENTUM
3. VOLATILITY
4. VOLUME
5. PRICE ACTION
6. MARKET STRUCTURE
7. SUPPORT / RESISTANCE
8. LIQUIDITY
9. DERIVATIVES DATA
10. CROSS-ASSET INTELLIGENCE

Pure Python (zero external dependencies), deterministic, zero-lookahead.
"""

import math
from typing import Dict, List, Any, Optional, Tuple


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0 and not math.isnan(b) else default


def _sma(values: List[float], period: int) -> List[float]:
    out = [float("nan")] * len(values)
    if len(values) < period:
        return out
    s = sum(values[:period])
    out[period - 1] = s / period
    for i in range(period, len(values)):
        s += values[i] - values[i - period]
        out[i] = s / period
    return out


def _ema(values: List[float], period: int) -> List[float]:
    out = [float("nan")] * len(values)
    if len(values) < period:
        return out
    k = 2.0 / (period + 1.0)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = values[i] * k + current * (1.0 - k)
        out[i] = current
    return out


def _rsi(values: List[float], period: int = 14) -> List[float]:
    out = [float("nan")] * len(values)
    if len(values) <= period:
        return out
    gains, losses = [], []
    for i in range(1, len(values)):
        d = values[i] - values[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        idx = i + 1
        out[idx] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return out


def _atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    tr = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return _ema(tr, period)


class FeatureEngine:
    def __init__(self):
        pass

    def compute_symbol_features(self, symbol_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes the complete factor profile for a single symbol across timeframes.
        Returns a structured dictionary of 10 factor families.
        """
        symbol = symbol_bundle["symbol"]
        tfs = symbol_bundle["timeframes"]
        deriv = symbol_bundle.get("derivatives", {})
        current_p = symbol_bundle.get("current_price", 0.0)

        # Primary series for detailed analysis: H1 (primary) and M15 (setup development)
        h1 = tfs.get("1h", [])
        m15 = tfs.get("15m", [])
        h4 = tfs.get("4h", [])
        m5 = tfs.get("5m", [])
        m1 = tfs.get("1m", [])

        # Default fallback candle if missing
        active_series = m15 if len(m15) >= 30 else (h1 if len(h1) >= 30 else [])
        if not active_series:
            return {"error": "Insufficient market data"}

        closes = [c["close"] for c in active_series]
        highs = [c["high"] for c in active_series]
        lows = [c["low"] for c in active_series]
        opens = [c["open"] for c in active_series]
        vols = [c["volume"] for c in active_series]
        tb_vols = [c.get("taker_buy_volume", c["volume"] * 0.5) for c in active_series]

        n = len(closes)
        idx = n - 1
        p = closes[idx] if current_p <= 0 else current_p

        # ── 1. TREND FAMILY (27 Features) ───────────────────────────────────
        ema9 = _ema(closes, 9)
        ema21 = _ema(closes, 21)
        ema50 = _ema(closes, 50)
        ema100 = _ema(closes, 100) if n >= 100 else _ema(closes, min(50, n))
        ema200 = _ema(closes, 200) if n >= 200 else _ema(closes, min(100, n))

        sma20 = _sma(closes, 20)
        sma50 = _sma(closes, 50)
        sma100 = _sma(closes, 100) if n >= 100 else _sma(closes, min(50, n))
        sma200 = _sma(closes, 200) if n >= 200 else _sma(closes, min(100, n))

        e9 = ema9[idx]
        e21 = ema21[idx]
        e50 = ema50[idx]
        e100 = ema100[idx] if not math.isnan(ema100[idx]) else e50
        e200 = ema200[idx] if not math.isnan(ema200[idx]) else e50

        s20 = sma20[idx] if not math.isnan(sma20[idx]) else p
        s50 = sma50[idx] if not math.isnan(sma50[idx]) else p
        s100 = sma100[idx] if not math.isnan(sma100[idx]) else p
        s200 = sma200[idx] if not math.isnan(sma200[idx]) else p

        # Slopes (% change over 3 bars)
        slope_e9 = _safe_div(e9 - ema9[max(0, idx - 3)], ema9[max(0, idx - 3)]) * 100.0
        slope_e21 = _safe_div(e21 - ema21[max(0, idx - 3)], ema21[max(0, idx - 3)]) * 100.0
        slope_e50 = _safe_div(e50 - ema50[max(0, idx - 3)], ema50[max(0, idx - 3)]) * 100.0
        slope_e100 = _safe_div(e100 - ema100[max(0, idx - 3)], ema100[max(0, idx - 3)]) * 100.0
        slope_e200 = _safe_div(e200 - ema200[max(0, idx - 3)], ema200[max(0, idx - 3)]) * 100.0
        prev_slope_e21 = _safe_div(ema21[max(0, idx - 3)] - ema21[max(0, idx - 6)], ema21[max(0, idx - 6)]) * 100.0 if idx >= 6 else slope_e21
        trend_accel = slope_e21 - prev_slope_e21

        # EMA & SMA alignments
        bullish_stack = e9 > e21 > e50 > e200
        bearish_stack = e9 < e21 < e50 < e200
        ema_alignment = "BULLISH_STACK" if bullish_stack else ("BEARISH_STACK" if bearish_stack else "MIXED")
        sma_alignment = "BULLISH_STACK" if s20 > s50 > s100 > s200 else ("BEARISH_STACK" if s20 < s50 < s100 < s200 else "MIXED")

        # ADX / DI+ / DI-
        atr14 = _atr(highs, lows, closes, 14)
        plus_dm, minus_dm = [], []
        for i in range(1, n):
            up = highs[i] - highs[i - 1]
            down = lows[i - 1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0.0)
            minus_dm.append(down if down > up and down > 0 else 0.0)
        smooth_plus = _ema(plus_dm, 14)
        smooth_minus = _ema(minus_dm, 14)
        cur_atr = atr14[idx] if not math.isnan(atr14[idx]) and atr14[idx] > 0 else 1.0
        di_plus = _safe_div(smooth_plus[-1] if smooth_plus else 0.0, cur_atr) * 100.0
        di_minus = _safe_div(smooth_minus[-1] if smooth_minus else 0.0, cur_atr) * 100.0
        dx = _safe_div(abs(di_plus - di_minus), di_plus + di_minus) * 100.0

        # Trend persistence
        persistence = 0
        is_above = p >= e50
        for i in range(idx, -1, -1):
            if (closes[i] >= ema50[i]) == is_above:
                persistence += 1
            else:
                break

        # Higher Highs / Lower Lows count in last 20 bars
        window_20 = range(max(1, idx - 19), idx + 1)
        hh_count = sum(1 for i in window_20 if highs[i] > highs[i - 1])
        hl_count = sum(1 for i in window_20 if lows[i] > lows[i - 1])
        lh_count = sum(1 for i in window_20 if highs[i] < highs[i - 1])
        ll_count = sum(1 for i in window_20 if lows[i] < lows[i - 1])

        trend_exhaustion = (dx > 45.0 and abs(slope_e21) < abs(prev_slope_e21)) or (persistence > 35 and abs(slope_e21) < 0.05)

        trend_family = {
            "ema9": round(e9, 2),
            "ema21": round(e21, 2),
            "ema50": round(e50, 2),
            "ema100": round(e100, 2),
            "ema200": round(e200, 2),
            "sma20": round(s20, 2),
            "sma50": round(s50, 2),
            "sma100": round(s100, 2),
            "sma200": round(s200, 2),
            "price_to_ema9_pct": round(_safe_div(p - e9, e9) * 100.0, 3),
            "price_to_ema21_pct": round(_safe_div(p - e21, e21) * 100.0, 3),
            "price_to_ema50_pct": round(_safe_div(p - e50, e50) * 100.0, 3),
            "price_to_ema100_pct": round(_safe_div(p - e100, e100) * 100.0, 3),
            "price_to_ema200_pct": round(_safe_div(p - e200, e200) * 100.0, 3),
            "price_to_sma20_pct": round(_safe_div(p - s20, s20) * 100.0, 3),
            "price_to_sma50_pct": round(_safe_div(p - s50, s50) * 100.0, 3),
            "ema9_slope_pct": round(slope_e9, 3),
            "ema21_slope_pct": round(slope_e21, 3),
            "ema50_slope_pct": round(slope_e50, 3),
            "ema_alignment": ema_alignment,
            "sma_alignment": sma_alignment,
            "adx_14": round(dx, 1),
            "di_plus": round(di_plus, 1),
            "di_minus": round(di_minus, 1),
            "trend_persistence_bars": persistence,
            "trend_acceleration_pct": round(trend_accel, 3),
            "trend_exhaustion": trend_exhaustion,
            "higher_highs_count": hh_count,
            "lower_lows_count": ll_count,
            "trend_direction": "BULLISH" if p > e50 and slope_e50 > 0 else ("BEARISH" if p < e50 and slope_e50 < 0 else "SIDEWAYS")
        }

        # ── 2. MOMENTUM FAMILY (16 Features) ─────────────────────────────────
        rsi14 = _rsi(closes, 14)
        cur_rsi = rsi14[idx] if not math.isnan(rsi14[idx]) else 50.0
        prev_rsi = rsi14[max(0, idx - 3)] if not math.isnan(rsi14[max(0, idx - 3)]) else 50.0
        rsi_slope = round(cur_rsi - prev_rsi, 2)

        recent_rsis = [r for r in rsi14[max(0, idx - 60):idx + 1] if not math.isnan(r)]
        rsi_pctile = round(sum(1 for r in recent_rsis if r <= cur_rsi) / len(recent_rsis) * 100.0, 1) if recent_rsis else 50.0

        stoch_k = 50.0
        if len(recent_rsis) >= 14:
            rsi_window = recent_rsis[-14:]
            min_r, max_r = min(rsi_window), max(rsi_window)
            stoch_k = _safe_div(cur_rsi - min_r, max_r - min_r) * 100.0

        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        macd_line = [ema12[i] - ema26[i] for i in range(n)]
        macd_signal = _ema(macd_line, 9)
        cur_macd = macd_line[idx] if not math.isnan(macd_line[idx]) else 0.0
        cur_sig = macd_signal[idx] if not math.isnan(macd_signal[idx]) else 0.0
        cur_hist = cur_macd - cur_sig
        prev_m = macd_line[idx - 1] if idx > 0 and not math.isnan(macd_line[idx - 1]) else 0.0
        prev_s = macd_signal[idx - 1] if idx > 0 and not math.isnan(macd_signal[idx - 1]) else 0.0
        prev_hist = prev_m - prev_s
        hist_slope = cur_hist - prev_hist if not math.isnan(cur_hist - prev_hist) else 0.0

        roc9 = _safe_div(p - closes[max(0, idx - 9)], closes[max(0, idx - 9)]) * 100.0
        roc21 = _safe_div(p - closes[max(0, idx - 21)], closes[max(0, idx - 21)]) * 100.0
        mom_accel = roc9 - roc21

        bullish_div = False
        bearish_div = False
        if idx >= 10:
            if lows[idx] < min(lows[idx - 10:idx]) and cur_rsi > min(rsi14[idx - 10:idx]):
                bullish_div = True
            if highs[idx] > max(highs[idx - 10:idx]) and cur_rsi < max(rsi14[idx - 10:idx]):
                bearish_div = True

        momentum_family = {
            "rsi_14": round(cur_rsi, 1),
            "rsi_slope_3bars": rsi_slope,
            "rsi_percentile": rsi_pctile,
            "stoch_rsi_k": round(stoch_k, 1),
            "stoch_rsi_d": round(stoch_k * 0.95, 1), # smoothed estimate
            "macd_line": round(cur_macd, 2),
            "macd_signal": round(cur_sig, 2),
            "macd_histogram": round(cur_hist, 2),
            "macd_histogram_slope": round(hist_slope, 2),
            "roc_9": round(roc9, 2),
            "roc_21": round(roc21, 2),
            "momentum_acceleration": round(mom_accel, 2),
            "momentum_deceleration": abs(roc9) < abs(roc21),
            "momentum_divergence": "BULLISH_DIV" if bullish_div else ("BEARISH_DIV" if bearish_div else "NONE"),
            "rsi_overbought": cur_rsi >= 70.0,
            "rsi_oversold": cur_rsi <= 30.0
        }

        # ── 3. VOLATILITY FAMILY (17 Features) ───────────────────────────────
        atr_val = atr14[idx] if not math.isnan(atr14[idx]) else (p * 0.01)
        atr_pct = _safe_div(atr_val, p) * 100.0
        recent_atrs = [a for a in atr14[max(0, idx - 60):idx + 1] if not math.isnan(a)]
        atr_pctile = round(sum(1 for a in recent_atrs if a <= atr_val) / len(recent_atrs) * 100.0, 1) if recent_atrs else 50.0
        atr_sma20 = sum(recent_atrs[-20:]) / min(20, len(recent_atrs)) if recent_atrs else atr_val
        atr_expansion = atr_val > atr_sma20
        atr_contraction = atr_val < (atr_sma20 * 0.85)

        mid_bb = s20
        bb_window = closes[max(0, idx - 19):idx + 1]
        std_bb = math.sqrt(sum((x - mid_bb) ** 2 for x in bb_window) / len(bb_window)) if len(bb_window) > 1 else (p * 0.01)
        upper_bb = mid_bb + 2.0 * std_bb
        lower_bb = mid_bb - 2.0 * std_bb
        bb_width_pct = _safe_div(upper_bb - lower_bb, mid_bb) * 100.0
        bb_percent_b = _safe_div(p - lower_bb, upper_bb - lower_bb)

        # Realized Volatility
        log_rets = [math.log(closes[i] / closes[i - 1]) for i in range(max(1, idx - 30), idx + 1)]
        mean_ret = sum(log_rets) / len(log_rets) if log_rets else 0.0
        realized_vol = math.sqrt(sum((r - mean_ret) ** 2 for r in log_rets) / len(log_rets)) * math.sqrt(365 * 96) * 100.0 if log_rets else 0.0

        c_range_cur = highs[idx] - lows[idx]
        range_expansion = c_range_cur > (1.5 * atr_val)
        range_compression = c_range_cur < (0.65 * atr_val)

        # Keltner Channel / Squeeze
        keltner_upper = e21 + 1.5 * atr_val
        keltner_lower = e21 - 1.5 * atr_val
        squeeze_active = (lower_bb > keltner_lower) and (upper_bb < keltner_upper)
        keltner_width_pct = _safe_div(keltner_upper - keltner_lower, e21) * 100.0

        volatility_family = {
            "atr": round(atr_val, 2),
            "atr_pct": round(atr_pct, 2),
            "atr_percentile": atr_pctile,
            "atr_expansion": atr_expansion,
            "atr_contraction": atr_contraction,
            "bb_upper": round(upper_bb, 2),
            "bb_mid": round(mid_bb, 2),
            "bb_lower": round(lower_bb, 2),
            "bb_width_pct": round(bb_width_pct, 2),
            "bb_percent_b": round(bb_percent_b, 3),
            "realized_volatility_annualized": round(realized_vol, 1),
            "volatility_percentile": atr_pctile,
            "range_expansion": range_expansion,
            "range_compression": range_compression,
            "keltner_width_pct": round(keltner_width_pct, 2),
            "squeeze_active": squeeze_active,
            "volatility_regime": "EXPANDING" if atr_expansion else "COMPRESSING"
        }

        # ── 4. VOLUME FAMILY (12 Features) ───────────────────────────────────
        cur_vol = vols[idx]
        vol_sma20 = sum(vols[max(0, idx - 19):idx + 1]) / min(20, idx + 1)
        vol_sma50 = sum(vols[max(0, idx - 49):idx + 1]) / min(50, idx + 1)
        rvol = _safe_div(cur_vol, vol_sma20, 1.0)
        tb_ratio = _safe_div(tb_vols[idx], cur_vol, 0.5)

        obv = 0.0
        for i in range(1, n):
            if closes[i] > closes[i - 1]:
                obv += vols[i]
            elif closes[i] < closes[i - 1]:
                obv -= vols[i]
        obv_slope = obv - (sum(vols[max(0, idx - 5):idx]) if idx >= 5 else 0.0)

        cum_vol = sum(vols[max(0, idx - 49):idx + 1])
        cum_pv = sum(closes[i] * vols[i] for i in range(max(0, idx - 49), idx + 1))
        vwap = _safe_div(cum_pv, cum_vol, p)
        vwap_dist = _safe_div(p - vwap, vwap) * 100.0

        volume_family = {
            "current_volume": round(cur_vol, 1),
            "volume_sma20": round(vol_sma20, 1),
            "volume_sma50": round(vol_sma50, 1),
            "relative_volume_rvol": round(rvol, 2),
            "taker_buy_ratio": round(tb_ratio, 3),
            "volume_ratio_buy_sell": round(_safe_div(tb_ratio, 1.0 - tb_ratio + 1e-6, 1.0), 2),
            "volume_spike": rvol >= 2.0,
            "volume_anomaly_z": round(_safe_div(cur_vol - vol_sma20, vol_sma20), 2),
            "obv": round(obv, 1),
            "obv_slope_5bars": round(obv_slope, 1),
            "vwap": round(vwap, 2),
            "vwap_distance_pct": round(vwap_dist, 2),
            "volume_trend": "ACCUMULATION" if rvol > 1.2 and closes[idx] > opens[idx] else ("DISTRIBUTION" if rvol > 1.2 and closes[idx] < opens[idx] else "NEUTRAL")
        }

        # ── 5. PRICE ACTION FAMILY (18 Features) ─────────────────────────────
        c_open = opens[idx]
        c_high = highs[idx]
        c_low = lows[idx]
        c_close = closes[idx]
        c_range = c_high - c_low
        c_body = abs(c_close - c_open)
        c_upper_wick = c_high - max(c_open, c_close)
        c_lower_wick = min(c_open, c_close) - c_low

        prev_open = opens[idx - 1]
        prev_close = closes[idx - 1]
        prev_high = highs[idx - 1]
        prev_low = lows[idx - 1]

        is_bullish_engulf = (prev_close < prev_open) and (c_close > c_open) and (c_close >= prev_high) and (c_open <= prev_low)
        is_bearish_engulf = (prev_close > prev_open) and (c_close < c_open) and (c_close <= prev_low) and (c_open >= prev_high)
        is_pin_bar_bull = c_lower_wick >= 0.55 * c_range and c_body <= 0.25 * c_range
        is_pin_bar_bear = c_upper_wick >= 0.55 * c_range and c_body <= 0.25 * c_range
        is_displacement = c_body >= 1.8 * atr_val
        is_inside_bar = c_high <= prev_high and c_low >= prev_low
        is_breakout_candle = c_close > prev_high and rvol > 1.5
        is_failed_breakout = (c_high > prev_high) and (c_close < prev_high) and (c_upper_wick > c_body)
        is_retest_candle = (c_low <= prev_high <= c_high) and (c_close > prev_high)

        pattern = "NONE"
        if is_bullish_engulf: pattern = "BULLISH_ENGULFING"
        elif is_bearish_engulf: pattern = "BEARISH_ENGULFING"
        elif is_pin_bar_bull: pattern = "BULLISH_PIN_BAR"
        elif is_pin_bar_bear: pattern = "BEARISH_PIN_BAR"
        elif is_displacement: pattern = "DISPLACEMENT"
        elif is_inside_bar: pattern = "INSIDE_BAR"

        price_action_family = {
            "candle_pattern": pattern,
            "body_to_range_ratio": round(_safe_div(c_body, c_range), 2),
            "upper_wick_ratio": round(_safe_div(c_upper_wick, c_range), 2),
            "lower_wick_ratio": round(_safe_div(c_lower_wick, c_range), 2),
            "wick_to_body_ratio": round(_safe_div(c_upper_wick + c_lower_wick, c_body + 1e-6), 2),
            "is_displacement": is_displacement,
            "is_rejection": (c_upper_wick >= 0.45 * c_range) or (c_lower_wick >= 0.45 * c_range),
            "is_inside_bar": is_inside_bar,
            "is_bullish_engulfing": is_bullish_engulf,
            "is_bearish_engulfing": is_bearish_engulf,
            "is_bullish_pin_bar": is_pin_bar_bull,
            "is_bearish_pin_bar": is_pin_bar_bear,
            "is_breakout_candle": is_breakout_candle,
            "is_failed_breakout": is_failed_breakout,
            "is_retest_candle": is_retest_candle,
            "range_to_atr_ratio": round(_safe_div(c_range, atr_val), 2),
            "large_candle_anomaly": c_range > (2.5 * atr_val),
            "compression_state": is_inside_bar or (c_range < 0.6 * atr_val)
        }

        # ── 6. MARKET STRUCTURE FAMILY (14 Features) ─────────────────────────
        swing_highs, swing_lows = [], []
        for i in range(2, n - 2):
            if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
                swing_highs.append({"index": i, "price": highs[i]})
            if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
                swing_lows.append({"index": i, "price": lows[i]})

        last_sh = swing_highs[-1]["price"] if swing_highs else c_high
        last_sl = swing_lows[-1]["price"] if swing_lows else c_low
        prev_sh = swing_highs[-2]["price"] if len(swing_highs) >= 2 else last_sh
        prev_sl = swing_lows[-2]["price"] if len(swing_lows) >= 2 else last_sl

        is_hh = last_sh > prev_sh
        is_hl = last_sl > prev_sl
        is_lh = last_sh < prev_sh
        is_ll = last_sl < prev_sl

        bos = (p > last_sh and is_hh) or (p < last_sl and is_ll)
        choch = (p < last_sl and is_hh) or (p > last_sh and is_ll)
        sh_age = (idx - swing_highs[-1]["index"]) if swing_highs else 0
        sl_age = (idx - swing_lows[-1]["index"]) if swing_lows else 0

        structure_family = {
            "recent_swing_high": round(last_sh, 2),
            "recent_swing_low": round(last_sl, 2),
            "prev_swing_high": round(prev_sh, 2),
            "prev_swing_low": round(prev_sl, 2),
            "is_higher_high": is_hh,
            "is_higher_low": is_hl,
            "is_lower_high": is_lh,
            "is_lower_low": is_ll,
            "bos_detected": bos,
            "choch_detected": choch,
            "structure_strength": round(75.0 if (is_hh and is_hl) or (is_lh and is_ll) else 45.0, 1),
            "structure_age_bars": min(sh_age, sl_age),
            "dist_to_swing_high_pct": round(_safe_div(last_sh - p, p) * 100.0, 2),
            "dist_to_swing_low_pct": round(_safe_div(p - last_sl, p) * 100.0, 2),
            "structure_state": "HIGHER_HIGHS_HIGHER_LOWS" if is_hh and is_hl else ("LOWER_HIGHS_LOWER_LOWS" if is_lh and is_ll else "COMPLEX_CONSOLIDATION")
        }

        # ── 7. SUPPORT / RESISTANCE FAMILY (14 Features) ─────────────────────
        all_levels = [sh["price"] for sh in swing_highs[-5:]] + [sl["price"] for sl in swing_lows[-5:]]
        resistances = sorted([lvl for lvl in all_levels if lvl > p])
        supports = sorted([lvl for lvl in all_levels if lvl < p], reverse=True)

        nearest_res = resistances[0] if resistances else upper_bb
        nearest_sup = supports[0] if supports else lower_bb

        dist_res_atr = round(_safe_div(nearest_res - p, atr_val), 2)
        dist_sup_atr = round(_safe_div(p - nearest_sup, atr_val), 2)
        dist_res_pct = round(_safe_div(nearest_res - p, p) * 100.0, 2)
        dist_sup_pct = round(_safe_div(p - nearest_sup, p) * 100.0, 2)

        sr_family = {
            "nearest_resistance": round(nearest_res, 2),
            "nearest_support": round(nearest_sup, 2),
            "dist_to_resistance_atr": dist_res_atr,
            "dist_to_support_atr": dist_sup_atr,
            "dist_to_resistance_pct": dist_res_pct,
            "dist_to_support_pct": dist_sup_pct,
            "major_swing_high_level": round(max(highs[max(0, idx - 50):idx + 1]), 2),
            "major_swing_low_level": round(min(lows[max(0, idx - 50):idx + 1]), 2),
            "volume_poc_level": round(vwap, 2),
            "breakout_level": round(last_sh, 2),
            "retest_level": round(last_sl, 2),
            "resistance_touches": len([h for h in highs[-20:] if abs(h - nearest_res) <= 0.5 * atr_val]),
            "support_touches": len([l for l in lows[-20:] if abs(l - nearest_sup) <= 0.5 * atr_val]),
            "breakout_probability_context": "HIGH_IF_VOLUME_EXPANDS" if dist_res_atr < 0.8 and rvol > 1.3 else "STANDARD_RANGE_CONTAINED"
        }

        # ── 8. LIQUIDITY FAMILY (11 Features) ────────────────────────────────
        eqh_detected = False
        eql_detected = False
        if len(swing_highs) >= 2:
            if abs(swing_highs[-1]["price"] - swing_highs[-2]["price"]) / p <= 0.0008:
                eqh_detected = True
        if len(swing_lows) >= 2:
            if abs(swing_lows[-1]["price"] - swing_lows[-2]["price"]) / p <= 0.0008:
                eql_detected = True

        bullish_sweep = (c_low < last_sl) and (c_close > last_sl)
        bearish_sweep = (c_high > last_sh) and (c_close < last_sh)
        stop_run = (c_low < last_sl and c_close > c_open) or (c_high > last_sh and c_close < c_open)

        liquidity_family = {
            "equal_highs_detected": eqh_detected,
            "equal_lows_detected": eql_detected,
            "recent_swing_liquidity_high": round(last_sh, 2),
            "recent_swing_liquidity_low": round(last_sl, 2),
            "bullish_liquidity_sweep": bullish_sweep,
            "bearish_liquidity_sweep": bearish_sweep,
            "stop_run_detected": stop_run,
            "failed_breakout_trap": is_failed_breakout,
            "reclaim_after_sweep": (bullish_sweep and c_close >= e9) or (bearish_sweep and c_close <= e9),
            "liquidity_density_score": round(80.0 if eqh_detected or eql_detected else 40.0, 1),
            "liquidity_event": "BULLISH_SWEEP_RECLAIM" if bullish_sweep else ("BEARISH_SWEEP_RECLAIM" if bearish_sweep else "NORMAL_FLOW")
        }

        # ── 9. DERIVATIVES FAMILY (10 Features) ──────────────────────────────
        def _d_val(v):
            return v.get("value") if isinstance(v, dict) else v

        f_rate = _d_val(deriv.get("funding_rate"))
        f_change = _d_val(deriv.get("funding_change_24h"))
        oi_val = _d_val(deriv.get("open_interest"))
        oi_notional = _d_val(deriv.get("open_interest_notional"))
        ls_ratio = _d_val(deriv.get("long_short_ratio"))
        basis = _d_val(deriv.get("basis") or deriv.get("basis_annualized_pct"))

        derivatives_family = {
            "funding_rate": f_rate,
            "funding_change_24h": f_change,
            "open_interest": oi_val,
            "open_interest_notional": oi_notional,
            "oi_change_24h_pct": _d_val(deriv.get("oi_change_24h_pct")),
            "oi_acceleration": (f_change or 0.0) > 0 and (oi_val or 0.0) > 0,
            "long_short_ratio": ls_ratio,
            "basis_bps": basis,
            "futures_premium_pct": round((basis / 100.0) if basis else 0.0, 3),
            "derivatives_sentiment": "LONG_CROWDED" if (ls_ratio or 1.0) > 1.8 else ("SHORT_CROWDED" if (ls_ratio or 1.0) < 0.7 else "BALANCED")
        }

        # ── 10. MULTI-TIMEFRAME SNAPSHOT (12 Features) ───────────────────────
        def tf_state(series):
            if not series or len(series) < 10:
                return "NEUTRAL"
            c = [x["close"] for x in series]
            e20 = _ema(c, 20)[-1]
            e50 = _ema(c, 50)[-1]
            last_close = c[-1]
            if last_close > e20 > e50:
                return "BULLISH"
            elif last_close < e20 < e50:
                return "BEARISH"
            return "CONSOLIDATION"

        h4_s = tf_state(h4)
        h1_s = tf_state(h1)
        m15_s = tf_state(m15)
        m5_s = tf_state(m5)
        m1_s = tf_state(m1)

        bull_tf_count = sum(1 for s in [h4_s, h1_s, m15_s, m5_s, m1_s] if s == "BULLISH")
        bear_tf_count = sum(1 for s in [h4_s, h1_s, m15_s, m5_s, m1_s] if s == "BEARISH")
        agreement_score = round(max(bull_tf_count, bear_tf_count) / 5.0 * 100.0, 1)

        htf_align = "BULLISH_ALIGNED" if h4_s == "BULLISH" and h1_s == "BULLISH" else ("BEARISH_ALIGNED" if h4_s == "BEARISH" and h1_s == "BEARISH" else "CONFLICTED")

        mtf_summary = {
            "H4": h4_s,
            "H1": h1_s,
            "M15": m15_s,
            "M5": m5_s,
            "M1": m1_s,
            "h4_trend": h4_s,
            "h1_trend": h1_s,
            "m15_trend": m15_s,
            "m5_trend": m5_s,
            "m1_trend": m1_s,
            "mtf_agreement_score": agreement_score,
            "htf_alignment": htf_align
        }

        def _clean_node(obj):
            if isinstance(obj, dict):
                return {k: _clean_node(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_clean_node(x) for x in obj]
            elif isinstance(obj, float):
                return None if math.isnan(obj) or math.isinf(obj) else obj
            return obj

        raw_result = {
            "symbol": symbol,
            "current_price": p,
            "timeframe_analyzed": "15m",
            "trend": trend_family,
            "momentum": momentum_family,
            "volatility": volatility_family,
            "volume": volume_family,
            "price_action": price_action_family,
            "market_structure": structure_family,
            "support_resistance": sr_family,
            "liquidity": liquidity_family,
            "derivatives": derivatives_family,
            "multi_timeframe": mtf_summary
        }
        return _clean_node(raw_result)

    def compute_cross_asset_features(self, universe_features: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes Cross-Asset Intelligence across BTCUSDT, ETHUSDT, SOLUSDT.
        Calculates momentum, relative strength, correlation, and market confirmation.
        """
        btc = universe_features.get("BTCUSDT", {})
        eth = universe_features.get("ETHUSDT", {})
        sol = universe_features.get("SOLUSDT", {})

        btc_p = btc.get("current_price", 1.0)
        eth_p = eth.get("current_price", 1.0)
        sol_p = sol.get("current_price", 1.0)

        btc_roc = btc.get("momentum", {}).get("roc_21", 0.0)
        eth_roc = eth.get("momentum", {}).get("roc_21", 0.0)
        sol_roc = sol.get("momentum", {}).get("roc_21", 0.0)

        eth_btc_ratio = round(_safe_div(eth_p, btc_p), 5)
        sol_btc_ratio = round(_safe_div(sol_p, btc_p), 6)

        # Performance ranking
        rankings = sorted([("BTC", btc_roc), ("ETH", eth_roc), ("SOL", sol_roc)], key=lambda x: x[1], reverse=True)
        strongest = rankings[0][0]
        weakest = rankings[-1][0]

        # Broad Market State
        bull_count = sum(1 for roc in [btc_roc, eth_roc, sol_roc] if roc > 0.5)
        bear_count = sum(1 for roc in [btc_roc, eth_roc, sol_roc] if roc < -0.5)

        if bull_count == 3:
            market_state = "BROAD_RISK_ON_EXPANSION"
        elif bear_count == 3:
            market_state = "BROAD_RISK_OFF_LIQUIDATION"
        elif btc_roc > 0 and (eth_roc < 0 or sol_roc < 0):
            market_state = "BTC_DOMINANCE_ALT_LAG"
        elif abs(btc_roc) <= 0.8 and (eth_roc > 1.5 or sol_roc > 1.5):
            market_state = "ALTCOIN_ROTATION"
        else:
            market_state = "MIXED_DISPERSION"

        return {
            "btc_momentum_roc21": btc_roc,
            "eth_momentum_roc21": eth_roc,
            "sol_momentum_roc21": sol_roc,
            "eth_btc_ratio": eth_btc_ratio,
            "sol_btc_ratio": sol_btc_ratio,
            "relative_strength_leader": strongest,
            "relative_strength_laggard": weakest,
            "cross_asset_regime": market_state,
            "cross_asset_confirmation": "CONFIRMED_BULLISH" if bull_count == 3 else ("CONFIRMED_BEARISH" if bear_count == 3 else "SELECTIVE_DIVERGENT")
        }
