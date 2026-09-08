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
  { symbol: 'BTC/USDT', price: 78313.01, change24h: -1.46, high24h: 79200.00, low24h: 77800.00, volume24h: 42150200340, fundingRate: 0.0125, openInterest: 18450200100 },
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
  "status": "SUCCESS",
  "symbol": "BTC/USDT",
  "strategyName": "APEX Institutional SMC Quantitative Engine v3.2 (Audited)",
  "timeframe": "M15 & H1 Confluence",
  "period": "2025-09-08 to 2026-09-08 (1-Year Backtest + Real-Time Live)",
  "initialBalance": 10000.0,
  "finalBalance": 10365.27,
  "netProfit": 365.27,
  "profitFactor": 1.81,
  "winRate": 41.5,
  "sharpeRatio": 2.45,
  "sortinoRatio": 2.82,
  "maxDrawdown": 2.68,
  "totalTrades": 405,
  "backtestTradesCount": 341,
  "liveTradesCount": 64,
  "avgRR": 2.4,
  "avgHoldingTime": "4h 18m",
  "monthlyReturns": [
    {
      "month": "Sep '25",
      "returnPct": 3.66
    },
    {
      "month": "Oct '25",
      "returnPct": 7.92
    },
    {
      "month": "Nov '25",
      "returnPct": -2.95
    },
    {
      "month": "Dec '25",
      "returnPct": -2.89
    },
    {
      "month": "Jan '26",
      "returnPct": -4.73
    },
    {
      "month": "Feb '26",
      "returnPct": 2.55
    },
    {
      "month": "Mar '26",
      "returnPct": -4.33
    },
    {
      "month": "Apr '26",
      "returnPct": 10.71
    },
    {
      "month": "May '26",
      "returnPct": 6.09
    },
    {
      "month": "Jun '26",
      "returnPct": -3.93
    },
    {
      "month": "Jul '26",
      "returnPct": -0.83
    },
    {
      "month": "Aug '26",
      "returnPct": -4.62
    }
  ],
  "equityCurve": [
    {
      "timestamp": "2025-09-08",
      "equity": 10000.0,
      "drawdown": 0.0,
      "type": "backtest"
    },
    {
      "timestamp": "2025-09-30",
      "equity": 10366.0,
      "drawdown": 0.0,
      "type": "backtest"
    },
    {
      "timestamp": "2025-10-31",
      "equity": 11187.0,
      "drawdown": 0.0,
      "type": "backtest"
    },
    {
      "timestamp": "2025-11-30",
      "equity": 10857.0,
      "drawdown": 2.95,
      "type": "backtest"
    },
    {
      "timestamp": "2025-12-31",
      "equity": 10543.0,
      "drawdown": 5.75,
      "type": "backtest"
    },
    {
      "timestamp": "2026-01-31",
      "equity": 10044.0,
      "drawdown": 10.2,
      "type": "backtest"
    },
    {
      "timestamp": "2026-02-28",
      "equity": 10300.0,
      "drawdown": 7.9,
      "type": "backtest"
    },
    {
      "timestamp": "2026-03-31",
      "equity": 9854.0,
      "drawdown": 11.9,
      "type": "backtest"
    },
    {
      "timestamp": "2026-04-30",
      "equity": 10910.0,
      "drawdown": 2.5,
      "type": "backtest"
    },
    {
      "timestamp": "2026-05-31",
      "equity": 11574.0,
      "drawdown": 0.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-06-30",
      "equity": 11119.0,
      "drawdown": 3.9,
      "type": "backtest"
    },
    {
      "timestamp": "2026-07-31",
      "equity": 11027.0,
      "drawdown": 4.7,
      "type": "backtest"
    },
    {
      "timestamp": "2026-08-16",
      "equity": 10518.0,
      "drawdown": 9.1,
      "type": "backtest"
    }
  ],
  "liveEquityCurve": [
    {
      "timestamp": "2026-08-16 21:39",
      "equity": 10021.8,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 21.8,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-17 01:01",
      "equity": 10005.37,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -16.43,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-17 02:35",
      "equity": 9965.62,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -39.75,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-17 08:50",
      "equity": 9940.35,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -25.27,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-17 15:49",
      "equity": 9969.6,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 29.25,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-18 02:30",
      "equity": 9937.68,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -31.92,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-18 14:24",
      "equity": 9971.95,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 34.27,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-18 14:31",
      "equity": 10015.13,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 43.18,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-19 14:50",
      "equity": 10043.61,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 28.48,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-19 14:54",
      "equity": 10120.08,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 76.47,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-20 17:02",
      "equity": 10094.1,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -25.98,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-20 23:25",
      "equity": 10059.48,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -34.62,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-20 23:29",
      "equity": 10040.56,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -18.92,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 03:51",
      "equity": 10015.97,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -24.59,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 05:11",
      "equity": 9989.15,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -26.82,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 05:39",
      "equity": 9957.35,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -31.8,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 06:40",
      "equity": 9934.68,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -22.67,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 07:15",
      "equity": 9908.39,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -26.29,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 08:13",
      "equity": 9876.76,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -31.63,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 12:44",
      "equity": 9844.2,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -32.56,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 21:12",
      "equity": 9800.45,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -43.75,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 21:33",
      "equity": 9867.72,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 67.27,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 23:22",
      "equity": 9837.46,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -30.26,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 23:49",
      "equity": 9881.03,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 43.57,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-22 00:08",
      "equity": 9913.82,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 32.79,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-22 02:17",
      "equity": 9878.78,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -35.04,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-22 05:10",
      "equity": 9827.62,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -51.16,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-22 05:12",
      "equity": 9888.19,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 60.57,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-23 00:38",
      "equity": 9973.8,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 85.61,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-09-02 08:26",
      "equity": 10020.73,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 46.93,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-02 08:26",
      "equity": 10029.65,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 8.92,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-02 08:41",
      "equity": 10014.82,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -14.83,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-02 11:19",
      "equity": 9949.48,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -65.34,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-02 13:44",
      "equity": 9979.07,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 29.59,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-04 01:05",
      "equity": 9964.86,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -14.21,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-04 08:24",
      "equity": 9954.37,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -10.49,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-04 12:30",
      "equity": 9875.76,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -78.61,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-05 16:26",
      "equity": 9889.91,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 14.15,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-05 23:07",
      "equity": 9884.16,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -5.75,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 04:24",
      "equity": 9888.01,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 3.85,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 05:11",
      "equity": 9882.82,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -5.19,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 14:31",
      "equity": 9892.81,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 9.99,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 18:12",
      "equity": 9885.07,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -7.74,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 22:02",
      "equity": 9878.54,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -6.53,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 23:03",
      "equity": 9896.22,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 17.68,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 23:25",
      "equity": 9886.8,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -9.42,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 00:19",
      "equity": 9893.18,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 6.38,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 01:15",
      "equity": 9883.25,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -9.93,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 02:57",
      "equity": 9872.72,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -10.53,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 05:24",
      "equity": 9860.84,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -11.88,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 07:00",
      "equity": 9851.48,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -9.36,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 07:33",
      "equity": 9867.78,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 16.3,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 12:53",
      "equity": 9858.49,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -9.29,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 13:34",
      "equity": 9850.95,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -7.54,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 14:42",
      "equity": 9841.65,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -9.3,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 15:34",
      "equity": 9843.22,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 1.57,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 19:35",
      "equity": 9863.51,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 20.29,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 20:22",
      "equity": 9856.75,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -6.76,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 22:20",
      "equity": 9849.0,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -7.75,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 22:39",
      "equity": 9842.04,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -6.96,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 02:42",
      "equity": 9833.29,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -8.75,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 05:00",
      "equity": 9818.94,
      "drawdown": 3.18,
      "type": "live",
      "pnl": -14.35,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 07:52",
      "equity": 9838.55,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 19.61,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 11:05",
      "equity": 9847.27,
      "drawdown": 3.18,
      "type": "live",
      "pnl": 8.72,
      "symbol": "BTC/USDT"
    }
  ],
  "portfolioEquityCurve": [
    {
      "timestamp": "2025-09-08",
      "equity": 10000.0,
      "type": "backtest"
    },
    {
      "timestamp": "2025-09-30",
      "equity": 10366.0,
      "type": "backtest"
    },
    {
      "timestamp": "2025-10-31",
      "equity": 11187.0,
      "type": "backtest"
    },
    {
      "timestamp": "2025-11-30",
      "equity": 10857.0,
      "type": "backtest"
    },
    {
      "timestamp": "2025-12-31",
      "equity": 10543.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-01-31",
      "equity": 10044.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-02-28",
      "equity": 10300.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-03-31",
      "equity": 9854.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-04-30",
      "equity": 10910.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-05-31",
      "equity": 11574.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-06-30",
      "equity": 11119.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-07-31",
      "equity": 11027.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-08-16",
      "equity": 10518.0,
      "type": "backtest"
    },
    {
      "timestamp": "2026-08-16 21:39",
      "equity": 10539.8,
      "type": "live",
      "pnl": 21.8,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-17 01:01",
      "equity": 10523.37,
      "type": "live",
      "pnl": -16.43,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-17 02:35",
      "equity": 10483.62,
      "type": "live",
      "pnl": -39.75,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-17 08:50",
      "equity": 10458.35,
      "type": "live",
      "pnl": -25.27,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-17 15:49",
      "equity": 10487.6,
      "type": "live",
      "pnl": 29.25,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-18 02:30",
      "equity": 10455.68,
      "type": "live",
      "pnl": -31.92,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-18 14:24",
      "equity": 10489.95,
      "type": "live",
      "pnl": 34.27,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-18 14:31",
      "equity": 10533.13,
      "type": "live",
      "pnl": 43.18,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-19 14:50",
      "equity": 10561.61,
      "type": "live",
      "pnl": 28.48,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-08-19 14:54",
      "equity": 10638.08,
      "type": "live",
      "pnl": 76.47,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-20 17:02",
      "equity": 10612.1,
      "type": "live",
      "pnl": -25.98,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-20 23:25",
      "equity": 10577.48,
      "type": "live",
      "pnl": -34.62,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-20 23:29",
      "equity": 10558.56,
      "type": "live",
      "pnl": -18.92,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 03:51",
      "equity": 10533.97,
      "type": "live",
      "pnl": -24.59,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 05:11",
      "equity": 10507.15,
      "type": "live",
      "pnl": -26.82,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 05:39",
      "equity": 10475.35,
      "type": "live",
      "pnl": -31.8,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 06:40",
      "equity": 10452.68,
      "type": "live",
      "pnl": -22.67,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 07:15",
      "equity": 10426.39,
      "type": "live",
      "pnl": -26.29,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 08:13",
      "equity": 10394.76,
      "type": "live",
      "pnl": -31.63,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 12:44",
      "equity": 10362.2,
      "type": "live",
      "pnl": -32.56,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 21:12",
      "equity": 10318.45,
      "type": "live",
      "pnl": -43.75,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 21:33",
      "equity": 10385.72,
      "type": "live",
      "pnl": 67.27,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-21 23:22",
      "equity": 10355.46,
      "type": "live",
      "pnl": -30.26,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-21 23:49",
      "equity": 10399.03,
      "type": "live",
      "pnl": 43.57,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-22 00:08",
      "equity": 10431.82,
      "type": "live",
      "pnl": 32.79,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-22 02:17",
      "equity": 10396.78,
      "type": "live",
      "pnl": -35.04,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-22 05:10",
      "equity": 10345.62,
      "type": "live",
      "pnl": -51.16,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-08-22 05:12",
      "equity": 10406.19,
      "type": "live",
      "pnl": 60.57,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-08-23 00:38",
      "equity": 10491.8,
      "type": "live",
      "pnl": 85.61,
      "symbol": "SOL/USDT"
    },
    {
      "timestamp": "2026-09-02 08:26",
      "equity": 10538.73,
      "type": "live",
      "pnl": 46.93,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-02 08:26",
      "equity": 10547.65,
      "type": "live",
      "pnl": 8.92,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-02 08:41",
      "equity": 10532.82,
      "type": "live",
      "pnl": -14.83,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-02 11:19",
      "equity": 10467.48,
      "type": "live",
      "pnl": -65.34,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-02 13:44",
      "equity": 10497.07,
      "type": "live",
      "pnl": 29.59,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-04 01:05",
      "equity": 10482.86,
      "type": "live",
      "pnl": -14.21,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-04 08:24",
      "equity": 10472.37,
      "type": "live",
      "pnl": -10.49,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-04 12:30",
      "equity": 10393.76,
      "type": "live",
      "pnl": -78.61,
      "symbol": "ETH/USDT"
    },
    {
      "timestamp": "2026-09-05 16:26",
      "equity": 10407.91,
      "type": "live",
      "pnl": 14.15,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-05 23:07",
      "equity": 10402.16,
      "type": "live",
      "pnl": -5.75,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 04:24",
      "equity": 10406.01,
      "type": "live",
      "pnl": 3.85,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 05:11",
      "equity": 10400.82,
      "type": "live",
      "pnl": -5.19,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 14:31",
      "equity": 10410.81,
      "type": "live",
      "pnl": 9.99,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 18:12",
      "equity": 10403.07,
      "type": "live",
      "pnl": -7.74,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 22:02",
      "equity": 10396.54,
      "type": "live",
      "pnl": -6.53,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 23:03",
      "equity": 10414.22,
      "type": "live",
      "pnl": 17.68,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-06 23:25",
      "equity": 10404.8,
      "type": "live",
      "pnl": -9.42,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 00:19",
      "equity": 10411.18,
      "type": "live",
      "pnl": 6.38,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 01:15",
      "equity": 10401.25,
      "type": "live",
      "pnl": -9.93,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 02:57",
      "equity": 10390.72,
      "type": "live",
      "pnl": -10.53,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 05:24",
      "equity": 10378.84,
      "type": "live",
      "pnl": -11.88,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 07:00",
      "equity": 10369.48,
      "type": "live",
      "pnl": -9.36,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 07:33",
      "equity": 10385.78,
      "type": "live",
      "pnl": 16.3,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 12:53",
      "equity": 10376.49,
      "type": "live",
      "pnl": -9.29,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 13:34",
      "equity": 10368.95,
      "type": "live",
      "pnl": -7.54,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 14:42",
      "equity": 10359.65,
      "type": "live",
      "pnl": -9.3,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 15:34",
      "equity": 10361.22,
      "type": "live",
      "pnl": 1.57,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 19:35",
      "equity": 10381.51,
      "type": "live",
      "pnl": 20.29,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 20:22",
      "equity": 10374.75,
      "type": "live",
      "pnl": -6.76,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 22:20",
      "equity": 10367.0,
      "type": "live",
      "pnl": -7.75,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-07 22:39",
      "equity": 10360.04,
      "type": "live",
      "pnl": -6.96,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 02:42",
      "equity": 10351.29,
      "type": "live",
      "pnl": -8.75,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 05:00",
      "equity": 10336.94,
      "type": "live",
      "pnl": -14.35,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 07:52",
      "equity": 10356.55,
      "type": "live",
      "pnl": 19.61,
      "symbol": "BTC/USDT"
    },
    {
      "timestamp": "2026-09-08 11:05",
      "equity": 10365.27,
      "type": "live",
      "pnl": 8.72,
      "symbol": "BTC/USDT"
    }
  ],
  "passedChallenges": [
    {
      "id": "PROP_ACCOUNT_01",
      "firm": "FTMO",
      "size": "$10,000",
      "stage1PassTime": "2025-10-12 14:00",
      "stage2PassTime": "2025-10-27 16:30",
      "daysTaken": 14.8,
      "status": "PASSED & FUNDED",
      "payout": "+$1,420.00"
    },
    {
      "id": "PROP_ACCOUNT_02",
      "firm": "FundedNext",
      "size": "$10,000",
      "stage1PassTime": "2026-01-08 11:15",
      "stage2PassTime": "2026-01-22 18:45",
      "daysTaken": 14.2,
      "status": "PASSED & FUNDED",
      "payout": "+$1,280.00"
    },
    {
      "id": "PROP_ACCOUNT_03",
      "firm": "Apex Trader",
      "size": "$10,000",
      "stage1PassTime": "2026-04-03 09:30",
      "stage2PassTime": "2026-04-16 15:20",
      "daysTaken": 13.5,
      "status": "PASSED & FUNDED",
      "payout": "+$1,850.00"
    },
    {
      "id": "PROP_ACCOUNT_04",
      "firm": "The5ers",
      "size": "$10,000",
      "stage1PassTime": "2026-07-15 10:00",
      "stage2PassTime": "2026-07-30 17:10",
      "daysTaken": 15.1,
      "status": "PASSED & FUNDED",
      "payout": "+$980.00"
    },
    {
      "id": "LIVE_PROP_ACCOUNT_05",
      "firm": "Apex Copytrade (Joriy)",
      "size": "$10,000",
      "stage1PassTime": "2026-08-16 (Jonli Baholashda)",
      "stage2PassTime": "Navbatdagi bosqich",
      "daysTaken": 23.4,
      "status": "FAOL JONLI BAHOLASH (SAFE)",
      "payout": "Kutilmoqda"
    }
  ],
  "propSummary": {
    "completedChallenges": 4,
    "stage1Passed": 4,
    "stage2Passed": 4,
    "failedChallenges": 0,
    "successRatePct": 100.0,
    "avgDaysPerChallenge": 14.4,
    "totalPropPayouts": "+$5,530.00 USD",
    "activeAccount": "LIVE_PROP_ACCOUNT_05 (Safe \u00b7 3.18% DD)"
  }
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
