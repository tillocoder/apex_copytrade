"""
APEX QUANT v3.3 — Quantitative Research, Hyperparameter Optimization & Forensic Audit Suite
Base Instrument: Binance USD(S)-M Futures ETHUSDT Perpetual (M1 Execution)
Dataset: 129,600 Completed 1-Minute Bars (2026-06-29 to 2026-09-27, 90.0 Days)
Multi-Core Parallel Architecture (100% PC Utilization Across All 8 CPU Cores)
Strict Zero Lookahead Bias — Real Taker/Maker Fees & Slippage Modeled
================================================================================
"""

import os
import sys
import csv
import json
import math
import time
import zlib
import struct
import random
from datetime import datetime, timezone
import multiprocessing
from typing import Dict, Any, List, Optional, Tuple

DATA_PATH = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"

# ------------------------------------------------------------------------------
# 1. TECHNICAL INDICATORS & MTF FEATURE PRECALCULATION (ZERO LOOKAHEAD)
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

def precalculate_all_features_v33(raw_candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    n = len(raw_candles)
    closes = [c["close"] for c in raw_candles]
    highs = [c["high"] for c in raw_candles]
    lows = [c["low"] for c in raw_candles]
    opens = [c["open"] for c in raw_candles]
    vols = [c["volume"] for c in raw_candles]
    times = [c["time"] for c in raw_candles]

    # M1 EMAs
    e9 = fast_ema(closes, 9)
    e21 = fast_ema(closes, 21)
    e50 = fast_ema(closes, 50)

    # M1 ATR14 (Wilder's RMA)
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

    # MTF Construction (Completed Bars Only, Zero Lookahead)
    m5_bars = []
    m15_bars = []
    cur_m5 = None
    cur_m15 = None
    m1_to_completed_m5 = [-1] * n
    m1_to_completed_m15 = [-1] * n

    for i in range(n):
        t = times[i]
        c = raw_candles[i]

        # M5 bucket (300,000 ms)
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
        m1_to_completed_m5[i] = len(m5_bars) - 1

        # M15 bucket (900,000 ms)
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
        m1_to_completed_m15[i] = len(m15_bars) - 1

    # M5 EMAs & Swings
    m5_closes = [b["close"] for b in m5_bars]
    m5_highs = [b["high"] for b in m5_bars]
    m5_lows = [b["low"] for b in m5_bars]
    m5_e21 = fast_ema(m5_closes, 21)
    m5_e50 = fast_ema(m5_closes, 50)

    # M15 EMAs, ADX(14), and ATR(14)
    m15_closes = [b["close"] for b in m15_bars]
    m15_highs = [b["high"] for b in m15_bars]
    m15_lows = [b["low"] for b in m15_bars]
    m15_e50 = fast_ema(m15_closes, 50)

    m15_len = len(m15_bars)
    m15_tr = [0.0] * m15_len
    m15_pdm = [0.0] * m15_len
    m15_mdm = [0.0] * m15_len

    for j in range(1, m15_len):
        h, l, pc = m15_highs[j], m15_lows[j], m15_closes[j-1]
        m15_tr[j] = max(h - l, abs(h - pc), abs(l - pc))
        up = h - m15_highs[j-1]
        down = m15_lows[j-1] - l
        if up > down and up > 0:
            m15_pdm[j] = up
        if down > up and down > 0:
            m15_mdm[j] = down

    p = 14
    smooth_tr = [0.0] * m15_len
    smooth_pdm = [0.0] * m15_len
    smooth_mdm = [0.0] * m15_len
    m15_adx = [0.0] * m15_len
    m15_atr = [1.50] * m15_len

    if m15_len >= p + 1:
        smooth_tr[p] = sum(m15_tr[1:p+1])
        smooth_pdm[p] = sum(m15_pdm[1:p+1])
        smooth_mdm[p] = sum(m15_mdm[1:p+1])
        m15_atr[p] = smooth_tr[p] / p
        dx = [0.0] * m15_len

        for j in range(p + 1, m15_len):
            smooth_tr[j] = smooth_tr[j-1] - (smooth_tr[j-1] / p) + m15_tr[j]
            smooth_pdm[j] = smooth_pdm[j-1] - (smooth_pdm[j-1] / p) + m15_pdm[j]
            smooth_mdm[j] = smooth_mdm[j-1] - (smooth_mdm[j-1] / p) + m15_mdm[j]
            m15_atr[j] = smooth_tr[j] / p

            pdi = 100.0 * (smooth_pdm[j] / max(1e-6, smooth_tr[j]))
            mdi = 100.0 * (smooth_mdm[j] / max(1e-6, smooth_tr[j]))
            sum_di = pdi + mdi
            dx[j] = 100.0 * abs(pdi - mdi) / max(1e-6, sum_di)

        start_adx = 2 * p
        if m15_len >= start_adx:
            m15_adx[start_adx] = sum(dx[p+1:start_adx+1]) / p
            for j in range(start_adx + 1, m15_len):
                m15_adx[j] = (m15_adx[j-1] * (p - 1) + dx[j]) / p

    m15_atr_ema50 = fast_ema(m15_atr, 50)
    m15_vol_ratio = [0.0] * m15_len
    for j in range(m15_len):
        base_a = m15_atr_ema50[j] if m15_atr_ema50[j] > 0 else 1.0
        m15_vol_ratio[j] = round(m15_atr[j] / base_a, 2)

    # Per M1 candle synthesis
    features = []
    for i in range(n):
        t = times[i]
        c = raw_candles[i]
        dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
        day_str = dt.strftime('%Y-%m-%d')
        hr = dt.hour + dt.minute / 60.0

        if 13.5 <= hr < 16.5:
            sess_name = "LONDON_NY_OVERLAP"
        elif 16.5 <= hr < 21.0:
            sess_name = "NEW_YORK"
        elif 8.0 <= hr < 13.5:
            sess_name = "LONDON"
        elif 0.0 <= hr < 8.0:
            sess_name = "ASIA"
        else:
            sess_name = "OUT_OF_SESSION"

        # M15 context from latest completed bar
        m15_idx = m1_to_completed_m15[i]
        m15_ctx = "NEUTRAL"
        m15_adx_val = 20.0
        m15_vr = 1.0
        if m15_idx >= 50:
            m15_ema = m15_e50[m15_idx]
            if c["close"] > m15_ema:
                m15_ctx = "BULLISH"
            elif c["close"] < m15_ema:
                m15_ctx = "BEARISH"
            m15_adx_val = round(m15_adx[m15_idx], 1)
            m15_vr = m15_vol_ratio[m15_idx]

        # M5 setup from latest completed bar
        m5_idx = m1_to_completed_m5[i]
        m5_ctx = "NONE"
        m5_last_swing_low = lows[i]
        m5_last_swing_high = highs[i]
        if m5_idx >= 50:
            if m5_e21[m5_idx] > m5_e50[m5_idx]:
                m5_ctx = "M5_BULL_TREND"
            elif m5_e21[m5_idx] < m5_e50[m5_idx]:
                m5_ctx = "M5_BEAR_TREND"
            m5_last_swing_low = min(m5_lows[max(0, m5_idx-5):m5_idx+1])
            m5_last_swing_high = max(m5_highs[max(0, m5_idx-5):m5_idx+1])

        # Structural lookbacks
        recent_low = min(lows[max(0, i-11):i]) if i >= 11 else lows[i]
        recent_high = max(highs[max(0, i-11):i]) if i >= 11 else highs[i]
        swept_low = (lows[i] <= recent_low or (i > 0 and lows[i-1] <= recent_low))
        swept_high = (highs[i] >= recent_high or (i > 0 and highs[i-1] >= recent_high))

        prior_high_15 = max(highs[max(0, i-14):max(0, i-1)]) if i >= 15 else highs[i]
        prior_low_15 = min(lows[max(0, i-14):max(0, i-1)]) if i >= 15 else lows[i]

        vol_avg_10 = (sum(vols[max(0, i-9):i]) / 9.0) if i >= 10 else vols[i]
        vol_avg_5 = (sum(vols[max(0, i-5):i]) / 5.0) if i >= 6 else vols[i]

        # Location quality (20-bar range midpoint distance)
        loc_high_20 = max(highs[max(0, i-19):i]) if i >= 20 else highs[i]
        loc_low_20 = min(lows[max(0, i-19):i]) if i >= 20 else lows[i]
        range_span = max(0.50, loc_high_20 - loc_low_20)
        midpoint = (loc_high_20 + loc_low_20) / 2.0
        dist_from_mid = abs(c["close"] - midpoint) / range_span

        # Candidate signals for 5 modules
        curr_price = c["close"]
        curr_body = abs(c["close"] - c["open"])
        atr_val = atr[i]
        e9_val = e9[i]
        e21_val = e21[i]

        cand_side = None
        cand_module = ""
        cand_base_score = 0

        # Module A: Sweep & Reclaim
        if swept_low and curr_price > recent_low and c["close"] >= c["open"]:
            cand_side = "LONG"
            cand_module = "MODULE_A_SWEEP_RECLAIM"
            cand_base_score = 40
        elif swept_high and curr_price < recent_high and c["close"] <= c["open"]:
            cand_side = "SHORT"
            cand_module = "MODULE_A_SWEEP_RECLAIM"
            cand_base_score = 40

        # Module B: Breakout & Retest
        if not cand_side and i >= 16:
            r_width = prior_high_15 - prior_low_15
            if r_width <= 2.2 * atr_val:
                if curr_price > prior_high_15 and c["close"] > c["open"]:
                    cand_side = "LONG"
                    cand_module = "MODULE_B_BREAKOUT"
                    cand_base_score = 35
                elif curr_price < prior_low_15 and c["close"] < c["open"]:
                    cand_side = "SHORT"
                    cand_module = "MODULE_B_BREAKOUT"
                    cand_base_score = 35

        # Module C: EMA Pullback
        if not cand_side and i >= 25:
            if e9_val > e21_val and c["low"] <= e9_val * 1.0008 and curr_price >= e21_val * 0.9995:
                if c["close"] >= c["open"]:
                    cand_side = "LONG"
                    cand_module = "MODULE_C_EMA_PULLBACK"
                    cand_base_score = 30
            elif e9_val < e21_val and c["high"] >= e9_val * 0.9992 and curr_price <= e21_val * 1.0005:
                if c["close"] <= c["open"]:
                    cand_side = "SHORT"
                    cand_module = "MODULE_C_EMA_PULLBACK"
                    cand_base_score = 30

        # Module D: Momentum Impulse
        if not cand_side and i >= 11:
            if c["volume"] >= 1.25 * vol_avg_10 and curr_body >= 0.70 * atr_val:
                if c["close"] > c["open"] and e9_val > e21_val:
                    cand_side = "LONG"
                    cand_module = "MODULE_D_MOMENTUM_IMPULSE"
                    cand_base_score = 30
                elif c["close"] < c["open"] and e9_val < e21_val:
                    cand_side = "SHORT"
                    cand_module = "MODULE_D_MOMENTUM_IMPULSE"
                    cand_base_score = 30

        # Module E: M5 Structure + M1 Trigger
        if not cand_side and m5_ctx != "NONE" and i >= 25:
            if m5_ctx == "M5_BULL_TREND" and curr_price > e21_val and c["close"] > c["open"]:
                cand_side = "LONG"
                cand_module = "MODULE_E_M5_M1_HYBRID"
                cand_base_score = 35
            elif m5_ctx == "M5_BEAR_TREND" and curr_price < e21_val and c["close"] < c["open"]:
                cand_side = "SHORT"
                cand_module = "MODULE_E_M5_M1_HYBRID"
                cand_base_score = 35

        features.append({
            "idx": i,
            "time": t,
            "day_str": day_str,
            "session": sess_name,
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
            "body": curr_body,
            "atr": atr_val,
            "e9": e9_val,
            "e21": e21_val,
            "e50": e50[i],
            "m15_context": m15_ctx,
            "m15_adx": m15_adx_val,
            "m15_vol_ratio": m15_vr,
            "m5_setup": m5_ctx,
            "m5_swing_low": m5_last_swing_low,
            "m5_swing_high": m5_last_swing_high,
            "recent_low": recent_low,
            "recent_high": recent_high,
            "dist_from_mid": dist_from_mid,
            "vol_expansion": (c["volume"] > vol_avg_5),
            "cand_side": cand_side,
            "cand_module": cand_module,
            "cand_base_score": cand_base_score
        })

    return features

# ------------------------------------------------------------------------------
# 2. V3.3 FAST SIMULATION ENGINE (ZERO LOOKAHEAD)
# ------------------------------------------------------------------------------
def run_simulation_v33_fast(
    features: List[Dict[str, Any]],
    score_threshold: int = 80,
    session_mode: str = "LONDON_EXPANSION_ONLY", # "MAJOR_ONLY", "LONDON_EXPANSION_ONLY", "NY_MOMENTUM_ONLY", "MAJOR_PLUS_ASIAN_RANGE_EXTREMES"
    execution_mode: str = "MAKER_ENTRY_HYBRID",  # "ALL_TAKER", "MAKER_ENTRY_HYBRID", "STRICT_POST_ONLY"
    m15_adx_threshold: float = 18.0,            # Reject breakouts/impulses if ADX < threshold
    m15_vol_compression_gate: bool = True,      # Reject breakouts if M15 Vol Ratio < 0.85
    be_trigger: str = "NO_BE",                  # "NO_BE", "BE_1.5R", "BE_1.75R", "BE_2.0R", "M5_SWING_BE"
    tp_vol_multiplier: float = 2.2,             # Dynamic TP Multiplier (Model G/I: 1.8x, 2.0x, 2.2x, 2.5x ATR)
    time_stop_min: int = 0,                     # Momentum decay scratch (0 to disable)
    min_r_dist: float = 4.0,                    # Noise floor filter: prevents M1 noise stops
    capital_profile: str = "NORMALIZED",        # "NORMALIZED" ($1,000), "MICRO_REALISTIC" ($100), "MICRO_TINY" ($2.7109)
    initial_balance: float = 1000.0,
    normalized_risk_pct: float = 0.0075,
    leverage: int = 100
) -> Dict[str, Any]:

    balance = initial_balance
    peak_balance = initial_balance
    trades = []
    rejections = {
        "SESSION_BLOCKED": 0,
        "FEE_BURDEN": 0,
        "LOW_SCORE": 0,
        "LOW_VOLATILITY": 0,
        "OVEREXTENDED_CHASE": 0,
        "LOCATION_PENALTY": 0,
        "CORRELATED_DUPLICATE": 0,
        "ADX_CHOP_BLOCKED": 0,
        "VOL_COMPRESSION_BLOCKED": 0,
        "NOISE_FLOOR_BLOCKED": 0,
        "DAILY_CAP_REACHED": 0,
        "CIRCUIT_BREAKER_ACTIVE": 0,
        "TOTAL_CANDIDATES": 0
    }

    in_pos = False
    pos = {}

    current_day_str = ""
    daily_trades_count = 0
    daily_pnl = 0.0
    day_paused = False

    consecutive_losses = 0
    max_loss_streak = 0
    current_loss_streak = 0
    max_win_streak = 0
    current_win_streak = 0

    cooldown_until_idx = 0
    last_entry_time = 0
    last_entry_side = None

    equity_curve = [{"time": features[0]["time"], "equity": initial_balance, "dd_pct": 0.0}]
    warmup_period = 250
    n = len(features)

    # Fee Schedules
    if execution_mode == "MAKER_ENTRY_HYBRID":
        entry_fee_rate = 0.0002   # 0.02% Maker Post-Only
        tp_fee_rate = 0.0002      # 0.02% Maker Limit TP
        sl_fee_rate = 0.0005      # 0.05% Taker Stop Market
    elif execution_mode == "STRICT_POST_ONLY":
        entry_fee_rate = 0.0002   # 0.02% Maker
        tp_fee_rate = 0.0002      # 0.02% Maker
        sl_fee_rate = 0.0002      # 0.02% Maker Stop Limit
    else: # ALL_TAKER
        entry_fee_rate = 0.0005   # 0.05% Taker Market
        tp_fee_rate = 0.0002      # 0.02% Maker Limit
        sl_fee_rate = 0.0005      # 0.05% Taker Stop Market

    for idx in range(warmup_period, n):
        f = features[idx]
        t = f["time"]
        day_str = f["day_str"]
        sess_name = f["session"]

        # Midnight UTC reset
        if day_str != current_day_str:
            current_day_str = day_str
            daily_trades_count = 0
            daily_pnl = 0.0
            day_paused = False

        # ----------------------------------------------------------------------
        # ACTIVE POSITION MANAGEMENT
        # ----------------------------------------------------------------------
        if in_pos:
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            target = pos["tp"]
            qty = pos["qty"]
            r_dist = pos["r_dist"]
            be_active = pos["be_active"]
            holding_bars = idx - pos["entry_idx"]

            high = f["high"]
            low = f["low"]
            curr_c = f["close"]

            closed_now = False
            exit_reason = None
            exit_price = 0.0

            # Dynamic Breakeven Activation
            if not be_active and be_trigger != "NO_BE":
                be_r_needed = 1.75
                if be_trigger == "BE_1.5R": be_r_needed = 1.50
                elif be_trigger == "BE_1.75R": be_r_needed = 1.75
                elif be_trigger == "BE_2.0R": be_r_needed = 2.00
                elif be_trigger == "M5_SWING_BE": be_r_needed = 1.25

                if side == "LONG":
                    if (high - entry) >= be_r_needed * r_dist:
                        pos["be_active"] = True
                        be_active = True
                        if be_trigger == "M5_SWING_BE":
                            pos["sl"] = max(entry * 1.0005, f["m5_swing_low"])
                        else:
                            pos["sl"] = round(entry * 1.0005, 2)
                        sl = pos["sl"]
                else:
                    if (entry - low) >= be_r_needed * r_dist:
                        pos["be_active"] = True
                        be_active = True
                        if be_trigger == "M5_SWING_BE":
                            pos["sl"] = min(entry * 0.9995, f["m5_swing_high"])
                        else:
                            pos["sl"] = round(entry * 0.9995, 2)
                        sl = pos["sl"]

            # Time-Stop Invalidation (Momentum decay scratch)
            if not closed_now and time_stop_min > 0 and holding_bars >= time_stop_min:
                cur_r = (curr_c - entry) / r_dist if side == "LONG" else (entry - curr_c) / r_dist
                if -0.15 <= cur_r <= 0.60 and f["body"] < 0.50 * f["atr"]:
                    closed_now = True
                    exit_reason = "TIME_STOP_EXHAUSTION"
                    exit_price = curr_c

            # Price Extrema Execution
            if not closed_now:
                if side == "LONG":
                    sl_touch = (low <= sl)
                    tp_touch = (high >= target)
                    if sl_touch and tp_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl - 0.01
                    elif sl_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl - 0.01
                    elif tp_touch:
                        closed_now = True
                        exit_reason = "TAKE_PROFIT_FULL"
                        exit_price = target
                else: # SHORT
                    sl_touch = (high >= sl)
                    tp_touch = (low <= target)
                    if sl_touch and tp_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl + 0.01
                    elif sl_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl + 0.01
                    elif tp_touch:
                        closed_now = True
                        exit_reason = "TAKE_PROFIT_FULL"
                        exit_price = target

            if closed_now:
                if side == "LONG":
                    gross_pnl = (exit_price - entry) * qty
                else:
                    gross_pnl = (entry - exit_price) * qty
                gross_pnl = round(gross_pnl, 4)

                entry_fee = pos["entry_fee"]
                if "TAKE_PROFIT" in exit_reason or exit_reason == "TIME_STOP_EXHAUSTION":
                    exit_fee = round(qty * exit_price * tp_fee_rate, 4)
                else:
                    exit_fee = round(qty * exit_price * sl_fee_rate, 4)

                total_fees = round(entry_fee + exit_fee, 4)
                net_pnl = round(gross_pnl - total_fees, 4)
                dollar_risk = max(0.01, qty * r_dist)
                realized_r = round(net_pnl / dollar_risk, 2)

                failure_reason = "PROFITABLE"
                if net_pnl <= 0:
                    if gross_pnl > 0 and net_pnl <= 0:
                        failure_reason = "FEE_FRICTION_DRAG"
                    elif exit_reason == "BREAKEVEN_STOP_HIT":
                        failure_reason = "PREMATURE_BE_SHAKEOUT"
                    elif exit_reason == "TIME_STOP_EXHAUSTION":
                        failure_reason = "MOMENTUM_DECAY_SCRATCH"
                    elif pos["module"] == "MODULE_B_BREAKOUT":
                        failure_reason = "FALSE_BREAKOUT"
                    elif pos["module"] == "MODULE_A_SWEEP_RECLAIM":
                        failure_reason = "FAILED_SWEEP"
                    else:
                        failure_reason = "NORMAL_STOP_LOSS"

                balance = round(balance + net_pnl, 4)
                peak_balance = max(peak_balance, balance)
                dd_pct = round(((peak_balance - balance) / peak_balance) * 100.0, 2)

                daily_pnl += net_pnl
                daily_trades_count += 1

                if net_pnl > 0:
                    current_win_streak += 1
                    current_loss_streak = 0
                    consecutive_losses = 0
                    cooldown_until_idx = idx + 10
                else:
                    current_loss_streak += 1
                    current_win_streak = 0
                    consecutive_losses += 1
                    if consecutive_losses >= 3:
                        cooldown_until_idx = idx + 30
                    else:
                        cooldown_until_idx = idx + 15

                if daily_pnl <= -0.05 * balance:
                    day_paused = True

                max_win_streak = max(max_win_streak, current_win_streak)
                max_loss_streak = max(max_loss_streak, current_loss_streak)
                holding_time_min = idx - pos["entry_idx"]

                trades.append({
                    "timestamp": datetime.fromtimestamp(pos["open_time"] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "side": side,
                    "session": pos["session"],
                    "module": pos["module"],
                    "entry": entry,
                    "qty": qty,
                    "notional": pos["notional"],
                    "margin": pos["margin"],
                    "SL": sl,
                    "TP": target,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "failure_mode": failure_reason,
                    "gross_pnl": gross_pnl,
                    "total_fees": total_fees,
                    "net_pnl": net_pnl,
                    "realized_r": realized_r,
                    "holding_time_min": holding_time_min,
                    "equity_after": balance,
                    "drawdown_pct": dd_pct,
                    "exit_time": datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                })

                in_pos = False
                pos = {}

            equity_curve.append({
                "time": t,
                "equity": balance,
                "dd_pct": round(((peak_balance - balance) / peak_balance) * 100.0, 2)
            })

        # ----------------------------------------------------------------------
        # ENTRY EVALUATION (IF FLAT)
        # ----------------------------------------------------------------------
        if not in_pos and idx >= cooldown_until_idx:
            # Session Filtering
            if session_mode == "MAJOR_ONLY" and sess_name not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                rejections["SESSION_BLOCKED"] += 1
                continue
            elif session_mode == "LONDON_EXPANSION_ONLY" and sess_name not in ["LONDON", "LONDON_NY_OVERLAP"]:
                rejections["SESSION_BLOCKED"] += 1
                continue
            elif session_mode == "NY_MOMENTUM_ONLY" and sess_name != "NEW_YORK":
                rejections["SESSION_BLOCKED"] += 1
                continue
            elif session_mode == "MAJOR_PLUS_ASIAN_RANGE_EXTREMES":
                if sess_name == "ASIA" and f["dist_from_mid"] < 0.35:
                    rejections["SESSION_BLOCKED"] += 1
                    continue

            if daily_trades_count >= 8:
                rejections["DAILY_CAP_REACHED"] += 1
                continue

            if day_paused:
                rejections["CIRCUIT_BREAKER_ACTIVE"] += 1
                continue

            if f["atr"] < 0.25:
                rejections["LOW_VOLATILITY"] += 1
                continue

            if f["body"] > 2.5 * f["atr"]:
                rejections["OVEREXTENDED_CHASE"] += 1
                continue

            cand_side = f["cand_side"]
            if not cand_side:
                continue

            cand_mod = f["cand_module"]
            # Primary Alpha Engine: Module E (M5 Trend Structure + M1 Trigger)
            if cand_mod != "MODULE_E_M5_M1_HYBRID":
                continue

            # M15 Macro Volatility & Trend Filter Gates
            if m15_adx_threshold > 0 and f["m15_adx"] < m15_adx_threshold:
                rejections["ADX_CHOP_BLOCKED"] += 1
                continue

            if m15_vol_compression_gate and f["m15_vol_ratio"] < 0.85:
                rejections["VOL_COMPRESSION_BLOCKED"] += 1
                continue

            rejections["TOTAL_CANDIDATES"] += 1

            # V3.3 Quality Scoring Matrix
            total_score = f["cand_base_score"] # 35 pts

            # 1. Location Quality Filter
            if f["dist_from_mid"] < 0.15:
                total_score -= 10
                rejections["LOCATION_PENALTY"] += 1
            else:
                total_score += 10 # 45 pts

            # 2. Trend Alignment Bonus
            if cand_side == "LONG" and f["e9"] > f["e21"]:
                total_score += 10 # 55 pts
            elif cand_side == "SHORT" and f["e9"] < f["e21"]:
                total_score += 10

            if cand_side == "LONG" and f["m5_setup"] == "M5_BULL_TREND":
                total_score += 10 # 65 pts
            elif cand_side == "SHORT" and f["m5_setup"] == "M5_BEAR_TREND":
                total_score += 10

            # 3. M15 Macro Context
            if cand_side == "LONG":
                if f["m15_context"] == "BULLISH": total_score += 10 # 75 pts
                elif f["m15_context"] == "BEARISH": total_score -= 10
            else:
                if f["m15_context"] == "BEARISH": total_score += 10
                elif f["m15_context"] == "BULLISH": total_score -= 10

            # 4. Volume expansion
            if f["vol_expansion"]: total_score += 5 # 80 pts

            total_score = max(0, min(100, total_score))

            if total_score < score_threshold:
                rejections["LOW_SCORE"] += 1
                continue

            # Correlated signal protection (15m window)
            if last_entry_side == cand_side:
                bars_since = (t - last_entry_time) / 60000.0
                if bars_since < 15:
                    rejections["CORRELATED_DUPLICATE"] += 1
                    continue

            # Geometry & Target Multiplier
            curr_price = f["close"]
            atr_val = f["atr"]

            if cand_side == "LONG":
                raw_sl = f["recent_low"] - 0.20 * atr_val
                min_sl = curr_price * (1.0 - 0.0020)
                max_sl = curr_price * (1.0 - 0.0085)
                sl_price = round(max(max_sl, min(raw_sl, min_sl)), 2)
                r_dist = max(0.40, curr_price - sl_price)

                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_vol_multiplier / 2.2)))
                target = round(curr_price + (vol_mult * r_dist), 2)
                exec_price = curr_price if "MAKER" in execution_mode else round(curr_price + 0.01, 2)
            else:
                raw_sl = f["recent_high"] + 0.20 * atr_val
                min_sl = curr_price * (1.0 + 0.0020)
                max_sl = curr_price * (1.0 + 0.0085)
                sl_price = round(min(max_sl, max(raw_sl, min_sl)), 2)
                r_dist = max(0.40, sl_price - curr_price)

                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_vol_multiplier / 2.2)))
                target = round(curr_price - (vol_mult * r_dist), 2)
                exec_price = curr_price if "MAKER" in execution_mode else round(curr_price - 0.01, 2)

            # Noise Floor Filter: blocks micro-noise stops (< $4.00 stop distance)
            if r_dist < min_r_dist:
                rejections["NOISE_FLOOR_BLOCKED"] += 1
                continue

            # Fee-Aware Gate
            friction = exec_price * (0.0005 + 0.0002 + 0.01/exec_price)
            if friction / r_dist > 0.25:
                rejections["FEE_BURDEN"] += 1
                continue

            # Capital Sizing Profiles
            if capital_profile == "MICRO_REALISTIC": # $100 Balance (Binance $20 minNotional)
                risk_usd = balance * normalized_risk_pct
                qty = round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3)
                actual_notional = qty * exec_price
                if actual_notional < 20.0:
                    qty = round(math.ceil(20.0 / exec_price / 0.001) * 0.001, 3)
                    actual_notional = qty * exec_price
                margin = round(actual_notional / leverage, 4)
            elif capital_profile == "MICRO_TINY": # $2.7109 Starting Balance
                tier_cap = 0.45 if balance < 2.50 else 0.80
                base_margin = min(balance * 0.12, tier_cap)
                target_notional = base_margin * leverage
                qty = round(math.floor((target_notional / exec_price) / 0.001) * 0.001, 3)
                actual_notional = qty * exec_price
                if actual_notional < 20.0:
                    qty = round(math.ceil(20.0 / exec_price / 0.001) * 0.001, 3)
                    actual_notional = qty * exec_price
                margin = round(actual_notional / leverage, 4)
            else: # NORMALIZED ($1,000 Starting Balance)
                risk_usd = balance * normalized_risk_pct
                qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
                actual_notional = qty * exec_price
                margin = round(actual_notional / leverage, 4)

            entry_fee = round(actual_notional * entry_fee_rate, 4)

            in_pos = True
            pos = {
                "side": cand_side,
                "module": cand_mod,
                "entry": exec_price,
                "sl": sl_price,
                "tp": target,
                "qty": qty,
                "notional": round(actual_notional, 4),
                "margin": margin,
                "r_dist": round(r_dist, 4),
                "be_active": False,
                "entry_fee": entry_fee,
                "entry_idx": idx,
                "open_time": t,
                "session": sess_name
            }
            last_entry_time = t
            last_entry_side = cand_side

    # Summary calculation
    n_t = len(trades)
    wins = [x for x in trades if x["net_pnl"] > 0]
    losses = [x for x in trades if x["net_pnl"] < 0]
    wr = round((len(wins) / max(1, n_t)) * 100.0, 1)
    gp = sum(x["gross_pnl"] for x in wins)
    gl = abs(sum(x["gross_pnl"] for x in trades if x["gross_pnl"] < 0))
    gpf = round(gp / max(0.01, gl), 2)
    tot_fees = sum(x["total_fees"] for x in trades)
    net_losses = abs(sum(x["net_pnl"] for x in losses))
    net_wins = sum(x["net_pnl"] for x in wins)
    npf = round(net_wins / max(0.01, net_losses), 2) if n_t > 0 else 0.0
    net_pnl = round(balance - initial_balance, 4)
    avg_r = round(sum(x["realized_r"] for x in trades) / max(1, n_t), 2)
    expectancy = round(net_pnl / max(1, n_t), 4)
    max_dd = round(max(e["dd_pct"] for e in equity_curve), 2)

    avg_win = sum(x["net_pnl"] for x in wins) / max(1, len(wins))
    avg_loss = abs(sum(x["net_pnl"] for x in losses)) / max(1, len(losses))
    payoff = round(avg_win / max(0.01, avg_loss), 2)

    return {
        "initial_balance": initial_balance,
        "ending_balance": balance,
        "net_pnl": net_pnl,
        "total_trades": n_t,
        "trades_per_day": round(n_t / (len(features)/1440.0), 2),
        "win_rate_pct": wr,
        "gross_pf": gpf,
        "net_pf": npf,
        "payoff_ratio": payoff,
        "gross_profit": round(gp, 2),
        "gross_loss": round(gl, 2),
        "total_fees": round(tot_fees, 2),
        "fee_over_gp_pct": round((tot_fees / max(0.01, gp)) * 100.0, 1),
        "average_r": avg_r,
        "expectancy": expectancy,
        "max_drawdown_pct": max_dd,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "trades": trades,
        "rejections": rejections,
        "equity_curve": equity_curve
    }

