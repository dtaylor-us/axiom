import { ApiError, authFetchJson } from './http';
import { SPECWEAVER_API_BASE } from './config';

const BASE = `${SPECWEAVER_API_BASE}/sessions`;

export type SessionStatus = 'ACTIVE' | 'PROCESSING' | 'PACKAGE_READY' | 'SENT_TO_ARCHON';
export type DocumentStatus = 'PENDING' | 'PROCESSING' | 'EXTRACTED' | 'FAILED';
export type DocumentType = 'PLAIN_TEXT' | 'MARKDOWN' | 'PDF' | 'DOCX' | 'EMAIL';
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'INFERRED';

export interface Session {
  id: string;
  title: string | null;
  status: SessionStatus;
  createdAt: string;
  updatedAt: string;
  documents?: SessionDocument[];
  archonConversationId: string | null;
}

export interface SessionDocument {
  id: string;
  documentType: DocumentType;
  filename: string | null;
  sourceLabel: string | null;
  storageKey?: string | null;
  status: DocumentStatus;
  createdAt: string;
  processedAt?: string | null;
  errorMessage?: string | null;
  extractedText?: string | null;
}

export interface GapArea {
  gapId: string;
  area: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  explanation: string;
  clarificationQuestion: string;
  affectedCategories: string[];
}

export interface ConflictItem {
  conflictId: string;
  requirementIds: string[];
  description: string;
  interpretations: string[];
  clarificationQuestion: string;
}

export interface SourceDocumentMeta {
  id?: string;
  documentId?: string;
  filename?: string | null;
  sourceLabel?: string | null;
  documentType?: DocumentType | string;
  [key: string]: unknown;
}

interface PackageResponseEnvelope {
  id?: string;
  packageId?: string;
  sessionId?: string;
  packageJson?: string;
  totalRequirements?: number;
  highConfidenceCount?: number;
  inferredCount?: number;
  duplicateCount?: number;
  gapCount?: number;
  conflictCount?: number;
  readinessScore?: number;
  readinessLabel?: string;
  systemDescription?: string;
  requirements?: unknown[];
  gaps?: unknown[];
  conflicts?: unknown[];
  sourceDocuments?: unknown[];
  createdAt?: string;
  sentToArchonAt?: string | null;
  archonConversationId?: string | null;
}

export interface ClassifiedRequirement {
  requirementId: string;
  category: string;
  statement: string;
  type: string;
  confidence: Confidence;
  isInferred: boolean;
  inferenceReasoning: string | null;
  sourceDocumentIds: string[];
  sourceExcerpts: string[];
  ambiguities: string[];
}

export interface ArchInputPackage {
  packageId: string;
  sessionId: string;
  createdAt: string;
  readinessScore: number;
  readinessLabel: string;
  systemDescription: string;
  requirements: ClassifiedRequirement[];
  gaps: GapArea[];
  conflicts: ConflictItem[];
  sourceDocuments: SourceDocumentMeta[];
  totalRequirements: number;
  highConfidenceCount: number;
  inferredCount: number;
  duplicateCount: number;
  gapCount: number;
  conflictCount: number;
}

export type RequirementAnnotation = 'accepted' | 'flagged' | 'edited';

export interface RequirementReview {
  requirementId: string;
  annotation: RequirementAnnotation;
  editedStatement?: string;
  note?: string;
}

export async function authPostJson<T>(
  url: string,
  token: string,
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'Network error — check your connection and try again.');
  }

  if (response.ok) {
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }

  let problem: { detail?: string; title?: string } | undefined;
  try {
    problem = (await response.json()) as { detail?: string; title?: string };
  } catch {
    problem = undefined;
  }
  throw new ApiError(response.status, problem?.detail ?? problem?.title ?? `Request failed (${response.status})`, problem);
}

async function authPatchJson<T>(url: string, token: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'Network error — check your connection and try again.');
  }

  if (response.ok) {
    return response.json() as Promise<T>;
  }

  let problem: { detail?: string; title?: string } | undefined;
  try {
    problem = (await response.json()) as { detail?: string; title?: string };
  } catch {
    problem = undefined;
  }
  throw new ApiError(response.status, problem?.detail ?? problem?.title ?? `Request failed (${response.status})`, problem);
}

async function authDelete(url: string, token: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new ApiError(0, 'Network error — check your connection and try again.');
  }

  if (response.ok || response.status === 204) return;
  throw new ApiError(response.status, `Request failed (${response.status})`);
}

/**
 * Creates a new SpecWeaver session for staged document ingestion.
 */
export async function createSession(token: string, title?: string): Promise<Session> {
  return authPostJson<Session>(BASE, token, { title });
}

/**
 * Lists SpecWeaver sessions visible to the current user.
 */
export async function getSessions(token: string): Promise<Session[]> {
  return authFetchJson<Session[]>(BASE, token);
}

/**
 * Fetches one SpecWeaver session including its document list.
 */
export async function getSession(token: string, sessionId: string): Promise<Session> {
  return authFetchJson<Session>(`${BASE}/${sessionId}`, token);
}

/**
 * Updates mutable fields for a SpecWeaver session.
 */
export async function updateSessionTitle(
  token: string,
  sessionId: string,
  title: string | null,
): Promise<Session> {
  return authPatchJson<Session>(`${BASE}/${sessionId}`, token, { title });
}

