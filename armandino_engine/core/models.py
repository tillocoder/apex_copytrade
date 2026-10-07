"""
Armandino Engine - Data Models
Defines core data structures for candles, orders, positions, trades, and portfolio state.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict


class Side(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ExitReason(Enum):
    TP1 = "TP1"
    TP2 = "TP2"
    STOP_LOSS = "STOP_LOSS"
    DRAWDOWN_CUT = "DRAWDOWN_CUT"
    TIME_EXPIRED = "TIME_EXPIRED"
    LIQUIDATION = "LIQUIDATION"
    END_OF_DATA = "END_OF_DATA"


@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    datetime_str: str


@dataclass
class Position:
    symbol: str
    side: Side
    entry_price: float
    initial_qty: float
    current_qty: float
    entry_time: int
    entry_bar_idx: int
    leverage: float
    allocated_margin: float
    tp1_price: float
    tp2_price: float
    tp1_hit: bool = False
    stop_loss_price: Optional[float] = None
    max_adverse_pct: float = 0.0
    max_favorable_pct: float = 0.0
    accumulated_realized_pnl: float = 0.0
    total_commission_paid: float = 0.0


@dataclass
class TradeRecord:
    trade_id: int
    symbol: str
    side: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    qty: float
    notional: float
    margin_used: float
    leverage: float
    gross_pnl: float
    commission: float
    net_pnl: float
    return_on_margin_pct: float
    exit_reason: str
    holding_hours: float
    max_floating_dd_pct: float
    tp1_hit: bool
    tp2_hit: bool


@dataclass
class ScenarioConfig:
    name: str
    has_hard_sl: bool
    sl_pct: float = 0.018              # 1.8% hard SL for Scenario B
    max_floating_dd_pct: float = 0.40  # 40% margin DD cut for Scenario A
    max_holding_hours: float = 36.0    # 36 hours max holding for Scenario A
    min_holding_hours: float = 2.0     # 2 hours minimum holding for pullback
    tp1_pct: float = 0.010             # +1.0% price move
    tp1_close_ratio: float = 0.50      # Close 50%
    tp2_pct: float = 0.025             # +2.5% price move
    leverage: float = 15.0             # 15x leverage
    margin_fraction: float = 0.20      # 20% of balance per trade ($4 on $20)
    max_concurrent_positions: int = 2   # Max 2 simultaneous open positions
    maker_fee: float = 0.0002          # 0.02% maker
    taker_fee: float = 0.0005          # 0.05% taker
    slippage_bps: float = 2.0          # 2 bps slippage on market orders
