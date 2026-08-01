export interface ProblemDetail {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
}

export class ApiError extends Error {
  status: number;
  problem?: ProblemDetail;

  constructor(status: number, message: string, problem?: ProblemDetail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.problem = problem;
  }
}

function decodeJwtIdentity(token: string): string | null {
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
    const payload = JSON.parse(atob(padded)) as { sub?: unknown; email?: unknown; username?: unknown };
    if (typeof payload.sub === 'string' && payload.sub.trim().length > 0) return payload.sub;
    if (typeof payload.email === 'string' && payload.email.trim().length > 0) return payload.email;
    if (typeof payload.username === 'string' && payload.username.trim().length > 0) return payload.username;
  } catch {
    // Ignore malformed token payloads and fall back to persisted identity.
  }
  return null;
}

function resolveUserIdentity(token?: string): string {
  if (token && token.length > 0) {
    const jwtIdentity = decodeJwtIdentity(token);
    if (jwtIdentity) return jwtIdentity;
  }
  if (typeof window === 'undefined') return 'guest';
  try {
    const raw = window.localStorage.getItem('archon.auth');
    if (!raw) return 'guest';
    const parsed = JSON.parse(raw) as { username?: unknown };
    if (typeof parsed.username === 'string' && parsed.username.trim().length > 0) {
      return parsed.username;
    }
  } catch {
    // Fall back to guest identity when local storage is unavailable or malformed.
  }
  return 'guest';
}

function buildAuthHeaders(token: string): HeadersInit {
  const headers: Record<string, string> = {
    'X-Axiom-User-Id': resolveUserIdentity(token),
  };

  const trimmedToken = token.trim();
  if (trimmedToken.length > 0 && trimmedToken !== 'null' && trimmedToken !== 'undefined') {
    headers.Authorization = `Bearer ${trimmedToken}`;
  }

  return headers;
}

/** Map an HTTP status to a user-readable sentence when the server hasn't given one. */
function statusMessage(status: number): string {
  switch (status) {
    case 400: return 'The request was invalid. Please check your input.';
    case 401: return 'Your session has expired. Please sign in again.';
    case 403: return 'You do not have permission to perform this action.';
    case 404: return 'The requested resource was not found.';
    case 408: return 'The request timed out. Please try again.';
    case 409: return 'A conflict occurred. The resource may have changed.';
    case 422: return 'The request was invalid. Please check your input.';
    case 429: return 'Too many requests. Please wait a moment and try again.';
    case 500: return 'Something went wrong on the server. Please try again.';
    case 502: return 'The server is temporarily unreachable. Please try again shortly.';
    case 503: return 'The AI agent is temporarily unavailable. Please retry shortly.';
    case 504: return 'The server took too long to respond. Please try again.';
    default:  return `Request failed (${status})`;
  }
}

export async function authFetchJson<T>(
  url: string,
  token: string,
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      headers: buildAuthHeaders(token),
    });
  } catch {
    // Network failure (offline, DNS error, refused connection, etc.)
    throw new ApiError(0, 'Network error — check your connection and try again.');
  }

  if (res.ok) {
    return res.json() as Promise<T>;
  }

  // Fire a session-expired event so App can clear auth without a circular import
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('archon:session-expired'));
  }

  let problem: ProblemDetail | undefined;
  try {
    const ct = res.headers.get('content-type') ?? '';
    if (ct.includes('application/json') || ct.includes('application/problem+json')) {
      problem = (await res.json()) as ProblemDetail;
    }
  } catch {
    // ignore parse errors
  }

  const msg = problem?.detail ?? problem?.title ?? statusMessage(res.status);
  throw new ApiError(res.status, msg, problem);
}
