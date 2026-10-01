import json

# Let's inspect the top 15 in detail
with open(r"data\targeted_high_winrate_results.json") as f:
    d = json.load(f)

print(f"Total configurations tested: {d['total_tested']:,}")
print(f"Profitable configurations count: {d['profitable_count']}")
print("\nDetailed Top 5 Breakdown:")
for i, m in enumerate(d["top_15"][:5]):
    p = m["params"]
    print(f"\nModel #{i+1}:")
    print(f"  Win Rate (90-Day Full) : {m['win_rate_pct']}% ({m['total_trades']} trades, {m['trades_per_day']} trades/day)")
    print(f"  Win Rate (Out-of-Sample): {m['oos_win_rate_pct']}% ({m['oos_trades']} trades)")
    print(f"  Net Profit Factor      : {m['net_pf']}x (OOS PF: {m['oos_pf']}x)")
    print(f"  Net PnL                : +${m['net_pnl']} (OOS PnL: +${m['oos_pnl']})")
    print(f"  Max Drawdown           : {m['max_dd_pct']}%")
    print(f"  Parameters:")
    print(f"    - Module            : {p['module']}")
    print(f"    - Session           : {p['session_mode']}")
    print(f"    - Trend Filter      : {p['trend_filter']}")
    print(f"    - Stop Loss Buffer  : {p['sl_atr_mult']}x ATR (min ${p['min_sl_usd']:.2f})")
    print(f"    - Take Profit       : {p['tp_r']}R (Scalp target)")
    print(f"    - Score Threshold   : >={p['score_thresh']}")
    print(f"    - ADX Filter        : >={p['adx_min']}")
