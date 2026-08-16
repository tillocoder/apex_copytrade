import type { Position, PropFirmAccount } from '../types';

export interface RiskAnalysisResult {
  currentDailyDrawdownPct: number;
  currentTotalDrawdownPct: number;
  remainingDailyLossAmount: number;
  remainingTotalDrawdownAmount: number;
  safeRiskRemainingAmount: number;
  recommendedLeverage: number;
  maxAllowedLotSize: number;
  passProbability: number;
  consistencyScore: number;
  projectedFinishDate: string;
  isViolationWarning: boolean;
  violationReason?: string;
}

export class PropFirmEngine {
  public static calculateRisk(
    account: PropFirmAccount | undefined | null,
    activePositions: Position[],
    accountEquity: number = 10000
  ): RiskAnalysisResult {
    const safeAccount: PropFirmAccount = account || {
      id: 'pf_default',
      firmName: 'FTMO',
      accountNumber: 'FTMO-10K-EVAL',
      stage: 'Funded',
      initialBalance: 10000,
      currentBalance: 10000,
      targetBalance: 11000,
      maxDailyDrawdownPct: 5.0,
      currentDailyDrawdownPct: 0.0,
      maxTotalDrawdownPct: 10.0,
      currentTotalDrawdownPct: 0.0,
      passProbability: 99.4,
      consistencyScore: 98.0,
      violationWarning: false,
      daysRemaining: 30,
      projectedFinishDate: '2026-08-31'
    };

    const currentUnrealizedPnl = activePositions.reduce((acc, p) => acc + (p?.unrealizedPnl || 0), 0);

    const initialCap = safeAccount.initialBalance || 10000;
    const maxDailyLossAllowed = (initialCap * (safeAccount.maxDailyDrawdownPct || 5.0)) / 100;
    const currentDailyDrawdownPct = Math.max(0, safeAccount.currentDailyDrawdownPct || 0);
    const remainingDailyLossAmount = Math.max(0, maxDailyLossAllowed - (initialCap * currentDailyDrawdownPct / 100));

    // Overall drawdown calculation
    const maxTotalDrawdownAllowed = (initialCap * (safeAccount.maxTotalDrawdownPct || 10.0)) / 100;
    const currentTotalDrawdownPct = Math.max(0, safeAccount.currentTotalDrawdownPct || 0);
    const remainingTotalDrawdownAmount = Math.max(0, maxTotalDrawdownAllowed - (initialCap * currentTotalDrawdownPct / 100));

    // Safe Risk Remaining (Cap at 1.5% of equity or remaining daily loss limit)
    const safeRiskRemainingAmount = Math.min(remainingDailyLossAmount * 0.75, accountEquity * 0.015);

    // Max allowed position size (based on $91,420 BTC price and 1.5% stop loss)
    const maxAllowedLotSize = Number(((safeRiskRemainingAmount / (91420 * 0.015))).toFixed(2));

    // Recommended Leverage (stay conservative based on current drawdown)
    const recommendedLeverage = currentDailyDrawdownPct > 3.0 ? 5 : currentDailyDrawdownPct > 1.5 ? 10 : 20;

    const isViolationWarning = currentDailyDrawdownPct >= (safeAccount.maxDailyDrawdownPct || 5.0) * 0.8 || currentTotalDrawdownPct >= (safeAccount.maxTotalDrawdownPct || 10.0) * 0.8;
    const violationReason = isViolationWarning ? 'Approaching max daily loss threshold (80% used)' : undefined;

    return {
      currentDailyDrawdownPct,
      currentTotalDrawdownPct,
      remainingDailyLossAmount,
      remainingTotalDrawdownAmount,
      safeRiskRemainingAmount,
      recommendedLeverage,
      maxAllowedLotSize,
      passProbability: safeAccount.passProbability || 99.4,
      consistencyScore: safeAccount.consistencyScore || 98.0,
      projectedFinishDate: safeAccount.projectedFinishDate || '2026-08-31',
      isViolationWarning,
      violationReason
    };
  }
}
