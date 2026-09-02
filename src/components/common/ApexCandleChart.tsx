import React from 'react';
import type { Position, Signal } from '../../types';
import { subscribeBinanceLivePrices } from '../../services/marketDataService';
import { 
  ZoomIn, 
  ZoomOut, 
  Activity, 
  BarChart2, 
  Maximize2, 
  Move, 
  Crosshair,
  RotateCcw,
  Sparkles
} from 'lucide-react';

// â”€â”€â”€ Types & Timeframes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export interface TimeframeOption {
  label: string;
  interval: string;
  dur: number;
}

export const TIMEFRAMES: TimeframeOption[] = [
  { label: '1m',  interval: '1m',  dur: 60    },
  { label: '3m',  interval: '3m',  dur: 180   },
  { label: '5m',  interval: '5m',  dur: 300   },
  { label: '15m', interval: '15m', dur: 900   },
  { label: '1h',  interval: '1h',  dur: 3600  },
  { label: '4h',  interval: '4h',  dur: 14400 },
  { label: '1D',  interval: '1d',  dur: 86400 },
];

export interface ApexCandleChartProps {
  symbol?: string;
  position?: Position | null;
  signal?: Signal | null;
  defaultTimeframe?: string;
  onTimeframeChange?: (tf: string) => void;
  showVolume?: boolean;
  className?: string;
  hideHeader?: boolean;
}

// â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const fmt = (v: any, d = 2) => {
  if (v === undefined || v === null || isNaN(Number(v))) return '0.00';
  const numVal = Number(v);
  const decimals = numVal < 1 ? Math.min(6, Math.max(2, (numVal.toString().split('.')[1] || '').length)) : d;
  return numVal.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};

const num = (v: unknown) => {
  const value = Number(v);
  return Number.isFinite(value) ? value : 0;
};

const epochSeconds = (v: unknown) => {
  if (!v) return 0;
  if (typeof v === 'number') {
    return v > 10_000_000_000 ? Math.floor(v / 1000) : Math.floor(v);
  }
  const str = String(v).trim();
  const numVal = Number(str);
  if (!isNaN(numVal) && numVal > 1_000_000) {
    return numVal > 10_000_000_000 ? Math.floor(numVal / 1000) : Math.floor(numVal);
  }
  const parsed = Date.parse(str.replace(' UTC', 'Z'));
  if (!isNaN(parsed) && parsed > 0) {
    return Math.floor(parsed / 1000);
  }
  return 0;
};

