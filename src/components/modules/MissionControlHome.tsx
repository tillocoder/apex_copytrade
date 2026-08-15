import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { getProfessionalChartOption, type CandleData } from '../../utils/chartDataGenerator';
import { 
  fetchRealKlines, 
  subscribeBinanceLivePrices, 
  updateCandlesWithLiveTick 
} from '../../services/marketDataService';
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
  BarChart2
} from 'lucide-react';

export const MissionControlHome: React.FC = () => {
  const { 
    selectedSymbol, 
    setSelectedSymbol, 
    tickers, 
    positions, 
    signals, 
    logs, 
    addLog,
    notificationPermission,
    requestWebNotifications,
    propAccounts,
    backtest
  } = useTerminal();

  const [timeframe, setTimeframe] = useState<'M1' | 'M5' | 'M15' | 'H1' | 'H4' | 'D1'>('M5');
  const [logFilter, setLogFilter] = useState<string>('ALL');
  const [overlaySMC, setOverlaySMC] = useState<boolean>(true);
  const [overlayAI, setOverlayAI] = useState<boolean>(true);
  const [realCandles, setRealCandles] = useState<CandleData[]>([]);
  const zoomRef = React.useRef<{ start: number; end: number }>({ start: 45, end: 95 });

  const currentTicker = tickers.find(t => t.symbol === selectedSymbol) || tickers[0];
  const activePosition = positions.find(p => p.symbol === selectedSymbol);

  // Fetch REAL Binance Candlestick Data & Subscribe to Live Realtime Ticks
  useEffect(() => {
    zoomRef.current = { start: 45, end: 95 };
    fetchRealKlines(selectedSymbol, timeframe, 200).then(data => {
      if (data.length > 0) {
        setRealCandles(data);
      }
    });

    const unsubscribe = subscribeBinanceLivePrices((sym, price) => {
      if (sym === selectedSymbol) {
        setRealCandles(prev => updateCandlesWithLiveTick(prev, sym, selectedSymbol, price));
      }
    });

    return () => unsubscribe();
  }, [selectedSymbol, timeframe]);

  const handleDataZoom = (e: any) => {
    let s: number | undefined;
    let end: number | undefined;
    if (e.batch && e.batch[0]) {
      s = e.batch[0].start;
      end = e.batch[0].end;
    } else if (e.start !== undefined && e.end !== undefined) {
      s = e.start;
      end = e.end;
    }
    if (s !== undefined && end !== undefined) {
      zoomRef.current = { start: s, end: end };
    }
  };

  // ECharts Candlestick & Volume Profile Options
  const getChartOption = () => {
    return getProfessionalChartOption({
      symbol: selectedSymbol,
      basePrice: currentTicker.price,
      overlaySMC,
      overlayAI,
      activePosition,
      realCandles,
      zoomStart: zoomRef.current.start,
      zoomEnd: zoomRef.current.end
    });
  };

  const filteredLogs = logFilter === 'ALL' 
    ? logs 
    : logs.filter(l => l.category.toUpperCase() === logFilter);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs">
      {/* Main Workspace Area (3 Columns: Market Watch, Chart, AI Radar) */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Column: Market Watch Panel */}
        <div className="w-64 bg-apex-bgSecondary border-r border-apex-border flex flex-col shrink-0 font-mono">
          <div className="p-2.5 border-b border-apex-border bg-apex-surface flex justify-between items-center font-medium text-xs">
            <span className="flex items-center gap-1.5 text-apex-text font-bold">
              <Flame className="w-3.5 h-3.5 text-apex-accent" /> MARKET WATCH
            </span>
            <span className="text-[10px] text-apex-muted">REAL-TIME</span>
          </div>

          {/* Ticker List */}
          <div className="flex-1 overflow-y-auto divide-y divide-apex-border/40">
            {tickers.map((t) => {
              const isSelected = t.symbol === selectedSymbol;
              return (
                <div
                  key={t.symbol}
                  onClick={() => setSelectedSymbol(t.symbol)}
                  className={`p-2.5 hover:bg-apex-hover cursor-pointer transition-apex flex items-center justify-between ${
                    isSelected ? 'bg-apex-surface border-l-2 border-apex-accent' : ''
                  }`}
                >
                  <div>
                    <div className="font-bold text-apex-text text-xs">{t.symbol}</div>
                    <div className="text-[10px] text-apex-muted">Vol: ${(t.volume24h / 1e9).toFixed(2)}B</div>
                  </div>

                  <div className="text-right">
                    <div className="font-bold text-apex-text text-xs">${t.price.toLocaleString()}</div>
                    <div className={`text-[10px] font-medium flex items-center justify-end ${
                      t.change24h >= 0 ? 'text-apex-success' : 'text-apex-danger'
                    }`}>
                      {t.change24h >= 0 ? '+' : ''}{t.change24h}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Order Book Sentiment */}
          <div className="p-2.5 border-t border-apex-border bg-apex-surface space-y-1.5 text-[11px]">
            <div className="flex justify-between items-center text-apex-muted">
              <span>FUNDING RATE</span>
              <span className="text-apex-muted font-mono font-medium">—</span>
            </div>
            <div className="flex justify-between items-center text-apex-muted">
              <span>OPEN INTEREST</span>
              <span className="text-apex-muted font-mono font-medium">—</span>
            </div>
            <div className="flex justify-between items-center text-apex-muted">
              <span>ORDER BOOK BIAS</span>
              <span className="text-apex-muted font-mono font-medium">NOT CONNECTED</span>
            </div>
          </div>
        </div>

        {/* Center Column: Professional Charting & Position Bar */}
        <div className="flex-1 flex flex-col border-r border-apex-border bg-apex-bgSecondary overflow-hidden">
          
          {/* Chart Control Bar */}
          <div className="h-10 bg-apex-surface border-b border-apex-border px-3 flex items-center justify-between font-mono shrink-0">
            <div className="flex items-center space-x-3">
              <span className="font-bold text-sm text-apex-text">{selectedSymbol}</span>
              <span className="text-apex-accent font-medium text-xs">${currentTicker.price.toLocaleString()}</span>

              {/* Timeframe Selectors */}
              <div className="flex space-x-1 pl-2 border-l border-apex-border">
                {(['M1', 'M5', 'M15', 'H1', 'H4', 'D1'] as const).map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={`px-2 py-0.5 rounded-md text-[11px] font-medium transition-apex ${
                      timeframe === tf 
                        ? 'bg-apex-hover text-apex-accent border border-apex-border' 
                        : 'text-apex-muted hover:text-apex-text hover:bg-apex-hover'
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>

            {/* Overlays Toggle */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setOverlaySMC(!overlaySMC)}
                className={`px-2.5 py-1 rounded-md text-[10px] font-medium border transition-apex ${
                  overlaySMC 
                    ? 'bg-apex-hover border-apex-accent text-apex-accent' 
                    : 'border-apex-border text-apex-muted hover:text-apex-text'
                }`}
              >
                SMC LEVELS
              </button>
              <button
                onClick={() => setOverlayAI(!overlayAI)}
                className={`px-2.5 py-1 rounded-md text-[10px] font-medium border transition-apex ${
                  overlayAI 
                    ? 'bg-apex-ai/15 border-apex-ai text-apex-ai' 
                    : 'border-apex-border text-apex-muted hover:text-apex-text'
                }`}
              >
                AI SIGNALS
              </button>
            </div>
          </div>

          {/* ECharts Candlestick Canvas */}
          <div className="flex-1 w-full h-full relative bg-apex-bgSecondary">
            <ReactECharts 
              option={getChartOption()} 
              notMerge={false}
              lazyUpdate={true}
              onEvents={{ datazoom: handleDataZoom }}
              style={{ height: '100%', width: '100%' }} 
            />

            {/* Active Position Overlay Box */}
            {activePosition && (
              <div className="absolute top-4 right-4 bg-apex-surface/90 backdrop-blur border border-apex-border p-3 rounded-panel shadow-panel font-mono space-y-1 text-xs">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-apex-text font-bold">ACTIVE POSITION</span>
                  <span className="bg-apex-success/15 text-apex-success border border-apex-success/30 px-1.5 py-0.2 rounded text-[10px] font-bold">{activePosition.side} 20X</span>
                </div>
                <div className="text-[11px] text-apex-textSecondary">Entry: <strong className="text-apex-text">${activePosition.entryPrice}</strong></div>
                <div className="text-[11px] text-apex-textSecondary">Unrealized PnL: <strong className="text-apex-success">+${activePosition.unrealizedPnl} ({activePosition.unrealizedPnlPercent}%)</strong></div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: AI Decision Center */}
        <div className="w-80 bg-apex-bgSecondary flex flex-col shrink-0 font-mono overflow-y-auto">
          <div className="p-2.5 border-b border-apex-border bg-apex-surface flex justify-between items-center font-medium">
            <span className="flex items-center gap-1.5 text-apex-ai font-bold text-xs">
              <Bot className="w-4 h-4 text-apex-ai" /> AI DECISION RADAR
            </span>
            <span className="text-[10px] bg-apex-ai/15 border border-apex-ai/30 text-apex-ai px-1.5 py-0.5 rounded font-mono">CONFIDENCE 96%</span>
          </div>

          <div className="p-3 space-y-3">
            {/* BUY / SELL Probability Gauge */}
            <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-2">
              <div className="flex justify-between items-center text-xs font-bold">
                <span className="text-apex-success flex items-center gap-1"><TrendingUp className="w-3.5 h-3.5" /> BUY 88.5%</span>
                <span className="text-apex-danger flex items-center gap-1"><TrendingDown className="w-3.5 h-3.5" /> SELL 11.5%</span>
              </div>
              <div className="w-full h-1.5 bg-apex-danger/30 rounded-full overflow-hidden flex">
                <div className="h-full bg-apex-success" style={{ width: '88.5%' }} />
              </div>
            </div>

            {/* AI Suggested Execution Parameters */}
            <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-2 text-xs">
              <div className="text-[10px] text-apex-ai font-semibold uppercase tracking-wider flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-apex-ai" /> AI EXECUTION SUGGESTION
              </div>
              
              <div className="flex justify-between py-1 border-b border-apex-border/50">
                <span className="text-apex-muted">ENTRY:</span>
                <span className="font-bold text-apex-text">${(currentTicker.price * 0.998).toFixed(2)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-apex-border/50">
                <span className="text-apex-muted">STOP LOSS (SL):</span>
                <span className="font-bold text-apex-danger">${(currentTicker.price * 0.988).toFixed(2)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-apex-border/50">
                <span className="text-apex-muted">TAKE PROFIT (TP1):</span>
                <span className="font-bold text-apex-success">${(currentTicker.price * 1.025).toFixed(2)}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-apex-muted">RISK / REWARD:</span>
                <span className="font-bold text-apex-accent">1 : 3.8</span>
              </div>
            </div>

            {/* AI Regime Analysis */}
            <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-1 text-xs">
              <div className="text-[10px] text-apex-muted uppercase tracking-wider">MARKET REGIME & CONFLUENCE</div>
              <div className="text-apex-success font-bold">Bullish Order Block Expansion</div>
              <p className="text-[11px] text-apex-muted leading-relaxed">
                Institutional delta divergence on Market Depth. CME open interest expanded by +$420M in 4H.
              </p>
            </div>

            {/* Engine Output Stats */}
            <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-2 text-xs">
              <div className="text-[10px] text-apex-muted uppercase tracking-wider flex items-center gap-1 mb-1">
                <Activity className="w-3 h-3 text-apex-accent" /> ENGINE OUTPUT
              </div>

              {/* Grid of 4 stats */}
              <div className="grid grid-cols-2 gap-2">
                {/* Avg Margin */}
                <div className="bg-apex-bg rounded-md p-2 border border-apex-border/60">
                  <div className="flex items-center gap-1 text-[9px] text-apex-muted uppercase mb-1">
                    <DollarSign className="w-2.5 h-2.5" /> AVG MARGIN
                  </div>
                  <div className="font-bold text-apex-text text-sm">
                    ${positions.length > 0
                      ? (positions.reduce((acc, p) => acc + p.marginUsed, 0) / positions.length).toFixed(0)
                      : '—'}
                  </div>
                </div>

                {/* Win Rate */}
                <div className="bg-apex-bg rounded-md p-2 border border-apex-border/60">
                  <div className="flex items-center gap-1 text-[9px] text-apex-muted uppercase mb-1">
                    <BarChart2 className="w-2.5 h-2.5" /> WIN RATE
                  </div>
                  <div className="font-bold text-apex-success text-sm">
                    {backtest?.winRate != null ? `${backtest.winRate.toFixed(1)}%` : '—'}
                  </div>
                </div>

                {/* Daily PnL */}
                <div className="bg-apex-bg rounded-md p-2 border border-apex-border/60">
                  <div className="flex items-center gap-1 text-[9px] text-apex-muted uppercase mb-1">
                    <TrendingUp className="w-2.5 h-2.5" /> DAILY PNL
                  </div>
                  <div className={`font-bold text-sm ${
                    positions.some(p => p.unrealizedPnl > 0) ? 'text-apex-success' : 'text-apex-muted'
                  }`}>
                    ${positions.reduce((acc, p) => acc + (p.unrealizedPnl || 0), 0).toFixed(2)}
                  </div>
                </div>

                {/* Prop DD usage */}
                <div className="bg-apex-bg rounded-md p-2 border border-apex-border/60">
                  <div className="flex items-center gap-1 text-[9px] text-apex-muted uppercase mb-1">
                    <ShieldCheck className="w-2.5 h-2.5" /> PROP DD
                  </div>
                  <div className={`font-bold text-sm ${
                    propAccounts[0] && propAccounts[0].currentDailyDrawdownPct > 3.5 ? 'text-apex-danger' : 'text-apex-accent'
                  }`}>
                    {propAccounts[0] ? `${propAccounts[0].currentDailyDrawdownPct.toFixed(2)}%` : '—'}
                  </div>
                </div>
              </div>
            </div>

            {/* Notification Permission */}
            <div className="pt-1">
              {notificationPermission === 'granted' ? (
                <div className="flex items-center gap-2 px-3 py-2 bg-apex-success/10 border border-apex-success/30 rounded-btn text-xs text-apex-success">
                  <Bell className="w-3.5 h-3.5" />
                  <span>Push Alerts Active</span>
                </div>
              ) : notificationPermission === 'denied' ? (
                <div className="flex items-center gap-2 px-3 py-2 bg-apex-danger/10 border border-apex-danger/30 rounded-btn text-xs text-apex-danger">
                  <Bell className="w-3.5 h-3.5" />
                  <span>Notifications Blocked — Enable in browser</span>
                </div>
              ) : (
                <button
                  onClick={() => requestWebNotifications()}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-apex-surface hover:bg-apex-hover border border-apex-accent/50 text-apex-accent rounded-btn text-xs font-semibold transition-apex"
                >
                  <Bell className="w-3.5 h-3.5" />
                  Enable Push Notifications
                </button>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
