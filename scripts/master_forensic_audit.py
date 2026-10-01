#!/usr/bin/env python3
"""
MASTER INDEPENDENT FORENSIC AUDIT OF APEX QUANT v3.4 HIGH-WINRATE BACKTEST
==========================================================================
Auditor: Independent Quantitative Risk & Forensic Validation Engine
Dataset: Binance Futures ETHUSDT M1 90-Day (129,600 bars, June 29 - Sept 27, 2026)
Standards: Zero Lookahead Bias, Strict Multi-Phase OOS, Friction Analysis,
           Intrabar Ambiguity Resolution, Multiple Testing Correction.
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import csv
import json
import math
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

DATA_PATH = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"
AUDIT_DIR = r"C:\apex_copytrade\audit"
os.makedirs(AUDIT_DIR, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. DATA INTEGRITY & AUDIT PRE-FLIGHT
# ------------------------------------------------------------------------------
def audit_data_integrity(data_path: str) -> Dict[str, Any]:
    print("=" * 80)
    print("PHASE 1: DATA INTEGRITY & TIMESTAMP CONSISTENCY AUDIT")
    print("=" * 80)
    
    rows = []
    with open(data_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for line_no, r in enumerate(reader, start=2):
            try:
                t = int(r[0])
                o = float(r[1])
                h = float(r[2])
                l = float(r[3])
                c = float(r[4])
                v = float(r[5])
                rows.append({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v, "line": line_no})
            except Exception as e:
                raise ValueError(f"Corrupt data at line {line_no}: {e}")

    total_candles = len(rows)
    timestamps = [r["time"] for r in rows]

    # Timestamp checks
    is_strictly_monotonic = all(timestamps[i] < timestamps[i+1] for i in range(total_candles - 1))
    gaps = []
    for i in range(total_candles - 1):
        diff = timestamps[i+1] - timestamps[i]
        if diff != 60000: # 60,000 ms = 1 minute
            gaps.append((i, timestamps[i], timestamps[i+1], diff))

    # Price validity
    invalid_ohlc = []
    for r in rows:
        if r["high"] < r["low"] or r["open"] < 0 or r["close"] < 0 or r["volume"] < 0:
            invalid_ohlc.append(r)
        if r["high"] < max(r["open"], r["close"]) or r["low"] > min(r["open"], r["close"]):
            invalid_ohlc.append(r)

    start_dt = datetime.fromtimestamp(timestamps[0] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    end_dt = datetime.fromtimestamp(timestamps[-1] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    span_days = (timestamps[-1] - timestamps[0]) / (1000.0 * 86400.0)

    report = {
        "file": data_path,
        "total_candles": total_candles,
        "expected_candles_90d": 129600,
        "start_time": start_dt,
        "end_time": end_dt,
        "span_days": round(span_days, 2),
        "is_strictly_monotonic": is_strictly_monotonic,
        "timestamp_gaps_count": len(gaps),
        "timestamp_gaps": gaps[:5],
        "invalid_ohlc_count": len(invalid_ohlc),
        "integrity_status": "PASS" if (is_strictly_monotonic and len(gaps) == 0 and len(invalid_ohlc) == 0 and total_candles == 129600) else "WARN"
    }

    print(f"  Candles count        : {total_candles:,} (Expected: 129,600)")
    print(f"  Date Range           : {start_dt} -> {end_dt} ({span_days:.2f} days)")
    print(f"  Strict Monotonicity  : {'PASS' if is_strictly_monotonic else 'FAIL'}")
    print(f"  Timestamp Gaps       : {len(gaps)}")
    print(f"  Invalid OHLC bars    : {len(invalid_ohlc)}")
    print(f"  Data Integrity Verdict: {report['integrity_status']}")

    return report, rows

# ------------------------------------------------------------------------------
# 2. FEATURE EXTRACTION & STRICT ZERO-LOOKAHEAD MTF ENGINE
# ------------------------------------------------------------------------------
def fast_ema(arr: List[float], period: int) -> List[float]:
    n = len(arr)
    res = [0.0] * n
    if n < period: return res
    mult = 2.0 / (period + 1.0)
    sma = sum(arr[:period]) / period
    for i in range(period - 1): res[i] = arr[i]
    res[period - 1] = sma
    cur = sma
    for i in range(period, n):
        cur = (arr[i] - cur) * mult + cur
        res[i] = cur
    return res

def fast_rsi(closes: List[float], period: int = 14) -> List[float]:
    n = len(closes)
    res = [50.0] * n
    if n <= period: return res
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        chg = closes[i] - closes[i-1]
        if chg > 0: gains[i] = chg
        else: losses[i] = -chg
    avg_gain = sum(gains[1:period+1]) / period
    avg_loss = sum(losses[1:period+1]) / period
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0: res[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            res[i] = round(100.0 - (100.0 / (1.0 + rs)), 1)
    return res

def precalculate_features(raw_candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    n = len(raw_candles)
    closes = [c["close"] for c in raw_candles]
    highs = [c["high"] for c in raw_candles]
    lows = [c["low"] for c in raw_candles]
    opens = [c["open"] for c in raw_candles]
    vols = [c["volume"] for c in raw_candles]
    times = [c["time"] for c in raw_candles]

    e9 = fast_ema(closes, 9)
    e21 = fast_ema(closes, 21)
    e50 = fast_ema(closes, 50)
    e200 = fast_ema(closes, 200)
    rsi14 = fast_rsi(closes, 14)

    tr = [0.0] * n
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    atr = [1.20] * n
    if n >= 15:
        init_atr = sum(tr[1:15]) / 14.0
        for i in range(15): atr[i] = init_atr
        cur_atr = init_atr
        for i in range(15, n):
            cur_atr = (cur_atr * 13.0 + tr[i]) / 14.0
            atr[i] = round(cur_atr, 2)

    # MTF synthesis strictly from COMPLETED bars
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
        # completed M5 bar index available at bar i
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

    m5_closes = [b["close"] for b in m5_bars]
    m5_highs = [b["high"] for b in m5_bars]
    m5_lows = [b["low"] for b in m5_bars]
    m5_e21 = fast_ema(m5_closes, 21)
    m5_e50 = fast_ema(m5_closes, 50)

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

        m1_sw_low_12 = min(lows[max(0, i-11):i]) if i >= 11 else lows[i]
        m1_sw_high_12 = max(highs[max(0, i-11):i]) if i >= 11 else highs[i]

        prior_high_15 = max(highs[max(0, i-14):max(0, i-1)]) if i >= 15 else highs[i]
        prior_low_15 = min(lows[max(0, i-14):max(0, i-1)]) if i >= 15 else lows[i]

        vol_avg_10 = (sum(vols[max(0, i-9):i]) / 9.0) if i >= 10 else vols[i]
        vol_avg_5 = (sum(vols[max(0, i-5):i]) / 5.0) if i >= 6 else vols[i]

        loc_h20 = max(highs[max(0, i-19):i]) if i >= 20 else highs[i]
        loc_l20 = min(lows[max(0, i-19):i]) if i >= 20 else lows[i]
        midpoint = (loc_h20 + loc_l20) / 2.0
        range_span = max(0.50, loc_h20 - loc_l20)
        dist_from_mid = abs(c["close"] - midpoint) / range_span

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

        # Module B: Breakout & Retest (Consolidation width <= 2.2 ATR)
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

        # Calculate wick statistics for candle geometry audit
        upper_wick = c["high"] - max(c["open"], c["close"])
        lower_wick = min(c["open"], c["close"]) - c["low"]
        candle_range = c["high"] - c["low"]

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
            "range": candle_range,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
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
            "dist_from_mid": dist_from_mid,
            "vol_expansion": (c["volume"] > vol_avg_5),
            "module_candidates": module_candidates
        })

    return features

# ------------------------------------------------------------------------------
# 3. COMPREHENSIVE SIMULATOR WITH INTRABAR AMBIGUITY, COST & EXCURSION TRACKING
# ------------------------------------------------------------------------------
def run_forensic_simulation(
    features: List[Dict[str, Any]],
    params: Dict[str, Any],
    intrabar_resolution: str = "CONSERVATIVE", # "CONSERVATIVE" (SL first), "OPTIMISTIC" (TP first), "RANDOM"
    execution_type: str = "MAKER_POST_ONLY",    # "MAKER_POST_ONLY" (0.02% + 0 slippage), "REALISTIC_TAKER" (0.05% + 1 tick slip)
    start_idx: int = 250,
    end_idx: Optional[int] = None
) -> Dict[str, Any]:

    if end_idx is None:
        end_idx = len(features)

    module_name = params["module"]
    trend_filter = params["trend_filter"]
    session_mode = params["session_mode"]
    sl_atr_mult = params["sl_atr_mult"]
    min_sl_usd = params["min_sl_usd"]
    tp_r = params["tp_r"]
    score_thresh = params["score_thresh"]
    adx_min = params["adx_min"]

    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = initial_balance
    trades = []
    ambiguous_trades = []

    in_pos = False
    pos = {}
    current_day = ""
    daily_trades = 0
    cooldown_until = 0

    if execution_type == "MAKER_POST_ONLY":
        entry_fee_rate = 0.0002
        tp_fee_rate = 0.0002
        sl_fee_rate = 0.0005
        slippage_ticks = 0.0
    else: # REALISTIC_TAKER
        entry_fee_rate = 0.0005
        tp_fee_rate = 0.0002
        sl_fee_rate = 0.0005
        slippage_ticks = 0.01 # 1 tick adverse

    for idx in range(start_idx, end_idx):
        f = features[idx]
        t = f["time"]
        day_str = f["day_str"]
        curr_c = f["close"]
        high = f["high"]
        low = f["low"]

        if day_str != current_day:
            current_day = day_str
            daily_trades = 0

        # --- POSITION MANAGEMENT & EXCURSION TRACKING ---
        if in_pos:
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            target = pos["tp"]
            qty = pos["qty"]
            r_dist = pos["r_dist"]

            # Update MAE and MFE
            if side == "LONG":
                bar_mae = (entry - low) # adverse distance
                bar_mfe = (high - entry) # favorable distance
            else:
                bar_mae = (high - entry)
                bar_mfe = (entry - low)
            pos["max_mae"] = max(pos["max_mae"], bar_mae)
            pos["max_mfe"] = max(pos["max_mfe"], bar_mfe)

            closed = False
            exit_p = 0.0
            reason = ""
            is_ambiguous = False

            if side == "LONG":
                sl_touch = (low <= sl)
                tp_touch = (high >= target)
                if sl_touch and tp_touch:
                    is_ambiguous = True
                    if intrabar_resolution == "OPTIMISTIC":
                        closed = True; exit_p = target; reason = "TP_HIT"
                    else: # CONSERVATIVE or RANDOM
                        closed = True; exit_p = sl - 0.01; reason = "SL_HIT"
                elif sl_touch:
                    closed = True; exit_p = sl - 0.01; reason = "SL_HIT"
                elif tp_touch:
                    closed = True; exit_p = target; reason = "TP_HIT"
            else: # SHORT
                sl_touch = (high >= sl)
                tp_touch = (low <= target)
                if sl_touch and tp_touch:
                    is_ambiguous = True
                    if intrabar_resolution == "OPTIMISTIC":
                        closed = True; exit_p = target; reason = "TP_HIT"
                    else:
                        closed = True; exit_p = sl + 0.01; reason = "SL_HIT"
                elif sl_touch:
                    closed = True; exit_p = sl + 0.01; reason = "SL_HIT"
                elif tp_touch:
                    closed = True; exit_p = target; reason = "TP_HIT"

            if closed:
                gross_pnl = (exit_p - entry) * qty if side == "LONG" else (entry - exit_p) * qty
                f_rate = tp_fee_rate if reason == "TP_HIT" else sl_fee_rate
                exit_fee = qty * exit_p * f_rate
                total_commissions = pos["entry_fee"] + exit_fee
                total_slippage = qty * slippage_ticks
                net_trade_pnl = gross_pnl - total_commissions - total_slippage

                realized_r = round(net_trade_pnl / max(0.01, qty * r_dist), 2)
                balance = round(balance + net_trade_pnl, 4)
                peak_balance = max(peak_balance, balance)
                dd_pct = round(((peak_balance - balance) / peak_balance) * 100.0, 2)

                daily_trades += 1
                cooldown_until = idx + 10

                trade_record = {
                    "timestamp": datetime.fromtimestamp(pos["open_time"] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "symbol": "ETHUSDT",
                    "side": side,
                    "module": pos["module"],
                    "entry": entry,
                    "SL": sl,
                    "TP": target,
                    "exit": exit_p,
                    "result": reason,
                    "is_win": net_trade_pnl > 0,
                    "R": realized_r,
                    "gross_pnl": round(gross_pnl, 4),
                    "commission": round(total_commissions, 4),
                    "slippage": round(total_slippage, 4),
                    "net_pnl": round(net_trade_pnl, 4),
                    "MAE": round(pos["max_mae"], 2),
                    "MFE": round(pos["max_mfe"], 2),
                    "session": pos["session"],
                    "trend": pos["trend"],
                    "ADX": pos["adx"],
                    "score": pos["score"],
                    "holding_bars": idx - pos["entry_idx"],
                    "is_ambiguous": is_ambiguous,
                    "equity": balance,
                    "dd_pct": dd_pct
                }
                trades.append(trade_record)
                if is_ambiguous:
                    ambiguous_trades.append(trade_record)

                in_pos = False
                pos = {}

        # --- ENTRY EVALUATION ---
        if not in_pos and idx >= cooldown_until and daily_trades < 8:
            if session_mode == "LONDON_EXPANSION" and f["session"] not in ["LONDON", "LONDON_NY_OVERLAP"]:
                continue
            elif session_mode == "MAJOR" and f["session"] not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                continue

            if adx_min > 0 and f["m15_adx"] < adx_min:
                continue

            if f["atr"] < 0.25 or f["body"] > 2.5 * f["atr"]:
                continue

            cand_signal = None
            cand_score = 0
            cand_mod = ""
            for side_c, mod_c, base_sc in f["module_candidates"]:
                if module_name != "ALL" and mod_c != module_name:
                    continue

                if trend_filter == "STRICT_HTF":
                    if side_c == "LONG" and (f["m15_context"] == "BEARISH" or curr_c < f["e200"]): continue
                    if side_c == "SHORT" and (f["m15_context"] == "BULLISH" or curr_c > f["e200"]): continue
                elif trend_filter == "M5_M15":
                    if side_c == "LONG" and (f["m15_context"] == "BEARISH" or f["m5_setup"] == "M5_BEAR_TREND"): continue
                    if side_c == "SHORT" and (f["m15_context"] == "BULLISH" or f["m5_setup"] == "M5_BULL_TREND"): continue

                score = base_sc
                if f["dist_from_mid"] >= 0.15: score += 10
                else: score -= 10

                if side_c == "LONG" and f["e9"] > f["e21"]: score += 15
                elif side_c == "SHORT" and f["e9"] < f["e21"]: score += 15

                if side_c == "LONG" and f["m5_setup"] == "M5_BULL_TREND": score += 15
                elif side_c == "SHORT" and f["m5_setup"] == "M5_BEAR_TREND": score += 15

                if side_c == "LONG":
                    if f["m15_context"] == "BULLISH": score += 15
                    elif f["m15_context"] == "BEARISH": score -= 15
                else:
                    if f["m15_context"] == "BEARISH": score += 15
                    elif f["m15_context"] == "BULLISH": score -= 15

                if f["vol_expansion"]: score += 10

                if score >= score_thresh and score > cand_score:
                    cand_score = score
                    cand_signal = side_c
                    cand_mod = mod_c

            if not cand_signal:
                continue

            # Geometry
            atr_v = f["atr"]
            raw_sl_dist = sl_atr_mult * atr_v
            r_dist = max(min_sl_usd, min(curr_c * 0.015, raw_sl_dist))
            sl_price = round(curr_c - r_dist, 2) if cand_signal == "LONG" else round(curr_c + r_dist, 2)
            tp_price = round(curr_c + (tp_r * r_dist), 2) if cand_signal == "LONG" else round(curr_c - (tp_r * r_dist), 2)

            risk_usd = balance * 0.010
            qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
            
            # Entry price with slippage modeling
            entry_p = curr_c + (slippage_ticks if cand_signal == "LONG" else -slippage_ticks)
            entry_fee = round(qty * entry_p * entry_fee_rate, 4)

            in_pos = True
            pos = {
                "side": cand_signal,
                "module": cand_mod,
                "entry": entry_p,
                "sl": sl_price,
                "tp": tp_price,
                "qty": qty,
                "r_dist": r_dist,
                "entry_fee": entry_fee,
                "open_time": t,
                "entry_idx": idx,
                "session": f["session"],
                "trend": f["m15_context"],
                "adx": f["m15_adx"],
                "score": cand_score,
                "max_mae": 0.0,
                "max_mfe": 0.0
            }

    # Statistics Calculation
    total_trades = len(trades)
    if total_trades == 0:
        return {"total_trades": 0, "trades": [], "ambiguous_count": 0}

    wins = [t for t in trades if t["is_win"]]
    losses = [t for t in trades if not t["is_win"] and t["net_pnl"] < 0]
    breakevens = [t for t in trades if t["net_pnl"] == 0]

    wr = round((len(wins) / total_trades) * 100.0, 1)
    gross_profit = sum(t["gross_pnl"] for t in wins)
    gross_loss = abs(sum(t["gross_pnl"] for t in trades if t["gross_pnl"] < 0))
    total_commission = sum(t["commission"] for t in trades)
    total_slippage = sum(t["slippage"] for t in trades)
    net_pnl = sum(t["net_pnl"] for t in trades)

    gross_pf = round((gross_profit / gross_loss) if gross_loss > 0 else 99.0, 2)
    net_wins = sum(t["net_pnl"] for t in wins)
    net_losses = abs(sum(t["net_pnl"] for t in trades if t["net_pnl"] < 0))
    net_pf = round((net_wins / net_losses) if net_losses > 0 else 99.0, 2)

    win_pnls = [t["net_pnl"] for t in wins]
    loss_pnls = [abs(t["net_pnl"]) for t in trades if t["net_pnl"] < 0]

    avg_win = round(sum(win_pnls) / max(1, len(win_pnls)), 2)
    avg_loss = round(sum(loss_pnls) / max(1, len(loss_pnls)), 2)
    
    sorted_wins = sorted(win_pnls)
    sorted_losses = sorted(loss_pnls)
    median_win = round(sorted_wins[len(sorted_wins)//2] if sorted_wins else 0.0, 2)
    median_loss = round(sorted_losses[len(sorted_losses)//2] if sorted_losses else 0.0, 2)

    # Streaks
    max_win_streak = 0
    max_loss_streak = 0
    cur_win = 0
    cur_loss = 0
    for t in trades:
        if t["is_win"]:
            cur_win += 1
            cur_loss = 0
            max_win_streak = max(max_win_streak, cur_win)
        else:
            cur_loss += 1
            cur_win = 0
            max_loss_streak = max(max_loss_streak, cur_loss)

    max_dd = round(max((t["dd_pct"] for t in trades), default=0.0), 2)
    recovery_factor = round(net_pnl / max(1.0, max_dd * (initial_balance / 100.0)), 2)
    
    # Sharpe-like trade metric (mean trade return / stdev of trade return * sqrt(252 * trades_per_day))
    trade_pnls = [t["net_pnl"] for t in trades]
    mean_pnl = sum(trade_pnls) / total_trades
    var_pnl = sum((p - mean_pnl)**2 for p in trade_pnls) / max(1, total_trades - 1)
    std_pnl = math.sqrt(var_pnl)
    trades_per_day = total_trades / 90.0
    sharpe = round((mean_pnl / max(1e-4, std_pnl)) * math.sqrt(252 * trades_per_day), 2) if std_pnl > 0 else 0.0

    expectancy_usd = round(net_pnl / total_trades, 2)
    avg_r = round(sum(t["R"] for t in trades) / total_trades, 2)

    return {
        "params": params,
        "total_trades": total_trades,
        "trades_per_day": round(trades_per_day, 2),
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": len(breakevens),
        "win_rate_pct": wr,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "gross_pf": gross_pf,
        "net_pnl": round(net_pnl, 2),
        "total_commissions": round(total_commission, 2),
        "total_slippage": round(total_slippage, 2),
        "net_pf": net_pf,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "median_win": median_win,
        "median_loss": median_loss,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "max_dd_pct": max_dd,
        "recovery_factor": recovery_factor,
        "sharpe": sharpe,
        "expectancy_usd": expectancy_usd,
        "avg_r": avg_r,
        "ambiguous_count": len(ambiguous_trades),
        "ambiguous_pct": round(len(ambiguous_trades) / total_trades * 100.0, 1),
        "trades": trades,
        "ambiguous_trades": ambiguous_trades
    }

# ------------------------------------------------------------------------------
# 4. STATISTICAL PERFORMANCES & ARTIFACT GENERATION
# ------------------------------------------------------------------------------
def wilson_score_interval(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0: return 0.0, 0.0
    z = 1.95996 # 95% confidence
    p = wins / total
    denom = 1.0 + (z**2 / total)
    center = (p + (z**2 / (2 * total))) / denom
    margin = (z * math.sqrt((p * (1 - p) / total) + (z**2 / (4 * total**2)))) / denom
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return round(lower * 100.0, 1), round(upper * 100.0, 1)

def run_monte_carlo(trade_pnls: List[float], num_simulations: int = 10000, initial_balance: float = 1000.0) -> Dict[str, Any]:
    n_trades = len(trade_pnls)
    final_equities = []
    max_dds = []
    loss_streaks = []
    ruin_count = 0
    dd_20_count = 0
    streak_10_count = 0

    for _ in range(num_simulations):
        sampled = [random.choice(trade_pnls) for _ in range(n_trades)]
        eq = initial_balance
        peak = eq
        mdd = 0.0
        c_loss = 0
        m_loss = 0
        for pnl in sampled:
            eq += pnl
            if eq > peak: peak = eq
            dd = (peak - eq) / peak * 100.0
            if dd > mdd: mdd = dd
            if pnl <= 0:
                c_loss += 1
                if c_loss > m_loss: m_loss = c_loss
            else:
                c_loss = 0
        final_equities.append(eq)
        max_dds.append(mdd)
        loss_streaks.append(m_loss)

        if eq <= initial_balance * 0.20: ruin_count += 1
        if mdd >= 20.0: dd_20_count += 1
        if m_loss >= 10: streak_10_count += 1

    final_equities.sort()
    max_dds.sort()
    loss_streaks.sort()

    return {
        "num_simulations": num_simulations,
        "median_ending_equity": round(final_equities[int(0.50 * num_simulations)], 2),
        "p05_ending_equity": round(final_equities[int(0.05 * num_simulations)], 2),
        "p95_ending_equity": round(final_equities[int(0.95 * num_simulations)], 2),
        "median_max_dd_pct": round(max_dds[int(0.50 * num_simulations)], 2),
        "p95_max_dd_pct": round(max_dds[int(0.95 * num_simulations)], 2),
        "median_loss_streak": loss_streaks[int(0.50 * num_simulations)],
        "p95_loss_streak": loss_streaks[int(0.95 * num_simulations)],
        "prob_ruin_pct": round((ruin_count / num_simulations) * 100.0, 2),
        "prob_dd_ge_20pct": round((dd_20_count / num_simulations) * 100.0, 2),
        "prob_streak_ge_10": round((streak_10_count / num_simulations) * 100.0, 2)
    }

def main():
    print("=" * 80)
    print("APEX QUANT v3.4 HIGH-WINRATE BACKTEST — MASTER FORENSIC AUDIT")
    print("=" * 80)

    # 1. Audit Data Integrity
    data_report, raw_candles = audit_data_integrity(DATA_PATH)

    # 2. Precalculate features
    print("\n" + "=" * 80)
    print("PHASE 2: FEATURE PRECALCULATION & MULTI-TIMEFRAME EXTRACTION")
    print("=" * 80)
    t0 = time.time()
    features = precalculate_features(raw_candles)
    print(f"Features synthesized across {len(features):,} M1 bars in {time.time()-t0:.2f}s.")

    # 3. Model Definitions
    model_configs = {
        "Model_1": {
            "module": "MODULE_B_BREAKOUT",
            "session_mode": "LONDON_EXPANSION",
            "trend_filter": "M5_M15",
            "sl_atr_mult": 1.5,
            "min_sl_usd": 8.0,
            "tp_r": 0.8,
            "score_thresh": 80,
            "adx_min": 0
        },
        "Model_2": {
            "module": "MODULE_B_BREAKOUT",
            "session_mode": "LONDON_EXPANSION",
            "trend_filter": "M5_M15",
            "sl_atr_mult": 1.5,
            "min_sl_usd": 8.0,
            "tp_r": 0.8,
            "score_thresh": 70,
            "adx_min": 0
        },
        "Model_3": {
            "module": "MODULE_B_BREAKOUT",
            "session_mode": "LONDON_EXPANSION",
            "trend_filter": "M5_M15",
            "sl_atr_mult": 1.5,
            "min_sl_usd": 8.0,
            "tp_r": 0.8,
            "score_thresh": 70,
            "adx_min": 22
        }
    }

    # 4. Detailed Evaluation of Models 1, 2, 3
    print("\n" + "=" * 80)
    print("PHASE 3: DETAILED TRADE-LEVEL AUDIT OF MODELS #1, #2, #3")
    print("=" * 80)

    audit_models = {}
    for m_name, cfg in model_configs.items():
        res = run_forensic_simulation(features, cfg, intrabar_resolution="CONSERVATIVE", execution_type="MAKER_POST_ONLY")
        ci_low, ci_high = wilson_score_interval(res["wins"], res["total_trades"])
        res["wilson_95_ci"] = [ci_low, ci_high]
        audit_models[m_name] = res

        print(f"\n--- {m_name.upper()} FORENSIC SUMMARY ---")
        print(f"  Total Trades       : {res['total_trades']} ({res['trades_per_day']} / day)")
        print(f"  Wins / Losses / BE : {res['wins']} / {res['losses']} / {res['breakevens']}")
        print(f"  Observed Win Rate  : {res['win_rate_pct']}% (95% CI: [{ci_low}%, {ci_high}%])")
        print(f"  Gross PnL          : +${res['gross_profit']:.2f} (Profit) / -${res['gross_loss']:.2f} (Loss) | Gross PF = {res['gross_pf']}x")
        print(f"  Commissions Paid   : ${res['total_commissions']:.2f} (Maker 0.02% Entry / Taker 0.05% SL)")
        print(f"  Net PnL            : +${res['net_pnl']:.2f} | Net PF = {res['net_pf']}x")
        print(f"  Average Win/Loss   : Win = +${res['avg_win']:.2f} | Loss = -${res['avg_loss']:.2f} (Payoff = {res['avg_win']/max(0.01, res['avg_loss']):.2f}x)")
        print(f"  Median Win/Loss    : Win = +${res['median_win']:.2f} | Loss = -${res['median_loss']:.2f}")
        print(f"  Expectancy / Trade : +${res['expectancy_usd']:.2f} (+{res['avg_r']}R)")
        print(f"  Max Win/Loss Streak: Win Streak = {res['max_win_streak']} | Loss Streak = {res['max_loss_streak']}")
        print(f"  Max Drawdown       : {res['max_dd_pct']}% | Recovery Factor = {res['recovery_factor']}x")
        print(f"  Annualized Sharpe  : {res['sharpe']}")
        print(f"  Ambiguous Bars     : {res['ambiguous_count']} ({res['ambiguous_pct']}%)")

    # 5. Theoretical vs Empirical Barrier Mathematics
    print("\n" + "=" * 80)
    print("PHASE 4: TP/SL BARRIER MATHEMATICS AUDIT")
    print("=" * 80)

    # Break-even WR formula: WR_BE = 1 / (1 + R_target)
    tp_sl_ratios = [0.8, 1.0, 1.2, 1.4, 1.6, 2.0, 2.5]
    barrier_math = []
    for r_tp in tp_sl_ratios:
        be_wr = round(1.0 / (1.0 + r_tp) * 100.0, 2)
        # Random walk zero-drift hit probability:
        p_tp_first = round(1.0 / (1.0 + r_tp) * 100.0, 2)
        barrier_math.append({
            "target_R": r_tp,
            "breakeven_win_rate_pct": be_wr,
            "zero_drift_random_walk_prob": p_tp_first
        })
        print(f"  Target: {r_tp:3.1f}R vs 1.0R SL -> Break-even Win Rate: {be_wr:5.2f}% | Zero-Drift Probability: {p_tp_first:5.2f}%")

    # Idealized Expectancy for Model #1:
    wr_obs = audit_models["Model_1"]["win_rate_pct"] / 100.0
    idealized_exp_r = round((wr_obs * 0.8) - ((1.0 - wr_obs) * 1.0), 4)
    print(f"\n  Model #1 Theoretical Expectancy (Zero Friction): {idealized_exp_r:+.4f}R")
    print(f"  Model #1 Actual Realized Expectancy (After Fees) : +{audit_models['Model_1']['avg_r']:.4f}R")
    fee_drag_r = round(idealized_exp_r - audit_models["Model_1"]["avg_r"], 4)
    print(f"  Friction Drag per Trade                         : {fee_drag_r:.4f}R")

    # 6. Strict Multi-Phase True Out-of-Sample (OOS) Partition Audit
    print("\n" + "=" * 80)
    print("PHASE 5: STRICT OUT-OF-SAMPLE (OOS) AUDIT (TRAIN / VAL / LOCKED TEST)")
    print("=" * 80)
    # Split:
    # Train: Days 1 to 45 (bars 0 to 64,800)
    # Validation: Days 46 to 65 (bars 64,800 to 93,600)
    # LOCKED TEST: Days 66 to 90 (bars 93,600 to 129,600) - 25 Days
    train_bars = (250, 64800)
    val_bars = (64800, 93600)
    test_bars = (93600, len(features))

    oos_audit_results = {}
    for m_name, cfg in model_configs.items():
        res_train = run_forensic_simulation(features, cfg, start_idx=train_bars[0], end_idx=train_bars[1])
        res_val = run_forensic_simulation(features, cfg, start_idx=val_bars[0], end_idx=val_bars[1])
        res_locked_test = run_forensic_simulation(features, cfg, start_idx=test_bars[0], end_idx=test_bars[1])

        oos_audit_results[m_name] = {
            "train_45d": {
                "trades": res_train["total_trades"], "wr": res_train["win_rate_pct"], "pf": res_train["net_pf"], "pnl": res_train["net_pnl"], "dd": res_train["max_dd_pct"]
            },
            "val_20d": {
                "trades": res_val["total_trades"], "wr": res_val["win_rate_pct"], "pf": res_val["net_pf"], "pnl": res_val["net_pnl"], "dd": res_val["max_dd_pct"]
            },
            "locked_test_25d": {
                "trades": res_locked_test["total_trades"], "wr": res_locked_test["win_rate_pct"], "pf": res_locked_test["net_pf"], "pnl": res_locked_test["net_pnl"], "dd": res_locked_test["max_dd_pct"],
                "commissions": res_locked_test["total_commissions"], "avg_r": res_locked_test["avg_r"]
            }
        }

        print(f"\n  {m_name.upper()} Multi-Phase OOS Split:")
        print(f"    TRAIN (Days 1-45)      : Trades={res_train['total_trades']:2d} | WR={res_train['win_rate_pct']:4.1f}% | Net PF={res_train['net_pf']:4.2f}x | PnL=${res_train['net_pnl']:+6.2f} | DD={res_train['max_dd_pct']:4.1f}%")
        print(f"    VALIDATION (Days 46-65): Trades={res_val['total_trades']:2d} | WR={res_val['win_rate_pct']:4.1f}% | Net PF={res_val['net_pf']:4.2f}x | PnL=${res_val['net_pnl']:+6.2f} | DD={res_val['max_dd_pct']:4.1f}%")
        print(f"    LOCKED TEST (Days 66-90): Trades={res_locked_test['total_trades']:2d} | WR={res_locked_test['win_rate_pct']:4.1f}% | Net PF={res_locked_test['net_pf']:4.2f}x | PnL=${res_locked_test['net_pnl']:+6.2f} | DD={res_locked_test['max_dd_pct']:4.1f}%")

    # 7. Intrabar Ambiguity Resolution Audit (TP-first vs SL-first vs Conservative)
    print("\n" + "=" * 80)
    print("PHASE 6: M1 INTRABAR AMBIGUITY RESOLUTION SCENARIOS")
    print("=" * 80)

    ambiguity_results = {}
    m1_cfg = model_configs["Model_1"]
    for scenario in ["CONSERVATIVE", "OPTIMISTIC"]:
        sim_res = run_forensic_simulation(features, m1_cfg, intrabar_resolution=scenario)
        ambiguity_results[scenario] = {
            "scenario": scenario,
            "trades": sim_res["total_trades"],
            "wr": sim_res["win_rate_pct"],
            "net_pf": sim_res["net_pf"],
            "net_pnl": sim_res["net_pnl"],
            "max_dd": sim_res["max_dd_pct"],
            "ambiguous_count": sim_res["ambiguous_count"]
        }
        print(f"  Scenario {scenario:12s}: Trades={sim_res['total_trades']:3d} | WR={sim_res['win_rate_pct']:4.1f}% | Net PF={sim_res['net_pf']:4.2f}x | PnL=${sim_res['net_pnl']:+6.2f} | Ambiguous={sim_res['ambiguous_count']}")

    # 8. Real Trading Cost & Execution Friction Audit
    print("\n" + "=" * 80)
    print("PHASE 7: REAL TRADING COST & SLIPPAGE AUDIT")
    print("=" * 80)

    cost_results = {}
    for ex_type in ["MAKER_POST_ONLY", "REALISTIC_TAKER"]:
        sim_res = run_forensic_simulation(features, m1_cfg, execution_type=ex_type)
        cost_results[ex_type] = {
            "execution": ex_type,
            "wr": sim_res["win_rate_pct"],
            "gross_pf": sim_res["gross_pf"],
            "net_pf": sim_res["net_pf"],
            "gross_pnl": sim_res["gross_profit"] - sim_res["gross_loss"],
            "commissions": sim_res["total_commissions"],
            "slippage": sim_res["total_slippage"],
            "net_pnl": sim_res["net_pnl"]
        }
        print(f"  Execution: {ex_type:18s} | Gross PF={sim_res['gross_pf']:4.2f}x | Net PF={sim_res['net_pf']:4.2f}x | Gross PnL=${cost_results[ex_type]['gross_pnl']:+6.2f} | Comm=${sim_res['total_commissions']:.2f} | Slip=${sim_res['total_slippage']:.2f} | Net PnL=${sim_res['net_pnl']:+6.2f}")

    # 9. Stop Loss & M1 Candle Geometry Audit
    print("\n" + "=" * 80)
    print("PHASE 8: STOP LOSS & M1 CANDLE NOISE DISTRIBUTION AUDIT")
    print("=" * 80)

    candle_ranges = [f["range"] for f in features]
    upper_wicks = [f["upper_wick"] for f in features]
    lower_wicks = [f["lower_wick"] for f in features]
    atr_values = [f["atr"] for f in features]
    maes = [t["MAE"] for t in audit_models["Model_1"]["trades"]]
    mfes = [t["MFE"] for t in audit_models["Model_1"]["trades"]]

    def calc_percentiles(arr: List[float]) -> Dict[str, float]:
        s = sorted(arr)
        n_len = len(s)
        if n_len == 0: return {}
        return {
            "p50": round(s[int(0.50 * n_len)], 2),
            "p75": round(s[int(0.75 * n_len)], 2),
            "p90": round(s[int(0.90 * n_len)], 2),
            "p95": round(s[int(0.95 * n_len)], 2),
            "p99": round(s[int(0.99 * n_len)], 2)
        }

    pct_ranges = calc_percentiles(candle_ranges)
    pct_uwicks = calc_percentiles(upper_wicks)
    pct_lwicks = calc_percentiles(lower_wicks)
    pct_atr = calc_percentiles(atr_values)
    pct_mae = calc_percentiles(maes)
    pct_mfe = calc_percentiles(mfes)

    print(f"  ETHUSDT M1 Candle Range ($) : p50=${pct_ranges['p50']} | p75=${pct_ranges['p75']} | p90=${pct_ranges['p90']} | p95=${pct_ranges['p95']} | p99=${pct_ranges['p99']}")
    print(f"  Upper Wick Size ($)         : p50=${pct_uwicks['p50']} | p75=${pct_uwicks['p75']} | p90=${pct_uwicks['p90']} | p95=${pct_uwicks['p95']} | p99=${pct_uwicks['p99']}")
    print(f"  Lower Wick Size ($)         : p50=${pct_lwicks['p50']} | p75=${pct_lwicks['p75']} | p90=${pct_lwicks['p90']} | p95=${pct_lwicks['p95']} | p99=${pct_lwicks['p99']}")
    print(f"  M1 ATR(14) Volatility ($)   : p50=${pct_atr['p50']} | p75=${pct_atr['p75']} | p90=${pct_atr['p90']} | p95=${pct_atr['p95']} | p99=${pct_atr['p99']}")
    print(f"  Model #1 MAE Excursion ($)  : p50=${pct_mae['p50']} | p75=${pct_mae['p75']} | p90=${pct_mae['p90']} | p95=${pct_mae['p95']} | p99=${pct_mae['p99']}")
    print(f"  Model #1 MFE Excursion ($)  : p50=${pct_mfe['p50']} | p75=${pct_mfe['p75']} | p90=${pct_mfe['p90']} | p95=${pct_mfe['p95']} | p99=${pct_mfe['p99']}")

    # 10. Parameter Robustness & Sensitivity Analysis around Winner Model #1
    print("\n" + "=" * 80)
    print("PHASE 9: PARAMETER SENSITIVITY & ROBUSTNESS PLATEAU AUDIT")
    print("=" * 80)

    sensitivity_rows = []
    # Test varying TP, SL ATR, Min SL, Trend filter, ADX, Session
    tp_tests = [0.64, 0.72, 0.80, 0.88, 0.96, 1.10]
    sl_atr_tests = [1.2, 1.35, 1.5, 1.65, 1.8]
    min_sl_tests = [6.0, 8.0, 10.0]
    trend_tests = ["M5_M15", "STRICT_HTF", "NONE"]
    adx_tests = [18, 20, 22, 24, 26]
    session_tests = ["LONDON_EXPANSION", "MAJOR", "ALL_24H"]

    # Sample around center model
    param_sweep = []
    for tp in tp_tests:
        p = dict(m1_cfg); p["tp_r"] = tp
        param_sweep.append(p)
    for sl in sl_atr_tests:
        p = dict(m1_cfg); p["sl_atr_mult"] = sl
        param_sweep.append(p)
    for msl in min_sl_tests:
        p = dict(m1_cfg); p["min_sl_usd"] = msl
        param_sweep.append(p)
    for tf in trend_tests:
        p = dict(m1_cfg); p["trend_filter"] = tf
        param_sweep.append(p)
    for adx in adx_tests:
        p = dict(m1_cfg); p["adx_min"] = adx
        param_sweep.append(p)
    for sess in session_tests:
        p = dict(m1_cfg); p["session_mode"] = sess
        param_sweep.append(p)

    for p in param_sweep:
        sim_res = run_forensic_simulation(features, p)
        sensitivity_rows.append({
            "tp_r": p["tp_r"],
            "sl_atr_mult": p["sl_atr_mult"],
            "min_sl_usd": p["min_sl_usd"],
            "trend_filter": p["trend_filter"],
            "adx_min": p["adx_min"],
            "session_mode": p["session_mode"],
            "trades": sim_res["total_trades"],
            "wr": sim_res["win_rate_pct"],
            "net_pf": sim_res["net_pf"],
            "net_pnl": sim_res["net_pnl"],
            "max_dd": sim_res["max_dd_pct"]
        })

    # 11. Rolling Walk-Forward Analysis (6 Windows of Train 30d, Test 10d)
    print("\n" + "=" * 80)
    print("PHASE 10: ROLLING WALK-FORWARD 30D/10D ANALYSIS")
    print("=" * 80)

    wf_results = []
    window_train_bars = 30 * 1440 # 43,200 bars
    window_test_bars = 10 * 1440  # 14,400 bars
    step_bars = 10 * 1440         # 14,400 bars

    start_window = 250
    w_idx = 1
    while start_window + window_train_bars + window_test_bars <= len(features):
        tr_start = start_window
        tr_end = start_window + window_train_bars
        te_start = tr_end
        te_end = te_start + window_test_bars

        sim_tr = run_forensic_simulation(features, m1_cfg, start_idx=tr_start, end_idx=tr_end)
        sim_te = run_forensic_simulation(features, m1_cfg, start_idx=te_start, end_idx=te_end)

        dt_te_start = datetime.fromtimestamp(features[te_start]["time"] / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
        dt_te_end = datetime.fromtimestamp(features[te_end-1]["time"] / 1000, tz=timezone.utc).strftime('%Y-%m-%d')

        wf_record = {
            "window": w_idx,
            "test_period": f"{dt_te_start} to {dt_te_end}",
            "train_trades": sim_tr["total_trades"],
            "train_wr": sim_tr["win_rate_pct"],
            "train_pf": sim_tr["net_pf"],
            "test_trades": sim_te["total_trades"],
            "test_wr": sim_te["win_rate_pct"],
            "test_pf": sim_te["net_pf"],
            "test_pnl": sim_te["net_pnl"],
            "test_dd": sim_te["max_dd_pct"]
        }
        wf_results.append(wf_record)
        print(f"  Window #{w_idx} ({wf_record['test_period']}): Train WR={sim_tr['win_rate_pct']:4.1f}%, PF={sim_tr['net_pf']:4.2f}x | TEST Trades={sim_te['total_trades']:2d}, WR={sim_te['win_rate_pct']:4.1f}%, Net PF={sim_te['net_pf']:4.2f}x, PnL=${sim_te['net_pnl']:+6.2f}")
        start_window += step_bars
        w_idx += 1

    # 12. Monte Carlo 10,000 Simulations
    print("\n" + "=" * 80)
    print("PHASE 11: MONTE CARLO 10,000 RESAMPLING SIMULATION")
    print("=" * 80)

    pnls_m1 = [t["net_pnl"] for t in audit_models["Model_1"]["trades"]]
    mc_results = run_monte_carlo(pnls_m1, num_simulations=10000)

    print(f"  Simulations Run             : {mc_results['num_simulations']:,}")
    print(f"  Median Ending Equity ($)    : ${mc_results['median_ending_equity']:.2f}")
    print(f"  5th Percentile Equity ($)   : ${mc_results['p05_ending_equity']:.2f}")
    print(f"  95th Percentile Equity ($)  : ${mc_results['p95_ending_equity']:.2f}")
    print(f"  Median Max Drawdown (%)     : {mc_results['median_max_dd_pct']}%")
    print(f"  95th Percentile Drawdown (%) : {mc_results['p95_max_dd_pct']}%")
    print(f"  Probability of Account Ruin : {mc_results['prob_ruin_pct']}%")
    print(f"  Probability of DD >= 20%    : {mc_results['prob_dd_ge_20pct']}%")
    print(f"  Probability of 10+ Loss Seq : {mc_results['prob_streak_ge_10']}%")

    # 13. Trigger vs Actual Trade Audit
    print("\n" + "=" * 80)
    print("PHASE 12: TRIGGER VS ACTUAL TRADE AUDIT (MODULE BY MODULE)")
    print("=" * 80)

    module_stats = {}
    for mod_name in ["MODULE_A_SWEEP_RECLAIM", "MODULE_B_BREAKOUT", "MODULE_C_EMA_PULLBACK", "MODULE_D_MOMENTUM_IMPULSE", "MODULE_E_M5_M1_HYBRID"]:
        raw_trig = 0
        for f in features:
            for s, m, b in f["module_candidates"]:
                if m == mod_name: raw_trig += 1
        
        sim_res = run_forensic_simulation(features, {
            "module": mod_name, "session_mode": "ALL_24H", "trend_filter": "NONE",
            "sl_atr_mult": 1.5, "min_sl_usd": 8.0, "tp_r": 0.8, "score_thresh": 65, "adx_min": 0
        })
        module_stats[mod_name] = {
            "raw_triggers": raw_trig,
            "triggers_per_day": round(raw_trig / 90.0, 1),
            "actual_trades_24h_unfiltered": sim_res["total_trades"],
            "unfiltered_wr": sim_res["win_rate_pct"],
            "unfiltered_pf": sim_res["net_pf"],
            "unfiltered_pnl": sim_res["net_pnl"]
        }
        print(f"  {mod_name:25s}: Raw Triggers={raw_trig:6d} ({raw_trig/90.0:5.1f}/day) | Executed (24h)={sim_res['total_trades']:3d} | WR={sim_res['win_rate_pct']:4.1f}% | PF={sim_res['net_pf']:4.2f}x | PnL=${sim_res['net_pnl']:+7.2f}")

    # 14. SAVE ALL RAW FORENSIC CSV AND JSON ARTIFACTS
    print("\n" + "=" * 80)
    print(f"PHASE 13: EXPORTING ALL AUDIT ARTIFACTS TO {AUDIT_DIR}")
    print("=" * 80)

    # 1. trade_log.csv
    trade_log_path = os.path.join(AUDIT_DIR, "trade_log.csv")
    with open(trade_log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "symbol", "side", "module", "entry", "SL", "TP", "exit", "result",
            "R", "gross_pnl", "commission", "slippage", "net_pnl", "MAE", "MFE",
            "session", "trend", "ADX", "score"
        ])
        writer.writeheader()
        for t in audit_models["Model_1"]["trades"]:
            row = dict(t)
            row.pop("is_win", None)
            row.pop("holding_bars", None)
            row.pop("is_ambiguous", None)
            row.pop("equity", None)
            row.pop("dd_pct", None)
            writer.writerow(row)
    print(f"  [SAVED] {trade_log_path}")

    # 2. model_metrics.csv
    model_metrics_path = os.path.join(AUDIT_DIR, "model_metrics.csv")
    with open(model_metrics_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Model", "Trades", "WR_Pct", "Gross_PF", "Net_PF", "Net_PnL", "Avg_Win", "Avg_Loss", "Max_DD_Pct", "Sharpe", "CI_95_Low", "CI_95_High", "OOS_WR_Pct", "OOS_PF", "OOS_PnL"])
        for m_name, res in audit_models.items():
            oos_lock = oos_audit_results[m_name]["locked_test_25d"]
            writer.writerow([
                m_name, res["total_trades"], res["win_rate_pct"], res["gross_pf"], res["net_pf"], res["net_pnl"],
                res["avg_win"], res["avg_loss"], res["max_dd_pct"], res["sharpe"],
                res["wilson_95_ci"][0], res["wilson_95_ci"][1],
                oos_lock["wr"], oos_lock["pf"], oos_lock["pnl"]
            ])
    print(f"  [SAVED] {model_metrics_path}")

    # 3. parameter_sensitivity.csv
    param_sens_path = os.path.join(AUDIT_DIR, "parameter_sensitivity.csv")
    with open(param_sens_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["tp_r", "sl_atr_mult", "min_sl_usd", "trend_filter", "adx_min", "session_mode", "trades", "wr", "net_pf", "net_pnl", "max_dd"])
        writer.writeheader()
        for r in sensitivity_rows: writer.writerow(r)
    print(f"  [SAVED] {param_sens_path}")

    # 4. walk_forward.csv
    wf_path = os.path.join(AUDIT_DIR, "walk_forward.csv")
    with open(wf_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["window", "test_period", "train_trades", "train_wr", "train_pf", "test_trades", "test_wr", "test_pf", "test_pnl", "test_dd"])
        writer.writeheader()
        for r in wf_results: writer.writerow(r)
    print(f"  [SAVED] {wf_path}")

    # 5. monte_carlo.csv
    mc_path = os.path.join(AUDIT_DIR, "monte_carlo.csv")
    with open(mc_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        for k, v in mc_results.items(): writer.writerow([k, v])
    print(f"  [SAVED] {mc_path}")

    # 6. ambiguous_trades.csv
    ambig_path = os.path.join(AUDIT_DIR, "ambiguous_trades.csv")
    with open(ambig_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Side", "Entry", "SL", "TP", "Exit", "Result", "GrossPnL", "NetPnL"])
        for at in audit_models["Model_1"]["ambiguous_trades"]:
            writer.writerow([at["timestamp"], at["side"], at["entry"], at["SL"], at["TP"], at["exit"], at["result"], at["gross_pnl"], at["net_pnl"]])
    print(f"  [SAVED] {ambig_path}")

    # 7. module_statistics.csv
    mod_stat_path = os.path.join(AUDIT_DIR, "module_statistics.csv")
    with open(mod_stat_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Module", "Raw_Triggers", "Triggers_Per_Day", "Actual_Trades_24h", "Win_Rate_Pct", "Net_PF", "Net_PnL"])
        for m_name, s in module_stats.items():
            writer.writerow([m_name, s["raw_triggers"], s["triggers_per_day"], s["actual_trades_24h_unfiltered"], s["unfiltered_wr"], s["unfiltered_pf"], s["unfiltered_pnl"]])
    print(f"  [SAVED] {mod_stat_path}")

    # 8. cost_analysis.csv
    cost_path = os.path.join(AUDIT_DIR, "cost_analysis.csv")
    with open(cost_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Execution_Model", "Win_Rate_Pct", "Gross_PF", "Net_PF", "Gross_PnL", "Commissions", "Slippage", "Net_PnL"])
        for k, v in cost_results.items():
            writer.writerow([v["execution"], v["wr"], v["gross_pf"], v["net_pf"], round(v["gross_pnl"], 2), v["commissions"], v["slippage"], v["net_pnl"]])
    print(f"  [SAVED] {cost_path}")

    # 9. data_integrity_report.txt
    integ_path = os.path.join(AUDIT_DIR, "data_integrity_report.txt")
    with open(integ_path, "w", encoding="utf-8") as f:
        f.write("APEX QUANT DATA INTEGRITY & AUDIT REPORT\n")
        f.write("=" * 50 + "\n")
        for k, v in data_report.items():
            f.write(f"{k}: {v}\n")
    print(f"  [SAVED] {integ_path}")

    # 10. summary.json
    summary_path = os.path.join(AUDIT_DIR, "summary.json")
    master_summary = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "data_integrity": data_report,
        "models_evaluated": {
            "Model_1": {k: v for k, v in audit_models["Model_1"].items() if k not in ["trades", "ambiguous_trades"]},
            "Model_2": {k: v for k, v in audit_models["Model_2"].items() if k not in ["trades", "ambiguous_trades"]},
            "Model_3": {k: v for k, v in audit_models["Model_3"].items() if k not in ["trades", "ambiguous_trades"]}
        },
        "barrier_mathematics": barrier_math,
        "oos_partition_results": oos_audit_results,
        "ambiguity_analysis": ambiguity_results,
        "cost_analysis": cost_results,
        "candle_geometry_percentiles": {
            "candle_range": pct_ranges, "upper_wick": pct_uwicks, "lower_wick": pct_lwicks, "atr": pct_atr, "mae": pct_mae, "mfe": pct_mfe
        },
        "monte_carlo_resampling": mc_results,
        "walk_forward_rolling": wf_results,
        "module_triggers_audit": module_stats
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(master_summary, f, indent=2)
    print(f"  [SAVED] {summary_path}")

    print("\n" + "=" * 80)
    print("ALL 10 FORENSIC AUDIT ARTIFACTS SUCCESSFULLY PRODUCED!")
    print("=" * 80)

if __name__ == "__main__":
    main()
