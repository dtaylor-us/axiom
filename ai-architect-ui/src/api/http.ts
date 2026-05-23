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
      headers: { Authorization: `Bearer ${token}` },
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
