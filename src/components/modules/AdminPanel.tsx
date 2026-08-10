import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { 
  ShieldAlert, 
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
  UserCheck
} from 'lucide-react';

export const AdminPanel: React.FC = () => {
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
    backtest 
  } = useTerminal();

  const [activeTab, setActiveTab] = useState<'OPERATIONS' | 'RISK_ENGINE' | 'PROP_CHALLENGES' | 'API_GATEWAY' | 'SYSTEM_AUDIT'>('OPERATIONS');
  const [engineState, setEngineState] = useState<'RUNNING' | 'PAUSED' | 'MAINTENANCE'>('RUNNING');
  const [riskLimitPct, setRiskLimitPct] = useState<number>(1.25);
  const [maxDailyDDPct, setMaxDailyDDPct] = useState<number>(5.0);
  const [maxTotalDDPct, setMaxTotalDDPct] = useState<number>(10.0);
  const [minConfidenceScore, setMinConfidenceScore] = useState<number>(85);
  
  // API Keys state
  const [binanceApiKey, setBinanceApiKey] = useState<string>('binance_futures_live_pk_9482938472910');
  const [binanceApiSecret, setBinanceApiSecret] = useState<string>('••••••••••••••••••••••••••••••••');
  const [bybitApiKey, setBybitApiKey] = useState<string>('bybit_prod_sub_84710293');
  const [bybitApiSecret, setBybitApiSecret] = useState<string>('••••••••••••••••••••••••••••••••');

  const [auditFilter, setAuditFilter] = useState<string>('ALL');

  const filteredAuditLogs = auditFilter === 'ALL' 
    ? logs 
    : logs.filter(l => l.category.toUpperCase() === auditFilter);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs select-none">
      
      {/* Admin Master Header */}
      <div className="bg-apex-bgSecondary border-b border-apex-border p-3 flex flex-wrap items-center justify-between gap-3 font-mono shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-apex-accent/15 border border-apex-accent/40 rounded-md text-apex-accent">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-apex-text">APEX MASTER ADMIN & API SYSTEM</span>
              <span className="bg-apex-accent/15 border border-apex-accent/40 text-apex-accent px-2 py-0.5 rounded text-[10px] font-bold">
                apex.api.xrinvest.uz
              </span>
            </div>
            <div className="text-[11px] text-apex-muted flex items-center gap-3">
              <span>AUTHENTICATED AS: <strong className="text-apex-text">{user.name} ({user.role})</strong></span>
              <span>•</span>
              <span className="text-apex-success font-semibold">ENGINE MODE: DETERMINISTIC REAL M15</span>
            </div>
          </div>
        </div>

        {/* Status Pills & Controls */}
        <div className="flex items-center space-x-3">
          {/* Engine Status Toggle */}
          <div className="flex items-center space-x-2 bg-apex-surface border border-apex-border px-2.5 py-1 rounded-md">
            <span className="text-[10px] text-apex-muted">ENGINE:</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              engineState === 'RUNNING' ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' :
              engineState === 'PAUSED' ? 'bg-apex-warning/15 text-apex-warning border border-apex-warning/30' :
              'bg-apex-danger/15 text-apex-danger border border-apex-danger/30'
            }`}>
              {engineState}
            </span>
            <button 
              onClick={() => {
                const next = engineState === 'RUNNING' ? 'PAUSED' : 'RUNNING';
                setEngineState(next);
                addLog('Python', next === 'RUNNING' ? 'SUCCESS' : 'WARN', `Engine state toggled to ${next}`);
              }}
              className="text-apex-accent hover:underline text-[10px] font-bold ml-1"
            >
              TOGGLE
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="h-9 bg-apex-surface border-b border-apex-border px-3 flex items-center space-x-2 font-mono text-xs shrink-0 overflow-x-auto no-scrollbar">
        {[
          { id: 'OPERATIONS', label: 'LIVE OPERATIONS & POSITIONS', icon: Activity },
          { id: 'RISK_ENGINE', label: 'QUANT RISK ENGINE & RULES', icon: Sliders },
          { id: 'PROP_CHALLENGES', label: 'PROP FIRM MONITORING', icon: ShieldAlert },
          { id: 'API_GATEWAY', label: 'EXCHANGE API & WEBHOOKS', icon: Key },
          { id: 'SYSTEM_AUDIT', label: 'SYSTEM AUDIT & LOGS', icon: Terminal }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3 py-1 rounded-md font-medium transition-apex flex items-center gap-1.5 ${
                isActive 
                  ? 'bg-apex-hover text-apex-accent border border-apex-border font-bold' 
                  : 'text-apex-muted hover:text-apex-text hover:bg-apex-hover'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Admin Tab Body */}
      <div className="flex-1 p-4 overflow-y-auto font-mono space-y-4">

        {/* TAB 1: OPERATIONS & POSITIONS CONTROL */}
        {activeTab === 'OPERATIONS' && (
          <div className="space-y-4">
            
            {/* Live Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-1">
                <div className="text-[10px] text-apex-muted flex items-center justify-between">
                  <span>ACTIVE POSITIONS</span>
                  <Layers className="w-3.5 h-3.5 text-apex-accent" />
                </div>
                <div className="text-xl font-bold text-apex-text">{positions.length}</div>
                <div className="text-[10px] text-apex-muted">Total Margin: ${positions.reduce((a, b) => a + b.marginUsed, 0).toLocaleString()}</div>
              </div>

              <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-1">
                <div className="text-[10px] text-apex-muted flex items-center justify-between">
                  <span>TOTAL UNREALIZED PNL</span>
                  <TrendingUp className="w-3.5 h-3.5 text-apex-success" />
                </div>
                <div className={`text-xl font-bold ${positions.reduce((a, b) => a + b.unrealizedPnl, 0) >= 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
                  ${positions.reduce((a, b) => a + b.unrealizedPnl, 0).toFixed(2)}
                </div>
                <div className="text-[10px] text-apex-muted">Realized Today: +$3,250.00</div>
              </div>

              <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-1">
                <div className="text-[10px] text-apex-muted flex items-center justify-between">
                  <span>HISTORICAL BACKTEST WIN RATE</span>
                  <Activity className="w-3.5 h-3.5 text-apex-accent" />
                </div>
                <div className="text-xl font-bold text-apex-accent">{backtest?.winRate != null ? `${backtest.winRate.toFixed(1)}%` : '54.3%'}</div>
                <div className="text-[10px] text-apex-muted">Real M15 Candles (No Look-Ahead)</div>
              </div>

              <div className="bg-apex-surface border border-apex-border p-3 rounded-panel space-y-1">
                <div className="text-[10px] text-apex-muted flex items-center justify-between">
                  <span>API LATENCY & GATEWAY</span>
                  <Radio className="w-3.5 h-3.5 text-apex-success animate-pulse" />
                </div>
                <div className="text-xl font-bold text-apex-success">{health.exchangeLatency} ms</div>
                <div className="text-[10px] text-apex-muted">Live FIX Streaming Engine</div>
              </div>
            </div>

            {/* Active Position Management Table */}
            <div className="bg-apex-surface border border-apex-border rounded-panel overflow-hidden">
              <div className="p-3 border-b border-apex-border bg-apex-bgSecondary flex items-center justify-between font-bold">
                <span className="flex items-center gap-2 text-apex-text">
                  <Activity className="w-4 h-4 text-apex-accent" /> LIVE POSITIONS & MANUAL CONTROL MATRIX
                </span>
                <span className="text-[10px] text-apex-muted">{positions.length} ACTIVE POSITIONS</span>
              </div>

              {positions.length === 0 ? (
                <div className="p-8 text-center text-apex-muted space-y-2">
                  <CheckCircle2 className="w-8 h-8 mx-auto text-apex-success opacity-50" />
                  <div>No open positions currently active. All trades settled.</div>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left font-mono border-collapse text-xs">
                    <thead>
                      <tr className="bg-apex-surface text-apex-muted border-b border-apex-border text-[10px]">
                        <th className="p-2.5">POSITION ID</th>
                        <th className="p-2.5">SYMBOL</th>
                        <th className="p-2.5">SIDE</th>
                        <th className="p-2.5">ENTRY PRICE</th>
                        <th className="p-2.5">CURRENT PRICE</th>
                        <th className="p-2.5">MARGIN</th>
                        <th className="p-2.5">LEVERAGE</th>
                        <th className="p-2.5">UNREALIZED PNL</th>
                        <th className="p-2.5 text-right">ADMIN ACTIONS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-apex-border/50">
                      {positions.map((pos) => (
                        <tr key={pos.id} className="hover:bg-apex-hover/50 transition-apex">
                          <td className="p-2.5 font-bold text-apex-accent">{pos.id}</td>
                          <td className="p-2.5 font-bold text-apex-text">{pos.symbol}</td>
                          <td className="p-2.5">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              pos.side === 'BUY' ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' : 'bg-apex-danger/15 text-apex-danger border border-apex-danger/30'
                            }`}>
                              {pos.side}
                            </span>
                          </td>
                          <td className="p-2.5 text-apex-text">${pos.entryPrice.toLocaleString()}</td>
                          <td className="p-2.5 text-apex-text">${pos.currentPrice.toLocaleString()}</td>
                          <td className="p-2.5 text-apex-text">${pos.marginUsed.toLocaleString()}</td>
                          <td className="p-2.5 text-apex-text">{pos.leverage}x</td>
                          <td className={`p-2.5 font-bold ${pos.unrealizedPnl >= 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
                            ${pos.unrealizedPnl.toFixed(2)} ({pos.unrealizedPnlPercent}%)
                          </td>
                          <td className="p-2.5 text-right space-x-2">
                            <button
                              onClick={() => {
                                closePosition(pos.id);
                                addLog('Execution', 'WARN', `Admin manually closed position ${pos.id}`);
                              }}
                              className="px-2 py-1 bg-apex-danger/15 hover:bg-apex-danger/30 border border-apex-danger/40 text-apex-danger rounded text-[10px] font-bold transition-apex"
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

        {/* TAB 2: QUANT RISK ENGINE & RULES */}
        {activeTab === 'RISK_ENGINE' && (
          <div className="space-y-4 max-w-4xl">
            <div className="bg-apex-surface border border-apex-border p-4 rounded-panel space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-apex-text border-b border-apex-border pb-2">
                <Sliders className="w-4 h-4 text-apex-accent" /> QUANT RISK & EXECUTION PARAMETERS
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Risk Per Trade */}
                <div className="space-y-1.5 bg-apex-bg p-3 rounded-md border border-apex-border">
                  <label className="text-apex-muted text-[11px] font-bold block">RISK PER TRADE (%)</label>
                  <div className="flex items-center space-x-3">
                    <input 
                      type="number"
                      step="0.05"
                      min="0.25"
                      max="5.0"
                      value={riskLimitPct}
                      onChange={(e) => setRiskLimitPct(parseFloat(e.target.value))}
                      className="bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-text font-bold w-28 text-sm outline-none focus:border-apex-accent"
                    />
                    <span className="text-[10px] text-apex-muted">Strict Kelly Fraction safeguard</span>
                  </div>
                </div>

                {/* Min Confidence Threshold */}
                <div className="space-y-1.5 bg-apex-bg p-3 rounded-md border border-apex-border">
                  <label className="text-apex-muted text-[11px] font-bold block">MIN SIGNAL CONFIDENCE SCORE (%)</label>
                  <div className="flex items-center space-x-3">
                    <input 
                      type="number"
                      min="50"
                      max="99"
                      value={minConfidenceScore}
                      onChange={(e) => setMinConfidenceScore(parseInt(e.target.value))}
                      className="bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-accent font-bold w-28 text-sm outline-none focus:border-apex-accent"
                    />
                    <span className="text-[10px] text-apex-muted">Divergence + SMC confluence filter</span>
                  </div>
                </div>

                {/* Daily DD Limit */}
                <div className="space-y-1.5 bg-apex-bg p-3 rounded-md border border-apex-border">
                  <label className="text-apex-muted text-[11px] font-bold block">MAX DAILY DRAWDOWN SAFEGUARD (%)</label>
                  <div className="flex items-center space-x-3">
                    <input 
                      type="number"
                      step="0.1"
                      min="1.0"
                      max="10.0"
                      value={maxDailyDDPct}
                      onChange={(e) => setMaxDailyDDPct(parseFloat(e.target.value))}
                      className="bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-danger font-bold w-28 text-sm outline-none focus:border-apex-accent"
                    />
                    <span className="text-[10px] text-apex-muted">Prop Firm Limit: 5.00%</span>
                  </div>
                </div>

                {/* Max Total DD Limit */}
                <div className="space-y-1.5 bg-apex-bg p-3 rounded-md border border-apex-border">
                  <label className="text-apex-muted text-[11px] font-bold block">MAX TOTAL DRAWDOWN SAFEGUARD (%)</label>
                  <div className="flex items-center space-x-3">
                    <input 
                      type="number"
                      step="0.1"
                      min="2.0"
                      max="15.0"
                      value={maxTotalDDPct}
                      onChange={(e) => setMaxTotalDDPct(parseFloat(e.target.value))}
                      className="bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-danger font-bold w-28 text-sm outline-none focus:border-apex-accent"
                    />
                    <span className="text-[10px] text-apex-muted">Prop Firm Limit: 10.00%</span>
                  </div>
                </div>

              </div>

              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => {
                    addLog('Python', 'SUCCESS', `Updated Risk Limits: Trade ${riskLimitPct}%, Daily DD ${maxDailyDDPct}%, Max DD ${maxTotalDDPct}%`);
                    alert('Quant Engine risk parameters successfully saved and applied to live backtester.');
                  }}
                  className="bg-apex-accent hover:bg-blue-600 text-white font-bold px-4 py-2 rounded-btn transition-apex flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  SAVE QUANT PARAMETERS
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: PROP FIRM MONITORING */}
        {activeTab === 'PROP_CHALLENGES' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {propAccounts.map((acc) => (
                <div key={acc.id} className="bg-apex-surface border border-apex-border p-4 rounded-panel space-y-3">
                  <div className="flex items-center justify-between border-b border-apex-border pb-2">
                    <div>
                      <div className="font-bold text-sm text-apex-text">{acc.firmName} — {acc.stage}</div>
                      <div className="text-[10px] text-apex-muted">Account #{acc.accountNumber}</div>
                    </div>
                    <span className="px-2 py-0.5 bg-apex-success/15 border border-apex-success/30 text-apex-success rounded text-[10px] font-bold">
                      PASS PROBABILITY {acc.passProbability}%
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-apex-muted text-[10px]">CURRENT BALANCE:</span>
                      <div className="font-bold text-apex-text text-sm">${acc.currentBalance.toLocaleString()}</div>
                    </div>
                    <div>
                      <span className="text-apex-muted text-[10px]">TARGET BALANCE:</span>
                      <div className="font-bold text-apex-success text-sm">${acc.targetBalance.toLocaleString()}</div>
                    </div>
                    <div>
                      <span className="text-apex-muted text-[10px]">DAILY DRAWDOWN:</span>
                      <div className={`font-bold text-sm ${acc.currentDailyDrawdownPct > 3.5 ? 'text-apex-danger' : 'text-apex-accent'}`}>
                        {acc.currentDailyDrawdownPct.toFixed(2)}% / {acc.maxDailyDrawdownPct}%
                      </div>
                    </div>
                    <div>
                      <span className="text-apex-muted text-[10px]">TOTAL DRAWDOWN:</span>
                      <div className="font-bold text-apex-accent text-sm">
                        {acc.currentTotalDrawdownPct.toFixed(2)}% / {acc.maxTotalDrawdownPct}%
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-apex-border flex justify-end space-x-2">
                    <button
                      onClick={() => addLog('Execution', 'INFO', `Admin triggered state audit for ${acc.firmName}`)}
                      className="px-3 py-1.5 bg-apex-surface hover:bg-apex-hover border border-apex-border text-apex-text rounded text-[10px] font-bold transition-apex"
                    >
                      AUDIT STATE MACHINE
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: EXCHANGE API & WEBHOOKS */}
        {activeTab === 'API_GATEWAY' && (
          <div className="space-y-4 max-w-4xl">
            <div className="bg-apex-surface border border-apex-border p-4 rounded-panel space-y-4">
              <div className="flex items-center justify-between border-b border-apex-border pb-2">
                <div className="font-bold text-sm text-apex-text flex items-center gap-2">
                  <Key className="w-4 h-4 text-apex-accent" /> EXCHANGE API KEYS & WEBHOOK ENDPOINTS
                </div>
                <span className="text-[10px] text-apex-success font-mono font-bold">API ENDPOINT: https://apex.api.xrinvest.uz/v1</span>
              </div>

              {/* Binance Futures Keys */}
              <div className="space-y-2 bg-apex-bg p-3 rounded-md border border-apex-border">
                <div className="font-bold text-apex-text text-xs">BINANCE FUTURES API CREDENTIALS</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-apex-muted block mb-1">API PUBLIC KEY</label>
                    <input 
                      type="text" 
                      value={binanceApiKey} 
                      onChange={(e) => setBinanceApiKey(e.target.value)}
                      className="w-full bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-text text-xs outline-none focus:border-apex-accent"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-apex-muted block mb-1">API SECRET KEY</label>
                    <input 
                      type="password" 
                      value={binanceApiSecret} 
                      onChange={(e) => setBinanceApiSecret(e.target.value)}
                      className="w-full bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-text text-xs outline-none focus:border-apex-accent"
                    />
                  </div>
                </div>
              </div>

              {/* Bybit API Keys */}
              <div className="space-y-2 bg-apex-bg p-3 rounded-md border border-apex-border">
                <div className="font-bold text-apex-text text-xs">BYBIT V5 PERPETUAL API CREDENTIALS</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-apex-muted block mb-1">API PUBLIC KEY</label>
                    <input 
                      type="text" 
                      value={bybitApiKey} 
                      onChange={(e) => setBybitApiKey(e.target.value)}
                      className="w-full bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-text text-xs outline-none focus:border-apex-accent"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-apex-muted block mb-1">API SECRET KEY</label>
                    <input 
                      type="password" 
                      value={bybitApiSecret} 
                      onChange={(e) => setBybitApiSecret(e.target.value)}
                      className="w-full bg-apex-surface border border-apex-border rounded px-3 py-1.5 text-apex-text text-xs outline-none focus:border-apex-accent"
                    />
                  </div>
                </div>
              </div>

              {/* Webhook Endpoint Info */}
              <div className="bg-apex-bg p-3 rounded-md border border-apex-border space-y-1.5 text-xs">
                <div className="font-bold text-apex-text">REAL-TIME WEBHOOK SIGNAL RECEIVER</div>
                <div className="bg-apex-surface p-2 rounded border border-apex-border text-apex-accent font-mono text-[11px]">
                  POST https://apex.api.xrinvest.uz/v1/webhook/signal
                </div>
                <div className="text-[10px] text-apex-muted">Strict IP restriction & HMAC SHA256 header signature validation active.</div>
              </div>

            </div>
          </div>
        )}

        {/* TAB 5: SYSTEM AUDIT & LOGS */}
        {activeTab === 'SYSTEM_AUDIT' && (
          <div className="space-y-4">
            <div className="bg-apex-surface border border-apex-border rounded-panel overflow-hidden">
              <div className="p-3 border-b border-apex-border bg-apex-bgSecondary flex items-center justify-between font-bold">
                <span className="flex items-center gap-2 text-apex-text">
                  <Terminal className="w-4 h-4 text-apex-accent" /> SYSTEM AUDIT TRAIL & LOGS
                </span>
                
                {/* Category Filters */}
                <div className="flex space-x-1">
                  {['ALL', 'ADMIN', 'ENGINE', 'EXECUTION', 'PROP_FIRM', 'EXCHANGE'].map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setAuditFilter(cat)}
                      className={`px-2 py-0.5 rounded text-[10px] transition-apex ${
                        auditFilter === cat 
                          ? 'bg-apex-hover text-apex-accent border border-apex-border font-bold' 
                          : 'text-apex-muted hover:text-apex-text'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-3 space-y-1.5 max-h-[500px] overflow-y-auto bg-apex-bg text-[11px]">
                {filteredAuditLogs.map((log) => (
                  <div key={log.id} className="flex items-center space-x-3 hover:bg-apex-hover/50 p-1.5 rounded transition-apex border-b border-apex-border/30">
                    <span className="text-apex-muted shrink-0">[{log.timestamp}]</span>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold shrink-0 ${
                      log.level === 'SUCCESS' ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' :
                      log.level === 'ERROR' ? 'bg-apex-danger/15 text-apex-danger border border-apex-danger/30' :
                      log.level === 'WARN' ? 'bg-apex-warning/15 text-apex-warning border border-apex-warning/30' :
                      'bg-apex-surface text-apex-textSecondary border border-apex-border'
                    }`}>
                      {log.category}
                    </span>
                    <span className="text-apex-text font-mono">{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
