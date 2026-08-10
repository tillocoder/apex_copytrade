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
    account: PropFirmAccount,
    activePositions: Position[],
    accountEquity: number = 109850
  ): RiskAnalysisResult {
    const currentUnrealizedPnl = activePositions.reduce((acc, p) => acc + p.unrealizedPnl, 0);

    // Daily loss limit calculation
    const maxDailyLossAllowed = (account.initialBalance * account.maxDailyDrawdownPct) / 100;
    const currentDailyDrawdownPct = Math.max(0, account.currentDailyDrawdownPct);
    const remainingDailyLossAmount = Math.max(0, maxDailyLossAllowed - (account.initialBalance * currentDailyDrawdownPct / 100));

    // Overall drawdown calculation
    const maxTotalDrawdownAllowed = (account.initialBalance * account.maxTotalDrawdownPct) / 100;
    const currentTotalDrawdownPct = Math.max(0, account.currentTotalDrawdownPct);
    const remainingTotalDrawdownAmount = Math.max(0, maxTotalDrawdownAllowed - (account.initialBalance * currentTotalDrawdownPct / 100));

    // Safe Risk Remaining (Cap at 1.5% of equity or remaining daily loss limit)
    const safeRiskRemainingAmount = Math.min(remainingDailyLossAmount * 0.75, accountEquity * 0.015);

    // Max allowed position size (based on $91,420 BTC price and 1.5% stop loss)
    const maxAllowedLotSize = Number(((safeRiskRemainingAmount / (91420 * 0.015))).toFixed(2));

    // Recommended Leverage (stay conservative based on current drawdown)
    const recommendedLeverage = currentDailyDrawdownPct > 3.0 ? 5 : currentDailyDrawdownPct > 1.5 ? 10 : 20;

    const isViolationWarning = currentDailyDrawdownPct >= account.maxDailyDrawdownPct * 0.8 || currentTotalDrawdownPct >= account.maxTotalDrawdownPct * 0.8;
    const violationReason = isViolationWarning ? 'Approaching max daily loss threshold (80% used)' : undefined;

    return {
      currentDailyDrawdownPct,
      currentTotalDrawdownPct,
      remainingDailyLossAmount,
      remainingTotalDrawdownAmount,
      safeRiskRemainingAmount,
      recommendedLeverage,
      maxAllowedLotSize,
      passProbability: account.passProbability,
      consistencyScore: account.consistencyScore,
      projectedFinishDate: account.projectedFinishDate,
      isViolationWarning,
      violationReason
    };
  }
}
