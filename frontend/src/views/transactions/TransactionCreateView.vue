<script setup lang="ts">
/**
 * Transaction Create View
 *
 * Form to create a new transaction (income or expense).
 *
 * Safety net: if the user has no accounts OR no categories, the form is
 * replaced with an EmptyState that guides them back to the dashboard to
 * complete setup. This handles direct URL navigation to /transactions/new
 * before prerequisites are met (e.g., deep link, back-button quirk).
 *
 * On success: redirects to / (home) so the user lands on the dashboard
 * where they can see their updated activity.
 *
 * Note: fee creation from detail views is handled inline in the detail views.
 * The fee toggle on this form handles inline fee creation tied to the new transaction.
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTransactionsStore, useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import { useRecurringRulesStore } from '@/stores/recurringRules'
import { usePendingOccurrences } from '@/composables/usePendingOccurrences'
import TransactionForm from '@/components/transactions/TransactionForm.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { CreateTransactionDto, UpdateTransactionDto } from '@/types'

const router = useRouter()
const route = useRoute()
const initialAccountId = route.query.account_id as string | undefined

const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()
const rulesStore = useRecurringRulesStore()

// Pre-fill from pending occurrence (bell dropdown "Edit" action)
const pendingOccurrenceId = route.query.pending_occurrence_id as string | undefined
const recurringRuleId = route.query.recurring_rule_id as string | undefined
const prefill = pendingOccurrenceId
  ? {
      type: (route.query.type as 'income' | 'expense') ?? 'expense',
      amount: route.query.amount ? Number(route.query.amount) : undefined,
      date: route.query.date as string | undefined,
      account_id: route.query.account_id as string | undefined,
      category_id: route.query.category_id as string | undefined,
      title: route.query.title as string | undefined,
      description: route.query.description as string | undefined,
    }
  : undefined

const accounts = computed(() => accountsStore.activeAccounts)
const categories = computed(() => categoriesStore.categories)

/** True when prerequisites for transaction creation are missing */
const needsSetup = computed(
  () => accountsStore.activeAccounts.length === 0 || categoriesStore.activeCategories.length === 0
)

const pendingHelper = usePendingOccurrences()

async function handleSubmit(data: CreateTransactionDto | UpdateTransactionDto, feeData?: CreateTransactionDto) {
  try {
    const createData = data as CreateTransactionDto
    // If editing a pending occurrence, attach the recurring_rule_id
    if (pendingOccurrenceId && recurringRuleId) {
      ;(createData as any).recurring_rule_id = recurringRuleId
    }
    const parentTx = await transactionsStore.createTransaction(createData)

    // If a fee was submitted inline via the form toggle, create it linked to the parent
    if (feeData && parentTx?.id) {
      const feePayload: CreateTransactionDto = {
        ...feeData,
        fee_for_transaction_id: parentTx.id,
      }
      try {
        await transactionsStore.createTransaction(feePayload)
      } catch {
        uiStore.showError('Transacción creada, pero hubo un error al registrar el fee. Puedes agregarlo desde el detalle.')
      }
    }

    // Mark pending occurrence as confirmed and increment occurrences_created on the rule
    if (pendingOccurrenceId) {
      await pendingHelper.loadOccurrences()
      await pendingHelper.confirm(pendingOccurrenceId)
      if (recurringRuleId) {
        await rulesStore.loadRules()
        const rule = rulesStore.rules.find(r => r.id === recurringRuleId)
        if (rule) {
          const newCount = (rule.occurrences_created ?? 0) + 1
          await rulesStore.updateRule(rule.id, { occurrences_created: newCount } as any)
          if (rule.max_occurrences && newCount >= rule.max_occurrences) {
            await rulesStore.updateRule(rule.id, { status: 'completed' } as any)
          }
        }
      }
    }
    uiStore.showSuccess('Transacción creada exitosamente')
    router.push('/')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al crear transacción')
  }
}

function handleCancel() {
  router.back()
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Nueva Transacción</h1>

    <!-- Safety net: shown when account or category prerequisites are missing -->
    <EmptyState
      v-if="needsSetup"
      icon="🔒"
      title="Configura tu wallet primero"
      message="Necesitas al menos una cuenta y una categoría para crear transacciones"
      action-text="Ir al inicio"
      @action="router.push('/')"
    />

    <BaseCard v-else>
      <TransactionForm
        :accounts="accounts"
        :categories="categories"
        :loading="transactionsStore.loading"
        :initial-account-id="initialAccountId"
        :prefill="prefill"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>
  </div>
</template>
