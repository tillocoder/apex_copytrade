import sys
sys.path.insert(0, r'C:\apex_copytrade')
from run_v32_forensic_suite import precalculate_all_features
import csv
import math

raw = []
with open(r'c:\apex_copytrade\data\binance_ethusdt_m1_90d.csv') as f:
    for r in csv.DictReader(f):
        raw.append({k: float(v) if k != 'time' else int(v) for k, v in r.items()})

print(f"Loaded {len(raw)} candles.")
features = precalculate_all_features(raw)

# Let's inspect the M15 ADX and Vol ratio distribution
from run_v33_hyperparameter_suite import precalculate_all_features_v33
feat_v33 = precalculate_all_features_v33(raw)
print("Features v33 ready.")

idx_val = int(len(feat_v33) * 0.8)

# Let's test a simulation function that exactly matches Candidate A's base scoring and gates,
# but adds the v3.3 enhancements: Maker entry, ADX filter, Vol compression, BE triggers, Time stop, TP mult.
def sim_test(feat_data, score_th=80, exec_mode="MAKER_HYBRID", adx_th=20.0, vol_comp=True, be_mode="BE_2.0R", tp_mult=2.2, time_stop=15):
    balance = 1000.0
    peak = balance
    trades = []
    in_pos = False
    pos = {}
    pending_maker = None
    
    cooldown_until = 0
    last_entry_time = 0
    last_entry_side = None
    current_day = ""
    daily_trades = 0
    daily_pnl = 0.0
    day_paused = False
    
    entry_fee_rate = 0.0002 if "MAKER" in exec_mode else 0.0005
    tp_fee_rate = 0.0002
    sl_fee_rate = 0.0002 if exec_mode == "STRICT_POST_ONLY" else 0.0005
    
    for i in range(250, len(feat_data)):
        f = feat_data[i]
        t = f["time"]
        day_str = f["day_str"]
        sess = f["session"]
        
        if day_str != current_day:
            current_day = day_str
            daily_trades = 0
            daily_pnl = 0.0
            day_paused = False
            
        # Maker fill check
        if pending_maker is not None and not in_pos:
            pside = pending_maker["side"]
            plim = pending_maker["limit"]
            pwait = i - pending_maker["idx"]
            
            filled = False
            if pside == "LONG" and f["low"] <= plim - 0.01:
                filled = True
            elif pside == "SHORT" and f["high"] >= plim + 0.01:
                filled = True
                
            if filled:
                in_pos = True
                pos = pending_maker["pos"]
                pos["entry_idx"] = i
                last_entry_time = t
                last_entry_side = pside
                pending_maker = None
            elif pwait >= 2:
                pending_maker = None
                
        # Active position management
        if in_pos:
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            target = pos["tp"]
            qty = pos["qty"]
            r_dist = pos["r_dist"]
            be_active = pos["be_active"]
            holding = i - pos["entry_idx"]
            
            high = f["high"]
            low = f["low"]
            curr_c = f["close"]
            
            closed = False
            exit_reason = ""
            exit_price = 0.0
            
            # BE activation
            if not be_active:
                be_r = 2.0 if be_mode == "BE_2.0R" else (1.75 if be_mode == "BE_1.75R" else (1.5 if be_mode == "BE_1.5R" else 1.25))
                if side == "LONG" and (high - entry) >= be_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    if be_mode == "M5_SWING_BE":
                        pos["sl"] = max(entry * 1.0005, f["m5_swing_low"])
                    elif be_mode != "NO_BE":
                        pos["sl"] = round(entry * 1.0005, 2)
                    sl = pos["sl"]
                elif side == "SHORT" and (entry - low) >= be_r * r_dist:
                    pos["be_active"] = True
                    be_active = True
                    if be_mode == "M5_SWING_BE":
                        pos["sl"] = min(entry * 0.9995, f["m5_swing_high"])
                    elif be_mode != "NO_BE":
                        pos["sl"] = round(entry * 0.9995, 2)
                    sl = pos["sl"]
                    
            # Time stop
            if not closed and time_stop > 0 and holding >= time_stop:
                cur_r = (curr_c - entry)/r_dist if side == "LONG" else (entry - curr_c)/r_dist
                if -0.1 <= cur_r < 0.8 and f["body"] < 0.6 * f["atr"]:
                    closed = True
                    exit_reason = "TIME_STOP"
                    exit_price = curr_c
                    
            if not closed:
                if side == "LONG":
                    sl_touch = (low <= sl)
                    tp_touch = (high >= target)
                    if sl_touch and tp_touch:
                        closed = True
                        exit_reason = "SL" if not be_active else "BE"
                        exit_price = sl - 0.01
                    elif sl_touch:
                        closed = True
                        exit_reason = "SL" if not be_active else "BE"
                        exit_price = sl - 0.01
                    elif tp_touch:
                        closed = True
                        exit_reason = "TP"
                        exit_price = target
                else:
                    sl_touch = (high >= sl)
                    tp_touch = (low <= target)
                    if sl_touch and tp_touch:
                        closed = True
                        exit_reason = "SL" if not be_active else "BE"
                        exit_price = sl + 0.01
                    elif sl_touch:
                        closed = True
                        exit_reason = "SL" if not be_active else "BE"
                        exit_price = sl + 0.01
                    elif tp_touch:
                        closed = True
                        exit_reason = "TP"
                        exit_price = target
                        
            if closed:
                gross = (exit_price - entry)*qty if side == "LONG" else (entry - exit_price)*qty
                en_fee = pos["entry_fee"]
                ex_fee = qty * exit_price * (tp_fee_rate if exit_reason in ["TP", "TIME_STOP"] else sl_fee_rate)
                fees = round(en_fee + ex_fee, 4)
                net = round(gross - fees, 4)
                
                balance += net
                peak = max(peak, balance)
                daily_pnl += net
                daily_trades += 1
                
                if net > 0:
                    cooldown_until = i + 10
                else:
                    cooldown_until = i + 15
                if daily_pnl <= -0.05 * balance:
                    day_paused = True
                    
                trades.append({
                    "side": side, "net_pnl": net, "gross_pnl": gross, "fees": fees,
                    "exit_reason": exit_reason, "holding": holding, "balance": balance,
                    "dd": round((peak - balance)/peak * 100, 2)
                })
                in_pos = False
                pos = {}
                
        # Entry evaluation
        if not in_pos and pending_maker is None and i >= cooldown_until:
            if sess not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                continue
            if daily_trades >= 8 or day_paused:
                continue
            if f["atr"] < 0.25 or f["body"] > 2.5 * f["atr"]:
                continue
            cand_side = f["cand_side"]
            if not cand_side:
                continue
                
            cand_mod = f["cand_module"]
            # M15 ADX gate
            if adx_th > 0 and f["m15_adx"] < adx_th:
                if cand_mod in ["MODULE_B_BREAKOUT", "MODULE_D_MOMENTUM_IMPULSE"]:
                    continue
                elif cand_mod == "MODULE_A_SWEEP_RECLAIM" and f["dist_from_mid"] < 0.25:
                    continue
                    
            # M15 Vol Compression gate
            if vol_comp and f["m15_vol_ratio"] < 0.85:
                if cand_mod in ["MODULE_B_BREAKOUT", "MODULE_D_MOMENTUM_IMPULSE"]:
                    continue
                    
            # Exact Candidate A scoring logic
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
            
            if total_score < score_th:
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
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_mult / 2.2)))
                target = round(curr_price + vol_mult * r_dist, 2)
                exec_price = curr_price if "MAKER" in exec_mode else round(curr_price + 0.01, 2)
            else:
                raw_sl = f["recent_high"] + 0.20 * atr_val
                min_sl = curr_price * (1.0 + 0.0020)
                max_sl = curr_price * (1.0 + 0.0085)
                sl_price = round(min(max_sl, max(raw_sl, min_sl)), 2)
                r_dist = max(0.40, sl_price - curr_price)
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (tp_mult / 2.2)))
                target = round(curr_price - vol_mult * r_dist, 2)
                exec_price = curr_price if "MAKER" in exec_mode else round(curr_price - 0.01, 2)
                
            cost = exec_price * (entry_fee_rate + tp_fee_rate + 0.01/exec_price)
            if cost / r_dist > 0.25:
                continue
                
            risk_usd = balance * 0.0075
            qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
            notional = qty * exec_price
            en_fee = round(notional * entry_fee_rate, 4)
            
            pos_info = {
                "side": cand_side, "entry": exec_price, "sl": sl_price, "tp": target,
                "qty": qty, "r_dist": r_dist, "be_active": False, "entry_fee": en_fee
            }
            
            if "MAKER" in exec_mode:
                pending_maker = {
                    "side": cand_side, "limit": exec_price, "idx": i, "pos": pos_info
                }
            else:
                in_pos = True
                pos = pos_info
                pos["entry_idx"] = i
                last_entry_time = t
                last_entry_side = cand_side
                
    nt = len(trades)
    if nt == 0:
        return {"trades": 0, "wr": 0, "gpf": 0, "npf": 0, "pnl": 0, "mdd": 0, "fees": 0, "feegp": 0}
    wins = [x for x in trades if x["net_pnl"] > 0]
    losses = [x for x in trades if x["net_pnl"] < 0]
    wr = round(len(wins)/nt * 100, 1)
    gp = sum(x["gross_pnl"] for x in wins)
    gl = abs(sum(x["gross_pnl"] for x in trades if x["gross_pnl"] < 0))
    gpf = round(gp / max(0.01, gl), 2)
    tot_fees = sum(x["fees"] for x in trades)
    net_w = sum(x["net_pnl"] for x in wins)
    net_l = abs(sum(x["net_pnl"] for x in losses))
    npf = round(net_w / max(0.01, net_l), 2)
    pnl = round(balance - 1000.0, 2)
    mdd = round(max(x["dd"] for x in trades), 2) if trades else 0.0
    feegp = round(tot_fees / max(0.01, gp) * 100, 1)
    
    return {
        "trades": nt, "wr": wr, "gpf": gpf, "npf": npf, "pnl": pnl, "mdd": mdd, "fees": round(tot_fees, 2), "feegp": feegp
    }

