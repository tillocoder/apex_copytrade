import random
from dataclasses import dataclass
from .config import ExecutionConfig

@dataclass
class ExecutionResult:
    filled: bool
    fill_price: float
    commission: float
    slippage_cost: float

class ExecutionEngine:
    """Simulates realistic market execution (spread, slippage, commissions, fills)."""

    def __init__(self, config: ExecutionConfig):
        self.cfg = config

    def execute_order(
        self,
        symbol: str,
        side: str,
        price: float,
        units: float,
        is_limit: bool = False
    ) -> ExecutionResult:
        # Check missed fill for limit orders
        if is_limit and random.random() < self.cfg.missed_fill_prob:
            return ExecutionResult(filled=False, fill_price=0.0, commission=0.0, slippage_cost=0.0)

        # Crypto Basis Points (bps) simulation (1 bps = 0.0001 = 0.01%)
        # Slippage distribution centered at config.slippage_bps
        slippage_bps = abs(random.gauss(self.cfg.slippage_bps, 0.2))
        half_spread_pct = (self.cfg.spread_bps / 2.0) * 0.0001
        slippage_pct = slippage_bps * 0.0001

        if side == "BUY":
            fill_price = price * (1.0 + half_spread_pct + slippage_pct)
        else:
            fill_price = price * (1.0 - half_spread_pct - slippage_pct)

        notional_val = fill_price * units
        commission = notional_val * self.cfg.commission_pct
        slippage_cost = abs(fill_price - price) * units

        return ExecutionResult(
            filled=True,
            fill_price=round(fill_price, 2),
            commission=round(commission, 2),
            slippage_cost=round(slippage_cost, 2)
        )
