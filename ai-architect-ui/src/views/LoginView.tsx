import { useState } from 'react';
import type { FormEvent } from 'react';
import { getToken, login, register } from '../api/auth';
import { useAuth } from '../hooks/useAuth';

type AuthMode = 'login' | 'register';

export function LoginView() {
  const { setAuth } = useAuth();
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === 'register') {
        const res = await register(email, password, name);
        setAuth(res.token, res.email ?? (name || email));
      } else {
        const res = await login(email, password);
        setAuth(res.token, res.email ?? email);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = async () => {
    setError(null);
    setLoading(true);
    try {
      const token = await getToken('Guest');
      setAuth(token, 'Guest');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full bg-gray-50" data-testid="login-view">
      <div className="w-full max-w-sm mx-4">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto bg-accent/90 rounded-2xl flex items-center justify-center shadow-sm mb-4">
            <svg className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 21h18M3 10h18M12 3l9 7H3l9-7zM5 10v11m4-11v11m4-11v11m4-11v11" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-gray-800">Archon</h1>
          <p className="text-sm text-gray-500 mt-1">
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label htmlFor="name" className="block text-xs font-medium text-gray-600 mb-1">
                  Name
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                  data-testid="auth-name"
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-medium text-gray-600 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                data-testid="auth-email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-gray-600 mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === 'register' ? 'Min 8 characters' : '••••••••'}
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                data-testid="auth-password"
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-100 rounded-lg px-3 py-2.5" data-testid="auth-error">
                <svg className="w-4 h-4 text-red-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-xs text-red-700">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent text-white rounded-lg py-2.5 text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors"
              data-testid="auth-submit"
            >
              {loading
                ? 'Please wait…'
                : mode === 'login'
                  ? 'Sign in'
                  : 'Create account'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white px-2 text-gray-400">or</span>
            </div>
          </div>

          {/* Guest access */}
          <button
            onClick={handleGuest}
            disabled={loading}
            className="w-full border border-gray-200 rounded-lg py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-50 transition-colors"
            data-testid="auth-guest"
          >
            Continue as Guest
          </button>
        </div>

        {/* Toggle mode */}
        <p className="text-center text-xs text-gray-500 mt-4">
          {mode === 'login' ? (
            <>
              Don&apos;t have an account?{' '}
              <button
                onClick={() => { setMode('register'); setError(null); }}
                className="text-accent hover:underline font-medium"
                data-testid="auth-toggle"
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                onClick={() => { setMode('login'); setError(null); }}
                className="text-accent hover:underline font-medium"
                data-testid="auth-toggle"
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
