/**
 * TransactionForm.exchange-rate-input.spec.ts
 *
 * RED tests: verifies that TransactionForm uses ExchangeRateInput for the
 * exchange rate field inside the FX section instead of a plain <input type="number">.
 *
 * Scope:
 *   1. When fxActive is true, ExchangeRateInput is rendered for the rate field
 *   2. No input[type="number"] exists anywhere after integration (0 count)
 *   3. handleRateInput function is NOT exposed on the component instance
 *      (it was removed because ExchangeRateInput emits update:modelValue directly)
 *
 * Why these tests complement TransactionForm.fx-amount-input.spec.ts?
 * The existing spec checked that originalAmount and accountAmount use AmountInput
 * and that exactly 1 input[type="number"] remains (the exchange rate field).
 * This spec focuses on the second phase: removing that last input[type="number"]
 * by replacing it with ExchangeRateInput.
 *
 * Mock strategy:
 * - Mirrors TransactionForm.fx-amount-input.spec.ts exactly so both test files
 *   are consistent and can be understood as a pair.
 * - ExchangeRateInput is NOT stubbed — rendered real so we can verify its presence.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import type { Account, Category } from '@/types'
import { CategoryType } from '@/types'

// ---------------------------------------------------------------------------
// Mocks — must be declared BEFORE component imports
// ---------------------------------------------------------------------------

vi.mock('@/utils/constants', () => ({
  TRANSACTION_TYPES: [
    { value: 'expense', label: 'Gasto' },
    { value: 'income', label: 'Ingreso' },
  ],
  CURRENCIES: [
    { value: 'USD', label: 'USD' },
    { value: 'EUR', label: 'EUR' },
    { value: 'COP', label: 'COP' },
  ],
  SUPPORTED_CURRENCIES: [
    { code: 'USD', symbol: '$' },
    { code: 'EUR', symbol: '€' },
    { code: 'COP', symbol: '$' },
  ],
}))

vi.mock('@/utils/validators', () => ({
  required: (v: unknown) => (v ? true : 'Required'),
  positiveNumber: (v: number) => (v > 0 ? true : 'Must be positive'),
}))

vi.mock('@/utils/formatters', () => ({
  formatDateForInput: () => '2026-03-25',
  formatNumber: (v: number) => String(v),
  parseFormattedNumber: (v: string) => parseFloat(v.replace(',', '.')) || 0,
}))

vi.mock('@/stores/exchangeRates', () => ({
  useExchangeRatesStore: () => ({
    getRate: (_from: string, _to: string) => 4200,
  }),
}))

// ---------------------------------------------------------------------------
// Stub heavy child components — keep ExchangeRateInput real
// ---------------------------------------------------------------------------

vi.mock('@/components/ui/BaseInput.vue', () => ({
  default: { template: '<input />' },
}))
vi.mock('@/components/ui/BaseSelect.vue', () => ({
  default: {
    props: ['modelValue', 'options'],
    emits: ['update:modelValue'],
    template: '<select @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option></select>',
  },
}))
vi.mock('@/components/ui/BaseButton.vue', () => ({
  default: { template: '<button><slot /></button>' },
}))
vi.mock('@/components/shared/DatePicker.vue', () => ({
  default: { template: '<input type="date" />' },
}))
vi.mock('@/components/accounts/AccountSelect.vue', () => ({
  default: {
    props: ['modelValue', 'accounts'],
    emits: ['update:modelValue'],
    template: '<select />',
  },
}))
vi.mock('@/components/categories/CategorySelect.vue', () => ({
  default: {
    props: ['modelValue', 'categories'],
    emits: ['update:modelValue'],
    template: '<select />',
  },
}))
vi.mock('@/components/shared/AmountInput.vue', () => ({
  default: {
    props: ['modelValue', 'currency', 'label', 'placeholder', 'error', 'required'],
    emits: ['update:modelValue'],
    template: '<input type="text" inputmode="decimal" />',
  },
}))

// ---------------------------------------------------------------------------
// Import component AFTER mocks
// ---------------------------------------------------------------------------
import TransactionForm from '../TransactionForm.vue'
import ExchangeRateInput from '@/components/shared/ExchangeRateInput.vue'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TEST_ACCOUNT: Account = {
  id: 'acc-1',
  name: 'Test Account',
  type: 'checking' as any,
  currency: 'COP',
  tags: [],
  active: true,
  sort_order: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const TEST_CATEGORY: Category = {
  id: 'cat-1',
  name: 'Food',
  type: CategoryType.EXPENSE,
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

/** Mounts TransactionForm with FX active (foreignCurrency = 'USD', account currency = 'COP') */
function buildWrapper() {
  return mount(TransactionForm, {
    props: {
      accounts: [TEST_ACCOUNT],
      categories: [TEST_CATEGORY],
      loading: false,
      transaction: {
        id: 'tx-1',
        type: 'expense',
        amount: 42000,
        date: '2026-03-25',
        account_id: 'acc-1',
        category_id: 'cat-1',
        title: '',
        description: '',
        tags: [],
        original_currency: 'USD',
        original_amount: 10,
        exchange_rate: 4200,
      } as any,
    },
    global: {
      plugins: [createPinia()],
    },
  })
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('TransactionForm — FX section uses ExchangeRateInput for the rate field', () => {
  it('renders ExchangeRateInput for the exchange rate in the FX section', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    // After integration, ExchangeRateInput must be present in the FX section
    const exchangeRateInputComponents = wrapper.findAllComponents(ExchangeRateInput)
    expect(exchangeRateInputComponents.length).toBe(1)
  })

  it('passes baseCurrency (foreignCurrency) to ExchangeRateInput', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    const exchangeRateInputComponent = wrapper.findComponent(ExchangeRateInput)
    expect(exchangeRateInputComponent.props('baseCurrency')).toBe('USD')
  })

  it('passes quoteCurrency (selectedAccountCurrency) to ExchangeRateInput', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    const exchangeRateInputComponent = wrapper.findComponent(ExchangeRateInput)
    expect(exchangeRateInputComponent.props('quoteCurrency')).toBe('COP')
  })

  it('has zero input[type="number"] elements after ExchangeRateInput integration', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    // Before integration: 1 input[type="number"] (the rate field).
    // After integration: 0 — ExchangeRateInput uses type="text" inputmode="decimal".
    const numberInputs = wrapper.findAll('input[type="number"]')
    expect(numberInputs.length).toBe(0)
  })

  it('does not expose handleRateInput on the component instance after integration', async () => {
    const wrapper = buildWrapper()
    await flushPromises()

    // handleRateInput was the bridge between the old plain <input> @input event
    // and the exchangeRate ref. After replacing with ExchangeRateInput, this
    // handler is no longer needed and must be removed.
    const vm = wrapper.vm as any
    expect(typeof vm.handleRateInput).not.toBe('function')
  })
})
