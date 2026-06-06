import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ConflictsPanel } from '../components/specweaver/ConflictsPanel';
import { GapsPanel } from '../components/specweaver/GapsPanel';
import { ReadinessScore } from '../components/specweaver/ReadinessScore';
import type { ArchInputPackage, ClassifiedRequirement, GapArea, Session } from '../api/specweaver';
import { PackageDetailView } from '../views/specweaver/PackageDetailView';
import { useStore } from '../store/useStore';
import { useSpecWeaverStore } from '../store/useSpecWeaverStore';

const initialLoadSession = useSpecWeaverStore.getState().loadSession;
const initialSendToArchon = useSpecWeaverStore.getState().sendToArchon;

const requirements: ClassifiedRequirement[] = [
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
  {
    requirementId: 'REQ-2',
    category: 'non_functional',
    statement: 'Claims must be retained for seven years.',
    type: 'QUALITY_ATTRIBUTE',
    confidence: 'MEDIUM',
    isInferred: false,
    inferenceReasoning: null,
    sourceDocumentIds: ['doc-2'],
    sourceExcerpts: ['Retention must satisfy compliance policy.'],
    ambiguities: [],
  },
];

const gaps: GapArea[] = [
  {
    gapId: 'GAP-LOW',
    area: 'Monitoring',
    severity: 'low',
    explanation: 'Operational monitoring is not described.',
    clarificationQuestion: 'What monitoring signals are required?',
    affectedCategories: ['non_functional'],
  },
  {
    gapId: 'GAP-CRITICAL',
    area: 'Security',
    severity: 'critical',
    explanation: 'Authentication requirements are absent.',
    clarificationQuestion: 'Who can access claims?',
    affectedCategories: ['actors_and_users'],
  },
  {
    gapId: 'GAP-HIGH',
    area: 'Availability',
    severity: 'high',
    explanation: 'Availability expectations are unclear.',
    clarificationQuestion: 'What uptime target is required?',
    affectedCategories: ['non_functional'],
  },
  {
    gapId: 'GAP-MEDIUM',
    area: 'Data Migration',
    severity: 'medium',
    explanation: 'Migration scope is not defined.',
    clarificationQuestion: 'What historical records must migrate?',
    affectedCategories: ['data_considerations'],
  },
];

function packageData(overrides: Partial<ArchInputPackage> = {}): ArchInputPackage {
  return {
    packageId: 'pkg-1',
    sessionId: 'sw-1',
    createdAt: '2026-05-30T00:00:00Z',
    readinessScore: 0.42,
    readinessLabel: 'Significant review needed.',
    systemDescription: 'A claims intake system.',
    requirements,
    gaps,
    conflicts: [
      {
        conflictId: 'CONFLICT-1',
        requirementIds: ['REQ-1', 'REQ-2'],
        description: 'Submission and retention expectations point to different data handling needs.',
        interpretations: [
          'Submission speed is prioritized over long-term storage design.',
          'Retention policy drives storage and audit capabilities.',
        ],
        clarificationQuestion: 'Which policy should drive the claims data model?',
      },
    ],
    sourceDocuments: [],
    totalRequirements: requirements.length,
    highConfidenceCount: 1,
    inferredCount: 1,
    duplicateCount: 2,
    gapCount: gaps.length,
    conflictCount: 1,
    ...overrides,
  };
}

function sessionData(overrides: Partial<Session> = {}): Session {
  return {
    id: 'sw-1',
    title: 'Discovery',
    status: 'PACKAGE_READY',
    createdAt: '2026-05-30T00:00:00Z',
    updatedAt: '2026-05-30T00:00:00Z',
    archonConversationId: null,
    ...overrides,
  };
}

function renderPackageView(pkg = packageData(), session = sessionData()) {
  const sendToArchon = vi.fn().mockResolvedValue('brief text');
  useStore.setState({ token: 'jwt', username: 'User' });
  useSpecWeaverStore.setState({
    currentPackage: pkg,
    currentSession: session,
    error: null,
    isSending: false,
    loadSession: vi.fn(),
    sendToArchon,
  });

  function ChatStateProbe() {
    const location = useLocation();
    return (
      <div>
        <span>Archon chat root</span>
        <span data-testid="prefill-state">{(location.state as { prefillMessage?: string } | null)?.prefillMessage ?? ''}</span>
        <span data-testid="source-state">{(location.state as { source?: string } | null)?.source ?? ''}</span>
      </div>
    );
  }

  render(
    <MemoryRouter initialEntries={['/specweaver/sessions/sw-1/package']}>
      <Routes>
        <Route path="/specweaver/sessions/:sessionId/package" element={<PackageDetailView />} />
        <Route path="/" element={<ChatStateProbe />} />
      </Routes>
    </MemoryRouter>,
  );

  return { sendToArchon };
}

