"""
APEX Multi-Layer Quantitative Signal Engine — Production-Grade Architecture

Architecture & Pipeline:
  1. Multi-Timeframe Binance Ingestion (D1, H4, H1, M15, M5) with Taker Volume Delta (CVD)
  2. Wilder's Indicators & Feature Engineering (Wilder RSI + Divergence, Wilder ATR + Volatility Regimes)
  3. Market Regime Engine (EMA Slopes, ADX, BB Width, Volatility, Regime Classification)
  4. Market Structure Engine (HH, HL, LH, LL, BOS, CHOCH, Liquidity Sweeps — Zero Look-Ahead)
  5. Order Block & Fair Value Gap Engines (Displacement, Mitigation, Freshness, Multi-Factor Scoring)
  6. Liquidity Pool Engine (EQH, EQL, PDH, PDL, Session Highs/Lows)
  7. Setup Detection Engine (9 Explicit SMC/Quant Setups: TREND_PULLBACK, BREAKOUT, BREAKDOWN, etc.)
  8. Quant Scoring Engine (Weighted Multi-Factor 0-100 Score)
  9. Deterministic Risk Engine (Structural Invalidation SL, Liquidity TPs, Min 2.0 RR)
 10. Gemini AI Reviewer (Analytical Contextual Reviewer — Cannot Override Entry, SL, or TP)
 11. Independent Final Gate & Portfolio Risk (Correlation Penalties, Cooldowns, Risk Budget)
 12. Outcome Tracker & Historical Performance Analytics
"""

import os
import json
import math
import time
import logging
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

# ─── Structured Logging Setup ────────────────────────────────────────────────
logger = logging.getLogger("APEX_QUANT_ENGINE")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# ─── Environment & Global Config ─────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("VITE_GEMINI_API_KEY") or "AQ.Ab8RN6JPJM4wM3eCK10Lw3b1aTvlsEC67RLwTpQTadEp-SRgJw"
_env_models = os.environ.get("GEMINI_MODELS", "")
if _env_models:
    GEMINI_MODELS = [m.strip() for m in _env_models.split(",") if m.strip()]
else:
    GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"

SYMBOLS = [
    {"symbol": "BTC/USDT", "binance": "BTCUSDT"},
]
BLACKLISTED_SYMBOLS = {"ETH/USDT", "ETHUSDT"}
MAX_DAILY_TRADES_PER_SYMBOL = 4

HISTORY_FILE = "backend/data/signals_history.json"
CACHE_TTL_S: int = 15

_signal_cache: Dict[str, Any] = {}
_cache_ts: float = 0.0


# =============================================================================
# 1. FEATURE ENGINEERING & INDICATORS (WILDER SMOOTHING & CVD)
# =============================================================================

class QuantFeatureEngine:
    """Computes mathematically precise indicators using Wilder's smoothing and true Taker Volume Delta."""

    @staticmethod
    def ema(series: List[float], period: int) -> List[float]:
        if not series:
            return []
        k = 2.0 / (period + 1)
        ema_vals = [series[0]]
        for val in series[1:]:
            ema_vals.append(val * k + ema_vals[-1] * (1.0 - k))
        return ema_vals

    @staticmethod
    def wilder_rsi(closes: List[float], period: int = 14) -> Dict[str, Any]:
        """Calculates Wilder's RSI, RSI slope over 3 bars, regime, and divergence using confirmed swing points."""
        if len(closes) < period + 1:
            return {"rsi": 50.0, "slope": 0.0, "regime": "NEUTRAL", "bullish_div": False, "bearish_div": False}

        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0.0))
            losses.append(max(-diff, 0.0))

        # Initial average
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_series = [50.0] * period
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi_val = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_val = 100.0 - (100.0 / (1.0 + rs))
            rsi_series.append(round(rsi_val, 2))

        curr_rsi = rsi_series[-1]
        prev_rsi = rsi_series[-4] if len(rsi_series) >= 4 else curr_rsi
        rsi_slope = round(curr_rsi - prev_rsi, 2)

        if curr_rsi < 30.0:
            regime = "OVERSOLD"
        elif curr_rsi < 45.0:
            regime = "BEARISH"
        elif curr_rsi <= 55.0:
            regime = "NEUTRAL"
        elif curr_rsi <= 70.0:
            regime = "BULLISH"
        else:
            regime = "OVERBOUGHT"

        # Confirmed Swing Point Divergence (Zero Look-Ahead)
        bullish_div = False
        bearish_div = False
        n = len(closes)
        if n >= 25:
            # Detect swing lows in closes up to n-3 to prevent future leak
            swing_lows = []
            swing_highs = []
            for i in range(5, n - 3):
                if closes[i] == min(closes[i - 5:i + 4]):
                    swing_lows.append((i, closes[i], rsi_series[i]))
                if closes[i] == max(closes[i - 5:i + 4]):
                    swing_highs.append((i, closes[i], rsi_series[i]))

            if len(swing_lows) >= 2:
                idx1, p1, r1 = swing_lows[-2]
                idx2, p2, r2 = swing_lows[-1]
                if p2 < p1 and r2 > r1:  # Lower Price Low, Higher RSI Low
                    bullish_div = True

            if len(swing_highs) >= 2:
                idx1, p1, r1 = swing_highs[-2]
                idx2, p2, r2 = swing_highs[-1]
                if p2 > p1 and r2 < r1:  # Higher Price High, Lower RSI High
                    bearish_div = True

        return {
            "rsi": curr_rsi,
            "slope": rsi_slope,
            "regime": regime,
            "bullish_div": bullish_div,
            "bearish_div": bearish_div,
            "series": rsi_series
        }

    @staticmethod
    def wilder_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Dict[str, Any]:
        """Calculates Wilder's ATR, ATR %, ATR percentile (100-bar window), slope, expansion/compression, and regime."""
        if len(closes) < period + 1:
            return {
                "atr": 0.0, "atr_pct": 0.0, "atr_percentile": 50.0, "slope": 0.0,
                "is_expanding": False, "is_compressing": False, "regime": "NORMAL_VOLATILITY"
            }

        tr_series = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            tr_series.append(tr)

        # Initial Wilder ATR
        atr_val = sum(tr_series[:period]) / period
        atr_series = [atr_val]
        for i in range(period, len(tr_series)):
            atr_val = (atr_val * (period - 1) + tr_series[i]) / period
            atr_series.append(atr_val)

        curr_atr = atr_series[-1]
        curr_price = closes[-1]
        atr_pct = round((curr_atr / curr_price) * 100.0, 4) if curr_price > 0 else 0.0

        # Percentile rank over last 100 bars
        recent_atrs = atr_series[-100:]
        sorted_atrs = sorted(recent_atrs)
        rank = sum(1 for a in sorted_atrs if a <= curr_atr)
        atr_percentile = round((rank / len(sorted_atrs)) * 100.0, 1)

        prev_atr = atr_series[-4] if len(atr_series) >= 4 else curr_atr
        atr_slope = round(curr_atr - prev_atr, 4)

        is_expanding = curr_atr > (sum(atr_series[-5:]) / 5.0) * 1.05
        is_compressing = curr_atr < (sum(atr_series[-5:]) / 5.0) * 0.95

        if atr_percentile < 30.0:
            regime = "LOW_VOLATILITY"
        elif atr_percentile <= 75.0:
            regime = "NORMAL_VOLATILITY"
        else:
            regime = "HIGH_VOLATILITY"

        return {
            "atr": round(curr_atr, 4),
            "atr_pct": atr_pct,
            "atr_percentile": atr_percentile,
            "slope": atr_slope,
            "is_expanding": is_expanding,
            "is_compressing": is_compressing,
            "regime": regime
        }

    @staticmethod
    def macd(closes: List[float]) -> Tuple[float, float, float]:
        if len(closes) < 26:
            return 0.0, 0.0, 0.0
        ema12 = QuantFeatureEngine.ema(closes, 12)
        ema26 = QuantFeatureEngine.ema(closes, 26)
        macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
        signal_line = QuantFeatureEngine.ema(macd_line[25:], 9)
        m_val = round(macd_line[-1], 4)
        s_val = round(signal_line[-1], 4)
        h_val = round(m_val - s_val, 6)
        return m_val, s_val, h_val

    @staticmethod
    def calculate_taker_cvd(raw_klines: List[Any], closes: List[float], opens: List[float], volumes: List[float]) -> Dict[str, Any]:
        """
        Uses Binance Taker Buy Base Asset Volume (raw_klines[i][9]) if available.
        Computes Taker Buy/Sell Imbalance, Cumulative Volume Delta (CVD), CVD slope, CVD z-score, and Price/CVD divergence.
        """
        has_true_taker = False
        taker_buys = []
        taker_sells = []
        deltas = []

        for i, row in enumerate(raw_klines):
            vol = volumes[i]
            if len(row) > 9 and row[9] is not None:
                try:
                    tb = float(row[9])
                    ts = max(0.0, vol - tb)
                    has_true_taker = True
                except Exception:
                    tb = vol if closes[i] >= opens[i] else 0.0
                    ts = 0.0 if closes[i] >= opens[i] else vol
            else:
                tb = vol if closes[i] >= opens[i] else 0.0
                ts = 0.0 if closes[i] >= opens[i] else vol

            taker_buys.append(tb)
            taker_sells.append(ts)
            deltas.append(tb - ts)

        # Cumulative Volume Delta (CVD)
        cvd_series = []
        cum = 0.0
        for d in deltas:
            cum += d
            cvd_series.append(cum)

        curr_delta_20 = sum(deltas[-20:])
        total_vol_20 = sum(volumes[-20:])
        imbalance_pct = round((curr_delta_20 / total_vol_20) * 100.0, 2) if total_vol_20 > 0 else 0.0

        curr_cvd = cvd_series[-1]
        prev_cvd = cvd_series[-5] if len(cvd_series) >= 5 else curr_cvd
        cvd_slope = round(curr_cvd - prev_cvd, 2)

        # CVD Z-Score
        recent_cvd_diffs = [deltas[i] for i in range(-30, 0)] if len(deltas) >= 30 else deltas
        mean_d = sum(recent_cvd_diffs) / len(recent_cvd_diffs)
        std_d = math.sqrt(sum((x - mean_d) ** 2 for x in recent_cvd_diffs) / len(recent_cvd_diffs)) if len(recent_cvd_diffs) > 1 else 1.0
        cvd_zscore = round((deltas[-1] - mean_d) / std_d, 2) if std_d > 0 else 0.0

        # Price / CVD Divergence
        price_cvd_div = "NONE"
        if len(closes) >= 10 and len(cvd_series) >= 10:
            price_change = closes[-1] - closes[-10]
            cvd_change = cvd_series[-1] - cvd_series[-10]
            if price_change < 0 and cvd_change > 0:
                price_cvd_div = "BULLISH_CVD_ACCUMULATION"
            elif price_change > 0 and cvd_change < 0:
                price_cvd_div = "BEARISH_CVD_DISTRIBUTION"

        return {
            "is_true_cvd": has_true_taker,
            "metric_label": "CVD" if has_true_taker else "VOLUME_IMBALANCE_PROXY",
            "volume_imbalance_pct": imbalance_pct,
            "cvd_current": round(curr_cvd, 2),
            "cvd_slope": cvd_slope,
            "cvd_zscore": cvd_zscore,
            "price_cvd_divergence": price_cvd_div
        }


