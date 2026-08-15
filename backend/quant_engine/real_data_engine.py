import os
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from typing import List, Optional, Dict
from .market_data import Candle

class RealHistoricalDataEngine:
    """
    Production-grade Real Historical Market Data Engine.
    Downloads and caches Binance M15 OHLCV data or ingests a verified local CSV
    cache. Synthetic price generation is deliberately not supported.
    """

    BINANCE_SPOT_URL = "https://api.binance.com/api/v3/klines"
    CACHE_DIR = "backend/data/historical"

    @classmethod
    def get_symbol_data(
        cls, 
        symbol: str = "BTC/USDT", 
        years: float = 3.0, 
        force_download: bool = False
    ) -> List[Candle]:
        """
        Gets real M15 historical candles.
        Existing real-data caches are preferred; if none exists, Binance is used.
        The engine fails closed when market history is unavailable rather than
        silently replacing it with simulated candles.
        """
        clean_symbol = symbol.replace("/", "").upper()
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        max_candles = int(years * 35040)
        cache_candidates = [os.path.join(cls.CACHE_DIR, f"{clean_symbol}_M15_REAL.csv")]
        if years <= 1.05:
            cache_candidates = [
                os.path.join(cls.CACHE_DIR, f"{clean_symbol}_M15_1Y_2025.csv"),
                os.path.join(cls.CACHE_DIR, f"{clean_symbol}_REAL_M15_1Y.csv"),
                *cache_candidates,
            ]

        if not force_download:
            for cache_path in cache_candidates:
                if not os.path.exists(cache_path):
                    continue
                candles = cls.load_from_csv(cache_path, symbol, max_candles=max_candles)
                if len(candles) >= 1000:
                    print(f"[REAL DATA] Loading verified Binance OHLCV cache: {cache_path} ({len(candles):,} bars)")
                    return candles

        print(f"[REAL DATA] Downloading {years:g} year(s) of Binance M15 OHLCV for {symbol}...")
        candles = cls.fetch_binance_m15(clean_symbol, years=years, display_symbol=symbol)
        if len(candles) < 1000:
            raise RuntimeError(f"Insufficient real Binance history for {symbol}; synthetic fallback is disabled.")

        cache_path = os.path.join(cls.CACHE_DIR, f"{clean_symbol}_M15_REAL.csv")
        cls.save_to_csv(candles, cache_path)
        print(f"[REAL DATA] Cached {len(candles):,} real Binance M15 candles to {cache_path}")
        return candles

    @classmethod
    def fetch_binance_m15(
        cls, 
        binance_symbol: str, 
        years: float = 3.0, 
        display_symbol: str = "BTC/USDT"
    ) -> List[Candle]:
        """Downloads historical M15 candles in 1000-candle chunks."""
        end_time_ms = int(time.time() * 1000)
        start_time_ms = end_time_ms - int(years * 365.25 * 24 * 3600 * 1000)
        
        candles: List[Candle] = []
        curr_start = start_time_ms

        headers = {'User-Agent': 'Mozilla/5.0'}

        try:
            while curr_start < end_time_ms:
                url = f"{cls.BINANCE_SPOT_URL}?symbol={binance_symbol}&interval=15m&startTime={curr_start}&limit=1000"
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status != 200:
                        break
                    data = json.loads(resp.read().decode('utf-8'))

                if not data:
                    break

                for row in data:
                    open_time = datetime.fromtimestamp(row[0] / 1000.0, tz=timezone.utc)
                    c = Candle(
                        timestamp=open_time,
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                        symbol=display_symbol
                    )
                    candles.append(c)

                last_time = data[-1][0]
                if last_time <= curr_start:
                    break
                curr_start = last_time + 1
                time.sleep(0.05)  # rate limit safety
        except Exception as e:
            print(f"[REAL DATA WARNING] Binance API fetch notice ({e}). Switching to historical dataset...")
            return []

        # Ensure candles sorted chronologically
        candles.sort(key=lambda x: x.timestamp)
        return candles

    @classmethod
    def load_from_csv(cls, csv_path: str, symbol: str, max_candles: Optional[int] = None) -> List[Candle]:
        """Ingests CSV OHLCV files."""
        candles: List[Candle] = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            return []
            
        header = lines[0]
        data_lines = lines[1:]
        
        if max_candles is not None and len(data_lines) > max_candles:
            data_lines = data_lines[-max_candles:]
            
        reader = csv.DictReader([header] + data_lines)
        for row in reader:
            ts_val = row.get('timestamp') or row.get('datetime') or row.get('time')
            try:
                ts = datetime.fromisoformat(ts_val)
            except Exception:
                ts = datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S")

            c = Candle(
                timestamp=ts,
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row.get('volume', 100.0)),
                symbol=symbol
            )
            candles.append(c)
        candles.sort(key=lambda x: x.timestamp)
        return candles

    @classmethod
    def save_to_csv(cls, candles: List[Candle], csv_path: str) -> None:
        """Saves candles to CSV file."""
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol'])
            for c in candles:
                writer.writerow([
                    c.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    c.open,
                    c.high,
                    c.low,
                    c.close,
                    c.volume,
                    c.symbol
                ])
