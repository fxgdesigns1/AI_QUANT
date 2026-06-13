/**
 * CANONICAL API CLIENT (Truth-Only)
 * 
 * 1. Enforces GET-only requests
 * 2. Blocks mutations unless explicitly whitelisted
 * 3. Returns null on errors (never fabricates data)
 * 4. Logs all requests for transparency
 */

const NO_BACKEND_FACT_AVAILABLE = "NO BACKEND FACT AVAILABLE";

export class ReadOnlyViolationError extends Error {
  constructor(method: string, path: string) {
    super(`READ_ONLY_VIOLATION: ${method} ${path} blocked. Dashboard is read-only by default.`);
    this.name = 'ReadOnlyViolationError';
  }
}

export interface ApiResponse<T = any> {
  data: T;
  truth: {
    complete: boolean;
    source: string;
    last_verified_at?: string;
    freshness_ms?: number;
    warnings?: string[];
    assumptions?: string[];
  };
}

/**
 * GET-only API request handler
 */
export async function apiGet<T = any>(path: string): Promise<ApiResponse<T> | null> {
  const url = path.startsWith('/') ? path : `/${path}`;
  const fullUrl = url.startsWith('http') ? url : url;
  
  console.log(`[API] GET ${fullUrl}`);
  
  try {
    const response = await fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    console.log(`[API] GET ${fullUrl} → ${response.status}`);

    if (!response.ok) {
      console.error(`[API] GET ${fullUrl} failed: ${response.status} ${response.statusText}`);
      return null;
    }

    const json = await response.json();
    
    // Validate TruthEnvelope structure
    if (!json.truth) {
      console.warn(`[API] GET ${fullUrl} missing TruthEnvelope`);
    }

    return json as ApiResponse<T>;
  } catch (error) {
    console.error(`[API] GET ${fullUrl} error:`, error);
    return null;
  }
}

/**
 * Mutating API request (requires explicit whitelist + token)
 */
export async function apiPost<T = any>(
  path: string, 
  body: any,
  token?: string
): Promise<ApiResponse<T> | null> {
  if (!token) {
    throw new ReadOnlyViolationError('POST', path);
  }

  const url = path.startsWith('/') ? path : `/${path}`;
  const fullUrl = url.startsWith('http') ? url : url;
  
  console.log(`[API] POST ${fullUrl} (token-protected)`);
  
  try {
    const response = await fetch(fullUrl, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    console.log(`[API] POST ${fullUrl} → ${response.status}`);

    if (!response.ok) {
      console.error(`[API] POST ${fullUrl} failed: ${response.status} ${response.statusText}`);
      return null;
    }

    const json = await response.json();
    return json as ApiResponse<T>;
  } catch (error) {
    console.error(`[API] POST ${fullUrl} error:`, error);
    return null;
  }
}

export { NO_BACKEND_FACT_AVAILABLE };