export const ApexCandleChart: React.FC<ApexCandleChartProps> = ({
  symbol: propSymbol,
  position,
  signal,
  defaultTimeframe = '15m',
  onTimeframeChange,
  showVolume = true,
  className = '',
  hideHeader = false
}) => {
  const activeSymbol = (position?.symbol || signal?.symbol || propSymbol || 'BTC/USDT').toUpperCase();
  const wrapRef = React.useRef<HTMLDivElement>(null);
  
  // Ref states for performance & wheel / drag handling
  const zoomRef = React.useRef(1);
  const offsetRef = React.useRef(0);
  const dataRef = React.useRef(0);
  const vScaleRef = React.useRef(1); // vertical scale multiplier

  const [W, setW] = React.useState(900);
  const [H, setH] = React.useState(380);
  const [zoom, setZoom] = React.useState(1);
  const [vScale, setVScale] = React.useState(1);
  const [offsetX, setOffsetX] = React.useState(0);
  
  // Drag states
  const [dragging, setDragging] = React.useState(false);
  const [dragMode, setDragMode] = React.useState<'pan' | 'vscale' | 'pos_stretch'>('pan');
  const [dragX0, setDragX0] = React.useState(0);
  const [dragY0, setDragY0] = React.useState(0);
  const [dragDelta, setDragDelta] = React.useState(0);
  const [posLengthBars, setPosLengthBars] = React.useState<number>(18); // length of TradingView position box in bars
  const [hoverPrice, setHoverPrice] = React.useState<number | null>(null);
  const [hoverIndex, setHoverIndex] = React.useState<number | null>(null);

  // Timeframe selection
  const initialTf = TIMEFRAMES.find(t => 
    t.label.toLowerCase() === defaultTimeframe.toLowerCase() || 
    t.interval.toLowerCase() === defaultTimeframe.toLowerCase()
  ) || TIMEFRAMES[3]; // default 15m

  const [tf, setTf] = React.useState<TimeframeOption>(initialTf);
  const [klines, setKlines] = React.useState<any[]>([]);
  const [loadingK, setLoadingK] = React.useState(false);
  const [livePrice, setLivePrice] = React.useState<number | null>(null);

  // Trade / Signal Parameters
  const side = position?.side || signal?.side || 'BUY';
  const isBuy = side === 'BUY';
  const entryPrice = num(position?.entryPrice || signal?.entry);
  const stopLoss = num(position?.sl || signal?.sl);
  
  // Extract Target Levels (TP1, TP2, TP3)
  const targets = React.useMemo(() => {
    const list: Array<{ label: string; value: number }> = [];
    if (position) {
      if (position.tp1 && num(position.tp1) > 0) list.push({ label: 'TP1', value: num(position.tp1) });
      if (position.tp2 && num(position.tp2) > 0) list.push({ label: 'TP2', value: num(position.tp2) });
      if (position.tp3 && num(position.tp3) > 0) list.push({ label: 'TP3', value: num(position.tp3) });
    } else if (signal) {
      if (signal.tp1 && num(signal.tp1) > 0) list.push({ label: 'TP1', value: num(signal.tp1) });
      if (signal.tp2 && num(signal.tp2) > 0) list.push({ label: 'TP2', value: num(signal.tp2) });
      if (signal.tp3 && num(signal.tp3) > 0) list.push({ label: 'TP3', value: num(signal.tp3) });
      if (list.length === 0 && signal.tp && num(signal.tp) > 0) list.push({ label: 'TP1', value: num(signal.tp) });
    }
    return list.filter(t => isBuy ? t.value > entryPrice : t.value < entryPrice);
  }, [position, signal, entryPrice, isBuy]);

  const hasStop = entryPrice > 0 && stopLoss > 0 && (isBuy ? stopLoss < entryPrice : stopLoss > entryPrice);

  // Calculated Risk/Reward
  const calculatedRR = React.useMemo(() => {
    if (signal?.rr) return Number(signal.rr).toFixed(2);
    if (position?.rewardPercent) return Number(position.rewardPercent).toFixed(2);
    if (entryPrice > 0 && stopLoss > 0 && targets.length > 0) {
      const risk = Math.abs(entryPrice - stopLoss);
      const reward = Math.abs(targets[0].value - entryPrice);
      if (risk > 0) return (reward / risk).toFixed(2);
    }
    return '2.00';
  }, [signal?.rr, position?.rewardPercent, entryPrice, stopLoss, targets]);

  // Keep refs in sync for wheel/drag handlers
  React.useEffect(() => { zoomRef.current = zoom; }, [zoom]);
  React.useEffect(() => { offsetRef.current = offsetX; }, [offsetX]);
  React.useEffect(() => { vScaleRef.current = vScale; }, [vScale]);

  // Measure container and attach non-passive wheel listener
  React.useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 20 && height > 20) {
          setW(Math.floor(width));
          setH(Math.floor(height));
        }
      }
    });
    ro.observe(el);

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const PL2 = 10, PR2 = 85;
      const cw2 = Math.max(1, el.getBoundingClientRect().width - PL2 - PR2);
      const rect = el.getBoundingClientRect();
      const mouseX = e.clientX - rect.left - PL2;

      // If wheel over price scale (right 85px), scale vertically!
      if (e.clientX > rect.right - PR2) {
        const vDelta = e.deltaY > 0 ? -0.1 : 0.1;
        setVScale(vs => Math.max(0.3, Math.min(4.0, vs * (1 + vDelta))));
        return;
      }

      // Horizontal zoom centered on cursor
      const curZoom = zoomRef.current;
      const curOffset = offsetRef.current;
      const nData = dataRef.current + 35; // include 35 future empty bars buffer
      const curStep = Math.max(3, (cw2 / Math.max(1, nData)) * curZoom);
      const priceIdxUnderCursor = (curOffset + mouseX) / curStep;

      const delta = e.deltaY > 0 ? -0.14 : 0.14;
      const newZoom = Math.max(0.15, Math.min(16, curZoom * (1 + delta)));
      const newStep = Math.max(3, (cw2 / Math.max(1, nData)) * newZoom);
      const newOff = Math.max(0, priceIdxUnderCursor * newStep - mouseX);
      const maxO2 = Math.max(0, nData * newStep - cw2);
      const finalOff = Math.min(newOff, maxO2);

      zoomRef.current = newZoom;
      offsetRef.current = finalOff;
      setZoom(newZoom);
      setOffsetX(finalOff);
    };

    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      ro.disconnect();
      el.removeEventListener('wheel', handleWheel);
    };
  }, []);

  // Fetch Klines from API
  const fetchKlines = React.useCallback(async () => {
    if (!activeSymbol) return;
    setLoadingK(true);
    try {
      const formattedSymbol = activeSymbol.replace('/', '').toUpperCase();
      const res = await fetch(`/api/v1/market/klines?symbol=${encodeURIComponent(formattedSymbol)}&interval=${tf.interval}&limit=200`);
      if (res.ok) {
        const j = await res.json();
        if (j?.status === 'SUCCESS' && Array.isArray(j.data)) {
          const filtered = j.data.filter((k: any) => k && typeof k.high === 'number' && typeof k.low === 'number');
          setKlines(filtered);
          if (filtered.length > 0) {
            setLivePrice(filtered[filtered.length - 1].close);
          }
          return;
        }
      }
      
      // Direct Binance fallback
      const bRes = await fetch(`https://api.binance.com/api/v3/klines?symbol=${formattedSymbol}&interval=${tf.interval}&limit=200`);
      if (bRes.ok) {
        const raw = await bRes.json();
        const mapped = raw.map((d: any) => ({
          timestamp: Math.floor(d[0] / 1000),
          time: new Date(d[0]).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          open: parseFloat(d[1]),
          high: parseFloat(d[2]),
          low: parseFloat(d[3]),
          close: parseFloat(d[4]),
          volume: parseFloat(d[5]),
          isUp: parseFloat(d[4]) >= parseFloat(d[1])
        }));
        setKlines(mapped);
        if (mapped.length > 0) {
          setLivePrice(mapped[mapped.length - 1].close);
        }
      }
    } catch (e) {
      console.warn('Error fetching klines:', e);
    } finally {
      setLoadingK(false);
    }
  }, [activeSymbol, tf.interval]);

  React.useEffect(() => {
    fetchKlines();
  }, [fetchKlines]);

  // Subscribe to live price ticks
  React.useEffect(() => {
    if (!activeSymbol) return;
    const unsub = subscribeBinanceLivePrices((sym, price) => {
      const normSym = sym.replace('/', '').toUpperCase();
      const normTarget = activeSymbol.replace('/', '').toUpperCase();
      if (normSym === normTarget && price > 0) {
        setLivePrice(price);
        setKlines(prev => {
          if (!prev || prev.length === 0) return prev;
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          const last = { ...updated[lastIdx] };
          last.close = price;
          if (price > last.high) last.high = price;
          if (price < last.low) last.low = price;
          last.isUp = last.close >= last.open;
          updated[lastIdx] = last;
          return updated;
        });
      }
    });
    return () => unsub();
  }, [activeSymbol]);

  const data = React.useMemo(() => {
    return Array.isArray(klines) ? klines.filter(k => k && typeof k.high === 'number' && typeof k.low === 'number') : [];
  }, [klines]);

  React.useEffect(() => {
    dataRef.current = data.length;
  }, [data.length]);

  // â”€â”€â”€ Center / Position Logic like TradingView â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // FUTURE_BARS adds empty space on the right (like TradingView's right margin)
  const FUTURE_BARS = 35;
  const totalSlots = Math.max(1, data.length + FUTURE_BARS);

  // Position chart nicely centered with right-side breathing room
  const centerOnTradeOrLatest = React.useCallback((mode: 'center_entry' | 'latest' = 'center_entry') => {
    if (data.length === 0 || W <= 20) return;
    
    const cw2 = Math.max(1, W - 10 - 85);
    const SHOW = 65; // standard TradingView visible candles
    const newZoom = Math.max(0.4, Math.min(6, totalSlots / SHOW));
    const newStep = Math.max(3, (cw2 / totalSlots) * newZoom);
    const maxO = Math.max(0, totalSlots * newStep - cw2);

    let targetOffset = 0;
    if (mode === 'center_entry' && entryPrice > 0) {
      // Find entry index
      let entryIdx = Math.max(0, data.length - 2);
        const rawTime = (position as any)?.entry_timestamp || 
                        (position as any)?.formatted_entry_time || 
                        position?.timeOpen || 
                        signal?.timestamp || 
                        signal?.createdAt;
        const entryTime = epochSeconds(rawTime);
        if (entryTime > 0) {
          data.forEach((k, i) => {
            if (k.timestamp && entryTime >= k.timestamp && entryTime < k.timestamp + tf.dur) {
              entryIdx = i;
            }
          });
        }
        const entryPx = entryIdx * newStep;
        targetOffset = Math.max(0, entryPx - cw2 * 0.42);
    } else {
      // Latest candle at 68% from left (leaving 32% future space on the right, NOT glued!)
      const latestPx = (data.length - 1) * newStep;
      targetOffset = Math.max(0, latestPx - cw2 * 0.68);
    }

    setZoom(newZoom);
    setVScale(1);
    setOffsetX(Math.min(targetOffset, maxO));
    setDragDelta(0);
  }, [data, W, totalSlots, entryPrice, position?.timeOpen, signal?.timestamp, signal?.createdAt, tf.dur]);

  // Run initial centering on symbol / trade change
  React.useEffect(() => {
    centerOnTradeOrLatest('center_entry');
  }, [activeSymbol, position?.id, signal?.id, data.length > 0]);

  // Dimensions & Coordinates
  const PL = 10, PR = 85, PT = 16, PB = 28;
  const cW = Math.max(1, W - PL - PR);
  const cH = Math.max(1, H - PT - PB);
  const n = data.length;
  const step = Math.max(3, (cW / totalSlots) * zoom);
  const cndW = Math.max(1.8, step * 0.72);
  const maxOff = Math.max(0, totalSlots * step - cW);
  const off = Math.max(0, Math.min(offsetX + dragDelta, maxOff));

  const fi = Math.max(0, Math.floor(off / step));
  const li = Math.min(n - 1, Math.ceil((off + cW) / step) + 1);
  const vis = data.slice(fi, Math.max(fi + 1, li + 1));

  const lastClose = livePrice || num(data[data.length - 1]?.close);

  // Price boundaries
  const prices: number[] = [
    ...vis.map(k => k.high).filter(isFinite),
    ...vis.map(k => k.low).filter(isFinite),
  ];
  if (entryPrice > 0) prices.push(entryPrice);
  if (hasStop) prices.push(stopLoss);
  targets.forEach(target => prices.push(target.value));
  if (lastClose > 0) prices.push(lastClose);

  let rawHi = prices.length ? Math.max(...prices) : 100;
  let rawLo = prices.length ? Math.min(...prices) : 90;
  const rawRng = rawHi - rawLo || 1;

  // Apply vertical scale (vScale) & padding
  const midPrice = (rawHi + rawLo) / 2;
  const scaledHalfRng = ((rawRng * 1.25) / 2) / vScale;
  const hi = midPrice + scaledHalfRng;
  const lo = midPrice - scaledHalfRng;
  const PR2 = hi - lo || 1;

  // Max volume for volume histogram
  const maxVol = Math.max(...vis.map(k => k.volume || 0), 1);

  const gx = (ai: number) => PL + (ai - fi) * step + step / 2 - (off % step);
  const gy = (p: number) => PT + cH - ((p - lo) / PR2) * cH;

  // Find Entry candle index
  let entryIndex = Math.max(0, n - 2);
    if (entryPrice > 0) {
      const rawTime = (position as any)?.entry_timestamp || 
                      (position as any)?.formatted_entry_time || 
                      position?.timeOpen || 
                      signal?.timestamp || 
                      signal?.createdAt;
      const entryTime = epochSeconds(rawTime);
      let found = false;
      if (entryTime > 0) {
        data.forEach((k, i) => {
          if (k.timestamp && entryTime >= k.timestamp && entryTime < k.timestamp + tf.dur) {
            entryIndex = i;
            found = true;
          }
        });
      }
      if (!found) {
        entryIndex = Math.max(0, n - 2);
      }
  }

  // Position Box (TradingView Long / Short Tool)
  // Starts precisely at entry candle, extends across current trade with clean width
  const posStartX = gx(entryIndex);
  // Box end in pixels
  const posWidthPx = Math.max(step * 6, step * posLengthBars);
  const posEndX = Math.min(W - PR, posStartX + posWidthPx);

  // Target values
  const finalTarget = targets[targets.length - 1] || (entryPrice > 0 ? { label: 'TP1', value: isBuy ? entryPrice * 1.03 : entryPrice * 0.97 } : null);

  // Mouse Handlers
  const onMD = (e: React.MouseEvent) => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    
    // Check if dragging right scale (Y-axis vertical stretch)
    if (mx > W - PR) {
      setDragMode('vscale');
      setDragY0(e.clientY);
    } else if (Math.abs(mx - posEndX) < 14) {
      // Dragging the right edge of position tool
      setDragMode('pos_stretch');
      setDragX0(e.clientX);
    } else {
      // Normal chart pan
      setDragMode('pan');
      setDragX0(e.clientX);
      setDragDelta(0);
    }
    setDragging(true);
  };

  const onMM = (e: React.MouseEvent) => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Calculate hover price & bar
    const p = lo + ((PT + cH - my) / cH) * PR2;
    setHoverPrice(p > 0 ? p : null);
    const barIdx = Math.floor((off + mx - PL) / step);
    setHoverIndex(barIdx >= 0 && barIdx < n ? barIdx : null);

    if (dragging) {
      if (dragMode === 'pan') {
        setDragDelta(-(e.clientX - dragX0));
      } else if (dragMode === 'vscale') {
        const deltaY = dragY0 - e.clientY;
        const factor = 1 + (deltaY / 200);
        setVScale(vs => Math.max(0.2, Math.min(5.0, vs * factor)));
        setDragY0(e.clientY);
      } else if (dragMode === 'pos_stretch') {
        const deltaBars = Math.round((e.clientX - dragX0) / step);
        if (deltaBars !== 0) {
          setPosLengthBars(b => Math.max(6, Math.min(80, b + deltaBars)));
          setDragX0(e.clientX);
        }
      }
    }
  };

  const onMU = () => {
    if (dragging && dragMode === 'pan') {
      setOffsetX(p => {
        const finalOff = Math.max(0, Math.min(p + dragDelta, maxOff));
        offsetRef.current = finalOff;
        return finalOff;
      });
      setDragDelta(0);
    }
    setDragging(false);
  };

  const GRID = 7;
  const plotRight = W - PR;

  const handleTimeframeSelect = (newTf: TimeframeOption) => {
    setTf(newTf);
    if (onTimeframeChange) onTimeframeChange(newTf.label);
  };

  return (
    <div className={`w-full h-full flex flex-col font-mono select-none bg-[#131722] text-[#d1d4dc] ${className}`}>
      {/* Top TradingView-Style Bar */}
      {!hideHeader && (
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1e222d] border-b border-[#2a2e39] shrink-0 gap-2 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold overflow-hidden flex-wrap">
          <span className="text-white font-bold">{activeSymbol}</span>
          <span className="text-[#50535e]">Â·</span>
          
          {/* Timeframe Selector Pills */}
          <div className="flex items-center bg-[#131722] p-0.5 rounded border border-[#2a2e39]">
            {TIMEFRAMES.map(t => (
              <button
                key={t.label}
                onClick={() => handleTimeframeSelect(t)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                  tf.label === t.label
                    ? 'bg-[#2962ff] text-white shadow-sm'
                    : 'text-[#787b86] hover:text-white hover:bg-[#2a2e39]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          
          <span className="text-[#50535e]">Â·</span>
          <span className="text-[#787b86] text-[10px]">BINANCE PERPETUAL</span>

          {entryPrice > 0 && (
            <>
              <span className="text-[#50535e]">Â·</span>
              <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                isBuy ? 'bg-[#089981]/20 text-[#089981] border border-[#089981]/40' : 'bg-[#f23645]/20 text-[#f23645] border border-[#f23645]/40'
              }`}>
                {isBuy ? 'LONG' : 'SHORT'}
              </span>
              <span className="text-[#787b86]">entry: <strong className="text-white">${fmt(entryPrice)}</strong></span>
              {hasStop && <span className="text-[#f23645]">sl: ${fmt(stopLoss)}</span>}
              {targets.map(target => (
                <span key={target.label} className="text-[#089981]">{target.label}: ${fmt(target.value)}</span>
              ))}
              <span className="text-[#2962ff] font-bold">R:R 1:{calculatedRR}</span>
            </>
          )}
        </div>

        {/* View & Navigation Controls */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => setZoom(z => Math.min(16, z * 1.25))}
            className="p-1 text-[#787b86] hover:text-white hover:bg-[#2a2e39] rounded transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          
          <button
            onClick={() => setZoom(z => Math.max(0.15, z / 1.25))}
            className="p-1 text-[#787b86] hover:text-white hover:bg-[#2a2e39] rounded transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => centerOnTradeOrLatest('center_entry')}
            className="px-2 py-0.5 text-[10px] text-white bg-[#2a2e39] hover:bg-[#363a45] rounded font-bold transition-colors flex items-center gap-1"
            title="Center Trade on Screen"
          >
            <Crosshair className="w-3 h-3 text-[#2962ff]" />
            <span>TRADE</span>
          </button>

          <button
            onClick={() => centerOnTradeOrLatest('latest')}
            className="px-2 py-0.5 text-[10px] text-[#2962ff] hover:bg-[#2962ff]/10 border border-[#2962ff]/30 rounded font-bold transition-colors"
            title="Go to latest candle"
          >
            LATEST
          </button>

          <button
            onClick={() => { setVScale(1); centerOnTradeOrLatest('center_entry'); }}
            className="p-1 text-[#787b86] hover:text-white hover:bg-[#2a2e39] rounded transition-colors"
            title="Reset Chart View (100%)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      )}

      {/* Main TradingView SVG Chart Area */}
      <div
        ref={wrapRef}
        className={`flex-1 bg-[#131722] relative overflow-hidden ${
          dragging ? (dragMode === 'vscale' ? 'cursor-ns-resize' : 'cursor-grabbing') : 'cursor-crosshair'
        }`}
        onMouseDown={onMD}
        onMouseMove={onMM}
        onMouseUp={onMU}
        onMouseLeave={onMU}
        style={{ touchAction: 'none', userSelect: 'none' }}
      >
        {loadingK ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <Activity className="w-6 h-6 animate-spin text-[#2962ff]" />
            <span className="text-[11px] text-[#787b86] uppercase tracking-widest">Loading Binance Market Depth...</span>
          </div>
        ) : data.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <BarChart2 className="w-8 h-8 text-[#2a2e39]" />
            <span className="text-[11px] text-[#787b86] uppercase tracking-widest">No Market Data Available</span>
          </div>
        ) : (
          <svg width={W} height={H} style={{ display: 'block', width: '100%', height: '100%' }}>
            <defs>
              {/* TradingView Long Position Shaded Fills */}
              <linearGradient id="tv_green_zone" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#089981" stopOpacity="0.28"/>
                <stop offset="100%" stopColor="#089981" stopOpacity="0.14"/>
              </linearGradient>
              <linearGradient id="tv_red_zone" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f23645" stopOpacity="0.14"/>
                <stop offset="100%" stopColor="#f23645" stopOpacity="0.28"/>
              </linearGradient>
            </defs>

            {/* TradingView Large Watermark in background */}
            <text
              x={cW * 0.42}
              y={cH * 0.55}
              fill="#1e222d"
              fontSize={Math.min(48, W * 0.055)}
              fontWeight="bold"
              fontFamily="sans-serif"
              textAnchor="middle"
              pointerEvents="none"
            >
              {activeSymbol}, {tf.label}
            </text>

            {/* Horizontal Price Grid Lines */}
            {Array.from({ length: GRID }, (_, i) => {
              const p = lo + (i / (GRID - 1)) * PR2;
              const y = gy(p);
              return (
                <g key={i}>
                  <line x1={PL} y1={y} x2={W - PR} y2={y} stroke="#1e222d" strokeWidth={1} strokeDasharray="3 3"/>
                  <text x={W - PR + 6} y={y + 3.5} fill="#787b86" fontSize={9} fontFamily="monospace">${fmt(p)}</text>
                </g>
              );
            })}

            {/* Vertical Time Grid Ticks */}
            {vis.filter((_, i) => i % Math.max(1, Math.floor(vis.length / 8)) === 0).map((k, i) => {
              const ai = fi + i * Math.max(1, Math.floor(vis.length / 8));
              const x = gx(ai);
              const lbl = k.timestamp ? new Date(k.timestamp * 1000).toLocaleDateString([], { month: 'short', day: 'numeric' }) : k.time || '';
              return (
                <g key={i}>
                  <line x1={x} y1={PT} x2={x} y2={H - PB} stroke="#1e222d" strokeWidth={1} strokeDasharray="3 3"/>
                  <text x={x} y={H - PB + 13} fill="#50535e" fontSize={8.5} fontFamily="monospace" textAnchor="middle">{lbl}</text>
                </g>
              );
            })}

            {/* Axis Separator Lines */}
            <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="#2a2e39" strokeWidth={1}/>
            <line x1={W - PR} y1={PT} x2={W - PR} y2={H - PB} stroke="#2a2e39" strokeWidth={1}/>

            {/* Volume Histogram (TradingView subtle bottom bars) */}
            {showVolume && vis.map((k, ri) => {
              const ai = fi + ri;
              const x = gx(ai);
              if (x < PL - cndW || x > W - PR + cndW) return null;
              const volRatio = (k.volume || 0) / maxVol;
              const vH = Math.max(2, volRatio * (cH * 0.18));
              const vY = H - PB - vH;
              const col = k.close >= k.open ? 'rgba(8, 153, 129, 0.20)' : 'rgba(242, 54, 69, 0.20)';
              return (
                <rect key={`v_${ai}`} x={x - cndW / 2} y={vY} width={cndW} height={vH} fill={col} shapeRendering="crispEdges"/>
              );
            })}

            {/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                TRADINGVIEW POSITION TOOL (EXACT MATCH TO REFERENCE SCREENSHOT)
               â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
            {entryPrice > 0 && finalTarget && (
              <g>
                {/* 1. Subtle TP zone tint - lines only, no box */}
                <rect
                  x={PL}
                  y={Math.min(gy(entryPrice), gy(finalTarget.value))}
                  width={Math.max(0, plotRight - PL)}
                  height={Math.abs(gy(entryPrice) - gy(finalTarget.value))}
                  fill="rgba(8,153,129,0.04)"
                  stroke="none"
                />

                {/* 2. Subtle SL zone tint - lines only, no box */}
                {hasStop && (
                  <rect
                    x={PL}
                    y={Math.min(gy(entryPrice), gy(stopLoss))}
                    width={Math.max(0, plotRight - PL)}
                    height={Math.abs(gy(entryPrice) - gy(stopLoss))}
                    fill="rgba(242,54,69,0.04)"
                    stroke="none"
                  />
                )}

                {/* 3. Drag Handle on Right Edge of Position Tool */}
                <rect
                  x={posEndX - 3}
                  y={Math.min(gy(finalTarget.value), gy(stopLoss || entryPrice))}
                  width={6}
                  height={Math.abs(gy(finalTarget.value) - gy(stopLoss || entryPrice))}
                  fill="#ffffff"
                  fillOpacity={0.01}
                  className="cursor-ew-resize hover:fill-white/20"
                />

                {/* 4. TP Horizontal Level Lines & Centered Label */}
                {targets.map((target, tidx) => {
                  const ty = gy(target.value);
                  return (
                    <g key={target.label}>
                      {/* Full horizontal line across chart */}
                      <line x1={posStartX} y1={ty} x2={plotRight} y2={ty} stroke="#089981" strokeWidth={2}/>
                      
                      {/* Centered TP text in white, matching TradingView */}
                      <text
                        x={(posStartX + plotRight) / 2}
                        y={ty - 5}
                        fill="#ffffff"
                        fontSize={10}
                        fontWeight="bold"
                        fontFamily="sans-serif"
                        textAnchor="middle"
                      >
                        {target.label === 'TP1' ? 'TP' : target.label}
                      </text>

                      {/* Right Axis Green Badge */}
                      <rect x={plotRight + 1} y={ty - 8} width={80} height={16} rx={2} fill="#089981"/>
                      <text x={plotRight + 5} y={ty + 3.5} fill="#ffffff" fontSize={9} fontWeight="bold" fontFamily="monospace">
                        {fmt(target.value)}
                      </text>
                    </g>
                  );
                })}

                {/* 5. Entry Horizontal Level Line & Centered Label */}
                <g>
                  <line x1={posStartX} y1={gy(entryPrice)} x2={plotRight} y2={gy(entryPrice)} stroke="#e2e8f0" strokeWidth={2}/>
                  
                  {/* Centered 'entry' label in white */}
                  <text
                    x={(posStartX + plotRight) / 2}
                    y={gy(entryPrice) - 5}
                    fill="#ffffff"
                    fontSize={10}
                    fontWeight="bold"
                    fontFamily="sans-serif"
                    textAnchor="middle"
                  >
                    entry
                  </text>

                  {/* Right Axis Silver/Gray Badge */}
                  <rect x={plotRight + 1} y={gy(entryPrice) - 8} width={80} height={16} rx={2} fill="#475569"/>
                  <text x={plotRight + 5} y={gy(entryPrice) + 3.5} fill="#ffffff" fontSize={9} fontWeight="bold" fontFamily="monospace">
                    {fmt(entryPrice)}
                  </text>
                </g>

                {/* 6. Stop Loss Horizontal Level Line & Centered Label */}
                {hasStop && (
                  <g>
                    <line x1={posStartX} y1={gy(stopLoss)} x2={plotRight} y2={gy(stopLoss)} stroke="#f23645" strokeWidth={2}/>
                    
                    {/* Centered 'sl' label in white */}
                    <text
                      x={(posStartX + plotRight) / 2}
                      y={gy(stopLoss) - 5}
                      fill="#ffffff"
                      fontSize={10}
                      fontWeight="bold"
                      fontFamily="sans-serif"
                      textAnchor="middle"
                    >
                      sl
                    </text>

                    {/* Right Axis Red Badge */}
                    <rect x={plotRight + 1} y={gy(stopLoss) - 8} width={80} height={16} rx={2} fill="#f23645"/>
                    <text x={plotRight + 5} y={gy(stopLoss) + 3.5} fill="#ffffff" fontSize={9} fontWeight="bold" fontFamily="monospace">
                      {fmt(stopLoss)}
                    </text>
                  </g>
                )}
              </g>
            )}

            {/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                CANDLESTICKS (SHARP PIXEL TRADINGVIEW RENDER)
               â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
            {vis.map((k, ri) => {
              const ai = fi + ri;
              const x = gx(ai);
              if (x < PL - cndW * 2 || x > W - PR + cndW * 2) return null;
              
              const up = k.close >= k.open;
              const col = up ? '#089981' : '#f23645'; // TradingView standard candle colors
              const bTop = Math.min(gy(k.open), gy(k.close));
              const bH = Math.max(1.5, Math.abs(gy(k.open) - gy(k.close)));
              
              return (
                <g key={ai}>
                  {/* High/Low Wick */}
                  <line x1={x} y1={gy(k.high)} x2={x} y2={gy(k.low)} stroke={col} strokeWidth={1.2} shapeRendering="crispEdges"/>
                  {/* Candle Body */}
                  <rect x={x - cndW / 2} y={bTop} width={cndW} height={bH} fill={col} shapeRendering="crispEdges"/>
                </g>
              );
            })}

            {/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                REAL-TIME LIVE PRICE LINE & TRADINGVIEW ORANGE/AMBER BADGE
               â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
            {lastClose > 0 && (
              <g>
                {/* Dashed line across whole chart */}
                <line
                  x1={PL}
                  y1={gy(lastClose)}
                  x2={plotRight}
                  y2={gy(lastClose)}
                  stroke="#f59e0b"
                  strokeDasharray="3 3"
                  strokeWidth={1.2}
                />
                
                {/* Right-scale TradingView Orange / Amber Price Pill */}
                <rect x={plotRight + 1} y={gy(lastClose) - 8} width={80} height={16} rx={2} fill="#f59e0b"/>
                <text x={plotRight + 5} y={gy(lastClose) + 3.5} fill="#000000" fontSize={9} fontWeight="bold" fontFamily="monospace">
                  {fmt(lastClose)}
                </text>
              </g>
            )}

            {/* Crosshair on hover */}
            {hoverPrice && (
              <g pointerEvents="none" opacity={0.65}>
                <line x1={PL} y1={gy(hoverPrice)} x2={plotRight} y2={gy(hoverPrice)} stroke="#787b86" strokeDasharray="2 2" strokeWidth={0.8}/>
                <rect x={plotRight + 1} y={gy(hoverPrice) - 7} width={80} height={14} fill="#2a2e39"/>
                <text x={plotRight + 5} y={gy(hoverPrice) + 3} fill="#d1d4dc" fontSize={8} fontFamily="monospace">${fmt(hoverPrice)}</text>
              </g>
            )}
          </svg>
        )}
      </div>

      {/* Bottom Status / Navigation Bar */}
      {!hideHeader && (
      <div className="h-6 bg-[#1e222d] border-t border-[#2a2e39] px-3 flex items-center justify-between text-[9px] font-mono text-[#787b86] shrink-0">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-white">
            <span className="w-1.5 h-1.5 rounded-full bg-[#089981] animate-pulse"/> LIVE FEED
          </span>
          <span>O: <strong className="text-white">${fmt(vis[vis.length - 1]?.open || lastClose)}</strong></span>
          <span>H: <strong className="text-[#089981]">${fmt(vis[vis.length - 1]?.high || lastClose)}</strong></span>
          <span>L: <strong className="text-[#f23645]">${fmt(vis[vis.length - 1]?.low || lastClose)}</strong></span>
          <span>C: <strong className="text-white">${fmt(lastClose)}</strong></span>
        </div>

        <div className="flex items-center gap-3">
          <span>Drag = Pan</span>
          <span>Wheel = Zoom</span>
          <span>Scale Drag = Vert Scale</span>
          <span>Box Edge = Stretch</span>
        </div>
      </div>
      )}
    </div>
  );
};

export default ApexCandleChart;

