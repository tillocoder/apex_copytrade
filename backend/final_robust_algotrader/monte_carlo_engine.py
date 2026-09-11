"""
Monte Carlo & Prop Firm Career Simulator — 100,000 Runs.
"""
import random
from typing import Dict, Any, List
from collections import defaultdict

class MonteCarloEngine:
    @staticmethod
    def run_drawdown_streaks(trades: List[Dict[str, Any]], num_sims: int = 100000) -> Dict[str, Any]:
        pnls = [t["pnl"] for t in trades]
        n_t = len(pnls)
        if n_t == 0: return {}

        mc_dds = []
        mc_streaks = []

        for _ in range(num_sims):
            sampled = [pnls[random.randint(0, n_t - 1)] for _ in range(n_t)]
            curr_s = 0; max_s = 0
            for p in sampled:
                if p <= 0:
                    curr_s += 1
                    if curr_s > max_s: max_s = curr_s
                else: curr_s = 0
            mc_streaks.append(max_s)

            cap = 10000.0; peak = 10000.0; max_d = 0.0
            for p in sampled:
                cap += p
                if cap > peak: peak = cap
                dd = ((peak - cap) / peak) * 100.0 if peak > 0 else 0.0
                if dd > max_d: max_d = dd
            mc_dds.append(max_d)

        mc_dds.sort()
        mc_streaks.sort()

        return {
            "dd_p50": round(mc_dds[int(num_sims * 0.50)], 2),
            "dd_p75": round(mc_dds[int(num_sims * 0.75)], 2),
            "dd_p90": round(mc_dds[int(num_sims * 0.90)], 2),
            "dd_p95": round(mc_dds[int(num_sims * 0.95)], 2),
            "dd_p99": round(mc_dds[int(num_sims * 0.99)], 2),
            "streak_p50": mc_streaks[int(num_sims * 0.50)],
            "streak_p75": mc_streaks[int(num_sims * 0.75)],
            "streak_p90": mc_streaks[int(num_sims * 0.90)],
            "streak_p95": mc_streaks[int(num_sims * 0.95)],
            "streak_p99": mc_streaks[int(num_sims * 0.99)],
        }

    @staticmethod
    def run_prop_challenge(trades: List[Dict[str, Any]], num_sims: int = 100000) -> Dict[str, Any]:
        day_groups = defaultdict(list)
        for t in trades:
            day_groups[t["day"]].append(t)
        unique_days = sorted(day_groups.keys())
        n_days = len(unique_days)

        p1_passes = 0; p2_passes = 0
        p1_days = []; p2_days = []

        for _ in range(num_sims):
            # Phase 1
            bal = 10000.0; peak = 10000.0; d_cnt = 0
            p1_ok = False; p1_fail = False
            while not p1_ok and not p1_fail:
                d_key = unique_days[random.randint(0, n_days - 1)]
                d_trades = day_groups[d_key]
                day_start = bal
                d_cnt += 1
                for tr in d_trades:
                    bal += tr["pnl"]
                    if bal > peak: peak = bal
                    if (day_start - bal) >= 500.0 or (peak - bal) >= 1000.0:
                        p1_fail = True; break
                    if bal >= 10800.0:
                        p1_ok = True; break
                if d_cnt > 365: p1_fail = True

            if p1_ok:
                p1_passes += 1
                p1_days.append(d_cnt)

                # Phase 2
                bal2 = 10000.0; peak2 = 10000.0; d_cnt2 = 0
                p2_ok = False; p2_fail = False
                while not p2_ok and not p2_fail:
                    d_key = unique_days[random.randint(0, n_days - 1)]
                    d_trades = day_groups[d_key]
                    day_start2 = bal2
                    d_cnt2 += 1
                    for tr in d_trades:
                        bal2 += tr["pnl"]
                        if bal2 > peak2: peak2 = bal2
                        if (day_start2 - bal2) >= 500.0 or (peak2 - bal2) >= 1000.0:
                            p2_fail = True; break
                        if bal2 >= 10500.0:
                            p2_ok = True; break
                    if d_cnt2 > 365: p2_fail = True

                if p2_ok:
                    p2_passes += 1
                    p2_days.append(d_cnt2)

        p1_days.sort(); p2_days.sort()
        m_p1 = p1_days[len(p1_days)//2] if p1_days else 0
        m_p2 = p2_days[len(p2_days)//2] if p2_days else 0

        return {
            "phase_1_pass_pct": round(p1_passes / num_sims * 100.0, 2),
            "phase_2_pass_pct": round(p2_passes / max(1, p1_passes) * 100.0, 2),
            "overall_pass_pct": round(p2_passes / num_sims * 100.0, 2),
            "median_p1_days": m_p1,
            "median_p2_days": m_p2,
            "median_total_days": m_p1 + m_p2
        }

    @staticmethod
    def run_career_simulation(trades: List[Dict[str, Any]], num_sims: int = 100000) -> Dict[str, Any]:
        day_groups = defaultdict(list)
        for t in trades:
            day_groups[t["day"]].append(t)
        unique_days = sorted(day_groups.keys())
        n_days = len(unique_days)
        pass_counts = defaultdict(int)

        for _ in range(num_sims):
            days_left = 365
            passed = 0
            while days_left > 10:
                # Phase 1
                p1_ok = False; bal = 10000.0; peak = 10000.0
                while days_left > 0 and not p1_ok:
                    d_key = unique_days[random.randint(0, n_days - 1)]
                    days_left -= 1
                    s_day = bal
                    for tr in day_groups[d_key]:
                        bal += tr["pnl"]
                        if bal > peak: peak = bal
                        if (s_day - bal) >= 500.0 or (peak - bal) >= 1000.0:
                            days_left -= 1; break
                        if bal >= 10800.0: p1_ok = True; break
                    if (s_day - bal) >= 500.0 or (peak - bal) >= 1000.0: break

                if not p1_ok: continue

                # Phase 2
                p2_ok = False; bal2 = 10000.0; peak2 = 10000.0
                while days_left > 0 and not p2_ok:
                    d_key = unique_days[random.randint(0, n_days - 1)]
                    days_left -= 1
                    s_day2 = bal2
                    for tr in day_groups[d_key]:
                        bal2 += tr["pnl"]
                        if bal2 > peak2: peak2 = bal2
                        if (s_day2 - bal2) >= 500.0 or (peak2 - bal2) >= 1000.0:
                            days_left -= 1; break
                        if bal2 >= 10500.0: p2_ok = True; break
                    if (s_day2 - bal2) >= 500.0 or (peak2 - bal2) >= 1000.0: break

                if p2_ok: passed += 1
            pass_counts[passed] += 1

        return {
            "p_0": round(pass_counts[0] / num_sims * 100.0, 2),
            "p_ge_1": round(sum(pass_counts[k] for k in pass_counts if k >= 1) / num_sims * 100.0, 2),
            "p_ge_2": round(sum(pass_counts[k] for k in pass_counts if k >= 2) / num_sims * 100.0, 2),
            "p_ge_3": round(sum(pass_counts[k] for k in pass_counts if k >= 3) / num_sims * 100.0, 2),
            "p_ge_4": round(sum(pass_counts[k] for k in pass_counts if k >= 4) / num_sims * 100.0, 2),
            "p_ge_5": round(sum(pass_counts[k] for k in pass_counts if k >= 5) / num_sims * 100.0, 2),
        }
