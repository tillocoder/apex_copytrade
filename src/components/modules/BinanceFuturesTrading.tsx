import React, { useState, useEffect, useRef } from 'react';
import { 
  Flame, 
  TrendingUp, 
  TrendingDown, 
  ShieldAlert, 
  AlertTriangle, 
  Play, 
  Pause, 
  RotateCcw, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Activity, 
  DollarSign, 
  Zap, 
  ShieldCheck, 
  Sliders, 
  BarChart3, 
  Layers, 
  Wifi, 
  WifiOff, 
  Lock, 
  Key, 
  ExternalLink,
  ChevronRight,
  Info
} from 'lucide-react';

interface SignalStep {
  pass: boolean;
  desc: string;
}

interface SignalMatrix {
  h1_trend?: SignalStep;
  m15_structure?: SignalStep;
  m5_momentum?: SignalStep;
  m1_sweep?: SignalStep;
  m1_bos?: SignalStep;
  volume?: SignalStep;
  spread?: SignalStep;
  risk?: SignalStep;
}

interface ActiveSignal {
  final_signal?: string;
  entry_price?: number;
  sl?: number;
  tp?: number;
  sl_distance?: number;
  risk_reward?: number;
  reason?: string;
  matrix?: SignalMatrix;
}

interface ActivePosition {
  id: string;
  symbol: string;
  displaySymbol: string;
  side: 'LONG' | 'SHORT';
  qty: number;
  entryPrice: number;
  markPrice: number;
  liquidationPrice: number;
  margin: number;
  leverage: number;
  sl: number;
  tp: number;
  unrealizedPnl: number;
  roi: number;
  openedAt: string;
}

interface TradeHistoryItem {
  id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry_price: number;
  exit_price?: number;
  qty: number;
  margin: number;
  leverage: number;
  sl: number;
  tp: number;
  pnl: number;
  roi_pct: number;
  fee: number;
  status: string;
  close_reason?: string;
  opened_at: string;
  closed_at?: string;
}

interface DashboardState {
  bot: {
    connected: boolean;
    running: boolean;
    mode: 'PAPER' | 'LIVE' | 'BACKTEST';
    liveEnabled: boolean;
    symbol: string;
    timeframe: string;
    leverage: number;
    marginUsd: number;
    approxNotional: number;
    maxOpenPositions: number;
    sessionTargetUsd: number;
    status: string;
  };
  account: {
    balance: number;
    availableBalance: number;
    usedMargin: number;
    unrealizedPnl: number;
    sessionPnl: number;
    targetProgressPct: number;
    targetReached: boolean;
  };
  position: ActivePosition | null;
  market: {
    symbol: string;
    displaySymbol: string;
    price: number;
    bid: number;
    ask: number;
    spread: number;
    spreadPct: number;
    spreadAcceptable: boolean;
    markPrice: number;
    fundingRate: number;
    atrM1: number;
    atrM5: number;
    volume1h: number;
    session: string;
    sessionAllowed: boolean;
    sessionTashkent: string;
    volatility: string;
    isStale: boolean;
  };
  signal: ActiveSignal;
  risk: {
    sessionProfitTarget: number;
    sessionPnl: number;
    targetProgressPct: number;
    targetReached: boolean;
    tradesCount: number;
    maxTrades: number;
    consecutiveLosses: number;
    cooldownSecondsRemaining: number;
    emergencyStop: boolean;
    maxSessionLoss: number;
    maxDailyLoss: number;
  };
  trades: TradeHistoryItem[];
}

