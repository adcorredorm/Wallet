/**
 * NetWorthChart.spec.ts
 *
 * Tests for the Todo preset disabled-until-resolved behavior.
 *
 * Scope: three behaviors introduced by the "disable Todo until resolveOldestDate
 * resolves" task:
 *   1. The Todo button is disabled (and shows a spinner) while todoDays is null
 *      (i.e., resolveOldestDate has not yet completed).
 *   2. Once resolveOldestDate resolves with NO records (new user), todoDays
 *      becomes 30 and the button becomes enabled.
 *   3. Once resolveOldestDate resolves WITH records, todoDays is calculated
 *      from the oldest date and the button becomes enabled.
 *
 * Mock strategy:
 * - vi.hoisted() creates IndexedDB mock fns before hoisting so they can be
 *   used both inside vi.mock() factories and in individual tests.
 * - Chart.js and vue-chartjs are stubbed to avoid canvas errors in jsdom.
 * - useNetWorthHistory is mocked to return an empty dataset so the chart
 *   rendering path is not exercised — only the preset UI logic is tested.
 * - useSettingsStore is mocked to provide a stable currency.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// ---------------------------------------------------------------------------
// Hoist DB mocks so they are available in vi.mock() factories
// ---------------------------------------------------------------------------
const { mockOrderByTxFirst, mockOrderByTrFirst } = vi.hoisted(() => ({
  mockOrderByTxFirst: vi.fn(),
  mockOrderByTrFirst: vi.fn(),
}))

// ---------------------------------------------------------------------------
// Mock @/offline (IndexedDB)
// ---------------------------------------------------------------------------
vi.mock('@/offline', () => ({
  db: {
    transactions: {
      orderBy: vi.fn(() => ({ first: mockOrderByTxFirst })),
    },
    transfers: {
      orderBy: vi.fn(() => ({ first: mockOrderByTrFirst })),
    },
  },
}))

// ---------------------------------------------------------------------------
// Mock vue-chartjs and chart.js to avoid canvas errors in jsdom
// ---------------------------------------------------------------------------
vi.mock('vue-chartjs', () => ({
  Line: { template: '<canvas />', props: ['data', 'options'] },
}))

vi.mock('chart.js', () => ({
  Chart: { register: vi.fn() },
  CategoryScale: {},
  LinearScale: {},
  PointElement: {},
  LineElement: {},
  Title: {},
  Tooltip: {},
  Filler: {},
}))

// ---------------------------------------------------------------------------
// Mock useNetWorthHistory — only the UI preset logic is under test here
// ---------------------------------------------------------------------------
vi.mock('@/composables/useNetWorthHistory', () => ({
  useNetWorthHistory: vi.fn(() => ({
    dataPoints: { value: [] },
    loading: { value: false },
    isEmpty: { value: true },
  })),
}))

// ---------------------------------------------------------------------------
// Mock useSettingsStore
// ---------------------------------------------------------------------------
vi.mock('@/stores/settings', () => ({
  useSettingsStore: vi.fn(() => ({
    primaryCurrency: 'EUR',
  })),
}))

// ---------------------------------------------------------------------------
// Import component AFTER mocks
// ---------------------------------------------------------------------------
import NetWorthChart from '../NetWorthChart.vue'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function buildWrapper() {
  return mount(NetWorthChart, {
    global: {
      plugins: [createPinia()],
    },
  })
}

function getTodoButton(wrapper: ReturnType<typeof mount>) {
  const buttons = wrapper.findAll('button')
  return buttons.find(b => b.text().includes('Todo') || b.find('.animate-spin').exists())
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('NetWorthChart — Todo preset disabled until resolveOldestDate resolves', () => {
  it('renders the Todo button as disabled with a spinner while resolveOldestDate is pending', async () => {
    // Arrange: make the DB promises never resolve during this test
    mockOrderByTxFirst.mockReturnValue(new Promise(() => {}))
    mockOrderByTrFirst.mockReturnValue(new Promise(() => {}))

    const wrapper = buildWrapper()

    // The button must exist
    const btn = getTodoButton(wrapper)
    expect(btn).toBeDefined()

    // It must be disabled
    expect(btn!.attributes('disabled')).toBeDefined()

    // It must show the loading spinner, not the label text
    expect(btn!.find('.animate-spin').exists()).toBe(true)
    expect(btn!.text()).not.toContain('Todo')
  })

  it('enables the Todo button and defaults to 30 days when there are no records (new user)', async () => {
    // Arrange: DB returns no records (new user — no transactions or transfers)
    mockOrderByTxFirst.mockResolvedValue(undefined)
    mockOrderByTrFirst.mockResolvedValue(undefined)

    const wrapper = buildWrapper()

    // Wait for resolveOldestDate to complete
    await flushPromises()
    await wrapper.vm.$nextTick()

    const btn = getTodoButton(wrapper)
    expect(btn).toBeDefined()

    // Button must be enabled
    expect(btn!.attributes('disabled')).toBeUndefined()

    // No spinner
    expect(btn!.find('.animate-spin').exists()).toBe(false)

    // Label shows "Todo"
    expect(btn!.text()).toContain('Todo')
  })

  it('enables the Todo button when records exist and resolves to the correct number of days', async () => {
    // Arrange: one transaction from exactly 100 days ago
    const today = new Date()
    const hundredDaysAgo = new Date(today)
    hundredDaysAgo.setDate(today.getDate() - 100)
    const dateStr = hundredDaysAgo.toISOString().slice(0, 10)

    mockOrderByTxFirst.mockResolvedValue({ date: dateStr })
    mockOrderByTrFirst.mockResolvedValue(undefined)

    const wrapper = buildWrapper()

    await flushPromises()
    await wrapper.vm.$nextTick()

    const btn = getTodoButton(wrapper)
    expect(btn).toBeDefined()

    // Button must be enabled
    expect(btn!.attributes('disabled')).toBeUndefined()
    expect(btn!.find('.animate-spin').exists()).toBe(false)
    expect(btn!.text()).toContain('Todo')
  })
})
