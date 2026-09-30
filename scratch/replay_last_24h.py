import urllib.request
import json
import time
from datetime import datetime, timezone, timedelta

# Fetch last 1500 M1 candles from Binance Futures public API
url = "https://fapi.binance.com/fapi/v1/klines?symbol=ETHUSDT&interval=1m&limit=1500"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    raw = json.loads(resp.read().decode())

print(f"Fetched {len(raw)} M1 candles from Binance Futures.")
candles = []
for r in raw:
    candles.append({
        "time": int(r[0]),
        "open": float(r[1]),
        "high": float(r[2]),
        "low": float(r[3]),
        "close": float(r[4]),
        "volume": float(r[5])
    })

tashkent_tz = timezone(timedelta(hours=5))
start_dt = datetime.fromtimestamp(candles[0]["time"]/1000, tz=tashkent_tz)
end_dt = datetime.fromtimestamp(candles[-1]["time"]/1000, tz=tashkent_tz)
print(f"Time range: {start_dt} to {end_dt}")

# Now import our strategy engine and simulate candle by candle
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.binance_futures.config import DEFAULT_CONFIG
from backend.binance_futures.market_data import MarketDataManager
from backend.binance_futures.strategy_engine import ETHM1ScalpingStrategy
from backend.binance_futures.risk_manager import RiskManager

md = MarketDataManager(symbol="ETHUSDT")
risk = RiskManager(md)
strat = ETHM1ScalpingStrategy(md)

# Pre-load first 50 candles
md.load_initial_klines([[c["time"], c["open"], c["high"], c["low"], c["close"], c["volume"]] for c in candles[:60]], "1m")

signals = []
rejection_stats = {}
scores_distribution = []

for idx, c in enumerate(candles[60:], start=60):
    # Update candle and ticker
    md.update_book_ticker(c["close"], c["close"] + 0.01, 10.0, 10.0)
    md.update_kline_stream({
        "t": c["time"],
        "o": c["open"],
        "h": c["high"],
        "l": c["low"],
        "c": c["close"],
        "v": c["volume"],
        "x": True
    })
    md.best_bid = c["close"]
    md.best_ask = c["close"] + 0.01

    c_utc = datetime.fromtimestamp(c["time"]/1000, tz=timezone.utc)
    c_hr = c_utc.hour + c_utc.minute / 60.0
    s_name = "OUT_OF_SESSION"
    if 13.5 <= c_hr < 16.5: s_name = "LONDON_NY_OVERLAP"
    elif 13.5 <= c_hr < 20.0: s_name = "NEW_YORK"
    elif 8.0 <= c_hr < 16.5: s_name = "LONDON"
    elif 0.0 <= c_hr < 8.0: s_name = "ASIA"
    md.get_current_session = lambda s=s_name: {
        "session": s,
        "is_allowed": DEFAULT_CONFIG.enabled_sessions.get(s, False) if s != "OUT_OF_SESSION" else False
    }

    risk_check = risk.check_preflight_risk(has_open_position=False, is_live_mode=False)
    res = strat.evaluate_setup(risk_check)
    
    score = res.get("score", 0)
    scores_distribution.append(score)
    sig = res.get("final_signal")
    reason = res.get("rejection_reason") or res.get("reason")
    
    rejection_stats[reason] = rejection_stats.get(reason, 0) + 1
    
    c_dt = datetime.fromtimestamp(c["time"]/1000, tz=tashkent_tz)
    if sig in ("LONG", "SHORT"):
        signals.append({
            "idx": idx,
            "time": str(c_dt),
            "signal": sig,
            "score": score,
            "price": c["close"],
            "reason": res.get("reason"),
            "sl": res.get("sl"),
            "tp": res.get("tp")
        })

print("\n" + "="*80)
print(f"ANALYSIS WITH CURRENT CONFIG (Score >= {DEFAULT_CONFIG.min_score_threshold}, London Only):")
print(f"Total signals triggered: {len(signals)}")
for s in signals:
    print(f"  [{s['time']}] {s['signal']} @ ${s['price']} | Score: {s['score']} | {s['reason']}")

print("\nTop 10 Rejection Reasons:")
sorted_rej = sorted(rejection_stats.items(), key=lambda x: x[1], reverse=True)
for r, count in sorted_rej[:10]:
    print(f"  {count}x: {r}")

max_score = max(scores_distribution) if scores_distribution else 0
avg_score = sum(scores_distribution)/len(scores_distribution) if scores_distribution else 0
p95_score = sorted(scores_distribution)[int(len(scores_distribution)*0.95)] if scores_distribution else 0
print(f"\nScore Stats: Max Score={max_score}, p95={p95_score}, Avg={avg_score:.1f}")
