/**
 * settings-hide-balances.spec.ts
 *
 * Tests for the hide_balances feature in useSettingsStore.
 *
 * What we test:
 * 1. hideBalances defaults to false
 * 2. toggleHideBalances() sets it to true
 * 3. toggleHideBalances() toggles back to false
 * 4. toggleHideBalances() writes to Dexie with _sync_status: 'synced'
 * 5. hideBalances is exposed in the store return
 * 6. toggleHideBalances is exposed in the store return
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------
const { mockSettingsPut, mockSettingsToArray, mockSettingsWhere } = vi.hoisted(() => ({
  mockSettingsPut: vi.fn().mockResolvedValue(undefined),
  mockSettingsToArray: vi.fn().mockResolvedValue([]),
  mockSettingsWhere: vi.fn().mockReturnValue({
    equals: vi.fn().mockReturnValue({
      toArray: vi.fn().mockResolvedValue([])
    })
  })
}))

vi.mock('@/offline', () => ({
  db: {
    settings: {
      put: mockSettingsPut,
      toArray: mockSettingsToArray,
      where: mockSettingsWhere
    }
  },
  mutationQueue: {
    enqueue: vi.fn().mockResolvedValue(undefined)
  }
}))

vi.mock('@/api/settings', () => ({
  fetchSettings: vi.fn().mockResolvedValue({})
}))

// Import AFTER mocks
import { useSettingsStore } from '../settings'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('useSettingsStore — hide_balances', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockSettingsPut.mockResolvedValue(undefined)
    mockSettingsToArray.mockResolvedValue([])
    mockSettingsWhere.mockReturnValue({
      equals: vi.fn().mockReturnValue({
        toArray: vi.fn().mockResolvedValue([])
      })
    })
  })

  it('hideBalances defaults to false', () => {
    const store = useSettingsStore()
    expect(store.hideBalances).toBe(false)
  })

  it('toggleHideBalances() sets hideBalances to true', async () => {
    const store = useSettingsStore()
    expect(store.hideBalances).toBe(false)

    await store.toggleHideBalances()

    expect(store.hideBalances).toBe(true)
  })

  it('toggleHideBalances() toggles back to false on second call', async () => {
    const store = useSettingsStore()

    await store.toggleHideBalances()
    expect(store.hideBalances).toBe(true)

    await store.toggleHideBalances()
    expect(store.hideBalances).toBe(false)
  })

  it('toggleHideBalances() writes to Dexie with _sync_status: synced', async () => {
    const store = useSettingsStore()

    await store.toggleHideBalances()

    expect(mockSettingsPut).toHaveBeenCalledWith(
      expect.objectContaining({
        key: 'hide_balances',
        value: true,
        _sync_status: 'synced'
      })
    )
  })

  it('toggleHideBalances() never enqueues a mutation', async () => {
    const { mutationQueue } = await import('@/offline')
    const store = useSettingsStore()

    await store.toggleHideBalances()

    expect(mutationQueue.enqueue).not.toHaveBeenCalled()
  })

  it('hideBalances is exposed in the store', () => {
    const store = useSettingsStore()
    expect('hideBalances' in store).toBe(true)
  })

  it('toggleHideBalances is exposed in the store', () => {
    const store = useSettingsStore()
    expect('toggleHideBalances' in store).toBe(true)
    expect(typeof store.toggleHideBalances).toBe('function')
  })
})
