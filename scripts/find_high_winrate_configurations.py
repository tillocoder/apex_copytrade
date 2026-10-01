import os
import sys

# Ensure UTF-8 output encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import csv
import json
import time
import math
import multiprocessing
from datetime import datetime, timezone
from typing import Dict, Any, List

DATA_PATH = r"C:\apex_copytrade\data\binance_ethusdt_m1_90d.csv"

# Import precalculated features logic from run_high_winrate_multicore_search
from run_high_winrate_multicore_search import precalculate_features

_GLOBAL_FEAT = None

def init_worker(feat):
    global _GLOBAL_FEAT
    _GLOBAL_FEAT = feat

def simulate_one(params: Dict[str, Any]) -> Dict[str, Any]:
    global _GLOBAL_FEAT
    features = _GLOBAL_FEAT

    module_name = params["module"]          # "MODULE_A", "MODULE_B", "MODULE_C", "MODULE_D", "MODULE_E"
    trend_filter = params["trend_filter"]   # "STRICT_HTF", "M5_M15", "NONE"
    session_mode = params["session_mode"]   # "LONDON_EXPANSION", "MAJOR", "ALL_24H"
    sl_atr_mult = params["sl_atr_mult"]     # 1.5, 2.0, 2.5, 3.0
    min_sl_usd = params["min_sl_usd"]       # 4.0, 6.0, 8.0, 10.0
    tp_r = params["tp_r"]                   # 0.8, 1.0, 1.2, 1.5, 1.8, 2.0
    score_thresh = params["score_thresh"]   # 65, 70, 75, 80
    adx_min = params["adx_min"]             # 0, 18, 22

    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = initial_balance
    trades = []
    
    in_pos = False
    pos = {}
    current_day = ""
    daily_trades = 0
    cooldown_until = 0

    entry_fee_rate = 0.0002 # Maker Post-Only
    tp_fee_rate = 0.0002    # Maker Limit
    sl_fee_rate = 0.0005    # Taker Stop Market

    n = len(features)
    for idx in range(250, n):
        f = features[idx]
        t = f["time"]
        day_str = f["day_str"]
        curr_c = f["close"]
        high = f["high"]
        low = f["low"]

        if day_str != current_day:
            current_day = day_str
            daily_trades = 0

        # --- POSITION MANAGEMENT ---
        if in_pos:
            side = pos["side"]
            entry = pos["entry"]
            sl = pos["sl"]
            target = pos["tp"]
            qty = pos["qty"]
            r_dist = pos["r_dist"]

            closed = False
            exit_p = 0.0
            reason = ""

            if side == "LONG":
                if low <= sl and high >= target:
                    closed = True; exit_p = sl - 0.01; reason = "SL_HIT"
                elif low <= sl:
                    closed = True; exit_p = sl - 0.01; reason = "SL_HIT"
                elif high >= target:
                    closed = True; exit_p = target; reason = "TP_HIT"
            else: # SHORT
                if high >= sl and low <= target:
                    closed = True; exit_p = sl + 0.01; reason = "SL_HIT"
                elif high >= sl:
                    closed = True; exit_p = sl + 0.01; reason = "SL_HIT"
                elif low <= target:
                    closed = True; exit_p = target; reason = "TP_HIT"

            if closed:
                gross_pnl = (exit_p - entry) * qty if side == "LONG" else (entry - exit_p) * qty
                f_rate = tp_fee_rate if reason == "TP_HIT" else sl_fee_rate
                exit_fee = qty * exit_p * f_rate
                net_trade_pnl = gross_pnl - pos["entry_fee"] - exit_fee

                balance = round(balance + net_trade_pnl, 4)
                peak_balance = max(peak_balance, balance)
                dd_pct = round(((peak_balance - balance) / peak_balance) * 100.0, 2)
                
                daily_trades += 1
                cooldown_until = idx + 10

                trades.append({
                    "is_win": net_trade_pnl > 0,
                    "net_pnl": net_trade_pnl,
                    "reason": reason,
                    "dd_pct": dd_pct
                })

                in_pos = False
                pos = {}

        # --- ENTRY SCAN ---
        if not in_pos and idx >= cooldown_until and daily_trades < 8:
            # Session filter
            if session_mode == "LONDON_EXPANSION" and f["session"] not in ["LONDON", "LONDON_NY_OVERLAP"]:
                continue
            elif session_mode == "MAJOR" and f["session"] not in ["LONDON", "LONDON_NY_OVERLAP", "NEW_YORK"]:
                continue

            if adx_min > 0 and f["m15_adx"] < adx_min:
                continue

            if f["atr"] < 0.25 or f["body"] > 2.5 * f["atr"]:
                continue

            # Find candidate matching module_name
            cand_signal = None
            cand_score = 0
            for side_c, mod_c, base_sc in f["module_candidates"]:
                if module_name != "ALL" and mod_c != module_name:
                    continue

                # Trend Filter
                if trend_filter == "STRICT_HTF":
                    if side_c == "LONG" and (f["m15_context"] == "BEARISH" or curr_c < f["e200"]): continue
                    if side_c == "SHORT" and (f["m15_context"] == "BULLISH" or curr_c > f["e200"]): continue
                elif trend_filter == "M5_M15":
                    if side_c == "LONG" and (f["m15_context"] == "BEARISH" or f["m5_setup"] == "M5_BEAR_TREND"): continue
                    if side_c == "SHORT" and (f["m15_context"] == "BULLISH" or f["m5_setup"] == "M5_BULL_TREND"): continue

                # Scoring
                score = base_sc
                if f["dist_from_mid"] >= 0.15: score += 10
                else: score -= 10

                if side_c == "LONG" and f["e9"] > f["e21"]: score += 15
                elif side_c == "SHORT" and f["e9"] < f["e21"]: score += 15

                if side_c == "LONG" and f["m5_setup"] == "M5_BULL_TREND": score += 15
                elif side_c == "SHORT" and f["m5_setup"] == "M5_BEAR_TREND": score += 15

                if side_c == "LONG":
                    if f["m15_context"] == "BULLISH": score += 15
                    elif f["m15_context"] == "BEARISH": score -= 15
                else:
                    if f["m15_context"] == "BEARISH": score += 15
                    elif f["m15_context"] == "BULLISH": score -= 15

                if f["vol_expansion"]: score += 10

                if score >= score_thresh and score > cand_score:
                    cand_score = score
                    cand_signal = side_c

            if not cand_signal:
                continue

            # Geometry
            atr_v = f["atr"]
            raw_sl_dist = sl_atr_mult * atr_v
            r_dist = max(min_sl_usd, min(curr_c * 0.015, raw_sl_dist))
            sl_price = round(curr_c - r_dist, 2) if cand_signal == "LONG" else round(curr_c + r_dist, 2)
            tp_price = round(curr_c + (tp_r * r_dist), 2) if cand_signal == "LONG" else round(curr_c - (tp_r * r_dist), 2)

            risk_usd = balance * 0.010
            qty = max(0.005, round(math.floor((risk_usd / r_dist) / 0.001) * 0.001, 3))
            entry_fee = round(qty * curr_c * entry_fee_rate, 4)

            in_pos = True
            pos = {
                "side": cand_signal,
                "entry": curr_c,
                "sl": sl_price,
                "tp": tp_price,
                "qty": qty,
                "r_dist": r_dist,
                "entry_fee": entry_fee
            }

    total_trades = len(trades)
    if total_trades < 10:
        return {"total_trades": total_trades, "win_rate_pct": 0.0, "net_pf": 0.0, "net_pnl": 0.0, "params": params}

    wins = [t for t in trades if t["is_win"]]
    losses = [t for t in trades if not t["is_win"]]
    wr = round((len(wins) / total_trades) * 100.0, 1)
    
    gp = sum(t["net_pnl"] for t in wins)
    gl = abs(sum(t["net_pnl"] for t in losses))
    pf = round((gp / gl) if gl > 0 else 99.0, 2)
    net_pnl = round(sum(t["net_pnl"] for t in trades), 2)
    max_dd = round(max((t["dd_pct"] for t in trades), default=0.0), 2)

    # OOS validation (last 33% of trades)
    split_idx = int(total_trades * 0.67)
    oos_trades = trades[split_idx:]
    oos_wins = [t for t in oos_trades if t["is_win"]]
    oos_wr = round((len(oos_wins) / max(1, len(oos_trades))) * 100.0, 1)
    oos_gp = sum(t["net_pnl"] for t in oos_wins)
    oos_gl = abs(sum(t["net_pnl"] for t in oos_trades if not t["is_win"]))
    oos_pf = round((oos_gp / oos_gl) if oos_gl > 0 else 99.0, 2)
    oos_pnl = round(sum(t["net_pnl"] for t in oos_trades), 2)

    return {
        "params": params,
        "total_trades": total_trades,
        "trades_per_day": round(total_trades / 90.0, 2),
        "win_rate_pct": wr,
        "net_pf": pf,
        "net_pnl": net_pnl,
        "max_dd_pct": max_dd,
        "oos_trades": len(oos_trades),
        "oos_win_rate_pct": oos_wr,
        "oos_pf": oos_pf,
        "oos_pnl": oos_pnl
    }