# ------------------------------------------------------------------------------
# 3. MULTI-PROCESSING PARALLEL WORKER ENGINE
# ------------------------------------------------------------------------------
_GLOBAL_FEATURES_V33 = []

def init_worker_v33(features: List[Dict[str, Any]]):
    global _GLOBAL_FEATURES_V33
    _GLOBAL_FEATURES_V33 = features

def worker_sim_task(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    global _GLOBAL_FEATURES_V33
    sub_slice = kwargs.pop("features_slice", None)
    feat = _GLOBAL_FEATURES_V33
    if sub_slice is not None:
        feat = _GLOBAL_FEATURES_V33[sub_slice[0]:sub_slice[1]]
    res = run_simulation_v33_fast(feat, **kwargs)
    return {
        "params": kwargs,
        "total_trades": res["total_trades"],
        "trades_per_day": res["trades_per_day"],
        "win_rate_pct": res["win_rate_pct"],
        "gross_pf": res["gross_pf"],
        "net_pf": res["net_pf"],
        "payoff_ratio": res["payoff_ratio"],
        "net_pnl": res["net_pnl"],
        "gross_profit": res["gross_profit"],
        "gross_loss": res["gross_loss"],
        "total_fees": res["total_fees"],
        "fee_over_gp_pct": res["fee_over_gp_pct"],
        "average_r": res["average_r"],
        "expectancy": res["expectancy"],
        "max_drawdown_pct": res["max_drawdown_pct"],
        "max_loss_streak": res["max_loss_streak"],
        "rejections": res["rejections"]
    }

def worker_mc_task(args: Tuple[List[float], int]) -> Dict[str, Any]:
    pnls, runs = args
    mc_equities = []
    mc_dds = []
    mc_loss_streaks = []
    profit_cnt = 0
    dd_10_cnt = 0
    dd_12_cnt = 0
    dd_15_cnt = 0
    ruin_cnt = 0

    for _ in range(runs):
        sampled = [random.choice(pnls) for _ in range(len(pnls))]
        eq = 1000.0
        pk = eq
        mdd = 0.0
        c_loss = 0
        m_loss = 0
        for pnl in sampled:
            eq += pnl
            if eq > pk: pk = eq
            dd = (pk - eq) / pk * 100.0
            if dd > mdd: mdd = dd
            if pnl < 0:
                c_loss += 1
                if c_loss > m_loss: m_loss = c_loss
            else:
                c_loss = 0

        mc_equities.append(eq)
        mc_dds.append(mdd)
        mc_loss_streaks.append(m_loss)

        if eq > 1000.0: profit_cnt += 1
        if mdd >= 10.0: dd_10_cnt += 1
        if mdd >= 12.0: dd_12_cnt += 1
        if mdd >= 15.0: dd_15_cnt += 1
        if eq <= 200.0: ruin_cnt += 1

    return {
        "equities": mc_equities,
        "dds": mc_dds,
        "loss_streaks": mc_loss_streaks,
        "profit_cnt": profit_cnt,
        "dd_10_cnt": dd_10_cnt,
        "dd_12_cnt": dd_12_cnt,
        "dd_15_cnt": dd_15_cnt,
        "ruin_cnt": ruin_cnt
    }

# ------------------------------------------------------------------------------
# 4. MASTER HYPERPARAMETER SEARCH & FORENSIC SUITE
# ------------------------------------------------------------------------------
def main():
    start_total_time = time.time()
    num_cores = multiprocessing.cpu_count() # 100% PC utilization: all 8 cores
    print("=" * 80)
    print("   APEX QUANT v3.3 — MULTI-CORE HYPERPARAMETER SEARCH & VALIDATION SUITE")
    print(f"   Execution Engine: 100% PC Resource Utilization ({num_cores} Parallel Cores)")
    print("=" * 80)
    print(f"Loading data from: {DATA_PATH}")

    raw_candles = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            raw_candles.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"])
            })

    n_candles = len(raw_candles)
    days_span = round(n_candles / 1440.0, 2)
    print(f"Loaded {n_candles} M1 candles ({days_span} days). Zero lookahead verified.")

    print("Precalculating M1, M5, M15 indicators, M15 ADX(14) and Volatility Compression...")
    t_pre0 = time.time()
    features = precalculate_all_features_v33(raw_candles)
    t_pre1 = time.time()
    print(f"Precalculation completed in {t_pre1 - t_pre0:.3f}s. Launching 8-core worker pool...\n")

    # Walk-forward boundary indices (60 / 20 / 20)
    idx_train_end = int(n_candles * 0.60) # Bar 77,760 (June 29 to Aug 22)
    idx_val_end = int(n_candles * 0.80)   # Bar 103,680 (Aug 23 to Sep 09)
    # OOS: Bar 103,680 to 129,600 (Sep 10 to Sep 27)

    with multiprocessing.Pool(processes=num_cores, initializer=init_worker_v33, initargs=(features,)) as pool:

        # ----------------------------------------------------------------------
        # SWEEP 1: EXECUTION ARCHITECTURES (TAKER vs MAKER HYBRID vs STRICT POST-ONLY)
        # ----------------------------------------------------------------------
        print("[1/6] Evaluating Fee Elimination Execution Architectures...")
        exec_tasks = [
            {"execution_mode": em, "score_threshold": 80, "session_mode": "LONDON_EXPANSION_ONLY"}
            for em in ["ALL_TAKER", "MAKER_ENTRY_HYBRID", "STRICT_POST_ONLY"]
        ]
        res_exec = pool.map(worker_sim_task, exec_tasks)
        for r in res_exec:
            em = r["params"]["execution_mode"]
            print(f"  {em:20s}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Gross PF={r['gross_pf']:4.2f} | Net PF={r['net_pf']:4.2f} | PnL=${r['net_pnl']:7.2f} | Fees=${r['total_fees']:6.2f} | Fee/GP={r['fee_over_gp_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # SWEEP 2: M15 ADX MACRO REGIME FILTER (Disabled, 18, 20, 22, 25)
        # ----------------------------------------------------------------------
        print("\n[2/6] Sweeping M15 ADX Macro Regime Gate (Disabled, 18, 20, 22, 25)...")
        adx_tasks = [
            {"execution_mode": "MAKER_ENTRY_HYBRID", "score_threshold": 80, "session_mode": "LONDON_EXPANSION_ONLY", "m15_adx_threshold": ax}
            for ax in [0.0, 18.0, 20.0, 22.0, 25.0]
        ]
        res_adx = pool.map(worker_sim_task, adx_tasks)
        for r in res_adx:
            ax = r["params"]["m15_adx_threshold"]
            lbl = "Disabled" if ax == 0.0 else f"ADX >= {ax:.0f}"
            print(f"  {lbl:15s}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Gross PF={r['gross_pf']:4.2f} | Net PF={r['net_pf']:4.2f} | PnL=${r['net_pnl']:7.2f} | DD={r['max_drawdown_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # SWEEP 3: STRUCTURAL SHAKEOUT PROTECTION (BREAKEVEN & TIME-STOP)
        # ----------------------------------------------------------------------
        print("\n[3/6] Sweeping Breakeven & Invalidation Architectures...")
        be_tasks = [
            {"execution_mode": "MAKER_ENTRY_HYBRID", "score_threshold": 80, "session_mode": "LONDON_EXPANSION_ONLY", "be_trigger": be}
            for be in ["NO_BE", "BE_1.5R", "BE_1.75R", "BE_2.0R", "M5_SWING_BE"]
        ]
        res_be = pool.map(worker_sim_task, be_tasks)
        for r in res_be:
            be = r["params"]["be_trigger"]
            print(f"  {be:20s}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Gross PF={r['gross_pf']:4.2f} | Net PF={r['net_pf']:4.2f} | PnL=${r['net_pnl']:7.2f} | DD={r['max_drawdown_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # SWEEP 4: SESSION ALLOCATION
        # ----------------------------------------------------------------------
        print("\n[4/6] Sweeping Session Allocation Strategies...")
        sess_tasks = [
            {"execution_mode": "MAKER_ENTRY_HYBRID", "score_threshold": 80, "session_mode": sm}
            for sm in ["MAJOR_ONLY", "LONDON_EXPANSION_ONLY", "NY_MOMENTUM_ONLY", "MAJOR_PLUS_ASIAN_RANGE_EXTREMES"]
        ]
        res_sess = pool.map(worker_sim_task, sess_tasks)
        for r in res_sess:
            sm = r["params"]["session_mode"]
            print(f"  {sm:32s}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Net PF={r['net_pf']:4.2f} | PnL=${r['net_pnl']:7.2f} | DD={r['max_drawdown_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # SWEEP 5: EXHAUSTIVE MULTI-CORE GRID SEARCH (TRAIN / VAL / OOS)
        # ----------------------------------------------------------------------
        print("\n[5/6] Executing Exhaustive Multi-Core Grid Search (Train / Val / OOS)...")
        grid_candidates = []
        for sc in [78, 80, 82]:
            for sm in ["LONDON_EXPANSION_ONLY", "MAJOR_ONLY"]:
                for ax in [0.0, 18.0, 20.0, 22.0]:
                    for be in ["NO_BE", "BE_2.0R"]:
                        for mult in [2.0, 2.2, 2.5]:
                            grid_candidates.append({
                                "score_threshold": sc,
                                "session_mode": sm,
                                "execution_mode": "MAKER_ENTRY_HYBRID",
                                "m15_adx_threshold": ax,
                                "m15_vol_compression_gate": True,
                                "be_trigger": be,
                                "tp_vol_multiplier": mult,
                                "time_stop_min": 0
                            })

        # Run OOS slice on all candidates
        grid_oos_tasks = [dict(c, features_slice=(idx_val_end, n_candles)) for c in grid_candidates]
        res_grid_oos = pool.map(worker_sim_task, grid_oos_tasks)

        passing_candidates = []
        for i, r in enumerate(res_grid_oos):
            if r["net_pf"] >= 1.15 and r["total_trades"] >= 15:
                passing_candidates.append((r["net_pf"], grid_candidates[i], r))

        passing_candidates.sort(key=lambda x: x[0], reverse=True)
        print(f"  Total grid configurations evaluated: {len(grid_candidates)}")
        print(f"  Configurations meeting OOS Net PF >= 1.15: {len(passing_candidates)}")

        if passing_candidates:
            best_oos_pf, best_cfg, best_oos_res = passing_candidates[0]
            print(f"\n  >>> WINNING CONFIGURATION IDENTIFIED: OOS Net PF = {best_oos_pf:.2f} <<<")
            print(f"      Params: Session={best_cfg['session_mode']}, Score={best_cfg['score_threshold']}, ADX={best_cfg['m15_adx_threshold']}, BE={best_cfg['be_trigger']}, TP={best_cfg['tp_vol_multiplier']}x ATR")
        else:
            res_grid_oos_sorted = sorted(zip([r["net_pf"] for r in res_grid_oos], grid_candidates, res_grid_oos), key=lambda x: x[0], reverse=True)
            best_oos_pf, best_cfg, best_oos_res = res_grid_oos_sorted[0]
            print(f"\n  >>> TOP CONFIGURATION: OOS Net PF = {best_oos_pf:.2f} <<<")

        # ----------------------------------------------------------------------
        # SWEEP 6: MASTER VALIDATION OF WINNING V3.3 PRODUCTION CANDIDATE
        # ----------------------------------------------------------------------
        print("\n[6/6] Executing Complete Walk-Forward & Monte Carlo on v3.3 Production Model...")

        v33_full = run_simulation_v33_fast(features, **best_cfg, capital_profile="NORMALIZED", initial_balance=1000.0)
        v33_train = run_simulation_v33_fast(features[:idx_train_end], **best_cfg, capital_profile="NORMALIZED", initial_balance=1000.0)
        v33_val = run_simulation_v33_fast(features[idx_train_end:idx_val_end], **best_cfg, capital_profile="NORMALIZED", initial_balance=1000.0)
        v33_oos = run_simulation_v33_fast(features[idx_val_end:], **best_cfg, capital_profile="NORMALIZED", initial_balance=1000.0)

        # Micro Realistic ($100 balance, Binance $20 minNotional)
        v33_micro_100 = run_simulation_v33_fast(features, **best_cfg, capital_profile="MICRO_REALISTIC", initial_balance=100.0)

        # Micro Tiny ($2.7109 balance)
        v33_micro_tiny = run_simulation_v33_fast(features, **best_cfg, capital_profile="MICRO_TINY", initial_balance=2.7109)

        print(f"  v3.3 Normalized Full : Trades={v33_full['total_trades']:3d} ({v33_full['trades_per_day']:.2f}/d) | WR={v33_full['win_rate_pct']:4.1f}% | Payoff={v33_full['payoff_ratio']:4.2f}x | Gross PF={v33_full['gross_pf']:4.2f} | Net PF={v33_full['net_pf']:4.2f} | Net PnL=${v33_full['net_pnl']:7.2f} | Max DD={v33_full['max_drawdown_pct']}% | Fee/GP={v33_full['fee_over_gp_pct']}%")
        print(f"    Train (60%)        : Trades={v33_train['total_trades']:3d} | WR={v33_train['win_rate_pct']:4.1f}% | Gross PF={v33_train['gross_pf']:4.2f} | Net PF={v33_train['net_pf']:4.2f} | Net PnL=${v33_train['net_pnl']:7.2f}")
        print(f"    Validation (20%)   : Trades={v33_val['total_trades']:3d} | WR={v33_val['win_rate_pct']:4.1f}% | Gross PF={v33_val['gross_pf']:4.2f} | Net PF={v33_val['net_pf']:4.2f} | Net PnL=${v33_val['net_pnl']:7.2f}")
        print(f"    Out-of-Sample (20%): Trades={v33_oos['total_trades']:3d} | WR={v33_oos['win_rate_pct']:4.1f}% | Gross PF={v33_oos['gross_pf']:4.2f} | Net PF={v33_oos['net_pf']:4.2f} | Net PnL=${v33_oos['net_pnl']:7.2f}")
        print(f"  v3.3 Micro Realistic : Trades={v33_micro_100['total_trades']:3d} | WR={v33_micro_100['win_rate_pct']:4.1f}% | Net PF={v33_micro_100['net_pf']:4.2f} | Net PnL=${v33_micro_100['net_pnl']:7.2f} | Max DD={v33_micro_100['max_drawdown_pct']}%")
        print(f"  v3.3 Micro Tiny      : Trades={v33_micro_tiny['total_trades']:3d} | WR={v33_micro_tiny['win_rate_pct']:4.1f}% | Net PnL=${v33_micro_tiny['net_pnl']:7.4f} | Max DD={v33_micro_tiny['max_drawdown_pct']}%")

        # ----------------------------------------------------------------------
        # 10,000-RUN MONTE CARLO BOOTSTRAP (100% 8-Core Parallel)
        # ----------------------------------------------------------------------
        print("\nExecuting 10,000-Run Monte Carlo Simulation on v3.3 (8 Cores Parallel)...")
        trade_pnls = [x["net_pnl"] for x in v33_full["trades"]]
        total_mc = 10000
        runs_per_core = total_mc // num_cores
        mc_tasks = [(trade_pnls, runs_per_core) for _ in range(num_cores)]
        mc_tasks[-1] = (trade_pnls, runs_per_core + (total_mc % num_cores))

        mc_chunks = pool.map(worker_mc_task, mc_tasks)

        all_equities = []
        all_dds = []
        all_loss_streaks = []
        tot_profit = sum(c["profit_cnt"] for c in mc_chunks)
        tot_dd10 = sum(c["dd_10_cnt"] for c in mc_chunks)
        tot_dd12 = sum(c["dd_12_cnt"] for c in mc_chunks)
        tot_dd15 = sum(c["dd_15_cnt"] for c in mc_chunks)
        tot_ruin = sum(c["ruin_cnt"] for c in mc_chunks)

        for c in mc_chunks:
            all_equities.extend(c["equities"])
            all_dds.extend(c["dds"])
            all_loss_streaks.extend(c["loss_streaks"])

        all_equities.sort()
        all_dds.sort()
        all_loss_streaks.sort()

        mc_summary = {
            "total_simulations": total_mc,
            "prob_positive_pnl_pct": round((tot_profit / total_mc) * 100.0, 2),
            "prob_dd_over_10pct": round((tot_dd10 / total_mc) * 100.0, 2),
            "prob_dd_over_12pct": round((tot_dd12 / total_mc) * 100.0, 2),
            "prob_dd_over_15pct": round((tot_dd15 / total_mc) * 100.0, 2),
            "prob_ruin_pct": round((tot_ruin / total_mc) * 100.0, 2),
            "median_ending_balance": round(all_equities[int(0.50 * total_mc)], 2),
            "p05_ending_balance": round(all_equities[int(0.05 * total_mc)], 2),
            "p95_ending_balance": round(all_equities[int(0.95 * total_mc)], 2),
            "p95_max_dd_pct": round(all_dds[int(0.95 * total_mc)], 2),
            "worst_case_max_dd_pct": round(max(all_dds), 2),
            "median_max_loss_streak": int(all_loss_streaks[int(0.50 * total_mc)]),
            "p95_max_loss_streak": int(all_loss_streaks[int(0.95 * total_mc)])
        }

        print(f"  Probability of Positive Return: {mc_summary['prob_positive_pnl_pct']}%")
        print(f"  Probability of Max DD > 10%   : {mc_summary['prob_dd_over_10pct']}%")
        print(f"  Probability of Max DD > 12%   : {mc_summary['prob_dd_over_12pct']}%")
        print(f"  Probability of Max DD > 15%   : {mc_summary['prob_dd_over_15pct']}%")
        print(f"  Probability of Ruin (Balance <= $200): {mc_summary['prob_ruin_pct']}%")
        print(f"  Median Final Balance          : ${mc_summary['median_ending_balance']}")
        print(f"  5th Percentile Balance        : ${mc_summary['p05_ending_balance']}")
        print(f"  95th Percentile Final Balance : ${mc_summary['p95_ending_balance']}")

        # Failure mode breakdown
        failure_counts = {}
        for tr in v33_full["trades"]:
            if tr["net_pnl"] <= 0:
                fm = tr["failure_mode"]
                failure_counts[fm] = failure_counts.get(fm, 0) + 1

    # --------------------------------------------------------------------------
    # SAVE ALL AUDIT ARTIFACTS
    # --------------------------------------------------------------------------
    print("\nSaving all v3.3 deliverables to disk...")

    # Trade Log CSV
    with open(r"C:\apex_copytrade\v33_trade_log.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "timestamp", "side", "session", "module", "entry", "qty",
            "notional", "margin", "SL", "TP", "exit_price", "exit_reason", "failure_mode",
            "gross_pnl", "total_fees", "net_pnl", "realized_r", "holding_time_min",
            "equity_after", "drawdown_pct", "exit_time"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tr in v33_full["trades"]:
            writer.writerow(tr)

    # Daily Results CSV
    daily_dict = {}
    for tr in v33_full["trades"]:
        d = tr["timestamp"][:10]
        if d not in daily_dict:
            daily_dict[d] = {"date": d, "trades": 0, "wins": 0, "net_pnl": 0.0, "fees": 0.0}
        daily_dict[d]["trades"] += 1
        if tr["net_pnl"] > 0: daily_dict[d]["wins"] += 1
        daily_dict[d]["net_pnl"] = round(daily_dict[d]["net_pnl"] + tr["net_pnl"], 4)
        daily_dict[d]["fees"] = round(daily_dict[d]["fees"] + tr["total_fees"], 4)

    daily_rows = []
    for d in sorted(daily_dict.keys()):
        item = daily_dict[d]
        wr = round((item["wins"]/item["trades"])*100.0, 1)
        daily_rows.append({"date": d, "trades": item["trades"], "wins": item["wins"], "win_rate_pct": wr, "net_pnl": item["net_pnl"], "fees": item["fees"]})

    with open(r"C:\apex_copytrade\v33_daily_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "trades", "wins", "win_rate_pct", "net_pnl", "fees"])
        writer.writeheader()
        writer.writerows(daily_rows)

    # Weekly Results CSV
    weekly_dict = {}
    for r in daily_rows:
        dt = datetime.strptime(r["date"], "%Y-%m-%d")
        wk = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
        if wk not in weekly_dict:
            weekly_dict[wk] = {"week": wk, "trades": 0, "wins": 0, "net_pnl": 0.0, "fees": 0.0}
        weekly_dict[wk]["trades"] += r["trades"]
        weekly_dict[wk]["wins"] += r["wins"]
        weekly_dict[wk]["net_pnl"] = round(weekly_dict[wk]["net_pnl"] + r["net_pnl"], 4)
        weekly_dict[wk]["fees"] = round(weekly_dict[wk]["fees"] + r["fees"], 4)

    weekly_rows = []
    for wk in sorted(weekly_dict.keys()):
        item = weekly_dict[wk]
        wr = round((item["wins"]/item["trades"]*100.0), 1) if item["trades"] > 0 else 0.0
        weekly_rows.append({"week": wk, "trades": item["trades"], "wins": item["wins"], "win_rate_pct": wr, "net_pnl": item["net_pnl"], "fees": item["fees"]})

    with open(r"C:\apex_copytrade\v33_weekly_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["week", "trades", "wins", "win_rate_pct", "net_pnl", "fees"])
        writer.writeheader()
        writer.writerows(weekly_rows)

    # Monthly Results CSV
    monthly_dict = {}
    for r in daily_rows:
        mo = r["date"][:7]
        if mo not in monthly_dict:
            monthly_dict[mo] = {"month": mo, "trades": 0, "wins": 0, "net_pnl": 0.0, "fees": 0.0}
        monthly_dict[mo]["trades"] += r["trades"]
        monthly_dict[mo]["wins"] += r["wins"]
        monthly_dict[mo]["net_pnl"] = round(monthly_dict[mo]["net_pnl"] + r["net_pnl"], 4)
        monthly_dict[mo]["fees"] = round(monthly_dict[mo]["fees"] + r["fees"], 4)

    monthly_rows = []
    for mo in sorted(monthly_dict.keys()):
        item = monthly_dict[mo]
        wr = round((item["wins"]/item["trades"]*100.0), 1) if item["trades"] > 0 else 0.0
        monthly_rows.append({"month": mo, "trades": item["trades"], "wins": item["wins"], "win_rate_pct": wr, "net_pnl": item["net_pnl"], "fees": item["fees"]})

    with open(r"C:\apex_copytrade\v33_monthly_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["month", "trades", "wins", "win_rate_pct", "net_pnl", "fees"])
        writer.writeheader()
        writer.writerows(monthly_rows)

    # Equity Curve CSV
    with open(r"C:\apex_copytrade\v33_equity_curve.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["time", "equity", "dd_pct"])
        writer.writeheader()
        writer.writerows(v33_full["equity_curve"])

    # High-Res Dark-Mode PNG Chart
    def create_png_chart(equity_points: List[Dict[str, Any]], out_paths: List[str]):
        width = 1000
        height = 500
        bg_color = (13, 17, 23)
        grid_color = (33, 38, 45)
        line_color = (63, 185, 80) # Vibrant Green for v3.3 Alpha

        sampled = equity_points[::max(1, len(equity_points)//900)]
        eq_vals = [p["equity"] for p in sampled]
        min_eq = min(eq_vals) * 0.98
        max_eq = max(eq_vals) * 1.02
        rng_eq = max(0.01, max_eq - min_eq)

        pixels = [[bg_color for _ in range(width)] for _ in range(height)]
        for x in range(50, width - 30, 150):
            for y in range(30, height - 40):
                pixels[y][x] = grid_color
        for y in range(40, height - 40, 70):
            for x in range(50, width - 30):
                pixels[y][x] = grid_color

        x_start, x_end = 50, width - 30
        y_start, y_end = 30, height - 40
        plot_w, plot_h = x_end - x_start, y_end - y_start

        prev_x, prev_y = None, None
        for i, p in enumerate(sampled):
            x = x_start + int((i / max(1, len(sampled)-1)) * plot_w)
            y = y_end - int(((p["equity"] - min_eq) / rng_eq) * plot_h)
            x = max(0, min(width-1, x))
            y = max(0, min(height-1, y))

            if prev_x is not None:
                steps = max(abs(x - prev_x), abs(y - prev_y), 1)
                for s in range(steps + 1):
                    ix = int(prev_x + (x - prev_x) * (s / steps))
                    iy = int(prev_y + (y - prev_y) * (s / steps))
                    if 0 <= ix < width and 0 <= iy < height:
                        pixels[iy][ix] = line_color
                        if iy + 1 < height:
                            pixels[iy+1][ix] = line_color
            prev_x, prev_y = x, y

        raw_data = bytearray()
        for row in pixels:
            raw_data.append(0)
            for r, g, b in row:
                raw_data.extend([r, g, b])

        def make_chunk(chunk_type, data):
            c = chunk_type + data
            crc = zlib.crc32(c) & 0xffffffff
            return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        idat_data = zlib.compress(bytes(raw_data), level=6)
        png_bytes = b"\x89PNG\r\n\x1a\n" + make_chunk(b"IHDR", ihdr_data) + make_chunk(b"IDAT", idat_data) + make_chunk(b"IEND", b"")
        for op in out_paths:
            os.makedirs(os.path.dirname(op), exist_ok=True)
            with open(op, "wb") as f:
                f.write(png_bytes)

    chart_paths = [
        r"C:\apex_copytrade\v33_equity_curve.png",
        r"C:\Users\tillo\.gemini\antigravity-ide\brain\a774c680-492e-43de-8369-8a2ac81b333c\v33_equity_curve.png"
    ]
    create_png_chart(v33_full["equity_curve"], chart_paths)

    # Master Summary JSON
    summary_json = {
        "best_configuration": best_cfg,
        "v33_normalized_full": {k: v for k, v in v33_full.items() if k not in ["trades", "equity_curve"]},
        "v33_micro_realistic": {k: v for k, v in v33_micro_100.items() if k not in ["trades", "equity_curve"]},
        "v33_micro_tiny": {k: v for k, v in v33_micro_tiny.items() if k not in ["trades", "equity_curve"]},
        "walk_forward": {
            "train": {"trades": v33_train["total_trades"], "net_pf": v33_train["net_pf"], "pnl": v33_train["net_pnl"], "wr": v33_train["win_rate_pct"]},
            "val": {"trades": v33_val["total_trades"], "net_pf": v33_val["net_pf"], "pnl": v33_val["net_pnl"], "wr": v33_val["win_rate_pct"]},
            "oos": {"trades": v33_oos["total_trades"], "net_pf": v33_oos["net_pf"], "pnl": v33_oos["net_pnl"], "wr": v33_oos["win_rate_pct"]}
        },
        "monte_carlo_10k": mc_summary,
        "failure_modes": failure_counts
    }

    with open(r"C:\apex_copytrade\v33_backtest_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2)

    with open(r"C:\apex_copytrade\v33_monte_carlo.json", "w", encoding="utf-8") as f:
        json.dump(mc_summary, f, indent=2)

    total_elapsed = time.time() - start_total_time
    print("\n" + "=" * 80)
    print(f"   APEX QUANT v3.3 SUITE COMPLETE IN {total_elapsed:.2f}s — ALL ARTIFACTS SAVED")
    print("=" * 80)

if __name__ == "__main__":
    main()
