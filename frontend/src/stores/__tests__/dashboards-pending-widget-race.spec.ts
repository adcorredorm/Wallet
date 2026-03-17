/**
 * dashboards-pending-widget-race.spec.ts
 *
 * Regression tests for two related bugs in fetchDashboard() background revalidation:
 *
 * BUG 1 — race condition wipes pending widgets:
 *   The revalidation did bulkDelete(allWidgets) then bulkPut(server+pending).
 *   If two concurrent revalidations ran, the second captured pendingWidgets=[]
 *   (the first had already deleted them) and set currentDashboard.widgets=[],
 *   permanently hiding the pending widget from the UI.
 *
 * BUG 2 — error-status widgets silently deleted:
 *   The filter at line ~149 only preserved _sync_status==='pending' widgets.
 *   A widget whose CREATE mutation failed (status='error') was deleted by
 *   bulkDelete and never re-added, permanently removing it from Dexie and UI.
 *
 * Fix: never delete unsynced widgets. Instead upsert server widgets, delete
 * only 'synced' widgets absent from server response, then read all from Dexie.
 */

import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import type { LocalDashboardWidget } from '@/offline/types'

// ── Hoisted constants & mocks ─────────────────────────────────────────────────
const {
  DASHBOARD_ID,
  PENDING_WIDGET_ID,
  ERROR_WIDGET_ID,
  mockDashboardsGet,
  mockDashboardsPut,
  widgetStore,
} = vi.hoisted(() => {
  const widgetStore = { widgets: [] as LocalDashboardWidget[] }
  return {
    DASHBOARD_ID: 'dashboard-real-uuid',
    PENDING_WIDGET_ID: 'temp-widget-pending',
    ERROR_WIDGET_ID: 'temp-widget-error',
    mockDashboardsGet: vi.fn(),
    mockDashboardsPut: vi.fn(),
    widgetStore,
  }
})

vi.mock('@/offline', () => {
  const widgetTableFor = (filterId: string) => ({
    toArray: async () => widgetStore.widgets.filter(w => w.dashboard_id === filterId),
    filter: (fn: (w: LocalDashboardWidget) => boolean) => ({
      toArray: async () => widgetStore.widgets.filter(w => w.dashboard_id === filterId && fn(w)),
      primaryKeys: async () =>
        widgetStore.widgets
          .filter(w => w.dashboard_id === filterId && fn(w))
          .map(w => w.id),
    }),
    primaryKeys: async () =>
      widgetStore.widgets.filter(w => w.dashboard_id === filterId).map(w => w.id),
  })

  return {
    db: {
      dashboards: {
        get: mockDashboardsGet,
        put: mockDashboardsPut,
        toArray: vi.fn().mockResolvedValue([]),
        where: vi.fn().mockReturnValue({
          equals: vi.fn().mockReturnValue({
            toArray: vi.fn().mockResolvedValue([]),
          }),
        }),
      },
      dashboardWidgets: {
        where: (_field: string) => ({
          equals: (val: string) => widgetTableFor(val),
        }),
        bulkPut: async (items: LocalDashboardWidget[]) => {
          for (const item of items) {
            const idx = widgetStore.widgets.findIndex(w => w.id === item.id)
            if (idx >= 0) widgetStore.widgets[idx] = item
            else widgetStore.widgets.push(item)
          }
        },
        bulkDelete: async (ids: string[]) => {
          widgetStore.widgets = widgetStore.widgets.filter(w => !ids.includes(w.id))
        },
        put: vi.fn().mockResolvedValue(undefined),
      },
    },
    mutationQueue: {
      enqueue: vi.fn().mockResolvedValue(undefined),
      findPendingCreate: vi.fn().mockResolvedValue(null),
    },
  }
})

vi.mock('@/offline/temp-id', () => ({
  generateTempId: vi.fn().mockReturnValue('temp-new'),
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: vi.fn(() => ({ primaryCurrency: 'USD' })),
}))

