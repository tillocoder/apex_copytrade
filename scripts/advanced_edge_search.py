#!/usr/bin/env python3
"""
APEX QUANT v4 — ADVANCED EDGE SEARCH & PARAMETER PERTURBATION
================================================================================
Investigates asymmetric high-R setups, strict institutional regime filters,
MTF confirmation (H1 + M15 + M5), London/US session effects, and Breakeven logic.
Tests across both BTCUSDT and ETHUSDT (2 full years, 212,000+ M5 candles each).
"""
import os
import sys
import json
import math
import time
import random
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import core simulation context and aggregation from quant_discovery_engine
from quant_discovery_engine import (
    load_cached_klines, aggregate_candles, SimulationContext, 
    run_strategy_simulation, run_walk_forward_4fold, run_monte_carlo,
    DATA_DIR
)

# ==============================================================================
# ADVANCED STRATEGY VARIANTS WITH INSTITUTIONAL REGIME & MTF CONFLUENCE
# ==============================================================================

def signal_mtf_trend_expansion(ctx, i, 
                               rr=3.0, 
                               h1_adx_floor=25, 
                               session_start=12, 
                               session_end=18, 
                               weekday_only=True,
                               atr_mult_stop=1.5,
                               vol_mult=1.5,
                               use_m15_align=True):
    """
    Variant B/C: Triple-Screen MTF Trend Expansion
    - H1: Super-Trended Regime (EMA 50 > EMA 200 AND H1 ADX >= h1_adx_floor)
    - M15: Directional Confirmation (M15 Close > EMA 50)
    - Time: London/NY Overlap (default 12:00 to 18:00 UTC), Weekday only
    - M5: Breakout of 20-bar high with Volume Surge >= vol_mult AND ATR expansion
    - Target: High Asymmetric R (default 3.0R) with structural/ATR stop
    """
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    
    # 1. Day & Session Filter
    if weekday_only and dt_utc.weekday() >= 5:  # Skip Sat & Sun
        return None
    if not (session_start <= dt_utc.hour < session_end):
        return None
        
    # 2. Zero-Lookahead H1 Regime
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_e50 = ctx.h1_ema50[h_idx]
    h_e200 = ctx.h1_ema200[h_idx]
    h_adx = ctx.h1_adx[h_idx]
    
    if h_adx < h1_adx_floor: return None
    
    h1_bull = (h_close > h_e50 > h_e200)
    h1_bear = (h_close < h_e50 < h_e200)
    if not (h1_bull or h1_bear): return None
    
    # 3. M15 Confirmation
    if use_m15_align:
        m_idx = ctx.m5_to_m15[i]
        if m_idx < 0: return None
        m_close = ctx.m15_closes[m_idx]
        m_e50 = ctx.m15_ema50[m_idx]
        if h1_bull and m_close <= m_e50: return None
        if h1_bear and m_close >= m_e50: return None

    # 4. M5 Volatility & Volume Expansion
    c_close = ctx.closes[i]
    c_high = ctx.highs[i]
    c_low = ctx.lows[i]
    c_atr = ctx.m5_atr14[i]
    c_vol = ctx.vols[i]
    avg_vol = ctx.m5_vol_sma20[i]
    
    if (c_vol / max(1.0, avg_vol)) < vol_mult: return None
    
    # Prior 20-bar Donchian High/Low (excluding current)
    don_u = ctx.don20_u[i]
    don_l = ctx.don20_l[i]
    
    # Long Setup
    if h1_bull and c_close > don_u:
        sl = c_close - (atr_mult_stop * c_atr)
        sl_dist = c_close - sl
        return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
        
    # Short Setup
    if h1_bear and c_close < don_l:
        sl = c_close + (atr_mult_stop * c_atr)
        sl_dist = sl - c_close
        return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
        
    return None

def signal_liquidity_sweep_reversal(ctx, i, 
                                     rr=3.0, 
                                     lookback=30, 
                                     session_start=8, 
                                     session_end=20,
                                     weekday_only=True):
    """
    Family F: Smart Money / Liquidity Sweep with Asymmetric R:R
    - Identifies institutional stop hunts: Price sweeps a major 30-bar high/low with a wick,
      then rejects strongly back inside the range.
    - Session: European & US active trading (08:00 - 20:00 UTC).
    - Stop: Just outside the sweep wick tip (tight risk).
    - Target: Opposite range extreme or 3.0R to 4.0R.
    """
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    if weekday_only and dt_utc.weekday() >= 5: return None
    if not (session_start <= dt_utc.hour < session_end): return None
    
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_e200 = ctx.h1_ema200[h_idx]
    
    c_open = ctx.opens[i]
    c_close = ctx.closes[i]
    c_high = ctx.highs[i]
    c_low = ctx.lows[i]
    c_atr = ctx.m5_atr14[i]
    
    # 30-bar prior structure extreme
    prior_high = max(ctx.highs[i-lookback:i-1])
    prior_low = min(ctx.lows[i-lookback:i-1])
    
    # Bullish Liquidity Sweep (Swept low, closed above)
    if c_low < prior_low and c_close > prior_low and c_close > c_open and h_close > h_e200:
        lower_wick = min(c_open, c_close) - c_low
        candle_range = c_high - c_low
        if lower_wick >= 0.50 * candle_range and candle_range >= 0.8 * c_atr:
            sl = c_low - (0.15 * c_atr)
            sl_dist = c_close - sl
            if 0.6 * c_atr <= sl_dist <= 2.0 * c_atr:
                return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
                
    # Bearish Liquidity Sweep (Swept high, closed below)
    if c_high > prior_high and c_close < prior_high and c_close < c_open and h_close < h_e200:
        upper_wick = c_high - max(c_open, c_close)
        candle_range = c_high - c_low
        if upper_wick >= 0.50 * candle_range and candle_range >= 0.8 * c_atr:
            sl = c_high + (0.15 * c_atr)
            sl_dist = sl - c_close
            if 0.6 * c_atr <= sl_dist <= 2.0 * c_atr:
                return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
                
    return None

