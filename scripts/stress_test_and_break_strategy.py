#!/usr/bin/env python3
"""
APEX QUANT v3.4 — INSTITUTIONAL FRAGILITY & STRESS-TEST SUITE
"BREAK THE STRATEGY" PROTOCOL
================================================================================
Implements rigorous institutional auditing:
1. Zero-Lookahead: Entry at open of (i+1), H1 EMA from closed H1 bars only.
2. Realistic Friction: 0.05% entry slippage, 0.05% SL exit slippage, 0.05% taker fees, 8h funding.
3. Pessimistic Same-Bar Collision: SL always hits first if both touched.
4. True Binance minNotional = $20 clamp (raw dollar risk audit).
5. Walk-Forward OOS Split: 120 days In-Sample vs 60 days Out-of-Sample.
6. 1,000-Run Monte Carlo trade sequence permutation (95% & 99% Max DD).
7. Complete Raw CSV Export of every single trade.
"""

import os
import sys
import json
import math
import time
import random
import urllib.request
from datetime import datetime, timezone, timedelta

def fetch_binance_klines(symbol="ETHUSDT", interval="5m", days=180):
    now_ms = int(time.time() * 1000)
    total_days = days + 14
    start_ms = now_ms - (total_days * 24 * 3600 * 1000)
    
    print(f"📥 Fetching {days} days of {interval} klines from Binance Futures...")
    all_candles = []
    current_start = start_ms
    
    while current_start < now_ms:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&startTime={current_start}&limit=1500"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                if not data: break
                for k in data:
                    all_candles.append({
                        "time": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])
                    })
                current_start = int(data[-1][0]) + 1
                if len(data) < 1500: break
                time.sleep(0.05)
        except Exception as e:
            time.sleep(1.0)
            
    seen = set()
    unique = []
    for c in all_candles:
        if c["time"] not in seen:
            seen.add(c["time"])
            unique.append(c)
    print(f"   ✅ Fetched {len(unique)} {interval} candles.")
    return unique

