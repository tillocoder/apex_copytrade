#!/usr/bin/env python3
"""
APEX QUANT v3.4 — 180-DAY FORENSIC AUDIT & BACKTEST ENGINE
Asset: ETHUSDT.P (Binance Futures) | Timeframe: M5
Strategy: M5 SuperTrend (10, 2.5) + H1 EMA 200 + Volume >= 1.3x
Risk Model: 1.0% Account Risk Compounding | 20x Leverage | Starting Balance: $20.00
Take Profit: 2.0R | Stop Loss: SuperTrend Line + 0.20 ATR (Clamped $10 - $40)
Session: 07:00 - 21:00 UTC (Institutional Liquidity Window)
Fee Model: Maker 0.02% Entry, Maker 0.02% TP Exit, Taker 0.05% SL Exit
"""

import os
import sys
import json
import math
import time
import urllib.request
from datetime import datetime, timezone, timedelta

def fetch_binance_klines(symbol="ETHUSDT", interval="5m", days=180):
    now_ms = int(time.time() * 1000)
    # Fetch extra 10 days for indicator warm-up (H1 EMA 200 requires ~200 hours = 8.3 days)
    total_days = days + 12
    start_ms = now_ms - (total_days * 24 * 3600 * 1000)
    
    print(f"📥 Fetching {days} days of {interval} klines for {symbol} from Binance Futures...")
    
    all_candles = []
    current_start = start_ms
    batch_count = 0
    
    while current_start < now_ms:
        batch_count += 1
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&startTime={current_start}&limit=1500"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                if not data:
                    break
                for k in data:
                    all_candles.append({
                        "time": int(k[0]),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                current_start = int(data[-1][0]) + 1
                if len(data) < 1500:
                    break
                time.sleep(0.08)  # Gentle rate limiting
        except Exception as e:
            print(f"   [WARN] Batch {batch_count} retry: {e}")
            time.sleep(1.0)
            
    # Deduplicate by timestamp
    unique_candles = []
    seen = set()
    for c in all_candles:
        if c["time"] not in seen:
            seen.add(c["time"])
            unique_candles.append(c)
            
    print(f"   ✅ Fetched {len(unique_candles)} {interval} candles.")
    return unique_candles

def run_180d_backtest():
    print("=" * 80)
    print("🚀 APEX QUANT v3.4: 180-DAY BACKTEST STARTING")
    print("   Starting Capital: $20.00 | Account Risk: 1.0% | Leverage: 20x")
    print("   Asset: ETHUSDT.P | Execution: M5 SuperTrend (10, 2.5) + H1 EMA 200")
    print("=" * 80)
    
    # 1. Fetch H1 klines for Macro EMA 200
    h1_candles = fetch_binance_klines("ETHUSDT", "1h", days=180)
    # Calculate H1 EMA 200
    h1_closes = [c["close"] for c in h1_candles]
    h1_times = [c["time"] for c in h1_candles]
    n_h1 = len(h1_closes)
    
    k_ema = 2.0 / 201.0
    h1_ema = [0.0] * n_h1
    h1_ema[0] = h1_closes[0]
    for i in range(1, n_h1):
        h1_ema[i] = h1_closes[i] * k_ema + h1_ema[i-1] * (1.0 - k_ema)
        
    # 2. Fetch M5 klines
    m5_candles = fetch_binance_klines("ETHUSDT", "5m", days=180)
    n_m5 = len(m5_candles)
    
    highs = [c["high"] for c in m5_candles]
    lows = [c["low"] for c in m5_candles]
    closes = [c["close"] for c in m5_candles]
    volumes = [c["volume"] for c in m5_candles]
    times = [c["time"] for c in m5_candles]
    
    # 3. Indicators: ATR & SuperTrend (10, 2.5)
    tr = [highs[0] - lows[0]]
    for i in range(1, n_m5):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        
    period = 10
    mult = 2.5
    atr = [0.0] * n_m5
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

    # Map M5 time to latest closed H1 bar
    h1_idx_map = [-1] * n_m5
    h_idx = 0
    for i in range(n_m5):
        t = times[i]
        while h_idx + 1 < n_h1 and h1_times[h_idx + 1] <= t:
            h_idx += 1
        h1_idx_map[i] = h_idx

    # Simulation Execution State
    initial_balance = 20.00
    balance = initial_balance
    peak_balance = balance
    max_drawdown_usd = 0.0
    max_drawdown_pct = 0.0
    
    trades = []
    active_trade = None
    
    # Filter boundary: start only after warm-up period (first 12 days)
    warmup_cutoff_ms = times[0] + (12 * 24 * 3600 * 1000)
    
    # 4. Main Event Loop
    for i in range(period + 2, n_m5):
        c_time = times[i]
        c_open = m5_candles[i]["open"]
        c_high = highs[i]
        c_low = lows[i]
        c_close = closes[i]
        c_vol = volumes[i]
        c_atr = atr[i]
        
        dt_utc = datetime.fromtimestamp(c_time / 1000, tz=timezone.utc)
        
        # A. Evaluate Active Trade Exit (if any)
        if active_trade is not None:
            side = active_trade["side"]
            sl = active_trade["sl"]
            tp = active_trade["tp"]
            entry = active_trade["entry_price"]
            qty = active_trade["qty"]
            entry_fee = active_trade["entry_fee"]
            
            # Intra-candle check: Did price hit TP or SL on this candle?
            closed = False
            exit_price = 0.0
            close_reason = ""
            
            if side == "LONG":
                # Check SL first for conservative auditing
                if c_low <= sl:
                    exit_price = sl
                    close_reason = "STOP_LOSS_HIT"
                    closed = True
                elif c_high >= tp:
                    exit_price = tp
                    close_reason = "TAKE_PROFIT_HIT"
                    closed = True
            elif side == "SHORT":
                if c_high >= sl:
                    exit_price = sl
                    close_reason = "STOP_LOSS_HIT"
                    closed = True
                elif c_low <= tp:
                    exit_price = tp
                    close_reason = "TAKE_PROFIT_HIT"
                    closed = True
                    
            if closed:
                # Fee calculation: 0.02% maker for TP, 0.05% taker for SL
                exit_fee_rate = 0.0002 if close_reason == "TAKE_PROFIT_HIT" else 0.0005
                exit_fee = (exit_price * qty) * exit_fee_rate
                
                if side == "LONG":
                    gross_pnl = (exit_price - entry) * qty
                else:
                    gross_pnl = (entry - exit_price) * qty
                    
                net_pnl = gross_pnl - entry_fee - exit_fee
                balance += net_pnl
                
                if balance > peak_balance:
                    peak_balance = balance
                dd_usd = peak_balance - balance
                dd_pct = (dd_usd / peak_balance) * 100.0
                if dd_usd > max_drawdown_usd: max_drawdown_usd = dd_usd
                if dd_pct > max_drawdown_pct: max_drawdown_pct = dd_pct
                
                active_trade["exit_price"] = exit_price
                active_trade["exit_time"] = dt_utc.strftime("%Y-%m-%d %H:%M")
                active_trade["close_reason"] = close_reason
                active_trade["net_pnl"] = round(net_pnl, 4)
                active_trade["fee"] = round(entry_fee + exit_fee, 4)
                active_trade["end_balance"] = round(balance, 2)
                trades.append(active_trade)
                active_trade = None

        # B. Skip entry checks if we are still in warm-up or already have an active trade
        if c_time < warmup_cutoff_ms or active_trade is not None:
            continue
            
        # C. Detect SuperTrend Flip on completed M5 candle
        is_bull_flip = (st_dir[i-1] == -1 and st_dir[i] == 1)
        is_bear_flip = (st_dir[i-1] == 1 and st_dir[i] == -1)
        
        if not (is_bull_flip or is_bear_flip):
            continue
            
        # D. Session Window Filter: 07:00 - 21:00 UTC
        hour_utc = dt_utc.hour
        if not (7 <= hour_utc < 21):
            continue
            
        # E. Macro Filter: H1 EMA 200
        h_idx = h1_idx_map[i]
        if h_idx < 0:
            continue
        h1_c = h1_closes[h_idx]
        h1_e = h1_ema[h_idx]
        h1_bull = h1_c > h1_e
        h1_bear = h1_c < h1_e
        
        if is_bull_flip and not h1_bull:
            continue
        if is_bear_flip and not h1_bear:
            continue
            
        # F. Breakout Volume Expansion Filter: >= 1.30x (10-bar prior average)
        prior_10_vols = volumes[max(0, i-10):i]
        avg_10_vol = sum(prior_10_vols) / len(prior_10_vols) if prior_10_vols else 1.0
        vol_ratio = c_vol / max(1.0, avg_10_vol)
        if vol_ratio < 1.30:
            continue
            
        # G. Volatility Floor: ATR M5 >= $1.50
        if c_atr < 1.50:
            continue
            
        # H. Position Sizing & Geometry
        side = "LONG" if is_bull_flip else "SHORT"
        entry_price = c_close
        
        if side == "LONG":
            raw_sl_dist = (entry_price - st[i]) + (0.20 * c_atr)
        else:
            raw_sl_dist = (st[i] - entry_price) + (0.20 * c_atr)
            
        sl_dist = min(40.0, max(10.0, raw_sl_dist))
        tp_dist = 2.0 * sl_dist
        
        sl_price = round(entry_price - sl_dist if side == "LONG" else entry_price + sl_dist, 2)
        tp_price = round(entry_price + tp_dist if side == "LONG" else entry_price - tp_dist, 2)
        
        # 1.0% Account Risk Budget
        dollar_risk_budget = balance * 0.01  # $0.20 on $20
        raw_qty = dollar_risk_budget / sl_dist
        # Binance min notional: 20 USDT -> min qty at $2700 is ~0.008 ETH
        min_qty_notional = 20.0 / entry_price
        qty = round(max(raw_qty, min_qty_notional, 0.001), 3)
        notional = qty * entry_price
        margin = notional / 20.0  # 20x leverage
        
        # Post-only Maker Entry Fee (0.02%)
        entry_fee = notional * 0.0002
        
        active_trade = {
            "id": len(trades) + 1,
            "side": side,
            "entry_time": dt_utc.strftime("%Y-%m-%d %H:%M"),
            "entry_price": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "sl_dist": round(sl_dist, 2),
            "tp_dist": round(tp_dist, 2),
            "qty": qty,
            "notional": round(notional, 2),
            "margin": round(margin, 2),
            "entry_fee": round(entry_fee, 4),
            "vol_ratio": round(vol_ratio, 2),
            "start_balance": round(balance, 2)
        }

    # 5. Compile Backtest Statistics
    total_trades = len(trades)
    if total_trades == 0:
        print("❌ No trades qualified under these parameters.")
        return
        
    wins = [t for t in trades if t["net_pnl"] > 0]
    losses = [t for t in trades if t["net_pnl"] <= 0]
    
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = (n_wins / total_trades) * 100.0
    
    total_profit = sum(t["net_pnl"] for t in wins)
    total_loss = abs(sum(t["net_pnl"] for t in losses))
    net_pnl = total_profit - total_loss
    profit_factor = (total_profit / total_loss) if total_loss > 0 else 999.0
    
    avg_win = total_profit / n_wins if n_wins > 0 else 0.0
    avg_loss = total_loss / n_losses if n_losses > 0 else 0.0
    reward_to_risk = avg_win / avg_loss if avg_loss > 0 else 0.0
    
    roi_pct = ((balance - initial_balance) / initial_balance) * 100.0
    
    # Consecutive streaks
    max_consec_wins = 0
    max_consec_losses = 0
    cur_w, cur_l = 0, 0
    for t in trades:
        if t["net_pnl"] > 0:
            cur_w += 1
            cur_l = 0
            if cur_w > max_consec_wins: max_consec_wins = cur_w
        else:
            cur_l += 1
            cur_w = 0
            if cur_l > max_consec_losses: max_consec_losses = cur_l
            
    # Monthly Breakdown
    monthly_stats = {}
    for t in trades:
        m_key = t["entry_time"][:7]  # YYYY-MM
        if m_key not in monthly_stats:
            monthly_stats[m_key] = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        monthly_stats[m_key]["trades"] += 1
        monthly_stats[m_key]["pnl"] += t["net_pnl"]
        if t["net_pnl"] > 0:
            monthly_stats[m_key]["wins"] += 1
        else:
            monthly_stats[m_key]["losses"] += 1

    print("\n" + "=" * 80)
    print("📊 180-DAY BACKTEST EXECUTIVE RESULTS (ETHUSDT M5 SUPERTREND)")
    print("=" * 80)
    print(f"  Period                     : 180 Days (Last 6 Months up to Today)")
    print(f"  Starting Balance           : ${initial_balance:.2f} USDT")
    print(f"  Final Balance              : ${balance:.2f} USDT")
    print(f"  Total Net Profit           : ${net_pnl:+.2f} USDT ({roi_pct:+.1f}%)")
    print(f"  Profit Factor              : {profit_factor:.2f}")
    print(f"  Win Rate                   : {win_rate:.1f}% ({n_wins} Wins / {n_losses} Losses)")
    print(f"  Total Trades               : {total_trades} (Avg ~{total_trades/180:.2f} trades/day)")
    print(f"  Max Account Drawdown       : ${max_drawdown_usd:.2f} ({max_drawdown_pct:.1f}%)")
    print(f"  Average Trade PnL          : ${net_pnl/total_trades:+.2f}")
    print(f"  Average Win vs Avg Loss    : +${avg_win:.2f} vs -${avg_loss:.2f} (R:R {reward_to_risk:.2f}:1)")
    print(f"  Max Consecutive Wins       : {max_consec_wins}")
    print(f"  Max Consecutive Losses     : {max_consec_losses}")
    print("=" * 80)
    
    print("\n📅 MONTHLY PERFORMANCE BREAKDOWN:")
    print("-" * 65)
    print(f"{'Month':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Net PnL ($)':<12} | {'Status'}")
    print("-" * 65)
    for m, s in sorted(monthly_stats.items()):
        wr = (s['wins'] / s['trades']) * 100.0 if s['trades'] > 0 else 0.0
        status = "🟢 PROFIT" if s['pnl'] > 0 else "🔴 LOSS"
        print(f"{m:<10} | {s['trades']:<8} | {wr:>5.1f}%     | {s['pnl']:>+9.2f}    | {status}")
    print("-" * 65)

    # Save detailed JSON report
    report_data = {
        "period_days": 180,
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "net_pnl": round(net_pnl, 2),
        "roi_pct": round(roi_pct, 1),
        "profit_factor": round(profit_factor, 2),
        "win_rate_pct": round(win_rate, 1),
        "total_trades": total_trades,
        "wins": n_wins,
        "losses": n_losses,
        "max_drawdown_usd": round(max_drawdown_usd, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "reward_to_risk": round(reward_to_risk, 2),
        "max_consec_wins": max_consec_wins,
        "max_consec_losses": max_consec_losses,
        "monthly": monthly_stats,
        "trades": trades
    }
    
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "data", "backtest_180d_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\n💾 Full 180-day results saved to: {out_file}")

if __name__ == "__main__":
    run_180d_backtest()
