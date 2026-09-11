import json
DATA_PATH = 'c:/apex_copytrade/backend/data/btc_1y_klines_cache.json'
HOUR_MS = 3600 * 1000

def load():
    with open(DATA_PATH) as f:
        return json.load(f)

def test_candle_count():
    d = load()
    assert len(d) == 8760, f"Expected 8760, got {len(d)}"
    print(f"PASS test_candle_count: {len(d)}")

def test_no_duplicates():
    d = load()
    ts = [c[0] for c in d]
    dupes = len(ts) - len(set(ts))
    assert dupes == 0, f"Dupes: {dupes}"
    print("PASS test_no_duplicates: 0 duplicates")

def test_ordering():
    d = load()
    ts = [c[0] for c in d]
    ooo = sum(1 for i in range(1,len(ts)) if ts[i]<=ts[i-1])
    assert ooo == 0
    print("PASS test_ordering")

def test_intervals():
    d = load()
    ts = [c[0] for c in d]
    gaps = [(i, ts[i]-ts[i-1]) for i in range(1,len(ts)) if ts[i]-ts[i-1] != HOUR_MS]
    assert len(gaps)==0, f"Gaps: {gaps[:3]}"
    print("PASS test_intervals: all 1H")

def test_ohlc():
    d = load()
    bad = 0
    for c in d:
        o,h,l,cl = float(c[1]),float(c[2]),float(c[3]),float(c[4])
        if h < max(o,cl) or l > min(o,cl) or h < l:
            bad += 1
    assert bad == 0, f"Invalid OHLC: {bad}"
    print("PASS test_ohlc")

def test_volume():
    d = load()
    z = sum(1 for c in d if float(c[5])<=0)
    assert z == 0
    print("PASS test_volume")

if __name__ == '__main__':
    print('=== DATA QUALITY TESTS ===')
    test_candle_count()
    test_no_duplicates()
    test_ordering()
    test_intervals()
    test_ohlc()
    test_volume()
    print('ALL DATA QUALITY TESTS PASSED')
