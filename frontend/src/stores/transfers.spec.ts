/**
 * transfers.spec.ts
 *
 * Focused tests for base_rate population in createTransfer() and updateTransfer().
 * base_rate is derived from the SOURCE account's currency only.
 */

import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('@/offline', () => ({
  db: {
    transfers: {
      add: vi.fn().mockResolvedValue(undefined),
      update: vi.fn().mockResolvedValue(undefined),
    },
  },
  fetchAllWithRevalidation: vi.fn().mockResolvedValue([]),
  fetchByIdWithRevalidation: vi.fn().mockResolvedValue(undefined),
  generateTempId: vi.fn().mockReturnValue('temp-456'),
  mutationQueue: {
    enqueue: vi.fn().mockResolvedValue(undefined),
    findPendingCreate: vi.fn().mockResolvedValue(null),
    updatePayload: vi.fn().mockResolvedValue(undefined),
  },
}))

vi.mock('@/api/transfers', () => ({
  transfersApi: {
    getAll: vi.fn().mockResolvedValue([]),
    getById: vi.fn().mockResolvedValue(null),
    getByAccount: vi.fn().mockResolvedValue([]),
  },
}))

const mockGetRate = vi.fn()
const mockAdjustBalance = vi.fn()

vi.mock('@/stores/accounts', () => ({
  useAccountsStore: vi.fn(() => ({
    accounts: [
      { id: 'src-acc', currency: 'USD' },
      { id: 'dst-acc', currency: 'COP' },
    ],
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

import { useTransfersStore } from './transfers'

describe('useTransfersStore — base_rate population', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('populates base_rate from source account on createTransfer', async () => {
    mockGetRate.mockReturnValue(4200)

    const store = useTransfersStore()
    const { db } = await import('@/offline')

    await store.createTransfer({
      source_account_id: 'src-acc',
      destination_account_id: 'dst-acc',
      amount: 100,
      date: '2026-01-15',
    })

    const addCall = vi.mocked(db.transfers.add).mock.calls[0][0]
    expect(addCall.base_rate).toBe(4200)
    // Verify getRate was called with the SOURCE account currency
    expect(mockGetRate).toHaveBeenCalledWith('USD', 'COP')
  })

  it('sets base_rate to null when rate unavailable on createTransfer', async () => {
    mockGetRate.mockReturnValue(null)

    const store = useTransfersStore()
    const { db } = await import('@/offline')

    await store.createTransfer({
      source_account_id: 'src-acc',
      destination_account_id: 'dst-acc',
      amount: 50,
      date: '2026-01-15',
    })

    const addCall = vi.mocked(db.transfers.add).mock.calls[0][0]
    expect(addCall.base_rate).toBeNull()
  })

  it('populates base_rate on updateTransfer', async () => {
    mockGetRate.mockReturnValue(4300)

    const store = useTransfersStore()
    store.transfers = [{
      id: 'tr-1',
      source_account_id: 'src-acc',
      destination_account_id: 'dst-acc',
      amount: 100,
      date: '2026-01-10',
      tags: [],
      created_at: '2026-01-10T00:00:00Z',
      updated_at: '2026-01-10T00:00:00Z',
      _sync_status: 'synced',
      _local_updated_at: '2026-01-10T00:00:00Z',
    }] as any

    const { db } = await import('@/offline')

    await store.updateTransfer('tr-1', { amount: 200 })

    const updateCall = vi.mocked(db.transfers.update).mock.calls[0]
    const updatePayload = updateCall[1] as Record<string, unknown>
    expect(updatePayload['base_rate']).toBe(4300)
  })
})
