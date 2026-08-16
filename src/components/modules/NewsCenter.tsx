import React, { useEffect, useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { Newspaper, Calendar, Tag, Clock, ExternalLink, AlertTriangle } from 'lucide-react';

export const NewsCenter: React.FC = () => {
  const { news } = useTerminal();
  const [economicEvents, setEconomicEvents] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/v1/news/economic-calendar')
      .then(res => res.json())
      .then(json => {
        if (json.status === 'SUCCESS' && Array.isArray(json.data)) {
          setEconomicEvents(json.data);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Newspaper className="w-5 h-5 text-apex-cyan" />
          <span>AI NEWS TERMINAL & LIVE FOREXFACTORY ECONOMIC CALENDAR</span>
        </div>
        <div className="text-[11px] text-apex-green font-bold flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-apex-green animate-ping" /> LIVE RSS & FOREXFACTORY API STREAMING
        </div>
      </div>

      {/* Main 2-Column Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-hidden">
        {/* Left Column: Real Institutional News Stream (2 cols) */}
        <div className="lg:col-span-2 flex flex-col space-y-3 overflow-y-auto pr-1">
          <div className="font-bold text-apex-text text-xs flex items-center justify-between">
            <span>REAL-TIME INSTITUTIONAL NEWS</span>
            <span className="text-[10px] text-apex-muted">{news.length} LIVE HEADLINES</span>
          </div>

          {news.length === 0 ? (
            <div className="p-8 text-center text-apex-muted border border-apex-border rounded-lg">
              Fetching real-time news feed from CoinTelegraph & CoinDesk...
            </div>
          ) : (
            news.map((item) => (
              <div key={item.id} className="bg-apex-surface border border-apex-border rounded-lg p-4 space-y-2 shadow-xl hover:border-apex-cyan/40 transition-apex">
                <div className="flex items-center justify-between">
                  <span className="bg-apex-panel px-2 py-0.5 rounded text-[10px] text-apex-cyan border border-apex-border font-bold">
                    {item.source}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    item.sentiment === 'BULLISH' ? 'bg-apex-green/20 text-apex-green' : item.sentiment === 'BEARISH' ? 'bg-apex-red/20 text-apex-red' : 'bg-apex-panel text-apex-muted'
                  }`}>
                    {item.sentiment} ({Math.round((item.sentimentScore || 0.5) * 100)}%)
                  </span>
                </div>

                <h3 className="font-bold text-sm text-apex-text leading-snug">{item.title}</h3>
                <p className="text-apex-muted text-[11px] leading-relaxed">{item.summary}</p>

                <div className="pt-2 border-t border-apex-border flex justify-between items-center text-[10px]">
                  <div className="flex items-center space-x-1">
                    <Tag className="w-3 h-3 text-apex-cyan" />
                    <span className="text-apex-muted">{Array.isArray(item.affectedAssets) ? item.affectedAssets.join(', ') : 'BTC/USDT'}</span>
                  </div>
                  <span className="text-apex-muted">{item.publishedAt}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right Column: Real ForexFactory Economic Calendar (1 col) */}
        <div className="flex flex-col space-y-3 overflow-y-auto border-l border-apex-border pl-3">
          <div className="font-bold text-apex-text text-xs flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-apex-accent" />
            <span>HIGH IMPACT ECONOMIC CALENDAR</span>
          </div>

          {economicEvents.length === 0 ? (
            <div className="p-4 text-center text-apex-muted border border-apex-border rounded-lg text-[11px]">
              Loading ForexFactory calendar...
            </div>
          ) : (
            economicEvents.map((ev) => (
              <div key={ev.id} className="bg-apex-surface border border-apex-border rounded-lg p-3 space-y-1.5 shadow-xl">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-apex-text text-[11px]">{ev.title}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${ev.severity === 'high' ? 'bg-apex-red/20 text-apex-red border border-apex-red/30' : 'bg-amber-950/30 text-amber-400 border border-amber-500/30'}`}>
                    {ev.impact}
                  </span>
                </div>
                <div className="text-[10px] text-apex-muted flex justify-between pt-1 border-t border-apex-border">
                  <span>TIME: <b className="text-apex-text">{ev.time}</b></span>
                  <span>FORECAST: <b className="text-apex-cyan">{ev.forecast}</b></span>
                  <span>PREV: <b className="text-apex-muted">{ev.previous}</b></span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
