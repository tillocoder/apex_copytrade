"""
Setup Discovery Layer (Setups A through I)
Discovers and scores candidate trade setups:
- SETUP A: Trend continuation
- SETUP B: Pullback
- SETUP C: Breakout
- SETUP D: Breakout retest
- SETUP E: Liquidity sweep reversal
- SETUP F: Range rejection
- SETUP G: Momentum expansion
- SETUP H: Failed breakout
- SETUP I: Structure reversal

Computes structural invalidation, TP targets, expected R:R, and setup quality.
"""

import math
from typing import Dict, List, Any, Optional


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0 and not math.isnan(b) else default


class SetupDiscoveryEngine:
    def __init__(self):
        pass

    def evaluate_setups(self, features: Dict[str, Any], regime: str, cross_asset: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Discovers all mathematically plausible candidate setups from the feature profile.
        Returns a list of candidate setup dictionaries.
        """
        candidates = []
        p = features.get("current_price", 0.0)
        if p <= 0:
            return []

        trend = features.get("trend", {})
        mom = features.get("momentum", {})
        vol = features.get("volatility", {})
        volu = features.get("volume", {})
        pa = features.get("price_action", {})
        struct = features.get("market_structure", {})
        sr = features.get("support_resistance", {})
        liq = features.get("liquidity", {})
        deriv = features.get("derivatives", {})

        atr = vol.get("atr", p * 0.01)
        rsi = mom.get("rsi_14", 50.0)
        e21 = trend.get("ema21", p)
        e50 = trend.get("ema50", p)
        rvol = volu.get("relative_volume_rvol", 1.0)

        # ── SETUP A: Trend Continuation ───────────────────────────────────────
        if trend.get("ema_alignment") == "BULLISH_STACK" and p > e21 and rsi > 52.0:
            sl = round(min(e50, struct.get("recent_swing_low", p - 1.5 * atr)) - 0.2 * atr, 2)
            dist_sl = p - sl
            if dist_sl > 0:
                tp1 = round(p + 1.6 * dist_sl, 2)
                tp2 = round(p + 2.8 * dist_sl, 2)
                quality = 70.0 + (5.0 if rvol > 1.2 else 0.0) + (5.0 if regime == "TRENDING_UP" else 0.0)
                candidates.append({
                    "setup_type": "TREND_CONTINUATION",
                    "direction": "LONG",
                    "entry": round(p, 2),
                    "stop_loss": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "rr_tp1": round(1.6, 2),
                    "rr_tp2": round(2.8, 2),
                    "setup_quality": min(95.0, quality),
                    "invalidation": f"H1 Close below EMA 50 ({e50})"
                })

        elif trend.get("ema_alignment") == "BEARISH_STACK" and p < e21 and rsi < 48.0:
            sl = round(max(e50, struct.get("recent_swing_high", p + 1.5 * atr)) + 0.2 * atr, 2)
            dist_sl = sl - p
            if dist_sl > 0:
                tp1 = round(p - 1.6 * dist_sl, 2)
                tp2 = round(p - 2.8 * dist_sl, 2)
                quality = 70.0 + (5.0 if rvol > 1.2 else 0.0) + (5.0 if regime == "TRENDING_DOWN" else 0.0)
                candidates.append({
                    "setup_type": "TREND_CONTINUATION",
                    "direction": "SHORT",
                    "entry": round(p, 2),
                    "stop_loss": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "rr_tp1": round(1.6, 2),
                    "rr_tp2": round(2.8, 2),
                    "setup_quality": min(95.0, quality),
                    "invalidation": f"H1 Close above EMA 50 ({e50})"
                })

        # ── SETUP B: Pullback ─────────────────────────────────────────────────
        if trend.get("trend_direction") == "BULLISH" and abs(p - e21) / p < 0.005 and rsi <= 55.0:
            sl = round(e50 - 0.3 * atr, 2)
            dist_sl = p - sl
            if dist_sl > 0:
                tp1 = round(p + 1.8 * dist_sl, 2)
                tp2 = round(p + 3.0 * dist_sl, 2)
                quality = 74.0 + (6.0 if pa.get("candle_pattern") in ("BULLISH_PIN_BAR", "BULLISH_ENGULFING") else 0.0)
                candidates.append({
                    "setup_type": "PULLBACK",
                    "direction": "LONG",
                    "entry": round(p, 2),
                    "stop_loss": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "rr_tp1": round(1.8, 2),
                    "rr_tp2": round(3.0, 2),
                    "setup_quality": min(95.0, quality),
                    "invalidation": f"Clean break and close below EMA 50 ({e50})"
                })

        # ── SETUP E: Liquidity Sweep Reversal ─────────────────────────────────
        # PRIMARY HIGH VALUE SETUP: Sweep -> Reclaim -> Structure Confirmation
        if liq.get("bullish_liquidity_sweep") or (mom.get("momentum_divergence") == "BULLISH_DIV" and rsi < 35.0):
            sw_low = struct.get("recent_swing_low", p - atr)
            sl = round(sw_low - 0.3 * atr, 2)
            dist_sl = p - sl
            if dist_sl > 0:
                tp1 = round(p + 2.0 * dist_sl, 2)
                tp2 = round(p + 3.5 * dist_sl, 2)
                quality = 80.0 + (5.0 if rvol > 1.5 else 0.0) + (5.0 if liq.get("bullish_liquidity_sweep") else 0.0)
                candidates.append({
                    "setup_type": "LIQUIDITY_SWEEP_REVERSAL",
                    "direction": "LONG",
                    "entry": round(p, 2),
                    "stop_loss": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "rr_tp1": round(2.0, 2),
                    "rr_tp2": round(3.5, 2),
                    "setup_quality": min(98.0, quality),
                    "invalidation": f"Acceptance below swept liquidity low ({sw_low})"
                })

        if liq.get("bearish_liquidity_sweep") or (mom.get("momentum_divergence") == "BEARISH_DIV" and rsi > 65.0):
            sw_high = struct.get("recent_swing_high", p + atr)
            sl = round(sw_high + 0.3 * atr, 2)
            dist_sl = sl - p
            if dist_sl > 0:
                tp1 = round(p - 2.0 * dist_sl, 2)
                tp2 = round(p - 3.5 * dist_sl, 2)
                quality = 80.0 + (5.0 if rvol > 1.5 else 0.0) + (5.0 if liq.get("bearish_liquidity_sweep") else 0.0)
                candidates.append({
                    "setup_type": "LIQUIDITY_SWEEP_REVERSAL",
                    "direction": "SHORT",
                    "entry": round(p, 2),
                    "stop_loss": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "rr_tp1": round(2.0, 2),
                    "rr_tp2": round(3.5, 2),
                    "setup_quality": min(98.0, quality),
                    "invalidation": f"Acceptance above swept liquidity high ({sw_high})"
                })

        # ── SETUP F: Range Rejection ──────────────────────────────────────────
        if regime == "RANGING":
            bb_pos = vol.get("bb_percent_b", 0.5)
            if bb_pos <= 0.10: # At range bottom
                sl = round(vol.get("bb_lower", p - atr) - 0.25 * atr, 2)
                dist_sl = p - sl
                if dist_sl > 0:
                    tp1 = round(vol.get("bb_mid", p + dist_sl * 1.5), 2)
                    tp2 = round(vol.get("bb_upper", p + dist_sl * 2.5), 2)
                    candidates.append({
                        "setup_type": "RANGE_REJECTION",
                        "direction": "LONG",
                        "entry": round(p, 2),
                        "stop_loss": sl,
                        "tp1": tp1,
                        "tp2": tp2,
                        "rr_tp1": round(_safe_div(tp1 - p, dist_sl), 2),
                        "rr_tp2": round(_safe_div(tp2 - p, dist_sl), 2),
                        "setup_quality": 75.0,
                        "invalidation": "Breakdown below range support"
                    })
            elif bb_pos >= 0.90: # At range top
                sl = round(vol.get("bb_upper", p + atr) + 0.25 * atr, 2)
                dist_sl = sl - p
                if dist_sl > 0:
                    tp1 = round(vol.get("bb_mid", p - dist_sl * 1.5), 2)
                    tp2 = round(vol.get("bb_lower", p - dist_sl * 2.5), 2)
                    candidates.append({
                        "setup_type": "RANGE_REJECTION",
                        "direction": "SHORT",
                        "entry": round(p, 2),
                        "stop_loss": sl,
                        "tp1": tp1,
                        "tp2": tp2,
                        "rr_tp1": round(_safe_div(p - tp1, dist_sl), 2),
                        "rr_tp2": round(_safe_div(p - tp2, dist_sl), 2),
                        "setup_quality": 75.0,
                        "invalidation": "Breakout above range resistance"
                    })

        # Sort candidates by setup quality
        candidates.sort(key=lambda x: x["setup_quality"], reverse=True)
        return candidates
