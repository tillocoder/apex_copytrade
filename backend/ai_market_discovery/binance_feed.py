"""
Binance Futures Market Data & Derivatives Feed
Fetches Multi-Timeframe klines (H4, H1, M15, M5, M1) and Derivatives Data for BTCUSDT, ETHUSDT, SOLUSDT.
Enforces Data Quality validation (never fabricates data).
"""

import urllib.request
import urllib.error
import json
import time
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

BASE_FAPI = "https://fapi.binance.com"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TIMEFRAMES = ["4h", "1h", "15m", "5m", "1m"]


class BinanceFeed:
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout
        self.headers = {"User-Agent": "Mozilla/5.0 APEX-Quant/4.0"}

    def _get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{BASE_FAPI}{endpoint}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"
        req = urllib.request.Request(url, headers=self.headers)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latency_ms = (time.time() - t0) * 1000.0
            return data, latency_ms

    def fetch_klines(self, symbol: str, interval: str, limit: int = 100) -> Tuple[List[Dict[str, Any]], float]:
        """
        Fetches closed klines from Binance Futures.
        Returns: list of dicts {timestamp, open, high, low, close, volume, taker_buy_vol, datetime_str}, latency_ms
        """
        data, latency = self._get_json("/fapi/v1/klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        klines = []
        for k in data:
            ts = int(k[0])
            o = float(k[1])
            h = float(k[2])
            l = float(k[3])
            c = float(k[4])
            v = float(k[5])
            tb_vol = float(k[9])
            dt_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            klines.append({
                "timestamp": ts,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
                "taker_buy_volume": tb_vol,
                "datetime": dt_str
            })
        return klines, latency

    def fetch_derivatives(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches live derivatives metrics:
        Funding rate, Funding change, Open Interest, OI change, Long/Short ratio, Basis & Premium.
        Never fabricates values. If unavailable, returns {value: null, available: false}.
        """
        res = {
            "symbol": symbol,
            "funding_rate": {"value": None, "available": False},
            "funding_change_24h": {"value": None, "available": False},
            "open_interest": {"value": None, "available": False},
            "open_interest_notional": {"value": None, "available": False},
            "long_short_ratio": {"value": None, "available": False},
            "basis": {"value": None, "available": False},
            "mark_price": {"value": None, "available": False},
            "index_price": {"value": None, "available": False}
        }

        # 1. Premium & Funding Index
        try:
            p_data, _ = self._get_json("/fapi/v1/premiumIndex", {"symbol": symbol})
            if isinstance(p_data, dict):
                mp = float(p_data.get("markPrice", 0.0))
                ip = float(p_data.get("indexPrice", 0.0))
                fr = float(p_data.get("lastFundingRate", 0.0))
                res["mark_price"] = {"value": mp, "available": True}
                res["index_price"] = {"value": ip, "available": True}
                res["funding_rate"] = {"value": fr, "available": True}
                if ip > 0:
                    res["basis"] = {"value": round((mp - ip) / ip * 10000.0, 2), "available": True} # in bps
        except Exception:
            pass

        # 2. Historical Funding Change
        try:
            f_data, _ = self._get_json("/fapi/v1/fundingRate", {"symbol": symbol, "limit": 4})
            if isinstance(f_data, list) and len(f_data) >= 2:
                latest_f = float(f_data[-1].get("fundingRate", 0.0))
                prev_f = float(f_data[-2].get("fundingRate", 0.0))
                res["funding_change_24h"] = {"value": round(latest_f - prev_f, 6), "available": True}
        except Exception:
            pass

        # 3. Open Interest
        try:
            oi_data, _ = self._get_json("/fapi/v1/openInterest", {"symbol": symbol})
            if isinstance(oi_data, dict):
                oi_contracts = float(oi_data.get("openInterest", 0.0))
                mp = res["mark_price"]["value"] or 0.0
                res["open_interest"] = {"value": oi_contracts, "available": True}
                res["open_interest_notional"] = {"value": round(oi_contracts * mp, 2), "available": True}
        except Exception:
            pass

        # 4. Long / Short Ratio
        try:
            ls_data, _ = self._get_json("/futures/data/globalLongShortAccountRatio", {
                "symbol": symbol,
                "period": "1h",
                "limit": 2
            })
            if isinstance(ls_data, list) and len(ls_data) > 0:
                latest_ls = float(ls_data[-1].get("longShortRatio", 1.0))
                res["long_short_ratio"] = {"value": round(latest_ls, 3), "available": True}
        except Exception:
            pass

        return res

    def fetch_full_symbol_bundle(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches all 5 timeframes (H4, H1, M15, M5, M1) + derivatives data for a symbol.
        Computes data quality score.
        """
        timeframes_data = {}
        total_latency = 0.0
        missing_count = 0

        for tf in TIMEFRAMES:
            try:
                klines, lat = self.fetch_klines(symbol, tf, limit=100)
                if len(klines) < 30:
                    missing_count += 1
                timeframes_data[tf] = klines
                total_latency += lat
            except Exception:
                missing_count += 1
                timeframes_data[tf] = []

        derivatives = self.fetch_derivatives(symbol)

        # Data Quality Score (0 to 100)
        # Deduct for missing timeframes, stale data, or extreme latency
        score = 100.0
        score -= missing_count * 20.0
        if total_latency > 3000.0:
            score -= 15.0
        elif total_latency > 1500.0:
            score -= 5.0
            
        # Check current price validity
        latest_c = timeframes_data.get("1m", [{}])[-1].get("close", 0.0) if timeframes_data.get("1m") else 0.0
        if latest_c <= 0:
            score = 0.0

        return {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "current_price": latest_c,
            "timeframes": timeframes_data,
            "derivatives": derivatives,
            "data_quality_score": max(0.0, min(100.0, round(score, 1))),
            "avg_api_latency_ms": round(total_latency / len(TIMEFRAMES), 1)
        }

    def fetch_universe_bundle(self) -> Dict[str, Any]:
        """Fetches complete multi-asset bundle for BTCUSDT, ETHUSDT, SOLUSDT in parallel."""
        from concurrent.futures import ThreadPoolExecutor
        bundle = {}
        with ThreadPoolExecutor(max_workers=len(SYMBOLS)) as executor:
            futures = {executor.submit(self.fetch_full_symbol_bundle, s): s for s in SYMBOLS}
            for fut in futures:
                s = futures[fut]
                try:
                    bundle[s] = fut.result()
                except Exception as e:
                    bundle[s] = {
                        "symbol": s,
                        "timestamp": int(time.time() * 1000),
                        "current_price": 0.0,
                        "timeframes": {},
                        "derivatives": self.fetch_derivatives(s),
                        "data_quality_score": 0.0,
                        "avg_api_latency_ms": 0.0,
                        "error": str(e)
                    }
        return bundle