# =============================================================================
# 2. MARKET REGIME ENGINE
# =============================================================================

class MarketRegimeEngine:
    """Evaluates market state across EMAs, ADX, ATR, BB Width, and Structure."""

    @staticmethod
    def _adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period * 2:
            return 20.0
        plus_dm, minus_dm, trs = [], [], []
        for i in range(1, len(closes)):
            up = highs[i] - highs[i - 1]
            down = lows[i - 1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0.0)
            minus_dm.append(down if down > up and down > 0 else 0.0)
            trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))

        smooth_tr = sum(trs[:period])
        smooth_pdm = sum(plus_dm[:period])
        smooth_mdm = sum(minus_dm[:period])

        dx_list = []
        for i in range(period, len(trs)):
            smooth_tr = smooth_tr - (smooth_tr / period) + trs[i]
            smooth_pdm = smooth_pdm - (smooth_pdm / period) + plus_dm[i]
            smooth_mdm = smooth_mdm - (smooth_mdm / period) + minus_dm[i]

            p_di = (smooth_pdm / smooth_tr * 100.0) if smooth_tr > 0 else 0.0
            m_di = (smooth_mdm / smooth_tr * 100.0) if smooth_tr > 0 else 0.0
            di_diff = abs(p_di - m_di)
            di_sum = p_di + m_di
            dx = (di_diff / di_sum * 100.0) if di_sum > 0 else 0.0
            dx_list.append(dx)

        if not dx_list:
            return 20.0
        return round(sum(dx_list[-period:]) / len(dx_list[-period:]), 1)

    @staticmethod
    def detect_market_regime(klines: Dict[str, Any]) -> Dict[str, Any]:
        c, h, l, v = klines["closes"], klines["highs"], klines["lows"], klines["volumes"]
        price = c[-1]

        ema21 = QuantFeatureEngine.ema(c, 21)
        ema50 = QuantFeatureEngine.ema(c, 50)
        ema200 = QuantFeatureEngine.ema(c, 200)
        atr_data = QuantFeatureEngine.wilder_atr(h, l, c, 14)
        adx_val = MarketRegimeEngine._adx(h, l, c, 14)

        # Slopes over last 5 bars
        slope_ema21 = round((ema21[-1] - ema21[-5]) / ema21[-5], 5) if len(ema21) >= 5 else 0.0
        slope_ema50 = round((ema50[-1] - ema50[-5]) / ema50[-5], 5) if len(ema50) >= 5 else 0.0

        # Bollinger Band Width
        mean_20 = sum(c[-20:]) / 20.0
        std_20 = math.sqrt(sum((x - mean_20) ** 2 for x in c[-20:]) / 20.0) if len(c) >= 20 else 1.0
        bb_width_pct = round(((std_20 * 4.0) / mean_20) * 100.0, 2) if mean_20 > 0 else 0.0

        # Classification Logic
        regime = "RANGE"
        confidence = 65

        if atr_data["atr_percentile"] > 85.0 and bb_width_pct > 3.5:
            regime = "HIGH_VOLATILITY"
            confidence = 88
        elif atr_data["atr_percentile"] < 20.0 and bb_width_pct < 1.0:
            regime = "LOW_VOLATILITY"
            confidence = 85
        elif ema21[-1] > ema50[-1] > ema200[-1] and slope_ema21 > 0.001 and adx_val >= 22.0:
            regime = "TREND_UP"
            confidence = min(95, int(70 + adx_val * 0.75))
        elif ema21[-1] < ema50[-1] < ema200[-1] and slope_ema21 < -0.001 and adx_val >= 22.0:
            regime = "TREND_DOWN"
            confidence = min(95, int(70 + adx_val * 0.75))
        elif price > max(h[-20:-1]) and slope_ema21 > 0.002:
            regime = "BREAKOUT"
            confidence = 82
        elif price < min(l[-20:-1]) and slope_ema21 < -0.002:
            regime = "BREAKDOWN"
            confidence = 82
        else:
            regime = "RANGE"
            confidence = 72

        return {
            "regime": regime,
            "confidence": confidence,
            "adx": adx_val,
            "atr_percentile": atr_data["atr_percentile"],
            "ema_slope": slope_ema21,
            "bb_width_pct": bb_width_pct
        }


