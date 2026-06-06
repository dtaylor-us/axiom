import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSSEStream } from '../hooks/useSSEStream';
import { useStore } from '../store/useStore';

// Mock all chat API functions used by the hook.
vi.mock('../api/chat', () => ({
  streamChat: vi.fn(),
  getRunStatus: vi.fn(),
  reattachStream: vi.fn(),
}));

import { streamChat, getRunStatus, reattachStream } from '../api/chat';
const mockStreamChat = vi.mocked(streamChat);
const mockGetRunStatus = vi.mocked(getRunStatus);
const mockReattachStream = vi.mocked(reattachStream);

describe('useSSEStream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStore.setState({
      token: 'jwt-token',
      conversationId: null,
      isStreaming: false,
      error: null,
      streamingText: '',
    });
  });

  it('setsErrorWhenNotAuthenticated', async () => {
    useStore.setState({ token: null });
    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.send('hello');
    });

    expect(useStore.getState().error).toBe('Not authenticated');
    expect(mockStreamChat).not.toHaveBeenCalled();
  });

  it('callsStreamChatWithCorrectArgs', async () => {
    mockStreamChat.mockResolvedValue(undefined);
    useStore.setState({ token: 'jwt', conversationId: 'c1' });

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.send('build me a system');
    });

    expect(mockStreamChat).toHaveBeenCalledWith(
      'jwt',
      'build me a system',
      'c1',
      expect.any(String),
      expect.any(Function),
      expect.any(AbortSignal),
    );
  });

  it('setsStreamingTrueWhileRunning', async () => {
    let resolveStream: () => void;
    mockStreamChat.mockImplementation(
      () => new Promise<void>((r) => (resolveStream = r)),
    );

    const { result } = renderHook(() => useSSEStream());

    let sendPromise: Promise<void>;
    act(() => {
      sendPromise = result.current.send('test');
    });

    // send() performs an async preflight run-status check before startStream.
    await act(async () => {
      await Promise.resolve();
    });

    expect(useStore.getState().isStreaming).toBe(true);

    await act(async () => {
      resolveStream!();
      await sendPromise!;
    });

    expect(useStore.getState().isStreaming).toBe(false);
  });

  it('setsErrorOnStreamFailure', async () => {
    mockStreamChat.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.send('test');
    });

    expect(useStore.getState().error).toBe('Network error');
  });

  it('abort_stopsStreaming', () => {
    const { result } = renderHook(() => useSSEStream());

    act(() => {
      result.current.abort();
    });

    expect(useStore.getState().isStreaming).toBe(false);
  });

  it('pollsRunStatusWhenStreamFailsWithConversationId', async () => {
    mockGetRunStatus.mockResolvedValueOnce(null);
    mockStreamChat.mockRejectedValue(new Error('Proxy disconnect'));
    mockGetRunStatus.mockResolvedValueOnce({
      runId: 'run-abc',
      conversationId: 'conv-poll',
      status: 'RUNNING',
      lastStageCompleted: 'requirement_parsing',
      startedAt: '2024-01-01T00:00:00Z',
      eventCount: 0,
    });
    useStore.setState({ token: 'jwt', conversationId: 'conv-poll' });

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.send('test');
    });

    expect(mockGetRunStatus).toHaveBeenCalledWith('conv-poll', 'jwt');
    expect(useStore.getState().runId).toBe('run-abc');
    expect(useStore.getState().canReattach).toBe(true);
  });

  it('reattachesWhenRunAlreadyActiveBeforeSubmit', async () => {
    mockGetRunStatus.mockResolvedValue({
      runId: 'run-live',
      conversationId: 'conv-live',
      status: 'RUNNING',
      lastStageCompleted: 'requirements',
      startedAt: '2024-01-01T00:00:00Z',
      eventCount: 3,
    });
    mockReattachStream.mockResolvedValue(undefined);
    useStore.setState({ token: 'jwt', conversationId: 'conv-live' });

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.send('test');
    });

    expect(mockStreamChat).not.toHaveBeenCalled();
    expect(mockReattachStream).toHaveBeenCalledWith(
      'conv-live',
      'jwt',
      expect.any(Function),
      'run-live',
      expect.any(AbortSignal),
    );
  });

  it('reattachesWhenDuplicateRunRaceOccurs', async () => {
    mockGetRunStatus
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({
        runId: 'run-race',
        conversationId: 'conv-race',
        status: 'RUNNING',
        lastStageCompleted: 'governance_analysis',
        startedAt: '2024-01-01T00:00:00Z',
        eventCount: 5,
      });
    mockStreamChat.mockRejectedValue(
      new Error('Stream request failed: 409 {"type":"urn:archon:duplicate-pipeline-run"}'),
    );
    mockReattachStream.mockResolvedValue(undefined);
    useStore.setState({ token: 'jwt', conversationId: 'conv-race' });

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.send('test');
    });

    expect(mockReattachStream).toHaveBeenCalledWith(
      'conv-race',
      'jwt',
      expect.any(Function),
      'run-race',
      expect.any(AbortSignal),
    );
    expect(useStore.getState().error).toBeNull();
  });

  it('doesNotPollRunStatusWhenConversationIdIsNull', async () => {
    mockStreamChat.mockRejectedValue(new Error('Network error'));
    useStore.setState({ token: 'jwt', conversationId: null });

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.send('test');
    });

    expect(mockGetRunStatus).not.toHaveBeenCalled();
  });

  it('reconnect_setsErrorWhenNotAuthenticated', async () => {
    useStore.setState({ token: null, conversationId: null });
    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.reconnect();
    });

    expect(useStore.getState().error).toBe('Not authenticated');
    expect(mockReattachStream).not.toHaveBeenCalled();
  });

  it('reconnect_callsReattachStreamWithCorrectArgs', async () => {
    mockReattachStream.mockResolvedValue(undefined);
    useStore.setState({ token: 'jwt', conversationId: 'conv-r', runId: 'run-42' });

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.reconnect();
    });

    expect(mockReattachStream).toHaveBeenCalledWith(
      'conv-r',
      'jwt',
      expect.any(Function),
      'run-42',
      expect.any(AbortSignal),
    );
  });

  it('reconnect_setsErrorOnReattachFailure', async () => {
    mockReattachStream.mockRejectedValue(new Error('Reattach failed'));
    useStore.setState({ token: 'jwt', conversationId: 'conv-r', runId: null });

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.reconnect();
    });

    expect(useStore.getState().error).toBe('Reattach failed');
  });
});
