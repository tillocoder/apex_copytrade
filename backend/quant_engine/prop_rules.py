from enum import Enum
from dataclasses import dataclass
from .config import PropFirmRulesConfig

class PropStage(Enum):
    STAGE_1 = "STAGE_1"
    STAGE_2 = "STAGE_2"
    PASSED_CHALLENGE = "PASSED_CHALLENGE"
    FAILED_DAILY_DD = "FAILED_DAILY_DD"
    FAILED_TOTAL_DD = "FAILED_TOTAL_DD"

@dataclass
class PropState:
    stage: PropStage
    current_balance: float
    current_equity: float
    stage1_passed_time: str = ""
    stage2_passed_time: str = ""
    failure_reason: str = ""

class PropRulesEngine:
    """State machine tracking prop evaluation stages, target profits, and drawdown limits."""

    def __init__(self, config: PropFirmRulesConfig):
        self.cfg = config
        self.stage = PropStage.STAGE_1
        self.initial_balance = config.initial_capital
        self.current_balance = config.initial_capital
        self.current_equity = config.initial_capital
        self.daily_open_equity = config.initial_capital
        self.stage1_passed_bar = -1
        self.stage2_passed_bar = -1
        self.failure_reason = ""

    def start_new_day(self, equity: float) -> None:
        self.daily_open_equity = equity

    def update(self, current_balance: float, current_equity: float, current_bar: int, bar_time: str) -> PropState:
        self.current_balance = current_balance
        self.current_equity = current_equity

        # 1. Check Total Drawdown Violation (10% of Initial Capital)
        total_dd = (self.initial_balance - self.current_equity) / self.initial_balance
        if total_dd >= self.cfg.max_total_drawdown_pct:
            self.stage = PropStage.FAILED_TOTAL_DD
            self.failure_reason = f"Max total drawdown limit (10%) breached: -{round(total_dd * 100, 2)}%"
            return self._get_state()

        # 2. Check Daily Drawdown Violation (5% of Daily Open Equity)
        daily_dd = (self.daily_open_equity - self.current_equity) / self.daily_open_equity
        if daily_dd >= self.cfg.max_daily_drawdown_pct:
            self.stage = PropStage.FAILED_DAILY_DD
            self.failure_reason = f"Max daily drawdown limit (5%) breached: -{round(daily_dd * 100, 2)}%"
            return self._get_state()

        # 3. Stage 1 Target Check (+8% = $10,800)
        if self.stage == PropStage.STAGE_1:
            profit_pct = (self.current_balance - self.initial_balance) / self.initial_balance
            if profit_pct >= self.cfg.stage1_target_pct:
                self.stage = PropStage.STAGE_2
                self.stage1_passed_bar = current_bar
                # RESET ACCOUNT BALANCE TO $10,000 EXACTLY AS REAL PROP FIRMS DO
                if self.cfg.enforce_stage_reset:
                    self.current_balance = self.cfg.initial_capital
                    self.current_equity = self.cfg.initial_capital
                    self.daily_open_equity = self.cfg.initial_capital
                return self._get_state()

        # 4. Stage 2 Target Check (+5% = $10,500)
        elif self.stage == PropStage.STAGE_2:
            profit_pct = (self.current_balance - self.cfg.initial_capital) / self.cfg.initial_capital
            if profit_pct >= self.cfg.stage2_target_pct:
                self.stage = PropStage.PASSED_CHALLENGE
                self.stage2_passed_bar = current_bar
                return self._get_state()

        return self._get_state()

    def _get_state(self) -> PropState:
        return PropState(
            stage=self.stage,
            current_balance=round(self.current_balance, 2),
            current_equity=round(self.current_equity, 2),
            failure_reason=self.failure_reason
        )
