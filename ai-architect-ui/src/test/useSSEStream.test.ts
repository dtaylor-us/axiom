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
    mockStreamChat.mockRejectedValue(new Error('Proxy disconnect'));
    mockGetRunStatus.mockResolvedValue({
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
