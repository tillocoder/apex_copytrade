import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from pydantic import BaseModel

from .config import DEFAULT_CONFIG
from .database import init_futures_tables, get_trades, get_session_stats
from .binance_connector import BinanceFuturesConnector, run_in_thread
from .market_data import MarketDataManager
from .paper_engine import PaperTradingEngine
from .risk_manager import RiskManager
from .strategy_engine import ETHM1ScalpingStrategy
from .execution_engine import ExecutionEngine
from .backtest_engine import BinanceFuturesBacktestEngine
from .websocket_gateway import BinanceFuturesWebSocketGateway

class BinanceFuturesService:
    def __init__(self):
        init_futures_tables()
        self.connector = BinanceFuturesConnector()
        self.md = MarketDataManager()
        self.paper = PaperTradingEngine(self.md)
        self.risk = RiskManager(self.md)
        self.strategy = ETHM1ScalpingStrategy(self.md)
        self.executor = ExecutionEngine(self.connector, self.risk, self.md, self.paper)
        self.backtest = BinanceFuturesBacktestEngine()
        self.gateway = BinanceFuturesWebSocketGateway(
            self.md, self.paper, self.risk, self.strategy, self.executor, self.connector
        )
        self.background_tasks = []

    async def initialize(self):
        """
        Initializes exchange filters, syncs time, loads initial M1 klines,
        and starts background streaming & reconciliation tasks.
        """
        print("[BINANCE_FUTURES_SERVICE] Initializing...")
        await self.connector.sync_server_time_async()
        await self.connector.fetch_exchange_info_async()

        # Load initial M1 klines
        raw_klines = await run_in_thread(self.backtest.fetch_historical_klines, 500)
        formatted = [[k["time"], k["open"], k["high"], k["low"], k["close"], k["volume"]] for k in raw_klines]
        self.md.load_initial_klines(formatted, "1m")

        if self.connector.has_credentials():
            print("[BINANCE_FUTURES_SERVICE] Live Binance credentials detected. Reconciling live account...")
            try:
                await self.connector.verify_and_set_leverage_async(DEFAULT_CONFIG.default_leverage)
                await self.connector.verify_and_set_position_mode_async(dual_side=False)
                acc_info = await run_in_thread(self.connector.fetch_account_state)
                if acc_info.get("balance"):
                    self.risk.sync_live_balance(acc_info["balance"])
                    print(f"[BINANCE_FUTURES_SERVICE] Live Binance balance synchronized: ${acc_info['balance']:.2f} USDT")
            except Exception as e:
                print(f"[BINANCE_FUTURES_SERVICE_INIT_ERR] {e}")

        # Start background market stream
        stream_task = asyncio.create_task(self.gateway.start_market_stream())
        self.background_tasks.append(stream_task)

        # Start background listenKey keepalive loop
        listen_task = asyncio.create_task(self._listenkey_keepalive_loop())
        self.background_tasks.append(listen_task)

        print("[BINANCE_FUTURES_SERVICE] Production real-time engine running.")

    async def _listenkey_keepalive_loop(self):
        """Periodically refreshes Binance listenKey every 20 minutes if active."""
        while True:
            try:
                await asyncio.sleep(1200) # 20 minutes
                if self.connector.has_credentials():
                    await run_in_thread(self.connector.keepalive_listen_key)
            except Exception as e:
                print(f"[LISTENKEY_KEEPALIVE_ERR] {e}")

service_instance = BinanceFuturesService()

# --- FastAPI Router ---
router = APIRouter(prefix="/api/v1/futures", tags=["Binance Futures M1 Production Engine"])

@router.get("/state")
async def get_futures_state():
    return service_instance.gateway.build_dashboard_state()

@router.get("/connection")
async def get_connection_status():
    return service_instance.connector.get_public_connection_status()

class ControlPayload(BaseModel):
    action: str  # "run", "pause", "reset_session", "emergency_stop"

@router.post("/control")
async def control_bot(payload: ControlPayload):
    action = payload.action.lower()
    if action == "run":
        DEFAULT_CONFIG.is_running = True
        service_instance.risk.emergency_stop_triggered = False
        return {"status": "SUCCESS", "message": "Bot resumed"}
    elif action == "pause":
        DEFAULT_CONFIG.is_running = False
        return {"status": "SUCCESS", "message": "Bot paused"}
    elif action == "reset_session":
        service_instance.risk.reset_session()
        DEFAULT_CONFIG.is_running = True
        return {"status": "SUCCESS", "message": "Session PnL and $2 target reset"}
    elif action == "emergency_stop":
        res = await service_instance.executor.emergency_stop()
        DEFAULT_CONFIG.is_running = False
        return res
    else:
        raise HTTPException(status_code=400, detail="Unknown action")

class ModePayload(BaseModel):
    mode: str                          # "PAPER" or "LIVE"
    confirm_live: Optional[bool] = False
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

@router.post("/mode")
async def switch_mode(payload: ModePayload):
    req_mode = payload.mode.upper()
    if req_mode == "LIVE":
        if not payload.confirm_live:
            raise HTTPException(status_code=400, detail="Confirmation required to enable LIVE mode.")
        if payload.api_key and payload.api_secret:
            service_instance.connector.update_keys(payload.api_key, payload.api_secret)
        if not service_instance.connector.has_credentials():
            raise HTTPException(status_code=400, detail="Binance API Key and Secret are required for LIVE mode. Configure in .env.")
        
        # Verify and set 100x leverage
        ok, msg = await service_instance.connector.verify_and_set_leverage_async(DEFAULT_CONFIG.default_leverage)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Failed to set leverage: {msg}")

        # Verify and set One-Way position mode
        await service_instance.connector.verify_and_set_position_mode_async(dual_side=False)

        DEFAULT_CONFIG.mode = "LIVE"
        DEFAULT_CONFIG.live_enabled = True
        return {"status": "SUCCESS", "mode": "LIVE", "message": "LIVE trading activated on Binance Futures"}
    else:
        DEFAULT_CONFIG.mode = "PAPER"
        DEFAULT_CONFIG.live_enabled = False
        return {"status": "SUCCESS", "mode": "PAPER", "message": "Switched to Paper Trading simulation"}

class BacktestPayload(BaseModel):
    days: Optional[int] = 7
    candles: Optional[int] = 5000
    margin: Optional[float] = 0.50
    leverage: Optional[int] = 100

@router.post("/backtest")
async def run_backtest_endpoint(payload: BacktestPayload):
    candles_count = payload.candles if payload.candles and payload.candles > 500 else (payload.days * 1440)
    res = await run_in_thread(
        service_instance.backtest.run_backtest,
        total_candles=candles_count,
        margin_usd=payload.margin or DEFAULT_CONFIG.default_margin_usd,
        leverage=payload.leverage or DEFAULT_CONFIG.default_leverage
    )
    return res

@router.get("/trades")
async def get_trades_history(limit: int = 50):
    return get_trades(limit=limit)

@router.get("/session")
async def get_session_info():
    return service_instance.risk.get_risk_summary()

# WebSocket Endpoint for Real-time Dashboard Updates
@router.websocket("/ws")
async def websocket_futures_endpoint(websocket: WebSocket):
    await websocket.accept()
    service_instance.gateway.register_client(websocket)
    try:
        # Send initial state immediately
        initial_state = service_instance.gateway.build_dashboard_state()
        await websocket.send_text(json.dumps(initial_state))
        while True:
            # Keep socket open and handle incoming ping / actions
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        service_instance.gateway.unregister_client(websocket)
    except Exception:
        service_instance.gateway.unregister_client(websocket)
