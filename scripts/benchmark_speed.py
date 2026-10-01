import time
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
from run_v33_hyperparameter_suite import precalculate_all_features_v33, run_simulation_v33_fast, DATA_PATH

print("Loading CSV...")
t0 = time.time()
with open(DATA_PATH, "r") as f:
    reader = csv.reader(f)
    next(reader)
    raw = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in reader]
print(f"Loaded {len(raw)} candles in {time.time()-t0:.2f}s")

t0 = time.time()
features = precalculate_all_features_v33(raw)
print(f"Precalculated features in {time.time()-t0:.2f}s")

t0 = time.time()
res = run_simulation_v33_fast(features)
print(f"Simulated in {time.time()-t0:.4f}s: trades={res.get('total_trades')}, wr={res.get('win_rate_pct')}%, pf={res.get('net_pf')}")