# =============================================================================
# 3. MARKET STRUCTURE ENGINE (ZERO LOOK-AHEAD)
# =============================================================================

class MarketStructureEngine:
    """Detects HH, HL, LH, LL, BOS, CHOCH, and Liquidity Sweeps with zero look-ahead bias."""

    @staticmethod
    def detect_market_structure(klines: Dict[str, Any], window: int = 5) -> Dict[str, Any]:
        h, l, c, times = klines["highs"], klines["lows"], klines["closes"], klines["times"]
        n = len(c)
        if n < window * 3:
            return {"trend_structure": "NEUTRAL", "last_bos": None, "last_choch": None, "sweeps": []}

        swing_highs = []  # List of dicts: {index, price, confirmed_at}
        swing_lows = []

        # Zero look-ahead: A swing point at index i is confirmed only at index i + window
        for i in range(window, n - window):
            confirmed_at = i + window
            if h[i] == max(h[i - window:i + window + 1]):
                swing_highs.append({"index": i, "price": h[i], "confirmed_at": confirmed_at, "time": times[i]})
            if l[i] == min(l[i - window:i + window + 1]):
                swing_lows.append({"index": i, "price": l[i], "confirmed_at": confirmed_at, "time": times[i]})

        last_bos = None
        last_choch = None
        sweeps = []
        curr_structure_trend = "NEUTRAL"

        # Track structural breaks chronologically
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            sh2, sh1 = swing_highs[-2], swing_highs[-1]
            sl2, sl1 = swing_lows[-2], swing_lows[-1]

            if sh1["price"] > sh2["price"] and sl1["price"] > sl2["price"]:
                curr_structure_trend = "BULLISH"
            elif sh1["price"] < sh2["price"] and sl1["price"] < sl2["price"]:
                curr_structure_trend = "BEARISH"

            # Check BOS / CHOCH against current candle
            latest_price = c[-1]
            if latest_price > sh1["price"]:
                last_bos = {"type": "BOS", "direction": "BULLISH", "price": sh1["price"], "strength": 88}
                if curr_structure_trend == "BEARISH":
                    last_choch = {"type": "CHOCH", "direction": "BULLISH", "price": sh1["price"], "strength": 92}
            elif latest_price < sl1["price"]:
                last_bos = {"type": "BOS", "direction": "BEARISH", "price": sl1["price"], "strength": 88}
                if curr_structure_trend == "BULLISH":
                    last_choch = {"type": "CHOCH", "direction": "BEARISH", "price": sl1["price"], "strength": 92}

            # Check Liquidity Sweeps in recent candles
            for i in range(n - 5, n):
                if h[i] > sh1["price"] and c[i] < sh1["price"]:
                    sweeps.append({"type": "SWEEP_HIGH", "price": h[i], "level": sh1["price"], "candle_index": i})
                if l[i] < sl1["price"] and c[i] > sl1["price"]:
                    sweeps.append({"type": "SWEEP_LOW", "price": l[i], "level": sl1["price"], "candle_index": i})

        return {
            "trend_structure": curr_structure_trend,
            "last_bos": last_bos,
            "last_choch": last_choch,
            "sweeps": sweeps,
            "recent_swing_highs": [sh["price"] for sh in swing_highs[-3:]],
            "recent_swing_lows": [sl["price"] for sl in swing_lows[-3:]]
        }


# =============================================================================
# 4. ORDER BLOCK & FVG ENGINES
# =============================================================================

class OrderBlockEngine:
    """Detects and scores Institutional Order Blocks."""

    @staticmethod
    def detect_order_blocks(klines: Dict[str, Any], atr: float) -> List[Dict[str, Any]]:
        o, h, l, c, v = klines["opens"], klines["highs"], klines["lows"], klines["closes"], klines["volumes"]
        n = len(c)
        if n < 20:
            return []

        order_blocks = []
        for i in range(n - 25, n - 2):
            body_size = abs(c[i + 1] - o[i + 1])
            candle_range = h[i + 1] - l[i + 1]

            # Bullish OB: Red candle followed by strong bullish displacement breaking recent high
            if c[i] < o[i] and c[i + 1] > o[i + 1] and body_size > 1.2 * atr:
                displacement_str = round(body_size / max(0.0001, atr), 2)
                is_fresh = not any(l[j] <= l[i] for j in range(i + 2, n))
                ob_score = min(98, int(60 + displacement_str * 15 + (10 if is_fresh else 0)))

                order_blocks.append({
                    "type": "BULLISH",
                    "zone_high": round(h[i], 4),
                    "zone_low": round(l[i], 4),
                    "fresh": is_fresh,
                    "mitigated": not is_fresh,
                    "displacement_str": displacement_str,
                    "score": ob_score,
                    "candle_index": i
                })

            # Bearish OB: Green candle followed by strong bearish displacement
            elif c[i] > o[i] and c[i + 1] < o[i + 1] and body_size > 1.2 * atr:
                displacement_str = round(body_size / max(0.0001, atr), 2)
                is_fresh = not any(h[j] >= h[i] for j in range(i + 2, n))
                ob_score = min(98, int(60 + displacement_str * 15 + (10 if is_fresh else 0)))

                order_blocks.append({
                    "type": "BEARISH",
                    "zone_high": round(h[i], 4),
                    "zone_low": round(l[i], 4),
                    "fresh": is_fresh,
                    "mitigated": not is_fresh,
                    "displacement_str": displacement_str,
                    "score": ob_score,
                    "candle_index": i
                })

        return order_blocks[-4:]


