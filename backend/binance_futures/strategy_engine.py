from typing import Dict, Any, List, Optional, Tuple
import math
import time
from datetime import datetime, timezone

from .config import DEFAULT_CONFIG
from .market_data import MarketDataManager


class ETHM5SuperTrendStrategy:
    """
    APEX QUANT v3.4 Institutional M5 SuperTrend Engine
    ===================================================
    Audited Parameters:
    - Primary Execution Timeframe: M5 (5-minute completed bars)
    - Core Engine: SuperTrend (Period: 10, Multiplier: 2.5)
    - Macro Trend Gate: H1 EMA 200 (Long only if H1 Close > EMA200; Short only if H1 Close < EMA200)
    - Volume Filter: M5 Volume >= 1.30x (10-bar prior average)
    - Trading Window: 07:00 - 21:00 UTC (Institutional London & NY liquidity)
    - Stop Loss: SuperTrend Line + 0.20 ATR buffer (Minimum $10.00 distance)
    - Take Profit: 2.0R (Full exit at 2.0x Risk distance)
    - Risk Model: Strictly 1.0% account equity per trade
    """

    def __init__(self, market_data: MarketDataManager):
        self.md = market_data
        self.last_evaluated_candle_time: int = 0
        self.last_triggered_flip_time: int = 0

    def evaluate_setup(self, risk_status: Dict[str, Any], is_closed_bar: bool = False) -> Dict[str, Any]:
        """
        Evaluates current multi-timeframe state and returns actionable signal or precise rejection reason.
        is_closed_bar: If True, indicates evaluation is occurring on a confirmed completed candle close.
        Only completed candle closes can consume/record self.last_triggered_flip_time.
        """
        current_price = self.md.get_current_price()
        now_utc = datetime.now(timezone.utc)
        current_hour = now_utc.hour

        # 1. Hard Filter: Risk Manager Pre-Flight Checks
        if not risk_status.get("can_trade", False):
            return self._build_result(
                "NONE", 0, "Risk limits active",
                risk_status.get("reason", "Risk limits active"),
                {"risk_guard": {"pass": False, "desc": risk_status.get("reason", "Risk limits active")}}
            )

        # 2. Hard Filter: Institutional Trading Window (07:00 - 21:00 UTC)
        sess_info = self.md.get_current_session()
        is_window_active = (DEFAULT_CONFIG.session_start_hour_utc <= current_hour < DEFAULT_CONFIG.session_end_hour_utc)
        if not is_window_active:
            return self._build_result(
                "NONE", 0, "Out of session",
                f"Trading Window Closed: Active 07:00-21:00 UTC (Current: {sess_info.get('utc_time', 'N/A')}).",
                {"session": {"pass": False, "desc": f"Hour {current_hour} UTC outside [7, 21)"}}
            )

        # 3. Hard Filter: Spread Check
        spread_info = self.md.get_spread()
        if not spread_info.get("acceptable", True):
            return self._build_result(
                "NONE", 0, "Spread excessive",
                f"Spread too high: {spread_info.get('spread_usd', 0):.2f} USDT > ${DEFAULT_CONFIG.max_allowed_spread_usd} limit",
                {"spread": {"pass": False, "desc": f"Spread {spread_info.get('spread_usd', 0):.2f} USDT"}}
            )

        # 4. Hard Filter: Minimum Candle Buffers
        m5_candles = self.md.klines_m5
        if len(m5_candles) < DEFAULT_CONFIG.st_period + 2:
            return self._build_result(
                "NONE", 0, "Buffering candles",
                f"Buffering M5 candles: {len(m5_candles)}/{DEFAULT_CONFIG.st_period + 2}",
                {"buffer": {"pass": False, "desc": f"Need {DEFAULT_CONFIG.st_period + 2} M5 candles"}}
            )

        h1_candles = self.md.klines_h1
        if len(h1_candles) < 20:
            return self._build_result(
                "NONE", 0, "Buffering H1 candles",
                f"Buffering H1 candles: {len(h1_candles)}/20",
                {"buffer": {"pass": False, "desc": "Buffering H1 candles"}}
            )

        # 5. Volatility Floor: Minimum M5 ATR
        atr_m5 = self.md.get_atr_m5() or 2.50
        if atr_m5 < DEFAULT_CONFIG.min_atr_m5:
            return self._build_result(
                "NONE", 15, "Low volatility dead zone",
                f"Anti-Chop: ATR M5 (${atr_m5:.2f}) < ${DEFAULT_CONFIG.min_atr_m5:.2f} threshold",
                {"anti_chop": {"pass": False, "desc": f"ATR M5 (${atr_m5:.2f}) < ${DEFAULT_CONFIG.min_atr_m5:.2f}"}}
            )

        # ----------------------------------------------------------------------
        # MACRO FILTER: H1 EMA 200
        # ----------------------------------------------------------------------
        h1_closes = [c["close"] for c in h1_candles]
        h1_period = min(DEFAULT_CONFIG.h1_ema_period, len(h1_closes))
        h1_ema_series = self.md.calculate_ema(h1_closes, h1_period)
        
        if not h1_ema_series:
            h1_trend = "NEUTRAL"
            h1_last_ema = current_price
        else:
            h1_last_ema = h1_ema_series[-1]
            last_h1_close = h1_closes[-1]
            if last_h1_close > h1_last_ema:
                h1_trend = "BULLISH"
            elif last_h1_close < h1_last_ema:
                h1_trend = "BEARISH"
            else:
                h1_trend = "NEUTRAL"

        # ----------------------------------------------------------------------
        # PRIMARY ENGINE: M5 SUPERTREND (10, 2.5)
        # ----------------------------------------------------------------------
        st_vals, st_dirs = self.md.calculate_supertrend(
            m5_candles,
            period=DEFAULT_CONFIG.st_period,
            multiplier=DEFAULT_CONFIG.st_multiplier
        )

        curr_c = m5_candles[-1]
        candle_close = curr_c["close"]
        candle_time = curr_c["time"]
        
        curr_st_dir = st_dirs[-1]
        prev_st_dir = st_dirs[-2]
        curr_st_val = st_vals[-1]

        # Volume Expansion Ratio (Current completed M5 volume / 10-bar average)
        if len(m5_candles) >= 12:
            prior_vols = [c["volume"] for c in m5_candles[-11:-1]]
            vol_avg_10 = sum(prior_vols) / len(prior_vols)
        else:
            vol_avg_10 = curr_c["volume"]
        vol_ratio = curr_c["volume"] / max(1.0, vol_avg_10)

        # Telemetry Matrix
        matrix = {
            "timeframe": "5m",
            "supertrend": {
                "period": DEFAULT_CONFIG.st_period,
                "multiplier": DEFAULT_CONFIG.st_multiplier,
                "value": round(curr_st_val, 2),
                "direction": "BULLISH" if curr_st_dir == 1 else "BEARISH",
                "prev_direction": "BULLISH" if prev_st_dir == 1 else "BEARISH",
                "flip": curr_st_dir != prev_st_dir
            },
            "macro_h1": {
                "ema_period": h1_period,
                "ema_value": round(h1_last_ema, 2),
                "trend": h1_trend,
                "aligned": (curr_st_dir == 1 and h1_trend == "BULLISH") or (curr_st_dir == -1 and h1_trend == "BEARISH")
            },
            "volume": {
                "current_bar": round(curr_c["volume"], 2),
                "avg_10": round(vol_avg_10, 2),
                "ratio": round(vol_ratio, 2),
                "passed": vol_ratio >= DEFAULT_CONFIG.volume_ratio_min
            },
            "atr_m5": round(atr_m5, 2),
            "session": sess_info.get("session", "UNKNOWN"),
            "window_utc": f"{DEFAULT_CONFIG.session_start_hour_utc:02d}:00-{DEFAULT_CONFIG.session_end_hour_utc:02d}:00 UTC",
            "risk_pct": f"{DEFAULT_CONFIG.max_risk_pct_balance * 100:.1f}%"
        }

        # ----------------------------------------------------------------------
        # DETECT SUPERTREND FLIP SETUP
        # ----------------------------------------------------------------------
        is_bull_flip = (prev_st_dir == -1 and curr_st_dir == 1)
        is_bear_flip = (prev_st_dir == 1 and curr_st_dir == -1)

        if not (is_bull_flip or is_bear_flip):
            current_mode = "BULLISH" if curr_st_dir == 1 else "BEARISH"
            return self._build_result(
                "NONE", 50,
                f"M5 SuperTrend {current_mode} (Awaiting Flip)",
                f"Awaiting M5 SuperTrend Flip (Current: {current_mode}, H1: {h1_trend}, Vol: {vol_ratio:.2f}x)",
                matrix
            )

        # Prevent duplicate entries on the same completed M5 bar
        if is_closed_bar and candle_time == self.last_triggered_flip_time:
            return self._build_result(
                "NONE", 50,
                "Already processed candle",
                f"Flip on M5 candle {candle_time} already processed.",
                matrix
            )

        # ----------------------------------------------------------------------
        # LONG SETUP QUALIFICATION
        # ----------------------------------------------------------------------
        if is_bull_flip:
            # Check 1: Macro Trend (H1 Close > EMA 200)
            if h1_trend != "BULLISH":
                return self._build_result(
                    "NONE", 40, "Macro Filter Veto",
                    f"H1 Macro Filter Veto: H1 trend is {h1_trend} (Price ${candle_close:.2f} vs H1 EMA{h1_period} ${h1_last_ema:.2f})",
                    matrix
                )

            # Check 2: Volume Expansion >= 1.30x
            if vol_ratio < DEFAULT_CONFIG.volume_ratio_min:
                return self._build_result(
                    "NONE", 45, "Volume Filter Veto",
                    f"Volume Veto: M5 Volume ratio ({vol_ratio:.2f}x) < {DEFAULT_CONFIG.volume_ratio_min:.1f}x threshold",
                    matrix
                )

            # Geometry Calculation: Stop Loss & 2.0R Take Profit
            raw_sl_dist = (candle_close - curr_st_val) + (DEFAULT_CONFIG.sl_buffer_atr * atr_m5)
            max_sl = getattr(DEFAULT_CONFIG, "max_sl_dist", 40.0)
            sl_dist = min(max_sl, max(DEFAULT_CONFIG.min_sl_dist, raw_sl_dist))
            sl_price = round(candle_close - sl_dist, 2)
            tp_price = round(candle_close + (DEFAULT_CONFIG.tp1_r * sl_dist), 2)
            be_price = round(candle_close * (1.0 + DEFAULT_CONFIG.be_fee_buffer_pct), 2)

            if is_closed_bar:
                self.last_triggered_flip_time = candle_time
            score = 88

            reason_summary = (
                f"LONG M5 SuperTrend Bull Flip | H1 EMA{h1_period} Bullish | "
                f"Vol {vol_ratio:.2f}x >= 1.3x | SL: ${sl_price:.2f} (-${sl_dist:.2f}) | TP: ${tp_price:.2f} (+2.0R)"
            )

            return self._build_result(
                "LONG",
                score,
                reason_summary,
                "Setup Qualified (M5 SuperTrend 10/2.5 Bull Flip + H1 EMA200 + Volume 1.3x)",
                matrix,
                entry=candle_close,
                sl=sl_price,
                tp1=tp_price,
                tp2=tp_price,
                be=be_price,
                r_dist=round(sl_dist, 2),
                module="M5_SUPERTREND_BULL_FLIP"
            )

        # ----------------------------------------------------------------------
        # SHORT SETUP QUALIFICATION
        # ----------------------------------------------------------------------
        elif is_bear_flip:
            # Check 1: Macro Trend (H1 Close < EMA 200)
            if h1_trend != "BEARISH":
                return self._build_result(
                    "NONE", 40, "Macro Filter Veto",
                    f"H1 Macro Filter Veto: H1 trend is {h1_trend} (Price ${candle_close:.2f} vs H1 EMA{h1_period} ${h1_last_ema:.2f})",
                    matrix
                )

            # Check 2: Volume Expansion >= 1.30x
            if vol_ratio < DEFAULT_CONFIG.volume_ratio_min:
                return self._build_result(
                    "NONE", 45, "Volume Filter Veto",
                    f"Volume Veto: M5 Volume ratio ({vol_ratio:.2f}x) < {DEFAULT_CONFIG.volume_ratio_min:.1f}x threshold",
                    matrix
                )

            # Geometry Calculation: Stop Loss & 2.0R Take Profit
            raw_sl_dist = (curr_st_val - candle_close) + (DEFAULT_CONFIG.sl_buffer_atr * atr_m5)
            max_sl = getattr(DEFAULT_CONFIG, "max_sl_dist", 40.0)
            sl_dist = min(max_sl, max(DEFAULT_CONFIG.min_sl_dist, raw_sl_dist))
            sl_price = round(candle_close + sl_dist, 2)
            tp_price = round(candle_close - (DEFAULT_CONFIG.tp1_r * sl_dist), 2)
            be_price = round(candle_close * (1.0 - DEFAULT_CONFIG.be_fee_buffer_pct), 2)

            if is_closed_bar:
                self.last_triggered_flip_time = candle_time
            score = 88

            reason_summary = (
                f"SHORT M5 SuperTrend Bear Flip | H1 EMA{h1_period} Bearish | "
                f"Vol {vol_ratio:.2f}x >= 1.3x | SL: ${sl_price:.2f} (+${sl_dist:.2f}) | TP: ${tp_price:.2f} (+2.0R)"
            )

            return self._build_result(
                "SHORT",
                score,
                reason_summary,
                "Setup Qualified (M5 SuperTrend 10/2.5 Bear Flip + H1 EMA200 + Volume 1.3x)",
                matrix,
                entry=candle_close,
                sl=sl_price,
                tp1=tp_price,
                tp2=tp_price,
                be=be_price,
                r_dist=round(sl_dist, 2),
                module="M5_SUPERTREND_BEAR_FLIP"
            )

        return self._build_result("NONE", 0, "No setup", "No setup pattern matched", matrix)

    def _build_result(self, direction: str, score: int, reason: str, rejection_reason: str,
                      matrix: Dict[str, Any], entry: float = 0.0, sl: float = 0.0,
                      tp1: float = 0.0, tp2: float = 0.0, be: float = 0.0, r_dist: float = 0.0,
                      module: str = "") -> Dict[str, Any]:
        return {
            "final_signal": direction,
            "score": score,
            "reason": reason,
            "rejection_reason": rejection_reason,
            "matrix": matrix,
            "entry_price": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "tp": tp2,
            "be_price": be,
            "r_distance": r_dist,
            "module": module,
            "timestamp": int(time.time() * 1000)
        }


# Maintain backward compatibility for existing imports
ETHM1ScalpingStrategy = ETHM5SuperTrendStrategy
