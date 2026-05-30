import type { ArchitectureOutput, DiagramCollectionDto } from '../types/api';
import { authFetchJson } from './http';

const BASE = '/api/v1/sessions';

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
