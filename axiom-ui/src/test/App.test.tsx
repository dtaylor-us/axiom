import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { useStore } from '../store/useStore';
import { getToken } from '../api/auth';
import { getPipelineStatus, getRunStatus, reattachStream } from '../api/chat';
import { getSessionMessages } from '../api/sessions';
import { getSessions as getSpecWeaverSessions } from '../api/specweaver';
import { listReviewSessions } from '../api/lens';
import { useSpecWeaverStore } from '../store/useSpecWeaverStore';

vi.mock('../api/sessions', () => ({
  listSessions: vi.fn().mockResolvedValue([]),
  getSessionMessages: vi.fn().mockResolvedValue([]),
}));

vi.mock('../api/auth', () => ({
  getToken: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  requestPasswordReset: vi.fn(),
  validateResetToken: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));

vi.mock('../api/chat', () => ({
  getRunStatus: vi.fn().mockResolvedValue(null),
  getPipelineStatus: vi.fn().mockResolvedValue(null),
  reattachStream: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../api/specweaver', () => ({
  createSession: vi.fn(),
  deleteDocument: vi.fn(),
  generatePackage: vi.fn(),
  getPackage: vi.fn(),
  getSession: vi.fn(),
  getSessions: vi.fn().mockResolvedValue([]),
  sendToArchon: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock('../api/lens', () => ({
  createReviewSession: vi.fn(),
  listReviewSessions: vi.fn().mockResolvedValue([]),
}));

/* Mock auth gate */
vi.mock('../views/LoginView', () => ({
  LoginView: () => <div data-testid="login-view">Login Mock</div>,
}));
vi.mock('../views/ForgotPasswordView', () => ({
  ForgotPasswordView: () => <div data-testid="forgot-password-view">Forgot Mock</div>,
}));
vi.mock('../views/ResetPasswordView', () => ({
  ResetPasswordView: () => <div data-testid="reset-password-view">Reset Mock</div>,
}));

/* Mock views */
vi.mock('../views/AxiomHomePage', () => ({
  AxiomHomePage: () => <div data-testid="axiom-home-page">Axiom Home Mock</div>,
}));
vi.mock('../views/archon/ArchonHomePage', () => ({
  ArchonHomePage: () => <div data-testid="archon-home-page">Archon Home Mock</div>,
}));
vi.mock('../views/specweaver/SpecWeaverHomePage', () => ({
  SpecWeaverHomePage: () => <div data-testid="specweaver-home-page">SpecWeaver Home Mock</div>,
}));
vi.mock('../views/lens/LensHomePage', () => ({
  LensHomePage: () => <div data-testid="lens-home-page">Lens Home Mock</div>,
}));
vi.mock('../views/lens/LensReviewPage', () => ({
  LensReviewPage: () => <div data-testid="lens-review-page">Lens Review Mock</div>,
}));
vi.mock('../views/ChatView', () => ({
  ChatView: () => <div data-testid="chat-view">Chat Mock</div>,
}));
vi.mock('../views/ArchitectureView', () => ({
  ArchitectureView: () => <div data-testid="architecture-view">Arch Mock</div>,
}));
vi.mock('../views/GovernanceView', () => ({
  GovernanceView: () => <div data-testid="governance-view">Gov Mock</div>,
}));
vi.mock('../views/specweaver/SessionListView', () => ({
  SessionListView: () => <div data-testid="specweaver-session-list-view">SpecWeaver List Mock</div>,
}));
vi.mock('../views/specweaver/SessionView', () => ({
  SessionView: () => <div data-testid="specweaver-session-view">SpecWeaver Session Mock</div>,
}));
vi.mock('../views/specweaver/PackageDetailView', () => ({
  PackageDetailView: () => <div data-testid="specweaver-package-view">SpecWeaver Package Mock</div>,
}));
vi.mock('../components/StageProgress', () => ({
  StageProgress: () => <div data-testid="stage-progress">Stages Mock</div>,
}));

function resetStore() {
  useStore.setState({ token: null, username: null });
  useStore.getState().resetConversation();
  useSpecWeaverStore.setState({
    sessions: [],
    currentSession: null,
    currentPackage: null,
    isGenerating: false,
    isSending: false,
    error: null,
  });
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
    (getToken as unknown as ReturnType<typeof vi.fn>).mockResolvedValue('jwt-rehydrated');
    (getRunStatus as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(null);
    (getPipelineStatus as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(null);
    (reattachStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    window.history.pushState({}, '', '/');
    window.localStorage.removeItem('archon.auth');
    window.localStorage.removeItem('archon.lastConversationId');
    window.localStorage.removeItem('archon.lastView');
  });

  it('showsPlatformHomeWhenNotAuthenticatedAtRoot', () => {
    render(<App />);
    expect(screen.getByTestId('axiom-home-page')).toBeInTheDocument();
  });

  it('showsForgotPasswordRouteWhenUnauthenticated', () => {
    window.history.pushState({}, '', '/forgot-password');
    render(<App />);
    expect(screen.getByTestId('forgot-password-view')).toBeInTheDocument();
  });

  it('showsResetPasswordRouteWhenUnauthenticated', () => {
    window.history.pushState({}, '', '/reset-password?token=abc');
    render(<App />);
    expect(screen.getByTestId('reset-password-view')).toBeInTheDocument();
  });

  it('showsAppShellWhenTokenExists', () => {
    useStore.setState({ token: 'jwt', username: 'Alice' });
    render(<App />);
    expect(screen.getByTestId('app-shell')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-home-page')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('pillar-nav')).toBeInTheDocument();
    expect(screen.queryByTestId('login-view')).not.toBeInTheDocument();
  });

  it('showsSpecWeaverActionsAndHistoryOnSpecWeaverRoute', async () => {
    useStore.setState({ token: 'jwt', username: 'Alice' });
    (getSpecWeaverSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'sw-1',
        title: 'Billing extraction',
        status: 'ACTIVE',
        createdAt: '2026-05-30T00:00:00Z',
        updatedAt: '2026-05-30T00:00:00Z',
        archonConversationId: null,
      },
    ]);
    window.history.pushState({}, '', '/specweaver');

    render(<App />);

    await waitFor(() => {
      expect(getSpecWeaverSessions).toHaveBeenCalledWith('jwt');
    });

    expect(screen.getByTestId('new-specweaver-session')).toBeInTheDocument();
    expect(screen.queryByTestId('new-chat')).not.toBeInTheDocument();
    expect(screen.getByTestId('specweaver-history-sw-1')).toBeInTheDocument();
    expect(screen.getByTestId('specweaver-home-page')).toBeInTheDocument();
  });

  it('showsSpecWeaverActiveSessionNavigationWhenSessionIsOpen', async () => {
    useStore.setState({ token: 'jwt', username: 'Alice' });
    (getSpecWeaverSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'sw-1',
        title: 'Billing extraction',
        status: 'PACKAGE_READY',
        createdAt: '2026-05-30T00:00:00Z',
        updatedAt: '2026-05-30T00:00:00Z',
        archonConversationId: null,
      },
    ]);
    window.history.pushState({}, '', '/specweaver/sessions/sw-1');

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('nav-specweaver-session')).toBeInTheDocument();
    });
    expect(screen.getByTestId('nav-specweaver-sessions')).toHaveClass('sidebar-pillar-active--specweaver', 'sidebar-active-nav');
    expect(screen.getByTestId('nav-specweaver-session')).toHaveClass('sidebar-pillar-active--specweaver', 'sidebar-active-nav');
    expect(screen.getByTestId('nav-specweaver-package')).toBeInTheDocument();
    expect(screen.getByTestId('specweaver-history-sw-1')).toHaveClass('sidebar-pillar-active--specweaver', 'sidebar-active-item');
    expect(screen.getByTestId('specweaver-session-view')).toBeInTheDocument();
  });

  it('usesLensPillarColorForActiveReviewNavigationAndHistory', async () => {
    useStore.setState({ token: 'jwt', username: 'Alice' });
    (listReviewSessions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'lens-1',
        title: 'Checkout review',
        status: 'IN_REVIEW',
        createdAt: '2026-05-30T00:00:00Z',
        updatedAt: '2026-05-30T00:00:00Z',
      },
    ]);
    window.history.pushState({}, '', '/lens/sessions/lens-1');

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('lens-history-lens-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('nav-lens-reviews')).toHaveClass('sidebar-pillar-active--lens', 'sidebar-active-nav');
    expect(screen.getByTestId('lens-history-lens-1')).toHaveClass('sidebar-pillar-active--lens', 'sidebar-active-item');
    expect(screen.getByTestId('lens-review-page')).toBeInTheDocument();
  });

  it('showsUsernameInSidebar', () => {
    useStore.setState({ token: 'jwt', username: 'Alice' });
    render(<App />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  it('hidesContextNavWithoutConversation', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: null });
    render(<App />);
    expect(screen.queryByTestId('nav-architecture')).not.toBeInTheDocument();
    expect(screen.queryByTestId('nav-governance')).not.toBeInTheDocument();
  });

  it('showsContextNavWithConversation', () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1' });
    render(<App />);
    expect(screen.getByTestId('nav-architecture')).toBeInTheDocument();
    expect(screen.getByTestId('nav-governance')).toBeInTheDocument();
  });

  it('switchesToArchitectureView', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1' });
    window.history.pushState({}, '', '/archon/chat');
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByTestId('nav-architecture'));
    expect(screen.getByTestId('architecture-view')).toBeInTheDocument();
  });

  it('switchesToGovernanceView', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1' });
    window.history.pushState({}, '', '/archon/chat');
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByTestId('nav-governance'));
    expect(screen.getByTestId('governance-view')).toBeInTheDocument();
  });

  it('newChatButtonResetsConversation', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1', streamingText: 'hello' });
    window.history.pushState({}, '', '/archon/chat');
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByTestId('nav-architecture'));
    expect(screen.getByTestId('architecture-view')).toBeInTheDocument();
    await user.click(screen.getByTestId('new-chat'));
    expect(useStore.getState().conversationId).toBeNull();
    expect(useStore.getState().streamingText).toBe('');
    expect(screen.getByTestId('chat-view')).toBeInTheDocument();
  });

  it('signOutClearsAuthAndShowsLogin', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1', streamingText: 'hello' });
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByTestId('nav-logout'));
    await waitFor(() => {
      expect(screen.getByTestId('axiom-home-page')).toBeInTheDocument();
    });
    expect(useStore.getState().token).toBeNull();
    expect(useStore.getState().conversationId).toBeNull();
  });

  it('showsPipelineWhileStreamingAndStagesActive', () => {
    const stages = useStore.getState().stages.map((s, idx) =>
      idx === 0 ? { ...s, status: 'running' as const } : s,
    );
    useStore.setState({ token: 'jwt', username: 'User', isStreaming: true, stages });
    render(<App />);
    expect(screen.getByTestId('stage-progress')).toBeInTheDocument();
  });

  it('hidesPipelineAfterAllStagesCompleteAndNotStreaming', () => {
    const stages = useStore.getState().stages.map((s) => ({ ...s, status: 'complete' as const }));
    useStore.setState({ token: 'jwt', username: 'User', isStreaming: false, stages });
    render(<App />);
    expect(screen.queryByTestId('stage-progress')).not.toBeInTheDocument();
  });

  it('restoresLastConversationOnReloadWhenPersisted', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: null });
    window.localStorage.setItem('archon.lastConversationId', 'conv-123');
    (getSessionMessages as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { role: 'USER', content: 'hi' },
    ]);

    render(<App />);

    await waitFor(() => {
      expect(getSessionMessages).toHaveBeenCalledWith('conv-123', 'jwt');
    });
    await waitFor(() => {
      expect(useStore.getState().conversationId).toBe('conv-123');
    });
  });

  it('retries route hydration when a redirected conversation is briefly empty', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: null });
    window.history.pushState({}, '', '/conversations/conv-456');
    (getSessionMessages as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ role: 'USER', content: 'seeded brief' }]);

    render(<App />);

    await waitFor(() => {
      expect(getSessionMessages).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(useStore.getState().conversationId).toBe('conv-456');
      expect(useStore.getState().messages).toEqual([
        { role: 'USER', content: 'seeded brief' },
      ]);
    });
  });

  it('forces chat view on conversation route when last persisted view was specweaver', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: null });
    window.localStorage.setItem('archon.lastView', 'specweaver');
    window.history.pushState({}, '', '/conversations/conv-789');

    (getSessionMessages as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => undefined),
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });
  });

  it('doesNotForceChatAfterSelectingGovernanceOnConversationRoute', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'conv-999' });
    window.history.pushState({}, '', '/conversations/conv-999');

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('nav-governance'));

    expect(screen.getByTestId('governance-view')).toBeInTheDocument();
    expect(screen.queryByTestId('chat-view')).not.toBeInTheDocument();
  });

  it('restoresLastViewFromLocalStorage', () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1' });
    window.history.pushState({}, '', '/archon/chat');
    window.localStorage.setItem('archon.lastView', 'architecture');
    render(<App />);
    expect(screen.getByTestId('chat-view')).toBeInTheDocument();
  });

  it('rehydratesAuthFromPersistedUsernameOnReload', async () => {
    useStore.setState({ token: null, username: 'Guest' });

    render(<App />);

    await waitFor(() => {
      expect(getToken).toHaveBeenCalledWith('Guest');
    });
    await waitFor(() => {
      expect(useStore.getState().token).toBe('jwt-rehydrated');
    });
    expect(screen.getByTestId('app-shell')).toBeInTheDocument();
  });

  it('restoresInFlightRunStateAfterReload', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1' });
    (getRunStatus as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      runId: 'run-1',
      conversationId: 'c1',
      status: 'RUNNING',
      lastStageCompleted: 'scenario_modeling',
      startedAt: '2026-05-30T00:00:00Z',
      completedAt: null,
      governanceScore: null,
      governanceConfidence: null,
      hasGaps: null,
      gapSummary: null,
      errorStage: null,
      errorMessage: null,
      eventCount: 1,
    });

    render(<App />);

    await waitFor(() => {
      expect(getRunStatus).toHaveBeenCalledWith('c1', 'jwt');
    });
    await waitFor(() => {
      expect(useStore.getState().canReattach).toBe(true);
      expect(useStore.getState().runId).toBe('run-1');
      expect(useStore.getState().lastStageCompleted).toBe('scenario_modeling');
    });
  });

  it('fetchesPipelineStatusOnConversationMount', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c-pipe' });
    window.history.pushState({}, '', '/conversations/c-pipe');
    (getPipelineStatus as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      runId: 'run-10',
      status: 'COMPLETED',
      lastStageCompleted: 'requirement_parsing',
      completedStages: ['requirement_parsing'],
      activeStage: null,
      events: [
        {
          type: 'STAGE_COMPLETE',
          stage: 'requirement_parsing',
          sequenceNum: 1,
          emittedAt: '2026-06-01T00:00:00Z',
          payload: '{"type":"STAGE_COMPLETE","stage":"requirement_parsing","payload":{}}',
        },
      ],
      governanceScore: 70,
      hasGaps: false,
    });

    render(<App />);

    await waitFor(() => {
      expect(getPipelineStatus).toHaveBeenCalledWith('c-pipe', 'jwt');
    });
  });

  it('marksCompletedStagesBeforeSseWhenPipelineStatusExists', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c-replay' });
    window.history.pushState({}, '', '/conversations/c-replay');
    (getPipelineStatus as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      runId: 'run-11',
      status: 'COMPLETED',
      lastStageCompleted: 'requirement_challenge',
      completedStages: ['requirement_parsing', 'requirement_challenge'],
      activeStage: null,
      events: [
        {
          type: 'STAGE_COMPLETE',
          stage: 'requirement_parsing',
          sequenceNum: 1,
          emittedAt: '2026-06-01T00:00:00Z',
          payload: '{"type":"STAGE_COMPLETE","stage":"requirement_parsing","payload":{}}',
        },
        {
          type: 'STAGE_COMPLETE',
          stage: 'requirement_challenge',
          sequenceNum: 2,
          emittedAt: '2026-06-01T00:00:02Z',
          payload: '{"type":"STAGE_COMPLETE","stage":"requirement_challenge","payload":{}}',
        },
      ],
      governanceScore: 71,
      hasGaps: false,
    });

    render(<App />);

    await waitFor(() => {
      const stages = useStore.getState().stages;
      expect(stages.find((s) => s.name === 'requirement_parsing')?.status).toBe('complete');
      expect(stages.find((s) => s.name === 'requirement_challenge')?.status).toBe('complete');
    });
  });

  it('skipsSseAttachWhenPipelineAlreadyCompleted', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c-done' });
    window.history.pushState({}, '', '/conversations/c-done');
    (getPipelineStatus as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      runId: 'run-done',
      status: 'COMPLETED',
      lastStageCompleted: 'architecture_review',
      completedStages: ['architecture_review'],
      activeStage: null,
      events: [
        {
          type: 'STAGE_COMPLETE',
          stage: 'architecture_review',
          sequenceNum: 40,
          emittedAt: '2026-06-01T00:00:00Z',
          payload: '{"type":"STAGE_COMPLETE","stage":"architecture_review","payload":{}}',
        },
      ],
      governanceScore: 92,
      hasGaps: false,
    });

    render(<App />);

    await waitFor(() => {
      expect(getPipelineStatus).toHaveBeenCalledWith('c-done', 'jwt');
    });
    expect(reattachStream).not.toHaveBeenCalled();
  });

  it('attachesSseWhenPipelineStatusIsRunning', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c-running' });
    window.history.pushState({}, '', '/conversations/c-running');
    (getPipelineStatus as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      runId: 'run-live',
      status: 'RUNNING',
      lastStageCompleted: 'requirement_parsing',
      completedStages: ['requirement_parsing'],
      activeStage: 'requirement_challenge',
      events: [
        {
          type: 'STAGE_COMPLETE',
          stage: 'requirement_parsing',
          sequenceNum: 1,
          emittedAt: '2026-06-01T00:00:00Z',
          payload: '{"type":"STAGE_COMPLETE","stage":"requirement_parsing","payload":{}}',
        },
      ],
      governanceScore: null,
      hasGaps: false,
    });

    render(<App />);

    await waitFor(() => {
      expect(reattachStream).toHaveBeenCalled();
    });
    expect(reattachStream).toHaveBeenCalledWith(
      'c-running',
      'jwt',
      expect.any(Function),
      'run-live',
    );
  });
});
