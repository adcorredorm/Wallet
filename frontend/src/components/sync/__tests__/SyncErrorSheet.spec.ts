/**
 * SyncErrorSheet.spec.ts
 *
 * Tests for the error sheet open/close behavior and discard flow.
 *
 * Why mount with a real Pinia (not createTestingPinia)?
 * The sheet reads syncStore.syncErrorSheetOpen and calls syncStore.setErrorCount().
 * Real Pinia lets us set the state and observe side effects without stubbing
 * every method.
 *
 * Why mock the entire @/offline/db module?
 * Dexie (IndexedDB) is not available in jsdom. All db calls in the sheet are
 * replaced with vi.fn() returning controlled data.
 *
 * Why attachTo: document.body?
 * SyncErrorSheet uses <Teleport to="body">, which renders content outside the
 * component wrapper. attachTo: document.body ensures Teleport finds a real DOM
 * target and the sheet content is queryable via document.body.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const {
  mockAccountsWhere,
  mockTransactionsWhere,
  mockTransfersWhere,
  mockCategoriesWhere,
  mockDashboardsWhere,
  mockDashboardWidgetsWhere,
  mockPendingMutationsWhere,
  mockPendingMutationsToArray,
  mockPendingMutationsDelete,
  mockAccountsDelete,
} = vi.hoisted(() => {
  // makeEmptyWhere returns a where() mock whose equals() chain supports both
  // .toArray() (used by loadErrors and cascadeDelete) and .count() (used by
  // computeDependentCount). Both must be on the same returned object.
  const makeEmptyWhere = () =>
    vi.fn().mockReturnValue({
      equals: vi.fn().mockReturnValue({
        toArray: vi.fn().mockResolvedValue([]),
        count: vi.fn().mockResolvedValue(0),
      }),
    })
  return {
    mockAccountsWhere: makeEmptyWhere(),
    mockTransactionsWhere: makeEmptyWhere(),
    mockTransfersWhere: makeEmptyWhere(),
    mockCategoriesWhere: makeEmptyWhere(),
    mockDashboardsWhere: makeEmptyWhere(),
    mockDashboardWidgetsWhere: makeEmptyWhere(),
    mockPendingMutationsWhere: vi.fn().mockReturnValue({ equals: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }) }),
    mockPendingMutationsToArray: vi.fn().mockResolvedValue([]),
    mockPendingMutationsDelete: vi.fn().mockResolvedValue(undefined),
    mockAccountsDelete: vi.fn().mockResolvedValue(undefined),
  }
})

vi.mock('@/offline/db', () => ({
  db: {
    accounts:         { where: mockAccountsWhere,         delete: mockAccountsDelete },
    transactions:     { where: mockTransactionsWhere,     delete: vi.fn() },
    transfers:        { where: mockTransfersWhere,        delete: vi.fn() },
    categories:       { where: mockCategoriesWhere,       delete: vi.fn() },
    dashboards:       { where: mockDashboardsWhere,       delete: vi.fn() },
    dashboardWidgets: { where: mockDashboardWidgetsWhere, delete: vi.fn() },
    pendingMutations: {
      where: mockPendingMutationsWhere,
      toArray: mockPendingMutationsToArray,
      delete: mockPendingMutationsDelete,
    },
    settings: { delete: vi.fn() },
  },
}))

vi.mock('@/offline/sync-manager', () => ({
  DEPENDENCY_FIELDS: {
    account: [],
    transaction: ['account_id', 'category_id'],
    transfer: ['source_account_id', 'destination_account_id'],
    category: ['parent_category_id'],
    setting: [],
    dashboard: [],
    dashboard_widget: ['dashboard_id'],
  },
  syncManager: {
    forceFullSync: vi.fn().mockResolvedValue(undefined),
    refreshErrorCount: vi.fn().mockResolvedValue(undefined),
  },
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: vi.fn(() => ({
    showConfirm: vi.fn().mockResolvedValue(true),
  })),
}))

import SyncErrorSheet from '@/components/sync/SyncErrorSheet.vue'
import { useSyncStore } from '@/stores/sync'

describe('SyncErrorSheet', () => {
  let wrappers: ReturnType<typeof mount>[] = []

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Default: all tables return empty arrays for both toArray() and count()
    const emptyChain = { toArray: vi.fn().mockResolvedValue([]), count: vi.fn().mockResolvedValue(0) }
    ;[
      mockAccountsWhere,
      mockTransactionsWhere,
      mockTransfersWhere,
      mockCategoriesWhere,
      mockDashboardsWhere,
      mockDashboardWidgetsWhere,
    ].forEach(mock => {
      mock.mockReturnValue({ equals: vi.fn().mockReturnValue(emptyChain) })
    })
    mockPendingMutationsWhere.mockReturnValue({
      equals: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }),
    })
    mockPendingMutationsToArray.mockResolvedValue([])
    wrappers = []
  })

  afterEach(() => {
    // Unmount all wrappers to clean up teleported DOM
    wrappers.forEach(w => w.unmount())
  })

  it('renders nothing when syncErrorSheetOpen is false', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(SyncErrorSheet, {
      global: { plugins: [pinia] },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    const syncStore = useSyncStore()
    syncStore.setSyncErrorSheetOpen(false)

    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
  })

  it('shows the sheet when syncErrorSheetOpen is set to true', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const syncStore = useSyncStore()

    const wrapper = mount(SyncErrorSheet, {
      global: { plugins: [pinia] },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    syncStore.setSyncErrorSheetOpen(true)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()
  })

  it('closes the sheet when the close button is clicked', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const syncStore = useSyncStore()
    syncStore.setSyncErrorSheetOpen(true)

    const wrapper = mount(SyncErrorSheet, {
      global: { plugins: [pinia] },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 20))

    // Click the close button (aria-label="Cerrar")
    const closeBtn = document.body.querySelector<HTMLElement>('button[aria-label="Cerrar"]')
    expect(closeBtn).not.toBeNull()
    closeBtn!.click()
    await wrapper.vm.$nextTick()

    expect(syncStore.syncErrorSheetOpen).toBe(false)
  })

  it('shows "No hay errores" when all tables return empty arrays', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const syncStore = useSyncStore()
    syncStore.setSyncErrorSheetOpen(true)

    const wrapper = mount(SyncErrorSheet, {
      global: { plugins: [pinia] },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(document.body.textContent).toContain('No hay errores')
  })

  it('renders an error item for each errored account', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)

    // Mount first with sheet closed, then configure mocks, then open
    const wrapper = mount(SyncErrorSheet, {
      global: { plugins: [pinia] },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    // Configure mocks BEFORE opening the sheet so loadErrors() sees them.
    // equals() must return both toArray() (loadErrors) and count() (computeDependentCount).
    mockAccountsWhere.mockReturnValue({
      equals: vi.fn().mockReturnValue({
        toArray: vi.fn().mockResolvedValue([
          { id: 'acc-1', name: 'Bancolombia', _sync_status: 'error', updated_at: '2026-01-01T00:00:00Z' },
        ]),
        count: vi.fn().mockResolvedValue(0),
      }),
    })
    mockPendingMutationsWhere.mockReturnValue({
      equals: vi.fn().mockReturnValue({
        toArray: vi.fn().mockResolvedValue([
          { id: 10, entity_id: 'acc-1', entity_type: 'account', operation: 'create', last_error: 'HTTP 422', payload: {} },
        ]),
      }),
    })
    mockPendingMutationsToArray.mockResolvedValue([])

    // Now open the sheet — this triggers the watch → loadErrors()
    const syncStore = useSyncStore()
    syncStore.setSyncErrorSheetOpen(true)

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 150))

    expect(document.body.textContent).toContain('Bancolombia')
    expect(document.body.textContent).toContain('HTTP 422')
  })
})
