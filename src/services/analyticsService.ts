export interface PerformanceAnalyticsData {
  status: string;
  bestSession: string;
  bestDay: string;
  profitFactor: number;
  expectancy: string;
  winRate: number;
  totalTrades: number;
  heatmapData: number[][];
}

export class AnalyticsService {
  /**
   * Fetch performance metrics and session win-rate heatmap
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
