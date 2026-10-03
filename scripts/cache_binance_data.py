#!/usr/bin/env python3
"""
Downloads and caches 2 full years (730 days) of M5 klines from Binance Futures for BTCUSDT and ETHUSDT.
"""
import os
import sys
import json
import time
import urllib.request
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_and_cache(symbol, days=730):
    cache_path = os.path.join(DATA_DIR, f"klines_{symbol.lower()}_5m_2y.json")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000000:
        print(f"📦 Found existing cache for {symbol}: {cache_path} ({os.path.getsize(cache_path)//1024} KB)")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if len(data) >= 200000:
                print(f"   ✅ Cache valid with {len(data)} candles. Skipping download.")
                return data
        except Exception:
            pass

    now_ms = int(time.time() * 1000)
    total_days = days + 7  # buffer
    start_ms = now_ms - (total_days * 24 * 3600 * 1000)
    
    print(f"📥 Downloading {days} days of M5 candles for {symbol} from Binance Futures...")
    all_candles = []
    current_start = start_ms
    req_count = 0
    start_time = time.time()
    
    while current_start < now_ms:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=5m&startTime={current_start}&limit=1500"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode())
                if not raw:
                    break
                for k in raw:
                    all_candles.append({
                        "time": int(k[0]),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                current_start = int(raw[-1][0]) + 1
                req_count += 1
                if req_count % 20 == 0:
                    dt = datetime.fromtimestamp(current_start / 1000, tz=timezone.utc)
                    print(f"   Fetched {len(all_candles)} candles... (up to {dt.strftime('%Y-%m-%d')})")
                if len(raw) < 1500:
                    break
                time.sleep(0.04)
        except Exception as e:
            print(f"   ⚠️ Request error: {e}. Retrying in 1s...")
            time.sleep(1.0)
            
    # Deduplicate and sort
    seen = set()
    unique = []
    for c in all_candles:
        if c["time"] not in seen:
            seen.add(c["time"])
            unique.append(c)
    unique.sort(key=lambda x: x["time"])
    
    elapsed = time.time() - start_time
    print(f"✅ Finished {symbol}: {len(unique)} candles in {elapsed:.1f}s ({req_count} requests).")
    
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(unique, f)
    print(f"💾 Saved to {cache_path} ({os.path.getsize(cache_path)//1024} KB)")
    return unique

if __name__ == "__main__":
    print("=" * 70)
    print("📥 APEX QUANT v4: HISTORICAL DATA CACHING (2 YEARS BTC & ETH)")
    print("=" * 70)
    fetch_and_cache("BTCUSDT", days=730)
    fetch_and_cache("ETHUSDT", days=730)
    print("\n🎉 All historical data cached successfully!")
