import type { AuthTokenResponse } from '../types/api';

import { AUTH_BASE } from './config';

const BASE = AUTH_BASE;
const DEFAULT_NETWORK_ERROR = 'Network request failed. Please try again.';

type PasswordResetErrorField = 'newPassword' | 'confirmPassword' | 'form';

/**
 * Raised when the public reset-link request is throttled.
 */
export class RateLimitError extends Error {}

/**
 * Raised when a reset token is expired, invalid, or already consumed.
 */
export class ExpiredTokenError extends Error {}

/**
 * Raised when the reset API rejects the submitted password fields.
 */
export class PasswordResetValidationError extends Error {
  readonly field: PasswordResetErrorField;
  readonly code?: string;

  constructor(
    message: string,
    field: PasswordResetErrorField = 'form',
    code?: string,
  ) {
    super(message);
    this.name = 'PasswordResetValidationError';
    this.field = field;
    this.code = code;
  }
}

/**
 * Raised when a public auth request cannot reach the backend.
 */
export class NetworkError extends Error {}

async function readJsonBody(res: Response): Promise<Record<string, unknown>> {
  return res.json().catch(() => ({}));
}

function resolveErrorMessage(
  body: Record<string, unknown>,
  fallback: string,
): string {
  const detail = typeof body.detail === 'string' ? body.detail : null;
  const message = typeof body.message === 'string' ? body.message : null;
  return detail ?? message ?? fallback;
}

function normalizeNetworkError(err: unknown, fallback: string): never {
  if (err instanceof NetworkError) {
    throw err;
  }
  throw new NetworkError(fallback);
}

function classifyPasswordResetField(
  code: string | undefined,
  message: string,
): PasswordResetErrorField {
  if (code === 'password_mismatch') {
    return 'confirmPassword';
  }
  if (code === 'password_invalid') {
    return 'newPassword';
  }
  return message.toLowerCase().includes('password') ? 'newPassword' : 'form';
}

/** Quick auto-auth by username (guest mode) */
export async function getToken(username: string): Promise<string> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    });
  } catch (err) {
    normalizeNetworkError(err, DEFAULT_NETWORK_ERROR);
  }
  if (!res.ok) {
    throw new Error(`Auth failed: ${res.status}`);
  }
  const data: AuthTokenResponse = await res.json();
  return data.token;
}

/** Register a new account */
export async function register(
  email: string,
  password: string,
  name: string,
): Promise<AuthTokenResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    });
  } catch (err) {
    normalizeNetworkError(err, DEFAULT_NETWORK_ERROR);
  }
  if (!res.ok) {
    const body = await readJsonBody(res);
    throw new Error(
      resolveErrorMessage(body, `Registration failed: ${res.status}`),
    );
  }
  return res.json();
}

/** Login with email & password */
export async function login(
  email: string,
  password: string,
): Promise<AuthTokenResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    normalizeNetworkError(err, DEFAULT_NETWORK_ERROR);
  }
  if (!res.ok) {
    const body = await readJsonBody(res);
    throw new Error(
      resolveErrorMessage(body, `Login failed: ${res.status}`),
    );
  }
  return res.json();
}

/**
 * Requests a time-bounded password-reset link for the supplied email address.
 */
export async function requestPasswordReset(
  email: string,
): Promise<{ message: string }> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
  } catch (err) {
    normalizeNetworkError(
      err,
      'Unable to send a reset link right now. Please try again.',
    );
  }

  if (res.status === 429) {
    const body = await readJsonBody(res);
    throw new RateLimitError(
      resolveErrorMessage(body, 'Too many requests. Please wait before trying again.'),
    );
  }

  if (!res.ok) {
    const body = await readJsonBody(res);
    throw new Error(resolveErrorMessage(body, 'Request failed.'));
  }

  return res.json();
}

/**
 * Checks whether a password-reset token is still valid without consuming it.
 */
export async function validateResetToken(
  token: string,
): Promise<{ valid: boolean; message?: string }> {
  let res: Response;
  try {
    res = await fetch(
      `${BASE}/reset-password/validate?token=${encodeURIComponent(token)}`,
    );
  } catch (err) {
    normalizeNetworkError(
      err,
      'Unable to validate the reset link. Please try again.',
    );
  }

  if (res.status === 410) {
    const body = await readJsonBody(res);
    return {
      valid: false,
      message: resolveErrorMessage(
        body,
        'This reset link has expired or has already been used.',
      ),
    };
  }

  if (!res.ok) {
    const body = await readJsonBody(res);
    throw new Error(resolveErrorMessage(body, 'Validation failed.'));
  }

  return res.json();
}

/**
 * Submits a new password for a validated reset token.
 */
export async function confirmPasswordReset(
  token: string,
  newPassword: string,
  confirmPassword: string,
): Promise<{ message: string }> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, newPassword, confirmPassword }),
    });
  } catch (err) {
    normalizeNetworkError(
      err,
      'Unable to reset your password right now. Please try again.',
    );
  }

  if (res.status === 410) {
    const body = await readJsonBody(res);
    throw new ExpiredTokenError(
      resolveErrorMessage(
        body,
        'This reset link has expired or has already been used.',
      ),
    );
  }

  if (res.status === 400) {
    const body = await readJsonBody(res);
    const code =
      typeof body.error === 'string' ? body.error : undefined;
    const message = resolveErrorMessage(body, 'Reset failed.');
    throw new PasswordResetValidationError(
      message,
      classifyPasswordResetField(code, message),
      code,
    );
  }

  if (!res.ok) {
    const body = await readJsonBody(res);
    throw new Error(resolveErrorMessage(body, 'Reset failed.'));
  }

  return res.json();
}
