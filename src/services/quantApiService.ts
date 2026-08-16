// Centralized Quant Engine API Service for APEX CopyTrade

export interface BacktestResponse {
  status: string;
  message?: string;
  data?: any;
  monteCarlo?: any;
}

export interface NewsArticleItem {
  id: string;
  title: string;
  source: string;
  summary: string;
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  sentimentScore: number;
  impactLevel: 'HIGH' | 'MEDIUM' | 'LOW';
  affectedAssets: string[];
  publishedAt: string;
  readTime: string;
}

export interface SystemMetricsData {
  cpuUsagePct: number;
  gpuUsagePct: number;
  ramUsedGb: number;
  ramTotalGb: number;
  diskUsedGb: number;
  diskTotalGb: number;
  latencyMs: number;
  dockerContainers: Array<{ name: string; status: string; cpu: string; mem: string }>;
  redisStatus: string;
  postgresStatus: string;
  celeryWorkers: number;
}

export interface MarketAnalysisData {
  status: string;
  symbol: string;
  current_price: number;
  regime: string;
  regimeScore: number;
  indicators: {
    ema20: number;
    ema50: number;
    ema200: number;
    rsi: number;
    atr: number;
  };
  smc: {
    orderBlockLevel: number;
    fvgLevel: number;
    swingHigh: number;
    swingLow: number;
  };
}

export async function fetchBacktestResults(forceRerun: boolean = false): Promise<BacktestResponse> {
  const url = `/api/v1/quant/backtest-results${forceRerun ? '?force_rerun=true' : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch backtest results');
  return res.json();
}

export async function fetchNewsFeed(): Promise<NewsArticleItem[]> {
  try {
    const res = await fetch('/api/v1/news/feed');
    if (res.ok) {
      const body = await res.json();
      return body.data || [];
    }
  } catch (e) {
    console.error('Error fetching news feed:', e);
  }
  return [];
}

export async function fetchJournalTrades(): Promise<any[]> {
  try {
    const res = await fetch('/api/v1/journal/trades');
    if (res.ok) {
      const body = await res.json();
      return body.trades || [];
    }
  } catch (e) {
    console.error('Error fetching journal trades:', e);
  }
  return [];
}

export async function fetchSystemMetrics(): Promise<SystemMetricsData | null> {
  try {
    const res = await fetch('/api/v1/system/metrics');
    if (res.ok) {
      return res.json();
    }
  } catch (e) {
    console.error('Error fetching system metrics:', e);
  }
  return null;
}

export async function fetchMarketAnalysis(symbol: string = 'BTC/USDT'): Promise<MarketAnalysisData | null> {
  try {
    const res = await fetch(`/api/v1/market/analysis?symbol=${encodeURIComponent(symbol)}`);
    if (res.ok) {
      return res.json();
    }
  } catch (e) {
    console.error('Error fetching market analysis:', e);
  }
  return null;
}

export async function postCopilotChat(prompt: string, symbol: string = 'BTC/USDT'): Promise<string> {
  try {
    const res = await fetch('/api/v1/ai/copilot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, symbol })
    });
    if (res.ok) {
      const data = await res.json();
      return data.reply || 'No response generated.';
    }
  } catch (e) {
    console.error('Error calling copilot API:', e);
  }
  return 'Error communicating with AI Copilot backend.';
}

export async function fetchEngineConfig(): Promise<any> {
  try {
    const res = await fetch('/api/v1/config');
    if (res.ok) return res.json();
  } catch (e) {
    console.error('Error fetching config:', e);
  }
  return null;
}

export async function updateEngineConfig(configData: any): Promise<boolean> {
  try {
    const res = await fetch('/api/v1/config/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configData)
    });
    return res.ok;
  } catch (e) {
    console.error('Error updating config:', e);
    return false;
  }
}
