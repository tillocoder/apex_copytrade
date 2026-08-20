export interface AIChatMessagePayload {
  prompt: string;
  apiKey?: string;
  history?: Array<{ sender: string; text: string }>;
}

export interface AIChatResponse {
  status: 'SUCCESS' | 'ERROR';
  reply: string;
  message?: string;
}

export class AIChatService {
  /**
   * Send prompt to XR AI Chat solver
   */
  public static async sendAIChat(prompt: string, apiKey?: string, history?: any[]): Promise<string> {
    try {
      const res = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, apiKey, history })
      });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json: AIChatResponse = await res.json();
      if (json.status === 'SUCCESS' && json.reply) {
        return json.reply;
      }
      return json.reply || 'No response generated.';
    } catch (err) {
      console.error('[AIChatService] sendAIChat failed:', err);
      return 'Error connecting to XR AI Chat backend service.';
    }
  }

  /**
   * Send prompt to Copilot endpoint
   */
  public static async sendCopilot(prompt: string, symbol: string = 'BTC/USDT'): Promise<string> {
    try {
      const res = await fetch('/api/v1/ai/copilot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, symbol })
      });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      return json.reply || 'No response generated.';
    } catch (err) {
      console.error('[AIChatService] sendCopilot failed:', err);
      return 'Error connecting to AI Copilot backend.';
    }
  }
}
