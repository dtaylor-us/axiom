import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useStore } from '../store/useStore';
import { useBuyVsBuild } from '../hooks/useBuyVsBuild';
import { ApiError } from '../api/http';

vi.mock('../api/governance', () => ({
  getBuyVsBuildSummary: vi.fn(),
}));

import { getBuyVsBuildSummary } from '../api/governance';

const mockedGet = vi.mocked(getBuyVsBuildSummary);

const SUMMARY = {
  components: [{ componentName: 'Auth', recommendation: 'buy', rationale: 'Commodity' }],
  buildCount: 0,
  buyCount: 1,
  adoptCount: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
  useStore.setState({ token: null, conversationId: null, pipelineVersion: 0 });
});

describe('useBuyVsBuild', () => {
  it('returnsNullSummaryWhenNoToken', async () => {
    const { result } = renderHook(() => useBuyVsBuild());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.summary).toBeNull();
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it('doesNotFetchWithoutConversationId', async () => {
    useStore.setState({ token: 'tok', conversationId: null });
    const { result } = renderHook(() => useBuyVsBuild());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it('fetchesSummaryWhenTokenAndConversationIdAreSet', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGet.mockResolvedValue(SUMMARY as never);

    const { result } = renderHook(() => useBuyVsBuild());
    await waitFor(() => expect(result.current.summary).not.toBeNull());

    expect(mockedGet).toHaveBeenCalledWith('conv-1', 'tok', undefined);
    expect(result.current.summary).toEqual(SUMMARY);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('passesRecommendationParamToApi', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGet.mockResolvedValue(SUMMARY as never);

    renderHook(() => useBuyVsBuild({ recommendation: 'build' }));
    await waitFor(() => expect(mockedGet).toHaveBeenCalled());

    expect(mockedGet).toHaveBeenCalledWith('conv-1', 'tok', { recommendation: 'build' });
  });

  it('setsSummaryToNullOn404', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGet.mockRejectedValue(new ApiError(404, 'Not Found'));

    const { result } = renderHook(() => useBuyVsBuild());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.summary).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('setsErrorOnNon404Failure', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGet.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useBuyVsBuild());
    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.error).toBe('Network error');
  });

  it('exposesRefreshFunction', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGet.mockResolvedValue(SUMMARY as never);

    const { result } = renderHook(() => useBuyVsBuild());
    await waitFor(() => expect(result.current.summary).not.toBeNull());

    const callsBefore = mockedGet.mock.calls.length;
    await result.current.refresh();
    expect(mockedGet.mock.calls.length).toBeGreaterThan(callsBefore);
  });
});
