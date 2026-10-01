"""
================================================================================
APEX QUANT M5 ADVANCED QUANTUM SEARCH: 4 INSTITUTIONAL-GRADE ARCHITECTURES
================================================================================
Tests 4 advanced M5 architectures designed specifically for ETHUSDT Binance Futures:
  1. ARCH_1: London Open Range Expansion (LORE) - Asian Range Breakout
  2. ARCH_2: M5 Institutional Displacement & FVG (Fair Value Gap) Retest
  3. ARCH_3: Triple EMA Stack + RSI Momentum Reset (Trend Rider)
  4. ARCH_4: SuperTrend (10, 3.0) + H1 Macro Filter + Volume Expansion

Evaluates on the strict 3-phase partition:
  - TRAIN: Days 1 - 45 (12,960 M5 bars)
  - VALIDATION: Days 46 - 65 (5,760 M5 bars)
  - LOCKED TEST: Days 66 - 90 (7,200 M5 bars)
================================================================================
"""

import os
import sys
import math
import json
import time
from datetime import datetime, timezone

DATA_FILE = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"
OUTPUT_DIR = r"C:\apex_copytrade\audit\m5_advanced"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. LOAD & AGGREGATE DATA
# ------------------------------------------------------------------------------
def load_and_prep_m5(csv_path):
    print(f"\n[PHASE 1] Loading M1 and aggregating to M5 with intrabar data...")
    t0 = time.time()
    m1_times, m1_opens, m1_highs, m1_lows, m1_closes, m1_vols = [], [], [], [], [], []
    with open(csv_path, 'r', encoding='utf-8') as f:
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

    print(f"  Loaded {len(m5_bars):,} M5 bars in {time.time()-t0:.2f}s")
    return m5_bars, m5_sub_m1

# ------------------------------------------------------------------------------
# 2. INDICATOR COMPUTATIONS
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

def compute_rsi(closes, period=14):
    n = len(closes)
    rsi = [50.0] * n
    if n < period + 1: return rsi
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        diff = closes[i] - closes[i-1]
        if diff > 0: gains[i] = diff
        else: losses[i] = -diff
    avg_gain = sum(gains[1:period+1]) / period
    avg_loss = sum(losses[1:period+1]) / period
    if avg_loss == 0: rsi[period] = 100.0
    else: rsi[period] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0: rsi[i] = 100.0
        else: rsi[i] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return rsi

def compute_supertrend(highs, lows, closes, period=10, multiplier=3.0):
    n = len(closes)
    atr = compute_atr(highs, lows, closes, period)
    st = [0.0] * n
    direction = [1] * n # 1 = Bullish, -1 = Bearish
    upper = [0.0] * n
    lower = [0.0] * n
    
    for i in range(period, n):
        hl2 = (highs[i] + lows[i]) / 2.0
        basic_upper = hl2 + multiplier * atr[i]
        basic_lower = hl2 - multiplier * atr[i]
        
        lower[i] = basic_lower if basic_lower > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]
        upper[i] = basic_upper if basic_upper < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
        
        if closes[i] > upper[i-1]:
            direction[i] = 1
        elif closes[i] < lower[i-1]:
            direction[i] = -1
        else:
            direction[i] = direction[i-1]
            
        st[i] = lower[i] if direction[i] == 1 else upper[i]
    return st, direction

