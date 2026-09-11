import json, sys
sys.path.insert(0, 'c:/apex_copytrade')

def compute_from_trades(trades):
    tot = len(trades)
    if tot == 0: return {}
    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]
    wc = len(wins); lc = len(losses)
    gp = sum(t['pnl'] for t in wins)
    gl = abs(sum(t['pnl'] for t in losses))
    pf = gp/gl if gl > 0 else 99.9
    awr = sum(t['r_multiple'] for t in wins)/wc if wc > 0 else 0.0
    alr = sum(abs(t['r_multiple']) for t in losses)/lc if lc > 0 else 0.0
    exp = (wc/tot)*awr - (lc/tot)*alr
    return {
        'trades_count': tot,
        'win_rate': round(wc/tot*100.0, 2),
        'profit_factor': round(pf, 2),
        'net_pnl': round(gp-gl, 2),
        'expectancy_r': round(exp, 3),
        'avg_win_r': round(awr, 2),
        'avg_loss_r': round(alr, 2),
    }

def test_metrics_reproduce_from_raw():
    report = json.load(open('c:/apex_copytrade/backend/reports/FINAL_ROBUST_ALGOTRADER_REPORT.json'))
    trades = report['kpi']['trades']
    kpi = report['kpi']
    computed = compute_from_trades(trades)
    assert computed['win_rate'] == kpi['win_rate'], str(computed['win_rate']) + ' != ' + str(kpi['win_rate'])
    assert computed['profit_factor'] == kpi['profit_factor'], 'PF mismatch'
    assert computed['net_pnl'] == kpi['net_pnl'], 'Net PnL mismatch'
    wr = computed['win_rate']; pf = computed['profit_factor']; net = computed['net_pnl']
    print('PASS test_metrics_reproduce: WR=' + str(wr) + '%, PF=' + str(pf) + ', Net=$' + str(net))

def test_win_count():
    report = json.load(open('c:/apex_copytrade/backend/reports/FINAL_ROBUST_ALGOTRADER_REPORT.json'))
    trades = report['kpi']['trades']
    wins = sum(1 for t in trades if t['is_win'])
    total = len(trades)
    wr = round(wins/total*100.0, 2)
    assert wr == 32.52, 'WR from raw count: ' + str(wr)
    print('PASS test_win_count: ' + str(wins) + '/' + str(total) + ' = ' + str(wr) + '%')

if __name__ == '__main__':
    print('=== METRICS REPRODUCIBILITY TESTS ===')
    test_metrics_reproduce_from_raw()
    test_win_count()
    print('ALL METRICS TESTS PASSED')
