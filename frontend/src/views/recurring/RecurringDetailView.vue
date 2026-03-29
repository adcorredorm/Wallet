<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRecurringRulesStore } from '@/stores/recurringRules'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { useUiStore } from '@/stores'
import { usePendingOccurrences } from '@/composables/usePendingOccurrences'
import { db } from '@/offline'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import type { LocalTransaction, LocalPendingOccurrence } from '@/offline/types'

const route = useRoute()
const router = useRouter()
const rulesStore = useRecurringRulesStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()
const pendingHelper = usePendingOccurrences()

const ruleId = route.params.id as string

const loading = ref(true)
const toggling = ref(false)
const showDeleteDialog = ref(false)
const deleting = ref(false)
const historyTransactions = ref<LocalTransaction[]>([])

const rule = computed(() => rulesStore.rules.find(r => r.id === ruleId))

const accountName = computed(() => {
  if (!rule.value) return '—'
  return accountsStore.accounts.find(a => a.id === rule.value!.account_id)?.name ?? '—'
})

const categoryName = computed(() => {
  if (!rule.value) return '—'
  return categoriesStore.categories.find(c => c.id === rule.value!.category_id)?.name ?? '—'
})

const FREQUENCY_LABELS: Record<string, string> = {
  daily: 'Diario',
  weekly: 'Semanal',
  monthly: 'Mensual',
  yearly: 'Anual',
}

const frequencyLabel = computed(() => {
  if (!rule.value) return ''
  const base = FREQUENCY_LABELS[rule.value.frequency] ?? rule.value.frequency
  return rule.value.interval > 1
    ? `Cada ${rule.value.interval} ${base.toLowerCase()}s`
    : base
})

const statusLabel = computed(() => {
  if (!rule.value) return ''
  return { active: 'Activa', paused: 'Pausada', completed: 'Completada' }[rule.value.status] ?? rule.value.status
})

const statusClass = computed(() => {
  if (!rule.value) return ''
  return {
    active: 'text-green-400 bg-green-400/10',
    paused: 'text-yellow-400 bg-yellow-400/10',
    completed: 'text-gray-400 bg-gray-400/10',
  }[rule.value.status] ?? ''
})

// Combined history: transactions + non-pending occurrences sorted by date
type HistoryEntry =
  | { kind: 'transaction'; date: string; item: LocalTransaction }
  | { kind: 'occurrence'; date: string; item: LocalPendingOccurrence }

const historyEntries = computed((): HistoryEntry[] => {
  const txEntries: HistoryEntry[] = historyTransactions.value.map(tx => ({
    kind: 'transaction' as const,
    date: tx.date,
    item: tx,
  }))

  const occEntries: HistoryEntry[] = pendingHelper.occurrences.value
    .filter(o => o.recurring_rule_id === ruleId && o.status !== 'pending')
    .map(o => ({
      kind: 'occurrence' as const,
      date: o.due_date,
      item: o,
    }))

  return [...txEntries, ...occEntries].sort((a, b) => b.date.localeCompare(a.date))
})

function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-')
  return `${d}/${m}/${y}`
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount)
}

/** Advance a YYYY-MM-DD date by one recurrence cycle. */
function advanceDate(dateStr: string, r: NonNullable<typeof rule.value>): string {
  const date = new Date(dateStr + 'T00:00:00')
  switch (r.frequency) {
    case 'daily':
      date.setDate(date.getDate() + r.interval)
      break
    case 'weekly':
      date.setDate(date.getDate() + 7 * r.interval)
      break
    case 'monthly': {
      const targetDay = r.day_of_month ?? date.getDate()
      date.setMonth(date.getMonth() + r.interval, 1)
      const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
      date.setDate(Math.min(targetDay, lastDay))
      break
    }
    case 'yearly': {
      const targetDay = r.day_of_month ?? date.getDate()
      date.setFullYear(date.getFullYear() + r.interval, date.getMonth(), 1)
      const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
      date.setDate(Math.min(targetDay, lastDay))
      break
    }
  }
  return date.toISOString().slice(0, 10)
}

async function togglePauseResume() {
  if (!rule.value) return
  toggling.value = true
  try {
    const newStatus = rule.value.status === 'active' ? 'paused' : 'active'
    const updatePayload: Record<string, unknown> = { status: newStatus }

    if (newStatus === 'active') {
      // Resume: advance next_occurrence_date past today so the engine
      // does not generate missed cycles from the pause period.
      const today = new Date().toISOString().slice(0, 10)
      let nextDate = rule.value.next_occurrence_date
      while (nextDate <= today) {
        nextDate = advanceDate(nextDate, rule.value)
      }
      updatePayload.next_occurrence_date = nextDate
    }

    await rulesStore.updateRule(ruleId, updatePayload as any)
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al cambiar estado')
  } finally {
    toggling.value = false
  }
}

