import React, { createContext, useContext, useState, useEffect } from 'react';
import type { 
  ModuleView, 
  User, 
  TickerData, 
  SystemHealth, 
  Position, 
  Signal, 
  BacktestResult, 
  PropFirmAccount, 
  NewsArticle, 
  DevLog, 
  ServerMetric 
} from '../types';
import { soundEngine } from '../services/soundEngine';
import { eventBus, type TradingEvent } from '../services/eventEngine';
import { fetchReal24hTickers, subscribeBinanceLivePrices } from '../services/marketDataService';
import { getNotificationPermission, requestNotificationPermission, sendWebNotification } from '../utils/webNotification';
import { mockBacktest, propFirmAccounts as MOCK_PROP } from '../data/mockData';

interface NotificationItem {
  id: string;
  title: string;
  description: string;
  category: 'Trading' | 'Risk' | 'Challenge' | 'System' | 'AI' | 'News' | 'Exchange';
  severity: 'info' | 'success' | 'warning' | 'danger';
  timestamp: string;
  positionId?: string;
}

interface MissionCompleteData {
  positionId: string;
  symbol: string;
  side: string;
  pnl: number;
  pnlPct: number;
  duration: string;
  reason: string;
}

interface LivePortfolio {
  initialCapital: number;
  currentEquity: number;
  realizedPnl: number;
  unrealizedPnl: number;
  totalTrades: number;
  winRate: number;
}

const WATCHLIST: TickerData[] = ['BTC', 'ETH', 'SOL', 'BNB', 'AVAX', 'LINK', 'XRP'].map(symbol => ({
  symbol: `${symbol}/USDT`, price: 0, change24h: 0, high24h: 0, low24h: 0, volume24h: 0, fundingRate: 0, openInterest: 0
}));

const EMPTY_HEALTH: SystemHealth = {
  vpsStatus: 'OFFLINE', vpsLatency: 0, exchangeApiStatus: 'DISCONNECTED', exchangeLatency: 0,
  dbStatus: 'ERROR', dbLatency: 0, wsStatus: 'PAUSED', wsLatency: 0,
  pythonEngineStatus: 'PAUSED', aiEngineStatus: 'CALIBRATING'
};

const EMPTY_BACKTEST: BacktestResult = {
  id: 'pending', strategyName: 'Real-data backtest pending', symbol: '—', timeframe: 'M15',
  initialBalance: 0, finalBalance: 0, netProfit: 0, profitFactor: 0, winRate: 0,
  sharpeRatio: 0, sortinoRatio: 0, maxDrawdown: 0, totalTrades: 0, avgRR: 0,
  avgHoldingTime: '—', monthlyReturns: [], equityCurve: []
};

const EMPTY_METRICS: ServerMetric = {
  cpuUsagePct: 0, gpuUsagePct: 0, ramUsedGb: 0, ramTotalGb: 0, diskUsedGb: 0, diskTotalGb: 0,
  latencyMs: 0, dockerContainers: [], redisStatus: 'DEGRADED', postgresStatus: 'DEGRADED', celeryWorkers: 0
};

const EMPTY_PORTFOLIO: LivePortfolio = {
  initialCapital: 0, currentEquity: 0, realizedPnl: 0, unrealizedPnl: 0, totalTrades: 0, winRate: 0
};

const GUEST_USER: User = {
  id: 'guest', name: 'Guest', email: '', role: 'Guest', avatar: '', twoFactorEnabled: false, passkeyRegistered: false
};

interface TerminalContextType {
  activeModule: ModuleView;
  setActiveModule: (module: ModuleView) => void;
  user: User;
  setUser: (user: User) => void;
  loginUser: (user: User, rememberDays?: number) => void;
  logout: () => void;
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  tickers: TickerData[];
  health: SystemHealth;
  positions: Position[];
  signals: Signal[];
  propAccounts: PropFirmAccount[];
  backtest: BacktestResult;
  news: NewsArticle[];
  logs: DevLog[];
  metrics: ServerMetric;
  portfolio: LivePortfolio;
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  // Notification State
  notificationsOpen: boolean;
  setNotificationsOpen: (open: boolean) => void;
  notifications: NotificationItem[];
  notificationPermission: NotificationPermission;
  requestWebNotifications: () => Promise<NotificationPermission>;
  
