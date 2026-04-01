<script setup lang="ts">
/**
 * Transfer Form Component
 *
 * Form for creating/editing transfers between accounts.
 * Supports cross-currency transfers with a collapsible exchange-rate section.
 *
 * Cross-currency UX:
 *   When source and destination accounts have different currencies, a
 *   collapsible panel appears (auto-expanded) with three interdependent fields:
 *     - source_amount   (the main form amount — same ref, not duplicated)
 *     - destination_amount (new — how much the destination account receives)
 *     - exchange_rate   (pre-filled from the exchange-rates store cache)
 *
 *   Editing any two of the three recalculates the third:
 *     - source_amount change  → destination_amount = source_amount * exchange_rate
 *     - destination_amount change → exchange_rate = destination_amount / source_amount
 *     - exchange_rate change  → destination_amount = source_amount * exchange_rate
 *
 * Rate deviation alert (Phase 5.2):
 *   A non-blocking yellow warning appears when the user's exchange_rate
 *   deviates more than 10% from the cached suggested rate.
 */

import { reactive, ref, computed, watch } from 'vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import AmountInput from '@/components/shared/AmountInput.vue'
import DatePicker from '@/components/shared/DatePicker.vue'
import AccountSelect from '@/components/accounts/AccountSelect.vue'
import ExchangeRateInput from '@/components/shared/ExchangeRateInput.vue'
import { positiveNumber } from '@/utils/validators'
import { formatDateForInput } from '@/utils/formatters'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useCategoriesStore } from '@/stores/categories'
import type { Transfer, CreateTransferDto, UpdateTransferDto, Account, CreateTransactionDto } from '@/types'

interface Props {
  transfer?: Transfer
  accounts: Account[]
  loading?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  submit: [data: CreateTransferDto | UpdateTransferDto, feeData?: CreateTransactionDto]
  cancel: []
}>()

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const exchangeRatesStore = useExchangeRatesStore()
const categoriesStore = useCategoriesStore()

// ---------------------------------------------------------------------------
// Fee section state (create mode only)
// ---------------------------------------------------------------------------

const hasFee = ref(false)
const feeType = ref<'fixed' | 'percentage'>('fixed')
const feeAmount = ref<number>(0)
const feeCategoryId = ref<string>('')

const FEE_TYPE_OPTIONS = [
  { value: 'fixed', label: 'Fijo' },
  { value: 'percentage', label: 'Porcentaje (%)' },
]

const feeCategories = computed(() =>
  categoriesStore.categories.filter(c => c.type === 'expense' || c.type === 'both')
)

const computedFeeAmount = computed<number | null>(() => {
  if (!hasFee.value || feeType.value !== 'percentage') return null
  if (!form.amount || feeAmount.value <= 0) return null
  return parseFloat(((feeAmount.value / 100) * form.amount).toFixed(8))
})

const resolvedFeeAmount = computed<number>(() => {
  if (feeType.value === 'percentage') {
    return computedFeeAmount.value ?? 0
  }
  return feeAmount.value
})

// ---------------------------------------------------------------------------
// Form data
// ---------------------------------------------------------------------------

const form = reactive({
  source_account_id: props.transfer?.source_account_id || '',
  destination_account_id: props.transfer?.destination_account_id || '',
  amount: props.transfer?.amount || 0,
  date: props.transfer?.date || formatDateForInput(new Date()),
  title: props.transfer?.title || '',
  description: props.transfer?.description || '',
  tags: props.transfer?.tags?.join(', ') || ''
})

// Validation errors
const errors = reactive({
  source_account_id: '',
  destination_account_id: '',
  amount: '',
  date: '',
  fee_category_id: ''
})

// ---------------------------------------------------------------------------
// Cross-currency state
//
// Why separate refs instead of adding to `form` reactive object?
// The exchange section fields participate in a circular recalculation loop
// (source ↔ destination ↔ rate). Using individual refs lets each watcher
// be targeted and guarded with a single `isCalculating` flag, avoiding
// infinite loops. Adding them to the shared `form` reactive would require
// deep watchers that are harder to guard.
// ---------------------------------------------------------------------------

