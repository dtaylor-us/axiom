import { ApiError, authFetchJson } from './http';
import { LENS_API_BASE } from './config';

const BASE = `${LENS_API_BASE}/sessions`;

export type ReviewStatus = 'EVIDENCE_COLLECTION' | 'GAP_ELICITATION' | 'READY_FOR_REVIEW' | 'IN_REVIEW' | 'COMPLETE';
export type EvidenceType = 'TEXT_DESCRIPTION' | 'ADL_CONTENT' | 'DIAGRAM_DESCRIPTION' | 'DECISION_RECORD' | 'REQUIREMENTS_BRIEF';
export type GapCategory = 'RELIABILITY' | 'SECURITY' | 'COST' | 'OPERATIONS' | 'PERFORMANCE' | 'MODIFIABILITY' | 'INTEGRABILITY' | 'DATA' | 'STRUCTURAL' | 'GOVERNANCE';
export type OverallRating = 'APPROVED' | 'APPROVED_WITH_CONDITIONS' | 'NEEDS_REWORK' | 'NOT_APPROVED';

export interface ReviewSession {
  id: string;
  title: string;
  systemDescription: string;
  status: ReviewStatus;
  gapRound: number;
  gapsResolved: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ArchitectureEvidence {
  id: string;
  sessionId: string;
  evidenceType: EvidenceType;
  content: string;
  sourceLabel: string | null;
  submittedAt: string;
}

export interface GapQuestion {
  id: string;
  sessionId: string;
  round: number;
  category: GapCategory;
  question: string;
  rationale: string | null;
  answered: boolean;
  answer: string | null;
  skipped: boolean;
  askedAt: string;
  answeredAt: string | null;
}

export interface GapAssessmentResult {
  resolved: boolean;
  canProceed: boolean;
  remainingCount: number;
  unresolvableGaps: string[];
  summary: string;
}

export interface ReviewReportFinding {
  findingType: string;
  category: string | null;
  title: string;
  description: string;
  evidence: string | null;
  frameworkReference: string | null;
  severity: string;
}

export interface ReviewRisk {
  title: string;
  description: string;
  severity: string;
  likelihood: string;
  affectedArea: string | null;
  mitigationStrategy: string | null;
  frameworkReference: string | null;
}

export interface ReviewReport {
  id: string;
  sessionId: string;
  executiveSummary: string;
  azureWafScorecard: Record<string, unknown>;
  atamAnalysis: Record<string, unknown>;
  seiAnalysis: Record<string, unknown>;
  structuralAnalysis: Record<string, unknown>;
  insufficientInfoGaps: Record<string, unknown>;
  findings: ReviewReportFinding[];
  risks: ReviewRisk[];
  recommendationRoadmap: string;
  overallRating: OverallRating;
  generatedAt: string;
}

async function authPostJson<T>(url: string, token: string, body?: unknown): Promise<T> {
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

  throw new ApiError(response.status, `Request failed (${response.status})`);
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

export async function createReviewSession(token: string, title: string, systemDescription: string): Promise<ReviewSession> {
  return authPostJson<ReviewSession>(BASE, token, { title, systemDescription });
}

export async function listReviewSessions(token: string): Promise<ReviewSession[]> {
  return authFetchJson<ReviewSession[]>(BASE, token);
}

export async function getReviewSession(token: string, sessionId: string): Promise<ReviewSession> {
  return authFetchJson<ReviewSession>(`${BASE}/${sessionId}`, token);
}

export async function deleteReviewSession(token: string, sessionId: string): Promise<void> {
  return authDelete(`${BASE}/${sessionId}`, token);
}

export async function submitEvidence(token: string, sessionId: string, evidence: Omit<ArchitectureEvidence, 'id' | 'sessionId' | 'submittedAt'>): Promise<ArchitectureEvidence> {
  return authPostJson<ArchitectureEvidence>(`${BASE}/${sessionId}/evidence`, token, evidence);
}

export async function listEvidence(token: string, sessionId: string): Promise<ArchitectureEvidence[]> {
  return authFetchJson<ArchitectureEvidence[]>(`${BASE}/${sessionId}/evidence`, token);
}

export async function deleteEvidence(token: string, sessionId: string, evidenceId: string): Promise<void> {
  return authDelete(`${BASE}/${sessionId}/evidence/${evidenceId}`, token);
}

export async function generateGapQuestions(token: string, sessionId: string): Promise<GapQuestion[]> {
  return authPostJson<GapQuestion[]>(`${BASE}/${sessionId}/gaps/generate`, token);
}

export async function answerGapQuestion(token: string, sessionId: string, questionId: string, answer: string): Promise<GapQuestion> {
  return authPostJson<GapQuestion>(`${BASE}/${sessionId}/gaps/${questionId}/answer`, token, { answer });
}

export async function assessGaps(token: string, sessionId: string): Promise<GapAssessmentResult> {
  return authPostJson<GapAssessmentResult>(`${BASE}/${sessionId}/gaps/assess`, token);
}

export async function forceProceed(token: string, sessionId: string): Promise<ReviewSession> {
  return authPostJson<ReviewSession>(`${BASE}/${sessionId}/proceed`, token);
}

export async function getReviewReport(token: string, sessionId: string): Promise<ReviewReport> {
  return authFetchJson<ReviewReport>(`${BASE}/${sessionId}/report`, token);
}
