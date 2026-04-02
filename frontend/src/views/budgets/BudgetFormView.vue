<!-- frontend/src/views/budgets/BudgetFormView.vue -->
<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBudgetsStore } from '@/stores/budgets'
import { useAccountsStore } from '@/stores/accounts'
import { useSettingsStore } from '@/stores/settings'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import AccountSelect from '@/components/accounts/AccountSelect.vue'
import CategorySelect from '@/components/categories/CategorySelect.vue'
import AmountInput from '@/components/shared/AmountInput.vue'
import { CURRENCIES } from '@/utils/constants'
import type { CreateBudgetDto, UpdateBudgetDto, BudgetFrequency } from '@/types/budget'

const route = useRoute()
const router = useRouter()
const budgetsStore = useBudgetsStore()
const accountsStore = useAccountsStore()
const settingsStore = useSettingsStore()

const isEdit = computed(() => !!route.params.id)
const budgetId = computed(() => route.params.id as string)

const existing = computed(() =>
  isEdit.value ? budgetsStore.budgets.find(b => b.id === budgetId.value) : null
)

// Form state
const name = ref('')
const scopeType = ref<'account' | 'category'>('account')
const accountId = ref('')
const categoryId = ref('')
const amountLimit = ref(0)
const currency = ref(settingsStore.primaryCurrency)
// When an account is selected, default currency to that account's currency
watch(accountId, (id) => {
  if (id && scopeType.value === 'account') {
    const acc = accountsStore.accounts.find(a => a.id === id)
    if (acc) currency.value = acc.currency
  }
})

const budgetType = ref<'recurring' | 'one_time'>('recurring')
const frequency = ref<BudgetFrequency>('monthly')
const interval = ref(1)
const referenceDate = ref('')
const startDate = ref('')
const endDate = ref('')
const saving = ref(false)
const error = ref('')

onMounted(async () => {
  await budgetsStore.loadBudgets()
  if (existing.value) {
    const b = existing.value
    name.value = b.name
    scopeType.value = b.account_id ? 'account' : 'category'
    accountId.value = b.account_id ?? ''
    categoryId.value = b.category_id ?? ''
    amountLimit.value = b.amount_limit
    currency.value = b.currency
    budgetType.value = b.budget_type
    frequency.value = b.frequency ?? 'monthly'
    interval.value = b.interval ?? 1
    referenceDate.value = b.reference_date ?? ''
    startDate.value = b.start_date ?? ''
    endDate.value = b.end_date ?? ''
  }
})


async function submit() {
  error.value = ''
  if (!name.value.trim()) { error.value = 'El nombre es requerido'; return }
  if (!amountLimit.value || amountLimit.value <= 0) { error.value = 'El límite debe ser mayor a 0'; return }

  saving.value = true
  try {
    if (isEdit.value && existing.value) {
      const dto: UpdateBudgetDto = {
        name: name.value,
        amount_limit: amountLimit.value,
        currency: currency.value,
        frequency: budgetType.value === 'recurring' ? frequency.value : null,
        interval: budgetType.value === 'recurring' ? interval.value : undefined,
        reference_date: referenceDate.value || null,
        start_date: budgetType.value === 'one_time' ? startDate.value : null,
        end_date: budgetType.value === 'one_time' ? endDate.value : null,
      }
      await budgetsStore.updateBudget(budgetId.value, dto)
      router.push(`/budgets/${budgetId.value}`)
    } else {
      const dto: CreateBudgetDto = {
        name: name.value,
        account_id: scopeType.value === 'account' ? accountId.value : null,
        category_id: scopeType.value === 'category' ? categoryId.value : null,
        amount_limit: amountLimit.value,
        currency: currency.value,
        budget_type: budgetType.value,
        frequency: budgetType.value === 'recurring' ? frequency.value : null,
        interval: budgetType.value === 'recurring' ? interval.value : undefined,
        reference_date: referenceDate.value || null,
        start_date: budgetType.value === 'one_time' ? startDate.value : null,
        end_date: budgetType.value === 'one_time' ? endDate.value : null,
      }
      await budgetsStore.createBudget(dto)
      router.push('/budgets')
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error al guardar'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="flex flex-col min-h-screen bg-dark-bg pb-20">
    <div class="px-4 pt-6 pb-4">
      <h1 class="text-xl font-bold text-dark-text-primary">
        {{ isEdit ? 'Editar Presupuesto' : 'Nuevo Presupuesto' }}
      </h1>
    </div>

    <BaseCard class="mx-4 space-y-4">
      <!-- Name -->
      <BaseInput v-model="name" label="Nombre" placeholder="Ej. Comida del mes" required />

      <!-- Scope type (only on create) -->
      <div v-if="!isEdit">
        <label class="text-dark-text-secondary text-sm mb-1 block">Scope</label>
        <div class="flex gap-2">
          <button
            v-for="opt in [{ v: 'account', l: 'Cuenta' }, { v: 'category', l: 'Categoría' }]"
            :key="opt.v"
            :class="['flex-1 py-2 rounded-lg text-sm border transition-colors',
              scopeType === opt.v
                ? 'border-accent-blue text-accent-blue'
                : 'border-dark-border text-dark-text-secondary']"
            @click="scopeType = opt.v as 'account' | 'category'"
          >{{ opt.l }}</button>
        </div>
      </div>

      <!-- Account or category selector -->
      <AccountSelect
        v-if="scopeType === 'account' && !isEdit"
        v-model="accountId"
        :accounts="accountsStore.activeAccounts"
      />
      <CategorySelect
        v-if="scopeType === 'category' && !isEdit"
        v-model="categoryId"
        :filter-type="'expense' as any"
      />

      <!-- Amount + currency -->
      <AmountInput v-model="amountLimit" label="Límite" :currency="currency" required />
      <BaseSelect v-model="currency" label="Moneda" :options="CURRENCIES" />

      <!-- Budget type (only on create) -->
      <div v-if="!isEdit">
        <label class="text-dark-text-secondary text-sm mb-1 block">Tipo</label>
        <div class="flex gap-2">
          <button
            v-for="opt in [{ v: 'recurring', l: 'Recurrente' }, { v: 'one_time', l: 'Puntual' }]"
            :key="opt.v"
            :class="['flex-1 py-2 rounded-lg text-sm border transition-colors',
              budgetType === opt.v
                ? 'border-accent-blue text-accent-blue'
                : 'border-dark-border text-dark-text-secondary']"
            @click="budgetType = opt.v as 'recurring' | 'one_time'"
          >{{ opt.l }}</button>
        </div>
      </div>

      <!-- Recurring options -->
      <template v-if="budgetType === 'recurring'">
        <BaseSelect
          v-model="frequency"
          label="Frecuencia"
          :options="[
            { value: 'daily', label: 'Diario' },
            { value: 'weekly', label: 'Semanal' },
            { value: 'monthly', label: 'Mensual' },
            { value: 'yearly', label: 'Anual' },
          ]"
        />
        <BaseInput v-model.number="interval" label="Cada N períodos" type="number" />
        <BaseInput v-model="referenceDate" label="Fecha ancla (opcional)" type="date" />
      </template>

      <!-- One-time options -->
      <template v-if="budgetType === 'one_time'">
        <BaseInput v-model="startDate" label="Fecha inicio" type="date" />
        <BaseInput v-model="endDate" label="Fecha fin" type="date" />
      </template>

      <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

      <BaseButton variant="primary" class="w-full" :disabled="saving" @click="submit">
        {{ saving ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear presupuesto' }}
      </BaseButton>
    </BaseCard>
  </div>
</template>
