import time
import math
from typing import Dict, Any, Tuple, Optional

from .config import DEFAULT_CONFIG
from .market_data import MarketDataManager
from .database import get_session_stats

class RiskManager:
    """
    $2.50 Account Growth & Capital Preservation Engine:
    - Step-Based Compounding ($2.50 -> $5.00 -> $10.00 -> $20.00+)
    - Strict Anti-Revenge Loss Protection (Never increases margin or leverage after loss)
    - Dynamic Dollar Risk Clipping: Ensures maximum dollar loss per trade stays <= safe threshold
    - Session Target Gate ($2.00 target reached = clean halt)
    - Consecutive Loss Circuit Breakers
    """
    def __init__(self, market_data: MarketDataManager):
        self.md = market_data
        self.session_key = time.strftime('%Y-%m-%d_UTC', time.gmtime())
        self.current_balance = DEFAULT_CONFIG.initial_balance_usd
        self.session_pnl = 0.0
        self.daily_pnl = 0.0
        self.trades_count = 0
        self.consecutive_losses = 0
        self.last_trade_time = 0.0
        self.last_trade_pnl = 0.0
        self.cooldown_until = 0.0
        self.target_reached = False
        self.emergency_stop_triggered = False

        self._load_session_state()

    def _load_session_state(self):
        stats = get_session_stats(self.session_key)
        self.session_pnl = float(stats.get("session_pnl", 0.0))
        self.trades_count = int(stats.get("trades_count", 0))
        if self.session_pnl >= DEFAULT_CONFIG.session_profit_target_usd:
            self.target_reached = True

    def sync_live_balance(self, live_balance: float):
        """Updates internal balance from Binance live account."""
        if live_balance > 0:
            self.current_balance = live_balance

    def reset_session(self):
        self.session_key = time.strftime('%Y-%m-%d_UTC', time.gmtime())
        self.session_pnl = 0.0
        self.trades_count = 0
        self.consecutive_losses = 0
        self.cooldown_until = 0.0
        self.target_reached = False
        self.emergency_stop_triggered = False

    def trigger_emergency_stop(self):
        self.emergency_stop_triggered = True

    def get_compounding_tier(self) -> Dict[str, Any]:
        """
        Step-based capital compounding scale:
        Tier 0: < $2.50 -> $0.40 - $0.50 margin (survival mode)
        Tier 1: $2.50 - $4.99 -> $0.50 margin
        Tier 2: $5.00 - $9.99 -> $0.80 margin
        Tier 3: $10.00 - $19.99 -> $1.50 margin
        Tier 4: $20.00+ -> min(8% balance, $5.00)
        """
        bal = self.current_balance

        if bal < 2.50:
            tier_name = "Survival Tier (Sub-$2.50)"
            target_margin = 0.45
        elif bal < 5.00:
            tier_name = "Tier 1 ($2.50 - $5.00)"
            target_margin = 0.50
        elif bal < 10.00:
            tier_name = "Tier 2 ($5.00 - $10.00)"
            target_margin = 0.80
        elif bal < 20.00:
            tier_name = "Tier 3 ($10.00 - $20.00)"
            target_margin = 1.50
        else:
            tier_name = "Tier 4 Scaling ($20+)"
            target_margin = min(bal * 0.08, 5.00)

        # Anti-Revenge Loss Protection:
        # If last trade was a loss, strictly clamp margin to prevent revenge compounding
        if self.last_trade_pnl < 0:
            target_margin = min(target_margin, DEFAULT_CONFIG.default_margin_usd)

        return {
            "tier": tier_name,
            "balance": round(bal, 2),
            "targetMargin": round(target_margin, 2),
            "leverage": DEFAULT_CONFIG.default_leverage
        }

    def calculate_order_sizing(self, price: float, filters: Dict[str, Any], sl_distance: float = 0.0) -> Dict[str, Any]:
        """
        Calculates position size with:
        1. Compounding tier margin
        2. Maximum dollar risk clipping
        3. Binance stepSize & minNotional compliance
        """
        step_size = float(filters.get("stepSize", DEFAULT_CONFIG.step_size))
        min_qty = float(filters.get("minQty", DEFAULT_CONFIG.min_qty))
        min_notional = float(filters.get("minNotional", DEFAULT_CONFIG.min_notional))
        leverage = DEFAULT_CONFIG.default_leverage

        tier_info = self.get_compounding_tier()
        target_margin = tier_info["targetMargin"]
        target_notional = target_margin * leverage # e.g. $0.50 * 100 = $50.00

        # Raw quantity
        raw_qty = target_notional / max(1.0, price)
        decimals = max(0, int(round(-math.log10(step_size)))) if step_size > 0 else 3
        qty = round(math.floor(raw_qty / step_size) * step_size, decimals)

        # Maximum Dollar Risk Guard for $2.50 account
        # Max allowable dollar loss per trade = min(balance * max_risk_pct, $0.35)
        if sl_distance > 0:
            max_allowed_dollar_risk = max(0.15, min(self.current_balance * DEFAULT_CONFIG.max_risk_pct_balance, 0.40))
            dollar_risk = sl_distance * qty
            if dollar_risk > max_allowed_dollar_risk:
                capped_qty = max_allowed_dollar_risk / sl_distance
                qty = round(math.floor(capped_qty / step_size) * step_size, decimals)

        # Ensure minQty
        if qty < min_qty:
            qty = min_qty

        # Ensure minNotional
        actual_notional = qty * price
        if actual_notional < min_notional:
            qty = round(math.ceil(min_notional / price / step_size) * step_size, decimals)
            actual_notional = qty * price

        actual_margin = actual_notional / leverage

        return {
            "quantity": qty,
            "notional": round(actual_notional, 2),
            "margin": round(actual_margin, 4),
            "leverage": leverage,
            "tier": tier_info["tier"]
        }

    def check_preflight_risk(self, has_open_position: bool, is_live_mode: bool) -> Dict[str, Any]:
        """
        Evaluates pre-flight risk filters:
        - Emergency Stop
        - Session Profit Target ($2.00)
        - Max Open Position (1)
        - Session Loss Limit (-$1.50)
        - Daily Loss Limit (-$2.50)
        - Cooldown Timer
        - Consecutive Losses
        - Stale Data
        - Spread Check
        """
        now = time.time()

        if self.emergency_stop_triggered:
            return {"can_trade": False, "reason": "EMERGENCY STOP ACTIVE: Manual reset required"}

        # 1. Session Profit Target ($2)
        if self.target_reached or self.session_pnl >= DEFAULT_CONFIG.session_profit_target_usd:
            self.target_reached = True
            return {
                "can_trade": False,
                "reason": f"Session Target Reached: Net profit +${self.session_pnl:.2f} >= ${DEFAULT_CONFIG.session_profit_target_usd:.2f}. Halting entries."
            }

        # 2. Max Open Position
        if has_open_position:
            return {"can_trade": False, "reason": "Position Active: Max 1 open position allowed"}

        # 3. Session Loss Limit
        if self.session_pnl <= -abs(DEFAULT_CONFIG.max_session_loss_usd):
            return {"can_trade": False, "reason": f"Session Loss Limit Hit: PnL ${self.session_pnl:.2f} <= -${DEFAULT_CONFIG.max_session_loss_usd:.2f}"}

        # 4. Daily Loss Limit
        if self.daily_pnl <= -abs(DEFAULT_CONFIG.max_daily_loss_usd):
            return {"can_trade": False, "reason": f"Daily Loss Limit Hit: PnL ${self.daily_pnl:.2f} <= -${DEFAULT_CONFIG.max_daily_loss_usd:.2f}"}

        # 5. Cooldown Timer
        if now < self.cooldown_until:
            rem = int(self.cooldown_until - now)
            return {"can_trade": False, "reason": f"Cooldown Active: {rem}s remaining before next allowed trade"}

        # 6. Consecutive Losses Circuit Breaker
        if self.consecutive_losses >= DEFAULT_CONFIG.max_consecutive_losses:
            rem = int(self.cooldown_until - now) if self.cooldown_until > now else 0
            if rem > 0:
                return {"can_trade": False, "reason": f"Consecutive Losses (3x): Risk cooling down ({rem}s)"}

        # 7. Max Trades Limit
        if self.trades_count >= DEFAULT_CONFIG.max_trades_per_session:
            return {"can_trade": False, "reason": f"Max Trades Limit: {self.trades_count}/{DEFAULT_CONFIG.max_trades_per_session} trades completed"}

        # 8. Stale Data Filter
        if self.md.is_data_stale(DEFAULT_CONFIG.stale_data_timeout_sec):
            return {"can_trade": False, "reason": "Stale Data: WebSocket feed lag > 5 seconds"}

        # 9. Spread Filter
        spread_info = self.md.get_spread()
        if not spread_info.get("acceptable", True):
            return {"can_trade": False, "reason": f"Spread Too High: {spread_info.get('spread_usd', 0):.2f} USDT > ${DEFAULT_CONFIG.max_allowed_spread_usd}"}

        return {
            "can_trade": True,
            "reason": f"Risk Clear | Session PnL: ${self.session_pnl:+.2f} / $2.00 target"
        }

    def record_trade_completion(self, pnl: float):
        now = time.time()
        self.session_pnl += pnl
        self.daily_pnl += pnl
        self.current_balance += pnl
        self.trades_count += 1
        self.last_trade_time = now
        self.last_trade_pnl = pnl

        is_win = pnl > 0
        if is_win:
            self.consecutive_losses = 0
            self.cooldown_until = now + DEFAULT_CONFIG.cooldown_normal_sec
        else:
            self.consecutive_losses += 1
            if self.consecutive_losses >= DEFAULT_CONFIG.max_consecutive_losses:
                self.cooldown_until = now + 900  # 15 min extended cooling
            else:
                self.cooldown_until = now + DEFAULT_CONFIG.cooldown_loss_sec

        if self.session_pnl >= DEFAULT_CONFIG.session_profit_target_usd:
            self.target_reached = True

    def get_risk_summary(self) -> Dict[str, Any]:
        target_progress = min(100.0, max(0.0, (self.session_pnl / DEFAULT_CONFIG.session_profit_target_usd) * 100.0))
        tier_info = self.get_compounding_tier()
        return {
            "sessionProfitTarget": DEFAULT_CONFIG.session_profit_target_usd,
            "sessionPnl": round(self.session_pnl, 2),
            "targetProgressPct": round(target_progress, 1),
            "targetReached": self.target_reached,
            "tradesCount": self.trades_count,
            "maxTrades": DEFAULT_CONFIG.max_trades_per_session,
            "consecutiveLosses": self.consecutive_losses,
            "cooldownSecondsRemaining": max(0, int(self.cooldown_until - time.time())),
            "emergencyStop": self.emergency_stop_triggered,
            "maxSessionLoss": DEFAULT_CONFIG.max_session_loss_usd,
            "maxDailyLoss": DEFAULT_CONFIG.max_daily_loss_usd,
            "compoundingTier": tier_info["tier"],
            "targetMargin": tier_info["targetMargin"]
        }
