import time
import math
from typing import Dict, Any, Tuple, Optional

from .config import DEFAULT_CONFIG
from .market_data import MarketDataManager
from .database import get_session_stats

class RiskManager:
    """
    APEX QUANT v3.0 Production Risk and Capital Preservation Engine.

    SIZING: target_margin = min(balance * max_risk_pct_balance * leverage_margin_factor, tier_cap)
    At $2.71:  min(2.71 * 0.12, 0.50) = min(0.3252, 0.50) = $0.3252

    DRAWDOWN PROTECTION (peak-to-valley % of WALLET BALANCE only, not mark-to-market equity):
        * 0-5%  DD: 100% Risk Budget (mult = 1.00)
        * 5-8%  DD: 75%  Risk Budget (mult = 0.75)
        * 8-12% DD: 50%  Risk Budget (mult = 0.50)
        * 12-15% DD: 25% Risk Budget (mult = 0.25)
        * >15%  DD: Hard Circuit Breaker Pause (mult = 0.00)

    CONSECUTIVE LOSS CONTROL (no martingale):
        * 0-1 losses: 1.00
        * 2 losses:   0.75
        * 3 losses:   0.50
        * 4 losses:   0.25
        * 5+ losses:  PAUSE (0.00)

    MINIMUM NOTIONAL GUARD:
        If rounding up to min_notional causes dollar_risk > max_allowed_dollar_risk:
        REJECT the trade — do NOT silently inflate risk.
    """
    def __init__(self, market_data: MarketDataManager):
        self.md = market_data
        self.session_key = time.strftime('%Y-%m-%d_UTC', time.gmtime())
        # Balance initialized to config default; OVERWRITTEN on first sync_live_balance call
        self.current_balance = DEFAULT_CONFIG.initial_balance_usd
        # peak_balance must be initialized EQUAL to current_balance; never higher.
        # It will be properly set on the first live sync.
        self.peak_balance = DEFAULT_CONFIG.initial_balance_usd
        self._peak_initialized_from_live = False  # guard: peak only ever set once from live data

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
        self.session_pnl = float(stats.get('session_pnl', 0.0))
        self.trades_count = int(stats.get('trades_count', 0))
        if self.session_pnl >= DEFAULT_CONFIG.session_profit_target_usd:
            self.target_reached = True

    def sync_live_balance(self, live_balance: float):
        """
        Updates internal balance from Binance live wallet balance.
        IMPORTANT: live_balance must be totalWalletBalance (settled USDT), NOT equity+unrealizedPnL.
        Peak is only set once from live data, then tracked upward-only from actual closes.
        """
        if live_balance > 0:
            self.current_balance = live_balance
            # First ever live sync: anchor peak to actual live balance.
            # This prevents phantom peaks from prior sessions contaminating DD calculation.
            if not self._peak_initialized_from_live:
                self.peak_balance = live_balance
                self._peak_initialized_from_live = True
            elif live_balance > self.peak_balance:
                # Only increase peak (never decrease) on actual wins after trades close
                self.peak_balance = live_balance

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

    def get_drawdown_info(self) -> Dict[str, Any]:
        """
        Tracks peak-to-valley drawdown as a percentage of WALLET BALANCE peak.
        Uses only settled balance (totalWalletBalance), never mark-to-market equity.
        """
        # Ensure peak is never below current (if we win, peak rises)
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        peak = max(0.10, self.peak_balance)
        dd_usd = max(0.0, peak - self.current_balance)
        dd_pct = dd_usd / peak

        if dd_pct < 0.05:
            multiplier = 1.00
            tier = 'NORMAL (0-5% DD | 100% Risk Budget)'
        elif dd_pct < 0.08:
            multiplier = 0.75
            tier = 'MILD DE-RISK (5-8% DD | 75% Risk Budget)'
        elif dd_pct < 0.12:
            multiplier = 0.50
            tier = 'MODERATE DE-RISK (8-12% DD | 50% Risk Budget)'
        elif dd_pct < 0.15:
            multiplier = 0.25
            tier = 'DEFENSIVE (12-15% DD | 25% Risk Budget)'
        else:
            multiplier = 0.00
            tier = 'CIRCUIT BREAKER (>15% DD | PAUSE TRADING)'

        return {
            'peak_balance': round(peak, 4),
            'current_balance': round(self.current_balance, 4),
            'dd_usd': round(dd_usd, 4),
            'dd_pct': round(dd_pct * 100.0, 2),
            'multiplier': multiplier,
            'tier': tier
        }

    def get_consecutive_loss_info(self) -> Dict[str, Any]:
        """Calculates consecutive loss de-risking multiplier."""
        losses = self.consecutive_losses
        if losses <= 1:
            mult = 1.00
            desc = f'Normal ({losses} consecutive loss)'
        elif losses == 2:
            mult = 0.75
            desc = 'Mild Reduction (2 consecutive losses | 75% risk)'
        elif losses == 3:
            mult = 0.50
            desc = 'Strong Reduction (3 consecutive losses | 50% risk)'
        elif losses == 4:
            mult = 0.25
            desc = 'Minimal Risk (4 consecutive losses | 25% risk)'
        else:
            mult = 0.00
            desc = f'Extended Circuit Breaker ({losses} consecutive losses | PAUSE)'
        return {'consecutive_losses': losses, 'multiplier': mult, 'description': desc}

    def get_compounding_tier(self) -> Dict[str, Any]:
        """
        Equity-proportional margin sizing.
        Base margin = min(balance * max_risk_pct_balance, tier_cap)
        At $2.71: min(2.71 * 0.12, 0.50) = $0.3252 (NOT a flat $0.50)

        Tier caps (upper bound only):
          Sub-$2.50: $0.45 cap
          $2.50-$5.00: $0.50 cap
          $5.00-$10.00: $0.80 cap
          $10.00-$20.00: $1.50 cap
          $20.00+: min(8% balance, $5.00) cap
        """
        bal = self.current_balance

        if bal < 2.50:
            tier_name = 'Survival Tier (Sub-$2.50)'
            tier_cap = 0.45
        elif bal < 5.00:
            tier_name = 'Tier 1 ($2.50-$5.00)'
            tier_cap = 0.50
        elif bal < 10.00:
            tier_name = 'Tier 2 ($5.00-$10.00)'
            tier_cap = 0.80
        elif bal < 20.00:
            tier_name = 'Tier 3 ($10.00-$20.00)'
            tier_cap = 1.50
        else:
            tier_name = 'Tier 4 Scaling ($20+)'
            tier_cap = min(bal * 0.08, 5.00)

        # Base margin: proportional to balance, capped at tier ceiling
        base_margin = min(bal * DEFAULT_CONFIG.max_risk_pct_balance, tier_cap)

        # Apply DD and Loss multipliers
        dd_info = self.get_drawdown_info()
        loss_info = self.get_consecutive_loss_info()
        combined_mult = dd_info['multiplier'] * loss_info['multiplier']

        # Anti-Revenge Loss Protection: if last trade was a loss, never exceed config default
        if self.last_trade_pnl < 0:
            base_margin = min(base_margin, DEFAULT_CONFIG.default_margin_usd)

        # Apply multiplier, floor at $0.20 (absolute minimum to be operable)
        target_margin = max(0.20, base_margin * max(0.25, combined_mult))

        return {
            'tier': tier_name,
            'balance': round(bal, 4),
            'base_margin': round(base_margin, 4),
            'targetMargin': round(target_margin, 4),
            'leverage': DEFAULT_CONFIG.default_leverage,
            'dd_tier': dd_info['tier'],
            'loss_desc': loss_info['description'],
            'combined_mult': round(combined_mult, 2)
        }

    def calculate_order_sizing(self, price: float, filters: Dict[str, Any],
                                sl_distance: float = 0.0) -> Dict[str, Any]:
        """
        Calculates position size with strict safety:
        1. Proportional margin (balance * 12%, capped at tier ceiling)
        2. Dynamic DD + loss de-risking multipliers
        3. Max dollar risk cap (hard ceiling per trade)
        4. Binance stepSize + minQty compliance
        5. CRITICAL: If minNotional bump causes dollar_risk > cap -> REJECT (rejected=True)
        6. Returns is_sl_safe_from_liq based on actual liq distance estimate
        """
        step_size = float(filters.get('stepSize', DEFAULT_CONFIG.step_size))
        min_qty = float(filters.get('minQty', DEFAULT_CONFIG.min_qty))
        min_notional = float(filters.get('minNotional', DEFAULT_CONFIG.min_notional))
        leverage = DEFAULT_CONFIG.default_leverage

        tier_info = self.get_compounding_tier()
        target_margin = tier_info['targetMargin']
        target_notional = target_margin * leverage

        # Raw quantity from target notional
        raw_qty = target_notional / max(1.0, price)
        decimals = max(0, int(round(-math.log10(step_size)))) if step_size > 0 else 3
        qty = round(math.floor(raw_qty / step_size) * step_size, decimals)

        # Dynamic dollar risk cap with DD + Loss multipliers
        dd_info = self.get_drawdown_info()
        loss_info = self.get_consecutive_loss_info()
        risk_mult = dd_info['multiplier'] * loss_info['multiplier']

        base_dollar_risk = min(self.current_balance * DEFAULT_CONFIG.max_risk_pct_balance, 0.40)
        max_allowed_dollar_risk = max(0.10, base_dollar_risk * max(0.25, risk_mult))

        # Apply dollar risk cap: reduce qty if needed
        if sl_distance > 0 and qty > 0:
            dollar_risk = sl_distance * qty
            if dollar_risk > max_allowed_dollar_risk:
                capped_qty = max_allowed_dollar_risk / sl_distance
                qty = round(math.floor(capped_qty / step_size) * step_size, decimals)

        # Ensure minQty
        if qty < min_qty:
            qty = min_qty

        # Critical minNotional check: may need to bump qty upward
        actual_notional = qty * price
        min_notional_breached = actual_notional < min_notional
        notional_bump_rejected = False

        if min_notional_breached:
            # Calculate what qty would be needed to satisfy minNotional
            min_notional_qty = round(math.ceil(min_notional / price / step_size) * step_size, decimals)
            min_notional_dollar_risk = sl_distance * min_notional_qty if sl_distance > 0 else 0.0

            if sl_distance > 0 and min_notional_dollar_risk > max_allowed_dollar_risk:
                # REJECT: bumping to minNotional would silently blow our dollar risk cap
                notional_bump_rejected = True
                # Keep qty at the risk-capped level anyway for logging purposes
            else:
                # Safe to bump
                qty = min_notional_qty
                actual_notional = qty * price

        actual_margin = actual_notional / leverage

        # Liquidation safety estimate (approximate for 100x isolated)
        # Actual liq price is read from Binance after position opens
        est_liq_pct = 1.0 / leverage - 0.005  # ~0.0050 at 100x after MMR
        sl_pct = (sl_distance / price) if price > 0 else 0.0
        # SL must be at least 20% inside estimated liquidation distance
        is_sl_safe_from_liq = (sl_pct > 0) and (sl_pct <= est_liq_pct * 0.80)

        actual_dollar_risk = sl_distance * qty if sl_distance > 0 else 0.0

        return {
            'quantity': qty,
            'notional': round(actual_notional, 4),
            'margin': round(actual_margin, 4),
            'leverage': leverage,
            'tier': tier_info['tier'],
            'base_margin': tier_info['base_margin'],
            'target_margin': tier_info['targetMargin'],
            'risk_mult': round(risk_mult, 2),
            'max_dollar_risk': round(max_allowed_dollar_risk, 4),
            'actual_dollar_risk': round(actual_dollar_risk, 4),
            'is_sl_safe_from_liq': is_sl_safe_from_liq,
            'min_notional_breached': min_notional_breached,
            'notional_bump_rejected': notional_bump_rejected,
        }

    def check_preflight_risk(self, has_open_position: bool, is_live_mode: bool) -> Dict[str, Any]:
        """
        Evaluates pre-flight risk filters in priority order.
        Percentage-based DD circuit breaker fires BEFORE fixed-dollar limits.
        Fixed dollar limits serve as absolute fallback only.
        """
        now = time.time()

        if self.emergency_stop_triggered:
            return {'can_trade': False, 'reason': 'EMERGENCY STOP ACTIVE: Manual reset required'}

        # 1. Peak-to-Valley Drawdown Circuit Breaker (>15%) — PRIMARY protection
        dd_info = self.get_drawdown_info()
        if dd_info['multiplier'] <= 0.0:
            return {
                'can_trade': False,
                'reason': (
                    f"DD Circuit Breaker ({dd_info['dd_pct']}% > 15%): "
                    f"Peak=${dd_info['peak_balance']:.4f}, Current=${dd_info['current_balance']:.4f}. "
                    f"Trading paused."
                )
            }

        # 2. Consecutive Losses Circuit Breaker (>= 5)
        loss_info = self.get_consecutive_loss_info()
        if loss_info['multiplier'] <= 0.0:
            rem = int(self.cooldown_until - now) if self.cooldown_until > now else 0
            return {
                'can_trade': False,
                'reason': f"Consecutive Loss Circuit Breaker: 5+ losses. Cooldown: {rem}s."
            }

        # 3. Session Profit Target
        if self.target_reached or self.session_pnl >= DEFAULT_CONFIG.session_profit_target_usd:
            self.target_reached = True
            return {
                'can_trade': False,
                'reason': (
                    f"Session Target Reached: +${self.session_pnl:.4f} >= "
                    f"${DEFAULT_CONFIG.session_profit_target_usd:.2f}. Halting entries."
                )
            }

        # 4. Max Open Position
        if has_open_position:
            return {'can_trade': False, 'reason': 'Position Active: Max 1 open position allowed'}

        # 5. Session Loss Limit — converted to percentage-relative check first
        # Pct-based: if session loss >= 15% of current balance (aligned with DD tier)
        session_loss_pct_threshold = self.current_balance * DEFAULT_CONFIG.max_session_loss_pct
        if self.session_pnl <= -abs(session_loss_pct_threshold):
            return {
                'can_trade': False,
                'reason': (
                    f"Session Loss Limit (Pct): PnL ${self.session_pnl:.4f} <= "
                    f"-${session_loss_pct_threshold:.4f} ({DEFAULT_CONFIG.max_session_loss_pct*100:.0f}% of balance)"
                )
            }
        # Fallback fixed dollar limit (safety net for very small accounts)
        if self.session_pnl <= -abs(DEFAULT_CONFIG.max_session_loss_usd):
            return {
                'can_trade': False,
                'reason': (
                    f"Session Loss Limit (Fixed): PnL ${self.session_pnl:.4f} <= "
                    f"-${DEFAULT_CONFIG.max_session_loss_usd:.2f}"
                )
            }

        # 6. Daily Loss Limit — percentage-relative first
        daily_loss_pct_threshold = self.current_balance * DEFAULT_CONFIG.max_daily_loss_pct
        if self.daily_pnl <= -abs(daily_loss_pct_threshold):
            return {
                'can_trade': False,
                'reason': (
                    f"Daily Loss Limit (Pct): PnL ${self.daily_pnl:.4f} <= "
                    f"-${daily_loss_pct_threshold:.4f} ({DEFAULT_CONFIG.max_daily_loss_pct*100:.0f}% of balance)"
                )
            }
        if self.daily_pnl <= -abs(DEFAULT_CONFIG.max_daily_loss_usd):
            return {
                'can_trade': False,
                'reason': (
                    f"Daily Loss Limit (Fixed): PnL ${self.daily_pnl:.4f} <= "
                    f"-${DEFAULT_CONFIG.max_daily_loss_usd:.2f}"
                )
            }

        # 7. Cooldown Timer
        if now < self.cooldown_until:
            rem = int(self.cooldown_until - now)
            return {'can_trade': False, 'reason': f"Cooldown Active: {rem}s remaining"}

        # 8. Max Trades Limit
        if self.trades_count >= DEFAULT_CONFIG.max_trades_per_session:
            return {
                'can_trade': False,
                'reason': f"Max Trades Limit: {self.trades_count}/{DEFAULT_CONFIG.max_trades_per_session}"
            }

        # 9. Stale Data Filter
        if self.md.is_data_stale(DEFAULT_CONFIG.stale_data_timeout_sec):
            return {'can_trade': False, 'reason': 'Stale Data: WebSocket feed lag > 5 seconds'}

        # 10. Spread Filter
        spread_info = self.md.get_spread()
        if not spread_info.get('acceptable', True):
            return {
                'can_trade': False,
                'reason': (
                    f"Spread Too High: {spread_info.get('spread_usd', 0):.2f} USDT "
                    f"> ${DEFAULT_CONFIG.max_allowed_spread_usd}"
                )
            }

        return {
            'can_trade': True,
            'reason': (
                f"Risk Clear | Session PnL: ${self.session_pnl:+.4f} / "
                f"${DEFAULT_CONFIG.session_profit_target_usd:.2f} | "
                f"DD: {dd_info['dd_pct']}% | {dd_info['tier']}"
            )
        }

    def record_trade_completion(self, pnl: float):
        """Records settled trade outcome. Only call with SETTLED wallet balance delta."""
        now = time.time()
        self.session_pnl += pnl
        self.daily_pnl += pnl
        self.current_balance += pnl
        # Peak updates only after confirmed wins from settled balance
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        self.trades_count += 1
        self.last_trade_time = now
        self.last_trade_pnl = pnl

        is_win = pnl > 0
        if is_win:
            self.consecutive_losses = 0
            self.cooldown_until = now + DEFAULT_CONFIG.cooldown_normal_sec
        else:
            self.consecutive_losses += 1
            if self.consecutive_losses >= 5:
                self.cooldown_until = now + 1800  # 30 min pause
            elif self.consecutive_losses >= 3:
                self.cooldown_until = now + 900   # 15 min cooling
            else:
                self.cooldown_until = now + DEFAULT_CONFIG.cooldown_loss_sec

        if self.session_pnl >= DEFAULT_CONFIG.session_profit_target_usd:
            self.target_reached = True

    def get_risk_summary(self) -> Dict[str, Any]:
        target_progress = min(100.0, max(0.0, (
            self.session_pnl / DEFAULT_CONFIG.session_profit_target_usd
        ) * 100.0))
        tier_info = self.get_compounding_tier()
        dd_info = self.get_drawdown_info()
        loss_info = self.get_consecutive_loss_info()
        return {
            'sessionProfitTarget': DEFAULT_CONFIG.session_profit_target_usd,
            'sessionPnl': round(self.session_pnl, 4),
            'targetProgressPct': round(target_progress, 1),
            'targetReached': self.target_reached,
            'tradesCount': self.trades_count,
            'maxTrades': DEFAULT_CONFIG.max_trades_per_session,
            'consecutiveLosses': self.consecutive_losses,
            'cooldownSecondsRemaining': max(0, int(self.cooldown_until - time.time())),
            'emergencyStop': self.emergency_stop_triggered,
            'maxSessionLoss': DEFAULT_CONFIG.max_session_loss_usd,
            'maxDailyLoss': DEFAULT_CONFIG.max_daily_loss_usd,
            'compoundingTier': tier_info['tier'],
            'basemargin': tier_info['base_margin'],
            'targetMargin': tier_info['targetMargin'],
            'peakBalance': dd_info['peak_balance'],
            'currentBalance': dd_info['current_balance'],
            'drawdownPct': dd_info['dd_pct'],
            'drawdownTier': dd_info['tier'],
            'lossControlDesc': loss_info['description'],
            'combinedRiskMultiplier': tier_info['combined_mult']
        }