# ------------------------------------------------------------------------------
# 3. FEATURE EXTRACTION & ZERO-LOOKAHEAD HIGHER TIMEFRAMES
# ------------------------------------------------------------------------------
def build_features(m5_bars):
    print("\n[PHASE 2] Precomputing M5 indicators and H1 higher timeframe features...")
    n = len(m5_bars)
    times = [b["time"] for b in m5_bars]
    opens = [b["open"] for b in m5_bars]
    highs = [b["high"] for b in m5_bars]
    lows = [b["low"] for b in m5_bars]
    closes = [b["close"] for b in m5_bars]
    vols = [b["volume"] for b in m5_bars]
    
    e9 = fast_ema(closes, 9)
    e21 = fast_ema(closes, 21)
    e50 = fast_ema(closes, 50)
    e200 = fast_ema(closes, 200)
    atr14 = compute_atr(highs, lows, closes, 14)
    rsi14 = compute_rsi(closes, 14)
    st, st_dir = compute_supertrend(highs, lows, closes, 10, 3.0)
    
    # H1 aggregation
    h1_bars = []
    m5_to_h1 = [-1] * n
    cur_h1 = None
    for i in range(n):
        t = times[i]
        o, h, l, c, v = opens[i], highs[i], lows[i], closes[i], vols[i]
        h1_t = (t // 3600000) * 3600000
        if cur_h1 is None: cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        elif cur_h1["time"] == h1_t:
            cur_h1["high"] = max(cur_h1["high"], h); cur_h1["low"] = min(cur_h1["low"], l)
            cur_h1["close"] = c; cur_h1["vol"] += v
        else:
            h1_bars.append(cur_h1)
            cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        m5_to_h1[i] = len(h1_bars) - 1
        
    h1_closes = [b["close"] for b in h1_bars]
    h1_e50 = fast_ema(h1_closes, 50)
    h1_e200 = fast_ema(h1_closes, 200)
    
    features = []
    current_day_str = ""
    asian_high = 0.0
    asian_low = 999999.0
    
    for i in range(n):
        t = times[i]
        c, o, h, l, v = closes[i], opens[i], highs[i], lows[i], vols[i]
        dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
        day_str = dt.strftime("%Y-%m-%d")
        utc_hour = dt.hour
        utc_min = dt.minute
        
        # Reset Asian range at start of UTC day
        if day_str != current_day_str:
            current_day_str = day_str
            asian_high = h
            asian_low = l
            
        # Asian session is 00:00 to 07:00 UTC
        if 0 <= utc_hour < 7:
            asian_high = max(asian_high, h)
            asian_low = min(asian_low, l)
            
        # H1 Macro Trend
        h1_idx = m5_to_h1[i]
        h1_trend = "NEUTRAL"
        if h1_idx >= 50:
            if h1_closes[h1_idx] > h1_e50[h1_idx]: h1_trend = "BULLISH"
            elif h1_closes[h1_idx] < h1_e50[h1_idx]: h1_trend = "BEARISH"
            
        # Volume relative to 10-bar average
        v_avg_10 = sum(vols[max(0, i-10):i]) / 10.0 if i >= 10 else v
        v_ratio = v / max(1.0, v_avg_10)
        
        body = abs(c - o)
        tr = h - l
        
        features.append({
            "idx": i, "time": t, "open": o, "high": h, "low": l, "close": c, "volume": v,
            "day_str": day_str, "hour": utc_hour, "min": utc_min,
            "body": body, "range": tr, "atr": atr14[i],
            "e9": e9[i], "e21": e21[i], "e50": e50[i], "e200": e200[i],
            "rsi": rsi14[i], "st": st[i], "st_dir": st_dir[i],
            "h1_trend": h1_trend, "asian_high": asian_high, "asian_low": asian_low,
            "v_ratio": v_ratio
        })
    print(f"  Features prepared for {n:,} bars.")
    return features

# ------------------------------------------------------------------------------
# 4. SIMULATION ENGINE WITH M1 INTRABAR PRECISION
# ------------------------------------------------------------------------------
def simulate_strategy(features, m5_sub_m1, start_idx, end_idx, signal_gen_func, params):
    tp_r = params.get("tp_r", 1.8)
    exec_mode = params.get("exec_mode", "MAKER") # MAKER (0.02% / 0.02% / 0.05%) or TAKER (0.05% / 0.05%)
    taker_slip = params.get("taker_slip", 0.02)
    max_daily_trades = params.get("max_daily_trades", 3)
    
    entry_fee_rate = 0.0002 if exec_mode == "MAKER" else 0.0005
    tp_fee_rate = 0.0002
    sl_fee_rate = 0.0005
    
    balance = 1000.0
    peak_b = balance
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
            
        # 1. POSITION MANAGEMENT (Evaluated minute-by-minute across M1 sub-bars)
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
                    if m1_l <= sl:
                        closed = True; exit_p = sl - 0.02; reason = "SL_HIT"; break
                    elif m1_h >= tp:
                        closed = True; exit_p = tp; reason = "TP_HIT"; break
                else: # SHORT
                    if m1_h >= sl:
                        closed = True; exit_p = sl + 0.02; reason = "SL_HIT"; break
                    elif m1_l <= tp:
                        closed = True; exit_p = tp; reason = "TP_HIT"; break
                        
            if closed:
                gp = (exit_p - entry)*qty if side == "LONG" else (entry - exit_p)*qty
                comm = pos["entry_fee"] + round(qty * exit_p * (tp_fee_rate if reason == "TP_HIT" else sl_fee_rate), 4)
                net_pnl = gp - comm - pos["slippage"]
                balance += net_pnl
                if balance > peak_b: peak_b = balance
                dd = (peak_b - balance) / peak_b * 100.0
                trades.append({
                    "time": t, "side": side, "entry": entry, "exit": exit_p, "reason": reason,
                    "is_win": net_pnl > 0, "gross_pnl": round(gp, 2), "comm": round(comm, 2),
                    "net_pnl": round(net_pnl, 2), "r": round(net_pnl / pos["risk_usd"], 2),
                    "dd": round(dd, 2)
                })
                in_pos = False
                pos = {}
                cooldown = idx + 3 # 15 mins cooldown
                daily_count += 1
                
        # 2. ENTRY EVALUATION
        if not in_pos and idx >= cooldown and daily_count < max_daily_trades:
            sig, sl_dist = signal_gen_func(f, features, idx, params)
            if sig:
                curr_c = f["close"]
                r_dist = max(8.0, sl_dist)
                sl_p = round(curr_c - r_dist, 2) if sig == "LONG" else round(curr_c + r_dist, 2)
                tp_p = round(curr_c + (tp_r * r_dist), 2) if sig == "LONG" else round(curr_c - (tp_r * r_dist), 2)
                
                risk_usd = balance * 0.010 # 1% risk
                qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
                
                if exec_mode == "MAKER":
                    entry_p = curr_c
                    slip = 0.0
                else:
                    slip = qty * taker_slip
                    entry_p = curr_c + (taker_slip if sig == "LONG" else -taker_slip)
                    
                entry_fee = round(qty * entry_p * entry_fee_rate, 4)
                in_pos = True
                pos = {
                    "side": sig, "entry": entry_p, "sl": sl_p, "tp": tp_p, "qty": qty,
                    "r_dist": r_dist, "risk_usd": risk_usd, "entry_fee": entry_fee, "slippage": slip
                }
                
    return calc_metrics(trades)

def calc_metrics(trades):
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
        "max_dd": round(max_dd, 2), "payoff": payoff, "sharpe": sharpe
    }

