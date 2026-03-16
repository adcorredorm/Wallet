/**
 * useNetWorthHistory.spec.ts
 *
 * Tests for the net worth history composable.
 *
 * Mock strategy: vi.hoisted() creates the mock fns before any hoisting occurs,
 * making them available both inside vi.mock() factories and in test bodies.
 * This is the correct Vitest pattern for sharing mock state between the factory
 * and the test suite.
 */

import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'

// All vi.hoisted() calls must be grouped together before vi.mock() calls.
// Vitest hoists vi.mock() blocks to the top of the file during transformation,
// so any variables used inside mock factories must themselves be hoisted.
const {
  mockTx,
  mockTr,
  mockAcc,
  mockSyncStore,
  mockTransactionsStore,
  mockTransfersStore,
} = vi.hoisted(() => {
  // Mutable state objects — tests modify these directly before each run.
  // Using plain objects (not Vue refs) because the mock factory captures them
  // by reference, so mutations in tests are visible to the mock.
  const syncState = { isSyncing: false, initialSyncComplete: true }
  const txState = { transactions: [] as unknown[] }
  const tfState = { transfers: [] as unknown[] }

  return {
    mockTx: vi.fn().mockResolvedValue([]),
    mockTr: vi.fn().mockResolvedValue([]),
    mockAcc: vi.fn().mockResolvedValue([]),
    mockSyncStore: { state: syncState },
    mockTransactionsStore: { state: txState },
    mockTransfersStore: { state: tfState },
  }
})

vi.mock('@/offline', () => ({
  db: {
    transactions: { toArray: mockTx },
    transfers: { toArray: mockTr },
    accounts: { toArray: mockAcc },
  },
}))

const mockGetRate = vi.fn().mockReturnValue(1)

vi.mock('@/stores/exchangeRates', () => ({
  useExchangeRatesStore: vi.fn(() => ({
    getRate: mockGetRate,
    loading: false,
    rates: [{ id: 'fake' }],
  })),
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: vi.fn(() => ({
    primaryCurrency: 'USD',
  })),
}))

vi.mock('@/stores/sync', () => ({
  useSyncStore: vi.fn(() => ({
    get isSyncing() { return mockSyncStore.state.isSyncing },
    get initialSyncComplete() { return mockSyncStore.state.initialSyncComplete },
  })),
}))

vi.mock('@/stores/transactions', () => ({
  useTransactionsStore: vi.fn(() => ({
    get transactions() { return mockTransactionsStore.state.transactions },
  })),
}))

vi.mock('@/stores/transfers', () => ({
  useTransfersStore: vi.fn(() => ({
    get transfers() { return mockTransfersStore.state.transfers },
  })),
}))

import { useNetWorthHistory } from './useNetWorthHistory'

/** Wait for watchEffect debounce (300ms) + async computation to complete */
async function settle(ms = 350) {
  await nextTick()
  await new Promise(r => setTimeout(r, ms))
}

describe('useNetWorthHistory — empty state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockGetRate.mockReturnValue(1)
    mockTx.mockResolvedValue([])
    mockTr.mockResolvedValue([])
    mockAcc.mockResolvedValue([])
    mockSyncStore.state.isSyncing = false
    mockSyncStore.state.initialSyncComplete = true
    mockTransactionsStore.state.transactions = []
    mockTransfersStore.state.transfers = []
  })

  it('returns isEmpty=true when no transactions or transfers', async () => {
    const { dataPoints, isEmpty } = useNetWorthHistory({ rangeDays: 30 })
    await settle()

    expect(isEmpty.value).toBe(true)
    expect(dataPoints.value).toHaveLength(0)
  })

  it('returns loading=false after computation completes', async () => {
    const { loading } = useNetWorthHistory({ rangeDays: 30 })
    await settle()
    expect(loading.value).toBe(false)
  })
})

