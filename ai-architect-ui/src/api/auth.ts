import type { AuthTokenResponse } from '../types/api';

const BASE = '/api/v1/auth';

/** Quick auto-auth by username (guest mode) */
export async function getToken(username: string): Promise<string> {
  const res = await fetch(`${BASE}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username }),
  });
  if (!res.ok) {
    throw new Error(`Auth failed: ${res.status}`);
  }
  const data: AuthTokenResponse = await res.json();
  return data.token;
}

/** Register a new account */
export async function register(
  email: string,
  password: string,
  name: string,
): Promise<AuthTokenResponse> {
  const res = await fetch(`${BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      body.detail ?? body.message ?? `Registration failed: ${res.status}`,
    );
  }
  return res.json();
}

/** Login with email & password */
export async function login(
  email: string,
  password: string,
): Promise<AuthTokenResponse> {
  const res = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      body.detail ?? body.message ?? `Login failed: ${res.status}`,
    );
  }
  return res.json();
}
