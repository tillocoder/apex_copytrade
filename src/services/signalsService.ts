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

  /**
   * Fetch autonomous hourly AI market discovery cards (BTCUSDT, ETHUSDT, SOLUSDT)
   */
  public static async fetchMarketDiscoveryCards(): Promise<Record<string, any>> {
    try {
      const res = await fetch('/api/v1/ai/market-discovery/cards');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      return json?.cards || {};
    } catch (err) {
      console.error('[SignalsService] fetchMarketDiscoveryCards failed:', err);
      return {};
    }
  }

  /**
   * Fetch autonomous AI signal history & paper trade performance
   */
  public static async fetchMarketDiscoveryHistory(limit: number = 50): Promise<any[]> {
    try {
      const res = await fetch(`/api/v1/ai/market-discovery/history?limit=${limit}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      return Array.isArray(json?.history) ? json.history : [];
    } catch (err) {
      console.error('[SignalsService] fetchMarketDiscoveryHistory failed:', err);
      return [];
    }
  }

  /**
   * Fetch performance analytics across confidence buckets & setups
   */
  public static async fetchMarketDiscoveryAnalytics(): Promise<any> {
    try {
      const res = await fetch('/api/v1/ai/market-discovery/analytics');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      return json?.analytics || null;
    } catch (err) {
      console.error('[SignalsService] fetchMarketDiscoveryAnalytics failed:', err);
      return null;
    }
  }

  /**
   * Fetch Historical Replay & Forensic Statistical Validation Report
   */
  public static async fetchReplayReport(): Promise<any> {
    try {
      const res = await fetch('/api/v1/ai/replay/report');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      return json;
    } catch (err) {
      console.error('[SignalsService] fetchReplayReport failed:', err);
      return null;
    }
  }

  /**
   * Trigger on-demand Historical Replay or Walk-Forward Analysis
   */
  public static async runReplay(params: {
    symbol?: string;
    days?: number;
    mode?: string;
    same_bar_policy?: string;
    walk_forward?: boolean;
  }): Promise<any> {
    try {
      const res = await fetch('/api/v1/ai/replay/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('[SignalsService] runReplay failed:', err);
      return null;
    }
  }

  /**
   * Fetch Replayed Historical Signals Log
   */
  public static async fetchReplaySignals(limit: number = 50, symbol?: string): Promise<any[]> {
    try {
      let url = `/api/v1/ai/replay/signals?limit=${limit}`;
      if (symbol) url += `&symbol=${encodeURIComponent(symbol)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      return Array.isArray(json?.signals) ? json.signals : [];
    } catch (err) {
      console.error('[SignalsService] fetchReplaySignals failed:', err);
      return [];
    }
  }

  /**
   * Trigger an on-demand hourly AI analysis cycle
   */
  public static async triggerMarketDiscoveryNow(): Promise<any> {
    try {
      const res = await fetch('/api/v1/ai/market-discovery/run-now', { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('[SignalsService] triggerMarketDiscoveryNow failed:', err);
      return null;
    }
  }
}

