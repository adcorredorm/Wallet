// frontend/src/stores/budgets.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { db, generateTempId } from '@/offline'
import type { LocalBudget } from '@/offline/types'
import type { CreateBudgetDto, UpdateBudgetDto } from '@/types/budget'
import { useOfflineMutation } from '@/composables/useOfflineMutation'

export const useBudgetsStore = defineStore('budgets', () => {
  const budgets = ref<LocalBudget[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeBudgets = computed(() =>
    budgets.value.filter(b => b.status === 'active')
  )

  const pausedBudgets = computed(() =>
    budgets.value.filter(b => b.status === 'paused')
  )

  const visibleBudgets = computed(() =>
    budgets.value.filter(b => b.status !== 'archived')
  )

  const mutation = useOfflineMutation<LocalBudget, CreateBudgetDto, UpdateBudgetDto>({
    entityType: 'budget',
    table: db.budgets,
    items: budgets,
    generateId: generateTempId,
    toLocal: (dto, id, now): LocalBudget => ({
      id,
      offline_id: id,
      name: dto.name,
      account_id: dto.account_id ?? null,
      category_id: dto.category_id ?? null,
      amount_limit: dto.amount_limit,
      currency: dto.currency,
      budget_type: dto.budget_type,
      frequency: dto.frequency ?? null,
      interval: dto.interval ?? 1,
      reference_date: dto.reference_date ?? null,
      start_date: dto.start_date ?? null,
      end_date: dto.end_date ?? null,
      status: dto.status ?? 'active',
      icon: dto.icon ?? null,
      color: dto.color ?? null,
      created_at: now,
      updated_at: now,
      _sync_status: 'pending' as const,
      _local_updated_at: now,
    }),
    mergeUpdate: (existing, dto, _now) => ({
      ...existing,
      ...dto,
    } as LocalBudget),
    toCreatePayload: (local) => ({
      offline_id: local.offline_id ?? local.id,
      name: local.name,
      account_id: local.account_id,
      category_id: local.category_id,
      amount_limit: local.amount_limit,
      currency: local.currency,
      budget_type: local.budget_type,
      frequency: local.frequency,
      interval: local.interval,
      reference_date: local.reference_date,
      start_date: local.start_date,
      end_date: local.end_date,
      status: local.status,
      icon: local.icon,
      color: local.color,
    }),
    toUpdatePayload: (dto, _id) => dto as Record<string, unknown>,
    onRemove: async (id, _existing) => {
      await db.budgets.update(id, { status: 'archived', _sync_status: 'pending' })
      const idx = budgets.value.findIndex(b => b.id === id)
      if (idx !== -1) {
        budgets.value[idx] = { ...budgets.value[idx], status: 'archived', _sync_status: 'pending' }
      }
    },
  })

  async function loadBudgets() {
    loading.value = true
    error.value = null
    try {
      budgets.value = await db.budgets
        .where('status')
        .notEqual('archived')
        .toArray()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Error loading budgets'
    } finally {
      loading.value = false
    }
  }

  function getBudgetForAccount(accountId: string): LocalBudget | undefined {
    return activeBudgets.value.find(b => b.account_id === accountId)
  }

  function getBudgetForCategory(categoryId: string): LocalBudget | undefined {
    return activeBudgets.value.find(b => b.category_id === categoryId)
  }

  const createBudget = (dto: CreateBudgetDto) => mutation.create(dto)
  const updateBudget = (id: string, dto: UpdateBudgetDto) => mutation.update(id, dto)
  const archiveBudget = (id: string) => mutation.remove(id)
  const deleteBudgetPermanent = (id: string) => mutation.remove(id)

  if (typeof window !== 'undefined') {
    window.addEventListener('wallet:sync-complete', () => {
      loadBudgets().catch(console.error)
    })
  }

  return {
    budgets,
    loading,
    error,
    activeBudgets,
    pausedBudgets,
    visibleBudgets,
    loadBudgets,
    getBudgetForAccount,
    getBudgetForCategory,
    createBudget,
    updateBudget,
    archiveBudget,
    deleteBudgetPermanent,
  }
})
