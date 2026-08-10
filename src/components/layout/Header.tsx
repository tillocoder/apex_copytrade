import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { 
  ShieldAlert, 
  Search, 
  Terminal, 
  Server, 
  Database, 
  Wifi, 
  Cpu, 
  UserCheck,
  Bell,
  SlidersHorizontal
} from 'lucide-react';

export const Header: React.FC = () => {
  const { 
    user, 
    health, 
    positions = [], 
    setCommandPaletteOpen, 
    panicCloseAll,
    setActiveModule,
    logout,
    notifications,
    setNotificationsOpen,
    openCommandCenter
  } = useTerminal();

  const safePositions = Array.isArray(positions) ? positions : [];
  const totalUnrealizedPnl = safePositions.reduce((acc, p) => acc + (p?.unrealizedPnl || 0), 0);

  return (
    <header className="h-12 bg-apex-bgSecondary border-b border-apex-border flex items-center justify-between px-3 text-xs font-mono select-none shrink-0 z-30">
      {/* Left Branding & Module Selector */}
      <div className="flex items-center space-x-3">
        <div 
          className="flex items-center space-x-2 cursor-pointer group"
          onClick={() => setActiveModule('home')}
        >
          <div className="w-7 h-7 rounded-md bg-apex-surface border border-apex-border flex items-center justify-center text-apex-accent group-hover:border-apex-accent transition-apex">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-xs tracking-wider text-apex-text flex items-center gap-1.5">
              <span>APEX</span>
              <span className="text-apex-accent font-medium text-[10px] px-1.5 py-0.2 rounded bg-apex-surface border border-apex-border">QUANT</span>
            </div>
          </div>
        </div>

        {/* Command Center Quick Jumper */}
        {safePositions.length > 0 && safePositions[0]?.id && (
          <button
            onClick={() => openCommandCenter(safePositions[0].id)}
            className="hidden md:flex items-center space-x-1.5 bg-apex-surface hover:bg-apex-hover border border-apex-accent text-apex-accent px-2.5 py-1 rounded-btn text-[11px] font-medium transition-apex"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>COMMAND CENTER ({safePositions.length})</span>
          </button>
        )}

        {/* Global Latency Bar */}
        <div className="hidden xl:flex items-center space-x-2 pl-3 border-l border-apex-border text-[11px]">
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-apex-surface border border-apex-border text-apex-textSecondary">
            <Server className="w-3 h-3 text-apex-muted" />
            <span>VPS: <strong className="text-apex-text">{health.vpsLatency}ms</strong></span>
          </div>
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-apex-surface border border-apex-border text-apex-textSecondary">
            <Wifi className="w-3 h-3 text-apex-muted" />
            <span>WS: <strong className="text-apex-text">{health.wsLatency}ms</strong></span>
          </div>
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-apex-surface border border-apex-border text-apex-textSecondary">
            <Database className="w-3 h-3 text-apex-muted" />
            <span>DB: <strong className="text-apex-text">{health.dbLatency}ms</strong></span>
          </div>
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-apex-surface border border-apex-border text-apex-textSecondary">
            <Cpu className="w-3 h-3 text-apex-ai" />
            <span>AI: <strong className="text-apex-ai">{health.aiEngineStatus}</strong></span>
          </div>
        </div>
      </div>

      {/* Center High-Density Metrics Bar */}
      <div className="hidden lg:flex items-center space-x-4 bg-apex-surface px-3 py-1 rounded-md border border-apex-border">
        <div>
          <div className="text-[9px] text-apex-muted tracking-wider uppercase">NAV EQUITY</div>
          <div className="font-bold text-apex-text">$324,250.00</div>
        </div>

        <div className="w-px h-5 bg-apex-border" />

        <div>
          <div className="text-[9px] text-apex-muted tracking-wider uppercase">UNREALIZED PNL</div>
          <div className={`font-bold ${totalUnrealizedPnl >= 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
            {totalUnrealizedPnl >= 0 ? '+' : ''}${totalUnrealizedPnl.toFixed(2)}
          </div>
        </div>

        <div className="w-px h-5 bg-apex-border" />

        <div>
          <div className="text-[9px] text-apex-muted tracking-wider uppercase">TODAY PNL</div>
          <div className="font-bold text-apex-success">+$3,210.50 (+1.0%)</div>
        </div>

        <div className="w-px h-5 bg-apex-border" />

        <div>
          <div className="text-[9px] text-apex-muted tracking-wider uppercase">CURRENT DD</div>
          <div className="font-bold text-apex-warning">1.40% / 5.0%</div>
        </div>

        <div className="w-px h-5 bg-apex-border" />

        <div>
          <div className="text-[9px] text-apex-muted tracking-wider uppercase">WIN RATE</div>
          <div className="font-bold text-apex-accent">68.4%</div>
        </div>
      </div>

      {/* Right Controls & Notifications */}
      <div className="flex items-center space-x-2">
        {/* Real-time Notification Bell */}
        <button 
          onClick={() => setNotificationsOpen(true)}
          className="relative p-1.5 rounded-btn bg-apex-surface hover:bg-apex-hover border border-apex-border text-apex-textSecondary hover:text-apex-text transition-apex"
          title="Open Smart Notification Center"
        >
          <Bell className="w-4 h-4 text-apex-accent" />
          {notifications.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-apex-accent text-black text-[9px] font-bold px-1 rounded-full">
              {notifications.length}
            </span>
          )}
        </button>

        {/* Command Palette Trigger */}
        <button 
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center space-x-2 bg-apex-surface hover:bg-apex-hover border border-apex-border px-2.5 py-1 rounded-btn text-apex-textSecondary hover:text-apex-text transition-apex"
        >
          <Search className="w-3.5 h-3.5 text-apex-muted" />
          <span className="hidden md:inline text-[11px]">Command Palette</span>
          <kbd className="hidden md:inline bg-apex-bg text-[9px] px-1.5 py-0.5 rounded border border-apex-border text-apex-muted font-mono">⌘K</kbd>
        </button>

        {/* User Account Info */}
        <div 
          onClick={logout}
          title="Tizimdan chiqish (Log out)"
          className="flex items-center space-x-2 pl-2 border-l border-apex-border cursor-pointer hover:opacity-80 transition-apex"
        >
          <img 
            src={user.avatar} 
            alt={user.name} 
            className="w-6 h-6 rounded-full border border-apex-border object-cover"
          />
          <div className="hidden sm:block text-left">
            <div className="font-semibold text-apex-text text-[11px] leading-tight flex items-center gap-1">
              <span>{user.name.split(' ')[0]}</span>
              <UserCheck className="w-3 h-3 text-apex-accent" />
            </div>
            <div className="text-[9px] text-apex-muted uppercase font-mono">{user.role}</div>
          </div>
        </div>
      </div>
    </header>
  );
};
