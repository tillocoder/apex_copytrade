import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import ReactECharts from 'echarts-for-react';
import { getProfessionalChartOption, type CandleData } from '../../utils/chartDataGenerator';
import { soundEngine } from '../../services/soundEngine';
import { GeminiService, type GeminiAnalysisResponse } from '../../services/geminiService';
import { 
  fetchRealKlines, 
  subscribeBinanceLivePrices, 
  updateCandlesWithLiveTick 
} from '../../services/marketDataService';
import { 
  TrendingUp, 
  TrendingDown, 
  Bot, 
  ShieldCheck, 
  CheckCircle2, 
  Volume2, 
  VolumeX, 
  Sparkles, 
  ArrowLeft, 
  Play, 
  Lock,
  Flame,
  Zap,
  Activity
} from 'lucide-react';

export const PositionCommandCenter: React.FC = () => {
  const { 
    positions = [], 
    commandCenterPositionId, 
    openCommandCenter,
    setActiveModule, 
    openReplayModal,
    propAccounts,
    tickers,
    signals,
    addLog
  } = useTerminal();

  const safePositions = Array.isArray(positions) ? positions : [];
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [geminiAnalysis, setGeminiAnalysis] = useState<GeminiAnalysisResponse | null>(null);
  const [timeframe, setTimeframe] = useState<'M1' | 'M5' | 'M15' | 'H1' | 'H4' | 'D1'>('M5');
  const [realCandles, setRealCandles] = useState<CandleData[]>([]);

  const activePosition = safePositions.find(p => p && p.id === commandCenterPositionId) || safePositions[0] || null;
  const activeTicker = tickers.find(t => t.symbol === activePosition?.symbol) || tickers[0];
  const activePropAccount = propAccounts[0];

  // Fetch REAL Binance Candlestick Data & Subscribe to Live Realtime Ticks
  useEffect(() => {
    if (activePosition && activePosition.symbol) {
      fetchRealKlines(activePosition.symbol, timeframe, 200).then(data => {
        if (data.length > 0) {
          setRealCandles(data);
        }
      });

      const unsubscribe = subscribeBinanceLivePrices((sym, price) => {
        if (sym === activePosition.symbol) {
          setRealCandles(prev => updateCandlesWithLiveTick(prev, sym, activePosition.symbol, price));
        }
      });

      return () => unsubscribe();
    }
  }, [activePosition?.symbol, timeframe]);

  // Fetch Live AI Stream Rationale
  useEffect(() => {
    if (activePosition && activeTicker && activePropAccount) {
      GeminiService.analyzePosition(activePosition, activeTicker, activePropAccount).then(res => {
        setGeminiAnalysis(res);
      });
    }
  }, [activePosition?.id, activeTicker?.price, activePropAccount]);

  if (!activePosition) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-apex-bg text-apex-muted p-8 font-mono">
        <ShieldCheck className="w-12 h-12 text-apex-accent mb-3" />
        <div className="text-sm font-bold text-apex-text">NO ACTIVE MISSION SELECTED FOR COMMAND CENTER</div>
        <button 
          onClick={() => setActiveModule('trades')}
          className="mt-4 px-4 py-2 bg-apex-surface hover:bg-apex-hover border border-apex-border text-apex-accent rounded-btn font-mono text-xs"
        >
          RETURN TO LIVE TRADES
        </button>
      </div>
    );
  }

  const livePrice = activePosition.currentPrice || activeTicker?.price || activePosition.entryPrice;
  const isProfit = (activePosition.unrealizedPnl || 0) >= 0;

  // Mini Chart Option (35% Max Height)
  const getMiniChartOption = () => {
    return getProfessionalChartOption({
      symbol: activePosition.symbol,
      basePrice: livePrice,
      overlaySMC: true,
      realCandles,
      activePosition: {
        side: activePosition.side,
        entryPrice: activePosition.entryPrice,
        sl: activePosition.sl,
        tp: activePosition.tp1,
        unrealizedPnl: activePosition.unrealizedPnl
      }
    });
  };

  const toggleSound = () => {
    const next = !audioEnabled;
    setAudioEnabled(next);
    soundEngine.setEnabled(next);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs">
      {/* Header Bar */}
      <div className="h-11 bg-apex-bgSecondary border-b border-apex-border px-4 flex items-center justify-between font-mono shrink-0">
        <div className="flex items-center space-x-3">
          <button 
            onClick={() => setActiveModule('trades')}
            className="flex items-center space-x-1.5 text-apex-muted hover:text-apex-text transition-apex bg-apex-surface border border-apex-border px-2.5 py-1 rounded-btn text-[11px]"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>BACK TO TRADES</span>
          </button>

          <span className="font-bold text-sm text-apex-text">MISSION #{activePosition.id.split('_')[1] || '001'} — {activePosition.symbol}</span>
          
          {/* Read-Only EA Observer Mode Badge */}
          <span className="bg-apex-surface border border-apex-accent text-apex-accent px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1">
            <Lock className="w-3 h-3 text-apex-accent" /> APEX REAL-TIME QUANT ENGINE ACTIVE
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <div className={`font-bold text-sm font-mono ${isProfit ? 'text-apex-success' : 'text-apex-danger'}`}>
            {isProfit ? '+' : ''}${(activePosition.unrealizedPnl || 0).toFixed(2)} ({isProfit ? '+' : ''}{activePosition.unrealizedPnlPercent || 0}%)
          </div>

          <button 
            onClick={() => openReplayModal(activePosition.id)}
            className="flex items-center space-x-1 bg-apex-surface hover:bg-apex-hover border border-apex-ai text-apex-ai px-2.5 py-1 rounded-btn text-[11px] font-medium transition-apex font-mono"
          >
            <Play className="w-3 h-3 fill-apex-ai" />
            <span>REPLAY MISSION</span>
          </button>

          <button 
            onClick={toggleSound}
            className="p-1.5 rounded-btn bg-apex-surface border border-apex-border text-apex-muted hover:text-apex-text transition-apex"
          >
            {audioEnabled ? <Volume2 className="w-4 h-4 text-apex-accent" /> : <VolumeX className="w-4 h-4 text-apex-muted" />}
          </button>
        </div>
      </div>

      {/* Main Workspace 3 Columns */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Column 1: Watchlist & Active Positions (Left 20%) */}
        <div className="w-64 bg-apex-bgSecondary border-r border-apex-border flex flex-col shrink-0 font-mono">
          
          {/* Active Positions Header & List */}
          <div className="p-2.5 border-b border-apex-border bg-apex-surface flex justify-between items-center font-bold text-[11px]">
            <span className="flex items-center gap-1.5 text-apex-accent">
              <Zap className="w-3.5 h-3.5 text-apex-accent" /> ACTIVE POSITIONS ({safePositions.length})
            </span>
          </div>

          <div className="max-h-48 overflow-y-auto divide-y divide-apex-border/40 border-b border-apex-border">
            {safePositions.map((p) => {
              const isSelected = p.id === activePosition.id;
              const posProfit = (p.unrealizedPnl || 0) >= 0;
              return (
                <div
                  key={p.id}
                  onClick={() => openCommandCenter(p.id)}
                  className={`p-2 cursor-pointer transition-apex flex justify-between items-center ${
                    isSelected ? 'bg-apex-surface border-l-2 border-apex-accent font-bold' : 'hover:bg-apex-hover bg-apex-bg/40'
                  }`}
                >
                  <div>
                    <div className="font-bold text-apex-text text-[11px]">{p.symbol}</div>
                    <div className="text-[9px] text-apex-muted">{p.side} {p.leverage}X</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-[10px] font-bold ${posProfit ? 'text-apex-success' : 'text-apex-danger'}`}>
                      {posProfit ? '+' : ''}${(p.unrealizedPnl || 0).toFixed(2)}
                    </div>
                    <div className="text-[9px] text-apex-accent font-bold">CLICK TO SWITCH</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Live Watchlist Header & List */}
          <div className="p-2.5 border-b border-apex-border bg-apex-surface flex justify-between items-center font-bold text-[11px]">
            <span className="flex items-center gap-1.5 text-apex-text">
              <Flame className="w-3.5 h-3.5 text-apex-accent" /> LIVE WATCHLIST
            </span>
            <span className="text-[10px] text-apex-muted">REAL-TIME</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-apex-border/40">
            {tickers.map((t) => {
              const matchingPos = safePositions.find(p => p.symbol === t.symbol);
              const isSelected = activePosition?.symbol === t.symbol;

              return (
                <div 
                  key={t.symbol}
                  onClick={() => {
                    if (matchingPos) {
                      openCommandCenter(matchingPos.id);
                    }
                  }}
                  className={`p-2 hover:bg-apex-hover cursor-pointer flex justify-between text-[11px] transition-apex ${
                    isSelected ? 'bg-apex-surface border-l-2 border-apex-cyan' : ''
                  }`}
                >
                  <div>
                    <div className="font-bold text-apex-text flex items-center gap-1">
                      <span>{t.symbol}</span>
                      {matchingPos && (
                        <span className="px-1 py-0.2 rounded bg-apex-accent/15 border border-apex-accent/30 text-apex-accent text-[8px] font-bold">
                          OPEN
                        </span>
                      )}
                    </div>
                    <div className="text-[9px] text-apex-muted">Vol ${(t.volume24h / 1e9).toFixed(1)}B</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-apex-text">${t.price.toLocaleString()}</div>
                    <div className={`text-[9px] font-bold ${t.change24h >= 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
                      {t.change24h >= 0 ? '+' : ''}{t.change24h}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Column 2: Position Center & Risk Engine (Center 55%) */}
        <div className="flex-1 flex flex-col border-r border-apex-border bg-apex-bgSecondary overflow-hidden">
          
          {/* Top Panel: Position & Challenge Metrics */}
          <div className="p-3 grid grid-cols-4 gap-2 font-mono text-[11px] shrink-0 border-b border-apex-border">
            <div className="workstation-panel p-2">
              <div className="text-apex-muted text-[9px]">MISSION STATUS</div>
              <div className="font-bold text-apex-success text-xs">RUNNING</div>
            </div>
            <div className="workstation-panel p-2">
              <div className="text-apex-muted text-[9px]">RISK REWARD</div>
              <div className="font-bold text-apex-accent text-xs">{activePosition.rewardPercent ? `1 : ${activePosition.rewardPercent.toFixed(2)}` : '—'}</div>
            </div>
            <div className="workstation-panel p-2">
              <div className="text-apex-muted text-[9px]">MISSION HEALTH</div>
              <div className="font-bold text-apex-success text-xs">{activePosition.positionHealthScore ? `${activePosition.positionHealthScore} / 100` : '—'}</div>
            </div>
            <div className="workstation-panel p-2">
              <div className="text-apex-muted text-[9px]">CHALLENGE DAILY DD</div>
              <div className="font-bold text-apex-warning text-xs">
                {activePropAccount ? `${activePropAccount.currentDailyDrawdownPct.toFixed(2)}% / ${activePropAccount.maxDailyDrawdownPct}%` : '—'}
              </div>
            </div>
          </div>

          {/* Center-Bottom: Real Exchange Mini Chart */}
          <div className="flex-1 w-full relative bg-apex-bgSecondary flex flex-col min-h-[220px]">
            <div className="h-7 bg-apex-surface border-b border-apex-border px-3 flex items-center justify-between font-mono text-[10px] shrink-0">
              <div className="flex items-center space-x-3">
                <span className="font-bold text-apex-text">{activePosition.symbol} EXECUTION CHART</span>
                <div className="flex space-x-1">
                  {(['M1', 'M5', 'M15', 'H1', 'H4', 'D1'] as const).map(tf => (
                    <button
                      key={tf}
                      onClick={() => setTimeframe(tf)}
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                        timeframe === tf ? 'bg-apex-accent text-black' : 'text-apex-muted hover:text-apex-text'
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center space-x-2 text-[10px]">
                <span className="text-apex-muted">ENTRY: <strong className="text-apex-text">${activePosition.entryPrice}</strong></span>
                <span className="text-apex-muted">SL: <strong className="text-apex-danger">${activePosition.sl}</strong></span>
                <span className="text-apex-muted">TP1: <strong className="text-apex-success">${activePosition.tp1}</strong></span>
              </div>
            </div>

            <div className="flex-1 w-full relative">
              <ReactECharts 
                option={getMiniChartOption()} 
                style={{ height: '100%', width: '100%' }} 
                opts={{ renderer: 'canvas' }}
              />
            </div>
          </div>

          {/* Timeline Event Event Bar */}
          <div className="h-10 border-t border-apex-border bg-apex-bg px-3 flex items-center justify-between text-[10px] font-mono shrink-0">
            <span className="text-apex-muted font-bold">MISSION EVENT TIMELINE</span>
            <div className="flex items-center space-x-4">
              {activePosition.timeline && activePosition.timeline.length > 0 ? (
                activePosition.timeline.map((evt, i) => (
                  <span key={evt.id || i} className="text-apex-textSecondary">
                    [{evt.timestamp}] <strong className="text-apex-text">{evt.title}</strong> — {evt.reason}
                  </span>
                ))
              ) : (
                <span className="text-apex-textSecondary">
                  [{activePosition.timeOpen || 'Just Now'}] <strong className="text-apex-text">Position Opened</strong> — AI Signal Executed at Market Price
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Column 3: Live XR AI 2.5 Stream (Right 25%) */}
        <div className="w-80 bg-apex-bg border-l border-apex-border flex flex-col shrink-0 font-mono p-3 space-y-3 overflow-y-auto">
          <div className="flex items-center justify-between border-b border-apex-border pb-2">
            <div className="flex items-center space-x-1.5 text-apex-ai font-bold text-[11px]">
              <Sparkles className="w-4 h-4 text-apex-ai animate-pulse" />
              <span>LIVE XR AI 2.5 STREAM</span>
            </div>
          </div>

          {/* AI Recommendation Box */}
          <div className="bg-apex-surface border border-apex-ai/40 p-3 rounded-md space-y-1 text-center">
            <div className="text-[9px] text-apex-muted uppercase tracking-wider">RECOMMENDATION & CONFIDENCE</div>
            <div className="font-bold text-sm text-apex-ai">
              {geminiAnalysis?.recommendation || activePosition.aiRecommendation || 'HOLD FOR TP2 TARGET'}
            </div>
            <div className="text-[10px] text-apex-textSecondary">
              Confidence Score: <strong className="text-apex-ai">{geminiAnalysis?.confidenceScore || activePosition.aiConfidence}%</strong>
            </div>
          </div>

          {/* Streaming Rationale */}
          <div className="bg-apex-surface border border-apex-border p-3 rounded-md space-y-1.5 text-[11px]">
            <div className="flex items-center space-x-1 text-apex-ai font-bold text-[10px]">
              <Bot className="w-3.5 h-3.5" />
              <span>LIVE STREAMING RATIONALE</span>
            </div>
            <p className="text-apex-textSecondary text-[10px] leading-relaxed">
              {geminiAnalysis?.explanation || activePosition.aiExplanation}
            </p>
          </div>

          {/* Prop Firm Safeguard Matrix */}
          <div className="bg-apex-surface border border-apex-border p-3 rounded-md space-y-1 text-[10px]">
            <div className="text-apex-muted font-bold text-[9px] uppercase">PROP RISK ASSESSMENT</div>
            <div className="text-apex-textSecondary">
              Prop Daily Drawdown: <strong className="text-apex-success">{activePropAccount ? `${activePropAccount.currentDailyDrawdownPct.toFixed(2)}%` : '0%'} / {activePropAccount?.maxDailyDrawdownPct || 5}% Limit.</strong> Safe Risk Remaining: <strong>$4,150.</strong>
            </div>
          </div>

          <div className="p-3 bg-apex-bgSecondary rounded border border-apex-border text-[9px] text-apex-muted space-y-1">
            <div className="font-bold text-apex-accent flex items-center gap-1">
              <Lock className="w-3 h-3" /> READ-ONLY MONITORING MODE
            </div>
            <div>All execution decisions are handled 100% autonomously by APEX M5 Engine. Manual override disabled.</div>
          </div>
        </div>

      </div>
    </div>
  );
};
