import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ArchonHomePage } from '../views/archon/ArchonHomePage';
import { listSessions } from '../api/sessions';

vi.mock('../api/sessions', () => ({
  listSessions: vi.fn().mockResolvedValue([]),
}));

vi.mock('../store/useStore', () => ({
  useStore: (selector: (state: { token: string }) => unknown) => selector({ token: 'jwt' }),
}));

describe('ArchonHomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and displays recent analyses', async () => {
    (listSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 'a1', title: 'Payments', createdAt: '2026-06-01T00:00:00Z' },
    ]);

    render(
      <MemoryRouter>
        <ArchonHomePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(listSessions).toHaveBeenCalledWith('jwt');
    });

    expect(screen.getByTestId('archon-recent-a1')).toBeInTheDocument();
  });

  it('navigates to chat when starting a new analysis', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/archon']}>
        <Routes>
          <Route path="/archon" element={<ArchonHomePage />} />
          <Route path="/archon/chat" element={<div data-testid="archon-chat-target" />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(screen.getByTestId('archon-start-analysis'));

    expect(screen.getByTestId('archon-chat-target')).toBeInTheDocument();
  });
});
