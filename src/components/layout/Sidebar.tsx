import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import type { ModuleView } from '../../types';
import { 
  TrendingUp, 
  SlidersHorizontal,
  Zap, 
  FlaskConical, 
  BrainCircuit, 
  Newspaper, 
  BookOpen, 
  BarChart3, 
  Bot, 
  Users, 
  Sliders, 
  Settings,
  LogIn,
  ShieldAlert,
  Flame
} from 'lucide-react';

interface NavSection {
  title?: string;
  items: Array<{
    id: ModuleView;
    label: string;
    icon: React.ElementType;
    badge?: string;
    isAi?: boolean;
  }>;
}

export const Sidebar: React.FC = () => {
  const { activeModule, setActiveModule, logout, positions = [], signals = [] } = useTerminal();
  const safePositions = Array.isArray(positions) ? positions.filter(p => p && String(p.status || 'OPEN').toUpperCase() === 'OPEN') : [];
  const safeSignals = Array.isArray(signals) ? signals.filter(s => s && String(s.status || 'ACTIVE').toUpperCase() === 'ACTIVE') : [];

  const sections: NavSection[] = [
    {
      title: "TRADING",
      items: [
        { id: 'trades', label: 'Live Trades', icon: TrendingUp, badge: safePositions.length > 0 ? `${safePositions.length}` : undefined },
        { id: 'command-center', label: 'Command Center', icon: SlidersHorizontal, badge: 'LIVE' },
        { id: 'signals', label: 'AI Signals', icon: Zap, badge: safeSignals.length > 0 ? `${safeSignals.length}` : undefined, isAi: true },
        { id: 'binance-futures', label: 'Binance ETH 100x', icon: Flame, badge: '100X', isAi: true },
      ]
    },
    {
      title: "QUANT & PROP",
      items: [
        { id: 'backtest', label: 'Backtest Lab', icon: FlaskConical },
        { id: 'analytics', label: 'Execution Metrics', icon: BarChart3 },
      ]
    },
    {
      title: "INTELLIGENCE",
      items: [
        { id: 'intelligence', label: 'Market Radar', icon: BrainCircuit },
        { id: 'copilot', label: 'XR AI Copilot', icon: Bot, badge: 'PRO', isAi: true },
        { id: 'news', label: 'Macro News Feed', icon: Newspaper, isAi: true },
        { id: 'journal', label: 'Trade Journal', icon: BookOpen },
      ]
    },
    {
      title: "SYSTEM",
      items: [
        { id: 'automation', label: 'Automation & Hooks', icon: Sliders },
        { id: 'admin', label: 'Admin Master API', icon: ShieldAlert, badge: 'API' },
        { id: 'settings', label: 'Terminal Settings', icon: Settings },
      ]
    }
  ];

  return (
    <aside className="w-12 hover:w-56 transition-all duration-150 ease-out bg-[#0A1224] border-r border-[#1C2E52] flex flex-col justify-between z-20 shrink-0 group overflow-hidden shadow-xl">
      {/* Top Module Items */}
      <div className="py-2 overflow-y-auto no-scrollbar space-y-3">
        {sections.map((sec, sIdx) => (
          <div key={sIdx} className="space-y-0.5">
            {sec.title && (
              <div className="px-3 py-1 text-[8.5px] font-bold tracking-wider text-slate-400 uppercase opacity-0 group-hover:opacity-100 transition-opacity duration-150 font-mono">
                {sec.title}
              </div>
            )}
            {sec.items.map((item) => {
              const Icon = item.icon;
              const isActive = activeModule === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveModule(item.id)}
                  className={`w-full h-8 px-3 flex items-center space-x-2.5 transition-apex relative text-xs font-medium ${
                    isActive 
                      ? 'bg-cyan-500/15 text-cyan-200 font-semibold' 
                      : 'text-slate-400 hover:text-white hover:bg-[#0E1B38]'
                  }`}
                  title={item.label}
                >
                  {/* Active Indicator Strip */}
                  {isActive && (
                    <div className="absolute left-0 top-1 bottom-1 w-0.5 bg-cyan-400 rounded-r shadow-[0_0_10px_rgba(6,182,212,0.9)]" />
                  )}

                  <Icon className={`w-3.5 h-3.5 shrink-0 ${
                    isActive 
                      ? 'text-cyan-400' 
                      : item.isAi 
                        ? 'text-purple-400' 
                        : 'text-slate-400 group-hover:text-[#9CA3AF]'
                  }`} />
                  
                  <span className="whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-[11.5px] font-sans">
                    {item.label}
                  </span>
                  
                  {/* Badge counter */}
                  {item.badge && (
                    <span className={`ml-auto opacity-0 group-hover:opacity-100 text-[9px] font-mono font-bold px-1.5 py-0.2 rounded ${
                      item.isAi ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30' : 'bg-[#080E1C] text-slate-300 border border-[#1C2E52]'
                    }`}>
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* Footer System Status */}
      <div className="p-2 border-t border-[#1C2E52] bg-[#080A0D] text-[9.5px] font-mono text-slate-400 flex items-center justify-center group-hover:justify-between px-3">
        <div className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 live-pulse-green shrink-0" />
          <span className="hidden group-hover:inline opacity-0 group-hover:opacity-100 transition-opacity uppercase tracking-wider font-bold text-[#9CA3AF]">
            ENGINE ONLINE
          </span>
        </div>
        <span className="hidden group-hover:inline opacity-0 group-hover:opacity-100 text-[8.5px] text-slate-400">
          v5.2
        </span>
      </div>
    </aside>
  );
};
