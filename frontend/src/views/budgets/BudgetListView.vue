<!-- frontend/src/views/budgets/BudgetListView.vue -->
<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBudgetsStore } from '@/stores/budgets'
import { useBudgetProgress } from '@/composables/useBudgetProgress'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { formatCurrency } from '@/utils/formatters'
import BudgetProgressBar from '@/components/budgets/BudgetProgressBar.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import type { LocalBudget } from '@/offline/types'

const router = useRouter()
const budgetsStore = useBudgetsStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()

// Budget progress cache: budgetId → BudgetProgress composable
const progressMap = {} as Record<string, ReturnType<typeof useBudgetProgress>>

function getProgress(budget: LocalBudget) {
  if (!progressMap[budget.id]) {
    progressMap[budget.id] = useBudgetProgress(budget)
  }
  return progressMap[budget.id].progress.value
}

function scopeLabel(budget: LocalBudget): string {
  if (budget.account_id) {
    const acc = accountsStore.accounts.find(a => a.id === budget.account_id)
    return acc ? `${acc.icon ? acc.icon + ' ' : ''}${acc.name}` : 'Cuenta'
  }
  const cat = categoriesStore.categories.find(c => c.id === budget.category_id)
  return cat ? `${cat.icon ? cat.icon + ' ' : ''}${cat.name}` : 'Categoría'
}

async function refreshAllProgress() {
  for (const b of budgetsStore.visibleBudgets) {
    if (!progressMap[b.id]) {
      progressMap[b.id] = useBudgetProgress(b)
    }
    await progressMap[b.id].refresh()
  }
}

onMounted(async () => {
  await budgetsStore.loadBudgets()
  await refreshAllProgress()
})

function onSyncComplete() { refreshAllProgress() }
onMounted(() => window.addEventListener('wallet:sync-complete', onSyncComplete))
onUnmounted(() => window.removeEventListener('wallet:sync-complete', onSyncComplete))
</script>

<template>
  <div class="flex flex-col min-h-screen bg-dark-bg pb-20">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 pt-6 pb-4">
      <h1 class="text-xl font-bold text-dark-text-primary">Presupuestos</h1>
      <BaseButton variant="primary" size="sm" @click="router.push('/budgets/new')">
        + Nuevo
      </BaseButton>
    </div>

    <!-- Loading -->
    <div v-if="budgetsStore.loading" class="flex justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-blue" />
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else-if="budgetsStore.visibleBudgets.length === 0"
      title="Sin presupuestos"
      message="Crea un presupuesto para controlar tus gastos"
      @action="router.push('/budgets/new')"
    />

    <template v-else>
      <!-- Active budgets -->
      <div class="px-4 space-y-3">
        <BaseCard
          v-for="budget in budgetsStore.activeBudgets"
          :key="budget.id"
          :clickable="true"
          class="cursor-pointer"
          @click="router.push(`/budgets/${budget.id}`)"
        >
          <div class="flex justify-between items-start mb-2">
            <div>
              <p class="text-dark-text-primary font-medium">{{ budget.name }}</p>
              <p class="text-dark-text-tertiary text-xs">{{ scopeLabel(budget) }}</p>
            </div>
            <div class="text-right">
              <p class="text-dark-text-primary text-sm font-semibold">
                {{ formatCurrency(getProgress(budget).spent, budget.currency, true) }} / {{ formatCurrency(budget.amount_limit, budget.currency, true) }}
              </p>
              <p class="text-dark-text-tertiary text-xs">
                {{ getProgress(budget).periodStart }} – {{ getProgress(budget).periodEnd }}
              </p>
            </div>
          </div>
          <BudgetProgressBar :percentage="getProgress(budget).percentage" />
          <p v-if="getProgress(budget).isOver" class="text-red-400 text-xs mt-1">
            Límite superado
          </p>
        </BaseCard>
      </div>

      <!-- Paused budgets -->
      <div v-if="budgetsStore.pausedBudgets.length > 0" class="px-4 mt-6">
        <p class="text-dark-text-tertiary text-xs uppercase tracking-wide mb-2">Pausados</p>
        <BaseCard
          v-for="budget in budgetsStore.pausedBudgets"
          :key="budget.id"
          :clickable="true"
          class="cursor-pointer opacity-60"
          @click="router.push(`/budgets/${budget.id}`)"
        >
          <p class="text-dark-text-secondary text-sm">{{ budget.name }}</p>
          <p class="text-dark-text-tertiary text-xs">Pausado</p>
        </BaseCard>
      </div>
    </template>
  </div>
</template>
