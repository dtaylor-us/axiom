import { useState, useEffect, useCallback } from 'react';
import { useStore } from '../store/useStore';
import type { BuyVsBuildSummary } from '../types/api';
import { getBuyVsBuildSummary } from '../api/governance';
import { ApiError } from '../api/http';

/**
 * Hook that fetches buy-vs-build sourcing decisions for a conversation.
 */
export function useBuyVsBuild(params?: { recommendation?: 'build' | 'buy' | 'adopt' }) {
  const token = useStore((s) => s.token);
  const conversationId = useStore((s) => s.conversationId);
  const pipelineVersion = useStore((s) => s.pipelineVersion);

  const [summary, setSummary] = useState<BuyVsBuildSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isNotFound = (err: unknown) => err instanceof ApiError && err.status === 404;

  const fetchSummary = useCallback(async () => {
    if (!token || !conversationId) return;
    setLoading(true);
    setError(null);
    try {
      const s = await getBuyVsBuildSummary(conversationId, token, params);
      setSummary(s);
    } catch (err) {
      if (isNotFound(err)) {
        setSummary(null);
      } else {
        setError((err as Error).message ?? 'Failed to load sourcing decisions');
      }
    } finally {
      setLoading(false);
    }
  }, [token, conversationId, pipelineVersion, params?.recommendation]);

  useEffect(() => {
    if (pipelineVersion > 0) {
      const id = setTimeout(() => { fetchSummary(); }, 1500);
      return () => clearTimeout(id);
    }
    fetchSummary();
  }, [fetchSummary, pipelineVersion]);

  return { summary, loading, error, refresh: fetchSummary };
}