/** Raw string value for the destination amount input — preserves full precision */
const destinationAmountStr = ref<string>(
  props.transfer?.destination_amount
    ? parseFloat(Number(props.transfer.destination_amount).toFixed(10)).toString()
    : ''
)

/** Raw string value for the exchange rate input — preserves full precision */
const exchangeRateStr = ref<string>(
  props.transfer?.exchange_rate
    ? parseFloat(Number(props.transfer.exchange_rate).toFixed(10)).toString()
    : ''
)

/** Parsed numeric versions — used for calculations and form submission */
const destinationAmount = computed<number>(() => {
  const n = parseFloat(destinationAmountStr.value)
  return isNaN(n) ? 0 : n
})

const exchangeRate = computed<number>(() => {
  const n = parseFloat(exchangeRateStr.value)
  return isNaN(n) ? 0 : n
})

/** Controls visibility of the exchange-rate collapsible section.
 * Auto-open in edit mode when the transfer already has FX data. */
const isRateSectionOpen = ref(!!(props.transfer?.exchange_rate))

/** Guard flag to prevent circular watcher loops during recalculation */
let isCalculating = false

// ---------------------------------------------------------------------------
// Computed — account lookups
// ---------------------------------------------------------------------------

const isEditMode = computed(() => !!props.transfer)

const sourceAccount = computed<Account | undefined>(() =>
  props.accounts.find(a => a.id === form.source_account_id)
)

const destinationAccount = computed<Account | undefined>(() =>
  props.accounts.find(a => a.id === form.destination_account_id)
)

/** Currency of the source account — used by AmountInput for symbol display */
const originAccountCurrency = computed<string>(() =>
  sourceAccount.value?.currency || 'USD'
)

const destAccountCurrency = computed<string>(() =>
  destinationAccount.value?.currency || 'USD'
)

/**
 * True when both accounts are selected and their currencies differ.
 *
 * Why computed and not a method?
 * Vue's reactive system tracks this as a dependency automatically.
 * Any watcher that reads isCrossCurrency.value is re-run when either
 * account ID changes — zero manual wiring needed.
 */
const isCrossCurrency = computed<boolean>(() => {
  if (!form.source_account_id || !form.destination_account_id) return false
  const src = sourceAccount.value?.currency
  const dst = destinationAccount.value?.currency
  return !!src && !!dst && src !== dst
})

// ---------------------------------------------------------------------------
// Suggested rate from cache — used for deviation alert (Phase 5.2)
// ---------------------------------------------------------------------------

/**
 * The exchange rate cached in the store at the time the currency pair is
 * selected. Computed so it updates live if the store refreshes while the
 * form is open (rare but possible via background revalidation).
 */
const suggestedRate = computed<number | null>(() => {
  if (!isCrossCurrency.value) return null
  return exchangeRatesStore.getRate(
    originAccountCurrency.value,
    destAccountCurrency.value
  )
})

/**
 * Phase 5.2 — Rate deviation alert.
 *
 * Yellow warning when user's exchange_rate deviates >10% from the cached
 * suggested rate. Non-blocking: the user may still submit. The alert
 * disappears automatically when the rate comes back within range.
 */
const showRateAlert = computed<boolean>(() => {
  if (!suggestedRate.value || !exchangeRate.value || !isCrossCurrency.value) return false
  const deviation = Math.abs(exchangeRate.value - suggestedRate.value) / suggestedRate.value
  return deviation > 0.10
})

// ---------------------------------------------------------------------------
// Auto-expand / auto-collapse + rate pre-fill
//
// When isCrossCurrency becomes true: open the panel and pre-fill the rate.
// When it becomes false: close the panel and clear the cross-currency fields.
// ---------------------------------------------------------------------------

watch(isCrossCurrency, (newVal) => {
  if (newVal) {
    isRateSectionOpen.value = true
    // Pre-fill from cache only if the rate field is currently empty or zero.
    // This preserves a manually-typed rate if the user toggles accounts back
    // and forth between same/different currencies.
    if (!exchangeRate.value && suggestedRate.value !== null) {
      exchangeRateStr.value = parseFloat(suggestedRate.value.toFixed(10)).toString()
      // Immediately calculate destination amount with the pre-filled rate.
      if (form.amount > 0 && suggestedRate.value > 0) {
        const calc = form.amount * suggestedRate.value
        destinationAmountStr.value = parseFloat(calc.toFixed(10)).toString()
      }
    }
  } else {
    isRateSectionOpen.value = false
    destinationAmountStr.value = ''
    exchangeRateStr.value = ''
  }
})

