import { createPinia, setActivePinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'

const {
  mockTxToArray, mockTxCount, mockTxWhere,
  mockTrToArray, mockTrCount, mockTrWhere,
  mockPendingMutationsToArray,
} = vi.hoisted(() => {
  const txToArray = vi.fn().mockResolvedValue([])
  const txCount = vi.fn().mockResolvedValue(0)
  const trToArray = vi.fn().mockResolvedValue([])
  const trCount = vi.fn().mockResolvedValue(0)
  const pendingToArray = vi.fn().mockResolvedValue([])
  return {
    mockTxToArray: txToArray,
    mockTxCount: txCount,
    mockTxWhere: vi.fn(() => ({
      equals: vi.fn(() => ({ toArray: txToArray, count: txCount })),
    })),
    mockTrToArray: trToArray,
    mockTrCount: trCount,
    mockTrWhere: vi.fn(() => ({
      equals: vi.fn(() => ({ toArray: trToArray, count: trCount })),
      anyOf: vi.fn(() => ({ toArray: trToArray, count: trCount })),
    })),
    mockPendingMutationsToArray: pendingToArray,
  }
})

vi.mock('@/offline', () => ({
  db: {
    transactions: { toArray: mockTxToArray, count: mockTxCount, where: mockTxWhere },
    transfers: { toArray: mockTrToArray, count: mockTrCount, where: mockTrWhere },
    pendingMutations: {
      where: vi.fn(() => ({
        equals: vi.fn(() => ({
          filter: vi.fn(() => ({ toArray: mockPendingMutationsToArray })),
        })),
      })),
    },
  },
}))

import { useMovements } from './useMovements'

async function settle(ms = 50) {
  await nextTick()
  await new Promise(r => setTimeout(r, ms))
}

function makeTxRow(id: string, createdAt: string) {
  return { id, created_at: createdAt, date: createdAt.slice(0, 10), type: 'expense', amount: 10 }
}
function makeTrRow(id: string, createdAt: string) {
  return { id, created_at: createdAt, date: createdAt.slice(0, 10), amount: 50 }
}

describe('useMovements — no accountId (all movements)', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('returns empty state when both tables are empty', async () => {
    mockTxToArray.mockResolvedValue([]); mockTxCount.mockResolvedValue(0)
    mockTrToArray.mockResolvedValue([]); mockTrCount.mockResolvedValue(0)
    const { items, totalItems, loading } = useMovements(undefined)
    await settle()
    expect(items.value).toHaveLength(0)
    expect(totalItems.value).toBe(0)
    expect(loading.value).toBe(false)
  })

  it('merges transactions and transfers sorted newest first', async () => {
    const tx1 = makeTxRow('tx-1', '2026-01-05T10:00:00Z')
    const tr1 = makeTrRow('tr-1', '2026-01-06T08:00:00Z')
    mockTxToArray.mockResolvedValue([tx1]); mockTxCount.mockResolvedValue(1)
    mockTrToArray.mockResolvedValue([tr1]); mockTrCount.mockResolvedValue(1)
    const { items } = useMovements(undefined, 20)
    await settle()
    expect(items.value[0].id).toBe('tr-1')
    expect(items.value[1].id).toBe('tx-1')
  })

  it('adds _type discriminator to each row', async () => {
    mockTxToArray.mockResolvedValue([makeTxRow('tx-1', '2026-01-05T00:00:00Z')]); mockTxCount.mockResolvedValue(1)
    mockTrToArray.mockResolvedValue([makeTrRow('tr-1', '2026-01-04T00:00:00Z')]); mockTrCount.mockResolvedValue(1)
    const { items } = useMovements(undefined, 20)
    await settle()
    const txItem = items.value.find(i => i.id === 'tx-1') as any
    const trItem = items.value.find(i => i.id === 'tr-1') as any
    expect(txItem._type).toBe('transaction')
    expect(trItem._type).toBe('transfer')
  })

  it('totalPages is ceil(totalItems / pageSize)', async () => {
    // totalItems is derived from rows.length (not from count() queries)
    mockTxToArray.mockResolvedValue(Array.from({ length: 30 }, (_, i) =>
      makeTxRow(`tx-${i}`, `2026-01-${String(30 - i).padStart(2, '0')}T00:00:00Z`)
    ))
    mockTrToArray.mockResolvedValue(Array.from({ length: 15 }, (_, i) =>
      makeTrRow(`tr-${i}`, `2025-12-${String(15 - i).padStart(2, '0')}T00:00:00Z`)
    ))
    const { totalPages, totalItems } = useMovements(undefined, 20)
    await settle()
    expect(totalItems.value).toBe(45)
    expect(totalPages.value).toBe(3)
  })
})

describe('useMovements — with accountId', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('filters transactions by account_id when accountId is provided', async () => {
    mockTxToArray.mockResolvedValue([]); mockTxCount.mockResolvedValue(0)
    mockTrToArray.mockResolvedValue([]); mockTrCount.mockResolvedValue(0)
    useMovements('acc-123', 20)
    await settle()
    expect(mockTxWhere).toHaveBeenCalledWith('account_id')
  })

  it('queries transfers by source_account_id when accountId is provided', async () => {
    mockTxToArray.mockResolvedValue([]); mockTxCount.mockResolvedValue(0)
    mockTrToArray.mockResolvedValue([]); mockTrCount.mockResolvedValue(0)
    useMovements('acc-123', 20)
    await settle()
    // Should have called where on transfers (for source or destination)
    expect(mockTrWhere).toHaveBeenCalled()
  })

  it('deduplicates transfers that appear as both source and destination', async () => {
    // A self-transfer (source === destination === accountId) would appear in both queries
    // It should only be included once in the result
    const selfTransfer = makeTrRow('tr-self', '2026-01-05T00:00:00Z')
    mockTxToArray.mockResolvedValue([]); mockTxCount.mockResolvedValue(0)
    // Both source and destination queries return the same transfer
    mockTrWhere.mockImplementation(() => ({
      equals: vi.fn(() => ({ toArray: vi.fn().mockResolvedValue([selfTransfer]), count: vi.fn().mockResolvedValue(1) })),
    }))
    mockTrCount.mockResolvedValue(1)
    const { items } = useMovements('acc-123', 20)
    await settle()
    // Despite appearing in two queries, the transfer appears only once
    const selfTransfers = items.value.filter(i => i.id === 'tr-self')
    expect(selfTransfers).toHaveLength(1)
  })
})

describe('useMovements — goToPage', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('clamps goToPage below 1 to 1', async () => {
    mockTxToArray.mockResolvedValue(Array.from({ length: 5 }, (_, i) =>
      makeTxRow(`tx-${i}`, `2026-01-0${i + 1}T00:00:00Z`)
    ))
    mockTxCount.mockResolvedValue(5); mockTrToArray.mockResolvedValue([]); mockTrCount.mockResolvedValue(0)
    const { goToPage, currentPage } = useMovements(undefined, 20)
    await settle()
    goToPage(-10); await settle()
    expect(currentPage.value).toBe(1)
  })

  it('clamps goToPage above totalPages to totalPages', async () => {
    mockTxToArray.mockResolvedValue(Array.from({ length: 5 }, (_, i) =>
      makeTxRow(`tx-${i}`, `2026-01-0${i + 1}T00:00:00Z`)
    ))
    mockTxCount.mockResolvedValue(5); mockTrToArray.mockResolvedValue([]); mockTrCount.mockResolvedValue(0)
    const { goToPage, currentPage, totalPages } = useMovements(undefined, 20)
    await settle()
    goToPage(999); await settle()
    expect(currentPage.value).toBe(totalPages.value)
  })
})
