<!-- frontend/src/views/budgets/BudgetDetailView.vue -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBudgetsStore } from '@/stores/budgets'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { useBudgetProgress } from '@/composables/useBudgetProgress'
import { formatCurrency } from '@/utils/formatters'
import BudgetProgressBar from '@/components/budgets/BudgetProgressBar.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const budgetsStore = useBudgetsStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()

const budgetId = route.params.id as string
const budget = computed(() => budgetsStore.budgets.find(b => b.id === budgetId))

const { progress, refresh } = useBudgetProgress(
  computed(() => budget.value!)
)

const showArchiveDialog = ref(false)
const archiving = ref(false)

const scopeLabel = computed(() => {
  if (!budget.value) return ''
  if (budget.value.account_id) {
    const acc = accountsStore.accounts.find(a => a.id === budget.value!.account_id)
    return acc ? `${acc.icon ? acc.icon + ' ' : ''}${acc.name}` : 'Cuenta'
  }
  const cat = categoriesStore.categories.find(c => c.id === budget.value!.category_id)
  return cat ? `${cat.icon ? cat.icon + ' ' : ''}${cat.name}` : 'Categoría'
})

const freqLabels: Record<string, string> = {
  daily: 'día',
  weekly: 'semana',
  monthly: 'mes',
  yearly: 'año',
}

const periodLabel = computed(() => {
  if (!budget.value) return ''
  if (budget.value.budget_type === 'recurring') {
    const freq = budget.value.frequency ?? 'monthly'
    const label = freqLabels[freq] ?? freq
    const budgetInterval = budget.value.interval ?? 1
    return budgetInterval === 1 ? `Cada ${label}` : `Cada ${budgetInterval} ${label}s`
  }
  return `${budget.value.start_date} – ${budget.value.end_date}`
})

async function confirmArchive() {
  archiving.value = true
  try {
    await budgetsStore.archiveBudget(budgetId)
    router.push('/budgets')
  } finally {
    archiving.value = false
  }
}

async function togglePause() {
  if (!budget.value) return
  const newStatus = budget.value.status === 'paused' ? 'active' : 'paused'
  await budgetsStore.updateBudget(budgetId, { status: newStatus })
}

onMounted(async () => {
  await budgetsStore.loadBudgets()
  await refresh()
})
</script>

<template>
  <div v-if="budget" class="flex flex-col min-h-screen bg-dark-bg pb-20">
    <div class="px-4 pt-6 pb-4">
      <h1 class="text-xl font-bold text-dark-text-primary">{{ budget.name }}</h1>
      <p class="text-dark-text-tertiary text-sm">{{ scopeLabel }} · {{ periodLabel }}</p>
    </div>

    <!-- Progress card -->
    <BaseCard class="mx-4 mb-4">
      <div class="flex justify-between mb-3">
        <div>
          <p class="text-dark-text-tertiary text-xs">Gastado</p>
          <p class="text-dark-text-primary text-2xl font-bold">
            {{ formatCurrency(progress.spent, budget.currency, true) }}
          </p>
        </div>
        <div class="text-right">
          <p class="text-dark-text-tertiary text-xs">Límite</p>
          <p class="text-dark-text-secondary text-2xl">
            {{ formatCurrency(budget.amount_limit, budget.currency, true) }}
          </p>
        </div>
      </div>
      <BudgetProgressBar :percentage="progress.percentage" height="h-3" />
      <div class="flex justify-between mt-2">
        <p class="text-dark-text-tertiary text-xs">{{ progress.periodStart }} – {{ progress.periodEnd }}</p>
        <p :class="['text-xs font-semibold', progress.isOver ? 'text-red-400' : 'text-dark-text-secondary']">
          {{ progress.percentage.toFixed(0) }}%
        </p>
      </div>
      <p class="text-dark-text-tertiary text-sm mt-2">
        Disponible:
        <span :class="progress.isOver ? 'text-red-400' : 'text-green-400'">
          {{ formatCurrency(budget.amount_limit - progress.spent, budget.currency, true) }}
        </span>
      </p>
    </BaseCard>

    <!-- Actions -->
    <div class="px-4 space-y-2">
      <BaseButton variant="secondary" class="w-full" @click="router.push(`/budgets/${budgetId}/edit`)">
        Editar
      </BaseButton>
      <BaseButton variant="secondary" class="w-full" @click="togglePause">
        {{ budget.status === 'paused' ? 'Reactivar' : 'Pausar' }}
      </BaseButton>
      <BaseButton variant="danger" class="w-full" @click="showArchiveDialog = true">
        Archivar
      </BaseButton>
    </div>

    <ConfirmDialog
      :show="showArchiveDialog"
      title="Archivar presupuesto"
      message="¿Archivás este presupuesto? Ya no aparecerá en la lista principal."
      confirm-text="Archivar"
      :loading="archiving"
      @confirm="confirmArchive"
      @cancel="showArchiveDialog = false"
    />
  </div>

  <div v-else class="flex items-center justify-center min-h-screen">
    <p class="text-dark-text-tertiary">Presupuesto no encontrado</p>
  </div>
</template>
