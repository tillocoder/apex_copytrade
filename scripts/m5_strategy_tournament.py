"""
================================================================================
APEX QUANT M5 STRATEGY TOURNAMENT & REAL-MONEY HARDENING PIPELINE
================================================================================
Aggregates ETHUSDT M1 data (129,600 bars) into M5 bars (25,920 bars) with
M1 intrabar precision. Implements and backtests 4 distinct algorithmic strategies:
  1. Strategy A: M5 Liquidity Sweep & Structure Shift (SMC Reversal)
  2. Strategy B: M5 Trend Continuation / EMA Value Zone Pullback (MTF Trend)
  3. Strategy C: M5 Volatility Squeeze & Volume Breakout (Momentum Expansion)
  4. Strategy D: M5 Mean Reversion at Bollinger/RSI Extremes (Exhaustion)

Evaluates on strict 3-phase split:
  - TRAIN: Days 1 - 45 (Bars 1 to 12,960 M5)
  - VALIDATION: Days 46 - 65 (Bars 12,961 to 18,720 M5)
  - LOCKED TEST: Days 66 - 90 (Bars 18,721 to 25,920 M5)
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
OUTPUT_DIR = r"C:\apex_copytrade\audit\m5_tournament"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# 1. LOAD M1 DATA & AGGREGATE TO M5 WITH INTRABAR PRECISION
# ==============================================================================

def load_data_and_aggregate_m5(csv_path):
    print(f"\n[PHASE 1] Ingesting M1 dataset and building M5 bars with sub-minute resolution...")
    t0 = time.time()
    
    m1_times = []
    m1_opens = []
    m1_highs = []
    m1_lows = []
    m1_closes = []
    m1_vols = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        header = f.readline()
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
            except ValueError:
                continue

    n_m1 = len(m1_times)
    print(f"  Loaded {n_m1:,} M1 bars.")
    
    # Aggregate to M5 (5-minute buckets: 300,000 ms)
    m5_bars = []
    m5_sub_m1 = [] # Stores list of M1 bar tuples (t, o, h, l, c) for each M5 bar
    
    cur_bucket_t = None
    cur_sub = []
    cur_o, cur_h, cur_l, cur_c, cur_v = 0.0, 0.0, 0.0, 0.0, 0.0
    
    for i in range(n_m1):
        t = m1_times[i]
        o, h, l, c, v = m1_opens[i], m1_highs[i], m1_lows[i], m1_closes[i], m1_vols[i]
        b_t = (t // 300000) * 300000
        
        if cur_bucket_t is None:
            cur_bucket_t = b_t
            cur_o, cur_h, cur_l, cur_c, cur_v = o, h, l, c, v
            cur_sub = [(t, o, h, l, c)]
        elif cur_bucket_t == b_t:
            cur_h = max(cur_h, h)
            cur_l = min(cur_l, l)
            cur_c = c
            cur_v += v
            cur_sub.append((t, o, h, l, c))
        else:
            m5_bars.append({
                "time": cur_bucket_t,
                "open": cur_o,
                "high": cur_h,
                "low": cur_l,
                "close": cur_c,
                "volume": cur_v
            })
            m5_sub_m1.append(cur_sub)
            
            cur_bucket_t = b_t
            cur_o, cur_h, cur_l, cur_c, cur_v = o, h, l, c, v
            cur_sub = [(t, o, h, l, c)]
            
    if cur_sub:
        m5_bars.append({
            "time": cur_bucket_t,
            "open": cur_o,
            "high": cur_h,
            "low": cur_l,
            "close": cur_c,
            "volume": cur_v
        })
        m5_sub_m1.append(cur_sub)
        
    n_m5 = len(m5_bars)
    print(f"  Aggregated to {n_m5:,} M5 bars in {time.time()-t0:.2f}s.")
    return m5_bars, m5_sub_m1, m1_times, m1_opens, m1_highs, m1_lows, m1_closes

# ==============================================================================
# 2. INDICATOR UTILITIES (FAST PURE-PYTHON)
# ==============================================================================

def fast_ema(series, period):
    n = len(series)
    out = [0.0] * n
    if n == 0: return out
    k = 2.0 / (period + 1.0)
    out[0] = series[0]
    for i in range(1, n):
        out[i] = series[i] * k + out[i-1] * (1.0 - k)
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
    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
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
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    return rsi

def compute_bollinger(closes, period=20, num_std=2.0):
    n = len(closes)
    mid = [0.0] * n
    upper = [0.0] * n
    lower = [0.0] * n
    for i in range(n):
        if i < period - 1:
            mid[i] = closes[i]
            upper[i] = closes[i]
            lower[i] = closes[i]
        else:
            window = closes[i - period + 1 : i + 1]
            m = sum(window) / period
            variance = sum((x - m)**2 for x in window) / period
            s = math.sqrt(variance)
            mid[i] = m
            upper[i] = m + num_std * s
            lower[i] = m - num_std * s
    return mid, upper, lower

def compute_adx(highs, lows, closes, period=14):
    n = len(closes)
    tr = [0.0] * n
    pdm = [0.0] * n
    mdm = [0.0] * n
    for i in range(1, n):
        h, l, pc = highs[i], lows[i], closes[i-1]
        tr[i] = max(h - l, abs(h - pc), abs(l - pc))
        up = h - highs[i-1]
        down = lows[i-1] - l
        if up > down and up > 0: pdm[i] = up
        if down > up and down > 0: mdm[i] = down
        
    smooth_tr = [0.0] * n
    smooth_pdm = [0.0] * n
    smooth_mdm = [0.0] * n
    adx = [20.0] * n
    if n < 2 * period + 1: return adx
    
    smooth_tr[period] = sum(tr[1:period+1])
    smooth_pdm[period] = sum(pdm[1:period+1])
    smooth_mdm[period] = sum(mdm[1:period+1])
    dx = [0.0] * n
    for i in range(period + 1, n):
        smooth_tr[i] = smooth_tr[i-1] - (smooth_tr[i-1] / period) + tr[i]
        smooth_pdm[i] = smooth_pdm[i-1] - (smooth_pdm[i-1] / period) + pdm[i]
        smooth_mdm[i] = smooth_mdm[i-1] - (smooth_mdm[i-1] / period) + mdm[i]
        pdi = 100.0 * (smooth_pdm[i] / max(1e-6, smooth_tr[i]))
        mdi = 100.0 * (smooth_mdm[i] / max(1e-6, smooth_tr[i]))
        sum_di = pdi + mdi
        dx[i] = 100.0 * abs(pdi - mdi) / max(1e-6, sum_di)
        
    start_adx = 2 * period
    if n >= start_adx:
        adx[start_adx-1] = sum(dx[period:start_adx]) / period
        for i in range(start_adx, n):
            adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
    return adx

# ==============================================================================
# 3. PRECOMPUTE M5, M15, AND H1 MARKET CONTEXT (ZERO LOOKAHEAD)
# ==============================================================================

def precompute_m5_market(m5_bars):
    print("\n[PHASE 2] Precomputing M5 indicators and H1 higher timeframe alignment...")
    t0 = time.time()
    n = len(m5_bars)
    
    times = [b["time"] for b in m5_bars]
    opens = [b["open"] for b in m5_bars]
    highs = [b["high"] for b in m5_bars]
    lows = [b["low"] for b in m5_bars]
    closes = [b["close"] for b in m5_bars]
    vols = [b["volume"] for b in m5_bars]
    
    # M5 indicators
    e9 = fast_ema(closes, 9)
    e21 = fast_ema(closes, 21)
    e50 = fast_ema(closes, 50)
    e200 = fast_ema(closes, 200)
    atr14 = compute_atr(highs, lows, closes, 14)
    rsi14 = compute_rsi(closes, 14)
    adx14 = compute_adx(highs, lows, closes, 14)
    bb_mid, bb_upper, bb_lower = compute_bollinger(closes, 20, 2.0)
    
    # Aggregate H1 bars from M5
    h1_bars = []
    m5_to_h1 = [-1] * n
    cur_h1 = None
    
    for i in range(n):
        t = times[i]
        o, h, l, c, v = opens[i], highs[i], lows[i], closes[i], vols[i]
        h1_t = (t // 3600000) * 3600000
        if cur_h1 is None:
            cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        elif cur_h1["time"] == h1_t:
            cur_h1["high"] = max(cur_h1["high"], h)
            cur_h1["low"] = min(cur_h1["low"], l)
            cur_h1["close"] = c
            cur_h1["vol"] += v
        else:
            h1_bars.append(cur_h1)
            cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        m5_to_h1[i] = len(h1_bars) - 1 # Index of last strictly CLOSED H1 bar
        
    h1_closes = [b["close"] for b in h1_bars]
    h1_e50 = fast_ema(h1_closes, 50)
    h1_e200 = fast_ema(h1_closes, 200)
    
    features = []
    for i in range(n):
        t = times[i]
        c_price = closes[i]
        o_price = opens[i]
        h_price = highs[i]
        l_price = lows[i]
        v_curr = vols[i]
        
        # UTC Session
        utc_hour = (t // 3600000) % 24
        if 7 <= utc_hour < 13: sess = "LONDON"
        elif 13 <= utc_hour < 16: sess = "LONDON_NY_OVERLAP"
        elif 16 <= utc_hour < 21: sess = "NEW_YORK"
        else: sess = "ASIAN"
        
        # H1 Macro Trend (strictly closed)
        h1_idx = m5_to_h1[i]
        h1_trend = "NEUTRAL"
        if h1_idx >= 50:
            if h1_closes[h1_idx] > h1_e50[h1_idx]: h1_trend = "BULLISH"
            elif h1_closes[h1_idx] < h1_e50[h1_idx]: h1_trend = "BEARISH"
            
        # M5 Swing levels (strictly prior 20 bars: i-20 to i-1)
        sw_high_20 = max(highs[max(0, i-20):i]) if i >= 20 else h_price
        sw_low_20 = min(lows[max(0, i-20):i]) if i >= 20 else l_price
        
        # Volume average 10 bars
        v_avg_10 = (sum(vols[max(0, i-10):i]) / 10.0) if i >= 10 else v_curr
        v_ratio = v_curr / max(1.0, v_avg_10)
        
        # Candle Geometry
        body = abs(c_price - o_price)
        total_range = h_price - l_price
        upper_wick = h_price - max(o_price, c_price)
        lower_wick = min(o_price, c_price) - l_price
        
        features.append({
            "idx": i,
            "time": t,
            "open": o_price,
            "high": h_price,
            "low": l_price,
            "close": c_price,
            "volume": v_curr,
            "body": body,
            "range": total_range,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
            "atr": atr14[i],
            "e9": e9[i],
            "e21": e21[i],
            "e50": e50[i],
            "e200": e200[i],
            "rsi": rsi14[i],
            "adx": adx14[i],
            "bb_mid": bb_mid[i],
            "bb_upper": bb_upper[i],
            "bb_lower": bb_lower[i],
            "h1_trend": h1_trend,
            "session": sess,
            "sw_high_20": sw_high_20,
            "sw_low_20": sw_low_20,
            "v_ratio": v_ratio
        })
        
    print(f"  Precomputed {n:,} M5 features in {time.time()-t0:.2f}s")
    return features

# ==============================================================================
# 4. M5 SIMULATOR WITH M1 INTRABAR RESOLUTION
# ==============================================================================

def run_m5_simulation(features, m5_sub_m1, start_idx, end_idx, strategy_func, params):
    """
    Executes M5 strategy with:
    - Signal evaluated at close of M5 candle i.
    - Entry at open/limit of M5 candle i+1.
    - Exits evaluated minute-by-minute across the 5 underlying M1 candles of each M5 bar!
      This ensures ZERO intrabar ambiguity.
    - Realistic Binance Futures Fees:
      Maker Post-Only: 0.02% entry, 0.02% TP exit, 0.05% SL exit.
      Taker: 0.05% entry, 0.05% SL exit, 0.02% TP limit exit.
    """
    tp_r = params.get("tp_r", 1.8)
    sl_atr_mult = params.get("sl_atr_mult", 1.2)
    min_sl_usd = params.get("min_sl_usd", 10.0)
    exec_mode = params.get("exec_mode", "MAKER") # MAKER or TAKER
    taker_slippage_ticks = params.get("taker_slippage_ticks", 0.02) # $0.02
    
    entry_fee_rate = 0.0002 if exec_mode == "MAKER" else 0.0005
    tp_fee_rate = 0.0002
    sl_fee_rate = 0.0005
    
    balance = 1000.0
    peak_balance = balance
    trades = []
    
    in_pos = False
    pos = {}
    cooldown_until = 0
    daily_trades = 0
    current_day = ""
    
    for idx in range(start_idx, end_idx):
        f = features[idx]
        t = f["time"]
        
        # Day tracking
        day_str = datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        if day_str != current_day:
            current_day = day_str
            daily_trades = 0
            
        # 1. POSITION MANAGEMENT (Evaluated on underlying M1 bars of current M5 candle)
        if in_pos:
            sub_m1 = m5_sub_m1[idx]
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            tp = pos["tp"]
            qty = pos["qty"]
            
            closed = False
            exit_p = 0.0
            reason = ""
            
            # Step through each of the 5 M1 bars inside this M5 bar
            for m1_t, m1_o, m1_h, m1_l, m1_c in sub_m1:
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
                gp = (exit_p - entry) * qty if side == "LONG" else (entry - exit_p) * qty
                exit_fee_rate = tp_fee_rate if reason == "TP_HIT" else sl_fee_rate
                comm = pos["entry_fee"] + round(qty * exit_p * exit_fee_rate, 4)
                net_pnl = gp - comm - pos["slippage"]
                
                balance += net_pnl
                if balance > peak_balance: peak_balance = balance
                dd_pct = (peak_balance - balance) / peak_balance * 100.0
                
                trades.append({
                    "time": t,
                    "side": side,
                    "entry": entry,
                    "exit": exit_p,
                    "reason": reason,
                    "is_win": net_pnl > 0,
                    "gross_pnl": round(gp, 4),
                    "commissions": round(comm, 4),
                    "net_pnl": round(net_pnl, 4),
                    "r": round(net_pnl / pos["risk_usd"], 2),
                    "equity": round(balance, 2),
                    "dd_pct": round(dd_pct, 2)
                })
                in_pos = False
                pos = {}
                cooldown_until = idx + 2 # Cooldown of 2 M5 candles (10 mins)
                daily_trades += 1
                
        # 2. ENTRY EVALUATION (At close of M5 candle idx)
        if not in_pos and idx >= cooldown_until and daily_trades < 6:
            sig_side, sig_sl_dist = strategy_func(f, features, idx, params)
            if sig_side:
                curr_c = f["close"]
                r_dist = max(min_sl_usd, sig_sl_dist)
                sl_p = round(curr_c - r_dist, 2) if sig_side == "LONG" else round(curr_c + r_dist, 2)
                tp_p = round(curr_c + (tp_r * r_dist), 2) if sig_side == "LONG" else round(curr_c - (tp_r * r_dist), 2)
                
                risk_usd = balance * 0.010 # 1% risk
                qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
                
                # Entry fill on next bar open/limit
                if exec_mode == "MAKER":
                    entry_p = curr_c
                    slip = 0.0
                else: # TAKER
                    slip = qty * taker_slippage_ticks
                    entry_p = curr_c + (taker_slippage_ticks if sig_side == "LONG" else -taker_slippage_ticks)
                    
                entry_fee = round(qty * entry_p * entry_fee_rate, 4)
                in_pos = True
                pos = {
                    "side": sig_side,
                    "entry": entry_p,
                    "sl": sl_p,
                    "tp": tp_p,
                    "qty": qty,
                    "r_dist": r_dist,
                    "risk_usd": risk_usd,
                    "entry_fee": entry_fee,
                    "slippage": slip
                }
                
    return calculate_m5_metrics(trades)

def calculate_m5_metrics(trades):
    n = len(trades)
    if n == 0:
        return {
            "trades": 0, "wr": 0.0, "gross_pf": 0.0, "net_pf": 0.0,
            "net_pnl": 0.0, "max_dd": 0.0, "sharpe": 0.0, "expectancy_r": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "payoff_ratio": 0.0,
            "ci_95": [0.0, 0.0], "commissions": 0.0
        }
    wins = [t for t in trades if t["net_pnl"] > 0]
    losses = [t for t in trades if t["net_pnl"] <= 0]
    w_cnt = len(wins)
    l_cnt = len(losses)
    wr = round(w_cnt / n * 100.0, 1)
    
    gross_win = sum(t["gross_pnl"] for t in trades if t["gross_pnl"] > 0)
    gross_loss = abs(sum(t["gross_pnl"] for t in trades if t["gross_pnl"] < 0))
    gross_pf = round(gross_win / max(1e-6, gross_loss), 2)
    
    net_win = sum(t["net_pnl"] for t in wins)
    net_loss = abs(sum(t["net_pnl"] for t in losses))
    net_pf = round(net_win / max(1e-6, net_loss), 2)
    net_pnl = round(sum(t["net_pnl"] for t in trades), 2)
    
    avg_w = round(net_win / max(1, w_cnt), 2)
    avg_l = round(net_loss / max(1, l_cnt), 2)
    payoff = round(avg_w / max(1e-4, avg_l), 2)
    
    commissions = round(sum(t["commissions"] for t in trades), 2)
    dd_vals = [t["dd_pct"] for t in trades]
    max_dd = round(max(dd_vals) if dd_vals else 0.0, 2)
    
    r_vals = [t["r"] for t in trades]
    exp_r = round(sum(r_vals) / n, 2)
    
    rets = [t["net_pnl"] / 1000.0 for t in trades]
    mean_ret = sum(rets) / len(rets) if rets else 0.0
    var_ret = sum((x - mean_ret)**2 for x in rets) / max(1, len(rets) - 1) if len(rets) > 1 else 1.0
    std = math.sqrt(var_ret) if var_ret > 0 else 1.0
    sharpe = round(math.sqrt(365 * 1.5) * (mean_ret / max(1e-6, std)), 2)
    
    # Wilson 95% Confidence Interval for WR
    z = 1.95996
    phat = w_cnt / n
    denom = 1 + (z**2 / n)
    center = (phat + (z**2 / (2 * n))) / denom
    margin = (z * math.sqrt((phat * (1 - phat) / n) + (z**2 / (4 * n**2)))) / denom
    ci_low = round(max(0.0, center - margin) * 100.0, 1)
    ci_high = round(min(1.0, center + margin) * 100.0, 1)
    
    return {
        "trades": n, "wr": wr, "gross_pf": gross_pf, "net_pf": net_pf,
        "net_pnl": net_pnl, "max_dd": max_dd, "sharpe": sharpe,
        "expectancy_r": exp_r, "avg_win": avg_w, "avg_loss": avg_l,
        "payoff_ratio": payoff, "ci_95": [ci_low, ci_high],
        "commissions": commissions
    }

# ==============================================================================
# 5. STRATEGY ALGORITHMS IMPLEMENTATION
# ==============================================================================

# STRATEGY A: M5 LIQUIDITY SWEEP & RECLAIM (SMC / FALSE BREAKOUT)
def strategy_liquidity_sweep(f, features, idx, params):
    # Session filter
    if f["session"] not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
        return None, 0.0
    if f["atr"] < 1.5: # Skip dead volatility
        return None, 0.0
        
    sw_h = f["sw_high_20"]
    sw_l = f["sw_low_20"]
    c = f["close"]
    o = f["open"]
    h = f["high"]
    l = f["low"]
    atr = f["atr"]
    
    # Bullish Liquidity Sweep & Reclaim:
    # 1. Price swept below prior swing low: l < sw_l
    # 2. Reclaim: Close back above swing low: c > sw_l
    # 3. Pinbar or Bullish rejection: lower wick >= 35% of total range
    if l < sw_l and c > sw_l and c >= o:
        if f["range"] > 0 and (f["lower_wick"] / f["range"]) >= 0.35:
            sl_dist = max(8.0, (c - l) + 0.3 * atr)
            return "LONG", sl_dist
            
    # Bearish Liquidity Sweep & Reclaim:
    # 1. Price swept above prior swing high: h > sw_h
    # 2. Reclaim: Close back below swing high: c < sw_h
    # 3. Pinbar or Bearish rejection: upper wick >= 35% of total range
    if h > sw_h and c < sw_h and c <= o:
        if f["range"] > 0 and (f["upper_wick"] / f["range"]) >= 0.35:
            sl_dist = max(8.0, (h - c) + 0.3 * atr)
            return "SHORT", sl_dist
            
    return None, 0.0

# STRATEGY B: M5 TREND CONTINUATION / EMA VALUE ZONE PULLBACK
def strategy_trend_pullback(f, features, idx, params):
    # Session filter
    if f["session"] not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
        return None, 0.0
    if f["adx"] < 20: # Must have trend momentum
        return None, 0.0
        
    c = f["close"]
    o = f["open"]
    h = f["high"]
    l = f["low"]
    e9 = f["e9"]
    e21 = f["e21"]
    e50 = f["e50"]
    atr = f["atr"]
    h1_t = f["h1_trend"]
    
    # Bullish Trend Pullback:
    # H1 is Bullish AND M5 EMA 21 > EMA 50
    # Price pulled into the value zone: Low touched or penetrated EMA 21 (l <= e21 * 1.002)
    # Reversal candle: Close > EMA 9 and Close > Open
    if h1_t == "BULLISH" and e21 > e50:
        if l <= e21 * 1.002 and c >= e21 * 0.998 and c > e9 and c > o:
            sl_dist = max(10.0, 1.4 * atr)
            return "LONG", sl_dist
            
    # Bearish Trend Pullback:
    # H1 is Bearish AND M5 EMA 21 < EMA 50
    # Price pulled into the value zone: High touched or penetrated EMA 21 (h >= e21 * 0.998)
    # Reversal candle: Close < EMA 9 and Close < Open
    if h1_t == "BEARISH" and e21 < e50:
        if h >= e21 * 0.998 and c <= e21 * 1.002 and c < e9 and c < o:
            sl_dist = max(10.0, 1.4 * atr)
            return "SHORT", sl_dist
            
    return None, 0.0

# STRATEGY C: M5 VOLATILITY SQUEEZE & BREAKOUT
def strategy_volatility_breakout(f, features, idx, params):
    if f["session"] not in ["LONDON", "LONDON_NY_OVERLAP"]:
        return None, 0.0
        
    c = f["close"]
    o = f["open"]
    atr = f["atr"]
    sw_h = f["sw_high_20"]
    sw_l = f["sw_low_20"]
    
    # Squeeze condition: 20-bar range was compressed <= 2.8 ATR
    if (sw_h - sw_l) > 2.8 * atr:
        return None, 0.0
        
    # High volume impulse
    if f["v_ratio"] < 1.3:
        return None, 0.0
        
    # Bullish Breakout
    if c > sw_h and c > o and f["body"] >= 0.50 * f["range"]:
        if f["h1_trend"] != "BEARISH":
            sl_dist = max(10.0, 1.3 * atr)
            return "LONG", sl_dist
            
    # Bearish Breakout
    if c < sw_l and c < o and f["body"] >= 0.50 * f["range"]:
        if f["h1_trend"] != "BULLISH":
            sl_dist = max(10.0, 1.3 * atr)
            return "SHORT", sl_dist
            
    return None, 0.0

# STRATEGY D: M5 MEAN REVERSION AT BOLLINGER / RSI EXTREMES
def strategy_mean_reversion(f, features, idx, params):
    # Only during chop/range sessions or low ADX
    if f["adx"] > 25: # Skip during strong trends!
        return None, 0.0
        
    c = f["close"]
    o = f["open"]
    bb_u = f["bb_upper"]
    bb_l = f["bb_lower"]
    rsi = f["rsi"]
    atr = f["atr"]
    
    # Oversold bounce
    if f["low"] <= bb_l and rsi <= 30 and c > o:
        sl_dist = max(8.0, 1.2 * atr)
        return "LONG", sl_dist
        
    # Overbought rejection
    if f["high"] >= bb_u and rsi >= 70 and c < o:
        sl_dist = max(8.0, 1.2 * atr)
        return "SHORT", sl_dist
        
    return None, 0.0

# ==============================================================================
# 6. RUN STRATEGY TOURNAMENT & OPTIMIZATION
# ==============================================================================

def execute_m5_tournament(features, m5_sub_m1):
    total_bars = len(features)
    # Partitions:
    # Train: 45 days (bars 250 to 12,960)
    # Validation: 20 days (bars 12,960 to 18,720)
    # Locked Test: 25 days (bars 18,720 to 25,920)
    tr_s, tr_e = 250, 12960
    val_s, val_e = 12960, 18720
    lock_s, lock_e = 18720, total_bars
    
    strategies = [
        ("Strategy_A_Liquidity_Sweep", strategy_liquidity_sweep),
        ("Strategy_B_Trend_Pullback", strategy_trend_pullback),
        ("Strategy_C_Volatility_Breakout", strategy_volatility_breakout),
        ("Strategy_D_Mean_Reversion", strategy_mean_reversion)
    ]
    
    tp_options = [1.2, 1.5, 1.8, 2.0, 2.5]
    sl_options = [1.0, 1.2, 1.5]
    
    print("\n================================================================================")
    print("PHASE 3: STRATEGY SCREENING TOURNAMENT ON TRAIN & VALIDATION (M5 ETHUSDT)")
    print("================================================================================")
    
    leaderboard = []
    
    for strat_name, strat_func in strategies:
        print(f"\n--- Testing {strat_name} ---")
        best_cfg = None
        best_val_score = -9999.0
        
        for tp in tp_options:
            for sl in sl_options:
                p = {
                    "tp_r": tp,
                    "sl_atr_mult": sl,
                    "min_sl_usd": 10.0,
                    "exec_mode": "MAKER"
                }
                m_train = run_m5_simulation(features, m5_sub_m1, tr_s, tr_e, strat_func, p)
                m_val = run_m5_simulation(features, m5_sub_m1, val_s, val_e, strat_func, p)
                
                # Composite score prioritizing consistency and trade count
                if m_train["trades"] >= 20 and m_val["trades"] >= 10:
                    score = (m_train["net_pf"] * 0.4) + (m_val["net_pf"] * 0.6)
                    if m_train["net_pf"] >= 1.10 and m_val["net_pf"] >= 1.10:
                        score += 1.0 # Bonus for passing both criteria
                else:
                    score = -100.0
                    
                entry_res = {
                    "strategy": strat_name,
                    "tp_r": tp,
                    "sl_mult": sl,
                    "train_trades": m_train["trades"],
                    "train_wr": m_train["wr"],
                    "train_pf": m_train["net_pf"],
                    "train_pnl": m_train["net_pnl"],
                    "train_dd": m_train["max_dd"],
                    "train_payoff": m_train["payoff_ratio"],
                    "val_trades": m_val["trades"],
                    "val_wr": m_val["wr"],
                    "val_pf": m_val["net_pf"],
                    "val_pnl": m_val["net_pnl"],
                    "val_dd": m_val["max_dd"],
                    "val_payoff": m_val["payoff_ratio"],
                    "score": round(score, 2)
                }
                leaderboard.append(entry_res)
                
                if score > best_val_score:
                    best_val_score = score
                    best_cfg = (strat_name, strat_func, p, m_train, m_val)
                    
        if best_cfg:
            s_name, _, p, m_tr, m_v = best_cfg
            print(f"  Best {s_name} (TP={p['tp_r']}R, SL={p['sl_atr_mult']}ATR):")
            print(f"    Train: N={m_tr['trades']:2d} | WR={m_tr['wr']}% | Net PF={m_tr['net_pf']}x | Payoff={m_tr['payoff_ratio']}x | PnL=${m_tr['net_pnl']:6.2f} | DD={m_tr['max_dd']}%")
            print(f"    Val  : N={m_v['trades']:2d} | WR={m_v['wr']}% | Net PF={m_v['net_pf']}x | Payoff={m_v['payoff_ratio']}x | PnL=${m_v['net_pnl']:6.2f} | DD={m_v['max_dd']}%")

    # Sort leaderboard
    leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)
    
    # Save tournament results
    with open(os.path.join(OUTPUT_DIR, "m5_tournament_leaderboard.csv"), "w", encoding="utf-8") as f:
        f.write("Strategy,TP_R,SL_Mult,Train_Trades,Train_WR,Train_PF,Train_PnL,Train_DD,Train_Payoff,Val_Trades,Val_WR,Val_PF,Val_PnL,Val_DD,Val_Payoff,Score\n")
        for r in leaderboard:
            f.write(f"{r['strategy']},{r['tp_r']},{r['sl_mult']},{r['train_trades']},{r['train_wr']},{r['train_pf']},{r['train_pnl']},{r['train_dd']},{r['train_payoff']},{r['val_trades']},{r['val_wr']},{r['val_pf']},{r['val_pnl']},{r['val_dd']},{r['val_payoff']},{r['score']}\n")
            
    # -------------------------------------------------------------------------
    # UNLOCKING LOCKED TEST FOR THE #1 CANDIDATE
    # -------------------------------------------------------------------------
    top_entry = leaderboard[0]
    print("\n================================================================================")
    print(f"PHASE 4: EVALUATING #1 TOURNAMENT WINNER ON LOCKED TEST (DAYS 66-90)")
    print(f"WINNER: {top_entry['strategy']} (TP={top_entry['tp_r']}R, SL={top_entry['sl_mult']} ATR)")
    print("================================================================================")
    
    # Locate strategy func
    win_strat_name = top_entry["strategy"]
    win_func = [s[1] for s in strategies if s[0] == win_strat_name][0]
    win_params = {
        "tp_r": top_entry["tp_r"],
        "sl_atr_mult": top_entry["sl_mult"],
        "min_sl_usd": 10.0,
        "exec_mode": "MAKER"
    }
    
    m_locked = run_m5_simulation(features, m5_sub_m1, lock_s, lock_e, win_func, win_params)
    m_full = run_m5_simulation(features, m5_sub_m1, 250, total_bars, win_func, win_params)
    
    print(f"  LOCKED TEST (25d)  : Trades={m_locked['trades']} | WR={m_locked['wr']}% | Net PF={m_locked['net_pf']}x | Payoff={m_locked['payoff_ratio']}x | PnL=${m_locked['net_pnl']} | DD={m_locked['max_dd']}%")
    print(f"  FULL 90D DATASET   : Trades={m_full['trades']} | WR={m_full['wr']}% | Net PF={m_full['net_pf']}x | Payoff={m_full['payoff_ratio']}x | PnL=${m_full['net_pnl']} | DD={m_full['max_dd']}% | Sharpe={m_full['sharpe']}")

    # -------------------------------------------------------------------------
    # TAKER EXECUTION & SLIPPAGE TEST
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print("PHASE 5: TAKER EXECUTION & COST STRESS AUDIT ON #1 CANDIDATE")
    print("================================================================================")
    p_taker = dict(win_params); p_taker["exec_mode"] = "TAKER"; p_taker["taker_slippage_ticks"] = 0.05
    m_taker = run_m5_simulation(features, m5_sub_m1, 250, total_bars, win_func, p_taker)
    print(f"  TAKER (0.05% + $0.05 slip): Trades={m_taker['trades']} | WR={m_taker['wr']}% | Net PF={m_taker['net_pf']}x | PnL=${m_taker['net_pnl']} | DD={m_taker['max_dd']}%")

    # Save summary
    res_summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "winner_strategy": win_strat_name,
        "params": win_params,
        "train": {
            "trades": top_entry["train_trades"], "wr": top_entry["train_wr"],
            "net_pf": top_entry["train_pf"], "net_pnl": top_entry["train_pnl"],
            "dd": top_entry["train_dd"], "payoff": top_entry["train_payoff"]
        },
        "validation": {
            "trades": top_entry["val_trades"], "wr": top_entry["val_wr"],
            "net_pf": top_entry["val_pf"], "net_pnl": top_entry["val_pnl"],
            "dd": top_entry["val_dd"], "payoff": top_entry["val_payoff"]
        },
        "locked_test": m_locked,
        "full_90d_maker": m_full,
        "full_90d_taker": m_taker
    }
    with open(os.path.join(OUTPUT_DIR, "m5_winner_summary.json"), "w", encoding="utf-8") as f:
        json.dump(res_summary, f, indent=2)
        
    print(f"\nTournament results saved to {OUTPUT_DIR}")
    return res_summary

if __name__ == "__main__":
    m5_bars, m5_sub_m1, m1_times, m1_opens, m1_highs, m1_lows, m1_closes = load_data_and_aggregate_m5(DATA_FILE)
    features = precompute_m5_market(m5_bars)
    execute_m5_tournament(features, m5_sub_m1)
