import type { 
  TickerData, 
  SystemHealth, 
  Position, 
  Signal, 
  BacktestResult, 
  PropFirmAccount, 
  NewsArticle, 
  DevLog, 
  ServerMetric,
  User 
} from '../types';

export const currentUser: User = {
  id: 'usr_apex_01',
  name: 'Hikmatillo (Owner & Head Quant)',
  email: 'tillo4079@gmail.com',
  role: 'Owner',
  avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=250&q=80',
  twoFactorEnabled: true,
  passkeyRegistered: true
};

export const initialTickers: TickerData[] = [
  { symbol: 'BTC/USDT', price: 91420.50, change24h: 3.42, high24h: 92100.00, low24h: 88200.00, volume24h: 42150200340, fundingRate: 0.0125, openInterest: 18450200100 },
  { symbol: 'ETH/USDT', price: 3480.25, change24h: 4.85, high24h: 3510.00, low24h: 3310.50, volume24h: 21405030400, fundingRate: 0.0085, openInterest: 9450100200 },
  { symbol: 'SOL/USDT', price: 194.60, change24h: -1.25, high24h: 202.10, low24h: 191.00, volume24h: 6840200100, fundingRate: -0.0024, openInterest: 3210400500 },
  { symbol: 'BNB/USDT', price: 588.30, change24h: 0.85, high24h: 594.00, low24h: 581.20, volume24h: 1250300400, fundingRate: 0.0050, openInterest: 1105003000 },
  { symbol: 'AVAX/USDT', price: 36.45, change24h: 6.12, high24h: 37.80, low24h: 34.10, volume24h: 890400300, fundingRate: 0.0110, openInterest: 640200100 },
  { symbol: 'LINK/USDT', price: 18.90, change24h: 2.15, high24h: 19.40, low24h: 18.20, volume24h: 670300200, fundingRate: 0.0075, openInterest: 480100200 },
  { symbol: 'XRP/USDT', price: 0.584, change24h: -0.45, high24h: 0.598, low24h: 0.575, volume24h: 1450200300, fundingRate: 0.0010, openInterest: 890300400 },
];

export const systemHealthStatus: SystemHealth = {
  vpsStatus: 'ONLINE',
  vpsLatency: 2,
  exchangeApiStatus: 'CONNECTED',
  exchangeLatency: 14,
  dbStatus: 'HEALTHY',
  dbLatency: 3,
  wsStatus: 'STREAMING',
  wsLatency: 8,
  pythonEngineStatus: 'RUNNING',
  aiEngineStatus: 'ACTIVE'
};

export const initialPositions: Position[] = [];

export const initialSignals: Signal[] = [];

export const propFirmAccounts: PropFirmAccount[] = [
  {
    id: 'pf_01',
    firmName: 'FTMO',
    accountNumber: 'FTMO-10K-CHALLENGE-01',
    stage: 'Funded',
    initialBalance: 10000,
    currentBalance: 10000,
    targetBalance: 11000,
    maxDailyDrawdownPct: 5.0,
    currentDailyDrawdownPct: 0.00,
    maxTotalDrawdownPct: 10.0,
    currentTotalDrawdownPct: 0.00,
    passProbability: 99.4,
    consistencyScore: 98.5,
    violationWarning: false,
    daysRemaining: 30,
    projectedFinishDate: '2026-08-31'
  },
  {
    id: 'pf_02',
    firmName: 'FTMO',
    accountNumber: 'FTMO-10K-CHALLENGE-02',
    stage: 'Funded',
    initialBalance: 10000,
    currentBalance: 10000,
    targetBalance: 11000,
    maxDailyDrawdownPct: 5.0,
    currentDailyDrawdownPct: 0.00,
    maxTotalDrawdownPct: 10.0,
    currentTotalDrawdownPct: 0.00,
    passProbability: 99.4,
    consistencyScore: 98.2,
    violationWarning: false,
    daysRemaining: 30,
    projectedFinishDate: '2026-08-31'
  },
  {
    id: 'pf_03',
    firmName: 'FTMO',
    accountNumber: 'FTMO-10K-CHALLENGE-03',
    stage: 'Evaluation 2',
    initialBalance: 10000,
    currentBalance: 10000,
    targetBalance: 10500,
    maxDailyDrawdownPct: 5.0,
    currentDailyDrawdownPct: 0.00,
    maxTotalDrawdownPct: 10.0,
    currentTotalDrawdownPct: 0.00,
    passProbability: 99.1,
    consistencyScore: 97.8,
    violationWarning: false,
    daysRemaining: 25,
    projectedFinishDate: '2026-08-28'
  }
];

