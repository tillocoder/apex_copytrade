import React, { useEffect, useState, useMemo } from 'react';
import type { Position } from '../../types';
import { ApexCandleChart } from '../common/ApexCandleChart';
import { 
  Target, 
  Activity, 
  RefreshCw, 
  Zap, 
  ArrowUpRight,
  ArrowDownRight,
  ShieldAlert
} from 'lucide-react';

export const TelegramLivePositionView: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [liveBinancePrice, setLiveBinancePrice] = useState<number | null>(null);

  // Extract pos_id from URL query string
  const urlParams = new URLSearchParams(window.location.search);
  const targetPosId = urlParams.get('pos');
  const targetSymbol = urlParams.get('symbol') || 'BTC/USDT';

  // Fetch live positions from backend
  const fetchLivePositions = async () => {
    try {
      const res = await fetch('https://apex.xrinvest.uz/api/v1/positions/live');
      if (res.ok) {
        const data = await res.json();
        setPositions(Array.isArray(data) ? data : []);
      }
      setLastUpdated(new Date());
    } catch (e) {
      console.error('Failed to fetch positions:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLivePositions();
    const interval = setInterval(fetchLivePositions, 2000);
    return () => clearInterval(interval);
  }, []);

  // Find target position or fallback to first open position
  const currentPos = useMemo(() => {
    if (targetPosId) {
      const found = positions.find(p => p.id === targetPosId);
      if (found) return found;
    }
    if (positions.length > 0) {
      return positions[0];
    }
    return null;
  }, [positions, targetPosId]);

  const sym = currentPos?.symbol || targetSymbol;
  const cleanSym = sym.replace('/', '').toUpperCase();

  // Connect direct live WebSocket to Binance for tick-by-tick mark price
  useEffect(() => {
    const ws = new WebSocket(`wss://stream.binance.com:9443/ws/${cleanSym.toLowerCase()}@ticker`);
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg && msg.c) {
          setLiveBinancePrice(parseFloat(msg.c));
        }
      } catch (e) {
        // ignore
      }
    };
    return () => {
      try { ws.close(); } catch (_) {}
    };
  }, [cleanSym]);

  const entry = Number(currentPos?.entryPrice || 0);
  const mark = liveBinancePrice || Number(currentPos?.currentPrice || entry);
  const sl = Number(currentPos?.sl || 0);
  const tp1 = Number(currentPos?.tp1 || 0);
  const isBuy = (currentPos?.side || 'BUY').toUpperCase() === 'BUY';
  const size = Number(currentPos?.size || 0.05);
  const margin = Number(currentPos?.marginUsed || 1000);

  // Compute live floating PnL
  const pnl = entry > 0 
    ? (isBuy ? (mark - entry) * size : (entry - mark) * size)
    : Number(currentPos?.unrealizedPnl || 0);
  const pnlPct = margin > 0 ? (pnl / margin) * 100 : 0;
  const isProfit = pnl >= 0;

  // Calculate distance to TP1 and SL
  const distToTp1 = tp1 > 0 ? Math.abs(tp1 - mark) : 0;
  const distToSl = sl > 0 ? Math.abs(mark - sl) : 0;

  // Progress gauge (0 to 100%)
  const totalRange = Math.abs(tp1 - sl);
  const progressToTp1 = totalRange > 0 
    ? Math.max(0, Math.min(100, isBuy ? ((mark - sl) / totalRange) * 100 : ((sl - mark) / totalRange) * 100))
    : 50;

  return (
    <div className="min-h-screen bg-[#080A0D] text-[#F3F4F6] font-sans antialiased pb-6 select-none flex flex-col">
      {/* 1. TOP TELEGRAM WEBAPP HEADER */}
      <header className="px-4 py-2.5 bg-[#0D1117] border-b border-[#1E293B] sticky top-0 z-50 flex items-center justify-between shadow-md">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <div>
            <div className="text-[9px] font-mono tracking-widest text-emerald-400 font-bold uppercase">
              PROP 10K // LIVE
            </div>
            <div className="text-xs font-black tracking-tight text-white flex items-center gap-1.5">
              <span>{sym}</span>
              <span className={`px-1.5 py-0.2 text-[9px] font-bold rounded ${isBuy ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'}`}>
                {isBuy ? 'BUY' : 'SELL'} {currentPos?.leverage || 2}X
              </span>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className={`text-base font-black font-mono tracking-tight leading-none ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isProfit ? '+' : ''}${pnl.toFixed(2)} USD
          </div>
          <div className={`text-[10px] font-mono font-bold mt-0.5 ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
            {isProfit ? '+' : ''}{pnlPct.toFixed(2)}% PnL
          </div>
        </div>
      </header>

      {/* 2. SPATIOUS FULL-HEIGHT CANDLESTICK CHART */}
      <div className="px-2 pt-2 pb-1">
        <div className="bg-[#131722] border border-[#1E293B] rounded-xl overflow-hidden shadow-2xl">
          {/* Chart Header Bar */}
          <div className="px-3 py-1.5 bg-[#181C27] border-b border-[#2A2E39] flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
              <span className="font-bold text-slate-200 text-[11px] uppercase tracking-wider">
                {sym} M15
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-300 font-bold flex items-center gap-1">
              <span className="text-slate-500 text-[9px] font-normal">MARK:</span>
              <span className="text-amber-400">${mark.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
          </div>

          {/* Clean Full-Height Canvas Container (No ugly text squeeze!) */}
          <div className="h-[360px] w-full relative">
            <ApexCandleChart 
              symbol={sym}
              position={currentPos}
              defaultTimeframe="15m"
              hideHeader={true}
              className="h-full w-full"
            />
          </div>

          {/* Clean Compact Price Targets Footer */}
          <div className="px-3 py-1.5 bg-[#0F141C] border-t border-[#1E293B] flex items-center justify-between text-[10px] font-mono">
            <div className="text-blue-400 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              <span>ENTRY ${entry.toFixed(2)}</span>
            </div>
            <div className="text-emerald-400 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>TP1 ${tp1.toFixed(2)}</span>
            </div>
            <div className="text-rose-400 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
              <span>SL ${sl.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. TRADE TARGET PROGRESS GAUGE */}
      <div className="px-2 pt-1 pb-2">
        <div className="p-3 bg-[#0D1117] border border-[#1E293B] rounded-xl shadow-md space-y-1.5">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-slate-400 font-semibold flex items-center gap-1">
              <Target className="w-3.5 h-3.5 text-emerald-400" />
              <span>Take Profit 1 Gacha:</span>
            </span>
            <span className="font-bold text-emerald-400">
              ${distToTp1.toFixed(2)} masofa qoldi
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-[#1A2230] h-2 rounded-full overflow-hidden p-0.5 relative">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${isProfit ? 'bg-gradient-to-r from-emerald-500 to-teal-400' : 'bg-gradient-to-r from-rose-500 to-amber-500'}`}
              style={{ width: `${progressToTp1}%` }}
            />
          </div>

          <div className="flex justify-between text-[9px] font-mono text-slate-500">
            <span>SL: ${sl.toFixed(2)}</span>
            <span className="text-slate-400 font-bold">Hozirgi: ${mark.toFixed(2)}</span>
            <span className="text-emerald-400">TP1: ${tp1.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* 4. INSTITUTIONAL TELEMETRY 4-GRID */}
      <div className="px-2 pb-2 grid grid-cols-2 gap-1.5 text-xs font-mono">
        <div className="p-2.5 bg-[#0D1117] border border-[#1E293B] rounded-xl space-y-0.5">
          <div className="text-[9px] text-slate-500 uppercase font-semibold">Kirish / Hozirgi</div>
          <div className="text-white font-bold">${entry.toFixed(2)}</div>
          <div className={`text-[10px] font-bold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
            ${mark.toFixed(2)} ({isProfit ? '+' : ''}{pnlPct.toFixed(2)}%)
          </div>
        </div>

        <div className="p-2.5 bg-[#0D1117] border border-[#1E293B] rounded-xl space-y-0.5">
          <div className="text-[9px] text-slate-500 uppercase font-semibold">Hajm / Margin</div>
          <div className="text-white font-bold">{size} {sym.split('/')[0]}</div>
          <div className="text-[10px] text-slate-400 font-semibold">${margin.toFixed(2)} USD</div>
        </div>

        <div className="p-2.5 bg-[#0D1117] border border-emerald-900/30 bg-emerald-950/10 rounded-xl space-y-0.5">
          <div className="text-[9px] text-emerald-400 uppercase font-semibold flex items-center gap-1">
            <ArrowUpRight className="w-3 h-3" />
            <span>Kutilayotgan TP1</span>
          </div>
          <div className="text-emerald-400 font-bold">${tp1.toFixed(2)}</div>
          <div className="text-[10px] text-emerald-500 font-semibold">
            +${(currentPos?.expectedProfit || (Math.abs(tp1 - entry) * size)).toFixed(2)} USD (1.5R)
          </div>
        </div>

        <div className="p-2.5 bg-[#0D1117] border border-rose-900/30 bg-rose-950/10 rounded-xl space-y-0.5">
          <div className="text-[9px] text-rose-400 uppercase font-semibold flex items-center gap-1">
            <ArrowDownRight className="w-3 h-3" />
            <span>Maksimal Risk (SL)</span>
          </div>
          <div className="text-rose-400 font-bold">${sl.toFixed(2)}</div>
          <div className="text-[10px] text-rose-500 font-semibold">
            -${(currentPos?.expectedLoss || (Math.abs(entry - sl) * size)).toFixed(2)} USD (0.13%)
          </div>
        </div>
      </div>

      {/* 5. AI STRATEGY & SMC REASONING */}
      <div className="px-2 pb-2">
        <div className="p-3 bg-[#0D1117] border border-[#1E293B] rounded-xl space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-purple-400" />
              <span className="text-[10px] font-bold text-purple-300 uppercase tracking-wide">
                SMC Strategiya & Kvant Tahlili
              </span>
            </div>
            <span className="px-1.5 py-0.2 bg-purple-500/20 text-purple-300 text-[9px] font-mono font-bold rounded border border-purple-500/30">
              Score: {currentPos?.aiConfidence || 77.9}%
            </span>
          </div>

          <p className="text-[10px] text-slate-300 leading-relaxed font-sans">
            {currentPos?.aiExplanation || "Senior Institutional Analysis: LIQUIDITY_SWEEP in M15 Intraday structure confirmed with 77.9% quantitative confluence and 2.80 R:R."}
          </p>
        </div>
      </div>

      {/* 6. BOTTOM STATUS TICKER */}
      <div className="mt-auto px-4 text-center">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#0D1117] border border-[#1E293B] rounded-full text-[9px] font-mono text-slate-400">
          <RefreshCw className="w-2.5 h-2.5 text-emerald-400 animate-spin" />
          <span>Binance Feed: {lastUpdated.toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
};
