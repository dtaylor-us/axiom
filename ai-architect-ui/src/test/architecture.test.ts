import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getArchitecture, getDiagramCollection } from '../api/architecture';

describe('architecture API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
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
      { headers: { Authorization: 'Bearer jwt-token' } },
    );
  });

  it('getArchitecture_throwsOnNonOk', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      headers: { get: () => null },
    } as unknown as Response);

    await expect(getArchitecture('bad', 'jwt')).rejects.toThrow('404');
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
      { headers: { Authorization: 'Bearer jwt' } },
    );
  });
});
