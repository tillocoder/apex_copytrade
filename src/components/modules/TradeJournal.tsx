import React from 'react';
import { BookOpen, Smile, AlertCircle, Sparkles, Image } from 'lucide-react';

export const TradeJournal: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BookOpen className="w-5 h-5 text-apex-cyan" />
          <span>TRADE JOURNAL & PSYCHOLOGY AUDITOR</span>
        </div>
      </div>

      <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-4 max-w-2xl">
        <div className="flex justify-between items-center font-bold">
          <span className="text-apex-text text-sm">LOGGED TRADE #428 - BTC/USDT LONG</span>
          <span className="bg-apex-green/20 text-apex-green px-2 py-0.5 rounded text-[10px]">+ $5,551.25 PROFIT</span>
        </div>

        <div className="space-y-2">
          <label className="text-apex-muted text-[10px]">TRADE NOTES & EXECUTION CHECKLIST</label>
          <p className="bg-apex-panel border border-apex-border p-3 rounded text-apex-text leading-relaxed">
            Took entry after 15m liquidity grab below 89,100. Followed trading plan 100%. Did not FOMO.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-apex-panel p-3 rounded border border-apex-border">
            <div className="text-apex-muted text-[10px]">EMOTION RATING</div>
            <div className="text-apex-cyan font-bold text-sm flex items-center gap-1">
              <Smile className="w-4 h-4 text-apex-green" /> 10 / 10 (Calm Focus)
            </div>
          </div>
          <div className="bg-apex-panel p-3 rounded border border-apex-border">
            <div className="text-apex-muted text-[10px]">AI EXECUTION SCORE</div>
            <div className="text-emerald-400 font-bold text-sm flex items-center gap-1">
              <Sparkles className="w-4 h-4 text-emerald-400" /> 98% PERFECT EXECUTION
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
