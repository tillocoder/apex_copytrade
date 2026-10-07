import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import {
  Zap, Sparkles, TrendingUp, TrendingDown, Minus,
  Activity, RefreshCw, History, Info,
  ChevronRight, BarChart2, ShieldCheck, AlertTriangle,
  CheckCircle2, Layers, Cpu, Compass, Crosshair, Clock,
  Play, Calendar, FileText
} from 'lucide-react';
import { ApexCandleChart } from '../common/ApexCandleChart';
import { SignalsService } from '../../services/signalsService';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Verification { label: string; passed: boolean; }
interface Signal {
  id: string; symbol: string; side: 'BUY' | 'SELL' | 'NO_TRADE';
  timeframe: string; aiScore: number; confidence: number;
  probability: number; rr: number; entry: number; sl: number; tp?: number;
  tp1?: number; tp2?: number; tp3?: number;
  status: string; quantScore?: number; aiNotes?: string; reasoning?: string;
  timestamp?: number; exit_timestamp?: number;
  formatted_time?: string; createdAt?: string;
  verification?: Verification[]; passedFactors?: number; totalFactors?: number;
  indicators?: { atr?: number; rsi?: number; ema21?: number; ema50?: number;
    ema200?: number; macdHist?: number; volumeDelta?: number; trend?: string; };
}

