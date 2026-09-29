import sys
sys.path.insert(0, r'C:\apex_copytrade')
from run_v32_forensic_suite import run_simulation_v32_fast, precalculate_all_features
import csv

raw = []
with open(r'c:\apex_copytrade\data\binance_ethusdt_m1_90d.csv') as f:
    for r in csv.DictReader(f):
        raw.append({k: float(v) if k != 'time' else int(v) for k, v in r.items()})

feat = precalculate_all_features(raw)
idx_val = int(len(feat) * 0.8)

# Get the exact 197 trades of Candidate A
res_a = run_simulation_v32_fast(feat, score_threshold=80, exit_model='G', session_mode='MAJOR_ONLY')
trades_a = res_a['trades']

print(f"Candidate A: {len(trades_a)} trades, Net PF = {res_a['net_pf']}, Net PnL = ${res_a['net_pnl']}, Fees = ${res_a['total_fees']}")

# Let's inspect the fill rate on next bar for these exact 197 trades!
# For each trade, find the entry candle index in feat
filled_as_maker_count = 0
maker_fills = []

for tr in trades_a:
    # Match by timestamp
    ts = tr['timestamp']
    entry_price = tr['entry']
    side = tr['side']
    
    # Find matching candle
    matched_idx = -1
    for i in range(250, len(feat)):
        c_ts = sys.modules['datetime'].datetime.fromtimestamp(feat[i]['time'] / 1000, tz=sys.modules['datetime'].timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        if c_ts == ts:
            matched_idx = i
            break
            
    if matched_idx != -1 and matched_idx + 1 < len(feat):
        next_c = feat[matched_idx + 1]
        # In Candidate A: entry was close + 0.01 (taker market)
        # Limit price would be close of candle matched_idx
        limit_px = feat[matched_idx]['close']
        
        # Check if next candle trades strictly through limit price (1 tick adverse)
        if side == 'LONG':
            maker_filled = (next_c['low'] <= limit_px - 0.01)
        else:
            maker_filled = (next_c['high'] >= limit_px + 0.01)
            
        if maker_filled:
            filled_as_maker_count += 1
            maker_fills.append(True)
        else:
            maker_fills.append(False)
    else:
        maker_fills.append(False)

print(f"Maker fill rate on next bar for Cand A entries: {filled_as_maker_count} / {len(trades_a)} ({filled_as_maker_count/len(trades_a)*100:.1f}%)")

# Now let's calculate what happens to fees and PnL if:
# 1. Maker Hybrid: 85% of trades enter as Maker (0.02% fee instead of 0.05%), remaining 15% enter as Taker (0.05%)
saved_fees = 0.0
for i, tr in enumerate(trades_a):
    notional = tr['notional']
    if maker_fills[i]:
        # Taker entry fee was notional * 0.0005
        # Maker entry fee is notional * 0.0002
        saved = notional * (0.0005 - 0.0002)
        saved_fees += saved

print(f"Fee savings from Maker Hybrid on Cand A: ${saved_fees:.2f}")
new_fees = res_a['total_fees'] - saved_fees
new_pnl = res_a['net_pnl'] + saved_fees
print(f"New Net PnL with Maker Hybrid: ${new_pnl:.2f} (from ${res_a['net_pnl']:.2f})")
print(f"New Fee drag: {new_fees / res_a['gross_profit'] * 100:.1f}% (from {res_a['total_fees'] / res_a['gross_profit'] * 100:.1f}%)")
