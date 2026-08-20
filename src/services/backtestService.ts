import type { BacktestResult } from '../types';

export interface BacktestResponse {
  status: string;
  message?: string;
  data?: Partial<BacktestResult>;
  monteCarlo?: {
    passRate: number;
    riskOfRuin: number;
    medianMaxDD: number;
    percentile95MaxDD: number;
  };
}

export class BacktestService {
  /**
   * Fetch real quant engine backtest results, with optional force re-run trigger
   */
  public static async fetchBacktestResults(forceRerun: boolean = false): Promise<BacktestResponse> {
    const url = `/api/v1/quant/backtest-results${forceRerun ? '?force_rerun=true' : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return res.json();
  }
}
