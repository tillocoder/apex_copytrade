"""
Production Risk Engine & Two-Parallel-Account Manager.
Enforces:
- Independent account tracking (balance, equity, phase, DD, pass/fail).
- Prop Daily DD Guard (warning at 3.5%, halt at 4.25%).
- Prop Max Trailing DD Guard (warning at 6.0%, reduction at 7.5%, halt at 8.5%).
- Portfolio Correlated Exposure Control (max 1.50% total simultaneous risk).
- Precise Position Sizing (Risk Amount / Stop Distance with precision rounding).
- Idempotent Signal Verification.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .config import ProductionConfig

class ChallengeAccountState:
    def __init__(self, account_id: str, start_day: int, initial_capital: float = 10000.0):
        self.account_id = account_id
        self.start_day = start_day
        self.balance = initial_capital
        self.equity = initial_capital
        self.daily_open_equity = initial_capital
        self.peak_equity = initial_capital
        self.phase = 1               # 1 or 2
        self.phase_start_equity = initial_capital
        self.passes = 0
        self.blowups = 0
        self.status = "ACTIVE"       # "ACTIVE", "HALTED", "PASSED", "BLOWN"
        self.daily_trades_count = 0
        self.curr_day_key = ""
        self.active_positions: Dict[str, Any] = {}
        self.trade_history: List[Dict[str, Any]] = []

    def update_day(self, day_key: str):
        if day_key != self.curr_day_key:
            self.curr_day_key = day_key
            self.daily_open_equity = self.equity
            self.daily_trades_count = 0
            if self.status == "HALTED":
                self.status = "ACTIVE" # Reset daily halt if not blown up

    def record_equity(self, current_equity: float):
        self.equity = current_equity
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

class ProductionRiskEngine:
    def __init__(self, cfg: ProductionConfig):
        self.cfg = cfg
        # Initialize 2 Parallel Challenge Accounts with 45-day stagger
        self.accounts = {
            "ACC_1": ChallengeAccountState("ACC_1", start_day=0, initial_capital=cfg.prop.initial_balance),
            "ACC_2": ChallengeAccountState("ACC_2", start_day=cfg.prop.account_stagger_days, initial_capital=cfg.prop.initial_balance)
        }
        self.executed_signal_ids = set()

    def get_account(self, acc_id: str) -> ChallengeAccountState:
        return self.accounts[acc_id]

    def check_daily_drawdown(self, acc: ChallengeAccountState) -> str:
        """Returns 'OK', 'WARNING', 'HALT', or 'BLOWN'."""
        loss = acc.daily_open_equity - acc.equity
        loss_pct = loss / acc.daily_open_equity if acc.daily_open_equity > 0 else 0.0

        if loss_pct >= self.cfg.prop.max_daily_drawdown_pct:
            return "BLOWN"
        if loss_pct >= self.cfg.prop.daily_dd_halt_pct:
            return "HALT"
        if loss_pct >= self.cfg.prop.daily_dd_warning_pct:
            return "WARNING"
        return "OK"

    def check_max_drawdown(self, acc: ChallengeAccountState) -> str:
        """Returns 'OK', 'WARNING', 'REDUCE', 'HALT', or 'BLOWN'."""
        dd = acc.peak_equity - acc.equity
        dd_pct = dd / acc.peak_equity if acc.peak_equity > 0 else 0.0

        if dd_pct >= self.cfg.prop.max_total_drawdown_pct:
            return "BLOWN"
        if dd_pct >= self.cfg.prop.total_dd_halt_pct:
            return "HALT"
        if dd_pct >= self.cfg.prop.total_dd_reduce_risk_pct:
            return "REDUCE"
        if dd_pct >= self.cfg.prop.total_dd_warning_pct:
            return "WARNING"
        return "OK"

    def can_open_position(self, acc_id: str, symbol: str, signal_id: str, day_idx: int) -> Tuple[bool, str]:
        acc = self.accounts[acc_id]
        if day_idx < acc.start_day:
            return False, f"Account {acc_id} has not started yet (stagger day {acc.start_day})"

        if acc.status != "ACTIVE":
            return False, f"Account {acc_id} status is {acc.status}"

        # Idempotency check
        if signal_id in self.executed_signal_ids:
            return False, f"Signal {signal_id} has already been executed"

        # Daily DD checks
        daily_status = self.check_daily_drawdown(acc)
        if daily_status in ["HALT", "BLOWN"]:
            acc.status = "HALTED" if daily_status == "HALT" else "BLOWN"
            return False, f"Daily DD status is {daily_status}"

        # Max DD checks
        max_status = self.check_max_drawdown(acc)
        if max_status in ["HALT", "BLOWN"]:
            acc.status = "HALTED" if max_status == "HALT" else "BLOWN"
            return False, f"Max DD status is {max_status}"

        # Trade limits
        if acc.daily_trades_count >= self.cfg.risk.max_daily_trades_per_account:
            return False, f"Daily trade limit ({self.cfg.risk.max_daily_trades_per_account}) reached"

        if symbol in acc.active_positions:
            return False, f"Position on {symbol} already open in {acc_id}"

        # Correlated portfolio exposure check
        current_risk_pct = sum(pos["risk_pct"] for pos in acc.active_positions.values())
        if current_risk_pct + self.cfg.risk.default_risk_per_trade_pct > self.cfg.risk.max_portfolio_correlated_risk_pct:
            return False, f"Total portfolio risk ({current_risk_pct + self.cfg.risk.default_risk_per_trade_pct:.4f}) exceeds cap ({self.cfg.risk.max_portfolio_correlated_risk_pct:.4f})"

        return True, "APPROVED"

    def calculate_position_size(self, acc_id: str, symbol: str, entry_price: float, sl_price: float) -> Dict[str, Any]:
        acc = self.accounts[acc_id]
        sl_dist = abs(entry_price - sl_price)
        if sl_dist <= 0:
            return {"size": 0.0, "risk_amount": 0.0, "risk_pct": 0.0}

        # Apply risk reduction if in total DD REDUCE state
        risk_pct = self.cfg.risk.default_risk_per_trade_pct
        if self.check_max_drawdown(acc) == "REDUCE":
            risk_pct = 0.0050 # Throttle to 0.50%

        risk_amount = acc.equity * risk_pct
        raw_qty = risk_amount / sl_dist

        # Precision & minimum quantity rounding
        if symbol == "BTCUSDT":
            prec = self.cfg.execution.qty_precision_btc
            min_q = self.cfg.execution.min_qty_btc
        else:
            prec = self.cfg.execution.qty_precision_eth
            min_q = self.cfg.execution.min_qty_eth

        final_qty = max(min_q, round(raw_qty, prec))
        return {
            "size": final_qty,
            "risk_amount": risk_amount,
            "risk_pct": risk_pct,
            "sl_distance": sl_dist
        }
from typing import Tuple
