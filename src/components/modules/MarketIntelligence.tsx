import React from 'react';
import { BrainCircuit } from 'lucide-react';

export const MarketIntelligence: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BrainCircuit className="w-5 h-5 text-apex-accent" />
          <span>INSTITUTIONAL MARKET INTELLIGENCE & MACRO MATRIX</span>
        </div>
        <div className="text-[11px] text-apex-muted">GLOBAL LIQUIDITY FLOWS STREAMING</div>
      </div>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 overflow-y-auto font-mono">
        {/* Fear & Greed Card */}
        <div className="workstation-panel p-4 space-y-3">
          <div className="text-apex-muted text-[10px]">CRYPTO FEAR & GREED INDEX</div>
          <div className="text-3xl font-bold text-apex-success">78</div>
          <div className="text-xs font-semibold text-apex-success uppercase">EXTREME GREED</div>
          <div className="w-full h-1 bg-apex-bg rounded-full overflow-hidden border border-apex-border">
            <div className="h-full bg-apex-success" style={{ width: '78%' }} />
          </div>
        </div>

        {/* Global Macro Dashboard */}
        <div className="workstation-panel p-4 space-y-2">
          <div className="text-apex-muted text-[10px]">MACRO CROSS CORRELATION</div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between">
              <span className="text-apex-muted">DXY (DOLLAR INDEX):</span>
              <span className="font-bold text-apex-danger">102.40 (-0.42%)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">GOLD (XAU/USD):</span>
              <span className="font-bold text-apex-success">$2,480.50 (+1.10%)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">NASDAQ 100:</span>
              <span className="font-bold text-apex-success">19,850.20 (+1.45%)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apex-muted">CRUDE OIL (WTI):</span>
              <span className="font-bold text-apex-text">$74.20 (+0.15%)</span>
            </div>
          </div>
        </div>

        {/* 24H Liquidation Cascade */}
        <div className="workstation-panel p-4 space-y-2">
          <div className="text-apex-muted text-[10px]">24H DERIVATIVES LIQUIDATIONS</div>
          <div className="text-2xl font-bold text-apex-danger">$142.80M</div>
          <div className="text-[11px] text-apex-muted space-y-1">
            <div className="flex justify-between">
              <span>Shorts Liquidated:</span>
              <span className="font-bold text-apex-success">$104.20M (73%)</span>
            </div>
            <div className="flex justify-between">
              <span>Longs Liquidated:</span>
              <span className="font-bold text-apex-danger">$38.60M (27%)</span>
            </div>
          </div>
        </div>

        {/* ETF Net Inflows */}
        <div className="workstation-panel p-4 space-y-2">
          <div className="text-apex-muted text-[10px]">SPOT BITCOIN ETF NET FLOW</div>
          <div className="text-2xl font-bold text-apex-success">+$640.50M</div>
          <div className="text-[11px] text-apex-muted">BlackRock (IBIT) Inflow +$412M</div>
        </div>
      </div>
    </div>
  );
};
