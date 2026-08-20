export interface JournalTradeItem {
  trade_id?: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  entryPrice?: number;
  exit_price: number;
  exitPrice?: number;
  pnl: number;
  net_pnl?: number;
  bars_held?: number;
  reason?: string;
  entry_time?: string;
  exit_time?: string;
}

export class JournalService {
  /**
   * Fetch closed trade logs from ledger
   */
  public static async fetchJournalTrades(): Promise<JournalTradeItem[]> {
    try {
      const res = await fetch('/api/v1/journal/trades');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      if (json.status === 'SUCCESS' && Array.isArray(json.trades)) {
        return json.trades;
      }
      return [];
    } catch (err) {
      console.error('[JournalService] fetchJournalTrades failed:', err);
      return [];
    }
  }
}
