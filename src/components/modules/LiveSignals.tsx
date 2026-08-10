import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { 
  Zap, 
  CheckCircle2, 
  XCircle, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Activity, 
  RefreshCw, 
  History, 
  Percent, 
  X, 
  Info,
  ChevronRight
} from 'lucide-react';

interface Verification {
  label: string;
  passed: boolean;
}

interface Signal {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL' | 'NO_TRADE';
  timeframe: string;
  aiScore: number;
  confidence: number;
  probability: number;
  rr: number;
  entry: number;
  sl: number;
  tp: number;
  status: string;
  aiNotes?: string;
  reasoning?: string;
  timestamp?: number;
  exit_timestamp?: number;
  formatted_time?: string;
  verification?: Verification[];
  passedFactors?: number;
  totalFactors?: number;
  indicators?: {
    atr?: number;
    rsi?: number;
    ema21?: number;
    ema50?: number;
    ema200?: number;
    macdHist?: number;
    volumeDelta?: number;
    trend?: string;
  };
}

export const LiveSignals: React.FC = () => {
  const { signals: initialSignals } = useTerminal();
  const [signals, setSignals] = React.useState<Signal[]>(initialSignals as Signal[]);
  const [history, setHistory] = React.useState<Signal[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [loadingHist, setLoadingHist] = React.useState(false);
  const [lastUpdate, setLastUpdate] = React.useState<Date | null>(null);

  // Modal / Chart States
  const [selectedSignal, setSelectedSignal] = React.useState<Signal | null>(null);
  const [klines, setKlines] = React.useState<any[]>([]);
  const [loadingKlines, setLoadingKlines] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  const fetchLiveSignals = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/signals/live');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setSignals(data);
          setLastUpdate(new Date());
        }
      }
    } catch (err) {
      console.warn('Error fetching live signals:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    setLoadingHist(true);
    try {
      const res = await fetch('/api/v1/signals/history');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setHistory(data);
        }
      }
    } catch (err) {
      console.warn('Error fetching signals history:', err);
    } finally {
      setLoadingHist(false);
    }
  };

  const fetchKlines = async (symbol: string) => {
    setLoadingKlines(true);
    try {
      // Fetch 80 candles to allow extensive scrolling and historical context
      const res = await fetch(`/api/v1/market/klines?symbol=${encodeURIComponent(symbol)}&interval=15m&limit=80`);
      if (res.ok) {
        const json = await res.json();
        if (json.status === 'SUCCESS' && Array.isArray(json.data)) {
          setKlines(json.data);
        }
      }
    } catch (err) {
      console.warn('Error fetching klines:', err);
    } finally {
      setLoadingKlines(false);
    }
  };

  React.useEffect(() => {
    fetchLiveSignals();
    fetchHistory();
    const interval = setInterval(() => {
      fetchLiveSignals();
      fetchHistory();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  React.useEffect(() => {
    if (selectedSignal) {
      fetchKlines(selectedSignal.symbol);
    } else {
      setKlines([]);
    }
  }, [selectedSignal]);

  React.useEffect(() => {
    if (scrollRef.current && klines.length > 0) {
      // Small timeout to allow browser layout to complete before scrolling
      setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
        }
      }, 50);
    }
  }, [klines]);

  const SideIcon = ({ side }: { side: string }) => {
    if (side === 'BUY')  return <TrendingUp  className="w-3.5 h-3.5" />;
    if (side === 'SELL') return <TrendingDown className="w-3.5 h-3.5" />;
    return <Minus className="w-3.5 h-3.5" />;
  };

  const FactorRow = ({ label, passed }: { label: string; passed: boolean }) => (
    <div className={`flex items-center space-x-1 ${passed ? 'text-apex-success' : 'text-apex-danger'}`}>
      {passed
        ? <CheckCircle2 className="w-3 h-3 shrink-0" />
        : <XCircle     className="w-3 h-3 shrink-0" />}
      <span>{label}: {passed ? 'PASS' : 'FAIL'}</span>
    </div>
  );

  // SVG Candlestick Chart Renderer
  const renderSVGChart = () => {
    if (loadingKlines) {
      return (
        <div className="h-[360px] flex flex-col items-center justify-center text-apex-muted border border-apex-border bg-apex-bg/30 rounded">
          <Activity className="w-7 h-7 animate-spin text-apex-accent mb-2" />
          <span className="text-[11px] uppercase tracking-wider font-bold">Connecting to Binance Data...</span>
        </div>
      );
    }

    if (klines.length === 0) {
      return (
        <div className="h-[360px] flex flex-col items-center justify-center text-apex-muted border border-apex-border bg-apex-bg/30 rounded">
          <Info className="w-7 h-7 text-apex-warning mb-2 animate-bounce" />
          <span className="text-[11px] uppercase tracking-wider font-bold text-apex-warning">No chart data found</span>
          <span className="text-[10px] text-apex-muted mt-1">Please verify server network connection.</span>
        </div>
      );
    }

    // Increased width for extra horizontal room: 1500px width
    const width = 1500;
    const height = 380;
    const paddingLeft = 30;
    const paddingRight = 110;
    const paddingTop = 45;
    const paddingBottom = 45;

    const chartWidth = width - paddingLeft - paddingRight;
    const chartHeight = height - paddingTop - paddingBottom;

    // Extract highs, lows
    const highs = klines.map(k => k.high);
    const lows = klines.map(k => k.low);

    // Scaling bounds must include candles + Entry + SL + TP levels
    const entryPrice = selectedSignal?.entry || 0;
    const slPrice = selectedSignal?.sl || 0;
    const tpPrice = selectedSignal?.tp || 0;

    let maxPrice = Math.max(...highs, entryPrice, slPrice, tpPrice);
    let minPrice = Math.min(...lows, entryPrice, slPrice, tpPrice);

    // Padding values to give space to visual targets
    const priceDiff = maxPrice - minPrice || 1.0;
    maxPrice += priceDiff * 0.08;
    minPrice -= priceDiff * 0.08;

    const getX = (index: number) => {
      return paddingLeft + (index / (klines.length - 1)) * chartWidth;
    };

    const getY = (price: number) => {
      return paddingTop + chartHeight - ((price - minPrice) / (maxPrice - minPrice)) * chartHeight;
    };

    // Professional Neon Colors for High Contrast Dark Mode
    const colorBullish = "#10b981"; // Emerald Green
    const colorBearish = "#f43f5e"; // Bright Rose Red
    const colorEntry = "#9ca3af";   // Medium Gray
    const colorGrid = "#27272a";    // Dark zinc grid lines
    const colorText = "#f4f4f5";    // Zinc 100 white text

    return (
      /* Responsive Horizontal Scroll Container (Minimum 1500px width to allow scroll/drag pan) */
      <div ref={scrollRef} className="overflow-x-auto border border-apex-border bg-apex-bgSecondary rounded p-2 select-none scrollbar-thin scrollbar-thumb-apex-border scrollbar-track-transparent">
        <div className="min-w-[1500px] w-full">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
            {/* Grid lines */}
            {[0, 0.25, 0.5, 0.75, 1.0].map((ratio, idx) => {
              const price = minPrice + ratio * (maxPrice - minPrice);
              const y = getY(price);
              return (
                <g key={idx} opacity={0.35}>
                  <line x1={paddingLeft} y1={y} x2={width - paddingRight} y2={y} stroke={colorGrid} strokeWidth={0.5} />
                  <text x={width - paddingRight + 5} y={y + 3} fill={colorText} fontSize={9} fontFamily="monospace">
                    ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </text>
                </g>
              );
            })}

            {/* Draw R:R shaded blocks */}
            {selectedSignal && (
              <>
                {selectedSignal.side === 'BUY' ? (
                  <>
                    {/* TP Green Zone */}
                    <rect 
                      x={paddingLeft} 
                      y={getY(tpPrice)} 
                      width={chartWidth} 
                      height={Math.abs(getY(entryPrice) - getY(tpPrice))} 
                      fill={colorBullish} 
                      opacity={0.08} 
                    />
                    {/* SL Red Zone */}
                    <rect 
                      x={paddingLeft} 
                      y={getY(entryPrice)} 
                      width={chartWidth} 
                      height={Math.abs(getY(slPrice) - getY(entryPrice))} 
                      fill={colorBearish} 
                      opacity={0.08} 
                    />
                  </>
                ) : (
                  <>
                    {/* TP Green Zone for Sell (TP is below Entry) */}
                    <rect 
                      x={paddingLeft} 
                      y={getY(entryPrice)} 
                      width={chartWidth} 
                      height={Math.abs(getY(tpPrice) - getY(entryPrice))} 
                      fill={colorBullish} 
                      opacity={0.08} 
                    />
                    {/* SL Red Zone for Sell (SL is above Entry) */}
                    <rect 
                      x={paddingLeft} 
                      y={getY(slPrice)} 
                      width={chartWidth} 
                      height={Math.abs(getY(entryPrice) - getY(slPrice))} 
                      fill={colorBearish} 
                      opacity={0.08} 
                    />
                  </>
                )}
              </>
            )}

            {/* Reference Targets Horizontal Lines */}
            {selectedSignal && (
              <g>
                {/* Entry Line */}
                <line 
                  x1={paddingLeft} 
                  y1={getY(entryPrice)} 
                  x2={width - paddingRight} 
                  y2={getY(entryPrice)} 
                  stroke={colorEntry} 
                  strokeDasharray="4,4" 
                  strokeWidth={1} 
                />
                <rect x={width - paddingRight + 5} y={getY(entryPrice) - 7} width={85} height={14} fill="#18181b" rx={2} stroke="var(--color-border)" strokeWidth={0.5} />
                <text x={width - paddingRight + 8} y={getY(entryPrice) + 3} fill={colorText} fontSize={8.5} fontWeight="bold" fontFamily="monospace">
                  ENT: ${entryPrice.toLocaleString()}
                </text>

                {/* Take Profit Line */}
                <line 
                  x1={paddingLeft} 
                  y1={getY(tpPrice)} 
                  x2={width - paddingRight} 
                  y2={getY(tpPrice)} 
                  stroke={colorBullish} 
                  strokeDasharray="4,4" 
                  strokeWidth={1.2} 
                />
                <rect x={width - paddingRight + 5} y={getY(tpPrice) - 7} width={85} height={14} fill="#064e3b" rx={2} stroke={colorBullish} strokeWidth={0.5} />
                <text x={width - paddingRight + 8} y={getY(tpPrice) + 3} fill="#a7f3d0" fontSize={8.5} fontWeight="bold" fontFamily="monospace">
                  TGT: ${tpPrice.toLocaleString()}
                </text>

                {/* Stop Loss Line */}
                <line 
                  x1={paddingLeft} 
                  y1={getY(slPrice)} 
                  x2={width - paddingRight} 
                  y2={getY(slPrice)} 
                  stroke={colorBearish} 
                  strokeDasharray="4,4" 
                  strokeWidth={1.2} 
                />
                <rect x={width - paddingRight + 5} y={getY(slPrice) - 7} width={85} height={14} fill="#4c0519" rx={2} stroke={colorBearish} strokeWidth={0.5} />
                <text x={width - paddingRight + 8} y={getY(slPrice) + 3} fill="#fecdd3" fontSize={8.5} fontWeight="bold" fontFamily="monospace">
                  STP: ${slPrice.toLocaleString()}
                </text>
              </g>
            )}

            {/* Entry / Exit Candlestick Markers & Dotted Timelines */}
            {selectedSignal && klines.map((k, idx) => {
              const x = getX(idx);
              const yLow = getY(k.low);
              const yHigh = getY(k.high);

              // 15-minute candle timestamp validation
              const isEntryCandle = k.timestamp && selectedSignal.timestamp && 
                selectedSignal.timestamp >= k.timestamp && 
                selectedSignal.timestamp < k.timestamp + 900;

              const isExitCandle = selectedSignal.exit_timestamp && k.timestamp && 
                selectedSignal.exit_timestamp >= k.timestamp && 
                selectedSignal.exit_timestamp < k.timestamp + 900;

              return (
                <g key={`marker-timeline-${idx}`}>
                  {isEntryCandle && (
                    <g>
                      {/* Vertical entry dotted line */}
                      <line x1={x} y1={paddingTop} x2={x} y2={height - paddingBottom} stroke="#10b981" strokeWidth={1} strokeDasharray="3,3" opacity={0.65} />
                      
                      {/* Marker shape depending on trade side */}
                      {selectedSignal.side === 'BUY' ? (
                        <path d={`M ${x} ${yLow + 12} L ${x - 5} ${yLow + 20} L ${x + 5} ${yLow + 20} Z`} fill="#10b981" />
                      ) : (
                        <path d={`M ${x} ${yHigh - 12} L ${x - 5} ${yHigh - 20} L ${x + 5} ${yHigh - 20} Z`} fill="#f43f5e" />
                      )}
                      
                      {/* Entry text label */}
                      <text 
                        x={x} 
                        y={selectedSignal.side === 'BUY' ? yLow + 30 : yHigh - 24} 
                        fill="#10b981" 
                        fontSize={8} 
                        fontWeight="bold" 
                        fontFamily="monospace" 
                        textAnchor="middle"
                      >
                        ENTRY
                      </text>
                    </g>
                  )}

                  {isExitCandle && (
                    <g>
                      {/* Vertical exit dotted line */}
                      <line x1={x} y1={paddingTop} x2={x} y2={height - paddingBottom} stroke="#f43f5e" strokeWidth={1} strokeDasharray="3,3" opacity={0.65} />
                      
                      {/* Exit Circle Marker */}
                      <circle cx={x} cy={selectedSignal.status?.includes('TP') ? yHigh - 12 : yLow + 12} r={4.5} fill="#f43f5e" />
                      
                      {/* Exit text label */}
                      <text 
                        x={x} 
                        y={selectedSignal.status?.includes('TP') ? yHigh - 22 : yLow + 26} 
                        fill="#f43f5e" 
                        fontSize={8} 
                        fontWeight="bold" 
                        fontFamily="monospace" 
                        textAnchor="middle"
                      >
                        EXIT ({selectedSignal.status?.includes('TP') ? 'TP' : 'SL'})
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* Candlesticks */}
            {klines.map((k, idx) => {
              const x = getX(idx);
              const yOpen = getY(k.open);
              const yClose = getY(k.close);
              const yHigh = getY(k.high);
              const yLow = getY(k.low);

              const isBullish = k.close >= k.open;
              const candleColor = isBullish ? colorBullish : colorBearish;
              const bodyHeight = Math.max(1.5, Math.abs(yClose - yOpen));
              const bodyY = Math.min(yOpen, yClose);
              const barWidth = Math.max(4, (chartWidth / klines.length) * 0.75);

              return (
                <g key={`candle-${idx}`}>
                  {/* Wick line */}
                  <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={candleColor} strokeWidth={1} />
                  {/* Real body */}
                  <rect 
                    x={x - barWidth / 2} 
                    y={bodyY} 
                    width={barWidth} 
                    height={bodyHeight} 
                    fill={candleColor} 
                    stroke={candleColor}
                    strokeWidth={0.5}
                  />
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 shrink-0">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Zap className="w-5 h-5 text-apex-accent animate-pulse" />
          <span>APEX AUTONOMOUS AI SIGNAL WORKSPACE (2-HOUR CYCLE)</span>
        </div>
        <div className="flex items-center gap-3">
          {(loading || loadingHist) && (
            <div className="flex items-center gap-1 text-apex-muted text-[10px] animate-pulse">
              <Activity className="w-3 h-3 animate-spin" /> FETCHING QUANT MATRIX...
            </div>
          )}
          {lastUpdate && (
            <div className="text-[10px] text-apex-muted">
              Last Sync: {lastUpdate.toLocaleTimeString()}
            </div>
          )}
          <button 
            onClick={() => { fetchLiveSignals(); fetchHistory(); }}
            className="flex items-center gap-1 px-2.5 py-1 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border rounded text-apex-text text-[10px] transition-colors"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
          <div className="text-[11px] text-apex-ai font-bold flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-apex-ai" /> GEMINI 2.5 FLASH ACTIVE
          </div>
        </div>
      </div>

      {/* Main Workspace split */}
      <div className="flex-1 flex flex-col md:flex-row gap-4 overflow-hidden">
        
        {/* Left Side: Active Signals Panel */}
        <div className="w-full md:w-3/5 flex flex-col overflow-hidden space-y-3">
          <div className="flex items-center justify-between font-bold text-apex-muted uppercase text-[10px] tracking-wider shrink-0">
            <span>ACTIVE LIVE SIGNALS (CLICK CARD FOR DETAILS &amp; CHART)</span>
            <span className="text-apex-accent">3 Target Pairs</span>
          </div>

          <div className="flex-1 overflow-y-auto grid grid-cols-1 xl:grid-cols-2 gap-4 auto-rows-max pr-1">
            {signals.map((sig) => {
              const verif = sig.verification ?? [];
              const passes = sig.passedFactors ?? verif.filter(v => v.passed).length;
              const total  = sig.totalFactors  ?? verif.length;
              const ind    = sig.indicators ?? {};
              return (
                <div 
                  key={sig.id} 
                  onClick={() => setSelectedSignal(sig)}
                  className="workstation-panel p-3.5 flex flex-col justify-between space-y-3 cursor-pointer hover:border-apex-accent transition-all group"
                >
                  {/* Top Bar */}
                  <div className="flex items-center justify-between border-b border-apex-border group-hover:border-apex-accent/40 pb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-sm text-apex-text">{sig.symbol}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 ${
                        sig.side === 'BUY'
                          ? 'bg-apex-success/15 text-apex-success border border-apex-success/30'
                          : 'bg-apex-danger/15 text-apex-danger border border-apex-danger/30'
                      }`}>
                        <SideIcon side={sig.side} />
                        {sig.side} ({sig.timeframe})
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-apex-muted">{sig.formatted_time?.split(' ')[1] || ''}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold flex items-center gap-1 ${
                        sig.status === 'CONFIRMED'
                          ? 'bg-apex-success/15 text-apex-success border border-apex-success/30'
                          : 'bg-apex-warning/15 text-apex-warning border border-apex-warning/30'
                      }`}>
                        <CheckCircle2 className="w-3 h-3" /> {sig.status}
                      </span>
                    </div>
                  </div>

                  {/* Price Targets & RR */}
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="p-2 bg-apex-bg rounded border border-apex-border group-hover:bg-apex-surface/40">
                      <div className="text-apex-muted text-[9px]">ENTRY LEVEL</div>
                      <div className="font-bold text-apex-text">${sig.entry.toLocaleString()}</div>
                    </div>
                    <div className="p-2 bg-apex-bg rounded border border-apex-border group-hover:bg-apex-surface/40">
                      <div className="text-apex-muted text-[9px]">STOP LOSS</div>
                      <div className="font-bold text-apex-danger">${sig.sl.toLocaleString()}</div>
                    </div>
                    <div className="p-2 bg-apex-bg rounded border border-apex-border group-hover:bg-apex-surface/40">
                      <div className="text-apex-muted text-[9px]">TAKE PROFIT</div>
                      <div className="font-bold text-apex-success">${sig.tp.toLocaleString()}</div>
                    </div>
                    <div className="p-2 bg-apex-bg rounded border border-apex-border group-hover:bg-apex-surface/40">
                      <div className="text-apex-muted text-[9px]">ESTIMATED R:R</div>
                      <div className="font-bold text-apex-accent">1 : {sig.rr.toFixed(2)}</div>
                    </div>
                  </div>

                  {/* Indicator Snapshot */}
                  {ind.rsi !== undefined && (
                    <div className="grid grid-cols-3 gap-1 text-[9px] font-mono">
                      <div className="p-1.5 bg-apex-bg/60 rounded border border-apex-border/40">
                        <div className="text-apex-muted">RSI 14</div>
                        <div className={`font-bold ${ind.rsi! < 35 ? 'text-apex-success' : ind.rsi! > 65 ? 'text-apex-danger' : 'text-apex-text'}`}>
                          {ind.rsi?.toFixed(1)}
                        </div>
                      </div>
                      <div className="p-1.5 bg-apex-bg/60 rounded border border-apex-border/40">
                        <div className="text-apex-muted">ATR</div>
                        <div className="font-bold text-apex-text">{ind.atr?.toFixed(2)}</div>
                      </div>
                      <div className="p-1.5 bg-apex-bg/60 rounded border border-apex-border/40">
                        <div className="text-apex-muted">VOL Δ</div>
                        <div className={`font-bold ${(ind.volumeDelta ?? 0) > 0 ? 'text-apex-success' : 'text-apex-danger'}`}>
                          {(ind.volumeDelta ?? 0) > 0 ? '+' : ''}{ind.volumeDelta?.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Interactive Button */}
                  <div className="flex items-center justify-between text-[10px] text-apex-accent font-bold pt-1.5 border-t border-apex-border/30">
                    <span className="flex items-center gap-0.5"><Sparkles className="w-3 h-3" /> View Interactive Chart</span>
                    <ChevronRight className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              );
            })}

            {signals.length === 0 && !loading && (
              <div className="col-span-2 flex items-center justify-center py-12 text-apex-muted">
                <div className="text-center space-y-2">
                  <Activity className="w-8 h-8 mx-auto animate-pulse text-apex-ai" />
                  <p className="text-sm font-bold">GEMINI AI RUNNING 2-HOUR INTERVALS...</p>
                  <p className="text-[11px]">No active signals generated yet. Next update shortly.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Signals Log History (Last 2 Months) */}
        <div className="w-full md:w-2/5 flex flex-col overflow-hidden space-y-3">
          <div className="flex items-center justify-between font-bold text-apex-muted uppercase text-[10px] tracking-wider shrink-0">
            <span className="flex items-center gap-1">
              <History className="w-3.5 h-3.5 text-apex-accent" /> APEX SIGNALS HISTORY LOG (LAST 60 DAYS)
            </span>
            <span className="text-apex-muted">{history.length} Saved</span>
          </div>

          <div className="flex-1 workstation-panel overflow-hidden p-2 flex flex-col justify-between">
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {history.map((hItem, idx) => (
                <div 
                  key={hItem.id || idx} 
                  onClick={() => setSelectedSignal(hItem)}
                  className="p-2.5 bg-apex-bg/40 hover:bg-apex-bg border border-apex-border/60 hover:border-apex-accent rounded text-[10.5px] transition-all flex flex-col space-y-1.5 cursor-pointer"
                >
                  {/* Top line info */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-apex-text text-[11px]">{hItem.symbol}</span>
                      <span className={`px-1.5 py-0.5 rounded-[3px] text-[9px] font-bold flex items-center gap-0.5 ${
                        hItem.side === 'BUY' 
                          ? 'bg-apex-success/10 text-apex-success border border-apex-success/20' 
                          : 'bg-apex-danger/10 text-apex-danger border border-apex-danger/20'
                      }`}>
                        {hItem.side}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`px-1.5 py-0.2 rounded text-[8px] font-bold ${
                        hItem.status?.includes('TP') 
                          ? 'bg-apex-success/15 text-apex-success' 
                          : hItem.status?.includes('SL') 
                          ? 'bg-apex-danger/15 text-apex-danger' 
                          : 'bg-apex-warning/15 text-apex-warning'
                      }`}>
                        {hItem.status}
                      </span>
                      <span className="text-[9px] text-apex-muted">{hItem.formatted_time || 'N/A'}</span>
                    </div>
                  </div>

                  {/* Pricing and accuracy */}
                  <div className="grid grid-cols-4 gap-1 text-[9.5px] font-mono text-apex-textSecondary">
                    <div>Entry: <span className="font-bold text-apex-text">${hItem.entry.toLocaleString()}</span></div>
                    <div>SL: <span className="font-bold text-apex-danger">${hItem.sl.toLocaleString()}</span></div>
                    <div>TP: <span className="font-bold text-apex-success">${hItem.tp.toLocaleString()}</span></div>
                    <div className="text-right">Score: <span className="font-bold text-apex-ai">{hItem.aiScore}%</span></div>
                  </div>
                </div>
              ))}

              {history.length === 0 && !loadingHist && (
                <div className="flex flex-col items-center justify-center py-20 text-apex-muted space-y-2">
                  <History className="w-8 h-8 opacity-40 text-apex-accent animate-pulse" />
                  <p className="font-bold">No historical records found</p>
                  <p className="text-[10px] max-w-[200px] text-center">Historical logs populate automatically on every 2-hour update.</p>
                </div>
              )}
            </div>
            
            {/* Purge / Retention Info */}
            <div className="mt-2 pt-2 border-t border-apex-border/30 text-[9px] text-apex-muted flex items-center justify-between shrink-0">
              <span>Automatic Retention: 60 Days</span>
              <span className="flex items-center gap-0.5 text-apex-success">
                <CheckCircle2 className="w-3 h-3 text-apex-success" /> DB Purge Active
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* Modal Dialog for Chart and Signal Details */}
      {selectedSignal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          {/* Main Modal container made wider and larger: max-w-5xl */}
          <div className="bg-apex-bgSecondary border border-apex-border rounded-lg max-w-5xl w-full flex flex-col overflow-hidden max-h-[95vh] shadow-2xl">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between p-3.5 border-b border-apex-border bg-apex-bg shrink-0">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-apex-text">{selectedSignal.symbol}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 ${
                  selectedSignal.side === 'BUY'
                    ? 'bg-apex-success/15 text-apex-success border border-apex-success/30'
                    : 'bg-apex-danger/15 text-apex-danger border border-apex-danger/30'
                }`}>
                  <SideIcon side={selectedSignal.side} />
                  {selectedSignal.side} (M15)
                </span>
                <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                  selectedSignal.status?.includes('TP') 
                    ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' 
                    : selectedSignal.status?.includes('SL') 
                    ? 'bg-apex-danger/15 text-apex-danger border border-apex-danger/30' 
                    : 'bg-apex-warning/15 text-apex-warning border border-apex-warning/30'
                }`}>
                  {selectedSignal.status}
                </span>
              </div>
              <button 
                onClick={() => setSelectedSignal(null)}
                className="text-apex-muted hover:text-apex-text p-1 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              
              {/* Large Candlestick Chart Area */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[10px] text-apex-muted uppercase font-bold px-1">
                  <span>Interactive SMC Target Chart (Scroll horizontally to view older candles)</span>
                  <span>15m Candles</span>
                </div>
                {renderSVGChart()}
              </div>

              {/* Price Targets, R:R, and Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px] shrink-0">
                <div className="p-2.5 bg-apex-bg border border-apex-border rounded">
                  <span className="text-apex-muted text-[9px] block">ENTRY LEVEL</span>
                  <span className="font-bold text-apex-text block text-sm">${selectedSignal.entry.toLocaleString()}</span>
                </div>
                <div className="p-2.5 bg-apex-bg border border-apex-border rounded">
                  <span className="text-apex-muted text-[9px] block">STOP LOSS</span>
                  <span className="font-bold text-apex-danger block text-sm">${selectedSignal.sl.toLocaleString()}</span>
                </div>
                <div className="p-2.5 bg-apex-bg border border-apex-border rounded">
                  <span className="text-apex-muted text-[9px] block">TAKE PROFIT</span>
                  <span className="font-bold text-apex-success block text-sm">${selectedSignal.tp.toLocaleString()}</span>
                </div>
                <div className="p-2.5 bg-apex-bg border border-apex-border rounded">
                  <span className="text-apex-muted text-[9px] block">ESTIMATED RISK REWARD</span>
                  <span className="font-bold text-apex-accent block text-sm">1 : {selectedSignal.rr.toFixed(2)}</span>
                </div>
              </div>

              {/* Split Details: Factors & Rationale */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 shrink-0">
                
                {/* Left Side: Rationale & Indicators */}
                <div className="space-y-3">
                  <div className="p-3 bg-apex-ai/10 border border-apex-ai/20 rounded font-sans text-xs space-y-2">
                    <div className="text-[10px] font-mono text-apex-ai font-bold flex items-center gap-1">
                      <Sparkles className="w-3.5 h-3.5 text-apex-ai" /> AI Signal Rationale
                    </div>
                    <p className="text-apex-textSecondary leading-relaxed">
                      {selectedSignal.reasoning || selectedSignal.aiNotes}
                    </p>
                  </div>

                  {/* Technical values */}
                  {selectedSignal.indicators && (
                    <div className="p-2.5 bg-apex-bg border border-apex-border rounded space-y-2">
                      <div className="text-[10px] text-apex-muted uppercase font-bold border-b border-apex-border/40 pb-1 flex items-center gap-1">
                        <Info className="w-3.5 h-3.5" /> Technical Indicators Snapshot
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-[10px]">
                        <div>RSI (14): <span className="font-bold text-apex-text">{selectedSignal.indicators.rsi?.toFixed(2)}</span></div>
                        <div>ATR (14): <span className="font-bold text-apex-text">${selectedSignal.indicators.atr?.toFixed(2)}</span></div>
                        <div>Volume Delta: <span className="font-bold text-apex-text">{selectedSignal.indicators.volumeDelta?.toFixed(2)}%</span></div>
                        <div>Trend (15m): <span className={`font-bold ${selectedSignal.indicators.trend?.includes('BULLISH') ? 'text-apex-success' : 'text-apex-danger'}`}>{selectedSignal.indicators.trend}</span></div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Side: Verification Audit */}
                {selectedSignal.verification && (
                  <div className="p-3 bg-apex-bg border border-apex-border rounded space-y-3 flex flex-col justify-between">
                    <div>
                      <div className="text-[10px] text-apex-muted uppercase font-bold border-b border-apex-border/40 pb-1 flex justify-between">
                        <span>8-Factor Verification Details</span>
                        <span className="text-apex-ai font-bold">Accuracy: {selectedSignal.aiScore}%</span>
                      </div>
                      <div className="grid grid-cols-1 gap-2 pt-2 text-[10px]">
                        {selectedSignal.verification.map((v, i) => (
                          <div key={i} className="flex items-center justify-between border-b border-apex-border/20 pb-1">
                            <span className="text-apex-textSecondary">{v.label}</span>
                            <span className={`font-bold ${v.passed ? 'text-apex-success' : 'text-apex-danger'}`}>
                              {v.passed ? 'PASSED' : 'FAILED'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="pt-2 border-t border-apex-border/40 flex justify-between font-bold text-[10.5px]">
                      <span>Confluence Success Rate:</span>
                      <span className="text-apex-accent">{selectedSignal.probability}%</span>
                    </div>
                  </div>
                )}

              </div>

            </div>

            {/* Modal Footer */}
            <div className="p-3.5 bg-apex-bg border-t border-apex-border flex items-center justify-between text-[10px] text-apex-muted shrink-0">
              <span>Signal ID: {selectedSignal.id}</span>
              <button 
                onClick={() => setSelectedSignal(null)}
                className="px-5 py-1.5 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border text-apex-text font-bold rounded-btn transition-colors"
              >
                Close Details
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
