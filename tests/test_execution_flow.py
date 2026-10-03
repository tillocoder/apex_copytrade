import asyncio
import time
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from backend.binance_futures.config import DEFAULT_CONFIG
from backend.binance_futures.market_data import MarketDataManager
from backend.binance_futures.risk_manager import RiskManager
from backend.binance_futures.paper_engine import PaperTradingEngine
from backend.binance_futures.binance_connector import BinanceFuturesConnector
from backend.binance_futures.strategy_engine import ETHM5SuperTrendStrategy
from backend.binance_futures.execution_engine import ExecutionEngine

async def run_test():
    print("================================================================================")
    print("END-TO-END VERIFICATION: STRATEGY QUALIFICATION & POSITION OPENING PIPELINE")
    print("================================================================================")
    
    # 1. Initialize components exactly as in backend
    md = MarketDataManager()
    risk = RiskManager(md)
    paper = PaperTradingEngine(md)
    connector = BinanceFuturesConnector()
    strategy = ETHM5SuperTrendStrategy(md)
    executor = ExecutionEngine(connector, risk, md, paper)
    
    print("1. Config verification:")
    print(f"   Mode: {DEFAULT_CONFIG.mode}")
    print(f"   Initial Balance: ${DEFAULT_CONFIG.initial_balance_usd}")
    print(f"   Max Risk Pct: {DEFAULT_CONFIG.max_risk_pct_balance * 100}%")
    print(f"   Default Leverage: {DEFAULT_CONFIG.default_leverage}x")
    print(f"   Session Start UTC: {DEFAULT_CONFIG.session_start_hour_utc:02d}:00")
    print(f"   Session End UTC: {DEFAULT_CONFIG.session_end_hour_utc:02d}:00")
    
    # 2. Check risk pre-flight
    risk_check = risk.check_preflight_risk(has_open_position=False, is_live_mode=False)
    print(f"\n2. Pre-flight Risk check:")
    print(f"   Can Trade: {risk_check.get('can_trade')} | Reason: {risk_check.get('reason')}")
    assert risk_check.get("can_trade") == True, "Risk pre-flight failed!"
    
    # 3. Populate market data with historical candles + simulated BULL FLIP
    now_ms = int(time.time() * 1000)
    # Generate 50 H1 candles (well above 200 EMA buffer or enough for trend)
    h1_list = []
    base_price = 2500.0
    for i in range(50):
        t = now_ms - (50 - i) * 3600 * 1000
        p = base_price + i * 2.0
        h1_list.append({"time": t, "open": p, "high": p+5, "low": p-5, "close": p+2, "volume": 50000.0})
    md.klines_h1 = h1_list
    
    # Generate 30 M5 candles ending in a BULL FLIP
    m5_list = []
    for i in range(25):
        t = now_ms - (30 - i) * 300 * 1000
        p = 2580.0 - i * 1.0 # Bearish drift
        m5_list.append({"time": t, "open": p, "high": p+1, "low": p-1, "close": p-0.5, "volume": 1000.0})
        
    # Bar 26: Strong bullish expansion flip with high volume
    t_flip = now_ms - 5 * 300 * 1000
    p_flip = 2650.0
    m5_list.append({"time": t_flip, "open": 2560.0, "high": 2660.0, "low": 2555.0, "close": 2650.0, "volume": 5000.0}) # 5x volume
    
    md.klines_m5 = m5_list
    md.current_price = 2650.0
    md.mark_price = 2650.0
    md.best_bid = 2649.99
    md.best_ask = 2650.01
    md.spread = 0.02
    
    DEFAULT_CONFIG.session_start_hour_utc = 0
    DEFAULT_CONFIG.session_end_hour_utc = 24

    # 4. Evaluate strategy
    print(f"\n3. Evaluating Strategy on simulated setup...")
    signal_res = strategy.evaluate_setup(risk_check, is_closed_bar=True)
    print(f"   Final Signal : {signal_res.get('final_signal')}")
    print(f"   Score        : {signal_res.get('score')}")
    print(f"   Reason       : {signal_res.get('reason')}")
    print(f"   SL           : ${signal_res.get('sl')}")
    print(f"   TP1          : ${signal_res.get('tp1')}")
    print(f"   TP2          : ${signal_res.get('tp2')}")
    print(f"   R Distance   : ${signal_res.get('r_distance')}")
    
    # 5. Test Execution Engine
    print(f"\n4. Triggering Execution Engine...")
    exec_res = await executor.execute_signal(signal_res, is_live_mode=False)
    print(f"   Execution Status : {exec_res.get('status')}")
    if exec_res.get("status") != "FILLED":
        print(f"   ❌ REJECTION REASON: {exec_res.get('reason')}")
    else:
        print(f"   ✅ POSITION OPENED SUCCESSFULLY!")
        print(f"      Side: {exec_res.get('side')} | Qty: {exec_res.get('qty')} ETH | Margin: ${exec_res.get('margin')}")
        print(f"      Entry: ${exec_res.get('entry_price')} | SL: ${exec_res.get('sl')} | TP: ${exec_res.get('tp1')}")
        
        # 6. Verify Paper Engine has active position
        assert paper.current_position is not None, "Paper engine current_position is None!"
        print(f"\n5. Active Position State:")
        print(f"   Symbol: {paper.current_position['symbol']}")
        print(f"   Qty: {paper.current_position['qty']}")
        print(f"   Unrealized PnL: ${paper.current_position['unrealizedPnl']}")
        
        # 7. Simulate Price Tick moving to TP
        tp_target = exec_res.get("tp1")
        print(f"\n6. Simulating price reaching TP target (${tp_target})...")
        md.mark_price = tp_target + 1.0
        closed_trade = paper.update_price_tick()
        if closed_trade:
            print(f"   ✅ TRADE CLOSED ON TAKE PROFIT!")
            print(f"      PnL: ${closed_trade['pnl']:+.2f} | Reason: {closed_trade['close_reason']}")
            print(f"      New Balance: ${paper.balance:.2f}")

    # =========================================================================
    # PART B: TEST SHORT SETUP & EXECUTION
    # =========================================================================
    print("\n--------------------------------------------------------------------------------")
    print("TESTING SHORT SETUP & EXECUTION PIPELINE")
    print("--------------------------------------------------------------------------------")
    
    # Generate Bearish H1 trend
    h1_list_short = []
    base_price = 2800.0
    for i in range(50):
        t = now_ms - (50 - i) * 3600 * 1000
        p = base_price - i * 2.0
        h1_list_short.append({"time": t, "open": p, "high": p+5, "low": p-5, "close": p-2, "volume": 50000.0})
    md.klines_h1 = h1_list_short
    
    # Generate M5 candles ending in a BEAR FLIP
    m5_list_short = []
    for i in range(25):
        t = now_ms - (30 - i) * 300 * 1000
        p = 2650.0 + i * 1.0 # Bullish drift
        m5_list_short.append({"time": t, "open": p, "high": p+1, "low": p-1, "close": p+0.5, "volume": 1000.0})
        
    t_flip_s = now_ms - 2 * 300 * 1000
    m5_list_short.append({"time": t_flip_s, "open": 2720.0, "high": 2725.0, "low": 2640.0, "close": 2645.0, "volume": 6000.0})
    
    md.klines_m5 = m5_list_short
    md.current_price = 2645.0
    md.mark_price = 2645.0
    md.best_bid = 2644.99
    md.best_ask = 2645.01
    
    risk_check_short = risk.check_preflight_risk(has_open_position=False, is_live_mode=False)
    signal_short = strategy.evaluate_setup(risk_check_short, is_closed_bar=True)
    print(f"   Final Signal : {signal_short.get('final_signal')}")
    print(f"   Reason       : {signal_short.get('reason')}")
    print(f"   SL           : ${signal_short.get('sl')}")
    print(f"   TP1          : ${signal_short.get('tp1')}")
    print(f"   R Distance   : ${signal_short.get('r_distance')}")
    
    exec_res_short = await executor.execute_signal(signal_short, is_live_mode=False)
    print(f"   Execution Status : {exec_res_short.get('status')}")
    assert exec_res_short.get("status") == "FILLED", f"SHORT execution failed: {exec_res_short}"
    print(f"   ✅ SHORT POSITION OPENED SUCCESSFULLY!")
    print(f"      Side: {exec_res_short.get('side')} | Qty: {exec_res_short.get('qty')} ETH | Margin: ${exec_res_short.get('margin')}")
    print(f"      Entry: ${exec_res_short.get('entry_price')} | SL: ${exec_res_short.get('sl')} | TP: ${exec_res_short.get('tp1')}")

if __name__ == "__main__":
    asyncio.run(run_test())
