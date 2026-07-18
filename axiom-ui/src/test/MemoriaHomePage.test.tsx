import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { MemoriaHomePage } from '../views/memoria/MemoriaHomePage';
import {
  getProjectSummary,
  listAdrs,
  listMemoryEntries,
  listProjects,
  listSessionLinks,
} from '../api/memoria';

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
  getProjectSummary: vi.fn(),
  listAdrs: vi.fn(),
  listMemoryEntries: vi.fn(),
  listProjects: vi.fn(),
  listSessionLinks: vi.fn(),
  promoteMemoryEntry: vi.fn(),
  removeSessionLink: vi.fn(),
  supersedeAdr: vi.fn(),
  supersedeMemoryEntry: vi.fn(),
  transitionMemoryEntry: vi.fn(),
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
  });

  it('keeps supersede selections independent per row', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <MemoriaHomePage />
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
    const firstAdrRow = screen.getByText('ADR 1: ADR One').closest('article');
    const secondAdrRow = screen.getByText('ADR 2: ADR Two').closest('article');

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
});