// Server returns 0 widgets for this dashboard
vi.mock('@/api/dashboards', () => ({
  dashboardsApi: {
    getById: vi.fn().mockResolvedValue({
      id: DASHBOARD_ID,
      name: 'Test',
      display_currency: 'USD',
      layout_columns: 2,
      is_default: false,
      sort_order: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      widgets: [],
    }),
    getAll: vi.fn().mockResolvedValue([]),
  },
}))

import { useDashboardsStore } from '@/stores/dashboards'

// ── Helpers ───────────────────────────────────────────────────────────────────
function makeWidget(id: string, status: 'pending' | 'error' | 'synced'): LocalDashboardWidget {
  return {
    id,
    offline_id: id,
    dashboard_id: DASHBOARD_ID,
    widget_type: 'number',
    title: `Widget ${id}`,
    position_x: 0, position_y: 0, width: 1, height: 1,
    config: {
      time_range: { type: 'dynamic', value: 'this_month' },
      filters: {}, granularity: 'month', group_by: 'none', aggregation: 'sum',
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    _sync_status: status,
    _local_updated_at: new Date().toISOString(),
  }
}

function setupDashboardInDexie() {
  mockDashboardsGet.mockResolvedValue({
    id: DASHBOARD_ID, name: 'Test', display_currency: 'USD',
    layout_columns: 2, is_default: false, sort_order: 0,
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    _sync_status: 'synced', _local_updated_at: new Date().toISOString(),
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('fetchDashboard — unsynced widgets survive background revalidation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    setupDashboardInDexie()
  })

  it('keeps a pending widget in the UI after server returns 0 widgets', async () => {
    widgetStore.widgets = [makeWidget(PENDING_WIDGET_ID, 'pending')]
    const store = useDashboardsStore()

    await store.fetchDashboard(DASHBOARD_ID)
    await new Promise(r => setTimeout(r, 50))

    expect(store.currentDashboard?.widgets.some(w => w.id === PENDING_WIDGET_ID)).toBe(true)
  })

  it('keeps a pending widget in Dexie after server returns 0 widgets', async () => {
    widgetStore.widgets = [makeWidget(PENDING_WIDGET_ID, 'pending')]
    const store = useDashboardsStore()

    await store.fetchDashboard(DASHBOARD_ID)
    await new Promise(r => setTimeout(r, 50))

    expect(widgetStore.widgets.find(w => w.id === PENDING_WIDGET_ID)).toBeDefined()
  })

  it('keeps an error-status widget in Dexie after server returns 0 widgets', async () => {
    // Simulates a widget whose CREATE mutation failed permanently
    widgetStore.widgets = [makeWidget(ERROR_WIDGET_ID, 'error')]
    const store = useDashboardsStore()

    await store.fetchDashboard(DASHBOARD_ID)
    await new Promise(r => setTimeout(r, 50))

    expect(widgetStore.widgets.find(w => w.id === ERROR_WIDGET_ID)).toBeDefined()
  })

  it('keeps an error-status widget in the UI after server returns 0 widgets', async () => {
    widgetStore.widgets = [makeWidget(ERROR_WIDGET_ID, 'error')]
    const store = useDashboardsStore()

    await store.fetchDashboard(DASHBOARD_ID)
    await new Promise(r => setTimeout(r, 50))

    expect(store.currentDashboard?.widgets.some(w => w.id === ERROR_WIDGET_ID)).toBe(true)
  })

  it('does not wipe pending widgets when two concurrent fetchDashboard calls race', async () => {
    widgetStore.widgets = [makeWidget(PENDING_WIDGET_ID, 'pending')]
    const store = useDashboardsStore()

    await Promise.all([
      store.fetchDashboard(DASHBOARD_ID),
      store.fetchDashboard(DASHBOARD_ID),
    ])
    await new Promise(r => setTimeout(r, 100))

    expect(widgetStore.widgets.find(w => w.id === PENDING_WIDGET_ID)).toBeDefined()
    expect(store.currentDashboard?.widgets.some(w => w.id === PENDING_WIDGET_ID)).toBe(true)
  })
})
