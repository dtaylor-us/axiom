import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Route, Routes } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { PackageDetailView } from '../views/specweaver/PackageDetailView';
import { SessionListView } from '../views/specweaver/SessionListView';
import { useStore } from '../store/useStore';
import { useSpecWeaverStore } from '../store/useSpecWeaverStore';
import type { ArchInputPackage } from '../api/specweaver';

describe('SpecWeaver views', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('SessionListView_showsEmptyState', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => [],
    } as unknown as Response);
    useStore.setState({ token: 'jwt', username: 'User' });
    useSpecWeaverStore.setState({ sessions: [], error: null });

    render(
      <MemoryRouter>
        <SessionListView />
      </MemoryRouter>,
    );

    expect(screen.getByText('No sessions yet. Create your first session to start extracting requirements.')).toBeInTheDocument();
  });

  it('PackageDetailView_groupsRequirementsByCategory', async () => {
    const user = userEvent.setup();
    const packageData: ArchInputPackage = {
      packageId: 'pkg-1',
      sessionId: 'sw-1',
      createdAt: '2026-05-30T00:00:00Z',
      readinessScore: 0,
      readinessLabel: 'Needs review.',
      systemDescription: 'A claims intake system.',
      gaps: [],
      conflicts: [],
      sourceDocuments: [],
      totalRequirements: 1,
      highConfidenceCount: 1,
      inferredCount: 0,
      duplicateCount: 0,
      gapCount: 0,
      conflictCount: 0,
      requirements: [
        {
          requirementId: 'REQ-1',
          category: 'functional',
          statement: 'Users can submit claims.',
          type: 'FUNCTIONAL',
          confidence: 'HIGH',
          isInferred: false,
          inferenceReasoning: null,
          sourceDocumentIds: ['doc-1'],
          sourceExcerpts: ['Users submit claims through the portal.'],
          ambiguities: [],
        },
      ],
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({
        id: 'pkg-1',
        sessionId: 'sw-1',
        packageJson: JSON.stringify(packageData),
        totalRequirements: 1,
        highConfidenceCount: 1,
        inferredCount: 0,
        readinessScore: 0,
        createdAt: '2026-05-30T00:00:00Z',
        sentToArchonAt: null,
        archonConversationId: null,
      }),
    } as unknown as Response);
    useStore.setState({ token: 'jwt', username: 'User' });
    useSpecWeaverStore.setState({
      error: null,
      currentPackage: packageData,
      currentSession: {
        id: 'sw-1',
        title: 'Discovery',
        status: 'PACKAGE_READY',
        createdAt: '2026-05-30T00:00:00Z',
        updatedAt: '2026-05-30T00:00:00Z',
        archonConversationId: null,
      },
      loadSession: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/specweaver/sessions/sw-1/package']}>
        <Routes>
          <Route path="/specweaver/sessions/:sessionId/package" element={<PackageDetailView />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('tab', { name: 'Requirements' }));

    expect(screen.getByText('Functional Requirements')).toBeInTheDocument();
    expect(screen.getAllByText('Users can submit claims.')[0]).toBeInTheDocument();
  });
});
