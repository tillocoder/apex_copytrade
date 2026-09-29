from typing import Dict, Any, List, Optional, Tuple
import math
import time
from datetime import datetime, timezone

from .config import DEFAULT_CONFIG
from .market_data import MarketDataManager


class ETHM1ScalpingStrategy:
    """
    APEX QUANT v3.1 — M1 High-Frequency Strategy Engine
    ===================================================
    Architecture:
    1. Timeframe Decoupling:
       - M15 = Macro Context Only (Bias / additive score, NOT a mandatory hard filter)
       - M5  = Setup Context (Trend / Pullback bonus confirmation, NOT mandatory)
       - M1  = Primary Execution Timeframe (Evaluates every completed M1 candle)
    2. Five Independent M1 Setup Modules:
       - Module A: Liquidity Sweep + Reclaim (Base: 45 pts)
       - Module B: M1 Breakout + Retest (Base: 40 pts)
       - Module C: EMA Pullback (EMA9/21/50) (Base: 35 pts)
       - Module D: Momentum Impulse (Volume + ATR expansion) (Base: 35 pts)
       - Module E: M5 Structure + M1 Hybrid Trigger (Base: 40 pts)
    3. Modular Additive Scoring (0 to 100):
       - Base Module Score (35-45 pts)
       - M1 EMA Alignment (+15 pts)
       - M5 Context Alignment (+15 pts)
       - M15 Macro Context (+15 pts aligned, -10 pts counter-trend)
       - Volume / Momentum Expansion (+10 pts)
       - Configurable Threshold: >= 65 pts default
    4. Structural Risk & Multi-Model Exits:
       - Structural Stop Loss (recent swing low/high +/- 0.20x ATR buffer)
       - Clamped between min_sl_pct (0.20%) and max_sl_pct (0.85%)
       - 2-Stage Exits (TP1 = 1.25R, TP2 = 2.50R) with Breakeven fee buffer (Model B)
       - Fee-Aware Trade Filter: roundtrip friction must not exceed 30% of R target
       - Anti-Chop Floor (ATR >= 0.25 USDT) & Anti-Chase Guard (body <= 2.5x ATR)
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
                "NONE", 0, "Risk limits active",
                risk_status.get("reason", "Risk limits active"),
                {"risk_guard": {"pass": False, "desc": risk_status.get("reason", "Risk limits active")}}
            )

        # Hard Filter 2: Session Filter (Session window check)
        sess_info = self.md.get_current_session()
        if not sess_info.get("is_allowed", False):
            return self._build_result(
                "NONE", 0, "Out of session",
                f"Session Filter: Current session ({sess_info.get('session')}) disabled.",
                {"session": {"pass": False, "desc": f"Session {sess_info.get('session')} not allowed"}}
            )

        # Hard Filter 3: Spread Check
        spread_info = self.md.get_spread()
        if not spread_info.get("acceptable", True):
            return self._build_result(
                "NONE", 0, "Spread excessive",
                f"Spread too high: {spread_info.get('spread_usd', 0):.2f} USDT > ${DEFAULT_CONFIG.max_allowed_spread_usd} limit",
                {"spread": {"pass": False, "desc": f"Spread {spread_info.get('spread_usd', 0):.2f} USDT"}}
            )

        # Hard Filter 4: Minimum Candle Buffers
        if len(self.md.klines_m1) < 25:
            return self._build_result(
                "NONE", 0, "Buffering candles",
                f"Buffering M1 candles: {len(self.md.klines_m1)}/25",
                {"buffer": {"pass": False, "desc": "Buffering candles"}}
            )

        m1_candles = self.md.klines_m1
        m5_candles = self.md.klines_m5
        m15_candles = self.md.klines_m15

        current_price = self.md.get_current_price()
        atr_m1 = self.md.get_atr_m1() or 1.20

        # Hard Filter 5: Anti-Chop Floor (Dynamic Volatility Floor)
        if atr_m1 < DEFAULT_CONFIG.min_atr_m1:
            return self._build_result(
                "NONE", 15, "Low volatility dead zone",
                f"Anti-Chop: ATR M1 ({atr_m1:.2f}) < {DEFAULT_CONFIG.min_atr_m1:.2f} threshold",
                {"anti_chop": {"pass": False, "desc": f"ATR ({atr_m1:.2f}) < {DEFAULT_CONFIG.min_atr_m1:.2f}"}}
            )

        # Hard Filter 6: Anti-Chase Filter (Blow-off candle guard)
        curr_c = m1_candles[-1]
        curr_body = abs(curr_c["close"] - curr_c["open"])
        if curr_body > DEFAULT_CONFIG.anti_chase_max_body_atr * atr_m1:
            return self._build_result(
                "NONE", 30, "Candle overextended",
                f"Anti-Chase: M1 candle body (${curr_body:.2f}) > {DEFAULT_CONFIG.anti_chase_max_body_atr}x ATR. Skip chasing.",
                {"anti_chase": {"pass": False, "desc": "Candle overextended"}}
            )

        # ----------------------------------------------------------------------
        # MULTI-TIMEFRAME CONTEXT (INFORMATIONAL / BIAS — NOT MANDATORY VETO)
        # ----------------------------------------------------------------------
        # M15 Macro Context
        m15_context = "NEUTRAL"
        m15_score_adj = 0
        if len(m15_candles) >= 15:
            m15_closes = [c["close"] for c in m15_candles]
            m15_e50 = self.md.calculate_ema(m15_closes, min(50, len(m15_closes)))
            if m15_e50:
                if current_price > m15_e50[-1]:
                    m15_context = "BULLISH"
                elif current_price < m15_e50[-1]:
                    m15_context = "BEARISH"

        # M5 Setup Context
        m5_setup = "NONE"
        if len(m5_candles) >= 15:
            m5_closes = [c["close"] for c in m5_candles]
            m5_e21 = self.md.calculate_ema(m5_closes, min(21, len(m5_closes)))
            m5_e50 = self.md.calculate_ema(m5_closes, min(50, len(m5_closes)))
            if m5_e21 and m5_e50:
                if m5_e21[-1] > m5_e50[-1]:
                    m5_setup = "M5_BULL_TREND"
                elif m5_e21[-1] < m5_e50[-1]:
                    m5_setup = "M5_BEAR_TREND"

        # M1 Indicators
        m1_closes = [c["close"] for c in m1_candles]
        m1_e9 = self.md.calculate_ema(m1_closes, 9)
        m1_e21 = self.md.calculate_ema(m1_closes, 21)
        m1_e50 = self.md.calculate_ema(m1_closes, min(50, len(m1_closes)))

        if not m1_e9 or not m1_e21:
            return self._build_result("NONE", 0, "Buffering M1 EMAs", "Insufficient M1 history", {})

        # ----------------------------------------------------------------------
        # EVALUATE 5 INDEPENDENT M1 SETUP MODULES
        # ----------------------------------------------------------------------
        signal_candidate = None
        module_name = ""
        base_score = 0
        module_desc = ""

        recent_m1_low = min(c["low"] for c in m1_candles[-12:-1])
        recent_m1_high = max(c["high"] for c in m1_candles[-12:-1])

        # --- MODULE A: LIQUIDITY SWEEP & RECLAIM ---
        swept_low = any(c["low"] <= recent_m1_low for c in m1_candles[-2:])
        if swept_low and current_price > recent_m1_low and curr_c["close"] >= curr_c["open"]:
            signal_candidate = "LONG"
            module_name = "MODULE_A_SWEEP_RECLAIM"
            base_score = 45
            module_desc = f"M1 Liquidity Sweep of ${recent_m1_low:.2f} & Bullish Reclaim"
        else:
            swept_high = any(c["high"] >= recent_m1_high for c in m1_candles[-2:])
            if swept_high and current_price < recent_m1_high and curr_c["close"] <= curr_c["open"]:
                signal_candidate = "SHORT"
                module_name = "MODULE_A_SWEEP_RECLAIM"
                base_score = 45
                module_desc = f"M1 Liquidity Sweep of ${recent_m1_high:.2f} & Bearish Reclaim"

        # --- MODULE B: M1 BREAKOUT & RETEST ---
        if not signal_candidate and len(m1_candles) >= 16:
            prior_high = max(c["high"] for c in m1_candles[-15:-2])
            prior_low = min(c["low"] for c in m1_candles[-15:-2])
            range_width = prior_high - prior_low
            if range_width <= 2.2 * atr_m1:
                if current_price > prior_high and curr_c["close"] > curr_c["open"]:
                    signal_candidate = "LONG"
                    module_name = "MODULE_B_BREAKOUT"
                    base_score = 40
                    module_desc = f"M1 Consolidation Breakout Above ${prior_high:.2f}"
                elif current_price < prior_low and curr_c["close"] < curr_c["open"]:
                    signal_candidate = "SHORT"
                    module_name = "MODULE_B_BREAKOUT"
                    base_score = 40
                    module_desc = f"M1 Consolidation Breakdown Below ${prior_low:.2f}"

        # --- MODULE C: EMA PULLBACK ---
        if not signal_candidate:
            e9 = m1_e9[-1]
            e21 = m1_e21[-1]
            # LONG: EMA9 > EMA21, price tests EMA9/EMA21 zone and holds
            if e9 > e21 and curr_c["low"] <= e9 * 1.0008 and current_price >= e21 * 0.9995:
                if curr_c["close"] >= curr_c["open"]:
                    signal_candidate = "LONG"
                    module_name = "MODULE_C_EMA_PULLBACK"
                    base_score = 35
                    module_desc = "M1 EMA9/EMA21 Dynamic Pullback Support"
            # SHORT: EMA9 < EMA21, price tests EMA9/EMA21 zone and rejects
            elif e9 < e21 and curr_c["high"] >= e9 * 0.9992 and current_price <= e21 * 1.0005:
                if curr_c["close"] <= curr_c["open"]:
                    signal_candidate = "SHORT"
                    module_name = "MODULE_C_EMA_PULLBACK"
                    base_score = 35
                    module_desc = "M1 EMA9/EMA21 Dynamic Pullback Resistance"

        # --- MODULE D: MOMENTUM IMPULSE ---
        if not signal_candidate and len(m1_candles) >= 11:
            vol_avg = sum(c["volume"] for c in m1_candles[-10:-1]) / 9.0
            if curr_c["volume"] >= 1.25 * vol_avg and curr_body >= 0.7 * atr_m1:
                if curr_c["close"] > curr_c["open"] and m1_e9[-1] > m1_e21[-1]:
                    signal_candidate = "LONG"
                    module_name = "MODULE_D_MOMENTUM_IMPULSE"
                    base_score = 35
                    module_desc = "M1 High-Volume Bullish Momentum Impulse"
                elif curr_c["close"] < curr_c["open"] and m1_e9[-1] < m1_e21[-1]:
                    signal_candidate = "SHORT"
                    module_name = "MODULE_D_MOMENTUM_IMPULSE"
                    base_score = 35
                    module_desc = "M1 High-Volume Bearish Momentum Impulse"

        # --- MODULE E: M5 STRUCTURE + M1 TRIGGER ---
        if not signal_candidate and m5_setup != "NONE":
            if m5_setup == "M5_BULL_TREND" and current_price > m1_e21[-1] and curr_c["close"] > curr_c["open"]:
                signal_candidate = "LONG"
                module_name = "MODULE_E_M5_M1_HYBRID"
                base_score = 40
                module_desc = "M5 Bull Trend + M1 Confirmation Hybrid"
            elif m5_setup == "M5_BEAR_TREND" and current_price < m1_e21[-1] and curr_c["close"] < curr_c["open"]:
                signal_candidate = "SHORT"
                module_name = "MODULE_E_M5_M1_HYBRID"
                base_score = 40
                module_desc = "M5 Bear Trend + M1 Confirmation Hybrid"

        if not signal_candidate:
            return self._build_result(
                "NONE", 25, "Scanning for M1 setup...",
                "Waiting for valid M1 setup: Sweep+Reclaim, Breakout, EMA Pullback, or Momentum",
                {
                    "m15_context": {"pass": True, "desc": f"M15 Context: {m15_context}"},
                    "m5_setup": {"pass": m5_setup != "NONE", "desc": f"M5 Setup: {m5_setup}"},
                    "m1_trigger": {"pass": False, "desc": "No active M1 module trigger"}
                }
            )

        # ----------------------------------------------------------------------
        # MODULAR ADDITIVE SCORING SYSTEM (0-100)
        # ----------------------------------------------------------------------
        total_score = base_score
        matrix: Dict[str, Any] = {
            "module": {"pass": True, "desc": f"{module_name} (+{base_score} pts)"}
        }

        # M1 EMA Alignment (+15)
        m1_aligned = False
        if signal_candidate == "LONG" and m1_e9[-1] > m1_e21[-1]:
            total_score += 15
            m1_aligned = True
        elif signal_candidate == "SHORT" and m1_e9[-1] < m1_e21[-1]:
            total_score += 15
            m1_aligned = True
        matrix["m1_alignment"] = {"pass": m1_aligned, "desc": "M1 EMA9/EMA21 Aligned (+15 pts)" if m1_aligned else "M1 EMA Misaligned"}

        # M5 Context Alignment (+15)
        m5_aligned = False
        if signal_candidate == "LONG" and m5_setup == "M5_BULL_TREND":
            total_score += 15
            m5_aligned = True
        elif signal_candidate == "SHORT" and m5_setup == "M5_BEAR_TREND":
            total_score += 15
            m5_aligned = True
        matrix["m5_context"] = {"pass": m5_aligned, "desc": f"M5 Trend Aligned: {m5_setup} (+15 pts)" if m5_aligned else "M5 Neutral/Misaligned"}

        # M15 Macro Context (+15 aligned, -10 opposed)
        if signal_candidate == "LONG":
            if m15_context == "BULLISH":
                total_score += 15
                matrix["m15_macro"] = {"pass": True, "desc": "M15 Bullish Context (+15 pts)"}
            elif m15_context == "BEARISH":
                total_score -= 10
                matrix["m15_macro"] = {"pass": False, "desc": "M15 Counter-Trend Penalty (-10 pts)"}
            else:
                matrix["m15_macro"] = {"pass": True, "desc": "M15 Neutral (0 pts)"}
        else:
            if m15_context == "BEARISH":
                total_score += 15
                matrix["m15_macro"] = {"pass": True, "desc": "M15 Bearish Context (+15 pts)"}
            elif m15_context == "BULLISH":
                total_score -= 10
                matrix["m15_macro"] = {"pass": False, "desc": "M15 Counter-Trend Penalty (-10 pts)"}
            else:
                matrix["m15_macro"] = {"pass": True, "desc": "M15 Neutral (0 pts)"}

        # Location Quality Filter (Penalize Range Midpoint Chop)
        if getattr(DEFAULT_CONFIG, "location_filter_enabled", True) and len(m1_candles) >= 21:
            loc_high = max(c["high"] for c in m1_candles[-20:-1])
            loc_low = min(c["low"] for c in m1_candles[-20:-1])
            range_span = max(0.50, loc_high - loc_low)
            midpoint = (loc_high + loc_low) / 2.0
            dist_from_mid = abs(current_price - midpoint) / range_span
            if dist_from_mid < 0.15:
                total_score -= 10
                matrix["location"] = {"pass": False, "desc": "Trapped in Range Midpoint (-10 pts)"}
            else:
                total_score += 10
                matrix["location"] = {"pass": True, "desc": "Structural Range Boundary (+10 pts)"}

        # Volume / Momentum Bonus (+10)
        recent_vols = [c["volume"] for c in m1_candles[-6:-1]]
        vol_bonus = (curr_c["volume"] > sum(recent_vols) / max(1, len(recent_vols)))
        if vol_bonus:
            total_score += 10
            matrix["volume"] = {"pass": True, "desc": "Volume Expansion (+10 pts)"}
        else:
            matrix["volume"] = {"pass": False, "desc": "Average Volume"}

        total_score = max(0, min(100, total_score))
        setup_class = "CLASS_A" if total_score >= 75 else ("CLASS_B" if total_score >= 65 else "CLASS_C")
        matrix["setup_class"] = {"class": setup_class, "desc": f"Setup Classification: {setup_class}"}
        matrix["score_gate"] = {
            "pass": total_score >= DEFAULT_CONFIG.min_score_threshold,
            "desc": f"Score {total_score}/100 ({setup_class} vs Threshold {DEFAULT_CONFIG.min_score_threshold})"
        }

        # Score Threshold Check
        if total_score < DEFAULT_CONFIG.min_score_threshold:
            return self._build_result(
                "NONE", total_score, f"Score below threshold ({total_score}/100 - {setup_class})",
                f"Confluence Score {total_score}/100 is below {DEFAULT_CONFIG.min_score_threshold} threshold",
                matrix
            )

        # ----------------------------------------------------------------------
        # STOP LOSS & TARGET GEOMETRY
        # ----------------------------------------------------------------------
        tp_mult = getattr(DEFAULT_CONFIG, "tp_vol_multiplier", 2.5)
        if signal_candidate == "LONG":
            raw_sl = recent_m1_low - 0.20 * atr_m1
            min_sl = current_price * (1.0 - DEFAULT_CONFIG.min_sl_pct)
            max_sl = current_price * (1.0 - DEFAULT_CONFIG.max_sl_pct)
            sl_price = max(max_sl, min(raw_sl, min_sl))
            r_dist = max(0.40, current_price - sl_price)

            vol_mult = max(1.5, min(3.0, (atr_m1 / 1.0) * (tp_mult / 2.2)))
            tp1_price = round(current_price + (vol_mult * r_dist), 2)
            tp2_price = tp1_price
            be_price = round(current_price * (1.0 + DEFAULT_CONFIG.be_fee_buffer_pct), 2) if getattr(DEFAULT_CONFIG, "be_mode", "NO_BE") != "NO_BE" else 0.0
        else:
            raw_sl = recent_m1_high + 0.20 * atr_m1
            min_sl = current_price * (1.0 + DEFAULT_CONFIG.min_sl_pct)
            max_sl = current_price * (1.0 + DEFAULT_CONFIG.max_sl_pct)
            sl_price = min(max_sl, max(raw_sl, min_sl))
            r_dist = max(0.40, sl_price - current_price)

            vol_mult = max(1.5, min(3.0, (atr_m1 / 1.0) * (tp_mult / 2.2)))
            tp1_price = round(current_price - (vol_mult * r_dist), 2)
            tp2_price = tp1_price
            be_price = round(current_price * (1.0 - DEFAULT_CONFIG.be_fee_buffer_pct), 2) if getattr(DEFAULT_CONFIG, "be_mode", "NO_BE") != "NO_BE" else 0.0

        sl_price = round(sl_price, 2)

        # ----------------------------------------------------------------------
        # STRUCTURAL NOISE FLOOR PROTECTION (v3.3)
        # ----------------------------------------------------------------------
        min_r = getattr(DEFAULT_CONFIG, "min_r_dist", 4.0)
        if r_dist < min_r:
            return self._build_result(
                "NONE", total_score, "Noise floor protection",
                f"Noise Floor Protection: Stop distance (${r_dist:.2f}) < ${min_r:.2f} structural threshold",
                matrix
            )

        # ----------------------------------------------------------------------
        # MANDATORY FEE-AWARE TRADE FILTER
        # ----------------------------------------------------------------------
        friction_pct = 0.0005 + 0.0002 + (0.01 / current_price)
        est_roundtrip_cost = current_price * friction_pct
        gate_ratio = getattr(DEFAULT_CONFIG, "fee_risk_gate_ratio", 0.25)
        if est_roundtrip_cost > gate_ratio * r_dist:
            return self._build_result(
                "NONE", total_score, "Fee burden excessive",
                f"Fee Burden: Estimated roundtrip cost (${est_roundtrip_cost:.2f}) > {gate_ratio*100:.0f}% of risk R (${r_dist:.2f})",
                matrix
            )

        reason_summary = f"{signal_candidate} {module_desc} ({setup_class} Score: {total_score}/100 | M15 {m15_context})"

        return self._build_result(
            signal_candidate,
            total_score,
            reason_summary,
            f"Setup Qualified ({setup_class} Confluence {total_score}/100 >= {DEFAULT_CONFIG.min_score_threshold})",
            matrix,
            current_price,
            sl_price,
            tp1_price,
            tp2_price,
            be_price,
            round(r_dist, 2),
            module_name
        )

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
