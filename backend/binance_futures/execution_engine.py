import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List

from .config import DEFAULT_CONFIG
from .binance_connector import BinanceFuturesConnector
from .risk_manager import RiskManager
from .market_data import MarketDataManager
from .paper_engine import PaperTradingEngine
from .database import save_trade, log_system_event

class ExecutionEngine:
    """
    Production-Grade Binance Futures Execution Engine:
    - Pre-flight account & permission checks
    - Idempotent order placement with unique clientOrderIds
    - 2-Stage Professional Order Staging:
        * Market Entry
        * Mandatory Immediate Initial Stop-Loss (with fail-safe emergency close)
        * TP1 (1R, 50% size)
        * TP2 (2R, 50% size)
        * Dynamic Breakeven Replacement once TP1 fills
    - Complete Binance State Reconciliation (survives restarts)
    - Instant Emergency Stop
    """
    def __init__(self, connector: BinanceFuturesConnector, risk_manager: RiskManager,
                 market_data: MarketDataManager, paper_engine: PaperTradingEngine):
        self.connector = connector
        self.risk = risk_manager
        self.md = market_data
        self.paper = paper_engine
        self.is_executing = False
        
        # Live tracking state
        self.live_position_tracking: Optional[Dict[str, Any]] = None

    async def execute_signal(self, signal_data: Dict[str, Any], is_live_mode: bool) -> Dict[str, Any]:
        """
        Executes a validated LONG or SHORT signal with full pre-flight verification,
        2-stage exits, and fail-safe stop-loss placement.
        """
        if self.is_executing:
            return {"status": "REJECTED", "reason": "Execution lock active"}

        signal = signal_data.get("final_signal")
        if signal not in ("LONG", "SHORT"):
            return {"status": "IGNORED", "reason": "No actionable signal"}

        self.is_executing = True
        try:
            current_price = self.md.get_current_price()
            sl = signal_data["sl"]
            tp1 = signal_data.get("tp1")
            tp2 = signal_data.get("tp2", signal_data.get("tp"))
            be_price = signal_data.get("be_price")
            r_dist = signal_data.get("r_distance", abs(current_price - sl))
            matrix = signal_data.get("matrix", {})

            # Calculate order size with dynamic dollar risk clipping & compounding tier
            sizing = self.risk.calculate_order_sizing(current_price, self.connector.exchange_filters, sl_distance=r_dist)
            qty = sizing["quantity"]

            # --- MODE 1: PAPER TRADING ---
            if not is_live_mode:
                pos = self.paper.open_position(signal, qty, sl, tp1, tp2, be_price, matrix)
                return {
                    "status": "FILLED",
                    "mode": "PAPER",
                    "side": signal,
                    "qty": qty,
                    "entry_price": pos["entryPrice"],
                    "sl": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "be_price": be_price,
                    "margin": pos["margin"],
                    "leverage": pos["leverage"],
                    "tier": sizing.get("tier")
                }

            # --- MODE 2: LIVE BINANCE FUTURES TRADING ---
            # Pre-flight 1: Check Credentials
            if not self.connector.has_credentials():
                return {"status": "REJECTED", "reason": "Binance API keys not set in .env"}

            # Pre-flight 2: Server time sync
            await self.connector.sync_server_time_async()

            # Pre-flight 3: Ensure One-Way Position Mode
            if not self.connector.position_mode_verified:
                ok, p_msg = await self.connector.verify_and_set_position_mode_async(dual_side=False)
                if not ok:
                    log_system_event("WARN", f"[LIVE_PREFLIGHT] Position mode check: {p_msg}")

            # Pre-flight 4: Ensure 100x Leverage
            if not self.connector.leverage_verified:
                ok, lev_msg = await self.connector.verify_and_set_leverage_async(DEFAULT_CONFIG.default_leverage)
                if not ok:
                    return {"status": "HALTED", "reason": f"Failed to set 100x leverage: {lev_msg}"}

            # Pre-flight 5: Account state & balance check
            acc = await self.connector.fetch_account_state_async()
            if not acc.get("connected"):
                return {"status": "REJECTED", "reason": f"Account check failed: {acc.get('reason')}"}

            if acc.get("position") is not None:
                return {"status": "REJECTED", "reason": "Active position already exists on Binance"}

            avail_bal = float(acc.get("availableBalance", 0.0))
            self.risk.sync_live_balance(float(acc.get("balance", avail_bal)))

            if avail_bal < sizing["margin"]:
                return {
                    "status": "REJECTED",
                    "reason": f"Insufficient available balance (${avail_bal:.2f} < ${sizing['margin']:.2f})"
                }

            # Generate Unique Client Order IDs
            uid = uuid.uuid4().hex[:6]
            entry_cid = f"APX_E_{signal[0]}_{int(time.time())}_{uid}"
            sl_cid = f"APX_SL_{int(time.time())}_{uid}"
            tp1_cid = f"APX_TP1_{int(time.time())}_{uid}"
            tp2_cid = f"APX_TP2_{int(time.time())}_{uid}"

            # Step 1: Place Entry Market Order
            entry_side = "BUY" if signal == "LONG" else "SELL"
            log_system_event("INFO", f"[LIVE] Submitting {signal} {qty} ETHUSDT @ MARKET (margin ~${sizing['margin']:.2f})...")

            order_res = await self.connector.place_order_async(
                symbol=DEFAULT_CONFIG.symbol,
                side=entry_side,
                order_type="MARKET",
                qty=qty,
                client_order_id=entry_cid
            )

            if order_res.get("error"):
                log_system_event("ERROR", f"[LIVE_ENTRY_FAILED] {order_res.get('msg')}")
                return {"status": "FAILED", "reason": order_res.get("msg")}

            executed_price = float(order_res.get("avgPrice", current_price)) or current_price

            # Step 2: IMMEDIATELY Place Mandatory Stop-Loss (CRITICAL SAFEGUARD)
            exit_side = "SELL" if signal == "LONG" else "BUY"
            sl_res = await self.connector.place_order_async(
                symbol=DEFAULT_CONFIG.symbol,
                side=exit_side,
                order_type="STOP_MARKET",
                qty=qty,
                stop_price=sl,
                client_order_id=sl_cid,
                reduce_only=True
            )

            # FAIL-SAFE WATCHDOG: If SL failed to place on Binance, EMERGENCY MARKET CLOSE
            if sl_res.get("error"):
                log_system_event("CRITICAL", f"[LIVE EMERGENCY] SL order failed ({sl_res.get('msg')})! Closing position immediately.")
                await self.connector.place_order_async(
                    symbol=DEFAULT_CONFIG.symbol,
                    side=exit_side,
                    order_type="MARKET",
                    qty=qty,
                    reduce_only=True
                )
                return {"status": "FAILED", "reason": f"SL rejected by Binance: {sl_res.get('msg')}. Emergency closed."}

            # Step 3: Place 2-Stage TP Orders (TP1 50% and TP2 50%)
            step = float(self.connector.exchange_filters.get("stepSize", DEFAULT_CONFIG.step_size))
            qty_tp1 = round(math.floor((qty * DEFAULT_CONFIG.tp1_close_pct) / step) * step, 3)
            qty_tp2 = round(qty - qty_tp1, 3)

            tp1_res = await self.connector.place_order_async(
                symbol=DEFAULT_CONFIG.symbol,
                side=exit_side,
                order_type="TAKE_PROFIT_MARKET",
                qty=qty_tp1,
                stop_price=tp1,
                client_order_id=tp1_cid,
                reduce_only=True
            )

            tp2_res = await self.connector.place_order_async(
                symbol=DEFAULT_CONFIG.symbol,
                side=exit_side,
                order_type="TAKE_PROFIT_MARKET",
                qty=qty_tp2,
                stop_price=tp2,
                client_order_id=tp2_cid,
                reduce_only=True
            )

            # Store live tracking state
            self.live_position_tracking = {
                "side": signal,
                "qty": qty,
                "initialQty": qty,
                "entryPrice": executed_price,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "bePrice": be_price,
                "tp1Hit": False,
                "beActive": False,
                "slOrderId": sl_res.get("orderId"),
                "tp1OrderId": tp1_res.get("orderId"),
                "tp2OrderId": tp2_res.get("orderId"),
                "entryOrderId": order_res.get("orderId"),
                "openedAt": time.time()
            }

            log_system_event("INFO", f"[LIVE] Position active: {signal} {qty} @ ${executed_price:.2f} | SL: ${sl:.2f} | TP1: ${tp1:.2f} | TP2: ${tp2:.2f}")

            return {
                "status": "FILLED",
                "mode": "LIVE",
                "side": signal,
                "qty": qty,
                "entry_price": executed_price,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "be_price": be_price,
                "margin": sizing["margin"],
                "leverage": DEFAULT_CONFIG.default_leverage,
                "order_id": order_res.get("orderId")
            }

        finally:
            self.is_executing = False

    async def reconcile_active_position(self) -> Optional[Dict[str, Any]]:
        """
        Reconciles active position and open orders with Binance:
        - Detects if TP1 filled -> Cancels full SL, moves SL of remaining 50% to Breakeven + fee buffer
        - Detects if position closed -> Cleans up open orders, records trade outcome
        """
        if not self.connector.has_credentials():
            return None

        try:
            acc = await self.connector.fetch_account_state_async()
            if not acc.get("connected"):
                return None

            pos = acc.get("position")
            
            # Case 1: No position active on Binance
            if not pos:
                if self.live_position_tracking:
                    log_system_event("INFO", "[LIVE] Position closed on Binance. Cleaning up open orders...")
                    await self.connector.cancel_all_orders_async(DEFAULT_CONFIG.symbol)
                    self.live_position_tracking = None
                return None

            # Case 2: Position is active on Binance
            if self.live_position_tracking:
                trk = self.live_position_tracking
                current_qty = pos["qty"]

                # Check if TP1 filled (qty dropped from initialQty to ~50%)
                if not trk["tp1Hit"] and current_qty < trk["initialQty"] * 0.75:
                    log_system_event("INFO", f"[LIVE] TP1 filled! Remaining: {current_qty} ETH. Moving SL to Breakeven (${trk['bePrice']:.2f})...")
                    
                    # 1. Cancel original full SL order
                    if trk.get("slOrderId"):
                        await self.connector.cancel_order_async(DEFAULT_CONFIG.symbol, order_id=trk["slOrderId"])

                    # 2. Place new SL order at Breakeven + fee buffer for remaining quantity
                    exit_side = "SELL" if trk["side"] == "LONG" else "BUY"
                    be_cid = f"APX_BE_{int(time.time())}"
                    new_sl_res = await self.connector.place_order_async(
                        symbol=DEFAULT_CONFIG.symbol,
                        side=exit_side,
                        order_type="STOP_MARKET",
                        qty=current_qty,
                        stop_price=trk["bePrice"],
                        client_order_id=be_cid,
                        reduce_only=True
                    )
                    trk["tp1Hit"] = True
                    trk["beActive"] = True
                    trk["slOrderId"] = new_sl_res.get("orderId")
                    trk["sl"] = trk["bePrice"]
                    pos["tp1Hit"] = True
                    pos["beActive"] = True
                    pos["bePrice"] = trk["bePrice"]

            # Merge tracking metadata into position display
            if self.live_position_tracking:
                pos["tp1"] = self.live_position_tracking.get("tp1")
                pos["tp2"] = self.live_position_tracking.get("tp2")
                pos["bePrice"] = self.live_position_tracking.get("bePrice")
                pos["tp1Hit"] = self.live_position_tracking.get("tp1Hit", False)
                pos["beActive"] = self.live_position_tracking.get("beActive", False)

            return pos

        except Exception as e:
            print(f"[RECONCILE_ERR] {e}")
            return None

    async def emergency_stop(self) -> Dict[str, Any]:
        """
        Instant Emergency Stop:
        - Cancels all open orders on Binance
        - Closes active positions at market price
        - Halts further entries
        """
        log_system_event("CRITICAL", "[EMERGENCY_STOP] Executing global emergency halt...")
        self.risk.trigger_emergency_stop()

        # Paper mode emergency close
        if self.paper.current_position:
            mark = self.md.get_current_price()
            self.paper.close_position(mark, "EMERGENCY_STOP_TRIGGERED")

        # Live mode emergency close
        if self.connector.has_credentials():
            try:
                # 1. Cancel all open orders
                await self.connector.cancel_all_orders_async(DEFAULT_CONFIG.symbol)

                # 2. Close active position
                acc = await self.connector.fetch_account_state_async()
                pos = acc.get("position")
                if pos and pos.get("qty", 0) > 0:
                    exit_side = "SELL" if pos["side"] == "LONG" else "BUY"
                    await self.connector.place_order_async(
                        symbol=DEFAULT_CONFIG.symbol,
                        side=exit_side,
                        order_type="MARKET",
                        qty=pos["qty"],
                        reduce_only=True
                    )
                    log_system_event("CRITICAL", f"[EMERGENCY_STOP] Market closed {pos['side']} {pos['qty']} ETHUSDT on Binance.")
            except Exception as e:
                log_system_event("ERROR", f"[EMERGENCY_STOP_ERR] {e}")

        self.live_position_tracking = None
        return {"status": "SUCCESS", "message": "Emergency Stop executed. All orders cancelled & positions closed."}
