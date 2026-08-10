import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import type { ModuleView } from '../../types';
import { 
  Search, 
  Terminal, 
  TrendingUp, 
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
  X,
  ShieldAlert
} from 'lucide-react';

export const CommandPalette: React.FC = () => {
  const { commandPaletteOpen, setCommandPaletteOpen, setActiveModule, setSelectedSymbol, tickers, panicCloseAll } = useTerminal();
  const [query, setQuery] = useState('');

  if (!commandPaletteOpen) return null;

  const moduleActions: { id: ModuleView; label: string; icon: React.ElementType; desc: string; isAi?: boolean }[] = [
    { id: 'home', label: 'Mission Control', icon: Terminal, desc: 'Multi-chart workstation view & AI decision radar' },
    { id: 'trades', label: 'Live Positions', icon: TrendingUp, desc: 'Active execution trades, TP/SL levels, and risk' },
    { id: 'signals', label: 'Institutional Signals', icon: Zap, desc: 'AI confidence score & confluence matrix', isAi: true },
    { id: 'backtest', label: 'Backtest Lab', icon: FlaskConical, desc: 'Historical equity curves & Sharpe ratio' },
    { id: 'prop-firm', label: 'Prop Firm Rules', icon: ShieldCheck, desc: 'FTMO, FundedNext, and drawdown violation detection' },
    { id: 'intelligence', label: 'Market Intelligence', icon: BrainCircuit, desc: 'Orderbook heatmap, liquidations & macro data' },
    { id: 'news', label: 'AI News Feed', icon: Newspaper, desc: 'Sentiment scoring and economic calendar', isAi: true },
    { id: 'portfolio', label: 'Portfolio Analytics', icon: PieChart, desc: 'Exposure, tax report, & asset allocation' },
    { id: 'journal', label: 'Trade Journal', icon: BookOpen, desc: 'Psychology rating, trade notes, and mistake log' },
    { id: 'analytics', label: 'Strategy Performance', icon: BarChart3, desc: 'Best trading hours, win rate by day and symbol' },
    { id: 'copilot', label: 'XR AI Copilot Chat', icon: Bot, desc: 'Natural language strategy diagnostic assistant', isAi: true },
    { id: 'team', label: 'Team Collaboration Hub', icon: Users, desc: 'Shared notes, live user cursors & chat' },
    { id: 'automation', label: 'Automation & Webhooks', icon: Sliders, desc: 'TradingView alerts, Telegram & Discord bots' },
    { id: 'server', label: 'Server & Infra Health', icon: Server, desc: 'CPU, RAM, Docker containers, and Python logs' },
    { id: 'settings', label: 'Settings', icon: Settings, desc: 'Exchange API keys, dark themes, & keybindings' }
  ];

  const filteredModules = moduleActions.filter(m => 
    m.label.toLowerCase().includes(query.toLowerCase()) || 
    m.desc.toLowerCase().includes(query.toLowerCase())
  );

  const filteredSymbols = tickers.filter(t => 
    t.symbol.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelectModule = (mod: ModuleView) => {
    setActiveModule(mod);
    setCommandPaletteOpen(false);
  };

  const handleSelectSymbol = (sym: string) => {
    setSelectedSymbol(sym);
    setActiveModule('home');
    setCommandPaletteOpen(false);
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-start justify-center pt-20 px-4">
      <div className="bg-apex-bgSecondary border border-apex-border rounded-panel shadow-panel w-full max-w-2xl overflow-hidden font-sans">
        {/* Search Input */}
        <div className="flex items-center px-4 py-3 border-b border-apex-border bg-apex-surface">
          <Search className="w-4 h-4 text-apex-accent mr-3 shrink-0" />
          <input 
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command, search symbol (e.g. BTC), or jump to module..."
            className="w-full bg-transparent text-apex-text placeholder-apex-muted text-xs outline-none font-mono"
            autoFocus
          />
          <button 
            onClick={() => setCommandPaletteOpen(false)}
            className="text-apex-muted hover:text-apex-text p-1 rounded-md transition-apex"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Command Options List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1 font-mono text-xs">

          {/* Asset Tickers Jump */}
          {filteredSymbols.length > 0 && (
            <div className="pt-2">
              <div className="text-[10px] text-apex-muted uppercase tracking-wider px-2 py-1">Symbol Jump</div>
              <div className="grid grid-cols-2 gap-1">
                {filteredSymbols.map((t) => (
                  <div
                    key={t.symbol}
                    onClick={() => handleSelectSymbol(t.symbol)}
                    className="p-2 rounded-btn bg-apex-surface hover:bg-apex-hover border border-apex-border flex items-center justify-between cursor-pointer transition-apex"
                  >
                    <span className="font-bold text-apex-text">{t.symbol}</span>
                    <span className={`text-[11px] font-bold ${t.change24h >= 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
                      ${t.price.toLocaleString()} ({t.change24h >= 0 ? '+' : ''}{t.change24h}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Module Navigation Jump */}
          <div className="pt-2">
            <div className="text-[10px] text-apex-muted uppercase tracking-wider px-2 py-1">Navigation Modules</div>
            {filteredModules.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.id}
                  onClick={() => handleSelectModule(item.id)}
                  className="p-2.5 rounded-btn hover:bg-apex-hover border border-transparent hover:border-apex-border flex items-center justify-between cursor-pointer transition-apex"
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`w-4 h-4 ${item.isAi ? 'text-apex-ai' : 'text-apex-accent'}`} />
                    <div>
                      <div className="font-bold text-apex-text text-xs">{item.label}</div>
                      <div className="text-[10px] text-apex-muted">{item.desc}</div>
                    </div>
                  </div>
                  <span className="text-[10px] text-apex-muted bg-apex-bg px-2 py-0.5 rounded border border-apex-border">Select</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer info */}
        <div className="p-2 bg-apex-surface border-t border-apex-border flex justify-between items-center text-[10px] text-apex-muted font-mono">
          <span>Use ARROW keys to navigate, ENTER to select</span>
          <span>APEX QUANT OS</span>
        </div>
      </div>
    </div>
  );
};
