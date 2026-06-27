/**
 * Shared API base URL configuration for local and gateway-backed routing.
 *
 * VITE_USE_GATEWAY stays false for local development so the UI can run without
 * axiom-api, and flips to true in gateway-backed environments.
 */
const USE_GATEWAY = import.meta.env.VITE_USE_GATEWAY === 'true';
const IS_VITE_DEV = import.meta.env.DEV;

export const ARCHON_API_BASE = USE_GATEWAY ? '/api/v1/archon' : '/api/v1';
// In local mode, SpecWeaver runs as its own service and is exposed through a
// dedicated reverse-proxy prefix to avoid clashing with archon-api /api/v1.
export const SPECWEAVER_API_BASE = USE_GATEWAY ? '/api/v1/specweaver' : '/specweaver-api/api/v1';
// In local mode, Lens runs as its own service and is exposed through a
// dedicated reverse-proxy prefix.
// Outside Vite dev, route through gateway so docker/nginx deployments keep
// the platform entrypoint contract.
export const LENS_API_BASE = USE_GATEWAY || !IS_VITE_DEV ? '/api/v1/lens' : '/lens-api/api/v1/lens';

export const AUTH_BASE = '/api/v1/auth';
export const CHAT_BASE = `${ARCHON_API_BASE}/chat`;
export const CONVERSATIONS_BASE = `${ARCHON_API_BASE}/conversations`;
export const SESSIONS_BASE = `${ARCHON_API_BASE}/sessions`;
export const WORKSHOP_BASE = `${ARCHON_API_BASE}/workshop`;
export const PIPELINE_BASE = `${ARCHON_API_BASE}/pipeline`;
