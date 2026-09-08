import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { ApexCandleChart } from '../common/ApexCandleChart';
import { 
  Bot, 
  ShieldCheck, 
  Sparkles, 
  Activity, 
  Lock, 
  Zap,
  CheckCircle2,
  SlidersHorizontal
} from 'lucide-react';

export const TradingWorkspace: React.FC = () => {
  const { 
    selectedSymbol, 
    setSelectedSymbol, 
    positions, 
    propAccounts,
    backtest,
    addLog,
    panicCloseAll
  } = useTerminal();

  const [copyTradeRatio, setCopyTradeRatio] = useState<number>(1.0);

  // Guarantee BTC/USDT is always active
  useEffect(() => {
    if (selectedSymbol !== 'BTC/USDT') {
      setSelectedSymbol('BTC/USDT');
    }
  }, [selectedSymbol, setSelectedSymbol]);

  const activePosition = positions.find(p => p.symbol === 'BTC/USDT');
  const activePropAccount = propAccounts[0];

  return (
    <div className="flex-1 flex overflow-hidden bg-apex-bg font-sans text-xs">
      {/* Large Full-Width Chart Canvas (Center/Left Area) */}
      <div className="flex-1 flex flex-col border-r border-apex-border bg-apex-bgSecondary overflow-hidden min-w-0">
        <ApexCandleChart
          symbol="BTC/USDT"
          position={activePosition}
          defaultTimeframe="15m"
        />
      </div>

      {/* Autonomous Engine Copy-Trade & Prop Risk Telemetry Panel (Right 280-320px) */}
      <div className="w-80 bg-apex-bgSecondary p-3 overflow-y-auto space-y-3 font-mono shrink-0 border-l border-apex-border">
        
        {/* Header Title */}
        <div className="font-bold text-xs text-apex-accent border-b border-apex-border pb-2 uppercase tracking-wider flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Bot className="w-4 h-4 text-apex-accent" /> ENGINE COPY DISPATCH
          </span>
          <span className="text-[10px] text-apex-success bg-apex-success/15 border border-apex-success/30 px-1.5 py-0.5 rounded">
            BTC/USDT EXCLUSIVE
          </span>
        </div>

        {/* Read-Only Observer Notice */}
        <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-1.5 text-[10px]">
          <div className="font-bold text-apex-text flex items-center gap-1">
            <Lock className="w-3 h-3 text-apex-accent" /> AUTONOMOUS MONITORING MODE
          </div>
          <p className="text-apex-muted leading-relaxed font-sans text-[11px]">
            Signals use real Binance BTC/USDT market data; execution is paper-mode until an exchange account is explicitly connected.
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
              <span className="text-apex-muted">ACTIVE PAIR:</span>
              <span className="font-bold text-apex-accent">BTC/USDT ONLY</span>
            </div>
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
              <span className="font-bold text-apex-text">1.5x ATR SL / 1.8R-3.0R TP</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">MAX DAILY TRADES:</span>
              <span className="font-bold text-emerald-400">2 TRADES / DAY (A+ ONLY)</span>
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
          <div className="text-xs font-bold text-apex-text">BTC/USDT SMC Demand Block Sweep</div>
          <div className="text-[10px] text-apex-muted">Confidence Score: <strong className="text-apex-ai">94.8%</strong></div>
        </div>

      </div>
    </div>
  );
};
