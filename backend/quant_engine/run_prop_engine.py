import os
import sys

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.quant_engine.config import EngineConfig, EngineMode, PropFirmRulesConfig, ExecutionConfig, RiskConfig, StrategyConfig
from backend.quant_engine.market_data import MarketDataEngine
from backend.quant_engine.backtest import BacktestEngine
from backend.quant_engine.optimization import MonteCarloOptimizer
from backend.quant_engine.real_data_engine import RealHistoricalDataEngine
from backend.quant_engine.reporting import ReportEngine

def main():
    use_synthetic_stress_test = "--stress-test" in sys.argv
    print("[INIT] Loading Institutional Prop Engine Configurations...")
    
    # 1. PROP FIRM EVALUATION MODE CONFIG
    prop_config = EngineConfig(
        mode=EngineMode.PROP_FIRM,
        prop_rules=PropFirmRulesConfig(
            initial_capital=10000.0,
            stage1_target_pct=0.08,
            stage2_target_pct=0.05,
            max_daily_drawdown_pct=0.05,
            max_total_drawdown_pct=0.10,
            enforce_stage_reset=True
        ),
        execution=ExecutionConfig(commission_pct=0.0004, spread_pips=0.8, slippage_pips=0.3),
        risk=RiskConfig(base_risk_pct=0.005, min_risk_pct=0.0025, max_risk_pct=0.0100, max_open_positions=2),
        strategy=StrategyConfig(timeframe="M15", confidence_threshold=70.0)
    )

    # 2. PORTFOLIO COMPOUNDING MODE CONFIG
    portfolio_config = EngineConfig(
        mode=EngineMode.PORTFOLIO,
        prop_rules=PropFirmRulesConfig(initial_capital=10000.0),
        execution=ExecutionConfig(commission_pct=0.0004, spread_pips=0.8, slippage_pips=0.3),
        risk=RiskConfig(base_risk_pct=0.005, min_risk_pct=0.0025, max_risk_pct=0.0100, max_open_positions=2),
        strategy=StrategyConfig(timeframe="M15", confidence_threshold=70.0)
    )

    market_data = MarketDataEngine()

    if use_synthetic_stress_test:
        print("[DATA STRESS TEST] Generating Synthetic 1-Year M15 Market Datasets (BTC/USDT & ETH/USDT)...")
        multi_data = market_data.generate_multi_symbol_1year(seed=42)
    else:
        print("[REAL DATA] Loading 3-Year Real Historical M15 OHLCV Datasets (BTC/USDT & ETH/USDT)...")
        btc_candles = RealHistoricalDataEngine.get_symbol_data("BTC/USDT", years=3.0)
        eth_candles = RealHistoricalDataEngine.get_symbol_data("ETH/USDT", years=3.0)
        multi_data = {"BTC/USDT": btc_candles, "ETH/USDT": eth_candles}

    all_candles = []
    for sym, c_list in multi_data.items():
        all_candles.extend(c_list)
    market_data.load_from_candles(all_candles)

    # EXECUTE MODE 1: PROP FIRM EVALUATION MODE
    print("\n[MODE 1] Executing Prop Firm Evaluation Engine...")
    prop_backtester = BacktestEngine(prop_config)
    prop_res = prop_backtester.run(market_data)

    print("[OPTIMIZATION] Running 1,000-Simulation Monte Carlo Stress Test...")
    mc_optimizer = MonteCarloOptimizer(prop_config, num_simulations=1000)
    mc_summary = mc_optimizer.run_monte_carlo(prop_res)

    print("[REPORT] Printing Prop Firm Evaluation Summary...")
    ReportEngine.print_summary(prop_res, mc_summary)
    ReportEngine.export_to_files(prop_res, mc_summary, output_dir="backend/reports")

    # EXECUTE MODE 2: UNLIMITED PORTFOLIO COMPOUNDING MODE
    print("\n[MODE 2] Executing Unlimited Portfolio Compounding Engine...")
    portfolio_backtester = BacktestEngine(portfolio_config)
    portfolio_res = portfolio_backtester.run(market_data)

    print("[REPORT] Printing Unlimited Portfolio Compounding Summary...")
    ReportEngine.print_portfolio_summary(portfolio_res)

if __name__ == "__main__":
    main()
