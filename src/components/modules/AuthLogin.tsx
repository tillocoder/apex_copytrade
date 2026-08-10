import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import type { UserRole } from '../../types';
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
  UserCheck
} from 'lucide-react';

interface PredefinedAccount {
  email: string;
  pass: string;
  name: string;
  role: UserRole;
}

const ACCOUNTS: PredefinedAccount[] = [
  { email: 'tillo4079@gmail.com', pass: 'Acer#4079', name: 'Hikmatillo', role: 'Owner' },
  { email: 'apextraderhojiakber@gmail.com', pass: 'hojiakbar123', name: 'Hojiakbar', role: 'Trader' },
  { email: 'apextraderzafarbek@gmail.com', pass: 'Zafarbek2026!', name: 'Zafarbek', role: 'Quant Developer' }
];

export const AuthLogin: React.FC = () => {
  const { loginUser, tickers, health } = useTerminal();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'credentials' | '2fa'>('credentials');
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [matchedAccount, setMatchedAccount] = useState<PredefinedAccount | null>(null);

  const btcTicker = tickers.find(t => t.symbol === 'BTC/USDT');
  const ethTicker = tickers.find(t => t.symbol === 'ETH/USDT');

  const handleCredentialsSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const found = ACCOUNTS.find(a => a.email.trim().toLowerCase() === email.trim().toLowerCase() && a.pass === password);
    if (!found) {
      setError('Invalid email or password. Access Denied.');
      return;
    }

    setMatchedAccount(found);
    setStep('2fa');
  };

  const handle2FASubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!matchedAccount) return;

    loginUser({
      id: `usr_${Date.now()}`,
      name: matchedAccount.name,
      email: matchedAccount.email,
      role: matchedAccount.role,
      avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=250&q=80',
      twoFactorEnabled: true,
      passkeyRegistered: true
    }, rememberMe ? 7 : 0);
  };

  return (
    <div className="min-h-screen bg-apex-bg text-apex-text flex flex-col justify-between p-4 relative overflow-hidden font-sans select-none">
      {/* Top Banner */}
      <div className="w-full bg-apex-bgSecondary border border-apex-border rounded-panel p-2.5 flex items-center justify-between font-mono text-xs z-10">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-apex-accent animate-pulse" />
            <span className="font-bold text-apex-text">APEX QUANT GATEWAY</span>
          </div>

          <div className="hidden sm:flex items-center space-x-4 border-l border-apex-border pl-4">
            <div className="flex items-center space-x-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-apex-success" />
              <span className="text-apex-muted">BTC:</span>
              <span className="font-bold text-apex-success">${btcTicker?.price.toLocaleString()}</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-apex-success" />
              <span className="text-apex-muted">ETH:</span>
              <span className="font-bold text-apex-success">${ethTicker?.price.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-[11px] text-apex-muted">
          <span className="flex items-center gap-1"><Server className="w-3 h-3 text-apex-muted" /> VPS ({health.vpsLatency}ms)</span>
          <span className="flex items-center gap-1"><Wifi className="w-3 h-3 text-apex-muted" /> WS ({health.wsLatency}ms)</span>
          <span className="flex items-center gap-1"><Database className="w-3 h-3 text-apex-muted" /> DB ({health.dbLatency}ms)</span>
        </div>
      </div>

      {/* Central Login Card */}
      <div className="w-full max-w-md mx-auto my-auto z-10 space-y-4">
        <div className="workstation-panel p-6 space-y-5">
          <div className="text-center space-y-2">
            <div className="w-10 h-10 rounded-md bg-apex-surface border border-apex-border text-apex-accent mx-auto flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h1 className="text-lg font-bold tracking-tight text-apex-text font-mono">APEX QUANT TERMINAL</h1>
            <p className="text-xs text-apex-muted font-mono">Institutional Access Control</p>
          </div>

          {error && (
            <div className="p-3 bg-apex-danger/15 border border-apex-danger text-apex-danger rounded-panel text-xs flex items-center gap-2 font-mono">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {step === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-apex-muted mb-1 text-[11px]">ACCOUNT EMAIL</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-apex-muted absolute left-3 top-2.5" />
                  <input 
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@gmail.com"
                    className="w-full bg-apex-bg border border-apex-border rounded-btn px-3 py-2 pl-9 text-apex-text focus:border-apex-accent outline-none transition-apex"
                  />
                </div>
              </div>

              <div>
                <label className="block text-apex-muted mb-1 text-[11px]">PASSWORD</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-apex-muted absolute left-3 top-2.5" />
                  <input 
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-apex-bg border border-apex-border rounded-btn px-3 py-2 pl-9 text-apex-text focus:border-apex-accent outline-none transition-apex"
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
                  <span>Tizimda 7 kun eslab qolinsin (7-Day Session)</span>
                </label>
              </div>

              <button 
                type="submit"
                className="w-full bg-apex-surface hover:bg-apex-hover border border-apex-accent text-apex-accent font-bold py-2.5 rounded-btn transition-apex flex items-center justify-center space-x-2 font-mono"
              >
                <KeyRound className="w-4 h-4" />
                <span>VERIFY CREDENTIALS & 2FA</span>
              </button>
            </form>
          ) : (
            <form onSubmit={handle2FASubmit} className="space-y-4 font-mono text-xs">
              <div className="bg-apex-surface p-3 rounded-panel border border-apex-border text-center space-y-1">
                <div className="text-apex-accent font-bold flex items-center justify-center gap-1.5 text-sm">
                  <UserCheck className="w-4 h-4 text-apex-accent" /> WELCOME, {matchedAccount?.name.toUpperCase()} ({matchedAccount?.role})
                </div>
                <div className="text-[10px] text-apex-muted">Enter 6-digit TOTP code or press Sign In to proceed.</div>
              </div>

              <div>
                <label className="block text-apex-muted mb-1 text-[11px]">2FA TOTP CODE</label>
                <input 
                  type="text"
                  maxLength={6}
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  placeholder="849204"
                  className="w-full bg-apex-bg border border-apex-border rounded-btn px-3 py-2 text-center text-apex-accent font-bold tracking-widest text-base outline-none focus:border-apex-accent"
                />
              </div>

              <button 
                type="submit"
                className="w-full bg-apex-accent hover:bg-blue-600 text-white font-bold py-2.5 rounded-btn transition-apex text-center font-mono shadow-subtle"
              >
                AUTHENTICATE & ENTER TERMINAL
              </button>
            </form>
          )}
        </div>
      </div>

      <div className="text-center font-mono text-[10px] text-apex-muted z-10">
        APEX QUANT OS v4.2.0 • 256-BIT AES ENCRYPTED GATEWAY
      </div>
    </div>
  );
};
