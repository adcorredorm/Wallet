/**
 * Recurring Rules Store
 *
 * Manages recurring transaction rules.
 * All writes follow the offline-first pattern via useOfflineMutation.
 * PendingOccurrences are Dexie-only (not managed here — see usePendingOccurrences).
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { db, generateTempId } from '@/offline'
import type { LocalRecurringRule } from '@/offline/types'
import type { CreateRecurringRuleDto, UpdateRecurringRuleDto } from '@/types/recurring-rule'
import { useOfflineMutation } from '@/composables/useOfflineMutation'

export const useRecurringRulesStore = defineStore('recurringRules', () => {
  const rules = ref<LocalRecurringRule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---------------------------------------------------------------------------
  // Offline mutation composable
  // ---------------------------------------------------------------------------

  const mutation = useOfflineMutation<LocalRecurringRule, CreateRecurringRuleDto, UpdateRecurringRuleDto>({
    entityType: 'recurring_rule',
    table: db.recurringRules,
    items: rules,
    generateId: generateTempId,
    toLocal: (dto, id, now): LocalRecurringRule => ({
      id,
      offline_id: id,
      title: dto.title,
      type: dto.type,
      amount: dto.amount,
      account_id: dto.account_id,
      category_id: dto.category_id,
      description: dto.description ?? null,
      tags: dto.tags ?? [],
      requires_confirmation: dto.requires_confirmation ?? false,
      frequency: dto.frequency,
      interval: dto.interval ?? 1,
      day_of_week: dto.day_of_week ?? null,
      day_of_month: dto.day_of_month ?? null,
      start_date: dto.start_date,
      end_date: dto.end_date ?? null,
      max_occurrences: dto.max_occurrences ?? null,
      occurrences_created: 0,
      next_occurrence_date: dto.next_occurrence_date,
      status: dto.status ?? 'active',
      created_at: now,
      updated_at: now,
      _sync_status: 'pending' as const,
      _local_updated_at: now,
    }),
    mergeUpdate: (existing, dto, _now) => ({
      ...existing,
      ...dto,
    } as LocalRecurringRule),
    toCreatePayload: (local) => ({
      offline_id: local.offline_id ?? local.id,
      title: local.title,
      type: local.type,
      amount: local.amount,
      account_id: local.account_id,
      category_id: local.category_id,
      description: local.description,
      tags: local.tags,
      requires_confirmation: local.requires_confirmation,
      frequency: local.frequency,
      interval: local.interval,
      day_of_week: local.day_of_week,
      day_of_month: local.day_of_month,
      start_date: local.start_date,
      end_date: local.end_date,
      max_occurrences: local.max_occurrences,
      next_occurrence_date: local.next_occurrence_date,
      status: local.status,
    }),
    toUpdatePayload: (dto, _id) => dto as Record<string, unknown>,
  })

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  async function loadRules() {
    loading.value = true
    error.value = null
    try {
      const data = await db.recurringRules.toArray()
      rules.value = data
    } catch (err: any) {
      error.value = err.message || 'Error al cargar reglas recurrentes'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createRule(dto: CreateRecurringRuleDto): Promise<LocalRecurringRule> {
    loading.value = true
    error.value = null
    try {
      return await mutation.create(dto)
    } catch (err: any) {
      error.value = err.message || 'Error al crear regla recurrente'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateRule(id: string, dto: UpdateRecurringRuleDto): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await mutation.update(id, dto)
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar regla recurrente'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteRule(id: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await mutation.remove(id)
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar regla recurrente'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function refreshFromDB() {
    const data = await db.recurringRules.toArray()
    rules.value = data
  }

  // Refresh when sync completes — same pattern as other stores
  if (typeof window !== 'undefined') {
    window.addEventListener('wallet:sync-complete', () => {
      refreshFromDB().catch(console.error)
    })
  }

  return {
    rules,
    loading,
    error,
    loadRules,
    createRule,
    updateRule,
    deleteRule,
    refreshFromDB,
  }
})
