import type { Position } from '../types';

export class TradesService {
  /**
   * Fetch live open positions with real-time mark prices and PnL
   */
  public static async fetchLivePositions(): Promise<Position[]> {
    try {
      const res = await fetch('/api/v1/positions/live');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      if (!Array.isArray(data)) return [];

      return data.map((p: any) => ({
        id: String(p?.id || ''),
        account: String(p?.account || 'PAPER EXECUTION · REAL MARKET DATA'),
        symbol: String(p?.symbol || ''),
        side: p?.side === 'SELL' ? ('SELL' as const) : ('BUY' as const),
        entryPrice: Number(p?.entryPrice) || 0,
        currentPrice: Number(p?.currentPrice) || 0,
        size: Number(p?.size) || 0,
        leverage: Number(p?.leverage) || 0,
        marginUsed: Number(p?.marginUsed) || 0,
        unrealizedPnl: Number(p?.unrealizedPnl) || 0,
        unrealizedPnlPercent: Number(p?.unrealizedPnlPercent) || 0,
        sl: Number(p?.sl) || 0,
        tp1: Number(p?.tp1) || 0,
        tp2: Number(p?.tp2) || 0,
        tp3: Number(p?.tp3) || 0,
        breakEvenPrice: Number(p?.breakEvenPrice) || 0,
        trailingStopActive: Boolean(p?.trailingStopActive),
        trailingDistancePct: Number(p?.trailingDistancePct) || 0,
        atr: Number(p?.atr) || 0,
        riskPercent: Number(p?.riskPercent) || 0,
        rewardPercent: Number(p?.rewardPercent) || 0,
        expectedProfit: Number(p?.expectedProfit) || 0,
        expectedLoss: Number(p?.expectedLoss) || 0,
        commission: Number(p?.commission) || 0,
        fundingFee: Number(p?.fundingFee) || 0,
        swapFees: Number(p?.swapFees) || 0,
        liquidationPrice: Number(p?.liquidationPrice) || 0,
        duration: String(p?.duration || ''),
        timeOpen: String(p?.timeOpen || ''),
        aiExplanation: String(p?.aiExplanation || p?.ai_explanation || ''),
        aiConfidence: Number(p?.aiConfidence ?? p?.ai_confidence) || 0,
        aiRecommendation: p?.aiRecommendation || 'HOLD',
        expectedNextMove: String(p?.expectedNextMove || ''),
        reason: String(p?.reason || ''),
        pattern: String(p?.pattern || ''),
        volumeProfile: String(p?.volumeProfile || ''),
        trendStatus: String(p?.trendStatus || ''),
        orderFlowAnalysis: String(p?.orderFlowAnalysis || ''),
        liquidityAnalysis: String(p?.liquidityAnalysis || ''),
        positionHealthScore: Number(p?.positionHealthScore) || 0,
        executionQualityScore: Number(p?.executionQualityScore) || 0,
        status: p?.status === 'PARTIAL' ? ('PARTIAL' as const) : p?.status === 'CLOSED' ? ('CLOSED' as const) : ('OPEN' as const),
        timeline: p?.timeline || []
      })).filter(p => p.id && p.symbol);
    } catch (err) {
      console.error('[TradesService] fetchLivePositions failed:', err);
      return [];
    }
  }

  /**
   * Panic close all open positions
   */
  public static async panicCloseAll(): Promise<boolean> {
    try {
      const res = await fetch('/api/v1/positions/panic-close', { method: 'POST' });
      return res.ok;
    } catch (err) {
      console.error('[TradesService] panicCloseAll failed:', err);
      return false;
    }
  }

  /**
   * Reset all positions and restore $10,000 equity baseline
   */
  public static async resetAllPositions(): Promise<boolean> {
    try {
      const res = await fetch('/api/v1/positions/reset', { method: 'POST' });
      return res.ok;
    } catch (err) {
      console.error('[TradesService] resetAllPositions failed:', err);
      return false;
    }
  }
}
