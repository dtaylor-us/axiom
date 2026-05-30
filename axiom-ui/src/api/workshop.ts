import { authFetchJson, ApiError } from './http';
import { WORKSHOP_BASE } from './config';
import type {
  WorkshopSessionSummary,
  WorkshopTurnResponse,
  WorkshopMessage,
  QualityAttribute,
  AttributeSummary,
  GenerationReadinessDto,
  WorkshopGenerationResponseDto,
  WorkshopScenario,
  UtilityTreeDto,
  ArchitectureImplicationDto,
} from '../types/workshop';

const BASE = `${WORKSHOP_BASE}/sessions`;

async function authPost<T>(
  url: string,
  token: string,
  body?: unknown,
  extraHeaders: Record<string, string> = {},
): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.ok) {
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }
  let problem;
  try { problem = await res.json(); } catch (_) { /* ignore */ }
  throw new ApiError(res.status, `Request failed: ${res.status}`, problem);
}

/** Create a new workshop session. */
export async function createWorkshopSession(
  token: string,
  systemName: string,
): Promise<WorkshopSessionSummary> {
  return authPost<WorkshopSessionSummary>(BASE, token, { systemName });
}

/** Submit a conversational turn. */
export async function submitWorkshopTurn(
  token: string,
  sessionId: string,
  userInput: string,
): Promise<WorkshopTurnResponse> {
  return authPost<WorkshopTurnResponse>(`${BASE}/${sessionId}/turn`, token, { userInput });
}

/** Get a single session. */
export async function getWorkshopSession(
  token: string,
  sessionId: string,
): Promise<WorkshopSessionSummary> {
  return authFetchJson<WorkshopSessionSummary>(`${BASE}/${sessionId}`, token);
}

/** Get quality attributes; optionally filter by confidence tier. */
export async function getWorkshopAttributes(
  token: string,
  sessionId: string,
  confidence?: 'confirmed' | 'partial' | 'weak',
): Promise<QualityAttribute[]> {
  const url = confidence
    ? `${BASE}/${sessionId}/attributes?confidence=${confidence}`
    : `${BASE}/${sessionId}/attributes`;
  return authFetchJson<QualityAttribute[]>(url, token);
}

/** Workshop scenarios from persisted session context. */
export async function getWorkshopScenarios(
  token: string,
  sessionId: string,
): Promise<WorkshopScenario[]> {
  return authFetchJson<WorkshopScenario[]>(`${BASE}/${sessionId}/scenarios`, token);
}

/** Complete the session; returns structured summary. */
export async function completeWorkshopSession(
  token: string,
  sessionId: string,
): Promise<AttributeSummary> {
  return authPost<AttributeSummary>(`${BASE}/${sessionId}/complete`, token);
}

/** Bridge workshop to main pipeline; returns the conversationId and the
 * requirements text to submit as the first pipeline message. */
export async function sendWorkshopToPipeline(
  token: string,
  sessionId: string,
): Promise<{ conversationId: string; initialMessage: string }> {
  const idempotencyKey = crypto.randomUUID();
  return authPost<{ conversationId: string; initialMessage: string }>(
    `${BASE}/${sessionId}/send-to-pipeline`,
    token,
    undefined,
    { 'Idempotency-Key': idempotencyKey },
  );
}

/** List all sessions for the current user. */
export async function listWorkshopSessions(
  token: string,
): Promise<WorkshopSessionSummary[]> {
  return authFetchJson<WorkshopSessionSummary[]>(BASE, token);
}

/** Get the conversation message history for a session, oldest first. */
export async function getWorkshopMessages(
  token: string,
  sessionId: string,
): Promise<WorkshopMessage[]> {
  return authFetchJson<WorkshopMessage[]>(`${BASE}/${sessionId}/messages`, token);
}

/** Read-only readiness preview for on-demand generation (does not persist). */
export async function assessGenerationReadiness(
  sessionId: string,
  token: string,
): Promise<GenerationReadinessDto> {
  return authFetchJson<GenerationReadinessDto>(
    `${BASE}/${sessionId}/generation-readiness`,
    token,
  );
}

/** Generate or regenerate quality attributes from current workshop evidence. */
export async function generateAttributes(
  sessionId: string,
  token: string,
): Promise<WorkshopGenerationResponseDto> {
  return authPost<WorkshopGenerationResponseDto>(
    `${BASE}/${sessionId}/generate`,
    token,
  );
}

/**
 * Returns the SEI QAW utility tree for a session.
 * Throws ApiError 404 when the utility tree has not been generated yet.
 */
export async function getUtilityTree(
  token: string,
  sessionId: string,
): Promise<UtilityTreeDto> {
  return authFetchJson<UtilityTreeDto>(`${BASE}/${sessionId}/utility-tree`, token);
}

/**
 * Returns architectural implications for a session.
 * Returns an empty array when none have been generated yet.
 */
export async function getImplications(
  token: string,
  sessionId: string,
): Promise<ArchitectureImplicationDto[]> {
  return authFetchJson<ArchitectureImplicationDto[]>(`${BASE}/${sessionId}/implications`, token);
}
