import React, { useEffect, useState, useMemo } from 'react';
import type { Position } from '../../types';
import { ApexCandleChart } from '../common/ApexCandleChart';
import { 
  Target, 
  Activity, 
  Zap, 
  CheckCircle2,
  XCircle
} from 'lucide-react';

export const TelegramLivePositionView: React.FC = () => {
  const [positions, setPositions] = useState<any[]>([]);
  const [targetPos, setTargetPos] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [liveBinancePrice, setLiveBinancePrice] = useState<number | null>(null);

  // Extract pos_id and symbol from URL query string
  const urlParams = new URLSearchParams(window.location.search);
  const targetPosId = urlParams.get('pos');
  const targetSymbol = urlParams.get('symbol') || 'BTC/USDT';

  // Fetch position by specific ID (covers both OPEN and CLOSED positions)
  const fetchTargetPosition = async () => {
    if (!targetPosId) return;
    try {
      const res = await fetch(`https://apex.xrinvest.uz/api/v1/positions/${targetPosId}`);
      if (res.ok) {
        const data = await res.json();
        setTargetPos(data);
      }
    } catch (e) {
      console.error('Failed to fetch target position:', e);
    }
  };

  // Fetch all live positions
  const fetchLivePositions = async () => {
    try {
      const res = await fetch('https://apex.xrinvest.uz/api/v1/positions/live');
      if (res.ok) {
        const data = await res.json();
        setPositions(Array.isArray(data) ? data : []);
      }
      if (targetPosId) {
        await fetchTargetPosition();
      }
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
  }, [targetPosId]);

  // Priority: 1) Target Pos by ID, 2) Matched open pos, 3) First open pos
  const currentPos = useMemo(() => {
    if (targetPos) return targetPos;
    if (targetPosId) {
      const found = positions.find(p => p.id === targetPosId);
      if (found) return found;
    }
    if (positions.length > 0) {
      return positions[0];
    }
    return null;
  }, [targetPos, positions, targetPosId]);

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
      ws.close();
    };
  }, [cleanSym]);

  if (loading && !currentPos) {
    return (
      <div className="min-h-screen bg-[#0a0e17] text-white flex flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-gray-400 font-mono text-sm animate-pulse">APEX Jonli Telemetriya Yuklanmoqda...</p>
      </div>
    );
  }

  // Format calculations
  const rawSide = String(currentPos?.side || currentPos?.direction || 'BUY').toUpperCase();
  const isBuy = rawSide === 'BUY' || rawSide === 'LONG';
  const side = isBuy ? 'BUY' : 'SELL';
  const entryPrice = Number(currentPos?.entryPrice || currentPos?.entry_price || 0);
  
  const statusStr = String(currentPos?.status || 'OPEN').toUpperCase();
  const isClosed = statusStr !== 'OPEN';
  const currentPrice = isClosed 
    ? Number(currentPos?.closePrice || currentPos?.currentPrice || entryPrice)
    : (liveBinancePrice || Number(currentPos?.currentPrice || entryPrice));

  const tp1 = Number(currentPos?.tp1 || currentPos?.takeProfit || 0);
  const tp2 = Number(currentPos?.tp2 || 0);
  const sl = Number(currentPos?.sl || currentPos?.stopLoss || 0);
  const size = Number(currentPos?.size || 0);
  const marginUsed = Number(currentPos?.marginUsed || currentPos?.margin || 0);

  // Realized PnL for closed vs Unrealized for open
  const pnl = isClosed 
    ? Number(currentPos?.realizedPnl ?? (isBuy ? (currentPrice - entryPrice) * size : (entryPrice - currentPrice) * size))
    : (isBuy ? (currentPrice - entryPrice) * size : (entryPrice - currentPrice) * size);

  const pnlPercent = marginUsed > 0 ? (pnl / marginUsed) * 100 : 0;
  const isProfit = pnl >= 0;

  const distanceToTp1 = isBuy ? (tp1 - currentPrice) : (currentPrice - tp1);
  const distanceToSl = isBuy ? (currentPrice - sl) : (sl - currentPrice);

  // Status Badge Helper
  const getStatusBadge = () => {
    if (!currentPos || statusStr === 'OPEN') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          JONLI FAOL
        </span>
      );
    }
    if (statusStr.includes('TP') || statusStr.includes('PROFIT')) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5" />
          YOPILGAN (FOYDA: +${Math.abs(pnl).toFixed(2)})
        </span>
      );
    }
    if (statusStr.includes('SL') || statusStr.includes('LOSS')) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1">
          <XCircle className="w-3.5 h-3.5" />
          YOPILGAN (STOP LOSS: -${Math.abs(pnl).toFixed(2)})
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-gray-500/20 text-gray-300 border border-gray-500/30">
        {statusStr}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100 flex flex-col font-sans select-none pb-8">
      {/* Header HUD Bar */}
      <div className="bg-[#0e1626]/90 backdrop-blur border-b border-slate-800/80 px-4 py-3 sticky top-0 z-20 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-emerald-400 tracking-wider font-semibold">PROP 10K // {isClosed ? 'ARXIV' : 'LIVE'}</span>
            <div className="flex items-center gap-2">
              <span className="font-black tracking-wide text-base">{sym}</span>
              <span className={`px-2 py-0.2 rounded text-[11px] font-black uppercase ${
                isBuy ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}>
                {side} {currentPos?.leverage || 2}X
              </span>
            </div>
          </div>
        </div>

        {/* Live PnL Pill */}
        <div className="flex flex-col items-end">
          <div className={`text-lg font-black font-mono flex items-center gap-0.5 ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isProfit ? '+' : ''}${pnl.toFixed(2)} <span className="text-xs font-bold">USD</span>
          </div>
          <span className={`text-[11px] font-mono font-semibold ${isProfit ? 'text-emerald-400/80' : 'text-rose-400/80'}`}>
            {isProfit ? '+' : ''}{pnlPercent.toFixed(2)}% PnL
          </span>
        </div>
      </div>

      {/* Main Container */}
      <div className="p-3.5 flex flex-col gap-3 max-w-lg mx-auto w-full">
        {/* Status Indicator Banner */}
        <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
            <span className="text-xs font-bold text-slate-300">Holat:</span>
          </div>
          {getStatusBadge()}
        </div>

        {/* Live Candlestick Canvas (Mobile Cleaned - 360px height) */}
        <div className="relative rounded-xl border border-slate-800 bg-[#090e17] overflow-hidden shadow-2xl h-[360px]">
          <ApexCandleChart 
            symbol={sym} 
            position={currentPos ? (currentPos as Position) : undefined} 
            hideHeader={true} 
          />
        </div>

        {/* Target Progress Bar */}
        <div className="bg-[#0e1626] border border-slate-800/80 rounded-xl p-3.5 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 font-semibold flex items-center gap-1">
              <Target className="w-3.5 h-3.5 text-emerald-400" /> Take Profit 1 Gacha:
            </span>
            <span className={`font-mono font-bold ${distanceToTp1 <= 0 ? 'text-emerald-400' : 'text-emerald-300'}`}>
              {distanceToTp1 <= 0 ? '🎯 TP1 Qisman Olingan!' : `$${Math.abs(distanceToTp1).toFixed(2)} masofa qoldi`}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-800/60 text-[11px] font-mono text-center">
            <div className="bg-slate-900/80 rounded p-1.5 border border-slate-800">
              <div className="text-slate-500 text-[9px] uppercase">SL: ${sl.toFixed(2)}</div>
              <div className={`font-bold ${distanceToSl > 0 ? 'text-rose-400' : 'text-rose-500'}`}>
                ${Math.abs(distanceToSl).toFixed(2)}
              </div>
            </div>

            <div className="bg-slate-900/80 rounded p-1.5 border border-slate-800">
              <div className="text-slate-500 text-[9px] uppercase">Hozirgi: ${currentPrice.toFixed(2)}</div>
              <div className="font-bold text-amber-400">${currentPrice.toFixed(2)}</div>
            </div>

            <div className="bg-slate-900/80 rounded p-1.5 border border-slate-800">
              <div className="text-slate-500 text-[9px] uppercase">TP1: ${tp1.toFixed(2)}</div>
              <div className="font-bold text-emerald-400">${tp1.toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* Position Metadata Card */}
        <div className="bg-[#0e1626] border border-slate-800/80 rounded-xl p-3.5 flex flex-col gap-2.5">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold border-b border-slate-800/60 pb-1.5">
            Savdo Parametrlari (Execution Forensics)
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Kirish Narxi:</span>
              <span className="font-mono font-bold text-slate-200">${entryPrice.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Hozirgi Narx:</span>
              <span className="font-mono font-bold text-amber-400">${currentPrice.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Hajm (Size):</span>
              <span className="font-mono font-bold text-slate-200">{size} {sym.split('/')[0]}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Band Margin:</span>
              <span className="font-mono font-bold text-slate-200">${marginUsed.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Stop Loss:</span>
              <span className="font-mono font-bold text-rose-400">${sl.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Take Profit 2:</span>
              <span className="font-mono font-bold text-emerald-400">${tp2.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Ochilgan Vaqt:</span>
              <span className="font-mono text-slate-300">{currentPos?.timeOpen || '11:18'} UTC</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">AI Ishonch:</span>
              <span className="font-mono font-bold text-emerald-400">{currentPos?.aiConfidence || 77.9}%</span>
            </div>
          </div>

          {currentPos?.aiExplanation && (
            <div className="bg-slate-900/60 rounded-lg p-2 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-1.5 mt-1">
              <Zap className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <span>{currentPos.aiExplanation}</span>
            </div>
          )}
        </div>

        {/* Footer Brand */}
        <div className="text-center text-[10px] text-slate-600 font-mono pt-1">
          APEX QUANT // @xrpropbot · High-Frequency Real Binance Stream
        </div>
      </div>
    </div>
  );
};
