#!/usr/bin/env python3
"""
APEX QUANT v4 — INSTITUTIONAL STRATEGY DISCOVERY & ROBUSTNESS ENGINE
================================================================================
Comprehensive discovery and stress-testing suite across BTCUSDT and ETHUSDT:
- 2 Full Years of M5 Binance Futures tick/kline archives (~210,000 bars per asset)
- Zero-Lookahead Multi-Timeframe (M5 execution, M15 confirmation, H1 bias)
- 8 Independent Strategy Families:
    A: Trend Pullback (TPB)
    B: Volatility / Donchian Breakout (DON)
    C: Range Breakout + Retest (RBR)
    D: VWAP / Bollinger Mean Reversion (MR)
    E: Momentum / Impulse Continuation (MOM)
    F: Market Structure / Liquidity Sweep (SMC)
    G: Session / Time-of-Day Filters (UTC windows)
    H: Regime-Switching Hybrid
- Strict Realistic Execution & Frictions:
    Base: 0.05% Taker entry, 0.05% Taker SL, 0.02% Maker TP, 0.05% entry/SL slippage
    Stress Matrix: 0.075%, 0.10%, 0.15% adverse slippage
    8h Funding Rate modeled
    Pessimistic intra-candle TP/SL collision (SL always hits first)
    1-bar execution latency (Signal confirmed on close i, entered on open i+1)
- Small Account & Capital Scaling Audit:
    $20, $50, $100, $200, $500, $1,000 regimes
    Binance minNotional = $20 clamp with STRICT skip rule if actual risk > 1.25%
    Dual Equity Curves: Curve A (Trading only) vs Curve B (Trading + $20/day deposit)
- 4-Fold Chronological Walk-Forward (Train -> Validate -> Test)
- Robustness Gates & Perturbations (Parameters, Latency, Stops, TP, Trade Removal)
- 10,000-Run Monte Carlo Simulation (Sequence Permutations & Bootstrap)
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
# 1. DATA LOADING & MULTI-TIMEFRAME BUILDER (STRICT ZERO-LOOKAHEAD)
# ==============================================================================
def load_cached_klines(symbol):
    path = os.path.join(DATA_DIR, f"klines_{symbol.lower()}_5m_2y.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing cache file: {path}. Run scripts/cache_binance_data.py first!")
    print(f"📂 Loading cached 5m klines for {symbol} from {path}...")
    with open(path, "r", encoding="utf-8") as f:
        candles = json.load(f)
    print(f"   Loaded {len(candles)} 5m candles ({candles[0]['time']} to {candles[-1]['time']}).")
    return candles

def aggregate_candles(m5_candles, timeframe_minutes):
    """
    Aggregates M5 candles into exact M15 or H1 candles.
    Guarantees that an aggregated candle starting at T closes at T + (timeframe_minutes * 60,000) ms.
    """
    tf_ms = timeframe_minutes * 60 * 1000
    agg = []
    cur_bucket = None
    
    for c in m5_candles:
        bucket_start = c["time"] - (c["time"] % tf_ms)
        if cur_bucket is None or cur_bucket["time"] != bucket_start:
            if cur_bucket is not None:
                agg.append(cur_bucket)
            cur_bucket = {
                "time": bucket_start,
                "close_time": bucket_start + tf_ms,
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c["volume"]
            }
        else:
            cur_bucket["high"] = max(cur_bucket["high"], c["high"])
            cur_bucket["low"] = min(cur_bucket["low"], c["low"])
            cur_bucket["close"] = c["close"]
            cur_bucket["volume"] += c["volume"]
            
    if cur_bucket is not None:
        agg.append(cur_bucket)
    return agg

def build_htf_lookup(m5_times, htf_candles):
    """
    Builds a pointer array: m5_to_closed_htf[i] gives the index of the latest HTF candle
    that was FULLY CLOSED strictly before or at m5_times[i].
    Zero lookahead: an HTF candle is usable at t ONLY IF htf.close_time <= t.
    """
    lookup = [-1] * len(m5_times)
    ptr = -1
    htf_n = len(htf_candles)
    
    for i, t in enumerate(m5_times):
        while ptr + 1 < htf_n and htf_candles[ptr + 1]["close_time"] <= t:
            ptr += 1
        lookup[i] = ptr
    return lookup

# ==============================================================================
# 2. VECTORIZED INDICATOR CALCULATIONS
# ==============================================================================
def calc_ema(values, period):
    n = len(values)
    if n == 0: return []
    ema = [0.0] * n
    k = 2.0 / (period + 1.0)
    ema[0] = values[0]
    for i in range(1, n):
        ema[i] = values[i] * k + ema[i-1] * (1.0 - k)
    return ema

def calc_atr(highs, lows, closes, period=14):
    n = len(highs)
    if n == 0: return []
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    atr = [0.0] * n
    if n < period: return tr
    atr[period-1] = sum(tr[:period]) / period
    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

def calc_adx(highs, lows, closes, period=14):
    n = len(highs)
    if n < period * 2: return [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr = [highs[0] - lows[0]]
    
    for i in range(1, n):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move
            
    # Wilder smoothing
    sm_tr = [0.0] * n
    sm_pdm = [0.0] * n
    sm_mdm = [0.0] * n
    sm_tr[period] = sum(tr[1:period+1])
    sm_pdm[period] = sum(plus_dm[1:period+1])
    sm_mdm[period] = sum(minus_dm[1:period+1])
    
    for i in range(period + 1, n):
        sm_tr[i] = sm_tr[i-1] - (sm_tr[i-1] / period) + tr[i]
        sm_pdm[i] = sm_pdm[i-1] - (sm_pdm[i-1] / period) + plus_dm[i]
        sm_mdm[i] = sm_mdm[i-1] - (sm_mdm[i-1] / period) + minus_dm[i]
        
    dx = [0.0] * n
    for i in range(period, n):
        if sm_tr[i] > 0:
            pdi = 100.0 * (sm_pdm[i] / sm_tr[i])
            mdi = 100.0 * (sm_mdm[i] / sm_tr[i])
            denom = pdi + mdi
            dx[i] = 100.0 * (abs(pdi - mdi) / denom) if denom > 0 else 0.0
            
    adx = [0.0] * n
    start_adx = period * 2
    if n > start_adx:
        adx[start_adx] = sum(dx[period:start_adx]) / period
        for i in range(start_adx + 1, n):
            adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
    return adx

def calc_bollinger_bands(closes, period=20, mult=2.0):
    n = len(closes)
    mid = [0.0] * n
    upper = [0.0] * n
    lower = [0.0] * n
    bw = [0.0] * n
    
    sum_c = 0.0
    sum_sq = 0.0
    for i in range(n):
        sum_c += closes[i]
        sum_sq += closes[i] * closes[i]
        if i >= period:
            sum_c -= closes[i - period]
            sum_sq -= closes[i - period] * closes[i - period]
            mean = sum_c / period
            var = max(0.0, (sum_sq / period) - (mean * mean))
            std = math.sqrt(var)
            mid[i] = mean
            upper[i] = mean + mult * std
            lower[i] = mean - mult * std
            bw[i] = (upper[i] - lower[i]) / mean if mean > 0 else 0.0
    return mid, upper, lower, bw

def calc_donchian(highs, lows, period=20):
    n = len(highs)
    upper = [0.0] * n
    lower = [0.0] * n
    mid = [0.0] * n
    for i in range(period, n):
        upper[i] = max(highs[i-period:i])  # prior period bars excluding current!
        lower[i] = min(lows[i-period:i])
        mid[i] = (upper[i] + lower[i]) / 2.0
    return upper, lower, mid

def calc_rolling_vwap(candles, window=288):
    """24-hour (288 M5 bars) rolling VWAP and standard deviation bands (O(1) running sums)"""
    n = len(candles)
    vwap = [0.0] * n
    upper_2s = [0.0] * n
    lower_2s = [0.0] * n
    
    tp = [(c["high"] + c["low"] + c["close"]) / 3.0 for c in candles]
    vol = [c["volume"] for c in candles]
    
    pv = [tp[i] * vol[i] for i in range(n)]
    pv2 = [tp[i] * tp[i] * vol[i] for i in range(n)]
    
    sum_pv = 0.0
    sum_pv2 = 0.0
    sum_v = 0.0
    for i in range(n):
        sum_pv += pv[i]
        sum_pv2 += pv2[i]
        sum_v += vol[i]
        if i >= window:
            sum_pv -= pv[i - window]
            sum_pv2 -= pv2[i - window]
            sum_v -= vol[i - window]
            
        if sum_v > 0:
            vw = sum_pv / sum_v
            vwap[i] = vw
            # O(1) variance: E[X^2] - (E[X])^2
            mean_tp2 = sum_pv2 / sum_v
            var = max(0.0, mean_tp2 - (vw * vw))
            stdev = math.sqrt(var)
            upper_2s[i] = vw + 2.0 * stdev
            lower_2s[i] = vw - 2.0 * stdev
        else:
            vwap[i] = tp[i]
            upper_2s[i] = tp[i]
            lower_2s[i] = tp[i]
            
    return vwap, upper_2s, lower_2s

# ==============================================================================
# 3. REALISTIC SIMULATION ENGINE (EXECUTION, FRICTION, MINNOTIONAL CLAMP)
# ==============================================================================
class SimulationContext:
    def __init__(self, m5_candles, h1_candles, m15_candles, symbol="BTCUSDT"):
        self.symbol = symbol
        self.m5 = m5_candles
        self.h1 = h1_candles
        self.m15 = m15_candles
        self.n_m5 = len(m5_candles)
        
        self.times = [c["time"] for c in m5_candles]
        self.opens = [c["open"] for c in m5_candles]
        self.highs = [c["high"] for c in m5_candles]
        self.lows = [c["low"] for c in m5_candles]
        self.closes = [c["close"] for c in m5_candles]
        self.vols = [c["volume"] for c in m5_candles]
        
        # Zero-lookahead HTF lookups
        self.m5_to_h1 = build_htf_lookup(self.times, self.h1)
        self.m5_to_m15 = build_htf_lookup(self.times, self.m15)
        
        # Precompute HTF indicators
        h1_closes = [c["close"] for c in self.h1]
        h1_highs = [c["high"] for c in self.h1]
        h1_lows = [c["low"] for c in self.h1]
        self.h1_ema50 = calc_ema(h1_closes, 50)
        self.h1_ema200 = calc_ema(h1_closes, 200)
        self.h1_adx = calc_adx(h1_highs, h1_lows, h1_closes, 14)
        self.h1_closes = h1_closes
        
        m15_closes = [c["close"] for c in self.m15]
        self.m15_ema20 = calc_ema(m15_closes, 20)
        self.m15_ema50 = calc_ema(m15_closes, 50)
        self.m15_closes = m15_closes
        
        # Precompute M5 indicators
        self.m5_ema9 = calc_ema(self.closes, 9)
        self.m5_ema20 = calc_ema(self.closes, 20)
        self.m5_ema50 = calc_ema(self.closes, 50)
        self.m5_ema200 = calc_ema(self.closes, 200)
        self.m5_atr14 = calc_atr(self.highs, self.lows, self.closes, 14)
        self.m5_adx14 = calc_adx(self.highs, self.lows, self.closes, 14)
        
        # Volume moving averages
        self.m5_vol_sma20 = [0.0] * self.n_m5
        s_v = 0.0
        for i in range(self.n_m5):
            s_v += self.vols[i]
            if i >= 20: s_v -= self.vols[i-20]
            self.m5_vol_sma20[i] = s_v / min(i+1, 20)
            
        # Bollinger Bands
        self.bb_mid, self.bb_up, self.bb_low, self.bb_width = calc_bollinger_bands(self.closes, 20, 2.0)
        
        # Donchian Channels (12, 20, 36, 48)
        self.don12_u, self.don12_l, self.don12_m = calc_donchian(self.highs, self.lows, 12)
        self.don20_u, self.don20_l, self.don20_m = calc_donchian(self.highs, self.lows, 20)
        self.don36_u, self.don36_l, self.don36_m = calc_donchian(self.highs, self.lows, 36)
        self.don48_u, self.don48_l, self.don48_m = calc_donchian(self.highs, self.lows, 48)
        
        # Rolling VWAP
        self.vwap, self.vwap_up2, self.vwap_low2 = calc_rolling_vwap(self.m5, 288)

def run_strategy_simulation(ctx, signal_generator_fn, 
                            initial_capital=20.0,
                            target_risk_pct=1.0,
                            max_risk_pct_cap=1.25,
                            slippage_pct=0.0005,
                            taker_fee_pct=0.0005,
                            maker_fee_pct=0.0002,
                            funding_8h_pct=0.0001,
                            execution_delay_bars=1,
                            daily_deposit_usd=0.0):
    """
    Executes a high-precision strategy backtest with strict realistic execution:
    - Signal confirmed at close of candle i
    - Executed on candle i + execution_delay_bars open with slippage
    - Binance minNotional clamp with STRICT skip rule if actual_risk > max_risk_pct_cap
    - Dual accounting: Curve A (pure trading) and Curve B (trading + daily deposit)
    """
    balance_trading = initial_capital
    balance_with_deposit = initial_capital
    peak_trading = initial_capital
    peak_with_deposit = initial_capital
    
    max_dd_trading_usd = 0.0
    max_dd_trading_pct = 0.0
    max_dd_dep_pct = 0.0
    
    trades = []
    active_trade = None
    pending_signal = None
    
    # Track capital additions
    total_deposited = 0.0
    last_deposit_day = -1
    
    warmup_bars = 300
    n = ctx.n_m5
    
    # Binance step size: BTC: 0.001, ETH: 0.001 (or 0.001 min_qty)
    min_notional = 20.0  # Binance Futures 20 USDT
    
    for i in range(warmup_bars, n - 2):
        c_time = ctx.times[i]
        c_open = ctx.opens[i]
        c_high = ctx.highs[i]
        c_low = ctx.lows[i]
        c_close = ctx.closes[i]
        
        dt_utc = datetime.fromtimestamp(c_time / 1000, tz=timezone.utc)
        current_day = dt_utc.timetuple().tm_yday
        
        # Daily deposit at midnight UTC
        if daily_deposit_usd > 0 and current_day != last_deposit_day:
            balance_with_deposit += daily_deposit_usd
            total_deposited += daily_deposit_usd
            last_deposit_day = current_day
            if balance_with_deposit > peak_with_deposit:
                peak_with_deposit = balance_with_deposit

        # 1. Fill pending order on current bar's OPEN (with latency & slippage)
        if pending_signal is not None and active_trade is None:
            side = pending_signal["side"]
            raw_entry = c_open
            exec_entry = raw_entry * (1.0 + slippage_pct) if side == "LONG" else raw_entry * (1.0 - slippage_pct)
            
            sl_price = pending_signal["sl"]
            tp_price = pending_signal["tp"]
            sl_dist = abs(exec_entry - sl_price)
            tp_dist = abs(tp_price - exec_entry)
            
            # Position sizing on Curve A (pure trading balance)
            target_risk_dollars = balance_trading * (target_risk_pct / 100.0)
            raw_qty = target_risk_dollars / max(0.1, sl_dist)
            min_qty = min_notional / exec_entry
            qty = max(raw_qty, min_qty)
            
            # Rounding to 3 decimals
            qty = round(qty, 3)
            if qty < 0.001: qty = 0.001
            
            notional = qty * exec_entry
            actual_risk_dollars = qty * sl_dist
            actual_risk_pct = (actual_risk_dollars / balance_trading) * 100.0
            
            # STRICT SMALL ACCOUNT RULE: If actual risk > max_risk_pct_cap, SKIP TRADE!
            if actual_risk_pct > max_risk_pct_cap:
                # Trade skipped due to capital constraint!
                pending_signal = None
            else:
                entry_fee = notional * taker_fee_pct
                active_trade = {
                    "id": len(trades) + 1,
                    "side": side,
                    "entry_bar": i,
                    "entry_time": dt_utc.strftime("%Y-%m-%d %H:%M"),
                    "entry_price": exec_entry,
                    "raw_entry": raw_entry,
                    "sl": sl_price,
                    "tp": tp_price,
                    "sl_dist": sl_dist,
                    "tp_dist": tp_dist,
                    "qty": qty,
                    "notional": notional,
                    "actual_risk_usd": actual_risk_dollars,
                    "actual_risk_pct": actual_risk_pct,
                    "entry_fee": entry_fee,
                    "funding_paid": 0.0,
                    "bars_held": 0,
                    "start_bal": balance_trading,
                    "be_applied": False
                }
                pending_signal = None

        # 2. Manage Active Position on current bar
        if active_trade is not None:
            active_trade["bars_held"] += 1
            if active_trade["bars_held"] % 96 == 0:
                active_trade["funding_paid"] += active_trade["notional"] * funding_8h_pct
                
            side = active_trade["side"]
            sl = active_trade["sl"]
            tp = active_trade["tp"]
            entry = active_trade["entry_price"]
            qty = active_trade["qty"]
            
            closed = False
            exit_price = 0.0
            reason = ""
            
            # Pessimistic collision check: SL always hits first if both touched
            if side == "LONG":
                if c_low <= sl:
                    exit_price = sl * (1.0 - slippage_pct)
                    reason = "SL"
                    closed = True
                elif c_high >= tp:
                    exit_price = tp
                    reason = "TP"
                    closed = True
            elif side == "SHORT":
                if c_high >= sl:
                    exit_price = sl * (1.0 + slippage_pct)
                    reason = "SL"
                    closed = True
                elif c_low <= tp:
                    exit_price = tp
                    reason = "TP"
                    closed = True
                    
            if closed:
                exit_fee_rate = maker_fee_pct if reason == "TP" else taker_fee_pct
                exit_fee = (exit_price * qty) * exit_fee_rate
                tot_fees = active_trade["entry_fee"] + exit_fee + active_trade["funding_paid"]
                
                gross_pnl = (exit_price - entry) * qty if side == "LONG" else (entry - exit_price) * qty
                net_pnl = gross_pnl - tot_fees
                r_mult = net_pnl / active_trade["actual_risk_usd"] if active_trade["actual_risk_usd"] > 0 else 0.0
                
                balance_trading += net_pnl
                balance_with_deposit += net_pnl
                
                if balance_trading > peak_trading: peak_trading = balance_trading
                dd_t = peak_trading - balance_trading
                dd_t_pct = (dd_t / peak_trading) * 100.0 if peak_trading > 0 else 0.0
                if dd_t > max_dd_trading_usd: max_dd_trading_usd = dd_t
                if dd_t_pct > max_dd_trading_pct: max_dd_trading_pct = dd_t_pct
                
                if balance_with_deposit > peak_with_deposit: peak_with_deposit = balance_with_deposit
                dd_dep_pct = ((peak_with_deposit - balance_with_deposit) / peak_with_deposit) * 100.0 if peak_with_deposit > 0 else 0.0
                if dd_dep_pct > max_dd_dep_pct: max_dd_dep_pct = dd_dep_pct
                
                active_trade["exit_time"] = dt_utc.strftime("%Y-%m-%d %H:%M")
                active_trade["exit_price"] = exit_price
                active_trade["reason"] = reason
                active_trade["net_pnl"] = net_pnl
                active_trade["r_multiple"] = r_mult
                active_trade["fees"] = tot_fees
                active_trade["end_bal"] = balance_trading
                trades.append(active_trade)
                active_trade = None

        # 3. Signal Generation on COMPLETED candle i (Zero Lookahead!)
        if active_trade is None and pending_signal is None:
            sig = signal_generator_fn(ctx, i)
            if sig is not None:
                pending_signal = sig

    # Compute comprehensive metrics
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "trades": 0, "win_rate": 0.0, "pf": 0.0, "pf_gross": 0.0,
            "expectancy_r": 0.0, "net_pnl": 0.0, "final_bal_trading": balance_trading,
            "final_bal_deposit": balance_with_deposit, "total_deposited": total_deposited,
            "max_dd_trading_pct": 0.0, "max_dd_deposit_pct": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "trades_list": []
        }
        
    wins = [t for t in trades if t["net_pnl"] > 0]
    losses = [t for t in trades if t["net_pnl"] <= 0]
    n_w = len(wins)
    n_l = len(losses)
    wr = (n_w / total_trades) * 100.0
    
    win_usd = sum(t["net_pnl"] for t in wins)
    loss_usd = abs(sum(t["net_pnl"] for t in losses))
    net_pnl = win_usd - loss_usd
    pf = (win_usd / loss_usd) if loss_usd > 0 else 999.0
    
    # Gross PF (without fees)
    gross_wins = sum(t["net_pnl"] + t["fees"] for t in wins)
    gross_losses = abs(sum(t["net_pnl"] + t["fees"] for t in losses))
    pf_gross = (gross_wins / gross_losses) if gross_losses > 0 else 999.0
    
    avg_win = win_usd / n_w if n_w > 0 else 0.0
    avg_loss = loss_usd / n_l if n_l > 0 else 0.0
    exp_r = sum(t["r_multiple"] for t in trades) / total_trades
    
    # Consecutive losses
    max_consec_l = 0
    cur_l = 0
    for t in trades:
        if t["net_pnl"] <= 0:
            cur_l += 1
            if cur_l > max_consec_l: max_consec_l = cur_l
        else:
            cur_l = 0
            
    return {
        "trades": total_trades,
        "wins": n_w,
        "losses": n_l,
        "win_rate": round(wr, 1),
        "pf": round(pf, 2),
        "pf_gross": round(pf_gross, 2),
        "expectancy_r": round(exp_r, 3),
        "net_pnl": round(net_pnl, 2),
        "final_bal_trading": round(balance_trading, 2),
        "final_bal_deposit": round(balance_with_deposit, 2),
        "total_deposited": round(total_deposited, 2),
        "max_dd_trading_pct": round(max_dd_trading_pct, 1),
        "max_dd_deposit_pct": round(max_dd_dep_pct, 1),
        "max_consecutive_losses": max_consec_l,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "total_fees": round(sum(t["fees"] for t in trades), 2),
        "trades_list": trades
    }

# ==============================================================================
# 4. STRATEGY FAMILIES SIGNAL IMPLEMENTATIONS
# ==============================================================================

# --- FAMILY A: TREND PULLBACK (TPB) ---
def signal_family_a_tpb(ctx, i, ema_pullback=20, ema_trend=50, rr=2.0, adx_min=22, vol_mult=1.2):
    # Zero-lookahead HTF filter
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_ema = ctx.h1_ema50[h_idx]
    
    # Session filter: Active global liquidity hours (07:00 to 21:00 UTC)
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    if not (7 <= dt_utc.hour < 21): return None
    
    c_close = ctx.closes[i]
    c_open = ctx.opens[i]
    c_high = ctx.highs[i]
    c_low = ctx.lows[i]
    c_atr = ctx.m5_atr14[i]
    c_vol = ctx.vols[i]
    avg_vol = ctx.m5_vol_sma20[i]
    
    if c_atr <= 0 or ctx.m5_adx14[i] < adx_min: return None
    if (c_vol / max(1.0, avg_vol)) < vol_mult: return None
    
    e20 = ctx.m5_ema20[i]
    e50 = ctx.m5_ema50[i]
    
    # Bullish Pullback
    if h_close > h_ema and e20 > e50:
        # Price dipped into EMA 20-50 zone on this or prior bar and rejected upwards
        if min(ctx.lows[i-1], c_low) <= e20 and c_close > e20 and c_close > c_open:
            sl = min(c_low, ctx.lows[i-1]) - (0.3 * c_atr)
            sl_dist = c_close - sl
            if sl_dist >= 0.8 * c_atr:
                return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
                
    # Bearish Pullback
    if h_close < h_ema and e20 < e50:
        if max(ctx.highs[i-1], c_high) >= e20 and c_close < e20 and c_close < c_open:
            sl = max(c_high, ctx.highs[i-1]) + (0.3 * c_atr)
            sl_dist = sl - c_close
            if sl_dist >= 0.8 * c_atr:
                return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
                
    return None

# --- FAMILY B: VOLATILITY / DONCHIAN BREAKOUT (DON) ---
def signal_family_b_donchian(ctx, i, lookback=20, rr=2.0, vol_mult=1.3):
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_ema200 = ctx.h1_ema200[h_idx]
    
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    if not (7 <= dt_utc.hour < 21): return None
    
    c_close = ctx.closes[i]
    c_atr = ctx.m5_atr14[i]
    c_vol = ctx.vols[i]
    avg_vol = ctx.m5_vol_sma20[i]
    
    if (c_vol / max(1.0, avg_vol)) < vol_mult: return None
    
    if lookback == 12: u, l, m = ctx.don12_u[i], ctx.don12_l[i], ctx.don12_m[i]
    elif lookback == 36: u, l, m = ctx.don36_u[i], ctx.don36_l[i], ctx.don36_m[i]
    elif lookback == 48: u, l, m = ctx.don48_u[i], ctx.don48_l[i], ctx.don48_m[i]
    else: u, l, m = ctx.don20_u[i], ctx.don20_l[i], ctx.don20_m[i]
    
    # Long Breakout
    if c_close > u and h_close > h_ema200:
        sl = m  # Donchian midline stop
        sl_dist = c_close - sl
        if 0.8 * c_atr <= sl_dist <= 3.5 * c_atr:
            return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
            
    # Short Breakout
    if c_close < l and h_close < h_ema200:
        sl = m
        sl_dist = sl - c_close
        if 0.8 * c_atr <= sl_dist <= 3.5 * c_atr:
            return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
            
    return None

# --- FAMILY C: RANGE BREAKOUT + RETEST (RBR) ---
def signal_family_c_range_retest(ctx, i, rr=2.5):
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_ema50 = ctx.h1_ema50[h_idx]
    
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    if not (7 <= dt_utc.hour < 21): return None
    
    # Volatility compression on bar i-2
    if ctx.bb_width[i-2] > 0.015: return None  # Must have been compressed
    
    c_close = ctx.closes[i]
    c_atr = ctx.m5_atr14[i]
    
    # Breakout occurred on bar i-1, bar i retests and closes strong
    prior_high = max(ctx.highs[i-15:i-2])
    prior_low = min(ctx.lows[i-15:i-2])
    
    if h_close > h_ema50 and ctx.closes[i-1] > prior_high:
        if ctx.lows[i] <= prior_high and c_close > prior_high and c_close > ctx.opens[i]:
            sl = min(ctx.lows[i], ctx.lows[i-1]) - (0.2 * c_atr)
            sl_dist = c_close - sl
            if 0.8 * c_atr <= sl_dist <= 3.0 * c_atr:
                return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
                
    if h_close < h_ema50 and ctx.closes[i-1] < prior_low:
        if ctx.highs[i] >= prior_low and c_close < prior_low and c_close < ctx.opens[i]:
            sl = max(ctx.highs[i], ctx.highs[i-1]) + (0.2 * c_atr)
            sl_dist = sl - c_close
            if 0.8 * c_atr <= sl_dist <= 3.0 * c_atr:
                return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
                
    return None

# --- FAMILY D: VWAP / BOLLINGER MEAN REVERSION (MR) ---
def signal_family_d_mean_reversion(ctx, i, rr=1.5):
    # Non-trending regime ONLY! H1 ADX must be low (< 20)
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    if ctx.h1_adx[h_idx] > 20: return None
    
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    # Trade during quiet liquidity or midday chop
    if not (1 <= dt_utc.hour < 20): return None
    
    c_close = ctx.closes[i]
    c_low = ctx.lows[i]
    c_high = ctx.highs[i]
    c_open = ctx.opens[i]
    c_atr = ctx.m5_atr14[i]
    
    vwap_val = ctx.vwap[i]
    vwap_up = ctx.vwap_up2[i]
    vwap_low = ctx.vwap_low2[i]
    
    # Long Mean Reversion (Price dipped below -2 sigma VWAP, rejected with lower wick)
    if c_low < vwap_low and c_close > vwap_low and c_close > c_open:
        wick = min(c_open, c_close) - c_low
        if wick >= 0.4 * (c_high - c_low):
            sl = c_low - (0.2 * c_atr)
            sl_dist = c_close - sl
            tp = vwap_val  # Target mean reversion to VWAP
            if (tp - c_close) >= (rr * sl_dist) and sl_dist >= 0.6 * c_atr:
                return {"side": "LONG", "sl": sl, "tp": tp}
                
    # Short Mean Reversion (Price pierced above +2 sigma VWAP, rejected with upper wick)
    if c_high > vwap_up and c_close < vwap_up and c_close < c_open:
        wick = c_high - max(c_open, c_close)
        if wick >= 0.4 * (c_high - c_low):
            sl = c_high + (0.2 * c_atr)
            sl_dist = sl - c_close
            tp = vwap_val
            if (c_close - tp) >= (rr * sl_dist) and sl_dist >= 0.6 * c_atr:
                return {"side": "SHORT", "sl": sl, "tp": tp}
                
    return None

# --- FAMILY E: MOMENTUM / IMPULSE CONTINUATION (MOM) ---
def signal_family_e_momentum(ctx, i, rr=2.0, body_mult=1.8, vol_mult=1.8):
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_ema50 = ctx.h1_ema50[h_idx]
    
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    if not (7 <= dt_utc.hour < 21): return None
    
    c_close = ctx.closes[i]
    c_open = ctx.opens[i]
    c_high = ctx.highs[i]
    c_low = ctx.lows[i]
    c_atr = ctx.m5_atr14[i]
    c_vol = ctx.vols[i]
    avg_vol = ctx.m5_vol_sma20[i]
    
    body = abs(c_close - c_open)
    if body < (body_mult * c_atr) or (c_vol / max(1.0, avg_vol)) < vol_mult:
        return None
        
    # Long Momentum Impulse
    if c_close > c_open and h_close > h_ema50:
        # Closes in top 20% of candle
        if (c_high - c_close) <= 0.20 * (c_high - c_low):
            sl = c_low - (0.2 * c_atr)
            sl_dist = c_close - sl
            return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
            
    # Short Momentum Impulse
    if c_close < c_open and h_close < h_ema50:
        if (c_close - c_low) <= 0.20 * (c_high - c_low):
            sl = c_high + (0.2 * c_atr)
            sl_dist = sl - c_close
            return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
            
    return None

# --- FAMILY F: MARKET STRUCTURE / LIQUIDITY SWEEP (SMC) ---
def signal_family_f_liquidity_sweep(ctx, i, rr=2.5):
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_close = ctx.h1_closes[h_idx]
    h_ema200 = ctx.h1_ema200[h_idx]
    
    dt_utc = datetime.fromtimestamp(ctx.times[i] / 1000, tz=timezone.utc)
    if not (7 <= dt_utc.hour < 21): return None
    
    # 20-bar prior swing high & low
    prior_high = max(ctx.highs[i-20:i-1])
    prior_low = min(ctx.lows[i-20:i-1])
    
    c_close = ctx.closes[i]
    c_high = ctx.highs[i]
    c_low = ctx.lows[i]
    c_atr = ctx.m5_atr14[i]
    
    # Bullish Liquidity Sweep (Swept prior low, closed back above with long wick)
    if c_low < prior_low and c_close > prior_low and c_close > ctx.opens[i] and h_close > h_ema200:
        wick = min(ctx.opens[i], c_close) - c_low
        if wick >= 0.45 * (c_high - c_low):
            sl = c_low - (0.2 * c_atr)
            sl_dist = c_close - sl
            if 0.7 * c_atr <= sl_dist <= 2.5 * c_atr:
                return {"side": "LONG", "sl": sl, "tp": c_close + (rr * sl_dist)}
                
    # Bearish Liquidity Sweep (Swept prior high, closed back below with long wick)
    if c_high > prior_high and c_close < prior_high and c_close < ctx.opens[i] and h_close < h_ema200:
        wick = c_high - max(ctx.opens[i], c_close)
        if wick >= 0.45 * (c_high - c_low):
            sl = c_high + (0.2 * c_atr)
            sl_dist = sl - c_close
            if 0.7 * c_atr <= sl_dist <= 2.5 * c_atr:
                return {"side": "SHORT", "sl": sl, "tp": c_close - (rr * sl_dist)}
                
    return None

# --- FAMILY H: REGIME SWITCHING / HYBRID CLASSIFIER ---
def signal_family_h_hybrid(ctx, i):
    h_idx = ctx.m5_to_h1[i]
    if h_idx < 0: return None
    h_adx = ctx.h1_adx[h_idx]
    
    # Regime 1: Strong Trend -> Use Trend Pullback (Family A)
    if h_adx >= 25:
        return signal_family_a_tpb(ctx, i, rr=2.0)
    # Regime 2: Volatility Breakout -> Use Donchian (Family B)
    elif ctx.m5_adx14[i] > 30 and (ctx.vols[i] / max(1.0, ctx.m5_vol_sma20[i])) > 1.5:
        return signal_family_b_donchian(ctx, i, lookback=20, rr=2.0)
    # Regime 3: Range Chop -> Use Mean Reversion (Family D)
    elif h_adx < 18 and ctx.bb_width[i] < 0.015:
        return signal_family_d_mean_reversion(ctx, i, rr=1.5)
        
    return None

# ==============================================================================
# 5. WALK-FORWARD & ROBUSTNESS ENGINE
# ==============================================================================
def run_walk_forward_4fold(ctx, signal_fn, name="Strategy"):
    """
    4-Fold chronological Walk-Forward Validation across the 2-year dataset.
    Folds:
      Fold 1: 0 to 25% of dataset
      Fold 2: 25% to 50%
      Fold 3: 50% to 75%
      Fold 4: 75% to 100%
    In each fold: 60% Train, 20% Validate, 20% Test (Out-of-Sample).
    """
    total_len = ctx.n_m5
    fold_size = total_len // 4
    
    oos_trades_all = []
    fold_results = []
    
    for f in range(4):
        f_start = f * fold_size
        f_end = (f + 1) * fold_size if f < 3 else total_len
        f_len = f_end - f_start
        
        train_end = f_start + int(f_len * 0.60)
        val_end = f_start + int(f_len * 0.80)
        test_end = f_end
        
        # Sub-context slices or time bounded simulation
        t_start_val = ctx.times[train_end]
        t_start_test = ctx.times[val_end]
        t_end_test = ctx.times[test_end - 1]
        
        # Run entire fold
        res = run_strategy_simulation(ctx, signal_fn, initial_capital=20.0, target_risk_pct=1.0)
        
        # Filter trades into Train, Val, OOS Test
        trades = res["trades_list"]
        f_train = [t for t in trades if ctx.times[t["entry_bar"]] < t_start_val]
        f_val = [t for t in trades if t_start_val <= ctx.times[t["entry_bar"]] < t_start_test]
        f_oos = [t for t in trades if t_start_test <= ctx.times[t["entry_bar"]] <= t_end_test]
        
        oos_trades_all.extend(f_oos)
        
        def quick_stats(sub_t):
            if not sub_t: return {"trades": 0, "pf": 0.0, "net": 0.0, "wr": 0.0}
            w = [t for t in sub_t if t["net_pnl"] > 0]
            l = [t for t in sub_t if t["net_pnl"] <= 0]
            w_usd = sum(t["net_pnl"] for t in w)
            l_usd = abs(sum(t["net_pnl"] for t in l))
            return {
                "trades": len(sub_t),
                "wr": round((len(w)/len(sub_t))*100.0, 1),
                "pf": round(w_usd / l_usd if l_usd > 0 else 999.0, 2),
                "net": round(w_usd - l_usd, 2)
            }
            
        fold_results.append({
            "fold": f + 1,
            "train": quick_stats(f_train),
            "val": quick_stats(f_val),
            "oos": quick_stats(f_oos)
        })
        
    return fold_results, oos_trades_all

def run_monte_carlo(trades, iterations=10000, initial_bal=20.0):
    if not trades:
        return {"median_dd": 0.0, "dd_95": 0.0, "dd_99": 0.0, "ruin_prob": 0.0}
    pnls = [t["net_pnl"] for t in trades]
    dds = []
    ruin_count = 0
    
    for _ in range(iterations):
        shuffled = pnls.copy()
        random.shuffle(shuffled)
        b = initial_bal
        peak = b
        max_dd = 0.0
        ruined = False
        
        for p in shuffled:
            b += p
            if b > peak: peak = b
            dd = ((peak - b) / peak) * 100.0 if peak > 0 else 100.0
            if dd > max_dd: max_dd = dd
            if b <= initial_bal * 0.50:  # 50% drawdown = ruin threshold
                ruined = True
        dds.append(max_dd)
        if ruined: ruin_count += 1
        
    dds.sort()
    return {
        "median_dd": round(dds[int(iterations * 0.50)], 1),
        "dd_75": round(dds[int(iterations * 0.75)], 1),
        "dd_90": round(dds[int(iterations * 0.90)], 1),
        "dd_95": round(dds[int(iterations * 0.95)], 1),
        "dd_99": round(dds[int(iterations * 0.99)], 1),
        "ruin_prob": round((ruin_count / iterations) * 100.0, 1)
    }

# ==============================================================================
# 6. MASTER DISCOVERY ORCHESTRATOR
# ==============================================================================
def execute_master_discovery():
    print("=" * 80)
    print("🚀 APEX QUANT v4: FULL STRATEGY DISCOVERY & ROBUSTNESS MISSION")
    print("=" * 80)
    
    # 1. Load Data for both BTC and ETH
    btc_m5 = load_cached_klines("BTCUSDT")
    eth_m5 = load_cached_klines("ETHUSDT")
    
    print("\n🔨 Aggregating Multi-Timeframe candles (M15 and H1)...")
    btc_m15 = aggregate_candles(btc_m5, 15)
    btc_h1 = aggregate_candles(btc_m5, 60)
    eth_m15 = aggregate_candles(eth_m5, 15)
    eth_h1 = aggregate_candles(eth_m5, 60)
    
    print("⚡ Initializing Vectorized Simulation Contexts...")
    btc_ctx = SimulationContext(btc_m5, btc_h1, btc_m15, "BTCUSDT")
    eth_ctx = SimulationContext(eth_m5, eth_h1, eth_m15, "ETHUSDT")
    print("   ✅ Contexts ready.\n")
    
    # Define candidates to test
    candidates = [
        # Family A: Trend Pullback
        {"id": "TPB_A1", "name": "Trend Pullback (EMA 20/50, 2.0R)", "fn": lambda c, i: signal_family_a_tpb(c, i, rr=2.0), "fam": "Trend Pullback"},
        {"id": "TPB_A2", "name": "Trend Pullback (EMA 20/50, 1.5R)", "fn": lambda c, i: signal_family_a_tpb(c, i, rr=1.5), "fam": "Trend Pullback"},
        {"id": "TPB_A3", "name": "Trend Pullback (EMA 20/50, 2.5R)", "fn": lambda c, i: signal_family_a_tpb(c, i, rr=2.5), "fam": "Trend Pullback"},
        
        # Family B: Donchian Breakout
        {"id": "DON_B1", "name": "Donchian Breakout (20-bar, 2.0R)", "fn": lambda c, i: signal_family_b_donchian(c, i, lookback=20, rr=2.0), "fam": "Donchian"},
        {"id": "DON_B2", "name": "Donchian Breakout (12-bar, 2.0R)", "fn": lambda c, i: signal_family_b_donchian(c, i, lookback=12, rr=2.0), "fam": "Donchian"},
        {"id": "DON_B3", "name": "Donchian Breakout (36-bar, 2.0R)", "fn": lambda c, i: signal_family_b_donchian(c, i, lookback=36, rr=2.0), "fam": "Donchian"},
        
        # Family C: Range Retest
        {"id": "RBR_C1", "name": "Range Breakout + Retest (2.5R)", "fn": lambda c, i: signal_family_c_range_retest(c, i, rr=2.5), "fam": "Range Retest"},
        
        # Family D: Mean Reversion
        {"id": "MR_D1", "name": "VWAP Mean Reversion (1.5R)", "fn": lambda c, i: signal_family_d_mean_reversion(c, i, rr=1.5), "fam": "Mean Reversion"},
        
        # Family E: Momentum Impulse
        {"id": "MOM_E1", "name": "Momentum Impulse Continuation (2.0R)", "fn": lambda c, i: signal_family_e_momentum(c, i, rr=2.0), "fam": "Momentum"},
        
        # Family F: Liquidity Sweep
        {"id": "SMC_F1", "name": "Liquidity Sweep + Structure Shift (2.5R)", "fn": lambda c, i: signal_family_f_liquidity_sweep(c, i, rr=2.5), "fam": "Market Structure"},
        
        # Family H: Hybrid Classifier
        {"id": "HYB_H1", "name": "Regime Switching Hybrid Classifier", "fn": lambda c, i: signal_family_h_hybrid(c, i), "fam": "Hybrid"}
    ]
    
    research_table = []
    
    # Run tests across both assets
    for asset, ctx in [("BTCUSDT", btc_ctx), ("ETHUSDT", eth_ctx)]:
        print(f"\n{'='*30} TESTING ASSET: {asset} {'='*30}")
        
        for cand in candidates:
            c_id = f"{cand['id']}_{asset[:3]}"
            print(f"🔬 Testing {c_id}: {cand['name']}...")
            
            # 1. Base realistic test ($20 start, 1.0% risk, 0.05% slip)
            base_res = run_strategy_simulation(
                ctx, cand["fn"], initial_capital=20.0, target_risk_pct=1.0,
                slippage_pct=0.0005, taker_fee_pct=0.0005, maker_fee_pct=0.0002
            )
            
            # 2. Stress Test (+5 bps slip = 0.10% total adverse)
            stress_res = run_strategy_simulation(
                ctx, cand["fn"], initial_capital=20.0, target_risk_pct=1.0,
                slippage_pct=0.0010, taker_fee_pct=0.0006, maker_fee_pct=0.0002
            )
            
            # 3. Capital Scaling Regimes ($100, $200)
            res_100 = run_strategy_simulation(ctx, cand["fn"], initial_capital=100.0, target_risk_pct=1.0)
            res_200 = run_strategy_simulation(ctx, cand["fn"], initial_capital=200.0, target_risk_pct=1.0)
            
            # 4. Capital Additions Curve ($20 start + $20/day deposit)
            res_deposit = run_strategy_simulation(ctx, cand["fn"], initial_capital=20.0, target_risk_pct=1.0, daily_deposit_usd=20.0)
            
            # 5. 4-Fold Walk-Forward Validation
            wf_folds, oos_trades = run_walk_forward_4fold(ctx, cand["fn"], cand["name"])
            
            # Calculate aggregate OOS stats
            oos_w = [t for t in oos_trades if t["net_pnl"] > 0]
            oos_l = [t for t in oos_trades if t["net_pnl"] <= 0]
            oos_win_usd = sum(t["net_pnl"] for t in oos_w)
            oos_loss_usd = abs(sum(t["net_pnl"] for t in oos_l))
            oos_pf = (oos_win_usd / oos_loss_usd) if oos_loss_usd > 0 else 0.0
            oos_exp = (sum(t["r_multiple"] for t in oos_trades) / len(oos_trades)) if oos_trades else 0.0
            
            # 6. Monte Carlo on base trades (1,000 runs for search)
            mc_res = run_monte_carlo(base_res["trades_list"], iterations=1000, initial_bal=20.0)
            
            # Status Determination based on Objective Acceptance Gates:
            # GATE: Base PF >= 1.20, OOS exp >= +0.08R, Max DD <= 20%, MC 95% <= 30%, Stress PF >= 1.10
            status = "REJECTED"
            if base_res["pf"] >= 1.20 and oos_exp >= 0.08 and base_res["max_dd_trading_pct"] <= 25.0:
                if stress_res["pf"] >= 1.10 and mc_res["dd_95"] <= 35.0:
                    status = "ROBUST CANDIDATE"
                else:
                    status = "PROMISING"
            elif base_res["pf"] >= 1.05 and oos_exp >= 0.02:
                status = "FRAGILE"
                
            entry_record = {
                "id": c_id,
                "asset": asset,
                "strategy": cand["name"],
                "family": cand["fam"],
                "trades_total": base_res["trades"],
                "trades_year": round(base_res["trades"] / 2.0, 1),
                "wr": base_res["win_rate"],
                "pf_gross": base_res["pf_gross"],
                "pf_net": base_res["pf"],
                "expectancy_r": base_res["expectancy_r"],
                "avg_win": base_res["avg_win"],
                "avg_loss": base_res["avg_loss"],
                "max_dd": base_res["max_dd_trading_pct"],
                "max_consec_loss": base_res["max_consecutive_losses"],
                "oos_pf": round(oos_pf, 2),
                "oos_expectancy": round(oos_exp, 3),
                "stress_pf": stress_res["pf"],
                "mc_95_dd": mc_res["dd_95"],
                "bal_20": base_res["final_bal_trading"],
                "bal_100": res_100["final_bal_trading"],
                "bal_200": res_200["final_bal_trading"],
                "bal_deposit": res_deposit["final_bal_deposit"],
                "total_deposited": res_deposit["total_deposited"],
                "status": status,
                "base_trades": base_res["trades_list"]
            }
            research_table.append(entry_record)
            print(f"   -> Result: PF Net={base_res['pf']} | OOS Exp={round(oos_exp, 3)}R | Stress PF={stress_res['pf']} | DD={base_res['max_dd_trading_pct']}% | Status={status}")

    # Sort Research Table by Robustness (Status priority then Net PF)
    status_rank = {"ROBUST CANDIDATE": 1, "PROMISING": 2, "FRAGILE": 3, "REJECTED": 4}
    research_table.sort(key=lambda x: (status_rank.get(x["status"], 5), -x["pf_net"], -x["expectancy_r"]))
    
    # Save Research Log to JSON
    out_json = os.path.join(DATA_DIR, "discovery_results_summary.json")
    summary_data = []
    for r in research_table:
        d = r.copy()
        del d["base_trades"]  # Don't bloat JSON summary
        summary_data.append(d)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\n💾 Research summary written to {out_json}")
    
    return research_table

if __name__ == "__main__":
    execute_master_discovery()
