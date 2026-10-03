import React, { useState, useEffect } from 'react';
import {
  X,
  TrendingUp,
  TrendingDown,
  Layers,
  BarChart3,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
  Target,
  Sparkles,
  Zap,
  Activity
} from 'lucide-react';
import { type PaperTradeRecord, PaperTradeChartModal } from './PaperTradeChartModal';

interface PaperPositionsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeLivePosition?: any;
}

export const PaperPositionsDrawer: React.FC<PaperPositionsDrawerProps> = ({
  isOpen,
  onClose,
  activeLivePosition
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'wins' | 'losses'>('all');
  const [loading, setLoading] = useState<boolean>(false);
  const [paperTrades, setPaperTrades] = useState<PaperTradeRecord[]>([]);
  const [activePaperPos, setActivePaperPos] = useState<any | null>(null);
  const [selectedTradeForChart, setSelectedTradeForChart] = useState<PaperTradeRecord | null>(null);

  const fetchPaperTrades = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/futures/paper-trades');
      if (res.ok) {
        const data = await res.json();
        if (data && data.trades) {
          setPaperTrades(data.trades);
        }
        if (data && data.activePosition) {
          setActivePaperPos(data.activePosition);
        } else if (activeLivePosition) {
          setActivePaperPos(activeLivePosition);
        }
      }
    } catch (e) {
      console.error('Failed to fetch paper trades:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchPaperTrades();
      const timer = setInterval(fetchPaperTrades, 5000);
      return () => clearInterval(timer);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Filter trades based on active tab
  const filteredTrades = paperTrades.filter((t) => {
    const pnl = Number(t.pnl !== undefined ? t.pnl : t.unrealizedPnl || 0);
    if (activeTab === 'wins') return pnl > 0;
    if (activeTab === 'losses') return pnl < 0;
    return true;
  });

  const totalWins = paperTrades.filter((t) => Number(t.pnl || 0) > 0).length;
  const totalLosses = paperTrades.filter((t) => Number(t.pnl || 0) < 0).length;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 animate-in fade-in">
      <div className="w-full max-w-5xl bg-[#070B14] border border-[#1C2E52] rounded-2xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden">
        
        {/* 1. DRAWER HEADER */}
        <div className="p-4 sm:px-6 bg-[#0A1224] border-b border-[#1C2E52] flex items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 text-cyan-400 flex items-center justify-center font-bold">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-1">
                <h2 className="text-base sm:text-lg font-black font-mono text-white">
                  24-SOATLIK REALTIME PAPER TEST POZITSIYALARI
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  100% XAVFSIZ SIMULYATSIYA
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/35">
                  REAL HISOBDAN AJRATILGAN
                </span>
              </div>
              <p className="text-xs text-[#9CA3AF] font-sans mt-0.5">
                Binance Futures ETHUSDT M5 24-soatlik jonli paper test sessiyasida ochilgan pozitsiyalar
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={fetchPaperTrades}
              disabled={loading}
              className="p-2 rounded-xl bg-[#0C152B] hover:bg-[#162544] border border-[#1C2E52] text-[#9CA3AF] hover:text-white transition-all cursor-pointer"
              title="Qayta yuklash"
            >
              <RotateCcw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-[#0C152B] hover:bg-[#162544] border border-[#1C2E52] text-[#9CA3AF] hover:text-white transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 2. LIVE ACTIVE PAPER POSITION CARD */}
        <div className="p-4 sm:px-6 bg-[#080E1D] border-b border-[#1C2E52]">
          <div className="text-[11px] font-mono font-bold text-[#9CA3AF] uppercase mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>Joriy Faol Paper Pozitsiya</span>
            </span>
            <span className="text-[10px] text-cyan-400 font-normal">Realtime WebSocket Tracking</span>
          </div>

          {activePaperPos ? (
            <div className="p-3.5 bg-gradient-to-r from-[#0C1A35] via-[#0E1F42] to-[#0A162D] border border-cyan-500/50 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-lg">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    activePaperPos.side === 'LONG' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                  }`}>
                    {activePaperPos.side} 100X
                  </span>
                  <span className="font-mono font-black text-white text-sm">
                    {activePaperPos.displaySymbol || activePaperPos.symbol || 'ETHUSDT.P'}
                  </span>
                  <span className="text-xs text-[#9CA3AF] font-mono">
                    Hajm: {activePaperPos.qty} ETH
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs font-mono text-[#9CA3AF] pt-1">
                  <div>Kirish: <strong className="text-cyan-300">${(activePaperPos.entryPrice || activePaperPos.entry_price || 0).toFixed(2)}</strong></div>
                  <div>Mark: <strong className="text-white">${(activePaperPos.markPrice || activePaperPos.mark_price || 0).toFixed(2)}</strong></div>
                  <div>SL: <strong className="text-rose-400">${(activePaperPos.sl || 0).toFixed(2)}</strong></div>
                  <div>TP: <strong className="text-emerald-400">${(activePaperPos.tp || activePaperPos.tp1 || 0).toFixed(2)}</strong></div>
                </div>
              </div>

              <div className="flex items-center space-x-3 w-full md:w-auto justify-between md:justify-end">
                <div className="text-right">
                  <div className={`text-lg font-black font-mono ${
                    (activePaperPos.unrealizedPnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {(activePaperPos.unrealizedPnl || 0) >= 0 ? '+' : ''}${(activePaperPos.unrealizedPnl || 0).toFixed(2)}
                  </div>
                  <div className="text-[10.5px] font-mono text-[#9CA3AF]">
                    ROI: {(activePaperPos.roi || 0) >= 0 ? '+' : ''}{(activePaperPos.roi || 0).toFixed(1)}%
                  </div>
                </div>

                <button
                  onClick={() => setSelectedTradeForChart({
                    id: activePaperPos.id || 'active_paper',
                    symbol: activePaperPos.symbol || 'ETHUSDT',
                    displaySymbol: activePaperPos.displaySymbol || 'ETHUSDT.P',
                    side: activePaperPos.side || 'LONG',
                    entryPrice: activePaperPos.entryPrice || activePaperPos.entry_price,
                    markPrice: activePaperPos.markPrice || activePaperPos.mark_price,
                    sl: activePaperPos.sl,
                    tp: activePaperPos.tp || activePaperPos.tp1,
                    unrealizedPnl: activePaperPos.unrealizedPnl,
                    roi: activePaperPos.roi,
                    margin: activePaperPos.margin,
                    status: 'OPEN',
                    openedAt: activePaperPos.openedAt
                  })}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl text-xs font-mono transition-all cursor-pointer shadow-md shadow-cyan-900/30 flex items-center gap-1.5 shrink-0"
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  <span>CHARTNI KO'RISH</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-[#0A1224] border border-[#162544] rounded-xl text-center text-xs font-sans text-[#6B7280]">
              <span className="text-[#9CA3AF] font-bold block mb-0.5">⚪ Hozirda ochiq pozitsiya mavjud emas</span>
              Bozor skanerlanmoqda: 24/7 Barcha sessiyalar (Asia, London, NY), ADX(14) &ge; 22 va Score &ge; 72 kutilmoqda.
            </div>
          )}
        </div>

        {/* 3. FILTER TABS & STATS BAR */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-2.5 bg-[#090F1E] border-b border-[#1C2E52] text-xs font-mono">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1 rounded-lg transition-all font-bold cursor-pointer ${
                activeTab === 'all' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-[#9CA3AF] hover:text-white'
              }`}
            >
              Barchasi ({paperTrades.length})
            </button>
            <button
              onClick={() => setActiveTab('wins')}
              className={`px-3 py-1 rounded-lg transition-all font-bold cursor-pointer ${
                activeTab === 'wins' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'text-[#9CA3AF] hover:text-white'
              }`}
            >
              Yutuqli ({totalWins})
            </button>
            <button
              onClick={() => setActiveTab('losses')}
              className={`px-3 py-1 rounded-lg transition-all font-bold cursor-pointer ${
                activeTab === 'losses' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' : 'text-[#9CA3AF] hover:text-white'
              }`}
            >
              Zararli ({totalLosses})
            </button>
          </div>

          <div className="text-[11px] text-[#6B7280] hidden sm:block">
            Har bir qatorga bosib <strong className="text-cyan-400">Entry / SL / TP</strong> grafikini ko'rishingiz mumkin
          </div>
        </div>

        {/* 4. PAPER TRADES TABLE */}
        <div className="flex-1 overflow-y-auto p-4 sm:px-6 space-y-2">
          {filteredTrades.length > 0 ? (
            <div className="divide-y divide-[#162544] border border-[#162544] rounded-xl overflow-hidden bg-[#0A1224]">
              {filteredTrades.map((t, idx) => {
                const isLong = (t.side || 'LONG').toUpperCase() === 'LONG';
                const pnl = Number(t.pnl !== undefined ? t.pnl : t.unrealizedPnl || 0);
                const isWin = pnl >= 0;
                const entry = Number(t.entry_price || t.entryPrice || 0);
                const exit = Number(t.exit_price || t.exitPrice || 0);
                const sl = Number(t.sl || 0);
                const tp = Number(t.tp || t.tp1 || 0);

                return (
                  <div
                    key={t.id || idx}
                    onClick={() => setSelectedTradeForChart(t)}
                    className="p-3 hover:bg-[#0F1B38] transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono"
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                        isWin ? 'bg-emerald-500/15 border-emerald-500/35 text-emerald-400' : 'bg-rose-500/15 border-rose-500/35 text-rose-400'
                      }`}>
                        {isLong ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                      </div>

                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-2">
                          <span className={`px-1.5 py-0.2 rounded text-[9.5px] font-bold ${
                            isLong ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                          }`}>
                            {t.side} 100x
                          </span>
                          <span className="font-bold text-white">
                            {t.displaySymbol || t.symbol || 'ETHUSDT.P'}
                          </span>
                          <span className="text-[10px] text-[#6B7280]">
                            {t.opened_at || t.openedAt || '2026-09-29'}
                          </span>
                        </div>

                        {/* Levels snippet */}
                        <div className="flex items-center space-x-3 text-[10.5px] text-[#9CA3AF]">
                          <span>Kirish: <strong className="text-cyan-300">${entry.toFixed(2)}</strong></span>
                          <span>•</span>
                          <span>SL: <strong className="text-rose-400">${sl.toFixed(2)}</strong></span>
                          <span>•</span>
                          <span>TP: <strong className="text-emerald-400">${tp.toFixed(2)}</strong></span>
                          <span>•</span>
                          <span>Chiqish: <strong className="text-white">${exit.toFixed(2)}</strong></span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 justify-between md:justify-end">
                      <div className="text-right">
                        <div className={`font-black text-sm ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} USDT
                        </div>
                        <div className="text-[10px] text-[#6B7280]">
                          {t.close_reason || t.closeReason || 'Yopilgan'}
                        </div>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedTradeForChart(t);
                        }}
                        className="px-3 py-1.5 bg-[#142344] hover:bg-cyan-500/25 border border-[#203766] hover:border-cyan-500/50 text-cyan-300 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-all cursor-pointer shrink-0"
                      >
                        <BarChart3 className="w-3.5 h-3.5" />
                        <span>CHART</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-10 text-center text-[#6B7280] space-y-3 bg-[#0A1224] border border-[#162544] rounded-xl my-4">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 mx-auto flex items-center justify-center">
                <Activity className="w-6 h-6 animate-pulse" />
              </div>
              <div className="text-sm font-bold text-white font-mono uppercase tracking-wider">
                24-SOATLIK PAPER TEST SESSIYASIDA HALI YANGI SAVDO OCHILMADI
              </div>
              <p className="text-xs text-[#9CA3AF] max-w-md mx-auto leading-relaxed">
                Bozor M5 filtrlari (SuperTrend 10/2.5 + H1 EMA 200 + Breakout Hajmi &ge; 1.3x) bo'yicha uzluksiz real-time skanerlanmoqda. Shartlar to'liq mos kelganda yangi ochilgan yoki yopilgan barcha pozitsiyalar shu yerda avtomatik paydo bo'ladi.
              </p>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>Realtime Daemon Faol (Soak Test 24H)</span>
              </div>
            </div>
          )}
        </div>

        {/* 5. FOOTER NOTICE */}
        <div className="p-3 bg-[#0A1224] border-t border-[#1C2E52] px-6 flex items-center justify-between text-xs font-mono text-[#9CA3AF]">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Xavfsizlik Kafolati:</strong> Ushbu ro'yxat faqat joriy 24-soatlik Paper Test sessiyasi davomida ochilgan real-time pozitsiyalarni o'z ichiga oladi. Real hisob balansiga hech qanday ta'sir o'tkazmaydi.
            </span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#0C152B] hover:bg-[#162544] text-white rounded-lg text-xs font-bold cursor-pointer"
          >
            YOPISH
          </button>
        </div>

      </div>

      {/* ── MODAL: INTERACTIVE TRADE CHART (ENTRY / SL / TP) ──────────────── */}
      {selectedTradeForChart && (
        <PaperTradeChartModal
          trade={selectedTradeForChart}
          onClose={() => setSelectedTradeForChart(null)}
        />
      )}
    </div>
  );
};
