import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { useStore } from '../store/useStore';
import { getSessionMessages } from '../api/sessions';

vi.mock('../api/sessions', () => ({
  listSessions: vi.fn().mockResolvedValue([]),
  getSessionMessages: vi.fn().mockResolvedValue([]),
}));

/* Mock auth gate */
vi.mock('../views/LoginView', () => ({
  LoginView: () => <div data-testid="login-view">Login Mock</div>,
}));

/* Mock views */
vi.mock('../views/HomeView', () => ({
  HomeView: () => <div data-testid="home-view">Home Mock</div>,
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
vi.mock('../components/StageProgress', () => ({
  StageProgress: () => <div data-testid="stage-progress">Stages Mock</div>,
}));

function resetStore() {
  useStore.setState({ token: null, username: null });
  useStore.getState().resetConversation();
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
    window.localStorage.removeItem('archon.auth');
    window.localStorage.removeItem('archon.lastConversationId');
    window.localStorage.removeItem('archon.lastView');
  });

  it('showsLoginViewWhenNotAuthenticated', () => {
    render(<App />);
    expect(screen.getByTestId('login-view')).toBeInTheDocument();
  });

  it('showsAppShellWhenTokenExists', () => {
    useStore.setState({ token: 'jwt', username: 'Alice' });
    render(<App />);
    expect(screen.getByTestId('app-shell')).toBeInTheDocument();
    expect(screen.getByTestId('home-view')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.queryByTestId('login-view')).not.toBeInTheDocument();
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
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByTestId('nav-architecture'));
    expect(screen.getByTestId('architecture-view')).toBeInTheDocument();
  });

  it('switchesToGovernanceView', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1' });
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByTestId('nav-governance'));
    expect(screen.getByTestId('governance-view')).toBeInTheDocument();
  });

  it('newChatButtonResetsConversation', async () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1', streamingText: 'hello' });
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
      expect(screen.getByTestId('login-view')).toBeInTheDocument();
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

  it('restoresLastViewFromLocalStorage', () => {
    useStore.setState({ token: 'jwt', username: 'User', conversationId: 'c1' });
    window.localStorage.setItem('archon.lastView', 'architecture');
    render(<App />);
    expect(screen.getByTestId('architecture-view')).toBeInTheDocument();
  });
});
