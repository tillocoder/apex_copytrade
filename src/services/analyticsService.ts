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

export interface PerformanceAnalyticsData {
  status: string;
  totalTrades: number;
  winCount: number;
  lossCount: number;
  winRate: number;
  profitFactor: number;
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
  equityCurve: { timestamp: string; equity: number }[];
}

export class AnalyticsService {
  /**
   * Fetch quantitative performance metrics, session win-rate heatmap, and strategy forensics
   */
  public static async fetchAnalyticsPerformance(): Promise<PerformanceAnalyticsData | null> {
    try {
      const res = await fetch('/api/v1/analytics/performance');
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
}
