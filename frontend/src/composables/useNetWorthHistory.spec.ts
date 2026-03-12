/**
 * useNetWorthHistory.spec.ts
 *
 * Tests for the net worth history composable.
 *
 * Dexie is mocked to return controlled fixtures. Exchange rates and settings
 * are mocked via Pinia store mocks. The composable is tested with real Vue
 * reactivity (setActivePinia + createPinia) to verify ComputedRef behavior.
 *
 * Date handling: all test dates are ISO strings (YYYY-MM-DD). The composable
 * uses date-fns for boundary calculations, which is not mocked — we use
 * dates far enough in the past that frozen-clock issues do not affect results.
 *
 * Async strategy: useNetWorthHistory triggers a watchEffect that runs async
 * computation. Tests must await nextTick() plus a small settling delay so the
 * watchEffect callback completes before assertions.
 */

import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'

// Mock Dexie — composable reads directly from db.transactions / db.transfers / db.accounts
const mockTransactions = vi.fn().mockResolvedValue([])
const mockTransfers = vi.fn().mockResolvedValue([])
const mockAccounts = vi.fn().mockResolvedValue([])

vi.mock('@/offline', () => ({
  db: {
    transactions: { toArray: mockTransactions },
    transfers: { toArray: mockTransfers },
    accounts: { toArray: mockAccounts },
  },
}))

const mockGetRate = vi.fn().mockReturnValue(1)

vi.mock('@/stores/exchangeRates', () => ({
  useExchangeRatesStore: vi.fn(() => ({
    getRate: mockGetRate,
    rates: [],
  })),
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: vi.fn(() => ({
    primaryCurrency: 'USD',
  })),
}))

import { useNetWorthHistory } from './useNetWorthHistory'

/** Wait for watchEffect async computation to complete */
async function settle(ms = 30) {
  await nextTick()
  await new Promise(r => setTimeout(r, ms))
}

describe('useNetWorthHistory — empty state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockGetRate.mockReturnValue(1)
    mockTransactions.mockResolvedValue([])
    mockTransfers.mockResolvedValue([])
    mockAccounts.mockResolvedValue([])
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
    mockGetRate.mockReturnValue(1) // USD→USD = 1
    mockTransfers.mockResolvedValue([])
  })

  it('produces correct net worth for a single income with base_rate=1', async () => {
    mockAccounts.mockResolvedValue([
      { id: 'acc-1', currency: 'USD', _sync_status: 'synced' }
    ])
    mockTransactions.mockResolvedValue([
      {
        id: 'tx-1',
        type: 'income',
        amount: 100,
        date: '2026-01-05',
        account_id: 'acc-1',
        base_rate: 1,
        created_at: '2026-01-05T10:00:00Z',
      }
    ])

    const { dataPoints, isEmpty } = useNetWorthHistory({
      rangeDays: 30,
      endDate: '2026-01-10',
    })
    await settle(50)

    expect(isEmpty.value).toBe(false)
    const pointAfterTx = dataPoints.value.find(p => p.date >= '2026-01-05')
    expect(pointAfterTx).toBeDefined()
    expect(pointAfterTx!.value).toBeCloseTo(100, 1)
  })

  it('uses base_rate=null fallback to getRate when base_rate is null', async () => {
    mockGetRate.mockReturnValue(4200)
    mockAccounts.mockResolvedValue([
      { id: 'acc-1', currency: 'USD', _sync_status: 'synced' }
    ])
    mockTransactions.mockResolvedValue([
      {
        id: 'tx-1',
        type: 'income',
        amount: 100,
        date: '2026-01-05',
        account_id: 'acc-1',
        base_rate: null,  // force fallback to live rate
        created_at: '2026-01-05T10:00:00Z',
      }
    ])

    const { dataPoints } = useNetWorthHistory({
      rangeDays: 30,
      endDate: '2026-01-10',
    })
    await settle(50)

    const pointAfterTx = dataPoints.value.find(p => p.date >= '2026-01-05')
    expect(pointAfterTx).toBeDefined()
    expect(pointAfterTx!.value).toBeCloseTo(100 * 4200, 0)
  })

  it('income increases net worth, expense decreases it', async () => {
    mockAccounts.mockResolvedValue([
      { id: 'acc-1', currency: 'USD', _sync_status: 'synced' }
    ])
    mockTransactions.mockResolvedValue([
      { id: 'tx-1', type: 'income', amount: 500, date: '2026-01-01', account_id: 'acc-1', base_rate: 1, created_at: '2026-01-01T00:00:00Z' },
      { id: 'tx-2', type: 'expense', amount: 200, date: '2026-01-02', account_id: 'acc-1', base_rate: 1, created_at: '2026-01-02T00:00:00Z' },
    ])

    const { dataPoints } = useNetWorthHistory({
      rangeDays: 10,
      endDate: '2026-01-10',
    })
    await settle(50)

    const lastPoint = dataPoints.value[dataPoints.value.length - 1]
    expect(lastPoint.value).toBeCloseTo(300, 1) // 500 - 200
  })
})

describe('useNetWorthHistory — transfer handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockGetRate.mockReturnValue(1)
  })

  it('transfer is balance-neutral: source loses, destination gains, total unchanged', async () => {
    mockAccounts.mockResolvedValue([
      { id: 'src', currency: 'USD', _sync_status: 'synced' },
      { id: 'dst', currency: 'USD', _sync_status: 'synced' },
    ])
    mockTransactions.mockResolvedValue([
      // Both accounts start with 500 USD via income
      { id: 'tx-src', type: 'income', amount: 500, date: '2026-01-01', account_id: 'src', base_rate: 1, created_at: '2026-01-01T00:00:00Z' },
      { id: 'tx-dst', type: 'income', amount: 500, date: '2026-01-01', account_id: 'dst', base_rate: 1, created_at: '2026-01-01T00:01:00Z' },
    ])
    mockTransfers.mockResolvedValue([
      {
        id: 'tr-1',
        source_account_id: 'src',
        destination_account_id: 'dst',
        amount: 200,
        destination_amount: 200,
        date: '2026-01-05',
        base_rate: 1,
        created_at: '2026-01-05T10:00:00Z',
      }
    ])

    const { dataPoints } = useNetWorthHistory({
      rangeDays: 30,
      endDate: '2026-01-10',
    })
    await settle(50)

    // Total net worth should be 1000 throughout — transfer is internal
    const lastPoint = dataPoints.value[dataPoints.value.length - 1]
    expect(lastPoint.value).toBeCloseTo(1000, 1)
  })
})

describe('useNetWorthHistory — granularity auto-selection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockTransactions.mockResolvedValue([])
    mockTransfers.mockResolvedValue([])
    mockAccounts.mockResolvedValue([])
  })

  it('selects day granularity for 30-day range', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 30 })
    expect(granularity.value).toBe('day')
  })

  it('selects day granularity for exactly 90-day range', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 90 })
    expect(granularity.value).toBe('day')
  })

  it('selects week granularity for 180-day range', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 180 })
    expect(granularity.value).toBe('week')
  })

  it('selects month granularity for 400-day range', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 400 })
    expect(granularity.value).toBe('month')
  })

  it('selects year granularity for 1200-day range', () => {
    const { granularity } = useNetWorthHistory({ rangeDays: 1200 })
    expect(granularity.value).toBe('year')
  })
})
