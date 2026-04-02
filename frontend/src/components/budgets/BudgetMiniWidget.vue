<!-- frontend/src/components/budgets/BudgetMiniWidget.vue -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useBudgetsStore } from '@/stores/budgets'
import { useBudgetProgress } from '@/composables/useBudgetProgress'
import BudgetProgressBar from './BudgetProgressBar.vue'

const props = defineProps<{
  accountId?: string
  categoryId?: string
}>()

const budgetsStore = useBudgetsStore()

const budget = computed(() => {
  if (props.accountId) return budgetsStore.getBudgetForAccount(props.accountId)
  if (props.categoryId) return budgetsStore.getBudgetForCategory(props.categoryId)
  return undefined
})

import type { BudgetProgress } from '@/composables/useBudgetProgress'

const progressData = ref<BudgetProgress | null>(null)
let progressComposable: ReturnType<typeof useBudgetProgress> | null = null

onMounted(async () => {
  await budgetsStore.loadBudgets()
  if (budget.value) {
    progressComposable = useBudgetProgress(budget.value)
    await progressComposable.refresh()
    progressData.value = progressComposable.progress.value
  }
})

const progress = computed(() => progressData.value)
</script>

<template>
  <div v-if="budget && progress" class="mt-4 px-4">
    <div class="flex justify-between items-center mb-1">
      <p class="text-dark-text-tertiary text-xs uppercase tracking-wide">Presupuesto activo</p>
      <p class="text-dark-text-secondary text-xs">
        {{ progress.spent.toFixed(2) }} / {{ budget.amount_limit }} {{ budget.currency }}
      </p>
    </div>
    <BudgetProgressBar :percentage="progress.percentage" />
    <p v-if="progress.isOver" class="text-red-400 text-xs mt-1">Límite superado</p>
  </div>
</template>
