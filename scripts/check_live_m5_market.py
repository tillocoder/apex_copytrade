import urllib.request
import json
import time
from datetime import datetime, timezone

def analyze():
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=ETHUSDT&interval=5m&limit=100"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    raw = urllib.request.urlopen(req).read()
    klines = json.loads(raw)
    
    # Parse candles
    candles = []
    for k in klines:
        t, o, h, l, c, v = int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
        candles.append({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v})
        
    n = len(candles)
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    vols = [c["volume"] for c in candles]
    
    # ATR 10
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
        
    print(f"Total M5 candles analyzed: {n}")
    print("\nRecent 15 M5 Candles (Last 75 minutes):")
    print("Time (UTC) | Time (Tashkent) | Close | ST Val | ST Dir | Flip? | Vol | Vol Ratio")
    print("-" * 80)
    for i in range(n-15, n):
        t_sec = candles[i]["time"] / 1000
        dt_utc = datetime.fromtimestamp(t_sec, tz=timezone.utc)
        dt_tsh = datetime.fromtimestamp(t_sec + 5*3600, tz=timezone.utc)
        
        is_flip = (direction[i] != direction[i-1]) if i > 0 else False
        dir_str = "BULL" if direction[i] == 1 else "BEAR"
        
        v_prior = [candles[j]["volume"] for j in range(max(0, i-10), i)]
        v_avg = sum(v_prior) / len(v_prior) if v_prior else candles[i]["volume"]
        v_ratio = candles[i]["volume"] / max(1.0, v_avg)
        
        print(f"{dt_utc.strftime('%H:%M')} UTC | {dt_tsh.strftime('%H:%M')} TSH | ${closes[i]:.2f} | ${st[i]:.2f} | {dir_str} | {'FLIP!' if is_flip else '  -  '} | {candles[i]['volume']:.0f} | {v_ratio:.2f}x")

    # Count total flips in the 100 candles
    flips = []
    for i in range(period+1, n):
        if direction[i] != direction[i-1]:
            t_sec = candles[i]["time"] / 1000
            dt_tsh = datetime.fromtimestamp(t_sec + 5*3600, tz=timezone.utc)
            flips.append((dt_tsh.strftime('%H:%M'), "BULL" if direction[i] == 1 else "BEAR", closes[i]))
            
    print(f"\nTotal Flips in last ~8 hours (100 M5 bars): {len(flips)}")
    for f in flips:
        print(f"  Flip at {f[0]} Tashkent -> {f[1]} @ ${f[2]:.2f}")

if __name__ == "__main__":
    analyze()
