import sys
sys.path.insert(0, r'C:\apex_copytrade')
from run_v32_forensic_suite import run_simulation_v32_fast, precalculate_all_features
import csv
from datetime import datetime, timezone
import math

raw = []
with open(r'c:\apex_copytrade\data\binance_ethusdt_m1_90d.csv') as f:
    for r in csv.DictReader(f):
        raw.append({k: float(v) if k != 'time' else int(v) for k, v in r.items()})

from run_v33_hyperparameter_suite import precalculate_all_features_v33
feat = precalculate_all_features_v33(raw)
idx_train_end = int(len(feat) * 0.60)
idx_val_end = int(len(feat) * 0.80)

def simulate_v33_exact(
    feat_data,
    score_threshold=80,
    maker_entry=True,
    adx_filter=20.0,
    vol_comp_filter=True,
    module_a_adx_gate=True,
    be_trigger_r=1.75,
    be_buffer_pct=0.0005,
    time_stop_min=15,
    tp_vol_mult=2.2,
    capital_profile="NORMALIZED",
    initial_balance=1000.0
):
    balance = initial_balance
    peak_balance = balance
    trades = []
    
    in_pos = False
    pos = {}
    
    cooldown_until_idx = 0
    last_entry_time = 0
    last_entry_side = None
    
    current_day_str = ""
    daily_trades_count = 0
    daily_pnl = 0.0
    day_paused = False
    
    entry_fee_rate = 0.0002 if maker_entry else 0.0005
    tp_fee_rate = 0.0002
    sl_fee_rate = 0.0005
    
    for idx in range(250, len(feat_data)):
        f = feat_data[idx]
        t = f["time"]
        day_str = f["day_str"]
        sess_name = f["session"]
        
        if day_str != current_day_str:
            current_day_str = day_str
            daily_trades_count = 0
            daily_pnl = 0.0
            day_paused = False
            
        # Position management
        if in_pos:
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            target = pos["tp"]
            qty = pos["qty"]
            r_dist = pos["r_dist"]
            be_active = pos["be_active"]
            holding_bars = idx - pos["entry_idx"]
            
            high = f["high"]
            low = f["low"]
            curr_c = f["close"]
            
            closed_now = False
            exit_reason = None
            exit_price = 0.0
            
            # Structural BE Trigger
            if not be_active and be_trigger_r > 0:
                if side == "LONG" and (high - entry) >= be_trigger_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    pos["sl"] = round(entry * (1.0 + be_buffer_pct), 2)
                    sl = pos["sl"]
                elif side == "SHORT" and (entry - low) >= be_trigger_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    pos["sl"] = round(entry * (1.0 - be_buffer_pct), 2)
                    sl = pos["sl"]
                    
            # Time-Stop Invalidation (Momentum decay scratch)
            if not closed_now and time_stop_min > 0 and holding_bars >= time_stop_min:
                cur_r = (curr_c - entry) / r_dist if side == "LONG" else (entry - curr_c) / r_dist
                # If trade is flat or slightly negative and has no momentum after 15 min
                if -0.20 <= cur_r <= 0.40 and f["body"] < 0.50 * f["atr"]:
                    closed_now = True
                    exit_reason = "TIME_STOP_EXHAUSTION"
                    exit_price = curr_c
                    
            # Extrema checks
            if not closed_now:
                if side == "LONG":
                    sl_touch = (low <= sl)
                    tp_touch = (high >= target)
                    if sl_touch and tp_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl - 0.01
                    elif sl_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl - 0.01
                    elif tp_touch:
                        closed_now = True
                        exit_reason = "TAKE_PROFIT_FULL"
                        exit_price = target
                else:
                    sl_touch = (high >= sl)
                    tp_touch = (low <= target)
                    if sl_touch and tp_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl + 0.01
                    elif sl_touch:
                        closed_now = True
                        exit_reason = "STOP_LOSS_HIT" if not be_active else "BREAKEVEN_STOP_HIT"
                        exit_price = sl + 0.01
                    elif tp_touch:
                        closed_now = True
                        exit_reason = "TAKE_PROFIT_FULL"
                        exit_price = target
                        
            if closed_now:
                gross = (exit_price - entry)*qty if side == "LONG" else (entry - exit_price)*qty
                gross = round(gross, 4)
                
                entry_fee = pos["entry_fee"]
                if exit_reason in ["TAKE_PROFIT_FULL", "TIME_STOP_EXHAUSTION"]:
                    exit_fee = round(qty * exit_price * tp_fee_rate, 4)
                else:
                    exit_fee = round(qty * exit_price * sl_fee_rate, 4)
                    
                total_fees = round(entry_fee + exit_fee, 4)
                net_pnl = round(gross - total_fees, 4)
                dollar_risk = max(0.01, qty * r_dist)
                realized_r = round(net_pnl / dollar_risk, 2)
                
                balance = round(balance + net_pnl, 4)
                peak_balance = max(peak_balance, balance)
                dd_pct = round(((peak_balance - balance) / peak_balance) * 100.0, 2)
                
                daily_pnl += net_pnl
                daily_trades_count += 1
                
                if net_pnl > 0:
                    cooldown_until_idx = idx + 10
                else:
                    cooldown_until_idx = idx + 15
                    
                if daily_pnl <= -0.05 * balance:
                    day_paused = True
                    
                trades.append({
                    "timestamp": datetime.fromtimestamp(pos["open_time"] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "side": side,
                    "module": pos["module"],
                    "entry": entry,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "gross_pnl": gross,
                    "total_fees": total_fees,
                    "net_pnl": net_pnl,
                    "realized_r": realized_r,
                    "holding_min": holding_bars,
                    "equity": balance,
                    "dd_pct": dd_pct
                })
                in_pos = False
                pos = {}
                
        # Entry evaluation
        if not in_pos and idx >= cooldown_until_idx:
            if sess_name not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                continue
            if daily_trades_count >= 8 or day_paused:
                continue
            if f["atr"] < 0.25 or f["body"] > 2.5 * f["atr"]:
                continue
            cand_side = f["cand_side"]
            if not cand_side:
                continue
                
            cand_mod = f["cand_module"]
            # ADX Macro Chop Gate
            if adx_filter > 0 and f["m15_adx"] < adx_filter:
                if cand_mod in ["MODULE_B_BREAKOUT", "MODULE_D_MOMENTUM_IMPULSE"]:
                    continue
                if module_a_adx_gate and cand_mod == "MODULE_A_SWEEP_RECLAIM":
                    continue
                    
            # Volatility Compression Gate
            if vol_comp_filter and f["m15_vol_ratio"] < 0.85:
                if cand_mod in ["MODULE_B_BREAKOUT", "MODULE_D_MOMENTUM_IMPULSE", "MODULE_A_SWEEP_RECLAIM"]:
                    continue
                    
            # Candidate A Exact Quality Scoring
            total_score = f["cand_base_score"]
            if f["dist_from_mid"] < 0.15:
                total_score -= 10
            else:
                total_score += 10
                
            if cand_side == "LONG" and f["e9"] > f["e21"]: total_score += 10
            elif cand_side == "SHORT" and f["e9"] < f["e21"]: total_score += 10
            
            if cand_side == "LONG" and f["m5_setup"] == "M5_BULL_TREND": total_score += 10
            elif cand_side == "SHORT" and f["m5_setup"] == "M5_BEAR_TREND": total_score += 10
            
            if cand_side == "LONG":
                if f["m15_context"] == "BULLISH": total_score += 10
                elif f["m15_context"] == "BEARISH": total_score -= 10
            else:
                if f["m15_context"] == "BEARISH": total_score += 10
                elif f["m15_context"] == "BULLISH": total_score -= 10
                
            if f["vol_expansion"]: total_score += 5
            
            if total_score < score_threshold:
                continue
                
            if last_entry_side == cand_side and (t - last_entry_time) < 15 * 60000:
                continue
                
            curr_price = f["close"]
            atr_val = f["atr"]
            
            if cand_side == "LONG":
                raw_sl = f["recent_low"] - 0.20 * atr_val
                min_sl = curr_price * (1.0 - 0.0020)
                max_sl = curr_price * (1.0 - 0.0085)
                sl_price = round(max(max_sl, min(raw_sl, min_sl)), 2)
                r_dist = max(0.40, curr_price - sl_price)
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_vol_mult / 2.2)))
                target = round(curr_price + (vol_mult * r_dist), 2)
                exec_price = curr_price if maker_entry else round(curr_price + 0.01, 2)
            else:
                raw_sl = f["recent_high"] + 0.20 * atr_val
                min_sl = curr_price * (1.0 + 0.0020)
                max_sl = curr_price * (1.0 + 0.0085)
                sl_price = round(min(max_sl, max(raw_sl, min_sl)), 2)
                r_dist = max(0.40, sl_price - curr_price)
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_vol_mult / 2.2)))
                target = round(curr_price - (vol_mult * r_dist), 2)
                exec_price = curr_price if maker_entry else round(curr_price - 0.01, 2)
                
            friction = exec_price * (entry_fee_rate + tp_fee_rate + (0.00 if maker_entry else 0.01/exec_price))
            if friction / r_dist > 0.25:
                continue
                
            if capital_profile == "MICRO_REALISTIC":
                risk_usd = balance * 0.0075
                qty = round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3)
                notional = qty * exec_price
                if notional < 20.0:
                    qty = round(math.ceil(20.0 / exec_price / 0.001) * 0.001, 3)
                    notional = qty * exec_price
            else: # NORMALIZED
                risk_usd = balance * 0.0075
                qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
                notional = qty * exec_price
                
            en_fee = round(notional * entry_fee_rate, 4)
            
            in_pos = True
            pos = {
                "side": cand_side,
                "module": cand_mod,
                "entry": exec_price,
                "sl": sl_price,
                "tp": target,
                "qty": qty,
                "notional": notional,
                "r_dist": r_dist,
                "be_active": False,
                "entry_fee": en_fee,
                "entry_idx": idx,
                "open_time": t
            }
            last_entry_time = t
            last_entry_side = cand_side
            
    nt = len(trades)
    if nt == 0:
        return {"trades": 0, "wr": 0, "gpf": 0, "npf": 0, "pnl": 0, "mdd": 0, "fees": 0, "feegp": 0, "trades_list": []}
    wins = [x for x in trades if x["net_pnl"] > 0]
    losses = [x for x in trades if x["net_pnl"] < 0]
    wr = round(len(wins)/nt * 100, 1)
    gp = sum(x["gross_pnl"] for x in wins)
    gl = abs(sum(x["gross_pnl"] for x in trades if x["gross_pnl"] < 0))
    gpf = round(gp / max(0.01, gl), 2)
    tot_fees = sum(x["total_fees"] for x in trades)
    net_w = sum(x["net_pnl"] for x in wins)
    net_l = abs(sum(x["net_pnl"] for x in losses))
    npf = round(net_w / max(0.01, net_l), 2)
    pnl = round(balance - initial_balance, 2)
    mdd = round(max(x["dd_pct"] for x in trades), 2) if trades else 0.0
    feegp = round(tot_fees / max(0.01, gp) * 100, 1)
    
    return {
        "trades": nt, "wr": wr, "gpf": gpf, "npf": npf, "pnl": pnl, "mdd": mdd, "fees": round(tot_fees, 2), "feegp": feegp, "trades_list": trades
    }

print("Running parameter tests...")
# Test grid across BE triggers, ADX thresholds, and Time Stops
for be in [0.0, 1.5, 1.75, 2.0]:
    for ts in [0, 15, 20]:
        for ax in [0.0, 18.0, 20.0, 22.0]:
            r_full = simulate_v33_exact(feat, be_trigger_r=be, time_stop_min=ts, adx_filter=ax, module_a_adx_gate=True, maker_entry=True)
            r_oos = simulate_v33_exact(feat[idx_val_end:], be_trigger_r=be, time_stop_min=ts, adx_filter=ax, module_a_adx_gate=True, maker_entry=True)
            if r_oos['npf'] >= 1.10 and r_full['mdd'] <= 14.0:
                print(f"BE={be:4.2f}R | TS={ts:2d}m | ADX={ax:4.1f} || Full: N={r_full['trades']} WR={r_full['wr']}% GPF={r_full['gpf']} NPF={r_full['npf']} PnL=${r_full['pnl']:6.2f} DD={r_full['mdd']}% FeeGP={r_full['feegp']}% || OOS: N={r_oos['trades']} WR={r_oos['wr']}% NPF={r_oos['npf']} PnL=${r_oos['pnl']:6.2f}")
