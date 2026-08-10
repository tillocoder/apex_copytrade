import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { PieChart, ShieldCheck, DollarSign, Calendar, FileText } from 'lucide-react';

export const PortfolioModule: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <PieChart className="w-5 h-5 text-apex-cyan" />
          <span>MULTI-ACCOUNT PORTFOLIO & ASSET ALLOCATION</span>
        </div>
        <button className="flex items-center space-x-1.5 bg-apex-panel hover:bg-apex-hover border border-apex-border px-3 py-1.5 rounded text-apex-text text-[11px]">
          <FileText className="w-3.5 h-3.5 text-apex-cyan" />
          <span>DOWNLOAD TAX REPORT</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="text-apex-muted text-[10px]">NET ASSET VALUE (NAV)</div>
          <div className="text-3xl font-bold text-apex-text">$324,250.00</div>
          <div className="text-apex-green font-bold">+18.4% YTD RETENTION</div>
        </div>
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2">
          <div className="text-apex-muted text-[10px]">EXPOSURE BY ASSET</div>
          <div className="space-y-1 text-[11px]">
            <div className="flex justify-between"><span>BTC:</span> <span className="font-bold text-apex-cyan">64.5%</span></div>
            <div className="flex justify-between"><span>ETH:</span> <span className="font-bold text-apex-cyan">22.1%</span></div>
            <div className="flex justify-between"><span>SOL:</span> <span className="font-bold text-apex-cyan">8.4%</span></div>
            <div className="flex justify-between"><span>USDT CASH:</span> <span className="font-bold text-apex-green">5.0%</span></div>
          </div>
        </div>
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-2">
          <div className="text-apex-muted text-[10px]">RISK EXPOSURE LIMITS</div>
          <div className="text-emerald-400 font-bold text-sm">Passes 100% Risk Policy</div>
          <div className="text-apex-muted text-[10px]">Max leverage capped at 25X across sub-accounts.</div>
        </div>
      </div>
    </div>
  );
};
