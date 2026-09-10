import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { 
  Terminal, 
  Search, 
  Wifi, 
  Server, 
  Cpu, 
  Database, 
  UserCheck, 
  Bell,
  SlidersHorizontal,
  ChevronRight,
  TrendingUp,
  ShieldCheck
} from 'lucide-react';

export const Header: React.FC = () => {
  const { 
    user, 
    health, 
    positions = [], 
    portfolio,
    setCommandPaletteOpen, 
    setActiveModule,
    logout,
    notifications,
    setNotificationsOpen,
    openCommandCenter
  } = useTerminal();

  const safePositions = Array.isArray(positions) ? positions.filter(p => p && String(p.status || 'OPEN').toUpperCase() === 'OPEN') : [];
  const totalUnrealizedPnl = Number(portfolio?.unrealizedPnl) || 0;
  const realizedPnl = Number(portfolio?.realizedPnl) || 0;
  const currentEquity = Number(portfolio?.currentEquity) || 10000.0;
  const initialCapital = Number(portfolio?.initialCapital) || 10000.0;
  
  const drawdownPct = initialCapital > 0
    ? Math.max(0, ((initialCapital - currentEquity) / initialCapital) * 100)
    : 0;
  
  const price = (value: number) => `$${Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const latency = (value: number) => value > 0 ? `${value}ms` : '12ms';

  return (
    <header className="h-11 bg-[#0D1117] border-b border-[#222C3A] flex items-center justify-between px-3 text-xs font-mono select-none shrink-0 z-30 shadow-sm">
      {/* Left Branding & Quick Nav */}
      <div className="flex items-center space-x-3">
        <div 
          className="flex items-center space-x-2.5 cursor-pointer group"
          onClick={() => setActiveModule('trades')}
        >
          <div className="w-7 h-7 rounded-lg bg-[#141A23] border border-[#2B384B] flex items-center justify-center text-blue-400 group-hover:border-blue-500/60 group-hover:text-blue-300 transition-apex shadow-inner">
            <Terminal className="w-3.5 h-3.5" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-extrabold text-sm tracking-tight text-white font-sans">APEX</span>
            <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">QUANT</span>
          </div>
        </div>

        {/* Command Center Quick Jumper */}
        {safePositions.length > 0 && safePositions[0]?.id && (
          <button
            onClick={() => openCommandCenter(safePositions[0].id)}
            className="hidden md:flex items-center space-x-1.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/40 text-blue-400 px-2.5 py-0.5 rounded text-[11px] font-bold transition-apex"
          >
            <SlidersHorizontal className="w-3 h-3" />
            <span>COMMAND ({safePositions.length})</span>
          </button>
        )}

        {/* Global Latency & Heartbeat Bar */}
        <div className="hidden xl:flex items-center space-x-1.5 pl-3 border-l border-[#222C3A] text-[10.5px]">
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-[#141A23] border border-[#222C3A] text-[#9CA3AF]">
            <Server className="w-3 h-3 text-[#6B7280]" />
            <span>API <strong className="text-white">{latency(health.vpsLatency)}</strong></span>
          </div>
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-[#141A23] border border-[#222C3A] text-[#9CA3AF]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 live-pulse-green"></span>
            <span>WS <strong className="text-white">LIVE</strong></span>
          </div>
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-[#141A23] border border-[#222C3A] text-[#9CA3AF]">
            <Cpu className="w-3 h-3 text-purple-400" />
            <span>AI <strong className="text-purple-300">ACTIVE</strong></span>
          </div>
        </div>
      </div>

      {/* Center High-Density Metrics Bar */}
      <div className="hidden lg:flex items-center space-x-3 bg-[#141A23] px-3 py-1 rounded-lg border border-[#222C3A] shadow-inner">
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-[#6B7280] uppercase tracking-wider font-semibold">NAV</span>
          <span className="font-bold text-white tabular-nums">${currentEquity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>

        <div className="w-px h-3.5 bg-[#283446]" />

        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-[#6B7280] uppercase tracking-wider font-semibold">UNREALIZED</span>
          <span className={`font-bold tabular-nums ${totalUnrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {totalUnrealizedPnl >= 0 ? '+' : '-'}{price(totalUnrealizedPnl)}
          </span>
        </div>

        <div className="w-px h-3.5 bg-[#283446]" />

        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-[#6B7280] uppercase tracking-wider font-semibold">REALIZED</span>
          <span className={`font-bold tabular-nums ${realizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {realizedPnl >= 0 ? '+' : '-'}{price(realizedPnl)}
          </span>
        </div>

        <div className="w-px h-3.5 bg-[#283446]" />

        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-[#6B7280] uppercase tracking-wider font-semibold">DRAWDOWN</span>
          <span className={`font-bold tabular-nums ${drawdownPct > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {drawdownPct.toFixed(2)}%
          </span>
        </div>

        <div className="w-px h-3.5 bg-[#283446]" />

        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-[#6B7280] uppercase tracking-wider font-semibold">PROP STATUS</span>
          <span className="text-emerald-400 font-bold flex items-center gap-0.5">
            <ShieldCheck className="w-3 h-3" />
            <span>SAFE</span>
          </span>
        </div>
      </div>

      {/* Right Controls & Profile */}
      <div className="flex items-center space-x-2">
        {/* Real-time Notification Bell */}
        <button 
          onClick={() => setNotificationsOpen(true)}
          className="relative p-1.5 rounded bg-[#141A23] hover:bg-[#1A222E] border border-[#222C3A] text-[#9CA3AF] hover:text-white transition-apex"
          title="Open Smart Notification Center"
        >
          <Bell className="w-3.5 h-3.5 text-blue-400" />
          {notifications.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-[8px] font-bold px-1 rounded-full">
              {notifications.length}
            </span>
          )}
        </button>

        {/* Command Palette Trigger */}
        <button 
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center space-x-2 bg-[#141A23] hover:bg-[#1A222E] border border-[#222C3A] px-2 py-1 rounded text-[#9CA3AF] hover:text-white transition-apex"
        >
          <Search className="w-3 h-3 text-[#6B7280]" />
          <span className="hidden md:inline text-[10.5px]">Command</span>
          <kbd className="hidden md:inline bg-[#080A0D] text-[9px] px-1.5 py-0.2 rounded border border-[#222C3A] text-[#6B7280] font-mono">⌘K</kbd>
        </button>

        {/* User Account Info */}
        <div 
          onClick={logout}
          title="Tizimdan chiqish (Log out)"
          className="flex items-center space-x-2 pl-2 border-l border-[#222C3A] cursor-pointer hover:opacity-85 transition-apex"
        >
          <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 border border-[#2B384B] flex items-center justify-center text-white text-[10px] font-bold">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'T'}
          </div>
          <div className="hidden sm:block text-left">
            <div className="font-semibold text-white text-[10.5px] leading-tight flex items-center gap-1 font-sans">
              <span>{user?.name?.split(' ')[0] || 'Trader'}</span>
              <UserCheck className="w-3 h-3 text-blue-400" />
            </div>
            <div className="text-[8.5px] text-[#6B7280] uppercase font-mono">{user?.role || 'PRO TRADER'}</div>
          </div>
        </div>
      </div>
    </header>
  );
};
