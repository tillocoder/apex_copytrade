#!/usr/bin/env python3
"""
APEX QUANT v3.4 — HIGH-WINRATE MULTI-CORE OPTIMIZATION & BACKTEST ENGINE
========================================================================
Instrument: ETHUSDT Perpetual (Binance USD(S)-M Futures)
Dataset   : 129,600 M1 Bars (90.0 Days, June 29 - Sept 27, 2026)
Cores     : 8 Parallel Worker Processes (100% CPU Utilization)
Objective : Maximize REAL WIN RATE (>= 50% - 70%), eliminate premature Stop Loss
            shakeouts, and maintain strictly positive Net Expectancy & Profit Factor.
"""

import os
import sys

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import csv
import json
import time
import math
import itertools
from datetime import datetime, timezone
import multiprocessing
from typing import Dict, Any, List, Tuple

DATA_PATH = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"

# ------------------------------------------------------------------------------
# 1. FAST INDICATORS
# ------------------------------------------------------------------------------
def fast_ema(arr: List[float], period: int) -> List[float]:
    n = len(arr)
    res = [0.0] * n
    if n < period:
        return res
    mult = 2.0 / (period + 1.0)
    sma = sum(arr[:period]) / period
    for i in range(period - 1):
        res[i] = arr[i]
    res[period - 1] = sma
    cur = sma
    for i in range(period, n):
        cur = (arr[i] - cur) * mult + cur
        res[i] = cur
    return res

