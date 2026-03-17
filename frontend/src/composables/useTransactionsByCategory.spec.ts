import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'

const { mockWhere, mockPendingMutationsToArray } = vi.hoisted(() => ({
  mockWhere: vi.fn(),
  mockPendingMutationsToArray: vi.fn().mockResolvedValue([]),
}))

vi.mock('@/offline', () => ({
  db: {
    transactions: { where: mockWhere },
    pendingMutations: {
      where: vi.fn(() => ({
        equals: vi.fn(() => ({
          filter: vi.fn(() => ({ toArray: mockPendingMutationsToArray })),
        })),
      })),
    },
  },
}))

import { useTransactionsByCategory } from './useTransactionsByCategory'

async function settle(ms = 50) {
  await nextTick()
  await new Promise(r => setTimeout(r, ms))
}

function makeTx(n: number, categoryId = 'cat-1') {
  return Array.from({ length: n }, (_, i) => ({
    id: `tx-${i}`,
    category_id: categoryId,
    date: `2026-01-${String(n - i).padStart(2, '0')}`,
    created_at: `2026-01-${String(n - i).padStart(2, '0')}T00:00:00Z`,
    type: 'expense' as const,
    amount: 10,
  }))
}

describe('useTransactionsByCategory', () => {
  let mockToArray: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockToArray = vi.fn().mockResolvedValue([])
    mockWhere.mockReturnValue({
      equals: vi.fn(() => ({ toArray: mockToArray })),
    })
  })

  it('returns empty items and totalPages=0 when Dexie is empty', async () => {
    const { items, totalPages, totalItems, loading } = useTransactionsByCategory('cat-1')
    await settle()
    expect(items.value).toHaveLength(0)
    expect(totalPages.value).toBe(0)
    expect(totalItems.value).toBe(0)
    expect(loading.value).toBe(false)
  })

  it('returns page 1 when there are exactly pageSize transactions', async () => {
    mockToArray.mockResolvedValue(makeTx(20))
    const { items, totalPages, currentPage } = useTransactionsByCategory('cat-1', 20)
    await settle()
    expect(items.value).toHaveLength(20)
    expect(totalPages.value).toBe(1)
    expect(currentPage.value).toBe(1)
  })

  it('paginates correctly when there are more than pageSize items', async () => {
    mockToArray.mockResolvedValue(makeTx(45))
    const { items, totalPages, totalItems } = useTransactionsByCategory('cat-1', 20)
    await settle()
    expect(items.value).toHaveLength(20)
    expect(totalPages.value).toBe(3)
    expect(totalItems.value).toBe(45)
  })

  it('goToPage(2) returns the second page of items', async () => {
    const allTx = makeTx(45)
    mockToArray.mockResolvedValue(allTx)
    const { items, goToPage } = useTransactionsByCategory('cat-1', 20)
    await settle()
    goToPage(2)
    await settle()
    expect(items.value).toHaveLength(20)
    expect(items.value[0].id).toBe(allTx[20].id)
  })

  it('goToPage clamps below 1 to page 1', async () => {
    mockToArray.mockResolvedValue(makeTx(25))
    const { currentPage, goToPage } = useTransactionsByCategory('cat-1', 20)
    await settle()
    goToPage(-5)
    expect(currentPage.value).toBe(1)
  })

  it('goToPage clamps above totalPages to totalPages', async () => {
    mockToArray.mockResolvedValue(makeTx(25))
    const { currentPage, totalPages, goToPage } = useTransactionsByCategory('cat-1', 20)
    await settle()
    goToPage(999)
    expect(currentPage.value).toBe(totalPages.value)
  })

  it('items are ordered newest first (date DESC, then created_at DESC)', async () => {
    const allTx = makeTx(5)
    mockToArray.mockResolvedValue([...allTx].reverse())
    const { items } = useTransactionsByCategory('cat-1', 20)
    await settle()
    expect(items.value[0].id).toBe('tx-0')
  })

  it('excludes transactions that have a pending delete mutation', async () => {
    const allTx = makeTx(3)
    mockToArray.mockResolvedValue(allTx)
    mockPendingMutationsToArray.mockResolvedValue([
      { entity_id: 'tx-1', operation: 'delete' },
    ])
    const { items, totalItems } = useTransactionsByCategory('cat-1', 20)
    await settle()
    expect(totalItems.value).toBe(2)
    expect(items.value.find(t => t.id === 'tx-1')).toBeUndefined()
  })

  it('queries db.transactions filtered by the given categoryId', async () => {
    useTransactionsByCategory('cat-xyz', 20)
    await settle()
    expect(mockWhere).toHaveBeenCalledWith('category_id')
  })
})