describe('useNetWorthHistory — single income transaction', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockGetRate.mockReturnValue(1)
    mockTr.mockResolvedValue([])
    mockSyncStore.state.isSyncing = false
    mockSyncStore.state.initialSyncComplete = true
    mockTransactionsStore.state.transactions = []
    mockTransfersStore.state.transfers = []
  })

  it('produces correct net worth for a single income with base_rate=1', async () => {
    mockAcc.mockResolvedValue([{ id: 'acc-1', currency: 'USD', _sync_status: 'synced' }])
    mockTx.mockResolvedValue([{
      id: 'tx-1', type: 'income', amount: 100, date: '2026-01-05',
      account_id: 'acc-1', base_rate: 1, created_at: '2026-01-05T10:00:00Z',
    }])

    const { dataPoints, isEmpty } = useNetWorthHistory({
      rangeDays: 30,
      endDate: '2026-01-10',
    })
    await settle(350)

    expect(isEmpty.value).toBe(false)
    const pointAfterTx = dataPoints.value.find(p => p.date >= '2026-01-05')
    expect(pointAfterTx).toBeDefined()
    expect(pointAfterTx!.value).toBeCloseTo(100, 1)
  })

  it('uses base_rate=null fallback to getRate when base_rate is null', async () => {
    mockGetRate.mockReturnValue(4200)
    mockAcc.mockResolvedValue([{ id: 'acc-1', currency: 'USD', _sync_status: 'synced' }])
    mockTx.mockResolvedValue([{
      id: 'tx-1', type: 'income', amount: 100, date: '2026-01-05',
      account_id: 'acc-1', base_rate: null, created_at: '2026-01-05T10:00:00Z',
    }])

    const { dataPoints } = useNetWorthHistory({
      rangeDays: 30,
      endDate: '2026-01-10',
    })
    await settle(350)

    const pointAfterTx = dataPoints.value.find(p => p.date >= '2026-01-05')
    expect(pointAfterTx).toBeDefined()
    expect(pointAfterTx!.value).toBeCloseTo(100 * 4200, 0)
  })

  it('income increases net worth, expense decreases it', async () => {
    mockAcc.mockResolvedValue([{ id: 'acc-1', currency: 'USD', _sync_status: 'synced' }])
    mockTx.mockResolvedValue([
      { id: 'tx-1', type: 'income', amount: 500, date: '2026-01-01', account_id: 'acc-1', base_rate: 1, created_at: '2026-01-01T00:00:00Z' },
      { id: 'tx-2', type: 'expense', amount: 200, date: '2026-01-02', account_id: 'acc-1', base_rate: 1, created_at: '2026-01-02T00:00:00Z' },
    ])

    const { dataPoints } = useNetWorthHistory({
      rangeDays: 10,
      endDate: '2026-01-10',
    })
    await settle(350)

    const lastPoint = dataPoints.value[dataPoints.value.length - 1]
    expect(lastPoint.value).toBeCloseTo(300, 1) // 500 - 200
  })
})

describe('useNetWorthHistory — transfer handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockGetRate.mockReturnValue(1)
    mockSyncStore.state.isSyncing = false
    mockSyncStore.state.initialSyncComplete = true
    mockTransactionsStore.state.transactions = []
    mockTransfersStore.state.transfers = []
  })

  it('transfer is balance-neutral: source loses, destination gains, total unchanged', async () => {
    mockAcc.mockResolvedValue([
      { id: 'src', currency: 'USD', _sync_status: 'synced' },
      { id: 'dst', currency: 'USD', _sync_status: 'synced' },
    ])
    mockTx.mockResolvedValue([
      { id: 'tx-src', type: 'income', amount: 500, date: '2026-01-01', account_id: 'src', base_rate: 1, created_at: '2026-01-01T00:00:00Z' },
      { id: 'tx-dst', type: 'income', amount: 500, date: '2026-01-01', account_id: 'dst', base_rate: 1, created_at: '2026-01-01T00:01:00Z' },
    ])
    mockTr.mockResolvedValue([{
      id: 'tr-1',
      source_account_id: 'src',
      destination_account_id: 'dst',
      amount: 200,
      destination_amount: 200,
      date: '2026-01-05',
      base_rate: 1,
      created_at: '2026-01-05T10:00:00Z',
    }])

    const { dataPoints } = useNetWorthHistory({
      rangeDays: 30,
      endDate: '2026-01-10',
    })
    await settle(350)

    // Total net worth should be 1000 throughout — transfer is purely internal
    const lastPoint = dataPoints.value[dataPoints.value.length - 1]
    expect(lastPoint.value).toBeCloseTo(1000, 1)
  })
})

