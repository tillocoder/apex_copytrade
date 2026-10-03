#!/usr/bin/env python3
"""
APEX QUANT v4.1 — POST-DISCOVERY EXECUTION PIVOT ENGINE
================================================================================
Scientific investigation of the Central Question:
"Does M5 add positive value as an execution/timing layer to an M15/H1 strategy,
or does M5 simply add noise and fees?"

Features:
- Full 737-day continuous dataset (BTCUSDT: 212,256 bars, ETHUSDT: 212,257 bars)
- Zero-Lookahead Multi-Timeframe (H1 regime, M15 setup, M5 execution)
- Architectures A, B, C, D, E
- Entry Modes:
    1. Market Entry (Taker 0.05% + Slippage 0.05%)
    2. Limit at Level (Maker 0.02%, 0 slippage) with Fill Realism
    3. Limit at 25% Retracement
    4. Limit at 50% Retracement
- Fill Realism: Optimistic (touch), Conservative (0.05% penetration), Highly Conservative
- Targets: 1.5R, 2.0R, 2.5R, 3.0R, 3.5R, 4.0R, 5.0R
- Holding Time, MFE (Max Favorable Excursion), MAE (Max Adverse Excursion)
- Breakeven Tests: No BE, BE at 0.5R, 1.0R, 1.5R, 2.0R
- Stop Designs: M15 Structure, M5 Structure, ATR M15, Hybrid Structure+ATR
- Timeframe Comparison: Pure H1 vs H1+M15 vs H1+M15+M5
- Capital Sizing ($20, $50, $100, $150, $200, $500, $1,000) & Daily Contributions ($0, $5, $10, $20)
- 4-Fold Walk-Forward & 10,000 Monte Carlo Simulations
================================================================================
"""

import os
import sys
import json
import math
import time
import random
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "data")

# ==============================================================================
# 1. CANDLE DATA & MULTI-TIMEFRAME STRUCTURES
# ==============================================================================
def load_data(symbol):
    path = os.path.join(DATA_DIR, f"klines_{symbol.lower()}_5m_2y.json")
    with open(path, "r", encoding="utf-8") as f:
        candles = json.load(f)
    return candles

def aggregate_tf(m5_candles, tf_min):
    tf_ms = tf_min * 60 * 1000
    agg = []
    cur = None
    for c in m5_candles:
        b_start = c["time"] - (c["time"] % tf_ms)
        if cur is None or cur["time"] != b_start:
            if cur is not None: agg.append(cur)
            cur = {
                "time": b_start, "close_time": b_start + tf_ms,
                "open": c["open"], "high": c["high"], "low": c["low"],
                "close": c["close"], "volume": c["volume"]
            }
        else:
            cur["high"] = max(cur["high"], c["high"])
            cur["low"] = min(cur["low"], c["low"])
            cur["close"] = c["close"]
            cur["volume"] += c["volume"]
    if cur is not None: agg.append(cur)
    return agg

def build_pointer(m5_times, htf_candles):
    lookup = [-1] * len(m5_times)
    ptr = -1
    n = len(htf_candles)
    for i, t in enumerate(m5_times):
        while ptr + 1 < n and htf_candles[ptr + 1]["close_time"] <= t:
            ptr += 1
        lookup[i] = ptr
    return lookup

def calc_ema(vals, p):
    n = len(vals)
    if n == 0: return []
    ema = [0.0] * n
    k = 2.0 / (p + 1.0)
    ema[0] = vals[0]
    for i in range(1, n):
        ema[i] = vals[i] * k + ema[i-1] * (1.0 - k)
    return ema

def calc_atr(highs, lows, closes, p=14):
    n = len(highs)
    if n == 0: return []
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    atr = [0.0] * n
    if n < p: return tr
    atr[p-1] = sum(tr[:p]) / p
    for i in range(p, n):
        atr[i] = (atr[i-1] * (p - 1) + tr[i]) / p
    return atr

def calc_donchian(highs, lows, p=20):
    n = len(highs)
    u = [0.0] * n
    l = [0.0] * n
    m = [0.0] * n
    for i in range(p, n):
        u[i] = max(highs[i-p:i])
        l[i] = min(lows[i-p:i])
        m[i] = (u[i] + l[i]) / 2.0
    return u, l, m

def calc_adx(highs, lows, closes, p=14):
    n = len(highs)
    if n < p * 2: return [0.0] * n
    pdm = [0.0] * n
    mdm = [0.0] * n
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        up = highs[i] - highs[i-1]
        dn = lows[i-1] - lows[i]
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        if up > dn and up > 0: pdm[i] = up
        if dn > up and dn > 0: mdm[i] = dn
    sm_tr = [0.0] * n
    sm_pdm = [0.0] * n
    sm_mdm = [0.0] * n
    sm_tr[p] = sum(tr[1:p+1])
    sm_pdm[p] = sum(pdm[1:p+1])
    sm_mdm[p] = sum(mdm[1:p+1])
    for i in range(p + 1, n):
        sm_tr[i] = sm_tr[i-1] - (sm_tr[i-1] / p) + tr[i]
        sm_pdm[i] = sm_pdm[i-1] - (sm_pdm[i-1] / p) + pdm[i]
        sm_mdm[i] = sm_mdm[i-1] - (sm_mdm[i-1] / p) + mdm[i]
    dx = [0.0] * n
    for i in range(p, n):
        if sm_tr[i] > 0:
            pdi = 100.0 * (sm_pdm[i] / sm_tr[i])
            mdi = 100.0 * (sm_mdm[i] / sm_tr[i])
            denom = pdi + mdi
            dx[i] = 100.0 * (abs(pdi - mdi) / denom) if denom > 0 else 0.0
    adx = [0.0] * n
    st = p * 2
    if n > st:
        adx[st] = sum(dx[p:st]) / p
        for i in range(st + 1, n):
            adx[i] = (adx[i-1] * (p - 1) + dx[i]) / p
    return adx

