<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRecurringRulesStore } from '@/stores/recurringRules'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { useUiStore } from '@/stores'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'
import type { LocalRecurringRule } from '@/offline/types'

const router = useRouter()
const rulesStore = useRecurringRulesStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

onMounted(async () => {
  try {
    await Promise.all([
      rulesStore.loadRules(),
      accountsStore.fetchAccounts(),
      categoriesStore.fetchCategories(),
    ])
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al cargar reglas recurrentes')
  }
})

const activeRules = computed(() => rulesStore.rules.filter(r => r.status === 'active'))
const pausedRules = computed(() => rulesStore.rules.filter(r => r.status === 'paused'))
const completedRules = computed(() => rulesStore.rules.filter(r => r.status === 'completed'))

function getAccountName(id: string): string {
  return accountsStore.accounts.find(a => a.id === id)?.name ?? '—'
}

function getCategoryName(id: string): string {
  return categoriesStore.categories.find(c => c.id === id)?.name ?? '—'
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount)
}

const FREQUENCY_LABELS: Record<string, string> = {
  daily: 'Diario',
  weekly: 'Semanal',
  monthly: 'Mensual',
  yearly: 'Anual',
}

function frequencyLabel(rule: LocalRecurringRule): string {
  const base = FREQUENCY_LABELS[rule.frequency] ?? rule.frequency
  return rule.interval > 1 ? `Cada ${rule.interval} ${base.toLowerCase()}s` : base
}

function goToDetail(id: string) {
  router.push(`/recurring/${id}`)
}

function createRule() {
  router.push('/recurring/new')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Recurrentes</h1>
    </div>

    <!-- Loading -->
    <BaseSpinner v-if="rulesStore.loading" centered />

    <!-- Error -->
    <EmptyState
      v-else-if="rulesStore.error"
      title="Error al cargar"
      :message="rulesStore.error"
      icon="⚠️"
      action-text="Reintentar"
      @action="rulesStore.loadRules"
    />

    <!-- Empty state -->
    <EmptyState
      v-else-if="rulesStore.rules.length === 0"
      title="Sin reglas recurrentes"
      message="Crea una regla para que tus transacciones se generen automáticamente"
      icon="🔁"
      action-text="Nueva regla"
      @action="createRule"
    />

    <!-- Rules list -->
    <div v-else class="space-y-6">
      <!-- Active -->
      <section v-if="activeRules.length > 0">
        <h2 class="text-xs font-semibold text-dark-text-secondary uppercase tracking-wide mb-2 px-1">
          Activas ({{ activeRules.length }})
        </h2>
        <div class="space-y-2">
          <div
            v-for="rule in activeRules"
            :key="rule.id"
            class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-dark-bg-tertiary/30 transition-colors"
            @click="goToDetail(rule.id)"
          >
            <!-- Type indicator -->
            <div
              class="w-2 h-2 rounded-full shrink-0"
              :class="rule.type === 'income' ? 'bg-green-400' : 'bg-red-400'"
            />

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <p class="font-medium truncate text-dark-text-primary">{{ rule.title }}</p>
              <p class="text-xs text-dark-text-secondary truncate">
                {{ frequencyLabel(rule) }} · {{ getAccountName(rule.account_id) }} · {{ getCategoryName(rule.category_id) }}
              </p>
            </div>

            <!-- Amount + confirmation badge -->
            <div class="text-right shrink-0">
              <p
                class="text-sm font-semibold"
                :class="rule.type === 'income' ? 'text-green-400' : 'text-red-400'"
              >
                {{ rule.type === 'income' ? '+' : '-' }}{{ formatAmount(rule.amount) }}
              </p>
              <p v-if="rule.requires_confirmation" class="text-xs text-yellow-400">confirmación</p>
            </div>

            <!-- Chevron -->
            <svg class="w-4 h-4 text-dark-text-tertiary shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </section>

      <!-- Paused -->
      <section v-if="pausedRules.length > 0">
        <h2 class="text-xs font-semibold text-dark-text-secondary uppercase tracking-wide mb-2 px-1">
          Pausadas ({{ pausedRules.length }})
        </h2>
        <div class="space-y-2">
          <div
            v-for="rule in pausedRules"
            :key="rule.id"
            class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-dark-bg-tertiary/30 transition-colors opacity-60"
            @click="goToDetail(rule.id)"
          >
            <div class="w-2 h-2 rounded-full bg-yellow-400 shrink-0" />
            <div class="flex-1 min-w-0">
              <p class="font-medium truncate text-dark-text-primary">{{ rule.title }}</p>
              <p class="text-xs text-dark-text-secondary truncate">
                {{ frequencyLabel(rule) }} · {{ getAccountName(rule.account_id) }}
              </p>
            </div>
            <div class="text-right shrink-0">
              <p class="text-sm font-semibold text-dark-text-secondary">
                {{ formatAmount(rule.amount) }}
              </p>
            </div>
            <svg class="w-4 h-4 text-dark-text-tertiary shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </section>

      <!-- Completed -->
      <section v-if="completedRules.length > 0">
        <h2 class="text-xs font-semibold text-dark-text-secondary uppercase tracking-wide mb-2 px-1">
          Completadas ({{ completedRules.length }})
        </h2>
        <div class="space-y-2">
          <div
            v-for="rule in completedRules"
            :key="rule.id"
            class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-dark-bg-tertiary/30 transition-colors opacity-40"
            @click="goToDetail(rule.id)"
          >
            <div class="w-2 h-2 rounded-full bg-gray-400 shrink-0" />
            <div class="flex-1 min-w-0">
              <p class="font-medium truncate text-dark-text-secondary">{{ rule.title }}</p>
              <p class="text-xs text-dark-text-secondary truncate">
                {{ frequencyLabel(rule) }} · {{ rule.occurrences_created }} ocurrencias
              </p>
            </div>
            <svg class="w-4 h-4 text-dark-text-tertiary shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </section>
    </div>

    <!-- FAB -->
    <SimpleFab ariaLabel="Crear nueva regla recurrente" @click="createRule" />
  </div>
</template>
