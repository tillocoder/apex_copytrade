import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { Bell, X, ShieldAlert, Zap, Bot, CheckCircle2, Play } from 'lucide-react';

export const NotificationDrawer: React.FC = () => {
  const { notificationsOpen, setNotificationsOpen, notifications, openCommandCenter, openReplayModal } = useTerminal();
  const [activeCategory, setActiveCategory] = useState<string>('ALL');

  if (!notificationsOpen) return null;

  const categories = ['ALL', 'Trading', 'Risk', 'Challenge', 'System', 'AI', 'News'];

  const filtered = activeCategory === 'ALL' 
    ? notifications 
    : notifications.filter(n => n.category === activeCategory);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex justify-end font-sans">
      <div className="w-full max-w-md bg-apex-bgSecondary border-l border-apex-border h-full flex flex-col shadow-panel">
        {/* Header */}
        <div className="p-4 bg-apex-surface border-b border-apex-border flex items-center justify-between font-mono">
          <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
            <Bell className="w-4 h-4 text-apex-accent" />
            <span>REAL-TIME NOTIFICATION CENTER</span>
          </div>
          <button 
            onClick={() => setNotificationsOpen(false)}
            className="p-1 rounded-md text-apex-muted hover:text-apex-text transition-apex"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Category Filters */}
        <div className="p-2 border-b border-apex-border bg-apex-bg flex space-x-1 overflow-x-auto no-scrollbar font-mono text-xs">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium whitespace-nowrap transition-apex ${
                activeCategory === cat 
                  ? 'bg-apex-hover text-apex-accent border border-apex-border' 
                  : 'text-apex-muted hover:text-apex-text'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* List of Notifications */}
        <div className="flex-1 p-3 overflow-y-auto space-y-2 font-mono text-xs">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-apex-muted">NO NOTIFICATIONS IN THIS CATEGORY</div>
          ) : (
            filtered.map((n) => (
              <div 
                key={n.id} 
                className="p-3 workstation-panel hover:bg-apex-hover transition-apex space-y-1.5 cursor-pointer"
                onClick={() => {
                  if (n.positionId) {
                    openCommandCenter(n.positionId);
                    setNotificationsOpen(false);
                  }
                }}
              >
                <div className="flex items-center justify-between">
                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                    n.severity === 'success' ? 'bg-apex-success/15 text-apex-success border border-apex-success/30' :
                    n.severity === 'danger' ? 'bg-apex-danger/15 text-apex-danger border border-apex-danger/30' :
                    n.severity === 'warning' ? 'bg-apex-warning/15 text-apex-warning border border-apex-warning/30' :
                    'bg-apex-surface text-apex-accent border border-apex-border'
                  }`}>
                    {n.category}
                  </span>
                  <span className="text-apex-muted text-[10px]">{n.timestamp}</span>
                </div>

                <div className="font-bold text-apex-text text-xs">{n.title}</div>
                <div className="text-apex-textSecondary text-[11px] leading-relaxed font-sans">{n.description}</div>

                {n.positionId && (
                  <div className="pt-1 flex items-center justify-between text-[10px] text-apex-accent">
                    <span>Click to open Position Command Center</span>
                    <button 
                      onClick={(e) => { e.stopPropagation(); openReplayModal(n.positionId!); setNotificationsOpen(false); }}
                      className="flex items-center space-x-1 text-apex-ai font-bold hover:underline"
                    >
                      <Play className="w-3 h-3 fill-apex-ai" />
                      <span>Replay Event</span>
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
