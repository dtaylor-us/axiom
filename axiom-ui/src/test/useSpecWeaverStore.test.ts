import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Session } from '../api/specweaver';
import { useSpecWeaverStore } from '../store/useSpecWeaverStore';

function mockFetchSequence(payloads: unknown[]) {
  const responses = payloads.map((payload) => ({
    ok: true,
    status: 200,
    headers: { get: () => 'application/json' },
    json: async () => payload,
  } as unknown as Response));
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
    const response = responses.shift();
    if (!response) throw new Error('Unexpected fetch call');
    return response;
  });
}

describe('useSpecWeaverStore', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useSpecWeaverStore.setState({
      sessions: [],
      currentSession: null,
      currentPackage: null,
      isGenerating: false,
      generationStages: [],
      isSending: false,
      error: null,
    });
  });

  it('loadSessions_storesReturnedSessions', async () => {
    mockFetchSequence([[{ id: 'sw-1', documents: [] }]]);

    await useSpecWeaverStore.getState().loadSessions('jwt');

    expect(useSpecWeaverStore.getState().sessions).toEqual([{ id: 'sw-1', documents: [] }]);
  });

  it('createSession_setsCurrentSession', async () => {
    mockFetchSequence([{ id: 'sw-1', documents: [] }]);

    const session = await useSpecWeaverStore.getState().createSession('jwt', 'Discovery');

    expect(session.id).toBe('sw-1');
    expect(useSpecWeaverStore.getState().currentSession?.id).toBe('sw-1');
  });

  it('updateSessionTitle_updatesCurrentSessionAndSessionList', async () => {
    const existingSession: Session = {
      id: 'sw-1',
      title: 'Original',
      status: 'ACTIVE',
      createdAt: '2026-05-30T00:00:00Z',
      updatedAt: '2026-05-30T00:00:00Z',
      archonConversationId: null,
      documents: [],
    };

    useSpecWeaverStore.setState({
      sessions: [existingSession],
      currentSession: existingSession,
    });
    mockFetchSequence([
      {
        ...existingSession,
        title: 'Updated',
      },
    ]);

    const session = await useSpecWeaverStore.getState().updateSessionTitle('jwt', 'sw-1', 'Updated');

    expect(session.title).toBe('Updated');
    expect(useSpecWeaverStore.getState().currentSession?.title).toBe('Updated');
    expect(useSpecWeaverStore.getState().sessions[0]?.title).toBe('Updated');
  });

  it('uploadDocument_refreshesCurrentSession', async () => {
    mockFetchSequence([
      { id: 'doc-1' },
      { id: 'sw-1', documents: [{ id: 'doc-1', status: 'EXTRACTED', documentType: 'PLAIN_TEXT' }] },
    ]);

    await useSpecWeaverStore.getState().uploadDocument('jwt', 'sw-1', null, 'notes', 'PLAIN_TEXT');

    expect(useSpecWeaverStore.getState().currentSession?.documents).toHaveLength(1);
  });

  it('deleteDocument_refreshesCurrentSession', async () => {
    mockFetchSequence([
      undefined,
      { id: 'sw-1', documents: [] },
    ]);

    await useSpecWeaverStore.getState().deleteDocument('jwt', 'sw-1', 'doc-1');

    expect(useSpecWeaverStore.getState().currentSession?.documents).toEqual([]);
  });

  it('generatePackage_storesGeneratedPackage', async () => {
    mockFetchSequence([
      { packageId: 'pkg-1' },
      { id: 'sw-1', status: 'PROCESSING', documents: [] },
      {
        id: 'pkg-1',
        sessionId: 'sw-1',
        packageJson: JSON.stringify({
          packageId: 'pkg-1',
          sessionId: 'sw-1',
          requirements: [],
          totalRequirements: 0,
          highConfidenceCount: 0,
          inferredCount: 0,
          readinessScore: 0,
        }),
        totalRequirements: 0,
        highConfidenceCount: 0,
        inferredCount: 0,
        readinessScore: 0,
        createdAt: '2026-05-30T00:00:00Z',
        sentToArchonAt: null,
        archonConversationId: null,
      },
      { id: 'sw-1', status: 'PACKAGE_READY', documents: [] },
    ]);

    await useSpecWeaverStore.getState().generatePackage('jwt', 'sw-1');

    expect(useSpecWeaverStore.getState().currentPackage?.packageId).toBe('pkg-1');
    expect(useSpecWeaverStore.getState().isGenerating).toBe(false);
    expect(useSpecWeaverStore.getState().generationStages.every((stage) => stage.status === 'complete')).toBe(true);
  });

  it('generatePackage_marksCurrentStageAsErrorWhenGenerationFails', async () => {
    mockFetchSequence([
      { id: 'sw-1', status: 'PROCESSING', documents: [] },
      { id: 'sw-1', status: 'ACTIVE', documents: [] },
    ]);
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(async () => {
      throw new Error('generation failed');
    });

    await expect(useSpecWeaverStore.getState().generatePackage('jwt', 'sw-1')).rejects.toThrow(
      'Network error',
    );

    expect(useSpecWeaverStore.getState().isGenerating).toBe(false);
    expect(useSpecWeaverStore.getState().generationStages.some((stage) => stage.status === 'error')).toBe(true);
  });

  it('generatePackage_advancesVisibleStagesWhenSessionRemainsActive', async () => {
    vi.useFakeTimers();
    try {
      const packagePayload = {
        id: 'pkg-1',
        sessionId: 'sw-1',
        packageJson: JSON.stringify({
          packageId: 'pkg-1',
          sessionId: 'sw-1',
          requirements: [],
          totalRequirements: 0,
          highConfidenceCount: 0,
          inferredCount: 0,
          readinessScore: 0,
        }),
        totalRequirements: 0,
        highConfidenceCount: 0,
        inferredCount: 0,
        readinessScore: 0,
        createdAt: '2026-05-30T00:00:00Z',
        sentToArchonAt: null,
        archonConversationId: null,
      };

      const responseQueue: Response[] = [
        {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({ packageId: 'pkg-1' }),
        } as unknown as Response,
        {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({ id: 'sw-1', status: 'ACTIVE', documents: [] }),
        } as unknown as Response,
        {
          ok: false,
          status: 404,
          headers: { get: () => 'application/problem+json' },
          json: async () => ({ detail: 'Package not generated' }),
        } as unknown as Response,
        {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({ id: 'sw-1', status: 'ACTIVE', documents: [] }),
        } as unknown as Response,
        {
          ok: false,
          status: 404,
          headers: { get: () => 'application/problem+json' },
          json: async () => ({ detail: 'Package not generated' }),
        } as unknown as Response,
        {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({ id: 'sw-1', status: 'ACTIVE', documents: [] }),
        } as unknown as Response,
        {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => packagePayload,
        } as unknown as Response,
        {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: async () => ({ id: 'sw-1', status: 'PACKAGE_READY', documents: [] }),
        } as unknown as Response,
      ];

      vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
        const nextResponse = responseQueue.shift();
        if (!nextResponse) {
          throw new Error('Unexpected fetch call');
        }
        return nextResponse;
      });

      const generationPromise = useSpecWeaverStore.getState().generatePackage('jwt', 'sw-1');

      // Two polling waits are required before the package appears in this scenario.
      await vi.advanceTimersByTimeAsync(10_000);
      await generationPromise;

      expect(useSpecWeaverStore.getState().currentPackage?.packageId).toBe('pkg-1');
      expect(useSpecWeaverStore.getState().generationStages.every((stage) => stage.status === 'complete')).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('sendToArchon_returnsBriefText', async () => {
    mockFetchSequence([
      { briefText: 'brief' },
    ]);

    const response = await useSpecWeaverStore.getState().sendToArchon('jwt', 'sw-1');

    expect(response).toBe('brief');
    expect(useSpecWeaverStore.getState().isSending).toBe(false);
  });

  it('loadSessions_setsErrorWhenRequestFails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));

    await useSpecWeaverStore.getState().loadSessions('jwt');

    expect(useSpecWeaverStore.getState().error).toContain('Network error');
  });

  it('loadSession_clearsStaleSessionWhenForbidden', async () => {
    const existingSession: Session = {
      id: 'sw-1',
      title: 'Existing',
      status: 'ACTIVE',
      createdAt: '2026-05-30T00:00:00Z',
      updatedAt: '2026-05-30T00:00:00Z',
      archonConversationId: null,
      documents: [],
    };

    useSpecWeaverStore.setState({
      currentSession: existingSession,
      currentPackage: {
        packageId: 'pkg-1',
        sessionId: 'sw-1',
        createdAt: '2026-05-30T00:00:00Z',
        readinessScore: 0,
        readinessLabel: 'Needs review',
        systemDescription: '',
        requirements: [],
        gaps: [],
        conflicts: [],
        sourceDocuments: [],
        totalRequirements: 0,
        highConfidenceCount: 0,
        inferredCount: 0,
        duplicateCount: 0,
        gapCount: 0,
        conflictCount: 0,
      },
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
      headers: { get: () => 'application/problem+json' },
      json: async () => ({ detail: 'Forbidden' }),
    } as unknown as Response);

    await useSpecWeaverStore.getState().loadSession('jwt', 'sw-1');

    expect(useSpecWeaverStore.getState().currentSession).toBeNull();
    expect(useSpecWeaverStore.getState().currentPackage).toBeNull();
    expect(useSpecWeaverStore.getState().error).toBe('You do not have access to this SpecWeaver session.');
  });
});
