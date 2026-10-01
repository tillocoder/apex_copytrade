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
    timeframe: str = "5m"                 # M5 Timeframe (5-minute execution)
    default_leverage: int = 50            # 50x Leverage
    default_margin_usd: float = 25.00     # Baseline margin
    approx_notional_usd: float = 1250.00  # Target notional
    max_open_positions: int = 1           # Exactly 1 position at a time
    one_way_mode: bool = True             # One-way mode (no dual side)
    allow_long: bool = True               # LONG enabled
    allow_short: bool = True              # SHORT enabled
    
    # Capital Growth & Risk Management (1% Risk Model)
    initial_balance_usd: float = 1000.00  # $1,000 Starting Account for Paper Test
    max_risk_pct_balance: float = 0.01    # Strictly 1.0% account risk per trade
    
    # Session Profit & Loss Targets (Calibrated to 1% Risk = $10/R)
    session_profit_target_usd: float = 200.00 # Session profit target (+$200 = 20R)
    max_session_loss_usd: float = 50.00       # -$50 (5R / 5% balance limit)
    max_daily_loss_usd: float = 50.00         # -$50 daily loss limit
    max_daily_loss_pct: float = 0.05          # 5% max daily drawdown
    max_session_loss_pct: float = 0.05        # 5% max session drawdown
    max_consecutive_losses: int = 3           # 3 losses trigger extended cooldown
    cooldown_normal_sec: int = 300            # 300s (1 M5 bar) cooldown after normal trade
    cooldown_loss_sec: int = 600              # 600s (2 M5 bars) cooldown after loss
    max_trades_per_session: int = 3           # Max 3 trades per 24h day (institutional discipline)
    cooldown_bars: int = 2                    # 2 M5 bars cooldown
    
    # M5 SuperTrend + H1 EMA200 Strategy Core Parameters
    strategy_name: str = "M5_SUPERTREND_H1_EMA200"
    st_period: int = 10                       # SuperTrend ATR Period (10)
    st_multiplier: float = 2.5                # SuperTrend Multiplier (2.5)
    h1_ema_period: int = 200                  # Macro Trend Filter: H1 EMA 200
    volume_ratio_min: float = 1.3             # Volume >= 1.3x 10-bar average
    session_start_hour_utc: int = 7           # 07:00 UTC (12:00 Tashkent)
    session_end_hour_utc: int = 21            # 21:00 UTC (02:00 Tashkent)
    
    # Professional SL / TP Model
    exit_model: str = "2R_FULL_TARGET"        # Audited 2.0R Target Model
    tp1_r: float = 2.00                       # Take Profit: 2.0R
    tp2_r: float = 2.00                       # Full exit at 2.0R
    tp1_close_pct: float = 1.00               # 100% exit at 2.0R target
    min_sl_dist: float = 10.0                 # Minimum $10.00 SL distance
    sl_buffer_atr: float = 0.20               # SuperTrend line + 0.20 ATR buffer
    min_r_dist: float = 10.0                  # Minimum $10.00 R distance
    be_fee_buffer_pct: float = 0.0005         # 0.05% buffer over entry for Breakeven
    be_mode: str = "NO_BE"                    # Preserve structural stops, avoid premature BE scratches
    
    # Execution & Fee Model (Post-Only Maker)
    execution_mode: str = "MAKER_POST_ONLY"
    post_only_entry: bool = True
    entry_fee_rate: float = 0.0002            # 0.02% Maker Post-Only
    tp_fee_rate: float = 0.0002               # 0.02% Maker Limit TP
    sl_fee_rate: float = 0.0005               # 0.05% Taker Stop Market
    
    # Safety Filters
    max_allowed_spread_usd: float = 0.25      # Spread <= $0.25 USDT
    stale_data_timeout_sec: float = 30.0      # Data timeout
    emergency_sl_timeout_sec: float = 5.0     # Emergency SL placement timeout
    min_atr_m5: float = 1.50                  # Minimum M5 ATR
    
    # Binance Endpoints (Official Futures API)
    rest_base_url: str = "https://fapi.binance.com"
    ws_base_url: str = "wss://fstream.binance.com/market/stream"
    
    # Operational Modes: Strictly PAPER
    mode: str = "PAPER"
    is_running: bool = True
    live_enabled: bool = False                # Strictly False for paper test
    shadow_mode: bool = True                  # Realtime shadow calculation active
    
    # Exchange Filters (Updated dynamically from /fapi/v1/exchangeInfo)
    tick_size: float = 0.01
    step_size: float = 0.001
    min_qty: float = 0.001
    min_notional: float = 20.0                 # Binance minNotional for ETHUSDT is $20
    
    # Active Trading Sessions (07:00 - 21:00 UTC Active Liquidity Window)
    session_mode: str = "INSTITUTIONAL_WINDOW_07_21"
    enabled_sessions: Dict[str, bool] = field(default_factory=lambda: {
        "ASIA": True,
        "LONDON": True,
        "LONDON_NY_OVERLAP": True,
        "NEW_YORK": True
    })

DEFAULT_CONFIG = BinanceFuturesConfig()

