/**
 * Transfers Store
 *
 * Manages transfers between accounts
 * - Filter by account (source or destination)
 * - Date range filtering
 * - CRUD operations
 *
 * Phase 3 change: write actions now follow the offline-first pattern.
 * Writes go to IndexedDB and the mutation queue immediately; the UI updates
 * optimistically. The SyncManager (Phase 4) will flush to the server.
 *
 * Important: source_account_id and destination_account_id in transfer payloads
 * may be temporary IDs if either account was created offline. The IDs are
 * preserved verbatim in the mutation payload. The SyncManager resolves
 * temp IDs to real server UUIDs before sending the mutation, relying on
 * FIFO queue ordering to guarantee the account CREATEs are processed first.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { transfersApi } from '@/api/transfers'
import type {
  CreateTransferDto,
  UpdateTransferDto,
  TransferFilters
} from '@/types'
import { db, fetchByIdWithRevalidation, generateTempId, mutationQueue } from '@/offline'
import type { LocalTransfer } from '@/offline'
import { useAccountsStore } from '@/stores/accounts'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'

export const useTransfersStore = defineStore('transfers', () => {
  // Cross-store references — called at the top of the setup function so that
  // Vue tracks reactive reads from these stores inside computed() bodies.
  const accountsStore = useAccountsStore()
  const exchangeRatesStore = useExchangeRatesStore()
  const settingsStore = useSettingsStore()

  // State
  // Why LocalTransfer[] instead of Transfer[]?
  // LocalTransfer extends Transfer, so all consumers continue to work.
  const transfers = ref<LocalTransfer[]>([])
  const filters = ref<TransferFilters>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, stale-while-revalidate)
  // ---------------------------------------------------------------------------

  async function fetchTransfers() {
    loading.value = true
    error.value = null
    try {
      await refreshFromDB()
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transferencias'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTransferById(id: string) {
    loading.value = true
    error.value = null
    try {
      const localItem = await fetchByIdWithRevalidation(
        db.transfers,
        id,
        (transferId) => transfersApi.getById(transferId),
        (freshItem) => {
          const index = transfers.value.findIndex(t => t.id === id)
          if (index >= 0) {
            transfers.value[index] = freshItem
          } else {
            transfers.value.push(freshItem)
          }
        }
      )

      if (localItem) {
        const index = transfers.value.findIndex(t => t.id === id)
        if (index >= 0) {
          transfers.value[index] = localItem
        } else {
          transfers.value.push(localItem)
        }
        return localItem
      }
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transferencia'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Writes (Phase 3: offline-first pattern)
  // ---------------------------------------------------------------------------

  async function createTransfer(data: CreateTransferDto) {
    const tempId = generateTempId()
    const now = new Date().toISOString()

    // Capture base_rate from the source account's currency at transfer creation time.
    // Only the source account's rate is captured; the destination account's net worth
    // effect is tracked via destination_amount which is already in destination currency.
    const srcAccount = accountsStore.accounts.find(a => a.id === data.source_account_id)
    const srcRate = srcAccount
      ? exchangeRatesStore.getRate(srcAccount.currency, settingsStore.primaryCurrency)
      : null

    // Build the full local transfer record.
    // tags defaults to [] because the Transfer interface requires string[]
    // (not optional), while CreateTransferDto.tags is optional.
    // source_account_id and destination_account_id are kept verbatim — they may
    // be temp-* IDs if either account was created offline in the same session.
    const localTransfer: LocalTransfer = {
      id: tempId,
      source_account_id: data.source_account_id,
      destination_account_id: data.destination_account_id,
      amount: data.amount,
      date: data.date,
      title: data.title,
      description: data.description,
      tags: data.tags ?? [],
      created_at: now,
      updated_at: now,
      _sync_status: 'pending',
      _local_updated_at: now,
      // Cross-currency fields: undefined for same-currency transfers, present for FX transfers.
      // Storing them here ensures IndexedDB (source of truth) has the full record and
      // recomputeBalancesFromTransactions() can use destination_amount on reload.
      destination_amount: data.destination_amount,
      exchange_rate: data.exchange_rate,
      destination_currency: data.destination_currency,
      base_rate: srcRate
    }

    loading.value = true
    error.value = null
    try {
      // Step 1 — IndexedDB write.
      await db.transfers.add(localTransfer)

      // Step 2 — Optimistic UI update. unshift places the newest transfer
      // at the top of the list to match read action ordering.
      transfers.value.unshift(localTransfer)

      // Adjust both account balances immediately so the UI is accurate offline.
      // Source always loses `amount` (the amount sent, in the source currency).
      // Destination gains `destination_amount` when set (cross-currency FX transfer)
      // or falls back to `amount` for same-currency transfers where destination_amount
      // is undefined. The ?? operator handles both cases cleanly.
      accountsStore.adjustBalance(data.source_account_id, -Number(data.amount))
      accountsStore.adjustBalance(
        data.destination_account_id,
        Number(data.destination_amount ?? data.amount)
      )

      // Step 3 — Enqueue CREATE mutation.
      // client_id enables server-side idempotency on retries.
      // source_account_id / destination_account_id may be temp IDs.
      await mutationQueue.enqueue({
        entity_type: 'transfer',
        entity_id: tempId,
        operation: 'create',
        payload: { ...data, base_rate: srcRate, client_id: tempId }
      })

      return localTransfer
    } catch (err: any) {
      error.value = err.message || 'Error al crear transferencia'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTransfer(id: string, data: UpdateTransferDto) {
    const localUpdatedAt = new Date().toISOString()

    // Recompute base_rate using the effective source account after this update.
    const effectiveSrcId = data.source_account_id ?? (
      transfers.value.find(t => t.id === id)?.source_account_id
    )
    const updateSrcAccount = effectiveSrcId
      ? accountsStore.accounts.find(a => a.id === effectiveSrcId)
      : undefined
    const updateSrcRate = updateSrcAccount
      ? exchangeRatesStore.getRate(updateSrcAccount.currency, settingsStore.primaryCurrency)
      : null

    loading.value = true
    error.value = null
    try {
      // Step 1 — Partial IndexedDB update.
      await db.transfers.update(id, {
        ...data,
        base_rate: updateSrcRate,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      })

      // Step 2 — Reactive ref update + optimistic balance adjustment.
      const idx = transfers.value.findIndex(t => t.id === id)
      if (idx !== -1) {
        const old = transfers.value[idx]
        transfers.value[idx] = {
          ...old,
          ...data,
          base_rate: updateSrcRate,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        }

        // Reverse the old transfer's effect, then apply the updated values.
        // This handles all cases: amount change, account change, or both.
        // For the destination reversal we use destination_amount ?? amount so a
        // cross-currency transfer is undone at the correct received amount, not
        // the source amount.
        accountsStore.adjustBalance(old.source_account_id, Number(old.amount))
        accountsStore.adjustBalance(
          old.destination_account_id,
          -Number(old.destination_amount ?? old.amount)
        )
        const newSourceId = data.source_account_id ?? old.source_account_id
        const newDestinationId = data.destination_account_id ?? old.destination_account_id
        const newAmount = data.amount ?? old.amount
        const newDestinationAmount = data.destination_amount ?? old.destination_amount
        accountsStore.adjustBalance(newSourceId, -Number(newAmount))
        accountsStore.adjustBalance(
          newDestinationId,
          Number(newDestinationAmount ?? newAmount)
        )
      }

      // Step 3 — Merge optimisation: collapse UPDATE into pending CREATE.
      const pendingCreate = await mutationQueue.findPendingCreate('transfer', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.updatePayload(pendingCreate.id, {
          ...pendingCreate.payload,
          ...data
        })
      } else {
        await mutationQueue.enqueue({
          entity_type: 'transfer',
          entity_id: id,
          operation: 'update',
          payload: { ...data, base_rate: updateSrcRate } as Record<string, unknown>
        })
      }
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar transferencia'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteTransfer(id: string) {
    loading.value = true
    error.value = null
    try {
      // Capture the transfer before removal so we can reverse its balance effects.
      const transfer = transfers.value.find(t => t.id === id)

      // Cancellation optimisation: if the CREATE is still pending, remove
      // everything locally without sending anything to the server.
      const pendingCreate = await mutationQueue.findPendingCreate('transfer', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.remove(pendingCreate.id)
        await db.transfers.delete(id)
        transfers.value = transfers.value.filter(t => t.id !== id)
        if (transfer) {
          // Restore source by adding back `amount`; restore destination by
          // removing `destination_amount ?? amount` — mirroring the create logic.
          accountsStore.adjustBalance(transfer.source_account_id, Number(transfer.amount))
          accountsStore.adjustBalance(
            transfer.destination_account_id,
            -Number(transfer.destination_amount ?? transfer.amount)
          )
        }
        return
      }

      // Entity exists on the server — mark pending, remove from UI, enqueue DELETE.
      await db.transfers.update(id, { _sync_status: 'pending' })
      transfers.value = transfers.value.filter(t => t.id !== id)
      if (transfer) {
        // Same reversal logic as the pending-CREATE path above.
        accountsStore.adjustBalance(transfer.source_account_id, Number(transfer.amount))
        accountsStore.adjustBalance(
          transfer.destination_account_id,
          -Number(transfer.destination_amount ?? transfer.amount)
        )
      }

      await mutationQueue.enqueue({
        entity_type: 'transfer',
        entity_id: id,
        operation: 'delete',
        payload: { id }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar transferencia'
      throw err
    } finally {
      loading.value = false
    }
  }

  function setFilters(newFilters: TransferFilters) {
    filters.value = newFilters
  }

  function clearFilters() {
    filters.value = {}
  }

  function getTransfersByAccount(accountId: string): LocalTransfer[] {
    return transfers.value.filter(t =>
      t.source_account_id === accountId || t.destination_account_id === accountId
    )
  }

  async function refreshFromDB() {
    const data = await db.transfers.toArray()
    transfers.value = [...data].sort((a, b) => b.date.localeCompare(a.date))
  }

  return {
    // State
    transfers,
    filters,
    loading,
    error,
    // Actions
    fetchTransfers,
    fetchTransferById,
    createTransfer,
    updateTransfer,
    deleteTransfer,
    setFilters,
    clearFilters,
    getTransfersByAccount,
    refreshFromDB
  }
})
