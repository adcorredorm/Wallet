/**
 * Transfers Store
 *
 * Manages transfers between accounts
 * - Filter by account (source or destination)
 * - Date range filtering
 * - CRUD operations
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { transfersApi } from '@/api/transfers'
import type {
  Transfer,
  CreateTransferDto,
  UpdateTransferDto,
  TransferFilters
} from '@/types'

export const useTransfersStore = defineStore('transfers', () => {
  // State
  const transfers = ref<Transfer[]>([])
  const filters = ref<TransferFilters>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchTransfers(customFilters?: TransferFilters) {
    loading.value = true
    error.value = null
    try {
      const appliedFilters = customFilters || filters.value
      transfers.value = await transfersApi.getAll(appliedFilters)
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
      const transfer = await transfersApi.getById(id)
      // Update or add to transfers array
      const index = transfers.value.findIndex(t => t.id === id)
      if (index >= 0) {
        transfers.value[index] = transfer
      } else {
        transfers.value.push(transfer)
      }
      return transfer
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transferencia'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchByAccount(accountId: string, customFilters?: TransferFilters) {
    loading.value = true
    error.value = null
    try {
      transfers.value = await transfersApi.getByAccount(accountId, customFilters)
    } catch (err: any) {
      error.value = err.message || 'Error al cargar transferencias de la cuenta'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTransfer(data: CreateTransferDto) {
    loading.value = true
    error.value = null
    try {
      const newTransfer = await transfersApi.create(data)
      transfers.value.unshift(newTransfer) // Add to beginning
      return newTransfer
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
      const updatedTransfer = await transfersApi.update(id, data)
      const index = transfers.value.findIndex(t => t.id === id)
      if (index >= 0) {
        transfers.value[index] = updatedTransfer
      }
      return updatedTransfer
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
      await transfersApi.delete(id)
      transfers.value = transfers.value.filter(t => t.id !== id)
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

  function getTransfersByAccount(accountId: string): Transfer[] {
    return transfers.value.filter(t =>
      t.cuenta_origen_id === accountId || t.cuenta_destino_id === accountId
    )
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
    fetchByAccount,
    createTransfer,
    updateTransfer,
    deleteTransfer,
    setFilters,
    clearFilters,
    getTransfersByAccount
  }
})