// ---------------------------------------------------------------------------
// Bidirectional field recalculation
//
// Three watchers implement the "edit any two, calculate the third" logic.
// The `isCalculating` flag breaks circular loops: when watcher A triggers
// a value update that would fire watcher B, B detects the guard and exits
// early rather than triggering A again.
//
// Why watch the string values (not the computed numerics)?
// We need to react to user input events, not derived state. Watching the
// computed numerics would also trigger during programmatic updates we make
// inside the watchers themselves, making the guard harder to reason about.
// ---------------------------------------------------------------------------

/** When source amount changes → recalculate destination amount */
watch(() => form.amount, (newAmount) => {
  if (!isCrossCurrency.value || isCalculating) return
  if (exchangeRate.value > 0) {
    isCalculating = true
    const calc = newAmount * exchangeRate.value
    destinationAmountStr.value = parseFloat(calc.toFixed(10)).toString()
    isCalculating = false
  }
})

/** When destination amount changes → recalculate exchange rate */
watch(destinationAmountStr, () => {
  if (!isCrossCurrency.value || isCalculating) return
  if (form.amount > 0 && destinationAmount.value > 0) {
    isCalculating = true
    const calc = destinationAmount.value / form.amount
    exchangeRateStr.value = parseFloat(calc.toFixed(10)).toString()
    isCalculating = false
  }
})

/** When exchange rate changes → recalculate destination amount */
watch(exchangeRateStr, () => {
  if (!isCrossCurrency.value || isCalculating) return
  if (form.amount > 0 && exchangeRate.value > 0) {
    isCalculating = true
    const calc = form.amount * exchangeRate.value
    destinationAmountStr.value = parseFloat(calc.toFixed(10)).toString()
    isCalculating = false
  }
})

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

function validateForm(): boolean {
  let isValid = true

  if (!form.source_account_id) {
    errors.source_account_id = 'Debes seleccionar una cuenta de origen'
    isValid = false
  } else {
    errors.source_account_id = ''
  }

  if (!form.destination_account_id) {
    errors.destination_account_id = 'Debes seleccionar una cuenta de destino'
    isValid = false
  } else if (form.destination_account_id === form.source_account_id) {
    errors.destination_account_id = 'La cuenta de destino debe ser diferente al origen'
    isValid = false
  } else {
    errors.destination_account_id = ''
  }

  const amountValidation = positiveNumber(form.amount)
  if (amountValidation !== true) {
    errors.amount = amountValidation as string
    isValid = false
  } else {
    errors.amount = ''
  }

  if (!form.date) {
    errors.date = 'Debes seleccionar una fecha'
    isValid = false
  } else {
    errors.date = ''
  }

  if (hasFee.value && !isEditMode.value && !feeCategoryId.value) {
    errors.fee_category_id = 'Selecciona una categoría para el fee'
    isValid = false
  } else {
    errors.fee_category_id = ''
  }

  return isValid
}

// ---------------------------------------------------------------------------
// Submission
// ---------------------------------------------------------------------------

