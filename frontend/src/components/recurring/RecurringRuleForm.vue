<script setup lang="ts">
/**
 * RecurringRuleForm — form for creating and editing recurring rules.
 * Used by RecurringCreateView and RecurringEditView.
 */

import { reactive, ref, computed } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AmountInput from '@/components/shared/AmountInput.vue'
import DatePicker from '@/components/shared/DatePicker.vue'
import AccountSelect from '@/components/accounts/AccountSelect.vue'
import CategorySelect from '@/components/categories/CategorySelect.vue'
import { formatDateForInput } from '@/utils/formatters'
import type { Account, Category } from '@/types'
import type { CategoryType } from '@/types'
import type { RecurringRule, CreateRecurringRuleDto, UpdateRecurringRuleDto, RecurringFrequency } from '@/types/recurring-rule'

interface Props {
  rule?: RecurringRule
  accounts: Account[]
  categories: Category[]
  loading?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  submit: [data: CreateRecurringRuleDto | UpdateRecurringRuleDto]
  cancel: []
}>()

const isEditMode = computed(() => !!props.rule)

const form = reactive({
  title: props.rule?.title ?? '',
  type: props.rule?.type ?? 'expense' as 'income' | 'expense',
  amount: props.rule?.amount ?? 0,
  account_id: props.rule?.account_id ?? '',
  category_id: props.rule?.category_id ?? '',
  description: props.rule?.description ?? '',
  frequency: props.rule?.frequency ?? 'monthly' as RecurringFrequency,
  interval: props.rule?.interval ?? 1,
  day_of_month: props.rule?.day_of_month ?? null as number | null,
  start_date: props.rule?.start_date ?? formatDateForInput(new Date()),
  requires_confirmation: props.rule?.requires_confirmation ?? false,
})

const durationType = ref<'indefinite' | 'until_date' | 'n_occurrences'>(
  props.rule?.max_occurrences ? 'n_occurrences'
  : props.rule?.end_date ? 'until_date'
  : 'indefinite'
)
const endDate = ref(props.rule?.end_date ?? '')
const maxOccurrences = ref<number | null>(props.rule?.max_occurrences ?? null)

const TRANSACTION_TYPE_OPTIONS = [
  { value: 'expense', label: 'Gasto' },
  { value: 'income', label: 'Ingreso' },
]

const FREQUENCY_OPTIONS = [
  { value: 'daily', label: 'Diario' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'monthly', label: 'Mensual' },
  { value: 'yearly', label: 'Anual' },
]

const errors = reactive({
  amount: '',
  account_id: '',
  category_id: '',
  start_date: '',
})

function validate(): boolean {
  let valid = true
  errors.amount = form.amount <= 0 ? 'El monto debe ser mayor a 0' : ''
  errors.account_id = !form.account_id ? 'Selecciona una cuenta' : ''
  errors.category_id = !form.category_id ? 'Selecciona una categoría' : ''
  errors.start_date = !form.start_date ? 'Selecciona una fecha de inicio' : ''
  if (errors.amount || errors.account_id || errors.category_id || errors.start_date) valid = false
  return valid
}

