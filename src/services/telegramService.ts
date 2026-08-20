export interface TelegramStatusResponse {
  status: string;
  bot_name: string;
  registered_chats_count: number;
  chat_ids: string[];
  tracked_messages?: Record<string, number>;
}

export class TelegramService {
  /**
   * Fetch Telegram bot status and registered chats
   */
  public static async fetchTelegramStatus(): Promise<TelegramStatusResponse | null> {
    try {
      const res = await fetch('/api/v1/telegram/status');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('[TelegramService] fetchTelegramStatus failed:', err);
      return null;
    }
  }

  /**
   * Dispatch full Telegram test trade flow
   */
  public static async testTradeFlow(symbol: string = 'BTC/USDT', side: string = 'SHORT'): Promise<any> {
    try {
      const res = await fetch(`/api/v1/telegram/test-flow?symbol=${encodeURIComponent(symbol)}&side=${encodeURIComponent(side)}`, {
        method: 'POST'
      });
      return await res.json();
    } catch (err) {
      console.error('[TelegramService] testTradeFlow failed:', err);
      return { status: 'ERROR', message: String(err) };
    }
  }

  /**
   * Dispatch prop milestone notification test
   */
  public static async testMilestone(eventType: string = 'STAGE_1_PASSED'): Promise<any> {
    try {
      const res = await fetch(`/api/v1/telegram/test-milestones?event_type=${encodeURIComponent(eventType)}`, {
        method: 'POST'
      });
      return await res.json();
    } catch (err) {
      console.error('[TelegramService] testMilestone failed:', err);
      return { status: 'ERROR', message: String(err) };
    }
  }
}
