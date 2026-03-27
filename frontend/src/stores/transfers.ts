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
import type {
  CreateTransferDto,
  UpdateTransferDto,
  TransferFilters
} from '@/types'
import { db, generateTempId } from '@/offline'
import type { LocalTransfer } from '@/offline'
import { useAccountsStore } from '@/stores/accounts'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import { useOfflineMutation } from '@/composables/useOfflineMutation'

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
  // Offline mutation composable — transfers
  // ---------------------------------------------------------------------------

  const transferMutation = useOfflineMutation<LocalTransfer, CreateTransferDto, UpdateTransferDto>({
    entityType: 'transfer',
    table: db.transfers,
    items: transfers,
    generateId: generateTempId,
    toLocal: (dto, id, now) => {
      const srcAccount = accountsStore.accounts.find(a => a.id === dto.source_account_id)
      const srcRate = srcAccount
        ? exchangeRatesStore.getRate(srcAccount.currency, settingsStore.primaryCurrency)
        : null

      return {
        id,
        source_account_id: dto.source_account_id,
        destination_account_id: dto.destination_account_id,
        amount: dto.amount,
        date: dto.date,
        title: dto.title,
        description: dto.description,
        tags: dto.tags ?? [],
        created_at: now,
        updated_at: now,
        _sync_status: 'pending' as const,
        _local_updated_at: now,
        destination_amount: dto.destination_amount,
        exchange_rate: dto.exchange_rate,
        destination_currency: dto.destination_currency,
        base_rate: srcRate,
      }
    },
    mergeUpdate: (existing, dto, _now) => ({
      ...existing,
      ...dto,
    } as LocalTransfer),
    toCreatePayload: (local) => ({
      source_account_id: local.source_account_id,
      destination_account_id: local.destination_account_id,
      amount: local.amount,
      date: local.date,
      title: local.title,
      description: local.description,
      tags: local.tags,
      destination_amount: local.destination_amount,
      exchange_rate: local.exchange_rate,
      destination_currency: local.destination_currency,
      base_rate: local.base_rate,
      offline_id: local.id,
    }),
    toUpdatePayload: (dto) => dto as Record<string, unknown>,
    afterCreate: (local) => {
      accountsStore.adjustBalance(local.source_account_id, -Number(local.amount))
      accountsStore.adjustBalance(
        local.destination_account_id,
        Number(local.destination_amount ?? local.amount)
      )
    },
    beforeUpdate: (_id, dto, existing) => {
      const effectiveSrcId = dto.source_account_id ?? existing.source_account_id
      const updateSrcAccount = effectiveSrcId
        ? accountsStore.accounts.find(a => a.id === effectiveSrcId)
        : undefined
      const updateSrcRate = updateSrcAccount
        ? exchangeRatesStore.getRate(updateSrcAccount.currency, settingsStore.primaryCurrency)
        : null
      return { ...dto, base_rate: updateSrcRate } as UpdateTransferDto
    },
    afterUpdate: (_id, _dto, old, merged) => {
      // Reverse old transfer's effect (4 adjustBalance calls)
      accountsStore.adjustBalance(old.source_account_id, Number(old.amount))
      accountsStore.adjustBalance(
        old.destination_account_id,
        -Number(old.destination_amount ?? old.amount)
      )
      // Apply new values
      accountsStore.adjustBalance(merged.source_account_id, -Number(merged.amount))
      accountsStore.adjustBalance(
        merged.destination_account_id,
        Number(merged.destination_amount ?? merged.amount)
      )
    },
    afterRemove: (_id, removed) => {
      accountsStore.adjustBalance(removed.source_account_id, Number(removed.amount))
      accountsStore.adjustBalance(
        removed.destination_account_id,
        -Number(removed.destination_amount ?? removed.amount)
      )
    },
    afterRemoveEvent: 'wallet:local-delete',
  })

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, Dexie-only)
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

  async function fetchTransferById(id: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const item = await db.transfers.get(id)
      if (item) {
        const index = transfers.value.findIndex(t => t.id === id)
        if (index >= 0) transfers.value[index] = item
        else transfers.value.push(item)
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
    loading.value = true
    error.value = null
    try {
      const local = await transferMutation.create(data)
      // Move to front for display order (composable pushes to end)
      const idx = transfers.value.indexOf(local)
      if (idx > 0) {
        transfers.value.splice(idx, 1)
        transfers.value.unshift(local)
      }
      return local
    } catch (err: any) {
      error.value = err.message || 'Error al crear transferencia'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTransfer(id: string, data: UpdateTransferDto) {
    loading.value = true
    error.value = null
    try {
      await transferMutation.update(id, data)
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
      await transferMutation.remove(id)
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
