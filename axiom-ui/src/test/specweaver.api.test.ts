import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createSession,
  deleteDocument,
  generatePackage,
  getPackage,
  getSession,
  getSessions,
  sendToArchon,
  updateSessionTitle,
  uploadDocument,
} from '../api/specweaver';

function mockJsonFetch(data: unknown, status = 200) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => 'application/json' },
    json: async () => data,
  } as unknown as Response);
}

describe('specweaver API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('createSession_postsTitleToSessionsEndpoint', async () => {
    mockJsonFetch({ id: 'sw-1', documents: [] }, 201);

    const result = await createSession('jwt', 'Discovery');

    expect(result.id).toBe('sw-1');
    expect(fetch).toHaveBeenCalledWith(
      '/specweaver-api/api/v1/sessions',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer jwt' }),
        body: JSON.stringify({ title: 'Discovery' }),
      }),
    );
  });

  it('getSessions_fetchesSessionsEndpoint', async () => {
    mockJsonFetch([{ id: 'sw-1' }]);

    const result = await getSessions('jwt');

    expect(result).toEqual([{ id: 'sw-1' }]);
    expect(fetch).toHaveBeenCalledWith(
      '/specweaver-api/api/v1/sessions',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer jwt' }) }),
    );
  });

  it('getSession_fetchesSingleSessionEndpoint', async () => {
    mockJsonFetch({ id: 'sw-1' });

    const result = await getSession('jwt', 'sw-1');

    expect(result.id).toBe('sw-1');
    expect(fetch).toHaveBeenCalledWith('/specweaver-api/api/v1/sessions/sw-1', expect.any(Object));
  });

  it('updateSessionTitle_patchesSessionEndpoint', async () => {
    mockJsonFetch({ id: 'sw-1', title: 'Updated' });

    const result = await updateSessionTitle('jwt', 'sw-1', 'Updated');

    expect(result.title).toBe('Updated');
    expect(fetch).toHaveBeenCalledWith(
      '/specweaver-api/api/v1/sessions/sw-1',
      expect.objectContaining({
        method: 'PATCH',
        headers: expect.objectContaining({ Authorization: 'Bearer jwt' }),
        body: JSON.stringify({ title: 'Updated' }),
      }),
    );
  });

  it('uploadDocument_postsMultipartFormData', async () => {
    mockJsonFetch({ id: 'doc-1' }, 201);
    const file = new File(['hello'], 'notes.pdf', { type: 'application/pdf' });

    const result = await uploadDocument('jwt', 'sw-1', file, null, 'PDF', 'Notes');

    expect(result.id).toBe('doc-1');
    expect(fetch).toHaveBeenCalledWith(
      '/specweaver-api/api/v1/sessions/sw-1/documents',
      expect.objectContaining({
        method: 'POST',
        headers: { Authorization: 'Bearer jwt' },
        body: expect.any(FormData),
      }),
    );
  });

  it('deleteDocument_deletesDocumentEndpoint', async () => {
    mockJsonFetch(undefined, 204);

    await deleteDocument('jwt', 'sw-1', 'doc-1');

    expect(fetch).toHaveBeenCalledWith(
      '/specweaver-api/api/v1/sessions/sw-1/documents/doc-1',
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('generatePackage_postsGenerateEndpoint', async () => {
    mockJsonFetch({ packageId: 'pkg-1' }, 202);

    const result = await generatePackage('jwt', 'sw-1');

    expect(result.packageId).toBe('pkg-1');
    expect(fetch).toHaveBeenCalledWith(
      '/specweaver-api/api/v1/sessions/sw-1/package/generate',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('getPackage_fetchesLegacyPackageEnvelopeEndpoint', async () => {
    mockJsonFetch({
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
    });

    const result = await getPackage('jwt', 'sw-1');

    expect(result.packageId).toBe('pkg-1');
    expect(fetch).toHaveBeenCalledWith('/specweaver-api/api/v1/sessions/sw-1/package', expect.any(Object));
  });

  it('getPackage_supportsDirectPackageResponseShape', async () => {
    mockJsonFetch({
      packageId: 'pkg-2',
      sessionId: 'sw-1',
      createdAt: '2026-05-30T00:00:00Z',
      readinessScore: 0.43,
      readinessLabel: 'Significant gaps — review needed',
      systemDescription: 'Healthcare appointment booking platform',
      requirements: [
        {
          requirementId: 'REQ-1',
          category: 'functional',
          statement: 'The user can book appointments.',
          type: 'explicit',
          confidence: 'HIGH',
          isInferred: false,
          inferenceReasoning: null,
          sourceDocumentIds: ['doc-1'],
          sourceExcerpts: ['Users need to book appointments online'],
          ambiguities: [],
        },
      ],
      gaps: [
        {
          gapId: 'GAP-1',
          area: 'Security requirements',
          severity: 'critical',
          explanation: 'No auth requirements were provided',
          clarificationQuestion: 'How should users authenticate?',
          affectedCategories: ['non_functional'],
        },
      ],
      conflicts: [
        {
          conflictId: 'C-1',
          requirementIds: ['REQ-1', 'REQ-2'],
          description: 'Booking must be instant and fully manual approval is required.',
          interpretations: ['instant auto booking', 'manual review before booking'],
          clarificationQuestion: 'Should booking be auto-approved or manual?',
        },
      ],
      sourceDocuments: [{ id: 'doc-1', filename: 'requirements.md' }],
      totalRequirements: 46,
      highConfidenceCount: 41,
      inferredCount: 5,
      duplicateCount: 3,
      gapCount: 7,
      conflictCount: 2,
    });

    const result = await getPackage('jwt', 'sw-1');

    expect(result.packageId).toBe('pkg-2');
    expect(result.requirements).toHaveLength(1);
    expect(result.gaps).toHaveLength(1);
    expect(result.conflicts).toHaveLength(1);
    expect(result.totalRequirements).toBe(46);
  });

  it('sendToArchon_postsSendEndpoint', async () => {
    mockJsonFetch({ briefText: 'brief' });

    const result = await sendToArchon('jwt', 'sw-1');

    expect(result.briefText).toBe('brief');
    expect(fetch).toHaveBeenCalledWith(
      '/specweaver-api/api/v1/sessions/sw-1/package/send-to-archon',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
