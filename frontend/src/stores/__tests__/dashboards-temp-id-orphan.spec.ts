/**
 * dashboards-temp-id-orphan.spec.ts
 *
 * Regression test: fetchDashboards() must NOT delete locally-created dashboards
 * with temp-* IDs during the orphan cleanup phase of background revalidation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const {
  TEMP_ID,
  SERVER_ID,
  mockDashboardsToArray,
  mockDashboardsPrimaryKeys,
  mockDashboardsBulkDelete,
  mockDashboardsBulkPut,
  mockGetAll,
} = vi.hoisted(() => ({
  TEMP_ID: 'temp-abc123',
  SERVER_ID: 'real-server-uuid',
  mockDashboardsToArray: vi.fn(),
  mockDashboardsPrimaryKeys: vi.fn(),
  mockDashboardsBulkDelete: vi.fn().mockResolvedValue(undefined),
  mockDashboardsBulkPut: vi.fn().mockResolvedValue(undefined),
  mockGetAll: vi.fn().mockResolvedValue([]),
}))

vi.mock('@/offline', () => ({
  db: {
    dashboards: {
      toArray: mockDashboardsToArray,
      bulkPut: mockDashboardsBulkPut,
      bulkDelete: mockDashboardsBulkDelete,
      toCollection: vi.fn().mockReturnValue({
        primaryKeys: mockDashboardsPrimaryKeys,
      }),
    },
    dashboardWidgets: {
      where: vi.fn().mockReturnValue({
        equals: vi.fn().mockReturnValue({
          toArray: vi.fn().mockResolvedValue([]),
        }),
      }),
    },
  },
  mutationQueue: {
    enqueue: vi.fn().mockResolvedValue(undefined),
    findPendingCreate: vi.fn().mockResolvedValue(null),
    getAll: mockGetAll,
  },
}))

vi.mock('@/api/dashboards', () => ({
  dashboardsApi: {
    getAll: vi.fn().mockResolvedValue([{ id: SERVER_ID, name: 'Server Dash', updated_at: '2026-01-01T00:00:00Z' }]),
    getById: vi.fn().mockResolvedValue({ id: SERVER_ID, name: 'Server Dash', updated_at: '2026-01-01T00:00:00Z', widgets: [] }),
  },
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: vi.fn(() => ({ primaryCurrency: 'USD' })),
}))

import { useDashboardsStore } from '@/stores/dashboards'

describe('fetchDashboards() — temp-* orphan protection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Local Dexie has: one server-synced record + one temp-* pending record
    mockDashboardsToArray.mockResolvedValue([
      { id: SERVER_ID, name: 'Server Dash', _sync_status: 'synced', _local_updated_at: '2026-01-01T00:00:00Z' },
      { id: TEMP_ID, name: 'Offline Dash', _sync_status: 'pending', _local_updated_at: '2026-01-02T00:00:00Z' },
    ])
    mockDashboardsPrimaryKeys.mockResolvedValue([SERVER_ID, TEMP_ID])
  })

  it('does NOT delete a temp-* dashboard during orphan cleanup', async () => {
    const store = useDashboardsStore()
    await store.fetchDashboards()

    // Give background async IIFE time to run
    await new Promise(resolve => setTimeout(resolve, 0))

    if (mockDashboardsBulkDelete.mock.calls.length > 0) {
      const deletedIds = mockDashboardsBulkDelete.mock.calls[0][0] as string[]
      expect(deletedIds).not.toContain(TEMP_ID)
    }
    // If bulkDelete was never called, the test also passes (nothing was deleted)
  })

  it('still deletes a genuine orphan (server record that was deleted on server)', async () => {
    const ORPHAN_ID = 'old-server-uuid'
    mockDashboardsPrimaryKeys.mockResolvedValue([SERVER_ID, TEMP_ID, ORPHAN_ID])

    const store = useDashboardsStore()
    await store.fetchDashboards()
    await new Promise(resolve => setTimeout(resolve, 0))

    // bulkDelete must have been called and must include ORPHAN_ID
    expect(mockDashboardsBulkDelete).toHaveBeenCalled()
    const deletedIds = mockDashboardsBulkDelete.mock.calls[0][0] as string[]
    expect(deletedIds).toContain(ORPHAN_ID)
    expect(deletedIds).not.toContain(TEMP_ID)
    expect(deletedIds).not.toContain(SERVER_ID)
  })
})
