import React, { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Target,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Zap,
  Copy,
  Check,
  Activity,
  ArrowRight,
  AlertCircle,
  Clock,
  Sparkles,
  Layers,
  Percent,
  Compass,
  Sliders,
  XCircle
} from 'lucide-react';

export interface PositionData {
  symbol: string;
  side: string;
  leverage: string;
  entryPrice: number;
  currentPrice: number;
  pnlText: string;
  isProfit: boolean;
  sl: number;
  tp1: number;
}

export interface PropData {
  dailyDD: string;
  totalDD: string;
  riskLevel: string;
}

export interface SignalData {
  id: string;
  score: string;
}

export interface ParsedMessage {
  introText: string;
  position: PositionData | null;
  prop: PropData | null;
  signal: SignalData | null;
  outroText: string;
  rawBlocks: string[];
}

// Helper to parse numbers safely
const parseNum = (str?: string): number => {
  if (!str) return 0;
  const clean = str.replace(/[^0-9.-]/g, '');
  return parseFloat(clean) || 0;
};

// Bulletproof Parser function that extracts visual trading entities from text
export function parseTradingEntities(text: string): ParsedMessage {
  if (!text) {
    return { introText: '', position: null, prop: null, signal: null, outroText: '', rawBlocks: [] };
  }

  // 1. Structured Position Tag Detection
  const posRegex = /(?:\*\*Aktiv Pozitsiya:\*\*|\bAktiv Pozitsiya:\s*)\s*([A-Z0-9/]+)(?:\s*\((.*?)\))?/i;
  const entryRegex = /Kirish(?:\s*narxi)?:\s*[`$]*([0-9,.]+)/i;
  const currentRegex = /Joriy(?:\s*narx)?:\s*[`$]*([0-9,.]+)/i;
  const pnlRegex = /PnL:\s*[`]*([+\-$0-9,.\s()%]+?)(?:`|\s*\*|\s*\|)/i;
  const slRegex = /Stop-Loss\s*(?:\(SL\))?:\s*[`$]*([0-9,.]+)/i;
  const tpRegex = /Take-Profit\s*(?:\(TP\d*\))?:\s*[`$]*([0-9,.]+)/i;

  const posMatch = text.match(posRegex);
  const entryMatch = text.match(entryRegex);
  const currentMatch = text.match(currentRegex);
  const pnlMatch = text.match(pnlRegex);
  const slMatch = text.match(slRegex);
  const tpMatch = text.match(tpRegex);

  let position: PositionData | null = null;
  if (posMatch || (entryMatch && (currentMatch || slMatch || tpMatch))) {
    const symbol = posMatch ? posMatch[1].trim() : 'BTC/USDT';
    const sideRaw = posMatch && posMatch[2] ? posMatch[2].toUpperCase() : 'BUY 2X';
    const side = sideRaw.includes('SELL') || sideRaw.includes('SHORT') ? 'SHORT' : 'LONG';
    const levMatch = sideRaw.match(/\d+(\.\d+)?X/i);
    const leverage = levMatch ? levMatch[0].toUpperCase() : '2.0X';

    const entryPrice = parseNum(entryMatch?.[1]);
    const currentPrice = parseNum(currentMatch?.[1]) || entryPrice;
    const sl = parseNum(slMatch?.[1]);
    const tp1 = parseNum(tpMatch?.[1]);

    const pnlText = pnlMatch
      ? pnlMatch[1].trim()
      : (currentPrice >= entryPrice ? `+$${(currentPrice - entryPrice).toFixed(2)}` : `-$${(entryPrice - currentPrice).toFixed(2)}`);
    const isProfit = !pnlText.includes('-') && (pnlText.includes('+') || currentPrice >= entryPrice);

    position = {
      symbol,
      side,
      leverage,
      entryPrice: entryPrice || (symbol.includes('BTC') ? 77186.46 : 2475.0),
      currentPrice: currentPrice || (symbol.includes('BTC') ? 77216.96 : 2482.0),
      pnlText: pnlText.startsWith('+') || pnlText.startsWith('-') ? pnlText : (isProfit ? `+${pnlText}` : pnlText),
      isProfit,
      sl: sl || (symbol.includes('BTC') ? 76987.48 : 2440.0),
      tp1: tp1 || (symbol.includes('BTC') ? 77550.20 : 2520.0)
    };
  }

  // 2. Prop Firm Drawdown Matrix Detection
  const propMatch = text.match(/Kunlik DD:\s*[`]*([0-9,.\s%/]+?)(?:`|\s*\*|\s*\|)/i);
  const totalDDMatch = text.match(/Umumiy DD:\s*[`]*([0-9,.\s%/]+?)(?:`|\s*\*|\s*\|)/i);
  const riskMatch = text.match(/Xavf(?:\s*darajasi)?:\s*([A-Za-z0-9\s]+?)(?:\)|\*|\.|$)/i);

  let prop: PropData | null = null;
  if (propMatch || totalDDMatch) {
    prop = {
      dailyDD: propMatch ? propMatch[1].trim() : '0.0% / 5%',
      totalDD: totalDDMatch ? totalDDMatch[1].trim() : '0.00% / 10%',
      riskLevel: riskMatch ? riskMatch[1].trim() : 'Minimal'
    };
  }

  // 3. Active Signal Detection
  const sigMatch = text.match(/sig_[a-z0-9_]+/i);
  const scoreMatch = text.match(/AI Score:\s*([0-9.]+)%/i);
  let signal: SignalData | null = null;
  if (sigMatch) {
    signal = {
      id: sigMatch[0],
      score: scoreMatch ? `${scoreMatch[1]}%` : '78.7%'
    };
  }

  // 4. Clean Split into Intro and Outro
  let introText = text;
  let outroText = '';

  if (position || prop || signal) {
    const statusHeaderRegex = /(?:---\s*\n+)?(?:###\s*📊\s*Joriy Pozitsiya Holati|\*\*Joriy terminal holati.*?\*\*|\*?\s*\*\*Aktiv Pozitsiya:\*\*|Joriy platforma va bozor holati|\*?\s*Kirish narxi:)/i;
    const headerMatch = text.match(statusHeaderRegex);

    if (headerMatch && headerMatch.index !== undefined) {
      introText = text.substring(0, headerMatch.index).trim();
      introText = introText.replace(/[\*\-:]+\s*$/, '').trim();
    }

    const sigIdx = text.search(/sig_[a-z0-9_]+/i);
    const searchAfter = sigIdx > 0 ? sigIdx : (headerMatch?.index || 0);
    const sub = text.substring(searchAfter);
    const m = sub.match(/(?:---\s*\n+|###\s*🏛|Bugun qaysi|Sizga qaysi|So'rovingizni|Qanday savol|Batafsil ma'lumot|Savolingiz bo'lsa)/i);
    if (m && m.index !== undefined) {
      outroText = sub.substring(m.index).replace(/^---\s*/, '').trim();
    }
  }

  return {
    introText,
    position,
    prop,
    signal,
    outroText,
    rawBlocks: []
  };
}

// Interactive Code Block with Copy
const CodeBlock: React.FC<{ code: string; language?: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-2.5 rounded-xl overflow-hidden border border-[#1C2E52] bg-[#050914] shadow-md">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#080E1C] border-b border-[#1C2E52] text-[10px] font-mono text-slate-400">
        <span className="uppercase font-bold text-cyan-400">{language || 'QUANT CODE'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-white transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-400" />}
          <span>{copied ? 'Nusxalandi' : 'Nusxa olish'}</span>
        </button>
      </div>
      <pre className="p-3 text-[11px] font-mono text-slate-200 overflow-x-auto selection:bg-cyan-500/30">
        <code>{code}</code>
      </pre>
    </div>
  );
};

// Rich Markdown Text Formatter
const RichMarkdownContent: React.FC<{ text: string }> = ({ text }) => {
  if (!text) return null;

  const codeBlockRegex = /```([a-zA-Z]*)\n([\s\S]*?)```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: text.substring(lastIndex, match.index) });
    }
    parts.push({ type: 'code', language: match[1], content: match[2] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  const renderFormattedParagraphs = (str: string) => {
    const lines = str.split('\n');
    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={idx} className="h-1.5" />;

      // Bullet points
      if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
        const itemText = trimmed.replace(/^[\*\-•]\s*/, '');
        return (
          <div key={idx} className="flex items-start gap-2 my-1 pl-1 font-sans">
            <span className="text-cyan-400 text-xs select-none mt-0.5">▪</span>
            <div className="flex-1 text-slate-200 text-xs leading-relaxed">
              {formatInlineTokens(itemText)}
            </div>
          </div>
        );
      }

      // Headers (### or ##)
      if (trimmed.startsWith('### ')) {
        return (
          <h4 key={idx} className="font-bold text-white text-xs mt-3 mb-1.5 font-mono flex items-center gap-1.5 text-cyan-300">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            {trimmed.replace(/^###\s*/, '')}
          </h4>
        );
      }

      if (trimmed.startsWith('## ')) {
        return (
          <h3 key={idx} className="font-extrabold text-sm text-white mt-3.5 mb-2 font-sans tracking-wide text-cyan-300">
            {trimmed.replace(/^##\s*/, '')}
          </h3>
        );
      }

      return (
        <p key={idx} className="my-1 text-slate-200 text-xs leading-relaxed font-sans">
          {formatInlineTokens(line)}
        </p>
      );
    });
  };

  const formatInlineTokens = (lineStr: string) => {
    const codeParts = lineStr.split(/(`[^`]+`)/g);
    return codeParts.map((part, pIdx) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={pIdx}
            className="px-1.5 py-0.5 mx-0.5 rounded bg-[#080E1C] border border-cyan-500/30 text-cyan-300 font-mono text-[11px] font-bold shadow-sm"
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
      return boldParts.map((bPart, bIdx) => {
        if (bPart.startsWith('**') && bPart.endsWith('**')) {
          return (
            <strong key={bIdx} className="font-bold text-white font-sans text-cyan-200">
              {bPart.slice(2, -2)}
            </strong>
          );
        }
        return bPart;
      });
    });
  };

  return (
    <div className="space-y-0.5">
      {parts.map((p, idx) => {
        if (p.type === 'code') {
          return <CodeBlock key={idx} code={p.content} language={p.language} />;
        }
        return <React.Fragment key={idx}>{renderFormattedParagraphs(p.content)}</React.Fragment>;
      })}
    </div>
  );
};

// Visual Trade Execution Ticket Card (Kirish, Chiqish, Joriy narx, PnL, TP, SL)
export const VisualTradeTicket: React.FC<{ pos: PositionData }> = ({ pos }) => {
  const isBuy = pos.side === 'LONG' || pos.side.includes('BUY');
  const slDist = Math.abs(pos.currentPrice - pos.sl);
  const tpDist = Math.abs(pos.tp1 - pos.currentPrice);
  const totalSpan = Math.abs(pos.tp1 - pos.sl);
  const progressPct = totalSpan > 0 ? Math.min(100, Math.max(0, ((pos.currentPrice - pos.sl) / totalSpan) * 100)) : 50;

  return (
    <div className="my-3 rounded-2xl bg-gradient-to-r from-[#0C152B] via-[#0E1B38] to-[#0A1224] border border-[#1C2E52] p-4 shadow-xl select-none">
      {/* Header Row */}
      <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-[#1C2E52]">
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs shadow-inner ${
            isBuy ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
          }`}>
            {isBuy ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          </div>
          <div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-extrabold text-sm text-white font-sans tracking-wide">{pos.symbol}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                isBuy ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}>
                {pos.side} {pos.leverage}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-[9px] font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                LIVE MISSION
              </span>
            </div>
          </div>
        </div>

        {/* Dynamic PnL Badge with Glow */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-mono text-xs font-black shadow-lg ${
          pos.isProfit
            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.25)]'
            : 'bg-rose-500/20 text-rose-300 border border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.25)]'
        }`}>
          <span>PnL:</span>
          <span className="text-sm tracking-tight">{pos.pnlText}</span>
        </div>
      </div>

      {/* 4-Metric Institutional Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-3">
        {/* Kirish Narxi (Entry Price) */}
        <div className="p-2.5 rounded-xl bg-[#080E1C] border border-[#1C2D4E]">
          <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
            <Clock className="w-3 h-3 text-cyan-400" />
            <span>KIRISH NARXI:</span>
          </div>
          <div className="text-white font-bold font-mono text-xs mt-0.5">
            ${pos.entryPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>

        {/* Joriy Narx (Mark Price) */}
        <div className="p-2.5 rounded-xl bg-[#080E1C] border border-[#1C2D4E]">
          <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>JORIY NARX:</span>
          </div>
          <div className="text-cyan-300 font-bold font-mono text-xs mt-0.5">
            ${pos.currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>

        {/* Stop-Loss (SL) */}
        <div className="p-2.5 rounded-xl bg-[#080E1C] border border-rose-500/30">
          <div className="text-[10px] text-rose-400 font-mono flex items-center gap-1">
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            <span>STOP-LOSS (SL):</span>
          </div>
          <div className="text-rose-300 font-bold font-mono text-xs mt-0.5">
            ${pos.sl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>

        {/* Take-Profit (TP1) */}
        <div className="p-2.5 rounded-xl bg-[#080E1C] border border-emerald-500/30">
          <div className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
            <Target className="w-3 h-3 text-emerald-400" />
            <span>TAKE-PROFIT (TP1):</span>
          </div>
          <div className="text-emerald-300 font-bold font-mono text-xs mt-0.5">
            ${pos.tp1.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {/* Visual Dynamic Range Bar (SL -> Current Price -> TP1) */}
      <div className="p-2.5 rounded-xl bg-[#080E1C] border border-[#1C2D4E] space-y-1.5">
        <div className="flex items-center justify-between text-[10px] font-mono">
          <span className="text-rose-400 flex items-center gap-1">
            SL: ${pos.sl} <span className="text-slate-500">(-${slDist.toFixed(1)})</span>
          </span>
          <span className="text-cyan-300 font-bold">
            Target Progress: {progressPct.toFixed(0)}%
          </span>
          <span className="text-emerald-400 flex items-center gap-1">
            TP1: ${pos.tp1} <span className="text-slate-500">(+${tpDist.toFixed(1)})</span>
          </span>
        </div>
        <div className="w-full h-2 bg-[#0C152B] rounded-full overflow-hidden border border-[#1C2E52] relative">
          <div
            className={`h-full transition-all duration-300 ${
              pos.isProfit
                ? 'bg-gradient-to-r from-cyan-500 to-emerald-400'
                : 'bg-gradient-to-r from-rose-500 to-amber-400'
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>
    </div>
  );
};

// Visual Prop Risk Guard Widget
export const VisualPropGuard: React.FC<{ prop: PropData }> = ({ prop }) => {
  return (
    <div className="my-2.5 rounded-2xl bg-[#080E1C] border border-[#1C2E52] p-3.5 space-y-2.5 shadow-md">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-bold text-white font-sans">FTMO PROP CHALLENGE MATRIX</span>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          {prop.riskLevel.toUpperCase()} XAVF
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
        <div className="p-2.5 rounded-xl bg-[#0C152B] border border-[#1C2D4E] flex items-center justify-between">
          <span className="text-slate-400 text-[11px]">Kunlik Drawdown:</span>
          <span className="font-bold text-emerald-400">{prop.dailyDD}</span>
        </div>
        <div className="p-2.5 rounded-xl bg-[#0C152B] border border-[#1C2D4E] flex items-center justify-between">
          <span className="text-slate-400 text-[11px]">Umumiy Drawdown:</span>
          <span className="font-bold text-cyan-300">{prop.totalDD}</span>
        </div>
      </div>
    </div>
  );
};

// Visual Signal Pill Card
export const VisualSignalPill: React.FC<{ signal: SignalData }> = ({ signal }) => {
  return (
    <div className="my-2 p-2.5 rounded-xl bg-[#080E1C] border border-cyan-500/30 flex items-center justify-between text-xs font-mono">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-cyan-400 animate-pulse" />
        <span className="text-slate-400 text-[11px]">Faol Signal:</span>
        <span className="text-white font-bold">{signal.id}</span>
      </div>
      <div className="px-2.5 py-1 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 font-bold text-[11px]">
        AI Score: {signal.score}
      </div>
    </div>
  );
};

// Master Message Renderer Component
export const XRVisualMessageRenderer: React.FC<{ text: string }> = ({ text }) => {
  const parsed = parseTradingEntities(text);

  // If no specific entities found, render as enhanced rich markdown directly
  if (!parsed.position && !parsed.prop && !parsed.signal) {
    return <RichMarkdownContent text={text} />;
  }

  return (
    <div className="space-y-2">
      {/* Intro Text (e.g. Greeting or Summary) */}
      {parsed.introText && (
        <RichMarkdownContent text={parsed.introText} />
      )}

      {/* Visual Position Ticket */}
      {parsed.position && (
        <VisualTradeTicket pos={parsed.position} />
      )}

      {/* Visual Prop Risk Guard */}
      {parsed.prop && (
        <VisualPropGuard prop={parsed.prop} />
      )}

      {/* Visual Active Signal Pill */}
      {parsed.signal && (
        <VisualSignalPill signal={parsed.signal} />
      )}

      {/* Outro Text (e.g. follow-up questions) */}
      {parsed.outroText && (
        <RichMarkdownContent text={parsed.outroText} />
      )}
    </div>
  );
};
