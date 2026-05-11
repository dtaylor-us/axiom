import { authFetchJson, ApiError } from './http';
import type {
  WorkshopSessionSummary,
  WorkshopTurnResponse,
  WorkshopMessage,
  QualityAttribute,
  AttributeSummary,
  GenerationReadinessDto,
  WorkshopGenerationResponseDto,
  WorkshopScenario,
} from '../types/workshop';

const BASE = '/api/v1/workshop/sessions';

async function authPost<T>(url: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
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

/** Bridge workshop to main pipeline; returns the new conversationId. */
export async function sendWorkshopToPipeline(
  token: string,
  sessionId: string,
): Promise<{ conversationId: string }> {
  return authPost<{ conversationId: string }>(
    `${BASE}/${sessionId}/send-to-pipeline`,
    token,
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
