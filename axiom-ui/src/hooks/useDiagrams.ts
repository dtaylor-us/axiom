import { useCallback, useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import type { DiagramCollectionDto } from '../types/api';
import { getDiagramCollection } from '../api/architecture';

export function useDiagrams() {
  const token = useStore((s) => s.token);
  const conversationId = useStore((s) => s.conversationId);

  const [collection, setCollection] = useState<DiagramCollectionDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDiagrams = useCallback(async () => {
    if (!token || !conversationId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getDiagramCollection(conversationId, token);
      setCollection(data);
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load diagrams');
    } finally {
      setLoading(false);
    }
  }, [token, conversationId]);

  useEffect(() => {
    fetchDiagrams();
  }, [fetchDiagrams]);

  return {
    collection,
    loading,
    error,
    refresh: fetchDiagrams,
  };
}
