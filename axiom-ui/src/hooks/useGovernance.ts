import { useState, useEffect, useCallback } from 'react';
import { useStore } from '../store/useStore';
import type {
  TradeOffDecision,
  AdlDocument,
  WeaknessReport,
  FmeaEntry,
  GovernanceReport,
} from '../types/api';
import {
  getTradeOffs,
  getAdl,
  getWeaknesses,
  getFmea,
  getGovernanceReport,
} from '../api/governance';
import { ApiError } from '../api/http';

/**
 * Hook that fetches governance artefacts for a conversation.
 */
export function useGovernance() {
  const token = useStore((s) => s.token);
  const conversationId = useStore((s) => s.conversationId);
  const pipelineVersion = useStore((s) => s.pipelineVersion);

  const [tradeOffs, setTradeOffs] = useState<TradeOffDecision[]>([]);
  const [adl, setAdl] = useState<AdlDocument | null>(null);
  const [weaknesses, setWeaknesses] = useState<WeaknessReport | null>(null);
  const [fmea, setFmea] = useState<FmeaEntry[]>([]);
  const [governanceReport, setGovernanceReport] = useState<GovernanceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isNotFound = (err: unknown) =>
    err instanceof ApiError && err.status === 404;

  const fetchAll = useCallback(async () => {
    if (!token || !conversationId) return;
    setLoading(true);
    setError(null);
    try {
      const [to, a, w, f] = await Promise.allSettled([
        getTradeOffs(conversationId, token),
        getAdl(conversationId, token),
        getWeaknesses(conversationId, token),
        getFmea(conversationId, token),
      ]);
      const gr = await getGovernanceReport(conversationId, token).catch((e) => e);

      if (to.status === 'fulfilled') setTradeOffs(to.value);
      else if (!isNotFound(to.reason)) throw to.reason;

      if (a.status === 'fulfilled') setAdl(a.value);
      else if (!isNotFound(a.reason)) throw a.reason;

      if (w.status === 'fulfilled') setWeaknesses(w.value);
      else if (!isNotFound(w.reason)) throw w.reason;

      if (f.status === 'fulfilled') setFmea(f.value);
      else if (!isNotFound(f.reason)) throw f.reason;

      if (gr instanceof ApiError && gr.status === 404) {
        setGovernanceReport(null);
      } else if (gr instanceof Error) {
        throw gr;
      } else {
        setGovernanceReport(gr as GovernanceReport);
      }
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load governance data');
    } finally {
      setLoading(false);
    }
  }, [token, conversationId, pipelineVersion]);

  useEffect(() => {
    if (pipelineVersion > 0) {
      const id = setTimeout(() => { fetchAll(); }, 1500);
      return () => clearTimeout(id);
    }
    fetchAll();
  }, [fetchAll, pipelineVersion]);

  return {
    tradeOffs,
    adl,
    weaknesses,
    fmea,
    governanceReport,
    loading,
    error,
    refresh: fetchAll,
  };
}
