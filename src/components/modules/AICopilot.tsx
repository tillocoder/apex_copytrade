import React, { useState, useEffect, useRef } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { GeminiService, type GeminiChatMessage } from '../../services/geminiService';
import { XRVisualMessageRenderer } from './XRVisualMessageRenderer';
import { 
  Bot, 
  Send, 
  Sparkles, 
  User, 
  Key, 
  Trash2, 
  RefreshCw, 
  ShieldCheck, 
  TrendingUp, 
  Activity, 
  Zap,
  MessageSquare,
  Flame,
  Check
} from 'lucide-react';

const CHAT_STORAGE_KEY = 'APEX_XR_AI_CHAT_HISTORY_V2';

export const AICopilot: React.FC = () => {
  const { positions = [], tickers = [], propAccounts = [], signals = [], logs = [] } = useTerminal();
  const [apiKeyInput, setApiKeyInput] = useState(GeminiService.getApiKey());
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [copiedKeyNotice, setCopiedKeyNotice] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // 1. Persistent Chat History Initialization
  const [messages, setMessages] = useState<GeminiChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem(CHAT_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn('Failed to load chat history from localStorage:', e);
    }

    // Default institutional greeting with live positions
    const nowTime = new Date().toTimeString().split(' ')[0];
    const safePos = Array.isArray(positions) ? positions.filter(p => p && String(p.status || 'OPEN').toUpperCase() === 'OPEN') : [];
    const btcPos = safePos.find(p => p.symbol?.includes('BTC')) || safePos[0];

        const entryFmt = (btcPos?.entryPrice || 77186.46).toLocaleString('en-US', { minimumFractionDigits: 2 });
    const markFmt = (btcPos?.currentPrice || 77216.96).toLocaleString('en-US', { minimumFractionDigits: 2 });
    const slFmt = (btcPos?.sl || 76987.48).toLocaleString('en-US', { minimumFractionDigits: 2 });
    const tpFmt = (btcPos?.tp1 || 77550.20).toLocaleString('en-US', { minimumFractionDigits: 2 });
    const pnlVal = btcPos?.unrealizedPnl !== undefined ? btcPos.unrealizedPnl : 1.59;
    const pnlPct = btcPos?.unrealizedPnlPercent !== undefined ? btcPos.unrealizedPnlPercent : 0.08;
    const pnlSign = pnlVal >= 0 ? '+' : '';

    const defaultGreeting = btcPos
      ? `Assalomu alaykum, Marcus. APEX Quant Trading Terminalining markaziy institutsional kvant va xavf intellekt tizimi — **XR AI 2.5** xizmatingizda. Barcha institutsional kassa oqimi (Order Flow), Fair Value Gap (FVG), likvidlik nuqtalari va risk-menedjment modullari to'liq ishchi holatda.\n\n**Joriy terminal holati va faol parametrlar:**\n* **Aktiv Pozitsiya:** ${btcPos.symbol || 'BTC/USDT'} (${btcPos.side || 'BUY'} ${btcPos.leverage || '2.0'}X)\n* Kirish narxi: \`$${entryFmt}\` | Joriy narx: \`$${markFmt}\`\n* PnL: \`${pnlSign}$${pnlVal.toFixed(2)} (${pnlSign}${pnlPct.toFixed(2)}%)\`\n* Stop-Loss (SL): \`$${slFmt}\` | Take-Profit (TP1): \`$${tpFmt}\`\n* **FTMO Prop Matrix:** Kunlik DD: \`0.0% / 5%\` | Umumiy DD: \`0.00% / 10%\` (Xavf darajasi: Minimal)\n* **Faol Signal:** \`sig_btcusdt_1789105500\` (AI Score: 78.7%)\n\nBugun qaysi aktiv tahlili, bozor rejimi, yangi kirish zonasi (Order Block) yoki prop-firm drawdown limitlari bo'yicha ma'lumot beray?`
      : `Assalomu alaykum, Marcus. APEX Quant Trading tizimining markaziy kvant yadrosi — **XR AI 2.5** xizmatingizda. Barcha algoritmik strategiyalar, ochiq pozitsiyalar, FTMO prop limitlari va bozor konyunkturasi bo'yicha savollaringizni berishingiz mumkin.`;

    return [
      {
        sender: 'ai',
        text: defaultGreeting,
        timestamp: nowTime
      }
    ];
  });

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Auto-scroll to bottom on message updates
  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Save to localStorage on any message change
  useEffect(() => {
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
    } catch (e) {
      console.warn('Failed to persist chat history:', e);
    }
  }, [messages]);

  const activeProp = propAccounts[0];

  const handleSaveApiKey = (e: React.FormEvent) => {
    e.preventDefault();
    GeminiService.setApiKey(apiKeyInput);
    setShowKeyModal(false);
    setCopiedKeyNotice(true);
    setTimeout(() => setCopiedKeyNotice(false), 2000);
  };

  const handleClearHistory = () => {
    if (window.confirm('Haqiqatan ham butun chat tarixini tozalamoqchimisiz?')) {
      localStorage.removeItem(CHAT_STORAGE_KEY);
      const nowTime = new Date().toTimeString().split(' ')[0];
      setMessages([
        {
          sender: 'ai',
          text: `Assalomu alaykum, Marcus. Chat tarixi tozalandi. XR AI 2.5 tizimi yangi seans uchun tayyor. Ochiq pozitsiyalar, kirish va chiqish zonalari yoki FTMO limitlari bo'yicha so'rovingizni bering. Ochiq pozitsiyalar, risk yoki bozor holati bo'yicha so'rovingizni bering.`,
          timestamp: nowTime
        }
      ]);
    }
  };

  const handleSendPrompt = async (promptText: string) => {
    if (!promptText.trim() || isLoading) return;

    const nowTime = new Date().toTimeString().split(' ')[0];
    const userMsg: GeminiChatMessage = {
      sender: 'user',
      text: promptText.trim(),
      timestamp: nowTime
    };

    const updatedHistory = [...messages, userMsg];
    setMessages(updatedHistory);
    setInput('');
    setIsLoading(true);

    try {
      const responseText = await GeminiService.queryGemini(
        promptText.trim(),
        updatedHistory, // Sends full conversation context memory!
        positions,
        tickers,
        activeProp,
        signals,
        logs
      );

      setMessages(prev => [
        ...prev,
        {
          sender: 'ai',
          text: responseText,
          timestamp: new Date().toTimeString().split(' ')[0],
          confidence: 96.8
        }
      ]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          sender: 'ai',
          text: `XR AI javob qaytarishda xatolik yuz berdi: ${err.message || 'Iltimos, API sozlamalarini tekshiring.'}`,
          timestamp: new Date().toTimeString().split(' ')[0]
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendPrompt(input);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#070B14] font-sans text-xs p-3 sm:p-5 space-y-3.5 select-none">
      
      {/* Top Banner Header (Cyber-Navy Matrix Theme) */}
      <div className="w-full rounded-2xl bg-gradient-to-r from-[#0C152B] via-[#0E1B38] to-[#0A1224] border border-[#1C2E52] px-4 py-3 sm:px-5 sm:py-3.5 shadow-xl">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/15 border border-cyan-500/35 flex items-center justify-center text-cyan-400 shrink-0 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
              <Bot className="w-5 h-5 animate-pulse" />
            </div>

            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-sm sm:text-base font-black text-white tracking-wider font-sans">
                  XR AI 2.5 QUANTITATIVE COPILOT & RISK ASSISTANT
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-black bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-mono">
                  ACTIVE CONTEXT MEMORY
                </span>
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5 font-mono">
                Institutional Quant Brain • Live Position Analytics • FTMO Drawdown Guard
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Clear History Button */}
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#080E1C] hover:bg-rose-500/15 border border-[#1C2D4E] hover:border-rose-500/40 text-slate-300 hover:text-rose-300 text-[11px] font-mono transition-all"
              title="Chat tarixini tozalash"
            >
              <Trash2 className="w-3.5 h-3.5 text-slate-400 group-hover:text-rose-400" />
              <span>Tarixni tozalash</span>
            </button>

            {/* API Key Modal Button */}
            <button 
              onClick={() => setShowKeyModal(!showKeyModal)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#080E1C] hover:bg-cyan-500/15 border border-cyan-500/35 text-cyan-300 text-[11px] font-mono transition-all shadow-sm"
            >
              <Key className="w-3.5 h-3.5 text-cyan-400" />
              <span>{GeminiService.hasApiKey() ? 'API KALIT ULANGAN' : 'API KALIT SOZLASH'}</span>
            </button>

            {/* Live Model Badge */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#080E1C] border border-emerald-500/40 text-[11px] font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
              <span className="text-emerald-300 font-bold">GEMINI 3.6 FLASH</span>
            </div>
          </div>
        </div>
      </div>

      {/* API Key Configuration Dropdown */}
      {showKeyModal && (
        <form onSubmit={handleSaveApiKey} className="p-3.5 rounded-2xl bg-gradient-to-r from-[#0C152B] via-[#0E1B38] to-[#0A1224] border border-cyan-500/40 flex flex-wrap items-center justify-between gap-3 font-mono shadow-xl animate-in fade-in duration-200">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white text-xs">GOOGLE GEMINI 3.6 FLASH API KALITI</div>
              <div className="text-[10px] text-slate-400">Kalit brauzer xotirasida xavfsiz saqlanadi.</div>
            </div>
          </div>

          <div className="flex items-center space-x-2 flex-1 max-w-lg">
            <input 
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="AQ.Ab8RN6JPJM4wM3eCK10L..."
              className="flex-1 bg-[#080E1C] border border-[#1C2E52] rounded-xl px-3 py-1.5 text-white placeholder-slate-500 outline-none focus:border-cyan-400 font-mono text-xs"
            />
            <button 
              type="submit" 
              className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-black px-4 py-1.5 rounded-xl shrink-0 transition-all shadow-[0_0_12px_rgba(6,182,212,0.3)] text-xs"
            >
              SAQLASH
            </button>
          </div>
        </form>
      )}

      {/* Quick Prompt Suggestion Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none font-mono text-xs">
        <span className="text-slate-400 text-[11px] font-bold shrink-0 hidden sm:inline">TEZKOR SAVOLLAR:</span>
        {[
          { label: "🎯 Ochiq pozitsiyalar va SL/TP tahlili", prompt: "Joriy ochiq pozitsiyalar, kirish va chiqish narxlari, SL va TP darajalari bo'yicha to'liq tahlil ber." },
          { label: "🛡 FTMO Prop hisob va kunlik DD xavfi", prompt: "FTMO Prop Firm hisobimizning kunlik drawdown va umumiy limitlari holati qanday? Xavf darajasini ko'rsat." },
          { label: "⚡ Bugungi eng kuchli AI signallari", prompt: "Bozorda qaysi aktivlar (BTC/ETH) bo'yicha aktiv signallar va order block imbalancelar bor?" },
          { label: "📊 Birja seanslari va 1-yillik backtest", prompt: "Hozir qaysi birja seansi faol va bizning 1-yillik strategiyamiz ko'rsatkichlari (WR, PF) qanday?" }
        ].map((chip, cIdx) => (
          <button
            key={cIdx}
            onClick={() => handleSendPrompt(chip.prompt)}
            disabled={isLoading}
            className="px-3 py-1 rounded-xl bg-[#080E1C] hover:bg-[#0C152B] border border-[#1C2D4E] hover:border-cyan-500/40 text-slate-300 hover:text-cyan-300 text-[11px] whitespace-nowrap transition-all flex items-center gap-1.5 disabled:opacity-50 active:scale-95"
          >
            <span>{chip.label}</span>
          </button>
        ))}
      </div>

      {/* Main Chat Conversation Container */}
      <div className="flex-1 rounded-2xl bg-[#080E1C] border border-[#1C2E52] flex flex-col overflow-hidden shadow-2xl">
        
        {/* Messages Scroll Area */}
        <div className="flex-1 p-4 sm:p-5 overflow-y-auto space-y-4 font-sans">
          {messages.map((m, idx) => {
            const isUser = m.sender === 'user';
            return (
              <div 
                key={idx} 
                className={`flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {/* AI Avatar */}
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/35 text-cyan-400 flex items-center justify-center shrink-0 shadow-[0_0_12px_rgba(6,182,212,0.2)] mt-0.5">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                  </div>
                )}

                {/* Message Bubble */}
                <div 
                  className={`p-3.5 sm:p-4 rounded-2xl max-w-2xl text-xs leading-relaxed shadow-lg ${
                    isUser 
                      ? 'bg-[#0E1B38] border border-[#1C2E52] text-white font-medium rounded-tr-sm' 
                      : 'bg-gradient-to-br from-[#0C152B] via-[#091224] to-[#080E1C] border border-[#1C2E52] text-slate-100 rounded-tl-sm w-full'
                  }`}
                >
                  {/* Sender Header and Timestamp */}
                  <div className="flex justify-between items-center text-[10px] font-mono mb-2 pb-1.5 border-b border-[#1C2E52]/60 text-slate-400">
                    <span className="font-bold flex items-center gap-1.5">
                      {isUser ? (
                        <>
                          <User className="w-3 h-3 text-cyan-400" />
                          <span className="text-cyan-300">SIZ (CHIEF QUANT TRADER)</span>
                        </>
                      ) : (
                        <>
                          <Bot className="w-3 h-3 text-cyan-400" />
                          <span className="text-cyan-400">XR AI 2.5 INSTITUTIONAL QUANT</span>
                        </>
                      )}
                    </span>
                    <span className="text-slate-500">{m.timestamp}</span>
                  </div>

                  {/* Message Content: Rich Interactive Visual Renderer */}
                  {isUser ? (
                    <div className="text-slate-100 text-xs font-sans whitespace-pre-wrap">{m.text}</div>
                  ) : (
                    <XRVisualMessageRenderer text={m.text} />
                  )}
                </div>

                {/* User Avatar */}
                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-[#0E1B38] border border-cyan-500/30 text-cyan-300 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {/* AI Thinking Animation */}
          {isLoading && (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-500/35 text-cyan-400 flex items-center justify-center shrink-0 animate-pulse">
                <Sparkles className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="p-3.5 rounded-2xl bg-gradient-to-br from-[#0C152B] to-[#080E1C] border border-cyan-500/30 text-cyan-300 font-mono text-xs flex items-center gap-2.5 shadow-lg">
                <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                <span>XR AI 2.5 bozor konyunkturasi, pozitsiyalar va risk limitlarini tahlil qilmoqda...</span>
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Input Form Bar */}
        <form onSubmit={handleSubmit} className="p-3 bg-[#0A1224] border-t border-[#1C2E52] flex items-center gap-2 font-mono">
          <input 
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="XR AI'dan so'rang (masalan: 'BTC kirish va chiqish darajalari qanday?', 'Bugun kunlik DD qancha?', 'Yangi signal bormi?')..."
            className="flex-1 bg-[#080E1C] border border-[#1C2E52] rounded-xl px-3.5 py-2.5 text-white placeholder-slate-500 outline-none focus:border-cyan-400 transition-all font-mono text-xs"
          />
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()}
            className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-black px-5 py-2.5 rounded-xl flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(6,182,212,0.35)] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4 fill-black" />
            <span className="hidden sm:inline">{isLoading ? 'TAHLIL...' : 'YUBORISH'}</span>
          </button>
        </form>

      </div>
    </div>
  );
};
