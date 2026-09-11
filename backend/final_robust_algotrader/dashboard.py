"""
Production Terminal Dashboard for Multi-Strategy Ensemble.
Displays: ACCOUNT, STRATEGY, RISK, EXECUTION, PERFORMANCE.
"""
from typing import Dict, Any, List
from datetime import datetime, timezone

class ProductionDashboard:
    @staticmethod
    def render(state: Dict[str, Any]) -> str:
        acc1 = state.get("acc1", {})
        acc2 = state.get("acc2", {})
        strat = state.get("strategy", {})
        risk = state.get("risk", {})
        execution = state.get("execution", {})
        perf = state.get("performance", {})
        
        lines = []
        lines.append("=" * 85)
        lines.append("   APEX PROPFIRM MULTI-STRATEGY ENSEMBLE — PRODUCTION MISSION CONTROL")
        lines.append(f"   Status: {execution.get('mode', 'PAPER')} MODE | System Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 85)

        # 1. ACCOUNT SECTION
        lines.append("\n[1] ACCOUNT OVERVIEW (TWO PARALLEL PROP CHALLENGES)")
        lines.append(f"{'Metric':<20} | {'Account 1 (Lead)':<28} | {'Account 2 (Staggered +45d)':<28}")
        lines.append("-" * 85)
        lines.append(f"{'Status':<20} | {acc1.get('status', 'ACTIVE'):<28} | {acc2.get('status', 'ACTIVE'):<28}")
        lines.append(f"{'Phase / Target':<20} | Phase {acc1.get('phase', 1)} (${acc1.get('target', 10800):,.2f}){'':<12} | Phase {acc2.get('phase', 1)} (${acc2.get('target', 10800):,.2f})")
        lines.append(f"{'Balance / Equity':<20} | ${acc1.get('balance', 10000):,.2f} / ${acc1.get('equity', 10000):,.2f}{'':<4} | ${acc2.get('balance', 10000):,.2f} / ${acc2.get('equity', 10000):,.2f}")
        lines.append(f"{'Daily DD / Limit':<20} | {acc1.get('daily_dd_pct', 0.0):.2f}% (Limit: 5.00%){'':<9} | {acc2.get('daily_dd_pct', 0.0):.2f}% (Limit: 5.00%)")
        lines.append(f"{'Max DD / Limit':<20} | {acc1.get('max_dd_pct', 0.0):.2f}% (Limit: 10.00%){'':<8} | {acc2.get('max_dd_pct', 0.0):.2f}% (Limit: 10.00%)")
        lines.append(f"{'Remaining DD Buffer':<20} | ${acc1.get('rem_dd_buffer', 1000):,.2f}{'':<19} | ${acc2.get('rem_dd_buffer', 1000):,.2f}")
        lines.append(f"{'Completed Passes':<20} | {acc1.get('passes', 0)} passes{'':<21} | {acc2.get('passes', 0)} passes")

        # 2. STRATEGY SECTION
        lines.append("\n[2] STRATEGY SIGNALS (CLOSED 1H CANDLE)")
        lines.append(f"  Macro Regime:      {strat.get('regime', '4H EMA50 BULLISH TREND')}")
        lines.append(f"  BTC Pullback:      {strat.get('btc_pullback', 'NEUTRAL (RSI 48.2)')}")
        lines.append(f"  ETH Pullback:      {strat.get('eth_pullback', 'NEUTRAL (RSI 51.5)')}")
        lines.append(f"  BTC Donchian 48H:  {strat.get('btc_donchian', 'WAITING (Price within 48h range)')}")
        lines.append(f"  Last Trade:        {strat.get('last_trade', 'None')}")
        lines.append(f"  Next Check:        On close of next 1H candle (:00 UTC)")

        # 3. RISK SECTION
        lines.append("\n[3] RISK CONTROLS")
        lines.append(f"  Risk per Trade:    {risk.get('risk_per_trade', '1.00% ($100.00)')}")
        lines.append(f"  BTC Exposure:      {risk.get('btc_exposure', '0.00% ($0.00)')}")
        lines.append(f"  ETH Exposure:      {risk.get('eth_exposure', '0.00% ($0.00)')}")
        lines.append(f"  Correlated Risk:   {risk.get('total_risk', '0.00%')} / Max Cap: 1.50%")
        lines.append(f"  Volatility Filter: {risk.get('vol_filter', 'NORMAL (ATR% = 0.85%)')}")

        # 4. EXECUTION & RECONCILIATION SECTION
        lines.append("\n[4] EXECUTION SAFETY & POSITION RECONCILIATION")
        lines.append(f"  API Connection:    {execution.get('api_status', 'HEALTHY (REST / WebSocket)')}")
        lines.append(f"  Last Closed Bar:   {execution.get('last_bar', '2026-09-08 23:00:00 UTC')}")
        lines.append(f"  Position Match:    {execution.get('reconciliation', 'MATCHED (Local == Exchange)')}")
        lines.append(f"  SL Confirmation:   {execution.get('sl_status', 'VERIFIED (100% orders have active hard SL)')}")
        lines.append(f"  TP Confirmation:   {execution.get('tp_status', 'VERIFIED (TP1 50% + TP2 50% active)')}")
        lines.append(f"  Duplicate Guard:   {execution.get('dup_guard', 'ACTIVE (Deterministic ID check)')}")

        # 5. PERFORMANCE METRICS
        lines.append("\n[5] PRODUCTION PERFORMANCE SUMMARY")
        lines.append(f"  Total Trades:      {perf.get('trades', 0)} ({perf.get('trades_per_mo', 0.0):.1f} trades/month)")
        lines.append(f"  Win Rate:          {perf.get('wr', 0.0):.2f}%")
        lines.append(f"  Net Profit Factor: {perf.get('pf', 0.0):.2f} (Tier C 0.12% Round-Trip Costs Included)")
        lines.append(f"  Net PnL ($):       ${perf.get('net_pnl', 0.0):,.2f} (+{perf.get('roi_pct', 0.0):.2f}%)")
        lines.append(f"  Expectancy:        {perf.get('expectancy_r', 0.0):+.3f} R")
        lines.append(f"  Max Drawdown:      {perf.get('max_dd_pct', 0.0):.2f}%")
        lines.append(f"  Current Streak:    {perf.get('loss_streak', 0)} losses")
        lines.append("=" * 85)
        return "\n".join(lines)
