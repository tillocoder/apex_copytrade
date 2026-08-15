import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { TrendingUp, ShieldAlert, SlidersHorizontal, Activity, X, RefreshCw, Lock } from 'lucide-react';

export const LiveTrades: React.FC = () => {
  const { positions = [], openCommandCenter, executePositionAction } = useTerminal();
  const safePositions = Array.isArray(positions) ? positions : [];
  
  const [selectedPosId, setSelectedPosId] = useState<string>(safePositions[0]?.id || '');
  const [showEquityModal, setShowEquityModal] = useState<boolean>(false);
  const [liveEquityData, setLiveEquityData] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const activePosition = safePositions.find(p => p && p.id === selectedPosId) || safePositions[0] || null;

  const fetchLiveEquity = async () => {
    try {
      setIsRefreshing(true);
      const res = await fetch('/api/v1/portfolio/live-equity');
      if (res.ok) {
        const json = await res.json();
        if (json.status === 'SUCCESS' && json.data) {
          setLiveEquityData(json.data);
        }
      }
    } catch (err) {
      console.error("Failed to fetch live equity:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLiveEquity();
    const interval = setInterval(fetchLiveEquity, 5000);
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
          <div className="flex items-center space-x-2 font-bold text-xs text-apex-text">
            <TrendingUp className="w-4 h-4 text-apex-accent" />
            <span>PAPER EXECUTION · REAL MARKET DATA ({safePositions.length})</span>
          </div>

          <button
            onClick={() => {
              setShowEquityModal(true);
              fetchLiveEquity();
            }}
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 font-bold text-[10px] transition-apex"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>VIEW REAL-TIME PAPER EQUITY</span>
          </button>
        </div>

        <div className="text-[10px] text-apex-muted">REAL MARKET PRICE · NO EXCHANGE ORDERS</div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Positions Table (Left 65%) */}
        <div className="flex-1 overflow-y-auto border-r border-apex-border bg-apex-bg">
          {safePositions.length === 0 ? (
            <div className="p-12 text-center text-apex-muted space-y-2 font-sans">
              <ShieldAlert className="w-8 h-8 text-apex-warning mx-auto" />
              <div className="text-xs">NO ACTIVE OPEN POSITIONS IN PORTFOLIO</div>
              <div className="text-[10px] text-apex-muted">Engine is scanning live Binance M15 order flow...</div>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-apex-surface border-b border-apex-border text-[10px] text-apex-muted uppercase">
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
                      className={`hover:bg-apex-hover cursor-pointer transition-apex ${
                        isSelected ? 'bg-apex-surface border-l-2 border-apex-accent' : idx % 2 === 1 ? 'bg-apex-bgSecondary/60' : 'bg-apex-bg'
                      }`}
                    >
                      <td className="p-2.5">
                        <div className="font-bold text-apex-text text-xs">{p.symbol || 'N/A'}</div>
                        <div className="text-[10px] text-apex-muted">{p.account || 'FTMO 10K LIVE'}</div>
                      </td>

                      <td className="p-2.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          p.side === 'BUY' ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' : 'bg-apex-danger/15 text-apex-danger border border-apex-danger/30'
                        }`}>
                          {p.side || 'BUY'} {p.leverage || 5}X
                        </span>
                      </td>

                      <td className="p-2.5 text-right font-bold text-apex-text">
                        ${(p.entryPrice || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>

                      <td className="p-2.5 text-right font-bold text-apex-accent">
                        ${(p.currentPrice || p.entryPrice || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>

                      <td className="p-2.5 text-right text-apex-textSecondary">
                        ${(p.marginUsed || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>

                      <td className="p-2.5 text-right text-[10px]">
                        <div className="text-apex-danger font-medium">${p.sl || 0}</div>
                        <div className="text-apex-success font-medium">${p.tp1 || 0}</div>
                      </td>

                      <td className="p-2.5 text-right">
                        <div className={`font-bold ${isProfit ? 'text-apex-success' : 'text-apex-danger'}`}>
                          {isProfit ? '+' : ''}${(p.unrealizedPnl || 0).toFixed(2)}
                        </div>
                        <div className={`text-[10px] ${isProfit ? 'text-apex-success' : 'text-apex-danger'}`}>
                          ({isProfit ? '+' : ''}{(p.unrealizedPnlPercent || 0)}%)
                        </div>
                      </td>

                      <td className="p-2.5 text-right space-x-1.5">
                        <button
                          onClick={(e) => { e.stopPropagation(); openCommandCenter(p.id); }}
                          className="px-2.5 py-1 rounded-md bg-apex-surface hover:bg-apex-hover border border-apex-accent text-apex-accent text-[10px] font-bold transition-apex flex items-center space-x-1 ml-auto"
                        >
                          <SlidersHorizontal className="w-3 h-3 text-apex-accent" />
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

        {/* Quick Position Overview Panel */}
        {activePosition && (
          <div className="w-96 bg-apex-bgSecondary p-4 overflow-y-auto space-y-4 shrink-0 font-sans">
            <div className="workstation-panel p-4 space-y-3 font-mono">
              <div className="flex justify-between items-center font-bold">
                <span className="text-apex-text text-sm">{activePosition.symbol || 'POSITION'} OVERVIEW</span>
                <span className="px-2 py-0.5 rounded bg-apex-surface border border-apex-accent text-apex-accent text-[9px] font-bold flex items-center gap-1">
                  <Lock className="w-3 h-3" /> AUTO EA ACTIVE
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                <div className="bg-apex-bg p-2.5 rounded-md border border-apex-border">
                  <div className="text-apex-muted text-[10px]">EXPECTED PROFIT</div>
                  <div className="text-apex-success font-bold">+${activePosition.expectedProfit || 0}</div>
                </div>
                <div className="bg-apex-bg p-2.5 rounded-md border border-apex-border">
                  <div className="text-apex-muted text-[10px]">MAX EXPECTED LOSS</div>
                  <div className="text-apex-danger font-bold">-${activePosition.expectedLoss || 0}</div>
                </div>
              </div>
            </div>

            {/* Read-Only EA Observer Mode */}
            <div className="p-3 bg-apex-surface rounded-md border border-apex-border text-[10px] font-mono space-y-1.5">
              <div className="font-bold text-apex-accent flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-apex-accent" /> READ-ONLY MONITORING MODE
              </div>
              <div className="text-apex-textSecondary text-[9px] leading-relaxed">
                All position management, trailing stops, break-even adjustments, and profit-taking are handled 100% autonomously by APEX M5 Quant Engine. Manual override disabled.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Live Real-Time Equity Curve Modal */}
      {showEquityModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-apex-surface border border-apex-border w-full max-w-4xl rounded-lg p-5 space-y-4 shadow-2xl font-mono">
            <div className="flex items-center justify-between border-b border-apex-border pb-3">
              <div className="flex items-center space-x-2">
                <Activity className="w-5 h-5 text-emerald-400" />
                <span className="font-bold text-sm text-apex-text">REAL-TIME LIVE PORTFOLIO EQUITY EXPANSION</span>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={fetchLiveEquity}
                  disabled={isRefreshing}
                  className="flex items-center space-x-1 text-xs text-apex-accent hover:text-apex-text transition-apex"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                  <span>REFRESH</span>
                </button>
                <button
                  onClick={() => setShowEquityModal(false)}
                  className="p-1 rounded text-apex-muted hover:text-apex-text transition-apex"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Key Live Equity Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-apex-bg p-3 rounded border border-apex-border">
                <div className="text-[10px] text-apex-muted">CURRENT LIVE EQUITY</div>
                <div className="text-lg font-bold text-emerald-400">
                  ${(liveEquityData?.currentEquity || 10000).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="bg-apex-bg p-3 rounded border border-apex-border">
                <div className="text-[10px] text-apex-muted">UNREALIZED PNL</div>
                <div className={`text-lg font-bold ${(liveEquityData?.unrealizedPnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}>
                  {(liveEquityData?.unrealizedPnl || 0) >= 0 ? '+' : ''}${(liveEquityData?.unrealizedPnl || 0).toFixed(2)}
                </div>
              </div>
              <div className="bg-apex-bg p-3 rounded border border-apex-border">
                <div className="text-[10px] text-apex-muted">REALIZED PNL</div>
                <div className={`text-lg font-bold ${(liveEquityData?.realizedPnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}>
                  {(liveEquityData?.realizedPnl || 0) >= 0 ? '+' : ''}${(liveEquityData?.realizedPnl || 0).toFixed(2)}
                </div>
              </div>
              <div className="bg-apex-bg p-3 rounded border border-apex-border">
                <div className="text-[10px] text-apex-muted">WIN RATE ({liveEquityData?.totalTrades || 0} Trades)</div>
                <div className="text-lg font-bold text-apex-accent">
                  {liveEquityData?.winRate || 100}%
                </div>
              </div>
            </div>

            {/* ECharts Live Equity Curve */}
            <div className="h-80 w-full bg-apex-bg rounded p-2 border border-apex-border">
              <ReactECharts option={getLiveEquityChartOption()} style={{ height: '100%', width: '100%' }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
