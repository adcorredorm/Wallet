/**
 * exchangeRates.spec.ts
 *
 * Unit tests for the useExchangeRatesStore seeding behavior.
 *
 * Why mock @/offline?
 * The store imports `db` from the '@/offline' barrel. Mocking the barrel
 * prevents real IndexedDB operations (which do not exist in jsdom) and lets
 * us control exactly what Dexie returns per test.
 *
 * Why mock @/api/exchangeRates?
 * fetchRates() triggers a background revalidation when online. We mock the
 * API so no real network calls are made, keeping tests hermetic.
 *
 * Why mock @vueuse/core (useOnline)?
 * By default we want isOnline = false so the background revalidation path
 * is skipped. Tests that need background revalidation can override this.
 *
 * Why use vi.fn() inside vi.mock() factory?
 * Vitest hoists vi.mock() calls to the top of the file before any variable
 * declarations. Top-level `const` variables declared outside the factory are
 * NOT yet initialized when the factory runs — accessing them causes a
 * ReferenceError. The correct pattern is to define vi.fn() stubs INSIDE the
 * factory, then access them later via dynamic `await import('@/offline')`.
 *
 * Why createTestingPinia({ stubActions: false })?
 * We need the store's own action code (fetchRates) to run so we can verify
 * the seeding logic. stubActions: false ensures no action is replaced.
 */

import { setActivePinia } from 'pinia'
import { createTestingPinia } from '@pinia/testing'
import { useExchangeRatesStore } from './exchangeRates'
import type { LocalExchangeRate } from '@/offline'

// ---------------------------------------------------------------------------
// Module-level mocks
// vi.mock factories run before variable declarations (hoisting). All vi.fn()
// stubs must be created INSIDE the factory. We retrieve them via dynamic
// import in tests/beforeEach.
// ---------------------------------------------------------------------------

vi.mock('@/offline', () => ({
  db: {
    exchangeRates: {
      toArray: vi.fn().mockResolvedValue([]),
      bulkPut: vi.fn().mockResolvedValue(undefined),
      put: vi.fn().mockResolvedValue(undefined),
    },
  },
  generateTempId: vi.fn().mockReturnValue('temp-test-id'),
  isTempId: vi.fn((id: string) => id.startsWith('temp-')),
  mutationQueue: {
    enqueue: vi.fn().mockResolvedValue(1),
    findPendingCreate: vi.fn().mockResolvedValue(undefined),
    updatePayload: vi.fn().mockResolvedValue(undefined),
    remove: vi.fn().mockResolvedValue(undefined),
    count: vi.fn().mockResolvedValue(0),
  },
  syncManager: {},
  MutationQueue: vi.fn(),
  SyncManager: vi.fn(),
}))

vi.mock('@/api/exchangeRates', () => ({
  fetchExchangeRates: vi.fn().mockResolvedValue({ rates: [] }),
}))

// Force isOnline = false so background revalidation is skipped by default.
vi.mock('@vueuse/core', () => ({
  useOnline: vi.fn(() => ({ value: false })),
}))