  // Command Center State
  commandCenterPositionId: string | null;
  openCommandCenter: (positionId: string) => void;

  // Mission Complete Modal State
  missionModalOpen: boolean;
  setMissionModalOpen: (open: boolean) => void;
  lastMissionData: MissionCompleteData | null;

  // Replay State
  replayModalOpen: boolean;
  setReplayModalOpen: (open: boolean) => void;
  replayPositionId: string | null;
  openReplayModal: (positionId: string) => void;

  // Actions
  closePosition: (id: string) => void;
  panicCloseAll: () => void;
  executePositionAction: (positionId: string, action: string, value?: number) => void;
  addLog: (category: DevLog['category'], level: DevLog['level'], message: string) => void;
}

const AUTH_SESSION_KEY = 'apex_auth_session';

const saveAuthSession = (user: User, days: number = 7) => {
  try {
    const expiresAt = Date.now() + days * 24 * 60 * 60 * 1000;
    localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify({ user, expiresAt }));
  } catch (e) {
    console.error('Failed to save auth session:', e);
  }
};

const clearAuthSession = () => {
  try {
    localStorage.removeItem(AUTH_SESSION_KEY);
  } catch (e) {
    console.error('Failed to clear auth session:', e);
  }
};

const loadInitialAuthSession = (): { user: User; module: ModuleView } => {
  try {
    const raw = localStorage.getItem(AUTH_SESSION_KEY);
    if (raw) {
      const session = JSON.parse(raw);
      if (session && session.expiresAt && Date.now() < session.expiresAt && session.user) {
        return { user: session.user, module: 'home' };
      }
      localStorage.removeItem(AUTH_SESSION_KEY);
    }
  } catch (e) {
    console.error('Failed to parse auth session:', e);
  }
  return { user: GUEST_USER, module: 'login' };
};

const TerminalContext = createContext<TerminalContextType | undefined>(undefined);

