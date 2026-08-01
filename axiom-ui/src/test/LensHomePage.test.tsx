import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { LensHomePage } from '../views/lens/LensHomePage';
import { listReviewSessions } from '../api/lens';

vi.mock('../api/lens', () => ({
  listReviewSessions: vi.fn().mockResolvedValue([]),
}));

vi.mock('../store/useStore', () => ({
  useStore: (selector: (state: { token: string }) => unknown) => selector({ token: 'jwt' }),
}));

describe('LensHomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={['/lens']}>
        <Routes>
          <Route path="/lens" element={<LensHomePage />} />
          <Route path="/lens/new" element={<div data-testid="lens-new-target" />} />
          <Route path="/lens/sessions/lens-1" element={<div data-testid="lens-session-target" />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it('loads recent reviews and navigates to a review', async () => {
    (listReviewSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'lens-1',
        title: 'Retail platform',
        status: 'READY_FOR_REVIEW',
        systemDescription: 'Retail platform',
        gapRound: 1,
        gapsResolved: false,
        createdAt: '2026-06-01T00:00:00Z',
        updatedAt: '2026-06-01T00:00:00Z',
      },
    ]);

    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(listReviewSessions).toHaveBeenCalledWith('jwt');
    });

    expect(screen.getByTestId('lens-home-page')).toBeInTheDocument();
    expect(screen.getByTestId('lens-home-session-lens-1')).toBeInTheDocument();
    expect(screen.getByText('READY_FOR_REVIEW')).toBeInTheDocument();

    await user.click(screen.getByTestId('lens-home-session-lens-1'));
    expect(screen.getByTestId('lens-session-target')).toBeInTheDocument();
  });

  it('navigates to the new review flow', async () => {
    (listReviewSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(listReviewSessions).toHaveBeenCalledWith('jwt');
    });

    await user.click(screen.getByRole('button', { name: /new architecture review/i }));
    expect(screen.getByTestId('lens-new-target')).toBeInTheDocument();
  });
});
