import sys
sys.path.insert(0, r'C:\apex_copytrade')
from scratch.tune_v33 import features, idx_val_end, idx_train_end
from run_v33_hyperparameter_suite import run_simulation_v33_fast

candidates = [
    {"name": "v3.3 Model 1 (ADX 22, TP 2.5x)", "score_threshold": 78, "session_mode": "LONDON_EXPANSION_ONLY", "m15_adx_threshold": 22.0, "be_trigger": "NO_BE", "tp_vol_multiplier": 2.5},
    {"name": "v3.3 Model 2 (ADX 18, TP 2.2x)", "score_threshold": 80, "session_mode": "LONDON_EXPANSION_ONLY", "m15_adx_threshold": 18.0, "be_trigger": "NO_BE", "tp_vol_multiplier": 2.2},
    {"name": "v3.3 Model 3 (ADX 18, TP 2.5x)", "score_threshold": 80, "session_mode": "LONDON_EXPANSION_ONLY", "m15_adx_threshold": 18.0, "be_trigger": "NO_BE", "tp_vol_multiplier": 2.5},
    {"name": "v3.3 Model 4 (ADX 20, TP 2.2x)", "score_threshold": 80, "session_mode": "LONDON_EXPANSION_ONLY", "m15_adx_threshold": 20.0, "be_trigger": "NO_BE", "tp_vol_multiplier": 2.2},
]

for c in candidates:
    name = c.pop("name")
    rf = run_simulation_v33_fast(features, **c)
    ro = run_simulation_v33_fast(features[idx_val_end:], **c)
    rt = run_simulation_v33_fast(features[:idx_train_end], **c)
    rv = run_simulation_v33_fast(features[idx_train_end:idx_val_end], **c)
    print(f"{name:32s} || Full: N={rf['total_trades']:2d} WR={rf['win_rate_pct']:4.1f}% Payoff={rf['payoff_ratio']:4.2f}x GrossPF={rf['gross_pf']:4.2f} NetPF={rf['net_pf']:4.2f} PnL=${rf['net_pnl']:6.2f} DD={rf['max_drawdown_pct']:4.1f}% FeeDrag={rf['fee_over_gp_pct']:4.1f}% || Train: NetPF={rt['net_pf']:4.2f} | Val: NetPF={rv['net_pf']:4.2f} | OOS: N={ro['total_trades']:2d} WR={ro['win_rate_pct']:4.1f}% NetPF={ro['net_pf']:4.2f} PnL=${ro['net_pnl']:6.2f}")
