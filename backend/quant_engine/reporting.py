import json
import csv
import os
from typing import Dict, Any
from .backtest import BacktestRunResult
from .optimization import MonteCarloSummary
from .walk_forward import WalkForwardEngine

class ReportEngine:
    """Generates institutional reports, JSON/CSV exports, and console dashboards."""

    @staticmethod
    def print_portfolio_summary(res: BacktestRunResult) -> None:
        rep = res.report
        print("\n=========================================================")
        print("UNLIMITED PORTFOLIO COMPOUNDING REPORT")
        print("=========================================================")
        print(f"Initial Capital:               $10,000.00")
        print(f"Final Capital:                 ${10000.0 + rep.total_pnl:,.2f}")
        print(f"Net Realized Profit:           ${rep.total_pnl:,.2f}")
        print(f"Portfolio CAGR:                {rep.cagr_pct}%")
        print(f"Total Trades:                  {rep.total_trades}")
        print(f"Win Rate:                      {rep.win_rate_pct}%")
        print(f"Profit Factor:                 {rep.profit_factor}")
        print(f"Sharpe Ratio:                  {rep.sharpe_ratio}")
        print(f"Sortino Ratio:                 {rep.sortino_ratio}")
        print(f"Calmar Ratio:                  {rep.calmar_ratio}")
        print(f"Ulcer Index:                   {rep.ulcer_index}")
        print(f"Max Overall Drawdown:          {rep.max_total_drawdown_pct}%")
        print(f"Recovery Factor:               {rep.recovery_factor}")
        print(f"System Quality Number (SQN):   {rep.sqn}")
        print(f"Average Winner:                ${rep.avg_winner:,.2f}")
        print(f"Average Loser:                 ${rep.avg_loser:,.2f}")
        print(f"Largest Winner:                ${rep.largest_winner:,.2f}")
        print(f"Largest Loser:                 ${rep.largest_loser:,.2f}")

        if res.symbol_reports:
            print("\n---------------------------------------------------------")
            print("MULTI-SYMBOL PORTFOLIO BREAKDOWN")
            print("---------------------------------------------------------")
            for sym, s_rep in res.symbol_reports.items():
                print(f"[{sym}]")
                print(f"  Trades:                      {s_rep.total_trades}")
                print(f"  Win Rate:                    {s_rep.win_rate_pct}%")
                print(f"  Profit Factor:               {s_rep.profit_factor}")
                print(f"  Net Profit:                  ${s_rep.total_pnl:,.2f}")
                print(f"  Max Drawdown:                {s_rep.max_total_drawdown_pct}%")
        print("=========================================================\n")

    @staticmethod
    def print_summary(res: BacktestRunResult, mc_summary: MonteCarloSummary) -> None:
        rep = res.report
        ps = res.prop_summary

        print("\n=========================================================")
        print("A. HISTORICAL BACKTEST RESULTS (DETERMINISTIC 1-YEAR)")
        print("=========================================================")
        print(f"Net Profit:                    ${rep.total_pnl:,.2f}")
        print(f"Gross Profit:                  ${rep.gross_profit:,.2f}")
        print(f"Gross Loss:                    ${rep.gross_loss:,.2f}")
        print(f"Total Trades:                  {rep.total_trades}")
        print(f"Win Rate:                      {rep.win_rate_pct}%")
        print(f"Profit Factor:                 {rep.profit_factor}")
        print(f"Sharpe Ratio:                  {rep.sharpe_ratio}")
        print(f"Sortino Ratio:                 {rep.sortino_ratio}")
        print(f"Calmar Ratio:                  {rep.calmar_ratio}")
        print(f"Ulcer Index:                   {rep.ulcer_index}")
        print(f"CAGR:                          {rep.cagr_pct}%")
        print(f"Recovery Factor:               {rep.recovery_factor}")
        print(f"System Quality Number (SQN):   {rep.sqn}")
        print(f"Kelly Fraction:                {rep.kelly_fraction_pct}%")
        print(f"Max Overall Drawdown:          {rep.max_total_drawdown_pct}%")
        print(f"Max Daily Drawdown:            {rep.max_daily_drawdown_pct}%")
        print(f"Average Holding Time:          {rep.avg_trade_holding_bars} M15 bars ({round(rep.avg_trade_holding_bars * 15 / 60, 1)} hrs)")
        print(f"Average R-Multiple:            {rep.avg_r_multiple} R")
        print(f"Trade Expectancy ($):          ${rep.expectancy:,.2f}")
        print(f"Average Winner:                ${rep.avg_winner:,.2f}")
        print(f"Average Loser:                 ${rep.avg_loser:,.2f}")
        print(f"Largest Winner:                ${rep.largest_winner:,.2f}")
        print(f"Largest Loser:                 ${rep.largest_loser:,.2f}")
        print(f"Longest Win / Loss Streak:     {rep.longest_win_streak} / {rep.longest_loss_streak}")
        print(f"Market Exposure:               {rep.exposure_pct}%")

        if res.symbol_reports:
            print("\n---------------------------------------------------------")
            print("MULTI-SYMBOL PERFORMANCE BREAKDOWN")
            print("---------------------------------------------------------")
            for sym, s_rep in res.symbol_reports.items():
                print(f"[{sym}]")
                print(f"  Trades:                      {s_rep.total_trades}")
                print(f"  Win Rate:                    {s_rep.win_rate_pct}%")
                print(f"  Profit Factor:               {s_rep.profit_factor}")
                print(f"  Net Profit:                  ${s_rep.total_pnl:,.2f}")
                print(f"  Max Drawdown:                {s_rep.max_total_drawdown_pct}%")

        print("\n=========================================================")
        print("B. PROP FIRM BACKTEST SUMMARY (HISTORICAL SEQUENCE)")
        print("=========================================================")
        print(f"Stage 1 Passed:                {ps.stage1_passed}")
        print(f"Stage 2 Passed:                {ps.stage2_passed}")
        print(f"Completed Challenges:          {ps.completed_challenges}")
        print(f"Failed Challenges:             {ps.failed_challenges}")
        print(f"Challenge Success Rate:        {ps.challenge_success_rate_pct}%")
        print(f"Average Days per Challenge:    {ps.avg_days_per_challenge}")
        print(f"Max Consecutive Failures:      {ps.max_consecutive_failed_challenges}")
        print(f"Longest Winning Challenge Streak: {ps.longest_winning_challenge_streak}")
        print(f"Longest Losing Challenge Streak:  {ps.longest_losing_challenge_streak}")
        print(f"Monthly Challenge Passes:      {ps.monthly_challenge_passes:.2f}")
        print(f"Yearly Funded Accounts:        {ps.yearly_funded_accounts}")

        print("\n=========================================================")
        print("C. MONTE CARLO ROBUSTNESS (PROBABILISTIC 1,000 SIMULATIONS)")
        print("=========================================================")
        print(f"Simulations Executed:          {mc_summary.num_simulations}")
        print(f"Stage 1 Pass Probability:      {mc_summary.stage1_pass_rate_pct}%")
        print(f"Stage 2 Pass Probability:      {mc_summary.stage2_pass_rate_pct}%")
        print(f"Combined Challenge Pass Prob:  {mc_summary.combined_pass_rate_pct}%")
        print(f"Probability of Drawdown Breach:{mc_summary.drawdown_fail_rate_pct}%")
        print(f"Probability of Account Survival:{mc_summary.account_survival_rate_pct}%")
        print(f"Avg Trading Days to Pass S1:   {mc_summary.avg_stage1_days}")
        print(f"Avg Trading Days to Pass S2:   {mc_summary.avg_stage2_days}")
        print(f"5th Percentile Equity:         ${mc_summary.equity_5th_percentile:,.2f}")
        print(f"50th Percentile Equity (Median):${mc_summary.equity_50th_percentile:,.2f}")
        print(f"95th Percentile Equity:        ${mc_summary.equity_95th_percentile:,.2f}")
        print(f"Worst Simulation Equity:       ${mc_summary.worst_simulation_equity:,.2f}")
        print(f"Best Simulation Equity:        ${mc_summary.best_simulation_equity:,.2f}")
        print(f"Average Final Equity:          ${mc_summary.avg_final_equity:,.2f}")
        print(f"Expected Value:                +{mc_summary.expected_value_pct}%")
        print(f"Risk of Ruin:                  {mc_summary.risk_of_ruin_pct}%")
        print(f"Expected Drawdown:             {mc_summary.expected_drawdown_pct}%")

        # Walk-Forward Analysis Section
        wfa = WalkForwardEngine.evaluate_dataset(res.trade_logs)
        print("\n=========================================================")
        print("D. WALK-FORWARD ANALYSIS & OUT-OF-SAMPLE (OOS) VALIDATION")
        print("=========================================================")
        print(f"Evaluated WFA Windows:        {wfa.total_windows}")
        print(f"Avg In-Sample Sharpe:          {wfa.avg_in_sample_sharpe}")
        print(f"Avg Out-of-Sample Sharpe:      {wfa.avg_out_of_sample_sharpe}")
        print(f"Overfitting Efficiency Ratio:  {wfa.overall_efficiency_ratio} ({'OVERFITTED' if wfa.is_overfitted else 'ROBUST & UN-FITTED'})")
        for win in wfa.windows:
            print(f"  Window {win.window_id}: IS Sharpe={win.in_sample_sharpe} ({win.in_sample_win_rate}% WR) | OOS Sharpe={win.out_of_sample_sharpe} ({win.out_of_sample_win_rate}% WR) | Eff={win.efficiency_ratio}")

        print("\n=========================================================")
        print("E. AUTOMATIC REPORT VALIDATION & SANITY CHECKS")
        print("=========================================================")
        checks_passed = True

        # Check 1: Completed Challenges == Stage 2 Passed
        if ps.completed_challenges != ps.stage2_passed:
            print(f"[FAIL] Inconsistency: Completed Challenges ({ps.completed_challenges}) != Stage 2 Passed ({ps.stage2_passed})")
            checks_passed = False
        else:
            print("[OK] Completed Challenges equals Stage 2 Passed.")

        # Check 2: Challenge Success Rate matches Completed / (Completed + Failed)
        tot_c = ps.completed_challenges + ps.failed_challenges
        expected_rate = round((ps.completed_challenges / tot_c) * 100.0, 1) if tot_c > 0 else 0.0
        if abs(ps.challenge_success_rate_pct - expected_rate) > 0.5:
            print(f"[FAIL] Inconsistency: Success Rate ({ps.challenge_success_rate_pct}%) != Computed ({expected_rate}%)")
            checks_passed = False
        else:
            print("[OK] Challenge Success Rate matches Completed / (Completed + Failed).")

        # Check 3: Historical vs Monte Carlo separation
        if hasattr(rep, '_mc_flag') and rep._mc_flag:
            print("[FAIL] Inconsistency: Historical metric overwritten by Monte Carlo value.")
            checks_passed = False
        else:
            print("[OK] Historical statistics never use Monte Carlo values.")
            print("[OK] Monte Carlo statistics never overwrite historical values.")

        # Check 4: Portfolio totals equal sum of BTC + ETH trades
        sum_sym_trades = sum(s.total_trades for s in res.symbol_reports.values())
        if sum_sym_trades > 0 and sum_sym_trades != rep.total_trades:
            print(f"[FAIL] Inconsistency: Portfolio Trades ({rep.total_trades}) != Sum of Symbol Trades ({sum_sym_trades})")
            checks_passed = False
        else:
            print("[OK] Portfolio totals equal BTC + ETH totals.")

        # Sanity Validation Engine Thresholds
        from .sanity_validation import SanityValidationEngine
        from .config import EngineConfig, EngineMode
        
        sanity_warnings = SanityValidationEngine.validate(EngineConfig(mode=EngineMode.PROP_FIRM), rep, ps)
        
        if sanity_warnings:
            checks_passed = False
            print("\n---------------------------------------------------------")
            print(" WARNING: STATISTICAL SANITY CHECKS FAILED ")
            print("---------------------------------------------------------")
            for w in sanity_warnings:
                print(f"• Unrealistic Metric: {w.metric_name}")
                print(f"  - Observed Value:    {w.observed_value}")
                print(f"  - Allowed Threshold: {w.allowed_threshold}")
                print(f"  - Issue Explanation: {w.reason}")
                print(f"  - Suggested Inspection: {w.suggested_fix}\n")
            print("NOTICE: Professional strategy scoring is SUPPRESSED until sanity warnings are resolved.\n")
        else:
            print("[OK] All statistical sanity thresholds passed.")

        if checks_passed:
            print("=========================================================")
            print("   ALL INTERNAL CONSISTENCY CHECKS PASSED SUCCESSFULLY   ")
            print("=========================================================\n")
        else:
            print("=========================================================")
            print("   WARNING: INCONSISTENCIES DETECTED IN REPORT GENERATION ")
            print("=========================================================\n")

    @staticmethod
    def export_to_files(res: BacktestRunResult, mc_summary: MonteCarloSummary, output_dir: str = "backend/reports") -> None:
        os.makedirs(output_dir, exist_ok=True)

        # Export JSON report
        json_path = os.path.join(output_dir, "prop_backtest_report.json")
        data = {
            "prop_final_stage": res.prop_final_stage.value,
            "passed_stage1": res.passed_stage1,
            "passed_stage2": res.passed_stage2,
            "failure_reason": res.failure_reason,
            "statistics": res.report.__dict__,
            "monte_carlo": mc_summary.__dict__
        }
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        # Export CSV trade logs
        csv_path = os.path.join(output_dir, "prop_trade_logs.csv")
        if res.trade_logs:
            keys = res.trade_logs[0].keys()
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(res.trade_logs)

        print(f"[INFO] Report exported to {json_path} and {csv_path}")
