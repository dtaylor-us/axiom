import { MEMORIA_API_BASE } from './config';
import { ApiError } from './http';

const PROJECTS_BASE = `${MEMORIA_API_BASE}/projects`;
const USE_LOCAL_MEMORIA_PROXY = MEMORIA_API_BASE.startsWith('/memoria-api');

export type ProjectStatus = 'ACTIVE' | 'ARCHIVED';
export type Pillar = 'ARCHON' | 'SPECWEAVER' | 'LENS';
export type MemoryType = 'DECISION' | 'REQUIREMENT' | 'RISK' | 'QUALITY_SCORE' | 'ASSUMPTION' | 'CONSTRAINT' | 'SESSION_SUMMARY';
export type MemoryTier = 'EPISODIC' | 'SEMANTIC';
export type MemoryConfidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'INFERRED';
export type MemoryStatus = 'ACTIVE' | 'SUPERSEDED' | 'STALE' | 'ARCHIVED';
export type AdrStatus = 'PROPOSED' | 'ACCEPTED' | 'SUPERSEDED' | 'DEPRECATED';

export interface MemoriaProject {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectMemorySummary {
  totalFacts: number;
  activeFacts: number;
  staleFacts: number;
  archivedFacts: number;
  supersededFacts: number;
  decisions: number;
  requirements: number;
  openRisks: number;
  adrCount: number;
  expiringSoon: number;
}

export interface MemoryEntry {
  id: string;
  projectId: string;
  memoryType: MemoryType;
  tier: MemoryTier;
  content: string;
  rationale: string | null;
  sourcePillar: Pillar | null;
  sourceSessionId: string | null;
  sourceExcerpt: string | null;
  confidence: MemoryConfidence;
  status: MemoryStatus;
  supersededBy: string | null;
  expiresAt: string | null;
  lastAccessedAt: string | null;
  accessCount: number;
  tags: string[] | null;
  createdAt: string;
  updatedAt: string;
}

export interface ArchitectureDecision {
  id: string;
  projectId: string;
  adrNumber: number;
  title: string;
  status: AdrStatus;
  context: string;
  decision: string;
  consequences: string | null;
  alternativesConsidered: string | null;
  sourcePillar: Pillar | null;
  sourceSessionId: string | null;
  sourceMemoryEntryId: string | null;
  supersededByAdrNumber: number | null;
  createdAt: string;
}

export interface SessionLink {
  id: string;
  projectId: string;
  pillar: Pillar;
  sessionId: string;
  linkedAt: string;
}

export interface MemoryFilters {
  status?: MemoryStatus;
  memoryType?: MemoryType;
  tier?: MemoryTier;
  sourcePillar?: Pillar;
  tag?: string;
  q?: string;
}

interface ProblemDetail {
  detail?: string;
  title?: string;
}

function decodeJwtIdentity(token: string): string | null {
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
    const payload = JSON.parse(atob(padded)) as { sub?: unknown; email?: unknown; username?: unknown };
    if (typeof payload.sub === 'string' && payload.sub.trim()) return payload.sub;
    if (typeof payload.email === 'string' && payload.email.trim()) return payload.email;
    if (typeof payload.username === 'string' && payload.username.trim()) return payload.username;
  } catch {
    // Best-effort identity forwarding only.
  }
  return null;
}

function resolveUserIdentity(token: string): string {
  const identity = decodeJwtIdentity(token);
  if (identity) return identity;
  try {
    const raw = window.localStorage.getItem('archon.auth');
    if (!raw) return 'guest';
    const parsed = JSON.parse(raw) as { username?: unknown };
    return typeof parsed.username === 'string' && parsed.username.trim() ? parsed.username : 'guest';
  } catch {
    return 'guest';
  }
}

function headers(token: string, includeJson = false): Record<string, string> {
  const result: Record<string, string> = {
    'X-Axiom-User-Id': resolveUserIdentity(token),
  };
  if (!USE_LOCAL_MEMORIA_PROXY && token.trim() && token !== 'null' && token !== 'undefined') {
    result.Authorization = `Bearer ${token}`;
  }
  if (includeJson) {
    result['Content-Type'] = 'application/json';
  }
  return result;
}

async function fetchJson<T>(url: string, token: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      headers: headers(token),
    });
  } catch {
    throw new ApiError(0, 'Network error - check your connection and try again.');
  }
  if (response.ok) {
    return response.json() as Promise<T>;
  }
  let problem: ProblemDetail | undefined;
  try {
    problem = (await response.json()) as ProblemDetail;
  } catch {
    problem = undefined;
  }
  throw new ApiError(response.status, problem?.detail ?? problem?.title ?? `Request failed (${response.status})`, problem);
}

