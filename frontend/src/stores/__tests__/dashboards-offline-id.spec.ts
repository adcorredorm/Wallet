/**
 * dashboards-offline-id.spec.ts
 *
 * Regression tests for the bug where dashboard and widget optimistic records
 * were written to Dexie WITHOUT an offline_id field, causing the SyncManager's
 * findServerId() fallback to fail and widget mutations to be permanently dropped.
 *
 * Root cause: createDashboard() and createWidget() did not set offline_id on
 * the LocalDashboard / LocalDashboardWidget records stored in IndexedDB.
 * After resolveTemporaryId() replaced the temp-* record with the real UUID,
 * findServerId() fell back to scanning by offline_id — which was undefined —
 * so it could not resolve the dashboard_id in widget payloads. The widget POST
 * then went to /api/v1/dashboards/temp-…/widgets, received a 4xx, and the
 * mutation was permanently discarded.
 */

import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'

const { mockDashboardsPut, mockWidgetsPut, mockDashboardsToArray, TEMP_ID } = vi.hoisted(() => ({
  mockDashboardsPut: vi.fn().mockResolvedValue(undefined),
  mockWidgetsPut: vi.fn().mockResolvedValue(undefined),
  mockDashboardsToArray: vi.fn().mockResolvedValue([]),
  TEMP_ID: 'temp-abc123',
}))

vi.mock('@/offline', () => ({
  db: {
    dashboards: {
      put: mockDashboardsPut,
      toArray: mockDashboardsToArray,
      get: vi.fn().mockResolvedValue(undefined),
    },
    dashboardWidgets: {
      put: mockWidgetsPut,
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
    updatePayload: vi.fn().mockResolvedValue(undefined),
  },
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: vi.fn(() => ({
    primaryCurrency: 'USD',
  })),
}))

vi.mock('@/offline/temp-id', () => ({
  generateTempId: vi.fn().mockReturnValue(TEMP_ID),
}))

import { useDashboardsStore } from '@/stores/dashboards'

describe('useDashboardsStore — offline_id on optimistic records', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockDashboardsToArray.mockResolvedValue([])
  })

  describe('createDashboard', () => {
    it('writes offline_id equal to the temp id on the Dexie record', async () => {
      const store = useDashboardsStore()

      await store.createDashboard({ name: 'Mi Dashboard', display_currency: 'USD', layout_columns: 2 })

      const dexieRecord = mockDashboardsPut.mock.calls[0][0]
      expect(dexieRecord.offline_id).toBe(TEMP_ID)
    })

    it('uses the same value for id and offline_id (both = tempId)', async () => {
      const store = useDashboardsStore()

      await store.createDashboard({ name: 'Test', display_currency: 'USD', layout_columns: 2 })

      const dexieRecord = mockDashboardsPut.mock.calls[0][0]
      expect(dexieRecord.id).toBe(TEMP_ID)
      expect(dexieRecord.offline_id).toBe(TEMP_ID)
    })
  })

  describe('createWidget', () => {
    it('writes offline_id equal to the temp id on the Dexie record', async () => {
      const store = useDashboardsStore()

      await store.createWidget('dashboard-real-uuid', {
        widget_type: 'number',
        title: 'Total',
        position_x: 0,
        position_y: 0,
        width: 1,
        height: 1,
        config: {
          time_range: { type: 'dynamic', value: 'this_month' },
          filters: {},
          granularity: 'month',
          group_by: 'none',
          aggregation: 'sum',
        },
      })

      const dexieRecord = mockWidgetsPut.mock.calls[0][0]
      expect(dexieRecord.offline_id).toBe(TEMP_ID)
    })

    it('uses the same value for id and offline_id (both = tempId)', async () => {
      const store = useDashboardsStore()

      await store.createWidget('dashboard-real-uuid', {
        widget_type: 'bar',
        title: 'Bar',
        position_x: 0,
        position_y: 0,
        width: 2,
        height: 1,
        config: {
          time_range: { type: 'dynamic', value: 'this_month' },
          filters: {},
          granularity: 'month',
          group_by: 'category',
          aggregation: 'sum',
        },
      })

      const dexieRecord = mockWidgetsPut.mock.calls[0][0]
      expect(dexieRecord.id).toBe(TEMP_ID)
      expect(dexieRecord.offline_id).toBe(TEMP_ID)
    })
  })
})
