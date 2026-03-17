/**
 * useTransactionsByCategory — paginated list of transactions for a single category
 *
 * Mirrors usePaginatedList but queries db.transactions filtered by category_id.
 * No transfers are included (categories only apply to transactions).
 *
 * Sort order: date DESC, then created_at DESC (locale-independent Date.parse).
 * Re-fetches on 'wallet:sync-complete' and 'wallet:local-delete' window events.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { db } from '@/offline'
import type { LocalTransaction } from '@/offline/types'

export interface UseTransactionsByCategoryReturn {
  items: ComputedRef<LocalTransaction[]>
  currentPage: Ref<number>
  totalPages: ComputedRef<number>
  totalItems: ComputedRef<number>
  loading: Ref<boolean>
  goToPage: (page: number) => void
}

const byDateDesc = (a: LocalTransaction, b: LocalTransaction): number => {
  const aDate = a.date ? Date.parse(a.date) : 0
  const bDate = b.date ? Date.parse(b.date) : 0
  if (bDate !== aDate) return bDate - aDate
  const aCreated = a.created_at ? Date.parse(a.created_at) : 0
  const bCreated = b.created_at ? Date.parse(b.created_at) : 0
  return bCreated - aCreated
}

export function useTransactionsByCategory(
  categoryId: string,
  pageSize = 20
): UseTransactionsByCategoryReturn {
  const allRows = ref<LocalTransaction[]>([])
  const currentPage = ref(1)
  const loading = ref(false)

  const totalItems = computed(() => allRows.value.length)
  const totalPages = computed(() =>
    totalItems.value === 0 ? 0 : Math.ceil(totalItems.value / pageSize)
  )
  const items = computed<LocalTransaction[]>(() => {
    const start = (currentPage.value - 1) * pageSize
    return allRows.value.slice(start, start + pageSize)
  })

  async function fetchAll() {
    loading.value = true
    try {
      const pendingDeletes = await db.pendingMutations
        .where('entity_type').equals('transaction')
        .filter(m => m.operation === 'delete' || m.operation === 'delete_permanent')
        .toArray()
      const pendingDeleteIds = new Set(pendingDeletes.map(m => m.entity_id))

      const rawRows = await db.transactions.where('category_id').equals(categoryId).toArray()
      const rows = rawRows.filter(r => !pendingDeleteIds.has(r.id))
      rows.sort(byDateDesc)
      allRows.value = rows
      if (totalPages.value > 0 && currentPage.value > totalPages.value) {
        currentPage.value = totalPages.value
      }
    } finally {
      loading.value = false
    }
  }

  function goToPage(page: number) {
    const clamped = Math.max(1, Math.min(page, totalPages.value || 1))
    currentPage.value = clamped
  }

  function onSyncComplete() {
    currentPage.value = 1
    void fetchAll()
  }

  // Trigger immediately so it works in tests (no component lifecycle required).
  void fetchAll()

  onMounted(() => {
    window.addEventListener('wallet:sync-complete', onSyncComplete)
    window.addEventListener('wallet:local-delete', onSyncComplete)
  })

  onUnmounted(() => {
    window.removeEventListener('wallet:sync-complete', onSyncComplete)
    window.removeEventListener('wallet:local-delete', onSyncComplete)
  })

  return { items, currentPage, totalPages, totalItems, loading, goToPage }
}
