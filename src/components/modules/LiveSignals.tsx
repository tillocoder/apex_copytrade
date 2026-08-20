import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import {
  Zap, Sparkles, TrendingUp, TrendingDown, Minus,
  Activity, RefreshCw, History, Info,
  ChevronRight, ZoomIn, ZoomOut, BarChart2
} from 'lucide-react';
import { ApexCandleChart } from '../common/ApexCandleChart';

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
const epochSeconds = (v: unknown) => {
  const value = num(v);
  return value > 10_000_000_000 ? value / 1000 : value;
};
const tradeExitTime = (signal: Signal | null) => {
  const status = str(signal?.status).toUpperCase();
  return /(^|_)(TP\d*|SL|STOP)(_|$)/.test(status) ? epochSeconds(signal?.exit_timestamp) : 0;
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

  // Legacy signals can contain one unnumbered `tp` value.
  if (raw.length === 0 && num(signal.tp) > 0) raw.push({ label: 'TP1', order: 1, value: num(signal.tp) });

  return raw.filter(level =>
    level.value > 0 &&
    (isBuy ? level.value > entry : level.value < entry)
  ).sort((a, b) => a.order - b.order).map(({ label, value }) => ({ label, value }));
};

// ─── Interactive Candlestick Chart ──────────────────────────────────────────
const TIMEFRAMES = [
  { label: '1m',  interval: '1m',  dur: 60    },
  { label: '3m',  interval: '3m',  dur: 180   },
  { label: '5m',  interval: '5m',  dur: 300   },
  { label: '15m', interval: '15m', dur: 900   },
  { label: '1h',  interval: '1h',  dur: 3600  },
  { label: '4h',  interval: '4h',  dur: 14400 },
  { label: '1D',  interval: '1d',  dur: 86400 },
];

interface ChartProps {
  symbol: string;
  signal: Signal | null;
}

