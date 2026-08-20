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

export class IntelligenceService {
  /**
   * Fetch SMC and technical indicators analysis for a symbol
   */
  public static async fetchMarketAnalysis(symbol: string = 'BTC/USDT'): Promise<MarketAnalysisData | null> {
    try {
      const res = await fetch(`/api/v1/market/analysis?symbol=${encodeURIComponent(symbol)}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      if (json.status === 'SUCCESS') {
        return json;
      }
      return null;
    } catch (err) {
      console.error(`[IntelligenceService] fetchMarketAnalysis failed for ${symbol}:`, err);
      return null;
    }
  }
}
