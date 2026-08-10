import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { BookOpen, Smile, Sparkles, Image, Play } from 'lucide-react';

export const JournalWorkspace: React.FC = () => {
  const { positions, openReplayModal } = useTerminal();
  const trade = positions[0];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BookOpen className="w-5 h-5 text-apex-accent" />
          <span>TRADE JOURNAL & PSYCHOLOGY REVIEW</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-y-auto">
        {/* Chart Snapshot Viewer */}
        <div className="lg:col-span-2 workstation-panel p-4 space-y-3 font-mono">
          <div className="flex justify-between items-center text-xs font-bold border-b border-apex-border pb-2">
            <span className="text-apex-text flex items-center gap-1.5"><Image className="w-4 h-4 text-apex-accent" /> ENTRY & EXIT SNAPSHOT - {trade?.symbol}</span>
            <button 
              onClick={() => openReplayModal(trade?.id || 'pos_001')}
              className="bg-apex-ai/15 hover:bg-apex-ai border border-apex-ai/40 text-apex-ai hover:text-white px-2.5 py-1 rounded-btn text-[11px] font-bold flex items-center gap-1 transition-apex"
            >
              <Play className="w-3 h-3 fill-apex-ai" />
              <span>REPLAY TRADE</span>
            </button>
          </div>

          <div className="w-full h-72 bg-apex-bg border border-apex-border rounded-panel flex flex-col justify-center items-center text-apex-muted p-4 relative">
            <div className="text-apex-accent font-bold text-sm">TRADE SNAPSHOT #428 RECORDED</div>
            <div className="text-xs text-apex-muted font-mono mt-1">Entry: ${trade?.entryPrice} | SL: ${trade?.sl} | TP: ${trade?.tp1}</div>
            <div className="absolute bottom-3 right-3 text-[10px] bg-apex-surface border border-apex-border px-2 py-0.5 rounded text-apex-success">
              +${trade?.unrealizedPnl} LOCKED PROFIT
            </div>
          </div>
        </div>

        {/* Trade Notes & Psychology */}
        <div className="workstation-panel p-4 space-y-3 font-mono">
          <div className="font-bold text-xs text-apex-text border-b border-apex-border pb-2">
            PSYCHOLOGY & MISTAKE AUDIT
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-3 bg-apex-bg rounded-panel border border-apex-border space-y-1 font-sans">
              <div className="text-[10px] text-apex-muted font-mono">TRADE RATIONALE & NOTES</div>
              <p className="text-apex-textSecondary text-[11px] leading-relaxed">
                {trade?.aiExplanation}
              </p>
            </div>

            <div className="p-3 bg-apex-bg rounded-panel border border-apex-border flex items-center justify-between">
              <span className="text-apex-muted text-[10px]">EMOTION STATE:</span>
              <span className="text-apex-success font-bold flex items-center gap-1"><Smile className="w-4 h-4" /> Calm Focus (10/10)</span>
            </div>

            <div className="p-3 bg-apex-ai/15 border border-apex-ai/30 rounded-panel space-y-1 font-sans">
              <div className="text-[10px] font-mono text-apex-ai font-bold flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-apex-ai" /> AI EXECUTION SCORE
              </div>
              <div className="text-sm font-bold text-apex-ai font-mono">98% PERFECT EXECUTION</div>
              <p className="text-apex-textSecondary text-[11px]">Strict compliance with 15m SMC Order Block Strategy.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
