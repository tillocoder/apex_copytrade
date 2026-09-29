import sys
sys.path.insert(0, r'C:\apex_copytrade')
import csv
import math
import random
import json
from datetime import datetime, timezone
from run_v33_hyperparameter_suite import precalculate_all_features_v33

DATA_PATH = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"

raw = []
with open(DATA_PATH, "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        raw.append({k: float(v) if k != 'time' else int(v) for k, v in r.items()})

print(f"Loaded {len(raw)} candles. Computing features...")
features = precalculate_all_features_v33(raw)
print("Features computed.")

idx_train_end = int(len(features) * 0.60)
idx_val_end = int(len(features) * 0.80)
n_candles = len(features)

def run_production_candidate(feat_slice, capital_profile="NORMALIZED", initial_balance=1000.0):
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
    
    # MAKER_ENTRY_HYBRID
    entry_fee_rate = 0.0002 # 0.02% Maker Post-Only
    tp_fee_rate = 0.0002    # 0.02% Maker Limit TP
    sl_fee_rate = 0.0005    # 0.05% Taker Stop Market
    
    for idx in range(250, len(feat_slice)):
        f = feat_slice[idx]
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
            holding_bars = idx - pos["entry_idx"]
            
            high = f["high"]
            low = f["low"]
            curr_c = f["close"]
            
            closed_now = False
            exit_reason = None
            exit_price = 0.0
            
            if side == "LONG":
                sl_touch = (low <= sl)
                tp_touch = (high >= target)
                if sl_touch and tp_touch:
                    closed_now = True
                    exit_reason = "STOP_LOSS_HIT"
                    exit_price = sl - 0.01
                elif sl_touch:
                    closed_now = True
                    exit_reason = "STOP_LOSS_HIT"
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
                    exit_reason = "STOP_LOSS_HIT"
                    exit_price = sl + 0.01
                elif sl_touch:
                    closed_now = True
                    exit_reason = "STOP_LOSS_HIT"
                    exit_price = sl + 0.01
                elif tp_touch:
                    closed_now = True
                    exit_reason = "TAKE_PROFIT_FULL"
                    exit_price = target
                    
            if closed_now:
                gross = (exit_price - entry)*qty if side == "LONG" else (entry - exit_price)*qty
                gross = round(gross, 4)
                
                entry_fee = pos["entry_fee"]
                if exit_reason == "TAKE_PROFIT_FULL":
                    exit_fee = round(qty * exit_price * tp_fee_rate, 4)
                else:
                    exit_fee = round(qty * exit_price * sl_fee_rate, 4)
                    
                total_fees = round(entry_fee + exit_fee, 4)
                net_pnl = round(gross - total_fees, 4)
                dollar_risk = max(0.01, qty * r_dist)
                realized_r = round(net_pnl / dollar_risk, 2)
                
                failure_reason = "PROFITABLE"
                if net_pnl <= 0:
                    if gross > 0 and net_pnl <= 0:
                        failure_reason = "FEE_FRICTION_DRAG"
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
            # LONDON_EXPANSION_ONLY (08:00 - 16:30 UTC: London & London/NY Overlap)
            if sess_name not in ["LONDON", "LONDON_NY_OVERLAP"]:
                continue
                
            if daily_trades_count >= 8 or day_paused:
                continue
            if f["atr"] < 0.25 or f["body"] > 2.5 * f["atr"]:
                continue
                
            cand_side = f["cand_side"]
            if not cand_side:
                continue
                
            cand_mod = f["cand_module"]
            # Primary Alpha Engine: Module E (M5 Trend Structure + M1 Trigger)
            if cand_mod != "MODULE_E_M5_M1_HYBRID":
                continue
                
            # M15 Macro Regime Gate (ADX >= 18)
            if f["m15_adx"] < 18.0:
                continue
                
            # M15 Volatility Compression Gate (ATR >= 85% of EMA50)
            if f["m15_vol_ratio"] < 0.85:
                continue
                
            # Quality Scoring
            total_score = f["cand_base_score"] # 35
            if f["dist_from_mid"] < 0.15:
                total_score -= 10
            else:
                total_score += 10 # 45
                
            if cand_side == "LONG" and f["e9"] > f["e21"]: total_score += 10 # 55
            elif cand_side == "SHORT" and f["e9"] < f["e21"]: total_score += 10
            
            if cand_side == "LONG" and f["m5_setup"] == "M5_BULL_TREND": total_score += 10 # 65
            elif cand_side == "SHORT" and f["m5_setup"] == "M5_BEAR_TREND": total_score += 10
            
            if cand_side == "LONG":
                if f["m15_context"] == "BULLISH": total_score += 10 # 75
                elif f["m15_context"] == "BEARISH": total_score -= 10
            else:
                if f["m15_context"] == "BEARISH": total_score += 10
                elif f["m15_context"] == "BULLISH": total_score -= 10
                
            if f["vol_expansion"]: total_score += 5 # 80
            
            if total_score < 80:
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
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (2.2 / 2.2))) # 2.2x target
                target = round(curr_price + (vol_mult * r_dist), 2)
                exec_price = curr_price # Maker limit entry at close
            else:
                raw_sl = f["recent_high"] + 0.20 * atr_val
                min_sl = curr_price * (1.0 + 0.0020)
                max_sl = curr_price * (1.0 + 0.0085)
                sl_price = round(min(max_sl, max(raw_sl, min_sl)), 2)
                r_dist = max(0.40, sl_price - curr_price)
                
                vol_mult = max(1.5, min(3.0, (atr_val / 1.0) * (2.2 / 2.2)))
                target = round(curr_price - (vol_mult * r_dist), 2)
                exec_price = curr_price
                
            if r_dist < 4.0:
                continue
            friction = exec_price * (0.0005 + 0.0002 + 0.01/exec_price)
            if friction / r_dist > 0.25:
                continue
                
            if capital_profile == "MICRO_REALISTIC":
                risk_usd = balance * 0.0075
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
                risk_usd = balance * 0.0075
                qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
                notional = qty * exec_price
                margin = round(notional / 100, 4)
                
            en_fee = round(notional * entry_fee_rate, 4)
            
            in_pos = True
            pos = {
                "side": cand_side, "module": cand_mod, "entry": exec_price,
                "sl": sl_price, "tp": target, "qty": qty, "notional": notional,
                "margin": margin, "r_dist": r_dist, "entry_fee": en_fee,
                "entry_idx": idx, "open_time": t, "session": sess_name
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
    avg_r = round(sum(x["realized_r"] for x in trades) / nt, 2)
    exp = round(pnl / nt, 2)
    
    # Payoff ratio
    avg_win = sum(x["net_pnl"] for x in wins) / max(1, len(wins))
    avg_loss = abs(sum(x["net_pnl"] for x in losses)) / max(1, len(losses))
    payoff = round(avg_win / max(0.01, avg_loss), 2)
    
    return {
        "total_trades": nt, "trades_per_day": round(nt / (len(feat_slice)/1440.0), 2),
        "win_rate_pct": wr, "gross_pf": gpf, "net_pf": npf, "payoff_ratio": payoff,
        "net_pnl": pnl, "max_drawdown_pct": mdd, "total_fees": round(tot_fees, 2),
        "fee_over_gp_pct": feegp, "average_r": avg_r, "expectancy": exp,
        "ending_balance": balance, "trades": trades
    }

print("\n" + "=" * 80)
print("   APEX QUANT v3.3 PRODUCTION CANDIDATE — MASTER AUDIT")
print("=" * 80)

res_full = run_production_candidate(features)
res_train = run_production_candidate(features[:idx_train_end])
res_val = run_production_candidate(features[idx_train_end:idx_val_end])
res_oos = run_production_candidate(features[idx_val_end:])

res_micro_100 = run_production_candidate(features, capital_profile="MICRO_REALISTIC", initial_balance=100.0)
res_micro_tiny = run_production_candidate(features, capital_profile="MICRO_TINY", initial_balance=2.7109)

print(f"Full Period (90d) : Trades={res_full['total_trades']:3d} ({res_full['trades_per_day']:.2f}/d) | WR={res_full['win_rate_pct']:4.1f}% | Payoff={res_full['payoff_ratio']:4.2f}x | Gross PF={res_full['gross_pf']:4.2f} | Net PF={res_full['net_pf']:4.2f} | Net PnL=${res_full['net_pnl']:7.2f} | Max DD={res_full['max_drawdown_pct']:4.1f}% | Fee Drag={res_full['fee_over_gp_pct']:4.1f}%")
print(f"  Train (60%)     : Trades={res_train['total_trades']:3d} | WR={res_train['win_rate_pct']:4.1f}% | Gross PF={res_train['gross_pf']:4.2f} | Net PF={res_train['net_pf']:4.2f} | Net PnL=${res_train['net_pnl']:7.2f}")
print(f"  Validation (20%): Trades={res_val['total_trades']:3d} | WR={res_val['win_rate_pct']:4.1f}% | Gross PF={res_val['gross_pf']:4.2f} | Net PF={res_val['net_pf']:4.2f} | Net PnL=${res_val['net_pnl']:7.2f}")
print(f"  Out-of-Sample   : Trades={res_oos['total_trades']:3d} | WR={res_oos['win_rate_pct']:4.1f}% | Gross PF={res_oos['gross_pf']:4.2f} | Net PF={res_oos['net_pf']:4.2f} | Net PnL=${res_oos['net_pnl']:7.2f}")
print(f"Micro Realistic   : Trades={res_micro_100['total_trades']:3d} | WR={res_micro_100['win_rate_pct']:4.1f}% | Net PF={res_micro_100['net_pf']:4.2f} | Net PnL=${res_micro_100['net_pnl']:7.2f} | Max DD={res_micro_100['max_drawdown_pct']:4.1f}%")
print(f"Micro Tiny        : Trades={res_micro_tiny['total_trades']:3d} | WR={res_micro_tiny['win_rate_pct']:4.1f}% | Net PnL=${res_micro_tiny['net_pnl']:7.4f} | Max DD={res_micro_tiny['max_drawdown_pct']:4.1f}%")

# Monte Carlo 10,000 runs
print("\nRunning 10,000 Monte Carlo Simulations...")
pnls = [t["net_pnl"] for t in res_full["trades"]]
mc_eq = []
mc_dd = []
profit_cnt = 0
dd10_cnt = 0
dd12_cnt = 0
ruin_cnt = 0

for _ in range(10000):
    sample = [random.choice(pnls) for _ in range(len(pnls))]
    eq = 1000.0
    pk = eq
    mdd = 0.0
    for p in sample:
        eq += p
        if eq > pk: pk = eq
        dd = (pk - eq) / pk * 100.0
        if dd > mdd: mdd = dd
    mc_eq.append(eq)
    mc_dd.append(mdd)
    if eq > 1000.0: profit_cnt += 1
    if mdd >= 10.0: dd10_cnt += 1
    if mdd >= 12.0: dd12_cnt += 1
    if eq <= 200.0: ruin_cnt += 1

mc_eq.sort()
mc_dd.sort()

print(f"Monte Carlo Positive PnL Probability: {profit_cnt / 100:.2f}%")
print(f"Monte Carlo Prob DD > 10%           : {dd10_cnt / 100:.2f}%")
print(f"Monte Carlo Prob DD > 12%           : {dd12_cnt / 100:.2f}%")
print(f"Monte Carlo Prob Ruin (Balance<=200): {ruin_cnt / 100:.2f}%")
print(f"Median Ending Balance               : ${mc_eq[5000]:.2f}")
print(f"5th Percentile Ending Balance       : ${mc_eq[500]:.2f}")
print(f"95th Percentile Ending Balance      : ${mc_eq[9500]:.2f}")
print(f"95th Percentile Max Drawdown        : {mc_dd[9500]:.2f}%")