# ------------------------------------------------------------------------------
# 5. THE 4 ADVANCED STRATEGIES
# ------------------------------------------------------------------------------

# ARCH 1: LONDON OPEN RANGE EXPANSION (LORE)
def strat_lore(f, features, idx, params):
    # Only trade during the first 3 hours of London session: 07:00 to 10:00 UTC
    if not (7 <= f["hour"] < 10): return None, 0.0
    
    c, o, h, l = f["close"], f["open"], f["high"], f["low"]
    ah, al = f["asian_high"], f["asian_low"]
    atr = f["atr"]
    
    # Asian range must be valid and compressed (<= 3.5 ATR)
    if (ah - al) > 3.5 * atr or (ah - al) < 1.0 * atr:
        return None, 0.0
        
    # Bullish Breakout above Asian High with volume & momentum
    if c > ah and c > o and f["body"] >= 0.50 * f["range"] and f["v_ratio"] >= 1.25:
        if f["h1_trend"] != "BEARISH":
            sl_dist = max(10.0, (c - ah) + 1.0 * atr)
            return "LONG", sl_dist
            
    # Bearish Breakout below Asian Low
    if c < al and c < o and f["body"] >= 0.50 * f["range"] and f["v_ratio"] >= 1.25:
        if f["h1_trend"] != "BULLISH":
            sl_dist = max(10.0, (al - c) + 1.0 * atr)
            return "SHORT", sl_dist
            
    return None, 0.0

# ARCH 2: M5 INSTITUTIONAL DISPLACEMENT & FVG RETEST
def strat_fvg_displacement(f, features, idx, params):
    if idx < 4: return None, 0.0
    if not (7 <= f["hour"] < 19): return None, 0.0 # Active sessions
    
    c = f["close"]
    atr = f["atr"]
    
    # Check for Bullish Displacement on candle i-1
    # Candle i-2, i-1, i: Fair Value Gap is between i-2 High and i Low
    b_prev = features[idx-1]
    b_prev2 = features[idx-2]
    
    # Bullish Displacement on prev bar: large green candle
    if b_prev["close"] > b_prev["open"] and b_prev["body"] >= 1.4 * b_prev["atr"] and b_prev["v_ratio"] >= 1.3:
        # FVG exists if b_prev2["high"] < b_prev["close"]
        fvg_top = b_prev["close"]
        fvg_bottom = b_prev2["high"]
        if fvg_top > fvg_bottom:
            # Current candle retraces into FVG zone and bounces
            if f["low"] <= fvg_top and c > fvg_bottom and c > f["open"] and f["h1_trend"] != "BEARISH":
                sl_dist = max(10.0, (c - b_prev["low"]) + 0.3 * atr)
                return "LONG", sl_dist
                
    # Bearish Displacement on prev bar: large red candle
    if b_prev["close"] < b_prev["open"] and b_prev["body"] >= 1.4 * b_prev["atr"] and b_prev["v_ratio"] >= 1.3:
        fvg_bottom = b_prev["close"]
        fvg_top = b_prev2["low"]
        if fvg_top > fvg_bottom:
            if f["high"] >= fvg_bottom and c < fvg_top and c < f["open"] and f["h1_trend"] != "BULLISH":
                sl_dist = max(10.0, (b_prev["high"] - c) + 0.3 * atr)
                return "SHORT", sl_dist
                
    return None, 0.0

