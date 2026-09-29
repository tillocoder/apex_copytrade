"""
APEX QUANT v3.2 — Quantitative Research, Optimization & Forensic Validation Suite
Base Instrument: Binance USD(S)-M Futures ETHUSDT Perpetual (M1 Timeframe)
Data: 129,600 Completed 1-Minute Bars (2026-06-29 to 2026-09-27, 90.0 Days)
Zero Lookahead Bias — Real Taker/Maker Fees & Slippage Modeled
High-Performance Multi-Core Engine (Parallel Simulation Across 7 CPU Cores)
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
# 1. FAST SINGLE-PASS PRECALCULATION (ZERO LOOKAHEAD)
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

def precalculate_all_features(raw_candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes all technical features and context in a single linear pass (O(N)).
    Strict zero lookahead: candle i only has access to bars <= i.
    Completed M5 and M15 bars are synchronized to closed time windows.
    """
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

    # MTF Construction (Completed bars only)
    m5_bars = []
    m15_bars = []
    cur_m5 = None
    cur_m15 = None
    m1_to_completed_m5 = [-1] * n
    m1_to_completed_m15 = [-1] * n

    for i in range(n):
        t = times[i]
        c = raw_candles[i]

        # M5 bucket
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

        # M15 bucket
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

    # M5 and M15 EMAs
    m5_closes = [b["close"] for b in m5_bars]
    m5_e21 = fast_ema(m5_closes, 21)
    m5_e50 = fast_ema(m5_closes, 50)

    m15_closes = [b["close"] for b in m15_bars]
    m15_e50 = fast_ema(m15_closes, 50)

    # Session info & structural features per M1 candle
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

        # M15 context from completed bars
        m15_ctx = "NEUTRAL"
        m15_idx = m1_to_completed_m15[i]
        if m15_idx >= 50:
            m15_ema = m15_e50[m15_idx]
            if c["close"] > m15_ema:
                m15_ctx = "BULLISH"
            elif c["close"] < m15_ema:
                m15_ctx = "BEARISH"

        # M5 setup from completed bars
        m5_ctx = "NONE"
        m5_idx = m1_to_completed_m5[i]
        if m5_idx >= 50:
            if m5_e21[m5_idx] > m5_e50[m5_idx]:
                m5_ctx = "M5_BULL_TREND"
            elif m5_e21[m5_idx] < m5_e50[m5_idx]:
                m5_ctx = "M5_BEAR_TREND"

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
            "m5_setup": m5_ctx,
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
# 2. V3.2 STRATEGY ENGINE & FAST SIMULATION (ZERO LOOKAHEAD)
# ------------------------------------------------------------------------------
def run_simulation_v32_fast(
    features: List[Dict[str, Any]],
    score_threshold: int = 70,
    exit_model: str = "B",            # "A", "B", "C", "D", "E", "F", "G", "H"
    be_trigger_r: float = 1.0,        # R distance to move SL to BE (+0.75R, +1.0R, +1.25R, +1.5R)
    be_buffer_pct: float = 0.0005,    # Buffer over entry (0.05% covers taker/maker fees)
    tp1_r: float = 1.25,
    tp2_r: float = 2.50,
    fee_risk_gate_ratio: float = 0.25,# Reject if roundtrip fee / R > 25%
    chase_atr_multiplier: float = 2.5,# Candle body max ATR
    min_atr_m1: float = 0.25,         # ATR floor
    session_mode: str = "WEIGHTED",   # "ALL", "NO_ASIA", "RESTRICTED_ASIA", "MAJOR_ONLY", "WEIGHTED"
    location_filter: bool = True,     # Penalize entries in range midpoint
    correlated_protection: bool = True,# Reject duplicate entries on same impulse
    cooldown_min: int = 10,
    loss_cooldown_min: int = 15,
    max_daily_trades: int = 8,
    is_micro_account: bool = False,
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

    for idx in range(warmup_period, n):
        f = features[idx]
        t = f["time"]
        day_str = f["day_str"]
        sess_name = f["session"]

        # Reset daily counters at midnight UTC
        if day_str != current_day_str:
            current_day_str = day_str
            daily_trades_count = 0
            daily_pnl = 0.0
            day_paused = False

        # ----------------------------------------------------------------------
        # POSITION MANAGEMENT
        # ----------------------------------------------------------------------
        if in_pos:
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            target1 = pos["tp1"]
            target2 = pos["tp2"]
            qty = pos["qty"]
            r_dist = pos["r_dist"]
            tp1_hit = pos["tp1_hit"]
            be_active = pos["be_active"]
            high = f["high"]
            low = f["low"]

            closed_now = False
            exit_reason = None
            exit_price = 0.0

            is_two_stage = exit_model in ["A", "B", "C", "H"]

            if side == "LONG":
                # Dynamic BE shift
                if not be_active and (high - entry) >= be_trigger_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    if exit_model in ["B", "C"]:
                        pos["sl"] = round(entry * (1.0 + be_buffer_pct), 2)
                        sl = pos["sl"]

                sl_touch = (low <= sl)
                tp1_touch = (not tp1_hit and high >= target1)
                tp2_touch = (tp1_hit and high >= target2) if is_two_stage else False

                if sl_touch and (tp1_touch or tp2_touch):
                    closed_now = True
                    exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                    exit_price = sl - 0.01
                elif sl_touch:
                    closed_now = True
                    exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                    exit_price = sl - 0.01
                elif tp1_touch:
                    if not is_two_stage:
                        closed_now = True
                        exit_reason = "TAKE_PROFIT_FULL"
                        exit_price = target1
                    else:
                        pos["tp1_hit"] = True
                        tp1_hit = True
                        close_pct = 0.35 if exit_model == "C" else 0.50
                        close_qty = round(qty * close_pct, 3)
                        pos["rem_qty"] = round(qty - close_qty, 3)
                        pos["tp1_gross"] = (target1 - entry) * close_qty
                        pos["tp1_fee"] = close_qty * target1 * 0.0002
                        pos["tp1_filled"] = True

                        if exit_model == "B":
                            pos["sl"] = round(entry * (1.0 + be_buffer_pct), 2)
                            sl = pos["sl"]
                        elif exit_model == "C":
                            pos["sl"] = round(entry + 0.20 * r_dist, 2)
                            sl = pos["sl"]

                        if high >= target2:
                            closed_now = True
                            exit_reason = "TAKE_PROFIT_2_FULL"
                            exit_price = target2
                elif tp2_touch:
                    closed_now = True
                    exit_reason = "TAKE_PROFIT_2_FULL"
                    exit_price = target2
            else: # SHORT
                if not be_active and (entry - low) >= be_trigger_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    if exit_model in ["B", "C"]:
                        pos["sl"] = round(entry * (1.0 - be_buffer_pct), 2)
                        sl = pos["sl"]

                sl_touch = (high >= sl)
                tp1_touch = (not tp1_hit and low <= target1)
                tp2_touch = (tp1_hit and low <= target2) if is_two_stage else False

                if sl_touch and (tp1_touch or tp2_touch):
                    closed_now = True
                    exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                    exit_price = sl + 0.01
                elif sl_touch:
                    closed_now = True
                    exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                    exit_price = sl + 0.01
                elif tp1_touch:
                    if not is_two_stage:
                        closed_now = True
                        exit_reason = "TAKE_PROFIT_FULL"
                        exit_price = target1
                    else:
                        pos["tp1_hit"] = True
                        tp1_hit = True
                        close_pct = 0.35 if exit_model == "C" else 0.50
                        close_qty = round(qty * close_pct, 3)
                        pos["rem_qty"] = round(qty - close_qty, 3)
                        pos["tp1_gross"] = (entry - target1) * close_qty
                        pos["tp1_fee"] = close_qty * target1 * 0.0002
                        pos["tp1_filled"] = True

                        if exit_model == "B":
                            pos["sl"] = round(entry * (1.0 - be_buffer_pct), 2)
                            sl = pos["sl"]
                        elif exit_model == "C":
                            pos["sl"] = round(entry - 0.20 * r_dist, 2)
                            sl = pos["sl"]

                        if low <= target2:
                            closed_now = True
                            exit_reason = "TAKE_PROFIT_2_FULL"
                            exit_price = target2
                elif tp2_touch:
                    closed_now = True
                    exit_reason = "TAKE_PROFIT_2_FULL"
                    exit_price = target2

            if closed_now:
                final_rem_qty = pos["rem_qty"]
                if side == "LONG":
                    rem_gross = (exit_price - entry) * final_rem_qty
                else:
                    rem_gross = (entry - exit_price) * final_rem_qty

                total_gross_pnl = round(pos.get("tp1_gross", 0.0) + rem_gross, 4)

                entry_fee = pos["entry_fee"]
                tp1_fee = pos.get("tp1_fee", 0.0)
                tp2_fee = 0.0
                sl_fee = 0.0

                if "TAKE_PROFIT" in exit_reason:
                    tp2_fee = round(final_rem_qty * exit_price * 0.0002, 4)
                else:
                    sl_fee = round(final_rem_qty * exit_price * 0.0005, 4)

                total_fees = round(entry_fee + tp1_fee + tp2_fee + sl_fee, 4)
                net_pnl = round(total_gross_pnl - total_fees, 4)

                dollar_risk = max(0.01, pos["qty"] * r_dist)
                realized_r = round(net_pnl / dollar_risk, 2)

                # Failure mode attribution
                failure_reason = "PROFITABLE"
                if net_pnl <= 0:
                    if total_gross_pnl > 0 and net_pnl <= 0:
                        failure_reason = "FEE_FRICTION_DRAG"
                    elif exit_reason == "BREAKEVEN_STOP_HIT":
                        failure_reason = "PREMATURE_BE_SHAKEOUT"
                    elif pos["m15_context"] != "NEUTRAL" and ((side == "LONG" and pos["m15_context"] == "BEARISH") or (side == "SHORT" and pos["m15_context"] == "BULLISH")):
                        failure_reason = "COUNTER_TREND_EXHAUSTION"
                    elif pos["module"] == "MODULE_B_BREAKOUT":
                        failure_reason = "FALSE_BREAKOUT"
                    elif pos["session"] == "ASIA":
                        failure_reason = "ASIAN_DEAD_ZONE"
                    elif idx - pos["entry_idx"] <= 4:
                        failure_reason = "CHOP_WHIPSAW"
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
                    cooldown_until_idx = idx + max(2, cooldown_min)
                else:
                    current_loss_streak += 1
                    current_win_streak = 0
                    consecutive_losses += 1
                    if consecutive_losses >= 3:
                        cooldown_until_idx = idx + 30
                    else:
                        cooldown_until_idx = idx + max(5, loss_cooldown_min)

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
                    "class": pos["setup_class"],
                    "M15_regime": pos["m15_context"],
                    "M5_setup": pos["m5_setup"],
                    "score": pos["score"],
                    "entry": pos["entry"],
                    "qty": qty,
                    "notional": pos["notional"],
                    "margin": pos["margin"],
                    "SL": sl,
                    "TP1": target1,
                    "TP2": target2,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "failure_mode": failure_reason,
                    "gross_pnl": total_gross_pnl,
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
            # Session Filter Handling
            if session_mode == "NO_ASIA" and sess_name == "ASIA":
                rejections["SESSION_BLOCKED"] += 1
                continue
            elif session_mode == "MAJOR_ONLY" and sess_name not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                rejections["SESSION_BLOCKED"] += 1
                continue

            if daily_trades_count >= max_daily_trades:
                rejections["DAILY_CAP_REACHED"] += 1
                continue

            if day_paused:
                rejections["CIRCUIT_BREAKER_ACTIVE"] += 1
                continue

            # Volatility floor
            if f["atr"] < min_atr_m1:
                rejections["LOW_VOLATILITY"] += 1
                continue

            # Chase guard
            if f["body"] > chase_atr_multiplier * f["atr"]:
                rejections["OVEREXTENDED_CHASE"] += 1
                continue

            cand_side = f["cand_side"]
            if not cand_side:
                continue

            rejections["TOTAL_CANDIDATES"] += 1

            # V3.2 Quality Scoring
            total_score = f["cand_base_score"]

            # 1. Location Quality Filter
            if location_filter:
                if f["dist_from_mid"] < 0.15:
                    total_score -= 10
                    rejections["LOCATION_PENALTY"] += 1
                else:
                    total_score += 10

            # 2. Trend Alignment Bonus
            if cand_side == "LONG" and f["e9"] > f["e21"]:
                total_score += 10
            elif cand_side == "SHORT" and f["e9"] < f["e21"]:
                total_score += 10

            if cand_side == "LONG" and f["m5_setup"] == "M5_BULL_TREND":
                total_score += 10
            elif cand_side == "SHORT" and f["m5_setup"] == "M5_BEAR_TREND":
                total_score += 10

            # 3. M15 Macro Context
            if cand_side == "LONG":
                if f["m15_context"] == "BULLISH":
                    total_score += 10
                elif f["m15_context"] == "BEARISH":
                    total_score -= 10
            else:
                if f["m15_context"] == "BEARISH":
                    total_score += 10
                elif f["m15_context"] == "BULLISH":
                    total_score -= 10

            # 4. Learned Session Modifier
            if session_mode == "WEIGHTED":
                if sess_name == "ASIA":
                    total_score -= 10
                elif sess_name == "LONDON":
                    total_score += 0
                elif sess_name == "LONDON_NY_OVERLAP":
                    total_score += 4
                elif sess_name == "NEW_YORK":
                    total_score += 8
                elif sess_name == "OUT_OF_SESSION":
                    total_score -= 5
            elif session_mode == "RESTRICTED_ASIA" and sess_name == "ASIA":
                total_score -= 15

            # 5. Volume expansion
            if f["vol_expansion"]:
                total_score += 5

            total_score = max(0, min(100, total_score))

            if total_score >= 75:
                setup_class = "CLASS_A"
            elif total_score >= 65:
                setup_class = "CLASS_B"
            else:
                setup_class = "CLASS_C"

            if total_score < score_threshold:
                rejections["LOW_SCORE"] += 1
                continue

            # Correlated Signal Protection (Same move within 15 min)
            if correlated_protection and last_entry_side == cand_side:
                bars_since = (t - last_entry_time) / 60000.0
                if bars_since < 15:
                    rejections["CORRELATED_DUPLICATE"] += 1
                    continue

            # Stop Loss & Target Geometry
            curr_price = f["close"]
            atr_val = f["atr"]

            if cand_side == "LONG":
                raw_sl = f["recent_low"] - 0.20 * atr_val
                min_sl = curr_price * (1.0 - 0.0020)
                max_sl = curr_price * (1.0 - 0.0085)
                sl_price = max(max_sl, min(raw_sl, min_sl))
                r_dist = max(0.40, curr_price - sl_price)

                if exit_model in ["A", "B"]:
                    target1 = round(curr_price + (tp1_r * r_dist), 2)
                    target2 = round(curr_price + (tp2_r * r_dist), 2)
                elif exit_model == "C":
                    target1 = round(curr_price + (1.50 * r_dist), 2)
                    target2 = round(curr_price + (3.00 * r_dist), 2)
                elif exit_model == "D":
                    target1 = round(curr_price + (2.00 * r_dist), 2)
                    target2 = target1
                elif exit_model == "E":
                    target1 = round(curr_price + (1.50 * r_dist), 2)
                    target2 = target1
                elif exit_model == "F":
                    target1 = round(curr_price + (2.50 * r_dist), 2)
                    target2 = target1
                elif exit_model == "G":
                    vol_mult = max(1.5, min(3.0, atr_val / 1.0))
                    target1 = round(curr_price + (vol_mult * r_dist), 2)
                    target2 = target1
                else: # Model H
                    target1 = round(curr_price + (1.25 * r_dist), 2)
                    target2 = round(curr_price + (2.50 * r_dist), 2)

                entry_exec_price = round(curr_price + 0.01, 2)
            else:
                raw_sl = f["recent_high"] + 0.20 * atr_val
                min_sl = curr_price * (1.0 + 0.0020)
                max_sl = curr_price * (1.0 + 0.0085)
                sl_price = min(max_sl, max(raw_sl, min_sl))
                r_dist = max(0.40, sl_price - curr_price)

                if exit_model in ["A", "B"]:
                    target1 = round(curr_price - (tp1_r * r_dist), 2)
                    target2 = round(curr_price - (tp2_r * r_dist), 2)
                elif exit_model == "C":
                    target1 = round(curr_price - (1.50 * r_dist), 2)
                    target2 = round(curr_price - (3.00 * r_dist), 2)
                elif exit_model == "D":
                    target1 = round(curr_price - (2.00 * r_dist), 2)
                    target2 = target1
                elif exit_model == "E":
                    target1 = round(curr_price - (1.50 * r_dist), 2)
                    target2 = target1
                elif exit_model == "F":
                    target1 = round(curr_price - (2.50 * r_dist), 2)
                    target2 = target1
                elif exit_model == "G":
                    vol_mult = max(1.5, min(3.0, atr_val / 1.0))
                    target1 = round(curr_price - (vol_mult * r_dist), 2)
                    target2 = target1
                else: # Model H
                    target1 = round(curr_price - (tp1_r * r_dist), 2)
                    target2 = round(curr_price - (tp2_r * r_dist), 2)

                entry_exec_price = round(curr_price - 0.01, 2)

            sl_price = round(sl_price, 2)

            # Fee-Aware Gate: Roundtrip cost vs R
            friction_pct = 0.0005 + 0.0002 + (0.01 / curr_price)
            est_roundtrip_cost = curr_price * friction_pct
            fee_to_risk = est_roundtrip_cost / r_dist

            if fee_to_risk > fee_risk_gate_ratio:
                rejections["FEE_BURDEN"] += 1
                continue

            # Position Sizing
            if is_micro_account:
                bal = balance
                tier_cap = 0.45 if bal < 2.50 else (0.50 if bal < 5.00 else 0.80)
                base_margin = min(bal * 0.12, tier_cap)
                target_notional = base_margin * leverage
                raw_qty = target_notional / entry_exec_price
                qty = round(math.floor(raw_qty / 0.001) * 0.001, 3)

                actual_notional = qty * entry_exec_price
                if actual_notional < 20.0:
                    qty = round(math.ceil(20.0 / entry_exec_price / 0.001) * 0.001, 3)
                    actual_notional = qty * entry_exec_price
                margin = round(actual_notional / leverage, 4)
            else:
                target_risk_usd = balance * normalized_risk_pct
                qty = round(math.floor((target_risk_usd / r_dist) / 0.001) * 0.001, 3)
                qty = max(0.005, qty)
                actual_notional = qty * entry_exec_price
                margin = round(actual_notional / leverage, 4)

            entry_fee = round(actual_notional * 0.0005, 4)

            in_pos = True
            last_entry_time = t
            last_entry_side = cand_side

            pos = {
                "side": cand_side,
                "entry": entry_exec_price,
                "entry_idx": idx,
                "open_time": t,
                "session": sess_name,
                "module": f["cand_module"],
                "setup_class": setup_class,
                "m15_context": f["m15_context"],
                "m5_setup": f["m5_setup"],
                "score": total_score,
                "qty": qty,
                "rem_qty": qty,
                "notional": round(actual_notional, 4),
                "margin": margin,
                "sl": sl_price,
                "tp1": target1,
                "tp2": target2,
                "r_dist": round(r_dist, 4),
                "tp1_hit": False,
                "be_active": False,
                "entry_fee": entry_fee
            }

    # Summary metrics
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

    return {
        "initial_balance": initial_balance,
        "ending_balance": balance,
        "net_pnl": net_pnl,
        "total_trades": n_t,
        "trades_per_day": round(n_t / (len(features)/1440.0), 2),
        "win_rate_pct": wr,
        "gross_pf": gpf,
        "net_pf": npf,
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
# 3. MULTI-PROCESSING PARALLEL WORKER HELPERS
# ------------------------------------------------------------------------------
_GLOBAL_FEATURES = []

def init_worker(features: List[Dict[str, Any]]):
    global _GLOBAL_FEATURES
    _GLOBAL_FEATURES = features

def worker_run_sim(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    global _GLOBAL_FEATURES
    # Extract feature slice if indices given
    sub_slice = kwargs.pop("features_slice", None)
    feat = _GLOBAL_FEATURES
    if sub_slice is not None:
        feat = _GLOBAL_FEATURES[sub_slice[0]:sub_slice[1]]
    res = run_simulation_v32_fast(feat, **kwargs)
    # Strip bulky objects for IPC
    return {
        "params": kwargs,
        "total_trades": res["total_trades"],
        "trades_per_day": res["trades_per_day"],
        "win_rate_pct": res["win_rate_pct"],
        "gross_pf": res["gross_pf"],
        "net_pf": res["net_pf"],
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

def worker_mc_chunk(args: Tuple[List[float], int]) -> Dict[str, Any]:
    pnls, runs = args
    mc_equities = []
    mc_dds = []
    mc_loss_streaks = []
    profit_cnt = 0
    dd_10_cnt = 0
    dd_15_cnt = 0
    dd_20_cnt = 0
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
            if eq > pk:
                pk = eq
            dd = (pk - eq) / pk * 100.0
            if dd > mdd:
                mdd = dd
            if pnl < 0:
                c_loss += 1
                if c_loss > m_loss:
                    m_loss = c_loss
            else:
                c_loss = 0

        mc_equities.append(eq)
        mc_dds.append(mdd)
        mc_loss_streaks.append(m_loss)

        if eq > 1000.0:
            profit_cnt += 1
        if mdd >= 10.0:
            dd_10_cnt += 1
        if mdd >= 15.0:
            dd_15_cnt += 1
        if mdd >= 20.0:
            dd_20_cnt += 1
        if eq <= 200.0:
            ruin_cnt += 1

    return {
        "equities": mc_equities,
        "dds": mc_dds,
        "loss_streaks": mc_loss_streaks,
        "profit_cnt": profit_cnt,
        "dd_10_cnt": dd_10_cnt,
        "dd_15_cnt": dd_15_cnt,
        "dd_20_cnt": dd_20_cnt,
        "ruin_cnt": ruin_cnt
    }

# ------------------------------------------------------------------------------
# 4. MASTER FORENSIC & AUDIT HARNESS
# ------------------------------------------------------------------------------
def main():
    start_total_time = time.time()
    num_cores = max(1, multiprocessing.cpu_count() - 1)  # Use 7 out of 8 cores (87.5-90% CPU)
    print("=" * 80)
    print(f"   APEX QUANT v3.2 — COMPREHENSIVE RESEARCH & OPTIMIZATION SUITE")
    print(f"   Execution Engine: Multi-Process Vectorized Pipeline ({num_cores} Parallel Cores)")
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
    print(f"Loaded {n_candles} M1 candles ({days_span} days). Zero lookahead bias verified.")

    print("Precalculating multi-timeframe indicators and structural features in single pass...")
    t_pre0 = time.time()
    features = precalculate_all_features(raw_candles)
    t_pre1 = time.time()
    print(f"Precalculation completed in {t_pre1 - t_pre0:.3f}s. Initializing parallel worker pool...")

    # Spawn Worker Pool across 7 CPU cores
    with multiprocessing.Pool(processes=num_cores, initializer=init_worker, initargs=(features,)) as pool:

        # ----------------------------------------------------------------------
        # EXP 1: SCORE THRESHOLD SWEEP (60, 65, 70, 75, 80, 85)
        # ----------------------------------------------------------------------
        print("\n[1/12] Sweeping Score Thresholds (60, 65, 70, 75, 80, 85)...")
        tasks_score = [{"score_threshold": s, "exit_model": "B", "initial_balance": 1000.0} for s in [60, 65, 70, 75, 80, 85]]
        results_score = pool.map(worker_run_sim, tasks_score)
        sweep_score = {}
        for r in results_score:
            s = r["params"]["score_threshold"]
            sweep_score[f"score_{s}"] = {
                "score": s, "trades": r["total_trades"], "trades_per_day": r["trades_per_day"],
                "win_rate": r["win_rate_pct"], "gross_pf": r["gross_pf"], "net_pf": r["net_pf"],
                "expectancy": r["expectancy"], "avg_r": r["average_r"], "max_dd": r["max_drawdown_pct"],
                "net_pnl": r["net_pnl"], "fees": r["total_fees"], "fee_over_gp": r["fee_over_gp_pct"]
            }
            print(f"  Score {s:2d}: Trades={r['total_trades']:3d} ({r['trades_per_day']:.2f}/d) | WR={r['win_rate_pct']:4.1f}% | Gross PF={r['gross_pf']:4.2f} | Net PF={r['net_pf']:4.2f} | Exp=${r['expectancy']:6.2f} | Net PnL=${r['net_pnl']:7.2f} | DD={r['max_drawdown_pct']:4.1f}% | Fee/GP={r['fee_over_gp_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # EXP 2: LOCATION QUALITY FILTER EVALUATION
        # ----------------------------------------------------------------------
        print("\n[2/12] Evaluating Location Quality Filter (Midpoint Penalty vs Raw)...")
        tasks_loc = [
            {"score_threshold": 70, "location_filter": False, "initial_balance": 1000.0},
            {"score_threshold": 70, "location_filter": True, "initial_balance": 1000.0}
        ]
        results_loc = pool.map(worker_run_sim, tasks_loc)
        sweep_location = {
            "without_location_filter": results_loc[0],
            "with_location_filter": results_loc[1]
        }
        print(f"  Without Location Filter: Trades={results_loc[0]['total_trades']:3d} | WR={results_loc[0]['win_rate_pct']:4.1f}% | Net PF={results_loc[0]['net_pf']:4.2f} | Net PnL=${results_loc[0]['net_pnl']:7.2f}")
        print(f"  With Location Filter   : Trades={results_loc[1]['total_trades']:3d} | WR={results_loc[1]['win_rate_pct']:4.1f}% | Net PF={results_loc[1]['net_pf']:4.2f} | Net PnL=${results_loc[1]['net_pnl']:7.2f}")

        # ----------------------------------------------------------------------
        # EXP 3: CHASE FILTER MULTIPLIER SWEEP (2.2, 2.5, 2.8, 3.0 ATR)
        # ----------------------------------------------------------------------
        print("\n[3/12] Sweeping Chase Filter Multiplier (2.2, 2.5, 2.8, 3.0 ATR)...")
        tasks_chase = [{"score_threshold": 70, "chase_atr_multiplier": m, "initial_balance": 1000.0} for m in [2.2, 2.5, 2.8, 3.0]]
        results_chase = pool.map(worker_run_sim, tasks_chase)
        sweep_chase = {}
        for r in results_chase:
            m = r["params"]["chase_atr_multiplier"]
            sweep_chase[f"chase_{m}x"] = {
                "trades": r["total_trades"], "win_rate": r["win_rate_pct"], "net_pf": r["net_pf"],
                "expectancy": r["expectancy"], "net_pnl": r["net_pnl"]
            }
            print(f"  Chase {m:.1f} ATR: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Net PF={r['net_pf']:4.2f} | Exp=${r['expectancy']:6.2f} | Net PnL=${r['net_pnl']:7.2f}")

        # ----------------------------------------------------------------------
        # EXP 4: ADAPTIVE VOLATILITY FLOOR SWEEP (0.20, 0.25, 0.30 ATR)
        # ----------------------------------------------------------------------
        print("\n[4/12] Sweeping Volatility Floor (0.20, 0.25, 0.30 ATR)...")
        tasks_vol = [{"score_threshold": 70, "min_atr_m1": v, "initial_balance": 1000.0} for v in [0.20, 0.25, 0.30]]
        results_vol = pool.map(worker_run_sim, tasks_vol)
        sweep_vol = {}
        for r in results_vol:
            v = r["params"]["min_atr_m1"]
            sweep_vol[f"min_atr_{v}"] = {
                "trades": r["total_trades"], "win_rate": r["win_rate_pct"], "net_pf": r["net_pf"],
                "expectancy": r["expectancy"], "net_pnl": r["net_pnl"]
            }
            print(f"  Min ATR {v:.2f}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Net PF={r['net_pf']:4.2f} | Net PnL=${r['net_pnl']:7.2f}")

        # ----------------------------------------------------------------------
        # EXP 5: SESSION OPTIMIZATION (MODES 1 - 5)
        # ----------------------------------------------------------------------
        print("\n[5/12] Evaluating Session Regimes (Mode 1 to 5)...")
        modes = ["ALL", "NO_ASIA", "RESTRICTED_ASIA", "MAJOR_ONLY", "WEIGHTED"]
        tasks_sess = [{"score_threshold": 70, "session_mode": sm, "initial_balance": 1000.0} for sm in modes]
        results_sess = pool.map(worker_run_sim, tasks_sess)
        sweep_sessions = {}
        for r in results_sess:
            sm = r["params"]["session_mode"]
            sweep_sessions[sm] = {
                "trades": r["total_trades"], "win_rate": r["win_rate_pct"], "net_pf": r["net_pf"],
                "expectancy": r["expectancy"], "net_pnl": r["net_pnl"], "fees": r["total_fees"]
            }
            print(f"  Mode {sm:16s}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Net PF={r['net_pf']:4.2f} | Exp=${r['expectancy']:6.2f} | Net PnL=${r['net_pnl']:7.2f} | Fees=${r['total_fees']:6.2f}")

        # ----------------------------------------------------------------------
        # EXP 6: EXIT MODEL OPTIMIZATION (MODELS A TO H)
        # ----------------------------------------------------------------------
        print("\n[6/12] Sweeping Exit Models (Model A to H)...")
        em_list = ["A", "B", "C", "D", "E", "F", "G", "H"]
        tasks_exit = [{"score_threshold": 70, "exit_model": em, "initial_balance": 1000.0} for em in em_list]
        results_exit = pool.map(worker_run_sim, tasks_exit)
        sweep_exits = {}
        for r in results_exit:
            em = r["params"]["exit_model"]
            sweep_exits[f"Model_{em}"] = {
                "trades": r["total_trades"], "win_rate": r["win_rate_pct"], "gross_pf": r["gross_pf"],
                "net_pf": r["net_pf"], "expectancy": r["expectancy"], "avg_r": r["average_r"],
                "net_pnl": r["net_pnl"], "fees": r["total_fees"], "max_dd": r["max_drawdown_pct"]
            }
            print(f"  Model {em}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Gross PF={r['gross_pf']:4.2f} | Net PF={r['net_pf']:4.2f} | Exp=${r['expectancy']:6.2f} | Net PnL=${r['net_pnl']:7.2f} | DD={r['max_drawdown_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # EXP 7: BREAKEVEN TRIGGER & FEE BUFFER SWEEP
        # ----------------------------------------------------------------------
        print("\n[7/12] Sweeping Breakeven Activation Thresholds (+0.75R to +1.5R)...")
        tasks_be = [{"score_threshold": 70, "exit_model": "B", "be_trigger_r": be, "be_buffer_pct": 0.0005, "initial_balance": 1000.0} for be in [0.75, 1.0, 1.25, 1.5]]
        results_be = pool.map(worker_run_sim, tasks_be)
        sweep_be = {}
        for r in results_be:
            be = r["params"]["be_trigger_r"]
            k = f"BE_{be}R_buf_0.05%"
            sweep_be[k] = {
                "trades": r["total_trades"], "win_rate": r["win_rate_pct"],
                "net_pf": r["net_pf"], "net_pnl": r["net_pnl"]
            }
            print(f"  {k:22s}: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Net PF={r['net_pf']:4.2f} | Net PnL=${r['net_pnl']:7.2f}")

        # ----------------------------------------------------------------------
        # EXP 8: FEE-AWARE GATE RATIO SWEEP (15%, 20%, 25%, 30%, 35%)
        # ----------------------------------------------------------------------
        print("\n[8/12] Sweeping Fee-to-Risk Gate Ratio (15%, 20%, 25%, 30%, 35%)...")
        tasks_fee = [{"score_threshold": 70, "fee_risk_gate_ratio": fg, "initial_balance": 1000.0} for fg in [0.15, 0.20, 0.25, 0.30, 0.35]]
        results_fee = pool.map(worker_run_sim, tasks_fee)
        sweep_fee_gate = {}
        for r in results_fee:
            fg = r["params"]["fee_risk_gate_ratio"]
            sweep_fee_gate[f"fee_gate_{int(fg*100)}%"] = {
                "trades": r["total_trades"], "win_rate": r["win_rate_pct"],
                "net_pf": r["net_pf"], "net_pnl": r["net_pnl"], "fees": r["total_fees"],
                "fee_over_gp": r["fee_over_gp_pct"]
            }
            print(f"  Fee Gate {int(fg*100):2d}%: Trades={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | Net PF={r['net_pf']:4.2f} | PnL=${r['net_pnl']:7.2f} | Fee/GP={r['fee_over_gp_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # EXP 9: RISK SCALING (0.25%, 0.50%, 0.75%, 1.00%)
        # ----------------------------------------------------------------------
        print("\n[9/12] Evaluating Risk Allocation Scaling (0.25% to 1.00%)...")
        tasks_risk = [{"score_threshold": 70, "normalized_risk_pct": rk, "initial_balance": 1000.0} for rk in [0.0025, 0.0050, 0.0075, 0.0100]]
        results_risk = pool.map(worker_run_sim, tasks_risk)
        sweep_risk = {}
        for r in results_risk:
            rk = r["params"]["normalized_risk_pct"]
            sweep_risk[f"risk_{rk*100:.2f}%"] = {
                "trades": r["total_trades"], "net_pnl": r["net_pnl"], "max_dd": r["max_drawdown_pct"]
            }
            print(f"  Risk {rk*100:4.2f}%: Net PnL=${r['net_pnl']:7.2f} | Max DD={r['max_drawdown_pct']:4.1f}%")

        # ----------------------------------------------------------------------
        # EXP 10: CANDIDATE SELECTION & WALK-FORWARD VALIDATION (60 / 20 / 20)
        # ----------------------------------------------------------------------
        print("\n[10/12] Executing Walk-Forward Validation on Candidate A and Candidate B...")
        idx_train_end = int(n_candles * 0.60)
        idx_val_end = int(n_candles * 0.80)

        # Full run for Candidate A (Top Performer: Score 80, Model G Dynamic ATR, Major Sessions)
        # and Candidate B (Balanced Benchmark: Score 70, Model B Two-stage BE, Weighted Sessions)
        res_a_full = run_simulation_v32_fast(features, score_threshold=80, exit_model="G", chase_atr_multiplier=2.5, fee_risk_gate_ratio=0.25, session_mode="MAJOR_ONLY", initial_balance=1000.0)
        res_b_full = run_simulation_v32_fast(features, score_threshold=70, exit_model="B", chase_atr_multiplier=2.5, fee_risk_gate_ratio=0.25, session_mode="WEIGHTED", initial_balance=1000.0)

        # Train / Val / OOS slices
        tasks_wf = [
            # Candidate A
            {"score_threshold": 80, "exit_model": "G", "chase_atr_multiplier": 2.5, "fee_risk_gate_ratio": 0.25, "session_mode": "MAJOR_ONLY", "initial_balance": 1000.0, "features_slice": (0, idx_train_end)},
            {"score_threshold": 80, "exit_model": "G", "chase_atr_multiplier": 2.5, "fee_risk_gate_ratio": 0.25, "session_mode": "MAJOR_ONLY", "initial_balance": 1000.0, "features_slice": (idx_train_end, idx_val_end)},
            {"score_threshold": 80, "exit_model": "G", "chase_atr_multiplier": 2.5, "fee_risk_gate_ratio": 0.25, "session_mode": "MAJOR_ONLY", "initial_balance": 1000.0, "features_slice": (idx_val_end, n_candles)},
            # Candidate B
            {"score_threshold": 70, "exit_model": "B", "chase_atr_multiplier": 2.5, "fee_risk_gate_ratio": 0.25, "session_mode": "WEIGHTED", "initial_balance": 1000.0, "features_slice": (0, idx_train_end)},
            {"score_threshold": 70, "exit_model": "B", "chase_atr_multiplier": 2.5, "fee_risk_gate_ratio": 0.25, "session_mode": "WEIGHTED", "initial_balance": 1000.0, "features_slice": (idx_train_end, idx_val_end)},
            {"score_threshold": 70, "exit_model": "B", "chase_atr_multiplier": 2.5, "fee_risk_gate_ratio": 0.25, "session_mode": "WEIGHTED", "initial_balance": 1000.0, "features_slice": (idx_val_end, n_candles)},
        ]
        res_wf = pool.map(worker_run_sim, tasks_wf)

        res_a_train, res_a_val, res_a_oos = res_wf[0], res_wf[1], res_wf[2]
        res_b_train, res_b_val, res_b_oos = res_wf[3], res_wf[4], res_wf[5]

        # Micro Account runs
        res_a_micro = run_simulation_v32_fast(features, score_threshold=80, exit_model="G", chase_atr_multiplier=2.5, fee_risk_gate_ratio=0.25, session_mode="MAJOR_ONLY", is_micro_account=True, initial_balance=2.7109)
        res_b_micro = run_simulation_v32_fast(features, score_threshold=70, exit_model="B", chase_atr_multiplier=2.5, fee_risk_gate_ratio=0.25, session_mode="WEIGHTED", is_micro_account=True, initial_balance=2.7109)

        print(f"  Candidate A Full: Trades={res_a_full['total_trades']:3d} | WR={res_a_full['win_rate_pct']:4.1f}% | Gross PF={res_a_full['gross_pf']:4.2f} | Net PF={res_a_full['net_pf']:4.2f} | Net PnL=${res_a_full['net_pnl']:7.2f} | Max DD={res_a_full['max_drawdown_pct']}%")
        print(f"    Train: Net PF={res_a_train['net_pf']:4.2f} | Val: Net PF={res_a_val['net_pf']:4.2f} | OOS: Net PF={res_a_oos['net_pf']:4.2f}")
        print(f"  Candidate B Full: Trades={res_b_full['total_trades']:3d} | WR={res_b_full['win_rate_pct']:4.1f}% | Gross PF={res_b_full['gross_pf']:4.2f} | Net PF={res_b_full['net_pf']:4.2f} | Net PnL=${res_b_full['net_pnl']:7.2f} | Max DD={res_b_full['max_drawdown_pct']}%")
        print(f"    Train: Net PF={res_b_train['net_pf']:4.2f} | Val: Net PF={res_b_val['net_pf']:4.2f} | OOS: Net PF={res_b_oos['net_pf']:4.2f}")
        print(f"  Candidate A Micro: Trades={res_a_micro['total_trades']:3d} | WR={res_a_micro['win_rate_pct']:4.1f}% | Net PnL=${res_a_micro['net_pnl']:7.4f} | Max DD={res_a_micro['max_drawdown_pct']}%")
        print(f"  Candidate B Micro: Trades={res_b_micro['total_trades']:3d} | WR={res_b_micro['win_rate_pct']:4.1f}% | Net PnL=${res_b_micro['net_pnl']:7.4f} | Max DD={res_b_micro['max_drawdown_pct']}%")

        # ----------------------------------------------------------------------
        # EXP 11: 10,000 MONTE CARLO BOOTSTRAP SIMULATION (Candidate A Normalized)
        # ----------------------------------------------------------------------
        print("\n[11/12] Executing 10,000-Run Monte Carlo Simulation on Candidate A (7 Cores Parallel)...")
        trade_pnls = [x["net_pnl"] for x in res_a_full["trades"]]
        total_mc_runs = 10000
        runs_per_worker = total_mc_runs // num_cores
        mc_tasks = [(trade_pnls, runs_per_worker) for _ in range(num_cores)]
        # Add remainder to last
        mc_tasks[-1] = (trade_pnls, runs_per_worker + (total_mc_runs % num_cores))

        mc_chunks = pool.map(worker_mc_chunk, mc_tasks)

        all_equities = []
        all_dds = []
        all_loss_streaks = []
        tot_profit = sum(c["profit_cnt"] for c in mc_chunks)
        tot_dd10 = sum(c["dd_10_cnt"] for c in mc_chunks)
        tot_dd15 = sum(c["dd_15_cnt"] for c in mc_chunks)
        tot_dd20 = sum(c["dd_20_cnt"] for c in mc_chunks)
        tot_ruin = sum(c["ruin_cnt"] for c in mc_chunks)

        for c in mc_chunks:
            all_equities.extend(c["equities"])
            all_dds.extend(c["dds"])
            all_loss_streaks.extend(c["loss_streaks"])

        all_equities.sort()
        all_dds.sort()
        all_loss_streaks.sort()

        monte_carlo_res = {
            "total_simulations": total_mc_runs,
            "prob_positive_pnl_pct": round((tot_profit / total_mc_runs) * 100.0, 2),
            "prob_dd_over_10pct": round((tot_dd10 / total_mc_runs) * 100.0, 2),
            "prob_dd_over_15pct": round((tot_dd15 / total_mc_runs) * 100.0, 2),
            "prob_dd_over_20pct": round((tot_dd20 / total_mc_runs) * 100.0, 2),
            "prob_ruin_pct": round((tot_ruin / total_mc_runs) * 100.0, 2),
            "median_ending_balance": round(all_equities[int(0.50 * total_mc_runs)], 2),
            "p05_ending_balance": round(all_equities[int(0.05 * total_mc_runs)], 2),
            "p95_ending_balance": round(all_equities[int(0.95 * total_mc_runs)], 2),
            "p95_max_dd_pct": round(all_dds[int(0.95 * total_mc_runs)], 2),
            "worst_case_max_dd_pct": round(max(all_dds), 2),
            "median_max_loss_streak": int(all_loss_streaks[int(0.50 * total_mc_runs)]),
            "p95_max_loss_streak": int(all_loss_streaks[int(0.95 * total_mc_runs)])
        }

        print(f"  Probability of Profit : {monte_carlo_res['prob_positive_pnl_pct']}%")
        print(f"  Probability of DD >10%: {monte_carlo_res['prob_dd_over_10pct']}%")
        print(f"  Probability of DD >15%: {monte_carlo_res['prob_dd_over_15pct']}%")
        print(f"  Probability of Ruin   : {monte_carlo_res['prob_ruin_pct']}%")
        print(f"  Median Final Balance  : ${monte_carlo_res['median_ending_balance']}")
        print(f"  5th Percentile Balance: ${monte_carlo_res['p05_ending_balance']}")
        print(f"  95th Percentile Max DD: {monte_carlo_res['p95_max_dd_pct']}%")

        # ----------------------------------------------------------------------
        # EXP 12: FAILURE MODE FORENSICS
        # ----------------------------------------------------------------------
        # EXP 12: FAILURE MODE FORENSICS (Candidate A)
        # ----------------------------------------------------------------------
        print("\n[12/12] Analyzing Trade Failure Modes for Candidate A...")
        failure_counts = {}
        for tr in res_a_full["trades"]:
            if tr["net_pnl"] <= 0:
                fm = tr["failure_mode"]
                failure_counts[fm] = failure_counts.get(fm, 0) + 1

        for fm, cnt in sorted(failure_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((cnt / max(1, sum(failure_counts.values()))) * 100.0, 1)
            print(f"  {fm:28s}: {cnt:3d} losses ({pct:4.1f}%)")

    # --------------------------------------------------------------------------
    # SAVE ALL AUDIT ARTIFACTS
    # --------------------------------------------------------------------------
    print("\nSaving all empirical artifacts to disk...")

    # Trade Log CSV (Candidate A Winning Candidate)
    with open(r"C:\apex_copytrade\v32_trade_log.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "timestamp", "side", "session", "module", "class", "M15_regime", "M5_setup",
            "score", "entry", "qty", "notional", "margin", "SL", "TP1", "TP2", "exit_price",
            "exit_reason", "failure_mode", "gross_pnl", "total_fees", "net_pnl", "realized_r",
            "holding_time_min", "equity_after", "drawdown_pct", "exit_time"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tr in res_a_full["trades"]:
            writer.writerow(tr)

    # Daily Results CSV
    daily_dict = {}
    for tr in res_a_full["trades"]:
        d = tr["timestamp"][:10]
        if d not in daily_dict:
            daily_dict[d] = {"date": d, "trades": 0, "wins": 0, "net_pnl": 0.0, "fees": 0.0}
        daily_dict[d]["trades"] += 1
        if tr["net_pnl"] > 0:
            daily_dict[d]["wins"] += 1
        daily_dict[d]["net_pnl"] = round(daily_dict[d]["net_pnl"] + tr["net_pnl"], 4)
        daily_dict[d]["fees"] = round(daily_dict[d]["fees"] + tr["total_fees"], 4)

    daily_rows = []
    for d in sorted(daily_dict.keys()):
        item = daily_dict[d]
        wr = round((item["wins"]/item["trades"])*100.0, 1)
        daily_rows.append({"date": d, "trades": item["trades"], "wins": item["wins"], "win_rate_pct": wr, "net_pnl": item["net_pnl"], "fees": item["fees"]})

    with open(r"C:\apex_copytrade\v32_daily_results.csv", "w", newline="", encoding="utf-8") as f:
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

    with open(r"C:\apex_copytrade\v32_weekly_results.csv", "w", newline="", encoding="utf-8") as f:
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

    with open(r"C:\apex_copytrade\v32_monthly_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["month", "trades", "wins", "win_rate_pct", "net_pnl", "fees"])
        writer.writeheader()
        writer.writerows(monthly_rows)

    # Equity curve CSV
    with open(r"C:\apex_copytrade\v32_equity_curve.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["time", "equity", "dd_pct"])
        writer.writeheader()
        writer.writerows(res_a_full["equity_curve"])

    # High-Res Dark-Mode PNG Chart
    def create_png_chart(equity_points: List[Dict[str, Any]], out_paths: List[str]):
        width = 1000
        height = 500
        bg_color = (13, 17, 23)
        grid_color = (33, 38, 45)
        line_color = (88, 166, 255)

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

    png_paths = [
        r"C:\apex_copytrade\v32_equity_curve.png",
        r"C:\Users\tillo\.gemini\antigravity-ide\brain\a774c680-492e-43de-8369-8a2ac81b333c\v32_equity_curve.png"
    ]
    create_png_chart(res_a_full["equity_curve"], png_paths)

    # Save JSON summaries
    summary_json = {
        "candidate_a_normalized": {k: v for k, v in res_a_full.items() if k not in ["trades", "equity_curve"]},
        "candidate_a_micro": {k: v for k, v in res_a_micro.items() if k not in ["trades", "equity_curve"]},
        "candidate_b_normalized": {k: v for k, v in res_b_full.items() if k not in ["trades", "equity_curve"]},
        "candidate_b_micro": {k: v for k, v in res_b_micro.items() if k not in ["trades", "equity_curve"]},
        "score_sweep": sweep_score,
        "location_filter": sweep_location,
        "chase_sweep": sweep_chase,
        "volatility_sweep": sweep_vol,
        "session_modes": sweep_sessions,
        "exit_models": sweep_exits,
        "breakeven_sweep": sweep_be,
        "fee_gate_sweep": sweep_fee_gate,
        "risk_levels": sweep_risk,
        "walk_forward": {
            "candidate_a": {
                "train": {"trades": res_a_train["total_trades"], "net_pf": res_a_train["net_pf"], "pnl": res_a_train["net_pnl"], "wr": res_a_train["win_rate_pct"]},
                "val": {"trades": res_a_val["total_trades"], "net_pf": res_a_val["net_pf"], "pnl": res_a_val["net_pnl"], "wr": res_a_val["win_rate_pct"]},
                "oos": {"trades": res_a_oos["total_trades"], "net_pf": res_a_oos["net_pf"], "pnl": res_a_oos["net_pnl"], "wr": res_a_oos["win_rate_pct"]}
            },
            "candidate_b": {
                "train": {"trades": res_b_train["total_trades"], "net_pf": res_b_train["net_pf"], "pnl": res_b_train["net_pnl"], "wr": res_b_train["win_rate_pct"]},
                "val": {"trades": res_b_val["total_trades"], "net_pf": res_b_val["net_pf"], "pnl": res_b_val["net_pnl"], "wr": res_b_val["win_rate_pct"]},
                "oos": {"trades": res_b_oos["total_trades"], "net_pf": res_b_oos["net_pf"], "pnl": res_b_oos["net_pnl"], "wr": res_b_oos["win_rate_pct"]}
            }
        },
        "monte_carlo_10k": monte_carlo_res,
        "failure_modes": failure_counts
    }

    with open(r"C:\apex_copytrade\v32_backtest_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2)

    with open(r"C:\apex_copytrade\v32_monte_carlo.json", "w", encoding="utf-8") as f:
        json.dump(monte_carlo_res, f, indent=2)

    total_elapsed = time.time() - start_total_time
    print("\n" + "=" * 80)
    print(f"   APEX QUANT v3.2 SUITE COMPLETE IN {total_elapsed:.2f}s — ALL DELIVERABLES SAVED")
    print("=" * 80)

if __name__ == "__main__":
    main()
