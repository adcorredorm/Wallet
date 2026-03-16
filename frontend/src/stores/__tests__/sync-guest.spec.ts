/**
 * sync-guest.spec.ts
 *
 * Tests for the 'guest' status added to useSyncStore (Task 7).
 *
 * What we test:
 * 1. syncStatus returns 'guest' when isGuest is true and we are online
 * 2. syncStatus priority: offline > guest > syncing > error > pending > synced
 * 3. setGuest(true/false) correctly sets the isGuest flag
 * 4. isGuest is false by default
 * 5. When isGuest is false, syncStatus behaves exactly as before (no regression)
 * 6. useSyncStatus composable has a label and color for 'guest' state
 *
 * Priority rationale:
 * - 'offline' always wins — can't sync if there's no network
 * - 'guest' comes before syncing/error/pending — if not authenticated,
 *   those states are irrelevant because sync is intentionally skipped
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSyncStore } from '../sync'
import { useSyncStatus } from '@/composables/useSyncStatus'

function setup() {
  setActivePinia(createPinia())
  const store = useSyncStore()
  const status = useSyncStatus()
  return { store, status }
}

// ---------------------------------------------------------------------------
// isGuest initial state
// ---------------------------------------------------------------------------
describe('useSyncStore — isGuest initial state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('isGuest is false by default', () => {
    const store = useSyncStore()
    expect(store.isGuest).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// setGuest action
// ---------------------------------------------------------------------------
describe('useSyncStore — setGuest action', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('setGuest(true) sets isGuest to true', () => {
    const store = useSyncStore()
    store.setGuest(true)
    expect(store.isGuest).toBe(true)
  })

  it('setGuest(false) sets isGuest to false', () => {
    const store = useSyncStore()
    store.setGuest(true)
    store.setGuest(false)
    expect(store.isGuest).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// syncStatus — 'guest' token
// ---------------------------------------------------------------------------
describe('useSyncStore — syncStatus "guest" token', () => {
  it('returns "guest" when online and isGuest is true', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setGuest(true)
    expect(store.syncStatus).toBe('guest')
  })

  it('returns "offline" (not "guest") when offline even if isGuest is true', () => {
    const { store } = setup()
    store.setOnline(false)
    store.setGuest(true)
    expect(store.syncStatus).toBe('offline')
  })

  it('guest beats syncing: returns "guest" when online, isGuest=true, and isSyncing=true', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setGuest(true)
    store.setSyncing(true)
    expect(store.syncStatus).toBe('guest')
  })

  it('guest beats error: returns "guest" when online, isGuest=true, and errorCount>0', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setGuest(true)
    store.setErrorCount(3)
    expect(store.syncStatus).toBe('guest')
  })

  it('guest beats pending: returns "guest" when online, isGuest=true, and pendingCount>0', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setGuest(true)
    store.setPendingCount(5)
    expect(store.syncStatus).toBe('guest')
  })

  it('does NOT return "guest" when isGuest is false — falls through to normal logic', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setGuest(false)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(0)
    expect(store.syncStatus).toBe('synced')
  })
})

// ---------------------------------------------------------------------------
// useSyncStatus composable — label and color for guest
// ---------------------------------------------------------------------------
describe('useSyncStatus — "guest" label and color', () => {
  it('returns "Modo invitado" label when syncStatus is "guest"', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setGuest(true)
    expect(status.statusLabel.value).toBe('Modo invitado')
  })

  it('returns amber color when syncStatus is "guest"', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setGuest(true)
    // guest uses amber to signal a non-critical attention state
    expect(status.statusColor.value).toBe('text-amber-400')
  })
})

// ---------------------------------------------------------------------------
// Regression: existing syncStatus values still work when isGuest is false
// ---------------------------------------------------------------------------
describe('useSyncStore — regression: existing syncStatus behavior unchanged', () => {
  it('is "offline" when isOnline is false', () => {
    const { store } = setup()
    store.setOnline(false)
    expect(store.syncStatus).toBe('offline')
  })

  it('is "syncing" when online and isSyncing is true', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(true)
    expect(store.syncStatus).toBe('syncing')
  })

  it('is "error" when online, not syncing, errorCount > 0', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(1)
    expect(store.syncStatus).toBe('error')
  })

  it('is "pending" when online, not syncing, no errors, pendingCount > 0', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(2)
    expect(store.syncStatus).toBe('pending')
  })

  it('is "synced" when all is well', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(0)
    expect(store.syncStatus).toBe('synced')
  })
})
