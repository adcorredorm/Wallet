/**
 * TransactionForm.fx-amount-input.spec.ts
 *
 * RED test: verifies that the FX section uses AmountInput for originalAmount
 * and accountAmount fields instead of plain <input type="number"> elements.
 *
 * Scope:
 *   1. When fxActive is true (foreignCurrency differs from account currency),
 *      the FX section renders AmountInput for originalAmount — not input[type="number"]
 *   2. When fxActive is true, the FX section renders AmountInput for accountAmount
 *      — not input[type="number"]
 *   3. The unused handlers handleOriginalAmountInput and handleAccountAmountInput
 *      do not exist on the component instance after the refactor
 *
 * Why we test via rendered DOM rather than vm methods?
 * The template is the public contract. Testing that the correct component is
 * rendered gives us confidence the refactor actually happened and that the
 * correct input mode (AmountInput) is being used by users.
 *
 * Mock strategy:
 * - All child components except AmountInput are stubbed to prevent deep
 *   dependency chains (Pinia stores, router, etc.) from breaking tests.
 * - AmountInput is NOT stubbed — we render it for real so we can verify
 *   AmountInput instances appear in the DOM via data-testid or component type.
 * - useExchangeRatesStore is mocked to return a static getRate function.
 * - SUPPORTED_CURRENCIES and CURRENCIES are mocked with minimal data.
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
// Stub heavy child components — only AmountInput is real
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

// ---------------------------------------------------------------------------
// Import component AFTER mocks
// ---------------------------------------------------------------------------
import TransactionForm from '../TransactionForm.vue'
import AmountInput from '@/components/shared/AmountInput.vue'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Minimal account data to satisfy AccountSelect and selectedAccountCurrency */
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

/** Mounts TransactionForm with FX active:
 *  account currency = COP, foreignCurrency preset to USD → fxActive = true */
function buildWrapper() {
  return mount(TransactionForm, {
    props: {
      accounts: [TEST_ACCOUNT],
      categories: [TEST_CATEGORY],
      loading: false,
      // Pre-populate a transaction with FX data so the section is open
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
describe('TransactionForm — FX section uses AmountInput', () => {
  it('renders AmountInput for originalAmount in FX section (not input[type="number"])', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    // The FX section should be open (transaction has original_currency)
    // AmountInput renders an <input type="text" inputmode="decimal">
    // A plain input[type="number"] would indicate the refactor did NOT happen

    const amountInputComponents = wrapper.findAllComponents(AmountInput)

    // There should be AmountInput instances: at least the main amount field
    // plus originalAmount and accountAmount in the FX section = 3 total
    expect(amountInputComponents.length).toBeGreaterThanOrEqual(3)

    // Confirm no input[type="number"] exists anywhere in the form.
    // originalAmount and accountAmount use AmountInput (type="text" inputmode="decimal").
    // The exchange_rate field was replaced by ExchangeRateInput (Task 4), which also
    // uses type="text" inputmode="decimal". So the total count must be 0.
    const numberInputs = wrapper.findAll('input[type="number"]')
    expect(numberInputs.length).toBe(0) // all rate/amount fields use text inputs
  })

  it('renders AmountInput for accountAmount in FX section (not input[type="number"])', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    // Find all AmountInput instances — after refactor there should be:
    // 1. Main amount field (top of form)
    // 2. originalAmount in FX section
    // 3. accountAmount in FX section
    const amountInputComponents = wrapper.findAllComponents(AmountInput)
    expect(amountInputComponents.length).toBeGreaterThanOrEqual(3)
  })

  it('does not expose handleOriginalAmountInput on the component instance', async () => {
    const wrapper = buildWrapper()
    await flushPromises()

    // After refactor, the handler should be removed because AmountInput
    // emits `update:modelValue` directly instead of relying on a raw input event.
    const vm = wrapper.vm as any
    expect(typeof vm.handleOriginalAmountInput).not.toBe('function')
  })

  it('does not expose handleAccountAmountInput on the component instance', async () => {
    const wrapper = buildWrapper()
    await flushPromises()

    // Same reasoning as above — should be deleted from <script setup>
    const vm = wrapper.vm as any
    expect(typeof vm.handleAccountAmountInput).not.toBe('function')
  })
})
