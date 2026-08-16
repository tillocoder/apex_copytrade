import React, { useEffect, useState } from 'react';
import { BookOpen, Smile, Sparkles, TrendingUp, TrendingDown, Clock, Activity } from 'lucide-react';
import { fetchJournalTrades } from '../../services/quantApiService';

export const TradeJournal: React.FC = () => {
  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchJournalTrades().then(data => {
      setTrades(data);
      setLoading(false);
    });
  }, []);

  const totalPnl = trades.reduce((acc, t) => acc + (Number(t.pnl || t.net_pnl) || 0), 0);
  const wins = trades.filter(t => (Number(t.pnl || t.net_pnl) || 0) > 0).length;
  const winRate = trades.length > 0 ? ((wins / trades.length) * 100).toFixed(1) : '0.0';

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <BookOpen className="w-5 h-5 text-apex-cyan" />
          <span>REAL QUANT TRADE JOURNAL & EXECUTION AUDITOR</span>
        </div>
        <div className="flex space-x-4 text-[11px]">
          <span className="text-apex-muted">TOTAL TRADES: <b className="text-apex-text">{trades.length}</b></span>
          <span className="text-apex-muted">WIN RATE: <b className="text-apex-green">{winRate}%</b></span>
          <span className="text-apex-muted">TOTAL PNL: <b className={totalPnl >= 0 ? 'text-apex-green' : 'text-apex-red'}>${totalPnl.toFixed(2)}</b></span>
        </div>
      </div>

      {/* Main Journal View */}
      <div className="flex-1 flex flex-col overflow-hidden bg-apex-surface border border-apex-border rounded-lg p-4 space-y-3 shadow-xl">
        <div className="flex justify-between items-center border-b border-apex-border pb-2">
          <span className="font-bold text-apex-text">AUDITED QUANT TRADE LEDGER</span>
          <span className="text-[10px] text-apex-muted">EXECUTION MODE: DETERMINISTIC BACKTEST & LIVE REPLAY</span>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-apex-muted">
            <Activity className="w-5 h-5 animate-spin mr-2 text-apex-cyan" /> Loading real trade journal...
          </div>
        ) : trades.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-2 text-apex-muted">
            <BookOpen className="w-8 h-8 text-apex-border" />
            <span>No closed trades in current ledger session. Trigger a backtest run or live signal.</span>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {trades.map((trade, idx) => {
              const pnl = Number(trade.pnl || trade.net_pnl) || 0;
              const isWin = pnl > 0;
              return (
                <div key={trade.trade_id || idx} className="bg-apex-panel border border-apex-border p-3 rounded flex justify-between items-center hover:border-apex-cyan/50 transition-apex">
                  <div className="flex items-center space-x-3">
                    {isWin ? (
                      <TrendingUp className="w-4 h-4 text-apex-green" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-apex-red" />
                    )}
                    <div>
                      <div className="font-bold text-apex-text text-xs flex items-center gap-2">
                        <span>{trade.symbol || 'BTC/USDT'}</span>
                        <span className={`px-1.5 py-0.2 text-[9px] rounded font-bold ${trade.side === 'BUY' ? 'bg-apex-green/20 text-apex-green' : 'bg-apex-red/20 text-apex-red'}`}>
                          {trade.side || 'BUY'}
                        </span>
                      </div>
                      <div className="text-[10px] text-apex-muted space-x-2">
                        <span>Entry: ${Number(trade.entry_price || trade.entryPrice || 0).toLocaleString()}</span>
                        <span>Exit: ${Number(trade.exit_price || trade.exitPrice || 0).toLocaleString()}</span>
                        <span>Bars: {trade.bars_held || 4}</span>
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className={`font-bold text-sm ${isWin ? 'text-apex-green' : 'text-apex-red'}`}>
                      {isWin ? '+' : ''}${pnl.toFixed(2)}
                    </div>
                    <div className="text-[10px] text-apex-muted">
                      {trade.reason || 'SMC_PROFIT_TARGET'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