# ARCH 3: TRIPLE EMA STACK + RSI MOMENTUM RESET
def strat_ema_stack_rsi(f, features, idx, params):
    if not (7 <= f["hour"] < 20): return None, 0.0
    c, o, h, l = f["close"], f["open"], f["high"], f["low"]
    e9, e21, e50 = f["e9"], f["e21"], f["e50"]
    rsi = f["rsi"]
    atr = f["atr"]
    
    # Bullish Trend Stack: EMA 9 > EMA 21 > EMA 50 AND H1 Bullish
    if e9 > e21 > e50 and f["h1_trend"] == "BULLISH":
        # RSI reset between 42 and 52 (healthy pullback in uptrend), now turning up
        if 40 <= rsi <= 55 and c > o and l <= e21 * 1.002:
            sl_dist = max(10.0, 1.2 * atr)
            return "LONG", sl_dist
            
    # Bearish Trend Stack: EMA 9 < EMA 21 < EMA 50 AND H1 Bearish
    if e9 < e21 < e50 and f["h1_trend"] == "BEARISH":
        # RSI reset between 48 and 58
        if 45 <= rsi <= 60 and c < o and h >= e21 * 0.998:
            sl_dist = max(10.0, 1.2 * atr)
            return "SHORT", sl_dist
            
    return None, 0.0

# ARCH 4: SUPERTREND (10, 3.0) + H1 MACRO FILTER + VOL EXPANSION
def strat_supertrend_h1(f, features, idx, params):
    if idx < 2: return None, 0.0
    if not (7 <= f["hour"] < 21): return None, 0.0
    
    prev_f = features[idx-1]
    c, o = f["close"], f["open"]
    atr = f["atr"]
    
    # Bullish Flip: SuperTrend flips from Bearish (-1) to Bullish (1)
    if prev_f["st_dir"] == -1 and f["st_dir"] == 1:
        if f["h1_trend"] == "BULLISH" and f["v_ratio"] >= 1.2:
            sl_dist = max(10.0, (c - f["st"]) + 0.2 * atr)
            return "LONG", sl_dist
            
    # Bearish Flip: SuperTrend flips from Bullish (1) to Bearish (-1)
    if prev_f["st_dir"] == 1 and f["st_dir"] == -1:
        if f["h1_trend"] == "BEARISH" and f["v_ratio"] >= 1.2:
            sl_dist = max(10.0, (f["st"] - c) + 0.2 * atr)
            return "SHORT", sl_dist
            
    return None, 0.0

