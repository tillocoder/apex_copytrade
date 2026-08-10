export type TradingEventType = 
  | 'POSITION_OPENED'
  | 'POSITION_CLOSED'
  | 'TP1_HIT'
  | 'TP2_HIT'
  | 'TP3_HIT'
  | 'SL_HIT'
  | 'BREAK_EVEN_ACTIVATED'
  | 'TRAILING_STOP_UPDATED'
  | 'PARTIAL_CLOSE'
  | 'MARGIN_WARNING'
  | 'DRAWDOWN_WARNING'
  | 'DAILY_LOSS_WARNING'
  | 'HIGH_VOLATILITY'
  | 'NEWS_IMPACT'
  | 'FUNDING_UPDATE'
  | 'EXCHANGE_STATUS'
  | 'WEBSOCKET_STATUS'
  | 'PYTHON_ENGINE_STATUS'
  | 'STRATEGY_SWITCHED'
  | 'CHALLENGE_PASSED'
  | 'CHALLENGE_FAILED';

export interface TradingEvent {
  id: string;
  type: TradingEventType;
  symbol?: string;
  positionId?: string;
  title: string;
  description: string;
  timestamp: string;
  category: 'Trading' | 'Risk' | 'Challenge' | 'System' | 'AI' | 'News' | 'Exchange';
  severity: 'info' | 'success' | 'warning' | 'danger';
  data?: Record<string, unknown>;
}

type EventListener = (event: TradingEvent) => void;

class EventBus {
  private listeners: EventListener[] = [];

  public subscribe(listener: EventListener): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  public publish(event: TradingEvent) {
    this.listeners.forEach(l => l(event));
  }
}

export const eventBus = new EventBus();
