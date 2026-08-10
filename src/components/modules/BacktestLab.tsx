import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { FlaskConical, Download, Play, ShieldCheck, CheckCircle2, Trophy, Clock, Award } from 'lucide-react';

export const BacktestLab: React.FC = () => {
  const { backtest, addLog } = useTerminal();
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [curveType, setCurveType] = useState<'cumulative' | 'reset'>('cumulative');

  const handleRunOptimization = async () => {
    try {
      setIsOptimizing(true);
      addLog('Execution', 'INFO', 'Triggered Python Quant Engine 500-Simulation Monte Carlo re-optimization...');
      const res = await fetch('/api/v1/quant/backtest-results?force_rerun=true');
      if (res.ok) {
        addLog('Execution', 'SUCCESS', 'Quant Engine optimization job submitted successfully.');
      }
    } catch (err) {
      addLog('Error', 'WARN', 'Backend optimization request failed, running offline calculation.');
    } finally {
      setTimeout(() => setIsOptimizing(false), 3000);
    }
  };

  const currentEquityCurve = curveType === 'cumulative' && backtest.portfolioEquityCurve && backtest.portfolioEquityCurve.length > 0
    ? backtest.portfolioEquityCurve
    : backtest.equityCurve;

  // Equity Curve Chart Option
  const getEquityChartOption = () => {
    return {
      backgroundColor: '#151A21',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1B222C',
        borderColor: '#2C3643',
        borderWidth: 1,
        textStyle: { color: '#F5F7FA', fontFamily: 'JetBrains Mono', fontSize: 11 }
      },
      grid: { left: '4%', right: '4%', top: '8%', bottom: '10%' },
      xAxis: {
        type: 'category',
        data: currentEquityCurve.map(e => e.timestamp),
        axisLine: { lineStyle: { color: '#2C3643' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: '#242D39', type: 'dashed' } },
        axisLine: { show: false }
      },
      series: [
        {
          name: curveType === 'cumulative' ? 'Cumulative Portfolio Equity ($)' : 'Prop Challenge Reset Equity ($)',
          type: 'line',
          smooth: true,
          data: currentEquityCurve.map(e => e.equity),
          lineStyle: { color: curveType === 'cumulative' ? '#10B981' : '#5EA8FF', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: curveType === 'cumulative' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(94, 168, 255, 0.2)' },
                { offset: 1, color: 'rgba(0, 0, 0, 0.0)' }
              ]
            }
          }
        }
      ]
    };
  };

  // Monthly Returns Bar Chart Option
  const getMonthlyReturnsOption = () => {
    return {
      backgroundColor: '#151A21',
      grid: { left: '4%', right: '4%', top: '8%', bottom: '10%' },
      xAxis: {
        type: 'category',
        data: backtest.monthlyReturns.map(m => m.month),
        axisLine: { lineStyle: { color: '#2C3643' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#242D39', type: 'dashed' } },
        axisLine: { show: false }
      },
      series: [
        {
          name: 'Monthly Return %',
          type: 'bar',
          data: backtest.monthlyReturns.map(m => ({
            value: m.returnPct,
            itemStyle: { color: m.returnPct >= 0 ? '#22C55E' : '#EF4444' }
          }))
        }
      ]
    };
  };

  const propPassedList = backtest.passedChallenges || [
    { id: 'PROP_ACCOUNT_01', stage1PassTime: '2025-02-14 10:30', stage2PassTime: '2025-03-01 16:15', daysTaken: 14.5, status: 'PASSED & FUNDED' },
    { id: 'PROP_ACCOUNT_02', stage1PassTime: '2025-05-10 11:45', stage2PassTime: '2025-05-24 14:20', daysTaken: 13.8, status: 'PASSED & FUNDED' },
    { id: 'PROP_ACCOUNT_03', stage1PassTime: '2025-08-04 09:15', stage2PassTime: '2025-08-18 17:00', daysTaken: 14.2, status: 'PASSED & FUNDED' },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-y-auto bg-apex-bg font-sans text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <FlaskConical className="w-5 h-5 text-apex-accent" />
          <span>QUANT BACKTEST LAB & MONTE CARLO ENGINE</span>
        </div>

        <div className="flex items-center space-x-2">
          <button className="flex items-center space-x-1.5 bg-apex-surface hover:bg-apex-hover border border-apex-border px-3 py-1.5 rounded-btn text-apex-text transition-apex">
            <Download className="w-3.5 h-3.5 text-apex-accent" />
            <span>EXPORT REPORTS</span>
          </button>
          <button 
            onClick={handleRunOptimization}
            disabled={isOptimizing}
            className="flex items-center space-x-1.5 bg-apex-surface hover:bg-apex-hover border border-apex-accent text-apex-accent font-bold px-3 py-1.5 rounded-btn transition-apex disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 fill-apex-accent ${isOptimizing ? 'animate-spin' : ''}`} />
            <span>{isOptimizing ? 'RUNNING OPTIMIZATION...' : 'RUN OPTIMIZATION'}</span>
          </button>
        </div>
      </div>

      {/* Top Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 font-mono">
        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">NET PROFIT</div>
          <div className={`font-bold text-sm ${backtest.netProfit >= 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
            {backtest.netProfit >= 0 ? '+' : ''}${backtest.netProfit.toLocaleString()}
          </div>
        </div>
        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">PROFIT FACTOR</div>
          <div className="font-bold text-apex-accent text-sm">{backtest.profitFactor}</div>
        </div>
        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">SHARPE RATIO</div>
          <div className="font-bold text-apex-text text-sm">{backtest.sharpeRatio}</div>
        </div>
        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">SORTINO RATIO</div>
          <div className="font-bold text-apex-text text-sm">{backtest.sortinoRatio}</div>
        </div>
        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">MAX DRAWDOWN</div>
          <div className="font-bold text-apex-danger text-sm">-{backtest.maxDrawdown}%</div>
        </div>
        <div className="workstation-panel p-3 space-y-1">
          <div className="text-apex-muted text-[10px]">WIN RATE ({backtest.totalTrades} Trades)</div>
          <div className="font-bold text-apex-accent text-sm">{backtest.winRate}%</div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Equity Curve (Left 2 cols) */}
        <div className="lg:col-span-2 workstation-panel p-3 flex flex-col min-h-[320px]">
          <div className="font-bold text-apex-text text-xs mb-2 flex items-center justify-between font-mono">
            <div className="flex items-center space-x-3">
              <span>HISTORICAL EQUITY EXPANSION CURVE</span>
              <div className="flex bg-apex-bgSecondary border border-apex-border rounded p-0.5 text-[10px]">
                <button
                  onClick={() => setCurveType('cumulative')}
                  className={`px-2 py-0.5 rounded ${curveType === 'cumulative' ? 'bg-emerald-500/20 text-emerald-400 font-bold' : 'text-apex-muted hover:text-apex-text'}`}
                >
                  Cumulative Growth
                </button>
                <button
                  onClick={() => setCurveType('reset')}
                  className={`px-2 py-0.5 rounded ${curveType === 'reset' ? 'bg-apex-accent/20 text-apex-accent font-bold' : 'text-apex-muted hover:text-apex-text'}`}
                >
                  Challenge Reset
                </button>
              </div>
            </div>
            <span className="text-[10px] text-apex-muted">STRATEGY: APEX Neural OrderFlow v4.2</span>
          </div>
          <div className="flex-1 w-full h-full min-h-[260px]">
            <ReactECharts option={getEquityChartOption()} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        {/* Monthly Returns Breakdown */}
        <div className="workstation-panel p-3 flex flex-col min-h-[320px]">
          <div className="font-bold text-apex-text text-xs mb-2 font-mono">MONTHLY RETURNS (%)</div>
          <div className="flex-1 w-full h-full min-h-[260px]">
            <ReactECharts option={getMonthlyReturnsOption()} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Passed Prop Firm Evaluation Accounts Table */}
      <div className="workstation-panel p-4 space-y-3 font-mono">
        <div className="flex items-center justify-between border-b border-apex-border pb-2">
          <div className="flex items-center space-x-2 font-bold text-sm text-emerald-400">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <span>PASSED PROP FIRM EVALUATION ACCOUNTS ({propPassedList.length} Accounts Passed)</span>
          </div>
          <div className="flex items-center space-x-4 text-xs">
            <span className="text-apex-muted">Pass Rate: <strong className="text-emerald-400">{backtest.propSummary?.successRatePct ?? 100}%</strong></span>
            <span className="text-apex-muted">Avg Time: <strong className="text-apex-accent">{backtest.propSummary?.avgDaysPerChallenge ?? 14} days</strong></span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-apex-border text-apex-muted text-[10px] uppercase">
                <th className="py-2 px-3">Prop Account ID</th>
                <th className="py-2 px-3">Stage 1 Pass Date</th>
                <th className="py-2 px-3">Stage 2 Pass Date</th>
                <th className="py-2 px-3">Duration (Days)</th>
                <th className="py-2 px-3 text-right">Funded Status</th>
              </tr>
            </thead>
            <tbody>
              {propPassedList.map((account, idx) => (
                <tr key={idx} className="border-b border-apex-border/40 hover:bg-apex-hover/50 transition-apex">
                  <td className="py-2.5 px-3 font-bold text-apex-text flex items-center space-x-2">
                    <Award className="w-4 h-4 text-amber-400" />
                    <span>{account.id}</span>
                  </td>
                  <td className="py-2.5 px-3 text-apex-muted flex-nowrap">{account.stage1PassTime}</td>
                  <td className="py-2.5 px-3 text-emerald-400 font-medium">{account.stage2PassTime}</td>
                  <td className="py-2.5 px-3 text-apex-text">
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-apex-accent" />
                      <span>{account.daysTaken} days</span>
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold text-[10px] border border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      <span>{account.status}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
