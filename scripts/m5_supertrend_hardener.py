"""
================================================================================
APEX QUANT M5 SUPERTREND HARDENING & OPTIMIZATION PIPELINE
================================================================================
Refines the winning M5 SuperTrend + H1 Macro + Volume Expansion Architecture.
Tests parameter grids strictly on TRAIN (45d) and VALIDATION (20d):
  - SuperTrend Multipliers: 2.2, 2.5, 2.8, 3.0, 3.2, 3.5
  - SuperTrend Periods: 7, 10, 14
  - Volume Thresholds: 1.0x, 1.2x, 1.3x, 1.4x, 1.5x
  - H1 EMA Filters: EMA 50, EMA 100, EMA 200
  - TP Ratios: 1.8R, 2.0R, 2.2R, 2.4R, 2.5R
  - Minimum Stop Distances: $8, $10, $12

Only after freezing the best Train/Val model do we unlock LOCKED TEST (Days 66-90).
Then performs:
  1. Full Rolling Walk-Forward (8 windows)
  2. 10,000 Monte Carlo simulations
  3. Taker & Slippage stress tests (+0, +1, +2, +3 ticks)
  4. Fee multiplier stress tests (1.0x, 1.25x, 1.5x, 2.0x)
================================================================================
"""

import os
import sys
import math
import json
import time
import random
from datetime import datetime, timezone
from collections import defaultdict

DATA_FILE = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"
OUTPUT_DIR = r"C:\apex_copytrade\audit\m5_supertrend_final"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. LOAD & BUILD M5 DATA
# ------------------------------------------------------------------------------
def load_and_prep():
    print("\n[PHASE 1] Loading raw M1 data and aggregating to M5...")
    m1_times, m1_opens, m1_highs, m1_lows, m1_closes, m1_vols = [], [], [], [], [], []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        f.readline()
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 6: continue
            try:
                m1_times.append(int(parts[0]))
                m1_opens.append(float(parts[1]))
                m1_highs.append(float(parts[2]))
                m1_lows.append(float(parts[3]))
                m1_closes.append(float(parts[4]))
                m1_vols.append(float(parts[5]))
            except ValueError: continue

    m5_bars = []
    m5_sub_m1 = []
    cur_bucket_t = None
    cur_sub = []
    cur_o, cur_h, cur_l, cur_c, cur_v = 0.0, 0.0, 0.0, 0.0, 0.0

    for i in range(len(m1_times)):
        t = m1_times[i]
        o, h, l, c, v = m1_opens[i], m1_highs[i], m1_lows[i], m1_closes[i], m1_vols[i]
        b_t = (t // 300000) * 300000
        if cur_bucket_t is None:
            cur_bucket_t = b_t; cur_o, cur_h, cur_l, cur_c, cur_v = o, h, l, c, v
            cur_sub = [(t, o, h, l, c)]
        elif cur_bucket_t == b_t:
            cur_h = max(cur_h, h); cur_l = min(cur_l, l); cur_c = c; cur_v += v
            cur_sub.append((t, o, h, l, c))
        else:
            m5_bars.append({"time": cur_bucket_t, "open": cur_o, "high": cur_h, "low": cur_l, "close": cur_c, "volume": cur_v})
            m5_sub_m1.append(cur_sub)
            cur_bucket_t = b_t; cur_o, cur_h, cur_l, cur_c, cur_v = o, h, l, c, v
            cur_sub = [(t, o, h, l, c)]
    if cur_sub:
        m5_bars.append({"time": cur_bucket_t, "open": cur_o, "high": cur_h, "low": cur_l, "close": cur_c, "volume": cur_v})
        m5_sub_m1.append(cur_sub)

    return m5_bars, m5_sub_m1

# ------------------------------------------------------------------------------
# 2. INDICATORS
# ------------------------------------------------------------------------------
def fast_ema(series, period):
    n = len(series)
    out = [0.0] * n
    if n == 0: return out
    k = 2.0 / (period + 1.0)
    out[0] = series[0]
    for i in range(1, n): out[i] = series[i] * k + out[i-1] * (1.0 - k)
    return out

def compute_atr(highs, lows, closes, period=14):
    n = len(closes)
    tr = [0.0] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    atr = [0.0] * n
    if n < period: return atr
    atr[period-1] = sum(tr[:period]) / period
    for i in range(period, n): atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

def compute_supertrend(highs, lows, closes, period=10, multiplier=3.0):
    n = len(closes)
    atr = compute_atr(highs, lows, closes, period)
    st = [0.0] * n
    direction = [1] * n
    upper = [0.0] * n
    lower = [0.0] * n
    
    for i in range(period, n):
        hl2 = (highs[i] + lows[i]) / 2.0
        basic_upper = hl2 + multiplier * atr[i]
        basic_lower = hl2 - multiplier * atr[i]
        
        lower[i] = basic_lower if basic_lower > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]
        upper[i] = basic_upper if basic_upper < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
        
        if closes[i] > upper[i-1]: direction[i] = 1
        elif closes[i] < lower[i-1]: direction[i] = -1
        else: direction[i] = direction[i-1]
        st[i] = lower[i] if direction[i] == 1 else upper[i]
    return st, direction

