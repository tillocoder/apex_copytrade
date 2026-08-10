import React from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { ShieldCheck, CheckCircle2 } from 'lucide-react';

export const PropFirmCenter: React.FC = () => {
  const { propAccounts } = useTerminal();

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-sans text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3 font-mono">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <ShieldCheck className="w-5 h-5 text-apex-accent" />
          <span>PROP FIRM GUARDIAN & RULE ENFORCEMENT</span>
        </div>
        <div className="text-[11px] text-apex-muted">REAL-TIME RISK LIMITS ACTIVE</div>
      </div>

      {/* Grid of Linked Accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-y-auto">
        {propAccounts.map((acc) => {
          const currentProfit = acc.currentBalance - acc.initialBalance;
          const targetProfit = acc.targetBalance - acc.initialBalance;
          const progressPct = Math.min(100, Math.max(0, (currentProfit / targetProfit) * 100));

          return (
            <div key={acc.id} className="workstation-panel p-4 space-y-4 font-mono">
              {/* Account Title */}
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-sm text-apex-text">{acc.firmName} ({acc.accountNumber})</div>
                  <div className="text-[10px] text-apex-muted">{acc.stage} Account</div>
                </div>
                <span className="bg-apex-surface border border-apex-border text-apex-textSecondary text-[10px] px-2 py-0.5 rounded font-mono">
                  PASS PROB {acc.passProbability}%
                </span>
              </div>

              {/* Balance Progress Bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-apex-muted">CHALLENGE TARGET PROGRESS</span>
                  <span className="font-bold text-apex-success">${currentProfit.toLocaleString()} / ${targetProfit.toLocaleString()}</span>
                </div>
                <div className="w-full h-1.5 bg-apex-bg rounded-full overflow-hidden border border-apex-border">
                  <div className="h-full bg-apex-success" style={{ width: `${progressPct}%` }} />
                </div>
              </div>

              {/* Drawdown Breakdown */}
              <div className="grid grid-cols-2 gap-2 bg-apex-bg p-2.5 rounded-md border border-apex-border text-[11px]">
                <div>
                  <div className="text-apex-muted text-[9px]">MAX DAILY DD</div>
                  <div className="font-bold text-apex-warning">{acc.currentDailyDrawdownPct}% / {acc.maxDailyDrawdownPct}%</div>
                </div>
                <div>
                  <div className="text-apex-muted text-[9px]">MAX TOTAL DD</div>
                  <div className="font-bold text-apex-accent">{acc.currentTotalDrawdownPct}% / {acc.maxTotalDrawdownPct}%</div>
                </div>
              </div>

              {/* Consistency & Timeline */}
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-apex-muted">CONSISTENCY SCORE:</span>
                  <span className="font-bold text-apex-text">{acc.consistencyScore}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-apex-muted">DAYS REMAINING:</span>
                  <span className="font-bold text-apex-text">{acc.daysRemaining} Days</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-apex-muted">PROJECTED FINISH:</span>
                  <span className="font-bold text-apex-success">{acc.projectedFinishDate}</span>
                </div>
              </div>

              {/* Safety Rail Guard Status */}
              <div className="p-2.5 rounded-md bg-apex-bg border border-apex-border flex items-center space-x-2 text-[11px] text-apex-textSecondary">
                <CheckCircle2 className="w-4 h-4 text-apex-success shrink-0" />
                <span>Auto-Killswitch Armed. 0 Violations.</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
