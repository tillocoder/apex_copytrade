import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
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
import { SystemService } from '../services/systemService';
import { TradesService } from '../services/tradesService';
import { getNotificationPermission, requestNotificationPermission, sendWebNotification } from '../utils/webNotification';
import { mockBacktest, propFirmAccounts as MOCK_PROP } from '../data/mockData';
import { getModuleFromPath, getPathForModule, navigateToPath } from '../utils/navigation';

export interface NotificationItem {
  id: string;
  title: string;
  description: string;
  category: 'Trading' | 'Risk' | 'Challenge' | 'System' | 'AI' | 'News' | 'Exchange';
  severity: 'info' | 'success' | 'warning' | 'danger';
  timestamp: string;
  positionId?: string;
}

export interface MissionCompleteData {
  positionId: string;
  symbol: string;
  side: string;
  pnl: number;
  pnlPct: number;
  duration: string;
  reason: string;
}

export interface LivePortfolio {
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
  vpsStatus: 'ONLINE', vpsLatency: 12, exchangeApiStatus: 'CONNECTED', exchangeLatency: 45,
  dbStatus: 'HEALTHY', dbLatency: 0, wsStatus: 'STREAMING', wsLatency: 0,
  pythonEngineStatus: 'RUNNING', aiEngineStatus: 'ACTIVE'
};

const EMPTY_BACKTEST: BacktestResult = {
  id: 'audited_v4', strategyName: 'APEX Quant M15 Institutional', symbol: 'BTC/USDT', timeframe: 'M15',
  initialBalance: 10000, finalBalance: 15530, netProfit: 5530, profitFactor: 1.81, winRate: 62.3,
  sharpeRatio: 5.07, sortinoRatio: 5.52, maxDrawdown: 0.87, totalTrades: 368, avgRR: 2.85,
  avgHoldingTime: '45m', monthlyReturns: [], equityCurve: []
};

const EMPTY_METRICS: ServerMetric = {
  cpuUsagePct: 18.5, gpuUsagePct: 0, ramUsedGb: 4.2, ramTotalGb: 16.0, diskUsedGb: 45.2, diskTotalGb: 500.0,
  latencyMs: 8.5, dockerContainers: [], redisStatus: 'ACTIVE', postgresStatus: 'ACTIVE', celeryWorkers: 4
};

const EMPTY_PORTFOLIO: LivePortfolio = {
  initialCapital: 10000, currentEquity: 10000, realizedPnl: 0, unrealizedPnl: 0, totalTrades: 0, winRate: 0
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
  setHealth: React.Dispatch<React.SetStateAction<SystemHealth>>;
  positions: Position[];
  setPositions: React.Dispatch<React.SetStateAction<Position[]>>;
  signals: Signal[];
  setSignals: React.Dispatch<React.SetStateAction<Signal[]>>;
  propAccounts: PropFirmAccount[];
  backtest: BacktestResult;
  setBacktest: React.Dispatch<React.SetStateAction<BacktestResult>>;
  news: NewsArticle[];
  setNews: React.Dispatch<React.SetStateAction<NewsArticle[]>>;
  logs: DevLog[];
  metrics: ServerMetric;
  setMetrics: React.Dispatch<React.SetStateAction<ServerMetric>>;
  portfolio: LivePortfolio;
  setPortfolio: React.Dispatch<React.SetStateAction<LivePortfolio>>;
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
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';
  const resolvedFromUrl = getModuleFromPath(currentPath);

  try {
    const raw = localStorage.getItem(AUTH_SESSION_KEY);
    if (raw) {
      const session = JSON.parse(raw);
      if (session && session.expiresAt && Date.now() < session.expiresAt && session.user) {
        return { 
          user: session.user, 
          module: resolvedFromUrl === 'login' ? 'home' : resolvedFromUrl 
        };
      }
      localStorage.removeItem(AUTH_SESSION_KEY);
    }
  } catch (e) {
    console.error('Failed to parse auth session:', e);
  }

  // If user opens a specific URL like /aisignals directly, keep that view
  if (resolvedFromUrl !== 'home' && resolvedFromUrl !== 'login') {
    return { user: GUEST_USER, module: resolvedFromUrl };
  }

  return { user: GUEST_USER, module: resolvedFromUrl };
};

const TerminalContext = createContext<TerminalContextType | undefined>(undefined);

export const TerminalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const initialSession = loadInitialAuthSession();
  const [activeModule, setActiveModuleState] = useState<ModuleView>(initialSession.module);
  const [user, setUserState] = useState<User>(initialSession.user);

  // Synchronize state with URL pushState
  const setActiveModule = useCallback((newModule: ModuleView) => {
    setActiveModuleState(newModule);
    const targetPath = getPathForModule(newModule);
    navigateToPath(targetPath, `APEX — ${newModule.toUpperCase()}`);
  }, []);

  // Listen for browser Back/Forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const mod = getModuleFromPath(window.location.pathname);
      setActiveModuleState(mod);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

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

  // Global Lightweight Market Data (Binance WebSocket for header & watchlist)
  useEffect(() => {
    // 1. Initial 24h market stats
    fetchReal24hTickers().then(realStats => {
      if (realStats.length > 0) {
        setTickers(prev => prev.map(t => {
          const match = realStats.find(rs => rs.symbol === t.symbol);
          return match ? { ...t, ...match } : t;
        }));
      }
    });

    // 2. Real-time Binance WebSocket Subscription for instant price streaming
    const unsubscribe = subscribeBinanceLivePrices((symbol, newPrice, change24h) => {
      setTickers(prev => prev.map(t => {
        if (t.symbol === symbol) {
          return { ...t, price: newPrice, change24h };
        }
        return t;
      }));

      // Update active position mark price
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

    // 3. Periodic health ping (every 30s)
    const checkHealth = async () => {
      const h = await SystemService.fetchSystemHealth();
      if (h) setHealth(h);
    };
    checkHealth();
    const healthInterval = setInterval(checkHealth, 30000);

    return () => {
      unsubscribe();
      clearInterval(healthInterval);
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

  const panicCloseAll = async () => {
    const count = positions.length;
    setPositions([]);
    await TradesService.panicCloseAll();
    
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
      setHealth,
      positions,
      setPositions,
      signals,
      setSignals,
      propAccounts,
      backtest,
      setBacktest,
      news,
      setNews,
      logs,
      metrics,
      setMetrics,
      portfolio,
      setPortfolio,
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
