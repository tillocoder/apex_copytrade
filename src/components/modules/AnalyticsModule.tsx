import React from 'react';
import { BarChart3, Clock, Calendar, Award } from 'lucide-react';

export const AnalyticsModule: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BarChart3 className="w-5 h-5 text-apex-cyan" />
          <span>ADVANCED PERFORMANCE & TIMING ANALYTICS</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2">
          <div className="text-apex-muted text-[10px]">BEST TRADING HOUR</div>
          <div className="text-xl font-bold text-apex-green">13:00 - 15:00 UTC</div>
          <div className="text-apex-muted text-[10px]">NY Session Open (+78% Win Rate)</div>
        </div>
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2">
          <div className="text-apex-muted text-[10px]">BEST TRADING DAY</div>
          <div className="text-xl font-bold text-apex-cyan">TUESDAY & WEDNESDAY</div>
          <div className="text-apex-muted text-[10px]">Highest Volume & Order Flow Cleanliness</div>
        </div>
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2">
          <div className="text-apex-muted text-[10px]">BEST ASSET</div>
          <div className="text-xl font-bold text-apex-text">BTC/USDT (68.4% WR)</div>
          <div className="text-apex-muted text-[10px]">Average RR: 2.85</div>
        </div>
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2">
          <div className="text-apex-muted text-[10px]">BEST TIMEFRAME</div>
          <div className="text-xl font-bold text-emerald-400">M5 & M15 CONFLUENCE</div>
          <div className="text-apex-muted text-[10px]">91.2% AI Model Precision</div>
        </div>
      </div>
    </div>
  );
};
