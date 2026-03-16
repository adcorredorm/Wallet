/**
 * auth-db.spec.ts
 *
 * Tests for AuthDB — the separate Dexie instance for session data.
 *
 * Strategy: use fake-indexeddb to run a real Dexie instance in Node/jsdom
 * without needing a browser. This tests the actual Dexie logic (put, get,
 * delete) rather than mocking it away — validating the schema and helpers
 * work correctly.
 *
 * Why fake-indexeddb instead of mocking authDb?
 * AuthDB helpers are thin wrappers around Dexie operations. Mocking Dexie
 * would only test that we call the right method — not that the data actually
 * persists and is retrieved correctly. Using fake-indexeddb verifies the
 * full round-trip: put → get → delete.
 */

import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'

// We import the module under test AFTER fake-indexeddb/auto is loaded so
// that Dexie picks up the fake IDBFactory instead of undefined (jsdom has no
// real IndexedDB).
import {
  authDb,
  getRefreshToken,
  setRefreshToken,
  deleteRefreshToken,
  getLastUserId,
  setLastUserId,
  deleteLastUserId,
  clearAuthDb,
} from '../auth-db'

// ---------------------------------------------------------------------------
// Reset the auth table between tests to keep them isolated
// ---------------------------------------------------------------------------
beforeEach(async () => {
  await authDb.auth.clear()
})

// ---------------------------------------------------------------------------
// AuthDB schema
// ---------------------------------------------------------------------------
describe('authDb instance', () => {
  it('has a table named auth', () => {
    expect(authDb.auth).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// refresh_token helpers
// ---------------------------------------------------------------------------
describe('refresh_token helpers', () => {
  it('returns undefined when no refresh_token is stored', async () => {
    const value = await getRefreshToken()
    expect(value).toBeUndefined()
  })

  it('stores and retrieves a refresh_token', async () => {
    await setRefreshToken('token-abc-123')
    const value = await getRefreshToken()
    expect(value).toBe('token-abc-123')
  })

  it('overwrites existing refresh_token on setRefreshToken', async () => {
    await setRefreshToken('old-token')
    await setRefreshToken('new-token')
    const value = await getRefreshToken()
    expect(value).toBe('new-token')
  })

  it('removes refresh_token after deleteRefreshToken', async () => {
    await setRefreshToken('token-to-delete')
    await deleteRefreshToken()
    const value = await getRefreshToken()
    expect(value).toBeUndefined()
  })

  it('deleteRefreshToken is idempotent when called twice', async () => {
    await deleteRefreshToken()
    await deleteRefreshToken()
    const value = await getRefreshToken()
    expect(value).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// last_user_id helpers
// ---------------------------------------------------------------------------
describe('last_user_id helpers', () => {
  it('returns undefined when no last_user_id is stored', async () => {
    const value = await getLastUserId()
    expect(value).toBeUndefined()
  })

  it('stores and retrieves a last_user_id', async () => {
    await setLastUserId('user-uuid-456')
    const value = await getLastUserId()
    expect(value).toBe('user-uuid-456')
  })

  it('overwrites existing last_user_id on setLastUserId', async () => {
    await setLastUserId('old-user-id')
    await setLastUserId('new-user-id')
    const value = await getLastUserId()
    expect(value).toBe('new-user-id')
  })

  it('removes last_user_id after deleteLastUserId', async () => {
    await setLastUserId('user-to-delete')
    await deleteLastUserId()
    const value = await getLastUserId()
    expect(value).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// clearAuthDb
// ---------------------------------------------------------------------------
describe('clearAuthDb', () => {
  it('clears both refresh_token and last_user_id', async () => {
    await setRefreshToken('some-token')
    await setLastUserId('some-user-id')

    await clearAuthDb()

    expect(await getRefreshToken()).toBeUndefined()
    expect(await getLastUserId()).toBeUndefined()
  })

  it('is safe to call on an already-empty db', async () => {
    await expect(clearAuthDb()).resolves.not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// Isolation: refresh_token and last_user_id use different keys
// ---------------------------------------------------------------------------
describe('key isolation', () => {
  it('refresh_token and last_user_id are stored under separate keys', async () => {
    await setRefreshToken('rt-value')
    await setLastUserId('uid-value')

    expect(await getRefreshToken()).toBe('rt-value')
    expect(await getLastUserId()).toBe('uid-value')

    await deleteRefreshToken()
    // last_user_id should NOT be affected
    expect(await getLastUserId()).toBe('uid-value')
  })
})
