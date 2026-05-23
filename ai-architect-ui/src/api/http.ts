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

export async function authFetchJson<T>(
  url: string,
  token: string,
): Promise<T> {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.ok) {
    return res.json() as Promise<T>;
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

  const msg =
    problem?.detail ?? problem?.title ?? `Request failed: ${res.status}`;
  throw new ApiError(res.status, msg, problem);
}
