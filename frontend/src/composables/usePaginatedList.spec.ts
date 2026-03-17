import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'

const { mockTxToArray, mockTrToArray, mockPendingMutationsToArray } = vi.hoisted(() => ({
  mockTxToArray: vi.fn().mockResolvedValue([]),
  mockTrToArray: vi.fn().mockResolvedValue([]),
  mockPendingMutationsToArray: vi.fn().mockResolvedValue([]),
}))

vi.mock('@/offline', () => ({
  db: {
    transactions: { toArray: mockTxToArray },
    transfers: { toArray: mockTrToArray },
    pendingMutations: {
      where: vi.fn(() => ({
        equals: vi.fn(() => ({
          filter: vi.fn(() => ({ toArray: mockPendingMutationsToArray })),
        })),
      })),
    },
  },
}))

import { usePaginatedList } from './usePaginatedList'

async function settle(ms = 50) {
  await nextTick()
  await new Promise(r => setTimeout(r, ms))
}

function makeTx(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `tx-${i}`,
    created_at: `2026-01-${String(n - i).padStart(2, '0')}T00:00:00Z`,
    type: 'expense',
    amount: 10,
  }))
}

describe('usePaginatedList — transactions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('returns empty items and totalPages=0 when Dexie is empty', async () => {
    mockTxToArray.mockResolvedValue([])
    const { items, totalPages, totalItems, loading } = usePaginatedList('transactions')
    await settle()
    expect(items.value).toHaveLength(0)
    expect(totalPages.value).toBe(0)
    expect(totalItems.value).toBe(0)
    expect(loading.value).toBe(false)
  })

  it('returns page 1 of 20 items when there are exactly 20 records', async () => {
    mockTxToArray.mockResolvedValue(makeTx(20))
    const { items, totalPages, currentPage } = usePaginatedList('transactions', 20)
    await settle()
    expect(items.value).toHaveLength(20)
    expect(totalPages.value).toBe(1)
    expect(currentPage.value).toBe(1)
  })

  it('returns only the first pageSize items when totalItems > pageSize', async () => {
    mockTxToArray.mockResolvedValue(makeTx(45))
    const { items, totalPages, totalItems } = usePaginatedList('transactions', 20)
    await settle()
    expect(items.value).toHaveLength(20)
    expect(totalPages.value).toBe(3)
    expect(totalItems.value).toBe(45)
  })

  it('goToPage(2) returns items 21-40', async () => {
    const allTx = makeTx(45)
    mockTxToArray.mockResolvedValue(allTx)
    const { items, goToPage } = usePaginatedList('transactions', 20)
    await settle()
    goToPage(2)
    await settle()
    expect(items.value).toHaveLength(20)
    expect(items.value[0].id).toBe(allTx[20].id)
  })

  it('goToPage clamps below 1 to page 1', async () => {
    mockTxToArray.mockResolvedValue(makeTx(25))
    const { currentPage, goToPage } = usePaginatedList('transactions', 20)
    await settle()
    goToPage(-5)
    await settle()
    expect(currentPage.value).toBe(1)
  })

  it('goToPage clamps above totalPages to totalPages', async () => {
    mockTxToArray.mockResolvedValue(makeTx(25))
    const { currentPage, totalPages, goToPage } = usePaginatedList('transactions', 20)
    await settle()
    goToPage(999)
    await settle()
    expect(currentPage.value).toBe(totalPages.value)
  })

  it('items are ordered newest first (created_at DESC)', async () => {
    const allTx = makeTx(5)
    mockTxToArray.mockResolvedValue([...allTx].reverse())
    const { items } = usePaginatedList('transactions', 20)
    await settle()
    expect(items.value[0].id).toBe('tx-0')
  })
})

describe('usePaginatedList — transfers', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('queries db.transfers (not db.transactions) when type is "transfers"', async () => {
    mockTrToArray.mockResolvedValue([])
    usePaginatedList('transfers')
    await settle()
    expect(mockTrToArray).toHaveBeenCalledTimes(1)
    expect(mockTxToArray).not.toHaveBeenCalled()
  })
})
