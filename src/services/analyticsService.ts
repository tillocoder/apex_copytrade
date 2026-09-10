export interface StrategyBreakdown {
  setup: string;
  trades: number;
  winRate: number;
  profitFactor: number;
  avgRR: number;
}

export interface SymbolBreakdown {
  symbol: string;
  trades: number;
  winRate: number;
  pnl: number;
  profitFactor: number;
}

export interface RDistributionItem {
  r: string;
  count: number;
  pct: number;
  type: 'WIN' | 'LOSS' | 'BREAKEVEN';
}

export interface AvailableDayItem {
  date: string;
  display: string;
  shortDisplay: string;
  tradesCount: number;
  winsCount: number;
  lossesCount: number;
  winRate: number;
  pnl: number;
}

export interface AvailableMonthItem {
  month: string;
  display: string;
  shortDisplay: string;
  tradesCount: number;
  winsCount: number;
  lossesCount: number;
  winRate: number;
  pnl: number;
}

export interface ForensicTradeItem {
  id: string;
  trade_number?: number;
  signal_id?: string;
  symbol: string;
  side: string;
  entryPrice: number;
  closePrice: number;
  realizedPnl: number;
  tp1_realized_pnl?: number;
  status: string;
  is_win: boolean;
  duration: string;
  r_multiple: string;
  date_str: string;
  month_str: string;
  time_str: string;
  formatted_date: string;
  setup: string;
  leverage: number;
  marginUsed: number;
  aiConfidence?: number;
  stopLoss?: number;
  sl?: number;
  tp1?: number;
  tp2?: number;
  tp1_hit?: boolean;
  trailingStopActive?: boolean;
  riskAmount?: number;
  riskPercent?: number;
  size?: number;
  original_size?: number;
  entry_timestamp?: number;
  exit_timestamp?: number;
  events?: Array<{ timestamp: string; event: string; price: number; note?: string }>;
}

export interface PerformanceAnalyticsData {
  status: string;
  rangeType: string;
  activeRangeLabel: string;
  selectedDate: string;
  selectedMonth: string;
  availableDays: AvailableDayItem[];
  availableMonths: AvailableMonthItem[];
  totalTrades: number;
  winCount: number;
  lossCount: number;
  beCount: number;
  winRate: number;
  profitFactor: number;
  grossProfit: number;
  grossLoss: number;
  sharpeRatio: number;
  maxDrawdownPct: number;
  recoveryFactor: number;
  netPnl: number;
  expectancy: string;
  expectancyValue: number;
  bestSession: string;
  bestSessionSub: string;
  bestDay: string;
  bestDaySub: string;
  avgWin: number;
  avgLoss: number;
  longWinRate: number;
  shortWinRate: number;
  heatmapData: number[][];
  strategyBreakdown: StrategyBreakdown[];
  symbolBreakdown: SymbolBreakdown[];
  rDistribution: RDistributionItem[];
  equityCurve: { 
    timestamp: string; 
    equity: number; 
    trade_pnl?: number; 
    is_win?: boolean;
    symbol?: string;
    status?: string;
  }[];
  trades: ForensicTradeItem[];
}

export interface AnalyticsFilterParams {
  rangeType?: 'all' | 'today' | 'yesterday' | 'week' | 'month' | 'this_month' | 'last_month' | 'day' | 'custom';
  date?: string;
  month?: string;
  startDate?: string;
  endDate?: string;
  symbol?: string;
}

export class AnalyticsService {
  /**
   * Fetch quantitative performance metrics, session win-rate heatmap, and forensic trade records
   * filtered dynamically by range (day, month, all, custom) and asset.
   */
  public static async fetchAnalyticsPerformance(params?: AnalyticsFilterParams): Promise<PerformanceAnalyticsData | null> {
    try {
      const queryParts: string[] = [];
      if (params?.rangeType) queryParts.push(`range_type=${encodeURIComponent(params.rangeType)}`);
      if (params?.date) queryParts.push(`date=${encodeURIComponent(params.date)}`);
      if (params?.month) queryParts.push(`month=${encodeURIComponent(params.month)}`);
      if (params?.startDate) queryParts.push(`start_date=${encodeURIComponent(params.startDate)}`);
      if (params?.endDate) queryParts.push(`end_date=${encodeURIComponent(params.endDate)}`);
      if (params?.symbol) queryParts.push(`symbol=${encodeURIComponent(params.symbol)}`);

      const queryString = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
      const res = await fetch(`/api/v1/analytics/performance${queryString}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      if (json.status === 'SUCCESS') {
        return json;
      }
      return null;
    } catch (err) {
      console.error('[AnalyticsService] fetchAnalyticsPerformance failed:', err);
      return null;
    }
  }

  static async fetchTradeKlines(
    symbol: string = 'BTC/USDT',
    interval: string = '15m',
    startTime?: number,
    endTime?: number,
    limit: number = 60
  ): Promise<Array<{ time: number; open: number; high: number; low: number; close: number; volume: number }>> {
    try {
      const params = new URLSearchParams({ symbol, interval, limit: String(limit) });
      if (startTime) params.append('startTime', String(Math.floor(startTime)));
      if (endTime) params.append('endTime', String(Math.floor(endTime)));

      const res = await fetch(`/api/v1/market/klines?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('[AnalyticsService] fetchTradeKlines fallback:', err);
      return [];
    }
  }
}
