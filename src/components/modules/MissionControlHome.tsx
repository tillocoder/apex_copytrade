import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { ApexCandleChart } from '../common/ApexCandleChart';
import { SignalsService } from '../../services/signalsService';
import { TradesService } from '../../services/tradesService';
import { 
  TrendingUp, 
  TrendingDown, 
  Terminal, 
  Flame, 
  Sparkles,
  Bot,
  Bell,
  ShieldCheck,
  Activity,
  DollarSign,
  BarChart2,
  ChevronRight,
  Target
} from 'lucide-react';

export const MissionControlHome: React.FC = () => {
  const { 
    selectedSymbol, 
    setSelectedSymbol, 
    tickers, 
    positions, 
    setPositions,
    signals, 
    setSignals,
    logs, 
    addLog,
    notificationPermission,
    requestWebNotifications,
    propAccounts,
    backtest
  } = useTerminal();

  const [logFilter, setLogFilter] = useState<string>('ALL');

  useEffect(() => {
    const fetchHomeData = async () => {
      try {
        const [liveSigs, livePos] = await Promise.all([
          SignalsService.fetchLiveSignals(),
          TradesService.fetchLivePositions()
        ]);
        if (liveSigs.length > 0 && setSignals) setSignals(liveSigs);
        if (livePos && setPositions) setPositions(livePos);
      } catch (err) {
        console.error('[MissionControlHome] Error fetching data:', err);
      }
    };

    fetchHomeData();
    const interval = setInterval(fetchHomeData, 8000);
    return () => clearInterval(interval);
  }, []);

  const currentTicker = tickers.find(t => t.symbol === selectedSymbol) || tickers[0];
  const activePosition = positions.find(p => p.symbol === selectedSymbol);

  const filteredLogs = logFilter === 'ALL' 
    ? logs 
    : logs.filter(l => l.category.toUpperCase() === logFilter);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#080A0D] font-sans text-xs">
      {/* Main Workspace Area (3 Columns: Market Watch, Chart, AI Radar) */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Column: Market Watch Panel */}
        <div className="w-60 bg-[#0D1117] border-r border-[#222C3A] flex flex-col shrink-0 font-mono">
          <div className="p-2.5 border-b border-[#222C3A] bg-[#141A23] flex justify-between items-center font-medium text-xs">
            <span className="flex items-center gap-1.5 text-white font-bold font-sans">
              <Flame className="w-3.5 h-3.5 text-amber-400" /> MARKET WATCH
            </span>
            <span className="text-[9.5px] text-[#6B7280]">LIVE</span>
          </div>

          {/* Ticker List */}
          <div className="flex-1 overflow-y-auto divide-y divide-[#1A222E]">
            {tickers.map((t) => {
              const isSelected = t.symbol === selectedSymbol;
              return (
                <div
                  key={t.symbol}
                  onClick={() => setSelectedSymbol(t.symbol)}
                  className={`p-2.5 hover:bg-[#141A23] cursor-pointer transition-apex flex items-center justify-between ${
                    isSelected ? 'bg-blue-500/10 border-l-2 border-blue-500' : ''
                  }`}
                >
                  <div>
                    <div className="font-bold text-white text-xs">{t.symbol}</div>
                    <div className="text-[9px] text-[#6B7280]">Vol: ${(t.volume24h / 1e9).toFixed(2)}B</div>
                  </div>

                  <div className="text-right">
                    <div className="font-bold text-white text-xs tabular-nums">${t.price.toLocaleString()}</div>
                    <div className={`text-[10px] font-medium tabular-nums flex items-center justify-end ${
                      t.change24h >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                      {t.change24h >= 0 ? '+' : ''}{t.change24h.toFixed(2)}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Stats at Bottom of Left Panel */}
          <div className="p-2.5 bg-[#141A23] border-t border-[#222C3A] text-[10px] space-y-1">
            <div className="flex justify-between text-[#9CA3AF]">
              <span>Active Signals:</span>
              <strong className="text-purple-400 font-mono">{signals.length}</strong>
            </div>
            <div className="flex justify-between text-[#9CA3AF]">
              <span>Open Trades:</span>
              <strong className="text-emerald-400 font-mono">{positions.length}</strong>
            </div>
          </div>
        </div>

        {/* Center Column: High-Performance Live Trading Chart */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#080A0D]">
          <div className="flex-1 overflow-hidden relative">
            <ApexCandleChart 
              symbol={selectedSymbol} 
              position={activePosition}
              className="w-full h-full"
            />
          </div>
        </div>

        {/* Right Column: AI Signal Stream & Log Radar */}
        <div className="w-80 bg-[#0D1117] border-l border-[#222C3A] flex flex-col shrink-0">
          
          {/* Signal Radar Header */}
          <div className="p-2.5 border-b border-[#222C3A] bg-[#141A23] flex justify-between items-center text-xs font-mono">
            <span className="flex items-center gap-1.5 font-bold text-white font-sans">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" /> AI SIGNALS
            </span>
            <span className="text-[9.5px] px-1.5 py-0.2 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30">
              {signals.length} ACTIVE
            </span>
          </div>

          {/* Signal Cards */}
          <div className="p-2 space-y-2 overflow-y-auto max-h-[48%] border-b border-[#222C3A]">
            {signals.length === 0 ? (
              <div className="p-6 text-center text-[#6B7280] text-[11px]">
                No active signals right now. Skaner faol...
              </div>
            ) : (
              signals.map((sig) => (
                <div 
                  key={sig.id}
                  onClick={() => setSelectedSymbol(sig.symbol)}
                  className="p-2.5 bg-[#141A23] hover:bg-[#1A222E] border border-[#222C3A] rounded-lg cursor-pointer transition-apex space-y-1.5"
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-1.5">
                      <span className="font-bold text-white text-xs">{sig.symbol}</span>
                      <span className={`px-1 rounded text-[9px] font-bold ${
                        sig.side === 'BUY' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'
                      }`}>
                        {sig.side}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-purple-400 font-bold">
                      {sig.confidence ?? sig.aiScore ?? 85}%
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-1 font-mono text-[9.5px] text-[#9CA3AF] tabular-nums">
                    <div>E: <strong className="text-white">${sig.entry?.toLocaleString()}</strong></div>
                    <div>SL: <strong className="text-rose-400">${sig.sl?.toLocaleString()}</strong></div>
                    <div>TP1: <strong className="text-emerald-400">${sig.tp1?.toLocaleString()}</strong></div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Execution Log Terminal */}
          <div className="p-2.5 border-b border-[#222C3A] bg-[#141A23] flex justify-between items-center text-xs font-mono">
            <span className="flex items-center gap-1.5 font-bold text-white font-sans">
              <Terminal className="w-3.5 h-3.5 text-blue-400" /> EXECUTION LOGS
            </span>
            <div className="flex gap-1 text-[9px]">
              {['ALL', 'SYSTEM', 'QUANT'].map(f => (
                <button
                  key={f}
                  onClick={() => setLogFilter(f)}
                  className={`px-1.5 py-0.2 rounded font-bold ${
                    logFilter === f ? 'bg-blue-600 text-white' : 'text-[#6B7280] hover:text-white'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 p-2 overflow-y-auto font-mono text-[10px] space-y-1 bg-[#080A0D]">
            {filteredLogs.slice(-25).map((l, i) => (
              <div key={i} className="text-[#9CA3AF] leading-tight flex items-start space-x-1.5">
                <span className="text-[#6B7280] shrink-0">{l.timestamp?.split(' ')[1] || '00:00'}</span>
                <span className="text-white break-words">{l.message}</span>
              </div>
            ))}
          </div>

        </div>

      </div>
    </div>
  );
};

export default MissionControlHome;
