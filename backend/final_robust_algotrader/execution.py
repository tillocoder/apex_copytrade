"""
Production Execution Engine — Realistic Slippage, Commission & Reconciliation.
"""
from typing import Dict, Any, List
from .config import ProductionConfig

class ProductionExecutionEngine:
    def __init__(self, cfg: ProductionConfig):
        self.cfg = cfg

    def compute_transaction_cost(self, notional: float) -> float:
        rate = self.cfg.execution.commission_per_side_pct + self.cfg.execution.slippage_per_side_pct
        return notional * rate

    def simulate_entry_fill(self, symbol: str, side: str, order_price: float, qty: float) -> Dict[str, Any]:
        slip_pct = self.cfg.execution.slippage_per_side_pct
        if side == "BUY":
            fill_price = order_price * (1.0 + slip_pct)
        else:
            fill_price = order_price * (1.0 - slip_pct)

        notional = fill_price * qty
        fee = notional * self.cfg.execution.commission_per_side_pct
        return {
            "fill_price": round(fill_price, 2),
            "fee": round(fee, 4),
            "notional": round(notional, 2),
            "status": "FILLED"
        }

    def simulate_exit_fill(self, symbol: str, side: str, target_price: float, qty: float) -> Dict[str, Any]:
        slip_pct = self.cfg.execution.slippage_per_side_pct
        if side == "SELL": # Exiting BUY
            fill_price = target_price * (1.0 - slip_pct)
        else: # Exiting SELL
            fill_price = target_price * (1.0 + slip_pct)

        notional = fill_price * qty
        fee = notional * self.cfg.execution.commission_per_side_pct
        return {
            "fill_price": round(fill_price, 2),
            "fee": round(fee, 4),
            "notional": round(notional, 2),
            "status": "FILLED"
        }
