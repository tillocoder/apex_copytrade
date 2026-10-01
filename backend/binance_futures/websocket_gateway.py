import asyncio
import json
import time
import websockets
from typing import Set, Dict, Any, Optional

from .config import DEFAULT_CONFIG
from .market_data import MarketDataManager
from .paper_engine import PaperTradingEngine
from .risk_manager import RiskManager
from .strategy_engine import ETHM1ScalpingStrategy
from .execution_engine import ExecutionEngine
from .binance_connector import BinanceFuturesConnector
from .database import get_trades, log_system_event

class BinanceFuturesWebSocketGateway:
    """
    Unified Real-time Gateway:
    - Streams Binance Futures market data (bookTicker, kline_1m, markPrice)
    - Pushes comprehensive real-time trading state to frontend clients
    - Reconciles live Binance positions and orders continuously
    - Broadcasts live signal score, precise rejection reasons, and 2-stage TP/SL levels
    """
    def __init__(self, market_data: MarketDataManager, paper_engine: PaperTradingEngine,
                 risk_manager: RiskManager, strategy_engine: ETHM1ScalpingStrategy,
                 execution_engine: ExecutionEngine, connector: BinanceFuturesConnector):
        self.md = market_data
        self.paper = paper_engine
        self.risk = risk_manager
        self.strategy = strategy_engine
        self.executor = execution_engine
        self.connector = connector
        
        self.client_connections: Set[websockets.WebSocketServerProtocol] = set()
        self.is_running = True
        self.is_connected_to_binance = False
        self.last_broadcast_ts = 0.0
        self.last_reconcile_ts = 0.0
        self.latest_signal_cache: Dict[str, Any] = {}
        self.live_position_cache: Optional[Dict[str, Any]] = None
        self.cached_dashboard_state: Optional[Dict[str, Any]] = None
        self.cached_state_ts: float = 0.0

    def register_client(self, websocket):
        self.client_connections.add(websocket)

    def unregister_client(self, websocket):
        self.client_connections.discard(websocket)

    async def broadcast_to_clients(self, payload: Dict[str, Any]):
        if not self.client_connections:
            return
        # Pre-serialize once for all connected clients
        msg = json.dumps(payload)
        clients = list(self.client_connections)

        async def _safe_send(ws):
            try:
                await ws.send_text(msg)
                return None
            except Exception:
                return ws

        # Parallel non-blocking socket dispatch across all connected clients
        dead = await asyncio.gather(*[_safe_send(ws) for ws in clients], return_exceptions=True)
        for d in dead:
            if d is not None and not isinstance(d, Exception):
                self.client_connections.discard(d)

    def get_cached_dashboard_state(self) -> Dict[str, Any]:
        """Returns ultra-fast in-memory cached state (200ms TTL) preventing SQLite disk lock thrashing."""
        now = time.monotonic()
        if self.cached_dashboard_state is not None and (now - self.cached_state_ts) < 0.20:
            return self.cached_dashboard_state
        state = self.build_dashboard_state()
        self.cached_dashboard_state = state
        self.cached_state_ts = now
        return state

    async def start_market_stream(self):
        """
        Background loop streaming real-time bookTicker, kline_1m, kline_5m, and markPrice from Binance.
        """
        stream_url = f"{DEFAULT_CONFIG.ws_base_url}?streams=ethusdt@kline_1m/ethusdt@kline_5m/ethusdt@markPrice@1s/ethusdt@ticker"
        backoff = 1.0

        while self.is_running:
            try:
                print(f"[BINANCE_WS] Connecting to {stream_url}...")
                log_system_event("INFO", f"[BINANCE_WS] Connecting to Binance Futures stream...")
                async with websockets.connect(stream_url, ping_interval=None) as ws:
                    self.is_connected_to_binance = True
                    backoff = 1.0
                    print(f"[BINANCE_WS] Connected successfully to Binance stream!")
                    log_system_event("INFO", f"[BINANCE_WS] Connected to Binance Futures stream.")

                    while self.is_running:
                        msg = await ws.recv()
                        raw = json.loads(msg)
                        stream_name = raw.get("stream", "")
                        data = raw.get("data", {})

                        # 1. Ticker / Book Ticker (Best Bid / Ask & Spread)
                        if "@ticker" in stream_name:
                            last_price = float(data.get("c") or 0)
                            bid = float(data.get("b") or (last_price - 0.01 if last_price > 0 else 0))
                            ask = float(data.get("a") or (last_price + 0.01 if last_price > 0 else 0))
                            self.md.update_book_ticker(
                                bid=bid,
                                ask=ask,
                                bid_qty=float(data.get("Q") or 1.0),
                                ask_qty=float(data.get("Q") or 1.0)
                            )
                        elif "@bookTicker" in stream_name:
                            self.md.update_book_ticker(
                                bid=float(data.get("b", 0)),
                                ask=float(data.get("a", 0)),
                                bid_qty=float(data.get("B", 0)),
                                ask_qty=float(data.get("A", 0))
                            )

                        # 2. Mark Price & Funding Rate
                        elif "@markPrice" in stream_name:
                            self.md.update_mark_price(
                                mark=float(data.get("p", 0)),
                                funding_rate=float(data.get("r", 0))
                            )
                            # Evaluate active position for Paper mode TP / SL hit
                            if DEFAULT_CONFIG.mode == "PAPER":
                                closed_trade = self.paper.update_price_tick()
                                if closed_trade:
                                    self.risk.record_trade_completion(closed_trade["pnl"])

                        # 3. 5m Kline stream (Primary M5 Execution Engine)
                        elif "@kline_5m" in stream_name:
                            k = data.get("k", {})
                            self.md.update_kline_stream(k, interval="5m")

                            has_open_pos = bool(self.paper.current_position) if DEFAULT_CONFIG.mode == "PAPER" else bool(self.live_position_cache)
                            risk_check = self.risk.check_preflight_risk(
                                has_open_position=has_open_pos,
                                is_live_mode=DEFAULT_CONFIG.live_enabled
                            )

                            signal_res = self.strategy.evaluate_setup(risk_check)
                            self.latest_signal_cache = signal_res

                            # Execute strictly on confirmed completed M5 candle flip
                            if k.get("x", False) and DEFAULT_CONFIG.is_running and signal_res.get("final_signal") in ("LONG", "SHORT"):
                                if risk_check.get("can_trade", False) and not has_open_pos:
                                    exec_res = await self.executor.execute_signal(signal_res, DEFAULT_CONFIG.live_enabled)
                                    print(f"🎯 [AUTO_EXECUTION M5] {signal_res.get('final_signal')} -> Status: {exec_res.get('status')}")
                                    log_system_event("INFO", f"🎯 [AUTO_EXECUTION M5] {signal_res.get('final_signal')} -> {exec_res}")

                        # 4. 1m Kline stream
                        elif "@kline_1m" in stream_name:
                            k = data.get("k", {})
                            self.md.update_kline_stream(k, interval="1m")
                            
                            # Determine open position status
                            has_open_pos = bool(self.paper.current_position) if DEFAULT_CONFIG.mode == "PAPER" else bool(self.live_position_cache)
                            
                            # Evaluate Pre-flight Risk Constraints
                            risk_check = self.risk.check_preflight_risk(
                                has_open_position=has_open_pos,
                                is_live_mode=DEFAULT_CONFIG.live_enabled
                            )

                            # Evaluate Strategy Engine
                            signal_res = self.strategy.evaluate_setup(risk_check)
                            self.latest_signal_cache = signal_res

                            # Auto-Execution Gate (1m only if configured for 1m timeframe)
                            if DEFAULT_CONFIG.timeframe == "1m" and DEFAULT_CONFIG.is_running and signal_res.get("final_signal") in ("LONG", "SHORT"):
                                if risk_check.get("can_trade", False) and not has_open_pos:
                                    exec_res = await self.executor.execute_signal(signal_res, DEFAULT_CONFIG.live_enabled)
                                    print(f"🎯 [AUTO_EXECUTION] {signal_res.get('final_signal')} -> Status: {exec_res.get('status')}")
                                    log_system_event("INFO", f"🎯 [AUTO_EXECUTION] {signal_res.get('final_signal')} -> {exec_res}")

                        # Periodic Live State Reconciliation (every 10s in LIVE mode)
                        now = time.time()
                        if DEFAULT_CONFIG.mode == "LIVE" and now - self.last_reconcile_ts >= 10.0:
                            self.last_reconcile_ts = now
                            self.live_position_cache = await self.executor.reconcile_active_position()

                        # Throttle client broadcasts to max 4 times per second (250ms)
                        if now - self.last_broadcast_ts >= 0.25:
                            self.last_broadcast_ts = now
                            state_payload = self.build_dashboard_state()
                            self.cached_dashboard_state = state_payload
                            self.cached_state_ts = time.monotonic()
                            await self.broadcast_to_clients(state_payload)

            except Exception as e:
                self.is_connected_to_binance = False
                print(f"[BINANCE_WS_ERR] {e}. Retrying in {backoff:.1f}s...")
                log_system_event("ERROR", f"[BINANCE_WS_RECONNECT] {e}. Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(15.0, backoff * 1.5)

    def build_dashboard_state(self) -> Dict[str, Any]:
        """
        Builds unified realtime JSON payload consumed by the frontend trading dashboard.
        """
        market = self.md.get_market_summary()
        risk_summary = self.risk.get_risk_summary()
        public_conn = self.connector.get_public_connection_status()

        # Account & Position
        if DEFAULT_CONFIG.mode == "LIVE" and self.connector.has_credentials():
            acc = self.connector.fetch_account_state()
            position = acc.get("position") or self.live_position_cache
            balance = acc.get("balance", 0.0)
            avail = acc.get("availableBalance", 0.0)
            used_margin = acc.get("usedMargin", 0.0)
            unreal_pnl = acc.get("unrealizedPnl", 0.0)
            self.risk.sync_live_balance(balance)
        else:
            position = self.paper.current_position
            balance = self.paper.balance
            avail = self.paper.available_balance
            used_margin = position["margin"] if position else 0.0
            unreal_pnl = position["unrealizedPnl"] if position else 0.0
            self.risk.sync_live_balance(balance)

        # Dynamic On-Demand Strategy Evaluation if not already calculated
        has_open_pos = bool(position is not None)
        risk_check = self.risk.check_preflight_risk(
            has_open_position=has_open_pos,
            is_live_mode=DEFAULT_CONFIG.live_enabled
        )
        current_signal = self.strategy.evaluate_setup(risk_check)
        self.latest_signal_cache = current_signal

        # Bot status determination
        if risk_summary.get("emergencyStop"):
            bot_status = "EMERGENCY_STOP"
        elif risk_summary.get("targetReached"):
            bot_status = "TARGET_REACHED"
        elif not DEFAULT_CONFIG.is_running:
            bot_status = "PAUSED"
        elif risk_summary.get("cooldownSecondsRemaining", 0) > 0:
            bot_status = "COOLDOWN"
        elif position is not None:
            bot_status = "IN_POSITION"
        else:
            bot_status = "SCANNING"

        # Recent Trades from Database
        trades = get_trades(limit=25)

        return {
            "type": "FUTURES_DASHBOARD_STATE",
            "timestamp": int(time.time() * 1000),
            "bot": {
                "connected": self.is_connected_to_binance,
                "running": DEFAULT_CONFIG.is_running,
                "mode": DEFAULT_CONFIG.mode,
                "liveEnabled": DEFAULT_CONFIG.live_enabled,
                "symbol": DEFAULT_CONFIG.display_symbol,
                "binanceSymbol": DEFAULT_CONFIG.symbol,
                "timeframe": DEFAULT_CONFIG.timeframe,
                "leverage": DEFAULT_CONFIG.default_leverage,
                "marginUsd": risk_summary.get("targetMargin", DEFAULT_CONFIG.default_margin_usd),
                "approxNotional": DEFAULT_CONFIG.approx_notional_usd,
                "maxOpenPositions": DEFAULT_CONFIG.max_open_positions,
                "sessionTargetUsd": DEFAULT_CONFIG.session_profit_target_usd,
                "status": bot_status,
                "compoundingTier": risk_summary.get("compoundingTier")
            },
            "account": {
                "balance": round(balance, 2),
                "availableBalance": round(avail, 2),
                "usedMargin": round(used_margin, 2),
                "unrealizedPnl": round(unreal_pnl, 2),
                "sessionPnl": risk_summary["sessionPnl"],
                "targetProgressPct": risk_summary["targetProgressPct"],
                "targetReached": risk_summary["targetReached"],
                "initialBalance": DEFAULT_CONFIG.initial_balance_usd
            },
            "connection": public_conn,
            "position": position,
            "market": market,
            "signal": current_signal,
            "risk": risk_summary,
            "trades": trades
        }