export const mockBacktest: BacktestResult = {
  id: 'bt_apex_audited_2026',
  strategyName: 'APEX Quant Engine v3.2 (Audited)',
  symbol: 'BTC/USDT & ETH/USDT',
  timeframe: 'M15',
  initialBalance: 10000,
  finalBalance: 15530,
  netProfit: 5530,
  profitFactor: 1.81,
  winRate: 62.3,
  sharpeRatio: 5.07,
  sortinoRatio: 5.52,
  maxDrawdown: 0.87,
  totalTrades: 368,
  avgRR: 2.85,
  avgHoldingTime: '58m',
  monthlyReturns: [
    { month: 'Aug', returnPct: 4.5 },
    { month: 'Sep', returnPct: 5.2 },
    { month: 'Oct', returnPct: 3.8 },
    { month: 'Nov', returnPct: 6.1 },
    { month: 'Dec', returnPct: 4.9 },
    { month: 'Jan', returnPct: 5.4 },
    { month: 'Feb', returnPct: 3.9 },
    { month: 'Mar', returnPct: 4.8 },
    { month: 'Apr', returnPct: 5.1 },
    { month: 'May', returnPct: 3.6 },
    { month: 'Jun', returnPct: 4.2 },
    { month: 'Jul', returnPct: 3.8 }
  ],
  equityCurve: [
    { timestamp: '2025-08', equity: 10000, drawdown: 0 },
    { timestamp: '2025-10', equity: 10830, drawdown: 0.2 },
    { timestamp: '2025-12', equity: 11890, drawdown: 0.4 },
    { timestamp: '2026-02', equity: 12980, drawdown: 0.5 },
    { timestamp: '2026-04', equity: 14120, drawdown: 0.7 },
    { timestamp: '2026-06', equity: 14950, drawdown: 0.8 },
    { timestamp: '2026-08', equity: 15530, drawdown: 0.87 }
  ]
};

export const newsArticles: NewsArticle[] = [
  {
    id: 'news_01',
    title: 'Fed Signals Potential Rate Shift as Inflation Cools to Target Range',
    source: 'Bloomberg',
    summary: 'Institutional yield markets reprice rate cut probabilities to 88% for the upcoming FOMC meeting, driving risk asset expansion across crypto and tech equities.',
    sentiment: 'BULLISH',
    sentimentScore: 0.88,
    impactLevel: 'HIGH',
    affectedAssets: ['BTC', 'ETH', 'NDX'],
    publishedAt: '12m ago',
    readTime: '2 min'
  },
  {
    id: 'news_02',
    title: 'BlackRock Bitcoin ETF Records $640M Net Inflow in Single Session',
    source: 'Reuters',
    summary: 'IBIT dominates institutional volume as sovereign fund allocations begin trickling into US spot ETF wrappers.',
    sentiment: 'BULLISH',
    sentimentScore: 0.94,
    impactLevel: 'HIGH',
    affectedAssets: ['BTC', 'IBIT'],
    publishedAt: '45m ago',
    readTime: '3 min'
  },
  {
    id: 'news_03',
    title: 'CME Derivatives Open Interest Hits All-Time High of $12.4 Billion',
    source: 'CoinDesk',
    summary: 'Institutional traders expand futures and options exposure ahead of quarterly expiration cycles.',
    sentiment: 'NEUTRAL',
    sentimentScore: 0.52,
    impactLevel: 'MEDIUM',
    affectedAssets: ['BTC', 'ETH'],
    publishedAt: '2h ago',
    readTime: '1 min'
  }
];

export const initialLogs: DevLog[] = [
  { id: 'log_1', timestamp: '13:00:14.204', category: 'Python', level: 'INFO', message: 'APEX_M5_Engine initialized. Model weights loaded from /weights/apex_v4.2.onnx' },
  { id: 'log_2', timestamp: '13:00:15.012', category: 'WebSocket', level: 'SUCCESS', message: 'ccxt.pro WebSocket connection established to Binance Futures (8ms latency)' },
  { id: 'log_3', timestamp: '13:00:16.890', category: 'Redis', level: 'INFO', message: 'Redis pub/sub subscriber listening on channel [apex_tick_stream]' },
  { id: 'log_4', timestamp: '13:00:17.110', category: 'Execution', level: 'SUCCESS', message: 'Position pos_001 trailing stop updated to $87,800.00 (+1.25% lock)' },
  { id: 'log_5', timestamp: '13:00:18.005', category: 'Docker', level: 'INFO', message: 'Container apex_celery_worker_1 healthy (0.4% CPU, 120MB RAM)' }
];

export const serverMetrics: ServerMetric = {
  cpuUsagePct: 24.5,
  gpuUsagePct: 41.2,
  ramUsedGb: 14.8,
  ramTotalGb: 64.0,
  diskUsedGb: 128.4,
  diskTotalGb: 1024.0,
  latencyMs: 12,
  dockerContainers: [
    { name: 'apex_api_fastapi', status: 'running', cpu: '1.2%', mem: '180MB' },
    { name: 'apex_ai_engine', status: 'running', cpu: '18.4%', mem: '2.4GB' },
    { name: 'apex_redis_pubsub', status: 'running', cpu: '0.8%', mem: '95MB' },
    { name: 'apex_postgres_db', status: 'running', cpu: '2.1%', mem: '410MB' },
    { name: 'apex_celery_worker', status: 'running', cpu: '1.9%', mem: '210MB' },
  ],
  redisStatus: 'ACTIVE',
  postgresStatus: 'ACTIVE',
  celeryWorkers: 4
};
