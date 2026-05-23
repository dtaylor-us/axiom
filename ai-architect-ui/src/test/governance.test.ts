import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getTradeOffs,
  getAdl,
  getAdlHard,
  getAdlByCategory,
  getWeaknesses,
  getFmea,
} from '../api/governance';

function mockFetch(data: unknown) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    headers: { get: () => 'application/json' },
    json: async () => data,
  } as unknown as Response);
}

describe('governance API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('getTradeOffs_fetchesCorrectEndpoint', async () => {
    mockFetch([{ id: 'T-1' }]);
    const result = await getTradeOffs('s1', 'jwt');
    expect(result).toEqual([{ id: 'T-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/trade-offs',
      expect.objectContaining({ headers: { Authorization: 'Bearer jwt' } }),
    );
  });

  it('getAdl_fetchesCorrectEndpoint', async () => {
    mockFetch({ document: 'doc', rules: [] });
    const result = await getAdl('s1', 'jwt');
    expect(result.document).toBe('doc');
  });

  it('getAdlHard_fetchesHardEndpoint', async () => {
    mockFetch({ document: 'hard', rules: [] });
    const result = await getAdlHard('s1', 'jwt');
    expect(result.document).toBe('hard');
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/adl/hard',
      expect.any(Object),
    );
  });

  it('getAdlByCategory_fetchesCategoryEndpoint', async () => {
    mockFetch({ document: 'cat', rules: [] });
    const result = await getAdlByCategory('s1', 'security', 'jwt');
    expect(result.document).toBe('cat');
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/adl/security',
      expect.any(Object),
    );
  });

  it('getWeaknesses_fetchesCorrectEndpoint', async () => {
    mockFetch({ weaknesses: [], summary: 'ok' });
    const result = await getWeaknesses('s1', 'jwt');
    expect(result.summary).toBe('ok');
  });

  it('getFmea_fetchesCorrectEndpoint', async () => {
    mockFetch([{ id: 'F-1' }]);
    const result = await getFmea('s1', 'jwt');
    expect(result).toEqual([{ id: 'F-1' }]);
  });

  it('throwsOnNonOkResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      headers: { get: () => null },
    } as unknown as Response);
    await expect(getTradeOffs('s1', 'jwt')).rejects.toThrow('500');
  });
});
