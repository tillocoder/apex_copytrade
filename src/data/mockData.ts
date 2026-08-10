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

export const initialSignals: Signal[] = [
  {
    id: 'sig_101',
    symbol: 'BTC/USDT',
    side: 'BUY',
    timeframe: 'M15',
    aiScore: 94.8,
    confidence: 92.5,
    probability: 84.0,
    rr: 3.8,
    entry: 64800.00,
    sl: 63800.00,
    tp: 66500.00,
    status: 'CONFIRMED',
    trendConfirmation: true,
    mtfConfirmation: true,
    liquidityConfirmation: true,
    volumeConfirmation: true,
    patternConfirmation: true,
    aiNotes: '15m Bullish SMC Order Block Sweep + Positive CME Delta Imbalance.',
    createdAt: '5 mins ago'
  },
  {
    id: 'sig_102',
    symbol: 'ETH/USDT',
    side: 'BUY',
    timeframe: 'H1',
    aiScore: 91.2,
    confidence: 90.0,
    probability: 81.5,
    rr: 3.2,
    entry: 3460.00,
    sl: 3390.00,
    tp: 3550.00,
    status: 'CONFIRMED',
    trendConfirmation: true,
    mtfConfirmation: true,
    liquidityConfirmation: true,
    volumeConfirmation: true,
    patternConfirmation: true,
    aiNotes: '4H CHOCH confirmation after breaking 3450 swing high with high volume.',
    createdAt: '15 mins ago'
  },
  {
    id: 'sig_103',
    symbol: 'SOL/USDT',
    side: 'SELL',
    timeframe: 'M15',
    aiScore: 88.4,
    confidence: 87.0,
    probability: 76.5,
    rr: 2.7,
    entry: 147.00,
    sl: 150.00,
    tp: 142.00,
    status: 'CONFIRMED',
    trendConfirmation: true,
    mtfConfirmation: true,
    liquidityConfirmation: true,
    volumeConfirmation: true,
    patternConfirmation: true,
    aiNotes: '15m SFP Liquidity Sweep above $147 level followed by market sell delta.',
    createdAt: '25 mins ago'
  }
];

export const propFirmAccounts: PropFirmAccount[] = [
  {
    id: 'pf_01',
    firmName: 'FTMO',
    accountNumber: 'FTMO-100K-9402',
    stage: 'Funded',
    initialBalance: 100000,
    currentBalance: 100000,
    targetBalance: 110000,
    maxDailyDrawdownPct: 5.0,
    currentDailyDrawdownPct: 0.00,
    maxTotalDrawdownPct: 10.0,
    currentTotalDrawdownPct: 0.00,
    passProbability: 99.5,
    consistencyScore: 98.0,
    violationWarning: false,
    daysRemaining: 30,
    projectedFinishDate: '2026-08-31'
  },
  {
    id: 'pf_02',
    firmName: 'FundedNext',
    accountNumber: 'FN-200K-3310',
    stage: 'Evaluation 2',
    initialBalance: 200000,
    currentBalance: 200000,
    targetBalance: 216000,
    maxDailyDrawdownPct: 5.0,
    currentDailyDrawdownPct: 0.00,
    maxTotalDrawdownPct: 10.0,
    currentTotalDrawdownPct: 0.00,
    passProbability: 96.2,
    consistencyScore: 95.0,
    violationWarning: false,
    daysRemaining: 25,
    projectedFinishDate: '2026-08-28'
  },
  {
    id: 'pf_03',
    firmName: 'The5ers',
    accountNumber: 'T5-50K-8819',
    stage: 'Evaluation 1',
    initialBalance: 50000,
    currentBalance: 50000,
    targetBalance: 54000,
    maxDailyDrawdownPct: 4.0,
    currentDailyDrawdownPct: 0.00,
    maxTotalDrawdownPct: 8.0,
    currentTotalDrawdownPct: 0.00,
    passProbability: 94.0,
    consistencyScore: 92.5,
    violationWarning: false,
    daysRemaining: 30,
    projectedFinishDate: '2026-08-31'
  }
];

export const mockBacktest: BacktestResult = {
  id: 'bt_apex_alpha_v4',
  strategyName: 'APEX Neural OrderFlow v4.2',
  symbol: 'BTC/USDT & ETH/USDT',
  timeframe: 'M5 / M15 Dual',
  initialBalance: 100000,
  finalBalance: 284500,
  netProfit: 184500,
  profitFactor: 2.85,
  winRate: 68.4,
  sharpeRatio: 3.12,
  sortinoRatio: 4.45,
  maxDrawdown: 6.2,
  totalTrades: 428,
  avgRR: 2.45,
  avgHoldingTime: '42m 15s',
  monthlyReturns: [
    { month: 'Jan', returnPct: 14.2 },
    { month: 'Feb', returnPct: 18.5 },
    { month: 'Mar', returnPct: 9.8 },
    { month: 'Apr', returnPct: 22.1 },
    { month: 'May', returnPct: 16.4 },
    { month: 'Jun', returnPct: -2.1 },
    { month: 'Jul', returnPct: 25.8 },
  ],
  equityCurve: [
    { timestamp: '01/01', equity: 100000, drawdown: 0 },
    { timestamp: '02/01', equity: 114200, drawdown: 0.4 },
    { timestamp: '03/01', equity: 135300, drawdown: 1.1 },
    { timestamp: '04/01', equity: 148500, drawdown: 0.8 },
    { timestamp: '05/01', equity: 181200, drawdown: 1.5 },
    { timestamp: '06/01', equity: 177400, drawdown: 4.2 },
    { timestamp: '07/01', equity: 223100, drawdown: 2.0 },
    { timestamp: '08/01', equity: 284500, drawdown: 1.2 },
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
