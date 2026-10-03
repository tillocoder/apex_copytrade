import time
import uuid
from typing import Dict, Any, Optional, List

from .config import DEFAULT_CONFIG
from .market_data import MarketDataManager
from .database import save_trade, log_system_event

class PaperTradingEngine:
    """
    High-Fidelity Paper Trading Simulation for ETHUSDT.P:
    - Real-time Bid/Ask execution with 1-tick slippage & 0.05% taker fee
    - 2-Stage Position Management:
        * TP1 (1R): Closes 50% of position
        * Dynamic Breakeven: Shifts remaining 50% SL to BE + 0.06% fee buffer
        * TP2 (2R): Closes remaining 50% of position
    - Real-time Mark Price Liquidation & SL/TP triggers
    """
    def __init__(self, market_data: MarketDataManager):
        self.md = market_data
        
        # Calculate balance from initial capital + accumulated realized PnL of closed paper trades
        try:
            from .database import get_trades
            closed = [t for t in get_trades(limit=500) if t.get("mode") == "PAPER" and t.get("status") == "CLOSED"]
            total_realized_pnl = sum(float(t.get("pnl", 0.0)) for t in closed)
        except Exception:
            total_realized_pnl = 0.0

        self.balance = round(DEFAULT_CONFIG.initial_balance_usd + total_realized_pnl, 2)
        self.available_balance = self.balance
        self.current_position: Optional[Dict[str, Any]] = None
        self.open_orders: List[Dict[str, Any]] = []

    def open_position(self, side: str, qty: float, sl: float, tp1: float, tp2: float, be_price: float, signal_matrix: Dict[str, Any]) -> Dict[str, Any]:
        """
        Opens a position at Best Ask (LONG) or Best Bid (SHORT) + 1-tick slippage.
        """
        bid = self.md.best_bid or self.md.get_current_price()
        ask = self.md.best_ask or self.md.get_current_price()
        
        # 1-tick slippage (0.01 USDT)
        entry_price = round(ask + DEFAULT_CONFIG.tick_size if side == "LONG" else bid - DEFAULT_CONFIG.tick_size, 2)
        notional = round(qty * entry_price, 2)
        margin = round(notional / DEFAULT_CONFIG.default_leverage, 4)
        
        # Binance VIP0 Futures taker fee: 0.05%
        entry_fee = round(notional * 0.0005, 4)
        
        pos_id = f"pos_paper_{int(time.time()*1000)}"
        trade_id = f"trd_paper_{uuid.uuid4().hex[:8]}"

        # Liquidation price for 100x (approx 0.8% away accounting for maintenance margin)
        liq_distance = entry_price * 0.008
        liq_price = round(entry_price - liq_distance if side == "LONG" else entry_price + liq_distance, 2)

        self.current_position = {
            "id": pos_id,
            "trade_id": trade_id,
            "symbol": DEFAULT_CONFIG.symbol,
            "displaySymbol": DEFAULT_CONFIG.display_symbol,
            "side": side,
            "qty": qty,
            "initialQty": qty,
            "entryPrice": entry_price,
            "markPrice": entry_price,
            "liquidationPrice": liq_price,
            "margin": margin,
            "initialMargin": margin,
            "leverage": DEFAULT_CONFIG.default_leverage,
            "sl": sl,
            "initialSl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "bePrice": be_price,
            "tp1Hit": False,
            "beActive": False,
            "unrealizedPnl": 0.0,
            "realizedPnl": 0.0,
            "roi": 0.0,
            "fee": entry_fee,
            "openedAt": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            "signalSnapshot": signal_matrix
        }

        self.available_balance = max(0.0, self.available_balance - margin)
        log_system_event("INFO", f"[PAPER] Opened {side} {qty} {DEFAULT_CONFIG.symbol} @ ${entry_price:.2f} | TP1(1R): ${tp1:.2f} | TP2(2R): ${tp2:.2f} | SL: ${sl:.2f}")
        return self.current_position

    def update_price_tick(self) -> Optional[Dict[str, Any]]:
        """
        Evaluates active position on each price tick:
        1. Checks TP1 (50% partial exit & shift to Breakeven + fee buffer)
        2. Checks TP2 (full remaining exit)
        3. Checks Breakeven exit (if TP1 was already hit)
        4. Checks Stop Loss
        5. Checks Liquidation
        """
        if not self.current_position:
            return None

        mark = self.md.mark_price or self.md.get_current_price()
        pos = self.current_position
        pos["markPrice"] = mark
        
        side = pos["side"]
        entry = pos["entryPrice"]
        qty = pos["qty"]
        margin = pos["margin"]

        # Calculate unrealized PnL on current remaining size
        if side == "LONG":
            raw_pnl = (mark - entry) * qty
        else:
            raw_pnl = (entry - mark) * qty

        pos["unrealizedPnl"] = round(raw_pnl, 4)
        pos["roi"] = round((raw_pnl / max(0.01, margin)) * 100.0, 2)

        sl = pos["sl"]
        tp1 = pos["tp1"]
        tp2 = pos["tp2"]
        be_price = pos["bePrice"]
        tp1_hit = pos["tp1Hit"]

        # 1. Check TP1 (1R / Target) if not already hit
        if not tp1_hit:
            hit_tp1 = (side == "LONG" and mark >= tp1) or (side == "SHORT" and mark <= tp1)
            if hit_tp1:
                close_pct = getattr(DEFAULT_CONFIG, "tp1_close_pct", 0.5)
                if close_pct >= 1.0 or pos["tp1"] == pos["tp2"]:
                    # Full 100% position close at TP target
                    return self.close_position(tp1, "TAKE_PROFIT_HIT")

                # Partial Close: 50%
                step = DEFAULT_CONFIG.step_size
                close_qty = round(pos["initialQty"] * close_pct, 3)
                rem_qty = round(pos["qty"] - close_qty, 3)
                if rem_qty <= 0:
                    return self.close_position(tp1, "TAKE_PROFIT_HIT")
                
                # Realize 50% PnL
                if side == "LONG":
                    gross_tp1 = (tp1 - entry) * close_qty
                else:
                    gross_tp1 = (entry - tp1) * close_qty
                fee_tp1 = close_qty * tp1 * 0.0005
                net_tp1 = round(gross_tp1 - fee_tp1, 4)

                pos["qty"] = rem_qty
                pos["margin"] = round(pos["initialMargin"] * 0.5, 4)
                pos["realizedPnl"] = round(pos["realizedPnl"] + net_tp1, 4)
                pos["fee"] = round(pos["fee"] + fee_tp1, 4)
                pos["tp1Hit"] = True
                pos["beActive"] = True
                pos["sl"] = be_price # Move remaining SL to Breakeven + fee buffer!

                self.balance += net_tp1
                self.available_balance += (pos["initialMargin"] * 0.5) + net_tp1

                log_system_event("INFO", f"[PAPER] TP1 HIT @ ${tp1:.2f}! Closed 50% ({close_qty} ETH). SL moved to BE (${be_price:.2f}). PnL: +${net_tp1:.2f}")

        # 2. Check TP2 (2R)
        hit_tp2 = (side == "LONG" and mark >= tp2) or (side == "SHORT" and mark <= tp2)
        if hit_tp2:
            return self.close_position(tp2, "TAKE_PROFIT_2_HIT")

        # 3. Check Breakeven or Stop Loss
        if pos["beActive"]:
            hit_be = (side == "LONG" and mark <= be_price) or (side == "SHORT" and mark >= be_price)
            if hit_be:
                return self.close_position(be_price, "BREAKEVEN_HIT")
        else:
            hit_sl = (side == "LONG" and mark <= sl) or (side == "SHORT" and mark >= sl)
            if hit_sl:
                return self.close_position(sl, "STOP_LOSS_HIT")

        # 4. Check Liquidation Protection
        hit_liq = (side == "LONG" and mark <= pos["liquidationPrice"]) or (side == "SHORT" and mark >= pos["liquidationPrice"])
        if hit_liq:
            return self.close_position(pos["liquidationPrice"], "LIQUIDATION_PROTECTION")

        return None

    def close_position(self, exit_price: float, reason: str) -> Dict[str, Any]:
        if not self.current_position:
            return {}

        pos = self.current_position
        side = pos["side"]
        entry = pos["entryPrice"]
        qty = pos["qty"]
        margin = pos["margin"]
        
        # Exit fee 0.05%
        exit_notional = qty * exit_price
        exit_fee = exit_notional * 0.0005
        total_fee = round(pos["fee"] + exit_fee, 4)

        if side == "LONG":
            gross_pnl = (exit_price - entry) * qty
        else:
            gross_pnl = (entry - exit_price) * qty

        # Combine with already realized TP1 PnL if applicable
        final_net_pnl = round(pos["realizedPnl"] + gross_pnl - exit_fee, 4)
        roi = round((final_net_pnl / max(0.01, pos["initialMargin"])) * 100.0, 2)

        closed_at = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        trade_record = {
            "id": pos["trade_id"],
            "client_order_id": pos["id"],
            "mode": "PAPER",
            "symbol": DEFAULT_CONFIG.symbol,
            "side": side,
            "entry_price": entry,
            "exit_price": round(exit_price, 2),
            "qty": pos["initialQty"],
            "margin": pos["initialMargin"],
            "leverage": pos["leverage"],
            "sl": pos["sl"],
            "tp": pos["tp2"],
            "tp1": pos["tp1"],
            "tp2": pos["tp2"],
            "pnl": final_net_pnl,
            "roi_pct": roi,
            "fee": total_fee,
            "status": "CLOSED",
            "close_reason": reason,
            "opened_at": pos["openedAt"],
            "closed_at": closed_at,
            "signal_snapshot": pos.get("signalSnapshot", {})
        }

        # Update balance
        self.balance += round(gross_pnl - exit_fee, 4)
        self.available_balance = self.balance
        self.current_position = None

        # Persist to SQLite
        try:
            save_trade(trade_record)
        except Exception as e:
            print(f"[PAPER_SAVE_ERR] {e}")

        log_system_event("INFO", f"[PAPER] Closed {side} @ ${exit_price:.2f} | Reason: {reason} | Final PnL: ${final_net_pnl:+.2f} ({roi:+.1f}%)")
        return trade_record
