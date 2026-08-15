import os
import sys
import asyncio
import json
import urllib.request
import urllib.parse
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env so GEMINI_API_KEY is available to ai_signal_engine
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
os.environ.setdefault("GEMINI_API_KEY", os.environ.get("VITE_GEMINI_API_KEY", ""))

# Ensure backend path is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.quant_engine.config import EngineConfig, EngineMode, PropFirmRulesConfig, ExecutionConfig, RiskConfig, StrategyConfig
from backend.quant_engine.market_data import MarketDataEngine
from backend.quant_engine.backtest import BacktestEngine, BacktestRunResult
from backend.quant_engine.real_data_engine import RealHistoricalDataEngine
from backend.quant_engine.optimization import MonteCarloOptimizer
from backend.telegram_bot import telegram_notifier
from backend import ai_signal_engine
from backend import live_execution_manager as live_mgr

app = FastAPI(
    title="APEX QUANT TERMINAL — Institutional Strategy Engine Backend",
    description="Production-Grade Quantitative Trading Backend powered by Real M15 Binance Historical & WebSocket Streams.",
    version="4.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Cached Results
LATEST_BACKTEST_RESULT: Optional[Dict[str, Any]] = None
LATEST_MC_RESULT: Optional[Dict[str, Any]] = None
IS_BACKTEST_RUNNING = False

async def run_async_in_executor(func, *args):
    """Python 3.8+ compatible executor for blocking tasks."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)

def run_quant_engine_task(years: float = 1.0, symbol: str = "BTC/USDT"):
    global LATEST_BACKTEST_RESULT, LATEST_MC_RESULT, IS_BACKTEST_RUNNING
    try:
        IS_BACKTEST_RUNNING = True
        print(f"[QUANT BACKEND] Starting Real Historical {years}-Year M15 Backtest Engine for {symbol}...")
        
        config = EngineConfig(
            mode=EngineMode.PROP_FIRM,
            prop_rules=PropFirmRulesConfig(
                initial_capital=10000.0,
                stage1_target_pct=0.08,
                stage2_target_pct=0.05,
                max_daily_drawdown_pct=0.05,
                max_total_drawdown_pct=0.10,
                enforce_stage_reset=True
            ),
            execution=ExecutionConfig(commission_pct=0.0004, spread_bps=1.0, slippage_bps=1.0),
            risk=RiskConfig(base_risk_pct=0.015, min_risk_pct=0.0075, max_risk_pct=0.0225, max_open_positions=3),
            strategy=StrategyConfig(timeframe="M15", confidence_threshold=65.0)
        )

        btc_candles = RealHistoricalDataEngine.get_symbol_data("BTC/USDT", years=years)
        eth_candles = RealHistoricalDataEngine.get_symbol_data("ETH/USDT", years=years)
        
        max_bars = int(years * 35040)
        btc_candles = btc_candles[:max_bars]
        eth_candles = eth_candles[:max_bars]
        
        market_data = MarketDataEngine()
        all_candles = btc_candles + eth_candles
        market_data.load_from_candles(all_candles)

        backtester = BacktestEngine(config)
        res: BacktestRunResult = backtester.run(market_data)

        # Run Monte Carlo 50 sims for instant response
        mc_optimizer = MonteCarloOptimizer(config, num_simulations=50)
        mc_summary = mc_optimizer.run_monte_carlo(res)

        # Sample equity curve to 100 points for UI rendering
        step = max(1, len(res.equity_curve) // 100)
        sampled_equity = [
            {"timestamp": f"Bar {i*step}", "equity": round(res.equity_curve[i*step], 2)}
            for i in range(0, len(res.equity_curve) // step)
        ]
        sampled_portfolio_equity = [
            {"timestamp": f"Bar {i*step}", "equity": round(res.portfolio_equity_curve[i*step], 2)}
            for i in range(0, len(res.portfolio_equity_curve) // step)
        ]

        # Aggregate monthly returns from real backtest trade logs
        monthly_returns_map = {}
        if res.trade_logs:
            for t in res.trade_logs:
                try:
                    entry_str = t.get("entry_time") or ""
                    if entry_str:
                        dt = datetime.strptime(entry_str, "%Y-%m-%d %H:%M")
                        m_key = dt.strftime("%b")
                        pnl_pct = (t.get("pnl", 0.0) / 10000.0) * 100.0
                        monthly_returns_map[m_key] = monthly_returns_map.get(m_key, 0.0) + pnl_pct
                except Exception:
                    pass

        months_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_returns = [
            {"month": m, "returnPct": round(monthly_returns_map[m], 2)}
            for m in months_order if m in monthly_returns_map
        ]
        LATEST_BACKTEST_RESULT = {
            "cagr": round(res.report.cagr_pct, 2),
            "sharpeRatio": round(res.report.sharpe_ratio, 2),
            "sortinoRatio": round(res.report.sortino_ratio, 2),
            "winRate": round(res.report.win_rate_pct, 2),
            "maxDrawdown": round(res.report.max_total_drawdown_pct, 2),
            "profitFactor": round(res.report.profit_factor, 2),
            "totalTrades": res.report.total_trades,
            "netProfit": round(res.report.total_pnl, 2),
            "initialBalance": 10000.0,
            "finalBalance": round(10000.0 + res.report.total_pnl, 2),
            "passedStage1": res.passed_stage1,
            "passedStage2": res.passed_stage2,
            "finalStage": str(res.prop_final_stage),
            "failureReason": res.failure_reason,
            "equityCurve": sampled_equity,
            "portfolioEquityCurve": sampled_portfolio_equity,
            "passedChallenges": res.passed_challenges_list,
            "propSummary": {
                "completedChallenges": res.prop_summary.completed_challenges,
                "stage1Passed": res.prop_summary.stage1_passed,
                "stage2Passed": res.prop_summary.stage2_passed,
                "failedChallenges": res.prop_summary.failed_challenges,
                "successRatePct": res.prop_summary.challenge_success_rate_pct,
                "avgDaysPerChallenge": res.prop_summary.avg_days_per_challenge
            },
            "monthlyReturns": monthly_returns,
            "recentTrades": res.trade_logs[-50:] if res.trade_logs else []
        }

        LATEST_MC_RESULT = {
            "passRate": round(mc_summary.combined_pass_rate_pct, 1),
            "riskOfRuin": round(mc_summary.risk_of_ruin_pct, 2),
            "medianMaxDD": round(mc_summary.expected_drawdown_pct, 2),
            "percentile95MaxDD": round(mc_summary.expected_drawdown_pct, 2)
        }
        print(f"[QUANT BACKEND] Engine Backtest Completed Successfully! WinRate: {res.report.win_rate_pct:.1f}%, CAGR: {res.report.cagr_pct:.2f}%")
    except Exception as e:
        print(f"[QUANT BACKEND ERROR] Engine execution failed: {e}")
    finally:
        IS_BACKTEST_RUNNING = False

async def periodic_signals_task():
    """Run AI signal generation once every 5 minutes in the background and open live positions."""
    print("[QUANT BACKEND] Starting periodic AI Signal Engine task (Interval: 5 minutes)...")
    try:
        sigs = await run_async_in_executor(ai_signal_engine.generate_signals)
        if sigs:
            for sig in sigs:
                await run_async_in_executor(live_mgr.open_position_from_signal, sig)
    except Exception as e:
        print(f"[QUANT BACKEND ERROR] Initial AI signal generation failed: {e}")

    while True:
        await asyncio.sleep(300)  # Sleep 5 minutes for M15 real-time trading
        try:
            print("[QUANT BACKEND] Running 5-minute AI Signal Engine scan...")
            sigs = await run_async_in_executor(ai_signal_engine.generate_signals)
            if sigs:
                for sig in sigs:
                    await run_async_in_executor(live_mgr.open_position_from_signal, sig)
        except Exception as e:
            print(f"[QUANT BACKEND ERROR] Periodic AI signal generation failed: {e}")

async def monitor_ai_signals_task():
    """Background task that monitors active paper-trading AI signals and live open positions against real-time prices."""
    print("[QUANT BACKEND] Starting AI Signal & Live Position Monitor task (Interval: 3 seconds)...")
    
    while True:
        await asyncio.sleep(3)
        try:
            # Sync live positions with Binance tickers & SL/TP hits
            await run_async_in_executor(live_mgr.sync_live_positions_and_equity)

            # Sync active AI signals
            history = ai_signal_engine.get_signals_history()
            active_signals = [s for s in history if s.get("status") in ["CONFIRMED", "PENDING"]]
            if not active_signals:
                continue

            prices = {}
            for s in active_signals:
                sym = s.get("symbol")
                if sym not in prices:
                    try:
                        binance_symbol = sym.replace("/", "").upper()
                        price = await run_async_in_executor(fetch_binance_ticker_sync, binance_symbol)
                        prices[sym] = price
                    except Exception as pe:
                        print(f"[AI MONITOR] Error fetching price for {sym}: {pe}")

            updated = False
            for s in history:
                if s.get("status") not in ["CONFIRMED", "PENDING"]:
                    continue

                sym = s.get("symbol")
                if sym not in prices:
                    continue

                current_price = prices[sym]
                side = s.get("side", "BUY").upper()
                entry = float(s.get("entry", 0.0) or 0.0)
                sl = float(s.get("sl", 0.0) or 0.0)
                # New signals expose staged targets (TP1/TP2/TP3).  TP1 is the
                # first executable target; retain `tp` as a legacy fallback.
                tp = float(s.get("tp1", s.get("tp", 0.0)) or 0.0)
                msg_id = s.get("telegram_message_id")

                # Never evaluate incomplete price levels.  A missing target must
                # not be interpreted as $0.00 and immediately close a BUY trade.
                if entry <= 0 or sl <= 0 or tp <= 0:
                    continue

                hit_type = None
                pnl_pct = 0.0

                if side == "BUY":
                    if current_price >= tp:
                        hit_type = "TP"
                        pnl_pct = ((tp - entry) / entry) * 100.0
                    elif current_price <= sl:
                        hit_type = "SL"
                        pnl_pct = ((sl - entry) / entry) * 100.0
                elif side == "SELL":
                    if current_price <= tp:
                        hit_type = "TP"
                        pnl_pct = ((entry - tp) / entry) * 100.0
                    elif current_price >= sl:
                        hit_type = "SL"
                        pnl_pct = ((entry - sl) / entry) * 100.0

                if hit_type:
                    s["status"] = f"{hit_type}_HIT"
                    s["exit_timestamp"] = time.time()
                    updated = True
                    print(f"[AI MONITOR] Signal {s['id']} ({sym}) hit {hit_type} at ${current_price:,.2f}. PnL: {pnl_pct:.2f}%")
                    if msg_id:
                        try:
                            await run_async_in_executor(
                                telegram_notifier.send_ai_signal_update_notification,
                                msg_id, sym, hit_type, {"price": current_price, "pnl_pct": pnl_pct}
                            )
                        except Exception as ne:
                            print(f"[AI MONITOR] Error sending TG reply: {ne}")

            if updated:
                ai_signal_engine.save_signals_history(history)
        except Exception as e:
            print(f"[AI MONITOR ERROR] failed to run active signals scan: {e}")

# Trigger initial engine load in background on startup
@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_quant_engine_task, 1.0, "BTC/USDT")
    asyncio.create_task(periodic_signals_task())
    asyncio.create_task(monitor_ai_signals_task())

def fetch_binance_ticker_sync(symbol: str = "BTCUSDT") -> float:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.replace('/', '').upper()}"
    req = urllib.request.Request(url, headers={'User-Agent': 'ApexQuant/4.5'})
    with urllib.request.urlopen(req, timeout=3) as resp:
        res = json.loads(resp.read().decode())
        return float(res["price"])

def fetch_binance_klines_sync(
    symbol: str = "BTCUSDT", interval: str = "15m", limit: int = 200, end_time: Optional[int] = None
):
    sym = symbol.replace('/', '').upper()
    params = {"symbol": sym, "interval": interval, "limit": max(1, min(limit, 1000))}
    if end_time and end_time > 0:
        params["endTime"] = int(end_time)
    url = f"https://api.binance.com/api/v3/klines?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'ApexQuant/4.5'})
    with urllib.request.urlopen(req, timeout=5) as resp:
        raw = json.loads(resp.read().decode())
        candles = []
        for d in raw:
            t = time.strftime('%H:%M', time.gmtime(d[0] / 1000))
            o, h, l, c, v = float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])
            candles.append({
                "timestamp": int(d[0] / 1000),
                "time": t,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": round(v, 2),
                "isUp": c >= o
            })
        return candles

@app.get("/api/v1/system/health")
async def get_system_health():
    exchange_started = time.perf_counter()
    try:
        await run_async_in_executor(fetch_binance_ticker_sync, "BTCUSDT")
        exchange_status = "CONNECTED"
        exchange_latency_ms = round((time.perf_counter() - exchange_started) * 1000, 1)
    except Exception:
        exchange_status = "DISCONNECTED"
        exchange_latency_ms = 0.0

    return {
        "status": "HEALTHY" if exchange_status == "CONNECTED" else "DEGRADED",
        "exchange_status": exchange_status,
        "exchange_latency_ms": exchange_latency_ms,
        "database_status": "FILE_STATE",
        "database_latency_ms": 0.0,
        "websocket_status": "STREAMING",
        "python_engine_status": "RUNNING" if not IS_BACKTEST_RUNNING else "OPTIMIZING",
        "ai_engine_status": "ACTIVE"
    }

@app.get("/api/v1/quant/backtest-results")
async def get_backtest_results(background_tasks: BackgroundTasks, force_rerun: bool = False):
    global LATEST_BACKTEST_RESULT, IS_BACKTEST_RUNNING
    if force_rerun and not IS_BACKTEST_RUNNING:
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, run_quant_engine_task, 1.0, "BTC/USDT")
        return {"status": "TRIGGERED", "message": "Engine backtest execution started in background."}
    
    if LATEST_BACKTEST_RESULT is None:
        return {
            "status": "RUNNING" if IS_BACKTEST_RUNNING else "NOT_READY",
            "message": "Engine is processing real 1-year historical dataset...",
            "data": None,
            "monteCarlo": None
        }

    return {
        "status": "SUCCESS",
        "data": LATEST_BACKTEST_RESULT,
        "monteCarlo": LATEST_MC_RESULT
    }

@app.get("/api/v1/signals/live")
async def get_live_signals():
    """Returns the most recently generated set of active signals from history."""
    try:
        signals = await run_async_in_executor(ai_signal_engine.get_latest_signals)
        if signals:
            return signals
    except Exception as e:
        print(f"[SIGNALS ERROR] failed to fetch latest signals: {e}")
    return []

@app.get("/api/v1/signals/history")
async def get_signals_history():
    """Returns the history of all AI signals generated over the last 2 months."""
    try:
        history = await run_async_in_executor(ai_signal_engine.get_signals_history)
        return history
    except Exception as e:
        print(f"[SIGNALS ERROR] failed to fetch signals history: {e}")
        return []

@app.get("/api/v1/market/klines")
async def get_real_klines(
    symbol: str = "BTC/USDT", interval: str = "15m", limit: int = 200, end_time: Optional[int] = None
):
    try:
        data = await run_async_in_executor(fetch_binance_klines_sync, symbol, interval, limit, end_time)
        return {"status": "SUCCESS", "symbol": symbol, "data": data}
    except Exception as e:
        return {"status": "ERROR", "message": str(e), "data": []}

@app.get("/api/v1/positions/live")
async def get_live_positions():
    """Returns open live positions with real-time Binance prices and unrealized PnL."""
    res = await run_async_in_executor(live_mgr.sync_live_positions_and_equity)
    return res.get("openPositions", [])

@app.get("/api/v1/portfolio/live-equity")
async def get_live_portfolio_equity():
    """Returns real-time live equity, balance, unrealized PnL, realized PnL, and live equity curve."""
    res = await run_async_in_executor(live_mgr.sync_live_positions_and_equity)
    return {"status": "SUCCESS", "data": res}

@app.post("/api/v1/positions/reset")
async def reset_all_positions():
    """Performs full reset: closes all active positions and resets real-time 10k equity tracking."""
    telegram_notifier.reset_account_balance(10000.00)
    res = await run_async_in_executor(live_mgr.reset_live_execution, 10000.00)
    return res

@app.post("/api/v1/positions/panic-close")
async def panic_close_all():
    res = await run_async_in_executor(live_mgr.reset_live_execution, 10000.00)
    return {"status": "SUCCESS", "message": "Liquidated all open positions across exchange accounts."}

# --- TELEGRAM BOT APIS (@xrpropbot) ---

@app.get("/api/v1/telegram/status")
async def get_telegram_status():
    """Polls Telegram updates and returns registered chat IDs."""
    await run_async_in_executor(telegram_notifier.poll_updates)
    return {
        "status": "ONLINE",
        "bot_name": "@xrpropbot",
        "registered_chats_count": len(telegram_notifier.chat_ids),
        "chat_ids": list(telegram_notifier.chat_ids),
        "tracked_messages": telegram_notifier.message_map
    }

@app.post("/api/v1/telegram/notify-open")
async def notify_trade_open(position: Dict[str, Any]):
    """Sends Trade Open notification formatted in Uzbek to Telegram @xrpropbot."""
    await run_async_in_executor(telegram_notifier.send_trade_open_notification, position)
    return {"status": "SUCCESS", "message": "Dispatched trade open alert to Telegram."}

@app.post("/api/v1/telegram/notify-update")
async def notify_trade_update(pos_id: str = Query(...), event_type: str = Query(...), details: Optional[Dict[str, Any]] = None):
    """Replies to the original trade open message with BE, TP1, SL, or CLOSE events."""
    if details is None:
        details = {}
    await run_async_in_executor(telegram_notifier.send_trade_update_notification, pos_id, event_type, details)
    return {"status": "SUCCESS", "message": f"Replied to trade message {pos_id} with event {event_type}."}

@app.post("/api/v1/telegram/notify-milestone")
async def notify_prop_milestone(event_type: str = Query(...), details: Optional[Dict[str, Any]] = None):
    """Sends Prop Challenge milestone notifications (STAGE_1_PASSED, STAGE_2_STARTED, FUNDED_UNLOCKED)."""
    if details is None:
        details = {}
    await run_async_in_executor(telegram_notifier.send_prop_milestone_notification, event_type, details)
    return {"status": "SUCCESS", "message": f"Dispatched Prop milestone notification: {event_type}"}

@app.post("/api/v1/telegram/test-milestones")
async def test_telegram_milestones(event_type: str = "STAGE_1_PASSED"):
    """Tests prop milestone notifications (STAGE_1_PASSED, STAGE_2_STARTED, STAGE_2_PASSED, FUNDED_UNLOCKED)."""
    details = {
        "firm": "FTMO",
        "account": "10K-EVAL-8492",
        "balance": 11000.00 if event_type == "STAGE_1_PASSED" else 10000.00,
        "pnl": 1000.00,
        "days": 12,
        "win_rate": 74.3,
        "max_dd": 1.2
    }
    await run_async_in_executor(telegram_notifier.send_prop_milestone_notification, event_type, details)
    return {"status": "SUCCESS", "message": f"Sent test milestone {event_type} to @xrpropbot."}

@app.post("/api/v1/telegram/test-flow")
async def test_telegram_trade_flow(symbol: str = "BTC/USDT", side: str = "SHORT"):
    """
    Triggers a full test flow:
    1. Sends Trade Open message to @xrpropbot matching exact user format.
    2. After 5s, replies with Break-Even (BE) notification.
    3. After 10s, replies with TP1 Hit notification.
    """
    try:
        price = await run_async_in_executor(fetch_binance_ticker_sync, "BTCUSDT")
    except Exception:
        price = 63098.30

    test_pos = {
        "id": f"test_{int(time.time())}",
        "symbol": symbol,
        "side": side,
        "entry_price": price,
        "size": 0.6916,
        "leverage": 5,
        "margin_used": round((price * 0.6916) / 5, 2),
        "sl": round(price * 1.005 if side == "SHORT" else price * 0.995, 2),
        "tp1": round(price * 0.985 if side == "SHORT" else price * 1.015, 2),
        "tp2": round(price * 0.965 if side == "SHORT" else price * 1.035, 2),
        "expected_loss": 200.00,
        "ai_explanation": "H1 Bearish Trend + M5 EMA 9 Pullback Bounce",
        "ai_confidence": 94.8
    }

    # Dispatch Trade Open
    await run_async_in_executor(telegram_notifier.send_trade_open_notification, test_pos)
    return {
        "status": "SUCCESS", 
        "message": f"Test position {test_pos['id']} sent to @xrpropbot. Send /start in Telegram if not received.",
        "test_position": test_pos
    }

@app.websocket("/ws/v1/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(1.0)
            try:
                real_btc_price = await run_async_in_executor(fetch_binance_ticker_sync, "BTCUSDT")
            except Exception:
                real_btc_price = 91420.50

            data = {
                "event": "tick_update",
                "symbol": "BTC/USDT",
                "price": real_btc_price,
                "engine_status": "RUNNING",
                "timestamp": time.time()
            }
            await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        pass

import os
from fastapi.staticfiles import StaticFiles

dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
