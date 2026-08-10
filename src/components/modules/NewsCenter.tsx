import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { Newspaper, Flame, Tag, Clock, ExternalLink } from 'lucide-react';

export const NewsCenter: React.FC = () => {
  const { news } = useTerminal();

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Newspaper className="w-5 h-5 text-apex-cyan" />
          <span>AI-SUMMARIZED INSTITUTIONAL NEWS TERMINAL</span>
        </div>
        <div className="text-[11px] text-apex-muted">NLP SENTIMENT SCORING ACTIVE</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-y-auto">
        {news.map((item) => (
          <div key={item.id} className="bg-apex-surface border border-apex-border rounded-lg p-4 space-y-3 shadow-xl">
            <div className="flex items-center justify-between">
              <span className="bg-apex-panel px-2 py-0.5 rounded text-[10px] text-apex-cyan border border-apex-border font-bold">
                {item.source}
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                item.sentiment === 'BULLISH' ? 'bg-apex-green/20 text-apex-green' : 'bg-amber-950 text-amber-400'
              }`}>
                {item.sentiment} ({Math.round(item.sentimentScore * 100)}%)
              </span>
            </div>

            <h3 className="font-bold text-sm text-apex-text leading-snug">{item.title}</h3>
            <p className="text-apex-muted text-[11px] leading-relaxed">{item.summary}</p>

            <div className="pt-2 border-t border-apex-border flex justify-between items-center text-[10px]">
              <div className="flex items-center space-x-1">
                <Tag className="w-3 h-3 text-apex-cyan" />
                <span className="text-apex-muted">{item.affectedAssets.join(', ')}</span>
              </div>
              <span className="text-apex-muted">{item.publishedAt}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
