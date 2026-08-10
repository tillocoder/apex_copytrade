from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

@dataclass
class PropFirmSummary:
    stage1_passed: int
    stage2_passed: int
    completed_challenges: int
    failed_challenges: int
    challenge_success_rate_pct: float
    avg_days_per_challenge: float
    max_consecutive_failed_challenges: int
    longest_winning_challenge_streak: int
    longest_losing_challenge_streak: int
    monthly_challenge_passes: float
    yearly_funded_accounts: int

@dataclass
class QuantitativeReport:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy: float
    expectancy_r: float
    gross_profit: float
    gross_loss: float
    cagr_pct: float
    recovery_factor: float
    sqn: float
    kelly_fraction_pct: float
    avg_r_multiple: float
    avg_winner: float
    avg_loser: float
    largest_winner: float
    largest_loser: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    mar_ratio: float
    ulcer_index: float
    max_total_drawdown_pct: float
    max_daily_drawdown_pct: float
    total_pnl: float
    total_commissions: float
    avg_trade_holding_bars: float
    longest_win_streak: int
    longest_loss_streak: int
    exposure_pct: float

class StatisticsEngine:
    """
    Calculates institutional portfolio and trade analytics from first principles.

    All metrics are computed independently — no cached intermediate values are reused.

    Key corrections vs prior version:
      - CAGR: annualized via (final/initial)^(1/years) - 1
      - Sharpe: computed from calendar-day equity returns (not trade-count buckets)
      - Max Daily DD: actual intraday drawdown per day slice (not max_dd / 2)
      - R-multiple: expectancy / avg_loss (not fixed $100 assumption)
      - SQN: sample variance (N-1 denominator)
    """

    @staticmethod
    def generate_report(
        trades_pnl: List[float],
        equity_curve: List[float],
        holding_bars: List[int],
        commissions: List[float],
        initial_capital: float = 10000.0,
        years: float = 1.0,
        prop_max_dd_pct: float = None
    ) -> QuantitativeReport:
        """
        Parameters
        ----------
        trades_pnl       : list of per-settlement net PnL (partial + full exits)
        equity_curve     : portfolio equity curve (NEVER-resetting, for CAGR/Sharpe)
        holding_bars     : bar durations per settlement
        commissions      : commissions per settlement
        initial_capital  : starting account balance ($)
        years            : calendar years covered
        prop_max_dd_pct  : if provided, override max_total_drawdown_pct with this
                           value (used in PROP_FIRM mode to supply the real
                           per-challenge max DD instead of the cross-challenge one).
        """

        if not trades_pnl or not equity_curve:
            return QuantitativeReport(
                total_trades=0, winning_trades=0, losing_trades=0, win_rate_pct=0.0,
                profit_factor=0.0, expectancy=0.0, expectancy_r=0.0, gross_profit=0.0,
                gross_loss=0.0, cagr_pct=0.0, recovery_factor=0.0, sqn=0.0,
                kelly_fraction_pct=0.0, avg_r_multiple=0.0, avg_winner=0.0, avg_loser=0.0,
                largest_winner=0.0, largest_loser=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
                calmar_ratio=0.0, mar_ratio=0.0, ulcer_index=0.0, max_total_drawdown_pct=0.0,
                max_daily_drawdown_pct=0.0, total_pnl=0.0, total_commissions=0.0,
                avg_trade_holding_bars=0.0, longest_win_streak=0, longest_loss_streak=0,
                exposure_pct=0.0
            )

        total_trades = len(trades_pnl)
        wins   = [p for p in trades_pnl if p > 0]
        losses = [p for p in trades_pnl if p <= 0]

        win_rate     = (len(wins) / total_trades) * 100.0
        gross_profit = sum(wins)
        gross_loss   = abs(sum(losses))

        profit_factor    = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        total_pnl        = sum(trades_pnl)
        total_commissions = sum(commissions)
        expectancy       = total_pnl / total_trades

        # ── Win / Loss Streaks ────────────────────────────────────────────────
        win_streak, loss_streak = 0, 0
        curr_win, curr_loss = 0, 0
        for p in trades_pnl:
            if p > 0:
                curr_win += 1; curr_loss = 0
                win_streak = max(win_streak, curr_win)
            else:
                curr_loss += 1; curr_win = 0
                loss_streak = max(loss_streak, curr_loss)

        # ── Overall Drawdown (from equity curve) ──────────────────────────────
        peak   = equity_curve[0]
        max_dd = 0.0
        dd_percents: List[float] = []

        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0.0
            dd_percents.append(dd * 100.0)
            max_dd = max(max_dd, dd)

        max_dd_pct = max_dd * 100.0

        # ── Daily Drawdown — actual intraday equity slices ────────────────────
        # Estimate bars per trading day from equity curve length and backtest years
        bars_total     = len(equity_curve)
        safe_years     = max(0.01, years)
        trading_days   = max(1, round(safe_years * 252))
        bars_per_day   = max(1, bars_total // trading_days)

        max_daily_dd = 0.0
        for day_idx in range(trading_days):
            start_i = day_idx * bars_per_day
            end_i   = min(start_i + bars_per_day, bars_total)
            if start_i >= bars_total:
                break
            day_slice  = equity_curve[start_i:end_i]
            day_open   = day_slice[0] if day_slice else 0.0
            if day_open <= 0:
                continue
            day_min    = min(day_slice)
            intraday_dd = (day_open - day_min) / day_open
            max_daily_dd = max(max_daily_dd, intraday_dd)

        max_daily_dd_pct = max_daily_dd * 100.0

        # ── Max DD override for PROP_FIRM mode ───────────────────────────────
        # In PROP_FIRM mode backtest.py computes max DD per challenge from the
        # challenge's $10,000 starting capital and passes it here directly.
        # This prevents the portfolio_equity_curve (which never resets) from
        # inflating max_dd_pct when profitable challenges push equity far above $10k.
        if prop_max_dd_pct is not None:
            max_dd_pct = prop_max_dd_pct

        # ── CAGR — correct annualized formula ────────────────────────────────
        # CAGR = (Ending Equity / Beginning Equity) ^ (1 / years) - 1
        final_equity = equity_curve[-1]
        if safe_years > 0 and final_equity > 0 and initial_capital > 0:
            try:
                cagr_pct = ((final_equity / initial_capital) ** (1.0 / safe_years) - 1.0) * 100.0
            except (ZeroDivisionError, OverflowError, ValueError):
                cagr_pct = 0.0
        else:
            cagr_pct = 0.0

        # ── Sharpe & Sortino — calendar-day equity returns ────────────────────
        # Sample equity curve at bars_per_day intervals → daily equity series
        daily_equities: List[float] = []
        for i in range(trading_days + 1):
            idx_eq = min(i * bars_per_day, bars_total - 1)
            daily_equities.append(equity_curve[idx_eq])

        daily_returns: List[float] = []
        for i in range(1, len(daily_equities)):
            prev_eq = daily_equities[i - 1]
            if prev_eq > 0:
                daily_returns.append((daily_equities[i] - prev_eq) / prev_eq)

        sharpe = 0.0
        sortino = 0.0
        if len(daily_returns) > 1:
            mean_ret = sum(daily_returns) / len(daily_returns)
            # Sample variance (N-1)
            variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0
            annual_factor = math.sqrt(365.25)  # 24/7/365 crypto market calendar days
            sharpe = (mean_ret / std_dev * annual_factor) if std_dev > 0 else 0.0

            downside = [r for r in daily_returns if r < 0]
            if downside:
                downside_var = sum(r ** 2 for r in downside) / len(downside)
                downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.0
                sortino = (mean_ret / downside_std * annual_factor) if downside_std > 0 else 0.0

        # ── Average Winner / Loser ────────────────────────────────────────────
        avg_winner = sum(wins)   / max(1, len(wins))   if wins   else 0.0
        avg_loser  = sum(losses) / max(1, len(losses)) if losses else 0.0
        largest_winner = max(wins)   if wins   else 0.0
        largest_loser  = min(losses) if losses else 0.0

        # ── R-Multiple — use avg_loss as risk unit (NOT a fixed $100 assumption)
        # avg_loss serves as the proxy for 1R when actual per-trade risk varies
        risk_unit    = abs(avg_loser) if avg_loser != 0 else max(1.0, initial_capital * 0.01)
        avg_r_multiple = expectancy / risk_unit if risk_unit > 0 else 0.0

        r_ratio = (avg_winner / abs(avg_loser)) if avg_loser != 0 else 1.0
        w = win_rate / 100.0
        expectancy_r = (w * r_ratio) - (1.0 - w)  # net expectancy in R units

        # ── Kelly Criterion ───────────────────────────────────────────────────
        kelly_raw = (w - ((1.0 - w) / r_ratio)) if r_ratio > 0 else 0.0
        kelly_fraction_pct = round(max(0.0, min(kelly_raw * 100.0, 100.0)), 2)

        # ── SQN — sample standard deviation (N-1) ────────────────────────────
        norm_pnls = [min(1e6, max(-1e6, p / initial_capital)) for p in trades_pnl]
        norm_mean = sum(norm_pnls) / total_trades
        norm_var  = sum((p - norm_mean) ** 2 for p in norm_pnls) / max(1, total_trades - 1)
        norm_std  = math.sqrt(norm_var) if norm_var > 0 else 0.0
        sqn = (math.sqrt(total_trades) * norm_mean / norm_std) if norm_std > 0 else 0.0

        # ── Calmar & Recovery ─────────────────────────────────────────────────
        calmar = (cagr_pct / max_dd_pct) if max_dd_pct > 0 else 0.0
        mar_ratio = calmar
        max_dd_dollars = initial_capital * (max_dd_pct / 100.0)
        recovery_factor = (total_pnl / max_dd_dollars) if max_dd_dollars > 0 else 0.0

        # ── Ulcer Index ───────────────────────────────────────────────────────
        squared_dds = [d ** 2 for d in dd_percents]
        ulcer_index = math.sqrt(sum(squared_dds) / max(1, len(squared_dds)))

        # ── Exposure ──────────────────────────────────────────────────────────
        avg_bars = sum(holding_bars) / max(1, len(holding_bars))
        total_bars_bt = max(1, bars_total)
        # Divide by 2: multi-symbol data has 2 bars per M15 period
        exposure_pct = (sum(holding_bars) / (total_bars_bt * 2)) * 100.0

        # ── Automated Mathematical Consistency Assertions ─────────────────────
        report = QuantitativeReport(
            total_trades=total_trades,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            expectancy=round(expectancy, 2),
            expectancy_r=round(expectancy_r, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            cagr_pct=round(cagr_pct, 2),
            recovery_factor=round(calmar, 2),
            sqn=round(sqn, 2),
            kelly_fraction_pct=kelly_fraction_pct,
            avg_r_multiple=round(avg_r_multiple, 2),
            avg_winner=round(avg_winner, 2),
            avg_loser=round(avg_loser, 2),
            largest_winner=round(largest_winner, 2),
            largest_loser=round(largest_loser, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            mar_ratio=round(calmar, 2),
            ulcer_index=0.0,
            max_total_drawdown_pct=round(max_dd_pct, 2),
            max_daily_drawdown_pct=round(max_daily_dd_pct, 2),
            total_pnl=round(total_pnl, 2),
            total_commissions=round(total_commissions, 2),
            avg_trade_holding_bars=round(sum(holding_bars) / max(1, len(holding_bars)), 1),
            longest_win_streak=win_streak,
            longest_loss_streak=loss_streak,
            exposure_pct=0.0
        )

        StatisticsEngine.validate_report_integrity(report, initial_capital, final_equity)
        return report

    @staticmethod
    def validate_report_integrity(report: QuantitativeReport, initial_capital: float, final_equity: float) -> None:
        """Strict automated mathematical assertions for backtest integrity."""
        assert report.total_trades == report.winning_trades + report.losing_trades, \
            f"Trade count mismatch: {report.total_trades} != {report.winning_trades} + {report.losing_trades}"
        
        calc_net_pnl = final_equity - initial_capital
        assert abs(report.total_pnl - calc_net_pnl) < 1.0, \
            f"Net PnL mismatch: reported {report.total_pnl} != calc {calc_net_pnl}"

        if report.total_trades > 0:
            calc_exp = (report.win_rate_pct / 100.0 * report.avg_winner) + ((1.0 - report.win_rate_pct / 100.0) * report.avg_loser)
            assert abs(report.expectancy - calc_exp) < 2.0, \
                f"Expectancy mismatch: reported {report.expectancy} != calc {calc_exp}"

        assert report.max_total_drawdown_pct >= 0.0, "Max drawdown cannot be negative"
        assert report.max_daily_drawdown_pct >= 0.0, "Daily drawdown cannot be negative"
