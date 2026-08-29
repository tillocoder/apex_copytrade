import React, { useEffect, useState, useCallback } from 'react';
import {
  ShieldCheck, CheckCircle2, XCircle, AlertTriangle, TrendingUp, TrendingDown,
  Target, Award, Activity, RefreshCw, Clock, Zap, BarChart3,
  AlertCircle, Calculator, Flame, Layers, ChevronRight, Info
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';

// ─── Types ────────────────────────────────────────────────────────────────────
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
  winRate: number;
  profitFactor: number;
  consistencyScore: number;
  passProbability: number;
  projectedFinishDate: string;
  violationsCount: number;
  rules: RiskRule[];
  openPositions: number;
}

const API = 'https://apex.xrinvest.uz/api/v1';
const fmt = (v: number, d = 2) => Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

// ─── Equity Mini Chart ─────────────────────────────────────────────────────────
const EquityMiniChart: React.FC<{ curve: Array<{ timestamp: string; equity: number }>; initial: number }> = ({ curve, initial }) => {
  if (!curve || curve.length < 2) {
    return (
      <div className="flex items-center justify-center h-full text-apex-muted text-[10px]">
        Accumulating equity data...
      </div>
    );
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1B222C',
      borderColor: '#2C3643',
      borderWidth: 1,
      textStyle: { color: '#F5F7FA', fontFamily: 'JetBrains Mono', fontSize: 10 },
      formatter: (params: any) => {
        const pt = params[0];
        const diff = Number(pt.value) - initial;
        const color = diff >= 0 ? '#10B981' : '#F43F5E';
        return `<strong>${pt.name}</strong><br/>Equity: <span style="color:${color};font-weight:bold;">$${Number(pt.value).toFixed(2)}</span>`;
      }
    },
    grid: { left: '6%', right: '2%', top: '8%', bottom: '18%' },
    xAxis: {
      type: 'category',
      data: curve.map(c => c.timestamp),
      axisLine: { lineStyle: { color: '#2C3643' } },
      axisLabel: { color: '#8899A6', fontSize: 8 }
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { color: '#242D39', type: 'dashed' } },
      axisLabel: { color: '#8899A6', fontSize: 8, formatter: (v: number) => `$${v.toFixed(0)}` }
    },
    series: [{
      type: 'line',
      data: curve.map(c => Number(c.equity)),
      smooth: true,
      lineStyle: { color: '#0EA5E9', width: 2 },
      itemStyle: { color: '#0EA5E9' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(14,165,233,0.30)' },
            { offset: 1, color: 'rgba(14,165,233,0.00)' }
          ]
        }
      },
      markLine: {
        silent: true,
        data: [{ yAxis: initial, lineStyle: { color: '#8899A6', type: 'dashed', width: 1 } }],
        label: { show: true, formatter: `$${initial.toFixed(0)}`, color: '#8899A6', fontSize: 9 }
      }
    }]
  };

  return <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />;
};

