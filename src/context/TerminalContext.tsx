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
import { 
  currentUser, 
  initialTickers, 
  systemHealthStatus, 
  initialPositions, 
  initialSignals, 
  propFirmAccounts, 
  mockBacktest, 
  newsArticles, 
  initialLogs, 
  serverMetrics 
} from '../data/mockData';
import { soundEngine } from '../services/soundEngine';
import { eventBus, type TradingEvent } from '../services/eventEngine';
import { fetchReal24hTickers, subscribeBinanceLivePrices } from '../services/marketDataService';
import { getNotificationPermission, requestNotificationPermission, sendWebNotification } from '../utils/webNotification';

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
  return { user: currentUser, module: 'login' };
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
  const [tickers, setTickers] = useState<TickerData[]>(initialTickers);
  const [health] = useState<SystemHealth>(systemHealthStatus);
  const [positions, setPositions] = useState<Position[]>(initialPositions);
  const [signals] = useState<Signal[]>(initialSignals);
  const [propAccounts] = useState<PropFirmAccount[]>(propFirmAccounts);
  const [backtest, setBacktest] = useState<BacktestResult>(mockBacktest);
  const [news] = useState<NewsArticle[]>(newsArticles);
  const [logs, setLogs] = useState<DevLog[]>(initialLogs);
  const [metrics] = useState<ServerMetric>(serverMetrics);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState<boolean>(false);

  const [notificationsOpen, setNotificationsOpen] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([
    { id: 'n1', title: 'MISSION OPENED: BTC/USDT BUY 20X', description: 'Entry $89,200.00. 1.25% Planned Risk. Zero prop firm rule violation.', category: 'Trading', severity: 'success', timestamp: '02:41:08', positionId: 'pos_001' },
    { id: 'n2', title: 'TP1 TARGET HIT: BTC/USDT', description: 'Locked +$3,250 profit (+1.46R). Stop loss automatically updated to Entry.', category: 'Trading', severity: 'success', timestamp: '07:10:00', positionId: 'pos_001' },
    { id: 'n3', title: 'PROP FIRM DRAWDOWN SAFEGUARD', description: 'Current daily drawdown at 0.85% / 5.0% limit. Safe risk remaining: $4,150.', category: 'Risk', severity: 'info', timestamp: '09:00:00' },
  ]);

  // Browser Notification Permission
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>(
    () => getNotificationPermission()
  );

  const requestWebNotifications = async (): Promise<NotificationPermission> => {
    const perm = await requestNotificationPermission();
    setNotificationPermission(perm);
    return perm;
  };

  const [commandCenterPositionId, setCommandCenterPositionId] = useState<string | null>('pos_001');

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
              id: p?.id || `pos_${Math.random()}`,
              account: p?.account || 'FTMO 10K LIVE EVALUATION',
              symbol: p?.symbol || 'BTC/USDT',
              side: p?.side === 'SELL' ? 'SELL' : 'BUY',
              entryPrice: p?.entryPrice || 0,
              currentPrice: p?.currentPrice || p?.entryPrice || 0,
              size: p?.size || 0.1,
              leverage: p?.leverage || 5,
              marginUsed: p?.marginUsed || 100,
              unrealizedPnl: p?.unrealizedPnl || 0,
              unrealizedPnlPercent: p?.unrealizedPnlPercent || 0,
              sl: p?.sl || 0,
              tp1: p?.tp1 || 0,
              tp2: p?.tp2 || 0,
              tp3: p?.tp3 || 0,
              breakEvenPrice: p?.breakEvenPrice || p?.entryPrice || 0,
              trailingStopActive: false,
              trailingDistancePct: 0.5,
              atr: p?.atr || 35.0,
              riskPercent: p?.riskPercent || 1.5,
              rewardPercent: p?.rewardPercent || 3.0,
              expectedProfit: p?.expectedProfit || 150,
              expectedLoss: p?.expectedLoss || 150,
              commission: p?.commission || 4.5,
              fundingFee: 0,
              swapFees: 0,
              liquidationPrice: p?.liquidationPrice || 0,
              duration: p?.duration || '0h 15m',
              timeOpen: p?.timeOpen || 'Just Now',
              aiExplanation: p?.aiExplanation || p?.ai_explanation || 'M15 OrderFlow Confluence',
              aiConfidence: p?.aiConfidence || p?.ai_confidence || 85,
              aiRecommendation: 'HOLD',
              expectedNextMove: p?.expectedNextMove || 'Bullish Continuation',
              reason: p?.reason || 'M15 SMC Confluence',
              pattern: p?.pattern || 'Bullish FVG + Order Block',
              volumeProfile: p?.volumeProfile || 'High Volume Node Support',
              trendStatus: p?.trendStatus || 'Strong Bullish Alignment',
              orderFlowAnalysis: p?.orderFlowAnalysis || 'Net Buying Pressure',
              liquidityAnalysis: p?.liquidityAnalysis || 'Buy-side Liquidity Target',
              positionHealthScore: p?.positionHealthScore || 92,
              executionQualityScore: p?.executionQualityScore || 95,
              status: p?.status === 'CLOSED' ? 'CLOSED' : 'OPEN',
              timeline: p?.timeline || []
            }));
            setPositions(formatted);
          }
        }
      } catch (err) {
        console.error("Error fetching live positions:", err);
      }
    };
    fetchLivePositions();

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
    const interval = setInterval(fetchQuantEngineResults, 10000);

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
      clearInterval(interval);
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
