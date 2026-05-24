import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useGovernance } from '../hooks/useGovernance';
import { useStore } from '../store/useStore';

// Mock all API modules
vi.mock('../api/governance', () => ({
  getTradeOffs: vi.fn(),
  getAdl: vi.fn(),
  getWeaknesses: vi.fn(),
  getFmea: vi.fn(),
  getGovernanceReport: vi.fn(),
}));

import {
  getTradeOffs,
  getAdl,
  getWeaknesses,
  getFmea,
  getGovernanceReport,
} from '../api/governance';

const mockGetTradeOffs = vi.mocked(getTradeOffs);
const mockGetAdl = vi.mocked(getAdl);
const mockGetWeaknesses = vi.mocked(getWeaknesses);
const mockGetFmea = vi.mocked(getFmea);
const mockGetGovernanceReport = vi.mocked(getGovernanceReport);

describe('useGovernance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStore.setState({ token: 'jwt', conversationId: 'c1' });
  });

  it('fetchesAllGovernanceData_whenTokenAndConversationExist', async () => {
    mockGetTradeOffs.mockResolvedValue([]);
    mockGetAdl.mockResolvedValue({ document: 'doc', rules: [] });
    mockGetWeaknesses.mockResolvedValue({ weaknesses: [], summary: 'ok' });
    mockGetFmea.mockResolvedValue([]);
    mockGetGovernanceReport.mockResolvedValue({
      id: 'g1',
      conversationId: 'c1',
      iteration: 0,
      governanceScore: 80,
      governanceScoreConfidence: 'high',
      reviewCompletedFully: true,
      failedReviewNodes: [],
      requirementCoverage: 20,
      architecturalSoundness: 20,
      riskMitigation: 20,
      governanceCompleteness: 20,
      justification: 'ok',
      shouldReiterate: false,
      reviewFindings: {},
      improvementRecommendations: [],
      createdAt: new Date().toISOString(),
    });

    const { result } = renderHook(() => useGovernance());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockGetTradeOffs).toHaveBeenCalledWith('c1', 'jwt');
    expect(result.current.adl?.document).toBe('doc');
    expect(result.current.governanceReport?.governanceScore).toBe(80);
    expect(result.current.error).toBeNull();
  });

  it('doesNotFetch_whenTokenIsNull', () => {
    useStore.setState({ token: null });

    renderHook(() => useGovernance());
    expect(mockGetTradeOffs).not.toHaveBeenCalled();
  });

  it('doesNotFetch_whenConversationIdIsNull', () => {
    useStore.setState({ conversationId: null });

    renderHook(() => useGovernance());
    expect(mockGetTradeOffs).not.toHaveBeenCalled();
  });

  it('setsError_whenFetchFails', async () => {
    mockGetTradeOffs.mockRejectedValue(new Error('API down'));
    mockGetAdl.mockRejectedValue(new Error('API down'));
    mockGetWeaknesses.mockRejectedValue(new Error('API down'));
    mockGetFmea.mockRejectedValue(new Error('API down'));
    mockGetGovernanceReport.mockRejectedValue(new Error('API down'));

    const { result } = renderHook(() => useGovernance());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('API down');
  });

  it('delaysFetchByTimeoutWhenPipelineVersionIsPositive', () => {
    // Covers the setTimeout/clearTimeout branch (lines 79-80) triggered when
    // the hook detects a pipeline completion rather than an initial render.
    // waitFor is intentionally avoided: it also uses setTimeout internally,
    // which deadlocks with fake timers. The mock call is synchronous up to
    // the first await inside fetchAll, so a plain assertion suffices.
    vi.useFakeTimers();
    try {
      useStore.setState({ token: 'jwt', conversationId: 'c1', pipelineVersion: 1 });
      mockGetTradeOffs.mockResolvedValue([]);
      mockGetAdl.mockResolvedValue({ document: 'doc', rules: [] });
      mockGetWeaknesses.mockResolvedValue({ weaknesses: [], summary: 'ok' });
      mockGetFmea.mockResolvedValue([]);
      mockGetGovernanceReport.mockResolvedValue(null as never);

      renderHook(() => useGovernance());
      // Fetch must not fire immediately — it waits 1500 ms for the DB flush.
      expect(mockGetTradeOffs).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1500);

      expect(mockGetTradeOffs).toHaveBeenCalledWith('c1', 'jwt');
    } finally {
      vi.useRealTimers();
    }
  });
});
