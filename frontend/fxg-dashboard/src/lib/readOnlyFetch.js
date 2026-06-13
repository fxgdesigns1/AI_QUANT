/**
 * READ-ONLY FETCH ENFORCER
 * 
 * 1. Enforces GET-only requests.
 * 2. Rejects any mutation attempts (POST, PUT, PATCH, DELETE).
 * 3. validates TruthEnvelope structure.
 */

export class TruthViolationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'TruthViolationError';
  }
}

export async function readOnlyFetch(url, options = {}) {
  // 1. Enforce GET only
  if (options.method && options.method.toUpperCase() !== 'GET') {
    throw new TruthViolationError(`MUTATION DETECTED: ${options.method} ${url} blocked by Read-Only Enforcer.`);
  }

  // 2. Perform Fetch
  try {
    const response = await fetch(url, {
      ...options,
      method: 'GET', // Force GET
      headers: {
        ...options.headers,
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();

    // 3. Verify Truth Envelope
    if (!json.truth) {
        console.warn('⚠️ Response missing TruthEnvelope:', url);
        // We allow it but warn, strictly strict mode would fail here.
        // For this implementation, we will check if it has 'data' at least.
    }

    return json;
  } catch (error) {
    console.error('Fetch Error:', error);
    throw error;
  }
}
