import { useState, useEffect, useCallback } from 'react';
import { useStore } from '../store/useStore';
import type { TacticRecommendation, TacticsSummary } from '../types/api';
import { getTactics, getTacticsSummary } from '../api/governance';
import { ApiError } from '../api/http';

export interface TacticsFilter {
  characteristic?: string;
  priority?: string;
  newOnly?: boolean;
}

/**
 * Hook that fetches architecture tactic recommendations for a conversation.
 *
 * Tactic catalog source: Bass, Clements, Kazman
 * "Software Architecture in Practice", 4th ed., SEI/Addison-Wesley 2021.
 */
export function useTactics(filter?: TacticsFilter) {
  const token = useStore((s) => s.token);
  const conversationId = useStore((s) => s.conversationId);
  const pipelineVersion = useStore((s) => s.pipelineVersion);

  const [tactics, setTactics] = useState<TacticRecommendation[]>([]);
  const [summary, setSummary] = useState<TacticsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isNotFound = (err: unknown) =>
    err instanceof ApiError && err.status === 404;

  const fetchAll = useCallback(async () => {
    if (!token || !conversationId) return;
    setLoading(true);
    setError(null);
    try {
      const [t, s] = await Promise.allSettled([
        getTactics(conversationId, token, filter),
        getTacticsSummary(conversationId, token),
      ]);

      if (t.status === 'fulfilled') setTactics(t.value);
      else if (!isNotFound(t.reason)) throw t.reason;

      if (s.status === 'fulfilled') setSummary(s.value);
      else if (!isNotFound(s.reason)) throw s.reason;
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load tactics');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, conversationId, pipelineVersion, filter?.characteristic, filter?.priority, filter?.newOnly]);

  useEffect(() => {
    // When triggered by a pipeline completion (pipelineVersion > 0), delay
    // briefly so the Java async persistence flush has time to commit before
    // we query the database.
    if (pipelineVersion > 0) {
      const id = setTimeout(() => { fetchAll(); }, 1500);
      return () => clearTimeout(id);
    }
    fetchAll();
  }, [fetchAll, pipelineVersion]);

  return { tactics, summary, loading, error, refresh: fetchAll };
}
