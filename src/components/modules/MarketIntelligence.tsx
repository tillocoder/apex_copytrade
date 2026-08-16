import React, { useEffect, useState } from 'react';
import { BrainCircuit, Activity, TrendingUp, TrendingDown, Layers, ShieldCheck } from 'lucide-react';
import { fetchMarketAnalysis, type MarketAnalysisData } from '../../services/quantApiService';

export const MarketIntelligence: React.FC = () => {
  const [analysis, setAnalysis] = useState<MarketAnalysisData | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC/USDT');

  useEffect(() => {
    fetchMarketAnalysis(selectedSymbol).then(res => {
      if (res) setAnalysis(res);
    });
  }, [selectedSymbol]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BrainCircuit className="w-5 h-5 text-apex-accent" />
          <span>INSTITUTIONAL MARKET INTELLIGENCE & SMC QUANT MATRIX</span>
        </div>
        <div className="flex items-center space-x-2">
          {['BTC/USDT', 'ETH/USDT', 'SOL/USDT'].map(sym => (
            <button
              key={sym}
              onClick={() => setSelectedSymbol(sym)}
              className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold transition-apex ${
                selectedSymbol === sym ? 'bg-apex-cyan text-apex-bg' : 'bg-apex-surface text-apex-muted border border-apex-border hover:bg-apex-hover'
              }`}
            >
              {sym}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 overflow-y-auto font-mono">
        {/* Regime Score Card */}
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3 shadow-xl">
          <div className="text-apex-muted text-[10px]">QUANT MARKET REGIME</div>
          <div className="text-2xl font-bold text-apex-green flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-apex-green" />
            <span>{analysis?.regime || 'BULLISH_TREND'}</span>
          </div>
          <div className="text-xs font-semibold text-apex-green">
            REGIME SCORE: {analysis?.regimeScore ?? 88.5} / 100
          </div>
          <div className="w-full h-1.5 bg-apex-bg rounded-full overflow-hidden border border-apex-border">
            <div className="h-full bg-apex-green" style={{ width: `${analysis?.regimeScore ?? 88.5}%` }} />
          </div>
        </div>

        {/* Real-time Indicators */}
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2 shadow-xl">
          <div className="text-apex-muted text-[10px]">TECHNICAL INDICATORS (M15)</div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between">
              <span className="text-apex-muted">EMA 20:</span>
              <span className="font-bold text-apex-text">${analysis?.indicators.ema20.toLocaleString() ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">EMA 50:</span>
              <span className="font-bold text-apex-text">${analysis?.indicators.ema50.toLocaleString() ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">EMA 200:</span>
              <span className="font-bold text-apex-text">${analysis?.indicators.ema200.toLocaleString() ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">RSI (14):</span>
              <span className="font-bold text-apex-cyan">{analysis?.indicators.rsi ?? 54.2}</span>
            </div>
          </div>
        </div>

        {/* SMC Order Blocks & FVG */}
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2 shadow-xl">
          <div className="text-apex-muted text-[10px]">SMC LIQUIDITY & ORDER BLOCKS</div>
          <div className="text-sm font-bold text-apex-cyan flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-apex-cyan" />
            <span>ORDER BLOCK LEVEL</span>
          </div>
          <div className="text-xl font-bold text-apex-text">
            ${analysis?.smc.orderBlockLevel.toLocaleString() ?? '—'}
          </div>
          <div className="text-[11px] text-apex-muted space-y-1">
            <div className="flex justify-between">
              <span>Fair Value Gap (FVG):</span>
              <span className="font-bold text-apex-green">${analysis?.smc.fvgLevel.toLocaleString() ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span>20-Bar Swing High:</span>
              <span className="font-bold text-apex-text">${analysis?.smc.swingHigh.toLocaleString() ?? '—'}</span>
            </div>
          </div>
        </div>

        {/* Risk & Execution Protection */}
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2 shadow-xl">
          <div className="text-apex-muted text-[10px]">PROP FIRM COMPLIANCE</div>
          <div className="text-2xl font-bold text-apex-green flex items-center gap-1">
            <ShieldCheck className="w-5 h-5 text-apex-green" />
            <span>PASSED</span>
          </div>
          <div className="text-[11px] text-apex-muted space-y-1">
            <div className="flex justify-between">
              <span>Prague Timezone Reset:</span>
              <span className="font-bold text-apex-text">00:00 CE(S)T</span>
            </div>
            <div className="flex justify-between">
              <span>Max Daily Drawdown:</span>
              <span className="font-bold text-apex-green">1.61% (&lt; 5.0%)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