const CandleChart: React.FC<ChartProps> = ({ symbol, signal }) => {
  const wrapRef    = React.useRef<HTMLDivElement>(null);
  const zoomRef    = React.useRef(1);            // ref for native wheel handler
  const offsetRef  = React.useRef(0);            // ref for native wheel handler
  const [W,  setW]  = React.useState(800);
  const [H,  setH]  = React.useState(320);
  const [zoom,      setZoom]      = React.useState(1);
  const [offsetX,   setOffsetX]   = React.useState(0);
  const [dragging,  setDragging]  = React.useState(false);
  const [dragX0,    setDragX0]    = React.useState(0);
  const [dragDelta, setDragDelta] = React.useState(0);
  const [tf,        setTf]        = React.useState(TIMEFRAMES[3]); // default 15m
  const [klines,    setKlines]    = React.useState<any[]>([]);
  const [loadingK,  setLoadingK]  = React.useState(false);
  const exitTime = tradeExitTime(signal);

  // Keep refs in sync for native wheel handler
  React.useEffect(() => { zoomRef.current   = zoom;    }, [zoom]);
  React.useEffect(() => { offsetRef.current = offsetX; }, [offsetX]);

  // Measure real container pixels + attach passive:false wheel listener
  React.useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    // ResizeObserver
    const ro = new ResizeObserver(ents => {
      for (const e of ents) {
        const { width, height } = e.contentRect;
        if (width > 20 && height > 20) { setW(Math.floor(width)); setH(Math.floor(height)); }
      }
    });
    ro.observe(el);
    // Native wheel — passive:false so preventDefault works
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const PL2 = 8, PR2 = 90;
      const cw2  = Math.max(1, el.getBoundingClientRect().width - PL2 - PR2);
      const rect = el.getBoundingClientRect();
      const mouseX = e.clientX - rect.left - PL2; // cursor pos relative to chart
      const curZoom    = zoomRef.current;
      const curOffset  = offsetRef.current;
      // calc candle index under cursor
      const nData = dataRef.current;
      const curStep = Math.max(4, (cw2 / Math.max(1, nData)) * curZoom);
      const priceIdxUnderCursor = (curOffset + mouseX) / curStep;
      // new zoom
      const delta    = e.deltaY > 0 ? -0.12 : 0.12;
      const newZoom  = Math.max(0.2, Math.min(12, curZoom * (1 + delta)));
      const newStep  = Math.max(4, (cw2 / Math.max(1, nData)) * newZoom);
      // keep the candle under cursor stationary
      const newOff   = Math.max(0, priceIdxUnderCursor * newStep - mouseX);
      const maxO2    = Math.max(0, nData * newStep - cw2);
      const finalOff = Math.min(newOff, maxO2);
      zoomRef.current   = newZoom;
      offsetRef.current = finalOff;
      setZoom(newZoom);
      setOffsetX(finalOff);
    };
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => { ro.disconnect(); el.removeEventListener('wheel', handleWheel); };
  }, []);

  // A completed signal loads the market window ending at its exit candle.
  // That prevents price action from continuing to the right of TP/SL.
  const dataRef = React.useRef(0); // store data length for wheel handler
  React.useEffect(() => {
    if (!symbol) return;
    setLoadingK(true);
    const endTime = exitTime ? `&end_time=${Math.round(exitTime * 1000)}` : '';
    fetch(`/api/v1/market/klines?symbol=${encodeURIComponent(symbol)}&interval=${tf.interval}&limit=200${endTime}`)
      .then(r => r.ok ? r.json() : null)
      .then(j => {
        if (j?.status === 'SUCCESS' && Array.isArray(j.data)) {
          const filtered = j.data.filter((k: any) => k && typeof k.high === 'number' && typeof k.low === 'number');
          setKlines(filtered);
        } else {
          setKlines([]);
        }
      })
      .catch(() => setKlines([]))
      .finally(() => setLoadingK(false));
  }, [symbol, tf, exitTime]);

  // When signal changes → reset zoom, scroll to latest (will be refined by klines effect)
  React.useEffect(() => { setZoom(1); setDragDelta(0); setOffsetX(999999); }, [signal?.id]);

  const data = React.useMemo(() => {
    const all = Array.isArray(klines) ? klines.filter(k => k && typeof k.high === 'number' && typeof k.low === 'number') : [];
    if (!exitTime) return all;
    const exitIndex = all.findIndex(k => exitTime >= num(k.timestamp) && exitTime < num(k.timestamp) + tf.dur);
    return exitIndex >= 0 ? all.slice(0, exitIndex + 1) : all;
  }, [klines, exitTime, tf.dur]);
  // Keep dataRef length in sync for native wheel handler
  React.useEffect(() => { dataRef.current = data.length; }, [data.length]);

  // Auto-center + auto-zoom on entry candle when klines/signal changes
  React.useEffect(() => {
    if (!signal || data.length === 0 || W <= 20) return;
    const ep2 = num(signal.entry);
    const entryTime = epochSeconds(signal.timestamp);

    // Find entry candle index
    let entryIdx = data.length - 1; // default: latest candle
    let found = false;
    data.forEach((k, i) => {
      if (!k.timestamp) return;
      if (entryTime && entryTime >= k.timestamp && entryTime < k.timestamp + tf.dur) {
        entryIdx = i; found = true;
      }
    });
    if (!found && ep2 > 0) {
      const cl = data.map((k, i) => ({ i, d: Math.abs(k.close - ep2) })).sort((a, b) => a.d - b.d);
      if (cl.length) entryIdx = cl[0].i;
    }

    // Zoom so ~55 candles are visible — entry is clearly sized
    const cw2   = Math.max(1, W - 8 - 90);
    const SHOW  = Math.min(data.length, 55); // candles to show
    const newZoom = Math.max(0.4, Math.min(8, data.length / SHOW));
    const newStep = Math.max(4, (cw2 / Math.max(1, data.length)) * newZoom);

    // Place entry at 30% from left (context behind it, TP zone ahead)
    const entryPx = entryIdx * newStep;
    const target  = Math.max(0, entryPx - cw2 * 0.30);
    const maxO    = Math.max(0, data.length * newStep - cw2);

    setZoom(newZoom);
    setOffsetX(Math.min(target, maxO));
    setDragDelta(0);
  }, [data, signal?.id, tf.dur, W]);

  const PL = 8, PR = 90, PT = 14, PB = 28;
  const cW = Math.max(1, W - PL - PR);
  const cH = Math.max(1, H - PT - PB);
  const n   = data.length;
  const step = Math.max(4, (cW / Math.max(1, n)) * zoom);
  const cndW = Math.max(1.5, step * 0.68);
  const maxOff = Math.max(0, n * step - cW);
  const off    = Math.max(0, Math.min(offsetX + dragDelta, maxOff));

  const fi = Math.max(0, Math.floor(off / step));
  const li = Math.min(n - 1, Math.ceil((off + cW) / step) + 1);
  const vis = data.slice(fi, li + 1);

  const ep = num(signal?.entry);
  const sp = num(signal?.sl);
  const targets = signalTargets(signal);
  const isBuy = signal?.side === 'BUY';
  const hasStop = ep > 0 && sp > 0 && (isBuy ? sp < ep : sp > ep);
  const lastClose = num(data[data.length - 1]?.close);

  const prices: number[] = [
    ...vis.map(k => k.high).filter(isFinite),
    ...vis.map(k => k.low).filter(isFinite),
  ];
  if (ep > 0) prices.push(ep);
  if (hasStop) prices.push(sp);
  targets.forEach(target => prices.push(target.value));

  let hi = prices.length ? Math.max(...prices) : 100;
  let lo = prices.length ? Math.min(...prices) : 90;
  const rng = hi - lo || 1;
  hi += rng * 0.14;
  lo -= rng * 0.08;
  const PR2 = hi - lo || 1;

  const gx = (ai: number) => PL + (ai - fi) * step + step / 2 - (off % step);
  const gy = (p: number)  => PT + cH - ((p - lo) / PR2) * cH;

  // Detect entry/exit candles
  const entryIdxs: number[] = [];
  if (signal && n > 0) {
    data.forEach((k, i) => {
      const ts = k.timestamp;
      if (!ts) return;
      const entryTime = epochSeconds(signal.timestamp);
      if (entryTime && entryTime >= ts && entryTime < ts + tf.dur) entryIdxs.push(i);
    });
    if (entryIdxs.length === 0 && ep > 0) {
      const cl = data.map((k, i) => ({ i, d: Math.abs(k.close - ep) })).sort((a, b) => a.d - b.d);
      if (cl.length) entryIdxs.push(cl[0].i);
    }
  }

  const onMD = (e: React.MouseEvent) => { setDragging(true); setDragX0(e.clientX); setDragDelta(0); };
  const onMM = (e: React.MouseEvent) => { if (dragging) setDragDelta(-(e.clientX - dragX0)); };
  const onMU = () => {
    if (dragging) {
      setOffsetX(p => {
        const finalOff = Math.max(0, Math.min(p + dragDelta, maxOff));
        offsetRef.current = finalOff;
        return finalOff;
      });
      setDragDelta(0);
    }
    setDragging(false);
  };

  const GRID = 6;
  const entryIndex = entryIdxs[0] ?? Math.max(fi, Math.min(li, n - 1));
  const positionX = Math.max(PL, Math.min(W - PR, gx(entryIndex)));
  const plotRight = W - PR;
  const positionEndX = exitTime
    ? Math.max(positionX, Math.min(plotRight, gx(Math.max(0, n - 1)) + cndW / 2))
    : plotRight;
  const finalTarget = targets[targets.length - 1];

  return (
    <div className="w-full h-full flex flex-col">
      {/* Timeframe Selector + Controls */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#12121a] border-b border-[#27272a] shrink-0 gap-2">
        <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold overflow-hidden flex-wrap">
          <span className="text-apex-accent">{signal?.symbol || symbol || '—'}</span>
          <span className="text-[#3f3f46]">·</span>
          {/* Timeframe buttons */}
          {TIMEFRAMES.map(t => (
            <button key={t.label} onClick={() => setTf(t)}
              className={`px-1.5 py-0.5 rounded text-[9px] font-bold transition-colors ${
                tf.label === t.label
                  ? 'bg-apex-accent/20 text-apex-accent border border-apex-accent/40'
                  : 'text-[#52525b] hover:text-white border border-transparent hover:border-[#27272a]'
              }`}>
              {t.label}
            </button>
          ))}
          <span className="text-[#3f3f46]">·</span>
          <span className="text-[#52525b]">BINANCE</span>
          {ep > 0 && (
            <>
              <span className="text-[#3f3f46]">·</span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${signal?.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>
                {signal?.side}
              </span>
              <span className="text-[#71717a]">E:<span className="text-white">${fmt(ep)}</span></span>
              {hasStop && <span className="text-rose-400">SL:${fmt(sp)}</span>}
              {targets.map(target => <span key={target.label} className="text-emerald-400">{target.label}:${fmt(target.value)}</span>)}
              <span className="text-cyan-400 font-bold">R:R 1:{fmtRR(signal?.rr)}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => setZoom(z => Math.min(12, z * 1.3))} className="p-1 text-[#52525b] hover:text-white hover:bg-[#27272a] rounded transition-colors"><ZoomIn className="w-3.5 h-3.5" /></button>
          <button onClick={() => setZoom(z => Math.max(0.2, z / 1.3))} className="p-1 text-[#52525b] hover:text-white hover:bg-[#27272a] rounded transition-colors"><ZoomOut className="w-3.5 h-3.5" /></button>
          <button onClick={() => {
            setZoom(1); setDragDelta(0);
            if (entryIdxs.length > 0) {
              const entryX = entryIdxs[0] * Math.max(4, cW / Math.max(1, n));
              const target = Math.max(0, entryX - cW * 0.38);
              setOffsetX(Math.min(target, maxOff));
            } else { setOffsetX(maxOff); }
          }} className="px-2 py-0.5 text-[9px] text-[#71717a] hover:text-white border border-[#27272a] hover:border-[#52525b] rounded font-mono font-bold transition-colors">ENTRY</button>
          <button onClick={() => { setOffsetX(maxOff); setDragDelta(0); }} className="px-2 py-0.5 text-[9px] text-apex-accent border border-apex-accent/30 hover:bg-apex-accent/10 rounded font-mono font-bold transition-colors">LATEST</button>
          <span className="hidden lg:inline text-[8px] text-[#3f3f46] border-l border-[#27272a] pl-2 ml-1 font-mono">Drag·Scroll=Zoom</span>
        </div>
      </div>

      {/* Chart canvas */}
      <div
        ref={wrapRef}
        className={`flex-1 bg-[#0b0b0f] overflow-hidden ${dragging ? 'cursor-grabbing' : 'cursor-crosshair'}`}
        onMouseDown={onMD} onMouseMove={onMM} onMouseUp={onMU} onMouseLeave={onMU}
        style={{ touchAction: 'none', userSelect: 'none' }}
      >
        {loadingK ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <Activity className="w-6 h-6 animate-spin text-apex-accent" />
            <span className="text-[10px] text-[#52525b] uppercase tracking-widest">Fetching OHLCV...</span>
          </div>
        ) : data.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <BarChart2 className="w-8 h-8 text-[#3f3f46]" />
            <span className="text-[10px] text-[#52525b] uppercase tracking-widest">No Market Data</span>
            <span className="text-[9px] text-[#3f3f46]">Verify Binance server connection</span>
          </div>
        ) : (
          /* SVG uses REAL pixel width/height — no stretching */
          <svg width={W} height={H} style={{ display: 'block' }}>
            <defs>
              <linearGradient id="zTP" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.15"/>
                <stop offset="100%" stopColor="#10b981" stopOpacity="0.02"/>
              </linearGradient>
              <linearGradient id="zSL" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.02"/>
                <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.15"/>
              </linearGradient>
              <filter id="gG"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
              <filter id="gR"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
            </defs>

            {/* Horizontal price grid */}
            {Array.from({ length: GRID }, (_, i) => {
              const p = lo + (i / (GRID - 1)) * PR2;
              const y = gy(p);
              return (
                <g key={i}>
                  <line x1={PL} y1={y} x2={W - PR} y2={y} stroke="#1a1a1f" strokeWidth={0.7}/>
                  <text x={W - PR + 4} y={y + 3.5} fill="#52525b" fontSize={8} fontFamily="monospace">${fmt(p)}</text>
                </g>
              );
            })}

            {/* Vertical time ticks */}
            {vis.filter((_, i) => i % Math.max(1, Math.floor(vis.length / 7)) === 0).map((k, i) => {
              const ai = fi + i * Math.max(1, Math.floor(vis.length / 7));
              const x  = gx(ai);
              const lbl = k.timestamp ? new Date(k.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
              return (
                <g key={i}>
                  <line x1={x} y1={PT} x2={x} y2={H - PB} stroke="#16161b" strokeWidth={0.6}/>
                  <text x={x} y={H - PB + 11} fill="#3f3f46" fontSize={7.5} fontFamily="monospace" textAnchor="middle">{lbl}</text>
                </g>
              );
            })}

            {/* Axis borders */}
            <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="#27272a" strokeWidth={0.8}/>
            <line x1={W - PR} y1={PT} x2={W - PR} y2={H - PB} stroke="#27272a" strokeWidth={0.8}/>

            {/* TradingView-style position tool: zones start at entry, not across the entire chart. */}
            {signal && ep > 0 && (
              <g>
                {finalTarget && (
                  <rect
                    x={positionX} y={Math.min(gy(ep), gy(finalTarget.value))}
                    width={Math.max(1, positionEndX - positionX)} height={Math.abs(gy(ep) - gy(finalTarget.value))}
                    fill="url(#zTP)"
                  />
                )}
                {hasStop && (
                  <rect
                    x={positionX} y={Math.min(gy(ep), gy(sp))}
                    width={Math.max(1, positionEndX - positionX)} height={Math.abs(gy(ep) - gy(sp))}
                    fill="url(#zSL)"
                  />
                )}
                <rect x={positionX + 5} y={PT + 5} width={isBuy ? 92 : 98} height={17} rx={3} fill="#111827" stroke={isBuy ? "#10b981" : "#f43f5e"} strokeOpacity={0.55}/>
                <text x={positionX + 10} y={PT + 16} fill={isBuy ? "#6ee7b7" : "#fda4af"} fontSize={8} fontWeight="bold" fontFamily="monospace">
                  {isBuy ? 'LONG POSITION' : 'SHORT POSITION'}
                </text>
              </g>
            )}

            {/* Candles — proportional body/wick */}
            {vis.map((k, ri) => {
              const ai = fi + ri;
              const x  = gx(ai);
              if (x < PL - cndW * 2 || x > W - PR + cndW * 2) return null;
              const up    = k.close >= k.open;
              const col   = up ? '#10b981' : '#ef4444';
              const bTop  = Math.min(gy(k.open), gy(k.close));
              const bH    = Math.max(1.5, Math.abs(gy(k.open) - gy(k.close)));
              return (
                <g key={ai}>
                  <line x1={x} y1={gy(k.high)} x2={x} y2={gy(k.low)} stroke={col} strokeWidth={Math.max(0.8, cndW * 0.1)}/>
                  <rect x={x - cndW / 2} y={bTop} width={cndW} height={bH} fill={col} rx={cndW > 6 ? 1 : 0}/>
                </g>
              );
            })}

            {/* Clean level lines and price-scale tags, matching TradingView's order tool. */}
            {signal && ep > 0 && (
              <g>
                <line x1={PL} y1={gy(ep)} x2={plotRight} y2={gy(ep)} stroke="#cbd5e1" strokeDasharray="5 4" strokeWidth={1}/>
                <rect x={plotRight + 2} y={gy(ep) - 8} width={86} height={16} rx={2} fill="#1e293b" stroke="#64748b" strokeWidth={0.8}/>
                <text x={plotRight + 6} y={gy(ep) + 3.5} fill="#f8fafc" fontSize={8} fontWeight="bold" fontFamily="monospace">ENTRY {fmt(ep)}</text>

                {hasStop && (
                  <g>
                    <line x1={PL} y1={gy(sp)} x2={plotRight} y2={gy(sp)} stroke="#fb7185" strokeDasharray="4 3" strokeWidth={1}/>
                    <rect x={plotRight + 2} y={gy(sp) - 8} width={86} height={16} rx={2} fill="#4c0519" stroke="#fb7185" strokeWidth={0.8}/>
                    <text x={plotRight + 6} y={gy(sp) + 3.5} fill="#fecdd3" fontSize={8} fontWeight="bold" fontFamily="monospace">STOP {fmt(sp)}</text>
                  </g>
                )}

                {targets.map(target => (
                  <g key={target.label}>
                    <line x1={PL} y1={gy(target.value)} x2={plotRight} y2={gy(target.value)} stroke="#34d399" strokeDasharray="4 3" strokeWidth={1}/>
                    <rect x={plotRight + 2} y={gy(target.value) - 8} width={86} height={16} rx={2} fill="#064e3b" stroke="#34d399" strokeWidth={0.8}/>
                    <text x={plotRight + 6} y={gy(target.value) + 3.5} fill="#d1fae5" fontSize={8} fontWeight="bold" fontFamily="monospace">{target.label} {fmt(target.value)}</text>
                  </g>
                ))}

                {lastClose > 0 && (
                  <g opacity={0.9}>
                    <line x1={PL} y1={gy(lastClose)} x2={plotRight} y2={gy(lastClose)} stroke="#38bdf8" strokeDasharray="2 3" strokeWidth={0.8}/>
                    <rect x={plotRight + 2} y={gy(lastClose) - 8} width={86} height={16} rx={2} fill="#082f49" stroke="#38bdf8" strokeWidth={0.7}/>
                    <text x={plotRight + 6} y={gy(lastClose) + 3.5} fill="#bae6fd" fontSize={8} fontWeight="bold" fontFamily="monospace">LAST {fmt(lastClose)}</text>
                  </g>
                )}
              </g>
            )}
          </svg>
        )}
      </div>
    </div>
  );
};

import { SignalsService } from '../../services/signalsService';

// ─── Main Content ─────────────────────────────────────────────────────────────
const LiveSignalsContent: React.FC = () => {
  const { signals: initSigs, setSignals: setGlobalSignals } = useTerminal();
  const [signals,      setSig]     = React.useState<Signal[]>(() => Array.isArray(initSigs) ? (initSigs as Signal[]) : []);
  const [history,      setHist]    = React.useState<Signal[]>([]);
  const [loading,      setLoad]    = React.useState(false);
  const [loadingHist,  setLoadH]   = React.useState(false);
  const [lastUpdate,   setLU]      = React.useState<Date | null>(null);
  const [selected,     setSel]     = React.useState<Signal | null>(null);
  const [klines,       setKl]      = React.useState<any[]>([]);
  const [loadingKlines,setLoadKl]  = React.useState(false);

  const fetchSignals = async () => {
    setLoad(true);
    try {
      const d = await SignalsService.fetchLiveSignals();
      if (Array.isArray(d)) {
        setSig(d.filter(Boolean));
        if (setGlobalSignals) setGlobalSignals(d.filter(Boolean));
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

  const fetchKlines = async (sym: string) => {
    if (!sym) return;
    setLoadKl(true);
    try {
      const d = await SignalsService.fetchMarketKlines(sym, '15m', 200);
      if (Array.isArray(d)) {
        setKl(d.filter((k: any) => k && typeof k.high === 'number' && typeof k.low === 'number'));
      }
    } catch (e) {
      console.warn('[LiveSignals] klines fetch error:', e);
    } finally {
      setLoadKl(false);
    }
  };

  React.useEffect(() => {
    fetchSignals();
    fetchHistory();
    const iv = setInterval(() => {
      fetchSignals();
      fetchHistory();
    }, 15000);
    return () => clearInterval(iv);
  }, []);

  React.useEffect(() => {
    if (selected?.symbol) fetchKlines(selected.symbol);
    else setKl([]);
  }, [selected]);

  const SIcon = ({ side }: { side?: string }) => {
    if (side === 'BUY')  return <TrendingUp  className="w-3.5 h-3.5"/>;
    if (side === 'SELL') return <TrendingDown className="w-3.5 h-3.5"/>;
    return <Minus className="w-3.5 h-3.5"/>;
  };

  // The API is expected to send active signals only; keep this guard so a
  // completed/expired signal can never remain in the Active Signals panel.
  const sigs = Array.isArray(signals)
    ? signals.filter(signal => signal && (signal.status === 'PENDING' || signal.status === 'CONFIRMED'))
    : [];
  const hist = Array.isArray(history) ? history.filter(Boolean) : [];
  const selectedTargets = signalTargets(selected);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs">

      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-apex-border shrink-0 bg-apex-bgSecondary">
        <div className="flex items-center gap-2 font-bold text-sm text-apex-text">
          <Zap className="w-4 h-4 text-apex-accent animate-pulse"/>
          <span>APEX AI SIGNAL CENTER</span>
          <span className="text-[10px] text-apex-muted font-normal">— 2-Hour Autonomous Cycle</span>
        </div>
        <div className="flex items-center gap-3">
          {(loading || loadingHist) && (
            <div className="flex items-center gap-1 text-apex-muted text-[10px] animate-pulse">
              <Activity className="w-3 h-3 animate-spin"/> Syncing...
            </div>
          )}
          {lastUpdate && <div className="text-[9px] text-apex-muted">Updated: {lastUpdate.toLocaleTimeString()}</div>}
          <button onClick={() => { fetchSignals(); fetchHistory(); }}
            className="flex items-center gap-1 px-2.5 py-1 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border rounded text-apex-text text-[10px] transition-colors">
            <RefreshCw className="w-3 h-3"/> Refresh
          </button>
          <div className="text-[10px] text-apex-ai font-bold flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-apex-ai"/> GEMINI 2.5 FLASH
          </div>
        </div>
      </div>

      {/* 3-Panel Layout */}
      <div className="flex-1 flex overflow-hidden">

        {/* LEFT: Signal Cards */}
        <div className="w-[320px] shrink-0 flex flex-col border-r border-apex-border overflow-hidden">
          <div className="px-3 py-1.5 border-b border-apex-border bg-apex-bgSecondary text-[9px] font-bold text-apex-muted uppercase tracking-widest flex justify-between">
            <span>Active Signals</span>
            <span className="text-apex-accent">{sigs.length} Live</span>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {sigs.map(s => {
              if (!s) return null;
              const buy  = s.side === 'BUY';
              const sel  = selected?.id === s.id;
              const targets = signalTargets(s);
              return (
                <div key={s.id || Math.random()} onClick={() => setSel(s)}
                  className={`p-3 rounded border cursor-pointer transition-all group ${sel
                    ? 'border-apex-accent bg-apex-accent/5'
                    : 'border-apex-border hover:border-apex-accent/40 bg-apex-surface/30 hover:bg-apex-surface/50'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-[13px] text-apex-text">{s.symbol || 'BTC/USDT'}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold flex items-center gap-0.5 ${buy ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25' : 'bg-rose-500/15 text-rose-400 border border-rose-500/25'}`}>
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
                        <div key={target.label} className="font-bold text-emerald-400 leading-tight">{target.label} ${fmt(target.value)}</div>
                      )) : <div className="font-bold text-apex-muted">—</div>}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[9px]">
                    <span className="text-apex-muted">R:R <span className="text-apex-accent font-bold">1:{fmtRR(s.rr)}</span></span>
                    <span className="text-apex-muted">AI <span className="text-apex-ai font-bold">{s.aiScore || s.confidence || '—'}%</span></span>
                    <span className="text-apex-accent font-bold flex items-center gap-0.5 group-hover:gap-1 transition-all">Chart <ChevronRight className="w-3 h-3"/></span>
                  </div>
                </div>
              );
            })}
            {sigs.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center py-16 text-apex-muted gap-2">
                <Activity className="w-7 h-7 animate-pulse text-apex-ai"/>
                <p className="text-[11px] font-bold">No Active Signals</p>
                <p className="text-[10px] text-center max-w-[180px]">Gemini AI scans every 2h. Check back soon.</p>
              </div>
            )}
          </div>
        </div>

        {/* CENTER: Chart */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {selected ? (
            <>
              {/* Chart takes the top portion — fixed height for proper proportions */}
              <div className="h-[380px] shrink-0 border-b border-apex-border">
                <ApexCandleChart symbol={selected.symbol} signal={selected as any}/>
              </div>
              {/* Details below */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-[#0d0d10]">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { l: 'ENTRY',       v: `$${fmt(selected.entry)}`, c: 'text-apex-text' },
                    { l: 'STOP LOSS',   v: `$${fmt(selected.sl)}`,    c: 'text-rose-400' },
                    ...selectedTargets.map(target => ({ l: target.label, v: `$${fmt(target.value)}`, c: 'text-emerald-400' })),
                    { l: 'R:R RATIO',   v: `1 : ${fmtRR(selected.rr)}`, c: 'text-cyan-400' },
                  ].map((item, i) => (
                    <div key={i} className="p-2.5 bg-apex-bg rounded border border-apex-border">
                      <div className="text-[8px] text-apex-muted uppercase">{item.l}</div>
                      <div className={`font-bold text-[13px] mt-0.5 ${item.c}`}>{item.v}</div>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 bg-apex-ai/5 border border-apex-ai/15 rounded space-y-1.5">
                    <div className="text-[9px] text-apex-ai font-bold uppercase flex items-center gap-1"><Sparkles className="w-3 h-3"/> AI Analysis</div>
                    <p className="text-[10px] text-apex-textSecondary leading-relaxed">{selected.reasoning || selected.aiNotes || 'Quant Engine Confluence Order Block Setup detected.'}</p>
                  </div>
                  {selected.indicators && (
                    <div className="p-3 bg-apex-bg border border-apex-border rounded space-y-1.5">
                      <div className="text-[9px] text-apex-muted font-bold uppercase flex items-center gap-1"><Info className="w-3 h-3"/> Indicators</div>
                      <div className="grid grid-cols-2 gap-1.5 text-[9.5px]">
                        <div>RSI 14: <span className="font-bold text-apex-text">{selected.indicators.rsi != null ? Number(selected.indicators.rsi).toFixed(1) : 'N/A'}</span></div>
                        <div>ATR: <span className="font-bold text-apex-text">${selected.indicators.atr != null ? Number(selected.indicators.atr).toFixed(2) : 'N/A'}</span></div>
                        <div>Vol Δ: <span className="font-bold text-apex-text">{selected.indicators.volumeDelta != null ? Number(selected.indicators.volumeDelta).toFixed(1) : '0.0'}%</span></div>
                        <div>Trend: <span className={`font-bold ${inc(selected.indicators.trend, 'BULLISH') ? 'text-emerald-400' : 'text-rose-400'}`}>{str(selected.indicators.trend, 'NEUTRAL')}</span></div>
                      </div>
                    </div>
                  )}
                </div>
                {selected.verification && Array.isArray(selected.verification) && (
                  <div className="p-3 bg-apex-bg border border-apex-border rounded">
                    <div className="text-[9px] text-apex-muted font-bold uppercase mb-2 flex justify-between">
                      <span>Verification Factors</span>
                      <span className="text-apex-ai">{selected.passedFactors || selected.verification.filter(v => v.passed).length}/{selected.totalFactors || selected.verification.length} Passed</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      {selected.verification.map((v, i) => (
                        <div key={i} className="flex items-center justify-between text-[9px] border-b border-apex-border/20 pb-1">
                          <span className="text-apex-muted">{v?.label || `Factor ${i + 1}`}</span>
                          <span className={`font-bold ${v?.passed ? 'text-emerald-400' : 'text-rose-400'}`}>{v?.passed ? '✓ PASS' : '✕ FAIL'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center bg-[#0d0d10] gap-3 text-apex-muted">
              <BarChart2 className="w-14 h-14 opacity-10"/>
              <p className="text-sm font-bold opacity-30">Select a Signal to View Chart</p>
              <p className="text-[10px] opacity-20">Click any signal card on the left</p>
            </div>
          )}
        </div>

        {/* RIGHT: History */}
        <div className="w-[260px] shrink-0 flex flex-col border-l border-apex-border overflow-hidden">
          <div className="px-3 py-1.5 border-b border-apex-border bg-apex-bgSecondary text-[9px] font-bold text-apex-muted uppercase tracking-widest flex justify-between">
            <span className="flex items-center gap-1"><History className="w-3 h-3 text-apex-accent"/> Signal History</span>
            <span>{hist.length} records</span>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
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
            {hist.length === 0 && !loadingHist && (
              <div className="flex flex-col items-center justify-center py-16 text-apex-muted gap-1.5">
                <History className="w-6 h-6 opacity-25"/>
                <p className="text-[10px] font-bold">No History</p>
                <p className="text-[9px] text-center">Records appear after first signal cycle.</p>
              </div>
            )}
          </div>
          <div className="p-2 border-t border-apex-border bg-apex-bgSecondary text-[8px] text-apex-muted flex justify-between">
            <span>60-day retention</span>
            <span className="text-emerald-400">● Auto-purge active</span>
          </div>
        </div>

      </div>
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
