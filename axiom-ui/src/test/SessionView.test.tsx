import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type { ArchInputPackage, Session } from '../api/specweaver';
import { useStore } from '../store/useStore';
import { useSpecWeaverStore } from '../store/useSpecWeaverStore';
import { SessionView } from '../views/specweaver/SessionView';
import { downloadPackageExport } from '../views/specweaver/packageExport';

vi.mock('../views/specweaver/packageExport', () => ({
  downloadPackageExport: vi.fn(),
}));

const initialLoadSession = useSpecWeaverStore.getState().loadSession;
const initialUploadDocument = useSpecWeaverStore.getState().uploadDocument;
const initialDeleteDocument = useSpecWeaverStore.getState().deleteDocument;
const initialGeneratePackage = useSpecWeaverStore.getState().generatePackage;
const initialSendToArchon = useSpecWeaverStore.getState().sendToArchon;
const initialUpdateSessionTitle = useSpecWeaverStore.getState().updateSessionTitle;
const initialClearError = useSpecWeaverStore.getState().clearError;

function buildSession(overrides: Partial<Session> = {}): Session {
  return {
    id: 'sw-1',
    title: 'Discovery Session',
    status: 'ACTIVE',
    createdAt: '2026-06-01T00:00:00Z',
    updatedAt: '2026-06-01T00:00:00Z',
    archonConversationId: null,
    documents: [],
    ...overrides,
  };
}

function buildPackage(overrides: Partial<ArchInputPackage> = {}): ArchInputPackage {
  return {
    packageId: 'pkg-1',
    sessionId: 'sw-1',
    createdAt: '2026-06-01T00:00:00Z',
    readinessScore: 0.75,
    readinessLabel: 'Needs review',
    systemDescription: 'Claims intake service.',
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
    gaps: [],
    conflicts: [],
    sourceDocuments: [],
    totalRequirements: 1,
    highConfidenceCount: 1,
    inferredCount: 0,
    duplicateCount: 0,
    gapCount: 0,
    conflictCount: 0,
    ...overrides,
  };
}

function ChatStateProbe() {
  const location = useLocation();
  const state = (location.state as { prefillMessage?: string; source?: string } | null) ?? null;
  return (
    <div>
      <span>Archon chat root</span>
      <span data-testid="prefill-state">{state?.prefillMessage ?? ''}</span>
      <span data-testid="source-state">{state?.source ?? ''}</span>
    </div>
  );
}

