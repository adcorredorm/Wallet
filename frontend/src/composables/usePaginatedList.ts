/**
 * usePaginatedList — generic paginated list from a single Dexie table
 *
 * Why toArray() + sort + slice (not orderBy().offset().limit())?
 * Dexie's sortBy() returns Promise<T[]> — it cannot be chained with
 * .offset()/.limit(). orderBy() supports offset/limit but only sorts by
 * an indexed field. created_at is not indexed in WalletDB, so the only
 * correct approach is toArray() → JS sort → slice.
 *
 * Re-fetch trigger: listens to 'wallet:sync-complete' window event,
 * same event used by the Pinia stores' refreshFromDB() calls.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { db } from '@/offline'
import type { LocalTransaction } from '@/offline/types'
import type { LocalTransfer } from '@/offline/types'

type EntityType = 'transactions' | 'transfers'
type Row = LocalTransaction | LocalTransfer

export interface UsePaginatedListReturn<T extends Row> {
  items: ComputedRef<T[]>
  currentPage: Ref<number>
  totalPages: ComputedRef<number>
  totalItems: ComputedRef<number>
  loading: Ref<boolean>
  goToPage: (page: number) => void
}

const byCreatedAtDesc = (a: Row, b: Row): number => {
  const byCreated = (b.created_at ?? '').localeCompare(a.created_at ?? '')
  if (byCreated !== 0) return byCreated
  return (b.date ?? '').localeCompare(a.date ?? '')
}

export function usePaginatedList<T extends Row>(
  type: EntityType,
  pageSize = 20
) {
  const allRows = ref<T[]>([])
  const currentPage = ref(1)
  const loading = ref(false)

  const totalItems = computed(() => allRows.value.length)
  const totalPages = computed(() =>
    totalItems.value === 0 ? 0 : Math.ceil(totalItems.value / pageSize)
  )
  const items = computed<T[]>(() => {
    const start = (currentPage.value - 1) * pageSize
    return allRows.value.slice(start, start + pageSize) as T[]
  })

  async function fetchAll() {
    loading.value = true
    try {
      const rows = type === 'transactions'
        ? await db.transactions.toArray()
        : await db.transfers.toArray()
      rows.sort(byCreatedAtDesc)
      allRows.value = rows as T[]
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
    void fetchAll().then(() => { currentPage.value = 1 })
  }

  // Trigger the initial fetch immediately (not only in onMounted) so the
  // composable works correctly in unit tests where no component lifecycle
  // exists. The event listener is still registered in onMounted/onUnmounted
  // so it is properly cleaned up when a real component unmounts.
  void fetchAll()

  onMounted(() => {
    window.addEventListener('wallet:sync-complete', onSyncComplete)
  })

  onUnmounted(() => {
    window.removeEventListener('wallet:sync-complete', onSyncComplete)
  })

  return { items, currentPage, totalPages, totalItems, loading, goToPage }
}
