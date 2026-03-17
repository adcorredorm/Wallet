/**
 * useMovements — merged paginated list of transactions + transfers
 *
 * Why not reuse usePaginatedList?
 * usePaginatedList handles a single Dexie table. useMovements merges two
 * tables (transactions and transfers) and needs to dedup transfers when
 * filtering by accountId (source OR destination). These concerns are
 * fundamentally incompatible with the single-table abstraction.
 *
 * Algorithm — N * pageSize page-window:
 * To display page N with pageSize P:
 *   1. Count total records from both tables (totalTx + totalTr = totalItems)
 *   2. fetchLimit = N * P (worst case: all P records on page N come from one table)
 *   3. Fetch top fetchLimit rows from each table (filtered by accountId if given)
 *   4. Sort each list desc, merge, sort merged desc
 *   5. Slice [(N-1)*P, N*P] to get the current page
 *
 * Transfer accountId filtering:
 * Dexie can only use one index per query. To find transfers where accountId
 * is source OR destination we run two separate queries and dedup by id.
 *
 * Discriminator:
 * Each merged row gets `_type: 'transaction' | 'transfer'` at merge time
 * so consumers can narrow the union type without runtime checks on fields.
 *
 * Re-fetch trigger: listens to 'wallet:sync-complete' window event,
 * same pattern as usePaginatedList.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { db } from '@/offline'
import type { LocalTransaction, LocalTransfer } from '@/offline/types'

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type Movement =
  | (LocalTransaction & { _type: 'transaction' })
  | (LocalTransfer & { _type: 'transfer' })

export interface UseMovementsReturn {
  items: ComputedRef<Movement[]>
  currentPage: Ref<number>
  totalPages: ComputedRef<number>
  totalItems: ComputedRef<number>
  loading: Ref<boolean>
  goToPage: (page: number) => void
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const byCreatedAtDesc = (a: { created_at?: string; date?: string }, b: { created_at?: string; date?: string }): number => {
  const aDate = a.date ? Date.parse(a.date) : 0
  const bDate = b.date ? Date.parse(b.date) : 0
  if (bDate !== aDate) return bDate - aDate
  const aCreated = a.created_at ? Date.parse(a.created_at) : 0
  const bCreated = b.created_at ? Date.parse(b.created_at) : 0
  return bCreated - aCreated
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useMovements(
  accountId: string | undefined,
  pageSize = 20
): UseMovementsReturn {
  // allRows holds the slice of merged rows for the CURRENT page only.
  // The full merged list is reconstructed on every fetch — we never cache it
  // because the fetch itself is already bounded by fetchLimit = N * pageSize.
  const pageRows = ref<Movement[]>([])
  const currentPage = ref(1)
  const txCount = ref(0)
  const trCount = ref(0)
  const totalItems = computed(() => txCount.value + trCount.value)
  const loading = ref(false)

  const totalPages = computed(() =>
    totalItems.value === 0 ? 0 : Math.ceil(totalItems.value / pageSize)
  )

  const items = computed<Movement[]>(() => pageRows.value)

  // -------------------------------------------------------------------------
  // Fetch logic
  // -------------------------------------------------------------------------

  async function fetchPage() {
    loading.value = true
    try {
      const page = currentPage.value
      const fetchLimit = page * pageSize

      // Step 1 — count totals (cheap — no full table scan in Dexie)
      let txRows: LocalTransaction[]
      let trRows: LocalTransfer[]

      // Fetch pending deletes for both entity types to filter them out of results.
      // Records pending server deletion stay in Dexie with _sync_status: 'pending'
      // until the sync manager confirms removal — exclude them immediately.
      const [txPendingDeletes, trPendingDeletes] = await Promise.all([
        db.pendingMutations.where('entity_type').equals('transaction')
          .filter(m => m.operation === 'delete' || m.operation === 'delete_permanent')
          .toArray(),
        db.pendingMutations.where('entity_type').equals('transfer')
          .filter(m => m.operation === 'delete' || m.operation === 'delete_permanent')
          .toArray(),
      ])
      const txDeleteIds = new Set(txPendingDeletes.map(m => m.entity_id))
      const trDeleteIds = new Set(trPendingDeletes.map(m => m.entity_id))

      if (accountId) {
        // Filtered path — use index on account_id for transactions
        const txQuery = db.transactions.where('account_id').equals(accountId)
        let txCountVal: number
        ;[txCountVal, txRows] = await Promise.all([
          txQuery.count(),
          txQuery.toArray(),
        ])
        txRows = txRows.filter(r => !txDeleteIds.has(r.id))
        txCount.value = txRows.length
        txCountVal = txRows.length

        // Transfers need two queries: source OR destination
        const [trSrc, trDst] = await Promise.all([
          db.transfers.where('source_account_id').equals(accountId).toArray(),
          db.transfers.where('destination_account_id').equals(accountId).toArray(),
        ])

        // Dedup by id and filter pending deletes
        const trMap = new Map<string, LocalTransfer>()
        for (const t of [...trSrc, ...trDst]) trMap.set(t.id, t)
        trRows = Array.from(trMap.values()).filter(r => !trDeleteIds.has(r.id))
        trCount.value = trRows.length
      } else {
        // Unfiltered path — full table counts and arrays
        let txRaw: LocalTransaction[]
        let trRaw: LocalTransfer[]
        ;[txRaw, trRaw] = await Promise.all([
          db.transactions.toArray(),
          db.transfers.toArray(),
        ])
        txRows = txRaw.filter(r => !txDeleteIds.has(r.id))
        trRows = trRaw.filter(r => !trDeleteIds.has(r.id))
        txCount.value = txRows.length
        trCount.value = trRows.length
      }

      // Step 2 — totalItems is now a computed: txCount + trCount (already updated above)

      // Step 3 — sort each list desc, take only fetchLimit candidates
      txRows.sort(byCreatedAtDesc)
      trRows.sort(byCreatedAtDesc)
      const txCandidates = txRows.slice(0, fetchLimit)
      const trCandidates = trRows.slice(0, fetchLimit)

      // Step 4 — add discriminator, merge, sort merged list desc
      const txTagged: Movement[] = txCandidates.map(r => ({ ...r, _type: 'transaction' as const }))
      const trTagged: Movement[] = trCandidates.map(r => ({ ...r, _type: 'transfer' as const }))
      const merged = [...txTagged, ...trTagged]
      merged.sort(byCreatedAtDesc)

      // Step 5 — slice the current page
      const start = (page - 1) * pageSize
      pageRows.value = merged.slice(start, start + pageSize)

      // Clamp currentPage if it went out of range after a delete/filter change
      const pages = totalItems.value === 0 ? 0 : Math.ceil(totalItems.value / pageSize)
      if (pages > 0 && currentPage.value > pages) {
        currentPage.value = pages
      }
    } finally {
      loading.value = false
    }
  }

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  function goToPage(page: number) {
    const pages = totalPages.value || 1
    const clamped = Math.max(1, Math.min(page, pages))
    currentPage.value = clamped
    void fetchPage()
  }

  // -------------------------------------------------------------------------
  // Sync re-fetch
  // -------------------------------------------------------------------------

  function onSyncComplete() {
    currentPage.value = 1
    void fetchPage()
  }

  // Trigger immediately (same pattern as usePaginatedList) so tests work
  // without a component lifecycle.
  void fetchPage()

  onMounted(() => {
    window.addEventListener('wallet:sync-complete', onSyncComplete)
  })

  onUnmounted(() => {
    window.removeEventListener('wallet:sync-complete', onSyncComplete)
  })

  return { items, currentPage, totalPages, totalItems, loading, goToPage }
}
