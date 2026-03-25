/**
 * ExchangeRateInput.spec.ts
 *
 * Tests for the bidirectional exchange rate input component.
 *
 * Scope:
 *   1. Typing in Field 1 (quoteCurrency per 1 baseCurrency) updates Field 2 with
 *      the inverse rate in real-time
 *   2. Typing in Field 2 (baseCurrency per 1 quoteCurrency) updates Field 1 with
 *      the inverse rate and emits the canonical rate
 *   3. modelValue=0 → both fields show empty string
 *   4. disabled=true → both inputs render as readonly and have opacity class
 *   5. External modelValue update (prop change) syncs both display fields
 *   6. Invalid / negative / zero input clears the other field gracefully
 *   7. Error prop renders the error message
 *   8. No infinite loop: sequential inputs do not stack up unboundedly
 *
 * Why plain-text inputs with :value (not v-model)?
 * The component uses :value + @input to retain full control over displayed text
 * (same pattern as AmountInput). jsdom reflects Vue's reactive :value binding in
 * wrapper.find('input').attributes('value') after nextTick, which is the reliable
 * read path used throughout these tests.
 *
 * formatRateForDisplay uses toFixed(10) then parseFloat().toString() to strip
 * trailing zeros. Tests use closeTo / string parsing to remain resilient against
 * floating-point representation edge cases.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import ExchangeRateInput from '../ExchangeRateInput.vue'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildWrapper(props: Record<string, unknown> = {}) {
  return mount(ExchangeRateInput, {
    props: {
      modelValue: 0,
      baseCurrency: 'USD',
      quoteCurrency: 'COP',
      ...props,
    },
  })
}

/** Returns [field1Value, field2Value] from the two inputs in the component. */
function getDisplayValues(wrapper: ReturnType<typeof buildWrapper>): [string, string] {
  const inputs = wrapper.findAll('input')
  // :value binding is reflected in the attribute after Vue re-renders
  return [
    inputs[0].attributes('value') ?? '',
    inputs[1].attributes('value') ?? '',
  ]
}

/**
 * Simulates typing a value into the nth input (0 = Field 1, 1 = Field 2).
 * Sets el.value and dispatches an input event — same pattern as AmountInput tests.
 */