async function confirmDelete() {
  deleting.value = true
  try {
    await rulesStore.deleteRule(ruleId)
    router.push('/recurring')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al eliminar regla')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}

function editRule() {
  router.push(`/recurring/${ruleId}/edit`)
}

onMounted(async () => {
  try {
    await Promise.all([
      rulesStore.loadRules(),
      accountsStore.fetchAccounts(),
      categoriesStore.fetchCategories(),
      pendingHelper.loadOccurrences(),
    ])
    historyTransactions.value = await db.transactions
      .filter(tx => tx.recurring_rule_id === ruleId)
      .toArray()
    historyTransactions.value.sort((a, b) => b.date.localeCompare(a.date))
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al cargar detalle')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <BaseSpinner v-if="loading" centered />

    <!-- Not found -->
    <div v-else-if="!rule" class="text-center py-12 text-dark-text-secondary">
      Regla no encontrada
    </div>

    <template v-else>
      <!-- Rule info card -->
      <div class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 p-4 space-y-4">
        <!-- Title + status -->
        <div class="flex items-start justify-between gap-2">
          <h1 class="text-xl font-bold text-dark-text-primary">{{ rule.title }}</h1>
          <span
            class="text-xs font-medium px-2 py-1 rounded-full shrink-0"
            :class="statusClass"
          >
            {{ statusLabel }}
          </span>
        </div>

        <!-- Fields grid -->
        <dl class="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Tipo</dt>
            <dd class="font-medium" :class="rule.type === 'income' ? 'text-green-400' : 'text-red-400'">
              {{ rule.type === 'income' ? 'Ingreso' : 'Gasto' }}
            </dd>
          </div>
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Monto</dt>
            <dd class="font-semibold text-dark-text-primary">{{ formatAmount(rule.amount) }}</dd>
          </div>
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Cuenta</dt>
            <dd class="text-dark-text-primary truncate">{{ accountName }}</dd>
          </div>
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Categoría</dt>
            <dd class="text-dark-text-primary truncate">{{ categoryName }}</dd>
          </div>
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Frecuencia</dt>
            <dd class="text-dark-text-primary">{{ frequencyLabel }}</dd>
          </div>
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Próxima</dt>
            <dd class="text-dark-text-primary">{{ formatDate(rule.next_occurrence_date) }}</dd>
          </div>
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Inicio</dt>
            <dd class="text-dark-text-primary">{{ formatDate(rule.start_date) }}</dd>
          </div>
          <div v-if="rule.end_date">
            <dt class="text-dark-text-secondary text-xs mb-0.5">Fin</dt>
            <dd class="text-dark-text-primary">{{ formatDate(rule.end_date) }}</dd>
          </div>
          <div v-if="rule.max_occurrences">
            <dt class="text-dark-text-secondary text-xs mb-0.5">Max. ocurrencias</dt>
            <dd class="text-dark-text-primary">{{ rule.occurrences_created }} / {{ rule.max_occurrences }}</dd>
          </div>
          <div>
            <dt class="text-dark-text-secondary text-xs mb-0.5">Confirmación</dt>
            <dd class="text-dark-text-primary">{{ rule.requires_confirmation ? 'Manual' : 'Automática' }}</dd>
          </div>
        </dl>
      </div>

      <!-- Actions -->
      <div class="flex flex-col gap-2">
        <BaseButton variant="secondary" full-width @click="editRule">
          Editar regla
        </BaseButton>

        <BaseButton
          v-if="rule.status !== 'completed'"
          :variant="rule.status === 'active' ? 'ghost' : 'secondary'"
          full-width
          :loading="toggling"
          @click="togglePauseResume"
        >
          {{ rule.status === 'active' ? 'Pausar' : 'Reanudar' }}
        </BaseButton>

        <BaseButton
          variant="danger"
          full-width
          @click="showDeleteDialog = true"
        >
          Eliminar regla
        </BaseButton>
      </div>

      <!-- History -->
      <section>
        <h2 class="text-sm font-semibold text-dark-text-secondary uppercase tracking-wide mb-3 px-1">
          Historial ({{ historyEntries.length }})
        </h2>

        <div v-if="historyEntries.length === 0" class="text-sm text-dark-text-secondary text-center py-6">
          Aún no hay ocurrencias registradas
        </div>

        <ul v-else class="space-y-2">
          <li
            v-for="entry in historyEntries"
            :key="entry.kind + (entry.kind === 'transaction' ? entry.item.id : entry.item.id)"
            class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 px-4 py-3 flex items-center gap-3"
          >
            <!-- Status icon -->
            <template v-if="entry.kind === 'transaction'">
              <!-- Checkmark — confirmed/registered -->
              <svg class="w-5 h-5 text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </template>
            <template v-else-if="entry.item.status === 'expired'">
              <!-- X — expired -->
              <svg class="w-5 h-5 text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </template>
            <template v-else>
              <!-- Circle — discarded -->
              <svg class="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" stroke-width="2" />
              </svg>
            </template>

            <!-- Date + description -->
            <div class="flex-1 min-w-0">
              <p class="text-sm text-dark-text-primary">{{ formatDate(entry.date) }}</p>
              <p class="text-xs text-dark-text-secondary">
                <template v-if="entry.kind === 'transaction'">
                  {{ formatAmount((entry.item as LocalTransaction).amount) }} — registrada
                </template>
                <template v-else>
                  {{ formatAmount((entry.item as LocalPendingOccurrence).suggested_amount) }} —
                  {{ entry.item.status === 'expired' ? 'expirada' : 'descartada' }}
                </template>
              </p>
            </div>
          </li>
        </ul>
      </section>
    </template>

    <!-- Delete confirm dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Eliminar regla recurrente"
      message="¿Estás seguro de que deseas eliminar esta regla? Las transacciones ya generadas no se eliminarán."
      confirm-text="Eliminar"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>
</template>
