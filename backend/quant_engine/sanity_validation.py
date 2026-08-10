from dataclasses import dataclass
from typing import List, Optional
from .statistics_engine import QuantitativeReport, PropFirmSummary
from .config import EngineConfig, EngineMode

@dataclass
class SanityCheckWarning:
    metric_name: str
    observed_value: float
    allowed_threshold: str
    reason: str
    suggested_fix: str

class SanityValidationEngine:
    """Statistical Sanity Validation Engine for Quantitative Trading Systems."""

    @staticmethod
    def validate(config: EngineConfig, rep: QuantitativeReport, ps: Optional[PropFirmSummary] = None) -> List[SanityCheckWarning]:
        warnings: List[SanityCheckWarning] = []
        initial_cap = config.prop_rules.initial_capital

        # 1. Profit Factor > 10
        if rep.profit_factor > 10.0:
            warnings.append(SanityCheckWarning(
                metric_name="Profit Factor",
                observed_value=rep.profit_factor,
                allowed_threshold="<= 10.0",
                reason="Unusually high Profit Factor indicates synthetic zero-noise market data or overfitted win rate.",
                suggested_fix="Inspect market data generator noise, spread/commission deduction, or entry filter strictness."
            ))

        # 2. Sharpe < -1 or > 5
        if rep.sharpe_ratio < -1.0 or rep.sharpe_ratio > 5.0:
            warnings.append(SanityCheckWarning(
                metric_name="Sharpe Ratio",
                observed_value=rep.sharpe_ratio,
                allowed_threshold="-1.0 <= Sharpe <= 5.0",
                reason="Sharpe Ratio outside realistic institutional boundaries [-1.0, 5.0].",
                suggested_fix="Inspect return variance calculation, risk-free rate assumption, or daily return aggregation."
            ))

        # 3. CAGR > 1000%
        if rep.cagr_pct > 1000.0:
            warnings.append(SanityCheckWarning(
                metric_name="CAGR (%)",
                observed_value=rep.cagr_pct,
                allowed_threshold="<= 1000.0%",
                reason="Compounded Annual Growth Rate exceeds 1,000%, which is mathematically unrealistic in prop trading.",
                suggested_fix="Inspect position sizing, account equity resets, or compounding leverage model."
            ))

        # 4. Average R-Multiple > 10
        if rep.avg_r_multiple > 10.0:
            warnings.append(SanityCheckWarning(
                metric_name="Average R-Multiple",
                observed_value=rep.avg_r_multiple,
                allowed_threshold="<= 10.0 R",
                reason="Average R-multiple exceeds 10.0 R, indicating inaccurate stop loss or take profit distance calculations.",
                suggested_fix="Inspect ATR stop loss / take profit multiplier logic and exit fill price calculations."
            ))

        # 5. Largest Winner > 20 * Initial Capital
        max_allowed_winner = 20.0 * initial_cap
        if rep.largest_winner > max_allowed_winner:
            warnings.append(SanityCheckWarning(
                metric_name="Largest Winner ($)",
                observed_value=rep.largest_winner,
                allowed_threshold=f"<= ${max_allowed_winner:,.2f}",
                reason=f"Single trade profit of ${rep.largest_winner:,.2f} exceeds 20x initial capital (${initial_cap:,.2f}).",
                suggested_fix="Inspect lot sizing formula in position_sizing.py and leverage constraints."
            ))

        # 6. Max Drawdown > Prop Limit (in Prop Mode)
        if config.mode == EngineMode.PROP_FIRM:
            max_limit_pct = config.prop_rules.max_total_drawdown_pct * 100.0
            if rep.max_total_drawdown_pct > max_limit_pct:
                warnings.append(SanityCheckWarning(
                    metric_name="Max Overall Drawdown (%)",
                    observed_value=rep.max_total_drawdown_pct,
                    allowed_threshold=f"<= {max_limit_pct}%",
                    reason=f"Max Overall Drawdown ({rep.max_total_drawdown_pct}%) exceeded hard Prop Firm Limit ({max_limit_pct}%).",
                    suggested_fix="Inspect Prop State Machine equity reset logic and account termination triggers."
                ))

            # 7. Max Daily Drawdown > Daily Prop Limit (in Prop Mode)
            daily_limit_pct = config.prop_rules.max_daily_drawdown_pct * 100.0
            if rep.max_daily_drawdown_pct > daily_limit_pct:
                warnings.append(SanityCheckWarning(
                    metric_name="Max Daily Drawdown (%)",
                    observed_value=rep.max_daily_drawdown_pct,
                    allowed_threshold=f"<= {daily_limit_pct}%",
                    reason=f"Max Daily Drawdown ({rep.max_daily_drawdown_pct}%) exceeded hard Daily Prop Firm Limit ({daily_limit_pct}%).",
                    suggested_fix="Inspect RiskEngine daily loss tracking and intraday open equity calculation."
                ))

        # 8. Kelly Fraction > 50%
        if rep.kelly_fraction_pct > 50.0:
            warnings.append(SanityCheckWarning(
                metric_name="Kelly Fraction (%)",
                observed_value=rep.kelly_fraction_pct,
                allowed_threshold="<= 50.0%",
                reason="Kelly Criterion fraction exceeds 50%, indicating overestimating edge or underestimating loss variance.",
                suggested_fix="Inspect Win Rate vs Risk-to-Reward ratio formula in Kelly calculation."
            ))

        # 9. Recovery Factor > 20
        if rep.recovery_factor > 20.0:
            warnings.append(SanityCheckWarning(
                metric_name="Recovery Factor",
                observed_value=rep.recovery_factor,
                allowed_threshold="<= 20.0",
                reason="Recovery Factor (Net Profit / Max DD) exceeds 20.0, indicating unrealistically suppressed drawdown.",
                suggested_fix="Inspect peak drawdown denominator or compounding equity curve normalization."
            ))

        return warnings
