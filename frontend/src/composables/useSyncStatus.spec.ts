/**
 * useSyncStatus.spec.ts
 *
 * Tests for the useSyncStatus composable.
 *
 * Why real Pinia (createPinia + setActivePinia) and NOT createTestingPinia?
 * useSyncStatus derives its output from computed properties on the sync store
 * (statusLabel, statusColor). Those computeds depend on the store's reactive
 * state. createTestingPinia stubs actions and optionally bypasses computed
 * getters, which would hide the very logic we want to verify. Using real
 * Pinia lets us set store state directly (store.setOnline(false), etc.) and
 * then assert that the composable's derived computeds update correctly —
 * end-to-end reactive correctness is what we are testing.
 *
 * Test isolation:
 * Each test gets a brand-new Pinia instance (beforeEach creates + activates it).
 * This prevents any state leakage between tests since Pinia stores are singletons
 * within a given Pinia context.
 *
 * navigator.onLine:
 * jsdom initialises navigator.onLine to true. The store initialises isOnline
 * from navigator.onLine at module evaluation time, so after setActivePinia the
 * default isOnline is true. Tests that need offline state explicitly call
 * store.setOnline(false).
 */

import { createPinia, setActivePinia } from 'pinia'
import { useSyncStatus } from './useSyncStatus'
import { useSyncStore } from '@/stores/sync'

// ---------------------------------------------------------------------------
// Helper: get a fresh store + composable pair with an isolated Pinia context
// ---------------------------------------------------------------------------
function setup() {
  setActivePinia(createPinia())
  const store = useSyncStore()
  const status = useSyncStatus()
  return { store, status }
}

// ---------------------------------------------------------------------------
// syncStatus priority — offline beats everything
// ---------------------------------------------------------------------------
describe('useSyncStatus — syncStatus token priority', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('is "offline" when isOnline is false regardless of other state', () => {
    const { store } = setup()
    store.setOnline(false)
    store.setSyncing(true)      // would be 'syncing' if online
    store.setPendingCount(5)    // would be 'pending' if online
    store.setErrorCount(2)      // would be 'error' if online
    expect(store.syncStatus).toBe('offline')
  })

  it('is "syncing" when online and isSyncing is true', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(true)
    expect(store.syncStatus).toBe('syncing')
  })

  it('is "error" when online, not syncing, and errorCount > 0', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(1)
    expect(store.syncStatus).toBe('error')
  })

  it('is "pending" when online, not syncing, no errors, and pendingCount > 0', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(3)
    expect(store.syncStatus).toBe('pending')
  })

  it('is "synced" when online, not syncing, no errors, and no pending', () => {
    const { store } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(0)
    expect(store.syncStatus).toBe('synced')
  })
})

// ---------------------------------------------------------------------------
// statusLabel — Spanish labels per status
// ---------------------------------------------------------------------------
describe('useSyncStatus — statusLabel', () => {
  it('returns "Sin conexión" when offline', () => {
    const { store, status } = setup()
    store.setOnline(false)
    expect(status.statusLabel.value).toBe('Sin conexión')
  })

  it('returns "Sincronizando..." when syncing', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(true)
    expect(status.statusLabel.value).toBe('Sincronizando...')
  })

  it('pluralises "pendientes" for pendingCount > 1', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setPendingCount(3)
    expect(status.statusLabel.value).toBe('3 pendientes')
  })

  it('uses singular "pendiente" for pendingCount === 1', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setPendingCount(1)
    expect(status.statusLabel.value).toBe('1 pendiente')
  })

  it('pluralises "errores" for errorCount > 1', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(2)
    expect(status.statusLabel.value).toBe('2 errores')
  })

  it('uses singular "error" for errorCount === 1', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(1)
    expect(status.statusLabel.value).toBe('1 error')
  })

  it('returns "Sincronizado" when synced and lastSyncAt is set', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(0)
    store.setLastSyncAt('2024-06-15T10:00:00.000Z')
    expect(status.statusLabel.value).toBe('Sincronizado')
  })

  it('returns "Listo" when synced and lastSyncAt is null (never synced)', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(0)
    // lastSyncAt defaults to null in a fresh store
    expect(status.statusLabel.value).toBe('Listo')
  })
})

// ---------------------------------------------------------------------------
// statusColor — Tailwind class per status
// ---------------------------------------------------------------------------
describe('useSyncStatus — statusColor', () => {
  it('returns "text-amber-400" when offline', () => {
    const { store, status } = setup()
    store.setOnline(false)
    expect(status.statusColor.value).toBe('text-amber-400')
  })

  it('returns "text-blue-400" when syncing', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(true)
    expect(status.statusColor.value).toBe('text-blue-400')
  })

  it('returns "text-amber-400" when pending', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setPendingCount(2)
    expect(status.statusColor.value).toBe('text-amber-400')
  })

  it('returns "text-red-400" when in error state', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(1)
    expect(status.statusColor.value).toBe('text-red-400')
  })

  it('returns "text-green-400" when synced', () => {
    const { store, status } = setup()
    store.setOnline(true)
    store.setSyncing(false)
    store.setErrorCount(0)
    store.setPendingCount(0)
    expect(status.statusColor.value).toBe('text-green-400')
  })
})

describe('syncStore — initialSyncComplete', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('is false by default', () => {
    const store = useSyncStore()
    expect(store.initialSyncComplete).toBe(false)
  })

  it('becomes true after setInitialSyncComplete(true)', () => {
    const store = useSyncStore()
    store.setInitialSyncComplete(true)
    expect(store.initialSyncComplete).toBe(true)
  })
})
