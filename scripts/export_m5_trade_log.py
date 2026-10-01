import sys
import json
from datetime import datetime, timezone
sys.path.insert(0, r"C:\apex_copytrade\scripts")
from m5_supertrend_hardener import load_and_prep, build_multi_supertrend_features, run_sim

m5_bars, m5_sub_m1 = load_and_prep()
features = build_multi_supertrend_features(m5_bars)

with open(r'C:\apex_copytrade\audit\m5_supertrend_final\m5_supertrend_hardened_summary.json') as f:
    d = json.load(f)
p = d['winner_params']

res = run_sim(features, m5_sub_m1, 250, len(features), p)
trades = res['trades_list']

csv_path = r'C:\apex_copytrade\audit\m5_supertrend_final\m5_trade_log.csv'
with open(csv_path, 'w', encoding='utf-8') as f:
    f.write('timestamp,side,entry,exit,reason,is_win,gross_pnl,comm,net_pnl,R,drawdown_pct\n')
    for t in trades:
        dt_str = datetime.fromtimestamp(t['time']/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        f.write(f"{dt_str},{t['side']},{t['entry']},{t['exit']},{t['reason']},{t['is_win']},{t['gross_pnl']},{t['comm']},{t['net_pnl']},{t['r']},{t['dd']}\n")

print(f"Exported {len(trades)} trades to {csv_path}")