async function requestJson<T>(url: string, token: string, method: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: headers(token, body !== undefined),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'Network error - check your connection and try again.');
  }
  if (response.ok) {
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }
  let problem: ProblemDetail | undefined;
  try {
    problem = (await response.json()) as ProblemDetail;
  } catch {
    problem = undefined;
  }
  throw new ApiError(response.status, problem?.detail ?? problem?.title ?? `Request failed (${response.status})`, problem);
}

function queryString(values: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value && value.trim()) params.set(key, value);
  });
  const text = params.toString();
  return text ? `?${text}` : '';
}

export function listProjects(token: string): Promise<MemoriaProject[]> {
  return fetchJson<MemoriaProject[]>(PROJECTS_BASE, token);
}

export function createProject(token: string, name: string, description: string): Promise<MemoriaProject> {
  return requestJson<MemoriaProject>(PROJECTS_BASE, token, 'POST', { name, description });
}

export function getProjectSummary(token: string, projectId: string): Promise<ProjectMemorySummary> {
  return fetchJson<ProjectMemorySummary>(`${PROJECTS_BASE}/${projectId}/summary`, token);
}

export function listMemoryEntries(token: string, projectId: string, filters: MemoryFilters = {}): Promise<MemoryEntry[]> {
  const query = queryString({
    status: filters.status,
    memoryType: filters.memoryType,
    tier: filters.tier,
    sourcePillar: filters.sourcePillar,
    tag: filters.tag,
    q: filters.q,
  });
  return fetchJson<MemoryEntry[]>(`${PROJECTS_BASE}/${projectId}/memory${query}`, token);
}

export function createMemoryEntry(
  token: string,
  projectId: string,
  body: {
    memoryType: MemoryType;
    tier: MemoryTier;
    content: string;
    rationale?: string;
    sourcePillar?: Pillar;
    sourceSessionId?: string;
    confidence?: MemoryConfidence;
    tags?: string[];
  },
): Promise<MemoryEntry> {
  return requestJson<MemoryEntry>(`${PROJECTS_BASE}/${projectId}/memory`, token, 'POST', body);
}

export function transitionMemoryEntry(
  token: string,
  projectId: string,
  entryId: string,
  action: 'mark-stale' | 'archive' | 'restore',
): Promise<MemoryEntry> {
  return requestJson<MemoryEntry>(`${PROJECTS_BASE}/${projectId}/memory/${entryId}/${action}`, token, 'POST');
}

export function supersedeMemoryEntry(token: string, projectId: string, entryId: string, newEntryId: string): Promise<MemoryEntry> {
  return requestJson<MemoryEntry>(`${PROJECTS_BASE}/${projectId}/memory/${entryId}/supersede`, token, 'POST', { newEntryId });
}

export function promoteMemoryEntry(
  token: string,
  projectId: string,
  entryId: string,
  body: { title?: string; context: string; decision: string; consequences?: string; alternativesConsidered?: string },
): Promise<ArchitectureDecision> {
  return requestJson<ArchitectureDecision>(`${PROJECTS_BASE}/${projectId}/memory/${entryId}/promote-to-adr`, token, 'POST', body);
}

export function listAdrs(token: string, projectId: string, filters: { status?: AdrStatus; q?: string } = {}): Promise<ArchitectureDecision[]> {
  const query = queryString(filters);
  return fetchJson<ArchitectureDecision[]>(`${PROJECTS_BASE}/${projectId}/adrs${query}`, token);
}

export function createAdr(
  token: string,
  projectId: string,
  body: { title: string; context: string; decision: string; consequences?: string; alternativesConsidered?: string },
): Promise<ArchitectureDecision> {
  return requestJson<ArchitectureDecision>(`${PROJECTS_BASE}/${projectId}/adrs`, token, 'POST', body);
}

export function supersedeAdr(token: string, projectId: string, adrId: string, newAdrId: string): Promise<ArchitectureDecision> {
  return requestJson<ArchitectureDecision>(`${PROJECTS_BASE}/${projectId}/adrs/${adrId}/supersede`, token, 'POST', { newAdrId });
}

export function listSessionLinks(token: string, projectId: string): Promise<SessionLink[]> {
  return fetchJson<SessionLink[]>(`${PROJECTS_BASE}/${projectId}/sessions`, token);
}

export function createSessionLink(token: string, projectId: string, pillar: Pillar, sessionId: string): Promise<SessionLink> {
  return requestJson<SessionLink>(`${PROJECTS_BASE}/${projectId}/sessions`, token, 'POST', { pillar, sessionId });
}

export async function removeSessionLink(token: string, projectId: string, linkId: string): Promise<void> {
  await requestJson<void>(`${PROJECTS_BASE}/${projectId}/sessions/${linkId}`, token, 'DELETE');
}
