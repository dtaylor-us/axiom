import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkshopView } from '../views/workshop/WorkshopView';
import { useStore } from '../store/useStore';

// Mock all workshop API calls so no network requests are made.
vi.mock('../api/workshop', () => ({
  createWorkshopSession: vi.fn(),
  submitWorkshopTurn: vi.fn(),
  getWorkshopSession: vi.fn(),
  getWorkshopAttributes: vi.fn(),
  getWorkshopScenarios: vi.fn(),
  getWorkshopMessages: vi.fn(),
  sendWorkshopToPipeline: vi.fn(),
  assessGenerationReadiness: vi.fn(),
  generateAttributes: vi.fn(),
  getUtilityTree: vi.fn(),
  getImplications: vi.fn(),
  completeWorkshopSession: vi.fn(),
  listWorkshopSessions: vi.fn(),
}));

// Mock child components that have their own heavy dependencies.
vi.mock('../views/workshop/components/ProgressTracker', () => ({
  ProgressTracker: ({ currentPhase }: { currentPhase: string }) => (
    <div data-testid="mock-progress-tracker">{currentPhase}</div>
  ),
}));
vi.mock('../views/workshop/components/ConversationThread', () => ({
  ConversationThread: () => <div data-testid="mock-conversation-thread" />,
}));
vi.mock('../views/workshop/components/InputPanel', () => ({
  InputPanel: ({
    onSubmit,
    disabled,
  }: {
    onSubmit: (v: string) => void;
    disabled: boolean;
  }) => (
    <button
      data-testid="mock-input-panel"
      disabled={disabled}
      onClick={() => onSubmit('test input')}
    >
      Submit
    </button>
  ),
}));
vi.mock('../views/workshop/components/GapIndicator', () => ({
  GapIndicator: () => <div data-testid="mock-gap-indicator" />,
}));
vi.mock('../views/workshop/components/AttributePanel', () => ({
  AttributePanel: () => <div data-testid="mock-attribute-panel" />,
}));
vi.mock('../views/workshop/components/GeneratePanel', () => ({
  GeneratePanel: () => <div data-testid="mock-generate-panel" />,
}));
vi.mock('../views/workshop/components/ReadinessModal', () => ({
  ReadinessModal: () => null,
}));
vi.mock('../views/workshop/components/ScenarioCard', () => ({
  ScenarioCard: () => <div data-testid="mock-scenario-card" />,
}));
vi.mock('../components/StructuredData', () => ({
  MarkdownExportActions: () => null,
}));

import { createWorkshopSession, getWorkshopSession, getWorkshopAttributes, getWorkshopScenarios, getWorkshopMessages, getUtilityTree, getImplications } from '../api/workshop';

// jsdom does not implement matchMedia; provide a minimal stub so the
// useMinWidthLg hook inside WorkshopView does not throw.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
});

const DEFAULT_PROPS = {
  onNavigateToChat: vi.fn(),
  initialSessionId: null as string | null,
  onSessionCreated: vi.fn(),
};

