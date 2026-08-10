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

const ModuleContainer: React.FC = () => {
  const { activeModule, positions = [] } = useTerminal();
  const safePositions = Array.isArray(positions) ? positions : [];

  if (activeModule === 'login') {
    return <AuthLogin />;
  }

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
          {renderModule()}
        </main>
      </div>
      <CommandPalette />
      <NotificationDrawer />
      <TradeReplayModal />
      <MissionCompleteModal />
    </div>
  );
};

export function App() {
  return (
    <TerminalProvider>
      <ModuleContainer />
    </TerminalProvider>
  );
}

export default App;
