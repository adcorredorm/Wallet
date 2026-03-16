import axios from 'axios'

/**
 * Checks whether the backend is reachable by calling GET /health.
 *
 * Why raw axios.get (no baseURL)?
 * The health endpoint lives at the root (/health), not under /api/v1.
 * Using a plain axios.get with a relative path keeps the call simple and
 * avoids the need to strip the /api/v1 prefix from API_BASE_URL.
 * The Vite dev proxy forwards /health to the backend. In production the
 * app is served from the same origin as the backend.
 *
 * Returns true if the backend responds with any 2xx status.
 * Returns false on any error (network failure, timeout, 4xx, 5xx).
 * Never throws.
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    await axios.get('/health', { timeout: 5000 })
    return true
  } catch {
    return false
  }
}
