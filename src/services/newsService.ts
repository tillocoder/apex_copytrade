import type { NewsArticle } from '../types';

export interface EconomicEvent {
  id: string;
  title: string;
  impact: string;
  severity: 'high' | 'medium' | 'low';
  date: string;
  time: string;
  forecast: string;
  previous: string;
  country: string;
}

export class NewsService {
  /**
   * Fetch live crypto institutional news feed
   */
  public static async fetchNewsFeed(): Promise<NewsArticle[]> {
    try {
      const res = await fetch('/api/v1/news/feed');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      if (json.status === 'SUCCESS' && Array.isArray(json.data)) {
        return json.data;
      }
      return [];
    } catch (err) {
      console.error('[NewsService] fetchNewsFeed failed:', err);
      return [];
    }
  }

  /**
   * Fetch ForexFactory high/medium impact economic calendar events
   */
  public static async fetchEconomicCalendar(): Promise<EconomicEvent[]> {
    try {
      const res = await fetch('/api/v1/news/economic-calendar');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      if (json.status === 'SUCCESS' && Array.isArray(json.data)) {
        return json.data;
      }
      return [];
    } catch (err) {
      console.error('[NewsService] fetchEconomicCalendar failed:', err);
      return [];
    }
  }
}
