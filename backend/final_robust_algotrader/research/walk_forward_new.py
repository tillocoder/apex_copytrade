from typing import List, Dict, Any

def run_walk_forward(trades: List[Dict[str, Any]], n_splits: int = 4) -> Dict[str, Any]:
    if len(trades) < 20:
        return {'error': 'insufficient trades'}
    
    # Sort strictly by day (already chronological from backtest)
    sorted_trades = sorted(trades, key=lambda t: t['day'])
    n = len(sorted_trades)
    chunk = n // n_splits
    
    windows = []
    for w in range(n_splits):
        start = w * chunk
        end = (w + 1) * chunk if w < n_splits - 1 else n
        window_trades = sorted_trades[start:end]
        
        if not window_trades:
            continue
        
        wt = len(window_trades)
        wins = [t for t in window_trades if t['is_win']]
        losses = [t for t in window_trades if not t['is_win']]
        win_cnt = len(wins); loss_cnt = len(losses)
        
        gp = sum(t['pnl'] for t in wins)
        gl = abs(sum(t['pnl'] for t in losses))
        pf = gp / gl if gl > 0 else (99.9 if gp > 0 else 0.0)
        
        avg_win_r = sum(t['r_multiple'] for t in wins) / win_cnt if win_cnt > 0 else 0.0
        avg_loss_r = sum(abs(t['r_multiple']) for t in losses) / loss_cnt if loss_cnt > 0 else 0.0
        exp_r = (win_cnt / wt) * avg_win_r - (loss_cnt / wt) * avg_loss_r if wt > 0 else 0.0
        
        windows.append({
            'window': f'W{w+1}',
            'date_start': window_trades[0]['day'],
            'date_end': window_trades[-1]['day'],
            'trades': wt,
            'win_rate': round(win_cnt / wt * 100.0, 2),
            'profit_factor': round(pf, 2),
            'expectancy_r': round(exp_r, 3),
            'net_pnl': round(gp - gl, 2),
            'avg_win_r': round(avg_win_r, 2),
            'avg_loss_r': round(avg_loss_r, 2),
        })
    
    # Strict IS/OOS: last window = OOS (never seen during param selection)
    oos = windows[-1] if windows else {}
    in_sample_pfs = [w['profit_factor'] for w in windows[:-1]]
    avg_is_pf = sum(in_sample_pfs) / len(in_sample_pfs) if in_sample_pfs else 0.0
    
    oos_pass = oos.get('profit_factor', 0.0) >= 1.0
    
    return {
        'method': 'Time-sliced walk-forward (n_splits={})'.format(n_splits),
        'total_trades': n,
        'windows': windows,
        'oos_window': oos,
        'avg_is_pf': round(avg_is_pf, 2),
        'oos_pf': round(oos.get('profit_factor', 0.0), 2),
        'oos_status': 'PASS (PF>=1.0)' if oos_pass else 'FAIL (PF<1.0)',
        'note': 'Last window is untouched OOS — NOT used for parameter selection'
    }
