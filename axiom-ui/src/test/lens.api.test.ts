import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  answerGapQuestion,
  assessGaps,
  createReviewSession,
  deleteEvidence,
  deleteReviewSession,
  forceProceed,
  generateGapQuestions,
  getReviewReport,
  getReviewSession,
  listEvidence,
  listGapQuestions,
  listReviewSessions,
  startReview,
  submitEvidence,
  updateReviewSession,
} from '../api/lens';

function mockJsonFetch(data: unknown, status = 200, contentType = 'application/json') {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => contentType },
    json: async () => data,
  } as unknown as Response);
}

function makeJwt(sub: string): string {
  const payload = Buffer.from(JSON.stringify({ sub })).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `header.${payload}.sig`;
}

describe('lens API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('createReviewSession_postsSessionPayload', async () => {
    mockJsonFetch({ id: 'lens-1', title: 'Retail platform review' }, 201);

    const result = await createReviewSession(makeJwt('lens-user'), 'Retail platform review', 'System description');

    expect(result.id).toBe('lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: `Bearer ${makeJwt('lens-user')}`,
          'X-Axiom-User-Id': 'lens-user',
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({
          title: 'Retail platform review',
          systemDescription: 'System description',
        }),
      }),
    );
  });

  it('coversReviewSessionCrudAndReportEndpoints', async () => {
    mockJsonFetch([{ id: 'lens-1' }]);
    await listReviewSessions('jwt-token');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt-token',
          'X-Axiom-User-Id': 'guest',
        }),
      }),
    );

    mockJsonFetch({ id: 'lens-1' });
    await getReviewSession('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1',
      expect.any(Object),
    );

    mockJsonFetch({ id: 'lens-1', title: 'Updated' });
    await updateReviewSession('jwt-token', 'lens-1', { title: 'Updated', systemDescription: 'Updated system' });
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt-token',
          'X-Axiom-User-Id': 'guest',
          'Content-Type': 'application/json',
        }),
      }),
    );

    mockJsonFetch(undefined, 204);
    await deleteReviewSession('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1',
      expect.objectContaining({
        method: 'DELETE',
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt-token',
          'X-Axiom-User-Id': 'guest',
        }),
      }),
    );

    mockJsonFetch([{ id: 'e-1' }]);
    await listEvidence('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/evidence',
      expect.any(Object),
    );

    mockJsonFetch({ id: 'e-1', content: 'evidence' }, 201);
    await submitEvidence('jwt-token', 'lens-1', {
      evidenceType: 'TEXT_DESCRIPTION',
      content: 'evidence',
      sourceLabel: 'Notes',
    });
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/evidence',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt-token',
          'X-Axiom-User-Id': 'guest',
          'Content-Type': 'application/json',
        }),
      }),
    );

    mockJsonFetch(undefined, 204);
    await deleteEvidence('jwt-token', 'lens-1', 'e-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/evidence/e-1',
      expect.objectContaining({ method: 'DELETE' }),
    );

    mockJsonFetch([{ id: 'g-1' }], 201);
    await generateGapQuestions('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/gaps/generate',
      expect.objectContaining({ method: 'POST' }),
    );

    mockJsonFetch([{ id: 'g-1' }]);
    await listGapQuestions('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/gaps',
      expect.any(Object),
    );

    mockJsonFetch({ id: 'g-1' }, 201);
    await answerGapQuestion('jwt-token', 'lens-1', 'q-1', 'yes', true);
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/gaps/q-1/answer',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ answer: 'yes', skipped: true }),
      }),
    );

    mockJsonFetch({ resolved: true }, 201);
    await assessGaps('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/gaps/assess',
      expect.objectContaining({ method: 'POST' }),
    );

    mockJsonFetch({ status: 'READY_FOR_REVIEW' }, 201);
    await forceProceed('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/proceed',
      expect.objectContaining({ method: 'POST' }),
    );

    mockJsonFetch({ overallRating: 'APPROVED' }, 201);
    await startReview('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/review',
      expect.objectContaining({ method: 'POST' }),
    );

    mockJsonFetch({ overallRating: 'APPROVED' });
    await getReviewReport('jwt-token', 'lens-1');
    expect(fetch).toHaveBeenCalledWith(
      '/lens-api/api/v1/lens/sessions/lens-1/report',
      expect.any(Object),
    );
  });
});
