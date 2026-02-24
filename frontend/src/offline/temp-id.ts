/**
 * Temporary ID utilities for offline-created entities
 *
 * Why a prefixed UUID instead of a plain UUID?
 * When the sync queue (Phase 3) processes a PendingMutation it needs to know
 * whether to call POST (the entity was created offline and has no server ID)
 * or PUT (the entity exists on the server but has local changes).
 *
 * A plain UUID would be indistinguishable from a real server UUID. The 'temp-'
 * prefix makes this check O(1) and explicit — no database lookup needed.
 *
 * Why crypto.randomUUID()?
 * - Cryptographically random: collision probability is negligible.
 * - No external dependency.
 * - Available natively in all modern browsers and Node 14.17+.
 * - Vite's dev server runs in Node, so it works in both environments.
 */

/**
 * Generate a temporary local ID for an entity created while offline.
 * Example output: "temp-550e8400-e29b-41d4-a716-446655440000"
 */
export function generateTempId(): string {
  return `temp-${crypto.randomUUID()}`
}

/**
 * Returns true if the given ID was generated locally (not assigned by the
 * server). Used by the Phase 3 sync queue to determine the HTTP verb.
 */
export function isTempId(id: string): boolean {
  return id.startsWith('temp-')
}
