import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import type { ModuleView } from '../../types';
import { 
  LayoutDashboard, 
  TrendingUp, 
  SlidersHorizontal,
  Zap, 
  FlaskConical, 
  ShieldCheck, 
  BrainCircuit, 
  Newspaper, 
  PieChart, 
  BookOpen, 
  BarChart3, 
  Bot, 
  Users, 
  Sliders, 
  Server, 
  Settings,
  LogIn,
  ShieldAlert
} from 'lucide-react';

interface NavItem {
  id: ModuleView;
  label: string;
  icon: React.ElementType;
  badge?: string;
  isAi?: boolean;
}

export const Sidebar: React.FC = () => {
  const { activeModule, setActiveModule, logout, positions = [], signals = [] } = useTerminal();
  const safePositions = Array.isArray(positions) ? positions : [];
  const safeSignals = Array.isArray(signals) ? signals : [];

  const navItems: NavItem[] = [
    { id: 'login', label: 'Auth Gate', icon: LogIn },
    { id: 'home', label: 'Mission Control', icon: LayoutDashboard },
    { id: 'trades', label: 'Live Trades', icon: TrendingUp, badge: safePositions.length ? `${safePositions.length}` : undefined },
    { id: 'command-center', label: 'Command Center', icon: SlidersHorizontal, badge: 'LIVE' },
    { id: 'signals', label: 'AI Signals', icon: Zap, badge: `${safeSignals.length}`, isAi: true },
    { id: 'backtest', label: 'Backtest Lab', icon: FlaskConical },
    { id: 'prop-firm', label: 'Prop Firm Center', icon: ShieldCheck },
    { id: 'intelligence', label: 'Intelligence', icon: BrainCircuit },
    { id: 'news', label: 'AI News Feed', icon: Newspaper, isAi: true },
    { id: 'portfolio', label: 'Portfolio', icon: PieChart },
    { id: 'journal', label: 'Trade Journal', icon: BookOpen },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'copilot', label: 'XR AI Copilot', icon: Bot, badge: 'PRO', isAi: true },
    { id: 'team', label: 'Team Hub', icon: Users },
    { id: 'automation', label: 'Automation', icon: Sliders },
    { id: 'server', label: 'Server Center', icon: Server },
    { id: 'admin', label: 'Admin Master API', icon: ShieldAlert, badge: 'API' },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-14 hover:w-56 transition-all duration-150 bg-apex-bgSecondary border-r border-apex-border flex flex-col justify-between z-20 shrink-0 group overflow-hidden">
      {/* Top Module Items */}
      <div className="py-2 space-y-0.5 overflow-y-auto no-scrollbar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeModule === item.id;
          return (
            <button
              key={item.id}
              onClick={() => item.id === 'login' ? logout() : setActiveModule(item.id)}
              className={`w-full h-9 px-3.5 flex items-center space-x-3 transition-apex relative text-xs font-medium ${
                isActive 
                  ? 'bg-apex-surface text-apex-accent border-r-2 border-apex-accent' 
                  : 'text-apex-muted hover:text-apex-text hover:bg-apex-hover'
              }`}
              title={item.label}
            >
              <Icon className={`w-4 h-4 shrink-0 ${
                isActive 
                  ? 'text-apex-accent' 
                  : item.isAi 
                    ? 'text-apex-ai' 
                    : 'text-apex-muted group-hover:text-apex-textSecondary'
              }`} />
              <span className="whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                {item.label}
              </span>
              
              {/* Badge counter */}
              {item.badge && (
                <span className={`ml-auto opacity-0 group-hover:opacity-100 text-[10px] font-mono font-medium px-1.5 py-0.2 rounded ${
                  item.isAi ? 'bg-apex-ai/15 text-apex-ai border border-apex-ai/30' : 'bg-apex-surface text-apex-textSecondary border border-apex-border'
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer System Status */}
      <div className="p-2.5 border-t border-apex-border bg-apex-bg text-[10px] font-mono text-apex-muted flex items-center justify-center group-hover:justify-between px-3">
        <div className="w-1.5 h-1.5 rounded-full bg-apex-success shrink-0" />
        <span className="hidden group-hover:inline opacity-0 group-hover:opacity-100 transition-opacity uppercase tracking-wider">
          EVENT ENGINE ACTIVE
        </span>
      </div>
    </aside>
  );
};
