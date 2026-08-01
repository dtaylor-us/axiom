import type { ChatMessage, SessionSummary } from '../types/api';
import { authFetchJson } from './http';
import { SESSIONS_BASE } from './config';

const BASE = SESSIONS_BASE;

export async function listSessions(token: string): Promise<SessionSummary[]> {
  return authFetchJson<SessionSummary[]>(BASE, token);
}

export async function getSessionMessages(
  sessionId: string,
  token: string,
): Promise<ChatMessage[]> {
  return authFetchJson<ChatMessage[]>(`${BASE}/${sessionId}/messages`, token);
}
