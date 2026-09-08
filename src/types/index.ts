export type UserRole = 'Owner' | 'Administrator' | 'Quant Developer' | 'Trader' | 'Risk Manager' | 'Viewer' | 'Guest';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  twoFactorEnabled: boolean;
  passkeyRegistered: boolean;
}

export type ModuleView = 
  | 'login'
  | 'home'
  | 'trades'
  | 'command-center'
  | 'signals'
  | 'backtest'
  | 'prop-firm'
  | 'intelligence'
  | 'news'
  | 'portfolio'
  | 'journal'
  | 'analytics'
  | 'copilot'
  | 'team'
  | 'automation'
  | 'server'
  | 'settings'
  | 'admin';

export interface TickerData {
  symbol: string;
  price: number;
  change24h: number;
  high24h: number;
  low24h: number;
  volume24h: number;
  fundingRate: number;
  openInterest: number;
}

export interface SystemHealth {
  vpsStatus: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  vpsLatency: number;
  exchangeApiStatus: 'CONNECTED' | 'DISCONNECTED';
  exchangeLatency: number;
  dbStatus: 'HEALTHY' | 'SYNCING' | 'ERROR';
  dbLatency: number;
  wsStatus: 'STREAMING' | 'RECONNECTING' | 'PAUSED';
  wsLatency: number;
  pythonEngineStatus: 'RUNNING' | 'PAUSED' | 'CRASHED';
  aiEngineStatus: 'ACTIVE' | 'CALIBRATING';
}

export interface TradeTimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  reason: string;
  triggeredBy: string;
  riskImpact: string;
  challengeImpact: string;
  severity: 'info' | 'success' | 'warning' | 'danger';
}

export type AIRecommendation = 'HOLD' | 'SCALE_IN' | 'SCALE_OUT' | 'MOVE_SL_BREAKEVEN' | 'TAKE_PARTIAL' | 'CLOSE_NOW';

export interface Position {
  id: string;
  account: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entryPrice: number;
  currentPrice: number;
  size: number;
  leverage: number;
  marginUsed: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  sl: number;
  tp1: number;
  tp2: number;
  tp3: number;
  breakEvenPrice?: number;
  trailingStopActive: boolean;
  trailingDistancePct?: number;
  atr: number;
  riskPercent: number;
  rewardPercent: number;
  expectedProfit: number;
  expectedLoss: number;
  commission: number;
  fundingFee: number;
  swapFees: number;
  liquidationPrice: number;
  duration: string;
  timeOpen: string;
  aiExplanation: string;
  aiConfidence: number;
  aiRecommendation: AIRecommendation;
  expectedNextMove: string;
  reason: string;
  pattern: string;
  volumeProfile: string;
  trendStatus: string;
  orderFlowAnalysis: string;
  liquidityAnalysis: string;
  positionHealthScore: number; // 0 - 100
  executionQualityScore: number; // 0 - 100
  status: 'OPEN' | 'PARTIAL' | 'CLOSED';
  timeline: TradeTimelineEvent[];
}

export interface Signal {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  timeframe: 'M1' | 'M5' | 'M15' | 'H1' | 'H4' | 'D1';
  aiScore: number;
  confidence: number;
  probability: number;
  rr: number;
  entry: number;
  sl: number;
  tp: number;
  tp1?: number;
  tp2?: number;
  tp3?: number;
  timestamp?: number;
  exit_timestamp?: number;
  leverage?: number;
  reasoning?: string;
  status: 'PENDING' | 'CONFIRMED' | 'EXPIRED' | 'INVALIDATED';
  trendConfirmation: boolean;
  mtfConfirmation: boolean;
  liquidityConfirmation: boolean;
  volumeConfirmation: boolean;
  patternConfirmation: boolean;
  aiNotes: string;
  createdAt: string;
}

export interface BacktestResult {
  status?: string;
  id?: string;
  strategyName: string;
  symbol: string;
  timeframe: string;
  period?: string;
  initialBalance: number;
  finalBalance: number;
  netProfit: number;
  cagr?: number;
  profitFactor: number;
  winRate: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  totalTrades: number;
  backtestTradesCount?: number;
  liveTradesCount?: number;
  avgRR: number;
  avgHoldingTime: string;
  monthlyReturns: { month: string; returnPct: number }[];
  equityCurve: { timestamp: string; equity: number; drawdown?: number; type?: string }[];
  liveEquityCurve?: { timestamp: string; equity: number; drawdown?: number; type?: string; pnl?: number; symbol?: string }[];
  portfolioEquityCurve?: { timestamp: string; equity: number; type?: 'backtest' | 'live'; pnl?: number; symbol?: string }[];
  passedChallenges?: { 
    id: string; 
    firm?: string;
    size?: string;
    stage1PassTime: string; 
    stage2PassTime: string; 
    daysTaken: number; 
    status: string;
    payout?: string;
  }[];
  propSummary?: {
    completedChallenges: number;
    stage1Passed: number;
    stage2Passed: number;
    failedChallenges: number;
    successRatePct: number;
    avgDaysPerChallenge: number;
    totalPropPayouts?: string;
    activeAccount?: string;
  };
}

export interface PropFirmAccount {
  id: string;
  firmName: 'BitFunded' | 'FundedNext' | 'FTMO' | 'The5ers' | 'FundingPips' | 'HashHedge';
  accountNumber: string;
  stage: 'Evaluation 1' | 'Evaluation 2' | 'Funded' | 'Scaling';
  initialBalance: number;
  currentBalance: number;
  targetBalance: number;
  maxDailyDrawdownPct: number;
  currentDailyDrawdownPct: number;
  maxTotalDrawdownPct: number;
  currentTotalDrawdownPct: number;
  passProbability: number;
  consistencyScore: number;
  violationWarning: boolean;
  daysRemaining: number;
  projectedFinishDate: string;
}

export interface NewsArticle {
  id: string;
  title: string;
  source: 'CoinDesk' | 'Cointelegraph' | 'CryptoPanic' | 'Reuters' | 'Bloomberg' | 'Twitter/X';
  summary: string;
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  sentimentScore: number;
  impactLevel: 'HIGH' | 'MEDIUM' | 'LOW';
  affectedAssets: string[];
  publishedAt: string;
  readTime: string;
}

export interface DevLog {
  id: string;
  timestamp: string;
  category: 'Python' | 'Execution' | 'Exchange' | 'Database' | 'Redis' | 'Docker' | 'WebSocket' | 'Error';
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
  message: string;
}

export interface ServerMetric {
  cpuUsagePct: number;
  gpuUsagePct: number;
  ramUsedGb: number;
  ramTotalGb: number;
  diskUsedGb: number;
  diskTotalGb: number;
  latencyMs: number;
  dockerContainers: { name: string; status: 'running' | 'exited'; cpu: string; mem: string }[];
  redisStatus: 'ACTIVE' | 'DEGRADED';
  postgresStatus: 'ACTIVE' | 'DEGRADED';
  celeryWorkers: number;
}
