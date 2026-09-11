import random
import math
from typing import List, Dict, Any

SEED = 42

def compute_bootstrap_ci(trades: List[Dict[str, Any]], n_resamples: int = 10000) -> Dict[str, Any]:
    rng = random.Random(SEED)
    n = len(trades)
    if n < 10:
        return {'error': 'insufficient trades (need >= 10)'}
    
    pnls = [t['pnl'] for t in trades]
    r_mults = [t['r_multiple'] for t in trades]
    is_wins = [t['is_win'] for t in trades]
    
    wrs = []
    pfs = []
    exps = []
    
    for _ in range(n_resamples):
        indices = [rng.randint(0, n-1) for _ in range(n)]
        sample_wins = [is_wins[i] for i in indices]
        sample_pnls = [pnls[i] for i in indices]
        sample_rs = [r_mults[i] for i in indices]
        
        wr = sum(sample_wins) / n
        wrs.append(wr)
        
        gp = sum(p for p in sample_pnls if p > 0)
        gl = abs(sum(p for p in sample_pnls if p <= 0))
        pf = gp / gl if gl > 0 else 99.9
        pfs.append(pf)
        
        win_cnt = sum(sample_wins)
        loss_cnt = n - win_cnt
        avg_wr = sum(r for r, w in zip(sample_rs, sample_wins) if w) / max(1, win_cnt)
        avg_lr = sum(abs(r) for r, w in zip(sample_rs, sample_wins) if not w) / max(1, loss_cnt)
        exp = (win_cnt / n) * avg_wr - (loss_cnt / n) * avg_lr
        exps.append(exp)
    
    wrs.sort(); pfs.sort(); exps.sort()
    
    lo = int(n_resamples * 0.025)
    hi = int(n_resamples * 0.975)
    
    # t-statistic and p-value approximation
    mean_exp = sum(exps) / len(exps)
    std_exp = math.sqrt(sum((x - mean_exp)**2 for x in exps) / len(exps))
    t_stat = mean_exp / max(1e-9, std_exp / math.sqrt(n))
    # Two-tailed p-value approximation (normal)
    p_val = 2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2))))
    
    obs_wr = sum(is_wins) / n * 100.0
    gp_obs = sum(p for p in pnls if p > 0)
    gl_obs = abs(sum(p for p in pnls if p <= 0))
    pf_obs = gp_obs / gl_obs if gl_obs > 0 else 99.9
    win_cnt_obs = sum(is_wins)
    loss_cnt_obs = n - win_cnt_obs
    avg_wr_obs = sum(r for r, w in zip(r_mults, is_wins) if w) / max(1, win_cnt_obs)
    avg_lr_obs = sum(abs(r) for r, w in zip(r_mults, is_wins) if not w) / max(1, loss_cnt_obs)
    exp_obs = (win_cnt_obs / n) * avg_wr_obs - (loss_cnt_obs / n) * avg_lr_obs
    
    return {
        'n_trades': n,
        'n_resamples': n_resamples,
        'seed': SEED,
        'observed_wr_pct': round(obs_wr, 2),
        'observed_pf': round(pf_obs, 2),
        'observed_expectancy_r': round(exp_obs, 3),
        'wr_ci_95_low': round(wrs[lo] * 100, 2),
        'wr_ci_95_high': round(wrs[hi] * 100, 2),
        'pf_ci_95_low': round(pfs[lo], 2),
        'pf_ci_95_high': round(pfs[hi], 2),
        'expectancy_ci_95_low': round(exps[lo], 3),
        'expectancy_ci_95_high': round(exps[hi], 3),
        't_statistic': round(t_stat, 3),
        'p_value': round(p_val, 4),
        'statistically_significant_5pct': p_val < 0.05,
        'note': 'Bootstrap CI uses sampling with replacement, seed=42 for reproducibility'
    }
