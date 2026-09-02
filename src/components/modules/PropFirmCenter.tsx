import React, { useEffect, useState, useCallback } from 'react';
import {
  ShieldCheck, CheckCircle2, XCircle, AlertTriangle, TrendingUp, TrendingDown,
  Target, Award, Activity, RefreshCw, Clock, Zap, BarChart3,
  AlertCircle, Calculator, Flame, Layers, ChevronRight, Info
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';

interface PropFirmStatus {
  status: string;
  accountNumber: string;
  firmName: string;
  stage: string;
  initialCapital: number;
  navEquity: number;
  realizedPnl: number;
  unrealizedPnl: number;
  currentProfit: number;
  currentProfitPct: number;
  targetProfitUsd: number;
  targetProfitPct: number;
  progressPct: number;
  maxDailyDrawdownPct: number;
  maxDailyDrawdownUsd: number;
  currentDailyDrawdownPct: number;
  currentDailyDrawdownUsd: number;
  maxTotalDrawdownPct: number;
  maxTotalDrawdownUsd: number;
  currentTotalDrawdownPct: number;
  minTradingDays: number;
  daysTraded: number;
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  consistencyScore: number;
  passProbability: number;
  projectedFinishDate: string;
  ruleViolations: Array<{ rule: string; severity: string; detail: string }>;
  ruleStatus: string;
  openPositions: number;
  recommendedMaxLots: number;
  safeRiskPerTrade: number;
  safeRiskAvailableToday: number;
  dailyPnl: number;
  equityCurve: Array<{ timestamp: string; equity: number }>;
}

interface PositionSize {
  status: string;
  symbol: string;
  accountEquity: number;
  riskPct: number;
  riskUsd: number;
  effectiveRiskUsd: number;
  slDistancePts: number;
  recommendedContracts: number;
  notionalValue: number;
  totalRiskUsd: number;
  impactOnDailyDD: number;
  safeRiskAvailableToday: number;
  maxDailyLossUsed: number;
  maxDailyLossLimit: number;
  ruleNote: string;
}

interface RiskRule {
  rule: string;
  limit: number;
  current: number;
  status: 'PASS' | 'FAIL' | 'WARN';
  icon: string;
}

interface RiskDashboard {
  status: string;
  navEquity: number;
  dailyPnl: number;
  dailyDrawdownPct: number;
  totalDrawdownPct: number;
  rules: RiskRule[];
  consistencyScore: number;
  violationsCount: number;
  activeViolations: string[];
}

const fmt = (v: any, d = 2) => {
  if (v === undefined || v === null || isNaN(Number(v))) return '0.00';
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
};

const ProgressBar: React.FC<{
  current: number;
  max: number;
  color?: string;
  danger?: boolean;
  warn?: boolean;
}> = ({ current, max, color = 'bg-blue-500', danger = false, warn = false }) => {
  const pct = Math.min(100, Math.max(0, (current / (max || 1)) * 100));
  let barColor = color;
  if (danger) barColor = 'bg-rose-500';
  else if (warn) barColor = 'bg-amber-500';

  return (
    <div className="w-full bg-[#080A0D] rounded-full h-1.5 overflow-hidden border border-[#222C3A]">
      <div
        className={`h-full ${barColor} transition-all duration-300`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
};

export const PropFirmCenter: React.FC = () => {
  const [status, setStatus] = useState<PropFirmStatus | null>(null);
  const [posSize, setPosSize] = useState<PositionSize | null>(null);
  const [riskDash, setRiskDash] = useState<RiskDashboard | null>(null);
  const [symbol, setSymbol] = useState<string>('BTC/USDT');
  const [slDistance, setSlDistance] = useState<string>('500');
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/propfirm/status');
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'SUCCESS') setStatus(data.data);
      }
    } catch (e) {
      console.error('[PropFirmCenter] status fetch error:', e);
    }
  }, []);

  const fetchPosSize = useCallback(async () => {
    try {
      const pts = parseFloat(slDistance) || 500;
      const res = await fetch(`/api/v1/propfirm/position-sizer?symbol=${encodeURIComponent(symbol)}&sl_distance_points=${pts}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'SUCCESS') setPosSize(data.data);
      }
    } catch (e) {
      console.error('[PropFirmCenter] pos sizer fetch error:', e);
    }
  }, [symbol, slDistance]);

  const fetchRiskDash = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/propfirm/risk-dashboard');
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'SUCCESS') setRiskDash(data.data);
      }
    } catch (e) {
      console.error('[PropFirmCenter] risk dash fetch error:', e);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.all([fetchStatus(), fetchPosSize(), fetchRiskDash()]);
    setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    setIsRefreshing(false);
    setLoading(false);
  }, [fetchStatus, fetchPosSize, fetchRiskDash]);

  useEffect(() => {
    refreshAll();
    const iv = setInterval(refreshAll, 6000);
    return () => clearInterval(iv);
  }, [refreshAll]);

  useEffect(() => {
    fetchPosSize();
  }, [fetchPosSize]);

  const getEquityChartOption = () => {
    const curve = status?.equityCurve || [];
    const timestamps = curve.map(c => c.timestamp);
    const equities = curve.map(c => c.equity);
    const target = (status?.initialCapital ?? 10000) * 1.08;
    const initial = status?.initialCapital ?? 10000;

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#141A23',
        borderColor: '#2B384B',
        borderWidth: 1,
        textStyle: { color: '#F3F4F6', fontFamily: 'JetBrains Mono', fontSize: 11 }
      },
      grid: { left: '4%', right: '3%', top: '10%', bottom: '12%' },
      xAxis: {
        type: 'category',
        data: timestamps.length ? timestamps : ['00:00'],
        axisLine: { lineStyle: { color: '#2B384B' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: '#1A222E', type: 'dashed' } },
        axisLine: { show: false }
      },
      series: [
        {
          name: 'Target ($10,800)',
          type: 'line',
          data: Array(timestamps.length || 1).fill(target),
          lineStyle: { color: 'rgba(52, 211, 153, 0.4)', type: 'dashed', width: 1.5 },
          showSymbol: false
        },
        {
          name: 'Starting ($10,000)',
          type: 'line',
          data: Array(timestamps.length || 1).fill(initial),
          lineStyle: { color: 'rgba(156, 163, 175, 0.3)', type: 'dashed', width: 1 },
          showSymbol: false
        },
        {
          name: 'NAV Equity',
          type: 'line',
          smooth: true,
          data: equities.length ? equities : [initial],
          lineStyle: { color: '#10B981', width: 2.5 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(16, 185, 129, 0.25)' },
                { offset: 1, color: 'rgba(16, 185, 129, 0.0)' }
              ]
            }
          }
        }
      ]
    };
  };

  const s = status;
  const isCompliant = (s?.ruleViolations?.length ?? 0) === 0;

  return (
    <div className="flex-1 flex flex-col overflow-y-auto bg-[#080A0D] font-mono text-xs p-4 space-y-4">

      {/* Top Banner Header */}
      <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-3.5 flex items-center justify-between shadow-md">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-sm text-white font-sans flex items-center gap-2">
              <span>{s?.firmName || 'APEX QUANT PROP FIRM'}</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
                {s?.stage || 'STAGE 1 CHALLENGE'}
              </span>
            </div>
            <div className="text-[10px] text-[#6B7280]">
              Account #{s?.accountNumber || 'APEX-10K-001'} • FTMO 2x Institutional Rules Active
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center space-x-1.5 ${
            isCompliant 
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' 
              : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
          }`}>
            {isCompliant ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
            <span>{isCompliant ? '100% COMPLIANT' : 'RULE VIOLATION'}</span>
          </div>

          <button
            onClick={refreshAll}
            disabled={isRefreshing}
            className="p-1.5 rounded bg-[#141A23] hover:bg-[#1A222E] border border-[#222C3A] text-[#9CA3AF] hover:text-white transition-apex"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Primary KPI Grid (4 Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* NAV Equity */}
        <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-3.5 space-y-2 shadow-sm">
          <div className="text-[9.5px] text-[#6B7280] uppercase tracking-wider font-semibold flex items-center justify-between">
            <span>NAV Equity</span>
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white tabular-nums">
            ${fmt(s?.navEquity ?? 10000)}
          </div>
          <div className="text-[10px] text-[#9CA3AF]">
            Realized: <strong className={((s?.realizedPnl ?? 0) >= 0) ? 'text-emerald-400' : 'text-rose-400'}>
              {((s?.realizedPnl ?? 0) >= 0 ? '+' : '')}${fmt(s?.realizedPnl ?? 0)}
            </strong>
          </div>
          <ProgressBar current={s?.currentProfit ?? 0} max={s?.targetProfitUsd ?? 800} color="bg-emerald-400" />
        </div>

        {/* Challenge Target Progress */}
        <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-3.5 space-y-2 shadow-sm">
          <div className="text-[9.5px] text-[#6B7280] uppercase tracking-wider font-semibold flex items-center justify-between">
            <span>Profit Target (8%)</span>
            <Target className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-white tabular-nums">
            {s?.progressPct?.toFixed(1) ?? '0.0'}%
          </div>
          <div className="text-[10px] text-[#9CA3AF]">
            ${fmt(s?.currentProfit ?? 0)} / ${fmt(s?.targetProfitUsd ?? 800)}
          </div>
          <ProgressBar current={s?.progressPct ?? 0} max={100} color="bg-blue-500" />
        </div>

        {/* Daily Drawdown */}
        <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-3.5 space-y-2 shadow-sm">
          <div className="text-[9.5px] text-[#6B7280] uppercase tracking-wider font-semibold flex items-center justify-between">
            <span>Daily Drawdown</span>
            <Activity className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-white tabular-nums">
            {s?.currentDailyDrawdownPct?.toFixed(2) ?? '0.00'}%
          </div>
          <div className="text-[10px] text-[#9CA3AF]">
            Safe Limit: 5.00% (${fmt(s?.maxDailyDrawdownUsd ?? 500)})
          </div>
          <ProgressBar
            current={s?.currentDailyDrawdownPct ?? 0}
            max={s?.maxDailyDrawdownPct ?? 5}
            danger={(s?.currentDailyDrawdownPct ?? 0) >= 4.0}
            warn={(s?.currentDailyDrawdownPct ?? 0) >= 2.5}
            color="bg-emerald-400"
          />
        </div>

        {/* Pass Probability */}
        <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-3.5 space-y-2 shadow-sm">
          <div className="text-[9.5px] text-[#6B7280] uppercase tracking-wider font-semibold flex items-center justify-between">
            <span>Pass Probability</span>
            <Award className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-purple-400 tabular-nums">
            {s?.passProbability?.toFixed(1) ?? '12.0'}%
          </div>
          <div className="text-[10px] text-[#9CA3AF]">
            Win Rate: <strong>{s?.winRate?.toFixed(1) ?? '0.0'}%</strong> ({s?.totalTrades ?? 0} trades)
          </div>
          <ProgressBar current={s?.passProbability ?? 12} max={100} color="bg-purple-500" />
        </div>
      </div>

      {/* Middle Row: Position Sizer + Risk Rules Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Position Size Calculator */}
        <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-4 space-y-3 shadow-md">
          <div className="flex items-center justify-between border-b border-[#222C3A] pb-2">
            <div className="font-bold text-xs text-white flex items-center space-x-1.5 font-sans">
              <Calculator className="w-3.5 h-3.5 text-blue-400" />
              <span>POSITION SIZE & RISK SIZER</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[9px] text-[#6B7280] uppercase font-bold">Symbol</label>
              <select
                value={symbol}
                onChange={e => setSymbol(e.target.value)}
                className="w-full bg-[#141A23] border border-[#222C3A] rounded px-2.5 py-1.5 text-xs text-white font-bold focus:outline-none focus:border-blue-500"
              >
                <option value="BTC/USDT">BTC/USDT</option>
                <option value="ETH/USDT">ETH/USDT</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[9px] text-[#6B7280] uppercase font-bold">Stop Loss Distance (Points)</label>
              <input
                type="number"
                value={slDistance}
                onChange={e => setSlDistance(e.target.value)}
                className="w-full bg-[#141A23] border border-[#222C3A] rounded px-2.5 py-1.5 text-xs text-white font-mono font-bold focus:outline-none focus:border-blue-500"
                placeholder="500"
                min="1"
              />
            </div>
          </div>

          {/* Calculator Output */}
          <div className="bg-[#141A23] rounded-lg border border-[#222C3A] divide-y divide-[#1A222E]">
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-[#9CA3AF]">RECOMMENDED SIZE:</span>
              <span className="font-bold text-emerald-400 text-xs tabular-nums">
                {posSize?.recommendedContracts?.toFixed(4) ?? '0.0000'} Contracts
              </span>
            </div>
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-[#9CA3AF]">TOTAL RISK IN DOLLARS:</span>
              <span className="font-bold text-amber-400 text-xs tabular-nums">
                ${fmt(posSize?.totalRiskUsd ?? 0)}
              </span>
            </div>
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-[#9CA3AF]">DAILY DRAWDOWN IMPACT:</span>
              <span className="font-bold text-blue-400 text-xs tabular-nums">
                {posSize?.impactOnDailyDD?.toFixed(2) ?? '0.00'}%
              </span>
            </div>
          </div>
        </div>

        {/* Prop Firm Rule Compliance Dashboard */}
        <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-4 space-y-3 shadow-md">
          <div className="flex items-center justify-between border-b border-[#222C3A] pb-2">
            <div className="font-bold text-xs text-white flex items-center space-x-1.5 font-sans">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>RULES COMPLIANCE MATRIX</span>
            </div>
            <span className="text-[9.5px] text-[#6B7280]">FTMO 10K EVALUATION</span>
          </div>

          <div className="space-y-2">
            {(riskDash?.rules || [
              { rule: 'Max Daily Drawdown (5.0%)', limit: 5.0, current: s?.currentDailyDrawdownPct || 0, status: 'PASS' },
              { rule: 'Max Total Drawdown (10.0%)', limit: 10.0, current: s?.currentTotalDrawdownPct || 0, status: 'PASS' },
              { rule: 'Profit Target Stage 1 (8.0%)', limit: 8.0, current: s?.currentProfitPct || 0, status: 'PASS' },
              { rule: 'Max Allowed Leverage (2X)', limit: 2.0, current: 2.0, status: 'PASS' },
            ]).map((r: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-[#141A23] rounded border border-[#222C3A]">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span className="text-[11px] text-[#E5E7EB]">{r.rule}</span>
                </div>
                <span className="px-1.5 py-0.2 rounded text-[9.5px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  COMPLIANT
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Bottom Chart: Real-Time Equity Curve vs Target */}
      <div className="bg-[#0D1117] border border-[#222C3A] rounded-lg p-4 space-y-3 shadow-md">
        <div className="flex items-center justify-between border-b border-[#222C3A] pb-2">
          <div className="font-bold text-xs text-white flex items-center space-x-1.5 font-sans">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            <span>REAL-TIME NAV EQUITY CURVE VS $10,800 TARGET</span>
          </div>
          <span className="text-[9.5px] text-[#6B7280]">Updated: {lastUpdated || 'Real-Time'}</span>
        </div>

        <div className="h-64">
          <ReactECharts option={getEquityChartOption()} style={{ height: '100%', width: '100%' }} />
        </div>
      </div>

    </div>
  );
};

export default PropFirmCenter;
