export interface LivePortfolioData {
  initialCapital: number;
  currentEquity: number;
  realizedPnl: number;
  unrealizedPnl: number;
  totalTrades: number;
  winRate: number;
  openPositions?: any[];
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
      if (json.status === 'SUCCESS' && json.data) {
        return {
          initialCapital: Number(json.data.initialCapital) || 0,
          currentEquity: Number(json.data.currentEquity) || 0,
          realizedPnl: Number(json.data.realizedPnl) || 0,
          unrealizedPnl: Number(json.data.unrealizedPnl) || 0,
          totalTrades: Number(json.data.totalTrades) || 0,
          winRate: Number(json.data.winRate) || 0,
          openPositions: json.data.openPositions || [],
          liveEquityCurve: json.data.liveEquityCurve || []
        };
      }
      return null;
    } catch (err) {
      console.error('[PortfolioService] fetchLivePortfolioEquity failed:', err);
      return null;
    }
  }
}
