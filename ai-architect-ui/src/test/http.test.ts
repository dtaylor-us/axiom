import { describe, it, expect, vi, beforeEach } from 'vitest';
import { authFetchJson, ApiError } from '../api/http';

describe('authFetchJson', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returnsJsonOnSuccess', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'abc' }),
    } as unknown as Response);

    const result = await authFetchJson<{ id: string }>('/api/resource', 'tok');
    expect(result).toEqual({ id: 'abc' });
  });

  it('throwsApiErrorOnNetworkFailure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'));

    await expect(authFetchJson('/api/resource', 'tok')).rejects.toThrow(ApiError);
  });

  it('throwsApiErrorWithStatusOnHttpError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(403);
  });

  it('dispatchesSessionExpiredEventOn401', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
      headers: { get: () => null },
    } as unknown as Response);

    const dispatched = vi.spyOn(window, 'dispatchEvent');

    await authFetchJson('/api/resource', 'tok').catch(() => {});

    const expiredEvent = dispatched.mock.calls.find(
      ([e]) => (e as CustomEvent).type === 'archon:session-expired',
    );
    expect(expiredEvent).toBeDefined();
  });

  it('parsesProblemDetailFromJsonResponseBody', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 422,
      headers: { get: () => 'application/problem+json' },
      json: async () => ({ detail: 'Validation failed', title: 'Bad input' }),
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toBe('Validation failed');
  });

  it('usesDefaultMessageForUnknownStatus', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 418,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/418/);
  });

  it('uses503MessageForServiceUnavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 503,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/temporarily unavailable/);
  });

  it('uses400MessageForBadRequest', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 400,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/invalid/i);
  });

  it('uses408MessageForTimeout', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 408,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/timed out/i);
  });

  it('uses429MessageForRateLimit', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 429,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/many requests/i);
  });

  it('uses409MessageForConflict', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 409,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/conflict/i);
  });

  it('uses502MessageForBadGateway', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 502,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/temporarily unreachable/i);
  });

  it('uses504MessageForGatewayTimeout', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 504,
      headers: { get: () => null },
    } as unknown as Response);

    const err = await authFetchJson('/api/resource', 'tok').catch((e) => e);
    expect(err.message).toMatch(/took too long/i);
  });
});
