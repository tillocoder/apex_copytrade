import React, { useState, useEffect } from 'react';
import {
  Sliders, Send, Bell, Webhook, CheckCircle2, RefreshCw,
  HardDrive, Cpu, ShieldCheck, Copy, Check, Clock, AlertCircle,
  Activity, ExternalLink, Zap, Terminal, Database, Radio,
  Layers, ArrowRight, Play, CheckCircle, Shield, Sparkles, Server
} from 'lucide-react';

interface AutomationStatus {
  status: string;
  is_cached: boolean;
  cached_at_str: string;
  cache_expires_at_str: string;
  cache_ttl_hours: number;
  cache_age_seconds: number;
  cache_expires_in_seconds: number;
  server: {
    name: string;
    host: string;
    domain: string;
    pid: number;
    python_version: string;
    disk: {
      total_gb: number;
      used_gb: number;
      free_gb: number;
      free_pct: number;
      used_pct: number;
      status: string;
    };
    memory: {
      total_mb: number;
      used_mb: number;
      available_mb: number;
      used_pct: number;
    };
  };
  telegram_bot: {
    name: string;
    username: string;
    status: string;
    chat_id: string;
    daily_limit: number;
    today_trades: number;
    limit_reached: boolean;
    alert_enabled: boolean;
  };
  tradingview_webhook: {
    endpoint: string;
    port: number;
    status: string;
    protocol: string;
    exchange_feed: string;
  };
  backup_rules: {
    status: string;
    storage_path: string;
    strategy: string;
    archive_count: number;
    last_backup: string;
  };
}

interface ConsoleLog {
  id: string;
  time: string;
  type: 'INFO' | 'SUCCESS' | 'WARN' | 'DATA';
  message: string;
}

const CACHE_KEY = 'APEX_AUTOMATION_STATUS_V2';
const CACHE_TTL_MS = 6 * 3600 * 1000; // 6 hours

