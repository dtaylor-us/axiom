import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import {
  ExpiredTokenError,
  NetworkError,
  PasswordResetValidationError,
  confirmPasswordReset,
  validateResetToken,
} from '../api/auth';

const MIN_PASSWORD_LENGTH = 12;

type ValidationState = 'loading' | 'valid' | 'expired' | 'error';

function passwordStrengthLabel(password: string): 'Too short' | 'Weak' | 'Fair' | 'Strong' {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return 'Too short';
  }

  let score = 0;
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score >= 4 && password.length >= 16) {
    return 'Strong';
  }
  if (score >= 3) {
    return 'Fair';
  }
  return 'Weak';
}

/**
 * Public password-reset completion screen.
 *
 * It validates the emailed token before rendering the form so expired or
 * already-consumed links never show a password entry UI.
 */
export function ResetPasswordView() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token')?.trim() ?? '';
  const [validationState, setValidationState] = useState<ValidationState>('loading');
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [newPasswordError, setNewPasswordError] = useState<string | null>(null);
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const strength = useMemo(
    () => passwordStrengthLabel(newPassword),
    [newPassword],
  );
  const passwordsMatch = newPassword === confirmPassword;
  const canSubmit =
    newPassword.length >= MIN_PASSWORD_LENGTH &&
    confirmPassword.length >= MIN_PASSWORD_LENGTH &&
    passwordsMatch &&
    !submitting;

  const validateCurrentToken = async () => {
    if (!token) {
      setValidationState('expired');
      setValidationMessage(
        'Password reset links expire after 30 minutes and can only be used once.',
      );
      return;
    }

    setValidationState('loading');
    setValidationMessage(null);
    try {
      const result = await validateResetToken(token);
      if (result.valid) {
        setValidationState('valid');
        return;
      }
      setValidationState('expired');
      setValidationMessage(
        result.message ??
          'Password reset links expire after 30 minutes and can only be used once.',
      );
    } catch (err) {
      setValidationState('error');
      setValidationMessage((err as Error).message);
    }
  };

  useEffect(() => {
    // Intentional fire-and-forget token validation on mount.
    void validateCurrentToken();
  }, [token]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setNewPasswordError(null);
    setConfirmPasswordError(null);
    setFormError(null);

    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setNewPasswordError(
        `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`,
      );
      return;
    }

    if (!passwordsMatch) {
      setConfirmPasswordError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await confirmPasswordReset(token, newPassword, confirmPassword);
      setSubmitted(true);
    } catch (err) {
      if (err instanceof ExpiredTokenError) {
        setValidationState('expired');
        setValidationMessage(err.message);
      } else if (err instanceof PasswordResetValidationError) {
        if (err.field === 'newPassword') {
          setNewPasswordError(err.message);
        } else if (err.field === 'confirmPassword') {
          setConfirmPasswordError(err.message);
        } else {
          setFormError(err.message);
        }
      } else if (err instanceof NetworkError) {
        setFormError(err.message);
      } else {
        setFormError((err as Error).message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div
        className="flex items-center justify-center min-h-full bg-gray-50"
        data-testid="reset-password-view"
      >
        <div className="w-full max-w-sm mx-4">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
            <div>
              <h1 className="text-2xl font-semibold text-gray-800">Password updated</h1>
              <p className="text-sm text-gray-600 mt-2">
                Your password has been changed. You can now sign in with your new password.
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="w-full bg-accent text-white rounded-lg py-2.5 text-sm font-medium hover:bg-accent-hover transition-colors"
              data-testid="reset-password-sign-in"
            >
              Sign in
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (validationState === 'loading') {
    return (
      <div
        className="flex items-center justify-center min-h-full bg-gray-50"
        data-testid="reset-password-view"
      >
        <div className="w-full max-w-sm mx-4 bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <svg
              className="w-4 h-4 animate-spin text-accent shrink-0"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
              <path d="M8 2a6 6 0 0 1 6 6" />
            </svg>
            Validating your reset link…
          </div>
        </div>
      </div>
    );
  }

  if (validationState === 'expired') {
    return (
      <div
        className="flex items-center justify-center min-h-full bg-gray-50"
        data-testid="reset-password-view"
      >
        <div className="w-full max-w-sm mx-4">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
            <div>
              <h1 className="text-2xl font-semibold text-gray-800">This link has expired</h1>
              <p className="text-sm text-gray-600 mt-2">
                {validationMessage ??
                  'Password reset links expire after 30 minutes and can only be used once.'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/forgot-password')}
              className="w-full bg-accent text-white rounded-lg py-2.5 text-sm font-medium hover:bg-accent-hover transition-colors"
              data-testid="reset-password-request-new-link"
            >
              Request a new link
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (validationState === 'error') {
    return (
      <div
        className="flex items-center justify-center min-h-full bg-gray-50"
        data-testid="reset-password-view"
      >
        <div className="w-full max-w-sm mx-4">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
            <div>
              <h1 className="text-2xl font-semibold text-gray-800">Unable to verify link</h1>
              <p className="text-sm text-gray-600 mt-2">
                {validationMessage ?? 'Please try again.'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                void validateCurrentToken();
              }}
              className="w-full border border-gray-200 rounded-lg py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors"
              data-testid="reset-password-retry-validate"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex items-center justify-center min-h-full bg-gray-50"
      data-testid="reset-password-view"
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
          <h1 className="text-2xl font-semibold text-gray-800">Set a new password</h1>
          <p className="text-sm text-gray-500 mt-1">
            Choose a new password for your Archon account.
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="new-password"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                New password
              </label>
              <input
                id="new-password"
                type="password"
                required
                minLength={MIN_PASSWORD_LENGTH}
                value={newPassword}
                onChange={(e) => {
                  setNewPassword(e.target.value);
                  if (newPasswordError) {
                    setNewPasswordError(null);
                  }
                }}
                placeholder="New password (min. 12 characters)"
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                data-testid="reset-password-new"
              />
              <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                <div className="flex items-center gap-1 flex-1">
                  {[0, 1, 2].map((idx) => {
                    const activeCount =
                      strength === 'Strong' ? 3 : strength === 'Fair' ? 2 : strength === 'Weak' ? 1 : 0;
                    return (
                      <span
                        key={idx}
                        className={`h-1.5 flex-1 rounded-full ${
                          idx < activeCount ? 'bg-accent' : 'bg-gray-200'
                        }`}
                      />
                    );
                  })}
                </div>
                <span>{strength}</span>
              </div>
              {newPasswordError && (
                <p
                  className="mt-2 text-xs text-red-700"
                  data-testid="reset-password-new-error"
                >
                  {newPasswordError}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="confirm-password"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Confirm password
              </label>
              <input
                id="confirm-password"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (confirmPasswordError) {
                    setConfirmPasswordError(null);
                  }
                }}
                placeholder="Confirm new password"
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                data-testid="reset-password-confirm"
              />
              {!confirmPasswordError &&
                confirmPassword.length > 0 &&
                !passwordsMatch && (
                  <p className="mt-2 text-xs text-red-700">
                    Passwords do not match.
                  </p>
                )}
              {confirmPasswordError && (
                <p
                  className="mt-2 text-xs text-red-700"
                  data-testid="reset-password-confirm-error"
                >
                  {confirmPasswordError}
                </p>
              )}
            </div>

            {formError && (
              <div
                className="flex items-start gap-2 bg-red-50 border border-red-100 rounded-lg px-3 py-2.5"
                data-testid="reset-password-form-error"
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
                <p className="text-xs text-red-700">{formError}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full bg-accent text-white rounded-lg py-2.5 text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors inline-flex items-center justify-center gap-2"
              data-testid="reset-password-submit"
            >
              {submitting && (
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
              {submitting ? 'Updating…' : 'Set new password'}
            </button>
          </form>
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
