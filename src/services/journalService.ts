export interface JournalTrade {
  id: string;
  date: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  riskPct: number;
  entryPrice: number;
  exitPrice: number;
  sl?: number | null;
  tp?: number | null;
  emotion: string;
  reason?: string;
  lesson?: string;
  pnlPct: number;
  isWin: boolean;
  createdAt: number;
  // Compatibility fields
  trade_id?: string;
  side?: 'BUY' | 'SELL';
  entry_price?: number;
  exit_price?: number;
  pnl?: number;
  net_pnl?: number;
}

// Backward compatibility alias
export type JournalTradeItem = JournalTrade;

export interface JournalStats {
  totalTrades: number;
  winRate: number;
  totalPnlPct: number;
  avgRR: string;
  currentStreak: string;
  wins: number;
  losses: number;
}

export interface NewTradeInput {
  date: string;
  symbol: string;
  direction: 'Long' | 'Short' | 'LONG' | 'SHORT';
  riskPct: number;
  entryPrice: number;
  exitPrice: number;
  sl?: number | null;
  tp?: number | null;
  emotion?: string;
  reason?: string;
  lesson?: string;
}

const LOCAL_STORAGE_PREFIX = 'apex_journal_user_';

const calculateLocalStats = (trades: JournalTrade[]): JournalStats => {
  const total = trades.length;
  if (total === 0) {
    return {
      totalTrades: 0,
      winRate: 0.0,
      totalPnlPct: 0.0,
      avgRR: '—',
      currentStreak: '—',
      wins: 0,
      losses: 0
    };
  }

  const wins = trades.filter(t => t.pnlPct > 0).length;
  const losses = trades.filter(t => t.pnlPct < 0).length;
  const winRate = Number(((wins / total) * 100).toFixed(1));
  const totalPnlPct = Number(trades.reduce((acc, t) => acc + (t.pnlPct || 0), 0).toFixed(2));

  // Average R:R
  const rrValues: number[] = [];
  trades.forEach(t => {
    if (t.sl && t.sl > 0 && t.entryPrice > 0 && t.exitPrice > 0) {
      if (t.direction === 'LONG' && t.entryPrice > t.sl) {
        const risk = t.entryPrice - t.sl;
        const reward = t.exitPrice - t.entryPrice;
        if (risk > 0 && reward > 0) rrValues.push(reward / risk);
      } else if (t.direction === 'SHORT' && t.sl > t.entryPrice) {
        const risk = t.sl - t.entryPrice;
        const reward = t.entryPrice - t.exitPrice;
        if (risk > 0 && reward > 0) rrValues.push(reward / risk);
      }
    }
  });

  const avgRR = rrValues.length > 0 ? `1:${(rrValues.reduce((a, b) => a + b, 0) / rrValues.length).toFixed(1)}` : '—';

  // Streak
  let streakStr = '—';
  if (trades.length > 0) {
    const firstPnl = trades[0].pnlPct;
    if (firstPnl > 0) {
      let count = 0;
      for (const t of trades) {
        if (t.pnlPct > 0) count++;
        else break;
      }
      streakStr = `${count} g'alaba`;
    } else if (firstPnl < 0) {
      let count = 0;
      for (const t of trades) {
        if (t.pnlPct < 0) count++;
        else break;
      }
      streakStr = `${count} mag'lubiyat`;
    } else {
      streakStr = '0 durang';
    }
  }

  return {
    totalTrades: total,
    winRate,
    totalPnlPct,
    avgRR,
    currentStreak: streakStr,
    wins,
    losses
  };
};

export class JournalService {
  /**
   * Helper to normalize user identifier
   */
  public static normalizeUserId(rawId?: string): string {
    if (!rawId) return 'usr_apex_01';
    return rawId.trim().toLowerCase().replace(/[@.]/g, '_') || 'usr_apex_01';
  }

