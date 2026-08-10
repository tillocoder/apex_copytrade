import React from 'react';
import { Sliders, Send, Bell, Webhook, CheckCircle2 } from 'lucide-react';

export const AutomationCenter: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Sliders className="w-5 h-5 text-apex-cyan" />
          <span>AUTOMATION CENTER, BOTS & WEBHOOKS</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="flex justify-between items-center font-bold">
            <span className="text-apex-text text-sm">TELEGRAM SIGNAL BOT</span>
            <span className="text-apex-green text-[10px] bg-apex-green/20 px-2 py-0.5 rounded">CONNECTED</span>
          </div>
          <p className="text-apex-muted text-[11px]">Instant execution alerts & signal notifications dispatched to @ApexQuantSignals_Bot.</p>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="flex justify-between items-center font-bold">
            <span className="text-apex-text text-sm">TRADINGVIEW WEBHOOK INGRESS</span>
            <span className="text-apex-cyan text-[10px] bg-apex-cyan/20 px-2 py-0.5 rounded">LISTENING :8000</span>
          </div>
          <p className="text-apex-muted text-[11px]">JSON Webhook endpoint: https://api.apexquant.fund/v1/webhook/tv-alerts</p>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="flex justify-between items-center font-bold">
            <span className="text-apex-text text-sm">AUTO-BACKUP & RESTART RULES</span>
            <span className="text-emerald-400 text-[10px] bg-emerald-950 px-2 py-0.5 rounded">ACTIVE DAILY 00:00</span>
          </div>
          <p className="text-apex-muted text-[11px]">PostgreSQL dumps & Redis snapshot sent to encrypted AWS S3 cold vault.</p>
        </div>
      </div>
    </div>
  );
};
