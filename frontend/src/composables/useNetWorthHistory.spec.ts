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
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'

// Create mock fns via vi.hoisted() — these are available before vi.mock() hoisting
const { mockTx, mockTr, mockAcc } = vi.hoisted(() => ({
  mockTx: vi.fn().mockResolvedValue([]),
  mockTr: vi.fn().mockResolvedValue([]),
  mockAcc: vi.fn().mockResolvedValue([]),
}))

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
async function settle(ms = 40) {
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
    await settle(50)

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
    await settle(50)

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
    await settle(50)

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
