import urllib.request
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.binance_futures.market_data import MarketDataManager
from backend.binance_futures.strategy_engine import ETHM1ScalpingStrategy
from backend.binance_futures.config import DEFAULT_CONFIG

def fmt_time(ts_ms):
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone(timedelta(hours=5))).strftime('%Y-%m-%d %H:%M:%S')

def main():
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=ETHUSDT&interval=1m&limit=1500"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        raw_klines = json.loads(resp.read().decode())
    
    print(f"Candles from {fmt_time(raw_klines[0][0])} to {fmt_time(raw_klines[-1][0])}")
    
    # Enable all sessions
    DEFAULT_CONFIG.enabled_sessions = {
        "ASIA": True,
        "LONDON": True,
        "LONDON_NY_OVERLAP": True,
        "NEW_YORK": True
    }
    
    for threshold in [78, 72]:
        DEFAULT_CONFIG.min_score_threshold = threshold
        md_sim = MarketDataManager()
        strat_sim = ETHM1ScalpingStrategy(md_sim)
        
        signals_by_session = {"ASIA": 0, "LONDON": 0, "LONDON_NY_OVERLAP": 0, "NEW_YORK": 0, "OUT_OF_SESSION": 0}
        signals_list = []
        
        for i, k in enumerate(raw_klines):
            candle = {
                "t": k[0], "o": k[1], "h": k[2], "l": k[3], "c": k[4], "v": k[5], "x": True
            }
            md_sim.update_kline_stream(candle)
            md_sim.best_bid = float(k[4]) - 0.01
            md_sim.best_ask = float(k[4]) + 0.01
            md_sim.last_update_ts = candle["t"] / 1000.0
            
            # calculate session
            h = (datetime.fromtimestamp(k[0]/1000.0, tz=timezone.utc).hour + 
                 datetime.fromtimestamp(k[0]/1000.0, tz=timezone.utc).minute / 60.0)
            
            is_asia = (0.0 <= h < 8.0)
            is_london = (8.0 <= h < 16.5)
            is_ny = (13.5 <= h < 20.0)
            is_overlap = (13.5 <= h < 16.5)

            s_name = "OUT_OF_SESSION"
            if is_overlap:
                s_name = "LONDON_NY_OVERLAP"
            elif is_ny:
                s_name = "NEW_YORK"
            elif is_london:
                s_name = "LONDON"
            elif is_asia:
                s_name = "ASIA"
            
            if i >= 30:
                res = strat_sim.evaluate_setup({"can_trade": True, "reason": "OK"})
                if res["final_signal"] in ("LONG", "SHORT"):
                    signals_by_session[s_name] = signals_by_session.get(s_name, 0) + 1
                    signals_list.append({
                        "time": fmt_time(k[0]),
                        "session": s_name,
                        "sig": res["final_signal"],
                        "score": res["score"],
                        "mod": res["module"],
                        "price": float(k[4])
                    })
        
        print(f"\n================ Threshold: {threshold} ================")
        print("Signals breakdown by session:", signals_by_session)
        print(f"Total signals: {len(signals_list)}")
        print("Sample of signals:")
        for s in signals_list[:10]:
            print(f"  {s['time']} | {s['session']} | {s['sig']} @ ${s['price']} | Score: {s['score']} | {s['mod']}")

if __name__ == "__main__":
    main()
