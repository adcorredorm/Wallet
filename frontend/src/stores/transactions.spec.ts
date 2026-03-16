/**
 * transactions.spec.ts
 *
 * Focused tests for base_rate population in createTransaction() and
 * updateTransaction(). The full offline-first write sequence (IndexedDB,
 * mutation queue, optimistic balance) is covered by the accounts spec
 * pattern — we only verify the base_rate computation here.
 */

import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'

// Mock Dexie/offline module before any store import
vi.mock('@/offline', () => ({
  db: {
    transactions: {
      add: vi.fn().mockResolvedValue(undefined),
      update: vi.fn().mockResolvedValue(undefined),
    },
  },
  generateTempId: vi.fn().mockReturnValue('temp-123'),
  mutationQueue: {
    enqueue: vi.fn().mockResolvedValue(undefined),
    findPendingCreate: vi.fn().mockResolvedValue(null),
    updatePayload: vi.fn().mockResolvedValue(undefined),
  },
}))

// We will control these store return values in each test
const mockGetRate = vi.fn()
const mockAdjustBalance = vi.fn()

vi.mock('@/stores/accounts', () => ({
  useAccountsStore: vi.fn(() => ({
    accounts: [{ id: 'acc-1', currency: 'USD' }],
    adjustBalance: mockAdjustBalance,
  })),
}))

vi.mock('@/stores/exchangeRates', () => ({
  useExchangeRatesStore: vi.fn(() => ({
    getRate: mockGetRate,
  })),
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: vi.fn(() => ({
    primaryCurrency: 'COP',
  })),
}))

import { useTransactionsStore } from './transactions'
import { TransactionType } from '@/types/transaction'

describe('useTransactionsStore — base_rate population', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('populates base_rate on createTransaction when rate is available', async () => {
    mockGetRate.mockReturnValue(4200)

    const store = useTransactionsStore()
    const { db } = await import('@/offline')

    await store.createTransaction({
      type: TransactionType.EXPENSE,
      amount: 100,
      date: '2026-01-15',
      account_id: 'acc-1',
      category_id: 'cat-1',
    })

    const addCall = vi.mocked(db.transactions.add).mock.calls[0][0]
    expect(addCall.base_rate).toBe(4200)
  })

  it('sets base_rate to null on createTransaction when rate is unavailable', async () => {
    mockGetRate.mockReturnValue(null)

    const store = useTransactionsStore()
    const { db } = await import('@/offline')

    await store.createTransaction({
      type: TransactionType.INCOME,
      amount: 50,
      date: '2026-01-15',
      account_id: 'acc-1',
      category_id: 'cat-1',
    })

    const addCall = vi.mocked(db.transactions.add).mock.calls[0][0]
    expect(addCall.base_rate).toBeNull()
  })

  it('populates base_rate on updateTransaction when rate is available', async () => {
    mockGetRate.mockReturnValue(4300)

    const store = useTransactionsStore()
    // Pre-populate in-memory so idx !== -1 path is exercised
    store.transactions = [{
      id: 'tx-1',
      type: TransactionType.EXPENSE,
      amount: 100,
      date: '2026-01-10',
      account_id: 'acc-1',
      category_id: 'cat-1',
      tags: [],
      created_at: '2026-01-10T00:00:00Z',
      updated_at: '2026-01-10T00:00:00Z',
      _sync_status: 'synced',
      _local_updated_at: '2026-01-10T00:00:00Z',
    }] as any

    const { db } = await import('@/offline')

    await store.updateTransaction('tx-1', { amount: 200 })

    const updateCall = vi.mocked(db.transactions.update).mock.calls[0]
    // updateCall[0] is the id, updateCall[1] is the partial update object.
    // Cast to Record to access dynamic fields — Dexie's UpdateSpec type does not
    // expose nullable fields as plain property access.
    const updatePayload = updateCall[1] as Record<string, unknown>
    expect(updatePayload['base_rate']).toBe(4300)
  })

  it('sets base_rate to null on updateTransaction when account not found', async () => {
    // Return a store where accounts array is empty
    const { useAccountsStore } = await import('@/stores/accounts')
    vi.mocked(useAccountsStore).mockReturnValueOnce({
      accounts: [],
      adjustBalance: mockAdjustBalance,
    } as any)

    const store = useTransactionsStore()
    store.transactions = [{
      id: 'tx-2',
      type: TransactionType.EXPENSE,
      amount: 50,
      date: '2026-01-10',
      account_id: 'acc-missing',
      category_id: 'cat-1',
      tags: [],
      created_at: '2026-01-10T00:00:00Z',
      updated_at: '2026-01-10T00:00:00Z',
      _sync_status: 'synced',
      _local_updated_at: '2026-01-10T00:00:00Z',
    }] as any

    const { db } = await import('@/offline')

    await store.updateTransaction('tx-2', { amount: 75 })

    const updateCall = vi.mocked(db.transactions.update).mock.calls[0]
    const updatePayload = updateCall[1] as Record<string, unknown>
    expect(updatePayload['base_rate']).toBeNull()
  })
})
