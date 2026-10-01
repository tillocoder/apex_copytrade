import json

with open(r"data\high_winrate_optimization_summary.json") as f:
    d = json.load(f)

print("Total tested:", d.get("total_combinations_tested"))
print("High WR count:", d.get("high_winrate_models_count"))
candidates = d.get("top_10_candidates", [])
print(f"Top candidates count: {len(candidates)}")
for idx, m in enumerate(candidates):
    p = m.get("params", {})
    print(f"#{idx+1}: WR={m.get('win_rate_pct')}% | PF={m.get('net_pf')} | PnL=${m.get('net_pnl')} | Trades={m.get('total_trades')} | MaxDD={m.get('max_dd_pct')}% | OOS_WR={m.get('oos_win_rate_pct')}% | OOS_PF={m.get('oos_pf')}")
    print(f"   Mod={p.get('allowed_modules')} | TF={p.get('trend_filter')} | SL={p.get('sl_model')} x{p.get('sl_mult')} (min ${p.get('min_sl_usd')}) | TP={p.get('tp_mode')} {p.get('tp_r')}R | BE={p.get('be_after_r')}R | Score>={p.get('score_threshold')}")