// ─── Error Boundary ───────────────────────────────────────────────────────────
class LiveSignalsErrorBoundary extends React.Component<
  { children: React.ReactNode }, { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(e: any, i: any) { console.error('LiveSignals error:', e, i); }
  render() {
    if (this.state.hasError) return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-apex-bg text-apex-text">
        <div className="p-4 bg-apex-danger/10 border border-apex-danger/30 rounded-lg text-center max-w-md space-y-3">
          <h3 className="text-sm font-bold text-apex-danger">LIVE AI SIGNALS RECOVERED</h3>
          <p className="text-xs text-apex-muted">A rendering anomaly occurred. Workspace safely reset.</p>
          <button onClick={() => this.setState({ hasError: false })}
            className="px-4 py-1.5 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border rounded text-xs font-bold text-apex-text transition-colors">
            Reload Workspace
          </button>
        </div>
      </div>
    );
    return this.props.children;
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
const fmt = (v: any, d = 2) => {
  if (v === undefined || v === null || isNaN(Number(v))) return '0.00';
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
};
const fmtRR = (v: any) => { if (v == null || isNaN(Number(v))) return '2.00'; return Number(v).toFixed(2); };
const str = (v: any, fb = '') => (typeof v === 'string' ? v : typeof v === 'number' || typeof v === 'boolean' ? String(v) : fb);
const inc = (v: any, s: string) => typeof v === 'string' && v.includes(s);
const num = (v: unknown) => {
  const value = Number(v);
  return Number.isFinite(value) ? value : 0;
};

const signalTargets = (signal: Signal | null) => {
  if (!signal) return [] as Array<{ label: string; value: number }>;
  const entry = num(signal.entry);
  const isBuy = signal.side === 'BUY';
  const raw = Object.entries(signal as unknown as Record<string, unknown>)
    .map(([key, value]) => {
      const match = /^tp(\d+)$/i.exec(key);
      return match ? { label: `TP${match[1]}`, order: Number(match[1]), value: num(value) } : null;
    })
    .filter((level): level is { label: string; order: number; value: number } => level !== null);

  if (raw.length === 0 && num(signal.tp) > 0) raw.push({ label: 'TP1', order: 1, value: num(signal.tp) });

  return raw.filter(level =>
    level.value > 0 &&
    (isBuy ? level.value > entry : level.value < entry)
  ).sort((a, b) => a.order - b.order).map(({ label, value }) => ({ label, value }));
};

// ─── Main Content ─────────────────────────────────────────────────────────────
const LiveSignalsContent: React.FC = () => {
  const { signals: initSigs, setSignals: setGlobalSignals } = useTerminal();
  const [signals, setSig] = React.useState<Signal[]>(() => Array.isArray(initSigs) ? (initSigs as Signal[]) : []);
  const [history, setHist] = React.useState<Signal[]>([]);
  const [loading, setLoad] = React.useState(false);
  const [loadingHist, setLoadH] = React.useState(false);
  const [lastUpdate, setLU] = React.useState<Date | null>(null);
  const [selected, setSel] = React.useState<Signal | null>(null);

  // Autonomous AI Discovery State
  const [viewMode, setViewMode] = React.useState<'DISCOVERY' | 'ACTIVE_LEGACY' | 'ANALYTICS' | 'REPLAY_LAB'>('DISCOVERY');
  const [discoveryCards, setDiscoveryCards] = React.useState<Record<string, any>>({});
  const [selectedSymbol, setSelectedSymbol] = React.useState<string>('BTCUSDT');
  const [discoveryHistory, setDiscoveryHistory] = React.useState<any[]>([]);
  const [discoveryAnalytics, setDiscoveryAnalytics] = React.useState<any>(null);
  const [scanningNow, setScanningNow] = React.useState<boolean>(false);
  const [historyTab, setHistoryTab] = React.useState<'AI_PAPER' | 'LEGACY_HISTORY'>('AI_PAPER');

  // Historical Replay & Forensic Statistical Validation Lab State
  const [replayReport, setReplayReport] = React.useState<any>(null);
  const [replayOosReport, setReplayOosReport] = React.useState<any>(null);
  const [replaySignals, setReplaySignals] = React.useState<any[]>([]);
  const [replayRunning, setReplayRunning] = React.useState<boolean>(false);
  const [replaySymbol, setReplaySymbol] = React.useState<string>('BTCUSDT');
  const [replayDays, setReplayDays] = React.useState<number>(60);
  const [replayMode, setReplayMode] = React.useState<string>('CACHED_GEMINI_REPLAY');
  const [replayPolicy, setReplayPolicy] = React.useState<string>('STOP_FIRST');
  const [replaySubTab, setReplaySubTab] = React.useState<'CONFIDENCE' | 'SETUPS' | 'REGIMES' | 'SESSIONS' | 'WALK_FORWARD' | 'SIGNALS_LOG'>('CONFIDENCE');
  const [signalsLogFilter, setSignalsLogFilter] = React.useState<'ALL' | 'WIN' | 'LOSS' | 'EXPIRED'>('ALL');

  const fetchDiscoveryData = async () => {
    try {
      const cards = await SignalsService.fetchMarketDiscoveryCards();
      if (cards && Object.keys(cards).length > 0) {
        setDiscoveryCards(cards);
      }
      const hist = await SignalsService.fetchMarketDiscoveryHistory();
      if (Array.isArray(hist)) {
        setDiscoveryHistory(hist);
      }
      const an = await SignalsService.fetchMarketDiscoveryAnalytics();
      if (an) {
        setDiscoveryAnalytics(an);
      }
    } catch (e) {
      console.warn('[LiveSignals] fetchDiscoveryData error:', e);
    }
  };

  const fetchReplayData = async () => {
    try {
      const res = await SignalsService.fetchReplayReport();
      if (res?.report) {
        setReplayReport(res.report);
      }
      if (res?.oos_report) {
        setReplayOosReport(res.oos_report);
      }
      const sigs = await SignalsService.fetchReplaySignals(100);
      if (Array.isArray(sigs)) {
        setReplaySignals(sigs);
      }
    } catch (e) {
      console.warn('[LiveSignals] fetchReplayData error:', e);
    }
  };

  const handleRunReplay = async (walkForward: boolean = false) => {
    setReplayRunning(true);
    try {
      await SignalsService.runReplay({
        symbol: replaySymbol,
        days: replayDays,
        mode: replayMode,
        same_bar_policy: replayPolicy,
        walk_forward: walkForward
      });
      await fetchReplayData();
    } catch (e) {
      console.error('[LiveSignals] handleRunReplay error:', e);
    } finally {
      setReplayRunning(false);
    }
  };

  const handleScanNow = async () => {
    setScanningNow(true);
    try {
      await SignalsService.triggerMarketDiscoveryNow();
      await fetchDiscoveryData();
      await fetchSignals();
    } catch (e) {
      console.error('[LiveSignals] Scan error:', e);
    } finally {
      setScanningNow(false);
    }
  };

  const fetchSignals = async () => {
    setLoad(true);
    try {
      const d = await SignalsService.fetchLiveSignals();
      if (Array.isArray(d)) {
        const isActive = (s: any) => {
          if (!s) return false;
          const st = String(s.status || '').toUpperCase();
          if (st.startsWith('CLOSED_') || st === 'SL_HIT' || st === 'TP1_HIT' ||
              st === 'TP2_HIT' || st === 'TP3_HIT' || st === 'CLOSED' ||
              st === 'EXPIRED' || st === 'CANCELLED') return false;
          return true;
        };
        const activeOnly = d.filter(isActive);
        setSig(activeOnly);
        if (setGlobalSignals) setGlobalSignals(activeOnly);
        setLU(new Date());
      }
    } catch (e) {
      console.warn('[LiveSignals] signals fetch error:', e);
    } finally {
      setLoad(false);
    }
  };

  const fetchHistory = async () => {
    setLoadH(true);
    try {
      const d = await SignalsService.fetchSignalsHistory();
      if (Array.isArray(d)) setHist(d.filter(Boolean));
    } catch (e) {
      console.warn('[LiveSignals] history fetch error:', e);
    } finally {
      setLoadH(false);
    }
  };

  React.useEffect(() => {
    fetchSignals();
    fetchHistory();
    fetchDiscoveryData();
    fetchReplayData();
    const iv = setInterval(() => {
      fetchSignals();
      fetchHistory();
      fetchDiscoveryData();
    }, 15000);
    return () => clearInterval(iv);
  }, []);

  const SIcon = ({ side }: { side?: string }) => {
    if (side === 'BUY' || side === 'LONG')  return <TrendingUp  className="w-3.5 h-3.5 text-emerald-400"/>;
    if (side === 'SELL' || side === 'SHORT') return <TrendingDown className="w-3.5 h-3.5 text-rose-400"/>;
    return <Minus className="w-3.5 h-3.5 text-amber-400"/>;
  };

  const ACTIVE_STATUSES = new Set(['ACTIVE', 'PENDING', 'CONFIRMED', 'OPEN']);
  const CLOSED_PREFIXES = ['CLOSED_', 'SL_HIT', 'TP1_HIT', 'TP2_HIT', 'TP3_HIT'];
  const sigs = Array.isArray(signals)
    ? signals.filter(signal => {
        if (!signal) return false;
        const st = String(signal.status || '').toUpperCase();
        if (CLOSED_PREFIXES.some(p => st.startsWith(p) || st === p)) return false;
        if (st === 'CLOSED' || st === 'EXPIRED' || st === 'CANCELLED') return false;
        return ACTIVE_STATUSES.has(st);
      })
    : [];
  const hist = Array.isArray(history) ? history.filter(Boolean) : [];
  const selectedTargets = signalTargets(selected);

  // Active discovery card for the selected symbol
  const activeDiscoveryCard = discoveryCards[selectedSymbol] || null;

  // Build simulated signal object for ApexCandleChart from discovery card
  const chartSignal = React.useMemo(() => {
    if (selected) return selected;
    if (!activeDiscoveryCard) return null;
    const dec = activeDiscoveryCard.decision;
    if (dec !== 'LONG' && dec !== 'SHORT') {
      return {
        id: `card_${activeDiscoveryCard.symbol}`,
        symbol: activeDiscoveryCard.symbol,
        side: 'NO_TRADE',
        entry: activeDiscoveryCard.price,
        sl: activeDiscoveryCard.price * 0.99,
        tp1: activeDiscoveryCard.price * 1.015,
        tp2: activeDiscoveryCard.price * 1.025,
        confidence: activeDiscoveryCard.confidence,
        timeframe: '15m',
        status: 'MONITORING'
      } as unknown as Signal;
    }
    const sideValue = dec === 'LONG' ? ('BUY' as const) : ('SELL' as const);
    return {
      id: `ai_${activeDiscoveryCard.symbol}`,
      symbol: activeDiscoveryCard.symbol,
      side: sideValue,
      entry: activeDiscoveryCard.entry || activeDiscoveryCard.price,
      sl: activeDiscoveryCard.stop_loss || (dec === 'LONG' ? activeDiscoveryCard.price * 0.985 : activeDiscoveryCard.price * 1.015),
      tp1: activeDiscoveryCard.take_profit_1 || (dec === 'LONG' ? activeDiscoveryCard.price * 1.015 : activeDiscoveryCard.price * 0.985),
      tp2: activeDiscoveryCard.take_profit_2 || (dec === 'LONG' ? activeDiscoveryCard.price * 1.028 : activeDiscoveryCard.price * 0.972),
      confidence: activeDiscoveryCard.confidence,
      timeframe: '15m',
      status: 'ACTIVE'
    } as unknown as Signal;
  }, [selected, activeDiscoveryCard]);

  const targetSymbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs">

      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-apex-border shrink-0 bg-apex-bgSecondary">
        <div className="flex items-center gap-3 font-bold text-sm text-apex-text">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-apex-accent animate-pulse"/>
            <span>APEX AI SIGNAL CENTER</span>
          </div>
          <span className="text-[10px] text-apex-muted font-normal">| 1-Hour Autonomous Market Discovery</span>

          {/* Mode Switcher */}
          <div className="flex items-center bg-apex-bg border border-apex-border rounded p-0.5 ml-3 text-[10px]">
            <button
              onClick={() => setViewMode('DISCOVERY')}
              className={`px-2.5 py-1 rounded font-bold flex items-center gap-1 transition-colors ${
                viewMode === 'DISCOVERY'
                  ? 'bg-apex-accent text-apex-bg font-extrabold shadow-sm'
                  : 'text-apex-muted hover:text-apex-text'
              }`}
            >
              <Cpu className="w-3 h-3"/> AI Market Discovery (BTC / ETH / SOL)
            </button>
            <button
              onClick={() => setViewMode('REPLAY_LAB')}
              className={`px-2.5 py-1 rounded font-bold flex items-center gap-1 transition-colors ${
                viewMode === 'REPLAY_LAB'
                  ? 'bg-apex-accent text-apex-bg font-extrabold shadow-sm'
                  : 'text-apex-muted hover:text-apex-text'
              }`}
            >
              <ShieldCheck className="w-3 h-3"/> 🔬 Replay & Edge Lab
            </button>
            <button
              onClick={() => setViewMode('ANALYTICS')}
              className={`px-2.5 py-1 rounded font-bold flex items-center gap-1 transition-colors ${
                viewMode === 'ANALYTICS'
                  ? 'bg-apex-accent text-apex-bg font-extrabold shadow-sm'
                  : 'text-apex-muted hover:text-apex-text'
              }`}
            >
              <BarChart2 className="w-3 h-3"/> AI Analytics
            </button>
            <button
              onClick={() => setViewMode('ACTIVE_LEGACY')}
              className={`px-2.5 py-1 rounded font-bold flex items-center gap-1 transition-colors ${
                viewMode === 'ACTIVE_LEGACY'
                  ? 'bg-apex-accent text-apex-bg font-extrabold shadow-sm'
                  : 'text-apex-muted hover:text-apex-text'
              }`}
            >
              <Activity className="w-3 h-3"/> Active Signals ({sigs.length})
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {(loading || loadingHist || scanningNow) && (
            <div className="flex items-center gap-1 text-apex-muted text-[10px] animate-pulse">
              <Activity className="w-3 h-3 animate-spin"/> {scanningNow ? 'Gemini 3.5 Flash Scanning...' : 'Syncing...'}
            </div>
          )}
          {lastUpdate && <div className="text-[9px] text-apex-muted">Updated: {lastUpdate.toLocaleTimeString()}</div>}

          <button
            onClick={handleScanNow}
            disabled={scanningNow}
            className="flex items-center gap-1 px-3 py-1 bg-apex-accent/15 hover:bg-apex-accent/25 border border-apex-accent/40 rounded text-apex-accent text-[10px] font-bold transition-all disabled:opacity-50"
          >
            <Sparkles className={`w-3 h-3 ${scanningNow ? 'animate-spin' : ''}`}/>
            {scanningNow ? 'Analyzing...' : 'Scan Market Now'}
          </button>

          <button
            onClick={() => { fetchSignals(); fetchHistory(); fetchDiscoveryData(); }}
            className="flex items-center gap-1 px-2.5 py-1 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border rounded text-apex-text text-[10px] transition-colors"
          >
            <RefreshCw className="w-3 h-3"/> Refresh
          </button>

          <div className="text-[10px] text-apex-ai font-bold flex items-center gap-1 px-2 py-0.5 rounded bg-apex-ai/10 border border-apex-ai/20">
            <Sparkles className="w-3.5 h-3.5 text-apex-ai"/> GEMINI 3.5 FLASH
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === 'REPLAY_LAB' ? (
        <div className="flex-1 flex flex-col overflow-y-auto bg-[#0a0a0d] p-4 space-y-4">
          
          {/* Header & Controls Toolbar */}
          <div className="p-3.5 bg-apex-bgSecondary/70 rounded-xl border border-apex-border/80 shadow-lg space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-apex-border/50 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-apex-accent"/>
                  <h2 className="text-sm font-extrabold text-apex-text tracking-wide uppercase">
                    Institutional Historical Replay & Forensic Statistical Validation Lab
                  </h2>
                </div>
                <p className="text-[10px] text-apex-muted mt-0.5">
                  Strict Zero-Lookahead Replay (Candles &le; T) | Real Binance Futures Candles | Event-Driven M5 Execution | Realistic Friction (Net R)
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleRunReplay(false)}
                  disabled={replayRunning}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-apex-accent hover:bg-apex-accentHover text-apex-bg rounded-lg font-extrabold text-xs transition-all shadow-md disabled:opacity-50"
                >
                  <Play className={`w-3.5 h-3.5 fill-current ${replayRunning ? 'animate-spin' : ''}`} />
                  {replayRunning ? 'Simulating Historical Engine...' : 'Run Historical Replay'}
                </button>
                <button
                  onClick={() => handleRunReplay(true)}
                  disabled={replayRunning}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border rounded-lg text-apex-text font-bold text-xs transition-colors disabled:opacity-50"
                >
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  Walk-Forward (4 Windows)
                </button>
                <button
                  onClick={fetchReplayData}
                  disabled={replayRunning}
                  className="p-1.5 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border rounded-lg text-apex-text transition-colors"
                  title="Refresh Audit Data"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Interactive Parameters Controls */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-[10px]">
              {/* Symbol */}
              <div>
                <label className="text-[9px] font-bold text-apex-muted uppercase">Target Asset</label>
                <select
                  value={replaySymbol}
                  onChange={e => setReplaySymbol(e.target.value)}
                  className="mt-1 w-full bg-apex-bg border border-apex-border rounded px-2.5 py-1.5 text-apex-text font-mono font-bold focus:border-apex-accent outline-none"
                >
                  <option value="BTCUSDT">BTCUSDT (Binance Futures)</option>
                  <option value="ETHUSDT">ETHUSDT (Binance Futures)</option>
                  <option value="SOLUSDT">SOLUSDT (Binance Futures)</option>
                </select>
              </div>

              {/* Horizon */}
              <div>
                <label className="text-[9px] font-bold text-apex-muted uppercase">Replay Horizon</label>
                <select
                  value={replayDays}
                  onChange={e => setReplayDays(Number(e.target.value))}
                  className="mt-1 w-full bg-apex-bg border border-apex-border rounded px-2.5 py-1.5 text-apex-text font-mono font-bold focus:border-apex-accent outline-none"
                >
                  <option value={30}>30 Days (Fast Audit)</option>
                  <option value={60}>60 Days (Recommended)</option>
                  <option value={90}>90 Days (Quarterly Horizon)</option>
                  <option value={180}>180 Days (Half Year Multi-Regime)</option>
                  <option value={365}>365 Days (Full 1-Year Forensic)</option>
                </select>
              </div>

              {/* Mode */}
              <div>
                <label className="text-[9px] font-bold text-apex-muted uppercase">Replay Mode</label>
                <select
                  value={replayMode}
                  onChange={e => setReplayMode(e.target.value)}
                  className="mt-1 w-full bg-apex-bg border border-apex-border rounded px-2.5 py-1.5 text-apex-text font-mono font-bold focus:border-apex-accent outline-none"
                >
                  <option value="CACHED_GEMINI_REPLAY">MODE B: Cached Gemini (Hash-Keyed)</option>
                  <option value="DETERMINISTIC_REPLAY">MODE D: Deterministic Component Replay</option>
                  <option value="LIVE_GEMINI_REPLAY">MODE A: Live Gemini 3.5 Flash Replay</option>
                  <option value="SNAPSHOT_EXPORT">MODE C: Snapshot Export (No Gemini)</option>
                </select>
              </div>

              {/* Ambiguity Policy */}
              <div>
                <label className="text-[9px] font-bold text-apex-muted uppercase">Same-Bar SL/TP Policy</label>
                <select
                  value={replayPolicy}
                  onChange={e => setReplayPolicy(e.target.value)}
                  className="mt-1 w-full bg-apex-bg border border-apex-border rounded px-2.5 py-1.5 text-apex-text font-mono font-bold focus:border-apex-accent outline-none"
                >
                  <option value="STOP_FIRST">STOP_FIRST (Conservative Default)</option>
                  <option value="TARGET_FIRST">TARGET_FIRST (Aggressive)</option>
                  <option value="AMBIGUOUS_REJECT">AMBIGUOUS_REJECT (Discard Ambiguity)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Audit Status & Production Decision Banner */}
          {replayReport?.summary && (
            <div className={`p-3.5 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-3 ${
              replayReport.summary.production_classification === 'NOT_SUPPORTED_BY_DATA'
                ? 'bg-rose-950/20 border-rose-500/40 text-rose-200'
                : replayReport.summary.production_classification === 'PAPER_TEST_REQUIRED'
                ? 'bg-amber-950/20 border-amber-500/40 text-amber-200'
                : 'bg-emerald-950/20 border-emerald-500/40 text-emerald-200'
            }`}>
              <div className="flex items-center gap-2.5">
                <AlertTriangle className={`w-5 h-5 shrink-0 ${
                  replayReport.summary.production_classification === 'NOT_SUPPORTED_BY_DATA'
                    ? 'text-rose-400'
                    : replayReport.summary.production_classification === 'PAPER_TEST_REQUIRED'
                    ? 'text-amber-400'
                    : 'text-emerald-400'
                }`} />
                <div>
                  <div className="text-xs font-extrabold flex items-center gap-2 uppercase tracking-wide">
                    <span>PRODUCTION STATUS: {replayReport.summary.production_classification}</span>
                    <span className="px-2 py-0.5 rounded text-[8px] font-bold bg-apex-bg border border-apex-border text-apex-text">
                      {replayReport.summary.sample_size_rating} (N={replayReport.summary.executed_signals})
                    </span>
                  </div>
                  <p className="text-[10px] text-apex-muted mt-0.5">
                    {replayReport.summary.production_classification === 'NOT_SUPPORTED_BY_DATA'
                      ? 'Net expectancy is negative after realistic Binance Futures friction (commissions, slippage, spread). Live trading is strictly prohibited.'
                      : replayReport.summary.production_classification === 'PAPER_TEST_REQUIRED'
                      ? 'Positive gross expectancy detected, but requires continuous forward paper confirmation before capital commitment.'
                      : 'Statistical edge confirmed across multiple market regimes.'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-[9px] font-mono shrink-0">
                <span className="px-2 py-1 rounded bg-black/40 border border-white/10 text-emerald-400 font-bold">
                  ✓ ZERO LOOKAHEAD (t &le; T)
                </span>
                <span className="px-2 py-1 rounded bg-black/40 border border-white/10 text-cyan-400 font-bold">
                  FRICTION APPLIED: NET R
                </span>
              </div>
            </div>
          )}

          {/* Core Forensic KPI Cards */}
          {replayReport?.summary ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {/* Card 1: Net Expectancy */}
              <div className="p-3 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-1">
                <div className="text-[9px] font-bold text-apex-muted uppercase">Net Expectancy (R)</div>
                <div className={`text-xl font-extrabold font-mono ${
                  replayReport.summary.avg_net_r >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {replayReport.summary.avg_net_r > 0 ? '+' : ''}{replayReport.summary.avg_net_r} R
                </div>
                <div className="text-[8px] text-apex-muted font-mono">
                  95% Bootstrap CI: [{replayReport.summary.bootstrap_ci_expectancy?.[0] ?? '—'}, {replayReport.summary.bootstrap_ci_expectancy?.[1] ?? '—'}]
                </div>
                <div className="text-[8px] text-cyan-400">
                  Gross: {replayReport.summary.avg_gross_r > 0 ? '+' : ''}{replayReport.summary.avg_gross_r} R
                </div>
              </div>

              {/* Card 2: Win Rate */}
              <div className="p-3 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-1">
                <div className="text-[9px] font-bold text-apex-muted uppercase">Win Rate (Net)</div>
                <div className={`text-xl font-extrabold font-mono ${
                  replayReport.summary.win_rate_pct >= 40 ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {replayReport.summary.win_rate_pct}%
                </div>
                <div className="text-[8px] text-apex-muted font-mono">
                  95% Bootstrap CI: [{replayReport.summary.bootstrap_ci_win_rate?.[0] ?? '—'}%, {replayReport.summary.bootstrap_ci_win_rate?.[1] ?? '—'}%]
                </div>
                <div className="text-[8px] text-apex-muted">
                  TP1: {replayReport.summary.tp1_hit_rate_pct}% | TP2: {replayReport.summary.tp2_hit_rate_pct}%
                </div>
              </div>

              {/* Card 3: Profit Factor & Max DD */}
              <div className="p-3 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-1">
                <div className="text-[9px] font-bold text-apex-muted uppercase">Profit Factor & Drawdown</div>
                <div className="text-xl font-extrabold text-apex-accent font-mono">
                  {replayReport.summary.profit_factor}
                </div>
                <div className="text-[8px] text-rose-400 font-mono">
                  Max Drawdown: {replayReport.summary.max_drawdown_r} R
                </div>
                <div className="text-[8px] text-apex-muted">
                  Median R: {replayReport.summary.median_net_r} R
                </div>
              </div>

              {/* Card 4: Selectivity */}
              <div className="p-3 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-1">
                <div className="text-[9px] font-bold text-apex-muted uppercase">Selectivity (NO_TRADE)</div>
                <div className="text-xl font-extrabold text-cyan-400 font-mono">
                  {replayReport.summary.no_trade_pct}%
                </div>
                <div className="text-[8px] text-apex-muted">
                  Total Analyses: {replayReport.summary.total_analyses} H1 bars
                </div>
                <div className="text-[8px] text-emerald-400">
                  NO_TRADE Filtered: {replayReport.summary.no_trade_count}
                </div>
              </div>

              {/* Card 5: Excursions & Duration */}
              <div className="p-3 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-1">
                <div className="text-[9px] font-bold text-apex-muted uppercase">MFE / MAE / Duration</div>
                <div className="text-base font-extrabold text-apex-text font-mono">
                  <span className="text-emerald-400">+{replayReport.summary.avg_mfe_r}R</span> / <span className="text-rose-400">-{replayReport.summary.avg_mae_r}R</span>
                </div>
                <div className="text-[8px] text-apex-muted">
                  Avg Duration: {replayReport.summary.avg_holding_minutes} mins
                </div>
                <div className="text-[8px] text-apex-muted">
                  SL Hit Rate: {replayReport.summary.sl_hit_rate_pct}%
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 bg-apex-bgSecondary/40 rounded-xl border border-apex-border text-center text-apex-muted space-y-2">
              <Activity className="w-8 h-8 mx-auto text-apex-accent animate-spin" />
              <p className="text-xs font-bold text-apex-text">Loading Historical Replay Report...</p>
              <p className="text-[10px]">Click "Run Historical Replay" above to trigger a fresh analysis.</p>
            </div>
          )}

          {/* Deep-Dive Forensic Sub-Tabs */}
          {replayReport && (
            <div className="space-y-3">
              {/* Navigation Tabs */}
              <div className="flex flex-wrap items-center gap-1.5 border-b border-apex-border/60 pb-2 text-[10px]">
                {[
                  { id: 'CONFIDENCE', label: '1. Confidence Calibration (Sec 18)' },
                  { id: 'SETUPS', label: '2. Setup Families (Sec 19)' },
                  { id: 'REGIMES', label: '3. Market Regimes (Sec 20)' },
                  { id: 'SESSIONS', label: '4. Sessions & MTF (Sec 23-24)' },
                  { id: 'WALK_FORWARD', label: '5. Walk-Forward Windows (Sec 29)' },
                  { id: 'SIGNALS_LOG', label: '6. Historical Replay Signals Log (Sec 43)' },
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setReplaySubTab(tab.id as any)}
                    className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                      replaySubTab === tab.id
                        ? 'bg-apex-accent text-apex-bg font-extrabold shadow'
                        : 'bg-apex-surface hover:bg-apex-surfaceHover text-apex-muted hover:text-apex-text border border-apex-border'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Sub-Tab 1: CONFIDENCE CALIBRATION */}
              {replaySubTab === 'CONFIDENCE' && (
                <div className="p-4 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" /> Confidence Calibration Matrix (Section 18 & 26)
                      </h3>
                      <p className="text-[10px] text-apex-muted">
                        Forensic Question: Does higher AI confidence actually equate to higher historical win rate and positive expectancy?
                      </p>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-[10px]">
                      <thead>
                        <tr className="border-b border-apex-border text-apex-muted font-bold">
                          <th className="py-2 px-2">Confidence Bucket</th>
                          <th className="py-2 px-2">Signals Count</th>
                          <th className="py-2 px-2">Win Rate (%)</th>
                          <th className="py-2 px-2">Avg Net Expectancy (R)</th>
                          <th className="py-2 px-2">Profit Factor</th>
                          <th className="py-2 px-2">Statistical Calibration Reliability</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(replayReport.confidence_calibration || {}).map(([b, v]: [string, any]) => (
                          <tr key={b} className="border-b border-apex-border/30 hover:bg-white/5">
                            <td className="py-2 px-2 font-bold text-apex-text font-mono">{b}%</td>
                            <td className="py-2 px-2 text-apex-muted font-mono">{v.count}</td>
                            <td className={`py-2 px-2 font-bold font-mono ${
                              v.win_rate_pct >= 40 ? 'text-emerald-400' : 'text-rose-400'
                            }`}>
                              {v.win_rate_pct}%
                            </td>
                            <td className={`py-2 px-2 font-bold font-mono ${
                              v.avg_net_r >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}>
                              {v.avg_net_r > 0 ? '+' : ''}{v.avg_net_r} R
                            </td>
                            <td className="py-2 px-2 font-bold text-apex-accent font-mono">{v.profit_factor}</td>
                            <td className="py-2 px-2">
                              <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                                v.reliability === 'RELIABLE_EDGE'
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  : v.reliability === 'INVERTED_EDGE'
                                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              }`}>
                                {v.reliability}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Sub-Tab 2: SETUP FAMILIES */}
              {replaySubTab === 'SETUPS' && (
                <div className="p-4 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-3">
                  <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-cyan-400" /> Setup Families Performance (Section 19)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-[10px]">
                      <thead>
                        <tr className="border-b border-apex-border text-apex-muted font-bold">
                          <th className="py-2 px-2">Setup Type</th>
                          <th className="py-2 px-2">Signals Count</th>
                          <th className="py-2 px-2">Win Rate (%)</th>
                          <th className="py-2 px-2">Avg Net Expectancy (R)</th>
                          <th className="py-2 px-2">Profit Factor</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(replayReport.setup_breakdown || {}).map(([s, v]: [string, any]) => (
                          <tr key={s} className="border-b border-apex-border/30 hover:bg-white/5">
                            <td className="py-2 px-2 font-bold text-apex-text">{s}</td>
                            <td className="py-2 px-2 text-apex-muted font-mono">{v.count}</td>
                            <td className={`py-2 px-2 font-bold font-mono ${v.win_rate_pct >= 40 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {v.win_rate_pct}%
                            </td>
                            <td className={`py-2 px-2 font-bold font-mono ${v.avg_net_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {v.avg_net_r > 0 ? '+' : ''}{v.avg_net_r} R
                            </td>
                            <td className="py-2 px-2 font-bold text-apex-accent font-mono">{v.profit_factor}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Sub-Tab 3: REGIMES */}
              {replaySubTab === 'REGIMES' && (
                <div className="p-4 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-3">
                  <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                    <Compass className="w-4 h-4 text-amber-400" /> Market Regimes Performance (Section 20)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-[10px]">
                      <thead>
                        <tr className="border-b border-apex-border text-apex-muted font-bold">
                          <th className="py-2 px-2">Regime Classification</th>
                          <th className="py-2 px-2">Signals Count</th>
                          <th className="py-2 px-2">Win Rate (%)</th>
                          <th className="py-2 px-2">Avg Net Expectancy (R)</th>
                          <th className="py-2 px-2">Profit Factor</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(replayReport.regime_breakdown || {}).map(([r, v]: [string, any]) => (
                          <tr key={r} className="border-b border-apex-border/30 hover:bg-white/5">
                            <td className="py-2 px-2 font-bold text-apex-text">{r}</td>
                            <td className="py-2 px-2 text-apex-muted font-mono">{v.count}</td>
                            <td className={`py-2 px-2 font-bold font-mono ${v.win_rate_pct >= 40 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {v.win_rate_pct}%
                            </td>
                            <td className={`py-2 px-2 font-bold font-mono ${v.avg_net_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {v.avg_net_r > 0 ? '+' : ''}{v.avg_net_r} R
                            </td>
                            <td className="py-2 px-2 font-bold text-apex-accent font-mono">{v.profit_factor}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Sub-Tab 4: SESSIONS & MTF */}
              {replaySubTab === 'SESSIONS' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Sessions */}
                  <div className="p-4 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-3">
                    <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-cyan-400" /> Trading Sessions (UTC) (Section 23)
                    </h3>
                    <table className="w-full text-left border-collapse text-[10px]">
                      <thead>
                        <tr className="border-b border-apex-border text-apex-muted font-bold">
                          <th className="py-2">Session</th>
                          <th className="py-2">Signals</th>
                          <th className="py-2">Win Rate</th>
                          <th className="py-2">Net Exp (R)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(replayReport.session_breakdown || {}).map(([s, v]: [string, any]) => (
                          <tr key={s} className="border-b border-apex-border/30 hover:bg-white/5">
                            <td className="py-1.5 font-bold text-apex-text">{s}</td>
                            <td className="py-1.5 text-apex-muted font-mono">{v.count}</td>
                            <td className={`py-1.5 font-bold font-mono ${v.win_rate_pct >= 40 ? 'text-emerald-400' : 'text-rose-400'}`}>{v.win_rate_pct}%</td>
                            <td className={`py-1.5 font-bold font-mono ${v.avg_net_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {v.avg_net_r > 0 ? '+' : ''}{v.avg_net_r} R
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* MTF Alignment */}
                  <div className="p-4 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-3">
                    <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-emerald-400" /> Multi-Timeframe Alignment (Section 24)
                    </h3>
                    <table className="w-full text-left border-collapse text-[10px]">
                      <thead>
                        <tr className="border-b border-apex-border text-apex-muted font-bold">
                          <th className="py-2">MTF Status</th>
                          <th className="py-2">Signals</th>
                          <th className="py-2">Win Rate</th>
                          <th className="py-2">Net Exp (R)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(replayReport.mtf_breakdown || {}).map(([m, v]: [string, any]) => (
                          <tr key={m} className="border-b border-apex-border/30 hover:bg-white/5">
                            <td className="py-1.5 font-bold text-apex-text">{m}</td>
                            <td className="py-1.5 text-apex-muted font-mono">{v.count}</td>
                            <td className={`py-1.5 font-bold font-mono ${v.win_rate_pct >= 40 ? 'text-emerald-400' : 'text-rose-400'}`}>{v.win_rate_pct}%</td>
                            <td className={`py-1.5 font-bold font-mono ${v.avg_net_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {v.avg_net_r > 0 ? '+' : ''}{v.avg_net_r} R
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Sub-Tab 5: WALK-FORWARD WINDOWS */}
              {replaySubTab === 'WALK_FORWARD' && (
                <div className="p-4 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                        <Activity className="w-4 h-4 text-cyan-400" /> Walk-Forward Out-Of-Sample Validation (Section 29)
                      </h3>
                      <p className="text-[10px] text-apex-muted">
                        Rolling 4 Windows (60-Day In-Sample Training &rarr; 30-Day Out-of-Sample Forward Test)
                      </p>
                    </div>
                    {replayOosReport?.oos_edge_classification && (
                      <span className="px-3 py-1 rounded bg-cyan-950/40 border border-cyan-500/40 text-cyan-300 font-bold text-xs">
                        CLASSIFICATION: {replayOosReport.oos_edge_classification}
                      </span>
                    )}
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-[10px]">
                      <thead>
                        <tr className="border-b border-apex-border text-apex-muted font-bold">
                          <th className="py-2 px-2">Window</th>
                          <th className="py-2 px-2">Train Period</th>
                          <th className="py-2 px-2">Train Trades</th>
                          <th className="py-2 px-2">Train Exp (R)</th>
                          <th className="py-2 px-2">Test Period</th>
                          <th className="py-2 px-2">Test Trades</th>
                          <th className="py-2 px-2">Test Exp (R)</th>
                          <th className="py-2 px-2">Delta R (Decay)</th>
                          <th className="py-2 px-2">Window Outcome</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Array.isArray(replayOosReport?.windows) ? (
                          replayOosReport.windows.map((w: any) => (
                            <tr key={w.window_id} className="border-b border-apex-border/30 hover:bg-white/5">
                              <td className="py-2 px-2 font-bold text-apex-text font-mono">{w.window_id}</td>
                              <td className="py-2 px-2 text-apex-muted font-mono">{w.train_period}</td>
                              <td className="py-2 px-2 text-apex-muted font-mono">{w.train_trades}</td>
                              <td className="py-2 px-2 font-mono font-bold">{w.train_expectancy_r > 0 ? '+' : ''}{w.train_expectancy_r} R</td>
                              <td className="py-2 px-2 text-apex-muted font-mono">{w.test_period}</td>
                              <td className="py-2 px-2 text-apex-muted font-mono">{w.test_trades}</td>
                              <td className={`py-2 px-2 font-mono font-bold ${w.test_expectancy_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {w.test_expectancy_r > 0 ? '+' : ''}{w.test_expectancy_r} R
                              </td>
                              <td className="py-2 px-2 font-mono text-apex-muted">{w.delta_r > 0 ? '+' : ''}{w.delta_r} R</td>
                              <td className="py-2 px-2">
                                <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                                  w.result === 'ROBUST_EDGE' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                }`}>
                                  {w.result}
                                </span>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={9} className="py-6 text-center text-apex-muted">
                              Click "Walk-Forward (4 Windows)" above to run rolling out-of-sample testing.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Sub-Tab 6: SIGNALS LOG */}
              {replaySubTab === 'SIGNALS_LOG' && (
                <div className="p-4 bg-apex-bgSecondary/60 rounded-xl border border-apex-border space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-apex-accent" /> Executed Replay Signals Journal (Section 43)
                      </h3>
                      <p className="text-[10px] text-apex-muted">
                        Every historical trade verified with zero look-ahead bias and simulated on future M5 candles.
                      </p>
                    </div>

                    {/* Outcome Filters */}
                    <div className="flex items-center gap-1 text-[9px]">
                      {(['ALL', 'WIN', 'LOSS', 'EXPIRED'] as const).map(f => (
                        <button
                          key={f}
                          onClick={() => setSignalsLogFilter(f)}
                          className={`px-2.5 py-1 rounded font-bold transition-colors ${
                            signalsLogFilter === f
                              ? 'bg-apex-accent text-apex-bg font-extrabold'
                              : 'bg-apex-surface hover:bg-apex-surfaceHover text-apex-muted border border-apex-border'
                          }`}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="overflow-x-auto max-h-[500px]">
                    <table className="w-full text-left border-collapse text-[10px]">
                      <thead className="sticky top-0 bg-apex-bgSecondary border-b border-apex-border text-apex-muted font-bold">
                        <tr>
                          <th className="py-2 px-2">Timestamp (UTC)</th>
                          <th className="py-2 px-2">Symbol</th>
                          <th className="py-2 px-2">Side</th>
                          <th className="py-2 px-2">Setup Type</th>
                          <th className="py-2 px-2">Entry Price</th>
                          <th className="py-2 px-2">Stop Loss</th>
                          <th className="py-2 px-2">Take Profit 1</th>
                          <th className="py-2 px-2">Outcome Status</th>
                          <th className="py-2 px-2">MFE</th>
                          <th className="py-2 px-2">MAE</th>
                          <th className="py-2 px-2">Gross R</th>
                          <th className="py-2 px-2">Net R</th>
                        </tr>
                      </thead>
                      <tbody>
                        {replaySignals
                          .filter(s => {
                            if (signalsLogFilter === 'ALL') return true;
                            const st = String(s.status || '');
                            if (signalsLogFilter === 'WIN') return st.startsWith('WIN');
                            if (signalsLogFilter === 'LOSS') return st.startsWith('LOSS');
                            if (signalsLogFilter === 'EXPIRED') return st === 'EXPIRED';
                            return true;
                          })
                          .slice(0, 50)
                          .map((s, idx) => {
                            const isWin = String(s.status || '').startsWith('WIN');
                            const isLoss = String(s.status || '').startsWith('LOSS');
                            return (
                              <tr key={idx} className="border-b border-apex-border/30 hover:bg-white/5 font-mono">
                                <td className="py-2 px-2 text-apex-muted">{s.datetime || s.timestamp}</td>
                                <td className="py-2 px-2 font-bold text-apex-text">{s.symbol}</td>
                                <td className="py-2 px-2">
                                  <span className={`px-1.5 py-0.5 rounded font-bold text-[8px] ${
                                    s.decision === 'LONG' ? 'text-emerald-400 bg-emerald-500/15' : 'text-rose-400 bg-rose-500/15'
                                  }`}>
                                    {s.decision}
                                  </span>
                                </td>
                                <td className="py-2 px-2 text-apex-text">{s.setup_type}</td>
                                <td className="py-2 px-2 text-apex-text">${fmt(s.fill_price || s.entry)}</td>
                                <td className="py-2 px-2 text-rose-400">${fmt(s.stop_loss)}</td>
                                <td className="py-2 px-2 text-emerald-400">${fmt(s.take_profit_1)}</td>
                                <td className="py-2 px-2">
                                  <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                                    isWin ? 'bg-emerald-500/20 text-emerald-400' : isLoss ? 'bg-rose-500/20 text-rose-400' : 'bg-apex-surface text-apex-muted'
                                  }`}>
                                    {s.status}
                                  </span>
                                </td>
                                <td className="py-2 px-2 text-emerald-400">+{s.mfe_r}R</td>
                                <td className="py-2 px-2 text-rose-400">-{s.mae_r}R</td>
                                <td className="py-2 px-2 font-bold">{s.gross_r > 0 ? '+' : ''}{s.gross_r}R</td>
                                <td className={`py-2 px-2 font-extrabold ${Number(s.net_r) > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  {Number(s.net_r) > 0 ? '+' : ''}{s.net_r}R
                                </td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* 3-Panel Main Layout */
        <div className="flex-1 flex overflow-hidden">

        {/* LEFT PANEL */}
        <div className="w-[360px] shrink-0 flex flex-col border-r border-apex-border overflow-hidden bg-apex-bgSecondary/30">
          
          {viewMode === 'DISCOVERY' ? (
            <>
              {/* Top Section Header */}
              <div className="px-3 py-2 border-b border-apex-border bg-apex-bgSecondary text-[10px] font-bold text-apex-muted uppercase tracking-wider flex justify-between items-center">
                <span className="flex items-center gap-1.5 text-apex-text font-extrabold">
                  <Compass className="w-3.5 h-3.5 text-apex-accent"/> Autonomous Asset Discovery
                </span>
                <span className="text-[9px] text-emerald-400 font-mono">3 Assets Active</span>
              </div>

              {/* 3 Asset Cards */}
              <div className="flex-1 overflow-y-auto p-2.5 space-y-2.5">
                {targetSymbols.map(sym => {
                  const card = discoveryCards[sym];
                  const isSel = selectedSymbol === sym;
                  const isLong = card?.decision === 'LONG';
                  const isShort = card?.decision === 'SHORT';
                  const isNoTrade = card?.decision === 'NO_TRADE';

                  return (
                    <div
                      key={sym}
                      onClick={() => { setSelectedSymbol(sym); setSel(null); }}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSel
                          ? 'border-apex-accent bg-apex-accent/10 shadow-md ring-1 ring-apex-accent/40'
                          : 'border-apex-border/60 hover:border-apex-accent/40 bg-apex-bg/90 hover:bg-apex-surface/40'
                      }`}
                    >
                      {/* Top Symbol & Live Price */}
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-extrabold text-sm text-apex-text tracking-wide">{sym}</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-apex-surface border border-apex-border font-bold text-apex-muted">
                            Q:{card ? card.data_quality_score : 100}%
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-[13px] text-apex-text font-mono">
                            ${card ? fmt(card.price) : '...'}
                          </div>
                        </div>
                      </div>

                      {/* Decision & Regime Banner */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-1">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-extrabold flex items-center gap-1 ${
                              isLong
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                                : isShort
                                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                                : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            <SIcon side={card?.decision}/>
                            {card?.decision || 'NO_TRADE'}
                          </span>
                          <span className="text-[9px] text-apex-muted font-bold">
                            {card?.confidence || 0}% Conf
                          </span>
                        </div>

                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-apex-surface border border-apex-border/50 text-apex-muted font-medium">
                          {card?.regime || 'RANGING'}
                        </span>
                      </div>

                      {/* Setup Info & MTF pills */}
                      <div className="bg-apex-bg/60 p-2 rounded border border-apex-border/40 text-[9px] space-y-1 mb-2">
                        <div className="flex justify-between items-center text-apex-muted">
                          <span>Setup: <strong className="text-apex-text">{card?.setup_type || 'NONE'}</strong></span>
                          <span>Quality: <strong className="text-apex-accent">{card?.setup_quality || 0}%</strong></span>
                        </div>
                        {card?.timeframe_analysis && (
                          <div className="flex items-center gap-1 pt-0.5 border-t border-apex-border/20 text-[8px]">
                            {['H4', 'H1', 'M15', 'M5', 'M1'].map(tf => {
                              const desc = card.timeframe_analysis[tf] || '';
                              const isBull = desc.toLowerCase().includes('bull');
                              const isBear = desc.toLowerCase().includes('bear');
                              return (
                                <span
                                  key={tf}
                                  className={`px-1 rounded font-bold ${
                                    isBull
                                      ? 'text-emerald-400 bg-emerald-500/10'
                                      : isBear
                                      ? 'text-rose-400 bg-rose-500/10'
                                      : 'text-apex-muted bg-apex-surface'
                                  }`}
                                  title={`${tf}: ${desc}`}
                                >
                                  {tf}
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* Levels Grid (if LONG or SHORT) */}
                      {card && (isLong || isShort) && (
                        <div className="grid grid-cols-3 gap-1 text-[8px] bg-apex-bg p-1.5 rounded border border-apex-border/60">
                          <div>
                            <span className="text-apex-muted">Entry</span>
                            <div className="font-bold text-apex-text font-mono">${fmt(card.entry)}</div>
                          </div>
                          <div>
                            <span className="text-rose-400">SL</span>
                            <div className="font-bold text-rose-400 font-mono">${fmt(card.stop_loss)}</div>
                          </div>
                          <div>
                            <span className="text-emerald-400">TP1 (1:{card.rr_tp1 || 1.6})</span>
                            <div className="font-bold text-emerald-400 font-mono">${fmt(card.take_profit_1)}</div>
                          </div>
                        </div>
                      )}

                      {/* Footer: Latency & Model */}
                      <div className="flex items-center justify-between text-[8px] text-apex-muted mt-1.5 pt-1 border-t border-apex-border/30">
                        <span>{card?.model_used || 'gemini-3.5-flash'}</span>
                        <span className="flex items-center gap-1 text-apex-accent font-bold">
                          View Analysis <ChevronRight className="w-2.5 h-2.5"/>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : viewMode === 'ACTIVE_LEGACY' ? (
            <>
              {/* Legacy Active Signals */}
              <div className="px-3 py-1.5 border-b border-apex-border bg-apex-bgSecondary text-[9px] font-bold text-apex-muted uppercase tracking-widest flex justify-between">
                <span>Active Signals</span>
                <span className="text-apex-accent">{sigs.length} Live</span>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {sigs.map(s => {
                  if (!s) return null;
                  const buy = s.side === 'BUY';
                  const sel = selected?.id === s.id;
                  const targets = signalTargets(s);
                  return (
                    <div
                      key={s.id || Math.random()}
                      onClick={() => { setSel(s); setSelectedSymbol(s.symbol.replace('/', '')); }}
                      className={`p-3 rounded border cursor-pointer transition-all group ${
                        sel
                          ? 'border-apex-accent bg-apex-accent/5'
                          : 'border-apex-border hover:border-apex-accent/40 bg-apex-surface/30 hover:bg-apex-surface/50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-[13px] text-apex-text">{s.symbol || 'BTC/USDT'}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold flex items-center gap-0.5 ${
                            buy
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25'
                              : 'bg-rose-500/15 text-rose-400 border border-rose-500/25'
                          }`}>
                            <SIcon side={s.side}/>{s.side}
                          </span>
                          <span className="text-[9px] text-apex-muted">{s.timeframe || 'M15'}</span>
                        </div>
                        <span className="text-[8px] text-apex-muted">
                          {typeof s.formatted_time === 'string' ? (s.formatted_time.split(' ')[1] || s.formatted_time) : str(s.createdAt, '')}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-1 text-[10px] mb-2">
                        <div className="bg-apex-bg p-1.5 rounded border border-apex-border/40">
                          <div className="text-[8px] text-apex-muted">ENTRY</div>
                          <div className="font-bold text-apex-text">${fmt(s.entry)}</div>
                        </div>
                        <div className="bg-apex-bg p-1.5 rounded border border-rose-500/20">
                          <div className="text-[8px] text-rose-400">STOP</div>
                          <div className="font-bold text-rose-400">${fmt(s.sl)}</div>
                        </div>
                        <div className="bg-apex-bg p-1.5 rounded border border-emerald-500/20">
                          <div className="text-[8px] text-emerald-400">TARGETS {targets.length ? `(${targets.length})` : ''}</div>
                          {targets.length ? targets.map(target => (
                            <div key={target.label} className="font-bold text-emerald-400 leading-tight">
                              {target.label} ${fmt(target.value)}
                            </div>
                          )) : <div className="font-bold text-apex-muted">—</div>}
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-[9px]">
                        <span className="text-apex-muted">R:R <span className="text-apex-accent font-bold">1:{fmtRR(s.rr)}</span></span>
                        <span className="text-apex-muted">AI <span className="text-apex-ai font-bold">{s.aiScore || s.confidence || '—'}%</span></span>
                        <span className="text-apex-accent font-bold flex items-center gap-0.5 group-hover:gap-1 transition-all">
                          Chart <ChevronRight className="w-3 h-3"/>
                        </span>
                      </div>
                    </div>
                  );
                })}
                {sigs.length === 0 && !loading && (
                  <div className="flex flex-col items-center justify-center py-16 text-apex-muted gap-2">
                    <Activity className="w-7 h-7 animate-pulse text-apex-ai"/>
                    <p className="text-[11px] font-bold">No Active Signals</p>
                    <p className="text-[10px] text-center max-w-[180px]">Hourly Autonomous AI scan active.</p>
                  </div>
                )}
              </div>
            </>
          ) : (
            /* ANALYTICS TAB SUMMARY */
            <div className="p-3 space-y-3 overflow-y-auto">
              <div className="font-bold text-apex-text text-sm flex items-center gap-1.5">
                <BarChart2 className="w-4 h-4 text-apex-accent"/> AI Performance Summary
              </div>
              {discoveryAnalytics ? (
                <div className="space-y-2 text-[10px]">
                  <div className="p-2.5 bg-apex-bg rounded border border-apex-border space-y-1">
                    <div className="flex justify-between">
                      <span className="text-apex-muted">Win Rate:</span>
                      <strong className="text-emerald-400">{discoveryAnalytics.win_rate_pct}%</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-apex-muted">Profit Factor:</span>
                      <strong className="text-apex-accent">{discoveryAnalytics.profit_factor}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-apex-muted">Expectancy (R/trade):</span>
                      <strong className="text-apex-text">+{discoveryAnalytics.expectancy_r}R</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-apex-muted">Total Realized R:</span>
                      <strong className="text-cyan-400">{discoveryAnalytics.total_r_realized}R</strong>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-10 text-apex-muted">Loading Analytics...</div>
              )}
            </div>
          )}
        </div>

        {/* CENTER PANEL: Chart & Detailed Factor Diagnostics */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {viewMode === 'ANALYTICS' && discoveryAnalytics ? (
            /* FULL PERFORMANCE ANALYTICS VIEW */
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#0d0d10]">
              <div className="flex items-center justify-between border-b border-apex-border/60 pb-3">
                <div>
                  <h2 className="text-base font-bold text-apex-text flex items-center gap-2">
                    <BarChart2 className="w-5 h-5 text-apex-accent"/> Autonomous AI Signal Performance Analytics
                  </h2>
                  <p className="text-[10px] text-apex-muted">
                    Evaluated historically & forward-tracked with zero lookahead bias.
                  </p>
                </div>
                <div className="text-[10px] px-3 py-1 rounded bg-apex-surface border border-apex-border text-apex-accent font-bold">
                  Total Signals Logged: {discoveryAnalytics.total_signals_recorded}
                </div>
              </div>

              {/* Top Stats Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-apex-bg rounded-lg border border-apex-border">
                  <div className="text-[9px] text-apex-muted uppercase font-bold">Win Rate</div>
                  <div className="text-xl font-extrabold text-emerald-400 mt-1 font-mono">{discoveryAnalytics.win_rate_pct}%</div>
                  <div className="text-[8px] text-apex-muted mt-0.5">TP1 Hit: {discoveryAnalytics.tp1_hit_rate_pct}%</div>
                </div>
                <div className="p-3 bg-apex-bg rounded-lg border border-apex-border">
                  <div className="text-[9px] text-apex-muted uppercase font-bold">Profit Factor</div>
                  <div className="text-xl font-extrabold text-apex-accent mt-1 font-mono">{discoveryAnalytics.profit_factor}</div>
                  <div className="text-[8px] text-apex-muted mt-0.5">SL Hit Rate: {discoveryAnalytics.sl_rate_pct}%</div>
                </div>
                <div className="p-3 bg-apex-bg rounded-lg border border-apex-border">
                  <div className="text-[9px] text-apex-muted uppercase font-bold">Expectancy</div>
                  <div className="text-xl font-extrabold text-cyan-400 mt-1 font-mono">+{discoveryAnalytics.expectancy_r} R</div>
                  <div className="text-[8px] text-apex-muted mt-0.5">Avg per trade</div>
                </div>
                <div className="p-3 bg-apex-bg rounded-lg border border-apex-border">
                  <div className="text-[9px] text-apex-muted uppercase font-bold">Avg MFE vs MAE</div>
                  <div className="text-xl font-extrabold text-apex-text mt-1 font-mono">
                    +{discoveryAnalytics.avg_mfe_r}R / -{discoveryAnalytics.avg_mae_r}R
                  </div>
                  <div className="text-[8px] text-apex-muted mt-0.5">Favorable vs Adverse</div>
                </div>
              </div>

              {/* Confidence Bucket Correlation Table */}
              <div className="p-3.5 bg-apex-surface/40 rounded-lg border border-apex-border space-y-2.5">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-apex-text uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400"/> Confidence Bucket Correlation Matrix
                  </h3>
                  <span className="text-[9px] text-apex-muted">Proves whether confidence actually correlates with real outcome</span>
                </div>
                <table className="w-full text-left border-collapse text-[10px]">
                  <thead>
                    <tr className="border-b border-apex-border text-apex-muted font-bold">
                      <th className="py-1.5">Confidence Bucket</th>
                      <th className="py-1.5">Total Signals</th>
                      <th className="py-1.5">Win Rate (%)</th>
                      <th className="py-1.5">Expectancy (R)</th>
                      <th className="py-1.5">Statistical Validity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(discoveryAnalytics.confidence_bucket_breakdown || {}).map(([b, v]: [string, any]) => (
                      <tr key={b} className="border-b border-apex-border/30 hover:bg-apex-surface/50">
                        <td className="py-1.5 font-bold text-apex-text font-mono">{b}%</td>
                        <td className="py-1.5 text-apex-muted font-mono">{v.total_trades}</td>
                        <td className={`py-1.5 font-bold font-mono ${v.win_rate_pct >= 50 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {v.win_rate_pct}%
                        </td>
                        <td className="py-1.5 font-bold text-cyan-400 font-mono">+{v.expectancy_r} R</td>
                        <td className="py-1.5 text-apex-muted">
                          {v.total_trades >= 10 ? '✓ Statistically Grounded' : 'Sample Size Gathering'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <>
              {/* Candlestick Chart */}
              <div className="h-[480px] shrink-0 border-b border-apex-border">
                <ApexCandleChart
                  symbol={selected ? selected.symbol : selectedSymbol}
                  signal={chartSignal as any}
                />
              </div>

              {/* Detailed Factor Diagnostics for Selected Symbol */}
              <div className="flex-1 overflow-y-auto p-3.5 space-y-3 bg-[#0d0d10]">
                {activeDiscoveryCard ? (
                  <>
                    {/* Header bar of selected symbol */}
                    <div className="flex items-center justify-between p-2.5 bg-apex-bg rounded-lg border border-apex-border">
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold text-sm text-apex-text">{activeDiscoveryCard.symbol}</span>
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold flex items-center gap-1 ${
                          activeDiscoveryCard.decision === 'LONG'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : activeDiscoveryCard.decision === 'SHORT'
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                        }`}>
                          <SIcon side={activeDiscoveryCard.decision}/>
                          {activeDiscoveryCard.decision}
                        </span>
                        <span className="text-[10px] text-apex-muted">
                          Regime: <strong className="text-apex-text">{activeDiscoveryCard.regime}</strong> ({activeDiscoveryCard.regime_confidence}%)
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[9px] text-apex-muted font-mono">
                        <span>Quality: <strong className="text-apex-accent">{activeDiscoveryCard.setup_quality}%</strong></span>
                        <span>Confidence: <strong className="text-apex-ai">{activeDiscoveryCard.confidence}%</strong></span>
                        <span>Latency: <strong>{activeDiscoveryCard.gemini_latency_ms}ms</strong></span>
                      </div>
                    </div>

                    {/* Multi-Timeframe Hierarchy */}
                    <div className="p-3 bg-apex-surface/40 rounded-lg border border-apex-border space-y-2">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-apex-muted flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-apex-accent"/> Multi-Timeframe Hierarchy (H4 ➔ H1 ➔ M15 ➔ M5 ➔ M1)
                      </div>
                      <div className="grid grid-cols-5 gap-2 text-[9px]">
                        {['H4', 'H1', 'M15', 'M5', 'M1'].map(tf => {
                          const desc = activeDiscoveryCard.timeframe_analysis?.[tf] || 'Analysis complete';
                          const isBull = desc.toLowerCase().includes('bull');
                          const isBear = desc.toLowerCase().includes('bear');
                          return (
                            <div key={tf} className="p-2 bg-apex-bg rounded border border-apex-border/60 space-y-1">
                              <div className="font-bold flex justify-between items-center">
                                <span>{tf}</span>
                                <span className={`text-[8px] px-1 rounded ${
                                  isBull ? 'text-emerald-400 bg-emerald-500/15' : isBear ? 'text-rose-400 bg-rose-500/15' : 'text-apex-muted'
                                }`}>
                                  {isBull ? 'BULL' : isBear ? 'BEAR' : 'NEUT'}
                                </span>
                              </div>
                              <p className="text-[8px] text-apex-muted line-clamp-3 leading-tight">{desc}</p>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Factors: Bullish, Bearish, Conflicts */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-[9px]">
                      {/* Bullish */}
                      <div className="p-2.5 bg-emerald-500/5 rounded-lg border border-emerald-500/20 space-y-1.5">
                        <div className="font-bold text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3"/> Bullish Factors ({activeDiscoveryCard.bullish_factors?.length || 0})
                        </div>
                        <ul className="space-y-1 text-apex-textSecondary">
                          {activeDiscoveryCard.bullish_factors?.map((f: string, i: number) => (
                            <li key={i} className="flex items-start gap-1">
                              <span className="text-emerald-400 font-bold">•</span>
                              <span>{f}</span>
                            </li>
                          ))}
                          {(!activeDiscoveryCard.bullish_factors || activeDiscoveryCard.bullish_factors.length === 0) && (
                            <li className="text-apex-muted italic">None recorded</li>
                          )}
                        </ul>
                      </div>

                      {/* Bearish */}
                      <div className="p-2.5 bg-rose-500/5 rounded-lg border border-rose-500/20 space-y-1.5">
                        <div className="font-bold text-rose-400 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3"/> Bearish Factors ({activeDiscoveryCard.bearish_factors?.length || 0})
                        </div>
                        <ul className="space-y-1 text-apex-textSecondary">
                          {activeDiscoveryCard.bearish_factors?.map((f: string, i: number) => (
                            <li key={i} className="flex items-start gap-1">
                              <span className="text-rose-400 font-bold">•</span>
                              <span>{f}</span>
                            </li>
                          ))}
                          {(!activeDiscoveryCard.bearish_factors || activeDiscoveryCard.bearish_factors.length === 0) && (
                            <li className="text-apex-muted italic">None recorded</li>
                          )}
                        </ul>
                      </div>

                      {/* Conflicts & Invalidation */}
                      <div className="p-2.5 bg-amber-500/5 rounded-lg border border-amber-500/20 space-y-1.5">
                        <div className="font-bold text-amber-300 flex items-center gap-1">
                          <Crosshair className="w-3 h-3"/> Conflicts & Invalidation
                        </div>
                        <div className="text-apex-textSecondary space-y-1">
                          <div>
                            <strong className="text-apex-muted">Invalidation:</strong> {activeDiscoveryCard.invalidation || 'N/A'}
                          </div>
                          <div>
                            <strong className="text-apex-muted">Confirmation:</strong> {activeDiscoveryCard.required_confirmation || 'N/A'}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Reasoning Quote Box */}
                    <div className="p-3 bg-apex-ai/5 rounded-lg border border-apex-ai/20 space-y-1">
                      <div className="text-[9px] font-bold text-apex-ai uppercase flex items-center gap-1">
                        <Sparkles className="w-3 h-3"/> Gemini Autonomous Strategic Assessment
                      </div>
                      <p className="text-[10px] text-apex-text leading-relaxed">
                        {activeDiscoveryCard.why_this_setup || 'Autonomous market scan complete. Market state monitored hourly.'}
                      </p>
                    </div>
                  </>
                ) : (
                  <div className="py-8 text-center text-apex-muted">Select an asset from the left panel</div>
                )}
              </div>
            </>
          )}
        </div>

        {/* RIGHT PANEL: Paper Trade Outcomes & History */}
        <div className="w-[300px] shrink-0 flex flex-col border-l border-apex-border overflow-hidden bg-apex-bgSecondary/20">
          <div className="px-3 py-1.5 border-b border-apex-border bg-apex-bgSecondary text-[9px] font-bold text-apex-muted uppercase tracking-widest flex justify-between items-center">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setHistoryTab('AI_PAPER')}
                className={`flex items-center gap-1 transition-colors ${
                  historyTab === 'AI_PAPER' ? 'text-apex-accent font-extrabold' : 'text-apex-muted hover:text-apex-text'
                }`}
              >
                <Cpu className="w-3 h-3"/> AI Paper Log
              </button>
              <span>|</span>
              <button
                onClick={() => setHistoryTab('LEGACY_HISTORY')}
                className={`flex items-center gap-1 transition-colors ${
                  historyTab === 'LEGACY_HISTORY' ? 'text-apex-accent font-extrabold' : 'text-apex-muted hover:text-apex-text'
                }`}
              >
                <History className="w-3 h-3"/> Execution Log
              </button>
            </div>
            <span className="font-mono text-apex-muted">
              {historyTab === 'AI_PAPER' ? discoveryHistory.length : hist.length} records
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {historyTab === 'AI_PAPER' ? (
              <>
                {discoveryHistory.map((h, idx) => {
                  if (!h) return null;
                  const isWin = (h.r_result || 0) > 0;
                  const isLong = h.direction === 'LONG';
                  return (
                    <div
                      key={h.id || idx}
                      className="p-2 bg-apex-bg hover:bg-apex-surface border border-apex-border/50 rounded transition-all text-[9px]"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-1">
                          <span className="font-bold text-apex-text">{h.symbol}</span>
                          <span className={`px-1 rounded text-[8px] font-bold ${
                            isLong ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'
                          }`}>
                            {h.direction}
                          </span>
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                          h.status === 'CLOSED_TP2' || h.status === 'CLOSED_TP1'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : h.status === 'CLOSED_SL'
                            ? 'bg-rose-500/20 text-rose-400'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {h.status}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-1 text-[8px] text-apex-muted font-mono mb-1">
                        <div>E: <strong className="text-apex-text">${fmt(h.entry_price)}</strong></div>
                        <div>SL: <strong className="text-rose-400">${fmt(h.stop_loss)}</strong></div>
                        <div>TP: <strong className="text-emerald-400">${fmt(h.take_profit_1)}</strong></div>
                      </div>

                      <div className="flex items-center justify-between text-[8px] border-t border-apex-border/30 pt-1 text-apex-muted">
                        <span>MFE: <strong className="text-emerald-400">+{h.mfe_r}R</strong></span>
                        <span>MAE: <strong className="text-rose-400">-{h.mae_r}R</strong></span>
                        <span>Res: <strong className={isWin ? 'text-emerald-400' : 'text-rose-400'}>
                          {h.r_result !== null ? `${h.r_result}R` : 'OPEN'}
                        </strong></span>
                      </div>
                    </div>
                  );
                })}
                {discoveryHistory.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-16 text-apex-muted gap-1.5">
                    <History className="w-6 h-6 opacity-25"/>
                    <p className="text-[10px] font-bold">No Paper Trades Yet</p>
                    <p className="text-[9px] text-center">Paper outcomes record automatically over time.</p>
                  </div>
                )}
              </>
            ) : (
              <>
                {hist.map((h, idx) => {
                  if (!h) return null;
                  const status = str(h.status, 'PENDING');
                  const score  = typeof h.aiScore === 'number' ? h.aiScore : (typeof h.quantScore === 'number' ? h.quantScore : 0);
                  const target = signalTargets(h)[0];
                  return (
                    <div key={h.id || idx} onClick={() => setSel(h)}
                      className="p-2 bg-apex-bg hover:bg-apex-surface border border-apex-border/50 hover:border-apex-accent/40 rounded cursor-pointer transition-all">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-1">
                          <span className="font-bold text-[11px] text-apex-text">{h.symbol || 'BTC/USDT'}</span>
                          <span className={`text-[8px] font-bold px-1 rounded ${h.side === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}`}>{h.side}</span>
                        </div>
                        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded ${inc(status, 'TP') ? 'bg-emerald-500/15 text-emerald-400' : inc(status, 'SL') ? 'bg-rose-500/15 text-rose-400' : 'bg-amber-500/15 text-amber-400'}`}>{status}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-1 text-[8px] text-apex-muted">
                        <div>E <span className="text-apex-text font-bold">${fmt(h.entry)}</span></div>
                        <div>SL <span className="text-rose-400 font-bold">${fmt(h.sl)}</span></div>
                        <div>{target?.label || 'TP'} <span className="text-emerald-400 font-bold">{target ? `$${fmt(target.value)}` : '—'}</span></div>
                      </div>
                      <div className="flex items-center justify-between mt-1 text-[8px] text-apex-muted">
                        <span>{typeof h.formatted_time === 'string' ? h.formatted_time : str(h.createdAt, '')}</span>
                        <span className="text-apex-ai font-bold">{score}%</span>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>

          <div className="p-2 border-t border-apex-border bg-apex-bgSecondary text-[8px] text-apex-muted flex justify-between">
            <span>Autonomous Risk Engine</span>
            <span className="text-emerald-400">● Paper Tracking Active</span>
          </div>
        </div>

      </div>
      )}
    </div>
  );
};

// ─── Exports ──────────────────────────────────────────────────────────────────
export const LiveSignals: React.FC = () => (
  <LiveSignalsErrorBoundary>
    <LiveSignalsContent/>
  </LiveSignalsErrorBoundary>
);

export default LiveSignals;
