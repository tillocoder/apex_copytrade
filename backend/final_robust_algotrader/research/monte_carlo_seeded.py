import random
from typing import List, Dict, Any
from collections import defaultdict

SEED = 42

def run_drawdown_stress(trades: List[Dict[str, Any]], num_sims: int = 100000) -> Dict[str, Any]:
    rng = random.Random(SEED)
    pnls = [t['pnl'] for t in trades]
    n_t = len(pnls)
    if n_t == 0: return {}
    
    mc_dds = []
    mc_streaks = []
    
    for _ in range(num_sims):
        sampled = [pnls[rng.randint(0, n_t - 1)] for _ in range(n_t)]
        
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
    
    mc_dds.sort(); mc_streaks.sort()
    p = lambda arr, pct: arr[int(num_sims * pct)]
    
    return {
        'num_sims': num_sims,
        'seed': SEED,
        'method': 'Bootstrap with replacement — trade sequence randomization',
        'sampling': 'Each sim draws n_trades samples with replacement from observed PnL pool',
        'dd_p50': round(p(mc_dds, 0.50), 2),
        'dd_p75': round(p(mc_dds, 0.75), 2),
        'dd_p90': round(p(mc_dds, 0.90), 2),
        'dd_p95': round(p(mc_dds, 0.95), 2),
        'dd_p99': round(p(mc_dds, 0.99), 2),
        'dd_worst': round(mc_dds[-1], 2),
        'streak_p50': p(mc_streaks, 0.50),
        'streak_p75': p(mc_streaks, 0.75),
        'streak_p90': p(mc_streaks, 0.90),
        'streak_p95': p(mc_streaks, 0.95),
        'streak_p99': p(mc_streaks, 0.99),
        'streak_worst': mc_streaks[-1],
    }


