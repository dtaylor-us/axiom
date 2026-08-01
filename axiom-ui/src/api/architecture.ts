import type { ArchitectureOutput, DiagramCollectionDto, DiagramDto } from '../types/api';
import { ApiError, authFetchJson } from './http';
import { SESSIONS_BASE } from './config';

const BASE = SESSIONS_BASE;

export async function getArchitecture(
  sessionId: string,
  token: string,
): Promise<ArchitectureOutput> {
  return authFetchJson<ArchitectureOutput>(
    `${BASE}/${sessionId}/architecture`,
    token,
  );
}

export async function getDiagramCollection(
  sessionId: string,
  token: string,
): Promise<DiagramCollectionDto> {
  return authFetchJson<DiagramCollectionDto>(
    `${BASE}/${sessionId}/diagram`,
    token,
  );
}

export async function getDiagramByType(
  sessionId: string,
  type: string,
  token: string,
): Promise<string | null> {
  try {
    const dto = await authFetchJson<DiagramDto>(
      `${BASE}/${sessionId}/diagram/${encodeURIComponent(type)}`,
      token,
    );
    return dto.mermaidSource || null;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
