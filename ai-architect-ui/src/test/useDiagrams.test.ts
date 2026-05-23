import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useDiagrams } from '../hooks/useDiagrams';
import { useStore } from '../store/useStore';

vi.mock('../api/architecture', () => ({
  getArchitecture: vi.fn(),
  getDiagramCollection: vi.fn(),
}));

import { getDiagramCollection } from '../api/architecture';

describe('useDiagrams', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useStore.setState({ token: null, conversationId: null });
  });

  it('returnsNullCollectionWhenNoTokenOrConversation', () => {
    const { result } = renderHook(() => useDiagrams());

    expect(result.current.collection).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('doesNotFetchWhenTokenMissing', () => {
    useStore.setState({ token: null, conversationId: 'conv-1' });

    renderHook(() => useDiagrams());

    expect(getDiagramCollection).not.toHaveBeenCalled();
  });

  it('doesNotFetchWhenConversationIdMissing', () => {
    useStore.setState({ token: 'jwt', conversationId: null });

    renderHook(() => useDiagrams());

    expect(getDiagramCollection).not.toHaveBeenCalled();
  });

  it('fetchesDiagramCollectionWhenTokenAndConversationPresent', async () => {
    const mockCollection = { diagrams: [{ id: 'd1', type: 'c4' }] };
    vi.mocked(getDiagramCollection).mockResolvedValue(mockCollection as never);

    useStore.setState({ token: 'jwt', conversationId: 'conv-1' });

    const { result } = renderHook(() => useDiagrams());

    await waitFor(() => expect(result.current.collection).toEqual(mockCollection));
    expect(getDiagramCollection).toHaveBeenCalledWith('conv-1', 'jwt');
  });

  it('setsErrorWhenFetchFails', async () => {
    vi.mocked(getDiagramCollection).mockRejectedValue(new Error('Diagrams unavailable'));

    useStore.setState({ token: 'jwt', conversationId: 'conv-1' });

    const { result } = renderHook(() => useDiagrams());

    await waitFor(() => expect(result.current.error).toBe('Diagrams unavailable'));
    expect(result.current.collection).toBeNull();
  });

  it('exposesRefreshFunction', async () => {
    const mockCollection = { diagrams: [] };
    vi.mocked(getDiagramCollection).mockResolvedValue(mockCollection as never);

    useStore.setState({ token: 'jwt', conversationId: 'conv-1' });

    const { result } = renderHook(() => useDiagrams());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const callsBefore = vi.mocked(getDiagramCollection).mock.calls.length;
    await act(async () => {
      await result.current.refresh();
    });

    // At least one additional call should have been made by refresh().
    expect(vi.mocked(getDiagramCollection).mock.calls.length).toBeGreaterThan(callsBefore);
  });
});
