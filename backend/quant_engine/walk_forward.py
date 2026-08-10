from dataclasses import dataclass
from typing import List, Dict, Any
from .statistics_engine import StatisticsEngine, QuantitativeReport

@dataclass
class WalkForwardWindow:
    window_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    in_sample_win_rate: float
    out_of_sample_win_rate: float
    efficiency_ratio: float  # OOS Sharpe / IS Sharpe

@dataclass
class WalkForwardReport:
    total_windows: int
    avg_in_sample_sharpe: float
    avg_out_of_sample_sharpe: float
    overall_efficiency_ratio: float  # OER
    is_overfitted: bool
    windows: List[WalkForwardWindow]

class WalkForwardEngine:
    """
    Walk-Forward Analysis (WFA) and Out-of-Sample (OOS) validation.

    Ensures strict separation between In-Sample (training) and Out-of-Sample (testing)
    periods. No data leakage: each OOS window uses trades strictly after the IS period.

    Overfitting Efficiency Ratio (OER) = OOS Sharpe / IS Sharpe:
      OER >= 0.60 → ROBUST (OOS performance close to IS)
      OER  < 0.50 → OVERFITTED (OOS degrades significantly vs IS)

    Bug fixes vs prior version:
      - IS and OOS equity curves are built incrementally (not flat $10,000)
      - IS Sharpe floor (max(0.01, ...)) removed — allows detection of negative IS
      - OER handles negative IS Sharpe explicitly (returns 0.0 = overfitted)
      - Window date ranges are printed from actual trade entry_time fields
    """

    @staticmethod
    def evaluate_dataset(
        trade_logs: List[Dict[str, Any]],
        num_windows: int = 4,
        total_years: float = 1.0
    ) -> WalkForwardReport:

        if len(trade_logs) < 20:
            return WalkForwardReport(
                total_windows=0,
                avg_in_sample_sharpe=0.0,
                avg_out_of_sample_sharpe=0.0,
                overall_efficiency_ratio=0.0,
                is_overfitted=True,
                windows=[]
            )

        # Sort chronologically — strict separation requires time ordering
        sorted_trades = sorted(trade_logs, key=lambda t: t['entry_time'])
        chunk_size = len(sorted_trades) // num_windows

        # Approximate years per window
        window_years = max(0.1, total_years / max(1, num_windows - 1))

        windows: List[WalkForwardWindow] = []
        is_sharpes:  List[float] = []
        oos_sharpes: List[float] = []

        for i in range(num_windows - 1):
            train_trades = sorted_trades[i * chunk_size : (i + 1) * chunk_size]
            test_trades  = sorted_trades[(i + 1) * chunk_size : (i + 2) * chunk_size]

            # Assert strict OOS separation: test must start AFTER training ends
            if not train_trades or not test_trades:
                continue
            assert test_trades[0]['entry_time'] >= train_trades[-1]['entry_time'], \
                f"WFA OVERLAP BUG: OOS window {i+1} starts before IS ends!"

            train_pnls = [t['pnl'] for t in train_trades]
            test_pnls  = [t['pnl'] for t in test_trades]

            train_wr = sum(1 for p in train_pnls if p > 0) / len(train_pnls) if train_pnls else 0.0
            test_wr  = sum(1 for p in test_pnls  if p > 0) / len(test_pnls)  if test_pnls  else 0.0

            # ── Build real incremental equity curves (no longer flat $10k) ────
            train_equity = [10000.0]
            for p in train_pnls:
                train_equity.append(train_equity[-1] + p)

            # OOS equity continues from IS final equity for drawdown continuity
            oos_start = train_equity[-1]
            oos_equity = [oos_start]
            for p in test_pnls:
                oos_equity.append(oos_equity[-1] + p)

            is_initial  = train_equity[0]
            oos_initial = oos_equity[0]

            is_rep  = StatisticsEngine.generate_report(
                train_pnls, train_equity,
                [1] * len(train_pnls), [0.0] * len(train_pnls),
                initial_capital=is_initial, years=window_years
            )
            oos_rep = StatisticsEngine.generate_report(
                test_pnls, oos_equity,
                [1] * len(test_pnls), [0.0] * len(test_pnls),
                initial_capital=oos_initial, years=window_years
            )

            is_sharpe  = is_rep.sharpe_ratio   # NO floor — allows negative IS detection
            oos_sharpe = oos_rep.sharpe_ratio

            # OER computation: handles negative IS correctly
            if is_sharpe > 0:
                eff = oos_sharpe / is_sharpe
            elif is_sharpe < 0:
                eff = 0.0  # IS negative → strategy loses money in-sample → overfitted
            else:
                eff = 0.0  # IS = 0 → undefined

            is_sharpes.append(is_sharpe)
            oos_sharpes.append(oos_sharpe)

            windows.append(WalkForwardWindow(
                window_id=i + 1,
                train_start=train_trades[0]['entry_time'],
                train_end=train_trades[-1]['entry_time'],
                test_start=test_trades[0]['entry_time'],
                test_end=test_trades[-1]['entry_time'],
                in_sample_sharpe=round(is_sharpe, 2),
                out_of_sample_sharpe=round(oos_sharpe, 2),
                in_sample_win_rate=round(train_wr * 100, 2),
                out_of_sample_win_rate=round(test_wr * 100, 2),
                efficiency_ratio=round(eff, 2)
            ))

        avg_is  = sum(is_sharpes)  / len(is_sharpes)  if is_sharpes  else 0.0
        avg_oos = sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0.0

        if avg_is > 0:
            overall_oer = avg_oos / avg_is
        elif avg_is < 0:
            overall_oer = 0.0
        else:
            overall_oer = 0.0

        is_overfitted = overall_oer < 0.50

        return WalkForwardReport(
            total_windows=len(windows),
            avg_in_sample_sharpe=round(avg_is, 2),
            avg_out_of_sample_sharpe=round(avg_oos, 2),
            overall_efficiency_ratio=round(overall_oer, 2),
            is_overfitted=is_overfitted,
            windows=windows
        )
