<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePendingOccurrences } from '@/composables/usePendingOccurrences'
import { useRecurringRulesStore } from '@/stores/recurringRules'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { useTransactionsStore } from '@/stores/transactions'
import type { LocalPendingOccurrence } from '@/offline/types'

const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const pendingHelper = usePendingOccurrences()
const rulesStore = useRecurringRulesStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const transactionsStore = useTransactionsStore()

const isConfirming = ref<string | null>(null)
const isDiscarding = ref<string | null>(null)

const pendingOccurrences = computed(() =>
  pendingHelper.occurrences.value.filter(o => o.status === 'pending')
)

function getRuleForOccurrence(occ: LocalPendingOccurrence) {
  return rulesStore.rules.find(r => r.id === occ.recurring_rule_id)
}

function getAccountName(accountId: string): string {
  return accountsStore.accounts.find(a => a.id === accountId)?.name ?? '—'
}

function getCategoryName(categoryId: string): string {
  return categoriesStore.categories.find(c => c.id === categoryId)?.name ?? '—'
}

function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-')
  return `${d}/${m}/${y}`
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount)
}

async function confirmOccurrence(occ: LocalPendingOccurrence) {
  const rule = getRuleForOccurrence(occ)
  if (!rule) return
  isConfirming.value = occ.id
  try {
    await transactionsStore.createTransaction({
      type: rule.type,
      amount: occ.suggested_amount,
      date: occ.due_date,
      account_id: rule.account_id,
      category_id: rule.category_id,
      title: rule.title,
      description: rule.description ?? undefined,
      tags: [...rule.tags.filter(t => t !== 'Recurrente'), 'Recurrente'],
      recurring_rule_id: rule.id,
    } as any)
    await pendingHelper.confirm(occ.id)
    // Increment occurrences_created now that a real transaction was created
    const updatedRule = rulesStore.rules.find(r => r.id === rule.id)
    if (updatedRule) {
      const newCount = (updatedRule.occurrences_created ?? 0) + 1
      await rulesStore.updateRule(rule.id, { occurrences_created: newCount } as any)
      // Check max_occurrences completion
      if (rule.max_occurrences && newCount >= rule.max_occurrences) {
        await rulesStore.updateRule(rule.id, { status: 'completed' } as any)
      }
    }
  } finally {
    isConfirming.value = null
  }
}

async function discardOccurrence(occ: LocalPendingOccurrence) {
  isDiscarding.value = occ.id
  try {
    await pendingHelper.discard(occ.id)
  } finally {
    isDiscarding.value = null
  }
}

function editOccurrence(occ: LocalPendingOccurrence) {
  const rule = getRuleForOccurrence(occ)
  if (!rule) return
  emit('close')
  router.push({
    name: 'transaction-create',
    query: {
      pending_occurrence_id: occ.id,
      recurring_rule_id: rule.id,
      type: rule.type,
      amount: String(occ.suggested_amount),
      date: occ.due_date,
      account_id: rule.account_id,
      category_id: rule.category_id,
      title: rule.title,
      description: rule.description ?? '',
    },
  })
}

function goToRecurring() {
  emit('close')
  router.push('/recurring')
}

onMounted(async () => {
  await pendingHelper.loadOccurrences()
  await rulesStore.loadRules()
})
</script>

<template>
  <div
    class="absolute right-0 top-full mt-2 w-80 rounded-xl border border-dark-border shadow-xl z-40 overflow-hidden"
    style="background-color: #1e293b;"
  >
    <!-- Header -->
    <div class="px-4 py-3 border-b border-dark-border flex items-center justify-between">
      <span class="text-sm font-semibold text-dark-text-primary">Transacciones pendientes</span>
      <span
        v-if="pendingOccurrences.length > 0"
        class="text-xs font-bold bg-red-500 text-white rounded-full px-2 py-0.5"
      >
        {{ pendingOccurrences.length }}
      </span>
    </div>

    <!-- Empty state -->
    <div
      v-if="pendingOccurrences.length === 0"
      class="px-4 py-8 text-center text-dark-text-secondary text-sm"
    >
      No hay transacciones pendientes
    </div>

    <!-- Occurrence list -->
    <ul v-else class="max-h-80 overflow-y-auto divide-y divide-dark-border">
      <li
        v-for="occ in pendingOccurrences"
        :key="occ.id"
        class="px-4 py-3"
      >
        <!-- Rule title + date -->
        <div class="flex items-start justify-between gap-2 mb-1">
          <span class="text-sm font-medium text-dark-text-primary leading-tight truncate">
            {{ getRuleForOccurrence(occ)?.title ?? '—' }}
          </span>
          <span class="text-xs text-dark-text-secondary whitespace-nowrap shrink-0">
            {{ formatDate(occ.due_date) }}
          </span>
        </div>

        <!-- Amount + account / category -->
        <div class="flex items-center gap-2 mb-2">
          <span
            class="text-sm font-semibold"
            :class="getRuleForOccurrence(occ)?.type === 'income' ? 'text-green-400' : 'text-red-400'"
          >
            {{ getRuleForOccurrence(occ)?.type === 'income' ? '+' : '-' }}{{ formatAmount(occ.suggested_amount) }}
          </span>
          <span class="text-xs text-dark-text-secondary">
            {{ getRuleForOccurrence(occ) ? getAccountName(getRuleForOccurrence(occ)!.account_id) : '—' }}
            ·
            {{ getRuleForOccurrence(occ) ? getCategoryName(getRuleForOccurrence(occ)!.category_id) : '—' }}
          </span>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2">
          <!-- Confirm -->
          <button
            class="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-xs font-medium bg-accent text-white hover:bg-blue-600 transition-colors disabled:opacity-50"
            style="min-height: 32px;"
            :disabled="isConfirming === occ.id || isDiscarding === occ.id"
            @click="confirmOccurrence(occ)"
          >
            <svg v-if="isConfirming === occ.id" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Confirmar
          </button>

          <!-- Edit -->
          <button
            class="p-1.5 rounded-lg text-dark-text-secondary hover:bg-dark-bg-tertiary hover:text-dark-text-primary transition-colors"
            style="min-width: 32px; min-height: 32px;"
            title="Ver regla"
            :disabled="isConfirming === occ.id || isDiscarding === occ.id"
            @click="editOccurrence(occ)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>

          <!-- Discard -->
          <button
            class="p-1.5 rounded-lg text-dark-text-secondary hover:bg-dark-bg-tertiary hover:text-red-400 transition-colors"
            style="min-width: 32px; min-height: 32px;"
            title="Descartar"
            :disabled="isConfirming === occ.id || isDiscarding === occ.id"
            @click="discardOccurrence(occ)"
          >
            <svg v-if="isDiscarding === occ.id" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </li>
    </ul>

    <!-- Footer -->
    <div class="px-4 py-2.5 border-t border-dark-border">
      <button
        class="w-full text-xs text-accent hover:underline text-center"
        @click="goToRecurring"
      >
        Ver todas las reglas recurrentes
      </button>
    </div>
  </div>
</template>