def signal_volatility_breakout_session_open(ctx, i, rr=2.5):
    """
    Session Open Volatility Breakout (London Open 08:00 UTC or US Open 13:30/14:00 UTC)
    Captures the opening momentum burst of major financial centres.
    """
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    if dt_utc.weekday() >= 5: return None
    
    # Focus only on high-liquidity session opens: 07:00-09:00 UTC and 13:00-15:00 UTC
    is_open_hour = (7 <= dt_utc.hour < 9) or (13 <= dt_utc.hour < 15)
    if not is_open_hour: return None
    
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_e50 = ctx.h1_ema50[h_idx]
    
    c_close = ctx.closes[i]
    c_open = ctx.opens[i]
    c_atr = ctx.m5_atr14[i]
    c_vol = ctx.vols[i]
    avg_vol = ctx.m5_vol_sma20[i]
    
    # Strong candle breaking 12-bar Donchian with 2.0x volume surge
    if (c_vol / max(1.0, avg_vol)) < 2.0: return None
    
    if c_close > ctx.don12_u[i] and c_close > c_open and h_close > h_e50:
        sl = c_open - (0.5 * c_atr)
        sl_dist = c_close - sl
        return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
        
    if c_close < ctx.don12_l[i] and c_close < c_open and h_close < h_e50:
        sl = c_open + (0.5 * c_atr)
        sl_dist = sl - c_close
        return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
        
    return None

