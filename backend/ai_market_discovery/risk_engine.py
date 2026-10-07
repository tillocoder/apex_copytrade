"""
Deterministic Risk Engine & Position Sizer
Enforces strict separation between AI reasoning and execution:
- Gemini only outputs Direction, Entry, SL, TP, Confidence, Quality.
- Risk Engine calculates position sizing, leverage, and margin.
- Strictly NO LIVE EXECUTION (Modes: SIGNAL_ONLY, PAPER, OFF).
"""

import math
from typing import Dict, Any

STEP_SIZES = {
    "BTCUSDT": 0.001,
    "ETHUSDT": 0.001,
    "SOLUSDT": 0.01
}

MIN_NOTIONALS = {
    "BTCUSDT": 20.0,
    "ETHUSDT": 20.0,
    "SOLUSDT": 5.0
}


class RiskEngine:
    def __init__(self, mode: str = "PAPER", risk_per_trade_pct: float = 0.01, leverage: float = 15.0):
        self.mode = mode  # "PAPER" or "SIGNAL_ONLY"
        self.risk_per_trade_pct = risk_per_trade_pct
        self.leverage = leverage

    def calculate_position(self, signal: Dict[str, Any], account_balance: float = 20.0) -> Dict[str, Any]:
        """
        Calculates position size and margin requirements without live exchange execution.
        """
        if signal.get("decision") not in ("LONG", "SHORT"):
            return {"status": "NO_POSITION"}

        symbol = signal.get("symbol", "BTCUSDT").replace("/", "")
        entry = float(signal.get("entry", 0.0))
        sl = float(signal.get("stop_loss", 0.0))

        sl_dist = abs(entry - sl)
        if sl_dist <= 0 or entry <= 0:
            return {"status": "INVALID_PRICES"}

        # Target risk amount in USD (e.g. 1% of $20 = $0.20)
        target_risk_usd = account_balance * self.risk_per_trade_pct

        # Raw quantity to lose exactly target_risk_usd if SL is hit
        raw_qty = target_risk_usd / sl_dist

        # Enforce Binance exchange filters
        step = STEP_SIZES.get(symbol, 0.001)
        min_notional = MIN_NOTIONALS.get(symbol, 5.0)

        min_qty_for_notional = min_notional / entry
        contract_qty = max(min_qty_for_notional, raw_qty)

        # Round to step size
        decimals = 3 if step == 0.001 else 2
        final_qty = round(math.ceil(contract_qty / step) * step, decimals)

        notional_usd = round(final_qty * entry, 2)
        required_margin_usd = round(notional_usd / self.leverage, 2)
        actual_risk_usd = round(final_qty * sl_dist, 2)

        return {
            "mode": self.mode,
            "symbol": symbol,
            "direction": signal.get("decision"),
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit_1": signal.get("take_profit_1"),
            "take_profit_2": signal.get("take_profit_2"),
            "quantity": final_qty,
            "notional_usd": notional_usd,
            "leverage": self.leverage,
            "required_margin_usd": required_margin_usd,
            "projected_risk_usd": actual_risk_usd,
            "risk_pct_of_account": round((actual_risk_usd / account_balance) * 100.0, 2),
            "execution_status": "PAPER_PENDING" if self.mode == "PAPER" else "SIGNAL_LOGGED_ONLY"
        }
