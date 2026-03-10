// Smoke test — verifies Vitest globals work, the @-alias resolves,
// and jsdom environment provides window/navigator.
import { formatCurrency } from '@/utils/formatters'

describe('vitest setup smoke test', () => {
  it('resolves the @ path alias', () => {
    expect(typeof formatCurrency).toBe('function')
  })

  it('runs in jsdom (window is defined)', () => {
    expect(typeof window).toBe('object')
  })

  it('navigator.onLine is accessible', () => {
    expect(typeof navigator.onLine).toBe('boolean')
  })
})
