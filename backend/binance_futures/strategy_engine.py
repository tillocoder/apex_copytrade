from typing import Dict, Any, List, Optional, Tuple
import math

from .config import DEFAULT_CONFIG
from .market_data import MarketDataManager

class ETHM1ScalpingStrategy:
    """
    Production M1 Scalping Strategy for ETHUSDT.P:
    - Balanced, Non-Overfiltered Execution Model:
      1. Market Bias (H1/M15 trend direction, rejects only strong opposing trend)
      2. M1 Trigger (at least ONE: Sweep+Reclaim, BOS+Retest, Impulse+Retest)
      3. Confirmation (at least ONE: Momentum, Volume, EMA Bounce, M5 Structure)
      4. Confluence Score >= 65/100
      5. Anti-Chase Quality Filter (skips overextended candles)
    - Professional 2-Stage Exit Plan (TP1 1R 50% + Breakeven fee buffer, TP2 2R 50%)
    """
    def __init__(self, market_data: MarketDataManager):
        self.md = market_data

    def evaluate_setup(self, risk_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates current multi-timeframe state and returns actionable signal or precise rejection reason.
        """
        # Hard Filter 1: Risk Manager Pre-Flight Checks
        if not risk_status.get("can_trade", False):
            return self._build_result(
                "NONE", 0, "No setup",
                risk_status.get("reason", "Risk limits active"),
                {}
            )

        # Hard Filter 2: Spread Check
        spread_info = self.md.get_spread()
        if not spread_info.get("acceptable", True):
            return self._build_result(
                "NONE", 0, "No setup",
                f"Spread too high: {spread_info.get('spread_usd', 0):.2f} USDT > ${DEFAULT_CONFIG.max_allowed_spread_usd} limit",
                {"spread": {"pass": False, "desc": f"Spread {spread_info.get('spread_usd', 0):.2f} USDT"}}
            )

        # Hard Filter 3: Minimum M1 candles buffered
        if len(self.md.klines_m1) < 25:
            return self._build_result(
                "NONE", 0, "No setup",
                f"Buffering M1 candles ({len(self.md.klines_m1)}/25 ready)",
                {}
            )

        m1_candles = self.md.klines_m1
        m5_candles = self.md.klines_m5 if len(self.md.klines_m5) >= 10 else m1_candles
        h1_candles = self.md.klines_h1 if len(self.md.klines_h1) >= 6 else m5_candles

        current_price = self.md.get_current_price()
        atr_m1 = self.md.get_atr_m1() or 1.2

        # Hard Filter 4: Anti-Chop Floor
        if atr_m1 < DEFAULT_CONFIG.min_atr_m1:
            return self._build_result(
                "NONE", 15, "Market in low-volatility dead zone",
                f"Anti-Chop: ATR M1 ({atr_m1:.2f}) < {DEFAULT_CONFIG.min_atr_m1:.2f} threshold",
                {
                    "bias": {"pass": False, "desc": "Low Volatility / Chop"},
                    "m1_trigger": {"pass": False, "desc": "Waiting for ATR expansion"},
                    "confirmation": {"pass": False, "desc": "Dead zone filter active"},
                    "score_gate": {"pass": False, "desc": "Score 15/100 (< 65)"},
                    "anti_chase": {"pass": True, "desc": "Normal candle size"},
                    "risk_guard": {"pass": False, "desc": f"Anti-Chop: ATR ({atr_m1:.2f}) < {DEFAULT_CONFIG.min_atr_m1:.2f}"}
                }
            )

        # Hard Filter 5: Anti-Chase Filter (if current candle body is excessively bloated > 2.2x ATR)
        curr_c = m1_candles[-1]
        curr_body = abs(curr_c["close"] - curr_c["open"])
        if curr_body > DEFAULT_CONFIG.anti_chase_max_body_atr * atr_m1:
            return self._build_result(
                "NONE", 30, "Candle overextended",
                f"Anti-Chase: M1 candle body (${curr_body:.2f}) > {DEFAULT_CONFIG.anti_chase_max_body_atr}x ATR. Skip chasing.",
                {}
            )

        # --- STEP 1: MARKET BIAS (H1 & M15) ---
        bias_res = self._evaluate_bias(h1_candles, m15_candles=self.md.klines_m15, current_price=current_price)
        h1_trend = bias_res["h1_trend"]
        bias_score = bias_res["score"]

        # Evaluate both LONG and SHORT possibilities
        long_eval = self._evaluate_direction("LONG", m1_candles, m5_candles, current_price, atr_m1, h1_trend, bias_score)
        short_eval = self._evaluate_direction("SHORT", m1_candles, m5_candles, current_price, atr_m1, h1_trend, bias_score)

        # Select the higher scoring setup
        best_eval = long_eval if long_eval["score"] >= short_eval["score"] else short_eval
        other_eval = short_eval if best_eval == long_eval else long_eval

        # Check if the best setup meets the execution criteria
        if best_eval["score"] >= DEFAULT_CONFIG.min_score_threshold and best_eval["has_trigger"] and best_eval["has_confirm"]:
            # Valid Entry Signal!
            return self._build_result(
                best_eval["direction"],
                best_eval["score"],
                best_eval["reason"],
                "Setup Qualified (Confluence >= 65)",
                best_eval["matrix"],
                best_eval["entry_price"],
                best_eval["sl"],
                best_eval["tp1"],
                best_eval["tp2"],
                best_eval["be_price"],
                best_eval["r_dist"]
            )
        else:
            # Rejection with specific clear reason
            rejection = best_eval.get("rejection_reason") or "Waiting for valid M1 trigger + confirmation"
            return self._build_result(
                "NONE",
                best_eval["score"],
                best_eval.get("reason", "Scanning M1 market structure..."),
                rejection,
                best_eval.get("matrix", {})
            )

    def _evaluate_bias(self, h1_candles: List[Dict[str, Any]], m15_candles: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """
        Determines general bias: BULLISH, BEARISH, or NEUTRAL.
        Rejects strong opposing trend.
        """
        h1_closes = [c["close"] for c in h1_candles]
        h1_ema20 = self.md.calculate_ema(h1_closes, min(20, len(h1_closes)))
        h1_ema50 = self.md.calculate_ema(h1_closes, min(50, len(h1_closes)))

        h1_trend = "NEUTRAL"
        score = 15  # Default neutral bias score

        if h1_ema20 and h1_ema50:
            e20 = h1_ema20[-1]
            e50 = h1_ema50[-1]
            if e20 > e50 and current_price >= e50 * 0.999:
                h1_trend = "BULLISH"
                score = 25
            elif e20 < e50 and current_price <= e50 * 1.001:
                h1_trend = "BEARISH"
                score = 25
        else:
            slope = (h1_closes[-1] - h1_closes[0]) / max(1.0, h1_closes[0])
            if slope > 0.002:
                h1_trend = "BULLISH"
                score = 22
            elif slope < -0.002:
                h1_trend = "BEARISH"
                score = 22

        return {"h1_trend": h1_trend, "score": score}

    def _evaluate_direction(self, direction: str, m1_candles: List[Dict[str, Any]], m5_candles: List[Dict[str, Any]],
                            current_price: float, atr_m1: float, h1_trend: str, bias_score: int) -> Dict[str, Any]:
        """
        Evaluates setup for either LONG or SHORT:
        - Opposing trend rejection
        - M1 Trigger: Sweep+Reclaim, BOS+Retest, Impulse+Retest
        - Confirmation: Momentum, Volume, EMA bounce, M5 structure
        - Confluence Scoring & SL/TP math
        """
        # Opposing trend check
        if direction == "LONG" and h1_trend == "BEARISH":
            return {
                "direction": direction,
                "score": 10,
                "has_trigger": False,
                "has_confirm": False,
                "reason": "Opposing H1 Bearish Trend",
                "rejection_reason": "Opposing H1 Trend: Bearish bias rejects Long entries",
                "matrix": {"bias": {"pass": False, "desc": "Opposing H1 Bearish Trend"}}
            }
        if direction == "SHORT" and h1_trend == "BULLISH":
            return {
                "direction": direction,
                "score": 10,
                "has_trigger": False,
                "has_confirm": False,
                "reason": "Opposing H1 Bullish Trend",
                "rejection_reason": "Opposing H1 Trend: Bullish bias rejects Short entries",
                "matrix": {"bias": {"pass": False, "desc": "Opposing H1 Bullish Trend"}}
            }

        matrix: Dict[str, Any] = {
            "bias": {"pass": True, "desc": f"Bias: {h1_trend} ({bias_score} pts)"}
        }

        # --- STEP 2: M1 TRIGGER CHECK (At least ONE required) ---
        triggers_hit = []
        trigger_score = 0
        swing_level = current_price

        # A. Liquidity Sweep + Reclaim
        # For LONG: look for sweep of recent 6-12 candle low
        if direction == "LONG":
            prior_low = min(c["low"] for c in m1_candles[-12:-2]) if len(m1_candles) >= 12 else m1_candles[-3]["low"]
            # Triggered if recent low dipped below prior_low and current close is back above prior_low
            recent_min = min(c["low"] for c in m1_candles[-3:])
            if recent_min < prior_low and current_price > prior_low:
                triggers_hit.append("Sweep+Reclaim")
                swing_level = recent_min
        else: # SHORT
            prior_high = max(c["high"] for c in m1_candles[-12:-2]) if len(m1_candles) >= 12 else m1_candles[-3]["high"]
            recent_max = max(c["high"] for c in m1_candles[-3:])
            if recent_max > prior_high and current_price < prior_high:
                triggers_hit.append("Sweep+Reclaim")
                swing_level = recent_max

        # B. Break of Structure (BOS) + Retest
        if direction == "LONG":
            m1_highs = [c["high"] for c in m1_candles[-10:-3]]
            local_res = max(m1_highs) if m1_highs else current_price
            # Broken by recent candle and currently holding above/near
            if m1_candles[-2]["close"] > local_res and current_price >= local_res * 0.9992:
                triggers_hit.append("BOS+Retest")
                swing_level = min(c["low"] for c in m1_candles[-5:])
        else: # SHORT
            m1_lows = [c["low"] for c in m1_candles[-10:-3]]
            local_sup = min(m1_lows) if m1_lows else current_price
            if m1_candles[-2]["close"] < local_sup and current_price <= local_sup * 1.0008:
                triggers_hit.append("BOS+Retest")
                swing_level = max(c["high"] for c in m1_candles[-5:])

        # C. Impulse Breakout + Retest / Continuation
        avg_body = sum(abs(c["close"] - c["open"]) for c in m1_candles[-10:]) / 10.0
        last_body = abs(m1_candles[-2]["close"] - m1_candles[-2]["open"])
        if direction == "LONG":
            is_bull_impulse = m1_candles[-2]["close"] > m1_candles[-2]["open"] and last_body >= 1.3 * avg_body
            if is_bull_impulse and current_price >= m1_candles[-2]["close"] * 0.9995:
                triggers_hit.append("Impulse Breakout")
                swing_level = min(m1_candles[-2]["low"], m1_candles[-1]["low"])
        else: # SHORT
            is_bear_impulse = m1_candles[-2]["close"] < m1_candles[-2]["open"] and last_body >= 1.3 * avg_body
            if is_bear_impulse and current_price <= m1_candles[-2]["close"] * 1.0005:
                triggers_hit.append("Impulse Breakout")
                swing_level = max(m1_candles[-2]["high"], m1_candles[-1]["high"])

        has_trigger = len(triggers_hit) > 0
        if has_trigger:
            trigger_score = 35 if len(triggers_hit) == 1 else 40
            matrix["m1_trigger"] = {"pass": True, "desc": f"{' + '.join(triggers_hit)} (+{trigger_score} pts)"}
        else:
            matrix["m1_trigger"] = {"pass": False, "desc": "No valid M1 trigger pattern"}

        # --- STEP 3: CONFIRMATIONS (At least ONE required) ---
        confirmations_hit = []
        confirm_score = 0

        # A. Momentum (Fast M1 RSI / Directional thrust)
        m1_closes = [c["close"] for c in m1_candles]
        rsi = self.md.calculate_rsi(m1_closes, 14)
        if direction == "LONG":
            if (rsi and rsi[-1] > 48 and rsi[-1] > rsi[-2]) or (m1_closes[-1] > m1_closes[-2] > m1_closes[-3]):
                confirmations_hit.append("Momentum")
                confirm_score += 10
        else:
            if (rsi and rsi[-1] < 52 and rsi[-1] < rsi[-2]) or (m1_closes[-1] < m1_closes[-2] < m1_closes[-3]):
                confirmations_hit.append("Momentum")
                confirm_score += 10

        # B. Volume Expansion (>= 1.15x 10-period volume SMA)
        vols = [c["volume"] for c in m1_candles]
        vol_sma = sum(vols[-10:]) / 10.0 if len(vols) >= 10 else vols[-1]
        recent_vol = max(vols[-2], vols[-1])
        if recent_vol >= 1.15 * vol_sma:
            confirmations_hit.append("Volume Expansion")
            confirm_score += 10

        # C. EMA / Pullback Bounce (EMA9 / EMA21 alignment)
        ema9 = self.md.calculate_ema(m1_closes, 9)
        ema21 = self.md.calculate_ema(m1_closes, 21)
        if ema9 and ema21:
            if direction == "LONG" and ema9[-1] >= ema21[-1] and current_price >= ema21[-1] * 0.9995:
                confirmations_hit.append("EMA9/21 Pullback Support")
                confirm_score += 10
            elif direction == "SHORT" and ema9[-1] <= ema21[-1] and current_price <= ema21[-1] * 1.0005:
                confirmations_hit.append("EMA9/21 Pullback Resistance")
                confirm_score += 10

        # D. M5 Structure Alignment
        if len(m5_candles) >= 5:
            m5_c = m5_candles[-1]
            if direction == "LONG" and m5_c["close"] >= m5_c["open"]:
                confirmations_hit.append("M5 Bullish Alignment")
                confirm_score += 10
            elif direction == "SHORT" and m5_c["close"] <= m5_c["open"]:
                confirmations_hit.append("M5 Bearish Alignment")
                confirm_score += 10

        has_confirm = len(confirmations_hit) > 0
        if has_confirm:
            matrix["confirmation"] = {"pass": True, "desc": f"{', '.join(confirmations_hit[:2])} (+{confirm_score} pts)"}
        else:
            matrix["confirmation"] = {"pass": False, "desc": "No secondary confirmation"}

        # Total Confluence Score
        total_score = bias_score + trigger_score + min(35, confirm_score)

        matrix["score_gate"] = {
            "pass": total_score >= DEFAULT_CONFIG.min_score_threshold,
            "desc": f"Score {total_score}/100 (Threshold {DEFAULT_CONFIG.min_score_threshold})"
        }
        matrix["anti_chase"] = {"pass": True, "desc": "Candle body optimal (< 2.2x ATR)"}
        matrix["risk_guard"] = {"pass": True, "desc": "Execution risk limits clear"}

        # SL / TP Math
        # Adaptive SL: structural swing level +/- 0.5x ATR, clamped between min_sl_pct and max_sl_pct
        if direction == "LONG":
            raw_sl = swing_level - 0.5 * atr_m1
            min_sl_price = current_price * (1.0 - DEFAULT_CONFIG.min_sl_pct)
            max_sl_price = current_price * (1.0 - DEFAULT_CONFIG.max_sl_pct)
            sl_price = max(max_sl_price, min(raw_sl, min_sl_price))
            r_dist = max(0.50, current_price - sl_price)
            tp1_price = round(current_price + (DEFAULT_CONFIG.tp1_r * r_dist), 2)
            tp2_price = round(current_price + (DEFAULT_CONFIG.tp2_r * r_dist), 2)
            be_price = round(current_price * (1.0 + DEFAULT_CONFIG.be_fee_buffer_pct), 2)
        else:
            raw_sl = swing_level + 0.5 * atr_m1
            min_sl_price = current_price * (1.0 + DEFAULT_CONFIG.min_sl_pct)
            max_sl_price = current_price * (1.0 + DEFAULT_CONFIG.max_sl_pct)
            sl_price = min(max_sl_price, max(raw_sl, min_sl_price))
            r_dist = max(0.50, sl_price - current_price)
            tp1_price = round(current_price - (DEFAULT_CONFIG.tp1_r * r_dist), 2)
            tp2_price = round(current_price - (DEFAULT_CONFIG.tp2_r * r_dist), 2)
            be_price = round(current_price * (1.0 - DEFAULT_CONFIG.be_fee_buffer_pct), 2)

        sl_price = round(sl_price, 2)

        # Build precise reason
        reason_summary = f"{direction} Setup: {', '.join(triggers_hit)} with {', '.join(confirmations_hit[:2])} (Score: {total_score}/100)"
        
        # Build rejection reason if not qualified
        rejection_reason = None
        if not has_trigger:
            rejection_reason = "No M1 Trigger: Waiting for Sweep+Reclaim, BOS, or Impulse Retest"
        elif not has_confirm:
            rejection_reason = "No Confirmation: Lacks volume expansion, momentum, or EMA alignment"
        elif total_score < DEFAULT_CONFIG.min_score_threshold:
            rejection_reason = f"Confluence Score {total_score}/100 is below {DEFAULT_CONFIG.min_score_threshold} threshold"

        return {
            "direction": direction,
            "score": total_score,
            "has_trigger": has_trigger,
            "has_confirm": has_confirm,
            "reason": reason_summary,
            "rejection_reason": rejection_reason,
            "matrix": matrix,
            "entry_price": current_price,
            "sl": sl_price,
            "tp1": tp1_price,
            "tp2": tp2_price,
            "be_price": be_price,
            "r_dist": r_dist
        }

    def _build_result(self, signal: str, score: int, reason: str, rejection_reason: str,
                      matrix: Dict[str, Any], entry_price: float = 0.0, sl: float = 0.0,
                      tp1: float = 0.0, tp2: float = 0.0, be_price: float = 0.0, r_dist: float = 0.0) -> Dict[str, Any]:
        return {
            "final_signal": signal,
            "score": score,
            "reason": reason,
            "rejection_reason": rejection_reason,
            "matrix": matrix,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp2,           # default full TP
            "tp1": tp1,         # 1R target (50% close)
            "tp2": tp2,         # 2R target (remaining 50% close)
            "be_price": be_price, # Breakeven + fee buffer level
            "r_distance": round(r_dist, 2),
            "risk_reward": DEFAULT_CONFIG.tp2_r
        }
