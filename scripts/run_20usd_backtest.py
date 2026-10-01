import os
import math
import time
from datetime import datetime, timezone

DATA_FILE = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"

def run_20usd_backtest():
    print("================================================================================")
    print("BACKTEST: ETHUSDT M5 SUPERTREND + H1 EMA200 (STARTING BALANCE: $20.00)")
    print("================================================================================")
    
    # 1. Load M1 and aggregate to M5
    m1_times, m1_opens, m1_highs, m1_lows, m1_closes, m1_vols = [], [], [], [], [], []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        f.readline()
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 6: continue
            m1_times.append(int(parts[0]))
            m1_opens.append(float(parts[1]))
            m1_highs.append(float(parts[2]))
            m1_lows.append(float(parts[3]))
            m1_closes.append(float(parts[4]))
            m1_vols.append(float(parts[5]))

    n_m1 = len(m1_times)
    m5_bars = []
    m5_sub_m1 = []
    cur_bucket_t = None
    cur_sub = []
    cur_o, cur_h, cur_l, cur_c, cur_v = 0.0, 0.0, 0.0, 0.0, 0.0

    for i in range(n_m1):
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

    n_m5 = len(m5_bars)
    
    # 2. Indicators
    highs = [b["high"] for b in m5_bars]
    lows = [b["low"] for b in m5_bars]
    closes = [b["close"] for b in m5_bars]
    vols = [b["volume"] for b in m5_bars]
    times = [b["time"] for b in m5_bars]
    
    # ATR 14
    tr = [0.0] * n_m5
    tr[0] = highs[0] - lows[0]
    for i in range(1, n_m5):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    atr = [0.0] * n_m5
    atr[13] = sum(tr[:14]) / 14.0
    for i in range(14, n_m5): atr[i] = (atr[i-1] * 13.0 + tr[i]) / 14.0
    
    # SuperTrend 10, 2.5
    st_period = 10
    st_mult = 2.5
    st_atr = [0.0] * n_m5
    st_atr[st_period-1] = sum(tr[:st_period]) / st_period
    for i in range(st_period, n_m5): st_atr[i] = (st_atr[i-1] * (st_period-1) + tr[i]) / st_period
    
    st_val = [0.0] * n_m5
    st_dir = [1] * n_m5
    upper = [0.0] * n_m5
    lower = [0.0] * n_m5
    for i in range(st_period, n_m5):
        hl2 = (highs[i] + lows[i]) / 2.0
        bu = hl2 + st_mult * st_atr[i]
        bl = hl2 - st_mult * st_atr[i]
        lower[i] = bl if bl > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]
        upper[i] = bu if bu < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
        if closes[i] > upper[i-1]: st_dir[i] = 1
        elif closes[i] < lower[i-1]: st_dir[i] = -1
        else: st_dir[i] = st_dir[i-1]
        st_val[i] = lower[i] if st_dir[i] == 1 else upper[i]
        
    # H1 bars & EMA 200
    h1_bars = []
    m5_to_h1 = [-1] * n_m5
    cur_h1 = None
    for i in range(n_m5):
        t = times[i]
        o, h, l, c, v = m5_bars[i]["open"], highs[i], lows[i], closes[i], vols[i]
        h1_t = (t // 3600000) * 3600000
        if cur_h1 is None: cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        elif cur_h1["time"] == h1_t:
            cur_h1["high"] = max(cur_h1["high"], h); cur_h1["low"] = min(cur_h1["low"], l); cur_h1["close"] = c; cur_h1["vol"] += v
        else:
            h1_bars.append(cur_h1)
            cur_h1 = {"time": h1_t, "open": o, "high": h, "low": l, "close": c, "vol": v}
        m5_to_h1[i] = len(h1_bars) - 1

    h1_closes = [b["close"] for b in h1_bars]
    h1_ema200 = [0.0] * len(h1_closes)
    k = 2.0 / 201.0
    if len(h1_closes) > 0:
        h1_ema200[0] = h1_closes[0]
        for i in range(1, len(h1_closes)):
            h1_ema200[i] = h1_closes[i] * k + h1_ema200[i-1] * (1.0 - k)

    # 3. Simulate with multiple risk sizes starting strictly at $20.00
    # Note: On Binance Futures, minNotional = $20 USDT, minQty = 0.001 ETH, stepSize = 0.001 ETH.
    risk_modes = [
        {"name": "1.0% Risk (Theoretical Exact Math)", "risk_pct": 0.01, "enforce_min_notional": False},
        {"name": "1.0% Risk (Binance Min Notional 20 USDT Enforced)", "risk_pct": 0.01, "enforce_min_notional": True},
        {"name": "2.0% Risk (Binance Min Notional 20 USDT Enforced)", "risk_pct": 0.02, "enforce_min_notional": True},
        {"name": "3.0% Risk (Binance Min Notional 20 USDT Enforced)", "risk_pct": 0.03, "enforce_min_notional": True},
        {"name": "5.0% Risk (Binance Min Notional 20 USDT Enforced)", "risk_pct": 0.05, "enforce_min_notional": True},
        {"name": "Fixed Micro-Lot (0.008 ETH ~ $20-25 Notional)", "risk_pct": 0.0, "enforce_min_notional": True, "fixed_qty": 0.008}
    ]

    for rm in risk_modes:
        balance = 20.00
        peak_b = 20.00
        max_dd = 0.0
        trades = []
        in_pos = False
        pos = {}
        cooldown = 0
        daily_count = 0
        cur_day = ""
        
        entry_fee_rate = 0.0002
        tp_fee_rate = 0.0002
        sl_fee_rate = 0.0005
        
        for idx in range(100, n_m5):
            t = times[idx]
            dt = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
            day_str = dt.strftime("%Y-%m-%d")
            hour = dt.hour
            
            if day_str != cur_day:
                cur_day = day_str
                daily_count = 0
                
            # Intrabar exit evaluation
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
                    gp = (exit_p - entry) * qty if side == "LONG" else (entry - exit_p) * qty
                    comm = pos["entry_comm"] + round(qty * exit_p * (tp_fee_rate if reason == "TP_HIT" else sl_fee_rate), 4)
                    net = gp - comm
                    balance += net
                    if balance > peak_b: peak_b = balance
                    dd = (peak_b - balance) / peak_b * 100.0
                    if dd > max_dd: max_dd = dd
                    trades.append({
                        "side": side, "entry": entry, "exit": exit_p, "qty": qty,
                        "reason": reason, "net_pnl": net, "balance": balance, "dd": dd
                    })
                    in_pos = False; pos = {}; cooldown = idx + 2; daily_count += 1
                    
            # Entry evaluation
            if not in_pos and idx >= cooldown and daily_count < 3:
                if not (7 <= hour < 21): continue
                
                p_dir = st_dir[idx-1]
                c_dir = st_dir[idx]
                c_st = st_val[idx]
                curr_c = closes[idx]
                c_atr = atr[idx]
                
                h1_idx = m5_to_h1[idx]
                if h1_idx < 200: continue
                h1_c = h1_closes[h1_idx]
                h1_ema = h1_ema200[h1_idx]
                h1_bull = h1_c > h1_ema
                h1_bear = h1_c < h1_ema
                
                v_avg_10 = sum(vols[max(0, idx-10):idx]) / 10.0 if idx >= 10 else vols[idx]
                v_ratio = vols[idx] / max(1.0, v_avg_10)
                if v_ratio < 1.3: continue
                
                sig = None
                sl_dist = 0.0
                if p_dir == -1 and c_dir == 1 and h1_bull:
                    sig = "LONG"
                    sl_dist = max(10.0, (curr_c - c_st) + 0.2 * c_atr)
                elif p_dir == 1 and c_dir == -1 and h1_bear:
                    sig = "SHORT"
                    sl_dist = max(10.0, (c_st - curr_c) + 0.2 * c_atr)
                    
                if sig:
                    # Next bar penetration test (Post-Only)
                    if idx + 1 >= n_m5: continue
                    nb = m5_bars[idx+1]
                    penetrated = (nb["low"] <= curr_c) if sig == "LONG" else (nb["high"] >= curr_c)
                    if not penetrated: continue
                    
                    # Position sizing
                    if "fixed_qty" in rm:
                        qty = rm["fixed_qty"]
                    else:
                        risk_usd = balance * rm["risk_pct"]
                        calc_qty = risk_usd / sl_dist
                        if rm.get("enforce_min_notional", False):
                            min_notional_qty = math.ceil(20.0 / curr_c / 0.001) * 0.001
                            qty = round(max(calc_qty, min_notional_qty), 3)
                        else:
                            qty = max(0.001, round(calc_qty, 3))
                        
                    notional = qty * curr_c
                    sl_p = round(curr_c - sl_dist, 2) if sig == "LONG" else round(curr_c + sl_dist, 2)
                    tp_p = round(curr_c + 2.0 * sl_dist, 2) if sig == "LONG" else round(curr_c - 2.0 * sl_dist, 2)
                    entry_comm = round(qty * curr_c * entry_fee_rate, 4)
                    
                    in_pos = True
                    pos = {
                        "side": sig, "entry": curr_c, "sl": sl_p, "tp": tp_p, "qty": qty,
                        "sl_dist": sl_dist, "entry_comm": entry_comm, "notional": notional
                    }
                    
        # Calculate summary
        n_trades = len(trades)
        wins = [t for t in trades if t["net_pnl"] > 0]
        losses = [t for t in trades if t["net_pnl"] <= 0]
        wr = len(wins) / n_trades * 100.0 if n_trades > 0 else 0.0
        tot_win = sum(t["net_pnl"] for t in wins)
        tot_loss = abs(sum(t["net_pnl"] for t in losses)) if losses else 0.0001
        pf = tot_win / tot_loss
        net_pnl = balance - 20.00
        roi = net_pnl / 20.00 * 100.0
        
        print(f"\n--- {rm['name']} ---")
        print(f"  Starting Balance : $20.00")
        print(f"  Final Balance    : ${balance:.2f} ({roi:+.2f}%)")
        print(f"  Net Profit       : ${net_pnl:+.2f}")
        print(f"  Total Trades     : {n_trades} (Wins: {len(wins)}, Losses: {len(losses)})")
        print(f"  Win Rate         : {wr:.2f}%")
        print(f"  Profit Factor    : {pf:.2f}")
        print(f"  Max Drawdown     : {max_dd:.2f}%")
        if trades:
            sample = trades[0]
            print(f"  Trade #1 Example : Qty={sample['qty']} ETH | Entry=${sample['entry']:.2f} | Exit=${sample['exit']:.2f} | PnL=${sample['net_pnl']:+.2f} | Bal=${sample['balance']:.2f}")

if __name__ == "__main__":
    run_20usd_backtest()
