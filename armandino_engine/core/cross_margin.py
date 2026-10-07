"""
Armandino Engine - Cross Margin Portfolio Manager
Accurately models Binance Futures Cross Margin mechanics:
- Shared margin pool for multi-asset positions
- Initial Margin, Maintenance Margin, Margin Ratio
- Unrealized PnL and Equity tracking
- Conservative Intra-bar liquidation check
"""

from typing import Dict, List, Optional, Tuple
from .models import Position, Side, TradeRecord, ExitReason


class CrossMarginAccount:
    def __init__(self, initial_balance: float = 20.0, leverage: float = 15.0):
        self.initial_balance = initial_balance
        self.wallet_balance = initial_balance
        self.leverage = leverage
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[TradeRecord] = []
        self.is_liquidated: bool = False
        self.liquidation_time: Optional[str] = None
        self.liquidation_bar_idx: Optional[int] = None
        self.peak_equity: float = initial_balance
        self.max_drawdown_pct: float = 0.0
        self.total_commissions_paid: float = 0.0
        self.trade_counter: int = 0
        
        # Binance Futures Maintenance Margin Rates (MMR)
        self.mmr_rates = {
            "ETHUSDT": 0.005,  # 0.5% Tier 1
            "ZECUSDT": 0.010,  # 1.0% Tier 1
        }
        
    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        total_upnl = 0.0
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol, pos.entry_price)
            if pos.side == Side.LONG:
                total_upnl += (price - pos.entry_price) * pos.current_qty
            else:
                total_upnl += (pos.entry_price - price) * pos.current_qty
        return total_upnl

    def get_equity(self, current_prices: Dict[str, float]) -> float:
        if self.is_liquidated:
            return 0.0
        return max(0.0, self.wallet_balance + self.get_unrealized_pnl(current_prices))

    def get_total_initial_margin(self, current_prices: Dict[str, float]) -> float:
        total_im = 0.0
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol, pos.entry_price)
            notional = price * pos.current_qty
            total_im += notional / pos.leverage
        return total_im

    def get_total_maintenance_margin(self, current_prices: Dict[str, float]) -> float:
        total_mm = 0.0
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol, pos.entry_price)
            notional = price * pos.current_qty
            rate = self.mmr_rates.get(symbol, 0.010)
            total_mm += notional * rate
        return total_mm

    def get_free_margin(self, current_prices: Dict[str, float]) -> float:
        if self.is_liquidated:
            return 0.0
        equity = self.get_equity(current_prices)
        total_im = self.get_total_initial_margin(current_prices)
        return max(0.0, equity - total_im)

    def can_open_position(self, current_prices: Dict[str, float], max_positions: int = 2) -> bool:
        if self.is_liquidated:
            return False
        if len(self.positions) >= max_positions:
            return False
        free_margin = self.get_free_margin(current_prices)
        # Need at least $2 free margin to open a position
        return free_margin >= 2.0

    def check_liquidation(self, bar_prices: Dict[str, Dict[str, float]], timestamp_str: str, bar_idx: int) -> bool:
        """
        Pessimistic intra-candle liquidation check.
        Evaluates the worst adverse price for each open position during the bar.
        """
        if self.is_liquidated or not self.positions:
            return self.is_liquidated
            
        worst_prices = {}
        for symbol, pos in self.positions.items():
            if symbol not in bar_prices:
                continue
            candle = bar_prices[symbol]
            # Worst case for LONG is the low; for SHORT is the high
            if pos.side == Side.LONG:
                worst_prices[symbol] = candle["low"]
            else:
                worst_prices[symbol] = candle["high"]
                
        worst_equity = self.wallet_balance + self.get_unrealized_pnl(worst_prices)
        worst_mm = self.get_total_maintenance_margin(worst_prices)
        
        if worst_equity <= worst_mm or worst_equity <= 0.0:
            # LIQUIDATION TRIGGERED
            self.is_liquidated = True
            self.liquidation_time = timestamp_str
            self.liquidation_bar_idx = bar_idx
            
            # Close all positions as liquidated
            for symbol, pos in list(self.positions.items()):
                self.trade_counter += 1
                exit_price = worst_prices.get(symbol, pos.entry_price)
                if pos.side == Side.LONG:
                    pnl = (exit_price - pos.entry_price) * pos.current_qty
                else:
                    pnl = (pos.entry_price - exit_price) * pos.current_qty
                    
                record = TradeRecord(
                    trade_id=self.trade_counter,
                    symbol=symbol,
                    side=pos.side.value,
                    entry_time=str(pos.entry_time),
                    exit_time=timestamp_str,
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    qty=pos.initial_qty,
                    notional=pos.entry_price * pos.initial_qty,
                    margin_used=pos.allocated_margin,
                    leverage=pos.leverage,
                    gross_pnl=pnl + pos.accumulated_realized_pnl,
                    commission=pos.total_commission_paid,
                    net_pnl=-pos.allocated_margin,  # Capital lost
                    return_on_margin_pct=-100.0,
                    exit_reason=ExitReason.LIQUIDATION.value,
                    holding_hours=(bar_idx - pos.entry_bar_idx) * 0.25,
                    max_floating_dd_pct=100.0,
                    tp1_hit=pos.tp1_hit,
                    tp2_hit=False
                )
                self.closed_trades.append(record)
                
            self.positions.clear()
            self.wallet_balance = 0.0
            return True
            
        return False

    def update_drawdown(self, current_prices: Dict[str, float]):
        equity = self.get_equity(current_prices)
        if equity > self.peak_equity:
            self.peak_equity = equity
        if self.peak_equity > 0:
            dd = (self.peak_equity - equity) / self.peak_equity * 100.0
            if dd > self.max_drawdown_pct:
                self.max_drawdown_pct = dd
