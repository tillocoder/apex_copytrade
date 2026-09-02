export interface LivePortfolioData {
  initialCapital: number;
  currentEquity: number;
  realizedPnl: number;
  unrealizedPnl: number;
  totalTrades: number;
  winRate: number;
  openPositions?: any[];
  tradeHistory?: any[];
  liveEquityCurve?: Array<{ timestamp: string; equity: number }>;
}

export class PortfolioService {
  /**
   * Fetch real-time live equity, realized/unrealized PnL, and live equity curve
   */
  public static async fetchLivePortfolioEquity(): Promise<LivePortfolioData | null> {
    try {
      const res = await fetch('/api/v1/portfolio/live-equity');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      const raw = json.data || json;
      return {
        initialCapital: Number(raw.initialCapital) || 10000,
        currentEquity: Number(raw.currentEquity) || 10000,
        realizedPnl: Number(raw.realizedPnl) || 0,
        unrealizedPnl: Number(raw.unrealizedPnl) || 0,
        totalTrades: Number(raw.totalTrades ?? raw.closedTradesCount) || 0,
        winRate: Number(raw.winRate) || 0,
        openPositions: raw.openPositions || [],
        tradeHistory: Array.isArray(raw.tradeHistory) ? raw.tradeHistory : [],
        liveEquityCurve: Array.isArray(raw.liveEquityCurve) ? raw.liveEquityCurve : []
      };
    } catch (err) {
      console.error('[PortfolioService] fetchLivePortfolioEquity failed:', err);
      return null;
    }
  }
}
