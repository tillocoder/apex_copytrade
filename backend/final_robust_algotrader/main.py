"""
CLI Execution Entrypoint for FINAL_ROBUST_ALGOTRADER.
"""
import os
import json
from datetime import datetime, timezone

from .config import AlgoTraderConfig
from .market_data import MarketDataEngine
from .backtest_engine import BacktestEngine
from .monte_carlo_engine import MonteCarloEngine

def main():
    print("=" * 80)
    print("FINAL_ROBUST_ALGOTRADER — PRODUCTION INITIALIZATION")
    print("=" * 80)

    cfg = AlgoTraderConfig()
    data = MarketDataEngine(cfg.market_data.cache_path)
    bt = BacktestEngine(cfg, data)

    print("\n[1] Running Full 1-Year Event-Driven Backtest (Net of 0.12% fees)...")
    res = bt.run()
    trades = res["trades"]
    print(f"  Trades: {res['trades_count']}, WR: {res['win_rate']}%, PF: {res['profit_factor']}, Net: ${res['net_pnl']:.2f}, DD: {res['max_dd_pct']}%")

    print("\n[2] Running 100,000 Monte Carlo Stress Tests...")
    mc_dd = MonteCarloEngine.run_drawdown_streaks(trades, num_sims=100000)
    print(f"  MC Max DD P95: {mc_dd['dd_p95']}%, Streak P95: {mc_dd['streak_p95']}")

    print("\n[3] Running 100,000 Prop Firm Challenge Simulations...")
    prop_res = MonteCarloEngine.run_prop_challenge(trades, num_sims=100000)
    print(f"  P1 Pass: {prop_res['phase_1_pass_pct']}%, P2 Pass: {prop_res['phase_2_pass_pct']}%, Overall: {prop_res['overall_pass_pct']}%")

    print("\n[4] Running 100,000 1-Year Career Simulations...")
    career = MonteCarloEngine.run_career_simulation(trades, num_sims=100000)
    print(f"  P(>=1): {career['p_ge_1']}%, P(>=2): {career['p_ge_2']}%, P(>=5): {career['p_ge_5']}%")

    # Export master report
    rep = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kpi": res,
        "monte_carlo_drawdown": mc_dd,
        "prop_challenge": prop_res,
        "career_1y": career
    }
    out_file = "c:/apex_copytrade/backend/reports/FINAL_ROBUST_ALGOTRADER_REPORT.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print(f"\nReport saved to: {out_file}")

if __name__ == "__main__":
    main()
