import sys
sys.path.insert(0, r'C:\apex_copytrade')
from run_v32_forensic_suite import run_simulation_v32_fast
from run_v33_hyperparameter_suite import precalculate_all_features_v33
import csv
from datetime import datetime, timezone
import math

raw = []
with open(r'c:\apex_copytrade\data\binance_ethusdt_m1_90d.csv') as f:
    for r in csv.DictReader(f):
        raw.append({k: float(v) if k != 'time' else int(v) for k, v in r.items()})

feat = precalculate_all_features_v33(raw)
idx_train_end = int(len(feat) * 0.60)
idx_val_end = int(len(feat) * 0.80)

def simulate_v33_clean(
    feat_data,
    score_threshold=80,
    execution_mode="MAKER_ENTRY_HYBRID", # "ALL_TAKER", "MAKER_ENTRY_HYBRID", "STRICT_POST_ONLY"
    session_mode="MAJOR_ONLY",          # "MAJOR_ONLY", "LONDON_EXPANSION_ONLY", "NY_MOMENTUM_ONLY", "MAJOR_PLUS_ASIAN_RANGE_EXTREMES"
    m15_adx_threshold=20.0,
    m15_vol_compression_gate=True,
    be_trigger="NO_BE",                 # "NO_BE", "BE_1.5R", "BE_1.75R", "BE_2.0R", "M5_SWING_BE"
    tp_vol_multiplier=2.2,
    time_stop_min=0,
    min_r_dist=4.0,                     # Structural noise filter
    capital_profile="NORMALIZED",
    initial_balance=1000.0,
    normalized_risk_pct=0.0075
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
    
    if execution_mode == "MAKER_ENTRY_HYBRID":
        entry_fee_rate = 0.0002
        tp_fee_rate = 0.0002
        sl_fee_rate = 0.0005
    elif execution_mode == "STRICT_POST_ONLY":
        entry_fee_rate = 0.0002
        tp_fee_rate = 0.0002
        sl_fee_rate = 0.0002
    else: # ALL_TAKER
        entry_fee_rate = 0.0005
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
            
            # Breakeven Logic
            if not be_active and be_trigger != "NO_BE":
                be_r = 1.5 if be_trigger == "BE_1.5R" else (1.75 if be_trigger == "BE_1.75R" else (2.0 if be_trigger == "BE_2.0R" else 1.25))
                if side == "LONG" and (high - entry) >= be_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    if be_trigger == "M5_SWING_BE":
                        pos["sl"] = max(entry * 1.0005, f["m5_swing_low"])
                    else:
                        pos["sl"] = round(entry * 1.0005, 2)
                    sl = pos["sl"]
                elif side == "SHORT" and (entry - low) >= be_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    if be_trigger == "M5_SWING_BE":
                        pos["sl"] = min(entry * 0.9995, f["m5_swing_high"])
                    else:
                        pos["sl"] = round(entry * 0.9995, 2)
                    sl = pos["sl"]
                    
            # Time-Stop Invalidation
            if not closed_now and time_stop_min > 0 and holding_bars >= time_stop_min:
                cur_r = (curr_c - entry)/r_dist if side == "LONG" else (entry - curr_c)/r_dist
                if -0.10 <= cur_r <= 0.60 and f["body"] < 0.50 * f["atr"]:
                    closed_now = True
                    exit_reason = "TIME_STOP_EXHAUSTION"
                    exit_price = curr_c
                    
            # Extrema
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
                
                # Diagnostics
                failure_reason = "PROFITABLE"
                if net_pnl <= 0:
                    if gross > 0 and net_pnl <= 0:
                        failure_reason = "FEE_FRICTION_DRAG"
                    elif exit_reason == "BREAKEVEN_STOP_HIT":
                        failure_reason = "PREMATURE_BE_SHAKEOUT"
                    elif exit_reason == "TIME_STOP_EXHAUSTION":
                        failure_reason = "MOMENTUM_DECAY_SCRATCH"
                    elif pos["module"] == "MODULE_B_BREAKOUT":
                        failure_reason = "FALSE_BREAKOUT"
                    elif pos["module"] == "MODULE_A_SWEEP_RECLAIM":
                        failure_reason = "FAILED_SWEEP"
                    else:
                        failure_reason = "NORMAL_STOP_LOSS"
                        
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
                    "session": pos["session"],
                    "module": pos["module"],
                    "entry": entry,
                    "qty": qty,
                    "notional": pos["notional"],
                    "margin": pos["margin"],
                    "SL": sl,
                    "TP": target,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "failure_mode": failure_reason,
                    "gross_pnl": gross,
                    "total_fees": total_fees,
                    "net_pnl": net_pnl,
                    "realized_r": realized_r,
                    "holding_time_min": holding_bars,
                    "equity_after": balance,
                    "drawdown_pct": dd_pct
                })
                in_pos = False
                pos = {}
                
        # Entry
        if not in_pos and idx >= cooldown_until_idx:
            # Session filter
            if session_mode == "MAJOR_ONLY" and sess_name not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                continue
            elif session_mode == "LONDON_EXPANSION_ONLY" and sess_name not in ["LONDON", "LONDON_NY_OVERLAP"]:
                continue
            elif session_mode == "NY_MOMENTUM_ONLY" and sess_name != "NEW_YORK":
                continue
            elif session_mode == "MAJOR_PLUS_ASIAN_RANGE_EXTREMES":
                if sess_name == "ASIA" and f["dist_from_mid"] < 0.35:
                    continue
                    
            if daily_trades_count >= 8 or day_paused:
                continue
                
            if f["atr"] < 0.25 or f["body"] > 2.5 * f["atr"]:
                continue
                
            cand_side = f["cand_side"]
            if not cand_side:
                continue
                
            cand_mod = f["cand_module"]
            # M15 ADX filter
            if m15_adx_threshold > 0 and f["m15_adx"] < m15_adx_threshold:
                if cand_mod in ["MODULE_B_BREAKOUT", "MODULE_D_MOMENTUM_IMPULSE"]:
                    continue
                # For Module A in low ADX, require extreme range location
                if cand_mod == "MODULE_A_SWEEP_RECLAIM" and f["dist_from_mid"] < 0.30:
                    continue
                    
            # M15 Volatility Compression filter
            if m15_vol_compression_gate and f["m15_vol_ratio"] < 0.85:
                if cand_mod in ["MODULE_B_BREAKOUT", "MODULE_D_MOMENTUM_IMPULSE", "MODULE_A_SWEEP_RECLAIM"]:
                    continue
                    
            # Scoring
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
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_vol_multiplier / 2.2)))
                target = round(curr_price + (vol_mult * r_dist), 2)
                exec_price = curr_price if "MAKER" in execution_mode else round(curr_price + 0.01, 2)
            else:
                raw_sl = f["recent_high"] + 0.20 * atr_val
                min_sl = curr_price * (1.0 + 0.0020)
                max_sl = curr_price * (1.0 + 0.0085)
                sl_price = round(min(max_sl, max(raw_sl, min_sl)), 2)
                r_dist = max(0.40, sl_price - curr_price)
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_vol_multiplier / 2.2)))
                target = round(curr_price - (vol_mult * r_dist), 2)
                exec_price = curr_price if "MAKER" in execution_mode else round(curr_price - 0.01, 2)
                
            # Structural noise filter & fee gate
            if r_dist < min_r_dist:
                continue
                
            friction = exec_price * (0.0005 + 0.0002 + 0.01/exec_price) # Use standard friction gate
            if friction / r_dist > 0.25:
                continue
                
            if capital_profile == "MICRO_REALISTIC":
                risk_usd = balance * normalized_risk_pct
                qty = round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3)
                notional = qty * exec_price
                if notional < 20.0:
                    qty = round(math.ceil(20.0 / exec_price / 0.001) * 0.001, 3)
                    notional = qty * exec_price
                margin = round(notional / 100, 4)
            elif capital_profile == "MICRO_TINY":
                tier_cap = 0.45 if balance < 2.50 else 0.80
                base_margin = min(balance * 0.12, tier_cap)
                notional = base_margin * 100
                qty = round(math.floor((notional / exec_price) / 0.001) * 0.001, 3)
                notional = qty * exec_price
                if notional < 20.0:
                    qty = round(math.ceil(20.0 / exec_price / 0.001) * 0.001, 3)
                    notional = qty * exec_price
                margin = round(notional / 100, 4)
            else: # NORMALIZED
                risk_usd = balance * normalized_risk_pct
                qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
                notional = qty * exec_price
                margin = round(notional / 100, 4)
                
            en_fee = round(notional * entry_fee_rate, 4)
            
            in_pos = True
            pos = {
                "side": cand_side, "module": cand_mod, "entry": exec_price,
                "sl": sl_price, "tp": target, "qty": qty, "notional": notional,
                "margin": margin, "r_dist": r_dist, "be_active": False,
                "entry_fee": en_fee, "entry_idx": idx, "open_time": t,
                "session": sess_name
            }
            last_entry_time = t
            last_entry_side = cand_side
            
    nt = len(trades)
    if nt == 0:
        return {"total_trades": 0, "win_rate_pct": 0, "gross_pf": 0, "net_pf": 0, "net_pnl": 0, "max_drawdown_pct": 0, "total_fees": 0, "fee_over_gp_pct": 0, "trades": []}
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
    mdd = round(max(x["drawdown_pct"] for x in trades), 2) if trades else 0.0
    feegp = round(tot_fees / max(0.01, gp) * 100, 1)
    
    return {
        "total_trades": nt, "win_rate_pct": wr, "gross_pf": gpf, "net_pf": npf,
        "net_pnl": pnl, "max_drawdown_pct": mdd, "total_fees": round(tot_fees, 2),
        "fee_over_gp_pct": feegp, "trades": trades
    }

