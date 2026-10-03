import urllib.request
import json
import time
from datetime import datetime, timezone

now = int(time.time() * 1000)
# Test 730 days (2 years)
start = now - (730 * 24 * 3600 * 1000)
url = f"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=5m&startTime={start}&limit=5"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())
    first_t = data[0][0]
    dt = datetime.fromtimestamp(first_t / 1000, tz=timezone.utc)
    print("BTCUSDT 2-year test -> First candle:", dt.strftime("%Y-%m-%d %H:%M:%S UTC"), "Days back:", round((now - first_t)/(24*3600*1000), 1))

# Check ETHUSDT
url = f"https://fapi.binance.com/fapi/v1/klines?symbol=ETHUSDT&interval=5m&startTime={start}&limit=5"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())
    first_t = data[0][0]
    dt = datetime.fromtimestamp(first_t / 1000, tz=timezone.utc)
    print("ETHUSDT 2-year test -> First candle:", dt.strftime("%Y-%m-%d %H:%M:%S UTC"), "Days back:", round((now - first_t)/(24*3600*1000), 1))
