import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getToken, register, login } from '../api/auth';

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

    const res = await register('a@b.com', 'password1', 'Alice');
    expect(res).toEqual({ token: 'jwt-reg', email: 'a@b.com' });
    expect(fetch).toHaveBeenCalledWith('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'a@b.com', password: 'password1', name: 'Alice' }),
    });
  });

  it('throwsOnConflict', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Email already registered' }),
    } as unknown as Response);

    await expect(register('dup@b.com', 'pw123456', 'Dup')).rejects.toThrow('Email already registered');
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

    const res = await login('a@b.com', 'password1');
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
