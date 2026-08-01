import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getTradeOffs,
  getAdl,
  getAdlHard,
  getAdlByCategory,
  getWeaknesses,
  getFmea,
  getFmeaRisks,
  getGovernanceReport,
  getTactics,
  getTacticsSummary,
  getBuyVsBuildSummary,
  getBuyVsBuildConflicts,
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
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt',
          'X-Axiom-User-Id': 'guest',
        }),
      }),
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
    await expect(getTradeOffs('s1', 'jwt')).rejects.toThrow(
      'Something went wrong on the server. Please try again.',
    );
  });

  it('getFmeaRisks_fetchesCorrectEndpoint', async () => {
    mockFetch([{ id: 'R-1' }]);
    const result = await getFmeaRisks('s1', 'jwt');
    expect(result).toEqual([{ id: 'R-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/fmea-risks',
      expect.any(Object),
    );
  });

  it('getGovernanceReport_fetchesCorrectEndpoint', async () => {
    mockFetch({ score: 85, summary: 'good' });
    const result = await getGovernanceReport('s1', 'jwt');
    expect((result as unknown as { score: number }).score).toBe(85);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/governance',
      expect.any(Object),
    );
  });

  it('getTactics_fetchesWithNoParams', async () => {
    mockFetch([{ id: 'TAC-1' }]);
    const result = await getTactics('s1', 'jwt');
    expect(result).toEqual([{ id: 'TAC-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/tactics',
      expect.any(Object),
    );
  });

  it('getTactics_appendsQueryParamsWhenProvided', async () => {
    mockFetch([{ id: 'TAC-2' }]);
    await getTactics('s1', 'jwt', { characteristic: 'scalability', priority: 'high', newOnly: true });
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/tactics?characteristic=scalability&priority=high&newOnly=true',
      expect.any(Object),
    );
  });

  it('getTacticsSummary_fetchesCorrectEndpoint', async () => {
    mockFetch({ totalCount: 5 });
    const result = await getTacticsSummary('s1', 'jwt');
    expect((result as unknown as { totalCount: number }).totalCount).toBe(5);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/tactics/summary',
      expect.any(Object),
    );
  });

  it('getBuyVsBuildSummary_fetchesWithNoParams', async () => {
    mockFetch({ decisions: [] });
    const result = await getBuyVsBuildSummary('s1', 'jwt');
    expect((result as { decisions: unknown[] }).decisions).toEqual([]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/build-analysis',
      expect.any(Object),
    );
  });

  it('getBuyVsBuildSummary_appendsRecommendationParam', async () => {
    mockFetch({ decisions: [] });
    await getBuyVsBuildSummary('s1', 'jwt', { recommendation: 'build' });
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/build-analysis?recommendation=build',
      expect.any(Object),
    );
  });

  it('getBuyVsBuildConflicts_fetchesCorrectEndpoint', async () => {
    mockFetch([{ id: 'C-1' }]);
    const result = await getBuyVsBuildConflicts('s1', 'jwt');
    expect(result).toEqual([{ id: 'C-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/build-analysis/conflicts',
      expect.any(Object),
    );
  });
});
