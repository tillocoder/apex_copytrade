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
    max_daily_loss_usd: float = 1.70          # -$2.50 max daily loss limit
    max_consecutive_losses: int = 3           # 3 losses trigger extended cooldown
    cooldown_normal_sec: int = 60             # 60s cooldown after trade
    cooldown_loss_sec: int = 180              # 180s cooldown after loss
    max_trades_per_session: int = 30          # Maximum trades per active session
    
    # Professional 2-Stage SL / TP Model
    tp1_r: float = 1.0                        # TP1: 1R
    tp1_close_pct: float = 0.50               # Close 50% position at TP1
    tp2_r: float = 2.0                        # TP2: 2R (Close remaining 50%)
    be_fee_buffer_pct: float = 0.0006         # 0.06% buffer over entry for Breakeven (covers 0.10% roundtrip fees)
    min_sl_pct: float = 0.0025                # Min SL 0.25% (protects from M1 noise shakeouts)
    max_sl_pct: float = 0.0085                # Max SL 0.85% (caps risk)
    
    # Strategy Scoring & Entry Quality
    min_score_threshold: int = 65             # Confluence score >= 65/100 required
    anti_chase_max_body_atr: float = 2.2      # Skip entry if signal candle body > 2.2x ATR
    
    # Safety Filters
    max_allowed_spread_usd: float = 0.15      # Spread <= $0.15 USDT
    stale_data_timeout_sec: float = 5.0       # Ticks older than 5s rejected
    emergency_sl_timeout_sec: float = 2.0     # If SL not placed in 2s, emergency market close!
    min_atr_m1: float = 0.25                   # Anti-chop minimum ATR
    max_atr_multiplier: float = 3.5           # Abnormal volatility spike filter
    
    # Binance Endpoints
    rest_base_url: str = "https://fapi.binance.com"
    ws_base_url: str = "wss://fstream.binance.com/stream"
    
    # Operational Modes: "BACKTEST", "PAPER", "LIVE"
    mode: str = "LIVE" if (os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_FUTURES_MODE", "LIVE").upper() == "LIVE") else "PAPER"
    is_running: bool = True
    live_enabled: bool = bool(os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_FUTURES_MODE", "LIVE").upper() == "LIVE")
    
    # Exchange Filters (Updated dynamically from /fapi/v1/exchangeInfo)
    tick_size: float = 0.01
    step_size: float = 0.001
    min_qty: float = 0.001
    min_notional: float = 20.0                # Binance minNotional for ETHUSDT is $20
    
    # Active Trading Sessions (Tashkent Time UTC+5)
    enabled_sessions: Dict[str, bool] = field(default_factory=lambda: {
        "ASIA": True,
        "LONDON": True,
        "NEW_YORK": True,
        "LONDON_NY_OVERLAP": True
    })

DEFAULT_CONFIG = BinanceFuturesConfig()