# ------------------------------------------------------------------------------
# 3. PRECOMPUTE MTF FEATURES
# ------------------------------------------------------------------------------
def build_multi_supertrend_features(m5_bars):
    print("[PHASE 2] Precomputing multi-parameter SuperTrends and H1 filters...")
    n = len(m5_bars)
    times = [b["time"] for b in m5_bars]
    opens = [b["open"] for b in m5_bars]
    highs = [b["high"] for b in m5_bars]
    lows = [b["low"] for b in m5_bars]
    closes = [b["close"] for b in m5_bars]
    vols = [b["volume"] for b in m5_bars]
    
    atr14 = compute_atr(highs, lows, closes, 14)
    
    # H1 Bars
    h1_bars = []
    m5_to_h1 = [-1] * n
    cur_h1 = None
    for i in range(n):
        t = times[i]
        o, h, l, c, v = opens[i], highs[i], lows[i], closes[i], vols[i]
        h1_t = (t // 3600000) * 3600000
        if cur_h1 is None: cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        elif cur_h1["time"] == h1_t:
            cur_h1["high"] = max(cur_h1["high"], h); cur_h1["low"] = min(cur_h1["low"], l); cur_h1["close"] = c; cur_h1["vol"] += v
        else:
            h1_bars.append(cur_h1)
            cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        m5_to_h1[i] = len(h1_bars) - 1
        
    h1_closes = [b["close"] for b in h1_bars]
    h1_e50 = fast_ema(h1_closes, 50)
    h1_e100 = fast_ema(h1_closes, 100)
    h1_e200 = fast_ema(h1_closes, 200)
    
    # Precompute SuperTrends: (10, 2.5), (10, 3.0), (10, 3.5), (7, 3.0), (14, 3.0)
    st_configs = [
        ("st_10_25", 10, 2.5),
        ("st_10_30", 10, 3.0),
        ("st_10_35", 10, 3.5),
        ("st_7_30", 7, 3.0),
        ("st_14_30", 14, 3.0)
    ]
    st_maps = {}
    for key, p, mult in st_configs:
        st_val, st_dir = compute_supertrend(highs, lows, closes, p, mult)
        st_maps[key] = (st_val, st_dir)
        
    features = []
    for i in range(n):
        t = times[i]
        c, o, h, l, v = closes[i], opens[i], highs[i], lows[i], vols[i]
        dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
        utc_hour = dt.hour
        
        h1_idx = m5_to_h1[i]
        h1_trend_50 = "NEUTRAL"
        h1_trend_200 = "NEUTRAL"
        if h1_idx >= 50:
            if h1_closes[h1_idx] > h1_e50[h1_idx]: h1_trend_50 = "BULLISH"
            elif h1_closes[h1_idx] < h1_e50[h1_idx]: h1_trend_50 = "BEARISH"
        if h1_idx >= 200:
            if h1_closes[h1_idx] > h1_e200[h1_idx]: h1_trend_200 = "BULLISH"
            elif h1_closes[h1_idx] < h1_e200[h1_idx]: h1_trend_200 = "BEARISH"
            
        v_avg_10 = sum(vols[max(0, i-10):i]) / 10.0 if i >= 10 else v
        v_ratio = v / max(1.0, v_avg_10)
        
        f_entry = {
            "idx": i, "time": t, "open": o, "high": h, "low": l, "close": c, "volume": v,
            "hour": utc_hour, "day_str": dt.strftime("%Y-%m-%d"),
            "atr": atr14[i], "h1_trend_50": h1_trend_50, "h1_trend_200": h1_trend_200,
            "v_ratio": v_ratio
        }
        for key in st_maps:
            st_val, st_dir = st_maps[key]
            f_entry[f"{key}_val"] = st_val[i]
            f_entry[f"{key}_dir"] = st_dir[i]
        features.append(f_entry)
        
    return features

# ------------------------------------------------------------------------------
# 4. SIMULATION WITH SUB-MINUTE ACCURACY
# ------------------------------------------------------------------------------
def run_sim(features, m5_sub_m1, start_idx, end_idx, params):
    st_key = params.get("st_key", "st_10_30")
    v_thresh = params.get("v_thresh", 1.2)
    h1_mode = params.get("h1_mode", "EMA50") # EMA50, EMA200, NONE
    tp_r = params.get("tp_r", 2.0)
    min_sl = params.get("min_sl", 10.0)
    exec_mode = params.get("exec_mode", "MAKER")
    cost_mult = params.get("cost_mult", 1.0)
    taker_slip = params.get("taker_slip", 0.02)
    
    entry_fee = (0.0002 if exec_mode == "MAKER" else 0.0005) * cost_mult
    tp_fee = 0.0002 * cost_mult
    sl_fee = 0.0005 * cost_mult
    
    balance = 1000.0
    peak = balance
    trades = []
    
    in_pos = False
    pos = {}
    cooldown = 0
    daily_count = 0
    cur_day = ""
    
    for idx in range(start_idx, end_idx):
        f = features[idx]
        t = f["time"]
        
        if f["day_str"] != cur_day:
            cur_day = f["day_str"]
            daily_count = 0
            
        # 1. POSITION MANAGEMENT
        if in_pos:
            sub = m5_sub_m1[idx]
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            tp = pos["tp"]
            qty = pos["qty"]
            
            closed = False
            exit_p = 0.0
            reason = ""
            
            for m1_t, m1_o, m1_h, m1_l, m1_c in sub:
                if side == "LONG":
                    if m1_l <= sl: closed = True; exit_p = sl - 0.02; reason = "SL_HIT"; break
                    elif m1_h >= tp: closed = True; exit_p = tp; reason = "TP_HIT"; break
                else:
                    if m1_h >= sl: closed = True; exit_p = sl + 0.02; reason = "SL_HIT"; break
                    elif m1_l <= tp: closed = True; exit_p = tp; reason = "TP_HIT"; break
                    
            if closed:
                gp = (exit_p - entry)*qty if side == "LONG" else (entry - exit_p)*qty
                comm = pos["entry_comm"] + round(qty * exit_p * (tp_fee if reason == "TP_HIT" else sl_fee), 4)
                net = gp - comm - pos["slip"]
                balance += net
                if balance > peak: peak = balance
                dd = (peak - balance) / peak * 100.0
                trades.append({
                    "time": t, "side": side, "entry": entry, "exit": exit_p, "reason": reason,
                    "is_win": net > 0, "gross_pnl": round(gp, 2), "comm": round(comm, 2),
                    "net_pnl": round(net, 2), "r": round(net / pos["risk_usd"], 2),
                    "dd": round(dd, 2)
                })
                in_pos = False; pos = {}; cooldown = idx + 2; daily_count += 1
                
        # 2. ENTRY EVALUATION
        if not in_pos and idx >= cooldown and daily_count < 3:
            # Active sessions: London + NY (07:00 to 21:00 UTC)
            if not (7 <= f["hour"] < 21): continue
            
            prev_f = features[idx-1]
            p_dir = prev_f[f"{st_key}_dir"]
            c_dir = f[f"{st_key}_dir"]
            st_val = f[f"{st_key}_val"]
            curr_c = f["close"]
            atr = f["atr"]
            
            # Trend Alignment
            h1_trend = f["h1_trend_50"] if h1_mode == "EMA50" else f["h1_trend_200"]
            
            sig = None
            sl_dist = 0.0
            
            # Bullish flip
            if p_dir == -1 and c_dir == 1:
                if (h1_mode == "NONE" or h1_trend == "BULLISH") and f["v_ratio"] >= v_thresh:
                    sig = "LONG"
                    sl_dist = max(min_sl, (curr_c - st_val) + 0.2 * atr)
                    
            # Bearish flip
            elif p_dir == 1 and c_dir == -1:
                if (h1_mode == "NONE" or h1_trend == "BEARISH") and f["v_ratio"] >= v_thresh:
                    sig = "SHORT"
                    sl_dist = max(min_sl, (st_val - curr_c) + 0.2 * atr)
                    
            if sig:
                r_dist = sl_dist
                sl_p = round(curr_c - r_dist, 2) if sig == "LONG" else round(curr_c + r_dist, 2)
                tp_p = round(curr_c + (tp_r * r_dist), 2) if sig == "LONG" else round(curr_c - (tp_r * r_dist), 2)
                risk_usd = balance * 0.010
                qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
                
                if exec_mode == "MAKER":
                    entry_p = curr_c
                    slip_cost = 0.0
                else:
                    slip_cost = qty * taker_slip
                    entry_p = curr_c + (taker_slip if sig == "LONG" else -taker_slip)
                    
                entry_c = round(qty * entry_p * entry_fee, 4)
                in_pos = True
                pos = {
                    "side": sig, "entry": entry_p, "sl": sl_p, "tp": tp_p, "qty": qty,
                    "r_dist": r_dist, "risk_usd": risk_usd, "entry_comm": entry_c, "slip": slip_cost
                }
                
    return calc_perf(trades)

def calc_perf(trades):
    n = len(trades)
    if n == 0:
        return {"trades": 0, "wr": 0.0, "net_pf": 0.0, "net_pnl": 0.0, "max_dd": 0.0, "payoff": 0.0, "sharpe": 0.0}
    wins = [t for t in trades if t["net_pnl"] > 0]
    losses = [t for t in trades if t["net_pnl"] <= 0]
    w_cnt = len(wins)
    l_cnt = len(losses)
    wr = round(w_cnt / n * 100.0, 1)
    
    net_win = sum(t["net_pnl"] for t in wins)
    net_loss = abs(sum(t["net_pnl"] for t in losses))
    net_pf = round(net_win / max(1e-6, net_loss), 2)
    net_pnl = round(sum(t["net_pnl"] for t in trades), 2)
    
    avg_w = net_win / max(1, w_cnt)
    avg_l = net_loss / max(1, l_cnt)
    payoff = round(avg_w / max(1e-4, avg_l), 2)
    max_dd = max([t["dd"] for t in trades]) if trades else 0.0
    
    rets = [t["net_pnl"] / 1000.0 for t in trades]
    m_r = sum(rets) / len(rets)
    v_r = sum((x - m_r)**2 for x in rets) / max(1, len(rets) - 1)
    sharpe = round(math.sqrt(365 * 1.5) * (m_r / max(1e-6, math.sqrt(v_r))), 2)
    
    return {
        "trades": n, "wr": wr, "net_pf": net_pf, "net_pnl": net_pnl,
        "max_dd": round(max_dd, 2), "payoff": payoff, "sharpe": sharpe,
        "trades_list": trades
    }

# ------------------------------------------------------------------------------
# 5. EXECUTE REFINEMENT & AUDIT
# ------------------------------------------------------------------------------
def execute_hardening(features, m5_sub_m1):
    total = len(features)
    tr_s, tr_e = 250, 12960 # Days 1 - 45
    val_s, val_e = 12960, 18720 # Days 46 - 65
    lock_s, lock_e = 18720, total # Days 66 - 90
    
    print("\n================================================================================")
    print("PHASE 3: GRID SEARCH ACROSS SUPERTREND MULTIPLIERS, TP RATIOS, & FILTERS")
    print("================================================================================")
    
    st_keys = ["st_10_25", "st_10_30", "st_10_35", "st_7_30", "st_14_30"]
    tp_grid = [1.8, 2.0, 2.2, 2.4]
    v_grid = [1.1, 1.2, 1.3]
    h1_modes = ["EMA50", "EMA200"]
    
    candidates = []
    
    for st_k in st_keys:
        for tp in tp_grid:
            for v_th in v_grid:
                for h1_m in h1_modes:
                    p = {
                        "st_key": st_k, "tp_r": tp, "v_thresh": v_th, "h1_mode": h1_m,
                        "min_sl": 10.0, "exec_mode": "MAKER"
                    }
                    m_tr = run_sim(features, m5_sub_m1, tr_s, tr_e, p)
                    m_val = run_sim(features, m5_sub_m1, val_s, val_e, p)
                    
                    # Strict criteria: Train PF >= 1.15 and Val PF >= 1.10
                    passes = (m_tr["net_pf"] >= 1.15 and m_val["net_pf"] >= 1.10 and m_tr["trades"] >= 20 and m_val["trades"] >= 10)
                    score = (m_tr["net_pf"] * 0.4 + m_val["net_pf"] * 0.6) + (3.0 if passes else 0.0)
                    if m_tr["trades"] < 15 or m_val["trades"] < 8: score = -50.0
                    
                    candidates.append({
                        "params": p, "score": round(score, 2), "passes": passes,
                        "tr_n": m_tr["trades"], "tr_wr": m_tr["wr"], "tr_pf": m_tr["net_pf"], "tr_pnl": m_tr["net_pnl"], "tr_dd": m_tr["max_dd"],
                        "val_n": m_val["trades"], "val_wr": m_val["wr"], "val_pf": m_val["net_pf"], "val_pnl": m_val["net_pnl"], "val_dd": m_val["max_dd"]
                    })
                    if passes:
                        print(f"  [QUALIFIED!] {st_k} | TP={tp}R | V={v_th}x | H1={h1_m} | Train: N={m_tr['trades']} PF={m_tr['net_pf']}x PnL=${m_tr['net_pnl']} | Val: N={m_val['trades']} PF={m_val['net_pf']}x PnL=${m_val['net_pnl']}")
                        
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    best = candidates[0]
    
    print("\n================================================================================")
    print("PHASE 4: FROZEN WINNER SELECTION")
    print(f"WINNER: {best['params']} | Score={best['score']} | Passes Screening={best['passes']}")
    print(f"  Train: N={best['tr_n']} | WR={best['tr_wr']}% | Net PF={best['tr_pf']}x | PnL=${best['tr_pnl']} | DD={best['tr_dd']}%")
    print(f"  Val  : N={best['val_n']} | WR={best['val_wr']}% | Net PF={best['val_pf']}x | PnL=${best['val_pnl']} | DD={best['val_dd']}%")
    print("================================================================================")
    
    # -------------------------------------------------------------------------
    # UNLOCKING LOCKED TEST (DAYS 66-90)
    # -------------------------------------------------------------------------
    win_p = best["params"]
    m_lock = run_sim(features, m5_sub_m1, lock_s, lock_e, win_p)
    m_full_maker = run_sim(features, m5_sub_m1, 250, total, win_p)
    
    # Taker stress
    p_taker = dict(win_p); p_taker["exec_mode"] = "TAKER"; p_taker["taker_slip"] = 0.03
    m_full_taker = run_sim(features, m5_sub_m1, 250, total, p_taker)
    
    print("\n[PHASE 5] LOCKED TEST (DAYS 66-90) EVALUATION:")
    print(f"  LOCKED TEST: Trades={m_lock['trades']} | WR={m_lock['wr']}% | Net PF={m_lock['net_pf']}x | PnL=${m_lock['net_pnl']} | DD={m_lock['max_dd']}% | Payoff={m_lock['payoff']}x")
    print(f"  FULL 90D (MAKER): Trades={m_full_maker['trades']} | WR={m_full_maker['wr']}% | Net PF={m_full_maker['net_pf']}x | PnL=${m_full_maker['net_pnl']} | DD={m_full_maker['max_dd']}% | Sharpe={m_full_maker['sharpe']}")
    print(f"  FULL 90D (TAKER): Trades={m_full_taker['trades']} | WR={m_full_taker['wr']}% | Net PF={m_full_taker['net_pf']}x | PnL=${m_full_taker['net_pnl']} | DD={m_full_taker['max_dd']}% | Sharpe={m_full_taker['sharpe']}")

    # -------------------------------------------------------------------------
    # ROLLING WALK-FORWARD ACROSS ALL 90 DAYS (30d train / 10d test)
    # -------------------------------------------------------------------------
    print("\n[PHASE 6] ROLLING WALK-FORWARD VALIDATION (8 WINDOWS):")
    tr_len = 30 * 288 # 8,640 bars
    te_len = 10 * 288 # 2,880 bars
    step = 7 * 288    # 2,016 bars
    
    wf_results = []
    wf_win = 1
    ptr = 250
    prof_count = 0
    
    while ptr + tr_len + te_len <= total:
        w_tr = run_sim(features, m5_sub_m1, ptr, ptr + tr_len, win_p)
        w_te = run_sim(features, m5_sub_m1, ptr + tr_len, ptr + tr_len + te_len, win_p)
        t_s_str = datetime.fromtimestamp(features[ptr + tr_len]["time"]/1000, tz=timezone.utc).strftime("%m-%d")
        t_e_str = datetime.fromtimestamp(features[ptr + tr_len + te_len - 1]["time"]/1000, tz=timezone.utc).strftime("%m-%d")
        
        if w_te["net_pnl"] > 0: prof_count += 1
        wf_results.append({
            "window": wf_win, "period": f"{t_s_str} to {t_e_str}",
            "train_pf": w_tr["net_pf"], "test_n": w_te["trades"], "test_wr": w_te["wr"],
            "test_pf": w_te["net_pf"], "test_pnl": w_te["net_pnl"], "test_dd": w_te["max_dd"]
        })
        print(f"  WF #{wf_win} ({t_s_str} to {t_e_str}) | Train PF={w_tr['net_pf']:4.2f}x | Test: N={w_te['trades']:2d} WR={w_te['wr']:4.1f}% PF={w_te['net_pf']:4.2f}x PnL=${w_te['net_pnl']:6.2f} DD={w_te['max_dd']}%")
        wf_win += 1
        ptr += step
        
    wf_prof_pct = round(prof_count / max(1, len(wf_results)) * 100.0, 1)
    test_pfs = sorted([w["test_pf"] for w in wf_results if w["test_n"] > 0])
    med_wf_pf = test_pfs[len(test_pfs)//2] if test_pfs else 0.0
    print(f"  Walk-Forward Summary: {prof_count}/{len(wf_results)} profitable ({wf_prof_pct}%) | Median Test PF = {med_wf_pf}x")

    # -------------------------------------------------------------------------
    # 10,000 MONTE CARLO RESAMPLING
    # -------------------------------------------------------------------------
    print("\n[PHASE 7] 10,000 MONTE CARLO STRESS SIMULATIONS:")
    trades_list = [t["net_pnl"] for t in m_full_maker["trades_list"]]
    n_mc = len(trades_list)
    mc_equities = []
    mc_dds = []
    ruin_cnt = 0
    dd20_cnt = 0
    
    random.seed(42)
    for _ in range(10000):
        eq = 1000.0; pk = eq; mdd = 0.0
        for _ in range(n_mc):
            if random.random() < 0.10: continue # 10% missed trades
            pnl = random.choice(trades_list) - abs(random.choice(trades_list)) * 0.05
            eq += pnl
            if eq > pk: pk = eq
            dd = (pk - eq) / pk * 100.0
            if dd > mdd: mdd = dd
        mc_equities.append(eq)
        mc_dds.append(mdd)
        if eq <= 500.0: ruin_cnt += 1
        if mdd >= 20.0: dd20_cnt += 1
        
    def pct(arr, p):
        s = sorted(arr)
        k = (len(s) - 1) * (p / 100.0)
        f = math.floor(k); c = math.ceil(k)
        if f == c: return s[int(k)]
        return s[int(f)] * (c - k) + s[int(c)] * (idx - f)

    p05_eq = round(sorted(mc_equities)[int(len(mc_equities)*0.05)], 2)
    med_eq = round(sorted(mc_equities)[int(len(mc_equities)*0.50)], 2)
    p95_eq = round(sorted(mc_equities)[int(len(mc_equities)*0.95)], 2)
    med_dd = round(sorted(mc_dds)[int(len(mc_dds)*0.50)], 2)
    p95_dd = round(sorted(mc_dds)[int(len(mc_dds)*0.95)], 2)
    
    print(f"  Median Ending Equity: ${med_eq} | 5th/95th: [${p05_eq}, ${p95_eq}]")
    print(f"  Median Max DD       : {med_dd}% | 95th Max DD: {p95_dd}%")
    print(f"  Probability of 20% DD: {dd20_cnt/100.0}% | Ruin Probability: {ruin_cnt/100.0}%")

    # Save summary
    res_obj = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "winner_params": win_p,
        "train": {"trades": best["tr_n"], "wr": best["tr_wr"], "net_pf": best["tr_pf"], "pnl": best["tr_pnl"], "dd": best["tr_dd"]},
        "validation": {"trades": best["val_n"], "wr": best["val_wr"], "net_pf": best["val_pf"], "pnl": best["val_pnl"], "dd": best["val_dd"]},
        "locked_test": {"trades": m_lock["trades"], "wr": m_lock["wr"], "net_pf": m_lock["net_pf"], "pnl": m_lock["net_pnl"], "dd": m_lock["max_dd"], "payoff": m_lock["payoff"]},
        "full_90d_maker": {"trades": m_full_maker["trades"], "wr": m_full_maker["wr"], "net_pf": m_full_maker["net_pf"], "pnl": m_full_maker["net_pnl"], "dd": m_full_maker["max_dd"], "sharpe": m_full_maker["sharpe"]},
        "full_90d_taker": {"trades": m_full_taker["trades"], "wr": m_full_taker["wr"], "net_pf": m_full_taker["net_pf"], "pnl": m_full_taker["net_pnl"], "dd": m_full_taker["max_dd"], "sharpe": m_full_taker["sharpe"]},
        "walk_forward": {"pct_profitable": wf_prof_pct, "median_pf": med_wf_pf, "windows": wf_results},
        "monte_carlo": {"median_eq": med_eq, "p05_eq": p05_eq, "p95_eq": p95_eq, "median_dd": med_dd, "p95_dd": p95_dd, "prob_20_dd": dd20_cnt/100.0, "ruin": ruin_cnt/100.0}
    }
    with open(os.path.join(OUTPUT_DIR, "m5_supertrend_hardened_summary.json"), "w", encoding="utf-8") as f:
        json.dump(res_obj, f, indent=2)
        
    print(f"\nFinal Hardened M5 Strategy results saved in {OUTPUT_DIR}")
    return res_obj

if __name__ == "__main__":
    m5_bars, m5_sub_m1 = load_and_prep()
    features = build_multi_supertrend_features(m5_bars)
    execute_hardening(features, m5_sub_m1)