// ─── Progress Bar ──────────────────────────────────────────────────────────────
const ProgressBar: React.FC<{
  current: number; max: number; color?: string; danger?: boolean; warn?: boolean; label?: string;
}> = ({ current, max, color = 'bg-emerald-400', danger = false, warn = false, label }) => {
  const pct = Math.min(100, Math.max(0, (current / Math.max(0.01, max)) * 100));
  const barColor = danger ? 'bg-rose-500' : warn ? 'bg-amber-400' : color;
  return (
    <div className="space-y-0.5">
      {label && (
        <div className="flex justify-between text-[9px] text-apex-muted">
          <span>{label}</span>
          <span className="font-bold text-apex-text">{pct.toFixed(1)}%</span>
        </div>
      )}
      <div className="w-full h-1.5 bg-apex-bg rounded-full overflow-hidden border border-apex-border/30">
        <div
          className={`${barColor} h-full rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

// ─── Main Component ────────────────────────────────────────────────────────────
export const PropFirmCenter: React.FC = () => {
  const [propStatus, setPropStatus] = useState<PropFirmStatus | null>(null);
  const [riskDash, setRiskDash] = useState<RiskDashboard | null>(null);
  const [posSize, setPosSize] = useState<PositionSize | null>(null);
  const [slDistance, setSlDistance] = useState<string>('500');
  const [symbol, setSymbol] = useState<string>('BTC/USDT');
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const [statusRes, riskRes] = await Promise.all([
        fetch(`${API}/propfirm/status`).then(r => r.json()).catch(() => null),
        fetch(`${API}/propfirm/risk-dashboard`).then(r => r.json()).catch(() => null),
      ]);
      if (statusRes) setPropStatus(statusRes);
      if (riskRes) setRiskDash(riskRes);
      setLastUpdate(new Date());
    } catch (e) {
      console.error('[PropFirmCenter] fetch error:', e);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  const calcPosSize = useCallback(async () => {
    const sl = parseFloat(slDistance) || 500;
    try {
      const res = await fetch(`${API}/propfirm/position-sizer?symbol=${encodeURIComponent(symbol)}&sl_distance_pts=${sl}`);
      const data = await res.json();
      setPosSize(data);
    } catch (e) {
      console.error('[PropFirmCenter] position sizer error:', e);
    }
  }, [slDistance, symbol]);

  useEffect(() => {
    fetchAll();
    calcPosSize();
    const interval = setInterval(fetchAll, 8000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  useEffect(() => {
    const t = setTimeout(calcPosSize, 400);
    return () => clearTimeout(t);
  }, [slDistance, symbol, calcPosSize]);

  const s = propStatus;
  const r = riskDash;

  return (
    <div className="flex-1 flex flex-col overflow-y-auto bg-apex-bg font-mono text-xs p-4 space-y-4">

      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded bg-apex-surface border border-apex-border">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="font-bold text-sm text-apex-text flex items-center space-x-2">
              <span>DEDICATED RISK WORKSPACE & PROP FIRM ENGINE</span>
              <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                r?.violationsCount === 0
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}>
                {r?.violationsCount === 0 ? 'ALL RISK RULES COMPLIANT' : `${r?.violationsCount} VIOLATION(S)`}
              </span>
            </div>
            <div className="text-[10px] text-apex-muted">
              Real-time Prop Firm challenge tracking from live SQLite equity engine
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-3 text-[10px]">
          <span className="text-apex-muted">Updated: {lastUpdate.toLocaleTimeString()}</span>
          <button
            onClick={fetchAll}
            disabled={isRefreshing}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border text-apex-text font-bold transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>REFRESH</span>
          </button>
        </div>
      </div>

      {/* ── Top KPI Row ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Remaining Daily Loss */}
        <div className="bg-apex-surface/90 border border-apex-border rounded-lg p-3.5 space-y-2 shadow-md">
          <div className="text-[9px] text-apex-muted flex items-center justify-between">
            <span>REMAINING DAILY LOSS</span>
            <AlertTriangle className="w-3 h-3 text-amber-400" />
          </div>
          <div className="text-lg font-bold text-amber-400">
            ${fmt(s?.safeRiskAvailableToday ?? 500)}
          </div>
          <div className="text-[9px] text-apex-muted">
            Limit: 5% (${fmt(s?.maxDailyDrawdownUsd ?? 500)})
          </div>
          <ProgressBar
            current={s?.currentDailyDrawdownUsd ?? 0}
            max={s?.maxDailyDrawdownUsd ?? 500}
            danger={(s?.currentDailyDrawdownPct ?? 0) >= 4.0}
            warn={(s?.currentDailyDrawdownPct ?? 0) >= 2.5}
          />
        </div>

        {/* Overall DD */}
        <div className="bg-apex-surface/90 border border-apex-border rounded-lg p-3.5 space-y-2 shadow-md">
          <div className="text-[9px] text-apex-muted flex items-center justify-between">
            <span>RUNNING OVERALL DD</span>
            <BarChart3 className="w-3 h-3 text-rose-400" />
          </div>
          <div className="text-lg font-bold text-apex-text">
            ${fmt(s?.maxTotalDrawdownUsd ?? 1000)}
          </div>
          <div className="text-[9px] text-apex-muted">
            Limit: 10% (${fmt(s?.maxTotalDrawdownUsd ?? 1000)})
          </div>
          <ProgressBar
            current={s?.currentTotalDrawdownPct ?? 0}
            max={s?.maxTotalDrawdownPct ?? 10}
            danger={(s?.currentTotalDrawdownPct ?? 0) >= 8.0}
            warn={(s?.currentTotalDrawdownPct ?? 0) >= 5.0}
          />
        </div>

        {/* Safe Risk Available */}
        <div className="bg-apex-surface/90 border border-apex-border rounded-lg p-3.5 space-y-2 shadow-md">
          <div className="text-[9px] text-apex-muted flex items-center justify-between">
            <span>SAFE RISK AVAILABLE</span>
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
          </div>
          <div className="text-lg font-bold text-cyan-400">
            ${fmt(s?.safeRiskPerTrade ?? 75)}
          </div>
          <div className="text-[9px] text-apex-muted">
            Calc: 1.15% risk per trade
          </div>
          <ProgressBar current={75} max={100} color="bg-cyan-400" />
        </div>

        {/* Recommended Max Lots */}
        <div className="bg-apex-surface/90 border border-apex-border rounded-lg p-3.5 space-y-2 shadow-md">
          <div className="text-[9px] text-apex-muted flex items-center justify-between">
            <span>RECOMMENDED MAX LOTS</span>
            <Target className="w-3 h-3 text-emerald-400" />
          </div>
          <div className="text-lg font-bold text-emerald-400">
            {s?.recommendedMaxLots?.toFixed(2) ?? '0.11'} CONTRACTS
          </div>
          <div className="text-[9px] text-apex-muted">
            Prop Law: 200
          </div>
        </div>
      </div>

      {/* ── Middle Row: Position Sizer + Rule Violations ───────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Real-Time Position Size Calculator */}
        <div className="bg-apex-surface/90 border border-apex-border rounded-lg p-4 space-y-3 shadow-lg">
          <div className="flex items-center justify-between border-b border-apex-border/50 pb-2">
            <div className="font-bold text-xs text-apex-text flex items-center space-x-1.5">
              <Calculator className="w-3.5 h-3.5 text-apex-accent" />
              <span>REAL TIME POSITION SIZE CALCULATOR</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[9px] text-apex-muted font-bold">SYMBOL</label>
              <select
                value={symbol}
                onChange={e => setSymbol(e.target.value)}
                className="w-full bg-apex-bg border border-apex-border rounded px-2 py-1.5 text-[11px] text-apex-text font-bold focus:outline-none focus:border-apex-accent"
              >
                <option value="BTC/USDT">BTC/USDT</option>
                <option value="ETH/USDT">ETH/USDT</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[9px] text-apex-muted font-bold">PLANNED STOP LOSS DISTANCE (POINTS / $)</label>
              <input
                type="number"
                value={slDistance}
                onChange={e => setSlDistance(e.target.value)}
                className="w-full bg-apex-bg border border-apex-border rounded px-2 py-1.5 text-[11px] text-apex-text font-bold focus:outline-none focus:border-apex-accent"
                placeholder="500"
                min="1"
              />
            </div>
          </div>

          {/* Result */}
          <div className="bg-apex-bg rounded-lg border border-apex-border/60 divide-y divide-apex-border/30">
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-apex-muted">RECOMMENDED POSITION SIZE:</span>
              <span className="font-bold text-emerald-400 text-[11px]">
                {posSize?.recommendedContracts?.toFixed(4) ?? '0.0000'} Contracts
              </span>
            </div>
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-apex-muted">TOTAL RISK IN DOLLARS:</span>
              <span className="font-bold text-amber-400 text-[11px]">
                ${fmt(posSize?.totalRiskUsd ?? 0)}
              </span>
            </div>
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-apex-muted">IMPACT ON DAILY DRAWDOWN:</span>
              <span className={`font-bold text-[11px] ${(posSize?.impactOnDailyDD ?? 0) >= 2.0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {posSize?.impactOnDailyDD?.toFixed(2) ?? '0.00'}%
              </span>
            </div>
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-apex-muted">SAFE RISK AVAILABLE TODAY:</span>
              <span className="font-bold text-cyan-400 text-[11px]">
                ${fmt(posSize?.safeRiskAvailableToday ?? 0)}
              </span>
            </div>
            <div className="flex justify-between items-center p-2.5">
              <span className="text-[10px] text-apex-muted">NOTIONAL VALUE:</span>
              <span className="font-bold text-apex-text text-[11px]">
                ${fmt(posSize?.notionalValue ?? 0)}
              </span>
            </div>
          </div>

          <div className="p-2 bg-apex-bg rounded border border-apex-border/40 text-[9px] text-apex-muted">
            ⚡ {posSize?.ruleNote || '0.75% risk per trade | 5% max daily DD | 10% max total DD — FTMO Compliant'}
          </div>
        </div>

        {/* Rule Violation Detector */}
        <div className="bg-apex-surface/90 border border-apex-border rounded-lg p-4 space-y-3 shadow-lg">
          <div className="flex items-center justify-between border-b border-apex-border/50 pb-2">
            <div className="font-bold text-xs text-apex-text flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>RULE VIOLATION DETECTOR & HEALTH</span>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="p-2 bg-apex-bg rounded border border-apex-border/50 space-y-0.5">
              <div className="text-[9px] text-apex-muted">PASS PROBABILITY</div>
              <div className={`font-bold text-sm ${(r?.passProbability ?? 0) >= 60 ? 'text-emerald-400' : (r?.passProbability ?? 0) >= 40 ? 'text-amber-400' : 'text-rose-400'}`}>
                {r?.passProbability?.toFixed(1) ?? '0.0'}%
              </div>
            </div>
            <div className="p-2 bg-apex-bg rounded border border-apex-border/50 space-y-0.5">
              <div className="text-[9px] text-apex-muted">CONSISTENCY SCORE</div>
              <div className="font-bold text-sm text-cyan-400">
                {r?.consistencyScore?.toFixed(1) ?? '0.0'}%
              </div>
            </div>
            <div className="p-2 bg-apex-bg rounded border border-apex-border/50 space-y-0.5">
              <div className="text-[9px] text-apex-muted">PROJECTED FINISH</div>
              <div className="font-bold text-[10px] text-purple-400">
                {r?.projectedFinishDate ?? 'N/A'}
              </div>
            </div>
          </div>

          {/* Rule checklist */}
          <div className="space-y-1.5">
            {(r?.rules ?? []).map((rule, i) => {
              const isPass = rule.status === 'PASS';
              const isWarn = rule.status === 'WARN';
              const color = isPass ? 'text-emerald-400 border-emerald-500/20' : isWarn ? 'text-amber-400 border-amber-500/20' : 'text-rose-400 border-rose-500/20';
              const bg = isPass ? 'bg-emerald-500/5' : isWarn ? 'bg-amber-500/5' : 'bg-rose-500/5';
              return (
                <div key={i} className={`flex items-center justify-between p-2 rounded border ${bg} ${color}`}>
                  <div className="flex items-center space-x-2">
                    {isPass ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> : isWarn ? <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> : <XCircle className="w-3.5 h-3.5 shrink-0" />}
                    <span className="text-[10px] font-bold text-apex-text">{rule.rule}</span>
                  </div>
                  <div className="flex items-center space-x-2 text-[10px] shrink-0">
                    <span className="text-apex-muted">{rule.current.toFixed(1)}</span>
                    <span className={`font-bold ${color.split(' ')[0]}`}>{rule.status}</span>
                  </div>
                </div>
              );
            })}

            {/* Final summary */}
            <div className={`flex items-center space-x-2 p-2.5 rounded border text-[10px] mt-1 ${
              (r?.violationsCount ?? 0) === 0
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
            }`}>
              {(r?.violationsCount ?? 0) === 0
                ? <CheckCircle2 className="w-4 h-4 shrink-0" />
                : <XCircle className="w-4 h-4 shrink-0" />
              }
              <span className="font-bold">
                {(r?.violationsCount ?? 0) === 0
                  ? 'All 5 challenge rules fully compliant. Zero violations detected.'
                  : `${r?.violationsCount} rule violation(s) detected! Review immediately.`
                }
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Challenge Progress & Equity Curve ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

        {/* Challenge Progress Panel */}
        <div className="lg:col-span-4 bg-apex-surface/90 border border-apex-border rounded-lg p-4 space-y-4 shadow-lg">
          <div className="font-bold text-xs text-apex-text flex items-center space-x-1.5 border-b border-apex-border/50 pb-2">
            <Flame className="w-3.5 h-3.5 text-orange-400" />
            <span>CHALLENGE PROGRESS</span>
          </div>

          {/* Account Header */}
          <div className="p-3 bg-apex-bg rounded-lg border border-apex-border space-y-2">
            <div className="flex justify-between items-center">
              <div>
                <div className="font-bold text-apex-text text-[11px]">{s?.firmName ?? 'APEX PROP ENGINE'}</div>
                <div className="text-[9px] text-apex-muted">{s?.stage ?? 'STAGE 1 CHALLENGE'}</div>
              </div>
              <div className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                (s?.passProbability ?? 0) >= 60
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              }`}>
                PASS PROB {s?.passProbability?.toFixed(1) ?? '0.0'}%
              </div>
            </div>

            {/* Challenge Target Progress */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[9px]">
                <span className="text-apex-muted">TARGET PROGRESS ({s?.targetProfitPct ?? 8}%)</span>
                <span className="font-bold text-emerald-400">
                  ${fmt(s?.currentProfit ?? 0)} / ${fmt(s?.targetProfitUsd ?? 800)}
                </span>
              </div>
              <div className="w-full h-3 bg-apex-bg rounded-full overflow-hidden border border-apex-border/30 relative">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 rounded-full transition-all duration-700"
                  style={{ width: `${s?.progressPct ?? 0}%` }}
                />
                <div className="absolute inset-0 flex items-center justify-center text-[8px] font-bold text-white">
                  {s?.progressPct?.toFixed(1) ?? '0.0'}%
                </div>
              </div>
            </div>
          </div>

          {/* Real Stats Grid */}
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'NAV EQUITY', value: `$${fmt(s?.navEquity ?? 10000)}`, color: 'text-apex-text' },
              { label: 'REALIZED PNL', value: `${(s?.realizedPnl ?? 0) >= 0 ? '+' : ''}$${fmt(s?.realizedPnl ?? 0)}`, color: (s?.realizedPnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400' },
              { label: 'UNREALIZED PNL', value: `${(s?.unrealizedPnl ?? 0) >= 0 ? '+' : ''}$${fmt(s?.unrealizedPnl ?? 0)}`, color: (s?.unrealizedPnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400' },
              { label: 'TODAY PNL', value: `${(s?.dailyPnl ?? 0) >= 0 ? '+' : ''}$${fmt(s?.dailyPnl ?? 0)}`, color: (s?.dailyPnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400' },
              { label: 'WIN RATE', value: `${s?.winRate?.toFixed(1) ?? '0.0'}%`, color: 'text-purple-400' },
              { label: 'PROFIT FACTOR', value: `${s?.profitFactor?.toFixed(2) ?? '1.00'}`, color: 'text-cyan-400' },
              { label: 'DAYS TRADED', value: `${s?.daysTraded ?? 0} / ${s?.minTradingDays ?? 10} min`, color: 'text-amber-400' },
              { label: 'TOTAL TRADES', value: `${s?.totalTrades ?? 0}`, color: 'text-apex-text' },
            ].map((item, i) => (
              <div key={i} className="p-2 bg-apex-bg rounded border border-apex-border/50 space-y-0.5">
                <div className="text-[8.5px] text-apex-muted">{item.label}</div>
                <div className={`font-bold text-[10px] ${item.color}`}>{item.value}</div>
              </div>
            ))}
          </div>

          {/* Drawdown Status */}
          <div className="space-y-2">
            <ProgressBar
              label={`DAILY DD: ${s?.currentDailyDrawdownPct?.toFixed(2) ?? '0.00'}% / ${s?.maxDailyDrawdownPct ?? 5}%`}
              current={s?.currentDailyDrawdownPct ?? 0}
              max={s?.maxDailyDrawdownPct ?? 5}
              danger={(s?.currentDailyDrawdownPct ?? 0) >= 4.0}
              warn={(s?.currentDailyDrawdownPct ?? 0) >= 2.5}
            />
            <ProgressBar
              label={`TOTAL DD: ${s?.currentTotalDrawdownPct?.toFixed(2) ?? '0.00'}% / ${s?.maxTotalDrawdownPct ?? 10}%`}
              current={s?.currentTotalDrawdownPct ?? 0}
              max={s?.maxTotalDrawdownPct ?? 10}
              danger={(s?.currentTotalDrawdownPct ?? 0) >= 8.0}
              warn={(s?.currentTotalDrawdownPct ?? 0) >= 5.0}
            />
            <ProgressBar
              label={`CONSISTENCY: ${s?.consistencyScore?.toFixed(1) ?? '0'}%`}
              current={s?.consistencyScore ?? 0}
              max={100}
              color="bg-cyan-400"
            />
          </div>
        </div>

        {/* Equity Growth Curve */}
        <div className="lg:col-span-8 bg-apex-surface/90 border border-apex-border rounded-lg p-4 shadow-lg flex flex-col">
          <div className="flex items-center justify-between border-b border-apex-border/50 pb-2 mb-2">
            <div className="font-bold text-xs text-apex-text flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              <span>LIVE EQUITY GROWTH CURVE</span>
            </div>
            <div className="flex items-center space-x-3 text-[10px]">
              <span className="text-emerald-400 font-bold">
                Current: ${fmt(s?.navEquity ?? 10000)}
              </span>
              <span className={`font-bold ${(s?.currentProfitPct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {(s?.currentProfitPct ?? 0) >= 0 ? '+' : ''}{s?.currentProfitPct?.toFixed(2) ?? '0.00'}%
              </span>
            </div>
          </div>
          <div className="flex-1 min-h-[320px]">
            <EquityMiniChart curve={s?.equityCurve ?? []} initial={s?.initialCapital ?? 10000} />
          </div>

          {/* Quick stats below chart */}
          <div className="grid grid-cols-4 gap-2 mt-2 pt-2 border-t border-apex-border/30">
            {[
              { label: 'INITIAL', value: `$${fmt(s?.initialCapital ?? 10000)}`, color: 'text-apex-muted' },
              { label: 'TARGET', value: `$${fmt((s?.initialCapital ?? 10000) + (s?.targetProfitUsd ?? 800))}`, color: 'text-emerald-400' },
              { label: 'OPEN POS', value: `${s?.openPositions ?? 0}`, color: 'text-purple-400' },
              { label: 'PROJECTED', value: s?.projectedFinishDate ?? 'N/A', color: 'text-cyan-400' },
            ].map((item, i) => (
              <div key={i} className="p-2 bg-apex-bg rounded border border-apex-border/40 space-y-0.5">
                <div className="text-[8.5px] text-apex-muted">{item.label}</div>
                <div className={`font-bold text-[10px] ${item.color}`}>{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Auto Killswitch Status ─────────────────────────────────── */}
      <div className={`flex items-center space-x-3 p-3 rounded-lg border ${
        (r?.violationsCount ?? 0) === 0
          ? 'bg-emerald-500/5 border-emerald-500/20'
          : 'bg-rose-500/5 border-rose-500/20'
      }`}>
        <ShieldCheck className={`w-5 h-5 shrink-0 ${(r?.violationsCount ?? 0) === 0 ? 'text-emerald-400' : 'text-rose-400'}`} />
        <div>
          <div className={`font-bold text-[11px] ${(r?.violationsCount ?? 0) === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {(r?.violationsCount ?? 0) === 0
              ? '⚡ AUTO-KILLSWITCH ARMED — All 5 challenge rules fully compliant. Zero violations detected.'
              : `⚠️ KILLSWITCH ALERT — ${r?.violationsCount} violation(s) detected. Review and rectify immediately.`
            }
          </div>
          <div className="text-[9px] text-apex-muted mt-0.5">
            Daily DD: {r?.dailyDrawdownPct?.toFixed(2) ?? '0.00'}% | Total DD: {r?.totalDrawdownPct?.toFixed(2) ?? '0.00'}% | Win Rate: {r?.winRate?.toFixed(1) ?? '0.0'}% | PF: {r?.profitFactor?.toFixed(2) ?? '1.00'} | Consistency: {r?.consistencyScore?.toFixed(1) ?? '0.0'}% | Open Positions: {r?.openPositions ?? 0}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PropFirmCenter;
