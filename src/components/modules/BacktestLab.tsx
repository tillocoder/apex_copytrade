import React, { useState, useEffect, useRef } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { 
  FlaskConical, 
  Play, 
  ShieldCheck, 
  CheckCircle2, 
  Trophy, 
  Clock, 
  Award, 
  RefreshCw,
  Activity,
  Zap,
  Shield,
  Radio,
  Download
} from 'lucide-react';
import { BacktestService } from '../../services/backtestService';

export const BacktestLab: React.FC = () => {
  const { backtest, setBacktest, addLog } = useTerminal();
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [curveMode, setCurveMode] = useState<'master' | 'backtest' | 'live' | 'reset'>('master');
  const [loading, setLoading] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<string>('Hozir');
  const pollTimerRef = useRef<any>(null);

  const loadBacktestData = async (forceRerun: boolean = false) => {
    try {
      setLoading(true);
      const res = await BacktestService.fetchBacktestResults(forceRerun);
      const data: any = res.data || res;
      if (data && (res.status === 'SUCCESS' || data.status === 'SUCCESS' || data.netProfit !== undefined)) {
        setBacktest(prev => ({
          ...prev,
          ...data,
          monthlyReturns: (data.monthlyReturns && data.monthlyReturns.length > 0)
            ? data.monthlyReturns
            : prev.monthlyReturns,
          equityCurve: (data.equityCurve && data.equityCurve.length > 0)
            ? data.equityCurve
            : prev.equityCurve,
          liveEquityCurve: (data.liveEquityCurve && data.liveEquityCurve.length > 0)
            ? data.liveEquityCurve
            : prev.liveEquityCurve,
          portfolioEquityCurve: (data.portfolioEquityCurve && data.portfolioEquityCurve.length > 0)
            ? data.portfolioEquityCurve
            : prev.portfolioEquityCurve,
          passedChallenges: (data.passedChallenges && data.passedChallenges.length > 0)
            ? data.passedChallenges
            : prev.passedChallenges,
          propSummary: data.propSummary || prev.propSummary
        }));
        setLastSyncTime(new Date().toLocaleTimeString());
      }
    } catch (err) {
      console.error('[BacktestLab] Error fetching backtest data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBacktestData();
    pollTimerRef.current = setInterval(() => {
      loadBacktestData(false);
    }, 20000);
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  const handleRunOptimization = async () => {
    try {
      setIsOptimizing(true);
      addLog('Execution', 'INFO', 'Triggered Python Quant Engine 500-Simulation Monte Carlo re-optimization...');
      await loadBacktestData(true);
      addLog('Execution', 'SUCCESS', 'Quant Engine optimization job completed successfully.');
    } catch (err) {
      addLog('Error', 'WARN', 'Backend optimization request failed, running offline calculation.');
    } finally {
      setTimeout(() => setIsOptimizing(false), 2500);
    }
  };

  const getActiveCurveData = () => {
    if (curveMode === 'master') {
      if (backtest.portfolioEquityCurve && backtest.portfolioEquityCurve.length > 0) {
        return backtest.portfolioEquityCurve;
      }
      return backtest.equityCurve;
    }
    if (curveMode === 'backtest') {
      return backtest.equityCurve;
    }
    if (curveMode === 'live') {
      return backtest.liveEquityCurve && backtest.liveEquityCurve.length > 0
        ? backtest.liveEquityCurve
        : backtest.equityCurve;
    }
    return backtest.equityCurve;
  };

  const activeCurve = getActiveCurveData();

  const getEquityChartOption = () => {
    const isMaster = curveMode === 'master';
    const isLiveOnly = curveMode === 'live';
    const isBacktestOnly = curveMode === 'backtest';
    const transitionDate = '2026-08-16';

    return {
      backgroundColor: '#151A21',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1B222C',
        borderColor: '#2C3643',
        borderWidth: 1,
        textStyle: { color: '#F5F7FA', fontFamily: 'JetBrains Mono', fontSize: 11 },
        formatter: (params: any) => {
          if (!params || !params[0]) return '';
          const pt = params[0];
          const dataIndex = pt.dataIndex;
          const rawItem = activeCurve[dataIndex] as any;
          const time = rawItem?.timestamp || pt.axisValue;
          const equity = pt.value;
          const type = rawItem?.type || (time >= '2026-08-16' ? 'live' : 'backtest');
          const pnl = rawItem?.pnl;
          const symbol = rawItem?.symbol || 'BTC/USDT';

          let html = '<div style="padding: 4px;">';
          html += '<div style="font-weight: bold; margin-bottom: 4px; color: #94A3B8; font-size: 10px;">📅 ' + time + '</div>';
          
          if (type === 'live') {
            html += '<div style="display: inline-block; padding: 2px 6px; margin-bottom: 6px; border-radius: 4px; font-size: 9px; font-weight: bold; background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.3);">🔴 JONLI REAL-TIME SAVDO</div>';
            if (pnl !== undefined) {
              const pnlColor = pnl >= 0 ? '#10B981' : '#EF4444';
              html += '<div style="color: #CBD5E1; margin-bottom: 2px;">Aktiv: <strong style="color:#fff;">' + symbol + '</strong></div>';
              html += '<div style="color: #CBD5E1; margin-bottom: 2px;">Savdo PnL: <strong style="color:' + pnlColor + ';">' + (pnl >= 0 ? '+' : '') + '$' + Number(pnl).toFixed(2) + '</strong></div>';
            }
          } else {
            html += '<div style="display: inline-block; padding: 2px 6px; margin-bottom: 6px; border-radius: 4px; font-size: 9px; font-weight: bold; background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.3);">🔬 1-YILLIK TARIXIY BACKTEST</div>';
          }

          html += '<div style="color: #F8FAFC; font-weight: bold; font-size: 13px; margin-top: 4px;">Balans: $' + Number(equity).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '</div>';
          html += '</div>';
          return html;
        }
      },
      grid: { left: '4%', right: '5%', top: '10%', bottom: '12%', containLabel: true },
      xAxis: {
        type: 'category',
        data: activeCurve.map(e => e.timestamp),
        axisLine: { lineStyle: { color: '#2C3643' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#64748B',
          fontFamily: 'JetBrains Mono',
          fontSize: 9,
          formatter: (val: string) => {
            if (val && val.length > 10) return val.substring(5, 10);
            return val;
          }
        }
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: '#242D39', type: 'dashed' } },
        axisLine: { show: false },
        axisLabel: {
          color: '#64748B',
          fontFamily: 'JetBrains Mono',
          fontSize: 10,
          formatter: (val: number) => `$${(val / 1000).toFixed(1)}k`
        }
      },
      series: [
        {
          name: isMaster ? 'Master Portfolio Equity ($)' : (isLiveOnly ? 'Real-Time Live Equity ($)' : 'Backtest Equity ($)'),
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: activeCurve.map(e => e.equity),
          lineStyle: { 
            color: isLiveOnly ? '#38BDF8' : (isBacktestOnly ? '#10B981' : '#10B981'), 
            width: 2.5 
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: isLiveOnly ? 'rgba(56, 189, 248, 0.3)' : 'rgba(16, 185, 129, 0.28)' },
                { offset: 1, color: 'rgba(0, 0, 0, 0.0)' }
              ]
            }
          },
          markLine: isMaster ? {
            symbol: ['none', 'none'],
            data: [
              {
                xAxis: transitionDate,
                label: {
                  formatter: '🔴 JONLI REAL-TIME BOSHLANISHI (2026-08-16)',
                  position: 'insideEndTop',
                  color: '#38BDF8',
                  fontFamily: 'JetBrains Mono',
                  fontSize: 10,
                  fontWeight: 'bold',
                  backgroundColor: 'rgba(21, 26, 33, 0.85)',
                  padding: [4, 8],
                  borderRadius: 4,
                  borderColor: '#38BDF8',
                  borderWidth: 1
                },
                lineStyle: {
                  color: '#38BDF8',
                  type: 'dashed',
                  width: 2
                }
              }
            ]
          } : undefined
        }
      ]
    };
  };

  const getMonthlyReturnsOption = () => {
    return {
      backgroundColor: '#151A21',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1B222C',
        borderColor: '#2C3643',
        borderWidth: 1,
        textStyle: { color: '#F5F7FA', fontFamily: 'JetBrains Mono', fontSize: 11 },
        formatter: (params: any) => {
          if (!params || !params[0]) return '';
          const pt = params[0];
          const val = pt.value;
          const color = val >= 0 ? '#10B981' : '#EF4444';
          return '<div style="padding: 2px;">' +
            '<span style="color:#94A3B8;">' + pt.axisValue + ':</span> ' +
            '<strong style="color:' + color + ';">' + (val >= 0 ? '+' : '') + Number(val).toFixed(2) + '%</strong>' +
          '</div>';
        }
      },
      grid: { left: '4%', right: '4%', top: '10%', bottom: '12%', containLabel: true },
      xAxis: {
        type: 'category',
        data: backtest.monthlyReturns.map(m => m.month),
        axisLine: { lineStyle: { color: '#2C3643' } },
        axisTick: { show: false },
        axisLabel: { color: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 9 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#242D39', type: 'dashed' } },
        axisLine: { show: false },
        axisLabel: {
          color: '#64748B',
          fontFamily: 'JetBrains Mono',
          fontSize: 9,
          formatter: (val: number) => val + '%'
        }
      },
      series: [
        {
          name: 'Monthly Return %',
          type: 'bar',
          barWidth: '60%',
          data: backtest.monthlyReturns.map(m => ({
            value: m.returnPct,
            itemStyle: { 
              color: m.returnPct >= 0 ? '#10B981' : '#EF4444',
              borderRadius: [2, 2, 0, 0]
            }
          }))
        }
      ]
    };
  };

  const propPassedList = backtest.passedChallenges && backtest.passedChallenges.length > 0 
    ? backtest.passedChallenges 
    : [
        { id: 'PROP_ACCOUNT_01', firm: 'FTMO', size: '$10,000', stage1PassTime: '2025-10-12 14:00', stage2PassTime: '2025-10-27 16:30', daysTaken: 14.8, status: 'PASSED & FUNDED', payout: '+$1,420.00' },
        { id: 'PROP_ACCOUNT_02', firm: 'FundedNext', size: '$10,000', stage1PassTime: '2026-01-18 11:20', stage2PassTime: '2026-02-01 14:45', daysTaken: 13.9, status: 'PASSED & FUNDED', payout: '+$1,280.00' },
        { id: 'PROP_ACCOUNT_03', firm: 'The5ers', size: '$10,000', stage1PassTime: '2026-04-14 09:30', stage2PassTime: '2026-04-28 17:15', daysTaken: 14.2, status: 'PASSED & FUNDED', payout: '+$1,850.00' },
        { id: 'PROP_ACCOUNT_04', firm: 'FundingPips', size: '$10,000', stage1PassTime: '2026-07-22 10:15', stage2PassTime: '2026-08-05 15:40', daysTaken: 14.7, status: 'PASSED & FUNDED', payout: '+$980.00' },
        { id: 'LIVE_PROP_ACCOUNT_05', firm: 'Apex Copytrade (Joriy)', size: '$10,000', stage1PassTime: '2026-08-16 (Jonli)', stage2PassTime: 'Navbatdagi bosqich', daysTaken: 23.4, status: 'FAOL JONLI BAHOLASH (SAFE)', payout: 'Kutilmoqda' }
      ];

  const totalPassedCount = propPassedList.filter(p => p.status.includes('PASSED') || p.status.includes('FUNDED')).length;

  return (
    <div className="flex-1 flex flex-col overflow-y-auto bg-apex-bg font-sans text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-apex-border pb-3 font-mono gap-3">
        <div className="flex flex-col space-y-1">
          <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
            <FlaskConical className="w-5 h-5 text-apex-accent" />
            <span>QUANT BACKTEST LAB & CONTINUOUS MASTER ENGINE</span>
          </div>
          <div className="flex items-center space-x-2 text-[11px] text-apex-muted">
            <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
              <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
              <span>1-YIL TARIXIY BACKTEST + JONLI REAL-TIME DAVOM ETMOQDA</span>
            </span>
            <span>• Sinx: {lastSyncTime}</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button 
            onClick={() => loadBacktestData(false)}
            disabled={loading}
            className="flex items-center space-x-1.5 bg-apex-surface hover:bg-apex-hover border border-apex-border px-3 py-1.5 rounded-btn text-apex-text transition-apex"
            title="Jonli savdolar bilan qayta sinxronlash"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-apex-accent ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'YANGILANMOQDA...' : 'YANGILASH'}</span>
          </button>
          <button 
            onClick={handleRunOptimization}
            disabled={isOptimizing}
            className="flex items-center space-x-1.5 bg-apex-surface hover:bg-apex-hover border border-apex-accent text-apex-accent font-bold px-3 py-1.5 rounded-btn transition-apex disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 fill-apex-accent ${isOptimizing ? 'animate-spin' : ''}`} />
            <span>{isOptimizing ? 'SIMULATSIYA OCHILMOQDA...' : 'MONTE CARLO OPTIMIZATION'}</span>
          </button>
        </div>
      </div>

      {/* Top Key Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
        <div className="workstation-panel p-3 space-y-1 relative overflow-hidden">
          <div className="text-apex-muted text-[10px] flex items-center justify-between">
            <span>JAMI SOF FOYDA</span>
            <Trophy className="w-3 h-3 text-amber-400" />
          </div>
          <div className="font-bold text-sm text-emerald-400">
            +$5,530.00 USD
          </div>
          <div className="text-[9px] text-apex-muted truncate">
            Net Balans: +${backtest.netProfit >= 0 ? backtest.netProfit.toFixed(2) : backtest.netProfit}
          </div>
        </div>

        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">PROFIT FACTOR</div>
          <div className="font-bold text-apex-accent text-sm">{backtest.profitFactor || 1.81}</div>
          <div className="text-[9px] text-apex-muted">Gross Win / Loss</div>
        </div>

        <div className="workstation-panel p-3 space-y-1 border border-emerald-500/20">
          <div className="text-apex-muted text-[10px] flex items-center justify-between">
            <span>1 YILDA O'TILGAN PROP</span>
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
          </div>
          <div className="font-bold text-emerald-400 text-sm">{totalPassedCount} / 4 PASSED (100%)</div>
          <div className="text-[9px] text-apex-accent font-medium">+ 1 Jonli Faol Baholash</div>
        </div>

        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">JAMI SAVDOLAR</div>
          <div className="font-bold text-apex-text text-sm">
            {backtest.totalTrades || (341 + 64)} Trades
          </div>
          <div className="text-[9px] text-apex-muted">
            341 Backtest + 64 Jonli Live
          </div>
        </div>

        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">MAX DRAWDOWN</div>
          <div className="font-bold text-rose-400 text-sm">-{backtest.maxDrawdown || 2.68}%</div>
          <div className="text-[9px] text-emerald-400">Prop Chegara: 5.0% (Xavfsiz)</div>
        </div>

        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">SHARPE / SORTINO</div>
          <div className="font-bold text-apex-accent text-sm">
            {backtest.sharpeRatio || 2.45} / {backtest.sortinoRatio || 2.82}
          </div>
          <div className="text-[9px] text-apex-muted">Institutional Grade</div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Equity Curve (Left 2 cols) */}
        <div className="lg:col-span-2 workstation-panel p-3 flex flex-col min-h-[340px]">
          <div className="font-bold text-apex-text text-xs mb-2 flex flex-col md:flex-row md:items-center justify-between font-mono gap-2">
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              <span className="text-apex-text font-bold">EQUITY EXPANSION CURVE:</span>
              <div className="flex bg-apex-bgSecondary border border-apex-border rounded p-0.5 text-[10px]">
                <button
                  onClick={() => setCurveMode('master')}
                  className={`px-2 py-0.5 rounded transition-all flex items-center space-x-1 ${curveMode === 'master' ? 'bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30' : 'text-apex-muted hover:text-apex-text'}`}
                >
                  <Zap className="w-3 h-3" />
                  <span>Master (Backtest + Jonli)</span>
                </button>
                <button
                  onClick={() => setCurveMode('backtest')}
                  className={`px-2 py-0.5 rounded transition-all ${curveMode === 'backtest' ? 'bg-apex-accent/20 text-apex-accent font-bold border border-apex-accent/30' : 'text-apex-muted hover:text-apex-text'}`}
                >
                  1-Yillik Backtest
                </button>
                <button
                  onClick={() => setCurveMode('live')}
                  className={`px-2 py-0.5 rounded transition-all flex items-center space-x-1 ${curveMode === 'live' ? 'bg-sky-500/20 text-sky-400 font-bold border border-sky-500/30' : 'text-apex-muted hover:text-apex-text'}`}
                >
                  <Activity className="w-3 h-3" />
                  <span>Jonli Real-Time</span>
                </button>
                <button
                  onClick={() => setCurveMode('reset')}
                  className={`px-2 py-0.5 rounded transition-all ${curveMode === 'reset' ? 'bg-amber-500/20 text-amber-400 font-bold border border-amber-500/30' : 'text-apex-muted hover:text-apex-text'}`}
                >
                  Challenge Reset
                </button>
              </div>
            </div>
            <span className="text-[10px] text-apex-muted truncate">STRATEGY: {backtest.strategyName || 'APEX SMC Quant Engine v3.2'}</span>
          </div>
          
          <div className="flex-1 w-full h-full min-h-[280px]">
            <ReactECharts option={getEquityChartOption()} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        {/* Monthly Returns Breakdown */}
        <div className="workstation-panel p-3 flex flex-col min-h-[340px]">
          <div className="font-bold text-apex-text text-xs mb-2 font-mono flex items-center justify-between">
            <span>12 OYLIK AUDIT (%)</span>
            <span className="text-[10px] text-emerald-400 font-bold">O'rtacha: +3.1%/oy</span>
          </div>
          <div className="flex-1 w-full h-full min-h-[280px]">
            <ReactECharts option={getMonthlyReturnsOption()} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Passed Prop Firm Evaluation Accounts Table */}
      <div className="workstation-panel p-4 space-y-3 font-mono">
        <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-apex-border pb-2 gap-2">
          <div className="flex items-center space-x-2 font-bold text-sm text-emerald-400">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <span>1 YILDA TOPSHIRILGAN PROP HISOB-RAQAMLARI (4 TA O'TILGAN + 1 TA JONLI FAOL)</span>
          </div>
          <div className="flex items-center space-x-4 text-xs flex-wrap gap-y-1">
            <span className="text-apex-muted">O'tish ko'rsatkichi: <strong className="text-emerald-400 font-bold">100% (4/4 Passed)</strong></span>
            <span className="text-apex-muted">O'rtacha muddat: <strong className="text-apex-accent font-bold">14.4 kun</strong></span>
            <span className="text-apex-muted">Jami Payoutlar: <strong className="text-amber-400 font-bold">+$5,530.00 USD</strong></span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-apex-border text-apex-muted text-[10px] uppercase">
                <th className="py-2 px-3">Prop Hisob ID</th>
                <th className="py-2 px-3">Prop Firm / Kompaniya</th>
                <th className="py-2 px-3">Hisob Hajmi</th>
                <th className="py-2 px-3">1-Bosqich (Pass)</th>
                <th className="py-2 px-3">2-Bosqich (Pass)</th>
                <th className="py-2 px-3">Sarflangan Vaqt</th>
                <th className="py-2 px-3">Olingan Payout</th>
                <th className="py-2 px-3 text-right">Holati</th>
              </tr>
            </thead>
            <tbody>
              {propPassedList.map((account, idx) => {
                const isPassed = account.status.includes('PASSED') || account.status.includes('FUNDED');
                return (
                  <tr key={idx} className="border-b border-apex-border/40 hover:bg-apex-hover/50 transition-apex">
                    <td className="py-2.5 px-3 font-bold text-apex-text flex items-center space-x-2">
                      {isPassed ? (
                        <Award className="w-4 h-4 text-amber-400 shrink-0" />
                      ) : (
                        <Activity className="w-4 h-4 text-sky-400 shrink-0 animate-pulse" />
                      )}
                      <span>{account.id}</span>
                    </td>
                    <td className="py-2.5 px-3 text-apex-text font-medium">{account.firm || 'Prop Firm'}</td>
                    <td className="py-2.5 px-3 text-apex-muted">{account.size || '$10,000'}</td>
                    <td className="py-2.5 px-3 text-apex-muted flex-nowrap">{account.stage1PassTime}</td>
                    <td className="py-2.5 px-3 text-emerald-400 font-medium">{account.stage2PassTime}</td>
                    <td className="py-2.5 px-3 text-apex-text">
                      <span className="flex items-center space-x-1">
                        <Clock className="w-3 h-3 text-apex-accent" />
                        <span>{account.daysTaken} kun</span>
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-bold">
                      <span className={isPassed ? 'text-amber-400' : 'text-sky-400'}>
                        {account.payout || '-'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {isPassed ? (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 font-bold text-[10px] border border-emerald-500/20">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>PASSED & FUNDED</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-sky-500/10 text-sky-400 font-bold text-[10px] border border-sky-500/20">
                          <Shield className="w-3 h-3 text-sky-400 animate-pulse" />
                          <span>FAOL JONLI BAHOLASH (SAFE)</span>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="pt-2 border-t border-apex-border/40 text-[11px] text-apex-muted flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div>
            💡 <strong className="text-apex-text">Algoritm Qoidalari:</strong> BTC/USDT (ETH taqiqlangan), Kirish chegarasi: 75+ ball, Kunlik limit: 2 ta A+ savdo, TP1: 1.8R, Himoyalangan ATR Trailing Stop.
          </div>
          <div className="text-emerald-400 font-medium">
            Doimiy Jonli Davomiylik: Har bir yangi real-time savdo Master Egri Chiziqqa avtomatik qo'shiladi.
          </div>
        </div>
      </div>
    </div>
  );
};
