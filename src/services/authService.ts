import type { User } from '../types';

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  user: User;
  expiresAt: number;
}

const TOKEN_STORAGE_KEY = 'apex_auth_session';

export class AuthService {
  static getStoredSession(): AuthSession | null {
    try {
      const raw = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (!raw) return null;
      const session = JSON.parse(raw) as AuthSession;
      if (!session || !session.accessToken || !session.user) {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        return null;
      }
      return session;
    } catch {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      return null;
    }
  }

  static async login(usernameOrEmail: string, pass: string, twoFactor?: string, rememberDays: number = 30): Promise<AuthSession> {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: usernameOrEmail.trim().toLowerCase(),
        password: pass,
        two_factor_code: twoFactor || null,
        remember_me: rememberDays > 0
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Kirish rad etildi' }));
      throw new Error(err.detail || 'Kirish rad etildi: Faqat vakolatli egasi (tillo) kira oladi.');
    }

    const data = await res.json();
    const session: AuthSession = {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
      expiresAt: Date.now() + (rememberDays > 0 ? rememberDays : 30) * 86400 * 1000
    };

    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(session));
    return session;
  }

  static async verifySession(): Promise<User | null> {
    const session = this.getStoredSession();
    if (!session) return null;

    try {
      const res = await fetch('/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${session.accessToken}` }
      });

      if (res.ok) {
        const user = await res.json();
        session.user = user;
        localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(session));
        return user;
      }

      // If access token expired, attempt refresh
      if (session.refreshToken) {
        const refreshRes = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: session.refreshToken })
        });

        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          session.accessToken = refreshData.access_token;
          localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(session));
          return session.user;
        }
      }

      this.logout();
      return null;
    } catch {
      if (session.expiresAt && Date.now() < session.expiresAt && session.user.role !== 'Guest') {
        return session.user;
      }
      this.logout();
      return null;
    }
  }

  static logout() {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {}
  }
}
