import { enqueue } from '../lib/offline';

const BASE = '/api/v1';
const TOKEN_KEY = 'rli_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    setToken(null);
    window.dispatchEvent(new Event('rli:logout'));
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

/** Paths whose POSTs are queued for later sync when offline. */
const OFFLINE_QUEUEABLE = /^\/reviews\/\d+$/;

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: async <T>(path: string, body?: unknown): Promise<T> => {
    try {
      return await request<T>(path, {
        method: 'POST',
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (error) {
      // Network failure on a queueable write → persist and report queued.
      if (
        OFFLINE_QUEUEABLE.test(path) &&
        (error instanceof TypeError || !navigator.onLine)
      ) {
        enqueue(path, body);
        return { queued: true } as T;
      }
      throw error;
    }
  },
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  loginForm: async (email: string, password: string): Promise<{ access_token: string }> => {
    const form = new URLSearchParams({ username: email, password });
    const response = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    if (!response.ok) throw new ApiError(response.status, 'Incorrect email or password');
    return response.json();
  },
};
