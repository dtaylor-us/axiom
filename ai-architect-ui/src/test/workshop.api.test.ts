import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createWorkshopSession,
  submitWorkshopTurn,
  getWorkshopSession,
  getWorkshopAttributes,
  getWorkshopScenarios,
  completeWorkshopSession,
  sendWorkshopToPipeline,
  listWorkshopSessions,
  getWorkshopMessages,
  assessGenerationReadiness,
  generateAttributes,
  getUtilityTree,
  getImplications,
} from '../api/workshop';

function mockGetFetch(data: unknown) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    status: 200,
    headers: { get: () => 'application/json' },
    json: async () => data,
  } as unknown as Response);
}

function mockPostFetch(data: unknown, status = 200) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    status,
    headers: { get: () => 'application/json' },
    json: async () => data,
  } as unknown as Response);
}

describe('workshop API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Stub crypto.randomUUID used by sendWorkshopToPipeline
    vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' });
  });

  it('createWorkshopSession_postsToBaseEndpoint', async () => {
    mockPostFetch({ sessionId: 'ws-1', systemName: 'MyApp' });

    const result = await createWorkshopSession('jwt', 'MyApp');

    expect((result as { sessionId: string }).sessionId).toBe('ws-1');
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ systemName: 'MyApp' }),
      }),
    );
  });

  it('submitWorkshopTurn_postsUserInputToTurnEndpoint', async () => {
    mockPostFetch({ response: 'ok' });

    await submitWorkshopTurn('jwt', 'ws-1', 'Hello agent');

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/turn',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ userInput: 'Hello agent' }),
      }),
    );
  });

  it('getWorkshopSession_fetchesSessionEndpoint', async () => {
    mockGetFetch({ sessionId: 'ws-1' });

    const result = await getWorkshopSession('jwt', 'ws-1');

    expect((result as { sessionId: string }).sessionId).toBe('ws-1');
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer jwt' }) }),
    );
  });

  it('getWorkshopAttributes_fetchesAttributesEndpoint', async () => {
    mockGetFetch([{ id: 'A-1' }]);

    const result = await getWorkshopAttributes('jwt', 'ws-1');

    expect(result).toEqual([{ id: 'A-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/attributes',
      expect.any(Object),
    );
  });

  it('getWorkshopAttributes_appendsConfidenceFilter', async () => {
    mockGetFetch([]);

    await getWorkshopAttributes('jwt', 'ws-1', 'confirmed');

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/attributes?confidence=confirmed',
      expect.any(Object),
    );
  });

  it('getWorkshopScenarios_fetchesScenariosEndpoint', async () => {
    mockGetFetch([{ id: 'S-1' }]);

    const result = await getWorkshopScenarios('jwt', 'ws-1');

    expect(result).toEqual([{ id: 'S-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/scenarios',
      expect.any(Object),
    );
  });

  it('completeWorkshopSession_postsToCompleteEndpoint', async () => {
    mockPostFetch({ confirmed: 3 });

    const result = await completeWorkshopSession('jwt', 'ws-1');

    expect((result as unknown as { confirmed: number }).confirmed).toBe(3);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/complete',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('sendWorkshopToPipeline_postsWithIdempotencyKey', async () => {
    mockPostFetch({ conversationId: 'c-1', initialMessage: 'ready' });

    const result = await sendWorkshopToPipeline('jwt', 'ws-1');

    expect((result as { conversationId: string }).conversationId).toBe('c-1');
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/send-to-pipeline',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Idempotency-Key': 'test-uuid' }),
      }),
    );
  });

  it('listWorkshopSessions_fetchesBaseEndpoint', async () => {
    mockGetFetch([{ sessionId: 'ws-1' }, { sessionId: 'ws-2' }]);

    const result = await listWorkshopSessions('jwt');

    expect(result).toHaveLength(2);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer jwt' }) }),
    );
  });

  it('getWorkshopMessages_fetchesMessagesEndpoint', async () => {
    mockGetFetch([{ role: 'user', content: 'hi' }]);

    const result = await getWorkshopMessages('jwt', 'ws-1');

    expect(result).toEqual([{ role: 'user', content: 'hi' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/messages',
      expect.any(Object),
    );
  });

  it('assessGenerationReadiness_fetchesReadinessEndpoint', async () => {
    mockGetFetch({ ready: true, score: 90 });

    const result = await assessGenerationReadiness('ws-1', 'jwt');

    expect((result as unknown as { ready: boolean }).ready).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/generation-readiness',
      expect.any(Object),
    );
  });

  it('generateAttributes_postsToGenerateEndpoint', async () => {
    mockPostFetch({ generated: 5 });

    const result = await generateAttributes('ws-1', 'jwt');

    expect((result as unknown as { generated: number }).generated).toBe(5);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/generate',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('getUtilityTree_fetchesUtilityTreeEndpoint', async () => {
    mockGetFetch({ nodes: [] });

    const result = await getUtilityTree('jwt', 'ws-1');

    expect((result as { nodes: unknown[] }).nodes).toEqual([]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/utility-tree',
      expect.any(Object),
    );
  });

  it('getImplications_fetchesImplicationsEndpoint', async () => {
    mockGetFetch([{ id: 'I-1' }]);

    const result = await getImplications('jwt', 'ws-1');

    expect(result).toEqual([{ id: 'I-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workshop/sessions/ws-1/implications',
      expect.any(Object),
    );
  });

  it('throwsApiErrorOnNonOkPostResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ message: 'Validation failed' }),
    } as unknown as Response);

    await expect(createWorkshopSession('jwt', 'BadName')).rejects.toThrow();
  });
});
