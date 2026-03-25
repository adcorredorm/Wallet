/**
 * TransferForm.exchange-rate-input.spec.ts
 *
 * RED tests: verifies that TransferForm uses ExchangeRateInput for the
 * exchange rate field instead of a plain <input> with v-model="exchangeRateStr".
 *
 * Scope:
 *   1. When isCrossCurrency is true, ExchangeRateInput is rendered instead of
 *      a plain <input type="text"> for the rate field
 *   2. The old bidirectional display div (rateDisplayForward / rateDisplayInverse)
 *      is no longer rendered separately — ExchangeRateInput handles it internally
 *   3. rateDisplayForward and rateDisplayInverse are NOT exposed on the
 *      component instance (they were removed from <script setup>)
 *   4. The rate deviation alert div (showRateAlert) still renders when
 *      applicable — it must NOT have been removed
 *
 * Mock strategy:
 * - All heavy child components are stubbed except ExchangeRateInput (rendered real)
 * - useExchangeRatesStore returns getRate() = 4200 for any currency pair
 * - formatDateForInput / validators are mocked with minimal implementations
 *
 * Why we test by rendered component type?
 * The template is the public contract. Verifying ExchangeRateInput renders
 * proves the integration happened and that users see the bidirectional UI.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import type { Account } from '@/types'

// ---------------------------------------------------------------------------
// Mocks — must be declared BEFORE component imports
// ---------------------------------------------------------------------------

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
    getRateDisplay: (_from: string, _to: string) => '1 USD = 4,200 COP',
  }),
}))

// ---------------------------------------------------------------------------
// Stub heavy child components — keep ExchangeRateInput real
// ---------------------------------------------------------------------------

vi.mock('@/components/ui/BaseInput.vue', () => ({
  default: { template: '<input />' },
}))
vi.mock('@/components/ui/BaseButton.vue', () => ({
  default: { template: '<button><slot /></button>' },
}))
vi.mock('@/components/shared/DatePicker.vue', () => ({
  default: { template: '<input type="date" />' },
}))
vi.mock('@/components/shared/AmountInput.vue', () => ({
  default: {
    props: ['modelValue', 'currency', 'label', 'placeholder', 'error', 'required'],
    emits: ['update:modelValue'],
    template: '<input type="text" inputmode="decimal" />',
  },
}))
vi.mock('@/components/accounts/AccountSelect.vue', () => ({
  default: {
    props: ['modelValue', 'accounts', 'label', 'placeholder', 'error', 'filterOutAccountId'],
    emits: ['update:modelValue'],
    template: '<select />',
  },
}))

// ---------------------------------------------------------------------------
// Import component AFTER mocks
// ---------------------------------------------------------------------------
import TransferForm from '../TransferForm.vue'
import ExchangeRateInput from '@/components/shared/ExchangeRateInput.vue'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const USD_ACCOUNT: Account = {
  id: 'acc-usd',
  name: 'USD Account',
  type: 'checking' as any,
  currency: 'USD',
  tags: [],
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const COP_ACCOUNT: Account = {
  id: 'acc-cop',
  name: 'COP Account',
  type: 'savings' as any,
  currency: 'COP',
  tags: [],
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

/** Mounts TransferForm with a pre-existing cross-currency transfer
 *  so isCrossCurrency is true and the exchange rate section is visible. */
function buildWrapper() {
  return mount(TransferForm, {
    props: {
      accounts: [USD_ACCOUNT, COP_ACCOUNT],
      loading: false,
      transfer: {
        id: 'tf-1',
        source_account_id: 'acc-usd',
        destination_account_id: 'acc-cop',
        amount: 100,
        date: '2026-03-25',
        exchange_rate: 4200,
        destination_amount: 420000,
        destination_currency: 'COP',
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
describe('TransferForm — exchange rate section uses ExchangeRateInput', () => {
  it('renders ExchangeRateInput in the exchange-rate section (not a plain input)', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    // After integration, ExchangeRateInput must be present
    const exchangeRateInputs = wrapper.findAllComponents(ExchangeRateInput)
    expect(exchangeRateInputs.length).toBe(1)
  })

  it('passes baseCurrency (originAccountCurrency) to ExchangeRateInput', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    const exchangeRateInputComponent = wrapper.findComponent(ExchangeRateInput)
    expect(exchangeRateInputComponent.props('baseCurrency')).toBe('USD')
  })

  it('passes quoteCurrency (destAccountCurrency) to ExchangeRateInput', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    const exchangeRateInputComponent = wrapper.findComponent(ExchangeRateInput)
    expect(exchangeRateInputComponent.props('quoteCurrency')).toBe('COP')
  })

  it('passes the numeric exchangeRate as modelValue to ExchangeRateInput', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    const exchangeRateInputComponent = wrapper.findComponent(ExchangeRateInput)
    // transfer.exchange_rate = 4200
    expect(exchangeRateInputComponent.props('modelValue')).toBeCloseTo(4200, 5)
  })

  it('does not expose rateDisplayForward computed on the component instance', async () => {
    const wrapper = buildWrapper()
    await flushPromises()

    const vm = wrapper.vm as any
    expect(vm.rateDisplayForward).toBeUndefined()
  })

  it('does not expose rateDisplayInverse computed on the component instance', async () => {
    const wrapper = buildWrapper()
    await flushPromises()

    const vm = wrapper.vm as any
    expect(vm.rateDisplayInverse).toBeUndefined()
  })

  it('does not render the old separate bidirectional rate display div', async () => {
    const wrapper = buildWrapper()
    await flushPromises()
    await nextTick()

    // The old pattern was: <div v-if="rateDisplayForward && rateDisplayInverse" ...>
    // We look for the specific class combination used in that div
    const rateDisplayDiv = wrapper.find('.text-xs.text-slate-400.space-y-0\\.5')
    expect(rateDisplayDiv.exists()).toBe(false)
  })

  it('still renders the rate deviation alert when showRateAlert would be true', async () => {
    // Mount with an extreme rate that deviates >10% from the suggested 4200
    const wrapper = mount(TransferForm, {
      props: {
        accounts: [USD_ACCOUNT, COP_ACCOUNT],
        loading: false,
        transfer: {
          id: 'tf-2',
          source_account_id: 'acc-usd',
          destination_account_id: 'acc-cop',
          amount: 100,
          date: '2026-03-25',
          exchange_rate: 1000, // far from suggested 4200 → should trigger alert
          destination_amount: 100000,
          destination_currency: 'COP',
        } as any,
      },
      global: {
        plugins: [createPinia()],
      },
    })
    await flushPromises()
    await nextTick()

    // The deviation alert text must still be present
    expect(wrapper.text()).toContain('tasa')
  })
})
