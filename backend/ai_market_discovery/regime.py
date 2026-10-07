"""
Market Regime Classification Engine
Classifies market state into:
- TRENDING_UP
- TRENDING_DOWN
- RANGING
- BREAKOUT
- BREAKDOWN
- REVERSAL
- HIGH_VOLATILITY
- LOW_VOLATILITY
- CHOPPY
- UNCERTAIN

Computes regime_confidence (0-100) and maps compatible setup families.
"""

from typing import Dict, Any, Tuple, List


class MarketRegimeEngine:
    def __init__(self):
        pass

    def classify_regime(self, features: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """
        Classifies the market regime from computed factor families.
        Returns: regime, regime_confidence (0-100), compatible_setups list
        """
        trend = features.get("trend", {})
        momentum = features.get("momentum", {})
        volatility = features.get("volatility", {})
        volume = features.get("volume", {})
        structure = features.get("market_structure", {})
        liquidity = features.get("liquidity", {})

        p_to_e50 = trend.get("price_to_ema50_pct", 0.0)
        adx = trend.get("adx_14", 20.0)
        ema_align = trend.get("ema_alignment", "MIXED")
        persistence = trend.get("trend_persistence_bars", 0)

        rsi = momentum.get("rsi_14", 50.0)
        div = momentum.get("momentum_divergence", "NONE")

        bb_width = volatility.get("bb_width_pct", 3.0)
        atr_pctile = volatility.get("atr_percentile", 50.0)

        rvol = volume.get("relative_volume_rvol", 1.0)
        vol_spike = volume.get("volume_spike", False)

        bos = structure.get("bos_detected", False)
        choch = structure.get("choch_detected", False)
        struct_state = structure.get("structure_state", "")

        bull_sweep = liquidity.get("bullish_liquidity_sweep", False)
        bear_sweep = liquidity.get("bearish_liquidity_sweep", False)

        # 1. Breakout / Breakdown (Displacement + Vol Spike + BOS)
        if bos and (vol_spike or rvol > 2.0) and bb_width > 2.5:
            if p_to_e50 > 0:
                conf = min(95.0, 75.0 + (rvol - 2.0) * 10.0)
                return "BREAKOUT", round(conf, 1), ["SETUP_C_BREAKOUT", "SETUP_D_BREAKOUT_RETEST", "SETUP_G_MOMENTUM_EXPANSION"]
            else:
                conf = min(95.0, 75.0 + (rvol - 2.0) * 10.0)
                return "BREAKDOWN", round(conf, 1), ["SETUP_C_BREAKOUT", "SETUP_D_BREAKOUT_RETEST", "SETUP_G_MOMENTUM_EXPANSION"]

        # 2. Reversal (CHoCH + Liquidity Sweep or Strong Divergence)
        if choch or bull_sweep or bear_sweep or div != "NONE":
            conf = 72.0
            if (bull_sweep or bear_sweep) and div != "NONE": conf += 15.0
            if choch: conf += 10.0
            return "REVERSAL", min(95.0, round(conf, 1)), ["SETUP_E_LIQUIDITY_SWEEP", "SETUP_I_STRUCTURE_REVERSAL", "SETUP_H_FAILED_BREAKOUT"]

        # 3. Strong Trending (ADX > 28 + EMA alignment + persistent position)
        if adx >= 28.0 and ema_align == "BULLISH_STACK" and p_to_e50 > 0.5:
            conf = min(95.0, 65.0 + adx * 0.7)
            return "TRENDING_UP", round(conf, 1), ["SETUP_A_TREND_CONTINUATION", "SETUP_B_PULLBACK", "SETUP_D_BREAKOUT_RETEST"]

        if adx >= 28.0 and ema_align == "BEARISH_STACK" and p_to_e50 < -0.5:
            conf = min(95.0, 65.0 + adx * 0.7)
            return "TRENDING_DOWN", round(conf, 1), ["SETUP_A_TREND_CONTINUATION", "SETUP_B_PULLBACK", "SETUP_D_BREAKOUT_RETEST"]

        # 4. Extreme Volatility
        if atr_pctile >= 90.0 or bb_width >= 8.0:
            return "HIGH_VOLATILITY", 80.0, ["SETUP_E_LIQUIDITY_SWEEP", "SETUP_F_RANGE_REJECTION"]

        # 5. Low Volatility / Squeeze
        if atr_pctile <= 15.0 or bb_width <= 1.2:
            return "LOW_VOLATILITY", 82.0, ["SETUP_C_BREAKOUT", "SETUP_G_MOMENTUM_EXPANSION"]

        # 6. Ranging / Compression
        if adx < 20.0 and abs(p_to_e50) < 1.0 and 40.0 <= rsi <= 60.0:
            return "RANGING", 85.0, ["SETUP_F_RANGE_REJECTION", "SETUP_E_LIQUIDITY_SWEEP", "SETUP_B_PULLBACK"]

        # 7. Choppy / Uncertain
        if ema_align == "MIXED" and persistence < 3:
            return "CHOPPY", 78.0, []

        return "UNCERTAIN", 60.0, []
