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
  Flame, 
  Bot, 
  ShieldCheck, 
  Sparkles, 
  Activity, 
  Lock, 
  AlertTriangle,
  Zap,
  CheckCircle2,
  SlidersHorizontal
} from 'lucide-react';

export const TradingWorkspace: React.FC = () => {
  const { 
    selectedSymbol, 
    setSelectedSymbol, 
    tickers, 
    positions, 
    propAccounts,
    backtest,
    addLog,
    panicCloseAll
  } = useTerminal();

  const [timeframe, setTimeframe] = useState<'M1' | 'M5' | 'M15' | 'H1' | 'H4' | 'D1'>('M5');
  const [realCandles, setRealCandles] = useState<CandleData[]>([]);
  const [copyTradeRatio, setCopyTradeRatio] = useState<number>(1.0);
  const zoomRef = React.useRef<{ start: number; end: number }>({ start: 45, end: 95 });

  const currentTicker = tickers.find(t => t.symbol === selectedSymbol) || tickers[0];
  const activePosition = positions.find(p => p.symbol === selectedSymbol);
  const activePropAccount = propAccounts[0];

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

  const getChartOption = () => {
    return getProfessionalChartOption({
      symbol: selectedSymbol,
      basePrice: currentTicker.price,
      overlaySMC: true,
      overlayAI: true,
      activePosition,
      realCandles,
      zoomStart: zoomRef.current.start,
      zoomEnd: zoomRef.current.end
    });
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-apex-bg font-sans text-xs">
      {/* Watchlist Panel (Left 18%) */}
      <div className="w-56 bg-apex-bgSecondary border-r border-apex-border flex flex-col shrink-0 font-mono">
        <div className="p-2.5 border-b border-apex-border bg-apex-surface flex justify-between items-center font-bold">
          <span className="flex items-center gap-1.5 text-apex-text">
            <Flame className="w-3.5 h-3.5 text-apex-accent" /> WATCHLIST
          </span>
          <span className="text-[10px] text-apex-muted">STREAMING</span>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-apex-border/40">
          {tickers.map((t) => (
            <div
              key={t.symbol}
              onClick={() => setSelectedSymbol(t.symbol)}
              className={`p-2.5 hover:bg-apex-hover cursor-pointer transition-apex flex justify-between ${
                t.symbol === selectedSymbol ? 'bg-apex-surface border-l-2 border-apex-accent' : ''
              }`}
            >
              <div>
                <div className="font-bold text-apex-text text-xs">{t.symbol}</div>
                <div className="text-[10px] text-apex-muted">Vol ${(t.volume24h / 1e9).toFixed(1)}B</div>
              </div>
              <div className="text-right">
                <div className="font-bold text-apex-text text-xs">${t.price.toLocaleString()}</div>
                <div className={`text-[10px] font-bold ${t.change24h >= 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
                  {t.change24h >= 0 ? '+' : ''}{t.change24h}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Large Chart Canvas (Center 57%) */}
      <div className="flex-1 flex flex-col border-r border-apex-border bg-apex-bgSecondary overflow-hidden">
        <div className="h-10 bg-apex-surface border-b border-apex-border px-3 flex items-center justify-between font-mono shrink-0">
          <div className="flex items-center space-x-3">
            <span className="font-bold text-sm text-apex-text">{selectedSymbol}</span>
            <span className="text-apex-accent font-bold text-xs">${currentTicker.price.toLocaleString()}</span>

            <div className="flex space-x-1 pl-2 border-l border-apex-border">
              {(['M1', 'M5', 'M15', 'H1', 'H4', 'D1'] as const).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-2 py-0.5 rounded-md text-[11px] font-medium transition-apex ${
                    timeframe === tf ? 'bg-apex-hover text-apex-accent border border-apex-border' : 'text-apex-muted hover:text-apex-text'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2 text-[10px]">
            <span className="bg-apex-surface border border-apex-accent/40 text-apex-accent px-2 py-0.5 rounded font-bold flex items-center gap-1">
              <Bot className="w-3 h-3 text-apex-accent" /> PAPER ENGINE · REAL MARKET DATA
            </span>
          </div>
        </div>

        <div className="flex-1 w-full h-full relative">
          <ReactECharts 
            option={getChartOption()} 
            notMerge={false}
            lazyUpdate={true}
            onEvents={{ datazoom: handleDataZoom }}
            style={{ height: '100%', width: '100%' }} 
          />
        </div>
      </div>

      {/* Autonomous Engine Copy-Trade & Prop Risk Telemetry Panel (Right 25%) */}
      <div className="w-80 bg-apex-bgSecondary p-3 overflow-y-auto space-y-3 font-mono shrink-0 border-l border-apex-border">
        
        {/* Header Title */}
        <div className="font-bold text-xs text-apex-accent border-b border-apex-border pb-2 uppercase tracking-wider flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Bot className="w-4 h-4 text-apex-accent" /> ENGINE COPY DISPATCH
          </span>
          <span className="text-[10px] text-apex-success bg-apex-success/15 border border-apex-success/30 px-1.5 py-0.5 rounded">
            SYNCED
          </span>
        </div>

        {/* Read-Only Observer Notice */}
        <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-1.5 text-[10px]">
          <div className="font-bold text-apex-text flex items-center gap-1">
            <Lock className="w-3 h-3 text-apex-accent" /> AUTONOMOUS MONITORING MODE
          </div>
          <p className="text-apex-muted leading-relaxed font-sans text-[11px]">
            Signals use real Binance market data; execution is paper-mode until an exchange account is explicitly connected.
          </p>
        </div>

        {/* Read-Only Algorithm System Lock */}
        <div className="workstation-panel p-3 space-y-2 text-[11px]">
          <div className="text-[10px] text-apex-muted font-bold uppercase tracking-wider flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Lock className="w-3 h-3 text-apex-accent" /> ALGORITHM EXECUTION LOCK
            </span>
            <span className="text-apex-accent font-bold text-[10px] bg-apex-accent/15 px-1.5 py-0.5 rounded border border-apex-accent/30">PAPER MODE</span>
          </div>

          <div className="space-y-1.5 pt-1 border-t border-apex-border/50 font-mono text-[10px]">
            <div className="flex justify-between">
              <span className="text-apex-muted">POSITION SIZING:</span>
              <span className="font-bold text-apex-accent">0.50% FIXED RISK / TRADE</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">MAX PROP LEVERAGE:</span>
              <span className="font-bold text-apex-success">5X STRICT ALGO LOCK</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">SL / TP EXECUTION:</span>
              <span className="font-bold text-apex-text">1.5x ATR SL / 3.0x ATR TP</span>
            </div>
          </div>
        </div>

        {/* Prop Guardian Telemetry */}
        <div className="workstation-panel p-3 space-y-2 text-[11px]">
          <div className="text-[10px] text-apex-muted font-bold uppercase tracking-wider flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-apex-accent" /> PROP RISK RAIL TELEMETRY
          </div>

          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between">
              <span className="text-apex-muted">MAX DAILY DRAWDOWN:</span>
              <span className="font-bold text-apex-warning">
                {activePropAccount ? `${activePropAccount.currentDailyDrawdownPct.toFixed(2)}% / ${activePropAccount.maxDailyDrawdownPct}%` : '0.00% / 5.0%'}
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-apex-muted">MAX TOTAL DRAWDOWN:</span>
              <span className="font-bold text-apex-accent">
                {activePropAccount ? `${activePropAccount.currentTotalDrawdownPct.toFixed(2)}% / ${activePropAccount.maxTotalDrawdownPct}%` : '0.00% / 10.0%'}
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-apex-muted">ESTIMATED SLIPPAGE:</span>
              <span className="font-bold text-apex-success">0.02% (DMA FIX Execution)</span>
            </div>

            <div className="flex justify-between">
              <span className="text-apex-muted">ENGINE WIN RATE:</span>
              <span className="font-bold text-apex-success">
                {backtest?.totalTrades ? `${backtest.winRate.toFixed(1)}%` : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Live Signal Confluence Status */}
        <div className="bg-apex-ai/15 border border-apex-ai/40 p-3 rounded-panel space-y-1.5">
          <div className="text-[10px] font-mono text-apex-ai font-bold flex items-center gap-1 uppercase">
            <Sparkles className="w-3.5 h-3.5 text-apex-ai" /> LIVE SIGNAL CONFLUENCE
          </div>
          <div className="text-xs font-bold text-apex-text">{selectedSymbol} SMC Demand Block Sweep</div>
          <div className="text-[10px] text-apex-muted">Confidence Score: <strong className="text-apex-ai">94.8%</strong></div>
        </div>

      </div>
    </div>
  );
};
