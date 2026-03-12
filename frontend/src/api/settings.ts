/**
 * Settings API Client
 *
 * Why two separate functions instead of an object like accountsApi?
 * Settings has a much smaller surface area (fetch all + update one key).
 * Named exports are simpler to tree-shake and match the "do one thing well"
 * principle — the settingsStore imports only what it needs.
 *
 * Why `Record<string, unknown>` for the return of fetchSettings?
 * The backend returns a flat JSON object of arbitrary key/value pairs
 * (e.g. { primary_currency: "COP", display_precision: 2 }). Using
 * `Record<string, unknown>` forces callers to narrow each value before use,
 * which is safer than `any` and correctly models the heterogeneous shape.
 *
 * Why `updateSetting` takes `unknown` for value?
 * Individual setting values can be strings, numbers, or booleans. The caller
 * (settingsStore) is responsible for validating the value before calling this
 * function. Accepting `unknown` here keeps the API layer thin.
 */

import apiClient from './index'

/**
 * Fetch all user settings from the backend.
 *
 * GET /api/v1/settings
 * Response shape (after apiClient unwraps data envelope):
 *   { primary_currency: "COP", display_precision: 2, ... }
 */
export async function fetchSettings(): Promise<Record<string, unknown>> {
  return apiClient.get('/settings')
}

/**
 * Persist a single setting to the backend.
 *
 * PUT /api/v1/settings/{key}
 * Body: { value: <value> }
 *
 * Why PUT instead of PATCH?
 * Individual settings are identified by key — there is no partial-update
 * concept for a single scalar value. PUT is idempotent and semantically
 * correct: "set the value for this key to exactly this".
 *
 * Why return void?
 * The backend returns a 200 with the updated setting, but the settingsStore
 * does not need the server's echo — it already has the value it just wrote.
 * Ignoring the response body keeps the API client thin.
 */
export async function updateSetting(key: string, value: unknown): Promise<void> {
  await apiClient.put(`/settings/${key}`, { value })
}
