from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

@dataclass
class PropFirmRulesConfig:
    initial_capital: float = 10000.0
    stage1_target_pct: float = 0.08  # +8% ($800)
    stage2_target_pct: float = 0.05  # +5% ($500)
    max_daily_drawdown_pct: float = 0.05  # 5.0% ($500)
    max_total_drawdown_pct: float = 0.10  # 10.0% ($1000)
    enforce_stage_reset: bool = True  # Balance resets to $10,000 after Stage 1

    # Institutional Risk & Margin Limits
    # NOTE: Prop firm leverage = 2x crypto (FTMO, Topstep, etc.)
    # 20x leverage is NOT allowed on standard prop firm accounts.
    # With 2x leverage: $10K account can open max $20K notional per position.
    # We cap further to 1.5x equity = $15K per position for safety.
    risk_per_trade_pct: float = 0.015       # 1.5% base risk ($150 on $10k)
    min_sl_distance_pct: float = 0.005     # 0.50% minimum SL distance floor
    max_single_position_notional_mult: float = 1.5   # Max 1.5x equity per position ($15k on $10k)
    max_total_notional_exposure_mult: float = 3.0    # Max 3.0x total portfolio notional ($30k on $10k)
    max_crypto_portfolio_risk_pct: float = 0.03      # Max 3.0% aggregate planned risk ($300 on $10k)
    max_margin_utilization_pct: float = 0.80         # Max 80% capital used as margin (no artificial leverage)
    maintenance_margin_rate: float = 0.05            # 5.0% maintenance margin
    fee_buffer_pct: float = 0.0008          # 0.08% roundtrip fee buffer
    slippage_buffer_pct: float = 0.0005     # 0.05% slippage buffer
    funding_buffer_usd: float = 0.0         # $0 default funding buffer
    default_leverage: float = 2.0           # 2x prop firm leverage (FTMO crypto standard)
    symbol_leverage_map: Dict[str, float] = field(default_factory=lambda: {
        "BTC/USDT": 2.0,
        "ETH/USDT": 2.0,
        "SOL/USDT": 2.0
    })
    max_position_margin_pct: float = 0.40   # 40% of equity max per position = $4,000 margin ($8,000 notional = ~1% risk)

@dataclass
class ExecutionConfig:
    commission_pct: float = 0.0004  # 0.04% maker/taker ($4 per $10k traded per side)
    spread_bps: float = 1.0  # 1.0 basis point (0.01% spread)
    slippage_bps: float = 1.0  # 1.0 basis point (0.01% adverse slippage)
    spread_pips: float = 1.0
    slippage_pips: float = 1.0
    funding_rate_8h: float = 0.0001  # 0.01% per 8-hour funding rate (perpetual stress test)
    enable_funding_fee: bool = False  # Set True for perpetual funding stress test
    intrabar_sl_tp_mode: str = "CONSERVATIVE"  # "CONSERVATIVE", "DIRECTIONAL", "OPTIMISTIC"
    latency_ms: int = 50  # 50ms network delay
    partial_fill_prob: float = 0.02  # 2% partial fill probability
    missed_fill_prob: float = 0.01  # 1% missed limit fill probability

@dataclass
class RiskConfig:
    base_risk_pct: float = 0.015    # 1.50% base risk per trade
    min_risk_pct: float = 0.005     # 0.50% min risk
    max_risk_pct: float = 0.020     # 2.00% max risk (raised from 1.5% for high-conf trades)
    max_open_positions: int = 2     # Max 2 simultaneous: BTC + ETH only
    daily_max_losses: int = 3       # Pause trading after 3 consecutive daily losses
    equity_protection_buffer: float = 0.80

@dataclass
class StrategyConfig:
    timeframe: str = "M15"
    confidence_threshold: float = 75.0    # Raised from 70 → 75 (stricter quality)
    ema_fast: int = 20
    ema_slow: int = 50
    ema_trend: int = 200
    atr_period: int = 14
    atr_multiplier_sl: float = 1.2        # Tighter SL (was 1.5)
    atr_multiplier_tp: float = 3.0        # Wider TP = 3:1 RR (was 2.0)
    fvg_min_size_atr: float = 0.5  # FVG must be at least 0.5 ATR
    session_filters: List[str] = field(default_factory=lambda: ["LONDON", "NEW_YORK"])

class EngineMode(Enum):
    PROP_FIRM = "PROP_FIRM"
    PORTFOLIO = "PORTFOLIO"

@dataclass
class EngineConfig:
    mode: EngineMode = EngineMode.PROP_FIRM
    prop_rules: PropFirmRulesConfig = field(default_factory=PropFirmRulesConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