print("\n--- BASELINE REPRODUCTION (ALL_TAKER, NO ADX, NO BE, NO TIME_STOP) ---")
r_base = sim_test(feat_v33, score_th=80, exec_mode="ALL_TAKER", adx_th=0.0, vol_comp=False, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
print("Base Full:", r_base)
r_base_oos = sim_test(feat_v33[idx_val:], score_th=80, exec_mode="ALL_TAKER", adx_th=0.0, vol_comp=False, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
print("Base OOS:", r_base_oos)

print("\n--- TEST 1: ADD MAKER POST-ONLY ENTRY (0.02% Fee) ---")
r_mkr = sim_test(feat_v33, score_th=80, exec_mode="MAKER_HYBRID", adx_th=0.0, vol_comp=False, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
print("Maker Full:", r_mkr)
r_mkr_oos = sim_test(feat_v33[idx_val:], score_th=80, exec_mode="MAKER_HYBRID", adx_th=0.0, vol_comp=False, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
print("Maker OOS:", r_mkr_oos)

print("\n--- TEST 2: ADD M15 ADX FILTER (18, 20, 22) ---")
for ax in [18.0, 20.0, 22.0]:
    r_adx = sim_test(feat_v33, score_th=80, exec_mode="MAKER_HYBRID", adx_th=ax, vol_comp=False, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
    r_adx_oos = sim_test(feat_v33[idx_val:], score_th=80, exec_mode="MAKER_HYBRID", adx_th=ax, vol_comp=False, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
    print(f"ADX >= {ax:.0f} | Full: NPf={r_adx['npf']}, PnL={r_adx['pnl']}, DD={r_adx['mdd']}%, Trades={r_adx['trades']} | OOS: NPf={r_adx_oos['npf']}, PnL={r_adx_oos['pnl']}, Trades={r_adx_oos['trades']}")

print("\n--- TEST 3: ADD M15 VOLATILITY COMPRESSION GATE ---")
r_vc = sim_test(feat_v33, score_th=80, exec_mode="MAKER_HYBRID", adx_th=20.0, vol_comp=True, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
r_vc_oos = sim_test(feat_v33[idx_val:], score_th=80, exec_mode="MAKER_HYBRID", adx_th=20.0, vol_comp=True, be_mode="NO_BE", tp_mult=2.2, time_stop=0)
print(f"VolComp True | Full: NPf={r_vc['npf']}, PnL={r_vc['pnl']}, DD={r_vc['mdd']}%, Trades={r_vc['trades']} | OOS: NPf={r_vc_oos['npf']}, PnL={r_vc_oos['pnl']}, Trades={r_vc_oos['trades']}")

print("\n--- TEST 4: ADD BREAKEVEN TRIGGER & TIME-STOP ---")
for be in ["NO_BE", "BE_1.5R", "BE_1.75R", "BE_2.0R", "M5_SWING_BE"]:
    for ts in [0, 15, 20]:
        r_comb = sim_test(feat_v33, score_th=80, exec_mode="MAKER_HYBRID", adx_th=20.0, vol_comp=True, be_mode=be, tp_mult=2.2, time_stop=ts)
        r_comb_oos = sim_test(feat_v33[idx_val:], score_th=80, exec_mode="MAKER_HYBRID", adx_th=20.0, vol_comp=True, be_mode=be, tp_mult=2.2, time_stop=ts)
        print(f"{be:12s} TS={ts:2d} | Full: NPf={r_comb['npf']}, PnL={r_comb['pnl']}, DD={r_comb['mdd']}%, FeeGP={r_comb['feegp']}%, WR={r_comb['wr']}% | OOS: NPf={r_comb_oos['npf']}, PnL={r_comb_oos['pnl']}")
