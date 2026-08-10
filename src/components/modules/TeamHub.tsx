import React from 'react';
import { Users, MessageSquare, Share2, ShieldCheck, Activity } from 'lucide-react';

export const TeamHub: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Users className="w-5 h-5 text-apex-cyan" />
          <span>TEAM COLLABORATION & AUDIT LOGS</span>
        </div>
        <div className="text-[11px] text-apex-green font-bold flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-apex-green animate-ping" /> 4 QUANT TRADERS ACTIVE ONLINE
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="text-apex-muted text-[10px]">ACTIVE WORKSPACE MEMBERS</div>
          <div className="space-y-2">
            <div className="flex justify-between items-center bg-apex-panel p-2 rounded border border-apex-border">
              <span className="font-bold text-apex-text">Marcus Vance (Owner)</span>
              <span className="text-apex-cyan text-[10px]">ACTIVE HOME</span>
            </div>
            <div className="flex justify-between items-center bg-apex-panel p-2 rounded border border-apex-border">
              <span className="font-bold text-apex-text">Alex Chen (Quant Dev)</span>
              <span className="text-apex-green text-[10px]">BACKTESTING</span>
            </div>
            <div className="flex justify-between items-center bg-apex-panel p-2 rounded border border-apex-border">
              <span className="font-bold text-apex-text">Sarah Jenkins (Risk Mgr)</span>
              <span className="text-amber-400 text-[10px]">INSPECTING FTMO</span>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="text-apex-muted text-[10px]">IMMUTABLE AUDIT TRAIL</div>
          <div className="space-y-1.5 text-[11px]">
            <div className="p-2 bg-apex-panel rounded border border-apex-border flex justify-between">
              <span>[12:45:10] Alex Chen updated strategy parameters for APEX_M5_Engine</span>
              <span className="text-apex-muted">IP 192.168.1.42</span>
            </div>
            <div className="p-2 bg-apex-panel rounded border border-apex-border flex justify-between">
              <span>[12:30:04] Sarah Jenkins adjusted max daily drawdown limit to 4.0%</span>
              <span className="text-apex-muted">IP 10.0.0.15</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
