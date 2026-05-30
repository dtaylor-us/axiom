import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useConversation } from '../hooks/useConversation';
import { useStore } from '../store/useStore';

// Mock useSSEStream
vi.mock('../hooks/useSSEStream', () => ({
  useSSEStream: () => ({
    send: vi.fn(),
    abort: vi.fn(),
  }),
}));

describe('useConversation', () => {
  beforeEach(() => {
    useStore.setState({
      streamingText: '',
      isStreaming: false,
      error: null,
      conversationId: null,
      stages: useStore.getState().stages.map((s) => ({
        ...s,
        status: 'pending' as const,
      })),
    });
  });

  it('returnsConversationState', () => {
    const { result } = renderHook(() => useConversation());
    expect(result.current.streamingText).toBe('');
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.conversationId).toBeNull();
    expect(result.current.stages).toHaveLength(14);
  });

  it('returnsSendMessageFunction', () => {
    const { result } = renderHook(() => useConversation());
    expect(typeof result.current.sendMessage).toBe('function');
  });

  it('returnsAbortFunction', () => {
    const { result } = renderHook(() => useConversation());
    expect(typeof result.current.abort).toBe('function');
  });

  it('returnsResetConversationFunction', () => {
    const { result } = renderHook(() => useConversation());
    expect(typeof result.current.resetConversation).toBe('function');
  });
});
