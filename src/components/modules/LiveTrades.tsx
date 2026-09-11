import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { 
  TrendingUp, 
  TrendingDown, 
  ShieldAlert, 
  SlidersHorizontal, 
  Activity, 
  X, 
  RefreshCw, 
  History, 
  CheckCircle2, 
  AlertCircle, 
  ArrowUpRight, 
  ArrowDownRight,
  ShieldCheck,
  Zap,
  Target,
  Clock,
  Layers
} from 'lucide-react';
import { TradesService } from '../../services/tradesService';
import { PortfolioService, type LivePortfolioData } from '../../services/portfolioService';

export const LiveTrades: React.FC = () => {
  const { positions = [], setPositions, openCommandCenter } = useTerminal();
  
  // STRICT: Only genuine OPEN positions appear in the OPEN tab
  const rawPositions = Array.isArray(positions) ? positions : [];
  const safePositions = rawPositions.filter(p => p && String(p.status || 'OPEN').toUpperCase() === 'OPEN' && p.symbol === 'BTC/USDT');
  
  const [activeTab, setActiveTab] = useState<'OPEN' | 'HISTORY'>('OPEN');
  const [selectedPosId, setSelectedPosId] = useState<string>('');
  const [showEquityModal, setShowEquityModal] = useState<boolean>(false);
  const [liveEquityData, setLiveEquityData] = useState<any | null>(null);
  const [historyTrades, setHistoryTrades] = useState<any[]>([]);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const tradeHistory = historyTrades.length > 0
    ? historyTrades
    : (Array.isArray(liveEquityData?.tradeHistory) ? liveEquityData.tradeHistory : []);

  const activePosition = safePositions.find(p => p && p.id === selectedPosId) || safePositions[0] || null;

  const fetchLiveState = async () => {
    try {
      setIsRefreshing(true);
      const [equityData, livePos, histPos] = await Promise.all([
        PortfolioService.fetchLivePortfolioEquity(),
        TradesService.fetchLivePositions(),
        TradesService.fetchPositionsHistory()
      ]);
      if (equityData) setLiveEquityData(equityData);
      if (livePos && setPositions) setPositions(livePos);
      if (histPos && histPos.length > 0) {
        setHistoryTrades(histPos);
      } else if (equityData?.tradeHistory) {
        setHistoryTrades(equityData.tradeHistory);
      }
    } catch (err) {
      console.error("[LiveTrades] Failed to fetch live state:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLiveState();
    const interval = setInterval(fetchLiveState, 4000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (safePositions.length > 0 && !selectedPosId) {
      setSelectedPosId(safePositions[0].id);
    }
  }, [safePositions, selectedPosId]);

  const getLiveEquityChartOption = () => {
    const curve = Array.isArray(liveEquityData?.liveEquityCurve) ? liveEquityData.liveEquityCurve : [];

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#141A23',
        borderColor: '#2B384B',
        borderWidth: 1,
        textStyle: { color: '#F3F4F6', fontFamily: 'JetBrains Mono', fontSize: 11 }
      },
      grid: { left: '5%', right: '4%', top: '8%', bottom: '12%' },
      xAxis: {
        type: 'category',
        data: curve.map((c: any) => c?.timestamp || '00:00'),
        axisLine: { lineStyle: { color: '#2B384B' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: '#1A222E', type: 'dashed' } },
        axisLine: { show: false }
      },
      series: [
        {
          name: 'Equity ($)',
          type: 'line',
          smooth: true,
          data: curve.map((c: any) => Number(c?.equity) || 0),
          lineStyle: { color: '#10B981', width: 2.5 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(16, 185, 129, 0.25)' },
                { offset: 1, color: 'rgba(16, 185, 129, 0.0)' }
              ]
            }
          }
        }
      ]
    };
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#070B14] font-mono text-xs">
      {/* Module Navigation Bar */}
      <div className="h-10 bg-[#0A1224] border-b border-[#1C2E52] px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          {/* Tab buttons */}
          <div className="flex items-center space-x-1 bg-[#0C152B] p-0.5 rounded-lg border border-[#1C2E52]">
            <button
              onClick={() => setActiveTab('OPEN')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-bold transition-apex ${
                activeTab === 'OPEN'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/20'
                  : 'text-[#9CA3AF] hover:text-white hover:bg-[#0E1B38]'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>OPEN POSITIONS ({safePositions.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('HISTORY')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-bold transition-apex ${
                activeTab === 'HISTORY'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/20'
                  : 'text-[#9CA3AF] hover:text-white hover:bg-[#0E1B38]'
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
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 font-bold text-[10.5px] transition-apex"
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>REAL-TIME EQUITY CURVE</span>
          </button>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-[10.5px] text-[#9CA3AF]">
            <span>NAV Equity:</span>
            <span className="font-bold text-white font-mono tabular-nums">
              ${(Number(liveEquityData?.currentEquity) || 10000.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[#2B384B]">|</span>
            <span>Realized:</span>
            <span className={`font-bold font-mono tabular-nums ${(Number(liveEquityData?.realizedPnl) || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {(Number(liveEquityData?.realizedPnl) || 0) >= 0 ? '+' : ''}${(Number(liveEquityData?.realizedPnl) || 0).toFixed(2)}
            </span>
          </div>

          <button
            onClick={fetchLiveState}
            disabled={isRefreshing}
            className="p-1 rounded bg-[#0C152B] hover:bg-[#0E1B38] border border-[#1C2E52] text-[#9CA3AF] hover:text-white transition-apex"
            title="Refresh Live Data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {activeTab === 'OPEN' ? (
          /* OPEN POSITIONS VIEW */
          <>
            {/* Positions Table (Left 65%) */}
            <div className="flex-1 overflow-y-auto border-r border-[#1C2E52] bg-[#070B14]">
              {safePositions.length === 0 ? (
                <div className="p-14 text-center text-[#6B7280] space-y-2.5 font-sans">
                  <ShieldAlert className="w-9 h-9 text-amber-400/70 mx-auto" />
                  <div className="text-xs font-bold text-white uppercase tracking-wider">NO ACTIVE OPEN POSITIONS IN PORTFOLIO</div>
                  <div className="text-[11px] text-[#9CA3AF]">Engine is scanning live Binance M15 order flow for institutional SMC setups...</div>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-[#0A1224] border-b border-[#1C2E52] text-[9.5px] text-[#9CA3AF] uppercase tracking-wider font-semibold">
                      <th className="p-2.5">Account / Symbol</th>
                      <th className="p-2.5">Side / Lev</th>
                      <th className="p-2.5 text-right font-mono">Entry Price</th>
                      <th className="p-2.5 text-right font-mono">Mark Price</th>
                      <th className="p-2.5 text-right font-mono">Margin</th>
                      <th className="p-2.5 text-center font-mono">SL / TP</th>
                      <th className="p-2.5 text-right font-mono">Unrealized PnL</th>
                      <th className="p-2.5 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1A222E] font-mono text-[11px]">
                    {safePositions.map((p, idx) => {
                      if (!p) return null;
                      const isSelected = p.id === selectedPosId;
                      const isProfit = (p.unrealizedPnl || 0) >= 0;

                      return (
                        <tr
                          key={p.id || idx}
                          onClick={() => setSelectedPosId(p.id)}
                          className={`cursor-pointer transition-apex ${
                            isSelected 
                              ? 'bg-blue-500/10 border-l-2 border-cyan-500' 
                              : 'hover:bg-[#12171F]'
                          }`}
                        >
                          <td className="p-2.5 font-sans">
                            <div className="font-bold text-white text-xs">{p.symbol}</div>
                            <div className="text-[9px] text-[#6B7280] font-mono">{p.account}</div>
                          </td>
                          <td className="p-2.5">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              p.side === 'BUY' 
                                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' 
                                : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            }`}>
                              {p.side} {p.leverage}X
                            </span>
                          </td>
                          <td className="p-2.5 text-right text-white tabular-nums">
                            ${(p.entryPrice || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="p-2.5 text-right text-cyan-400 font-bold tabular-nums">
                            ${(p.currentPrice || p.entryPrice || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="p-2.5 text-right text-[#9CA3AF] tabular-nums">
                            ${(p.marginUsed || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="p-2.5 text-center text-[10px] tabular-nums">
                            <div className="text-rose-400">${(p.sl || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                            <div className="text-emerald-400">${(p.tp1 || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                          </td>
                          <td className="p-2.5 text-right">
                            <div className={`font-bold tabular-nums flex items-center justify-end space-x-1 ${
                              isProfit ? 'text-emerald-400' : 'text-rose-400'
                            }`}>
                              {isProfit ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                              <span>{isProfit ? '+' : ''}${(p.unrealizedPnl || 0).toFixed(2)}</span>
                            </div>
                            <div className={`text-[9px] tabular-nums ${isProfit ? 'text-emerald-500/80' : 'text-rose-500/80'}`}>
                              ({isProfit ? '+' : ''}{(p.unrealizedPnlPercent || 0).toFixed(2)}%)
                            </div>
                          </td>
                          <td className="p-2.5 text-center" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={() => openCommandCenter(p.id)}
                              className="px-2 py-1 bg-[#0C152B] hover:bg-[#0E1B38] border border-[#1C2D4E] rounded text-[10px] font-bold text-white transition-apex flex items-center space-x-1 mx-auto"
                            >
                              <SlidersHorizontal className="w-3 h-3 text-cyan-400" />
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

            {/* Position Inspector Right Panel (35%) */}
            <div className="w-[35%] overflow-y-auto bg-[#0A1224] p-4 space-y-3.5 font-sans text-xs border-l border-[#1C2E52]">
              {activePosition ? (
                <>
                  {/* Position Header Banner */}
                  <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg space-y-2 shadow-inner">
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-sm text-white flex items-center space-x-2">
                        <span>{activePosition.symbol}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${
                          activePosition.side === 'BUY' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        }`}>
                          {activePosition.side} {activePosition.leverage}X
                        </span>
                      </div>
                      <div className="text-[10px] font-mono text-[#9CA3AF] flex items-center gap-1">
                        <Clock className="w-3 h-3 text-[#6B7280]" />
                        <span>{activePosition.duration || 'Running'}</span>
                      </div>
                    </div>
                    <div className="text-[10px] text-[#6B7280] font-mono">
                      Executed: {activePosition.timeOpen || 'Live'} UTC
                    </div>
                  </div>

                  {/* AI Trade Rationale & Logic */}
                  <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg space-y-2">
                    <div className="text-[9.5px] font-bold text-[#9CA3AF] uppercase tracking-wider flex items-center space-x-1.5 font-mono">
                      <Activity className="w-3.5 h-3.5 text-purple-400" />
                      <span>Institutional AI Rationale</span>
                    </div>
                    <div className="text-xs text-[#E5E7EB] leading-relaxed">
                      {activePosition.aiExplanation || 'SMC Liquidity Sweep & Institutional Order Block Execution.'}
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t border-[#1C2E52] text-[10px] font-mono">
                      <span className="text-[#6B7280]">Confidence:</span>
                      <span className="text-purple-400 font-bold">{activePosition.aiConfidence || 88.5}%</span>
                    </div>
                  </div>

                  {/* Trailing & Dynamic SL Roadmap */}
                  <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg space-y-2 font-mono">
                    <div className="text-[9.5px] font-bold text-[#9CA3AF] uppercase tracking-wider font-mono flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Autonomous Roadmap</span>
                    </div>
                    <div className="space-y-1.5 text-[10.5px]">
                      <div className="flex justify-between p-1.5 bg-[#0A1224] rounded border border-[#1C2E52]">
                        <span className="text-[#9CA3AF]">1. Target TP1:</span>
                        <span className="text-emerald-400 font-bold tabular-nums">${(activePosition.tp1 || 0).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between p-1.5 bg-[#0A1224] rounded border border-[#1C2E52]">
                        <span className="text-[#9CA3AF]">2. Target TP2:</span>
                        <span className="text-emerald-400 font-bold tabular-nums">${(activePosition.tp2 || 0).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between p-1.5 bg-[#0A1224] rounded border border-[#1C2E52]">
                        <span className="text-[#9CA3AF]">3. Stop Loss:</span>
                        <span className="text-rose-400 font-bold tabular-nums">${(activePosition.sl || 0).toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="p-8 text-center text-[#6B7280]">Select a position from the table to inspect.</div>
              )}
            </div>
          </>
        ) : (
          /* POSITION HISTORY / CLOSED TRADES VIEW */
          <div className="flex-1 overflow-y-auto bg-[#070B14]">
            {tradeHistory.length === 0 ? (
              <div className="p-14 text-center text-[#6B7280] space-y-2.5 font-sans">
                <History className="w-9 h-9 text-[#4B5563] mx-auto" />
                <div className="text-xs font-bold text-white uppercase tracking-wider">NO HISTORICAL TRADES RECORDED</div>
                <div className="text-[11px] text-[#9CA3AF]">Closed positions will appear here with full execution forensics.</div>
              </div>
            ) : (
              <table className="w-full text-left border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="bg-[#0A1224] border-b border-[#1C2E52] text-[9.5px] text-[#9CA3AF] uppercase tracking-wider font-semibold font-sans">
                    <th className="p-2.5">Symbol / Side</th>
                    <th className="p-2.5 text-right font-mono">Entry Price</th>
                    <th className="p-2.5 text-right font-mono">Exit Price</th>
                    <th className="p-2.5 text-right font-mono">Size / Leverage</th>
                    <th className="p-2.5 text-center">Status</th>
                    <th className="p-2.5 text-right font-mono">Realized PnL</th>
                    <th className="p-2.5 text-right font-sans">Execution Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A222E]">
                  {tradeHistory.map((t: any, idx: number) => {
                    const pnl = Number(t.realizedPnl ?? t.realized_pnl ?? 0);
                    const isWin = pnl > 0;
                    const side = String(t.side || t.direction || 'BUY').toUpperCase();
                    const statusStr = String(t.status || 'CLOSED').toUpperCase();

                    return (
                      <tr key={t.id || idx} className="hover:bg-[#12171F] transition-apex">
                        <td className="p-2.5">
                          <div className="font-bold text-white flex items-center space-x-1.5 font-sans">
                            {isWin ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                            )}
                            <span>{t.symbol}</span>
                            <span className={`px-1 rounded text-[9px] font-bold ${
                              side === 'BUY' ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'
                            }`}>
                              {side}
                            </span>
                          </div>
                        </td>
                        <td className="p-2.5 text-right text-white font-mono tabular-nums">
                          ${(Number(t.entryPrice ?? t.entry_price) || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="p-2.5 text-right text-cyan-400 font-bold font-mono tabular-nums">
                          ${(Number(t.closePrice ?? t.exit_price ?? t.currentPrice) || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="p-2.5 text-right text-[#9CA3AF] font-mono tabular-nums">
                          {t.size} ({t.leverage || 2}X)
                        </td>
                        <td className="p-2.5 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            statusStr.includes('TP') || isWin ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                          }`}>
                            {statusStr}
                          </span>
                        </td>
                        <td className="p-2.5 text-right">
                          <div className={`font-bold font-mono tabular-nums ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isWin ? '+' : ''}${pnl.toFixed(2)}
                          </div>
                        </td>
                        <td className="p-2.5 text-right text-[10px] text-[#6B7280] font-sans">
                          {t.formatted_entry_time || t.timeOpen || 'Completed'}
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

      {/* Real-Time Paper Equity Modal */}
      {showEquityModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-4xl bg-[#0A1224] border border-[#1C2E52] rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="h-12 bg-[#0C152B] border-b border-[#1C2E52] px-5 flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-2 font-bold text-sm text-white font-sans">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <span>INSTITUTIONAL EQUITY CURVE</span>
              </div>
              <button
                onClick={() => setShowEquityModal(false)}
                className="p-1.5 rounded hover:bg-[#0E1B38] text-[#9CA3AF] hover:text-white transition-apex"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Equity KPIs */}
              <div className="grid grid-cols-4 gap-4">
                <div className="p-3 bg-[#0C152B] rounded-lg border border-[#1C2E52]">
                  <div className="text-[10px] text-[#6B7280] font-sans uppercase tracking-wider font-semibold">Starting Capital</div>
                  <div className="text-base font-bold text-white font-mono tabular-nums">$10,000.00</div>
                </div>
                <div className="p-3 bg-[#0C152B] rounded-lg border border-[#1C2E52]">
                  <div className="text-[10px] text-[#6B7280] font-sans uppercase tracking-wider font-semibold">Current NAV Equity</div>
                  <div className="text-base font-bold text-emerald-400 font-mono tabular-nums">
                    ${(Number(liveEquityData?.currentEquity) || 10000.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="p-3 bg-[#0C152B] rounded-lg border border-[#1C2E52]">
                  <div className="text-[10px] text-[#6B7280] font-sans uppercase tracking-wider font-semibold">Realized PnL</div>
                  <div className={`text-base font-bold font-mono tabular-nums ${(Number(liveEquityData?.realizedPnl) || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {(Number(liveEquityData?.realizedPnl) || 0) >= 0 ? '+' : ''}${(Number(liveEquityData?.realizedPnl) || 0).toFixed(2)}
                  </div>
                </div>
                <div className="p-3 bg-[#0C152B] rounded-lg border border-[#1C2E52]">
                  <div className="text-[10px] text-[#6B7280] font-sans uppercase tracking-wider font-semibold">Total Trades</div>
                  <div className="text-base font-bold text-cyan-400 font-mono tabular-nums">
                    {Number(liveEquityData?.totalTrades ?? liveEquityData?.closedTradesCount) || 0} Trades
                  </div>
                </div>
              </div>

              {/* Chart */}
              <div className="h-[280px] bg-[#0C152B] rounded-lg border border-[#1C2E52] p-2">
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
