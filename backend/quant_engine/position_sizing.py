import os
import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .config import PropFirmRulesConfig, RiskConfig

logger = logging.getLogger("APEX_POSITION_SIZING")

@dataclass
class PositionSizingResult:
    is_approved: bool
    final_size: float
    final_notional: float
    initial_margin: float
    effective_leverage: float
    effective_sl_distance: float
    risk_budget_usd: float
    raw_size: float
    raw_notional: float
    rejection_reason: Optional[str]
    audit_log: Dict[str, Any]

class PositionSizingEngine:
    """
    Institutional Multi-Layer Risk, Sizing & Margin Engine.
    Shared identically by both Backtest Engine and LIVE Execution Manager.
    """

    @staticmethod
    def calculate_position_size(
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        current_equity: float,
        open_positions: List[Dict[str, Any]],
        pending_orders: List[Dict[str, Any]],
        prop_rules: PropFirmRulesConfig,
        risk_cfg: Optional[RiskConfig] = None,
        min_qty: float = 0.001,
        step_size: float = 0.001,
        confidence_score: float = 80.0
    ) -> PositionSizingResult:

        # Helper to construct rejection result
        def reject(reason: str, audit: Dict[str, Any]) -> PositionSizingResult:
            logger.warning(f"[SIZING REJECTED] {symbol} {side} — Reason: {reason}")
            return PositionSizingResult(
                is_approved=False,
                final_size=0.0,
                final_notional=0.0,
                initial_margin=0.0,
                effective_leverage=prop_rules.symbol_leverage_map.get(symbol, prop_rules.default_leverage),
                effective_sl_distance=0.0,
                risk_budget_usd=0.0,
                raw_size=0.0,
                raw_notional=0.0,
                rejection_reason=reason,
                audit_log=audit
            )

        # 1. Entry & SL Price Validation
        if entry_price <= 0 or stop_loss <= 0 or current_equity <= 0:
            return reject("INVALID_PRICE: Entry, SL, or Equity <= 0", {})

        raw_sl_dist = abs(entry_price - stop_loss)
        min_sl_dist = entry_price * prop_rules.min_sl_distance_pct
        effective_sl_distance = max(raw_sl_dist, min_sl_dist)

        # 2. Drawdown-Adjusted Adaptive Risk Budgeting
        total_drawdown_pct = max(0.0, (prop_rules.initial_capital - current_equity) / prop_rules.initial_capital)
        
        if total_drawdown_pct >= prop_rules.max_total_drawdown_pct:
            return reject("RISK_REJECT: Maximum total drawdown threshold exceeded", {"drawdown_pct": total_drawdown_pct})

        if total_drawdown_pct < 0.02:
            adaptive_risk_pct = prop_rules.risk_per_trade_pct
        elif total_drawdown_pct < 0.04:
            adaptive_risk_pct = 0.010
        elif total_drawdown_pct < 0.05:
            adaptive_risk_pct = 0.005
        else:
            adaptive_risk_pct = 0.0025

        # 3. Fee + Slippage + Funding Buffer Adjustment
        unit_fee_slippage = entry_price * (prop_rules.fee_buffer_pct + prop_rules.slippage_buffer_pct)
        effective_unit_loss = effective_sl_distance + unit_fee_slippage
        risk_budget_usd = max(0.0, current_equity * adaptive_risk_pct - prop_rules.funding_buffer_usd)
        
        if effective_unit_loss <= 0 or risk_budget_usd <= 0:
            return reject("RISK_REJECT: Effective unit loss or risk budget <= 0", {})

        raw_size = risk_budget_usd / effective_unit_loss
        raw_notional = raw_size * entry_price

        # 4. Single Position Notional Cap (Max 3.0x Equity = $30k on $10k)
        single_pos_cap_notional = current_equity * prop_rules.max_single_position_notional_mult
        cap1_size = single_pos_cap_notional / entry_price

        # 5. Portfolio Total Exposure Cap (Max 8.0x Equity = $80k on $10k)
        portfolio_exposure_cap_notional = current_equity * prop_rules.max_total_notional_exposure_mult
        all_active = open_positions + pending_orders
        
        existing_open_notional = sum(
            float(p.get("entryPrice") or p.get("entry_price") or entry_price) * float(p.get("size", 0.0))
            for p in all_active
        )
        remaining_portfolio_notional = max(0.0, portfolio_exposure_cap_notional - existing_open_notional)
        cap2_size = remaining_portfolio_notional / entry_price

        # 6. Portfolio Aggregate Risk Cap (Max 4.0% Aggregate Risk = $400 on $10k)
        portfolio_risk_cap_usd = current_equity * prop_rules.max_crypto_portfolio_risk_pct
        existing_risk_usd = sum(
            abs(float(p.get("entryPrice") or p.get("entry_price", entry_price)) - float(p.get("sl") or p.get("stop_loss", 0.0))) * float(p.get("size", 0.0))
            for p in all_active
        )
        remaining_risk_usd = max(0.0, portfolio_risk_cap_usd - existing_risk_usd)
        cap3_size = remaining_risk_usd / effective_unit_loss

        # 7. Initial Margin Utilization Cap (Max 45% Initial Margin = $4,500 on $10k)
        max_margin_capacity_usd = current_equity * prop_rules.max_margin_utilization_pct
        effective_leverage = float(prop_rules.symbol_leverage_map.get(symbol, prop_rules.default_leverage))
        
        existing_margin_used = sum(
            (float(p.get("entryPrice") or p.get("entry_price", entry_price)) * float(p.get("size", 0.0))) / max(1.0, float(p.get("leverage", effective_leverage)))
            for p in all_active
        )
        remaining_margin_capacity = max(0.0, max_margin_capacity_usd - existing_margin_used)
        cap4_size = (remaining_margin_capacity * effective_leverage) / entry_price

        # 8. Maintenance Margin Safety Guard
        max_maint_margin_allowed = current_equity * 0.80
        existing_maint_margin = sum(
            float(p.get("entryPrice") or p.get("entry_price", entry_price)) * float(p.get("size", 0.0)) * prop_rules.maintenance_margin_rate
            for p in all_active
        )
        remaining_maint_capacity = max(0.0, max_maint_margin_allowed - existing_maint_margin)
        cap5_size = remaining_maint_capacity / (entry_price * prop_rules.maintenance_margin_rate)

        # 9. Multi-Cap Consolidation & Step Rounding
        unrounded_size = min(raw_size, cap1_size, cap2_size, cap3_size, cap4_size, cap5_size)

        if step_size > 0:
            final_size = math.floor(unrounded_size / step_size) * step_size
            prec = max(0, -int(math.floor(math.log10(step_size)))) if step_size < 1 else 0
            final_size = round(final_size, prec)
        else:
            final_size = round(unrounded_size, 4)

        # 10. Rejection Guard Verifications
        if remaining_portfolio_notional <= 0:
            return reject("RISK_REJECT: Maximum total portfolio exposure cap exceeded ($80,000)", {})

        if remaining_risk_usd <= 0:
            return reject("RISK_REJECT: Maximum portfolio aggregate risk cap exceeded ($400)", {})

        if remaining_margin_capacity <= 0:
            return reject("MARGIN_REJECT: Maximum margin utilization exceeded ($4,500)", {})

        if remaining_maint_capacity <= 0:
            return reject("MARGIN_REJECT: Maintenance margin safety limit exceeded", {})

        if final_size < min_qty:
            return reject(f"SIZE_REJECT: Calculated position size ({final_size}) is below minimum tradable quantity ({min_qty})", {})

        # Compute Final Audit Log & Metrics
        final_notional = round(final_size * entry_price, 2)
        initial_margin = round(final_notional / effective_leverage, 2)
        projected_portfolio_exposure = round(existing_open_notional + final_notional, 2)
        projected_margin_used = round(existing_margin_used + initial_margin, 2)
        trade_risk_usd = round(effective_unit_loss * final_size, 2)
        projected_aggregate_risk = round(existing_risk_usd + trade_risk_usd, 2)

        audit_log = {
            "symbol": symbol,
            "side": side,
            "entry": entry_price,
            "sl": stop_loss,
            "effective_sl_distance": round(effective_sl_distance, 4),
            "risk_budget_usd": round(risk_budget_usd, 2),
            "raw_size": round(raw_size, 4),
            "raw_notional": round(raw_notional, 2),
            "final_size": final_size,
            "final_notional": final_notional,
            "leverage": effective_leverage,
            "initial_margin": initial_margin,
            "existing_margin_used": round(existing_margin_used, 2),
            "projected_margin_used": projected_margin_used,
            "existing_portfolio_exposure": round(existing_open_notional, 2),
            "projected_portfolio_exposure": projected_portfolio_exposure,
            "trade_risk_usd": trade_risk_usd,
            "projected_aggregate_risk": projected_aggregate_risk,
            "fee_buffer_usd": round(entry_price * prop_rules.fee_buffer_pct * final_size, 2),
            "slippage_buffer_usd": round(entry_price * prop_rules.slippage_buffer_pct * final_size, 2),
            "decision": "APPROVED"
        }

        logger.info(
            f"[SIZING APPROVED] {symbol} {side} | Entry: ${entry_price:,.2f} | Size: {final_size} | "
            f"Notional: ${final_notional:,.2f} | Margin: ${initial_margin:,.2f} | Risk: ${trade_risk_usd:,.2f}"
        )

        return PositionSizingResult(
            is_approved=True,
            final_size=final_size,
            final_notional=final_notional,
            initial_margin=initial_margin,
            effective_leverage=effective_leverage,
            effective_sl_distance=round(effective_sl_distance, 4),
            risk_budget_usd=round(risk_budget_usd, 2),
            raw_size=round(raw_size, 4),
            raw_notional=round(raw_notional, 2),
            rejection_reason=None,
            audit_log=audit_log
        )
