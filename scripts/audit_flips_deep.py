import urllib.request
import json
from datetime import datetime, timezone, timedelta

def analyze_flips_deep():
    # 1. Fetch H1 candles for H1 EMA200
    h1_url = "https://fapi.binance.com/fapi/v1/klines?symbol=ETHUSDT&interval=1h&limit=300"
    h1_raw = json.loads(urllib.request.urlopen(urllib.request.Request(h1_url, headers={'User-Agent': 'Mozilla/5.0'})).read())
    h1_closes = [float(k[4]) for k in h1_raw]
    h1_times = [int(k[0]) for k in h1_raw]
    
    # Calculate H1 EMA 200
    k_ema = 2.0 / 201.0
    h1_ema = [0.0] * len(h1_closes)
    h1_ema[0] = h1_closes[0]
    for i in range(1, len(h1_closes)):
        h1_ema[i] = h1_closes[i] * k_ema + h1_ema[i-1] * (1.0 - k_ema)
        
    # 2. Fetch M5 candles (350 candles = ~29 hours)
    m5_url = "https://fapi.binance.com/fapi/v1/klines?symbol=ETHUSDT&interval=5m&limit=350"
    m5_raw = json.loads(urllib.request.urlopen(urllib.request.Request(m5_url, headers={'User-Agent': 'Mozilla/5.0'})).read())
    
    candles = []
    for k in m5_raw:
        candles.append({
            "time": int(k[0]), "open": float(k[1]), "high": float(k[2]),
            "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])
        })
        
    n = len(candles)
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    
    # SuperTrend 10, 2.5
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    atr = [0.0] * n
    period = 10
    mult = 2.5
    atr[period-1] = sum(tr[:period]) / period
    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
    st = [0.0] * n
    direction = [1] * n
    upper = [0.0] * n
    lower = [0.0] * n
    for i in range(period, n):
        hl2 = (highs[i] + lows[i]) / 2.0
        bu = hl2 + mult * atr[i]
        bl = hl2 - mult * atr[i]
        lower[i] = bl if bl > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]
        upper[i] = bu if bu < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
        if closes[i] > upper[i-1]: direction[i] = 1
        elif closes[i] < lower[i-1]: direction[i] = -1
        else: direction[i] = direction[i-1]
        st[i] = lower[i] if direction[i] == 1 else upper[i]

    print("================================================================================")
    print("DETAILED FORENSIC AUDIT OF EVERY M5 FLIP (FULL LAST 24+ HOURS)")
    print("================================================================================")
    
    flips_found = 0
    qualified_count = 0
    vetoed_count = 0
    
    for i in range(period+1, n):
        if direction[i] != direction[i-1]:
            flips_found += 1
            t_sec = candles[i]["time"] / 1000
            dt_utc = datetime.fromtimestamp(t_sec, tz=timezone.utc)
            dt_tsh = dt_utc + timedelta(hours=5)
            flip_side = "LONG (Bull Flip)" if direction[i] == 1 else "SHORT (Bear Flip)"
            close_p = closes[i]
            
            # Find corresponding H1 EMA
            c_time_ms = candles[i]["time"]
            h1_idx = -1
            for hi in range(len(h1_times)):
                if h1_times[hi] <= c_time_ms:
                    h1_idx = hi
                    
            h1_val = h1_ema[h1_idx] if h1_idx >= 0 else 0.0
            h1_close = h1_closes[h1_idx] if h1_idx >= 0 else 0.0
            h1_trend = "BULLISH" if h1_close > h1_val else "BEARISH"
            h1_aligned = (direction[i] == 1 and h1_trend == "BULLISH") or (direction[i] == -1 and h1_trend == "BEARISH")
            
            # Volume check
            prev_10_vol = [candles[j]["volume"] for j in range(max(0, i-10), i)]
            avg_10_vol = sum(prev_10_vol) / len(prev_10_vol) if prev_10_vol else 1.0
            cur_vol = candles[i]["volume"]
            vol_ratio = cur_vol / avg_10_vol if avg_10_vol > 0 else 0.0
            vol_passed = vol_ratio >= 1.30
            
            # Session check (07:00 to 21:00 UTC)
            session_hour = dt_utc.hour
            session_passed = 7 <= session_hour < 21
            
            # Overall decision
            qualified = h1_aligned and vol_passed and session_passed
            if qualified: qualified_count += 1
            else: vetoed_count += 1
            
            print(f"\n[FLIP #{flips_found}] {dt_tsh.strftime('%Y-%m-%d %H:%M')} Tashkent ({dt_utc.strftime('%H:%M')} UTC)")
            print(f"  Setup Type       : {flip_side} @ ${close_p:.2f}")
            print(f"  Macro H1 Filter  : H1 Close=${h1_close:.2f} vs H1 EMA200=${h1_val:.2f} -> {h1_trend} (Aligned: {h1_aligned})")
            print(f"  Volume Filter    : Vol={cur_vol:.0f} vs 10-bar Avg={avg_10_vol:.0f} -> Ratio={vol_ratio:.2f}x (>=1.3x: {vol_passed})")
            print(f"  Session Window   : {dt_utc.strftime('%H:%M')} UTC (07:00-21:00 UTC: {session_passed})")
            
            if qualified:
                print(f"  QUALIFIED TRADE? : ✅ YES - SHOULD EXECUTE")
            else:
                veto_reasons = []
                if not session_passed: veto_reasons.append("Out of Session Window")
                if not h1_aligned: veto_reasons.append(f"H1 Trend Mismatch ({h1_trend} != {flip_side.split()[0]})")
                if not vol_passed: veto_reasons.append(f"Low Volume ({vol_ratio:.2f}x < 1.3x)")
                print(f"  QUALIFIED TRADE? : ❌ NO - VETOED BY FILTERS")
                print(f"  Veto Reason      : {', '.join(veto_reasons)}")
                
    print("\n================================================================================")
    print(f"SUMMARY: Total Flips: {flips_found} | Qualified Trades: {qualified_count} | Vetoed Signals: {vetoed_count}")
    print("================================================================================")

if __name__ == "__main__":
    analyze_flips_deep()