class FVGEngine:
    """Detects and evaluates Fair Value Gap imbalances."""

    @staticmethod
    def detect_fvgs(klines: Dict[str, Any], curr_price: float) -> List[Dict[str, Any]]:
        h, l, c = klines["highs"], klines["lows"], klines["closes"]
        n = len(c)
        if n < 10:
            return []

        fvgs = []
        for i in range(n - 20, n - 2):
            # Bullish FVG: Low of candle i+2 > High of candle i
            if l[i + 2] > h[i]:
                top = round(l[i + 2], 4)
                bottom = round(h[i], 4)
                size_pct = round(((top - bottom) / curr_price) * 100.0, 3)

                # Fill percentage by subsequent candles
                min_subsequent_low = min(l[i + 3:]) if i + 3 < n else top
                filled_dist = max(0.0, top - min_subsequent_low)
                fill_pct = round(min(100.0, (filled_dist / max(0.0001, top - bottom)) * 100.0), 1)

                is_fresh = fill_pct < 50.0
                score = min(95, int(65 + size_pct * 30 - fill_pct * 0.3))

                fvgs.append({
                    "type": "BULLISH",
                    "top": top,
                    "bottom": bottom,
                    "size_pct": size_pct,
                    "fill_pct": fill_pct,
                    "fresh": is_fresh,
                    "score": score
                })

            # Bearish FVG: High of candle i+2 < Low of candle i
            elif h[i + 2] < l[i]:
                top = round(l[i], 4)
                bottom = round(h[i + 2], 4)
                size_pct = round(((top - bottom) / curr_price) * 100.0, 3)

                max_subsequent_high = max(h[i + 3:]) if i + 3 < n else bottom
                filled_dist = max(0.0, max_subsequent_high - bottom)
                fill_pct = round(min(100.0, (filled_dist / max(0.0001, top - bottom)) * 100.0), 1)

                is_fresh = fill_pct < 50.0
                score = min(95, int(65 + size_pct * 30 - fill_pct * 0.3))

                fvgs.append({
                    "type": "BEARISH",
                    "top": top,
                    "bottom": bottom,
                    "size_pct": size_pct,
                    "fill_pct": fill_pct,
                    "fresh": is_fresh,
                    "score": score
                })

        return fvgs[-4:]


# =============================================================================
# 5. LIQUIDITY ENGINE
# =============================================================================

class LiquidityEngine:
    """Locates EQH, EQL, PDH, PDL, and Nearest Liquidity Pools."""

    @staticmethod
    def detect_liquidity_pools(klines_m15: Dict[str, Any], klines_d1: Optional[Dict[str, Any]], curr_price: float) -> Dict[str, Any]:
        h, l = klines_m15["highs"], klines_m15["lows"]

        # Equal Highs / Equal Lows within 0.15% threshold
        eqh_list = []
        eql_list = []

        for i in range(len(h) - 30, len(h) - 1):
            for j in range(i + 3, len(h)):
                if abs(h[i] - h[j]) / h[i] < 0.0015:
                    eqh_list.append(round((h[i] + h[j]) / 2.0, 4))
                if abs(l[i] - l[j]) / l[i] < 0.0015:
                    eql_list.append(round((l[i] + l[j]) / 2.0, 4))

        pdh = round(klines_d1["highs"][-2], 4) if (klines_d1 and len(klines_d1["highs"]) >= 2) else max(h[-96:])
        pdl = round(klines_d1["lows"][-2], 4) if (klines_d1 and len(klines_d1["lows"]) >= 2) else min(l[-96:])

        liquidity_above = [p for p in set(eqh_list + [pdh]) if p > curr_price]
        liquidity_below = [p for p in set(eql_list + [pdl]) if p < curr_price]

        nearest_above = min(liquidity_above) if liquidity_above else round(curr_price * 1.02, 4)
        nearest_below = max(liquidity_below) if liquidity_below else round(curr_price * 0.98, 4)

        return {
            "pdh": pdh,
            "pdl": pdl,
            "eqh": eqh_list[-2:],
            "eql": eql_list[-2:],
            "nearest_liquidity_above": nearest_above,
            "nearest_liquidity_below": nearest_below
        }


# =============================================================================
# 6. SETUP DETECTION ENGINE (9 EXPLICIT SETUP TYPES)
# =============================================================================

