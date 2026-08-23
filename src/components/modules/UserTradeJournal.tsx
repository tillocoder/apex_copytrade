import React, { useState, useEffect, useMemo } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { 
  JournalService, 
  type JournalTrade, 
  type JournalStats, 
  type NewTradeInput 
} from '../../services/journalService';
import { 
  Plus, 
  Minus, 
  Trash2, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle2, 
  User as UserIcon,
  ChevronDown,
  ChevronUp,
  Sparkles,
  RefreshCw,
  Info
} from 'lucide-react';

const EMOTIONS = [
  'Xotirjam',
  "FOMO / Ochko'zlik",
  "Qo'rquv / Ikkilanish",
  'Shoshqaloqlik',
  'Haddan ortiq ishonch',
  'Intizomli / Reja asosida'
];

export const UserTradeJournal: React.FC = () => {
  const { user } = useTerminal();
  const activeUserId = user?.id || user?.email || 'usr_apex_01';

  const [trades, setTrades] = useState<JournalTrade[]>([]);
  const [stats, setStats] = useState<JournalStats>({
    totalTrades: 0,
    winRate: 0.0,
    totalPnlPct: 0.0,
    avgRR: '—',
    currentStreak: '—',
    wins: 0,
    losses: 0
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [expandedTradeId, setExpandedTradeId] = useState<string | null>(null);
  const [showClearModal, setShowClearModal] = useState<boolean>(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState<NewTradeInput>({
    date: new Date().toISOString().slice(0, 10),
    symbol: 'BTC/USDT',
    direction: 'Long',
    riskPct: 1.5,
    entryPrice: 0,
    exitPrice: 0,
    sl: null,
    tp: null,
    emotion: 'Xotirjam',
    reason: '',
    lesson: ''
  });

  // Load trades for current active user
  const loadUserJournal = async () => {
    setLoading(true);
    try {
      const res = await JournalService.fetchUserTrades(activeUserId);
      setTrades(res.trades);
      setStats(res.stats);
    } catch (e) {
      console.error('Failed to load user journal:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUserJournal();
  }, [activeUserId]);

  // Temporary flash success message helper
  const flashMessage = (msg: string) => {
    setActionSuccessMsg(msg);
    setTimeout(() => setActionSuccessMsg(null), 3500);
  };

  // Dynamic Live PnL calculation in form
  const previewPnl = useMemo(() => {
    const entry = Number(formData.entryPrice);
    const exitP = Number(formData.exitPrice);
    if (!entry || entry <= 0 || !exitP) return null;
    const isLong = formData.direction.toLowerCase() === 'long';
    const pnl = isLong 
      ? ((exitP - entry) / entry) * 100 
      : ((entry - exitP) / entry) * 100;
    return Number(pnl.toFixed(2));
  }, [formData.entryPrice, formData.exitPrice, formData.direction]);

  // Form Submission
  const handleSaveTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.symbol.trim()) {
      alert("Iltimos, Coin / Juftlik nomini kiriting (masalan: BTC/USDT)");
      return;
    }
    if (!formData.entryPrice || formData.entryPrice <= 0) {
      alert("Kirish narxi 0 dan katta bo'lishi kerak");
      return;
    }
    if (!formData.exitPrice || formData.exitPrice <= 0) {
      alert("Chiqish narxini kiriting");
      return;
    }

    try {
      const res = await JournalService.addUserTrade(activeUserId, formData);
      setTrades(prev => [res.trade, ...prev.filter(t => t.id !== res.trade.id)]);
      setStats(res.stats);
      setIsFormOpen(false);
      flashMessage(`✓ ${formData.symbol.toUpperCase()} treydi muvaffaqiyatli saqlandi!`);
      
      // Reset form
      setFormData({
        date: new Date().toISOString().slice(0, 10),
        symbol: 'BTC/USDT',
        direction: 'Long',
        riskPct: 1.5,
        entryPrice: 0,
        exitPrice: 0,
        sl: null,
        tp: null,
        emotion: 'Xotirjam',
        reason: '',
        lesson: ''
      });
    } catch (e) {
      console.error('Error saving trade:', e);
      alert('Treydni saqlashda xatolik yuz berdi.');
    }
  };

  // Delete Single Trade
  const handleDeleteTrade = async (tradeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Rostdan ham ushbu treydni o'chirmoqchimisiz?")) return;

    try {
      const res = await JournalService.deleteUserTrade(activeUserId, tradeId);
      setTrades(prev => prev.filter(t => t.id !== tradeId));
      setStats(res.stats);
      flashMessage("Treyd o'chirildi.");
    } catch (e) {
      console.error('Error deleting trade:', e);
    }
  };

  // Clear All Trades for User
  const handleClearAllTrades = async () => {
    try {
      const res = await JournalService.clearAllUserTrades(activeUserId);
      setTrades([]);
      setStats(res.stats);
      setShowClearModal(false);
      flashMessage("Barcha treydlar tozalandi.");
    } catch (e) {
      console.error('Error clearing trades:', e);
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-[#0B0F17] text-[#F5F7FA] overflow-y-auto font-sans p-4 sm:p-6 lg:p-8 space-y-6">
      
      {/* Toast Notification */}
      {actionSuccessMsg && (
        <div className="fixed top-4 right-4 z-50 bg-emerald-500/90 text-black font-bold px-4 py-2.5 rounded-lg shadow-2xl flex items-center gap-2 animate-bounce text-xs">
          <CheckCircle2 className="w-4 h-4" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* Header Section */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="text-[11px] sm:text-xs font-semibold tracking-widest text-[#E5A93C] uppercase">
            RISK MENEJMENT &nbsp;/&nbsp; JURNAL
          </div>
          <div className="flex items-center gap-2 text-xs bg-[#131b2a] border border-[#1F293D] px-3 py-1 rounded-full text-gray-400">
            <UserIcon className="w-3.5 h-3.5 text-[#E5A93C]" />
            <span className="text-gray-300 font-medium">{user?.name || 'Foydalanuvchi'}</span>
            <span className="text-[10px] text-gray-500">({user?.role || 'Trader'})</span>
          </div>
        </div>

        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Treyding Jurnali
        </h1>

        <p className="text-xs sm:text-sm text-gray-400 max-w-3xl leading-relaxed">
          Har bir treydni yozib boring — kirish sababi, hissiyot va natijani. Naqadar shaffof bo'lsangiz, xatolarni shuncha tez ko'rasiz.
        </p>
      </div>

      {/* Summary Stat Cards (Grid of 5) */}
      {trades.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-4">
          
          {/* Card 1: JAMI TREYDLAR */}
          <div className="bg-[#121824] border border-[#1F293D] rounded-xl p-4 sm:p-5 flex flex-col justify-between">
            <div className="text-[10px] sm:text-[11px] font-semibold text-gray-400 tracking-wider uppercase">
              JAMI TREYDLAR
            </div>
            <div className="text-xl sm:text-2xl font-bold font-mono text-white mt-2">
              {stats.totalTrades}
            </div>
          </div>

          {/* Card 2: WIN-RATE */}
          <div className="bg-[#121824] border border-[#1F293D] rounded-xl p-4 sm:p-5 flex flex-col justify-between">
            <div className="text-[10px] sm:text-[11px] font-semibold text-gray-400 tracking-wider uppercase">
              WIN-RATE
            </div>
            <div className="text-xl sm:text-2xl font-bold font-mono text-[#00E676] mt-2">
              {stats.winRate.toFixed(1)}%
            </div>
          </div>

          {/* Card 3: UMUMIY P/L */}
          <div className="bg-[#121824] border border-[#1F293D] rounded-xl p-4 sm:p-5 flex flex-col justify-between">
            <div className="text-[10px] sm:text-[11px] font-semibold text-gray-400 tracking-wider uppercase">
              UMUMIY P/L
            </div>
            <div className={`text-xl sm:text-2xl font-bold font-mono mt-2 ${stats.totalPnlPct >= 0 ? 'text-[#00E676]' : 'text-rose-500'}`}>
              {stats.totalPnlPct > 0 ? `+${stats.totalPnlPct.toFixed(2)}%` : `${stats.totalPnlPct.toFixed(2)}%`}
            </div>
          </div>

          {/* Card 4: O'RTACHA R:R */}
          <div className="bg-[#121824] border border-[#1F293D] rounded-xl p-4 sm:p-5 flex flex-col justify-between">
            <div className="text-[10px] sm:text-[11px] font-semibold text-gray-400 tracking-wider uppercase">
              O'RTACHA R:R
            </div>
            <div className="text-xl sm:text-2xl font-bold font-mono text-white mt-2">
              {stats.avgRR}
            </div>
          </div>

          {/* Card 5: JORIY SERIYA */}
          <div className="bg-[#121824] border border-[#1F293D] rounded-xl p-4 sm:p-5 flex flex-col justify-between col-span-2 sm:col-span-1">
            <div className="text-[10px] sm:text-[11px] font-semibold text-gray-400 tracking-wider uppercase">
              JORIY SERIYA
            </div>
            <div className={`text-xl sm:text-2xl font-bold font-mono mt-2 ${
              stats.currentStreak.includes("g'alaba") 
                ? 'text-[#00E676]' 
                : stats.currentStreak.includes("mag'lubiyat") 
                ? 'text-rose-500' 
                : 'text-gray-400'
            }`}>
              {stats.currentStreak}
            </div>
          </div>

        </div>
      )}

      {/* Accordion: + Yangi treyd qo'shish */}
      <div className="bg-[#121824] border border-[#1F293D] rounded-xl overflow-hidden shadow-lg transition-all">
        <button
          onClick={() => setIsFormOpen(!isFormOpen)}
          type="button"
          className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-[#182030] transition text-sm font-medium text-white"
        >
          <span className="font-semibold flex items-center gap-2">
            <span>+ Yangi treyd qo'shish</span>
            {previewPnl !== null && isFormOpen && (
              <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${previewPnl >= 0 ? 'bg-emerald-500/20 text-[#00E676]' : 'bg-rose-500/20 text-rose-400'}`}>
                Taxminiy P/L: {previewPnl >= 0 ? `+${previewPnl}%` : `${previewPnl}%`}
              </span>
            )}
          </span>
          <span className="text-gray-400 hover:text-white">
            {isFormOpen ? <Minus className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          </span>
        </button>

        {isFormOpen && (
          <form onSubmit={handleSaveTrade} className="p-5 sm:p-6 border-t border-[#1F293D] space-y-4 bg-[#0e1420]">
            
            {/* Form Row 1: Sana, Coin / Juftlik, Yo'nalish, Risk %, Kirish narxi */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
              {/* Sana */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Sana</label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={e => setFormData({ ...formData, date: e.target.value })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-mono"
                  required
                />
              </div>

              {/* Coin / Juftlik */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Coin / Juftlik</label>
                <input
                  type="text"
                  placeholder="BTC/USDT"
                  value={formData.symbol}
                  onChange={e => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-mono font-bold"
                  required
                />
              </div>

              {/* Yo'nalish */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Yo'nalish</label>
                <select
                  value={formData.direction}
                  onChange={e => setFormData({ ...formData, direction: e.target.value as 'Long' | 'Short' })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-medium"
                >
                  <option value="Long">Long</option>
                  <option value="Short">Short</option>
                </select>
              </div>

              {/* Risk % */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Risk %</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="1.5"
                  value={formData.riskPct || ''}
                  onChange={e => setFormData({ ...formData, riskPct: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-mono"
                />
              </div>

              {/* Kirish narxi */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Kirish narxi</label>
                <input
                  type="number"
                  step="any"
                  placeholder="0.00"
                  value={formData.entryPrice || ''}
                  onChange={e => setFormData({ ...formData, entryPrice: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-mono"
                  required
                />
              </div>
            </div>

            {/* Form Row 2: Chiqish narxi, Stop-loss, Take-profit, Emotsional holat */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {/* Chiqish narxi */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Chiqish narxi</label>
                <input
                  type="number"
                  step="any"
                  placeholder="0.00"
                  value={formData.exitPrice || ''}
                  onChange={e => setFormData({ ...formData, exitPrice: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-mono"
                  required
                />
              </div>

              {/* Stop-loss */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Stop-loss</label>
                <input
                  type="number"
                  step="any"
                  placeholder="ixtiyoriy"
                  value={formData.sl || ''}
                  onChange={e => setFormData({ ...formData, sl: e.target.value ? parseFloat(e.target.value) : null })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-mono"
                />
              </div>

              {/* Take-profit */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Take-profit</label>
                <input
                  type="number"
                  step="any"
                  placeholder="ixtiyoriy"
                  value={formData.tp || ''}
                  onChange={e => setFormData({ ...formData, tp: e.target.value ? parseFloat(e.target.value) : null })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none font-mono"
                />
              </div>

              {/* Emotsional holat */}
              <div className="space-y-1.5">
                <label className="text-xs text-gray-400 font-medium">Emotsional holat</label>
                <select
                  value={formData.emotion}
                  onChange={e => setFormData({ ...formData, emotion: e.target.value })}
                  className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg px-3 py-2 text-xs text-white focus:border-[#E5A93C] focus:outline-none"
                >
                  {EMOTIONS.map(emo => (
                    <option key={emo} value={emo}>{emo}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Form Row 3: Kirish sababi */}
            <div className="space-y-1.5">
              <label className="text-xs text-gray-400 font-medium">Kirish sababi</label>
              <textarea
                placeholder="Nima uchun bu treydga kirdingiz?"
                value={formData.reason}
                onChange={e => setFormData({ ...formData, reason: e.target.value })}
                rows={2}
                className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg p-3 text-xs text-white placeholder-gray-600 focus:border-[#E5A93C] focus:outline-none resize-none leading-relaxed"
              />
            </div>

            {/* Form Row 4: Dars / Xulosa */}
            <div className="space-y-1.5">
              <label className="text-xs text-gray-400 font-medium">Dars / Xulosa</label>
              <textarea
                placeholder="Bu treyddan nima o'rgandingiz?"
                value={formData.lesson}
                onChange={e => setFormData({ ...formData, lesson: e.target.value })}
                rows={2}
                className="w-full bg-[#0B0F17] border border-[#1F293D] rounded-lg p-3 text-xs text-white placeholder-gray-600 focus:border-[#E5A93C] focus:outline-none resize-none leading-relaxed"
              />
            </div>

            {/* Form Actions */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsFormOpen(false)}
                className="text-xs text-gray-400 hover:text-white px-4 py-2 rounded-lg bg-transparent hover:bg-[#1F293D]/40 transition"
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                className="bg-[#E5A93C] hover:bg-[#d99b2f] text-[#0B0F17] font-bold text-xs px-5 py-2.5 rounded-lg transition shadow-lg flex items-center gap-1.5"
              >
                Treydni saqlash
              </button>
            </div>

          </form>
        )}
      </div>

      {/* History Section: Treydlar tarixi */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white tracking-wide">
            Treydlar tarixi
          </h2>
          {trades.length > 0 && (
            <button
              onClick={() => setShowClearModal(true)}
              type="button"
              className="text-xs text-gray-500 hover:text-rose-400 transition underline underline-offset-4 cursor-pointer"
            >
              Hammasini tozalash
            </button>
          )}
        </div>

        {/* Loading Spinner */}
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3 text-gray-500">
            <RefreshCw className="w-6 h-6 animate-spin text-[#E5A93C]" />
            <span className="text-xs">Treydlar jurnali yuklanmoqda...</span>
          </div>
        ) : trades.length === 0 ? (
          /* Empty State */
          <div className="border border-dashed border-[#1F293D] rounded-xl p-12 text-center bg-[#121824]/30 space-y-2">
            <p className="text-xs sm:text-sm text-gray-400">
              Hali treyd qo'shilmagan. Yuqoridagi tugma orqali birinchi treydingizni yozing.
            </p>
          </div>
        ) : (
          /* Trades List */
          <div className="space-y-3">
            {trades.map((trade) => {
              const isWin = trade.pnlPct > 0;
              const isLoss = trade.pnlPct < 0;
              const isExpanded = expandedTradeId === trade.id;

              // Calculate R:R
              let calculatedRR = '—';
              if (trade.sl && trade.sl > 0 && trade.entryPrice > 0 && trade.exitPrice > 0) {
                if (trade.direction === 'LONG' && trade.entryPrice > trade.sl) {
                  const risk = trade.entryPrice - trade.sl;
                  const reward = trade.exitPrice - trade.entryPrice;
                  if (risk > 0 && reward > 0) {
                    calculatedRR = `1:${(reward / risk).toFixed(1)}`;
                  }
                } else if (trade.direction === 'SHORT' && trade.sl > trade.entryPrice) {
                  const risk = trade.sl - trade.entryPrice;
                  const reward = trade.entryPrice - trade.exitPrice;
                  if (risk > 0 && reward > 0) {
                    calculatedRR = `1:${(reward / risk).toFixed(1)}`;
                  }
                }
              }

              return (
                <div
                  key={trade.id}
                  onClick={() => setExpandedTradeId(isExpanded ? null : trade.id)}
                  className={`bg-[#121824] border border-[#1F293D] rounded-xl p-4 sm:p-5 transition hover:border-gray-600 cursor-pointer ${
                    isWin ? 'border-l-4 border-l-emerald-500' : isLoss ? 'border-l-4 border-l-rose-500' : 'border-l-4 border-l-gray-500'
                  }`}
                >
                  {/* Top Bar: Symbol, Direction, Date, PnL */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-base font-bold font-mono text-white">
                        {trade.symbol}
                      </span>
                      <span className={`text-[10px] sm:text-xs font-bold px-2 py-0.5 rounded font-mono ${
                        trade.direction === 'LONG' 
                          ? 'text-[#00E676] bg-emerald-500/10 border border-emerald-500/20' 
                          : 'text-rose-400 bg-rose-500/10 border border-rose-500/20'
                      }`}>
                        {trade.direction}
                      </span>
                      <span className="text-xs text-gray-400 font-mono">
                        {trade.date}
                      </span>
                    </div>

                    <div className={`text-base font-bold font-mono ${isWin ? 'text-[#00E676]' : isLoss ? 'text-rose-500' : 'text-gray-400'}`}>
                      {trade.pnlPct > 0 ? `+${trade.pnlPct.toFixed(2)}%` : `${trade.pnlPct.toFixed(2)}%`}
                    </div>
                  </div>

                  {/* Visual Timeline / Price Slider Gauge */}
                  <div className="py-3 px-1 my-2 select-none">
                    <div className="relative w-full h-8 flex items-center">
                      {/* Horizontal track line */}
                      <div className="absolute left-0 right-0 h-[2px] bg-[#1F293D] rounded-full" />

                      {/* Active colored segment */}
                      <div 
                        className={`absolute h-[2px] rounded-full ${isWin ? 'bg-[#00E676]' : 'bg-rose-500'}`}
                        style={{ left: '20%', right: '20%' }}
                      />

                      {/* Ticks and price annotations */}
                      <div className="w-full flex items-center justify-between text-[10px] font-mono z-10">
                        
                        {/* SL Marker */}
                        {trade.sl ? (
                          <div className="flex flex-col items-start text-rose-400">
                            <span className="h-2.5 w-[2px] bg-rose-500 mb-1 ml-1" />
                            <span>SL {Number(trade.sl).toFixed(4)}</span>
                          </div>
                        ) : (
                          <div className="text-gray-600">SL —</div>
                        )}

                        {/* Entry Marker */}
                        <div className="flex flex-col items-center text-gray-200 font-bold">
                          <span className="h-3 w-[2px] bg-white mb-1" />
                          <span>Kirish: {Number(trade.entryPrice).toFixed(4)}</span>
                        </div>

                        {/* Exit Marker */}
                        <div className={`flex flex-col items-end ${isWin ? 'text-[#00E676]' : 'text-rose-400'} font-bold`}>
                          <span className={`h-2.5 w-[2px] ${isWin ? 'bg-[#00E676]' : 'bg-rose-500'} mb-1 mr-1`} />
                          <span>Chiqish {Number(trade.exitPrice).toFixed(4)}</span>
                        </div>

                      </div>
                    </div>
                  </div>

                  {/* Metrics & Tags Row */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs font-mono text-gray-400 border-t border-[#1F293D]/60">
                    <div className="flex flex-wrap items-center gap-3 sm:gap-5">
                      <span>Risk: <b className="text-gray-300 font-normal">{trade.riskPct}%</b></span>
                      <span>R:R: <b className="text-gray-300 font-normal">{calculatedRR}</b></span>
                      <span>Kirish: <b className="text-gray-300 font-normal">{Number(trade.entryPrice).toFixed(4)}</b></span>
                      <span>Chiqish: <b className="text-gray-300 font-normal">{Number(trade.exitPrice).toFixed(4)}</b></span>
                      {trade.emotion && (
                        <span className="text-[10px] bg-[#1a2336] border border-[#26354f] text-gray-300 px-2 py-0.5 rounded-md font-sans">
                          {trade.emotion}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={(e) => handleDeleteTrade(trade.id, e)}
                        className="text-xs text-gray-500 hover:text-rose-400 transition cursor-pointer font-sans"
                      >
                        O'chirish
                      </button>
                    </div>
                  </div>

                  {/* Expanded Details: Kirish sababi & Dars / Xulosa */}
                  {isExpanded && (trade.reason || trade.lesson) && (
                    <div className="mt-4 pt-3 border-t border-[#1F293D] grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-sans bg-[#0c111c] p-3.5 rounded-lg">
                      {trade.reason && (
                        <div className="space-y-1">
                          <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Kirish sababi:</span>
                          <p className="text-gray-300 text-xs leading-relaxed">{trade.reason}</p>
                        </div>
                      )}
                      {trade.lesson && (
                        <div className="space-y-1">
                          <span className="text-[10px] font-semibold text-[#E5A93C] uppercase tracking-wider">Dars / Xulosa:</span>
                          <p className="text-gray-300 text-xs leading-relaxed">{trade.lesson}</p>
                        </div>
                      )}
                    </div>
                  )}

                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Confirmation Modal for Clearing All Trades */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121824] border border-[#1F293D] rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base font-bold text-white">Barcha treydlarni o'chirish</h3>
            </div>

            <p className="text-xs sm:text-sm text-gray-300 leading-relaxed">
              Rostdan ham ushbu hisobingizdagi barcha jurnallarni tozalab yubormoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowClearModal(false)}
                className="text-xs text-gray-400 hover:text-white px-4 py-2 rounded-lg bg-transparent hover:bg-[#1F293D] transition"
              >
                Bekor qilish
              </button>
              <button
                type="button"
                onClick={handleClearAllTrades}
                className="bg-rose-500 hover:bg-rose-600 text-white font-bold text-xs px-4 py-2 rounded-lg transition"
              >
                Ha, tozalansin
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