def main():
    cpu_count = os.cpu_count() or 8
    print("=" * 80)
    print(f"🚀 RUNNING TARGETED HIGH-WINRATE SEARCH ACROSS {cpu_count} CORES")
    print("=" * 80)

    # Load data
    with open(DATA_PATH, "r") as f:
        reader = csv.reader(f)
        next(reader)
        raw = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in reader]

    features = precalculate_features(raw)

    # Targeted Grid: testing modules, session modes, SL mults, and TP R ratios
    grid = []
    for mod in ["MODULE_E_M5_M1_HYBRID", "MODULE_A_SWEEP_RECLAIM", "MODULE_B_BREAKOUT", "MODULE_C_EMA_PULLBACK", "MODULE_D_MOMENTUM_IMPULSE", "ALL"]:
        for sess in ["LONDON_EXPANSION", "MAJOR", "ALL_24H"]:
            for tf in ["STRICT_HTF", "M5_M15"]:
                for sl_v in [1.5, 2.0, 2.5, 3.0]:
                    for min_sl in [4.0, 6.0, 8.0]:
                        for tp_r in [0.8, 1.0, 1.2, 1.4, 1.6, 2.0]:
                            for sc in [70, 75, 80]:
                                for adx in [0, 18, 22]:
                                    grid.append({
                                        "module": mod,
                                        "session_mode": sess,
                                        "trend_filter": tf,
                                        "sl_atr_mult": sl_v,
                                        "min_sl_usd": min_sl,
                                        "tp_r": tp_r,
                                        "score_thresh": sc,
                                        "adx_min": adx
                                    })

    total = len(grid)
    print(f"Testing {total:,} configurations...")

    t0 = time.time()
    results = []
    with multiprocessing.Pool(processes=cpu_count, initializer=init_worker, initargs=(features,)) as pool:
        for res in pool.imap_unordered(simulate_one, grid, chunksize=50):
            if res.get("total_trades", 0) >= 15:
                results.append(res)

    print(f"Completed in {time.time()-t0:.2f}s! Total qualifying: {len(results):,}")

    # Sort by Win Rate (with PF >= 1.10 and positive Net PnL)
    profitable = [r for r in results if r["net_pf"] >= 1.10 and r["net_pnl"] > 0 and r["oos_pf"] >= 1.05 and r["total_trades"] >= 25]
    profitable.sort(key=lambda x: (x["win_rate_pct"], x["net_pf"]), reverse=True)

    print("\n" + "=" * 90)
    print("🏆 TOP 15 HIGHEST WIN-RATE PROFITABLE MODELS (PROFIT FACTOR >= 1.10 & POSITIVE OOS):")
    print(f"{'Rank':<4} | {'WinRate':<7} | {'Net PF':<6} | {'Trades':<6} | {'PnL':<8} | {'MaxDD':<6} | {'OOS WR':<7} | {'OOS PF':<6} | Setup")
    print("-" * 105)

    for idx, r in enumerate(profitable[:15]):
        p = r["params"]
        setup = f"{p['module']} | {p['session_mode']} | {p['trend_filter']} | SL x{p['sl_atr_mult']} (min ${p['min_sl_usd']}) | TP {p['tp_r']}R | Score>={p['score_thresh']}"
        print(f"#{idx+1:<3} | {r['win_rate_pct']:>5.1f}% | {r['net_pf']:>5.2f}x | {r['total_trades']:>5}t | ${r['net_pnl']:>6.2f} | {r['max_dd_pct']:>5.1f}% | {r['oos_win_rate_pct']:>5.1f}% | {r['oos_pf']:>5.2f}x | {setup}")

    # Save to JSON
    with open(r"C:\apex_copytrade\data\targeted_high_winrate_results.json", "w", encoding="utf-8") as f:
        json.dump({"total_tested": total, "profitable_count": len(profitable), "top_15": profitable[:15]}, f, indent=2)

if __name__ == "__main__":
    main()
