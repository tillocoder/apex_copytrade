import type { ModuleView } from '../types';

export interface RouteMapping {
  moduleId: ModuleView;
  path: string;
  aliases: string[];
}

export const APP_ROUTES: RouteMapping[] = [
  { moduleId: 'login', path: '/login', aliases: ['/auth', '/signin'] },
  { moduleId: 'trades', path: '/livetrades', aliases: ['/', '/home', '/trades', '/live-trades', '/missioncontrol', '/mission-control'] },
  { moduleId: 'command-center', path: '/commandcenter', aliases: ['/command-center', '/command'] },
  { moduleId: 'signals', path: '/aisignals', aliases: ['/signals', '/ai-signals'] },
  { moduleId: 'binance-futures', path: '/binance-futures', aliases: ['/eth-scalper', '/futures', '/binance'] },
  { moduleId: 'backtest', path: '/backtestlab', aliases: ['/backtest', '/backtest-lab', '/lab'] },
  { moduleId: 'analytics', path: '/analytics', aliases: ['/stats', '/performance', '/propfirmcenter', '/prop-firm', '/prop', '/portfolio', '/portfolio-risk'] },
  { moduleId: 'intelligence', path: '/intelligence', aliases: ['/marketintelligence', '/market-intelligence'] },
  { moduleId: 'news', path: '/ainewsfeed', aliases: ['/news', '/newsfeed', '/ai-news'] },
  { moduleId: 'journal', path: '/tradejournal', aliases: ['/journal', '/trade-journal'] },
  { moduleId: 'copilot', path: '/xraichat', aliases: ['/copilot', '/ai-chat', '/aichat'] },
  { moduleId: 'team', path: '/teamhub', aliases: ['/team', '/team-hub'] },
  { moduleId: 'automation', path: '/automation', aliases: ['/auto', '/bot-automation', '/server', '/servercenter', '/server-center', '/cluster'] },
  { moduleId: 'admin', path: '/admin', aliases: ['/adminapi', '/admin-api'] },
  { moduleId: 'settings', path: '/settings', aliases: ['/config', '/preferences'] },
];

/**
 * Resolves current pathname to a valid ModuleView
 */
export function getModuleFromPath(pathname: string): ModuleView {
  const cleanPath = (pathname || '/').toLowerCase().replace(/\/$/, '') || '/';

  for (const route of APP_ROUTES) {
    if (route.path === cleanPath || route.aliases.includes(cleanPath)) {
      return route.moduleId;
    }
  }

  // Support direct sub-routes e.g. /aisignals/BTC
  for (const route of APP_ROUTES) {
    if (route.path !== '/' && cleanPath.startsWith(route.path)) {
      return route.moduleId;
    }
  }

  return 'trades';
}

/**
 * Returns canonical URL path for a given module ID
 */
export function getPathForModule(moduleId: ModuleView): string {
  const route = APP_ROUTES.find(r => r.moduleId === moduleId);
  return route ? route.path : '/livetrades';
}

/**
 * Updates browser URL cleanly using HTML5 History API without reloading page
 */
export function navigateToPath(path: string, title?: string): void {
  if (typeof window === 'undefined') return;
  if (window.location.pathname !== path) {
    window.history.pushState({ path }, title || 'APEX QUANT TERMINAL', path);
  }
}
