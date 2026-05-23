import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  ExpiredTokenError,
  PasswordResetValidationError,
  RateLimitError,
  confirmPasswordReset,
  getToken,
  login,
  register,
  requestPasswordReset,
  validateResetToken,
} from '../api/auth';

describe('getToken', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sendsPostRequestAndReturnsToken', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ token: 'jwt-123' }),
    } as unknown as Response);

    const token = await getToken('alice');
    expect(token).toBe('jwt-123');
    expect(fetch).toHaveBeenCalledWith('/api/v1/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'alice' }),
    });
  });

  it('throwsOnNonOkResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
    } as unknown as Response);

    await expect(getToken('bad')).rejects.toThrow('Auth failed: 401');
  });
});

describe('register', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sendsRegisterRequestAndReturnsResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ token: 'jwt-reg', email: 'a@b.com' }),
    } as unknown as Response);

    const res = await register('a@b.com', 'password1234', 'Alice');
    expect(res).toEqual({ token: 'jwt-reg', email: 'a@b.com' });
    expect(fetch).toHaveBeenCalledWith('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'a@b.com', password: 'password1234', name: 'Alice' }),
    });
  });

  it('throwsOnConflict', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Email already registered' }),
    } as unknown as Response);

    await expect(register('dup@b.com', 'pw123456789', 'Dup')).rejects.toThrow('Email already registered');
  });
});

describe('login', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sendsLoginRequestAndReturnsResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ token: 'jwt-login', email: 'a@b.com' }),
    } as unknown as Response);

    const res = await login('a@b.com', 'password1234');
    expect(res).toEqual({ token: 'jwt-login', email: 'a@b.com' });
  });

  it('throwsOnInvalidCredentials', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid credentials' }),
    } as unknown as Response);

    await expect(login('a@b.com', 'wrong')).rejects.toThrow('Invalid credentials');
  });
});

describe('requestPasswordReset', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('postsResetRequestAndReturnsMessage', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: 'sent' }),
    } as unknown as Response);

    const res = await requestPasswordReset('a@b.com');

    expect(res).toEqual({ message: 'sent' });
    expect(fetch).toHaveBeenCalledWith('/api/v1/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'a@b.com' }),
    });
  });

  it('throwsRateLimitErrorOn429', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ message: 'Too many requests. Please wait before trying again.' }),
    } as unknown as Response);

    await expect(requestPasswordReset('a@b.com')).rejects.toBeInstanceOf(RateLimitError);
  });
});

describe('validateResetToken', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returnsValidityPayloadForExpiredToken', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 410,
      json: async () => ({ valid: false, message: 'expired' }),
    } as unknown as Response);

    const res = await validateResetToken('token-value');

    expect(res).toEqual({ valid: false, message: 'expired' });
  });
});

describe('confirmPasswordReset', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('postsResetConfirmationAndReturnsMessage', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: 'updated' }),
    } as unknown as Response);

    const res = await confirmPasswordReset('token-value', 'Password12345', 'Password12345');

    expect(res).toEqual({ message: 'updated' });
    expect(fetch).toHaveBeenCalledWith('/api/v1/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: 'token-value',
        newPassword: 'Password12345',
        confirmPassword: 'Password12345',
      }),
    });
  });

  it('throwsExpiredTokenErrorOn410', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 410,
      json: async () => ({ message: 'expired' }),
    } as unknown as Response);

    await expect(
      confirmPasswordReset('token-value', 'Password12345', 'Password12345'),
    ).rejects.toBeInstanceOf(ExpiredTokenError);
  });

  it('throwsPasswordResetValidationErrorOn400', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: 'password_mismatch', message: 'Passwords do not match.' }),
    } as unknown as Response);

    await expect(
      confirmPasswordReset('token-value', 'Password12345', 'Mismatch12345'),
    ).rejects.toBeInstanceOf(PasswordResetValidationError);
  });
});
