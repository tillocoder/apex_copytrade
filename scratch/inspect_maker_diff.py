import sys
sys.path.insert(0, r'C:\apex_copytrade')
import csv
from scratch.test_v33_features import feat_v33, precalculate_all_features

# Let's check:
# In ALL_TAKER, when an order enters at bar idx, what is exec_price?
# exec_price = round(curr_price + 0.01, 2)
# And what was target and sl?
# In Base Full:
# target = round(curr_price + vol_mult * r_dist, 2)
# sl = round(max(max_sl, min(raw_sl, min_sl)), 2)

# Why did MAKER have 447 trades?
# In MAKER:
# pending_maker = {'side': cand_side, 'limit': exec_price, 'idx': i, 'pos': pos_info}
# At next bar i+1:
# if f['low'] <= plim - 0.01:
#    filled = True
#    in_pos = True
#    pos['entry_idx'] = i
# NOTICE THIS: pos['entry_idx'] was set to i (which was the previous bar)!
# BUT wait! When pos was filled at bar i+1:
# Did it exit at bar i+1?
# In sim_test:
# Look at the order of code in sim_test:
# 1. Maker fill check:
#    if filled:
#       in_pos = True
# 2. Active position management:
#    if in_pos: ...
# Because 'if in_pos:' comes AFTER 'Maker fill check' IN THE SAME BAR LOOP,
# bar i+1 IMMEDIATELY checked:
# sl_touch = (low <= sl)
# tp_touch = (high >= target)
# On bar i+1, price touched plim - 0.01. But was sl also touched on bar i+1?
# Let's check!
print("Done writing inspect script.")