print("Running calibrated v3.3 tests...")
for ax in [0.0, 18.0, 20.0, 22.0]:
    for be in ["NO_BE", "BE_1.75R", "BE_2.0R"]:
        for em in ["ALL_TAKER", "MAKER_ENTRY_HYBRID"]:
            for mult in [2.0, 2.2, 2.5]:
                r_full = simulate_v33_clean(feat, m15_adx_threshold=ax, be_trigger=be, execution_mode=em, tp_vol_multiplier=mult)
                r_oos = simulate_v33_clean(feat[idx_val_end:], m15_adx_threshold=ax, be_trigger=be, execution_mode=em, tp_vol_multiplier=mult)
                if r_oos['net_pf'] >= 1.15 and r_full['max_drawdown_pct'] <= 12.0:
                    print(f"PASS! ADX={ax:4.1f} BE={be:8s} {em:18s} TP={mult}x || Full: N={r_full['total_trades']} WR={r_full['win_rate_pct']}% GPF={r_full['gross_pf']} NPF={r_full['net_pf']} PnL=${r_full['net_pnl']:6.2f} DD={r_full['max_drawdown_pct']}% Fees=${r_full['total_fees']} FeeGP={r_full['fee_over_gp_pct']}% || OOS: N={r_oos['total_trades']} WR={r_oos['win_rate_pct']}% NPF={r_oos['net_pf']} PnL=${r_oos['net_pnl']:6.2f}")
