import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { PropFirmEngine } from '../../services/propFirmEngine';
import { ShieldCheck, ShieldAlert, AlertTriangle, Calculator, Percent } from 'lucide-react';

export const RiskWorkspace: React.FC = () => {
  const { propAccounts, positions } = useTerminal();
  const activePropAccount = propAccounts[0];

  const [plannedStopLossPts, setPlannedStopLossPts] = useState<number>(500);

  const riskStats = PropFirmEngine.calculateRisk(activePropAccount, positions);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <ShieldCheck className="w-5 h-5 text-apex-accent" />
          <span>DEDICATED RISK WORKSPACE & PROP FIRM ENGINE</span>
        </div>
        <div className="text-[11px] text-apex-success font-bold">ALL RISK RULES COMPLIANT</div>
      </div>

      {/* Top Level Challenge Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">REMAINING DAILY LOSS</div>
          <div className="text-2xl font-bold text-apex-success">${riskStats.remainingDailyLossAmount.toLocaleString()}</div>
          <div className="text-[10px] text-apex-muted">Limit: {activePropAccount.maxDailyDrawdownPct}% ($5,000)</div>
        </div>

        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">REMAINING OVERALL DD</div>
          <div className="text-2xl font-bold text-apex-accent">${riskStats.remainingTotalDrawdownAmount.toLocaleString()}</div>
          <div className="text-[10px] text-apex-muted">Limit: {activePropAccount.maxTotalDrawdownPct}% ($10,000)</div>
        </div>

        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">SAFE RISK AVAILABLE</div>
          <div className="text-2xl font-bold text-apex-text">${riskStats.safeRiskRemainingAmount.toLocaleString()}</div>
          <div className="text-[10px] text-apex-muted">Cap: 1.5% max risk per trade</div>
        </div>

        <div className="workstation-panel p-4 space-y-1">
          <div className="text-apex-muted text-[10px]">RECOMMENDED MAX LOTS</div>
          <div className="text-2xl font-bold text-apex-warning">{riskStats.maxAllowedLotSize} CONTRACTS</div>
          <div className="text-[10px] text-apex-muted">Max Lev: {riskStats.recommendedLeverage}X</div>
        </div>
      </div>

      {/* Position Calculator & Prop Rules Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Position Size Calculator */}
        <div className="workstation-panel p-4 space-y-3 font-sans">
          <div className="font-bold text-xs text-apex-text font-mono flex items-center gap-1.5 border-b border-apex-border pb-2">
            <Calculator className="w-4 h-4 text-apex-accent" /> REAL-TIME POSITION SIZE CALCULATOR
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="text-[10px] text-apex-muted font-mono">PLANNED STOP LOSS DISTANCE (POINTS / $)</label>
              <input 
                type="number"
                value={plannedStopLossPts}
                onChange={(e) => setPlannedStopLossPts(Number(e.target.value))}
                className="w-full bg-apex-bg border border-apex-border rounded-btn px-3 py-2 text-apex-text font-bold font-mono outline-none"
              />
            </div>

            <div className="p-3 bg-apex-bg rounded-panel border border-apex-border space-y-1.5 font-mono text-[11px]">
              <div className="flex justify-between"><span className="text-apex-muted">RECOMMENDED POSITION SIZE:</span><strong className="text-apex-success">{(riskStats.safeRiskRemainingAmount / plannedStopLossPts).toFixed(2)} Contracts</strong></div>
              <div className="flex justify-between"><span className="text-apex-muted">TOTAL RISK IN DOLLARS:</span><strong className="text-apex-danger">${riskStats.safeRiskRemainingAmount.toFixed(2)}</strong></div>
              <div className="flex justify-between"><span className="text-apex-muted">IMPACT ON DAILY DRAWDOWN:</span><strong className="text-apex-warning">+{(riskStats.safeRiskRemainingAmount / activePropAccount.initialBalance * 100).toFixed(2)}%</strong></div>
            </div>
          </div>
        </div>

        {/* Emergency Breach Guard Status */}
        <div className="workstation-panel p-4 space-y-3 font-mono">
          <div className="font-bold text-xs text-apex-text border-b border-apex-border pb-2">
            RULE VIOLATION DETECTOR & HEALTH
          </div>

          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between py-1 border-b border-apex-border">
              <span className="text-apex-muted">PASS PROBABILITY:</span>
              <span className="font-bold text-apex-success">{riskStats.passProbability}%</span>
            </div>
            <div className="flex justify-between py-1 border-b border-apex-border">
              <span className="text-apex-muted">CONSISTENCY SCORE:</span>
              <span className="font-bold text-apex-accent">{riskStats.consistencyScore}%</span>
            </div>
            <div className="flex justify-between py-1 border-b border-apex-border">
              <span className="text-apex-muted">PROJECTED FINISH DATE:</span>
              <span className="font-bold text-apex-text">{riskStats.projectedFinishDate}</span>
            </div>
          </div>

          {riskStats.isViolationWarning ? (
            <div className="p-3 rounded-panel bg-apex-danger/15 border border-apex-danger text-apex-danger flex items-center space-x-2 text-xs">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <span>{riskStats.violationReason}</span>
            </div>
          ) : (
            <div className="p-3 rounded-panel bg-apex-surface border border-apex-border text-apex-success flex items-center space-x-2 text-xs">
              <ShieldCheck className="w-5 h-5 shrink-0 text-apex-success" />
              <span>All 5 challenge risk rules fully compliant. Zero violations detected.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
