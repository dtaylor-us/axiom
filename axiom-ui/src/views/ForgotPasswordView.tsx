import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';

import {
  NetworkError,
  RateLimitError,
  requestPasswordReset,
} from '../api/auth';

const RESET_LINK_MESSAGE =
  'If an account exists for this address, a reset link has been sent. The link expires in 30 minutes.';

/**
 * Public password-reset request screen.
 *
 * Users submit an email address and always receive the same success copy to
 * avoid leaking whether an account exists.
 */
export function ForgotPasswordView() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<'network' | 'rate-limit' | 'generic' | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setErrorKind(null);
    setLoading(true);
    try {
      await requestPasswordReset(email);
      setSubmitted(true);
    } catch (err) {
      if (err instanceof RateLimitError) {
        setError(err.message);
        setErrorKind('rate-limit');
      } else if (err instanceof NetworkError) {
        setError(err.message);
        setErrorKind('network');
      } else {
        setError((err as Error).message);
        setErrorKind('generic');
      }
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSubmitted(false);
    setError(null);
    setErrorKind(null);
  };

  return (
    <div
      className="flex items-center justify-center min-h-full bg-gray-50"
      data-testid="forgot-password-view"
    >
      <div className="w-full max-w-sm mx-4">
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto bg-accent/90 rounded-2xl flex items-center justify-center shadow-sm mb-4">
            <svg
              className="w-7 h-7 text-white"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 17v.01M7 10V8a5 5 0 1110 0v2M5 10h14v9H5z" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-gray-800">Forgot password</h1>
          <p className="text-sm text-gray-500 mt-1">
            Request a time-limited link to set a new password.
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          {submitted ? (
            <div className="space-y-4" data-testid="forgot-password-success">
              <div>
                <h2 className="text-lg font-semibold text-gray-800">Check your email</h2>
                <p className="text-sm text-gray-600 mt-2">
                  {RESET_LINK_MESSAGE}
                </p>
              </div>

              <p className="text-sm text-gray-500">
                Didn&apos;t receive it? Check your spam folder, or request another link.
              </p>

              <button
                type="button"
                onClick={resetForm}
                className="w-full border border-gray-200 rounded-lg py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors"
                data-testid="forgot-password-reset"
              >
                Request another link
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="forgot-email"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Email address
                </label>
                <input
                  id="forgot-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                  data-testid="forgot-password-email"
                />
              </div>

              {error && (
                <div
                  className="flex items-start gap-2 bg-red-50 border border-red-100 rounded-lg px-3 py-2.5"
                  data-testid="forgot-password-error"
                >
                  <svg
                    className="w-4 h-4 text-red-500 mt-0.5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-red-700">{error}</p>
                    {errorKind === 'network' && (
                      <button
                        type="submit"
                        disabled={loading || !email.trim()}
                        className="mt-2 text-xs font-medium text-red-700 underline hover:text-red-800 disabled:opacity-50"
                        data-testid="forgot-password-retry"
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-accent text-white rounded-lg py-2.5 text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors inline-flex items-center justify-center gap-2"
                data-testid="forgot-password-submit"
              >
                {loading && (
                  <svg
                    className="w-4 h-4 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="12" cy="12" r="9" strokeOpacity="0.25" />
                    <path d="M12 3a9 9 0 019 9" />
                  </svg>
                )}
                {loading ? 'Sending…' : 'Send reset link'}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-gray-500 mt-4">
          <Link className="text-accent hover:underline font-medium" to="/login">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
