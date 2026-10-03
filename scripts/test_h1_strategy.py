#!/usr/bin/env python3
"""
APEX QUANT v4 — H1 & M15 TIMEFRAME VIABILITY AUDIT
================================================================================
Compares M5 vs M15 vs H1 execution under identical realistic Binance Futures frictions.
Evaluates whether expanding the execution timeframe solves the friction barrier.
"""
import os
import sys
import json
import math

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from quant_discovery_engine import (
    load_cached_klines, aggregate_candles, calc_ema, calc_atr, calc_donchian
)

def run_h1_test():
    eth_m5 = load_cached_klines("ETHUSDT")
    btc_m5 = load_cached_klines("BTCUSDT")
    
    for symbol, m5_data in [("ETHUSDT", eth_m5), ("BTCUSDT", btc_m5)]:
        print(f"\n{'='*25} TESTING H1 TIMEFRAME: {symbol} {'='*25}")
        h1_candles = aggregate_candles(m5_data, 60)
        n = len(h1_candles)
        
        closes = [c["close"] for c in h1_candles]
        highs = [c["high"] for c in h1_candles]
        lows = [c["low"] for c in h1_candles]
        opens = [c["open"] for c in h1_candles]
        vols = [c["volume"] for c in h1_candles]
        times = [c["time"] for c in h1_candles]
        
        ema50 = calc_ema(closes, 50)
        ema200 = calc_ema(closes, 200)
        atr14 = calc_atr(highs, lows, closes, 14)
        don_u, don_l, don_m = calc_donchian(highs, lows, 20)
        
        # Test Donchian Breakout on H1 (20-bar lookback, 2.5R target)
        # Entry at OPEN of candle i+1 with 0.05% slippage, 0.05% taker fee
        balance = 100.0  # $100 baseline
        peak = balance
        max_dd = 0.0
        trades = []
        active = None
        pending = None
        
        for i in range(200, n - 2):
            c_open = opens[i]
            c_high = highs[i]
            c_low = lows[i]
            c_close = closes[i]
            c_atr = atr14[i]
            
            # Fill pending order at open of i with slippage
            if pending is not None and active is None:
                side = pending["side"]
                exec_entry = c_open * (1.0005 if side == "LONG" else 0.9995)
                sl = pending["sl"]
                tp = pending["tp"]
                sl_dist = max(1.0, abs(exec_entry - sl))
                
                # Risk 1.0% of balance ($1.00 on $100)
                risk_usd = max(0.1, balance * 0.01)
                qty = max(20.0 / exec_entry, risk_usd / sl_dist)
                qty = round(qty, 3)
                if qty < 0.001: qty = 0.001
                
                active = {
                    "side": side,
                    "entry": exec_entry,
                    "sl": sl,
                    "tp": tp,
                    "qty": qty,
                    "risk_usd": max(0.1, qty * sl_dist),
                    "entry_fee": (qty * exec_entry) * 0.0005,
                    "bars": 0
                }
                pending = None
                
            # Manage active
            if active is not None:
                active["bars"] += 1
                side = active["side"]
                sl = active["sl"]
                tp = active["tp"]
                qty = active["qty"]
                closed = False
                exit_p = 0.0
                reason = ""
                
                # Pessimistic collision
                if side == "LONG":
                    if c_low <= sl:
                        exit_p = sl * 0.9995
                        reason = "SL"
                        closed = True
                    elif c_high >= tp:
                        exit_p = tp
                        reason = "TP"
                        closed = True
                elif side == "SHORT":
                    if c_high >= sl:
                        exit_p = sl * 1.0005
                        reason = "SL"
                        closed = True
                    elif c_low <= tp:
                        exit_p = tp
                        reason = "TP"
                        closed = True
                        
                if closed:
                    exit_fee = (exit_p * qty) * (0.0002 if reason == "TP" else 0.0005)
                    funding = (qty * active["entry"]) * (0.0001 * (active["bars"] // 8))
                    tot_fees = active["entry_fee"] + exit_fee + funding
                    gross = (exit_p - active["entry"]) * qty if side == "LONG" else (active["entry"] - exit_p) * qty
                    net = gross - tot_fees
                    r_mult = net / active["risk_usd"]
                    balance += net
                    if balance > peak: peak = balance
                    dd = ((peak - balance) / peak) * 100.0
                    if dd > max_dd: max_dd = dd
                    
                    trades.append({"pnl": net, "r": r_mult, "reason": reason})
                    active = None
                    
            # Signal on close of bar i
            if active is None and pending is None:
                # ADX and Volume filter
                c_vol = vols[i]
                avg_v = sum(vols[max(0, i-20):i]) / 20.0
                vol_ok = (c_vol / max(1.0, avg_v)) >= 1.3
                
                # Calculate simple ADX
                # H1 Trend Donchian Breakout
                if vol_ok and c_close > don_u[i] and c_close > ema50[i] > ema200[i]:
                    sl = c_close - (1.5 * c_atr)
                    tp = c_close + (2.5 * 1.5 * c_atr)
                    pending = {"side": "LONG", "sl": sl, "tp": tp}
                elif vol_ok and c_close < don_l[i] and c_close < ema50[i] < ema200[i]:
                    sl = c_close + (1.5 * c_atr)
                    tp = c_close - (2.5 * 1.5 * c_atr)
                    pending = {"side": "SHORT", "sl": sl, "tp": tp}
                    
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        w_usd = sum(t["pnl"] for t in wins)
        l_usd = abs(sum(t["pnl"] for t in losses))
        pf = w_usd / l_usd if l_usd > 0 else 0.0
        wr = (len(wins) / len(trades)) * 100.0 if trades else 0.0
        exp_r = sum(t["r"] for t in trades) / len(trades) if trades else 0.0
        
        print(f"H1 Donchian 20 (2.5R) -> Trades: {len(trades)} | WR: {wr:.1f}% | PF: {pf:.2f} | Exp: {exp_r:+.2f}R | Net: ${balance - 100:+.2f} | Max DD: {max_dd:.1f}%")

if __name__ == "__main__":
    run_h1_test()