function renderWithRoutes(initialPath = '/specweaver/sessions/sw-1') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/specweaver/sessions" element={<SessionView />} />
        <Route path="/specweaver/sessions/:sessionId" element={<SessionView />} />
        <Route path="/specweaver/sessions/:sessionId/package" element={<div>Package detail route</div>} />
        <Route path="/specweaver" element={<div>SpecWeaver sessions list</div>} />
        <Route path="/archon" element={<ChatStateProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SessionView', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useStore.setState({ token: 'jwt', username: 'User' });
    useSpecWeaverStore.setState({
      currentSession: null,
      currentPackage: null,
      error: null,
      isGenerating: false,
      generationStages: [],
      isSending: false,
      loadSession: initialLoadSession,
      uploadDocument: initialUploadDocument,
      deleteDocument: initialDeleteDocument,
      generatePackage: initialGeneratePackage,
      sendToArchon: initialSendToArchon,
      updateSessionTitle: initialUpdateSessionTitle,
      clearError: initialClearError,
    });
  });

  it('shows_not_found_state_when_session_id_is_missing', () => {
    renderWithRoutes('/specweaver/sessions');

    expect(screen.getByText('Session not found.')).toBeInTheDocument();
  });

  it('uploads_text_evidence_and_trims_payload', async () => {
    const user = userEvent.setup();
    const uploadDocument = vi.fn().mockResolvedValue(undefined);

    useSpecWeaverStore.setState({
      currentSession: buildSession(),
      uploadDocument,
      loadSession: vi.fn(),
    });

    renderWithRoutes();

    await user.type(screen.getByLabelText('Text evidence'), '  Important requirement text  ');
    await user.type(screen.getByLabelText('Source label'), '  discovery notes  ');
    await user.click(screen.getByRole('button', { name: 'Add Document' }));

    await waitFor(() => {
      expect(uploadDocument).toHaveBeenCalledWith(
        'jwt',
        'sw-1',
        null,
        'Important requirement text',
        'PLAIN_TEXT',
        'discovery notes',
      );
    });
  });

  it('renders_generation_progress_when_polling_is_active', () => {
    useSpecWeaverStore.setState({
      currentSession: buildSession({
        documents: [
          {
            id: 'doc-1',
            documentType: 'PDF',
            filename: 'notes.pdf',
            sourceLabel: 'Workshop',
            status: 'EXTRACTED',
            createdAt: '2026-06-01T00:00:00Z',
            extractedText: 'Extracted evidence text',
          },
        ],
      }),
      isGenerating: true,
      generationStages: [
        { name: 'extraction', status: 'complete' },
        { name: 'classification', status: 'running' },
        { name: 'output_formatting', status: 'pending' },
      ],
      loadSession: vi.fn(),
    });

    renderWithRoutes();

    expect(screen.getByRole('button', { name: 'Generating package…' })).toBeInTheDocument();
    expect(screen.getByText('Extraction')).toBeInTheDocument();
    expect(screen.getByText('Classification')).toBeInTheDocument();
    expect(screen.getByText('Output formatting')).toBeInTheDocument();
  });

  it('triggers_package_generation_when_extracted_evidence_exists', async () => {
    const user = userEvent.setup();
    const generatePackage = vi.fn().mockResolvedValue(undefined);

    useSpecWeaverStore.setState({
      currentSession: buildSession({
        documents: [
          {
            id: 'doc-1',
            documentType: 'PDF',
            filename: 'notes.pdf',
            sourceLabel: 'Workshop',
            status: 'EXTRACTED',
            createdAt: '2026-06-01T00:00:00Z',
            extractedText: 'Extracted evidence text',
          },
        ],
      }),
      isGenerating: false,
      generationStages: [],
      generatePackage,
      loadSession: vi.fn(),
    });

    renderWithRoutes();

    await user.click(screen.getByRole('button', { name: 'Generate Package' }));

    expect(generatePackage).toHaveBeenCalledWith('jwt', 'sw-1');
  });

  it('exports_package_and_navigates_to_archon_with_prefill_message', async () => {
    const user = userEvent.setup();
    const sendToArchon = vi.fn().mockResolvedValue('spec brief');

    useSpecWeaverStore.setState({
      currentSession: buildSession({
        documents: [
          {
            id: 'doc-1',
            documentType: 'PDF',
            filename: 'notes.pdf',
            sourceLabel: 'Workshop',
            status: 'EXTRACTED',
            createdAt: '2026-06-01T00:00:00Z',
          },
        ],
      }),
      currentPackage: buildPackage(),
      sendToArchon,
      loadSession: vi.fn(),
    });

    renderWithRoutes();

    await user.click(screen.getByRole('button', { name: 'Export as Markdown' }));
    await user.click(screen.getByRole('button', { name: 'Export as Text' }));

    expect(downloadPackageExport).toHaveBeenNthCalledWith(1, expect.any(Object), 'markdown');
    expect(downloadPackageExport).toHaveBeenNthCalledWith(2, expect.any(Object), 'text');

    await user.click(screen.getByRole('button', { name: 'Open in Archon →' }));

    expect(sendToArchon).toHaveBeenCalledWith('jwt', 'sw-1');
    expect(await screen.findByText('Archon chat root')).toBeInTheDocument();
    expect(screen.getByTestId('prefill-state')).toHaveTextContent('spec brief');
    expect(screen.getByTestId('source-state')).toHaveTextContent('specweaver');
  });

  it('shows_ownership_error_actions', async () => {
    const user = userEvent.setup();
    const clearError = vi.fn();

    useSpecWeaverStore.setState({
      currentSession: buildSession(),
      error: 'You do not have access to this SpecWeaver session.',
      clearError,
      loadSession: vi.fn(),
    });

    renderWithRoutes();

    expect(screen.getByRole('alert')).toHaveTextContent('You do not have access to this SpecWeaver session.');

    await user.click(screen.getByRole('button', { name: 'Dismiss' }));
    expect(clearError).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'Back to sessions' }));
    expect(await screen.findByText('SpecWeaver sessions list')).toBeInTheDocument();
  });
});
