export class SettingsService {
  /**
   * Fetch current strategy engine configuration
   */
  public static async fetchEngineConfig(): Promise<any> {
    try {
      const res = await fetch('/api/v1/config');
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('[SettingsService] fetchEngineConfig failed:', err);
      return null;
    }
  }

  /**
   * Update engine configuration
   */
  public static async updateEngineConfig(configData: any): Promise<boolean> {
    try {
      const res = await fetch('/api/v1/config/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configData)
      });
      return res.ok;
    } catch (err) {
      console.error('[SettingsService] updateEngineConfig failed:', err);
      return false;
    }
  }
}
