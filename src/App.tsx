import React from 'react';
import { TerminalProvider, useTerminal } from './context/TerminalContext';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { CommandPalette } from './components/common/CommandPalette';
import { NotificationDrawer } from './components/common/NotificationDrawer';
import { TradeReplayModal } from './components/common/TradeReplayModal';
import { MissionCompleteModal } from './components/common/MissionCompleteModal';

import { AuthLogin } from './components/modules/AuthLogin';
import { MissionControlHome } from './components/modules/MissionControlHome';
import { LiveTrades } from './components/modules/LiveTrades';
import { PositionCommandCenter } from './components/modules/PositionCommandCenter';
import { LiveSignals } from './components/modules/LiveSignals';
import { BacktestLab } from './components/modules/BacktestLab';
import { PropFirmCenter } from './components/modules/PropFirmCenter';
import { MarketIntelligence } from './components/modules/MarketIntelligence';
import { AICopilot } from './components/modules/AICopilot';
import { TeamHub } from './components/modules/TeamHub';
import { AutomationCenter } from './components/modules/AutomationCenter';
import { ServerCenter } from './components/modules/ServerCenter';
import { SettingsModule } from './components/modules/SettingsModule';
import { StandaloneAdminDashboard } from './components/admin/StandaloneAdminDashboard';

import { TradingWorkspace } from './components/workspaces/TradingWorkspace';
import { RiskWorkspace } from './components/workspaces/RiskWorkspace';
import { JournalWorkspace } from './components/workspaces/JournalWorkspace';
import { AnalyticsWorkspace } from './components/workspaces/AnalyticsWorkspace';
import { NewsWorkspace } from './components/workspaces/NewsWorkspace';

class GlobalModuleErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: any }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("Global Module Error Boundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-apex-bg text-apex-text space-y-4 font-mono text-xs">
          <div className="p-6 bg-apex-danger/10 border border-apex-danger/40 rounded-lg text-center max-w-lg space-y-3 shadow-2xl">
            <h3 className="text-sm font-bold text-apex-danger">MODULE RENDERING RECOVERED</h3>
            <p className="text-xs text-apex-muted">An unexpected formatting anomaly occurred in this module view:</p>
            <pre className="p-2.5 bg-black/70 text-apex-danger rounded text-[10px] text-left overflow-x-auto border border-apex-danger/20 font-mono">
              {String(this.state.error?.message || this.state.error)}
            </pre>
            <button 
              onClick={() => { this.setState({ hasError: false, error: null }); }} 
              className="px-4 py-2 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border text-apex-text font-bold rounded text-xs transition-colors"
            >
              Reset Module View
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const ModuleContainer: React.FC = () => {
  const { activeModule, positions = [] } = useTerminal();
  const safePositions = Array.isArray(positions) ? positions : [];

  // Standalone Admin Dashboard UI/UX for apex-api.xrinvest.uz or apex.api.xrinvest.uz
  if (window.location.hostname.includes('api') || activeModule === 'admin') {
    return <StandaloneAdminDashboard />;
  }

  const renderModule = () => {
    switch (activeModule) {
      case 'home': 
        return safePositions.length > 0 ? <MissionControlHome /> : <TradingWorkspace />;
      case 'trades': return <LiveTrades />;
      case 'command-center': return <PositionCommandCenter />;
      case 'signals': return <LiveSignals />;
      case 'backtest': return <BacktestLab />;
      case 'prop-firm': return <RiskWorkspace />;
      case 'intelligence': return <MarketIntelligence />;
      case 'news': return <NewsWorkspace />;
      case 'portfolio': return <RiskWorkspace />;
      case 'journal': return <JournalWorkspace />;
      case 'analytics': return <AnalyticsWorkspace />;
      case 'copilot': return <AICopilot />;
      case 'team': return <TeamHub />;
      case 'automation': return <AutomationCenter />;
      case 'server': return <ServerCenter />;
      case 'settings': return <SettingsModule />;
      default: return <MissionControlHome />;
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-apex-bg text-apex-text overflow-hidden select-none">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex overflow-hidden">
          <GlobalModuleErrorBoundary>
            {renderModule()}
          </GlobalModuleErrorBoundary>
        </main>
      </div>
      <CommandPalette />
      <NotificationDrawer />
      <TradeReplayModal />
      <MissionCompleteModal />
    </div>
  );
};

const RootSecurityGate: React.FC = () => {
  const { user, activeModule } = useTerminal();

  // STRICT AUTH GATEWAY: Unauthenticated or Guest visitors MUST see AuthLogin standalone page
  if (!user || user.role === 'Guest' || !user.email || activeModule === 'login') {
    return <AuthLogin />;
  }

  return <ModuleContainer />;
};

export function App() {
  return (
    <TerminalProvider>
      <RootSecurityGate />
    </TerminalProvider>
  );
}

export default App;