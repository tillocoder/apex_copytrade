"""
FINAL_ROBUST_ALGOTRADER — Production Configuration
===================================================
Frozen parameters for Multi-Strategy Ensemble:
1. BTCUSDT — 1H EMA Trend Pullback
2. ETHUSDT — 1H EMA Trend Pullback
3. BTCUSDT — 1H Donchian 48H Breakout

Cost Model C: 0.12% Round-Trip (0.04% commission + 0.02% slippage per side)
Prop Model: $10,000 account, Phase 1: +8%, Phase 2: +5%, Daily DD: 5%, Max DD: 10%
Two Parallel Accounts: 45-day stagger
Default Production Risk: 1.00% per trade
"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class MarketDataConfig:
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    primary_timeframe: str = "1H"
    htf_timeframe: str = "4H"
    btc_cache_path: str = "c:/apex_copytrade/backend/data/btc_1y_klines_cache.json"
    eth_cache_path: str = "c:/apex_copytrade/backend/data/ethusdt_1y_klines_cache.json"
    min_warmup_bars: int = 250

@dataclass
class StrategyAConfig:
    """Strategy A: 1H EMA Trend Pullback (BTC & ETH)"""
    name: str = "EMA_Trend_Pullback"
    htf_ema_period: int = 50          # 4H EMA50 for macro trend
    ltf_ema_period: int = 50          # 1H EMA50 for immediate trend
    rsi_period: int = 14              # 14-period RSI
    rsi_pullback_long: float = 45.0   # RSI < 45 for Long pullback
    rsi_pullback_short: float = 55.0  # RSI > 55 for Short pullback
    volume_multiplier: float = 1.10   # Volume > 1.1x 20-period MA
    min_atr_pct: float = 0.15         # Minimum ATR%
    max_atr_pct: float = 4.00         # Maximum ATR%
    sl_atr_multiplier: float = 1.50   # 1.5x ATR Stop Loss
    tp1_atr_multiplier: float = 2.00  # 2.0x ATR TP1 (closes 50%)
    tp2_atr_multiplier: float = 3.00  # 3.0x ATR TP2 (closes remaining 50%)
    breakeven_on_tp1: bool = True     # Move SL to Entry after TP1

@dataclass
class StrategyBConfig:
    """Strategy B: 1H Donchian 48H Breakout (BTC Only)"""
    name: str = "Donchian_48H_Breakout"
    symbol: str = "BTCUSDT"
    lookback_bars: int = 48           # 48 hours swing high/low
    trend_ema_period: int = 200       # 200H EMA trend filter
    volume_multiplier: float = 1.30   # Volume > 1.3x 20-period MA
    min_atr_pct: float = 0.15
    max_atr_pct: float = 4.00
    sl_atr_multiplier: float = 2.00   # 2.0x ATR Stop Loss
    tp1_atr_multiplier: float = 3.00  # 3.0x ATR TP1 (closes 50%)
    tp2_atr_multiplier: float = 4.50  # 4.5x ATR TP2 (closes remaining 50%)
    breakeven_on_tp1: bool = True     # Move SL to Entry after TP1

@dataclass
class RiskConfig:
    default_risk_per_trade_pct: float = 0.0100   # 1.00% default production risk
    stress_risk_per_trade_pct: float = 0.0125    # 1.25% stress configuration
    max_portfolio_correlated_risk_pct: float = 0.0150 # Max 1.50% total concurrent risk on BTC+ETH
    max_daily_trades_per_account: int = 4        # Cap trades per account per day
    max_open_positions_per_symbol: int = 1       # 1 active position per symbol per account
    cooldown_bars_after_loss: int = 2            # 2 hours cooldown after a loss

@dataclass
class PropFirmConfig:
    initial_balance: float = 10000.0             # $10,000 account
    phase_1_target_pct: float = 0.08             # +8% ($800)
    phase_2_target_pct: float = 0.05             # +5% ($500)
    max_daily_drawdown_pct: float = 0.05         # 5% hard limit ($500)
    daily_dd_warning_pct: float = 0.0350         # 3.50% internal warning
    daily_dd_halt_pct: float = 0.0425            # 4.25% internal halt (safety buffer)
    max_total_drawdown_pct: float = 0.10         # 10% hard limit ($1,000)
    total_dd_warning_pct: float = 0.0600         # 6.00% internal warning
    total_dd_reduce_risk_pct: float = 0.0750     # 7.50% throttle risk to 0.50%
    total_dd_halt_pct: float = 0.0850            # 8.50% internal halt
    parallel_accounts_count: int = 2             # 2 parallel challenge accounts
    account_stagger_days: int = 45               # 45-day stagger between accounts

@dataclass
class ExecutionConfig:
    commission_per_side_pct: float = 0.0004      # 0.04% VIP/Prop commission
    slippage_per_side_pct: float = 0.0002        # 0.02% realistic slippage
    # Total Round-Trip = (0.0004 + 0.0002) * 2 = 0.0012 (0.12% Cost C)
    price_precision_btc: int = 2
    qty_precision_btc: int = 3
    min_qty_btc: float = 0.001
    price_precision_eth: int = 2
    qty_precision_eth: int = 3
    min_qty_eth: float = 0.01
    max_allowed_spread_pct: float = 0.0005       # 0.05% max spread before entry block

@dataclass
class ProductionConfig:
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    strategy_a: StrategyAConfig = field(default_factory=StrategyAConfig)
    strategy_b: StrategyBConfig = field(default_factory=StrategyBConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    prop: PropFirmConfig = field(default_factory=PropFirmConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    mode: str = "PAPER"                          # "PAPER", "SHADOW", or "LIVE"
