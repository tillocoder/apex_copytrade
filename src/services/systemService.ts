import type { ServerMetric, SystemHealth } from '../types';

export interface RawHealthResponse {
  status: string;
  exchange_status: string;
  exchange_latency_ms: number;
  database_status: string;
  database_latency_ms: number;
  websocket_status: string;
  python_engine_status: string;
  ai_engine_status: string;
}

export class SystemService {
  /**
   * Fetch server hardware metrics (CPU, RAM, Disk, Containers)
   */
  public static async fetchSystemMetrics(): Promise<ServerMetric | null> {
    try {
      const res = await fetch('/api/v1/system/metrics');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      if (json && typeof json.cpuUsagePct === 'number') {
        return json;
      }
      return null;
    } catch (err) {
      console.error('[SystemService] fetchSystemMetrics failed:', err);
      return null;
    }
  }

  /**
   * Fetch system engine health
   */
  public static async fetchSystemHealth(): Promise<SystemHealth | null> {
    const startedAt = performance.now();
    try {
      const res = await fetch('/api/v1/system/health');
      const latency = Math.round(performance.now() - startedAt);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data: RawHealthResponse = await res.json();
      return {
        vpsStatus: data.status === 'HEALTHY' ? 'ONLINE' : 'DEGRADED',
        vpsLatency: latency,
        exchangeApiStatus: data.exchange_status === 'CONNECTED' ? 'CONNECTED' : 'DISCONNECTED',
        exchangeLatency: Number(data.exchange_latency_ms) || 0,
        dbStatus: data.database_status === 'HEALTHY' || data.database_status === 'FILE_STATE' ? 'HEALTHY' : 'ERROR',
        dbLatency: Number(data.database_latency_ms) || 0,
        wsStatus: data.websocket_status === 'STREAMING' ? 'STREAMING' : 'PAUSED',
        wsLatency: 0,
        pythonEngineStatus: ['RUNNING', 'OPTIMIZING'].includes(data.python_engine_status) ? 'RUNNING' : 'PAUSED',
        aiEngineStatus: data.ai_engine_status === 'ACTIVE' ? 'ACTIVE' : 'CALIBRATING'
      };
    } catch (err) {
      console.error('[SystemService] fetchSystemHealth failed:', err);
      return null;
    }
  }
}
