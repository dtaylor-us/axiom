import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listSessions, getSessionMessages } from '../api/sessions';

function mockFetch(data: unknown) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    headers: { get: () => 'application/json' },
    json: async () => data,
  } as unknown as Response);
}

describe('sessions API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('listSessions_fetchesSessionsEndpoint', async () => {
    mockFetch([{ sessionId: 'abc', title: 'My session' }]);

    const result = await listSessions('jwt-token');

    expect(result).toEqual([{ sessionId: 'abc', title: 'My session' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt-token',
          'X-Axiom-User-Id': 'guest',
        }),
      }),
    );
  });

  it('listSessions_returnsEmptyArrayWhenNoSessions', async () => {
    mockFetch([]);

    const result = await listSessions('jwt-token');

    expect(result).toEqual([]);
  });

  it('getSessionMessages_fetchesMessagesForSession', async () => {
    mockFetch([{ role: 'user', content: 'hello' }]);

    const result = await getSessionMessages('session-42', 'jwt-token');

    expect(result).toEqual([{ role: 'user', content: 'hello' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/session-42/messages',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt-token',
          'X-Axiom-User-Id': 'guest',
        }),
      }),
    );
  });

  it('getSessionMessages_throwsOnHttpError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
      headers: { get: () => null },
    } as unknown as Response);

    await expect(getSessionMessages('session-42', 'bad-token')).rejects.toThrow();
  });
});
