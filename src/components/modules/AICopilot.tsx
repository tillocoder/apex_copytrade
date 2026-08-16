import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { GeminiService, type GeminiChatMessage } from '../../services/geminiService';
import { Bot, Send, Sparkles, User, Key } from 'lucide-react';

export const AICopilot: React.FC = () => {
  const { positions, tickers, propAccounts, signals, logs } = useTerminal();
  const [apiKeyInput, setApiKeyInput] = useState(GeminiService.getApiKey());
  const [showKeyModal, setShowKeyModal] = useState(!GeminiService.hasApiKey());

  const [messages, setMessages] = useState<GeminiChatMessage[]>([
    { 
      sender: 'ai', 
      text: 'Greeting Marcus. I am XR AI — the central operating intelligence of APEX Quant Terminal. Ask me anything about live positions, market regime, order flow, or prop firm drawdown limits.',
      timestamp: '13:00:00' 
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const activeProp = propAccounts[0];

  const handleSaveApiKey = (e: React.FormEvent) => {
    e.preventDefault();
    GeminiService.setApiKey(apiKeyInput);
    setShowKeyModal(false);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input;
    const userMsg: GeminiChatMessage = {
      sender: 'user',
      text: userText,
      timestamp: new Date().toISOString().split('T')[1].slice(0, 8)
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const responseText = await GeminiService.queryGemini(
        userText,
        messages,
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
          timestamp: new Date().toISOString().split('T')[1].slice(0, 8),
          confidence: 96.5
        }
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          sender: 'ai',
          text: 'Error generating response from XR AI API. Please check your API key.',
          timestamp: new Date().toISOString().split('T')[1].slice(0, 8)
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs p-4 space-y-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Bot className="w-5 h-5 text-apex-ai" />
          <span>REAL-TIME XR AI CHAT & QUANT ASSISTANT</span>
        </div>

        <div className="flex items-center space-x-3">
          <button 
            onClick={() => setShowKeyModal(true)}
            className="flex items-center space-x-1.5 bg-apex-surface hover:bg-apex-hover border border-apex-border text-apex-accent px-2.5 py-1 rounded-btn text-[11px] transition-apex"
          >
            <Key className="w-3.5 h-3.5 text-apex-accent" />
            <span>{GeminiService.hasApiKey() ? 'API KEY CONFIGURED' : 'SET XR AI API KEY'}</span>
          </button>

          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
            GeminiService.hasApiKey() ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' : 'bg-apex-warning/15 text-apex-warning border border-apex-warning/30'
          }`}>
            {GeminiService.hasApiKey() ? 'XR AI 2.5 CONNECTED' : 'XR LOCAL ENGINE ACTIVE'}
          </span>
        </div>
      </div>

      {/* API Key Setup Banner if not set */}
      {showKeyModal && (
        <form onSubmit={handleSaveApiKey} className="p-3 bg-apex-surface border border-apex-ai rounded-panel flex items-center justify-between space-x-3 font-mono">
          <div className="flex items-center space-x-2">
            <Key className="w-4 h-4 text-apex-ai shrink-0" />
            <div>
              <div className="font-bold text-apex-text text-xs">ENTER YOUR XR AI API KEY</div>
              <div className="text-[10px] text-apex-muted">Key is saved securely in your local browser storage.</div>
            </div>
          </div>

          <div className="flex items-center space-x-2 flex-1 max-w-md">
            <input 
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="AIzaSy..."
              className="w-full bg-apex-bg border border-apex-border rounded-btn px-3 py-1.5 text-apex-text outline-none focus:border-apex-ai"
            />
            <button type="submit" className="bg-apex-ai text-white font-bold px-3 py-1.5 rounded-btn shrink-0 transition-apex">
              SAVE KEY
            </button>
          </div>
        </form>
      )}

      {/* Chat Workspace */}
      <div className="flex-1 workstation-panel flex flex-col overflow-hidden">
        {/* Chat History */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3 font-sans">
          {messages.map((m, idx) => (
            <div key={idx} className={`flex items-start space-x-2.5 ${m.sender === 'user' ? 'justify-end' : ''}`}>
              {m.sender === 'ai' && (
                <div className="w-7 h-7 rounded-md bg-apex-ai/15 border border-apex-ai/30 text-apex-ai flex items-center justify-center shrink-0">
                  <Sparkles className="w-4 h-4 text-apex-ai" />
                </div>
              )}
              <div className={`p-3 rounded-panel max-w-xl text-xs leading-relaxed font-sans ${
                m.sender === 'user' 
                  ? 'bg-apex-surface border border-apex-border text-apex-text font-medium' 
                  : 'bg-apex-bgSecondary border border-apex-border text-apex-textSecondary'
              }`}>
                <div className="flex justify-between items-center text-[10px] font-mono mb-1 text-apex-muted">
                  <span>{m.sender === 'user' ? 'YOU (CHIEF QUANT)' : 'XR AI 2.5'}</span>
                  <span>{m.timestamp}</span>
                </div>
                <div>{m.text}</div>
              </div>
              {m.sender === 'user' && (
                <div className="w-7 h-7 rounded-md bg-apex-surface border border-apex-border text-apex-muted flex items-center justify-center shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex items-center space-x-2 text-apex-ai font-mono text-xs p-2">
              <Sparkles className="w-4 h-4 animate-spin text-apex-ai" />
              <span>XR AI is evaluating OHLCV, Order Flow & Prop Limits...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="p-3 bg-apex-bgSecondary border-t border-apex-border flex space-x-2 font-mono">
          <input 
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask XR AI (e.g. 'Why was BTC trade opened?', 'Can I increase leverage?', 'Analyze today drawdown')..."
            className="flex-1 bg-apex-bg border border-apex-border rounded-btn px-3 py-2 text-apex-text placeholder-apex-muted outline-none focus:border-apex-ai transition-apex"
          />
          <button 
            type="submit" 
            disabled={isLoading}
            className="bg-apex-ai hover:bg-purple-600 text-white font-bold px-4 py-2 rounded-btn flex items-center space-x-1.5 transition-apex shadow-subtle disabled:opacity-50"
          >
            <Send className="w-4 h-4 fill-white" />
            <span>{isLoading ? 'STREAMING...' : 'SEND'}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
