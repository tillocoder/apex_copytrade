import React from 'react';
import { Settings, Key, Shield, Monitor, Bell, HardDrive } from 'lucide-react';

export const SettingsModule: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-apex-bg font-mono text-xs p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-apex-border pb-3">
        <div className="flex items-center space-x-2 font-bold text-sm text-apex-text">
          <Settings className="w-5 h-5 text-apex-cyan" />
          <span>TERMINAL SETTINGS & API CONFIGURATION</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="flex items-center space-x-2 text-apex-cyan font-bold text-xs">
            <Key className="w-4 h-4" />
            <span>EXCHANGE API KEYS (ENCRYPTED)</span>
          </div>
          <div className="space-y-2">
            <div>
              <label className="text-apex-muted text-[10px]">BINANCE FUTURES API KEY</label>
              <input type="password" value="••••••••••••••••••••••••" readOnly className="w-full bg-apex-panel border border-apex-border rounded px-3 py-1.5 text-apex-text outline-none" />
            </div>
            <div>
              <label className="text-apex-muted text-[10px]">BYBIT PRO API KEY</label>
              <input type="password" value="••••••••••••••••••••••••" readOnly className="w-full bg-apex-panel border border-apex-border rounded px-3 py-1.5 text-apex-text outline-none" />
            </div>
            <div>
              <label className="text-apex-muted text-[10px]">HYPERLIQUID WALLET PRIVATE KEY</label>
              <input type="password" value="••••••••••••••••••••••••" readOnly className="w-full bg-apex-panel border border-apex-border rounded px-3 py-1.5 text-apex-text outline-none" />
            </div>
          </div>
        </div>

        <div className="bg-apex-surface border border-apex-border p-4 rounded-lg space-y-3">
          <div className="flex items-center space-x-2 text-apex-cyan font-bold text-xs">
            <Shield className="w-4 h-4" />
            <span>RISK & LEVERAGE SAFETY RAILS</span>
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between py-1 border-b border-apex-border">
              <span className="text-apex-muted">MAX DRAWDOWN AUTO-KILL:</span>
              <span className="font-bold text-apex-red">5.0%</span>
            </div>
            <div className="flex justify-between py-1 border-b border-apex-border">
              <span className="text-apex-muted">MAX ACCOUNT LEVERAGE:</span>
              <span className="font-bold text-apex-cyan">25X</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-apex-muted">MAX SLIPPAGE TOLERANCE:</span>
              <span className="font-bold text-apex-green">0.05%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