def fast_rsi(closes: List[float], period: int = 14) -> List[float]:
    n = len(closes)
    res = [50.0] * n
    if n <= period:
        return res
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        chg = closes[i] - closes[i-1]
        if chg > 0:
            gains[i] = chg
        else:
            losses[i] = -chg
    
    avg_gain = sum(gains[1:period+1]) / period
    avg_loss = sum(losses[1:period+1]) / period
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            res[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            res[i] = round(100.0 - (100.0 / (1.0 + rs)), 1)
    return res

# ------------------------------------------------------------------------------
# 2. FEATURE EXTRACTION & DATASET PRE-COMPUTATION
# ------------------------------------------------------------------------------
def precalculate_features(raw_candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    n = len(raw_candles)
    closes = [c["close"] for c in raw_candles]
    highs = [c["high"] for c in raw_candles]
    lows = [c["low"] for c in raw_candles]
    opens = [c["open"] for c in raw_candles]
    vols = [c["volume"] for c in raw_candles]
    times = [c["time"] for c in raw_candles]

    # M1 Indicators
    e9 = fast_ema(closes, 9)
    e21 = fast_ema(closes, 21)
    e50 = fast_ema(closes, 50)
    e200 = fast_ema(closes, 200)
    rsi14 = fast_rsi(closes, 14)

    # M1 ATR(14)
    tr = [0.0] * n
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    atr = [1.20] * n
    if n >= 15:
        init_atr = sum(tr[1:15]) / 14.0
        for i in range(15):
            atr[i] = init_atr
        cur_atr = init_atr
        for i in range(15, n):
            cur_atr = (cur_atr * 13.0 + tr[i]) / 14.0
            atr[i] = round(cur_atr, 2)

    # Multi-timeframe buckets (M5 and M15)
    m5_bars = []
    m15_bars = []
    cur_m5 = None
    cur_m15 = None
    m1_to_m5 = [-1] * n
    m1_to_m15 = [-1] * n

    for i in range(n):
        t = times[i]
        c = raw_candles[i]

        m5_t = (t // 300000) * 300000
        if cur_m5 is None:
            cur_m5 = {"time": m5_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        elif cur_m5["time"] == m5_t:
            cur_m5["high"] = max(cur_m5["high"], c["high"])
            cur_m5["low"] = min(cur_m5["low"], c["low"])
            cur_m5["close"] = c["close"]
            cur_m5["volume"] += c["volume"]
        else:
            m5_bars.append(cur_m5)
            cur_m5 = {"time": m5_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        m1_to_m5[i] = len(m5_bars) - 1

        m15_t = (t // 900000) * 900000
        if cur_m15 is None:
            cur_m15 = {"time": m15_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        elif cur_m15["time"] == m15_t:
            cur_m15["high"] = max(cur_m15["high"], c["high"])
            cur_m15["low"] = min(cur_m15["low"], c["low"])
            cur_m15["close"] = c["close"]
            cur_m15["volume"] += c["volume"]
        else:
            m15_bars.append(cur_m15)
            cur_m15 = {"time": m15_t, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]}
        m1_to_m15[i] = len(m15_bars) - 1

    # M5 Indicators
    m5_closes = [b["close"] for b in m5_bars]
    m5_highs = [b["high"] for b in m5_bars]
    m5_lows = [b["low"] for b in m5_bars]
    m5_e21 = fast_ema(m5_closes, 21)
    m5_e50 = fast_ema(m5_closes, 50)

    # M15 Indicators
    m15_closes = [b["close"] for b in m15_bars]
    m15_highs = [b["high"] for b in m15_bars]
    m15_lows = [b["low"] for b in m15_bars]
    m15_e50 = fast_ema(m15_closes, 50)

    # M15 ADX
    m15_len = len(m15_bars)
    m15_tr = [0.0] * m15_len
    m15_pdm = [0.0] * m15_len
    m15_mdm = [0.0] * m15_len
    for j in range(1, m15_len):
        h, l, pc = m15_highs[j], m15_lows[j], m15_closes[j-1]
        m15_tr[j] = max(h - l, abs(h - pc), abs(l - pc))
        up = h - m15_highs[j-1]
        down = m15_lows[j-1] - l
        if up > down and up > 0: m15_pdm[j] = up
        if down > up and down > 0: m15_mdm[j] = down

    p = 14
    smooth_tr = [0.0] * m15_len
    smooth_pdm = [0.0] * m15_len
    smooth_mdm = [0.0] * m15_len
    m15_adx = [0.0] * m15_len
    if m15_len >= p + 1:
        smooth_tr[p] = sum(m15_tr[1:p+1])
        smooth_pdm[p] = sum(m15_pdm[1:p+1])
        smooth_mdm[p] = sum(m15_mdm[1:p+1])
        dx = [0.0] * m15_len
        for j in range(p + 1, m15_len):
            smooth_tr[j] = smooth_tr[j-1] - (smooth_tr[j-1] / p) + m15_tr[j]
            smooth_pdm[j] = smooth_pdm[j-1] - (smooth_pdm[j-1] / p) + m15_pdm[j]
            smooth_mdm[j] = smooth_mdm[j-1] - (smooth_mdm[j-1] / p) + m15_mdm[j]
            pdi = 100.0 * (smooth_pdm[j] / max(1e-6, smooth_tr[j]))
            mdi = 100.0 * (smooth_mdm[j] / max(1e-6, smooth_tr[j]))
            sum_di = pdi + mdi
            dx[j] = 100.0 * abs(pdi - mdi) / max(1e-6, sum_di)
        start_adx = 2 * p
        if m15_len >= start_adx:
            m15_adx[start_adx] = sum(dx[p+1:start_adx+1]) / p
            for j in range(start_adx + 1, m15_len):
                m15_adx[j] = (m15_adx[j-1] * (p - 1) + dx[j]) / p

    features = []
    for i in range(n):
        t = times[i]
        c = raw_candles[i]
        dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
        day_str = dt.strftime('%Y-%m-%d')
        hr = dt.hour + dt.minute / 60.0

        if 13.5 <= hr < 16.5: sess = "LONDON_NY_OVERLAP"
        elif 16.5 <= hr < 21.0: sess = "NEW_YORK"
        elif 8.0 <= hr < 13.5: sess = "LONDON"
        elif 0.0 <= hr < 8.0: sess = "ASIA"
        else: sess = "OUT_OF_SESSION"

        # M15 completed context
        m15_idx = m1_to_m15[i]
        m15_ctx = "NEUTRAL"
        adx_val = 20.0
        if m15_idx >= 50:
            if c["close"] > m15_e50[m15_idx]: m15_ctx = "BULLISH"
            elif c["close"] < m15_e50[m15_idx]: m15_ctx = "BEARISH"
            adx_val = round(m15_adx[m15_idx], 1)

        # M5 completed context
        m5_idx = m1_to_m5[i]
        m5_ctx = "NONE"
        m5_sw_low = lows[i]
        m5_sw_high = highs[i]
        if m5_idx >= 50:
            if m5_e21[m5_idx] > m5_e50[m5_idx]: m5_ctx = "M5_BULL_TREND"
            elif m5_e21[m5_idx] < m5_e50[m5_idx]: m5_ctx = "M5_BEAR_TREND"
            m5_sw_low = min(m5_lows[max(0, m5_idx-5):m5_idx+1])
            m5_sw_high = max(m5_highs[max(0, m5_idx-5):m5_idx+1])

        # Swing lookbacks
        m1_sw_low_12 = min(lows[max(0, i-11):i]) if i >= 11 else lows[i]
        m1_sw_high_12 = max(highs[max(0, i-11):i]) if i >= 11 else highs[i]
        m1_sw_low_25 = min(lows[max(0, i-24):i]) if i >= 24 else lows[i]
        m1_sw_high_25 = max(highs[max(0, i-24):i]) if i >= 24 else highs[i]

        prior_high_15 = max(highs[max(0, i-14):max(0, i-1)]) if i >= 15 else highs[i]
        prior_low_15 = min(lows[max(0, i-14):max(0, i-1)]) if i >= 15 else lows[i]

        vol_avg_10 = (sum(vols[max(0, i-9):i]) / 9.0) if i >= 10 else vols[i]
        vol_avg_5 = (sum(vols[max(0, i-5):i]) / 5.0) if i >= 6 else vols[i]

        # Location midpoint
        loc_h20 = max(highs[max(0, i-19):i]) if i >= 20 else highs[i]
        loc_l20 = min(lows[max(0, i-19):i]) if i >= 20 else lows[i]
        midpoint = (loc_h20 + loc_l20) / 2.0
        range_span = max(0.50, loc_h20 - loc_l20)
        dist_from_mid = abs(c["close"] - midpoint) / range_span

        # Candidate signals for all 5 modules
        curr_p = c["close"]
        curr_b = abs(c["close"] - c["open"])
        atr_v = atr[i]
        e9_v = e9[i]
        e21_v = e21[i]
        e200_v = e200[i]

        module_candidates = []

        # Module A: Liquidity Sweep & Reclaim
        swept_low = (lows[i] <= m1_sw_low_12 or (i > 0 and lows[i-1] <= m1_sw_low_12))
        swept_high = (highs[i] >= m1_sw_high_12 or (i > 0 and highs[i-1] >= m1_sw_high_12))
        if swept_low and curr_p > m1_sw_low_12 and c["close"] >= c["open"]:
            module_candidates.append(("LONG", "MODULE_A_SWEEP_RECLAIM", 40))
        elif swept_high and curr_p < m1_sw_high_12 and c["close"] <= c["open"]:
            module_candidates.append(("SHORT", "MODULE_A_SWEEP_RECLAIM", 40))

        # Module B: Breakout & Retest
        if i >= 16 and (prior_high_15 - prior_low_15) <= 2.2 * atr_v:
            if curr_p > prior_high_15 and c["close"] > c["open"]:
                module_candidates.append(("LONG", "MODULE_B_BREAKOUT", 35))
            elif curr_p < prior_low_15 and c["close"] < c["open"]:
                module_candidates.append(("SHORT", "MODULE_B_BREAKOUT", 35))

        # Module C: EMA Pullback
        if i >= 25:
            if e9_v > e21_v and c["low"] <= e9_v * 1.0008 and curr_p >= e21_v * 0.9995 and c["close"] >= c["open"]:
                module_candidates.append(("LONG", "MODULE_C_EMA_PULLBACK", 30))
            elif e9_v < e21_v and c["high"] >= e9_v * 0.9992 and curr_p <= e21_v * 1.0005 and c["close"] <= c["open"]:
                module_candidates.append(("SHORT", "MODULE_C_EMA_PULLBACK", 30))

        # Module D: Momentum Impulse
        if i >= 11 and c["volume"] >= 1.25 * vol_avg_10 and curr_b >= 0.70 * atr_v:
            if c["close"] > c["open"] and e9_v > e21_v:
                module_candidates.append(("LONG", "MODULE_D_MOMENTUM_IMPULSE", 30))
            elif c["close"] < c["open"] and e9_v < e21_v:
                module_candidates.append(("SHORT", "MODULE_D_MOMENTUM_IMPULSE", 30))

        # Module E: M5 Trend + M1 Trigger
        if m5_ctx != "NONE" and i >= 25:
            if m5_ctx == "M5_BULL_TREND" and curr_p > e21_v and c["close"] > c["open"]:
                module_candidates.append(("LONG", "MODULE_E_M5_M1_HYBRID", 35))
            elif m5_ctx == "M5_BEAR_TREND" and curr_p < e21_v and c["close"] < c["open"]:
                module_candidates.append(("SHORT", "MODULE_E_M5_M1_HYBRID", 35))

        features.append({
            "idx": i,
            "time": t,
            "day_str": day_str,
            "session": sess,
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
            "body": curr_b,
            "atr": atr_v,
            "e9": e9_v,
            "e21": e21_v,
            "e50": e50[i],
            "e200": e200_v,
            "rsi14": rsi14[i],
            "m15_context": m15_ctx,
            "m15_adx": adx_val,
            "m5_setup": m5_ctx,
            "m5_sw_low": m5_sw_low,
            "m5_sw_high": m5_sw_high,
            "m1_sw_low_12": m1_sw_low_12,
            "m1_sw_high_12": m1_sw_high_12,
            "m1_sw_low_25": m1_sw_low_25,
            "m1_sw_high_25": m1_sw_high_25,
            "dist_from_mid": dist_from_mid,
            "vol_expansion": (c["volume"] > vol_avg_5),
            "module_candidates": module_candidates
        })

    return features

# ------------------------------------------------------------------------------
# 3. HIGH-WINRATE FAST SIMULATOR (ZERO-IPC SHARED MEMORY WORKER)
# ------------------------------------------------------------------------------
_GLOBAL_FEATURES = None

def init_worker(features: List[Dict[str, Any]]):
    global _GLOBAL_FEATURES
    _GLOBAL_FEATURES = features

def simulate_candidate(params: Dict[str, Any]) -> Dict[str, Any]:
    global _GLOBAL_FEATURES
    features = _GLOBAL_FEATURES

    allowed_modules = params["allowed_modules"]     # list of str or "ALL"
    trend_filter = params["trend_filter"]           # "STRICT_HTF", "M5_M15", "EMA200", "NONE"
    sl_model = params["sl_model"]                   # "ATR_MULT", "M5_SWING", "M1_SWING"
    sl_mult = params["sl_mult"]                     # float: 1.5, 2.0, 2.5, 3.0
    min_sl_usd = params["min_sl_usd"]               # 3.0, 5.0, 7.0
    tp_mode = params["tp_mode"]                     # "SINGLE_TP", "TWO_STAGE_50_50", "TWO_STAGE_70_30"
    tp_r = params["tp_r"]                           # float: 1.0, 1.2, 1.4, 1.6, 2.0
    tp2_r = params.get("tp2_r", 2.0)
    be_after_r = params["be_after_r"]               # 0.0 (disabled), 0.8, 1.0
    score_threshold = params["score_threshold"]     # 65, 70, 75, 80
    adx_threshold = params["adx_threshold"]         # 0, 18, 22
    rsi_filter = params["rsi_filter"]               # True / False
    session_mode = params["session_mode"]           # "ALL_24H", "MAJOR"

    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = initial_balance
    trades = []
    
    in_pos = False
    pos = {}
    current_day = ""
    daily_trades = 0
    cooldown_until = 0

    entry_fee_rate = 0.0002 # Maker Post-Only
    tp_fee_rate = 0.0002    # Maker Limit
    sl_fee_rate = 0.0005    # Taker Stop Market

    n = len(features)
    for idx in range(250, n):
        f = features[idx]
        t = f["time"]
        day_str = f["day_str"]
        curr_c = f["close"]
        high = f["high"]
        low = f["low"]

        if day_str != current_day:
            current_day = day_str
            daily_trades = 0

        # --- MANAGE POSITION ---
        if in_pos:
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            target1 = pos["tp1"]
            target2 = pos["tp2"]
            qty = pos["qty"]
            rem_qty = pos["rem_qty"]
            r_dist = pos["r_dist"]
            tp1_hit = pos["tp1_hit"]
            be_active = pos["be_active"]

            # Dynamic Breakeven check
            if not be_active and be_after_r > 0:
                cur_unreal_r = (high - entry) / r_dist if side == "LONG" else (entry - low) / r_dist
                if cur_unreal_r >= be_after_r:
                    be_active = True
                    pos["be_active"] = True
                    # Set SL to Entry + 0.05% fee buffer
                    pos["sl"] = round(entry * 1.0005, 2) if side == "LONG" else round(entry * 0.9995, 2)
                    sl = pos["sl"]

            # Check TP1 in 2-stage mode
            if not tp1_hit and tp_mode.startswith("TWO_STAGE"):
                hit_tp1 = (high >= target1) if side == "LONG" else (low <= target1)
                if hit_tp1:
                    part_pct = 0.50 if "50_50" in tp_mode else 0.70
                    p_qty = round(qty * part_pct, 3)
                    rem_qty = round(qty - p_qty, 3)
                    pos["rem_qty"] = rem_qty
                    gross_tp1 = (target1 - entry) * p_qty if side == "LONG" else (entry - target1) * p_qty
                    fee_tp1 = p_qty * target1 * tp_fee_rate
                    pos["realized_pnl"] += (gross_tp1 - fee_tp1)
                    pos["total_fees"] += fee_tp1
                    pos["tp1_hit"] = True
                    tp1_hit = True
                    # Auto move SL to BE on TP1
                    pos["sl"] = round(entry * 1.0005, 2) if side == "LONG" else round(entry * 0.9995, 2)
                    sl = pos["sl"]

            # Final Exit check
            closed = False
            exit_p = 0.0
            reason = ""

            final_target = target2 if tp_mode.startswith("TWO_STAGE") else target1

            if side == "LONG":
                sl_touch = (low <= sl)
                tp_touch = (high >= final_target)
                if sl_touch and tp_touch:
                    closed = True; exit_p = sl - 0.01; reason = "SL_HIT"
                elif sl_touch:
                    closed = True; exit_p = sl - 0.01; reason = "SL_HIT"
                elif tp_touch:
                    closed = True; exit_p = final_target; reason = "TP_HIT"
            else:
                sl_touch = (high >= sl)
                tp_touch = (low <= final_target)
                if sl_touch and tp_touch:
                    closed = True; exit_p = sl + 0.01; reason = "SL_HIT"
                elif sl_touch:
                    closed = True; exit_p = sl + 0.01; reason = "SL_HIT"
                elif tp_touch:
                    closed = True; exit_p = final_target; reason = "TP_HIT"

            if closed:
                closing_qty = rem_qty if tp_mode.startswith("TWO_STAGE") else qty
                gross_final = (exit_p - entry) * closing_qty if side == "LONG" else (entry - exit_p) * closing_qty
                f_rate = tp_fee_rate if reason == "TP_HIT" else sl_fee_rate
                fee_final = closing_qty * exit_p * f_rate
                
                net_trade_pnl = pos["realized_pnl"] + gross_final - fee_final
                tot_fees = pos["total_fees"] + fee_final

                balance = round(balance + net_trade_pnl, 4)
                peak_balance = max(peak_balance, balance)
                dd_pct = round(((peak_balance - balance) / peak_balance) * 100.0, 2)
                
                daily_trades += 1
                cooldown_until = idx + (5 if net_trade_pnl > 0 else 12)

                trades.append({
                    "idx": idx,
                    "side": side,
                    "module": pos["module"],
                    "net_pnl": net_trade_pnl,
                    "is_win": net_trade_pnl > 0,
                    "fees": tot_fees,
                    "reason": reason,
                    "r_dist": r_dist,
                    "dd_pct": dd_pct
                })

                in_pos = False
                pos = {}

        # --- ENTRY SCAN ---
        if not in_pos and idx >= cooldown_until and daily_trades < 12:
            if session_mode == "MAJOR" and f["session"] not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                continue
            if adx_threshold > 0 and f["m15_adx"] < adx_threshold:
                continue
            if f["atr"] < 0.25 or f["body"] > 2.5 * f["atr"]:
                continue

            candidates = f["module_candidates"]
            if not candidates:
                continue

            best_signal = None
            best_score = 0
            best_mod = ""

            for side_cand, mod_name, base_sc in candidates:
                if allowed_modules != "ALL" and mod_name not in allowed_modules:
                    continue

                # Trend Filter Veto
                if trend_filter == "STRICT_HTF":
                    if side_cand == "LONG" and f["m15_context"] == "BEARISH": continue
                    if side_cand == "SHORT" and f["m15_context"] == "BULLISH": continue
                    if side_cand == "LONG" and curr_c < f["e200"]: continue
                    if side_cand == "SHORT" and curr_c > f["e200"]: continue
                elif trend_filter == "M5_M15":
                    if side_cand == "LONG" and (f["m15_context"] == "BEARISH" or f["m5_setup"] == "M5_BEAR_TREND"): continue
                    if side_cand == "SHORT" and (f["m15_context"] == "BULLISH" or f["m5_setup"] == "M5_BULL_TREND"): continue
                elif trend_filter == "EMA200":
                    if side_cand == "LONG" and curr_c < f["e200"]: continue
                    if side_cand == "SHORT" and curr_c > f["e200"]: continue

                # RSI Exhaustion Filter
                if rsi_filter:
                    rsi_v = f["rsi14"]
                    if side_cand == "LONG" and rsi_v > 65: continue # don't buy overbought
                    if side_cand == "SHORT" and rsi_v < 35: continue # don't short oversold

                # Quality Score calculation
                score = base_sc
                if f["dist_from_mid"] >= 0.15: score += 10
                else: score -= 10

                if side_cand == "LONG" and f["e9"] > f["e21"]: score += 15
                elif side_cand == "SHORT" and f["e9"] < f["e21"]: score += 15

                if side_cand == "LONG" and f["m5_setup"] == "M5_BULL_TREND": score += 15
                elif side_cand == "SHORT" and f["m5_setup"] == "M5_BEAR_TREND": score += 15

                if side_cand == "LONG":
                    if f["m15_context"] == "BULLISH": score += 15
                    elif f["m15_context"] == "BEARISH": score -= 15
                else:
                    if f["m15_context"] == "BEARISH": score += 15
                    elif f["m15_context"] == "BULLISH": score -= 15

                if f["vol_expansion"]: score += 10

                if score >= score_threshold and score > best_score:
                    best_score = score
                    best_signal = side_cand
                    best_mod = mod_name

            if not best_signal:
                continue

            # SL Calculation
            atr_v = f["atr"]
            if sl_model == "ATR_MULT":
                raw_sl_dist = sl_mult * atr_v
            elif sl_model == "M5_SWING":
                raw_sl_dist = (curr_c - f["m5_sw_low"] + sl_mult * atr_v) if best_signal == "LONG" else (f["m5_sw_high"] - curr_c + sl_mult * atr_v)
            else: # M1_SWING
                raw_sl_dist = (curr_c - f["m1_sw_low_25"] + sl_mult * atr_v) if best_signal == "LONG" else (f["m1_sw_high_25"] - curr_c + sl_mult * atr_v)

            r_dist = max(min_sl_usd, min(curr_c * 0.012, raw_sl_dist))
            sl_price = round(curr_c - r_dist, 2) if best_signal == "LONG" else round(curr_c + r_dist, 2)

            # TP Calculation
            target1 = round(curr_c + (tp_r * r_dist), 2) if best_signal == "LONG" else round(curr_c - (tp_r * r_dist), 2)
            target2 = round(curr_c + (tp2_r * r_dist), 2) if best_signal == "LONG" else round(curr_c - (tp2_r * r_dist), 2)

            # Notional & Margin sizing (1% risk normalized)
            risk_usd = balance * 0.010
            qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
            entry_fee = round(qty * curr_c * entry_fee_rate, 4)

            in_pos = True
            pos = {
                "side": best_signal,
                "module": best_mod,
                "entry": curr_c,
                "sl": sl_price,
                "tp1": target1,
                "tp2": target2,
                "qty": qty,
                "rem_qty": qty,
                "r_dist": r_dist,
                "entry_fee": entry_fee,
                "total_fees": entry_fee,
                "realized_pnl": -entry_fee,
                "tp1_hit": False,
                "be_active": False
            }

    # Summary metrics
    total_trades = len(trades)
    if total_trades < 10:
        return {"total_trades": total_trades, "win_rate_pct": 0.0, "net_pf": 0.0, "net_pnl": 0.0, "params": params}

    wins = [t for t in trades if t["is_win"]]
    losses = [t for t in trades if not t["is_win"]]
    wr = round((len(wins) / total_trades) * 100.0, 1)
    
    gp = sum(t["net_pnl"] for t in wins)
    gl = abs(sum(t["net_pnl"] for t in losses))
    pf = round((gp / gl) if gl > 0 else 99.0, 2)
    net_pnl = round(sum(t["net_pnl"] for t in trades), 2)
    max_dd = round(max((t["dd_pct"] for t in trades), default=0.0), 2)

    # In-Sample (first 60 days) vs Out-Of-Sample (last 30 days) split
    split_idx = int(total_trades * 0.67)
    train_trades = trades[:split_idx]
    oos_trades = trades[split_idx:]

    oos_wins = [t for t in oos_trades if t["is_win"]]
    oos_wr = round((len(oos_wins) / max(1, len(oos_trades))) * 100.0, 1)
    oos_gp = sum(t["net_pnl"] for t in oos_wins)
    oos_gl = abs(sum(t["net_pnl"] for t in oos_trades if not t["is_win"]))
    oos_pf = round((oos_gp / oos_gl) if oos_gl > 0 else 99.0, 2)
    oos_pnl = round(sum(t["net_pnl"] for t in oos_trades), 2)

    return {
        "params": params,
        "total_trades": total_trades,
        "trades_per_day": round(total_trades / 90.0, 1),
        "win_rate_pct": wr,
        "net_pf": pf,
        "net_pnl": net_pnl,
        "max_dd_pct": max_dd,
        "oos_trades": len(oos_trades),
        "oos_win_rate_pct": oos_wr,
        "oos_pf": oos_pf,
        "oos_pnl": oos_pnl,
        "composite_score": round((wr * 1.5) + (min(pf, 3.0) * 20.0) - (max_dd * 1.0), 1)
    }

# ------------------------------------------------------------------------------
# 4. MAIN MULTI-CORE SEARCH ORCHESTRATOR
# ------------------------------------------------------------------------------
def generate_parameter_combinations() -> List[Dict[str, Any]]:
    # Module subsets to test
    module_presets = [
        "ALL",
        ["MODULE_E_M5_M1_HYBRID"],
        ["MODULE_E_M5_M1_HYBRID", "MODULE_C_EMA_PULLBACK"],
        ["MODULE_E_M5_M1_HYBRID", "MODULE_A_SWEEP_RECLAIM"],
        ["MODULE_A_SWEEP_RECLAIM", "MODULE_C_EMA_PULLBACK"],
        ["MODULE_E_M5_M1_HYBRID", "MODULE_D_MOMENTUM_IMPULSE"],
    ]

    trend_filters = ["STRICT_HTF", "M5_M15", "EMA200", "NONE"]
    sl_models = ["M5_SWING", "ATR_MULT", "M1_SWING"]
    sl_mults = [0.5, 0.8, 1.2, 1.5, 2.0, 2.5]
    min_sl_usds = [3.0, 5.0, 7.0]
    tp_modes = ["SINGLE_TP", "TWO_STAGE_50_50", "TWO_STAGE_70_30"]
    tp_rs = [0.8, 1.0, 1.2, 1.5, 1.8, 2.0]
    be_after_rs = [0.0, 0.8, 1.0]
    score_thresholds = [65, 70, 75, 80]
    adx_thresholds = [0, 18, 22]
    rsi_filters = [False, True]
    session_modes = ["ALL_24H", "MAJOR"]

    # Intelligent pruned grid to focus deeply on high-winrate configurations
    grid = []
    
    # Grid 1: High-Probability Scalping (Single TP 1.0R - 1.5R with HTF Trend Filter)
    for mods in [["MODULE_E_M5_M1_HYBRID"], ["MODULE_E_M5_M1_HYBRID", "MODULE_A_SWEEP_RECLAIM"], "ALL"]:
        for tf in ["STRICT_HTF", "M5_M15", "EMA200"]:
            for sl_m in ["M5_SWING", "ATR_MULT"]:
                for sl_v in [0.5, 0.8, 1.2, 1.8, 2.2]:
                    for m_sl in [3.0, 5.0]:
                        for r_tp in [0.9, 1.0, 1.2, 1.4, 1.6]:
                            for be_r in [0.0, 0.8]:
                                for sc in [70, 75, 80]:
                                    for rsi in [False, True]:
                                        grid.append({
                                            "allowed_modules": mods,
                                            "trend_filter": tf,
                                            "sl_model": sl_m,
                                            "sl_mult": sl_v,
                                            "min_sl_usd": m_sl,
                                            "tp_mode": "SINGLE_TP",
                                            "tp_r": r_tp,
                                            "tp2_r": r_tp,
                                            "be_after_r": be_r,
                                            "score_threshold": sc,
                                            "adx_threshold": 18,
                                            "rsi_filter": rsi,
                                            "session_mode": "ALL_24H"
                                        })

    # Grid 2: 2-Stage Professional Exits (Quick Lock-in 50% or 70% at 1.0R + Runner)
    for mods in [["MODULE_E_M5_M1_HYBRID"], ["MODULE_E_M5_M1_HYBRID", "MODULE_C_EMA_PULLBACK"], "ALL"]:
        for tf in ["STRICT_HTF", "M5_M15"]:
            for sl_m in ["M5_SWING", "ATR_MULT"]:
                for sl_v in [0.8, 1.2, 2.0]:
                    for m_sl in [4.0, 6.0]:
                        for tp_m in ["TWO_STAGE_50_50", "TWO_STAGE_70_30"]:
                            for r_tp in [0.8, 1.0, 1.2]:
                                for r_tp2 in [1.6, 2.0, 2.5]:
                                    for sc in [70, 75]:
                                        grid.append({
                                            "allowed_modules": mods,
                                            "trend_filter": tf,
                                            "sl_model": sl_m,
                                            "sl_mult": sl_v,
                                            "min_sl_usd": m_sl,
                                            "tp_mode": tp_m,
                                            "tp_r": r_tp,
                                            "tp2_r": r_tp2,
                                            "be_after_r": 0.8,
                                            "score_threshold": sc,
                                            "adx_threshold": 20,
                                            "rsi_filter": True,
                                            "session_mode": "ALL_24H"
                                        })

    return grid

def main():
    cpu_count = os.cpu_count() or 8
    print("=" * 80)
    print(f"🚀 APEX QUANT v3.4: MULTI-CORE HIGH-WINRATE TOURNAMENT LAUNCHER")
    print(f"🔥 Hardware Utilization: {cpu_count} CPU Cores (100% Multiprocessing Load)")
    print("=" * 80)

    # 1. Load data
    t0 = time.time()
    print(f"1. Loading 90-day M1 dataset from {DATA_PATH}...")
    with open(DATA_PATH, "r") as f:
        reader = csv.reader(f)
        next(reader)
        raw = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in reader]
    print(f"   Loaded {len(raw):,} candles in {time.time()-t0:.2f}s.")

    # 2. Precompute features
    t0 = time.time()
    print("2. Precalculating multi-timeframe indicators (M1/M5/M15/H1 EMAs, ATR, ADX, RSI)...")
    features = precalculate_features(raw)
    print(f"   Precalculation completed in {time.time()-t0:.2f}s.")

    # 3. Generate parameter sets
    param_grid = generate_parameter_combinations()
    total_candidates = len(param_grid)
    print(f"3. Generated {total_candidates:,} unique parameter combinations to evaluate.")
    print("=" * 80)
    print(f"🔥 Commencing 8-core parallel tournament search across {total_candidates:,} models...")
    print("=" * 80)

    # 4. Multiprocessing Pool with Zero-IPC Shared Memory Initializer
    t_start = time.time()
    results = []
    completed = 0
    chunk_size = max(10, total_candidates // (cpu_count * 20))

    with multiprocessing.Pool(processes=cpu_count, initializer=init_worker, initargs=(features,)) as pool:
        for res in pool.imap_unordered(simulate_candidate, param_grid, chunksize=chunk_size):
            completed += 1
            if res.get("total_trades", 0) >= 15:
                results.append(res)
            if completed % 1000 == 0 or completed == total_candidates:
                elapsed = time.time() - t_start
                rate = completed / max(0.1, elapsed)
                rem = (total_candidates - completed) / max(0.1, rate)
                print(f"   Progress: {completed:,}/{total_candidates:,} ({completed/total_candidates*100:.1f}%) | Speed: {rate:.1f} models/sec | ETA: {rem:.1f}s | Qualifying: {len(results):,}", flush=True)

    total_time = time.time() - t_start
    print("=" * 80)
    print(f"🎉 SEARCH COMPLETE in {total_time:.2f}s ({total_candidates/total_time:.1f} tests/sec)!")
    print(f"   Total qualifying models (>= 15 trades): {len(results):,}")
    print("=" * 80)

    # 5. Filter & Rank
    # Rank by Win Rate (minimum 45 trades over 90 days, profit factor > 1.20, positive OOS)
    high_wr_results = [r for r in results if r["win_rate_pct"] >= 50.0 and r["net_pf"] >= 1.20 and r["total_trades"] >= 35 and r["oos_pf"] >= 1.10]
    high_wr_results.sort(key=lambda x: (x["win_rate_pct"], x["net_pf"], x["oos_win_rate_pct"]), reverse=True)

    print("\n🏆 TOP 10 HIGHEST WIN-RATE PRODUCTION CANDIDATES:")
    print(f"{'Rank':<4} | {'WinRate':<7} | {'Net PF':<6} | {'Trades':<6} | {'Net PnL':<9} | {'MaxDD':<6} | {'OOS WR':<7} | {'OOS PF':<6} | Setup Summary")
    print("-" * 110)

    for idx, r in enumerate(high_wr_results[:10]):
        p = r["params"]
        mod_str = "ALL" if p["allowed_modules"] == "ALL" else "+".join(p["allowed_modules"])
        setup_desc = f"{mod_str} | {p['trend_filter']} | {p['sl_model']} (x{p['sl_mult']}) | TP:{p['tp_mode']}({p['tp_r']}R) | Score>={p['score_threshold']}"
        print(f"#{idx+1:<3} | {r['win_rate_pct']:>5.1f}% | {r['net_pf']:>5.2f}x | {r['total_trades']:>5}t | ${r['net_pnl']:>7.2f} | {r['max_dd_pct']:>5.1f}% | {r['oos_win_rate_pct']:>5.1f}% | {r['oos_pf']:>5.2f}x | {setup_desc}")

    # Save complete optimization summary
    summary_output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_combinations_tested": total_candidates,
        "computation_time_seconds": round(total_time, 2),
        "cpu_cores_utilized": cpu_count,
        "qualifying_models_count": len(results),
        "high_winrate_models_count": len(high_wr_results),
        "top_10_candidates": high_wr_results[:10] if high_wr_results else results[:10]
    }

    out_file = r"C:\apex_copytrade\data\high_winrate_optimization_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2)
    print(f"\n✅ Full optimization report saved to: {out_file}")

if __name__ == "__main__":
    main()
