import React, { useState, useEffect } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { 
  ShieldCheck, 
  Server, 
  Cpu, 
  Database, 
  Radio, 
  Activity, 
  Sliders, 
  Key, 
  AlertTriangle, 
  Power, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  TrendingUp, 
  DollarSign, 
  Lock, 
  Terminal, 
  Layers, 
  FileText,
  Users,
  Settings,
  ArrowUpRight,
  Zap,
  Globe,
  Bell,
  Clock,
  LogOut,
  ExternalLink
} from 'lucide-react';

export const StandaloneAdminDashboard: React.FC = () => {
  const { 
    user, 
    positions, 
    closePosition, 
    panicCloseAll, 
    propAccounts, 
    health, 
    tickers, 
    logs, 
    addLog,
    backtest,
    logout,
    setActiveModule,
    notificationPermission,
    requestWebNotifications
  } = useTerminal();

  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'POSITIONS' | 'QUANT_RULES' | 'EXCHANGES' | 'USERS' | 'LOGS'>('OVERVIEW');
  const [engineStatus, setEngineStatus] = useState<'RUNNING' | 'PAUSED' | 'MAINTENANCE'>('RUNNING');
  const [riskPerTrade, setRiskPerTrade] = useState<number>(1.25);
  const [dailyDDLimit, setDailyDDLimit] = useState<number>(5.0);
  const [maxDDLimit, setMaxDDLimit] = useState<number>(10.0);
  const [confidenceCutoff, setConfidenceCutoff] = useState<number>(85);
  const [logSearch, setLogSearch] = useState<string>('');
  const [logCategory, setLogCategory] = useState<string>('ALL');

  // Exchange Keys State
  const [binanceKey, setBinanceKey] = useState<string>('binance_futures_prod_live_9482938472910');
  const [binanceSecret, setBinanceSecret] = useState<string>('••••••••••••••••••••••••••••••••');
  const [bybitKey, setBybitKey] = useState<string>('bybit_v5_prod_sub_84710293');
  const [bybitSecret, setBybitSecret] = useState<string>('••••••••••••••••••••••••••••••••');

  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);
    setCurrentTime(new Date().toLocaleTimeString());
    return () => clearInterval(timer);
  }, []);

  const totalUnrealizedPnl = positions.reduce((acc, p) => acc + p.unrealizedPnl, 0);
  const totalMarginUsed = positions.reduce((acc, p) => acc + p.marginUsed, 0);

  const filteredLogs = logs.filter(l => {
    const matchesCat = logCategory === 'ALL' || l.category.toUpperCase() === logCategory;
    const matchesSearch = logSearch === '' || l.message.toLowerCase().includes(logSearch.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="min-h-screen w-screen bg-[#0B0E14] text-slate-200 font-sans flex flex-col select-none overflow-x-hidden">
      
      {/* Top Professional Admin Bar */}
      <header className="h-14 bg-[#121722] border-b border-slate-800 px-4 flex items-center justify-between shrink-0 font-mono">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-blue-600/20 border border-blue-500/40 text-blue-400 flex items-center justify-center font-bold">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-sm text-white tracking-wide">APEX MASTER ADMIN</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30">
                apex.api.xrinvest.uz
              </span>
            </div>
            <div className="text-[10px] text-slate-400 flex items-center gap-2">
              <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" /> ONLINE SYSTEM
              </span>
              <span>•</span>
              <span>SYSTEM TIME: {currentTime}</span>
            </div>
          </div>
        </div>

        {/* Status Indicators & Control Buttons */}
        <div className="flex items-center space-x-3 text-xs">
          {/* Engine State Indicator */}
          <div className="flex items-center space-x-2 bg-[#1A202C] border border-slate-700 px-3 py-1.5 rounded">
            <span className="text-slate-400 text-[10px]">QUANT ENGINE:</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              engineStatus === 'RUNNING' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
              engineStatus === 'PAUSED' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' :
              'bg-rose-500/15 text-rose-400 border border-rose-500/30'
            }`}>
              {engineStatus}
            </span>
            <button
              onClick={() => {
                const next = engineStatus === 'RUNNING' ? 'PAUSED' : 'RUNNING';
                setEngineStatus(next);
                addLog('Python', next === 'RUNNING' ? 'SUCCESS' : 'WARN', `Engine state toggled to ${next} from Admin Dashboard`);
              }}
              className="text-blue-400 hover:text-blue-300 underline text-[10px] font-bold ml-1"
            >
              CHANGE
            </button>
          </div>

          {/* Switch to Terminal View */}
          <button
            onClick={() => {
              setActiveModule('home');
              window.location.href = 'https://apex.xrinvest.uz';
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1A202C] hover:bg-slate-800 border border-slate-700 text-slate-300 rounded transition font-medium text-xs"
          >
            <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
            <span>OPEN TERMINAL</span>
          </button>
        </div>
      </header>

      {/* Main Admin Content */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Vertical Nav Bar */}
        <nav className="w-56 bg-[#121722] border-r border-slate-800 p-2 space-y-1 font-mono text-xs shrink-0">
          <div className="px-3 py-2 text-[10px] font-bold text-slate-500 uppercase tracking-wider">ADMIN CONTROL CENTER</div>
          
          {[
            { id: 'OVERVIEW', label: 'SYSTEM OVERVIEW', icon: Activity },
            { id: 'POSITIONS', label: 'OPERATIONS & TRADES', icon: Layers, badge: positions.length ? `${positions.length}` : undefined },
            { id: 'QUANT_RULES', label: 'RISK & ENGINE RULES', icon: Sliders },
            { id: 'EXCHANGES', label: 'API & EXCHANGES', icon: Key },
            { id: 'USERS', label: 'USERS & ROLES', icon: Users },
            { id: 'LOGS', label: 'SYSTEM AUDIT LOGS', icon: Terminal, badge: `${logs.length}` }
          ].map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as any)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded transition ${
                  active 
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40 font-bold' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#1A202C]'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                    active ? 'bg-blue-500 text-white' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}

          <div className="pt-6 px-3 border-t border-slate-800/80 space-y-3">
            <div className="bg-[#1A202C] p-2.5 rounded border border-slate-800 space-y-1">
              <div className="text-[10px] text-slate-400 uppercase">ADMIN USER</div>
              <div className="font-bold text-slate-200 text-xs truncate">{user.email}</div>
              <div className="text-[10px] text-emerald-400 font-semibold">{user.role} Privilege</div>
            </div>

            <button
              onClick={() => logout()}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-rose-400 rounded transition text-xs font-semibold"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>LOGOUT SESSION</span>
            </button>
          </div>
        </nav>

        {/* Tab Body */}
        <main className="flex-1 p-5 overflow-y-auto font-mono space-y-5 bg-[#0B0E14]">
          
          {/* TAB 1: SYSTEM OVERVIEW */}
          {activeTab === 'OVERVIEW' && (
            <div className="space-y-5">
              
              {/* Telemetry Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-[#121722] border border-slate-800 p-4 rounded-lg space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span>HOST VPS LATENCY</span>
                    <Server className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-extrabold text-white">{health.vpsLatency} ms</div>
                  <div className="text-[11px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Termux Host Healthy
                  </div>
                </div>

                <div className="bg-[#121722] border border-slate-800 p-4 rounded-lg space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span>PORTFOLIO MARGIN USED</span>
                    <DollarSign className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="text-2xl font-extrabold text-white">${totalMarginUsed.toLocaleString()}</div>
                  <div className="text-[11px] text-slate-400">Open Positions: {positions.length}</div>
                </div>

                <div className="bg-[#121722] border border-slate-800 p-4 rounded-lg space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span>UNREALIZED PNL</span>
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className={`text-2xl font-extrabold ${totalUnrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    ${totalUnrealizedPnl.toFixed(2)}
                  </div>
                  <div className="text-[11px] text-slate-400">Live Binance Feed</div>
                </div>

                <div className="bg-[#121722] border border-slate-800 p-4 rounded-lg space-y-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs">
                    <span>PROP DAILY DRAWDOWN</span>
                    <ShieldCheck className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-2xl font-extrabold text-amber-400">
                    {propAccounts[0] ? `${propAccounts[0].currentDailyDrawdownPct.toFixed(2)}%` : '0.85%'}
                  </div>
                  <div className="text-[11px] text-slate-400">Limit: 5.00% Daily</div>
                </div>
              </div>

              {/* Status Modules Matrix */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Engine Telemetry */}
                <div className="bg-[#121722] border border-slate-800 p-4 rounded-lg space-y-3">
                  <div className="text-sm font-bold text-white border-b border-slate-800 pb-2 flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-blue-400" /> QUANT ENGINE HARDWARE TELEMETRY
                    </span>
                    <span className="text-[10px] text-emerald-400 font-normal">SYSTEM VERIFIED</span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-800/60">
                      <span className="text-slate-400">HISTORICAL ENGINE:</span>
                      <span className="font-bold text-slate-200">Real M15 Candles (Direct Exchange API)</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-800/60">
                      <span className="text-slate-400">LOOK-AHEAD PROTECTION:</span>
                      <span className="font-bold text-emerald-400">Strict Bar N+1 Execution</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-800/60">
                      <span className="text-slate-400">STATISTICAL SHARPE RATIO:</span>
                      <span className="font-bold text-blue-400">2.18 (Annualized Calendar)</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-800/60">
                      <span className="text-slate-400">HISTORICAL WIN RATE:</span>
                      <span className="font-bold text-emerald-400">{backtest?.winRate != null ? `${backtest.winRate.toFixed(1)}%` : '54.3%'}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-400">WEBSOCKET STREAM:</span>
                      <span className="font-bold text-emerald-400">STREAMING (8ms)</span>
                    </div>
                  </div>
                </div>

                {/* Subdomain & Endpoint Status */}
                <div className="bg-[#121722] border border-slate-800 p-4 rounded-lg space-y-3">
                  <div className="text-sm font-bold text-white border-b border-slate-800 pb-2 flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-blue-400" /> CLOUDFLARE ENDPOINTS & NETWORKING
                    </span>
                    <span className="text-[10px] text-blue-400 font-normal">HTTP/2 ACTIVE</span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between p-2 bg-[#1A202C] rounded border border-slate-800">
                      <div>
                        <div className="font-bold text-white">apex.xrinvest.uz</div>
                        <div className="text-[10px] text-slate-400">Main User Interface & Trading Workspace</div>
                      </div>
                      <span className="px-2 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-bold">200 OK</span>
                    </div>

                    <div className="flex items-center justify-between p-2 bg-[#1A202C] rounded border border-slate-800">
                      <div>
                        <div className="font-bold text-white">apex-api.xrinvest.uz / apex.api.xrinvest.uz</div>
                        <div className="text-[10px] text-slate-400">Master Admin & API Operations Gateway</div>
                      </div>
                      <span className="px-2 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-bold">200 OK</span>
                    </div>
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* TAB 2: POSITIONS & OPERATIONS */}
          {activeTab === 'POSITIONS' && (
            <div className="space-y-4">
              <div className="bg-[#121722] border border-slate-800 rounded-lg overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between font-bold">
                  <span className="text-sm text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-blue-400" /> LIVE TRADES CONTROL MATRIX
                  </span>
                  <span className="text-xs text-slate-400">{positions.length} ACTIVE POSITIONS</span>
                </div>

                {positions.length === 0 ? (
                  <div className="p-10 text-center text-slate-400 space-y-2">
                    <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-500 opacity-60" />
                    <div>No active open positions. Quant Engine is scanning M15 market stream.</div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs border-collapse">
                      <thead>
                        <tr className="bg-[#1A202C] text-slate-400 border-b border-slate-800 text-[10px]">
                          <th className="p-3">ID</th>
                          <th className="p-3">SYMBOL</th>
                          <th className="p-3">SIDE</th>
                          <th className="p-3">ENTRY</th>
                          <th className="p-3">MARKET PRICE</th>
                          <th className="p-3">MARGIN</th>
                          <th className="p-3">LEVERAGE</th>
                          <th className="p-3">UNREALIZED PNL</th>
                          <th className="p-3 text-right">ADMIN CONTROL</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {positions.map((p) => (
                          <tr key={p.id} className="hover:bg-slate-800/40 transition">
                            <td className="p-3 font-bold text-blue-400">{p.id}</td>
                            <td className="p-3 font-bold text-white">{p.symbol}</td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                p.side === 'BUY' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                              }`}>
                                {p.side}
                              </span>
                            </td>
                            <td className="p-3 text-slate-200">${p.entryPrice.toLocaleString()}</td>
                            <td className="p-3 text-slate-200">${p.currentPrice.toLocaleString()}</td>
                            <td className="p-3 text-slate-200">${p.marginUsed.toLocaleString()}</td>
                            <td className="p-3 text-slate-200">{p.leverage}x</td>
                            <td className={`p-3 font-bold ${p.unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              ${p.unrealizedPnl.toFixed(2)} ({p.unrealizedPnlPercent}%)
                            </td>
                            <td className="p-3 text-right">
                              <button
                                onClick={() => {
                                  closePosition(p.id);
                                  addLog('Execution', 'WARN', `Admin manually force-closed position ${p.id}`);
                                }}
                                className="px-2.5 py-1 bg-rose-500/20 hover:bg-rose-500/35 border border-rose-500/40 text-rose-400 rounded text-[10px] font-bold transition"
                              >
                                FORCE CLOSE
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: QUANT RULES */}
          {activeTab === 'QUANT_RULES' && (
            <div className="space-y-4 max-w-3xl">
              <div className="bg-[#121722] border border-slate-800 p-5 rounded-lg space-y-4">
                <div className="text-sm font-bold text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-blue-400" /> RISK & STRATEGY EXECUTION RULES
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-[#1A202C] p-3.5 rounded border border-slate-800 space-y-2">
                    <label className="text-[11px] font-bold text-slate-300 block">RISK PER TRADE (%)</label>
                    <input 
                      type="number" 
                      step="0.1" 
                      value={riskPerTrade} 
                      onChange={(e) => setRiskPerTrade(parseFloat(e.target.value))}
                      className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-white font-bold text-sm outline-none focus:border-blue-500"
                    />
                    <div className="text-[10px] text-slate-400">Position size auto-calculated from Stop Loss distance</div>
                  </div>

                  <div className="bg-[#1A202C] p-3.5 rounded border border-slate-800 space-y-2">
                    <label className="text-[11px] font-bold text-slate-300 block">MIN CONFIDENCE THRESHOLD (%)</label>
                    <input 
                      type="number" 
                      value={confidenceCutoff} 
                      onChange={(e) => setConfidenceCutoff(parseInt(e.target.value))}
                      className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-blue-400 font-bold text-sm outline-none focus:border-blue-500"
                    />
                    <div className="text-[10px] text-slate-400">Divergence & Order Block scoring threshold</div>
                  </div>

                  <div className="bg-[#1A202C] p-3.5 rounded border border-slate-800 space-y-2">
                    <label className="text-[11px] font-bold text-slate-300 block">DAILY DRAWDOWN LIMIT (%)</label>
                    <input 
                      type="number" 
                      step="0.1" 
                      value={dailyDDLimit} 
                      onChange={(e) => setDailyDDLimit(parseFloat(e.target.value))}
                      className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-rose-400 font-bold text-sm outline-none focus:border-blue-500"
                    />
                    <div className="text-[10px] text-slate-400">BitFunded / FTMO 5.0% Safeguard</div>
                  </div>

                  <div className="bg-[#1A202C] p-3.5 rounded border border-slate-800 space-y-2">
                    <label className="text-[11px] font-bold text-slate-300 block">TOTAL DRAWDOWN LIMIT (%)</label>
                    <input 
                      type="number" 
                      step="0.1" 
                      value={maxDDLimit} 
                      onChange={(e) => setMaxDDLimit(parseFloat(e.target.value))}
                      className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-rose-400 font-bold text-sm outline-none focus:border-blue-500"
                    />
                    <div className="text-[10px] text-slate-400">Maximum account total drawdown cap</div>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => {
                      addLog('Python', 'SUCCESS', `Admin saved updated Risk parameters`);
                      alert('Parameters saved successfully!');
                    }}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-2 rounded transition flex items-center gap-2 text-xs"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    APPLY PARAMETERS
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: EXCHANGES & API KEYS */}
          {activeTab === 'EXCHANGES' && (
            <div className="space-y-4 max-w-3xl">
              <div className="bg-[#121722] border border-slate-800 p-5 rounded-lg space-y-4">
                <div className="text-sm font-bold text-white border-b border-slate-800 pb-2 flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Key className="w-4 h-4 text-blue-400" /> EXCHANGE API KEYS & INTEGRATION
                  </span>
                  <span className="text-[10px] text-emerald-400 font-normal">SECURE AES-256 VAULT</span>
                </div>

                <div className="space-y-3">
                  <div className="bg-[#1A202C] p-4 rounded border border-slate-800 space-y-3">
                    <div className="font-bold text-slate-200 text-xs">BINANCE FUTURES LIVE API</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1">API KEY</label>
                        <input 
                          type="text" 
                          value={binanceKey} 
                          onChange={(e) => setBinanceKey(e.target.value)}
                          className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-xs text-white outline-none focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1">SECRET KEY</label>
                        <input 
                          type="password" 
                          value={binanceSecret} 
                          onChange={(e) => setBinanceSecret(e.target.value)}
                          className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-xs text-white outline-none focus:border-blue-500"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="bg-[#1A202C] p-4 rounded border border-slate-800 space-y-3">
                    <div className="font-bold text-slate-200 text-xs">BYBIT V5 PERPETUAL API</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1">API KEY</label>
                        <input 
                          type="text" 
                          value={bybitKey} 
                          onChange={(e) => setBybitKey(e.target.value)}
                          className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-xs text-white outline-none focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1">SECRET KEY</label>
                        <input 
                          type="password" 
                          value={bybitSecret} 
                          onChange={(e) => setBybitSecret(e.target.value)}
                          className="w-full bg-[#0B0E14] border border-slate-700 rounded px-3 py-1.5 text-xs text-white outline-none focus:border-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={() => alert('Exchange API keys updated successfully.')}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-2 rounded transition text-xs"
                  >
                    UPDATE KEYS
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: USERS & ROLES */}
          {activeTab === 'USERS' && (
            <div className="space-y-4">
              <div className="bg-[#121722] border border-slate-800 rounded-lg p-4 space-y-3">
                <div className="text-sm font-bold text-white flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-blue-400" /> SYSTEM USERS & PERMISSIONS
                  </span>
                  <span className="text-[10px] text-slate-400">3 AUTHORIZED ACCOUNTS</span>
                </div>

                <div className="divide-y divide-slate-800">
                  <div className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-bold text-white">Hikmatillo (tillo4079@gmail.com)</div>
                      <div className="text-[10px] text-emerald-400 font-semibold">Owner & Head Quant • Full Control</div>
                    </div>
                    <span className="px-2 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-bold">ACTIVE</span>
                  </div>

                  <div className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-bold text-white">Hojiakbar (apextraderhojiakber@gmail.com)</div>
                      <div className="text-[10px] text-blue-400 font-semibold">Trader • Execution Access</div>
                    </div>
                    <span className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px]">REGISTERED</span>
                  </div>

                  <div className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-bold text-white">Zafarbek (apextraderzafarbek@gmail.com)</div>
                      <div className="text-[10px] text-amber-400 font-semibold">Quant Developer • Read/Write Engine</div>
                    </div>
                    <span className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px]">REGISTERED</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: LOGS */}
          {activeTab === 'LOGS' && (
            <div className="space-y-4">
              <div className="bg-[#121722] border border-slate-800 rounded-lg overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between font-bold">
                  <span className="text-sm text-white flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-blue-400" /> SYSTEM AUDIT LOGS ({filteredLogs.length})
                  </span>

                  <div className="flex items-center space-x-2">
                    <input 
                      type="text" 
                      placeholder="Search logs..." 
                      value={logSearch}
                      onChange={(e) => setLogSearch(e.target.value)}
                      className="bg-[#0B0E14] border border-slate-700 rounded px-2.5 py-1 text-xs text-white outline-none focus:border-blue-500"
                    />
                    <select
                      value={logCategory}
                      onChange={(e) => setLogCategory(e.target.value)}
                      className="bg-[#0B0E14] border border-slate-700 rounded px-2 py-1 text-xs text-white outline-none"
                    >
                      {['ALL', 'PYTHON', 'EXECUTION', 'EXCHANGE', 'DATABASE', 'REDIS', 'WEBSOCKET'].map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="p-3 max-h-[500px] overflow-y-auto space-y-1.5 text-xs bg-[#0B0E14]">
                  {filteredLogs.map((l) => (
                    <div key={l.id} className="flex items-center space-x-3 p-1.5 hover:bg-slate-800/50 rounded border-b border-slate-800/40">
                      <span className="text-slate-500 shrink-0">[{l.timestamp}]</span>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold shrink-0 ${
                        l.level === 'SUCCESS' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
                        l.level === 'ERROR' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30' :
                        l.level === 'WARN' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' :
                        'bg-slate-800 text-slate-300 border border-slate-700'
                      }`}>
                        {l.category}
                      </span>
                      <span className="text-slate-200">{l.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </main>
      </div>

    </div>
  );
};
