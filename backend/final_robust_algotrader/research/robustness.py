from typing import Dict, Any

def run_robustness_grid(data, cfg, exec_cfg) -> Dict[str, Any]:
    from backend.final_robust_algotrader.research.candidates import CandidateB
    from backend.final_robust_algotrader.research.tournament_engine import TournamentBacktest

    engine = TournamentBacktest(data, cfg, exec_cfg)

    results = []
    base_lb = cfg.strategy.breakout_lookback_bars
    base_sl = cfg.strategy.sl_atr_multiplier
    base_vol = cfg.strategy.volume_expansion_multiplier

    lookbacks = [40, 44, 48, 52, 56]
    sl_atrs = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
    vol_mults = [1.1, 1.25, 1.35, 1.50]

    total = len(lookbacks) * len(sl_atrs) * len(vol_mults)
    print("  Running " + str(total) + " parameter combinations...")
    done = 0

    for lb in lookbacks:
        for sl in sl_atrs:
            for vm in vol_mults:
                cfg.strategy.breakout_lookback_bars = lb
                cfg.strategy.sl_atr_multiplier = sl
                cfg.strategy.volume_expansion_multiplier = vm

                res = engine.run(CandidateB)

                cfg.strategy.breakout_lookback_bars = base_lb
                cfg.strategy.sl_atr_multiplier = base_sl
                cfg.strategy.volume_expansion_multiplier = base_vol

                results.append({
                    "lookback": lb,
                    "sl_atr": sl,
                    "vol_mult": vm,
                    "trades": res["trades_count"],
                    "win_rate": res["win_rate"],
                    "profit_factor": res["profit_factor"],
                    "net_pnl": res["net_pnl"],
                    "expectancy_r": res["expectancy_r"],
                    "max_dd_pct": res["max_dd_pct"],
                    "profitable": res["profit_factor"] >= 1.0,
                })
                done += 1
                if done % 30 == 0:
                    print("    " + str(done) + "/" + str(total) + " done...")

    pfs = [r["profit_factor"] for r in results]
    profitable = [r for r in results if r["profitable"]]
    avg_pf = sum(pfs) / len(pfs) if pfs else 0.0

    return {
        "total_combinations": total,
        "profitable_count": len(profitable),
        "profitable_pct": round(len(profitable) / total * 100.0, 2),
        "avg_pf_across_grid": round(avg_pf, 3),
        "min_pf": round(min(pfs), 2),
        "max_pf": round(max(pfs), 2),
        "base_params": {"lookback": base_lb, "sl_atr": base_sl, "vol_mult": base_vol},
        "results": results,
        "note": "Parameter selection NOT based on OOS results"
    }
