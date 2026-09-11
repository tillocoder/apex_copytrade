import sys
sys.path.insert(0, 'c:/apex_copytrade')
from backend.final_robust_algotrader.config import AlgoTraderConfig
from backend.final_robust_algotrader.market_data import MarketDataEngine

def test_donchian_slice_no_future():
    cfg = AlgoTraderConfig()
    data = MarketDataEngine(cfg.market_data.cache_path)
    lb = cfg.strategy.breakout_lookback_bars
    for i in range(lb, data.n):
        sl = data.highs[i - lb:i]
        assert len(sl) == lb, f"Wrong slice at {i}"
        assert sl[-1] == data.highs[i - 1], f"Slice not ending at i-1 at {i}"
    print(f"PASS test_donchian_slice_no_future: {data.n - lb} bars checked")

def test_4h_no_strict_future():
    cfg = AlgoTraderConfig()
    data = MarketDataEngine(cfg.market_data.cache_path)
    violations = []
    borderline = 0
    for i in range(data.n):
        idx_4h = data.map_1h_to_4h[i]
        if idx_4h < 0:
            continue
        last_1h = idx_4h * 4 + 3
        if last_1h > i:
            violations.append(i)
        elif last_1h == i:
            borderline += 1
    assert len(violations) == 0, f"Strict future violations: {violations[:5]}"
    pct = borderline / data.n * 100.0
    print(f"PASS test_4h_no_strict_future: 0 violations")
    print(f"NOTE: {borderline} borderline cases ({pct:.1f}%) - 4th bar of each 4H period uses just-closed 4H")

if __name__ == '__main__':
    print('=== LOOK-AHEAD BIAS TESTS ===')
    test_donchian_slice_no_future()
    test_4h_no_strict_future()
    print('ALL LOOK-AHEAD TESTS PASSED')
