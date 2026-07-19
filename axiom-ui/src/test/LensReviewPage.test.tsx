import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as lensApi from '../api/lens';
import { LensReviewPage } from '../views/lens/LensReviewPage';

vi.mock('../api/lens', () => ({
  answerGapQuestion: vi.fn(),
  assessGaps: vi.fn(),
  createReviewSession: vi.fn(),
  deleteEvidence: vi.fn(),
  forceProceed: vi.fn(),
  generateGapQuestions: vi.fn(),
  getReviewReport: vi.fn(),
  getReviewSession: vi.fn(),
  listGapQuestions: vi.fn(),
  listEvidence: vi.fn(),
  startReview: vi.fn(),
  submitEvidence: vi.fn(),
  updateReviewSession: vi.fn(),
}));

vi.mock('../store/useStore', () => ({
  useStore: (selector: (state: { token: string }) => unknown) => selector({ token: 'jwt' }),
}));

const session = {
  id: '00000000-0000-0000-0000-000000000001',
  title: 'Retail review',
  systemDescription: 'Original description',
  status: 'EVIDENCE_COLLECTION' as const,
  gapRound: 0,
  gapsResolved: false,
  createdAt: '2026-07-01T00:00:00Z',
  updatedAt: '2026-07-01T00:00:00Z',
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/lens/sessions/${session.id}`]}>
      <Routes>
        <Route path="/lens/sessions/:sessionId" element={<LensReviewPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LensReviewPage actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(lensApi.getReviewSession).mockResolvedValue(session);
    vi.mocked(lensApi.listEvidence).mockResolvedValue([]);
  });

  it('saves the title and system description through the API', async () => {
    vi.mocked(lensApi.updateReviewSession).mockImplementation(async (_token, _id, payload) => ({
      ...session,
      ...payload,
    }));
    const user = userEvent.setup();
    renderPage();

    const description = await screen.findByDisplayValue('Original description');
    await user.clear(description);
    await user.type(description, 'Updated system description');
    await user.click(screen.getByRole('button', { name: 'Save details' }));

    await waitFor(() => expect(lensApi.updateReviewSession).toHaveBeenCalledWith('jwt', session.id, {
      title: 'Retail review',
      systemDescription: 'Updated system description',
    }));
    expect(await screen.findByText('Session details saved.')).toBeInTheDocument();
  });

  it('submits evidence and adds it to the review', async () => {
    vi.mocked(lensApi.submitEvidence).mockResolvedValue({
      id: 'evidence-1',
      sessionId: session.id,
      evidenceType: 'TEXT_DESCRIPTION',
      content: 'The service runs in two Azure regions with active failover.',
      sourceLabel: 'Architecture brief',
      submittedAt: '2026-07-01T00:00:00Z',
    });
    vi.mocked(lensApi.getReviewSession)
      .mockResolvedValueOnce(session)
      .mockResolvedValueOnce({ ...session, status: 'GAP_ELICITATION' });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add Evidence' }));
    await user.type(screen.getByPlaceholderText(/paste architecture evidence/i), 'The service runs in two Azure regions with active failover.');
    await user.type(screen.getByPlaceholderText(/source label/i), 'Architecture brief');
    await user.click(screen.getByRole('button', { name: 'Submit evidence' }));

    await waitFor(() => expect(lensApi.submitEvidence).toHaveBeenCalled());
    expect(await screen.findByText('The service runs in two Azure regions with active failover.')).toBeInTheDocument();
  });

  it('shows evidence submission failures inside the open dialog', async () => {
    vi.mocked(lensApi.submitEvidence).mockRejectedValue(new Error('Evidence service unavailable.'));
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add Evidence' }));
    await user.type(screen.getByPlaceholderText(/paste architecture evidence/i), 'Valid architecture evidence.');
    await user.click(screen.getByRole('button', { name: 'Submit evidence' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Evidence service unavailable.');
    expect(screen.getByRole('heading', { name: 'Add evidence' })).toBeInTheDocument();
  });

  it('submits gap answers and assesses the refreshed session', async () => {
    const gapSession = { ...session, status: 'GAP_ELICITATION' as const, gapRound: 1 };
    const question = {
      id: 'question-1',
      sessionId: session.id,
      round: 1,
      category: 'RELIABILITY' as const,
      question: 'How is disaster recovery tested?',
      rationale: 'Recovery evidence is required.',
      answered: false,
      answer: null,
      skipped: false,
      askedAt: '2026-07-01T00:00:00Z',
      answeredAt: null,
    };
    const answeredQuestion = {
      ...question,
      answered: true,
      answer: 'Quarterly failover exercises verify recovery.',
      answeredAt: '2026-07-01T01:00:00Z',
    };
    vi.mocked(lensApi.getReviewSession)
      .mockResolvedValueOnce(gapSession)
      .mockResolvedValueOnce({ ...gapSession, status: 'READY_FOR_REVIEW', gapsResolved: true });
    vi.mocked(lensApi.listEvidence).mockResolvedValue([{
      id: 'evidence-1',
      sessionId: session.id,
      evidenceType: 'TEXT_DESCRIPTION',
      content: 'Architecture and recovery evidence.',
      sourceLabel: null,
      submittedAt: '2026-07-01T00:00:00Z',
    }]);
    vi.mocked(lensApi.listGapQuestions)
      .mockResolvedValueOnce([question])
      .mockResolvedValueOnce([answeredQuestion]);
    vi.mocked(lensApi.answerGapQuestion).mockResolvedValue(answeredQuestion);
    vi.mocked(lensApi.assessGaps).mockResolvedValue({
      resolved: true,
      canProceed: true,
      remainingCount: 0,
      unresolvableGaps: [],
      summary: 'All critical gaps are resolved.',
    });
    const user = userEvent.setup();
    renderPage();

    const answer = await screen.findByPlaceholderText('Answer this question or skip it.');
    await user.type(answer, 'Quarterly failover exercises verify recovery.');
    await user.click(screen.getByRole('button', { name: 'Submit answers' }));

    await waitFor(() => expect(lensApi.answerGapQuestion).toHaveBeenCalledWith(
      'jwt',
      session.id,
      question.id,
      'Quarterly failover exercises verify recovery.',
      false,
    ));
    expect(await screen.findByText('Gap answers saved.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Assess gaps' }));

    await waitFor(() => expect(lensApi.assessGaps).toHaveBeenCalledWith('jwt', session.id));
    expect(await screen.findByText('All critical gaps are resolved.')).toBeInTheDocument();
    expect(screen.getByText('READY_FOR_REVIEW')).toBeInTheDocument();
  });
});
