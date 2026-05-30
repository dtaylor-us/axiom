import { useCallback, useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import type { ArchitectureOutput } from '../types/api';
import { getArchitecture } from '../api/architecture';

export function useArchitecture() {
  const token = useStore((s) => s.token);
  const conversationId = useStore((s) => s.conversationId);

  const [architecture, setArchitecture] = useState<ArchitectureOutput | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchArchitecture = useCallback(async () => {
    if (!token || !conversationId) return;
    setLoading(true);
    setError(null);
    try {
      const arch = await getArchitecture(conversationId, token);
      setArchitecture(arch);
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load architecture');
    } finally {
      setLoading(false);
    }
  }, [token, conversationId]);

  useEffect(() => {
    fetchArchitecture();
  }, [fetchArchitecture]);

  return {
    architecture,
    loading,
    error,
    refresh: fetchArchitecture,
  };
}
