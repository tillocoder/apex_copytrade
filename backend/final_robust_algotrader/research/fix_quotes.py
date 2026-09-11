with open('C:/apex_copytrade/backend/final_robust_algotrader/research/tournament_engine.py', 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace("\\\\'", "'")
with open('C:/apex_copytrade/backend/final_robust_algotrader/research/tournament_engine.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Fixed')