def run_prop_simulator(trades: List[Dict[str, Any]], num_sims: int = 100000) -> Dict[str, Any]:
    rng = random.Random(SEED)
    day_groups = defaultdict(list)
    for t in trades:
        day_groups[t['day']].append(t)
    unique_days = sorted(day_groups.keys())
    n_days = len(unique_days)
    
    # Prop rules
    P1_TARGET = 10800.0   # +8%
    P2_TARGET = 10500.0   # +5%
    DAILY_LIMIT = 500.0   # 5% daily DD
    TOTAL_LIMIT = 1000.0  # 10% total DD
    
    p1_passes = 0; p2_passes = 0
    p1_days_list = []; p2_days_list = []
    
    for _ in range(num_sims):
        # Phase 1
        bal = 10000.0; peak = 10000.0; d_cnt = 0
        p1_ok = False; p1_fail = False
        while not p1_ok and not p1_fail:
            d_key = unique_days[rng.randint(0, n_days - 1)]
            d_trades = day_groups[d_key]
            day_start = bal; d_cnt += 1
            for tr in d_trades:
                bal += tr['pnl']
                if bal > peak: peak = bal
                # Daily and total drawdown checks
                if (day_start - bal) >= DAILY_LIMIT or (peak - bal) >= TOTAL_LIMIT:
                    p1_fail = True; break
                if bal >= P1_TARGET:
                    p1_ok = True; break
            if d_cnt > 365: p1_fail = True
        
        if p1_ok:
            p1_passes += 1
            p1_days_list.append(d_cnt)
            
            # Phase 2
            bal2 = 10000.0; peak2 = 10000.0; d_cnt2 = 0
            p2_ok = False; p2_fail = False
            while not p2_ok and not p2_fail:
                d_key = unique_days[rng.randint(0, n_days - 1)]
                d_trades = day_groups[d_key]
                day_start2 = bal2; d_cnt2 += 1
                for tr in d_trades:
                    bal2 += tr['pnl']
                    if bal2 > peak2: peak2 = bal2
                    if (day_start2 - bal2) >= DAILY_LIMIT or (peak2 - bal2) >= TOTAL_LIMIT:
                        p2_fail = True; break
                    if bal2 >= P2_TARGET:
                        p2_ok = True; break
                if d_cnt2 > 365: p2_fail = True
            
            if p2_ok:
                p2_passes += 1
                p2_days_list.append(d_cnt2)
    
    p1_days_list.sort(); p2_days_list.sort()
    med_p1 = p1_days_list[len(p1_days_list)//2] if p1_days_list else 0
    med_p2 = p2_days_list[len(p2_days_list)//2] if p2_days_list else 0
    
    return {
        'num_sims': num_sims,
        'seed': SEED,
        'method': 'Day-level bootstrap resampling (SYNTHETIC — not sequential history)',
        'p1_target_pct': 8.0,
        'p2_target_pct': 5.0,
        'daily_dd_limit_usd': DAILY_LIMIT,
        'total_dd_limit_usd': TOTAL_LIMIT,
        'phase_1_pass_count': p1_passes,
        'phase_1_pass_pct': round(p1_passes / num_sims * 100.0, 2),
        'phase_2_pass_count': p2_passes,
        'phase_2_pass_pct': round(p2_passes / max(1, p1_passes) * 100.0, 2),
        'overall_pass_count': p2_passes,
        'overall_pass_pct': round(p2_passes / num_sims * 100.0, 2),
        'median_p1_days': med_p1,
        'median_p2_days': med_p2,
        'median_total_days': med_p1 + med_p2,
    }


def run_career_simulation(trades: List[Dict[str, Any]], num_sims: int = 100000) -> Dict[str, Any]:
    rng = random.Random(SEED)
    day_groups = defaultdict(list)
    for t in trades:
        day_groups[t['day']].append(t)
    unique_days = sorted(day_groups.keys())
    n_days = len(unique_days)
    
    P1_TARGET = 10800.0; P2_TARGET = 10500.0
    DAILY_LIMIT = 500.0; TOTAL_LIMIT = 1000.0
    
    pass_counts = defaultdict(int)
    
    for _ in range(num_sims):
        days_left = 365
        passed = 0
        
        while days_left > 5:
            # Phase 1
            p1_ok = False; p1_fail = False
            bal = 10000.0; peak = 10000.0
            
            while days_left > 0 and not p1_ok and not p1_fail:
                d_key = unique_days[rng.randint(0, n_days - 1)]
                days_left -= 1
                day_start = bal
                for tr in day_groups[d_key]:
                    bal += tr['pnl']
                    if bal > peak: peak = bal
                    if (day_start - bal) >= DAILY_LIMIT or (peak - bal) >= TOTAL_LIMIT:
                        p1_fail = True; break
                    if bal >= P1_TARGET:
                        p1_ok = True; break
                if p1_fail: break
            
            if not p1_ok: break
            
            # Phase 2
            p2_ok = False; p2_fail = False
            bal2 = 10000.0; peak2 = 10000.0
            
            while days_left > 0 and not p2_ok and not p2_fail:
                d_key = unique_days[rng.randint(0, n_days - 1)]
                days_left -= 1
                day_start2 = bal2
                for tr in day_groups[d_key]:
                    bal2 += tr['pnl']
                    if bal2 > peak2: peak2 = bal2
                    if (day_start2 - bal2) >= DAILY_LIMIT or (peak2 - bal2) >= TOTAL_LIMIT:
                        p2_fail = True; break
                    if bal2 >= P2_TARGET:
                        p2_ok = True; break
                if p2_fail: break
            
            if p2_ok: passed += 1
            else: break
        
        pass_counts[passed] += 1
    
    return {
        'num_sims': num_sims,
        'seed': SEED,
        'method': 'SYNTHETIC CAREER RESAMPLING (Bootstrap day sequences, not sequential real history)',
        'p_0_count': pass_counts[0],
        'p_ge_1_count': sum(pass_counts[k] for k in pass_counts if k >= 1),
        'p_ge_2_count': sum(pass_counts[k] for k in pass_counts if k >= 2),
        'p_ge_3_count': sum(pass_counts[k] for k in pass_counts if k >= 3),
        'p_ge_4_count': sum(pass_counts[k] for k in pass_counts if k >= 4),
        'p_ge_5_count': sum(pass_counts[k] for k in pass_counts if k >= 5),
        'p_0': round(pass_counts[0] / num_sims * 100.0, 2),
        'p_ge_1': round(sum(pass_counts[k] for k in pass_counts if k >= 1) / num_sims * 100.0, 2),
        'p_ge_2': round(sum(pass_counts[k] for k in pass_counts if k >= 2) / num_sims * 100.0, 2),
        'p_ge_3': round(sum(pass_counts[k] for k in pass_counts if k >= 3) / num_sims * 100.0, 2),
        'p_ge_4': round(sum(pass_counts[k] for k in pass_counts if k >= 4) / num_sims * 100.0, 2),
        'p_ge_5': round(sum(pass_counts[k] for k in pass_counts if k >= 5) / num_sims * 100.0, 2),
        'raw_pass_distribution': dict(sorted(pass_counts.items())),
    }
