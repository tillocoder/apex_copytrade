#!/usr/bin/env python3
"""
Microstructure & Friction Barrier Diagnostic on 2 Years of Binance Futures Data
"""
import json
import math

with open("backend/data/klines_ethusdt_5m_2y.json", "r") as f:
    eth_m5 = json.load(f)
with open("backend/data/klines_btcusdt_5m_2y.json", "r") as f:
    btc_m5 = json.load(f)

def analyze_friction(candles, name):
    n = len(candles)
    ranges_pct = [((c["high"] - c["low"]) / c["open"]) * 100.0 for c in candles]
    avg_range_pct = sum(ranges_pct) / n
    median_range_pct = sorted(ranges_pct)[n // 2]
    
    # Round trip taker + slippage:
    # 0.05% taker entry + 0.05% taker exit + 0.05% entry slip + 0.05% exit slip = 0.20%
    round_trip_friction_pct = 0.20
    friction_share_of_candle = (round_trip_friction_pct / avg_range_pct) * 100.0
    
    # Aggregate to M15 and H1
    # M15
    m15_ranges = []
    for i in range(0, n - 2, 3):
        h = max(candles[i]["high"], candles[i+1]["high"], candles[i+2]["high"])
        l = min(candles[i]["low"], candles[i+1]["low"], candles[i+2]["low"])
        o = candles[i]["open"]
        m15_ranges.append(((h - l) / o) * 100.0)
    avg_m15_range = sum(m15_ranges) / len(m15_ranges)
    friction_share_m15 = (round_trip_friction_pct / avg_m15_range) * 100.0

    # H1
    h1_ranges = []
    for i in range(0, n - 11, 12):
        h = max(c["high"] for c in candles[i:i+12])
        l = min(c["low"] for c in candles[i:i+12])
        o = candles[i]["open"]
        h1_ranges.append(((h - l) / o) * 100.0)
    avg_h1_range = sum(h1_ranges) / len(h1_ranges)
    friction_share_h1 = (round_trip_friction_pct / avg_h1_range) * 100.0

    print(f"=== {name} MICROSTRUCTURE & FRICTION AUDIT (2 YEARS) ===")
    print(f"Total M5 Candles: {n}")
    print(f"M5 Avg Candle Range: {avg_range_pct:.3f}% (Median: {median_range_pct:.3f}%)")
    print(f"  -> Round-Trip Friction (0.20%): consumes {friction_share_of_candle:.1f}% of the entire M5 candle!")
    print(f"M15 Avg Candle Range: {avg_m15_range:.3f}%")
    print(f"  -> Round-Trip Friction (0.20%): consumes {friction_share_m15:.1f}% of M15 candle")
    print(f"H1 Avg Candle Range: {avg_h1_range:.3f}%")
    print(f"  -> Round-Trip Friction (0.20%): consumes {friction_share_h1:.1f}% of H1 candle")
    print()

analyze_friction(eth_m5, "ETHUSDT")
analyze_friction(btc_m5, "BTCUSDT")