export const BinanceFuturesTrading: React.FC = () => {
  const [state, setState] = useState<DashboardState | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'live' | 'backtest' | 'forensics'>('live');
  
  // Modals & Action States
  const [showLiveModal, setShowLiveModal] = useState<boolean>(false);
  const [showEmergencyModal, setShowEmergencyModal] = useState<boolean>(false);
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [apiSecretInput, setApiSecretInput] = useState<string>('');
  const [confirmLiveCheck, setConfirmLiveCheck] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Backtest state
  const [backtestCandles, setBacktestCandles] = useState<number>(3000);
  const [backtestRunning, setBacktestRunning] = useState<boolean>(false);
  const [backtestResult, setBacktestResult] = useState<any | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // 1. Initial State Poll + WebSocket Connection
  useEffect(() => {
    let isMounted = true;

    const fetchInitial = async () => {
      try {
        const res = await fetch('/api/v1/futures/state');
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setState(data);
        }
      } catch (err) {
        console.error('Failed to fetch initial futures state:', err);
      }
    };
    fetchInitial();

    // Setup WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/futures/ws`;

    const connectWs = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isMounted) setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data && data.type === 'FUTURES_DASHBOARD_STATE') {
              if (isMounted) setState(data);
            }
          } catch (e) {
            console.error('WS parse error:', e);
          }
        };

        ws.onerror = () => {
          if (isMounted) setWsConnected(false);
        };

        ws.onclose = () => {
          if (isMounted) {
            setWsConnected(false);
            // Reconnect after 2 seconds
            setTimeout(connectWs, 2000);
          }
        };
      } catch (e) {
        console.error('WS Connection error:', e);
        setTimeout(connectWs, 2000);
      }
    };

    connectWs();

    // Fallback polling every 3 seconds
    const interval = setInterval(fetchInitial, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // 2. Bot Control Actions
  const handleControlAction = async (action: 'run' | 'pause' | 'reset_session' | 'emergency_stop') => {
    setActionLoading(true);
    setStatusMessage(null);
    try {
      const res = await fetch('/api/v1/futures/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMessage(data.message || `Action ${action.toUpperCase()} completed successfully.`);
      } else {
        setStatusMessage(`Error: ${data.detail || 'Action failed'}`);
      }
    } catch (e: any) {
      setStatusMessage(`Error: ${e.message}`);
    } finally {
      setActionLoading(false);
      setShowEmergencyModal(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  // 3. Switch Mode (Paper / Live)
  const handleSwitchMode = async (targetMode: 'PAPER' | 'LIVE') => {
    if (targetMode === 'LIVE' && !confirmLiveCheck) {
      alert('Please check the confirmation box to acknowledge real financial risk.');
      return;
    }
    setActionLoading(true);
    try {
      const res = await fetch('/api/v1/futures/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: targetMode,
          confirm_live: confirmLiveCheck,
          api_key: apiKeyInput.trim() || undefined,
          api_secret: apiSecretInput.trim() || undefined
        })
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMessage(data.message || `Switched to ${targetMode} mode.`);
        setShowLiveModal(false);
      } else {
        alert(data.detail || 'Failed to switch mode.');
      }
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // 4. Run Backtest
  const handleRunBacktest = async () => {
    setBacktestRunning(true);
    try {
      const res = await fetch('/api/v1/futures/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candles: backtestCandles,
          margin: 0.50,
          leverage: 100
        })
      });
      const data = await res.json();
      setBacktestResult(data);
    } catch (e: any) {
      alert(`Backtest error: ${e.message}`);
    } finally {
      setBacktestRunning(false);
    }
  };

  const bot = state?.bot;
  const acc = state?.account;
  const mkt = state?.market;
  const pos = state?.position;
  const sig = state?.signal;
  const risk = state?.risk;
  const trades = state?.trades || [];

  return (
    <div className="flex-1 flex flex-col h-full bg-[#070B14] text-[#F3F4F6] overflow-y-auto no-scrollbar font-sans select-none p-4 md:p-6 space-y-5">
      
      {/* 1. TOP HEADER BAR */}
      <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center space-x-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 text-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/20 shrink-0">
            <Flame className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg md:text-xl font-black tracking-tight text-white font-mono">
                ETHUSDT.P
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/35">
                BINANCE USDⓈ-M
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/15 text-purple-300 border border-purple-500/35">
                M1 100X
              </span>
            </div>
            <p className="text-xs text-[#9CA3AF] font-sans">
              High-Frequency M1 Institutional Liquidity Sweep & Micro BOS Scalping Engine
            </p>
          </div>
        </div>

        {/* Global Controls & Status */}
        <div className="flex items-center flex-wrap gap-2.5">
          {/* Status Badge */}
          <div className="flex items-center space-x-2 px-3 py-1.5 bg-[#0C152B] border border-[#1C2E52] rounded-lg text-xs font-mono">
            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            <span className="text-[#9CA3AF]">FEED:</span>
            <span className={wsConnected ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
              {wsConnected ? 'LIVE STREAM' : 'RECONNECTING'}
            </span>
          </div>

          {/* Mode Pill */}
          <button
            onClick={() => {
              if (bot?.mode === 'PAPER') {
                setShowLiveModal(true);
              } else {
                handleSwitchMode('PAPER');
              }
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition-apex flex items-center gap-1.5 cursor-pointer ${
              bot?.mode === 'LIVE'
                ? 'bg-rose-500/15 border-rose-500/40 text-rose-400 hover:bg-rose-500/25'
                : 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/25'
            }`}
          >
            {bot?.mode === 'LIVE' ? <Lock className="w-3.5 h-3.5" /> : <Layers className="w-3.5 h-3.5" />}
            <span>MODE: {bot?.mode || 'PAPER'}</span>
          </button>

          {/* Run/Pause Button */}
          <button
            onClick={() => handleControlAction(bot?.running ? 'pause' : 'run')}
            disabled={actionLoading}
            className={`px-3 py-1.5 rounded-lg text-xs font-sans font-bold border transition-apex flex items-center gap-1.5 cursor-pointer ${
              bot?.running
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-300 hover:bg-amber-500/25'
                : 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/25'
            }`}
          >
            {bot?.running ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{bot?.running ? 'PAUSE BOT' : 'RESUME BOT'}</span>
          </button>

          {/* Reset $2 Session Target */}
          <button
            onClick={() => handleControlAction('reset_session')}
            disabled={actionLoading}
            className="px-3 py-1.5 rounded-lg text-xs font-sans font-semibold bg-[#0C152B] border border-[#1C2E52] text-[#9CA3AF] hover:text-white hover:bg-[#0E1B38] transition-apex flex items-center gap-1.5 cursor-pointer"
            title="Reset Session PnL and $2 Target"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESET $2</span>
          </button>

          {/* Emergency Stop Button */}
          <button
            onClick={() => setShowEmergencyModal(true)}
            className="px-3 py-1.5 rounded-lg text-xs font-sans font-bold bg-rose-600/25 hover:bg-rose-600/40 border border-rose-500 text-rose-400 hover:text-rose-300 transition-apex flex items-center gap-1.5 cursor-pointer shadow-lg shadow-rose-900/30"
          >
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <span>EMERGENCY STOP</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 bg-blue-500/15 border border-blue-500/30 text-cyan-300 rounded-lg text-xs font-mono flex items-center gap-2 animate-in fade-in">
          <Info className="w-4 h-4 shrink-0 text-cyan-400" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* 2. TOP METRICS CARDS (ACCOUNT, $2 TARGET, POSITION, MARKET) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Account Capital & Margin */}
        <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl p-4 space-y-2 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between text-[11px] text-[#9CA3AF] font-sans font-semibold">
            <span>FUTURES BALANCE</span>
            <span className="font-mono text-cyan-400">100X LEVERAGE</span>
          </div>
          <div className="text-2xl font-black text-white font-mono tracking-tight">
            ${acc ? acc.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '100.00'}
          </div>
          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[#1C2E52]/60 text-[11px] font-mono">
            <div>
              <span className="text-[#6B7280] block text-[10px]">Available:</span>
              <span className="text-emerald-400 font-bold">${acc?.availableBalance?.toFixed(2) || '100.00'}</span>
            </div>
            <div>
              <span className="text-[#6B7280] block text-[10px]">Used Margin:</span>
              <span className="text-white font-bold">${acc?.usedMargin?.toFixed(2) || '0.00'}</span>
            </div>
          </div>
        </div>

        {/* Card 2: $2 Session Target Progress */}
        <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl p-4 space-y-2 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between text-[11px] text-[#9CA3AF] font-sans font-semibold">
            <span>SESSION PnL TARGET ($2.00)</span>
            <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
              risk?.targetReached ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' : 'bg-cyan-500/10 text-cyan-300'
            }`}>
              {risk?.targetReached ? 'TARGET ATTAINED' : 'IN PROGRESS'}
            </span>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className={`text-2xl font-black font-mono tracking-tight ${
              (acc?.sessionPnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}>
              {(acc?.sessionPnl || 0) >= 0 ? '+' : ''}${acc?.sessionPnl?.toFixed(2) || '0.00'}
            </span>
            <span className="text-xs text-[#9CA3AF] font-mono">/ $2.00 Target</span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-[#0C152B] rounded-full h-2 border border-[#1C2E52] overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${
                risk?.targetReached ? 'bg-gradient-to-r from-purple-500 to-emerald-400' : 'bg-gradient-to-r from-cyan-500 to-blue-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, acc?.targetProgressPct || 0))}%` }}
            />
          </div>
          <div className="flex justify-between items-center text-[10px] text-[#6B7280] font-mono">
            <span>Progress: {acc?.targetProgressPct?.toFixed(1) || 0}%</span>
            <span>Trades: {risk?.tradesCount || 0}/{risk?.maxTrades || 25}</span>
          </div>
        </div>

        {/* Card 3: Active Position Status */}
        <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl p-4 space-y-2 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between text-[11px] text-[#9CA3AF] font-sans font-semibold">
            <span>ACTIVE POSITION</span>
            <span className={`px-1.5 py-0.2 rounded text-[9.5px] font-bold ${
              pos ? (pos.side === 'LONG' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-400 border border-rose-500/40') : 'bg-gray-800 text-gray-400'
            }`}>
              {pos ? pos.side : 'FLAT'}
            </span>
          </div>
          {pos ? (
            <div>
              <div className="flex items-baseline space-x-2">
                <span className={`text-xl font-bold font-mono ${pos.unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {pos.unrealizedPnl >= 0 ? '+' : ''}${pos.unrealizedPnl.toFixed(2)}
                </span>
                <span className={`text-xs font-mono font-semibold ${pos.roi >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  ({pos.roi >= 0 ? '+' : ''}{pos.roi.toFixed(1)}%)
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-2 text-[10.5px] font-mono text-[#9CA3AF] pt-1">
                <div>Entry: <span className="text-white">${pos.entryPrice.toFixed(2)}</span></div>
                <div>Mark: <span className="text-cyan-400">${pos.markPrice.toFixed(2)}</span></div>
                <div>SL: <span className="text-rose-400">${pos.sl.toFixed(2)}</span></div>
                <div>TP: <span className="text-emerald-400">${pos.tp.toFixed(2)}</span></div>
              </div>
            </div>
          ) : (
            <div className="py-2 text-center text-[#6B7280] font-sans text-xs">
              <span className="block font-bold text-[#9CA3AF]">NO OPEN POSITION</span>
              <span className="text-[10px]">Scanning M1 order flow for setup...</span>
            </div>
          )}
        </div>

        {/* Card 4: Market ETH Price & Session */}
        <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl p-4 space-y-2 relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between text-[11px] text-[#9CA3AF] font-sans font-semibold">
            <span>ETH SPOT / MARK</span>
            <span className="px-1.5 py-0.2 rounded text-[9.5px] font-mono font-bold bg-blue-500/15 text-blue-300 border border-blue-500/30">
              {mkt?.session || 'SESSION'}
            </span>
          </div>
          <div className="text-2xl font-black text-cyan-400 font-mono tracking-tight">
            ${mkt ? mkt.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '2,684.00'}
          </div>
          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[#1C2E52]/60 text-[10.5px] font-mono">
            <div>
              <span className="text-[#6B7280] block text-[10px]">Spread:</span>
              <span className={mkt?.spreadAcceptable ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                ${mkt?.spread?.toFixed(2) || '0.02'} ({mkt?.spreadPct?.toFixed(3) || '0.001'}%)
              </span>
            </div>
            <div>
              <span className="text-[#6B7280] block text-[10px]">Session (Tashkent):</span>
              <span className="text-white font-bold">{mkt?.sessionTashkent || 'Tashkent UTC+5'}</span>
            </div>
          </div>
        </div>

      </div>

      {/* 3. TABS NAVIGATION */}
      <div className="flex items-center space-x-2 border-b border-[#1C2E52] pb-2">
        <button
          onClick={() => setActiveTab('live')}
          className={`px-4 py-2 rounded-lg text-xs font-sans font-bold transition-apex flex items-center space-x-2 cursor-pointer ${
            activeTab === 'live' 
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm' 
              : 'text-[#9CA3AF] hover:text-white hover:bg-[#0C152B]'
          }`}
        >
          <Activity className="w-4 h-4 text-cyan-400" />
          <span>Realtime Terminal & Forensics</span>
        </button>

        <button
          onClick={() => setActiveTab('backtest')}
          className={`px-4 py-2 rounded-lg text-xs font-sans font-bold transition-apex flex items-center space-x-2 cursor-pointer ${
            activeTab === 'backtest' 
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm' 
              : 'text-[#9CA3AF] hover:text-white hover:bg-[#0C152B]'
          }`}
        >
          <BarChart3 className="w-4 h-4 text-purple-400" />
          <span>Binance Historical Backtest Lab</span>
        </button>
      </div>

      {/* 4. MAIN CONTENT AREA */}
      {activeTab === 'live' ? (
        <div className="space-y-5">
          
          {/* Dual Panel: Signal Forensics Matrix + Execution Specs */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            
            {/* Left 2 Cols: Signal Debug Matrix */}
            <div className="lg:col-span-2 bg-[#0A1224] border border-[#1C2E52] rounded-xl p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-[#1C2E52] pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                  <h3 className="text-sm font-bold text-white font-mono tracking-wide">
                    SIGNAL FORENSICS DEBUG MATRIX
                  </h3>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] text-[#9CA3AF] font-sans">FINAL SIGNAL:</span>
                  <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-black tracking-wider ${
                    sig?.final_signal === 'LONG'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 animate-pulse'
                      : sig?.final_signal === 'SHORT'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/50 animate-pulse'
                        : 'bg-[#0C152B] text-[#9CA3AF] border border-[#1C2E52]'
                  }`}>
                    {sig?.final_signal || 'WAITING'}
                  </span>
                </div>
              </div>

              {/* 8 Step Verification Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                {/* 1. H1 Trend */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">H1 HIGHER TIMEFRAME TREND</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.h1_trend?.desc || 'Evaluating EMA50/200 trend...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.h1_trend?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.h1_trend?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>

                {/* 2. M15 Structure */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">M15 MARKET STRUCTURE</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.m15_structure?.desc || 'Verifying swing structure...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.m15_structure?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.m15_structure?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>

                {/* 3. M5 Momentum */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">M5 MOMENTUM & PULLBACK</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.m5_momentum?.desc || 'Monitoring EMA20 pullback...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.m5_momentum?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.m5_momentum?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>

                {/* 4. M1 Liquidity Sweep */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">M1 LIQUIDITY SWEEP</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.m1_sweep?.desc || 'Detecting swing sweep...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.m1_sweep?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.m1_sweep?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>

                {/* 5. M1 BOS */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">M1 BREAK OF STRUCTURE (BOS)</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.m1_bos?.desc || 'Awaiting micro break...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.m1_bos?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.m1_bos?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>

                {/* 6. Volume Confirmation */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">VOLUME IMPULSE (20-SMA)</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.volume?.desc || 'Checking volume multiplier...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.volume?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.volume?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>

                {/* 7. Spread Filter */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">SPREAD FILTER (≤ 0.15 USDT)</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.spread?.desc || 'Spread evaluation...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.spread?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.spread?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>

                {/* 8. Risk Management Filter */}
                <div className="p-3 bg-[#0C152B] border border-[#1C2E52] rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[#9CA3AF] text-[10px] font-sans font-semibold">RISK & SESSION GUARD</div>
                    <div className="text-white text-[11px]">{sig?.matrix?.risk?.desc || 'Checking cooldown and limits...'}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig?.matrix?.risk?.pass ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {sig?.matrix?.risk?.pass ? 'PASS' : 'FAIL'}
                  </span>
                </div>
              </div>

              {/* Status explanation */}
              <div className="p-3 bg-[#0C152B]/60 rounded-lg border border-[#1C2E52] text-xs font-sans text-[#9CA3AF] flex items-center justify-between">
                <div>
                  <span className="font-semibold text-white">Current Engine State: </span>
                  <span>{sig?.reason || 'Monitoring order book and candle structure.'}</span>
                </div>
                {risk?.cooldownSecondsRemaining ? (
                  <span className="text-amber-400 font-mono text-[11px] flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Cooldown: {risk.cooldownSecondsRemaining}s
                  </span>
                ) : null}
              </div>
            </div>

            {/* Right 1 Col: Execution Specs & Risk Rules */}
            <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl p-5 space-y-4 shadow-xl">
              <h3 className="text-sm font-bold text-white font-mono tracking-wide border-b border-[#1C2E52] pb-3 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                <span>EXECUTION & RISK RULES</span>
              </h3>

              <div className="space-y-2.5 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Target Asset:</span>
                  <span className="font-bold text-white">ETHUSDT (Binance USDⓈ-M)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Fixed Margin:</span>
                  <span className="font-bold text-cyan-400">$0.50 USDT</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Leverage:</span>
                  <span className="font-bold text-purple-400">100X (One-Way Mode)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Approx Notional:</span>
                  <span className="font-bold text-white">~$50.00 USDT</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Session Profit Target:</span>
                  <span className="font-bold text-emerald-400">$2.00 (Halt on Target)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Max Open Positions:</span>
                  <span className="font-bold text-white">1 Position</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Adaptive SL:</span>
                  <span className="font-bold text-rose-400">Structure + 1.0x ATR</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Take-Profit:</span>
                  <span className="font-bold text-emerald-400">2.0R (Risk-Based)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2E52]/40">
                  <span className="text-[#9CA3AF]">Emergency Watchdog:</span>
                  <span className="font-bold text-emerald-400">Active (2.0s timeout)</span>
                </div>
              </div>

              <div className="p-3 bg-cyan-500/10 border border-cyan-500/25 rounded-lg text-[11px] text-[#9CA3AF] font-sans">
                💡 <span className="font-semibold text-cyan-300">Target Rule:</span> $2 session target represents 400% ROI on the $0.50 base margin. When reached, bot halts further risk automatically.
              </div>
            </div>

          </div>

          {/* 5. REALTIME ORDERS & TRADES TABLE */}
          <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl shadow-xl overflow-hidden">
            <div className="h-12 bg-[#0C152B] border-b border-[#1C2E52] px-5 flex items-center justify-between">
              <div className="flex items-center space-x-2 font-bold text-xs text-white font-mono uppercase tracking-wider">
                <Layers className="w-4 h-4 text-cyan-400" />
                <span>REALTIME EXECUTION & TRADES FORENSICS</span>
              </div>
              <span className="text-[11px] text-[#6B7280] font-mono">
                {trades.length} Trades Recorded
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="bg-[#0A1224] border-b border-[#1C2E52] text-[10px] text-[#9CA3AF] uppercase font-semibold font-sans">
                    <th className="p-3">Time</th>
                    <th className="p-3">Side</th>
                    <th className="p-3 text-right">Entry Price</th>
                    <th className="p-3 text-right">Exit Price</th>
                    <th className="p-3 text-right">Quantity</th>
                    <th className="p-3 text-right">SL / TP</th>
                    <th className="p-3 text-center">Status / Reason</th>
                    <th className="p-3 text-right">Fee</th>
                    <th className="p-3 text-right">Net PnL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A222E]">
                  {trades.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="p-8 text-center text-[#6B7280] font-sans">
                        No closed trades yet in this session. Live executions will appear here in real time.
                      </td>
                    </tr>
                  ) : (
                    trades.map((t, idx) => {
                      const isWin = (t.pnl || 0) > 0;
                      return (
                        <tr key={t.id || idx} className="hover:bg-[#0C152B]/70 transition-apex">
                          <td className="p-3 text-[#9CA3AF] text-[10.5px]">
                            {t.opened_at ? t.opened_at.split(' ')[1] : 'Just now'}
                          </td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              t.side === 'LONG' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'
                            }`}>
                              {t.side}
                            </span>
                          </td>
                          <td className="p-3 text-right text-white font-bold">
                            ${t.entry_price?.toFixed(2)}
                          </td>
                          <td className="p-3 text-right text-cyan-400 font-bold">
                            {t.exit_price ? `$${t.exit_price.toFixed(2)}` : 'Active'}
                          </td>
                          <td className="p-3 text-right text-[#9CA3AF]">
                            {t.qty} ETH
                          </td>
                          <td className="p-3 text-right text-[10px]">
                            <span className="text-rose-400">${t.sl?.toFixed(2)}</span> / <span className="text-emerald-400">${t.tp?.toFixed(2)}</span>
                          </td>
                          <td className="p-3 text-center">
                            <span className={`px-2 py-0.5 rounded text-[9.5px] font-bold ${
                              t.close_reason === 'TAKE_PROFIT_HIT' || isWin
                                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            }`}>
                              {t.close_reason || t.status}
                            </span>
                          </td>
                          <td className="p-3 text-right text-[#6B7280]">
                            ${t.fee?.toFixed(4) || '0.0000'}
                          </td>
                          <td className={`p-3 text-right font-bold text-xs ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isWin ? '+' : ''}${t.pnl?.toFixed(2)} ({isWin ? '+' : ''}{t.roi_pct?.toFixed(1)}%)
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      ) : (
        /* BACKTEST TAB */
        <div className="bg-[#0A1224] border border-[#1C2E52] rounded-xl p-6 space-y-6 shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1C2E52] pb-5">
            <div>
              <h2 className="text-lg font-bold text-white font-mono flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-purple-400" />
                <span>BINANCE FUTURES HISTORICAL M1 BACKTEST LAB</span>
              </h2>
              <p className="text-xs text-[#9CA3AF] font-sans">
                Rigorous In-Sample & Out-of-Sample Walk-Forward Simulation using Real Binance ETHUSDT M1 Klines.
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <select
                value={backtestCandles}
                onChange={(e) => setBacktestCandles(Number(e.target.value))}
                className="bg-[#0C152B] border border-[#1C2E52] text-white text-xs rounded-lg px-3 py-2 outline-none font-mono"
              >
                <option value={1500}>1,500 M1 Candles (~25 Hours)</option>
                <option value={3000}>3,000 M1 Candles (~2 Days)</option>
                <option value={5000}>5,000 M1 Candles (~3.5 Days)</option>
                <option value={10000}>10,000 M1 Candles (~7 Days)</option>
              </select>

              <button
                onClick={handleRunBacktest}
                disabled={backtestRunning}
                className="px-5 py-2 bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-400 hover:to-blue-500 text-white font-bold rounded-lg text-xs font-sans transition-apex flex items-center gap-2 cursor-pointer shadow-lg shadow-purple-900/30"
              >
                {backtestRunning ? (
                  <>
                    <RotateCcw className="w-4 h-4 animate-spin" />
                    <span>FETCHING & SIMULATING...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    <span>RUN REAL BACKTEST</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {backtestResult ? (
            <div className="space-y-6 animate-in fade-in">
              {/* Badge & Dates */}
              <div className="flex items-center justify-between p-3.5 bg-[#0C152B] border border-[#1C2E52] rounded-xl text-xs font-mono">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="font-bold text-white">{backtestResult.verificationBadge}</span>
                  <span className="text-[#6B7280]">|</span>
                  <span className="text-[#9CA3AF]">
                    Range: {backtestResult.dateRange?.start} → {backtestResult.dateRange?.end}
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold">
                  {backtestResult.totalCandlesTested} Candles Tested
                </span>
              </div>

              {/* Overall Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-[#0C152B] border border-[#1C2E52] rounded-xl text-center">
                  <div className="text-[10.5px] text-[#6B7280] uppercase font-sans">Total Trades</div>
                  <div className="text-xl font-black text-white font-mono pt-1">
                    {backtestResult.overall?.totalTrades}
                  </div>
                </div>

                <div className="p-4 bg-[#0C152B] border border-[#1C2E52] rounded-xl text-center">
                  <div className="text-[10.5px] text-[#6B7280] uppercase font-sans">Win Rate %</div>
                  <div className="text-xl font-black text-emerald-400 font-mono pt-1">
                    {backtestResult.overall?.winRatePct}%
                  </div>
                </div>

                <div className="p-4 bg-[#0C152B] border border-[#1C2E52] rounded-xl text-center">
                  <div className="text-[10.5px] text-[#6B7280] uppercase font-sans">Profit Factor</div>
                  <div className="text-xl font-black text-cyan-400 font-mono pt-1">
                    {backtestResult.overall?.profitFactor}x
                  </div>
                </div>

                <div className="p-4 bg-[#0C152B] border border-[#1C2E52] rounded-xl text-center">
                  <div className="text-[10.5px] text-[#6B7280] uppercase font-sans">Net PnL ($0.50 Margin)</div>
                  <div className={`text-xl font-black font-mono pt-1 ${
                    (backtestResult.overall?.netPnlUsd || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {(backtestResult.overall?.netPnlUsd || 0) >= 0 ? '+' : ''}${backtestResult.overall?.netPnlUsd?.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* In-Sample vs Out-of-Sample Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="p-4 bg-[#0C152B] border border-[#1C2E52] rounded-xl space-y-3 font-mono text-xs">
                  <div className="font-bold text-cyan-300 font-sans border-b border-[#1C2E52] pb-2">
                    In-Sample (Train Dataset)
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Trades:</span> <span className="text-white">{backtestResult.inSample?.total_trades}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Win Rate:</span> <span className="text-emerald-400">{backtestResult.inSample?.win_rate_pct}%</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Profit Factor:</span> <span className="text-white">{backtestResult.inSample?.profit_factor}x</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Net PnL:</span> <span className={backtestResult.inSample?.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>${backtestResult.inSample?.net_pnl}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Max Drawdown:</span> <span className="text-rose-400">${backtestResult.inSample?.max_drawdown_usd}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Losing Streak:</span> <span className="text-white">{backtestResult.inSample?.max_losing_streak}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Fees Paid (0.05%):</span> <span className="text-gray-400">${backtestResult.inSample?.fees}</span>
                  </div>
                </div>

                <div className="p-4 bg-[#0C152B] border border-[#1C2E52] rounded-xl space-y-3 font-mono text-xs">
                  <div className="font-bold text-purple-300 font-sans border-b border-[#1C2E52] pb-2">
                    Out-Of-Sample (Validation Dataset)
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Trades:</span> <span className="text-white">{backtestResult.outOfSample?.total_trades}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Win Rate:</span> <span className="text-emerald-400">{backtestResult.outOfSample?.win_rate_pct}%</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Profit Factor:</span> <span className="text-white">{backtestResult.outOfSample?.profit_factor}x</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Net PnL:</span> <span className={backtestResult.outOfSample?.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>${backtestResult.outOfSample?.net_pnl}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Max Drawdown:</span> <span className="text-rose-400">${backtestResult.outOfSample?.max_drawdown_usd}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Losing Streak:</span> <span className="text-white">{backtestResult.outOfSample?.max_losing_streak}</span>
                  </div>
                  <div className="flex justify-between text-[#9CA3AF]">
                    <span>Fees Paid (0.05%):</span> <span className="text-gray-400">${backtestResult.outOfSample?.fees}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-[#0C152B] rounded-lg border border-[#1C2E52] text-xs font-sans text-[#9CA3AF]">
                ⚠️ <span className="font-semibold text-white">Honest Forensics:</span> {backtestResult.disclaimer}
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-[#6B7280] space-y-3">
              <Activity className="w-10 h-10 text-[#4B5563] mx-auto" />
              <div className="text-sm font-bold text-white font-mono uppercase tracking-wider">
                NO BACKTEST EXECUTED YET
              </div>
              <p className="text-xs text-[#9CA3AF] max-w-md mx-auto">
                Select candle range and click "Run Real Backtest" to test the M1 Institutional Strategy on historical Binance ETHUSDT perpetual data.
              </p>
            </div>
          )}
        </div>
      )}

      {/* MODAL: LIVE TRADING CONFIRMATION */}
      {showLiveModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#0A1224] border border-rose-500/50 rounded-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-rose-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base font-bold text-white font-mono">ACTIVATE LIVE BINANCE FUTURES</h3>
            </div>
            <p className="text-xs text-[#9CA3AF] leading-relaxed">
              You are about to switch the M1 Scalper from Paper simulation to <span className="text-rose-400 font-bold">REAL LIVE BINANCE FUTURES TRADING</span> with 100x leverage on ETHUSDT.
            </p>

            <div className="space-y-3 text-xs font-mono">
              <div>
                <label className="text-[#9CA3AF] block mb-1">BINANCE API KEY</label>
                <input
                  type="text"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder="Enter Binance Futures API Key"
                  className="w-full bg-[#0C152B] border border-[#1C2E52] rounded-lg p-2.5 text-white focus:border-rose-400 outline-none text-xs"
                />
              </div>
              <div>
                <label className="text-[#9CA3AF] block mb-1">BINANCE API SECRET (Kept Secure)</label>
                <input
                  type="password"
                  value={apiSecretInput}
                  onChange={(e) => setApiSecretInput(e.target.value)}
                  placeholder="Enter Binance Futures API Secret"
                  className="w-full bg-[#0C152B] border border-[#1C2E52] rounded-lg p-2.5 text-white focus:border-rose-400 outline-none text-xs"
                />
              </div>

              <label className="flex items-start space-x-2 pt-2 cursor-pointer font-sans text-xs text-white">
                <input
                  type="checkbox"
                  checked={confirmLiveCheck}
                  onChange={(e) => setConfirmLiveCheck(e.target.checked)}
                  className="mt-0.5"
                />
                <span>I confirm that I understand real trading involves capital risk. 100x leverage on $0.50 margin is configured.</span>
              </label>
            </div>

            <div className="flex justify-end space-x-2 pt-3">
              <button
                onClick={() => setShowLiveModal(false)}
                className="px-4 py-2 bg-[#0C152B] hover:bg-[#0E1B38] text-[#9CA3AF] rounded-lg text-xs font-bold"
              >
                CANCEL
              </button>
              <button
                onClick={() => handleSwitchMode('LIVE')}
                disabled={actionLoading || !confirmLiveCheck}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-bold rounded-lg text-xs font-sans transition-all cursor-pointer shadow-lg shadow-rose-900/40"
              >
                {actionLoading ? 'CONNECTING...' : 'CONFIRM & ACTIVATE LIVE'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: EMERGENCY STOP CONFIRMATION */}
      {showEmergencyModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-[#0A1224] border border-rose-500 rounded-2xl p-6 space-y-4 shadow-2xl text-center">
            <ShieldAlert className="w-12 h-12 text-rose-500 mx-auto" />
            <h3 className="text-base font-bold text-white font-mono">CONFIRM EMERGENCY STOP</h3>
            <p className="text-xs text-[#9CA3AF] leading-relaxed">
              This will immediately cancel all open Binance orders, market-close any active position, and halt the bot.
            </p>
            <div className="flex justify-center space-x-3 pt-2">
              <button
                onClick={() => setShowEmergencyModal(false)}
                className="px-4 py-2 bg-[#0C152B] text-[#9CA3AF] rounded-lg text-xs font-bold"
              >
                ABORT
              </button>
              <button
                onClick={() => handleControlAction('emergency_stop')}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-lg text-xs font-mono shadow-lg shadow-rose-900/40 cursor-pointer"
              >
                EXECUTE STOP
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