export const TerminalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const initialSession = loadInitialAuthSession();
  const [activeModule, setActiveModule] = useState<ModuleView>(initialSession.module);
  const [user, setUserState] = useState<User>(initialSession.user);

  const setUser = (newUser: User) => {
    setUserState(newUser);
    saveAuthSession(newUser, 7);
  };

  const loginUser = (newUser: User, rememberDays: number = 7) => {
    setUserState(newUser);
    if (rememberDays > 0) {
      saveAuthSession(newUser, rememberDays);
    } else {
      clearAuthSession();
    }
    setActiveModule('home');
  };

  const logout = () => {
    clearAuthSession();
    setActiveModule('login');
  };

  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC/USDT');
  const [tickers, setTickers] = useState<TickerData[]>(WATCHLIST);
  const [health, setHealth] = useState<SystemHealth>(EMPTY_HEALTH);
  const [positions, setPositions] = useState<Position[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [propAccounts] = useState<PropFirmAccount[]>(MOCK_PROP);
  const [backtest, setBacktest] = useState<BacktestResult>(mockBacktest);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [logs, setLogs] = useState<DevLog[]>([]);
  const [metrics, setMetrics] = useState<ServerMetric>(EMPTY_METRICS);
  const [portfolio, setPortfolio] = useState<LivePortfolio>(EMPTY_PORTFOLIO);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState<boolean>(false);

  const [notificationsOpen, setNotificationsOpen] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  // Browser Notification Permission
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>(
    () => getNotificationPermission()
  );

  const requestWebNotifications = async (): Promise<NotificationPermission> => {
    const perm = await requestNotificationPermission();
    setNotificationPermission(perm);
    return perm;
  };

  const [commandCenterPositionId, setCommandCenterPositionId] = useState<string | null>(null);

  const [missionModalOpen, setMissionModalOpen] = useState<boolean>(false);
  const [lastMissionData, setLastMissionData] = useState<MissionCompleteData | null>(null);

  const [replayModalOpen, setReplayModalOpen] = useState<boolean>(false);
  const [replayPositionId, setReplayPositionId] = useState<string | null>(null);

  // Real-time Binance Live Market Stream & PnL updates
  useEffect(() => {
    // 1. Initial REST fetch for real 24h market stats & live positions
    fetchReal24hTickers().then(realStats => {
      if (realStats.length > 0) {
        setTickers(prev => prev.map(t => {
          const match = realStats.find(rs => rs.symbol === t.symbol);
          return match ? { ...t, ...match } : t;
        }));
      }
    });

    const fetchLivePositions = async () => {
      try {
        const res = await fetch('/api/v1/positions/live');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            const formatted: Position[] = data.map((p: any) => ({
              id: String(p?.id || ''),
              account: String(p?.account || 'PAPER EXECUTION · REAL MARKET DATA'),
              symbol: String(p?.symbol || ''),
              side: p?.side === 'SELL' ? 'SELL' as const : 'BUY' as const,
              entryPrice: Number(p?.entryPrice) || 0,
              currentPrice: Number(p?.currentPrice) || 0,
              size: Number(p?.size) || 0,
              leverage: Number(p?.leverage) || 0,
              marginUsed: Number(p?.marginUsed) || 0,
              unrealizedPnl: Number(p?.unrealizedPnl) || 0,
              unrealizedPnlPercent: Number(p?.unrealizedPnlPercent) || 0,
              sl: Number(p?.sl) || 0,
              tp1: Number(p?.tp1) || 0,
              tp2: Number(p?.tp2) || 0,
              tp3: Number(p?.tp3) || 0,
              breakEvenPrice: Number(p?.breakEvenPrice) || 0,
              trailingStopActive: Boolean(p?.trailingStopActive),
              trailingDistancePct: Number(p?.trailingDistancePct) || 0,
              atr: Number(p?.atr) || 0,
              riskPercent: Number(p?.riskPercent) || 0,
              rewardPercent: Number(p?.rewardPercent) || 0,
              expectedProfit: Number(p?.expectedProfit) || 0,
              expectedLoss: Number(p?.expectedLoss) || 0,
              commission: Number(p?.commission) || 0,
              fundingFee: Number(p?.fundingFee) || 0,
              swapFees: Number(p?.swapFees) || 0,
              liquidationPrice: Number(p?.liquidationPrice) || 0,
              duration: String(p?.duration || ''),
              timeOpen: String(p?.timeOpen || ''),
              aiExplanation: String(p?.aiExplanation || p?.ai_explanation || ''),
              aiConfidence: Number(p?.aiConfidence ?? p?.ai_confidence) || 0,
              aiRecommendation: p?.aiRecommendation || 'HOLD',
              expectedNextMove: String(p?.expectedNextMove || ''),
              reason: String(p?.reason || ''),
              pattern: String(p?.pattern || ''),
              volumeProfile: String(p?.volumeProfile || ''),
              trendStatus: String(p?.trendStatus || ''),
              orderFlowAnalysis: String(p?.orderFlowAnalysis || ''),
              liquidityAnalysis: String(p?.liquidityAnalysis || ''),
              positionHealthScore: Number(p?.positionHealthScore) || 0,
              executionQualityScore: Number(p?.executionQualityScore) || 0,
              status: p?.status === 'PARTIAL' ? 'PARTIAL' as const : p?.status === 'CLOSED' ? 'CLOSED' as const : 'OPEN' as const,
              timeline: p?.timeline || []
            })).filter(p => p.id && p.symbol);
            setPositions(formatted);
          }
        }
      } catch (err) {
        console.error("Error fetching live positions:", err);
      }
    };
    fetchLivePositions();

    const fetchPortfolio = async () => {
      try {
        const res = await fetch('/api/v1/portfolio/live-equity');
        if (!res.ok) return;
        const json = await res.json();
        if (json.status === 'SUCCESS' && json.data) {
          const data = json.data;
          setPortfolio({
            initialCapital: Number(data.initialCapital) || 0,
            currentEquity: Number(data.currentEquity) || 0,
            realizedPnl: Number(data.realizedPnl) || 0,
            unrealizedPnl: Number(data.unrealizedPnl) || 0,
            totalTrades: Number(data.totalTrades) || 0,
            winRate: Number(data.winRate) || 0
          });
        }
      } catch (err) {
        console.error('Error fetching portfolio state:', err);
      }
    };

    const fetchSystemHealth = async () => {
      const startedAt = performance.now();
      try {
        const res = await fetch('/api/v1/system/health');
        const latency = Math.round(performance.now() - startedAt);
        if (!res.ok) throw new Error(`health request failed (${res.status})`);
        const data = await res.json();
        setHealth({
          vpsStatus: data.status === 'HEALTHY' ? 'ONLINE' : 'DEGRADED',
          vpsLatency: latency,
          exchangeApiStatus: data.exchange_status === 'CONNECTED' ? 'CONNECTED' : 'DISCONNECTED',
          exchangeLatency: Number(data.exchange_latency_ms) || 0,
          dbStatus: data.database_status === 'HEALTHY' ? 'HEALTHY' : 'ERROR',
          dbLatency: Number(data.database_latency_ms) || 0,
          wsStatus: data.websocket_status === 'STREAMING' ? 'STREAMING' : 'PAUSED',
          wsLatency: 0,
          pythonEngineStatus: ['RUNNING', 'OPTIMIZING'].includes(data.python_engine_status) ? 'RUNNING' : 'PAUSED',
          aiEngineStatus: data.ai_engine_status === 'ACTIVE' ? 'ACTIVE' : 'CALIBRATING'
        });
      } catch (err) {
        setHealth(EMPTY_HEALTH);
      }
    };

    const fetchActiveSignals = async () => {
      try {
        const res = await fetch('/api/v1/signals/live');
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data)) setSignals(data as Signal[]);
      } catch (err) {
        console.error('Error fetching active signals:', err);
      }
    };

    const fetchLiveNews = async () => {
      try {
        const res = await fetch('/api/v1/news/feed');
        if (res.ok) {
          const json = await res.json();
          if (Array.isArray(json.data) && json.data.length > 0) {
            setNews(json.data);
          }
        }
      } catch (err) {
        console.error('Error fetching news:', err);
      }
    };

    const fetchLiveMetrics = async () => {
      try {
        const res = await fetch('/api/v1/system/metrics');
        if (res.ok) {
          const json = await res.json();
          if (json && json.cpuUsagePct !== undefined) {
            setMetrics(json);
          }
        }
      } catch (err) {
        console.error('Error fetching metrics:', err);
      }
    };

    fetchPortfolio();
    fetchSystemHealth();
    fetchActiveSignals();
    fetchLiveNews();
    fetchLiveMetrics();

    // 2. Fetch Real Quant Engine Backtest Results from Python Backend
    const fetchQuantEngineResults = async () => {
      try {
        const res = await fetch('/api/v1/quant/backtest-results');
        if (res.ok) {
          const json = await res.json();
          if (json.status === 'SUCCESS' && json.data) {
            setBacktest(prev => ({
              ...prev,
              cagr: json.data.cagr ?? prev.cagr,
              sharpeRatio: json.data.sharpeRatio ?? prev.sharpeRatio,
              sortinoRatio: json.data.sortinoRatio ?? prev.sortinoRatio,
              winRate: json.data.winRate ?? prev.winRate,
              maxDrawdown: json.data.maxDrawdown ?? prev.maxDrawdown,
              profitFactor: json.data.profitFactor ?? prev.profitFactor,
              totalTrades: json.data.totalTrades ?? prev.totalTrades,
              netProfit: json.data.netProfit ?? prev.netProfit,
              initialBalance: json.data.initialBalance ?? prev.initialBalance,
              finalBalance: json.data.finalBalance ?? prev.finalBalance,
              portfolioEquityCurve: json.data.portfolioEquityCurve ?? prev.portfolioEquityCurve,
              passedChallenges: json.data.passedChallenges ?? prev.passedChallenges,
              propSummary: json.data.propSummary ?? prev.propSummary,
              monthlyReturns: (json.data.monthlyReturns && json.data.monthlyReturns.length > 0) 
                ? json.data.monthlyReturns 
                : prev.monthlyReturns,
              equityCurve: (json.data.equityCurve && json.data.equityCurve.length > 0) 
                ? json.data.equityCurve 
                : prev.equityCurve
            }));
          }
        }
      } catch (e) {
        // Backend offline or local fallback
      }
    };
    fetchQuantEngineResults();
    const backtestInterval = setInterval(fetchQuantEngineResults, 10000);
    const liveStateInterval = setInterval(() => {
      fetchLivePositions();
      fetchPortfolio();
      fetchSystemHealth();
      fetchActiveSignals();
      fetchLiveNews();
      fetchLiveMetrics();
    }, 5000);

    // 2. Real-time Binance WebSocket Subscription
    const unsubscribe = subscribeBinanceLivePrices((symbol, newPrice, change24h) => {
      setTickers(prev => prev.map(t => {
        if (t.symbol === symbol) {
          return { ...t, price: newPrice, change24h };
        }
        return t;
      }));

      // Dynamically calculate position unrealized PnL based on REAL price tick
      setPositions(prev => prev.map(p => {
        if (p.symbol === symbol) {
          const diff = p.side === 'BUY' ? (newPrice - p.entryPrice) : (p.entryPrice - newPrice);
          const pnl = Number(((diff / p.entryPrice) * p.marginUsed * p.leverage).toFixed(2));
          const pnlPct = Number(((pnl / p.marginUsed) * 100).toFixed(2));
          return {
            ...p,
            currentPrice: newPrice,
            unrealizedPnl: pnl,
            unrealizedPnlPercent: pnlPct
          };
        }
        return p;
      }));
    });

    return () => {
      unsubscribe();
      clearInterval(backtestInterval);
      clearInterval(liveStateInterval);
    };
  }, []);

  // Subscribe to Event Bus + Web Notifications
  useEffect(() => {
    const unsubscribe = eventBus.subscribe((ev: TradingEvent) => {
      const newNotif: NotificationItem = {
        id: `notif_${Date.now()}`,
        title: ev.title,
        description: ev.description,
        category: ev.category,
        severity: ev.severity,
        timestamp: ev.timestamp,
        positionId: ev.positionId
      };
      setNotifications(prev => [newNotif, ...prev]);

      // Fire browser Web Notification (if permission granted)
      sendWebNotification(`APEX: ${ev.title}`, {
        body: ev.description,
        tag: `apex-${ev.type}-${ev.positionId || ''}`,
      });

      if (ev.type === 'POSITION_OPENED') soundEngine.playPositionOpened();
      else if (ev.type.includes('TP')) soundEngine.playTpHit();
      else if (ev.type === 'SL_HIT') soundEngine.playSlHit();
      else if (ev.type.includes('WARNING')) soundEngine.playWarningAlert();
    });

    return () => unsubscribe();
  }, []);

  const openCommandCenter = (positionId: string) => {
    setCommandCenterPositionId(positionId);
    setActiveModule('command-center');
  };

  const openReplayModal = (positionId: string) => {
    setReplayPositionId(positionId);
    setReplayModalOpen(true);
  };

  const closePosition = (id: string) => {
    const pos = positions.find(p => p.id === id);
    const finalPnl = pos?.unrealizedPnl ?? 0;
    const finalPnlPct = pos?.unrealizedPnlPercent ?? 0;

    if (pos) {
      setLastMissionData({
        positionId: pos.id,
        symbol: pos.symbol,
        side: pos.side,
        pnl: finalPnl,
        pnlPct: finalPnlPct,
        duration: pos.duration,
        reason: 'Closed by APEX Engine Execution Rules'
      });
      setMissionModalOpen(true);
    }

    setPositions(prev => prev.filter(p => p.id !== id));
    
    eventBus.publish({
      id: `ev_${Date.now()}`,
      type: 'POSITION_CLOSED',
      symbol: pos?.symbol,
      positionId: id,
      title: `MISSION CLOSED: ${pos?.symbol}`,
      description: `APEX Engine closed mission. Final PnL: ${finalPnl >= 0 ? '+' : ''}$${finalPnl.toFixed(2)}`,
      timestamp: new Date().toISOString().split('T')[1].slice(0, 8),
      category: 'Trading',
      severity: finalPnl >= 0 ? 'success' : 'danger'
    });

    addLog('Execution', 'WARN', `Mission ${id} closed by APEX Python Engine.`);
  };

  const panicCloseAll = () => {
    const count = positions.length;
    setPositions([]);
    
    eventBus.publish({
      id: `ev_${Date.now()}`,
      type: 'POSITION_CLOSED',
      title: 'PANIC CLOSE ALL EXECUTED',
      description: `Liquidated all ${count} active missions across portfolio.`,
      timestamp: new Date().toISOString().split('T')[1].slice(0, 8),
      category: 'Risk',
      severity: 'danger'
    });

    addLog('Execution', 'ERROR', `PANIC CLOSE ALL EXECUTED. ${count} active positions liquidated.`);
  };

  const executePositionAction = (positionId: string, action: string, value?: number) => {
    setPositions(prev => prev.map(p => {
      if (p.id !== positionId) return p;

      const newTimeline = [...p.timeline];
      const nowTime = new Date().toISOString().split('T')[1].slice(0, 8);

      if (action === 'breakEven') {
        soundEngine.playTpHit();
        newTimeline.push({
          id: `ev_${Date.now()}`,
          timestamp: nowTime,
          title: 'Break Even Activated',
          reason: `Stop loss moved to entry price ($${p.entryPrice})`,
          triggeredBy: 'APEX M5 Engine',
          riskImpact: '0.00% Risk',
          challengeImpact: 'Capital Protected',
          severity: 'success'
        });
        return { ...p, sl: p.entryPrice, breakEvenPrice: p.entryPrice, timeline: newTimeline };
      }

      if (action === 'trailing') {
        const nextTrailing = !p.trailingStopActive;
        soundEngine.playWarningAlert();
        newTimeline.push({
          id: `ev_${Date.now()}`,
          timestamp: nowTime,
          title: nextTrailing ? 'Trailing Stop Enabled' : 'Trailing Stop Disabled',
          reason: nextTrailing ? 'Dynamic 1.0% trailing distance active' : 'Trailing stopped',
          triggeredBy: 'APEX M5 Engine',
          riskImpact: 'Dynamic Lock',
          challengeImpact: 'Risk Protected',
          severity: 'info'
        });
        return { ...p, trailingStopActive: nextTrailing, timeline: newTimeline };
      }

      if (action === 'partial' && value) {
        soundEngine.playTpHit();
        const closePct = value / 100;
        const remainingSize = Number((p.size * (1 - closePct)).toFixed(2));
        newTimeline.push({
          id: `ev_${Date.now()}`,
          timestamp: nowTime,
          title: `Partial ${value}% Close`,
          reason: `Secured PnL on ${value}% of position. Remaining size: ${remainingSize}`,
          triggeredBy: 'APEX M5 Engine',
          riskImpact: 'Reduced Exposure',
          challengeImpact: '+PnL Locked',
          severity: 'success'
        });
        return { ...p, size: remainingSize, timeline: newTimeline };
      }

      if (action === 'close') {
        closePosition(positionId);
      }

      return p;
    }));
  };

  const addLog = (category: DevLog['category'], level: DevLog['level'], message: string) => {
    const newLog: DevLog = {
      id: `log_${Date.now()}`,
      timestamp: new Date().toISOString().split('T')[1].slice(0, 12),
      category,
      level,
      message
    };
    setLogs(prev => [newLog, ...prev.slice(0, 49)]);
  };

  return (
    <TerminalContext.Provider value={{
      activeModule,
      setActiveModule,
      user,
      setUser,
      loginUser,
      logout,
      selectedSymbol,
      setSelectedSymbol,
      tickers,
      health,
      positions,
      signals,
      propAccounts,
      backtest,
      news,
      logs,
      metrics,
      portfolio,
      commandPaletteOpen,
      setCommandPaletteOpen,
      notificationsOpen,
      setNotificationsOpen,
      notifications,
      notificationPermission,
      requestWebNotifications,
      commandCenterPositionId,
      openCommandCenter,
      missionModalOpen,
      setMissionModalOpen,
      lastMissionData,
      replayModalOpen,
      setReplayModalOpen,
      replayPositionId,
      openReplayModal,
      closePosition,
      panicCloseAll,
      executePositionAction,
      addLog
    }}>
      {children}
    </TerminalContext.Provider>
  );
};

export const useTerminal = () => {
  const context = useContext(TerminalContext);
  if (!context) throw new Error('useTerminal must be used within a TerminalProvider');
  return context;
};
