import csv
from run_v32_forensic_suite import DATA_PATH, precalculate_all_features, run_simulation_v32_fast

raw_candles = []
with open(DATA_PATH, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        raw_candles.append({
            "time": int(r["time"]), "open": float(r["open"]),
            "high": float(r["high"]), "low": float(r["low"]),
            "close": float(r["close"]), "volume": float(r["volume"])
        })

features = precalculate_all_features(raw_candles)
n = len(features)
i_tr = int(n * 0.60)
i_val = int(n * 0.80)

f_train = features[:i_tr]
f_val = features[i_tr:i_val]
f_oos = features[i_val:]

print("--- Walk-Forward for Sc=80 Em=G Sm=MAJOR_ONLY ---")
r_full = run_simulation_v32_fast(features, score_threshold=80, exit_model="G", session_mode="MAJOR_ONLY")
r_train = run_simulation_v32_fast(f_train, score_threshold=80, exit_model="G", session_mode="MAJOR_ONLY")
r_val = run_simulation_v32_fast(f_val, score_threshold=80, exit_model="G", session_mode="MAJOR_ONLY")
r_oos = run_simulation_v32_fast(f_oos, score_threshold=80, exit_model="G", session_mode="MAJOR_ONLY")

print(f"FULL : Trades={r_full['total_trades']:3d} | WR={r_full['win_rate_pct']:4.1f}% | Gross PF={r_full['gross_pf']:4.2f} | Net PF={r_full['net_pf']:4.2f} | PnL=${r_full['net_pnl']:7.2f} | Max DD={r_full['max_drawdown_pct']}%")
print(f"TRAIN: Trades={r_train['total_trades']:3d} | WR={r_train['win_rate_pct']:4.1f}% | Gross PF={r_train['gross_pf']:4.2f} | Net PF={r_train['net_pf']:4.2f} | PnL=${r_train['net_pnl']:7.2f}")
print(f"VAL  : Trades={r_val['total_trades']:3d} | WR={r_val['win_rate_pct']:4.1f}% | Gross PF={r_val['gross_pf']:4.2f} | Net PF={r_val['net_pf']:4.2f} | PnL=${r_val['net_pnl']:7.2f}")
print(f"OOS  : Trades={r_oos['total_trades']:3d} | WR={r_oos['win_rate_pct']:4.1f}% | Gross PF={r_oos['gross_pf']:4.2f} | Net PF={r_oos['net_pf']:4.2f} | PnL=${r_oos['net_pnl']:7.2f}")

print("\n--- Testing variations around Sc=80 Em=G ---")
for sc in [78, 80, 82]:
    for be in [1.5, 2.0]:
        for fee_gate in [0.20, 0.25]:
            r_tr = run_simulation_v32_fast(f_train, score_threshold=sc, exit_model="G", session_mode="MAJOR_ONLY", be_trigger_r=be, fee_risk_gate_ratio=fee_gate)
            r_o = run_simulation_v32_fast(f_oos, score_threshold=sc, exit_model="G", session_mode="MAJOR_ONLY", be_trigger_r=be, fee_risk_gate_ratio=fee_gate)
            print(f"Sc={sc} BE={be} FG={fee_gate} | Train NPF={r_tr['net_pf']:4.2f} PnL=${r_tr['net_pnl']:6.2f} | OOS NPF={r_o['net_pf']:4.2f} PnL=${r_o['net_pnl']:6.2f} WR={r_o['win_rate_pct']:4.1f}% Tr={r_o['total_trades']}")