# ==============================================================================
# EXECUTION & ADVANCED EXPERIMENTS
# ==============================================================================
def run_advanced_experiments():
    print("=" * 80)
    print("🔬 RUNNING APEX QUANT v4 ADVANCED EDGE DISCOVERY & ABLATION MATRIX")
    print("=" * 80)
    
    btc_m5 = load_cached_klines("BTCUSDT")
    eth_m5 = load_cached_klines("ETHUSDT")
    
    btc_m15 = aggregate_candles(btc_m5, 15)
    btc_h1 = aggregate_candles(btc_m5, 60)
    eth_m15 = aggregate_candles(eth_m5, 15)
    eth_h1 = aggregate_candles(eth_m5, 60)
    
    btc_ctx = SimulationContext(btc_m5, btc_h1, btc_m15, "BTCUSDT")
    eth_ctx = SimulationContext(eth_m5, eth_h1, eth_m15, "ETHUSDT")
    
    experiments = [
        # 1. MTF Trend Expansion (R:R variations: 2.0R, 2.5R, 3.0R, 3.5R, 4.0R)
        {"id": "MTF_EXP_20R", "name": "MTF Trend Expansion (2.0R)", "fn": lambda c, i: signal_mtf_trend_expansion(c, i, rr=2.0)},
        {"id": "MTF_EXP_25R", "name": "MTF Trend Expansion (2.5R)", "fn": lambda c, i: signal_mtf_trend_expansion(c, i, rr=2.5)},
        {"id": "MTF_EXP_30R", "name": "MTF Trend Expansion (3.0R)", "fn": lambda c, i: signal_mtf_trend_expansion(c, i, rr=3.0)},
        {"id": "MTF_EXP_35R", "name": "MTF Trend Expansion (3.5R)", "fn": lambda c, i: signal_mtf_trend_expansion(c, i, rr=3.5)},
        {"id": "MTF_EXP_40R", "name": "MTF Trend Expansion (4.0R)", "fn": lambda c, i: signal_mtf_trend_expansion(c, i, rr=4.0)},
        
        # 2. Session Variations (Full 08-20 UTC vs London/NY 12-18 UTC)
        {"id": "MTF_EXP_08_20", "name": "MTF Trend Expansion (08-20 UTC, 3.0R)", "fn": lambda c, i: signal_mtf_trend_expansion(c, i, rr=3.0, session_start=8, session_end=20)},
        {"id": "MTF_EXP_24H", "name": "MTF Trend Expansion (24H All Hours, 3.0R)", "fn": lambda c, i: signal_mtf_trend_expansion(c, i, rr=3.0, session_start=0, session_end=24, weekday_only=False)},
        
        # 3. Liquidity Sweep Reversals (2.5R, 3.0R, 3.5R)
        {"id": "SMC_SWEEP_25R", "name": "SMC Liquidity Sweep (2.5R)", "fn": lambda c, i: signal_liquidity_sweep_reversal(c, i, rr=2.5)},
        {"id": "SMC_SWEEP_30R", "name": "SMC Liquidity Sweep (3.0R)", "fn": lambda c, i: signal_liquidity_sweep_reversal(c, i, rr=3.0)},
        {"id": "SMC_SWEEP_35R", "name": "SMC Liquidity Sweep (3.5R)", "fn": lambda c, i: signal_liquidity_sweep_reversal(c, i, rr=3.5)},
        
        # 4. Session Open Volatility Burst
        {"id": "SESS_OPEN_25R", "name": "Session Open Volatility Burst (2.5R)", "fn": lambda c, i: signal_volatility_breakout_session_open(c, i, rr=2.5)},
        {"id": "SESS_OPEN_30R", "name": "Session Open Volatility Burst (3.0R)", "fn": lambda c, i: signal_volatility_breakout_session_open(c, i, rr=3.0)}
    ]
    
    results = []
    
    for asset, ctx in [("ETHUSDT", eth_ctx), ("BTCUSDT", btc_ctx)]:
        print(f"\n{'='*25} ASSET: {asset} {'='*25}")
        for exp in experiments:
            c_id = f"{exp['id']}_{asset[:3]}"
            print(f"Testing {c_id}: {exp['name']}...")
            
            # Base realistic simulation ($20 start, 1.0% risk, 0.05% slippage, taker entry/SL, maker TP)
            base = run_strategy_simulation(ctx, exp["fn"], initial_capital=20.0, target_risk_pct=1.0)
            
            # Stress simulation (0.10% slippage, 0.06% VIP0 fee)
            stress = run_strategy_simulation(ctx, exp["fn"], initial_capital=20.0, target_risk_pct=1.0,
                                             slippage_pct=0.0010, taker_fee_pct=0.0006)
                                             
            # Walk-forward 4-fold
            wf_folds, oos_t = run_walk_forward_4fold(ctx, exp["fn"])
            oos_w = [t for t in oos_t if t["net_pnl"] > 0]
            oos_l = [t for t in oos_t if t["net_pnl"] <= 0]
            oos_w_usd = sum(t["net_pnl"] for t in oos_w)
            oos_l_usd = abs(sum(t["net_pnl"] for t in oos_l))
            oos_pf = oos_w_usd / oos_l_usd if oos_l_usd > 0 else 0.0
            oos_exp = (sum(t["r_multiple"] for t in oos_t) / len(oos_t)) if oos_t else 0.0
            
            # Capital scaling ($100, $200)
            res100 = run_strategy_simulation(ctx, exp["fn"], initial_capital=100.0)
            res200 = run_strategy_simulation(ctx, exp["fn"], initial_capital=200.0)
            
            # Deposit curve ($20 start + $20/day)
            res_dep = run_strategy_simulation(ctx, exp["fn"], initial_capital=20.0, daily_deposit_usd=20.0)
            
            # Monte Carlo
            mc = run_monte_carlo(base["trades_list"], iterations=1000, initial_bal=20.0)
            
            status = "REJECTED"
            if base["pf"] >= 1.20 and oos_exp >= 0.08 and base["max_dd_trading_pct"] <= 25.0:
                if stress["pf"] >= 1.10 and mc["dd_95"] <= 35.0:
                    status = "ROBUST CANDIDATE"
                else:
                    status = "PROMISING"
            elif base["pf"] >= 1.05 and oos_exp >= 0.02:
                status = "FRAGILE"
                
            rec = {
                "id": c_id, "asset": asset, "strategy": exp["name"],
                "trades": base["trades"], "trades_year": round(base["trades"] / 2.0, 1),
                "wr": base["win_rate"], "pf": base["pf"], "pf_gross": base["pf_gross"],
                "expectancy_r": base["expectancy_r"], "avg_win": base["avg_win"], "avg_loss": base["avg_loss"],
                "max_dd": base["max_dd_trading_pct"], "max_consec_loss": base["max_consecutive_losses"],
                "oos_pf": round(oos_pf, 2), "oos_exp": round(oos_exp, 3), "stress_pf": stress["pf"],
                "mc_95_dd": mc["dd_95"], "bal_20": base["final_bal_trading"],
                "bal_100": res100["final_bal_trading"], "bal_200": res200["final_bal_trading"],
                "bal_dep": res_dep["final_bal_deposit"], "status": status
            }
            results.append(rec)
            print(f"   -> Trades={base['trades']} | PF={base['pf']} (Gross={base['pf_gross']}) | OOS Exp={round(oos_exp, 3)}R | Stress PF={stress['pf']} | DD={base['max_dd_trading_pct']}% | Status={status}")

    # Output JSON summary
    out_file = os.path.join(DATA_DIR, "advanced_experiments_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Saved advanced summary to {out_file}")
    return results

if __name__ == "__main__":
    run_advanced_experiments()
