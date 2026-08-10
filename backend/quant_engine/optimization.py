import random
import statistics as stats_lib
from dataclasses import dataclass
from typing import List
from .config import EngineConfig
from .market_data import MarketDataEngine
from .backtest import BacktestEngine, BacktestRunResult
from .prop_rules import PropStage

@dataclass
class MonteCarloSummary:
    num_simulations: int
    stage1_pass_rate_pct: float
    stage2_pass_rate_pct: float
    combined_pass_rate_pct: float
    drawdown_fail_rate_pct: float
    account_survival_rate_pct: float
    avg_stage1_days: float
    avg_stage2_days: float
    equity_5th_percentile: float
    equity_50th_percentile: float
    equity_95th_percentile: float
    worst_simulation_equity: float
    best_simulation_equity: float
    avg_final_equity: float
    expected_value_pct: float
    risk_of_ruin_pct: float
    expected_drawdown_pct: float

class MonteCarloOptimizer:
    """Robustness Optimization & Monte Carlo Stress Testing Engine."""

    def __init__(self, base_config: EngineConfig, num_simulations: int = 1000):
        self.base_config = base_config
        self.num_simulations = num_simulations

    def run_monte_carlo(self, base_result: BacktestRunResult) -> MonteCarloSummary:
        trade_pnls = [t["pnl"] for t in base_result.trade_logs] if base_result.trade_logs else [0.0]
        
        s1_passes = 0
        s2_passes = 0
        dd_fails = 0

        s1_trades_list = []
        s2_trades_list = []
        final_equities = []

        initial_cap = self.base_config.prop_rules.initial_capital
        s1_target = initial_cap * self.base_config.prop_rules.stage1_target_pct
        s2_target = initial_cap * self.base_config.prop_rules.stage2_target_pct
        daily_dd_limit = self.base_config.prop_rules.max_daily_drawdown_pct
        total_dd_limit = self.base_config.prop_rules.max_total_drawdown_pct

        # Compute realistic noise from actual trade PnL volatility
        # Using 30% of historical std dev — large enough to stress-test but
        # grounded in real distribution rather than an arbitrary constant.
        if len(trade_pnls) > 1:
            pnl_std = stats_lib.stdev(trade_pnls)
        else:
            pnl_std = abs(trade_pnls[0]) * 0.5 if trade_pnls and trade_pnls[0] != 0 else 50.0
        noise_sigma = max(10.0, pnl_std * 0.30)  # minimum $10 noise per trade

        for sim_idx in range(self.num_simulations):
            # Bootstrap resample trades with replacement + realistic Gaussian noise
            sampled_pnls = [
                random.choice(trade_pnls) + random.gauss(0, noise_sigma)
                for _ in range(len(trade_pnls))
            ]

            balance = initial_cap
            equity = initial_cap
            daily_open_equity = initial_cap
            stage = PropStage.STAGE_1

            s1_trade_count = -1
            s2_trade_count = -1

            for t_idx, pnl in enumerate(sampled_pnls):
                # Simulate daily open equity reset every 6 trades (approx 1 day)
                if t_idx % 6 == 0:
                    daily_open_equity = equity

                balance += pnl
                equity += pnl

                # 1. Total DD Breach (10%)
                if (initial_cap - equity) / initial_cap >= total_dd_limit:
                    stage = PropStage.FAILED_TOTAL_DD
                    dd_fails += 1
                    break

                # 2. Daily DD Breach (5%)
                if (daily_open_equity - equity) / daily_open_equity >= daily_dd_limit:
                    stage = PropStage.FAILED_DAILY_DD
                    dd_fails += 1
                    break

                # 3. Stage 1 Pass (+8%)
                if stage == PropStage.STAGE_1:
                    if (balance - initial_cap) >= s1_target:
                        stage = PropStage.STAGE_2
                        s1_passes += 1
                        s1_trade_count = t_idx + 1
                        # RESET TO $10,000 FOR STAGE 2
                        balance = initial_cap
                        equity = initial_cap
                        daily_open_equity = initial_cap

                # 4. Stage 2 Pass (+5%)
                elif stage == PropStage.STAGE_2:
                    if (balance - initial_cap) >= s2_target:
                        stage = PropStage.PASSED_CHALLENGE
                        s2_passes += 1
                        s2_trade_count = t_idx + 1 - s1_trade_count
                        break

            if s1_trade_count > 0:
                s1_trades_list.append(s1_trade_count)
            if s2_trade_count > 0:
                s2_trades_list.append(s2_trade_count)

            final_equities.append(equity)

        s1_rate = (s1_passes / self.num_simulations) * 100.0
        s2_rate = (s2_passes / max(1, s1_passes)) * 100.0 if s1_passes > 0 else 0.0
        combined_rate = (s2_passes / self.num_simulations) * 100.0
        fail_rate = (dd_fails / self.num_simulations) * 100.0

        # Trades to days conversion (approx 2 trades per day)
        avg_s1_days = (sum(s1_trades_list) / max(1, len(s1_trades_list))) / 2.0 if s1_trades_list else 0.0
        avg_s2_days = (sum(s2_trades_list) / max(1, len(s2_trades_list))) / 2.0 if s2_trades_list else 0.0

        sorted_eqs = sorted(final_equities) if final_equities else [10000.0]
        eq_5 = sorted_eqs[int(0.05 * len(sorted_eqs))]
        eq_50 = sorted_eqs[int(0.50 * len(sorted_eqs))]
        eq_95 = sorted_eqs[int(0.95 * len(sorted_eqs))]

        worst_eq = min(sorted_eqs)
        best_eq = max(sorted_eqs)
        avg_final_eq = sum(sorted_eqs) / len(sorted_eqs)

        expected_val_pct = round(((avg_final_eq - initial_cap) / initial_cap) * 100.0, 2)
        risk_of_ruin_pct = round(fail_rate, 2)
        expected_dd_pct = round(max(0.0, ((initial_cap - eq_5) / initial_cap) * 100.0), 2)
        survival_rate_pct = round(100.0 - fail_rate, 2)

        return MonteCarloSummary(
            num_simulations=self.num_simulations,
            stage1_pass_rate_pct=round(s1_rate, 2),
            stage2_pass_rate_pct=round(s2_rate, 2),
            combined_pass_rate_pct=round(combined_rate, 2),
            drawdown_fail_rate_pct=round(fail_rate, 2),
            account_survival_rate_pct=survival_rate_pct,
            avg_stage1_days=round(avg_s1_days, 1),
            avg_stage2_days=round(avg_s2_days, 1),
            equity_5th_percentile=round(eq_5, 2),
            equity_50th_percentile=round(eq_50, 2),
            equity_95th_percentile=round(eq_95, 2),
            worst_simulation_equity=round(worst_eq, 2),
            best_simulation_equity=round(best_eq, 2),
            avg_final_equity=round(avg_final_eq, 2),
            expected_value_pct=expected_val_pct,
            risk_of_ruin_pct=risk_of_ruin_pct,
            expected_drawdown_pct=expected_dd_pct
        )
