import type {
  TradeOffDecision,
  AdlDocument,
  WeaknessReport,
  FmeaEntry,
  GovernanceReport,
  TacticRecommendation,
  TacticsSummary,
  BuyVsBuildSummary,
  BuyVsBuildDecision,
} from '../types/api';
import { authFetchJson } from './http';

const BASE = '/api/v1/sessions';

export async function getTradeOffs(
  sessionId: string,
  token: string,
): Promise<TradeOffDecision[]> {
  return authFetchJson<TradeOffDecision[]>(
    `${BASE}/${sessionId}/trade-offs`,
    token,
  );
}

export async function getAdl(
  sessionId: string,
  token: string,
): Promise<AdlDocument> {
  return authFetchJson<AdlDocument>(`${BASE}/${sessionId}/adl`, token);
}

export async function getAdlHard(
  sessionId: string,
  token: string,
): Promise<AdlDocument> {
  return authFetchJson<AdlDocument>(`${BASE}/${sessionId}/adl/hard`, token);
}

export async function getAdlByCategory(
  sessionId: string,
  category: string,
  token: string,
): Promise<AdlDocument> {
  return authFetchJson<AdlDocument>(
    `${BASE}/${sessionId}/adl/${category}`,
    token,
  );
}

export async function getWeaknesses(
  sessionId: string,
  token: string,
): Promise<WeaknessReport> {
  return authFetchJson<WeaknessReport>(
    `${BASE}/${sessionId}/weaknesses`,
    token,
  );
}

export async function getFmea(
  sessionId: string,
  token: string,
): Promise<FmeaEntry[]> {
  return authFetchJson<FmeaEntry[]>(`${BASE}/${sessionId}/fmea`, token);
}

export async function getFmeaRisks(
  sessionId: string,
  token: string,
): Promise<FmeaEntry[]> {
  return authFetchJson<FmeaEntry[]>(`${BASE}/${sessionId}/fmea-risks`, token);
}

export async function getGovernanceReport(
  sessionId: string,
  token: string,
): Promise<GovernanceReport> {
  return authFetchJson<GovernanceReport>(
    `${BASE}/${sessionId}/governance`,
    token,
  );
}

export async function getTactics(
  sessionId: string,
  token: string,
  params?: { characteristic?: string; priority?: string; newOnly?: boolean },
): Promise<TacticRecommendation[]> {
  const qs = new URLSearchParams();
  if (params?.characteristic) qs.set('characteristic', params.characteristic);
  if (params?.priority) qs.set('priority', params.priority);
  if (params?.newOnly) qs.set('newOnly', 'true');
  const query = qs.toString() ? `?${qs.toString()}` : '';
  return authFetchJson<TacticRecommendation[]>(
    `${BASE}/${sessionId}/tactics${query}`,
    token,
  );
}

export async function getTacticsSummary(
  sessionId: string,
  token: string,
): Promise<TacticsSummary> {
  return authFetchJson<TacticsSummary>(
    `${BASE}/${sessionId}/tactics/summary`,
    token,
  );
}

export async function getBuyVsBuildSummary(
  sessionId: string,
  token: string,
  params?: { recommendation?: 'build' | 'buy' | 'adopt' },
): Promise<BuyVsBuildSummary> {
  const qs = new URLSearchParams();
  if (params?.recommendation) qs.set('recommendation', params.recommendation);
  const query = qs.toString() ? `?${qs.toString()}` : '';
  return authFetchJson<BuyVsBuildSummary>(
    `${BASE}/${sessionId}/build-analysis${query}`,
    token,
  );
}

export async function getBuyVsBuildConflicts(
  sessionId: string,
  token: string,
): Promise<BuyVsBuildDecision[]> {
  return authFetchJson<BuyVsBuildDecision[]>(
    `${BASE}/${sessionId}/build-analysis/conflicts`,
    token,
  );
}
