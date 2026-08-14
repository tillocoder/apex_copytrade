from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from .config import PropFirmRulesConfig

try:
    from zoneinfo import ZoneInfo
    PRAGUE_TZ = ZoneInfo("Europe/Prague")
except Exception:
    PRAGUE_TZ = None

def get_prague_date(dt: datetime):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if PRAGUE_TZ:
        return dt.astimezone(PRAGUE_TZ).date()
    else:
        year = dt.year
        march_last_sun = max(day for day in range(25, 32) if datetime(year, 3, day, tzinfo=timezone.utc).weekday() == 6)
        oct_last_sun = max(day for day in range(25, 32) if datetime(year, 10, day, tzinfo=timezone.utc).weekday() == 6)
        start_dst = datetime(year, 3, march_last_sun, 1, 0, tzinfo=timezone.utc)
        end_dst = datetime(year, 10, oct_last_sun, 1, 0, tzinfo=timezone.utc)
        offset_hours = 2 if (start_dst <= dt < end_dst) else 1
        return (dt + timedelta(hours=offset_hours)).date()

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
    floating_equity: float
    stage1_passed_time: str = ""
    stage2_passed_time: str = ""
    failure_reason: str = ""

class PropRulesEngine:
    """
    Institutional Prop Evaluation State Machine.
    Strictly adheres to FTMO rules:
      - Daily reset at 00:00 CE(S)T (Prague local midnight with automatic DST)
      - Daily DD evaluated on Floating Equity (balance + unrealized PnL of open positions)
      - Max Total Drawdown evaluated against Initial Capital ($10,000)
    """

    def __init__(self, config: PropFirmRulesConfig):
        self.cfg = config
        self.stage = PropStage.STAGE_1
        self.initial_balance = config.initial_capital
        self.current_balance = config.initial_capital
        self.current_equity = config.initial_capital
        self.daily_open_equity = config.initial_capital
        self.current_prague_date = None
        self.stage1_passed_bar = -1
        self.stage2_passed_bar = -1
        self.failure_reason = ""

    def update(self, current_balance: float, current_equity: float, floating_equity: float, current_bar: int, bar_time_dt: datetime) -> PropState:
        self.current_balance = current_balance
        self.current_equity = current_equity

        # Prague Midnight Date Reset
        prague_date = get_prague_date(bar_time_dt)
        if self.current_prague_date is None or prague_date != self.current_prague_date:
            self.current_prague_date = prague_date
            self.daily_open_equity = floating_equity

        # 1. Total Drawdown Violation (10% of Initial Capital = $1,000 on $10k)
        total_dd = (self.initial_balance - floating_equity) / self.initial_balance
        if total_dd >= self.cfg.max_total_drawdown_pct:
            self.stage = PropStage.FAILED_TOTAL_DD
            self.failure_reason = f"Max total drawdown limit (10%) breached on floating equity: -{round(total_dd * 100, 2)}%"
            return self._get_state(floating_equity)

        # 2. Daily Drawdown Violation (5% of Prague Daily Open Equity)
        daily_dd = (self.daily_open_equity - floating_equity) / self.daily_open_equity
        if daily_dd >= self.cfg.max_daily_drawdown_pct:
            self.stage = PropStage.FAILED_DAILY_DD
            self.failure_reason = f"Max daily drawdown limit (5%) breached on floating equity: -{round(daily_dd * 100, 2)}%"
            return self._get_state(floating_equity)

        # 3. Stage 1 Target Check (+8% = $10,800)
        if self.stage == PropStage.STAGE_1:
            profit_pct = (self.current_balance - self.initial_balance) / self.initial_balance
            if profit_pct >= self.cfg.stage1_target_pct:
                self.stage = PropStage.STAGE_2
                self.stage1_passed_bar = current_bar
                if self.cfg.enforce_stage_reset:
                    self.current_balance = self.cfg.initial_capital
                    self.current_equity = self.cfg.initial_capital
                    self.daily_open_equity = self.cfg.initial_capital
                return self._get_state(floating_equity)

        # 4. Stage 2 Target Check (+5% = $10,500)
        elif self.stage == PropStage.STAGE_2:
            profit_pct = (self.current_balance - self.cfg.initial_capital) / self.cfg.initial_capital
            if profit_pct >= self.cfg.stage2_target_pct:
                self.stage = PropStage.PASSED_CHALLENGE
                self.stage2_passed_bar = current_bar
                return self._get_state(floating_equity)

        return self._get_state(floating_equity)

    def _get_state(self, floating_equity: float) -> PropState:
        return PropState(
            stage=self.stage,
            current_balance=round(self.current_balance, 2),
            current_equity=round(self.current_equity, 2),
            floating_equity=round(floating_equity, 2),
            failure_reason=self.failure_reason
        )