describe('useNetWorthHistory — granularity auto-selection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockTx.mockResolvedValue([])
    mockTr.mockResolvedValue([])
    mockAcc.mockResolvedValue([])
    mockSyncStore.state.isSyncing = false
    mockSyncStore.state.initialSyncComplete = true
    mockTransactionsStore.state.transactions = []
    mockTransfersStore.state.transfers = []
  })

  it('selects day granularity for 7-day range (1S)', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 7 })
    expect(granularity.value).toBe('day')
  })

  it('selects triday granularity for 30-day range (1M)', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 30 })
    expect(granularity.value).toBe('triday')
  })

  it('selects month granularity for 90-day range', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 90 })
    expect(granularity.value).toBe('month')
  })

  it('selects month granularity for 365-day range (1A)', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 365 })
    expect(granularity.value).toBe('month')
  })

  it('selects year granularity for 500-day range (Todo >15 months)', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 500 })
    expect(granularity.value).toBe('year')
  })

  it('selects year granularity for 1200-day range', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 1200 })
    expect(granularity.value).toBe('year')
  })
})

describe('useNetWorthHistory — Guard 2 sync blocking', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockGetRate.mockReturnValue(1)
    mockTx.mockResolvedValue([])
    mockTr.mockResolvedValue([])
    mockAcc.mockResolvedValue([])
  })

  afterEach(() => {
    vi.useRealTimers()
    // Reset sync state to safe defaults after fake-timer tests
    mockSyncStore.state.isSyncing = false
    mockSyncStore.state.initialSyncComplete = true
    mockTransactionsStore.state.transactions = []
    mockTransfersStore.state.transfers = []
  })

  it('Guard 2 active: loading stays true while isSyncing=true, initialSyncComplete=false, and Dexie empty', async () => {
    vi.useFakeTimers()

    mockSyncStore.state.isSyncing = true
    mockSyncStore.state.initialSyncComplete = false
    mockTransactionsStore.state.transactions = []
    mockTransfersStore.state.transfers = []

    const { loading } = useNetWorthHistory({ rangeDays: 30 })

    // Advance past debounce delay (300ms) but well under the 15s timeout
    await vi.advanceTimersByTimeAsync(400)
    await nextTick()

    // Guard 2 should have fired: loading stays true, computation blocked
    expect(loading.value).toBe(true)
  })

  it('Guard 2 timeout: after 15 seconds syncTimedOut unblocks the chart and shows empty state', async () => {
    vi.useFakeTimers()

    mockSyncStore.state.isSyncing = true
    mockSyncStore.state.initialSyncComplete = false
    mockTransactionsStore.state.transactions = []
    mockTransfersStore.state.transfers = []

    const { loading, isEmpty } = useNetWorthHistory({ rangeDays: 30 })

    // Still blocked before timeout
    await vi.advanceTimersByTimeAsync(400)
    await nextTick()
    expect(loading.value).toBe(true)

    // Advance past the 15s timeout — syncTimedOut flips, watchEffect re-runs,
    // debounce fires, computation runs with empty Dexie → loading=false, isEmpty=true
    await vi.advanceTimersByTimeAsync(15_001)
    await nextTick()
    // Allow debounce (300ms) + async resolution
    await vi.advanceTimersByTimeAsync(400)
    await nextTick()

    expect(loading.value).toBe(false)
    expect(isEmpty.value).toBe(true)
  })
})