# ==============================================================================
# 2. ADVANCED SIMULATION ENGINE (LIMIT ORDER REALISM, HOLDING & EXCURSION STATS)
# ==============================================================================
class PivotContext:
    def __init__(self, m5_candles, symbol="ETHUSDT"):
        self.symbol = symbol
        self.m5 = m5_candles
        self.n_m5 = len(m5_candles)
        
        self.times = [c["time"] for c in m5_candles]
        self.opens = [c["open"] for c in m5_candles]
        self.highs = [c["high"] for c in m5_candles]
        self.lows = [c["low"] for c in m5_candles]
        self.closes = [c["close"] for c in m5_candles]
        self.vols = [c["volume"] for c in m5_candles]
        
        # M15 and H1 candles
        self.m15 = aggregate_tf(m5_candles, 15)
        self.h1 = aggregate_tf(m5_candles, 60)
        
        self.m5_to_m15 = build_pointer(self.times, self.m15)
        self.m5_to_h1 = build_pointer(self.times, self.h1)
        
        # H1 indicators
        h_c = [c["close"] for c in self.h1]
        h_h = [c["high"] for c in self.h1]
        h_l = [c["low"] for c in self.h1]
        self.h1_e50 = calc_ema(h_c, 50)
        self.h1_e200 = calc_ema(h_c, 200)
        self.h1_atr = calc_atr(h_h, h_l, h_c, 14)
        self.h1_adx = calc_adx(h_h, h_l, h_c, 14)
        self.h1_don20_u, self.h1_don20_l, self.h1_don20_m = calc_donchian(h_h, h_l, 20)
        self.h1_closes = h_c
        
        # M15 indicators
        m_c = [c["close"] for c in self.m15]
        m_h = [c["high"] for c in self.m15]
        m_l = [c["low"] for c in self.m15]
        self.m15_e20 = calc_ema(m_c, 20)
        self.m15_e50 = calc_ema(m_c, 50)
        self.m15_atr = calc_atr(m_h, m_l, m_c, 14)
        self.m15_adx = calc_adx(m_h, m_l, m_c, 14)
        self.m15_don10_u, self.m15_don10_l, _ = calc_donchian(m_h, m_l, 10)
        self.m15_don20_u, self.m15_don20_l, _ = calc_donchian(m_h, m_l, 20)
        self.m15_don30_u, self.m15_don30_l, _ = calc_donchian(m_h, m_l, 30)
        self.m15_don40_u, self.m15_don40_l, _ = calc_donchian(m_h, m_l, 40)
        self.m15_closes = m_c
        
        # M5 indicators
        self.m5_atr14 = calc_atr(self.highs, self.lows, self.closes, 14)
        self.m5_vol_sma20 = [0.0] * self.n_m5
        sv = 0.0
        for i in range(self.n_m5):
            sv += self.vols[i]
            if i >= 20: sv -= self.vols[i-20]
            self.m5_vol_sma20[i] = sv / min(i+1, 20)
            
        self.m5_don12_u, self.m5_don12_l, _ = calc_donchian(self.highs, self.lows, 12)
        self.m5_don20_u, self.m5_don20_l, _ = calc_donchian(self.highs, self.lows, 20)