function handleSubmit() {
  if (!validate()) return

  const data: CreateRecurringRuleDto | UpdateRecurringRuleDto = {
    title: form.title.trim() || `${form.type === 'income' ? 'Ingreso' : 'Gasto'} recurrente`,
    type: form.type,
    amount: form.amount,
    account_id: form.account_id,
    category_id: form.category_id,
    description: form.description.trim() || null,
    frequency: form.frequency,
    interval: form.interval,
    day_of_month: form.frequency === 'monthly'
      ? (form.day_of_month ?? null)
      : null,
    start_date: form.start_date,
    next_occurrence_date: form.start_date,
    end_date: durationType.value === 'until_date' ? endDate.value : null,
    max_occurrences: durationType.value === 'n_occurrences' ? maxOccurrences.value : null,
    requires_confirmation: form.requires_confirmation,
  }

  emit('submit', data)
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <!-- Tipo -->
    <BaseSelect
      v-model="form.type"
      label="Tipo"
      :options="TRANSACTION_TYPE_OPTIONS"
    />

    <!-- Título -->
    <BaseInput
      v-model="form.title"
      label="Título (opcional)"
      placeholder="Ej: Suscripción Netflix"
    />

    <!-- Monto -->
    <AmountInput
      v-model="form.amount"
      label="Monto"
      currency="—"
      placeholder="0.00"
      :error="errors.amount"
      required
    />

    <!-- Cuenta -->
    <AccountSelect
      v-model="form.account_id"
      :accounts="accounts"
      :error="errors.account_id"
      required
    />

    <!-- Categoría -->
    <CategorySelect
      v-model="form.category_id"
      :categories="categories"
      :filter-type="(form.type as unknown as CategoryType)"
      :error="errors.category_id"
      required
    />

    <!-- Descripción -->
    <BaseInput
      v-model="form.description"
      label="Descripción (opcional)"
      placeholder="Notas adicionales"
    />

    <!-- Frecuencia -->
    <BaseSelect
      v-model="form.frequency"
      label="Frecuencia"
      :options="FREQUENCY_OPTIONS"
    />

    <!-- Intervalo -->
    <div>
      <label class="block text-sm font-medium text-dark-text-secondary mb-1">
        Cada cuántos periodos
      </label>
      <input
        v-model.number="form.interval"
        type="number"
        min="1"
        max="365"
        class="w-full bg-dark-bg-tertiary border border-dark-border rounded-lg px-3 py-2 text-dark-text-primary text-sm focus:outline-none focus:border-accent"
        style="min-height: 44px;"
      />
    </div>

    <!-- Día del mes (mensual) -->
    <div v-if="form.frequency === 'monthly'">
      <label class="block text-sm font-medium text-dark-text-secondary mb-1">
        Día del mes (opcional)
      </label>
      <input
        v-model.number="form.day_of_month"
        type="number"
        min="1"
        max="31"
        placeholder="Día de inicio por defecto"
        class="w-full bg-dark-bg-tertiary border border-dark-border rounded-lg px-3 py-2 text-dark-text-primary text-sm focus:outline-none focus:border-accent placeholder:text-dark-text-tertiary"
        style="min-height: 44px;"
      />
    </div>

    <!-- Fecha de inicio -->
    <DatePicker
      v-model="form.start_date"
      label="Fecha de inicio"
      :error="errors.start_date"
      required
    />

    <!-- Duración -->
    <div class="rounded-lg border border-dark-border bg-dark-bg-secondary p-4 space-y-3">
      <span class="block text-sm font-medium text-dark-text-secondary">Duración</span>
      <div class="space-y-2">
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="durationType" type="radio" value="indefinite" class="accent-accent" />
          <span class="text-sm text-dark-text-primary">Indefinida</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="durationType" type="radio" value="until_date" class="accent-accent" />
          <span class="text-sm text-dark-text-primary">Hasta una fecha</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="durationType" type="radio" value="n_occurrences" class="accent-accent" />
          <span class="text-sm text-dark-text-primary">Número de repeticiones</span>
        </label>
      </div>

      <DatePicker
        v-if="durationType === 'until_date'"
        v-model="endDate"
        label="Fecha de fin"
      />

      <div v-if="durationType === 'n_occurrences'">
        <label class="block text-sm font-medium text-dark-text-secondary mb-1">
          Número de repeticiones
        </label>
        <input
          v-model.number="maxOccurrences"
          type="number"
          min="1"
          max="9999"
          placeholder="Ej: 12"
          class="w-full bg-dark-bg-tertiary border border-dark-border rounded-lg px-3 py-2 text-dark-text-primary text-sm focus:outline-none focus:border-accent placeholder:text-dark-text-tertiary"
          style="min-height: 44px;"
        />
      </div>
    </div>

    <!-- Requiere confirmación -->
    <label class="flex items-start gap-3 cursor-pointer rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 p-4">
      <input
        v-model="form.requires_confirmation"
        type="checkbox"
        class="w-5 h-5 rounded accent-accent cursor-pointer mt-0.5 shrink-0"
      />
      <div>
        <span class="text-sm font-medium text-dark-text-primary">Requiere confirmación</span>
        <p class="text-xs text-dark-text-secondary mt-0.5">
          Cada ciclo creará una transacción pendiente que deberás aprobar manualmente.
        </p>
      </div>
    </label>

    <!-- Actions -->
    <div class="flex flex-col gap-2 pt-2">
      <BaseButton type="submit" variant="primary" full-width :loading="loading">
        {{ isEditMode ? 'Guardar cambios' : 'Crear regla' }}
      </BaseButton>
      <BaseButton type="button" variant="ghost" full-width :disabled="loading" @click="emit('cancel')">
        Cancelar
      </BaseButton>
    </div>
  </form>
</template>
