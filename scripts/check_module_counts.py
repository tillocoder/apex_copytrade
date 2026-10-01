import time
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
from run_v33_hyperparameter_suite import precalculate_all_features_v33, DATA_PATH

print("Loading data...")
with open(DATA_PATH, "r") as f:
    reader = csv.reader(f)
    next(reader)
    raw = [{"time": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in reader]

features = precalculate_all_features_v33(raw)

modules = [
    "MODULE_A_SWEEP_RECLAIM",
    "MODULE_B_BREAKOUT",
    "MODULE_C_EMA_PULLBACK",
    "MODULE_D_MOMENTUM_IMPULSE",
    "MODULE_E_M5_M1_HYBRID"
]

counts = {}
for f in features:
    mod = f.get("cand_module")
    if mod:
        counts[mod] = counts.get(mod, 0) + 1

print("\nCandidate module triggers in 90 days (129,600 M1 bars):")
for m, c in counts.items():
    print(f"  {m}: {c} triggers ({c/90:.1f} per day)")
