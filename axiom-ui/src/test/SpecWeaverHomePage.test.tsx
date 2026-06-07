import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { SpecWeaverHomePage } from '../views/specweaver/SpecWeaverHomePage';

const loadSessions = vi.fn().mockResolvedValue(undefined);
const createSession = vi.fn().mockResolvedValue({ id: 'sw-new' });

vi.mock('../store/useStore', () => ({
  useStore: (selector: (state: { token: string }) => unknown) => selector({ token: 'jwt' }),
}));

vi.mock('../store/useSpecWeaverStore', () => ({
  useSpecWeaverStore: (selector: (state: unknown) => unknown) =>
    selector({
      sessions: [
        {
          id: 'sw-1',
          title: 'Billing requirements',
          status: 'PACKAGE_READY',
          createdAt: '2026-06-01T00:00:00Z',
          updatedAt: '2026-06-01T00:00:00Z',
          archonConversationId: null,
          documents: [],
        },
      ],
      error: null,
      loadSessions,
      createSession,
    }),
}));

vi.mock('../api/specweaver', () => ({}));

describe('SpecWeaverHomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads sessions and renders recent list', async () => {
    render(
      <MemoryRouter>
        <SpecWeaverHomePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(loadSessions).toHaveBeenCalledWith('jwt');
    });

    expect(screen.getByTestId('specweaver-home-page')).toBeInTheDocument();
    expect(screen.getByTestId('specweaver-home-recent-sw-1')).toBeInTheDocument();
  });

  it('creates a new session and navigates to session page', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/specweaver']}>
        <Routes>
          <Route path="/specweaver" element={<SpecWeaverHomePage />} />
          <Route path="/specweaver/sessions/sw-new" element={<div data-testid="specweaver-session-target" />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(screen.getByTestId('specweaver-start-session'));

    await waitFor(() => {
      expect(createSession).toHaveBeenCalledWith('jwt', undefined);
    });
    expect(screen.getByTestId('specweaver-session-target')).toBeInTheDocument();
  });
});
