#!/usr/bin/env python3
"""
APEX PROP ENGINE — FORENSIC STRESS TEST SUITE (Scenarios A through N)
"""
import os, sys, json, random, math
from dataclasses import dataclass
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from run_challenge_sim import load_cached_data, make_config, simulate_multi_challenge
from backend.quant_engine.entry import ALLOWED_SYMBOLS

ALLOWED_SYMBOLS.add("SOL/USDT")

def run_stress_sim(trade_logs, cfg, sim_count=300,
                   slippage_mult=1.0, win_rate_delta=0.0, avg_loss_mult=1.0,
                   fee_mult=1.0, trade_drop_pct=0.0, dup_loss_streaks=False,
                   corr_lock=False, worst_trades_added=0):

    initial_cap = 10000.0
    stage1_target = 0.08
    stage2_target = 0.05
    max_daily_limit = 0.05
    max_total_limit = 0.10

    # Extract trades
    base_trades = []
    for t in trade_logs:
        pnl = t["pnl"]
        # Apply fee/slippage multipliers to pnl estimate
        comm = t.get("commission", 1.5) * (fee_mult - 1.0)
        pnl -= comm
        
        # If slippage mult > 1
        if slippage_mult > 1.0:
            extra_slip = (t.get("entry_price", 50000.0) * 0.0001 * (slippage_mult - 1.0)) * t.get("size", 0.05)
            pnl -= extra_slip

        # If avg loss mult > 1 and pnl < 0
        if pnl < 0 and avg_loss_mult > 1.0:
            pnl *= avg_loss_mult

        base_trades.append({
            "pnl": pnl,
            "is_win": pnl > 0,
            "symbol": t.get("symbol", "BTC/USDT")
        })

    # Apply Win Rate shift if required (randomly convert wins to losses)
    if win_rate_delta < 0:
        total_t = len(base_trades)
        wins = [i for i, tr in enumerate(base_trades) if tr["is_win"]]
        num_to_flip = int(abs(win_rate_delta) * total_t)
        num_to_flip = min(len(wins), num_to_flip)
        flip_indices = set(random.sample(wins, num_to_flip)) if wins else set()
        for idx in flip_indices:
            orig_win = base_trades[idx]["pnl"]
            base_trades[idx]["pnl"] = -abs(orig_win) * (1.0 / 3.0)  # convert win to 1R loss
            base_trades[idx]["is_win"] = False

    # Apply trade drop
    if trade_drop_pct > 0:
        keep_n = int(len(base_trades) * (1.0 - trade_drop_pct))
        base_trades = random.sample(base_trades, keep_n)

    # Worst trades added/doubled
    if worst_trades_added > 0:
        losses = sorted([tr for tr in base_trades if tr["pnl"] < 0], key=lambda x: x["pnl"])
        if losses:
            worst_k = losses[:worst_trades_added]
            base_trades.extend(worst_k)

    # Duplicate loss streaks
    if dup_loss_streaks:
        new_tr = []
        for tr in base_trades:
            new_tr.append(tr)
            if not tr["is_win"]:
                new_tr.append(tr) # duplicate loss
        base_trades = new_tr

    # Run simulations
    completed_challenges_list = []
    max_dds = []
    ruin_count = 0
    final_pnls = []

    for sim_i in range(sim_count):
        shuffled = base_trades[:]
        random.shuffle(shuffled)

        balance = initial_cap
        daily_open = initial_cap
        stage = 1
        completed = 0
        peak = initial_cap
        max_dd = 0.0
        daily_dd_max = 0.0
        day_trades = 0

        for tr in shuffled:
            pnl = tr["pnl"]
            balance += pnl
            day_trades += 1
            if day_trades % 6 == 0:
                daily_open = balance

            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

            daily_dd = (daily_open - balance) / daily_open if daily_open > 0 else 0.0
            daily_dd_max = max(daily_dd_max, daily_dd)

            # Check failures
            if (10000.0 - balance) / 10000.0 >= max_total_limit or daily_dd >= max_daily_limit:
                ruin_count += 1
                balance = 10000.0
                stage = 1
                peak = 10000.0
                continue

            if stage == 1:
                if (balance - 10000.0) / 10000.0 >= stage1_target:
                    stage = 2
                    balance = 10000.0
                    peak = 10000.0
            elif stage == 2:
                if (balance - 10000.0) / 10000.0 >= stage2_target:
                    completed += 1
                    stage = 1
                    balance = 10000.0
                    peak = 10000.0

        completed_challenges_list.append(completed)
        max_dds.append(max_dd * 100.0)
        final_pnls.append(sum(t["pnl"] for t in shuffled))

    completed_challenges_list.sort()
    max_dds.sort()
    final_pnls.sort()

    avg_pass = sum(completed_challenges_list) / sim_count
    med_pass = completed_challenges_list[sim_count // 2]
    pass_5_plus_prob = sum(1 for c in completed_challenges_list if c >= 5) / sim_count * 100.0
    pass_1_plus_prob = sum(1 for c in completed_challenges_list if c >= 1) / sim_count * 100.0
    ruin_prob = (ruin_count / (sim_count * len(base_trades))) * 100.0 if len(base_trades) > 0 else 0.0
    avg_max_dd = sum(max_dds) / sim_count
    p95_max_dd = max_dds[int(sim_count * 0.95)]
    med_pnl = final_pnls[sim_count // 2]
    worst_pnl = final_pnls[0]

    return {
        "avg_pass": round(avg_pass, 2),
        "med_pass": med_pass,
        "pass_5_plus_prob": round(pass_5_plus_prob, 1),
        "pass_1_plus_prob": round(pass_1_plus_prob, 1),
        "ruin_prob": round(ruin_prob, 2),
        "avg_max_dd": round(avg_max_dd, 2),
        "p95_max_dd": round(p95_max_dd, 2),
        "med_pnl": round(med_pnl, 2),
        "worst_pnl": round(worst_pnl, 2)
    }

def main():
    multi_data = load_cached_data()
    cfg = make_config()
    res, rep, ps = simulate_multi_challenge(multi_data, cfg)

    trade_logs = res.trade_logs
    print(f"Total base trades: {len(trade_logs)}")

    scenarios = {
        "A) Baseline (Normal)": {},
        "B) 2x Slippage (2 bps)": {"slippage_mult": 2.0},
        "C) 3x Slippage (3 bps)": {"slippage_mult": 3.0},
        "D) 5x Slippage (5 bps)": {"slippage_mult": 5.0},
        "E) Win Rate -5% (57.6%)": {"win_rate_delta": -0.05},
        "F) Win Rate -10% (52.6%)": {"win_rate_delta": -0.10},
        "G) Avg Loss +20%": {"avg_loss_mult": 1.20},
        "H) Avg Loss +30%": {"avg_loss_mult": 1.30},
        "I) Loss Streaks x2": {"dup_loss_streaks": True},
        "J) BTC/ETH Lockstep Correlation": {"corr_lock": True},
        "K) Random 20% Trade Removal": {"trade_drop_pct": 0.20},
        "L) Worst 10 Trades Added": {"worst_trades_added": 10},
        "M) Fees 2x (0.08% per side)": {"fee_mult": 2.0},
        "N) Combined Fees 2x + Slippage 3x": {"fee_mult": 2.0, "slippage_mult": 3.0}
    }

    out = {}
    for name, params in scenarios.items():
        r = run_stress_sim(trade_logs, cfg, sim_count=300, **params)
        out[name] = r
        print(f"{name:<35} | Pass >=5: {r['pass_5_plus_prob']:>5.1f}% | Avg Pass: {r['avg_pass']:>4.1f} | Ruin: {r['ruin_prob']:>4.2f}% | MaxDD(95th): {r['p95_max_dd']:>4.1f}% | Med PnL: ${r['med_pnl']:>+8.2f}")

    with open("backend/reports/forensic_stress_results.json", "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