vi.mock('@/utils/formatters', () => ({
  formatCurrency: vi.fn((amount: number, currency: string) => `${currency} ${amount}`),
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setup() {
  setActivePinia(createTestingPinia({ stubActions: false }))
  return useExchangeRatesStore()
}

// ---------------------------------------------------------------------------
// seeding behavior — BASE_RATES
// ---------------------------------------------------------------------------

describe('useExchangeRatesStore — BASE_RATES seeding', () => {
  beforeEach(async () => {
    // resetAllMocks clears both call history AND pending mockResolvedValueOnce
    // queues from the previous test. clearAllMocks only clears call history,
    // leaving queued one-time return values which would leak between tests.
    vi.resetAllMocks()
    // Re-apply default: Dexie is empty (cold start)
    const { db } = await import('@/offline')
    ;(db.exchangeRates.toArray as ReturnType<typeof vi.fn>).mockResolvedValue([])
    ;(db.exchangeRates.bulkPut as ReturnType<typeof vi.fn>).mockResolvedValue(undefined)
    ;(db.exchangeRates.put as ReturnType<typeof vi.fn>).mockResolvedValue(undefined)
  })

  it('seeds BASE_RATES via bulkPut when Dexie is empty (cold start)', async () => {
    const { db } = await import('@/offline')
    const toArray = db.exchangeRates.toArray as ReturnType<typeof vi.fn>
    const bulkPut = db.exchangeRates.bulkPut as ReturnType<typeof vi.fn>

    // bulkPut captures the seeded rates and makes them available to the
    // subsequent toArray call that confirms what was stored.
    bulkPut.mockImplementationOnce(async (rates: LocalExchangeRate[]) => {
      toArray.mockResolvedValueOnce(rates)
      return undefined
    })

    const store = setup()
    await store.fetchRates()

    expect(bulkPut).toHaveBeenCalledOnce()
    expect(store.rates.length).toBeGreaterThan(0)
  })

  it('does NOT call bulkPut when Dexie already has data', async () => {
    const { db } = await import('@/offline')
    const existingRates: LocalExchangeRate[] = [
      {
        currency_code: 'USD',
        rate_to_usd: 1,
        fetched_at: '2026-01-01T00:00:00Z',
        source: 'exchangerate.host',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]
    // Provide existing data — fetchRates should use it as-is without seeding.
    // mockResolvedValue (not Once) ensures all toArray calls during this test
    // return the existing data, preventing the cold-start branch.
    ;(db.exchangeRates.toArray as ReturnType<typeof vi.fn>).mockResolvedValue(existingRates)

    const store = setup()
    await store.fetchRates()

    expect(db.exchangeRates.bulkPut).not.toHaveBeenCalled()
    // rates must match the existing data (not BASE_RATES)
    expect(store.rates).toHaveLength(1)
    expect(store.rates[0].currency_code).toBe('USD')
    expect(store.rates[0].source).toBe('exchangerate.host')
  })

  it('falls back to BASE_RATES in memory when Dexie fails entirely', async () => {
    const { db } = await import('@/offline')
    ;(db.exchangeRates.toArray as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('IDB unavailable')
    )

    const store = setup()
    await store.fetchRates()

    // bulkPut must NOT have been called — Dexie is broken
    expect(db.exchangeRates.bulkPut).not.toHaveBeenCalled()
    // In-memory BASE_RATES must be loaded into rates.value
    expect(store.rates.length).toBeGreaterThan(0)
  })

  it('contains all 9 supported currency codes after cold start seeding', async () => {
    const { db } = await import('@/offline')
    const toArray = db.exchangeRates.toArray as ReturnType<typeof vi.fn>
    const bulkPut = db.exchangeRates.bulkPut as ReturnType<typeof vi.fn>

    bulkPut.mockImplementationOnce(async (rates: LocalExchangeRate[]) => {
      toArray.mockResolvedValueOnce(rates)
      return undefined
    })

    const store = setup()
    await store.fetchRates()

    const codes = store.rates.map(r => r.currency_code)
    expect(codes).toContain('USD')
    expect(codes).toContain('COP')
    expect(codes).toContain('EUR')
    expect(codes).toContain('BRL')
    expect(codes).toContain('JPY')
    expect(codes).toContain('ARS')
    expect(codes).toContain('GBP')
    expect(codes).toContain('BTC')
    expect(codes).toContain('ETH')
    expect(store.rates).toHaveLength(9)
  })

  it('USD rate_to_usd equals 1 after cold start seeding', async () => {
    const { db } = await import('@/offline')
    const toArray = db.exchangeRates.toArray as ReturnType<typeof vi.fn>
    const bulkPut = db.exchangeRates.bulkPut as ReturnType<typeof vi.fn>

    bulkPut.mockImplementationOnce(async (rates: LocalExchangeRate[]) => {
      toArray.mockResolvedValueOnce(rates)
      return undefined
    })

    const store = setup()
    await store.fetchRates()

    const usd = store.rates.find(r => r.currency_code === 'USD')
    expect(usd).toBeDefined()
    expect(usd!.rate_to_usd).toBe(1)
  })

  it('loading is false after fetchRates() completes', async () => {
    const { db } = await import('@/offline')
    const toArray = db.exchangeRates.toArray as ReturnType<typeof vi.fn>
    const bulkPut = db.exchangeRates.bulkPut as ReturnType<typeof vi.fn>

    bulkPut.mockImplementationOnce(async (rates: LocalExchangeRate[]) => {
      toArray.mockResolvedValueOnce(rates)
      return undefined
    })

    const store = setup()
    await store.fetchRates()

    expect(store.loading).toBe(false)
  })

  it('seeded records have source === "system"', async () => {
    const { db } = await import('@/offline')
    const toArray = db.exchangeRates.toArray as ReturnType<typeof vi.fn>
    const bulkPut = db.exchangeRates.bulkPut as ReturnType<typeof vi.fn>

    bulkPut.mockImplementationOnce(async (rates: LocalExchangeRate[]) => {
      toArray.mockResolvedValueOnce(rates)
      return undefined
    })

    const store = setup()
    await store.fetchRates()

    // Rates must be present AND every one must have source 'system'
    expect(store.rates.length).toBeGreaterThan(0)
    const nonSystemRecords = store.rates.filter(r => r.source !== 'system')
    expect(nonSystemRecords).toHaveLength(0)
  })
})
