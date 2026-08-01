import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useArchitecture } from '../hooks/useArchitecture';
import { useStore } from '../store/useStore';

vi.mock('../api/architecture', () => ({
  getArchitecture: vi.fn(),
  getDiagramCollection: vi.fn(),
}));

import { getArchitecture } from '../api/architecture';

describe('useArchitecture', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
    useStore.setState({ token: null, conversationId: null });
  });

  it('returnsNullArchitectureWhenNoTokenOrConversation', () => {
    const { result } = renderHook(() => useArchitecture());

    expect(result.current.architecture).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('doesNotFetchWhenTokenMissing', () => {
    useStore.setState({ token: null, conversationId: 'conv-1' });

    renderHook(() => useArchitecture());

    expect(getArchitecture).not.toHaveBeenCalled();
  });

  it('doesNotFetchWhenConversationIdMissing', () => {
    useStore.setState({ token: 'jwt', conversationId: null });

    renderHook(() => useArchitecture());

    expect(getArchitecture).not.toHaveBeenCalled();
  });

  it('fetchesArchitectureWhenTokenAndConversationPresent', async () => {
    const mockArch = { style: 'microservices', components: [] };
    vi.mocked(getArchitecture).mockResolvedValue(mockArch as never);

    useStore.setState({ token: 'jwt', conversationId: 'conv-1' });

    const { result } = renderHook(() => useArchitecture());

    await waitFor(() => expect(result.current.architecture).toEqual(mockArch));
    expect(getArchitecture).toHaveBeenCalledWith('conv-1', 'jwt');
  });

  it('setsErrorWhenFetchFails', async () => {
    vi.mocked(getArchitecture).mockRejectedValue(new Error('Network failure'));

    useStore.setState({ token: 'jwt', conversationId: 'conv-1' });

    const { result } = renderHook(() => useArchitecture());

    await waitFor(() => expect(result.current.error).toBe('Network failure'));
    expect(result.current.architecture).toBeNull();
  });

  it('exposesRefreshFunction', async () => {
    const mockArch = { style: 'layered', components: [] };
    vi.mocked(getArchitecture).mockResolvedValue(mockArch as never);

    useStore.setState({ token: 'jwt', conversationId: 'conv-1' });

    const { result } = renderHook(() => useArchitecture());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const callsBefore = vi.mocked(getArchitecture).mock.calls.length;
    await act(async () => {
      await result.current.refresh();
    });

    // At least one additional call should have been made by refresh().
    expect(vi.mocked(getArchitecture).mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it('refetchesAfterPipelineCompletion', async () => {
    vi.mocked(getArchitecture).mockResolvedValue({ style: 'Service-based', components: [] } as never);
    useStore.setState({ token: 'jwt', conversationId: 'conv-1', pipelineVersion: 0 });

    renderHook(() => useArchitecture());
    await waitFor(() => expect(getArchitecture).toHaveBeenCalledTimes(1));

    act(() => useStore.setState({ pipelineVersion: 1 }));

    await waitFor(() => expect(getArchitecture).toHaveBeenCalledTimes(2));
  });
});
