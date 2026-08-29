import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { TrendingUp, TrendingDown, ShieldAlert, SlidersHorizontal, Activity, X, RefreshCw, Lock, History, CheckCircle2, AlertCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { TradesService } from '../../services/tradesService';
import { PortfolioService, type LivePortfolioData } from '../../services/portfolioService';

export const LiveTrades: React.FC = () => {
  const { positions = [], setPositions, openCommandCenter } = useTerminal();
  const safePositions = Array.isArray(positions) ? positions : [];
  
  const [activeTab, setActiveTab] = useState<'OPEN' | 'HISTORY'>('OPEN');
  const [selectedPosId, setSelectedPosId] = useState<string>(safePositions[0]?.id || '');
  const [showEquityModal, setShowEquityModal] = useState<boolean>(false);
  const [liveEquityData, setLiveEquityData] = useState<any | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const activePosition = safePositions.find(p => p && p.id === selectedPosId) || safePositions[0] || null;
  const tradeHistory = Array.isArray(liveEquityData?.tradeHistory) ? liveEquityData.tradeHistory : [];

  const fetchLiveState = async () => {
    try {
      setIsRefreshing(true);
      const [equityData, livePos] = await Promise.all([
        PortfolioService.fetchLivePortfolioEquity(),
        TradesService.fetchLivePositions()
      ]);
      if (equityData) setLiveEquityData(equityData);
      if (livePos && setPositions) setPositions(livePos);
    } catch (err) {
      console.error("[LiveTrades] Failed to fetch live state:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLiveState();
    const interval = setInterval(fetchLiveState, 5000);
    return () => clearInterval(interval);
  }, []);

  const getLiveEquityChartOption = () => {
    const curve = Array.isArray(liveEquityData?.liveEquityCurve) ? liveEquityData.liveEquityCurve : [];

    return {
      backgroundColor: '#151A21',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1B222C',
        borderColor: '#2C3643',
        borderWidth: 1,
        textStyle: { color: '#F5F7FA', fontFamily: 'JetBrains Mono', fontSize: 11 }
      },
      grid: { left: '5%', right: '4%', top: '8%', bottom: '12%' },
      xAxis: {
        type: 'category',
        data: curve.map((c: any) => c?.timestamp || '00:00'),
        axisLine: { lineStyle: { color: '#2C3643' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: '#242D39', type: 'dashed' } },
        axisLine: { show: false }
      },
      series: [
        {
          name: 'Real-Time Portfolio Equity ($)',
          type: 'line',
          smooth: true,
          data: curve.map((c: any) => Number(c?.equity) || 0),
          lineStyle: { color: '#10B981', width: 2.5 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
                { offset: 1, color: 'rgba(16, 185, 129, 0.0)' }
              ]
            }
          }
        }
      ]
    };
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs">
      {/* Module Title Header */}
      <div className="h-10 bg-apex-surface border-b border-apex-border px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          {/* Tab buttons */}
          <div className="flex items-center space-x-1 bg-apex-bg p-0.5 rounded border border-apex-border">
            <button
              onClick={() => setActiveTab('OPEN')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-bold transition-all ${
                activeTab === 'OPEN'
                  ? 'bg-apex-accent text-apex-bg shadow-sm'
                  : 'text-apex-muted hover:text-apex-text'
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              <span>OPEN POSITIONS ({safePositions.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('HISTORY')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-bold transition-all ${
                activeTab === 'HISTORY'
                  ? 'bg-apex-accent text-apex-bg shadow-sm'
                  : 'text-apex-muted hover:text-apex-text'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>POSITION HISTORY ({tradeHistory.length})</span>
            </button>
          </div>

          <button
            onClick={() => {
              setShowEquityModal(true);
              fetchLiveState();
            }}
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 font-bold text-[10px] transition-apex"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>VIEW REAL-TIME PAPER EQUITY</span>
          </button>
        </div>

        <div className="flex items-center space-x-3 text-[10px] text-apex-muted">
          <button
            onClick={fetchLiveState}
            disabled={isRefreshing}
            className="flex items-center space-x-1 px-2 py-0.5 rounded bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border text-apex-text"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>REFRESH</span>
          </button>
          <span>REAL MARKET PRICE • BINANCE DATA FEED</span>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {activeTab === 'OPEN' ? (
          /* OPEN POSITIONS VIEW */
          <>
            {/* Positions Table (Left 65%) */}
            <div className="flex-1 overflow-y-auto border-r border-apex-border bg-apex-bg">
              {safePositions.length === 0 ? (
                <div className="p-12 text-center text-apex-muted space-y-2 font-sans">
                  <ShieldAlert className="w-8 h-8 text-apex-warning mx-auto" />
                  <div className="text-xs font-bold text-apex-text">NO ACTIVE OPEN POSITIONS IN PORTFOLIO</div>
                  <div className="text-[10px] text-apex-muted">Engine is scanning live Binance M15 order flow for high probability SMC setups...</div>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-apex-surface border-b border-apex-border text-[10px] text-apex-muted uppercase tracking-wider">
                      <th className="p-2.5">Account / Symbol</th>
                      <th className="p-2.5">Side / Lev</th>
                      <th className="p-2.5 text-right font-mono">Entry Price</th>
                      <th className="p-2.5 text-right font-mono">Mark Price</th>
                      <th className="p-2.5 text-right font-mono">Margin</th>
                      <th className="p-2.5 text-right font-mono">SL / TP</th>
                      <th className="p-2.5 text-right font-mono">Unrealized PnL</th>
                      <th className="p-2.5 text-right">Command Center</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-apex-border/40 font-mono">
                    {safePositions.map((p, idx) => {
                      if (!p) return null;
                      const isSelected = p.id === selectedPosId;
                      const isProfit = (p.unrealizedPnl || 0) >= 0;

                      return (
                        <tr
                          key={p.id || idx}
                          onClick={() => setSelectedPosId(p.id)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-apex-accent/10 border-l-2 border-apex-accent' : 'hover:bg-apex-surfaceHover/50'
                          }`}
                        >
                          <td className="p-2.5">
                            <div className="font-bold text-apex-text">{p.symbol}</div>
                            <div className="text-[9px] text-apex-muted uppercase">{p.account || 'PAPER EXECUTION • REAL BINANCE DATA'}</div>
                          </td>
                          <td className="p-2.5">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              p.side === 'BUY'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}>
                              {p.side} {p.leverage}X
                            </span>
                          </td>
                          <td className="p-2.5 text-right font-bold text-apex-text">
                            ${Number(p.entryPrice || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="p-2.5 text-right font-bold text-apex-accent">
                            ${Number(p.currentPrice || p.entryPrice || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="p-2.5 text-right text-apex-text">
                            ${Number(p.marginUsed || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="p-2.5 text-right">
                            <div className="text-rose-400 text-[10px]">
                              ${Number(p.sl || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </div>
                            <div className="text-emerald-400 text-[10px]">
                              ${Number(p.tp1 || p.tp2 || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </div>
                          </td>
                          <td className="p-2.5 text-right">
                            <div className={`font-bold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {isProfit ? '+' : ''}${Number(p.unrealizedPnl || 0).toFixed(2)}
                            </div>
                            <div className={`text-[9px] ${isProfit ? 'text-emerald-500/80' : 'text-rose-500/80'}`}>
                              ({isProfit ? '+' : ''}{Number(p.unrealizedPnlPercent || 0).toFixed(2)}%)
                            </div>
                          </td>
                          <td className="p-2.5 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                if (openCommandCenter) openCommandCenter(p.id);
                              }}
                              className="px-2.5 py-1 rounded bg-apex-surface hover:bg-apex-accent hover:text-apex-bg text-apex-text border border-apex-border text-[10px] font-bold transition-all inline-flex items-center space-x-1"
                            >
                              <SlidersHorizontal className="w-3 h-3" />
                              <span>INSPECT</span>
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Position Summary Sidebar (Right 35%) */}
            {activePosition && (
              <div className="w-[360px] bg-apex-surface/40 p-4 border-l border-apex-border flex flex-col space-y-4 overflow-y-auto">
                <div className="flex items-center justify-between border-b border-apex-border pb-2">
                  <div className="font-bold text-xs text-apex-text flex items-center space-x-2">
                    <span>{activePosition.symbol} OVERVIEW</span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[9px] bg-apex-accent/10 border border-apex-accent/30 text-apex-accent font-bold">
                    AUTO RA ACTIVE
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-apex-surface p-2.5 rounded border border-apex-border">
                    <div className="text-[9px] text-apex-muted">EXPECTED PROFIT</div>
                    <div className="text-sm font-bold text-emerald-400">
                      +${Number(activePosition.expectedProfit || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-apex-surface p-2.5 rounded border border-apex-border">
                    <div className="text-[9px] text-apex-muted">MAX EXPECTED LOSS</div>
                    <div className="text-sm font-bold text-rose-400">
                      -${Number(activePosition.expectedLoss || 0).toFixed(2)}
                    </div>
                  </div>
                </div>

                <div className="bg-apex-surface/80 p-3 rounded border border-apex-border/60 space-y-2 text-[11px]">
                  <div className="text-apex-accent font-bold text-xs flex items-center space-x-1">
                    <Lock className="w-3.5 h-3.5" />
                    <span>READ-ONLY MONITORING MODE</span>
                  </div>
                  <p className="text-apex-muted text-[10px] leading-relaxed">
                    All position management, trailing stops, break-even adjustments, and profit-taking are handled 100% autonomously by APEX Quant Engine.
                  </p>
                </div>
              </div>
            )}
          </>
        ) : (
          /* POSITION HISTORY / CLOSED TRADES VIEW */
          <div className="flex-1 overflow-y-auto bg-apex-bg">
            {tradeHistory.length === 0 ? (
              <div className="p-12 text-center text-apex-muted space-y-2 font-sans">
                <History className="w-8 h-8 text-apex-muted mx-auto" />
                <div className="text-xs font-bold text-apex-text">NO HISTORICAL TRADES RECORDED</div>
                <div className="text-[10px] text-apex-muted">Closed positions will appear here with full execution forensics.</div>
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-apex-surface border-b border-apex-border text-[10px] text-apex-muted uppercase tracking-wider">
                    <th className="p-2.5">Symbol / Side</th>
                    <th className="p-2.5 text-right font-mono">Entry Price</th>
                    <th className="p-2.5 text-right font-mono">Exit Price</th>
                    <th className="p-2.5 text-right font-mono">Size / Leverage</th>
                    <th className="p-2.5 text-center">Status</th>
                    <th className="p-2.5 text-right font-mono">Realized PnL</th>
                    <th className="p-2.5 text-right">Time Open / Close</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-apex-border/40 font-mono">
                  {tradeHistory.map((t: any, idx: number) => {
                    const pnl = Number(t.realizedPnl ?? t.realized_pnl ?? 0);
                    const isWin = pnl > 0;
                    const side = String(t.side || t.direction || 'BUY').toUpperCase();
                    const statusStr = String(t.status || 'CLOSED').toUpperCase();

                    return (
                      <tr key={t.id || idx} className="hover:bg-apex-surfaceHover/40 transition-colors">
                        <td className="p-2.5">
                          <div className="font-bold text-apex-text flex items-center space-x-1.5">
                            {isWin ? (
                              <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <ArrowDownRight className="w-3.5 h-3.5 text-rose-400" />
                            )}
                            <span>{t.symbol || 'BTC/USDT'}</span>
                          </div>
                          <div className="text-[9px]">
                            <span className={`font-bold ${side === 'BUY' || side === 'LONG' ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {side}
                            </span>
                            <span className="text-apex-muted ml-1">{t.leverage || 2}X</span>
                          </div>
                        </td>
                        <td className="p-2.5 text-right font-bold text-apex-text">
                          ${Number(t.entryPrice ?? t.entry_price ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="p-2.5 text-right font-bold text-apex-accent">
                          ${Number(t.closePrice ?? t.mark_price ?? t.entryPrice ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="p-2.5 text-right text-apex-muted">
                          <div>{Number(t.size || 0.1).toFixed(3)}</div>
                          <div className="text-[9px] text-apex-muted">${Number(t.marginUsed ?? t.margin ?? 500).toFixed(0)} Margin</div>
                        </td>
                        <td className="p-2.5 text-center">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                            statusStr.includes('TP')
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              : statusStr.includes('SL')
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                              : 'bg-apex-surface text-apex-muted border border-apex-border'
                          }`}>
                            {statusStr}
                          </span>
                        </td>
                        <td className="p-2.5 text-right">
                          <div className={`font-bold text-xs ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isWin ? '+' : ''}${pnl.toFixed(2)}
                          </div>
                          <div className={`text-[9px] ${isWin ? 'text-emerald-500/80' : 'text-rose-500/80'}`}>
                            {Number(t.unrealizedPnlPercent ?? t.pnl_pct ?? 0).toFixed(2)}%
                          </div>
                        </td>
                        <td className="p-2.5 text-right text-apex-muted text-[10px]">
                          <div>{t.formatted_entry_time || t.timeOpen || '2026-08-28'}</div>
                          <div className="text-[9px] text-apex-muted/70">{t.duration || '0h 15m'}</div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* Real-time Equity Curve Modal */}
      {showEquityModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-apex-surface border border-apex-border rounded-lg w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col">
            <div className="p-3 border-b border-apex-border flex items-center justify-between bg-apex-bg">
              <div className="flex items-center space-x-2 font-bold text-xs text-apex-text">
                <Activity className="w-4 h-4 text-emerald-400" />
                <span>INSTITUTIONAL REAL-TIME EQUITY CURVE</span>
              </div>
              <button
                onClick={() => setShowEquityModal(false)}
                className="p-1 rounded hover:bg-apex-surface text-apex-muted hover:text-apex-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div className="grid grid-cols-4 gap-3 text-center">
                <div className="bg-apex-bg p-2.5 rounded border border-apex-border">
                  <div className="text-[9px] text-apex-muted">INITIAL CAPITAL</div>
                  <div className="text-sm font-bold text-apex-text">
                    ${Number(liveEquityData?.initialCapital || 10000).toLocaleString()}
                  </div>
                </div>
                <div className="bg-apex-bg p-2.5 rounded border border-apex-border">
                  <div className="text-[9px] text-apex-muted">REALIZED PNL</div>
                  <div className={`text-sm font-bold ${(liveEquityData?.realizedPnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {(liveEquityData?.realizedPnl || 0) >= 0 ? '+' : ''}${Number(liveEquityData?.realizedPnl || 0).toFixed(2)}
                  </div>
                </div>
                <div className="bg-apex-bg p-2.5 rounded border border-apex-border">
                  <div className="text-[9px] text-apex-muted">CLOSED TRADES</div>
                  <div className="text-sm font-bold text-apex-text">
                    {liveEquityData?.closedTradesCount || 0}
                  </div>
                </div>
                <div className="bg-apex-bg p-2.5 rounded border border-apex-border">
                  <div className="text-[9px] text-apex-muted">WIN COUNT</div>
                  <div className="text-sm font-bold text-emerald-400">
                    {liveEquityData?.winCount || 0}
                  </div>
                </div>
              </div>

              <div className="h-64 bg-apex-bg rounded border border-apex-border p-2">
                <ReactECharts option={getLiveEquityChartOption()} style={{ height: '100%', width: '100%' }} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveTrades;