  /**
   * Get cached local trades for snappy instant rendering
   */
  public static getLocalTrades(userId: string): JournalTrade[] {
    try {
      const key = `${LOCAL_STORAGE_PREFIX}${this.normalizeUserId(userId)}`;
      const saved = localStorage.getItem(key);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (e) {
      console.warn('[JournalService] LocalStorage read failed:', e);
    }
    return [];
  }

  /**
   * Save trades into local storage cache
   */
  public static setLocalTrades(userId: string, trades: JournalTrade[]) {
    try {
      const key = `${LOCAL_STORAGE_PREFIX}${this.normalizeUserId(userId)}`;
      localStorage.setItem(key, JSON.stringify(trades));
    } catch (e) {
      console.warn('[JournalService] LocalStorage write failed:', e);
    }
  }

  /**
   * Fetch user isolated trades from backend with LocalStorage fallback
   */
  public static async fetchUserTrades(userId: string = 'usr_apex_01'): Promise<{ trades: JournalTrade[]; stats: JournalStats }> {
    const normId = this.normalizeUserId(userId);
    try {
      const res = await fetch(`/api/v1/journal/trades?user_id=${encodeURIComponent(normId)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'SUCCESS' && Array.isArray(data.trades)) {
          const trades: JournalTrade[] = data.trades.map((t: any) => ({
            ...t,
            id: t.id || t.trade_id || `tr_${Date.now()}`,
            direction: (t.direction || (t.side === 'BUY' ? 'LONG' : 'SHORT')).toUpperCase(),
            pnlPct: Number(t.pnlPct ?? t.pnl ?? t.net_pnl ?? 0),
            isWin: t.isWin ?? ((Number(t.pnlPct ?? t.pnl ?? 0)) > 0)
          }));
          this.setLocalTrades(normId, trades);
          const stats: JournalStats = data.stats || calculateLocalStats(trades);
          return { trades, stats };
        }
      }
    } catch (err) {
      console.warn('[JournalService] fetchUserTrades network fallback to local storage:', err);
    }

    // Fallback to local storage
    const cached = this.getLocalTrades(normId);
    return {
      trades: cached,
      stats: calculateLocalStats(cached)
    };
  }

  /**
   * Add a new trade for user
   */
  public static async addUserTrade(userId: string, payload: NewTradeInput): Promise<{ trade: JournalTrade; stats: JournalStats }> {
    const normId = this.normalizeUserId(userId);
    const directionUpper = (payload.direction || 'LONG').toUpperCase() as 'LONG' | 'SHORT';
    const isLong = directionUpper === 'LONG';

    const entry = Number(payload.entryPrice);
    const exitP = Number(payload.exitPrice);
    let pnlPct = 0;
    if (entry > 0) {
      pnlPct = isLong 
        ? Number((((exitP - entry) / entry) * 100).toFixed(2))
        : Number((((entry - exitP) / entry) * 100).toFixed(2));
    }

    const localNewTrade: JournalTrade = {
      id: `tr_${Date.now()}`,
      date: payload.date || new Date().toISOString().slice(0, 10),
      symbol: (payload.symbol || 'BTC/USDT').toUpperCase().trim(),
      direction: directionUpper,
      riskPct: Number(payload.riskPct) || 1.0,
      entryPrice: entry,
      exitPrice: exitP,
      sl: payload.sl ? Number(payload.sl) : null,
      tp: payload.tp ? Number(payload.tp) : null,
      emotion: payload.emotion || 'Xotirjam',
      reason: payload.reason || '',
      lesson: payload.lesson || '',
      pnlPct,
      isWin: pnlPct > 0,
      createdAt: Date.now()
    };

    try {
      const res = await fetch('/api/v1/journal/trades', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: normId,
          date: localNewTrade.date,
          symbol: localNewTrade.symbol,
          direction: localNewTrade.direction,
          riskPct: localNewTrade.riskPct,
          entryPrice: localNewTrade.entryPrice,
          exitPrice: localNewTrade.exitPrice,
          sl: localNewTrade.sl,
          tp: localNewTrade.tp,
          emotion: localNewTrade.emotion,
          reason: localNewTrade.reason,
          lesson: localNewTrade.lesson
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.status === 'SUCCESS' && data.trade) {
          const updatedCached = [data.trade, ...this.getLocalTrades(normId).filter(t => t.id !== data.trade.id)];
          this.setLocalTrades(normId, updatedCached);
          return { trade: data.trade, stats: data.stats || calculateLocalStats(updatedCached) };
        }
      }
    } catch (err) {
      console.warn('[JournalService] addUserTrade network error, falling back locally:', err);
    }

    // Local update fallback
    const current = this.getLocalTrades(normId);
    const updated = [localNewTrade, ...current];
    this.setLocalTrades(normId, updated);
    return {
      trade: localNewTrade,
      stats: calculateLocalStats(updated)
    };
  }

  /**
   * Delete specific trade
   */
  public static async deleteUserTrade(userId: string, tradeId: string): Promise<{ success: boolean; stats: JournalStats }> {
    const normId = this.normalizeUserId(userId);
    try {
      const res = await fetch(`/api/v1/journal/trades/${encodeURIComponent(tradeId)}?user_id=${encodeURIComponent(normId)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        const data = await res.json();
        const updated = this.getLocalTrades(normId).filter(t => t.id !== tradeId);
        this.setLocalTrades(normId, updated);
        return { success: true, stats: data.stats || calculateLocalStats(updated) };
      }
    } catch (err) {
      console.warn('[JournalService] deleteUserTrade network fallback:', err);
    }

    const updated = this.getLocalTrades(normId).filter(t => t.id !== tradeId);
    this.setLocalTrades(normId, updated);
    return { success: true, stats: calculateLocalStats(updated) };
  }

  /**
   * Clear all trades for a user
   */
  public static async clearAllUserTrades(userId: string): Promise<{ success: boolean; stats: JournalStats }> {
    const normId = this.normalizeUserId(userId);
    try {
      const res = await fetch(`/api/v1/journal/trades-clear-all?user_id=${encodeURIComponent(normId)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        const data = await res.json();
        this.setLocalTrades(normId, []);
        return { success: true, stats: data.stats || calculateLocalStats([]) };
      }
    } catch (err) {
      console.warn('[JournalService] clearAllUserTrades network fallback:', err);
    }

    this.setLocalTrades(normId, []);
    return { success: true, stats: calculateLocalStats([]) };
  }

  /**
   * Backward compatibility method
   */
  public static async fetchJournalTrades(): Promise<JournalTrade[]> {
    const res = await this.fetchUserTrades('usr_apex_01');
    return res.trades;
  }
}