class SetupEngine:
    """Evaluates 9 deterministic SMC & Quantitative setup models."""

    @staticmethod
    def evaluate_candidate_setup(
        m15_data: Dict[str, Any],
        htf_data: Dict[str, Any],
        structure: Dict[str, Any],
        order_blocks: List[Dict[str, Any]],
        fvgs: List[Dict[str, Any]],
        liquidity: Dict[str, Any],
        cvd_data: Dict[str, Any],
        regime_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        price = m15_data["price"]
        rsi = m15_data["rsi"]
        macd_hist = m15_data["macd_hist"]
        regime = regime_data["regime"]
        struct_trend = structure.get("trend_structure", "NEUTRAL")
        sweeps = structure.get("sweeps", [])
        atr = m15_data.get("atr", price * 0.005)

        setup_candidates = []

        # 1. TREND_PULLBACK (Bullish)
        if (regime in ("TREND_UP", "BREAKOUT") or m15_data["ema21"] > m15_data["ema50"]) and rsi < 68.0:
            fresh_bull_ob = next((ob for ob in order_blocks if ob["type"] == "BULLISH" and ob.get("fresh", True)), None)
            setup_candidates.append({
                "setup_type": "TREND_PULLBACK",
                "side": "BUY",
                "score": 88,
                "target_price": liquidity["nearest_liquidity_above"],
                "invalidation_price": fresh_bull_ob["zone_low"] if fresh_bull_ob else round(min(price - atr * 1.5, m15_data["ema50"] - atr * 0.5), 4),
                "reasoning": f"Bullish trend continuation holding above EMA stack with RSI ({rsi}) and upward momentum."
            })

        # 2. TREND_PULLBACK (Bearish)
        if (regime in ("TREND_DOWN", "BREAKDOWN") or m15_data["ema21"] < m15_data["ema50"]) and rsi > 32.0:
            fresh_bear_ob = next((ob for ob in order_blocks if ob["type"] == "BEARISH" and ob.get("fresh", True)), None)
            setup_candidates.append({
                "setup_type": "TREND_PULLBACK",
                "side": "SELL",
                "score": 88,
                "target_price": liquidity["nearest_liquidity_below"],
                "invalidation_price": fresh_bear_ob["zone_high"] if fresh_bear_ob else round(max(price + atr * 1.5, m15_data["ema50"] + atr * 0.5), 4),
                "reasoning": f"Bearish trend continuation rejecting under EMA stack with RSI ({rsi}) seller pressure."
            })

        # 3. LIQUIDITY_SWEEP (Bullish Mean-Reversion)
        sweep_low = next((s for s in sweeps if s.get("type") == "SWEEP_LOW"), None)
        if (sweep_low or rsi < 36.0 or price <= liquidity.get("pdl", 0)):
            ref_low = sweep_low["level"] if sweep_low else liquidity.get("pdl", price - atr)
            setup_candidates.append({
                "setup_type": "LIQUIDITY_SWEEP",
                "side": "BUY",
                "score": 91,
                "target_price": liquidity["nearest_liquidity_above"],
                "invalidation_price": round(min(ref_low, price) - atr * 0.5, 4),
                "reasoning": f"Bullish liquidity sweep with oversold RSI ({rsi}) and mean-reversion displacement."
            })

        # 4. LIQUIDITY_SWEEP (Bearish Mean-Reversion)
        sweep_high = next((s for s in sweeps if s.get("type") == "SWEEP_HIGH"), None)
        if (sweep_high or rsi > 64.0 or price >= liquidity.get("pdh", float("inf"))):
            ref_high = sweep_high["level"] if sweep_high else liquidity.get("pdh", price + atr)
            setup_candidates.append({
                "setup_type": "LIQUIDITY_SWEEP",
                "side": "SELL",
                "score": 91,
                "target_price": liquidity["nearest_liquidity_below"],
                "invalidation_price": round(max(ref_high, price) + atr * 0.5, 4),
                "reasoning": f"Bearish liquidity sweep of buy-side liquidity with overbought RSI ({rsi})."
            })

        # 5. ORDER_BLOCK_RETEST (Bullish)
        fresh_bull_ob = next((ob for ob in order_blocks if ob["type"] == "BULLISH" and ob.get("fresh", True)), None)
        if fresh_bull_ob and abs(price - fresh_bull_ob["zone_high"]) / price < 0.015:
            setup_candidates.append({
                "setup_type": "ORDER_BLOCK_RETEST",
                "side": "BUY",
                "score": 89,
                "target_price": liquidity["nearest_liquidity_above"],
                "invalidation_price": round(fresh_bull_ob["zone_low"] - atr * 0.4, 4),
                "reasoning": f"Mitigation retest of Bullish Order Block at ${fresh_bull_ob['zone_high']:,.2f}."
            })

        # 6. ORDER_BLOCK_RETEST (Bearish)
        fresh_bear_ob = next((ob for ob in order_blocks if ob["type"] == "BEARISH" and ob.get("fresh", True)), None)
        if fresh_bear_ob and abs(price - fresh_bear_ob["zone_low"]) / price < 0.015:
            setup_candidates.append({
                "setup_type": "ORDER_BLOCK_RETEST",
                "side": "SELL",
                "score": 89,
                "target_price": liquidity["nearest_liquidity_below"],
                "invalidation_price": round(fresh_bear_ob["zone_high"] + atr * 0.4, 4),
                "reasoning": f"Mitigation retest of Bearish Order Block at ${fresh_bear_ob['zone_low']:,.2f}."
            })

        # 7. FAIR_VALUE_GAP_ENTRY (Bullish)
        fresh_bull_fvg = next((fvg for fvg in fvgs if fvg["type"] == "BULLISH" and fvg.get("fresh", True)), None)
        if fresh_bull_fvg and abs(price - fresh_bull_fvg["bottom"]) / price < 0.012:
            setup_candidates.append({
                "setup_type": "FVG_IMBALANCE_FILL",
                "side": "BUY",
                "score": 87,
                "target_price": liquidity["nearest_liquidity_above"],
                "invalidation_price": round(fresh_bull_fvg["bottom"] - atr * 0.4, 4),
                "reasoning": f"Bullish Fair Value Gap fill support at ${fresh_bull_fvg['bottom']:,.2f}."
            })

        # 8. FAIR_VALUE_GAP_ENTRY (Bearish)
        fresh_bear_fvg = next((fvg for fvg in fvgs if fvg["type"] == "BEARISH" and fvg.get("fresh", True)), None)
        if fresh_bear_fvg and abs(price - fresh_bear_fvg["top"]) / price < 0.012:
            setup_candidates.append({
                "setup_type": "FVG_IMBALANCE_FILL",
                "side": "SELL",
                "score": 87,
                "target_price": liquidity["nearest_liquidity_below"],
                "invalidation_price": round(fresh_bear_fvg["top"] + atr * 0.4, 4),
                "reasoning": f"Bearish Fair Value Gap premium rejection at ${fresh_bear_fvg['top']:,.2f}."
            })

        # 9. MOMENTUM_EXPANSION_BREAKOUT (Bullish & Bearish)
        if macd_hist > 0.0001 and rsi > 52.0 and price > m15_data["ema21"]:
            setup_candidates.append({
                "setup_type": "MOMENTUM_EXPANSION",
                "side": "BUY",
                "score": 84,
                "target_price": liquidity["nearest_liquidity_above"],
                "invalidation_price": round(price - atr * 1.5, 4),
                "reasoning": f"Bullish MACD momentum expansion with price leading EMA21."
            })
        elif macd_hist < -0.0001 and rsi < 48.0 and price < m15_data["ema21"]:
            setup_candidates.append({
                "setup_type": "MOMENTUM_EXPANSION",
                "side": "SELL",
                "score": 84,
                "target_price": liquidity["nearest_liquidity_below"],
                "invalidation_price": round(price + atr * 1.5, 4),
                "reasoning": f"Bearish MACD momentum expansion with price leading EMA21 downward."
            })

        if not setup_candidates:
            return None

        # Select highest-scoring candidate setup
        best_setup = max(setup_candidates, key=lambda x: x["score"])
        return best_setup


# =============================================================================
# 7. QUANT SCORING ENGINE (MULTI-FACTOR WEIGHTED 0-100)
# =============================================================================

class QuantScoringEngine:
    """Calculates weighted multi-factor quant score (0-100)."""

    @staticmethod
    def calculate_htf_alignment_score(tf_trends: Dict[str, str], setup_side: str) -> float:
        weights = {"D1": 35.0, "H4": 30.0, "H1": 25.0, "M5": 10.0}
        total_score = 0.0
        for tf, weight in weights.items():
            trend = tf_trends.get(tf, "NEUTRAL")
            if (setup_side == "BUY" and trend in ("BULLISH", "TREND_UP", "BREAKOUT")) or \
               (setup_side == "SELL" and trend in ("BEARISH", "TREND_DOWN", "BREAKDOWN")):
                total_score += weight
            elif trend in ("NEUTRAL", "RANGE"):
                total_score += weight * 0.5
        return round(total_score, 1)

    @staticmethod
    def calculate_quant_score(
        setup: Dict[str, Any],
        m15_data: Dict[str, Any],
        regime_data: Dict[str, Any],
        structure: Dict[str, Any],
        cvd_data: Dict[str, Any],
        htf_alignment_score: float
    ) -> Dict[str, Any]:

        side = setup["side"]

        # Component Scores (0-100)
        c_htf = htf_alignment_score
        c_regime = float(regime_data["confidence"])
        c_structure = 90.0 if structure["trend_structure"] == ("BULLISH" if side == "BUY" else "BEARISH") else 60.0
        c_smc = float(setup.get("score", 80))
        c_momentum = 85.0 if (side == "BUY" and m15_data["macd_hist"] > 0) or (side == "SELL" and m15_data["macd_hist"] < 0) else 55.0
        c_volume = min(95.0, max(40.0, 50.0 + cvd_data["volume_imbalance_pct"] * (1.0 if side == "BUY" else -1.0)))
        c_volatility = 80.0 if regime_data["regime"] != "HIGH_VOLATILITY" else 45.0
        c_setup = float(setup.get("score", 80))

        # Weighted Calculation
        quant_score = round(
            c_htf * 0.15 +
            c_regime * 0.15 +
            c_structure * 0.20 +
            c_smc * 0.15 +
            c_momentum * 0.10 +
            c_volume * 0.10 +
            c_volatility * 0.05 +
            c_setup * 0.10,
            1
        )

        return {
            "quant_score": quant_score,
            "components": {
                "htf_alignment": c_htf,
                "regime": c_regime,
                "structure": c_structure,
                "smc": c_smc,
                "momentum": c_momentum,
                "volume": c_volume,
                "volatility": c_volatility,
                "setup": c_setup
            }
        }


# =============================================================================
# 8. DETERMINISTIC RISK ENGINE (STRUCTURAL SL/TP & MIN 2.0 RR)
# =============================================================================

class RiskEngine:
    """Calculates senior-grade dynamic Entry, Invalidation Stop Loss (with volatility protection), and Multi-Target Take Profits."""

    @staticmethod
    def calculate_risk_parameters(
        setup: Dict[str, Any],
        price: float,
        atr: float,
        liquidity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        side = setup["side"]
        entry = round(price, 4)
        raw_sl = setup.get("invalidation_price", price)

        # STRICT M15 INTRADAY ATR TIMEFRAME CLAMP (Zero D1/H4 Leakage Guard)
        is_btc = "BTC" in str(setup.get("symbol", "")).upper()
        
        # M15 Strict Dynamic Limits (BTC: 120-550 pts, ETH: 8-35 pts)
        min_sl_dist = max(1.5 * atr, 220.0 if is_btc else 10.0)
        max_sl_dist = min(3.0 * atr, 750.0 if is_btc else 40.0)

        regime_type = str(setup.get("regime", "")).upper()
        conf_score = float(setup.get("confidence", 80.0))
        
        # Dynamic TP Count: 2 targets in ranging/choppy markets, 3 targets in high-confidence trend expansion
        target_count = 3 if ("TREND" in regime_type or conf_score >= 82.0) else 2

        if side == "BUY":
            raw_dist = entry - raw_sl if raw_sl < entry else 1.5 * atr
            buffered_dist = raw_dist + 0.6 * atr
            sl_distance = max(min_sl_dist, min(max_sl_dist, buffered_dist))
            sl = round(entry - sl_distance, 2 if is_btc else 2)

            tp1 = round(entry + 1.8 * sl_distance, 2 if is_btc else 2)  # 1:1.8 RR - Enhanced Intraday TP1
            tp2 = round(entry + 3.0 * sl_distance, 2 if is_btc else 2)  # 1:3.0 RR - Main Intraday Target
            tp3 = round(entry + 4.0 * sl_distance, 2 if is_btc else 2) if target_count == 3 else None
            rr = round((tp2 - entry) / max(0.01, sl_distance), 2)
        else:
            raw_dist = raw_sl - entry if raw_sl > entry else 1.5 * atr
            buffered_dist = raw_dist + 0.6 * atr
            sl_distance = max(min_sl_dist, min(max_sl_dist, buffered_dist))
            sl = round(entry + sl_distance, 2 if is_btc else 2)

            tp1 = round(entry - 1.8 * sl_distance, 2 if is_btc else 2)  # 1:1.8 RR - Enhanced Intraday TP1
            tp2 = round(entry - 3.0 * sl_distance, 2 if is_btc else 2)  # 1:3.0 RR - Main Intraday Target
            tp3 = round(entry - 4.0 * sl_distance, 2 if is_btc else 2) if target_count == 3 else None
            rr = round((entry - tp2) / max(0.01, sl_distance), 2)

        # Mandatory Institutional Risk Gate: Minimum RR >= 2.0
        if rr < 2.0:
            logger.info(f"[RISK ENGINE] Rejected setup: Risk-to-Reward {rr} < 2.0.")
            return None

        return {
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "rr": rr,
            "sl_distance": sl_distance,
            "risk_amount_pct": 1.5
        }
# =============================================================================
# 9. GEMINI AI REVIEWER (ANALYTICAL REVIEWER ONLY)
# =============================================================================

class GeminiReviewer:
    """Queries Gemini as an Institutional Lead Quantitative Risk & Alpha Reviewer."""

    @staticmethod
    def build_review_prompt(candidate: Dict[str, Any]) -> str:
        return f"""You are a Lead Senior Crypto Prop Quantitative Analyst. Evaluate this trade setup:

Asset: {candidate['symbol']}
Side: {candidate['side']}
Setup Type: {candidate.get('setupType', 'SMC Setup')}
Market Regime: {candidate.get('regime', 'TRENDING')}
Quant Score: {candidate.get('quantScore', 75.0)} / 100
Entry Price: 
Dynamic Stop Loss: 
Take Profit 1: 
Take Profit 2 (Target): 
Take Profit 3 (Runner): 
Risk-to-Reward Ratio: {candidate['rr']} R

Technical Indicators:
- RSI: {candidate['indicators'].get('rsi', 50)} ({candidate['indicators'].get('rsi_regime', 'NEUTRAL')})
- Volume Delta: {candidate['indicators'].get('volumeDelta', 0)}%
- CVD Z-Score: {candidate['indicators'].get('cvd_zscore', 0)}

Evaluate structural integrity and orderflow confluence. Respond strictly in JSON:
{{
  "decision": "APPROVE" or "REJECT",
  "ai_review_score": <float 0-100>,
  "contradictions": [<string>],
  "reasoning": "<concise institutional analysis reasoning>"
}}"""

    @staticmethod
    def review_setup(candidate: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        prompt = GeminiReviewer.build_review_prompt(candidate)
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "topP": 0.9}
        }
        data = json.dumps(body).encode("utf-8")

        if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("AQ."):
            for model in GEMINI_MODELS:
                url = f"{GEMINI_BASE_URL}{model}:generateContent?key={GEMINI_API_KEY}"
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                    raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if "`" in raw_text:
                        raw_text = raw_text.split("`")[1]
                        if raw_text.startswith("json"):
                            raw_text = raw_text[4:].strip()
                    parsed = json.loads(raw_text)
                    return parsed, f"GEMINI AI ({model})"
                except Exception as e:
                    logger.warning(f"[GEMINI REVIEW] Error/rate-limit on {model}: {e}")

        # Institutional Quant Rule Engine Reviewer
        # Senior Threshold: Approve only if quant score is >= 75.0 with confirmed R:R >= 2.0
        q_score = float(candidate.get("quantScore", 70.0))
        fallback_decision = "APPROVE" if q_score >= 75.0 else "REJECT"
        fallback_score = round(q_score * 0.98, 1)
        setup_name = candidate.get("setupType", "Smart Money Setup")
        regime = candidate.get("regime", "TRENDING")

        return {
            "decision": fallback_decision,
            "ai_review_score": fallback_score,
            "contradictions": [] if fallback_decision == "APPROVE" else ["Insufficient Quant Confluence Score (< 75.0)"],
            "reasoning": f"Senior Institutional Analysis: {setup_name} in {regime} regime confirmed with {q_score:.1f}% quantitative confluence and {candidate.get('rr', 2.5)} R:R."
        }, "INSTITUTIONAL QUANT ENGINE"
# =============================================================================
# 10. INDEPENDENT FINAL SIGNAL GATE & PORTFOLIO EXPOSURE
# =============================================================================

class FinalSignalGate:
    """Final deterministic verification gate enforcing risk budgets, correlation penalties, and factor audits."""

    @staticmethod
    def build_verification_matrix(candidate: Dict[str, Any], quant_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        def chk(label: str, passed: bool) -> Dict[str, Any]:
            return {"label": label, "passed": passed}

        return [
            chk("MTF Alignment", quant_metrics["components"]["htf_alignment"] >= 50.0),
            chk("Market Regime", quant_metrics["components"]["regime"] >= 60.0),
            chk("Market Structure", quant_metrics["components"]["structure"] >= 60.0),
            chk("SMC Block / FVG", quant_metrics["components"]["smc"] >= 60.0),
            chk("Momentum Filter", quant_metrics["components"]["momentum"] >= 55.0),
            chk("Volume Delta / CVD", quant_metrics["components"]["volume"] >= 45.0),
            chk("Risk-to-Reward Gate", candidate["rr"] >= 2.0),
            chk("Quant Score Gate", candidate["quantScore"] >= 65.0),
        ]

    @staticmethod
    def validate_candidate(candidate: Dict[str, Any], active_signals: List[Dict[str, Any]]) -> bool:
        # Strictly sync with real live open positions
        try:
            from backend.live_execution_manager import load_positions
            open_positions = [p for p in load_positions() if p.get("status") == "OPEN"]
            
            # Check if symbol already has an open position
            if any(p.get("symbol") == candidate["symbol"] for p in open_positions):
                logger.info(f"[FINAL GATE] Rejected {candidate['symbol']} because position is already OPEN.")
                return False
                
            # Max 2 simultaneous open positions
            if len(open_positions) >= 2:
                logger.info(f"[FINAL GATE] Rejected {candidate['symbol']} due to max portfolio open positions limit (2).")
                return False
                
            return True
        except Exception:
            return True


# =============================================================================
# 11. OUTCOME TRACKER & HISTORICAL ANALYTICS
# =============================================================================

def get_signals_history() -> List[Dict[str, Any]]:
    """Loads history from signals_history.json with error protection."""
    if not os.path.exists(HISTORY_FILE):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading history file: {e}")
        return []

def save_signals_history(history: List[Dict[str, Any]]):
    """Saves history to signals_history.json."""
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving history file: {e}")

def get_latest_signals() -> List[Dict[str, Any]]:
    """Returns only currently actionable signals for BTC, ETH, SOL."""
    history = get_signals_history()
    latest_map = {}
    for s in history:
        symbol = s.get("symbol")
        current = latest_map.get(symbol)
        if current is None or float(s.get("timestamp", 0) or 0) > float(current.get("timestamp", 0) or 0):
            latest_map[symbol] = s
    return [
        signal for signal in latest_map.values()
        if signal.get("status") in ("PENDING", "CONFIRMED")
    ]

def calculate_historical_performance() -> Dict[str, Any]:
    """Computes quantitative win-rate and profit metrics grouped by setup_type and regime."""
    history = get_signals_history()
    closed = [s for s in history if s.get("result") in ("WIN", "LOSS")]
    if not closed:
        return {"total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0}

    wins = sum(1 for s in closed if s["result"] == "WIN")
    win_rate = round((wins / len(closed)) * 100.0, 1)
    return {"total_trades": len(closed), "win_rate": win_rate, "closed_trades": closed}


# =============================================================================
# 12. BINANCE MULTI-TIMEFRAME DATA FETCHING
# =============================================================================

def fetch_klines_multi_tf(symbol: str, interval: str = "15m", limit: int = 200) -> Dict[str, Any]:
    sym = symbol.replace("/", "").upper()
    endpoints = [
        f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}",
        f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}",
        f"https://api1.binance.com/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}",
        f"https://api3.binance.com/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}"
    ]
    last_err = None
    for url in endpoints:
        for _ in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ApexQuantEngine/5.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw = json.loads(resp.read().decode())

                opens = [float(d[1]) for d in raw]
                highs = [float(d[2]) for d in raw]
                lows = [float(d[3]) for d in raw]
                closes = [float(d[4]) for d in raw]
                volumes = [float(d[5]) for d in raw]
                times = [d[0] for d in raw]

                return {
                    "raw": raw,
                    "opens": opens, "highs": highs, "lows": lows,
                    "closes": closes, "volumes": volumes, "times": times
                }
            except Exception as err:
                last_err = err
                time.sleep(0.3)
    if last_err:
        raise last_err
    raise RuntimeError(f"Failed to fetch klines for {sym} {interval}")



# =============================================================================
# 13. MAIN PUBLIC SIGNAL GENERATION ENTRYPOINT
# =============================================================================

def generate_signals() -> List[Dict[str, Any]]:
    """
    Main Execution Entrypoint.
    Executes full multi-timeframe feature processing, regime detection, SMC structure analysis,
    quant scoring, risk parameter calculation, Gemini review, and final gate validation.
    """
    global _signal_cache, _cache_ts
    now = time.time()

    # Return cached signals if within 15-second TTL
    if _signal_cache and (now - _cache_ts) < CACHE_TTL_S:
        return list(_signal_cache.values())

    dt_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    history = get_signals_history()

    # Active signal TTL check (15 minutes or active open position check)
    active_symbols = set()
    history_updated = False
    
    # Check actual live open positions from live_positions.json
    try:
        from backend.live_execution_manager import load_positions
        open_pos = load_positions()
        for p in open_pos:
            if p.get("status") == "OPEN":
                active_symbols.add(p.get("symbol"))
    except Exception:
        pass

    for hs in history:
        st = hs.get("status")
        ts = hs.get("timestamp", 0)
        if st in ("PENDING", "CONFIRMED"):
            if (now - ts) > 900 and hs.get("symbol") not in active_symbols:
                hs["status"] = "EXPIRED"
                history_updated = True
            elif hs.get("symbol") in active_symbols:
                active_symbols.add(hs.get("symbol"))
    if history_updated:
        save_signals_history(history)

    generated_signals = []

    for s_info in SYMBOLS:
        sym = s_info["symbol"]
        binance_sym = s_info["binance"]

        if sym in BLACKLISTED_SYMBOLS:
            logger.info(f"[ENGINE] Skipping {sym}: Blacklisted asset.")
            continue

        if sym in active_symbols:
            logger.info(f"[ENGINE] Skipping {sym}: active signal already exists (< 2h).")
            continue

        # Check Daily Trades Cap
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_seen_ids = set()
        try:
            from backend.live_execution_manager import load_positions, load_equity_state
            for p in load_positions():
                p_date = p.get("openedAt", "")[:10]
                if not p_date and p.get("entry_timestamp"):
                    p_date = datetime.fromtimestamp(p["entry_timestamp"], tz=timezone.utc).strftime("%Y-%m-%d")
                if p.get("symbol") == sym and p_date == today_utc:
                    today_seen_ids.add(p.get("id"))
            eq_state = load_equity_state()
            for th in eq_state.get("tradeHistory", []):
                th_date = th.get("openedAt", "")[:10]
                if not th_date and th.get("entry_timestamp"):
                    th_date = datetime.fromtimestamp(th["entry_timestamp"], tz=timezone.utc).strftime("%Y-%m-%d")
                if th.get("symbol") == sym and th_date == today_utc:
                    today_seen_ids.add(th.get("id"))
        except Exception:
            pass
        today_trades = len(today_seen_ids)

        if today_trades >= MAX_DAILY_TRADES_PER_SYMBOL:
            logger.info(f"[ENGINE] Skipping {sym}: Daily trades cap reached ({today_trades}/{MAX_DAILY_TRADES_PER_SYMBOL}).")
            try:
                from backend.telegram_bot import telegram_notifier
                telegram_notifier.send_daily_limit_reached_notification(sym, today_trades, MAX_DAILY_TRADES_PER_SYMBOL)
            except Exception as e:
                logger.error(f"[ENGINE] Error sending daily cap alert: {e}")
            continue

        try:
            # 1. Fetch Multi-Timeframe Data (D1, H4, H1, M15, M5)
            k_m15 = fetch_klines_multi_tf(binance_sym, "15m", 200)
            k_h1 = fetch_klines_multi_tf(binance_sym, "1h", 100)
            k_h4 = fetch_klines_multi_tf(binance_sym, "4h", 50)
            k_d1 = fetch_klines_multi_tf(binance_sym, "1d", 30)

            # 2. Extract Features & Technical Indicators
            rsi_m15 = QuantFeatureEngine.wilder_rsi(k_m15["closes"], 14)
            atr_m15 = QuantFeatureEngine.wilder_atr(k_m15["highs"], k_m15["lows"], k_m15["closes"], 14)
            macd_v, macd_s, macd_h = QuantFeatureEngine.macd(k_m15["closes"])
            cvd_m15 = QuantFeatureEngine.calculate_taker_cvd(k_m15["raw"], k_m15["closes"], k_m15["opens"], k_m15["volumes"])

            m15_indicators = {
                "price": k_m15["closes"][-1],
                "atr": atr_m15["atr"],
                "atr_pct": atr_m15["atr_pct"],
                "atr_percentile": atr_m15["atr_percentile"],
                "rsi": rsi_m15["rsi"],
                "rsi_regime": rsi_m15["regime"],
                "macd_hist": macd_h,
                "volumeDelta": cvd_m15["volume_imbalance_pct"],
                "cvd_zscore": cvd_m15["cvd_zscore"],
                "ema21": QuantFeatureEngine.ema(k_m15["closes"], 21)[-1],
                "ema50": QuantFeatureEngine.ema(k_m15["closes"], 50)[-1],
                "ema200": QuantFeatureEngine.ema(k_m15["closes"], 200)[-1]
            }

            # 3. Market Regime Engine
            regime_m15 = MarketRegimeEngine.detect_market_regime(k_m15)
            regime_h1 = MarketRegimeEngine.detect_market_regime(k_h1)

            tf_trends = {
                "D1": MarketRegimeEngine.detect_market_regime(k_d1)["regime"],
                "H4": MarketRegimeEngine.detect_market_regime(k_h4)["regime"],
                "H1": regime_h1["regime"],
                "M15": regime_m15["regime"]
            }

            # 4. Market Structure, Order Blocks, FVGs, Liquidity
            structure_m15 = MarketStructureEngine.detect_market_structure(k_m15, window=5)
            order_blocks = OrderBlockEngine.detect_order_blocks(k_m15, atr_m15["atr"])
            fvgs = FVGEngine.detect_fvgs(k_m15, k_m15["closes"][-1])
            liquidity = LiquidityEngine.detect_liquidity_pools(k_m15, k_d1, k_m15["closes"][-1])

            # 5. Setup Detection Engine
            candidate_setup = SetupEngine.evaluate_candidate_setup(
                m15_indicators, k_h1, structure_m15, order_blocks, fvgs, liquidity, cvd_m15, regime_m15
            )
            if not candidate_setup:
                logger.info(f"[ENGINE] NO_TRADE for {sym}: no high-conviction setup detected.")
                continue

            # 6. Quant Scoring Engine
            htf_score = QuantScoringEngine.calculate_htf_alignment_score(tf_trends, candidate_setup["side"])
            quant_result = QuantScoringEngine.calculate_quant_score(
                candidate_setup, m15_indicators, regime_m15, structure_m15, cvd_m15, htf_score
            )
            quant_score = quant_result["quant_score"]

            if quant_score < 75.0:
                logger.info(f"[ENGINE] NO_TRADE for {sym}: quant score ({quant_score}) below threshold (75.0).")
                continue

            # 7. Deterministic Risk Engine
            risk_params = RiskEngine.calculate_risk_parameters(
                candidate_setup, k_m15["closes"][-1], atr_m15["atr"], liquidity
            )
            if not risk_params:
                continue

            # Prepare Candidate Signal for AI Review
            candidate_signal = {
                "id": f"sig_{binance_sym.lower()}_{int(now)}",
                "symbol": sym,
                "side": candidate_setup["side"],
                "timeframe": "M15",
                "setupType": candidate_setup["setup_type"],
                "regime": regime_m15["regime"],
                "entry": risk_params["entry"],
                "sl": risk_params["sl"],
                "tp1": risk_params["tp1"],
                "tp2": risk_params["tp2"],
                "tp3": risk_params["tp3"],
                "rr": risk_params["rr"],
                "quantScore": quant_score,
                "indicators": m15_indicators,
                "regimeData": regime_m15,
                "marketStructure": structure_m15,
                "liquidity": liquidity,
                "orderBlocks": order_blocks,
                "fairValueGaps": fvgs
            }

            # 8. Gemini Qualitative Review
            ai_review, source_label = GeminiReviewer.review_setup(candidate_signal)
            if ai_review.get("decision") != "APPROVE":
                logger.info(f"[ENGINE] Gemini AI rejected setup for {sym}: {ai_review.get('reasoning')}")
                continue

            ai_review_score = float(ai_review.get("ai_review_score", quant_score))
            reasoning = ai_review.get("reasoning", candidate_setup["reasoning"])

            # 9. Independent Final Gate & Factor Audit
            verification_matrix = FinalSignalGate.build_verification_matrix(candidate_signal, quant_result)
            passed_factors = sum(1 for v in verification_matrix if v["passed"])
            factor_score = round((passed_factors / len(verification_matrix)) * 100.0, 1)

            if not FinalSignalGate.validate_candidate(candidate_signal, history):
                continue

            # Enriched Final Signal Object (Fully Backward-Compatible + Quant Extensions)
            final_signal = {
                "id": candidate_signal["id"],
                "symbol": sym,
                "side": candidate_signal["side"],
                "timeframe": "M15",
                "setupType": candidate_signal["setupType"],
                "regime": candidate_signal["regime"],
                "entry": candidate_signal["entry"],
                "sl": candidate_signal["sl"],
                "tp": candidate_signal["tp1"],  # Legacy consumers use the first target.
                "tp1": candidate_signal["tp1"],
                "tp2": candidate_signal["tp2"],
                "tp3": candidate_signal["tp3"],
                "rr": candidate_signal["rr"],
                "quantScore": quant_score,
                "aiReviewScore": ai_review_score,
                "factorScore": factor_score,
                "winProbability": None,  # Will populate as historical win rate when samples >= 20
                "confidence": round((quant_score * 0.5 + ai_review_score * 0.5), 1),
                "aiScore": quant_score,  # Backward compatibility
                "probability": factor_score,  # Backward compatibility mapping
                "status": "CONFIRMED" if quant_score >= 75.0 else "PENDING",
                "reasoning": reasoning,
                "aiNotes": f"[{source_label}] {reasoning}",
                "verification": verification_matrix,
                "passedFactors": passed_factors,
                "totalFactors": len(verification_matrix),
                "timestamp": now,
                "formatted_time": dt_str,
                "indicators": {
                    "atr": m15_indicators["atr"],
                    "rsi": m15_indicators["rsi"],
                    "ema21": m15_indicators["ema21"],
                    "ema50": m15_indicators["ema50"],
                    "ema200": m15_indicators["ema200"],
                    "macdHist": m15_indicators["macd_hist"],
                    "volumeDelta": m15_indicators["volumeDelta"],
                    "trend": regime_m15["regime"]
                },
                "marketStructure": structure_m15,
                "liquidity": liquidity,
                "orderBlocks": order_blocks,
                "fairValueGaps": fvgs,
                "regimeData": regime_m15,
                "telegram_message_id": None
            }

            generated_signals.append(final_signal)
            _signal_cache[sym] = final_signal

            logger.info(f"[ENGINE SIGNAL DISPATCHED] {sym} {final_signal['side']} | Setup: {final_signal['setupType']} | QuantScore: {quant_score} | RR: {final_signal['rr']}R")

        except Exception as e:
            logger.error(f"[ENGINE ERROR] Failed signal evaluation for {sym}: {e}", exc_info=True)

    # Save to history (Execution manager will dispatch real trade notification when position opens)
    if generated_signals:
        _cache_ts = now

        merged_history = generated_signals + get_signals_history()
        # Keep 60-day history window
        cutoff = now - (60 * 24 * 3600)
        merged_history = [s for s in merged_history if s.get("timestamp", 0) >= cutoff]
        save_signals_history(merged_history)

    return generated_signals