# ------------------------------------------------------------------------------
# 6. RUN THE QUANTUM TOURNAMENT ACROSS ALL ARCHITECTURES
# ------------------------------------------------------------------------------
def run_quantum_tournament(features, m5_sub_m1):
    total = len(features)
    tr_s, tr_e = 250, 12960 # Days 1 - 45
    val_s, val_e = 12960, 18720 # Days 46 - 65
    lock_s, lock_e = 18720, total # Days 66 - 90
    
    strats = [
        ("LORE_Asian_Breakout", strat_lore),
        ("FVG_Displacement_Retest", strat_fvg_displacement),
        ("EMA_Stack_RSI_Reset", strat_ema_stack_rsi),
        ("SuperTrend_H1_Momentum", strat_supertrend_h1)
    ]
    
    tp_grid = [1.4, 1.6, 1.8, 2.0, 2.2]
    
    print("\n================================================================================")
    print("PHASE 3: RUNNING ADVANCED QUANTUM SCREENING ON TRAIN & VALIDATION")
    print("================================================================================")
    
    leaderboard = []
    
    for name, func in strats:
        print(f"\n>>> ARCHITECTURE: {name} <<<")
        for tp in tp_grid:
            p = {"tp_r": tp, "exec_mode": "MAKER", "max_daily_trades": 3}
            m_tr = simulate_strategy(features, m5_sub_m1, tr_s, tr_e, func, p)
            m_val = simulate_strategy(features, m5_sub_m1, val_s, val_e, func, p)
            
            passes_criteria = (m_tr["net_pf"] >= 1.15 and m_val["net_pf"] >= 1.10 and m_tr["trades"] >= 15 and m_val["trades"] >= 8)
            score = (m_tr["net_pf"] * 0.4 + m_val["net_pf"] * 0.6) + (2.0 if passes_criteria else 0.0)
            if m_tr["trades"] < 10 or m_val["trades"] < 5: score = -50.0
            
            entry = {
                "name": name, "tp_r": tp,
                "train_n": m_tr["trades"], "train_wr": m_tr["wr"], "train_pf": m_tr["net_pf"], "train_pnl": m_tr["net_pnl"], "train_dd": m_tr["max_dd"],
                "val_n": m_val["trades"], "val_wr": m_val["wr"], "val_pf": m_val["net_pf"], "val_pnl": m_val["net_pnl"], "val_dd": m_val["max_dd"],
                "passes_screen": passes_criteria, "score": round(score, 2)
            }
            leaderboard.append(entry)
            status_tag = "[PASSES CRITERIA!]" if passes_criteria else ""
            print(f"  TP {tp:3.1f}R | Train: N={m_tr['trades']:2d} WR={m_tr['wr']:4.1f}% PF={m_tr['net_pf']:4.2f}x PnL=${m_tr['net_pnl']:6.2f} | Val: N={m_val['trades']:2d} WR={m_val['wr']:4.1f}% PF={m_val['net_pf']:4.2f}x PnL=${m_val['net_pnl']:6.2f} {status_tag}")

    leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)
    top_cand = leaderboard[0]
    
    print("\n================================================================================")
    print(f"PHASE 4: TOP CANDIDATE SELECTED FROM TRAIN & VALIDATION")
    print(f"WINNER: {top_cand['name']} | TP={top_cand['tp_r']}R | Score={top_cand['score']}")
    print("================================================================================")
    
    # Locate func
    top_func = [s[1] for s in strats if s[0] == top_cand["name"]][0]
    top_p = {"tp_r": top_cand["tp_r"], "exec_mode": "MAKER", "max_daily_trades": 3}
    
    # UNLOCK LOCKED TEST (Days 66 - 90)
    m_locked = simulate_strategy(features, m5_sub_m1, lock_s, lock_e, top_func, top_p)
    m_full = simulate_strategy(features, m5_sub_m1, 250, total, top_func, top_p)
    
    # Taker execution test
    p_taker = dict(top_p); p_taker["exec_mode"] = "TAKER"; p_taker["taker_slip"] = 0.03
    m_taker = simulate_strategy(features, m5_sub_m1, 250, total, top_func, p_taker)
    
    print(f"  LOCKED TEST (25d) : Trades={m_locked['trades']} | WR={m_locked['wr']}% | Net PF={m_locked['net_pf']}x | PnL=${m_locked['net_pnl']} | DD={m_locked['max_dd']}%")
    print(f"  FULL 90D (MAKER)  : Trades={m_full['trades']} | WR={m_full['wr']}% | Net PF={m_full['net_pf']}x | PnL=${m_full['net_pnl']} | DD={m_full['max_dd']}% | Sharpe={m_full['sharpe']}")
    print(f"  FULL 90D (TAKER)  : Trades={m_taker['trades']} | WR={m_taker['wr']}% | Net PF={m_taker['net_pf']}x | PnL=${m_taker['net_pnl']} | DD={m_taker['max_dd']}% | Sharpe={m_taker['sharpe']}")

    # Save to JSON
    out_obj = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "top_candidate": top_cand,
        "locked_test": m_locked,
        "full_maker": m_full,
        "full_taker": m_taker,
        "leaderboard": leaderboard
    }
    with open(os.path.join(OUTPUT_DIR, "quantum_search_results.json"), "w", encoding="utf-8") as f:
        json.dump(out_obj, f, indent=2)
        
    print(f"\nArtifacts saved in {OUTPUT_DIR}")
    return out_obj

if __name__ == "__main__":
    m5_bars, m5_sub_m1 = load_and_prep_m5(DATA_FILE)
    features = build_features(m5_bars)
    run_quantum_tournament(features, m5_sub_m1)
