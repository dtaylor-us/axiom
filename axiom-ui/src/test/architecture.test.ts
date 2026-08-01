import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getArchitecture, getDiagramByType, getDiagramCollection } from '../api/architecture';

describe('architecture API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.removeItem('archon.auth');
  });

  it('getArchitecture_fetchesWithAuthHeader', async () => {
    const mockData = {
      conversationId: 'c1',
      style: 'microservices',
      components: [],
      interactions: [],
      componentDiagram: '',
      sequenceDiagram: '',
    };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => mockData,
    } as unknown as Response);

    const result = await getArchitecture('session-1', 'jwt-token');
    expect(result).toEqual(mockData);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/session-1/architecture',
      {
        headers: {
          Authorization: 'Bearer jwt-token',
          'X-Axiom-User-Id': 'guest',
        },
      },
    );
  });

  it('getArchitecture_throwsOnNonOk', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      headers: { get: () => null },
    } as unknown as Response);

    await expect(getArchitecture('bad', 'jwt')).rejects.toThrow(
      'The requested resource was not found.',
    );
  });

  it('getDiagramCollection_fetchesAndReturnsDiagramCollection', async () => {
    const mockData = {
      diagramCount: 1,
      diagramTypes: ['c4_container'],
      diagrams: [{
        diagramId: 'D-001',
        type: 'c4_container',
        title: 'C4 Container',
        description: 'Container view',
        mermaidSource: 'graph TD\nA-->B',
        characteristicAddressed: 'modularity',
      }],
    };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => mockData,
    } as unknown as Response);

    const result = await getDiagramCollection('s1', 'jwt');
    expect(result).toEqual(mockData);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/s1/diagram',
      {
        headers: {
          Authorization: 'Bearer jwt',
          'X-Axiom-User-Id': 'guest',
        },
      },
    );
  });

  it('getDiagramByType_returnsMermaidSource_andEncodesTheType', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ mermaidSource: 'graph TD; A-->B' }),
    } as unknown as Response);

    await expect(getDiagramByType('s1', 'deployment view', 'jwt')).resolves.toBe('graph TD; A-->B');
    expect(fetch).toHaveBeenCalledWith('/api/v1/sessions/s1/diagram/deployment%20view', expect.any(Object));
  });

  it('getDiagramByType_returnsNullForMissingOrEmptyDiagrams', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: true, headers: { get: () => 'application/json' }, json: async () => ({ mermaidSource: '' }) } as unknown as Response)
      .mockResolvedValueOnce({ ok: false, status: 404, headers: { get: () => null } } as unknown as Response);

    await expect(getDiagramByType('s1', 'deployment', 'jwt')).resolves.toBeNull();
    await expect(getDiagramByType('s1', 'missing', 'jwt')).resolves.toBeNull();
  });

  it('getDiagramByType_rethrowsNon404Errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 500, headers: { get: () => null } } as unknown as Response);
    await expect(getDiagramByType('s1', 'deployment', 'jwt')).rejects.toThrow('Something went wrong on the server. Please try again.');
  });
});
