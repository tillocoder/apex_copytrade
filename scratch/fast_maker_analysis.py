import sys
sys.path.insert(0, r'C:\apex_copytrade')
from run_v32_forensic_suite import run_simulation_v32_fast, precalculate_all_features
import csv
from datetime import datetime, timezone

raw = []
with open(r'c:\apex_copytrade\data\binance_ethusdt_m1_90d.csv') as f:
    for r in csv.DictReader(f):
        raw.append({k: float(v) if k != 'time' else int(v) for k, v in r.items()})

feat = precalculate_all_features(raw)
ts_to_idx = {datetime.fromtimestamp(f['time'] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'): i for i, f in enumerate(feat)}

res_a = run_simulation_v32_fast(feat, score_threshold=80, exit_model='G', session_mode='MAJOR_ONLY')
trades_a = res_a['trades']

filled_maker_count = 0
for tr in trades_a:
    idx = ts_to_idx.get(tr['timestamp'], -1)
    if idx != -1 and idx + 1 < len(feat):
        next_c = feat[idx + 1]
        lim_px = feat[idx]['close']
        if tr['side'] == 'LONG':
            filled = (next_c['low'] <= lim_px - 0.01)
        else:
            filled = (next_c['high'] >= lim_px + 0.01)
        if filled:
            filled_maker_count += 1

print(f"Cand A Maker Fill Rate (1-tick adverse test): {filled_maker_count} / {len(trades_a)} ({filled_maker_count/len(trades_a)*100:.1f}%)")
