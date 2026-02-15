/**
 * CANONICAL API CLIENT (Truth-Only)
 * 
 * Centralized API handling with:
 * - Timeout (3s default)
 * - Retries (max 2) with jittered backoff
 * - Circuit Breaker (3 failures -> 30s cooldown)
 * - Standardized error handling
 */

export interface ApiResponse<T = any> {
  data: T;
  truth?: {
    complete: boolean;
    source: string;
    last_verified_at?: string;
    freshness_ms?: number;
    warnings?: string[];
    assumptions?: string[];
  };
  error?: string;
}

export interface RequestResult<T = any> {
  ok: boolean;
  status: number;
  data?: T;
  error?: string;
  fetchedAtUtc: string;
  durationMs: number;
}

interface CircuitBreakerState {
  failures: number;
  lastFailure: number;
  isOpen: boolean;
}

// Circuit breaker state per endpoint (simplified path)
const breakers: Record<string, CircuitBreakerState> = {};
const MAX_FAILURES = 3;
const BREAKER_COOLDOWN_MS = 30000;
const DEFAULT_TIMEOUT_MS = 3000;
const MAX_RETRIES = 2;

function getBreaker(path: string): CircuitBreakerState {
  if (!breakers[path]) {
    breakers[path] = { failures: 0, lastFailure: 0, isOpen: false };
  }
  const state = breakers[path];
  if (state.isOpen && Date.now() - state.lastFailure > BREAKER_COOLDOWN_MS) {
    // Reset after cooldown
    state.isOpen = false;
    state.failures = 0;
  }
  return state;
}

function recordSuccess(path: string) {
  const state = getBreaker(path);
  state.failures = 0;
  state.isOpen = false;
}

function recordFailure(path: string) {
  const state = getBreaker(path);
  state.failures++;
  state.lastFailure = Date.now();
  if (state.failures >= MAX_FAILURES) {
    state.isOpen = true;
    console.warn(`[API] Circuit breaker OPEN for ${path}`);
  }
}

async function wait(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// The core implementation returning raw JSON in data
export async function getJSON<T = any>(
  path: string, 
  options: { timeoutMs?: number; retries?: number } = {}
): Promise<RequestResult<T>> {
  const start = Date.now();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const retries = options.retries ?? MAX_RETRIES;
  const breakerPath = path.split('?')[0];
  const breaker = getBreaker(breakerPath);

  if (breaker.isOpen) {
    return { ok: false, status: 503, error: 'Circuit breaker open', fetchedAtUtc: new Date().toISOString(), durationMs: 0 };
  }

  let lastError: any;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(path, { headers: { 'Accept': 'application/json' }, signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        recordSuccess(breakerPath);
        const json = await res.json();
        return { ok: true, status: res.status, data: json, fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
      } else {
        if (res.status >= 500) recordFailure(breakerPath);
        return { ok: false, status: res.status, error: `HTTP ${res.status}`, fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
      }
    } catch (err: any) {
      clearTimeout(timeoutId);
      lastError = err;
      const isAbort = err.name === 'AbortError';
      if (attempt < retries && !isAbort) {
        const backoff = 500 * Math.pow(2, attempt) + Math.random() * 100;
        await wait(backoff);
        continue;
      }
    }
  }
  recordFailure(breakerPath);
  return { ok: false, status: 0, error: lastError?.message || 'Network error', fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
}

/**
 * Legacy wrapper for backward compatibility
 */
export async function apiGet<T = any>(path: string): Promise<ApiResponse<T> | null> {
  const res = await getJSON<T>(path);
  if (res.ok) {
    return res.data as ApiResponse<T>;
  }
  return null;
}

export async function apiPost<T = any>(
  path: string, 
  body: any,
  token?: string
): Promise<RequestResult<T>> {
  const start = Date.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s for POST
  
  try {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(path, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
        const json = await res.json();
        return { ok: true, status: res.status, data: json, fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
    } else {
        return { ok: false, status: res.status, error: `HTTP ${res.status}`, fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
    }
  } catch (err: any) {
      clearTimeout(timeoutId);
      return { ok: false, status: 0, error: err.message || 'Network error', fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
  }
}

export async function apiPut<T = any>(
  path: string, 
  body: any,
  token?: string
): Promise<RequestResult<T>> {
  const start = Date.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s for PUT
  
  try {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(path, {
      method: 'PUT',
      headers,
      body: JSON.stringify(body),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
        const json = await res.json();
        return { ok: true, status: res.status, data: json, fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
    } else {
        return { ok: false, status: res.status, error: `HTTP ${res.status}`, fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
    }
  } catch (err: any) {
      clearTimeout(timeoutId);
      return { ok: false, status: 0, error: err.message || 'Network error', fetchedAtUtc: new Date().toISOString(), durationMs: Date.now() - start };
  }
}

export const NO_BACKEND_FACT_AVAILABLE = "NO BACKEND FACT AVAILABLE";
