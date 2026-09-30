import sys
import os

sys.path.insert(0, os.path.expanduser("~/apex_copytrade"))

from backend.binance_futures import service_instance, DEFAULT_CONFIG

md = service_instance.md
strat = service_instance.strategy
risk = service_instance.risk

print("=== MARKET DATA SNAPSHOT ===")
print("Symbol:", md.symbol)
print("Current Price:", md.get_current_price())
print("Mark Price:", md.mark_price)
print("Bid/Ask:", md.best_bid, "/", md.best_ask)
print("Spread:", md.get_spread())
print("M1 Candles Count:", len(md.klines_m1))
print("M5 Candles Count:", len(md.klines_m5))
print("M15 Candles Count:", len(md.klines_m15))
print("Session Info:", md.get_current_session())
print("Config enabled_sessions:", DEFAULT_CONFIG.enabled_sessions)
print("Config min_score_threshold:", DEFAULT_CONFIG.min_score_threshold)
print("Config min_r_dist:", getattr(DEFAULT_CONFIG, "min_r_dist", None))
print("Config anti_chase_max_body_atr:", DEFAULT_CONFIG.anti_chase_max_body_atr)
print("Config min_atr_m1:", DEFAULT_CONFIG.min_atr_m1)
print("Config m15_adx_threshold:", getattr(DEFAULT_CONFIG, "m15_adx_threshold", None))

risk_check = risk.check_preflight_risk(has_open_position=False, is_live_mode=False)
print("\n=== RISK CHECK ===")
print(risk_check)

print("\n=== STRATEGY EVALUATION (LIVE SESSION) ===")
res_live = strat.evaluate_setup(risk_check)
print("Signal:", res_live.get("final_signal"))
print("Score:", res_live.get("score"))
print("Rejection:", res_live.get("rejection_reason") or res_live.get("rejectionReason"))
print("Matrix:", res_live.get("matrix"))

print("\n=== STRATEGY EVALUATION (IF SESSION ALLOWED) ===")
# Temporarily bypass session check to inspect setup score and modules right now
orig_sess = md.get_current_session
md.get_current_session = lambda: {"session": "LONDON", "is_allowed": True, "tashkent_time": "11:00 Tashkent"}
res_forced = strat.evaluate_setup(risk_check)
print("Forced Signal:", res_forced.get("final_signal"))
print("Forced Score:", res_forced.get("score"))
print("Forced Rejection:", res_forced.get("rejection_reason") or res_forced.get("rejectionReason"))
print("Forced Matrix:", res_forced.get("matrix"))
md.get_current_session = orig_sess