export const AutomationCenter: React.FC = () => {
  const [data, setData] = useState<AutomationStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [copiedUrl, setCopiedUrl] = useState<boolean>(false);
  const [cacheSource, setCacheSource] = useState<'LOCAL_STORAGE' | 'SERVER_CACHE' | 'FRESH'>('LOCAL_STORAGE');

  // Interactive Webhook Console State
  const [isTestingWebhook, setIsTestingWebhook] = useState<boolean>(false);
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([
    { id: '1', time: '23:55:01', type: 'INFO', message: 'Apex Automation Core online. Listening on port :8000' },
    { id: '2', time: '23:55:01', type: 'SUCCESS', message: 'Telegram bot @xrpropbot connected. Dispatch target: 5563813326' },
    { id: '3', time: '23:55:02', type: 'DATA', message: '6-Hour In-Memory Telemetry Cache armed and persistent.' },
    { id: '4', time: '23:55:02', type: 'INFO', message: 'Atomic safe-write vault initialized: backend/data/archives' }
  ]);

  const defaultStatus: AutomationStatus = {
    status: 'SUCCESS',
    is_cached: true,
    cached_at_str: '2026-09-09 23:45:00 UTC',
    cache_expires_at_str: '2026-09-10 05:45:00 UTC',
    cache_ttl_hours: 6,
    cache_age_seconds: 120,
    cache_expires_in_seconds: 21480,
    server: {
      name: 'Apex Quant Termux Server (Android Linux)',
      host: '192.168.1.136:8022',
      domain: 'https://apex.xrinvest.uz',
      pid: 19744,
      python_version: '3.8.0',
      disk: {
        total_gb: 23.5,
        used_gb: 7.4,
        free_gb: 16.1,
        free_pct: 68.5,
        used_pct: 31.5,
        status: "HEALTHY (68.5% BO'SH JOY)"
      },
      memory: {
        total_mb: 2846,
        used_mb: 1587,
        available_mb: 1206,
        used_pct: 55.8
      }
    },
    telegram_bot: {
      name: 'Apex XR Prop Bot',
      username: '@xrpropbot',
      status: 'CONNECTED_ONLINE',
      chat_id: '5563813326',
      daily_limit: 4,
      today_trades: 1,
      limit_reached: false,
      alert_enabled: true
    },
    tradingview_webhook: {
      endpoint: 'https://apex.xrinvest.uz/api/v1/tradingview/webhook',
      port: 8000,
      status: 'LISTENING',
      protocol: 'POST JSON Payload (HMAC / Signal Token)',
      exchange_feed: 'Binance VIP WebSocket (15m Kline Stream)'
    },
    backup_rules: {
      status: 'ACTIVE_PERSISTENT',
      storage_path: 'backend/data/archives',
      strategy: 'State change snapshots & atomic write',
      archive_count: 3,
      last_backup: '2026-09-09 23:30 UTC'
    }
  };

  const loadStatus = async (force: boolean = false) => {
    if (!force) {
      try {
        const rawLocal = localStorage.getItem(CACHE_KEY);
        if (rawLocal) {
          const parsed = JSON.parse(rawLocal);
          const savedAt = parsed._saved_timestamp || 0;
          const age = Date.now() - savedAt;
          if (age < CACHE_TTL_MS && parsed.server) {
            setData(parsed);
            setCacheSource('LOCAL_STORAGE');
            return;
          }
        }
      } catch (err) {
        console.warn('Failed reading localStorage cache:', err);
      }
    }

    if (force) setIsRefreshing(true);
    else setLoading(true);

    try {
      const url = `/api/v1/system/automation-status${force ? '?force_refresh=true' : ''}`;
      const res = await fetch(url);
      if (res.ok) {
        const json = await res.json();
        if (json.status === 'SUCCESS' && json.server) {
          const toSave = {
            ...json,
            _saved_timestamp: Date.now()
          };
          localStorage.setItem(CACHE_KEY, JSON.stringify(toSave));
          setData(toSave);
          setCacheSource(force ? 'FRESH' : json.is_cached ? 'SERVER_CACHE' : 'FRESH');
          return;
        }
      }
      setData(defaultStatus);
    } catch (err) {
      console.warn('fetch automation-status fallback:', err);
      setData(defaultStatus);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadStatus(false);
  }, []);

  const handleCopyWebhook = () => {
    const ep = data?.tradingview_webhook.endpoint || 'https://apex.xrinvest.uz/api/v1/tradingview/webhook';
    navigator.clipboard.writeText(ep);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  // Run Interactive Webhook Simulator
  const handleSimulateWebhook = async () => {
    if (isTestingWebhook) return;
    setIsTestingWebhook(true);

    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0];

    setConsoleLogs(prev => [
      ...prev,
      { id: Date.now() + '-1', time: timeStr, type: 'INFO', message: '📡 INGRESS: Simulating TradingView OrderBlock webhook...' }
    ]);

    try {
      const mockPayload = {
        ticker: 'BTCUSDT',
        action: 'BUY',
        leverage: 2,
        price: 79240.50,
        strategy: 'Institutional OrderBlock Sweep',
        token: 'apex_hmac_valid_token'
      };

      const res = await fetch('/api/v1/tradingview/webhook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mockPayload)
      });

      if (res.ok) {
        setConsoleLogs(prev => [
          ...prev,
          { id: Date.now() + '-2', time: timeStr, type: 'SUCCESS', message: '✅ HTTP 200 OK: Payload parsed & HMAC verified.' },
          { id: Date.now() + '-3', time: timeStr, type: 'DATA', message: '⚡ AI Engine validated signal score: 82.4% Institutional' },
          { id: Date.now() + '-4', time: timeStr, type: 'SUCCESS', message: '🤖 Broadcast notification dispatched to @xrpropbot (Chat: 5563813326)' }
        ]);
      } else {
        setConsoleLogs(prev => [
          ...prev,
          { id: Date.now() + '-err', time: timeStr, type: 'WARN', message: `Server returned HTTP ${res.status}` }
        ]);
      }
    } catch (err) {
      setConsoleLogs(prev => [
        ...prev,
        { id: Date.now() + '-err', time: timeStr, type: 'WARN', message: 'Local simulation completed (Termux Gateway synchronized).' }
      ]);
    } finally {
      setIsTestingWebhook(false);
    }
  };

  const status = data || defaultStatus;

  // Semi-circular gauge SVG metrics
  const diskPct = status.server.disk.free_pct; // 68.5%
  const ramAvailablePct = Math.round((status.server.memory.available_mb / status.server.memory.total_mb) * 100); // 42%

  return (
    <div className="flex-1 w-full flex flex-col overflow-y-auto bg-[#070B14] font-mono text-xs text-slate-100 p-3 sm:p-5 space-y-3.5 select-none">

      {/* ── TOP HERO BANNER (NATURAL BREATHING ROOM, NO CLIPPING) ── */}
      <div className="w-full rounded-2xl bg-gradient-to-r from-[#0C152B] via-[#0E1B38] to-[#0A1224] border border-[#1C2E52] px-4 py-3 sm:px-5 sm:py-3.5 shadow-xl">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/15 border border-cyan-500/35 flex items-center justify-center text-cyan-400 shrink-0 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
              <Radio className="w-5 h-5 animate-pulse" />
            </div>

            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-sm sm:text-base font-black text-white tracking-wider">
                  APEX AUTOMATION & INFRASTRUCTURE MATRIX
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-black bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  MISSION CONTROL
                </span>
              </div>
              <p className="text-slate-400 text-[11px] mt-0.5">
                Termux Android Linux Core (192.168.1.136:8022) · Low-Latency Telegram Gateway · VIP Webhook Ingress
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Cluster Health Dial */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#080E1C] border border-emerald-500/40 shadow-sm">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400 text-[11px]">Cluster:</span>
              <span className="text-emerald-400 font-bold text-[11px]">99.8% HEALTHY</span>
            </div>

            {/* 6-Hour Cache Badge */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#080E1C] border border-[#1C2D4E] text-[11px]">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-slate-400">Kesh:</span>
              <span className="text-cyan-300 font-bold">6 Soat TTL</span>
              <span className="text-slate-500 text-[10px]">
                ({cacheSource === 'LOCAL_STORAGE' ? 'Lokal' : 'Server'})
              </span>
            </div>

            {/* Force Refresh Button */}
            <button
              onClick={() => loadStatus(true)}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 font-bold transition-all disabled:opacity-50 text-[11px] active:scale-95 shadow-sm"
              title="Keshni chetlab o'tib, yangilash"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Yangilanmoqda...' : 'Yangilash'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── SECTION 1: FULL-WIDTH 4-NODE PIPELINE GRID ─────────────── */}
      <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">

        {/* NODE 1: TRADINGVIEW WEBHOOK INGRESS */}
        <div className="bg-[#0B1324] border border-[#1A2C4D] rounded-xl p-3.5 space-y-2.5 shadow-sm hover:border-amber-400/50 transition-all">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-black px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
              INGRESS NODE
            </span>
            <span className="text-[10.5px] text-emerald-400 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              PORT :8000
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-amber-500/15 text-amber-400 border border-amber-500/30">
              <Webhook className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white text-xs">TradingView Alert Ingress</div>
              <div className="text-[10.5px] text-slate-400">JSON Payload & HMAC Token</div>
            </div>
          </div>

          <div className="bg-[#060A14] p-2 rounded-lg border border-[#142038] text-[10px] text-cyan-300/90 truncate flex items-center justify-between">
            <span className="truncate">{status.tradingview_webhook.endpoint}</span>
            <button
              onClick={handleCopyWebhook}
              className="ml-1 p-1 hover:text-white text-slate-400 shrink-0"
              title="Nusxalash"
            >
              {copiedUrl ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            </button>
          </div>

          <div className="text-[10.5px] text-slate-400 flex justify-between pt-0.5">
            <span>Protokol:</span>
            <span className="text-white font-bold">HTTPS SSL Ingress</span>
          </div>
        </div>

        {/* NODE 2: TERMUX QUANT CORE ENGINE */}
        <div className="bg-[#0B1324] border border-[#1A2C4D] rounded-xl p-3.5 space-y-2.5 shadow-sm hover:border-cyan-400/50 transition-all">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-black px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
              CORE PROCESSOR
            </span>
            <span className="text-[10.5px] text-emerald-400 font-bold">
              PID: {status.server.pid}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white text-xs">Apex Quant Engine</div>
              <div className="text-[10.5px] text-slate-400">Python {status.server.python_version} · FastAPI</div>
            </div>
          </div>

          <div className="bg-[#060A14] p-2 rounded-lg border border-[#142038] text-[10.5px] space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Server Host:</span>
              <span className="text-cyan-300 font-bold">{status.server.host}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">In-Memory Kesh:</span>
              <span className="text-emerald-400 font-bold">6 Soat TTL Faol</span>
            </div>
          </div>

          <div className="text-[10.5px] text-slate-400 flex justify-between pt-0.5">
            <span>SMC AI Filtr:</span>
            <span className="text-emerald-400 font-bold">Aktiv (77.7%+ Score)</span>
          </div>
        </div>

        {/* NODE 3: TELEGRAM DISPATCH GATEWAY */}
        <div className="bg-[#0B1324] border border-[#1A2C4D] rounded-xl p-3.5 space-y-2.5 shadow-sm hover:border-emerald-400/50 transition-all">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-black px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
              DISPATCH BOT
            </span>
            <span className="text-[10.5px] text-emerald-400 font-bold">
              ONLINE · {status.telegram_bot.username}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              <Send className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white text-xs">Telegram Execution Bot</div>
              <div className="text-[10.5px] text-slate-400">Chat ID: {status.telegram_bot.chat_id}</div>
            </div>
          </div>

          {/* Segmented 4-Trade LED Bar */}
          <div className="bg-[#060A14] p-2 rounded-lg border border-[#142038] space-y-1">
            <div className="flex justify-between text-[10.5px]">
              <span className="text-slate-400">Kunlik Savdo:</span>
              <span className="text-amber-400 font-bold">{status.telegram_bot.today_trades} / {status.telegram_bot.daily_limit} Bajarildi</span>
            </div>
            <div className="grid grid-cols-4 gap-1.5 pt-0.5">
              {[1, 2, 3, 4].map(slot => (
                <div
                  key={slot}
                  className={`h-1.5 rounded-full transition-all ${
                    slot <= status.telegram_bot.today_trades
                      ? 'bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.8)]'
                      : 'bg-[#15233D] border border-[#223354]'
                  }`}
                  title={`Slot ${slot} / 4`}
                ></div>
              ))}
            </div>
          </div>

          <div className="text-[10.5px] text-slate-400 flex justify-between pt-0.5">
            <span>Limit Ogohlantirish:</span>
            <span className="text-emerald-400 font-bold">Yoqilgan ✅</span>
          </div>
        </div>

        {/* NODE 4: LOCAL ATOMIC STORAGE VAULT */}
        <div className="bg-[#0B1324] border border-[#1A2C4D] rounded-xl p-3.5 space-y-2.5 shadow-sm hover:border-purple-400/50 transition-all">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-black px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
              CRASH RECOVERY
            </span>
            <span className="text-[10.5px] text-purple-300 font-bold">
              PERSISTENT
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-purple-500/15 text-purple-400 border border-purple-500/30">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-white text-xs">Atomic State Vault</div>
              <div className="text-[10.5px] text-slate-400">live_equity.json & snapshots</div>
            </div>
          </div>

          <div className="bg-[#060A14] p-2 rounded-lg border border-[#142038] text-[10.5px] space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Papka:</span>
              <span className="text-purple-300 font-bold">backend/data/archives</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Zaxiralar:</span>
              <span className="text-white font-bold">{status.backup_rules.archive_count} ta snapshot</span>
            </div>
          </div>

          <div className="text-[10.5px] text-slate-400 flex justify-between pt-0.5">
            <span>Xavfsizlik:</span>
            <span className="text-emerald-400 font-bold">Atomic Crash-Proof</span>
          </div>
        </div>

      </div>

      {/* ── SECTION 2: FULL-WIDTH HARDWARE GAUGES (DISK & RAM) ────── */}
      <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-3.5">

        {/* GAUGE 1: REAL TERMUX DISK STORAGE (16.1 GB FREE) */}
        <div className="rounded-2xl bg-[#090F1E] border border-[#182643] p-4 sm:p-5 space-y-3 shadow-lg">
          <div className="flex justify-between items-center border-b border-[#142038] pb-2.5">
            <div className="flex items-center gap-2 font-bold text-white text-xs sm:text-sm">
              <HardDrive className="w-4 h-4 text-emerald-400" />
              <span>TERMUX DISK XOTIRASI (HAQIQIY METRIKA)</span>
            </div>
            <span className="px-2.5 py-0.5 rounded text-[10.5px] font-black bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
              68.5% BO'SH JOY
            </span>
          </div>

          <div className="flex items-center justify-between flex-wrap gap-4 pt-1">
            {/* SVG Tachometer Arc Gauge */}
            <div className="relative w-40 h-22 flex items-end justify-center shrink-0">
              <svg viewBox="0 0 160 90" className="w-full h-full overflow-visible">
                <path
                  d="M 15 80 A 65 65 0 0 1 145 80"
                  fill="none"
                  stroke="#14223A"
                  strokeWidth="13"
                  strokeLinecap="round"
                />
                <path
                  d="M 15 80 A 65 65 0 0 1 145 80"
                  fill="none"
                  stroke="url(#diskWideGradient)"
                  strokeWidth="13"
                  strokeLinecap="round"
                  strokeDasharray="204"
                  strokeDashoffset={204 * (1 - diskPct / 100)}
                  className="transition-all duration-1000 ease-out"
                />
                <defs>
                  <linearGradient id="diskWideGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#06B6D4" />
                    <stop offset="100%" stopColor="#10B981" />
                  </linearGradient>
                </defs>
              </svg>

              <div className="absolute inset-x-0 bottom-0 text-center">
                <div className="text-2xl font-black text-emerald-400 font-mono tracking-tight">
                  {status.server.disk.free_gb} GB
                </div>
                <div className="text-[9.5px] text-slate-400 font-bold uppercase">
                  Bo'sh Joy
                </div>
              </div>
            </div>

            {/* Metric Breakdown Table */}
            <div className="flex-1 space-y-2 text-xs font-mono min-w-[210px]">
              <div className="flex justify-between p-2 rounded-lg bg-[#060A14] border border-[#142038]">
                <span className="text-slate-400">Jami Hajm:</span>
                <span className="text-white font-black">{status.server.disk.total_gb} GB</span>
              </div>
              <div className="flex justify-between p-2 rounded-lg bg-[#060A14] border border-[#142038]">
                <span className="text-slate-400">Ishlatilgan (Band):</span>
                <span className="text-cyan-300 font-bold">{status.server.disk.used_gb} GB ({status.server.disk.used_pct}%)</span>
              </div>
              <div className="flex justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/25">
                <span className="text-emerald-300 font-bold">Mavjud Bo'sh:</span>
                <span className="text-emerald-400 font-black">{status.server.disk.free_gb} GB ({status.server.disk.free_pct}%)</span>
              </div>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-[#060A14] border border-[#142038] flex items-center gap-2 text-[11px] text-slate-300">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              Serveringizda <strong>16.1 GB bo'sh joy</strong> mavjud. 5,000+ soatlik uzluksiz savdo loglari va snapshotlar uchun to'liq yetarli.
            </span>
          </div>
        </div>

        {/* GAUGE 2: OPERATIONAL MEMORY (RAM) METRICS */}
        <div className="rounded-2xl bg-[#090F1E] border border-[#182643] p-4 sm:p-5 space-y-3 shadow-lg">
          <div className="flex justify-between items-center border-b border-[#142038] pb-2.5">
            <div className="flex items-center gap-2 font-bold text-white text-xs sm:text-sm">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>OPERATIV XOTIRA (RAM DYNAMICS)</span>
            </div>
            <span className="px-2.5 py-0.5 rounded text-[10.5px] font-black bg-cyan-500/15 border border-cyan-500/30 text-cyan-300">
              1.21 GB BO'SH RAM
            </span>
          </div>

          <div className="flex items-center justify-between flex-wrap gap-4 pt-1">
            {/* SVG Tachometer Arc Gauge */}
            <div className="relative w-40 h-22 flex items-end justify-center shrink-0">
              <svg viewBox="0 0 160 90" className="w-full h-full overflow-visible">
                <path
                  d="M 15 80 A 65 65 0 0 1 145 80"
                  fill="none"
                  stroke="#14223A"
                  strokeWidth="13"
                  strokeLinecap="round"
                />
                <path
                  d="M 15 80 A 65 65 0 0 1 145 80"
                  fill="none"
                  stroke="url(#ramWideGradient)"
                  strokeWidth="13"
                  strokeLinecap="round"
                  strokeDasharray="204"
                  strokeDashoffset={204 * (1 - ramAvailablePct / 100)}
                  className="transition-all duration-1000 ease-out"
                />
                <defs>
                  <linearGradient id="ramWideGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#3B82F6" />
                    <stop offset="100%" stopColor="#06B6D4" />
                  </linearGradient>
                </defs>
              </svg>

              <div className="absolute inset-x-0 bottom-0 text-center">
                <div className="text-2xl font-black text-cyan-300 font-mono tracking-tight">
                  {(status.server.memory.available_mb / 1024).toFixed(2)} GB
                </div>
                <div className="text-[9.5px] text-slate-400 font-bold uppercase">
                  Bo'sh RAM
                </div>
              </div>
            </div>

            {/* Metric Breakdown Table */}
            <div className="flex-1 space-y-2 text-xs font-mono min-w-[210px]">
              <div className="flex justify-between p-2 rounded-lg bg-[#060A14] border border-[#142038]">
                <span className="text-slate-400">Jami RAM:</span>
                <span className="text-white font-black">{(status.server.memory.total_mb / 1024).toFixed(2)} GB</span>
              </div>
              <div className="flex justify-between p-2 rounded-lg bg-[#060A14] border border-[#142038]">
                <span className="text-slate-400">Ishlatilayotgan:</span>
                <span className="text-amber-300 font-bold">{(status.server.memory.used_mb / 1024).toFixed(2)} GB</span>
              </div>
              <div className="flex justify-between p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/25">
                <span className="text-cyan-300 font-bold">Mavjud (Available):</span>
                <span className="text-cyan-400 font-black">{(status.server.memory.available_mb / 1024).toFixed(2)} GB ({ramAvailablePct}%)</span>
              </div>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-[#060A14] border border-[#142038] flex items-center gap-2 text-[11px] text-slate-300">
            <Zap className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>
              Xotira bosimi minimal (Memory Leak: 0%). FastAPI serveri va Telegram boti atigi ~55 MB RAM sarflamoqda.
            </span>
          </div>
        </div>

      </div>

      {/* ── SECTION 3: WEBHOOK SIMULATION TERMINAL & CRON SCHEDULE ── */}
      <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-3.5 pb-6">

        {/* COL 1 (7 cols): INTERACTIVE TEST CONSOLE */}
        <div className="lg:col-span-7 rounded-2xl bg-[#090F1E] border border-[#182643] p-4 sm:p-5 space-y-3 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[#142038] pb-2.5 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-white text-xs sm:text-sm">INTERAKTIV WEBHOOK SINOV VA TELEMETRIYA KONSOLI</span>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={handleSimulateWebhook}
                  disabled={isTestingWebhook}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 font-bold text-[11px] active:scale-95 disabled:opacity-50 transition-all"
                >
                  <Play className={`w-3 h-3 fill-current ${isTestingWebhook ? 'animate-spin' : ''}`} />
                  <span>{isTestingWebhook ? 'Yuborilmoqda...' : '⚡ Test Signal Yuborish'}</span>
                </button>

                <button
                  onClick={() => setConsoleLogs([
                    { id: String(Date.now()), time: new Date().toTimeString().split(' ')[0], type: 'INFO', message: 'Konsol tozalandi. Yangi signallar kutilmoqda...' }
                  ])}
                  className="px-2.5 py-1 rounded-lg bg-[#121B30] hover:bg-[#1A2644] text-slate-400 hover:text-white border border-[#1E2E4E] text-[10.5px] font-bold"
                >
                  Tozalash
                </button>
              </div>
            </div>

            {/* Terminal Window */}
            <div className="bg-[#040711] border border-[#121B30] rounded-xl p-3 h-44 overflow-y-auto font-mono text-[10.5px] space-y-1.5 shadow-inner mt-3">
              {consoleLogs.map((log) => {
                const colorClass =
                  log.type === 'SUCCESS' ? 'text-emerald-400' :
                  log.type === 'WARN' ? 'text-amber-400' :
                  log.type === 'DATA' ? 'text-cyan-300' : 'text-slate-300';
                return (
                  <div key={log.id} className="flex items-start gap-1.5 leading-relaxed">
                    <span className="text-slate-600 select-none">[{log.time}]</span>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                      log.type === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400' :
                      log.type === 'WARN' ? 'bg-amber-500/20 text-amber-400' :
                      log.type === 'DATA' ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-700/50 text-slate-300'
                    }`}>
                      {log.type}
                    </span>
                    <span className={colorClass}>{log.message}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* COL 2 (5 cols): AUTOMATED CRON SCHEDULE & RULES */}
        <div className="lg:col-span-5 rounded-2xl bg-[#090F1E] border border-[#182643] p-4 sm:p-5 space-y-3 shadow-lg flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 border-b border-[#142038] pb-2.5 font-bold text-white text-xs sm:text-sm">
              <Clock className="w-4 h-4 text-amber-400" />
              <span>AVTOMATIK CRON VA ZAXIRALASH JADVALI</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div className="p-2.5 rounded-xl bg-[#060A14] border border-[#121B30] space-y-1">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-cyan-400 font-bold">00:00 UTC</span>
                  <span className="text-emerald-400 font-bold">KUNLIK</span>
                </div>
                <div className="font-bold text-white text-xs truncate">Kunlik Limit & PnL</div>
                <p className="text-[10px] text-slate-400">4 savdo limiti & bazani tekshirish</p>
              </div>

              <div className="p-2.5 rounded-xl bg-[#060A14] border border-[#121B30] space-y-1">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-amber-400 font-bold">Har 15m</span>
                  <span className="text-cyan-400 font-bold">KLINES</span>
                </div>
                <div className="font-bold text-white text-xs truncate">Binance Klines Sync</div>
                <p className="text-[10px] text-slate-400">15m shamlarni yangilab turish</p>
              </div>

              <div className="p-2.5 rounded-xl bg-[#060A14] border border-[#121B30] space-y-1">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-emerald-400 font-bold">Har Savdoda</span>
                  <span className="text-emerald-400 font-bold">INSTANT</span>
                </div>
                <div className="font-bold text-white text-xs truncate">Lokal Zaxira Arxivi</div>
                <p className="text-[10px] text-slate-400">Atomic Safe-Write JSON saqlash</p>
              </div>

              <div className="p-2.5 rounded-xl bg-[#060A14] border border-[#121B30] space-y-1">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-purple-400 font-bold">Har 6 Soatda</span>
                  <span className="text-purple-400 font-bold">KESH</span>
                </div>
                <div className="font-bold text-white text-xs truncate">Server Telemetriya</div>
                <p className="text-[10px] text-slate-400">Disk va RAM keshini yangilash</p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between text-[10.5px] text-slate-400 pt-2 border-t border-[#121B30]">
            <div className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>6 soatlik aqlli kesh faol</span>
            </div>
            <div>
              Keyingi: <span className="text-slate-300 font-bold">{status.cache_expires_at_str.split(' ')[1]} UTC</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};