function handleSubmit() {
  if (!validateForm()) return

  const data: CreateTransferDto | UpdateTransferDto = {
    source_account_id: form.source_account_id,
    destination_account_id: form.destination_account_id,
    amount: form.amount,
    date: form.date,
    title: form.title.trim() || undefined,
    description: form.description.trim() || undefined,
    tags: form.tags
      ? form.tags.split(',').map(t => t.trim()).filter(t => t.length > 0)
      : [],
    // Cross-currency fields — only included when currencies differ.
    // undefined is omitted by JSON.stringify, so same-currency payloads
    // stay clean without extra branching in the store.
    destination_amount: isCrossCurrency.value ? destinationAmount.value || undefined : undefined,
    exchange_rate: isCrossCurrency.value ? exchangeRate.value || undefined : undefined,
    destination_currency: isCrossCurrency.value ? destAccountCurrency.value : undefined
  }

  let feeData: CreateTransactionDto | undefined
  if (hasFee.value && !isEditMode.value && resolvedFeeAmount.value > 0 && feeCategoryId.value) {
    feeData = {
      type: 'expense' as any,
      amount: resolvedFeeAmount.value,
      date: form.date,
      account_id: form.source_account_id,
      category_id: feeCategoryId.value,
      title: 'Fee',
      tags: [],
      // fee_for_transfer_id will be set by TransferCreateView after it knows the transfer ID
    }
  }

  emit('submit', data, feeData)
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-4">
    <!-- Cuenta origen -->
    <AccountSelect
      v-model="form.source_account_id"
      :accounts="accounts"
      label="Cuenta de origen"
      placeholder="Selecciona cuenta origen"
      :error="errors.source_account_id"
      required
    />

    <!-- Cuenta destino -->
    <AccountSelect
      v-model="form.destination_account_id"
      :accounts="accounts"
      label="Cuenta de destino"
      placeholder="Selecciona cuenta destino"
      :filter-out-account-id="form.source_account_id"
      :error="errors.destination_account_id"
      required
    />

    <!-- Monto (source amount) -->
    <AmountInput
      v-model="form.amount"
      label="Monto"
      :currency="originAccountCurrency"
      placeholder="0.00"
      :error="errors.amount"
      required
    />

    <!-- ===================================================================
         Collapsible cross-currency exchange-rate section
         Appears only when source and destination accounts have different
         currencies. Collapsed by default; auto-expands when currencies differ.
         =================================================================== -->
    <div v-if="isCrossCurrency" class="rounded-lg border border-slate-700 overflow-hidden">
      <!-- Section header / toggle -->
      <button
        type="button"
        class="w-full flex items-center justify-between px-4 py-3 bg-slate-800 text-left hover:bg-slate-700 transition-colors duration-200"
        :aria-expanded="isRateSectionOpen"
        aria-controls="exchange-rate-panel"
        @click="isRateSectionOpen = !isRateSectionOpen"
      >
        <span class="text-sm font-medium text-slate-200">
          Tipo de cambio
          <span class="ml-2 text-xs text-slate-400 font-normal">
            {{ originAccountCurrency }} → {{ destAccountCurrency }}
          </span>
        </span>
        <!-- Chevron icon — rotates 180° when open -->
        <svg
          :class="[
            'w-4 h-4 text-slate-400 transition-transform duration-200',
            isRateSectionOpen ? 'rotate-180' : 'rotate-0'
          ]"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <!-- Collapsible body -->
      <div
        v-show="isRateSectionOpen"
        id="exchange-rate-panel"
        class="px-4 py-4 space-y-4 bg-slate-900"
      >
        <!--
          Destination amount field.

          Why plain <input> instead of AmountInput?
          AmountInput formats to exactly 2 decimal places on blur.
          Exchange amounts may need more precision (e.g. COP/BTC pairs).
          The spec explicitly says "full decimal precision only in this section."
          We use inputmode="decimal" for the correct mobile keyboard.
        -->
        <div class="w-full">
          <label class="label">
            Monto recibido
            <span class="text-xs text-slate-400 font-normal ml-1">({{ destAccountCurrency }})</span>
          </label>
          <div class="relative">
            <input
              v-model="destinationAmountStr"
              type="text"
              inputmode="decimal"
              placeholder="0"
              class="input"
              autocomplete="off"
            />
          </div>
        </div>

        <!-- Exchange rate (bidirectional) -->
        <ExchangeRateInput
          :model-value="exchangeRate"
          :base-currency="originAccountCurrency"
          :quote-currency="destAccountCurrency"
          @update:model-value="exchangeRateStr = String($event)"
        />

        <!-- Phase 5.2 — Rate deviation alert -->
        <div
          v-if="showRateAlert"
          class="flex items-center gap-1 text-xs text-yellow-500 dark:text-yellow-400 mt-1"
        >
          <span>⚠️</span>
          <span>La tasa ingresada difiere más del 10% de la tasa de mercado sugerida</span>
        </div>
      </div>
    </div>

    <!-- Fecha -->
    <DatePicker
      v-model="form.date"
      label="Fecha"
      :error="errors.date"
      :max="formatDateForInput(new Date())"
      required
    />

    <!-- Título -->
    <BaseInput
      v-model="form.title"
      label="Título (opcional)"
      placeholder="Ej: Transferencia a ahorros"
    />

    <!-- Descripción -->
    <BaseInput
      v-model="form.description"
      label="Descripción (opcional)"
      placeholder="Detalles adicionales"
    />

    <!-- Tags -->
    <BaseInput
      v-model="form.tags"
      label="Etiquetas (opcional)"
      placeholder="ahorro, mensual (separadas por comas)"
      helper-text="Separadas por comas"
    />

    <!-- Fee toggle (create mode only) -->
    <div v-if="!isEditMode" class="rounded-lg border border-dark-border bg-dark-bg-secondary overflow-hidden">
      <label
        class="flex items-center gap-3 px-4 py-3 cursor-pointer min-h-touch hover:bg-dark-bg-tertiary transition-colors select-none"
      >
        <input
          v-model="hasFee"
          type="checkbox"
          class="w-5 h-5 rounded accent-accent cursor-pointer"
        />
        <div>
          <span class="text-sm font-medium text-dark-text-primary">Agregar fee</span>
          <p class="text-xs text-dark-text-secondary">Registrar comisión o cargo asociado a esta transferencia</p>
        </div>
      </label>

      <Transition name="fee-expand">
        <div
          v-if="hasFee"
          class="px-4 pb-4 space-y-3 border-t border-dark-border pt-4"
        >
          <!-- Tipo -->
          <div>
            <label class="block text-sm font-medium text-dark-text-secondary mb-1">Tipo de fee</label>
            <select
              v-model="feeType"
              class="w-full bg-dark-bg-tertiary border border-dark-border rounded-lg px-3 py-2 text-dark-text-primary text-sm focus:outline-none focus:border-accent"
              style="min-height: 44px;"
            >
              <option v-for="opt in FEE_TYPE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>

          <!-- Monto -->
          <div>
            <label class="block text-sm font-medium text-dark-text-secondary mb-1">Monto del fee</label>
            <input
              v-model.number="feeAmount"
              type="number"
              min="0"
              step="any"
              placeholder="0.00"
              inputmode="decimal"
              class="w-full bg-dark-bg-tertiary border border-dark-border rounded-lg px-3 py-2 text-dark-text-primary text-sm focus:outline-none focus:border-accent"
              style="min-height: 44px;"
            />
            <p v-if="feeType === 'percentage' && computedFeeAmount !== null" class="mt-1 text-xs text-dark-text-tertiary">
              = {{ originAccountCurrency }} {{ computedFeeAmount.toFixed(2) }}
            </p>
          </div>

          <!-- Categoría -->
          <div>
            <label class="block text-sm font-medium text-dark-text-secondary mb-1">Categoría del fee</label>
            <select
              v-model="feeCategoryId"
              :class="[
                'w-full bg-dark-bg-tertiary border rounded-lg px-3 py-2 text-dark-text-primary text-sm focus:outline-none focus:border-accent',
                errors.fee_category_id ? 'border-error' : 'border-dark-border'
              ]"
              style="min-height: 44px;"
            >
              <option value="">Selecciona categoría</option>
              <option v-for="cat in feeCategories" :key="cat.id" :value="cat.id">
                {{ cat.icon }} {{ cat.name }}
              </option>
            </select>
            <p v-if="errors.fee_category_id" class="mt-1 text-xs text-error">{{ errors.fee_category_id }}</p>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Actions -->
    <div class="flex gap-3 pt-4 flex-col md:flex-row">
      <BaseButton
        type="submit"
        variant="primary"
        :loading="loading"
        full-width
      >
        {{ isEditMode ? 'Actualizar' : 'Crear' }} transferencia
      </BaseButton>
      <BaseButton
        type="button"
        variant="ghost"
        :disabled="loading"
        full-width
        @click="emit('cancel')"
      >
        Cancelar
      </BaseButton>
    </div>
  </form>
</template>

<style scoped>
/* Fee section expand — accordion animation. */
.fee-expand-enter-active,
.fee-expand-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
  max-height: 400px;
}

.fee-expand-enter-from,
.fee-expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
