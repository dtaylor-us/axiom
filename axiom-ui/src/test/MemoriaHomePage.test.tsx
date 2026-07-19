import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { MemoriaWorkspacePage } from '../views/memoria/MemoriaHomePage';
import {
  createSessionLink,
  getProjectSummary,
  listAdrs,
  listMemoryEntries,
  listProjects,
  listSessionLinks,
} from '../api/memoria';
import { emitToast } from '../components/Toast';
import { ApiError } from '../api/http';
import { listSessions as listArchonSessions } from '../api/sessions';
import { getSessions as listSpecWeaverSessions } from '../api/specweaver';
import { listReviewSessions } from '../api/lens';

vi.mock('../store/useStore', () => ({
  useStore: (selector: (state: { token: string }) => unknown) => selector({ token: 'jwt' }),
}));

vi.mock('../components/Toast', () => ({
  emitToast: vi.fn(),
}));

vi.mock('../api/memoria', () => ({
  createAdr: vi.fn(),
  createMemoryEntry: vi.fn(),
  createProject: vi.fn(),
  createSessionLink: vi.fn(),
  distillAllSessions: vi.fn(),
  distillSingleSession: vi.fn(),
  getProjectSummary: vi.fn(),
  listAdrs: vi.fn(),
  listDistillationJobs: vi.fn().mockResolvedValue([]),
  listMemoryEntries: vi.fn(),
  listProjects: vi.fn(),
  listSessionLinks: vi.fn(),
  promoteMemoryEntry: vi.fn(),
  removeSessionLink: vi.fn(),
  supersedeAdr: vi.fn(),
  supersedeMemoryEntry: vi.fn(),
  transitionMemoryEntry: vi.fn(),
}));

vi.mock('../api/sessions', () => ({
  listSessions: vi.fn(),
}));

vi.mock('../api/specweaver', () => ({
  getSessions: vi.fn(),
}));

vi.mock('../api/lens', () => ({
  listReviewSessions: vi.fn(),
}));

