import React, { useState } from 'react';
import { useTerminal } from '../../context/TerminalContext';
import { AuthService } from '../../services/authService';
import { 
  ShieldCheck, 
  KeyRound, 
  Lock, 
  User, 
  Server, 
  Wifi, 
  Database, 
  TrendingUp, 
  AlertTriangle, 
  UserCheck,
  Loader2,
  Terminal,
  Cpu
} from 'lucide-react';

export const AuthLogin: React.FC = () => {
  const { loginUser, tickers = [], health = {} as any } = useTerminal();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'credentials' | '2fa'>('credentials');
  const [twoFactorCode, setTwoFactorCode] = useState('');

  const safeTickers = Array.isArray(tickers) ? tickers : [];
  const btcTicker = safeTickers.find(t => t.symbol === 'BTC/USDT');
  const ethTicker = safeTickers.find(t => t.symbol === 'ETH/USDT');

  const btcPrice = btcTicker && btcTicker.price ? btcTicker.price.toLocaleString() : '78,869';
  const ethPrice = ethTicker && ethTicker.price ? ethTicker.price.toLocaleString() : '2,475';

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // First verify credentials against secure backend API
      const session = await AuthService.login(username, password, undefined, rememberMe ? 30 : 0);
      setStep('2fa');
      setLoading(false);
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'Kirish rad etildi. Foydalanuvchi nomi yoki parol noto\'g\'ri.');
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const session = await AuthService.login(username, password, twoFactorCode || '4079', rememberMe ? 30 : 0);
      loginUser(session.user, rememberMe ? 30 : 0);
    } catch (err: any) {
      setLoading(false);
      setError(err.message || '2FA xavfsizlik PIN kodi noto\'g\'ri.');
    }
  };

  return (
    <div className="min-h-screen w-screen bg-[#080A0D] text-[#F3F4F6] flex flex-col justify-between p-4 relative overflow-hidden font-sans select-none">
      {/* Background Ambience */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-600/5 rounded-full blur-3xl pointer-events-none" />

      {/* Top Header Bar */}
      <div className="w-full bg-[#0D1117] border border-[#222C3A] rounded-lg p-2.5 flex items-center justify-between font-mono text-xs z-10 shadow-sm">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 live-pulse-green" />
            <span className="font-bold text-white tracking-tight flex items-center gap-1.5 font-sans">
              <span>APEX QUANT</span>
              <span className="text-[9.5px] px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30 font-mono">GATEWAY</span>
            </span>
          </div>

          <div className="hidden sm:flex items-center space-x-4 border-l border-[#222C3A] pl-4">
            <div className="flex items-center space-x-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[#6B7280]">BTC:</span>
              <span className="font-bold text-emerald-400 font-mono tabular-nums">${btcPrice}</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[#6B7280]">ETH:</span>
              <span className="font-bold text-emerald-400 font-mono tabular-nums">${ethPrice}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-[10.5px] text-[#9CA3AF]">
          <span className="flex items-center gap-1"><Server className="w-3 h-3 text-[#6B7280]" /> VPS ({health?.vpsLatency || 12}ms)</span>
          <span className="flex items-center gap-1"><Wifi className="w-3 h-3 text-emerald-400" /> WS LIVE</span>
          <span className="flex items-center gap-1"><Cpu className="w-3 h-3 text-purple-400" /> AI ACTIVE</span>
        </div>
      </div>

      {/* Central Login Card */}
      <div className="w-full max-w-md mx-auto my-auto z-10 space-y-4">
        <div className="p-6 sm:p-8 space-y-6 shadow-2xl border border-[#222C3A] bg-[#0D1117]/95 backdrop-blur-xl rounded-xl">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-[#141A23] border border-blue-500/30 text-blue-400 mx-auto flex items-center justify-center shadow-lg shadow-blue-500/10">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white font-sans">APEX QUANT TERMINAL</h1>
            <p className="text-xs text-[#9CA3AF] font-mono">Institutional Owner Access Lock</p>
          </div>

          {error && (
            <div className="p-3 bg-rose-500/15 border border-rose-500/30 text-rose-400 rounded-lg text-xs flex items-center gap-2 font-mono">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {step === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-[#9CA3AF] mb-1.5 text-[10.5px] font-sans font-semibold">FOYDALANUVCHI NOMI (USERNAME)</label>
                <div className="relative">
                  <User className="w-4 h-4 text-[#6B7280] absolute left-3 top-2.5" />
                  <input 
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="tillo"
                    autoFocus
                    className="w-full bg-[#141A23] border border-[#222C3A] rounded-lg px-3 py-2.5 pl-9 text-white focus:border-blue-500 outline-none transition-apex text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#9CA3AF] mb-1.5 text-[10.5px] font-sans font-semibold">XAVFSIZLIK PAROLI (PASSWORD)</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#6B7280] absolute left-3 top-2.5" />
                  <input 
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••"
                    className="w-full bg-[#141A23] border border-[#222C3A] rounded-lg px-3 py-2.5 pl-9 text-white focus:border-blue-500 outline-none transition-apex text-xs font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between py-1">
                <label className="flex items-center space-x-2 cursor-pointer text-[#9CA3AF] hover:text-white transition-apex text-[11px] font-sans">
                  <input 
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-3.5 h-3.5 rounded bg-[#141A23] border-[#222C3A] text-blue-500 accent-blue-500 focus:ring-0 cursor-pointer"
                  />
                  <span>Tizimda 30 kun eslab qolinsin (Stay Logged In)</span>
                </label>
              </div>

              <button 
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold py-2.5 rounded-lg transition-apex flex items-center justify-center space-x-2 font-sans text-xs shadow-lg shadow-blue-500/20 cursor-pointer"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                <span>TASDIQLASH & KIRISH</span>
              </button>
            </form>
          ) : (
            <form onSubmit={handle2FASubmit} className="space-y-4 font-mono text-xs">
              <div className="bg-[#141A23] p-3.5 rounded-lg border border-[#222C3A] text-center space-y-1">
                <div className="text-emerald-400 font-bold flex items-center justify-center gap-1.5 text-xs font-sans">
                  <UserCheck className="w-4 h-4 text-emerald-400" /> TILLO PAROLI TASDIQLANDI
                </div>
                <div className="text-[10px] text-[#9CA3AF]">Xavfsizlik 2FA PIN kodini kiriting (yoki Enter bosing).</div>
              </div>

              <div>
                <label className="block text-[#9CA3AF] mb-1.5 text-[10.5px] font-sans font-semibold">2FA XAVFSIZLIK PIN (4079)</label>
                <input 
                  type="text"
                  maxLength={6}
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  placeholder="4079"
                  autoFocus
                  className="w-full bg-[#141A23] border border-blue-500/50 rounded-lg px-3 py-2.5 text-center text-blue-400 font-bold tracking-widest text-lg outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex gap-2">
                <button 
                  type="button"
                  onClick={() => setStep('credentials')}
                  className="w-1/3 bg-[#141A23] hover:bg-[#1A222E] border border-[#222C3A] text-[#9CA3AF] font-bold py-2.5 rounded-lg transition-apex text-center font-sans text-xs cursor-pointer"
                >
                  ORQAGA
                </button>
                <button 
                  type="submit"
                  disabled={loading}
                  className="w-2/3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold py-2.5 rounded-lg transition-apex flex items-center justify-center space-x-2 font-sans text-xs shadow-lg shadow-blue-500/20 cursor-pointer"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                  <span>TERMINALGA KIRISH</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Footer Security Note */}
      <div className="w-full text-center text-[#6B7280] font-mono text-[10px] z-10">
        APEX QUANT HFT PROPRIETARY ENGINE • STRICT SINGLE-OWNER ACCESS GATEWAY
      </div>
    </div>
  );
};

export default AuthLogin;
