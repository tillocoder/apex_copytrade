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

print(f"Loaded {len(raw_candles)} candles. Precalculating...")
features = precalculate_all_features(raw_candles)

print("\n--- Testing parameter combinations ---")
for sc in [70, 75, 80]:
    for em in ["A", "B", "D", "E", "G"]:
        for sm in ["WEIGHTED", "MAJOR_ONLY", "RESTRICTED_ASIA"]:
            r = run_simulation_v32_fast(features, score_threshold=sc, exit_model=em, session_mode=sm)
            print(f"Sc={sc} Em={em} Sm={sm:15s} | Tr={r['total_trades']:3d} | WR={r['win_rate_pct']:4.1f}% | GPF={r['gross_pf']:4.2f} | NPF={r['net_pf']:4.2f} | PnL=${r['net_pnl']:7.2f} | Fee=${r['total_fees']:6.2f}")
