import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const showWarning = vi.fn()
vi.mock('@/stores', () => ({
  useUiStore: () => ({ showWarning }),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

import FloatingActionButton from '../FloatingActionButton.vue'

describe('FloatingActionButton disabled', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens menu when not disabled', async () => {
    const w = mount(FloatingActionButton, { props: { disabled: false } })
    await w.find('.fab-button').trigger('click')
    expect(w.find('.fab-menu').exists()).toBe(true)
  })

  it('does NOT open menu when disabled', async () => {
    const w = mount(FloatingActionButton, { props: { disabled: true } })
    await w.find('.fab-button').trigger('click')
    expect(w.find('.fab-menu').exists()).toBe(false)
  })

  it('shows warning toast when tapped while disabled', async () => {
    const w = mount(FloatingActionButton, { props: { disabled: true } })
    await w.find('.fab-button').trigger('click')
    expect(showWarning).toHaveBeenCalledWith('Completa la configuración primero')
  })

  it('applies disabled visual styles when disabled', () => {
    const w = mount(FloatingActionButton, { props: { disabled: true } })
    expect(w.find('.fab-button').classes()).toContain('fab-button-disabled')
  })
})