def run_stress_test():
    print("=" * 80)
    print("🔬 RUNNING STRESS-TEST & FRAGILITY AUDIT: 'BREAK THE STRATEGY'")
    print("=" * 80)
    
    # 1. Fetch data
    h1_candles = fetch_binance_klines("ETHUSDT", "1h", days=180)
    m5_candles = fetch_binance_klines("ETHUSDT", "5m", days=180)
    
    n_h1 = len(h1_candles)
    n_m5 = len(m5_candles)
    
    # Pre-calculate H1 EMA 200 strictly on closed H1 candles
    h1_closes = [c["close"] for c in h1_candles]
    h1_times = [c["time"] for c in h1_candles]
    k_ema = 2.0 / 201.0
    h1_ema = [0.0] * n_h1
    h1_ema[0] = h1_closes[0]
    for i in range(1, n_h1):
        h1_ema[i] = h1_closes[i] * k_ema + h1_ema[i-1] * (1.0 - k_ema)
        
    # Map M5 candle to PREVIOUSLY CLOSED H1 candle (zero lookahead!)
    # H1 candle starting at T closes at T + 3,600,000 ms.
    # Therefore, M5 candle at t can only use H1 if H1_close_time <= t.
    m5_to_closed_h1 = [-1] * n_m5
    h_ptr = 0
    for i in range(n_m5):
        t = m5_candles[i]["time"]
        while h_ptr + 1 < n_h1 and (h1_times[h_ptr + 1] + 3600000) <= t:
            h_ptr += 1
        # Check if the candle at h_ptr is fully closed before t
        if h1_times[h_ptr] + 3600000 <= t:
            m5_to_closed_h1[i] = h_ptr
        else:
            m5_to_closed_h1[i] = -1

    # Pre-calculate M5 Indicators
    highs = [c["high"] for c in m5_candles]
    lows = [c["low"] for c in m5_candles]
    closes = [c["close"] for c in m5_candles]
    volumes = [c["volume"] for c in m5_candles]
    times = [c["time"] for c in m5_candles]
    
    # ATR 10
    tr = [highs[0] - lows[0]]
    for i in range(1, n_m5):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    atr = [0.0] * n_m5
    period = 10
    mult = 2.5
    atr[period-1] = sum(tr[:period]) / period
    for i in range(period, n_m5):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
    st = [0.0] * n_m5
    st_dir = [1] * n_m5
    upper = [0.0] * n_m5
    lower = [0.0] * n_m5
    
    for i in range(period, n_m5):
        hl2 = (highs[i] + lows[i]) / 2.0
        bu = hl2 + mult * atr[i]
        bl = hl2 - mult * atr[i]
        lower[i] = bl if bl > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]
        upper[i] = bu if bu < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
        if closes[i] > upper[i-1]: st_dir[i] = 1
        elif closes[i] < lower[i-1]: st_dir[i] = -1
        else: st_dir[i] = st_dir[i-1]
        st[i] = lower[i] if st_dir[i] == 1 else upper[i]

    # Stress Test Simulation Function
    def execute_simulation(slippage_pct=0.0005, taker_fee_pct=0.0005, maker_fee_pct=0.0002, funding_8h_pct=0.0001, execution_delay_bars=1):
        balance = 20.00
        peak_balance = balance
        max_dd_usd = 0.0
        max_dd_pct = 0.0
        
        trades = []
        active_trade = None
        warmup_cutoff = times[0] + (14 * 24 * 3600 * 1000)
        
        pending_order = None  # To simulate execution on the OPEN of candle i+1 (latency/execution delay)
        
        for i in range(period + 2, n_m5 - 1):
            c_time = times[i]
            c_open = m5_candles[i]["open"]
            c_high = highs[i]
            c_low = lows[i]
            c_close = closes[i]
            c_vol = volumes[i]
            c_atr = atr[i]
            
            dt_utc = datetime.fromtimestamp(c_time / 1000, tz=timezone.utc)
            
            # 1. Fill pending order from previous signal on current bar's OPEN (with slippage!)
            if pending_order is not None and active_trade is None:
                # Apply slippage on entry (buy higher for Long, sell lower for Short)
                side = pending_order["side"]
                raw_entry = c_open
                if side == "LONG":
                    exec_entry = raw_entry * (1.0 + slippage_pct)
                else:
                    exec_entry = raw_entry * (1.0 - slippage_pct)
                    
                sl_price = pending_order["sl"]
                tp_price = pending_order["tp"]
                sl_dist = abs(exec_entry - sl_price)
                tp_dist = abs(tp_price - exec_entry)
                
                # Check Binance minNotional clamp
                dollar_risk_target = balance * 0.01  # 1.0% target
                raw_qty = dollar_risk_target / max(1.0, sl_dist)
                min_qty = 20.0 / exec_entry  # 20 USDT minNotional
                qty = round(max(raw_qty, min_qty, 0.001), 3)
                
                notional = qty * exec_entry
                margin = notional / 20.0
                actual_dollar_risk = qty * sl_dist
                actual_risk_pct = (actual_dollar_risk / balance) * 100.0
                
                # Taker entry fee (0.05%)
                entry_fee = notional * taker_fee_pct
                
                active_trade = {
                    "id": len(trades) + 1,
                    "side": side,
                    "signal_time": pending_order["signal_time"],
                    "entry_time": dt_utc.strftime("%Y-%m-%d %H:%M"),
                    "entry_price": round(exec_entry, 2),
                    "raw_entry": round(raw_entry, 2),
                    "sl": round(sl_price, 2),
                    "tp": round(tp_price, 2),
                    "sl_dist": round(sl_dist, 2),
                    "tp_dist": round(tp_dist, 2),
                    "qty": qty,
                    "notional": round(notional, 2),
                    "margin": round(margin, 2),
                    "target_risk_usd": round(dollar_risk_target, 4),
                    "actual_dollar_risk": round(actual_dollar_risk, 4),
                    "actual_risk_pct": round(actual_risk_pct, 2),
                    "entry_fee": round(entry_fee, 4),
                    "funding_paid": 0.0,
                    "bars_held": 0,
                    "start_balance": round(balance, 2)
                }
                pending_order = None

            # 2. Evaluate active position for exit on current bar
            if active_trade is not None:
                active_trade["bars_held"] += 1
                # Accumulate funding fee every 8 hours (approx 96 M5 bars)
                if active_trade["bars_held"] % 96 == 0:
                    active_trade["funding_paid"] += active_trade["notional"] * funding_8h_pct

                side = active_trade["side"]
                sl = active_trade["sl"]
                tp = active_trade["tp"]
                entry = active_trade["entry_price"]
                qty = active_trade["qty"]
                
                closed = False
                exit_price = 0.0
                close_reason = ""
                
                # PESSIMISTIC SAME-BAR COLLISION:
                # If both SL and TP are within candle high/low, SL ALWAYS hits first!
                if side == "LONG":
                    if c_low <= sl:
                        # Slippage on SL exit (sell lower)
                        exit_price = sl * (1.0 - slippage_pct)
                        close_reason = "STOP_LOSS_HIT"
                        closed = True
                    elif c_high >= tp:
                        exit_price = tp
                        close_reason = "TAKE_PROFIT_HIT"
                        closed = True
                elif side == "SHORT":
                    if c_high >= sl:
                        # Slippage on SL exit (buy higher)
                        exit_price = sl * (1.0 + slippage_pct)
                        close_reason = "STOP_LOSS_HIT"
                        closed = True
                    elif c_low <= tp:
                        exit_price = tp
                        close_reason = "TAKE_PROFIT_HIT"
                        closed = True
                        
                if closed:
                    exit_fee_rate = maker_fee_pct if close_reason == "TAKE_PROFIT_HIT" else taker_fee_pct
                    exit_fee = (exit_price * qty) * exit_fee_rate
                    total_fees = active_trade["entry_fee"] + exit_fee + active_trade["funding_paid"]
                    
                    if side == "LONG":
                        gross_pnl = (exit_price - entry) * qty
                    else:
                        gross_pnl = (entry - exit_price) * qty
                        
                    net_pnl = gross_pnl - total_fees
                    r_mult = net_pnl / active_trade["actual_dollar_risk"] if active_trade["actual_dollar_risk"] > 0 else 0.0
                    
                    balance += net_pnl
                    if balance > peak_balance: peak_balance = balance
                    dd = peak_balance - balance
                    dd_p = (dd / peak_balance) * 100.0
                    if dd > max_dd_usd: max_dd_usd = dd
                    if dd_p > max_dd_pct: max_dd_pct = dd_p
                    
                    active_trade["exit_price"] = round(exit_price, 2)
                    active_trade["exit_time"] = dt_utc.strftime("%Y-%m-%d %H:%M")
                    active_trade["close_reason"] = close_reason
                    active_trade["net_pnl"] = round(net_pnl, 4)
                    active_trade["fee_total"] = round(total_fees, 4)
                    active_trade["r_multiple"] = round(r_mult, 2)
                    active_trade["end_balance"] = round(balance, 2)
                    trades.append(active_trade)
                    active_trade = None

            # 3. Entry Signal Generation on COMPLETED candle i (Zero Lookahead!)
            if c_time < warmup_cutoff or active_trade is not None or pending_order is not None:
                continue
                
            is_bull_flip = (st_dir[i-1] == -1 and st_dir[i] == 1)
            is_bear_flip = (st_dir[i-1] == 1 and st_dir[i] == -1)
            
            if not (is_bull_flip or is_bear_flip):
                continue
                
            # Session check
            if not (7 <= dt_utc.hour < 21):
                continue
                
            # Zero-Lookahead H1 EMA check (only use fully closed H1)
            h_closed_idx = m5_to_closed_h1[i]
            if h_closed_idx < 0:
                continue
            h1_c = h1_closes[h_closed_idx]
            h1_e = h1_ema[h_closed_idx]
            
            if is_bull_flip and h1_c <= h1_e:
                continue
            if is_bear_flip and h1_c >= h1_e:
                continue
                
            # Volume Expansion >= 1.30x (10-bar prior)
            prior_vols = volumes[max(0, i-10):i]
            avg_vol = sum(prior_vols) / len(prior_vols) if prior_vols else 1.0
            if (c_vol / max(1.0, avg_vol)) < 1.30:
                continue
                
            # ATR floor
            if c_atr < 1.50:
                continue
                
            # Calculate SL and TP levels based on candle i close
            signal_side = "LONG" if is_bull_flip else "SHORT"
            close_p = c_close
            if signal_side == "LONG":
                raw_sl_dist = (close_p - st[i]) + (0.20 * c_atr)
            else:
                raw_sl_dist = (st[i] - close_p) + (0.20 * c_atr)
            sl_dist = min(40.0, max(10.0, raw_sl_dist))
            tp_dist = 2.0 * sl_dist
            sl_price = close_p - sl_dist if signal_side == "LONG" else close_p + sl_dist
            tp_price = close_p + tp_dist if signal_side == "LONG" else close_p - tp_dist
            
            # Queue pending order to be executed on the OPEN of candle i+1!
            pending_order = {
                "side": signal_side,
                "sl": sl_price,
                "tp": tp_price,
                "signal_time": dt_utc.strftime("%Y-%m-%d %H:%M")
            }

        return trades, balance, max_dd_usd, max_dd_pct

    # --- EXPERIMENT 1: BASELINE WITH REALISTIC FRICTION & ZERO LOOKAHEAD ---
    trades_base, end_bal_base, dd_usd_base, dd_pct_base = execute_simulation(
        slippage_pct=0.0005,      # 0.05% slippage on entry and SL exit
        taker_fee_pct=0.0005,     # 0.05% taker fee
        maker_fee_pct=0.0002,     # 0.02% maker fee on TP
        funding_8h_pct=0.0001,    # 0.01% funding every 8 hours
        execution_delay_bars=1    # Entered at OPEN of NEXT candle
    )
    
    # --- EXPERIMENT 2: HIGH-STRESS (DOUBLE SLIPPAGE 0.10% + WORST FEES) ---
    trades_stress, end_bal_stress, dd_usd_stress, dd_pct_stress = execute_simulation(
        slippage_pct=0.0010,      # 0.10% slippage on entry and exit!
        taker_fee_pct=0.0006,     # 0.06% VIP0 fee
        maker_fee_pct=0.0002,
        funding_8h_pct=0.00015
    )

    # Compile Statistics for Baseline
    total_t = len(trades_base)
    wins = [t for t in trades_base if t["net_pnl"] > 0]
    losses = [t for t in trades_base if t["net_pnl"] <= 0]
    
    n_wins = len(wins)
    n_losses = len(losses)
    wr = (n_wins / total_t) * 100.0 if total_t > 0 else 0.0
    
    tot_win_usd = sum(t["net_pnl"] for t in wins)
    tot_loss_usd = abs(sum(t["net_pnl"] for t in losses))
    net_profit = tot_win_usd - tot_loss_usd
    pf = (tot_win_usd / tot_loss_usd) if tot_loss_usd > 0 else 0.0
    
    avg_win = tot_win_usd / n_wins if n_wins > 0 else 0.0
    avg_loss = tot_loss_usd / n_losses if n_losses > 0 else 0.0
    avg_r = sum(t["r_multiple"] for t in trades_base) / total_t if total_t > 0 else 0.0
    
    # Sizing / MinNotional Risk Audit
    risk_pcts = [t["actual_risk_pct"] for t in trades_base]
    avg_risk_pct = sum(risk_pcts) / len(risk_pcts) if risk_pcts else 0.0
    max_risk_pct = max(risk_pcts) if risk_pcts else 0.0
    min_risk_pct = min(risk_pcts) if risk_pcts else 0.0
    
    # Streaks
    max_w_streak, max_l_streak = 0, 0
    cur_w, cur_l = 0, 0
    for t in trades_base:
        if t["net_pnl"] > 0:
            cur_w += 1; cur_l = 0
            if cur_w > max_w_streak: max_w_streak = cur_w
        else:
            cur_l += 1; cur_w = 0
            if cur_l > max_l_streak: max_l_streak = cur_l
            
    # Walk-Forward / Out-of-Sample (OOS) Split (Days 1-120 Train vs Days 121-180 Test)
    # Split by date (August 4, 2026 cutoff)
    train_trades = [t for t in trades_base if t["entry_time"] < "2026-08-04"]
    oos_trades = [t for t in trades_base if t["entry_time"] >= "2026-08-04"]
    
    def calc_stats(sub_trades, start_equity):
        if not sub_trades: return {}
        w = [t for t in sub_trades if t["net_pnl"] > 0]
        l = [t for t in sub_trades if t["net_pnl"] <= 0]
        win_sum = sum(t["net_pnl"] for t in w)
        loss_sum = abs(sum(t["net_pnl"] for t in l))
        net = win_sum - loss_sum
        return {
            "trades": len(sub_trades),
            "wins": len(w),
            "losses": len(l),
            "wr": (len(w) / len(sub_trades)) * 100.0,
            "net": net,
            "pf": (win_sum / loss_sum) if loss_sum > 0 else 999.0
        }
        
    train_stats = calc_stats(train_trades, 20.0)
    oos_stats = calc_stats(oos_trades, 20.0 + train_stats.get("net", 0.0))

    # --- MONTE CARLO SIMULATION (1,000 PERMUTATIONS) ---
    print("🎲 Running 1,000 Monte Carlo Trade Sequence Permutations...")
    pnls = [t["net_pnl"] for t in trades_base]
    mc_max_dds = []
    mc_ruin_count = 0
    
    for _ in range(1000):
        shuffled = pnls.copy()
        random.shuffle(shuffled)
        sim_bal = 20.0
        sim_peak = sim_bal
        sim_max_dd = 0.0
        ruined = False
        
        for p in shuffled:
            sim_bal += p
            if sim_bal > sim_peak: sim_peak = sim_bal
            dd_p = ((sim_peak - sim_bal) / sim_peak) * 100.0
            if dd_p > sim_max_dd: sim_max_dd = dd_p
            if sim_bal <= 10.0:  # 50% drawdown = ruin
                ruined = True
                
        mc_max_dds.append(sim_max_dd)
        if ruined: mc_ruin_count += 1
        
    mc_max_dds.sort()
    mc_median_dd = mc_max_dds[500]
    mc_95_dd = mc_max_dds[950]
    mc_99_dd = mc_max_dds[990]
    prob_ruin = (mc_ruin_count / 1000.0) * 100.0

    # Monthly Breakdown
    monthly_stats = {}
    for t in trades_base:
        m_key = t["entry_time"][:7]
        if m_key not in monthly_stats:
            monthly_stats[m_key] = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        monthly_stats[m_key]["trades"] += 1
        monthly_stats[m_key]["pnl"] += t["net_pnl"]
        if t["net_pnl"] > 0: monthly_stats[m_key]["wins"] += 1
        else: monthly_stats[m_key]["losses"] += 1

    # Print Executive Stress Report
    print("\n" + "=" * 80)
    print("🚨 FRAGILITY AUDIT: STRESS-TEST RESULTS (STRICT FRICTION & ZERO LOOKAHEAD)")
    print("=" * 80)
    print(f"  Total Trades (180 Days)      : {total_t}")
    print(f"  Starting Balance             : $20.00 USDT")
    print(f"  Final Balance (Realistic)    : ${end_bal_base:.2f} USDT (Net: ${net_profit:+.2f} / {(net_profit/20)*100:+.1f}%)")
    print(f"  Final Balance (High-Stress)  : ${end_bal_stress:.2f} USDT (Double Slippage 0.10%)")
    print(f"  Win Rate                     : {wr:.1f}% ({n_wins} Wins / {n_losses} Losses)")
    print(f"  Profit Factor (PF)           : {pf:.2f}")
    print(f"  Average R-Multiple           : {avg_r:+.2f}R per trade")
    print(f"  Average Win vs Avg Loss      : +${avg_win:.2f} vs -${avg_loss:.2f} (R:R {avg_win/avg_loss if avg_loss > 0 else 0:.2f}:1)")
    print(f"  Max Drawdown (Historical)    : ${dd_usd_base:.2f} ({dd_pct_base:.1f}%)")
    print(f"  Max Consecutive Losses       : {max_l_streak} losses in a row")
    print("-" * 80)
    print("⚡ MIN-NOTIONAL ($20) RISK AUDIT:")
    print(f"  Target Risk Pct              : 1.00% ($0.20)")
    print(f"  Actual Average Risk Pct      : {avg_risk_pct:.2f}%")
    print(f"  Actual Max Risk Pct          : {max_risk_pct:.2f}% (Forced by Binance 20 USDT MinNotional)")
    print(f"  Actual Min Risk Pct          : {min_risk_pct:.2f}%")
    print("-" * 80)
    print("🧪 WALK-FORWARD / OUT-OF-SAMPLE (OOS) VALIDATION:")
    print(f"  In-Sample (Train 120 Days)   : {train_stats.get('trades')} trades | WR: {train_stats.get('wr', 0):.1f}% | PF: {train_stats.get('pf', 0):.2f} | Net: ${train_stats.get('net', 0):+.2f}")
    print(f"  Out-of-Sample (Test 60 Days) : {oos_stats.get('trades')} trades | WR: {oos_stats.get('wr', 0):.1f}% | PF: {oos_stats.get('pf', 0):.2f} | Net: ${oos_stats.get('net', 0):+.2f}")
    print("-" * 80)
    print("🎲 MONTE CARLO (1,000 RUNS) SEQUENCE RISK:")
    print(f"  Median Expected Drawdown     : {mc_median_dd:.1f}%")
    print(f"  95% Confidence Worst-Case DD : {mc_95_dd:.1f}%")
    print(f"  99% Confidence Extreme DD    : {mc_99_dd:.1f}%")
    print(f"  Probability of Ruin (50% DD) : {prob_ruin:.1f}%")
    print("=" * 80)
    
    print("\n📅 MONTHLY BREAKDOWN (UNDER REALISTIC FRICTION):")
    print("-" * 65)
    print(f"{'Month':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Net PnL ($)':<12} | {'Status'}")
    print("-" * 65)
    for m, s in sorted(monthly_stats.items()):
        m_wr = (s['wins'] / s['trades']) * 100.0 if s['trades'] > 0 else 0.0
        status = "🟢 PROFIT" if s['pnl'] > 0 else "🔴 LOSS"
        print(f"{m:<10} | {s['trades']:<8} | {m_wr:>5.1f}%     | {s['pnl']:>+9.2f}    | {status}")
    print("-" * 65)

    # Save detailed CSV of all trades
    csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "data", "raw_trade_log_180d.csv")
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("TradeID,SignalTime,EntryTime,ExitTime,Side,RawEntry,ExecutedEntry,SL,TP,SL_Dist,TP_Dist,Qty,Margin,Notional,TargetRiskUSD,ActualRiskUSD,ActualRiskPct,ExitPrice,CloseReason,NetPnL,FeeTotal,R_Multiple,Balance\n")
        for t in trades_base:
            f.write(
                f"{t['id']},{t['signal_time']},{t['entry_time']},{t['exit_time']},{t['side']},"
                f"{t['raw_entry']},{t['entry_price']},{t['sl']},{t['tp']},{t['sl_dist']},{t['tp_dist']},"
                f"{t['qty']},{t['margin']},{t['notional']},{t['target_risk_usd']},{t['actual_dollar_risk']},"
                f"{t['actual_risk_pct']},{t['exit_price']},{t['close_reason']},{t['net_pnl']},"
                f"{t['fee_total']},{t['r_multiple']},{t['end_balance']}\n"
            )
    print(f"\n💾 Full Raw Trade CSV exported to: {csv_file}")
    
    # Return dictionary for programmatic use
    return {
        "baseline": {
            "total_trades": total_t,
            "wins": n_wins,
            "losses": n_losses,
            "win_rate": round(wr, 1),
            "profit_factor": round(pf, 2),
            "final_balance": round(end_bal_base, 2),
            "net_profit": round(net_profit, 2),
            "max_dd_pct": round(dd_pct_base, 1),
            "max_l_streak": max_l_streak,
            "avg_r": round(avg_r, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2)
        },
        "stress": {
            "final_balance": round(end_bal_stress, 2),
            "max_dd_pct": round(dd_pct_stress, 1)
        },
        "min_notional_risk": {
            "avg_risk_pct": round(avg_risk_pct, 2),
            "max_risk_pct": round(max_risk_pct, 2)
        },
        "walk_forward": {
            "train": train_stats,
            "oos": oos_stats
        },
        "monte_carlo": {
            "median_dd": round(mc_median_dd, 1),
            "dd_95": round(mc_95_dd, 1),
            "dd_99": round(mc_99_dd, 1),
            "ruin_prob": round(prob_ruin, 1)
        },
        "monthly": monthly_stats
    }

if __name__ == "__main__":
    run_stress_test()
