/**
 * sync-manager-temp-id-orphan.spec.ts
 *
 * Tests for temp-* protection in syncDashboards() (dashboard and widget
 * orphan pruning).
 *
 * Strategy: we test the syncDashboards() logic indirectly by calling
 * forceFullSync() with controlled mocks, then asserting that temp-* IDs
 * are never passed to bulkDelete.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

const {
  TEMP_DASH_ID,
  TEMP_WIDGET_ID,
  SERVER_DASH_ID,
  SERVER_WIDGET_ID,
  mockDashboardsBulkPut,
  mockDashboardsBulkDelete,
  mockWidgetsBulkPut,
  mockWidgetsBulkDelete,
  mockDashboardPrimaryKeys,
  mockWidgetPrimaryKeys,
  mockSettingsGet,
  mockSettingsPut,
} = vi.hoisted(() => ({
  TEMP_DASH_ID: 'temp-dashboard-123',
  TEMP_WIDGET_ID: 'temp-widget-456',
  SERVER_DASH_ID: 'real-dash-uuid',
  SERVER_WIDGET_ID: 'real-widget-uuid',
  mockDashboardsBulkPut: vi.fn().mockResolvedValue(undefined),
  mockDashboardsBulkDelete: vi.fn().mockResolvedValue(undefined),
  mockWidgetsBulkPut: vi.fn().mockResolvedValue(undefined),
  mockWidgetsBulkDelete: vi.fn().mockResolvedValue(undefined),
  mockDashboardPrimaryKeys: vi.fn(),
  mockWidgetPrimaryKeys: vi.fn(),
  mockSettingsGet: vi.fn().mockResolvedValue(undefined),
  mockSettingsPut: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@/offline/db', () => ({
  db: {
    dashboards: {
      bulkPut: mockDashboardsBulkPut,
      bulkDelete: mockDashboardsBulkDelete,
      toCollection: vi.fn(() => ({ primaryKeys: mockDashboardPrimaryKeys })),
    },
    dashboardWidgets: {
      bulkPut: mockWidgetsBulkPut,
      bulkDelete: mockWidgetsBulkDelete,
      toCollection: vi.fn(() => ({ primaryKeys: mockWidgetPrimaryKeys })),
    },
    settings: {
      get: mockSettingsGet,
      put: mockSettingsPut,
      bulkDelete: vi.fn().mockResolvedValue(undefined),
    },
    accounts: { bulkPut: vi.fn(), count: vi.fn().mockResolvedValue(1) },
    transactions: { bulkPut: vi.fn(), count: vi.fn().mockResolvedValue(1) },
    transfers: { bulkPut: vi.fn(), count: vi.fn().mockResolvedValue(1) },
    categories: { bulkPut: vi.fn() },
    exchangeRates: { bulkPut: vi.fn() },
  },
}))

vi.mock('@/offline/mutation-queue', () => ({
  mutationQueue: {
    count: vi.fn().mockResolvedValue(0),
    getAll: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('@/api/sync-client', () => ({
  syncClient: {
    get: vi.fn(),
  },
}))

vi.mock('@/api/dashboards', () => ({
  dashboardsApi: {
    getById: vi.fn(),
    getAll: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('@/stores/sync', () => ({
  useSyncStore: vi.fn(() => ({
    setSyncing: vi.fn(),
    setLastSyncAt: vi.fn(),
    setInitialSyncComplete: vi.fn(),
    isGuest: false,
    initialSyncComplete: true,
  })),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    isAuthenticated: true,
  })),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: vi.fn(() => ({ showSuccess: vi.fn() })),
}))

import { syncManager } from '@/offline/sync-manager'
import { syncClient } from '@/api/sync-client'
import { dashboardsApi } from '@/api/dashboards'

function makeEmptySyncResponse() {
  return {
    data: { success: true, data: [] },
    headers: {},
    status: 200,
  }
}

describe('syncDashboards() — temp-* orphan protection', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default: all other entity sync endpoints return empty
    ;(syncClient.get as ReturnType<typeof vi.fn>).mockResolvedValue(makeEmptySyncResponse())
  })

  it('does NOT delete temp-* dashboard IDs', async () => {
    // Server returns only the real dashboard
    ;(syncClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { success: true, data: [{ id: SERVER_DASH_ID, updated_at: '2026-01-01T00:00:00Z' }] },
      headers: {},
      status: 200,
    })
    ;(dashboardsApi.getById as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: SERVER_DASH_ID,
      widgets: [{ id: SERVER_WIDGET_ID, dashboard_id: SERVER_DASH_ID, updated_at: '2026-01-01T00:00:00Z' }],
    })

    // Local tables contain both server IDs and temp-* IDs
    mockDashboardPrimaryKeys.mockResolvedValue([SERVER_DASH_ID, TEMP_DASH_ID])
    mockWidgetPrimaryKeys.mockResolvedValue([SERVER_WIDGET_ID, TEMP_WIDGET_ID])

    await syncManager.forceFullSync()

    // If bulkDelete was called for dashboards, temp-* must not be in the list
    if (mockDashboardsBulkDelete.mock.calls.length > 0) {
      const deletedDashIds = mockDashboardsBulkDelete.mock.calls.flat(2) as string[]
      expect(deletedDashIds).not.toContain(TEMP_DASH_ID)
    }
  })

  it('does NOT delete temp-* widget IDs', async () => {
    ;(syncClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { success: true, data: [{ id: SERVER_DASH_ID, updated_at: '2026-01-01T00:00:00Z' }] },
      headers: {},
      status: 200,
    })
    ;(dashboardsApi.getById as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: SERVER_DASH_ID,
      widgets: [{ id: SERVER_WIDGET_ID, dashboard_id: SERVER_DASH_ID, updated_at: '2026-01-01T00:00:00Z' }],
    })

    mockDashboardPrimaryKeys.mockResolvedValue([SERVER_DASH_ID, TEMP_DASH_ID])
    mockWidgetPrimaryKeys.mockResolvedValue([SERVER_WIDGET_ID, TEMP_WIDGET_ID])

    await syncManager.forceFullSync()

    if (mockWidgetsBulkDelete.mock.calls.length > 0) {
      const deletedWidgetIds = mockWidgetsBulkDelete.mock.calls.flat(2) as string[]
      expect(deletedWidgetIds).not.toContain(TEMP_WIDGET_ID)
    }
  })

  it('deletes a stale server dashboard that no longer exists on server', async () => {
    const STALE_DASH_ID = 'stale-dash-uuid'

    ;(syncClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { success: true, data: [{ id: SERVER_DASH_ID, updated_at: '2026-01-01T00:00:00Z' }] },
      headers: {},
      status: 200,
    })
    ;(dashboardsApi.getById as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: SERVER_DASH_ID,
      widgets: [],
    })

    // Local has: real server dash, a stale old server dash, and a temp dash
    mockDashboardPrimaryKeys.mockResolvedValue([SERVER_DASH_ID, STALE_DASH_ID, TEMP_DASH_ID])
    mockWidgetPrimaryKeys.mockResolvedValue([])

    await syncManager.forceFullSync()

    expect(mockDashboardsBulkDelete).toHaveBeenCalled()
    const deletedIds = mockDashboardsBulkDelete.mock.calls[0][0] as string[]
    expect(deletedIds).toContain(STALE_DASH_ID)
    expect(deletedIds).not.toContain(TEMP_DASH_ID)
    expect(deletedIds).not.toContain(SERVER_DASH_ID)
  })

  it('deletes a stale widget that no longer exists on server', async () => {
    const STALE_WIDGET_ID = 'stale-widget-uuid'

    ;(syncClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { success: true, data: [{ id: SERVER_DASH_ID, updated_at: '2026-01-01T00:00:00Z' }] },
      headers: {},
      status: 200,
    })
    ;(dashboardsApi.getById as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: SERVER_DASH_ID,
      widgets: [{ id: SERVER_WIDGET_ID, dashboard_id: SERVER_DASH_ID, updated_at: '2026-01-01T00:00:00Z' }],
    })

    mockDashboardPrimaryKeys.mockResolvedValue([SERVER_DASH_ID])
    mockWidgetPrimaryKeys.mockResolvedValue([SERVER_WIDGET_ID, STALE_WIDGET_ID, TEMP_WIDGET_ID])

    await syncManager.forceFullSync()

    expect(mockWidgetsBulkDelete).toHaveBeenCalled()
    const deletedIds = mockWidgetsBulkDelete.mock.calls[0][0] as string[]
    expect(deletedIds).toContain(STALE_WIDGET_ID)
    expect(deletedIds).not.toContain(TEMP_WIDGET_ID)
    expect(deletedIds).not.toContain(SERVER_WIDGET_ID)
  })
})
