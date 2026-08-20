import type { Signal } from '../types';

export interface KlineCandle {
  timestamp: number;
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  isUp: boolean;
}

export interface KlineResponse {
  status: 'SUCCESS' | 'ERROR';
  symbol?: string;
  message?: string;
  data: KlineCandle[];
}

export class SignalsService {
  /**
   * Fetch latest active AI signals
   */
  public static async fetchLiveSignals(): Promise<Signal[]> {
    try {
      const res = await fetch('/api/v1/signals/live');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    } catch (err) {
      console.error('[SignalsService] fetchLiveSignals failed:', err);
      return [];
    }
  }

  /**
   * Fetch AI signal history (past 2 months)
   */
  public static async fetchSignalsHistory(): Promise<Signal[]> {
    try {
      const res = await fetch('/api/v1/signals/history');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    } catch (err) {
      console.error('[SignalsService] fetchSignalsHistory failed:', err);
      return [];
    }
  }

  /**
   * Fetch Binance M15 klines for a specific symbol
   */
  public static async fetchMarketKlines(
    symbol: string,
    interval: string = '15m',
    limit: number = 200,
    endTime?: number
  ): Promise<KlineCandle[]> {
    try {
      let url = `/api/v1/market/klines?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=${limit}`;
      if (endTime) url += `&end_time=${endTime}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json: KlineResponse = await res.json();
      if (json.status === 'SUCCESS' && Array.isArray(json.data)) {
        return json.data;
      }
      return [];
    } catch (err) {
      console.error(`[SignalsService] fetchMarketKlines failed for ${symbol}:`, err);
      return [];
    }
  }
}