describe('MemoriaHomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (listProjects as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'project-1',
        name: 'Project One',
        description: 'Memory project',
        status: 'ACTIVE',
        createdAt: '2026-07-01T00:00:00Z',
        updatedAt: '2026-07-01T00:00:00Z',
      },
    ]);
    (getProjectSummary as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      totalFacts: 2,
      activeFacts: 2,
      staleFacts: 0,
      archivedFacts: 0,
      supersededFacts: 0,
      decisions: 2,
      requirements: 0,
      openRisks: 0,
      adrCount: 2,
      expiringSoon: 0,
    });
    (listMemoryEntries as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'entry-1',
        projectId: 'project-1',
        memoryType: 'DECISION',
        tier: 'EPISODIC',
        content: 'First memory',
        rationale: null,
        sourcePillar: null,
        sourceSessionId: null,
        sourceExcerpt: null,
        confidence: 'HIGH',
        status: 'ACTIVE',
        supersededBy: null,
        expiresAt: null,
        lastAccessedAt: null,
        accessCount: 0,
        tags: [],
        createdAt: '2026-07-01T00:00:00Z',
        updatedAt: '2026-07-01T00:00:00Z',
      },
      {
        id: 'entry-2',
        projectId: 'project-1',
        memoryType: 'DECISION',
        tier: 'EPISODIC',
        content: 'Second memory',
        rationale: null,
        sourcePillar: null,
        sourceSessionId: null,
        sourceExcerpt: null,
        confidence: 'HIGH',
        status: 'ACTIVE',
        supersededBy: null,
        expiresAt: null,
        lastAccessedAt: null,
        accessCount: 0,
        tags: [],
        createdAt: '2026-07-01T00:00:00Z',
        updatedAt: '2026-07-01T00:00:00Z',
      },
    ]);
    (listAdrs as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'adr-1',
        projectId: 'project-1',
        adrNumber: 1,
        title: 'ADR One',
        status: 'ACCEPTED',
        context: 'Context one',
        decision: 'Decision one',
        consequences: null,
        alternativesConsidered: null,
        sourcePillar: null,
        sourceSessionId: null,
        sourceMemoryEntryId: null,
        supersededByAdrNumber: null,
        createdAt: '2026-07-01T00:00:00Z',
      },
      {
        id: 'adr-2',
        projectId: 'project-1',
        adrNumber: 2,
        title: 'ADR Two',
        status: 'ACCEPTED',
        context: 'Context two',
        decision: 'Decision two',
        consequences: null,
        alternativesConsidered: null,
        sourcePillar: null,
        sourceSessionId: null,
        sourceMemoryEntryId: null,
        supersededByAdrNumber: null,
        createdAt: '2026-07-01T00:00:00Z',
      },
    ]);
    (listSessionLinks as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (listArchonSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (listSpecWeaverSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (listReviewSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  it('keeps supersede selections independent per row', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/memoria/projects/project-1']}>
        <Routes>
          <Route path="/memoria/projects/:projectId" element={<MemoriaWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(listProjects).toHaveBeenCalledWith('jwt');
      expect(listMemoryEntries).toHaveBeenCalledWith('jwt', 'project-1', {
        status: 'ACTIVE',
        tag: undefined,
        q: undefined,
      });
      expect(listAdrs).toHaveBeenCalledWith('jwt', 'project-1', {
        status: undefined,
        q: undefined,
      });
    });

    const firstMemoryRow = screen.getByText('First memory', { selector: 'p' }).closest('article');
    const secondMemoryRow = screen.getByText('Second memory', { selector: 'p' }).closest('article');
    const firstAdrRow = screen.getByText('ADR 1: ADR One', { selector: 'span' }).closest('article');
    const secondAdrRow = screen.getByText('ADR 2: ADR Two', { selector: 'span' }).closest('article');

    expect(firstMemoryRow).not.toBeNull();
    expect(secondMemoryRow).not.toBeNull();
    expect(firstAdrRow).not.toBeNull();
    expect(secondAdrRow).not.toBeNull();

    const firstMemorySelect = within(firstMemoryRow as HTMLElement).getByRole('combobox');
    const secondMemorySelect = within(secondMemoryRow as HTMLElement).getByRole('combobox');
    const firstAdrSelect = within(firstAdrRow as HTMLElement).getByRole('combobox');
    const secondAdrSelect = within(secondAdrRow as HTMLElement).getByRole('combobox');

    await user.selectOptions(firstMemorySelect, 'entry-2');
    await user.selectOptions(firstAdrSelect, 'adr-2');

    expect(firstMemorySelect).toHaveValue('entry-2');
    expect(secondMemorySelect).toHaveValue('');
    expect(firstAdrSelect).toHaveValue('adr-2');
    expect(secondAdrSelect).toHaveValue('');
  });

  it('displays session links when another workspace request fails', async () => {
    (listAdrs as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('ADR query failed'));
    (listSessionLinks as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 'link-1', projectId: 'project-1', pillar: 'ARCHON', sessionId: '4a214a1c-c9e7-4b64-90a9-622aa75083c8', linkedAt: '2026-07-03T00:00:00Z' },
    ]);

    render(
      <MemoryRouter initialEntries={['/memoria/projects/project-1']}>
        <Routes>
          <Route path="/memoria/projects/:projectId" element={<MemoriaWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('4a214a1c-c9e7-4b64-90a9-622aa75083c8')).toBeInTheDocument();
    expect(emitToast).toHaveBeenCalledWith('ADR query failed', 'error');
  });

  it('links a selected recent session and refreshes the linked-session list', async () => {
    const user = userEvent.setup();
    (listArchonSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: '4a214a1c-c9e7-4b64-90a9-622aa75083c8',
        title: 'Architecture analysis',
        createdAt: '2026-07-01T00:00:00Z',
        updatedAt: '2026-07-02T00:00:00Z',
      },
    ]);
    (createSessionLink as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'link-1',
      projectId: 'project-1',
      pillar: 'ARCHON',
      sessionId: '4a214a1c-c9e7-4b64-90a9-622aa75083c8',
      linkedAt: '2026-07-03T00:00:00Z',
    });
    (listSessionLinks as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: 'link-1', projectId: 'project-1', pillar: 'ARCHON', sessionId: '4a214a1c-c9e7-4b64-90a9-622aa75083c8', linkedAt: '2026-07-03T00:00:00Z' }]);

    render(
      <MemoryRouter initialEntries={['/memoria/projects/project-1']}>
        <Routes>
          <Route path="/memoria/projects/:projectId" element={<MemoriaWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const sessionSelect = (await screen.findAllByRole('combobox')).find((element) =>
      within(element).queryByText(/Architecture analysis/),
    );
    expect(sessionSelect).toBeDefined();
    await user.selectOptions(sessionSelect as HTMLElement, '4a214a1c-c9e7-4b64-90a9-622aa75083c8');
    await user.click(screen.getByRole('button', { name: 'Link session' }));

    await waitFor(() => expect(createSessionLink).toHaveBeenCalledWith(
      'jwt',
      'project-1',
      'ARCHON',
      '4a214a1c-c9e7-4b64-90a9-622aa75083c8',
    ));
    expect(await screen.findByText('4a214a1c-c9e7-4b64-90a9-622aa75083c8')).toBeInTheDocument();
    expect(emitToast).toHaveBeenCalledWith('Session linked to project.', 'info');
  });

  it('reports a link failure and keeps the selected session for retry', async () => {
    const user = userEvent.setup();
    (createSessionLink as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Session is already linked to a project'));

    render(
      <MemoryRouter initialEntries={['/memoria/projects/project-1']}>
        <Routes>
          <Route path="/memoria/projects/:projectId" element={<MemoriaWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const sessionInput = await screen.findByPlaceholderText('Session UUID');
    await user.type(sessionInput, '4a214a1c-c9e7-4b64-90a9-622aa75083c8');
    await user.click(screen.getByRole('button', { name: 'Link session' }));

    await waitFor(() => expect(emitToast).toHaveBeenCalledWith('Session is already linked to a project', 'error'));
    expect(sessionInput).toHaveValue('4a214a1c-c9e7-4b64-90a9-622aa75083c8');
    expect(screen.getByRole('button', { name: 'Link session' })).toBeEnabled();
  });

  it('opens the owning project when the session is linked elsewhere', async () => {
    const user = userEvent.setup();
    (listProjects as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 'project-1', name: 'Current project', description: '', status: 'ACTIVE', createdAt: '2026-07-01T00:00:00Z', updatedAt: '2026-07-01T00:00:00Z' },
      { id: 'project-2', name: 'Neteru Path', description: '', status: 'ACTIVE', createdAt: '2026-07-01T00:00:00Z', updatedAt: '2026-07-01T00:00:00Z' },
    ]);
    (createSessionLink as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new ApiError(
      409,
      "Session is already linked to project 'Neteru Path' (project-2)",
      { type: 'urn:memoria:duplicate-session-link', projectId: 'project-2', projectName: 'Neteru Path' } as never,
    ));

    render(
      <MemoryRouter initialEntries={['/memoria/projects/project-1']}>
        <Routes>
          <Route path="/memoria/projects/:projectId" element={<MemoriaWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const sessionInput = await screen.findByPlaceholderText('Session UUID');
    await user.type(sessionInput, '4a214a1c-c9e7-4b64-90a9-622aa75083c8');
    await user.click(screen.getByRole('button', { name: 'Link session' }));

    await waitFor(() => expect(listSessionLinks).toHaveBeenCalledWith('jwt', 'project-2'));
    expect(emitToast).toHaveBeenCalledWith('Opening Neteru Path, where this session is already linked.', 'info');
  });
});
