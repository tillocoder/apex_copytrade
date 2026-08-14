from dataclasses import dataclass
from .config import RiskConfig, PropFirmRulesConfig

@dataclass
class RiskStatus:
    can_trade: bool
    risk_pct: float
    reason: str

class RiskEngine:
    """Enforces prop firm risk guards and 4-tier adaptive drawdown throttling."""

    def __init__(self, risk_cfg: RiskConfig, prop_cfg: PropFirmRulesConfig):
        self.risk_cfg = risk_cfg
        self.prop_cfg = prop_cfg
        self.daily_open_equity: float = prop_cfg.initial_capital
        self.consecutive_losses: int = 0
        self.consecutive_wins: int = 0

    def start_new_day(self, current_equity: float) -> None:
        """Reset daily high-water mark at day start."""
        self.daily_open_equity = current_equity
        self.consecutive_losses = 0
        self.consecutive_wins = 0

    def record_trade_result(self, is_win: bool) -> None:
        if is_win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0

    def evaluate_risk(
        self,
        current_equity: float,
        open_positions_count: int,
        confidence_score: float,
        is_high_volatility: bool = False
    ) -> RiskStatus:
        # 1. Check Max Simultaneous Open Positions
        if open_positions_count >= self.risk_cfg.max_open_positions:
            return RiskStatus(can_trade=False, risk_pct=0.0, reason="Max simultaneous open positions reached")

        # 2. Check Daily Drawdown Guard (85% of 5.0% Limit = 4.25%)
        daily_loss = self.daily_open_equity - current_equity
        max_daily_loss_allowed = self.daily_open_equity * self.prop_cfg.max_daily_drawdown_pct

        if daily_loss >= (0.85 * max_daily_loss_allowed):
            return RiskStatus(can_trade=False, risk_pct=0.0, reason="Daily loss guard limit reached (85% of 5% limit)")

        # 3. Check Overall Total Drawdown Guard (85% of 10.0% Limit = 8.5%)
        total_loss = self.prop_cfg.initial_capital - current_equity
        max_total_loss_allowed = self.prop_cfg.initial_capital * self.prop_cfg.max_total_drawdown_pct

        if total_loss >= (0.85 * max_total_loss_allowed):
            return RiskStatus(can_trade=False, risk_pct=0.0, reason="Total loss guard limit reached (85% of 10% limit)")

        # 4. Adaptive Tier Sizing scaled from self.risk_cfg.base_risk_pct
        base_r = self.prop_cfg.risk_per_trade_pct
        
        total_dd_pct = max(0.0, total_loss / self.prop_cfg.initial_capital)
        if total_dd_pct >= 0.04:
            base_r = min(base_r, 0.005)
        elif total_dd_pct >= 0.02:
            base_r = min(base_r, 0.010)

        if confidence_score >= 85.0:
            tier_risk = base_r * 1.0
        elif confidence_score >= 75.0:
            tier_risk = base_r * 0.8
        elif confidence_score >= 70.0:
            tier_risk = base_r * 0.65
        else:
            tier_risk = base_r * 0.50

        # Loss Streak Throttling — only reduce after 3+ consecutive losses
        # (was cutting to 50% after just 2 losses — too aggressive)
        if self.consecutive_losses >= 3:
            tier_risk = min(tier_risk, base_r * 0.65)
        elif self.consecutive_losses >= 5:
            tier_risk = min(tier_risk, base_r * 0.50)

        # High Volatility Risk Halving
        if is_high_volatility:
            tier_risk = max(self.risk_cfg.min_risk_pct, tier_risk * 0.5)

        # Enforce bounds
        tier_risk = max(self.risk_cfg.min_risk_pct, min(self.risk_cfg.max_risk_pct, tier_risk))

        return RiskStatus(can_trade=True, risk_pct=round(tier_risk, 6), reason="Adaptive risk approved")
