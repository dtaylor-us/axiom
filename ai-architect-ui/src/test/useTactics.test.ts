import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useStore } from '../store/useStore';
import { useTactics } from '../hooks/useTactics';

vi.mock('../api/governance', () => ({
  getTactics: vi.fn(),
  getTacticsSummary: vi.fn(),
}));

import { getTactics, getTacticsSummary } from '../api/governance';

const mockedGetTactics = vi.mocked(getTactics);
const mockedGetSummary = vi.mocked(getTacticsSummary);

const TACTICS = [
  { tacticId: 'tac-001', name: 'Cache aside', description: 'Cache DB reads', priority: 'H' },
];
const SUMMARY = { total: 1, byPriority: { H: 1, M: 0, L: 0 } };

beforeEach(() => {
  vi.clearAllMocks();
  useStore.setState({ token: null, conversationId: null, pipelineVersion: 0 });
});

describe('useTactics', () => {
  it('returnsEmptyTacticsWhenNoToken', async () => {
    const { result } = renderHook(() => useTactics());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.tactics).toEqual([]);
    expect(mockedGetTactics).not.toHaveBeenCalled();
  });

  it('doesNotFetchWithoutConversationId', async () => {
    useStore.setState({ token: 'tok', conversationId: null });
    const { result } = renderHook(() => useTactics());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockedGetTactics).not.toHaveBeenCalled();
  });

  it('fetchesTacticsAndSummaryWhenBothPresent', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGetTactics.mockResolvedValue(TACTICS as never);
    mockedGetSummary.mockResolvedValue(SUMMARY as never);

    const { result } = renderHook(() => useTactics());
    await waitFor(() => expect(result.current.tactics.length).toBeGreaterThan(0));

    expect(result.current.tactics).toEqual(TACTICS);
    expect(result.current.summary).toEqual(SUMMARY);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('passesFilterParamsToApi', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGetTactics.mockResolvedValue(TACTICS as never);
    mockedGetSummary.mockResolvedValue(SUMMARY as never);

    renderHook(() => useTactics({ characteristic: 'performance', priority: 'H', newOnly: true }));
    await waitFor(() => expect(mockedGetTactics).toHaveBeenCalled());

    expect(mockedGetTactics).toHaveBeenCalledWith(
      'conv-1', 'tok',
      { characteristic: 'performance', priority: 'H', newOnly: true },
    );
  });

  it('setsErrorWhenFetchFails', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGetTactics.mockRejectedValue(new Error('Server error'));
    mockedGetSummary.mockResolvedValue(SUMMARY as never);

    const { result } = renderHook(() => useTactics());
    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.error).toBe('Server error');
  });

  it('exposesRefreshFunction', async () => {
    useStore.setState({ token: 'tok', conversationId: 'conv-1' });
    mockedGetTactics.mockResolvedValue(TACTICS as never);
    mockedGetSummary.mockResolvedValue(SUMMARY as never);

    const { result } = renderHook(() => useTactics());
    await waitFor(() => expect(result.current.tactics.length).toBeGreaterThan(0));

    const callsBefore = mockedGetTactics.mock.calls.length;
    await result.current.refresh();
    expect(mockedGetTactics.mock.calls.length).toBeGreaterThan(callsBefore);
  });
});