async function simulateInput(
  wrapper: ReturnType<typeof buildWrapper>,
  fieldIndex: 0 | 1,
  value: string
): Promise<void> {
  const inputs = wrapper.findAll('input')
  const el = inputs[fieldIndex].element as HTMLInputElement
  el.value = value
  await inputs[fieldIndex].trigger('input')
  await flushPromises()
  await nextTick()
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
beforeEach(() => {
  // No stores or mocks required — ExchangeRateInput is a standalone
  // presentational component with no external dependencies.
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('ExchangeRateInput — bidirectional rate display', () => {
  it('both fields are empty when modelValue is 0', () => {
    const wrapper = buildWrapper({ modelValue: 0 })
    const [f1, f2] = getDisplayValues(wrapper)
    expect(f1).toBe('')
    expect(f2).toBe('')
  })

  it('initialises both fields from a non-zero modelValue', () => {
    // modelValue=4200 (COP per 1 USD) → field1="4200", field2="0.0002380952380952"
    const wrapper = buildWrapper({ modelValue: 4200 })
    const [f1, f2] = getDisplayValues(wrapper)
    expect(parseFloat(f1)).toBeCloseTo(4200, 5)
    expect(parseFloat(f2)).toBeCloseTo(1 / 4200, 10)
  })

  it('typing in Field 1 updates Field 2 with the inverse rate', async () => {
    const wrapper = buildWrapper()
    await simulateInput(wrapper, 0, '4200')

    const [, f2] = getDisplayValues(wrapper)
    expect(parseFloat(f2)).toBeCloseTo(1 / 4200, 10)
  })

  it('typing in Field 1 emits the canonical rate (quoteCurrency per baseCurrency)', async () => {
    const wrapper = buildWrapper()
    await simulateInput(wrapper, 0, '4200')

    const emitted = wrapper.emitted('update:modelValue') as number[][]
    expect(emitted).toBeTruthy()
    const lastEmit = emitted[emitted.length - 1][0]
    expect(lastEmit).toBeCloseTo(4200, 5)
  })

  it('typing in Field 2 updates Field 1 with the inverse', async () => {
    const wrapper = buildWrapper()
    await simulateInput(wrapper, 1, '0.0002')

    const [f1] = getDisplayValues(wrapper)
    // 1 / 0.0002 = 5000
    expect(parseFloat(f1)).toBeCloseTo(5000, 5)
  })

  it('typing in Field 2 emits the canonical rate (1 / field2Value)', async () => {
    const wrapper = buildWrapper()
    await simulateInput(wrapper, 1, '0.0002')

    const emitted = wrapper.emitted('update:modelValue') as number[][]
    expect(emitted).toBeTruthy()
    const lastEmit = emitted[emitted.length - 1][0]
    // canonical = 1 / 0.0002 = 5000
    expect(lastEmit).toBeCloseTo(5000, 5)
  })

  it('clears Field 2 when Field 1 is cleared', async () => {
    const wrapper = buildWrapper({ modelValue: 4200 })
    await simulateInput(wrapper, 0, '')

    const [, f2] = getDisplayValues(wrapper)
    expect(f2).toBe('')
  })

  it('clears Field 1 when Field 2 is cleared', async () => {
    const wrapper = buildWrapper({ modelValue: 4200 })
    await simulateInput(wrapper, 1, '')

    const [f1] = getDisplayValues(wrapper)
    expect(f1).toBe('')
  })

  it('renders both inputs as readonly when disabled=true', () => {
    const wrapper = buildWrapper({ disabled: true })
    const inputs = wrapper.findAll('input')
    // The spec uses :readonly="disabled" — check the attribute
    expect(inputs[0].attributes('readonly')).toBeDefined()
    expect(inputs[1].attributes('readonly')).toBeDefined()
  })

  it('applies opacity class to both inputs when disabled=true', () => {
    const wrapper = buildWrapper({ disabled: true })
    const inputs = wrapper.findAll('input')
    expect(inputs[0].classes()).toContain('opacity-50')
    expect(inputs[1].classes()).toContain('opacity-50')
  })

  it('renders error message when error prop is provided', () => {
    const wrapper = buildWrapper({ error: 'Tasa inválida' })
    expect(wrapper.text()).toContain('Tasa inválida')
  })

  it('does not render error paragraph when error prop is absent', () => {
    const wrapper = buildWrapper()
    expect(wrapper.find('p').exists()).toBe(false)
  })

  it('external modelValue update syncs both fields without loop', async () => {
    const wrapper = buildWrapper({ modelValue: 100 })
    const [f1Before] = getDisplayValues(wrapper)
    expect(parseFloat(f1Before)).toBeCloseTo(100, 5)

    // Simulate parent updating modelValue programmatically
    await wrapper.setProps({ modelValue: 200 })
    await flushPromises()
    await nextTick()

    const [f1After, f2After] = getDisplayValues(wrapper)
    expect(parseFloat(f1After)).toBeCloseTo(200, 5)
    expect(parseFloat(f2After)).toBeCloseTo(1 / 200, 10)
  })

  it('invalid text in Field 1 clears Field 2', async () => {
    const wrapper = buildWrapper({ modelValue: 4200 })
    await simulateInput(wrapper, 0, 'abc')

    const [, f2] = getDisplayValues(wrapper)
    expect(f2).toBe('')
  })

  it('zero in Field 1 clears Field 2', async () => {
    const wrapper = buildWrapper({ modelValue: 4200 })
    await simulateInput(wrapper, 0, '0')

    const [, f2] = getDisplayValues(wrapper)
    expect(f2).toBe('')
  })

  it('renders labels with currency names', () => {
    const wrapper = buildWrapper({ baseCurrency: 'USD', quoteCurrency: 'COP' })
    const text = wrapper.text()
    expect(text).toContain('COP')
    expect(text).toContain('USD')
  })

  it('sequential inputs in Field 1 do not accumulate emit events unboundedly', async () => {
    const wrapper = buildWrapper()
    await simulateInput(wrapper, 0, '100')
    await simulateInput(wrapper, 0, '200')
    await simulateInput(wrapper, 0, '300')

    const emitted = wrapper.emitted('update:modelValue') as number[][]
    // Each simulateInput triggers exactly 1 emit — total should be exactly 3
    expect(emitted.length).toBe(3)
    // Last emit is the rate for 300
    expect(emitted[emitted.length - 1][0]).toBeCloseTo(300, 5)
  })

  it('formatRateForDisplay strips trailing zeros for whole numbers', async () => {
    const wrapper = buildWrapper({ modelValue: 5000 })
    const [f1] = getDisplayValues(wrapper)
    // 5000 must display as "5000" not "5000.0000000000"
    expect(f1).toBe('5000')
  })
})
