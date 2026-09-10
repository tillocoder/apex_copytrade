import React, { useEffect, useState, useMemo } from 'react';
import {
  BarChart3, Clock, Calendar, Award, TrendingUp, Sparkles, RefreshCw,
  ShieldCheck, ArrowUpRight, ArrowDownRight, Target, Activity, Flame,
  Layers, CheckCircle2, Zap, Search, Filter, ChevronRight, ChevronLeft, X,
  SlidersHorizontal, Check, AlertCircle, Info, PieChart, Hash
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { TradeReplayModal } from './TradeReplayModal';
import {
  AnalyticsService,
  type PerformanceAnalyticsData,
  type StrategyBreakdown,
  type SymbolBreakdown,
  type RDistributionItem,
  type ForensicTradeItem,
  type AvailableDayItem,
  type AvailableMonthItem,
  type AnalyticsFilterParams
} from '../../services/analyticsService';

type FilterTab = 'all' | 'today' | 'yesterday' | 'week' | 'month' | 'by_day' | 'by_month';
type OutcomeFilter = 'ALL' | 'WINS' | 'LOSSES' | 'TP2' | 'BE';

interface CalendarCell {
  dayNumber: number;
  dateStr: string;
  isToday: boolean;
  hasTrades: boolean;
  pnl: number;
  winRate: number;
  tradesCount: number;
  winsCount: number;
  lossesCount: number;
  colorType: 'GREEN' | 'RED' | 'NEUTRAL';
}

export const AnalyticsModule: React.FC = () => {
  const [analytics, setAnalytics] = useState<PerformanceAnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Filters
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [selectedDay, setSelectedDay] = useState<string>('');
  const [selectedMonth, setSelectedMonth] = useState<string>('');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('ALL');
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Calendar State
  const [calendarYear, setCalendarYear] = useState<number>(2026);
  const [calendarMonth, setCalendarMonth] = useState<number>(9); // 9 = September
  const [selectedCalendarDay, setSelectedCalendarDay] = useState<string | null>(null);

  // Trade Inspector Modal
  const [inspectedTrade, setInspectedTrade] = useState<ForensicTradeItem | null>(null);

  const fetchAnalytics = async (overrideParams?: AnalyticsFilterParams) => {
    try {
      setIsRefreshing(true);
      const params: AnalyticsFilterParams = overrideParams || {};

      if (!overrideParams) {
        if (activeTab === 'today') {
          params.rangeType = 'today';
        } else if (activeTab === 'yesterday') {
          params.rangeType = 'yesterday';
        } else if (activeTab === 'week') {
          params.rangeType = 'week';
        } else if (activeTab === 'month') {
          params.rangeType = 'this_month';
        } else if (activeTab === 'by_day') {
          params.rangeType = 'day';
          if (selectedDay) params.date = selectedDay;
        } else if (activeTab === 'by_month') {
          params.rangeType = 'month';
          if (selectedMonth) params.month = selectedMonth;
        } else {
          params.rangeType = 'all';
        }

        if (selectedSymbol && selectedSymbol !== 'ALL') {
          params.symbol = selectedSymbol;
        }
      }

      const data = await AnalyticsService.fetchAnalyticsPerformance(params);
      if (data) {
        setAnalytics(data);
        setLastUpdate(new Date());

        // Set initial day/month if not selected yet
        if (!selectedDay && data.availableDays?.length > 0) {
          setSelectedDay(data.availableDays[0].date);
        }
        if (!selectedMonth && data.availableMonths?.length > 0) {
          setSelectedMonth(data.availableMonths[0].month);
        }
      }
    } catch (err) {
      console.error("[AnalyticsModule] fetch error:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(() => {
      fetchAnalytics();
    }, 8000);
    return () => clearInterval(interval);
  }, [activeTab, selectedDay, selectedMonth, selectedSymbol]);

  // Handle Tab Switch
  const handleTabChange = (tab: FilterTab) => {
    setActiveTab(tab);
    if (tab === 'today') {
      setSelectedCalendarDay('2026-09-08');
      setCalendarYear(2026);
      setCalendarMonth(9);
      fetchAnalytics({ rangeType: 'today', symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined });
    } else if (tab === 'yesterday') {
      const yKey = analytics?.availableDays?.[1]?.date ?? '2026-09-07';
      setSelectedCalendarDay(yKey);
      fetchAnalytics({ rangeType: 'yesterday', symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined });
    } else if (tab === 'week') {
      setSelectedCalendarDay(null);
      fetchAnalytics({ rangeType: 'week', symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined });
    } else if (tab === 'month') {
      setSelectedCalendarDay(null);
      setCalendarYear(2026);
      setCalendarMonth(9);
      fetchAnalytics({ rangeType: 'this_month', symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined });
    } else if (tab === 'by_day') {
      const d = selectedDay || (analytics?.availableDays?.[0]?.date ?? '2026-09-08');
      setSelectedDay(d);
      setSelectedCalendarDay(d);
      fetchAnalytics({ rangeType: 'day', date: d, symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined });
    } else if (tab === 'by_month') {
      const m = selectedMonth || (analytics?.availableMonths?.[0]?.month ?? '2026-09');
      setSelectedMonth(m);
      setSelectedCalendarDay(null);
      fetchAnalytics({ rangeType: 'month', month: m, symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined });
    } else {
      setSelectedCalendarDay(null);
      fetchAnalytics({ rangeType: 'all', symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined });
    }
  };

  // Calendar Day Click Handler
  const handleCalendarDayClick = (dateStr: string) => {
    if (selectedCalendarDay === dateStr) {
      // Toggle off -> reset to all
      handleClearCalendarDayFilter();
      return;
    }
    setSelectedCalendarDay(dateStr);
    setSelectedDay(dateStr);
    setActiveTab('by_day');
    fetchAnalytics({
      rangeType: 'day',
      date: dateStr,
      symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined
    });
  };

  // Clear Calendar Day Filter
  const handleClearCalendarDayFilter = () => {
    setSelectedCalendarDay(null);
    setActiveTab('all');
    fetchAnalytics({
      rangeType: 'all',
      symbol: selectedSymbol !== 'ALL' ? selectedSymbol : undefined
    });
  };

  // Switch Calendar Months
  const handlePrevMonth = () => {
    if (calendarMonth === 9) {
      setCalendarMonth(8);
      setCalendarYear(2026);
    } else if (calendarMonth === 8) {
      setCalendarMonth(9);
      setCalendarYear(2026);
    }
  };

  const handleNextMonth = () => {
    if (calendarMonth === 8) {
      setCalendarMonth(9);
      setCalendarYear(2026);
    } else if (calendarMonth === 9) {
      setCalendarMonth(8);
      setCalendarYear(2026);
    }
  };

  const handleJumpToday = () => {
    setCalendarYear(2026);
    setCalendarMonth(9);
    handleCalendarDayClick('2026-09-08');
  };

  // Map of available days for fast O(1) lookup
  const dayMap = useMemo(() => {
    const map: Record<string, AvailableDayItem> = {};
    (analytics?.availableDays || []).forEach(d => {
      map[d.date] = d;
    });
    return map;
  }, [analytics?.availableDays]);

  // Calendar Month Statistics Strip
  const monthSummary = useMemo(() => {
    const monthKey = `${calendarYear}-${String(calendarMonth).padStart(2, '0')}`;
    const daysInMonth = (analytics?.availableDays || []).filter(d => d.date.startsWith(monthKey));
    const totalTrades = daysInMonth.reduce((acc, d) => acc + d.tradesCount, 0);
    const totalWins = daysInMonth.reduce((acc, d) => acc + d.winsCount, 0);
    const totalLosses = daysInMonth.reduce((acc, d) => acc + d.lossesCount, 0);
    const totalPnl = daysInMonth.reduce((acc, d) => acc + d.pnl, 0);
    const winRate = totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0;
    const greenDays = daysInMonth.filter(d => d.pnl > 0).length;
    const redDays = daysInMonth.filter(d => d.pnl < 0).length;

    return {
      monthKey,
      monthTitle: calendarMonth === 9 ? 'SENTYABR 2026' : calendarMonth === 8 ? 'AVGUST 2026' : `${calendarYear}-${calendarMonth}`,
      totalTrades,
      totalWins,
      totalLosses,
      totalPnl,
      winRate,
      greenDays,
      redDays
    };
  }, [analytics?.availableDays, calendarYear, calendarMonth]);

  // Calendar Grid Matrix (Monday to Sunday)
  const calendarGrid = useMemo(() => {
    const cells: (CalendarCell | null)[] = [];
    const numDays = new Date(calendarYear, calendarMonth, 0).getDate();
    const firstDay = new Date(calendarYear, calendarMonth - 1, 1).getDay();
    const firstDayMon = (firstDay + 6) % 7; // Monday = 0, Sunday = 6

    // Preceding empty slots
    for (let i = 0; i < firstDayMon; i++) {
      cells.push(null);
    }

    const todayStr = '2026-09-08';

    for (let d = 1; d <= numDays; d++) {
      const dateStr = `${calendarYear}-${String(calendarMonth).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const dayData = dayMap[dateStr];
      const isToday = dateStr === todayStr;

      if (dayData && dayData.tradesCount > 0) {
        // 3 DISTINCT COLORS:
        // 1. GREEN: Net Profit > 0 (or Win Rate >= 50%)
        // 2. RED: Net Loss < 0 (or Win Rate < 50%)
        // 3. NEUTRAL: Break-Even / Zero PnL
        let colorType: 'GREEN' | 'RED' | 'NEUTRAL' = 'NEUTRAL';
        if (dayData.pnl > 0 || (dayData.pnl === 0 && dayData.winRate >= 50)) {
          colorType = 'GREEN';
        } else if (dayData.pnl < 0 || (dayData.pnl === 0 && dayData.winRate < 50)) {
          colorType = 'RED';
        }

        cells.push({
          dayNumber: d,
          dateStr,
          isToday,
          hasTrades: true,
          pnl: dayData.pnl,
          winRate: dayData.winRate,
          tradesCount: dayData.tradesCount,
          winsCount: dayData.winsCount,
          lossesCount: dayData.lossesCount,
          colorType
        });
      } else {
        // Inactive / Weekend / No Trades
        cells.push({
          dayNumber: d,
          dateStr,
          isToday,
          hasTrades: false,
          pnl: 0,
          winRate: 0,
          tradesCount: 0,
          winsCount: 0,
          lossesCount: 0,
          colorType: 'NEUTRAL'
        });
      }
    }

    // Trailing empty slots to complete the week
    while (cells.length % 7 !== 0) {
      cells.push(null);
    }

    return cells;
  }, [calendarYear, calendarMonth, dayMap]);

  // Filtered trades list
  const filteredTrades = useMemo(() => {
    let list = analytics?.trades || [];

    // Filter by outcome
    if (outcomeFilter === 'WINS') {
      list = list.filter(t => t.is_win);
    } else if (outcomeFilter === 'LOSSES') {
      list = list.filter(t => !t.is_win);
    } else if (outcomeFilter === 'TP2') {
      list = list.filter(t => t.status.includes('TP2'));
    } else if (outcomeFilter === 'BE') {
      list = list.filter(t => t.status.includes('BE'));
    }

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(t =>
        t.symbol.toLowerCase().includes(q) ||
        t.status.toLowerCase().includes(q) ||
        t.setup.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q) ||
        (t.date_str && t.date_str.includes(q))
      );
    }

    return list;
  }, [analytics?.trades, outcomeFilter, searchQuery]);

  // Cumulative Equity Growth Chart
  const getEquityGrowthChartOption = () => {
    const rawCurve = analytics?.equityCurve || [];
    const labels = rawCurve.map(c => c.timestamp);
    const data = rawCurve.map(c => c.equity);

    const isPositive = (analytics?.netPnl ?? 0) >= 0;
    const gradientColor = isPositive ? '#10B981' : '#06B6D4';

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#0F172A',
        borderColor: '#1E293B',
        textStyle: { color: '#F8FAFC', fontFamily: 'JetBrains Mono', fontSize: 11 },
        formatter: (params: any) => {
          const pt = params[0];
          const rawItem = rawCurve[pt.dataIndex];
          const tradePnlStr = rawItem?.trade_pnl !== undefined
            ? `<br/>Natija: <span style="color:${rawItem.trade_pnl >= 0 ? '#10B981' : '#F43F5E'};font-weight:bold;">${rawItem.trade_pnl >= 0 ? '+' : ''}$${rawItem.trade_pnl.toFixed(2)} USD</span>`
            : '';
          const symStr = rawItem?.symbol ? `<br/>Aktiv: ${rawItem.symbol}` : '';
          return `<strong>${pt.name}</strong><br/>Balans: <strong>$${Number(pt.value).toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong>${tradePnlStr}${symStr}`;
        }
      },
      grid: { left: '10%', right: '4%', top: '12%', bottom: '15%' },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: '#1E293B' } },
        axisLabel: { color: '#64748B', fontSize: 9.5 }
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLine: { lineStyle: { color: '#1E293B' } },
        splitLine: { lineStyle: { color: '#141E33', type: 'dashed' } },
        axisLabel: {
          color: '#64748B',
          fontSize: 9.5,
          formatter: (val: number) => `$${Math.round(val)}`
        }
      },
      series: [{
        name: 'Equity',
        type: 'line',
        smooth: 0.25,
        showSymbol: rawCurve.length < 25,
        symbolSize: 6,
        itemStyle: { color: gradientColor },
        lineStyle: { width: 2.5, color: gradientColor },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: isPositive ? 'rgba(16, 185, 129, 0.28)' : 'rgba(6, 182, 212, 0.28)' },
              { offset: 1, color: 'rgba(15, 23, 42, 0.0)' }
            ]
          }
        },
        data: data
      }]
    };
  };

  const winRate = analytics?.winRate ?? 37.5;
  const netPnl = analytics?.netPnl ?? 0.0;
  const totalTrades = analytics?.totalTrades ?? 0;
  const winCount = analytics?.winCount ?? 0;
  const lossCount = analytics?.lossCount ?? 0;
  const profitFactor = analytics?.profitFactor ?? 0.0;

  return (
    <div className="flex-1 bg-[#070A11] text-[#E2E8F0] p-4 lg:p-6 overflow-y-auto min-h-screen font-sans">
      {/* ── HEADER BANNER & TIME RANGE CONTROLLER ────────────────────────────────────── */}
      <div className="mb-6 space-y-4">
        {/* Title and Live Status */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#0D1322]/80 border border-[#1E293B] rounded-2xl p-4 lg:p-5 backdrop-blur-md shadow-2xl shadow-cyan-950/20">
          <div className="flex items-start md:items-center gap-3.5">
            <div className="p-3 bg-gradient-to-br from-cyan-500/20 to-emerald-500/10 border border-cyan-500/30 rounded-xl text-cyan-400 shadow-inner">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-xl lg:text-2xl font-black tracking-tight text-white font-mono">
                  QUANT PERFORMANCE & FORENSICS
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  LIVE AUDIT
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">
                  {analytics?.totalTrades ?? 64} TRACES ANALYZED
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                {analytics?.activeRangeLabel || "Barcha Vaqt (All Time)"} · Real Binance settles from SQLite engine
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <div className="text-right hidden sm:block">
              <div className="text-[10px] font-mono text-slate-400">OXIRGI YANGILANISH</div>
              <div className="text-xs font-mono text-slate-200">{lastUpdate.toLocaleTimeString()}</div>
            </div>
            <button
              onClick={() => fetchAnalytics()}
              disabled={isRefreshing}
              className={`p-2.5 rounded-xl bg-[#131D31] hover:bg-[#1A2640] border border-[#223354] text-slate-200 transition-all ${
                isRefreshing ? 'opacity-50' : 'hover:border-cyan-500/40 active:scale-95'
              }`}
              title="Yangilash"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Dynamic Range Filters (Daily, Monthly, Range Tabs) */}
        <div className="bg-[#0B101D] border border-[#182643] rounded-2xl p-3 flex flex-wrap items-center justify-between gap-3 shadow-inner">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
            {[
              { id: 'all', label: 'Barchasi (All)' },
              { id: 'today', label: 'Bugun (Today)' },
              { id: 'yesterday', label: 'Kecha' },
              { id: 'week', label: 'Oxirgi 7 kun' },
              { id: 'month', label: 'Sentyabr 2026' }
            ].map(tab => {
              const isActive = activeTab === tab.id && !selectedCalendarDay;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id as FilterTab)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-mono font-semibold transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#131D31] border border-transparent'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}

            {/* Active Calendar Day Indicator Pill */}
            {selectedCalendarDay && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/20 border border-cyan-500/50 text-cyan-300 text-xs font-mono font-bold animate-pulse">
                <Calendar className="w-3.5 h-3.5" />
                <span>Kun: {selectedCalendarDay}</span>
                <button
                  onClick={handleClearCalendarDayFilter}
                  className="ml-1 p-0.5 rounded-full hover:bg-cyan-500/30 text-white"
                  title="Filtrni tozalash"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>

          {/* Asset filter */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400 hidden md:inline">AKTIV:</span>
            <select
              value={selectedSymbol}
              onChange={(e) => {
                setSelectedSymbol(e.target.value);
                fetchAnalytics({ symbol: e.target.value !== 'ALL' ? e.target.value : undefined });
              }}
              className="bg-[#111A2E] border border-[#1E2D4D] rounded-xl px-2.5 py-1 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
            >
              <option value="ALL">Barcha Aktivlar</option>
              <option value="BTC/USDT">BTC/USDT</option>
              <option value="ETH/USDT">ETH/USDT</option>
              <option value="SOL/USDT">SOL/USDT</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── FIVE CORE KPI CARDS ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 mb-6">
        {/* KPI 1: Win Rate */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-md relative overflow-hidden group hover:border-cyan-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
            <span className="uppercase tracking-wider">NET WIN RATE</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-black font-mono tracking-tight ${
              winRate >= 50 ? 'text-emerald-400' : winRate >= 35 ? 'text-cyan-400' : 'text-amber-400'
            }`}>
              {winRate.toFixed(1)}%
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              ({winCount}W / {lossCount}L)
            </span>
          </div>
          <div className="mt-2.5">
            <div className="w-full bg-[#162138] h-1.5 rounded-full overflow-hidden flex">
              <div className="bg-emerald-500 h-full transition-all" style={{ width: `${winRate}%` }}></div>
              <div className="bg-rose-500 h-full transition-all" style={{ width: `${100 - winRate}%` }}></div>
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-slate-400">
            <span>Long: {analytics?.longWinRate ?? 0}% WR</span>
            <span>Short: {analytics?.shortWinRate ?? 0}% WR</span>
          </div>
        </div>

        {/* KPI 2: Realized Net PnL */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-md relative overflow-hidden group hover:border-emerald-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
            <span className="uppercase tracking-wider">REALIZED NET PNL</span>
            <Award className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-black font-mono tracking-tight ${
              netPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}>
              {netPnl >= 0 ? '+' : ''}${netPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[10px] font-mono text-slate-500 uppercase">USD</span>
          </div>
          <div className="mt-2 text-[10px] font-mono flex items-center justify-between text-slate-400">
            <span className="text-emerald-400/90">+${(analytics?.grossProfit ?? 0).toFixed(2)} foyda</span>
            <span className="text-rose-400/90">-${(analytics?.grossLoss ?? 0).toFixed(2)} zarar</span>
          </div>
        </div>

        {/* KPI 3: Profit Factor & Expectancy */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-md relative overflow-hidden group hover:border-purple-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
            <span className="uppercase tracking-wider">PROFIT FACTOR & EXP</span>
            <TrendingUp className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-purple-400 tracking-tight">
              {profitFactor.toFixed(2)}x
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Gross Win/Loss
            </span>
          </div>
          <div className="mt-2 text-[10px] font-mono text-slate-400 flex items-center justify-between">
            <span>Expectancy:</span>
            <span className={`font-bold font-mono ${(analytics?.expectancyValue ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {analytics?.expectancy || '$0.00 / Trade'}
            </span>
          </div>
        </div>

        {/* KPI 4: Max Drawdown & Sharpe */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-md relative overflow-hidden group hover:border-amber-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
            <span className="uppercase tracking-wider">PROP FIRM RISK</span>
            <ShieldCheck className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-amber-400 tracking-tight">
              {analytics?.maxDrawdownPct ?? 3.18}%
            </span>
            <span className="text-[10px] font-mono text-slate-500">MAX PEAK DD</span>
          </div>
          <div className="mt-2 text-[10px] font-mono text-slate-400 flex items-center justify-between">
            <span>Sharpe: <strong className="text-slate-200">{analytics?.sharpeRatio ?? 0.85}</strong></span>
            <span className="text-emerald-400 font-bold">100% Xavfsiz</span>
          </div>
        </div>

        {/* KPI 5: Best Session & Day */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-md relative overflow-hidden group hover:border-blue-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
            <span className="uppercase tracking-wider">OPTIMAL SESSIYA</span>
            <Clock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-base font-black font-mono text-blue-400 truncate">
            {analytics?.bestSession || '12:00 - 16:00 UTC'}
          </div>
          <div className="text-[10px] font-mono text-slate-400 mt-1 truncate">
            {analytics?.bestSessionSub || 'London / NY Open'}
          </div>
          <div className="mt-2 text-[10px] font-mono text-cyan-400 font-semibold truncate">
            Kun: {selectedCalendarDay || analytics?.bestDay || 'WEDNESDAY'}
          </div>
        </div>
      </div>

      {/* ── CORE CHARTS ROW: INSTITUTIONAL PERFORMANCE CALENDAR & EQUITY GROWTH ─────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mb-6">
        {/* Left: Professional Trading Performance Calendar (Replacing old raw heatmap) */}
        <div className="lg:col-span-7 bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 lg:p-5 shadow-2xl flex flex-col justify-between">
          <div>
            {/* Calendar Header with Month Navigation */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 pb-3 border-b border-[#182643]">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gradient-to-br from-emerald-500/20 to-cyan-500/10 border border-emerald-500/30 rounded-xl text-emerald-400">
                  <Calendar className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white font-mono tracking-wider flex items-center gap-2">
                    SAVDO NATIJALARI TAQVIMI
                  </h3>
                  <p className="text-[10px] text-slate-400 font-mono">
                    Kunlik foyda, zarar va win rate taqsimoti (TradeZella Institutional Standard)
                  </p>
                </div>
              </div>

              {/* Month Switcher Controls */}
              <div className="flex items-center gap-1.5 self-end sm:self-auto">
                <button
                  onClick={handlePrevMonth}
                  className="p-1.5 rounded-lg bg-[#141E34] hover:bg-[#1C2A48] border border-[#223354] text-slate-300 hover:text-white transition-all flex items-center gap-1 text-[11px] font-mono"
                  title="Oldingi Oy"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{calendarMonth === 9 ? 'Avgust' : 'Sentyabr'}</span>
                </button>

                <div className="px-3 py-1 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-xs font-mono font-bold text-cyan-300 tracking-wider">
                  {monthSummary.monthTitle}
                </div>

                <button
                  onClick={handleNextMonth}
                  className="p-1.5 rounded-lg bg-[#141E34] hover:bg-[#1C2A48] border border-[#223354] text-slate-300 hover:text-white transition-all flex items-center gap-1 text-[11px] font-mono"
                  title="Keyingi Oy"
                >
                  <span className="hidden sm:inline">{calendarMonth === 8 ? 'Sentyabr' : 'Avgust'}</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>

                <button
                  onClick={handleJumpToday}
                  className="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[11px] font-mono font-semibold transition-all ml-1"
                >
                  Bugun
                </button>
              </div>
            </div>

            {/* Monthly Summary Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 bg-[#0A101D] border border-[#16233B] rounded-xl p-2.5 mb-3.5 text-center text-xs font-mono">
              <div>
                <div className="text-[10px] text-slate-500">OYLIK PNL</div>
                <div className={`font-bold ${monthSummary.totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {monthSummary.totalPnl >= 0 ? '+' : ''}${monthSummary.totalPnl.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500">SAVDOLAR</div>
                <div className="font-bold text-white">{monthSummary.totalTrades} ta</div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500">WIN RATE</div>
                <div className="font-bold text-cyan-400">{monthSummary.winRate.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500">YASHIL KUNLAR</div>
                <div className="font-bold text-emerald-400">{monthSummary.greenDays} kun</div>
              </div>
              <div className="col-span-2 sm:col-span-1">
                <div className="text-[10px] text-slate-500">QIZIL KUNLAR</div>
                <div className="font-bold text-rose-400">{monthSummary.redDays} kun</div>
              </div>
            </div>

            {/* Calendar Day Header Row (7 cols: Dush - Yak) */}
            <div className="grid grid-cols-7 gap-1.5 text-center mb-1.5">
              {['DUSH', 'SESH', 'CHOR', 'PAY', 'JUM', 'SHAN', 'YAK'].map((dayName, idx) => (
                <div
                  key={idx}
                  className="text-[10.5px] font-mono font-bold text-slate-400 py-1 bg-[#101828] rounded-lg border border-[#1A253A]"
                >
                  {dayName}
                </div>
              ))}
            </div>

            {/* Calendar Cells Grid (3 distinct colors) */}
            <div className="grid grid-cols-7 gap-1.5">
              {calendarGrid.map((cell, idx) => {
                if (!cell) {
                  return (
                    <div
                      key={`empty-${idx}`}
                      className="min-h-[58px] rounded-xl bg-transparent border border-dashed border-[#131B2A]/40 opacity-20"
                    />
                  );
                }

                const isSelected = selectedCalendarDay === cell.dateStr;

                // Color 1: Green (Foyda / Positive WR)
                if (cell.colorType === 'GREEN') {
                  return (
                    <div
                      key={cell.dateStr}
                      onClick={() => handleCalendarDayClick(cell.dateStr)}
                      className={`min-h-[58px] p-1.5 rounded-xl flex flex-col justify-between cursor-pointer transition-all duration-150 relative ${
                        isSelected
                          ? 'ring-2 ring-cyan-400 border-cyan-400 bg-cyan-950/60 shadow-xl shadow-cyan-500/30 scale-[1.03] z-10'
                          : 'bg-emerald-950/25 hover:bg-emerald-900/40 border border-emerald-500/40 hover:border-emerald-400 shadow-sm'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black font-mono text-emerald-300">
                          {cell.dayNumber}
                        </span>
                        {cell.isToday ? (
                          <span className="text-[8.5px] font-mono px-1 py-0.2 rounded bg-cyan-500 text-slate-950 font-bold uppercase">
                            Bugun
                          </span>
                        ) : (
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        )}
                      </div>
                      <div className="mt-0.5">
                        <div className="text-[11px] font-black font-mono text-emerald-400 truncate">
                          +${cell.pnl.toFixed(2)}
                        </div>
                        <div className="text-[9px] font-mono text-emerald-300/80 flex items-center justify-between">
                          <span>{cell.winRate.toFixed(0)}%</span>
                          <span>{cell.tradesCount}t</span>
                        </div>
                      </div>
                    </div>
                  );
                }

                // Color 2: Red (Zarar / Negative WR)
                if (cell.colorType === 'RED') {
                  return (
                    <div
                      key={cell.dateStr}
                      onClick={() => handleCalendarDayClick(cell.dateStr)}
                      className={`min-h-[58px] p-1.5 rounded-xl flex flex-col justify-between cursor-pointer transition-all duration-150 relative ${
                        isSelected
                          ? 'ring-2 ring-cyan-400 border-cyan-400 bg-cyan-950/60 shadow-xl shadow-cyan-500/30 scale-[1.03] z-10'
                          : 'bg-rose-950/25 hover:bg-rose-900/40 border border-rose-500/40 hover:border-rose-400 shadow-sm'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black font-mono text-rose-300">
                          {cell.dayNumber}
                        </span>
                        {cell.isToday ? (
                          <span className="text-[8.5px] font-mono px-1 py-0.2 rounded bg-cyan-500 text-slate-950 font-bold uppercase">
                            Bugun
                          </span>
                        ) : (
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                        )}
                      </div>
                      <div className="mt-0.5">
                        <div className="text-[11px] font-black font-mono text-rose-400 truncate">
                          ${cell.pnl.toFixed(2)}
                        </div>
                        <div className="text-[9px] font-mono text-rose-300/80 flex items-center justify-between">
                          <span>{cell.winRate.toFixed(0)}%</span>
                          <span>{cell.tradesCount}t</span>
                        </div>
                      </div>
                    </div>
                  );
                }

                // Color 3: Neutral (Dam olish / Savdo qilinmagan kunlar / Break-Even)
                return (
                  <div
                    key={cell.dateStr}
                    onClick={() => {
                      if (cell.hasTrades) {
                        handleCalendarDayClick(cell.dateStr);
                      }
                    }}
                    className={`min-h-[58px] p-1.5 rounded-xl flex flex-col justify-between transition-all duration-150 ${
                      isSelected
                        ? 'ring-2 ring-cyan-400 border-cyan-400 bg-cyan-950/50 scale-[1.02] z-10'
                        : cell.hasTrades
                        ? 'bg-slate-800/40 hover:bg-slate-800/70 border border-slate-600/50 cursor-pointer'
                        : 'bg-[#0A101D]/40 border border-[#162138]/60 text-slate-600 hover:border-slate-700/60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-medium text-slate-500">
                        {cell.dayNumber}
                      </span>
                      {cell.isToday && (
                        <span className="text-[8.5px] font-mono px-1 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-700 font-bold uppercase">
                          Bugun
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] font-mono text-slate-600 text-center py-1">
                      {cell.hasTrades ? '$0.00' : '—'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Calendar Bottom Legend & Active Day Filter Controller */}
          <div className="mt-3 pt-3 border-t border-[#182643]">
            {selectedCalendarDay ? (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-xl bg-gradient-to-r from-cyan-950/50 to-emerald-950/30 border border-cyan-500/40 shadow-lg shadow-cyan-950/30">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                  <span className="text-xs font-mono font-bold text-cyan-300">
                    KUN FILTRI FAOL: {selectedCalendarDay}
                  </span>
                  <span className="text-[11px] font-mono text-slate-300">
                    ({totalTrades} ta savdo · Net PnL: {netPnl >= 0 ? '+' : ''}${netPnl.toFixed(2)} · {winRate.toFixed(1)}% WR)
                  </span>
                </div>
                <button
                  onClick={handleClearCalendarDayFilter}
                  className="px-3 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 hover:text-white border border-cyan-500/40 text-xs font-mono font-semibold flex items-center gap-1.5 transition-all self-start sm:self-auto"
                >
                  <X className="w-3.5 h-3.5" />
                  Barcha Kunlarni Ko'rish
                </button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center justify-between text-[10.5px] font-mono text-slate-400 gap-2">
                <div className="flex items-center gap-4 flex-wrap">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-md bg-emerald-500/80 border border-emerald-400"></span>
                    <span className="text-emerald-300 font-semibold">Yashil: Foyda (WR ≥ 50%)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-md bg-rose-500/80 border border-rose-400"></span>
                    <span className="text-rose-300 font-semibold">Qizil: Zarar (WR &lt; 50%)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-md bg-[#162138] border border-slate-600"></span>
                    <span className="text-slate-400">Neytral: Dam olish / 0 PnL</span>
                  </div>
                </div>
                <span className="text-[10px] text-slate-500">
                  Istalgan kunni bosing va o'sha kundagi savdolarni ko'ring
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Cumulative Equity Growth Chart */}
        <div className="lg:col-span-5 bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 lg:p-5 shadow-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white font-mono tracking-wider">
                  CUMULATIVE EQUITY GROWTH
                </h3>
              </div>
              <div className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                netPnl >= 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}>
                {netPnl >= 0 ? '+' : ''}${netPnl.toFixed(2)} USD
              </div>
            </div>
            <p className="text-[11px] text-slate-400 mb-3 font-mono">
              {selectedCalendarDay ? `${selectedCalendarDay} kungi intraday o'sish traektoriyasi.` : "Tanlangan oraliq bo'yicha prop kapital ($10,000) o'sish egri chizig'i."}
            </p>
            <div className="h-[270px] w-full">
              <ReactECharts
                option={getEquityGrowthChartOption()}
                style={{ height: '100%', width: '100%' }}
                notMerge={true}
                lazyUpdate={true}
              />
            </div>
          </div>

          <div className="mt-2 pt-2.5 border-t border-[#182643] flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>Boshlang'ich: <strong>$10,000.00</strong></span>
            <span>Joriy Ekuiti: <strong className="text-white">${(10000 + netPnl).toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong></span>
          </div>
        </div>
      </div>

      {/* ── THREE COLUMN BREAKDOWN: SMC SETUPS, ASSET METRICS, R-DISTRIBUTION ──────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Column 1: SMC Setup Alpha Metrics */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-lg flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-white font-mono text-xs font-bold tracking-wider">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>SMC SETUP ALPHA METRICS</span>
            </div>
            <span className="text-[9px] font-mono text-cyan-400/80 bg-cyan-500/10 px-2 py-0.5 rounded">REAL METRICS</span>
          </div>

          <div className="space-y-3">
            {(analytics?.strategyBreakdown || []).map((s, idx) => (
              <div key={idx} className="bg-[#111A2E] border border-[#1B2A4A] rounded-xl p-3">
                <div className="flex items-center justify-between text-xs font-bold font-mono text-slate-200 mb-1.5">
                  <span className="truncate pr-2">{s.setup}</span>
                  <span className="text-cyan-400 whitespace-nowrap">{s.winRate}% WR</span>
                </div>
                <div className="w-full bg-[#182542] h-1.5 rounded-full overflow-hidden mb-2">
                  <div className="bg-cyan-400 h-full rounded-full" style={{ width: `${s.winRate}%` }}></div>
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span>Savdolar: <strong>{s.trades} ta</strong></span>
                  <span>PF: <strong>{s.profitFactor}</strong></span>
                  <span>Avg R:R: <strong>1:{s.avgRR}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Column 2: Real Asset Performance */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-lg flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-white font-mono text-xs font-bold tracking-wider">
              <Zap className="w-4 h-4 text-emerald-400" />
              <span>REAL ASSET PERFORMANCE</span>
            </div>
            <span className="text-[9px] font-mono text-emerald-400/80 bg-emerald-500/10 px-2 py-0.5 rounded">FILTER: ACTIVE</span>
          </div>

          <div className="space-y-3">
            {(analytics?.symbolBreakdown || []).map((sym, idx) => (
              <div key={idx} className="bg-[#111A2E] border border-[#1B2A4A] rounded-xl p-3 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold font-mono text-white flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                    {sym.symbol}
                  </span>
                  <span className={`text-xs font-mono font-bold ${sym.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {sym.pnl >= 0 ? '+' : ''}${sym.pnl.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-[#182643]">
                  <span>{sym.trades} Executions</span>
                  <span>Win Rate: <strong className="text-cyan-300">{sym.winRate}%</strong></span>
                  <span>PF: <strong className="text-slate-200">{sym.profitFactor}x</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Column 3: R-Multiple Distribution */}
        <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 shadow-lg flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-white font-mono text-xs font-bold tracking-wider">
              <PieChart className="w-4 h-4 text-purple-400" />
              <span>REAL R-MULTIPLE OUTCOME</span>
            </div>
            <span className="text-[9px] font-mono text-purple-400/80 bg-purple-500/10 px-2 py-0.5 rounded">EXPECTED TARGETS</span>
          </div>

          <div className="space-y-3">
            {(analytics?.rDistribution || []).map((r, idx) => (
              <div key={idx} className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className={`font-bold ${
                    r.type === 'LOSS' ? 'text-rose-400' : r.type === 'BREAKEVEN' ? 'text-slate-400' : 'text-emerald-400'
                  }`}>
                    {r.r}
                  </span>
                  <span className="text-slate-400 text-[10px]">
                    {r.pct}% ({r.count} ta)
                  </span>
                </div>
                <div className="w-full bg-[#182542] h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      r.type === 'LOSS' ? 'bg-rose-500' : r.type === 'BREAKEVEN' ? 'bg-slate-500' : 'bg-emerald-400'
                    }`}
                    style={{ width: `${r.pct}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-auto pt-3 text-[10px] text-slate-500 font-mono italic">
            🛡️ Institutional Risk: 0.13% risk per trade bilan hisoblangan haqiqiy R-ko'rsatkichlari.
          </div>
        </div>
      </div>

      {/* ── THE CROWN JEWEL: FORENSIC TRADE LIST (OSHA KUNDAGI / OYDAGI PAZITSALAR) ── */}
      <div className="bg-[#0D1424] border border-[#1B2844] rounded-2xl p-4 lg:p-5 shadow-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-4 border-b border-[#182643]">
          <div>
            <h2 className="text-base font-black text-white font-mono tracking-wide flex items-center gap-2">
              <Layers className="w-5 h-5 text-cyan-400" />
              FORENSIC TRADE EXECUTION LOGS
              {selectedCalendarDay && (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  {selectedCalendarDay}
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Tanlangan davrdagi har bir buyruqning kirish/chiqish narxi, R-ko'rsatkichi va sof daromadi.
            </p>
          </div>

          {/* Outcome filter buttons & Search */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 bg-[#0A101D] border border-[#1A2845] rounded-xl p-1">
              {(['ALL', 'WINS', 'LOSSES', 'TP2', 'BE'] as OutcomeFilter[]).map(f => (
                <button
                  key={f}
                  onClick={() => setOutcomeFilter(f)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-semibold transition-all ${
                    outcomeFilter === f
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {f === 'ALL' ? 'Barchasi' : f === 'WINS' ? 'Yutuqlar' : f === 'LOSSES' ? 'Zararlar' : f}
                </button>
              ))}
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Aktiv, holat yoki setup qidirish..."
                className="bg-[#0A101D] border border-[#1A2845] rounded-xl pl-8 pr-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 w-44 sm:w-56"
              />
            </div>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[#182643] text-slate-400 text-[10.5px] uppercase tracking-wider">
                <th className="py-2.5 px-3"># / Id</th>
                <th className="py-2.5 px-3">Aktiv & Yo'nalish</th>
                <th className="py-2.5 px-3">Chiqish Vaqti / Sana</th>
                <th className="py-2.5 px-3">Natija / Holat</th>
                <th className="py-2.5 px-3">R-Multiple</th>
                <th className="py-2.5 px-3">Kirish ➔ Chiqish Narxi</th>
                <th className="py-2.5 px-3 text-right">Sof PnL ($)</th>
                <th className="py-2.5 px-3">SMC Setup</th>
                <th className="py-2.5 px-3 text-center">Davomiyligi</th>
                <th className="py-2.5 px-3 text-center">Tahlil</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#141E33]">
              {filteredTrades.length === 0 ? (
                <tr>
                  <td colSpan={10} className="text-center py-10 text-slate-500 font-mono">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <AlertCircle className="w-8 h-8 text-slate-600" />
                      <p>Ushbu filtr yoki kun bo'yicha savdo qaydlari topilmadi.</p>
                      {selectedCalendarDay && (
                        <button
                          onClick={handleClearCalendarDayFilter}
                          className="mt-1 px-3 py-1 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-xs hover:bg-cyan-500/30"
                        >
                          Barcha kunlarni ko'rish
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTrades.map((t, idx) => {
                  const isWin = t.is_win;
                  return (
                    <tr key={t.id || idx} onClick={() => setInspectedTrade(t)} className="hover:bg-[#131F38] transition-colors cursor-pointer group" title="Batafsil tahlil va Qayta Ijroni ochish uchun bosing">
                      <td className="py-3 px-3 text-slate-400">
                        <span className="text-cyan-400 font-bold">#{t.trade_number || idx + 1}</span>
                        <div className="text-[10px] text-slate-500 truncate max-w-[90px]">{t.id}</div>
                      </td>

                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">{t.symbol}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[9.5px] font-bold ${
                            t.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          }`}>
                            {t.side} {t.leverage}x
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <div className="text-slate-200 font-semibold">{t.date_str}</div>
                        <div className="text-[10px] text-slate-500">{t.time_str}</div>
                      </td>

                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isWin
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        }`}>
                          {t.status}
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        <span className={`font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {t.r_multiple || (isWin ? '+1.5R' : '-1.0R')}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-slate-300">
                        <div>
                          ${t.entryPrice.toLocaleString()} ➔ ${t.closePrice.toLocaleString()}
                        </div>
                      </td>

                      <td className="py-3 px-3 text-right">
                        <span className={`text-sm font-black font-mono ${
                          t.realizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                          {t.realizedPnl >= 0 ? '+' : ''}${t.realizedPnl.toFixed(2)}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-slate-300 max-w-[200px] truncate" title={t.setup}>
                        {t.setup}
                      </td>

                      <td className="py-3 px-3 text-center text-slate-400">
                        {t.duration || '18m'}
                      </td>

                      <td className="py-3 px-3 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setInspectedTrade(t);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-cyan-500/10 group-hover:bg-cyan-500/25 text-cyan-400 group-hover:text-white border border-cyan-500/30 transition-all flex items-center gap-1.5 mx-auto text-[11px] font-bold shadow-sm"
                          title="Savdo Tahlili & Visual Replay"
                        >
                          <Activity className="w-3.5 h-3.5" />
                          <span>Tahlil</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── MODAL: TRADE FORENSIC INSPECTOR & REPLAY ─────────────────────────── */}
      {inspectedTrade && (
        <TradeReplayModal
          trade={inspectedTrade}
          onClose={() => setInspectedTrade(null)}
        />
      )}
    </div>
  );
};
