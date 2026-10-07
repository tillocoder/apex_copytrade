"""
Data Downloader for Armandino Engine
Fetches 95 days of Binance Futures M15 and H1 data for ETHUSDT and ZECUSDT.
Pure Python Standard Library (No external dependencies needed).
"""

import os
import sys
import time
import json
import csv
import datetime
import urllib.request

SYMBOLS = ["ETHUSDT", "ZECUSDT"]
INTERVALS = ["15m", "1h"]
DAYS_BACK = 95
BASE_URL = "https://fapi.binance.com/fapi/v1/klines"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_klines(symbol: str, interval: str, start_ts: int, end_ts: int) -> list:
    all_klines = []
    current_start = start_ts
    headers = {"User-Agent": "Mozilla/5.0"}
    
    while current_start < end_ts:
        url = f"{BASE_URL}?symbol={symbol}&interval={interval}&startTime={current_start}&endTime={end_ts}&limit=1500"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Error fetching {symbol} {interval} at {current_start}: {e}. Retrying in 2s...")
            time.sleep(2)
            continue

        if not data:
            break
            
        all_klines.extend(data)
        last_close_time = data[-1][6]
        current_start = last_close_time + 1
        
        if len(data) < 1500:
            break
            
        time.sleep(0.08)  # Rate limit safety
        
    return all_klines


def download_all():
    now = datetime.datetime.now(datetime.timezone.utc)
    end_ts = int(now.timestamp() * 1000)
    start_ts = int((now - datetime.timedelta(days=DAYS_BACK)).timestamp() * 1000)
    
    print(f"=== Armandino Data Downloader ===")
    print(f"Time range: {datetime.datetime.fromtimestamp(start_ts/1000, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} -> {now.strftime('%Y-%m-%d %H:%M UTC')}")
    
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            print(f"Fetching {symbol} ({interval})...", end=" ", flush=True)
            klines = fetch_klines(symbol, interval, start_ts, end_ts)
            
            # Deduplicate by open timestamp
            seen = set()
            clean_klines = []
            for k in klines:
                if k[0] not in seen:
                    seen.add(k[0])
                    clean_klines.append(k)
                    
            clean_klines.sort(key=lambda x: x[0])
            
            filename = os.path.join(DATA_DIR, f"{symbol}_{interval}_3m.csv")
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base",
                    "taker_buy_quote", "datetime"
                ])
                for row in clean_klines:
                    dt_str = datetime.datetime.fromtimestamp(row[0]/1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    writer.writerow([
                        int(row[0]),
                        float(row[1]),
                        float(row[2]),
                        float(row[3]),
                        float(row[4]),
                        float(row[5]),
                        int(row[6]),
                        float(row[7]),
                        int(row[8]),
                        float(row[9]),
                        float(row[10]),
                        dt_str
                    ])
                    
            first_dt = datetime.datetime.fromtimestamp(clean_klines[0][0]/1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
            last_dt = datetime.datetime.fromtimestamp(clean_klines[-1][0]/1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
            print(f"Done. {len(clean_klines)} candles ({first_dt} -> {last_dt}) saved to {os.path.basename(filename)}")


if __name__ == "__main__":
    download_all()
