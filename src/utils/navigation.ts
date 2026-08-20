import type { ModuleView } from '../types';

export interface RouteMapping {
  moduleId: ModuleView;
  path: string;
  aliases: string[];
}

export const APP_ROUTES: RouteMapping[] = [
  { moduleId: 'login', path: '/login', aliases: ['/auth', '/signin'] },
  { moduleId: 'home', path: '/missioncontrol', aliases: ['/', '/home', '/mission-control'] },
  { moduleId: 'trades', path: '/livetrades', aliases: ['/trades', '/live-trades'] },
  { moduleId: 'command-center', path: '/commandcenter', aliases: ['/command-center', '/command'] },
  { moduleId: 'signals', path: '/aisignals', aliases: ['/signals', '/ai-signals'] },
  { moduleId: 'backtest', path: '/backtestlab', aliases: ['/backtest', '/backtest-lab', '/lab'] },
  { moduleId: 'prop-firm', path: '/propfirmcenter', aliases: ['/prop-firm', '/propfirm', '/prop'] },
  { moduleId: 'intelligence', path: '/intelligence', aliases: ['/marketintelligence', '/market-intelligence'] },
  { moduleId: 'news', path: '/ainewsfeed', aliases: ['/news', '/newsfeed', '/ai-news'] },
  { moduleId: 'portfolio', path: '/portfolio', aliases: ['/portfolio-risk'] },
  { moduleId: 'journal', path: '/tradejournal', aliases: ['/journal', '/trade-journal'] },
  { moduleId: 'analytics', path: '/analytics', aliases: ['/stats', '/performance'] },
  { moduleId: 'copilot', path: '/xraichat', aliases: ['/copilot', '/ai-chat', '/aichat'] },
  { moduleId: 'team', path: '/teamhub', aliases: ['/team', '/team-hub'] },
  { moduleId: 'automation', path: '/automation', aliases: ['/auto', '/bot-automation'] },
  { moduleId: 'server', path: '/servercenter', aliases: ['/server', '/server-center', '/cluster'] },
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

  return 'home';
}

/**
 * Returns canonical URL path for a given module ID
 */
export function getPathForModule(moduleId: ModuleView): string {
  const route = APP_ROUTES.find(r => r.moduleId === moduleId);
  return route ? route.path : '/missioncontrol';
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