/**
 * Uploads either a source file or pasted text to a SpecWeaver session.
 */
export async function uploadDocument(
  token: string,
  sessionId: string,
  file: File | null,
  text: string | null,
  documentType: string,
  sourceLabel?: string,
): Promise<SessionDocument> {
  const formData = new FormData();
  if (file) formData.append('file', file);
  if (text) formData.append('text', text);
  formData.append('documentType', documentType);
  if (sourceLabel) formData.append('sourceLabel', sourceLabel);

  let response: Response;
  try {
    response = await fetch(`${BASE}/${sessionId}/documents`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
  } catch {
    throw new ApiError(0, 'Network error — check your connection and try again.');
  }

  if (response.ok) return response.json() as Promise<SessionDocument>;
  throw new ApiError(response.status, `Document upload failed (${response.status})`);
}

/**
 * Removes a document from a session before package generation.
 */
export async function deleteDocument(
  token: string,
  sessionId: string,
  documentId: string,
): Promise<void> {
  return authDelete(`${BASE}/${sessionId}/documents/${documentId}`, token);
}

/**
 * Starts asynchronous ArchInputPackage generation.
 */
export async function generatePackage(
  token: string,
  sessionId: string,
): Promise<{ packageId: string }> {
  return authPostJson<{ packageId: string }>(`${BASE}/${sessionId}/package/generate`, token);
}

function parseArchInputPackage(envelope: PackageResponseEnvelope): ArchInputPackage {
  let parsed: Partial<ArchInputPackage> = {};

  // Backward compatibility for old API responses that wrapped the package in packageJson.
  if (typeof envelope.packageJson === 'string' && envelope.packageJson.length > 0) {
    try {
      parsed = JSON.parse(envelope.packageJson) as Partial<ArchInputPackage>;
    } catch {
      parsed = {};
    }
  } else {
    parsed = envelope as Partial<ArchInputPackage>;
  }

  const requirements = Array.isArray(parsed.requirements)
    ? parsed.requirements
    : Array.isArray(envelope.requirements)
      ? envelope.requirements
      : [];
  const gaps = Array.isArray(parsed.gaps)
    ? parsed.gaps
    : Array.isArray(envelope.gaps)
      ? envelope.gaps
      : [];
  const conflicts = Array.isArray(parsed.conflicts)
    ? parsed.conflicts
    : Array.isArray(envelope.conflicts)
      ? envelope.conflicts
      : [];
  const sourceDocuments = Array.isArray(parsed.sourceDocuments)
    ? parsed.sourceDocuments
    : Array.isArray(envelope.sourceDocuments)
      ? envelope.sourceDocuments
      : [];

  return {
    packageId: parsed.packageId ?? envelope.packageId ?? envelope.id ?? '',
    sessionId: parsed.sessionId ?? envelope.sessionId ?? '',
    createdAt: parsed.createdAt ?? envelope.createdAt ?? new Date(0).toISOString(),
    readinessScore:
      typeof parsed.readinessScore === 'number'
        ? parsed.readinessScore
        : envelope.readinessScore ?? 0,
    readinessLabel:
      parsed.readinessLabel
      ?? envelope.readinessLabel
      ?? 'Review requirements before sending to Archon.',
    systemDescription: parsed.systemDescription ?? envelope.systemDescription ?? '',
    requirements: requirements as ClassifiedRequirement[],
    gaps: gaps as GapArea[],
    conflicts: conflicts as ConflictItem[],
    sourceDocuments: sourceDocuments as SourceDocumentMeta[],
    totalRequirements:
      typeof parsed.totalRequirements === 'number'
        ? parsed.totalRequirements
        : envelope.totalRequirements ?? 0,
    highConfidenceCount:
      typeof parsed.highConfidenceCount === 'number'
        ? parsed.highConfidenceCount
        : envelope.highConfidenceCount ?? 0,
    inferredCount:
      typeof parsed.inferredCount === 'number'
        ? parsed.inferredCount
        : envelope.inferredCount ?? 0,
    duplicateCount:
      typeof parsed.duplicateCount === 'number'
        ? parsed.duplicateCount
        : envelope.duplicateCount ?? 0,
    gapCount:
      typeof parsed.gapCount === 'number'
        ? parsed.gapCount
        : typeof envelope.gapCount === 'number'
          ? envelope.gapCount
        : gaps.length,
    conflictCount:
      typeof parsed.conflictCount === 'number'
        ? parsed.conflictCount
        : typeof envelope.conflictCount === 'number'
          ? envelope.conflictCount
        : conflicts.length,
  };
}

/**
 * Retrieves the latest generated ArchInputPackage.
 */
export async function getPackage(
  token: string,
  sessionId: string,
): Promise<ArchInputPackage> {
  const envelope = await authFetchJson<PackageResponseEnvelope>(`${BASE}/${sessionId}/package`, token);
  return parseArchInputPackage(envelope);
}

/**
 * Retrieves the persisted package brief for user-controlled handoff to Archon chat.
 */
export async function sendToArchon(
  token: string,
  sessionId: string,
): Promise<{ briefText: string }> {
  return authPostJson<{ briefText: string }>(
    `${BASE}/${sessionId}/package/send-to-archon`,
    token,
  );
}
