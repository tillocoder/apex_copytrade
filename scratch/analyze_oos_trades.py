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
idx_val = int(len(feat) * 0.8)

# Run Cand A on OOS
res_oos = run_simulation_v32_fast(feat[idx_val:], score_threshold=80, exit_model='G', session_mode='MAJOR_ONLY')
trades = res_oos['trades']

print(f"Cand A OOS Trades: {len(trades)}")
print(f"Wins: {len([t for t in trades if t['net_pnl'] > 0])}, Losses: {len([t for t in trades if t['net_pnl'] < 0])}")
print(f"Gross PF: {res_oos['gross_pf']}, Net PF: {res_oos['net_pf']}, Net PnL: ${res_oos['net_pnl']}")

# Module breakdown in OOS
by_mod = {}
for tr in trades:
    m = tr['module']
    if m not in by_mod: by_mod[m] = {'trades': 0, 'wins': 0, 'net_pnl': 0.0, 'fees': 0.0}
    by_mod[m]['trades'] += 1
    if tr['net_pnl'] > 0: by_mod[m]['wins'] += 1
    by_mod[m]['net_pnl'] += tr['net_pnl']
    by_mod[m]['fees'] += tr['total_fees']

print("\n--- OOS Breakdown by Module ---")
for m, d in by_mod.items():
    wr = d['wins']/d['trades']*100
    print(f"  {m:25s}: Trades={d['trades']:2d} | WR={wr:4.1f}% | Net PnL=${d['net_pnl']:6.2f} | Fees=${d['fees']:5.2f}")

# Exit reason breakdown in OOS
by_exit = {}
for tr in trades:
    ex = tr['exit_reason']
    if ex not in by_exit: by_exit[ex] = {'count': 0, 'pnl': 0.0}
    by_exit[ex]['count'] += 1
    by_exit[ex]['pnl'] += tr['net_pnl']

print("\n--- OOS Breakdown by Exit Reason ---")
for ex, d in by_exit.items():
    print(f"  {ex:25s}: Count={d['count']:2d} | Net PnL=${d['pnl']:6.2f}")

# Failure mode breakdown in OOS
by_fail = {}
for tr in trades:
    if tr['net_pnl'] <= 0:
        fm = tr['failure_mode']
        by_fail[fm] = by_fail.get(fm, 0) + 1

print("\n--- OOS Failure Modes ---")
for fm, cnt in by_fail.items():
    print(f"  {fm:25s}: Count={cnt:2d}")
