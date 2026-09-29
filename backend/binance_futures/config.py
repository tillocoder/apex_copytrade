import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

def load_env_file():
    """Dynamically parses .env in project root or current working dir."""
    env_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        ".env",
        os.path.expanduser("~/.env"),
        "/data/data/com.termux/files/home/apex_copytrade/.env"
    ]
    for p in env_paths:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k not in os.environ or not os.environ[k]:
                                os.environ[k] = v
            except Exception:
                pass

load_env_file()

@dataclass
class BinanceFuturesConfig:
    # Asset & Symbols
    symbol: str = "ETHUSDT"               # Binance API Symbol
    display_symbol: str = "ETHUSDT.P"     # UI Display Symbol
    base_asset: str = "ETH"
    quote_asset: str = "USDT"
    
    # Trading Defaults
    timeframe: str = "1m"                 # M1 Timeframe
    default_leverage: int = 100           # 100x Leverage
    default_margin_usd: float = 0.50      # $0.50 initial target margin
    approx_notional_usd: float = 50.00    # ~$50 = $0.50 * 100
    max_open_positions: int = 1           # Exactly 1 position at a time
    one_way_mode: bool = True             # One-way mode (no dual side)
    allow_long: bool = True               # LONG enabled
    allow_short: bool = True              # SHORT enabled
    
    # Capital Growth & Compounding ($2.50 Starting Account)
    initial_balance_usd: float = 2.50     # $2.50 starting balance
    max_risk_pct_balance: float = 0.12    # Max 12% account risk per trade
    
    # Session Profit & Loss Targets
    session_profit_target_usd: float = 2.00   # SESSION_PROFIT_TARGET = $2.00 (not per-trade TP)
    max_session_loss_usd: float = 1.70        # -$1.50 max session loss limit
    max_daily_loss_usd: float = 1.70
    max_daily_loss_pct: float = 0.15
    max_session_loss_pct: float = 0.15          # -$2.50 max daily loss limit
    max_consecutive_losses: int = 3           # 3 losses trigger extended cooldown
    cooldown_normal_sec: int = 60             # 60s cooldown after trade
    cooldown_loss_sec: int = 180              # 180s cooldown after loss
    max_trades_per_session: int = 30          # Maximum trades per active session
    
    # Professional SL / TP Model
    exit_model: str = "G"                     # Model G: Dynamic Volatility Target (v3.3 Production)
    tp1_r: float = 2.50                       # Dynamic TP baseline R (2.5x ATR dynamic multiplier)
    tp1_close_pct: float = 1.00              # Single full expansion target
    tp2_r: float = 2.50                       # Secondary target
    be_fee_buffer_pct: float = 0.0005        # 0.05% buffer over entry for Breakeven
    min_sl_pct: float = 0.0020               # Min SL 0.20%
    max_sl_pct: float = 0.0085               # Max SL 0.85%
    be_mode: str = "NO_BE"                   # v3.3: Eliminate premature breakeven noise
    tp_vol_multiplier: float = 2.5           # 2.5x dynamic ATR multiplier
    
    # Strategy Scoring & Entry Quality (v3.3 Production Model)
    min_score_threshold: int = 78            # Quality Score >= 78/100 required
    anti_chase_max_body_atr: float = 2.5     # Skip entry if signal candle body > 2.5x ATR
    location_filter_enabled: bool = True     # Penalize range midpoint chop
    fee_risk_gate_ratio: float = 0.25        # Reject if fee burden > 25% of R
    min_r_dist: float = 4.0                  # Minimum $4.00 stop distance to filter M1 micro-noise
    
    # M15 Macro Regime & Volatility Compression Gates
    m15_adx_filter_enabled: bool = True
    m15_adx_threshold: float = 22.0          # Block breakouts when M15 ADX < 22
    m15_vol_compression_gate: bool = True
    m15_vol_compression_ratio: float = 0.85  # Reject when M15 ATR < 85% of EMA50
    
    # Fee Elimination & Execution Model
    execution_mode: str = "MAKER_ENTRY_HYBRID"
    post_only_entry: bool = True
    entry_fee_rate: float = 0.0002           # 0.02% Maker Post-Only
    tp_fee_rate: float = 0.0002              # 0.02% Maker Limit TP
    sl_fee_rate: float = 0.0005              # 0.05% Taker Stop Market
    
    # Safety Filters
    max_allowed_spread_usd: float = 0.15     # Spread <= $0.15 USDT
    stale_data_timeout_sec: float = 5.0      # Ticks older than 5s rejected
    emergency_sl_timeout_sec: float = 2.0    # If SL not placed in 2s, emergency market close!
    min_atr_m1: float = 0.25                 # Anti-chop minimum ATR (0.25 USDT)
    max_atr_multiplier: float = 3.5          # Abnormal volatility spike filter
    
    # Binance Endpoints
    rest_base_url: str = "https://fapi.binance.com"
    ws_base_url: str = "wss://fstream.binance.com/stream"
    
    # Operational Modes: Strictly PAPER / NO-ENTRY until validation gates pass
    mode: str = "PAPER"
    is_running: bool = True
    live_enabled: bool = False               # MUST REMAIN FALSE: Paper mode until final approval
    shadow_mode: bool = True                 # Realtime shadow calculation active
    
    # Exchange Filters (Updated dynamically from /fapi/v1/exchangeInfo)
    tick_size: float = 0.01
    step_size: float = 0.001
    min_qty: float = 0.001
    min_notional: float = 20.0                # Binance minNotional for ETHUSDT is $20
    
    # Active Trading Sessions (London & Overlap Volatility Expansion Focus)
    session_mode: str = "LONDON_EXPANSION_ONLY"
    enabled_sessions: Dict[str, bool] = field(default_factory=lambda: {
        "ASIA": False,
        "LONDON": True,
        "LONDON_NY_OVERLAP": True,
        "NEW_YORK": False                    # Late NY consolidation noise blocked in v3.3
    })

DEFAULT_CONFIG = BinanceFuturesConfig()