describe('ReadinessScore', () => {
  it('shows green when score is at least 0.85', () => {
    render(<ReadinessScore score={0.9} label="Ready" gapCount={0} conflictCount={0} inferredCount={0} totalCount={2} criticalGaps={0} highGaps={0} />);

    expect(screen.getByText('90%')).toHaveStyle({ color: 'var(--color-success)' });
  });

  it('shows warning when score is below 0.70', () => {
    render(<ReadinessScore score={0.6} label="Needs review" gapCount={1} conflictCount={0} inferredCount={0} totalCount={2} criticalGaps={0} highGaps={0} />);

    expect(screen.getByText('60%')).toHaveStyle({ color: 'var(--color-warning-dark)' });
  });

  it('shows error when score is below 0.30', () => {
    render(<ReadinessScore score={0.2} label="Blocked" gapCount={1} conflictCount={1} inferredCount={0} totalCount={2} criticalGaps={1} highGaps={0} />);

    expect(screen.getByText('20%')).toHaveStyle({ color: 'var(--color-error)' });
  });

  it('shows critical gap count when greater than zero', () => {
    render(<ReadinessScore score={0.8} label="Review" gapCount={1} conflictCount={0} inferredCount={0} totalCount={2} criticalGaps={2} highGaps={0} />);

    expect(screen.getByText('⚠ 2 critical gaps')).toBeInTheDocument();
  });

  it('hides critical deduction when there are no critical gaps', () => {
    render(<ReadinessScore score={0.8} label="Review" gapCount={0} conflictCount={0} inferredCount={0} totalCount={2} criticalGaps={0} highGaps={0} />);

    expect(screen.queryByText(/critical gap/)).not.toBeInTheDocument();
  });
});

describe('GapsPanel', () => {
  it('shows empty state when there are no gaps', () => {
    render(<GapsPanel gaps={[]} />);

    expect(screen.getByText('✓ No requirement gaps identified')).toBeInTheDocument();
  });

  it('shows gap count in title', () => {
    render(<GapsPanel gaps={gaps} />);

    expect(screen.getByText('Requirement Gaps (4)')).toBeInTheDocument();
  });

  it('sorts critical gaps before high before medium', () => {
    const { container } = render(<GapsPanel gaps={gaps} />);

    const areas = Array.from(container.querySelectorAll('.gap-area')).map((element) => element.textContent);
    expect(areas).toEqual(['Security', 'Availability', 'Data Migration', 'Monitoring']);
  });

  it('shows clarification question for each gap', () => {
    render(<GapsPanel gaps={gaps} />);

    expect(screen.getByText('Who can access claims?')).toBeInTheDocument();
    expect(screen.getByText('What uptime target is required?')).toBeInTheDocument();
  });

  it('shows severity badge for each gap', () => {
    render(<GapsPanel gaps={gaps} />);

    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
  });
});

describe('ConflictsPanel', () => {
  it('shows empty state when there are no conflicts', () => {
    render(<ConflictsPanel conflicts={[]} requirements={requirements} />);

    expect(screen.getByText('✓ No requirement conflicts detected')).toBeInTheDocument();
  });

  it('shows conflict count in title', () => {
    render(<ConflictsPanel conflicts={packageData().conflicts} requirements={requirements} />);

    expect(screen.getByText('Conflicts (1)')).toBeInTheDocument();
  });

  it('shows conflicting requirement statements', () => {
    render(<ConflictsPanel conflicts={packageData().conflicts} requirements={requirements} />);

    expect(screen.getByText('Users can submit claims.')).toBeInTheDocument();
    expect(screen.getByText('Claims must be retained for seven years.')).toBeInTheDocument();
  });

  it('shows clarification question', () => {
    render(<ConflictsPanel conflicts={packageData().conflicts} requirements={requirements} />);

    expect(screen.getByText('Which policy should drive the claims data model?')).toBeInTheDocument();
  });

  it('shows interpretations in collapsible details', () => {
    render(<ConflictsPanel conflicts={packageData().conflicts} requirements={requirements} />);

    expect(screen.getByText('Possible interpretations')).toBeInTheDocument();
    expect(screen.getByText('Retention policy drives storage and audit capabilities.')).toBeInTheDocument();
  });
});

describe('PackageDetailView Phase 1b', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useSpecWeaverStore.setState({
      currentPackage: null,
      currentSession: null,
      error: null,
      isSending: false,
      loadSession: initialLoadSession,
      sendToArchon: initialSendToArchon,
    });
  });

  it('shows four tabs: Overview, Requirements, Gaps, Conflicts', () => {
    renderPackageView();

    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Requirements' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Gaps/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Conflicts/ })).toBeInTheDocument();
  });

  it('shows gap count badge on Gaps tab when gaps exist', () => {
    renderPackageView();

    expect(screen.getByRole('tab', { name: /Gaps4/ })).toBeInTheDocument();
  });

  it('shows conflict count badge on Conflicts tab', () => {
    renderPackageView();

    expect(screen.getByRole('tab', { name: /Conflicts1/ })).toBeInTheDocument();
  });

  it('shows readiness warning when score is below 0.5', () => {
    renderPackageView();

    expect(screen.getByText(/This package has significant gaps or conflicts/)).toBeInTheDocument();
  });

  it('showsPreparingBriefLabelWhileSending', () => {
    useStore.setState({ token: 'jwt', username: 'User' });
    useSpecWeaverStore.setState({
      currentPackage: packageData({ readinessScore: 0.8 }),
      currentSession: sessionData(),
      error: null,
      isSending: true,
      loadSession: vi.fn(),
      sendToArchon: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/specweaver/sessions/sw-1/package']}>
        <Routes>
          <Route path="/specweaver/sessions/:sessionId/package" element={<PackageDetailView />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: 'Preparing brief...' })).toBeInTheDocument();
  });

  it('navigatesToArchonRootWithPrefillStateOnSend', async () => {
    const user = userEvent.setup();
    const { sendToArchon } = renderPackageView(packageData({ readinessScore: 0.8 }));

    await user.click(screen.getByRole('button', { name: 'Open in Archon →' }));

    expect(sendToArchon).toHaveBeenCalledWith('jwt', 'sw-1');
    expect(await screen.findByText('Archon chat root')).toBeInTheDocument();
    expect(screen.getByTestId('prefill-state')).toHaveTextContent('brief text');
    expect(screen.getByTestId('source-state')).toHaveTextContent('specweaver');
  });
});