describe('WorkshopView — system name entry screen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStore.setState({ token: 'jwt-test' });
  });

  it('rendersWorkshopViewContainer', () => {
    render(<WorkshopView {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('workshop-view')).toBeInTheDocument();
  });

  it('rendersSystemNameInputWhenNoSession', () => {
    render(<WorkshopView {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('system-name-input')).toBeInTheDocument();
  });

  it('rendersStartWorkshopButton', () => {
    render(<WorkshopView {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('start-workshop-btn')).toBeInTheDocument();
  });

  it('startWorkshopButtonIsDisabledWhenInputIsEmpty', () => {
    render(<WorkshopView {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('start-workshop-btn')).toBeDisabled();
  });

  it('startWorkshopButtonEnablesWhenInputHasText', async () => {
    const user = userEvent.setup();
    render(<WorkshopView {...DEFAULT_PROPS} />);

    await user.type(screen.getByTestId('system-name-input'), 'Payment Service');

    expect(screen.getByTestId('start-workshop-btn')).toBeEnabled();
  });

  it('rendersQualityAttributeWorkshopHeading', () => {
    render(<WorkshopView {...DEFAULT_PROPS} />);
    expect(screen.getByText('Quality Attribute Workshop')).toBeInTheDocument();
  });

  it('rendersSeqMethodologyLabel', () => {
    render(<WorkshopView {...DEFAULT_PROPS} />);
    expect(screen.getByText('SEI QAW methodology')).toBeInTheDocument();
  });
});

describe('WorkshopView — session creation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStore.setState({ token: 'jwt-test' });
  });

  it('callsCreateWorkshopSessionWithSystemName', async () => {
    vi.mocked(createWorkshopSession).mockResolvedValue({
      sessionId: 'ws-new',
      systemName: 'Payment Service',
    } as never);

    const user = userEvent.setup();
    render(<WorkshopView {...DEFAULT_PROPS} />);

    await user.type(screen.getByTestId('system-name-input'), 'Payment Service');
    await user.click(screen.getByTestId('start-workshop-btn'));

    await waitFor(() =>
      expect(createWorkshopSession).toHaveBeenCalledWith('jwt-test', 'Payment Service'),
    );
  });

  it('callsOnSessionCreatedWithNewSessionId', async () => {
    vi.mocked(createWorkshopSession).mockResolvedValue({
      sessionId: 'ws-new',
      systemName: 'Payment Service',
    } as never);

    const onSessionCreated = vi.fn();
    const user = userEvent.setup();
    render(<WorkshopView {...DEFAULT_PROPS} onSessionCreated={onSessionCreated} />);

    await user.type(screen.getByTestId('system-name-input'), 'Payment Service');
    await user.click(screen.getByTestId('start-workshop-btn'));

    await waitFor(() => expect(onSessionCreated).toHaveBeenCalledWith('ws-new'));
  });

  it('displaysErrorWhenSessionCreationFails', async () => {
    vi.mocked(createWorkshopSession).mockRejectedValue(new Error('Server error'));

    const user = userEvent.setup();
    render(<WorkshopView {...DEFAULT_PROPS} />);

    await user.type(screen.getByTestId('system-name-input'), 'Payment Service');
    await user.click(screen.getByTestId('start-workshop-btn'));

    await waitFor(() => expect(screen.getByText('Server error')).toBeInTheDocument());
  });

  it('submitsOnEnterKeyPress', async () => {
    vi.mocked(createWorkshopSession).mockResolvedValue({
      sessionId: 'ws-enter',
      systemName: 'Order Service',
    } as never);

    const user = userEvent.setup();
    render(<WorkshopView {...DEFAULT_PROPS} />);

    await user.type(screen.getByTestId('system-name-input'), 'Order Service{Enter}');

    await waitFor(() =>
      expect(createWorkshopSession).toHaveBeenCalledWith('jwt-test', 'Order Service'),
    );
  });
});

describe('WorkshopView — historical session load', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStore.setState({ token: 'jwt-test' });
  });

  it('loadsExistingSessionWhenInitialSessionIdIsProvided', async () => {
    vi.mocked(getWorkshopSession).mockResolvedValue({
      sessionId: 'ws-existing',
      systemName: 'Existing App',
      phase: 'ATTRIBUTE_ELICITATION',
      turnNumber: 5,
      hasSufficientAttributes: true,
      gapSummary: { total: 3, filled: 2, completionPct: 66, inProgressCount: 0, openGaps: [] },
    } as never);
    vi.mocked(getWorkshopMessages).mockResolvedValue([]);
    vi.mocked(getWorkshopAttributes).mockResolvedValue([]);
    vi.mocked(getWorkshopScenarios).mockResolvedValue([]);
    vi.mocked(getUtilityTree).mockRejectedValue({ status: 404 });
    vi.mocked(getImplications).mockResolvedValue([]);

    render(<WorkshopView {...DEFAULT_PROPS} initialSessionId="ws-existing" />);

    await waitFor(() => expect(getWorkshopSession).toHaveBeenCalledWith('jwt-test', 'ws-existing'));
  });

  it('rendersLoadFailureScreenWithRetryButtonOnError', async () => {
    vi.mocked(getWorkshopSession).mockRejectedValue(new Error('Not found'));

    render(<WorkshopView {...DEFAULT_PROPS} initialSessionId="ws-missing" />);

    await waitFor(() =>
      expect(screen.getByText('Failed to load session')).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
  });

  it('retriggersLoadOnRetryButtonClick', async () => {
    vi.mocked(getWorkshopSession)
      .mockRejectedValueOnce(new Error('Transient error'))
      .mockResolvedValue({
        sessionId: 'ws-retry',
        systemName: 'Retry App',
        phase: 'CONTEXT_SETTING',
        turnNumber: 0,
        hasSufficientAttributes: false,
        gapSummary: { total: 0, filled: 0, completionPct: 0, inProgressCount: 0, openGaps: [] },
      } as never);
    vi.mocked(getWorkshopMessages).mockResolvedValue([]);
    vi.mocked(getWorkshopAttributes).mockResolvedValue([]);
    vi.mocked(getWorkshopScenarios).mockResolvedValue([]);
    vi.mocked(getUtilityTree).mockRejectedValue({ status: 404 });
    vi.mocked(getImplications).mockResolvedValue([]);

    const user = userEvent.setup();
    render(<WorkshopView {...DEFAULT_PROPS} initialSessionId="ws-retry" />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Try Again' }));

    await waitFor(() => expect(getWorkshopSession).toHaveBeenCalledTimes(2));
  });
});
