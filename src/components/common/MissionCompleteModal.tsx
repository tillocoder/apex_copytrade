import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { Award, CheckCircle2, XCircle, Sparkles, X, Clock, TrendingUp, ShieldCheck } from 'lucide-react';

export const MissionCompleteModal: React.FC = () => {
  const { missionModalOpen, setMissionModalOpen, lastMissionData, openCommandCenter } = useTerminal();

  if (!missionModalOpen || !lastMissionData) return null;

  const isSuccess = lastMissionData.pnl >= 0;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-apex-bgSecondary border border-apex-border rounded-panel w-full max-w-lg overflow-hidden font-mono shadow-panel flex flex-col animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className={`p-4 border-b border-apex-border flex items-center justify-between ${
          isSuccess ? 'bg-apex-success/15 text-apex-success' : 'bg-apex-danger/15 text-apex-danger'
        }`}>
          <div className="flex items-center space-x-2 font-bold text-sm">
            {isSuccess ? <Award className="w-5 h-5 text-apex-success" /> : <XCircle className="w-5 h-5 text-apex-danger" />}
            <span>MISSION {isSuccess ? 'COMPLETE' : 'TERMINATED'}</span>
          </div>

          <button 
            onClick={() => setMissionModalOpen(false)}
            className="p-1 rounded-md text-apex-muted hover:text-apex-text transition-apex"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 font-sans text-xs">
          <div className="text-center space-y-1">
            <div className="text-apex-muted font-mono text-[10px]">MISSION ID #428</div>
            <div className="text-xl font-bold text-apex-text font-mono">{lastMissionData.symbol} ({lastMissionData.side})</div>
            <div className={`text-2xl font-bold font-mono ${isSuccess ? 'text-apex-success' : 'text-apex-danger'}`}>
              {isSuccess ? '+' : ''}${lastMissionData.pnl.toFixed(2)} ({isSuccess ? '+' : ''}{lastMissionData.pnlPct.toFixed(2)}%)
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 workstation-panel p-3 font-mono text-[11px]">
            <div>
              <div className="text-apex-muted text-[9px]">MISSION DURATION</div>
              <div className="font-bold text-apex-text">{lastMissionData.duration}</div>
            </div>
            <div>
              <div className="text-apex-muted text-[9px]">CLOSE REASON</div>
              <div className="font-bold text-apex-accent">{lastMissionData.reason}</div>
            </div>
          </div>

          {/* AI Review Ready Box */}
          <div className="p-3 bg-apex-ai/15 border border-apex-ai/40 rounded-panel space-y-1 font-mono">
            <div className="text-apex-ai font-bold text-[11px] flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-apex-ai" /> AI REVIEW & JOURNAL READY
            </div>
            <p className="text-apex-textSecondary text-[11px] font-sans">
              APEX Engine executed 100% compliant risk parameters. Logged into Trade Journal.
            </p>
          </div>

          {/* Action Button */}
          <button
            onClick={() => {
              setMissionModalOpen(false);
              if (lastMissionData.positionId) {
                openCommandCenter(lastMissionData.positionId);
              }
            }}
            className="w-full bg-apex-surface hover:bg-apex-hover border border-apex-accent text-apex-accent font-bold py-2.5 rounded-btn transition-apex text-center font-mono"
          >
            VIEW FULL MISSION TIMELINE & AI REVIEW
          </button>
        </div>
      </div>
    </div>
  );
};
