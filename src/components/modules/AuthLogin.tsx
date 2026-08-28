import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { AuthService } from '../../services/authService';
import { 
  ShieldCheck, 
  KeyRound, 
  Lock, 
  Mail, 
  Server, 
  Wifi, 
  Database, 
  TrendingUp, 
  AlertTriangle, 
  UserCheck,
  Loader2
} from 'lucide-react';

export const AuthLogin: React.FC = () => {
  const { loginUser, tickers = [], health = {} as any } = useTerminal();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'credentials' | '2fa'>('credentials');
  const [twoFactorCode, setTwoFactorCode] = useState('');

  const safeTickers = Array.isArray(tickers) ? tickers : [];
  const btcTicker = safeTickers.find(t => t.symbol === 'BTC/USDT');
  const ethTicker = safeTickers.find(t => t.symbol === 'ETH/USDT');

  const btcPrice = btcTicker && btcTicker.price ? btcTicker.price.toLocaleString() : '80,724';
  const ethPrice = ethTicker && ethTicker.price ? ethTicker.price.toLocaleString() : '2,527';

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // First verify credentials against secure backend API
      const session = await AuthService.login(email, password, undefined, rememberMe ? 7 : 0);
      setStep('2fa');
      setLoading(false);
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'Kirish rad etildi. Email yoki parol noto\'g\'ri.');
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const session = await AuthService.login(email, password, twoFactorCode, rememberMe ? 7 : 0);
      loginUser(session.user, rememberMe ? 7 : 0);
    } catch (err: any) {
      setLoading(false);
      setError(err.message || '2FA kodi noto\'g\'ri.');
    }
  };

  return (
    <div className="min-h-screen w-screen bg-apex-bg text-apex-text flex flex-col justify-between p-4 relative overflow-hidden font-sans select-none">
      {/* Dynamic Background Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[550px] h-[550px] bg-apex-accent/5 rounded-full blur-3xl pointer-events-none" />

      {/* Top Status Header */}
      <div className="w-full bg-apex-bgSecondary border border-apex-border rounded-panel p-2.5 flex items-center justify-between font-mono text-xs z-10">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-apex-accent animate-pulse" />
            <span className="font-bold text-apex-text tracking-wide">APEX QUANT GATEWAY</span>
          </div>

          <div className="hidden sm:flex items-center space-x-4 border-l border-apex-border pl-4">
            <div className="flex items-center space-x-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-apex-success" />
              <span className="text-apex-muted">BTC:</span>
              <span className="font-bold text-apex-success">${btcPrice}</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-apex-success" />
              <span className="text-apex-muted">ETH:</span>
              <span className="font-bold text-apex-success">${ethPrice}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-[11px] text-apex-muted">
          <span className="flex items-center gap-1"><Server className="w-3 h-3 text-apex-muted" /> VPS ({health?.vpsLatency || 12}ms)</span>
          <span className="flex items-center gap-1"><Wifi className="w-3 h-3 text-apex-muted" /> WS ({health?.wsLatency || 8}ms)</span>
          <span className="flex items-center gap-1"><Database className="w-3 h-3 text-apex-muted" /> DB ({health?.dbLatency || 0}ms)</span>
        </div>
      </div>

      {/* Central Login Card */}
      <div className="w-full max-w-md mx-auto my-auto z-10 space-y-4">
        <div className="p-6 sm:p-8 space-y-6 shadow-2xl border border-apex-border/80 bg-apex-bgSecondary/95 backdrop-blur-md rounded-panel">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-apex-surface border border-apex-accent/40 text-apex-accent mx-auto flex items-center justify-center shadow-lg shadow-apex-accent/10">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-apex-text font-mono">APEX QUANT TERMINAL</h1>
            <p className="text-xs text-apex-muted font-mono">Institutional Access Control & Security Lock</p>
          </div>

          {error && (
            <div className="p-3 bg-apex-danger/15 border border-apex-danger/40 text-apex-danger rounded-panel text-xs flex items-center gap-2 font-mono">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {step === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-apex-muted mb-1 text-[11px]">ACCOUNT EMAIL</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-apex-muted absolute left-3 top-3" />
                  <input 
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter email address"
                    className="w-full bg-apex-bg border border-apex-border rounded-btn px-3 py-2.5 pl-9 text-apex-text focus:border-apex-accent outline-none transition-apex"
                  />
                </div>
              </div>

              <div>
                <label className="block text-apex-muted mb-1 text-[11px]">PASSWORD</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-apex-muted absolute left-3 top-3" />
                  <input 
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter security password"
                    className="w-full bg-apex-bg border border-apex-border rounded-btn px-3 py-2.5 pl-9 text-apex-text focus:border-apex-accent outline-none transition-apex"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <label className="flex items-center space-x-2 cursor-pointer text-apex-muted hover:text-apex-text transition-apex text-[11px]">
                  <input 
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-3.5 h-3.5 rounded bg-apex-bg border-apex-border text-apex-accent accent-apex-accent focus:ring-0 cursor-pointer"
                  />
                  <span>Tizimda 7 kun eslab qolinsin (Stay Logged In)</span>
                </label>
              </div>

              <button 
                type="submit"
                disabled={loading}
                className="w-full bg-apex-accent hover:bg-blue-600 disabled:opacity-50 text-white font-bold py-3 rounded-btn transition-apex flex items-center justify-center space-x-2 font-mono shadow-lg shadow-apex-accent/20 cursor-pointer"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                <span>VERIFY & PROCEED TO 2FA</span>
              </button>
            </form>
          ) : (
            <form onSubmit={handle2FASubmit} className="space-y-4 font-mono text-xs">
              <div className="bg-apex-surface/80 p-3.5 rounded-panel border border-apex-border text-center space-y-1">
                <div className="text-apex-accent font-bold flex items-center justify-center gap-1.5 text-sm">
                  <UserCheck className="w-4 h-4 text-apex-accent" /> CREDENTIALS CONFIRMED
                </div>
                <div className="text-[10px] text-apex-muted">Enter 2FA Security PIN (or press Enter) to access terminal.</div>
              </div>

              <div>
                <label className="block text-apex-muted mb-1 text-[11px]">2FA SECURITY PIN</label>
                <input 
                  type="text"
                  maxLength={6}
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  placeholder="------"
                  autoFocus
                  className="w-full bg-apex-bg border border-apex-accent/50 rounded-btn px-3 py-2.5 text-center text-apex-accent font-bold tracking-widest text-lg outline-none focus:border-apex-accent"
                />
              </div>

              <div className="flex gap-2">
                <button 
                  type="button"
                  onClick={() => setStep('credentials')}
                  className="w-1/3 bg-apex-surface hover:bg-apex-surfaceHover border border-apex-border text-apex-muted font-bold py-3 rounded-btn transition-apex text-center font-mono cursor-pointer"
                >
                  ORQAGA
                </button>
                <button 
                  type="submit"
                  disabled={loading}
                  className="w-2/3 bg-apex-accent hover:bg-blue-600 disabled:opacity-50 text-white font-bold py-3 rounded-btn transition-apex flex items-center justify-center space-x-2 font-mono shadow-lg shadow-apex-accent/20 cursor-pointer"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  <span>TERMINALGA KIRISH</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      <div className="text-center font-mono text-[10px] text-apex-muted z-10">
        APEX INSTITUTIONAL OS v4.2.0 â€¢ 256-BIT ENCRYPTED QUANT TERMINAL
      </div>
    </div>
  );
};