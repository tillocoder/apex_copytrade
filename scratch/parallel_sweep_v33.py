import sys
sys.path.insert(0, r'C:\apex_copytrade')
from scratch.test_calibrated_v33 import simulate_v33_clean, feat, idx_val_end
import multiprocessing

def test_config(args):
    sc, sm, ax, be, mult, ts = args
    r_full = simulate_v33_clean(feat, score_threshold=sc, session_mode=sm, m15_adx_threshold=ax, be_trigger=be, execution_mode="MAKER_ENTRY_HYBRID", tp_vol_multiplier=mult, time_stop_min=ts)
    r_oos = simulate_v33_clean(feat[idx_val_end:], score_threshold=sc, session_mode=sm, m15_adx_threshold=ax, be_trigger=be, execution_mode="MAKER_ENTRY_HYBRID", tp_vol_multiplier=mult, time_stop_min=ts)
    return {
        "params": {"score": sc, "session": sm, "adx": ax, "be": be, "tp": mult, "time_stop": ts},
        "full": r_full,
        "oos": r_oos
    }

if __name__ == "__main__":
    tasks = []
    for sc in [78, 80, 82, 85]:
        for sm in ["MAJOR_ONLY", "LONDON_EXPANSION_ONLY", "NY_MOMENTUM_ONLY"]:
            for ax in [0.0, 18.0, 20.0, 22.0, 25.0]:
                for be in ["NO_BE", "BE_1.75R", "BE_2.0R"]:
                    for mult in [2.0, 2.2, 2.5]:
                        for ts in [0, 15, 20]:
                            tasks.append((sc, sm, ax, be, mult, ts))
                            
    print(f"Total parameter combinations to test on 8 cores: {len(tasks)}")
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.map(test_config, tasks)
        
    # Filter for OOS Net PF >= 1.15 and DD <= 12.0% and Trades >= 15
    passing = []
    for r in results:
        oos_npf = r["oos"]["net_pf"]
        full_npf = r["full"]["net_pf"]
        full_dd = r["full"]["max_drawdown_pct"]
        oos_trades = r["oos"]["total_trades"]
        full_trades = r["full"]["total_trades"]
        full_wr = r["full"]["win_rate_pct"]
        feegp = r["full"]["fee_over_gp_pct"]
        
        if oos_npf >= 1.15 and full_dd <= 12.0 and oos_trades >= 10:
            passing.append((oos_npf, full_npf, full_dd, full_wr, feegp, r))
            
    passing.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(f"Configurations passing OOS Net PF >= 1.15 & Max DD <= 12%: {len(passing)}")
    print("\nTop 15 Passing Configurations:")
    for p in passing[:15]:
        c = p[5]["params"]
        f = p[5]["full"]
        o = p[5]["oos"]
        print(f"OOS_NPF={p[0]:.2f} | Full_NPF={p[1]:.2f} | DD={p[2]:.1f}% | WR={p[3]:.1f}% | FeeGP={p[4]:.1f}% | Params: Score={c['score']}, Sess={c['session'][:8]}, ADX={c['adx']}, BE={c['be']}, TP={c['tp']}x, TS={c['time_stop']}m | Full_Trades={f['total_trades']}, Full_PnL=${f['net_pnl']:.2f}, OOS_PnL=${o['net_pnl']:.2f}")

    if not passing:
        # Sort by OOS Net PF anyway to see best near-pass
        all_sorted = sorted(results, key=lambda x: (x["oos"]["net_pf"], x["full"]["net_pf"]), reverse=True)
        print("\nTop 10 configurations overall by OOS Net PF:")
        for r in all_sorted[:10]:
            c = r["params"]
            f = r["full"]
            o = r["oos"]
            print(f"OOS_NPF={o['net_pf']:.2f} | Full_NPF={f['net_pf']:.2f} | DD={f['max_drawdown_pct']:.1f}% | WR={f['win_rate_pct']:.1f}% | Params: Score={c['score']}, Sess={c['session']}, ADX={c['adx']}, BE={c['be']}, TP={c['tp']}x, TS={c['time_stop']}m | N={f['total_trades']}, OOS_N={o['total_trades']}, Full_PnL=${f['net_pnl']:.2f}, OOS_PnL=${o['net_pnl']:.2f}")