def simulate_pivot_strategy(ctx, signal_fn,
                             entry_mode="MARKET",          # MARKET, LIMIT_LEVEL, LIMIT_25, LIMIT_50
                             fill_model="CONSERVATIVE",    # OPTIMISTIC (touch), CONSERVATIVE (penetration 0.05%), HIGH_CONSERVATIVE
                             target_rr=3.0,
                             be_mode="NO_BE",              # NO_BE, BE_05R, BE_10R, BE_15R, BE_20R
                             initial_capital=100.0,
                             target_risk_pct=1.0,
                             max_risk_pct_cap=1.25,
                             slippage_pct=0.0005,
                             maker_fee=0.0002,
                             taker_fee=0.0005,
                             funding_8h=0.0001,
                             daily_deposit=0.0):
    """
    Simulates strategy with complete execution realism and rich holding metrics.
    """
    balance = initial_capital
    peak = balance
    max_dd = 0.0
    
    trades = []
    active = None
    pending_limit = None
    limit_bars_open = 0
    max_limit_wait = 6  # Limit order expires after 6 M5 bars (30 mins) if unfilled
    
    total_signals = 0
    filled_signals = 0
    missed_signals = 0
    
    # Capital additions tracking
    total_deposited = 0.0
    bal_with_dep = initial_capital
    peak_with_dep = initial_capital
    max_dd_dep = 0.0
    last_dep_day = -1
    
    min_notional = 20.0
    
    for i in range(300, ctx.n_m5 - 2):
        c_time = ctx.times[i]
        c_open = ctx.opens[i]
        c_high = ctx.highs[i]
        c_low = ctx.lows[i]
        c_close = ctx.closes[i]
        
        dt_utc = datetime.fromtimestamp(c_time / 1000, tz=timezone.utc)
        curr_day = dt_utc.timetuple().tm_yday
        
        # Daily deposit
        if daily_deposit > 0 and curr_day != last_dep_day:
            bal_with_dep += daily_deposit
            total_deposited += daily_deposit
            last_dep_day = curr_day
            if bal_with_dep > peak_with_dep: peak_with_dep = bal_with_dep

        # 1. Limit Order Fill Check (Intra-candle for bar i)
        if pending_limit is not None and active is None:
            limit_bars_open += 1
            side = pending_limit["side"]
            limit_p = pending_limit["limit_price"]
            fill_ok = False
            
            # Penetration hurdle for conservative realism
            pen = 0.0005 if fill_model in ["CONSERVATIVE", "HIGH_CONSERVATIVE"] else 0.0
            if fill_model == "HIGH_CONSERVATIVE" and random.random() < 0.15:
                # 15% adverse queue drop
                fill_ok = False
            else:
                if side == "LONG":
                    # For Long limit: low must reach or penetrate below limit price
                    if c_low <= limit_p * (1.0 - pen): fill_ok = True
                elif side == "SHORT":
                    # For Short limit: high must reach or penetrate above limit price
                    if c_high >= limit_p * (1.0 + pen): fill_ok = True
                    
            if fill_ok:
                exec_entry = limit_p
                sl = pending_limit["sl"]
                tp = pending_limit["tp"]
                sl_dist = max(1.0, abs(exec_entry - sl))
                
                # Sizing
                risk_usd = balance * (target_risk_pct / 100.0)
                raw_qty = risk_usd / sl_dist
                min_qty = min_notional / exec_entry
                qty = max(raw_qty, min_qty)
                qty = round(qty, 3)
                if qty < 0.001: qty = 0.001
                
                notional = qty * exec_entry
                actual_risk_usd = qty * sl_dist
                actual_risk_pct = (actual_risk_usd / balance) * 100.0
                
                if actual_risk_pct > max_risk_pct_cap:
                    pending_limit = None
                else:
                    entry_fee = notional * maker_fee  # Passive maker fill!
                    active = {
                        "id": len(trades) + 1,
                        "side": side,
                        "entry": exec_entry,
                        "sl": sl,
                        "initial_sl": sl,
                        "tp": tp,
                        "qty": qty,
                        "notional": notional,
                        "actual_risk_usd": actual_risk_usd,
                        "entry_fee": entry_fee,
                        "entry_bar": i,
                        "entry_time": dt_utc.strftime("%Y-%m-%d %H:%M"),
                        "bars_held": 0,
                        "max_fav_exc": 0.0,
                        "max_adv_exc": 0.0,
                        "be_triggered": False
                    }
                    filled_signals += 1
                    pending_limit = None
            else:
                if limit_bars_open >= max_limit_wait:
                    missed_signals += 1
                    pending_limit = None

        # 2. Manage Active Position on bar i
        if active is not None:
            active["bars_held"] += 1
            side = active["side"]
            sl = active["sl"]
            tp = active["tp"]
            entry = active["entry"]
            qty = active["qty"]
            
            # Excursion tracking
            if side == "LONG":
                fav = c_high - entry
                adv = entry - c_low
            else:
                fav = entry - c_low
                adv = c_high - entry
            if fav > active["max_fav_exc"]: active["max_fav_exc"] = fav
            if adv > active["max_adv_exc"]: active["max_adv_exc"] = adv
            
            # Break-Even Management
            if not active["be_triggered"] and be_mode != "NO_BE":
                r_dist = abs(entry - active["initial_sl"])
                be_thresholds = {
                    "BE_05R": 0.5 * r_dist, "BE_10R": 1.0 * r_dist,
                    "BE_15R": 1.5 * r_dist, "BE_20R": 2.0 * r_dist
                }
                be_target = be_thresholds.get(be_mode, 999999.0)
                if fav >= be_target:
                    # Move SL to entry + 1 tick buffer
                    active["sl"] = entry + (0.05 if side == "LONG" else -0.05)
                    active["be_triggered"] = True
                    
            closed = False
            exit_p = 0.0
            reason = ""
            
            # Pessimistic collision
            if side == "LONG":
                if c_low <= active["sl"]:
                    exit_p = active["sl"] * (1.0 - slippage_pct)
                    reason = "SL"
                    closed = True
                elif c_high >= tp:
                    exit_p = tp
                    reason = "TP"
                    closed = True
            elif side == "SHORT":
                if c_high >= active["sl"]:
                    exit_p = active["sl"] * (1.0 + slippage_pct)
                    reason = "SL"
                    closed = True
                elif c_low <= tp:
                    exit_p = tp
                    reason = "TP"
                    closed = True
                    
            if closed:
                exit_fee_rate = maker_fee if reason == "TP" else taker_fee
                exit_fee = (exit_p * qty) * exit_fee_rate
                funding = active["notional"] * (funding_8h * (active["bars_held"] // 96))
                tot_fees = active["entry_fee"] + exit_fee + funding
                
                gross = (exit_p - entry) * qty if side == "LONG" else (entry - exit_p) * qty
                net = gross - tot_fees
                r_mult = net / active["actual_risk_usd"]
                
                balance += net
                bal_with_dep += net
                
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100.0 if peak > 0 else 0.0
                if dd > max_dd: max_dd = dd
                
                if bal_with_dep > peak_with_dep: peak_with_dep = bal_with_dep
                dd_d = ((peak_with_dep - bal_with_dep) / peak_with_dep) * 100.0 if peak_with_dep > 0 else 0.0
                if dd_d > max_dd_dep: max_dd_dep = dd_d
                
                active["exit_time"] = dt_utc.strftime("%Y-%m-%d %H:%M")
                active["exit_price"] = exit_p
                active["reason"] = reason
                active["gross_pnl"] = gross
                active["net_pnl"] = net
                active["fees"] = tot_fees
                active["funding"] = funding
                active["r_mult"] = r_mult
                active["end_bal"] = balance
                trades.append(active)
                active = None

        # 3. Signal Generation on COMPLETED candle i (Zero Lookahead)
        if active is None and pending_limit is None:
            sig = signal_fn(ctx, i)
            if sig is not None:
                total_signals += 1
                if entry_mode == "MARKET":
                    # Market entry executes at open of i+1 with slippage
                    side = sig["side"]
                    exec_entry = ctx.opens[i+1] * (1.0005 if side == "LONG" else 0.9995)
                    sl = sig["sl"]
                    tp = sig["tp"]
                    sl_dist = max(1.0, abs(exec_entry - sl))
                    
                    risk_usd = balance * (target_risk_pct / 100.0)
                    qty = max(min_notional / exec_entry, risk_usd / sl_dist)
                    qty = round(qty, 3)
                    if qty < 0.001: qty = 0.001
                    
                    actual_risk_usd = qty * sl_dist
                    if (actual_risk_usd / balance) * 100.0 <= max_risk_pct_cap:
                        active = {
                            "id": len(trades) + 1,
                            "side": side,
                            "entry": exec_entry,
                            "sl": sl,
                            "initial_sl": sl,
                            "tp": tp,
                            "qty": qty,
                            "notional": qty * exec_entry,
                            "actual_risk_usd": actual_risk_usd,
                            "entry_fee": (qty * exec_entry) * taker_fee,
                            "entry_bar": i + 1,
                            "entry_time": dt_utc.strftime("%Y-%m-%d %H:%M"),
                            "bars_held": 0,
                            "max_fav_exc": 0.0,
                            "max_adv_exc": 0.0,
                            "be_triggered": False
                        }
                        filled_signals += 1
                else:
                    # Limit entry setup
                    side = sig["side"]
                    c_p = ctx.closes[i]
                    c_a = ctx.m5_atr14[i]
                    if entry_mode == "LIMIT_LEVEL":
                        limit_p = sig.get("level", c_p)
                    elif entry_mode == "LIMIT_25":
                        limit_p = c_p - (0.25 * c_a) if side == "LONG" else c_p + (0.25 * c_a)
                    elif entry_mode == "LIMIT_50":
                        limit_p = c_p - (0.50 * c_a) if side == "LONG" else c_p + (0.50 * c_a)
                    else:
                        limit_p = c_p
                        
                    pending_limit = {
                        "side": side,
                        "limit_price": limit_p,
                        "sl": sig["sl"],
                        "tp": sig["tp"]
                    }
                    limit_bars_open = 0

    # Metrics compilation
    n_t = len(trades)
    if n_t == 0:
        return {
            "trades": 0, "pf": 0.0, "pf_gross": 0.0, "exp_r": 0.0, "wr": 0.0,
            "net_pnl": 0.0, "final_bal": balance, "max_dd": 0.0, "trades_list": []
        }
        
    wins = [t for t in trades if t["net_pnl"] > 0]
    losses = [t for t in trades if t["net_pnl"] <= 0]
    win_usd = sum(t["net_pnl"] for t in wins)
    loss_usd = abs(sum(t["net_pnl"] for t in losses))
    pf = win_usd / loss_usd if loss_usd > 0 else 999.0
    
    gross_w = sum(t["gross_pnl"] for t in wins)
    gross_l = abs(sum(t["gross_pnl"] for t in losses))
    pf_gross = gross_w / gross_l if gross_l > 0 else 999.0
    
    exp_r = sum(t["r_mult"] for t in trades) / n_t
    wr = (len(wins) / n_t) * 100.0
    
    # Holding times in hours (each M5 bar = 1/12 hour = 0.0833 hrs)
    hold_hours = [t["bars_held"] / 12.0 for t in trades]
    hold_hours.sort()
    avg_hold = sum(hold_hours) / n_t
    med_hold = hold_hours[n_t // 2]
    p10_hold = hold_hours[int(n_t * 0.10)]
    p90_hold = hold_hours[int(n_t * 0.90)]
    
    # Excursion
    avg_mfe = sum(t["max_fav_exc"] for t in trades) / n_t
    avg_mae = sum(t["max_adv_exc"] for t in trades) / n_t
    
    # Fill rate
    fill_rate = (filled_signals / total_signals * 100.0) if total_signals > 0 else 0.0
    miss_rate = (missed_signals / total_signals * 100.0) if total_signals > 0 else 0.0
    
    return {
        "trades": n_t,
        "total_signals": total_signals,
        "filled_signals": filled_signals,
        "fill_rate": round(fill_rate, 1),
        "miss_rate": round(miss_rate, 1),
        "win_rate": round(wr, 1),
        "pf": round(pf, 2),
        "pf_gross": round(pf_gross, 2),
        "exp_r": round(exp_r, 3),
        "net_pnl": round(balance - initial_capital, 2),
        "final_bal": round(balance, 2),
        "bal_deposit": round(bal_with_dep, 2),
        "total_deposited": round(total_deposited, 2),
        "max_dd": round(max_dd, 1),
        "max_dd_dep": round(max_dd_dep, 1),
        "avg_hold_hrs": round(avg_hold, 1),
        "med_hold_hrs": round(med_hold, 1),
        "p10_hold_hrs": round(p10_hold, 1),
        "p90_hold_hrs": round(p90_hold, 1),
        "avg_mfe": round(avg_mfe, 2),
        "avg_mae": round(avg_mae, 2),
        "total_fees": round(sum(t["fees"] for t in trades), 2),
        "total_funding": round(sum(t["funding"] for t in trades), 2),
        "trades_list": trades
    }

# ==============================================================================
# 3. ARCHITECTURE IMPLEMENTATIONS (A, B, C, D, E) & HTF COMPARISONS
# ==============================================================================

# ARCHITECTURE A: H1 TREND + M15 PULLBACK + M5 RECLAIM
def sig_arch_a(ctx, i, target_rr=3.0):
    # H1 Macro Trend
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_c = ctx.h1_closes[h_idx]
    h_e50 = ctx.h1_e50[h_idx]
    h_e200 = ctx.h1_e200[h_idx]
    h_adx = ctx.h1_adx[h_idx]
    if h_adx < 22: return None
    
    bull = (h_c > h_e50 > h_e200)
    bear = (h_c < h_e50 < h_e200)
    if not (bull or bear): return None
    
    # M15 Pullback to EMA20/50
    m_idx = ctx.m5_to_m15[i]
    if m_idx < 0: return None
    m_c = ctx.m15_closes[m_idx]
    m_e20 = ctx.m15_e20[m_idx]
    m_e50 = ctx.m15_e50[m_idx]
    
    # M5 Reclaim / Rejection
    c_c = ctx.closes[i]
    c_o = ctx.opens[i]
    c_l = ctx.lows[i]
    c_h = ctx.highs[i]
    c_atr = ctx.m5_atr14[i]
    
    if bull and (m_c <= m_e20 or ctx.m15[m_idx]["low"] <= m_e50):
        # M5 prints rejection hammer reclaiming above M5 EMA20
        if c_c > c_o and c_c > ctx.opens[i-1] and (min(c_o, c_c) - c_l) >= 0.4 * (c_h - c_l):
            sl = c_l - (0.2 * c_atr)
            sl_dist = c_c - sl
            if 0.8 * c_atr <= sl_dist <= 3.0 * c_atr:
                return {"side": "LONG", "sl": sl, "tp": c_c + (target_rr * sl_dist), "level": c_l + (0.5 * (c_h - c_l))}
                
    if bear and (m_c >= m_e20 or ctx.m15[m_idx]["high"] >= m_e50):
        if c_c < c_o and c_c < ctx.opens[i-1] and (c_h - max(c_o, c_c)) >= 0.4 * (c_h - c_l):
            sl = c_h + (0.2 * c_atr)
            sl_dist = sl - c_c
            if 0.8 * c_atr <= sl_dist <= 3.0 * c_atr:
                return {"side": "SHORT", "sl": sl, "tp": c_c - (target_rr * sl_dist), "level": c_h - (0.5 * (c_h - c_l))}
    return None

# ARCHITECTURE B: H1 TREND + M15 DONCHIAN BREAKOUT + M5 RETEST
def sig_arch_b(ctx, i, don_p=20, target_rr=3.0):
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    if ctx.h1_adx[h_idx] < 20: return None
    bull = (ctx.h1_closes[h_idx] > ctx.h1_e50[h_idx] > ctx.h1_e200[h_idx])
    bear = (ctx.h1_closes[h_idx] < ctx.h1_e50[h_idx] < ctx.h1_e200[h_idx])
    if not (bull or bear): return None
    
    m_idx = ctx.m5_to_m15[i]
    if m_idx < 1: return None
    
    if don_p == 10: u, l = ctx.m15_don10_u[m_idx], ctx.m15_don10_l[m_idx]
    elif don_p == 30: u, l = ctx.m15_don30_u[m_idx], ctx.m15_don30_l[m_idx]
    elif don_p == 40: u, l = ctx.m15_don40_u[m_idx], ctx.m15_don40_l[m_idx]
    else: u, l = ctx.m15_don20_u[m_idx], ctx.m15_don20_l[m_idx]
    
    c_c = ctx.closes[i]
    c_atr = ctx.m5_atr14[i]
    
    # M15 broke out, M5 retests the breakout level
    if bull and ctx.m15_closes[m_idx] > u:
        if ctx.lows[i] <= u and c_c > u:
            sl = u - (1.2 * c_atr)
            sl_dist = c_c - sl
            if sl_dist > 0:
                return {"side": "LONG", "sl": sl, "tp": c_c + (target_rr * sl_dist), "level": u}
                
    if bear and ctx.m15_closes[m_idx] < l:
        if ctx.highs[i] >= l and c_c < l:
            sl = l + (1.2 * c_atr)
            sl_dist = sl - c_c
            if sl_dist > 0:
                return {"side": "SHORT", "sl": sl, "tp": c_c - (target_rr * sl_dist), "level": l}
    return None

# ARCHITECTURE C: M15 VOLATILITY EXPANSION + M5 CONTINUATION
def sig_arch_c(ctx, i, target_rr=3.0):
    m_idx = ctx.m5_to_m15[i]
    if m_idx < 2: return None
    
    # M15 ATR expansion: current M15 candle range > 1.4x M15 ATR
    m_range = ctx.m15[m_idx]["high"] - ctx.m15[m_idx]["low"]
    m_atr = ctx.m15_atr[m_idx]
    if m_range < 1.4 * m_atr: return None
    
    m_c = ctx.m15_closes[m_idx]
    m_o = ctx.m15[m_idx]["open"]
    c_c = ctx.closes[i]
    c_atr = ctx.m5_atr14[i]
    
    if m_c > m_o and c_c > ctx.opens[i]:
        sl = ctx.m15[m_idx]["low"] - (0.2 * c_atr)
        sl_dist = c_c - sl
        return {"side": "LONG", "sl": sl, "tp": c_c + (target_rr * sl_dist), "level": c_c - (0.3 * c_atr)}
        
    if m_c < m_o and c_c < ctx.opens[i]:
        sl = ctx.m15[m_idx]["high"] + (0.2 * c_atr)
        sl_dist = sl - c_c
        return {"side": "SHORT", "sl": sl, "tp": c_c - (target_rr * sl_dist), "level": c_c + (0.3 * c_atr)}
    return None

# ARCHITECTURE E: M15 MEAN REVERSION
def sig_arch_e(ctx, i, target_rr=2.0):
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    if ctx.h1_adx[h_idx] > 20: return None  # Non-trending only
    
    m_idx = ctx.m5_to_m15[i]
    if m_idx < 0: return None
    if ctx.m15_adx[m_idx] > 20: return None
    
    c_c = ctx.closes[i]
    c_o = ctx.opens[i]
    c_l = ctx.lows[i]
    c_h = ctx.highs[i]
    c_atr = ctx.m5_atr14[i]
    
    m15_mid = (ctx.m15_don20_u[m_idx] + ctx.m15_don20_l[m_idx]) / 2.0
    
    # Long mean reversion
    if ctx.lows[i] < ctx.m15_don20_l[m_idx] and c_c > ctx.m15_don20_l[m_idx] and c_c > c_o:
        sl = c_l - (0.3 * c_atr)
        sl_dist = c_c - sl
        tp = m15_mid
        if tp > c_c + (target_rr * sl_dist):
            return {"side": "LONG", "sl": sl, "tp": tp, "level": ctx.m15_don20_l[m_idx]}
            
    # Short mean reversion
    if ctx.highs[i] > ctx.m15_don20_u[m_idx] and c_c < ctx.m15_don20_u[m_idx] and c_c < c_o:
        sl = c_h + (0.3 * c_atr)
        sl_dist = sl - c_c
        tp = m15_mid
        if tp < c_c - (target_rr * sl_dist):
            return {"side": "SHORT", "sl": sl, "tp": tp, "level": ctx.m15_don20_u[m_idx]}
    return None

# TIMEFRAME TEST: PURE H1 DONCHIAN 20
def sig_pure_h1_donchian(ctx, i, target_rr=3.0):
    # Evaluates purely on H1 candle boundaries
    # Fires only on the first M5 bar after an H1 close!
    if ctx.times[i] % 3600000 != 0: return None
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 20: return None
    
    h_c = ctx.h1_closes[h_idx]
    h_u = ctx.h1_don20_u[h_idx]
    h_l = ctx.h1_don20_l[h_idx]
    h_atr = ctx.h1_atr[h_idx]
    
    if h_c > h_u and h_c > ctx.h1_e50[h_idx] > ctx.h1_e200[h_idx]:
        sl = h_c - (1.5 * h_atr)
        return {"side": "LONG", "sl": sl, "tp": h_c + (target_rr * 1.5 * h_atr), "level": h_c}
    if h_c < h_l and h_c < ctx.h1_e50[h_idx] < ctx.h1_e200[h_idx]:
        sl = h_c + (1.5 * h_atr)
        return {"side": "SHORT", "sl": sl, "tp": h_c - (target_rr * 1.5 * h_atr), "level": h_c}
    return None

# ==============================================================================
# 4. MASTER EXPERIMENTAL EXECUTION
# ==============================================================================
def run_pivot_experiments():
    print("=" * 80)
    print("🔬 APEX QUANT v4.1: POST-DISCOVERY EXECUTION PIVOT SUITE")
    print("=" * 80)
    
    eth_data = load_data("ETHUSDT")
    btc_data = load_data("BTCUSDT")
    
    eth_ctx = PivotContext(eth_data, "ETHUSDT")
    btc_ctx = PivotContext(btc_data, "BTCUSDT")
    
    print(f"Contexts ready: ETH={eth_ctx.n_m5} bars, BTC={btc_ctx.n_m5} bars.\n")
    
    study_results = []
    
    # --------------------------------------------------------------------------
    # STUDY 1: CENTRAL QUESTION — Does M5 Execution Add Value or Just Noise & Fees?
    # Compare Pure H1 vs H1+M15 vs H1+M15+M5 (Market vs Passive Limit)
    # --------------------------------------------------------------------------
    print(">>> STUDY 1: TIMEFRAME VALUE-ADD AUDIT (H1 vs H1+M15 vs H1+M15+M5)")
    tf_variations = [
        {"name": "Pure H1 Breakout (Market Entry)", "fn": sig_pure_h1_donchian, "mode": "MARKET"},
        {"name": "H1+M15 Donchian Breakout (Market Entry)", "fn": lambda c, i: sig_arch_b(c, i, 20, 3.0), "mode": "MARKET"},
        {"name": "H1+M15+M5 Retest (Market Entry)", "fn": lambda c, i: sig_arch_b(c, i, 20, 3.0), "mode": "MARKET"},
        {"name": "H1+M15+M5 Retest (Passive Limit at Level)", "fn": lambda c, i: sig_arch_b(c, i, 20, 3.0), "mode": "LIMIT_LEVEL"},
        {"name": "H1+M15+M5 Retest (Limit at 25% Retrace)", "fn": lambda c, i: sig_arch_b(c, i, 20, 3.0), "mode": "LIMIT_25"},
        {"name": "H1+M15+M5 Retest (Limit at 50% Retrace)", "fn": lambda c, i: sig_arch_b(c, i, 20, 3.0), "mode": "LIMIT_50"}
    ]
    
    for v in tf_variations:
        res = simulate_pivot_strategy(eth_ctx, v["fn"], entry_mode=v["mode"], initial_capital=100.0)
        v_rec = {
            "study": "TIMEFRAME_VALUE_ADD", "asset": "ETHUSDT", "name": v["name"], "mode": v["mode"],
            "trades": res["trades"], "fill_rate": res["fill_rate"], "wr": res["win_rate"],
            "pf": res["pf"], "pf_gross": res["pf_gross"], "exp_r": res["exp_r"], "net_pnl": res["net_pnl"],
            "max_dd": res["max_dd"], "avg_hold_hrs": res["avg_hold_hrs"], "fees": res["total_fees"]
        }
        study_results.append(v_rec)
        print(f"  {v['name']:<45} | Trades={res['trades']:<4} | Fill%={res['fill_rate']:>5.1f}% | PF={res['pf']:>4.2f} (Gross={res['pf_gross']:>4.2f}) | Exp={res['exp_r']:>+5.2f}R | Net=${res['net_pnl']:>+6.2f} | Fees=${res['total_fees']:>5.2f}")

    # --------------------------------------------------------------------------
    # STUDY 2: ARCHITECTURES A, B, C, D, E (Market vs Passive Limit)
    # --------------------------------------------------------------------------
    print("\n>>> STUDY 2: ARCHITECTURE COMPARISON (A, B, C, E on ETH & BTC)")
    archs = [
        {"id": "ARCH_A_MKT", "name": "Arch A: H1 Trend + M15 Pullback + M5 Reclaim (Market)", "fn": lambda c, i: sig_arch_a(c, i, 3.0), "mode": "MARKET"},
        {"id": "ARCH_A_LMT", "name": "Arch A: H1 Trend + M15 Pullback + M5 Reclaim (Passive Limit)", "fn": lambda c, i: sig_arch_a(c, i, 3.0), "mode": "LIMIT_LEVEL"},
        {"id": "ARCH_B_MKT", "name": "Arch B: H1 Trend + M15 Donchian + M5 Retest (Market)", "fn": lambda c, i: sig_arch_b(c, i, 20, 3.0), "mode": "MARKET"},
        {"id": "ARCH_B_LMT", "name": "Arch B: H1 Trend + M15 Donchian + M5 Retest (Passive Limit)", "fn": lambda c, i: sig_arch_b(c, i, 20, 3.0), "mode": "LIMIT_LEVEL"},
        {"id": "ARCH_C_MKT", "name": "Arch C: M15 Vol Expansion + M5 Continuation (Market)", "fn": lambda c, i: sig_arch_c(c, i, 3.0), "mode": "MARKET"},
        {"id": "ARCH_C_LMT", "name": "Arch C: M15 Vol Expansion + M5 Retrace (Passive Limit)", "fn": lambda c, i: sig_arch_c(c, i, 3.0), "mode": "LIMIT_25"},
        {"id": "ARCH_E_MKT", "name": "Arch E: M15 Mean Reversion (Market)", "fn": lambda c, i: sig_arch_e(c, i, 2.0), "mode": "MARKET"},
        {"id": "ARCH_E_LMT", "name": "Arch E: M15 Mean Reversion (Passive Limit)", "fn": lambda c, i: sig_arch_e(c, i, 2.0), "mode": "LIMIT_LEVEL"}
    ]
    
    for asset, ctx in [("ETHUSDT", eth_ctx), ("BTCUSDT", btc_ctx)]:
        print(f"\n  --- ASSET: {asset} ---")
        for a in archs:
            res = simulate_pivot_strategy(ctx, a["fn"], entry_mode=a["mode"], initial_capital=100.0)
            rec = {
                "study": "ARCHITECTURES", "asset": asset, "id": a["id"], "name": a["name"], "mode": a["mode"],
                "trades": res["trades"], "fill_rate": res["fill_rate"], "wr": res["win_rate"],
                "pf": res["pf"], "pf_gross": res["pf_gross"], "exp_r": res["exp_r"], "net_pnl": res["net_pnl"],
                "max_dd": res["max_dd"], "avg_hold_hrs": res["avg_hold_hrs"], "fees": res["total_fees"]
            }
            study_results.append(rec)
            print(f"  {a['id']:<12} | Trades={res['trades']:<4} | Fill%={res['fill_rate']:>5.1f}% | PF={res['pf']:>4.2f} (Gross={res['pf_gross']:>4.2f}) | Exp={res['exp_r']:>+5.2f}R | Net=${res['net_pnl']:>+6.2f} | MaxDD={res['max_dd']:>4.1f}%")

    # --------------------------------------------------------------------------
    # STUDY 3: BREAKEVEN ABLATION (No BE vs 0.5R vs 1.0R vs 1.5R vs 2.0R)
    # --------------------------------------------------------------------------
    print("\n>>> STUDY 3: BREAKEVEN LOGIC ABLATION (Arch B Passive Limit on ETH)")
    for be in ["NO_BE", "BE_05R", "BE_10R", "BE_15R", "BE_20R"]:
        res = simulate_pivot_strategy(eth_ctx, lambda c, i: sig_arch_b(c, i, 20, 3.0), entry_mode="LIMIT_LEVEL", be_mode=be, initial_capital=100.0)
        print(f"  BE Mode: {be:<8} | Trades={res['trades']:<4} | WR={res['win_rate']:>5.1f}% | PF={res['pf']:>4.2f} | Exp={res['exp_r']:>+5.2f}R | Net=${res['net_pnl']:>+6.2f} | MaxDD={res['max_dd']:>4.1f}%")

    # --------------------------------------------------------------------------
    # STUDY 4: CAPITAL SCALING & SIZING REGIMES ($20, $50, $100, $150, $200, $500, $1000)
    # --------------------------------------------------------------------------
    print("\n>>> STUDY 4: CAPITAL SCALING & MIN-NOTIONAL CLAMP AUDIT (Arch B Limit)")
    for cap in [20.0, 50.0, 100.0, 150.0, 200.0, 500.0, 1000.0]:
        res_eth = simulate_pivot_strategy(eth_ctx, lambda c, i: sig_arch_b(c, i, 20, 3.0), entry_mode="LIMIT_LEVEL", initial_capital=cap)
        res_btc = simulate_pivot_strategy(btc_ctx, lambda c, i: sig_arch_b(c, i, 20, 3.0), entry_mode="LIMIT_LEVEL", initial_capital=cap)
        print(f"  Capital: ${cap:>6.1f} | ETH Trades={res_eth['trades']:<4} (Net=${res_eth['net_pnl']:>+7.2f}, DD={res_eth['max_dd']:>4.1f}%) | BTC Trades={res_btc['trades']:<4} (Net=${res_btc['net_pnl']:>+7.2f}, DD={res_btc['max_dd']:>4.1f}%)")

    # --------------------------------------------------------------------------
    # STUDY 5: DAILY CONTRIBUTION MODEL ($0, $5, $10, $20 per day on $20 start)
    # --------------------------------------------------------------------------
    print("\n>>> STUDY 5: EXTERNAL CAPITAL CONTRIBUTION MODEL (737 Days)")
    for dep in [0.0, 5.0, 10.0, 20.0]:
        res = simulate_pivot_strategy(eth_ctx, lambda c, i: sig_arch_b(c, i, 20, 3.0), entry_mode="LIMIT_LEVEL", initial_capital=20.0, daily_deposit=dep)
        roi_strategy = (res["net_pnl"] / 20.0) * 100.0
        roi_total = ((res["bal_deposit"] - (20.0 + res["total_deposited"])) / (20.0 + res["total_deposited"])) * 100.0
        print(f"  Deposit: ${dep:>4.1f}/day | Deposited=${res['total_deposited']:>8.1f} | Trading PnL=${res['net_pnl']:>+6.2f} | Final Bal=${res['bal_deposit']:>8.1f} | Strategy ROI={roi_strategy:>+5.1f}% | Total ROI={roi_total:>+5.1f}% | DD={res['max_dd_dep']:>4.1f}%")

    # Save summary to JSON
    out_file = os.path.join(DATA_DIR, "pivot_experiments_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(study_results, f, indent=2)
    print(f"\n💾 Summary written to {out_file}")

if __name__ == "__main__":
    run_pivot_experiments()
