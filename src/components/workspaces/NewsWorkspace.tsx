import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { Newspaper, Calendar, Flame, Tag } from 'lucide-react';

export const NewsWorkspace: React.FC = () => {
  const { news } = useTerminal();

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Newspaper className="w-5 h-5 text-apex-accent" />
          <span>AI NEWS TERMINAL & ECONOMIC CALENDAR</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-y-auto">
        {/* News Stream (Left 2 cols) */}
        <div className="lg:col-span-2 space-y-3 font-mono">
          <div className="text-apex-muted text-[10px] uppercase font-bold">REAL-TIME INSTITUTIONAL NEWS</div>
          {news.map((item) => (
            <div key={item.id} className="workstation-panel p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="bg-apex-surface px-2 py-0.5 rounded text-[10px] text-apex-accent border border-apex-border font-bold">
                  {item.source}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  item.sentiment === 'BULLISH' ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' : 'bg-apex-warning/15 text-apex-warning border border-apex-warning/30'
                }`}>
                  {item.sentiment} ({Math.round(item.sentimentScore * 100)}%)
                </span>
              </div>

              <h3 className="font-bold text-sm text-apex-text leading-snug">{item.title}</h3>
              <p className="text-apex-textSecondary text-[11px] leading-relaxed font-sans">{item.summary}</p>

              <div className="pt-2 border-t border-apex-border flex justify-between items-center text-[10px]">
                <div className="flex items-center space-x-1">
                  <Tag className="w-3 h-3 text-apex-accent" />
                  <span className="text-apex-muted">{item.affectedAssets.join(', ')}</span>
                </div>
                <span className="text-apex-muted">{item.publishedAt}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Economic Calendar */}
        <div className="space-y-3 font-mono">
          <div className="text-apex-muted text-[10px] uppercase font-bold">HIGH IMPACT ECONOMIC CALENDAR</div>
          <div className="workstation-panel p-4 space-y-3">
            <div className="p-2.5 bg-apex-bg rounded-md border border-apex-border space-y-1">
              <div className="flex justify-between font-bold text-apex-text text-xs">
                <span>FOMC RATE DECISION</span>
                <span className="text-apex-danger font-bold">HIGH IMPACT</span>
              </div>
              <div className="text-[10px] text-apex-muted">14:00 UTC | Forecast: 5.25% | Prev: 5.50%</div>
            </div>

            <div className="p-2.5 bg-apex-bg rounded-md border border-apex-border space-y-1">
              <div className="flex justify-between font-bold text-apex-text text-xs">
                <span>US CPI INFLATION RATE (YoY)</span>
                <span className="text-apex-warning font-bold">MED IMPACT</span>
              </div>
              <div className="text-[10px] text-apex-muted">12:30 UTC | Forecast: 2.8% | Prev: 3.0%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
